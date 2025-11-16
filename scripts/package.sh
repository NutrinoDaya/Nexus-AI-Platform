#!/bin/bash
# NexusAIPlatform Docker Image Packaging Script
# Builds and packages Docker images for distribution

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

VERSION="${1:-latest}"
REGISTRY="${2:-}"

echo "======================================"
echo "NexusAIPlatform Docker Packaging"
echo "======================================"
echo "Version: $VERSION"
if [ ! -z "$REGISTRY" ]; then
    echo "Registry: $REGISTRY"
fi
echo ""

# Build images
echo "[1/5] Building backend image..."
docker build -f infra/docker/Dockerfile.backend -t NexusAIPlatform-backend:$VERSION .

echo ""
echo "[2/5] Building frontend image..."
docker build -f infra/docker/Dockerfile.frontend -t NexusAIPlatform-frontend:$VERSION ./frontend

echo ""
echo "[3/5] Creating image archives..."
mkdir -p ./dist

docker save NexusAIPlatform-backend:$VERSION | gzip > ./dist/NexusAIPlatform-backend-$VERSION.tar.gz
docker save NexusAIPlatform-frontend:$VERSION | gzip > ./dist/NexusAIPlatform-frontend-$VERSION.tar.gz

echo ""
echo "[4/5] Generating deployment package..."
mkdir -p ./dist/deploy-$VERSION
cp docker-compose.yml ./dist/deploy-$VERSION/
cp -r config ./dist/deploy-$VERSION/
cp -r scripts ./dist/deploy-$VERSION/
cp README.md ./dist/deploy-$VERSION/
cp QUICK_START.md ./dist/deploy-$VERSION/

# Create load script
cat > ./dist/deploy-$VERSION/load-images.sh << 'EOF'
#!/bin/bash
echo "Loading NexusAIPlatform Docker images..."
docker load < NexusAIPlatform-backend-*.tar.gz
docker load < NexusAIPlatform-frontend-*.tar.gz
echo "Images loaded successfully!"
EOF
chmod +x ./dist/deploy-$VERSION/load-images.sh

cat > ./dist/deploy-$VERSION/load-images.bat << 'EOF'
@echo off
echo Loading NexusAIPlatform Docker images...
docker load -i NexusAIPlatform-backend-*.tar.gz
docker load -i NexusAIPlatform-frontend-*.tar.gz
echo Images loaded successfully!
EOF

cd ./dist
tar -czf NexusAIPlatform-deploy-$VERSION.tar.gz deploy-$VERSION/
cd ..

echo ""
echo "[5/5] Pushing to registry (if specified)..."
if [ ! -z "$REGISTRY" ]; then
    docker tag NexusAIPlatform-backend:$VERSION $REGISTRY/NexusAIPlatform-backend:$VERSION
    docker tag NexusAIPlatform-frontend:$VERSION $REGISTRY/NexusAIPlatform-frontend:$VERSION
    
    echo "Pushing backend..."
    docker push $REGISTRY/NexusAIPlatform-backend:$VERSION
    
    echo "Pushing frontend..."
    docker push $REGISTRY/NexusAIPlatform-frontend:$VERSION
    
    echo "Tagged and pushed to $REGISTRY"
else
    echo "Skipping registry push (no registry specified)"
fi

echo ""
echo "======================================"
echo "Packaging Complete!"
echo "======================================"
echo ""
echo "Generated files:"
echo "  - dist/NexusAIPlatform-backend-$VERSION.tar.gz"
echo "  - dist/NexusAIPlatform-frontend-$VERSION.tar.gz"
echo "  - dist/NexusAIPlatform-deploy-$VERSION.tar.gz"
echo ""
echo "To deploy on another machine:"
echo "  1. Copy NexusAIPlatform-deploy-$VERSION.tar.gz to target machine"
echo "  2. Extract: tar -xzf NexusAIPlatform-deploy-$VERSION.tar.gz"
echo "  3. Load images: cd deploy-$VERSION && ./load-images.sh"
echo "  4. Deploy: ./scripts/deploy.sh"
echo ""

# Show image sizes
echo "Image sizes:"
ls -lh ./dist/*.tar.gz
echo ""
