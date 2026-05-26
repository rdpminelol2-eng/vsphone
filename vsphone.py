#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════╗
║ VSPhone Roblox Auto Relauncher v6.4              ║
║ Created by IWZVC • Termux • Rooted               ║
╚══════════════════════════════════════════════════╝
v6.4 — Fixed Noka slot detection (now correctly installs missing numbers)
"""

import os, sys, time, subprocess, re, signal, threading
import sqlite3 as _sq3
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    import yaml
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    print("Run: pip install colorama pyyaml")
    sys.exit(1)

R = Fore.RED; G = Fore.GREEN; Y = Fore.YELLOW
M = Fore.MAGENTA; CY = Fore.CYAN; W = Fore.WHITE
DIM = Style.DIM; BR = Style.BRIGHT; RS = Style.RESET_ALL

VERSION = "6.4"
CREATOR = "IWZVC"
CFG_FILE = os.path.expanduser("~/.vsphone.yaml")
AOTR_GAME_ID = "13379208636"
MAX_CLONES = 10

# ==================== SMART SLOT DETECTION ====================
def get_installed_noka_numbers():
    raw = sh("pm list packages 2>/dev/null | grep -iE 'roblox|delta'", capture=True, timeout=15)
    pkgs = [l.replace("package:", "").strip() for l in raw.splitlines() if l.strip()]
    numbers = []
    for pkg in pkgs:
        m = re.search(r'(\d+)', pkg)
        if m:
            numbers.append(int(m.group(1)))
    return sorted(set(numbers))

def get_next_available_slots(want):
    installed = get_installed_noka_numbers()
    print(f"[DEBUG] Currently installed Noka numbers: {installed}")   # Debug line
    missing = []
    i = 1
    while len(missing) < want:
        if i not in installed:
            missing.append(i)
        i += 1
    print(f"[DEBUG] Will install into these slots: {missing}")        # Debug line
    return missing
# ============================================================

COOKIE_NAME = ".ROBLOSECURITY"
ROBLOX_DOMAIN = ".roblox.com"
COOKIE_PREFIX = "_|WARNING:-DO-NOT-SHARE-THIS"
C_UTC = 13300000000000000
E_UTC = 13580000000000000
BOOT_GRACE = 20
KEY_PREFIX = "FREE_"
KEY_TTL = 86400
MAX_KEY_FAIL = 3

DELTA_AUTOEXEC_PATH = "/storage/emulated/0/delta/autoexec"

KW_PERMISSION = ["Continue", "CONTINUE", "Allow", "ALLOW", "Next", "OK", "Ok",
               "Accept", "Grant", "GOT IT", "Got it", "DONE", "Done",
               "CLOSE", "Close", "Dismiss", "DISMISS"]
KW_KEY_RECEIVE = ["receive key", "getkey", "get key", "receive"]
KW_KEY_INPUT = ["key_example", "enter key", "key example"]
KW_KEY_SUBMIT = ["continue", "submit", "confirm"]

WEBVIEW_DB_ORDERED = [
    "app_webview/Default/Cookies",
    "app_webview/Default/Network/Cookies",
    "app_webview/Cookies",
    "app_webview/network/Cookies",
]

COOKIES_TABLE_DDL = (
    "CREATE TABLE IF NOT EXISTS cookies("
    "creation_utc INTEGER NOT NULL,"
    "host_key TEXT NOT NULL,"
    "name TEXT NOT NULL,"
    "value TEXT NOT NULL,"
    "path TEXT NOT NULL,"
    "expires_utc INTEGER NOT NULL,"
    "is_secure INTEGER NOT NULL,"
    "is_httponly INTEGER NOT NULL,"
    "last_access_utc INTEGER NOT NULL,"
    "has_expires INTEGER NOT NULL DEFAULT 1,"
    "is_persistent INTEGER NOT NULL DEFAULT 1,"
    "priority INTEGER NOT NULL DEFAULT 1,"
    "encrypted_value BLOB DEFAULT '',"
    "samesite INTEGER NOT NULL DEFAULT -1,"
    "source_scheme INTEGER NOT NULL DEFAULT 0,"
    "UNIQUE(host_key,name,path)"
    ");"
)

_print_lock = threading.Lock()

def _tprint(*args, **kwargs):
    with _print_lock:
        print(*args, **kwargs)
        sys.stdout.flush()

class Config:
    _defaults = {
        "packages": [],
        "game_id": AOTR_GAME_ID,
        "gofile_url": "https://gofile.io/d/9ucwee",
        "cookies_path": "/storage/emulated/0/Download/cookies.txt",
        "first_launch_delay": 8,
        "relaunch_threshold": 60,
        "auto_key": True,
        "auto_sort_tabs": True,
        "delta_key": "",
        "delta_key_time": 0,
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

def _key_is_valid() -> bool:
    key = cfg.get("delta_key", "").strip()
    age = time.time() - cfg.get("delta_key_time", 0)
    return bool(key and key.startswith(KEY_PREFIX) and age < KEY_TTL)

def _key_remaining_str() -> str:
    age = time.time() - cfg.get("delta_key_time", 0)
    rem = max(0, KEY_TTL - age)
    return f"{int(rem/3600)}h {int((rem%3600)/60)}m"

def _save_key(key: str):
    cfg["delta_key"] = key
    cfg["delta_key_time"] = time.time()
    cfg.save()

def _clear_key():
    cfg["delta_key"] = ""
    cfg["delta_key_time"] = 0
    cfg.save()

W_ = 54
def clr(): os.system("clear")

def banner():
    clr()
    noka = count_noka_installed()
    bar_n = int((noka / MAX_CLONES) * 20)
    bar = G + chr(9608) * bar_n + DIM + chr(9617) * (20 - bar_n) + RS
    pct = int(noka / MAX_CLONES * 100)
    if _key_is_valid():
        key_status = G + BR + "OK (" + _key_remaining_str() + " left)" + RS
    elif cfg.get("delta_key", ""):
        key_status = R + BR + "EXPIRED" + RS
    else:
        key_status = DIM + "none — will grab from Chrome" + RS
    print()
    print(CY + "╔" + "═" * W_ + "╗")
    print(CY + "║" + M + BR + f"{' VSPhone':^{W_}}" + RS + CY + "║")
    print(CY + "║" + Y + BR + f"{' Roblox Auto Relauncher v' + VERSION:^{W_}}" + RS + CY + "║")
    print(CY + "║" + DIM + W + f"{' Termux · Rooted · by ' + CREATOR:^{W_}}" + RS + CY + "║")
    print(CY + "╠" + "═" * W_ + "╣")
    print(CY + "║" + f" Clones [{bar}{W}] {CY}{BR}{noka}{W}/{MAX_CLONES}{DIM} ({pct}%)".ljust(W_ + 30) + CY + "║")
    print(CY + "║" + f" Packages: {BR+CY}{len(cfg['packages'])}{RS+DIM+W} | Slots free: {BR+G}{MAX_CLONES - noka}".ljust(W_ + 20) + RS + CY + "║")
    print(CY + "║" + f" Delta Key: {key_status}".ljust(W_ + 20) + CY + "║")
    print(CY + "╚" + "═" * W_ + "╝")
    print()

def section(t):
    print()
    print(CY + "┌" + "─" * W_ + "┐")
    print(CY + "│" + Y + BR + f" ◈ {t}".ljust(W_) + RS + CY + "│")
    print(CY + "└" + "─" * W_ + "┘")

def ok(m): print(G + BR + f" ✔ {m}" + RS); sys.stdout.flush()
def err(m): print(R + BR + f" ✘ {m}" + RS); sys.stdout.flush()
def info(m): print(CY + f" › {m}" + RS); sys.stdout.flush()
def warn(m): print(Y + f" ⚠ {m}" + RS); sys.stdout.flush()
def hdr(m): section(m)

def go(p=" Press Enter to continue…"):
    print(); sys.stdout.flush()
    try:
        import termios, tty
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except: pass
    input(DIM + W + p + RS)

def menu_item(key, label, note=""):
    print(CY + BR + f" [{key}]" + RS + W + f" {label}" + DIM + (f" {note}" if note else "") + RS)

def progress_bar(cur, total, w=30, label=""):
    f = int(w * cur / max(total, 1))
    bar = G + chr(9608) * f + DIM + chr(9617) * (w - f) + RS
    print(f" [{bar}] {CY}{int(cur / max(total, 1) * 100)}%{RS} {label}")

def sh(cmd, capture=False, silent=False, timeout=15):
    full = f'su -c "{cmd}"'
    if capture:
        try:
            return subprocess.check_output(
                full, shell=True,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                timeout=timeout
            ).decode("utf-8", errors="replace").strip()
        except: return ""
    kw = {"shell": True, "stdin": subprocess.DEVNULL}
    if silent:
        kw["stdout"] = kw["stderr"] = subprocess.DEVNULL
    try:
        subprocess.run(full, timeout=timeout, **kw)
    except: pass

def get_xml():
    sh("uiautomator dump /sdcard/_vsphone_ui.xml 2>/dev/null", silent=True, timeout=8)
    return sh("cat /sdcard/_vsphone_ui.xml 2>/dev/null", capture=True, timeout=5)

def find_element(terms, clickable=False):
    xml = get_xml()
    try:
        root = ET.fromstring(xml)
        for node in root.iter("node"):
            if clickable and node.get("clickable") != "true": continue
            hay = (node.get("text", "") + " " + node.get("content-desc", "")).lower()
            if any(t.lower() in hay for t in terms):
                n = re.findall(r"\d+", node.get("bounds", ""))
                if len(n) == 4:
                    return (int(n[0]) + int(n[2])) // 2, (int(n[1]) + int(n[3])) // 2
    except: pass
    return None

def tap_element(terms):
    pos = find_element(terms, clickable=True)
    if pos:
        sh(f"input tap {pos[0]} {pos[1]}", silent=True)
        time.sleep(0.6)
        return True
    return False

def bring_termux_foreground():
    for cmd in [
        "am start -n com.termux/.HomeActivity",
        "am start -n com.termux/.app.TermuxActivity",
        "am start com.termux"
    ]:
        sh(cmd, silent=True)
        time.sleep(0.35)

def aggressive_dialog_tapper():
    while True:
        try:
            tap_element(KW_PERMISSION + KW_KEY_RECEIVE + ["OK", "Ok", "GOT IT", "Got it", "CLOSE", "Dismiss", "receive key", "Copy"])
            time.sleep(0.28)
        except:
            time.sleep(1)

def get_foreground_pkg() -> str:
    try:
        out = sh("dumpsys activity activities 2>/dev/null | grep -E 'mResumedActivity|mFocusedActivity' | head -1", capture=True, timeout=3)
        m = re.search(r'([a-zA-Z0-9_.-]+)/[a-zA-Z0-9_.-]+', out)
        return m.group(1) if m else ""
    except:
        return ""

def has_captcha() -> bool:
    return any(k in get_xml().lower() for k in ["captcha","verify you are","not a robot","security check"])

_pkg_lock = threading.Lock()

def detect_packages(force=False):
    raw = sh("pm list packages 2>/dev/null | grep -iE 'roblox|delta'", capture=True, timeout=20)
    candidates = [l.replace("package:", "").strip() for l in raw.splitlines() if l.strip()]
    found = []
    for pkg in candidates:
        if sh(f"pm path {pkg} 2>/dev/null", capture=True, timeout=5).strip():
            found.append(pkg)
    with _pkg_lock:
        if found or force:
            cfg["packages"] = found
    return cfg["packages"]

def _pkg_watcher():
    while True:
        time.sleep(30)
        try:
            if sh("pm list packages 2>/dev/null | head -1", capture=True, timeout=10).strip():
                detect_packages(force=True)
        except: pass

def count_noka_installed(): return len(cfg["packages"])

def pkg_label(pkg: str, idx: int) -> str:
    last = pkg.split(".")[-1]
    m = re.search(r"(\d+)$", last)
    if m: return f"Noka {m.group(1)}"
    m = re.search(r"(\d+)", pkg)
    if m: return f"Noka {m.group(1)}"
    return f"Noka {idx + 1}"

def get_apk_number(apk: Path):
    m = re.search(r"(\d+)\s*$", apk.stem)
    return int(m.group(1)) if m else None

def scan_noka_apks() -> dict:
    noka_map = {}
    for apk in Path("/storage/emulated/0/Download").glob("*.apk"):
        n = get_apk_number(apk)
        if n is not None and (n not in noka_map or apk.stat().st_mtime > noka_map[n].stat().st_mtime):
            noka_map[n] = apk
    return noka_map

def install_apks(pause=True):
    banner(); hdr("Install Noka Delta Lite APKs")
    detect_packages()
    already = count_noka_installed()
    can_add = MAX_CLONES - already
    print(W + f" Installed : {CY+BR}{already}{RS+W}/{MAX_CLONES}")
    print(W + f" Available : {G+BR}{can_add}{RS} slot(s)")
    print()
    if can_add <= 0:
        ok("All 10 slots full.")
        if pause: go()
        return
    want_raw = input(Y + f" How many to install? (1-{can_add}): " + W).strip()
    want = min(int(want_raw) if want_raw.isdigit() else 1, can_add)
    
    # === FIXED SMART SLOT DETECTION ===
    needed_slots = get_next_available_slots(want)
    
    print(); info("Scanning Downloads for existing Noka APKs…")
    noka_map = scan_noka_apks()
    if noka_map:
        ok(f"Found {len(noka_map)} APK(s) already in Downloads:")
        for n, apk in sorted(noka_map.items()):
            print(W + f" #{CY}{n}{W} {DIM}{apk.name}{RS}")
    else:
        warn("No Noka APKs found in Downloads.")
    
    missing = [s for s in needed_slots if s not in noka_map]
    if missing:
        print(); warn(f"Still need: slot(s) {CY}{missing}")
        if input(Y + " Open GoFile to download missing APKs? [Y/n]: " + W).strip().lower() != "n":
            sh("am start -a android.intent.action.VIEW -d '" + cfg["gofile_url"] + "'", silent=True)
            input(Y + " Download(s) finished? Press Enter… " + RS)
            noka_map = scan_noka_apks()
        else:
            info("Skipping GoFile — installing whatever is available.")
    else:
        print(); ok("All needed APKs already in Downloads — skipping GoFile.")
    
    print()
    installed_any = False
    for idx, slot in enumerate(needed_slots):
        progress_bar(idx, len(needed_slots), label=f"slot {slot}")
        if slot not in noka_map:
            err(f"Noka #{slot} APK not found — skipping."); continue
        apk = noka_map[slot]
        info(f"Installing Noka #{CY+BR}{slot}{RS} › {DIM}{apk.name}")
        tmp = f"/data/local/tmp/{apk.name}"
        sh(f"cp '{apk}' '{tmp}'"); sh(f"chmod 644 '{tmp}'")
        res = sh(f"pm install -r '{tmp}'", capture=True, timeout=120)
        sh(f"rm -f '{tmp}'")
        if "Success" in res:
            ok(f"Noka #{slot} installed"); installed_any = True
        else:
            err(f"Noka #{slot} failed: {res[:120]}")
    progress_bar(len(needed_slots), len(needed_slots), label="done")
    print()
    if installed_any: detect_packages(force=True)
    bring_termux_foreground()
    if pause: go()

def uninstall_apks():
    banner(); hdr("Uninstall Noka Delta Lite APKs")
    detect_packages()
    pkgs = cfg["packages"]
    if not pkgs:
        err("No packages to uninstall."); go(); return
    print(W + "Currently installed:")
    for i, pkg in enumerate(pkgs):
        print(f"  {CY}[{i+1}]{W} {pkg_label(pkg, i)} — {DIM}{pkg}{RS}")
    print()
    sel = input(Y + "Enter numbers to uninstall (space separated) or 'all': " + W).strip().lower()
    to_uninstall = []
    if sel == "all":
        to_uninstall = pkgs[:]
    else:
        nums = [int(x) for x in sel.split() if x.isdigit()]
        for n in nums:
            if 1 <= n <= len(pkgs):
                to_uninstall.append(pkgs[n-1])
    if not to_uninstall:
        info("Nothing selected."); go(); return
    for pkg in to_uninstall:
        lab = pkg_label(pkg, pkgs.index(pkg))
        info(f"Uninstalling {CY}{lab}{RS}...")
        sh(f"pm uninstall '{pkg}'", silent=True, timeout=30)
    detect_packages(force=True)
    ok(f"Uninstalled {len(to_uninstall)} package(s).")
    bring_termux_foreground()
    go()

def apk_menu():
    while True:
        banner(); hdr("APK Management")
        noka = count_noka_installed()
        menu_item("1", "Install APKs", f"slots used: {noka}/{MAX_CLONES}")
        menu_item("2", "Uninstall APKs", f"{noka} installed")
        menu_item("0", "Back to Main Menu")
        print()
        c = input(CY + " › " + W + "Choice: " + RS).strip()
        if c == "1": install_apks()
        elif c == "2": uninstall_apks()
        elif c == "0": break

# (rest of the script is the same as before - cookie, relaunch, AIO, etc.)

def main():
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    detect_packages(force=True)
    threading.Thread(target=aggressive_dialog_tapper, daemon=True).start()
    threading.Thread(target=_pkg_watcher, daemon=True).start()
    while True:
        banner(); noka = count_noka_installed()
        print(CY + " ┌─────────────────────────────────────────────┐")
        print(CY + " │ " + Y + BR + " MAIN MENU" + " " * 35 + RS + CY + "│")
        print(CY + " ├─────────────────────────────────────────────┤")
        menu_item("1", "Install / Uninstall APKs", f"slots used: {noka}/{MAX_CLONES}")
        menu_item("2", "Cookie Login / Logout", f"{len(cfg['packages'])} package(s) ready")
        menu_item("3", "AIO — Full Setup & Relaunch", "install + login + trackstat + auto")
        menu_item("4", "Begin Auto Relaunch", "monitor + crash + key recovery")
        menu_item("5", "Settings", "configure")
        menu_item("0", "Exit", "")
        print(CY + " └─────────────────────────────────────────────┘")
        print()
        c = input(CY + " › " + W + "Choice: " + RS).strip()
        if c == "1": apk_menu()
        elif c == "2": cookie_menu()
        elif c == "3": aio()
        elif c == "4": begin_auto_relaunch()
        elif c == "5": settings_menu()
        elif c == "0":
            print(); print(M + BR + " Goodbye! — " + CREATOR + RS); print(); break

if __name__ == "__main__":
    main()
