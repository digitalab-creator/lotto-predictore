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

There is no CI workflow. After `origin/dev` contains the commit, stop. Do not watch Deploy.

Retry at most 5 times.
