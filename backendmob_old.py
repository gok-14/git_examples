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

from database import init_db, save_owner, get_line_user_id, get_all_owners, save_location

load_dotenv()

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
INTERNAL_API_KEY = os.getenv("API_KEY")

app = Flask(__name__)
configuration = Configuration(access_token=ACCESS_TOKEN)

# Initialize DB
init_db()

# -----------------------------
# Verify LINE webhook signature
# -----------------------------
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

# -----------------------------
# LINE Webhook
# -----------------------------
@app.post("/line/webhook")
def webhook():

    if not verify_signature(request):
        abort(403, "Invalid signature")

    body = request.json
    events = body.get("events", [])

    for event in events:
        handle_event(event)

    return "OK", 200


# -----------------------------
# Handle LINE Events
# -----------------------------
def handle_event(event):

    event_type = event.get("type")
    source = event.get("source", {})
    user_id = source.get("userId")
    reply_token = event.get("replyToken")

    # New user adds bot
    if event_type == "follow":

        print(f"New user added bot: {user_id}")

        reply_message(
            reply_token,
            "Welcome! 🚛\n\n"
            "To receive fleet updates, send your mobile number:\n"
            "LINK:your_mobile_number\n\n"
            "Example: LINK:9876543210"
        )

    # Message event
    if event_type == "message":

        msg_type = event["message"]["type"]

        if msg_type == "text":

            user_text = event["message"]["text"].strip()

            # -----------------------------
            # LINK MOBILE NUMBER
            # -----------------------------
            if user_text.upper().startswith("LINK:"):

                owner_mobile = user_text.split(":", 1)[1].strip()

                save_owner(owner_mobile, user_id)

                reply_message(
                    reply_token,
                    f"✅ Successfully linked!\n"
                    f"Mobile Number: {owner_mobile}\n\n"
                    f"You will now receive fleet location updates here. 🚛"
                )

            # -----------------------------
            # STATUS
            # -----------------------------
            elif user_text.upper() == "STATUS":

                all_owners = get_all_owners()

                linked = next((o for o in all_owners if o[1] == user_id), None)

                if linked:

                    reply_message(
                        reply_token,
                        f"✅ Linked!\n"
                        f"Mobile Number : {linked[0]}\n"
                        f"Linked On     : {linked[2]}"
                    )

                else:

                    reply_message(
                        reply_token,
                        "❌ Not linked yet.\nSend: LINK:your_mobile_number"
                    )

            else:

                reply_message(
                    reply_token,
                    "Commands:\n"
                    "• LINK:mobile_number — Link your account\n"
                    "• STATUS — Check link status"
                )


# -----------------------------
# Receive Fleet Location
# -----------------------------
@app.post("/fleet/location")
def fleet_location():

    api_key = request.headers.get("X-API-Key", "")

    if api_key != INTERNAL_API_KEY:
        abort(403, "Unauthorized")

    data = request.json

    owner_mobile = data.get("owner_id")
    vehicle_id = data.get("vehicle_id", "Unknown")
    driver = data.get("driver_name", "Unknown")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    speed = data.get("speed", 0)
    status = data.get("status", "unknown")

    if not all([owner_mobile, latitude, longitude]):
        return jsonify({"error": "owner_id, latitude, longitude required"}), 400

    # Find LINE user
    line_user_id = get_line_user_id(owner_mobile)

    if not line_user_id:
        return jsonify({"error": f"Owner '{owner_mobile}' not linked to LINE"}), 404

    # Save location history
    save_location(owner_mobile, vehicle_id, driver, latitude, longitude, speed, status)

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

    push_location(
        line_user_id,
        title=f"{vehicle_id} — {driver}",
        address=f"Speed: {speed} km/h | {status.capitalize()}",
        latitude=latitude,
        longitude=longitude
    )

    return jsonify({"success": True, "sent_to": line_user_id}), 200


# -----------------------------
# Broadcast Message
# -----------------------------
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

    for owner_mobile, line_user_id, created_date in get_all_owners():

        if line_user_id:
            push_text(line_user_id, f"📢 Broadcast\n\n{message}")
            success_count += 1

    return jsonify({"success": True, "sent_to": success_count}), 200


# -----------------------------
# LINE Reply
# -----------------------------
def reply_message(reply_token, text):

    try:

        with ApiClient(configuration) as api_client:

            line_bot_api = MessagingApi(api_client)

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=text)]
                )
            )

    except Exception as e:
        print(f"Failed to reply: {e}")


# -----------------------------
# Push Text
# -----------------------------
def push_text(user_id, text):

    try:

        with ApiClient(configuration) as api_client:

            line_bot_api = MessagingApi(api_client)

            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=text)]
                )
            )

        print(f"✅ Push text sent to {user_id}")

    except Exception as e:
        print(f"Failed to push text: {e}")


# -----------------------------
# Push Location
# -----------------------------
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


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run(port=5000, debug=True)