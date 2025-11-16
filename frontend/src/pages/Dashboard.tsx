import { useQuery } from '@tanstack/react-query';
import { modelsApi, inferenceApi, camerasApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Brain, Zap, Video, TrendingUp } from 'lucide-react';

export default function Dashboard() {
  const { data: modelsData } = useQuery({
    queryKey: ['models'],
    queryFn: () => modelsApi.list({ page: 1, limit: 5 }),
  });

  const { data: inferenceData } = useQuery({
    queryKey: ['inference-jobs'],
    queryFn: () => inferenceApi.listJobs({ page: 1, limit: 10 }),
  });

  const { data: camerasData } = useQuery({
    queryKey: ['cameras'],
    queryFn: () => camerasApi.list({ page: 1, limit: 5 }),
  });

  const stats = [
    {
      name: 'Total Models',
      value: modelsData?.total || 0,
      icon: Brain,
      color: 'bg-blue-500',
    },
    {
      name: 'Inference Jobs',
      value: inferenceData?.total || 0,
      icon: Zap,
      color: 'bg-green-500',
    },
    {
      name: 'Active Cameras',
      value: camerasData?.items?.filter((c: any) => c.status === 'active').length || 0,
      icon: Video,
      color: 'bg-purple-500',
    },
    {
      name: 'Success Rate',
      value: inferenceData?.items?.length ? 
        `${Math.round((inferenceData.items.filter((job: any) => job.status === 'completed').length / inferenceData.items.length) * 100)}%` : 
        '0%',
      icon: TrendingUp,
      color: 'bg-orange-500',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-slate-100">Dashboard</h2>
        <p className="text-slate-400 mt-1">Welcome to NexusAIPlatform Analytics Platform</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.name}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-400">{stat.name}</p>
                    <p className="text-3xl font-bold text-slate-100 mt-2">{stat.value}</p>
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

      {/* Recent Inference Jobs */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Inference Jobs</CardTitle>
          <CardDescription>Latest AI inference results</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {inferenceData?.items?.slice(0, 5).map((job: any) => (
              <div key={job.id} className="flex items-center justify-between border-b pb-3 last:border-0">
                <div>
                  <p className="font-medium text-slate-100">Job #{job.id}</p>
                  <p className="text-sm text-slate-400">{job.model_name}</p>
                </div>
                <div className="text-right">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    job.status === 'completed' ? 'bg-green-500/20 text-green-300 border border-green-500/30' :
                    job.status === 'failed' ? 'bg-red-500/20 text-red-300 border border-red-500/30' :
                    'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30'
                  }`}>
                    {job.status}
                  </span>
                  {job.processing_time && (
                    <p className="text-xs text-gray-500 mt-1">{job.processing_time}ms</p>
                  )}
                </div>
              </div>
            ))}
            {!inferenceData?.items?.length && (
              <p className="text-center text-gray-500 py-4">No inference jobs yet</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Available Models */}
      <Card>
        <CardHeader>
          <CardTitle>Available Models</CardTitle>
          <CardDescription>AI models ready for inference</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {modelsData?.items?.map((model: any) => (
              <div key={model.id} className="border rounded-lg p-4 hover:border-blue-500 transition-colors">
                <h4 className="font-semibold text-gray-900">{model.name}</h4>
                <p className="text-sm text-gray-500 mt-1">{model.task_type}</p>
                <div className="flex items-center gap-2 mt-3">
                  <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
                    {model.framework}
                  </span>
                  <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">
                    {model.version}
                  </span>
                </div>
              </div>
            ))}
            {!modelsData?.items?.length && (
              <p className="col-span-3 text-center text-gray-500 py-4">No models available</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
