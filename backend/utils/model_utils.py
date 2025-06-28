"""
Utility functions for model operations.
"""

def normalize_model_name(name: str) -> str:
    """
    Normalize model names by removing prefixes.
    
    Args:
        name (str): Model name that may have 'main_' or 'strong_' prefix
        
    Returns:
        str: Normalized model name without prefix
    """
    if name.startswith('main_'):
        return name[len('main_'):]
    if name.startswith('strong_'):
        return name[len('strong_'):]
    return name


def denormalize_model_name(name: str, model_type: str) -> str:
    """
    Add prefix to model name based on type.
    
    Args:
        name (str): Model name without prefix
        model_type (str): Type of model ('main' or 'strong')
        
    Returns:
        str: Model name with appropriate prefix
    """
    if model_type == 'main':
        return f'main_{name}'
    elif model_type == 'strong':
        return f'strong_{name}'
    return name 