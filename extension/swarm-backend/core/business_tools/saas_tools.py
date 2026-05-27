"""
SaaS Micro-App Business Tools

Provides tooling for researching, generating, monetizing, packaging, and retiring
micro-SaaS applications. All tools are registered with the global
BusinessToolRegistry via the @business_tool decorator.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core import config
from core.business_tools.registry import business_tool
from core.business_tools.vault import vault


# ── Curated Idea Catalog ───────────────────────────────────────────────────

_IDEA_CATALOG: List[Dict[str, Any]] = [
    {
        "title": "URL Shortener with Analytics",
        "description": "Shorten links and track clicks, referrers, and geo-data.",
        "niche": "marketing",
        "difficulty": "easy",
        "monetization": "freemium",
        "estimated_mrr": 500,
    },
    {
        "title": "QR Code Designer",
        "description": "Generate branded QR codes with logos and colors.",
        "niche": "marketing",
        "difficulty": "easy",
        "monetization": "one_time",
        "estimated_mrr": 300,
    },
    {
        "title": "Secure Password Generator",
        "description": "Browser-based password generator with entropy analysis.",
        "niche": "security",
        "difficulty": "easy",
        "monetization": "donation",
        "estimated_mrr": 100,
    },
    {
        "title": "Meme Maker Pro",
        "description": "Upload images and overlay text to create shareable memes.",
        "niche": "social_media",
        "difficulty": "medium",
        "monetization": "freemium",
        "estimated_mrr": 400,
    },
    {
        "title": "JSON Formatter & Validator",
        "description": "Format, validate, and transform JSON data in the browser.",
        "niche": "developer_tools",
        "difficulty": "easy",
        "monetization": "saas",
        "estimated_mrr": 200,
    },
    {
        "title": "Unit Converter Suite",
        "description": "Convert between 100+ units across length, weight, temp, and volume.",
        "niche": "productivity",
        "difficulty": "easy",
        "monetization": "ads",
        "estimated_mrr": 150,
    },
    {
        "title": "Micro Todo with Teams",
        "description": "Minimalist todo lists with team sharing and due dates.",
        "niche": "productivity",
        "difficulty": "medium",
        "monetization": "saas",
        "estimated_mrr": 600,
    },
    {
        "title": "Markdown to HTML Converter",
        "description": "Live markdown editor with export to HTML/PDF.",
        "niche": "developer_tools",
        "difficulty": "medium",
        "monetization": "freemium",
        "estimated_mrr": 350,
    },
    {
        "title": "Color Palette Generator",
        "description": "Generate harmonious color palettes from images or color rules.",
        "niche": "design",
        "difficulty": "easy",
        "monetization": "one_time",
        "estimated_mrr": 250,
    },
    {
        "title": "Habit Tracker",
        "description": "Simple daily habit tracker with streaks and insights.",
        "niche": "health",
        "difficulty": "medium",
        "monetization": "subscription",
        "estimated_mrr": 800,
    },
]


# ── Production App Templates ───────────────────────────────────────────────

_URL_SHORTENER_CODE = '''from flask import Flask, request, redirect, render_template_string, jsonify
import sqlite3
import string
import random
import os

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
'''

_QR_GENERATOR_CODE = '''from flask import Flask, request, render_template_string
import qrcode
import io
import base64
import os

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QR Code Generator</title>
<style>
body { font-family: system-ui, -apple-system, sans-serif; max-width: 600px; margin: 40px auto; padding: 0 20px; }
textarea { width: 100%; padding: 12px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
button { padding: 12px 24px; background: #28a745; color: #fff; border: none; border-radius: 6px; cursor: pointer; margin-top: 10px; }
button:hover { background: #218838; }
img { max-width: 100%; height: auto; margin-top: 20px; border: 1px solid #ddd; border-radius: 8px; }
</style>
</head>
<body>
<h1>QR Code Generator</h1>
<form method="post" action="/">
<textarea name="data" rows="4" placeholder="Enter text or URL" required></textarea>
<button type="submit">Generate QR</button>
</form>
{% if qr %}
<img src="data:image/png;base64,{{ qr }}" alt="QR Code">
{% endif %}
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    qr_b64 = None
    if request.method == "POST":
        data = request.form.get("data", "").strip()
        if data:
            img = qrcode.make(data)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            qr_b64 = base64.b64encode(buf.getvalue()).decode()
    return render_template_string(HTML, qr=qr_b64)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
'''

_PASSWORD_GENERATOR_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Secure Password Generator</title>
<style>
body { font-family: system-ui, -apple-system, sans-serif; max-width: 600px; margin: 40px auto; padding: 0 20px; background: #0d1117; color: #c9d1d9; }
h1 { color: #58a6ff; }
label { display: block; margin: 8px 0; }
input[type=range] { width: 100%; }
button { padding: 12px 24px; background: #238636; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; margin-top: 10px; }
button:hover { background: #2ea043; }
.password { font-size: 1.5rem; background: #161b22; padding: 16px; border-radius: 8px; word-break: break-all; margin: 20px 0; border: 1px solid #30363d; color: #3fb950; }
.options { background: #161b22; padding: 16px; border-radius: 8px; border: 1px solid #30363d; }
</style>
</head>
<body>
<h1>Secure Password Generator</h1>
<div class="options">
  <label>Length: <span id="lenVal">16</span></label>
  <input type="range" id="length" min="8" max="64" value="16" oninput="document.getElementById('lenVal').innerText=this.value">
  <label><input type="checkbox" id="upper" checked> Uppercase (A-Z)</label>
  <label><input type="checkbox" id="lower" checked> Lowercase (a-z)</label>
  <label><input type="checkbox" id="nums" checked> Numbers (0-9)</label>
  <label><input type="checkbox" id="syms" checked> Symbols (!@#$...)</label>
</div>
<button onclick="generate()">Generate Password</button>
<div class="password" id="out">Click generate...</div>
<button onclick="copy()">Copy to Clipboard</button>
<script>
function generate() {
  const len = +document.getElementById('length').value;
  let chars = '';
  if (document.getElementById('lower').checked) chars += 'abcdefghijklmnopqrstuvwxyz';
  if (document.getElementById('upper').checked) chars += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  if (document.getElementById('nums').checked) chars += '0123456789';
  if (document.getElementById('syms').checked) chars += '!@#$%^&*()_+-=[]{}|;:,.<>?';
  if (!chars) { alert('Select at least one character set'); return; }
  let pass = '';
  const arr = new Uint32Array(len);
  window.crypto.getRandomValues(arr);
  for (let i = 0; i < len; i++) pass += chars.charAt(arr[i] % chars.length);
  document.getElementById('out').innerText = pass;
}
function copy() {
  const text = document.getElementById('out').innerText;
  if (text === 'Click generate...') return;
  navigator.clipboard.writeText(text).then(() => alert('Copied!'));
}
</script>
</body>
</html>'''

_MEME_MAKER_CODE = '''from flask import Flask, request, render_template_string
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import os

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Meme Maker</title>
<style>
body { font-family: system-ui, -apple-system, sans-serif; max-width: 600px; margin: 40px auto; padding: 0 20px; }
input, textarea { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
button { padding: 12px 24px; background: #ff4500; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
button:hover { background: #e03e00; }
img { max-width: 100%; height: auto; margin-top: 20px; border: 1px solid #ddd; border-radius: 8px; }
</style>
</head>
<body>
<h1>Meme Maker</h1>
<form method="post" action="/" enctype="multipart/form-data">
<input type="file" name="image" accept="image/*" required>
<input name="top" placeholder="Top text">
<input name="bottom" placeholder="Bottom text">
<button type="submit">Create Meme</button>
</form>
{% if meme %}
<img src="data:image/png;base64,{{ meme }}" alt="Meme">
{% endif %}
</body>
</html>
"""


