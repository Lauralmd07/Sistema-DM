import React, { useState, useEffect, useCallback } from 'react';
import { Layout } from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { Calendar, momentLocalizer } from 'react-big-calendar';
import moment from 'moment';
import 'moment/locale/pt-br';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { Plus, X } from 'lucide-react';

// Configure moment locale
moment.locale('pt-br');
const localizer = momentLocalizer(moment);

// Custom styles for the calendar
const customStyles = `
  .rbc-calendar {
    background-color: #1E1E1E;
    color: #F5F5F5;
    font-family: Inter, sans-serif;
  }
  
  .rbc-header {
    background-color: #0A0E17;
    color: #D4AF37;
    border-color: #3A3A3A;
    padding: 12px 8px;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
  }
  
  .rbc-today {
    background-color: rgba(74, 158, 255, 0.08);
  }
  
  .rbc-off-range {
    color: #475569;
  }
  
  .rbc-off-range-bg {
    background-color: #0A0E17;
  }
  
  .rbc-date-cell {
    color: #F5F5F5;
    padding: 8px;
  }
  
  .rbc-day-bg {
    background-color: #121212;
    border-color: #3A3A3A;
  }
  
  .rbc-month-view {
    background-color: #121212;
    border: 1px solid #3A3A3A;
    border-radius: 12px;
    overflow: hidden;
  }
  
  .rbc-time-view {
    background-color: #121212;
    border: 1px solid #3A3A3A;
    border-radius: 12px;
    overflow: hidden;
  }
  
  .rbc-time-header {
    background-color: #1E1E1E;
    border-color: #3A3A3A;
  }
  
  .rbc-time-content {
    border-color: #3A3A3A;
  }
  
  .rbc-timeslot-group {
    border-color: #3A3A3A;
  }
  
  .rbc-time-slot {
    color: #94A3B8;
    border-color: #2A2A2A;
  }
  
  .rbc-current-time-indicator {
    background-color: #D4AF37;
    height: 2px;
  }
  
  .rbc-event {
    background-color: #D4AF37;
    color: #121212;
    border: none;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 13px;
    font-weight: 500;
  }
  
  .rbc-event.lead-event {
    background: linear-gradient(135deg, #4A9EFF 0%, #3B82F6 100%);
    color: white;
  }
  
  .rbc-event.return-event {
    background: linear-gradient(135deg, #2DD4BF 0%, #14B8A6 100%);
    color: white;
  }
  
  .rbc-event:hover {
    opacity: 0.9;
  }
  
  .rbc-event-label {
    font-size: 11px;
  }
  
  .rbc-event-content {
    font-size: 13px;
  }
  
  .rbc-toolbar {
    padding: 16px;
    background-color: #1E1E1E;
    border: 1px solid #3A3A3A;
    border-radius: 12px;
    margin-bottom: 16px;
  }
  
  .rbc-toolbar button {
    color: #F5F5F5;
    background-color: #2A2A2A;
    border: 1px solid #3A3A3A;
    padding: 8px 16px;
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.2s;
  }
  
  .rbc-toolbar button:hover {
    background-color: #3A3A3A;
    border-color: #D4AF37;
  }
  
  .rbc-toolbar button:active,
  .rbc-toolbar button.rbc-active {
    background-color: #D4AF37;
    color: #121212;
    border-color: #D4AF37;
  }
  
  .rbc-toolbar-label {
    color: #F5F5F5;
    font-size: 18px;
    font-weight: 600;
  }
`;

