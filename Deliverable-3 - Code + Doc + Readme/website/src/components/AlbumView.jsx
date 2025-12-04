import React, { useRef, useState } from 'react';
import { motion, useScroll, useTransform, AnimatePresence } from 'framer-motion';
import { ChevronLeft, MoreVertical, Download, Share2, Trash2, CheckCircle2, Circle, X, Grid3x3, Grid, List } from 'lucide-react';

const AlbumView = ({ location, onBack, onSelectPhoto, onDeletePhotos }) => {
  const scrollRef = useRef(null);
  const [activeMenuPhoto, setActiveMenuPhoto] = useState(null);

  // Grid State
  const [columns, setColumns] = useState(1); // 1 -> 3 -> 5

  // Selection Mode State
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());

  // Menu Button State
  const menuTimerRef = useRef(null);
  const isMenuLongPress = useRef(false);

  // Use images from the location prop
  const photos = location?.images?.map((img, index) => ({
    id: index,
    image: img,
    title: `${location.title} ${index + 1}`
  })) || [];

  const toggleSelection = (id) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const handleEnterSelectionMode = () => {
    setIsSelectionMode(true);
  };

  const handleCancelSelection = () => {
    setIsSelectionMode(false);
    setSelectedIds(new Set());
  };

  const handleBack = () => {
    if (isSelectionMode) {
      handleCancelSelection();
    } else {
      onBack();
    }
  };

  const handleDeleteSelected = () => {
    if (onDeletePhotos) {
      onDeletePhotos(Array.from(selectedIds));
      handleCancelSelection();
    }
  };

  const handleDeleteSingle = () => {
    if (activeMenuPhoto && onDeletePhotos) {
      onDeletePhotos([activeMenuPhoto.id]);
      setActiveMenuPhoto(null);
    }
  };

  // Menu Button Handlers
  const handleMenuDown = () => {
    isMenuLongPress.current = false;
    menuTimerRef.current = setTimeout(() => {
      isMenuLongPress.current = true;
      handleEnterSelectionMode();
    }, 500);
  };

  const handleMenuUp = () => {
    clearTimeout(menuTimerRef.current);
    if (!isMenuLongPress.current) {
      // Single tap: Cycle grid
      if (columns === 1) setColumns(3);
      else if (columns === 3) setColumns(5);
      else setColumns(1);
    }
  };

  const handleMenuLeave = () => {
    clearTimeout(menuTimerRef.current);
  };

  const getMenuIcon = () => {
    if (columns === 1) return <Grid3x3 size={20} />;
    if (columns === 3) return <Grid size={20} />;
    return <List size={20} />;
  };

  return (
    <motion.div
      layoutId={`location-${location?.id}`}
      className="album-container gradient-bg"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4, ease: [0.43, 0.13, 0.23, 0.96] }}
    >
      <header className="album-header">
        <button onClick={handleBack} className="icon-btn glass">
          {isSelectionMode ? <X size={20} /> : <ChevronLeft size={20} />}
        </button>

        <h2>
          {isSelectionMode
            ? `${selectedIds.size} Selected`
            : location?.title}
        </h2>

        {!isSelectionMode ? (
          <button
            className="icon-btn glass"
            onPointerDown={handleMenuDown}
            onPointerUp={handleMenuUp}
            onPointerLeave={handleMenuLeave}
          >
            {getMenuIcon()}
          </button>
        ) : (
          <div style={{ width: 48 }} /> // Spacer for balance
        )}
      </header>

      {/* Simplified Feed with Scroll Animations */}
      <motion.div
        className={`simple-feed ${isSelectionMode ? 'selection-mode-active' : ''}`}
        ref={scrollRef}
        layout // Enable layout animations for the container
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${columns}, 1fr)`,
          gap: columns > 1 ? '2px' : '0px',
          paddingLeft: columns > 1 ? '0' : '20px',
          paddingRight: columns > 1 ? '0' : '20px',
        }}
      >
        <AnimatePresence>
          {photos.map((photo, index) => (
            <ScrollImage
              key={photo.id}
              photo={photo}
              index={index}
              columns={columns}
              onSelect={() => {
                if (isSelectionMode) {
                  toggleSelection(photo.id);
                } else {
                  onSelectPhoto(photo);
                }
              }}
              onLongPress={() => !isSelectionMode && setActiveMenuPhoto(photo)}
              containerRef={scrollRef}
              isSelectionMode={isSelectionMode}
              isSelected={selectedIds.has(photo.id)}
            />
          ))}
        </AnimatePresence>
      </motion.div>

      {/* Bottom Action Bar for Selection Mode */}
      <AnimatePresence>
        {isSelectionMode && (
          <motion.div
            className="selection-bar glass-heavy"
            initial={{ y: 100 }}
            animate={{ y: 0 }}
            exit={{ y: 100 }}
          >
            <button className="action-btn" disabled={selectedIds.size === 0} onClick={() => console.log('Share selected')}>
              <Share2 size={20} />
              <span>Share</span>
            </button>
            <button className="action-btn delete" disabled={selectedIds.size === 0} onClick={handleDeleteSelected}>
              <Trash2 size={20} />
              <span>Delete</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Long Press Menu Overlay */}
      <AnimatePresence>
        {activeMenuPhoto && (
          <motion.div
            className="photo-menu-overlay"
            initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
            animate={{ opacity: 1, backdropFilter: "blur(8px)" }}
            exit={{ opacity: 0, backdropFilter: "blur(0px)" }}
            onClick={() => setActiveMenuPhoto(null)}
          >
            <motion.div
              className="menu-actions"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="menu-row">
                <button className="menu-btn glass-btn">
                  <Download size={24} />
                </button>
                <button className="menu-btn glass-btn" onClick={() => console.log('Share single')}>
                  <Share2 size={24} />
                </button>
              </div>
              <div className="menu-divider"></div>
              <button className="menu-btn glass-btn delete-btn" onClick={handleDeleteSingle}>
                <Trash2 size={24} />
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <style>{`
        .album-container {
          height: 100%;
          position: relative;
          background: radial-gradient(64.54% 40.32% at 90% 28.3%, #101C28 24.84%, #0D0F12 44.63%);
          overflow: hidden;
          --feed-padding-left: 0px;
          --feed-padding-right: 6px;
        }

        .album-header {
          position: absolute;
          top: 64px;
          left: 0;
          right: 0;
          padding: 0 28px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          height: 44px;
          z-index: 20;
          pointer-events: none;
        }

        @media (max-width: 450px) {
          .album-header {
            top: 50px;
          }
        }
        
        .album-header button {
          pointer-events: auto;
          width: 48px;
          height: 48px;
          border-radius: 20px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          mix-blend-mode: difference;
          color: white;
        }

        .album-header h2 {
          font-size: 16px;
          font-weight: 600;
          mix-blend-mode: difference;
          color: white;
        }

        .header-dropdown {
          position: absolute;
          top: 54px;
          right: 0;
          width: 120px;
          background: rgba(30, 30, 30, 0.9);
          border-radius: 12px;
          padding: 6px;
          border: 1px solid rgba(255, 255, 255, 0.1);
          pointer-events: auto;
        }

        .header-dropdown button {
          width: 100%;
          height: 36px;
          border: none;
          background: transparent;
          color: white;
          font-size: 14px;
          border-radius: 8px;
          mix-blend-mode: normal;
        }

        .header-dropdown button:active {
          background: rgba(255, 255, 255, 0.1);
        }

        .simple-feed {
          height: 100%;
          overflow-y: auto;
          padding: 120px var(--feed-padding-right) max(40px, env(safe-area-inset-bottom) + 20px) var(--feed-padding-left);
          -webkit-overflow-scrolling: touch;
          scroll-behavior: smooth;
          overscroll-behavior-y: contain;
          scrollbar-width: none;
          -ms-overflow-style: none;
          transition: padding 0.3s ease;
        }

        @media (max-width: 450px) {
          .simple-feed {
            padding-top: 110px;
          }
        }
        
        .simple-feed.selection-mode-active {
          padding-bottom: 100px; /* Increase padding when action bar is visible */
        }
        
        .simple-feed::-webkit-scrollbar {
          display: none;
        }

        .simple-photo {
          width: 100%;
          height: 100%;
          display: block;
          border-radius: 40px;
          cursor: pointer;
          object-fit: cover;
          background: #1c1c1e;
          -webkit-touch-callout: none;
          user-select: none;
          transition: border-radius 0.3s;
        }
        
        .simple-photo.selection-mode {
          transform: scale(0.95); /* Shrink slightly in selection mode */
        }

        .selection-indicator {
          position: absolute;
          bottom: 8px;
          right: 8px;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10;
          pointer-events: none;
        }

        .selection-bar {
          position: absolute;
          bottom: 0;
          left: 0;
          width: 100%;
          height: 80px;
          background: rgba(20, 20, 20, 0.9);
          backdrop-filter: blur(20px);
          display: flex;
          justify-content: space-around;
          align-items: center;
          padding-bottom: 20px;
          z-index: 30;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        .action-btn {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
          background: none;
          border: none;
          color: #0a84ff;
          font-size: 12px;
        }

        .action-btn.delete {
          color: #ff453a;
        }

        .action-btn:disabled {
          opacity: 0.3;
        }

        /* Menu Overlay Styles */
        .photo-menu-overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.4);
          z-index: 50;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .menu-actions {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
        }

        .menu-row {
          display: flex;
          gap: 12px;
        }

        .menu-divider {
          width: 80%;
          height: 1px;
          background: rgba(255, 255, 255, 0.2);
          margin: 4px 0;
        }

        .glass-btn {
          width: 64px;
          height: 64px;
          border-radius: 20px;
          background: rgba(255, 255, 255, 0.15);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          cursor: pointer;
          transition: transform 0.2s, background 0.2s;
        }

        .glass-btn:active {
          transform: scale(0.95);
          background: rgba(255, 255, 255, 0.25);
        }

        .delete-btn {
          background: rgba(255, 69, 58, 0.2);
          border-color: rgba(255, 69, 58, 0.3);
          color: #ff453a;
        }
      `}</style>
    </motion.div>
  );
};

// Sub-component for scroll-driven animations
const ScrollImage = ({ photo, index, columns, onSelect, onLongPress, containerRef, isSelectionMode, isSelected }) => {
  const ref = useRef(null);
  const timerRef = useRef(null);
  const isLongPress = useRef(false);

  // Only enable scroll animations in list view (columns === 1)
  const { scrollYProgress } = useScroll({
    target: ref,
    container: containerRef,
    offset: ["start end", "end start"],
    layoutEffect: false // Optimize
  });

  // Apple-like scroll effect: subtle scale and opacity changes
  // Only apply when columns === 1
  const scale = useTransform(scrollYProgress, [0, 0.5, 1], columns === 1 ? [0.95, 1, 0.95] : [1, 1, 1]);
  const opacity = useTransform(scrollYProgress, [0, 0.2, 0.8, 1], columns === 1 ? [0.8, 1, 1, 0.8] : [1, 1, 1, 1]);

  const handlePointerDown = () => {
    if (isSelectionMode) return;
    isLongPress.current = false;
    timerRef.current = setTimeout(() => {
      isLongPress.current = true;
      if (onLongPress) onLongPress();
    }, 500);
  };

  const handlePointerUp = () => {
    clearTimeout(timerRef.current);
  };

  const handlePointerLeave = () => {
    clearTimeout(timerRef.current);
  };

  const handleClick = () => {
    if (!isLongPress.current) {
      onSelect();
    }
  };

  return (
    <motion.div
      layout // Enable layout animations for items
      ref={ref}
      style={{
        scale,
        opacity,
        aspectRatio: columns === 1 ? 'auto' : '1/1', // Square in grid
        marginBottom: columns === 1 ? '8px' : '0'
      }}
      className="scroll-image-wrapper"
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerLeave}
      onClick={handleClick}
    >
      <div style={{ position: 'relative', width: '100%', height: '100%' }}>
        <motion.img
          layout // Enable layout animations for the image itself
          src={photo.image}
          alt={photo.title}
          className={`simple-photo ${isSelectionMode ? 'selection-mode' : ''}`}
          style={{
            borderRadius: columns > 1 ? '0' : '40px', // Remove radius in grid
          }}
          initial={false}
          animate={{ opacity: 1, y: 0 }}
        />
        {isSelectionMode && (
          <div className="selection-indicator">
            {isSelected ? (
              <CheckCircle2 size={24} color="#0a84ff" fill="white" />
            ) : (
              <Circle size={24} color="rgba(255,255,255,0.5)" />
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default AlbumView;
