// ─────────────────────────────────────────────────────────────────────────────
// The motion layer.
//
// Two libraries, both pulled from their public repos:
//   lenis  (darkroomengineering/lenis) — momentum scrolling
//   gsap   (greensock/GSAP) + ScrollTrigger — scroll-driven animation
//
// They must share ONE clock. Lenis hijacks scrolling with its own rAF loop, so
// if ScrollTrigger keeps listening to native scroll events it reads positions
// one frame stale and every pinned section judders. The fix is to drive Lenis
// FROM gsap.ticker and feed its scroll callback INTO ScrollTrigger.update, so
// there is a single source of truth per frame. That wiring lives in
// SmoothScroll and nowhere else.
//
// REDUCED MOTION IS A FULL BYPASS, NOT A SHORTER DURATION. If the viewer asked
// for less motion, Lenis is never constructed (native scrolling is restored),
// no ScrollTrigger is created, reveals mount visible, and counters print their
// final value. A reveal that animates "quickly" still animates; a pinned
// section with motion disabled is a scroll trap. The only safe version of this
// layer for that viewer is its absence — which is also why every Reveal below
// defaults to opacity 1 in markup and is hidden by script, so a JS failure
// leaves a readable page rather than a blank one.
// ─────────────────────────────────────────────────────────────────────────────

import React, { useEffect, useRef, useState } from "react";
import Lenis from "lenis";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true
  );
}

/* ── smooth scroll ──────────────────────────────────────────────────────── */

let lenisRef: Lenis | null = null;

/* Scroll subscribers.
 *
 * Needed because there is no single event that covers both cases: Lenis emits
 * its own "scroll" only for motion IT drives, and the native scroll event does
 * NOT fire during a Lenis scroll at all (measured: scrollY advanced 900 -> 1020
 * with a listener attached and zero calls). So anything tracking scroll
 * position has to hear from both, and this is the one place that fan-out
 * lives. */
const scrollSubs = new Set<() => void>();

/* ── IntersectionObserver liveness ──────────────────────────────────────────
 *
 * Reveals hide themselves in CSS and rely on an IO callback to unhide. That is
 * safe only if IO actually delivers, and it does not always: in a
 * non-compositing context the intersection step of the rendering lifecycle is
 * skipped along with rAF, so observers are registered and never called. The
 * symptom was four pages rendering with every section at opacity 0.
 *
 * So the first IO callback anywhere on the site marks IO as alive; if nothing
 * has arrived shortly after the first Reveal mounts, IO is declared dead and a
 * class on <html> unhides everything. Scroll-triggered reveals still behave
 * normally whenever IO works -- this only costs the animation, never the
 * content. A per-element timeout would instead reveal the whole document up
 * front and lose the effect for everyone. */
let ioAlive = false;
let ioProbeStarted = false;

export function markIoAlive() {
  ioAlive = true;
}

function startIoProbe() {
  if (ioProbeStarted) return;
  ioProbeStarted = true;
  window.setTimeout(() => {
    if (!ioAlive) document.documentElement.classList.add("te-io-dead");
  }, 1500);
}

export function onScrollChange(cb: () => void): () => void {
  scrollSubs.add(cb);
  window.addEventListener("scroll", cb, { passive: true });
  window.addEventListener("resize", cb);
  return () => {
    scrollSubs.delete(cb);
    window.removeEventListener("scroll", cb);
    window.removeEventListener("resize", cb);
  };
}

/** Jump to top without a 3-second glide. Used on route change: a hash route
 *  that animates back to the top makes every nav click feel broken. */
export function scrollToTopImmediate() {
  /* Both, deliberately. The native call is what actually guarantees the new
   * route starts at the top -- Lenis applies its own scrollTo inside a rAF, so
   * if frames are not running the route change would silently leave the reader
   * part-way down a different page. The Lenis call then resyncs its internal
   * position, without which its next wheel event would animate back from the
   * old offset. */
  window.scrollTo({ top: 0, behavior: "auto" });
  lenisRef?.scrollTo(0, { immediate: true });
  // Pins and triggers were measured against the OUTGOING page's height.
  requestAnimationFrame(() => ScrollTrigger.refresh());
}

