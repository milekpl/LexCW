# Implementation Plan: IPA Anomaly Detection (Autoencoder) + POS-Conditioned G2P

Two models, one dataset:

* **byT5 G2P** (`app/services/ipa_byt5_service.py`) — *generates* IPA. Deployed, working, underperforming.
* **IPA autoencoder** — *judges* IPA. To be built. Learns what well-formed IPA looks like; flags
  transcriptions that do not.

Reference implementation:
`/mnt/d/Dokumenty/slownik-wielki/flextools-main/FlexTools/Modules/Wielki/g2p`
(`anomaly_detector.py`, `data_extractor.py`, `tokenizer.py`, `trainer.py`).

---

## 1. The dataset is wrong, and that is the root cause

Training data is currently **(headword, IPA) pairs** (`pairs.json`, 326K lines;
`scripts/extract_ipa_pairs_direct.py`, `scripts/ipa_training/export_ipa_pairs.py`). English
pronunciation depends on grammatical function, so a pair-only dataset gives the model **contradictory
supervision for identical inputs** — it is asked to map *separate* to both `ˈsepərət` and `ˈsepəreɪt`
and cannot possibly learn which.

Measured against the real dictionary (`/home/milek/basex123/data`, 153,421 entries):

| | count |
|---|---|
| entries with IPA (`seh-fonipa`) | 90,533 |
| entries with IPA **and** POS | **88,675 (98%)** |
| headwords with >1 entry and >1 distinct IPA | 428 |
| …of those, disambiguated by POS | **366 (86%)** |
| entries with >1 POS internally | 74 |

Examples: *separate, conscript, decrease, certificate, forte, grant, cross-section, air*.

Two things follow:

1. **POS is already there.** 98% of IPA-bearing entries carry `sense/grammatical-info/@value`.
   Triples cost an extra column in the export, nothing more.
2. **The damage is larger than 440 headwords.** Those are only the cases where *both* readings happen
   to be recorded. The noun/verb stress alternation is a productive rule of English
   (ˈrecord/reˈcord, ˈpermit/perˈmit, ˈconduct/conˈduct); without POS the model cannot represent the
   rule at all, so it mispronounces the whole class — including words where only one reading exists in
   the dictionary and no contradiction is visible in the data.

The reference `data_extractor.py` **already collects POS** (`pos`, `pos_distribution`) — and then the
tokenizer, model and detector never consume it. The information is extracted and thrown away.

---

1.  [ ] **Triples, everywhere**

    1.1. [x] **Export (headword, POS, IPA) triples**
        *   Implemented: `scripts/ipa_training/export_ipa_triples.py` → `triples.json` (98,437 triples, 90,313 entries, 0 malformed). Retires `pairs.json`.
        *   38 raw POS values normalised to a 14-tag set; the unmappable tail (`su`, `c`, `pre`) and the 1,858 entries with no POS become `UNK` rather than being discarded or, worse, guessed at.
        *   Multiple POS sharing one pronunciation is not a problem — they share it, and each gets a row (72 entries). The only unalignable case is **several POS *and* several distinct IPA**, where nothing in the LIFT says which reading belongs to which: **5 entries**, written to `triples.ambiguous.json` and never trained on. (An earlier draft of this plan called alignment "a real problem". It is five entries. The export simply never guesses.)
        *   Recovered the comma-separated variants (`ˈhektəˌɡræf, ˈhektəɡrɑːf, ˈhektəʊɡrɑːf`) that the old `.split(",")[0]` silently threw away — 7,136 fields' worth.

    1.2. [ ] **Condition byT5 on POS and retrain**
        *   The source prefix is already plumbed through: `IPAByT5Service` reads `source_prefix` from `metadata.json` and prepends it. Encode POS in the input, e.g. `"<NOUN> separate"` → `ˈsepərət`.
        *   Retrain per [[byt5-training-rtx4060-wsl]] (adafactor, batch 64, bf16 — AdamW and larger batches silently spill VRAM on the 4060).
        *   Evaluate specifically on the 428 heterophonic homographs, which the current model *cannot* get right more than half the time by construction. This is the headline metric: a pair-trained model is at chance there; a triple-trained one should not be.

## Results so far (2026-07-14)

**Triples export — done.** `scripts/ipa_training/export_ipa_triples.py` → `triples.json`:
98,437 triples from 90,313 entries, 0 malformed, 5 unalignable (written to
`triples.ambiguous.json`, never into training). The homographs now separate:

