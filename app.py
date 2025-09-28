import os
import time
from typing import Optional
from itertools import chain
from math import ceil
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import firebase_admin
from firebase_admin import credentials, db

ENV_VARS_CHECKED = False

COMMANDS = {
    "fetch": ["today", "<user-id>", "all", "me"],
    "count": ["<user-id>", "me"],
    "help": [],
}
CONFIG: dict = {}
WELCOME_MESSAGE = lambda channel_name: (
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"Hello, people of {channel_name}! I'm the Fork This Idea app.\n"
            "You can submit your ideas using the command 'PI: <title> | <description>'.\n"
            "You can use /forkthisidea for more commands.\n"
            "For more information, type '/forkthisidea help'.",
        },
    }
)
HELP_MESSAGE = lambda user_id: [
    {
        "type": "header",
        "text": {"type": "plain_text", "text": "Fork This Idea - Help", "emoji": True},
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"Hello <@{user_id}>! Here are the available commands:",
        },
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*Submit an idea:*\n`PI: <title> | <description>`\nYou can use 'Pi:' and 'pi:' as well.",
        },
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*Fetch ideas:*\n`/forkthisidea fetch [today|all|me]`\nRetrieve ideas by different criteria.",
        },
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*Count ideas:*\n`/forkthisidea count [me|@user]`\nCount ideas for yourself or others.",
        },
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*Example:*\n`PI: My Idea | This is a description of my idea.`",
        },
    },
    {
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": "Ever need help? Type `/forkthisidea help`"}
        ],
    },
]
INVALID_COMMAND = lambda user_id: (
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"Hi <@{user_id}>! That was an invalid command. Please use one of the following commands:\n"
            "- '/forkthisidea fetch [today|all|me]': Fetch ideas by different criteria\n"
            "- '/forkthisidea count [me]': Count ideas for yourself or others\n"
            "- '/forkthisidea help': See detailed help information\n"
            "Type '/forkthisidea help' for more information.",
        },
    }
)
IDEA_SUBMISSION_DETAILS = lambda user_id, title, description, timestamp: (
    f"<@{user_id}> submitted an idea *{title}: {description}* at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(timestamp))}"
)
IDEA_SUBMISSION_SUCCESS = lambda user_id: (
    f"Thank you <@{user_id}>! Your idea has been submitted."
)
IDEA_SUBMISSION_EMPTY = lambda user_id: (
    f"Hello <@{user_id}>! Please provide an idea with your command."
)
IDEA_DETAILS = lambda idea: (
    [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{idea.get('title')}",
                "emoji": True,
            },
            "block_id": f"header_block_{idea.get('id')}",
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{idea.get('description')}",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Submitted by <@{idea.get('user_id')}> "
                    f"on {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(idea.get('timestamp')))} "
                    f"with {idea.get('votes')['upvotes']} upvotes and {idea.get('votes')['downvotes']} downvotes",
                }
            ],
        },
        {
            "type": "actions",
            "block_id": f"link_action_block_{idea.get('id')}",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": f"{(idea.get('title') or 'Untitled').split()[0]} ...",
                    },
                    "url": "https://google.com",  # TODO: Link to the site with a query parameter for the idea ID
                    "action_id": f"action_{idea.get('id')}",
                },
            ],
        },
        {"type": "divider"},
    ]
)

UPVOTE_EMOJIS: set[str] = {
    "thumbsup",
    "heart",
    "saluting_face",
    "star",
    # Upvotes
    "upvote",
    "double-upvote",
    "upvote5",
    "upvote3",
    "8bit-upvote",
    "super-mega-upvote",
}
DOWNVOTE_EMOJIS: set[str] = {
    "thumbsdown",
    # Downvotes
    "downvote",
    "downdoot",
    "downvote2",
    "downvote3",
    "downvotex",
    "downvote-red",
    "double-downvote",
}


