import React, { useState, useEffect } from 'react';
import { Layout } from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { Calendar, Plus, X, Edit2, Trash2 } from 'lucide-react';

export const Agenda = () => {
  const { api } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [view, setView] = useState('month'); // month or week
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

  const loadAppointments = async () => {
    try {
      const { data } = await api.get('/appointments');
      setAppointments(data);
    } catch (error) {
      console.error('Error loading appointments:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post('/appointments', formData);
      await loadAppointments();
      setShowForm(false);
      resetForm();
    } catch (error) {
      console.error('Error creating appointment:', error);
      alert('Erro ao criar agendamento');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Deseja realmente excluir este agendamento?')) return;
    
    try {
      await api.delete(`/appointments/${id}`);
      await loadAppointments();
    } catch (error) {
      console.error('Error deleting appointment:', error);
      alert('Erro ao excluir agendamento');
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
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  return (
    <Layout>
      <div className="max-w-7xl mx-auto" data-testid="agenda-page">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-[#F5F5F5] mb-2">Agenda de Consultas</h1>
            <p className="text-[#F5F5F5]/60">Gerencie seus agendamentos de primeira consulta e retorno</p>
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

        {/* View Toggle */}
        <div className="flex space-x-2 mb-6">
          <button
            onClick={() => setView('month')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              view === 'month'
                ? 'bg-[#D4AF37] text-[#121212]'
                : 'bg-[#1E1E1E] text-[#F5F5F5] hover:bg-[#2A2A2A]'
            }`}
          >
            Mês
          </button>
          <button
            onClick={() => setView('week')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              view === 'week'
                ? 'bg-[#D4AF37] text-[#121212]'
                : 'bg-[#1E1E1E] text-[#F5F5F5] hover:bg-[#2A2A2A]'
            }`}
          >
            Semana
          </button>
        </div>

        {/* Appointments List */}
        <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-6">
          {loading ? (
            <p className="text-center text-[#F5F5F5]/60 py-8">Carregando...</p>
          ) : appointments.length === 0 ? (
            <div className="text-center py-12">
              <Calendar size={48} className="mx-auto text-[#D4AF37] mb-4" />
              <p className="text-[#F5F5F5]/60">Nenhuma consulta agendada</p>
            </div>
          ) : (
            <div className="space-y-4">
              {appointments.map((appointment) => (
                <div
                  key={appointment.id}
                  className="flex items-center justify-between p-4 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg hover:border-[#D4AF37] transition-all"
                  data-testid={`appointment-card-${appointment.id}`}
                >
                  <div className="flex items-center space-x-4">
                    <div
                      className="w-3 h-12 rounded-full"
                      style={{ backgroundColor: appointment.color }}
                    />
                    <div>
                      <div className="flex items-center space-x-3 mb-1">
                        <h3 className="text-[#F5F5F5] font-bold">{appointment.client_name}</h3>
                        <span className={`px-2 py-1 text-xs font-medium rounded ${
                          appointment.type === 'lead'
                            ? 'bg-blue-900/30 text-blue-400'
                            : 'bg-green-900/30 text-green-400'
                        }`}>
                          {appointment.type === 'lead' ? 'Primeira Consulta' : 'Retorno'}
                        </span>
                      </div>
                      <p className="text-[#F5F5F5]/60 text-sm">{appointment.subject}</p>
                      <p className="text-[#D4AF37] text-sm mt-1">
                        {appointment.phone} • {new Date(appointment.date).toLocaleDateString('pt-BR')} às {appointment.time}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(appointment.id)}
                    className="p-2 text-red-400 hover:bg-red-900/20 rounded-lg transition-colors"
                    data-testid={`delete-appointment-${appointment.id}`}
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

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

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                  <div>
                    <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                      Cor
                    </label>
                    <input
                      type="color"
                      name="color"
                      value={formData.color}
                      onChange={handleChange}
                      className="w-full h-[50px] px-2 py-1 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg cursor-pointer"
                    />
                  </div>
                </div>

                {/* Return Fields */}
                {formData.type === 'return' && (
                  <div className="border-t border-[#3A3A3A] pt-6 mt-6">
                    <h3 className="text-lg font-bold text-[#D4AF37] mb-4">Informações Adicionais (Retorno)</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                          CPF
                        </label>
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
                        <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                          RG
                        </label>
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
