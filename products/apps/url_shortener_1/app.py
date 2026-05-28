from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# In-memory store
store = {}

HTML = """
<!doctype html>
<title>Url Shortener</title>
<h1>Welcome to Url Shortener</h1>
<p>Users: {{ users }}</p>
"""

@app.route("/")
def home():
    return render_template_string(HTML, users=len(store))

@app.route("/api/data", methods=["GET", "POST"])
def api_data():
    if request.method == "POST":
        data = request.get_json(force=True)
        store[data.get("id", "x")] = data
        return jsonify({"saved": True})
    return jsonify(store)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
