import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

// View Imports
import AuthView from './views/AuthView';
import DashboardView from './views/DashboardView';
import LibraryView from './views/LibraryView';
import WorkspaceView from './views/WorkspaceView';
import ProfileView from './views/ProfileView';
import SettingsView from './views/SettingsView';
import AdminView from './views/AdminView';
import MultiWorkspaceView from './views/MultiWorkspaceView';

// Component Imports
import Sidebar from './components/Sidebar';
import Toast from './components/Toast';
import ActiveUploadsTracker from './components/ActiveUploadsTracker';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// =====================================================================
// Axios Configuration with Request Interceptors
// =====================================================================
const api = axios.create({
  baseURL: API_BASE_URL
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

function App() {
  // Authentication states
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authTab, setAuthTab] = useState('login'); // 'login' or 'register'
  const [authLoading, setAuthLoading] = useState(false);
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authFullName, setAuthFullName] = useState('');
  const [userProfile, setUserProfile] = useState(null);
  
  // App Navigation state
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard', 'library', 'workspace', 'profile', 'settings', 'admin'
  
  // Dashboard & Library states
  const [stats, setStats] = useState({
    documents_processed: 0,
    pages_processed: 0,
    total_chats: 0,
    storage_used_bytes: 0,
    storage_used_formatted: '0 Bytes',
    recent_uploads: [],
    recent_activities: []
  });
  const [documents, setDocuments] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [sortOrder, setSortOrder] = useState('newest');
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  
  // Real-time asynchronous processing tracker
  const [activeUploads, setActiveUploads] = useState({}); // { [docId]: { status, progress, message } }

  // Workspace / Detail states
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [docTab, setDocTab] = useState('ocr'); // 'ocr' or 'data'
  const [extractedData, setExtractedData] = useState(null);
  const [extractedLoading, setExtractedLoading] = useState(false);
  const [chatQuestion, setChatQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [renameId, setRenameId] = useState(null);
  const [renameVal, setRenameVal] = useState('');

  // Multi-RAG states
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const [multiChatQuestion, setMultiChatQuestion] = useState('');
  const [multiChatHistory, setMultiChatHistory] = useState([]);
  const [multiChatLoading, setMultiChatLoading] = useState(false);
  
  // Profile & Settings fields
  const [profileName, setProfileName] = useState('');
  const [profileAvatar, setProfileAvatar] = useState('');
  const [profilePassword, setProfilePassword] = useState('');
  const [settingsTheme, setSettingsTheme] = useState('light');
  const [settingsLanguage, setSettingsLanguage] = useState('en');
  const [settingsOcrLang, setSettingsOcrLang] = useState('en');
  const [settingsNotify, setSettingsNotify] = useState(true);
  
  // Admin panel states
  const [adminStats, setAdminStats] = useState(null);
  const [adminUsers, setAdminUsers] = useState([]);
  const [adminLogs, setAdminLogs] = useState([]);
  const [adminLoading, setAdminLoading] = useState(false);
  
  // Notifications state
  const [toast, setToast] = useState(null);
  
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);

  // =====================================================================
  // Hooks and Initial Loaders
  // =====================================================================
  useEffect(() => {
    // Check if token exists on load
    const token = localStorage.getItem('access_token');
    if (token) {
      fetchUserProfile();
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      loadViewData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, currentView, sortOrder, filterType, filterStatus, searchQuery]);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory]);

  // =====================================================================
  // WebSocket Progress Tracking Connection Lifecycle
  // =====================================================================
  useEffect(() => {
    if (!isAuthenticated || !userProfile?.id) return;
    
    let socket;
    let reconnectTimeout;
    
    const connectWs = () => {
      const cleanBaseUrl = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
      const wsProtocol = cleanBaseUrl.startsWith('https') ? 'wss:' : 'ws:';
      const wsHost = cleanBaseUrl.replace(/^https?:\/\//, '');
      const wsUrl = `${wsProtocol}//${wsHost}/ws/${userProfile.id}`;
      console.log('Connecting to WebSocket channel:', wsUrl);
      
      socket = new WebSocket(wsUrl);
      
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Real-time pipeline broadcast:', data);
          const { document_id, status, progress, message } = data;
          
          setActiveUploads((prev) => {
            const updated = { ...prev };
            
            if (status === 'COMPLETED' || status === 'FAILED') {
              // Hide from progress tracker after 4 seconds
              setTimeout(() => {
                setActiveUploads((curr) => {
                  const next = { ...curr };
                  delete next[document_id];
                  return next;
                });
              }, 4000);
              
              // If completed doc is currently viewed in workspace, reload detail data
              if (selectedDocId === document_id && currentView === 'workspace') {
                fetchWorkspaceDoc(document_id);
              }
              
              // Reload general library/stats data
              loadViewData();
            }
            
            updated[document_id] = { status, progress, message };
            return updated;
          });
          
          if (status === 'COMPLETED') {
            showToast(`Scanned successfully: document completed!`);
          } else if (status === 'FAILED') {
            showToast(`Analysis failure: ${message}`, 'error');
          }
        } catch (err) {
          console.error('Failed to parse WS payload:', err);
        }
      };
      
      socket.onclose = () => {
        console.log('WebSocket stream closed. Retrying connection...');
        reconnectTimeout = setTimeout(connectWs, 3000);
      };
      
      socket.onerror = (err) => {
        console.error('WebSocket error encountered:', err);
        socket.close();
      };
    };
    
    connectWs();
    
    return () => {
      if (socket) socket.close();
      clearTimeout(reconnectTimeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, userProfile?.id, selectedDocId, currentView]);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const fetchUserProfile = async () => {
    try {
      const res = await api.get('/auth/me');
      setUserProfile(res.data);
      setIsAuthenticated(true);
      
      // Load user settings parameters
      if (res.data.settings) {
        setProfileName(res.data.full_name || '');
        setProfileAvatar(res.data.avatar_url || '');
        setSettingsTheme(res.data.settings.theme);
        setSettingsLanguage(res.data.settings.language);
        setSettingsOcrLang(res.data.settings.default_ocr_language);
        setSettingsNotify(res.data.settings.email_notifications);
      }
    } catch (err) {
      console.error('Profile fetch failed:', err);
      handleLogout();
    }
  };

  const loadViewData = () => {
    if (currentView === 'dashboard') {
      fetchDashboardStats();
    } else if (currentView === 'library') {
      fetchLibraryDocuments();
    } else if (currentView === 'admin') {
      fetchAdminData();
    } else if (currentView === 'workspace' && selectedDocId) {
      fetchWorkspaceDoc(selectedDocId);
    }
  };

  const fetchDashboardStats = async () => {
    try {
      const res = await api.get('/dashboard/stats');
      setStats(res.data);
    } catch (err) {
      console.error(err);
      showToast('Failed to fetch dashboard metrics.', 'error');
    }
  };

  const fetchLibraryDocuments = async () => {
    try {
      const params = {
        sort: sortOrder
      };
      if (searchQuery) params.search = searchQuery;
      if (filterType) params.doc_type = filterType;
      if (filterStatus) params.status = filterStatus;
      
      const res = await api.get('/document/list', { params });
      setDocuments(res.data);
    } catch (err) {
      console.error(err);
      showToast('Failed to retrieve library documents.', 'error');
    }
  };

  const fetchWorkspaceDoc = async (docId) => {
    try {
      // 1. Fetch complete document metadata & OCR text from our new endpoint
      const meta = await api.get(`/document/${docId}`);
      setSelectedDoc(meta.data);
      
      // 2. Fetch structured json data in the background if completed
      if (meta.data.ocr_status === 'COMPLETED') {
        setExtractedLoading(true);
        try {
          const ext = await api.get(`/document/${docId}/download-json`);
          setExtractedData(ext.data);
        } catch (e) {
          console.error("JSON fetch failed:", e);
          setExtractedData(null);
        }
        setExtractedLoading(false);
      } else {
        setExtractedData(null);
      }
      
      // 3. Clear workspace chat
      setChatHistory([]);
    } catch (err) {
      console.error(err);
      showToast('Failed to retrieve document details.', 'error');
      setCurrentView('library');
    }
  };

  const fetchAdminData = async () => {
    setAdminLoading(true);
    try {
      const statsRes = await api.get('/admin/analytics');
      const usersRes = await api.get('/admin/users');
      const logsRes = await api.get('/admin/logs');
      
      setAdminStats(statsRes.data);
      setAdminUsers(usersRes.data);
      setAdminLogs(logsRes.data);
    } catch (err) {
      console.error(err);
      showToast('Administrative access denied.', 'error');
      setCurrentView('dashboard');
    }
    setAdminLoading(false);
  };

  // =====================================================================
  // Auth Handlers
  // =====================================================================
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    if (!authEmail || !authPassword) {
      showToast('Please fill in all credentials.', 'error');
      return;
    }
    
    setAuthLoading(true);
    try {
      if (authTab === 'login') {
        const res = await api.post('/auth/login', {
          email: authEmail,
          password: authPassword
        });
        localStorage.setItem('access_token', res.data.access_token);
        localStorage.setItem('refresh_token', res.data.refresh_token);
        await fetchUserProfile();
        showToast('Login successful!');
      } else {
        await api.post('/auth/register', {
          email: authEmail,
          password: authPassword,
          full_name: authFullName || null
        });
        showToast('Account registered successfully. Please login.');
        setAuthTab('login');
        setAuthPassword('');
      }
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Authentication failed. Please verify fields.';
      showToast(errMsg, 'error');
    }
    setAuthLoading(false);
  };

  const handleLogout = async () => {
    try {
      if (localStorage.getItem('access_token')) {
        await api.post('/auth/logout');
      }
    } catch (e) {
      console.error(e);
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setIsAuthenticated(false);
    setUserProfile(null);
    setSelectedDocId(null);
    setSelectedDoc(null);
    setCurrentView('dashboard');
    setActiveUploads({});
    showToast('Logged out securely.');
  };

  // =====================================================================
  // Document Operations Handlers
  // =====================================================================
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (selectedFile) => {
    const name = selectedFile.name.toLowerCase();
    if (!name.endsWith('.pdf') && !name.endsWith('.png') && !name.endsWith('.jpg') && !name.endsWith('.jpeg')) {
      showToast('Only JPG, JPEG, PNG, or PDF formats are supported.', 'error');
      return;
    }
    
    setIsUploading(true);
    showToast('Uploading file. Processing OCR extraction...');
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    try {
      const res = await api.post('/document/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const docId = res.data.document_id;
      showToast('Document uploaded successfully!');
      
      // If the backend processed it synchronously (e.g. MOCK_VLM is true), load immediately.
      if (res.data.data || (res.data.message && res.data.message.includes("synchronously"))) {
        setSelectedDocId(docId);
        setCurrentView('workspace');
        fetchWorkspaceDoc(docId);
      } else {
        // Asynchronous processing: track via WebSockets
        setActiveUploads((prev) => ({
          ...prev,
          [docId]: { status: 'PENDING', progress: 10, message: 'File uploaded. Initializing pipeline...' }
        }));
        setSelectedDocId(docId);
        setCurrentView('workspace');
      }
    } catch (err) {
      console.error(err);
      const msg = err.response?.data?.detail || 'File upload analysis failed.';
      showToast(msg, 'error');
    }
    setIsUploading(false);
  };

  const handleRename = async (id) => {
    if (!renameVal.trim()) return;
    try {
      await api.post(`/document/${id}/rename`, { filename: renameVal.trim() });
      showToast('Document renamed.');
      setRenameId(null);
      setRenameVal('');
      
      // Refresh current viewed doc if applicable
      if (selectedDocId === id) {
        fetchWorkspaceDoc(id);
      }
      loadViewData();
    } catch (err) {
      console.error(err);
      showToast('Rename operation failed.', 'error');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to permanently delete this document index and purge physical files?')) return;
    try {
      await api.delete(`/document/${id}`);
      showToast('Document deleted.');
      if (selectedDocId === id) {
        setSelectedDocId(null);
        setSelectedDoc(null);
        setCurrentView('library');
      }
      loadViewData();
    } catch (err) {
      console.error(err);
      showToast('Delete operation failed.', 'error');
    }
  };

  // =====================================================================
  // RAG Chat Handler
  // =====================================================================
  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatQuestion.trim() || chatLoading) return;
    
    const query = chatQuestion.trim();
    setChatQuestion('');
    
    // Optimistic messaging state
    const newChatHistory = [...chatHistory, { sender: 'user', text: query }];
    setChatHistory(newChatHistory);
    setChatLoading(true);
    
    try {
      const res = await api.post('/document/chat', {
        document_id: selectedDocId,
        question: query
      });
      
      setChatHistory([
        ...newChatHistory,
        { sender: 'vlm', text: res.data.answer, sources: res.data.sources }
      ]);
    } catch (err) {
      console.error(err);
      showToast('Inference prompt failed.', 'error');
    }
    setChatLoading(false);
  };

  const handleMultiChatSubmit = async (e) => {
    e.preventDefault();
    if (!multiChatQuestion.trim() || multiChatLoading || selectedDocIds.length === 0) return;
    
    const query = multiChatQuestion.trim();
    setMultiChatQuestion('');
    
    const newChatHistory = [...multiChatHistory, { sender: 'user', text: query }];
    setMultiChatHistory(newChatHistory);
    setMultiChatLoading(true);
    
    try {
      const res = await api.post('/documents/chat', {
        document_ids: selectedDocIds,
        question: query
      });
      
      setMultiChatHistory([
        ...newChatHistory,
        { sender: 'vlm', text: res.data.answer, sources: res.data.sources }
      ]);
    } catch (err) {
      console.error(err);
      showToast('Multi-document inference failed.', 'error');
    }
    setMultiChatLoading(false);
  };

  // =====================================================================
  // Settings & Profile Updates
  // =====================================================================
  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    try {
      const payload = { full_name: profileName, avatar_url: profileAvatar || null };
      if (profilePassword) payload.new_password = profilePassword;
      
      await api.post('/profile/update', payload);
      setProfilePassword('');
      showToast('Profile settings updated.');
      fetchUserProfile();
    } catch (err) {
      console.error(err);
      showToast('Failed to update profile values.', 'error');
    }
  };

  const handleSettingsUpdate = async (themeOverride, langOverride, ocrLangOverride, notifyOverride) => {
    try {
      const themeVal = themeOverride !== undefined && themeOverride !== null ? themeOverride : settingsTheme;
      const langVal = langOverride !== undefined && langOverride !== null ? langOverride : settingsLanguage;
      const ocrLangVal = ocrLangOverride !== undefined && ocrLangOverride !== null ? ocrLangOverride : settingsOcrLang;
      const notifyVal = notifyOverride !== undefined && notifyOverride !== null ? notifyOverride : settingsNotify;

      await api.post('/settings/update', {
        theme: themeVal,
        language: langVal,
        default_ocr_language: ocrLangVal,
        email_notifications: notifyVal
      });
      showToast('Preferences updated.');
      
      // Update HTML theme classes
      if (themeVal === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    } catch (err) {
      console.error(err);
      showToast('Failed to save settings variables.', 'error');
    }
  };

  const handleDeleteAccount = async () => {
    if (!confirm('WARNING: Deleting your account will permanently purge all uploaded files, chats logs, and profile records. This action is irreversible. Proceed?')) return;
    try {
      await api.delete('/profile/delete-account');
      showToast('Account permanently closed.', 'warning');
      handleLogout();
    } catch (err) {
      console.error(err);
      showToast('Failed to delete account.', 'error');
    }
  };

  // =====================================================================
  // Admin Toggle Handler
  // =====================================================================
  const handleToggleUserStatus = async (userId) => {
    try {
      const res = await api.post(`/admin/users/${userId}/toggle-status`);
      showToast(res.data.message);
      fetchAdminData();
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to toggle status.', 'error');
    }
  };

  // =====================================================================
  // Render Auth view if not logged in
  // =====================================================================
  if (!isAuthenticated) {
    return (
      <AuthView 
        authTab={authTab}
        setAuthTab={setAuthTab}
        authEmail={authEmail}
        setAuthEmail={setAuthEmail}
        authPassword={authPassword}
        setAuthPassword={setAuthPassword}
        authFullName={authFullName}
        setAuthFullName={setAuthFullName}
        authLoading={authLoading}
        handleAuthSubmit={handleAuthSubmit}
        toast={toast}
      />
    );
  }

  // =====================================================================
  // Main Dashboard App layout
  // =====================================================================
  return (
    <div className="app-container">
      
      {/* Toast Alert */}
      <Toast toast={toast} />

      {/* Floating Active Tasks Upload Tracker */}
      <ActiveUploadsTracker activeUploads={activeUploads} />

      {/* Sidebar Navigation */}
      <Sidebar 
        currentView={currentView}
        setCurrentView={setCurrentView}
        userProfile={userProfile}
        handleLogout={handleLogout}
      />

      {/* Main View Area */}
      <main className="main-content">
        {currentView === 'dashboard' && (
          <DashboardView 
            stats={stats}
            isUploading={isUploading}
            dragActive={dragActive}
            handleDrag={handleDrag}
            handleDrop={handleDrop}
            handleFileChange={handleFileChange}
            fileInputRef={fileInputRef}
            setCurrentView={setCurrentView}
            setSelectedDocId={setSelectedDocId}
          />
        )}

        {currentView === 'library' && (
          <LibraryView 
            documents={documents}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            filterType={filterType}
            setFilterType={setFilterType}
            filterStatus={filterStatus}
            setFilterStatus={setFilterStatus}
            sortOrder={sortOrder}
            setSortOrder={setSortOrder}
            renameId={renameId}
            setRenameId={setRenameId}
            renameVal={renameVal}
            setRenameVal={setRenameVal}
            handleRename={handleRename}
            handleDelete={handleDelete}
            setSelectedDocId={setSelectedDocId}
            setCurrentView={setCurrentView}
            fileInputRef={fileInputRef}
            API_BASE_URL={API_BASE_URL}
            selectedDocIds={selectedDocIds}
            setSelectedDocIds={setSelectedDocIds}
          />
        )}

        {currentView === 'multi-workspace' && (
          <MultiWorkspaceView 
            selectedDocIds={selectedDocIds}
            setSelectedDocIds={setSelectedDocIds}
            documents={documents}
            chatHistory={multiChatHistory}
            setChatHistory={setMultiChatHistory}
            chatLoading={multiChatLoading}
            chatQuestion={multiChatQuestion}
            setChatQuestion={setMultiChatQuestion}
            handleChatSubmit={handleMultiChatSubmit}
            chatEndRef={chatEndRef}
            setCurrentView={setCurrentView}
            API_BASE_URL={API_BASE_URL}
          />
        )}

        {currentView === 'workspace' && selectedDoc && (
          <WorkspaceView 
            selectedDoc={selectedDoc}
            selectedDocId={selectedDocId}
            activeUploads={activeUploads}
            docTab={docTab}
            setDocTab={setDocTab}
            extractedLoading={extractedLoading}
            extractedData={extractedData}
            chatHistory={chatHistory}
            chatLoading={chatLoading}
            chatQuestion={chatQuestion}
            setChatQuestion={setChatQuestion}
            handleChatSubmit={handleChatSubmit}
            chatEndRef={chatEndRef}
            setCurrentView={setCurrentView}
            API_BASE_URL={API_BASE_URL}
          />
        )}

        {currentView === 'profile' && (
          <ProfileView 
            profileName={profileName}
            setProfileName={setProfileName}
            profileAvatar={profileAvatar}
            setProfileAvatar={setProfileAvatar}
            profilePassword={profilePassword}
            setProfilePassword={setProfilePassword}
            handleProfileUpdate={handleProfileUpdate}
            handleDeleteAccount={handleDeleteAccount}
          />
        )}

        {currentView === 'settings' && (
          <SettingsView 
            settingsTheme={settingsTheme}
            setSettingsTheme={setSettingsTheme}
            settingsLanguage={settingsLanguage}
            setSettingsLanguage={setSettingsLanguage}
            settingsOcrLang={settingsOcrLang}
            setSettingsOcrLang={setSettingsOcrLang}
            settingsNotify={settingsNotify}
            setSettingsNotify={setSettingsNotify}
            handleSettingsUpdate={handleSettingsUpdate}
          />
        )}

        {currentView === 'admin' && (
          <AdminView 
            adminLoading={adminLoading}
            adminStats={adminStats}
            adminUsers={adminUsers}
            adminLogs={adminLogs}
            userProfile={userProfile}
            handleToggleUserStatus={handleToggleUserStatus}
          />
        )}
      </main>
    </div>
  );
}

export default App;
