import React from 'react';

interface InfoIconProps {
  tooltip: string;
}

export const InfoIcon: React.FC<InfoIconProps> = ({ tooltip }) => {
  return (
    <div className="info-icon-container">
      <span className="info-icon">ⓘ</span>
      <span className="tooltip">{tooltip}</span>
    </div>
  );
};
