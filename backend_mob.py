import os

import hmac

import hashlib

import base64

import logging

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

 

# -----------------------------

# Setup

# -----------------------------

load_dotenv()

 

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

INTERNAL_API_KEY = os.getenv("API_KEY")

 

app = Flask(__name__)

configuration = Configuration(access_token=ACCESS_TOKEN)

 

# Initialize DB

init_db()

 

# -----------------------------

# Logging

# -----------------------------

logging.basicConfig(

    level=logging.INFO,

    format="%(asctime)s | %(levelname)s | %(message)s"

)

logger = logging.getLogger("fleet-tracker")

 

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

 

    is_valid = hmac.compare_digest(signature, expected_signature)

    if not is_valid:

        logger.warning("Invalid LINE signature.")

    return is_valid

 

# -----------------------------

# Helper: Welcome message

# -----------------------------

WELCOME_TEXT = (

    "👋 Welcome to Fleet Tracker! 🚛\n"

    "━━━━━━━━━━━━━━━\n\n"

    "To get started, link your mobile number so we can send you fleet updates.\n\n"

    "📌 Send this command:\n"

    "LINK:your_mobile_number\n\n"

    "Example:\n"

    "LINK:9876543210\n\n"

    "━━━━━━━━━━━━━━━\n"

    "Other commands:\n"

    "• STATUS — Check if your account is linked"

)

 

def send_welcome_message(reply_token=None, user_id=None):

    """

    Prefer replying (ensures 'first message' in the same conversation flow).

    Fallback to push if reply_token not available.

    """

    if reply_token:

        ok = reply_message(reply_token, WELCOME_TEXT, log_tag="welcome-reply")

        if ok:

            return True

        # fallback to push if reply failed

        if user_id:

            return push_text(user_id, WELCOME_TEXT, log_tag="welcome-push")

        return False

    elif user_id:

        return push_text(user_id, WELCOME_TEXT, log_tag="welcome-push")

    return False

 

# -----------------------------

# LINE Webhook

# -----------------------------

@app.post("/line/webhook")

def webhook():

 

    if not verify_signature(request):

        abort(403, "Invalid signature")

 

    body = request.json or {}

    events = body.get("events", [])

 

    logger.info("Received webhook with %d event(s).", len(events))

 

    for event in events:

        handle_event(event)

 

    return "OK", 200

 

# -----------------------------

# Handle LINE Events

# -----------------------------

def handle_event(event):

 

    event_type = event.get("type")

    source = event.get("source", {}) or {}

    user_id = source.get("userId")

    reply_token = event.get("replyToken")

 

    logger.info("Event type=%s | user_id=%s", event_type, user_id)

 

    # -------------------------------------------------------

    # FOLLOW EVENT — user adds bot by scanning QR or search

    # -------------------------------------------------------

    if event_type == "follow":

        logger.info("New user followed — LINE User ID: %s", user_id)

        # Send welcome as a reply (first message from bot). Fallback to push.

        send_welcome_message(reply_token=reply_token, user_id=user_id)

 

    # -------------------------------------------------------

    # MESSAGE EVENT — user sends a message

    # -------------------------------------------------------

    elif event_type == "message":

        msg = event.get("message", {}) or {}

        msg_type = msg.get("type")

        logger.info("Incoming message | user_id=%s | type=%s | raw=%s", user_id, msg_type, msg)

 

        if msg_type == "text":

            user_text = (msg.get("text") or "").strip()

            logger.info("User text | user_id=%s | text=%r", user_id, user_text)

 

            # -----------------------------

            # LINK MOBILE NUMBER

            # -----------------------------

            if user_text.upper().startswith("LINK:"):

                # robust split

                _, _, value = user_text.partition(":")

                owner_mobile = value.strip().replace(" ", "")

 

                if not owner_mobile:

                    reply_message(

                        reply_token,

                        "❗ Please provide a mobile number. Example:\nLINK:9876543210",

                        log_tag="link-invalid"

                    )

                    return

 

                try:

                    save_owner(owner_mobile, user_id)

                    logger.info("Linked | mobile=%s | user_id=%s", owner_mobile, user_id)

 

                    reply_message(

                        reply_token,

                        (

                            f"✅ Successfully linked!\n"

                            f"Mobile Number: {owner_mobile}\n\n"

                            f"You will now receive fleet location updates here. 🚛"

                        ),

                        log_tag="link-success"

                    )

                except Exception as e:

                    logger.exception("Error linking owner: %s", e)

                    reply_message(

                        reply_token,

                        "⚠️ Could not link at the moment. Please try again.",

                        log_tag="link-failed"

                    )

 

            # -----------------------------

            # STATUS

            # -----------------------------

            elif user_text.upper() == "STATUS":

                try:

                    all_owners = get_all_owners()

                    linked = next((o for o in all_owners if o[1] == user_id), None)

 

                    if linked:

                        reply_message(

                            reply_token,

                            (

                                f"✅ Linked!\n"

                                f"Mobile Number : {linked[0]}\n"

                                f"Linked On     : {linked[2]}"

                            ),

                            log_tag="status-linked"

                        )

                    else:

                        reply_message(

                            reply_token,

                            (

                                "❌ Not linked yet.\n\n"

                                "Send: LINK:your_mobile_number\n"

                                "Example: LINK:9876543210"

                            ),

                            log_tag="status-not-linked"

                        )

                except Exception as e:

                    logger.exception("Error fetching status: %s", e)

                    reply_message(

                        reply_token,

                        "⚠️ Could not fetch status. Please try again.",

                        log_tag="status-error"

                    )

 

            # -----------------------------

            # UNKNOWN COMMAND

            # -----------------------------

            else:

                reply_message(

                    reply_token,

                    (

                        "Commands:\n"

                        "• LINK:mobile_number — Link your account\n"

                        "• STATUS — Check link status"

                    ),

                    log_tag="unknown-command"

                )

 

        else:

            # Non-text messages can be acknowledged or ignored as needed

            reply_message(

                reply_token,

                "I can currently process text commands only.\nTry: STATUS or LINK:9876543210",

                log_tag="non-text"

            )

 

    # -------------------------------------------------------

    # Unhandled events (join, unfollow, postback, etc.)

    # -------------------------------------------------------

    else:

        logger.info("Unhandled event type=%s | event=%s", event_type, event)

 

