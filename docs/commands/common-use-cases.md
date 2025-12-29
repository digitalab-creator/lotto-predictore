# Common Use Cases

## Schedule Weekly Combinations in 2 Minutes

**Quick Command:**
```bash
curl -X POST http://localhost:8002/api/schedule -H "Content-Type: application/json" -d '{"job_name": "generate-weekly-combinations-optimized", "minutes_from_now": 2}'
```

**With Pretty Output:**
```bash
curl -X POST http://localhost:8002/api/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "generate-weekly-combinations-optimized",
    "minutes_from_now": 2
  }' | python3 -m json.tool
```

**Save Job ID for Monitoring:**
```bash
JOB_ID=$(curl -s -X POST http://localhost:8002/api/schedule \
  -H "Content-Type: application/json" \
  -d '{"job_name": "generate-weekly-combinations-optimized", "minutes_from_now": 2}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])")
echo "Job ID: $JOB_ID"
```

## Schedule Job for Tomorrow at 3 AM

```bash
curl -X POST http://localhost:8002/api/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "fetch-draws",
    "scheduled_time": "2025-12-30T03:00:00"
  }'
```

## Check What Jobs Are Available

```bash
curl http://localhost:8002/api/schedule/jobs | python3 -m json.tool
```

## Check All Scheduled Jobs

```bash
curl http://localhost:8002/api/schedule | python3 -m json.tool
```

