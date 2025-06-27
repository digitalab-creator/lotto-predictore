import datetime
import os
import sys
import json
import requests
from pathlib import Path

# Add backend directory to Python path
backend_dir = str(Path(__file__).parent.parent)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from logger import logger

def send_best_model_email():
    """
    Sends an email with the best model tables using the email microservice.
    """
    logger.info("Arrr! Starting best model email sending! Praisin' the FSM!")
    
    try:
        # Read the tables from the temporary file
        temp_file = "/tmp/best_model_tables.json"
        
        if not os.path.exists(temp_file):
            logger.error("Arrr! Best model tables file not found!")
            return {
                "success": False,
                "message": "Best model tables file not found"
            }
        
        with open(temp_file, 'r') as f:
            data = json.load(f)
        
        if not data.get("success", False):
            logger.warning("Arrr! Best model tables generation was not successful!")
            return {
                "success": False,
                "message": data.get("message", "Best model tables generation was not successful")
            }
        
        # Prepare data for email service
        email_data = {
            "date": data["date"],
            "tables": [
                {
                    "numbers": table['numbers'],
                    "strong": table['strong']
                }
                for table in data["tables"]
            ],
            "model_info": data["model_info"]
        }
        
        logger.info(
            "Arrr! Sending best model email",
            context={
                "date": data["date"],
                "num_tables": len(data["tables"]),
                "main_model": data["model_info"]["main_model"],
                "strong_model": data["model_info"]["strong_model"],
                "roi_ratio": data["model_info"]["roi_ratio"]
            }
        )
        
        # Send request to email service
        response = requests.post(
            "http://email-service:8000/send-best-model-tables",
            json=email_data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Email service returned status code {response.status_code}: {response.text}")
        
        # Clean up the temporary file
        try:
            os.remove(temp_file)
            logger.info("Arrr! Temporary file cleaned up successfully!")
        except Exception as e:
            logger.warning(f"Arrr! Could not clean up temporary file: {e}")
        
        logger.info("Arrr! Best model email sent successfully!")
        
        return {
            "success": True,
            "message": "Best model email sent successfully",
            "data": {
                "date": data["date"],
                "num_tables": len(data["tables"]),
                "main_model": data["model_info"]["main_model"],
                "strong_model": data["model_info"]["strong_model"],
                "roi_ratio": data["model_info"]["roi_ratio"]
            }
        }
        
    except requests.exceptions.ConnectionError as e:
        logger.error(
            "Arrr! Connection error calling email service!",
            context={"error": str(e)}
        )
        return {
            "success": False,
            "message": f"Connection error calling email service: {str(e)}"
        }
    except requests.exceptions.Timeout as e:
        logger.error(
            "Arrr! Timeout calling email service!",
            context={"error": str(e)}
        )
        return {
            "success": False,
            "message": f"Timeout calling email service: {str(e)}"
        }
    except Exception as e:
        logger.error(
            "Arrr! Failed to send best model email!",
            context={"error": str(e)}
        )
        return {
            "success": False,
            "message": f"Failed to send best model email: {str(e)}"
        }

if __name__ == "__main__":
    send_best_model_email() 