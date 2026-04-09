# Guardrails Evidence

This folder contains the Phase 7 prompt-injection rejection evidence bundle:

- `1-rejection-response.png`: rendered rejection response showing the rejected incident payload result
- `2-notification-security-alert.png`: rendered Notification mock page with the security alert evidence
- `3-jira-security-ticket.png`: rendered Jira mock page with the security review ticket evidence
- `4-guardrails-log.png`: rendered structured log evidence for `guardrails.injection_detected` and `guardrails.rejected`
- `rejection_response.json`: raw rejected incident response payload
- `notification_security_alert.json`: raw Notification mock API response
- `jira_security_ticket.json`: raw Jira mock API response
- `guardrails_log_lines.txt`: raw structured log lines captured from the agent output

The HTML files in this folder were used as local render sources for the PNG evidence.
