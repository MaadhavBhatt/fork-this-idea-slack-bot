# User utilities
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


# Message utilities
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
