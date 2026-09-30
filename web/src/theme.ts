import { useEffect, useState } from "react";

// Reads the CSS tokens into JS so SVG/Recharts marks use the same, mode-aware colours.
export function readVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888";
}

export function useThemeTick(): number {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const bump = () => setTick((t) => t + 1);
    mq.addEventListener("change", bump);
    const obs = new MutationObserver(bump);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => {
      mq.removeEventListener("change", bump);
      obs.disconnect();
    };
  }, []);
  return tick;
}

export function useColors() {
  const tick = useThemeTick();
  const [c, setC] = useState(() => snapshot());
  useEffect(() => setC(snapshot()), [tick]);
  return c;
}

function snapshot() {
  const v = readVar;
  return {
    ink: v("--ink"), ink2: v("--ink-2"), muted: v("--muted"), grid: v("--grid"), axis: v("--axis"),
    surface: v("--surface"), deemph: v("--deemph"), accent: v("--accent"),
    series: ["--series-1", "--series-2", "--series-3", "--series-4", "--series-5", "--series-6"].map(v),
    seq: ["--seq-0", "--seq-1", "--seq-2", "--seq-3"].map(v),
    status: (k: string) => v(k),
  };
}
