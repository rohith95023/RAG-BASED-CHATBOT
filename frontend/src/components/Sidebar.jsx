import React, { useState } from 'react';
import './Sidebar.css';

const Sidebar = ({ currentView = 'upload', onViewChange, isMobileOpen = false, onMobileClose }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [internalMobileOpen, setInternalMobileOpen] = useState(false);

  const handleMobileOpen = isMobileOpen !== undefined ? isMobileOpen : internalMobileOpen;
  const setHandleMobileOpen = isMobileOpen !== undefined ? onMobileClose : setInternalMobileOpen;

  const mainMenuItems = [
    { id: 'upload', icon: '📤', label: 'Upload', badge: null },
    { id: 'chat', icon: '💬', label: 'Chat', badge: null },
    { id: 'documents', icon: '📄', label: 'Documents', badge: null },
    { id: 'history', icon: '🕒', label: 'History', badge: null },
  ];

  const secondaryMenuItems = [
    { id: 'settings', icon: '⚙️', label: 'Settings', badge: null },
    { id: 'help', icon: '❓', label: 'Help', badge: null },
  ];

  const handleItemClick = (itemId) => {
    if (onViewChange) {
      onViewChange(itemId);
    }
    if (onMobileClose) {
      onMobileClose();
    } else {
      setInternalMobileOpen(false);
    }
  };

  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  const toggleMobile = () => {
    if (onMobileClose) {
      onMobileClose();
    } else {
      setInternalMobileOpen(!internalMobileOpen);
    }
  };

  return (
    <>
      {handleMobileOpen && <div className="sidebar-overlay active" onClick={toggleMobile} />}
      <div className={`sidebar ${isCollapsed ? 'collapsed' : ''} ${handleMobileOpen ? 'open' : ''}`}>
        {/* Mobile Close Button */}
        <button
          className="mobile-close-button"
          onClick={toggleMobile}
          style={{
            display: window.innerWidth <= 768 ? 'flex' : 'none',
            position: 'absolute',
            top: '16px',
            right: '16px',
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            background: 'var(--bg-hover)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '18px',
            zIndex: 10
          }}
        >
          ✕
        </button>

        {/* Logo */}
        <div className="sidebar-logo" onClick={() => handleItemClick('upload')}>
          <div className="sidebar-logo-icon">F</div>
          <div>
            <div className="sidebar-logo-text">FLASH MAN</div>
            <div className="sidebar-logo-subtitle">Enterprise Edition</div>
          </div>
        </div>

        {/* Main Navigation */}
        <nav className="sidebar-nav">
          <div className="sidebar-section">
            <div className="sidebar-section-title">Main</div>
            {mainMenuItems.map((item) => (
              <div
                key={item.id}
                className={`sidebar-item ${currentView === item.id ? 'active' : ''}`}
                onClick={() => handleItemClick(item.id)}
                data-tooltip={item.label}
              >
                <span className="sidebar-item-icon">{item.icon}</span>
                <span className="sidebar-item-text">{item.label}</span>
                {item.badge && <span className="sidebar-item-badge">{item.badge}</span>}
              </div>
            ))}
          </div>

          {/* Secondary Navigation */}
          <div className="sidebar-section">
            <div className="sidebar-section-title">System</div>
            {secondaryMenuItems.map((item) => (
              <div
                key={item.id}
                className={`sidebar-item ${currentView === item.id ? 'active' : ''}`}
                onClick={() => handleItemClick(item.id)}
                data-tooltip={item.label}
              >
                <span className="sidebar-item-icon">{item.icon}</span>
                <span className="sidebar-item-text">{item.label}</span>
              </div>
            ))}
          </div>
        </nav>

        {/* Divider */}
        <div className="sidebar-divider"></div>

        {/* User Section */}
        <div className="sidebar-user">
          <div className="sidebar-user-avatar">JD</div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">John Doe</div>
            <div className="sidebar-user-role">Administrator</div>
          </div>
          <div className="sidebar-user-actions">
            <div className="sidebar-user-action" title="Profile">👤</div>
            <div className="sidebar-user-action" title="Logout">🚪</div>
          </div>
        </div>

        {/* Collapse Toggle */}
        <div className="sidebar-collapse" onClick={toggleCollapse} title="Toggle Sidebar">
          ◀
        </div>
      </div>
    </>
  );
};

export default Sidebar;
