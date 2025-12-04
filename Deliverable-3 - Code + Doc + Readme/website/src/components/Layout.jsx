import React from 'react';
import { motion } from 'framer-motion';
import iphoneLayout from '../assets/emulator/iphone-layout.png';

const Layout = ({ children }) => {
  return (
    <div className="layout-container">
      <motion.div
        className="phone-frame-wrapper"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
      >
        <img src={iphoneLayout} alt="iPhone Frame" className="phone-frame-image" />

        <main className="app-content">
          {children}
        </main>
      </motion.div>

      <style>{`
        :root {
          --frame-width: 600px;
          --frame-height: 920px;
          --content-width: 400px;
          --content-height: 870px;
          --content-margin-top: 10px;
          --content-margin-left: -20px;
        }

        * {
          -webkit-user-select: none;
          -moz-user-select: none;
          -ms-user-select: none;
          user-select: none;
          -webkit-touch-callout: none;
        }

        input, textarea {
          -webkit-user-select: text;
          user-select: text;
        }

        .layout-container {
          width: 100vw;
          height: 100vh;
          display: flex;
          justify-content: center;
          align-items: center;
          background: #000;
        }

        .phone-frame-wrapper {
          position: relative;
          width: var(--frame-width);
          height: var(--frame-height);
          display: flex;
          justify-content: center;
          align-items: center;
        }

        .phone-frame-image {
          position: absolute;
          width: 560px;
          height: 104%;
          top: -2%;
          left: 50%;
          padding-left: 0px;
          transform: translateX(-50%);
          pointer-events: none;
          z-index: 10;
        }

        @media (max-width: 450px) {
          .phone-frame-wrapper {
            width: 100%;
            height: 100%;
          }
          
          .phone-frame-image {
            display: none;
          }
        }

        .app-content {
          position: relative;
          width: var(--content-width);
          height: var(--content-height);
          background: var(--bg-primary);
          overflow-y: auto;
          overflow-x: hidden;
          border-radius: 42px;
          z-index: 1;
          margin-top: var(--content-margin-top);
          margin-left: var(--content-margin-left);
        }

        @media (max-width: 450px) {
          .app-content {
            width: 100%;
            height: 100%;
            max-width: 100%;
            max-height: 100%;
            border-radius: 0;
            margin: 0; /* Reset margins for mobile */
          }
        }
      `}</style>
    </div>
  );
};

export default Layout;
