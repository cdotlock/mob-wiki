---
title: SFX Pipeline Design
updated: 2026-05-12
tags: [sfx, audio, pipeline, elevenlabs, normalizer]
---

# SFX Pipeline Design — `sfx-normalizer` skill + dramatizer integration

**Status:** design approved 2026-05-12
**Author:** AI-assisted via superpowers brainstorming
**Spec date:** 2026-05-12
**Scope:** add a complete SFX pipeline parallel to the existing music pipeline. No changes to backgrounds, sprites, CGs, or any other asset stream.

---

## Problem

Episode scripts use `@sfx play <name>` 53 times across 60 final LS files with **43 unique semantic names** (`doorbell_chime_clean`, `phone_buzz_short`, `knuckle_door_knock_soft`, …). Today:

- No SFX alias map exists.
- No SFX audio assets exist anywhere in the repo.
- `dramatizer.build` does not emit any `@sfx` → URL mapping.
- Engine-side, `@sfx play X` will silently no-op because the compiled `mapping.json` has no entry for X.

The `music-normalizer` skill (5.5b) solves the analogous problem for BGM by clustering 353 semantic names onto 5 palette files via LLM + injecting a flat `name → URL` lookup into `mapping.json`. SFX needs the same shape — **plus** an AI generation step because, unlike music, we do not yet have any source audio.

## Goals

1. Drop-in pipeline parallel to music-normalizer. New books opt in by adding a `sfx:` section to their dramatizer config; books without that section see zero behavior change.
2. Two-phase workflow:
   - **Phase 1 (normalize):** scan scripts → cluster semantic names into buckets via LLM → write `sfx_alias_map.json` + `sfx_buckets.json` + human-review report.
   - **Phase 2 (generate):** for each bucket, call ElevenLabs Sound Effects API → write `<bucket_id>.mp3` to `raw_audio/<slug>/sfx/`.
3. Hard contract with `dramatizer.build`: if `sfx:` is configured but Phase 1 / Phase 2 products are missing, the build fails with a clear pointer to the missing subcommand.
4. Zero changes to LS spec, Go interpreter, or source `.md` scripts. The integration is a compile-time URL substitution exactly like music.
5. Idempotent and incremental: re-running `normalize` only reclassifies low/medium-confidence entries; re-running `generate` skips buckets that already have a `generated` record (overridable via `--only`).

## Non-goals

- Building a generic AI audio framework. Pluggable provider design is included only to the extent of not hard-coding ElevenLabs string literals; the only implemented provider in this spec is ElevenLabs.
- Touching music-normalizer, asset-prompt-generator, or any other 06-* output.
- Resolving the other three asset gaps (backgrounds 65 missing, KEEP-character sprite 33 missing, CG pipeline). Those have separate specs.
- SFX waveform editing, mixing, or post-production. Each bucket = one raw mp3, played by the engine as-is.

---

## Validated assumptions

A clustering dry-run on the actual 43 names + per-occurrence context produced **28 buckets (1.5:1 compression)**. Distribution:

| Bucket size | Count | Example buckets |
|---:|---:|---|
| 5 names | 1 | `window_tap_glass` (knock_glass_three_taps, tap_glass_three, tap_glass_three_steady, tap_glass_three_uneven, window_tap_soft) |
| 4 names | 1 | `phone_buzz` (4 variants of phone vibration) |
| 3 names | 3 | `doorbell`, `door_knock`, `stair_creak` |
| 2 names | 2 | `rain_soft`, `acoustic_guitar_soft` |
| 1 name | 21 | `speakerphone_static`, `locker_slam_metal`, `splash_loud`, etc. — genuinely unique events |

Full output captured in the brainstorming run; will be regenerated as the real Phase 1 artifact. The 1.5:1 ratio is far lower than music's 70:1 because SFX semantic names refer to concrete distinguishable audio events, not vibe categories.

**Cost estimate (ElevenLabs):**

| Phase | Calls | Unit cost | Subtotal |
|---|---:|---|---|
| Phase 1 LLM cluster | 1 | ~$0.01 | $0.01 |
| Phase 2 first pass | 28 | ~$0.05 | $1.40 |
| Phase 2 re-iterations (2× budget) | ~10 | ~$0.05 | $0.50 |
| **Total budget** | | | **~$2** |

ElevenLabs registration is a Phase 2 prerequisite; Phase 1 is unblocked.

---

## Architecture

### Directory layout

