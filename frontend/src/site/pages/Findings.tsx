import { C, F, S } from "../design";
import { BarPair, Badge, Card, Caveat, P, Section, Table } from "../ui";
import { ENSEMBLE_SIZE, FINDINGS, SCORING_RULES, type Finding } from "../facts";

const STATUS_STYLE: Record<Finding["status"], { fg: string; bg: string }> = {
  SOUND: { fg: C.go, bg: C.goGhost },
  "SOUND (scoped)": { fg: C.accent, bg: C.accentGhost },
  REFUTED: { fg: C.nogo, bg: C.nogoGhost },
  RETRACTED: { fg: C.nogo, bg: C.nogoGhost },
  OPEN: { fg: C.inconc, bg: C.inconcGhost },
};

export function Findings() {
  const kRows = ENSEMBLE_SIZE.seed0.map((r) => {
    const held = ENSEMBLE_SIZE.seed1.find((x) => x.k === r.k);
    return {
      label: `k = ${r.k}`,
      a: r.fpr,
      b: held ? held.fpr : null,
      nA: r.n,
      nB: held?.n,
    };
  });

  return (
    <div style={S.page}>
      <div style={{ paddingTop: 44 }}>
        <div style={S.eyebrow}>Findings</div>
        <h1 style={S.h1}>What we actually learned</h1>
        <P>
          The tool is half the project. The other half is a result about how
          tools like it get evaluated — and it is the half we would defend
          harder. Every claim below carries its status, including the ones that
          did not survive.
        </P>
      </div>

      <Section title="The headline, stated carefully">
        <P>
          The three rows below come from the <em>same stored verdicts</em> on the
          same 2,142 contracts. Only the rule that reads the findings changes.
        </P>
        <Table
          head={["Scoring rule", "Recall", "False-alarm rate"]}
          emphasiseRow={1}
          rows={SCORING_RULES.map((r) => [
            <span>
              {r.rule}
              {r.shipped && (
                <span style={{ marginLeft: 8 }}>
                  <Badge>shipped</Badge>
                </span>
              )}
            </span>,
            <span>
              {r.recall}{" "}
              <span style={{ color: C.inkDim, fontSize: 11.5 }}>{r.recallCI}</span>
            </span>,
            <span>
              {r.fpr} <span style={{ color: C.inkDim, fontSize: 11.5 }}>{r.fprCI}</span>
            </span>,
          ])}
        />
        <Caveat title="Reporting any one of these as 'the' false-alarm rate would be defensible">
          That is the problem. All three rules appear in published work, none of
          them is wrong, and the choice between them is almost never stated.
        </Caveat>
      </Section>

      <Section title="The largest effect is one nobody selects">
        <P>
          On identical safe contracts, the false-alarm rate rises monotonically
          with how many specialists the router happened to fire. The council is
          a logical OR over k detectors, so contract-level false positives grow
          as 1 − (1 − p)<sup>k</sup>. Nobody picks k — it falls out of routing.
        </P>
        <Card>
          <BarPair
            rows={kRows}
            labelA="seed 0 (1,027 of 1,046 safe contracts; k = 7–8 omitted, n ≤ 15)"
            labelB="held-out seed 1 (n = 162)"
          />
        </Card>
        <P style={{ marginTop: 14 }}>
          It replicated on a seed the hypothesis never saw, tracking within a
          few points at every k with enough data. That matters because it is the
          claim that held on the same day another one of ours failed — and the
          difference is that this one is a structural property of the
          aggregation, while the other was selected by looking at the data.
        </P>
      </Section>

      <Section title="Every claim, with its status">
        <div style={{ display: "grid", gap: 12 }}>
          {FINDINGS.map((f) => {
            const st = STATUS_STYLE[f.status];
            return (
              <Card key={f.id}>
                <div
                  style={{
                    display: "flex",
                    gap: 10,
                    alignItems: "center",
                    flexWrap: "wrap",
                    marginBottom: 8,
                  }}
                >
                  <span style={{ fontFamily: F.mono, fontSize: 12, color: C.inkDim }}>
                    {f.id}
                  </span>
                  <strong style={{ fontSize: 15.5, color: C.ink }}>{f.title}</strong>
                  <span style={{ marginLeft: "auto" }}>
                    <Badge fg={st.fg} bg={st.bg}>
                      {f.status}
                    </Badge>
                  </span>
                </div>
                <P style={{ margin: "0 0 10px", fontSize: 14.5 }}>{f.body}</P>
                <div
                  style={{
                    fontFamily: F.mono,
                    fontSize: 12,
                    color: C.inkDim,
                    borderTop: `1px solid ${C.line}`,
                    paddingTop: 9,
                  }}
                >
                  {f.evidence}
                </div>
              </Card>
            );
          })}
        </div>
      </Section>

      <Section title="Things we are not claiming">
        <Caveat title="Not that ThirdEye beats commercial auditors">
          It does not. At a 45.9% false-alarm rate it is a cheap local filter
          that runs before a human looks, not a replacement for one.
        </Caveat>
        <Caveat title="Not that the council beats a single model everywhere">
          On the access-control slice, scored on a common contract set, a
          single-model baseline beat the council on F1 (0.420 against 0.363) and
          on precision (0.268 against 0.221). The council won recall, 1.000
          against 0.971. Which of those you care about is a deployment choice,
          and we report both.
        </Caveat>
        <Caveat title="Not that these numbers transfer to another corpus">
          The whole point of the project is that they would not. A different
          safe class, a different matching rule, or a different context window
          gives a different headline from the identical tool.
        </Caveat>
      </Section>
    </div>
  );
}
