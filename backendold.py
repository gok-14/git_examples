# import os

# import hmac

# import hashlib

# import base64

# import json

# from flask import Flask, request, abort

# import requests

# from dotenv import load_dotenv

 

# load_dotenv()

 

# CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

 

# app = Flask(__name__)

 

# # -----------------------------

# # 1️⃣ Verify LINE Signature

# # -----------------------------

# def verify_signature(request):

#     signature = request.headers.get("X-Line-Signature", "")

#     body = request.get_data(as_text=True)

 

#     hash = hmac.new(

#         CHANNEL_SECRET.encode("utf-8"),

#         body.encode("utf-8"),

#         hashlib.sha256

#     ).digest()

 

#     expected_signature = base64.b64encode(hash).decode("utf-8")

 

#     return signature == expected_signature

 

# # -----------------------------

# # 2️⃣ Webhook Endpoint

# # -----------------------------

# @app.post("/line/webhook")

# def webhook():

#     if not verify_signature(request):

#         abort(403, "Invalid signature")

 

#     body = request.json

#     events = body.get("events", [])

 

#     for event in events:

#         handle_event(event)

 

#     return "OK", 200

 

# # -----------------------------

# # 3️⃣ Event Handling Logic

# # -----------------------------

# def handle_event(event):

#     event_type = event.get("type")

#     source = event.get("source", {})

#     user_id = source.get("userId")

 

#     # When user adds the bot → event.type = follow

#     if event_type == "follow":

#         print(f"User added bot: {user_id}")

#         save_user_id(user_id)

 

#         # Send welcome message

#         push_message(user_id, "Thank you for adding our fleet service!")

 

#     # When user sends a text message

#     if event_type == "message":

#         msg_type = event["message"]["type"]

 

#         if msg_type == "text":

#             user_text = event["message"]["text"]

#             print(f"User message: {user_text}")

#             push_message(user_id, f"You said: {user_text}")

 

# # -----------------------------

# # 4️⃣ Database Mock (Replace with real DB)

# # -----------------------------

# USER_DB = {}  # For demo only

 

# def save_user_id(user_id):

#     # In production store:

#     # phone_number ↔ userId

#     USER_DB[user_id] = True

 

# # -----------------------------

# # 5️⃣ Push Message Function

# # -----------------------------

# def push_message(user_id, text):

#     url = "https://api.line.me/v2/bot/message/push"

 

#     headers = {

#         "Content-Type": "application/json",

#         "Authorization": f"Bearer {ACCESS_TOKEN}"

#     }

 

#     body = {

#         "to": user_id,

#         "messages": [

#             {"type": "text", "text": text}

#         ]

#     }

 

#     response = requests.post(url, headers=headers, json=body,verify=False)

 

#     print("Push API response:", response.text)

 

# # -----------------------------

# # 6️⃣ Run Flask

# # -----------------------------

# if __name__ == "__main__":

#     app.run(port=5000, debug=True)


import os
import hmac
import hashlib
import base64
from flask import Flask, request, abort
from dotenv import load_dotenv

from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage
)

load_dotenv()

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

app = Flask(__name__)

# LINE SDK Configuration
configuration = Configuration(access_token=ACCESS_TOKEN)

# -----------------------------
# 1️⃣ Verify LINE Signature
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
# 2️⃣ Webhook Endpoint
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
# 3️⃣ Event Handling Logic
# -----------------------------
def handle_event(event):
    event_type = event.get("type")
    source = event.get("source", {})
    user_id = source.get("userId")

    # When user adds the bot → event.type = follow
    if event_type == "follow":
        print(f"User added bot: {user_id}")
        save_user_id(user_id)
        push_message(user_id, "Thank you for adding our fleet service!")

    # When user sends a text message
    if event_type == "message":
        msg_type = event["message"]["type"]

        if msg_type == "text":
            user_text = event["message"]["text"]
            print(f"User message: {user_text}")
            push_message(user_id, f"You said: {user_text}")

# -----------------------------
# 4️⃣ Database Mock (Replace with real DB)
# -----------------------------
USER_DB = {}

def save_user_id(user_id):
    USER_DB[user_id] = True
    print(f"Saved user: {user_id}")

# -----------------------------
# 5️⃣ Push Message Function (LINE SDK)
# -----------------------------
def push_message(user_id, text):
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=text)]
                )
            )
        print(f"Message sent to {user_id}: {text}")

    except Exception as e:
        print(f"Failed to send message: {e}")

# -----------------------------
# 6️⃣ Run Flask
# -----------------------------
if __name__ == "__main__":
    app.run(port=5000, debug=True)