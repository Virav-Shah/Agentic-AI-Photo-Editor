import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, FolderPlus, ImagePlus } from 'lucide-react';

export const CreateLibraryModal = ({ isOpen, onClose, onCreate }) => {
  const [libraryName, setLibraryName] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (libraryName.trim()) {
      onCreate(libraryName.trim());
      setLibraryName('');
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="modal-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="modal-content glass-heavy"
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
          >
            <div className="modal-header">
              <h3>New Library</h3>
              <button onClick={onClose} className="close-btn">
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="modal-form">
              <div className="input-group">
                <FolderPlus size={20} className="input-icon" />
                <input
                  type="text"
                  placeholder="Library Name"
                  value={libraryName}
                  onChange={(e) => setLibraryName(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="modal-actions">
                <button type="button" onClick={onClose} className="cancel-btn">
                  Cancel
                </button>
                <button type="submit" className="create-btn" disabled={!libraryName.trim()}>
                  Create
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export const SelectLibraryModal = ({ isOpen, onClose, libraries, onSelect }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="modal-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="modal-content glass-heavy"
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
          >
            <div className="modal-header">
              <h3>Add to Library</h3>
              <button onClick={onClose} className="close-btn">
                <X size={20} />
              </button>
            </div>

            <div className="library-list">
              {libraries.map((lib) => (
                <button
                  key={lib.id}
                  className="library-item"
                  onClick={() => {
                    onSelect(lib);
                    onClose();
                  }}
                >
                  <div className="library-info">
                    <span className="library-name">{lib.title}</span>
                    <span className="library-count">{lib.images?.length || 0} photos</span>
                  </div>
                  <ImagePlus size={20} className="add-icon" />
                </button>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export const RenameLibraryModal = ({ isOpen, onClose, onRename, currentName }) => {
  const [libraryName, setLibraryName] = useState(currentName);

  // Update local state when currentName prop changes
  React.useEffect(() => {
    setLibraryName(currentName);
  }, [currentName]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (libraryName.trim()) {
      onRename(libraryName.trim());
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="modal-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="modal-content glass-heavy"
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
          >
            <div className="modal-header">
              <h3>Rename Library</h3>
              <button onClick={onClose} className="close-btn">
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="modal-form">
              <div className="input-group">
                <FolderPlus size={20} className="input-icon" />
                <input
                  type="text"
                  placeholder="Library Name"
                  value={libraryName}
                  onChange={(e) => setLibraryName(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="modal-actions">
                <button type="button" onClick={onClose} className="cancel-btn">
                  Cancel
                </button>
                <button type="submit" className="create-btn" disabled={!libraryName.trim()}>
                  Save
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

// Shared Styles
export const modalStyles = `
  .modal-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(8px);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }

  .modal-content {
    width: 100%;
    max-width: 320px;
    background: rgba(30, 30, 30, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 24px;
    padding: 24px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }

  .modal-header h3 {
    font-size: 20px;
    font-weight: 600;
    color: white;
    margin: 0;
  }

  .close-btn {
    background: rgba(255, 255, 255, 0.1);
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

  .modal-form {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .input-group {
    position: relative;
    display: flex;
    align-items: center;
  }

  .input-icon {
    position: absolute;
    left: 16px;
    color: rgba(255, 255, 255, 0.5);
  }

  .input-group input {
    width: 100%;
    height: 50px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 0 16px 0 48px;
    color: white;
    font-size: 16px;
    outline: none;
  }

  .input-group input:focus {
    border-color: #0a84ff;
  }

  .modal-actions {
    display: flex;
    gap: 12px;
  }

  .cancel-btn, .create-btn {
    flex: 1;
    height: 44px;
    border-radius: 12px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    border: none;
  }

  .cancel-btn {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }

  .create-btn {
    background: #0a84ff;
    color: white;
  }

  .create-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .library-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 300px;
    overflow-y: auto;
  }

  .library-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
  }

  .library-item:hover {
    background: rgba(255, 255, 255, 0.1);
  }

  .library-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .library-name {
    color: white;
    font-size: 16px;
    font-weight: 500;
  }

  .library-count {
    color: rgba(255, 255, 255, 0.5);
    font-size: 13px;
  }

  .add-icon {
    color: #0a84ff;
    opacity: 0;
    transition: opacity 0.2s;
  }

  .library-item:hover .add-icon {
    opacity: 1;
  }
`;
