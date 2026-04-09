# SCALING.md

This document explains how Upstream would scale beyond the hackathon demo.
Unless a metric is explicitly described as measured, the numbers below are
planning estimates based on the architecture decisions for this project.
The goal is to show a credible path from a single-machine demo to a
production-style deployment without pretending we have already run full
benchmark campaigns.

Pricing-sensitive references in this document were checked against official
vendor pages on April 8, 2026. Those values can change and should be
revalidated before any real production budget is approved.

## 1. Current Implementation Capacity

### Single-instance throughput estimate

The current design target is approximately **10 concurrent incidents per agent
instance**. That number is the capacity assumption used for queue depth,
memory budgeting, and provider-rate planning. It does not mean the agent
instantly completes ten incidents at once; it means one replica should be able
to hold roughly that many active graph executions without severe degradation
when build-time retrieval indexing is already done and incident payloads stay in
the expected size range.

### End-to-end latency envelope

The main model-dependent steps are extraction, causal analysis, and in some
configurations severity estimation. A practical planning envelope for the full
graph is:

- **Fast path:** 10-15 seconds
- **Typical path:** 15-25 seconds
- **Slow path:** 25-40 seconds

The user-provided planning number of **3-8 seconds** is best read as the main
reasoning-call latency window, not the total lifecycle from intake to ticket
creation. Retrieval, validation, ticket creation, and notification delivery add
their own overhead around the core model calls.

### Incidents per hour per replica

At the current target profile, one agent replica should comfortably sustain
approximately **40-60 incidents/hour** on a slower provider day and
**60-120 incidents/hour** under normal conditions. These figures assume no
queue-backed intake yet; bursty traffic will always look worse than steady
traffic until the UI and the graph are decoupled by a durable queue.

### Memory and storage footprint

The current system footprint can be reasoned about in layers:

| Component | Planning estimate | Notes |
| --- | --- | --- |
| Agent service | 1-2 GiB RAM | FastAPI app, LangGraph runtime, provider clients, prompt assembly buffers |
| UI service | 256-512 MiB RAM | Mostly server-rendered request handling |
| Jira mock | 256-512 MiB RAM | File-backed mock workload is intentionally small |
| Notification mock | 256-512 MiB RAM | Similar profile to Jira mock |
| Qdrant | 1-2 GiB RAM | Curated eShop snapshot is much smaller than a full enterprise code index |
| Langfuse stack | 2-4 GiB+ RAM | Depends on retention, ClickHouse sizing, and trace volume |

A realistic demo machine should budget **8-12 GiB RAM** for the whole Docker
Compose stack if every service is running locally. For persistent storage,
**20-50 GiB** is a reasonable starting envelope for the demo and early internal
pilots. The fastest-growing storage consumers will be Langfuse traces, uploaded
logs, screenshots, and Qdrant snapshots.

### LLM cost per incident

Upstream's cost profile is driven primarily by extraction and causal-analysis
prompts. Using official Anthropic pricing checked on April 8, 2026, Claude
Sonnet is priced at **$3 / MTok input** and **$15 / MTok output** for prompts
at or below 200K input tokens.

For Upstream, a reasonable planning estimate per incident is:

- **Input tokens:** 12K-25K
- **Output tokens:** 1.5K-4K

That produces a rough per-incident cost envelope of:

- input: **$0.036-$0.075**
- output: **$0.0225-$0.060**
- total: **$0.0585-$0.135**

Rounded for planning, that is **about $0.06-$0.14 per incident** on Claude
Sonnet-class pricing. Guardrail rejections cost much less because the expensive
reasoning path is skipped. Ollama may reduce direct API spend to near-zero, but
it moves cost into hardware, operations, and lower-quality triage outcomes.

## 2. Identified Bottlenecks

### LLM API latency

The biggest bottleneck is still model time. Even excellent orchestration does
not matter if the slowest step is waiting on external inference. The current
working assumption is **3-8 seconds** for the most important model call under
normal conditions, with longer tails during provider load or when prompts grow
too large.

This matters because model latency:

- directly caps synchronous request throughput
- shapes user-perceived responsiveness
- compounds when multiple reasoning calls are chained
- becomes painful during incident spikes and retry storms

### Vector search at high QPS

Qdrant is a strong fit for the current workload, but a single-node vector store
has natural limits. High retrieval QPS, larger collections, or more aggressive
chunk sizes all increase memory and disk pressure.

