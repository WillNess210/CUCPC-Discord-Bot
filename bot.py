# bot.py
import os
import zipfile
import discord
import subprocess
from subprocess import DEVNULL
import re
from dotenv import load_dotenv
from urllib.request import Request, urlopen
import time
import asyncio
import json
import elopy
import configparser
import random

# CONSTANTS
SLEEP_TIME = 5 # Background processes repeat every X seconds
path_to_Elo = os.getcwd() + "/elos.json"
starting_elo = 1000
match_queue = []
message_queue = []
config = configparser.RawConfigParser()
config.read('discord_bot.properties')
leaderboard_channel_id = int(config.get('bot', 'leaderboard_channel_id'))
print_leaderboard_every_seconds = int(config.get('bot', 'leaderboard_refresh_time'))

users_that_should_have_bots = ["188407516844130305"]
last_remind_time = -1
remind_every_seconds = 43200 # currently 12 hours
remind_channel_id = int(config.get('bot', 'remind_channel_id'))

# HELPER FUNCTIONS

async def sendMatchResponse(msg, winner, score0, score1, p1, p2):
    winner_string = "Winner: "
    if winner == 0:
        winner_string += getUsernameFromID(p1)
    elif winner == 1:
        winner_string += getUsernameFromID(p2)
    elif winner == 2:
        winner_string += "tie"
    embed = discord.Embed(title="Match Results", color=getColor(winner), description=winner_string)
    embed.add_field(name = getUsernameFromID(p1), value = score0)
    embed.add_field(name = getUsernameFromID(p2), value = score1)
    await msg.channel.send(embed=embed)

async def sendMatchesResponse(msg, results, p1, p2):
    # CALCULATING WINS
    wins = [0, 0, 0]
    for match_result in results:
        wins[match_result[0]] += 1
    desc_string = "Wins: " + str(wins[0]) + "-" + str(wins[1]) + "-" + str(wins[2])

    # GETTING WINNER
    winner = 2
    if wins[0] > wins[1]:
        winner = 0
    elif wins[1] > wins[0]:
        winner = 1
    
    # AVERAGE SCORES
    averages = [0, 0]
    for match_result in results:
        averages[0] += match_result[1]
        averages[1] += match_result[2]
    averages[0] /= len(results)
    averages[1] /= len(results)

    ### MAIN REPORTING EMBED
    embed = discord.Embed(title="Series Results", color=getColor(winner), description=desc_string)
    await msg.channel.send(embed=embed)

    ### PLAYER STATS EMBED

    ## PLAYER 0 EMBED
    embedp0 = discord.Embed(title="Player 0", color = getColor(0), description=getPlayerMention(p1))
    embedp0.add_field(name="W-L", value=(str(wins[0]) + "-" + str(wins[1])), inline=True) # WINS - LOSSES
    embedp0.add_field(name="Average Score", value=averages[0], inline=True) # AVG SCORE
    # SEND
    await msg.channel.send(embed=embedp0)
    
    ## PLAYER 1 EMBED
    embedp1 = discord.Embed(title="Player 1", color = getColor(1), description=getPlayerMention(p2))
    embedp1.add_field(name="W-L", value=(str(wins[1]) + "-" + str(wins[0])), inline=False) # WINS - LOSSES
    embedp1.add_field(name="Average Score", value=averages[1], inline=True) # AVG SCORE
    # SEND
    await msg.channel.send(embed=embedp1)
    

async def sendResponse(msg, resp):
    embed = discord.Embed(description=resp)
    await msg.channel.send(embed=embed)

async def sendReplay(msg, replay_file, new_name):
    await msg.channel.send(file = discord.File(replay_file, new_name))

def getReplayValues(replay_file): #returns winner, 0_score, 1_score
    f = open(replay_file, 'r')
    winner = int(f.readline())
    scores = f.readline().split()
    return winner, int(scores[0]), int(scores[1])

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

def playMatches(p1, p2, num_matches):
    results = []
    for i in range(num_matches):
        winner, score_0, score_1 = playMatch(p1, p2)
        results.append([winner, score_0, score_1])
    return results

