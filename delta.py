#!/usr/bin/env python3
"""
Delta Key System v6.6 - FINAL
"""

import os, re, yaml, asyncio
import discord
import discum

USER_TOKEN_FILE = "/storage/emulated/0/Download/token.txt"
CFG_FILE = os.path.expanduser("~/.delta_key_system.yaml")
GUILD_ID = "1424475459441262807"
CHANNEL_ID = "1509123025381888020"

def get_token():
    if os.path.exists(USER_TOKEN_FILE):
        return open(USER_TOKEN_FILE).read().strip()
    return ""

def load_cfg():
    if os.path.exists(CFG_FILE):
        return yaml.safe_load(open(CFG_FILE)) or {}
    return {}

def save_cfg(data):
    yaml.dump(data, open(CFG_FILE, "w"))

async def send_slash_command(link: str):
    token = get_token()
    if not token:
        return False
    
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        guild = client.get_guild(int(GUILD_ID))
        channel = guild.get_channel(int(CHANNEL_ID))
        
        commands = await guild.application_commands()
        bypass_cmd = next((c for c in commands if c.name == "bypass"), None)
        
        if bypass_cmd:
            await bypass_cmd(channel, url=link)
            print("[DEBUG] Slash command sent")
        
        await client.close()
    
    await client.start(token)
    return True

def send_real_bypass(link: str) -> str:
    token = get_token()
    if not token:
        print("[DEBUG] No token!")
        return ""
    
    print(f"[DEBUG] Token: {token[:25]}...")
    
    key_found = None
    
    print("[DEBUG] Sending slash command...")
    asyncio.run(send_slash_command(link))
    
    print("[DEBUG] Listening for key...")
    
    bot = discum.Client(token=token, log=False)
    
    @bot.gateway.command
    def on_message(resp):
        nonlocal key_found
        
        if resp.event.message or resp.event.message_updated:
            msg = resp.parsed.auto()
            
            if msg.get("channel_id") != CHANNEL_ID:
                return
            
            full_text = str(resp.raw)
            
            m = re.search(r"FREE_[A-Za-z0-9]+", full_text)
            
            if m:
                key_found = m.group(0)
                print(f"[DEBUG] ✅ KEY FOUND: {key_found}")
                bot.gateway.close()
    
    bot.gateway.run(auto_reconnect=True)
    
    return key_found or ""

def get_key_from_discord(link: str) -> str:
    return send_real_bypass(link)

def main():
    cfg = load_cfg()
    while True:
        os.system("clear")
        print("\033[96m╔════════════════════════════════════════════╗")
        print("\033[96m║\033[1m     DELTA KEY SYSTEM v6.6 - FINAL     \033[0m\033[96m║")
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
