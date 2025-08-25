# main.py
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/api", methods=["GET"])
def hello():
    return jsonify({"message": "Hello from your EC2-hosted API!"})

@app.route("/api/echo", methods=["POST"])
def echo():
    data = request.json
    return jsonify({"you_sent": data})

@app.route("/api/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
