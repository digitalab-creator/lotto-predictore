#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

# Set log directory to local logs folder
os.environ['LOG_DIR'] = str(project_root / 'logs')

import subprocess
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv
from dataclasses import dataclass
import re
from datetime import datetime
from shared.logging_service import LoggingService

# Initialize logger
logger = LoggingService('git_manager')

@dataclass
class GitConfig:
    repo_url: str
    author_name: str
    author_email: str
    branch: str
    github_token: str

def load_config() -> GitConfig:
    """Load configuration from environment variables."""
    load_dotenv('.env.development')
    
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
        logger.error('GITHUB_TOKEN environment variable is missing', {
            'help': 'To fix this:\n1. Create a Personal Access Token (PAT) on GitHub\n2. Add GITHUB_TOKEN=your_token_here to your .env file'
        })
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
        logger.error(f"Failed to execute git command: {description}", {
            'error': e.stderr,
            'command': command
        })
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
    except Exception as e:
        logger.debug(f"Failed to remove remote {remote_name}", {'error': str(e)})
        pass  # Ignore errors if remote doesn't exist

def commit_all_files(config: GitConfig) -> None:
    """Commit and push all files to GitHub."""
    try:
        # Initialize git if needed
        try:
            run_command('git rev-parse --is-inside-work-tree', 'Check if git repo exists')
        except:
            run_command('git init', 'Initialize git repository')

        # Check if there are any changes
        status = run_command('git status --porcelain', 'Check for changes')[0]
        if not status:
            logger.info("No changes to commit - working tree is clean")
            sys.exit(0)

        # Get commit message
        commit_message = ask_commit_message()
        if not commit_message:
            logger.error("Empty commit message provided")
            sys.exit(1)

        # Set git config
        run_command(f'git config user.name "{config.author_name}"', 
                   'Set git author name')
        run_command(f'git config user.email "{config.author_email}"', 
                   'Set git author email')

        # Add and commit files
        run_command('git add -A', 'Stage all files')
        
        # Check if there are any staged changes
        staged_changes = run_command('git diff --cached --name-only', 'Check for staged changes')[0]
        if not staged_changes:
            logger.info("No changes were staged for commit")
            sys.exit(0)
            
        run_command(f'git commit -m "{commit_message}"', 
                   'Commit files')

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
        run_command(f'git branch -M {config.branch}', 
                   f'Set branch to {config.branch}')
        
        # Test repository access
        try:
            run_command('git ls-remote origin', 'Test repository access')
        except subprocess.CalledProcessError:
            logger.error("Failed to access repository - check your token and repo URL", {
                'repo_url': config.repo_url
            })
            raise

        run_command(f'git push -u origin {config.branch} --force', 
                   'Push files to GitHub')

        logger.info(f"Successfully pushed to {config.branch}", {
            'branch': config.branch,
            'repo': config.repo_url
        })

    except Exception as e:
        logger.error(f"Failed to commit and push: {str(e)}", {
            'error': str(e),
            'repo': config.repo_url,
            'branch': config.branch
        })
        sys.exit(1)

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

        logger.info("Successfully fetched latest commit", {
            'branch': config.branch,
            'repo': config.repo_url
        })

    except Exception as e:
        logger.error(f"Failed to fetch latest commit: {str(e)}", {
            'error': str(e),
            'repo': config.repo_url,
            'branch': config.branch
        })
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
            logger.error(f"Invalid commit ID: {commit_id}", {
                'commit_id': commit_id,
                'repo': config.repo_url
            })
            raise ValueError(f"Commit '{commit_id}' not found")

        # Reset to specific commit
        run_command(f'git reset --hard {commit_id}', 
                   f'Reset to commit {commit_id}')

        logger.info(f"Successfully reset to commit {commit_id}", {
            'commit_id': commit_id,
            'repo': config.repo_url,
            'branch': config.branch
        })

    except Exception as e:
        logger.error(f"Failed to fetch commit: {str(e)}", {
            'error': str(e),
            'commit_id': commit_id,
            'repo': config.repo_url
        })
        sys.exit(1)

def commit_and_push():
    """Commit and push changes to GitHub"""
    # Check if we're in a git repository
    if not os.path.exists('.git'):
        logger.error("Not a git repository")
        sys.exit(1)

    # Get current branch
    current_branch = run_command('git rev-parse --abbrev-ref HEAD', 'Get current branch')[0].strip()
    logger.info(f"Current branch: {current_branch}", {'branch': current_branch})

    # Check if there are any changes
    status = run_command('git status --porcelain', 'Check for changes')[0]
    if not status:
        logger.info("No changes to commit - working tree is clean")
        sys.exit(0)  # Exit with success code since this is a valid state

    # Add all changes
    logger.info("Adding changes...")
    run_command('git add .', 'Add all changes')

    # Check if there are any staged changes
    staged_changes = run_command('git diff --cached --name-only', 'Check for staged changes')[0]
    if not staged_changes:
        logger.info("No changes were staged for commit")
        sys.exit(0)

    # Get commit message from command line or use default
    commit_message = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else f"Update {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Commit changes
    logger.info(f"Committing changes with message: {commit_message}", {
        'message': commit_message,
        'branch': current_branch
    })
    run_command(f'git commit -m "{commit_message}"', 'Commit changes')

    # Push changes
    logger.info("Pushing changes...", {'branch': current_branch})
    run_command(f'git push origin {current_branch}', 'Push changes')

    logger.info("Changes successfully committed and pushed!", {
        'branch': current_branch,
        'message': commit_message
    })

def find_git_root() -> str:
    """Find the root directory of the git repository (where .git lives)."""
    current = os.path.abspath(os.getcwd())
    while current != os.path.dirname(current):
        if os.path.isdir(os.path.join(current, '.git')):
            return current
        current = os.path.dirname(current)
    logger.error("Could not find .git directory! Are ye in a git repo, matey?")
    raise RuntimeError("Could not find .git directory! Are ye in a git repo, matey?")

def main():
    """Main function to handle command-line arguments."""
    try:
        git_root = find_git_root()
        os.chdir(git_root)
        logger.info(f"Arrr! Changed working directory to git root: {git_root}", {
            'git_root': git_root
        })

        config = load_config()
        args = sys.argv[1:]
        action = args[0] if args else None
        commit_id = args[1] if len(args) > 1 else None

        if action == 'fetch':
            fetch_latest_commit(config)
        elif action == 'commit':
            commit_all_files(config)
        elif action == 'checkout' and commit_id:
            fetch_specific_commit(config, commit_id)
        else:
            logger.error("Invalid command. Use: commit, fetch, or checkout <commit_id>", {
                'action': action,
                'commit_id': commit_id
            })
            sys.exit(1)

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", {
            'error': str(e),
            'action': action if 'action' in locals() else None,
            'commit_id': commit_id if 'commit_id' in locals() else None
        })
        sys.exit(1)

if __name__ == '__main__':
    try:
        git_root = find_git_root()
        os.chdir(git_root)
        logger.info(f"Arrr! Changed working directory to git root: {git_root}", {
            'git_root': git_root
        })
    except Exception as e:
        logger.error(f"Failed to find or change to git root: {e}", {
            'error': str(e),
            'current_dir': os.getcwd()
        })
        sys.exit(1)

    main() 