def check_environment_variables() -> None:
    """
    Checks if the required environment variables are set for the application.

    Raises:
        ValueError: If any of the required environment variables are not set or if the Firebase credentials file does not exist.

    This function checks for the following environment variables:
        - SLACK_BOT_TOKEN: The token for the Slack bot.
        - SLACK_APP_TOKEN: The token for the Slack app.
        - FIREBASE_URL: The URL for the Firebase Realtime Database.
        - FIREBASE_CREDENTIALS_PATH: The path to the Firebase credentials JSON file.
    """
    required_vars = [
        "SLACK_BOT_TOKEN",
        "SLACK_APP_TOKEN",
        "FIREBASE_URL",
        "FIREBASE_CREDENTIALS_PATH",
    ]

    optional_vars = [
        "SEND_CHANNEL_MESSAGE_ON_SUBMISSIONS",
    ]

    for var in required_vars:
        if os.environ.get(var) is None:
            raise ValueError(f"{var} environment variable is not set.")

    if not os.path.exists(os.environ.get("FIREBASE_CREDENTIALS_PATH")):
        raise ValueError(
            "Firebase credentials file not found at path given by FIREBASE_CREDENTIALS_PATH environment variable."
        )

    global CONFIG
    for var in optional_vars:
        if os.environ.get(var) is None:
            os.environ[var] = "false"
            print(
                f"Optional environment variable {var} is not set. Defaulting to false."
            )
        CONFIG[var.lower()] = os.environ.get(var).lower() == "true"

    global ENV_VARS_CHECKED
    ENV_VARS_CHECKED = True


def initialize_firebase() -> db:
    """
    Initializes Firebase Realtime Database connection using the credentials and URL from environment variables.
    Checks if the required environment variables are set before initialization.

    Returns:
        db: A reference to the Firebase Realtime Database.
    """
    if not ENV_VARS_CHECKED:
        check_environment_variables()

    cred = credentials.Certificate(os.environ.get("FIREBASE_CREDENTIALS_PATH"))
    firebase_admin.initialize_app(cred, {"databaseURL": os.environ.get("FIREBASE_URL")})

    return db


def add_idea_to_firebase(
    user_id, user_name, title, description, timestamp=int(time.time())
) -> str:
    """
    Adds an idea to Firebase Realtime Database. Initializes Firebase if not already initialized.

    Args:
        user_id (str): The ID of the user submitting the idea.
        user_name (str): The name of the user submitting the idea.
        title (str): The title of the idea.
        description (str): The description of the idea.
        timestamp (int, optional): The timestamp of the idea submission. Defaults to the current time.

    Returns:
        str: The ID of the newly created idea entry in Firebase.
    """
    if not firebase_admin._apps:
        initialize_firebase()

    # Get a database reference
    ref = db.reference("/ideas")

    # Create data object
    idea_data = {
        "user_id": user_id,
        "user_name": user_name,
        "title": title,
        "description": description,
        "timestamp": timestamp,
        "votes": {
            "upvotes": 0,
            "downvotes": 0,
        },
    }

    # Push data (creates a new entry with auto-generated ID)
    new_idea_ref = ref.push(idea_data)

    # Return the generated ID
    return new_idea_ref.key


def get_idea_from_firebase(idea_id) -> dict:
    """
    Retrieves an idea from Firebase by its ID. Initializes Firebase if not already initialized.

    Args:
        idea_id (str): The ID of the idea to retrieve.

    Returns:
        dict: A dictionary containing the idea's details, or None if the idea does not exist.
    """
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
        "timestamp": idea_data.get("timestamp", None),
        "votes": idea_data.get("votes", {"upvotes": 0, "downvotes": 0}),
    }


def get_all_ideas_from_firebase() -> list:
    """
    Retrieves all ideas from Firebase. Initializes Firebase if not already initialized.

    Returns:
        list: A list of all ideas, each represented as a dictionary with keys
    """
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
                "timestamp": idea.get("timestamp", None),
                "votes": idea.get("votes", {"upvotes": 0, "downvotes": 0}),
            }
        )

    return ideas_list


def get_ideas_by_user_from_firebase(user_id) -> list:
    """
    Retrieves all ideas submitted by a specific user from Firebase.
    Initializes Firebase if not already initialized.

    Args:
        user_id (str): The user ID to filter ideas by.

    Returns:
        list: A list of ideas submitted by the specified user.
    """
    if not firebase_admin._apps:
        initialize_firebase()

    return [
        idea for idea in get_all_ideas_from_firebase() if idea["user_id"] == user_id
    ]


def get_ideas_by_time_range_from_firebase(
    start_timetime, end_time=ceil(time.time())
) -> list:
    """
    Retrieves ideas submitted within a specific time range from Firebase.
    Initializes Firebase if not already initialized.

    Args:
        start_timetime (int): The start timestamp for filtering ideas.
        end_time (int, optional): The end timestamp for filtering ideas. Defaults to the current time.

    Returns:
        list: A list of ideas that fall within the specified time range.
    """
    if not firebase_admin._apps:
        initialize_firebase()

    # Get all ideas
    ideas = get_all_ideas_from_firebase()
    # Filter ideas by timestamp
    filtered_ideas = [
        idea for idea in ideas if start_timetime <= idea.get("timestamp", 0) <= end_time
    ]
    return filtered_ideas


