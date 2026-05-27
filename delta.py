#!/usr/bin/env python3
"""
Delta Key System v4.8 - FINAL (Search "Bypass" + Delete)
"""

import os, asyncio, re, yaml
import discord

TOKEN_FILE = "/storage/emulated/0/Download/token.txt"
CFG_FILE = os.path.expanduser("~/.delta_key_system.yaml")
GUILD_ID = 1424475459441262807
CHANNEL_ID = 1509123025381888020

def get_token():
    if os.path.exists(TOKEN_FILE):
        return open(TOKEN_FILE).read().strip()
    return ""

def load_cfg():
    if os.path.exists(CFG_FILE):
        return yaml.safe_load(open(CFG_FILE)) or {}
    return {}

def save_cfg(data):
    yaml.dump(data, open(CFG_FILE, "w"))

async def send_real_bypass(link: str) -> str:
    token = get_token()
    if not token: return ""
    client = discord.Client()
    key_found = None

    @client.event
    async def on_ready():
        nonlocal key_found
        guild = client.get_guild(GUILD_ID)
        channel = guild.get_channel(CHANNEL_ID)
        
        commands = await guild.application_commands()
        bypass_cmd = next((c for c in commands if c.name == "bypass"), None)
        
        if bypass_cmd:
            await bypass_cmd(channel, url=link)
            await asyncio.sleep(10)
            
            # Get last 3 messages and find the one with "Bypass"
            messages = [msg async for msg in channel.history(limit=3)]
            
            for msg in messages:
                if "bypass" in msg.content.lower() or any("**Bypass Success**" in str(e).lower() for e in msg.embeds):
                    full_text = msg.content + " " + str(msg.embeds)
                    m = re.search(r"FREE_[A-Za-z0-9_\-]{10,}", full_text)
                    if m:
                        key_found = m.group(0)
                        # Delete the message
                        try:
                            await msg.delete()
                        except:
                            pass
                        break
        
        await client.close()

    await client.start(token)
    return key_found or ""

def get_key_from_discord(link: str) -> str:
    return asyncio.run(send_real_bypass(link))

def main():
    cfg = load_cfg()
    while True:
        os.system("clear")
        print("\033[96m╔════════════════════════════════════════════╗")
        print("\033[96m║\033[1m     DELTA KEY SYSTEM v4.8 - FINAL     \033[0m\033[96m║")
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
