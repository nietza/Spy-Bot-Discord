import discord
from discord.ext import commands
import datetime
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

LOGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Logs Users")
if not os.path.exists(LOGS_PATH):
    os.makedirs(LOGS_PATH)

user_data = {}

def load_allowed_users():
    try:
        with open('allowed_users.txt', 'r') as file:
            allowed_users = set(file.read().splitlines())
            print(f"Loaded allowed users: {allowed_users}")  
            return allowed_users
    except FileNotFoundError:
        print("allowed_users.txt not found!")
        return set()

ALLOWED_USERS = load_allowed_users()

def is_allowed_user():
    async def predicate(ctx):
        user_id = str(ctx.author.id)
        print(f"Checking if user {user_id} is allowed...")  
        print(f"Allowed users are: {ALLOWED_USERS}")  
        is_allowed = user_id in ALLOWED_USERS
        print(f"Is user allowed: {is_allowed}")  
        return is_allowed
    return commands.check(predicate)

def format_duration(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"**{hours}h {minutes}m**"

@bot.event
async def on_ready():
    print(f'Bot {bot.user} is ready for work!')

@bot.command(name='spy')
@is_allowed_user()
async def setup_logging(ctx, user_id: str, channel_id: str = None):
    if not user_id:
        await ctx.send("Please, state user ID")
        return

    try:
        target_user = await bot.fetch_user(int(user_id))
    except Exception as e:
        await ctx.send("Wrong user ID!")
        print(f"Error fetching user: {e}")
        return

    # folder
    user_folder = os.path.join(LOGS_PATH, target_user.name)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file_path = os.path.join(user_folder, f"logs_{current_date}.txt")
    
    user_data[int(user_id)] = {
        'channel_id': channel_id,
        'last_online': None,
        'last_offline': None,
        'log_file': None if channel_id else log_file_path,
        'user_folder': user_folder
    }
    
    log_location = f"channel <#{channel_id}>" if channel_id else f"folder `{user_folder}`"
    await ctx.send(f"👁️ Started spying on **{target_user.name}**\nLogs will be saved in: {log_location}")

# error
@setup_logging.error
async def spy_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You don't have permission to use this command.")
    else:
        print(f"An error occurred: {error}")


async def log_event(user_id: int, message: str):
    data = user_data.get(int(user_id))
    if not data:
        return

    discord_timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    discord_message = f"{message}     **{discord_timestamp}**"

    file_timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    file_message = message.replace('**', '') 
    file_log = f"{file_message}     [{file_timestamp}]"

    if data['channel_id']:
        try:
            channel = await bot.fetch_channel(int(data['channel_id']))
            await channel.send(discord_message)
        except Exception as e:
            print(f"Error in sending to channel {data['channel_id']}: {e}")
    else:
        try:
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            log_file_path = os.path.join(data['user_folder'], f"logs_{current_date}.txt")
            
            with open(log_file_path, 'a', encoding='utf-8') as f:
                f.write(file_log + '\n')
        except Exception as e:
            print(f"Error writing to log file: {e}")

@bot.event
async def on_presence_update(before, after):
    user_id = after.id
    if user_id not in user_data:
        return

    if before.status != after.status:
        if str(after.status) == "offline":
            user_data[user_id]['last_offline'] = datetime.datetime.now()
            if user_data[user_id]['last_online']:
                duration = (user_data[user_id]['last_offline'] - user_data[user_id]['last_online']).total_seconds()
                await log_event(user_id, f"🔴 **{after.name}** went offline. Was online for: {format_duration(int(duration))}")
        elif str(after.status) == "online":
            user_data[user_id]['last_online'] = datetime.datetime.now()
            await log_event(user_id, f"🟢 **{after.name}** went online")

    before_activity = next((activity for activity in before.activities if isinstance(activity, discord.Game)), None)
    after_activity = next((activity for activity in after.activities if isinstance(activity, discord.Game)), None)

    if before_activity != after_activity:
        if after_activity:
            await log_event(user_id, f"🎮 **{after.name}** started playing **{after_activity.name}**")
        elif before_activity:
            await log_event(user_id, f"🎮 **{after.name}** stopped playing **{before_activity.name}**")

@bot.event
async def on_voice_state_update(member, before, after):
    user_id = member.id
    if user_id not in user_data:
        return

    if before.channel != after.channel:
        if after.channel:
            await log_event(user_id, f"🎤 **{member.name}** joined voice channel: **{after.channel.name}**")
        else:
            duration = (datetime.datetime.now() - user_data[user_id]['last_online']).total_seconds() \
                if user_data[user_id]['last_online'] else 0
            await log_event(user_id, f"🎤 **{member.name}** left voice channel: **{before.channel.name}**. Was in voice for: {format_duration(int(duration))}")

@bot.event
async def on_typing(channel, user, when):
    user_id = user.id
    if user_id not in user_data:
        return

    await log_event(user_id, f"⌨️ **{user.name}** started typing in channel: **{channel.name}**")
    
@bot.command(name='shelp')
@is_allowed_user()
async def help_command(ctx):
    help_text = """
**📋 Spy Bot Help Guide:**

**/spy [user_id] [channel_id]** - Start spying on a user
• channel_id - Channel where logs will be sent (optional)
• user_id - ID of the user to spy on (required)

**The bot tracks:**
• 🟢 Online/Offline status
• 🎮 Gaming activity
• 🎤 Voice channel activity
• ⌨️ Typing activity

If channel_id is not provided, logs will be saved to a text file.
"""
    await ctx.send(help_text)

# Your bot token (will be replaced by setup script)
bot.run('Bot token')