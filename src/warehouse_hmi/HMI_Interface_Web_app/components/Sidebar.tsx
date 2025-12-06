import React from 'react';
import { Activity, Map, Database, Settings, LogOut, Cpu, Gamepad2 } from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange, onLogout }) => {
  const menuItems = [
    { id: 'dashboard', icon: Activity, label: 'Dashboard' },
    { id: 'manual', icon: Gamepad2, label: 'Manual Control' },
    { id: 'map', icon: Map, label: 'Map Generator' },
    { id: 'data', icon: Database, label: 'Scan Data' },
    { id: 'system', icon: Cpu, label: 'System & ROS' },
    { id: 'settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="w-64 bg-sci-panel border-r border-slate-700 flex flex-col h-screen">
      <div className="p-6 flex items-center space-x-3 border-b border-slate-700">
        <img
          src="/eternal-logo.png"
          alt="Logo"
          className="w-10 h-10 object-contain drop-shadow-[0_0_15px_rgba(14,165,233,0.5)]"
        />
        <span className="text-xl font-bold tracking-wider">ETERNAL</span>
      </div>

      <nav className="flex-1 px-4 space-y-2 overflow-y-auto custom-scrollbar">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${isActive
                ? 'bg-sci-accent/10 text-sci-accent border border-sci-accent/50 shadow-[0_0_10px_rgba(14,165,233,0.2)]'
                : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                }`}
            >
              <Icon size={20} />
              <span className="font-medium">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-700">
        <button
          onClick={onLogout}
          className="w-full flex items-center space-x-3 px-4 py-3 text-slate-400 hover:text-sci-danger transition-colors"
        >
          <LogOut size={20} />
          <span>Disconnect</span>
        </button>
      </div>
    </div>
  );
};
