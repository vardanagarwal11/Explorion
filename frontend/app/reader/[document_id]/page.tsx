"use client";

import { useCallback, useEffect, useState, use } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";

import { PdfViewer } from "@/components/doc-reader/PdfViewer";
import { ExplainPopover } from "@/components/doc-reader/ExplainPopover";
import { QuestionPanel } from "@/components/doc-reader/QuestionPanel";
import { getPdfUrl, streamPost } from "@/lib/doc-reader-api";

type AiTab = "explain" | "ask";

export default function DocumentReaderPage({
  params,
}: {
  params: Promise<{ document_id: string }>;
}) {
  const { document_id } = use(params);

  // Active document
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  // Highlight/explain
  const [selectedText, setSelectedText] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [isExplaining, setIsExplaining] = useState(false);
  const [explainError, setExplainError] = useState<string | null>(null);

  // AI tab
  const [aiTab, setAiTab] = useState<AiTab>("explain");

  useEffect(() => {
    setPdfUrl(getPdfUrl(document_id));
  }, [document_id]);

  // Text selection
  const handleSelectionChange = useCallback((text: string | null) => {
    setSelectedText(text);
    setExplanation(null);
    setExplainError(null);
    if (text) setAiTab("explain");
  }, []);

  // Explain (streaming)
  const handleExplain = async () => {
    if (!document_id || !selectedText) return;
    setIsExplaining(true);
    setExplainError(null);
    setExplanation("");
    try {
      await streamPost(
        "/explain/stream",
        { document_id, selected_text: selectedText },
        (token) => setExplanation((prev) => (prev ?? "") + token),
      );
    } catch (err) {
      setExplainError(
        err instanceof Error ? err.message : "Explanation failed",
      );
      setExplanation(null);
    } finally {
      setIsExplaining(false);
    }
  };

  // Ask (streaming)
  const handleAsk = async (
    question: string,
    onChunk: (t: string) => void,
  ) => {
    if (!document_id) throw new Error("No document selected");
    await streamPost(
      "/ask/stream",
      { document_id, question },
      onChunk,
    );
  };

  return (
    <div className="h-screen flex flex-col bg-black text-white font-mono overflow-hidden">
      {/* Top Header */}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex-shrink-0 border-b border-white/10 bg-black"
      >
        <div className="flex items-center justify-between px-4 lg:px-6 py-3">
          <div className="flex items-center gap-3">
            <Link
              href="/reader"
              className="flex items-center text-white/40 hover:text-white/70 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div className="w-px h-4 bg-white/15" />
            <Image
              src="/logo-new.png"
              alt="Explorion"
              width={32}
              height={32}
              className="object-contain drop-shadow-[0_0_6px_rgba(255,255,255,0.4)]"
            />
            <span className="text-sm font-bold tracking-widest italic transform -skew-x-12 text-white/90">
              Explorion
            </span>
            <span className="text-[10px] uppercase tracking-wider text-white/30">
              Document Reader
            </span>
          </div>

          <div className="hidden lg:flex items-center gap-3 text-[10px] text-white/40">
            <span>SYS.STATUS: ONLINE</span>
            <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse shadow-[0_0_6px_rgba(74,222,128,0.5)]" />
          </div>
        </div>
      </motion.header>

      {/* Main split view */}
      <div className="flex-1 flex overflow-hidden">
        {/* PDF Viewer */}
        <div className="flex-[3] border-r border-white/10 overflow-hidden">
          {pdfUrl ? (
            <PdfViewer
              fileUrl={pdfUrl}
              onSelectionChange={handleSelectionChange}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-white/30">
              <div className="text-5xl">📖</div>
              <p className="text-xs font-mono">Loading document…</p>
            </div>
          )}
        </div>

        {/* AI Sidebar */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="flex-[2] max-w-[420px] min-w-[320px] flex flex-col overflow-hidden bg-black/50"
        >
          {/* Tabs */}
          <div className="flex border-b border-white/10 flex-shrink-0">
            <button
              className={`flex-1 py-3 text-center text-xs tracking-wider transition-all border-b-2 ${
                aiTab === "explain"
                  ? "text-white/80 border-white/40 bg-white/[0.04]"
                  : "text-white/30 border-transparent hover:text-white/50 hover:bg-white/[0.02]"
              }`}
              onClick={() => setAiTab("explain")}
            >
              ✨ EXPLAIN
            </button>
            <button
              className={`flex-1 py-3 text-center text-xs tracking-wider transition-all border-b-2 ${
                aiTab === "ask"
                  ? "text-white/80 border-white/40 bg-white/[0.04]"
                  : "text-white/30 border-transparent hover:text-white/50 hover:bg-white/[0.02]"
              }`}
              onClick={() => setAiTab("ask")}
            >
              💬 ASK
            </button>
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto p-4">
            {aiTab === "explain" && (
              <ExplainPopover
                selectedText={selectedText}
                explanation={explanation}
                isExplaining={isExplaining}
                error={explainError}
                onExplain={handleExplain}
                documentReady={true}
              />
            )}
            {aiTab === "ask" && (
              <QuestionPanel documentReady={true} onAsk={handleAsk} />
            )}
          </div>
        </motion.div>
      </div>

      {/* Bottom status bar */}
      <div className="flex-shrink-0 border-t border-white/10 px-4 py-1.5 flex items-center justify-between">
        <div className="flex items-center gap-3 text-[9px] text-white/30">
          <span>ENGINE.ACTIVE</span>
          <div className="flex gap-0.5">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="w-0.5 bg-white/20 animate-pulse"
                style={{
                  height: `${Math.random() * 8 + 3}px`,
                  animationDelay: `${i * 0.1}s`,
                }}
              />
            ))}
          </div>
          <span>DOCREADER.V1</span>
        </div>
        <div className="flex items-center gap-3 text-[9px] text-white/30">
          <span>◐ STREAMING</span>
          <div className="flex gap-1">
            <div className="w-1 h-1 bg-white/40 rounded-full animate-pulse" />
            <div
              className="w-1 h-1 bg-white/25 rounded-full animate-pulse"
              style={{ animationDelay: "0.2s" }}
            />
            <div
              className="w-1 h-1 bg-white/15 rounded-full animate-pulse"
              style={{ animationDelay: "0.4s" }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
