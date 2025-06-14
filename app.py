import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))


@app.command("/forkthisidea")
def handle_command(ack, body, say, client):
    # Acknowledge the command request immediately
    ack()

    # Get the command text
    command_text = body.get("text", "").strip()

    if command_text:
        # Separate command_text into parts before and after hyphen
        if "-" in command_text:
            title, description = command_text.split("-", 1)
            title = title.strip()
            description = description.strip()
        else:
            title = command_text
            description = ""

        # Say hello to the user who invoked the command
        say(
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


# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
