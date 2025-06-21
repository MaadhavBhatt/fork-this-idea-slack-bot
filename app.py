import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import firebase_admin
from firebase_admin import credentials, db

ENV_VARS_CHECKED = False

# SUBCOMMANDS = {
#     "fetch": ["recent", "<user-id>", "all"],
#     "count": ["<user-id>"],
#     "help": [],
# }
SUBCOMMANDS = {
    "fetch": None,
    "count": None,
    "help": None,
}
INVALID_COMMAND = lambda user_id: (
    f"Hi {user_id}! That was an invalid command. Please use one of the following commands: "
    + ", ".join(SUBCOMMANDS.keys())
)
IDEA_SUBMISSION_DETAILS = lambda user_id, title, description: (
    f"<@{user_id}> submitted an idea *{title}: {description}*"
)
IDEA_SUBMISSION_SUCCESS = lambda user_id: (
    f"Thank you <@{user_id}>! Your idea has been submitted."
)
IDEA_SUBMISSION_EMPTY = lambda user_id: (
    f"Hello <@{user_id}>! Please provide an idea with your command."
)
HELP_MESSAGE = lambda user_id: (
    f"Hello <@{user_id}>! Here are the available commands:\n"
    f"- 'PI: <title> | <description>' to submit an idea. You can use 'Pi:' and 'pi:' as well.\n"
    f"- '/forkthisidea fetch' to fetch the most recent idea.\n"
    f"- '/forkthisidea count' to get the count of ideas submitted by you.\n"
    f"- '/forkthisidea help' to see this help message.\n"
    f"Make sure to use the correct format for your ideas. For example: 'PI: My Idea | This is a description of my idea.'"
    f"If you need help, just type '/forkthisidea help'."
)


def check_environment_variables():
    required_vars = [
        "SLACK_BOT_TOKEN",
        "SLACK_APP_TOKEN",
        "FIREBASE_URL",
        "FIREBASE_CREDENTIALS_PATH",
    ]

    for var in required_vars:
        if os.environ.get(var) is None:
            raise ValueError(f"{var} environment variable is not set.")

    if not os.path.exists(os.environ.get("FIREBASE_CREDENTIALS_PATH")):
        raise ValueError(
            "Firebase credentials file not found at path given by FIREBASE_CREDENTIALS_PATH environment variable."
        )

    global ENV_VARS_CHECKED
    ENV_VARS_CHECKED = True


def initialize_firebase():
    if not ENV_VARS_CHECKED:
        check_environment_variables()

    cred = credentials.Certificate(os.environ.get("FIREBASE_CREDENTIALS_PATH"))
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


def get_idea_from_firebase(idea_id):
    if not firebase_admin._apps:
        initialize_firebase()

    # Get a database reference
    ref = db.reference(f"/ideas/{idea_id}")

    # Retrieve the idea data
    idea_data = ref.get()

    if idea_data is None:
        return None

    return {
        "id": idea_id,
        "user_id": idea_data["user_id"],
        "title": idea_data["title"],
        "description": idea_data["description"],
    }


def get_all_ideas_from_firebase():
    if not firebase_admin._apps:
        initialize_firebase()

    # Get a database reference
    ref = db.reference("/ideas")

    # Retrieve all ideas
    ideas_data = ref.get()

    if ideas_data is None:
        return []

    # Convert to list of dictionaries
    ideas_list = []
    for idea_id, idea in ideas_data.items():
        ideas_list.append(
            {
                "id": idea_id,
                "user_id": idea["user_id"],
                "title": idea["title"],
                "description": idea["description"],
            }
        )

    return ideas_list


def get_ideas_by_user_from_firebase(user_id):
    if not firebase_admin._apps:
        initialize_firebase()

    return [
        idea for idea in get_all_ideas_from_firebase() if idea["user_id"] == user_id
    ]


def get_idea_count_from_firebase(user_id=None):
    if not firebase_admin._apps:
        initialize_firebase()

    if user_id:
        ideas = get_ideas_by_user_from_firebase(user_id)
    else:
        ideas = get_all_ideas_from_firebase()
    return len(ideas)


