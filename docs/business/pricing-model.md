# MiroConsumer Pricing Model

## Pricing Principles

MiroConsumer is priced around a simulation run because each run maps directly to LLM cost, storage, report generation, and reviewer time. Pricing must stay honest about the product boundary: the output is directional consumer research, not a real-market forecast.

The commercial model has two stages:

- short-term unified pricing: keep one base price per simulation run while enterprise pilots validate usage patterns.
- long-term differentiated pricing: price by test type once customers can see distinct mechanics for concept, copy, packaging, price, A/B, and propagation tests.

## Metering Unit

The base metering unit is one simulation run. A run includes:

- one accepted BusinessBrief
- one configured Persona Pack
- one society runtime execution
- one generated report
- one retained Graph Snapshot and audit trail

LLM cost is the variable cost driver. The platform should track prompt tokens, completion tokens, fallback rate, report section generation, and retry count per run.

## Consumer Count Tiers

Consumer count controls statistical power, runtime cost, and report richness.

| Tier | Consumer count | Intended use | Resource quota guidance |
| --- | ---: | --- | --- |
| Starter | 16 consumers | quick directional scan | low LLM budget, one report, limited export |
| Team | 32 consumers | standard concept/copy validation | standard LLM budget, report plus interview unlock |
| Growth | 64 consumers | broader segment coverage | higher LLM budget, branch diff, export allowance |
| Enterprise | 128 consumers | high-value launch decisions | dedicated quota, priority workers, admin controls |

The resource quota should cover API rate limits, export limits, concurrent runs, retained snapshots, and monthly LLM budget.

## Editions

Professional includes standard Persona Packs, dashboard access, API access, standard report generation, and shared SaaS infrastructure.

Enterprise includes custom Persona Pack development, private deployment, SSO/SAML readiness, dedicated worker capacity, image signing/SBOM evidence, tenant audit export, and negotiated data retention.

## Test Type Pricing

In the short term, concept, copy, packaging, price, A/B, and propagation tests can share short-term unified pricing to reduce sales friction.

In the long term, long-term differentiated pricing should reflect analysis depth:

- Concept and copy tests remain baseline directional tiers.
- Packaging adds visual attention and shelf-context interpretation.
- Price tests add Gabor-Granger style acceptance and elasticity signals.
- A/B tests add paired comparison and preference strength.
- Propagation tests add channel spread, misread risk, and intervention replay.

## Add-On Services

Add-ons should be quoted separately:

- custom Persona Pack design and validation
- external validity validation against surveys, sales, or panel research
- private deployment setup and security review
- bespoke report template and executive workshop

## Review Owners

The pricing model requires review owners across product, technical, and finance teams before being used as a quote book.

- Product owner: validates packaging, value metrics, and edition boundaries.
- Technical owner: maps each tier to resource quota, LLM budget, retention, and rate limits.
- Finance owner: confirms gross margin after LLM cost, support cost, and deployment overhead.
