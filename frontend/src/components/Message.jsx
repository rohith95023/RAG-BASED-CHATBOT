import React from 'react';
import './Message.css';

const Message = ({
  messageId,
  text,
  isUser,
  isError,
  isStreaming,
  image,
  mimeType,
  onSpeak,
  onStopSpeak,
  isSpeaking,
}) => {
  const [copied, setCopied] = React.useState(false);

  const getClassName = () => {
    let className = 'message-bubble';
    if (isUser) className += ' message-user';
    else className += ' message-ai';
    if (isError) className += ' message-error';
    return className;
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderText = (content) => {
    if (!content) return null;

    const lines = content.split('\n');
    let inList = false;
    let listItems = [];
    const elements = [];

    lines.forEach((line, index) => {
      const isBullet = /^[*-]\s+/.test(line.trim()) || /^\d+\.\s+/.test(line.trim());

      if (isBullet) {
        if (!inList) {
          inList = true;
          listItems = [];
        }
        const cleanLine = line.trim().replace(/^[*-]\s+/, '').replace(/^\d+\.\s+/, '');
        listItems.push(<li key={`li-${index}`} style={{ marginBottom: '4px' }}>{cleanLine}</li>);
      } else {
        if (inList) {
          elements.push(<ul key={`ul-${index}`} style={{ margin: '8px 0', paddingLeft: '24px' }}>{[...listItems]}</ul>);
          inList = false;
          listItems = [];
        }

        if (line.trim()) {
          elements.push(<p key={`p-${index}`} style={{ margin: '8px 0', lineHeight: '1.5' }}>{line}</p>);
        }
      }
    });

    if (inList && listItems.length > 0) {
      elements.push(<ul key="ul-end" style={{ margin: '8px 0', paddingLeft: '24px' }}>{listItems}</ul>);
    }

    return elements.length > 0 ? elements : <p>{content}</p>;
  };

  const imageSrc = image
    ? image.startsWith('data:')
      ? image
      : `data:${mimeType || 'image/png'};base64,${image}`
    : null;

  return (
    <div className={`message-wrapper ${isUser ? 'user' : 'ai'}`}>
      <div className={getClassName()}>
        {isError && <span className="message-error-icon">!</span>}

        {imageSrc && (
          <div className="message-image">
            <img src={imageSrc} alt="Uploaded context" />
          </div>
        )}

        {isStreaming && !text ? (
          <div className="message-thinking" role="status" aria-label="Generating response">
            <span className="thinking-dot"></span>
            <span className="thinking-dot"></span>
            <span className="thinking-dot"></span>
            <span>Thinking</span>
          </div>
        ) : (
          <div className="message-content">
            {renderText(text)}
          </div>
        )}

        {!isError && text && !isStreaming && (
          <div className="message-actions">
            {!isUser && (
              <button
                onClick={() => {
                  if (isSpeaking) onStopSpeak?.();
                  else onSpeak?.(text, messageId);
                }}
                className={`message-action-button ${isSpeaking ? 'speaking' : ''}`}
                title={isSpeaking ? 'Stop reading' : 'Read aloud'}
                type="button"
              >
                {isSpeaking ? 'Stop' : 'Speak'}
              </button>
            )}
            <button
              onClick={handleCopy}
              className="message-action-button"
              title="Copy message"
              type="button"
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Message;
