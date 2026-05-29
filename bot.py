from dotenv import load_dotenv
import logging
import os
import json

import discord
from discord import app_commands
from discord.ext import commands

load_dotenv()

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
VERIFY_SETTINGS_FILE = "verify_settings.json"

# --------------------
# UTIL: VERIFY SETTINGS MAPPING
# --------------------
def load_verify_settings():
    if os.path.isfile(VERIFY_SETTINGS_FILE):
        with open(VERIFY_SETTINGS_FILE, "r") as f:
            try:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
            except json.JSONDecodeError:
                # If corrupted, reset file
                return {}
    else:
        return {}

def save_verify_settings(data):
    with open(VERIFY_SETTINGS_FILE, "w") as f:
        json.dump(data, f)

def set_guild_verify_settings(guild_id, channel_id, role_id):
    data = load_verify_settings()
    data[str(guild_id)] = {"channel_id": channel_id, "role_id": role_id}
    save_verify_settings(data)

def get_guild_verify_settings(guild_id):
    data = load_verify_settings()
    return data.get(str(guild_id))

class VerifyView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.success, custom_id="verify:button")
    async def verify_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message("This button can only be used in a server.", ephemeral=True)
            return

        settings = get_guild_verify_settings(guild.id)
        verified_role = None
        if settings:
            role_id = settings.get("role_id")
            if role_id:
                verified_role = guild.get_role(int(role_id))
        if verified_role is None:
            await interaction.response.send_message(
                f"Verified role is missing. Ask an admin to run /verifychannel again.",
                ephemeral=True,
            )
            return

        if verified_role in member.roles:
            await interaction.response.send_message("You are already verified.", ephemeral=True)
            return

        try:
            await member.add_roles(verified_role, reason="User verified via verification button.")
        except discord.Forbidden:
            await interaction.response.send_message(
                "I couldn't assign the role. Please check my role permissions/order.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("Verification complete. You now have access.", ephemeral=True)


intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready() -> None:
    logging.info("Logged in as %s (%s)", bot.user, bot.user.id if bot.user else "unknown")

@bot.tree.command(name="verifychannel", description="Set this channel as the verification channel.")
@app_commands.describe(role="The role to use as the verified role.")
@app_commands.default_permissions(manage_guild=True)
@app_commands.checks.has_permissions(manage_guild=True)
async def verifychannel(interaction: discord.Interaction, role: discord.Role) -> None:
    guild = interaction.guild
    channel = interaction.channel
    if guild is None or not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Use this command in a server text channel.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        everyone = guild.default_role

        for guild_channel in guild.channels:
            if not isinstance(guild_channel, discord.abc.GuildChannel):
                continue
            if guild_channel.id == channel.id:
                everyone_overwrite = guild_channel.overwrites_for(everyone)
                everyone_overwrite.view_channel = True
                everyone_overwrite.send_messages = False
                if guild_channel.overwrites_for(everyone) != everyone_overwrite:
                    await guild_channel.set_permissions(everyone, overwrite=everyone_overwrite)

                verified_overwrite = guild_channel.overwrites_for(role)
                verified_overwrite.view_channel = True
                verified_overwrite.send_messages = True
                if guild_channel.overwrites_for(role) != verified_overwrite:
                    await guild_channel.set_permissions(role, overwrite=verified_overwrite)
            else:
                everyone_overwrite = guild_channel.overwrites_for(everyone)
                everyone_overwrite.view_channel = False
                if guild_channel.overwrites_for(everyone) != everyone_overwrite:
                    await guild_channel.set_permissions(everyone, overwrite=everyone_overwrite)

                verified_overwrite = guild_channel.overwrites_for(role)
                verified_overwrite.view_channel = True
                if guild_channel.overwrites_for(role) != verified_overwrite:
                    await guild_channel.set_permissions(role, overwrite=verified_overwrite)

        # Store verification channel and role ID mapping in the JSON
        set_guild_verify_settings(guild.id, channel.id, role.id)

    except discord.Forbidden:
        await interaction.followup.send(
            "I need Manage Channels and Manage Roles permissions to configure verification.",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title="Server Verification",
        description="Click **Verify** below to get access to the rest of the server.",
        color=discord.Color.green(),
    )
    await channel.send(embed=embed, view=VerifyView())
    await interaction.followup.send("Verification channel configured.", ephemeral=True)

@verifychannel.error
async def verifychannel_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(
            "You need the 'Manage Server' permission to use this command.",
            ephemeral=True,
        )
        return
    raise error

@bot.event
async def setup_hook() -> None:
    bot.add_view(VerifyView())
    await bot.tree.sync()

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN environment variable is required. "
            "Set it to your bot token from https://discord.com/developers/applications"
        )
    bot.run(TOKEN)