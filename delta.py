#!/usr/bin/env python3
"""
Delta Key System v6.1 - FINAL (Correct Discum)
"""

import os, re, yaml
import discum
from discum.utils.slash import SlashCommander

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

def send_real_bypass(link: str) -> str:
    token = get_token()
    if not token:
        print("[DEBUG] No token!")
        return ""
    
    print(f"[DEBUG] Token: {token[:25]}...")
    
    key_found = None
    
    bot = discum.Client(token=token, log=False)
    
    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            print("[DEBUG] Connected to Discord!")
            
            slash = SlashCommander(
                bot.getSlashCommands(str(GUILD_ID)).json()
            )
            
            print("[DEBUG] Sending slash command...")
            
            bot.triggerSlashCommand(
                slash.get("bypass"),
                channelID=str(CHANNEL_ID),
                guildID=str(GUILD_ID),
                data={"url": link}
            )
            
            print("[DEBUG] Slash command sent!")
    
    @bot.gateway.command
    def on_message(resp):
        nonlocal key_found
        
        if resp.event.message or resp.event.message_updated:
            msg = resp.parsed.auto()
            
            print(msg)  # RAW PAYLOAD DEBUG
            
            if msg.get("channel_id") != str(CHANNEL_ID):
                return
            
            full_text = msg.get("content", "")
            
            for embed in msg.get("embeds", []):
                if embed.get("title"):
                    full_text += " " + embed["title"]
                if embed.get("description"):
                    full_text += " " + embed["description"]
                for field in embed.get("fields", []):
                    full_text += f" {field.get('name','')}"
                    full_text += f" {field.get('value','')}"
            
            print(f"[DEBUG] FULL: {full_text}")
            
            m = re.search(r"FREE_[A-Za-z0-9]+", full_text)
            
            if m:
                key_found = m.group(0)
                print(f"[DEBUG] ✅ KEY FOUND: {key_found}")
                
                try:
                    bot.deleteMessage(str(CHANNEL_ID), msg.get("id"))
                    print("[DEBUG] Message deleted")
                except:
                    pass
                
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
        print("\033[96m║\033[1m     DELTA KEY SYSTEM v6.1 - FINAL     \033[0m\033[96m║")
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
