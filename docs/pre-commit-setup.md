# 🏴‍☠️ Pre-commit Setup Guide

Praise the FSM for automated code quality checks!

## What is Pre-commit?

Pre-commit hooks run automatically before each git commit to ensure code quality. Think of it as your first mate checkin' yer code before it goes to sea!

## Initial Setup

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Install pre-commit hooks (run once)
pre-commit install

# That's it! Now pre-commit will run on every commit
```

## What Gets Checked?

### 🔍 General File Checks
- **Trailing whitespace** - Removes extra spaces
- **End of file** - Ensures files end with newline
- **YAML validation** - Checks all YAML files
- **Large files** - Flags files > 1MB
- **Merge conflicts** - Catches leftover conflict markers
- **Private keys** - Detects accidentally committed secrets

### 🐍 Python Code Quality
- **Black** - Auto-formats code (120 char line length)
- **Ruff** - Fast linter (replaces flake8)
- **isort** - Organizes imports
- **Bandit** - Security vulnerability scanner

## Running Manually

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files only (default)
pre-commit run

# Run specific hook
pre-commit run black
pre-commit run ruff
```

## Skipping Hooks (In Case of Emergency!)

```bash
# Skip all hooks for this commit
git commit --no-verify -m "Emergency fix!"

# Use sparingly - arrr, ye've been warned!
```

## Updating Hooks

```bash
# Update to latest versions
pre-commit autoupdate
```

## Configuration

Edit `.pre-commit-config.yaml` to:
- Add new hooks
- Change configuration
- Exclude specific paths
- Adjust line lengths

## Troubleshooting

### Hook fails but code looks fine
```bash
# Try auto-fixing first
pre-commit run ruff --all-files

# Black auto-fixes most issues
pre-commit run black --all-files
```

### Pre-commit not running
```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install
```

### Install errors
```bash
# Clear cache and reinstall
pre-commit clean
pre-commit install
```

## Tips

1. **Run `pre-commit run --all-files`** before your first commit to fix everything at once
2. **Let Black auto-format** - it's opinionated but consistent
3. **Ruff is fast** - runs in milliseconds even on large codebases
4. **Check before push** - don't wait for CI to catch issues

Arrr! Keep yer code clean and ye'll avoid walkin' the plank! 🏴‍☠️

