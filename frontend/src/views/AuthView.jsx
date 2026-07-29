import React from 'react';
import { FileText } from 'lucide-react';
import Toast from '../components/Toast';

function AuthView({
  authTab,
  setAuthTab,
  authEmail,
  setAuthEmail,
  authPassword,
  setAuthPassword,
  authFullName,
  setAuthFullName,
  authLoading,
  handleAuthSubmit,
  toast
}) {
  return (
    <div className="auth-container">
      {/* Floating toast */}
      <Toast toast={toast} />

      <div className="auth-card glass-panel">
        <div className="logo-container" style={{ justifyContent: 'center', marginBottom: '2rem' }}>
          <div className="logo-icon">
            <FileText size={24} style={{ color: '#fff' }} />
          </div>
          <span className="logo-text">DocuMind</span>
        </div>
        
        <div className="tabs" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)' }}>
          <button 
            onClick={() => setAuthTab('login')} 
            className={`tab-btn ${authTab === 'login' ? 'active' : ''}`}
            style={{ flex: 1, paddingBottom: '0.75rem', borderRadius: 0 }}
          >
            Sign In
          </button>
          <button 
            onClick={() => setAuthTab('register')} 
            className={`tab-btn ${authTab === 'register' ? 'active' : ''}`}
            style={{ flex: 1, paddingBottom: '0.75rem', borderRadius: 0 }}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleAuthSubmit} className="settings-form-layout">
          {authTab === 'register' && (
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input 
                type="text" 
                value={authFullName}
                onChange={(e) => setAuthFullName(e.target.value)}
                placeholder="John Doe" 
                className="form-input"
              />
            </div>
          )}
          
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input 
              type="email" 
              value={authEmail}
              onChange={(e) => setAuthEmail(e.target.value)}
              placeholder="you@example.com" 
              className="form-input"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input 
              type="password" 
              value={authPassword}
              onChange={(e) => setAuthPassword(e.target.value)}
              placeholder="••••••••" 
              className="form-input"
              required
            />
          </div>

          <button 
            type="submit" 
            disabled={authLoading}
            className="btn-primary"
            style={{ marginTop: '1rem' }}
          >
            {authLoading ? 'Loading...' : authTab === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default AuthView;
