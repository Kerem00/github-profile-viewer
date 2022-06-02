#   GitHub Profile Viewer - Discord bot for viewing GitHub profiles by slash commands.
#   Copyright (C) 2022  Kerem Biçen

#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.

#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

import re
import requests
import keyring
import discord
from discord import app_commands

BOT_TOKEN = keyring.get_password("bot", "token")
APP_ID = keyring.get_password("app", "id")

def search_github_user(username):
    if not re.match(r"^\w+$", username):
        return
    try:
        info = {}
        user = requests.get(f"https://api.github.com/users/{username}")
        user.raise_for_status()
        user = user.json()
        info["user"] = user
        info["repos"] = requests.get(user["repos_url"]).json()
        info["followers"] = requests.get(user["followers_url"]).json()
        info["following"] = requests.get(user["following_url"]).json()
        return info
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return

class Client(discord.Client):
    def __init__(self, *, intents: discord.Intents, application_id: int):
        super().__init__(intents=intents, application_id=application_id)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = Client(intents=discord.Intents.default(), application_id=APP_ID)

@client.event
async def on_ready():
    msg_on_login = f"Logged in as {client.user} (ID: {client.user.id})"
    print(msg_on_login)
    print("_" * len(msg_on_login))
    await client.change_presence(activity=discord.Game(name="GitHub"))

@client.tree.command()
@app_commands.describe(username="GitHub  username.")
async def profile(interaction: discord.Interaction, username: str):
    """Show GitHub profile by username."""
    if not re.match(r"^\w+$", username):
        await interaction.response.send_message(content="Specified username is invalid.")
        return
    info = search_github_user(username)
    if info is not None:
        embed = discord.Embed(title=info["user"]["name"], description=info["user"]["bio"], color=0x2f3136)
        embed.set_author(name=info["user"]["login"], icon_url=info["user"]["avatar_url"], url=info["user"]["html_url"])
        embed.add_field(name="Repos", value=str(info["user"]["public_repos"]))
        embed.add_field(name="Followers", value=str(info["user"]["followers"]))
        embed.add_field(name="Following", value=str(info["user"]["following"]))
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(content=f"'{username}' not found.")

client.run(BOT_TOKEN)
