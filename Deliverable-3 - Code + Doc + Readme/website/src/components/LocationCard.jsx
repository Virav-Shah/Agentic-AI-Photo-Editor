import React, { useRef, useState, useEffect } from 'react';
import { motion, useScroll, useTransform, AnimatePresence } from 'framer-motion';
import { Trash2, Share2, Edit2 } from 'lucide-react';

const LocationCard = ({ location, onClick, index, scrollContainerRef, onDelete, onRename, onShare }) => {
  const cardRef = useRef(null);
  const [showMenu, setShowMenu] = useState(false);
  const longPressTimer = useRef(null);
  const isLongPress = useRef(false);

  const { scrollYProgress } = useScroll({
    target: cardRef,
    container: scrollContainerRef,
    offset: ["start end", "end start"]
  });

  const scale = useTransform(scrollYProgress, [0, 0.45, 0.55, 1], [0.85, 1, 1, 0.85]);
  const opacity = useTransform(scrollYProgress, [0, 0.45, 0.55, 1], [0.6, 1, 1, 0.6]);

  // Handle clicking outside to close menu
  useEffect(() => {
    if (!showMenu) return;

    const handleClickOutside = (event) => {
      if (cardRef.current && !cardRef.current.contains(event.target)) {
        setShowMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [showMenu]);

  const handlePointerDown = () => {
    isLongPress.current = false;
    longPressTimer.current = setTimeout(() => {
      isLongPress.current = true;
      setShowMenu(true);
    }, 500); // 500ms threshold for long press
  };

  const handlePointerUp = () => {
    clearTimeout(longPressTimer.current);
  };

  const handlePointerLeave = () => {
    clearTimeout(longPressTimer.current);
  };

  const handleClick = () => {
    if (isLongPress.current) {
      return;
    }
    if (showMenu) {
      setShowMenu(false);
      return;
    }
    onClick(location);
  };

  const handleMenuAction = (e, action) => {
    e.stopPropagation();
    setShowMenu(false);

    if (action === 'delete' && onDelete) onDelete();
    if (action === 'rename' && onRename) onRename();
    if (action === 'share' && onShare) onShare();
  };

  return (
    <motion.div
      layoutId={`location-${location.id}`}
      ref={cardRef}
      className="location-card"
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerLeave}
      onClick={handleClick}
      style={{ scale, opacity }}
      whileHover={{ y: -8, transition: { duration: 0.4, ease: "easeInOut" } }}
      whileTap={{ scale: 0.95, transition: { duration: 0.2, ease: "easeInOut" } }}
    >
      <div className="image-stack">
        {location.images?.length > 0 || location.folder ? (
          <>
            <img src={location.images?.[3] || (location.folder ? `${location.folder}/4.png` : null)} alt="" className="stack-img img-4" style={{ opacity: location.images?.[3] || location.folder ? 1 : 0 }} />
            <img src={location.images?.[2] || (location.folder ? `${location.folder}/3.png` : null)} alt="" className="stack-img img-3" style={{ opacity: location.images?.[2] || location.folder ? 1 : 0 }} />
            <img src={location.images?.[1] || (location.folder ? `${location.folder}/2.png` : null)} alt="" className="stack-img img-2" style={{ opacity: location.images?.[1] || location.folder ? 1 : 0 }} />
            <div className="img-1-wrapper">
              <img src={location.images?.[0] || (location.folder ? `${location.folder}/1.png` : null)} alt={location.title} className="stack-img img-1" />
              <div className="gradient-overlay"></div>
            </div>
          </>
        ) : (
          <div className="img-1-wrapper">
            <div className="stack-img img-1 placeholder-stack">
              <div className="placeholder-content">
                <span>Empty</span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="card-info">
        <h3 className="location-title">{location.title}</h3>
        <div className="card-meta">
          <span className="date">{location.date}</span>
          <span className="dot"></span>
          <span className="count">{location.photos} Photos</span>
        </div>
      </div>

      <AnimatePresence>
        {showMenu && (
          <motion.div
            className="glass-menu-overlay"
            initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
            animate={{ opacity: 1, backdropFilter: "blur(12px)" }}
            exit={{ opacity: 0, backdropFilter: "blur(0px)" }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
          >
            <div className="menu-buttons">
              <motion.button
                className="menu-btn delete"
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.1, duration: 0.4, ease: "easeOut" }}
                onClick={(e) => handleMenuAction(e, 'delete')}
              >
                <Trash2 size={18} />
                <span>Delete</span>
              </motion.button>

              <motion.button
                className="menu-btn share"
                initial={{ x: 20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.15, duration: 0.4, ease: "easeOut" }}
                onClick={(e) => handleMenuAction(e, 'share')}
              >
                <Share2 size={18} />
                <span>Share</span>
              </motion.button>

              <motion.button
                className="menu-btn rename"
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.2, duration: 0.4, ease: "easeOut" }}
                onClick={(e) => handleMenuAction(e, 'rename')}
              >
                <Edit2 size={18} />
                <span>Rename</span>
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <style>{`
        .location-card {
          width: 186px;
          height: 189px;
          border-radius: 24px;
          overflow: hidden;
          background: #0E1621;
          position: relative;
          cursor: pointer;
          box-shadow: 0 4px 20px rgba(0,0,0,0.2);
          transition: box-shadow 0.3s ease;
          user-select: none; /* Prevent text selection during long press */
          -webkit-user-select: none;
        }

        .location-card:hover {
          box-shadow: 0 12px 30px rgba(0,0,0,0.4);
        }

        .image-stack {
          position: relative;
          width: 100%;
          height: 140px;
          display: flex;
          align-items: center;
          justify-content: center;
          perspective: 250px;
          perspective-origin: center center;
        }

        .stack-img {
          position: absolute;
          width: 160px;
          height: 100px;
          object-fit: cover;
          border-radius: 8px;
          left: 50%;
          transform-origin: center center;
          transform: translateX(-50%) rotateX(-12deg);
          transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
        }

        /* Fan out animation on hover */
        .location-card:hover .img-4 {
          top: 6px;
          transform: translateX(-50%) rotateX(-8deg) scale(0.9);
          filter: blur(0px);
        }

        .location-card:hover .img-3 {
          top: 14px;
          transform: translateX(-50%) rotateX(-10deg) scale(0.95);
          filter: blur(0px);
        }

        .location-card:hover .img-2 {
          top: 24px;
          transform: translateX(-50%) rotateX(-11deg) scale(0.98);
          filter: blur(0px);
        }

        .img-4 {
          top: 14px;
          z-index: 1;
          width: 128px;
          height: 88px;
          filter: blur(0.5px);
        }

        .img-3 {
          top: 18px;
          z-index: 2;
          width: 138px;
          height: 93px;
          filter: blur(0.5px);
        }

        .img-2 {
          top: 24px;
          z-index: 3;
          width: 150px;
          height: 106px;
          filter: blur(0.5px);
        }

        .img-1-wrapper {
          position: absolute;
          top: 30px;
          left: 50%;
          transform: translateX(-50%) rotateX(-12deg);
          transform-origin: center center;
          z-index: 4;
          width: 161px;
          height: 101px;
          transition: transform 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
        }

        .location-card:hover .img-1-wrapper {
             transform: translateX(-50%) rotateX(0deg) scale(1.02);
        }

        .img-1 {
          width: 100%;
          height: 100%;
          position: relative;
          top: 0;
          left: 0;
          transform: none;
          border-radius: 8px;
        }

        .gradient-overlay {
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          height: 60%;
          background: linear-gradient(to top, rgba(14, 22, 33, 1.0) 0%, rgba(14, 22, 33, 0.5) 30%, transparent 100%);
          pointer-events: none;
          border-radius: 0px;
        }

        .card-info {
          position: absolute;
          left: 18px;
          bottom: 17px;
          right: 14px;
          transition: transform 0.3s ease;
        }

        .location-card:hover .card-info {
          transform: translateY(-2px);
        }

        .location-title {
          font-family: 'SF Pro', -apple-system, sans-serif;
          font-weight: 600;
          font-size: 16px;
          line-height: 19px;
          color: #d9d9d9;
          margin: 0 0 4px 0;
        }

        .card-meta {
          display: flex;
          align-items: center;
          gap: 5px;
          font-family: 'SF Pro', -apple-system, sans-serif;
          font-weight: 400;
          font-size: 12px;
          line-height: 19px;
          color: #8e8e93;
        }

        .card-meta .date,
        .card-meta .count {
          white-space: nowrap;
        }

        .card-meta .dot {
          width: 3px;
          height: 3px;
          border-radius: 50%;
          background: #8e8e93;
          flex-shrink: 0;
          align-self: center;
        }

        /* Glass Menu Styles */
        .glass-menu-overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(10, 10, 15, 0.65);
          z-index: 20;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .menu-buttons {
          display: flex;
          flex-direction: column;
          gap: 12px;
          width: 80%;
        }

        .menu-btn {
          display: flex;
          align-items: center;
          gap: 10px;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.1);
          padding: 10px 16px;
          border-radius: 12px;
          color: white;
          font-family: 'SF Pro', sans-serif;
          font-size: 14px;
          cursor: pointer;
          backdrop-filter: blur(4px);
          transition: background 0.2s;
        }

        .menu-btn:hover {
          background: rgba(255, 255, 255, 0.2);
        }

        .menu-btn.delete {
          color: #ff453a;
          background: rgba(255, 69, 58, 0.15);
        }
        
        .menu-btn.delete:hover {
          background: rgba(255, 69, 58, 0.25);
        }

        .placeholder-stack {
          background: rgba(255, 255, 255, 0.05);
          border: 1px dashed rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          height: 100%;
          border-radius: 8px;
        }

        .placeholder-content {
          color: rgba(255, 255, 255, 0.3);
          font-size: 14px;
          font-weight: 500;
        }
      `}</style>
    </motion.div>
  );
};

export default LocationCard;
