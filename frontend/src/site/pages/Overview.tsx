import { C, F, S } from "../design";
import { Badge, Card, Caveat, Grid, P, Section, Stat, Table } from "../ui";
import { CouncilEye } from "../CouncilEye";
import { SplitWords } from "../motion";
import { CORPUS, SCORING_RULES, TESTING } from "../facts";

export function Overview({ go }: { go: (route: string) => void }) {
  return (
    <div style={S.page}>
      {/* ── hero ── */}
      <div style={{ paddingTop: 64, paddingBottom: 8 }}>
        <div style={S.eyebrow}>ThirdEye · PES University capstone</div>
        <h1 style={{ ...S.h1, fontSize: "clamp(32px, 6.4vw, 54px)", maxWidth: "19ch" }}>
          <SplitWords text="A smart-contract auditor that runs entirely on your machine" />
        </h1>
        <P style={{ fontSize: 17, maxWidth: "62ch" }}>
          A router picks which of eight specialist models should read a Solidity
          contract, each must quote the line it is accusing, and the surviving
          findings are pooled into one verdict: <strong style={{ color: C.go }}>GO</strong>,{" "}
          <strong style={{ color: C.nogo }}>NO-GO</strong>, or{" "}
          <strong style={{ color: C.inconc }}>INCONCLUSIVE</strong>. No API key,
          no network call, no contract source leaving the laptop.
        </P>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 22 }}>
          <button
            onClick={() => go("tool")}
            style={{
              background: C.accent,
              color: C.bg,
              border: "none",
              borderRadius: 7,
              padding: "11px 22px",
              fontFamily: F.sans,
              fontSize: 14.5,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Scan a contract
          </button>
          <button
            onClick={() => go("findings")}
            style={{
              background: "transparent",
              color: C.ink,
              border: `1px solid ${C.lineHi}`,
              borderRadius: 7,
              padding: "11px 22px",
              fontFamily: F.sans,
              fontSize: 14.5,
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Read the findings
          </button>
        </div>

        {/* The hero visual IS the headline finding, played from its measured
            rows -- see CouncilEye. A reviewer who only watches the loop has
            still read FINDING 0. */}
        <div
          style={{
            marginTop: 40,
            padding: "26px 28px",
            background: C.panel,
            border: `1px solid ${C.line}`,
            borderRadius: 14,
          }}
        >
          <CouncilEye />
        </div>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 20 }}>
          <Badge>local-only</Badge>
          <Badge>8 specialist roles</Badge>
          <Badge>3 model families</Badge>
          <Badge>{CORPUS.total.toLocaleString()}-contract benchmark</Badge>
        </div>
      </div>

      {/* ── the honest headline ── */}
      <Section title="Where it stands">
        <Grid min={210} stagger>
          <Stat value="89.1%" label="Recall" sub="vulnerable contracts caught, shipped setting" tone={C.go} />
          <Stat value="45.9%" label="False-alarm rate" sub="safe contracts wrongly flagged" tone={C.nogo} />
          <Stat value={CORPUS.scored.toLocaleString()} label="Contracts scored" sub="balanced safe / vulnerable" />
          <Stat value="$0" label="Cost per scan" sub="local models, no quota" />
        </Grid>
        <Caveat title="We lead with the bad number on purpose">
          A 45.9% false-alarm rate means roughly one in two clean contracts gets
          flagged. ThirdEye is a cheap local filter that runs before a human
          looks — not a replacement for an audit. Every finding ships with the
          line of code it rests on precisely so a wrong one takes seconds to
          dismiss.
        </Caveat>
      </Section>

      {/* ── the research result ── */}
      <Section eyebrow="The other half of the project" title="That number is not a property of the tool">
        <P>
          The three rows below are the <em>same stored verdicts</em> on the same
          contracts. Only the rule that reads them changes — and all three rules
          appear in published work.
        </P>
        <Table
          head={["Scoring rule", "Recall", "False-alarm rate"]}
          emphasiseRow={1}
          rows={SCORING_RULES.map((r) => [
            <span>
              {r.rule}
              {r.shipped && (
                <span style={{ marginLeft: 8 }}>
                  <Badge>ours</Badge>
                </span>
              )}
            </span>,
            r.recall,
            r.fpr,
          ])}
        />
        <P style={{ marginTop: 14 }}>
          Holding the tool, the seed, the model digests and the machine fixed,
          five unreported evaluation choices each move the headline by more than
          any tool-versus-tool difference we found in the literature. That is
          the finding we would defend hardest.
        </P>
        <button
          onClick={() => go("findings")}
          style={{
            background: "transparent",
            color: C.accent,
            border: "none",
            padding: 0,
            fontFamily: F.sans,
            fontSize: 14.5,
            cursor: "pointer",
            textDecoration: "underline",
            textUnderlineOffset: 3,
          }}
        >
          All findings, with status →
        </button>
      </Section>

      {/* ── map of the site ── */}
      <Section title="What is here">
        <Grid min={250}>
          {[
            ["how", "How it works", "Six stages, the eight specialists, and the one rule that does the real work."],
            ["datasets", "Datasets", "2,250 contracts with a real safe class, stratified by how each label was obtained."],
            ["testing", "Testing", `${TESTING.tests} tests, most of them aimed at catching our own measurement errors.`],
            ["findings", "Findings", "Every claim with a status — including the ones we refuted ourselves."],
            ["tool", "The tool", "Audit six sample contracts locally — three safe, three vulnerable — or paste your own."],
            ["team", "Team", "Four subsystems, four owners."],
          ].map(([route, title, blurb]) => (
            <Card
              key={route}
              style={{ cursor: "pointer" }}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              {...({ onClick: () => go(route) } as any)}
            >
              <div style={S.h3}>{title}</div>
              <P style={{ fontSize: 13.5, margin: 0 }}>{blurb}</P>
            </Card>
          ))}
        </Grid>
      </Section>
    </div>
  );
}
