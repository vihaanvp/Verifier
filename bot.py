import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
VERIFIED_ROLE_NAME = os.getenv("VERIFIED_ROLE_NAME", "Verified")


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

        verified_role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
        if verified_role is None:
            await interaction.response.send_message(
                f"Verified role '{VERIFIED_ROLE_NAME}' is missing. Ask an admin to run /verifychannel again.",
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


async def get_or_create_verified_role(guild: discord.Guild) -> discord.Role:
    role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
    if role is None:
        role = await guild.create_role(name=VERIFIED_ROLE_NAME, reason="Role required for verification workflow.")
    return role


@bot.tree.command(name="verifychannel", description="Set this channel as the verification channel.")
@app_commands.default_permissions(manage_channels=True, manage_roles=True)
@app_commands.checks.has_permissions(manage_channels=True, manage_roles=True)
async def verifychannel(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    channel = interaction.channel
    if guild is None or not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Use this command in a server text channel.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        verified_role = await get_or_create_verified_role(guild)
        everyone = guild.default_role

        for guild_channel in guild.channels:
            if not isinstance(guild_channel, discord.abc.GuildChannel):
                continue
            if guild_channel.id == channel.id:
                await guild_channel.set_permissions(everyone, view_channel=True, send_messages=False)
                await guild_channel.set_permissions(verified_role, view_channel=True, send_messages=True)
            else:
                await guild_channel.set_permissions(everyone, view_channel=False)
                await guild_channel.set_permissions(verified_role, view_channel=True)
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
            "You need Manage Channels and Manage Roles permissions to use this command.",
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
        raise RuntimeError("DISCORD_BOT_TOKEN environment variable is required.")
    bot.run(TOKEN)
