#!/usr/bin/env python3
"""
Delta Key System - FULL DEBUG + POLLING
"""

import os, asyncio, re, yaml, traceback, time
import discord

TOKEN_FILE = "/storage/emulated/0/Download/token.txt"
CFG_FILE = os.path.expanduser("~/.delta_key_system.yaml")
GUILD_ID = 1424475459441262807
CHANNEL_ID = 1509123025381888020

def get_token():
    if os.path.exists(TOKEN_FILE):
        return open(TOKEN_FILE).read().strip()
    print("[DEBUG] Token file not found!")
    return ""

def load_cfg():
    if os.path.exists(CFG_FILE):
        return yaml.safe_load(open(CFG_FILE)) or {}
    return {}

def save_cfg(data):
    yaml.dump(data, open(CFG_FILE, "w"))

async def send_real_bypass(link: str) -> str:
    token = get_token()
    if not token:
        print("[DEBUG] No token!")
        return ""
    
    print(f"[DEBUG] Token loaded: {token[:25]}...")
    print(f"[DEBUG] Guild: {GUILD_ID} | Channel: {CHANNEL_ID}")
    
    client = discord.Client()
    key_found = None

    @client.event
    async def on_ready():
        nonlocal key_found
        print("[DEBUG] Discord client ready!")
        
        try:
            guild = client.get_guild(GUILD_ID)
            channel = guild.get_channel(CHANNEL_ID)
            
            if not guild or not channel:
                print("[DEBUG] ERROR: Guild or Channel not found!")
                await client.close()
                return
            
            print(f"[DEBUG] Channel: {channel.name}")
            
            commands = await guild.application_commands()
            bypass_cmd = next((c for c in commands if c.name == "bypass"), None)
            
            if not bypass_cmd:
                print("[DEBUG] ERROR: /bypass command not found!")
                await client.close()
                return
            
            print(f"[DEBUG] Sending /bypass command...")
            await bypass_cmd(channel, url=link)
            print("[DEBUG] Command sent! Starting poll...")
            
            # Poll for 20 seconds
            for i in range(20):
                await asyncio.sleep(1)
                
                try:
                    last_msg = await channel.fetch_message(channel.last_message_id)
                    full_text = last_msg.content + " " + str(last_msg.embeds)
                    
                    if i % 3 == 0:
                        print(f"[DEBUG] Poll {i}s - Last msg: {last_msg.content[:60]}...")
                    
                    m = re.search(r"FREE_[A-Za-z0-9_\-]{10,}", full_text)
                    if m:
                        key_found = m.group(0)
                        print(f"[DEBUG] ✅ KEY FOUND: {key_found}")
                        try:
                            await last_msg.delete()
                            print("[DEBUG] Message deleted")
                        except Exception as e:
                            print(f"[DEBUG] Delete error: {e}")
                        break
                        
                except Exception as e:
                    print(f"[DEBUG] Poll error at {i}s: {e}")
            
            if not key_found:
                print("[DEBUG] ❌ No key found after 20 seconds")
        
        except Exception as e:
            print(f"[DEBUG] FATAL ERROR: {e}")
            traceback.print_exc()
        
        await client.close()
        print("[DEBUG] Client closed")

    try:
        await client.start(token)
    except Exception as e:
        print(f"[DEBUG] Start error: {e}")
        traceback.print_exc()
    
    return key_found or ""

def get_key_from_discord(link: str) -> str:
    return asyncio.run(send_real_bypass(link))

def main():
    cfg = load_cfg()
    while True:
        os.system("clear")
        print("\033[96m╔════════════════════════════════════════════╗")
        print("\033[96m║\033[1m     DELTA KEY SYSTEM - DEBUG POLL     \033[0m\033[96m║")
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
            print("\033[96m › Starting FULL DEBUG POLL...\033[0m")
            key = get_key_from_discord(link)
            if key.startswith("FREE_"):
                print(f"\033[92m ✔ FINAL KEY: {key}\033[0m")
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
