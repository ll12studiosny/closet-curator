# Closet Curator

Your AI personal stylist — upload your wardrobe, get outfits built only from clothes you own, tuned to your style, body, the event, and the weather.

Built with Flask + Claude (Sonnet 4.5) for vision-based clothing tagging and outfit generation.

## Quick start

```bash
cd closet-curator

# Install deps (already done if you used the setup script)
./venv/bin/pip install flask anthropic python-dotenv

# Add your Anthropic API key
cp .env.example .env
# then edit .env and paste your key

# Run
./venv/bin/python app.py
```

Then open http://127.0.0.1:5050 in your browser. **For the mobile-app feel, open Chrome DevTools → toggle device toolbar (cmd+shift+M) → pick iPhone.**

## What's inside

| Page | What it does |
|------|---|
| `/` | Landing page — value prop + how it works |
| `/onboarding` | 3-step: pick & rank styles → body & fit → done |
| `/closet` | Cloud closet grid; tap + to upload, AI auto-tags type/color/fit/style |
| `/generator` | Pick event + weather → Claude builds outfits with reasoning |
| `/saved` | Bookmarked looks |
| `/profile` | Edit styles, body, fit; reset data |

## How the AI is used

- **`/api/categorize`** — sends an image to Claude Sonnet 4.5 (vision) and gets back structured JSON: `type`, `subtype`, colors, `fit`, `style_tags`, `warmth`, `season`, `formality`.
- **`/api/generate`** — sends your slim closet (no images), profile, event, weather, and feedback history. Claude returns 3 distinct outfits (referencing real `item_id`s only) plus a `why_it_works` explanation per look. Liked/disliked history is fed back so it improves over time.

## Storage

For this prototype, all user data (closet items, saved outfits, feedback) lives in `localStorage` on the client. No accounts, no backend DB. Your photos never leave your device except as base64 to Claude for one-shot categorization (not persisted server-side).

To productionize: add Supabase (auth + Postgres + Storage), keep the same API surface, swap `window.CC` for fetch calls.

## Stack

- **Flask** — minimal Python backend, two AI endpoints
- **Vanilla JS + custom CSS** — no build step, mobile-first dark UI
- **Claude Sonnet 4.5** — vision for categorization, reasoning for outfit generation
- **localStorage** — client-side persistence

## Roadmap

- [ ] Real auth + cloud sync
- [ ] Live weather API integration (OpenWeather)
- [ ] Outfit history calendar
- [ ] Shopping recommendations for "wardrobe gaps"
- [ ] Native mobile shells (Capacitor / React Native)
