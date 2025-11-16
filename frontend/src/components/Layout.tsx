import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useAuthStore } from '@/lib/auth-store';

export default function Layout() {
  const user = useAuthStore((state) => state.user);

  return (
    <div className="min-h-screen bg-slate-900">
      <Sidebar />
      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 bg-slate-800/95 backdrop-blur-sm border-b border-slate-700 px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-slate-100">NexusAIPlatform Analytics</h1>
            <div className="flex items-center gap-4">
              <span className="text-sm text-slate-300">
                {user?.full_name || user?.username}
              </span>
              <span className="px-3 py-1 text-xs font-medium rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                {user?.role}
              </span>
            </div>
          </div>
        </header>
        
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
