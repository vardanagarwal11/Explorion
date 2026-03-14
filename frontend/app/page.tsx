'use client';

import { useEffect, useState } from 'react';
import { UniversalInputForm } from '@/components/ui/universal-input-form';
import { motion } from 'framer-motion';
import Image from 'next/image';

export default function Home() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const embedScript = document.createElement('script');
    embedScript.type = 'text/javascript';
    embedScript.textContent = `
      !function(){
        if(!window.UnicornStudio){
          window.UnicornStudio={isInitialized:!1};
          var i=document.createElement("script");
          i.src="https://cdn.jsdelivr.net/gh/hiunicornstudio/unicornstudio.js@v1.4.33/dist/unicornStudio.umd.js";
          i.onload=function(){
            window.UnicornStudio.isInitialized||(UnicornStudio.init(),window.UnicornStudio.isInitialized=!0)
          };
          (document.head || document.body).appendChild(i)
        }
      }();
    `;
    document.head.appendChild(embedScript);

    // Add CSS to hide branding elements and crop canvas
    const style = document.createElement('style');
    style.textContent = `
      [data-us-project] {
        position: relative !important;
        overflow: hidden !important;
      }
      
      [data-us-project] canvas {
        clip-path: inset(0 0 10% 0) !important;
      }
      
      [data-us-project] * {
        pointer-events: none !important;
      }
      [data-us-project] a[href*="unicorn"],
      [data-us-project] button[title*="unicorn"],
      [data-us-project] div[title*="Made with"],
      [data-us-project] .unicorn-brand,
      [data-us-project] [class*="brand"],
      [data-us-project] [class*="credit"],
      [data-us-project] [class*="watermark"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        position: absolute !important;
        left: -9999px !important;
        top: -9999px !important;
      }
    `;
    document.head.appendChild(style);

    // Function to aggressively hide branding
    const hideBranding = () => {
      const selectors = [
        '[data-us-project]',
        '[data-us-project="OMzqyUv6M3kSnv0JeAtC"]',
        '.unicorn-studio-container',
        'canvas[aria-label*="Unicorn"]'
      ];

      selectors.forEach(selector => {
        const containers = document.querySelectorAll(selector);
        containers.forEach(container => {
          const allElements = container.querySelectorAll('*');
          allElements.forEach(el => {
            const text = (el.textContent || '').toLowerCase();
            const title = (el.getAttribute('title') || '').toLowerCase();
            const href = (el.getAttribute('href') || '').toLowerCase();

            if (
              text.includes('made with') ||
              text.includes('unicorn') ||
              title.includes('made with') ||
              title.includes('unicorn') ||
              href.includes('unicorn.studio')
            ) {
              //@ts-ignore
              el.style.display = 'none';
              //@ts-ignore
              el.style.visibility = 'hidden';
              //@ts-ignore
              el.style.opacity = '0';
              //@ts-ignore
              el.style.pointerEvents = 'none';
              //@ts-ignore
              el.style.position = 'absolute';
              //@ts-ignore
              el.style.left = '-9999px';
              //@ts-ignore
              el.style.top = '-9999px';
              try { el.remove(); } catch (e) { }
            }
          });
        });
      });
    };

    hideBranding();
    const interval = setInterval(hideBranding, 50);

    setTimeout(hideBranding, 500);
    setTimeout(hideBranding, 1000);
    setTimeout(hideBranding, 2000);

    return () => {
      clearInterval(interval);
      try {
        if (embedScript.parentNode) document.head.removeChild(embedScript);
        if (style.parentNode) document.head.removeChild(style);
      } catch (e) { }
    };
  }, []);

  if (!mounted) return null;

  return (
    <main className="relative min-h-screen overflow-hidden bg-black">
      {/* Background Animation */}
      <div className="absolute inset-0 w-full h-full hidden lg:block">
        <div
          data-us-project="OMzqyUv6M3kSnv0JeAtC"
          style={{ width: '100%', height: '100%', minHeight: '100vh' }}
        />
      </div>

      {/* Mobile stars background */}
      <div className="absolute inset-0 w-full h-full lg:hidden stars-bg"></div>

      {/* Top Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="absolute top-0 left-0 right-0 z-20 border-b border-white/20"
      >
        <div className="container mx-auto px-4 lg:px-8 py-3 lg:py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 lg:gap-4">
            <Image src="/logo-new.png" alt="Explorion Logo" width={36} height={36} className="object-contain drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]" />
            <div className="font-mono text-white text-xl lg:text-2xl font-bold tracking-widest italic transform -skew-x-12">
              Explorion
            </div>
            <div className="h-3 lg:h-4 w-px bg-white/40"></div>
            <span className="text-white/60 text-[8px] lg:text-[10px] font-mono">EST. 2025</span>
          </div>

          <div className="hidden lg:flex items-center gap-3 text-[10px] font-mono text-white/60">
            <span>SYS.STATUS: ONLINE</span>
            <div className="w-1 h-1 bg-[#7dd19b] rounded-full animate-pulse shadow-[0_0_8px_#7dd19b]"></div>
          </div>
        </div>
      </motion.div>

      {/* Corner Frame Accents */}
      <div className="absolute top-0 left-0 w-8 h-8 lg:w-12 lg:h-12 border-t-2 border-l-2 border-white/30 z-20"></div>
      <div className="absolute top-0 right-0 w-8 h-8 lg:w-12 lg:h-12 border-t-2 border-r-2 border-white/30 z-20"></div>
      <div className="absolute left-0 w-8 h-8 lg:w-12 lg:h-12 border-b-2 border-l-2 border-white/30 z-20" style={{ bottom: '5vh' }}></div>
      <div className="absolute right-0 w-8 h-8 lg:w-12 lg:h-12 border-b-2 border-r-2 border-white/30 z-20" style={{ bottom: '5vh' }}></div>

      {/* CTA Content */}
      <div className="relative z-10 flex min-h-screen items-center justify-end pt-24 lg:pt-0" style={{ marginTop: '5vh' }}>
        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="w-full lg:w-1/2 px-6 lg:px-16 lg:pr-[10%]"
        >
          <div className="max-w-xl relative lg:ml-auto">
            {/* Top decorative line */}
            <div className="flex items-center gap-2 mb-3 opacity-60">
              <div className="w-8 h-px bg-white"></div>
              <span className="text-white text-[10px] font-mono tracking-wider">∞</span>
              <div className="flex-1 h-px bg-white"></div>
            </div>

            {/* Title with dithered accent */}
            <div className="relative">
              <div className="hidden lg:block absolute -right-3 top-0 bottom-0 w-1 dither-pattern opacity-40"></div>
              <h1 className="text-3xl lg:text-5xl font-bold text-white mb-3 lg:mb-4 leading-tight font-mono tracking-wider whitespace-nowrap lg:-ml-[5%]" style={{ letterSpacing: '0.1em' }}>
                DECODE THE COMPLEX
              </h1>
            </div>

            {/* Decorative dots pattern - desktop only */}
            <div className="hidden lg:flex gap-1 mb-3 opacity-40">
              {Array.from({ length: 40 }).map((_, i) => (
                <div key={i} className="w-0.5 h-0.5 bg-white rounded-full"></div>
              ))}
            </div>

            {/* Description */}
            <div className="relative">
              <p className="text-xs lg:text-sm text-gray-300 mb-2 leading-relaxed font-mono opacity-80 max-w-md">
                Generate long-form animated explanation videos. Paste an arXiv paper, GitHub repo, or technical blog to visualize architectures, math, and concepts.
              </p>

              {/* Universal Input Form */}
              <UniversalInputForm />
            </div>

            {/* Bottom technical notation - desktop only */}
            <div className="hidden lg:flex items-center gap-2 mt-6 opacity-40">
              <span className="text-white text-[9px] font-mono">∞</span>
              <div className="flex-1 h-px bg-white"></div>
              <span className="text-white text-[9px] font-mono">UIMIX.PROTOCOL</span>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Bottom Footer */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.4 }}
        className="absolute left-0 right-0 z-20 border-t border-white/20 bg-black/40 backdrop-blur-sm" style={{ bottom: '5vh' }}
      >
        <div className="container mx-auto px-4 lg:px-8 py-2 lg:py-3 flex items-center justify-between">
          <div className="flex items-center gap-3 lg:gap-6 text-[8px] lg:text-[9px] font-mono text-white/50">
            <span className="hidden lg:inline">ENGINE.ACTIVE</span>
            <span className="lg:hidden">ENG.ACT</span>
            <div className="hidden lg:flex gap-1">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="w-1 h-3 bg-white/30 animate-pulse" style={{ height: `${Math.random() * 12 + 4}px`, animationDelay: `${i * 0.1}s` }}></div>
              ))}
            </div>
            <span>V2.0.0</span>
          </div>

          <div className="flex items-center gap-4 text-[8px] lg:text-[9px] font-mono text-white/50">
            <a href="/reader" className="hover:text-white transition-colors">DOC_READER_&gt;</a>
            <a href="/dashboard" className="hover:text-white transition-colors">DASHBOARD_&gt;</a>
            <div className="flex items-center gap-2">
              <span className="hidden lg:inline">◐ RENDERING</span>
              <div className="flex gap-1">
                <div className="w-1 h-1 bg-white/60 rounded-full animate-pulse"></div>
                <div className="w-1 h-1 bg-white/40 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-1 h-1 bg-white/20 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </main >
  );
}