def get_idea_count_from_firebase(user_id=None) -> int:
    """
    Retrieves the count of ideas submitted by a user or all ideas if no user ID is provided.
    Initializes Firebase if not already initialized.

    Args:
        user_id (str, optional): The user ID to filter ideas by. If None, it counts all ideas.

    Returns:
        int: The count of ideas.
    """
    if not firebase_admin._apps:
        initialize_firebase()

    if user_id:
        ideas = get_ideas_by_user_from_firebase(user_id)
    else:
        ideas = get_all_ideas_from_firebase()
    return len(ideas)


def parse_idea_from_message_text(message_text) -> tuple[str, str]:
    """
    Parses the message text to extract the title and description of an idea.
    The expected format is "PI: Title | Description" or "PI Title | Description".
    If the message starts with "PI:" or "PI", it will be stripped off, and the rest will be processed.
    If the message does not contain a pipe ("|"), the entire message will be treated as the title,
    and the description will be an empty string. Otherwise, the part before the pipe will be the title,
    and the part after the pipe will be the description.

    Args:
        message_text (str): The message text to parse.

    Returns:
        tuple[str, str]: A tuple containing the title and description of the idea.
    """
    if message_text.upper().startswith("PI:"):
        message_text = message_text[3:].strip()
    elif message_text.upper().startswith("PI"):
        message_text = message_text[2:].strip()

    if "|" in message_text:
        title, description = message_text.split("|", 1)
        title = title.strip()
        description = description.strip()
    else:
        title = message_text
        description = ""

    return title, description


def get_user_name_from_id(client, user_id) -> str:
    """
    Fetches the display name or real name of a user from Slack using their user ID.

    Args:
        client: Slack client instance.
        user_id (str): The user ID to fetch the name for.

    Returns:
        str: The display name or real name of the user, or the user ID if not found.
    """
    try:
        result = client.users_info(user=user_id)
        user = result["user"]
        display_name = user.get("profile", {}).get("display_name", "")
        real_name = user.get("profile", {}).get("real_name", "")
        return display_name if display_name else real_name or user_id
    except Exception as e:
        print(f"Error fetching user info for {user_id}: {e}")
        return user_id


