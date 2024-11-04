import React from 'react';

interface LoadingBarProps {
  progress: number;
  onCancel: () => void;
}

export const LoadingBar: React.FC<LoadingBarProps> = ({ progress, onCancel }) => {
  return (
    <div className="loading-bar-container">
      <div className="loading-bar" style={{ width: `${progress}%` }}></div>
      <button className="cancel-button" onClick={onCancel} aria-label="Cancel upload">✕</button>
    </div>
  );
};
