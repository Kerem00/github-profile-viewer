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
from datetime import datetime

BOT_TOKEN = keyring.get_password("bot", "token")
APP_ID = keyring.get_password("app", "id")

headers = {"User-Agent": "GitHub Profile Viewer", "Authorization": f"token {keyring.get_password('github', 'token')}"}
params = {"per_page": 10}

def search_github_user(username):
    if not re.match(r"^\w+$", username):
        return
    try:
        info = {}
        user = requests.get(f"https://api.github.com/users/{username}", headers=headers)
        user.raise_for_status()
        user = user.json()
        info["user"] = user
        info["repos"] = requests.get(user["repos_url"], headers=headers, params=params).json()
        info["followers"] = requests.get(user["followers_url"], headers=headers, params=params).json()
        info["following"] = requests.get(user["following_url"][0:-13], headers=headers, params=params).json()
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

class ViewButtons(discord.ui.View):
    def __init__(self, default_embed, interaction_message, info):
        super().__init__()
        self.default_embed = default_embed
        self.interaction_message = interaction_message
        self.info = info
        self.add_item(ButtonProfile())
        self.add_item(ButtonTemplate("Repos"))
        self.add_item(ButtonTemplate("Followers"))
        self.add_item(ButtonTemplate("Following"))

class ButtonProfile(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Profile")

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ViewButtons = self.view
        await view.interaction_message.edit(embed=view.default_embed)
        await interaction.response.defer()

class ButtonTemplate(discord.ui.Button):
    def __init__(self, btnlabel: str):
        super().__init__(style=discord.ButtonStyle.primary, label=btnlabel)
        self.btnlabel = btnlabel

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ViewButtons = self.view
        embed = discord.Embed(title=self.btnlabel, color=0x2f3136)
        embed.set_author(name=view.info["user"]["login"], icon_url=view.info["user"]["avatar_url"], url=view.info["user"]["html_url"])
        for i in view.info[self.btnlabel.lower()]:
            embed.add_field(name=i["name"] if i.get("name") is not None else i["login"], value=i["description"] if i.get("description") is not None else f"[Click]({i['html_url']})", inline=False)
        embed.set_footer(text=datetime.strptime(view.info["user"]["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime('Created on %d %b, %Y.'))
        await view.interaction_message.edit(embed=embed)
        await interaction.response.defer()

client = Client(intents=discord.Intents.default(), application_id=APP_ID)

@client.event
async def on_ready():
    msg_on_login = f"Logged in as {client.user} (ID: {client.user.id})"
    print(msg_on_login)
    print("_" * len(msg_on_login))
    await client.change_presence(activity=discord.Game(name="GitHub Profile Viewer"))

@client.tree.command()
@app_commands.describe(username="GitHub username.")
async def profile(interaction: discord.Interaction, username: str):
    """Show GitHub profile by username."""
    await interaction.response.defer()
    if not re.match(r"^\w+$", username):
        await interaction.edit_original_message(content="Specified username is invalid.")
        return
    info = search_github_user(username)
    if info is not None:
        embed = discord.Embed(title=info["user"]["name"], description=info["user"]["bio"], color=0x2f3136)
        embed.set_author(name=info["user"]["login"], icon_url=info["user"]["avatar_url"], url=info["user"]["html_url"])
        embed.add_field(name="Repos", value=str(info["user"]["public_repos"]))
        embed.add_field(name="Followers", value=str(info["user"]["followers"]))
        embed.add_field(name="Following", value=str(info["user"]["following"]))
        embed.set_footer(text=datetime.strptime(info["user"]["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime('Created on %d %b, %Y.'))
        await interaction.edit_original_message(embed=embed, view=ViewButtons(embed, await interaction.original_message(), info))
    else:
        await interaction.edit_original_message(content=f"'{username}' not found.")

client.run(BOT_TOKEN)
