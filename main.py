import discord
from discord.ext import commands
import datetime
import os
import asyncio
import aioconsole
from spy_config import add_spy_target, remove_spy_target, get_spy_targets
from mirror_config import add_mirror_channel, remove_mirror_channel, get_mirror_channels

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

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
        # check if user is allowed
        if not os.path.exists('allowed_users.txt') or os.path.getsize('allowed_users.txt') == 0:
            return True
            
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
    bot.loop.create_task(console_input())
    config = get_spy_targets()
    for user_id, data in config.items():
        try:
            target_user = await bot.fetch_user(int(user_id))
            user_folder = os.path.join(LOGS_PATH, target_user.name)
            if not os.path.exists(user_folder):
                os.makedirs(user_folder)
            
            user_data[int(user_id)] = {
                'channel_id': data.get('channel_id'),
                'last_online': None,
                'last_offline': None,
                'log_file': None if data.get('channel_id') else user_folder,
                'user_folder': user_folder
            }
            print(f"Loaded spy configuration for {target_user.name}")
        except Exception as e:
            print(f"Error loading spy configuration for user {user_id}: {e}")

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
    user_folder = os.path.join(LOGS_PATH, target_user.name)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    
    #user data save
    user_data[int(user_id)] = {
        'channel_id': channel_id,
        'last_online': None,
        'last_offline': None,
        'log_file': None if channel_id else user_folder,
        'user_folder': user_folder
    }
    add_spy_target(user_id, channel_id, None if channel_id else user_folder)
    
    log_location = f"channel <#{channel_id}>" if channel_id else f"folder `{user_folder}`"
    await ctx.send(f"👁️ Started spying on **{target_user.name}**\nLogs will be saved in: {log_location}")

@bot.command(name='unspy')
@is_allowed_user()
async def stop_logging(ctx, user_id: str):
    try:
        target_user = await bot.fetch_user(int(user_id))
        if int(user_id) in user_data:
            del user_data[int(user_id)]
            remove_spy_target(user_id)
            await ctx.send(f"🚫 Stopped spying on **{target_user.name}**")
        else:
            await ctx.send(f"⚠️ Wasn't spying on **{target_user.name}**")
    except Exception as e:
        await ctx.send("Wrong user ID!")
        print(f"Error in unspy command: {e}")

@setup_logging.error
async def spy_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You don't have permission to use this command.")
    else:
        print(f"An error occurred: {error}")

@stop_logging.error
async def unspy_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You don't have permission to use this command.")
    else:
        print(f"An error occurred: {error}")

async def log_event(user_id: int, message: str, guild_name: str = None):
    data = user_data.get(int(user_id))
    if not data:
        return

    server_info = f" [Server: {guild_name}]" if guild_name else ""
    discord_timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    discord_message = f"{message}{server_info}     **{discord_timestamp}**"

    file_timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    file_message = message.replace('**', '')
    file_log = f"{file_message}{server_info}     [{file_timestamp}]"

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
            await log_event(user_id, f"🟢 **{after.name}** is online now")

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
            await log_event(user_id, f"🎤 **{member.name}** joined voice channel: **{after.channel.name}**", after.channel.guild.name)
        else:
            duration = (datetime.datetime.now() - user_data[user_id]['last_online']).total_seconds() \
                if user_data[user_id]['last_online'] else 0
            await log_event(user_id, f"🎤 **{member.name}** left voice channel: **{before.channel.name}**. Was in voice for: {format_duration(int(duration))}")
            
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    mirror_config = get_mirror_channels()
    source_channel_id = str(message.channel.id)
    
    if source_channel_id in mirror_config:
        try:
            target_channel = await bot.fetch_channel(int(mirror_config[source_channel_id]))

            content = message.content
            embeds = [embed.to_dict() for embed in message.embeds]
            files = []
            for attachment in message.attachments:
                file = await attachment.to_file()
                files.append(file)
            await target_channel.send(
                content=f"**{message.author.name}**: {content}",
                embeds=[discord.Embed.from_dict(embed) for embed in embeds],
                files=files if files else None
            )
        except Exception as e:
            print(f"Error mirroring message: {e}")
