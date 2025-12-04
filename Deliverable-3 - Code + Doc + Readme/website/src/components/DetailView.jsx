import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ShareModal from './ShareModal';
import ParallaxViewer from './ParallaxViewer';
import DetailHeader from './detail-view/DetailHeader';
import ImageDisplay from './detail-view/ImageDisplay';
import AutoRelightTool from './detail-view/AutoRelightTool';
import DepthTool from './detail-view/DepthTool';
import VoiceDrawer from './detail-view/VoiceDrawer';
import RelightViewer from './RelightViewer';
import FinalView from './FinalView';
import { ENDPOINTS } from '../config';
import { saveImageState, getImageState } from '../utils/stateStore';

const DetailView = ({ location, photo, onBack }) => {
  // Unique ID for the current image
  const imageId = photo?.id || location?.id || 'default';

  // Initialize state from memory store if available
  const savedState = getImageState(imageId) || {};

  const [showShare, setShowShare] = useState(false);
  const [activeTool, setActiveTool] = useState(null);
  const [relightValue, setRelightValue] = useState(savedState.relightValue || 50);
  const [depthValue, setDepthValue] = useState(30);
  const [showVoiceDrawer, setShowVoiceDrawer] = useState(false);
  const [depthData, setDepthData] = useState(savedState.depthData || null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedImage, setProcessedImage] = useState(savedState.processedImage || null);
  const [previousImage, setPreviousImage] = useState(null); // For reject functionality
  const [showParallax, setShowParallax] = useState(false); // For viewing parallax after depth is applied
  const [hasEdited, setHasEdited] = useState(savedState.hasEdited || false);
  const [showRelightViewer, setShowRelightViewer] = useState(false);
  const [showFinalView, setShowFinalView] = useState(false);



  // Track applied effects for final view
  const [appliedEffects, setAppliedEffects] = useState(savedState.appliedEffects || []);

  const [agentMessage, setAgentMessage] = useState(null);
  const [lastOperationSuccess, setLastOperationSuccess] = useState(false);

  // Agent State
  const [agentState, setAgentState] = useState(savedState.agentState || null);
  const [lastAgentState, setLastAgentState] = useState(null); // For undo
  const [aiMode, setAiMode] = useState('fast'); // 'thinking' | 'fast'

  // Voice Recording State
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = React.useRef(null);
  const chunksRef = React.useRef([]);



  // History State
  const [history, setHistory] = useState(savedState.history || []);

  // Save state to memory store whenever relevant data changes
  React.useEffect(() => {
    saveImageState(imageId, {
      history,
      processedImage,
      appliedEffects,
      agentState,
      depthData,
      hasEdited,
      relightValue
    });
  }, [imageId, history, processedImage, appliedEffects, agentState, depthData, hasEdited, relightValue]);

  const addToHistory = (item) => {
    setHistory(prev => [...prev, { ...item, id: Date.now(), timestamp: Date.now() }]);
  };

  const handleRestore = (historyItem) => {
    if (historyItem.depthData) {
      // Restore depth effect
      setDepthData(historyItem.depthData);
      setActiveTool('depth');
      setHasEdited(true);
    } else if (historyItem.image) {
      // Restore regular image
      setProcessedImage(historyItem.image);
      setHasEdited(true);
    }
  };

  const handleSave = () => {
    setShowShare(true);
  };

  const handleNext = () => {
    setShowFinalView(true);
  };

  const handleImageClick = () => {
    // If depth data exists and no tool is active, show parallax viewer
    if (depthData && !activeTool) {
      setShowParallax(true);
    }
  };

  const toggleRelight = () => {
    if (activeTool === 'relight') {
      setActiveTool(null);
      setPreviousImage(null); // Clear if toggling off
      return;
    }

    // Just open the tool, don't apply effect yet
    setActiveTool('relight');
    // Store original image BEFORE any edits
    setPreviousImage(processedImage || photo?.image || location?.image);
  };

  const toggleDepth = () => {
    if (activeTool === 'depth') {
      setActiveTool(null);
      return;
    }

    // Just open the tool, don't apply effect yet
    setActiveTool('depth');
  };

  const handleRelight = async () => {
    setIsProcessing(true);
    try {
      // Use previousImage (original) as source to prevent accumulation of effects
      const currentImage = previousImage || processedImage || photo?.image || location?.image;


      // Always convert to PNG to ensure backend compatibility
      const img = new Image();
      img.crossOrigin = 'anonymous';

      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = currentImage;
      });

      // Draw to canvas and convert to PNG with compression
      const canvas = document.createElement('canvas');

      // Auto-resize large images to prevent fetch failures
      let width = img.width;
      let height = img.height;
      const maxDim = 2048;

      if (width > maxDim || height > maxDim) {
        if (width > height) {
          height = (height / width) * maxDim;
          width = maxDim;
        } else {
          width = (width / height) * maxDim;
          height = maxDim;
        }
      }

      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, width, height);

      // Compress image to stay under 5MB
      let quality = 0.9;
      let dataUrl;
      let base64Data;

      do {
        dataUrl = canvas.toDataURL('image/jpeg', quality);
        base64Data = dataUrl.split(',')[1];

        const sizeInBytes = (base64Data.length * 3) / 4;

        if (sizeInBytes < 5 * 1024 * 1024) { // 5MB limit
          break;
        }

        quality -= 0.1;
      } while (quality > 0.1);

      // Convert final dataUrl to Blob for file upload
      const fetchRes = await fetch(dataUrl);
      const blob = await fetchRes.blob();

      // Map slider (0-100) to time_of_day (0-100)
      const timeOfDay = relightValue;

      const formData = new FormData();
      formData.append('image', blob, 'image.jpg');
      formData.append('time_of_day', timeOfDay);

      // Call the external API
      const apiResponse = await fetch(ENDPOINTS.THEME_CHANGE, {
        method: 'POST',
        body: formData
      });

      if (!apiResponse.ok) {
        const errorData = await apiResponse.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to apply relighting');
      }

      // Parse JSON response
      const data = await apiResponse.json();

      if (data.success && data.transformed_image) {
        // Apply directly to processedImage (no preview)
        const imageUrl = `data:image/png;base64,${data.transformed_image}`;
        setProcessedImage(imageUrl);
        setHasEdited(true);
      } else {
        throw new Error('Invalid response from server');
      }

    } catch (error) {
      console.error('Error applying relight:', error);
      alert(`Failed to apply auto relight: ${error.message}`);
      // Restore previous image on error
      if (previousImage) {
        setProcessedImage(previousImage);
      }
      setActiveTool(null);
    } finally {
      setIsProcessing(false);
    }
  };

  const generateDepthMap = async () => {
    setIsProcessing(true);
    try {
      const currentImage = processedImage || photo?.image || location?.image;

      // Convert to PNG using canvas (same as relight)
      const img = new Image();
      img.crossOrigin = 'anonymous';

      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = currentImage;
      });

      const canvas = document.createElement('canvas');

      // Auto-resize large images to prevent fetch failures
      let width = img.width;
      let height = img.height;
      const maxDim = 2048;

      if (width > maxDim || height > maxDim) {
        if (width > height) {
          height = (height / width) * maxDim;
          width = maxDim;
        } else {
          width = (width / height) * maxDim;
          height = maxDim;
        }
      }

      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, width, height);

      // Convert to Blob
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.95));

      // Create form data
      const formData = new FormData();
      formData.append('image', blob, 'image.jpg');
      formData.append('output_format', 'json'); // Request JSON format for depth data
      formData.append('depth_scale', '20.0'); // Match parallax_app default

      // Call the API (use network IP for cross-device access)
      const apiResponse = await fetch(ENDPOINTS.GENERATE_DEPTH, {
        method: 'POST',
        body: formData
      });

      if (!apiResponse.ok) {
        const errorText = await apiResponse.text();
        let errorMessage = 'Failed to generate depth map';
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const data = await apiResponse.json();

      if (data.success) {
        setDepthData(data);
        // Keep depth tool open, don't show parallax viewer
        setHasEdited(true);
      } else {
        throw new Error(data.error || 'Unknown error');
      }
    } catch (error) {
      console.error('Error generating depth map:', error);
      alert(`Failed to generate 3D depth map: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const recordingStartTimeRef = useRef(null);
  const abortControllerRef = useRef(null);

  const cancelRecording = () => {
    console.log('🛑 Cancelling recording/processing');

    // Stop recording if active
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }

    // Abort any ongoing backend request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Reset states
    setIsRecording(false);
    setIsProcessing(false);
    setAgentMessage(null);
    recordingStartTimeRef.current = null;

    console.log('✅ Cancelled successfully');
  };

  const startRecording = async () => {
    console.log('🎙️ startRecording called');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('✅ Got media stream');
      mediaRecorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];
      recordingStartTimeRef.current = Date.now();

      mediaRecorderRef.current.ondataavailable = (e) => {
        console.log('📦 Data available, size:', e.data.size);
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        console.log('🛑 MediaRecorder onstop triggered');
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        console.log('🎵 Audio blob created, size:', audioBlob.size);
        await handleVoiceCommand(audioBlob, aiMode);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current.start();
      console.log('▶️ MediaRecorder started, setting isRecording=true');
      setIsRecording(true);
    } catch (err) {
      console.error('Error accessing microphone:', err);
      alert('Could not access microphone. Please ensure permissions are granted.');
    }
  };

  const stopRecording = () => {
    console.log('⏹️ stopRecording called, mediaRecorder state:', mediaRecorderRef.current?.state);

    // Check minimum recording duration (200ms)
    const recordingDuration = Date.now() - (recordingStartTimeRef.current || 0);
    if (recordingDuration < 200) {
      console.log('⚠️ Recording too short, minimum 200ms required. Duration:', recordingDuration);
      return;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      console.log('⏹️ Stopping MediaRecorder');
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      recordingStartTimeRef.current = null;
    } else {
      console.log('⚠️ Cannot stop - recorder not in recording state');
    }
  };

  const toggleRecording = () => {
    console.log('🔄 toggleRecording called, mediaRecorder state:', mediaRecorderRef.current?.state, 'isProcessing:', isProcessing);

    // If processing, cancel everything
    if (isProcessing || isRecording) {
      cancelRecording();
      return;
    }

    // Otherwise start recording
    startRecording();
  };

  const handleVoiceCommand = async (commandOrBlob, mode = 'thinking') => {
    setIsProcessing(true);
    try {
      const currentImage = processedImage || photo?.image || location?.image;

      // Convert to canvas and compress (same as relight)
      const img = new Image();
      img.crossOrigin = 'anonymous';

      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = currentImage;
      });

      const canvas = document.createElement('canvas');

      // Auto-resize large images to prevent fetch failures
      let width = img.width;
      let height = img.height;
      const maxDim = 2048;

      if (width > maxDim || height > maxDim) {
        if (width > height) {
          height = (height / width) * maxDim;
          width = maxDim;
        } else {
          width = (width / height) * maxDim;
          height = maxDim;
        }
      }

      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, width, height);

      // Compress image to stay under 1MB
      let quality = 0.9;
      let dataUrl;
      let base64Data;

      do {
        dataUrl = canvas.toDataURL('image/jpeg', quality);
        base64Data = dataUrl.split(',')[1];

        const sizeInBytes = (base64Data.length * 3) / 4;

        if (sizeInBytes < 5 * 1024 * 1024) { // 5MB limit
          break;
        }

        quality -= 0.1;
      } while (quality > 0.1);

      const formData = new FormData();
      formData.append('image', base64Data);

      let endpoint = ENDPOINTS.AGENT_RUN;

      if (commandOrBlob instanceof Blob) {
        // Voice command (Audio Blob)
        formData.append('audio', commandOrBlob, 'command.webm');
        formData.append('mode', mode); // Pass mode to backend
        endpoint = ENDPOINTS.AGENT_VOICE;
      } else {
        // Text command (String)
        formData.append('query', commandOrBlob);

        if (mode === 'fast') {
          endpoint = ENDPOINTS.QUICK_EDIT_EXECUTE;
        } else if (agentState) {
          // Only send existing_state for text commands in thinking mode
          formData.append('existing_state', JSON.stringify(agentState));
        }

        // Add user query to history
        addToHistory({
          type: 'user',
          content: commandOrBlob,
          mode: mode
        });
      }

      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      const apiResponse = await fetch(endpoint, {
        method: 'POST',
        body: formData,
        signal: abortControllerRef.current.signal
      });

      if (!apiResponse.ok) throw new Error('Agent execution failed');

      const data = await apiResponse.json();

      if (data.success) {
        // Handle parallax/3D depth effect
        if (data.html_output || (data.subject_layer && data.foreground_depth)) {
          console.log('Received depth data from voice:', data);
          setDepthData(data);
          setShowParallax(true);
          setHasEdited(true);
          setAgentMessage('3D depth effect applied!');
        }
        // Handle regular image result
        else if (data.result_image) {
          setLastAgentState(agentState);
          // Apply directly to processedImage
          const imageUrl = `data:image/png;base64,${data.result_image}`;
          setPreviousImage(processedImage || photo?.image || location?.image);
          setProcessedImage(imageUrl);
          setHasEdited(true);
        }

        // Update state if available (Thinking mode)
        if (data.state) {
          setAgentState(data.state);
        }

        // Helper to clean and truncate message
        const cleanMessage = (msg) => {
          if (!msg) return mode === 'fast' ? 'Quick edit applied!' : 'Done!';

          // Remove JSON-like formatting
          let cleaned = msg.replace(/[{}'"]/g, '');

          // Take only first sentence or first 50 characters
          const firstSentence = cleaned.split(/[.!?]/)[0];
          const truncated = firstSentence.length > 50
            ? firstSentence.substring(0, 47) + '...'
            : firstSentence;

          return truncated.trim();
        };

        // Show explanation in voice bar
        if (!data.html_output && !data.subject_layer) {
          const message = cleanMessage(data.explain);
          setAgentMessage(message);
        }

        // Clear message after 5 seconds
        setTimeout(() => setAgentMessage(null), 5000);

        // Add agent result to history
        if (data.result_image) {
          addToHistory({
            type: 'agent',
            content: data.explain || 'Applied effect',
            image: `data:image/png;base64,${data.result_image}`,
            mode: mode
          });
        } else if (data.subject_layer) {
          // Add depth effect to history
          addToHistory({
            type: 'agent',
            content: 'Applied 3D Depth Effect',
            image: `data:image/png;base64,${data.subject_layer}`, // Use subject layer as preview
            mode: mode,
            depthData: data // Store full depth data for restoration
          });
        }

      } else {
        throw new Error(data.status || 'Unknown error');
      }

      // Mark operation as successful
      setLastOperationSuccess(true);

    } catch (error) {
      console.error('Error running agent:', error);
      setAgentMessage('Failed to execute command.');
      setLastOperationSuccess(false);
      setTimeout(() => setAgentMessage(null), 3000);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleUndo = async () => {
    // Fast mode: simple image revert
    if (previousImage && !agentState) {
      console.log('🔄 Undoing (Fast mode): Reverting to previous image');
      setProcessedImage(previousImage);
      setPreviousImage(null);
      setAgentMessage('Undone!');
      setTimeout(() => setAgentMessage(null), 2000);
      return;
    }

    // Thinking mode: use agent undo endpoint
    if (!agentState) return;
    setIsProcessing(true);
    try {
      const formData = new FormData();
      formData.append('state', JSON.stringify(agentState));

      const apiResponse = await fetch(ENDPOINTS.AGENT_UNDO, {
        method: 'POST',
        body: formData
      });

      if (!apiResponse.ok) throw new Error('Undo failed');

      const data = await apiResponse.json();

      if (data.success) {
        if (data.current_image) {
          setProcessedImage(`data:image/png;base64,${data.current_image}`);
        }
        setAgentState(data.state);
        setAgentMessage('Undone!');
        setTimeout(() => setAgentMessage(null), 2000);
      }

    } catch (error) {
      console.error('Error undoing:', error);
      alert('Failed to undo last action.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleAcceptRelight = async () => {
    // Apply effect and show preview
    setPreviousImage(processedImage || photo?.image || location?.image);
    await handleRelight();

    // Show fullscreen preview after effect is applied
    setShowRelightViewer(true);
  };

  const handleRelightPreviewAccept = () => {
    // User accepted the changes - keep them and return to slider

    // Track that relight was applied
    if (!appliedEffects.includes('relight')) {
      setAppliedEffects([...appliedEffects, 'relight']);
    }

    // Add to history
    addToHistory({
      type: 'user',
      content: 'Applied Auto Relight',
      image: processedImage,
      mode: 'manual'
    });

    // Close preview but KEEP tool open (return to EditingToolBase)
    setShowRelightViewer(false);

    // Clear previous image so that "Cross" in slider acts as "Close" (Preserve)
    // instead of "Undo"
    setPreviousImage(null);

    // Clear depth data since the image has changed
    setDepthData(null);
  };

  const handleRelightPreviewReject = () => {
    // User rejected the changes - undo and return to slider

    // Restore previous image
    if (previousImage) {
      setProcessedImage(previousImage);
    }

    // Close preview but KEEP tool open (return to EditingToolBase)
    setShowRelightViewer(false);

    // Do NOT clear previousImage, so user can still Cancel/Undo from slider
  };

  const handleRejectRelight = () => {
    // User clicked X in editing tool - just close without applying
    setActiveTool(null);
    setPreviousImage(null);
  };



  const handleAcceptDepth = async () => {
    // Apply depth effect and show preview
    await generateDepthMap();

    // Show fullscreen preview after effect is applied
    setShowParallax(true);
  };

  const handleDepthPreviewAccept = () => {
    // User accepted the changes - keep them and return to slider

    // Track that 3D depth was applied
    if (!appliedEffects.includes('depth')) {
      setAppliedEffects([...appliedEffects, 'depth']);
    }

    // Add to history
    addToHistory({
      type: 'user',
      content: 'Applied 3D Depth Effect',
      image: processedImage || photo?.image || location?.image,
      mode: 'manual',
      depthData: depthData
    });

    // Close preview and tool
    setShowParallax(false);
    setActiveTool(null);

    // Open ShareModal to save as video/GIF
    setShowShare(true);
  };

  const handleDepthPreviewReject = () => {
    // User rejected the changes - undo and return to slider

    // Clear depth data
    setDepthData(null);

    // Close preview but KEEP tool open
    setShowParallax(false);
  };

  const handleRejectDepth = () => {
    // Close tool and discard changes
    setActiveTool(null);
    setDepthData(null);
  };

  // Use photo if available, otherwise fallback to location
  const displayImage = processedImage || photo?.image || location?.image;
  const displayTitle = photo?.title || location?.title;

  return (
    <motion.div
      className="detail-container gradient-bg"
      initial={{ opacity: 0, x: 30 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 30 }}
      transition={{ duration: 0.5, ease: "easeInOut" }}
    >
      <DetailHeader
        title={displayTitle}
        onBack={onBack}
        showNext={true}
        onNext={handleNext}
      />

      <ImageDisplay
        image={displayImage}
        title={displayTitle}
        id={photo?.id || location?.id}
        activeTool={activeTool}
        onToggleRelight={toggleRelight}
        onToggleDepth={toggleDepth}
        onOpenVoice={() => setShowVoiceDrawer(true)}
        isRecording={isRecording}
        onToggleRecording={toggleRecording}
        isProcessing={isProcessing}
        agentMessage={agentMessage}
        onImageClick={handleImageClick}
        onUndo={handleUndo}
        canUndo={!!(previousImage || agentState) && lastOperationSuccess}
      >
        <AutoRelightTool
          active={activeTool === 'relight'}
          value={relightValue}
          onChange={setRelightValue}
          onClose={handleRejectRelight}
          onApply={handleAcceptRelight}
          isProcessing={isProcessing}
          image={displayImage}
          imageTitle={displayTitle}
          id={photo?.id || location?.id}
          onOpenViewer={() => setShowRelightViewer(true)}
        />
        <DepthTool
          active={activeTool === 'depth'}
          value={depthValue}
          onChange={setDepthValue}
          onClose={handleRejectDepth}
          onApply={handleAcceptDepth}
          isProcessing={isProcessing}
          image={displayImage}
          imageTitle={displayTitle}
          id={photo?.id || location?.id}
          depthData={depthData}
        />


      </ImageDisplay>

      {/* Parallax Viewer - Shows when user taps image after depth is applied */}
      <AnimatePresence>
        {showParallax && depthData && (
          <ParallaxViewer
            depthData={depthData}
            onClose={handleDepthPreviewReject}
            onAccept={handleDepthPreviewAccept}
            onReject={handleDepthPreviewReject}
          />
        )}
      </AnimatePresence>

      {/* Relight Viewer */}
      <AnimatePresence>
        {showRelightViewer && (
          <RelightViewer
            image={processedImage || photo?.image || location?.image}
            onClose={handleRelightPreviewReject}
            onAccept={handleRelightPreviewAccept}
            onReject={handleRelightPreviewReject}
          />
        )}
      </AnimatePresence>

      <VoiceDrawer
        isOpen={showVoiceDrawer}
        onClose={() => setShowVoiceDrawer(false)}
        history={history}
        onRestore={handleRestore}
        aiMode={aiMode}
        setAiMode={setAiMode}
        isProcessing={isProcessing}
      />



      {/* Share Modal */}
      <AnimatePresence>
        {showShare && (
          <ShareModal
            photo={photo || location}
            onClose={() => setShowShare(false)}
          />
        )}
      </AnimatePresence>

      {/* Final View Overlay */}
      <AnimatePresence>
        {showFinalView && (
          <FinalView
            image={displayImage}
            onClose={() => setShowFinalView(false)}
            appliedEffects={appliedEffects}
          />
        )}
      </AnimatePresence>

      <style>{`
        .detail-container {
          height: 100%;
      display: flex;
      flex - direction: column;
      overflow: hidden;
      background: #1a1a1d;
      position: relative;
    }
        
        .agent - review - overlay {
  position: absolute;
  bottom: 140px;
  left: 0;
  right: 0;
  z - index: 100;
  display: flex;
  justify - content: center;
  padding: 0 20px;
}
        
        .review - buttons {
  display: flex;
  gap: 20px;
}
        
        .reject - btn, .accept - btn {
  display: flex;
  align - items: center;
  gap: 8px;
  padding: 12px 24px;
  border - radius: 40px;
  border: 1px solid;
  background: rgba(0, 0, 0, 0.6);
  backdrop - filter: blur(10px);
  color: white;
  font - size: 16px;
  font - weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
        
        .reject - btn {
  border - color: #ef4444;
}
        
        .reject - btn:hover {
  background: rgba(239, 68, 68, 0.2);
  transform: scale(1.05);
}
        
        .accept - btn {
  border - color: #10b981;
}
        
        .accept - btn:hover {
  background: rgba(16, 185, 129, 0.2);
  transform: scale(1.05);
}
        
        .reject - btn span: first - child,
        .accept - btn span: first - child {
  font - size: 20px;
}
`}</style>
    </motion.div>
  );
};

export default DetailView;