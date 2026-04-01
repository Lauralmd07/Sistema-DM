import React, { useState, useEffect } from 'react';
import { Layout } from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { 
  Plus, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  AlertCircle,
  FileText,
  Clock,
  Shield
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
import { PremiumTable } from '../components/premium/PremiumTable';
import { StatusBadge } from '../components/premium/StatusBadge';
import { premiumTheme } from '../theme-premium';

export const FinanceiroPremium = () => {
  const { api, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [trustAccounts, setTrustAccounts] = useState([]);

  useEffect(() => {
    if (user?.role === 'admin') {
      loadFinancialData();
    }
  }, [user]);

  const loadFinancialData = async () => {
    try {
      const [analyticsRes, invoicesRes, trustAccountsRes] = await Promise.all([
        api.get('/analytics/dashboard'),
        api.get('/invoices'),
        api.get('/trust-accounts'),
      ]);

      setAnalytics(analyticsRes.data);
      setInvoices(invoicesRes.data);
      setTrustAccounts(trustAccountsRes.data);
    } catch (error) {
      console.error('Error loading financial data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Access control
  if (user?.role !== 'admin') {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <GlassCard className="text-center max-w-md">
            <Shield size={64} className="mx-auto mb-4" style={{ color: premiumTheme.semantic.danger }} />
            <h2 className="text-2xl font-bold mb-2" style={{ color: premiumTheme.text.primary }}>
              Acesso Restrito
            </h2>
            <p style={{ color: premiumTheme.text.secondary }}>
              Apenas administradores podem acessar o módulo financeiro
            </p>
          </GlassCard>
        </div>
      </Layout>
    );
  }

  if (loading || !analytics) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 mx-auto mb-4"
                 style={{ borderColor: premiumTheme.gold.matte }} />
            <p style={{ color: premiumTheme.text.secondary }}>Carregando dados financeiros...</p>
          </div>
        </div>
      </Layout>
    );
  }

  const { kpis, monthly_trend, alerts } = analytics;

  // Invoice table columns
  const invoiceColumns = [
    {
      accessorKey: 'invoice_number',
      header: 'Fatura',
      cell: ({ row }) => (
        <div className="flex items-center space-x-3">
          <FileText size={18} style={{ color: premiumTheme.electric.blue }} />
          <span className="font-medium">{row.original.invoice_number}</span>
        </div>
      ),
    },
    {
      accessorKey: 'client_name',
      header: 'Cliente',
      cell: ({ row }) => (
        <div>
          <div className="font-medium" style={{ color: premiumTheme.text.primary }}>
            {row.original.client_name}
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'issue_date',
      header: 'Emissão',
      cell: ({ row }) => new Date(row.original.issue_date).toLocaleDateString('pt-BR'),
    },
    {
      accessorKey: 'due_date',
      header: 'Vencimento',
      cell: ({ row }) => {
        const dueDate = new Date(row.original.due_date);
        const isOverdue = dueDate < new Date() && row.original.status !== 'paid';
        return (
          <div style={{ color: isOverdue ? premiumTheme.semantic.danger : premiumTheme.text.primary }}>
            {dueDate.toLocaleDateString('pt-BR')}
          </div>
        );
      },
    },
    {
      accessorKey: 'total',
      header: 'Valor',
      cell: ({ row }) => (
        <div className="text-right font-light text-lg">
          R$ {row.original.total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
        </div>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.status} variant="glassmorphic" />,
    },
  ];

  return (
    <Layout>
      <div className="max-w-[1600px] mx-auto space-y-8" data-testid="financeiro-premium-page">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex items-center justify-between mb-2">
            <h1 
              className="text-4xl font-light tracking-tight"
              style={{ 
                color: premiumTheme.text.primary,
                fontFamily: premiumTheme.typography.fontFamily.display 
              }}
            >
              Dashboard Financeiro
            </h1>
            <button
              className="flex items-center space-x-2 px-6 py-3 rounded-lg font-medium transition-all"
              style={{
                background: premiumTheme.gradients.gold,
                color: premiumTheme.background.primary,
              }}
              data-testid="create-invoice-btn"
            >
              <Plus size={20} />
              <span>Nova Fatura</span>
            </button>
          </div>
          <p style={{ color: premiumTheme.text.secondary }}>
            Visão consolidada de receitas, despesas e fluxo de caixa
          </p>
        </motion.div>

        {/* Alerts */}
        {(alerts.overdue_invoices > 0 || alerts.trust_reconciliation_pending > 0) && (
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
                    {alerts.overdue_invoices > 0 && (
                      <p>• {alerts.overdue_invoices} fatura(s) vencida(s) pendente(s) de pagamento</p>
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
            change={15.5}
            icon={TrendingUp}
            gradient={premiumTheme.gradients.revenue}
            trend="up"
          />

          <KPICard
            title="Despesas Totais"
            value={kpis.total_expenses}
            format="currency"
            change={-8.2}
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
            trend="up"
          />

          <KPICard
            title="A Receber"
            value={kpis.receivables}
            format="currency"
            change={5.3}
            changeLabel={`${kpis.overdue_count} vencida(s)`}
            icon={Clock}
            gradient={premiumTheme.gradients.electric}
            trend="down"
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

        {/* Trust Accounts Summary */}
        {trustAccounts.length > 0 && (
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
                  Contas Caução
                </h2>
                <div 
                  className="text-2xl font-light"
                  style={{ color: premiumTheme.gold.matte }}
                >
                  R$ {kpis.trust_accounts_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {trustAccounts.slice(0, 3).map((account) => (
                  <div
                    key={account.id}
                    className="p-4 rounded-lg border"
                    style={{
                      backgroundColor: `${premiumTheme.background.secondary}80`,
                      borderColor: premiumTheme.border.primary,
                    }}
                  >
                    <div className="text-sm mb-1" style={{ color: premiumTheme.text.secondary }}>
                      {account.client_name}
                    </div>
                    <div className="text-lg font-medium mb-2" style={{ color: premiumTheme.text.primary }}>
                      {account.account_number}
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs" style={{ color: premiumTheme.text.tertiary }}>
                        {account.bank_name}
                      </span>
                      <StatusBadge status={account.reconciliation.status} size="sm" />
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* Invoices Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
        >
          <div className="mb-4">
            <h2 
              className="text-xl font-semibold"
              style={{ color: premiumTheme.text.primary }}
            >
              Faturas Recentes
            </h2>
          </div>
          <PremiumTable
            data={invoices.slice(0, 10)}
            columns={invoiceColumns}
            onRowClick={(invoice) => console.log('Invoice clicked:', invoice)}
          />
        </motion.div>
      </div>
    </Layout>
  );
};