```
separate   ADJ=ˈseprət    VERB=ˈsepəreɪt
record     NOUN=ˈrekɔːd   VERB=rɪˈkɔːd
permit     NOUN=ˈpɜːmɪt   VERB=pəˈmɪt
conduct    NOUN=ˈkɒndʌkt  VERB=kənˈdʌkt
```

350 headwords where POS separates genuinely different IPA — every one of them an
unlearnable contradiction in the old pairs file.

**Anomaly detector — done, and it changed the design.** Detection rate at a *measured* 1.28%
false-positive rate on unseen clean data (`scripts/ipa_training/train_ipa_autoencoder.py`):

| corruption | reference-style AE | **density model** |
|---|---|---|
| moved stress | ~34% | **46.1%** |
| swapped phonemes | ~26% | **45.9%** |
| dropped stress | 4.5% | **33.8%** |
| confused phoneme | 6.4% | **18.5%** |
| dropped schwa | 6.6% | **14.4%** |
| wrong-POS reading | 0.1% | 1.2% (at chance — see below) |

Three findings, none of which was the plan:

*   **The obvious fix made it worse.** Giving the autoencoder's decoder autoregression —
    the correct diagnosis of the reference model's flaw — lets teacher forcing hand it the
    ground truth, so it learns to *copy* rather than compress. Loss fell to 0.03 and
    detection collapsed to 3%. A model that reconstructs everything distinguishes nothing.
*   **Reconstruction is the wrong objective entirely.** Any autoencoder feeds the string it
    is judging into its own encoder, so it encodes the anomaly and rebuilds it. Replaced
    with a **density model** — a POS-conditioned character LM that never sees the string it
    scores and must predict each phoneme from the prefix. That is what the table above
    measures.
*   **POS conditioning does not help the detector.** `--no-pos` scores the same (49.7% vs
    46.1% on moved stress). It was expected to catch a plausible pronunciation filed under
    the wrong POS — and it cannot, because *no IPA-only model can*: ˈrekɔːd and rɪˈkɔːd are
    both unremarkable for a noun (compare ˈrecord, hoˈtel). That error is only visible if
    you know the **headword**, which makes it byT5's job. POS is decisive for *generation*
    and near-useless for *density*. The two detectors are complementary; this one owns
    phonotactics.

Remaining: dropped schwa and confused phonemes are still weakly detected (14-18%) — they
are near-homophonous by construction, and may simply not be recoverable from phonotactics
alone. That is the byT5-disagreement signal's territory too.

2.  [ ] **The detector, decomposed**

    One scorer straining to cover every error class is what produced 46% on stress and 18%
    on confused phonemes. Different errors are visible to different models, and — the point
    that reorganised this plan — **stress is not an anomaly-detection problem at all.** We
    already know where the stress is in every entry. That is a free label, so it is a
    *supervised* problem, and one-class methods are the wrong tool for it entirely.

    Four detectors, each on the class it can actually see:

    2.1. [ ] **Deterministic stress rule (no model)** — ships first
        *   A stress mark that is not at a syllable onset is an error by construction, not by probability: `ˌriːɪmprˈeʃən` has the mark *inside* the `pr` cluster. ~100% precision, milliseconds, and it explains itself to the editor.
        *   Strictly better than any probabilistic model on the cases it covers, so there is no reason to reach for ML here. See §3.

    2.2. [ ] **Supervised stress-position classifier** — the real lever
        *   Predict `p(stress index | POS, syllable count, suffix, phoneme skeleton)` from the syllabified triples; flag entries whose *stored* stress position the model finds improbable.
        *   Measured predictability of stress position (majority-per-context, single-word entries with one primary stress, n=65,963):

            | context | correct |
            |---|---|
            | nothing (global majority) | 55.7% |
            | + syllable count | 62.9% |
            | + POS | 66.2% |
            | + suffix (3 graphemes) | **84.3%** |

        *   **This number is optimistic and must not be trusted yet.** It is majority-class lookup over 8,638 contexts *on the training data itself* — memorisation, re-measured on the data it memorised. A held-out estimate will be lower, possibly much lower for rare suffixes. Re-measure properly before building on it.
        *   Even so the shape is unambiguous and matches English stress phonology: the **suffix** carries most of the signal (`-ity`, `-tion`, `-ic` fix the stress relative to the end of the word), and the density model cannot see it at all — it reads phonemes left to right and never learns the grapheme suffix.
        *   **On the SVM question.** A one-class SVM as a drop-in replacement for the density model would likely be *worse*: same boundary/density job, worse scaling (kernel matrix over 66K samples), no localisation, and decision values that need Platt scaling before they can be thresholded at a target FPR. It would still need these features to be any good — which is the tell that the **features**, not the classifier family, were doing the work. For the supervised stress problem an SVM is a perfectly reasonable choice, but it has no edge over logistic regression or gradient boosting on ~8.6K categorical contexts, and those hand you **calibrated probabilities**, which is exactly what a 1%-FPR threshold needs. Prefer them; keep the SVM as a baseline to check we are not fooling ourselves.

    2.3. [x] **Density model over phonemes** — keeps the residual
        *   Implemented (`scripts/ipa_training/train_ipa_autoencoder.py --model density`). Owns what the others cannot see: confused vowels, dropped schwas, odd phonotactics. It **localises** the error (which phoneme it balked at), which neither the rule nor the classifier does.
        *   Retained rather than replaced, but demoted: it is the residual detector, not the primary one.
        *   Do **not** revive the autoencoder — see the results section for why reconstruction is the wrong objective, and why the obvious fix to the reference model made it strictly worse.

    2.4. [ ] **byT5 disagreement** — word-specific errors
        *   Generate from (headword, POS) and compare with what is stored (CER). This is the only detector that can catch a *plausible* pronunciation filed under the wrong word or POS — `rɪˈkɔːd` stored as the noun — because it is the only one that knows the headword. No IPA-only model can do this, at any level of sophistication (see the `wrong_pos_stress` row: ~1%, i.e. chance).
        *   Depends on 1.2 (POS-conditioned byT5).

    2.5. [ ] **Combine them honestly**
        *   Report each detector's flags separately as well as combined. They fail differently; "two independent detectors agree" is the high-precision set worth an editor's time, and a union is the high-recall set worth a batch review.
        *   Calibrate the *combined* flag rate, not each detector's in isolation — four detectors at 1% FPR each is a 4% flag rate on a clean dictionary if they are independent, which is 3,600 false flags on 90K entries.

