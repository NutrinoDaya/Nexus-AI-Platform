import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Brain, 
  Zap, 
  Video, 
  Settings, 
  Users, 
  LogOut,
  Target
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';

export default function Sidebar() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  const navigation = [
    { name: 'Dashboard', to: '/', icon: LayoutDashboard },
    { name: 'Models', to: '/models', icon: Brain },
    { name: 'Inference', to: '/inference', icon: Zap },
    { name: 'Cameras', to: '/cameras', icon: Video },
    { name: 'YOLO', to: '/yolo', icon: Target },
    { name: 'Settings', to: '/settings', icon: Settings },
    ...(user?.role === 'admin' ? [{ name: 'Users', to: '/users', icon: Users }] : []),
  ];

  const handleLogout = async () => {
    await logout();
    window.location.href = '/login';
  };

  return (
    <div className="fixed inset-y-0 left-0 z-50 w-64 bg-slate-800/95 backdrop-blur-sm border-r border-slate-700 text-white flex flex-col">
      <div className="p-6 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
            <Video className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              NexusAIPlatform
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">Analytics Platform</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                  isActive
                    ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/25'
                    : 'text-slate-300 hover:bg-slate-700/50 hover:text-white'
                }`
              }
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-700">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-4 py-3 w-full rounded-lg text-slate-300 hover:bg-red-500/10 hover:text-red-400 transition-all duration-200 group"
        >
          <LogOut className="w-5 h-5 group-hover:rotate-12 transition-transform duration-200" />
          <span className="font-medium">Logout</span>
        </button>
      </div>
    </div>
  );
}
