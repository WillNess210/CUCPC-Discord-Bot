# bot.py
import os

import discord
from dotenv import load_dotenv
import urllib.request

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
command_symbol = '!'

client = discord.Client()

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    msg_content = message.content.lower()
    if msg_content[0] != command_symbol:
        return
    msg_content = msg_content[1:]
    args = msg_content.split()
    if args[0] == "uploadbot":
        authorid = message.author.mention
        atts = message.attachments
        if(len(atts) != 1):
            await message.channel.send("uploadbot needs 1 message attachment.")
            return
        att = atts[0]
        if(att.filename[-4:] != ".zip"):
            await message.channel.send("attachment must be a zip file.")
            return 
        print("received '" + att.filename + "' from " + authorid + ".")

    else:
        await message.channel.send("Unknown command.")

client.run(token)


# HELPER FUNCTIONS

def sendResponse(msg, resp):
    msg.channel.send(resp)