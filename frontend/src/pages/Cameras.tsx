import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { camerasApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Video, VideoOff, Camera as CameraIcon, Plus, Trash2 } from 'lucide-react';

export default function Cameras() {
  const queryClient = useQueryClient();
  const [showAddForm, setShowAddForm] = useState(false);
  const [newCamera, setNewCamera] = useState({
    name: '',
    rtsp_url: '',
    location: '',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['cameras'],
    queryFn: () => camerasApi.list({}),
  });

  const createMutation = useMutation({
    mutationFn: camerasApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cameras'] });
      setShowAddForm(false);
      setNewCamera({ name: '', rtsp_url: '', location: '' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: camerasApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cameras'] });
    },
  });

  const toggleStreamMutation = useMutation({
    mutationFn: ({ id, start }: { id: number; start: boolean }) =>
      start ? camerasApi.startStream(id) : camerasApi.stopStream(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cameras'] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(newCamera);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-slate-100">Cameras</h2>
          <p className="text-slate-400 mt-1">Manage live camera streams</p>
        </div>
        <Button onClick={() => setShowAddForm(!showAddForm)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Camera
        </Button>
      </div>

      {/* Add Camera Form */}
      {showAddForm && (
        <Card>
          <CardHeader>
            <CardTitle>Add New Camera</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Camera Name</Label>
                  <Input
                    id="name"
                    value={newCamera.name}
                    onChange={(e) => setNewCamera({ ...newCamera, name: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="location">Location</Label>
                  <Input
                    id="location"
                    value={newCamera.location}
                    onChange={(e) => setNewCamera({ ...newCamera, location: e.target.value })}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="rtsp_url">RTSP URL</Label>
                <Input
                  id="rtsp_url"
                  type="url"
                  placeholder="rtsp://username:password@ip:port/stream"
                  value={newCamera.rtsp_url}
                  onChange={(e) => setNewCamera({ ...newCamera, rtsp_url: e.target.value })}
                  required
                />
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creating...' : 'Create Camera'}
                </Button>
                <Button type="button" variant="outline" onClick={() => setShowAddForm(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Camera Grid */}
      {isLoading ? (
        <div className="text-center py-8">Loading cameras...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data?.items?.map((camera: any) => (
            <Card key={camera.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{camera.name}</CardTitle>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    camera.is_active ? 'bg-green-500/20 text-green-300 border border-green-500/30' : 'bg-slate-500/20 text-slate-300 border border-slate-500/30'
                  }`}>
                    {camera.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Video Preview */}
                <div className="bg-slate-800 rounded-lg aspect-video flex items-center justify-center border border-slate-700">
                  {camera.stream_url ? (
                    <img
                      src={`${camera.stream_url}/snapshot`}
                      alt={camera.name}
                      className="w-full h-full object-cover rounded-lg"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                        e.currentTarget.nextElementSibling?.classList.remove('hidden');
                      }}
                    />
                  ) : null}
                  <CameraIcon className={`w-12 h-12 text-slate-500 ${camera.stream_url ? 'hidden' : ''}`} />
                </div>

                {/* Camera Info */}
                <div className="space-y-1 text-sm">
                  {camera.location && (
                    <p className="text-gray-600">Location: {camera.location}</p>
                  )}
                  <p className="text-gray-500 truncate" title={camera.rtsp_url}>
                    {camera.rtsp_url}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant={camera.is_active ? 'outline' : 'default'}
                    onClick={() => toggleStreamMutation.mutate({ 
                      id: camera.id, 
                      start: !camera.is_active 
                    })}
                    disabled={toggleStreamMutation.isPending}
                  >
                    {camera.is_active ? (
                      <><VideoOff className="w-4 h-4 mr-1" />Stop</>
                    ) : (
                      <><Video className="w-4 h-4 mr-1" />Start</>
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      if (confirm('Delete this camera?')) {
                        deleteMutation.mutate(camera.id);
                      }
                    }}
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!isLoading && data?.items?.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <CameraIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No cameras configured</p>
            <Button className="mt-4" onClick={() => setShowAddForm(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Your First Camera
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
