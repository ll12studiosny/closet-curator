import os
import json
import base64
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB

CLAUDE_MODEL = "claude-sonnet-4-5"

_client = None


def client():
    global _client
    if _client is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
        _client = Anthropic(api_key=key)
    return _client


# ---------- Pages ----------

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/onboarding")
def onboarding():
    return render_template("onboarding.html")


@app.route("/closet")
def closet():
    return render_template("closet.html")


@app.route("/generator")
def generator():
    return render_template("generator.html")


@app.route("/saved")
def saved():
    return render_template("saved.html")


@app.route("/profile")
def profile():
    return render_template("profile.html")


@app.route("/wishlist")
def wishlist():
    return render_template("wishlist.html")


# ---------- API ----------

@app.post("/api/categorize")
def api_categorize():
    """Accept an uploaded image, ask Claude to categorize the clothing."""
    data = request.get_json(silent=True) or {}
    image_b64 = data.get("image")
    media_type = data.get("media_type", "image/jpeg")
    if not image_b64:
        return jsonify({"error": "missing image"}), 400

    # Strip data URL prefix if present
    if image_b64.startswith("data:"):
        try:
            header, image_b64 = image_b64.split(",", 1)
            if "image/png" in header:
                media_type = "image/png"
            elif "image/webp" in header:
                media_type = "image/webp"
            else:
                media_type = "image/jpeg"
        except ValueError:
            pass

    system = (
        "You categorize a single clothing item from a photo. "
        "Return STRICT JSON only, no prose. Schema: "
        '{"name": string, "type": one of [top, bottom, outerwear, shoes, accessory, dress, full_body], '
        '"subtype": string, "primary_color": string, "secondary_color": string|null, '
        '"pattern": string, "fit": one of [slim, regular, relaxed, oversized, tailored], '
        '"style_tags": string[] from [streetwear, minimal, sporty, vintage, formal, casual, business, y2k, techwear, preppy, bohemian], '
        '"warmth": integer 1-5, "season": string[] from [spring, summer, fall, winter], '
        '"formality": integer 1-5}'
    )

    try:
        msg = client().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=600,
            system=system,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                    {"type": "text", "text": "Categorize this clothing item. Return only the JSON object."},
                ],
            }],
        )
        text = msg.content[0].text.strip()
        # Strip code fences if Claude included them
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        result = json.loads(text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/generate")
def api_generate():
    """Generate outfit combinations from the user's closet."""
    data = request.get_json(silent=True) or {}
    closet_items = data.get("closet", [])
    preferences = data.get("preferences", {})
    event = data.get("event", "casual")
    weather = data.get("weather", {})
    feedback = data.get("feedback", {"liked": [], "disliked": []})
    n = int(data.get("n", 3))

    if not closet_items:
        return jsonify({"error": "Closet is empty. Add items first."}), 400

    system = (
        "You are a world-class personal stylist. You build outfits using ONLY the items "
        "the user owns. You respect their style preferences, body proportions, and fit "
        "preferences. You follow real fashion principles: silhouette balance, color harmony, "
        "proportion, layering, formality matching the occasion, and weather appropriateness. "
        "You never invent items not in the closet. You learn from the user's liked/disliked history. "
        "Return STRICT JSON only, no prose."
    )

    schema = (
        '{"outfits": [{"id": string, "name": string, "item_ids": string[], '
        '"why_it_works": string (max 240 chars, confident and specific), '
        '"vibe_tags": string[]}], "missing": string[] (key wardrobe gaps, may be empty)}'
    )

    user_prompt = (
        f"Closet (use ONLY these item ids):\n{json.dumps(closet_items, ensure_ascii=False)}\n\n"
        f"User style preferences: {json.dumps(preferences.get('styles', []))}\n"
        f"Body profile: {json.dumps(preferences.get('body', {}))}\n"
        f"Fit preference: {preferences.get('fit_preference', 'regular')}\n"
        f"Event/occasion: {event}\n"
        f"Weather: {json.dumps(weather)}\n"
        f"Previously liked outfit ids: {json.dumps(feedback.get('liked', []))}\n"
        f"Previously disliked outfit ids: {json.dumps(feedback.get('disliked', []))}\n\n"
        f"Build {n} distinct outfit combinations. Each must be realistic, wearable, "
        f"and reflect the user's style. Use the item_id values exactly. "
        f"Return JSON matching this schema: {schema}"
    )

    try:
        msg = client().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        result = json.loads(text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/wishlist-outfit")
def api_wishlist_outfit():
    """Imagine a candidate item the user is considering buying, and build outfits
    combining it with items already in their closet. Helps decide if the purchase
    is worth it."""
    data = request.get_json(silent=True) or {}
    candidate = data.get("candidate", {})
    closet_items = data.get("closet", [])
    preferences = data.get("preferences", {})
    n = int(data.get("n", 3))

    if not candidate.get("description"):
        return jsonify({"error": "Describe the item you're considering."}), 400
    if not closet_items:
        return jsonify({"error": "Add items to your closet first."}), 400

    system = (
        "You are a personal stylist helping the user decide whether to buy a candidate "
        "clothing item. The candidate is described in text (and optionally an image). "
        "Build outfits combining the candidate with items already in the user's closet. "
        "Use ONLY the candidate plus items from their closet by id. Honor their style, "
        "fit, and body preferences. End with a clear verdict: WORTH IT or PASS, with a "
        "one-sentence reason. Return STRICT JSON only."
    )

    schema = (
        '{"candidate_summary": string (one line), '
        '"outfits": [{"id": string, "name": string, "candidate_in_outfit": true, '
        '"item_ids": string[] (ids from closet only, NOT including candidate), '
        '"why_it_works": string (max 240 chars), "vibe_tags": string[]}], '
        '"verdict": one of ["worth_it", "pass", "maybe"], '
        '"verdict_reason": string (max 200 chars), '
        '"versatility_score": integer 1-10}'
    )

    candidate_text = (
        f"Candidate item: {candidate.get('description', '')}\n"
        f"Color/details: {candidate.get('color', 'unspecified')}\n"
        f"Type: {candidate.get('type', 'unspecified')}\n"
    )

    user_content = []
    if candidate.get("image"):
        img = candidate["image"]
        media_type = "image/jpeg"
        if img.startswith("data:"):
            try:
                header, img = img.split(",", 1)
                if "image/png" in header: media_type = "image/png"
                elif "image/webp" in header: media_type = "image/webp"
            except ValueError:
                pass
        user_content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": img},
        })

    user_content.append({"type": "text", "text": (
        f"{candidate_text}\n"
        f"Closet (use these item ids only):\n{json.dumps(closet_items, ensure_ascii=False)}\n\n"
        f"User style preferences: {json.dumps(preferences.get('styles', []))}\n"
        f"Body profile: {json.dumps(preferences.get('body', {}))}\n"
        f"Fit preference: {preferences.get('fit_preference', 'regular')}\n\n"
        f"Build {n} distinct outfits that include the candidate. "
        f"Then judge whether buying the candidate is worth it given the user's wardrobe and taste. "
        f"Return JSON matching this schema: {schema}"
    )})

    try:
        msg = client().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        result = json.loads(text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/health")
def health():
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return jsonify({"ok": True, "claude_configured": has_key})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
