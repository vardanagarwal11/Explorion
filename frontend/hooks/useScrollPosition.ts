"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type ScrollDirection = "up" | "down" | null;

type ScrollPositionState = {
  /** Current scroll Y position in pixels */
  scrollY: number;
  /** Scroll progress as percentage (0-100) */
  scrollProgress: number;
  /** Current scroll direction */
  direction: ScrollDirection;
  /** Whether the user is currently scrolling */
  isScrolling: boolean;
  /** Whether the page is scrolled past a threshold */
  isScrolled: boolean;
};

type UseScrollPositionOptions = {
  /** Threshold in pixels before isScrolled becomes true (default: 50) */
  threshold?: number;
  /** Debounce time in ms for isScrolling state (default: 150) */
  scrollEndDelay?: number;
  /** Enable/disable the hook (default: true) */
  enabled?: boolean;
};

/**
 * Track the current scroll position and direction.
 *
 * @example
 * const { scrollY, scrollProgress, direction, isScrolled } = useScrollPosition();
 */
export function useScrollPosition(
  options: UseScrollPositionOptions = {}
): ScrollPositionState {
  const { threshold = 50, scrollEndDelay = 150, enabled = true } = options;

  const [state, setState] = useState<ScrollPositionState>({
    scrollY: 0,
    scrollProgress: 0,
    direction: null,
    isScrolling: false,
    isScrolled: false,
  });

  const lastScrollY = useRef(0);
  const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;

    function calculateProgress(): number {
      const scrollHeight = document.documentElement.scrollHeight;
      const clientHeight = document.documentElement.clientHeight;
      const maxScroll = scrollHeight - clientHeight;
      if (maxScroll <= 0) return 0;
      return Math.min(100, (window.scrollY / maxScroll) * 100);
    }

    function handleScroll() {
      const currentY = window.scrollY;
      const direction: ScrollDirection =
        currentY > lastScrollY.current
          ? "down"
          : currentY < lastScrollY.current
            ? "up"
            : null;

      setState({
        scrollY: currentY,
        scrollProgress: calculateProgress(),
        direction,
        isScrolling: true,
        isScrolled: currentY > threshold,
      });

      lastScrollY.current = currentY;

      // Clear existing timeout
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }

      // Set isScrolling to false after delay
      scrollTimeoutRef.current = setTimeout(() => {
        setState((prev) => ({ ...prev, isScrolling: false }));
      }, scrollEndDelay);
    }

    // Initial state
    handleScroll();

    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("resize", handleScroll, { passive: true });

    return () => {
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("resize", handleScroll);
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, [enabled, threshold, scrollEndDelay]);

  return state;
}

/**
 * Track scroll position within a specific container element.
 *
 * @example
 * const ref = useRef<HTMLDivElement>(null);
 * const { scrollY, scrollProgress } = useContainerScroll(ref);
 */
export function useContainerScroll(
  containerRef: React.RefObject<HTMLElement | null>,
  options: Omit<UseScrollPositionOptions, "threshold"> = {}
): ScrollPositionState {
  const { scrollEndDelay = 150, enabled = true } = options;

  const [state, setState] = useState<ScrollPositionState>({
    scrollY: 0,
    scrollProgress: 0,
    direction: null,
    isScrolling: false,
    isScrolled: false,
  });

  const lastScrollY = useRef(0);
  const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!enabled || !container) return;

    function handleScroll() {
      if (!container) return;

      const currentY = container.scrollTop;
      const maxScroll = container.scrollHeight - container.clientHeight;
      const progress = maxScroll > 0 ? (currentY / maxScroll) * 100 : 0;

      const direction: ScrollDirection =
        currentY > lastScrollY.current
          ? "down"
          : currentY < lastScrollY.current
            ? "up"
            : null;

      setState({
        scrollY: currentY,
        scrollProgress: Math.min(100, progress),
        direction,
        isScrolling: true,
        isScrolled: currentY > 0,
      });

      lastScrollY.current = currentY;

      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }

      scrollTimeoutRef.current = setTimeout(() => {
        setState((prev) => ({ ...prev, isScrolling: false }));
      }, scrollEndDelay);
    }

    handleScroll();
    container.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      container.removeEventListener("scroll", handleScroll);
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, [containerRef, enabled, scrollEndDelay]);

  return state;
}

/**
 * Track which section is currently in view based on scroll position.
 *
 * @example
 * const { activeSection, visibleSections } = useSectionInView(sectionIds);
 */
export function useSectionInView(sectionIds: string[]): {
  activeSection: string | null;
  visibleSections: Set<string>;
  scrollToSection: (id: string) => void;
} {
  const [activeSection, setActiveSection] = useState<string | null>(
    sectionIds[0] ?? null
  );
  const [visibleSections, setVisibleSections] = useState<Set<string>>(
    new Set()
  );

  const scrollToSection = useCallback((id: string) => {
    const el = document.querySelector(`[data-section-id="${id}"]`);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || sectionIds.length === 0) return;

    const observers: IntersectionObserver[] = [];
    const sectionVisibility = new Map<string, number>();

    sectionIds.forEach((id) => {
      const el = document.querySelector(`[data-section-id="${id}"]`);
      if (!el) return;

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              sectionVisibility.set(id, entry.intersectionRatio);
              setVisibleSections((prev) => new Set([...prev, id]));
            } else {
              sectionVisibility.delete(id);
              setVisibleSections((prev) => {
                const next = new Set(prev);
                next.delete(id);
                return next;
              });
            }

            // Find the most visible section
            let maxRatio = 0;
            let maxId: string | null = null;
            sectionVisibility.forEach((ratio, sectionId) => {
              if (ratio > maxRatio) {
                maxRatio = ratio;
                maxId = sectionId;
              }
            });

            if (maxId) {
              setActiveSection(maxId);
            }
          });
        },
        {
          threshold: [0, 0.25, 0.5, 0.75, 1],
          rootMargin: "-10% 0px -10% 0px",
        }
      );

      observer.observe(el);
      observers.push(observer);
    });

    return () => {
      observers.forEach((obs) => obs.disconnect());
    };
  }, [sectionIds]);

  return { activeSection, visibleSections, scrollToSection };
}
