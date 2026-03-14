"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

export interface ChatEntry {
  question: string;
  answer: string;
}

type QuestionPanelProps = {
  documentReady: boolean;
  onAsk(question: string, onChunk: (t: string) => void): Promise<void>;
};

export function QuestionPanel({ documentReady, onAsk }: QuestionPanelProps) {
  const [question, setQuestion] = useState("");
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [streamingAnswer, setStreamingAnswer] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<ChatEntry[]>([]);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to latest
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, streamingAnswer]);

  const handleAsk = async () => {
    const q = question.trim();
    if (!q || isAsking) return;

    setCurrentQuestion(q);
    setQuestion("");
    setStreamingAnswer("");
    setError(null);
    setIsAsking(true);

    let full = "";
    try {
      await onAsk(q, (token) => {
        full += token;
        setStreamingAnswer(full);
      });
      setHistory((prev) => [...prev, { question: q, answer: full }]);
      setStreamingAnswer("");
      setCurrentQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get answer");
      setStreamingAnswer("");
    } finally {
      setIsAsking(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleAsk();
    }
  };

  if (!documentReady) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[200px] gap-3 text-center">
        <span className="text-3xl">💬</span>
        <p className="text-xs font-mono text-white/40">
          Upload a document first to ask questions.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Chat history */}
      {history.length > 0 && (
        <div className="flex flex-col gap-4">
          {history.map((entry, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col gap-2 pb-4 border-b border-white/8"
            >
              <div className="flex items-start gap-2">
                <span className="text-xs mt-0.5">🧑</span>
                <div className="rounded-lg bg-white/8 border border-white/12 px-3 py-2 text-sm text-white/80 flex-1">
                  {entry.question}
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-xs mt-0.5">🤖</span>
                <div className="rounded-lg bg-white/[0.04] border border-white/10 px-3 py-2 text-sm leading-relaxed text-white/80 whitespace-pre-wrap break-words flex-1">
                  {entry.answer}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* In-flight streaming */}
      {isAsking && (
        <div className="flex flex-col gap-2">
          <div className="flex items-start gap-2">
            <span className="text-xs mt-0.5">🧑</span>
            <div className="rounded-lg bg-white/8 border border-white/12 px-3 py-2 text-sm text-white/80 flex-1">
              {currentQuestion}
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-xs mt-0.5">🤖</span>
            <div className="rounded-lg bg-white/[0.04] border border-white/10 px-3 py-2 text-sm leading-relaxed text-white/80 whitespace-pre-wrap break-words flex-1">
              {streamingAnswer || (
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
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="px-3 py-2 rounded-lg border border-red-400/30 bg-red-400/10 text-red-400 text-xs font-mono">
          {error}
        </div>
      )}

      {/* Scroll anchor */}
      <div ref={bottomRef} />

      {/* Input row */}
      <div className="flex flex-col gap-2">
        <textarea
          className="w-full bg-white/[0.04] border border-white/10 focus:border-white/25 rounded-lg text-sm text-white/80 placeholder:text-white/25 px-3 py-2 outline-none resize-none font-mono transition-colors"
          rows={3}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isAsking}
          placeholder="Ask anything about this document… (Ctrl+Enter to send)"
        />
        <button
          className="self-start inline-flex items-center gap-2 px-4 py-2 rounded-md bg-white/10 border border-white/15 text-white/80 font-mono text-xs tracking-wider hover:bg-white/15 hover:border-white/25 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          onClick={handleAsk}
          disabled={isAsking || !question.trim()}
        >
          {isAsking ? (
            <>
              <div className="w-3 h-3 border border-white/30 border-t-white/70 rounded-full animate-spin" />
              Answering…
            </>
          ) : (
            <>💬 Ask question</>
          )}
        </button>
      </div>
    </div>
  );
}
