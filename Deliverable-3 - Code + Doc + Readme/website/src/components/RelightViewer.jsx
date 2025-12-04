import React, { useRef } from 'react';
import { motion } from 'framer-motion';
import { X } from 'lucide-react';
import CheckIcon from '../assets/icons/Screen-4/check.svg';
import XIcon from '../assets/icons/Screen-4/x.svg';

const RelightViewer = ({ image, onClose, onAccept, onReject }) => {
  return (
    <motion.div
      className="relight-viewer-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {/* Blurred Background Image */}
      <div
        className="blurred-background"
        style={{
          backgroundImage: `url(${image})`,
        }}
      />

      <div className="viewer-controls">
        <button className="icon-btn glass" onClick={onClose}>
          <X size={20} />
        </button>
      </div>

      <div className="image-container">
        <img src={image} alt="Relight Preview" />
      </div>

      <div className="edit-actions">
        <button className="circle-action cancel" onClick={onReject}>
          <img src={XIcon} alt="Cancel" style={{ width: 24, height: 24 }} />
        </button>
        <button className="circle-action confirm" onClick={onAccept}>
          <img src={CheckIcon} alt="Confirm" style={{ width: 24, height: 24 }} />
        </button>
      </div>

      <style>{`
        .relight-viewer-overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: #000;
          z-index: 300;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          overflow: hidden;
        }

        .blurred-background {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background-size: cover;
          background-position: center;
          background-repeat: no-repeat;
          filter: blur(40px);
          transform: scale(1.1);
          opacity: 0.3;
          z-index: 0;
        }

        .blurred-background::after {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.5);
        }

        .viewer-controls {
          position: absolute;
          top: 20px;
          left: 20px;
          z-index: 301;
        }

        .icon-btn {
          width: 44px;
          height: 44px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .icon-btn:active {
          transform: scale(0.95);
          background: rgba(255, 255, 255, 0.2);
        }

        .image-container {
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          z-index: 1;
        }

        .image-container img {
          width: 100%;
          height: 100%;
          object-fit: contain;
        }

        .edit-actions {
          display: flex;
          justify-content: space-between;
          align-items: center;
          width: 100%;
          position: absolute;
          bottom: 64px;
          max-width: 300px;
          padding: 0 32px;
          z-index: 302;
          left: 50%;
          transform: translateX(-50%);
          pointer-events: auto;
        }

        .circle-action {
          display: flex;
          width: 36px;
          height: 36px;
          padding: 6px;
          justify-content: center;
          align-items: center;
          aspect-ratio: 1/1;
          border-radius: 40px;
          border: 1px solid #68AFFF;
          background: rgba(0, 0, 0, 0.40);
          box-shadow: 1px -1px 24px -2px #68AFFF inset;
          backdrop-filter: blur(2px);
          cursor: pointer;
          transition: transform 0.2s;
          color: white;
        }

        .circle-action:active {
          transform: scale(0.95);
        }
      `}</style>
    </motion.div>
  );
};

export default RelightViewer;
