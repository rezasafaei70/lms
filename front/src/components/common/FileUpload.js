import React, { useRef, useState } from 'react';
import { useS3Upload } from '../../hooks/useS3Upload';
import './FileUpload.css';

/**
 * S3 File Upload Component
 * Supports both simple and multipart uploads
 */
const FileUpload = ({
  onUploadComplete,
  onUploadError,
  accept = '*',
  maxSize = 100 * 1024 * 1024, // 100MB default
  folder = 'uploads',
  targetModel = '',
  targetField = '',
  targetObjectId = '',
  preview = true,
  previewUrl = null,
  label = 'انتخاب فایل',
  hint = '',
  className = '',
  disabled = false,
}) => {
  const fileInputRef = useRef(null);
  const [previewSrc, setPreviewSrc] = useState(previewUrl);
  const [fileName, setFileName] = useState('');

  const {
    upload,
    abort,
    reset,
    uploading,
    progress,
    error,
    uploadedFile,
  } = useS3Upload({
    targetFolder: folder,
    targetModel,
    targetField,
    targetObjectId,
    onComplete: (result) => {
      if (onUploadComplete) {
        onUploadComplete(result);
      }
    },
    onError: (err) => {
      if (onUploadError) {
        onUploadError(err);
      }
    },
  });

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file size
    if (file.size > maxSize) {
      const maxSizeMB = Math.round(maxSize / (1024 * 1024));
      alert(`حداکثر حجم فایل ${maxSizeMB} مگابایت است`);
      return;
    }

    setFileName(file.name);

    // Show preview for images
    if (preview && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewSrc(reader.result);
      };
      reader.readAsDataURL(file);
    }

    // Start upload
    await upload(file);
  };

  const handleClick = () => {
    if (!uploading && !disabled) {
      fileInputRef.current?.click();
    }
  };

  const handleAbort = (e) => {
    e.stopPropagation();
    abort();
  };

  const handleRemove = (e) => {
    e.stopPropagation();
    reset();
    setPreviewSrc(null);
    setFileName('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const isImage = accept.includes('image') || previewSrc?.startsWith('data:image') || previewSrc?.includes('/branches/') || previewSrc?.includes('/profiles/');

  return (
    <div className={`file-upload ${className} ${disabled ? 'disabled' : ''}`}>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileSelect}
        className="file-input-hidden"
        disabled={disabled || uploading}
      />

      <div className="file-upload-area" onClick={handleClick}>
        {/* Preview Area */}
        {preview && (previewSrc || isImage) && (
          <div className="file-preview">
            {previewSrc ? (
              <img src={previewSrc} alt="پیش‌نمایش" />
            ) : (
              <div className="file-preview-placeholder">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
              </div>
            )}
          </div>
        )}

        {/* Upload Progress */}
        {uploading && (
          <div className="upload-progress">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="progress-info">
              <span>{progress}%</span>
              <button 
                type="button" 
                className="abort-btn"
                onClick={handleAbort}
              >
                لغو
              </button>
            </div>
          </div>
        )}

        {/* Upload Area Content */}
        {!uploading && (
          <div className="upload-content">
            {!previewSrc && !uploadedFile && (
              <>
                <div className="upload-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <span className="upload-label">{label}</span>
                {hint && <span className="upload-hint">{hint}</span>}
              </>
            )}

            {(previewSrc || uploadedFile) && (
              <div className="upload-success">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
                <span>{fileName || 'آپلود شد'}</span>
                <button 
                  type="button" 
                  className="remove-btn"
                  onClick={handleRemove}
                >
                  حذف
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="upload-error">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </div>
      )}
    </div>
  );
};

export default FileUpload;

