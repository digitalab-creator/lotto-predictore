# commit-dev-until-green extension (lotto)

This file is the command list. Push branch `main` only. Remote `dev` is unused. Do not merge to a second branch. Do not run Deploy. Do not start `backend-debug`.

Root: `/opt/apps/lotto-predictore`.

Never stage `.env`, `backend/.env`, `email-service/.env`, `gcp-credentials.json`, `logs/`, or `tmp/`. Leave `docs/` as they are.

If `GH_TOKEN` is unset, stop and name that missing key. Do not print tokens.

There is no CI workflow. After a successful push to `main`, stop. Do not watch Deploy.

Retry at most 5 times.
