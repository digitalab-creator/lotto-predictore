# ship extension (lotto)

This file is the command list. Kit skill `ship` prints `workflows.ship.runner.command`, then follows these steps. Do not invent a second sequence. Do not dispatch during profile setup.

Root: `/opt/apps/lotto-predictore`. Repo: `digitalab-creator/lotto-predictore`. Branch: `main`. Remote `dev` is unused by this workflow.

## Before dispatch

1. Dirty tracked files block the release. Commit them with `/commit-dev-until-green` first.
2. Freeze `FROZEN_SHA` from `origin/main`.
3. The `digitalab-prod` runner is registered on `digitalab-new-design` only. Confirm it is online for this repo before the first real dispatch. If it cannot accept this repo, the job stays queued.

## Dispatch

Consent is the slash command. Do not ask for a second typed confirmation.

```bash
gh workflow run Deploy --repo digitalab-creator/lotto-predictore --ref main \
  -f sha="$FROZEN_SHA" \
  -f confirm="DEPLOY $FROZEN_SHA TO PRODUCTION" \
  -f mode=deploy
```

Watch workflow `Deploy`. Retry at most 5 times. The workflow:

- Checks the SHA out in the live tree.
- Does not touch the Postgres volume.
- Does not start `backend-debug`.
- Rebuilds only when a Dockerfile or dependency file in that SHA changed. Backend code is bind-mounted, so a source-only SHA needs no image rebuild.

## After CI is green

Smoke `http://127.0.0.1:8000/`.

Rollback reads `previous_sha` from `tmp/deploy/latest-release.json` and runs the same workflow with `mode=rollback` and `-f previous_sha`.

Leave `docs/` as they are. Never print `.env` or tokens.
