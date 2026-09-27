# ship extension (lotto)

**Business outcome:** apply a **frozen, CI-green** `origin/dev` commit to the live lotto stack on this server (checkout + optional image rebuild + health check).

**This command is not `/commit-dev-until-green`.** Ship never commits WIP and never watches **CI** (CI must already be green). Ship dispatches **Deploy** and watches that workflow.

| | `/commit-dev-until-green` | `/ship` |
| --- | --- | --- |
| Push to `origin/dev` | yes | no |
| Watch **CI** | yes | no |
| Watch **Deploy** | no | yes |
| CI green required | on the commit you push | on `FROZEN_SHA` before dispatch |

Kit skill `ship` prints `workflows.ship.runner.command`, then follows these steps. Do not invent a second sequence. Do not dispatch during profile setup.

Root: `/opt/apps/lotto-predictore`. Repo: `digitalab-creator/lotto-predictore`. Integration branch: `dev`. `/ship` updates the live containers. It does not merge `dev` into `main`.

## Before dispatch

1. Dirty tracked files block the release. Commit them with `/commit-dev-until-green` first.
2. `git fetch origin dev` and freeze `FROZEN_SHA` from `origin/dev` (not unpushed local-only commits).
3. Preflight (from `project.yaml`): `bash scripts/gha/verify-ci-green-for-sha.sh "$FROZEN_SHA"`. If this fails, fix CI on `dev` or ship an older green SHA — do not deploy red CI.
4. The `digitalab-prod` runner must accept this repo. If the Deploy job stays queued, fix runner labels before retrying.

## Dispatch

Consent is the slash command. Do not ask for a second typed confirmation.

```bash
gh workflow run Deploy --repo digitalab-creator/lotto-predictore --ref dev \
  -f sha="$FROZEN_SHA" \
  -f confirm="DEPLOY $FROZEN_SHA TO PRODUCTION" \
  -f mode=deploy
```

Watch workflow **Deploy** for that run (not CI). Retry at most 5 times. The workflow:

- Checks the SHA out in the live tree.
- Does not touch the Postgres volume.
- Does not start `backend-debug`.
- Rebuilds only when a Dockerfile or dependency file in that SHA changed. Backend code is bind-mounted, so a source-only SHA needs no image rebuild.

```bash
REPO="digitalab-creator/lotto-predictore"
# After dispatch, poll Deploy for FROZEN_SHA until completed (success or failure).
gh run list --repo "$REPO" --workflow Deploy --branch dev --limit 5
```

## After Deploy succeeds

Smoke `http://127.0.0.1:8000/` (health should return 200).

Rollback reads `previous_sha` from `tmp/deploy/latest-release.json` and runs the same workflow with `mode=rollback` and `-f previous_sha`.

Leave `docs/` as they are. Never print `.env` or tokens.
