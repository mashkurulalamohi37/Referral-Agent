/**
 * Motion presets (plan §5). Durations mirror the CSS tokens; every preset collapses to an instant
 * change when the user prefers reduced motion (see usePresets).
 */

import { useReducedMotion, type Transition, type Variants } from 'motion/react';

export const duration = { fast: 0.12, base: 0.2, slow: 0.32 } as const;
export const easeOut = [0.16, 1, 0.3, 1] as const;

export const spring = {
  sheet: { type: 'spring', stiffness: 380, damping: 34 } as Transition,
  press: { type: 'spring', stiffness: 500, damping: 35 } as Transition,
  layout: { type: 'spring', stiffness: 420, damping: 36 } as Transition,
};

const instant: Transition = { duration: 0 };

export function usePresets() {
  const reduce = useReducedMotion() ?? false;
  const t = (transition: Transition): Transition => (reduce ? instant : transition);

  const page: Variants = {
    initial: { opacity: 0, y: reduce ? 0 : 16, filter: reduce ? 'none' : 'blur(4px)' },
    animate: { opacity: 1, y: 0, filter: 'blur(0px)', transition: t({ duration: 0.38, ease: easeOut }) },
    exit: { opacity: 0, y: reduce ? 0 : -8, filter: reduce ? 'none' : 'blur(2px)', transition: t({ duration: duration.fast }) },
  };

  /** Container + item variants for staggered lists (first 8 items only, plan §5). */
  const list: Variants = {
    animate: { transition: reduce ? {} : { staggerChildren: 0.04 } },
  };
  const item = (index = 0): Variants => ({
    initial: index < 8 && !reduce ? { opacity: 0, y: 12 } : { opacity: 1, y: 0 },
    animate: { opacity: 1, y: 0, transition: t({ duration: duration.base, ease: easeOut }) },
  });

  return { reduce, t, page, list, item, spring: reduce ? { sheet: instant, press: instant, layout: instant } : spring };
}
