# NexusAIPlatform Analytics Platform

A scalable computer vision platform for real-time inference with YOLO models, video streaming, and production-ready deployment capabilities.

## Overview

NexusAIPlatform is a production-ready computer vision platform that provides:

- **YOLO Model Support**: Complete support for YOLOv8 detection, segmentation, and tracking
- **Scalable Inference**: Async queue-based processing with concurrent request handling
- **Real-time Streaming**: RTSP camera integration with WebSocket streams
- **Modern Architecture**: FastAPI backend with React TypeScript frontend
- **Production Ready**: Docker deployment with monitoring and authentication

## Key Features

### Backend Services
- [DONE] FastAPI-based REST API with OpenAPI documentation
- [DONE] JWT + API key authentication with role-based access control
- [DONE] YOLO model management (load, unload, inference)
- [DONE] Scalable inference queue with priority handling
- [DONE] Real-time camera streaming with RTSP support
- [DONE] MongoDB integration for data persistence
- [DONE] Redis caching and session management
- [DONE] Celery background task processing
- [DONE] Comprehensive logging and monitoring

### Frontend Application
- [DONE] React TypeScript SPA with Tailwind CSS
- [DONE] Modern UI components with Radix UI
- [DONE] Real-time dashboard with WebSocket integration
- [DONE] YOLO model interface with canvas visualization
- [DONE] Camera management and streaming interface
- [DONE] Authentication and user management
- [DONE] Dark theme support

### Infrastructure
- [DONE] Docker containerization with multi-stage builds
- [DONE] Docker Compose orchestration
- [DONE] Production-ready configuration management
- [DONE] Health checks and graceful shutdown
- [DONE] Performance optimizations

## Quick Start

### Prerequisites
- Docker and Docker Compose
- NVIDIA GPU (optional, for CUDA acceleration)
- 4GB+ RAM recommended

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/NexusAIPlatform.git
   cd NexusAIPlatform
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the platform**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Development Setup

For development without Docker:

1. **Backend setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Frontend setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## API Usage

### Authentication
```bash
# Register a new user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "email": "user@example.com", "password": "password"}'

# Login to get access token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "password"}'
```

### YOLO Inference
```bash
# Load a YOLO model
curl -X POST "http://localhost:8000/api/v1/yolo/models/load" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "model_path=yolov8n.pt" \
  -F "model_id=yolo_v8_nano"

# Run detection on an image
curl -X POST "http://localhost:8000/api/v1/yolo/detect" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@image.jpg" \
  -F "model_id=yolo_v8_nano" \
  -F "confidence_threshold=0.5"

# Async processing for high-load scenarios
curl -X POST "http://localhost:8000/api/v1/yolo/detect" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@image.jpg" \
  -F "model_id=yolo_v8_nano" \
  -F "async_processing=true" \
  -F "priority=2"
```

### Queue Management
```bash
# Check job status
curl "http://localhost:8000/api/v1/yolo/jobs/{job_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get queue statistics
curl "http://localhost:8000/api/v1/yolo/queue/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Scalability Features

### Concurrent Processing
- **Async Queue System**: Handles multiple inference requests concurrently
- **Priority Processing**: High-priority requests processed first
- **Thread Pool**: CPU-intensive inference in separate thread pool
- **Resource Management**: Configurable worker limits and queue sizes

### Configuration
```bash
# Environment variables for scaling
INFERENCE_MAX_WORKERS=4          # Number of inference workers
INFERENCE_QUEUE_SIZE=256         # Maximum queue size
INFERENCE_DEVICE=cuda            # cuda or cpu
API_WORKERS=8                    # FastAPI worker processes
```

### Performance Optimizations
- Model caching and warming
- Connection pooling for databases
- Redis caching for frequent queries
- Gzip compression for API responses
- Optimized Docker images with multi-stage builds

## Project Structure

```
NexusAIPlatform/
├── backend/                 # FastAPI backend application
│   ├── api/                # API routes and endpoints
│   ├── core/               # Core configuration and utilities
│   ├── models/             # Database models and schemas
│   ├── services/           # Business logic and services
│   └── tasks/              # Background tasks (Celery)
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Application pages
│   │   ├── lib/            # API client and utilities
│   │   └── hooks/          # Custom React hooks
├── config/                 # Configuration files
├── docs/                   # Documentation
├── scripts/                # Deployment and utility scripts
├── docker-compose.yml      # Development orchestration
└── Dockerfile.*           # Container definitions
```

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **Ultralytics YOLO**: Computer vision models
- **MongoDB**: Document database
- **Redis**: Caching and session store
- **Celery**: Background task processing
- **Pydantic**: Data validation and serialization

### Frontend
- **React 18**: Modern React with hooks
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Radix UI**: Accessible component primitives
- **React Query**: Server state management
- **Vite**: Fast build tool and dev server

### Infrastructure
- **Docker**: Containerization
- **NGINX**: Reverse proxy and static serving
- **PostgreSQL**: Optional relational database
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the documentation in `/docs`
- Review the API documentation at `/docs` endpoint

## Roadmap

- [ ] TensorRT optimization for NVIDIA GPUs
- [ ] Model training pipeline integration  
- [ ] Advanced analytics dashboard
- [ ] Kubernetes deployment manifests
- [ ] Edge deployment support
- [ ] Multi-model ensemble inference