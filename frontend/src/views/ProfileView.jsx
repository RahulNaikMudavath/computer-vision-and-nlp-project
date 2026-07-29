import React from 'react';
import { AlertCircle } from 'lucide-react';

function ProfileView({
  profileName,
  setProfileName,
  profileAvatar,
  setProfileAvatar,
  profilePassword,
  setProfilePassword,
  handleProfileUpdate,
  handleDeleteAccount
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '600px' }}>
      <div className="dashboard-title-area" style={{ marginBottom: 0 }}>
        <h1>My Profile</h1>
        <p>Configure your personal information, display settings, or secure your credentials.</p>
      </div>

      <form onSubmit={handleProfileUpdate} className="controls-card glass-panel settings-form-layout">
        <div className="form-group">
          <label className="form-label">Display Name</label>
          <input 
            type="text" 
            value={profileName}
            onChange={(e) => setProfileName(e.target.value)}
            className="form-input"
            placeholder="Hacker User"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Avatar Image URL</label>
          <input 
            type="text" 
            value={profileAvatar}
            onChange={(e) => setProfileAvatar(e.target.value)}
            placeholder="https://example.com/avatar.jpg"
            className="form-input"
          />
        </div>

        <div className="form-group">
          <label className="form-label">New Password (leave blank to keep current)</label>
          <input 
            type="password" 
            value={profilePassword}
            onChange={(e) => setProfilePassword(e.target.value)}
            placeholder="••••••••"
            className="form-input"
          />
        </div>

        <button 
          type="submit" 
          className="btn-primary"
          style={{ alignSelf: 'flex-start', width: 'auto', padding: '0.7rem 2rem' }}
        >
          Save Profile Changes
        </button>
      </form>

      <div className="danger-zone-container">
        <h3 className="danger-zone-title"><AlertCircle size={18} /> Danger Zone</h3>
        <p className="danger-zone-desc">Permanently close your platform profile and purge all document records and RAG indexes. This operation cannot be undone.</p>
        <button 
          onClick={handleDeleteAccount}
          className="btn-danger"
        >
          Permanently Delete Account
        </button>
      </div>
    </div>
  );
}

export default ProfileView;
