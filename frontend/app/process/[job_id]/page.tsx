"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { Loader2, CheckCircle2, ChevronRight, AlertCircle } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface StepInfo {
  name: string;
  status: "pending" | "in_progress" | "complete";
}

interface StatusResponse {
  job_id: string;
  content_id: string;
  content_type: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress: number;
  current_step: string;
  sections_completed: number;
  sections_total: number;
  steps_completed: StepInfo[];
  error?: string;
}

const STEP_LABELS: Record<string, string> = {
  ingest_content: "Content Ingestion",
  analyze_sections: "Structural Analysis",
  generate_visualizations: "Animation Synthesis",
  render_videos: "Final Render Compilation"
};

export default function ProcessPage({ params }: { params: Promise<{ job_id: string }> }) {
  const router = useRouter();
  const unwrappedParams = use(params);
  const [statusObj, setStatusObj] = useState<StatusResponse | null>(null);
  const [errorObj, setErrorObj] = useState<string | null>(null);

  useEffect(() => {
    let interval: NodeJS.Timeout;

    const pollStatus = async () => {
      try {
        const res = await fetch(`${API_URL}/api/status/${unwrappedParams.job_id}`);
        if (!res.ok) throw new Error("Failed to fetch status");
        const data: StatusResponse = await res.json();

        setStatusObj(data);

        if (data.status === "completed") {
          clearInterval(interval);
          setTimeout(() => {
            router.push(`/result/${encodeURIComponent(data.content_id)}`);
          }, 1500);
        } else if (data.status === "failed") {
          clearInterval(interval);
          setErrorObj(data.error || "An unknown error occurred during generation.");
        }
      } catch (err) {
        console.warn(err);
      }
    };

    pollStatus();
    interval = setInterval(pollStatus, 3000);
    return () => clearInterval(interval);
  }, [unwrappedParams.job_id, router]);

  const progressPercent = Math.round((statusObj?.progress || 0) * 100);

  return (
    <main className="min-h-screen bg-black flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Background Starfield */}
      <div className="absolute inset-0 w-full h-full opacity-30 stars-bg" />

      <div className="z-10 w-full max-w-2xl bg-black/40 backdrop-blur-xl border border-white/20 p-8 pt-12 relative shadow-[0_0_50px_rgba(255,255,255,0.05)]">
        {/* Frame Ornaments */}
        <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-white/40" />
        <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-white/40" />
        <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-white/40" />
        <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-white/40" />

        {/* Title & Progress Header */}
        <div className="mb-10 text-center">
          <div className="flex items-center justify-center gap-2 mb-4 opacity-60">
            <div className="w-8 h-px bg-white/50" />
            <span className="text-white text-[10px] font-mono tracking-widest uppercase">
              {statusObj?.status === "completed" ? "SYSTEM.READY" :
                statusObj?.status === "failed" ? "SYSTEM.ERROR" :
                  "PROCESSING.SEQUENCE"}
            </span>
            <div className="w-8 h-px bg-white/50" />
          </div>

          <h1 className="text-2xl md:text-4xl font-mono text-white tracking-widest uppercase mb-6">
            {statusObj?.status === "completed" ? "Sequence Complete" :
              statusObj?.status === "failed" ? "Sequence Halted" :
                "Synthesizing"}
          </h1>

          {/* Master Progress Bar */}
          <div className="relative h-2 w-full bg-white/5 overflow-hidden">
            <div
              className="absolute top-0 left-0 h-full bg-white transition-all duration-1000 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
            {statusObj?.status === "processing" && (
              <div className="absolute top-0 left-0 h-full w-20 bg-gradient-to-r from-transparent via-white/50 to-transparent animate-pulse" />
            )}
          </div>
          <p className="text-right text-[10px] font-mono text-white/40 mt-2">
            {progressPercent}%
          </p>
        </div>

        {/* Status Stepper */}
        {errorObj ? (
          <div className="border border-red-500/20 bg-red-500/10 p-4 font-mono text-sm text-red-400 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{errorObj}</span>
          </div>
        ) : (
          <div className="space-y-6">
            {statusObj?.steps_completed?.map((step, idx) => {
              const isActive = step.status === "in_progress";
              const isPast = step.status === "complete";
              const isPending = step.status === "pending";

              return (
                <div key={idx} className="flex items-start gap-4">
                  <div className="flex flex-col items-center mt-0.5 relative pt-1">
                    {isPast ? (
                      <CheckCircle2 className="w-5 h-5 text-white/80" />
                    ) : isActive ? (
                      <Loader2 className="w-5 h-5 text-white animate-spin" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border border-white/20" />
                    )}

                    {statusObj && idx < (statusObj.steps_completed.length - 1) && (
                      <div className={`w-px h-8 my-1 ${isPast ? "bg-white/40" : "bg-white/10"}`} />
                    )}
                  </div>

                  <div className={`flex-1 ${isPending ? "opacity-30" :
                    isPast ? "opacity-70" :
                      "opacity-100"
                    }`}>
                    <div className="flex items-center gap-2">
                      <h3 className="font-mono text-sm tracking-wider text-white uppercase">
                        {STEP_LABELS[step.name] || step.name.replace(/_/g, " ")}
                      </h3>
                      {isActive && (
                        <span className="flex h-2 w-2 relative ml-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white/60 opacity-75" />
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-white" />
                        </span>
                      )}
                    </div>
                    {isActive && statusObj?.current_step && (
                      <p className="text-xs text-white/50 font-mono mt-2 animate-pulse flex items-center gap-1">
                        <ChevronRight className="w-3 h-3" />
                        {statusObj.current_step}
                      </p>
                    )}
                    {(step.name === "analyze_sections" || step.name === "generate_visualizations" || step.name === "render_videos") && isActive && statusObj && statusObj.sections_total > 0 && (
                      <p className="text-[10px] text-white/40 font-mono mt-1">
                        [{statusObj.sections_completed} / {statusObj.sections_total} modules processed]
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
