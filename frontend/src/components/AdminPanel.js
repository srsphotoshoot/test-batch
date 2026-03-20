import React, { useState, useEffect } from 'react';
import './AdminPanel.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

function AdminPanel({ token }) {
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState(null);
  const [uploadStats, setUploadStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState('stats');
  const [systemHealth, setSystemHealth] = useState(null);
  const [queueInfo, setQueueInfo] = useState(null);
  const [allBatches, setAllBatches] = useState([]);
  const [signupCode, setSignupCode] = useState('');

  // Auto-refresh data
  useEffect(() => {
    loadAllData();
    const interval = setInterval(loadAllData, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const loadAllData = async () => {
    setLoading(true);
    setError('');

    try {
      // Load system health
      await loadSystemHealth();

      // Load queue info
      await loadQueueInfo();

      // Load stats only if admin
      if (token) {
        await loadStats();
        await loadUsers();
        await loadUploadStats();
        await loadAllBatches();
        await loadSignupCode();
      }
    } catch (err) {
      console.error('Error loading admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadSystemHealth = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      if (res.ok) {
        const data = await res.json();
        setSystemHealth(data);
      }
    } catch (err) {
      console.error('Error loading system health:', err);
    }
  };

  const loadQueueInfo = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/queue/status`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const data = await res.json();
        setQueueInfo(data);
      }
    } catch (err) {
      console.error('Error loading queue info:', err);
    }
  };

  const loadStats = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/stats`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || {});
      } else if (res.status === 403) {
        setError('Admin access required');
      }
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  };

  const loadUsers = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/users`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
      }
    } catch (err) {
      console.error('Error loading users:', err);
    }
  };

  const loadUploadStats = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/upload-stats`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setUploadStats(data.upload_stats || {});
      }
    } catch (err) {
      console.error('Error loading upload stats:', err);
    }
  };

  const loadAllBatches = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/batches/all`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setAllBatches(data || []);
      }
    } catch (err) {
      console.error('Error loading batches:', err);
    }
  };

  const loadSignupCode = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/signup-code`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSignupCode(data.code || '');
      }
    } catch (err) {
      console.error('Error loading signup code:', err);
    }
  };

  const rotateSignupCode = async () => {
    if (!window.confirm('Generate a new signup code? New users will need the new code.')) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/signup-code/rotate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSignupCode(data.code);
        setSuccess('Signup code rotated successfully');
        setTimeout(() => setSuccess(''), 3000);
      }
    } catch (err) {
      setError('Error rotating signup code: ' + err.message);
    }
  };

  const updateUserLimits = async (userId, limitChange) => {
    const user = users.find(u => u.id === userId);
    if (!user) return;

    const newLimit = (user.batch_limit || 50) + limitChange;
    if (newLimit < 0) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/users/${userId}/limits?batch_limit=${newLimit}`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        setUsers(users.map(u => u.id === userId ? { ...u, batch_limit: newLimit } : u));
        setSuccess('User limits updated');
        setTimeout(() => setSuccess(''), 2000);
      }
    } catch (err) {
      setError('Error updating limits: ' + err.message);
    }
  };

  const deleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        setSuccess('User deleted successfully');
        setUsers(users.filter(u => u.id !== userId));
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError('Failed to delete user');
      }
    } catch (err) {
      setError('Error deleting user: ' + err.message);
    }
  };

  const clearUploadCache = async () => {
    if (!window.confirm('Clear all upload cache? This cannot be undone.')) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/clear-cache`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        setSuccess('Upload cache cleared successfully');
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError('Failed to clear cache');
      }
    } catch (err) {
      setError('Error clearing cache: ' + err.message);
    }
  };

  return (
    <div className="admin-panel">
      <div className="admin-header">
        <h1>🔧 Admin Dashboard</h1>
        <div className="admin-controls">
          <button
            className={`tab-btn ${activeTab === 'stats' ? 'active' : ''}`}
            onClick={() => setActiveTab('stats')}
          >
            📊 Statistics
          </button>
          <button
            className={`tab-btn ${activeTab === 'uploads' ? 'active' : ''}`}
            onClick={() => setActiveTab('uploads')}
          >
            📤 Uploads
          </button>
          <button
            className={`tab-btn ${activeTab === 'batches' ? 'active' : ''}`}
            onClick={() => setActiveTab('batches')}
          >
            📋 All Batches
          </button>
          <button
            className={`tab-btn ${activeTab === 'users' ? 'active' : ''}`}
            onClick={() => setActiveTab('users')}
          >
            👥 Users
          </button>
          <button
            className={`tab-btn ${activeTab === 'system' ? 'active' : ''}`}
            onClick={() => setActiveTab('system')}
          >
            ⚙️ System
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">❌ {error}</div>}
      {success && <div className="alert alert-success">✅ {success}</div>}

      {loading && !stats && <div className="loading">Loading admin data...</div>}

      {/* Statistics Tab */}
      {activeTab === 'stats' && stats && (
        <div className="admin-section">
          <h2>📊 System Statistics</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Total Users</div>
              <div className="stat-value">{stats.total_users || 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total Batches</div>
              <div className="stat-value">{stats.total_batches || 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Processing</div>
              <div className="stat-value">{queueInfo?.generating || 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Queued</div>
              <div className="stat-value">{queueInfo?.queued || 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Completed</div>
              <div className="stat-value">{stats.completed_batches || 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Failed</div>
              <div className="stat-value">{stats.failed_batches || 0}</div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Stats Tab */}
      {activeTab === 'uploads' && uploadStats && (
        <div className="admin-section">
          <div className="section-header">
            <h2>📤 Image Upload Statistics</h2>
            <button className="btn btn-danger" onClick={clearUploadCache}>
              🗑️ Clear Cache
            </button>
          </div>

          <div className="upload-stats-grid">
            <div className="stat-card">
              <div className="stat-label">Total Uploads</div>
              <div className="stat-value">{uploadStats.total_uploads || 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Avg Size Original</div>
              <div className="stat-value">{(uploadStats.avg_size_original_mb || 0).toFixed(2)} MB</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Avg Size Compressed</div>
              <div className="stat-value">{(uploadStats.avg_size_compressed_mb || 0).toFixed(2)} MB</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Avg Compression</div>
              <div className="stat-value">{(uploadStats.avg_compression_ratio || 1).toFixed(2)}x</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Space Saved</div>
              <div className="stat-value">{(uploadStats.total_space_saved_mb || 0).toFixed(2)} MB</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Success Rate</div>
              <div className="stat-value">{(uploadStats.success_rate || 100).toFixed(1)}%</div>
            </div>
          </div>

          <div className="upload-optimization-info">
            <h3>🚀 Upload Optimization</h3>
            <ul>
              <li>✅ Images automatically compressed on upload</li>
              <li>✅ Average {(uploadStats.avg_compression_ratio || 1).toFixed(1)}x file size reduction</li>
              <li>✅ {(uploadStats.total_space_saved_mb || 0).toFixed(2)} MB total space saved</li>
              <li>✅ Async processing prevents 503 errors</li>
              <li>✅ Smart compression based on file size and quality requirements</li>
            </ul>
          </div>
        </div>
      )}

      {/* All Batches Tab */}
      {activeTab === 'batches' && (
        <div className="admin-section">
          <h2>📋 All Batches ({allBatches.length} batches)</h2>
          <div className="batches-table">
            <div className="table-header">
              <div className="col-id">Batch ID</div>
              <div className="col-name">Output Name</div>
              <div className="col-status">Status</div>
              <div className="col-created">Created</div>
              <div className="col-resolution">Resolution</div>
              <div className="col-pose">Pose</div>
            </div>
            {allBatches.length === 0 ? (
              <div className="empty-state">No batches found</div>
            ) : (
              allBatches.map(batch => (
                <div key={batch.id} className="table-row">
                  <div className="col-id"><small>{batch.id.substring(0, 8)}...</small></div>
                  <div className="col-name">{batch.output_name}</div>
                  <div className="col-status">
                    <span className={`status-badge status-${batch.status}`}>
                      {batch.status}
                    </span>
                  </div>
                  <div className="col-created">
                    <small>{new Date(batch.created_at).toLocaleDateString()}</small>
                  </div>
                  <div className="col-resolution">{batch.resolution || 'N/A'}</div>
                  <div className="col-pose">{batch.pose || 'N/A'}</div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div className="admin-section">
          <h2>👥 User Management ({users.length} users)</h2>
          <div className="users-table">
            <div className="table-header">
              <div className="col-email">Email / Name</div>
              <div className="col-role">Role</div>
              <div className="col-batches">Batches / Limit</div>
              <div className="col-status">Status</div>
              <div className="col-actions">Actions</div>
            </div>
            {users.map(user => (
              <div key={user.id} className="table-row">
                <div className="col-email">
                  <div className="user-email">{user.email}</div>
                  <div className="user-name">
                    {user.first_name || user.last_name ?
                      `👤 ${user.first_name || ''} ${user.last_name || ''}` :
                      'Unnamed User'}
                  </div>
                </div>
                <div className="col-role">
                  <span className={`role-badge role-${user.role}`}>
                    {user.role}
                  </span>
                </div>
                <div className="col-batches">
                  <div className="batch-stats">
                    <span className="count">{user.batch_count || 0}</span>
                    <span className="separator">/</span>
                    <span className="limit">{user.batch_limit || 50}</span>
                  </div>
                  <div className="limit-controls">
                    <button onClick={() => updateUserLimits(user.id, -5)} className="btn-limit">-5</button>
                    <button onClick={() => updateUserLimits(user.id, 5)} className="btn-limit">+5</button>
                  </div>
                </div>
                <div className="col-status">
                  <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                    {user.is_active ? '🟢 Active' : '🔴 Inactive'}
                  </span>
                </div>
                <div className="col-actions">
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={() => deleteUser(user.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* System Health Tab */}
      {activeTab === 'system' && systemHealth && (
        <div className="admin-section">
          <h2>⚙️ System Health</h2>
          <div className="system-info">
            <div className="info-block">
              <h3>🟢 Status</h3>
              <p>API Server: <strong>Running</strong></p>
              <p>Database: <strong>{systemHealth.database || 'Connected'}</strong></p>
              <p>Gemini API: <strong>{systemHealth.gemini || 'Ready'}</strong></p>

              <div className="signup-code-box">
                <h4>🔑 Current Signup Code</h4>
                <div className="code-display">
                  <code>{signupCode}</code>
                  <button className="btn btn-sm" onClick={rotateSignupCode}>🔄 Rotate Code</button>
                </div>
                <p className="hint">Share this code with new users to allow signup.</p>
              </div>
            </div>

            <div className="info-block">
              <h3>📊 Configuration</h3>
              <p>Environment: <strong>{systemHealth.environment || 'Production'}</strong></p>
              <p>API Version: <strong>{systemHealth.version || '1.0.0'}</strong></p>
              <p>Debug Mode: <strong>{systemHealth.debug ? 'Enabled' : 'Disabled'}</strong></p>
            </div>

            <div className="info-block">
              <h3>🔧 Optimization Settings</h3>
              <ul>
                <li>Timeout Keep-Alive: 5 seconds</li>
                <li>Worker Processes: 4</li>
                <li>Max Concurrent Connections: 100</li>
                <li>GZIP Compression: Enabled</li>
                <li>Max Upload Size: 50 MB</li>
                <li>Auto Image Compression: Enabled</li>
              </ul>
            </div>
          </div>

          <div className="system-notes">
            <h3>📝 Notes</h3>
            <ul>
              <li>✅ Image uploads are automatically optimized to prevent 503 errors</li>
              <li>✅ Async processing allows concurrent uploads without blocking</li>
              <li>✅ Multiple workers handle requests efficiently</li>
              <li>✅ GZIP compression reduces response size</li>
              <li>✅ Keep-alive timeout prevents premature disconnections</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminPanel;
