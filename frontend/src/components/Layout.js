import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Calendar, FolderKanban, DollarSign, FolderTree, LogOut, Menu, X, User, Users } from 'lucide-react';

export const Layout = ({ children }) => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = async () => { await logout(); navigate('/login'); };

  const menuItems = [
    { path: '/dashboard', icon: User, label: 'Dashboard' },
    { path: '/agenda', icon: Calendar, label: 'Agenda' },
    { path: '/processos', icon: FolderKanban, label: 'Processos' },
    { path: '/clientes', icon: Users, label: 'Clientes' },
    { path: '/drive', icon: FolderTree, label: 'Drive Jurídico' },
    { path: '/financeiro', icon: DollarSign, label: 'Financeiro' },
  ];

  return (
    <div className="min-h-screen bg-[#121212] text-[#F5F5F5]">
      <aside className={`fixed top-0 left-0 h-full bg-[#1E1E1E] border-r border-[#3A3A3A] transition-all duration-300 z-30 ${sidebarOpen ? 'w-64' : 'w-20'}`}>
        <div className="h-16 flex items-center justify-between px-4 border-b border-[#3A3A3A]">
          {sidebarOpen && <h1 className="text-xl font-bold text-[#D4AF37]">Sistema Jurídico</h1>}
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 hover:bg-[#2A2A2A] rounded-lg" data-testid="sidebar-toggle-btn">
            {sidebarOpen ? <X size={20} className="text-[#D4AF37]" /> : <Menu size={20} className="text-[#D4AF37]" />}
          </button>
        </div>
        <div className="p-4 border-b border-[#3A3A3A]"><div className="flex items-center space-x-3"><div className="w-10 h-10 bg-[#D4AF37] rounded-full flex items-center justify-center"><span className="text-[#121212] font-bold">{user?.name?.charAt(0).toUpperCase()}</span></div>{sidebarOpen && <div className="flex-1 min-w-0"><p className="text-sm font-medium truncate">{user?.name}</p><p className="text-xs text-gray-400 capitalize">{user?.role}</p></div>}</div></div>
        <nav className="flex-1 p-4 space-y-2">
          {menuItems.map((item) => { const Icon = item.icon; const isActive = location.pathname === item.path; return <Link key={item.path} to={item.path} data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`} className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${isActive ? 'bg-[#D4AF37] text-[#121212]' : 'hover:bg-[#2A2A2A] text-[#F5F5F5]'}`}><Icon size={20} />{sidebarOpen && <span className="font-medium">{item.label}</span>}</Link>; })}
        </nav>
        <div className="p-4 border-t border-[#3A3A3A]"><button onClick={handleLogout} data-testid="logout-btn" className="w-full flex items-center space-x-3 px-4 py-3 rounded-lg hover:bg-red-900/20 text-red-400"><LogOut size={20} />{sidebarOpen && <span className="font-medium">Sair</span>}</button></div>
      </aside>
      <main className={`transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-20'}`}><div className="min-h-screen p-8">{children}</div></main>
    </div>
  );
};
