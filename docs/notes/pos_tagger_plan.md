# POS Tagger Integration Plan

## Background
- spaCy is slow mainly due to per-request model loading; with `nlp.pipe()` + disabled
  components (`parser`, `ner`, `senter`) it does ~50k tokens/sec on short headwords.
- We run a local LanguageTool server that already has a POS tagger + custom SVM
  corrections trained on English + Polish dictionary data.
- LT's tagger is very fast and domain-adapted; disambiguation rules could be further
  tuned for comma-delimited dictionary definitions (different POS context than prose).

## Proposed Architecture

```
Request: POST /api/ai/pos-tag  { "text": "acid", "lang": "en" }
         ↓
POSTaggerService
  .tag(text, lang)
    1. LT server  (primary)  — configured via project_settings.external_service_urls["languagetool"]
    2. spaCy batch (fallback) — en_core_web_sm, pipe(), disable=[parser,ner,senter]
    3. LT CLI subprocess      (emergency fallback)
         java -jar languagetool-commandline.jar --taggeronly -l en
```

## spaCy Speed Tips (if used as fallback)
```python
nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "senter"])
tags = list(nlp.pipe(headwords, batch_size=256))   # ~50k tok/sec on sm model
```
- Load model once at startup (singleton), not per request
- Use `sm` not `trf` — accuracy difference minimal for 1-3 word dictionary lemmas
- Enable CUDA with `spacy.prefer_gpu()` if available

## LT Server Integration
- LT already running locally (port TBD — store in project_settings.external_service_urls)
- Tagging code already written elsewhere — trivially portable
- Key advantage: LT POS disambiguation rules can be tweaked for dictionary input
  (comma-delimited definitions ≠ prose; different syntactic context)
- Custom SVM tagger trained on English + Polish dictionary entries already in use

## TODO
- [ ] Wire up LT server URL in project settings (existing `external_service_urls` JSON field)
- [ ] Implement `POSTaggerService` with the three-backend fallback chain
- [ ] Build `POST /api/ai/pos-tag` endpoint
- [ ] Add "Suggest POS" button in entry edit UI (calls the endpoint for the headword)
- [ ] Consider batch POS suggestion for entries missing grammatical-info
- [ ] Explore LT POS disambiguation rule tweaks for comma-delimited input
