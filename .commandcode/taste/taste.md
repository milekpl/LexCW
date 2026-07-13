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
- Use Kaggle (not Colab) for ML model training notebooks. Confidence: 0.60
- For byte-level tokenizers (like ByT5), use dynamic padding via DataCollatorForSeq2Seq instead of static padding='max_length' — static padding on short byte sequences creates extremely sparse loss signals and causes model collapse. Confidence: 0.70
- Don't pass 'tokenizer' to Seq2SeqTrainer constructor — it's not a valid keyword argument; the data collator handles tokenizer needs. Confidence: 0.70
- For Kaggle notebooks, use IPython.display.FileLink for download links — it displays a clear clickable link; don't replace it with shutil.move + print instructions. Confidence: 0.80
- For ML model training (especially GPU-heavy like ByT5), use the existing Colab/Kaggle notebooks instead of training locally on the dev machine. Confidence: 0.90