/** Bring an element to rest just under the sticky nav.
 *
 *  Both paths again, for the reason scrollToTopImmediate documents: Lenis
 *  drives its scrollTo from inside a rAF, and rAF has been measured at 0
 *  ticks/second in a non-compositing context -- so the Lenis call alone can
 *  silently do nothing and leave the reader looking at the wrong part of the
 *  page. The native smooth scroll is the guarantee; the Lenis call keeps its
 *  internal position in sync so the next wheel event does not jump back. */
export function scrollElementIntoView(el: HTMLElement, offset = 88) {
  const top = el.getBoundingClientRect().top + window.scrollY - offset;
  if (prefersReducedMotion()) {
    window.scrollTo({ top, behavior: "auto" });
    lenisRef?.scrollTo(top, { immediate: true });
    return;
  }
  const before = window.scrollY;
  window.scrollTo({ top, behavior: "smooth" });
  lenisRef?.scrollTo(top, { duration: 0.75 });

  /* ...and a hard landing if neither engaged.
   *
   * Measured: in a non-compositing context a smooth scrollTo does nothing at
   * all -- scrollY sat at 0 while the target was 1068px down the page. Lenis
   * cannot cover for it there either, since it drives from rAF. Without this
   * the reader presses the button and the animation plays off-screen, which is
   * the exact failure this function exists to prevent.
   *
   * Only corrects when the page has not moved AT ALL, so a reader who scrolled
   * somewhere themselves in the meantime is never yanked back. */
  window.setTimeout(() => {
    if (window.scrollY === before && Math.abs(before - top) > 8) {
      window.scrollTo({ top, behavior: "auto" });
      lenisRef?.scrollTo(top, { immediate: true });
    }
  }, 650);
}

export function SmoothScroll({ children }: { children: React.ReactNode }) {
  /* Adding this class from script is what makes the reveal styles safe: the
   * hidden state only exists once JS is known to be running. See index.css. */
  useEffect(() => {
    document.documentElement.classList.add("te-motion");
    return () => document.documentElement.classList.remove("te-motion");
  }, []);

  useEffect(() => {
    if (prefersReducedMotion()) return;

    const lenis = new Lenis({
      // 1.1s to settle: long enough to read as weight, short enough that a
      // reviewer scanning for a number does not feel held back.
      duration: 1.1,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      // Touch is left native. Mobile browsers already have momentum, and
      // doubling it is the thing that makes "smooth scroll" sites unusable
      // on a phone.
      syncTouch: false,
    });
    lenisRef = lenis;

    const onScroll = () => {
      ScrollTrigger.update();
      scrollSubs.forEach((cb) => cb());
    };
    lenis.on("scroll", onScroll);

    const raf = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(raf);
    // lagSmoothing lets GSAP skip time after a long frame; with an external
    // scroll driver that desynchronises Lenis from ScrollTrigger on any hitch.
    gsap.ticker.lagSmoothing(0);

    return () => {
      lenis.off("scroll", onScroll);
      gsap.ticker.remove(raf);
      gsap.ticker.lagSmoothing(500, 33);
      lenis.destroy();
      lenisRef = null;
    };
  }, []);

  return <>{children}</>;
}

/* ── reveal on scroll ───────────────────────────────────────────────────── */

/**
 * Fade + rise as the element enters. `stagger` animates direct children
 * instead of the wrapper, which is what grids and lists want.
 *
 * `once` is deliberately the default: an element that re-animates every time
 * it scrolls back into view turns a long document into a flicker.
 */
