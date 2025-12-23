import React, { useState, useRef } from 'react';

export default function MeasulorMobile() {
  const [status, setStatus] = useState('idle'); // idle | uploading | processing | done | error
  const [result, setResult] = useState(null);
  const [processingTime, setProcessingTime] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setStatus('uploading');
    setResult(null);
    setProcessingTime(null);

    const startTime = Date.now();
    const formData = new FormData();
    formData.append('image', file);

    try {
      setStatus('processing');
      
      const res = await fetch('/api/measure', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error('Measurement failed');
      }

      const data = await res.json();
      const endTime = Date.now();
      const timeTaken = ((endTime - startTime) / 1000).toFixed(1);
      
      setResult(data.measurements);
      setProcessingTime(timeTaken);
      setStatus('done');
    } catch (err) {
      console.error(err);
      setStatus('error');
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleRetake = () => {
    setStatus('idle');
    setResult(null);
    setProcessingTime(null);
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '20px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      color: 'white'
    }}>
      {/* Header */}
      <div style={{
        textAlign: 'center',
        marginBottom: '30px'
      }}>
        <h1 style={{ fontSize: '2em', marginBottom: '10px' }}>👕 Measulor</h1>
        <p style={{ fontSize: '1.1em', opacity: 0.9 }}>AI Body Measurement System</p>
      </div>

      {/* Upload Section */}
      <div style={{
        background: 'rgba(255,255,255,0.1)',
        backdropFilter: 'blur(10px)',
        borderRadius: '15px',
        padding: '25px',
        marginBottom: '20px'
      }}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileSelect}
          disabled={status === 'processing' || status === 'uploading'}
          style={{ display: 'none' }}
          id="photo-input"
        />
        
        <label
          htmlFor="photo-input"
          style={{
            display: 'block',
            width: '100%',
            padding: '20px',
            background: status === 'processing' || status === 'uploading' ? '#999' : '#48bb78',
            color: 'white',
            border: 'none',
            borderRadius: '12px',
            fontSize: '1.1em',
            fontWeight: 'bold',
            textAlign: 'center',
            cursor: status === 'processing' || status === 'uploading' ? 'not-allowed' : 'pointer',
            transition: 'all 0.3s'
          }}
        >
          {status === 'idle' && '📸 Take Photo / Upload'}
          {status === 'uploading' && '⏳ Uploading...'}
          {status === 'processing' && '🔄 Processing...'}
          {status === 'done' && '✅ Measurements Ready!'}
          {status === 'error' && '❌ Try Again'}
        </label>
      </div>

      {/* Status Message */}
      {status === 'processing' && (
        <div style={{
          background: 'rgba(255,255,255,0.15)',
          backdropFilter: 'blur(10px)',
          borderRadius: '12px',
          padding: '20px',
          marginBottom: '20px',
          textAlign: 'center'
        }}>
          <div style={{
            fontSize: '2em',
            marginBottom: '10px',
            animation: 'spin 2s linear infinite'
          }}>
            ⚙️
          </div>
          <p style={{ fontSize: '1.1em', marginBottom: '5px' }}>
            Processing your measurements...
          </p>
          <p style={{ fontSize: '0.9em', opacity: 0.8 }}>
            This usually takes 5-10 seconds
          </p>
        </div>
      )}

      {/* Results */}
      {status === 'done' && result && (
        <div>
          {/* Processing Time */}
          <div style={{
            background: 'rgba(72, 187, 120, 0.2)',
            border: '2px solid #48bb78',
            borderRadius: '12px',
            padding: '15px',
            marginBottom: '20px',
            textAlign: 'center'
          }}>
            <p style={{ fontSize: '1em', marginBottom: '5px' }}>
              ⚡ Results ready in <strong>{processingTime}s</strong>
            </p>
          </div>

          {/* Measurements Table */}
          <div style={{
            background: 'rgba(255,255,255,0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: '15px',
            padding: '25px',
            marginBottom: '20px'
          }}>
            <h2 style={{
              fontSize: '1.5em',
              marginBottom: '20px',
              borderBottom: '2px solid rgba(255,255,255,0.2)',
              paddingBottom: '10px'
            }}>
              📐 Your Measurements
            </h2>
            
            {Object.entries(result).map(([key, value]) => (
              <div key={key} style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '12px 0',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                fontSize: '1em'
              }}>
                <span style={{ textTransform: 'capitalize', opacity: 0.9 }}>
                  {key.replace(/_/g, ' ')}
                </span>
                <span style={{ fontWeight: 'bold', fontSize: '1.1em' }}>
                  {typeof value === 'number' ? value.toFixed(1) : value} cm
                </span>
              </div>
            ))}
          </div>

          {/* Retake Button */}
          <button
            onClick={handleRetake}
            style={{
              width: '100%',
              padding: '18px',
              background: '#4299e1',
              color: 'white',
              border: 'none',
              borderRadius: '12px',
              fontSize: '1.1em',
              fontWeight: 'bold',
              cursor: 'pointer',
              transition: 'all 0.3s'
            }}
          >
            📸 Take Another Photo
          </button>
        </div>
      )}

      {/* Error State */}
      {status === 'error' && (
        <div style={{
          background: 'rgba(245, 87, 108, 0.2)',
          border: '2px solid #f5576c',
          borderRadius: '12px',
          padding: '20px',
          marginBottom: '20px',
          textAlign: 'center'
        }}>
          <p style={{ fontSize: '1.1em', marginBottom: '10px' }}>
            ❌ Unable to process the image
          </p>
          <p style={{ fontSize: '0.9em', opacity: 0.9 }}>
            Please try again with better lighting and a full-body photo
          </p>
        </div>
      )}

      {/* Instructions */}
      <div style={{
        background: 'rgba(255,255,255,0.1)',
        backdropFilter: 'blur(10px)',
        borderRadius: '15px',
        padding: '25px',
        marginTop: '20px'
      }}>
        <h3 style={{ fontSize: '1.3em', marginBottom: '15px' }}>💡 Instructions</h3>
        <ul style={{
          fontSize: '0.95em',
          lineHeight: '1.8',
          paddingLeft: '20px',
          opacity: 0.95
        }}>
          <li>Stand 6-8 feet away from the camera</li>
          <li>Ensure your full body is visible</li>
          <li>Stand in a T-pose for best results</li>
          <li>Make sure the lighting is good</li>
          <li>Wear fitted clothing</li>
        </ul>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

