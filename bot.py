import discord
from discord.ext import commands
from notion_client import Client
from dotenv import load_dotenv
import requests
import os
import logging
import re
from datetime import datetime

# Load environment variables
load_dotenv()

# Set up intents
intents = discord.Intents.default()
intents.messages = True  # Enable message content intent
intents.message_content = True  # Enable message content too

# DO NOT USE THE COMMAND PREFIX. IT IS AN ARTIFACT I HAVEN'T REMOVED. USE SLASH COMMANDS INSTEAD
bot = commands.Bot(command_prefix='!', intents=intents)

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
NOTION_API_KEY = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))  # Ensure channel ID is an integer

# Set up Notion client
notion = Client(auth=NOTION_API_KEY)

# Set up logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)
logger.debug("Logging in DEBUG mode")
logger.error("Logging in ERROR mode")

# Helper function to fetch existing laws from Notion
def fetch_existing_laws():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28"
    }
    response = requests.post(url, headers=headers)
    response.raise_for_status()

    # Store existing laws with creation time for duplicate detection
    existing_laws = {}
    for result in response.json().get("results", []):
        name = result["properties"]["Name"]["title"][0]["text"]["content"]
        created_time = result["properties"]["Created Time"]["created_time"]
        page_id = result["id"]

        if name not in existing_laws:
            existing_laws[name] = {"created_time": created_time, "page_id": page_id}
        else:
            # Check for the older version
            if created_time < existing_laws[name]["created_time"]:
                archive_duplicate(existing_laws[name]["page_id"])  # Archive newer duplicate
                existing_laws[name] = {"created_time": created_time, "page_id": page_id}
            else:
                archive_duplicate(page_id)  # Archive the current page

    return existing_laws

# Helper function to archive a duplicate page in Notion
def archive_duplicate(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    payload = {"archived": True}

    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        logger.debug(f"Archived duplicate page with ID {page_id}.")
    else:
        logger.error(f"Failed to archive duplicate page: {response.status_code} - {response.text}")

# Function to parse "Passage Date" from thread content
def parse_passage_date(content):
    match = re.search(r'[Pp]assed\s+(\d{1,2}/\d{1,2}/\d{4})', content)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, '%m/%d/%Y').date()
        except ValueError:
            try:
                return datetime.strptime(date_str, '%d/%m/%Y').date()
            except ValueError:
                logger.error(f"Unrecognized date format in '{date_str}'")
                return None
    return None

# Helper function to add a law to Notion, splitting content if needed
async def save_to_notion(thread_name, thread_content):
    existing_laws = fetch_existing_laws()
    if thread_name in existing_laws:
        logger.debug(f"Skipping upload: '{thread_name}' already exists in the database.")
        return

    notion_url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    passage_date = parse_passage_date(thread_content)
    notion_date = passage_date.isoformat() if passage_date else None

    chunk_size = 2000
    rich_text_chunks = [
        {"text": {"content": thread_content[i:i + chunk_size]}}
        for i in range(0, len(thread_content), chunk_size)
    ]

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": thread_name or "Unnamed Law"}}]},
            "Content": {"rich_text": rich_text_chunks},
            "Passage Date": {"date": {"start": notion_date} if notion_date else None}
        }
    }

    response = requests.post(notion_url, headers=headers, json=payload)
    if response.status_code == 200:
        logger.debug("Successfully saved to Notion.")
    else:
        logger.error(f"Failed to save to Notion: {response.status_code} - {response.text}")

async def process_thread(thread):
    thread_content = ""
    async for message in thread.history(limit=None):
        thread_content += f"{message.content}\n"

    if not thread_content.strip():
        logger.error("Thread content is empty.")
        return

    await save_to_notion(thread.name, thread_content)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

@bot.tree.command(name="archive_laws", description="Just a tad self-explanatory")
async def archive_laws(interaction: discord.Interaction):
    await interaction.response.send_message("Tryin' my best to be yer filin' cabinet boss!", ephemeral=True)

    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if channel is None or not isinstance(channel, discord.ForumChannel):
        await interaction.followup.send("The specified channel is not a valid forum channel.", ephemeral=True)
        return

    if not interaction.guild.me.guild_permissions.read_message_history:
        await interaction.followup.send("I don't have permission to read message history in this channel.", ephemeral=True)
        return

    try:
        for thread in channel.threads:
            await process_thread(thread)

        async for archived_thread in channel.archived_threads(limit=None):
            await process_thread(archived_thread)

    except discord.Forbidden:
        await interaction.followup.send("I don't have permission to access this channel.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.followup.send(f"Error fetching threads: {e}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"An unexpected error occurred: {e}", ephemeral=True)

@bot.tree.command(name="ping", description="I am become raquet, destroyer of tables")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong", ephemeral=True)

bot.run(DISCORD_TOKEN)
