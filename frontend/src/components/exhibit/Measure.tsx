import { useEffect, useRef, useState } from "react";
import { EX, MONO, M, T } from "../../lib/exhibit-theme";
import { ci95 } from "../../lib/stats";

/** Shared measurement primitives.
 *
 * Every rate on this page is drawn the same way: a point estimate sitting on
 * its 95% interval, on a common 0–100% scale. That is the page's identity and
 * also its argument — the paper's claim is that this field reports rates
 * without their uncertainty, so a page that showed bare numbers would undercut
 * itself in its own typography.
 *
 * A shared scale is what makes the intervals comparable at a glance: a wide bar
 * is visibly a weak claim next to a narrow one, with no arithmetic asked of the
 * reader.
 */


/** Reveal-on-scroll must FAIL VISIBLE.
 *
 * IntersectionObserver does not fire in a tab that is not compositing frames
 * (backgrounded, off-screen, some embedded/preview contexts, and some remote
 * desktop setups). This project has already been bitten by the same class of
 * bug once: requestAnimationFrame is suspended in a background tab, which froze
 * the scan replay mid-run.
 *
 * If the observer never fires and reveal is the only path to visibility, the
 * page renders BLANK. During a panel review that is unrecoverable. So every
 * reveal carries a timer that shows the content regardless — the animation is
 * an enhancement, never the thing standing between a reader and the evidence.
 */
const REVEAL_FALLBACK_MS = 900;

function isOnScreen(el: Element) {
  const r = el.getBoundingClientRect();
  return r.top < window.innerHeight && r.bottom > 0 && r.width > 0;
}

/** Reveal on scroll. Structure-revealing only — the interval draws to its true
 *  width, so the motion IS the measurement arriving, not decoration.
 *  Honours prefers-reduced-motion by rendering the final state immediately. */
export function Reveal({
  children, delay = 0, as: As = "div",
}: { children: React.ReactNode; delay?: number; as?: any }) {
  const ref = useRef<HTMLElement | null>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) { setShown(true); return; }
    const el = ref.current;
    if (!el) return;
    // A one-shot observer: once revealed it never re-hides, so scrolling back up
    // does not replay animations and turn the page into a slideshow.
    if (isOnScreen(el)) { setShown(true); return; }
    const io = new IntersectionObserver(
      (es) => es.forEach((e) => { if (e.isIntersecting) { setShown(true); io.disconnect(); } }),
      { rootMargin: "0px 0px -12% 0px", threshold: 0.08 }
    );
    io.observe(el);
    const t = window.setTimeout(() => setShown(true), REVEAL_FALLBACK_MS);
    return () => { io.disconnect(); window.clearTimeout(t); };
  }, []);

  return (
    <As
      ref={ref as any}
      style={{
        opacity: shown ? 1 : 0,
        transform: shown ? "none" : "translateY(10px)",
        transition: `opacity ${M.base}ms ${M.ease} ${delay}ms, transform ${M.base}ms ${M.ease} ${delay}ms`,
      }}
    >
      {children}
    </As>
  );
}

/** Has this element been scrolled into view? Drives the bar/interval draw. */
function useInView<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) { setInView(true); return; }
    const el = ref.current;
    if (!el) return;
    if (isOnScreen(el)) { setInView(true); return; }
    const io = new IntersectionObserver(
      (es) => es.forEach((e) => { if (e.isIntersecting) { setInView(true); io.disconnect(); } }),
      { threshold: 0.25 }
    );
    io.observe(el);
    const t = window.setTimeout(() => setInView(true), REVEAL_FALLBACK_MS);
    return () => { io.disconnect(); window.clearTimeout(t); };
  }, []);
  return { ref, inView };
}

/** THE core mark: a rate as a point on its interval, on a 0–100% scale.
 *
 * Spec notes: 2px interval line, an >=8px point marker with a 2px surface ring
 * so it stays separable where it overlaps the line, and a recessive tick scale.
 * The value is direct-labelled; the axis is not repeated per row. */
