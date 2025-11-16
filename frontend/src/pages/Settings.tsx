import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Save } from 'lucide-react';

export default function Settings() {
  const queryClient = useQueryClient();
  const [settings, setSettings] = useState<Record<string, string>>({});

  const { data, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsApi.list(),
  });

  // Use useEffect instead of deprecated onSuccess
  useEffect(() => {
    if (data) {
      const settingsMap: Record<string, string> = {};
      (data as any[]).forEach((s: any) => {
        settingsMap[s.key] = s.value;
      });
      setSettings(settingsMap);
    }
  }, [data]);

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      settingsApi.update(key, { value }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  const bulkUpdateMutation = useMutation({
    mutationFn: (updates: Array<{ key: string; value: string }>) =>
      settingsApi.bulkUpdate(updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  const handleChange = (key: string, value: string) => {
    setSettings({ ...settings, [key]: value });
  };

  const handleSave = (key: string) => {
    updateMutation.mutate({ key, value: settings[key] });
  };

  const handleSaveAll = () => {
    const updates = Object.entries(settings).map(([key, value]) => ({ key, value }));
    bulkUpdateMutation.mutate(updates);
  };

  const settingCategories = [
    {
      title: 'General',
      description: 'General system settings',
      keys: ['app_name', 'max_upload_size', 'timezone'],
    },
    {
      title: 'Inference',
      description: 'Model inference configuration',
      keys: ['default_model', 'inference_timeout', 'max_batch_size'],
    },
    {
      title: 'Storage',
      description: 'File storage and retention',
      keys: ['storage_backend', 'retention_days', 'max_storage_gb'],
    },
    {
      title: 'Streaming',
      description: 'Camera streaming settings',
      keys: ['stream_protocol', 'stream_quality', 'max_concurrent_streams'],
    },
  ];

  if (isLoading) {
    return <div className="text-center py-8">Loading settings...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Settings</h2>
          <p className="text-gray-600 mt-1">Configure system settings</p>
        </div>
        <Button onClick={handleSaveAll} disabled={bulkUpdateMutation.isPending}>
          <Save className="w-4 h-4 mr-2" />
          Save All
        </Button>
      </div>

      {settingCategories.map((category) => (
        <Card key={category.title}>
          <CardHeader>
            <CardTitle>{category.title}</CardTitle>
            <CardDescription>{category.description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {category.keys.map((key) => {
              const setting = data?.find((s: any) => s.key === key);
              if (!setting) return null;

              return (
                <div key={key} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
                  <div>
                    <Label htmlFor={key}>{setting.key}</Label>
                    {setting.description && (
                      <p className="text-sm text-gray-500 mt-1">{setting.description}</p>
                    )}
                  </div>
                  <Input
                    id={key}
                    value={settings[key] || setting.value}
                    onChange={(e) => handleChange(key, e.target.value)}
                    placeholder={setting.default_value}
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleSave(key)}
                    disabled={updateMutation.isPending}
                  >
                    <Save className="w-4 h-4 mr-1" />
                    Save
                  </Button>
                </div>
              );
            })}
          </CardContent>
        </Card>
      ))}

      {/* Additional Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Advanced Settings</CardTitle>
          <CardDescription>Other system configurations</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {data
            ?.filter((s: any) => !settingCategories.some(cat => cat.keys.includes(s.key)))
            .map((setting: any) => (
              <div key={setting.key} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
                <div>
                  <Label htmlFor={setting.key}>{setting.key}</Label>
                  {setting.description && (
                    <p className="text-sm text-gray-500 mt-1">{setting.description}</p>
                  )}
                </div>
                <Input
                  id={setting.key}
                  value={settings[setting.key] || setting.value}
                  onChange={(e) => handleChange(setting.key, e.target.value)}
                  placeholder={setting.default_value}
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleSave(setting.key)}
                  disabled={updateMutation.isPending}
                >
                  <Save className="w-4 h-4 mr-1" />
                  Save
                </Button>
              </div>
            ))}
        </CardContent>
      </Card>
    </div>
  );
}