def extract_idea_from_command(command_text):
    if command_text.upper().startswith("PI:"):
        command_text = command_text[3:].strip()
    elif command_text.upper().startswith("PI"):
        command_text = command_text[2:].strip()

    if "|" in command_text:
        title, description = command_text.split("|", 1)
        title = title.strip()
        description = description.strip()
    else:
        title = command_text
        description = ""

    return title, description


# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))


def send_ephemeral_message(client, user_id, channel_id, message, thread_ts=None):
    client.chat_postEphemeral(
        user=user_id,
        channel=channel_id,
        thread_ts=thread_ts,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{message}",
                },
            }
        ],
        text=f"{message}",
    )


def send_channel_message(client, channel_id, message, thread_ts=None):
    client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{message}",
                },
            }
        ],
        text=message,
    )


def handle_subcommand(subcommand, user_id, client, channel_id, thread_ts=None):
    message = ""
    if subcommand == "fetch":
        # Fetch the most recent idea
        ideas = get_all_ideas_from_firebase()
        if ideas:
            latest_idea = ideas[-1]
            message = (
                f"Latest idea: *{latest_idea['title']}* - {latest_idea['description']}"
            )

        else:
            message = "No ideas found."
    elif subcommand == "count":
        # Count the number of ideas submitted by the user
        ideas_count = get_idea_count_from_firebase(user_id)
        message = f"You have submitted {ideas_count} ideas."
    elif subcommand == "help":
        # Provide help message
        message = HELP_MESSAGE(user_id)
    else:
        # Invalid subcommand
        message = INVALID_COMMAND(user_id)

    client.chat_postEphemeral(
        user=user_id,
        channel=channel_id,
        thread_ts=thread_ts,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{message}",
                },
            }
        ],
        text=message,
    )


@app.command("/forkthisidea")
def handle_command(ack, body, client):
    ack()

    user_id = body.get("user_id", "unknown_user")
    channel_id = body.get("channel_id", "unknown_channel")
    thread_ts = body.get("thread_ts")
    command_text = body.get("text", "").strip()

    # Check if the command text starts with a valid subcommand
    parts = command_text.split()

    if not len(parts) > 0:
        # If no subcommand is provided, send an ephemeral message to the user
        send_ephemeral_message(client, user_id, channel_id, INVALID_COMMAND(user_id))
        return

    subcommand = parts[0].lower().strip()
    handle_subcommand(subcommand, user_id, client, channel_id, thread_ts)


def handle_message(ack, body, say, client):
    # Acknowledge the command request immediately
    ack()

    user_id = body.get("user_id") or body["event"].get("user", "unknown_user")
    channel_id = body.get("channel_id") or body["event"].get(
        "channel", "unknown_channel"
    )
    thread_ts = body.get("thread_ts")
    command_text = body.get("text", "").strip() or body["event"].get("text", "").strip()

    if command_text:
        title, description = extract_idea_from_command(command_text)
        add_idea_to_firebase(user_id, title, description)

        # Send a message to the channel with the idea submission
        send_channel_message(
            client,
            channel_id,
            IDEA_SUBMISSION_DETAILS(user_id, title, description),
            thread_ts,
        )

        # Send an ephemeral message to the user who submitted the idea
        send_ephemeral_message(
            client,
            user_id,
            channel_id,
            IDEA_SUBMISSION_SUCCESS(user_id),
            thread_ts,
        )
    else:
        # If no command text is provided, send an ephemeral message to the user
        send_ephemeral_message(
            client,
            user_id,
            channel_id,
            IDEA_SUBMISSION_EMPTY(user_id),
            thread_ts,
        )


# Register the command handler for the /forkthisidea command and PI prefixed messages
app.message("PI:")(handle_message)
app.message("Pi:")(handle_message)
app.message("pi:")(handle_message)


if __name__ == "__main__":
    if not ENV_VARS_CHECKED:
        check_environment_variables()
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
