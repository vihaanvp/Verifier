# Verifier

A Discord user verification bot for Discord servers.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set environment variable (see `.env.example` file for more information):
   - `DISCORD_BOT_TOKEN` (required)
3. Run the bot:
   ```bash
   python bot.py
   ```

## Usage

- Invite the bot with permissions integer `268520464` and `bot` and `application.commands` Scopes
- Run `/verifychannel` in the channel you want to use for verification, and also mention the "Verified role in the required command parameter"
- The bot posts an embed with a **Verify** button.
- Clicking the button assigns the verified role that you chose, which grants access to other channels if the roles are set up correctly.
