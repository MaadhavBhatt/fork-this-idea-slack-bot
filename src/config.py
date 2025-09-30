import os
import time

ENV_VARS_CHECKED = False

COMMANDS = {
    "fetch": ["today", "<user-id>", "all", "me"],
    "count": ["<user-id>", "me"],
    "help": [],
}
CONFIG: dict = {}

# Message templates
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
            "text": "*Count ideas:*\n`/forkthisidea count [me]`\nCount ideas for yourself or others.",
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

# Emoji sets for upvotes and downvotes
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