```
novels-to-lunascript/
├── skills/
│   └── sfx-normalizer/                        ← NEW
│       ├── SKILL.md
│       ├── __init__.py
│       ├── __main__.py                         ← subcommand router (normalize|generate)
│       ├── context_collector.py                ← scan @sfx play with surrounding context
│       ├── llm_clusterer.py                    ← LLM call: discover buckets + write alias/buckets JSON
│       ├── elevenlabs_generator.py             ← Phase 2: call ElevenLabs SFX API
│       ├── report_writer.py                    ← normalize_report.md + generation_report.md
│       └── tests/
│           ├── conftest.py
│           ├── fixtures/
│           ├── test_context_collector.py
│           ├── test_llm_clusterer.py
│           ├── test_elevenlabs_generator.py
│           └── test_orchestrator.py
│
├── lunascripts/no-rules-in-bad-ideas/
│   └── 05.5c-sfx-normalizer/                  ← NEW (05.5b is music)
│       ├── sfx_alias_map.json                  ← Phase 1 product
│       ├── sfx_buckets.json                    ← Phase 1 + Phase 2 product
│       ├── normalize_report.md                 ← human review (low-conf)
│       ├── generation_report.md                ← Phase 2 outcome / cost / failures
│       └── _collected_contexts.json            ← debug, gitignored
│
├── dramatizer/
│   ├── raw_audio/no-rules-in-bad-ideas/
│   │   ├── 01_theme.mp3 ... 05_daily.mp3       (existing music)
│   │   └── sfx/                                ← NEW subdirectory
│   │       ├── doorbell.mp3
│   │       ├── door_knock.mp3
│   │       └── ... (28 files post Phase 2)
│   ├── configs/no-rules-in-bad-ideas.yaml
│   │   ├── music: ...                          (existing)
│   │   └── sfx: ...                            ← NEW section
│   └── pipeline/
│       ├── sfx_config.py                       ← NEW: parse yaml sfx:
│       ├── stage_sfx.py                        ← NEW: hardlink mp3
│       └── sfx_mapping.py                      ← NEW: build flat {name: url}
│
└── docs/superpowers/specs/
    └── 2026-05-12-sfx-pipeline-design.md       ← THIS DOC
```

### Subcommand entry points

```bash
# Phase 1 — scan + LLM cluster (~$0.01)
python -m skills.sfx-normalizer no-rules-in-bad-ideas normalize
python -m skills.sfx-normalizer no-rules-in-bad-ideas normalize --force      # rerun all
python -m skills.sfx-normalizer no-rules-in-bad-ideas normalize --dry-run    # counts only

# Phase 2 — ElevenLabs generation (~$1.40 first pass)
python -m skills.sfx-normalizer no-rules-in-bad-ideas generate
python -m skills.sfx-normalizer no-rules-in-bad-ideas generate --only doorbell,phone_buzz
python -m skills.sfx-normalizer no-rules-in-bad-ideas generate --skip-existing    # default true
python -m skills.sfx-normalizer no-rules-in-bad-ideas generate --dry-run          # estimate cost only
python -m skills.sfx-normalizer no-rules-in-bad-ideas generate --cost-cap 5.0
```

---

## Data contracts

### `sfx_alias_map.json` — Phase 1 product

```json
{
  "doorbell_chime_clean": {
    "bucket_id": "doorbell",
    "confidence": "high",
    "reason": "standard clean doorbell, merges with low/two_chimes variants"
  },
  "phone_buzz_short": {
    "bucket_id": "phone_buzz",
    "confidence": "high",
    "reason": "duration variant of vibration buzz, same audio source"
  },
  "speakerphone_static": {
    "bucket_id": "speakerphone_static",
    "confidence": "high",
    "reason": "unique audio event"
  }
}
```

- `bucket_id` ∈ keys of `sfx_buckets.json["buckets"]`.
- `confidence` ∈ {`high`, `med`, `low`}. Default `normalize` rerun skips `high`; `--force` reclassifies all.

### `sfx_buckets.json` — Phase 1 + 2 product

```json
{
  "schema_version": 1,
  "buckets": {
    "doorbell": {
      "description": "Brief warm electronic doorbell chime, single press, residential American home.",
      "members": ["doorbell_chime_clean", "doorbell_low", "doorbell_two_chimes"],
      "duration_s": null,
      "prompt_influence": null,
      "prompt_override_suffix": null,
      "generated": {
        "file": "doorbell.mp3",
        "provider": "elevenlabs",
        "model": "eleven_text_to_sound_v2",
        "generated_at": "2026-05-12T15:32:01Z",
        "cost_usd": 0.052,
        "iteration": 1
      }
    },
    "voicemail_playback": {
      "description": "Voicemail playback of a low male voice, calm but tense.",
      "members": ["voicemail_low_charged"],
      "duration_s": 4.0,
      "prompt_influence": 0.4,
      "prompt_override_suffix": "Low male voice, calm but tense, voicemail recording.",
      "generated": null
    }
  }
}
```

