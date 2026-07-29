import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Download, Layers, XCircle, RefreshCw, MessageSquare, CheckCircle, Edit2, Save, X 
} from 'lucide-react';

function WorkspaceView({
  selectedDoc,
  selectedDocId,
  activeUploads,
  docTab,
  setDocTab,
  extractedLoading,
  extractedData,
  chatHistory,
  chatLoading,
  chatQuestion,
  setChatQuestion,
  handleChatSubmit,
  chatEndRef,
  setCurrentView,
  API_BASE_URL
}) {
  // Local state for interactive editing & citations
  const [isEditing, setIsEditing] = useState(false);
  const [editableFields, setEditableFields] = useState({});
  const [editLoading, setEditLoading] = useState(false);
  const [activePage, setActivePage] = useState(1);
  const [saveStatus, setSaveStatus] = useState(null);

  // Initialize editable fields whenever extractedData changes
  useEffect(() => {
    if (extractedData) {
      setEditableFields(extractedData);
    }
  }, [extractedData]);

  // Handle saveStatus timeout clear
  useEffect(() => {
    if (saveStatus) {
      const timer = setTimeout(() => setSaveStatus(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [saveStatus]);

  const handleFieldChange = (key, value) => {
    setEditableFields(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSaveChanges = async () => {
    setEditLoading(true);
    setSaveStatus(null);
    try {
      const token = localStorage.getItem('access_token');
      await axios.post(`${API_BASE_URL}/document/${selectedDocId}/update-json`, editableFields, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setIsEditing(false);
      setSaveStatus({ type: 'success', message: 'Structured data saved successfully!' });
    } catch (err) {
      console.error('Failed to update structured fields:', err);
      setSaveStatus({ type: 'error', message: 'Failed to update fields. Please check format.' });
    }
    setEditLoading(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', height: 'calc(100vh - 6rem)' }}>
      <div className="panel-header glass-panel" style={{ padding: '0.75rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', overflow: 'hidden' }}>
          <button onClick={() => setCurrentView('library')} className="tab-btn active" style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}>← Library</button>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }} className="truncate">{selectedDoc.original_filename || selectedDoc.filename}</h2>
          <span className="status-badge" style={{ backgroundColor: 'rgba(99, 102, 241, 0.08)', color: 'var(--primary)', border: '1px solid rgba(99, 102, 241, 0.2)' }}>{selectedDoc.file_type.toUpperCase()}</span>
        </div>
        <div className="actions-toolbar">
          <a 
            href={`${API_BASE_URL}/document/${selectedDocId}/download-text`}
            className="tab-btn active"
            style={{ fontSize: '0.75rem', padding: '0.4rem 0.8rem' }}
          >
            <Download size={12} /> Text
          </a>
          <a 
            href={`${API_BASE_URL}/document/${selectedDocId}/download-json`}
            className="tab-btn active"
            style={{ fontSize: '0.75rem', padding: '0.4rem 0.8rem' }}
            download
          >
            <Layers size={12} /> JSON Schema
          </a>
        </div>
      </div>

      {/* Save Status Banner */}
      {saveStatus && (
        <div 
          className={`status-badge ${saveStatus.type === 'error' ? 'failed' : 'completed'}`} 
          style={{ 
            padding: '0.6rem 1rem', 
            justifyContent: 'center', 
            fontWeight: 600,
            fontSize: '0.8rem',
            animation: 'fadeIn 0.2s ease-in'
          }}
        >
          {saveStatus.message}
        </div>
      )}

      {/* Check if currently in active uploads and not completed yet */}
      {activeUploads[selectedDocId] ? (
        <div className="glass-panel" style={{ padding: '3rem', flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ width: '100%', maxWidth: '500px' }}>
            <div className="upload-progress-header">
              <span className="text-white font-semibold">Vision Processing Pipeline</span>
              <span style={{ color: 'var(--primary)', fontWeight: 'bold' }}>{activeUploads[selectedDocId].progress}%</span>
            </div>
            <div className="animated-progress-container">
              <div className="animated-progress-bar" style={{ width: `${activeUploads[selectedDocId].progress}%` }}></div>
            </div>
            <p className="upload-progress-msg">{activeUploads[selectedDocId].message}</p>
          </div>
        </div>
      ) : selectedDoc.ocr_status !== 'COMPLETED' ? (
        <div className="glass-panel" style={{ padding: '3rem', flexGrow: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
          <XCircle size={48} style={{ color: 'var(--error)' }} />
          <h3 style={{ fontWeight: 600 }}>OCR Processing Failed</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>The scanning pipeline encountered a critical VLM error or the file could not be parsed.</p>
          <button onClick={() => setCurrentView('library')} className="btn-primary" style={{ width: 'auto' }}>Return to Library</button>
        </div>
      ) : (
        <div className="dashboard-layout-grid" style={{ flexGrow: 1, minHeight: 0 }}>
          
          {/* Left Panel: OCR or Extraction Keys */}
          <div className="workspace-panel glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <div className="tabs" style={{ borderBottom: '1px solid var(--border-color)', gap: 0 }}>
              <button 
                onClick={() => setDocTab('ocr')} 
                className={`tab-btn ${docTab === 'ocr' ? 'active' : ''}`}
                style={{ flex: 1, textAlign: 'center', justifyContent: 'center', padding: '0.8rem', borderRadius: 0 }}
              >
                Plain OCR Text
              </button>
              <button 
                onClick={() => setDocTab('document')} 
                className={`tab-btn ${docTab === 'document' ? 'active' : ''}`}
                style={{ flex: 1, textAlign: 'center', justifyContent: 'center', padding: '0.8rem', borderRadius: 0 }}
              >
                Original Document
              </button>
              <button 
                onClick={() => setDocTab('data')} 
                className={`tab-btn ${docTab === 'data' ? 'active' : ''}`}
                style={{ flex: 1, textAlign: 'center', justifyContent: 'center', padding: '0.8rem', borderRadius: 0 }}
              >
                Intelligent Fields ({selectedDoc.document_type})
              </button>
            </div>

            <div style={{ flexGrow: 1, overflowY: 'auto', padding: '1.25rem' }}>
              {docTab === 'ocr' && (
                <div className="text-viewer" style={{ height: '100%', minHeight: '300px' }}>
                  {selectedDoc.ocr_text || 'OCR content empty.'}
                </div>
              )}

              {docTab === 'document' && (
                <div style={{ height: '100%', minHeight: '500px' }}>
                  {selectedDoc.file_type === 'pdf' ? (
                    <iframe 
                      src={`${API_BASE_URL}/document/${selectedDocId}/file#page=${activePage || 1}`} 
                      width="100%" 
                      height="100%" 
                      style={{ border: 'none', minHeight: '500px', borderRadius: '8px', background: '#1e293b' }}
                      title="PDF Document Viewer"
                    />
                  ) : (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#1e293b', padding: '1rem', borderRadius: '8px', minHeight: '500px' }}>
                      <img 
                        src={`${API_BASE_URL}/document/${selectedDocId}/file`} 
                        alt="Document Preview" 
                        style={{ maxWidth: '100%', maxHeight: '600px', objectFit: 'contain', borderRadius: '4px' }}
                      />
                    </div>
                  )}
                </div>
              )}

              {docTab === 'data' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div className="status-badge" style={{ backgroundColor: 'rgba(16, 185, 129, 0.08)', color: 'var(--secondary)', border: '1px solid rgba(16, 185, 129, 0.2)', width: '100%', justifyContent: 'space-between', padding: '0.6rem 1rem' }}>
                    <span>Matching Schema: {selectedDoc.document_type}</span>
                    <span>Accuracy Confidence: {Math.round(selectedDoc.confidence_score * 100)}%</span>
                    
                    {extractedData && !isEditing && (
                      <button 
                        onClick={() => setIsEditing(true)} 
                        className="tab-btn active" 
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                      >
                        <Edit2 size={10} /> Edit Fields
                      </button>
                    )}
                  </div>
                  
                  {extractedLoading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '3rem', gap: '0.5rem', color: 'var(--primary)' }}>
                      <RefreshCw className="spinner" size={20} /> Field mapping analysis...
                    </div>
                  ) : extractedData ? (
                    <div className="table-wrapper glass-panel" style={{ border: '1px solid var(--border-color)', borderRadius: '8px', padding: isEditing ? '1rem' : 0 }}>
                      {isEditing ? (
                        <div className="settings-form-layout" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                          {Object.entries(editableFields).map(([key, val]) => (
                            <div key={key} className="form-group" style={{ margin: 0 }}>
                              <label className="form-label" style={{ textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</label>
                              {typeof val === 'object' ? (
                                <textarea
                                  value={typeof val === 'object' ? JSON.stringify(val, null, 2) : val}
                                  onChange={(e) => {
                                    try {
                                      const parsed = JSON.parse(e.target.value);
                                      handleFieldChange(key, parsed);
                                    } catch (err) {
                                      handleFieldChange(key, e.target.value);
                                    }
                                  }}
                                  className="form-input"
                                  rows={4}
                                  style={{ fontFamily: 'Consolas, monospace', fontSize: '0.8rem' }}
                                />
                              ) : (
                                <input
                                  type="text"
                                  value={val !== null ? String(val) : ''}
                                  onChange={(e) => handleFieldChange(key, e.target.value)}
                                  className="form-input"
                                />
                              )}
                            </div>
                          ))}
                          
                          <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                            <button 
                              onClick={handleSaveChanges} 
                              disabled={editLoading}
                              className="btn-primary" 
                              style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                            >
                              {editLoading ? <RefreshCw className="spinner" size={14} /> : <Save size={14} />} Save Changes
                            </button>
                            <button 
                              onClick={() => { setIsEditing(false); setEditableFields(extractedData); }} 
                              disabled={editLoading}
                              className="tab-btn" 
                              style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', border: '1px solid var(--border-color)' }}
                            >
                              <X size={14} /> Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <table className="premium-table">
                          <thead>
                            <tr>
                              <th>Field Key</th>
                              <th>Mapped Value</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(editableFields).map(([key, val]) => (
                              <tr key={key}>
                                <td style={{ fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</td>
                                <td style={{ fontFamily: 'Consolas, monospace', fontSize: '0.8rem', userSelect: 'all' }}>
                                  {typeof val === 'object' ? JSON.stringify(val, null, 2) : String(val)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  ) : (
                    <p style={{ fontStyle: 'italic', color: 'var(--text-muted)', textAlign: 'center', padding: '3rem' }}>No structured fields indexed.</p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right Panel: Interactive RAG Chat Box */}
          <div className="workspace-panel glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <div className="panel-header" style={{ padding: '0.8rem 1.25rem', borderBottom: '1px solid var(--border-color)' }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                <MessageSquare size={14} style={{ color: 'var(--primary)' }} /> RAG Assistant Chat
              </h3>
            </div>

            {/* Messages feed */}
            <div style={{ flexGrow: 1, overflowY: 'auto', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {chatHistory.length === 0 ? (
                <div className="empty-state" style={{ height: '100%', minHeight: 0 }}>
                  <div className="empty-state-icon"><MessageSquare size={32} /></div>
                  <p style={{ fontWeight: 600 }}>Ask details about this document</p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '-0.75rem' }}>The VLM answers questions strictly utilizing the document chunks context.</p>
                </div>
              ) : (
                chatHistory.map((chat, idx) => (
                  <div key={idx} className={`chat-bubble ${chat.sender === 'user' ? 'user' : 'ai'}`}>
                    <p style={{ fontSize: '0.85rem' }}>{chat.text}</p>
                    {chat.sources && chat.sources.length > 0 && (
                      <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase' }}>Source Pages:</span>
                        {chat.sources.map((s, sIdx) => (
                          <button 
                            key={sIdx} 
                            onClick={() => {
                              setDocTab('document');
                              setActivePage(s.page);
                            }}
                            className="status-badge" 
                            style={{ 
                              padding: '0.1rem 0.35rem', 
                              fontSize: '0.65rem', 
                              backgroundColor: 'rgba(99,102,241,0.1)', 
                              color: 'var(--primary)', 
                              border: '1px solid rgba(99,102,241,0.2)',
                              cursor: 'pointer',
                              transition: 'all 0.2s',
                              borderRadius: '4px'
                            }}
                          >
                            Page {s.page}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
              {chatLoading && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--primary)', fontSize: '0.8rem', paddingLeft: '0.5rem' }}>
                  <RefreshCw className="spinner" size={12} />
                  VLM searching document chunks...
                </div>
              )}
              <div ref={chatEndRef}></div>
            </div>

            {/* Input form */}
            <form onSubmit={handleChatSubmit} className="chat-input-area" style={{ padding: '1rem', borderTop: '1px solid var(--border-color)' }}>
              <input 
                type="text" 
                value={chatQuestion}
                onChange={(e) => setChatQuestion(e.target.value)}
                placeholder="Ask about this document..."
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
      )}
    </div>
  );
}

export default WorkspaceView;