Qdrant's official cloud documentation makes clear that free clusters are meant
for prototyping. The free tier is a single node with **1 GB RAM, 0.5 vCPU, and
4 GB disk**, which they note is enough for roughly **1 million vectors at 768
dimensions**. Upstream's curated eShop snapshot should stay comfortably below
that ceiling, but a broader repository set or multi-tenant deployment would
outgrow the single-node profile quickly.

### SQLite checkpointer

SQLite is the right answer for a hackathon build because it is simple, portable,
and excellent for a single writer on a single host. It is also the wrong answer
once multiple replicas need shared durable graph state. The core issue is not
raw speed; it is the **single-writer model**. That becomes painful when
multiple replicas, replays, and background work all want to persist checkpoints
through the same file.

### Single-instance mocks

The Jira mock and notification mock are intentionally lightweight. That is good
for demo clarity, but it means they are not production-grade components. In
their current planned form they are single-instance, file-backed, and not
designed for high write concurrency. These services are good enough to prove
the handoff story; in a real deployment they should be replaced rather than
scaled deeply.

### Upload and parsing pressure

Logs are often larger than the surrounding request metadata. If users upload
large files or repeated noisy stack traces, request parsing and prompt assembly
can become CPU- and memory-heavy before the LLM is even called. The fix is not
just "use a faster model." The fix is streaming uploads, size limits, log
summarization, and structured truncation before expensive reasoning begins.

## 3. Scaling Strategy by Component

### Agent service

The agent service should scale horizontally behind a load balancer. FastAPI is
not the real constraint here; the constraint is graph runtime plus LLM latency.
Horizontal replicas are therefore the cleanest way to increase concurrency.

The main architectural change required before true multi-replica operation is
replacing the SQLite checkpointer with a shared database-backed alternative.
The intended upgrade path is **Postgres-backed checkpoint persistence**. In the
final implementation this should be localized near the graph-builder layer
rather than spread across every node.

Recommended production path:

1. Keep the agent stateless between requests except for checkpoint persistence.
2. Put accepted incidents behind a queue.
3. Make downstream ticket and notification writes idempotent.
4. Scale replicas independently from the UI.

### Vector store

Qdrant scales much more naturally as its own concern than as a side effect of
the agent service. Once retrieval load rises, the right move is to upgrade or
cluster Qdrant directly rather than to keep adding API replicas and hoping the
problem disappears.

The production path is:

- move from single-node to **cluster mode**
- shard collections when repository scope grows
- add replicas for higher availability
- tune HNSW and compression settings for the actual query mix

For Upstream specifically, the curated snapshot strategy delays this pain. That
is a deliberate trade-off: it keeps early retrieval efficient and predictable
because the indexed surface area stays narrow and the codebase does not change
daily.

### Observability

Langfuse is already designed for more serious deployments than a hackathon
demo. Its official self-hosting documentation recommends Docker or VM-based
deployments for lower scale and Kubernetes / AWS / Azure / GCP / Railway for
production-scale or high-availability deployments.

The same documentation notes that self-hosted Langfuse uses the same core
infrastructure model as Langfuse Cloud, including separate web and worker
containers plus Postgres, ClickHouse, Redis or Valkey, and S3 / Blob storage.
They also state that Langfuse Cloud serves **thousands of teams**.

For Upstream, that means observability can be split into its own tier once
traces become operationally important. I treat **~10M events/day** as a
planning ceiling for a dedicated, properly provisioned Langfuse deployment, not
as a guaranteed benchmark. It is useful for capacity thinking, but it should be
validated against real event size, retention, and storage layout before any
promise is made.

### Mocks and downstream integrations

The two mock services should not be scaled as if they were long-term platform
components. The real production strategy is replacement, not heroic
optimization.

Recommended path:

- replace Jira mock with Jira API or equivalent ticketing integration
- replace notification mock with Slack, Teams, email, PagerDuty, or an internal
  notification service
- preserve the message contracts and payload schemas from the mocks

That lets the demo prove the orchestration model now without locking the real
system into toy storage semantics later.

### LLM providers

Provider scaling is partly technical and partly commercial. At larger volume,
the system needs request throttling, provider-aware rate limiting, retry
budgets, fallback logic between Claude and OpenAI, and a clear decision about
when Ollama is acceptable.

For privacy-sensitive deployments, Ollama should live on a dedicated
GPU-capable node or at minimum on compute isolated from the API servers. Local
inference can remove cloud API costs, but it should not silently consume the
same machines that are serving intake traffic.

### UI service

