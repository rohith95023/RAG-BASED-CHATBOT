/**
 * Upload Modal Component
 * Provides drag-and-drop PDF upload with progress tracking
 */
import React, { useState, useRef, useEffect } from 'react';
import { documentsAPI } from '../../services/api';
import './UploadModal.css';

const SUPPORTED_DOCUMENT_EXTENSIONS = [
  '.pdf', '.docx', '.doc', '.xlsx', '.xlsm', '.xls', '.pptx',
  '.txt', '.md', '.markdown', '.csv', '.tsv', '.json', '.xml',
  '.html', '.htm', '.rtf', '.odt', '.ods', '.odp',
];

const ACCEPTED_DOCUMENT_TYPES = SUPPORTED_DOCUMENT_EXTENSIONS.join(',');

const isSupportedDocument = (selectedFile) => {
  if (!selectedFile?.name) return false;
  const lowerName = selectedFile.name.toLowerCase();
  return SUPPORTED_DOCUMENT_EXTENSIONS.some((extension) => lowerName.endsWith(extension));
};

const UploadModal = ({ onClose, onUpload }) => {
  const [file, setFile] = useState(null);
  const [category, setCategory] = useState('general');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    // Focus trap
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  const handleFileChange = (selectedFile) => {
    setFile(selectedFile);
    setError('');
    setUploadProgress(0);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);

    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles.length > 0) {
      const selectedFile = droppedFiles[0];
      if (isSupportedDocument(selectedFile)) {
        handleFileChange(selectedFile);
      } else {
        setError('Unsupported file type');
      }
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setUploading(true);
    setError('');
    setUploadProgress(0);

    try {
      const result = await documentsAPI.uploadDocument(file, category, (progress) => {
        setUploadProgress(progress);
      });

      if (result.success !== false) {
        setUploadProgress(100);
        onUpload(result);
        handleReset();
      } else {
        throw new Error(result.error || 'Upload failed');
      }

    } catch (error) {
      setError(`Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setCategory('general');
    setError('');
    setUploadProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleBackdropClick = (e) => {
    if (e.target.className === 'upload-modal-backdrop') {
      onClose();
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="upload-modal-backdrop" onClick={handleBackdropClick}>
      <div className="upload-modal" onClick={(e) => e.stopPropagation()}>
        <div className="upload-header">
          <h2>Upload Document</h2>
          <button onClick={onClose} className="close-button">
            ×
          </button>
        </div>

        <div
          className={`upload-area ${dragOver ? 'drag-over' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          {file ? (
            <div className="file-info">
              <div className="file-icon">📄</div>
              <div className="file-details">
                <div className="file-name">{file.name}</div>
                <div className="file-size">{formatFileSize(file.size)}</div>
              </div>
              {!uploading && (
                <button onClick={handleReset} className="change-file-button">
                  Change File
                </button>
              )}
            </div>
          ) : (
            <div className="upload-prompt">
              <div className="upload-icon">📤</div>
              <div className="upload-text">
                <h3>Drag & drop document here</h3>
                <p>or click to browse files</p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_DOCUMENT_TYPES}
                onChange={(e) => handleFileChange(e.target.files[0])}
                className="file-input"
              />
            </div>
          )}

          <input
            type="file"
            ref={fileInputRef}
            accept={ACCEPTED_DOCUMENT_TYPES}
            onChange={(e) => handleFileChange(e.target.files[0])}
            className="hidden-file-input"
          />
        </div>

        <div className="upload-footer">
          <div className="category-select">
            <label htmlFor="category">Category:</label>
            <select
              id="category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={uploading}
              className="category-dropdown"
            >
              <option value="general">General</option>
              <option value="technical">Technical</option>
              <option value="legal">Legal</option>
              <option value="financial">Financial</option>
              <option value="medical">Medical</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div className="upload-actions">
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className={`upload-button ${uploading ? 'uploading' : ''}`}
            >
              {uploading ? 'Uploading...' : 'Upload Document'}
            </button>
            <button
              onClick={onClose}
              disabled={uploading}
              className="cancel-button"
            >
              Cancel
            </button>
          </div>
        </div>

        {error && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            {error}
          </div>
        )}

        {uploading && (
          <div className="upload-progress">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
            <div className="progress-text">{uploadProgress}%</div>
          </div>
        )}
      </div>
    </div>
  );
};

export default UploadModal;
