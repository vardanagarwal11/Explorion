"use client";

import { useState } from "react";
import { motion } from "framer-motion";

type ExplainPopoverProps = {
  selectedText: string | null;
  explanation: string | null;
  isExplaining: boolean;
  error: string | null;
  onExplain(): void;
  documentReady: boolean;
};

export function ExplainPopover({
  selectedText,
  explanation,
  isExplaining,
  error,
  onExplain,
  documentReady,
}: ExplainPopoverProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!explanation) return;
    navigator.clipboard.writeText(explanation).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };

  if (!documentReady) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[200px] gap-3 text-center">
        <span className="text-3xl">📄</span>
        <p className="text-xs font-mono text-white/40">
          Upload a document first to use AI explanations.
        </p>
      </div>
    );
  }

  if (!selectedText) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[200px] gap-3 text-center px-4">
        <span className="text-3xl">🔍</span>
        <p className="text-xs font-mono text-white/40">
          Select any text in the PDF viewer to get an AI-powered explanation.
        </p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col gap-3"
    >
      {/* Selected text card */}
      <div className="rounded-lg border border-white/10 bg-white/[0.04] p-3">
        <div className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-2">
          Selected text
        </div>
        <div className="text-sm text-white/60 border-l-2 border-white/20 pl-3 italic leading-relaxed">
          {selectedText.length > 300
            ? selectedText.slice(0, 300) + "…"
            : selectedText}
        </div>
      </div>

      {/* Action button */}
      <button
        className="self-start inline-flex items-center gap-2 px-4 py-2 rounded-md bg-white/10 border border-white/15 text-white/80 font-mono text-xs tracking-wider hover:bg-white/15 hover:border-white/25 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        onClick={onExplain}
        disabled={isExplaining}
      >
        {isExplaining ? (
          <>
            <div className="w-3 h-3 border border-white/30 border-t-white/70 rounded-full animate-spin" />
            Explaining…
          </>
        ) : (
          <>✨ Explain selection</>
        )}
      </button>

      {/* Error */}
      {error && (
        <div className="px-3 py-2 rounded-lg border border-red-400/30 bg-red-400/10 text-red-400 text-xs font-mono">
          {error}
        </div>
      )}

      {/* Streaming / completed explanation */}
      {(explanation || isExplaining) && (
        <div className="relative">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm leading-relaxed text-white/80 whitespace-pre-wrap break-words"
          >
            {explanation ? (
              explanation
            ) : (
              <div className="flex gap-1 items-center">
                <span className="w-1.5 h-1.5 rounded-full bg-white/40 animate-pulse" />
                <span
                  className="w-1.5 h-1.5 rounded-full bg-white/40 animate-pulse"
                  style={{ animationDelay: "0.2s" }}
                />
                <span
                  className="w-1.5 h-1.5 rounded-full bg-white/40 animate-pulse"
                  style={{ animationDelay: "0.4s" }}
                />
              </div>
            )}
          </motion.div>
          {explanation && (
            <button
              className="absolute top-2 right-2 px-2 py-1 rounded text-[10px] font-mono text-white/40 hover:text-white/70 hover:bg-white/10 transition-all"
              onClick={handleCopy}
              title="Copy explanation"
            >
              {copied ? "✓ Copied" : "Copy"}
            </button>
          )}
        </div>
      )}
    </motion.div>
  );
}
