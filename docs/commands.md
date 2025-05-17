# Useful Commands for Lotto Predictore ⚓️
start
./scripts/up_with_cron.sh   
./scripts/cleanup.sh   

docker-compose logs backend | tail -30
## Import Draws

To import draws from the paisapi, run this command:

```sh
docker-compose exec backend python import_draws_paisapi.py
docker-compose run --rm backend python import_draws_magayo.py
docker-compose run --rm backend python scrape_israel_lotto_draw_dates.py

curl -G 'http://localhost:8000/simulate' --data-urlencode 'train_start=2024-01-01' --data-urlencode 'train_end=2024-05-01' --data-urlencode 'test_count=4' --data-urlencode 'top_n=3' | jq .
```
curl -G 'http://localhost:8000/simulate/table' \
  --data-urlencode 'train_start=1980-01-01' \
  --data-urlencode 'train_end=2025-04-01' \
  --data-urlencode 'test_count=12' \
  --data-urlencode 'top_n=3'

curl http://localhost:8000/recommend

curl -G 'http://localhost:8000/simulate/table' \
  --data-urlencode 'train_start=1980-01-01' \
  --data-urlencode 'train_end=2025-04-01' \
  --data-urlencode 'test_count=12' \
  --data-urlencode 'top_n=3' \
  --data-urlencode 'algorithms=sequence_lstm_classifier_gridsearch'

  curl -G 'http://localhost:8000/simulate/table' \
  --data-urlencode 'train_start=1980-01-01' \
  --data-urlencode 'train_end=2025-04-01' \
  --data-urlencode 'test_count=12' \
  --data-urlencode 'top_n=3' \
  --data-urlencode 'algorithms=random_from_top15_pool'


docker-compose -f ~/lotto-predictore/docker-compose.yml run --rm backend bash -c "cd /app && python3 -m scripts.grid_search_lstm"

   docker-compose -f ~/lotto-predictore/docker-compose.yml run -d --name grid_search backend bash -c "cd /app && python3 -m scripts.grid_search_lstm"

      docker logs -f grid_search

         docker stop grid_search

   docker rm grid_search

docker-compose exec db psql -U lotto_user -d lotto_db -c "\dt"
docker-compose exec db psql -U lotto_user -d lotto_db -c "SELECT * FROM draws ORDER BY id DESC LIMIT 100;"
docker-compose exec db psql -U lotto_user -d lotto_db -c "SELECT date FROM draws ORDER BY date DESC LIMIT 1;"
May the FSM bless yer draws and yer noodles never be soggy! 



docker-compose exec backend alembic downgrade 2f0e51283d21
docker-compose exec backend alembic upgrade head