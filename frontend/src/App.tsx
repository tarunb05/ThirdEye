import { useState } from "react";
import type { User } from "./lib/api";
import { Layout, type Tab } from "./components/Layout";
import { Landing } from "./views/Landing";
import { Exhibit } from "./views/Exhibit";
import { Login } from "./views/Login";
import { Analyze } from "./views/Analyze";
import { History } from "./views/History";

const STORAGE_KEY = "te_user";

// Pre-login screens for an unauthenticated visitor.
type PublicScreen = "landing" | "login" | "trial";

// Synthetic user for anonymous / trial scans. streamCouncil never sends
// user_id and works with just { code }; createSession may fail for this id and
// is handled gracefully (anonymous scans still run).
const ANON_USER: User = { user_id: -1, username: "guest", token: "" };

export default function App() {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const s = localStorage.getItem(STORAGE_KEY);
      return s ? (JSON.parse(s) as User) : null;
    } catch {
      return null;
    }
  });
  const [screen, setScreen] = useState<PublicScreen>("landing");
  // The exhibit is the front door for EVERY visitor, not just logged-out ones.
  // It used to live inside the `if (!user)` branch, so anyone with a stored
  // session went straight to the app shell and never saw it — which on a review
  // laptop with a leftover login means the panel would never see the exhibit at
  // all. It is now a separate gate above the auth split, dismissed per tab
  // (sessionStorage) so returning within a session does not re-show it.
  // The exhibit IS the site — one URL, one scroll, one design system. The tool
  // is embedded in it, so entering the app shell is now an explicit opt-in for
  // the product-only features (sign-in, history, PDF export) rather than the
  // default destination.
  const [showExhibit, setShowExhibit] = useState<boolean>(true);

  function enterApp() {
    setShowExhibit(false);
    if (!user) setScreen("trial");
  }

  function backToExhibit() {
    setShowExhibit(true);
  }
  // Scan is the default landing tab inside the authenticated shell.
  const [tab, setTab] = useState<Tab>("analyze");
  // Bump to force History to re-fetch sessions after a scan completes.
  const [scanNonce, setScanNonce] = useState(0);

  function onAuth(u: User) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(u));
    setUser(u);
    setTab("analyze");
  }

  function onLogout() {
    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
    setScreen("landing");
  }

  // The exhibit outranks the auth split — it is the case for the project, and
  // every visitor should land on it.
  if (showExhibit) {
    return <Exhibit onOpenApp={enterApp} />;
  }

  // ─── Unauthenticated flow: Login or an anonymous Scan trial ───
  if (!user) {
    if (screen === "login") {
      return <Login onAuth={onAuth} onBack={() => setScreen("landing")} />;
    }
    if (screen === "trial") {
      // Anonymous trial — the full app shell, but "Sign out" returns to Landing
      // and the account footer reflects a guest session.
      return (
        <Layout
          user={ANON_USER}
          tab={tab}
          onTab={setTab}
          onLogout={backToExhibit}
          anonymous
          onSignIn={() => setScreen("login")}
          onHome={backToExhibit}
        >
          {tab === "analyze" && <Analyze user={ANON_USER} onNavigate={setTab} />}
          {tab === "history" && <History key={`hist-anon`} user={ANON_USER} />}
        </Layout>
      );
    }
    return (
      <Landing onTryScan={() => setScreen("trial")} onSignIn={() => setScreen("login")} />
    );
  }

  return (
    <Layout user={user} tab={tab} onTab={setTab} onLogout={onLogout} onHome={backToExhibit}>
      {tab === "analyze" && (
        <Analyze
          user={user}
          onNavigate={setTab}
          onScanComplete={() => setScanNonce((n) => n + 1)}
        />
      )}
      {tab === "history" && <History key={`hist-${scanNonce}`} user={user} />}
    </Layout>
  );
}
