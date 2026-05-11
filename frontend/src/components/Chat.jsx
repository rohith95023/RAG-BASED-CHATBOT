import React, { useEffect, useRef, useState } from 'react';
import Message from './Message';
import { chatAPI, documentsAPI } from '../services/api';
import './Chat.css?v=3';

const APP_NAME = 'FLASH MAN';
const APP_SHORT = 'FM';

const DEFAULT_GREETING = {
  text: `Hello! I'm in ${APP_NAME} mode by default. Ask anything, attach an image, or switch to Documents when you want answers grounded in your PDFs.`,
  isUser: false,
};

const Chat = ({ selectedDocumentIds = [] }) => {
  const [messages, setMessages] = useState([DEFAULT_GREETING]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chatMode, setChatMode] = useState(selectedDocumentIds.length > 0 ? 'document' : 'gemini');
  const [activeDocuments, setActiveDocuments] = useState([]);
  const [attachedImage, setAttachedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [speakingMessageId, setSpeakingMessageId] = useState(null);
  const [abortController, setAbortController] = useState(null);
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const fileInputRef = useRef(null);
  const recognitionRef = useRef(null);
  const speechUtteranceRef = useRef(null);
  const speechStopTimerRef = useRef(null);

  const hasSelectedDocuments = selectedDocumentIds.length > 0;
  const effectiveDocumentIds = chatMode === 'document' && hasSelectedDocuments ? selectedDocumentIds : [];

  useEffect(() => {
    if (selectedDocumentIds.length > 0) {
      setChatMode('document');
    }
  }, [selectedDocumentIds]);

  useEffect(() => {
    const fetchDocDetails = async () => {
      if (hasSelectedDocuments) {
        try {
          const docs = await Promise.all(selectedDocumentIds.map(id => documentsAPI.getDocument(id)));
          setActiveDocuments(docs);
        } catch (err) {
          console.error('Failed to fetch doc details:', err);
          setActiveDocuments([]);
        }
      } else {
        setActiveDocuments([]);
      }
    };

    fetchDocDetails();
  }, [hasSelectedDocuments, selectedDocumentIds]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    return () => {
      if (imagePreview) URL.revokeObjectURL(imagePreview);
    };
  }, [imagePreview]);

  useEffect(() => {
    const stopSpeech = () => {
      window.speechSynthesis?.cancel();
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') stopSpeech();
    };

    stopSpeech();

    // Some browsers keep queued speech alive briefly across reloads, so we cancel
    // a few times during startup to make the stop behavior reliable.
    speechStopTimerRef.current = window.setTimeout(stopSpeech, 50);
    const followUpTimer = window.setTimeout(stopSpeech, 250);

    window.addEventListener('beforeunload', stopSpeech);
    window.addEventListener('pagehide', stopSpeech);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      stopSpeech();
      recognitionRef.current?.stop();
      if (speechStopTimerRef.current) window.clearTimeout(speechStopTimerRef.current);
      window.clearTimeout(followUpTimer);
      window.removeEventListener('beforeunload', stopSpeech);
      window.removeEventListener('pagehide', stopSpeech);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  const handleModeChange = (mode) => {
    setChatMode(mode);
    setError(null);
    if (mode === 'document' && attachedImage) {
      clearImage();
    }
  };

  const clearImage = () => {
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setAttachedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const fileToBase64 = (file) => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });

  const handleImageChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setError('Please attach an image file.');
      return;
    }

    try {
      if (imagePreview) URL.revokeObjectURL(imagePreview);
      const base64 = await fileToBase64(file);
      setAttachedImage({ base64, mimeType: file.type, name: file.name });
      setImagePreview(URL.createObjectURL(file));
      setChatMode('gemini');
      setError(null);
    } catch {
      setError('Could not read the selected image.');
    }
  };

  const handleVoiceInput = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError('Voice input is not supported in this browser.');
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      return;
    }

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    let committed = input ? `${input} ` : '';
    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
    };
    recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) committed += transcript;
        else interim += transcript;
      }
      setInput(`${committed}${interim}`.trimStart());
    };
    recognition.onerror = (event) => {
      setIsListening(false);
      setError(event.error === 'not-allowed' ? 'Microphone access denied.' : `Voice input failed: ${event.error}`);
    };
    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };
    recognition.start();
  };

  const stopSpeaking = () => {
    window.speechSynthesis?.cancel();
    if (speechUtteranceRef.current) {
      speechUtteranceRef.current.onend = null;
      speechUtteranceRef.current.onerror = null;
      speechUtteranceRef.current = null;
    }
    setSpeakingMessageId(null);
  };

  const speakText = (text, messageId) => {
    if (!('speechSynthesis' in window)) {
      setError('Text-to-speech is not supported in this browser.');
      return;
    }

    if (speakingMessageId === messageId) {
      stopSpeaking();
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.onstart = () => setSpeakingMessageId(messageId);
    utterance.onend = () => {
      speechUtteranceRef.current = null;
      setSpeakingMessageId(null);
    };
    utterance.onerror = () => {
      speechUtteranceRef.current = null;
      setSpeakingMessageId(null);
    };
    speechUtteranceRef.current = utterance;
    setSpeakingMessageId(messageId);
    window.speechSynthesis.speak(utterance);
  };

  const handleSend = async () => {
    if ((!input.trim() && !attachedImage) || isLoading) return;

    const userQuestion = input.trim() || 'Please analyze this image.';
    const imageForRequest = attachedImage;

    setMessages(prev => [
      ...prev,
      {
        text: userQuestion,
        isUser: true,
        image: imageForRequest?.base64 || null,
        mimeType: imageForRequest?.mimeType,
      },
      { text: '', isUser: false, isStreaming: true },
    ]);
    setInput('');
    clearImage();
    setIsLoading(true);
    setError(null);

    const controller = new AbortController();
    setAbortController(controller);

    try {
      let fullAnswer = '';

      await chatAPI.queryDocumentsStreaming(
        userQuestion,
        effectiveDocumentIds,
        null,
        5,
        0.3,
        (data) => {
          if (data.type === 'content') {
            fullAnswer += data.text;
            setMessages(prev => {
              const newMessages = [...prev];
              newMessages[newMessages.length - 1] = {
                ...newMessages[newMessages.length - 1],
                text: fullAnswer,
              };
              return newMessages;
            });
          } else if (data.type === 'error') {
            throw new Error(data.message);
          }
        },
        controller.signal,
        chatMode,
        chatMode === 'gemini' ? imageForRequest?.base64 : null,
        chatMode === 'gemini' ? imageForRequest?.mimeType : null,
      );

      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1] = {
          ...newMessages[newMessages.length - 1],
          isStreaming: false,
        };
        return newMessages;
      });
    } catch (error) {
      if (error.name === 'AbortError') {
        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            ...newMessages[newMessages.length - 1],
            isStreaming: false,
          };
          return newMessages;
        });
      } else {
        console.error('Chat error:', error);
        setError(error.message || 'Failed to get response. Please try again.');
        setMessages(prev => {
          const newMessages = [...prev];
          if (newMessages[newMessages.length - 1]?.isStreaming) {
            newMessages.pop();
          }
          return [
            ...newMessages,
            {
              text: `I apologize, but I encountered an error: ${error.message || 'Unknown error'}. Please try again.`,
              isUser: false,
              isError: true,
            },
          ];
        });
      }
    } finally {
      setIsLoading(false);
      setAbortController(null);
    }
  };

  const handleStop = () => {
    abortController?.abort();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearChat = () => {
    stopSpeaking();
    setMessages([DEFAULT_GREETING]);
    setError(null);
  };

  const handleSuggestionClick = (suggestion) => {
    setInput(suggestion);
    messagesContainerRef.current?.querySelector('textarea')?.focus();
  };

  const suggestions = chatMode === 'gemini'
    ? [
      'Explain this concept simply',
      'Draft a professional email',
      'Help me plan a project',
      'Analyze the image I attach',
    ]
    : [
      'What are the main topics in these documents?',
      'Summarize the key findings across documents',
      'What are the important dates mentioned?',
      'Explain the methodology used',
    ];

  const characterCount = input.length;
  const maxCharacters = 2000;
  const statusText = chatMode === 'gemini'
    ? `${APP_NAME} general chat`
    : activeDocuments.length > 0
      ? `Document answers from ${activeDocuments.length} selected document${activeDocuments.length !== 1 ? 's' : ''}`
      : 'Document answers from all documents';

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-header-info">
          <div className="chat-header-avatar">{chatMode === 'gemini' ? APP_SHORT : 'D'}</div>
          <div className="chat-header-details">
            <h2>{chatMode === 'gemini' ? `${APP_NAME} Assistant` : 'PDF Assistant'}</h2>
            <div className="chat-header-status">{statusText}</div>
          </div>
        </div>

        <div className="chat-header-actions">
          <div className="chat-mode-toggle" role="group" aria-label="Answer mode">
            <button
              className={`chat-mode-button ${chatMode === 'gemini' ? 'active' : ''}`}
              onClick={() => handleModeChange('gemini')}
              type="button"
            >
              {APP_NAME}
            </button>
            <button
              className={`chat-mode-button ${chatMode === 'document' ? 'active' : ''}`}
              onClick={() => handleModeChange('document')}
              type="button"
            >
              Documents
            </button>
          </div>
          <button
            className="chat-header-action stop-speaking"
            onClick={stopSpeaking}
            title={speakingMessageId ? 'Stop speaking' : 'No speech is currently playing'}
            type="button"
            disabled={!speakingMessageId}
          >
            Stop Audio
          </button>
          <button className="chat-header-action" onClick={handleClearChat} title="Clear chat" type="button">
            Clear
          </button>
        </div>
      </div>

      {error && (
        <div className="chat-inline-error">
          <span>{error}</span>
          <button onClick={() => setError(null)} type="button">Dismiss</button>
        </div>
      )}

      {messages.length === 1 && !isLoading && (
        <div className="chat-empty">
          <div className="chat-empty-icon">{chatMode === 'gemini' ? APP_SHORT : 'D'}</div>
          <h3>{chatMode === 'gemini' ? `Ask ${APP_NAME} anything` : 'Ask from your documents'}</h3>
          <p>
            {chatMode === 'gemini'
              ? `Use ${APP_NAME} for normal assistant answers, voice input, and image questions.`
              : hasSelectedDocuments
                ? 'Your selected documents are active. Questions will be grounded in those files.'
                : 'No specific documents selected, so document mode searches all uploaded PDFs.'}
          </p>
          <div className="chat-empty-suggestions">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                className="chat-empty-suggestion"
                onClick={() => handleSuggestionClick(suggestion)}
                type="button"
              >
                <span className="chat-empty-suggestion-text">{suggestion}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="messages-list" ref={messagesContainerRef}>
        {messages.map((msg, index) => (
          <div key={index} className={`message-group ${msg.isUser ? 'user' : 'ai'}`}>
            <Message
              messageId={`message-${index}`}
              text={msg.text}
              isUser={msg.isUser}
              isError={msg.isError}
              isStreaming={msg.isStreaming}
              image={msg.image}
              mimeType={msg.mimeType}
              onSpeak={speakText}
              onStopSpeak={stopSpeaking}
              isSpeaking={speakingMessageId === `message-${index}`}
            />
            {!msg.isUser && messages.length > 1 && !msg.isStreaming && (
              <div className="message-meta">
                {chatMode === 'gemini' ? APP_NAME : 'PDF Assistant'} - {new Date().toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            )}
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-shell">
        {imagePreview && (
          <div className="chat-attachment-preview">
            <img src={imagePreview} alt="Attachment preview" />
            <div>
              <strong>{attachedImage?.name}</strong>
              <span>Image will be sent to FLASH MAN</span>
            </div>
            <button onClick={clearImage} type="button">Remove</button>
          </div>
        )}

        <div className="chat-input-wrapper">
          <textarea
            className="chat-input"
            placeholder={
              chatMode === 'gemini'
                ? 'Ask FLASH MAN, speak with the mic, or attach an image...'
                : hasSelectedDocuments
                  ? `Ask about ${selectedDocumentIds.length} selected document${selectedDocumentIds.length !== 1 ? 's' : ''}...`
                  : 'Ask about all uploaded documents...'
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
            rows={1}
            onInput={(e) => {
              e.target.style.height = 'auto';
              e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
            }}
          />

          <div className="chat-input-actions">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageChange}
              style={{ display: 'none' }}
            />
            <button
              className="chat-input-action"
              title="Attach image"
              aria-label="Attach image"
              disabled={isLoading}
              onClick={() => fileInputRef.current?.click()}
              type="button"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="3" y="3" width="18" height="18" rx="3" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="M21 15l-4.5-4.5L5 21" />
              </svg>
            </button>
            <button
              className={`chat-input-action ${isListening ? 'listening' : ''}`}
              title={isListening ? 'Stop voice input' : 'Voice input'}
              aria-label={isListening ? 'Stop voice input' : 'Voice input'}
              disabled={isLoading}
              onClick={handleVoiceInput}
              type="button"
            >
              {isListening ? (
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="7" y="7" width="10" height="10" rx="2" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z" />
                  <path d="M19 11a7 7 0 0 1-14 0" />
                  <path d="M12 18v3" />
                  <path d="M8 21h8" />
                </svg>
              )}
            </button>
            {isLoading ? (
              <button
                className="chat-input-action send"
                onClick={handleStop}
                title="Stop generating"
                aria-label="Stop generating"
                type="button"
              >
                <div className="stop-square" />
              </button>
            ) : (
              <button
              className="chat-input-action send"
              onClick={handleSend}
              disabled={!input.trim() && !attachedImage}
              title="Send message"
              aria-label="Send message"
                type="button"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M22 2 11 13" />
                  <path d="m22 2-7 20-4-9-9-4 20-7Z" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>

      {characterCount > maxCharacters * 0.8 && (
        <div className="chat-input-footer">
          <div className={`character-count ${characterCount > maxCharacters ? 'error' : 'warning'}`}>
            {characterCount}/{maxCharacters}
          </div>
        </div>
      )}
    </div>
  );
};

export default Chat;
