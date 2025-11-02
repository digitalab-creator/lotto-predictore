#!/usr/bin/env python3
import os
import sys
import subprocess
from typing import Dict, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
import logging
from dataclasses import dataclass
import re
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class GitConfig:
    repo_url: str
    author_name: str
    author_email: str
    branch: str
    github_token: str

def load_config() -> GitConfig:
    """Load configuration from environment variables."""
    # Find git root and load .env.development from there
    git_root = find_git_root()
    env_path = os.path.join(git_root, '.env.development')
    if not os.path.exists(env_path):
        logger.error(f'Could not find .env.development at {env_path}')
        sys.exit(1)
    load_dotenv(env_path)
    
    config = GitConfig(
        repo_url=os.getenv('GITHUB_REPO_URL', ''),
        author_name=os.getenv('GIT_AUTHOR_NAME', 'Anonymous Pirate'),
        author_email=os.getenv('GIT_AUTHOR_EMAIL', 'pirate@example.com'),
        branch=os.getenv('GIT_BRANCH', 'main'),
        github_token=os.getenv('GITHUB_TOKEN', '')
    )
    
    if not config.repo_url:
        logger.error('GITHUB_REPO_URL environment variable is missing')
        sys.exit(1)
    
    if not config.github_token:
        logger.error('GITHUB_TOKEN environment variable is missing')
        logger.error('\nTo fix this:')
        logger.error('1. Create a Personal Access Token (PAT) on GitHub')
        logger.error('2. Add GITHUB_TOKEN=your_token_here to your .env.development file')
        sys.exit(1)
    
    return config

