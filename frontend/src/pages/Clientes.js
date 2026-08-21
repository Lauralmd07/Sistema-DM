import React, { useEffect, useState, useCallback } from 'react';
import { Layout } from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { UserPlus, Search, Upload, FileText, Image as ImageIcon, Eye, Trash2, X, UserRound, FolderOpen } from 'lucide-react';

const emptyForm = { full_name: '', identification_number: '', identification_type: 'CPF', birth_date: '', phone: '', email: '', address: '', process_number: '', notes: '' };

export const Clientes = () => {
  const { api } = useAuth();
  const [clients, setClients] = useState([]);
  const [selected, setSelected] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [viewing, setViewing] = useState(null);

  const loadClients = useCallback(async () => {
    try {
      const response = await api.get('/clients');
      setClients(response.data);
      if (selected) {
        const fresh = response.data.find(c => c.id === selected.id);
        setSelected(fresh || null);
      }
    } finally { setLoading(false); }
  }, [api, selected?.id]);

  const loadDocuments = useCallback(async (clientId) => {
    const response = await api.get(`/clients/${clientId}/documents`);
    setDocuments(response.data);
  }, [api]);

  useEffect(() => { loadClients(); }, [loadClients]);
  useEffect(() => { if (selected?.id) loadDocuments(selected.id); else setDocuments([]); }, [selected?.id, loadDocuments]);

  const openNew = () => { setForm(emptyForm); setEditing(false); setShowForm(true); };
  const openEdit = () => { setForm({ ...emptyForm, ...selected }); setEditing(true); setShowForm(true); };

  const saveClient = async (e) => {
    e.preventDefault();
    const payload = { ...form, email: form.email || null };
    if (editing) await api.put(`/clients/${selected.id}`, payload); else await api.post('/clients', payload);
    setShowForm(false);
    await loadClients();
  };

  const removeClient = async () => {
    if (!selected || !window.confirm('Excluir este cliente e todos os documentos vinculados?')) return;
    await api.delete(`/clients/${selected.id}`);
    setSelected(null); setDocuments([]); await loadClients();
  };

  const upload = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file || !selected) return;
    setUploading(true);
    try {
      const data = new FormData(); data.append('file', file);
      await api.post(`/clients/${selected.id}/documents`, data, { headers: { 'Content-Type': 'multipart/form-data' } });
      await loadDocuments(selected.id);
    } catch (error) { alert(error.response?.data?.detail || 'Não foi possível enviar o arquivo.'); }
    finally { setUploading(false); }
  };

  const openDocument = async (doc) => {
    const response = await api.get(`/clients/${selected.id}/documents/${doc.id}`);
    setViewing(response.data);
  };

  const removeDocument = async (doc) => {
    if (!window.confirm('Excluir este documento?')) return;
    await api.delete(`/clients/${selected.id}/documents/${doc.id}`);
    await loadDocuments(selected.id);
  };

  const filtered = clients.filter(c => `${c.full_name} ${c.identification_number} ${c.process_number || ''}`.toLowerCase().includes(search.toLowerCase()));

  const input = (name, label, required = false, type = 'text') => (
    <div>
      <label className="block text-sm font-medium text-[#F5F5F5] mb-2">{label}{required ? ' *' : ''}</label>
      <input type={type} required={required} value={form[name] || ''} onChange={e => setForm({ ...form, [name]: e.target.value })} className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]" />
    </div>
  );

  return (
    <Layout>
      <div className="max-w-7xl mx-auto" data-testid="clientes-page">
        <div className="flex items-center justify-between mb-8">
          <div><h1 className="text-3xl font-bold text-[#F5F5F5] mb-2">Clientes</h1><p className="text-[#F5F5F5]/60">Cadastro, dados pessoais e documentos em um único lugar.</p></div>
          <button onClick={openNew} className="flex items-center gap-2 px-5 py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg"><UserPlus size={19} /> Novo cliente</button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[330px_1fr] gap-6">
          <section className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl overflow-hidden">
            <div className="p-4 border-b border-[#3A3A3A]"><div className="relative"><Search size={18} className="absolute left-3 top-3 text-[#F5F5F5]/40" /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar cliente..." className="w-full pl-10 pr-3 py-2.5 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] outline-none" /></div></div>
            <div className="max-h-[650px] overflow-y-auto">
              {loading ? <p className="p-6 text-[#F5F5F5]/50 text-center">Carregando...</p> : filtered.length === 0 ? <div className="p-8 text-center"><UserRound size={38} className="mx-auto text-[#D4AF37] mb-3" /><p className="text-[#F5F5F5]/50">Nenhum cliente cadastrado.</p></div> : filtered.map(client => (
                <button key={client.id} onClick={() => setSelected(client)} className={`w-full text-left p-4 border-b border-[#3A3A3A] hover:bg-[#2A2A2A] ${selected?.id === client.id ? 'bg-[#2A2A2A] border-l-2 border-l-[#D4AF37]' : ''}`}>
                  <p className="font-semibold text-[#F5F5F5] truncate">{client.full_name}</p><p className="text-xs text-[#F5F5F5]/50 mt-1">{client.identification_type}: {client.identification_number}</p>
                  {client.process_number && <p className="text-xs text-[#D4AF37] mt-1">Processo: {client.process_number}</p>}
                </button>
              ))}
            </div>
          </section>

          <section className="min-w-0">
            {!selected ? <div className="h-full min-h-[500px] bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl flex flex-col items-center justify-center text-center p-10"><FolderOpen size={56} className="text-[#D4AF37] mb-4" /><h2 className="text-xl font-semibold">Selecione um cliente</h2><p className="text-[#F5F5F5]/50 mt-2">Os dados pessoais, processo e documentos aparecerão aqui.</p></div> : <>
              <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-6 mb-6">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                  <div className="flex items-start gap-4"><div className="w-14 h-14 rounded-full bg-[#D4AF37] flex items-center justify-center"><UserRound size={27} className="text-[#121212]" /></div><div><h2 className="text-2xl font-bold text-[#F5F5F5]">{selected.full_name}</h2><div className="flex flex-wrap gap-x-5 gap-y-1 mt-2 text-sm text-[#F5F5F5]/60"><span><strong className="text-[#F5F5F5]">{selected.identification_type}:</strong> {selected.identification_number}</span>{selected.process_number && <span><strong className="text-[#F5F5F5]">Processo:</strong> {selected.process_number}</span>}</div></div></div>
                  <div className="flex gap-2"><button onClick={openEdit} className="px-4 py-2 border border-[#3A3A3A] rounded-lg hover:bg-[#2A2A2A]">Editar</button><button onClick={removeClient} className="px-4 py-2 text-red-400 border border-red-900/50 rounded-lg hover:bg-red-900/20">Excluir</button></div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6 pt-5 border-t border-[#3A3A3A] text-sm"><div><span className="text-[#F5F5F5]/40">Telefone</span><p className="mt-1">{selected.phone || '—'}</p></div><div><span className="text-[#F5F5F5]/40">E-mail</span><p className="mt-1 break-all">{selected.email || '—'}</p></div><div><span className="text-[#F5F5F5]/40">Endereço</span><p className="mt-1">{selected.address || '—'}</p></div></div>
              </div>

              <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-6">
                <div className="flex items-center justify-between mb-5"><div><h3 className="text-xl font-bold">Documentos do cliente</h3><p className="text-sm text-[#F5F5F5]/50 mt-1">Todos os arquivos ficam vinculados a {selected.full_name}.</p></div><label className={`flex items-center gap-2 px-4 py-2.5 bg-[#D4AF37] text-[#121212] font-bold rounded-lg cursor-pointer ${uploading ? 'opacity-50 pointer-events-none' : ''}`}><Upload size={18} /> {uploading ? 'Enviando...' : 'Adicionar documento'}<input type="file" className="hidden" onChange={upload} /></label></div>
                {documents.length === 0 ? <div className="border border-dashed border-[#3A3A3A] rounded-lg p-10 text-center"><FileText size={42} className="mx-auto text-[#F5F5F5]/20 mb-3" /><p className="text-[#F5F5F5]/50">Nenhum documento cadastrado para este cliente.</p></div> : <div className="grid grid-cols-1 md:grid-cols-2 gap-3">{documents.map(doc => <div key={doc.id} className="bg-[#121212] border border-[#3A3A3A] rounded-lg p-4 flex items-center gap-3"><div className="w-10 h-10 rounded-lg bg-[#2A2A2A] flex items-center justify-center">{doc.file_type?.startsWith('image/') ? <ImageIcon size={19} className="text-[#D4AF37]" /> : <FileText size={19} className="text-[#D4AF37]" />}</div><div className="min-w-0 flex-1"><p className="font-medium truncate">{doc.filename}</p><p className="text-xs text-[#F5F5F5]/40 mt-1">{(doc.file_size / 1024 / 1024).toFixed(2)} MB • {new Date(doc.created_at).toLocaleDateString('pt-BR')}</p></div><button onClick={() => openDocument(doc)} title="Ver" className="p-2 hover:bg-[#2A2A2A] rounded"><Eye size={17} className="text-[#D4AF37]" /></button><button onClick={() => removeDocument(doc)} title="Excluir" className="p-2 hover:bg-red-900/20 rounded"><Trash2 size={17} className="text-red-400" /></button></div>)}</div>}
              </div>
            </>}
          </section>
        </div>

        {showForm && <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"><div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto"><div className="p-6 border-b border-[#3A3A3A] flex justify-between"><div><h2 className="text-2xl font-bold">{editing ? 'Editar cliente' : 'Cadastrar cliente'}</h2><p className="text-sm text-[#F5F5F5]/50 mt-1">Dados pessoais e identificação.</p></div><button onClick={() => setShowForm(false)}><X /></button></div><form onSubmit={saveClient} className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">{input('full_name','Nome completo',true)}<div><label className="block text-sm font-medium mb-2">Tipo de identificação *</label><select value={form.identification_type} onChange={e => setForm({ ...form, identification_type: e.target.value })} className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5]"><option>CPF</option><option>CNPJ</option><option>RG</option><option>Outro</option></select></div>{input('identification_number','Número de identificação',true)}{input('birth_date','Data de nascimento',false,'date')}{input('phone','Telefone')}{input('email','E-mail',false,'email')}{input('address','Endereço')}{input('process_number','Número do processo')}
                <div className="md:col-span-2"><label className="block text-sm font-medium mb-2">Observações</label><textarea value={form.notes || ''} onChange={e => setForm({ ...form, notes: e.target.value })} rows="3" className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5]" /></div><div className="md:col-span-2 flex justify-end gap-3 pt-2"><button type="button" onClick={() => setShowForm(false)} className="px-5 py-3 border border-[#3A3A3A] rounded-lg">Cancelar</button><button className="px-6 py-3 bg-[#D4AF37] text-[#121212] font-bold rounded-lg">{editing ? 'Salvar alterações' : 'Cadastrar cliente'}</button></div></form></div></div>}

        {viewing && <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4"><div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl w-full max-w-5xl max-h-[90vh] overflow-hidden"><div className="p-4 border-b border-[#3A3A3A] flex justify-between items-center"><div><p className="font-bold">{viewing.filename}</p><p className="text-xs text-[#F5F5F5]/40">{selected.full_name}</p></div><button onClick={() => setViewing(null)}><X /></button></div><div className="p-4 bg-[#121212] overflow-auto max-h-[80vh]">{viewing.file_type?.startsWith('image/') ? <img src={`data:${viewing.file_type};base64,${viewing.file_data}`} alt={viewing.filename} className="max-w-full max-h-[70vh] mx-auto" /> : viewing.file_type === 'application/pdf' ? <iframe src={`data:application/pdf;base64,${viewing.file_data}`} title={viewing.filename} className="w-full h-[70vh]" /> : <div className="text-center py-16"><FileText size={56} className="mx-auto text-[#D4AF37] mb-4" /><p className="text-[#F5F5F5]/60">Pré-visualização não disponível para este tipo de arquivo.</p></div>}</div></div></div>}
      </div>
    </Layout>
  );
};
