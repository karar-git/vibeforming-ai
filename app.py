import json
from flask import Flask, jsonify, request
from ai_features import AIClient

app = Flask(__name__)
client = AIClient()

@app.route("/generate", methods=["POST"])
def generate_form():
    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt")
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    result = client.generate_form(prompt)
    parsed = json.loads(result)
    return jsonify(parsed)

@app.route("/analyze", methods=["POST"])
def analyze_text():
    print("Content-Type:", request.content_type)
    print("Raw data:", request.data)
    print("JSON attempt:", request.get_json(silent=True))
    
    payload = request.get_json(silent=True, force=True) or {}
    text = payload.get("question")
    csv_data = payload.get("csv_data")
    
    if not text or not csv_data:
        return jsonify({"error": "question and csv_data are required"}), 400
    
    result = client.analyze_data(csv_data, text)
    parsed = json.loads(result)
    return jsonify(parsed)

@app.route("/", methods=["GET"])
def healthcheck():
    return jsonify({"status": "ok"})
