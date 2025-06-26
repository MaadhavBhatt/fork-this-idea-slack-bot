# Fork This Idea (Slack Bot)

A Slack bot for submitting and voting on ideas, built with Python. Submitted ideas are stored in a Firebase database, and displayed on a web page developed [here](https://github.com/yajurrsharma/fork-this-idea).

The Slack bot component of this project is being developed under the Thunder You-Ship-We-Ship by [Hack Club](https://hackclub.com/).

I'm following the tutorial from [Slack Developer Tools](https://tools.slack.dev/bolt-python/) in the initial stages.

## MVP Features

- Submit ideas
- Vote on ideas

## Future Features

- View top ideas
- View recent ideas

## Firebase Setup

1. Create a Firebase project:

- Go to the [Firebase Console](https://console.firebase.google.com/)
- Click "Add project" and follow the setup wizard
- Enter a project name and accept the terms
- (Optional) Configure Google Analytics
- Click "Create project"

2. Create a Realtime Database:

- In your Firebase project console, click on "Build" in the left sidebar
- Select "Realtime Database"
- Click "Create Database"
- Choose a location for your database (typically the default option is fine)
- Start in test mode for development (you can update security rules later)

3. Add a service account key to your project:

- In your Firebase project console, go to Project Settings (gear icon)
- Select the "Service accounts" tab
- Click "Generate new private key" button
- Save the JSON file securely (you'll need this for your application)
- Never commit this file to version control

## Nest Setup

If you're hosting this bot on Hack Club's Nest, follow these steps:

1. Create a nest account following the instructions [here](https://guides.hackclub.app/index.php/Quickstart).
2. Connect to nest via ssh as described in the guide above.
3. Clone this repository in the `pub/` directory:

```bash
cd pub/
git clone https://github.com/MaadhavBhatt/fork-this-idea-slack-bot.git
cd ..
```

4. Move `update_repo.sh` to the root and make it executable. Use it to clone the repository automatically every time you deploy:

```bash
mv pub/fork-this-idea-slack-bot/update_repo.sh .
chmod +x update_repo.sh
```

5. Create a `.env` file in the root directory and copy the contents from `.env.example`, then fill in your Firebase and Slack credentials:

```bash
cp pub/fork-this-idea-slack-bot/.env.example .env
nano .env
```

6. Copy the example service file into the systemd directory:

```bash
cp pub/fork-this-idea-slack-bot/ftibot.service.example ~/.config/systemd/user/ftibot.service
```

7. Enable the service and check its status:

```bash
systemctl --user daemon-reload
systemctl --user enable --now ftibot.service
systemctl --user status ftibot.service
```
