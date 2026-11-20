import { Site } from "./site/Site";

/* The site IS the app.
 *
 * The previous shell had a landing page, a login gate, an authenticated
 * scan/history product, and a separate "exhibit" marketing view — four
 * entry points competing to be the front door, with the actual tool behind a
 * sign-in that a review panel would have to be walked through.
 *
 * For a capstone demo and a public write-up that is all cost and no benefit:
 * there is no multi-user deployment, the backend runs on localhost, and the
 * scan endpoint never needed an account. One URL, seven pages, the tool on
 * one of them, nothing to log into.
 *
 * The old views remain in src/views/ (Analyze, History, Login) for the
 * authenticated product path; they are simply not routed here. */
export default function App() {
  return <Site />;
}
