# CampusFix AI — 90-second demo

Use synthetic reports. Never delete an existing database just to reset the demo; use a separate `CAMPUSFIX_DB_PATH` if needed.

| Time | Show | Say |
|---|---|---|
| 0–10s | Dashboard and sidebar | “CampusFix turns campus maintenance messages into a trackable queue.” |
| 10–30s | Report an issue: missing room label, Academic Block, A-101, automatic priority | “A student adds the issue and location. Rules suggest a category and priority; Other defaults to Low when no hazard matches.” |
| 30–40s | Ticket ID and Track a ticket | “Every saved complaint gets a persistent ID. Students can check progress with this reference.” |
| 40–55s | Staff desk, manual priority dropdown | “Students can choose priority themselves. Staff can override it, and we show who chose the current priority separately from the recommendation.” |
| 55–70s | Start work, then Mark as resolved, then dashboard | “Staff move a ticket through Reported, In Progress, and Resolved. Dashboard counts come directly from SQLite.” |
| 70–82s | Expand Local AI assistant on a non-hazard ticket | If Gemma is actually running: “Local Gemma reviews priority or suggests safe checks only when asked. The queue priority stays unchanged until staff explicitly acts.” If offline: “Local AI is optional; it is not connected in this demo, and the correctly labelled rules still work.” |
| 82–90s | Closing | “The next step is a pilot with real maintenance staff after adding campus authentication, permissions, and deployment safeguards.” |

## Before recording

- Confirm the source update is installed and the app launches.
- Use the real ticket ID returned by your submission; do not assume it is CF-000001.
- Run `python -m pytest -q` from the project environment.
- If demonstrating AI, warm the model first with `ollama run gemma4:e4b "Reply READY."` and make a real test request. Do not present mocked or rule-based output as a model response.
- For sparks, gas leaks, flooding, or other potential danger, show the fixed escalation warning—not DIY repair instructions. This is not an emergency-response system.
- A localhost address is not a public demo link. Use a recording if your event accepts one.
