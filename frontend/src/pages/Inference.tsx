import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { inferenceApi, modelsApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Upload, Clock } from 'lucide-react';
import { formatDate, formatDuration } from '@/lib/utils';

export default function Inference() {
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [selectedModel, setSelectedModel] = useState<number | undefined>();
  const [preview, setPreview] = useState<string | null>(null);

  const { data: modelsData } = useQuery({
    queryKey: ['models'],
    queryFn: () => modelsApi.list({}),
  });

  const { data: jobsData, refetch } = useQuery({
    queryKey: ['inference-jobs'],
    queryFn: () => inferenceApi.listJobs({}),
  });

  const predictMutation = useMutation({
    mutationFn: ({ image, modelId }: { image: File; modelId?: number }) =>
      inferenceApi.predict(image, modelId),
    onSuccess: () => {
      refetch();
      setSelectedImage(null);
      setPreview(null);
    },
  });

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedImage(file);
      const reader = new FileReader();
      reader.onloadend = () => setPreview(reader.result as string);
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedImage) {
      predictMutation.mutate({ image: selectedImage, modelId: selectedModel });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Inference</h2>
        <p className="text-gray-600 mt-1">Run AI inference on images</p>
      </div>

      {/* Upload Form */}
      <Card>
        <CardHeader>
          <CardTitle>New Inference</CardTitle>
          <CardDescription>Upload an image and select a model</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="image">Upload Image</Label>
                <Input
                  id="image"
                  type="file"
                  accept="image/*"
                  onChange={handleImageSelect}
                  required
                />
                {preview && (
                  <img src={preview} alt="Preview" className="mt-2 rounded-lg max-h-48 object-contain" />
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="model">Select Model (Optional)</Label>
                <select
                  id="model"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2"
                  value={selectedModel || ''}
                  onChange={(e) => setSelectedModel(e.target.value ? Number(e.target.value) : undefined)}
                >
                  <option value="">Default Model</option>
                  {modelsData?.items?.map((model: any) => (
                    <option key={model.id} value={model.id}>
                      {model.name} ({model.framework})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <Button type="submit" disabled={!selectedImage || predictMutation.isPending}>
              <Upload className="w-4 h-4 mr-2" />
              {predictMutation.isPending ? 'Processing...' : 'Run Inference'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Results Table */}
      <Card>
        <CardHeader>
          <CardTitle>Inference Results</CardTitle>
          <CardDescription>Recent inference jobs and results</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Model</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Processing Time</TableHead>
                <TableHead>Created At</TableHead>
                <TableHead>Results</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobsData?.items?.map((job: any) => (
                <TableRow key={job.id}>
                  <TableCell className="font-medium">#{job.id}</TableCell>
                  <TableCell>{job.model_name || 'Default'}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      job.status === 'completed' ? 'bg-green-100 text-green-800' :
                      job.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {job.status}
                    </span>
                  </TableCell>
                  <TableCell>
                    {job.processing_time ? (
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatDuration(job.processing_time)}
                      </div>
                    ) : '-'}
                  </TableCell>
                  <TableCell>{formatDate(job.created_at)}</TableCell>
                  <TableCell>
                    {job.result_data && (
                      <span className="text-sm text-gray-600">
                        {job.result_data.num_detections || 0} detections
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