export function Reveal({
  children,
  delay = 0,
  stagger,
  style,
  as: As = "div",
}: {
  children: React.ReactNode;
  /** Kept for call-site compatibility; the distance is set in CSS now. */
  y?: number;
  delay?: number;
  stagger?: number;
  style?: React.CSSProperties;
  as?: "div" | "section" | "span";
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const targets: HTMLElement[] =
      stagger != null
        ? (Array.from(el.children) as HTMLElement[])
        : [el];
    if (!targets.length) return;

    targets.forEach((t, i) => {
      t.dataset.reveal = "";
      const ms = (delay + (stagger ?? 0) * i) * 1000;
      if (ms) t.style.setProperty("--reveal-delay", `${ms}ms`);
    });

    // IntersectionObserver rather than a scroll handler: it fires without an
    // animation frame and without a scroll event, both of which can be
    // absent (see index.css). Once in, the observer is done with that node.
    const io = new IntersectionObserver(
      (entries) => {
        markIoAlive();
        for (const e of entries) {
          if (e.isIntersecting) {
            (e.target as HTMLElement).classList.add("is-in");
            io.unobserve(e.target);
          }
        }
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.01 }
    );
    targets.forEach((t) => io.observe(t));
    startIoProbe();

    return () => {
      io.disconnect();
      targets.forEach((t) => {
        delete t.dataset.reveal;
        t.classList.remove("is-in");
        t.style.removeProperty("--reveal-delay");
      });
    };
  }, [delay, stagger]);

  return (
    <As ref={ref as React.Ref<HTMLDivElement>} style={style}>
      {children}
    </As>
  );
}

/* ── animated numerals ──────────────────────────────────────────────────── */

/**
 * Counts every numeric run in a string up from zero, preserving everything
 * around them — so "45.9%", "2,142", "$0", "1,125 : 1,125" and "7–8%" all
 * work without each caller pre-splitting its value.
 *
 * Decimal places and thousands separators are read back off the source token,
 * because "89.1%" must not land on "89%" and "2142" must not land on "2,142"
 * unless it started that way.
 */
export function CountUp({
  value,
  duration = 1.25,
  style,
}: {
  value: string;
  duration?: number;
  style?: React.CSSProperties;
}) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion()) return;

    const parts = value.split(/([\d][\d.,]*)/);
    const specs = parts
      .map((p, i) => ({ p, i }))
      .filter(({ p }) => /^[\d][\d.,]*$/.test(p))
      .map(({ p, i }) => {
        const grouped = p.includes(",");
        const dot = p.lastIndexOf(".");
        // A trailing "." group of <= 2 digits is a decimal; otherwise the dot
        // belongs to a version-like token and the value is an integer.
        const decimals =
          dot >= 0 && p.length - dot - 1 <= 2 ? p.length - dot - 1 : 0;
        return { i, target: parseFloat(p.replace(/,/g, "")), grouped, decimals };
      });
    if (!specs.length) return;

    const fmt = (n: number, sp: (typeof specs)[number]) => {
      const f = n.toFixed(sp.decimals);
      return sp.grouped
        ? Number(f).toLocaleString(undefined, {
            minimumFractionDigits: sp.decimals,
            maximumFractionDigits: sp.decimals,
          })
        : f;
    };
    const paint = (t: number) => {
      const out = [...parts];
      for (const sp of specs) out[sp.i] = fmt(sp.target * t, sp);
      el.textContent = out.join("");
    };

    let raf = 0;
    let safety = 0;
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      cancelAnimationFrame(raf);
      clearTimeout(safety);
      el.textContent = value; // the true value, exactly as authored
    };

    const run = () => {
      const t0 = performance.now();
      const step = (now: number) => {
        const t = Math.min(1, (now - t0) / (duration * 1000));
        // easeOutCubic
        paint(1 - Math.pow(1 - t, 3));
        if (t < 1) raf = requestAnimationFrame(step);
        else finish();
      };
      paint(0);
      raf = requestAnimationFrame(step);

      /* The guarantee. If rAF never fires -- measured at 0 ticks/second in a
       * non-compositing context -- the loop above would leave this element
       * reading "0" forever, turning every headline figure on the site into a
       * zero. This timer force-writes the real value slightly after the
       * animation should have ended, so the worst case is a number that
       * appears without counting rather than a wrong number. */
      safety = window.setTimeout(finish, duration * 1000 + 400);
    };

    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          io.disconnect();
          run();
        }
      },
      { threshold: 0.2 }
    );
    io.observe(el);

    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
      clearTimeout(safety);
      el.textContent = value;
    };
  }, [value, duration]);

  return (
    <span ref={ref} style={style}>
      {value}
    </span>
  );
}

/* ── scroll progress ────────────────────────────────────────────────────── */

/** A 2px rule under the nav. On a document this long, it is the only cheap
 *  signal of "how much of this argument is left". */
