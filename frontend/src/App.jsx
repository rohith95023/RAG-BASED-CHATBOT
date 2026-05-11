import React, { useState, Suspense, lazy } from 'react';
import Sidebar from './components/Sidebar';
import HistoryView from './components/Pages/HistoryView';
import SettingsView from './components/Pages/SettingsView';
import HelpView from './components/Pages/HelpView';
import './App.css';

// Lazy load components for better performance
const Upload = lazy(() => import('./components/Upload'));
const Chat = lazy(() => import('./components/Chat'));
const DocumentManager = lazy(() => import('./components/Documents/DocumentManager'));

function App() {
  const [view, setView] = useState('upload');
  const [error, setError] = useState(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState([]);

  const handleViewChange = (newView) => {
    setView(newView);
  };

  const handleUploadSuccess = (document) => {
    if (document && document.id) {
      setSelectedDocumentIds([document.id]);
    }
    handleViewChange('chat');
  };

  const renderView = () => {
    switch (view) {
      case 'upload':
        return <Upload key="upload" onUploadSuccess={handleUploadSuccess} />;
      case 'chat':
        return <Chat key="chat" selectedDocumentIds={selectedDocumentIds} />;
      case 'documents':
        return (
          <DocumentManager
            key="documents"
            onChat={(ids) => {
              setSelectedDocumentIds(Array.isArray(ids) ? ids : [ids]);
              handleViewChange('chat');
            }}
          />
        );
      case 'history':
        return <HistoryView key="history" onNavigate={handleViewChange} />;
      case 'settings':
        return <SettingsView key="settings" />;
      case 'help':
        return <HelpView key="help" onNavigate={handleViewChange} />;
      default:
        return <Upload key="upload" onUploadSuccess={handleUploadSuccess} />;
    }
  };

  if (error) {
    return (
      <div className="app-error">
        <div className="app-error-icon">⚠️</div>
        <h1 className="app-error-title">Something went wrong</h1>
        <p className="app-error-message">{error.message || 'An unexpected error occurred. Please try again.'}</p>
        <button className="app-error-button" onClick={() => setError(null)}>
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="app-container">
      <Sidebar
        currentView={view}
        onViewChange={handleViewChange}
        isMobileOpen={isMobileMenuOpen}
        onMobileClose={() => setIsMobileMenuOpen(false)}
      />
      <main className="main-content">
        <button
          className="mobile-menu-toggle"
          onClick={() => setIsMobileMenuOpen(true)}
          style={{
            display: window.innerWidth <= 768 ? 'flex' : 'none',
            position: 'fixed',
            top: '16px',
            left: '16px',
            zIndex: 1000,
            width: '40px',
            height: '40px',
            borderRadius: '8px',
            background: 'var(--primary)',
            color: 'white',
            border: 'none',
            cursor: 'pointer',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px',
            boxShadow: 'var(--shadow-md)',
          }}
        >
          ☰
        </button>

        <Suspense
          fallback={
            <div className="app-loading">
              <div className="app-loading-logo">FLASH MAN</div>
              <div className="app-loading-spinner"></div>
            </div>
          }
        >
          <div className="page-transition-wrapper">
            {renderView()}
          </div>
        </Suspense>
      </main>
    </div>
  );
}

export default App;
