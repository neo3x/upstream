# eShop Snapshot

This folder contains a **curated subset** of files copied from
[dotnet/eShop](https://github.com/dotnet/eShop), used as technical context by
the Upstream agent during incident triage.

The snapshot is intentionally small.
It is not a mirror of the full repository.
It only includes files that are directly useful for the two code-grounded demo
scenarios:

1. **Identity cascade**
2. **Silent EventBus**

The prompt-injection scenario does not rely on eShop code and is therefore not
represented here.

## Source

- Repository: <https://github.com/dotnet/eShop>
- Pinned commit: `b81ad9557090cc37233b9d1a0a729db7b44b6f14`
- Snapshot date: April 9, 2026

Pinning the source commit is important because file locations in `dotnet/eShop`
can change over time.
Upstream's indexer and later retrieval behavior should point to a stable,
documented source revision.

## License and Attribution

The files in this folder are copied from `dotnet/eShop`,
which is licensed under the **MIT License**.
The original copyright belongs to the **.NET Foundation and Contributors**.

- Original repository license:
  <https://github.com/dotnet/eShop/blob/main/LICENSE>
- Upstream root license:
  [LICENSE](../LICENSE)

These copied source files remain subject to the original MIT terms from the
source repository.

## Purpose

Upstream is an SRE intake and triage agent that grounds its hypotheses in real
code from a real e-commerce application.
Rather than relying on generic knowledge of microservices,
the agent will semantically search this snapshot to find evidence supporting or
contradicting the reporter's diagnosis.

The snapshot is later indexed in Phase 4 using
[indexer/eshop_files.yaml](../indexer/eshop_files.yaml).

## Curation Criteria

Files were selected using one question:

**Will the agent plausibly need to cite this file when explaining one of the
demo scenarios?**

If the answer was no,
the file was left out.

The result is a targeted snapshot that favors:

- auth and identity wiring used by `Ordering.API`
- token and scope configuration exposed by `Identity.API`
- event publication and consumption around payment success
- base EventBus abstractions and the RabbitMQ implementation
- one cross-cutting auth helper from `eShop.ServiceDefaults`
- original upstream documentation artifacts that help with architecture context

## Scenario Coverage

### Scenario 1 — Identity cascade

Relevant files show:

- `Ordering.API` requires authorization on order endpoints
- `Ordering.API` resolves the current user from auth claims
- `eShop.ServiceDefaults` configures JWT bearer authentication using Identity
  authority and audience settings
- `Identity.API` exposes the IdentityServer setup,
  API scopes,
  resources,
  and client definitions used by downstream services

Important note:
the current pinned eShop commit does **not** expose a neat,
single file that literally shows "`Ordering` calls `Identity` and turns a 401
into a 500".
Instead,
the relationship is expressed through shared authentication wiring,
JWT bearer configuration,
and protected ordering endpoints.
This snapshot reflects the real code as it exists at the pinned commit,
not an older mental model of the repo.

### Scenario 2 — Silent EventBus

Relevant files show:

- `Ordering.API` publishes and consumes integration events
- `Ordering.API` moves order state forward when payment-success events arrive
- `PaymentProcessor` publishes `OrderPaymentSucceededIntegrationEvent`
  in the current pinned commit
- `EventBus` defines the publish/handle abstractions
- `EventBusRabbitMQ` binds those abstractions to RabbitMQ

Important note:
the phase brief described `Ordering` as the publisher of
`OrderPaymentSucceededIntegrationEvent`.
In the current pinned eShop commit,
that specific event is actually published from `PaymentProcessor`
and consumed by `Ordering.API`.
The snapshot preserves the real flow instead of forcing the older wording.

### Scenario 3 — Prompt injection

No eShop files are needed for this scenario.
It is handled entirely by Upstream guardrails and safety logic.

## Included Folders

```text
eshop_snapshot/
├── README.md
├── Ordering.API/
├── Identity.API/
├── PaymentProcessor/
├── EventBus/
├── EventBusRabbitMQ/
├── eShop.ServiceDefaults/
└── docs/
```

### Why `PaymentProcessor` is included

`PaymentProcessor` is present because the current eShop event flow uses it to
publish `OrderPaymentSucceededIntegrationEvent`.
Leaving it out would make the payment-success path incomplete and reduce the
agent's ability to explain why an order might remain in the wrong state when an
expected event never arrives.

### Why `eShop.ServiceDefaults` is included

`Ordering.API` calls `AddDefaultAuthentication()`,
but the implementation of that helper lives in `eShop.ServiceDefaults`.
Including that file makes the auth relationship to `Identity.API` traceable
instead of implicit.

## Modification Policy

All copied eShop source files in this folder are **unmodified copies** taken
from the pinned commit above.

The only files authored by the Upstream project in this folder are:

- `eshop_snapshot/README.md`
- any future local metadata files added explicitly for indexing support

If a copied upstream file ever needs to be changed locally,
that change must be documented here with the reason.
At the time of this phase,
no such modifications have been made.
