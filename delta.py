#!/usr/bin/env python3
"""
Delta Key System v3.5 - FINAL CLEAN VERSION
- Token loaded from /storage/emulated/0/Download/token.txt
- Channel ID HARDCODED: 1509123025381888020
- Correct format: /bypass url:{link}
- Auto-delete bypass bot messages
- Supports both user and bot tokens
- Safe to push to GitHub (no token in code)
"""

import os, sys, time, subprocess, re, threading, signal, json
try:
    import yaml
    import requests
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    print("Run: pkg update -y && pkg install -y python python-pip termux-api openssl openssl-tool && pip install pyyaml colorama requests")
    sys.exit(1)

R = Fore.RED; G = Fore.GREEN; Y = Fore.YELLOW
M = Fore.MAGENTA; CY = Fore.CYAN; W = Fore.WHITE
DIM = Style.DIM; BR = Style.BRIGHT; RS = Style.RESET_ALL

VERSION = "3.5-FINAL"
CREATOR = "IWZVC + Grok"
CFG_FILE = os.path.expanduser("~/.delta_key_system.yaml")
TOKEN_FILE = "/storage/emulated/0/Download/token.txt"
HARDCODED_CHANNEL_ID = "1509123025381888020"   # <-- Your channel

KEY_PREFIX = "FREE_"
KEY_TTL = 86400
DISCORD_API = "https://discord.com/api/v10"

KEY_PATTERN = re.compile(r"FREE_[A-Za-z0-9_\-]{10,}")
KW_KEY_INPUT = ["key_example", "KEY_Example", "enter key", "key example", "paste key", "your key", "key input"]
KW_KEY_SUBMIT = ["continue", "submit", "confirm", "continue key", "submit key"]
AM_FRONT_FLAG = "0x20000000"

_print_lock = threading.Lock()
def _tprint(*args, **kwargs):
    with _print_lock:
        print(*args, **kwargs)
        sys.stdout.flush()

class Config:
    _defaults = {
        "packages": [],
        "delta_key_link": "",
        "delta_key": "",
        "delta_key_time": 0,
        "check_interval": 300,
        "auto_delete_bot_messages": True,
        "auto_enter_on_grab": True,
    }
    def __init__(self):
        self.data = dict(self._defaults)
        if os.path.exists(CFG_FILE):
            try:
                with open(CFG_FILE) as f:
                    self.data.update(yaml.safe_load(f) or {})
            except: pass
    def save(self):
        with open(CFG_FILE, "w") as f: yaml.dump(self.data, f)
    def __getitem__(self, k): return self.data.get(k, self._defaults.get(k))
    def __setitem__(self, k, v): self.data[k] = v; self.save()
    def get(self, k, default=None): return self.data.get(k, default)

cfg = Config()

def get_discord_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            token = f.read().strip()
            if token:
                return token
    print()
    print(Y + "First time setup - enter your Discord token:")
    token = input(CY + "Token: " + W).strip()
    if token:
        with open(TOKEN_FILE, "w") as f:
            f.write(token)
        ok("Token saved to token.txt")
        return token
    err("No token provided")
    return ""

def sh(cmd, capture=False, silent=False, timeout=15):
    full = f'su -c "{cmd}"'
    if capture:
        try:
            return subprocess.check_output(full, shell=True, stderr=subprocess.DEVNULL, timeout=timeout).decode("utf-8", errors="replace").strip()
        except: return ""
    kw = {"shell": True, "stdin": subprocess.DEVNULL}
    if silent: kw["stdout"] = kw["stderr"] = subprocess.DEVNULL
    try: subprocess.run(full, timeout=timeout, **kw)
    except: pass

def clr(): os.system("clear")
def ok(m): print(G + BR + f" ✔ {m}" + RS); sys.stdout.flush()
def err(m): print(R + BR + f" ✘ {m}" + RS); sys.stdout.flush()
def info(m): print(CY + f" › {m}" + RS); sys.stdout.flush()
def warn(m): print(Y + f" ⚠ {m}" + RS); sys.stdout.flush()

