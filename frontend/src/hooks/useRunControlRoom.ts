import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import { ControlRoomSnapshotResponse } from '../api/types';

export interface UseRunControlRoomReturn {
  snapshot: ControlRoomSnapshotResponse | null;
  loading: boolean;
  error: string | null;
  isPolling: boolean;
  lastUpdated: Date | null;
  isStale: boolean;
  refresh: () => Promise<void>;
}

export function useRunControlRoom(runId: number | null): UseRunControlRoomReturn {
  const [snapshot, setSnapshot] = useState<ControlRoomSnapshotResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isStale, setIsStale] = useState<boolean>(false);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef<boolean>(true);

  // Clear timer helper
  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  // Fetch snapshot function
  const fetchSnapshot = useCallback(
    async (isManualRefresh = false) => {
      if (!runId) return;

      if (!snapshot && !isManualRefresh) {
        setLoading(true);
      }

      try {
        const data = await api.getControlRoomSnapshot(runId);
        if (!mountedRef.current) return;

        setSnapshot(data);
        setError(null);
        setIsStale(false);
        setLastUpdated(new Date());

        // Determine if polling should continue
        const status = data.run.status;
        const orchState = data.orchestration?.state;
        const isTerminal =
          status === 'COMPLETED' ||
          status === 'FAILED' ||
          status === 'CANCELLED' ||
          orchState === 'COMPLETED' ||
          orchState === 'FAILED' ||
          orchState === 'CANCELLED';

        const isPaused = status === 'PAUSED' || orchState === 'PAUSED';

        clearTimer();

        if (isTerminal) {
          setIsPolling(false);
          return;
        }

        // Active run polls every 3s, paused run polls every 6s
        setIsPolling(true);
        const interval = isPaused ? 6000 : 3000;
        timerRef.current = setTimeout(() => {
          if (mountedRef.current) {
            fetchSnapshot(false);
          }
        }, interval);
      } catch (err: unknown) {
        if (!mountedRef.current) return;
        const msg = err instanceof Error ? err.message : 'Failed to fetch control room snapshot';

        // If we already have snapshot, maintain it but mark stale
        if (snapshot) {
          setIsStale(true);
        } else {
          setError(msg);
        }

        // Retry polling after 5s even on temporary failure if not terminal
        clearTimer();
        timerRef.current = setTimeout(() => {
          if (mountedRef.current) {
            fetchSnapshot(false);
          }
        }, 5000);
      } finally {
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    },
    [runId, snapshot, clearTimer]
  );

  // Manual refresh
  const refresh = useCallback(async () => {
    clearTimer();
    await fetchSnapshot(true);
  }, [fetchSnapshot, clearTimer]);

  // Handle runId change
  useEffect(() => {
    mountedRef.current = true;
    setSnapshot(null);
    setError(null);
    setIsStale(false);
    clearTimer();

    if (runId) {
      fetchSnapshot(false);
    } else {
      setLoading(false);
      setIsPolling(false);
    }

    return () => {
      mountedRef.current = false;
      clearTimer();
    };
  }, [runId]);

  return {
    snapshot,
    loading,
    error,
    isPolling,
    lastUpdated,
    isStale,
    refresh,
  };
}
