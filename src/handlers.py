import time
from math import ceil
from itertools import chain

from .firebase_service import (
    add_idea_to_firebase,
    get_all_ideas_from_firebase,
    get_ideas_by_user_from_firebase,
    get_ideas_by_time_range_from_firebase,
    get_idea_count_from_firebase,
    update_votes,
)
from .config import (
    COMMANDS,
    CONFIG,
    INVALID_COMMAND,
    IDEA_DETAILS,
    HELP_MESSAGE,
    IDEA_SUBMISSION_DETAILS,
    IDEA_SUBMISSION_SUCCESS,
    IDEA_SUBMISSION_EMPTY,
    UPVOTE_EMOJIS,
    DOWNVOTE_EMOJIS,
)
from .slack_utils import (
    send_ephemeral_message,
    send_channel_message,
    get_user_name_from_id,
)
from .utils import parse_idea_from_message_text, sort_and_limit_ideas


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
