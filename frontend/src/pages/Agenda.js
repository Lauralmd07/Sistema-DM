import React, { useState, useEffect, useCallback } from 'react';
import { Layout } from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { Calendar, momentLocalizer } from 'react-big-calendar';
import moment from 'moment';
import 'moment/locale/pt-br';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { Plus, X, Trash2, User, Phone, FileText, Calendar as CalendarIcon, IdCard, Scale, Gavel } from 'lucide-react';

moment.locale('pt-br');
const localizer = momentLocalizer(moment);

const initialForm = () => ({
  type: 'lead',
  client_name: '',
  phone: '',
  subject: '',
  date: moment().format('YYYY-MM-DD'),
  time: moment().add(1, 'hour').format('HH:00'),
  color: '#D4AF37',
  cpf: '',
  rg: '',
  address: '',
  process_number: '',
  court: '',
});

const customStyles = `
.rbc-calendar{background:#1E1E1E;color:#F5F5F5;font-family:Inter,sans-serif}.rbc-header{background:#0A0E17;color:#D4AF37;border-color:#3A3A3A;padding:12px 8px;font-weight:600;text-transform:uppercase;font-size:11px}.rbc-today{background:rgba(74,158,255,.08)}.rbc-off-range{color:#475569}.rbc-off-range-bg{background:#0A0E17}.rbc-date-cell{color:#F5F5F5;padding:8px}.rbc-day-bg{background:#121212;border-color:#3A3A3A}.rbc-month-view,.rbc-time-view{background:#121212;border:1px solid #3A3A3A;border-radius:12px;overflow:hidden}.rbc-time-header,.rbc-time-content,.rbc-timeslot-group{border-color:#3A3A3A}.rbc-time-slot{color:#94A3B8;border-color:#2A2A2A}.rbc-current-time-indicator{background:#D4AF37;height:2px}.rbc-event{background:#D4AF37;color:#121212;border:none;border-radius:6px;padding:4px 8px;font-size:13px;font-weight:500}.rbc-toolbar{padding:16px;background:#1E1E1E;border:1px solid #3A3A3A;border-radius:12px;margin-bottom:16px}.rbc-toolbar button{color:#F5F5F5;background:#2A2A2A;border:1px solid #3A3A3A;padding:8px 16px;border-radius:8px;font-weight:500}.rbc-toolbar button:hover{background:#3A3A3A;border-color:#D4AF37}.rbc-toolbar button.rbc-active{background:#D4AF37;color:#121212;border-color:#D4AF37}.rbc-toolbar-label{color:#F5F5F5;font-size:18px;font-weight:600}
`;

