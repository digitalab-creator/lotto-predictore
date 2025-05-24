import numpy as np

def calculate_roi_with_tax(prizes, total_cost):
    """
    Calculate ROI with tax applied to prizes over 30,000.
    Args:
        prizes (list of float): List of individual prize amounts.
        total_cost (float): Total cost spent.
    Returns:
        float: ROI value.
    """
    taxed_prizes = []
    for prize in prizes:
        if prize > 30000:
            taxed_prizes.append(prize * 0.65)  # 35% tax
        else:
            taxed_prizes.append(prize)
    all_prizes = sum(taxed_prizes)
    if total_cost == 0:
        return 0
    return (all_prizes - total_cost) / total_cost

def to_native(obj):
    """Recursively convert numpy types to native Python types."""
    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_native(x) for x in obj]
    elif isinstance(obj, np.generic):
        return obj.item()
    else:
        return obj 