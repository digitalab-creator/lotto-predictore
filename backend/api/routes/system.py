from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.base import SessionLocal
from datetime import datetime
from models import Model
from logger import logger
import torch
import torch.nn as nn
from pathlib import Path
import shutil
import re
import asyncio
from algorithms.dl.sequence_classifier import LottoLSTM

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/health")
async def health_check():
    """
    Health check endpoint that verifies FastAPI is running.
    Database check is optional and non-blocking to prevent timeouts during heavy operations.
    Returns immediately if FastAPI is up, even if DB check is slow/busy.
    """
    # FastAPI is always up if we can respond
    fastapi_status = "up"
    database_status = "unknown"
    database_error = None
    
    # Try to check database with a very short timeout to avoid blocking
    # Use a separate task that we can cancel if it takes too long
    try:
        db = SessionLocal()
        db_check_task = None
        try:
            # Run the database check with a very short timeout (1 second)
            # This ensures we return quickly even if DB is busy
            db_check_task = asyncio.create_task(
                asyncio.wait_for(
                    asyncio.to_thread(db.execute, text("SELECT 1")),
                    timeout=1.0  # 1 second timeout - very aggressive
                )
            )
            await db_check_task
            database_status = "up"
        except asyncio.TimeoutError:
            database_status = "timeout"
            database_error = "Database check timed out (likely busy with operations)"
            # Cancel the task if it's still running
            if db_check_task and not db_check_task.done():
                db_check_task.cancel()
            logger.debug(
                "Arrr! Health check database timeout - service may be busy",
                context={"timeout_seconds": 1}
            )
        except asyncio.CancelledError:
            database_status = "timeout"
            database_error = "Database check cancelled (likely busy)"
            logger.debug("Arrr! Health check database check cancelled")
        except Exception as e:
            database_status = "down"
            database_error = str(e)
            logger.warning(
                "Arrr! Health check database error",
                context={"error": str(e)}
            )
        finally:
            try:
                db.close()
            except Exception:
                pass  # Ignore errors during cleanup
    except Exception as e:
        database_status = "error"
        database_error = str(e)
        logger.warning(
            "Arrr! Health check database connection error",
            context={"error": str(e)}
        )
    
    # Return healthy if FastAPI is up, even if DB check fails/timeouts
    # This prevents health checks from failing during heavy operations
    # The cron service can still proceed even if DB is busy
    return {
        "status": "healthy" if fastapi_status == "up" else "unhealthy",
        "services": {
            "fastapi": fastapi_status,
            "database": database_status
        },
        "database_error": database_error,
        "timestamp": datetime.now().isoformat()
    }

