/** Wilson 95% score interval for a proportion.
 *
 * Every headline on this page is a rate estimated from a finite sample, and the
 * whole argument of the paper is that this field reports such rates without
 * saying how sure it is. Printing a bare point estimate here would repeat the
 * mistake we are documenting, so nothing is shown without its interval.
 *
 * NOT WALD, which is what this used to be. Wald is p +/- 1.96*sqrt(p(1-p)/n),
 * and its width goes to ZERO as p approaches 0 or 1 — so a 63/63 detection rate
 * renders as "100.0% [100.0, 100.0]", claiming perfect certainty from a finite
 * sample. That is exactly the unqualified rate this page exists to object to,
 * and the head-to-head in section 05 sits at 33/34, right where Wald breaks.
 * Wilson stays inside (0,1) and keeps a sane width at the boundary.
 *
 * The backend uses the identical estimator, so a number quoted in the paper and
 * the same number on this page cannot disagree.
 */
export function ci95(k: number, n: number): { p: number; lo: number; hi: number; halfWidth: number } | null {
  if (!n || n <= 0) return null;
  const z = 1.96;
  const p = k / n;
  const d = 1 + (z * z) / n;
  const centre = (p + (z * z) / (2 * n)) / d;
  const half = (z / d) * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n));
  const lo = Math.max(0, centre - half);
  const hi = Math.min(1, centre + half);
  return { p, lo, hi, halfWidth: half };
}

/** "29.4% [26.8, 32.2]" — the form every rate on the page takes. */
export function fmtCI(k: number, n: number): string {
  const c = ci95(k, n);
  if (!c) return "—";
  return `${(c.p * 100).toFixed(1)}% [${(c.lo * 100).toFixed(1)}, ${(c.hi * 100).toFixed(1)}]`;
}

/** Do two proportions' 95% intervals fail to overlap?
 *  Used to say plainly whether a claimed gap is supported or merely suggested. */
export function separated(k1: number, n1: number, k2: number, n2: number): boolean {
  const a = ci95(k1, n1), b = ci95(k2, n2);
  if (!a || !b) return false;
  return a.hi < b.lo || b.hi < a.lo;
}
