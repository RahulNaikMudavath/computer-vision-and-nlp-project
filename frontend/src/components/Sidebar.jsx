import React from 'react';
import { FileText, LayoutDashboard, Layers, User, Settings, Shield, LogOut } from 'lucide-react';

function Sidebar({ currentView, setCurrentView, userProfile, handleLogout }) {
  return (
    <aside className="sidebar">
      <div>
        <div className="sidebar-logo" onClick={() => setCurrentView('dashboard')}>
          <div className="logo-icon" style={{ width: '32px', height: '32px', borderRadius: '6px' }}>
            <FileText size={18} style={{ color: '#fff' }} />
          </div>
          <span>DocuMind</span>
        </div>

        <nav className="sidebar-nav">
          <button 
            onClick={() => setCurrentView('dashboard')}
            className={`nav-link ${currentView === 'dashboard' ? 'active' : ''}`}
          >
            <LayoutDashboard size={18} />
            Dashboard
          </button>

          <button 
            onClick={() => setCurrentView('library')}
            className={`nav-link ${currentView === 'library' || currentView === 'workspace' ? 'active' : ''}`}
          >
            <Layers size={18} />
            Document Library
          </button>

          <button 
            onClick={() => setCurrentView('profile')}
            className={`nav-link ${currentView === 'profile' ? 'active' : ''}`}
          >
            <User size={18} />
            My Profile
          </button>

          <button 
            onClick={() => setCurrentView('settings')}
            className={`nav-link ${currentView === 'settings' ? 'active' : ''}`}
          >
            <Settings size={18} />
            Settings
          </button>

          {userProfile?.role === 'Admin' && (
            <button 
              onClick={() => setCurrentView('admin')}
              className={`nav-link ${currentView === 'admin' ? 'active' : ''}`}
            >
              <Shield size={18} />
              Admin Console
            </button>
          )}
        </nav>
      </div>

      <div className="sidebar-footer">
        <div className="user-profile-widget">
          <div className="user-avatar">
            {userProfile?.avatar_url ? (
              <img src={userProfile.avatar_url} alt="avatar" />
            ) : (
              (userProfile?.email || '').slice(0, 2).toUpperCase()
            )}
          </div>
          <div className="user-info">
            <p className="user-name">{userProfile?.full_name || 'Standard User'}</p>
            <p className="user-role">{userProfile?.email}</p>
          </div>
        </div>

        <button 
          onClick={handleLogout}
          className="logout-btn"
        >
          <LogOut size={16} />
          Logout
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
