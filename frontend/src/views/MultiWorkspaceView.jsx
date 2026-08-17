import React, { useState, useEffect } from 'react';
import { 
  MessageSquare, X, RefreshCw, FileText, CheckCircle, XCircle, Plus, Eye 
} from 'lucide-react';

function MultiWorkspaceView({
  selectedDocIds,
  setSelectedDocIds,
  documents,
  chatHistory,
  setChatHistory,
  chatLoading,
  chatQuestion,
  setChatQuestion,
  handleChatSubmit,
  chatEndRef,
  setCurrentView,
  API_BASE_URL
}) {
  // Modal state for active preview
  const [previewDoc, setPreviewDoc] = useState(null); // { id, name, type, page }
  const [showAddModal, setShowAddModal] = useState(false);

  // Map selectedDocIds to actual document records
  const selectedDocs = documents.filter(doc => selectedDocIds.includes(doc.id));

  // Documents available to add (not yet selected)
  const addableDocs = documents.filter(doc => !selectedDocIds.includes(doc.id));

  const handleRemoveDoc = (id) => {
    if (selectedDocIds.length <= 1) {
      alert("You must have at least one document in the workspace.");
      return;
    }
    setSelectedDocIds(prev => prev.filter(x => x !== id));
  };

  const handleAddDoc = (id) => {
    setSelectedDocIds(prev => [...prev, id]);
  };

  const handleClearChat = () => {
    setChatHistory([]);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', height: 'calc(100vh - 6rem)' }}>
      {/* Header bar */}
      <div className="panel-header glass-panel" style={{ padding: '0.75rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', overflow: 'hidden' }}>
          <button onClick={() => setCurrentView('library')} className="tab-btn active" style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}>← Library</button>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }} className="truncate">Multi-Document Workspace</h2>
          <span className="status-badge" style={{ backgroundColor: 'rgba(16, 185, 129, 0.08)', color: 'var(--secondary)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
            {selectedDocs.length} Active Files
          </span>
        </div>
        <div className="actions-toolbar" style={{ gap: '0.5rem' }}>
          <button 
            onClick={() => setShowAddModal(true)} 
            className="tab-btn active"
            style={{ fontSize: '0.75rem', padding: '0.4rem 0.8rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
          >
            <Plus size={12} /> Add Files
          </button>
          <button 
            onClick={handleClearChat}
            className="tab-btn"
            style={{ fontSize: '0.75rem', padding: '0.4rem 0.8rem', border: '1px solid var(--border-color)' }}
          >
            Clear History
          </button>
        </div>
      </div>

      <div className="dashboard-layout-grid" style={{ flexGrow: 1, minHeight: 0 }}>
        {/* Left Panel: Active Document List Manager */}
        <div className="workspace-panel glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div className="panel-header" style={{ padding: '0.8rem 1.25rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between' }}>
            <h3 style={{ fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
              Selected Context Sources
            </h3>
          </div>
          <div style={{ flexGrow: 1, overflowY: 'auto', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {selectedDocs.map(doc => (
              <div 
                key={doc.id} 
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between',
                  background: 'rgba(255,255,255,0.02)', 
                  padding: '0.75rem 1rem', 
                  borderRadius: '10px',
                  border: '1px solid var(--border-color)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', overflow: 'hidden', marginRight: '0.5rem' }}>
                  <FileText size={18} style={{ color: 'var(--primary)', flexShrink: 0 }} />
                  <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.85rem' }} className="truncate">
                      {doc.original_filename}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      {doc.document_type} • {doc.size_formatted}
                    </span>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span className={`status-badge ${doc.ocr_status.toLowerCase()}`} style={{ padding: '0.1rem 0.4rem', fontSize: '0.65rem' }}>
                    {doc.ocr_status}
                  </span>
                  <button 
                    onClick={() => handleRemoveDoc(doc.id)} 
                    className="action-btn-circle delete"
                    title="Remove from Workspace"
                    style={{ width: '24px', height: '24px' }}
                  >
                    <X size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Panel: Cross-Document Chat Room */}
        <div className="workspace-panel glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div className="panel-header" style={{ padding: '0.8rem 1.25rem', borderBottom: '1px solid var(--border-color)' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
              <MessageSquare size={14} style={{ color: 'var(--primary)' }} /> AI Cross-Document Assistant
            </h3>
          </div>

          {/* Chat Room History Feed */}
          <div style={{ flexGrow: 1, overflowY: 'auto', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {chatHistory.length === 0 ? (
              <div className="empty-state" style={{ height: '100%', minHeight: 0 }}>
                <div className="empty-state-icon"><MessageSquare size={32} /></div>
                <p style={{ fontWeight: 600 }}>Compare and search files together</p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '-0.75rem' }}>
                  Ask questions about skills, prices, or dates across all selected documents.
                </p>
              </div>
            ) : (
              chatHistory.map((chat, idx) => (
                <div key={idx} className={`chat-bubble ${chat.sender === 'user' ? 'user' : 'ai'}`}>
                  <p style={{ fontSize: '0.85rem', whiteSpace: 'pre-wrap' }}>{chat.text}</p>
                  {chat.sources && chat.sources.length > 0 && (
                    <div style={{ marginTop: '0.6rem', paddingTop: '0.6rem', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase' }}>Source Citations:</span>
                      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                        {chat.sources.map((s, sIdx) => (
                          <button 
                            key={sIdx} 
                            onClick={() => setPreviewDoc({ id: s.document_id, name: s.filename, page: s.page })}
                            className="status-badge" 
                            style={{ 
                              padding: '0.2rem 0.5rem', 
                              fontSize: '0.65rem', 
                              backgroundColor: 'rgba(99,102,241,0.08)', 
                              color: 'var(--primary)', 
                              border: '1px solid rgba(99,102,241,0.2)',
                              cursor: 'pointer',
                              borderRadius: '4px',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.25rem'
                            }}
                          >
                            <Eye size={10} /> {s.filename} (Page {s.page})
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
            {chatLoading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--primary)', fontSize: '0.8rem', paddingLeft: '0.5rem' }}>
                <RefreshCw className="spinner" size={12} />
                Scanning matching collections context...
              </div>
            )}
            <div ref={chatEndRef}></div>
          </div>

          {/* Chat Form panel */}
          <form onSubmit={handleChatSubmit} className="chat-input-area" style={{ padding: '1rem', borderTop: '1px solid var(--border-color)' }}>
            <input 
              type="text" 
              value={chatQuestion}
              onChange={(e) => setChatQuestion(e.target.value)}
              placeholder="Ask a question across active files..."
              className="chat-input"
              style={{ padding: '0.6rem 1rem' }}
              disabled={chatLoading}
            />
            <button 
              type="submit" 
              disabled={chatLoading || !chatQuestion.trim()}
              className="btn-send"
              style={{ width: '40px', height: '40px' }}
            >
              Send
            </button>
          </form>
        </div>
      </div>

      {/* Modal 1: Document Viewer Modal */}
      {previewDoc && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
          backdropFilter: 'blur(8px)'
        }}>
          <div className="glass-panel" style={{
            width: '90%',
            maxWidth: '1000px',
            height: '85vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '1rem 1.5rem',
              borderBottom: '1px solid var(--border-color)'
            }}>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }} className="truncate">{previewDoc.name}</h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Showing Page {previewDoc.page}</span>
              </div>
              <button 
                onClick={() => setPreviewDoc(null)} 
                className="action-btn-circle" 
                style={{ width: '28px', height: '28px', border: 'none' }}
              >
                <X size={14} />
              </button>
            </div>
            
            <div style={{ flexGrow: 1, padding: '1rem', background: '#101726', position: 'relative' }}>
              <iframe 
                src={`${API_BASE_URL}/document/${previewDoc.id}/file#page=${previewDoc.page}`} 
                width="100%" 
                height="100%" 
                style={{ border: 'none', borderRadius: '8px', background: '#1e293b' }}
                title="Preview Page"
              />
            </div>
          </div>
        </div>
      )}

      {/* Modal 2: Add Files Modal */}
      {showAddModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
          backdropFilter: 'blur(8px)'
        }}>
          <div className="glass-panel" style={{
            width: '90%',
            maxWidth: '550px',
            maxHeight: '75vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '1rem 1.5rem',
              borderBottom: '1px solid var(--border-color)'
            }}>
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Add Documents to Workspace</h3>
              <button 
                onClick={() => setShowAddModal(false)} 
                className="action-btn-circle" 
                style={{ width: '28px', height: '28px', border: 'none' }}
              >
                <X size={14} />
              </button>
            </div>
            
            <div style={{ flexGrow: 1, overflowY: 'auto', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {addableDocs.length === 0 ? (
                <p style={{ fontStyle: 'italic', color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
                  All library documents are already in the workspace.
                </p>
              ) : (
                addableDocs.map(doc => (
                  <div 
                    key={doc.id} 
                    style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'space-between',
                      background: 'rgba(255,255,255,0.01)', 
                      padding: '0.6rem 0.8rem', 
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', overflow: 'hidden' }}>
                      <FileText size={16} style={{ color: 'var(--text-secondary)' }} />
                      <span style={{ fontSize: '0.8rem', fontWeight: 500 }} className="truncate">
                        {doc.original_filename}
                      </span>
                    </div>
                    <button 
                      onClick={() => { handleAddDoc(doc.id); setShowAddModal(false); }} 
                      className="tab-btn active"
                      style={{ fontSize: '0.7rem', padding: '0.35rem 0.65rem', display: 'flex', alignItems: 'center', gap: '0.2rem' }}
                    >
                      <Plus size={10} /> Add
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MultiWorkspaceView;