@router.post("/api/check-model-files")
async def check_model_files_endpoint(db: Session = Depends(get_db)):
    """
    Endpoint to check all PyTorch model files for corruption.
    Does a thorough check by trying to use the model, not just load it.
    If loading fails, tries different model architectures to find the correct one.
    Returns detailed report of model file health status.
    """
    try:
        models_dir = Path("/app/algorithms/dl/models")
        corrupted_files = []
        healthy_files = []
        
        # Get all models from database
        db_models = db.query(Model).all()
        model_paths = {m.model_path for m in db_models if m.model_path}
        
        # Model class definitions for thorough testing
        class LottoLSTMPosition(nn.Module):
            def __init__(self, num_numbers=37, seq_len=10, hidden_size=64, num_layers=2, num_positions=6):
                super().__init__()
                self.num_numbers = num_numbers
                self.seq_len = seq_len
                self.num_positions = num_positions
                self.lstm = nn.LSTM(input_size=num_numbers, hidden_size=hidden_size, num_layers=num_layers, batch_first=True)
                self.fc = nn.Linear(hidden_size, num_numbers * num_positions)
                self.softmax = nn.Softmax(dim=2)

            def forward(self, x):
                out, _ = self.lstm(x)
                out = out[:, -1, :]  # Take last output
                out = self.fc(out)
                out = out.view(-1, self.num_positions, self.num_numbers)
                out = self.softmax(out)
                return out

        def try_load_model(fname, is_position_model, state_dict):
            """Try loading the model with different architectures until one works."""
            # Try architectures in order of likelihood
            hidden_sizes = [64, 128, 256, 32]  # Most common first
            num_layers_options = [2, 1, 3]      # Most common first
            
            # First try the architecture from filename
            hidden_size = 64  # default
            num_layers = 2    # default
            if "h128" in fname.name:
                hidden_size = 128
            elif "h256" in fname.name:
                hidden_size = 256
            elif "h32" in fname.name:
                hidden_size = 32
            if "l1" in fname.name:
                num_layers = 1
            elif "l3" in fname.name:
                num_layers = 3
            
            # Try the architecture from filename first
            try:
                if is_position_model:
                    model = LottoLSTMPosition(hidden_size=hidden_size, num_layers=num_layers)
                else:
                    model = LottoLSTM(hidden_size=hidden_size, num_layers=num_layers)
                model.load_state_dict(state_dict)
                return model, hidden_size, num_layers
            except Exception as e:
                logger.warning(
                    f"Arrr! Failed to load {fname.name} with architecture from filename, trying others...",
                    context={
                        "file": fname.name,
                        "error": str(e),
                        "tried_hidden_size": hidden_size,
                        "tried_num_layers": num_layers
                    }
                )
            
            # Try other architectures
            for h in hidden_sizes:
                for l in num_layers_options:
                    if h == hidden_size and l == num_layers:
                        continue  # Skip the one we already tried
                    try:
                        if is_position_model:
                            model = LottoLSTMPosition(hidden_size=h, num_layers=l)
                        else:
                            model = LottoLSTM(hidden_size=h, num_layers=l)
                        model.load_state_dict(state_dict)
                        logger.info(
                            f"Arrr! Found correct architecture for {fname.name}!",
                            context={
                                "file": fname.name,
                                "actual_hidden_size": h,
                                "actual_num_layers": l,
                                "filename_hidden_size": hidden_size,
                                "filename_num_layers": num_layers
                            }
                        )
                        return model, h, l
                    except Exception:
                        continue
            
            raise Exception("Could not find a working architecture for this model")
        
        # Check each .pt file
        for fname in models_dir.glob("*.pt"):
            try:
                # First try loading the state dict
                state_dict = torch.load(str(fname))
                
                # Determine model type from filename
                is_position_model = "position" in fname.name
                
                # Try to load the model with different architectures
                model, actual_hidden_size, actual_num_layers = try_load_model(fname, is_position_model, state_dict)
                
                # Try to use the model
                model.eval()
                with torch.no_grad():
                    # Create dummy input
                    if is_position_model:
                        dummy_input = torch.zeros((1, model.seq_len, 37))
                        output = model(dummy_input)
                        # Check output shape
                        assert output.shape == (1, model.num_positions, 37), f"Invalid output shape: {output.shape}"
                    else:
                        dummy_input = torch.zeros((1, model.seq_len, 37))
                        output = model(dummy_input)
                        # Check output shape
                        assert output.shape == (1, 37), f"Invalid output shape: {output.shape}"
                
                # Get architecture from filename for comparison
                filename_hidden_size = 64  # default
                filename_num_layers = 2    # default
                if "h128" in fname.name:
                    filename_hidden_size = 128
                elif "h256" in fname.name:
                    filename_hidden_size = 256
                elif "h32" in fname.name:
                    filename_hidden_size = 32
                if "l1" in fname.name:
                    filename_num_layers = 1
                elif "l3" in fname.name:
                    filename_num_layers = 3
                
                file_info = {
                    "file": fname.name,
                    "size": fname.stat().st_size,
                    "last_modified": datetime.fromtimestamp(fname.stat().st_mtime).isoformat(),
                    "in_db": str(fname) in model_paths,
                    "model_type": "position" if is_position_model else "sequence",
                    "filename_hidden_size": filename_hidden_size,
                    "filename_num_layers": filename_num_layers,
                    "actual_hidden_size": actual_hidden_size,
                    "actual_num_layers": actual_num_layers,
                    "architecture_mismatch": filename_hidden_size != actual_hidden_size or filename_num_layers != actual_num_layers
                }
                healthy_files.append(file_info)
                logger.info(
                    f"Arrr! Model file {fname.name} be healthy!",
                    context={
                        "file": fname.name,
                        "in_db": file_info["in_db"],
                        "model_type": file_info["model_type"],
                        "filename_hidden_size": filename_hidden_size,
                        "filename_num_layers": filename_num_layers,
                        "actual_hidden_size": actual_hidden_size,
                        "actual_num_layers": actual_num_layers,
                        "architecture_mismatch": file_info["architecture_mismatch"]
                    }
                )
            except Exception as e:
                file_info = {
                    "file": fname.name,
                    "error": str(e),
                    "size": fname.stat().st_size,
                    "last_modified": datetime.fromtimestamp(fname.stat().st_mtime).isoformat(),
                    "in_db": str(fname) in model_paths,
                    "model_type": "position" if "position" in fname.name else "sequence"
                }
                corrupted_files.append(file_info)
                logger.error(
                    f"Arrr! Found corrupted model file: {fname.name}!",
                    context={
                        "file": fname.name,
                        "error": str(e),
                        "in_db": file_info["in_db"],
                        "model_type": file_info["model_type"]
                    }
                )
                # Move corrupted file to backup directory
                backup_dir = models_dir / "corrupted_backups"
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / f"{fname.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{fname.suffix}"
                shutil.move(str(fname), str(backup_path))
                logger.info(
                    f"Arrr! Moved corrupted file {fname.name} to backup: {backup_path.name}",
                    context={
                        "original_file": fname.name,
                        "backup_file": backup_path.name
                    }
                )
                
                # Update database if model was registered
                if str(fname) in model_paths:
                    db_model = next((m for m in db_models if m.model_path == str(fname)), None)
                    if db_model:
                        db_model.model_path = None  # Clear the path since file is corrupted
                        db.add(db_model)
                        logger.warning(
                            f"Arrr! Cleared model_path for corrupted model in DB: {db_model.name} v{db_model.version}",
                            context={
                                "model_id": db_model.id,
                                "model_name": db_model.name,
                                "model_version": db_model.version
                            }
                        )
        
        # Commit any database changes
        if corrupted_files:
            db.commit()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_checked": len(healthy_files) + len(corrupted_files),
                "healthy_files": len(healthy_files),
                "corrupted_files": len(corrupted_files),
                "files_in_db": len(model_paths),
                "files_with_architecture_mismatch": sum(1 for f in healthy_files if f.get("architecture_mismatch", False))
            },
            "healthy_files": healthy_files,
            "corrupted_files": corrupted_files
        }
        
    except Exception as e:
        logger.error(
            "Arrr! Error during model file check!",
            context={"error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check model files: {str(e)}"
        ) 