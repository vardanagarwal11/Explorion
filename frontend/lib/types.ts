export type ContentType = "research_paper" | "github_repo" | "technical_content";

export type ProcessingStatus = {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress: number; // 0.0 - 1.0
  sections_completed: number;
  sections_total: number;
  current_step?: string;
  error?: string;
};

export type Paper = {
  paper_id: string;
  title: string;
  authors: string[];
  abstract: string;
  pdf_url?: string;
  html_url?: string;
  source_url?: string;
  content_type?: ContentType;
  sections: Section[];
  visualizations?: Visualization[];
};

export type Section = {
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
};

export type Visualization = {
  id: string;
  section_id: string;
  concept: string;
  video_url?: string;
  subtitle_url?: string;
  audio_url?: string;
  status: "pending" | "rendering" | "complete" | "failed";
};
