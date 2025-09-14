import discord
from discord.ext import commands
from discord import app_commands 
import json
import datetime
import os
import uuid
import re
from dotenv import load_dotenv

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm making TKG which is Japanese Cuisine."

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

GUILD_ID = os.getenv('GUILD_ID')

bot = commands.Bot(command_prefix="!", intents=intents) 

class TaskCompleteView(discord.ui.View):
    def __init__(self, tasks_to_select):
        super().__init__(timeout=300) 

        select = discord.ui.Select(
            placeholder="完了にするタスクを選択...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=task['name'],
                    value=task['id'],
                ) for task in tasks_to_select 
            ]
        )

        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, ctx: discord.Interaction):

        selected_task_id = ctx.data['values'][0]
        
        tasks = load_tasks()
        target_task = None

        for task in tasks:
            if task['id'] == selected_task_id:
                if task['status'] == 'complete':
                    await ctx.response.send_message(f"タスク「{task['name']}」は既に完了しています。", ephemeral=True)
                    return
                task['status'] = 'complete'
                target_task = task
                break
        
        if not target_task:
            await ctx.response.send_message("エラー: タスクが見つかりませんでした。", ephemeral=True)
            return

        save_task(tasks)

        self.children[0].disabled = True
        await ctx.message.edit(view=self)


        embed = discord.Embed(
            title="🎉 タスク完了",
            description=f"タスク「**{target_task['name']}**」を完了しました。",
            color=discord.Color.dark_green()
        )
        assignee_mentions = ', '.join([f'<@{user_id}>' for user_id in target_task['assignees']])
        embed.add_field(name="担当者", value=assignee_mentions, inline=False)
        embed.set_footer(text=f"完了操作者: {ctx.user.display_name}")
        
        await ctx.response.send_message(embed=embed)


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
    assignees="担当者をメンションで指定（複数可, 指定がない場合はタスク登録者）。",
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

@bot.tree.command(name='check', description='自分のタスクを確認します。', guild=discord.Object(id=GUILD_ID))
async def check_my_tasks(ctx: discord.Interaction):

    tasks = load_tasks()
    author_id = ctx.user.id

    my_tasks = [task for task in tasks if author_id in task['assignees'] and task['status'] == 'incomplete']

    if not my_tasks:
        await ctx.response.send_message("あなたが担当している未完了のタスクはありません。", ephemeral=True)
        return
    
    tasks_for_view = my_tasks[:25]
    
    embed = discord.Embed(title=f"📝 {ctx.user.display_name}さんのタスク一覧", color=discord.Color.blue())
    for task in my_tasks:
        assignee_mentions = ', '.join([f'<@{user_id}>' for user_id in task['assignees']])
        due_date_str = f"期限: {task['due_date']}" if task['due_date'] else "期限: なし"
        
        field_value = (
            f"**概要**: {task['description']}\n"
            f"**担当**: {assignee_mentions}\n"
            f"**{due_date_str}** | **ID**: `{task['id']}`"
        )
        embed.add_field(name=f"{task['name']}", value=field_value, inline=False)
    
    view = TaskCompleteView(tasks_for_view)

    await ctx.response.send_message(embed=embed, view=view)


@bot.tree.command(name='allcheck', description='全員のタスクを確認します。', guild=discord.Object(id=GUILD_ID))
async def check_all_tasks(ctx: discord.Interaction):

    tasks = load_tasks()
    
    incomplete_tasks = [task for task in tasks if task['status'] == 'incomplete']

    if not incomplete_tasks:
        await ctx.response.send_message("未完了のタスクはありません。", ephemeral=True)
        return
    
    tasks_for_view = incomplete_tasks[:25]

    embed = discord.Embed(title=f"📝 全てのタスク一覧", color=discord.Color.blue())
    
    for task in tasks_for_view:
        assignee_mentions = ', '.join([f'<@{user_id}>' for user_id in task['assignees']])
        due_date_str = f"期限: {task['due_date']}" if task['due_date'] else "期限: なし"
        
        field_value = (
            f"**概要**: {task['description']}\n"
            f"**担当**: {assignee_mentions}\n"
            f"**{due_date_str}** | **ID**: `{task['id']}`"
        )
        embed.add_field(name=f"{task['name']}", value=field_value, inline=False)
    
    if len(incomplete_tasks) > 25:
        embed.set_footer(text=f"タスクが25件以上あります。一部のみ表示しています。")

    view = TaskCompleteView(tasks_for_view)

    await ctx.response.send_message(embed=embed, view=view)

# --- Botの実行 (変更なし) ---
bot_token = os.getenv('DISCORD_BOT_TOKEN')
if bot_token is None:
    print("エラー: Botのトークンが設定されていません。")
else:
    # Webサーバーを別スレッドで起動
    web_thread = Thread(target=run_web_server)
    web_thread.start()
    # Discord Botを起動
    bot.run(bot_token)