async def process_dm_command(message):
    # check is allowed
    if ALLOWED_USERS and str(message.author.id) not in ALLOWED_USERS:
        await message.channel.send("You don't have permission to use this bot.")
        return

    content = message.content.lower().strip()
    if content == "help":
        help_text = """
**📋 Available Commands:**
`spy <user_id> [channel_id]` - Start spying on a user
• channel_id - Channel where logs will be sent (optional) if not stated, folder with logs will be created. 
• user_id - ID of the user to spy on (required)
`unspy <user_id>` - Stop spying on a user
`list` - Show current spy targets
`help` - Show this help message

**The bot tracks:**
• 🟢 Online/Offline status
• 🎮 Gaming activity
• 🎤 Voice channel activity
• ⌨️ Typing activity
"""
        await message.channel.send(help_text)
        return

    #check 
    if content == "list":
        if not user_data:
            await message.channel.send("No users are being spied on currently.")
            return
            
        spy_list = "**Current spy targets:**\n"
        for user_id in user_data:
            try:
                user = await bot.fetch_user(user_id)
                data = user_data[user_id]
                location = f"channel <#{data['channel_id']}>" if data['channel_id'] else f"folder `{data['user_folder']}`"
                spy_list += f"• {user.name} (ID: {user_id}) - Logs in: {location}\n"
            except Exception as e:
                spy_list += f"• Unknown user (ID: {user_id}) - Error: {str(e)}\n"
        await message.channel.send(spy_list)
        return

    #spy
    if content.startswith("spy "):
        parts = content.split()
        if len(parts) < 2:
            await message.channel.send("Usage: `spy <user_id> [channel_id]`")
            return
            
        user_id = parts[1]
        channel_id = parts[2] if len(parts) > 2 else None
        
        try:
            target_user = await bot.fetch_user(int(user_id))
            user_folder = os.path.join(LOGS_PATH, target_user.name)
            if not os.path.exists(user_folder):
                os.makedirs(user_folder)
            
            user_data[int(user_id)] = {
                'channel_id': channel_id,
                'last_online': None,
                'last_offline': None,
                'log_file': None if channel_id else user_folder,
                'user_folder': user_folder
            }
            
            add_spy_target(user_id, channel_id, None if channel_id else user_folder)
            log_location = f"channel <#{channel_id}>" if channel_id else f"folder `{user_folder}`"
            await message.channel.send(f"👁️ Started spying on **{target_user.name}**\nLogs will be saved in: {log_location}")
        except Exception as e:
            await message.channel.send(f"Error: {str(e)}")
        return

    #unspy
    if content.startswith("unspy "):
        parts = content.split()
        if len(parts) < 2:
            await message.channel.send("Usage: `unspy <user_id>`")
            return
            
        user_id = parts[1]
        try:
            target_user = await bot.fetch_user(int(user_id))
            if int(user_id) in user_data:
                del user_data[int(user_id)]
                remove_spy_target(user_id)
                await message.channel.send(f"🚫 Stopped spying on **{target_user.name}**")
            else:
                await message.channel.send(f"⚠️ Wasn't spying on **{target_user.name}**")
        except Exception as e:
            await message.channel.send(f"Error: {str(e)}")
        return
    elif content.startswith("mirror "):
        parts = content.split()
        if len(parts) < 3:
            await message.channel.send("Usage: `mirror <source_channel_id> <target_channel_id>`")
            return
            
        source_id = parts[1]
        target_id = parts[2]
        
        try:
            source_channel = await bot.fetch_channel(int(source_id))
            target_channel = await bot.fetch_channel(int(target_id))
            
            add_mirror_channel(source_id, target_id)
            await message.channel.send(f"✅ Started mirroring channel **{source_channel.name}** to **{target_channel.name}**")
        except Exception as e:
            await message.channel.send(f"Error: {str(e)}")

    elif content.startswith("unmirror "):
        parts = content.split()
        if len(parts) < 2:
            await message.channel.send("Usage: `unmirror <source_channel_id>`")
            return
            
        source_id = parts[1]
        try:
            source_channel = await bot.fetch_channel(int(source_id))
            if remove_mirror_channel(source_id):
                await message.channel.send(f"🚫 Stopped mirroring channel **{source_channel.name}**")
            else:
                await message.channel.send(f"⚠️ Channel **{source_channel.name}** was not being mirrored")
        except Exception as e:
            await message.channel.send(f"Error: {str(e)}")

    elif content == "mirrorlist":
        mirror_config = get_mirror_channels()
        if not mirror_config:
            await message.channel.send("No channels are being mirrored currently.")
            return
            
        mirror_list = "**Current mirrored channels:**\n"
        for source_id, target_id in mirror_config.items():
            try:
                source_channel = await bot.fetch_channel(int(source_id))
                target_channel = await bot.fetch_channel(int(target_id))
                mirror_list += f"• {source_channel.name} ({source_id}) ➡️ {target_channel.name} ({target_id})\n"
            except Exception as e:
                mirror_list += f"• Unknown channel ({source_id}) ➡️ Unknown channel ({target_id}) - Error: {str(e)}\n"
        await message.channel.send(mirror_list)

    #if unknown command
    if content.startswith(("spy", "unspy", "list", "help")):
        await message.channel.send("Unknown command. Type `help` for available commands.")
