SEVERITY_PROMPT = """Given the agent's hypothesis and the blast radius (number of affected services),
assess severity:
- "critical": payment, checkout, or auth completely down
- "high": multiple services degraded, customer-visible
- "medium": single service degraded, partial impact
- "low": cosmetic, internal-only, or unclear impact

Suggest the team most likely responsible based on the suspected root service.
- Identity / auth issues route to `identity-team`
- RabbitMQ / EventBus / messaging issues route to `messaging-team`
- Ordering-only issues route to `ordering-team`"""
