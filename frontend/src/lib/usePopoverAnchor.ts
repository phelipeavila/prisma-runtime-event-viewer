import { useCallback, useLayoutEffect, useRef, useState } from "react";

export type AnchorSide = "left" | "right";

/**
 * Measures the trigger element's bounding rect against the viewport and
 * decides whether the popover should anchor to the trigger's left edge
 * (extending right) or right edge (extending left). Picks whichever side
 * has more horizontal space, so the popover never clips off-screen.
 *
 * Returns a callback ref to attach to the trigger element, plus the chosen
 * anchor side.
 */
export function usePopoverAnchor<T extends HTMLElement>(
  open: boolean,
  estimatedWidth = 320
): { setTrigger: (el: T | null) => void; side: AnchorSide } {
  const ref = useRef<T | null>(null);
  const [side, setSide] = useState<AnchorSide>("left");

  const recompute = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const spaceRight = vw - rect.left;
    const spaceLeft = rect.right;
    setSide(spaceRight >= estimatedWidth || spaceRight >= spaceLeft ? "left" : "right");
  }, [estimatedWidth]);

  useLayoutEffect(() => {
    if (open) recompute();
  }, [open, recompute]);

  const setTrigger = useCallback((el: T | null) => {
    ref.current = el;
    if (el && open) recompute();
  }, [open, recompute]);

  return { setTrigger, side };
}
