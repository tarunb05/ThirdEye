import { C, F, S } from "../design";
import { Card, Caveat, Grid, P, Section } from "../ui";

/* Four members, four subsystems, an equal quarter each.
 *
 * The split is the documented division of labour from the paper's authorship
 * note, not a count of git commits. Commit counts measure who pushed to this
 * repository, which is a poor proxy for who did the work: corpus
 * construction, prompt design and evaluation analysis mostly do not arrive as
 * commits under their author's name.
 *
 * EQUAL MEANS EQUAL IN THE WORDING TOO. An earlier version of this page gave
 * every member four bullets and then undercut it in the one-line summaries --
 * one read "owns the findings register" while the others owned a subsystem
 * apiece, which quietly made one member the lead and the rest contributors.
 * The evaluation is now split into four comparable parcels, each named, and
 * no summary line claims authority over another's. Each row carries the same
 * 25% marker because that is the actual arrangement.
 */

type Member = {
  name: string;
  srn: string;
  owns: string;
  detail: string[];
  evaluation: string;
};

const TEAM: Member[] = [
  {
    name: "Umar Ahmed",
    srn: "PES2UG23CS662",
    owns: "Benchmark & experimental design",
    detail: [
      "Full-corpus evaluation harness and the 2,142-row scoring pipeline",
      "Integrity layer — the asymmetric terminal rule and the dead-arm detector",
      "Cross-machine parity study (0.735 agreement, parallelism excluded)",
      "Checkpoint format and the offline re-derivation path",
    ],
    evaluation: "Evaluation quarter: the context-window and model-size ablations.",
  },
  {
    name: "V Lakshitha",
    srn: "PES2UG23CS665",
    owns: "Grounding & delivery",
    detail: [
      "Retrieval grounding and the context-aware suppression layer",
      "Adversarial arbitration: the judge prompt and the red-team stage",
      "FastAPI service, streaming scan API, SARIF export for CI",
      "This site and the local-only demo path",
    ],
    evaluation: "Evaluation quarter: the arbitration sweep and the grounding ablation.",
  },
  {
    name: "Anvita Agarwal",
    srn: "PES2UG23CS085",
    owns: "Corpus & ground truth",
    detail: [
      "2,250-contract corpus: sourcing, deduplication, parse verification",
      "The six-tier provenance stratification that makes provenance measurable",
      "Dataset loaders and the contract verifier",
      "DASP-10 class mapping and the class-coverage audit",
    ],
    evaluation: "Evaluation quarter: the stratified tier analysis and class coverage.",
  },
  {
    name: "Tarun B",
    srn: "PES2UG23CS644",
    owns: "Council & verdict rule",
    detail: [
      "Eight-specialist council and the per-role model assignment",
      "Static router — the single biggest lever on the false-alarm rate",
      "Evidence gate: the verbatim-quote requirement and the confidence bar",
      "Noisy-OR risk pooling and the fail-closed INCONCLUSIVE verdict",
    ],
    evaluation: "Evaluation quarter: the threshold sweep and the held-out seed runs.",
  },
];
export function Team() {
  return (
    <div style={S.page}>
      <div style={{ paddingTop: 44 }}>
        <div style={S.eyebrow}>Team</div>
        <h1 style={S.h1}>Four subsystems, four owners</h1>
        <P>
          ThirdEye is built from four parts that each had to work for any number
          on this site to mean anything: a corpus, an analysis pipeline, an
          evaluation harness, and a delivery path. Each member owns one
          end-to-end and carries <strong style={{ color: C.ink }}>one quarter
          of the evaluation</strong> — four named parcels, not a lead and three
          contributors.
        </P>
        <P>
          Department of Computer Science and Engineering, PES University,
          Bengaluru · Capstone Project Phase 3 · UE23CS441A
        </P>
      </div>

      <Section>
        <div style={{ display: "grid", gap: 14 }}>
          {TEAM.map((m) => (
            <Card key={m.srn}>
              <div
                style={{
                  display: "flex",
                  gap: 12,
                  alignItems: "baseline",
                  flexWrap: "wrap",
                  marginBottom: 4,
                }}
              >
                <strong style={{ fontSize: 17, color: C.ink }}>{m.name}</strong>
                <span style={{ fontFamily: F.mono, fontSize: 12, color: C.inkDim }}>
                  {m.srn}
                </span>
                <span
                  style={{
                    marginLeft: "auto",
                    fontFamily: F.mono,
                    fontSize: 11.5,
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    color: C.accent,
                  }}
                >
                  {m.owns}
                </span>
                <span
                  style={{
                    fontFamily: F.mono,
                    fontSize: 11.5,
                    color: C.inkDim,
                    border: `1px solid ${C.line}`,
                    borderRadius: 5,
                    padding: "2px 7px",
                  }}
                >
                  25%
                </span>
              </div>

              <ul
                style={{
                  margin: "12px 0 0",
                  padding: "0 0 0 18px",
                  display: "grid",
                  gap: 6,
                }}
              >
                {m.detail.map((d) => (
                  <li
                    key={d}
                    style={{
                      fontFamily: F.sans,
                      fontSize: 14,
                      lineHeight: 1.55,
                      color: C.inkMid,
                    }}
                  >
                    {d}
                  </li>
                ))}
              </ul>

              <div
                style={{
                  marginTop: 12,
                  paddingTop: 10,
                  borderTop: `1px solid ${C.line}`,
                  fontFamily: F.sans,
                  fontSize: 13.5,
                  color: C.inkDim,
                }}
              >
                {m.evaluation}
              </div>
            </Card>
          ))}
        </div>
      </Section>

      <Section title="How the split was decided">
        <P>
          Four subsystems, assigned so that no member's work depends on another
          member finishing first. The corpus could be built while the council
          was being written; the evaluation harness could be tested against a
          stub while the delivery path was in progress.
        </P>
        <Caveat title="Why this page does not use commit counts">
          Git attributes commits to whoever pushed them, and most of this
          repository was pushed from one machine. Corpus curation, prompt
          design, failure analysis and the statistical work largely do not
          arrive as commits under their author's name, so a contributor graph
          would misrepresent the split rather than evidence it.
        </Caveat>
        <P>
          Each row above carries the same 25% because the work was scoped that
          way up front, not apportioned afterwards to look even. Author order on
          the paper remains a separate question from workload and is not settled
          by this page.
        </P>
      </Section>

      <Section title="Shared responsibilities">
        <Grid min={260}>
          <Card>
            <div style={S.h3}>Review discipline</div>
            <P style={{ fontSize: 14, margin: 0 }}>
              Every claim in the findings register carries a status, and anyone
              may demote one. Several of our own results are marked refuted or
              retracted by this rule.
            </P>
          </Card>
          <Card>
            <div style={S.h3}>Reproducibility</div>
            <P style={{ fontSize: 14, margin: 0 }}>
              Pinned model digests, recorded seeds, and a checkpoint per
              contract so any figure can be re-derived without a re-run.
            </P>
          </Card>
          <Card>
            <div style={S.h3}>Honest reporting</div>
            <P style={{ fontSize: 14, margin: 0 }}>
              Negative results stay on the site. The configuration we tuned and
              then failed to validate is documented as refuted rather than
              quietly dropped.
            </P>
          </Card>
        </Grid>
      </Section>
    </div>
  );
}
