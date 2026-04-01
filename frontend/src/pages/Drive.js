import React, { useState, useEffect } from 'react';
import { Layout } from '../components/Layout';
import { useAuth } from '../contexts/AuthContext';
import { FolderPlus, Upload, File, FileText, Image as ImageIcon, Trash2, Eye, X, Folder } from 'lucide-react';

export const Drive = () => {
  const { api } = useAuth();
  const [folders, setFolders] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showFolderForm, setShowFolderForm] = useState(false);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [viewingDocument, setViewingDocument] = useState(null);
  const [folderFormData, setFolderFormData] = useState({
    name: '',
    type: 'client',
    reference_id: '',
  });
  const [uploadFile, setUploadFile] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [foldersRes, documentsRes] = await Promise.all([
        api.get('/folders'),
        api.get('/documents'),
      ]);
      setFolders(foldersRes.data);
      setDocuments(documentsRes.data);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateFolder = async (e) => {
    e.preventDefault();
    try {
      await api.post('/folders', folderFormData);
      await loadData();
      setShowFolderForm(false);
      setFolderFormData({ name: '', type: 'client', reference_id: '' });
    } catch (error) {
      console.error('Error creating folder:', error);
      alert('Erro ao criar pasta');
    }
  };

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    if (!uploadFile || !selectedFolder) return;

    try {
      const formData = new FormData();
      formData.append('folder_id', selectedFolder);
      formData.append('file', uploadFile);

      await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      await loadData();
      setShowUploadForm(false);
      setUploadFile(null);
      setSelectedFolder(null);
    } catch (error) {
      console.error('Error uploading document:', error);
      alert('Erro ao fazer upload do documento');
    }
  };

  const handleDeleteFolder = async (folderId) => {
    if (!window.confirm('Deseja realmente excluir esta pasta e todos os documentos?')) return;

    try {
      await api.delete(`/folders/${folderId}`);
      await loadData();
    } catch (error) {
      console.error('Error deleting folder:', error);
      alert('Erro ao excluir pasta');
    }
  };

  const handleDeleteDocument = async (documentId) => {
    if (!window.confirm('Deseja realmente excluir este documento?')) return;

    try {
      await api.delete(`/documents/${documentId}`);
      await loadData();
    } catch (error) {
      console.error('Error deleting document:', error);
      alert('Erro ao excluir documento');
    }
  };

  const getFileIcon = (fileType) => {
    if (fileType?.includes('image')) return <ImageIcon size={20} className="text-blue-400" />;
    if (fileType?.includes('pdf')) return <FileText size={20} className="text-red-400" />;
    return <File size={20} className="text-gray-400" />;
  };

  const renderDocumentPreview = (doc) => {
    if (!doc) return null;

    if (doc.file_type?.includes('image')) {
      return (
        <img
          src={`data:${doc.file_type};base64,${doc.file_data}`}
          alt={doc.filename}
          className="max-w-full max-h-[70vh] mx-auto rounded"
        />
      );
    }

    if (doc.file_type?.includes('pdf')) {
      return (
        <iframe
          src={`data:application/pdf;base64,${doc.file_data}`}
          title={doc.filename}
          className="w-full h-[70vh] rounded border border-[#3A3A3A]"
        />
      );
    }

    return (
      <div className="text-center py-12">
        <FileText size={64} className="mx-auto text-[#D4AF37] mb-4" />
        <p className="text-[#F5F5F5]/60">Pré-visualização não disponível para este tipo de arquivo</p>
        <p className="text-sm text-[#D4AF37] mt-2">{doc.filename}</p>
      </div>
    );
  };

  return (
    <Layout>
      <div className="max-w-7xl mx-auto" data-testid="drive-page">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-[#F5F5F5] mb-2">Drive Jurídico</h1>
            <p className="text-[#F5F5F5]/60">Gerencie documentos por cliente ou processo</p>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={() => setShowFolderForm(true)}
              data-testid="create-folder-btn"
              className="flex items-center space-x-2 px-6 py-3 bg-[#1E1E1E] hover:bg-[#2A2A2A] border border-[#3A3A3A] text-[#F5F5F5] font-bold rounded-lg transition-all"
            >
              <FolderPlus size={20} />
              <span>Nova Pasta</span>
            </button>
            <button
              onClick={() => setShowUploadForm(true)}
              data-testid="upload-document-btn"
              className="flex items-center space-x-2 px-6 py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg transition-all"
            >
              <Upload size={20} />
              <span>Upload</span>
            </button>
          </div>
        </div>

        {loading ? (
          <p className="text-center text-[#F5F5F5]/60 py-8">Carregando...</p>
        ) : (
          <div className="space-y-8">
            {/* Folders */}
            <div>
              <h2 className="text-xl font-bold text-[#F5F5F5] mb-4">Pastas</h2>
              {folders.length === 0 ? (
                <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-12 text-center">
                  <Folder size={48} className="mx-auto text-[#D4AF37] mb-4" />
                  <p className="text-[#F5F5F5]/60">Nenhuma pasta criada</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {folders.map((folder) => {
                    const folderDocs = documents.filter(d => d.folder_id === folder.id);
                    return (
                      <div
                        key={folder.id}
                        className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-6 hover:border-[#D4AF37] transition-all group"
                        data-testid={`folder-${folder.id}`}
                      >
                        <div className="flex items-start justify-between mb-3">
                          <Folder size={32} className="text-[#D4AF37]" />
                          <button
                            onClick={() => handleDeleteFolder(folder.id)}
                            className="opacity-0 group-hover:opacity-100 p-1 text-red-400 hover:bg-red-900/20 rounded transition-all"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                        <h3 className="text-[#F5F5F5] font-bold mb-1">{folder.name}</h3>
                        <p className="text-xs text-[#F5F5F5]/60 mb-2 capitalize">{folder.type}</p>
                        <p className="text-xs text-[#D4AF37]">{folderDocs.length} documentos</p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Documents */}
            <div>
              <h2 className="text-xl font-bold text-[#F5F5F5] mb-4">Documentos</h2>
              {documents.length === 0 ? (
                <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-12 text-center">
                  <FileText size={48} className="mx-auto text-[#D4AF37] mb-4" />
                  <p className="text-[#F5F5F5]/60">Nenhum documento enviado</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl p-4 hover:border-[#D4AF37] transition-all"
                      data-testid={`document-${doc.id}`}
                    >
                      <div className="flex items-start space-x-3">
                        {getFileIcon(doc.file_type)}
                        <div className="flex-1 min-w-0">
                          <h3 className="text-[#F5F5F5] font-medium text-sm truncate mb-1">
                            {doc.filename}
                          </h3>
                          <p className="text-xs text-[#F5F5F5]/60">
                            {new Date(doc.created_at).toLocaleDateString('pt-BR')}
                          </p>
                        </div>
                      </div>
                      <div className="flex space-x-2 mt-4">
                        <button
                          onClick={() => setViewingDocument(doc)}
                          className="flex-1 flex items-center justify-center space-x-2 px-3 py-2 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] rounded text-sm font-medium transition-colors"
                        >
                          <Eye size={14} />
                          <span>Ver</span>
                        </button>
                        <button
                          onClick={() => handleDeleteDocument(doc.id)}
                          className="px-3 py-2 bg-red-900/20 hover:bg-red-900/40 text-red-400 rounded transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Folder Form Modal */}
        {showFolderForm && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
            <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl max-w-md w-full">
              <div className="border-b border-[#3A3A3A] p-6 flex items-center justify-between">
                <h2 className="text-2xl font-bold text-[#F5F5F5]">Nova Pasta</h2>
                <button onClick={() => setShowFolderForm(false)} className="p-2 hover:bg-[#2A2A2A] rounded-lg">
                  <X size={24} className="text-[#F5F5F5]" />
                </button>
              </div>
              <form onSubmit={handleCreateFolder} className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Nome da Pasta *</label>
                  <input
                    type="text"
                    value={folderFormData.name}
                    onChange={(e) => setFolderFormData({ ...folderFormData, name: e.target.value })}
                    required
                    data-testid="folder-name-input"
                    className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Tipo *</label>
                  <select
                    value={folderFormData.type}
                    onChange={(e) => setFolderFormData({ ...folderFormData, type: e.target.value })}
                    className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                  >
                    <option value="client">Cliente</option>
                    <option value="process">Processo</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">ID de Referência *</label>
                  <input
                    type="text"
                    value={folderFormData.reference_id}
                    onChange={(e) => setFolderFormData({ ...folderFormData, reference_id: e.target.value })}
                    required
                    placeholder="Ex: CPF do cliente ou número do processo"
                    className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg transition-all"
                >
                  Criar Pasta
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Upload Form Modal */}
        {showUploadForm && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
            <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-xl max-w-md w-full">
              <div className="border-b border-[#3A3A3A] p-6 flex items-center justify-between">
                <h2 className="text-2xl font-bold text-[#F5F5F5]">Upload Documento</h2>
                <button onClick={() => setShowUploadForm(false)} className="p-2 hover:bg-[#2A2A2A] rounded-lg">
                  <X size={24} className="text-[#F5F5F5]" />
                </button>
              </div>
              <form onSubmit={handleUploadDocument} className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Selecionar Pasta *</label>
                  <select
                    value={selectedFolder || ''}
                    onChange={(e) => setSelectedFolder(e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37]"
                  >
                    <option value="">Escolha uma pasta...</option>
                    {folders.map((folder) => (
                      <option key={folder.id} value={folder.id}>
                        {folder.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Arquivo *</label>
                  <input
                    type="file"
                    onChange={(e) => setUploadFile(e.target.files[0])}
                    required
                    data-testid="file-upload-input"
                    accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                    className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37] file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-[#D4AF37] file:text-[#121212] file:font-medium hover:file:bg-[#E5C158]"
                  />
                </div>
                <button
                  type="submit"
                  data-testid="upload-submit-btn"
                  className="w-full py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg transition-all"
                >
                  Fazer Upload
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Document Viewer Modal */}
        {viewingDocument && (
          <div className="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4">
            <div className="w-full max-w-5xl max-h-[90vh]">
              <div className="bg-[#1E1E1E] border border-[#3A3A3A] rounded-t-xl p-4 flex items-center justify-between">
                <h3 className="text-[#F5F5F5] font-bold">{viewingDocument.filename}</h3>
                <button
                  onClick={() => setViewingDocument(null)}
                  className="p-2 hover:bg-[#2A2A2A] rounded-lg transition-colors"
                >
                  <X size={24} className="text-[#F5F5F5]" />
                </button>
              </div>
              <div className="bg-[#121212] p-4 rounded-b-xl">
                {renderDocumentPreview(viewingDocument)}
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};