3.  [ ] **Stress normalisation and syllable structure (rule-based)**

    Using `/mnt/d/…/Wielki/syllabify.py` (maximal-onset syllabifier; `Syllable.__str__`
    already re-emits the stress mark at the syllable onset, so `string_without_dots()` is a
    canonical re-serialisation). Measured on `triples.json`, single-word IPA only:

    | | |
    |---|---|
    | parses without error | **100%** (0 failures on 5,000 sampled) |
    | already canonical | **94.8%** |
    | stress mark would move | 5.2% → **4.1%** after the `g` fix below |

    3.1. [ ] **Fix the phoneme inventory first — it has a real bug**
        *   `en.yml` declares onsets with **ASCII `g` (U+0067)** (`gr`, `gl`, `gw`, `gj`) while the dictionary's IPA uses **`ɡ` (U+0261, script g)**. The consonant list has both; the onset list does not. So every `ɡr`/`ɡl`/`ɡw` cluster fails the onset test, the syllabifier splits it, and the stress mark is dragged along: `ˌdiːˈɡriːs` → `ˌdiːɡˈriːs`, `ɪˌlektrəʊkɑːdɪəˈɡræfɪklɪ` → `…dɪəɡˈræfɪklɪ`.
        *   Unifying the two g's fixes both, and drops the "would move" rate from 5.2% to 4.1%. **Normalising before this fix would corrupt data.**

    3.2. [ ] **Flag, do not rewrite — the syllabifier is not always right**
        *   Of the 4.1% that still move, some are genuine errors and some are the syllabifier's own:
            *   **Real errors it catches**: `ˌriːɪmprˈeʃən` → `ˌriːɪmˈpreʃən` (the stress mark sits *inside* the `pr` cluster), `ˌlɑːrɪŋɡˈɒtəmɪ` → `ˌlɑːrɪŋˈɡɒtəmɪ`.
            *   **Errors it would introduce**: `dɪsˈmembəmənt` → `dɪˈsmembəmənt` (maximal onset overrides the *dis‑* morpheme boundary), `ˌnɔːθˈwestwədlɪ` → `ˌnɔːˈθwestwədlɪ` (north+west compound), `ˌbiːˌesˈtiː` → `ˌbiːˌeˈstiː` (spelled abbreviation).
        *   Maximal onset has no notion of morphology, and English stress placement respects morpheme and compound boundaries. So a blanket rewrite is not safe.
        *   **Auto-fix only the unambiguous class**: the stress mark falls *inside* a cluster whose remainder is itself a valid onset (`mprˈeʃ`). Nothing is being decided there — the mark is simply in an impossible position. Everything else goes to a review queue (~3,100 single-word entries), which is a tractable editorial task and exactly the kind of thing batch validation is for.
        *   Syllabify **per word** (split on spaces): the script drops spaces and happily syllabifies across word boundaries (`dɪˈlɪvərɪ ɡɜːl` → `…rɪɡ.ɜːl`). 22,731 of 98,437 IPA strings are multiword.

    3.3. [ ] **Deterministic stress validator for batch validation**
        *   No model needed: a stress mark not at a syllable onset is an error by construction. Precision ~100%, runs in milliseconds, and it explains itself to the editor ("stress mark inside the cluster *pr*"). This should ship *before* any ML detector — it is strictly better than a probabilistic model on the cases it covers.

    3.4. [ ] **Syllable count and stress index as features — where they can and cannot go**
        *   **Density detector: yes.** The IPA is given, so its structure is computable. Conditioning on (POS, syllable count, stress index) lets the model learn the actual regularity — English stress is largely predictable from syllable count, POS and suffix — instead of inferring it character by character. This is the most promising lever on the 46% stress-detection rate.
        *   **byT5 G2P: not as an input.** Syllable count of the *pronunciation* is not known at inference time; it is part of what we are predicting. Feeding it in would be leakage and the model would collapse at serving time.
        *   **byT5: yes as an auxiliary target.** Multi-task — predict the IPA *and* (syllable count, stress index). That gives the model an explicit, supervised notion of stress placement without leaking anything, which is the honest version of "providing numerical data on stress position helps it learn the regularity".

