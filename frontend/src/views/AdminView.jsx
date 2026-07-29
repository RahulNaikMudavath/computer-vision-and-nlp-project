import React from 'react';
import { RefreshCw, UserCheck, Terminal } from 'lucide-react';

function AdminView({
  adminLoading,
  adminStats,
  adminUsers,
  adminLogs,
  userProfile,
  handleToggleUserStatus
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div className="dashboard-title-area" style={{ marginBottom: 0 }}>
        <h1>Administrative Console</h1>
        <p>Platform analytics, active logs, and multi-tenant management.</p>
      </div>

      {adminLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '5rem', gap: '0.5rem', color: 'var(--primary)' }}>
          <RefreshCw className="spinner" size={24} /> Fetching platform configurations...
        </div>
      ) : (
        <>
          {/* Platform Analytics Cards Grid */}
          {adminStats && (
            <div className="metrics-grid">
              <div className="metric-card glass-panel" style={{ padding: '1.25rem' }}>
                <span className="metric-card-header" style={{ fontSize: '0.7rem' }}>Total System Users</span>
                <h3 className="metric-value" style={{ fontSize: '1.5rem', marginTop: '0.5rem' }}>{adminStats.total_users}</h3>
              </div>
              <div className="metric-card glass-panel" style={{ padding: '1.25rem' }}>
                <span className="metric-card-header" style={{ fontSize: '0.7rem' }}>Platform Documents</span>
                <h3 className="metric-value" style={{ fontSize: '1.5rem', marginTop: '0.5rem' }}>{adminStats.total_documents}</h3>
              </div>
              <div className="metric-card glass-panel" style={{ padding: '1.25rem' }}>
                <span className="metric-card-header" style={{ fontSize: '0.7rem' }}>System RAG Queries</span>
                <h3 className="metric-value" style={{ fontSize: '1.5rem', marginTop: '0.5rem' }}>{adminStats.total_chats}</h3>
              </div>
              <div className="metric-card glass-panel" style={{ padding: '1.25rem' }}>
                <span className="metric-card-header" style={{ fontSize: '0.7rem' }}>Total Platform Storage</span>
                <h3 className="metric-value" style={{ fontSize: '1.5rem', marginTop: '0.5rem' }}>{adminStats.storage_used_formatted}</h3>
              </div>
            </div>
          )}

          <div className="dashboard-layout-grid">
            
            {/* Users accounts list table */}
            <div className="controls-card glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-heading)', fontWeight: 600 }}>
                <UserCheck size={18} style={{ color: 'var(--primary)' }} /> User Accounts Manager
              </h3>
              <div className="table-wrapper">
                <table className="premium-table">
                  <thead>
                    <tr>
                      <th>User Email</th>
                      <th>Role</th>
                      <th>Docs</th>
                      <th>Status</th>
                      <th style={{ textAlign: 'right' }}>Toggle Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {adminUsers.map((usr) => (
                      <tr key={usr.id}>
                        <td style={{ fontWeight: 600 }}>{usr.email}</td>
                        <td><span className="status-badge" style={{ backgroundColor: 'rgba(255,255,255,0.03)', color: '#fff', border: '1px solid rgba(255,255,255,0.06)', fontSize: '0.7rem' }}>{usr.role}</span></td>
                        <td>{usr.document_count}</td>
                        <td>
                          <span className={`status-badge ${usr.is_active ? 'completed' : 'failed'}`} style={{ fontSize: '0.7rem' }}>
                            {usr.is_active ? 'Active' : 'Suspended'}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          {usr.id !== userProfile?.id ? (
                            <button 
                              onClick={() => handleToggleUserStatus(usr.id)}
                              className="btn-primary"
                              style={{ width: 'auto', padding: '0.35rem 0.75rem', fontSize: '0.75rem', background: usr.is_active ? 'rgba(244,63,94,0.1)' : 'rgba(16,185,129,0.1)', border: '1px solid var(--border-color)', color: usr.is_active ? 'var(--error)' : 'var(--secondary)' }}
                            >
                              {usr.is_active ? 'Suspend' : 'Activate'}
                            </button>
                          ) : (
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>Self</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* System Logs console stream */}
            <div className="controls-card glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-heading)', fontWeight: 600 }}>
                <Terminal size={18} style={{ color: 'var(--primary)' }} /> System Logs
              </h3>
              <div className="terminal-console">
                {adminLogs.map((log, index) => (
                  <div key={index} className="log-row">
                    <span className="log-time">[{log.timestamp}]</span>
                    <span className={`log-level-badge ${log.level.toLowerCase()}`}>{log.level}</span>
                    <span className="log-msg">{log.message}</span>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </>
      )}
    </div>
  );
}

export default AdminView;
