import React, { useState } from 'react';
import { HealthResponse, HealthState } from '../hooks/useHealthStatus';

interface HealthStatusProps {
  checkHealth: () => Promise<boolean>;
  timeLeft: number;
  details: HealthResponse | null;
}

export const HealthStatus: React.FC<HealthStatusProps> = ({ 
  checkHealth, 
  timeLeft,
  details 
}) => {
  const [showDetails, setShowDetails] = useState(false);

  const getHealthState = (details: HealthResponse | null): HealthState => {
    if (!details) return HealthState.UNHEALTHY;
    
    const allHealthy = details.status === 'healthy' && 
                      details.api === 'healthy' && 
                      details.dask.status === 'healthy';
    
    const allUnhealthy = details.status === 'unhealthy' && 
                        details.api === 'unhealthy' && 
                        details.dask.status === 'unhealthy';
    
    if (allHealthy) return HealthState.HEALTHY;
    if (allUnhealthy) return HealthState.UNHEALTHY;
    return HealthState.DEGRADED;
  };

  const healthState = getHealthState(details);

  if (!details) return null;

  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    return `${Math.floor(seconds / 60)}:${(seconds % 60).toString().padStart(2, '0')}`;
  };

  const getStatusColor = (status: 'healthy' | 'unhealthy') => {
    return status === 'healthy' ? 'var(--health-status-healthy-color)' : 'var(--health-status-unhealthy-color)';
  };

  const getHealthIcon = (state: HealthState) => {
    switch (state) {
      case HealthState.HEALTHY:
        return '✓';
      case HealthState.DEGRADED:
        return '!';
      case HealthState.UNHEALTHY:
        return '✗';
    }
  };

  return (
    <div 
      className="health-status-wrapper"
      onMouseEnter={() => setShowDetails(true)}
      onMouseLeave={() => setShowDetails(false)}
    >
      <div className="health-status-container">
        <span className="next-check-timer">
          {formatTime(timeLeft)}
        </span>
        <button 
          className="refresh-button"
          onClick={(e) => {
            e.stopPropagation();
            checkHealth();
          }}
          aria-label="Refresh health status"
        >
          ↻
        </button>
        <span 
          className={`health-status-icon ${healthState.toLowerCase()}`}
          role="status"
          aria-label={`System is ${healthState.toLowerCase()}`}
        >
          {getHealthIcon(healthState)}
        </span>
      </div>
      {showDetails && details && (
        <div className="health-status-details">
          <div 
            className="status-item"
            style={{ color: getStatusColor(details.status) }}
          >
            Overall: {details.status}
          </div>
          <div 
            className="status-item"
            style={{ color: getStatusColor(details.api) }}
          >
            API: {details.api}
          </div>
          <div 
            className="status-item"
            style={{ color: getStatusColor(details.dask.status) }}
          >
            Dask: {details.dask.status}
          </div>
        </div>
      )}
    </div>
  );
};
