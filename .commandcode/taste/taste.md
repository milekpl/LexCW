# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# testing
- When investigating if a feature exists, check test files for `skip`/`xfail` markers first — it may be a regression, not something never built. Confidence: 0.85
- Proceed in TDD fashion: write/update tests before implementation code. Confidence: 0.70
- Use round-trip e2e tests (save → reload → assert data integrity) to verify data persistence after migrations. Confidence: 0.70

# workflow
- When delegating implementation to agents/subagents, independently verify the work with separate tests and audit tools. Confidence: 0.75
- Prioritize solid, complete deliverables over minimal but fragile solutions. Confidence: 0.75

# shortcuts
- Use Escape (Esc) key for cancel/close actions instead of Ctrl+Q. Confidence: 0.75

# architecture
- When adding new features alongside existing ones, keep and complement the existing approach rather than replacing it — especially when both approaches have different strengths. Confidence: 0.70
- When adding caching, integrate with the existing Redis infrastructure rather than adding new ad-hoc in-memory caches. Confidence: 0.60
- For infrequently-changing data (e.g., entry relations that change "once every two years"), use longer TTLs matching the data's stability — 24h or 7d — rather than short default TTLs like 1 hour. Confidence: 0.75

# ml-training
See [ml-training/taste.md](ml-training/taste.md)
