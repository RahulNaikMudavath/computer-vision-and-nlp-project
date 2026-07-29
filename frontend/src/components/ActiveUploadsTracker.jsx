import React from 'react';

function ActiveUploadsTracker({ activeUploads }) {
  const uploads = Object.entries(activeUploads);
  if (uploads.length === 0) return null;

  return (
    <div 
      className="floating-uploads-tracker" 
      style={{
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        zIndex: 9999,
        width: '320px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}
    >
      {uploads.map(([id, info]) => (
        <div 
          key={id} 
          className="glass-panel" 
          style={{
            padding: '1rem',
            border: '1px solid var(--border-color)',
            background: 'rgba(15, 23, 42, 0.95)',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
            borderRadius: '8px',
            backdropFilter: 'blur(12px)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600 }}>Processing pipeline...</span>
            <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--primary)' }}>{info.progress}%</span>
          </div>
          <div className="animated-progress-container" style={{ height: '4px' }}>
            <div className="animated-progress-bar" style={{ width: `${info.progress}%`, height: '100%' }}></div>
          </div>
          <p 
            style={{ 
              fontSize: '0.7rem', 
              color: 'var(--text-muted)', 
              marginTop: '0.25rem', 
              marginBottom: 0,
              textOverflow: 'ellipsis',
              overflow: 'hidden',
              whiteSpace: 'nowrap'
            }}
          >
            {info.message}
          </p>
        </div>
      ))}
    </div>
  );
}

export default ActiveUploadsTracker;
