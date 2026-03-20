import React, { useState, useEffect } from 'react';

const BatchDetail = ({ batchId, apiBaseUrl, onBatchUpdated }) => {
  const [batch, setBatch] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
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

  const handleImageUpload = async (role, file) => {
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(
        `${apiBaseUrl}/api/batch/${batchId}/upload/${role}`,
        { method: 'POST', body: formData }
      );

      if (!res.ok) throw new Error('Upload failed');
      await loadBatchDetail();
    } catch (err) {
      console.error('Error uploading image:', err);
      alert('Failed to upload image');
    } finally {
      setUploading(false);
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
            isUploading={uploading}
            onUpload={(file) => handleImageUpload('main', file)}
            onDownload={() => downloadImage('main')}
            apiBaseUrl={apiBaseUrl}
            batchId={batchId}
          />
          <ImageUploadCard
            title="Reference 1"
            role="ref1"
            hasImage={batch.has_ref1}
            isUploading={uploading}
            onUpload={(file) => handleImageUpload('ref1', file)}
            onDownload={() => downloadImage('ref1')}
            apiBaseUrl={apiBaseUrl}
            batchId={batchId}
          />
          <ImageUploadCard
            title="Reference 2"
            role="ref2"
            hasImage={batch.has_ref2}
            isUploading={uploading}
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

const ImageUploadCard = ({ title, role, hasImage, isUploading, onUpload, onDownload, apiBaseUrl, batchId }) => {
  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  };

  return (
    <div className={`image-card ${hasImage ? 'has-image' : 'empty'}`}>
      <h4>{title}</h4>

      <div className="upload-area">
        {hasImage ? (
          <ImagePreview apiBaseUrl={apiBaseUrl} batchId={batchId} role={role} />
        ) : (
          <label className="upload-placeholder">
            <div className="upload-icon">📁</div>
            <span>Click to Upload</span>
            <input type="file" accept="image/*" onChange={handleFileChange} hidden />
          </label>
        )}
      </div>

      <div className="image-actions">
        {hasImage && (
          <>
            <label className="btn btn-sm btn-secondary">
              Change
              <input type="file" accept="image/*" onChange={handleFileChange} hidden />
            </label>
            <button className="btn btn-sm btn-primary" onClick={onDownload}>
              Download
            </button>
          </>
        )}
        {!hasImage && isUploading && <div className="uploading-spinner">Uploading...</div>}
      </div>
    </div>
  );
};

const ImagePreview = ({ apiBaseUrl, batchId, role }) => {
  const [imageSrc, setImageSrc] = useState(null);

  useEffect(() => {
    const loadImage = async () => {
      try {
        const res = await fetch(`${apiBaseUrl}/api/batch/${batchId}/image/${role}`);
        const data = await res.json();
        setImageSrc(`data:image/png;base64,${data.b64}`);
      } catch (err) {
        console.error('Error loading image:', err);
      }
    };
    loadImage();
  }, [apiBaseUrl, batchId, role]);

  return (
    <>
      {imageSrc && <img src={imageSrc} alt={role} className="preview-image" />}
    </>
  );
};

const GeneratedImagePreview = ({ apiBaseUrl, batchId, onDownload }) => {
  const [imageSrc, setImageSrc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadImage = async () => {
      setLoading(true);
      setError(null);
      setImageSrc(null);

      try {
        console.log('📥 Loading generated image for batch:', batchId);
        const res = await fetch(`${apiBaseUrl}/api/batch/${batchId}/generated-image`);

        if (!res.ok) {
          throw new Error(`Failed to load: ${res.status}`);
        }

        const data = await res.json();

        if (!data.b64) {
          throw new Error('No image data in response');
        }

        // Verify base64 is valid
        if (data.b64.length < 100) {
          throw new Error(`Invalid base64 length: ${data.b64.length}`);
        }

        const src = `data:image/png;base64,${data.b64}`;
        console.log('✅ Generated image loaded successfully, size:', data.b64.length);
        setImageSrc(src);
      } catch (err) {
        console.error('❌ Error loading generated image:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadImage();
  }, [apiBaseUrl, batchId]);

  if (loading) {
    return <div className="loading">⏳ Loading generated image...</div>;
  }

  if (error) {
    return <div className="error">❌ {error}</div>;
  }

  if (!imageSrc) {
    return <div className="error">❌ No generated image available</div>;
  }

  return (
    <div className="generated-preview">
      <img src={imageSrc} alt="Generated" className="preview-image" />
      <button className="btn btn-primary" onClick={onDownload}>
        Download Generated Image
      </button>
    </div>
  );
};

export default BatchDetail;
