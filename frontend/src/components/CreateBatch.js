import React, { useState } from 'react';

const CreateBatch = ({ config, onBatchCreated, apiBaseUrl, token }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  // Default config if not loaded
  const defaultConfig = {
    backgrounds: ['royal grey', 'royal outdoor', 'royal brown', 'royal cream'],
    poses: ['Natural Standing', 'Soft Fashion', 'Editorial', 'Walk'],
    resolutions: ['1K', '2K', '4K'],
    aspect_ratios: ['1:1', '9:16', '16:9', '3:4', '4:3']
  };

  const activeConfig = config || defaultConfig;

  // Defensive checks to prevent "map is not a function"
  const backgrounds = Array.isArray(activeConfig.backgrounds) ? activeConfig.backgrounds : defaultConfig.backgrounds;
  const poses = Array.isArray(activeConfig.poses) ? activeConfig.poses : defaultConfig.poses;
  const resolutions = Array.isArray(activeConfig.resolutions) ? activeConfig.resolutions : defaultConfig.resolutions;
  const aspect_ratios = Array.isArray(activeConfig.aspect_ratios) ? activeConfig.aspect_ratios : defaultConfig.aspect_ratios;

  console.log('CreateBatch Render - Config:', {
    received: config,
    active: activeConfig,
    final: { backgrounds, poses, resolutions, aspect_ratios }
  });

  const [formData, setFormData] = useState({
    output_name: '',
    background: backgrounds[0],
    pose: poses[0],
    resolution: '2K',
    aspect_ratio: aspect_ratios[0],
  });

  // Effect to update defaults only if current selection is invalid (prevents overwriting on parent re-renders)
  React.useEffect(() => {
    if (config) {
      setFormData(prev => ({
        ...prev,
        background: Array.isArray(config.backgrounds) ? (config.backgrounds.includes(prev.background) ? prev.background : config.backgrounds[0]) : prev.background,
        pose: Array.isArray(config.poses) ? (config.poses.includes(prev.pose) ? prev.pose : config.poses[0]) : prev.pose,
        aspect_ratio: Array.isArray(config.aspect_ratios) ? (config.aspect_ratios.includes(prev.aspect_ratio) ? prev.aspect_ratio : config.aspect_ratios[0]) : prev.aspect_ratio,
      }));
    }
  }, [config]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    if (!formData.output_name.trim()) {
      alert('Please enter an output name');
      setIsLoading(false);
      return;
    }

    try {
      const formDataObj = new FormData();
      formDataObj.append('output_name', formData.output_name);
      formDataObj.append('background', formData.background);
      formDataObj.append('pose', formData.pose);
      formDataObj.append('resolution', formData.resolution);
      formDataObj.append('aspect_ratio', formData.aspect_ratio);

      const res = await fetch(`${apiBaseUrl}/api/batch/create`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        body: formDataObj
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || 'Failed to create batch');
        setIsLoading(false);
        return;
      }

      // Success - reset form and notify parent
      alert('Batch created successfully!');
      setFormData({
        output_name: '',
        background: formData.background,
        pose: formData.pose,
        resolution: '2K',
        aspect_ratio: formData.aspect_ratio,
      });
      
      if (onBatchCreated) {
        onBatchCreated();
      }
    } catch (err) {
      console.error('Error creating batch:', err);
      setError('Error creating batch: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="create-batch-form">
      <h2>Create New Batch</h2>
      
      {error && (
        <div className="error-message" style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '2px solid #ef4444',
          color: '#fecaca',
          padding: '14px 16px',
          borderRadius: '12px',
          marginBottom: '24px',
          fontSize: '0.95em'
        }}>
          ❌ {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="output_name">Output Name *</label>
          <input
            type="text"
            id="output_name"
            name="output_name"
            value={formData.output_name}
            onChange={handleChange}
            placeholder="e.g., Wedding Dress Collection"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="background">Background</label>
          <select
            id="background"
            name="background"
            value={formData.background}
            onChange={handleChange}
          >
            {backgrounds.map(bg => (
              <option key={bg} value={bg}>{bg}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="pose">Pose Style</label>
          <select
            id="pose"
            name="pose"
            value={formData.pose}
            onChange={handleChange}
          >
            {poses.map(pose => (
              <option key={pose} value={pose}>{pose}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="resolution">Resolution</label>
          <select
            id="resolution"
            name="resolution"
            value={formData.resolution}
            onChange={handleChange}
          >
            {resolutions.map(res => (
              <option key={res} value={res}>{res}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="aspect_ratio">Aspect Ratio</label>
          <select
            id="aspect_ratio"
            name="aspect_ratio"
            value={formData.aspect_ratio}
            onChange={handleChange}
          >
            {aspect_ratios.map(ratio => (
              <option key={ratio} value={ratio}>{ratio}</option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={isLoading}
        >
          {isLoading ? 'Creating...' : 'Create Batch'}
        </button>
      </form>
    </div>
  );
};

export default CreateBatch;
