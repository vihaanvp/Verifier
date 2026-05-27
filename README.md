# Verifier

A Discord user verification bot for Discord servers.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set environment variable:
   - `DISCORD_BOT_TOKEN` (required)
   - `VERIFIED_ROLE_NAME` (optional, default: `Verified`)
3. Run the bot:
   ```bash
   python bot.py
   ```

## Usage

- Invite the bot with permissions to manage roles/channels and read/send messages.
- Run `/verifychannel` in the channel you want to use for verification.
- The bot posts an embed with a **Verify** button.
- Clicking the button assigns the verified role, which grants access to other channels.
