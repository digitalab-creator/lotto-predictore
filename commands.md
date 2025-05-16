# Useful Commands for Lotto Predictore ⚓️

## Import Draws

To import draws from the paisapi, run this command:

```sh
docker-compose exec backend python import_draws_paisapi.py
docker-compose run --rm backend python import_draws_magayo.py
docker-compose run --rm backend python scrape_israel_lotto_draw_dates.py
```
docker-compose down
docker-compose up -d
docker-compose exec db psql -U lotto_user -d lotto_db -c "\dt"
docker-compose exec db psql -U lotto_user -d lotto_db -c "SELECT * FROM draws ORDER BY id DESC LIMIT 100;"
docker-compose exec db psql -U lotto_user -d lotto_db -c "SELECT date FROM draws ORDER BY date DESC LIMIT 1;"
May the FSM bless yer draws and yer noodles never be soggy! 