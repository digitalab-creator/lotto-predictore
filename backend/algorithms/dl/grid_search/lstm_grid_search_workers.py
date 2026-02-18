"""Worker functions for parallel LSTM grid search processing"""
import torch
import numpy as np
import random
import os
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from models import Draw
from shared.logging_service import get_backend_logger
from config import (
    SEQUENCE_CLASSIFIER_MODEL_DIR, 
    PRIZE_TABLE, 
    TICKET_COST_PER_TABLE,
    LOTTO_NUMBERS_COUNT,
    LSTM_GRID_SEARCH_TEST_COUNT,
    LSTM_TABLES_PER_DRAW,
    LSTM_GRID_SEARCH_THRESHOLD
)
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from services.simulation_helpers.simulation_utils import calculate_roi_with_tax
from ..core.lstm_model import LottoLSTM, draws_to_sequences

logger = get_backend_logger()


def _train_model_worker(model, train_draws, params, device):
    """Module-level function to train model"""
    X, y = draws_to_sequences(train_draws, seq_len=params['seq_len'], num_numbers=LOTTO_NUMBERS_COUNT)
    # Move data to device
    X = X.to(device)
    y = y.to(device)
    
    criterion = torch.nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=params['lr'])
    model = model.to(device)
    
    for epoch in range(params['epochs']):
        model.train()
        permutation = torch.randperm(X.size(0))
        for i in range(0, X.size(0), params['batch_size']):
            indices = permutation[i:i+params['batch_size']]
            batch_x, batch_y = X[indices], y[indices]
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
    
    return model


def _evaluate_single_strong_algo_worker(strong_name, strong_cls, model_path, params, train_draws, test_draws, combo_idx, total_combinations, strong_algos_count, device):
    """Module-level function to evaluate a single strong algorithm"""
    try:
        if len(train_draws) < params['seq_len'] + 1:
            logger.error(f"Arrr! [FSM GRID] Not enough draws for evaluation!")
            return None
        
        logger.info(
            f"Arrr! [FSM GRID] Evaluating strong algo: {strong_name}",
            context={
                "params": params,
                "test_count": len(test_draws),
                "strong_algo": strong_name,
                "combo_progress": f"{combo_idx}/{total_combinations}"
            }
        )
        
        strong_algo = strong_cls()
        all_prizes = 0
        total_tickets = 0
        prizes_list = []
        
        # Load model once for this strong algo evaluation
        model = LottoLSTM(
            num_numbers=LOTTO_NUMBERS_COUNT,
            seq_len=params['seq_len'],
            hidden_size=params['hidden_size'],
            num_layers=params['num_layers']
        )
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        model.load_state_dict(torch.load(model_path, map_location=device))
        model = model.to(device)
        model.eval()
        
        def predict_next_numbers_patched(draws, seq_len, threshold=LSTM_GRID_SEARCH_THRESHOLD):
            seq = draws[-seq_len:]
            x_seq = []
            for d in seq:
                onehot = [0]*LOTTO_NUMBERS_COUNT
                for n in d.numbers:
                    onehot[n-1] = 1
                x_seq.append(onehot)
            x_tensor = torch.tensor([x_seq], dtype=torch.float32).to(device)
            with torch.no_grad():
                output = model(x_tensor)[0].cpu()
            pred = (output > threshold).nonzero(as_tuple=True)[0].tolist()
            numbers = [i+1 for i in pred]
            NUMBERS_PER_COMBO = 6
            if len(numbers) > NUMBERS_PER_COMBO:
                top6 = output.topk(NUMBERS_PER_COMBO).indices.tolist()
                numbers = [i+1 for i in top6]
            elif len(numbers) < NUMBERS_PER_COMBO:
                all_numbers = [n for d in draws for n in d.numbers]
                from collections import Counter
                freq = Counter(all_numbers)
                for n, _ in freq.most_common():
                    if n not in numbers:
                        numbers.append(n)
                    if len(numbers) == NUMBERS_PER_COMBO:
                        break
            return sorted(numbers)
        
        for i, test_draw in enumerate(test_draws):
            if i % 2 == 0 or i == len(test_draws) - 1:
                logger.debug(
                    f"Arrr! [FSM GRID] Test draw {i+1}/{len(test_draws)} for {strong_name}",
                    context={
                        "test_draw_date": test_draw.date,
                        "params": params,
                        "strong_algo": strong_name,
                        "draw_progress": f"{i+1}/{len(test_draws)}"
                    }
                )
            available_draws = train_draws + test_draws[:i]
            combos = []
            for j in range(LSTM_TABLES_PER_DRAW):
                torch.manual_seed(j)
                np.random.seed(j)
                random.seed(j)
                numbers = predict_next_numbers_patched(available_draws, seq_len=params['seq_len'], threshold=LSTM_GRID_SEARCH_THRESHOLD)
                strong = strong_algo.predict(available_draws, numbers=numbers)
                combos.append({"numbers": numbers, "strong": strong})
            for combo in combos:
                hits = sum([n in test_draw.numbers for n in combo["numbers"]])
                strong_hit = (combo["strong"] == test_draw.strong_number)
                prize = PRIZE_TABLE.get((hits, strong_hit), 0)
                all_prizes += prize
                total_tickets += 1
                prizes_list.append(prize)
        
        total_cost = total_tickets * TICKET_COST_PER_TABLE
        roi = calculate_roi_with_tax(prizes_list, total_cost)
        
        logger.info(
            f"Arrr! [FSM GRID] Completed evaluation for {strong_name}",
            context={
                "params": params,
                "strong_algo": strong_name,
                "roi": roi,
                "total_prize": all_prizes,
                "test_count": len(test_draws)
            }
        )
        
        return {
            'params': params,
            'model_path': model_path,
            'strong_algo': strong_name,
            'roi': roi,
            'total_prize': all_prizes,
            'total_cost': total_cost,
            'test_count': len(test_draws)
        }
    except Exception as e:
        logger.error(
            f"Arrr! [FSM GRID] Error evaluating strong algo {strong_name}: {e}",
            context={"strong_algo": strong_name, "params": params, "error": str(e)}
        )
        return None


