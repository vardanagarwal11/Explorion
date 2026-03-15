"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

type PdfViewerProps = {
  fileUrl: string;
  onSelectionChange(selected: string | null): void;
};

export function PdfViewer({ fileUrl, onSelectionChange }: PdfViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Reset state when the file changes
  useEffect(() => {
    setNumPages(0);
    setCurrentPage(1);
    setLoading(true);
    setError(null);
  }, [fileUrl]);

  // Text selection handler
  useEffect(() => {
    function handleMouseUp() {
      const text = window.getSelection()?.toString().trim() ?? "";
      onSelectionChange(text || null);
    }
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("mouseup", handleMouseUp);
    return () => el.removeEventListener("mouseup", handleMouseUp);
  }, [onSelectionChange]);

  const onLoadSuccess = useCallback(
    ({ numPages }: { numPages: number }) => {
      setNumPages(numPages);
      setLoading(false);
      setError(null);
    },
    [],
  );

  const onLoadError = useCallback((err: Error) => {
    setError(err.message);
    setLoading(false);
  }, []);

  const goToPrev = () => setCurrentPage((p) => Math.max(1, p - 1));
  const goToNext = () =>
    setCurrentPage((p) => Math.min(numPages, p + 1));
  const zoomIn = () =>
    setScale((s) => Math.min(2.0, parseFloat((s + 0.15).toFixed(2))));
  const zoomOut = () =>
    setScale((s) => Math.max(0.5, parseFloat((s - 0.15).toFixed(2))));
  const resetZoom = () => setScale(1.0);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="sticky top-0 z-10 flex items-center gap-2 px-4 py-2 border-b border-white/10 bg-black/80 backdrop-blur-md">
        {/* Page nav */}
        <button
          className="w-8 h-8 flex items-center justify-center rounded text-white/60 hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed font-mono text-sm"
          onClick={goToPrev}
          disabled={currentPage <= 1 || loading}
          title="Previous page"
        >
          ←
        </button>
        <span className="text-xs font-mono text-white/50 min-w-[72px] text-center">
          {loading
            ? "Loading…"
            : numPages > 0
              ? `${currentPage} / ${numPages}`
              : "—"}
        </span>
        <button
          className="w-8 h-8 flex items-center justify-center rounded text-white/60 hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed font-mono text-sm"
          onClick={goToNext}
          disabled={currentPage >= numPages || loading}
          title="Next page"
        >
          →
        </button>

        <div className="w-px h-5 bg-white/15 mx-1" />

        {/* Zoom */}
        <button
          className="w-8 h-8 flex items-center justify-center rounded text-white/60 hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed font-mono text-sm"
          onClick={zoomOut}
          disabled={loading}
          title="Zoom out"
        >
          −
        </button>
        <button
          className="px-2 py-1 rounded text-[10px] font-mono text-white/50 hover:bg-white/10 transition-colors min-w-[42px] text-center"
          onClick={resetZoom}
          disabled={loading}
          title="Reset zoom"
        >
          {Math.round(scale * 100)}%
        </button>
        <button
          className="w-8 h-8 flex items-center justify-center rounded text-white/60 hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed font-mono text-sm"
          onClick={zoomIn}
          disabled={loading}
          title="Zoom in"
        >
          +
        </button>
      </div>

      {/* Document */}
      <div
        className="flex-1 overflow-auto flex flex-col items-center p-6 gap-4 pdf-viewer-selection"
        ref={containerRef}
      >
        <style>{`
          .pdf-viewer-selection ::selection {
            background-color: rgba(30, 144, 255, 0.3) !important;
            color: transparent !important;
          }
           /* For Firefox */
          .pdf-viewer-selection ::-moz-selection {
            background-color: rgba(30, 144, 255, 0.3) !important;
            color: transparent !important;
          }
          /* Ensure text layer spans don't become visible when selected */
          .react-pdf__Page__textContent span::selection {
            color: transparent !important;
          }
        `}</style>
        {error && (
          <div className="px-4 py-3 rounded-lg border border-red-400/30 bg-red-400/10 text-red-400 text-sm font-mono">
            Failed to load PDF: {error}
          </div>
        )}

        {loading && !error && (
          <div className="flex flex-col items-center gap-3 pt-10">
            <div className="w-5 h-5 border-2 border-white/20 border-t-white/70 rounded-full animate-spin" />
            <span className="text-xs font-mono text-white/40">
              Rendering PDF…
            </span>
          </div>
        )}

        <Document
          file={fileUrl}
          onLoadSuccess={onLoadSuccess}
          onLoadError={onLoadError}
          loading={null}
        >
          {numPages > 0 && (
            <Page
              key={`page_${currentPage}_${scale}`}
              pageNumber={currentPage}
              scale={scale}
              renderTextLayer={true}
              renderAnnotationLayer={true}
            />
          )}
        </Document>
      </div>
    </div>
  );
}
