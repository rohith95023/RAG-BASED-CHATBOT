import React, { useState, useRef } from 'react';
import { documentsAPI } from '../services/api';
import './Upload.css';

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

const Upload = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [category, setCategory] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (isSupportedDocument(selectedFile)) {
      setFile(selectedFile);
      setError('');
      setSuccessMsg('');
    } else {
      setFile(null);
      setError('Please select a supported document file.');
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (isSupportedDocument(droppedFile)) {
      setFile(droppedFile);
      setError('');
      setSuccessMsg('');
    } else {
      setError('Please drop a supported document file.');
    }
  };

  const handleRemoveFile = () => {
    setFile(null);
    setError('');
    setSuccessMsg('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const [processingStage, setProcessingStage] = useState('');

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first.');
      return;
    }

    setIsUploading(true);
    setError('');
    setSuccessMsg('');
    setUploadProgress(0);
    setProcessingStage('Preparing upload...');

    try {
      const finalCategory = category.trim() === '' ? 'general' : category;
      
      // Stage 1: Uploading
      setProcessingStage('Uploading document to server...');
      const result = await documentsAPI.uploadDocument(file, finalCategory, (progress) => {
        setUploadProgress(progress);
        if (progress === 100) {
          setProcessingStage('Extracting text from document...');
        }
      });

      // Stage 2: Processing (Backend is already doing this, but we show status)
      setUploadProgress(100);
      
      const stages = [
        { msg: 'Analyzing document structure...', delay: 2000 },
        { msg: 'Chunking text for RAG...', delay: 4000 },
        { msg: 'Generating semantic embeddings...', delay: 6000 },
        { msg: 'Indexing vectors in MongoDB Atlas...', delay: 4000 },
        { msg: 'Finalizing document record...', delay: 2000 }
      ];

      let currentDelay = 0;
      for (const stage of stages) {
        setTimeout(() => setProcessingStage(stage.msg), currentDelay);
        currentDelay += stage.delay;
      }

      setTimeout(() => {
        setSuccessMsg('File uploaded and processed successfully!');
        setProcessingStage('Ready!');
        onUploadSuccess(result);
      }, currentDelay);

    } catch (err) {
      setError(err.message || 'Failed to upload file. Please try again.');
      setUploadProgress(0);
      setProcessingStage('');
      setIsUploading(false);
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
    <div className="upload-container">
      {/* Hero Section */}
      <div className="upload-hero">
        <h1 className="upload-hero-title">
          Upload Documents to Start Chatting with FLASH MAN
        </h1>
        <p className="upload-hero-subtitle">
          FLASH MAN is ready to analyze your documents. Upload research papers,
          financial reports, or class notes to begin extracting insights immediately.
        </p>
      </div>

      {/* Upload Zone */}
      <div className="upload-zone-container">
        <div
          className={`upload-dropzone ${isDragOver ? 'drag-over' : ''}`}
          onClick={() => !isUploading && fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="upload-dropzone-content">
            <div className="upload-icon">📄</div>
            <h3>
              {file ? file.name : 'Drag and drop your document here or click to browse'}
            </h3>
            <p>
              {file
                ? `File size: ${formatFileSize(file.size)}`
                : 'Supports PDF, Word, Excel, PowerPoint, text, CSV, JSON, HTML, RTF, and OpenDocument files'}
            </p>
            <div className="upload-dropzone-features">
              <div className="upload-feature">
                <span>🔒</span> Secure Upload
              </div>
              <div className="upload-feature">
                <span>⚡</span> Fast Processing
              </div>
              <div className="upload-feature">
                <span>🤖</span> AI-Powered Analysis
              </div>
            </div>
          </div>
          <input
            type="file"
            accept={ACCEPTED_DOCUMENT_TYPES}
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={handleFileChange}
            disabled={isUploading}
          />
        </div>

        {/* File Preview */}
        {file && (
          <div className="upload-file-preview selected">
            <div className="upload-file-icon">📄</div>
            <div className="upload-file-info">
              <div className="upload-file-name">{file.name}</div>
              <div className="upload-file-size">{formatFileSize(file.size)}</div>
            </div>
            <button
              className="upload-file-remove"
              onClick={handleRemoveFile}
              disabled={isUploading}
              title="Remove file"
            >
              ✕
            </button>
          </div>
        )}

        {/* Progress Bar */}
        {isUploading && (
          <div className="upload-progress active">
            <div
              className="upload-progress-bar"
              style={{ width: `${uploadProgress}%` }}
            />
            <div className="upload-progress-text">
              <span>Uploading...</span>
              <span>{uploadProgress}%</span>
            </div>
          </div>
        )}

        {/* Form */}
        <div className="upload-form">
          <div className="upload-form-group">
            <label className="upload-form-label">Category (Optional)</label>
            <input
              type="text"
              className="upload-input"
              placeholder="e.g., Research, Finance, Legal"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={isUploading}
            />
          </div>

          {/* Status Messages */}
          {error && (
            <div className="upload-status error">
              <span className="upload-status-icon">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="upload-status success">
              <span className="upload-status-icon">✅</span>
              <span>{successMsg}</span>
            </div>
          )}

          {/* Actions */}
          <div className="upload-actions">
            <button
              className="upload-button"
              onClick={handleUpload}
              disabled={!file || isUploading}
            >
              {isUploading ? (
                <>
                  <div className="spinner-ring" style={{ width: 20, height: 20, borderWidth: 2 }} />
                  {processingStage || `Uploading (${uploadProgress}%)...`}
                </>
              ) : (
                <>
                  <span>📤</span>
                  Upload Document
                </>
              )}
            </button>
            <button
              className="upload-button upload-button-secondary"
              onClick={handleRemoveFile}
              disabled={!file || isUploading}
            >
              <span>🔄</span>
              Clear
            </button>
          </div>
        </div>
      </div>


    </div>
  );
};

export default Upload;
