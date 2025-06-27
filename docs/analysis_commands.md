# Analysis & Development Commands Guide ⚓️

May the Flying Spaghetti Monster bless yer predictions and models! 🍝

## Predictions & API

### API Endpoints
```sh
# Generate combinations using best performing algorithm
curl http://localhost:8000/generate-combinations

# Run simulation
curl -G 'http://localhost:8000/simulate' \
  --data-urlencode 'train_start=2024-01-01' \
  --data-urlencode 'train_end=2024-05-01' \
  --data-urlencode 'test_count=4' \
  --data-urlencode 'top_n=3' | jq .

# Get simulation table
curl -G 'http://localhost:8000/simulate/table' \
  --data-urlencode 'test_count=100' \
  --data-urlencode 'top_n=6'

# Run specific algorithm simulation
curl -G 'http://localhost:8000/simulate/table' \
  --data-urlencode 'test_count=12' \
  --data-urlencode 'top_n=6' \
  --data-urlencode 'algorithms=sequence_lstm_classifier_position_gridsearch'

# Run random pool simulation
curl -G 'http://localhost:8000/simulate/table' \
  --data-urlencode 'test_count=12' \
  --data-urlencode 'top_n=3' \
  --data-urlencode 'algorithms=random_from_top15_pool'
```

## Development

### Model Training
```sh
# Run LSTM grid search
docker-compose -f ~/lotto-predictore/docker-compose.yml run --rm backend bash -c "cd /app && python3 -m scripts.grid_search_lstm"

# Run grid search in background
docker-compose -f ~/lotto-predictore/docker-compose.yml run -d --name grid_search backend bash -c "cd /app && python3 -m scripts.grid_search_lstm"

# Monitor grid search logs
docker logs -f grid_search

# Stop grid search
docker stop grid_search
docker rm grid_search

# Run stock grid search POC
docker-compose run --rm backend python scripts/stock_gridsearch_poc.py
```

## Analysis & Queries

### ROI Analysis
```sql
-- ROI by model and parameters (ticket-level data, cost = ₪3.10)
SELECT
  p.model_id,
  p.main_model_params::text AS main_model_params_text,
  p.strong_model_params::text AS strong_model_params_text,
  ROUND(SUM(d.prize)::numeric / NULLIF(COUNT(d.id) * 3.10, 0)::numeric - 1, 4) AS total_roi,
  COUNT(DISTINCT p.id) AS num_prediction_runs,
  COUNT(d.id) AS num_tickets,
  ROUND((COUNT(d.id) * 3.10)::numeric, 2) AS total_cost,
  ROUND(SUM(d.prize)::numeric, 2) AS total_prize
FROM
  prediction_details d
JOIN
  predictions p ON p.id = d.prediction_id
GROUP BY
  p.model_id, p.main_model_params::text, p.strong_model_params::text
ORDER BY
  total_roi DESC;

-- Find specific model predictions
SELECT *
FROM predictions
WHERE main_model_params::text = '{"seq_len": 10, "model_version": "sequence_lstm_classifier_gridsearch", "top_n": 6, "num_for_analysis": 8, "num_to_recommend": 8}'
  AND strong_model_params::text = '{"strong_algo": "random"}';
```

### Regex Patterns
```sh
# Find positive ROI values
'roi':\s*(?!-)\d+(\.\d+)?

# Find negative ROI values
'roi':\s*-\d+(\.\d+)?
``` 