import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import firebase_admin
from firebase_admin import credentials, db


def initialize_firebase():
    if os.environ.get("FIREBASE_CREDENTIALS"):
        cred = credentials.Certificate(os.environ.get("FIREBASE_CREDENTIALS"))
    else:
        cred_path = "firebase-credentials.json"
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)

    firebase_admin.initialize_app(cred, {"databaseURL": os.environ.get("FIREBASE_URL")})

    return db


def add_idea_to_firebase(user_id, title, description):
    if not firebase_admin._apps:
        initialize_firebase()

    # Get a database reference
    ref = db.reference("/ideas")

    # Create data object
    idea_data = {
        "user_id": user_id,
        "title": title,
        "description": description,
    }

    # Push data (creates a new entry with auto-generated ID)
    new_idea_ref = ref.push(idea_data)

    # Return the generated ID
    return new_idea_ref.key


# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))


@app.command("/forkthisidea")
def handle_command(ack, body, say, client):
    # Acknowledge the command request immediately
    ack()

    say(
        response_type="in_channel",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<@{body['user_id']}> invoked the command with text: {body.get('text', '')}",
                },
            }
        ],
    )

    command_text = body.get("text", "").strip()

    if command_text:
        if "|" in command_text:
            title, description = command_text.split("|", 1)
            title = title.strip()
            description = description.strip()
        else:
            title = command_text
            description = ""

        idea_id = add_idea_to_firebase(body["user_id"], title, description)

        say(
            response_type="in_channel",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<@{body['user_id']}> submitted an idea *{title}: {description}*",
                    },
                }
            ],
            text=f"<@{body['user_id']}> submitted an idea {title}: {description}",
        )

        client.chat_postEphemeral(
            user=body["user_id"],
            channel=body["channel_id"],
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Thank you <@{body['user_id']}>! Your idea has been submitted.",
                    },
                }
            ],
            text=f"Thank you <@{body['user_id']}>! Your idea has been submitted.",
        )
    else:
        client.chat_postEphemeral(
            user=body["user_id"],
            channel=body["channel_id"],
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Hello <@{body['user_id']}>! Please provide an idea with your command.",
                    },
                }
            ],
            text=f"Hello <@{body['user_id']}>! Please provide an idea with your command.",
        )


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
