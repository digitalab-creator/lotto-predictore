from config import PRIZE_TABLE

def calculate_prize(hits, strong_hit):
    # Use the prize table from config, fallback to 0 if not found
    return PRIZE_TABLE.get((hits, strong_hit), 0) 