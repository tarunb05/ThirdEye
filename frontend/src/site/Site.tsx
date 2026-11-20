import { useEffect, useState } from "react";
import { C, F } from "./design";
import { ScrollProgress, SmoothScroll, scrollToTopImmediate } from "./motion";
import { Overview } from "./pages/Overview";
import { HowItWorks } from "./pages/HowItWorks";
import { Datasets } from "./pages/Datasets";
import { Testing } from "./pages/Testing";
import { Findings } from "./pages/Findings";
import { Tool } from "./pages/Tool";
import { Team } from "./pages/Team";

/* Hash routing, no dependency.
 *
 * react-router would be the obvious choice and is not worth 15 kB here: there
 * are seven static routes and no nesting, params or guards. Hash routes also
 * survive being opened from the filesystem, which matters because this deck of
 * pages has to work from a USB stick in a review room with no network. */

const ROUTES = [
  { id: "overview", label: "Overview" },
  { id: "how", label: "How it works" },
  { id: "datasets", label: "Datasets" },
  { id: "testing", label: "Testing" },
  { id: "findings", label: "Findings" },
  { id: "tool", label: "Tool", highlight: true },
  { id: "team", label: "Team" },
] as const;

type RouteId = (typeof ROUTES)[number]["id"];

function currentRoute(): RouteId {
  const h = window.location.hash.replace(/^#\/?/, "");
  return (ROUTES.find((r) => r.id === h)?.id ?? "overview") as RouteId;
}

export function Site() {
  const [route, setRoute] = useState<RouteId>(currentRoute);

  useEffect(() => {
    const onHash = () => {
      setRoute(currentRoute());
      scrollToTopImmediate();
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  function go(id: string) {
    window.location.hash = `#/${id}`;
  }

  return (
    <SmoothScroll>
      <div style={{ background: C.bg, minHeight: "100vh", color: C.ink }}>
        <div className="te-grain" aria-hidden />
        <Nav route={route} go={go} />
        <main style={{ position: "relative", zIndex: 2 }}>
          {route === "overview" && <Overview go={go} />}
          {route === "how" && <HowItWorks />}
          {route === "datasets" && <Datasets />}
          {route === "testing" && <Testing />}
          {route === "findings" && <Findings />}
          {route === "tool" && <Tool />}
          {route === "team" && <Team />}
        </main>
        <Footer />
      </div>
    </SmoothScroll>
  );
}

function Nav({ route, go }: { route: string; go: (id: string) => void }) {
  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 20,
        background: "rgba(247,245,240,0.86)",
        backdropFilter: "blur(10px)",
        borderBottom: `1px solid ${C.line}`,
      }}
    >
      <ScrollProgress color={C.accent} />
      <nav
        style={{
          maxWidth: 1120,
          margin: "0 auto",
          padding: "0 28px",
          display: "flex",
          alignItems: "center",
          gap: 20,
          minHeight: 58,
          flexWrap: "wrap",
        }}
      >
        <button
          onClick={() => go("overview")}
          style={{
            background: "none",
            border: "none",
            padding: 0,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 9,
          }}
        >
          <Eye />
          <span
            style={{
              fontFamily: F.sans,
              fontSize: 15,
              fontWeight: 600,
              color: C.ink,
              letterSpacing: "-0.01em",
            }}
          >
            ThirdEye
          </span>
        </button>

        <div style={{ display: "flex", gap: 2, marginLeft: "auto", flexWrap: "wrap" }}>
          {ROUTES.filter((r) => r.id !== "overview").map((r) => {
            const on = route === r.id;
            const hl = "highlight" in r && r.highlight;
            return (
              <button
                key={r.id}
                onClick={() => go(r.id)}
                className="te-nav-link"
                data-on={on ? "1" : "0"}
                style={{
                  background: on ? C.accentGhost : "transparent",
                  border: hl && !on ? `1px solid ${C.accentDim}` : "1px solid transparent",
                  borderRadius: 6,
                  padding: "6px 11px",
                  fontFamily: F.sans,
                  fontSize: 13.5,
                  fontWeight: on ? 600 : 400,
                  color: on ? C.accent : hl ? C.accent : C.inkMid,
                  cursor: "pointer",
                }}
              >
                {r.label}
              </button>
            );
          })}
        </div>
      </nav>
    </header>
  );
}

function Eye() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12Z"
        stroke={C.accent}
        strokeWidth="1.6"
      />
      <circle cx="12" cy="12" r="2.6" fill={C.accent} />
    </svg>
  );
}

function Footer() {
  return (
    <footer
      style={{
        borderTop: `1px solid ${C.line}`,
        marginTop: 40,
        padding: "26px 28px 48px",
      }}
    >
      <div
        style={{
          maxWidth: 1120,
          margin: "0 auto",
          display: "flex",
          gap: 16,
          flexWrap: "wrap",
          alignItems: "baseline",
          fontFamily: F.sans,
          fontSize: 13,
          color: C.inkDim,
        }}
      >
        <span>
          ThirdEye — Capstone Project Phase 3, UE23CS441A · Department of CSE,
          PES University, Bengaluru
        </span>
        <a
          href="https://github.com/umarahmed10/third-eye-capstone"
          style={{ marginLeft: "auto", color: C.accent, textDecoration: "none" }}
        >
          Source on GitHub →
        </a>
      </div>
    </footer>
  );
}
