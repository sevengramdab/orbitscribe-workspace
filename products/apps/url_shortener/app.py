from flask import Flask, request, redirect, render_template_string, jsonify
import sqlite3
import string
import random
import os

# Requested features: analytics dashboard, custom domains, QR codes


app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "urls.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY,
            short_code TEXT UNIQUE,
            original_url TEXT,
            clicks INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>URL Shortener</title>
<style>
body { font-family: system-ui, -apple-system, sans-serif; max-width: 600px; margin: 40px auto; padding: 0 20px; }
input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
button { padding: 12px 24px; background: #007bff; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
button:hover { background: #0056b3; }
.result { background: #f8f9fa; padding: 16px; margin-top: 20px; border-radius: 8px; border: 1px solid #e9ecef; }
</style>
</head>
<body>
<h1>URL Shortener</h1>
<form method="post" action="/">
<input name="url" type="url" placeholder="https://example.com" required>
<button type="submit">Shorten</button>
</form>
{% if short_url %}
<div class="result">
  <p>Short URL: <a href="{{ short_url }}">{{ short_url }}</a></p>
</div>
{% endif %}
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    short_url = None
    if request.method == "POST":
        original = request.form.get("url", "").strip()
        if original:
            code = generate_code()
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            try:
                c.execute(
                    "INSERT INTO urls (short_code, original_url, created_at) VALUES (?, ?, datetime('now'))",
                    (code, original),
                )
                conn.commit()
                short_url = request.url_root + code
            except sqlite3.IntegrityError:
                code = generate_code()
                c.execute(
                    "INSERT INTO urls (short_code, original_url, created_at) VALUES (?, ?, datetime('now'))",
                    (code, original),
                )
                conn.commit()
                short_url = request.url_root + code
            finally:
                conn.close()
    return render_template_string(HTML, short_url=short_url)


@app.route("/<code>")
def redirect_url(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT original_url FROM urls WHERE short_code = ?", (code,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?", (code,))
        conn.commit()
    conn.close()
    if row:
        return redirect(row[0])
    return "Not found", 404


@app.route("/api/stats/<code>")
def stats(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT original_url, clicks, created_at FROM urls WHERE short_code = ?", (code,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"original_url": row[0], "clicks": row[1], "created_at": row[2]})
    return jsonify({"error": "Not found"}), 404


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))