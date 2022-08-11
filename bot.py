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

import os
import re
import copy
import math
import requests
import discord
from discord import app_commands
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_ID = int(os.getenv("APP_ID"))

headers = {"User-Agent": "GitHub Profile Viewer", "Authorization": f"token {os.getenv('GITHUB_TOKEN')}"}
per_page = 5

def search_github_user(username):
    if not re.match(r"^[\w-]+$", username):
        return
    try:
        info = requests.get(f"https://api.github.com/users/{username}", headers=headers)
        info.raise_for_status()
        return info.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return

def get_lists(url, page):
    return requests.get(url, headers=headers, params={"per_page": per_page, "page": page}).json()

def add_fields(embed, url, page):
    embed.clear_fields()
    for i in get_lists(url, page):
        embed.add_field(name=f"{i['name']} {'(Fork)' if i['fork'] == True else ''}" if i.get("name") is not None else i["login"], value=i["description"] if i.get("description") is not None else f"[Click]({i['html_url']})", inline=False)

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
        self.add_item(ButtonTemplate("Repos"))
        self.add_item(ButtonTemplate("Followers"))
        self.add_item(ButtonTemplate("Following"))
        self.add_item(ButtonClose())

class ViewPages(discord.ui.View):
    def __init__(self, default_embed, default_view):
        super().__init__()
        self.default_embed = default_embed
        self.default_view = default_view
        self.page = 1
        self.max_page = math.ceil(default_view.info[default_embed.title.lower().replace("repos", "public_repos")] / per_page)
        self.add_item(ButtonNavigation("Previous", True, False))
        self.add_item(ButtonPageNumber())
        self.add_item(ButtonNavigation("Next", self.max_page <= 1, True))
        self.add_item(ButtonGoBack())

class ButtonClose(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Close")

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ViewButtons = self.view
        await view.interaction_message.delete()
        await interaction.response.defer()

class ButtonGoBack(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Go Back")

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ViewPages = self.view
        await view.default_view.interaction_message.edit(embed=view.default_view.default_embed, view=view.default_view)
        await interaction.response.defer()

class ButtonTemplate(discord.ui.Button):
    def __init__(self, btnlabel: str):
        super().__init__(style=discord.ButtonStyle.primary, label=btnlabel)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ViewButtons = self.view
        embed = copy.deepcopy(view.default_embed)
        embed.title = self.label
        embed.description = None
        add_fields(embed, view.info[f"{self.label.lower()}_url"].replace("{/other_user}", ""), 1)
        await view.interaction_message.edit(embed=embed, view=ViewPages(embed, view))
        await interaction.response.defer()

class ButtonPageNumber(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="1")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

class ButtonNavigation(discord.ui.Button):
    def __init__(self, btnlabel: str, btndisabled: bool, btnforward: bool):
        super().__init__(style=discord.ButtonStyle.primary, label=btnlabel, disabled=btndisabled)
        self.btnforward = btnforward

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ViewPages = self.view

        if self.btnforward:
            view.page += 1
        else:
            view.page -= 1
        
        add_fields(view.default_embed, view.default_view.info[f"{view.default_embed.title.lower()}_url"].replace("{/other_user}", ""), view.page)
        view.children[0].disabled = view.page == 1
        view.children[2].disabled = view.page == view.max_page
        view.children[1].label = str(view.page)
        await view.default_view.interaction_message.edit(embed=view.default_embed, view=view)
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
    if not re.match(r"^[\w-]+$", username):
        await interaction.edit_original_message(content="Specified username is invalid.")
        return
    info = search_github_user(username)
    if info is not None:
        embed = discord.Embed(title=info["name"], description=info["bio"], color=0x2f3136)
        embed.set_author(name=info["login"], icon_url=info["avatar_url"], url=info["html_url"])
        embed.add_field(name="Repos", value=str(info["public_repos"]))
        embed.add_field(name="Followers", value=str(info["followers"]))
        embed.add_field(name="Following", value=str(info["following"]))
        embed.set_footer(text=datetime.strptime(info["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime('Created on %d %b, %Y.'))
        await interaction.edit_original_message(embed=embed, view=ViewButtons(embed, await interaction.original_message(), info))
    else:
        await interaction.edit_original_message(content=f"'{username}' not found.")

client.run(BOT_TOKEN)
