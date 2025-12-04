import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const DetailHeader = ({ title, onBack, showNext, onNext }) => {
  return (
    <header className="detail-header">
      <button onClick={onBack} className="back-btn">
        <ChevronLeft size={24} />
      </button>
      <h2>{title || "Detail View"}</h2>

      {showNext ? (
        <button onClick={onNext} className="next-btn">
          <ChevronRight size={24} />
        </button>
      ) : (
        <div style={{ width: 48 }} /> /* Spacer for centering */
      )}

      <style>{`
        .detail-header {
          position: absolute;
          top: 64px;
          left: 0;
          right: 0;
          padding: 0 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          height: 44px;
          z-index: 30;
          pointer-events: none;
        }

        .back-btn, .next-btn {
          pointer-events: auto;
          width: 48px;
          height: 48px;
          border-radius: 20px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          background: transparent;
          mix-blend-mode: difference;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          cursor: pointer;
          transition: transform 0.2s;
        }

        .back-btn:active, .next-btn:active {
          transform: scale(0.95);
        }

        .detail-header h2 {
          font-size: 16px;
          font-weight: 600;
          color: white;
          text-align: center;
          flex: 1;
          pointer-events: none;
          mix-blend-mode: difference;
        }

        @media (max-width: 450px) {
          .detail-header {
            top: 50px;
          }
        }
      `}</style>
    </header>
  );
};

export default DetailHeader;
