import { useEffect, useRef } from 'react';

export const useInterval = (callback: () => void | Promise<void>, delay: number) => {
  const savedCallback = useRef<() => void | Promise<void>>();

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    const tick = async () => {
      if (savedCallback.current) {
        await savedCallback.current();
      }
    };

    if (delay !== null) {
      const id = setInterval(tick, delay);
      return () => clearInterval(id);
    }
  }, [delay]);
};
