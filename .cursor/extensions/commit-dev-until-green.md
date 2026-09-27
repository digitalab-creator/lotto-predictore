# commit-dev-until-green extension (lotto)

This file is the command list. Push `HEAD` to branch `dev`. Do not push or merge to `main`. Do not run Deploy. `/ship` updates the live site. Do not start `backend-debug`.

Root: `/opt/apps/lotto-predictore`.

Never stage `.env`, `backend/.env`, `email-service/.env`, `gcp-credentials.json`, `logs/`, or `tmp/`. Leave `docs/` as they are.

Load the server GitHub token. Do not print it, and do not copy it into this app's `.env`.

```bash
source /opt/apps/n8n/scripts/load-github-token.sh
load_server_github_token
```

Check out `dev` (create it from the current commit if needed). Commit the allowlisted files. Push with `HEAD:dev` only.

After push, watch GitHub Actions workflow **CI** for this commit on `dev` until success or failure. Ignore workflows whose name matches deploy. Retry at most 5 times on CI failure.

```bash
REPO="digitalab-creator/lotto-predictore"
SHA=$(git rev-parse HEAD)
TO="${COMMIT_DEV_WATCH_TIMEOUT_SECS:-1800}"
DEADLINE=$((SECONDS + TO))
watch_exit=3
while [ $SECONDS -lt $DEADLINE ]; do
  RUN_JSON=$(gh run list --repo "$REPO" --branch dev --commit "$SHA" --workflow CI --limit 5 --json databaseId,status,conclusion,name 2>/dev/null || echo '[]')
  set +e
  python3 - "$RUN_JSON" <<'PY'
import json, sys
runs = json.loads(sys.argv[1] if len(sys.argv) > 1 else "[]")
if not runs:
    raise SystemExit(3)
if any(r.get("status") != "completed" for r in runs):
    raise SystemExit(3)
bad = [r for r in runs if r.get("conclusion") not in ("success", "skipped")]
raise SystemExit(2 if bad else 0)
PY
  watch_exit=$?
  set -e
  if [ "$watch_exit" = "0" ] || [ "$watch_exit" = "2" ]; then
    break
  fi
  sleep 20
done
```

- **0** — CI green → stop.
- **2** — read failed logs once, fix, recommit, retry.
- **3** — pending → keep polling until deadline.

Retry at most 5 times.
