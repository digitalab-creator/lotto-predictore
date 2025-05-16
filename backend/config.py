# config.py
# All static (but changeable) settings for the lottery predictor backend
# Praise the FSM for single source of truth!

# Cost of a single ticket (per table)
TICKET_COST_PER_TABLE = 2.80  # Change as needed


# Number of combinations to use for analysis/simulation (e.g., in ROI calculations)
NUM_COMBINATIONS_FOR_ANALYSIS = 8

# Number of combinations to recommend to the user for the next draw
NUM_COMBINATIONS_TO_RECOMMEND = 8

# Prize table (average, adjust as needed)
# Key: (hits, strong_hit) -> value: average prize in NIS
PRIZE_TABLE = {
    (6, True): 6_000_000,   # 6 correct + strong
    (6, False): 250_000,    # 6 correct, no strong
    (5, True): 20_000,      # 5 correct + strong
    (5, False): 1_500,      # 5 correct, no strong
    (4, True): 500,         # 4 correct + strong
    (4, False): 60,         # 4 correct, no strong
    (3, True): 30,          # 3 correct + strong
    (3, False): 0,          # 3 correct, no strong
    (2, True): 10,          # 2 correct + strong
    (2, False): 0,          # 2 correct, no strong
}

# Add more config values as needed, matey! 