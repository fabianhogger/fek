# fek-daily-tweet

Reads the day's Εφημερίδα της Κυβερνήσεως publications, picks the most newsworthy
one, summarises it with OpenAI, and posts it to X — once a day, on a schedule.

Replaces the 2024 scripts in the parent directory, whose data source
(`www.et.gr/api/DownloadFeksApi`) now returns 301.

---

## How it works

```
EventBridge Scheduler  (21:00 Europe/Athens, Mon-Fri)
        ↓
   list the day's publications        POST /searchbydate      → issue numbers + page counts
        ↓
   rank candidates                    select.py               → Τεύχος Α by size, else Τεύχος Β
        ↓
   already posted?                    DynamoDB                → stop before spending anything
        ↓
   download + parse the PDF           fek_doc.py              → law name, table of contents, sections
        ↓
   STAGE 1  triage the contents       OpenAI                  → is this news? which articles?
        ↓
   STAGE 2  extract facts             OpenAI                  → structured JSON provisions
        ↓
   STAGE 3  compose                   compose.py              → 1 tweet or a thread, ≤280 chars
        ↓
   post + record                      X API v2 + DynamoDB
```

**The model never sees the whole document.** The largest law observed, `Ν. 5324/2026`,
is 112 pages and 454,344 characters. Stage 1 reads only its table of contents
(16,792 characters) and names the handful of articles worth reading; stage 2 reads
only those. A run costs roughly 15k tokens.

### Data source

`search.et.gr/el/daily-publications` is a React SPA — its HTML has nothing in it.
These are the endpoints behind it. Neither needs authentication.

| | |
|---|---|
| Listing | `POST https://searchetv99.azurewebsites.net/api/searchbydate` with `{"datePublished":"YYYY-MM-DD"}` |
| PDF | `https://ia37rg02wpsa01.blob.core.windows.net/fek/{issue:02d}/{year}/{year}{issue:02d}{number:05d}.pdf` |

The listing's `data` field is a JSON-encoded string inside the JSON body — it needs
decoding twice. It carries **no document title**; titles exist only inside the PDFs.

### What publishes, and when

Surveyed over two weeks (774 rows):

| | count | pages: median / p90 / max |
|---|---|---|
| Τεύχος Α (νόμοι, π.δ.) | 12 | 3 / 80 / 112 |
| Τεύχος Β (υπ. αποφάσεις) | 393 | 6 / 28 / 888 |

Weekends return zero rows. Τεύχος Α publishes only ~2–3×/week, hence the fallback to
Τεύχος Β. The listing fills through the day — one weekday held 4 rows at 13:00 and 90
by evening — which is why the schedule is at 21:00 rather than the morning.

---

## Tuning what counts as news

Everything editorial lives in [`src/prompts/`](src/prompts/) as plain markdown. Changing
the bot's focus does not require touching Python.

- **[`editorial_policy.md`](src/prompts/editorial_policy.md)** — the main dial. Injected
  verbatim into both LLM stages. Lists what ranks high (money, deadlines, obligations,
  penalties), what ranks low (individual appointments, internal reorganisations), and
  the hard exclusions.
- `triage.md` — the 0–10 newsworthiness scale and how to choose articles.
- `extract.md` — the shape of the extracted facts.
- `compose.md` — only used when `COMPOSE_MODE=llm`.

After editing, re-run `local_run.py` on a couple of past dates and check that the
picks move the way you expected.

### Privacy

Gazette issues routinely name private individuals — `Β 5013/2026` names two people
fined in smuggling cases. Publishing those names would be a real harm, so it is
blocked three ways:

1. The editorial policy forbids it (prompt-level).
2. Stage 2 returns `contains_personal_names`, which aborts the run.
3. `compose.py` extracts the actual names from the document's own `(επ)`/`(ον)`
   markers and refuses to post any text containing one. Names are taken from the
   source rather than guessed from capitalisation, so ministry names do not trip it.

Rule 3 is the one that holds if the model misbehaves. It is covered by tests.

---

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/fetch_fixtures.py    # test PDFs, not committed (10MB)
.venv/bin/python -m pytest tests/ -q
```

### Running locally

No API key needed for the parsing stages:

```bash
# what published that day, and what the parser makes of it
.venv/bin/python scripts/local_run.py --date 2026-07-31 --stage parse --explain

