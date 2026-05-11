import React, { useEffect, useMemo, useState } from 'react';
import { chatAPI } from '../../services/api';
import './Pages.css';

const formatDateTime = (value) => {
  if (!value) return 'Unknown time';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unknown time';
  return date.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const normalizeSessions = (response) => {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.sessions)) return response.sessions;
  if (Array.isArray(response?.items)) return response.items;
  if (Array.isArray(response?.data)) return response.data;
  return [];
};

const HistoryView = ({ onNavigate }) => {
  const [sessions, setSessions] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');

  const loadHistory = async () => {
    setLoading(true);
    setError('');

    try {
      const [sessionResponse, statsResponse] = await Promise.all([
        chatAPI.getSessions(null, 1, 20),
        chatAPI.getChatStats().catch(() => null),
      ]);

      setSessions(normalizeSessions(sessionResponse));
      setStats(statsResponse);
    } catch (err) {
      setError(err.message || 'Unable to load history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const filteredSessions = useMemo(() => {
    if (filter === 'all') return sessions;
    if (filter === 'active') return sessions.filter((session) => session.is_active !== false);
    if (filter === 'archived') return sessions.filter((session) => session.is_active === false);
    return sessions;
  }, [sessions, filter]);

  const totalSessions = stats?.total_sessions ?? sessions.length;
  const activeSessions = stats?.active_sessions ?? sessions.filter((session) => session.is_active !== false).length;
  const totalMessages = stats?.total_messages ?? stats?.messages_count ?? 0;

  return (
    <div className="page-view">
      <div className="page-hero">
        <div className="page-heading">
          <div className="page-title">
            <div className="page-icon">🕒</div>
            <div>
              <h1>History</h1>
              <p>Review recent conversations, active threads, and archived sessions.</p>
            </div>
          </div>
        </div>

        <div className="page-actions">
          <button className="page-button" onClick={loadHistory} type="button">
            Refresh
          </button>
          <button className="page-button primary" onClick={() => onNavigate?.('chat')} type="button">
            Open Chat
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Sessions</div>
          <div className="stat-value">{totalSessions}</div>
          <div className="stat-note">Saved chat threads in the database.</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Sessions</div>
          <div className="stat-value">{activeSessions}</div>
          <div className="stat-note">Sessions still marked active.</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Messages</div>
          <div className="stat-value">{totalMessages}</div>
          <div className="stat-note">Conversation turns across sessions.</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Visible Threads</div>
          <div className="stat-value">{filteredSessions.length}</div>
          <div className="stat-note">Current filter results.</div>
        </div>
      </div>

      <div className="content-grid">
        <section className="section-card">
          <h2>Recent Sessions</h2>
          <div className="pill-row" style={{ marginBottom: 'var(--space-4)' }}>
            <button className={`pill ${filter === 'all' ? '' : 'dim'}`} type="button" onClick={() => setFilter('all')}>
              All
            </button>
            <button className={`pill ${filter === 'active' ? '' : 'dim'}`} type="button" onClick={() => setFilter('active')}>
              Active
            </button>
            <button className={`pill ${filter === 'archived' ? '' : 'dim'}`} type="button" onClick={() => setFilter('archived')}>
              Archived
            </button>
          </div>

          {loading ? (
            <div className="page-loading">
              <div className="page-loading-spinner" />
              <div>Loading session history...</div>
            </div>
          ) : error ? (
            <div className="empty-state-card">
              <h3>Could not load history</h3>
              <p>{error}</p>
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="empty-state-card">
              <h3>No sessions yet</h3>
              <p>Start a chat and your conversation history will appear here.</p>
            </div>
          ) : (
            <div className="session-list">
              {filteredSessions.map((session) => (
                <div className="session-item" key={session.id || session._id || session.title}>
                  <div className="session-main">
                    <div className="session-title">{session.title || 'Untitled session'}</div>
                    <div className="session-meta">
                      {formatDateTime(session.created_at || session.updated_at)} •{' '}
                      {Array.isArray(session.document_ids) ? session.document_ids.length : 0} document
                      {Array.isArray(session.document_ids) && session.document_ids.length !== 1 ? 's' : ''}
                    </div>
                  </div>
                  <div className="pill-row">
                    <span className={`pill ${session.is_active === false ? 'dim' : ''}`}>
                      {session.is_active === false ? 'Archived' : 'Active'}
                    </span>
                    <button className="page-button" type="button" onClick={() => onNavigate?.('chat')}>
                      Open
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <aside className="section-card">
          <h3>Quick View</h3>
          <p>
            This page shows the most recent sessions returned by the backend. If you want a richer
            conversation browser later, we can add message previews and full session detail.
          </p>
          <div className="help-list" style={{ marginTop: 'var(--space-4)' }}>
            <div className="faq-item">
              <div className="session-main">
                <div className="session-title">Last refresh</div>
                <div className="session-meta">{new Date().toLocaleString()}</div>
              </div>
            </div>
            <div className="faq-item">
              <div className="session-main">
                <div className="session-title">Session source</div>
                <div className="session-meta">MongoDB-backed chat sessions</div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default HistoryView;
