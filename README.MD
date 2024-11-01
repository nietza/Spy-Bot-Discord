# Discord Spy Bot

Discord Spy Bot - track activity of particular users more deeply.

## Features

---

- Online/offline status tracking
- Monitor game activity
- Voice channel activity tracking
- Monitoring typing
- Saving logs to text files or sending them to a specified Discord channel

---

## Installation

```bash
git clone https://github.com/nietza/Spy-bot-discord
```

```bash
cd discord-spy-bot
```

```bash
python setup.py
```

---

## Usage

1. Run the bot:

```bash
python main.py
```

2. Use the following commands in Discord:
- `/shelp` - Show bot usage help

- `/spy [user_id] [channel_id]` - Start tracking a user
  - `user_id` - ID of the user to track (required)
  - `channel_id` - Channel ID for sending logs (optional)

## Logs

If `channel_id` is not specified when using the `/spy` command, logs will be saved to text files in the `Logs Users/[username]/logs_[date].txt` directory.

## Note

Using this bot to track users without their consent may violate Discord's terms of service and privacy laws.

