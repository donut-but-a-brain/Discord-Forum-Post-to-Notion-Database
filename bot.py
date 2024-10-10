import discord
from discord.ext import commands
from notion_client import Client as NotionClient
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')

# Set up Notion client
notion = NotionClient(auth=NOTION_TOKEN)

# Set up Discord client
intents = discord.Intents.default()
intents.message_content = True  # Allows access to message content
intents.guilds = True  # Required to access guild information like channels
bot = commands.Bot(command_prefix="!", intents=intents)

# add title/law to database function
def add_law_to_notion(law_title, law_text):
    new_page = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": law_title}}]},
            "Law": {"rich_text": [{"text": {"content": law_text}}]},
        },
    }
    notion.pages.create(**new_page)

# ONLY RUN THIS THE FIRST TIME PLEASE! - adds previous laws to notion
@bot.command()
async def archive(ctx, forum_channel_id: int):
    # Fetch the forum channel by ID
    forum_channel = bot.get_channel(forum_channel_id)
    
    if isinstance(forum_channel, discord.ForumChannel):
        # Loop through all existing threads in forum
        for thread in forum_channel.threads:
            first_message = await thread.fetch_message(thread.id)
            message_content = first_message.content

            # upload stuff to notion
            add_law_to_notion(thread.name, message_content)
            print(f"Archived law '{thread.name}' to Notion")

        await ctx.send(f"Archived all existing posts from forum channel '{forum_channel.name}'")
    else:
        await ctx.send("The provided channel is not a forum channel.")

# new thread creation
@bot.event
async def on_thread_create(thread):
    if isinstance(thread.parent, discord.ForumChannel):
        # Fetch the first message of the thread
        first_message = await thread.fetch_message(thread.id)
        message_content = first_message.content
        
        # uploads the stuff to notion
        add_law_to_notion(thread.name, message_content)
        print(f"Uploaded law '{thread.name}' to Notion")

# run it
bot.run(DISCORD_TOKEN)