#console control
@bot.event
async def on_typing(channel, user, when):
    user_id = user.id
    if user_id not in user_data:
        return

    await log_event(user_id, f"⌨️ **{user.name}** started typing in channel: **{channel.name}**" , channel.guild.name if hasattr(channel, 'guild') else None)

async def process_console_command(command):
    """Process commands in console"""
    parts = command.split()
    if not parts:
        return

    cmd = parts[0].lower()
    args = parts[1:]

    if cmd == 'spy':
        if len(args) >= 1:
            user_id = args[0]
            channel_id = args[1] if len(args) > 1 else None
            try:
                target_user = await bot.fetch_user(int(user_id))
                user_folder = os.path.join(LOGS_PATH, target_user.name)
                if not os.path.exists(user_folder):
                    os.makedirs(user_folder)
                
                user_data[int(user_id)] = {
                    'channel_id': channel_id,
                    'last_online': None,
                    'last_offline': None,
                    'log_file': None if channel_id else user_folder,
                    'user_folder': user_folder
                }
                
                add_spy_target(user_id, channel_id, None if channel_id else user_folder)
                print(f"👁️ Started spying on {target_user.name}")
                log_location = f"channel #{channel_id}" if channel_id else f"folder {user_folder}"
                print(f"Logs will be saved in: {log_location}")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("Usage: spy <user_id> [channel_id]")

    elif cmd == 'unspy':
        if len(args) >= 1:
            user_id = args[0]
            try:
                target_user = await bot.fetch_user(int(user_id))
                if int(user_id) in user_data:
                    del user_data[int(user_id)]
                    remove_spy_target(user_id)
                    print(f"🚫 Stopped spying on {target_user.name}")
                else:
                    print(f"⚠️ Wasn't spying on {target_user.name}")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("Usage: unspy <user_id>")
    elif cmd == 'list':
        if not user_data:
            print("No users are being spied on currently.")
            return
            
        print("Current spy targets:")
        for user_id in user_data:
            try:
                user = await bot.fetch_user(user_id)
                data = user_data[user_id]
                location = f"channel #{data['channel_id']}" if data['channel_id'] else f"folder {data['user_folder']}"
                print(f"• {user.name} (ID: {user_id}) - Logs in: {location}")
            except Exception as e:
                print(f"• Unknown user (ID: {user_id}) - Error: {str(e)}")
    elif cmd == 'mirror':
        if len(args) >= 2:
            source_id = args[0]
            target_id = args[1]
            try:
                source_channel = await bot.fetch_channel(int(source_id))
                target_channel = await bot.fetch_channel(int(target_id))
                
                add_mirror_channel(source_id, target_id)
                print(f"✅ Started mirroring channel {source_channel.name} to {target_channel.name}")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("Usage: mirror <source_channel_id> <target_channel_id>")

    elif cmd == 'unmirror':
        if len(args) >= 1:
            source_id = args[0]
            try:
                source_channel = await bot.fetch_channel(int(source_id))
                if remove_mirror_channel(source_id):
                    print(f"🚫 Stopped mirroring channel {source_channel.name}")
                else:
                    print(f"⚠️ Channel {source_channel.name} was not being mirrored")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("Usage: unmirror <source_channel_id>")

    elif cmd == 'mirrorlist':
        mirror_config = get_mirror_channels()
        if not mirror_config:
            print("No channels are being mirrored currently.")
            return
            
        print("Current mirrored channels:")
        for source_id, target_id in mirror_config.items():
            try:
                source_channel = await bot.fetch_channel(int(source_id))
                target_channel = await bot.fetch_channel(int(target_id))
                print(f"• {source_channel.name} ({source_id}) ➡️ {target_channel.name} ({target_id})")
            except Exception as e:
                print(f"• Unknown channel ({source_id}) ➡️ Unknown channel ({target_id}) - Error: {str(e)}")
    elif cmd == 'help':
        print("""
📋 Console Commands Help:
**spy [user_id] [channel_id]** - Start spying on a user
• channel_id - Channel where logs will be sent (optional) if not stated, folder with logs will be created. 
• user_id - ID of the user to spy on (required)
unspy <user_id> - Stop spying on a user
list - Show current spy targets
help - Show this help message
exit - Stop the bot

The bot tracks:
• 🟢 Online/Offline status
• 🎮 Gaming activity
• 🎤 Voice channel activity
• ⌨️ Typing activity
        """)
    
    elif cmd == 'exit':
        print("Stopping the bot...")
        await bot.close()
    
    else:
        print(f"Unknown command: {cmd}")
        print("Type 'help' for available commands")

