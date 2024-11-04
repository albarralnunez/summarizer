import React from 'react'

interface ErrorToastProps {
  error: string | null;
  showToast: boolean;
  onClose: () => void;
}

export const ErrorToast: React.FC<ErrorToastProps> = ({ error, showToast, onClose }) => {
  return (
    <div className={`error-toast-container ${showToast ? 'visible' : ''}`}>
      {showToast && error && (
        <div className="error-toast">
          {error}
          <button className="close-toast" onClick={onClose}></button>
        </div>
      )}
    </div>
  );
};
