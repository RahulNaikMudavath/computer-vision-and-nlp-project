import React from 'react';
import { 
  FilePlus, Search, FileText, Edit, CheckCircle, 
  XCircle, RefreshCw, MessageSquare, Download, Layers, Trash2 
} from 'lucide-react';

function LibraryView({
  documents,
  searchQuery,
  setSearchQuery,
  filterType,
  setFilterType,
  filterStatus,
  setFilterStatus,
  sortOrder,
  setSortOrder,
  renameId,
  setRenameId,
  renameVal,
  setRenameVal,
  handleRename,
  handleDelete,
  setSelectedDocId,
  setCurrentView,
  fileInputRef,
  API_BASE_URL,
  selectedDocIds = [],
  setSelectedDocIds
}) {
  const handleToggleSelectDoc = (id) => {
    if (selectedDocIds.includes(id)) {
      setSelectedDocIds(prev => prev.filter(x => x !== id));
    } else {
      setSelectedDocIds(prev => [...prev, id]);
    }
  };

  const handleSelectAll = () => {
    if (selectedDocIds.length === documents.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(documents.map(doc => doc.id));
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="library-header-row">
        <div className="dashboard-title-area" style={{ marginBottom: 0 }}>
          <h1>Document Library</h1>
          <p>Filter, sort, download and chat with indexed files.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          {selectedDocIds.length > 0 && (
            <button 
              onClick={() => setCurrentView('multi-workspace')}
              className="btn-secondary"
              style={{ 
                width: 'auto', 
                padding: '0.6rem 1.2rem', 
                display: 'flex', 
                alignItems: 'center', 
                gap: '0.5rem', 
                backgroundColor: 'var(--secondary)',
                border: 'none',
                borderRadius: '8px',
                color: '#fff',
                cursor: 'pointer',
                fontWeight: 600,
                transition: 'all 0.2s'
              }}
            >
              <MessageSquare size={16} /> Chat Selected ({selectedDocIds.length})
            </button>
          )}
          <button 
            onClick={() => fileInputRef.current?.click()}
            className="btn-primary"
            style={{ width: 'auto', padding: '0.6rem 1.2rem' }}
          >
            <FilePlus size={16} /> Upload New
          </button>
        </div>
      </div>

      {/* Filter Search bar */}
      <div className="filters-panel glass-panel">
        <div className="filters-layout-grid">
          <div className="search-input-wrapper">
            <Search size={16} />
            <input 
              type="text" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search files..."
              className="search-input"
              style={{ width: '100%' }}
            />
          </div>

          <select 
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="filter-select"
          >
            <option value="">All Document Types</option>
            <option value="Invoice">Invoice</option>
            <option value="Receipt">Receipt</option>
            <option value="Passport">Passport</option>
            <option value="PAN Card">PAN Card</option>
            <option value="Aadhaar Card">Aadhaar Card</option>
            <option value="Driving License">Driving License</option>
            <option value="Resume">Resume</option>
            <option value="Bank Statement">Bank Statement</option>
            <option value="Utility Bill">Utility Bill</option>
            <option value="Generic Document">Generic Document</option>
          </select>

          <select 
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="filter-select"
          >
            <option value="">All OCR Statuses</option>
            <option value="PENDING">PENDING</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="FAILED">FAILED</option>
          </select>

          <select 
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
            className="filter-select"
          >
            <option value="newest">Sort by: Newest</option>
            <option value="oldest">Sort by: Oldest</option>
          </select>
        </div>
      </div>

      {/* Document Library Table Grid */}
      <div className="table-wrapper glass-panel">
        {documents.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center' }}>
            <FileText className="empty-state-icon" style={{ margin: '0 auto 1rem auto' }} size={48} />
            <p style={{ fontWeight: 600 }}>No documents matched your criteria.</p>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Try resetting search filters or upload a document.</p>
          </div>
        ) : (
          <table className="premium-table">
            <thead>
              <tr>
                <th style={{ width: '40px', textAlign: 'center' }}>
                  <input 
                    type="checkbox" 
                    onChange={handleSelectAll} 
                    checked={documents.length > 0 && selectedDocIds.length === documents.length}
                    style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                  />
                </th>
                <th>Filename</th>
                <th>Type</th>
                <th>Size</th>
                <th>OCR Status</th>
                <th>Upload Date</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td style={{ textAlign: 'center' }}>
                    <input 
                      type="checkbox" 
                      checked={selectedDocIds.includes(doc.id)} 
                      onChange={() => handleToggleSelectDoc(doc.id)}
                      onClick={(e) => e.stopPropagation()}
                      style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                    />
                  </td>
                  <td>
                    {renameId === doc.id ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <input 
                          type="text" 
                          value={renameVal} 
                          onChange={(e) => setRenameVal(e.target.value)}
                          className="form-input"
                          style={{ padding: '0.35rem 0.75rem', fontSize: '0.85rem' }}
                        />
                        <button onClick={() => handleRename(doc.id)} className="btn-primary" style={{ width: 'auto', padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}>Save</button>
                        <button onClick={() => setRenameId(null)} className="tab-btn" style={{ fontSize: '0.75rem' }}>Cancel</button>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <FileText size={16} style={{ color: 'var(--text-secondary)' }} />
                        <span style={{ fontWeight: 600 }} className="truncate">{doc.original_filename}</span>
                        <button onClick={() => { setRenameId(doc.id); setRenameVal(doc.original_filename); }} className="action-btn-circle" style={{ width: '22px', height: '22px', border: 'none' }}><Edit size={10} /></button>
                      </div>
                    )}
                  </td>
                  <td><span className="status-badge" style={{ backgroundColor: 'rgba(255,255,255,0.03)', color: '#fff', border: '1px solid rgba(255,255,255,0.06)' }}>{doc.document_type}</span></td>
                  <td>{doc.size_formatted}</td>
                  <td>
                    <span className={`status-badge ${doc.ocr_status.toLowerCase()}`}>
                      {doc.ocr_status === 'COMPLETED' ? <CheckCircle size={10} /> : doc.ocr_status === 'FAILED' ? <XCircle size={10} /> : <RefreshCw className="spinner" size={10} />}
                      {doc.ocr_status}
                    </span>
                  </td>
                  <td>{new Date(doc.created_at).toLocaleDateString()}</td>
                  <td>
                    <div className="cell-actions-wrapper">
                      {doc.ocr_status === 'COMPLETED' && (
                        <>
                          <button 
                            onClick={() => { setSelectedDocId(doc.id); setCurrentView('workspace'); }}
                            className="action-btn-circle chat"
                            title="Open Chat Workspace"
                          >
                            <MessageSquare size={14} />
                          </button>
                          <a 
                            href={`${API_BASE_URL}/document/${doc.id}/download-text`}
                            className="action-btn-circle"
                            title="Download Plain OCR"
                          >
                            <Download size={14} />
                          </a>
                          <a 
                            href={`${API_BASE_URL}/document/${doc.id}/download-json`}
                            className="action-btn-circle"
                            title="Download structured JSON"
                            download
                          >
                            <Layers size={14} />
                          </a>
                        </>
                      )}
                      <button 
                        onClick={() => handleDelete(doc.id)}
                        className="action-btn-circle delete"
                        title="Delete Document"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default LibraryView;