W_ = 54
def banner():
    clr()
    print()
    print(CY + "╔" + "═"*W_ + "╗")
    print(CY + "║" + M + BR + f"{' DELTA KEY SYSTEM v' + VERSION:^{W_}}" + RS + CY + "║")
    print(CY + "║" + DIM + W + f"{' FINAL VERSION - HARDCODED CHANNEL':^{W_}}" + RS + CY + "║")
    print(CY + "╠" + "═"*W_ + "╣")
    key = cfg.get("delta_key", "")
    if key and key.startswith(KEY_PREFIX):
        age = time.time() - cfg.get("delta_key_time", 0)
        rem = max(0, KEY_TTL - age)
        status = G + BR + f"OK — {int(rem/3600)}h {int((rem%3600)/60)}m left" + RS
    else:
        status = R + "NONE" + RS
    link_short = (cfg.get("delta_key_link", "")[:40] + "...") if cfg.get("delta_key_link") else DIM + "not set" + RS
    print(CY + "║" + f" Key Status : {status}".ljust(W_+20) + CY + "║")
    print(CY + "║" + f" Link       : {CY}{link_short}".ljust(W_+20) + CY + "║")
    print(CY + "║" + f" Channel    : {CY}{HARDCODED_CHANNEL_ID}".ljust(W_+20) + CY + "║")
    print(CY + "║" + f" Packages   : {BR+CY}{len(cfg.get('packages', []))}{RS+DIM+W} ready".ljust(W_+20) + CY + "║")
    print(CY + "╚" + "═"*W_ + "╝")
    print()

def section(t):
    print()
    print(CY + "┌" + "─"*W_ + "┐")
    print(CY + "│" + Y + BR + f" ◈ {t}".ljust(W_) + RS + CY + "│")
    print(CY + "└" + "─"*W_ + "┘")

def menu_item(key, label, note=""):
    print(CY + BR + f" [{key}]" + RS + W + f" {label}" + DIM + (f"  {note}" if note else "") + RS)

def go(p=" Press Enter to continue…"):
    print(); sys.stdout.flush()
    try: import termios; termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except: pass
    input(DIM + W + p + RS)

def bring_to_front(pkg: str):
    sh(f"am start -f {AM_FRONT_FLAG} {pkg}", silent=True)
    time.sleep(1.2)

def detect_packages(force=False):
    raw = sh("pm list packages 2>/dev/null | grep -iE 'roblox|delta'", capture=True, timeout=15)
    found = [l.replace("package:","").strip() for l in raw.splitlines() if l.strip()]
    with threading.Lock():
        if found or force:
            cfg["packages"] = found
    return cfg["packages"]

def pkg_label(pkg: str, idx: int) -> str:
    last = pkg.split(".")[-1]
    m = re.search(r"(\d+)$", last)
    if m: return f"Noka {m.group(1)}"
    return f"Noka {idx+1}"

def _read_clipboard() -> str:
    out = sh("content query --uri content://com.android.clipboard/clip", capture=True, timeout=4)
    m = KEY_PATTERN.search(out)
    if m: return m.group(0)
    m = re.search(r"text=([^\s,\)]+)", out)
    if m and m.group(1).strip(): return m.group(1).strip()
    out = sh("termux-clipboard-get 2>/dev/null", capture=True, timeout=3)
    if out:
        m = KEY_PATTERN.search(out)
        if m: return m.group(0)
        return out.strip()
    return ""

def _set_clipboard(text: str):
    safe = text.replace("'", "\\'")
    sh(f"termux-clipboard-set '{safe}' 2>/dev/null", silent=True, timeout=3)
    sh(f"am broadcast -a clipper.set -e text '{safe}' 2>/dev/null", silent=True, timeout=3)

def _enter_key(key: str) -> bool:
    info(f"Entering key: {CY}{key[:22]}…{RS}")
    tapped = False
    for _ in range(5):
        if tapped: break
        tapped = tapped or tap_element(KW_KEY_INPUT)
        time.sleep(0.4)
    if not tapped:
        tap_element(["key", "example", "input", "paste", "enter key", "text field"])
    time.sleep(0.6)
    _set_clipboard(key)
    time.sleep(0.3)
    sh("input keyevent KEYCODE_PASTE", silent=True)
    time.sleep(0.4)
    tap_element(KW_KEY_SUBMIT)
    time.sleep(1.0)
    return True

def enter_key_into_all_packages(key: str = None):
    if key is None:
        key = cfg.get("delta_key", "")
    if not key.startswith(KEY_PREFIX):
        err("No valid key to enter!")
        return
    pkgs = cfg.get("packages", [])
    if not pkgs:
        detect_packages(force=True)
        pkgs = cfg.get("packages", [])
    if not pkgs:
        err("No packages found!")
        return
    ok(f"Entering key into {len(pkgs)} package(s)…")
    for i, pkg in enumerate(pkgs):
        label = pkg_label(pkg, i)
        bring_to_front(pkg)
        time.sleep(1.0)
        if _enter_key(key):
            ok(f"  {label} — key entered")
        else:
            err(f"  {label} — failed")
    ok("All packages updated!")

def get_xml() -> str:
    sh("uiautomator dump /sdcard/_delta_key_ui.xml 2>/dev/null", silent=True, timeout=5)
    return sh("cat /sdcard/_delta_key_ui.xml 2>/dev/null", capture=True, timeout=3)

