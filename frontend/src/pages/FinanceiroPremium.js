import React, { useState, useEffect } from 'react';
import { Layout } from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { 
  Plus, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  AlertCircle,
  Clock,
  Edit2,
  Trash2,
  Save,
  X,
  Eye
} from 'lucide-react';
import { motion } from 'framer-motion';
import { 
  AreaChart,
  Area,
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts';
import { KPICard } from '../components/premium/KPICard';
import { GlassCard } from '../components/premium/GlassCard';
import { StatusBadge } from '../components/premium/StatusBadge';
import { premiumTheme } from '../theme-premium';

export const FinanceiroPremium = () => {
  const { api, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState(null);
  const [trustAccounts, setTrustAccounts] = useState([]);
  const [financialRecords, setFinancialRecords] = useState([]);
  const [editingRecord, setEditingRecord] = useState(null);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [newRecord, setNewRecord] = useState({
    type: 'income',
    amount: '',
    description: '',
    category: '',
    date: new Date().toISOString().split('T')[0],
  });

  const isAdmin = user?.role === 'admin';

  useEffect(() => {
    loadFinancialData();
  }, [user]);

  const loadFinancialData = async () => {
    try {
      setError('');
      const [analyticsRes, trustAccountsRes, financialRes] = await Promise.all([
        api.get('/analytics/dashboard'),
        api.get('/trust-accounts').catch(() => ({ data: [] })),
        api.get('/financial'),
      ]);

      setAnalytics(analyticsRes.data);
      setTrustAccounts(trustAccountsRes.data);
      setFinancialRecords(financialRes.data);
    } catch (error) {
      setError(error.response?.data?.detail || 'Não foi possível carregar os dados financeiros.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddRecord = async (e) => {
    e.preventDefault();
    if (!isAdmin) return;

    try {
      await api.post('/financial', {
        ...newRecord,
        amount: parseFloat(newRecord.amount),
      });
      await loadFinancialData();
      setShowAddForm(false);
      setNewRecord({
        type: 'income',
        amount: '',
        description: '',
        category: '',
        date: new Date().toISOString().split('T')[0],
      });
    } catch (error) {
      alert('Erro ao adicionar registro');
    }
  };

  const handleDeleteRecord = async (id) => {
    if (!isAdmin) return;
    if (!window.confirm('Deseja realmente excluir este registro?')) return;

    try {
      await api.delete(`/financial/${id}`);
      await loadFinancialData();
    } catch (error) {
      alert('Erro ao excluir registro');
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]"><div className="text-center"><div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 mx-auto mb-4" style={{ borderColor: premiumTheme.gold.matte }} /><p style={{ color: premiumTheme.text.secondary }}>Carregando dados financeiros...</p></div></div>
      </Layout>
    );
  }

  if (!analytics) {
    return (
      <Layout>
        <div className="max-w-xl mx-auto mt-16 text-center p-8 bg-[#1E1E1E] border border-red-500/40 rounded-xl"><AlertCircle size={42} className="mx-auto mb-4 text-red-400" /><h2 className="text-xl font-bold mb-2">Não foi possível carregar o Financeiro</h2><p className="text-[#F5F5F5]/60 mb-5">{error || 'Tente novamente em alguns instantes.'}</p><button onClick={loadFinancialData} className="px-5 py-3 bg-[#D4AF37] text-[#121212] font-bold rounded-lg">Tentar novamente</button></div>
      </Layout>
    );
  }

  const { kpis, monthly_trend, alerts } = analytics;

  // Group records by month for table view
  const recordsByMonth = {};
  financialRecords.forEach(record => {
    const month = record.date.substring(0, 7); // YYYY-MM
    if (!recordsByMonth[month]) {
      recordsByMonth[month] = { income: [], expense: [] };
    }
    recordsByMonth[month][record.type].push(record);
  });

  const sortedMonths = Object.keys(recordsByMonth).sort().reverse();

  return (
    <Layout>
      <div className="max-w-[1600px] mx-auto space-y-8" data-testid="financeiro-premium-page">
        {error && <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-lg text-red-300">{error}</div>}

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex items-center justify-between mb-2">
            <div>
              <h1 
                className="text-4xl font-light tracking-tight"
                style={{ 
                  color: premiumTheme.text.primary,
                  fontFamily: premiumTheme.typography.fontFamily.display 
                }}
              >
                Dashboard Financeiro
              </h1>
              <p style={{ color: premiumTheme.text.secondary }}>
                {isAdmin ? 'Visão consolidada e gerenciamento de receitas e despesas' : 'Visualização dos resultados financeiros'}
              </p>
            </div>
            {isAdmin && (
              <button
                onClick={() => setShowAddForm(true)}
                className="flex items-center space-x-2 px-6 py-3 rounded-lg font-medium transition-all"
                style={{
                  background: premiumTheme.gradients.gold,
                  color: premiumTheme.background.primary,
                }}
                data-testid="add-financial-btn"
              >
                <Plus size={20} />
                <span>Novo Registro</span>
              </button>
            )}
            {!isAdmin && (
              <div className="flex items-center space-x-2 px-4 py-2 bg-blue-900/20 border border-blue-500/50 rounded-lg">
                <Eye size={18} className="text-blue-400" />
                <span className="text-sm text-blue-400 font-medium">Modo Visualização</span>
              </div>
            )}
          </div>
        </motion.div>

        {/* Alerts */}
        {alerts && (alerts.overdue_financial > 0 || alerts.trust_reconciliation_pending > 0) && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
          >
            <GlassCard className="border-l-4" style={{ borderLeftColor: premiumTheme.semantic.warning }}>
              <div className="flex items-start space-x-4">
                <AlertCircle size={24} style={{ color: premiumTheme.semantic.warning }} />
                <div className="flex-1">
                  <h3 className="font-semibold mb-2" style={{ color: premiumTheme.text.primary }}>
                    Alertas Financeiros
                  </h3>
                  <div className="space-y-1" style={{ color: premiumTheme.text.secondary }}>
                    {alerts.overdue_financial > 0 && (
                      <p>• {alerts.overdue_financial} fatura(s) vencida(s) pendente(s) de pagamento</p>
                    )}
                    {alerts.trust_reconciliation_pending > 0 && (
                      <p>• {alerts.trust_reconciliation_pending} conta(s) caução pendente(s) de conciliação</p>
                    )}
                  </div>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* KPI Cards */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
        >
          <KPICard
            title="Receitas Totais"
            value={kpis.total_revenue}
            format="currency"
            icon={TrendingUp}
            gradient={premiumTheme.gradients.revenue}
            trend="up"
          />

          <KPICard
            title="Despesas Totais"
            value={kpis.total_expenses}
            format="currency"
            icon={TrendingDown}
            gradient={premiumTheme.gradients.expense}
            trend="down"
          />

          <KPICard
            title="Lucro Líquido"
            value={kpis.net_profit}
            format="currency"
            change={kpis.profit_margin}
            changeLabel={`Margem: ${kpis.profit_margin.toFixed(1)}%`}
            icon={DollarSign}
            gradient={premiumTheme.gradients.gold}
            trend={kpis.net_profit >= 0 ? 'up' : 'down'}
          />

          <KPICard
            title="Total de Registros"
            value={financialRecords.length}
            format="number"
            changeLabel={`${financialRecords.filter(r => r.type === 'income').length} receita(s) / ${financialRecords.filter(r => r.type === 'expense').length} despesa(s)`}
            icon={Clock}
            gradient={premiumTheme.gradients.electric}
            trend="up"
          />
        </motion.div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Cash Flow Chart */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
          >
            <GlassCard>
              <h2 
                className="text-xl font-semibold mb-6"
                style={{ color: premiumTheme.text.primary }}
              >
                Fluxo de Caixa Mensal
              </h2>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={monthly_trend}>
                  <defs>
                    <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={premiumTheme.semantic.success} stopOpacity={0.8}/>
                      <stop offset="95%" stopColor={premiumTheme.semantic.success} stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="expenseGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={premiumTheme.semantic.danger} stopOpacity={0.8}/>
                      <stop offset="95%" stopColor={premiumTheme.semantic.danger} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={premiumTheme.border.secondary} />
                  <XAxis dataKey="month" stroke={premiumTheme.text.tertiary} />
                  <YAxis stroke={premiumTheme.text.tertiary} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: premiumTheme.background.tertiary,
                      border: `1px solid ${premiumTheme.border.primary}`,
                      borderRadius: '8px',
                      color: premiumTheme.text.primary,
                    }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke={premiumTheme.semantic.success}
                    fillOpacity={1}
                    fill="url(#revenueGradient)"
                    name="Receitas"
                  />
                  <Area
                    type="monotone"
                    dataKey="expenses"
                    stroke={premiumTheme.semantic.danger}
                    fillOpacity={1}
                    fill="url(#expenseGradient)"
                    name="Despesas"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </GlassCard>
          </motion.div>

          {/* Profit Trend Chart */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5 }}
          >
            <GlassCard>
              <h2 
                className="text-xl font-semibold mb-6"
                style={{ color: premiumTheme.text.primary }}
              >
                Evolução do Lucro
              </h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={monthly_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke={premiumTheme.border.secondary} />
                  <XAxis dataKey="month" stroke={premiumTheme.text.tertiary} />
                  <YAxis stroke={premiumTheme.text.tertiary} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: premiumTheme.background.tertiary,
                      border: `1px solid ${premiumTheme.border.primary}`,
                      borderRadius: '8px',
                      color: premiumTheme.text.primary,
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="profit"
                    stroke={premiumTheme.gold.matte}
                    strokeWidth={3}
                    dot={{ fill: premiumTheme.gold.matte, r: 5 }}
                    activeDot={{ r: 7 }}
                    name="Lucro"
                  />
                </LineChart>
              </ResponsiveContainer>
            </GlassCard>
          </motion.div>
        </div>

        {/* Monthly Financial Table (Editable for Admin) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <GlassCard>
            <div className="flex items-center justify-between mb-6">
              <h2 
                className="text-xl font-semibold"
                style={{ color: premiumTheme.text.primary }}
              >
                Registros Financeiros Mensais
              </h2>
              {!isAdmin && (
                <span className="text-sm text-blue-400">Somente visualização</span>
              )}
            </div>

            <div className="space-y-6">
              {sortedMonths.map((month) => {
                const monthData = recordsByMonth[month];
                const monthIncome = monthData.income.reduce((sum, r) => sum + r.amount, 0);
                const monthExpense = monthData.expense.reduce((sum, r) => sum + r.amount, 0);
                const monthProfit = monthIncome - monthExpense;
                
                return (
                  <div key={month} className="border border-[#3A3A3A] rounded-lg overflow-hidden">
                    {/* Month Header */}
                    <div className="bg-[#2A2A2A] px-6 py-4 flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <h3 className="text-lg font-bold text-[#F5F5F5]">
                          {new Date(month + '-01').toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })}
                        </h3>
                        <div className="flex items-center space-x-3 text-sm">
                          <span className="text-green-400">
                            ↑ R$ {monthIncome.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                          </span>
                          <span className="text-red-400">
                            ↓ R$ {monthExpense.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                          </span>
                          <span className={monthProfit >= 0 ? 'text-[#D4AF37]' : 'text-red-400'} style={{ fontWeight: 600 }}>
                            = R$ {monthProfit.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Records Table */}
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-[#1E1E1E]">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-[#D4AF37] uppercase">Data</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-[#D4AF37] uppercase">Tipo</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-[#D4AF37] uppercase">Descrição</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-[#D4AF37] uppercase">Categoria</th>
                            <th className="px-4 py-3 text-right text-xs font-medium text-[#D4AF37] uppercase">Valor</th>
                            {isAdmin && (
                              <th className="px-4 py-3 text-center text-xs font-medium text-[#D4AF37] uppercase">Ações</th>
                            )}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#3A3A3A]">
                          {[...monthData.income, ...monthData.expense]
                            .sort((a, b) => new Date(b.date) - new Date(a.date))
                            .map((record) => (
                            <tr key={record.id} className="hover:bg-[#2A2A2A] transition-colors">
                              <td className="px-4 py-3 text-sm text-[#F5F5F5]">
                                {new Date(record.date).toLocaleDateString('pt-BR')}
                              </td>
                              <td className="px-4 py-3">
                                <StatusBadge status={record.type === 'income' ? 'approved' : 'pending'} size="sm" />
                              </td>
                              <td className="px-4 py-3 text-sm text-[#F5F5F5]">{record.description}</td>
                              <td className="px-4 py-3 text-sm text-[#F5F5F5]/60">{record.category}</td>
                              <td className="px-4 py-3 text-right text-sm font-bold">
                                <span className={record.type === 'income' ? 'text-green-400' : 'text-red-400'}>
                                  {record.type === 'income' ? '+' : '-'} R$ {record.amount.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                </span>
                              </td>
                              {isAdmin && (
                                <td className="px-4 py-3 text-center">
                                  <button
                                    onClick={() => handleDeleteRecord(record.id)}
                                    className="p-2 text-red-400 hover:bg-red-900/20 rounded transition-colors"
                                    data-testid={`delete-record-${record.id}`}
                                  >
                                    <Trash2 size={16} />
                                  </button>
                                </td>
                              )}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })}

              {sortedMonths.length === 0 && (
                <div className="text-center py-12">
                  <DollarSign size={48} className="mx-auto mb-4" style={{ color: premiumTheme.gold.matte }} />
                  <p style={{ color: premiumTheme.text.secondary }}>Nenhum registro financeiro</p>
                </div>
              )}
            </div>
          </GlassCard>
        </motion.div>

        {/* Add Record Modal (Admin Only) */}
        {showAddForm && isAdmin && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
            <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl max-w-2xl w-full">
              <div className="border-b border-[#3A3A3A] p-6 flex items-center justify-between">
                <h2 className="text-2xl font-bold text-[#F5F5F5]">Novo Registro Financeiro</h2>
                <button
                  onClick={() => setShowAddForm(false)}
                  className="p-2 hover:bg-[#2A2A2A] rounded-lg transition-colors"
                >
                  <X size={24} className="text-[#F5F5F5]" />
                </button>
              </div>

              <form onSubmit={handleAddRecord} className="p-6 space-y-6">
                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Tipo *</label>
                  <div className="flex space-x-4">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        value="income"
                        checked={newRecord.type === 'income'}
                        onChange={(e) => setNewRecord({ ...newRecord, type: e.target.value })}
                        className="w-4 h-4"
                      />
                      <span className="text-green-400 font-medium">Receita</span>
                    </label>
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        value="expense"
                        checked={newRecord.type === 'expense'}
                        onChange={(e) => setNewRecord({ ...newRecord, type: e.target.value })}
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
                      value={newRecord.amount}
                      onChange={(e) => setNewRecord({ ...newRecord, amount: e.target.value })}
                      required
                      className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Data *</label>
                    <input
                      type="date"
                      value={newRecord.date}
                      onChange={(e) => setNewRecord({ ...newRecord, date: e.target.value })}
                      required
                      className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Descrição *</label>
                  <input
                    type="text"
                    value={newRecord.description}
                    onChange={(e) => setNewRecord({ ...newRecord, description: e.target.value })}
                    required
                    placeholder="Ex: Honorários processo XYZ, Aluguel escritório..."
                    className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Categoria *</label>
                  <input
                    type="text"
                    value={newRecord.category}
                    onChange={(e) => setNewRecord({ ...newRecord, category: e.target.value })}
                    required
                    placeholder="Ex: Honorários, Despesas Operacionais, Marketing..."
                    className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg transition-all"
                >
                  Adicionar Registro
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};