async def console_input():
    """console input"""
    print("Console commands enabled. Type 'help' for available commands.")
    while True:
        try:
            command = await aioconsole.ainput('> ')
            await process_console_command(command)
        except Exception as e:
            print(f"Error processing console command: {e}")
        await asyncio.sleep(0.1)

@bot.command(name='list')
@is_allowed_user()
async def list_spied_users(ctx):
    if not user_data:
        await ctx.send("No users are being spied on currently.")
        return
        
    spy_list = "**Current spy targets:**\n"
    for user_id in user_data:
        try:
            user = await bot.fetch_user(user_id)
            data = user_data[user_id]
            location = f"channel <#{data['channel_id']}>" if data['channel_id'] else f"folder `{data['user_folder']}`"
            spy_list += f"• {user.name} (ID: {user_id}) - Logs in: {location}\n"
        except Exception as e:
            spy_list += f"• Unknown user (ID: {user_id}) - Error: {str(e)}\n"
    await ctx.send(spy_list)
@bot.command(name='mirror')
@is_allowed_user()
async def mirror_channel(ctx, source_id: str, target_id: str):
    try:
        source_channel = await bot.fetch_channel(int(source_id))
        target_channel = await bot.fetch_channel(int(target_id))
        add_mirror_channel(source_id, target_id)
        await ctx.send(f"✅ Started mirroring channel **{source_channel.name}** to **{target_channel.name}**")
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

@bot.command(name='unmirror')
@is_allowed_user()
async def unmirror_channel(ctx, source_id: str):
    try:
        source_channel = await bot.fetch_channel(int(source_id))
        if remove_mirror_channel(source_id):
            await ctx.send(f"🚫 Stopped mirroring channel **{source_channel.name}**")
        else:
            await ctx.send(f"⚠️ Channel **{source_channel.name}** was not being mirrored")
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

@bot.command(name='mirrorlist')
@is_allowed_user()
async def list_mirrored_channels(ctx):
    mirror_config = get_mirror_channels()
    if not mirror_config:
        await ctx.send("No channels are being mirrored currently.")
        return
        
    mirror_list = "**Current mirrored channels:**\n"
    for source_id, target_id in mirror_config.items():
        try:
            source_channel = await bot.fetch_channel(int(source_id))
            target_channel = await bot.fetch_channel(int(target_id))
            mirror_list += f"• {source_channel.name} ({source_id}) ➡️ {target_channel.name} ({target_id})\n"
        except Exception as e:
            mirror_list += f"• Unknown channel ({source_id}) ➡️ Unknown channel ({target_id}) - Error: {str(e)}\n"
    await ctx.send(mirror_list)

@bot.command(name='shelp')
@is_allowed_user()
async def help_command(ctx):
    help_text = """
**📋 Spy Bot Help Guide:**

**!spy [user_id] [channel_id]** - Start spying on a user
• channel_id - Channel where logs will be sent (optional)
• user_id - ID of the user to spy on (required)

**!unspy [user_id]** - Stop spying on a user
• user_id - ID of the user to stop spying on
**!list** - Show current spy targets



**The bot tracks:**
• 🟢 Online/Offline status
• 🎮 Gaming activity
• 🎤 Voice channel activity
• ⌨️ Typing activity

If channel_id is not provided, logs will be saved to a text file.
"""
    await ctx.send(help_text)

# Your bot token (will be replaced by setup script)
bot.run('or du it manually')