/**
 * Document Card Component
 * Displays individual document with actions and metadata
 */
import React, { useState } from 'react';
import './DocumentCard.css';

const DocumentCard = ({ document, onDelete, onDownload, onChat, formatFileSize, isSelected, onSelect }) => {
  const [showActions, setShowActions] = useState(false);

  const getCategoryColor = (category) => {
    const colors = {
      'general': '#3498db',
      'technical': '#e74c3c',
      'legal': '#9b59b6',
      'financial': '#27ae60',
      'medical': '#f39c12',
      'other': '#95a5a6'
    };
    return colors[category] || colors['other'];
  };

  const getCategoryLabel = (category) => {
    const labels = {
      'general': 'General',
      'technical': 'Technical',
      'legal': 'Legal',
      'financial': 'Financial',
      'medical': 'Medical',
      'other': 'Other'
    };
    return labels[category] || 'Other';
  };

  const handleMouseEnter = () => {
    setShowActions(true);
  };

  const handleMouseLeave = () => {
    setShowActions(false);
  };

  return (
    <div
      className={`document-card ${isSelected ? 'selected' : ''}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={onSelect}
    >
      <div className="document-selection">
        <input 
          type="checkbox" 
          checked={isSelected} 
          onChange={(e) => {
            e.stopPropagation();
            onSelect();
          }}
          onClick={(e) => e.stopPropagation()}
        />
      </div>
      <div className="document-icon">
        📄
      </div>

      <div className="document-content">
        <div className="document-filename" title={document.filename}>
          {document.filename}
        </div>

        <div className="document-meta">
          <span
            className="category-badge"
            style={{ backgroundColor: getCategoryColor(document.category) }}
          >
            {getCategoryLabel(document.category)}
          </span>
          <span className="upload-date">
            {new Date(document.uploaded_at).toLocaleDateString()}
          </span>
        </div>

        <div className="document-stats">
          <span className="size-info">
            {formatFileSize(document.file_size)}
          </span>
          {document.chunk_count > 0 && (
            <span className="chunks-info">
              {document.chunk_count} chunks
            </span>
          )}
        </div>
      </div>

      <div className={`document-actions ${showActions ? 'visible' : ''}`}>
        <button
          onClick={() => onChat(document.id)}
          className="action-button chat"
          title="Chat with document"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        </button>

        <button
          onClick={() => onDownload(document.id, document.filename)}
          className="action-button download"
          title="Download document"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M21 15v4a2 2 0 002 2H3a2 2 0 00-2-2v-4M17 8h2a2 2 0 002 2h2.5a.5.5 0 01.5.5V9a.5.5 0 01-.5-.5H15a5 5 0 00-5-5V6a.5.5 0 01-.5-.5z" stroke="currentColor" strokeWidth="2"/>
            <path d="M12 11L15 14L9 14" stroke="currentColor" strokeWidth="2"/>
          </svg>
        </button>

        <button
          onClick={() => onDelete(document.id)}
          className="action-button delete"
          title="Delete document"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 6h18M19 6v14a2 2 0 01-2 2H5a2 2 0 01-2-2V6m3 0V4a2 2 0 00-2-2H6a2 2 0 00-2 2v2M10 10l4-4m0 0l-4 4m4-4H6" stroke="currentColor" strokeWidth="2"/>
          </svg>
        </button>
      </div>
    </div>
  );
};

export default DocumentCard;
