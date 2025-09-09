#!/bin/zsh

docker run -d --name redis \
  -p 6379:6379 \
  -v ~/redis-data:/data \
  -v $(pwd)/redis.conf:/Users/artyomzobkov/cbc_crew_selection_bot/app/infrastructure/cache/redis.conf \
  redis:7-alpine redis-server /Users/artyomzobkov/cbc_crew_selection_bot/app/infrastructure/cache/redis.conf