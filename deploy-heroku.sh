#!/bin/bash
# Heroku Deployment Script for Myanmar Election Visualization

set -e

echo "🚀 Starting Heroku deployment for Myanmar Election Visualization..."

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI is not installed. Please install it first:"
    echo "   https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Check if user is logged in to Heroku
if ! heroku auth:whoami &> /dev/null; then
    echo "❌ Not logged in to Heroku. Please run: heroku login"
    exit 1
fi

# Get app name from user or use default
read -p "Enter Heroku app name (or press Enter for 'myanmar-election-viz-2025'): " APP_NAME
APP_NAME=${APP_NAME:-myanmar-election-viz-2025}

echo "📱 App name: $APP_NAME"

# Check if app already exists
if heroku apps:info $APP_NAME &> /dev/null; then
    echo "✅ App '$APP_NAME' already exists"
    read -p "Do you want to deploy to existing app? (y/N): " DEPLOY_EXISTING
    if [[ ! $DEPLOY_EXISTING =~ ^[Yy]$ ]]; then
        echo "❌ Deployment cancelled"
        exit 1
    fi
else
    echo "🆕 Creating new Heroku app: $APP_NAME"
    heroku create $APP_NAME
    
    echo "🗄️ Adding PostgreSQL addon..."
    heroku addons:create heroku-postgresql:essential-0 --app $APP_NAME
fi

# Set environment variables
echo "⚙️ Setting environment variables..."
heroku config:set ENVIRONMENT=production --app $APP_NAME
heroku config:set DEBUG_MODE=false --app $APP_NAME
heroku config:set ENABLE_CACHING=true --app $APP_NAME
heroku config:set DEFAULT_MAP_PROVIDER=cartodb --app $APP_NAME
heroku config:set STREAMLIT_SERVER_HEADLESS=true --app $APP_NAME
heroku config:set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false --app $APP_NAME

# Add git remote if it doesn't exist
if ! git remote get-url heroku &> /dev/null; then
    echo "🔗 Adding Heroku git remote..."
    heroku git:remote -a $APP_NAME
fi

# Ensure we're on the heroku-deploy branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "heroku-deploy" ]; then
    echo "⚠️  Current branch is '$CURRENT_BRANCH'. Switching to 'heroku-deploy'..."
    git checkout heroku-deploy
fi

# Stage all changes
echo "📝 Staging changes for deployment..."
git add .

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "ℹ️ No changes to commit"
else
    echo "💾 Committing changes..."
    git commit -m "Prepare for Heroku deployment - $(date '+%Y-%m-%d %H:%M:%S')"
fi

# Deploy to Heroku
echo "🚀 Deploying to Heroku..."
git push heroku heroku-deploy:main

# Run database initialization
echo "🗄️ Initializing database..."
heroku run python database/init_heroku_db.py --app $APP_NAME

# Open the app
echo "🎉 Deployment completed successfully!"
echo "🌐 Your app is available at: https://$APP_NAME.herokuapp.com"
echo "📊 Opening app..."
heroku open --app $APP_NAME

echo "✅ Deployment script completed!"
echo ""
echo "📋 Next steps:"
echo "   1. Monitor app logs: heroku logs --tail --app $APP_NAME"
echo "   2. Check database status: heroku pg:info --app $APP_NAME"
echo "   3. Scale dynos if needed: heroku ps:scale web=1 --app $APP_NAME"