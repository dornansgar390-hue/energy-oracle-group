import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/', defaults={"path": ""})
@app.route('/<path:path>')
def handle_all(path):
    return jsonify({
        "status": "removed",
        "message": "This Energy Oracle endpoint has been permanently removed.",
        "reason": "Service discontinued. The oracle is no longer available at this endpoint.",
        "repository": "https://github.com/dornansgar390-hue/energy-oracle-group"
    }), 410