def _evaluate_strong_algos_parallel_worker(model_path, params, train_draws, test_draws, combo_idx, total_combinations, device, enable_parallel_strong, strong_algo_workers):
    """Module-level function to evaluate all strong algos in parallel"""
    strong_algo_list = list(STRONG_NUMBER_REGISTRY.items())
    results = []
    
    if enable_parallel_strong and len(strong_algo_list) > 1:
        # Use ThreadPoolExecutor for parallel strong algo evaluation
        with ThreadPoolExecutor(max_workers=strong_algo_workers) as executor:
            futures = {
                executor.submit(
                    _evaluate_single_strong_algo_worker,
                    strong_name,
                    strong_cls,
                    model_path,
                    params,
                    train_draws,
                    test_draws,
                    combo_idx,
                    total_combinations,
                    len(strong_algo_list),
                    device
                ): strong_name
                for strong_name, strong_cls in strong_algo_list
            }
            
            for future in as_completed(futures):
                strong_name = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(
                        f"Arrr! [FSM GRID] Error in parallel strong algo evaluation for {strong_name}: {e}",
                        context={"strong_algo": strong_name, "error": str(e)}
                    )
    else:
        # Sequential evaluation (fallback)
        for strong_name, strong_cls in strong_algo_list:
            result = _evaluate_single_strong_algo_worker(
                strong_name, strong_cls, model_path, params,
                train_draws, test_draws, combo_idx, total_combinations, len(strong_algo_list), device
            )
            if result:
                results.append(result)
    
    return results


def _evaluate_single_combination_worker(args, device, enable_parallel_strong, strong_algo_workers):
    """Module-level worker function for evaluating a single combination"""
    combo_idx, params, train_draws, test_draws, total_combinations, strong_algos_count = args
    
    try:
        model_path = str(SEQUENCE_CLASSIFIER_MODEL_DIR / f"sequence_classifier_grid_h{params['hidden_size']}_l{params['num_layers']}_s{params['seq_len']}_lr{params['lr']}_b{params['batch_size']}.pt")
        
        logger.info(
            f"Arrr! [FSM GRID] Processing combination {combo_idx}/{total_combinations}",
            context={
                "params": params,
                "progress": f"{combo_idx}/{total_combinations}",
                "percent_complete": round((combo_idx / total_combinations) * 100, 1)
            }
        )
        
        # Check cache before creating model
        need_train = True
        if os.path.exists(model_path):
            try:
                # Quick validation: try to load state dict
                state_dict = torch.load(model_path, map_location=device)
                # Create model and validate it works
                model = LottoLSTM(
                    num_numbers=LOTTO_NUMBERS_COUNT,
                    seq_len=params['seq_len'],
                    hidden_size=params['hidden_size'],
                    num_layers=params['num_layers']
                )
                model.load_state_dict(state_dict)
                model = model.to(device)
                dummy_input = torch.zeros((1, params['seq_len'], 37)).to(device)
                model.eval()
                with torch.no_grad():
                    _ = model(dummy_input)
                logger.info(f"Arrr! [FSM GRID] Loaded existing model for {params}")
                need_train = False
            except Exception as e:
                logger.warning(f"Arrr! [FSM GRID] Model file mismatch or unusable, will retrain: {e}")
                try:
                    os.remove(model_path)
                except Exception as del_e:
                    logger.error(f"Arrr! [FSM GRID] Failed to delete model file: {model_path}, error: {del_e}")
                need_train = True
        
        # Train model if needed
        if need_train:
            model = LottoLSTM(
                num_numbers=LOTTO_NUMBERS_COUNT,
                seq_len=params['seq_len'],
                hidden_size=params['hidden_size'],
                num_layers=params['num_layers']
            )
            model = _train_model_worker(model, train_draws, params, device)
            # Save model
            torch.save(model.state_dict(), model_path)
            # File sync to ensure data is written to disk
            try:
                with open(model_path, 'rb+') as f:
                    f.flush()
                    os.fsync(f.fileno())
            except Exception as e:
                logger.warning(f"Arrr! [FSM DEBUG] File sync failed for {model_path}: {e}")
            # Integrity check
            try:
                _ = torch.load(model_path, map_location=device)
            except Exception as e:
                logger.error(f"Arrr! [FSM DEBUG] Model integrity check failed for {model_path}: {e}")
        
        # Evaluate all strong algos (in parallel if enabled)
        results = _evaluate_strong_algos_parallel_worker(
            model_path, params, train_draws, test_draws, combo_idx, total_combinations, device, enable_parallel_strong, strong_algo_workers
        )
        
        logger.info(
            f"Arrr! [FSM GRID] Completed all evaluations for combination {combo_idx}/{total_combinations}",
            context={
                "params": params,
                "combo_progress": f"{combo_idx}/{total_combinations}",
                "percent_complete": round((combo_idx / total_combinations) * 100, 1),
                "results_count": len(results)
            }
        )
        
        return results
        
    except Exception as e:
        logger.error(
            f"Arrr! [FSM GRID] Error evaluating combination {combo_idx}: {e}",
            context={"combo_idx": combo_idx, "params": params, "error": str(e)}
        )
        return []

