# bot.py
import os
import zipfile
import discord
import subprocess
from subprocess import DEVNULL
import re
from dotenv import load_dotenv
from urllib.request import Request, urlopen

# HELPER FUNCTIONS

async def sendResponse(msg, resp):
    await msg.channel.send(resp)

async def sendReplay(msg, replay_file, new_name):
    await msg.channel.send(file = discord.File(replay_file, new_name))

def downloadBot(att):
    url = att.url
    #file_data = urllib.request.urlopen(url, headers={'User-Agent': 'Mozilla/5.0'}).read()
    file_data = urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'})).read()
    return file_data

def writeBot(bot_name, file_data):
    fullpath = getBotZipRef(bot_name)
    if not doesBotExist(bot_name):
        try:
            os.makedirs(os.path.dirname(fullpath))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
    f = open(fullpath, 'wb')
    f.write(file_data)
    f.close()

def unzipBot(bot_name):
    with zipfile.ZipFile(getBotZipRef(bot_name), 'r') as zip_ref:
        zip_ref.extractall(getBotFolderRef(bot_name))

def doesBotExist(bot_name):
    return os.path.exists(os.path.dirname(getBotFolderRef(bot_name)))

def playMatch(p1, p2):
    subprocess.check_call(["java", "-jar", jar_ref, getBotFolderRef(p1), getBotFolderRef(p2)], stdout=DEVNULL, stderr=subprocess.STDOUT)

def getBotZipRef(p):
    return bots_stored + "/" + p + "/" + bot_filename

def getBotFolderRef(p):
    return bots_stored + "/" + p + "/" + bot_foldername

def getStrippedPlayerName(p):
    return re.sub('[<@!>]', '', p)

def getPlayerMention(p):
    return "<@" + p + ">"

def getResponseReplayFilename(p1, p2):
    return p1 + "_vs_" + p2 + ".log"

def validChannel(message):
    chid = message.channel.id
    return chid in valid_channel_ids

# BOT CODE

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
command_symbol = '!'
bot_filename = "bot.zip"
bot_foldername = "bot"
latest_replay = "replays/latest_replay.log"
bots_stored = "bots"
jar_ref = "tank-engine.jar"
valid_channel_ids = [589849475896443012, 649677486937997313] #test id, actual id

client = discord.Client()

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    if message.author == client.user or not validChannel(message):
        return
    msg_content = message.content.lower()
    if len(msg_content) == 0 or msg_content[0] != command_symbol:
        return
    msg_content = msg_content[1:]
    args = msg_content.split()
    if args[0] == "uploadbot":
        authorid = getStrippedPlayerName(message.author.mention)
        atts = message.attachments
        if(len(atts) != 1):
            await sendResponse(message, "uploadbot needs 1 message attachment.")
            return
        att = atts[0]
        if(att.filename[-4:] != ".zip"):
            await sendResponse(message, "attachment must be a zip file.")
            return 
        print("received '" + att.filename + "' from " + authorid + ".")
        file_data = downloadBot(att)
        writeBot(authorid, file_data)
        unzipBot(authorid)
        await sendResponse(message, "Bot uploaded.")
        return
    elif args[0] == "play":
        authorid = getStrippedPlayerName(message.author.mention)
        p1 = ""
        p2 = ""
        if(len(args) == 2): # !play <oppid>
            p1 = authorid
            p2 = getStrippedPlayerName(args[1])
        elif(len(args) == 3): # !play <p1_id> <p2_id>
            p1 = getStrippedPlayerName(args[1])
            p2 = getStrippedPlayerName(args[2])
        else:
            await sendResponse(message, "play needs 1-2 parameters.")
            return
        if not doesBotExist(p1):
            await sendResponse(message, "Cannot find bot for " + getPlayerMention(p1))
            return
        elif not doesBotExist(p2):
            await sendResponse(message, "Cannot find bot for " + getPlayerMention(p2))
            return
        playMatch(p1, p2)
        await sendReplay(message, latest_replay, getResponseReplayFilename(p1, p2))
    else:
        await sendResponse(message, "Unknown command.")

client.run(token)


