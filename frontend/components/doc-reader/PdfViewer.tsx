"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const TOOLBAR_BTN =
  "min-w-[44px] min-h-[44px] flex items-center justify-center rounded text-white/60 hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed font-mono text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 focus-visible:ring-offset-2 focus-visible:ring-offset-black cursor-pointer";

type PdfViewerProps = {
  fileUrl: string;
  onSelectionChange(selected: string | null): void;
};

export function PdfViewer({ fileUrl, onSelectionChange }: PdfViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageInput, setPageInput] = useState("");
  const [scale, setScale] = useState(1.0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Reset state when the file changes
  useEffect(() => {
    setNumPages(0);
    setCurrentPage(1);
    setPageInput("");
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

  // Keyboard: arrow keys for page nav when viewer has focus
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (loading || numPages === 0) return;
      const target = e.target as HTMLElement;
      if (target.closest("input") || target.closest("textarea")) return;
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        setCurrentPage((p) => Math.max(1, p - 1));
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setCurrentPage((p) => Math.min(numPages, p + 1));
      }
    }
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("keydown", handleKeyDown);
    return () => el.removeEventListener("keydown", handleKeyDown);
  }, [loading, numPages]);

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

  const goToPage = (page: number) => {
    const p = Math.max(1, Math.min(numPages, page));
    setCurrentPage(p);
    setPageInput("");
  };

  const handlePageInputSubmit = () => {
    const n = parseInt(pageInput, 10);
    if (!Number.isNaN(n)) goToPage(n);
    else setPageInput("");
  };

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="sticky top-0 z-10 flex items-center gap-2 px-4 py-2 border-b border-white/10 bg-black/80 backdrop-blur-md">
        {/* Page nav */}
        <button
          type="button"
          className={TOOLBAR_BTN}
          onClick={goToPrev}
          disabled={currentPage <= 1 || loading}
          title="Previous page"
          aria-label="Previous page"
        >
          ←
        </button>
        <div className="flex items-center gap-1 min-w-[100px] justify-center">
          {loading ? (
            <span className="text-xs font-mono text-white/50">Loading…</span>
          ) : numPages > 0 ? (
            <>
              <input
                type="number"
                min={1}
                max={numPages}
                value={pageInput !== "" ? pageInput : String(currentPage)}
                onChange={(e) => setPageInput(e.target.value)}
                onBlur={handlePageInputSubmit}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handlePageInputSubmit();
                }}
                className="w-10 bg-white/5 border border-white/10 rounded text-center text-xs font-mono text-white/70 focus:border-white/25 focus:outline-none focus-visible:ring-1 focus-visible:ring-white/30 py-1.5"
                aria-label="Current page"
              />
              <span className="text-xs font-mono text-white/40">/ {numPages}</span>
            </>
          ) : (
            <span className="text-xs font-mono text-white/50">—</span>
          )}
        </div>
        <button
          type="button"
          className={TOOLBAR_BTN}
          onClick={goToNext}
          disabled={currentPage >= numPages || loading}
          title="Next page"
          aria-label="Next page"
        >
          →
        </button>

        <div className="w-px h-5 bg-white/15 mx-1" aria-hidden />

        {/* Zoom */}
        <button
          type="button"
          className={TOOLBAR_BTN}
          onClick={zoomOut}
          disabled={loading}
          title="Zoom out"
          aria-label="Zoom out"
        >
          −
        </button>
        <button
          type="button"
          className="min-h-[44px] px-2 rounded text-[10px] font-mono text-white/50 hover:bg-white/10 transition-colors min-w-[42px] text-center focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 focus-visible:ring-offset-2 focus-visible:ring-offset-black cursor-pointer"
          onClick={resetZoom}
          disabled={loading}
          title="Reset zoom"
          aria-label="Reset zoom to 100%"
        >
          {Math.round(scale * 100)}%
        </button>
        <button
          type="button"
          className={TOOLBAR_BTN}
          onClick={zoomIn}
          disabled={loading}
          title="Zoom in"
          aria-label="Zoom in"
        >
          +
        </button>
      </div>

      {/* Document */}
      <div
        className="flex-1 overflow-auto flex flex-col items-center p-6 gap-4 pdf-viewer-selection min-h-[320px]"
        ref={containerRef}
        tabIndex={0}
        role="region"
        aria-label="PDF document"
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
