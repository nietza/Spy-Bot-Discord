import os
import subprocess
import sys
import re

def install_rq():
    print("\nInstalling required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "discord.py"])
        return True
    except subprocess.CalledProcessError:
        print("Failed to install packages!")
        return False

def modify_main(bot_token):
    try:
        with open('main.py', 'r', encoding='utf-8') as file:
            content = file.read()

        pattern = r"bot\.run\(['\"].*['\"]\)"
        replacement = f"bot.run('{bot_token}')"
        
        modified_content = re.sub(pattern, replacement, content)
        
        with open('main.py', 'w', encoding='utf-8') as file:
            file.write(modified_content)

        with open('main.py', 'r', encoding='utf-8') as file:
            new_content = file.read()
        if f"bot.run('{bot_token}')" in new_content:
            print("Token successfully updated in main.py")
        else:
            print("Warning: Token might not have been updated correctly")

        return True
    except Exception as e:
        print(f"Error modifying main script: {e}")
        return False

def create_allowed_users(users):
#if empty - all users are allowed
    try:
        with open('allowed_users.txt', 'w') as file:
            if users:
                file.write('\n'.join(users))
        return True
    except Exception as e:
        print(f"Error creating allowed users file: {e}")
        return False

def setup():
    print("Welcome to Discord Spy Bot Setup!")
    print("-" * 40)

    bot_token = input("What is your bot token?: ").strip()
    while not bot_token:
        print("Token cannot be empty!")
        bot_token = input("What is your bot token?: ").strip()

    users_input = input("Which users are allowed to interact with a bot (state USER ID after space, or press Enter to allow all)?: ").strip()
    allowed_users = users_input.split() if users_input else []
    
    if not allowed_users:
        print("\nNo User IDs provided - all users will have access to bot commands!")
    
    print("\nStarting setup process...")

    if not install_rq():
        print("Setup failed at package installation!")
        return

    if not modify_main(bot_token):
        print("Setup failed at script modification!")
        return

    if not create_allowed_users(allowed_users):
        print("Setup failed at creating allowed users file!")
        return

    print("\n✅ Setup completed successfully!")
    print("✨ Your bot is ready to use!")
    print("\nYou can now run the bot using: python main.py")

if __name__ == "__main__":
    setup()