def add_text(img, top, bottom):
    draw = ImageDraw.Draw(img)
    width, height = img.size
    try:
        font = ImageFont.truetype("arial.ttf", int(height / 10))
    except Exception:
        font = ImageFont.load_default()
    for text, y_pos in [(top, 10), (bottom, height - int(height / 8))]:
        if not text:
            continue
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) / 2
        draw.text((x + 2, y_pos + 2), text, font=font, fill="black")
        draw.text((x, y_pos), text, font=font, fill="white")
    return img


@app.route("/", methods=["GET", "POST"])
def index():
    meme_b64 = None
    if request.method == "POST":
        file = request.files.get("image")
        top = request.form.get("top", "")
        bottom = request.form.get("bottom", "")
        if file:
            img = Image.open(file.stream).convert("RGBA")
            img = add_text(img, top, bottom)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            meme_b64 = base64.b64encode(buf.getvalue()).decode()
    return render_template_string(HTML, meme=meme_b64)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
'''

_JSON_FORMATTER_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JSON Formatter & Validator</title>
<style>
body { font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }
textarea { width: 100%; height: 200px; padding: 12px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-family: monospace; }
button { padding: 10px 20px; margin: 8px 4px 0 0; border: none; border-radius: 6px; cursor: pointer; }
.format { background: #007bff; color: #fff; }
.minify { background: #6c757d; color: #fff; }
.validate { background: #28a745; color: #fff; }
.result { background: #f8f9fa; padding: 16px; border-radius: 8px; border: 1px solid #e9ecef; margin-top: 16px; white-space: pre-wrap; font-family: monospace; }
.error { background: #f8d7da; color: #721c24; border-color: #f5c6cb; }
</style>
</head>
<body>
<h1>JSON Formatter & Validator</h1>
<textarea id="input" placeholder="Paste JSON here..."></textarea>
<div>
<button class="format" onclick="formatJson()">Format</button>
<button class="minify" onclick="minifyJson()">Minify</button>
<button class="validate" onclick="validateJson()">Validate</button>
</div>
<div id="output" class="result" style="display:none"></div>
<script>
function setOut(text, isError) {
  const el = document.getElementById('output');
  el.style.display = 'block';
  el.innerText = text;
  el.className = 'result' + (isError ? ' error' : '');
}
function formatJson() {
  try { const obj = JSON.parse(document.getElementById('input').value); setOut(JSON.stringify(obj, null, 2), false); }
  catch (e) { setOut('Invalid JSON: ' + e.message, true); }
}
function minifyJson() {
  try { const obj = JSON.parse(document.getElementById('input').value); setOut(JSON.stringify(obj), false); }
  catch (e) { setOut('Invalid JSON: ' + e.message, true); }
}
function validateJson() {
  try { JSON.parse(document.getElementById('input').value); setOut('Valid JSON!', false); }
  catch (e) { setOut('Invalid JSON: ' + e.message, true); }
}
</script>
</body>
</html>'''