def update_votes(
    idea_id: str,
    votes: Optional[tuple[int]] = None,
    votes_change: Optional[tuple[int]] = None,
) -> bool:
    """
    Updates the vote count for a specific idea in Firebase by the specified amount.
    Validates the input to ensure that either `votes` or `votes_change` is provided, but not both.
    Initializes Firebase if not already initialized.

    Args:
        idea_id (str): The ID of the idea to update votes for.
        votes (Optional[tuple[int]]): A tuple containing the new upvotes and downvotes.
            If provided, it will replace the current votes.
        votes_change (Optional[tuple[int]]): A dictionary containing the change in upvotes and downvotes.
            If provided, it will update the current votes by the specified amounts.
        If neither is provided, a ValueError will be raised.
        If both are provided, a ValueError will be raised.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    if votes is None and votes_change is None:
        raise ValueError("Either 'votes' or 'votes_change' must be provided.")
    elif votes is not None and votes_change is not None:
        raise ValueError("Only one of 'votes' or 'votes_change' can be provided.")

    if not firebase_admin._apps:
        initialize_firebase()

    idea_ref = db.reference(f"/ideas/{idea_id}")
    idea_data = idea_ref.get()

    if idea_data is None:
        return False

    if votes:
        upvotes, downvotes = votes
    elif votes_change:
        upvotes = idea_data["votes"].get("upvotes", 0) + votes_change[0]
        downvotes = idea_data["votes"].get("downvotes", 0) + votes_change[1]

    # Update the votes count by the specified amount
    new_votes = {
        "upvotes": upvotes,
        "downvotes": downvotes,
    }
    idea_ref.update({"votes": new_votes})
    return True


def sort_and_limit_ideas(ideas, limit=10, reverse=True) -> list:
    """
    Sorts the ideas by timestamp and limits the number of ideas returned.

    Args:
        ideas (list): List of ideas to sort.
        limit (int): Maximum number of ideas to return.
        reverse (bool): Whether to sort in descending order.

    Returns:
        list: Sorted and limited list of ideas.
    """
    if not ideas:
        return []

    if len(ideas) > 1:
        ideas = sorted(ideas, key=lambda x: x["timestamp"], reverse=reverse)

    if len(ideas) > limit:
        ideas = ideas[:limit]

    return ideas


def create_message_blocks(message=None, blocks=None):
    """
    Creates a list of message blocks for Slack messages.
    If both 'message' and 'blocks' are provided, it raises a ValueError.
    If neither is provided, it raises a ValueError.

    Args:
        message (str): The message text to include in the blocks.
        blocks (list): A list of blocks to include in the message.

    Returns:
        list: A list of blocks to be used in a Slack message.
    """
    if message and blocks:
        raise ValueError("Either 'message' or 'blocks' must be provided, but not both.")
    elif not message and not blocks:
        raise ValueError(
            "Either 'message' or 'blocks' must be provided. Both cannot be empty."
        )

    if blocks is None:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{message}",
                },
            }
        ]
    elif isinstance(blocks, dict):
        blocks = [blocks]

    return blocks


def send_ephemeral_message(
    client, user_id, channel_id, blocks=None, message=None, thread_ts=None
):
    """
    Sends an ephemeral message visible only to the specified user in a Slack channel.

    An ephemeral message is visible only to the user specified and not to other users
    in the channel.

    Args:
        client: The Slack client instance used to send the message.
        user_id (str): The ID of the user who will see the ephemeral message.
        channel_id (str): The ID of the channel where the message is sent.
        blocks (list, optional): Predefined blocks for structured message content.
            If not provided but message is, blocks will be created from the message.
        message (str, optional): Text content of the message.
        thread_ts (str, optional): Timestamp of the thread to send the message in.
            If omitted, the message will not be sent in a thread.

    Returns:
        None
    """
    blocks = create_message_blocks(message, blocks)
    client.chat_postEphemeral(
        user=user_id,
        channel=channel_id,
        thread_ts=thread_ts,
        blocks=blocks,
        text=f"{message}",
    )


def send_channel_message(client, channel_id, blocks=None, message=None, thread_ts=None):
    """
    Sends a message to a Slack channel.

    Args:
        client: The Slack client instance used to send the message.
        channel_id (str): The ID of the channel where the message is sent.
        blocks (list, optional): Predefined blocks for structured message content.
            If not provided but message is, blocks will be created from the message.
        message (str, optional): Text content of the message.
        thread_ts (str, optional): Timestamp of the thread to send the message in.
            If omitted, the message will not be sent in a thread.

    Returns:
        None
    """
    blocks = create_message_blocks(message, blocks)
    client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        blocks=blocks,
        text=message,
    )


def handle_command(parts, user_id, client, channel_id, thread_ts=None):
    def _fetch(limit=5):
        if subcommand not in COMMANDS["fetch"]:
            return INVALID_COMMAND(user_id)

        if subcommand == "today":
            ideas = get_ideas_by_time_range_from_firebase(
                start_timetime=int(time.time() - 24 * 60 * 60),
                end_time=ceil(time.time()),
            )

        elif subcommand == "all":
            ideas = get_all_ideas_from_firebase()

        elif subcommand == "me":
            ideas = get_ideas_by_user_from_firebase(user_id)

        elif subcommand.startswith("<@") and subcommand.endswith(">"):
            user_id_to_fetch = subcommand[2:-1]
            ideas = get_ideas_by_user_from_firebase(user_id_to_fetch)

        ideas = sort_and_limit_ideas(ideas, limit=limit, reverse=True)
        return ideas

    def _count():
        if subcommand.startswith("<@") and subcommand.endswith(">"):
            user_id_to_count = subcommand[2:-1]
            ideas_count = get_idea_count_from_firebase(user_id_to_count)
            return f"<@{user_id_to_count}> has submitted {ideas_count} ideas."

        elif subcommand == "me":
            ideas_count = get_idea_count_from_firebase(user_id)
            return f"You have submitted {ideas_count} ideas."

        else:
            ideas_count = get_idea_count_from_firebase()
            return f"There are a total of {ideas_count} ideas submitted."

    # If no command is provided, send an ephemeral message to the user
    if not len(parts) > 0:
        send_ephemeral_message(
            client=client,
            user_id=user_id,
            channel_id=channel_id,
            blocks=INVALID_COMMAND(user_id),
        )
        return

    command = parts[0]
    subcommand = parts[1] if len(parts) > 1 else ""

    # If the command or the subcommand is not valid, send an ephemeral message to the user
    # FIX: This doesn't handle user IDs.
    if command not in COMMANDS or (subcommand and subcommand not in COMMANDS[command]):
        send_ephemeral_message(
            client=client,
            user_id=user_id,
            channel_id=channel_id,
            blocks=INVALID_COMMAND(user_id),
            thread_ts=thread_ts,
        )
        return

    if command == "fetch":
        response = list(chain.from_iterable(IDEA_DETAILS(idea) for idea in _fetch()))
    elif command == "count":
        response = _count()
    elif command == "help":
        response = HELP_MESSAGE(user_id)
    else:
        response = INVALID_COMMAND(user_id)

    send_ephemeral_message(
        client=client,
        user_id=user_id,
        channel_id=channel_id,
        blocks=response if isinstance(response, (dict, list)) else None,
        message=response if isinstance(response, str) else None,
        thread_ts=thread_ts,
    )


def handle_slash_command(ack, body, client):
    ack()

    user_id = body.get("user_id", "unknown_user")
    channel_id = body.get("channel_id", "unknown_channel")
    thread_ts = body.get("thread_ts")
    command_text = body.get("text", "").strip()

    parts = command_text.split()
    parts = [part.lower().strip() for part in parts if part.strip()]

    handle_command(parts, user_id, client, channel_id, thread_ts)


def handle_message(ack, body, client):
    # Acknowledge the command request immediately
    ack()

    user_id = body.get("user_id") or body["event"].get("user", "unknown_user")
    channel_id = body.get("channel_id") or body["event"].get(
        "channel", "unknown_channel"
    )
    thread_ts = body.get("thread_ts") or body["event"].get("ts", None)
    message_text = body.get("text", "").strip() or body["event"].get("text", "").strip()
    timestamp = int(float(body["event"].get("ts", time.time())))

    if message_text:
        title, description = parse_idea_from_message_text(message_text)
        user_name = get_user_name_from_id(client, user_id)
        add_idea_to_firebase(user_id, user_name, title, description, timestamp)

        # Send a message to the channel with the idea submission
        if CONFIG.get("send_channel_message_on_submissions"):
            send_channel_message(
                client=client,
                channel_id=channel_id,
                message=IDEA_SUBMISSION_DETAILS(user_id, title, description, timestamp),
                thread_ts=thread_ts,
            )

        # Send an ephemeral message to the user who submitted the idea
        send_ephemeral_message(
            client=client,
            user_id=user_id,
            channel_id=channel_id,
            message=IDEA_SUBMISSION_SUCCESS(user_id),
            thread_ts=thread_ts,
        )
    else:
        # If no command text is provided, send an ephemeral message to the user
        send_ephemeral_message(
            client=client,
            user_id=user_id,
            channel_id=channel_id,
            message=IDEA_SUBMISSION_EMPTY(user_id),
            thread_ts=thread_ts,
        )


def handle_reaction(ack, body, client):
    ack()

    event = body["event"]
    reaction = event.get("reaction", "")
    user_id = event.get("user", "unknown_user")
    item = event.get("item", {})

    if item.get("type") != "message":
        return

    channel_id = item.get("channel")
    message_ts = item.get("ts")

    # If the reaction is not an upvote or downvote, ignore it
    if reaction not in UPVOTE_EMOJIS and reaction not in DOWNVOTE_EMOJIS:
        return

    sign = 1 if event["type"] == "reaction_added" else -1

    try:
        # Get the message that was reacted to
        # Read https://api.slack.com/methods/conversations.history#single-message for details
        result = client.conversations_history(
            channel=channel_id, oldest=message_ts, inclusive=True, limit=1
        )

        if not result["messages"]:
            return

        message = result["messages"][0]
        message_text = message.get("text", "")
        timestamp = int(float(message.get("ts", None)))

        if not message_text.upper().startswith(
            "PI:"
        ) and not message_text.upper().startswith("PI"):
            return

        ideas = get_ideas_by_time_range_from_firebase(
            start_timetime=timestamp, end_time=timestamp
        )
        if not ideas:
            return

        idea_id = ideas[0]["id"]
        assert ideas[0]["user_id"] == user_id, "User ID mismatch for idea submission."
        assert (
            ideas[0]["title"],
            ideas[0]["description"],
        ) == parse_idea_from_message_text(
            message_text
        ), "Title and description mismatch for idea submission."

        # Update votes based on reaction
        if reaction in UPVOTE_EMOJIS:
            update_votes(idea_id, votes_change=(1 * sign, 0))
        elif reaction in DOWNVOTE_EMOJIS:
            update_votes(idea_id, votes_change=(0, 1 * sign))

    except Exception as e:
        print(f"Error handling reaction: {e}")


# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Register the message handler for PI prefixed messages
app.message("PI:")(handle_message)
app.message("Pi:")(handle_message)
app.message("pi:")(handle_message)
app.message("pI:")(handle_message)

app.command("/forkthisidea")(handle_slash_command)

app.event("reaction_added")(handle_reaction)
app.event("reaction_removed")(handle_reaction)


if __name__ == "__main__":
    if not ENV_VARS_CHECKED:
        check_environment_variables()
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
