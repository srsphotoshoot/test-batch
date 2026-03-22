import React, { useState, useEffect } from 'react';
import { compressImage } from '../utils/imageUtils';

const BatchDetail = ({ batchId, apiBaseUrl, onBatchUpdated }) => {
  const [batch, setBatch] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploadingRoles, setUploadingRoles] = useState({ main: false, ref1: false, ref2: false });
  const [localPreviews, setLocalPreviews] = useState({ main: null, ref1: null, ref2: null });
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    loadBatchDetail();
    loadBatchDetail();
    const interval = setInterval(loadBatchDetail, 3000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId]);

  const loadBatchDetail = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/api/batch/${batchId}`);
      if (!res.ok) throw new Error('Batch not found');
      const data = await res.json();
      setBatch(data);
      setLoading(false);
    } catch (err) {
      console.error('Error loading batch:', err);
      setLoading(false);
    }
  };

  const [uploadProgress, setUploadProgress] = useState({}); // { role: percentage }

  const handleImageUpload = async (role, file) => {
    if (!file) return;

    // 1. Instant Local Preview
    const localUrl = URL.createObjectURL(file);
    setLocalPreviews(prev => ({ ...prev, [role]: localUrl }));
    setUploadingRoles(prev => ({ ...prev, [role]: true }));
    setUploadProgress(prev => ({ ...prev, [role]: 0 }));

    try {
      // 2. Client-side compression
      console.log(`[${role}] Original size: ${(file.size / 1024 / 1024).toFixed(2)}MB`);
      const compressedBlob = await compressImage(file, 2048, 0.85);
      console.log(`[${role}] Compressed size: ${(compressedBlob.size / 1024 / 1024).toFixed(2)}MB`);

      // Update local preview with compressed one if possible
      const compressedUrl = URL.createObjectURL(compressedBlob);
      setLocalPreviews(prev => ({ ...prev, [role]: compressedUrl }));

      // 3. Upload with Progress via XHR
      const formData = new FormData();
      formData.append('file', compressedBlob, file.name);

      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${apiBaseUrl}/api/batch/${batchId}/upload/${role}`, true);

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percentComplete = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(prev => ({ ...prev, [role]: percentComplete }));
        }
      };

      xhr.onload = async () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          console.log(`✅ Upload complete for ${role}`);
          setUploadProgress(prev => ({ ...prev, [role]: 100 }));
          
          // Optimistic update of local batch state
          setBatch(prev => {
            if (!prev) return prev;
            return {
              ...prev,
              [`has_${role}`]: true
            };
          });

          // Reload background data
          loadBatchDetail();
          setUploadingRoles(prev => ({ ...prev, [role]: false }));
        } else {
          console.error(`Upload failed for ${role}:`, xhr.responseText);
          alert(`Upload failed for ${role}: ` + xhr.responseText);
          setUploadingRoles(prev => ({ ...prev, [role]: false }));
          setLocalPreviews(prev => ({ ...prev, [role]: null })); // Revert preview on error
        }
      };

      xhr.onerror = () => {
        console.error(`XHR Error for ${role}`);
        alert(`Internal network error during upload of ${role}`);
        setUploadingRoles(prev => ({ ...prev, [role]: false }));
        setLocalPreviews(prev => ({ ...prev, [role]: null }));
      };

      xhr.send(formData);

    } catch (err) {
      console.error(`Error in upload flow for ${role}:`, err);
      alert(`Failed to process ${role} image: ` + err.message);
      setUploadingRoles(prev => ({ ...prev, [role]: false }));
      setLocalPreviews(prev => ({ ...prev, [role]: null }));
    }
  };

  const handleGenerate = async () => {
    if (!batch?.has_main || !batch?.has_ref1 || !batch?.has_ref2) {
      alert('Please upload all three images first');
      return;
    }

    setGenerating(true);
    try {
      console.log('🚀 Queuing generation request...');
      const res = await fetch(
        `${apiBaseUrl}/api/batch/${batchId}/generate`,
        { method: 'POST' }
      );

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Queue failed: ${res.status} - ${errorText}`);
      }

      console.log('✅ Batch queued successfully');
      await loadBatchDetail(); // Update status to 'queued' immediately
      setGenerating(false); // Reset local loader since we are now relying on batch.status
    } catch (err) {
      console.error('❌ Error generating:', err);
      alert(`Failed to start generation: ${err.message}`);
      setGenerating(false); // Only stop local loader if queue failed
    }
  };

  const downloadImage = async (role) => {
    try {
      const res = await fetch(
        role === 'generated'
          ? `${apiBaseUrl}/api/batch/${batchId}/generated-image`
          : `${apiBaseUrl}/api/batch/${batchId}/image/${role}`
      );

      if (!res.ok) throw new Error('Download failed');
      const data = await res.json();

      const link = document.createElement('a');
      link.href = `data:image/png;base64,${data.b64}`;
      link.download = `${batch.output_name}-${role}.png`;
      link.click();
    } catch (err) {
      console.error('Error downloading:', err);
      alert('Failed to download image');
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this batch? This action cannot be undone.')) {
      return;
    }

    try {
      const res = await fetch(
        `${apiBaseUrl}/api/batch/${batchId}`,
        { method: 'DELETE' }
      );

      if (!res.ok) throw new Error('Delete failed');
      onBatchUpdated?.();
    } catch (err) {
      console.error('Error deleting batch:', err);
      alert('Failed to delete batch');
    }
  };

  if (loading) {
    return <div className="loading">Loading batch...</div>;
  }

  if (!batch) {
    return <div className="error">Batch not found</div>;
  }

  return (
    <div className="batch-detail">
      <div className="batch-info">
        <h2>{batch.output_name}</h2>
        <div className="batch-meta-grid">
          <div>
            <strong>ID:</strong> {batch.id}
          </div>
          <div>
            <strong>Status:</strong> <span className="status">{batch.status}</span>
            {batch.status === 'queued' && batch.queue_position > 0 && (
              <span className="queue-pos"> (Position: {batch.queue_position})</span>
            )}
          </div>
          <div>
            <strong>Background:</strong> {batch.background}
          </div>
          <div>
            <strong>Pose:</strong> {batch.pose}
          </div>
          <div>
            <strong>Resolution:</strong> {batch.resolution} | <strong>Ratio:</strong> {batch.aspect_ratio}
          </div>
          <div>
            <strong>Created:</strong> {new Date(batch.created_at).toLocaleString()}
          </div>
        </div>
        {batch.error && <div className="error-message">{batch.error}</div>}
      </div>

      <div className="batch-images-section">
        <h3>Images</h3>
        <div className="images-grid">
          <ImageUploadCard
            title="Main Image"
            role="main"
            hasImage={batch.has_main}
            isUploading={uploadingRoles.main}
            uploadProgress={uploadProgress.main}
            localPreview={localPreviews.main}
            onUpload={(file) => handleImageUpload('main', file)}
            onDownload={() => downloadImage('main')}
            apiBaseUrl={apiBaseUrl}
            batchId={batchId}
          />
          <ImageUploadCard
            title="Reference 1"
            role="ref1"
            hasImage={batch.has_ref1}
            isUploading={uploadingRoles.ref1}
            uploadProgress={uploadProgress.ref1}
            localPreview={localPreviews.ref1}
            onUpload={(file) => handleImageUpload('ref1', file)}
            onDownload={() => downloadImage('ref1')}
            apiBaseUrl={apiBaseUrl}
            batchId={batchId}
          />
          <ImageUploadCard
            title="Reference 2"
            role="ref2"
            hasImage={batch.has_ref2}
            isUploading={uploadingRoles.ref2}
            uploadProgress={uploadProgress.ref2}
            localPreview={localPreviews.ref2}
            onUpload={(file) => handleImageUpload('ref2', file)}
            onDownload={() => downloadImage('ref2')}
            apiBaseUrl={apiBaseUrl}
            batchId={batchId}
          />
        </div>
      </div>

      {batch.status === "done" && batch.has_generated && (
        <div className="generated-image-section">
          <h3>Generated Image</h3>
          <GeneratedImagePreview
            batchId={batchId}
            apiBaseUrl={apiBaseUrl}
            onDownload={() => downloadImage('generated')}
          />
        </div>
      )}

      <div className="batch-actions">
        <button
          className="btn btn-primary"
          onClick={handleGenerate}
          disabled={
            generating ||
            batch.status === 'queued' ||
            batch.status === 'generating' ||
            !batch.has_main || !batch.has_ref1 || !batch.has_ref2
          }
        >
          {batch.status === 'queued' ? 'Queued...' :
            batch.status === 'generating' ? 'Generating...' :
              batch.status === 'error' ? 'Retry Generation' :
                generating ? 'Starting...' : 'Generate Image'}
        </button>
        <button
          className="btn btn-danger"
          onClick={handleDelete}
        >
          Delete Batch
        </button>
      </div>
    </div>
  );
};

const ImageUploadCard = ({ title, role, hasImage, isUploading, uploadProgress, localPreview, onUpload, onDownload, apiBaseUrl, batchId }) => {
  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  };

  return (
    <div className={`image-card ${hasImage ? 'has-image' : 'empty'}`}>
      <h4>{title}</h4>

      <div className="upload-area">
        {hasImage || localPreview ? (
          <ImagePreview apiBaseUrl={apiBaseUrl} batchId={batchId} role={role} localPreview={localPreview} />
        ) : (
          <label className="upload-placeholder">
            <div className="upload-icon">📁</div>
            <span>Click to Upload</span>
            <input type="file" accept="image/*" onChange={handleFileChange} hidden />
          </label>
        )}
      </div>

      <div className="image-actions">
        {(hasImage || localPreview) && (
          <>
            <label className="btn btn-sm btn-secondary">
              Change
              <input type="file" accept="image/*" onChange={handleFileChange} hidden />
            </label>
            <button className="btn btn-sm btn-primary" onClick={onDownload} disabled={!hasImage}>
              Download
            </button>
          </>
        )}
        {isUploading && uploadProgress !== undefined && (
          <div className="upload-progress-container">
            <span className="upload-progress-text">{uploadProgress}% Uploaded</span>
            <div className="upload-progress-bar">
              <div 
                className="upload-progress-fill" 
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
          </div>
        )}
        {!isUploading && hasImage && uploadProgress === 100 && (
          <div className="upload-success-indicator">
            <span>✅ Upload Successful</span>
          </div>
        )}
      </div>
    </div>
  );
};

const ImagePreview = ({ apiBaseUrl, batchId, role, localPreview }) => {
  const imageUrl = localPreview || `${apiBaseUrl}/api/batch/${batchId}/image/${role}/raw?t=${new Date().getTime()}`;

  return (
    <>
      <img 
        src={imageUrl} 
        alt={role} 
        className="preview-image" 
        onLoad={() => {
          // If it's a local URL, we might want to revoke it later, but for now just show it
        }}
        onError={(e) => {
          if (!localPreview) {
            e.target.style.display = 'none';
          }
        }}
      />
    </>
  );
};

const GeneratedImagePreview = ({ apiBaseUrl, batchId, onDownload }) => {
  const imageUrl = `${apiBaseUrl}/api/batch/${batchId}/generated-image/raw?t=${new Date().getTime()}`;

  return (
    <div className="generated-preview">
      <img src={imageUrl} alt="Generated" className="preview-image" />
      <button className="btn btn-primary" onClick={onDownload}>
        Download Generated Image
      </button>
    </div>
  );
};

export default BatchDetail;
