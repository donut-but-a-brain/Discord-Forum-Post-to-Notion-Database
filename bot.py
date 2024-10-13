import discord
from discord.ext import commands
from notion_client import Client
from dotenv import load_dotenv
import requests
import os
import logging

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
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))  # Make sure the channel ID is an integer

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

    # Extract the names of existing laws
    existing_laws = set()
    for result in response.json().get("results", []):
        name = result["properties"]["Name"]["title"][0]["text"]["content"]
        existing_laws.add(name)

    return existing_laws

# Helper function to add a law to Notion
async def save_to_notion(thread_name, thread_content):
    notion_url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    # Fetch existing laws to avoid duplicates
    existing_laws = fetch_existing_laws()
    if thread_name in existing_laws:
        logger.debug(f"Skipping upload: '{thread_name}' already exists in the database.")
        return

    # Build the payload for Notion
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": thread_name or "Unnamed Law"
                        }
                    }
                ]
            },
            "Content": {
                "rich_text": [
                    {
                        "text": {
                            "content": thread_content or "No content available"
                        }
                    }
                ]
            }
        }
    }

    logger.debug(f"Sending payload to Notion: {payload}")

    # Make the request to Notion API
    response = requests.post(notion_url, headers=headers, json=payload)

    # Log the response from Notion
    logger.debug(f"Response from Notion: {response.status_code} - {response.text}")

    if response.status_code == 200:
        logger.debug("Successfully saved to Notion.")
    else:
        logger.error(f"Failed to save to Notion: {response.status_code} - {response.text}")

@bot.event
async def on_ready():
    # Sync the slash commands
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

@bot.tree.command(name="archive_laws", description="It's just a LITTLE BIT self-explanatory, no?")
async def archive_laws(interaction: discord.Interaction):
    logger.debug("archive_laws command invoked.")
    await interaction.response.send_message("Archiving your law right now. If you aren't @alecstatic and it doesn't show up in the Notion database, contact @alecstatic please. Thank you!")

    # Get the channel where the command was invoked
    channel = bot.get_channel(DISCORD_CHANNEL_ID)

    logger.debug(f"Retrieved channel: {channel} (type: {type(channel)})")

    # Check if the channel is a valid channel and a forum channel
    if channel is None or not isinstance(channel, discord.ForumChannel):
        logger.error("The specified channel is not a valid forum channel.")
        await interaction.followup.send("The specified channel is not a valid forum channel.")
        return

    # Check for permissions
    if not interaction.guild.me.guild_permissions.read_message_history:
        logger.error("Bot lacks permission to read message history.")
        await interaction.followup.send("I don't have permission to read message history in this channel.")
        return

    logger.debug("Permissions are valid. Attempting to fetch all threads.")

    try:
        # Iterate over all threads (both active and archived)
        for thread in channel.threads:  # This is a list, so iterate over it directly
            logger.debug(f"Found thread: {thread.name}")

            # Collect the content of the messages
            thread_content = ""
            
            # Retrieve messages in the thread using async for loop
            async for message in thread.history(limit=None):
                thread_content += f"{message.content}\n"

            # Ensure thread_content is valid
            if not thread_content.strip():
                logger.error("Thread content is empty.")
                continue  # Skip to the next thread

            # Save the thread to Notion
            await save_to_notion(thread.name, thread_content)

    except discord.Forbidden:
        logger.error("I don't have permission to access this channel.")
        await interaction.followup.send("I don't have permission to access this channel.")
    except discord.HTTPException as e:
        logger.error(f"Error fetching threads: {e}")
        await interaction.followup.send(f"Error fetching threads: {e}")
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        await interaction.followup.send(f"An unexpected error occurred: {e}")

@bot.tree.command(name="ping", description="I am become racquet, destroyer of tables.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")
    logger.info("Ping command executed.")

# Run the bot
bot.run(DISCORD_TOKEN)