def playMatch(p1, p2):
    subprocess.check_call(["java", "-jar", jar_ref, getBotFolderRef(p1), getBotFolderRef(p2)], stdout=DEVNULL, stderr=subprocess.STDOUT)
    return getReplayValues(latest_replay)

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

def getColor(player):
    return colors[player]

def checkValidBot(player):
    return os.path.isfile(bots_stored + "/" + player + "/" + bot_foldername + "/bot_config.properties")

def getPropertyFromPlayer(property, player):
    CONFIG_PATH = bots_stored + "/" + player + "/" + bot_foldername + "/bot_config.properties"
    with open(CONFIG_PATH, 'r') as f:
        config_string = '[dummy_section]\n' + f.read()
    config = configparser.ConfigParser()
    config.read_string(config_string)
    return config.get('dummy_section', property)

def getPlayerLanguage(player):
    return int(getPropertyFromPlayer('bot_language', player))

def getPlayerMainFile(player):
    return getPropertyFromPlayer('main_file', player)

def removeMatchesFrom(mq, name):
    rq = []
    for match in mq:
        if not match["p0"] == name and not match["p1"] == name:
            rq.append(match)
    return rq

def removeBot(player, myclient):
    print("removing " + player)
    # remove all matches from queue
    mq = removeMatchesFrom(myclient.match_queue, player)
    emq = removeMatchesFrom(myclient.elo_match_queue, player)
    # removing from filesystem
    player = getStrippedPlayerName(player)
    wd = os.path.dirname(os.path.realpath(__file__)) + "/bots/" + player
    call = "rm " + wd + " -r"
    subprocess.Popen(call, shell = True, cwd=wd)
    return mq, emq

def removeSterr():
    call = "rm *.out"
    subprocess.Popen(call, shell = True, stdout=DEVNULL, stderr=subprocess.STDOUT)

def clearReplays():
    wd = os.path.dirname(os.path.realpath(__file__)) + "/replays"
    call = "find . ! -name 'latest_replay.log' -type f -exec rm -f {} +"
    subprocess.Popen(call, shell = True, cwd=wd)

def chmodxFile(fl):
    call = "chmod +x " + fl
    subprocess.Popen(call, shell = True, stdout=DEVNULL, stderr=subprocess.STDOUT)

def getPlayers():
    return os.listdir(os.getcwd() + "/bots")

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
colors = [255, 16711680, 10197915] #blue, red, tie


