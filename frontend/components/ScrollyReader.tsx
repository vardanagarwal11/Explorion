"use client";

import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ScrollySection, type ScrollySectionModel } from "./ScrollySection";

export function ScrollyReader({
  sections,
  heroContent,
  onProgressChange,
}: {
  sections: ScrollySectionModel[];
  heroContent?: ReactNode;
  onProgressChange?: (progress: number) => void;
}) {
  const [activeId, setActiveId] = useState<string | null>(
    sections[0]?.id ?? null
  );

  const items = useMemo(
    () => sections.map((s, i) => ({ id: s.id, index: i })),
    [sections]
  );

  const onActiveChange = useCallback((id: string, isActive: boolean) => {
    if (isActive) setActiveId(id);
  }, []);

  const activeIndex = items.findIndex((it) => it.id === activeId);
  const progress = items.length > 1 ? activeIndex / (items.length - 1) : 0;

  useEffect(() => {
    onProgressChange?.(progress);
  }, [progress, onProgressChange]);

  return (
    <div className="max-w-3xl mx-auto">
      {heroContent}

      <div className="space-y-10">
        {sections.map((s, i) => (
          <ScrollySection
            key={s.id}
            section={s}
            index={i}
            onActiveChange={onActiveChange}
          />
        ))}
      </div>

      {/* End of content */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="mt-16 flex flex-col items-center gap-4 py-8"
      >
        <div className="flex items-center gap-3 w-full text-sm text-white/25">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent to-white/[0.06]" />
          <span>End of paper</span>
          <div className="h-px flex-1 bg-gradient-to-l from-transparent to-white/[0.06]" />
        </div>

        <button
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="mt-2 text-xs text-white/30 hover:text-white/60 transition-colors"
        >
          Back to top
        </button>
      </motion.div>
    </div>
  );
}
