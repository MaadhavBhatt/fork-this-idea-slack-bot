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
