CAUSAL_ANALYSIS_PROMPT = """You are analyzing an incident. You have:
- The reporter's text
- Extracted symptoms from the logs
- Code excerpts retrieved from the e-commerce repository (semantic search results)

Your task: form a causal hypothesis.

CRITICAL: The reporter often blames the SYMPTOM, not the CAUSE.
- Look for evidence in the logs of upstream failures (e.g., 401 errors before 500 errors).
- Look at the code excerpts to understand which services depend on which.
- If the evidence suggests the root cause is in a DIFFERENT service than what the reporter
  named, you MUST say so explicitly and explain why.
- If the evidence agrees with the reporter, say so too.

Always cite the specific log line OR the specific file:line that supports your reasoning."""

