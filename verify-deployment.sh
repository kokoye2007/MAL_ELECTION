#!/bin/bash
# Deployment Verification Script

echo "🔍 Verifying Heroku deployment readiness..."

# Check if we're on the correct branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "heroku-deploy" ]; then
    echo "⚠️  Warning: Currently on '$CURRENT_BRANCH' branch, not 'heroku-deploy'"
    echo "   Run: git checkout heroku-deploy"
else
    echo "✅ On correct branch: heroku-deploy"
fi

# Check if essential files exist
echo ""
echo "📁 Checking essential deployment files..."

files=(
    "Procfile"
    "runtime.txt" 
    "app.json"
    "requirements.txt"
    ".streamlit/config.toml"
    "database/init_heroku_db.py"
    "src/app_enhanced.py"
    "src/database.py"
    "src/languages.json"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ Missing: $file"
    fi
done

# Check if git is clean
echo ""
echo "📝 Checking git status..."
if git diff --quiet && git diff --staged --quiet; then
    echo "✅ Git working tree is clean"
else
    echo "⚠️  Warning: Uncommitted changes detected"
fi

# Check last commit
echo ""
echo "📊 Latest commit:"
git log --oneline -1

# Check file sizes (Heroku has limits)
echo ""
echo "📦 Checking repository size..."
REPO_SIZE=$(du -sh .git | cut -f1)
echo "Repository size: $REPO_SIZE"

if [ -d "2020" ]; then
    DOC_SIZE=$(du -sh 2020 | cut -f1)
    echo "Historical documents size: $DOC_SIZE"
fi

# Check Heroku CLI
echo ""
echo "🔧 Checking Heroku CLI..."
if command -v heroku &> /dev/null; then
    echo "✅ Heroku CLI installed: $(heroku --version)"
    
    if heroku auth:whoami &> /dev/null; then
        echo "✅ Logged in to Heroku as: $(heroku auth:whoami)"
    else
        echo "❌ Not logged in to Heroku"
        echo "   Run: heroku login"
    fi
else
    echo "❌ Heroku CLI not found"
    echo "   Install from: https://devcenter.heroku.com/articles/heroku-cli"
fi

echo ""
echo "🎯 Next Steps:"
if ! heroku auth:whoami &> /dev/null; then
    echo "1. Login to Heroku: heroku login"
    echo "2. Run deployment: ./deploy-heroku.sh"
else
    echo "1. Run deployment: ./deploy-heroku.sh"
    echo "2. Or follow manual steps in README-HEROKU.md"
fi

echo ""
echo "🌐 After deployment, your app will be available at:"
echo "   https://your-app-name.herokuapp.com"