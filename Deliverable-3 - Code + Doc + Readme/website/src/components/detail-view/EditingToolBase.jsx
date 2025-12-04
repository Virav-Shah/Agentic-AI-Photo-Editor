import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RotateCcw } from 'lucide-react';
import CheckIcon from '../../assets/icons/Screen-4/check.svg';
import XIcon from '../../assets/icons/Screen-4/x.svg';
import RelightIcon from '../../assets/icons/Screen-4/relight.svg';

const EditingToolBase = ({
  active,
  value,
  onChange,
  onClose,
  onApply,
  isProcessing,
  image,
  title,
  imageTitle,
  id,
  centerIcon = RelightIcon,
  leftLabel = 'Day',
  rightLabel = 'Night',
  showViewButton = false,
  onViewClick,
  viewHint = "Tap to view",
  hideSlider = false
}) => {
  const [isDragging, setIsDragging] = React.useState(false);
  const [showControls, setShowControls] = React.useState(false);
  const hasShownControls = React.useRef(false);
  const containerRef = React.useRef(null);

  // Delay showing controls to prevent flicker during image transition
  React.useEffect(() => {
    if (active) {
      // Immediately hide on mount
      setShowControls(false);
      hasShownControls.current = false;

      const timer = setTimeout(() => {
        hasShownControls.current = true;
        setShowControls(true);
      }, 700); // Increased delay to ensure image settles

      return () => clearTimeout(timer);
    } else {
      setShowControls(false);
      hasShownControls.current = false;
    }
  }, [active]);

  // Arc configuration
  const arcRadius = 330;
  const arcCenter = { x: 330, y: 315 };
  const arcStartAngle = -55;
  const arcEndAngle = 55;
  const arcRange = arcEndAngle - arcStartAngle;

  // Handle drag interaction
  const handleInteraction = (clientX, clientY) => {
    if (!containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;

    // Calculate angle from center
    const dx = x - arcCenter.x;
    const dy = y - arcCenter.y;
    let angle = Math.atan2(dy, dx) * (180 / Math.PI) + 90;

    // Clamp angle to arc range
    if (angle < arcStartAngle) angle = arcStartAngle;
    if (angle > arcEndAngle) angle = arcEndAngle;

    // Map angle to value (0-100)
    const newValue = ((angle - arcStartAngle) / arcRange) * 100;
    onChange(Math.round(newValue));
  };

  // Helper for SVG Arc
  const polarToCartesian = (centerX, centerY, radius, angleInDegrees) => {
    const angleInRadians = (angleInDegrees - 90) * Math.PI / 180.0;
    return {
      x: centerX + (radius * Math.cos(angleInRadians)),
      y: centerY + (radius * Math.sin(angleInRadians))
    };
  };

  // Calculate current angle based on value (0-100)
  const currentAngle = arcStartAngle + (value / 100) * arcRange;

  // Knob position
  const knobPos = polarToCartesian(arcCenter.x, arcCenter.y, arcRadius, currentAngle);

  const isNearKnob = (clientX, clientY) => {
    if (!containerRef.current) return false;

    const rect = containerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;

    // Calculate distance from click to knob position
    const dx = x - knobPos.x;
    const dy = y - knobPos.y;
    const distance = Math.sqrt(dx * dx + dy * dy);

    // Allow dragging if within 50px of knob (increased from 30px)
    return distance < 50;
  };

  const handlePointerDown = (e) => {
    if (isNearKnob(e.clientX, e.clientY)) {
      setIsDragging(true);
      // Haptic feedback for iPhone
      if (navigator.vibrate) {
        navigator.vibrate(10); // 10ms vibration
      }
      handleInteraction(e.clientX, e.clientY); // Immediately update if near knob
    }
  };

  const handlePointerMove = (e) => {
    if (isDragging) {
      handleInteraction(e.clientX, e.clientY);
    }
  };

  const handlePointerUp = () => {
    setIsDragging(false);
  };

  const handleTouchStart = (e) => {
    const touch = e.touches[0];
    if (isNearKnob(touch.clientX, touch.clientY)) {
      setIsDragging(true);
      // Haptic feedback for iPhone
      if (navigator.vibrate) {
        navigator.vibrate(10); // 10ms vibration
      }
      handleInteraction(touch.clientX, touch.clientY); // Immediately update if near knob
    }
  };

  const handleTouchMove = (e) => {
    if (isDragging) {
      const touch = e.touches[0];
      handleInteraction(touch.clientX, touch.clientY);
    }
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
  };

  React.useEffect(() => {
    if (isDragging) {
      window.addEventListener('pointermove', handlePointerMove);
      window.addEventListener('pointerup', handlePointerUp);
      window.addEventListener('touchmove', handleTouchMove);
      window.addEventListener('touchend', handleTouchEnd);

      return () => {
        window.removeEventListener('pointermove', handlePointerMove);
        window.removeEventListener('pointerup', handlePointerUp);
        window.removeEventListener('touchmove', handleTouchMove);
        window.removeEventListener('touchend', handleTouchEnd);
      };
    }
  }, [isDragging]);

  const describeArc = (x, y, radius, startAngle, endAngle) => {
    const start = polarToCartesian(x, y, radius, endAngle);
    const end = polarToCartesian(x, y, radius, startAngle);
    const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
    const d = [
      "M", start.x, start.y,
      "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y
    ].join(" ");
    return d;
  };

  return (
    <AnimatePresence>
      {active && (
        <motion.div
          className="tool-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { delay: 0, duration: 0.6 } }}
          transition={{ duration: 0.6, ease: "easeIn" }}
        >
          {/* Header Title */}
          <div className="tool-header">
            <span>{title} {imageTitle}</span>
          </div>

          {/* Image with Gradients */}
          <div className="tool-image-container">
            <motion.div
              className="tool-image-wrapper"
              layoutId={`image-${id}`}
              transition={{ duration: 0.5, ease: "easeInOut" }}
              onClick={showViewButton ? onViewClick : undefined}
              style={{ cursor: showViewButton ? 'pointer' : 'default' }}
            >
              {/* Top Gradient Overlay */}
              <div className="gradient-overlay top"></div>

              {/* Bottom Gradient Overlay */}
              <div className="gradient-overlay bottom"></div>

              <img
                src={image}
                alt="Editing"
                className="tool-image"
                draggable={false}
                onContextMenu={(e) => e.preventDefault()}
              />

              {/* Tap hint overlay (optional, but good for UX) */}
              {showViewButton && (
                <div className="tap-hint-overlay">
                  <span>{viewHint}</span>
                </div>
              )}
            </motion.div>
          </div>

          {/* Controls Container - Only render after image transition completes */}
          {showControls && hasShownControls.current && (
            <motion.div
              className="controls-container"
              initial={{ y: 400, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 400, opacity: 0 }}
              transition={{
                type: "spring",
                stiffness: 120,
                damping: 20
              }}
              style={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                width: '100%',
                pointerEvents: 'none',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'flex-end',
                alignItems: 'center',
                paddingBottom: '40px',
                willChange: 'transform, opacity'
              }}
            >
              {/* Blur Layer - sits behind controls to blur the image */}
              <div className="controls-blur-layer">
                <img src={image} alt="" className="blur-image" />
              </div>

              {/* Controls Base Background */}
              <div className="controls-base" style={{ pointerEvents: 'auto' }}></div>

              <div className="curved-slider-wrapper" style={{ pointerEvents: hideSlider ? 'none' : 'auto' }}>
                <div
                  ref={containerRef}
                  className="curved-track-container"
                  onPointerDown={!hideSlider ? handlePointerDown : undefined}
                  onTouchStart={!hideSlider ? handleTouchStart : undefined}
                  style={{ cursor: hideSlider ? 'default' : 'pointer', touchAction: 'none' }}
                >
                  <svg width="660" height="160" viewBox="0 0 660 160" className="curved-svg">
                    {hideSlider ? (
                      /* Static Decorative Arc (Full Range) */
                      <path
                        d={describeArc(arcCenter.x, arcCenter.y, arcRadius, arcStartAngle, arcEndAngle)}
                        fill="none"
                        stroke="#68AFFF"
                        strokeWidth="2"
                        strokeLinecap="round"
                        style={{ filter: 'blur(2px)', opacity: 0.3 }}
                      />
                    ) : (
                      <>
                        {/* Glow Layer (Behind) */}
                        <path
                          d={describeArc(arcCenter.x, arcCenter.y, arcRadius, arcStartAngle, currentAngle)}
                          fill="none"
                          stroke="#68AFFF"
                          strokeWidth="6"
                          strokeLinecap="round"
                          style={{ filter: 'blur(8px)', opacity: 0.6 }}
                        />
                        {/* Active Fill Track */}
                        <path
                          d={describeArc(arcCenter.x, arcCenter.y, arcRadius, arcStartAngle, currentAngle)}
                          fill="none"
                          stroke="#9FCBFD"
                          strokeWidth="2"
                          strokeLinecap="round"
                          style={{ filter: 'drop-shadow(0 0 4px rgba(104, 175, 255, 0.8))' }}
                        />
                      </>
                    )}
                  </svg>

                  {/* Knob (Only if not hidden) */}
                  {!hideSlider && (
                    <div
                      className="curved-knob"
                      style={{
                        left: knobPos.x,
                        top: knobPos.y,
                        transform: `translate(-50%, -50%) scale(${isDragging ? 1.4 : 1})`,
                        transition: 'transform 0.15s ease-out'
                      }}
                    />
                  )}

                  {/* Center Status Icon (Always Visible) */}
                  <div className="center-status-icon">
                    <img src={centerIcon} alt="Status" />
                  </div>
                </div>

                {/* Labels (Always render to preserve layout spacing, just hide opacity) */}
                <div className="slider-labels" style={{ opacity: hideSlider ? 0 : 1 }}>
                  <span>{leftLabel}</span>
                  <span>{rightLabel}</span>
                </div>
              </div>

              <div className="edit-actions" style={{ pointerEvents: 'auto' }}>
                <button className="circle-action cancel" onClick={onClose}>
                  <img src={XIcon} alt="Cancel" style={{ width: 24, height: 24 }} />
                </button>
                <button
                  className="circle-action confirm"
                  onClick={onApply}
                  disabled={isProcessing}
                >
                  {isProcessing ? <div className="spinner"></div> : <img src={CheckIcon} alt="Confirm" style={{ width: 24, height: 24 }} />}
                </button>
              </div>
            </motion.div>
          )}

          <style>{`
            .tool-overlay {
              position: absolute;
              top: 0;
              left: 0;
              width: 100%;
              height: 100%;
              background: #000;
              z-index: 100;
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: flex-end;
              padding-bottom: 40px;
              overflow: hidden;
            }

            .controls-base {
              position: absolute;
              width: 659px;
              height: 731px;
              left: 50%;
              transform: translateX(-50%) translateZ(0);
              bottom: -420px;
              border-radius: 99999px;
              background: linear-gradient(187deg, rgba(35, 45, 56, 0.59) 7.38%, rgba(35, 45, 56, 0.59) 36.2%);
              z-index: 5;
              pointer-events: none;
              backdrop-filter: blur(20px);
              -webkit-backdrop-filter: blur(20px);
              border: 2px solid #232D38;
              will-change: backdrop-filter;
              overflow: hidden;
            }

            .controls-base::before {
              content: '';
              position: absolute;
              top: 0;
              left: 0;
              right: 0;
              bottom: 0;
              background: inherit;
              filter: blur(20px);
              opacity: 0.8;
              z-index: -1;
            }

            .controls-blur-layer {
              position: absolute;
              width: 659px;
              height: 170px;
              left: 50%;
              transform: translateX(-50%);
              bottom: 0;
              overflow: hidden;
              z-index: 4;
              pointer-events: none;
              border-radius: 99999px 99999px 0 0;
              mask-image: linear-gradient(to bottom, transparent 0%, black 20%, black 100%);
              -webkit-mask-image: linear-gradient(to bottom, transparent 0%, black 20%, black 100%);
            }

            .blur-image {
              position: absolute;
              width: 494px;
              height: 617px;
              left: 50%;
              top: -267px;
              transform: translateX(-50%);
              object-fit: cover;
              filter: blur(20px);
              opacity: 0.6;
              scale: 1.1;
            }

            .tool-header {
              position: absolute;
              top: 84px;
              width: 100%;
              text-align: center;
              z-index: 10;
              color: white;
              font-size: 17px;
              font-weight: 600;
              font-family: "SF Pro", -apple-system, sans-serif;
              pointer-events: none;
            }

            .tool-image-container {
              position: absolute;
              top: -20px;
              left: 0;
              width: 100%;
              height: 100%;
              display: flex;
              align-items: center;
              justify-content: center;
              z-index: 0;
            }

            .tool-image-wrapper {
              width: 494px;
              height: 617px;
              aspect-ratio: 494/617;
              position: relative;
              overflow: hidden;
            }

            .tool-image {
              width: 100%;
              height: 100%;
              object-fit: cover;
              display: block;
              user-select: none;
              -webkit-user-select: none;
              -webkit-touch-callout: none;
              pointer-events: none;
            }

            .gradient-overlay {
              position: absolute;
              left: 0;
              right: 0;
              pointer-events: none;
              z-index: 2;
            }

            .gradient-overlay.top {
              top: 0px;
              width: 100%;
              height: 126px;
              background: linear-gradient(180deg, #000 0%, rgba(0, 0, 0, 0.00) 100%);
            }

            .gradient-overlay.bottom {
              bottom: 0;
              width: 100%;
              height: 100px;
              background: linear-gradient(180deg, rgba(0, 0, 0, 0.00) -5%, #000 95%);
            }

            .curved-slider-wrapper {
              display: flex;
              flex-direction: column;
              align-items: center;
              margin-bottom: 30px;
              z-index: 10;
              position: relative;
            }

            .curved-track-container {
              position: relative;
              width: 660px;
              height: 160px;
              display: flex;
              align-items: center;
              justify-content: center;
            }

            .curved-svg {
              overflow: visible;
              position: absolute;
              top: 0;
              left: 0;
            }

            .curved-knob {
              position: absolute;
              width: 16px;
              height: 16px;
              background: #68AFFF;
              border-radius: 50%;
              box-shadow: 0 0 10px rgba(104, 175, 255, 0.8), 0 0 20px rgba(104, 175, 255, 0.4);
              pointer-events: none;
              z-index: 10;
            }

            .center-status-icon {
              position: absolute;
              top: 20px;
              left: 50%;
              transform: translateX(-50%);
              width: 48px;
              height: 48px;
              border-radius: 50%;
              background: rgba(255, 255, 255, 0.1);
              backdrop-filter: blur(10px);
              -webkit-backdrop-filter: blur(10px);
              border: 1px solid rgba(255, 255, 255, 0.2);
              display: flex;
              align-items: center;
              justify-content: center;
              z-index: 5;
              pointer-events: none;
            }
            
            .center-status-icon img {
              width: 24px;
              height: 24px;
              opacity: 0.9;
            }

            .invisible-slider {
              position: absolute;
              top: 0;
              left: 0;
              width: 100%;
              height: 100%;
              opacity: 0;
              cursor: pointer;
              z-index: 20;
            }

            .slider-labels {
              display: flex;
              justify-content: space-between;
              width: 360px;
              margin-top: 10px;
              transform: translateY(-120px);
              color: #D9D9D9;
              font-size: 13px;
              font-weight: 400;
              position: relative;
              z-index: 20;
            }

            .edit-actions {
              display: flex;
              justify-content: space-between;
              align-items: center;
              width: 100%;
              bottom: 64px;
              max-width: 300px;
              padding: 0 32px;
              z-index: 10;
              position: relative;
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

            .circle-action:disabled {
              opacity: 0.5;
              cursor: not-allowed;
            }

            .spinner {
              width: 16px;
              height: 16px;
              border: 2px solid rgba(255,255,255,0.3);
              border-top-color: white;
              border-radius: 50%;
              animation: spin 1s linear infinite;
            }

            @keyframes spin {
              to { transform: rotate(360deg); }
            }

            @media (max-width: 450px) {
              .tool-header {
                top: 74px;
              }

              .controls-container {
                padding-bottom: max(0px, env(safe-area-inset-bottom));
              }

              .controls-base {
                bottom: -450px;
              }

              .curved-slider-wrapper {
                margin-bottom: 0px;
                transform: translateY(0px);
              }

              .edit-actions {
                bottom: 60px;
              }
            }
            .tap-hint-overlay {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(4px);
            padding: 8px 16px;
            border-radius: 20px;
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            font-weight: 500;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s ease;
          }

          .tool-image-wrapper:hover .tap-hint-overlay {
            opacity: 1;
          }
        `}</style>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default EditingToolBase;
