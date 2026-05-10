"use client";

import { useState } from "react";
import Image from "next/image";
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
        <span className="text-3xl" aria-hidden>📄</span>
        <p className="text-xs font-mono text-white/40 max-w-[65ch] leading-relaxed">
          Upload a document first to use AI explanations.
        </p>
      </div>
    );
  }

  if (!selectedText) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[200px] gap-3 text-center px-4">
        <span className="text-3xl" aria-hidden>🔍</span>
        <p className="text-xs font-mono text-white/40 max-w-[65ch] leading-relaxed">
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
        <div className="text-sm text-white/60 border-l-2 border-white/20 pl-3 italic leading-[1.6] max-w-[65ch]">
          {selectedText.length > 300
            ? selectedText.slice(0, 300) + "…"
            : selectedText}
        </div>
      </div>

      {/* Action button */}
      <button
        type="button"
        className="self-start inline-flex items-center gap-2 min-h-[44px] px-4 py-2 rounded-md bg-white/10 border border-white/15 text-white/80 font-mono text-xs tracking-wider hover:bg-white/15 hover:border-white/25 transition-all disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 focus-visible:ring-offset-2 focus-visible:ring-offset-black cursor-pointer"
        onClick={onExplain}
        disabled={isExplaining}
        aria-busy={isExplaining}
        aria-label={isExplaining ? "Explaining selection" : "Explain selected text"}
      >
        {isExplaining ? (
          <>
            <div className="w-3 h-3 border border-white/30 border-t-white/70 rounded-full animate-spin" aria-hidden />
            Explaining…
          </>
        ) : (
          "Explain selection"
        )}
      </button>

      {/* Error */}
      {error && (
        <div role="alert" className="px-3 py-2 rounded-lg border border-red-400/30 bg-red-400/10 text-red-400 text-xs font-mono">
          {error}
        </div>
      )}

      {/* Streaming / completed explanation */}
      {(explanation || isExplaining) && (
        <div className="relative">
          <div className="flex items-center gap-2 mb-2">
            <span className="flex items-center justify-center w-7 h-7 rounded overflow-hidden bg-black border border-white/15 shrink-0">
              <Image src="/logo-new.png" alt="" width={28} height={28} className="object-contain w-5 h-5" />
            </span>
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">Explorion</span>
          </div>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm leading-[1.6] text-white/80 whitespace-pre-wrap break-words max-w-[65ch]"
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
              type="button"
              className="absolute top-2 right-2 min-h-[44px] min-w-[44px] flex items-center justify-center px-2 py-1 rounded text-[10px] font-mono text-white/40 hover:text-white/70 hover:bg-white/10 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 focus-visible:ring-inset cursor-pointer"
              onClick={handleCopy}
              title="Copy explanation"
              aria-label={copied ? "Copied to clipboard" : "Copy explanation"}
            >
              {copied ? "Copied" : "Copy"}
            </button>
          )}
        </div>
      )}
    </motion.div>
  );
}