def run_command(command: str, description: str) -> Tuple[str, str]:
    """Execute a git command and return stdout and stderr."""
    logger.info(f"Executing: {description}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stderr:
            logger.warning(f"Command stderr: {result.stderr}")
        
        if result.stdout:
            logger.info(f"Command stdout: {result.stdout.strip()}")
        
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to execute git command: {description}")
        logger.error(f"Error: {e.stderr}")
        raise

def ask_commit_message() -> str:
    """Prompt user for commit message."""
    message = input("📝 Enter commit message: ")
    return message.strip()

def safe_remove_remote(remote_name: str) -> None:
    """Safely remove a git remote if it exists."""
    try:
        subprocess.run(
            f'git remote remove {remote_name}',
            shell=True,
            capture_output=True,
            text=True
        )
    except:
        pass  # Ignore errors if remote doesn't exist

def run_pre_commit_checks():
    """Run pre-commit hooks before committing."""
    try:
        logger.info("Running pre-commit checks...")
        result = subprocess.run(
            'pre-commit run --all-files',
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            logger.info(result.stdout)
        
        # Check if pre-commit is not installed (command not found)
        if result.returncode == 127 or "command not found" in result.stderr.lower():
            logger.warning("Pre-commit not installed - skipping checks")
            logger.info("To install: pip install -r backend/requirements.txt && pre-commit install")
            return True
        
        if result.stderr and "command not found" not in result.stderr.lower():
            logger.error(result.stderr)
            
        if result.returncode != 0:
            logger.error("Pre-commit checks failed!")
            logger.error("Fix the issues above, or use --no-verify to skip")
            return False
        
        logger.info("Pre-commit checks passed!")
        return True
    except FileNotFoundError:
        logger.warning("Pre-commit not found - skipping checks")
        return True
    except Exception as e:
        logger.warning(f"Error running pre-commit: {e} - continuing anyway")
        return True

def commit_and_push():
    """Commit and push changes to GitHub, always using the branch from .env.development"""
    # Load config to get the branch from .env.development
    config = load_config()

    # Check if we're in a git repository
    if not os.path.exists('.git'):
        print("Error: Not a git repository")
        sys.exit(1)

    # Checkout the branch from config (create if missing)
    branches = run_command('git branch', 'List local branches')[0]
    branch_names = [b.strip().replace('* ', '') for b in branches.split('\n') if b.strip()]
    if config.branch not in branch_names:
        print(f"Branch '{config.branch}' does not exist. Creating it...")
        run_command(f'git checkout -b {config.branch}', f'Create and switch to branch {config.branch}')
    else:
        run_command(f'git checkout {config.branch}', f'Switch to branch {config.branch}')

    # Get current branch (should now be config.branch)
    current_branch = run_command('git rev-parse --abbrev-ref HEAD', 'Get current branch')[0].strip()
    print(f"Current branch: {current_branch}")

    # Check if there are any changes
    status = run_command('git status --porcelain', 'Check for changes')[0]
    if not status:
        print("No changes to commit - working tree is clean")
        sys.exit(0)  # Exit with success code since this is a valid state

    # Run pre-commit checks (with --no-verify bypass if needed)
    skip_checks = '--no-verify' in sys.argv
    if not skip_checks:
        if not run_pre_commit_checks():
            sys.exit(1)

    # Add all changes
    print("Adding changes...")
    run_command('git add .', 'Add all changes')

    # Check if there are any staged changes
    staged_changes = run_command('git diff --cached --name-only', 'Check for staged changes')[0]
    if not staged_changes:
        print("No changes were staged for commit")
        sys.exit(0)

    # Get commit message from user or use argument
    if len(sys.argv) > 2 and sys.argv[1] == 'commit':
        # Skip 'commit' argument
        commit_message = ask_commit_message()
    elif len(sys.argv) > 1 and sys.argv[1] not in ['commit', '--no-verify']:
        # Use remaining args as message
        commit_message = ' '.join([arg for arg in sys.argv[1:] if arg != '--no-verify'])
    else:
        # No message provided
        commit_message = ask_commit_message()

    # Commit changes
    print(f"Committing changes with message: {commit_message}")
    run_command(f'git commit -m "{commit_message}"', 'Commit changes')

    # Push changes
    print("Pushing changes...")
    run_command(f'git push origin {config.branch}', 'Push changes')

    print("Changes successfully committed and pushed!")

def fetch_latest_commit(config: GitConfig) -> None:
    """Fetch the latest commit from the remote repository."""
    try:
        # Initialize git if needed
        try:
            run_command('git rev-parse --is-inside-work-tree', 'Check if git repo exists')
        except:
            run_command('git init', 'Initialize git repository')

        # Set up remote with token
        safe_remove_remote('origin')
        
        # Insert token into repo URL
        repo_url_with_token = re.sub(
            r'https://github\.com/',
            f'https://{config.github_token}@github.com/',
            config.repo_url
        )
        
        run_command(f'git remote add origin {repo_url_with_token}', 
                   'Add remote origin')
        run_command('git fetch origin', 
                   'Fetch latest changes')
        run_command(f'git reset --hard origin/{config.branch}', 
                   f'Reset to latest commit')

        logger.info(f"Successfully fetched latest commit")

    except Exception as e:
        logger.error(f"Failed to fetch latest commit: {str(e)}")
        sys.exit(1)

def fetch_specific_commit(config: GitConfig, commit_id: str) -> None:
    """Fetch a specific commit from the remote repository."""
    try:
        # Initialize git if needed
        try:
            run_command('git rev-parse --is-inside-work-tree', 'Check if git repo exists')
        except:
            run_command('git init', 'Initialize git repository')

        # Set up remote with token
        safe_remove_remote('origin')
        
        # Insert token into repo URL
        repo_url_with_token = re.sub(
            r'https://github\.com/',
            f'https://{config.github_token}@github.com/',
            config.repo_url
        )
        
        run_command(f'git remote add origin {repo_url_with_token}', 
                   'Add remote origin')
        run_command('git fetch origin', 
                   'Fetch all changes')

        # Verify commit exists
        try:
            run_command(f'git rev-parse {commit_id}', 
                       'Verify commit exists')
        except subprocess.CalledProcessError:
            logger.error(f"Invalid commit ID: {commit_id}")
            raise ValueError(f"Commit '{commit_id}' not found")

        # Reset to specific commit
        run_command(f'git reset --hard {commit_id}', 
                   f'Reset to commit {commit_id}')

        logger.info(f"Successfully reset to commit {commit_id}")

    except Exception as e:
        logger.error(f"Failed to fetch commit: {str(e)}")
        sys.exit(1)

def find_git_root() -> str:
    """Find the root directory of the git repository (where .git lives)."""
    current = os.path.abspath(os.getcwd())
    while current != os.path.dirname(current):
        if os.path.isdir(os.path.join(current, '.git')):
            return current
        current = os.path.dirname(current)
    raise RuntimeError("Could not find .git directory! Are ye in a git repo, matey?")

def main():
    """Main function to handle command-line arguments."""
    try:
        git_root = find_git_root()
        os.chdir(git_root)
        logger.info(f"Arrr! Changed working directory to git root: {git_root}")

        config = load_config()
        args = sys.argv[1:]
        action = args[0] if args else None
        commit_id = args[1] if len(args) > 1 else None

        if action == 'fetch':
            fetch_latest_commit(config)
        elif action in ['commit', 'commit_and_push']:
            commit_and_push()
        elif action == 'checkout' and commit_id:
            fetch_specific_commit(config, commit_id)
        else:
            logger.error("Invalid command. Use: commit, commit_and_push, fetch, or checkout <commit_id>")
            sys.exit(1)

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        git_root = find_git_root()
        os.chdir(git_root)
        logger.info(f"Arrr! Changed working directory to git root: {git_root}")
    except Exception as e:
        logger.error(f"Failed to find or change to git root: {e}")
        sys.exit(1)

    main() 