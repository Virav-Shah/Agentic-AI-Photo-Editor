import React, { useRef, useEffect } from 'react';
import { StyleSheet, View, ActivityIndicator, Alert } from 'react-native';
import { WebView } from 'react-native-webview';
import { StatusBar } from 'expo-status-bar';
import { Camera } from 'expo-camera';
import { Audio } from 'expo-av';
import * as Location from 'expo-location';
import * as MediaLibrary from 'expo-media-library';
import * as Sensors from 'expo-sensors';
import * as FileSystem from 'expo-file-system/legacy';

// CHANGE THIS URL TO YOUR DESIRED WEBSITE
const WEBSITE_URL = 'http://<IP>:5173/';

export default function App() {
  const webViewRef = useRef(null);
  const recordingRef = useRef(null);

  useEffect(() => {
    // Request all permissions when app starts
    requestPermissions();
  }, []);

  const requestPermissions = async () => {
    try {
      // Request Camera permission
      const cameraStatus = await Camera.requestCameraPermissionsAsync();
      console.log('Camera permission:', cameraStatus.status);

      // Request Microphone permission
      const audioStatus = await Audio.requestPermissionsAsync();
      console.log('Microphone permission:', audioStatus.status);

      // Request Location permission
      const locationStatus = await Location.requestForegroundPermissionsAsync();
      console.log('Location permission:', locationStatus.status);

      // Request Media Library permission
      const mediaStatus = await MediaLibrary.requestPermissionsAsync();
      console.log('Media Library permission:', mediaStatus.status);

      // Check Motion/Gyroscope availability
      try {
        // Test if gyroscope is available by trying to access it
        const gyroscope = Sensors.Gyroscope;
        const isAvailable = await gyroscope.isAvailableAsync();
        console.log('Gyroscope available:', isAvailable);

        if (isAvailable) {
          console.log('✅ Motion sensors (gyroscope) are ready to use!');
        } else {
          console.log('⚠️ Gyroscope not available on this device');
        }
      } catch (e) {
        console.log('Motion sensor check:', e.message);
      }

      // Check if any critical permissions were denied
      if (cameraStatus.status === 'denied' || audioStatus.status === 'denied') {
        Alert.alert(
          'Permissions Required',
          'Some permissions were denied. The website may not function properly. Please enable permissions in Settings.',
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      console.error('Error requesting permissions:', error);
    }
  };

  // Handle audio recording from WebView
  const handleWebViewMessage = async (event) => {
    const data = event.nativeEvent.data;
    console.log('📱 WebView Message:', data);

    try {
      const message = JSON.parse(data);

      if (message.type === 'RECORDING_START') {
        console.log('🎤 Starting audio recording...');
        try {
          await Audio.setAudioModeAsync({
            allowsRecordingIOS: true,
            playsInSilentModeIOS: true,
          });

          const recording = new Audio.Recording();
          await recording.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
          await recording.startAsync();
          recordingRef.current = recording;
          console.log('✅ Recording started');
        } catch (err) {
          console.error('❌ Error starting recording:', err);
        }
      }
      else if (message.type === 'RECORDING_STOP') {
        console.log('🛑 Stopping audio recording...');
        if (recordingRef.current) {
          try {
            await recordingRef.current.stopAndUnloadAsync();
            const uri = recordingRef.current.getURI();
            console.log('📁 Recording saved to:', uri);

            // Use FileSystem to read the audio file
            const base64Audio = await FileSystem.readAsStringAsync(uri, {
              encoding: 'base64',
            });

            console.log('📦 Audio file read, size:', base64Audio.length, 'chars');

            // Send audio data back to WebView
            const base64data = `data:audio/m4a;base64,${base64Audio}`;
            webViewRef.current?.injectJavaScript(`
              window.dispatchEvent(new CustomEvent('audioRecorded', { 
                detail: { audioData: '${base64data}' } 
              }));
              true;
            `);
            console.log('✅ Audio data sent to WebView');

            recordingRef.current = null;
          } catch (err) {
            console.error('❌ Error stopping/reading recording:', err);
          }
        } else {
          console.warn('⚠️ No active recording to stop');
        }
      }
    } catch (e) {
      // Not a JSON message, just log it
    }
  };

  // Bridge device orientation data to WebView
  useEffect(() => {
    let subscription = null;

    const startDeviceMotion = async () => {
      try {
        // Set update interval to 60fps (16ms)
        Sensors.DeviceMotion.setUpdateInterval(16);

        // Subscribe to device motion updates
        let logCounter = 0;
        subscription = Sensors.DeviceMotion.addListener((data) => {
          // Send device orientation data to WebView
          if (webViewRef.current && data.rotation) {
            // DeviceMotion gives us rotation in radians
            // Convert to degrees for DeviceOrientationEvent
            // alpha: Z-axis (0-360)
            // beta: X-axis (-180 to 180)
            // DeviceMotion gives us rotation in radians
            // Map correctly to DeviceOrientationEvent standards:
            // Beta = Rotation around X axis (Pitch) - Front/Back tilt
            // Gamma = Rotation around Y axis (Roll) - Left/Right tilt

            const alpha = 0; // We don't need compass direction for parallax
            const beta = data.rotation.beta * (180 / Math.PI);
            const gamma = data.rotation.gamma * (180 / Math.PI);


            // Use postMessage for more reliable communication
            const message = JSON.stringify({
              type: 'deviceMotion',
              payload: {
                alpha,
                beta,
                gamma
              }
            });
            webViewRef.current.postMessage(message);
          } else if (!webViewRef.current) {
            if (logCounter++ % 60 === 0) console.log('⚠️ WebView ref is null');
          } else if (!data.rotation) {
            if (logCounter++ % 60 === 0) console.log('⚠️ No rotation data');
          }
        });

        console.log('✅ Device orientation bridge started (using postMessage)');
      } catch (error) {
        console.error('Error starting device orientation bridge:', error);
      }
    };

    // Start device motion after a short delay to ensure WebView is loaded
    const timer = setTimeout(startDeviceMotion, 2000);

    return () => {
      clearTimeout(timer);
      if (subscription) {
        subscription.remove();
        console.log('🛑 Device orientation bridge stopped');
      }
    };
  }, []);

  return (
    <View style={styles.container}>
      <StatusBar style="light" hidden={true} />
      <WebView
        ref={webViewRef}
        source={{ uri: WEBSITE_URL }}
        style={styles.webview}
        // Enable JavaScript
        javaScriptEnabled={true}
        // Enable DOM storage
        domStorageEnabled={true}
        // Allow file access
        allowFileAccess={true}
        // Allow universal access from file URLs
        allowUniversalAccessFromFileURLs={true}
        // Allow file access from file URLs
        allowFileAccessFromFileURLs={true}
        // Enable geolocation
        geolocationEnabled={true}
        // Allow media playback
        mediaPlaybackRequiresUserAction={false}
        // Allow inline media playback (iOS)
        allowsInlineMediaPlayback={true}
        // Start in loading state
        startInLoadingState={true}
        // Inject JavaScript BEFORE content loads to create polyfills
        injectedJavaScriptBeforeContentLoaded={`
          window.ReactNativeWebView.postMessage('WebView: Creating media polyfills...');
          
          // Create navigator.mediaDevices if it doesn't exist
          if (!navigator.mediaDevices) {
            navigator.mediaDevices = {};
          }
          
          // Create MediaStream polyfill
          window.MockMediaStream = function() {
            this.id = 'rn-stream-' + Date.now();
            this.active = true;
            this.getTracks = function() { return []; };
            this.getAudioTracks = function() { return []; };
            this.getVideoTracks = function() { return []; };
            this.addTrack = function() {};
            this.removeTrack = function() {};
            this.stop = function() {
              this.active = false;
            };
          };
          
          // Create getUserMedia polyfill
          navigator.mediaDevices.getUserMedia = function(constraints) {
            window.ReactNativeWebView.postMessage('getUserMedia called: ' + JSON.stringify(constraints));
            return new Promise((resolve, reject) => {
              if (constraints.audio) {
                const stream = new window.MockMediaStream();
                window.ReactNativeWebView.postMessage('Returning MediaStream');
                resolve(stream);
              } else {
                reject(new Error('Only audio is supported'));
              }
            });
          };
          
          // Create MediaRecorder polyfill
          window.MediaRecorder = function(stream, options) {
            this.state = 'inactive';
            this.stream = stream;
            this.ondataavailable = null;
            this.onstop = null;
            this.onerror = null;
            const self = this;
            
            this.start = function() {
              window.ReactNativeWebView.postMessage('MediaRecorder.start()');
              this.state = 'recording';
              // Notify RN to start recording
              window.ReactNativeWebView.postMessage(JSON.stringify({
                type: 'RECORDING_START'
              }));
            };
            
            this.stop = function() {
              window.ReactNativeWebView.postMessage('MediaRecorder.stop()');
              this.state = 'inactive';
              
              // Listen for audio data from React Native
              window.addEventListener('audioRecorded', function handler(event) {
                window.removeEventListener('audioRecorded', handler);
                window.ReactNativeWebView.postMessage('Received audio data from RN');
                
                // Convert base64 to Blob
                const audioData = event.detail.audioData;
                fetch(audioData)
                  .then(res => res.blob())
                  .then(blob => {
                    window.ReactNativeWebView.postMessage('Created blob from audio data');
                    
                    // Trigger data available event with real audio blob
                    if (self.ondataavailable) {
                      self.ondataavailable({ data: blob });
                    }
                    
                    // Trigger stop event
                    if (self.onstop) {
                      self.onstop();
                    }
                  })
                  .catch(err => {
                    window.ReactNativeWebView.postMessage('ERROR creating blob: ' + err.message);
                  });
              });
              
              // Notify RN to stop recording
              window.ReactNativeWebView.postMessage(JSON.stringify({
                type: 'RECORDING_STOP'
              }));
            };
            
            this.pause = function() { this.state = 'paused'; };
            this.resume = function() { this.state = 'recording'; };
          };
          
          window.MediaRecorder.isTypeSupported = function() { return true; };
          
          // Override console
          const originalLog = console.log;
          console.log = function(...args) {
            originalLog.apply(console, args);
            try {
              window.ReactNativeWebView.postMessage('LOG: ' + args.join(' '));
            } catch(e) {}
          };
          
          const originalError = console.error;
          console.error = function(...args) {
            originalError.apply(console, args);
            try {
              window.ReactNativeWebView.postMessage('ERROR: ' + args.join(' '));
            } catch(e) {}
          };
          
          window.ReactNativeWebView.postMessage('✅ Media polyfills installed');
          true;
        `}
        // Inject after page loads
        injectedJavaScript={`
          window.ReactNativeWebView.postMessage('Page loaded - Media APIs ready');
          true;
        `}
        // Handle messages from WebView
        onMessage={handleWebViewMessage}
        // Custom loading indicator
        renderLoading={() => (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#0000ff" />
          </View>
        )}
        // Handle errors
        onError={(syntheticEvent) => {
          const { nativeEvent } = syntheticEvent;
          console.warn('WebView error: ', nativeEvent);
        }}
        // Handle HTTP errors
        onHttpError={(syntheticEvent) => {
          const { nativeEvent } = syntheticEvent;
          console.warn('WebView HTTP error: ', nativeEvent);
        }}
        // Handle permission requests from web content (microphone, camera, etc.)
        onPermissionRequest={(request) => {
          const { resources } = request.nativeEvent;
          console.log('🎤 WebView permission request:', resources);

          // Grant all requested permissions
          if (resources && resources.length > 0) {
            request.grant(resources);
            console.log('✅ Granted WebView permissions:', resources);
          }
        }}
        // Android-specific: Set user agent to enable media permissions
        userAgent="Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
        // Mixed content mode (Android) - allow mixed HTTP/HTTPS content
        mixedContentMode="always"
        // Third party cookies (Android)
        thirdPartyCookiesEnabled={true}
        // Shared cookies (iOS)
        sharedCookiesEnabled={true}
        // Android: Enable media capture
        androidLayerType="hardware"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  webview: {
    flex: 1,
  },
  loadingContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
});