# -----------------------------

# Receive Fleet Location

# -----------------------------

@app.post("/fleet/location")

def fleet_location():

 

    api_key = request.headers.get("X-API-Key", "")

    if api_key != INTERNAL_API_KEY:

        abort(403, "Unauthorized")

 

    data = request.json or {}

 

    owner_mobile = data.get("owner_id")

    vehicle_id = data.get("vehicle_id", "Unknown")

    driver = data.get("driver_name", "Unknown")

    latitude = data.get("latitude")

    longitude = data.get("longitude")

    speed = data.get("speed", 0)

    status = data.get("status", "unknown")

 

    logger.info(

        "Fleet location | owner=%s | veh=%s | drv=%s | lat=%s | lon=%s | spd=%s | status=%s",

        owner_mobile, vehicle_id, driver, latitude, longitude, speed, status

    )

 

    if not all([owner_mobile, latitude, longitude]):

        return jsonify({"error": "owner_id, latitude, longitude required"}), 400

 

    # Find LINE user

    line_user_id = get_line_user_id(owner_mobile)

    if not line_user_id:

        return jsonify({"error": f"Owner '{owner_mobile}' not linked to LINE"}), 404

 

    # Save location history

    try:

        save_location(owner_mobile, vehicle_id, driver, latitude, longitude, speed, status)

    except Exception as e:

        logger.exception("Error saving location: %s", e)

 

    status_emoji = {"moving": "🟢", "idle": "🟡", "stopped": "🔴"}.get(status, "⚪")

 

    summary = (

        f"🚛 Fleet Update\n"

        f"━━━━━━━━━━━━━━━\n"

        f"Vehicle : {vehicle_id}\n"

        f"Driver  : {driver}\n"

        f"Speed   : {speed} km/h\n"

        f"Status  : {status_emoji} {str(status).capitalize()}\n"

        f"━━━━━━━━━━━━━━━"

    )

 

    push_text(line_user_id, summary, log_tag="fleet-summary")

 

    push_location(

        line_user_id,

        title=f"{vehicle_id} — {driver}",

        address=f"Speed: {speed} km/h | {str(status).capitalize()}",

        latitude=latitude,

        longitude=longitude,

        log_tag="fleet-location"

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

 

    data = request.json or {}

    message = data.get("message", "")

 

    if not message:

        return jsonify({"error": "message is required"}), 400

 

    success_count = 0

 

    for owner_mobile, line_user_id, created_date in get_all_owners():

        if line_user_id:

            if push_text(line_user_id, f"📢 Broadcast\n\n{message}", log_tag="broadcast"):

                success_count += 1

 

    logger.info("Broadcast sent to %d user(s).", success_count)

    return jsonify({"success": True, "sent_to": success_count}), 200

 

# -----------------------------

# LINE Reply

# -----------------------------

def reply_message(reply_token, text, log_tag="reply"):

    try:

        with ApiClient(configuration) as api_client:

            line_bot_api = MessagingApi(api_client)

            line_bot_api.reply_message(

                ReplyMessageRequest(

                    reply_token=reply_token,

                    messages=[TextMessage(text=text)]

                )

            )

        logger.info("✅ %s | Replied: %r", log_tag, text)

        return True

    except Exception as e:

        logger.exception("Failed to reply (%s): %s", log_tag, e)

        return False

 

# -----------------------------

# Push Text

# -----------------------------

def push_text(user_id, text, log_tag="push-text"):

    try:

        with ApiClient(configuration) as api_client:

            line_bot_api = MessagingApi(api_client)

            line_bot_api.push_message(

                PushMessageRequest(

                    to=user_id,

                    messages=[TextMessage(text=text)]

                )

            )

        logger.info("✅ %s | Push text sent to %s | text=%r", log_tag, user_id, text)

        return True

    except Exception as e:

        logger.exception("Failed to push text (%s): %s", log_tag, e)

        return False

 

# -----------------------------

# Push Location

# -----------------------------

def push_location(user_id, title, address, latitude, longitude, log_tag="push-location"):

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

        logger.info(

            "✅ %s | Push location to %s | title=%r | address=%r | lat=%s | lon=%s",

            log_tag, user_id, title, address, latitude, longitude

        )

        return True

    except Exception as e:

        logger.exception("Failed to push location (%s): %s", log_tag, e)

        return False

 

# -----------------------------

# Run App

# -----------------------------

if __name__ == "__main__":

    app.run(port=5000, debug=True)

 