- `generated: null` = pending. Phase 2 default skips non-null buckets; `--only` forces rerun.
- `iteration` increments per rerun; `file` stays stable (overwrite in place).
- `prompt_override_suffix` lets two outlier buckets (`acoustic_guitar_soft`, `voicemail_playback`) opt out of the default "no-voice / no-music" anchor suffix. Phase 1 LLM is prompted to set this field when it detects a bucket that genuinely needs voice or melody.
- `duration_s` / `prompt_influence` are per-bucket overrides; `null` falls back to yaml defaults.

### `dramatizer/configs/<slug>.yaml` — `sfx:` section

```yaml
sfx:
  source_dir: ../raw_audio/no-rules-in-bad-ideas/sfx/
  generator:
    provider: elevenlabs
    model: eleven_text_to_sound_v2
    default_duration_s: null            # null = ElevenLabs auto-decide
    default_prompt_influence: 0.3
    output_format: mp3_44100_128
    max_retries: 3
    cost_cap_usd: 5.0                   # abort + ask if estimate exceeds
```

No predefined palette: SFX buckets are LLM-discovered (Phase 1), not human-curated. The yaml carries only generator runtime settings.

### `normalize_report.md` shape

```markdown
# SFX Normalize Report — no-rules-in-bad-ideas
Generated: 2026-05-12 15:30 UTC

## Stats
- 43 unique @sfx names → 28 buckets (1.5:1)
- 53 total occurrences across 60 episode scripts
- Confidence: 38 high / 4 med / 1 low

## Bucket distribution
| Bucket | # names | Members |
|---|---:|---|
| window_tap_glass | 5 | knock_glass_three_taps, tap_glass_three, ... |
| phone_buzz | 4 | phone_buzz, phone_buzz_low, phone_buzz_short, phone_buzz_soft |
| ...

## ⚠ Low-confidence — please review
- `voicemail_low_charged` → `voicemail_playback`
  - reason: ambiguous, could fit phone_ring or voice_muffled
  - context: ep5 BEAT-2, Selena listens to a saved voicemail
  - **action**: confirm bucket OR rewrite @sfx name in script
```

### `generation_report.md` shape

```markdown
# SFX Generation Report — no-rules-in-bad-ideas
Phase 2 run: 2026-05-12 16:00 UTC

## Summary
- 28 buckets requested, 27 succeeded, 1 failed
- Total cost: $1.42 (ElevenLabs)
- Avg duration: 4.2s

## Per-bucket
| Bucket | Status | Iter | Duration | Cost | Notes |
|---|---|---:|---:|---:|---|
| doorbell | ✓ ok | 1 | 3.1s | $0.04 | |
| voicemail_playback | ✗ failed | 3 | — | $0.15 | API: content moderation rejected |
| ...

## Failed — manual intervention needed
- `voicemail_playback`: ElevenLabs rejected "low charged male voice" 3x.
  Suggest: rewrite description without "voice" keyword OR procure manually.
```

---

## Generator (ElevenLabs) details

### API call shape

```
POST https://api.elevenlabs.io/v1/sound-generation
Headers:
  xi-api-key: <ELEVENLABS_API_KEY>
  Content-Type: application/json
  Accept: audio/mpeg
Body:
{
  "text":              "<description + suffix>",   // < ~450 chars
  "duration_seconds":  3.1 | null,                  // null = auto
  "prompt_influence":  0.3,
  "model_id":          "eleven_text_to_sound_v2",
  "output_format":     "mp3_44100_128"
}
Response: audio/mpeg byte stream → write to raw_audio/<slug>/sfx/<bucket_id>.mp3
```

### Prompt assembly

```python
DEFAULT_SUFFIX = (
    " No human voice, no speech, no words. "
    "No music, no melody. "
    "Realistic foley-style sound effect, cinematic mix."
)

def build_prompt(description, override_suffix=None):
    base = description.strip().rstrip('.')
    suffix = override_suffix if override_suffix else DEFAULT_SUFFIX
    return f"{base}. {suffix.strip()}"
```

