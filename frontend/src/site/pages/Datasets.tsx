import { C, F, S } from "../design";
import { Card, Caveat, Grid, P, Section, Stat, Table } from "../ui";
import { CORPUS, TIERS } from "../facts";

export function Datasets() {
  const safe = TIERS.filter((t) => t.klass === "safe");
  const vuln = TIERS.filter((t) => t.klass === "vulnerable");

  return (
    <div style={S.page}>
      <div style={{ paddingTop: 44 }}>
        <div style={S.eyebrow}>Datasets</div>
        <h1 style={S.h1}>A benchmark with a real negative class</h1>
        <P>
          Most smart-contract benchmarks are lists of known-vulnerable
          contracts. You can score recall on those, but not precision — with no
          safe contracts, a tool that flags everything is indistinguishable from
          a good one. That gap is why false-alarm rates are rarely reported in
          this field, and it is the first thing we had to fix.
        </P>
      </div>

      <Section>
        <Grid min={200}>
          <Stat value={CORPUS.total.toLocaleString()} label="Contracts" sub="Solidity, deduplicated and parse-verified" />
          <Stat value="1,125 : 1,125" label="Safe : vulnerable" sub="balanced by construction, not by sampling" />
          <Stat value="6" label="Provenance tiers" sub="3 safe, 3 vulnerable" />
          <Stat value={CORPUS.scored.toLocaleString()} label="Scored contracts" sub="rows surviving the soundness rule" />
        </Grid>
      </Section>

      <Section title="The safe class is stratified by how the label was obtained">
        <P>
          This is the part that does not exist elsewhere. "Safe" is not one
          thing: a contract from an audited library has a far stronger claim to
          being correct than one that merely has no bug report filed against it.
          If you mix them, your false-alarm rate depends on the mixture — and
          nobody reports the mixture.
        </P>
        <Table
          head={["Safe tier", "n", "How the label was obtained", "False alarms"]}
          rows={safe.map((t) => [
            t.label,
            t.n,
            <span style={{ fontFamily: F.sans, fontWeight: 400, color: C.inkMid }}>{t.how}</span>,
            <strong style={{ color: C.ink }}>{t.fprShipped}</strong>,
          ])}
        />
        <P style={{ marginTop: 14 }}>
          Same tool, same settings, same corpus: <strong style={{ color: C.ink }}>27.8%</strong> on
          audited libraries against <strong style={{ color: C.ink }}>54.7%</strong> on
          audit-reviewed code. Choosing which of these to call "the safe class"
          moves the headline number by more than most published tool-versus-tool
          comparisons.
        </P>
        <Caveat title="And this effect is partly confounded">
          Audited libraries also draw fewer specialists — a median of 2 against
          3 elsewhere — and ensemble size drives false alarms on its own. At
          matched k = 2 the three tiers become statistically indistinguishable.
          The provenance effect is real but smaller than the raw comparison
          suggests, so we report it stratified. Finding it meant our own
          headline number got weaker, which is the point of looking.
        </Caveat>
      </Section>

      <Section title="The vulnerable class, by how the bug got there">
        <Table
          head={["Vulnerable tier", "n", "Provenance"]}
          rows={vuln.map((t) => [
            t.label,
            t.n,
            <span style={{ fontFamily: F.sans, fontWeight: 400, color: C.inkMid }}>{t.how}</span>,
          ])}
        />
        <P style={{ marginTop: 14 }}>
          These are not equally hard. Injected bugs are exact by construction
          and easy to match; audit-report bugs are real, subtle, and often
          require understanding what the protocol was <em>supposed</em> to do.
          A recall number averaged across all three hides that spread.
        </P>
      </Section>

      <Section title="What counts as a detection">
        <P>
          Even with fixed verdicts, the matching rule changes the answer. If a
          flagged contract counts as detected when any specialist fires, recall
          is 82.2%. If the finding's class must match the labelled bug class,
          recall is 25.5% — on the same 349 labelled contracts. 25.5% is a
          lower bound: only 5 of our 8 roles have an unambiguous DASP-10 slot,
          so three specialists can never score a class match.
        </P>
        <Card>
          <Table
            head={["Matching rule", "Recall"]}
            rows={[
              ["Any specialist fires on the contract", "82.2%"],
              ["Finding class must match the labelled class", "25.5%"],
              ["Any specialist fires — restricted to the 187 contracts carrying only covered classes", "77.0%"],
              ["Class must match — same 187 contracts", "45.5%"],
            ]}
          />
        </Card>
        <P style={{ marginTop: 14 }}>
          Part of that gap is our own coverage — we do not have a specialist for
          every labelled class. Controlling for it, 31.6 points remain
          attributable to the scoring protocol alone.
        </P>
      </Section>

      <Section title="Honest limits of this corpus">
        <Caveat title="Safe labels are inherited, not proven">
          No contract here is proven correct. "Audited" and "no bug reported"
          are the strongest practical signals available, and both have been
          wrong historically. A false alarm against this corpus may occasionally
          be a real bug nobody has found yet.
        </Caveat>
        <Caveat title="Multi-file projects are flattened">
          Project-level entries are concatenated rather than import-resolved, so
          cross-contract reasoning is weaker than it would be with a real
          compilation unit.
        </Caveat>
        <Caveat title="Class labels are incomplete">
          Of the 551 vulnerable contracts in the class-coverage run, 349 carry a
          mapped DASP-10 class and 202 carry none. Any class-level claim is made
          only over the 349, and 158 of those (45.3%) carry only classes the
          council has no specialist for at all.
        </Caveat>
      </Section>
    </div>
  );
}
