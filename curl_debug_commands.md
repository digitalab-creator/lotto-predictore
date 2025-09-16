# 🏴‍☠️ Curl Debug Commands for Long-Running Endpoints

## The Problem
The `/cron/generate-weekly-combinations` endpoint takes a very long time because it:
- Runs multiple machine learning algorithms
- Tests each algorithm combination for ROI
- Can take 10+ minutes or even hours

## Debugging Solutions

### 1. **FAST Test Endpoint** ⚡ (RECOMMENDED)
Use the new fast endpoint that only tests 2 algorithms instead of all:

```bash
# This should complete in under 2 minutes
docker-compose exec backend curl -X POST http://localhost:8000/cron/generate-weekly-combinations-fast
```

### 2. **Timeout with Progress Monitoring** ⏰
```bash
# Run with 5-minute timeout and detailed stats
timeout 300 docker-compose exec backend curl -X POST http://localhost:8000/cron/generate-weekly-combinations \
  --max-time 300 \
  --connect-timeout 30 \
  -w "\n\n📊 Curl Stats:\nTime Total: %{time_total}s\nTime Connect: %{time_connect}s\nTime Start Transfer: %{time_starttransfer}s\nHTTP Code: %{http_code}\n" \
  2>&1 | tee /tmp/curl_debug.log
```

### 3. **Real-time Log Monitoring** 📊
```bash
# Monitor logs while running curl
./monitor_logs.sh
```

### 4. **Verbose Curl with Timing** 🔍
```bash
# Detailed curl output with timing
docker-compose exec backend curl -X POST http://localhost:8000/cron/generate-weekly-combinations \
  -v \
  --max-time 600 \
  -w "\n\n📊 Detailed Stats:\nTotal Time: %{time_total}s\nConnect Time: %{time_connect}s\nStart Transfer: %{time_starttransfer}s\nPre Transfer: %{time_pretransfer}s\nHTTP Code: %{http_code}\nSize Download: %{size_download} bytes\nSpeed Download: %{speed_download} bytes/s\n"
```

### 5. **Background Execution with Log Monitoring** 🚀
```bash
# Run in background and monitor logs
docker-compose exec backend curl -X POST http://localhost:8000/cron/generate-weekly-combinations &
CURL_PID=$!

# Monitor logs in real-time
docker-compose logs -f backend | grep -E "(algorithm|ROI|error|completed)" &

# Wait for curl to complete
wait $CURL_PID
```

### 6. **Check Current Status** 📈
```bash
# Check if the endpoint is currently running
docker-compose exec backend curl -X GET http://localhost:8000/health

# Check recent cron jobs
docker-compose exec backend curl -X GET http://localhost:8000/cron/status
```

## Best Practices for Debugging

1. **Start with the FAST endpoint** - Use `/cron/generate-weekly-combinations-fast` first
2. **Monitor logs in real-time** - Use `./monitor_logs.sh` to see progress
3. **Set reasonable timeouts** - Don't wait hours, use 5-10 minute timeouts
4. **Check the logs** - Look at `/home/orshv/lotto-predictore/logs/backend_service/backend_service.log`
5. **Use background execution** - Run curl in background while monitoring logs

## Understanding the Process

The endpoint does these steps:
1. **Load draws** (~1-2 seconds)
2. **Get balanced algorithms** (~1-2 seconds) 
3. **Run algorithm evaluation** (THIS IS THE SLOW PART - can take 10+ minutes)
   - Tests each algorithm combination
   - Runs simulation engine
   - Calculates ROI for each
4. **Generate final combinations** (~1-2 seconds)
5. **Save to database** (~1-2 seconds)

The FAST endpoint skips step 3 and only tests 2 algorithms instead of 10+.
