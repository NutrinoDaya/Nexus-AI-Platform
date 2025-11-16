import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usersApi } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { UserPlus, Shield, ShieldOff } from 'lucide-react';
import { formatDate } from '@/lib/utils';

export default function Users() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const [search, setSearch] = useState('');

  // Redirect if not admin
  if (user?.role !== 'admin') {
    return (
      <div className="text-center py-12">
        <Shield className="w-16 h-16 text-red-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900">Access Denied</h2>
        <p className="text-gray-600 mt-2">You need admin privileges to access this page.</p>
      </div>
    );
  }

  const { data, isLoading } = useQuery({
    queryKey: ['users', search],
    queryFn: () => usersApi.list({ search }),
  });

  const updateRoleMutation = useMutation({
    mutationFn: ({ id, role }: { id: number; role: string }) =>
      usersApi.update(id, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      usersApi.update(id, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: usersApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Users</h2>
          <p className="text-gray-600 mt-1">Manage user accounts and permissions</p>
        </div>
        <Button>
          <UserPlus className="w-4 h-4 mr-2" />
          Add User
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Users</CardTitle>
          <div className="mt-4">
            <Input
              placeholder="Search users..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-sm"
            />
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">Loading...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Username</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Full Name</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items?.map((u: any) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">{u.username}</TableCell>
                    <TableCell>{u.email}</TableCell>
                    <TableCell>{u.full_name}</TableCell>
                    <TableCell>
                      <select
                        value={u.role}
                        onChange={(e) => updateRoleMutation.mutate({ 
                          id: u.id, 
                          role: e.target.value 
                        })}
                        className="px-2 py-1 text-xs rounded border border-gray-300"
                        disabled={u.id === user?.id}
                      >
                        <option value="user">User</option>
                        <option value="admin">Admin</option>
                      </select>
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => toggleActiveMutation.mutate({ 
                          id: u.id, 
                          is_active: !u.is_active 
                        })}
                        disabled={u.id === user?.id}
                      >
                        {u.is_active ? (
                          <span className="flex items-center text-green-600">
                            <Shield className="w-4 h-4 mr-1" />
                            Active
                          </span>
                        ) : (
                          <span className="flex items-center text-red-600">
                            <ShieldOff className="w-4 h-4 mr-1" />
                            Inactive
                          </span>
                        )}
                      </Button>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {formatDate(u.created_at)}
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          if (confirm('Delete this user?')) {
                            deleteMutation.mutate(u.id);
                          }
                        }}
                        disabled={u.id === user?.id}
                        className="text-red-600"
                      >
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
