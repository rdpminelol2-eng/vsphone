#!/usr/bin/env python3
"""
Delta Key System v4.12 - FINAL (User Token + Bot Token)
"""

import os, asyncio, re, yaml
import discord

USER_TOKEN_FILE = "/storage/emulated/0/Download/token.txt"
BOT_TOKEN_FILE = "/storage/emulated/0/Download/token2.txt"
CFG_FILE = os.path.expanduser("~/.delta_key_system.yaml")
GUILD_ID = 1424475459441262807
CHANNEL_ID = 1509123025381888020

def get_user_token():
    if os.path.exists(USER_TOKEN_FILE):
        return open(USER_TOKEN_FILE).read().strip()
    return ""

def get_bot_token():
    if os.path.exists(BOT_TOKEN_FILE):
        return open(BOT_TOKEN_FILE).read().strip()
    return ""

def load_cfg():
    if os.path.exists(CFG_FILE):
        return yaml.safe_load(open(CFG_FILE)) or {}
    return {}

def save_cfg(data):
    yaml.dump(data, open(CFG_FILE, "w"))

async def send_real_bypass(link: str) -> str:
    user_token = get_user_token()
    bot_token = get_bot_token()
    
    if not user_token or not bot_token:
        print("[DEBUG] Missing token(s)!")
        return ""
    
    print(f"[DEBUG] User token: {user_token[:20]}...")
    print(f"[DEBUG] Bot token: {bot_token[:20]}...")
    
    key_found = None
    
    # Step 1: Send slash command with USER token
    user_client = discord.Client()
    
    @user_client.event
    async def on_ready():
        guild = user_client.get_guild(GUILD_ID)
        channel = guild.get_channel(CHANNEL_ID)
        
        commands = await guild.application_commands()
        bypass_cmd = next((c for c in commands if c.name == "bypass"), None)
        
        if bypass_cmd:
            await bypass_cmd(channel, url=link)
            print("[DEBUG] Slash command sent with user token")
        
        await user_client.close()
    
    await user_client.start(user_token)
    
    # Step 2: Wait and read with BOT token
    await asyncio.sleep(10)
    
    bot_client = discord.Client()
    
    @bot_client.event
    async def on_ready():
        nonlocal key_found
        guild = bot_client.get_guild(GUILD_ID)
        channel = guild.get_channel(CHANNEL_ID)
        
        # Poll for key
        for i in range(15):
            await asyncio.sleep(1)
            try:
                last_msg = await channel.fetch_message(channel.last_message_id)
                full_text = last_msg.content + " " + str(last_msg.embeds)
                
                m = re.search(r"FREE_[A-Za-z0-9_\-]{10,}", full_text)
                if m:
                    key_found = m.group(0)
                    print(f"[DEBUG] Key found: {key_found}")
                    try:
                        await last_msg.delete()
                        print("[DEBUG] Message deleted with bot token")
                    except:
                        pass
                    break
            except Exception as e:
                print(f"[DEBUG] Poll error: {e}")
        
        await bot_client.close()
    
    await bot_client.start(bot_token)
    return key_found or ""

def get_key_from_discord(link: str) -> str:
    return asyncio.run(send_real_bypass(link))

def main():
    cfg = load_cfg()
    while True:
        os.system("clear")
        print("\033[96m╔════════════════════════════════════════════╗")
        print("\033[96m║\033[1m     DELTA KEY SYSTEM v4.12 - FINAL     \033[0m\033[96m║")
        print("\033[96m╚════════════════════════════════════════════╝\033[0m")
        
        link = cfg.get("delta_key_link", "")
        status = "\033[92m(link saved)\033[0m" if link else ""
        
        print(f"\n\033[96m[1]\033[97m Force Grab + Enter (Real Slash) {status}")
        print("\033[96m[2]\033[97m Enter Key to All Packages")
        print("\033[96m[3]\033[97m Set Delta Key Link")
        print("\033[96m[4]\033[97m Exit\n")
        
        c = input("\033[96m › \033[97m").strip()
        
        if c == "1":
            if not link:
                print("\033[93mNo link saved. Use option 3 first.\033[0m")
                input()
                continue
            print("\033[96m › Sending real /bypass command...\033[0m")
            key = get_key_from_discord(link)
            if key.startswith("FREE_"):
                print(f"\033[92m ✔ Key received: {key}\033[0m")
            else:
                print("\033[91m ✘ No key received\033[0m")
            input()
        
        elif c == "2":
            print("Key entering coming soon...")
            input()
        
        elif c == "3":
            new_link = input("\033[93mPaste Delta Key Link: \033[97m").strip()
            if new_link.startswith("http"):
                cfg["delta_key_link"] = new_link
                save_cfg(cfg)
                print("\033[92m ✔ Link saved permanently!\033[0m")
                input()
        
        elif c == "4":
            break

if __name__ == "__main__":
    main()
