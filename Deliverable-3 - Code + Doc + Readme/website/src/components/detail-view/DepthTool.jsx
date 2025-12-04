import React, { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import EditingToolBase from './EditingToolBase';
import ParallaxViewer from '../ParallaxViewer';
import BoxIcon from '../../assets/icons/Screen-3/box.svg';

const DepthTool = ({ active, value, onChange, onClose, onApply, isProcessing, image, imageTitle, id, depthData }) => {
  const [showParallax, setShowParallax] = useState(false);

  // If depthData exists, show it in the image preview
  // Otherwise show the original image
  const displayImage = depthData?.subject_layer
    ? `data:image/png;base64,${depthData.subject_layer}`
    : image;

  return (
    <>
      <EditingToolBase
        active={active}
        value={value}
        onChange={onChange}
        onClose={onClose}
        onApply={onApply}
        isProcessing={isProcessing}
        image={displayImage}
        title="3D Depth"
        imageTitle={imageTitle}
        id={id}
        centerIcon={BoxIcon}
        leftLabel="Low"
        rightLabel="High"
        showViewButton={!!depthData}
        onViewClick={() => setShowParallax(true)}
        hideSlider={true}
      />

      {/* Parallax Viewer */}
      <AnimatePresence>
        {showParallax && depthData && (
          <ParallaxViewer
            depthData={depthData}
            onClose={() => setShowParallax(false)}
            onAccept={() => setShowParallax(false)}
            onReject={() => setShowParallax(false)}
          />
        )}
      </AnimatePresence>
    </>
  );
};

export default DepthTool;
