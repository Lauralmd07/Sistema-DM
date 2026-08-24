import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Layout } from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { Plus, X, Trash2, Check, CalendarDays, Gavel, Clock3, AlertTriangle } from 'lucide-react';
import moment from 'moment';

const emptyForm = () => ({
  title: '', date: moment().format('YYYY-MM-DD'), time: '23:59', type: 'prazo', priority: 'normal',
  client_name: '', process_number: '', notes: '', status: 'pending'
});

const deadlineTypes = [
  ['prazo', 'Prazo processual'], ['peticao', 'Petição'], ['contestacao', 'Contestação'], ['recurso', 'Recurso'], ['outro', 'Outro']
];

const priorityLabel = { baixa: 'Baixa', normal: 'Normal', alta: 'Alta', urgente: 'Urgente' };

export const PrazosAudiencias = () => {
  const { api } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [deadlines, setDeadlines] = useState([]);
  const [tab, setTab] = useState('upcoming');
  const [showDeadline, setShowDeadline] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [appointmentsResponse, deadlinesResponse] = await Promise.all([
        api.get('/appointments'), api.get('/deadlines')
      ]);
      setAppointments(Array.isArray(appointmentsResponse.data) ? appointmentsResponse.data : []);
      setDeadlines(Array.isArray(deadlinesResponse.data) ? deadlinesResponse.data : []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Não foi possível carregar prazos e audiências.');
    } finally { setLoading(false); }
  }, [api]);

  useEffect(() => { load(); }, [load]);

  const hearings = useMemo(() => appointments.filter(a => a.type === 'hearing'), [appointments]);
  const today = moment().startOf('day');
  const upcomingDeadlines = deadlines.filter(d => d.status === 'pending' && !moment(d.date).isBefore(today, 'day'));
  const overdue = deadlines.filter(d => d.status === 'pending' && moment(d.date).isBefore(today, 'day'));
  const visibleDeadlines = tab === 'overdue' ? overdue : tab === 'completed' ? deadlines.filter(d => d.status === 'completed') : upcomingDeadlines;

  const openNew = () => { setEditingId(null); setForm(emptyForm()); setError(''); setShowDeadline(true); };
  const openEdit = d => { setEditingId(d.id); setForm({ ...emptyForm(), ...d }); setError(''); setShowDeadline(true); };
  const closeForm = () => { setShowDeadline(false); setEditingId(null); setForm(emptyForm()); };

  const saveDeadline = async e => {
    e.preventDefault(); setSaving(true); setError('');
    try {
      const payload = { ...form, title: form.title.trim(), client_name: form.client_name.trim(), process_number: form.process_number.trim(), notes: form.notes.trim() };
      if (!payload.title) throw new Error('Informe a descrição do prazo.');
      if (editingId) await api.put(`/deadlines/${editingId}`, payload); else await api.post('/deadlines', payload);
      closeForm(); await load();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Não foi possível salvar o prazo.');
    } finally { setSaving(false); }
  };

  const removeDeadline = async id => {
    if (!window.confirm('Deseja excluir este prazo?')) return;
    try { await api.delete(`/deadlines/${id}`); await load(); } catch (err) { setError(err.response?.data?.detail || 'Não foi possível excluir o prazo.'); }
  };

  const completeDeadline = async d => {
    try { await api.put(`/deadlines/${d.id}`, { ...d, status: d.status === 'completed' ? 'pending' : 'completed' }); await load(); }
    catch (err) { setError(err.response?.data?.detail || 'Não foi possível alterar o status.'); }
  };

  const formatDate = value => moment(value).format('DD/MM/YYYY');
  const daysUntil = value => {
    const days = moment(value).startOf('day').diff(today, 'days');
    if (days < 0) return `${Math.abs(days)} dia(s) em atraso`;
    if (days === 0) return 'Vence hoje';
    if (days === 1) return 'Vence amanhã';
    return `Em ${days} dias`;
  };

  return <Layout>
    <div className="max-w-7xl mx-auto" data-testid="prazos-audiencias-page">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-7">
        <div><h1 className="text-3xl font-bold text-[#F5F5F5]">Prazos e Audiências</h1><p className="text-[#F5F5F5]/60 mt-1">Controle compromissos processuais e audiências em um só lugar.</p></div>
        <div className="flex gap-3"><button onClick={openNew} className="flex items-center gap-2 px-5 py-3 bg-[#D4AF37] text-[#121212] font-bold rounded-lg"><Plus size={19}/> Novo Prazo</button></div>
      </div>

      {error && <div className="mb-5 p-4 bg-red-900/20 border border-red-500/50 rounded-lg text-red-300">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-7">
        <Stat icon={Clock3} title="Prazos em aberto" value={upcomingDeadlines.length}/>
        <Stat icon={AlertTriangle} title="Prazos vencidos" value={overdue.length}/>
        <Stat icon={Gavel} title="Audiências" value={hearings.length}/>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-5">
          <div className="flex items-center justify-between mb-4"><h2 className="text-xl font-bold flex items-center gap-2"><Clock3 className="text-[#D4AF37]"/> Prazos</h2><div className="flex gap-1 text-xs"><Tab active={tab==='upcoming'} onClick={()=>setTab('upcoming')}>Próximos</Tab><Tab active={tab==='overdue'} onClick={()=>setTab('overdue')}>Vencidos</Tab><Tab active={tab==='completed'} onClick={()=>setTab('completed')}>Concluídos</Tab></div></div>
          {loading ? <p className="py-10 text-center text-white/50">Carregando...</p> : visibleDeadlines.length === 0 ? <p className="py-10 text-center text-white/40">Nenhum prazo nesta categoria.</p> : <div className="space-y-3">{visibleDeadlines.map(d => <div key={d.id} className="border border-[#3A3A3A] rounded-lg p-4 bg-[#151515]">
            <div className="flex items-start justify-between gap-3"><div><h3 className={`font-semibold ${d.status==='completed'?'line-through text-white/40':''}`}>{d.title}</h3><p className="text-sm text-white/50 mt-1">{formatDate(d.date)} às {d.time}</p></div><span className={`text-xs px-2 py-1 rounded-full ${d.priority==='urgente'?'bg-red-900/50 text-red-300':d.priority==='alta'?'bg-orange-900/50 text-orange-300':'bg-[#2A2A2A] text-white/70'}`}>{priorityLabel[d.priority] || d.priority}</span></div>
            {(d.client_name || d.process_number) && <p className="text-sm text-white/65 mt-3">{d.client_name || 'Sem cliente'} {d.process_number ? `• ${d.process_number}` : ''}</p>}
            <p className={`text-xs mt-2 ${overdue.some(x=>x.id===d.id)?'text-red-400':'text-[#D4AF37]'}`}>{daysUntil(d.date)}</p>
            <div className="flex gap-2 mt-4"><button onClick={()=>completeDeadline(d)} className="flex-1 py-2 rounded bg-[#2A2A2A] hover:bg-[#333] text-sm flex justify-center items-center gap-2"><Check size={15}/>{d.status==='completed'?'Reabrir':'Concluir'}</button><button onClick={()=>openEdit(d)} className="px-3 py-2 rounded bg-[#2A2A2A] text-sm">Editar</button><button onClick={()=>removeDeadline(d.id)} className="px-3 py-2 rounded bg-red-900/30 text-red-300"><Trash2 size={16}/></button></div>
          </div>)}</div>}
        </section>

        <section className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-5">
          <div className="flex items-center justify-between mb-4"><h2 className="text-xl font-bold flex items-center gap-2"><Gavel className="text-[#D4AF37]"/> Audiências</h2><a href="#/agenda" className="text-sm text-[#D4AF37]">Abrir agenda</a></div>
          {loading ? <p className="py-10 text-center text-white/50">Carregando...</p> : hearings.length === 0 ? <p className="py-10 text-center text-white/40">Nenhuma audiência cadastrada.</p> : <div className="space-y-3">{hearings.map(h => <div key={h.id} className="border border-[#3A3A3A] rounded-lg p-4 bg-[#151515]"><div className="flex items-start justify-between"><div><h3 className="font-semibold">{h.client_name}</h3><p className="text-sm text-white/60 mt-1">{h.subject}</p></div><span className="text-xs px-2 py-1 rounded-full bg-[#D4AF37]/15 text-[#D4AF37]">Audiência</span></div><div className="mt-3 flex flex-wrap gap-3 text-sm text-white/60"><span className="flex items-center gap-1"><CalendarDays size={15}/> {formatDate(h.date)}</span><span>{h.time}</span></div>{h.process_number && <p className="text-xs text-white/45 mt-2">Processo: {h.process_number}{h.court ? ` • ${h.court}` : ''}</p>}</div>)}</div>}
        </section>
      </div>

      {showDeadline && <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"><div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"><div className="sticky top-0 bg-[#1E1E1E] border-b border-[#3A3A3A] p-5 flex justify-between items-center"><h2 className="text-xl font-bold">{editingId?'Editar Prazo':'Novo Prazo'}</h2><button onClick={closeForm}><X/></button></div><form onSubmit={saveDeadline} className="p-5 space-y-4">
        <Field label="Descrição do prazo *" name="title" value={form.title} onChange={e=>setForm({...form,[e.target.name]:e.target.value})} required />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4"><Field label="Data *" type="date" name="date" value={form.date} onChange={e=>setForm({...form,[e.target.name]:e.target.value})} required/><Field label="Hora limite" type="time" name="time" value={form.time} onChange={e=>setForm({...form,[e.target.name]:e.target.value})} required/></div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4"><Select label="Tipo" name="type" value={form.type} onChange={e=>setForm({...form,[e.target.name]:e.target.value})} options={deadlineTypes}/><Select label="Prioridade" name="priority" value={form.priority} onChange={e=>setForm({...form,[e.target.name]:e.target.value})} options={['baixa','normal','alta','urgente'].map(x=>[x,priorityLabel[x]])}/></div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4"><Field label="Cliente" name="client_name" value={form.client_name} onChange={e=>setForm({...form,[e.target.name]:e.target.value})}/><Field label="Número do processo" name="process_number" value={form.process_number} onChange={e=>setForm({...form,[e.target.name]:e.target.value})}/></div>
        <div><label className="block text-sm mb-2">Observações</label><textarea rows="4" name="notes" value={form.notes} onChange={e=>setForm({...form,[e.target.name]:e.target.value})} className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-white"/></div>
        <button disabled={saving} className="w-full py-3 bg-[#D4AF37] text-[#121212] font-bold rounded-lg disabled:opacity-50">{saving?'Salvando...':editingId?'Salvar alterações':'Criar prazo'}</button>
      </form></div></div>}
    </div>
  </Layout>;
};

const Field = ({label,...props}) => <div><label className="block text-sm mb-2">{label}</label><input {...props} className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-white"/></div>;
const Select = ({label,options,...props}) => <div><label className="block text-sm mb-2">{label}</label><select {...props} className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-white">{options.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></div>;
const Tab = ({active,children,...props}) => <button {...props} className={`px-2 py-1 rounded ${active?'bg-[#D4AF37] text-[#121212]':'text-white/60 hover:text-white'}`}>{children}</button>;
const Stat = ({icon:Icon,title,value}) => <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-5 flex items-center gap-4"><div className="p-3 rounded-lg bg-[#D4AF37]/10 text-[#D4AF37]"><Icon size={22}/></div><div><p className="text-sm text-white/50">{title}</p><p className="text-2xl font-bold mt-1">{value}</p></div></div>;