The UI is the easiest service to scale. It is mostly server-rendered and thin.
In a production deployment it can be replicated independently, cached
aggressively for static assets, and protected with rate limits and
authentication. If the UI becomes the main scaling anxiety, the larger
constraint is probably somewhere else.

## 4. Production Hardening Checklist

Before calling Upstream production-ready, the hardening list is:

- **Replace SQLite with Postgres.** This is the most important change before
  multi-replica rollout because shared checkpoint persistence matters more than
  local simplicity at scale.
- **Add Redis as a cache.** Useful for repeated incident patterns, retrieval
  results, and duplicate lookups during retries. It should stay a latency
  optimization, not a hidden source of truth.
- **Add a queue between UI and agent.** Kafka, RabbitMQ, or a managed queue all
  work. The important property is durable acceptance before expensive analysis.
- **Add OpenTelemetry alongside Langfuse.** Langfuse is excellent for LLM
  observability but is not a full replacement for infrastructure telemetry.
- **Add rate limiting per user and team.** A noisy script or retry storm should
  not starve everyone else.
- **Add SSO and RBAC.** Once the UI moves beyond demo mode, identity and
  authorization are table stakes.
- **Harden log and object retention.** Uploaded logs and screenshots may contain
  sensitive data and need explicit retention and deletion policies.

## 5. Cost Analysis

### Claude cost per incident

Using the planning envelope from Section 1 and official Anthropic pricing
checked on April 8, 2026:

| Assumption | Low | High |
| --- | --- | --- |
| Input tokens | 12K | 25K |
| Output tokens | 1.5K | 4K |
| Input cost @ $3/MTok | $0.036 | $0.075 |
| Output cost @ $15/MTok | $0.0225 | $0.060 |
| Total | $0.0585 | $0.135 |

That means:

- **100 incidents/day** is roughly **$6-$14/day**
- **1,000 incidents/day** is roughly **$60-$135/day**
- **10,000 incidents/day** is roughly **$600-$1,350/day**

Those numbers matter because they show when provider routing becomes a real
budget choice rather than a convenience setting.

### Langfuse self-hosted cost

Langfuse self-hosted cost is mostly infrastructure cost, not vendor license
cost for the open-source deployment path. For planning, I would budget
**$80-$200/month** for a small internal environment with modest retention and no
strong HA guarantees, and **$300-$1,000+/month** once production-grade
databases, object storage, backups, and HA expectations are added. These are
infrastructure estimates, not official Langfuse list prices.

### Qdrant cost at scale

Qdrant's official pricing starts at **$0** with a **1 GB free cluster**. Their
billing documentation also gives an example where a cluster costing **$85/month**
appears as **8,500 resource usage units** on a cloud-provider marketplace bill.

For Upstream, the curated eShop snapshot should keep early costs low. A
sensible planning envelope is:

- **$0-$20/month** while prototyping on a very small footprint
- **$85+/month** once moving into dedicated paid capacity
- **low hundreds per month and up** for highly available, replicated, and
  production-grade vector infrastructure

### Ollama cost model

Ollama changes the budget shape. The API bill can drop dramatically, but only
because cost moves to dedicated compute, model storage, slower or lower-quality
triage, and operational ownership of local inference. In other words, Ollama is
not "free"; it is "pay differently."

## 6. Assumptions and Trade-offs

- **Incidents are human-reported.** Upstream is built around skepticism toward
  human diagnosis, so it is stronger at intake triage than at large-scale alert
  correlation.
- **The target codebase is relatively stable.** Build-time indexing is
  reasonable because the curated eShop snapshot does not change daily. The
  trade-off is that a fast-moving monorepo would need incremental re-indexing.
- **Prompts are English-first for now.** This simplifies extraction and
  evaluation during the hackathon, but it leaves multilingual support as an
  obvious future gap.
- **Default quality beats default privacy.** Claude is recommended because the
  core value of Upstream depends on contradiction-aware reasoning, while Ollama
  remains available for privacy-sensitive deployments.
- **Guardrails favor false positives over false negatives.** The current
  prompt-injection detector is intentionally conservative and may reject some
  legitimate reports that contain suspicious phrasing. That trade-off is
  acceptable for the hackathon because evaluator-visible safety matters more
  than perfect recall on borderline submissions.
- **Demo clarity beats production completeness.** Mocks, SQLite, and a curated
  snapshot make the system easier to review inside hackathon constraints, while
  still preserving service boundaries that can be upgraded later.
