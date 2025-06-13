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
    if hits not in PRIZE_TABLE:
        return 0.0
        
    prize = PRIZE_TABLE[hits]
    if strong_hit:
        prize *= 2
        
    return prize 