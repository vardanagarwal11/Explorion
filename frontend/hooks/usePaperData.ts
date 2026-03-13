"use client";

import { useCallback, useEffect, useState } from "react";
import { getPaper, processArxivPaper, type ProcessResponse } from "@/lib/api";
import type { Paper } from "@/lib/types";

type PaperDataState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "not_found"; arxivId: string }
  | { status: "ready"; paper: Paper }
  | { status: "error"; error: string };

type UsePaperDataReturn = {
  /** Current state of the paper data */
  state: PaperDataState;
  /** The paper data if loaded, otherwise null */
  paper: Paper | null;
  /** Whether the hook is currently loading */
  isLoading: boolean;
  /** Whether the paper is ready to display */
  isReady: boolean;
  /** Whether there was an error */
  isError: boolean;
  /** Error message if any */
  error: string | null;
  /** Refetch the paper data */
  refetch: () => Promise<void>;
  /** Start processing a new paper (returns job info) */
  startProcessing: () => Promise<ProcessResponse | null>;
};

type UsePaperDataOptions = {
  /** Whether to fetch automatically on mount (default: true) */
  autoFetch?: boolean;
  /** Callback when paper is successfully loaded */
  onSuccess?: (paper: Paper) => void;
  /** Callback when an error occurs */
  onError?: (error: string) => void;
  /** Callback when paper is not found (not yet processed) */
  onNotFound?: (arxivId: string) => void;
};

/**
 * Hook for fetching and managing paper data.
 *
 * @param arxivId - The arXiv ID of the paper to fetch
 * @param options - Configuration options
 *
 * @example
 * const { paper, isLoading, isReady, startProcessing } = usePaperData("1706.03762");
 *
 * if (isLoading) return <LoadingState />;
 * if (isReady) return <PaperView paper={paper} />;
 */
export function usePaperData(
  arxivId: string | null | undefined,
  options: UsePaperDataOptions = {}
): UsePaperDataReturn {
  const { autoFetch = true, onSuccess, onError, onNotFound } = options;

  const [state, setState] = useState<PaperDataState>({ status: "idle" });

  const fetchPaper = useCallback(async () => {
    if (!arxivId) {
      setState({ status: "error", error: "No arXiv ID provided" });
      return;
    }

    setState({ status: "loading" });

    try {
      const paper = await getPaper(arxivId);

      if (paper) {
        setState({ status: "ready", paper });
        onSuccess?.(paper);
      } else {
        setState({ status: "not_found", arxivId });
        onNotFound?.(arxivId);
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch paper";
      setState({ status: "error", error: message });
      onError?.(message);
    }
  }, [arxivId, onSuccess, onError, onNotFound]);

  const startProcessing = useCallback(async (): Promise<ProcessResponse | null> => {
    if (!arxivId) return null;

    try {
      const response = await processArxivPaper(arxivId);
      return response;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to start processing";
      setState({ status: "error", error: message });
      onError?.(message);
      return null;
    }
  }, [arxivId, onError]);

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch && arxivId) {
      fetchPaper();
    }
  }, [autoFetch, arxivId, fetchPaper]);

  // Derived state
  const paper = state.status === "ready" ? state.paper : null;
  const isLoading = state.status === "loading";
  const isReady = state.status === "ready";
  const isError = state.status === "error";
  const error = state.status === "error" ? state.error : null;

  return {
    state,
    paper,
    isLoading,
    isReady,
    isError,
    error,
    refetch: fetchPaper,
    startProcessing,
  };
}

/**
 * Hook that combines paper fetching with section navigation.
 *
 * @example
 * const { paper, sections, activeSection, scrollToSection } = usePaperWithSections("1706.03762");
 */
export function usePaperWithSections(arxivId: string | null | undefined) {
  const paperData = usePaperData(arxivId);
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);

  // Initialize active section when paper loads
  useEffect(() => {
    if (paperData.paper && paperData.paper.sections.length > 0) {
      setActiveSectionId(paperData.paper.sections[0].id);
    }
  }, [paperData.paper]);

  const sections = paperData.paper?.sections ?? [];

  const scrollToSection = useCallback((sectionId: string) => {
    const el = document.querySelector(`[data-section-id="${sectionId}"]`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveSectionId(sectionId);
    }
  }, []);

  const handleSectionActiveChange = useCallback(
    (sectionId: string, isActive: boolean) => {
      if (isActive) {
        setActiveSectionId(sectionId);
      }
    },
    []
  );

  return {
    ...paperData,
    sections,
    activeSectionId,
    setActiveSectionId,
    scrollToSection,
    handleSectionActiveChange,
  };
}
