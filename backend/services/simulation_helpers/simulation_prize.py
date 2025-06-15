from config import PRIZE_TABLE

def calculate_prize(hits: int, strong_hit: bool) -> float:
    """
    Calculate prize based on number of hits and strong number hit.
    
    Args:
        hits (int): Number of regular number hits
        strong_hit (bool): Whether the strong number was hit
        
    Returns:
        float: Prize amount
    """
    return PRIZE_TABLE.get((hits, strong_hit), 0.0) 