Rationale: ElevenLabs SFX has a known tendency to (a) insert sung vowels when description mentions ambient mood words, and (b) turn "soft / gentle" into short melodic loops. The default suffix anchors output to foley. The two outlier buckets that legitimately need voice or melody set `prompt_override_suffix` (Phase 1 LLM auto-detects and writes the field).

### Failure handling

| Failure | Response |
|---|---|
| Network / 5xx | exponential-backoff retry ≤ `max_retries` |
| 4xx moderation | no retry, mark `failed_moderation`, surface in report |
| 401 / quota exhausted | abort run, prompt for credit top-up |
| Disk IO error | one retry, then abort run |
| Silent / sub-1KB response | retry ≤ 3 times, then mark `failed_silent` |

Every failure writes a row to `generation_report.md`. Idempotent rerun skips `ok` status and retries `failed_*`.

### Cost cap

Before any API call, the generator computes `estimated_total_cost = sum_per_bucket(estimate(prompt_len, duration))`. If this exceeds `cost_cap_usd`, the run aborts with an explicit summary and asks the user to raise the cap explicitly with `--cost-cap`. This protects against LLM-generated runaway descriptions (e.g., a 2000-char bucket description that would price 40x normal).

### Env vars

| Variable | Required | Purpose |
|---|---|---|
| `ELEVENLABS_API_KEY` | yes (Phase 2) | API auth |
| `ELEVENLABS_BASE_URL` | no | override for staging / proxy |
| `SFX_GENERATOR_DRY_RUN=1` | no | force dry-run regardless of CLI flag (CI safety) |

---

## Dramatizer integration

### Build flow extension

```
[1/6]    stage PNG assets             (existing)
[1.5/6]  stage music mp3              (existing)
[1.6/6]  stage sfx mp3                ← NEW
[2/6]    build mapping.json (PNG)     (existing)
[2.1/6]  merge music mapping          (existing)
[2.2/6]  merge sfx mapping            ← NEW
[2.5/6]  music postprocess inject     (existing; does NOT touch @sfx)
[3-6]    compile_ls / episodes       (existing; consumes augmented mapping.json)
```

### `stage_sfx.py`

Mirrors `stage_music.py` exactly. Hardlinks every `.mp3` from `raw_audio/<slug>/sfx/` into `dramatizer/build/<slug>/assets/<slug>/sfx/`. Idempotent. Returns the count. Raises if `source_dir` is missing.

### `sfx_mapping.py`

```python
def build_sfx_mapping(
    *, alias_map, buckets, slug, public_host,
) -> dict[str, str]:
    base = f"{public_host.rstrip('/')}/assets/{slug}/sfx"
    out = {}
    for name, info in alias_map.items():
        bucket_id = info["bucket_id"]
        bucket = buckets.get(bucket_id)
        if not bucket or not bucket.get("generated"):
            raise SfxMappingError(
                f"@sfx play {name!r} → bucket {bucket_id!r} not generated. "
                f"run: python -m skills.sfx-normalizer {slug} generate"
            )
        out[name] = f"{base}/{bucket['generated']['file']}"
    return out
```

Output is a flat `{semantic_name: full_url}` dict, merged into `mapping.json` via `existing.update(sfx_mapping)`. The Go engine's existing `@sfx play X` consumer reads `mapping.json[X]` exactly as it does for sprites and music.

### Hard-fail contract

```python
if sfx_cfg:
    if alias_map_path.missing:  raise SystemExit("...run: skills.sfx-normalizer normalize")
    if buckets_path.missing:    raise SystemExit("...run: skills.sfx-normalizer normalize")
    n_sfx = stage_sfx(...)
    if n_sfx == 0:              raise SystemExit("...run: skills.sfx-normalizer generate")
    # build_sfx_mapping itself raises if any bucket has generated==null
```

No silent fallbacks. If `sfx:` is configured, every prerequisite must be present. If `sfx:` is absent, the entire SFX pipeline is skipped — books without SFX are zero-impact.

### LS / Go engine changes

**None.** `@sfx play <name>` syntax already exists in LS spec. The Go engine already consumes `mapping.json[<name>]` for any reference. This pipeline operates purely at compile time as a URL substitution.

### Interaction with `music_postprocess`

`music_postprocess.py`'s regex matches `^\s*@music\s+...`, which does not match `@sfx`. SFX is therefore not subject to crossfade injection. The two stages are independent.

---

## Testing strategy

### Skill tests (`skills/sfx-normalizer/tests/`)

