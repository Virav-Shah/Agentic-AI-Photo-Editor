import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import LocationCard from './LocationCard';
import { Logo, NewLibraryButton } from './library/LibraryComponents';
import { CreateLibraryModal, SelectLibraryModal, RenameLibraryModal, modalStyles } from './library/LibraryModals';
import AddPhotoIcon from '../assets/icons/Screen-1/add-photo-icon.svg';

const Library = ({ onNavigate, libraries, setLibraries, onDeleteLibrary, onRenameLibrary }) => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showSelectModal, setShowSelectModal] = useState(false);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [libraryToRename, setLibraryToRename] = useState(null);
  const [pendingPhotos, setPendingPhotos] = useState([]);

  const fileInputRef = React.useRef(null);
  const scrollRef = React.useRef(null);

  const handleFileUpload = (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    const newPhotos = [];
    let processedCount = 0;

    files.forEach((file) => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          newPhotos.push(e.target.result);
          processedCount++;

          if (processedCount === files.length) {
            setPendingPhotos(newPhotos);
            setShowSelectModal(true);
            // Reset input
            if (fileInputRef.current) fileInputRef.current.value = '';
          }
        };
        reader.readAsDataURL(file);
      } else {
        processedCount++;
      }
    });
  };

  const handleCreateLibrary = (name) => {
    const newLibrary = {
      id: Date.now(),
      title: name,
      date: new Date().toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
      }),
      photos: '0',
      images: [], // Empty initially
    };
    setLibraries([newLibrary, ...libraries]);
  };

  const handleAddToLibrary = (library) => {
    const updatedLibraries = libraries.map(lib => {
      if (lib.id === library.id) {
        return {
          ...lib,
          images: [...pendingPhotos, ...lib.images],
          photos: String((lib.images?.length || 0) + pendingPhotos.length)
        };
      }
      return lib;
    });
    setLibraries(updatedLibraries);
    setPendingPhotos([]);
  };

  const handleRenameClick = (library) => {
    setLibraryToRename(library);
    setShowRenameModal(true);
  };

  const handleConfirmRename = (newName) => {
    if (libraryToRename) {
      onRenameLibrary(libraryToRename.id, newName);
      setLibraryToRename(null);
    }
  };

  return (
    <motion.div
      className="library-screen"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
    >
      {/* Logo centered at top */}
      <div className="logo-container">
        <Logo />
      </div>

      {/* Library title with new button */}
      <div className="library-header">
        <h1 className="library-title">Library</h1>
        <NewLibraryButton onClick={() => setShowCreateModal(true)} />
      </div>

      {/* Scrollable grid */}
      <div className="scroll-container" ref={scrollRef}>
        <div className="library-grid">
          {libraries.map((loc, index) => (
            <LocationCard
              key={loc.id}
              location={loc}
              index={index}
              onClick={onNavigate}
              scrollContainerRef={scrollRef}
              onDelete={() => onDeleteLibrary(loc.id)}
              onRename={() => handleRenameClick(loc)}
              onShare={() => console.log('Share', loc.title)}
            />
          ))}
        </div>
      </div>

      {/* Bottom FAB */}
      <div className="bottom-float z-[500]">
        <div className="bottom-blur"></div>
        <button className="fab-circle" onClick={() => fileInputRef.current?.click()}>
          <img src={AddPhotoIcon} alt="Add Photo" style={{ width: '56px', height: '56px' }} />
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        style={{ display: 'none' }}
        onChange={handleFileUpload}
      />

      {/* Modals */}
      <CreateLibraryModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={handleCreateLibrary}
      />

      <RenameLibraryModal
        isOpen={showRenameModal}
        onClose={() => setShowRenameModal(false)}
        onRename={handleConfirmRename}
        currentName={libraryToRename?.title || ''}
      />

      <SelectLibraryModal
        isOpen={showSelectModal}
        onClose={() => {
          setShowSelectModal(false);
          setPendingPhotos([]);
        }}
        libraries={libraries}
        onSelect={handleAddToLibrary}
      />

      <style>{`
        .library-screen {
          position: relative;
          width: 100%;
          height: 100%;
          background: radial-gradient(64.54% 40.32% at 90% 28.3%, #101C28 24.84%, #0D0F12 44.63%);
          overflow: hidden;
        }

        .logo-container {
          display: flex;
          justify-content: center;
          align-items: center;
          padding-top: 76px;
          margin-bottom: 40px;
        }

        .library-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0 22px;
          margin-bottom: 8px;
        }

        .library-title {
          font-feature-settings: 'liga' off, 'clig' off;
          font-family: "-apple-system";
          font-size: 48px;
          font-style: normal;
          font-weight: 400;
          background: linear-gradient(138deg, #D9D9D9 21.79%, #737373 71.18%);
          background-clip: text;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .scroll-container {
          position: relative;
          height: calc(100% - 204px);
          overflow-x: hidden;
          overflow-y: auto;
          scroll-behavior: smooth;
          -webkit-overflow-scrolling: touch;
        }

        .library-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px 4px;
          padding: 0 8px 68px;
        }

        .bottom-float {
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          height: 97px;
          pointer-events: none;
        }

        .bottom-blur {
          position: absolute;
          bottom: 0;
          left: 0;
          width: 393px;
          height: 69px;
          background: linear-gradient(180deg, rgba(4, 4, 4, 0.00) 0%, rgba(13, 13, 18, 1) 209.37%);
          backdrop-filter: blur(4px);
        }

        .fab-circle {
          position: absolute;
          bottom: 30px;
          right: 30px;
          width: 60px;
          height: 60px;
          pointer-events: auto;
          cursor: pointer;
          -webkit-tap-highlight-color: transparent;
          border: none;
          background: transparent;
          outline: none;
          user-select: none;
          -webkit-user-select: none;
          -moz-user-select: none;
          -ms-user-select: none;
        }

        .fab-circle img {
          user-select: none;
          -webkit-user-select: none;
          -webkit-user-drag: none;
          pointer-events: none;
        }

        .fab-circle:hover {
          transform: scale(1.05);
        }

        .fab-circle:active {
          transform: scale(0.95);
          background: transparent;
        }

        /* Hide scrollbar */
        .scroll-container::-webkit-scrollbar {
          display: none;
        }
        .scroll-container {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }

        ${modalStyles}
      `}</style>
    </motion.div>
  );
};

export default Library;
