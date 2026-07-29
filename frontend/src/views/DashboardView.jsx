import React from 'react';
import { 
  FileText, Layers, MessageSquare, Database, Upload, 
  RefreshCw, ChevronRight 
} from 'lucide-react';

function DashboardView({
  stats,
  isUploading,
  dragActive,
  handleDrag,
  handleDrop,
  handleFileChange,
  fileInputRef,
  setCurrentView,
  setSelectedDocId
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>
      <div className="dashboard-title-area">
        <h1>System Dashboard</h1>
        <p>Quick analysis overview of uploaded documents and page conversions.</p>
      </div>

      {/* Performance Stats Cards Grid */}
      <div className="metrics-grid">
        <div className="metric-card glass-panel">
          <div className="metric-card-header">
            <span>Processed Docs</span>
            <div className="metric-icon-box primary"><FileText size={18} /></div>
          </div>
          <h3 className="metric-value">{stats.documents_processed}</h3>
          <p className="metric-desc">Total documents OCR'd</p>
        </div>

        <div className="metric-card glass-panel">
          <div className="metric-card-header">
            <span>Total Chunks</span>
            <div className="metric-icon-box success"><Layers size={18} /></div>
          </div>
          <h3 className="metric-value">{stats.pages_processed}</h3>
          <p className="metric-desc">Relational chunks split</p>
        </div>

        <div className="metric-card glass-panel">
          <div className="metric-card-header">
            <span>QA Conversations</span>
            <div className="metric-icon-box warning"><MessageSquare size={18} /></div>
          </div>
          <h3 className="metric-value">{stats.total_chats}</h3>
          <p className="metric-desc">RAG prompts queried</p>
        </div>

        <div className="metric-card glass-panel">
          <div className="metric-card-header">
            <span>Storage Capacity</span>
            <div className="metric-icon-box accent"><Database size={18} /></div>
          </div>
          <h3 className="metric-value">{stats.storage_used_formatted}</h3>
          <div className="progress-meter-container">
            <div 
              className="progress-meter-bar"
              style={{ width: `${Math.min(100, (stats.storage_used_bytes / (20 * 1024 * 1024)) * 100)}%` }}
            ></div>
          </div>
          <p className="metric-desc" style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem' }}>
            <span>Usage Meter</span>
            <span>Max Limit: 20 MB</span>
          </p>
        </div>
      </div>

      <div className="dashboard-layout-grid">
        
        {/* Document Drag and Drop upload Box */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="upload-card glass-panel">
            <h3 style={{ marginBottom: '1rem', fontFamily: 'var(--font-heading)', fontWeight: 600 }}>Upload Document</h3>
            <div 
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`upload-area ${dragActive ? 'drag-active' : ''}`}
            >
              <input 
                type="file" 
                ref={fileInputRef}
                onChange={handleFileChange}
                className="hidden" 
                style={{ display: 'none' }}
                accept=".pdf,.png,.jpg,.jpeg"
              />
              <div className="upload-icon-container">
                <Upload size={28} />
              </div>
              <div style={{ textAlign: 'center' }}>
                <p style={{ fontSize: '0.9rem', fontWeight: 600 }}>Drag and drop file here, or click to upload</p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Accepts PDF, PNG, JPG, JPEG (Max 20MB images, 50MB PDFs)</p>
              </div>
              {isUploading && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--primary)', fontWeight: 600, fontSize: '0.85rem' }}>
                  <RefreshCw className="spinner" size={14} />
                  Uploading to server...
                </div>
              )}
            </div>
          </div>

          {/* Recent Uploaded documents list */}
          <div className="controls-card glass-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h3 style={{ fontFamily: 'var(--font-heading)', fontWeight: 600 }}>Recent Uploads</h3>
              <button 
                onClick={() => setCurrentView('library')} 
                className="tab-btn active"
                style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}
              >
                View Library <ChevronRight size={12} />
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {stats.recent_uploads.length === 0 ? (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '1rem', textAlign: 'center' }}>No documents uploaded yet.</p>
              ) : (
                stats.recent_uploads.map((doc) => (
                  <div key={doc.id} className="recent-row">
                    <div className="recent-info-block">
                      <div className="recent-icon"><FileText size={18} /></div>
                      <div className="recent-text">
                        <p className="recent-name">{doc.original_filename}</p>
                        <p className="recent-sub">{doc.document_type} • {doc.size_formatted}</p>
                      </div>
                    </div>
                    <button 
                      onClick={() => { setSelectedDocId(doc.id); setCurrentView('workspace'); }}
                      className="btn-small-chat"
                    >
                      <MessageSquare size={12} /> Chat
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Live activity feed */}
        <div className="controls-card glass-panel" style={{ alignSelf: 'start' }}>
          <h3 style={{ marginBottom: '1.25rem', fontFamily: 'var(--font-heading)', fontWeight: 600 }}>Recent Activity</h3>
          <div className="activity-feed">
            {stats.recent_activities.length === 0 ? (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '1rem', textAlign: 'center' }}>No active history logged.</p>
            ) : (
              stats.recent_activities.map((act, index) => (
                <div key={index} className="activity-item">
                  <div className={`activity-icon-badge ${act.activity_type}`}>
                    {act.activity_type === 'upload' ? <Upload size={12} /> : <MessageSquare size={12} />}
                  </div>
                  <div className="activity-body">
                    <p className="activity-msg">{act.message}</p>
                    <p className="activity-time">{new Date(act.timestamp).toLocaleTimeString()}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

export default DashboardView;