export const Agenda = () => {
  const { api } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [view, setView] = useState('week');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState(initialForm());

  const loadAppointments = useCallback(async () => {
    try {
      const { data } = await api.get('/appointments');
      setAppointments(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Erro ao carregar agenda:', err);
      setError(err.response?.data?.detail || 'Não foi possível carregar a agenda.');
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => { loadAppointments(); }, [loadAppointments]);

  useEffect(() => {
    setEvents(appointments.map(apt => {
      const start = moment(`${apt.date} ${apt.time}`, 'YYYY-MM-DD HH:mm').toDate();
      return {
        id: apt.id,
        title: apt.type === 'hearing' ? `⚖️ ${apt.client_name} - ${apt.process_number || apt.subject}` : `${apt.client_name} - ${apt.subject}`,
        start,
        end: moment(start).add(1, 'hour').toDate(),
        resource: apt,
      };
    }));
  }, [appointments]);

  const openNew = useCallback(() => {
    setEditingId(null);
    setSelectedEvent(null);
    setError('');
    setFormData(initialForm());
    setShowForm(true);
  }, []);

  const handleSelectSlot = useCallback(({ start }) => {
    setEditingId(null);
    setSelectedEvent(null);
    setError('');
    setFormData({
      ...initialForm(),
      date: moment(start).format('YYYY-MM-DD'),
      time: moment(start).format('HH:mm'),
    });
    setShowForm(true);
  }, []);

  const handleSelectEvent = useCallback(event => {
    setSelectedEvent(event.resource);
  }, []);

  const handleEdit = () => {
    if (!selectedEvent) return;
    setEditingId(selectedEvent.id);
    setFormData({ ...initialForm(), ...selectedEvent });
    setSelectedEvent(null);
    setError('');
    setShowForm(true);
  };

  const handleDelete = async () => {
    if (!selectedEvent || !window.confirm(`Deseja realmente excluir o compromisso de ${selectedEvent.client_name}?`)) return;
    try {
      await api.delete(`/appointments/${selectedEvent.id}`);
      setSelectedEvent(null);
      await loadAppointments();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao excluir compromisso.');
    }
  };

  const reset = () => {
    setShowForm(false);
    setEditingId(null);
    setError('');
    setFormData(initialForm());
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setSaving(true);
    setError('');

    const payload = {
      type: String(formData.type || 'lead').trim(),
      client_name: String(formData.client_name || '').trim(),
      phone: String(formData.phone || '').trim(),
      subject: String(formData.subject || '').trim() || 'Compromisso',
      date: String(formData.date || '').trim(),
      time: String(formData.time || '').trim(),
      color: formData.color || '#D4AF37',
      cpf: String(formData.cpf || '').trim(),
      rg: String(formData.rg || '').trim(),
      address: String(formData.address || '').trim(),
      process_number: String(formData.process_number || '').trim(),
      court: String(formData.court || '').trim(),
    };

    const missing = [];
    if (!payload.type) missing.push('tipo');
    if (!payload.client_name) missing.push('nome do cliente');
    if (!payload.date) missing.push('data');
    if (!payload.time) missing.push('hora');
    if (!payload.subject) missing.push('assunto');
    if (payload.type !== 'hearing' && !payload.phone) missing.push('telefone');
    if (payload.type === 'hearing' && !payload.process_number) missing.push('número do processo');
    if (payload.type === 'hearing' && !payload.court) missing.push('órgão julgador');

    if (missing.length) {
      setError(`Preencha: ${missing.join(', ')}.`);
      setSaving(false);
      return;
    }

    try {
      if (editingId) {
        await api.put(`/appointments/${editingId}`, payload);
      } else {
        await api.post('/appointments', payload);
      }
      await loadAppointments();
      reset();
    } catch (err) {
      console.error('Erro ao salvar agendamento:', err);
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map(item => item.msg || item.detail || 'Dados inválidos').join(' | '));
      } else {
        setError(detail || `Erro ${err.response?.status || ''} ao salvar agendamento.`);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleChange = e => setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));

  const messages = { allDay:'Dia inteiro', previous:'Anterior', next:'Próximo', today:'Hoje', month:'Mês', week:'Semana', day:'Dia', agenda:'Agenda', date:'Data', time:'Hora', event:'Evento', noEventsInRange:'Não há eventos neste período', showMore: total => `+${total} mais` };

  return (
    <Layout>
      <style>{customStyles}</style>
      <div className="max-w-[1800px] mx-auto" data-testid="agenda-page">
        <div className="flex items-center justify-between mb-6">
          <div><h1 className="text-3xl font-bold text-[#F5F5F5] mb-2">Agenda de Consultas</h1><p className="text-[#F5F5F5]/60">Gerencie seus compromissos e audiências.</p></div>
          <button onClick={openNew} data-testid="add-appointment-btn" className="flex items-center gap-2 px-6 py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg"><Plus size={20}/> Novo Compromisso</button>
        </div>

        {error && !showForm && <div className="mb-4 p-4 bg-red-900/20 border border-red-500/50 rounded-lg text-red-300">{error}</div>}

        {loading ? <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-[#D4AF37]"/></div> : <div style={{height:'calc(100vh - 300px)',minHeight:'600px'}}><Calendar localizer={localizer} events={events} startAccessor="start" endAccessor="end" style={{height:'100%'}} view={view} onView={setView} views={['month','week','day','agenda']} messages={messages} selectable onSelectSlot={handleSelectSlot} onSelectEvent={handleSelectEvent} popup step={30} timeslots={2} defaultDate={new Date()} scrollToTime={moment().set({hour:8,minute:0}).toDate()}/></div>}

        {showForm && <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-[#1E1E1E] border-b border-[#3A3A3A] p-6 flex items-center justify-between"><h2 className="text-2xl font-bold">{editingId ? 'Editar Compromisso' : 'Novo Compromisso'}</h2><button onClick={reset}><X/></button></div>
            {error && <div className="mx-6 mt-5 p-3 bg-red-900/20 border border-red-500/50 rounded-lg text-red-300 text-sm">{error}</div>}
            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div><label className="block text-sm mb-2">Tipo</label><div className="flex gap-5 flex-wrap">{[['lead','Primeira Consulta'],['return','Retorno'],['hearing','Audiência']].map(([value,label])=><label key={value} className="flex items-center gap-2"><input type="radio" name="type" value={value} checked={formData.type===value} onChange={handleChange}/><span className={value==='hearing'?'text-[#D4AF37]':''}>{label}</span></label>)}</div></div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label="Nome do Cliente *" name="client_name" value={formData.client_name} onChange={handleChange} required />
                <Field label={formData.type==='hearing'?'Telefone':'Telefone *'} name="phone" value={formData.phone} onChange={handleChange} required={formData.type!=='hearing'} type="tel" />
              </div>
              <Field label="Assunto *" name="subject" value={formData.subject} onChange={handleChange} required />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4"><Field label="Data *" name="date" value={formData.date} onChange={handleChange} required type="date"/><Field label="Hora *" name="time" value={formData.time} onChange={handleChange} required type="time"/></div>
              {formData.type==='hearing' && <div className="border-t border-[#3A3A3A] pt-5 grid grid-cols-1 md:grid-cols-2 gap-4"><Field label="Número do Processo *" name="process_number" value={formData.process_number} onChange={handleChange} required/><Field label="Órgão Julgador *" name="court" value={formData.court} onChange={handleChange} required/></div>}
              {formData.type==='return' && <div className="border-t border-[#3A3A3A] pt-5 space-y-4"><div className="grid grid-cols-1 md:grid-cols-2 gap-4"><Field label="CPF" name="cpf" value={formData.cpf} onChange={handleChange}/><Field label="RG" name="rg" value={formData.rg} onChange={handleChange}/></div><div><label className="block text-sm mb-2">Endereço Completo</label><textarea name="address" value={formData.address} onChange={handleChange} rows="3" className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5]"/></div></div>}
              <button type="submit" disabled={saving} data-testid="appointment-submit-btn" className="w-full py-3 bg-[#D4AF37] hover:bg-[#E5C158] disabled:opacity-50 text-[#121212] font-bold rounded-lg">{saving ? 'Salvando...' : editingId ? 'Salvar Alterações' : 'Criar Agendamento'}</button>
            </form>
          </div>
        </div>}

        {selectedEvent && <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={()=>setSelectedEvent(null)}><div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl max-w-lg w-full" onClick={e=>e.stopPropagation()}>
          <div className="p-6 border-b border-[#3A3A3A] flex justify-between"><h2 className="text-xl font-bold">{selectedEvent.type==='lead'?'Primeira Consulta':selectedEvent.type==='hearing'?'Audiência':'Retorno'}</h2><button onClick={()=>setSelectedEvent(null)}><X/></button></div>
          <div className="p-6 space-y-4"><Info icon={User} label="Cliente" value={selectedEvent.client_name}/><Info icon={Phone} label="Telefone" value={selectedEvent.phone}/><Info icon={FileText} label="Assunto" value={selectedEvent.subject}/>{selectedEvent.process_number&&<Info icon={Scale} label="Processo" value={selectedEvent.process_number}/>} {selectedEvent.court&&<Info icon={Gavel} label="Órgão Julgador" value={selectedEvent.court}/>}<Info icon={CalendarIcon} label="Data e Hora" value={moment(`${selectedEvent.date} ${selectedEvent.time}`,'YYYY-MM-DD HH:mm').format('DD/MM/YYYY [às] HH:mm')}/>{(selectedEvent.cpf||selectedEvent.rg)&&<Info icon={IdCard} label="Documentos" value={`CPF: ${selectedEvent.cpf||'—'} | RG: ${selectedEvent.rg||'—'}`}/>}</div>
          <div className="p-6 pt-0 flex gap-3"><button onClick={handleEdit} className="flex-1 py-3 bg-[#D4AF37] text-[#121212] font-bold rounded-lg">Editar</button><button onClick={handleDelete} className="px-4 py-3 border border-red-500/40 text-red-400 rounded-lg"><Trash2 size={18}/></button></div>
        </div></div>}
      </div>
    </Layout>
  );
};

const Field = ({label,name,value,onChange,required=false,type='text'}) => <div><label className="block text-sm mb-2">{label}</label><input type={type} name={name} value={value||''} onChange={onChange} required={required} className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"/></div>;
const Info = ({icon:Icon,label,value}) => <div className="flex gap-3"><Icon size={18} className="text-[#D4AF37] mt-0.5"/><div><p className="text-xs uppercase text-[#F5F5F5]/50">{label}</p><p className="font-medium">{value||'—'}</p></div></div>;
