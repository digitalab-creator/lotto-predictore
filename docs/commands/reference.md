# Reference

## Notes

- Jobs are scheduled using the `schedule` library and run within the cron service
- Scheduled jobs are stored in memory (will be lost on service restart)
- The cron service must be running and healthy for scheduling to work
- Jobs execute by calling the backend API endpoints
- All times are in local server time (not timezone-aware)

---

## Error Handling

If a job name is invalid:
```json
{
  "detail": "Unknown job name: invalid-job. Available jobs: ['generate-weekly-combinations-optimized', ...]"
}
```

If scheduling parameters are missing:
```json
{
  "detail": "Either scheduled_time or minutes_from_now must be provided"
}
```

---

## Related Endpoints

- **Scheduler Status**: `GET /api/scheduler-status` - Check all scheduled jobs (including system jobs)
- **Health Check**: `GET /health` - Check cron service health

