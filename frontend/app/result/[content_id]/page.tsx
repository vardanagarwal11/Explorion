"use client";

import { use, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Download, Share2, PlayCircle, Loader2, ArrowLeft, FileText, Code, Database, Volume2 } from "lucide-react";
import Link from "next/link";

const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_URL = rawApiUrl.startsWith("http") ? rawApiUrl : `http://${rawApiUrl}`;

interface Section {
    id: string;
    title: string;
    content: string;
    summary?: string;
    order_index?: number;
    video_url?: string;
    subtitle_url?: string;
    audio_url?: string;
    code_blocks?: string[];
}

interface Visualization {
    id: string;
    section_id: string;
    concept: string;
    video_url?: string;
    subtitle_url?: string;
    audio_url?: string;
    status: string;
}

interface PaperData {
    paper_id: string;
    title: string;
    authors: string[];
    abstract: string;
    pdf_url?: string;
    source_url?: string;
    content_type?: string;
    sections: Section[];
    visualizations: Visualization[];
}

const CONTENT_TYPE_LABELS: Record<string, { label: string; icon: typeof FileText }> = {
    research_paper: { label: "Research Paper", icon: FileText },
    github_repo: { label: "GitHub Repository", icon: Code },
    technical_content: { label: "Technical Content", icon: Database },
};