export function IntervalBar({
  k, n, label, tone = "data", sub,
}: { k: number; n: number; label: string; tone?: "data" | "signal"; sub?: string }) {
  const { ref, inView } = useInView<HTMLDivElement>();
  const c = ci95(k, n);
  if (!c) return null;
  const col = tone === "signal" ? EX.signal : EX.data;
  const pct = (x: number) => `${x * 100}%`;

  return (
    <div ref={ref} style={{ padding: "14px 0", borderBottom: `1px solid ${EX.hairline}` }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12, marginBottom: 9 }}>
        <span style={{ fontSize: T.body, color: EX.ink }}>{label}</span>
        <span style={{ fontFamily: MONO, fontSize: T.small, color: EX.ink, whiteSpace: "nowrap" }}>
          {(c.p * 100).toFixed(1)}%
          <span style={{ color: EX.slate }}>
            {" "}[{(c.lo * 100).toFixed(1)}–{(c.hi * 100).toFixed(1)}]
          </span>
        </span>
      </div>

      <div style={{ position: "relative", height: 18 }}>
        {/* recessive 0/25/50/75/100 calibration ticks */}
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <div key={t} style={{
            position: "absolute", left: pct(t), top: 4, bottom: 4, width: 1,
            background: EX.tick, opacity: t === 0 || t === 1 ? 0.9 : 0.5,
          }} />
        ))}
        {/* the interval — draws from the point estimate outwards to true width */}
        <div style={{
          position: "absolute", top: 8, height: 2, background: col, opacity: 0.45,
          left: inView ? pct(c.lo) : pct(c.p),
          width: inView ? pct(c.hi - c.lo) : "0%",
          transition: `left ${M.slow}ms ${M.ease}, width ${M.slow}ms ${M.ease}`,
        }} />
        {/* interval end caps */}
        {inView && [c.lo, c.hi].map((x, i) => (
          <div key={i} style={{
            position: "absolute", left: pct(x), top: 4, width: 1.5, height: 10,
            background: col, opacity: 0.7, transition: `opacity ${M.base}ms ${M.ease} ${M.slow}ms`,
          }} />
        ))}
        {/* the point estimate: >=8px marker, 2px surface ring */}
        <div style={{
          position: "absolute", left: pct(c.p), top: 3,
          width: 11, height: 11, marginLeft: -5.5, borderRadius: 11,
          background: col, border: `2px solid ${EX.surface}`, boxSizing: "content-box",
          transform: inView ? "scale(1)" : "scale(0.3)",
          transition: `transform ${M.base}ms ${M.ease}`,
        }} />
      </div>

      <div style={{ fontFamily: MONO, fontSize: T.micro, color: EX.slate, marginTop: 6 }}>
        n = {n}{sub ? ` · ${sub}` : ""}
      </div>
    </div>
  );
}

/** A headline rate. Same information as IntervalBar, sized to carry a section. */
export function StatCard({
  k, n, label, tone = "data", note,
}: { k: number; n: number; label: string; tone?: "data" | "signal"; note?: string }) {
  const { ref, inView } = useInView<HTMLDivElement>();
  const c = ci95(k, n);
  const col = tone === "signal" ? EX.signal : EX.data;
  return (
    <div ref={ref} style={{
      border: `1px solid ${EX.hairline}`, background: EX.surfaceLift, padding: "18px 20px",
    }}>
      <div style={{ fontFamily: MONO, fontSize: T.micro, color: EX.inkMuted, letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 10 }}>
        {label}
      </div>
      <div style={{
        fontFamily: MONO, fontSize: T.stat, lineHeight: 1, color: EX.ink,
        opacity: inView ? 1 : 0, transform: inView ? "none" : "translateY(5px)",
        transition: `opacity ${M.base}ms ${M.ease}, transform ${M.base}ms ${M.ease}`,
      }}>
        {c ? `${(c.p * 100).toFixed(1)}%` : "—"}
      </div>
      {/* the interval, in miniature, under the number */}
      {c && (
        <div style={{ position: "relative", height: 9, marginTop: 12 }}>
          <div style={{ position: "absolute", left: 0, right: 0, top: 4, height: 1, background: EX.tick }} />
          <div style={{
            position: "absolute", top: 3.5, height: 2, background: col,
            left: `${c.lo * 100}%`, width: inView ? `${(c.hi - c.lo) * 100}%` : "0%",
            transition: `width ${M.slow}ms ${M.ease}`,
          }} />
          <div style={{
            position: "absolute", left: `${c.p * 100}%`, top: 0, width: 9, height: 9,
            marginLeft: -4.5, borderRadius: 9, background: col,
            border: `2px solid ${EX.surfaceLift}`, boxSizing: "content-box",
          }} />
        </div>
      )}
      <div style={{ fontFamily: MONO, fontSize: T.micro, color: EX.slate, marginTop: 9 }}>
        {c ? `95% CI ${(c.lo * 100).toFixed(1)}–${(c.hi * 100).toFixed(1)} · n=${n}` : ""}
      </div>
      {note && (
        <div style={{ fontSize: T.small, color: EX.inkMuted, marginTop: 8, lineHeight: 1.5 }}>{note}</div>
      )}
    </div>
  );
}

/** Proportion bar for counts that are not rates (coverage, scored/attempted).
 *  Kept visually distinct from IntervalBar so the reader never mistakes a raw
 *  proportion for an estimate carrying uncertainty. */
export function CountBar({
  scored, total, label, tone = "data",
}: { scored: number; total: number; label: string; tone?: "data" | "signal" }) {
  const { ref, inView } = useInView<HTMLDivElement>();
  const col = tone === "signal" ? EX.signal : EX.data;
  return (
    <div ref={ref} style={{ marginBottom: 13 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5, gap: 10 }}>
        <span style={{ fontSize: T.small, color: EX.ink }}>{label}</span>
        <span style={{ fontFamily: MONO, fontSize: T.micro, color: EX.slate }}>{scored}/{total}</span>
      </div>
      <div style={{ height: 14, background: "rgba(22,21,15,0.055)" }}>
        <div style={{
          height: "100%", background: col,
          width: inView ? `${(scored / total) * 100}%` : "0%",
          transition: `width ${M.slow}ms ${M.ease}`,
          borderRadius: "0 3px 3px 0",
        }} />
      </div>
    </div>
  );
}