_UNIT_CONVERTER_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unit Converter</title>
<style>
body { font-family: system-ui, -apple-system, sans-serif; max-width: 600px; margin: 40px auto; padding: 0 20px; }
select, input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
button { padding: 12px 24px; background: #007bff; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
.result { font-size: 1.25rem; margin-top: 16px; padding: 16px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef; }
</style>
</head>
<body>
<h1>Unit Converter</h1>
<label>Category</label>
<select id="category" onchange="updateUnits()">
<option value="length">Length</option>
<option value="weight">Weight</option>
<option value="temperature">Temperature</option>
<option value="volume">Volume</option>
</select>
<label>From</label>
<select id="from"></select>
<label>To</label>
<select id="to"></select>
<label>Value</label>
<input type="number" id="value" value="1">
<button onclick="convert()">Convert</button>
<div class="result" id="out"></div>
<script>
const units = {
  length: { m: 1, km: 1000, cm: 0.01, mm: 0.001, mi: 1609.34, yd: 0.9144, ft: 0.3048, in: 0.0254 },
  weight: { kg: 1, g: 0.001, mg: 0.000001, lb: 0.453592, oz: 0.0283495 },
  volume: { l: 1, ml: 0.001, gal: 3.78541, qt: 0.946353, c: 0.236588 },
  temperature: {}
};
function updateUnits() {
  const cat = document.getElementById('category').value;
  const fromSel = document.getElementById('from');
  const toSel = document.getElementById('to');
  fromSel.innerHTML = ''; toSel.innerHTML = '';
  if (cat === 'temperature') {
    ['Celsius', 'Fahrenheit', 'Kelvin'].forEach(u => {
      fromSel.add(new Option(u, u[0]));
      toSel.add(new Option(u, u[0]));
    });
  } else {
    Object.keys(units[cat]).forEach(u => {
      fromSel.add(new Option(u, u));
      toSel.add(new Option(u, u));
    });
  }
}
function convert() {
  const cat = document.getElementById('category').value;
  const from = document.getElementById('from').value;
  const to = document.getElementById('to').value;
  const val = parseFloat(document.getElementById('value').value);
  let res;
  if (cat === 'temperature') {
    let c;
    if (from === 'C') c = val;
    else if (from === 'F') c = (val - 32) * 5 / 9;
    else if (from === 'K') c = val - 273.15;
    if (to === 'C') res = c;
    else if (to === 'F') res = c * 9 / 5 + 32;
    else if (to === 'K') res = c + 273.15;
  } else {
    const base = val * units[cat][from];
    res = base / units[cat][to];
  }
  document.getElementById('out').innerText = val + ' ' + from + ' = ' + res.toLocaleString(undefined, { maximumFractionDigits: 6 }) + ' ' + to;
}
updateUnits();
</script>
</body>
</html>'''

_TODO_MICRO_CODE = '''from flask import Flask, request, render_template_string, jsonify, redirect
import sqlite3
import os

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "todo.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            title TEXT,
            done INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Micro Todo</title>
<style>
body { font-family: system-ui, -apple-system, sans-serif; max-width: 600px; margin: 40px auto; padding: 0 20px; }
input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
button { padding: 8px 16px; background: #007bff; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
button:hover { background: #0056b3; }
ul { list-style: none; padding: 0; }
li { background: #f8f9fa; padding: 12px; margin: 8px 0; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #e9ecef; }
.done { text-decoration: line-through; color: #6c757d; }
</style>
</head>
<body>
<h1>Micro Todo</h1>
<form method="post" action="/add">
<input name="title" placeholder="New task..." required>
<button type="submit">Add</button>
</form>
<ul>
{% for task in tasks %}
<li class="{{ 'done' if task.done else '' }}">
  <span>{{ task.title }}</span>
  <div>
    <a href="/toggle/{{ task.id }}"><button>{{ 'Undo' if task.done else 'Done' }}</button></a>
    <a href="/delete/{{ task.id }}"><button style="background:#dc3545">Delete</button></a>
  </div>
</li>
{% endfor %}
</ul>
</body>
</html>
"""


@app.route("/")
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, done FROM tasks ORDER BY id DESC")
    tasks = [{"id": r[0], "title": r[1], "done": bool(r[2])} for r in c.fetchall()]
    conn.close()
    return render_template_string(HTML, tasks=tasks)


@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title", "").strip()
    if title:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO tasks (title, created_at) VALUES (?, datetime('now'))", (title,))
        conn.commit()
        conn.close()
    return redirect("/")


@app.route("/toggle/<int:task_id>")
def toggle(task_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE tasks SET done = 1 - done WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/delete/<int:task_id>")
def delete(task_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/api/tasks")
def api_tasks():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, done, created_at FROM tasks ORDER BY id DESC")
    tasks = [{"id": r[0], "title": r[1], "done": bool(r[2]), "created_at": r[3]} for r in c.fetchall()]
    conn.close()
    return jsonify(tasks)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
'''

_APP_CODE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "url_shortener": {
        "tech_stack": "flask",
        "main_file": "app.py",
        "files": {
            "app.py": _URL_SHORTENER_CODE,
            "requirements.txt": "flask\n",
            "README.md": "# URL Shortener\n\nRun: `python app.py`\n",
        },
    },
    "qr_generator": {
        "tech_stack": "flask",
        "main_file": "app.py",
        "files": {
            "app.py": _QR_GENERATOR_CODE,
            "requirements.txt": "flask\nqrcode\npillow\n",
            "README.md": "# QR Code Generator\n\nRun: `python app.py`\n",
        },
    },
    "password_generator": {
        "tech_stack": "static",
        "main_file": "index.html",
        "files": {
            "index.html": _PASSWORD_GENERATOR_HTML,
            "README.md": "# Password Generator\n\nOpen `index.html` in a browser.\n",
        },
    },
    "meme_maker": {
        "tech_stack": "flask",
        "main_file": "app.py",
        "files": {
            "app.py": _MEME_MAKER_CODE,
            "requirements.txt": "flask\npillow\n",
            "README.md": "# Meme Maker\n\nRun: `python app.py`\n",
        },
    },
    "json_formatter": {
        "tech_stack": "static",
        "main_file": "index.html",
        "files": {
            "index.html": _JSON_FORMATTER_HTML,
            "README.md": "# JSON Formatter\n\nOpen `index.html` in a browser.\n",
        },
    },
    "unit_converter": {
        "tech_stack": "static",
        "main_file": "index.html",
        "files": {
            "index.html": _UNIT_CONVERTER_HTML,
            "README.md": "# Unit Converter\n\nOpen `index.html` in a browser.\n",
        },
    },
    "todo_micro": {
        "tech_stack": "flask",
        "main_file": "app.py",
        "files": {
            "app.py": _TODO_MICRO_CODE,
            "requirements.txt": "flask\n",
            "README.md": "# Micro Todo\n\nRun: `python app.py`\n",
        },
    },
}


def _generate_custom_boilerplate(app_type: str, features: List[str], tech_stack: str) -> Dict[str, str]:
    """Generate a minimal but runnable boilerplate for unrecognized app types."""
    tech_stack = (tech_stack or "flask").lower().strip()
    title = app_type.replace("_", " ").title()
    feature_items = "\n".join(f"<li>{f}</li>" for f in features) if features else "<li>Coming soon</li>"
    if tech_stack == "flask":
        code = f'''from flask import Flask, render_template_string
import os

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }}
ul {{ line-height: 1.6; }}
</style>
</head>
<body>
<h1>{title}</h1>
<ul>
{feature_items}
</ul>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
'''
        return {
            "app.py": code,
            "requirements.txt": "flask\n",
            "README.md": f"# {title}\n\nRun: `python app.py`\n",
        }
    else:
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<ul>
{feature_items}
</ul>
</body>
</html>'''
        return {
            "index.html": html,
            "README.md": f"# {title}\n\nOpen `index.html` in a browser.\n",
        }


def _app_disk_path(app_id: str) -> str:
    """Return the absolute on-disk path for an app's product directory."""
    return os.path.join(config.WORKSPACE_ROOT, "products", "apps", app_id)


def _write_app_files(app_id: str, files: Dict[str, str]) -> List[str]:
    """Write app files to disk and return the list of written paths."""
    app_dir = _app_disk_path(app_id)
    os.makedirs(app_dir, exist_ok=True)
    written: List[str] = []
    for filename, content in files.items():
        file_path = os.path.join(app_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        written.append(file_path)
    return written


# ── Business Tools ─────────────────────────────────────────────────────────

@business_tool(
    name="research_micro_saas_ideas",
    description="Research viable micro-SaaS ideas for a given niche. Returns curated ideas with difficulty, monetization model, and estimated MRR.",
    category="saas",
)
def research_micro_saas_ideas(niche: str) -> Dict[str, Any]:
    """
    Return up to 5 curated micro-SaaS ideas filtered by niche.

    Args:
        niche: Target niche (e.g., 'marketing', 'developer_tools', 'general').

    Returns:
        Dict with 'niche' and 'ideas' list.
    """
    niche_lower = niche.lower().strip()
    if niche_lower in ("general", "all", ""):
        filtered = _IDEA_CATALOG[:5]
    else:
        filtered = [idea for idea in _IDEA_CATALOG if niche_lower in idea["niche"].lower()]
        if not filtered:
            filtered = _IDEA_CATALOG[:3]
    return {"niche": niche, "ideas": filtered}


@business_tool(
    name="generate_app_code",
    description="Generate complete, runnable app code for a given app type. Supports url_shortener, qr_generator, password_generator, meme_maker, json_formatter, unit_converter, todo_micro, and custom types.",
    category="saas",
)
def generate_app_code(app_type: str, features: List[str], tech_stack: str = "flask") -> Dict[str, Any]:
    """
    Generate production-ready app code and write files to disk.

    Args:
        app_type: Type of app (e.g., 'url_shortener', 'qr_generator', 'custom').
        features: List of desired features.
        tech_stack: Either 'flask' or 'static'.

    Returns:
        Dict with app_type, tech_stack, main_file, files dict, disk_paths, and a note.
    """
    app_type_clean = app_type.lower().strip().replace(" ", "_").replace("-", "_")
    template = _APP_CODE_TEMPLATES.get(app_type_clean)
    tech_stack = (tech_stack or "flask").lower().strip()

    if not template:
        files = _generate_custom_boilerplate(app_type_clean, features, tech_stack)
        disk_paths = _write_app_files(app_type_clean, files)
        return {
            "app_type": app_type_clean,
            "tech_stack": tech_stack,
            "main_file": "app.py" if tech_stack == "flask" else "index.html",
            "files": files,
            "disk_paths": disk_paths,
            "note": "Custom app generated from generic boilerplate and written to disk.",
        }

    files = dict(template["files"])
    if features:
        feat_comment = "\n# Requested features: " + ", ".join(features) + "\n"
        main_file = template["main_file"]
        if main_file in files:
            lines = files[main_file].splitlines()
            import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    import_idx = i + 1
            lines.insert(import_idx, feat_comment)
            files[main_file] = "\n".join(lines)

    disk_paths = _write_app_files(app_type_clean, files)

    return {
        "app_type": app_type_clean,
        "tech_stack": template["tech_stack"],
        "main_file": template["main_file"],
        "files": files,
        "disk_paths": disk_paths,
        "note": "App generated from production template and written to disk.",
    }


@business_tool(
    name="create_stripe_payment_link_for_app",
    description="Create a Stripe payment link for a micro-app. Uses real Stripe API in LIVE_MODE.",
    category="saas",
    requires_api_key=True,
    api_key_env="STRIPE_SECRET_KEY",
)
def create_stripe_payment_link_for_app(app_id: str, price: float, recurring: bool = False) -> Dict[str, Any]:
    """
    Create a Stripe payment link for the given app.

    Args:
        app_id: Unique app identifier.
        price: Price in USD.
        recurring: Whether the price is a monthly subscription.

    Returns:
        Dict with payment_link, price_id, product_id, and status.
    """
    if config.LIVE_MODE:
        if not config.STRIPE_SECRET_KEY:
            raise ValueError("STRIPE_SECRET_KEY required in LIVE_MODE")
        try:
            import stripe

            stripe.api_key = config.STRIPE_SECRET_KEY
            product = stripe.Product.create(
                name=f"{app_id} Pro",
                description=f"Premium access to {app_id}",
            )
            price_data: Dict[str, Any] = {
                "unit_amount": int(price * 100),
                "currency": "usd",
                "product": product.id,
            }
            if recurring:
                price_data["recurring"] = {"interval": "month"}
            price_obj = stripe.Price.create(**price_data)
            link = stripe.PaymentLink.create(
                line_items=[{"price": price_obj.id, "quantity": 1}],
            )
            return {
                "payment_link": link.url,
                "price_id": price_obj.id,
                "product_id": product.id,
                "status": "live",
                "app_id": app_id,
            }
        except Exception as exc:
            return {
                "error": str(exc),
                "payment_link": None,
                "status": "stripe_error",
                "app_id": app_id,
            }

    # Test mode: return setup instructions
    test_link = f"https://dashboard.stripe.com/test/payment-links/create?prefilled[amount]={int(price * 100)}"
    return {
        "payment_link": test_link,
        "price_id": f"test_price_{app_id}",
        "product_id": f"test_prod_{app_id}",
        "status": "test_mode",
        "app_id": app_id,
        "note": "Running in test mode. Set LIVE_MODE=true and STRIPE_SECRET_KEY to create live payment links.",
    }


@business_tool(
    name="package_app_for_deploy",
    description="Generate a deployment manifest (Dockerfile, docker-compose, deploy script) for a micro-app and write it to disk.",
    category="saas",
)
def package_app_for_deploy(app_id: str) -> Dict[str, Any]:
    """
    Create a deployment package for the specified app and write files to disk.

    Args:
        app_id: App identifier (must exist in vault micro_apps collection).

    Returns:
        Dict with manifest, disk_paths, and packaging status.
    """
    app_doc = vault.get("micro_apps", app_id)
    if not app_doc:
        return {"error": f"App {app_id} not found in vault", "status": "failed"}

    tech_stack = app_doc.get("tech_stack", "flask")
    files: Dict[str, str] = {}

    if tech_stack.lower() == "flask":
        files["Dockerfile"] = (
            "FROM python:3.11-slim\n"
            "WORKDIR /app\n"
            "COPY requirements.txt .\n"
            "RUN pip install --no-cache-dir -r requirements.txt\n"
            "COPY . .\n"
            "EXPOSE 5000\n"
            'CMD ["python", "app.py"]\n'
        )
        files["docker-compose.yml"] = (
            'version: "3.8"\n'
            "services:\n"
            f"  {app_id}:\n"
            "    build: .\n"
            "    ports:\n"
            '      - "5000:5000"\n'
            "    environment:\n"
            '      - PORT=5000\n'
        )
    else:
        files["Dockerfile"] = (
            "FROM nginx:alpine\n"
            "COPY index.html /usr/share/nginx/html/index.html\n"
            "EXPOSE 80\n"
        )
        files["docker-compose.yml"] = (
            'version: "3.8"\n'
            "services:\n"
            f"  {app_id}:\n"
            "    build: .\n"
            "    ports:\n"
            '      - "8080:80"\n'
        )

    files["deploy.sh"] = (
        "#!/bin/bash\n"
        "set -e\n"
        "docker-compose down || true\n"
        "docker-compose up --build -d\n"
        f'echo "Deployed {app_id}"\n'
    )

    manifest = {
        "app_id": app_id,
        "tech_stack": tech_stack,
        "files": files,
        "instructions": f"Run `bash deploy.sh` to start {app_id}.",
        "packaged_at": datetime.utcnow().isoformat(),
    }

    disk_paths = _write_app_files(app_id, files)
    vault.update("micro_apps", app_id, {"deploy_manifest": manifest})
    return {"manifest": manifest, "disk_paths": disk_paths, "status": "packaged"}


@business_tool(
    name="get_app_analytics",
    description="Return usage and revenue analytics for a micro-app. Returns real data only; never generates mock data.",
    category="saas",
)
def get_app_analytics(app_id: str) -> Dict[str, Any]:
    """
    Retrieve analytics for an app.

    Args:
        app_id: App identifier.

    Returns:
        Dict with users, revenue, churn_rate, mrr, and period; or empty data with a message.
    """
    existing = vault.find("app_analytics", lambda d: d.get("app_id") == app_id, limit=1)
    if existing:
        return existing[0]

    if config.LIVE_MODE:
        return {
            "app_id": app_id,
            "users": 0,
            "revenue": 0.0,
            "churn_rate": 0.0,
            "mrr": 0.0,
            "period": "last_30_days",
            "message": "No real analytics data available yet.",
        }

    return {
        "app_id": app_id,
        "users": 0,
        "revenue": 0.0,
        "churn_rate": 0.0,
        "mrr": 0.0,
        "period": "last_30_days",
        "message": "No analytics data available. Integrate a real analytics provider to populate this.",
    }


@business_tool(
    name="sunset_app",
    description="Mark a micro-app as deprecated/sunset in the vault.",
    category="saas",
)
def sunset_app(app_id: str) -> Dict[str, Any]:
    """
    Sunset an app by updating its status.

    Args:
        app_id: App identifier.

    Returns:
        Dict with app_id, status, and message.
    """
    success = vault.update(
        "micro_apps",
        app_id,
        {"status": "sunset", "sunset_at": datetime.utcnow().isoformat()},
    )
    if not success:
        return {"error": f"App {app_id} not found", "status": "failed"}
    return {
        "app_id": app_id,
        "status": "sunset",
        "message": f"App {app_id} has been sunset and is no longer active.",
    }