export default function ResultPage({ params }: { params: Promise<{ content_id: string }> }) {
    const unwrappedParams = use(params);
    const [data, setData] = useState<PaperData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [activeSectionId, setActiveSectionId] = useState<string | null>(null);

    // Resolve relative URLs (like /api/video/xxx) to absolute with backend host
    const resolveUrl = (url: string | undefined | null): string | undefined => {
        if (!url) return undefined;
        if (url.startsWith("http://") || url.startsWith("https://")) return url;
        return `${API_URL}${url}`;
    };

    useEffect(() => {
        fetch(`${API_URL}/api/paper/${unwrappedParams.content_id}`)
            .then(res => {
                if (!res.ok) throw new Error("Could not fetch the result data.");
                return res.json();
            })
            .then(json => {
                // Resolve all media URLs to absolute paths
                if (json.sections) {
                    json.sections = json.sections.map((s: Section) => ({
                        ...s,
                        video_url: resolveUrl(s.video_url),
                        subtitle_url: resolveUrl(s.subtitle_url),
                        audio_url: resolveUrl(s.audio_url),
                    }));
                }
                if (json.visualizations) {
                    json.visualizations = json.visualizations.map((v: Visualization) => ({
                        ...v,
                        video_url: resolveUrl(v.video_url),
                        subtitle_url: resolveUrl(v.subtitle_url),
                        audio_url: resolveUrl(v.audio_url),
                    }));
                }
                setData(json);
                if (json.sections && json.sections.length > 0) {
                    setActiveSectionId(json.sections[0].id);
                }
            })
            .catch(err => setError(err.message))
            .finally(() => setLoading(false));
    }, [unwrappedParams.content_id]);

    if (loading) {
        return (
            <div className="min-h-screen bg-black flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-white animate-spin" />
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="min-h-screen bg-black flex flex-col items-center justify-center p-8 text-center">
                <p className="text-red-400 font-mono mb-4">{error || "Data not found"}</p>
                <Link href="/">
                    <Button variant="outline" className="font-mono text-white border-white/20">Return Home</Button>
                </Link>
            </div>
        );
    }

    const activeSection = data.sections.find(s => s.id === activeSectionId);
    const finalFullVideo = data.visualizations?.find(v => v.concept === "full_stitched_video");
    const contentMeta = CONTENT_TYPE_LABELS[data.content_type || "research_paper"] || CONTENT_TYPE_LABELS.research_paper;
    const ContentIcon = contentMeta.icon;

    // Resolve video & subtitle URLs
    const currentVideoUrl = activeSection?.video_url || finalFullVideo?.video_url;
    const currentSubtitleUrl = activeSection?.subtitle_url || finalFullVideo?.subtitle_url;
    const currentAudioUrl = activeSection?.audio_url || finalFullVideo?.audio_url;

    return (
        <div className="min-h-screen bg-black text-white/80 font-mono flex flex-col lg:h-screen lg:overflow-hidden">
            {/* Top Banner */}
            <div className="h-16 border-b border-white/10 flex items-center px-4 md:px-8 shrink-0 relative bg-black/60 backdrop-blur-lg z-20">
                <Link href="/" className="mr-6 opacity-60 hover:opacity-100 transition-opacity">
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <h1 className="text-sm md:text-base font-bold truncate text-white">{data.title}</h1>
                        <span className="hidden md:inline-flex items-center gap-1 text-[9px] bg-white/10 px-2 py-0.5 text-white/60 uppercase tracking-wider shrink-0">
                            <ContentIcon className="w-3 h-3" />
                            {contentMeta.label}
                        </span>
                    </div>
                    <p className="text-[10px] text-white/40 truncate">{data.authors.join(", ")}</p>
                </div>

                <div className="hidden md:flex gap-3 ml-4 border-l border-white/10 pl-6 h-full items-center">
                    <Button size="sm" variant="outline" className="h-8 bg-transparent text-white/80 border-white/20 hover:bg-white/10 text-xs">
                        <Share2 className="w-3 h-3 mr-2" /> Share
                    </Button>
                    {(data.pdf_url || data.source_url) && (
                        <a href={data.pdf_url || data.source_url} target="_blank" rel="noreferrer">
                            <Button size="sm" className="h-8 bg-white text-black hover:bg-white/90 text-xs">
                                <Download className="w-3 h-3 mr-2" /> Source
                            </Button>
                        </a>
                    )}
                </div>
            </div>

            {/* Main Content Split */}
            <div className="flex flex-col lg:flex-row flex-1 overflow-hidden">
                {/* Left: Video / Visualization */}
                <div className="w-full lg:w-3/5 bg-[#050505] relative flex flex-col border-b lg:border-b-0 lg:border-r border-white/10">
                    <div className="p-4 border-b border-white/10 flex justify-between items-center bg-black/40">
                        <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                            <span className="text-[10px] uppercase tracking-widest text-white/50">Playback Engine</span>
                        </div>
                        <div className="flex items-center gap-2">
                            {currentAudioUrl && (
                                <span className="text-[10px] bg-white/10 text-white px-2 py-1 flex items-center gap-1">
                                    <Volume2 className="w-3 h-3" /> NARRATION
                                </span>
                            )}
                            {finalFullVideo && (
                                <span className="text-[10px] bg-white/10 text-white px-2 py-1">FULL RENDER</span>
                            )}
                        </div>
                    </div>

                    <div className="flex-1 relative flex items-center justify-center p-4">
                        {currentVideoUrl ? (
                            <video
                                key={currentVideoUrl}
                                controls
                                autoPlay
                                className="w-full max-h-[70vh] rounded-lg shadow-[0_0_30px_rgba(255,255,255,0.05)] border border-white/10"
                            >
                                <source src={currentVideoUrl} type="video/mp4" />
                                {currentSubtitleUrl && (
                                    <track
                                        kind="subtitles"
                                        src={currentSubtitleUrl}
                                        srcLang="en"
                                        label="English"
                                        default
                                    />
                                )}
                            </video>
                        ) : (
                            <div className="text-center opacity-40">
                                <PlayCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                                <p className="text-sm">No visualization available for this section.</p>
                            </div>
                        )}

                        {/* Corner Decorative */}
                        <div className="absolute top-8 left-8 w-4 h-4 border-t border-l border-white/20" />
                        <div className="absolute bottom-8 right-8 w-4 h-4 border-b border-r border-white/20" />
                    </div>
                </div>

                {/* Right: Sections & Info */}
                <div className="w-full lg:w-2/5 flex flex-col h-[50vh] lg:h-auto bg-black bg-opacity-95">
                    <Tabs defaultValue="sections" className="w-full h-full flex flex-col">
                        <TabsList className="w-full grid-cols-2 bg-transparent border-b border-white/10 rounded-none h-12 p-0 shrink-0">
                            <TabsTrigger value="sections" className="rounded-none data-[state=active]:bg-white/5 data-[state=active]:border-b-2 data-[state=active]:border-white h-full px-4 text-xs tracking-wider uppercase text-white/50 data-[state=active]:text-white">
                                Content Modules
                            </TabsTrigger>
                            <TabsTrigger value="abstract" className="rounded-none data-[state=active]:bg-white/5 data-[state=active]:border-b-2 data-[state=active]:border-white h-full px-4 text-xs tracking-wider uppercase text-white/50 data-[state=active]:text-white">
                                Abstract &amp; Meta
                            </TabsTrigger>
                        </TabsList>

                        <TabsContent value="sections" className="flex-1 overflow-hidden m-0 p-0 border-none outline-none">
                            <ScrollArea className="h-full w-full">
                                <div className="space-y-[1px] bg-white/5 pb-10">
                                    {data.sections.map((sec, idx) => (
                                        <div
                                            key={sec.id}
                                            onClick={() => setActiveSectionId(sec.id)}
                                            className={`p-5 cursor-pointer transition-all border-l-2 ${activeSectionId === sec.id ? "bg-white/5 border-white" : "bg-black hover:bg-white/[0.02] border-transparent"}`}
                                        >
                                            <h3 className={`text-sm font-semibold mb-2 ${activeSectionId === sec.id ? "text-white" : "text-white/70"}`}>
                                                <span className="text-white/30 mr-2 opacity-50">{String((sec.order_index ?? idx) + 1).padStart(2, '0')}</span>
                                                {sec.title}
                                            </h3>
                                            <p className="text-xs text-white/50 line-clamp-2 leading-relaxed">
                                                {sec.summary || sec.content.substring(0, 100) + '...'}
                                            </p>

                                            <div className="flex gap-2 mt-3">
                                                {sec.video_url && (
                                                    <span className="inline-flex items-center gap-1.5 text-[9px] bg-white/10 px-2 py-0.5 rounded text-white/80 uppercase">
                                                        <PlayCircle className="w-3 h-3" /> Visualized
                                                    </span>
                                                )}
                                                {sec.audio_url && (
                                                    <span className="inline-flex items-center gap-1.5 text-[9px] bg-white/10 px-2 py-0.5 rounded text-white/80 uppercase">
                                                        <Volume2 className="w-3 h-3" /> Audio
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </ScrollArea>
                        </TabsContent>

                        <TabsContent value="abstract" className="flex-1 overflow-hidden m-0 p-6 border-none outline-none">
                            <ScrollArea className="h-full w-full pr-4">
                                <h3 className="text-white text-lg font-bold mb-4 font-sans leading-snug">{data.title}</h3>
                                <div className="prose prose-invert prose-sm prose-p:leading-loose text-white/60 font-sans max-w-none">
                                    <ReactMarkdown>{data.abstract}</ReactMarkdown>
                                </div>

                                {(data.pdf_url || data.source_url) && (
                                    <a href={data.pdf_url || data.source_url} target="_blank" rel="noreferrer">
                                        <Button variant="outline" className="mt-8 w-full border-white/20 text-white/80 bg-transparent hover:bg-white/5 text-xs h-10">
                                            <Download className="w-4 h-4 mr-2" /> View Original Source
                                        </Button>
                                    </a>
                                )}
                            </ScrollArea>
                        </TabsContent>
                    </Tabs>
                </div>
            </div>
        </div>
    );
}
