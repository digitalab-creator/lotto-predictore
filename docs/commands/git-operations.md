# Git Operations 🏴‍☠️

May the Flying Spaghetti Monster guide yer version control! 🍝

## Basic Git Commands

### Commit and Push Changes

**Interactive commit (prompts for message, runs pre-commit checks):**
```bash
source venv/bin/activate && python3 scripts/git_manager.py commit
```

**Commit with message (bypasses prompt):**
```bash
source venv/bin/activate && python3 scripts/git_manager.py commit "fixed some bugswith weekly cron"
```

**Skip pre-commit checks (use sparingly!):**
```bash
source venv/bin/activate && python3 scripts/git_manager.py commit --no-verify
```

### Fetch Latest Commit

**Fetch and reset to latest commit from remote:**
```bash
python3 scripts/git_manager.py fetch
```

### Checkout Specific Commit

**Checkout a specific commit by ID:**
```bash
python3 scripts/git_manager.py checkout <commit_id>
```

**Example:**
```bash
python3 scripts/git_manager.py checkout abc123def456
```

## Environment Setup

**Required environment variables in `.env.development`:**
```bash
GITHUB_REPO_URL=https://github.com/username/repo.git
GIT_AUTHOR_NAME="Yer Pirate Name"
GIT_AUTHOR_EMAIL=pirate@example.com
GIT_BRANCH=main
GITHUB_TOKEN=your_github_personal_access_token
```

## Troubleshooting

**Check if in git repository:**
```bash
python3 scripts/git_manager.py
```

**View git root directory:**
```bash
python3 -c "from scripts.git_manager import find_git_root; print(find_git_root())"
```

**Test repository access:**
```bash
git ls-remote origin
```

## Notes

- Git operations run directly on the host machine, not in Docker
- The git manager script handles authentication automatically using your GitHub token
- It will initialize a git repository if one doesn't exist
- All operations are logged to the logs directory
- Force push is used to ensure remote matches local state
- Commit messages are required for commits
- Pre-commit hooks are run automatically (unless `--no-verify` is used)
- The script automatically switches to the branch specified in `GIT_BRANCH` from `.env.development`

