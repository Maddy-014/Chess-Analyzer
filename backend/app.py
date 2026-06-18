from flask import Flask, request, jsonify
from analyzer import analyze_game

app = Flask(__name__)

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()

    if not data or "pgn" not in data:
        return jsonify({"error": "Invalid input"}), 400

    pgn_text = data["pgn"]

    result = analyze_game(pgn_text)

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)