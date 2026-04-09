EXTRACTION_PROMPT = """You will receive an incident report from a human reporter.
The report contains:
- Free-text description of the symptom
- A log file (potentially long)
- Optionally, a screenshot from a dashboard or UI

Your task: extract structured symptoms from this evidence.

Be specific. Use exact service names mentioned. Use exact error codes seen in logs.
Do NOT invent services or errors that are not visible in the input."""

