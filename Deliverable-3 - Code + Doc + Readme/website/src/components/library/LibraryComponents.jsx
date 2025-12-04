import React from 'react';
import { imgRectangle2, imgRectangle4, imgVector2, imgVector3 } from './svg-assets';
import AddLibraryIcon from '../../assets/icons/Screen-1/add-library-icon.svg';
import LogoIcon from '../../assets/logo.svg';

export function NewLibraryButton({ className = '', onClick }) {
  return (
    <div
      className={`new-library-btn ${className}`}
      onClick={onClick}
      style={{
        position: 'relative',
        width: '47px',
        height: '47px',
        cursor: 'pointer'
      }}
    >
      <div style={{
        position: 'absolute',
        inset: 0,
        backdropFilter: 'blur(2px)',
        background: '#101c28',
        border: '2px solid #232d38',
        borderRadius: '20px',
        overflow: 'hidden'
      }}>
        <div style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'absolute'
        }}>

          {/* Library icon SVG */}
          <div style={{
            position: 'absolute',
            left: '8px',
            top: '11px',
            width: '26px',
            height: '26px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <img src={AddLibraryIcon} alt="Add Library" style={{ width: '100%', height: '100%' }} />
          </div>
        </div>
      </div>
    </div>
  );
}

export function Logo({ className = '' }) {
  return (
    <div
      className={`logo ${className}`}
      style={{
        position: 'relative',
        height: '41px',
        width: 'auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px'
      }}
    >
      <img src={LogoIcon} alt="AURURA Logo" style={{ height: '100%', width: 'auto' }} />
      <p style={{
        fontFamily: "'SF Pro', -apple-system, sans-serif",
        fontWeight: 'bold',
        fontSize: '15px',
        color: 'white',
        margin: 0,
        letterSpacing: '1px'
      }}>
        AURORA
      </p>
    </div>
  );
}

export function StatusBar({ className = '' }) {
  return (
    <div
      className={`status-bar ${className}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '21px 16px 19px',
        width: '100%',
        gap: '154px'
      }}
    >
      {/* Time */}
      <div style={{
        flex: '1 1 0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        paddingTop: '2px'
      }}>
        <p style={{
          fontFamily: "'SF Pro', -apple-system, sans-serif",
          fontWeight: 600,
          fontSize: '17px',
          color: '#d9d9d9',
          textAlign: 'center',
          whiteSpace: 'pre',
          margin: 0,
          lineHeight: '22px'
        }}>
          9:41
        </p>
      </div>

      {/* Status icons */}
      <div style={{
        flex: '1 1 0',
        display: 'flex',
        gap: '7px',
        alignItems: 'center',
        justifyContent: 'flex-end',
        paddingTop: '1px'
      }}>
        {/* Cellular */}
        <svg width="20" height="13" viewBox="0 0 20 13" fill="none">
          <path fillRule="evenodd" clipRule="evenodd" d="M17.6 2.4c.88 0 1.6.72 1.6 1.6v6.4c0 .88-.72 1.6-1.6 1.6H17V2.4h.6zm-3.2 0V12H3.2V2.4h11.2zM1.6 2.4V12h-.8c-.88 0-1.6-.72-1.6-1.6V4c0-.88.72-1.6 1.6-1.6h.8z" fill="#D9D9D9" />
        </svg>
        {/* WiFi */}
        <svg width="18" height="13" viewBox="0 0 18 13" fill="none">
          <path d="M2.13 4.8c.3-.4.78-.64 1.29-.64h11.16c.51 0 .99.24 1.29.64l1.73 2.3a.8.8 0 01-.64 1.28H.64a.8.8 0 01-.64-1.28l1.73-2.3zm13.01 2.72l-.56-.75H3.42l-.56.75h12.28z" fill="#D9D9D9" />
        </svg>
        {/* Battery */}
        <svg width="28" height="13" viewBox="0 0 28 13" fill="none">
          <rect x="0.5" y="0.5" width="21" height="12" rx="2.5" stroke="#D9D9D9" strokeOpacity="0.35" />
          <path opacity="0.4" d="M23 4v5" stroke="#D9D9D9" />
          <rect x="2" y="2" width="18" height="9" rx="1.5" fill="#D9D9D9" />
        </svg>
      </div>
    </div>
  );
}

export function UtilityButtons({ className = '' }) {
  return (
    <div
      className={`utility-buttons ${className}`}
      style={{
        display: 'flex',
        gap: '8px',
        alignItems: 'center'
      }}
    >
      {/* Download */}
      <div style={{
        background: '#151d28',
        height: '32px',
        width: '45px',
        borderRadius: '10px',
        overflow: 'hidden',
        position: 'relative',
        cursor: 'pointer'
      }}>
        <div style={{
          position: 'absolute',
          left: '13px',
          top: '7px',
          width: '18px',
          height: '18px'
        }}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M9 3v9m0 0l3-3m-3 3L6 9m9 6H3" stroke="#D9D9D9" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>

      {/* Share */}
      <div style={{
        background: '#151d28',
        height: '32px',
        width: '45px',
        borderRadius: '10px',
        overflow: 'hidden',
        position: 'relative',
        cursor: 'pointer'
      }}>
        <div style={{
          position: 'absolute',
          left: '14px',
          top: '8px',
          width: '16px',
          height: '16px'
        }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M13 8.5l2-2-2-2M10 3L6 13M3 8.5l-2-2 2-2" stroke="#D9D9D9" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
      </div>

      {/* Delete */}
      <div style={{
        background: '#151d28',
        height: '32px',
        width: '45px',
        borderRadius: '10px',
        overflow: 'hidden',
        position: 'relative',
        cursor: 'pointer'
      }}>
        <div style={{
          position: 'absolute',
          left: '14px',
          top: '8px',
          width: '16px',
          height: '16px'
        }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 4h10M5 4v10h6V4M7 7v4M9 7v4" stroke="#D9D9D9" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
      </div>
    </div>
  );
}