4.  [ ] **Evaluation without labelled anomalies**
    *   There is no ground-truth set of bad transcriptions, so build one: take held-out good IPA and **inject realistic corruptions** — move the stress mark, delete a schwa, substitute a phoneme from a confusion set (ɪ/iː, æ/ʌ, ɒ/ɔː), drop a syllable, swap adjacent phonemes. Implemented in `train_ipa_autoencoder.py`; reuse it for every detector so the numbers are comparable.
    *   **Calibrate and measure on disjoint clean splits.** Doing both on the same data returns the target FPR by construction and proves nothing. (The current script splits held-out in half: target 1%, measured 1.28%.)
    *   Report detection rate at a fixed false-positive rate. A detector that flags 5% of a clean dictionary is useless regardless of its recall.
    *   Corruptions measure *sensitivity*. Only human review of the top-N flagged **real** entries measures whether the flags are worth an editor's time — and that is the number that decides whether this ships.

5.  [ ] **Serving**
    *   Mirror `IPAByT5Service`: process-wide singleton, model discovered server-side under `instance/ipa_models/`, `local_files_only=True`, `trust_remote_code=False`, `available: false` when no model is deployed. See `docs/IPA_ANOMALY_DETECTION.md` and the existing `app/services/ipa_anomaly_service.py`.
    *   Endpoint `POST /api/pronunciation/batch-validate` is already specified in `docs/plans/2026-06-23-api-ecosystem-and-external-tools.md` (sync ≤500 entries, async job above that). Gate it with `@require_auth("pronunciation:read")` — it reads dictionary data and returns scores; it writes nothing.
    *   **Do not repeat the draft-button bug**: the UI must distinguish "no model deployed" from "you are not signed in". `auth.js` now handles the auth case globally, and `available: false` must mean exactly one thing.

---

## Suggested order

Cheapest and most certain first; nothing here needs the GPU until step 4.

1.  **Fix `en.yml`** (§3.1). The ASCII-`g` / script-`ɡ` mismatch in the onset list. Everything
    syllable-based is wrong until this is done, and normalising before it would *corrupt*
    data at scale.
2.  **Ship the deterministic stress rule** (§2.1). No model, ~100% precision, immediate value
    to editors. It also produces the first honest estimate of how many real stress errors the
    dictionary contains — which tells us whether the ML detectors are worth building at all.
3.  **Re-measure stress predictability on held-out data** (§2.2). The 84.3% is memorisation and
    must be re-earned before anything is built on it. Cheap, CPU, decides the next step.
4.  **Retrain byT5 on the triples with the POS prefix** (§1.2), and evaluate on the 350
    homographs where the pair-trained model is at chance by construction. This is the headline
    result, and the one that pays back the whole triples exercise.
5.  **Supervised stress classifier** (§2.2) and **byT5 disagreement** (§2.4), then combine (§2.5).

## Notes

*   **Where the data actually is:** the real dictionary is `/home/milek/basex123/data` (153,421 entries), *not* the `~/basex/data` the server defaults to — see [[basex-two-data-dirs]]. `extract_ipa_pairs_direct.py` hardcodes the right path, which is why exports work even when the app shows a few hundred entries.
*   POS conditioning is the thread running through all of this: [[g2p-needs-pos-triples]].
