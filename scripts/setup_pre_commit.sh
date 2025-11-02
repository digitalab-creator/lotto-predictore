#!/bin/bash
# 🏴‍☠️ Pre-commit Setup Script
# Praise the FSM for automated code quality!

set -e

echo "🏴‍☠️  Setting up pre-commit hooks..."

# Check if we're in venv
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: Not in virtual environment"
    echo "Activate venv first: source venv/bin/activate"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r backend/requirements.txt

# Install pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
pre-commit install

# Run on all files to catch existing issues
echo "🔍 Running pre-commit on all files..."
pre-commit run --all-files || true

echo ""
echo "✅ Pre-commit setup complete!"
echo ""
echo "Next time you commit, pre-commit will run automatically."
echo "To skip: git commit --no-verify -m 'message'"