class MyClient(discord.Client):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg_task = self.loop.create_task(self.match_player())
        self.match_queue = []
        self.elo_match_queue = []
        self.elo_system = elopy.Implementation()
        self.should_refresh_elo = True
        self.last_update = 0
        self.last_change = time.time()
        if not os.path.isfile(path_to_Elo):
            print("No elo file found. Loading fresh")
            self.loadFreshElos()
        else:
            print("Elo file found. Loading")
            self.loadEloFileToEloSystem()

    #@client.event
    async def on_ready(self):
        print(f'{client.user} has connected to Discord!')

    #@client.event
    async def on_message(self, message):
        if message.author == client.user or (not validChannel(message) and message.channel.type != discord.ChannelType.private):
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
            if os.path.isdir("bots/" + authorid):
                mq, emq = removeBot(authorid, self)
                self.match_queue = mq
                self.elo_match_queue = emq
            print("received '" + att.filename + "' from " + authorid + ".")
            file_data = downloadBot(att)
            writeBot(authorid, file_data)
            unzipBot(authorid)
            if not checkValidBot(authorid):
                mq, emq = removeBot(authorid, self)
                self.match_queue = mq
                self.elo_match_queue = emq
                self.removePlayerFromEloFile(authorid)
                self.removeEloPlayer(authorid)
                await sendResponse(message, "Invalid upload. Ensure that your bot_config.properties is in the root directory of your .zip")
                return
            await sendResponse(message, "Bot uploaded.")
            # if c++, chmod the main file
            if getPlayerLanguage(authorid) == 1:
                main_file = bots_stored + "/" + authorid + "/" + bot_foldername + "/" + getPlayerMainFile(authorid)
                chmodxFile(main_file)

            # set new bot elo in elosystem
            self.addEloPlayer(authorid)
            self.saveEloSystemToEloFile()
            self.addEloSetForPlayer(authorid, 5)
            self.last_change = time.time()
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
            self.addMatchPrint(message, p1, p2)
            return
        elif args[0] == "playmult":
            if(len(args) != 4):
                await sendResponse(message, "playmult needs 3 args: p1 p2 num_matches")
                return
            p1 = getStrippedPlayerName(args[1])
            p2 = getStrippedPlayerName(args[2])
            num_matches = abs(int(args[3]))
            if num_matches > 10:
                await sendResponse(message, "10 matches max right now.")
                return
            self.addMatchMult(message, p1, p2, num_matches)
            return
        elif args[0] == "lb":
            await self.printEloLeaderboard(message.channel.id)
        elif args[0] == 'eloset':
            if(len(args) > 2):
                await sendResponse(message, "eloset must be blank or 1 integer param")
                return
            num = 3
            if(len(args) == 2):
                num = int(args[1])
                if num > 10:
                    await sendResponse(message, "error, max of 10")
            self.addEloSet(num)
            await sendResponse(message, "Added " + str(num) + " Elo matches for each player.")
        else:
            await sendResponse(message, "Unknown command.")

    async def remindUsersToUpload(self):
        global last_remind_time, remind_every_seconds, remind_channel_id, users_that_should_have_bot
        if(time.time() > last_remind_time + remind_every_seconds): # 12 hours
            print("it's been 12 hours or the bot has restarted. annoying those who haven't uploaded")
            for userid in users_that_should_have_bots:
                if not doesBotExist(userid):
                    channel = client.get_channel(remind_channel_id)
                    await channel.send("Hey <@" + userid + ">. You still haven't uploaded a bot!")
            if last_remind_time == -1:
                last_remind_time = time.time()
            last_remind_time += remind_every_seconds

    async def match_player(self):
        await self.wait_until_ready()
        while True:
            await self.playNextMatch()
            await self.handleEloMatches()
            if(len(self.elo_match_queue) == 0):
                if(self.last_change > self.last_update and self.last_update + print_leaderboard_every_seconds < time.time()):
                    self.last_update = time.time()
                    await self.printEloLeaderboard()
                self.saveEloSystemToEloFile()
            await self.remindUsersToUpload()
            await asyncio.sleep(2)

    async def handleEloMatches(self):
        if(len(self.elo_match_queue) == 0):
            return
            '''playerss = self.elo_system.getRatingList()
            players = []
            for player in playerss:
                players.append(player[0])
            num_players = len(players)
            for k in range(1):
                for i in range(num_players):
                    for j in range(i + 1, num_players):
                        self.addMatchElo(players[i], players[j])'''
        
        match = self.elo_match_queue[0]
        self.elo_match_queue = self.elo_match_queue[1:len(self.elo_match_queue)]
        p0 = match["p0"]
        p1 = match["p1"]
        print("Playing elo match. " + p0 + " vs " + p1 + ". " + str(len(self.elo_match_queue)) + " left.")
        winner, score_0, score_1 = playMatch(p0, p1)
        if winner == 2:
            self.addMatchResult(p0, p1, 2)
        elif winner == 0:
            self.addMatchResult(p0, p1, p0)
        elif winner == 1:
            self.addMatchResult(p0, p1, p1)
        clearReplays()
        removeSterr()

    def addEloSetForPlayer(self, p0, num_player_each):
        self.removePlayerFromQueues(p0)
        players = getPlayers()
        for i in range(num_player_each):
            for player in players:
                if player != p0:
                    self.addMatchElo(p0, player)

    def addMatchElo(self, p0, p1):
        this_match = {}
        this_match["type"] = "elo"
        this_match["p0"] = p0
        this_match["p1"] = p1
        self.elo_match_queue.append(this_match)

    def addMatchPrint(self, message, p0, p1):
        this_match = {}
        this_match["type"] = "print"
        this_match["msg"] = message
        this_match["p0"] = p0
        this_match["p1"] = p1
        self.match_queue.append(this_match)

    def addMatchMult(self, message, p0, p1, num_matches):
        this_match = {}
        this_match["type"] = "mult"
        this_match["msg"] = message
        this_match["p0"] = p0
        this_match["p1"] = p1
        this_match["num_matches"] = num_matches
        self.match_queue.append(this_match)
    
    async def playNextMatch(self):
        if len(self.match_queue) == 0:
            return False
        match = self.match_queue[0]
        self.match_queue = self.match_queue[1:len(self.match_queue)]
        p0 = match["p0"]
        p1 = match["p1"]
        print("Playing match. " + str(p0) + " vs " + str(p1))
        message = match["msg"]
        if (match["type"] == "print"):
            winner, score_0, score_1 = playMatch(p0, p1)
            await sendReplay(message, latest_replay, getResponseReplayFilename(p0, p1))
            await sendMatchResponse(message, winner, score_0, score_1, p0, p1)
            clearReplays()
            removeSterr()
        elif (match["type"] == "mult"):
            results = playMatches(p0, p1, match["num_matches"])
            await sendMatchesResponse(message, results, p0, p1)
            clearReplays()
            removeSterr()
        return True
    
    def addMatchResult(self, p0, p1, win):
        if win == 2:
            self.elo_system.recordMatch(p0, p1, draw=True)
            return
        self.elo_system.recordMatch(p0, p1, winner=win)

    def playerInEloSystem(self, name):
        for player in self.elo_system.players:
            if player.name == name:
                return True
        return False

    def removeEloPlayer(self, name):
        if self.playerInEloSystem(name):
            self.elo_system.removePlayer(name)

    def addEloPlayer(self, name):
        if self.playerInEloSystem(name):
            self.elo_system.removePlayer(name)
        self.elo_system.addPlayer(name, rating=starting_elo)
        print("Adding " + name)

    def addEloSet(self, num = 3):
        players = getPlayers()
        for player in players:
            self.addEloSetForPlayer(player, num)
    
    def loadFreshElos(self):
        players = getPlayers()
        for player in players:
            self.addEloPlayer(player)
            self.addEloSetForPlayer(player, 3)
        self.saveEloSystemToEloFile()

    def loadEloFileToEloSystem(self):
        self.elo_system = elopy.Implementation()
        with open(path_to_Elo) as json_file:
            elos = json.load(json_file)
            for player, elo in elos.items():
                self.elo_system.addPlayer(player, rating=elo)
                print("Loading " + player + " w/ elo of " + str(elo))

    def saveEloSystemToEloFile(self):
        elos = {}
        for player_data in self.elo_system.getRatingList():
            elos[player_data[0]] = player_data[1]
        with open(path_to_Elo, 'w') as outfile:
            json.dump(elos, outfile)
    
    def removePlayerFromQueues(self, name):
        mq = []
        emq = []
        for m in self.match_queue:
            if m["p0"] != name and m["p1"] != name:
                mq.append(m)
        self.match_queue = mq
        for m in self.elo_match_queue:
            if m["p0"] != name and m["p1"] != name:
                emq.append(m)
        self.elo_match_queue = emq

    def removePlayerFromEloFile(self, name):
        elos = {}
        for player_data in self.elo_system.getRatingList():
            if player_data[0] != name:
                elos[player_data[0]] = player_data[1]
                print("adding " + player_data[0])
            else:
                print("withholding")
        with open(path_to_Elo, 'w') as outfile:
            json.dump(elos, outfile)

    async def printEloLeaderboard(self, chnl = leaderboard_channel_id):
        elos = []
        for player_data in self.elo_system.getRatingList():
            elos.append([player_data[0], player_data[1]])
        sorted_players = sorted(elos, key=lambda tup: tup[1], reverse=True)
        to_send_string = "Bot Leaderboard: \n"
        rank = 1
        for player in sorted_players:
            to_send_string += str(rank) + ". " + getPlayerMention(player[0]) + " - " + str(player[1]) + "\n"
            rank += 1
        if(len(to_send_string) > 0):
            print(to_send_string)
            channel = client.get_channel(chnl)
            embed = discord.Embed(description=to_send_string)
            await channel.send(embed=embed)
        
        
def getUsernameFromID(cid):
    global client
    for guild in client.guilds:
        for member in guild.members:
            if str(member.id) == str(cid):
                return member.display_name
    return cid

client = MyClient()

client.run(token)
