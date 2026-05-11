/**
 * Document Manager Component
 * Provides document upload, listing, search, categorization, and management
 */
import React, { useState, useEffect } from 'react';
import { documentsAPI } from '../../services/api';
import DocumentCard from './DocumentCard';
import UploadModal from './UploadModal';
import './DocumentManager.css';

const DocumentManager = ({ onChat }) => {
  const [documents, setDocuments] = useState([]);
  const [filteredDocuments, setFilteredDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedIds, setSelectedIds] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDocuments();
    loadStats();
  }, []);

  useEffect(() => {
    filterDocuments();
  }, [documents, searchQuery, selectedCategory]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const response = await documentsAPI.getDocuments(null, null, 1, 50);
      setDocuments(response.documents || []);
    } catch (error) {
      setError(`Failed to load documents: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await documentsAPI.getDocumentStats();
      setStats(response);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const filterDocuments = () => {
    let filtered = [...documents];

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(doc => doc.category === selectedCategory);
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(doc =>
        doc.filename.toLowerCase().includes(query) ||
        doc.category.toLowerCase().includes(query) ||
        doc.original_filename.toLowerCase().includes(query)
      );
    }

    setFilteredDocuments(filtered);
  };

  const handleUploadSuccess = async (result) => {
    try {
      setError(null);
      
      if (result && result.id) {
        // Reload documents and stats to show the new document
        await loadDocuments();
        await loadStats();
        setShowUploadModal(false);

        // Warn user if RAG processing failed after upload
        if (result.processing_status === 'failed') {
          setError(
            `⚠️ "${result.filename}" was uploaded but RAG processing failed — it cannot be searched in chat. ` +
            `Reason: ${result.processing_error || 'Unknown error'}. ` +
            `Try re-uploading a text-based (non-scanned) PDF.`
          );
        }
      }
    } catch (error) {
      setError(`Failed to refresh document list: ${error.message}`);
    }
  };

  const handleDelete = async (documentId) => {
    if (window.confirm('Are you sure you want to delete this document? This cannot be undone.')) {
      try {
        setError(null);
        await documentsAPI.deleteDocument(documentId);

        // Reload documents and stats
        await loadDocuments();
        await loadStats();
      } catch (error) {
        setError(`Delete failed: ${error.message}`);
      }
    }
  };

  const handleDownload = async (documentId, filename) => {
    try {
      setError(null);
      const doc = await documentsAPI.getDocument(documentId);

      // Create download link
      const link = window.document.createElement('a');
      link.href = `/api/documents/${documentId}/download`;
      link.download = filename;
      link.click();
    } catch (error) {
      setError(`Download failed: ${error.message}`);
    }
  };

  const handleRefresh = () => {
    loadDocuments();
    loadStats();
    setError(null);
  };

  const clearSearch = () => {
    setSearchQuery('');
    setSelectedCategory('all');
  };

  const handleCategoryChange = (category) => {
    setSelectedCategory(category);
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const handleToggleSelect = (id) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (selectedIds.length === filteredDocuments.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredDocuments.map(doc => doc.id));
    }
  };

  const handleBulkChat = () => {
    if (selectedIds.length > 0) {
      onChat(selectedIds);
    }
  };

  if (error) {
    return (
      <div className="document-manager error-state">
        <div className="error-message">
          <h3>⚠️ Error</h3>
          <p>{error}</p>
          <button onClick={handleRefresh} className="retry-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (loading && documents.length === 0) {
    return (
      <div className="document-manager">
        <DocumentHeader
          onUpload={() => setShowUploadModal(true)}
          onRefresh={handleRefresh}
        />
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading documents...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="document-manager">
      <DocumentHeader
        onUpload={() => setShowUploadModal(true)}
        onRefresh={handleRefresh}
        stats={stats}
      />

      {selectedIds.length > 0 && (
        <div className="bulk-actions-bar">
          <div className="selection-info">
            <span>{selectedIds.length} document{selectedIds.length !== 1 ? 's' : ''} selected</span>
          </div>
          <div className="bulk-actions">
            <button onClick={handleBulkChat} className="bulk-chat-button">
              💬 Chat with Selected
            </button>
            <button onClick={() => setSelectedIds([])} className="bulk-cancel-button">
              Cancel
            </button>
          </div>
        </div>
      )}

      <DocumentFilters
        searchQuery={searchQuery}
        selectedCategory={selectedCategory}
        onSearchChange={setSearchQuery}
        onCategoryChange={handleCategoryChange}
        onClearSearch={clearSearch}
        categories={stats?.categories || {}}
      />

      <div className="selection-header">
        <label className="select-all-label">
          <input 
            type="checkbox" 
            checked={selectedIds.length === filteredDocuments.length && filteredDocuments.length > 0}
            onChange={handleSelectAll}
          />
          <span>Select All Documents</span>
        </label>
      </div>

      <DocumentGrid
        documents={filteredDocuments}
        loading={loading}
        onDelete={handleDelete}
        onDownload={handleDownload}
        onChat={onChat}
        formatFileSize={formatFileSize}
        selectedIds={selectedIds}
        onToggleSelect={handleToggleSelect}
      />

      {showUploadModal && (
        <UploadModal
          onClose={() => setShowUploadModal(false)}
          onUpload={handleUploadSuccess}
        />
      )}
    </div>
  );
};

// Header Component
const DocumentHeader = ({ onUpload, onRefresh, stats }) => {
  return (
    <div className="document-header">
      <div className="header-left">
        <h1>📚 Document Manager</h1>
        {stats && (
          <span className="document-stats">
            {stats.total_documents} document{stats.total_documents !== 1 ? 's' : ''} •
            {formatFileSize(stats.total_size_bytes)}
          </span>
        )}
      </div>

      <div className="header-actions">
        <button onClick={onRefresh} className="refresh-button" title="Refresh">
          🔄
        </button>
        <button onClick={onUpload} className="upload-button" title="Upload Document">
          <span>+</span> Upload Document
        </button>
      </div>
    </div>
  );
};

// Filters Component
const DocumentFilters = ({ searchQuery, selectedCategory, onSearchChange, onCategoryChange, onClearSearch, categories }) => {
  const categoryOptions = [
    { value: 'all', label: 'All Categories' },
    { value: 'general', label: 'General' },
    { value: 'technical', label: 'Technical' },
    { value: 'legal', label: 'Legal' },
    { value: 'financial', label: 'Financial' },
    { value: 'medical', label: 'Medical' },
    { value: 'other', label: 'Other' }
  ];

  return (
    <div className="document-filters">
      <div className="search-bar">
        <input
          type="text"
          placeholder="Search documents..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="search-input"
        />
        {searchQuery && (
          <button onClick={onClearSearch} className="clear-search">
            ×
          </button>
        )}
      </div>

      <div className="category-filter">
        <select
          value={selectedCategory}
          onChange={(e) => onCategoryChange(e.target.value)}
          className="category-select"
        >
          {categoryOptions.map(cat => (
            <option key={cat.value} value={cat.value}>
              {cat.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

// Document Grid Component
const DocumentGrid = ({ documents, loading, onDelete, onDownload, onChat, formatFileSize, selectedIds, onToggleSelect }) => {
  if (loading) {
    return (
      <div className="document-grid">
        {[1, 2, 3, 4, 5, 6].map(i => (
          <div key={i} className="document-skeleton">
            <div className="skeleton-header"></div>
            <div className="skeleton-body"></div>
            <div className="skeleton-footer"></div>
          </div>
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="document-grid">
        <div className="empty-state">
          <div className="empty-icon">📄</div>
          <h3>No documents found</h3>
          <p>Upload your first PDF to get started with document analysis!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="document-grid">
      {documents.map(doc => (
        <DocumentCard
          key={doc.id}
          document={doc}
          onDelete={onDelete}
          onDownload={onDownload}
          onChat={onChat}
          formatFileSize={formatFileSize}
          isSelected={selectedIds.includes(doc.id)}
          onSelect={() => onToggleSelect(doc.id)}
        />
      ))}
    </div>
  );
};

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

export default DocumentManager;
