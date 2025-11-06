#!/bin/bash
# GitHub Setup Script
# This script helps you push the project to GitHub

echo "======================================================"
echo "  RDBMS-to-Graph Migration Engine - GitHub Setup"
echo "======================================================"
echo ""

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "Error: Git repository not initialized!"
    echo "Run: git init"
    exit 1
fi

echo "Step 1: Create a new repository on GitHub"
echo "-------------------------------------------"
echo "Go to: https://github.com/new"
echo ""
echo "Repository settings:"
echo "  - Name: rdbms-to-graph-migration"
echo "  - Description: Advanced RDBMS-to-Graph migration engine implementing SCT methodology"
echo "  - Visibility: Public (or Private)"
echo "  - DO NOT initialize with README, .gitignore, or license (we already have them)"
echo ""
read -p "Press Enter after you've created the repository on GitHub..."

echo ""
echo "Step 2: Get your repository URL"
echo "--------------------------------"
echo "After creating the repo, GitHub will show you the URL."
echo "It looks like: https://github.com/YOUR_USERNAME/rdbms-to-graph-migration.git"
echo ""
read -p "Enter your GitHub repository URL: " REPO_URL

if [ -z "$REPO_URL" ]; then
    echo "Error: Repository URL cannot be empty!"
    exit 1
fi

echo ""
echo "Step 3: Setting up remote and pushing..."
echo "-----------------------------------------"

# Add remote
git remote add origin "$REPO_URL"

# Rename branch to main (if using master)
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" == "master" ]; then
    echo "Renaming branch 'master' to 'main'..."
    git branch -M main
fi

# Push to GitHub
echo "Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================"
    echo "  ✓ Successfully pushed to GitHub!"
    echo "======================================================"
    echo ""
    echo "Your repository is now available at:"
    echo "$REPO_URL"
    echo ""
    echo "Next steps:"
    echo "  1. Visit your repository on GitHub"
    echo "  2. Add topics/tags for discoverability"
    echo "  3. Enable GitHub Pages (optional)"
    echo "  4. Set up GitHub Actions for CI/CD (optional)"
    echo ""
else
    echo ""
    echo "======================================================"
    echo "  ✗ Push failed!"
    echo "======================================================"
    echo ""
    echo "Common issues:"
    echo "  1. Authentication failed: Set up SSH key or use Personal Access Token"
    echo "  2. Repository doesn't exist: Double-check the URL"
    echo "  3. Permission denied: Make sure you own the repository"
    echo ""
    echo "Manual push commands:"
    echo "  git remote add origin $REPO_URL"
    echo "  git branch -M main"
    echo "  git push -u origin main"
    echo ""
fi
