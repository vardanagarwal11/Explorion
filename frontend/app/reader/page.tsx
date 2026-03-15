"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import {
  DocumentMeta,
  getDocuments,
  uploadDocument,
} from "@/lib/doc-reader-api";

type UploadStatus = "idle" | "uploading" | "done" | "error";

export default function ReaderPage() {
  const router = useRouter();
  const [library, setLibrary] = useState<DocumentMeta[]>([]);
  const [libLoading, setLibLoading] = useState(true);

  // Upload
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getDocuments()
      .then(setLibrary)
      .catch(() => {})
      .finally(() => setLibLoading(false));
  }, []);

  const processFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Only PDF files are supported.");
      return;
    }
    setUploadStatus("uploading");
    setUploadError(null);
    setUploadProgress(10);

    const interval = setInterval(() => {
      setUploadProgress((p) => Math.min(p + 8, 85));
    }, 600);

    try {
      const res = await uploadDocument(file);
      clearInterval(interval);
      setUploadProgress(100);

      const newDoc: DocumentMeta = {
        id: res.document_id,
        title: res.title,
        file_path: "",
        uploaded_at: new Date().toISOString(),
      };

      setLibrary((prev) => {
        const exists = prev.find((d) => d.id === res.document_id);
        return exists ? prev : [newDoc, ...prev];
      });

      setTimeout(() => {
        setUploadStatus("done");
        setUploadProgress(0);
        // Navigate to the document reader
        router.push(`/reader/${res.document_id}`);
      }, 800);
    } catch (err) {
      clearInterval(interval);
      setUploadStatus("error");
      setUploadProgress(0);
      setUploadError(
        err instanceof Error ? err.message : "Upload failed",
      );
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  const isUploading = uploadStatus === "uploading";

  return (
    <main className="min-h-screen bg-black text-white font-mono relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-white/[0.015] rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[40%] h-[40%] bg-white/[0.01] rounded-full blur-[100px] pointer-events-none" />

      {/* Corner Frame Accents */}
      <div className="absolute top-0 left-0 w-8 h-8 lg:w-12 lg:h-12 border-t-2 border-l-2 border-white/30 z-20" />
      <div className="absolute top-0 right-0 w-8 h-8 lg:w-12 lg:h-12 border-t-2 border-r-2 border-white/30 z-20" />
      <div className="absolute bottom-0 left-0 w-8 h-8 lg:w-12 lg:h-12 border-b-2 border-l-2 border-white/30 z-20" />
      <div className="absolute bottom-0 right-0 w-8 h-8 lg:w-12 lg:h-12 border-b-2 border-r-2 border-white/30 z-20" />

      <div className="relative z-10 max-w-4xl mx-auto px-6 py-12">
        {/* Header */}
        <header className="mb-12 border-b border-white/10 pb-8">
          <Link
            href="/"
            className="inline-flex items-center text-white/50 hover:text-white transition-colors mb-6 text-sm"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Systems Check
          </Link>
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-4"
          >
            <Image
              src="/logo-new.png"
              alt="Explorion"
              width={52}
              height={52}
              className="object-contain drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]"
            />
            <h1 className="text-3xl md:text-5xl font-bold tracking-widest uppercase">
              Document Reader
            </h1>
            <span className="text-xs bg-white/10 text-white/70 px-2 py-1 rounded font-normal leading-none tracking-normal">
              AI
            </span>
          </motion.div>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-white/40 mt-3 text-sm max-w-xl"
          >
            Upload PDFs, highlight text for instant explanations, and chat with
            your documents using AI.
          </motion.p>
        </header>

        {/* Upload zone */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mb-10"
        >
          <div
            className={`relative border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-all duration-300 ${
              isDragOver
                ? "border-white/40 bg-white/[0.06]"
                : "border-white/15 bg-white/[0.02] hover:border-white/25 hover:bg-white/[0.04]"
            }`}
            onDrop={handleDrop}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onClick={() => !isUploading && fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              onChange={handleFileChange}
              className="hidden"
            />
            {isUploading ? (
              <>
                <div className="text-3xl mb-3">⏳</div>
                <div className="text-sm text-white/60">
                  Indexing document…
                </div>
                <div className="mt-4 mx-auto max-w-xs h-1 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-white/30 to-white/60 rounded-full transition-all duration-400"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </>
            ) : (
              <>
                <div className="text-4xl mb-3">📂</div>
                <div className="text-sm text-white/50">
                  <span className="text-white/70 font-semibold">Click</span>{" "}
                  or drag a PDF here to begin
                </div>
              </>
            )}
          </div>

          {uploadError && (
            <div className="mt-3 px-4 py-2 rounded-lg border border-red-400/30 bg-red-400/10 text-red-400 text-xs font-mono">
              {uploadError}
            </div>
          )}
          {uploadStatus === "done" && (
            <div className="mt-3 px-4 py-2 rounded-lg border border-green-400/30 bg-green-400/10 text-green-400 text-xs font-mono">
              ✓ Document indexed and ready!
            </div>
          )}
        </motion.div>

        {/* Document library */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          <div className="flex items-center gap-2 mb-4">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-white/30">
              Documents
            </div>
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-[10px] text-white/20">
              {library.length} ENTRY(S)
            </span>
          </div>

          {libLoading ? (
            <div className="flex flex-col gap-3">
              {[1, 2].map((i) => (
                <div
                  key={i}
                  className="h-16 rounded-lg bg-white/[0.03] animate-pulse"
                />
              ))}
            </div>
          ) : library.length === 0 ? (
            <div className="text-center py-16 border border-white/5 bg-white/[0.02] rounded-lg">
              <span className="text-3xl block mb-3">📭</span>
              <p className="text-white/30 text-sm">
                No documents yet. Upload a PDF to get started.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {library.map((doc, idx) => (
                <motion.div
                  key={doc.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                >
                  <Link href={`/reader/${doc.id}`}>
                    <div className="group border border-white/10 bg-black hover:bg-white/[0.05] hover:border-white/25 transition-all duration-300 p-5 rounded-lg relative flex items-center gap-4">
                      <div className="absolute top-0 right-0 w-3 h-3 border-t border-r border-transparent group-hover:border-white/40 transition-colors" />
                      <div className="w-10 h-10 rounded bg-white/[0.06] border border-white/10 flex items-center justify-center text-lg flex-shrink-0">
                        📄
                      </div>
                      <div className="overflow-hidden flex-1">
                        <div className="text-sm font-medium text-white/80 truncate group-hover:text-white transition-colors">
                          {doc.title}
                        </div>
                        <div className="text-[10px] text-white/30 mt-1">
                          {new Date(doc.uploaded_at).toLocaleString("en-IN", {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                      <span className="text-[10px] font-mono opacity-0 group-hover:opacity-100 transition-opacity tracking-widest uppercase text-white/40">
                        Read_&gt;
                      </span>
                    </div>
                  </Link>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </main>
  );
}
