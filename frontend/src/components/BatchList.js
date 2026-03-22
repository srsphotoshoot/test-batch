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

import React from 'react';

const BatchList = ({ batches, onSelectBatch, userRole, token, apiBaseUrl, onBatchDeleted }) => {
  const handleDelete = async (e, batchId) => {
    e.stopPropagation(); // Prevents opening the batch
    if (!window.confirm('Delete this batch permanently? This will NOT reduce your batch count.')) return;
    
    try {
      const res = await fetch(`${apiBaseUrl}/api/batch/${batchId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        if (onBatchDeleted) onBatchDeleted();
      } else {
        alert('Failed to delete batch');
      }
    } catch (err) {
      console.error('Error deleting batch:', err);
      alert('Error deleting batch: ' + err.message);
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
                  {userRole === 'admin' && (
                    <button 
                      className="delete-card-btn"
                      onClick={(e) => handleDelete(e, batch.id)}
                      title="Delete Batch Permanently"
                    >
                      🗑️
                    </button>
                  )}
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
