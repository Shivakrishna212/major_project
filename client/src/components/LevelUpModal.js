import React, { useEffect, useState } from 'react';
import Confetti from 'react-confetti';
import '../App.css';

const LevelUpModal = ({ newLevel, onClose }) => {
  const [windowSize, setWindowSize] = useState({ width: window.innerWidth, height: window.innerHeight });

  useEffect(() => {
    const handleResize = () => setWindowSize({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className="modal-overlay">
      <Confetti width={windowSize.width} height={windowSize.height} recycle={false} numberOfPieces={500} />
      
      <div className="level-up-card fade-in">
        <div style={{ fontSize: '4rem', marginBottom: '10px' }}>🏆</div>
        <h1 className="gradient-text" style={{ fontSize: '2.5rem', margin: '0' }}>LEVEL UP!</h1>
        <p style={{ fontSize: '1.2rem', color: '#555', marginTop: '10px' }}>
          You are now a <strong>Level {newLevel} Scholar</strong>
        </p>
        <button className="primary-btn" onClick={onClose} style={{ marginTop: '20px', fontSize: '1.1rem' }}>
          Awesome!
        </button>
      </div>
    </div>
  );
};

export default LevelUpModal;