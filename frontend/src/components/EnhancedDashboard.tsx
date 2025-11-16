import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { modelsApi, camerasApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Brain, Zap, Video, TrendingUp, Activity, Clock, Eye } from 'lucide-react';

interface RealtimeMetrics {
  timestamp: string;
  cameras: {
    active: number;
    recent_events: number;
  };
  inference: {
    total_models: number;
    recent_jobs: number;
    running_jobs: number;
    cache_hit_rate: number;
  };
  system: {
    cpu_percent: number;
    memory_percent: number;
    disk_percent: number;
    cached_models: number;
  };
}

interface WebSocketMessage {
  type: string;
  data?: RealtimeMetrics;
  timestamp?: string;
}

// Custom hook for WebSocket connection
const useWebSocket = (url: string, userId: string) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [connectionState, setConnectionState] = useState<'connecting' | 'open' | 'closed'>('connecting');

  useEffect(() => {
    const wsUrl = `${url}?user_id=${userId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setConnectionState('open');
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        setLastMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      setConnectionState('closed');
      console.log('WebSocket disconnected');
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionState('closed');
    };

    setSocket(ws);

    // Cleanup on unmount
    return () => {
      ws.close();
    };
  }, [url, userId]);

  // Ping/pong for keepalive
  useEffect(() => {
    if (socket && connectionState === 'open') {
      const interval = setInterval(() => {
        socket.send(JSON.stringify({ type: 'ping' }));
      }, 30000); // Ping every 30 seconds

      return () => clearInterval(interval);
    }
  }, [socket, connectionState]);

  return { lastMessage, connectionState, socket };
};

// Performance indicator component
const PerformanceIndicator = ({ value, label, threshold = 80, unit = '%' }: {
  value: number;
  label: string;
  threshold?: number;
  unit?: string;
}) => {
  const getColor = (val: number) => {
    if (val < threshold * 0.7) return 'text-green-600';
    if (val < threshold) return 'text-yellow-600';
    return 'text-red-600';
  };



  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className={`text-sm font-bold ${getColor(value)}`}>
          {value.toFixed(1)}{unit}
        </span>
      </div>
      <Progress 
        value={value} 
        className="h-2"
        // Custom progress color would need additional styling
      />
    </div>
  );
};

// Live camera grid component
const LiveCameraGrid = () => {
  const { data: camerasData } = useQuery({
    queryKey: ['cameras'],
    queryFn: () => camerasApi.list({ limit: 8 }),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  const cameras = camerasData?.items || [];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {cameras.slice(0, 8).map((camera: any) => (
        <Card key={camera.id} className="overflow-hidden">
          <div className="aspect-video bg-gray-900 relative">
            {/* Video thumbnail placeholder */}
            <div className="w-full h-full flex items-center justify-center">
              <Video className="w-8 h-8 text-gray-500" />
            </div>
            
            {/* Status indicator */}
            <div className="absolute top-2 right-2">
              <Badge 
                variant={camera.status === 'active' ? 'default' : 'secondary'}
                className={camera.status === 'active' ? 'bg-green-500' : 'bg-gray-500'}
              >
                {camera.status === 'active' ? 'LIVE' : 'OFF'}
              </Badge>
            </div>
            
            {/* Motion indicator */}
            {camera.motion_detected && (
              <div className="absolute bottom-2 left-2">
                <Badge variant="destructive" className="animate-pulse">
                  <Activity className="w-3 h-3 mr-1" />
                  Motion
                </Badge>
              </div>
            )}
          </div>
          
          <div className="p-2">
            <h4 className="font-semibold text-sm truncate">{camera.name}</h4>
            <p className="text-xs text-gray-500 truncate">{camera.location}</p>
          </div>
        </Card>
      ))}
    </div>
  );
};

export default function EnhancedDashboard() {
  const [realtimeMetrics, setRealtimeMetrics] = useState<RealtimeMetrics | null>(null);
  
  // WebSocket connection for real-time updates
  const { lastMessage, connectionState } = useWebSocket(
    'ws://localhost:8000/ws/dashboard',
    'current-user-id' // TODO: Get from auth store
  );

  // Update metrics from WebSocket
  useEffect(() => {
    if (lastMessage && (lastMessage.type === 'dashboard_metrics' || lastMessage.type === 'initial_metrics')) {
      setRealtimeMetrics(lastMessage.data || null);
    }
  }, [lastMessage]);

  // Fallback API queries for when WebSocket is not available
  const { data: modelsData } = useQuery({
    queryKey: ['models'],
    queryFn: () => modelsApi.list({ page: 1, limit: 5 }),
    enabled: !realtimeMetrics, // Only query if no realtime data
  });



  // Determine data source (realtime or API)
  const metrics = realtimeMetrics || {
    cameras: { active: 0, recent_events: 0 },
    inference: { total_models: modelsData?.total || 0, recent_jobs: 0, running_jobs: 0, cache_hit_rate: 0 },
    system: { cpu_percent: 0, memory_percent: 0, disk_percent: 0, cached_models: 0 }
  };

  const stats = [
    {
      name: 'Active Cameras',
      value: metrics.cameras.active,
      icon: Video,
      color: 'bg-blue-500',
      trend: `${metrics.cameras.recent_events} events (10m)`,
    },
    {
      name: 'AI Models',
      value: metrics.inference.total_models,
      icon: Brain,
      color: 'bg-purple-500',
      trend: `${metrics.system.cached_models} cached`,
    },
    {
      name: 'Inference Jobs',
      value: metrics.inference.running_jobs,
      icon: Zap,
      color: 'bg-green-500',
      trend: `${metrics.inference.recent_jobs} recent (1h)`,
    },
    {
      name: 'Cache Hit Rate',
      value: `${metrics.inference.cache_hit_rate}%`,
      icon: TrendingUp,
      color: 'bg-orange-500',
      trend: 'Performance metric',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header with connection status */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Dashboard</h2>
          <p className="text-gray-600 mt-1">Real-time NexusAIPlatform Analytics</p>
        </div>
        
        {/* Connection indicator */}
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${
            connectionState === 'open' ? 'bg-green-500 animate-pulse' : 
            connectionState === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'
          }`} />
          <span className="text-sm text-gray-600">
            {connectionState === 'open' ? 'Live' : 
             connectionState === 'connecting' ? 'Connecting' : 'Offline'}
          </span>
          {realtimeMetrics && (
            <span className="text-xs text-gray-500">
              Updated: {new Date(realtimeMetrics.timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* Stats Grid with real-time updates */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.name} className="transition-all duration-200 hover:shadow-lg">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">{stat.value}</p>
                    <p className="text-xs text-gray-500 mt-1">{stat.trend}</p>
                  </div>
                  <div className={`${stat.color} p-3 rounded-lg`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* System Performance Monitoring */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Activity className="w-5 h-5 mr-2" />
              System Performance
            </CardTitle>
            <CardDescription>
              Real-time system resource utilization
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <PerformanceIndicator 
              value={metrics.system.cpu_percent} 
              label="CPU Usage" 
              threshold={80}
            />
            <PerformanceIndicator 
              value={metrics.system.memory_percent} 
              label="Memory Usage" 
              threshold={85}
            />
            <PerformanceIndicator 
              value={metrics.system.disk_percent} 
              label="Disk Usage" 
              threshold={90}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Eye className="w-5 h-5 mr-2" />
              Live Camera Feeds
            </CardTitle>
            <CardDescription>
              Active camera streams and status
            </CardDescription>
          </CardHeader>
          <CardContent>
            <LiveCameraGrid />
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity Feed */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Clock className="w-5 h-5 mr-2" />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* Activity feed would be populated by WebSocket events */}
          <div className="space-y-3">
            <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-2 h-2 bg-green-500 rounded-full" />
              <div className="flex-1">
                <p className="text-sm font-medium">Camera motion detected</p>
                <p className="text-xs text-gray-500">Front Door Camera - 2 minutes ago</p>
              </div>
            </div>
            <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-2 h-2 bg-blue-500 rounded-full" />
              <div className="flex-1">
                <p className="text-sm font-medium">Inference job completed</p>
                <p className="text-xs text-gray-500">YOLOv8 Person Detection - 5 minutes ago</p>
              </div>
            </div>
            <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-2 h-2 bg-purple-500 rounded-full" />
              <div className="flex-1">
                <p className="text-sm font-medium">New model uploaded</p>
                <p className="text-xs text-gray-500">Custom Vehicle Detector v2.1 - 12 minutes ago</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}