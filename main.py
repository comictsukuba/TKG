import discord
from discord.ext import commands
import json
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix='tkg!', intents=intents)

@bot.event
async def on_ready():
    print("on_ready")
    print(discord.__version__)

bot_token = os.getenv('DISCORD_BOT_TOKEN')
if bot_token is None:
    print("エラー: Botのトークンが設定されていません。")
    print(".envファイルを作成し、DISCORD_BOT_TOKENを設定してください。")
else:
    bot.run(bot_token)