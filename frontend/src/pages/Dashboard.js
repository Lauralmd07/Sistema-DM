import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Layout } from '../components/Layout';
import { Calendar, FolderKanban, FolderTree, DollarSign, TrendingUp, Users } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Dashboard = () => {
  const { user, api } = useAuth();
  const [stats, setStats] = useState({
    appointments: 0,
    processes: 0,
    documents: 0,
    recentActivities: [],
  });
  const [loading, setLoading] = useState(true);

  const loadStats = useCallback(async () => {
    try {
      const [appointmentsRes, processesRes, documentsRes] = await Promise.all([
        api.get('/appointments'),
        api.get('/processes'),
        api.get('/documents'),
      ]);

      setStats({
        appointments: appointmentsRes.data.length,
        processes: processesRes.data.length,
        documents: documentsRes.data.length,
        recentActivities: [
          ...processesRes.data.slice(0, 3).map(p => ({
            type: 'process',
            title: `Processo: ${p.client_number}`,
            description: p.action_type,
            date: new Date(p.created_at).toLocaleDateString('pt-BR'),
          })),
          ...appointmentsRes.data.slice(0, 2).map(a => ({
            type: 'appointment',
            title: `Consulta: ${a.client_name}`,
            description: a.subject,
            date: new Date(a.created_at).toLocaleDateString('pt-BR'),
          })),
        ].slice(0, 5),
      });
    } catch (error) {
      // Error handled silently for better UX
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const statCards = [
    {
      title: 'Agendamentos',
      value: stats.appointments,
      icon: Calendar,
      color: '#D4AF37',
      link: '/agenda',
    },
    {
      title: 'Processos',
      value: stats.processes,
      icon: FolderKanban,
      color: '#4CAF50',
      link: '/processos',
    },
    {
      title: 'Documentos',
      value: stats.documents,
      icon: FolderTree,
      color: '#2196F3',
      link: '/drive',
    },
  ];

  return (
    <Layout>
      <div className="max-w-7xl mx-auto" data-testid="dashboard">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[#F5F5F5] mb-2">
            Bem-vindo, {user?.name}!
          </h1>
          <p className="text-[#F5F5F5]/60">
            Você está logado como <span className="text-[#D4AF37] capitalize">{user?.role}</span>
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {statCards.map((stat) => {
            const Icon = stat.icon;
            return (
              <Link
                key={stat.path}
                to={stat.link}
                className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-6 hover:border-[#D4AF37] transition-all group"
                data-testid={`stat-card-${stat.title.toLowerCase()}`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-[#F5F5F5]/60 text-sm mb-2">{stat.title}</p>
                    <p className="text-3xl font-bold text-[#F5F5F5]">{loading ? '...' : stat.value}</p>
                  </div>
                  <div
                    className="w-12 h-12 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform"
                    style={{ backgroundColor: `${stat.color}20` }}
                  >
                    <Icon size={24} style={{ color: stat.color }} />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>

        {/* Recent Activities */}
        <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-6">
          <h2 className="text-xl font-bold text-[#F5F5F5] mb-4">Atividades Recentes</h2>
          
          {loading ? (
            <p className="text-[#F5F5F5]/60 text-center py-8">Carregando...</p>
          ) : stats.recentActivities.length === 0 ? (
            <p className="text-[#F5F5F5]/60 text-center py-8">Nenhuma atividade recente</p>
          ) : (
            <div className="space-y-4">
              {stats.recentActivities.map((activity) => (
                <div
                  key={`${activity.type}-${activity.title}`}
                  className="flex items-start space-x-4 p-4 bg-[#2A2A2A] rounded-lg hover:bg-[#3A3A3A] transition-colors"
                >
                  <div className="flex-1">
                    <h3 className="text-[#F5F5F5] font-medium mb-1">{activity.title}</h3>
                    <p className="text-[#F5F5F5]/60 text-sm">{activity.description}</p>
                  </div>
                  <span className="text-xs text-[#D4AF37]">{activity.date}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
          <Link
            to="/agenda"
            className="bg-gradient-to-br from-[#D4AF37] to-[#B8941F] text-[#121212] rounded-xl p-6 hover:scale-105 transition-transform"
            data-testid="quick-action-agenda"
          >
            <Calendar size={28} className="mb-2" />
            <h3 className="font-bold">Nova Consulta</h3>
          </Link>

          <Link
            to="/processos"
            className="bg-gradient-to-br from-green-600 to-green-700 text-white rounded-xl p-6 hover:scale-105 transition-transform"
            data-testid="quick-action-processo"
          >
            <FolderKanban size={28} className="mb-2" />
            <h3 className="font-bold">Novo Processo</h3>
          </Link>

          <Link
            to="/drive"
            className="bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-xl p-6 hover:scale-105 transition-transform"
            data-testid="quick-action-drive"
          >
            <FolderTree size={28} className="mb-2" />
            <h3 className="font-bold">Upload Documento</h3>
          </Link>

          {user?.role === 'admin' && (
            <Link
              to="/financeiro"
              className="bg-gradient-to-br from-purple-600 to-purple-700 text-white rounded-xl p-6 hover:scale-105 transition-transform"
              data-testid="quick-action-financeiro"
            >
              <DollarSign size={28} className="mb-2" />
              <h3 className="font-bold">Finanças</h3>
            </Link>
          )}
        </div>
      </div>
    </Layout>
  );
};