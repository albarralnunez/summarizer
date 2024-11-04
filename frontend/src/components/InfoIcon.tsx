import React, { useState } from 'react';

interface InfoIconProps {
  tooltip: string;
}

export const InfoIcon: React.FC<InfoIconProps> = ({ tooltip }) => {
  const [isTooltipVisible, setIsTooltipVisible] = useState(false);

  return (
    <div 
      className="info-icon-container"
      onMouseEnter={() => setIsTooltipVisible(true)}
      onMouseLeave={() => setIsTooltipVisible(false)}
    >
      <svg 
        className="info-icon" 
        width="16" 
        height="16" 
        viewBox="0 0 16 16"
      >
        <circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" strokeWidth="1.5"/>
        <text x="8" y="12" textAnchor="middle" fontSize="10" fill="currentColor">i</text>
      </svg>
      {isTooltipVisible && (
        <div className="tooltip">
          {tooltip}
        </div>
      )}
    </div>
  );
};
