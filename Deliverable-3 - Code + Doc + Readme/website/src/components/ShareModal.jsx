import React from 'react';
import { motion } from 'framer-motion';
import { X, Copy, Folder, MoreHorizontal, Sparkles, Box } from 'lucide-react';

const ShareModal = ({ photo, onClose }) => {
  return (
    <motion.div
      className="share-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <motion.div
        className="share-card glass-heavy"
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", damping: 25, stiffness: 300 }}
      >
        <div className="share-header">
          <button onClick={onClose} className="close-btn">
            <X size={20} />
          </button>
          <h3>Ready To Share</h3>
          <div style={{ width: 20 }}></div> {/* Spacer */}
        </div>

        <div className="preview-container">
          <img src={photo?.image} alt="Preview" className="preview-img" />
        </div>

        <div className="share-controls">
          <div className="ai-badge glass">
            <div className="badge-header">
              <Sparkles size={12} className="text-accent" />
              <span>AI Content Credentials</span>
              <div className="toggle-switch active"></div>
            </div>
            <div className="badge-tags">
              <span className="tag active"><Sparkles size={10} /> Auto Relight</span>
              <span className="tag active"><Box size={10} /> 3D Depth Effect</span>
            </div>
          </div>

          <div className="action-grid">
            <div className="action-item">
              <div className="circle-btn glass">
                <Copy size={20} />
              </div>
              <span>Copy</span>
            </div>
            <div className="action-item">
              <div className="circle-btn glass">
                <Folder size={20} />
              </div>
              <span>Folder</span>
            </div>
            <div className="action-item">
              <div className="circle-btn glass">
                <MoreHorizontal size={20} />
              </div>
              <span>More</span>
            </div>
          </div>

          <button className="save-btn">
            Save Image
          </button>
        </div>
      </motion.div>

      <style>{`
        .share-overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0,0,0,0.6);
          z-index: 100;
          display: flex;
          align-items: flex-end;
        }

        .share-card {
          width: 100%;
          height: 85%;
          border-top-left-radius: 32px;
          border-top-right-radius: 32px;
          padding: 20px;
          display: flex;
          flex-direction: column;
          background: #1c1c1e; /* Fallback */
        }

        .share-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .share-header h3 {
          font-size: 16px;
          font-weight: 600;
        }

        .close-btn {
          color: white;
          opacity: 0.7;
        }

        .preview-container {
          flex: 1;
          border-radius: 24px;
          overflow: hidden;
          margin-bottom: 20px;
          position: relative;
        }

        .preview-img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .share-controls {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .ai-badge {
          padding: 12px;
          border-radius: 16px;
          background: rgba(255,255,255,0.05);
        }

        .badge-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 10px;
          font-size: 12px;
          font-weight: 500;
        }

        .toggle-switch {
          width: 32px;
          height: 18px;
          background: rgba(255,255,255,0.2);
          border-radius: 10px;
          margin-left: auto;
          position: relative;
        }

        .toggle-switch.active {
          background: var(--accent-blue);
        }

        .toggle-switch::after {
          content: '';
          position: absolute;
          top: 2px;
          right: 2px;
          width: 14px;
          height: 14px;
          background: white;
          border-radius: 50%;
        }

        .badge-tags {
          display: flex;
          gap: 8px;
          overflow-x: auto;
        }

        .tag {
          padding: 4px 10px;
          border-radius: 12px;
          background: rgba(10, 132, 255, 0.2);
          color: #60a5fa;
          font-size: 10px;
          display: flex;
          align-items: center;
          gap: 4px;
          border: 1px solid rgba(10, 132, 255, 0.3);
        }

        .action-grid {
          display: flex;
          justify-content: space-around;
        }

        .action-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
        }

        .action-item span {
          font-size: 11px;
          color: rgba(255,255,255,0.6);
        }

        .circle-btn {
          width: 50px;
          height: 50px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(255,255,255,0.08);
        }

        .save-btn {
          width: 100%;
          padding: 16px;
          background: rgba(255,255,255,0.1);
          border-radius: 20px;
          color: var(--accent-blue);
          font-weight: 600;
          font-size: 16px;
          border: 1px solid rgba(255,255,255,0.1);
        }
      `}</style>
    </motion.div>
  );
};

export default ShareModal;
