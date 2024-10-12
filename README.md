# DISCORD FORUM TO NOTION DATABASE BOT
> [!CAUTION]
> I am in no way liable for any effects this program may have. That being said, if you don't do anything stupid, it probably won't brick it. Either way, please do run it in a venv

> [!INFO]
> This bot only works on a guild install afaik. Please make sure it has the necessary permissions
## About
This discord bot, custom-made for Voices of Democracy, uploads forum posts to a Notion database. 
## Installation
- I would recommend using a virtual environment for this, so set that up
- Install the stuff in requirements.txt to your virtual environment
- Create a Notion integration with at least read content, insert content, and update content perms
- Create a Discord application with the message content intent enabled at least
    - Your install settings should at least include applications.commands, bot, manage threads, read message history, send messages, send messages in threads, and view channels permissions.
- Put your various strings into the .env file (this is a likely culprit, troubleshooting-wise)
- Run the bot in your venv and you should be good to go!
## Troubleshooting
- Make sure your Notion database has 2 fields: A title field entitled "Name" and a text field entitled "Content". These can be changed if you also change it in bot.py
- Check that your credentials and ids are correct
- Check that your Notion integration has access to the database page
- Check that your bot has the necessary guild permissions and is installed
- Check that your bot has access to your forum channel
- Put your bot into DEBUG mode
- Open a github issue if you need more help, please give me the logs when you do so (minus personal info, should it happen to appear, but it shouldn't).
## FAQs (who am I kidding lol)
Q: Will this bot send data back to donut-but-a-brain?

A: No. If it did, it wouldn't be in a public Github repo.

