# Useful Commands for Lotto Predictore ⚓️

## Import Draws

To import draws from the paisapi, run this command:

```sh
docker-compose exec backend python import_draws_paisapi.py
```
docker-compose down
docker-compose up -d

docker-compose exec db psql -U lotto_user -d lotto_db -c "SELECT * FROM draws ORDER BY id LIMIT 10;"
May the FSM bless yer draws and yer noodles never be soggy! 