# the whole pipeline with a stubbed model — verifies wiring, not quality
.venv/bin/python scripts/local_run.py --date 2026-07-31 --fake-llm
```

With `OPENAI_API_KEY` exported, for real output:

```bash
export OPENAI_API_KEY=sk-...
.venv/bin/python scripts/local_run.py --date 2026-07-31 --explain
```

`--stage {list,parse,triage,extract,compose}` stops early. `--label 'Β 5013/2026'`
forces a specific issue. `--post` actually publishes (otherwise nothing is sent).

---

## Deploying

**1. Store the credentials.** They are read from SSM at cold start, never from the
template.

```bash
aws ssm put-parameter --type SecureString --name /fek-daily-tweet/openai_api_key            --value '...'
aws ssm put-parameter --type SecureString --name /fek-daily-tweet/twitter/consumer_key      --value '...'
aws ssm put-parameter --type SecureString --name /fek-daily-tweet/twitter/consumer_secret   --value '...'
aws ssm put-parameter --type SecureString --name /fek-daily-tweet/twitter/access_token      --value '...'
aws ssm put-parameter --type SecureString --name /fek-daily-tweet/twitter/access_token_secret --value '...'
```

> The Twitter keys committed to this repo's history in 2024 are **compromised** —
> `git show b599fe9^:secret_params.json` still returns them, on a public GitHub repo.
> Rotate before use.

**2. Deploy, with posting off.**

```bash
sam build --use-container
sam deploy --guided          # DryRun=true
```

**3. Check what it would have posted.**

```bash
aws lambda invoke --function-name fek-daily-tweet \
  --payload '{"date":"2026-07-31"}' --cli-binary-format raw-in-base64-out /dev/stdout
```

**4. Go live.**

```bash
sam deploy --parameter-overrides DryRun=false
```

### Configuration

| Env var | Default | |
|---|---|---|
| `DRY_RUN` | `true` | Compose and log, never post. |
| `OPENAI_MODEL` | `gpt-4o-mini` | |
| `MIN_NEWSWORTHINESS` | `4` | Below this, skip to the next candidate. |
| `TRIAGE_TOP_K` | `4` | Articles read in full per document. |
| `THREAD_MODE` | `auto` | `single`, `auto`, or `always`. |
| `THREAD_MAX_TWEETS` | `4` | |
| `THREAD_MIN_IMPORTANCE` | `6` | `auto` threads when ≥2 provisions clear this. |
| `MAX_CANDIDATES` | `8` | Documents tried per day before giving up. |
| `MAX_EXTRACT_CHARS` | `40000` | Stage 2 input budget. |
| `COMPOSE_MODE` | `template` | `llm` routes wording through `compose.md`. |
| `INCLUDE_LINK` | `true` | Appends the PDF URL (costs 24 characters). |

Operational state is a DynamoDB table keyed on `fek_id`, with a 90-day TTL. It stores
the extracted `facts_json`, so you can review what the pipeline decided when tuning
the editorial policy.

---

## Notes on the source PDFs

Three artefacts the parser handles, each found in a real issue:

- **Line-break hyphenation** — `Στρατη-\nγική`. Rejoined only when the following
  character is lowercase, so `Κληρονομιάς - Στρατηγική` survives intact.
- **Kerning spaces inside words** — `ΟΡΓ ΑΝΙΣΜΟΣ`, `Γ ραμματείας`. Not repaired
  (that needs a lexicon and risks merging genuinely separate words); instead every
  structural anchor is matched whitespace-insensitively.
- **Latin/Greek confusables** — `Ν. 5324/2026` spells its own heading `NOMOΣ` with a
  Latin N and O. Anchors are matched against a transliterated copy, so the largest
  laws are not silently missed.

And one that cannot be handled: **undecodable font encodings**. The 76-page annex of
`Π.Υ.Σ. 22/2026` extracts as `D\}ZR^l}N]\aRXRg}` under pypdf *and* poppler — the
embedded subset font carries no ToUnicode map. `fek_doc.is_garbled()` detects this and
drops the affected sections; if a whole document is unreadable it is skipped in favour
of the next candidate.

Document shapes the parser recognises: laws and presidential decrees with a
`ΠΙΝΑΚΑΣ ΠΕΡΙΕΧΟΜΕΝΩΝ`, short decrees without one, cabinet acts (`Π.Υ.Σ.`) with no
articles at all, and Τεύχος Β issues whose acts are delimited by bare `(n)` markers.
