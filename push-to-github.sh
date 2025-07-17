#!/bin/bash

echo "Pushing Compliance Agent to GitHub..."
echo "============================================"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "Error: Run this script from the compliance-agent directory"
    exit 1
fi

# Add the remote repository
echo "Adding remote repository..."
git remote add origin https://github.com/satv0878/compliance-agent.git

# Check if remote was added successfully
if [ $? -eq 0 ]; then
    echo "✓ Remote repository added successfully"
else
    echo "Remote repository might already exist, continuing..."
fi

# Push to GitHub
echo "Pushing to GitHub..."
git push -u origin master

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 SUCCESS! Compliance Agent has been pushed to GitHub!"
    echo ""
    echo "Repository URL: https://github.com/satv0878/compliance-agent"
    echo ""
    echo "Next steps:"
    echo "1. Visit the repository on GitHub"
    echo "2. Set up branch protection rules (Settings > Branches)"
    echo "3. Configure GitHub Actions (optional)"
    echo "4. Add collaborators if needed"
    echo ""
    echo "To clone on other machines:"
    echo "git clone https://github.com/satv0878/compliance-agent.git"
    echo "cd compliance-agent"
    echo "make setup"
    echo "make up"
else
    echo ""
    echo "❌ Push failed. Please check:"
    echo "1. Repository exists on GitHub"
    echo "2. You have write permissions"
    echo "3. You're authenticated (git config --global user.name/email)"
    echo ""
    echo "If the repository doesn't exist, create it first:"
    echo "https://github.com/new"
fi