export const Agenda = () => {
  const { api } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [view, setView] = useState('week');
  const [formData, setFormData] = useState({
    type: 'lead',
    client_name: '',
    phone: '',
    subject: '',
    date: '',
    time: '',
    color: '#D4AF37',
    cpf: '',
    rg: '',
    address: '',
  });

  useEffect(() => {
    loadAppointments();
  }, []);

  useEffect(() => {
    // Convert appointments to calendar events
    const calendarEvents = appointments.map(apt => {
      const startDateTime = moment(`${apt.date} ${apt.time}`, 'YYYY-MM-DD HH:mm').toDate();
      const endDateTime = moment(startDateTime).add(1, 'hour').toDate(); // Default 1 hour duration
      
      return {
        id: apt.id,
        title: `${apt.client_name} - ${apt.subject}`,
        start: startDateTime,
        end: endDateTime,
        resource: apt,
        className: apt.type === 'lead' ? 'lead-event' : 'return-event',
      };
    });
    
    setEvents(calendarEvents);
  }, [appointments]);

  const loadAppointments = async () => {
    try {
      const { data } = await api.get('/appointments');
      setAppointments(data);
    } catch (error) {
      // Error loading appointments
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSlot = useCallback(({ start, end }) => {
    const startMoment = moment(start);
    setSelectedSlot({ start, end });
    setFormData(prev => ({
      ...prev,
      date: startMoment.format('YYYY-MM-DD'),
      time: startMoment.format('HH:mm'),
    }));
    setShowForm(true);
  }, []);

  const handleSelectEvent = useCallback((event) => {
    // Event details can be shown in a modal
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post('/appointments', formData);
      await loadAppointments();
      setShowForm(false);
      resetForm();
    } catch (error) {
      alert('Erro ao criar agendamento');
    }
  };

  const resetForm = () => {
    setFormData({
      type: 'lead',
      client_name: '',
      phone: '',
      subject: '',
      date: '',
      time: '',
      color: '#D4AF37',
      cpf: '',
      rg: '',
      address: '',
    });
    setSelectedSlot(null);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  // Custom event style getter
  const eventStyleGetter = (event) => {
    const backgroundColor = event.resource.type === 'lead' 
      ? '#4A9EFF' 
      : '#2DD4BF';
    
    return {
      style: {
        backgroundColor,
        borderRadius: '6px',
        opacity: 0.9,
        color: 'white',
        border: 'none',
        display: 'block',
      }
    };
  };

  // Messages in Portuguese
  const messages = {
    allDay: 'Dia inteiro',
    previous: 'Anterior',
    next: 'Próximo',
    today: 'Hoje',
    month: 'Mês',
    week: 'Semana',
    day: 'Dia',
    agenda: 'Agenda',
    date: 'Data',
    time: 'Hora',
    event: 'Evento',
    noEventsInRange: 'Não há eventos neste período',
    showMore: (total) => `+${total} mais`,
  };

  return (
    <Layout>
      <style>{customStyles}</style>
      
      <div className="max-w-[1800px] mx-auto" data-testid="agenda-page">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-[#F5F5F5] mb-2">Agenda de Consultas</h1>
            <p className="text-[#F5F5F5]/60">Gerencie seus agendamentos - clique em um horário para criar</p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            data-testid="add-appointment-btn"
            className="flex items-center space-x-2 px-6 py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg transition-all"
          >
            <Plus size={20} />
            <span>Nova Consulta</span>
          </button>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-6 mb-4 p-4 bg-[#1E1E1E] border border-[#3A3A3A] rounded-lg">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded" style={{ background: 'linear-gradient(135deg, #4A9EFF 0%, #3B82F6 100%)' }}></div>
            <span className="text-sm text-[#F5F5F5]">Primeira Consulta (Lead)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded" style={{ background: 'linear-gradient(135deg, #2DD4BF 0%, #14B8A6 100%)' }}></div>
            <span className="text-sm text-[#F5F5F5]">Retorno</span>
          </div>
        </div>

        {/* Calendar */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-[#D4AF37]"></div>
          </div>
        ) : (
          <div style={{ height: 'calc(100vh - 300px)', minHeight: '600px' }}>
            <Calendar
              localizer={localizer}
              events={events}
              startAccessor="start"
              endAccessor="end"
              style={{ height: '100%' }}
              view={view}
              onView={setView}
              views={['month', 'week', 'day', 'agenda']}
              messages={messages}
              selectable
              onSelectSlot={handleSelectSlot}
              onSelectEvent={handleSelectEvent}
              eventPropGetter={eventStyleGetter}
              popup
              step={30}
              timeslots={2}
              defaultDate={new Date()}
              scrollToTime={moment().set({ hour: 8, minute: 0 }).toDate()}
            />
          </div>
        )}

        {/* Form Modal */}
        {showForm && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
            <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="sticky top-0 bg-[#1E1E1E] border-b border-[#3A3A3A] p-6 flex items-center justify-between">
                <h2 className="text-2xl font-bold text-[#F5F5F5]">Nova Consulta</h2>
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
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                    Tipo de Consulta
                  </label>
                  <div className="flex space-x-4">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        name="type"
                        value="lead"
                        checked={formData.type === 'lead'}
                        onChange={handleChange}
                        className="w-4 h-4"
                      />
                      <span className="text-[#F5F5F5]">Primeira Consulta</span>
                    </label>
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        name="type"
                        value="return"
                        checked={formData.type === 'return'}
                        onChange={handleChange}
                        className="w-4 h-4"
                      />
                      <span className="text-[#F5F5F5]">Retorno</span>
                    </label>
                  </div>
                </div>

                {/* Basic Fields */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                      Nome do Cliente *
                    </label>
                    <input
                      type="text"
                      name="client_name"
                      value={formData.client_name}
                      onChange={handleChange}
                      required
                      data-testid="appointment-client-name"
                      className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                      Telefone *
                    </label>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      required
                      data-testid="appointment-phone"
                      className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                    Assunto *
                  </label>
                  <input
                    type="text"
                    name="subject"
                    value={formData.subject}
                    onChange={handleChange}
                    required
                    data-testid="appointment-subject"
                    className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                      Data *
                    </label>
                    <input
                      type="date"
                      name="date"
                      value={formData.date}
                      onChange={handleChange}
                      required
                      data-testid="appointment-date"
                      className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                      Hora *
                    </label>
                    <input
                      type="time"
                      name="time"
                      value={formData.time}
                      onChange={handleChange}
                      required
                      data-testid="appointment-time"
                      className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                    />
                  </div>
                </div>

                {/* Return Fields */}
                {formData.type === 'return' && (
                  <div className="border-t border-[#3A3A3A] pt-6 mt-6">
                    <h3 className="text-lg font-bold text-[#D4AF37] mb-4">Informações Adicionais (Retorno)</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-[#F5F5F5] mb-2">CPF</label>
                        <input
                          type="text"
                          name="cpf"
                          value={formData.cpf}
                          onChange={handleChange}
                          data-testid="appointment-cpf"
                          className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[#F5F5F5] mb-2">RG</label>
                        <input
                          type="text"
                          name="rg"
                          value={formData.rg}
                          onChange={handleChange}
                          data-testid="appointment-rg"
                          className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                        />
                      </div>
                    </div>
                    <div className="mt-4">
                      <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                        Endereço Completo
                      </label>
                      <textarea
                        name="address"
                        value={formData.address}
                        onChange={handleChange}
                        rows={3}
                        data-testid="appointment-address"
                        className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                      />
                    </div>
                  </div>
                )}

                <button
                  type="submit"
                  data-testid="appointment-submit-btn"
                  className="w-full py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg transition-all"
                >
                  Criar Agendamento
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};
