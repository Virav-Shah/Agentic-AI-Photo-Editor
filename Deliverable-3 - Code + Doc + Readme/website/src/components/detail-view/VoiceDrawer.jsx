import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Square, Loader2, Image as ImageIcon, MessageSquare, ArrowLeft, Clock } from 'lucide-react';

const VoiceDrawer = ({ isOpen, onClose, history = [], onRestore, aiMode, setAiMode, isProcessing }) => {
  const [view, setView] = useState('pipeline'); // 'pipeline' | 'results'
  const scrollRef = useRef(null);

  // Auto-scroll to bottom of pipeline
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history, view, isOpen]);

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Filter history for results view (only items with images)
  const resultsHistory = history.filter(item => item.image);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className="drawer-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="voice-drawer"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
          >
            <div className="drawer-handle"></div>

            {/* Header */}
            <div className="drawer-header">
              <div className="header-left">
                <div className="ai-mode-toggle">
                  <button
                    className={`mode-btn ${aiMode === 'fast' ? 'active' : ''}`}
                    onClick={() => setAiMode('fast')}
                  >
                    Fast
                  </button>
                  <button
                    className={`mode-btn ${aiMode === 'thinking' ? 'active' : ''}`}
                    onClick={() => setAiMode('thinking')}
                  >
                    Thinking
                  </button>
                </div>
              </div>

              <button
                className={`view-switch-btn ${view === 'results' ? 'active' : ''}`}
                onClick={() => setView(view === 'pipeline' ? 'results' : 'pipeline')}
              >
                {view === 'pipeline' ? <ImageIcon size={18} /> : <MessageSquare size={18} />}
                <span>{view === 'pipeline' ? 'Results' : 'Pipeline'}</span>
              </button>
            </div>

            {/* Content Area */}
            <div className="drawer-content" ref={scrollRef}>
              {view === 'pipeline' ? (
                <div className="pipeline-view">
                  {history.length === 0 ? (
                    <div className="empty-state">
                      <p>No history yet. Start speaking!</p>
                    </div>
                  ) : (
                    history.map((item) => (
                      <div key={item.id} className={`pipeline-item ${item.type}`}>
                        <div className="item-content">
                          {item.type === 'user' ? (
                            <p className="user-text">"{item.content}"</p>
                          ) : (
                            <div className="agent-result">
                              <p className="agent-text">{item.content}</p>
                              {item.image && (
                                <img src={item.image} alt="Result" className="result-thumb" />
                              )}
                            </div>
                          )}
                          <span className="timestamp">{formatTime(item.timestamp)}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              ) : (
                <div className="results-view">
                  {resultsHistory.length === 0 ? (
                    <div className="empty-state">
                      <p>No results generated yet.</p>
                    </div>
                  ) : (
                    <div className="results-grid">
                      {resultsHistory.map((item) => (
                        <div key={item.id} className="result-card" onClick={() => { onRestore(item); onClose(); }}>
                          <img src={item.image} alt="Result" />
                          <div className="result-info">
                            <Clock size={12} />
                            <span>{formatTime(item.timestamp)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

          </motion.div>

          <style>{`
            .drawer-backdrop {
              position: absolute;
              top: 0;
              left: 0;
              width: 100%;
              height: 100%;
              background: rgba(0,0,0,0.5);
              z-index: 90;
            }

            .voice-drawer {
              position: absolute;
              bottom: 0;
              left: -2px;
              width: 100%;
              height: 80%; /* Taller drawer */
              background: linear-gradient(187deg, rgba(35, 45, 56, 0.95) 7.38%, rgba(35, 45, 56, 0.95) 36.2%);
              backdrop-filter: blur(20px);
              -webkit-backdrop-filter: blur(20px);
              border-top-left-radius: 32px;
              border-top-right-radius: 32px;
              border: 1px solid rgba(159, 203, 253, 0.39);
              border-bottom: none;
              padding: 20px;
              z-index: 100;
              display: flex;
              flex-direction: column;
            }

            .drawer-handle {
              width: 40px;
              height: 4px;
              background: rgba(255,255,255,0.3);
              border-radius: 2px;
              margin: 0 auto 20px;
              flex-shrink: 0;
            }

            .drawer-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                flex-shrink: 0;
            }

            .header-left {
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .back-btn {
                background: rgba(255,255,255,0.1);
                border: none;
                border-radius: 50%;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                cursor: pointer;
            }

            .ai-mode-toggle {
              display: flex;
              background: rgba(0,0,0,0.3);
              border-radius: 20px;
              padding: 2px;
            }

            .mode-btn {
              padding: 6px 16px;
              border-radius: 18px;
              border: none;
              background: transparent;
              color: var(--text-secondary);
              font-size: 13px;
              font-weight: 500;
              cursor: pointer;
              transition: all 0.2s;
            }

            .mode-btn.active {
              background: rgba(255,255,255,0.15);
              color: white;
            }

            .view-switch-btn {
                display: flex;
                align-items: center;
                gap: 6px;
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                padding: 6px 12px;
                border-radius: 16px;
                color: white;
                font-size: 13px;
                cursor: pointer;
            }

            .view-switch-btn.active {
                background: rgba(104, 175, 255, 0.2);
                border-color: #68AFFF;
            }

            .drawer-content {
                flex: 1;
                overflow-y: auto;
                margin-bottom: 20px;
                padding-right: 4px;
            }

            .pipeline-view {
                display: flex;
                flex-direction: column;
                gap: 16px;
            }

            .pipeline-item {
                display: flex;
                flex-direction: column;
                max-width: 85%;
            }

            .pipeline-item.user {
                align-self: flex-end;
                align-items: flex-end;
            }

            .pipeline-item.agent {
                align-self: flex-start;
                align-items: flex-start;
            }

            .item-content {
                padding: 12px 16px;
                border-radius: 16px;
                position: relative;
            }

            .pipeline-item.user .item-content {
                background: #0a84ff;
                color: white;
                border-bottom-right-radius: 4px;
            }

            .pipeline-item.agent .item-content {
                background: rgba(255,255,255,0.1);
                color: white;
                border-bottom-left-radius: 4px;
            }

            .user-text, .agent-text {
                margin: 0;
                font-size: 15px;
                line-height: 1.4;
            }

            .result-thumb {
                width: 100%;
                height: auto;
                border-radius: 8px;
                margin-top: 8px;
                border: 1px solid rgba(255,255,255,0.1);
            }

            .timestamp {
                font-size: 10px;
                opacity: 0.6;
                margin-top: 4px;
                display: block;
                text-align: right;
            }

            .results-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
            }

            .result-card {
                position: relative;
                aspect-ratio: 1;
                border-radius: 12px;
                overflow: hidden;
                border: 1px solid rgba(255,255,255,0.1);
                cursor: pointer;
            }

            .result-card img {
                width: 100%;
                height: 100%;
                object-fit: cover;
            }

            .result-info {
                position: absolute;
                bottom: 0;
                left: 0;
                width: 100%;
                background: rgba(0,0,0,0.6);
                padding: 6px;
                display: flex;
                align-items: center;
                gap: 4px;
                color: white;
                font-size: 11px;
            }

            .empty-state {
                text-align: center;
                color: var(--text-secondary);
                margin-top: 40px;
            }

            .drawer-footer {
                display: flex;
                align-items: center;
                gap: 16px;
                padding-top: 10px;
                border-top: 1px solid rgba(255,255,255,0.1);
                flex-shrink: 0;
            }

            .mic-container-small {
                width: 48px;
                height: 48px;
                border-radius: 50%;
                background: rgba(255,255,255,0.1);
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s;
            }

            .mic-container-small:active {
                transform: scale(0.95);
                background: rgba(255,255,255,0.2);
            }

            .status-text {
                color: var(--text-secondary);
                font-size: 14px;
            }

            .typing-indicator span {
                display: inline-block;
                width: 6px;
                height: 6px;
                background: white;
                border-radius: 50%;
                margin: 0 2px;
                animation: bounce 1.4s infinite ease-in-out both;
            }

            .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
            .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

            @keyframes bounce {
                0%, 80%, 100% { transform: scale(0); }
                40% { transform: scale(1); }
            }
          `}</style>
        </>
      )}
    </AnimatePresence>
  );
};

export default VoiceDrawer;
