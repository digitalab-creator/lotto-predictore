import sys
import os
import datetime
import requests
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from logger import logger

def main():
    """
    Generate weekly combinations by calling the /generate-combinations endpoint.
    This ensures consistency between manual runs and automated cron jobs.
    """
    logger.info("Arrr! Starting weekly combination generation via API endpoint, praisin' the FSM!")
    
    try:
        # Call the backend API endpoint
        backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        url = f"{backend_url}/generate-combinations"
        
        logger.info(f"Arrr! Calling API endpoint: {url}")
        
        response = requests.get(url)
        response.raise_for_status()
        
        result = response.json()
        
        logger.info(
            f"Arrr! Successfully generated {result.get('num_test_draws', 'unknown')} combinations!",
            context={
                "algorithm": result.get("algorithm"),
                "strong_algorithm": result.get("strong_algorithm"),
                "roi": result.get("roi"),
                "num_combinations": len(result.get("combinations", [])),
                "prediction_id": result.get("prediction_id")
            }
        )
        
        logger.info(f"Arrr! Generated combinations using {result.get('algorithm')} + {result.get('strong_algorithm')} with ROI: {result.get('roi'):.4f}")
        
    except requests.exceptions.ConnectionError as e:
        logger.error(
            "Arrr! Connection error calling API endpoint!",
            context={"error": str(e), "url": url}
        )
        raise
    except requests.exceptions.Timeout as e:
        logger.error(
            "Arrr! Timeout calling API endpoint!",
            context={"error": str(e), "url": url}
        )
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(
            "Arrr! HTTP error calling API endpoint!",
            context={"error": str(e), "url": url, "status_code": e.response.status_code}
        )
        raise
    except Exception as e:
        logger.error(
            "Arrr! Error in weekly combination generation!",
            context={"error": str(e)}
        )
        raise

if __name__ == "__main__":
    main() 