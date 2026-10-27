import { RefObject, useEffect } from 'react';

// Sample the actual browser scheduler without causing React renders each frame.
// This is a local diagnostic, not a guarantee for other computers or workloads.
export function useFrameSample(ref: RefObject<HTMLElement>, enabled: boolean) {
  useEffect(() => {
    if (!enabled) {
      if (ref.current) ref.current.dataset.frameSample = JSON.stringify({status:'paused',reason:'Tab is hidden'});
      return;
    }
    let handle = 0;
    let previous = 0;
    const intervals: number[] = [];
    const sample = (now: number) => {
      if (previous) intervals.push(now - previous);
      previous = now;
      if (intervals.length < 180) handle = requestAnimationFrame(sample);
      else if (ref.current) {
        const sorted = [...intervals].sort((a, b) => a - b);
        ref.current.dataset.frameSample = JSON.stringify({
          frames: intervals.length,
          averageFPS: Math.round(1000 / (intervals.reduce((a, b) => a + b, 0) / intervals.length)),
          p95FrameMs: Math.round(sorted[Math.floor(sorted.length * .95)] * 10) / 10,
          over33ms: intervals.filter(n => n > 33).length,
          visibility: document.visibilityState,
        });
      }
    };
    handle = requestAnimationFrame(sample);
    return () => cancelAnimationFrame(handle);
  }, [enabled, ref]);
}
