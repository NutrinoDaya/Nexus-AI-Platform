import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { yoloApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { 
  Brain, 
  Upload, 
  Eye, 
  Scissors, 
  Target, 
  Play, 
  Loader2, 
  Download,
  Trash2
} from 'lucide-react';

interface Detection {
  id: number;
  bbox: [number, number, number, number];
  confidence: number;
  class_id: number;
  class_name: string;
  polygon?: [number, number][];
}

interface Track {
  detection_id: number;
  bbox: [number, number, number, number];
  confidence: number;
  class_id: number;
  class_name: string;
  track_id: number | null;
}

interface YOLOResult {
  detections?: Detection[];
  tracks?: Track[];
  image_shape: [number, number, number];
  model_id: string;
  task: string;
}

export default function YOLOPage() {
  const queryClient = useQueryClient();
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>('');
  const [results, setResults] = useState<YOLOResult | null>(null);
  const [newModelPath, setNewModelPath] = useState('');
  const [newModelId, setNewModelId] = useState('');
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.25);
  const [iouThreshold, setIouThreshold] = useState(0.45);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Queries
  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ['yolo-models'],
    queryFn: yoloApi.listModels,
  });

  // Mutations
  const loadModelMutation = useMutation({
    mutationFn: ({ path, id }: { path: string; id?: string }) => 
      yoloApi.loadModel(path, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['yolo-models'] });
      setNewModelPath('');
      setNewModelId('');
    },
  });

  const unloadModelMutation = useMutation({
    mutationFn: yoloApi.unloadModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['yolo-models'] });
    },
  });

  const detectMutation = useMutation({
    mutationFn: ({ image, modelId }: { image: File; modelId: string }) =>
      yoloApi.detect(image, modelId, { 
        confidenceThreshold, 
        iouThreshold,
        maxDetections: 1000 
      }),
    onSuccess: (data) => {
      setResults(data);
      drawResults(data);
    },
  });

  const segmentMutation = useMutation({
    mutationFn: ({ image, modelId }: { image: File; modelId: string }) =>
      yoloApi.segment(image, modelId, { 
        confidenceThreshold, 
        iouThreshold,
        maxDetections: 1000 
      }),
    onSuccess: (data) => {
      setResults(data);
      drawResults(data);
    },
  });

  const trackMutation = useMutation({
    mutationFn: ({ image, modelId }: { image: File; modelId: string }) =>
      yoloApi.track(image, modelId, { 
        confidenceThreshold, 
        iouThreshold,
        tracker: 'bytetrack.yaml'
      }),
    onSuccess: (data) => {
      setResults(data);
      drawResults(data);
    },
  });

  const preloadMutation = useMutation({
    mutationFn: yoloApi.preloadDefaultModels,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['yolo-models'] });
    },
  });

  const handleImageSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedImage(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
        setResults(null);
      };
      reader.readAsDataURL(file);
    }
  };

  const drawResults = (data: YOLOResult) => {
    if (!canvasRef.current || !imagePreview) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);

      // Draw detections or tracks
      const items = data.detections || data.tracks || [];
      
      items.forEach((item, index) => {
        const bbox = 'bbox' in item ? item.bbox : [];
        const [x1, y1, x2, y2] = bbox;
        
        // Set colors
        const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8'];
        const color = colors[index % colors.length];
        
        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        ctx.lineWidth = 2;
        
        // Draw bounding box
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
        
        // Draw label
        const label = `${item.class_name} ${(item.confidence * 100).toFixed(1)}%`;
        const trackLabel = 'track_id' in item && item.track_id ? ` #${item.track_id}` : '';
        const fullLabel = label + trackLabel;
        
        ctx.font = '14px Arial';
        const textWidth = ctx.measureText(fullLabel).width;
        
        ctx.fillRect(x1, y1 - 25, textWidth + 10, 20);
        ctx.fillStyle = 'white';
        ctx.fillText(fullLabel, x1 + 5, y1 - 10);
        
        // Draw polygon for segmentation
        if ('polygon' in item && item.polygon && item.polygon.length > 0) {
          ctx.strokeStyle = color;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(item.polygon[0][0], item.polygon[0][1]);
          for (let i = 1; i < item.polygon.length; i++) {
            ctx.lineTo(item.polygon[i][0], item.polygon[i][1]);
          }
          ctx.closePath();
          ctx.stroke();
        }
      });
    };
    img.src = imagePreview;
  };

  const handleLoadModel = () => {
    if (newModelPath.trim()) {
      loadModelMutation.mutate({ 
        path: newModelPath.trim(), 
        id: newModelId.trim() || undefined 
      });
    }
  };

  const handleDetect = () => {
    if (selectedImage && selectedModel) {
      detectMutation.mutate({ image: selectedImage, modelId: selectedModel });
    }
  };

  const handleSegment = () => {
    if (selectedImage && selectedModel) {
      segmentMutation.mutate({ image: selectedImage, modelId: selectedModel });
    }
  };

  const handleTrack = () => {
    if (selectedImage && selectedModel) {
      trackMutation.mutate({ image: selectedImage, modelId: selectedModel });
    }
  };

  const models = modelsData?.models || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-slate-100">YOLO Models</h2>
        <p className="text-slate-400 mt-1">Object detection, segmentation and tracking with YOLO</p>
      </div>

      <Tabs defaultValue="inference" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="inference">Inference</TabsTrigger>
          <TabsTrigger value="models">Model Management</TabsTrigger>
        </TabsList>

        <TabsContent value="inference" className="space-y-6">
          {/* Model Selection and Image Upload */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="w-5 h-5" />
                  Model Selection
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Select YOLO Model</Label>
                  <Select value={selectedModel} onValueChange={setSelectedModel}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choose a model..." />
                    </SelectTrigger>
                    <SelectContent>
                      {models.map((model: any) => (
                        <SelectItem key={model.model_id} value={model.model_id}>
                          {model.model_id} ({model.task})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Confidence</Label>
                    <Input
                      type="number"
                      min="0"
                      max="1"
                      step="0.05"
                      value={confidenceThreshold}
                      onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>IoU Threshold</Label>
                    <Input
                      type="number"
                      min="0"
                      max="1"
                      step="0.05"
                      value={iouThreshold}
                      onChange={(e) => setIouThreshold(parseFloat(e.target.value))}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="w-5 h-5" />
                  Image Upload
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Select Image</Label>
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={handleImageSelect}
                  />
                </div>

                {imagePreview && (
                  <div className="w-full h-48 bg-slate-800 rounded-lg overflow-hidden">
                    <img
                      src={imagePreview}
                      alt="Preview"
                      className="w-full h-full object-contain"
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Inference Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Run Inference</CardTitle>
              <CardDescription>
                Choose the type of inference to run on your image
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4">
                <Button
                  onClick={handleDetect}
                  disabled={!selectedImage || !selectedModel || detectMutation.isPending}
                  className="flex items-center gap-2"
                >
                  {detectMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                  Detect Objects
                </Button>

                <Button
                  onClick={handleSegment}
                  disabled={!selectedImage || !selectedModel || segmentMutation.isPending}
                  className="flex items-center gap-2"
                  variant="outline"
                >
                  {segmentMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Scissors className="w-4 h-4" />
                  )}
                  Segment Objects
                </Button>

                <Button
                  onClick={handleTrack}
                  disabled={!selectedImage || !selectedModel || trackMutation.isPending}
                  className="flex items-center gap-2"
                  variant="outline"
                >
                  {trackMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Target className="w-4 h-4" />
                  )}
                  Track Objects
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Results */}
          {(results || imagePreview) && (
            <Card>
              <CardHeader>
                <CardTitle>Results</CardTitle>
                {results && (
                  <CardDescription>
                    Found {results.detections?.length || results.tracks?.length || 0} objects
                    using {results.model_id} ({results.task})
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent>
                <div className="relative">
                  <canvas
                    ref={canvasRef}
                    className="max-w-full h-auto border border-slate-700 rounded-lg"
                  />
                </div>

                {results && (
                  <div className="mt-4 space-y-2">
                    <h4 className="font-medium text-slate-200">Detections:</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                      {(results.detections || results.tracks || []).map((item, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-2 bg-slate-800 rounded"
                        >
                          <span className="text-sm text-slate-300">
                            {item.class_name}
                            {'track_id' in item && item.track_id && ` #${item.track_id}`}
                          </span>
                          <Badge variant="secondary">
                            {(item.confidence * 100).toFixed(1)}%
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="models" className="space-y-6">
          {/* Load New Model */}
          <Card>
            <CardHeader>
              <CardTitle>Load YOLO Model</CardTitle>
              <CardDescription>
                Load a YOLO model from file path or preload default models
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Model Path</Label>
                  <Input
                    placeholder="e.g., /models/yolov8n.pt"
                    value={newModelPath}
                    onChange={(e) => setNewModelPath(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Model ID (optional)</Label>
                  <Input
                    placeholder="e.g., yolov8n-custom"
                    value={newModelId}
                    onChange={(e) => setNewModelId(e.target.value)}
                  />
                </div>
              </div>
              
              <div className="flex gap-2">
                <Button
                  onClick={handleLoadModel}
                  disabled={!newModelPath.trim() || loadModelMutation.isPending}
                >
                  {loadModelMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <Download className="w-4 h-4 mr-2" />
                  )}
                  Load Model
                </Button>
                
                <Button
                  onClick={() => preloadMutation.mutate()}
                  disabled={preloadMutation.isPending}
                  variant="outline"
                >
                  {preloadMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <Play className="w-4 h-4 mr-2" />
                  )}
                  Preload Defaults
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Loaded Models */}
          <Card>
            <CardHeader>
              <CardTitle>Loaded Models</CardTitle>
              <CardDescription>
                Manage your loaded YOLO models
              </CardDescription>
            </CardHeader>
            <CardContent>
              {modelsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin" />
                </div>
              ) : models.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  No models loaded. Load a model or preload defaults to get started.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {models.map((model: any) => (
                    <div
                      key={model.model_id}
                      className="p-4 bg-slate-800 rounded-lg border border-slate-700"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-medium text-slate-200 truncate">
                          {model.model_id}
                        </h4>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => unloadModelMutation.mutate(model.model_id)}
                          disabled={unloadModelMutation.isPending}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                      
                      <div className="space-y-1 text-sm text-slate-400">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {model.task}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {model.class_count} classes
                          </Badge>
                        </div>
                        <p className="truncate">{model.path}</p>
                        <p>Input: {model.input_size}x{model.input_size}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}