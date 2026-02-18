# Lotto Predictor API Commands

Praisin' the FSM! 🍝⚓

## Documentation Structure

This commands documentation has been split into focused sections for easier navigation:

- **[Quick Start](quick-start.md)** - Get started quickly with scheduling and monitoring weekly jobs
- **[Scheduling API](scheduling-api.md)** - Complete API reference for the cron job scheduling service
- **[Common Use Cases](common-use-cases.md)** - Ready-to-use commands for common scenarios
- **[Monitoring](monitoring.md)** - Comprehensive monitoring commands and workflows
- **[Stop Processes](stop-processes.md)** - Commands to stop running weekly cron jobs and processes
- **[Git Operations](git-operations.md)** - Git manager script commands for version control
- **[Reference](reference.md)** - Notes, error handling, and related endpoints

---

## Quick Links

### Most Common Tasks

1. **Schedule Weekly Job in 2 Minutes**
   ```bash
   curl -X POST http://localhost:8002/api/schedule \
     -H "Content-Type: application/json" \
     -d '{"job_name": "generate-weekly-combinations-optimized", "minutes_from_now": 2}'
   ```

2. **Monitor Job Status**
   ```bash
   docker stats --no-stream lotto-predictore_backend_1
   ```

3. **Check Available Jobs**
   ```bash
   curl http://localhost:8002/api/schedule/jobs | python3 -m json.tool
   ```

See [Quick Start](quick-start.md) for detailed instructions.

