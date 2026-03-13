"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Clock, PlayCircle, Loader2, Search, FileText, Database, Code } from "lucide-react";
import { Input } from "@/components/ui/input";
import { motion } from "framer-motion";
import Image from "next/image";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PaperSummary {
    paper_id: string;
    title: string;
    authors: string[];
    content_type: string;
    visualization_count: number;
    processed_at: string;
}

export default function Dashboard() {
    const [papers, setPapers] = useState<PaperSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");

    useEffect(() => {
        fetch(`${API_URL}/api/papers`)
            .then(res => res.json())
            .then(data => {
                setPapers(data.papers || []);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    const filteredPapers = papers.filter(p =>
        p.title.toLowerCase().includes(search.toLowerCase()) ||
        p.paper_id.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <main className="min-h-screen bg-black text-white p-6 md:p-12 font-mono relative overflow-hidden">
            {/* Background Decor */}
            <div className="absolute top-[-20%] right-[-10%] w-[50%] h-[50%] bg-white/[0.02] rounded-full blur-[120px] pointer-events-none"></div>

            <div className="max-w-6xl mx-auto relative z-10">
                <header className="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-white/10 pb-8">
                    <div>
                        <Link href="/" className="inline-flex items-center text-white/50 hover:text-white transition-colors mb-6 text-sm">
                            <ArrowLeft className="w-4 h-4 mr-2" /> Back to Systems Check
                        </Link>
                        <motion.h1
                            initial={{ opacity: 0, y: -20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="text-3xl md:text-5xl font-bold tracking-widest uppercase flex items-center gap-4"
                        >
                            <Image src="/logo.png" alt="Explorion" width={40} height={40} className="object-contain drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]" />
                            Data Core
                            <span className="text-xs bg-white/10 text-white/70 px-2 py-1 rounded font-normal leading-none tracking-normal">
                                {papers.length} ENTRY(S)
                            </span>
                        </motion.h1>
                        <motion.p
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.2 }}
                            className="text-white/40 mt-3 text-sm max-w-xl line-clamp-2"
                        >
                            All processed content ingested by the Explorion rendering engine.
                        </motion.p>
                    </div>

                    <div className="relative w-full md:w-72">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                        <Input
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            placeholder="Search index..."
                            className="pl-10 bg-white/5 border-white/10 rounded-none h-10 text-sm focus-visible:ring-1 focus-visible:ring-white/30"
                        />
                    </div>
                </header>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 opacity-50">
                        <Loader2 className="w-8 h-8 animate-spin mb-4 text-white" />
                        <span className="tracking-widest uppercase text-sm">Accessing Archives...</span>
                    </div>
                ) : filteredPapers.length === 0 ? (
                    <div className="text-center py-20 border border-white/5 bg-white/[0.02]">
                        <Database className="w-12 h-12 text-white/20 mx-auto mb-4" />
                        <p className="text-white/40">No entries found matching query.</p>
                    </div>
                ) : (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ staggerChildren: 0.1 }}
                        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                    >
                        {filteredPapers.map((paper, index) => (
                            <motion.div
                                key={paper.paper_id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: index * 0.05 }}
                            >
                                <Link href={`/result/${encodeURIComponent(paper.paper_id)}`}>
                                    <div className="group border border-white/10 bg-black hover:bg-white/[0.05] hover:border-white/40 transition-all duration-300 p-6 relative h-[250px] flex flex-col shadow-[0_0_15px_rgba(0,0,0,0)] hover:shadow-[0_0_15px_rgba(255,255,255,0.1)]">
                                        {/* Decor */}
                                        <div className="absolute top-0 right-0 w-4 h-4 border-t border-r border-transparent group-hover:border-white/50 transition-colors"></div>

                                        <div className="flex items-center justify-between mb-4">
                                            <span className="text-[10px] bg-white/10 px-2 py-0.5 rounded text-white/60 uppercase tracking-wider flex items-center gap-1.5">
                                                {paper.content_type === "research_paper" && <FileText className="w-3 h-3" />}
                                                {paper.content_type === "github_repo" && <Code className="w-3 h-3" />}
                                                {paper.content_type === "technical_content" && <Database className="w-3 h-3" />}
                                                {paper.content_type.replace("_", " ")}
                                            </span>
                                            <span className="text-[10px] text-white/30 flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {new Date(paper.processed_at).toLocaleDateString()}
                                            </span>
                                        </div>

                                        <h3 className="text-lg font-semibold leading-tight mb-2 line-clamp-3 group-hover:text-white text-white/90">
                                            {paper.title}
                                        </h3>

                                        <p className="text-xs text-white/40 line-clamp-1 mt-auto">
                                            {paper.authors?.join(", ") || "Unknown Author"}
                                        </p>

                                        <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-between text-xs text-white/50">
                                            <div className="flex items-center gap-2">
                                                <PlayCircle className="w-4 h-4 text-white/30 group-hover:text-white transition-colors" />
                                                <span className="group-hover:text-white/80 transition-colors">{paper.visualization_count} Visuals</span>
                                            </div>
                                            <span className="text-[10px] font-mono opacity-0 group-hover:opacity-100 transition-opacity tracking-widest uppercase text-yellow-400">
                                                Access_&gt;
                                            </span>
                                        </div>
                                    </div>
                                </Link>
                            </motion.div>
                        ))}
                    </motion.div>
                )}
            </div>
        </main>
    );
}
