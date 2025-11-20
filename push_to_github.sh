#!/bin/bash
# GitHub Upload Script for RDBMS-to-Graph Migration Project
# 
# Usage: 
#   1. First, create a new repository on GitHub: https://github.com/new
#   2. Then run this script with your GitHub username:
#      ./push_to_github.sh YOUR_USERNAME
#
#   Or with the full repository URL:
#      ./push_to_github.sh https://github.com/username/repo.git

echo "═══════════════════════════════════════════════════════════════════"
echo "    🚀 GitHub Upload Script"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Check if argument is provided
if [ -z "$1" ]; then
    echo "❌ Error: GitHub username or repository URL required"
    echo ""
    echo "Usage:"
    echo "  Option 1: ./push_to_github.sh YOUR_USERNAME"
    echo "  Option 2: ./push_to_github.sh https://github.com/username/repo.git"
    echo ""
    exit 1
fi

# Determine if input is URL or username
if [[ "$1" == https://* ]] || [[ "$1" == git@* ]]; then
    REPO_URL="$1"
    echo "📍 Using repository URL: $REPO_URL"
else
    USERNAME="$1"
    REPO_NAME="rdbms-to-graph-migration"
    REPO_URL="https://github.com/${USERNAME}/${REPO_NAME}.git"
    echo "📍 GitHub Username: $USERNAME"
    echo "📍 Repository URL: $REPO_URL"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "⚠️  IMPORTANT: Make sure you've created the repository on GitHub first!"
echo "   Go to: https://github.com/new"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
read -p "Have you created the repository on GitHub? (y/n): " confirm

if [[ $confirm != [yY] && $confirm != [yY][eE][sS] ]]; then
    echo ""
    echo "Please create the repository first, then run this script again."
    exit 0
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "📤 Step 1: Adding remote repository..."
echo "═══════════════════════════════════════════════════════════════════"

# Check if remote already exists
if git remote | grep -q "^origin$"; then
    echo "⚠️  Remote 'origin' already exists. Updating URL..."
    git remote set-url origin "$REPO_URL"
else
    git remote add origin "$REPO_URL"
fi

echo "✅ Remote added: origin -> $REPO_URL"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "📤 Step 2: Renaming branch to 'main'..."
echo "═══════════════════════════════════════════════════════════════════"

git branch -M main
echo "✅ Branch renamed to 'main'"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "📤 Step 3: Pushing to GitHub..."
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "This may take a moment depending on your connection..."
echo ""

# Push to GitHub
if git push -u origin main; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════════"
    echo "    ✅ SUCCESS! Your project is now on GitHub!"
    echo "═══════════════════════════════════════════════════════════════════"
    echo ""
    echo "📊 Project Statistics:"
    echo "   • Total files: ~45 files"
    echo "   • Source code: 4,549 lines"
    echo "   • Documentation: 1,680 lines"
    echo "   • Commit: feat: Implement S→C→T architecture"
    echo ""
    echo "🌐 View your repository at:"
    if [[ "$REPO_URL" == https://* ]]; then
        VIEW_URL="${REPO_URL%.git}"
        echo "   $VIEW_URL"
    else
        echo "   Check your GitHub profile"
    fi
    echo ""
    echo "🎉 Your RDBMS-to-Graph migration project is now live!"
    echo "═══════════════════════════════════════════════════════════════════"
else
    echo ""
    echo "═══════════════════════════════════════════════════════════════════"
    echo "    ❌ Push Failed"
    echo "═══════════════════════════════════════════════════════════════════"
    echo ""
    echo "Common issues:"
    echo "1. Repository doesn't exist on GitHub"
    echo "   → Create it at: https://github.com/new"
    echo ""
    echo "2. Authentication failed"
    echo "   → You may need to enter your GitHub credentials"
    echo "   → Or set up SSH keys: https://docs.github.com/en/authentication"
    echo ""
    echo "3. Wrong repository URL"
    echo "   → Check the URL on your GitHub repository page"
    echo ""
    exit 1
fi
