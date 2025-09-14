import discord
from discord.ext import commands
from discord import app_commands 
import json
import datetime
import os
import uuid
import re
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

GUILD_ID = os.getenv('GUILD_ID')

bot = commands.Bot(command_prefix="!", intents=intents) 

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
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print("ログインしました。")



@bot.tree.command(name='add', description='タスクを追加します。', guild=discord.Object(id=GUILD_ID))
@app_commands.describe(
    task_name="タスク名",
    description="タスクの概要",
    assignees="担当者をメンションで指定（複数可）。",
    due_date="期限YYYY-MM-DD形式。(任意)"
)
async def add_task(
    ctx: discord.Interaction, 
    task_name: str,
    description: str,
    assignees: str = None, 
    due_date: str = None   
):

    assignee_ids = []
    if assignees:
        assignee_ids = [int(user_id) for user_id in re.findall(r'<@!?(\d+)>', assignees)]
    
    if not assignee_ids:
        assignee_ids = [ctx.user.id]

    validated_due_date = None
    if due_date:
        try:
            datetime.datetime.strptime(due_date, '%Y-%m-%d')
            validated_due_date = due_date
        except ValueError:
            await ctx.response.send_message("期限の形式が正しくありません。`YYYY-MM-DD`の形式で指定してください。", ephemeral=True)
            return
            
    new_task = {
        'id': str(uuid.uuid4()),
        'name': task_name,
        'description': description,
        'assignees': assignee_ids,
        'due_date': validated_due_date,
        'status': 'incomplete',
        'added_by': ctx.user.id,
    }

    tasks = load_tasks()
    tasks.append(new_task)
    save_task(tasks)


    embed = discord.Embed(title="✅ タスクが追加されました", color=discord.Color.green())
    embed.add_field(name="タスク名", value=task_name, inline=False)
    embed.add_field(name="概要", value=description, inline=False)
    assignee_mentions = [f'<@{user_id}>' for user_id in assignee_ids]
    embed.add_field(name="担当者", value=', '.join(assignee_mentions), inline=False)
    if validated_due_date:
        embed.add_field(name="期限", value=validated_due_date, inline=False)
    embed.set_footer(text=f"タスクID: {new_task['id']}")


    await ctx.response.send_message(embed=embed)


# --- Botの実行 (変更なし) ---
bot_token = os.getenv('DISCORD_BOT_TOKEN')
if bot_token is None:
    print("エラー: Botのトークンが設定されていません。")
else:
    bot.run(bot_token)