import React from 'react';
import EditingToolBase from './EditingToolBase';
import SunMoonIcon from '../../assets/icons/Screen-3/sun-moon.svg';

const AutoRelightTool = ({ active, value, onChange, onClose, onApply, isProcessing, image, imageTitle, id, onOpenViewer }) => {
  return (
    <EditingToolBase
      active={active}
      value={value}
      onChange={onChange}
      onClose={onClose}
      onApply={onApply}
      isProcessing={isProcessing}
      image={image}
      title="Relighting"
      imageTitle={imageTitle}
      id={id}
      centerIcon={SunMoonIcon}
      leftLabel="Day"
      rightLabel="Night"
      showViewButton={true}
      onViewClick={onOpenViewer}
      viewHint="Tap to view fullscreen"
    />
  );
};

export default AutoRelightTool;
