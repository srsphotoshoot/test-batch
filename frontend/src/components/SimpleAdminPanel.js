import React, { useState, useEffect } from 'react';
import './SimpleAdminPanel.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

function SimpleAdminPanel({ token, user }) {
  const [allBatches, setAllBatches] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (user?.role === 'admin') {
      loadAdminData();
    }
  }, [user, token]);

  const loadAdminData = async () => {
    setLoading(true);
    setError('');
    try {
      // Load all batches
      const batchRes = await fetch(`${API_BASE_URL}/api/batches`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });

      if (batchRes.ok) {
        const batchData = await batchRes.json();
        const batches = Array.isArray(batchData) ? batchData : batchData.batches || [];
        setAllBatches(batches);
      }

      // Load stats
      const statsRes = await fetch(`${API_BASE_URL}/api/admin/stats`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData.stats);
      }
    } catch (err) {
      setError('Error loading admin data: ' + err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      'pending': '#f59e0b',
      'queued': '#06b6d4',
      'generating': '#3b82f6',
      'completed': '#22c55e',
      'done': '#22c55e',
      'failed': '#ef4444',
      'error': '#ef4444'
    };
    return colors[status] || '#6b7280';
  };

  if (user?.role !== 'admin') {
    return (
      <div className="admin-panel-access-denied">
        <p>❌ Admin access required</p>
      </div>
    );
  }

  return (
    <div className="simple-admin-panel">
      <div className="admin-header">
        <h1>🔧 Admin Control Panel</h1>
        <button onClick={loadAdminData} className="refresh-btn">🔄 Refresh</button>
      </div>

      {error && <div className="error-alert">{error}</div>}

      {loading ? (
        <div className="loading">Loading admin data...</div>
      ) : (
        <>
          {/* Stats Section */}
          {stats && (
            <div className="stats-section">
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

          {/* All Batches Section */}
          <div className="batches-section">
            <h2>📋 All Batches ({allBatches.length})</h2>
            {allBatches.length === 0 ? (
              <div className="empty-state">No batches found</div>
            ) : (
              <div className="batches-list">
                <div className="batch-header">
                  <div className="col-name">Name</div>
                  <div className="col-status">Status</div>
                  <div className="col-date">Created</div>
                  <div className="col-resolution">Resolution</div>
                </div>
                {allBatches.map((batch) => (
                  <div key={batch.id} className="batch-row">
                    <div className="col-name">{batch.output_name || 'Unnamed'}</div>
                    <div className="col-status">
                      <span 
                        className="status-badge"
                        style={{ backgroundColor: getStatusColor(batch.status) }}
                      >
                        {batch.status}
                      </span>
                    </div>
                    <div className="col-date">
                      {batch.created_at 
                        ? new Date(batch.created_at).toLocaleDateString()
                        : 'N/A'
                      }
                    </div>
                    <div className="col-resolution">{batch.resolution || 'N/A'}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default SimpleAdminPanel;
