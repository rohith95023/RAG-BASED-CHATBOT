import React from 'react';
import './Pages.css';

const HelpView = ({ onNavigate }) => {
  const steps = [
    {
      title: 'Upload documents',
      body: 'Start with the Upload page to add PDFs or office files, then move to chat with your documents selected.',
    },
    {
      title: 'Ask in chat',
      body: 'Use FLASH MAN for general questions, or switch to Documents to ground answers in your files.',
    },
    {
      title: 'Use voice tools',
      body: 'Tap Speak on an assistant response, or use the microphone icon to dictate your prompt.',
    },
  ];

  const shortcuts = [
    { key: 'Enter', label: 'Send message' },
    { key: 'Shift + Enter', label: 'New line' },
    { key: 'Stop Audio', label: 'Cancel speech playback' },
    { key: 'Clear', label: 'Reset the current chat' },
  ];

  const faqs = [
    {
      question: 'Why is my response not speaking after refresh?',
      answer: 'The app now cancels any queued speech on load and page exit, so refresh should stop speech immediately.',
    },
    {
      question: 'Can I ask questions without documents?',
      answer: 'Yes. Use the FLASH MAN mode for standalone assistant answers, image questions, and voice input.',
    },
    {
      question: 'How do I get document-grounded answers?',
      answer: 'Go to Documents, select one or more files, and then chat from the selected set.',
    },
  ];

  return (
    <div className="page-view">
      <div className="page-hero">
        <div className="page-heading">
          <div className="page-title">
            <div className="page-icon">❓</div>
            <div>
              <h1>Help</h1>
              <p>Quick start, keyboard hints, and support notes for FLASH MAN.</p>
            </div>
          </div>
        </div>

        <div className="page-actions">
          <button className="page-button" onClick={() => onNavigate?.('upload')} type="button">
            Upload Files
          </button>
          <button className="page-button primary" onClick={() => onNavigate?.('chat')} type="button">
            Open Chat
          </button>
        </div>
      </div>

      <div className="help-grid">
        <section className="section-card">
          <h2>Quick Start</h2>
          <div className="help-steps">
            {steps.map((step, index) => (
              <div className="help-step" key={step.title}>
                <div className="help-step-index">{index + 1}</div>
                <div>
                  <h4>{step.title}</h4>
                  <p>{step.body}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="section-card">
          <h2>Keyboard & Actions</h2>
          <div className="help-list">
            {shortcuts.map((shortcut) => (
              <div className="shortcut-item" key={shortcut.key}>
                <div className="shortcut-key">{shortcut.key}</div>
                <div className="session-main" style={{ flex: 1 }}>
                  <div className="session-title">{shortcut.label}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="content-grid" style={{ marginTop: 'var(--space-4)' }}>
        <section className="section-card">
          <h2>FAQ</h2>
          <div className="help-list">
            {faqs.map((faq) => (
              <div className="faq-item" key={faq.question}>
                <div className="session-main">
                  <div className="session-title">{faq.question}</div>
                  <div className="faq-answer">{faq.answer}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="section-card">
          <h2>Need More?</h2>
          <p>
            If something still feels off, open History to review sessions or Settings to adjust the
            local UI behavior. The app is designed for offline-friendly local work, so most controls
            live directly in the interface.
          </p>
          <div className="empty-state-card" style={{ marginTop: 'var(--space-4)' }}>
            <h3>Support checklist</h3>
            <div className="pill-row">
              <span className="pill">Refresh chat</span>
              <span className="pill">Stop audio</span>
              <span className="pill">Check selected docs</span>
              <span className="pill">Review settings</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default HelpView;
