import React, { useState, useEffect, useCallback } from 'react';
import { Layout } from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { Plus, X, GripVertical, Clock, FileText } from 'lucide-react';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
} from '@dnd-kit/core';
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// Droppable Column Component
const DroppableColumn = ({ id, children, title, color, count }) => {
  const { setNodeRef, isOver } = useDroppable({ id });
  
  return (
    <div
      ref={setNodeRef}
      className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-4 transition-all"
      style={{
        borderColor: isOver ? '#D4AF37' : '#3A3A3A',
        backgroundColor: isOver ? 'rgba(212, 175, 55, 0.05)' : '#1E1E1E',
      }}
      data-testid={`kanban-column-${id}`}
    >
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#3A3A3A]">
        <div className="flex items-center space-x-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: color }}
          />
          <h2 className="text-lg font-bold text-[#F5F5F5]">{title}</h2>
        </div>
        <span className="px-2 py-1 bg-[#2A2A2A] text-[#D4AF37] text-sm font-bold rounded">
          {count}
        </span>
      </div>
      <div className="space-y-3 min-h-[400px]">
        {children}
      </div>
    </div>
  );
};

// Sortable Process Card Component
const ProcessCard = ({ process, onUpdate }) => {
  const [showDetails, setShowDetails] = useState(false);
  const [timelineEntry, setTimelineEntry] = useState({ date: '', description: '' });
  const [judgeSentence, setJudgeSentence] = useState(process.judge_sentence || '');

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: process.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const handleAddTimeline = async () => {
    if (!timelineEntry.date || !timelineEntry.description) return;
    
    const updatedTimeline = [...(process.timeline || []), timelineEntry];
    await onUpdate(process.id, { timeline: updatedTimeline });
    setTimelineEntry({ date: '', description: '' });
  };

  const handleSaveSentence = async () => {
    await onUpdate(process.id, { judge_sentence: judgeSentence });
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg p-4 hover:border-[#D4AF37] transition-all"
      data-testid={`process-card-${process.id}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start space-x-3 flex-1">
          <button
            {...attributes}
            {...listeners}
            className="mt-1 cursor-grab active:cursor-grabbing text-[#D4AF37] hover:text-[#E5C158] touch-none"
          >
            <GripVertical size={20} />
          </button>
          <div className="flex-1">
            <h3 className="text-[#F5F5F5] font-bold mb-1">
              Cliente #{process.client_number}
            </h3>
            <p className="text-[#F5F5F5]/60 text-sm mb-1">CPF: {process.cpf}</p>
            <p className="text-[#D4AF37] text-sm font-medium">{process.action_type}</p>
          </div>
        </div>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="px-3 py-1 text-xs bg-[#1E1E1E] text-[#D4AF37] rounded hover:bg-[#3A3A3A] transition-colors"
        >
          {showDetails ? 'Ocultar' : 'Detalhes'}
        </button>
      </div>

      {showDetails && (
        <div className="mt-4 pt-4 border-t border-[#3A3A3A]">
          <p className="text-[#F5F5F5]/80 text-sm mb-4">{process.description}</p>

          {/* Timeline for In Progress */}
          {process.status === 'in_progress' && (
            <div className="space-y-3">
              <h4 className="text-[#D4AF37] font-medium flex items-center space-x-2">
                <Clock size={16} />
                <span>Linha do Tempo</span>
              </h4>

              {process.timeline && process.timeline.length > 0 && (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {process.timeline.map((entry, idx) => (
                    <div key={idx} className="bg-[#1E1E1E] p-3 rounded">
                      <p className="text-xs text-[#D4AF37] mb-1">
                        {new Date(entry.date).toLocaleDateString('pt-BR')}
                      </p>
                      <p className="text-sm text-[#F5F5F5]">{entry.description}</p>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex space-x-2">
                <input
                  type="date"
                  value={timelineEntry.date}
                  onChange={(e) => setTimelineEntry({ ...timelineEntry, date: e.target.value })}
                  className="flex-1 px-3 py-2 bg-[#1E1E1E] border border-[#3A3A3A] rounded text-[#F5F5F5] text-sm focus:outline-none focus:ring-1 focus:ring-[#D4AF37]"
                />
              </div>
              <div className="flex space-x-2">
                <input
                  type="text"
                  placeholder="Descrição da atualização..."
                  value={timelineEntry.description}
                  onChange={(e) => setTimelineEntry({ ...timelineEntry, description: e.target.value })}
                  className="flex-1 px-3 py-2 bg-[#1E1E1E] border border-[#3A3A3A] rounded text-[#F5F5F5] text-sm focus:outline-none focus:ring-1 focus:ring-[#D4AF37]"
                />
                <button
                  onClick={handleAddTimeline}
                  className="px-4 py-2 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] rounded text-sm font-medium transition-colors"
                >
                  Adicionar
                </button>
              </div>
            </div>
          )}

          {/* Judge Sentence for Finished */}
          {process.status === 'finished' && (
            <div className="space-y-3">
              <h4 className="text-green-400 font-medium flex items-center space-x-2">
                <FileText size={16} />
                <span>Sentença do Juiz</span>
              </h4>
              <textarea
                value={judgeSentence}
                onChange={(e) => setJudgeSentence(e.target.value)}
                placeholder="Digite a sentença final do juiz..."
                rows={4}
                className="w-full px-3 py-2 bg-[#1E1E1E] border border-[#3A3A3A] rounded text-[#F5F5F5] text-sm focus:outline-none focus:ring-1 focus:ring-green-400 resize-none"
              />
              <button
                onClick={handleSaveSentence}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded text-sm font-medium transition-colors"
              >
                Salvar Sentença
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const Processos = () => {
  const { api } = useAuth();
  const [processes, setProcesses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [activeId, setActiveId] = useState(null);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    client_number: '',
    cpf: '',
    action_type: '',
    description: '',
  });

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const loadProcesses = useCallback(async () => {
    try {
      const { data } = await api.get('/processes');
      setProcesses(data);
    } catch (error) {
      setError(error.response?.data?.detail || 'Não foi possível carregar os processos.');
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    loadProcesses();
  }, [loadProcesses]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setError('');
      await api.post('/processes', formData);
      await loadProcesses();
      setShowForm(false);
      resetForm();
    } catch (error) {
      setError(error.response?.data?.detail || 'Não foi possível criar o processo.');
    }
  };

  const resetForm = () => {
    setFormData({
      client_number: '',
      cpf: '',
      action_type: '',
      description: '',
    });
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleDragStart = (event) => {
    setActiveId(event.active.id);
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    
    setActiveId(null);
    
    if (!over) return;

    const activeProcess = processes.find(p => p.id === active.id);
    
    // Check if dropping on a column
    if (over.id && ['new', 'in_progress', 'finished'].includes(over.id)) {
      if (activeProcess && activeProcess.status !== over.id) {
        try {
          await api.put(`/processes/${activeProcess.id}`, { status: over.id });
          await loadProcesses();
        } catch (error) {
          setError(error.response?.data?.detail || 'Não foi possível atualizar o status do processo.');
        }
      }
    }
  };

  const handleUpdateProcess = async (id, updates) => {
    try {
      await api.put(`/processes/${id}`, updates);
      await loadProcesses();
    } catch (error) {
      setError(error.response?.data?.detail || 'Não foi possível atualizar o processo.');
    }
  };

  const columns = [
    { id: 'new', title: 'Novos', color: '#2196F3' },
    { id: 'in_progress', title: 'Em Andamento', color: '#FF9800' },
    { id: 'finished', title: 'Finalizados', color: '#4CAF50' },
  ];

  const activeProcess = activeId ? processes.find(p => p.id === activeId) : null;

  return (
    <Layout>
      <div className="max-w-full mx-auto" data-testid="processos-page">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-[#F5F5F5] mb-2">Gestão de Processos</h1>
            <p className="text-[#F5F5F5]/60">Kanban drag-and-drop para gerenciar processos</p>
          </div>
          <button
            onClick={() => setShowForm(true)}
            data-testid="add-process-btn"
            className="flex items-center space-x-2 px-6 py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg transition-all"
          >
            <Plus size={20} />
            <span>Novo Processo</span>
          </button>
        </div>

        {error && <div className="mb-6 p-4 bg-red-900/20 border border-red-500/50 rounded-lg text-red-300">{error}</div>}

        {/* Kanban Board */}
        {loading ? (
          <p className="text-center text-[#F5F5F5]/60 py-8">Carregando...</p>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {columns.map((column) => {
                const columnProcesses = processes.filter(p => p.status === column.id);
                
                return (
                  <DroppableColumn
                    key={column.id}
                    id={column.id}
                    title={column.title}
                    color={column.color}
                    count={columnProcesses.length}
                  >
                    <SortableContext
                      items={columnProcesses.map(p => p.id)}
                      strategy={verticalListSortingStrategy}
                    >
                      {columnProcesses.length === 0 ? (
                        <p className="text-center text-[#F5F5F5]/40 text-sm py-8">
                          Arraste processos para cá
                        </p>
                      ) : (
                        columnProcesses.map((process) => (
                          <ProcessCard
                            key={process.id}
                            process={process}
                            onUpdate={handleUpdateProcess}
                          />
                        ))
                      )}
                    </SortableContext>
                  </DroppableColumn>
                );
              })}
            </div>
            
            <DragOverlay>
              {activeProcess ? (
                <div className="bg-[#2A2A2A] border-2 border-[#D4AF37] rounded-lg p-4 shadow-2xl">
                  <div className="flex items-start space-x-3">
                    <GripVertical size={20} className="text-[#D4AF37]" />
                    <div>
                      <h3 className="text-[#F5F5F5] font-bold">Cliente #{activeProcess.client_number}</h3>
                      <p className="text-[#D4AF37] text-sm">{activeProcess.action_type}</p>
                    </div>
                  </div>
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
        )}

        {/* Form Modal */}
        {showForm && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
            <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="sticky top-0 bg-[#1E1E1E] border-b border-[#3A3A3A] p-6 flex items-center justify-between">
                <h2 className="text-2xl font-bold text-[#F5F5F5]">Novo Processo</h2>
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
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                      Número do Cliente *
                    </label>
                    <input
                      type="text"
                      name="client_number"
                      value={formData.client_number}
                      onChange={handleChange}
                      required
                      data-testid="process-client-number"
                      className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                      CPF *
                    </label>
                    <input
                      type="text"
                      name="cpf"
                      value={formData.cpf}
                      onChange={handleChange}
                      required
                      data-testid="process-cpf"
                      className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                    Tipo de Ação *
                  </label>
                  <input
                    type="text"
                    name="action_type"
                    value={formData.action_type}
                    onChange={handleChange}
                    required
                    data-testid="process-action-type"
                    placeholder="Ex: Ação Trabalhista, Divórcio, etc."
                    className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                    Descrição *
                  </label>
                  <textarea
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    required
                    rows={4}
                    data-testid="process-description"
                    placeholder="Descreva os detalhes do processo..."
                    className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37] resize-none"
                  />
                </div>

                <button
                  type="submit"
                  data-testid="process-submit-btn"
                  className="w-full py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg transition-all"
                >
                  Criar Processo
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};