def _parse_bounds(node):
    nums = re.findall(r"\d+", node.get("bounds", ""))
    if len(nums) == 4:
        return (int(nums[0]) + int(nums[2])) // 2, (int(nums[1]) + int(nums[3])) // 2
    return None

def find_element(terms, clickable=False, xml=None):
    if xml is None: xml = get_xml()
    try:
        root = ET.fromstring(xml)
        for node in root.iter("node"):
            if clickable and node.get("clickable") != "true": continue
            hay = (node.get("text","") + " " + node.get("content-desc","")).lower()
            if any(t.lower() in hay for t in terms):
                pos = _parse_bounds(node)
                if pos: return pos
    except: pass
    return None

def tap_element(terms, xml=None) -> bool:
    pos = find_element(terms, clickable=True, xml=xml)
    if pos:
        sh(f"input tap {pos[0]} {pos[1]}", silent=True)
        time.sleep(0.5)
        return True
    return False

from xml.etree import ElementTree as ET

# ─────────────────────────────────────────────────────────────────────────────
# DISCORD (with hardcoded channel)
# ─────────────────────────────────────────────────────────────────────────────
def post_link_to_discord(link: str, token: str) -> str:
    auth = token if token.startswith("Bot ") else f"Bot {token}"
    headers = {
        "Authorization": auth,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {"content": f"/bypass url:{link}"}
    url = f"{DISCORD_API}/channels/{HARDCODED_CHANNEL_ID}/messages"
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        if r.status_code == 200:
            msg_id = r.json().get("id", "")
            ok(f"Link posted (msg ID: {msg_id})")
            return msg_id
        else:
            err(f"Post failed: {r.status_code}")
            return ""
    except Exception as e:
        err(f"Post error: {e}")
        return ""

def poll_discord_for_key(token: str, timeout: int = 120, poll_interval: float = 2.0) -> tuple:
    auth = token if token.startswith("Bot ") else f"Bot {token}"
    headers = {"Authorization": auth, "User-Agent": "Mozilla/5.0"}
    url = f"{DISCORD_API}/channels/{HARDCODED_CHANNEL_ID}/messages?limit=30"
    deadline = time.time() + timeout
    seen_ids = set()

    info("Polling Discord for bypass reply...")
    while time.time() < deadline:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                time.sleep(poll_interval)
                continue
            for msg in r.json():
                msg_id = msg.get("id")
                if msg_id in seen_ids:
                    continue
                seen_ids.add(msg_id)

                # Look for "Mobile Version" first
                embeds = msg.get("embeds", [])
                for embed in embeds:
                    for field in embed.get("fields", []):
                        if "Mobile Version" in field.get("name", ""):
                            m = KEY_PATTERN.search(field.get("value", ""))
                            if m:
                                return m.group(0), msg_id

                # Fallback
                content = msg.get("content", "") + " " + json.dumps(embeds)
                m = KEY_PATTERN.search(content)
                if m:
                    return m.group(0), msg_id
        except Exception as e:
            warn(f"Poll error: {e}")
        time.sleep(poll_interval)
    return "", ""

def delete_discord_message(token: str, message_id: str) -> bool:
    if not message_id:
        return False
    auth = token if token.startswith("Bot ") else f"Bot {token}"
    headers = {"Authorization": auth, "User-Agent": "Mozilla/5.0"}
    url = f"{DISCORD_API}/channels/{HARDCODED_CHANNEL_ID}/messages/{message_id}"
    try:
        r = requests.delete(url, headers=headers, timeout=10)
        if r.status_code in (200, 204):
            info("Bypass bot message deleted")
            return True
        return False
    except:
        return False

def get_key_from_discord() -> str:
    link = cfg.get("delta_key_link", "").strip()
    if not link:
        err("No Delta Key Link set!")
        return ""

    token = get_discord_token()
    if not token:
        return ""

    posted_msg_id = post_link_to_discord(link, token)
    if not posted_msg_id:
        return ""

    time.sleep(4)
    key, bot_msg_id = poll_discord_for_key(token)

    if key.startswith(KEY_PREFIX):
        if cfg.get("auto_delete_bot_messages", True) and bot_msg_id:
            delete_discord_message(token, bot_msg_id)
        return key
    return ""

# ─────────────────────────────────────────────────────────────────────────────
# Core logic
# ─────────────────────────────────────────────────────────────────────────────
def _key_is_valid() -> bool:
    key = cfg.get("delta_key", "").strip()
    age = time.time() - cfg.get("delta_key_time", 0)
    return bool(key and key.startswith(KEY_PREFIX) and age < KEY_TTL)

def _save_key(key: str):
    cfg["delta_key"] = key
    cfg["delta_key_time"] = time.time()
    cfg.save()
    ok(f"Key saved (24h TTL): {key[:20]}…")

def _clear_key():
    cfg["delta_key"] = ""
    cfg["delta_key_time"] = 0
    cfg.save()

def force_grab_and_enter():
    banner(); section("Force Grab + Enter")
    if not cfg.get("delta_key_link"):
        err("Set Delta Key Link first!")
        go(); return
    key = get_key_from_discord()
    if key.startswith(KEY_PREFIX):
        _save_key(key)
        if cfg.get("auto_enter_on_grab", True):
            enter_key_into_all_packages(key)
    else:
        warn("No key from Discord.")
        manual = input(Y + "Paste FREE_ key manually: " + W).strip()
        if manual.startswith(KEY_PREFIX):
            _save_key(manual)
            enter_key_into_all_packages(manual)
    go()

def start_monitor():
    banner(); section("Background Monitor Started")
    def monitor():
        while True:
            try:
                if cfg.get("delta_key_link") and not _key_is_valid():
                    info("Key expired — posting to Discord...")
                    key = get_key_from_discord()
                    if key.startswith(KEY_PREFIX):
                        _save_key(key)
                        if cfg.get("auto_enter_on_grab", True):
                            enter_key_into_all_packages(key)
            except Exception as e:
                warn(f"Monitor error: {e}")
            time.sleep(cfg.get("check_interval", 300))
    t = threading.Thread(target=monitor, daemon=True)
    t.start()
    try:
        while True: time.sleep(3600)
    except KeyboardInterrupt:
        print(); ok("Monitor stopped.")

def settings_menu():
    while True:
        banner(); section("Settings")
        link = (cfg.get("delta_key_link", "")[:40] + "...") if cfg.get("delta_key_link") else DIM + "(not set)" + RS
        auto_del = G+BR+"ON" if cfg.get("auto_delete_bot_messages", True) else R+BR+"OFF"
        interval = cfg.get("check_interval")
        auto = G+BR+"ON" if cfg.get("auto_enter_on_grab", True) else R+BR+"OFF"

        print(W + f" {CY}[1]{W} Delta Key Link         {DIM}→ {CY}{link}")
        print(W + f" {CY}[2]{W} Auto-Delete Bot Msgs   {DIM}→ {auto_del}{RS}")
        print(W + f" {CY}[3]{W} Check Interval         {DIM}→ {Y}{interval}s")
        print(W + f" {CY}[4]{W} Auto-Enter on Grab     {DIM}→ {auto}{RS}")
        print(W + f" {CY}[5]{W} Clear Current Key")
        print(W + f" {CY}[6]{W} Detect Packages Now")
        print(W + f" {CY}[0]{W} Back"); print()
        c = input(CY + " › " + W + "Choice: " + RS).strip()

        if c == "1":
            new_link = input(Y + "Paste Delta Key Link: " + W).strip()
            if new_link.startswith("http"):
                cfg["delta_key_link"] = new_link
                ok("Saved.")
        elif c == "2":
            cfg["auto_delete_bot_messages"] = not cfg.get("auto_delete_bot_messages", True)
            ok("Toggled.")
        elif c == "3":
            v = input(Y + "Seconds (60-3600): " + W).strip()
            if v.isdigit() and 60 <= int(v) <= 3600:
                cfg["check_interval"] = int(v)
                ok("Saved.")
        elif c == "4":
            cfg["auto_enter_on_grab"] = not cfg.get("auto_enter_on_grab", True)
            ok("Toggled.")
        elif c == "5":
            _clear_key()
            ok("Key cleared.")
        elif c == "6":
            detect_packages(force=True)
            ok(f"Found {len(cfg['packages'])} packages.")
        elif c == "0":
            break

def main():
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    detect_packages(force=True)
    while True:
        banner()
        print(CY + " ┌─────────────────────────────────────────────┐")
        print(CY + " │ " + Y + BR + " DELTA KEY SYSTEM v3.5 — FINAL" + " " * 10 + RS + CY + "│")
        print(CY + " ├─────────────────────────────────────────────┤")
        menu_item("1", "Set Delta Key Link", "")
        menu_item("2", "Force Grab + Enter", "Discord + auto-delete")
        menu_item("3", "Enter Current Key to All", "")
        menu_item("4", "Start Background Monitor", "auto every 5min")
        menu_item("5", "Settings", "link, auto-delete, interval")
        menu_item("0", "Exit", "")
        print(CY + " └─────────────────────────────────────────────┘")
        print()
        c = input(CY + " › " + W + "Choice: " + RS).strip()
        if c == "1":
            settings_menu()
        elif c == "2":
            force_grab_and_enter()
        elif c == "3":
            enter_key_into_all_packages()
            go()
        elif c == "4":
            start_monitor()
        elif c == "5":
            settings_menu()
        elif c == "0":
            print(); print(M + BR + " Goodbye!" + RS)
            print()
            break

if __name__ == "__main__":
    main()
