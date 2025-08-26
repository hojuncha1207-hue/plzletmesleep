import os, json
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS

REDIS_URL = os.environ.get("REDIS_URL")
redis_client = None
if REDIS_URL:
    try:
        import redis  # type: ignore
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        print("Redis import/connection failed:", e)

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

ORDERS = {}

def save_order(user_id: str, data: dict):
    payload = json.dumps(data, ensure_ascii=False)
    if redis_client:
        redis_client.set(user_id, payload)
    else:
        ORDERS[user_id] = payload

def load_order(user_id: str):
    if redis_client:
        return redis_client.get(user_id)
    return ORDERS.get(user_id)

@app.route("/api/health")
def health():
    return jsonify({"ok": True})

@app.route("/api/create-order", methods=["POST"])
def create_order():
    try:
        data = request.get_json(force=True, silent=False) or {}
    except Exception:
        return jsonify({"success": False, "error": "invalid JSON"}), 400

    user_id = (data.get("userId") or "").strip()
    items = data.get("items") or []
    ts = data.get("orderTimestamp")

    if not user_id or not isinstance(items, list) or len(items) == 0:
        return jsonify({"success": False, "error": "invalid payload"}), 400

    order_id = f"ORD-{user_id}"
    # QR 내용은 운영 정책에 맞게 바꾸면 됩니다. 여기선 간단히 URL 기반으로.
    qr_content = f"/launch/view-order?user_id={user_id}"

    order = {
        "orderId": order_id,
        "userId": user_id,
        "items": items,
        "orderTimestamp": ts,
        "qr": qr_content
    }
    save_order(user_id, order)

    return jsonify({"success": True, "orderId": order_id, "qr": qr_content})

@app.route("/api/order", methods=["GET"])
def get_order():
    user_id = request.args.get("user_id", "").strip()
    if not user_id:
        return jsonify({"success": False, "error": "missing user_id"}), 400

    raw = load_order(user_id)
    if not raw:
        return jsonify({"success": False, "error": "NOT_FOUND"}), 404

    try:
        order = json.loads(raw)
    except Exception:
        return jsonify({"success": False, "error": "CORRUPTED"}), 500

    return jsonify({"success": True, "data": order})

# ---------- Launch routes matching user's desired URLs ----------
@app.route("/launch/order")
def launch_order():
    return send_from_directory(".", "order.html")

@app.route("/launch/view-order")
def launch_view_order():
    return send_from_directory(".", "view-order.html")

# Optional helper: root redirect to /launch/order
@app.route("/")
def root():
    return redirect("/launch/order", code=302)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")), debug=True)
