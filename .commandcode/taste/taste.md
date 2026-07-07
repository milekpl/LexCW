# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# testing
- When investigating if a feature exists, check test files for `skip`/`xfail` markers first — it may be a regression, not something never built. Confidence: 0.85
- Proceed in TDD fashion: write/update tests before implementation code. Confidence: 0.70
- Use round-trip e2e tests (save → reload → assert data integrity) to verify data persistence after migrations. Confidence: 0.70

# workflow
- When delegating implementation to agents/subagents, independently verify the work with separate tests and audit tools. Confidence: 0.75
- Prioritize solid, complete deliverables over minimal but fragile solutions. Confidence: 0.75

