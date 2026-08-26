"""
Petit serveur relais (proxy) pour l'outil "Suivi des heures" du cabinet.

Rôle : cacher la clé jsonbin.io côté serveur (jamais envoyée au navigateur),
et transmettre les lectures/écritures vers jsonbin.io.

Variables d'environnement à définir dans le tableau de bord Render :
  JSONBIN_ID  = l'identifiant de votre bin jsonbin.io
  JSONBIN_KEY = votre X-Master-Key jsonbin.io

Aucune donnée n'est stockée sur ce serveur lui-même : il ne fait que relayer
vers jsonbin.io, donc pas de souci de perte de données au redémarrage.
"""

import json
import os
import urllib.request
import urllib.error
from flask import Flask, jsonify, request, Response

app = Flask(__name__)

JSONBIN_ID = os.environ.get("JSONBIN_ID", "")
JSONBIN_KEY = os.environ.get("JSONBIN_KEY", "")
JSONBIN_BASE = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"


def _add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.after_request
def apply_cors(resp):
    return _add_cors(resp)


@app.route("/api/data", methods=["OPTIONS"])
def preflight():
    return _add_cors(Response(status=204))


@app.route("/api/data", methods=["GET"])
def get_data():
    if not JSONBIN_ID or not JSONBIN_KEY:
        return jsonify({"error": "Serveur non configuré (JSONBIN_ID / JSONBIN_KEY manquants)"}), 500
    req = urllib.request.Request(
        JSONBIN_BASE + "/latest",
        headers={"X-Master-Key": JSONBIN_KEY, "X-Bin-Meta": "false"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return jsonify({"error": str(e)}), 502
    return jsonify(data)


@app.route("/api/data", methods=["POST"])
def set_data():
    if not JSONBIN_ID or not JSONBIN_KEY:
        return jsonify({"error": "Serveur non configuré (JSONBIN_ID / JSONBIN_KEY manquants)"}), 500
    payload = request.get_json(force=True, silent=True) or {}
    body = json.dumps({
        "employees": payload.get("employees", []),
        "entries": payload.get("entries", []),
    }).encode("utf-8")
    req = urllib.request.Request(
        JSONBIN_BASE,
        data=body,
        method="PUT",
        headers={"Content-Type": "application/json", "X-Master-Key": JSONBIN_KEY},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            res.read()
    except urllib.error.URLError as e:
        return jsonify({"error": str(e)}), 502
    return jsonify({"ok": True})


@app.route("/")
def index():
    return "Serveur relais OK. Ce service ne sert que l'API /api/data."


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