export function ScrollProgress({ color }: { color: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    /* Computed here rather than handed to ScrollTrigger. A ScrollTrigger with
     * no trigger element recomputes its progress only on refresh, so the
     * first version of this bar held one stale value for the whole page
     * (measured 0.568 while scrollY was 1762). This reads the position
     * directly and is told when to look by onScrollChange, which covers both
     * Lenis-driven and native scrolling. */
    const update = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      const p = max <= 0 ? 0 : Math.min(1, Math.max(0, window.scrollY / max));
      el.style.transform = `scaleX(${p})`;
    };

    update();
    return onScrollChange(update);
  }, []);

  return (
    <div
      aria-hidden
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: -1,
        height: 2,
        background: color,
        transformOrigin: "0 50%",
        transform: "scaleX(0)",
        willChange: "transform",
      }}
      ref={ref}
    />
  );
}

/* ── headline word reveal ───────────────────────────────────────────────── */

/**
 * Per-word rise, clipped. Words are wrapped in an overflow-hidden span so each
 * one appears to lift off its own baseline instead of fading in place.
 *
 * Splitting on whitespace only — never on characters. Per-character animation
 * on a 14-word headline is the single most common way these sites become
 * unreadable, and a screen reader announces a char-split heading one letter
 * at a time.
 */
export function SplitWords({
  text,
  style,
  delay = 0,
}: {
  text: string;
  style?: React.CSSProperties;
  delay?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion()) return;
    const words = el.querySelectorAll("[data-w]");
    if (!words.length) return;

    const anim = gsap.fromTo(
      words,
      { yPercent: 115 },
      {
        yPercent: 0,
        duration: 0.9,
        ease: "power3.out",
        stagger: 0.045,
        delay,
      }
    );
    return () => {
      anim.kill();
      gsap.set(words, { clearProps: "transform" });
    };
  }, [text, delay]);

  return (
    <span ref={ref} style={style}>
      {text.split(" ").map((w, i) => (
        <span
          key={i}
          style={{
            display: "inline-block",
            overflow: "hidden",
            verticalAlign: "bottom",
            // Descenders (g, y, p) are clipped by overflow:hidden at exactly
            // the line box, so the box is opened up and pulled back.
            paddingBottom: "0.12em",
            marginBottom: "-0.12em",
          }}
        >
          <span data-w style={{ display: "inline-block", willChange: "transform" }}>
            {w}
            {i < text.split(" ").length - 1 ? " " : ""}
          </span>
        </span>
      ))}
    </span>
  );
}

/* ── pointer-reactive lift ──────────────────────────────────────────────── */

/**
 * A card that tilts a degree or two toward the cursor. Deliberately tiny:
 * the effect should register as responsiveness, not as a gimmick, and a
 * strong tilt on a card full of 11px tabular numbers makes them unreadable
 * mid-motion.
 */
export function Tilt({
  children,
  style,
  max = 1.6,
}: {
  children: React.ReactNode;
  style?: React.CSSProperties;
  max?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [enabled] = useState(() => !prefersReducedMotion());

  useEffect(() => {
    const el = ref.current;
    if (!el || !enabled) return;
    // Pointer tilt is meaningless on touch and fires as a stuck hover state.
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;

    const q = gsap.quickTo(el, "rotateY", { duration: 0.5, ease: "power2.out" });
    const qx = gsap.quickTo(el, "rotateX", { duration: 0.5, ease: "power2.out" });
    const qy = gsap.quickTo(el, "y", { duration: 0.5, ease: "power2.out" });

    const move = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      q(((e.clientX - r.left) / r.width - 0.5) * 2 * max);
      qx(-((e.clientY - r.top) / r.height - 0.5) * 2 * max);
      qy(-3);
    };
    const leave = () => {
      q(0);
      qx(0);
      qy(0);
    };

    el.addEventListener("pointermove", move);
    el.addEventListener("pointerleave", leave);
    return () => {
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerleave", leave);
      gsap.killTweensOf(el);
    };
  }, [enabled, max]);

  return (
    <div
      ref={ref}
      style={{ ...style, transformStyle: "preserve-3d", willChange: "transform" }}
    >
      {children}
    </div>
  );
}

export { ScrollTrigger, gsap };
