import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ShieldCheck, Copy, Folder, MoreHorizontal, Sparkles } from 'lucide-react';
import SunMoonIcon from '../assets/icons/Screen-3/sun-moon.svg';
import BoxIcon from '../assets/icons/Screen-3/box.svg';

const FinalView = ({ image, onClose, appliedEffects = [] }) => {
  const [credentialsActive, setCredentialsActive] = useState(true);
  const [isSheetOpen, setIsSheetOpen] = useState(true);

  // Define all possible effects with their display info
  const effectsMap = {
    'relight': {
      icon: SunMoonIcon,
      label: 'Auto Relight',
      type: 'image'
    },
    'depth': {
      icon: BoxIcon,
      label: '3D Depth Effect',
      type: 'image'
    },
    'ai-edit': {
      icon: null,
      label: 'AI Edit',
      type: 'component',
      component: Sparkles
    }
  };

  const handleSave = (e) => {
    e.stopPropagation(); // Prevent toggling sheet
    const link = document.createElement('a');
    link.href = image;
    link.download = 'edited-image.png';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const toggleSheet = () => {
    setIsSheetOpen(!isSheetOpen);
  };

  return (
    <motion.div
      className="final-view"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      onClick={toggleSheet} // Tap anywhere to toggle
    >
      {/* Header */}
      <div className="header" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="close-btn">
          <X size={24} color="white" />
        </button>
        <h2>Ready To Share</h2>
        <div style={{ width: 40 }}></div> {/* Spacer */}
      </div>

      {/* Main Image */}
      <div className="image-container">
        <img src={image} alt="Final Result" className="final-image" />
      </div>

      {/* Bottom Sheet */}
      <motion.div
        className="bottom-sheet"
        initial={{ y: "100%" }}
        animate={{ y: isSheetOpen ? 0 : "85%" }} 
        transition={{ type: "spring", damping: 25, stiffness: 200 }}
        onClick={(e) => e.stopPropagation()} 
        drag="y"
        dragConstraints={{ top: 0, bottom: 300 }}
        dragElastic={0.2}
        onDragEnd={(e, { offset, velocity }) => {
          if (offset.y > 100 || velocity.y > 500) {
            setIsSheetOpen(false);
          } else {
            setIsSheetOpen(true);
          }
        }}
      >
        <div className="drag-handle" onClick={() => setIsSheetOpen(!isSheetOpen)}></div>

        {/* AI Content Credentials */}
        <div className="credentials-row">
          <div className="credentials-left">
            <ShieldCheck size={20} color="#fff" />
            <span>AI Content Credentials</span>
          </div>
          <div
            className={`toggle-switch ${credentialsActive ? 'active' : ''}`}
            onClick={() => setCredentialsActive(!credentialsActive)}
          >
            <div className="toggle-knob"></div>
          </div>
        </div>

        <div className="divider"></div>

        {/* Applied Effects Chips - Dynamic */}
        {appliedEffects.length > 0 && (
          <>
            <div className="effects-scroll">
              {appliedEffects.map((effectKey) => {
                const effect = effectsMap[effectKey];
                if (!effect) return null;

                return (
                  <div key={effectKey} className="effect-chip active">
                    {effect.type === 'image' && effect.icon && (
                      <img src={effect.icon} alt={effect.label} style={{ width: 14, height: 14 }} />
                    )}
                    {effect.type === 'component' && effect.component && (
                      <effect.component size={14} color="rgba(159, 203, 253, 1)" />
                    )}
                    <span>{effect.label}</span>
                  </div>
                );
              })}
            </div>
            <div className="divider"></div>
          </>
        )}

        {/* Action Buttons */}
        <div className="actions-row">
          <div className="action-item">
            <div className="action-circle">
              <Copy size={24} color="white" />
            </div>
            <span>Copy</span>
          </div>
          <div className="action-item">
            <div className="action-circle">
              <Folder size={24} color="white" />
            </div>
            <span>Folder</span>
          </div>
          <div className="action-item">
            <div className="action-circle">
              <MoreHorizontal size={24} color="white" />
            </div>
            <span>More</span>
          </div>
        </div>

        {/* Save Button */}
        <button className="save-btn" onClick={handleSave}>
          Save Image
        </button>
      </motion.div>

      <style>{`
        .final-view {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: #1a1a1d;
          z-index: 100;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 60px 20px 20px;
          z-index: 10;
        }

        .header h2 {
          color: white;
          font-size: 18px;
          font-weight: 600;
          margin: 0;
        }

        .close-btn {
          background: none;
          border: none;
          cursor: pointer;
          padding: 8px;
          margin-left: -8px;
        }

        .image-container {
          flex: 1;
          display: flex;
          justify-content: center;
          align-items: flex-start;
          margin-top: 10px;
        }

        .final-image {
          width: 360px;
          height: 450px;
          aspect-ratio: 4/5;
          border-radius: 16px;
          object-fit: cover;
        }

        .bottom-sheet {
          position: absolute;
          bottom: 0;
          left: -2px;
          width: 100%;
          height: 384px;
          background: linear-gradient(187deg, rgba(35, 45, 56, 0.75) 7.38%, rgba(35, 45, 56, 0.75) 36.2%);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border-top-left-radius: 42px;
          border-top-right-radius: 42px;
          border: 1px solid rgba(159, 203, 253, 0.39);
          border-bottom: none;
          padding: 12px 24px 40px;
          display: flex;
          flex-direction: column;
          gap: 20px;
          touch-action: none; /* Important for drag */
        }

        .drag-handle {
          width: 40px;
          height: 4px;
          background: rgba(255, 255, 255, 0.3);
          border-radius: 2px;
          align-self: center;
          margin-bottom: 10px;
          cursor: grab;
        }

        .credentials-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .credentials-left {
          display: flex;
          align-items: center;
          gap: 12px;
          color: white;
          font-size: 16px;
          font-weight: 500;
        }

        .toggle-switch {
          width: 44px;
          height: 24px;
          background: rgba(255, 255, 255, 0.2);
          border-radius: 12px;
          position: relative;
          cursor: pointer;
          transition: background 0.3s;
        }

        .toggle-switch.active {
          background: #68AFFF;
        }

        .toggle-knob {
          width: 20px;
          height: 20px;
          background: white;
          border-radius: 50%;
          position: absolute;
          top: 2px;
          left: 2px;
          transition: transform 0.3s;
          box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .toggle-switch.active .toggle-knob {
          transform: translateX(20px);
        }

        .divider {
          height: 1px;
          background: rgba(255, 255, 255, 0.1);
          width: 100%;
        }

        .effects-scroll {
          display: flex;
          gap: 12px;
          overflow-x: auto;
          padding-bottom: 4px;
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .effects-scroll::-webkit-scrollbar {
          display: none;
        }

        .effect-chip {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 16px 12px;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 20px;
          color: rgba(255, 255, 255, 0.6);
          font-size: 13px;
          white-space: nowrap;
        }

        .effect-chip.active {
          background: rgba(104, 175, 255, 0.15);
          border-color: #68AFFF;
          color: #fff;
        }

        .actions-row {
          display: flex;
          justify-content: space-around;
          padding: 10px 0;
        }

        .action-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
        }

        .action-circle {
          width: 64px;
          height: 64px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.1);
          display: flex;
          align-items: center;
          justify-content: center;
          border: 1px solid rgba(255, 255, 255, 0.1);
          cursor: pointer;
          transition: background 0.2s;
        }

        .action-circle:active {
          background: rgba(255, 255, 255, 0.2);
        }

        .action-item span {
          color: rgba(255, 255, 255, 0.6);
          font-size: 12px;
        }

        .save-btn {
          width: 100%;
          height: 56px;
          background: rgba(30, 30, 35, 0.6);
          border: 1px solid #68AFFF;
          border-radius: 16px;
          color: #68AFFF;
          font-size: 18px;
          font-weight: 600;
          cursor: pointer;
          box-shadow: 0 0 15px rgba(104, 175, 255, 0.15), inset 0 0 20px rgba(104, 175, 255, 0.1);
          transition: all 0.2s;
          margin-top: auto;
        }

        .save-btn:active {
          transform: scale(0.98);
          background: rgba(104, 175, 255, 0.1);
        }
      `}</style>
    </motion.div>
  );
};

export default FinalView;
