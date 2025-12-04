import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { RotateCcw, X } from 'lucide-react';
import CheckIcon from '../assets/icons/Screen-4/check.svg';
import XIcon from '../assets/icons/Screen-4/x.svg';

const ParallaxViewer = ({ depthData, onClose, isReviewing = false, onAccept, onReject, hideControls = false }) => {
    const containerRef = useRef(null);
    const viewerRef = useRef(null);
    const [gyroSupported, setGyroSupported] = useState(false);
    const [gyroPermission, setGyroPermission] = useState('unknown');
    const [calibrated, setCalibrated] = useState(false);
    const calibrationRef = useRef({ beta: 0, gamma: 0, hasCalibrated: false });
    const [hasAutoCalibrated, setHasAutoCalibrated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    // Smoothing for gyro input 
    const smoothedRef = useRef({ x: 0, y: 0 });
    const smoothingFactor = 0.8; // Very smooth 
    const [debugData, setDebugData] = useState({
        beta: 0, gamma: 0,
        adjBeta: 0, adjGamma: 0,
        rawNormX: 0, rawNormY: 0,
        normalizedX: 0, normalizedY: 0,
        lastMsg: 'none',
        clientX: 0, clientY: 0,
        rnBeta: 0,
        rnGamma: 0,
        clamped: false,
        viewerX: 0,
        viewerY: 0,
        rectW: 0,
        rectH: 0
    });

    // Shared function to process orientation data
    const processOrientation = (beta, gamma) => {
        if (!viewerRef.current || !viewerRef.current.onMouseMove) {
            return;
        }

        if (!containerRef.current) {
            return;
        }

        if (beta === null || gamma === null) return;

        // Auto-calibrate on first data using ref
        if (!calibrationRef.current.hasCalibrated && (beta !== 0 || gamma !== 0)) {
            calibrationRef.current = { beta, gamma, hasCalibrated: true };
            setHasAutoCalibrated(true);
            console.log('✅ Auto-calibrated to:', { beta, gamma });
        }

        const adjustedBeta = beta - calibrationRef.current.beta;
        const adjustedGamma = gamma - calibrationRef.current.gamma;

        // This gives full range of motion without hitting the limits
        const sensitivity = 3.0;

        // INVERT directions: tilt left = parallax right, tilt up = parallax down
        // We do this by negating the adjusted values
        const rawNormX = (-adjustedGamma / 45) * sensitivity;
        const rawNormY = (-adjustedBeta / 45) * sensitivity;

        // Clamped to -1 to 1
        const targetNormX = Math.max(-1, Math.min(1, rawNormX));
        const targetNormY = Math.max(-1, Math.min(1, rawNormY));

        // Apply STRONG smoothing for ultra-buttery movement
        smoothedRef.current.x += (targetNormX - smoothedRef.current.x) * smoothingFactor;
        smoothedRef.current.y += (targetNormY - smoothedRef.current.y) * smoothingFactor;

        const normalizedX = smoothedRef.current.x;
        const normalizedY = smoothedRef.current.y;

        // Get container rect for conversion
        const rect = containerRef.current.getBoundingClientRect();

        // Convert normalized (-1 to 1) to client coordinates
        const clientX = ((normalizedX + 1) / 2) * rect.width + rect.left;
        const clientY = ((normalizedY + 1) / 2) * rect.height + rect.top;

        // What the viewer will calculate from these coordinates
        const viewerWillGetX = (clientX - rect.left) / rect.width * 2 - 1;
        const viewerWillGetY = (clientY - rect.top) / rect.height * 2 - 1;


        const mouseEvent = new MouseEvent('mousemove', {
            bubbles: true,
            cancelable: true,
            clientX: clientX,
            clientY: clientY,
            view: window
        });

        // Dispatch to both the container and document
        containerRef.current.dispatchEvent(mouseEvent);
        document.dispatchEvent(mouseEvent);

        // ALSO call the method directly as backup
        viewerRef.current.onMouseMove({ clientX, clientY });
    };

    // Handle device orientation (native fallback)
    useEffect(() => {
        const handleOrientation = (event) => {
            processOrientation(event.beta, event.gamma);
        };

        window.addEventListener('deviceorientation', handleOrientation);

        return () => {
            window.removeEventListener('deviceorientation', handleOrientation);
        };
    }, []);

    // Handle messages from React Native WebView
    useEffect(() => {
        const handleReactNativeMessage = (event) => {
            try {
                // Log raw message reception (for debugging)
                if (!window._msgLogCounter) window._msgLogCounter = 0;
                if (window._msgLogCounter++ % 60 === 0) {
                    console.log('📩 Message received:', typeof event.data === 'string' ? event.data.substring(0, 50) + '...' : 'Object');
                }

                // Parse message if it's a string (Android sometimes sends stringified JSON)
                const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;

                if (data.type === 'deviceMotion') {
                    const { alpha, beta, gamma } = data.payload;

                    // Update debug data directly to verify message reception
                    setDebugData(prev => ({
                        ...prev,
                        lastMsg: new Date().toLocaleTimeString(),
                        rnBeta: beta.toFixed(1),
                        rnGamma: gamma.toFixed(1)
                    }));

                    // DIRECTLY PROCESS DATA
                    processOrientation(beta, gamma);
                }
            } catch (e) {
                // Ignore non-JSON messages
            }
        };

        // Listen for messages from React Native
        window.addEventListener('message', handleReactNativeMessage);
        document.addEventListener('message', handleReactNativeMessage);

        // Test if gyroscope actually works
        const testGyroscope = () => {
            return new Promise((resolve) => {
                if (!window.DeviceOrientationEvent) {
                    console.log('❌ DeviceOrientationEvent not available');
                    resolve(false);
                    return;
                }

                console.log('✅ DeviceOrientationEvent available, testing...');
                let eventFired = false;
                const testHandler = (event) => {
                    console.log('📱 Gyro event received:', { beta: event.beta, gamma: event.gamma });
                    if (event.beta !== null && event.gamma !== null) {
                        eventFired = true;
                    }
                };

                window.addEventListener('deviceorientation', testHandler, true);

                setTimeout(() => {
                    window.removeEventListener('deviceorientation', testHandler, true);
                    console.log('Gyro test result:', eventFired ? '✅ Working' : '⚠️ No events received');
                    resolve(eventFired);
                }, 1000);
            });
        };

        const init = async () => {
            console.log('🔄 Initializing ParallaxViewer...');

            const isIOS13Plus = typeof DeviceOrientationEvent !== 'undefined' &&
                typeof DeviceOrientationEvent.requestPermission === 'function';

            console.log('Platform check:', isIOS13Plus ? 'iOS 13+' : 'Other/Android');

            const gyroWorks = await testGyroscope();

            if (gyroWorks) {
                console.log('✅ Gyroscope is working!');
                setGyroSupported(true);
                if (isIOS13Plus) {
                    console.log('⚠️ iOS 13+ detected - permission prompt required');
                    setGyroPermission('prompt');
                } else {
                    console.log('✅ Auto-granting gyro permission (non-iOS13+)');
                    setGyroPermission('granted');
                    initViewer();
                }
            } else {
                console.log('⚠️ Gyroscope not working or not available');
                setGyroSupported(false);
                setGyroPermission('not-supported');
                initViewer();
            }
        };

        init();

        return () => {
            if (viewerRef.current && viewerRef.current.destroy) {
                viewerRef.current.destroy();
            }
            window.removeEventListener('message', handleReactNativeMessage);
            document.removeEventListener('message', handleReactNativeMessage);
        };
    }, []);

    const requestGyroPermission = async () => {
        console.log('🔐 Requesting gyroscope permission...');
        if (typeof DeviceOrientationEvent.requestPermission === 'function') {
            try {
                const permissionState = await DeviceOrientationEvent.requestPermission();
                console.log('Permission result:', permissionState);
                setGyroPermission(permissionState);
                if (permissionState === 'granted') {
                    console.log('✅ Gyroscope permission granted! Initializing viewer...');
                    initViewer();
                } else {
                    console.log('❌ Gyroscope permission denied');
                }
            } catch (error) {
                console.error('❌ Error requesting gyroscope permission:', error);
            }
        } else {
            console.log('ℹ️ No permission request needed, granting automatically');
            setGyroPermission('granted');
            initViewer();
        }
    };

    const calibrateGyro = (event) => {
        if (event.beta !== null && event.gamma !== null) {
            calibrationRef.current = {
                beta: event.beta,
                gamma: event.gamma,
                hasCalibrated: true
            };
            setCalibrated(true);
        }
    };

    const initViewer = async () => {
        if (!containerRef.current || !depthData) {
            setIsLoading(false);
            return;
        }

        try {
            if (depthData.has_layers === false) {
                containerRef.current.innerHTML = '';

                const { TieflingView } = await import('../tiefling_view.js');

                const imageUrl = `data:image/png;base64,${depthData.subject_layer}`;
                const depthUrl = depthData.full_depth ? `data:image/png;base64,${depthData.full_depth}` : null;

                const viewer = TieflingView(containerRef.current, imageUrl, depthUrl, {
                    background: null,
                    backgroundDepthMap: null,
                    mask: null,
                    focus: 0.5,
                    baseMouseSensitivity: 0.45,
                    meshResolution: 512,
                    meshDepth: 0.8,
                    cropPercent: 15,
                    foregroundSensitivity: 1.0,
                    groundedMode: false
                });
                viewerRef.current = viewer;
            } else {
                const { TieflingView } = await import('../tiefling_view.js');

                const foregroundUrl = `data:image/png;base64,${depthData.subject_layer}`;
                const foregroundDepthUrl = `data:image/png;base64,${depthData.foreground_depth}`;
                const backgroundUrl = depthData.background_layer ? `data:image/png;base64,${depthData.background_layer}` : null;
                const backgroundDepthUrl = depthData.background_depth ? `data:image/png;base64,${depthData.background_depth}` : null;
                const maskUrl = depthData.mask ? `data:image/png;base64,${depthData.mask}` : null;

                const viewer = TieflingView(containerRef.current, foregroundUrl, foregroundDepthUrl, {
                    background: backgroundUrl,
                    backgroundDepthMap: backgroundDepthUrl,
                    mask: maskUrl,
                    focus: 0.75,
                    baseMouseSensitivity: 0.4,
                    meshResolution: 512,
                    meshDepth: 1.0,
                    expandDepthmapRadius: 7,
                    cropPercent: 15,
                    foregroundSensitivity: 1.0,
                    backgroundSensitivity: 1.0,
                    groundedMode: false
                });

                viewerRef.current = viewer;
            }

            if (gyroPermission === 'granted' && gyroSupported) {
                setTimeout(() => {
                    const calibrateHandler = (event) => {
                        calibrateGyro(event);
                        window.removeEventListener('deviceorientation', calibrateHandler);
                    };
                    window.addEventListener('deviceorientation', calibrateHandler, true);
                }, 1000);
            }
        } catch (error) {
            console.error("Error initializing 3D viewer:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleRecalibrate = () => {
        setCalibrated(false);
        calibrationRef.current = { beta: 0, gamma: 0, hasCalibrated: false };
        const calibrateHandler = (event) => {
            calibrateGyro(event);
            window.removeEventListener('deviceorientation', calibrateHandler);
        };
        window.addEventListener('deviceorientation', calibrateHandler);
    };

    return (
        <motion.div
            className="parallax-viewer-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
        >
            {/* Blurred Background Image */}
            {depthData?.subject_layer && (
                <div
                    className="blurred-background"
                    style={{
                        backgroundImage: `url(data:image/png;base64,${depthData.subject_layer})`,
                    }}
                />
            )}

            <div className="parallax-controls">
                {gyroSupported && gyroPermission === 'granted' ? (
                    <button className="icon-btn glass" onClick={handleRecalibrate} title="Recalibrate">
                        <RotateCcw size={20} />
                    </button>
                ) : <div></div>}
            </div>

            {isLoading && (
                <div className="loader-container">
                    <div className="spinner"></div>
                    <div className="loading-text">Loading 3D View...</div>
                </div>
            )}


            {gyroPermission === 'prompt' && (
                <div className="permission-prompt">
                    <button className="permission-btn" onClick={requestGyroPermission}>
                        Enable Gyroscope
                    </button>
                </div>
            )}

            {!hideControls && (
                <div className="edit-actions">
                    <button className="circle-action cancel" onClick={onReject}>
                        <img src={XIcon} alt="Cancel" style={{ width: 24, height: 24 }} />
                    </button>
                    <button className="circle-action confirm" onClick={onAccept}>
                        <img src={CheckIcon} alt="Confirm" style={{ width: 24, height: 24 }} />
                    </button>
                </div>
            )}

            <div ref={containerRef} className="parallax-container"></div>

            <style>{`
        .parallax-viewer-overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: #000;
          z-index: 300;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .blurred-background {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background-size: cover;
          background-position: center;
          background-repeat: no-repeat;
          filter: blur(10px);
          transform: scale(1.1);
          opacity: 0.3;
          z-index: 0;
        }

        .blurred-background::after {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.5);
        }

        .parallax-controls {
          position: absolute;
          top: 20px;
          left: 20px;
          right: 20px;
          display: flex;
          justify-content: space-between;
          z-index: 301;
          pointer-events: none;
        }

        .parallax-controls button {
          pointer-events: auto;
        }

        .icon-btn {
          width: 44px;
          height: 44px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .icon-btn:active {
          transform: scale(0.95);
          background: rgba(255, 255, 255, 0.2);
        }

        .parallax-container {
          flex: 1;
          width: 100%;
          height: 100%;
          position: relative;
          z-index: 1;
        }

        .permission-prompt {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          z-index: 302;
        }

        .permission-btn {
          padding: 16px 32px;
          background: linear-gradient(135deg, rgba(10, 132, 255, 0.3) 0%, rgba(94, 92, 230, 0.3) 100%);
          border: 1px solid rgba(10, 132, 255, 0.5);
          border-radius: 16px;
          font-size: 16px;
          font-weight: 600;
          color: white;
          cursor: pointer;
          transition: all 0.3s;
          backdrop-filter: blur(10px);
        }

        .permission-btn:active {
          transform: scale(0.98);
        }

        .edit-actions {
          display: flex;
          justify-content: space-between;
          align-items: center;
          width: 100%;
          position: absolute;
          bottom: 64px;
          max-width: 300px;
          padding: 0 32px;
          z-index: 302;
          left: 50%;
          transform: translateX(-50%);
          pointer-events: auto;
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

        .loader-container {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
          z-index: 400;
        }

        .spinner {
          width: 40px;
          height: 40px;
          border: 3px solid rgba(255, 255, 255, 0.3);
          border-radius: 50%;
          border-top-color: #fff;
          animation: spin 1s ease-in-out infinite;
        }

        .loading-text {
          color: rgba(255, 255, 255, 0.8);
          font-size: 14px;
          font-weight: 500;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
        </motion.div>
    );
};

export default ParallaxViewer;