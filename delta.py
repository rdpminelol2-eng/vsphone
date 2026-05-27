#!/usr/bin/env python3
"""
Delta Key System v4.0 - FINAL CLEAN
- Real /bypass slash command (discord.py-self)
- Token loaded from /storage/emulated/0/Download/token.txt
- No tokens in code (safe for GitHub)
"""

import os, sys, time, subprocess, re, asyncio
import discord

TOKEN_FILE = "/storage/emulated/0/Download/token.txt"
GUILD_ID = 1424475459441262807
CHANNEL_ID = 1509123025381888020
KEY_PREFIX = "FREE_"

def get_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    print("Token file not found!")
    return ""

async def send_real_bypass(link: str) -> str:
    token = get_token()
    if not token:
        return ""
    
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
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
            await asyncio.sleep(6)
            async for msg in channel.history(limit=8):
                m = re.search(r"FREE_[A-Za-z0-9_\-]{10,}", msg.content)
                if m:
                    key_found = m.group(0)
                    break
        await client.close()

    await client.start(token, bot=False)
    return key_found or ""

def get_key_from_discord(link: str) -> str:
    return asyncio.run(send_real_bypass(link))

# ================== CLEAN MENU ==================
def banner():
    os.system("clear")
    print("\033[96m╔════════════════════════════════════════════╗")
    print("\033[96m║\033[1m     DELTA KEY SYSTEM v4.0 - FINAL     \033[0m\033[96m║")
    print("\033[96m╚════════════════════════════════════════════╝\033[0m")

def main():
    while True:
        banner()
        print("\n\033[96m[1]\033[97m Force Grab + Enter (Real Slash)")
        print("\033[96m[2]\033[97m Enter Key to All Packages")
        print("\033[96m[3]\033[97m Exit\n")
        
        c = input("\033[96m › \033[97m").strip()
        
        if c == "1":
            link = input("\033[93mPaste Delta Key Link: \033[97m").strip()
            if not link.startswith("http"): continue
            print("\033[96m › Sending real /bypass command...\033[0m")
            key = get_key_from_discord(link)
            if key.startswith(KEY_PREFIX):
                print(f"\033[92m ✔ Key received: {key[:30]}...\033[0m")
            else:
                print("\033[91m ✘ No key received\033[0m")
            input("\nPress Enter...")
        
        elif c == "2":
            print("Key entering coming soon...")
            input("\nPress Enter...")
        
        elif c == "3":
            break

if __name__ == "__main__":
    main()
