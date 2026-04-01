import React, { useState, useEffect } from 'react';
import { Layout } from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { Plus, X, TrendingUp, TrendingDown, DollarSign, Trash2 } from 'lucide-react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export const Financeiro = () => {
  const { api, user } = useAuth();
  const [records, setRecords] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    type: 'income',
    amount: '',
    description: '',
    category: '',
    lawyer_id: '',
    date: new Date().toISOString().split('T')[0],
  });

  useEffect(() => {
    if (user?.role === 'admin') {
      loadData();
    }
  }, [user]);

  const loadData = async () => {
    try {
      const [recordsRes, statsRes] = await Promise.all([
        api.get('/financial'),
        api.get('/financial/stats'),
      ]);
      setRecords(recordsRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error('Error loading financial data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const dataToSend = {
        ...formData,
        amount: parseFloat(formData.amount),
      };
      await api.post('/financial', dataToSend);
      await loadData();
      setShowForm(false);
      resetForm();
    } catch (error) {
      console.error('Error creating financial record:', error);
      alert('Erro ao criar registro financeiro');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Deseja realmente excluir este registro?')) return;

    try {
      await api.delete(`/financial/${id}`);
      await loadData();
    } catch (error) {
      console.error('Error deleting record:', error);
      alert('Erro ao excluir registro');
    }
  };

  const resetForm = () => {
    setFormData({
      type: 'income',
      amount: '',
      description: '',
      category: '',
      lawyer_id: '',
      date: new Date().toISOString().split('T')[0],
    });
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  if (user?.role !== 'admin') {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <DollarSign size={64} className="mx-auto text-red-400 mb-4" />
            <h2 className="text-2xl font-bold text-[#F5F5F5] mb-2">Acesso Restrito</h2>
            <p className="text-[#F5F5F5]/60">Apenas administradores podem acessar o módulo financeiro</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto" data-testid="financeiro-page">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-[#F5F5F5] mb-2">Módulo Financeiro</h1>
            <p className="text-[#F5F5F5]/60">Controle de receitas, despesas e fluxo de caixa</p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            data-testid="add-financial-record-btn"
            className="flex items-center space-x-2 px-6 py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg transition-all"
          >
            <Plus size={20} />
            <span>Novo Registro</span>
          </button>
        </div>

        {loading ? (
          <p className="text-center text-[#F5F5F5]/60 py-8">Carregando...</p>
        ) : (
          <>
            {/* Stats Cards */}
            {stats && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-gradient-to-br from-green-900/40 to-green-800/40 border border-green-700/50 rounded-xl p-6">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="text-green-300 text-sm mb-1">Receitas Totais</p>
                      <p className="text-3xl font-bold text-white">
                        R$ {stats.total_income.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                      </p>
                    </div>
                    <TrendingUp size={32} className="text-green-400" />
                  </div>
                </div>

                <div className="bg-gradient-to-br from-red-900/40 to-red-800/40 border border-red-700/50 rounded-xl p-6">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="text-red-300 text-sm mb-1">Despesas Totais</p>
                      <p className="text-3xl font-bold text-white">
                        R$ {stats.total_expense.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                      </p>
                    </div>
                    <TrendingDown size={32} className="text-red-400" />
                  </div>
                </div>

                <div className="bg-gradient-to-br from-[#D4AF37] to-[#B8941F] rounded-xl p-6">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="text-[#121212]/80 text-sm mb-1 font-medium">Lucro Líquido</p>
                      <p className="text-3xl font-bold text-[#121212]">
                        R$ {stats.profit.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                      </p>
                    </div>
                    <DollarSign size={32} className="text-[#121212]" />
                  </div>
                  <p className="text-[#121212]/60 text-sm">Receitas - Despesas</p>
                </div>
              </div>
            )}

            {/* Charts */}
            {stats && stats.monthly_stats && stats.monthly_stats.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                {/* Bar Chart */}
                <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-6">
                  <h2 className="text-xl font-bold text-[#F5F5F5] mb-6">Receitas vs Despesas (Mensal)</h2>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={stats.monthly_stats}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#3A3A3A" />
                      <XAxis dataKey="month" stroke="#F5F5F5" />
                      <YAxis stroke="#F5F5F5" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1E1E1E',
                          border: '1px solid #3A3A3A',
                          borderRadius: '8px',
                          color: '#F5F5F5',
                        }}
                      />
                      <Legend />
                      <Bar dataKey="income" fill="#4CAF50" name="Receitas" />
                      <Bar dataKey="expense" fill="#F44336" name="Despesas" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Line Chart */}
                <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-6">
                  <h2 className="text-xl font-bold text-[#F5F5F5] mb-6">Evolução do Lucro</h2>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={stats.monthly_stats}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#3A3A3A" />
                      <XAxis dataKey="month" stroke="#F5F5F5" />
                      <YAxis stroke="#F5F5F5" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1E1E1E',
                          border: '1px solid #3A3A3A',
                          borderRadius: '8px',
                          color: '#F5F5F5',
                        }}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="profit"
                        stroke="#D4AF37"
                        strokeWidth={3}
                        name="Lucro"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Records Table */}
            <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl overflow-hidden">
              <div className="p-6 border-b border-[#3A3A3A]">
                <h2 className="text-xl font-bold text-[#F5F5F5]">Histórico de Transações</h2>
              </div>

              {records.length === 0 ? (
                <div className="p-12 text-center">
                  <DollarSign size={48} className="mx-auto text-[#D4AF37] mb-4" />
                  <p className="text-[#F5F5F5]/60">Nenhum registro financeiro</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-[#2A2A2A]">
                      <tr>
                        <th className="px-6 py-4 text-left text-xs font-medium text-[#D4AF37] uppercase tracking-wider">
                          Data
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-medium text-[#D4AF37] uppercase tracking-wider">
                          Tipo
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-medium text-[#D4AF37] uppercase tracking-wider">
                          Descrição
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-medium text-[#D4AF37] uppercase tracking-wider">
                          Categoria
                        </th>
                        <th className="px-6 py-4 text-right text-xs font-medium text-[#D4AF37] uppercase tracking-wider">
                          Valor
                        </th>
                        <th className="px-6 py-4 text-center text-xs font-medium text-[#D4AF37] uppercase tracking-wider">
                          Ações
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#3A3A3A]">
                      {records.map((record) => (
                        <tr key={record.id} className="hover:bg-[#2A2A2A] transition-colors" data-testid={`financial-record-${record.id}`}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-[#F5F5F5]">
                            {new Date(record.date).toLocaleDateString('pt-BR')}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span
                              className={`px-3 py-1 text-xs font-medium rounded-full ${
                                record.type === 'income'
                                  ? 'bg-green-900/30 text-green-400'
                                  : 'bg-red-900/30 text-red-400'
                              }`}
                            >
                              {record.type === 'income' ? 'Receita' : 'Despesa'}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-sm text-[#F5F5F5]">{record.description}</td>
                          <td className="px-6 py-4 text-sm text-[#F5F5F5]/60">{record.category}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-bold">
                            <span className={record.type === 'income' ? 'text-green-400' : 'text-red-400'}>
                              {record.type === 'income' ? '+' : '-'} R${' '}
                              {record.amount.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-center">
                            <button
                              onClick={() => handleDelete(record.id)}
                              className="p-2 text-red-400 hover:bg-red-900/20 rounded transition-colors"
                              data-testid={`delete-financial-${record.id}`}
                            >
                              <Trash2 size={16} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}

        {/* Form Modal */}
        {showForm && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
            <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl max-w-2xl w-full">
              <div className="border-b border-[#3A3A3A] p-6 flex items-center justify-between">
                <h2 className="text-2xl font-bold text-[#F5F5F5]">Novo Registro Financeiro</h2>
                <button
                  onClick={() => {
                    setShowForm(false);
                    resetForm();
                  }}
                  className="p-2 hover:bg-[#2A2A2A] rounded-lg transition-colors"
                >
                  <X size={24} className="text-[#F5F5F5]" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="p-6 space-y-6">
                {/* Type Selection */}
                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Tipo *</label>
                  <div className="flex space-x-4">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        name="type"
                        value="income"
                        checked={formData.type === 'income'}
                        onChange={handleChange}
                        className="w-4 h-4"
                      />
                      <span className="text-green-400 font-medium">Receita</span>
                    </label>
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        name="type"
                        value="expense"
                        checked={formData.type === 'expense'}
                        onChange={handleChange}
                        className="w-4 h-4"
                      />
                      <span className="text-red-400 font-medium">Despesa</span>
                    </label>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Valor (R$) *</label>
                    <input
                      type="number"
                      step="0.01"
                      name="amount"
                      value={formData.amount}
                      onChange={handleChange}
                      required
                      data-testid="financial-amount"
                      className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Data *</label>
                    <input
                      type="date"
                      name="date"
                      value={formData.date}
                      onChange={handleChange}
                      required
                      data-testid="financial-date"
                      className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Descrição *</label>
                  <input
                    type="text"
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    required
                    data-testid="financial-description"
                    placeholder="Ex: Honorários processo XYZ, Aluguel escritório..."
                    className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Categoria *</label>
                  <input
                    type="text"
                    name="category"
                    value={formData.category}
                    onChange={handleChange}
                    required
                    data-testid="financial-category"
                    placeholder="Ex: Honorários, Despesas Operacionais, Marketing..."
                    className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                  />
                </div>

                <button
                  type="submit"
                  data-testid="financial-submit-btn"
                  className="w-full py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg transition-all"
                >
                  Criar Registro
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};
