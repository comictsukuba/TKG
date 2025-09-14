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

TASK_FILE = 'tasks.json'
def load_tasks():
    try:
        with open(TASK_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except(FileNotFoundError, json.JSONDecodeError):
        return []
    
def save_task(tasks):
    with open(TASK_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)

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