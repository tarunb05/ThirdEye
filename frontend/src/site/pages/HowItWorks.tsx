import { C, F, S } from "../design";
import { Badge, Card, Caveat, Grid, P, Section, Table } from "../ui";
import { Pipeline } from "../Pipeline";
import { STAGES } from "../stages";
import { SPECIALISTS } from "../facts";


export function HowItWorks() {
  return (
    <div style={S.page}>
      <div style={{ paddingTop: 44 }}>
        <div style={S.eyebrow}>How it works</div>
        <h1 style={S.h1}>Six stages, and one rule that matters</h1>
        <P>
          ThirdEye is not a model with a security prompt. It is a pipeline whose
          design is mostly about <em>not</em> raising findings: a router that
          declines to ask irrelevant questions, a gate that throws away any claim
          without a verbatim quote, and a verdict rule that needs more than one
          weak signal before it blocks a deploy.
        </P>
      </div>

      <Section title="The pipeline">
        <Pipeline stages={STAGES} />
      </Section>

      <Section title="The eight specialists">
        <P>
          Each is asked exactly one question. Five map onto an unambiguous
          DASP-10 class; <code style={{ fontFamily: F.mono, fontSize: 12.5 }}>business_logic</code>,{" "}
          <code style={{ fontFamily: F.mono, fontSize: 12.5 }}>oracle_price_manipulation</code> and{" "}
          <code style={{ fontFamily: F.mono, fontSize: 12.5 }}>proxy_upgradeability</code> are
          deliberately left unmapped, which is why a class-matched recall figure
          is a lower bound rather than a like-for-like score. The model
          assignment is by role, not by convenience — the code-reading roles go
          to a code-tuned model, the judgement roles to a general reasoner.
        </P>
        <Table
          head={["Specialist", "Model family", "Local model"]}
          rows={SPECIALISTS.map((s) => [
            s.label,
            s.model.startsWith("qwen")
              ? "qwen (code)"
              : s.model.startsWith("llama")
                ? "llama (general)"
                : "gemma (general)",
            <code style={{ fontFamily: F.mono, fontSize: 12.5 }}>{s.model}</code>,
          ])}
        />
        <Caveat title="On model diversity">
          Three families, not three model names. Running the same model under
          three aliases would give the appearance of a council and none of the
          benefit, because correlated models make correlated mistakes and the
          aggregation assumes they do not.
        </Caveat>
      </Section>

      <Section title="Why it runs on your machine">
        <Grid min={260}>
          <Card>
            <div style={S.h3}>The source never leaves</div>
            <P style={{ fontSize: 14, margin: 0 }}>
              You are handing an auditor unreleased, often proprietary code. A
              security tool that ships that to a third-party inference API by
              default has the wrong default, independent of cost.
            </P>
          </Card>
          <Card>
            <div style={S.h3}>No key, no quota, no bill</div>
            <P style={{ fontSize: 14, margin: 0 }}>
              Ollama, three small models, zero configuration beyond pulling
              them. A scan costs electricity.
            </P>
          </Card>
          <Card>
            <div style={S.h3}>Reproducible by anyone</div>
            <P style={{ fontSize: 14, margin: 0 }}>
              Hosted models change under you without a version bump. Pinned
              local models are the only way the numbers on this site can be
              re-derived next year.
            </P>
          </Card>
        </Grid>
        <div style={{ marginTop: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Badge>local-only by default</Badge>
          <Badge>cloud providers gated behind an explicit flag</Badge>
          <Badge>arbitration off by default</Badge>
        </div>
      </Section>

      <Section title="What the verdict does not mean">
        <Caveat title="GO is not a safety certificate">
          A GO means no specialist that ran — and the router fires a subset, not all
          eight — could quote a line supporting a finding above the confidence
          bar. On the benchmark the tool misses
          roughly 11% of genuinely vulnerable contracts at the shipped setting.
          It is a filter that catches most things cheaply and locally — not a
          replacement for an audit.
        </Caveat>
        <Caveat title="NO-GO is not proof of a bug">
          At the shipped setting it raises a false alarm on 45.9% of safe
          contracts. Every finding is shown with the quote it rests on
          specifically so you can dismiss it in seconds when it is wrong.
        </Caveat>
      </Section>
    </div>
  );
}
