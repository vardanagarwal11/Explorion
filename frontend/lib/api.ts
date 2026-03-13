/**
 * API client for communicating with the Explorion backend.
 *
 * Supports toggling between mock data and real API via environment variable.
 */

import { DEMO_PAPER_IDS, getDemoPaper, MOCK_PAPER, MOCK_STATUS } from "./mock-data";
import type { Paper, Section } from "./types";

// Toggle between mock and real API
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

// Backend API base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// === Types matching backend schemas ===

export type JobStatus = "queued" | "processing" | "completed" | "failed";
export type VisualizationStatus = "pending" | "rendering" | "complete" | "failed";

export interface ProcessResponse {
  job_id: string;
  content_id: string;
  status: JobStatus;
  message: string;
}

export interface StatusResponse {
  job_id: string;
  content_id: string;
  content_type: string;
  status: JobStatus;
  progress: number; // 0.0 - 1.0
  current_step?: string;
  sections_completed: number;
  sections_total: number;
  steps_completed?: { name: string; status: string }[];
  error?: string;
  created_at: string;
  estimated_completion?: string;
}

export interface SectionResponse {
  id: string;
  title: string;
  content: string;
  summary?: string;
  level: number;
  order_index: number;
  section_type?: string;
  equations: string[];
  code_blocks?: string[];
  video_url?: string;
  subtitle_url?: string;
  audio_url?: string;
}

export interface VisualizationResponse {
  id: string;
  section_id: string;
  concept: string;
  video_url?: string;
  subtitle_url?: string;
  audio_url?: string;
  status: VisualizationStatus;
}

export interface PaperResponse {
  paper_id: string;
  title: string;
  authors: string[];
  abstract: string;
  pdf_url: string;
  html_url?: string;
  source_url?: string;
  content_type?: string;
  sections: SectionResponse[];
  visualizations: VisualizationResponse[];
  processed_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  services: Record<string, string>;
}

// === Helpers ===

/**
 * Resolve a video URL: absolute URLs pass through,
 * relative URLs get prefixed with API_BASE.
 */
function resolveMediaUrl(url: string | undefined | null): string | undefined {
  if (!url) return undefined;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `${API_BASE}${url}`;
}

// === API Functions ===

/**
 * Start processing an arXiv paper (legacy endpoint, used by /abs/ route).
 */
export async function processArxivPaper(arxivId: string): Promise<ProcessResponse> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 500));
    return {
      job_id: "mock-job-" + Date.now(),
      content_id: arxivId,
      status: "queued",
      message: "Processing started (mock mode)",
    };
  }

  const res = await fetch(`${API_BASE}/api/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ arxiv_id: arxivId }),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to start processing: ${res.status} - ${errorText}`);
  }

  return res.json();
}

/**
 * Poll the processing status of a job.
 */
export async function getProcessingStatus(jobId: string): Promise<StatusResponse> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    return {
      job_id: jobId,
      content_id: MOCK_STATUS.job_id,
      content_type: "research_paper",
      status: MOCK_STATUS.status as JobStatus,
      progress: Math.round(MOCK_STATUS.progress * 100),
      current_step: MOCK_STATUS.current_step,
      sections_completed: MOCK_STATUS.sections_completed,
      sections_total: MOCK_STATUS.sections_total,
      created_at: new Date().toISOString(),
    };
  }

  const res = await fetch(`${API_BASE}/api/status/${encodeURIComponent(jobId)}`);

  if (!res.ok) {
    if (res.status === 404) throw new Error(`Job not found: ${jobId}`);
    const errorText = await res.text();
    throw new Error(`Failed to get status: ${res.status} - ${errorText}`);
  }

  return res.json();
}

/**
 * Get a processed paper with all sections and visualizations.
 * Returns null if paper hasn't been processed yet (404).
 */
export async function getPaper(contentId: string): Promise<Paper | null> {
  // Demo paper fast path — always works, no backend needed
  const demoPaper = getDemoPaper(contentId);
  if (demoPaper) return demoPaper;

  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 400));
    return { ...MOCK_PAPER, paper_id: contentId };
  }

  const res = await fetch(`${API_BASE}/api/paper/${encodeURIComponent(contentId)}`);

  if (res.status === 404) return null;

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to get paper: ${res.status} - ${errorText}`);
  }

  const data: PaperResponse = await res.json();

  // Convert backend response to frontend Paper type
  const vizBySectionId = new Map<string, VisualizationResponse>();
  for (const viz of data.visualizations) {
    const existing = vizBySectionId.get(viz.section_id);
    if (!existing || (viz.status === "complete" && existing.status !== "complete")) {
      vizBySectionId.set(viz.section_id, viz);
    }
  }

  const sections: Section[] = data.sections.map((s) => {
    const viz = vizBySectionId.get(s.id);
    return {
      id: s.id,
      title: s.title,
      content: s.content,
      summary: s.summary || undefined,
      level: s.level,
      order_index: s.order_index,
      section_type: s.section_type,
      equations: s.equations,
      code_blocks: s.code_blocks || [],
      video_url: resolveMediaUrl(viz?.video_url || s.video_url),
      subtitle_url: resolveMediaUrl(viz?.subtitle_url || s.subtitle_url),
      audio_url: resolveMediaUrl(viz?.audio_url || s.audio_url),
    };
  });

  return {
    paper_id: data.paper_id,
    title: data.title,
    authors: data.authors,
    abstract: data.abstract,
    pdf_url: data.pdf_url,
    html_url: data.html_url,
    source_url: data.source_url,
    content_type: data.content_type as Paper["content_type"],
    sections,
  };
}

/**
 * Get the URL for a video by ID.
 */
export function getVideoUrl(videoId: string): string {
  if (USE_MOCK) {
    return "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4";
  }
  return `${API_BASE}/api/video/${encodeURIComponent(videoId)}`;
}

/**
 * Check the health of the backend API.
 */
export async function checkHealth(): Promise<HealthResponse> {
  if (USE_MOCK) {
    return {
      status: "healthy",
      version: "mock",
      services: { database: "mock", manim: "mock", redis: "mock" },
    };
  }

  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

/**
 * Convert StatusResponse (backend) to ProcessingStatus (frontend).
 */
export function toProcessingStatus(response: StatusResponse) {
  return {
    job_id: response.job_id,
    status: response.status,
    progress: response.progress,
    sections_completed: response.sections_completed,
    sections_total: response.sections_total,
    current_step: response.current_step,
    error: response.error,
  };
}
