"""
Real-time WebSocket handler for dashboard updates
"""

import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from backend.core.logging_config import get_logger
from backend.core.mongodb import get_database

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.user_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept WebSocket connection and register user"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        
        logger.info(f"WebSocket connected: user_id={user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"WebSocket disconnected: user_id={user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user's connections"""
        if user_id in self.user_connections:
            disconnected = []
            for websocket in self.user_connections[user_id].copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected.append(websocket)
            
            # Clean up disconnected websockets
            for ws in disconnected:
                self.disconnect(ws, user_id)
    
    async def broadcast(self, message: dict):
        """Send message to all connected users"""
        disconnected = []
        for websocket in self.active_connections.copy():
            try:
                await websocket.send_text(json.dumps(message))
            except:
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            self.active_connections.discard(ws)


# Global connection manager
manager = ConnectionManager()


class DashboardMetrics:
    """Collects and broadcasts real-time dashboard metrics"""
    
    def __init__(self):
        self.metrics_task: asyncio.Task = None
        self.is_running = False
    
    async def start_metrics_collection(self):
        """Start collecting and broadcasting metrics"""
        if self.is_running:
            return
        
        self.is_running = True
        self.metrics_task = asyncio.create_task(self._metrics_loop())
        logger.info("Started dashboard metrics collection")
    
    async def stop_metrics_collection(self):
        """Stop metrics collection"""
        self.is_running = False
        if self.metrics_task:
            self.metrics_task.cancel()
            try:
                await self.metrics_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped dashboard metrics collection")
    
    async def _metrics_loop(self):
        """Main metrics collection loop"""
        while self.is_running:
            try:
                # Collect current metrics
                metrics = await self._collect_metrics()
                
                # Broadcast to all connected clients
                await manager.broadcast({
                    "type": "dashboard_metrics",
                    "data": metrics,
                    "timestamp": metrics["timestamp"]
                })
                
                # Wait 5 seconds before next update
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def _collect_metrics(self) -> Dict:
        """Collect current system metrics"""
        from datetime import datetime
        import psutil
        
        db = get_database()
        
        try:
            # Database metrics
            active_cameras = await db.cameras.count_documents({"status": "active"})
            total_models = await db.models.count_documents({})
            
            # Recent inference jobs (last hour)
            from datetime import timedelta
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_jobs = await db.inference_jobs.count_documents({
                "created_at": {"$gte": one_hour_ago}
            })
            
            # Running inference jobs
            running_jobs = await db.inference_jobs.count_documents({
                "status": "running"
            })
            
            # Recent camera events (last 10 minutes)
            ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
            recent_events = await db.camera_events.count_documents({
                "created_at": {"$gte": ten_minutes_ago}
            })
            
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Model cache metrics (if available)
            try:
                from backend.services.inference.model_cache import get_model_cache
                cache = get_model_cache()
                cache_stats = cache.get_stats()
            except:
                cache_stats = {"cached_models": 0, "hit_rate": 0}
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cameras": {
                    "active": active_cameras,
                    "recent_events": recent_events
                },
                "inference": {
                    "total_models": total_models,
                    "recent_jobs": recent_jobs,
                    "running_jobs": running_jobs,
                    "cache_hit_rate": round(cache_stats.get("hit_rate", 0) * 100, 1)
                },
                "system": {
                    "cpu_percent": round(cpu_percent, 1),
                    "memory_percent": round(memory.percent, 1),
                    "disk_percent": round(disk.percent, 1),
                    "cached_models": cache_stats.get("cached_models", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Failed to collect metrics"
            }


# Global metrics collector
metrics_collector = DashboardMetrics()


async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for dashboard updates"""
    await manager.connect(websocket, user_id)
    
    # Start metrics collection if not already running
    await metrics_collector.start_metrics_collection()
    
    try:
        # Send initial metrics
        metrics = await metrics_collector._collect_metrics()
        await websocket.send_text(json.dumps({
            "type": "initial_metrics",
            "data": metrics
        }))
        
        # Keep connection alive and handle messages
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message.get("type") == "request_metrics":
                metrics = await metrics_collector._collect_metrics()
                await websocket.send_text(json.dumps({
                    "type": "metrics_update",
                    "data": metrics
                }))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)