import { useState, useCallback, useEffect } from 'react';
import { useInterval } from './useInterval';

export enum HealthState {
  HEALTHY = 'healthy',
  UNHEALTHY = 'unhealthy',
  DEGRADED = 'degraded'
}

export interface DaskHealth {
  status: 'healthy' | 'unhealthy';
  workers: number;
  scheduler: string;
}

export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  api: 'healthy' | 'unhealthy';
  dask: DaskHealth;
}

interface HealthStatus {
  lastChecked: Date;
  nextCheckIn: number;
  timeLeft: number;
  details: HealthResponse | null;
}

const HEALTHY_INTERVAL = 60000;
const UNHEALTHY_INTERVAL = 15000;

export const useHealthStatus = () => {
  const [status, setStatus] = useState<HealthStatus>({
    lastChecked: new Date(),
    nextCheckIn: HEALTHY_INTERVAL,
    timeLeft: HEALTHY_INTERVAL,
    details: null
  });

  const checkHealth = useCallback(async () => {
    try {
      const response = await fetch('/api/health', {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        }
      });
      
      if (!response.ok) {
        const unhealthyResponse: HealthResponse = {
          status: 'unhealthy',
          api: 'unhealthy',
          dask: {
            status: 'unhealthy',
            workers: 0,
            scheduler: ''
          }
        };
        
        setStatus({
          lastChecked: new Date(),
          nextCheckIn: UNHEALTHY_INTERVAL,
          timeLeft: UNHEALTHY_INTERVAL,
          details: unhealthyResponse
        });
        
        return false;
      }

      const data: HealthResponse = await response.json();
      const healthState = getHealthState(data);
      const nextInterval = healthState === HealthState.HEALTHY ? HEALTHY_INTERVAL : UNHEALTHY_INTERVAL;
      
      setStatus({
        lastChecked: new Date(),
        nextCheckIn: nextInterval,
        timeLeft: nextInterval,
        details: data
      });

      return healthState === HealthState.HEALTHY;
    } catch {
      const unhealthyResponse: HealthResponse = {
        status: 'unhealthy',
        api: 'unhealthy',
        dask: {
          status: 'unhealthy',
          workers: 0,
          scheduler: ''
        }
      };

      setStatus({
        lastChecked: new Date(),
        nextCheckIn: UNHEALTHY_INTERVAL,
        timeLeft: UNHEALTHY_INTERVAL,
        details: unhealthyResponse
      });
      return false;
    }
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setStatus(prev => ({
        ...prev,
        timeLeft: Math.max(0, prev.timeLeft - 1000)
      }));
    }, 1000);

    return () => clearInterval(timer);
  }, []);

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

  useInterval(() => {
    checkHealth();
  }, getHealthState(status.details) === HealthState.HEALTHY ? HEALTHY_INTERVAL : UNHEALTHY_INTERVAL);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const healthState = getHealthState(status.details);

  return {
    healthState,
    lastChecked: status.lastChecked,
    timeLeft: status.timeLeft,
    details: status.details,
    checkHealth
  };
};
