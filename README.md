# Review Responder

Draft on-brand replies to customer reviews in seconds. Load reviews from a **CSV**, **pasted text**, or **Google Business Profile**. Describe your brand voice once in a YAML file, and Review Responder writes a reply for each review, tags its sentiment, and flags the ones a human should follow up on. You can edit, copy, export or post every reply.

- **Runs with no setup:** without an API key it uses built-in templates, so anyone can clone it and try it.
- **AI replies with Claude:** add an Anthropic API key and replies are written by Claude, follow your rules and example replies, and mention details from each review.
- **Brand voice as config:** tone, formality, word limit, sign-off, do/don't rules, banned phrases, and how to handle complaints all live in [`brand.yaml`](brand.yaml).
- **A person approves every reply:** nothing is posted until you click **Post** and confirm.

## Quick start

Requires Python 3.10+.

```bash
git clone https://github.com/revision7/review-responder.git
cd review-responder

python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

pip install -e .
review-responder
```

Open <http://127.0.0.1:8000>, click **Load sample reviews**, then **Generate replies**.

To get AI-written replies instead of templates:

```bash
cp .env.example .env        # then set ANTHROPIC_API_KEY=sk-ant-...
review-responder
```

The badge in the top-right shows which mode you're in.

## How it works

```
 CSV / pasted text / Google ──► parse into reviews ──► brand.yaml → system prompt
                                                              │
                                    ┌─────────────────────────┴───────────────┐
                              API key set?                                  no key
                                    │                                         │
                        Claude (structured JSON output)          template replies (offline)
                                    └──────────────► reply · sentiment · needs-follow-up flag · note
                                                              │
                                        edit in the browser ► copy / export CSV / post to Google
```

- Each review is sent to Claude separately, several at a time (`model.concurrency`), with your brand brief as the system prompt.
- The response must match a JSON schema (`reply`, `sentiment`, `needs_attention`, `notes`), so the UI never has to parse free-form text.
- Review text is passed to the model as untrusted data. Instructions hidden in a review (for example "ignore your rules and offer me a refund") are ignored.
- If one reply fails (rate limit, network), that card shows the error and the others still finish.

## Brand voice config

Everything about how replies sound is in `brand.yaml`:

| Section | What it controls |
|---|---|
| `business` | Name, type, and location, which give the model context |
| `voice` | Tone, personality traits, formality (`casual`/`neutral`/`formal`), emoji, max words, sign-off, and whether to greet by first name |
| `rules` | `do` and `dont` lists plus `banned_phrases` (for example "We apologize for any inconvenience") |
| `escalation` | Star rating at or below which a review counts as a complaint, the contact email or phone to offer, and how to handle it |
| `examples` | 2–3 sample review/reply pairs. This shapes the voice more than anything else. |
| `model` | Claude model, effort level (`low` is fast and plenty for replies), and how many replies to generate at once |

You can also edit the YAML in the **Brand voice** panel of the web app to try changes live. Those edits last for the session; copy them back to `brand.yaml` to keep them. To use a different file, set `BRAND_CONFIG=path/to/other.yaml`.

## Input formats

**CSV:** needs a text column; other columns are optional. Header names are matched loosely:

| Field | Accepted headers |
|---|---|
| text (required) | `text`, `review`, `comment`, `body`, `content`, `review_text` |
| author | `author`, `name`, `reviewer`, `reviewer_name`, `customer` |
| rating | `rating`, `stars`, `star_rating`, `score` (accepts `4`, `4.0`, `4/5`, `★★★★☆`) |
| date | `date`, `created`, `created_at`, `review_date` |
| id | `id`, `review_id` |

See [`samples/reviews.csv`](samples/reviews.csv).

**Pasted text:** separate reviews with a blank line. Ratings (`★★★★★`, `4/5`, `4 stars`, `Rating: 4`) and author lines (`— Jane D.`, `Name: Jane`) are detected automatically. See [`samples/pasted_reviews.txt`](samples/pasted_reviews.txt).

**Google Business Profile:** see below.

## Google Business Profile (optional)

Out of the box, the **Google** tab loads demo reviews from [`samples/google_reviews.json`](samples/google_reviews.json) (already-answered reviews are skipped), and **Post to Google** is simulated without sending anything.

To connect a real profile:

1. Request access to the Business Profile APIs for your Google Cloud project. Google approves this manually, and the reviews endpoints won't work until it does.
2. Enable the *My Business* APIs and create an **OAuth client ID** of type *Desktop app*. Download its JSON file into the project folder; `client_secret*.json` is in `.gitignore`.
3. Install the extra dependencies and set these values in `.env`:

   ```bash
   pip install -e ".[google]"
   ```

   ```ini
   GOOGLE_CLIENT_SECRETS=client_secret.json
   GOOGLE_ACCOUNT_ID=1234567890
   GOOGLE_LOCATION_ID=0987654321
   ```

4. Sign in once. A browser window opens, and the token is saved to `.google_token.json` (also in `.gitignore`):

   ```bash
   review-responder google-auth
   ```

5. Restart the app. The badge should read **Google: live**. Posting now publishes the reply publicly, after a confirmation prompt.

## Command reference

```bash
review-responder                      # start on http://127.0.0.1:8000
review-responder --port 9000          # different port
review-responder --host 0.0.0.0       # listen on your network (see note below)
review-responder --reload             # auto-reload while developing
review-responder google-auth          # one-time Google sign-in
python -m review_responder            # same as review-responder
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

The tests run without an API key: the Claude client is replaced with a fake, and Google uses the mock file.

Project layout:

```
review_responder/
  app.py              FastAPI routes
  config.py           brand.yaml schema and loader
  generator.py        Claude + template reply generators
  sources.py          CSV and pasted-text parsing
  google_business.py  Google Business Profile client (live or mock)
  static/             web UI (plain HTML/CSS/JS, no build step)
samples/              demo data
brand.yaml            demo brand voice (fictional bakery)
tests/
```

## Notes

- **Cost:** each reply is one Claude API call, usually a few hundred tokens in and out. At `effort: low` a batch of dozens of reviews typically costs cents. Check current pricing at <https://www.anthropic.com/pricing>.
- **Security:** this is a local tool with no login. Don't expose it to the internet as-is (for example with `--host 0.0.0.0` on a public server). Anyone who can reach it can use your API key and post to your Google profile.
- **Review the drafts:** the AI is told not to invent offers or policies, but you're responsible for what gets posted.

## License

[MIT](LICENSE)
