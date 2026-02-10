#!/bin/bash
# Quick deployment script dla Hetzner CX23

set -e

echo "🚀 RAG API Deployment Script"
echo "============================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root (sudo ./deploy.sh)"
  exit 1
fi

# 1. Update system
echo "📦 Updating system..."
apt update && apt upgrade -y

# 2. Install Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh

    apt install -y docker-compose-plugin
else
    echo "✅ Docker already installed"
fi

# 3. Install utilities
echo "🔧 Installing utilities..."
apt install -y curl git vim htop ufw

# 4. Configure firewall
echo "🔒 Configuring firewall..."
ufw allow 22/tcp
ufw allow 8000/tcp
echo "y" | ufw enable

# 5. Create app directory
echo "📁 Creating app directory..."
mkdir -p /opt/rag-api
cd /opt/rag-api

# 6. Check if .env exists
if [ ! -f "deployment/.env" ]; then
    echo "⚠️  .env file not found!"
    echo "Please create deployment/.env with:"
    echo "  QDRANT_URL=your_url"
    echo "  QDRANT_API_KEY=your_key"
    exit 1
fi

# 7. Build and start
echo "🏗️  Building Docker image..."
cd deployment
docker compose build

echo "🚀 Starting services..."
docker compose up -d

# 8. Wait for health check
echo "⏳ Waiting for API to start..."
sleep 10

# 9. Test health endpoint
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API is healthy!"
    docker compose logs --tail=20
else
    echo "❌ API health check failed"
    docker compose logs
    exit 1
fi

echo ""
echo "✅ Deployment complete!"
echo "============================"
echo "API endpoint: http://$(hostname -I | awk '{print $1}'):8000"
echo "Health check: http://$(hostname -I | awk '{print $1}'):8000/health"
echo "API docs: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo "View logs: docker compose logs -f"
echo "Restart: docker compose restart"
echo "Stop: docker compose down"
