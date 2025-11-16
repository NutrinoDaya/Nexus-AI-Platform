# Nexus AI Platform

A scalable computer vision platform for real-time model inference, video streaming, and production deployment.

## Overview

Nexus AI Platform provides a complete solution for computer vision applications with support for multiple model types including YOLO, classification, segmentation, and custom models. Built with modern technologies and designed for production workloads.

## Features

### Core Capabilities
- **Multi-Model Support**: YOLO v8 detection, segmentation, tracking, and custom models
- **Scalable Processing**: Async queue-based inference engine with priority scheduling
- **Real-Time Streaming**: RTSP camera integration with WebSocket connectivity
- **Modern Interface**: React TypeScript frontend with dark theme support
- **Enterprise Ready**: JWT authentication, role-based access, and comprehensive monitoring

### Backend Services
- FastAPI REST API with OpenAPI documentation
- MongoDB data persistence with Redis caching
- Celery background task processing
- Real-time WebSocket connections
- Health checks and metrics collection

### Frontend Application
- React 18 with TypeScript and Tailwind CSS
- Radix UI components for accessibility
- Real-time dashboard with live metrics
- Camera management interface
- Model inference visualization with canvas rendering

## Screenshots

### Login Interface
<img src="assets/Un4titled.jpg" alt="Login Page" width="600">

*Secure authentication with modern dark theme*

### Dashboard Overview  
<img src="assets/Untitl42ed.png" alt="Main Dashboard" width="600">

*Real-time system monitoring and analytics*

### Camera Management
<img src="assets/hyt4Untitled.png" alt="Camera Interface" width="600">

*Live camera feeds and streaming controls*

### Model Inference
<img src="assets/Unsdatitled.png" alt="Model Management" width="600">

*AI model configuration and inference results*

### System Settings
<img src="assets/Untitledd.jpg" alt="Settings Panel" width="600">

*Comprehensive system configuration*

### Detection Results
<img src="assets/Untitgrled.jpg" alt="Detection Output" width="600">

*Object detection with real-time visualization*

### Analysis Dashboard
<img src="assets/Untitlefdsd.jpg" alt="Analytics View" width="600">

*Advanced analytics and performance metrics*

## Quick Start

### Prerequisites
- Docker and Docker Compose
- 4GB+ RAM recommended
- NVIDIA GPU (optional, for CUDA acceleration)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/NutrinoDaya/Nexus-AI-Platform.git
   cd Nexus-AI-Platform
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start the platform**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## API Usage

### Authentication
```bash
# Register user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "email": "user@example.com", "password": "password"}'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "password"}'
```

### Model Inference
```bash
# Load YOLO model
curl -X POST "http://localhost:8000/api/v1/yolo/models/load" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "model_path=yolov8n.pt" \
  -F "model_id=yolo_nano"

# Run detection
curl -X POST "http://localhost:8000/api/v1/yolo/detect" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@image.jpg" \
  -F "model_id=yolo_nano" \
  -F "confidence_threshold=0.5"

# Async processing for high load
curl -X POST "http://localhost:8000/api/v1/yolo/detect" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@image.jpg" \
  -F "model_id=yolo_nano" \
  -F "async_processing=true" \
  -F "priority=2"
```

### Queue Management
```bash
# Check job status
curl "http://localhost:8000/api/v1/yolo/jobs/{job_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Queue statistics
curl "http://localhost:8000/api/v1/yolo/queue/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Configuration

### Scaling Settings
```bash
INFERENCE_MAX_WORKERS=4      # Number of inference workers
INFERENCE_QUEUE_SIZE=256     # Maximum queue size
INFERENCE_DEVICE=cuda        # Processing device (cuda/cpu)
API_WORKERS=8                # FastAPI worker processes
```

### Performance Optimizations
- Model caching and preloading
- Connection pooling for databases
- Redis caching for frequent queries
- Gzip compression for API responses
- Multi-stage Docker builds

## Development

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
Nexus-AI-Platform/
├── backend/                 # FastAPI application
│   ├── api/                # API routes and endpoints
│   ├── core/               # Configuration and utilities
│   ├── models/             # Database models
│   ├── services/           # Business logic
│   └── tasks/              # Background tasks
├── frontend/               # React TypeScript app
│   ├── src/
│   │   ├── components/     # UI components
│   │   ├── pages/          # Application pages
│   │   └── lib/            # API client and utilities
├── config/                 # Configuration files
├── docs/                   # Documentation
└── scripts/                # Deployment utilities
```

## Technology Stack

**Backend**
- FastAPI (Python web framework)
- Ultralytics YOLO (Computer vision)
- MongoDB (Database)
- Redis (Caching)
- Celery (Task queue)

**Frontend**
- React 18 (UI library)
- TypeScript (Type safety)
- Tailwind CSS (Styling)
- Radix UI (Components)
- Vite (Build tool)

**Infrastructure**
- Docker & Docker Compose
- NGINX (Reverse proxy)
- Prometheus (Metrics)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Create an issue for bug reports or feature requests
- Check the `/docs` directory for detailed documentation
- Review API documentation at `/docs` endpoint when running