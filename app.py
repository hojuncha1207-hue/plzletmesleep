import os, json, requests
from urllib.parse import urlencode
from flask import Flask, request, jsonify, send_from_directory, redirect, make_response, url_for
from flask_cors import CORS

# ---- Config via env ----
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "").strip()
KAKAO_REDIRECT_URI = os.environ.get("KAKAO_REDIRECT_URI", "").strip()  # e.g., https://plzletmesleep.onrender.com/oauth/kakao/callback
KAKAO_AUTH_HOST = "https://kauth.kakao.com"
KAKAO_API_HOST  = "https://kapi.kakao.com"

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

COOKIE_NAME = "k_uid"   # stores Kakao user id
COOKIE_MAX_AGE = 60*60*24*365  # 1 year

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

# ---------- Kakao OAuth (PKCE omitted for brevity) ----------
@app.route("/oauth/kakao/start")
def kakao_start():
    # send user to Kakao consent page
    if not KAKAO_REST_API_KEY or not KAKAO_REDIRECT_URI:
        return "Kakao OAuth not configured. Set KAKAO_REST_API_KEY and KAKAO_REDIRECT_URI.", 500
    params = {
        "client_id": KAKAO_REST_API_KEY,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "response_type": "code",
        "prompt": "login",  # ensure login when needed
    }
    return redirect(f"{KAKAO_AUTH_HOST}/oauth/authorize?{urlencode(params)}", code=302)

@app.route("/oauth/kakao/callback")
def kakao_callback():
    # exchange code -> token -> user info
    code = request.args.get("code")
    if not code:
        return "Missing code", 400
    if not KAKAO_REST_API_KEY or not KAKAO_REDIRECT_URI:
        return "Kakao OAuth not configured.", 500

    # token
    token_res = requests.post(f"{KAKAO_AUTH_HOST}/oauth/token", data={
        "grant_type": "authorization_code",
        "client_id": KAKAO_REST_API_KEY,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if token_res.status_code != 200:
        return f"Token error: {token_res.text}", 500
    token_json = token_res.json()
    access_token = token_json.get("access_token")
    if not access_token:
        return "No access_token", 500

    # /v2/user/me
    me_res = requests.get(f"{KAKAO_API_HOST}/v2/user/me",
                          headers={"Authorization": f"Bearer {access_token}"})
    if me_res.status_code != 200:
        return f"User info error: {me_res.text}", 500
    me = me_res.json()
    kakao_user_id = str(me.get("id"))  # numeric id
    if not kakao_user_id or kakao_user_id == "None":
        return "No Kakao user id", 500

    # set cookie and bounce user back
    resp = make_response(redirect(request.cookies.get("post_login_redirect") or "/launch/order", code=302))
    resp.set_cookie(COOKIE_NAME, kakao_user_id, max_age=COOKIE_MAX_AGE, httponly=False, samesite="Lax", path="/")
    return resp

@app.route("/api/whoami")
def whoami():
    # simple helper for the front-end
    uid = request.cookies.get(COOKIE_NAME, "")
    return jsonify({"user_id": uid or None})

# ---------- Orders API ----------
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
    qr_content = f"/launch/view-order"  # view page will use cookie to resolve user

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
    # prefer explicit param, else cookie
    user_id = (request.args.get("user_id") or request.cookies.get(COOKIE_NAME) or "").strip()
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

# ---------- Launch pages ----------
@app.route("/launch/order")
def launch_order():
    return send_from_directory(".", "order.html")

@app.route("/launch/view-order")
def launch_view_order():
    return send_from_directory(".", "view-order.html")

@app.route("/")
def root():
    return redirect("/launch/order", code=302)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")), debug=True)
