"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getProcessingStatus,
  toProcessingStatus,
  type StatusResponse,
} from "@/lib/api";
import type { ProcessingStatus } from "@/lib/types";

type ProcessingState =
  | { status: "idle" }
  | { status: "polling"; data: ProcessingStatus }
  | { status: "completed"; data: ProcessingStatus }
  | { status: "failed"; data: ProcessingStatus; error: string }
  | { status: "error"; error: string };

type UseProcessingStatusReturn = {
  /** Current processing state */
  state: ProcessingState;
  /** The processing status data if available */
  processingStatus: ProcessingStatus | null;
  /** Whether currently polling for status */
  isPolling: boolean;
  /** Whether processing is complete */
  isComplete: boolean;
  /** Whether processing failed */
  isFailed: boolean;
  /** Progress as a value between 0 and 1 */
  progress: number;
  /** Current processing step description */
  currentStep: string | null;
  /** Error message if any */
  error: string | null;
  /** Start polling for a job */
  startPolling: (jobId: string) => void;
  /** Stop polling */
  stopPolling: () => void;
  /** Reset state to idle */
  reset: () => void;
};

type UseProcessingStatusOptions = {
  /** Polling interval in milliseconds (default: 2000) */
  pollInterval?: number;
  /** Maximum polling attempts before giving up (default: 300 = 10 minutes at 2s interval) */
  maxAttempts?: number;
  /** Callback when processing completes */
  onComplete?: (status: ProcessingStatus) => void;
  /** Callback when processing fails */
  onFailed?: (status: ProcessingStatus, error: string) => void;
  /** Callback on each status update */
  onStatusUpdate?: (status: ProcessingStatus) => void;
  /** Callback on polling error */
  onError?: (error: string) => void;
};

/**
 * Hook for polling the processing status of a paper.
 *
 * @param options - Configuration options
 *
 * @example
 * const { startPolling, processingStatus, progress, isComplete } = useProcessingStatus({
 *   onComplete: (status) => {
 *     console.log("Processing complete!");
 *     refetchPaper();
 *   },
 * });
 *
 * // Start polling when we get a job ID
 * const handleStartProcessing = async () => {
 *   const response = await processArxivPaper(arxivId);
 *   startPolling(response.job_id);
 * };
 */
export function useProcessingStatus(
  options: UseProcessingStatusOptions = {}
): UseProcessingStatusReturn {
  const {
    pollInterval = 2000,
    maxAttempts = 300,
    onComplete,
    onFailed,
    onStatusUpdate,
    onError,
  } = options;

  const [state, setState] = useState<ProcessingState>({ status: "idle" });
  const [jobId, setJobId] = useState<string | null>(null);

  const attemptCountRef = useRef(0);
  const pollingRef = useRef(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    pollingRef.current = false;
  }, []);

  // Poll function
  const poll = useCallback(async () => {
    if (!jobId || !pollingRef.current) return;

    attemptCountRef.current += 1;

    // Check max attempts
    if (attemptCountRef.current > maxAttempts) {
      cleanup();
      const error = "Processing timed out. Please try again.";
      setState({ status: "error", error });
      onError?.(error);
      return;
    }

    try {
      const response: StatusResponse = await getProcessingStatus(jobId);
      const status = toProcessingStatus(response);

      onStatusUpdate?.(status);

      if (response.status === "completed") {
        cleanup();
        setState({ status: "completed", data: status });
        onComplete?.(status);
      } else if (response.status === "failed") {
        cleanup();
        const error = response.error || "Processing failed";
        setState({ status: "failed", data: status, error });
        onFailed?.(status, error);
      } else {
        setState({ status: "polling", data: status });
      }
    } catch (err) {
      // On transient errors, continue polling (don't stop)
      console.error("Polling error:", err);

      // Only stop on repeated failures
      if (attemptCountRef.current % 5 === 0) {
        // Log warning every 5 failures
        console.warn(
          `Polling failed ${attemptCountRef.current} times for job ${jobId}`
        );
      }
    }
  }, [
    jobId,
    maxAttempts,
    cleanup,
    onComplete,
    onFailed,
    onStatusUpdate,
    onError,
  ]);

  // Start polling
  const startPolling = useCallback(
    (newJobId: string) => {
      cleanup();
      setJobId(newJobId);
      attemptCountRef.current = 0;
      pollingRef.current = true;

      // Set initial state
      setState({
        status: "polling",
        data: {
          job_id: newJobId,
          status: "queued",
          progress: 0,
          sections_completed: 0,
          sections_total: 0,
          current_step: "Starting...",
        },
      });

      // Start polling immediately, then at interval
      poll();
      intervalRef.current = setInterval(poll, pollInterval);
    },
    [cleanup, poll, pollInterval]
  );

  // Stop polling
  const stopPolling = useCallback(() => {
    cleanup();
  }, [cleanup]);

  // Reset state
  const reset = useCallback(() => {
    cleanup();
    setJobId(null);
    attemptCountRef.current = 0;
    setState({ status: "idle" });
  }, [cleanup]);

  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  // Derived state
  const processingStatus =
    state.status === "polling" ||
    state.status === "completed" ||
    state.status === "failed"
      ? state.data
      : null;

  const isPolling = state.status === "polling";
  const isComplete = state.status === "completed";
  const isFailed = state.status === "failed" || state.status === "error";
  const progress = processingStatus?.progress ?? 0;
  const currentStep = processingStatus?.current_step ?? null;
  const error =
    state.status === "failed" || state.status === "error"
      ? state.error
      : null;

  return {
    state,
    processingStatus,
    isPolling,
    isComplete,
    isFailed,
    progress,
    currentStep,
    error,
    startPolling,
    stopPolling,
    reset,
  };
}

/**
 * Hook that combines processing status with automatic paper refetch on completion.
 *
 * @example
 * const { startProcessing, progress, isProcessing } = useProcessPaper({
 *   arxivId: "1706.03762",
 *   onPaperReady: (paper) => {
 *     // Paper is ready to display
 *   },
 * });
 */
export function useProcessPaper(options: {
  arxivId: string;
  onPaperReady?: () => void;
  onError?: (error: string) => void;
}) {
  const { arxivId, onPaperReady, onError } = options;

  const { startPolling, processingStatus, isPolling, isComplete, progress } =
    useProcessingStatus({
      onComplete: () => {
        onPaperReady?.();
      },
      onFailed: (_, error) => {
        onError?.(error);
      },
      onError,
    });

  const startProcessing = useCallback(async () => {
    try {
      const { processArxivPaper } = await import("@/lib/api");
      const response = await processArxivPaper(arxivId);
      startPolling(response.job_id);
      return response;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to start processing";
      onError?.(message);
      return null;
    }
  }, [arxivId, startPolling, onError]);

  return {
    startProcessing,
    processingStatus,
    isProcessing: isPolling,
    isComplete,
    progress,
  };
}
