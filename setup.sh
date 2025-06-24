#!/bin/bash

echo "🚀 Setting up Meeting Assistant..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+ first."
    exit 1
fi

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "⚠️  Redis is not installed. Please install Redis first."
    echo "   On macOS: brew install redis"
    echo "   On Ubuntu: sudo apt-get install redis-server"
    echo "   On Windows: Download from https://redis.io/download"
fi

echo "📦 Installing dependencies..."
npm run install:all

echo "🔧 Setting up environment files..."

# Create backend .env if it doesn't exist
if [ ! -f "backend/.env" ]; then
    echo "📝 Creating backend .env file..."
    cat > backend/.env << EOF
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here

# Google Service Account (for Drive API)
GOOGLE_APPLICATION_CREDENTIALS=path_to_service_account.json

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# Redis
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_BASE_URL=http://localhost:8000

# Security
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF
    echo "✅ Created backend/.env - Please update with your actual credentials"
fi

# Create frontend .env.local if it doesn't exist
if [ ! -f "frontend/.env.local" ]; then
    echo "📝 Creating frontend .env.local file..."
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local
    echo "✅ Created frontend/.env.local"
fi

echo "🗄️  Setting up database..."
npm run setup

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Update backend/.env with your Google Cloud credentials"
echo "2. Start Redis server: redis-server"
echo "3. Start Celery worker: cd backend && celery -A workers.task worker --loglevel=info"
echo "4. Start the application: npm run dev"
echo ""
echo "🌐 The application will be available at:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo ""
echo "📚 For more information, see README.md" 