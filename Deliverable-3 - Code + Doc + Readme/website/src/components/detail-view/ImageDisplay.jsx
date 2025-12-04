import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import MicIcon from '../../assets/icons/Screen-3/mic.svg';
import SunMoonIcon from '../../assets/icons/Screen-3/sun-moon.svg';
import BoxIcon from '../../assets/icons/Screen-3/box.svg';

const ImageDisplay = ({
  image,
  title,
  id,
  activeTool,
  showFinalView,
  onToggleRelight,
  onToggleDepth,
  onOpenVoice,
  isRecording,
  onToggleRecording,
  isProcessing,
  agentMessage,
  isReviewingAgent,
  onImageClick,
  onUndo,
  canUndo,
  children
}) => {
  const timerRef = React.useRef(null);
  const isLongPress = React.useRef(false);

  const truncateMessage = (message) => {
    const words = message.split(' ');
    if (words.length <= 5) return message;
    return words.slice(0, 5).join(' ') + '...';
  };

  const handleVoiceBarClick = (e) => {
    // If it's a long press, don't toggle recording
    if (isLongPress.current) {
      return;
    }
    console.log('📱 Voice bar clicked, calling onToggleRecording');
    onToggleRecording();
  };

  const handleTouchStart = (e) => {
    isLongPress.current = false;
    // Only enable long-press when NOT recording
    if (!isRecording) {
      timerRef.current = setTimeout(() => {
        isLongPress.current = true;
        if (navigator.vibrate) navigator.vibrate(50);
        onOpenVoice();
      }, 500);
    }
  };

  const handleTouchEnd = (e) => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
  };

  const handleTouchCancel = (e) => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
  };

  return (
    <div className="image-area">
      {/* Blurred Background */}
      <div
        className="blurred-bg"
        style={{ backgroundImage: `url(${image})` }}
      />

      {/* Image Section */}
      <div className="image-section">
        {!activeTool && !showFinalView && (
          <motion.div
            className="main-image-wrapper"
            layoutId={`image-${id}`}
            transition={{ duration: 0.5, ease: "easeInOut" }}
            onClick={onImageClick}
            style={{ cursor: onImageClick ? 'pointer' : 'default' }}
          >
            <img src={image} alt={title} />
          </motion.div>
        )}
      </div>

      {/* Tool Overlays */}
      {children}

      {/* Controls Section - Below Image */}
      <AnimatePresence>
        {!activeTool && (
          <motion.div
            className="controls-section"
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0, transition: { duration: 0 } }}
            transition={{ duration: 0.3, ease: "easeOut" }}
          >
            {/* Controls Section - Only show when no tool is active and not reviewing */}
            {!isReviewingAgent && (
              <div className="action-buttons">
                <button
                  className={`tool-btn relight-btn ${activeTool === 'relight' ? 'active' : ''}`}
                  onClick={onToggleRelight}
                >
                  <img src={SunMoonIcon} alt="Relight" style={{ width: 16, height: 16 }} />
                  <span>Auto Relight</span>
                </button>
                <button
                  className={`tool-btn depth-btn ${activeTool === 'depth' ? 'active' : ''}`}
                  onClick={onToggleDepth}
                >
                  <img src={BoxIcon} alt="3D Depth" style={{ width: 16, height: 16 }} />
                  <span>3D Depth Effect</span>
                </button>
              </div>
            )}

            {/* Voice Bar - Minimize during review */}
            <div
              className={`voice-bar glass-heavy ${isRecording ? 'recording' : ''} ${isProcessing ? 'processing' : ''} ${agentMessage ? 'speaking' : ''} ${isReviewingAgent ? 'minimized' : ''}`}
              onClick={handleVoiceBarClick}
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
              onTouchCancel={handleTouchCancel}
              onMouseDown={handleTouchStart}
              onMouseUp={handleTouchEnd}
              onMouseLeave={handleTouchCancel}
            >
              <div className="mic-icon">
                {isProcessing ? (
                  <div className="spinner"></div>
                ) : (
                  <img src={MicIcon} alt="Mic" style={{ width: 24, height: 24, opacity: isRecording ? 1 : 0.8 }} />
                )}
              </div>
              <div className="voice-divider"></div>
              <span className="voice-text">
                {isRecording ? 'Listening...' : isProcessing ? 'Thinking...' : agentMessage ? truncateMessage(agentMessage) : 'Tap to speak, hold for history'}
              </span>
              {/* Show undo button when message is displayed and undo is available */}
              {agentMessage && canUndo && !isProcessing && (
                <button
                  className="undo-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onUndo();
                  }}
                >
                  ↶
                </button>
              )}
              {isRecording && (
                <div className="waveform active">
                  {[...Array(12)].map((_, i) => (
                    <motion.div
                      key={i}
                      className="bar"
                      animate={{ height: [10, 24, 10] }}
                      transition={{ repeat: Infinity, duration: 0.8, delay: i * 0.05 }}
                    />
                  ))}
                </div>
              )}
              {!isRecording && !isProcessing && (
                <div className="waveform">
                  {[...Array(12)].map((_, i) => (
                    <motion.div
                      key={i}
                      className="bar"
                      animate={{ height: [10, 14, 10] }}
                      transition={{ repeat: Infinity, duration: 2, delay: i * 0.1 }}
                    />
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <style>{`
        .image-area {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          position: relative;
          padding: 0;
        }

        .blurred-bg {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background-size: cover;
          background-position: center;
          filter: blur(20px);
          opacity: 0.8;
          z-index: 0;
        }

        .blurred-bg::after {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.6);
        }

        .image-section {
          flex: 0 1 auto;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-top: 66px;
          padding: 56px 10px 8px 6px;
          z-index: 1;
        }

        @media (max-width: 450px) {
          .image-section {
            margin-top: 32px;
            padding-top: 80px;
            padding-bottom: 0px;
          }
          
          .main-image-wrapper {
            max-height: 60vh;
            width: auto;
            margin: 0 auto;
          }

          .controls-section {
            position: relative !important;
            bottom: auto !important;
            margin-top: 42px !important;
            left: 0;
            width: 100%;
            padding-bottom: 0px;
            gap: 4px;
            z-index: 10;
          }
        }

        .main-image-wrapper {
          width: 100%;
          max-width: 500px;
          aspect-ratio: 3/4;
          border-radius: 24px;
          overflow: hidden;
          position: relative;
          z-index: 1;
          box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }

        .main-image-wrapper img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          display: block;
        }

        .controls-section {
          position: absolute;
          bottom: 40px;
          left: 0;
          width: 100%;
          z-index: 10;
          padding-bottom: 20px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 20px;
          padding-top: 0; /* Ensure top padding is reset if needed */
          padding-left: 20px;
          padding-right: 20px;
          /* margin-top: 48px; - removed as it's now absolutely positioned */
        }

        .action-buttons {
          display: inline-flex;
          align-items: center;
          gap: 33px;
        }

        .tool-btn {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 8px;
          border-radius: 40px;
          border: 1px solid #68AFFF;
          background: rgba(0, 0, 0, 0.40);
          box-shadow: 1px -1px 24px -2px #68AFFF inset;
          backdrop-filter: blur(2px);
          cursor: pointer;
          transition: all 0.2s;
        }

        .tool-btn span {
          color: #D9D9D9;
          font-feature-settings: 'liga' off, 'clig' off;
          font-family: "SF Pro", -apple-system, sans-serif;
          font-size: 12px;
          font-style: normal;
          font-weight: 510;
          line-height: 41px;
        }

        .relight-btn {
          padding: 0 9.5px 0 10.5px;
        }

        .depth-btn {
          padding: 0 10.5px 0 11.5px;
        }

        .tool-btn:active {
          transform: scale(0.95);
          background: rgba(0, 0, 0, 0.6);
        }

        .tool-btn.active {
          background: rgba(50, 150, 200, 0.5);
          border-color: rgba(100, 200, 255, 0.5);
        }

        .voice-bar {
          width: 343px;
          max-width: 100%;
          height: 63px;
          border-radius: 40px;
          display: flex;
          align-items: center;
          padding: 0 16px;
          gap: 12px;
          border: 1px solid rgba(159, 203, 253, 0.75);
          background: rgba(0, 0, 0, 0.40);
          box-shadow: 1px -1px 24px -2px #68AFFF inset;
          backdrop-filter: blur(2px);
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .voice-bar.recording {
            border-color: #ef4444;
            box-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
        }

        .voice-bar.processing {
            border-color: #8b5cf6;
            box-shadow: 0 0 20px rgba(139, 92, 246, 0.3);
        }

        .voice-bar.speaking {
            border-color: #10b981;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
            background: rgba(16, 185, 129, 0.1);
        }

        .voice-bar.minimized {
            height: 40px;
            opacity: 0.5;
            transform: scale(0.95);
            pointer-events: none;
        }

        .voice-bar.minimized .voice-text {
            font-size: 12px;
        }

        .voice-bar.minimized .waveform {
            display: none;
        }

        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .mic-icon {
          width: 24px;
          height: 24px;
          aspect-ratio: 1/1;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .voice-divider {
          width: 1.5px;
          height: 25px;
          background: #BEDCFD;
          box-shadow: 0 2px 4px 0 rgba(255, 255, 255, 0.25);
          flex-shrink: 0;
        }

        .voice-text {
          flex: 1;
          font-size: 14px;
          color: rgba(255,255,255,0.9);
          font-weight: 400;
        }

        .undo-btn {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          border: 1px solid rgba(255,255,255,0.3);
          background: rgba(255,255,255,0.1);
          color: white;
          font-size: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s;
          flex-shrink: 0;
        }

        .undo-btn:hover {
          background: rgba(255,255,255,0.2);
          border-color: rgba(255,255,255,0.5);
          transform: scale(1.05);
        }

        .undo-btn:active {
          transform: scale(0.95);
        }

        .waveform {
          display: flex;
          align-items: center;
          gap: 3px;
          margin-right: 12px;
          width: 58px;
          height: 25px;
        }

        .bar {
          width: 3px;
          background: #9FCBFD;
          border-radius: 2px;
          stroke-width: 1px;
          stroke: rgba(255, 255, 255, 0.21);
          filter: drop-shadow(0 1px 8px rgba(255, 255, 255, 0.42));
        }
      `}</style>
    </div>
  );
};

export default ImageDisplay;