import React from 'react';
import { motion } from 'framer-motion';
import LogoIcon from '../assets/logo.svg';

const SplashScreen = () => {
    return (
        <motion.div
            className="splash-screen"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                background: '#000',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 9999
            }}
        >
            <motion.div
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '20px'
                }}
            >
                <div style={{
                    position: 'relative',
                    width: '100px',
                    height: '100px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                }}>
                    <img
                        src={LogoIcon}
                        alt="AURORA Logo"
                        style={{
                            width: '80px',
                            height: '80px',
                            position: 'relative',
                            zIndex: 1
                        }}
                    />
                </div>

                <motion.h1
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.3, duration: 0.5 }}
                    style={{
                        color: 'white',
                        fontSize: '24px',
                        fontWeight: '600',
                        letterSpacing: '1px',
                        margin: 0,
                        fontFamily: 'Inter, sans-serif'
                    }}
                >
                    AURORA
                </motion.h1>
            </motion.div>
        </motion.div>
    );
};

export default SplashScreen;