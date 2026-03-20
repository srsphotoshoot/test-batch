import React, { useState, useEffect } from 'react';
import './App.css';
import BatchList from './components/BatchList';
import BatchDetail from './components/BatchDetail';
import CreateBatch from './components/CreateBatch';
import BubbleBackground from './components/BubbleBackground';
import QueueDashboard from './components/QueueDashboard';
import LoginSignup from './components/LoginSignup';
import AdminPanel from './components/AdminPanel';

const API_BASE_URL =
  process.env.NODE_ENV === 'production'
    ? ''
    : process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

function App() {
  const [currentView, setCurrentView] = useState(() => {
    return localStorage.getItem('token') ? 'list' : 'login';
  });

  const [selectedBatchId, setSelectedBatchId] = useState(null);
  const [batches, setBatches] = useState([]);
  const [config, setConfig] = useState(null);
  const [queueStatus, setQueueStatus] = useState({ queued: 0, generating: 0 });
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('user');
    return stored ? JSON.parse(stored) : null;
  });

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
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));

    if (userData.role === 'admin') {
      setCurrentView('admin');
    } else {
      setCurrentView('list');
    }
    console.log('Login successful, user role:', userData.role, 'currentView:', userData.role === 'admin' ? 'admin' : 'list');
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
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
          <h1>🎨 SRS Batch Mode</h1>
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
        {currentView === 'admin' && (user?.role === 'admin' || localStorage.getItem('user')?.includes('"role":"admin"')) && (
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
        <p>SRS Batch Mode v1.0 | Powered by React + FastAPI</p>
      </footer>
    </div>
  );
}

export default App;
