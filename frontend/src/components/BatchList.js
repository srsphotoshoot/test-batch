// import React from 'react';

// const BatchList = ({ batches, onSelectBatch }) => {
//   const getStatusColor = (status) => {
//     switch(status) {
//       case 'pending': return '#ffc107';
//       case 'queued': return '#0dcaf0';
//       case 'generating': return '#0d6efd';
//       case 'done': return '#198754';
//       case 'error': return '#dc3545';
//       default: return '#6c757d';
//     }
//   };

//   const getStatusIcon = (status) => {
//     switch(status) {
//       case 'pending': return '⏳';
//       case 'queued': return '📋';
//       case 'generating': return '⚙️';
//       case 'done': return '✅';
//       case 'error': return '❌';
//       default: return '❓';
//     }
//   };

//   if (batches.length === 0) {
//     return (
//       <div className="empty-state">
//         <p>No batches yet. Create one to get started!</p>
//       </div>
//     );
//   }

//   return (
//     <div className="batch-list">
//       <h2>Recent Batches</h2>
//       <div className="batches-grid">
//         {batches.map(batch => (
//           <div key={batch.id} className="batch-card" onClick={() => onSelectBatch(batch.id)}>
//             <div className="batch-header">
//               <h3>{batch.output_name}</h3>
//               <span 
//                 className="status-badge"
//                 style={{ backgroundColor: getStatusColor(batch.status) }}
//               >
//                 {getStatusIcon(batch.status)} {batch.status}
//               </span>
//             </div>
//             <div className="batch-meta">
//               <p><small>ID: {batch.id}</small></p>
//               <p><small>Created: {new Date(batch.created_at).toLocaleDateString()}</small></p>
//             </div>
//             <div className="batch-images">
//               {batch.has_main && <span className="image-indicator" title="Main image">📷</span>}
//               {batch.has_ref1 && <span className="image-indicator" title="Reference 1">📷</span>}
//               {batch.has_ref2 && <span className="image-indicator" title="Reference 2">📷</span>}
//               {batch.has_generated && <span className="image-indicator generated" title="Generated">✨</span>}
//             </div>
//           </div>
//         ))}
//       </div>
//     </div>
//   );
// };

// export default BatchList;

import React, { useState } from 'react';

const BatchList = ({ batches, onSelectBatch, userRole, token, apiBaseUrl, onBatchDeleted }) => {
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [generatingId, setGeneratingId] = useState(null);

  const handleDelete = async (e, batchId) => {
    e.stopPropagation(); // Prevents opening the batch
    
    try {
      const res = await fetch(`${apiBaseUrl}/api/batch/${batchId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        if (onBatchDeleted) onBatchDeleted();
      }
    } catch (err) {
      console.error('Error deleting batch:', err);
    }
  };

  const handleGenerate = async (e, batchId) => {
    e.stopPropagation();
    setGeneratingId(batchId);
    
    try {
      const res = await fetch(`${apiBaseUrl}/api/batch/${batchId}/generate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        if (onBatchDeleted) onBatchDeleted(); // Silent refresh
      } else {
        const data = await res.json();
        alert('Failed to generate: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      console.error('Error starting generation:', err);
      alert('Error starting generation: ' + err.message);
    } finally {
      setGeneratingId(null);
    }
  };

  const handleDownload = async (e, batchId, outputName) => {
    e.stopPropagation();
    try {
      const res = await fetch(`${apiBaseUrl}/api/batch/${batchId}/generated-image/raw`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!res.ok) throw new Error('Failed to fetch image');
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${outputName || 'generated_image'}.png`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download err:', err);
      alert('Failed to download image: ' + err.message);
    }
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'pending': return '#f59e0b';
      case 'queued': return '#06b6d4';
      case 'generating': return '#3b82f6';
      case 'done': return '#22c55e';
      case 'error': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getStatusIcon = (status) => {
    switch(status) {
      case 'pending': return '⏳';
      case 'queued': return '📋';
      case 'generating': return '⚙️';
      case 'done': return '✅';
      case 'error': return '❌';
      default: return '❓';
    }
  };

  const getProgress = (status) => {

    switch(status) {
      case 'pending': return 10;
      case 'queued': return 30;
      case 'generating': return 70;
      case 'done': return 100;
      case 'error': return 100;
      default: return 0;
    }

  };

  if (batches.length === 0) {
    return (
      <div className="empty-state">
        <p>No batches yet. Create one to get started!</p>
      </div>
    );
  }

  return (
    <div className="batch-list">

      <h2>Recent Batches</h2>

      <div className="batches-grid">

        {batches.map(batch => {

          const progress = getProgress(batch.status);

          return (

            <div
              key={batch.id}
              className="batch-card"
              onClick={() => onSelectBatch(batch.id)}
            >

              <div className="batch-header">
                  <div className="batch-title-group">
                    <h3>{batch.output_name}</h3>
                    <div className="card-actions-row">
                      {(batch.status === 'pending' || batch.status === 'failed' || batch.status === 'error') && (
                        <button 
                          className={`btn btn-sm btn-generate-card ${generatingId === batch.id ? 'loading' : ''}`}
                          onClick={(e) => handleGenerate(e, batch.id)}
                          disabled={generatingId === batch.id}
                        >
                          {generatingId === batch.id ? '⚙️...' : '🚀 Generate'}
                        </button>
                      )}
                      {batch.status === 'done' && (
                        <button 
                          className="btn btn-sm btn-download-card"
                          onClick={(e) => handleDownload(e, batch.id, batch.output_name)}
                        >
                          ⬇️ Download
                        </button>
                      )}
                      {userRole === 'admin' && (
                        <div className="card-delete-container">
                          {confirmDeleteId === batch.id ? (
                            <div className="card-confirm-overlay" onClick={(e) => e.stopPropagation()}>
                              <button 
                                className="btn btn-sm btn-danger btn-solid-red"
                                onClick={(e) => {
                                  handleDelete(e, batch.id);
                                  setConfirmDeleteId(null);
                                }}
                              >
                                CONFIRM?
                              </button>
                            </div>
                          ) : (
                            <button 
                              className="delete-card-btn"
                              onClick={(e) => {
                                e.stopPropagation();
                                setConfirmDeleteId(batch.id);
                              }}
                              title="Delete Batch Permanently"
                            >
                              🗑️
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                <span
                  className="status-badge"
                  style={{ backgroundColor: getStatusColor(batch.status) }}
                >
                  {getStatusIcon(batch.status)} {batch.status}
                </span>
              </div>

              <div className="batch-meta">

                <div>ID</div>
                <div>{batch.id}</div>

                <div>Created</div>
                <div>{new Date(batch.created_at).toLocaleDateString()}</div>

              </div>

              {/* PROGRESS BAR */}

              <div className="progress-bar">

                <div
                  className="progress-fill"
                  style={{
                    width: `${progress}%`,
                    backgroundColor: getStatusColor(batch.status)
                  }}
                />

              </div>

              {/* IMAGE INDICATORS */}

              <div className="batch-images">

                {batch.has_main &&
                  <span className="image-indicator" title="Main image">📷</span>
                }

                {batch.has_ref1 &&
                  <span className="image-indicator" title="Reference 1">📷</span>
                }

                {batch.has_ref2 &&
                  <span className="image-indicator" title="Reference 2">📷</span>
                }

                {batch.has_generated &&
                  <span className="image-indicator generated" title="Generated">
                    ✨
                  </span>
                }

              </div>

            </div>

          );
        })}

      </div>

    </div>
  );
};

export default BatchList;
