# Запустить Postgres
docker run -d \
  --name mb_event_bot_postgres \
  -e POSTGRES_USER=mb_event_bot \
  -e POSTGRES_PASSWORD=mb_1337 \
  -e POSTGRES_DB=mb_event_bot_db \
  -p 5432:5432 \
  postgres:latest

# Запустить Redis
docker run -d \
  --name mb_event_bot_redis \
  -p 6380:6379 \
  redis:latest


