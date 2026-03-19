import os
import hmac
import hashlib
import base64
from flask import Flask, request, abort, jsonify
from dotenv import load_dotenv
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage,
    LocationMessage
)
from database_old import init_db, save_owner, get_line_user_id, get_all_owners, save_location

load_dotenv()

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
INTERNAL_API_KEY = os.getenv("API_KEY")

app = Flask(__name__)
configuration = Configuration(access_token=ACCESS_TOKEN)

# Init DB on startup
init_db()

def verify_signature(req):
    signature = req.headers.get("X-Line-Signature", "")
    body = req.get_data(as_text=True)
    mac = hmac.new(
        CHANNEL_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(signature, expected_signature)

@app.post("/line/webhook")
def webhook():
    if not verify_signature(request):
        abort(403, "Invalid signature")
    body = request.json
    events = body.get("events", [])
    for event in events:
        handle_event(event)
    return "OK", 200

def handle_event(event):
    event_type = event.get("type")
    source = event.get("source", {})
    user_id = source.get("userId")
    reply_token = event.get("replyToken")

    if event_type == "follow":
        print(f"New user added bot: {user_id}")
        reply_message(reply_token,
            "Welcome! 🚛\n\n"
            "To receive fleet updates, send your Owner ID:\n"
            "LINK:your_owner_id\n\n"
            "Example: LINK:owner001"
        )

    if event_type == "message":
        msg_type = event["message"]["type"]
        if msg_type == "text":
            user_text = event["message"]["text"].strip()

            if user_text.upper().startswith("LINK:"):
                owner_id = user_text.split(":", 1)[1].strip()
                save_owner(owner_id, user_id)           # ← saves to SQLite
                reply_message(reply_token,
                    f"✅ Successfully linked!\n"
                    f"Owner ID: {owner_id}\n\n"
                    f"You will now receive fleet location updates here. 🚛"
                )

            elif user_text.upper() == "STATUS":
                all_owners = get_all_owners()
                linked = next((o for o in all_owners if o[1] == user_id), None)
                if linked:
                    reply_message(reply_token,
                        f"✅ Linked!\n"
                        f"Owner ID : {linked[0]}\n"
                        f"Name     : {linked[2]}\n"
                        f"Phone    : {linked[3]}"
                    )
                else:
                    reply_message(reply_token, "❌ Not linked yet.\nSend: LINK:your_owner_id")
            else:
                reply_message(reply_token,
                    "Commands:\n"
                    "• LINK:owner_id — Link your account\n"
                    "• STATUS — Check link status"
                )

@app.post("/fleet/location")
def fleet_location():
    api_key = request.headers.get("X-API-Key", "")
    if api_key != INTERNAL_API_KEY:
        abort(403, "Unauthorized")

    data = request.json
    owner_id   = data.get("owner_id")
    vehicle_id = data.get("vehicle_id", "Unknown")
    driver     = data.get("driver_name", "Unknown")
    latitude   = data.get("latitude")
    longitude  = data.get("longitude")
    speed      = data.get("speed", 0)
    status     = data.get("status", "unknown")

    if not all([owner_id, latitude, longitude]):
        return jsonify({"error": "owner_id, latitude, longitude required"}), 400

    line_user_id = get_line_user_id(owner_id)       # ← fetch from SQLite
    if not line_user_id:
        return jsonify({"error": f"Owner '{owner_id}' not linked to LINE"}), 404

    # Save to location history
    save_location(owner_id, vehicle_id, driver, latitude, longitude, speed, status)

    status_emoji = {"moving": "🟢", "idle": "🟡", "stopped": "🔴"}.get(status, "⚪")
    summary = (
        f"🚛 Fleet Update\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Vehicle : {vehicle_id}\n"
        f"Driver  : {driver}\n"
        f"Speed   : {speed} km/h\n"
        f"Status  : {status_emoji} {status.capitalize()}\n"
        f"━━━━━━━━━━━━━━━"
    )

    push_text(line_user_id, summary)
    push_location(line_user_id,
        title=f"{vehicle_id} — {driver}",
        address=f"Speed: {speed} km/h | {status.capitalize()}",
        latitude=latitude,
        longitude=longitude
    )

    return jsonify({"success": True, "sent_to": line_user_id}), 200

@app.post("/fleet/broadcast")
def fleet_broadcast():
    api_key = request.headers.get("X-API-Key", "")
    if api_key != INTERNAL_API_KEY:
        abort(403, "Unauthorized")

    data = request.json
    message = data.get("message", "")
    if not message:
        return jsonify({"error": "message is required"}), 400

    success_count = 0
    for owner_id, line_user_id, name, phone in get_all_owners():
        if line_user_id:
            push_text(line_user_id, f"📢 Broadcast\n\n{message}")
            success_count += 1

    return jsonify({"success": True, "sent_to": success_count}), 200

def reply_message(reply_token, text):
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=text)])
            )
    except Exception as e:
        print(f"Failed to reply: {e}")

def push_text(user_id, text):
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(to=user_id, messages=[TextMessage(text=text)])
            )
        print(f"✅ Push text sent to {user_id}")
    except Exception as e:
        print(f"Failed to push text: {e}")

def push_location(user_id, title, address, latitude, longitude):
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[LocationMessage(
                        title=title,
                        address=address,
                        latitude=latitude,
                        longitude=longitude
                    )]
                )
            )
        print(f"✅ Push location sent to {user_id}")
    except Exception as e:
        print(f"Failed to push location: {e}")

if __name__ == "__main__":
    app.run(port=5000, debug=True)