from sqlalchemy.orm import Session
from sqlalchemy import text
from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from utils.model_utils import normalize_model_name
from logger import logger

def get_model_prediction_details_count(db: Session):
    """Get the current count of prediction details for each model combination"""
    query = """
    SELECT 
        mm.name AS main_model_name,
        sm.name AS strong_model_name,
        COUNT(pd.id) AS prediction_details_count
    FROM models mm
    CROSS JOIN models sm
    LEFT JOIN predictions p ON p.model_id = mm.id AND p.strong_model_id = sm.id
    LEFT JOIN prediction_details pd ON pd.prediction_id = p.id
    WHERE mm.type = 'main' AND sm.type = 'strong'
    GROUP BY mm.name, sm.name
    ORDER BY prediction_details_count ASC
    """
    
    result = db.execute(text(query))
    # Create a dictionary with key format: "main_model_name_strong_model_name"
    counts = {}
    for row in result:
        key = f"{row.main_model_name}_{row.strong_model_name}"
        counts[key] = row.prediction_details_count
    return counts

def get_balanced_algorithm_list(db: Session, target_details_per_model: int = 100):
    """Get a balanced list of algorithms to run, prioritizing those with fewer prediction details"""
    current_counts = get_model_prediction_details_count(db)
    
    # Create reverse lookup: normalized model name -> count
    normalized_counts = {}
    for key, count in current_counts.items():
        # Split the key "main_model_name_strong_model_name" into parts
        parts = key.split('_strong_')
        if len(parts) == 2:
            main_model_name = parts[0]  # "main_sequence_lstm_classifier_h128_l2"
            strong_model_name = f"strong_{parts[1]}"  # "strong_most_common"
            
            # Normalize to get algorithm registry keys
            main_algo = normalize_model_name(main_model_name)  # "sequence_lstm_classifier_h128_l2"
            strong_algo = normalize_model_name(strong_model_name)  # "most_common"
            
            # Create key using algorithm registry names
            algo_key = f"{main_algo}_{strong_algo}"
            normalized_counts[algo_key] = count
    
    # Get all algorithm combinations
    all_combinations = []
    
    for main_algo in ALGORITHM_REGISTRY.keys():
        for strong_algo in STRONG_NUMBER_REGISTRY.keys():
            # Create key using algorithm registry names
            key = f"{main_algo}_{strong_algo}"
            current_count = normalized_counts.get(key, 0)
            
            combo = {
                'main_algo': main_algo,
                'strong_algo': strong_algo,
                'current_details': current_count,
                'priority_score': current_count  # Use current_count directly for sorting
            }
            
            all_combinations.append(combo)
    
    # Debug logging
    logger.info(
        "Arrr! Algorithm selection debug info",
        context={
            "total_combinations": len(all_combinations),
            "grid_search_combinations": len([c for c in all_combinations if 'gridsearch' in c['main_algo'].lower()]),
            "sample_algorithms": [{"algo": c['main_algo'], "details": c['current_details']} for c in all_combinations[:5]]
        }
    )
    
    # Sort all algorithms by prediction details (lowest first)
    all_combinations.sort(key=lambda x: x['current_details'])
    
    # Take top 10 algorithms with least prediction details (this will include grid search if it has 0 details)
    top_10_combinations = all_combinations[:10]
    
    return top_10_combinations 