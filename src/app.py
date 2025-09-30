import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .config import check_environment_variables
from .handlers import handle_slash_command, handle_message, handle_reaction


# Initialize the app with the bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Register the message handler for PI prefixed messages
app.message(re.compile(r"^[Pp][Ii]:?\s+"))(handle_message)

# Register the slash command handler
app.command("/forkthisidea")(handle_slash_command)

# Register the reaction handler for both added and removed reactions
app.event("reaction_added")(handle_reaction)
app.event("reaction_removed")(handle_reaction)


if __name__ == "__main__":
    check_environment_variables()
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
