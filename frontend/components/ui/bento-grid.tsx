"use client";

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

export const BentoGrid = ({
  className,
  children,
}: {
  className?: string;
  children?: React.ReactNode;
}) => {
  return (
    <div
      className={cn(
        "grid grid-cols-1 md:grid-cols-3 gap-4 max-w-7xl mx-auto",
        className
      )}
    >
      {children}
    </div>
  );
};

export const BentoGridItem = ({
  className,
  title,
  description,
  header,
  icon,
  index,
}: {
  className?: string;
  title?: string | React.ReactNode;
  description?: string | React.ReactNode;
  header?: React.ReactNode;
  icon?: React.ReactNode;
  index?: number;
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: (index ?? 0) * 0.1 }}
      className={cn(
        "row-span-1 rounded-xl group/bento hover:shadow-xl transition duration-200 shadow-none p-4 bg-white/5 border border-white/10 justify-between flex flex-col space-y-4 overflow-hidden relative",
        className
      )}
    >
      {/* Gradient hover effect */}
      <motion.div
        className="absolute inset-0 opacity-0 group-hover/bento:opacity-100 transition-opacity duration-300"
        style={{
          background:
            "radial-gradient(400px at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(120, 119, 198, 0.1), transparent 40%)",
        }}
      />
      {header}
      <div className="group-hover/bento:translate-x-2 transition duration-200 relative z-10">
        {icon}
        <div className="font-semibold text-white mb-2 mt-2">{title}</div>
        <div className="text-sm text-white/60">{description}</div>
      </div>
    </motion.div>
  );
};