| File | Coverage | Count |
|---|---|---:|
| `test_context_collector.py` | scan `@sfx play`, skip `.zh.md`, capture bg anchor + line + before/after context | 3-4 |
| `test_llm_clusterer.py` | prompt build, JSON parse + retry, bad-response fallback, `prompt_override_suffix` triggering, incremental skip of high-conf | 5-6 |
| `test_elevenlabs_generator.py` | API call shape, write mp3, network retry, moderation no-retry, silent detection, cost accumulation + cap abort, `--only` filter, idempotent skip-existing | 6-8 |
| `test_orchestrator.py` | end-to-end normalize (fixture scripts + fake LLM → product schema), end-to-end generate (fixture buckets + mocked API → mp3 + buckets.json write-back) | 4-5 |
| `tests/fixtures/` | 3-5 mini `.md` scripts + mock LLM/API responses | — |

**Total: ~20-25 tests.**

### Dramatizer tests (`dramatizer/tests/`)

| File | Coverage | Count |
|---|---|---:|
| `test_sfx_config.py` | yaml parse, missing-field raise, None when section absent | 3 |
| `test_stage_sfx.py` | hardlink path, empty-dir raise, idempotent rerun | 3 |
| `test_sfx_mapping.py` | flat-dict shape, missing-`generated` raise, URL host/prefix, empty alias_map | 4 |
| extension to `test_build_cli.py` | "sfx: present, alias_map missing" / "buckets present, mp3 missing" / "no sfx: section" / "happy path end-to-end" | 4 |

**Total: ~14 tests.**

### Test principles

1. **Zero real API calls.** Both LLM and ElevenLabs are injected as `Callable`s; tests substitute fakes that return fixed JSON / silent-byte mp3s.
2. **Silent-byte fixtures.** mp3 fixtures are `b'\x00' * N` or ffmpeg-generated silence. No real audio committed.
3. **CI guard.** A pytest autouse fixture sets `SFX_GENERATOR_DRY_RUN=1` to backstop any test that forgets to inject.
4. **End-to-end smoke** in dramatizer: a fixture book with a small `sfx:` section runs the full `dramatizer.build`, asserts `mapping.json` contains the sfx entries and the staged dir holds the expected mp3s.
5. **Coverage target.** 80%+, matching music-normalizer. Emphasis on error paths (moderation, cost cap, missing-product build fail).

---

## Rollout

1. Implement Phase 1 + tests. Run normalize end-to-end on no-rules-in-bad-ideas. Spot-check `normalize_report.md` low/med confidence entries.
2. Implement dramatizer changes + tests. Run `dramatizer.build` and assert `mapping.json` lacks SFX entries because `generated: null` → expected SystemExit until Phase 2 completes. Adjust user onboarding wording in the SystemExit message.
3. Implement Phase 2 generator + tests. User registers ElevenLabs Starter ($5). Run generate; review the 28 mp3s aurally; iterate via `--only`.
4. Once all 28 buckets land, rerun `dramatizer.build`. Verify a sample compiled episode contains the SFX URLs and a smoke playback in the LS engine plays the expected sound at the expected beat.
5. Wiki-ingest the final design (this doc) into `mob-wiki` under `wiki/concepts/sfx-pipeline.md`.

## Open questions / deferred

- **Loudness normalization.** ElevenLabs outputs vary in loudness. If two adjacent SFX in a scene differ by >6dB it will feel uneven. Deferred: if review flags this, add a post-gen `ffmpeg-normalize` step in Phase 2.
- **SFX deduplication across books.** A future second book might rebuild many of the same buckets (doorbell, knock, phone_buzz). Out of scope here; could be a cross-book bucket library later.
- **Per-occurrence variants.** Right now `doorbell_two_chimes` and `doorbell_chime_clean` play the same mp3. If a scene needs the two-chimes variant to actually have two chimes, the bucket can be split manually by editing `sfx_buckets.json` and rerunning generate `--only`. Phase 1 LLM is told to keep duration-variant clusters together by default.
- **LS engine volume control.** SFX volume relative to BGM is engine-side; out of pipeline scope.

## Onboarding for a second book

```
1. Add a sfx: section to dramatizer/configs/<slug2>.yaml (copy from no-rules-in-bad-ideas.yaml)
2. python -m skills.sfx-normalizer <slug2> normalize
3. Review lunascripts/<slug2>/05.5c-sfx-normalizer/normalize_report.md
4. python -m skills.sfx-normalizer <slug2> generate
5. Review lunascripts/<slug2>/05.5c-sfx-normalizer/generation_report.md and any failed buckets
6. python -m dramatizer.build <slug2>
```

Zero code changes. Same model as music-normalizer.
