"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Copy, FileText, Github, Link as LinkIcon, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function UniversalInputForm() {
  const router = useRouter();
  const [inputType, setInputType] = useState<"url" | "arxiv" | "github" | "text">("url");
  const [inputValue, setInputValue] = useState("");
  const [videoMode, setVideoMode] = useState("standard");
  const [narrationStyle, setNarrationStyle] = useState("educational");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    setIsSubmitting(true);
    setError(null);

    const payload: Record<string, unknown> = {
      config: {
        video_mode: videoMode,
        narration_style: narrationStyle,
        tts_provider: "gtts",
        language: "en"
      }
    };

    if (inputType === "url") payload.url = inputValue.trim();
    if (inputType === "arxiv") payload.arxiv_id = inputValue.trim();
    if (inputType === "github") {
      payload.url = inputValue.trim();
      payload.content_type = "github_repo";
    }
    if (inputType === "text") payload.text = inputValue.trim();

    try {
      const endpoint = inputType === "github" ? "/api/process/github" :
        inputType === "text" ? "/api/process/content" :
          "/api/process/universal";

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();

      if (data.job_id) {
        router.push(`/process/${data.job_id}`);
      } else {
        throw new Error("No job ID returned from server");
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to connect to server";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full mt-8 max-w-xl relative bg-black/40 backdrop-blur-md border border-white/20 p-6 shadow-2xl">
      <div className="absolute top-0 right-0 w-8 h-8 border-t border-r border-white/40"></div>
      <div className="absolute bottom-0 left-0 w-8 h-8 border-b border-l border-white/40"></div>

      <div className="flex items-center gap-2 mb-6 opacity-80">
        <div className="w-6 h-px bg-white"></div>
        <span className="text-white text-[10px] font-mono tracking-widest">INPUT.MATRIX</span>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Tabs defaultValue="url" onValueChange={(v: any) => setInputType(v)} className="w-full">
          <TabsList className="grid w-full grid-cols-4 bg-white/5 border border-white/10 rounded-none mb-6">
            <TabsTrigger value="url" className="data-[state=active]:bg-white/10 data-[state=active]:text-white text-white/50 text-xs font-mono rounded-none">
              <LinkIcon className="w-3 h-3 mr-2" /> URL
            </TabsTrigger>
            <TabsTrigger value="arxiv" className="data-[state=active]:bg-white/10 data-[state=active]:text-white text-white/50 text-xs font-mono rounded-none">
              <FileText className="w-3 h-3 mr-2" /> ArXiv
            </TabsTrigger>
            <TabsTrigger value="github" className="data-[state=active]:bg-white/10 data-[state=active]:text-white text-white/50 text-xs font-mono rounded-none">
              <Github className="w-3 h-3 mr-2" /> Repo
            </TabsTrigger>
            <TabsTrigger value="text" className="data-[state=active]:bg-white/10 data-[state=active]:text-white text-white/50 text-xs font-mono rounded-none">
              <Copy className="w-3 h-3 mr-2" /> Text
            </TabsTrigger>
          </TabsList>

          <TabsContent value="url">
            <Input
              placeholder="Paste any article or document URL..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="bg-black/50 border-white/20 focus-visible:ring-1 focus-visible:ring-yellow-400 focus-visible:border-yellow-400 transition-all duration-300 text-white font-mono rounded-none h-12"
            />
          </TabsContent>
          <TabsContent value="arxiv">
            <Input
              placeholder="Paste an arXiv ID (e.g. 1706.03762)..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="bg-black/50 border-white/20 focus-visible:ring-1 focus-visible:ring-yellow-400 focus-visible:border-yellow-400 transition-all duration-300 text-white font-mono rounded-none h-12"
            />
          </TabsContent>
          <TabsContent value="github">
            <Input
              placeholder="Paste a public GitHub repo URL..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="bg-black/50 border-white/20 focus-visible:ring-1 focus-visible:ring-yellow-400 focus-visible:border-yellow-400 transition-all duration-300 text-white font-mono rounded-none h-12"
            />
          </TabsContent>
          <TabsContent value="text">
            <Textarea
              placeholder="Paste technical content or documentation here..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="bg-black/50 border-white/20 focus-visible:ring-1 focus-visible:ring-yellow-400 focus-visible:border-yellow-400 transition-all duration-300 text-white font-mono rounded-none min-h-[100px]"
            />
          </TabsContent>
        </Tabs>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label className="text-white/60 text-[10px] font-mono uppercase">Video Mode</Label>
            <Select value={videoMode} onValueChange={setVideoMode}>
              <SelectTrigger className="bg-white/5 border-white/10 text-white font-mono text-xs rounded-none h-10">
                <SelectValue placeholder="Select mode" />
              </SelectTrigger>
              <SelectContent className="bg-black border-white/20 text-white font-mono rounded-none">
                <SelectItem value="quick">Quick (2-3 min)</SelectItem>
                <SelectItem value="standard">Standard (5-8 min)</SelectItem>
                <SelectItem value="deep_dive">Deep Dive (10-20 min)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="text-white/60 text-[10px] font-mono uppercase">Voice Style</Label>
            <Select value={narrationStyle} onValueChange={setNarrationStyle}>
              <SelectTrigger className="bg-white/5 border-white/10 text-white font-mono text-xs rounded-none h-10">
                <SelectValue placeholder="Select style" />
              </SelectTrigger>
              <SelectContent className="bg-black border-white/20 text-white font-mono rounded-none">
                <SelectItem value="educational">Educational</SelectItem>
                <SelectItem value="teacher">Teacher (Slow)</SelectItem>
                <SelectItem value="youtube">YouTube Explainer</SelectItem>
                <SelectItem value="podcast">Podcast</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {error && (
          <div className="border border-red-500/30 bg-red-500/10 p-3 text-red-400 text-xs font-mono flex items-start gap-2">
            <span className="shrink-0 mt-0.5">✕</span>
            <span>{error}</span>
          </div>
        )}

        <Button
          type="submit"
          disabled={!inputValue || isSubmitting}
          className="w-full relative bg-yellow-400 text-black hover:bg-yellow-300 hover:shadow-[0_0_20px_rgba(250,204,21,0.4)] font-mono text-sm tracking-wider rounded-none h-12 group overflow-hidden border border-yellow-400 focus-visible:ring-2 focus-visible:ring-yellow-400 focus-visible:ring-offset-2 focus-visible:ring-offset-black transition-all duration-300"
        >
          <span className="relative z-10 flex items-center justify-center gap-2">
            {isSubmitting ? "INITIALIZING SEQUENCE..." : "GENERATE VISUAL EXPLANATION"}
            {!isSubmitting && <Sparkles className="w-4 h-4 ml-2" />}
          </span>
          {/* Glitch overlay on hover */}
          <div className="absolute inset-0 bg-white/30 translate-x-[-100%] group-hover:translate-x-0 transition-transform duration-500 ease-in-out z-0 opacity-50"></div>
        </Button>
      </form>
    </div>
  );
}
