import { C, F, S } from "../design";
import { Card, Caveat, Grid, P, Section, Stat, Table } from "../ui";
import { TESTING } from "../facts";

export function Testing() {
  return (
    <div style={S.page}>
      <div style={{ paddingTop: 44 }}>
        <div style={S.eyebrow}>Testing</div>
        <h1 style={S.h1}>Most of our testing is aimed at ourselves</h1>
        <P>
          Functional tests check that the tool works. The harder problem in a
          project like this is checking that the <em>measurements</em> work —
          that a run which failed cannot be scored as if it succeeded. Nearly
          every serious bug we found this year was of that second kind: not a
          wrong number, but a missing one that every available signal reported
          as present.
        </P>
      </div>

      <Section>
        <Grid min={200}>
          <Stat value={String(TESTING.tests)} label="Automated tests" sub="pytest, unit + integration" />
          <Stat value={String(TESTING.seeds)} label="Held-out seeds" sub={`${TESTING.seedSize} contracts each`} />
          <Stat value={TESTING.quarantineRate} label="Quarantine rate" sub="unsound rows excluded from scoring" />
          <Stat value="2" label="Hosts" sub="cross-machine reproducibility control" />
        </Grid>
      </Section>

      <Section title="Functional testing">
        <Table
          head={["Layer", "What is covered", "Method"]}
          rows={[
            [
              "Unit",
              "Router selection, feature extraction, the evidence gate's quote matching, noisy-OR arithmetic, severity mapping",
              "pytest, deterministic fixtures",
            ],
            [
              "Integration",
              "Full pipeline on known contracts: a vulnerable one must return NO-GO, a clean one GO, a partially-failed council INCONCLUSIVE",
              "pytest with a stubbed model layer",
            ],
            [
              "End-to-end",
              "Real models, real Ollama, the shipped demo samples",
              "build_demo_cache.py, run before every demo",
            ],
            [
              "Contract-level",
              "SARIF output is accepted by GitHub code scanning, which rejects a malformed file",
              "codeql-action/upload-sarif in the audit workflow",
            ],
          ]}
        />
      </Section>

      <Section title="Integrity testing — the part that matters">
        <P>
          These tests exist because each one corresponds to a real defect that
          silently corrupted results before we caught it. They are regression
          tests for specific incidents, not hypotheticals.
        </P>
        <div style={{ display: "grid", gap: 12 }}>
          {[
            {
              rule: "A GO with an errored specialist is never terminal",
              why: "An errored specialist can only fail to raise a flag, never invent one. So NO-GO with errors is still sound, but GO with errors is unearned. Before this rule, 32 of 198 rows were GO verdicts from partially-dead councils — all in the same direction, quietly inflating safe-tier accuracy.",
            },
            {
              rule: "A tool failure is never counted as sound",
              why: "The baseline guard treated 'no result' as terminal because it usually means a missing source file. It also means the tool could not run at all. A 100% dead analyzer was reported as sound=142, quarantined=0, two lines below ok: 0.",
            },
            {
              rule: "An arm that produced zero answers is flagged DEAD, not finished",
              why: "A failing stage that writes one empty record per contract is indistinguishable from a successful one by row count — and row count was the only thing being watched.",
            },
            {
              rule: "A fabricated quote is counted, not silently dropped",
              why: "The evidence gate discarded findings whose quote did not appear in the source and kept no record. Every surviving finding therefore had a valid quote by construction, so the measured fabrication rate was 0% no matter how often a model invented one. The question was unmeasurable, not unmeasured.",
            },
            {
              rule: "Preflight checks models by name, not by count",
              why: "The gate reported 'N models pulled' and passed — including on a day the judge model was absent. The count was correct and the run was worthless.",
            },
          ].map((t) => (
            <Card key={t.rule}>
              <div style={{ ...S.h3, color: C.accent, fontFamily: F.mono, fontSize: 13.5 }}>
                {t.rule}
              </div>
              <P style={{ margin: "8px 0 0", fontSize: 14 }}>{t.why}</P>
            </Card>
          ))}
        </div>
      </Section>

      <Section title="Statistical validation">
        <Table
          head={["Technique", "Where it is used", "Why that one"]}
          rows={[
            [
              "Wilson intervals",
              "Every rate on this site",
              "Wald intervals are wrong near 0 and 1, which is exactly where false-alarm rates live",
            ],
            [
              "Paired McNemar",
              "Any two configurations compared on the same contracts",
              "An unpaired test throws away the pairing and overstates uncertainty",
            ],
            [
              "Out-of-sample seeds",
              "Any configuration chosen by inspecting the data",
              "A hypothesis selected on seed 0 cannot be scored on seed 0 — that measures how well we fitted seed 0",
            ],
            [
              "Negative controls",
              "The preflight gate and the dead-arm detector",
              "A checker that has never been shown failing has not been tested",
            ],
            [
              "Cross-machine control",
              "Two hosts, identical inputs",
              "0.735 verdict agreement, with batch parallelism excluded as a cause (p = 0.75)",
            ],
          ]}
        />
      </Section>

      <Section title="A test we ran that we did not like">
        <Card>
          <P style={{ margin: 0 }}>
            Excluding the noisiest specialist improved results by 8.3 points
            in-sample. We had chosen that specialist by inspecting the same data,
            so we pre-registered a validator with a minimum-sample gate and ran
            two held-out seeds. The effect's sign flipped depending on the
            threshold: <code style={{ fontFamily: F.mono, color: C.ink }}>+1.4, −2.7, +2.6, +0.6</code>.
            The underlying mechanism replicated — that specialist really does put
            ~42% of its findings on safe contracts — but the benefit did not.
          </P>
          <P style={{ margin: "12px 0 0" }}>
            We did not ship it. A paper arguing that evaluation setup determines
            the answer cannot ship a configuration tuned on its own test set.
          </P>
        </Card>
        <Caveat title="The validator caught us mid-run too">
          At 206 of 334 rows it printed REFUTED. At the complete 334 one of
          those signs flipped. Thresholds being met is not the same as a run
          being finished, and we had to add a completion condition to the gate
          we had built to prevent exactly that class of error.
        </Caveat>
      </Section>
    </div>
  );
}
