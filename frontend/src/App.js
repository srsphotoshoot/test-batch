import React, { useState, useEffect } from 'react';
import './App.css';
import BatchList from './components/BatchList';
import BatchDetail from './components/BatchDetail';
import CreateBatch from './components/CreateBatch';
import BubbleBackground from './components/BubbleBackground';
import QueueDashboard from './components/QueueDashboard';
import LoginSignup from './components/LoginSignup';
import AdminPanel from './components/AdminPanel';

import API_BASE_URL from './api_config';

function App() {
  const [currentView, setCurrentView] = useState(() => {
    const token = sessionStorage.getItem('token');
    if (!token) return 'login';
    
    // Support Deep Linking on Refresh
    const path = window.location.pathname;
    if (path.includes('/admin')) return 'admin';
    if (path.includes('/create')) return 'create';
    if (path.includes('/batch/')) return 'detail';
    return 'list';
  });

  const [selectedBatchId, setSelectedBatchId] = useState(() => {
    const path = window.location.pathname;
    if (path.includes('/batch/')) {
      return path.split('/batch/')[1].split('/')[0];
    }
    return null;
  });

  // Sync URL with View (for stable Refresh)
  useEffect(() => {
    if (currentView === 'list') window.history.pushState({}, '', '/');
    else if (currentView === 'login') window.history.pushState({}, '', '/login');
    else if (currentView === 'admin') window.history.pushState({}, '', '/admin');
    else if (currentView === 'create') window.history.pushState({}, '', '/create');
    else if (currentView === 'detail' && selectedBatchId) {
      window.history.pushState({}, '', `/batch/${selectedBatchId}`);
    }
  }, [currentView, selectedBatchId]);
  const [batches, setBatches] = useState([]);
  const [config, setConfig] = useState(null);
  const [queueStatus, setQueueStatus] = useState({ queued: 0, generating: 0 });
  const [token, setToken] = useState(() => sessionStorage.getItem('token'));
  const [user, setUser] = useState(() => {
    const stored = sessionStorage.getItem('user');
    return stored ? JSON.parse(stored) : null;
  });

  // ---------------------------------------------------------
  // 120s INACTIVITY TIMEOUT & TAB CLOSE PROTECTION
  // ---------------------------------------------------------
  useEffect(() => {
    if (!token) return;

    let timeoutId;
    const TIMEOUT_MS = 120000; // 120 seconds

    const resetTimer = () => {
      if (timeoutId) clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        console.log("Inactivity timeout reached (120s). Logging out...");
        handleLogout();
      }, TIMEOUT_MS);
    };

    // Events to track user activity
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];

    events.forEach(event => {
      document.addEventListener(event, resetTimer);
    });

    // Initial timer start
    resetTimer();

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
      events.forEach(event => {
        document.removeEventListener(event, resetTimer);
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // ---------------------------------------------------------

  useEffect(() => {
    if (currentView !== 'login' && token) {
      loadConfig();
      loadBatches();
      loadQueueStatus();
    }

    const interval = setInterval(() => {
      if (currentView !== 'login' && token) {
        loadBatches();
        loadQueueStatus();
      }
    }, 5000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentView, token]);

  const loadQueueStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/queue/status`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const data = await res.json();
        setQueueStatus(data);
      }
    } catch (err) {
      console.error('Error loading queue status:', err);
    }
  };

  const loadConfig = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/config`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      }
    } catch (err) {
      console.error('Error loading config:', err);
    }
  };

  const loadBatches = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/batches`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const data = await res.json();
        // Handle both old format (array) and new format (object with batches array)
        if (Array.isArray(data)) {
          setBatches(data);
        } else if (data.batches) {
          setBatches(data.batches);
        } else {
          setBatches([]);
        }
      }
    } catch (err) {
      console.error('Error loading batches:', err);
    }
  };

  const handleLoginSuccess = (loginData) => {
    const token = loginData.access_token;
    const userData = {
      id: loginData.user_id,
      email: loginData.email,
      role: loginData.role
    };

    setToken(token);
    setUser(userData);
    // Use sessionStorage for security (Tab Close = Sign Out)
    sessionStorage.setItem('token', token);
    sessionStorage.setItem('user', JSON.stringify(userData));

    if (userData.role === 'admin') {
      setCurrentView('admin');
    } else {
      setCurrentView('list');
    }
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('user');
    setCurrentView('login');
  };

  const handleBackToList = () => {
    setSelectedBatchId(null);
    setCurrentView('list');
  };

  // Render login screen if not authenticated
  if (!token) {
    return (
      <div className="app">
        <BubbleBackground />
        <LoginSignup onLoginSuccess={handleLoginSuccess} />
      </div>
    );
  }

  // Render main app if authenticated
  return (
    <div className="app">
      <BubbleBackground />

      {/* Navigation Bar */}
      <nav className="navbar">
        <div className="navbar-brand">
          <img src="/2.png" alt="SRS Logo" className="navbar-logo" />
          <h1>🎨 Shree Radha Studio (SRS)</h1>
        </div>

        <div className="navbar-center">
          <div className="user-info">
            <span>👤 {user?.email}</span>
            <span className={`role-badge ${user?.role === 'admin' ? 'admin' : 'user'}`}>
              {user?.role === 'admin' ? '🔐 Admin' : 'User'}
            </span>
          </div>
        </div>

        <div className="navbar-end">
          {user?.role === 'admin' && (
            <button
              className="btn btn-primary"
              onClick={() => setCurrentView('admin')}
            >
              🔐 Admin Panel
            </button>
          )}
          <button
            className="btn btn-secondary"
            onClick={handleLogout}
          >
            🚪 Logout
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <div className="app-container">
        {/* Admin Panel View - More resilient check */}
        {currentView === 'admin' && (user?.role === 'admin' || sessionStorage.getItem('user')?.includes('"role":"admin"')) && (
          <div className="view-container">
            <button
              className="btn btn-secondary"
              onClick={() => setCurrentView('list')}
              style={{ marginBottom: '20px' }}
            >
              ← Back to Batches
            </button>
            <AdminPanel token={token} />
          </div>
        )}

        {/* Batch List View */}
        {currentView === 'list' && (
          <div className="view-container">
            <div className="view-header">
              <h2>📋 Batch Management</h2>
              <button
                className="btn btn-primary"
                onClick={() => setCurrentView('create')}
              >
                ➕ Create New Batch
              </button>
            </div>

            <div className="stats-bar">
              <div className="stat">
                <span>⏳ Queued:</span>
                <strong>{queueStatus.queued}</strong>
              </div>
              <div className="stat">
                <span>⚙️ Generating:</span>
                <strong>{queueStatus.generating}</strong>
              </div>
              <div className="stat">
                <span>📦 Total:</span>
                <strong>{batches.length}</strong>
              </div>
            </div>

            <BatchList
              batches={batches}
              onSelectBatch={(batchId) => {
                setSelectedBatchId(batchId);
                setCurrentView('detail');
              }}
              apiBaseUrl={API_BASE_URL}
              token={token}
              onBatchDeleted={loadBatches}
            />
          </div>
        )}

        {/* Create Batch View */}
        {currentView === 'create' && (
          <div className="view-container">
            <button
              className="btn btn-secondary"
              onClick={() => setCurrentView('list')}
            >
              ← Back to List
            </button>

            <CreateBatch
              config={config}
              apiBaseUrl={API_BASE_URL}
              token={token}
              onBatchCreated={() => {
                loadBatches();
                setCurrentView('list');
              }}
            />
          </div>
        )}

        {/* Batch Detail View */}
        {currentView === 'detail' && selectedBatchId && (
          <div className="view-container">
            <button
              className="btn btn-secondary"
              onClick={handleBackToList}
            >
              ← Back to List
            </button>

            <BatchDetail
              batchId={selectedBatchId}
              apiBaseUrl={API_BASE_URL}
              token={token}
              onBatchUpdated={loadBatches}
            />
          </div>
        )}

        {/* Queue Dashboard View */}
        {currentView === 'dashboard' && (
          <div className="view-container">
            <button
              className="btn btn-secondary"
              onClick={() => setCurrentView('list')}
            >
              ← Back to List
            </button>

            <QueueDashboard
              queueStatus={queueStatus}
              apiBaseUrl={API_BASE_URL}
              token={token}
            />
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="app-footer">
        <p>Shree Radha Studio (SRS) | Professional Batch Studio v1.2</p>
      </footer>
    </div>
  );
}

export default App;
