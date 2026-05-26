#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════╗
║     VSPhone Roblox Auto Relauncher  v5.8         ║
║     Created by IWZVC  •  Termux • Rooted         ║
╚══════════════════════════════════════════════════╝
  v5.8 fixes:
  • detect_packages() never wipes list if pm returns 0
  • launch() → status=BOOTING for 20s grace before
    crash-check begins (fixes false crash / WAIT loop)
  • BOOTING state shown in table as "○ BOOT"
  • Delta key: grabs FREE_... from Chrome clipboard
    automatically — zero user input needed
  • grab_key_from_chrome() runs in KEY state
  • GitHub loader: load script via raw URL, no paste
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

R  = Fore.RED;    G = Fore.GREEN;  Y  = Fore.YELLOW
M  = Fore.MAGENTA; CY= Fore.CYAN;  W  = Fore.WHITE
DIM= Style.DIM;  BR = Style.BRIGHT; RS= Style.RESET_ALL

VERSION       = "5.8"
CREATOR       = "IWZVC"
CFG_FILE      = os.path.expanduser("~/.vsphone.yaml")
AOTR_GAME_ID  = "13379208636"
MAX_CLONES    = 10
COOKIE_NAME   = ".ROBLOSECURITY"
ROBLOX_DOMAIN = ".roblox.com"
COOKIE_PREFIX = "_|WARNING:-DO-NOT-SHARE-THIS"
C_UTC         = 13300000000000000
E_UTC         = 13580000000000000

BOOT_GRACE    = 20   # seconds after launch before crash-check starts
KEY_PREFIX    = "FREE_"   # Delta keys always start with this

# ── Permission / dialog keywords ──────────────────
KW_PERMISSION = [
    "Continue","CONTINUE","Allow","ALLOW","Next","OK","Ok",
    "Accept","Grant","GOT IT","Got it","DONE","Done",
    "CLOSE","Close","Dismiss","DISMISS",
]

# ── Key-system dialog keywords ────────────────────
KW_KEY_DIALOG  = ["enter key","receive key","welcome back","key system","key example","getkey"]
KW_KEY_RECEIVE = ["receive key","getkey","get key"]
KW_KEY_INPUT   = ["key_example","enter key","key example"]
KW_KEY_SUBMIT  = ["continue","submit","confirm"]

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

# ═══════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════
class Config:
    _defaults = {
        "packages":           [],
        "game_id":            AOTR_GAME_ID,
        "gofile_url":         "https://gofile.io/d/9ucwee",
        "cookies_path":       "/storage/emulated/0/Download/cookies.txt",
        "first_launch_delay": 8,
        "relaunch_threshold": 60,
        "auto_key":           True,
        "auto_sort_tabs":     True,
        "delta_key":          "",
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
    def __getitem__(self, k):       return self.data.get(k, self._defaults.get(k))
    def __setitem__(self, k, v):    self.data[k] = v; self.save()
    def get(self, k, default=None): return self.data.get(k, default)

cfg = Config()

# ═══════════════════════════════════════════════════
#  DISPLAY
# ═══════════════════════════════════════════════════
W_ = 54

def clr(): os.system("clear")

def banner():
    clr()
    noka  = count_noka_installed()
    bar_n = int((noka / MAX_CLONES) * 20)
    bar   = G + "█" * bar_n + DIM + "░" * (20 - bar_n) + RS
    pct   = int(noka / MAX_CLONES * 100)
    print()
    print(CY + "╔" + "═" * W_ + "╗")
    print(CY + "║" + M + BR + f"{'  VSPhone':^{W_}}"                            + RS + CY + "║")
    print(CY + "║" + Y + BR + f"{'  Roblox Auto Relauncher  v' + VERSION:^{W_}}" + RS + CY + "║")
    print(CY + "║" + DIM + W + f"{'  Termux · Rooted · by ' + CREATOR:^{W_}}"   + RS + CY + "║")
    print(CY + "╠" + "═" * W_ + "╣")
    print(CY + "║" + f"  Clones  [{bar}{W}]  {CY}{BR}{noka}{W}/{MAX_CLONES}{DIM} ({pct}%)".ljust(W_ + 30) + CY + "║")
    print(CY + "║" + f"  Packages: {BR+CY}{len(cfg['packages'])}{RS+DIM+W}  │  Slots free: {BR+G}{MAX_CLONES - noka}".ljust(W_ + 20) + RS + CY + "║")
    print(CY + "╚" + "═" * W_ + "╝")
    print()

def section(t):
    print()
    print(CY + "┌" + "─" * W_ + "┐")
    print(CY + "│" + Y + BR + f"  ◈  {t}".ljust(W_) + RS + CY + "│")
    print(CY + "└" + "─" * W_ + "┘")

def ok(m):   print(G  + BR + f"  ✔  {m}" + RS); sys.stdout.flush()
def err(m):  print(R  + BR + f"  ✘  {m}" + RS); sys.stdout.flush()
def info(m): print(CY +      f"  ›  {m}" + RS); sys.stdout.flush()
def warn(m): print(Y  +      f"  ⚠  {m}" + RS); sys.stdout.flush()
def hdr(m):  section(m)

def go(p="  Press Enter to continue…"):
    print(); sys.stdout.flush(); input(DIM + W + p + RS)

def menu_item(key, label, note=""):
    print(CY + BR + f" [{key}]" + RS + W + f" {label}" + DIM + (f"  {note}" if note else "") + RS)

def progress_bar(cur, total, w=30, label=""):
    f   = int(w * cur / max(total, 1))
    bar = G + "█" * f + DIM + "░" * (w - f) + RS
    print(f"  [{bar}] {CY}{int(cur / max(total, 1) * 100)}%{RS}  {label}")

# ═══════════════════════════════════════════════════
#  SHELL — timeout on every call
# ═══════════════════════════════════════════════════
def sh(cmd, capture=False, silent=False, timeout=15):
    full = f'su -c "{cmd}"'
    if capture:
        try:
            return subprocess.check_output(
                full, shell=True, stderr=subprocess.DEVNULL, timeout=timeout
            ).decode("utf-8", errors="replace").strip()
        except Exception:
            return ""
    kw = {"shell": True}
    if silent:
        kw["stdout"] = kw["stderr"] = subprocess.DEVNULL
    try:
        subprocess.run(full, timeout=timeout, **kw)
    except Exception:
        pass

# ═══════════════════════════════════════════════════
#  UI AUTOMATOR
# ═══════════════════════════════════════════════════
def get_xml():
    sh("uiautomator dump /sdcard/_vsphone_ui.xml 2>/dev/null", silent=True, timeout=8)
    return sh("cat /sdcard/_vsphone_ui.xml 2>/dev/null", capture=True, timeout=5)

def find_element(terms, clickable=False):
    xml = get_xml()
    try:
        root = ET.fromstring(xml)
        for node in root.iter("node"):
            if clickable and node.get("clickable") != "true":
                continue
            hay = (node.get("text", "") + " " + node.get("content-desc", "")).lower()
            if any(t.lower() in hay for t in terms):
                n = re.findall(r"\d+", node.get("bounds", ""))
                if len(n) == 4:
                    return (int(n[0]) + int(n[2])) // 2, (int(n[1]) + int(n[3])) // 2
    except Exception:
        pass
    return None

def tap_element(terms):
    pos = find_element(terms, clickable=True)
    if pos:
        sh(f"input tap {pos[0]} {pos[1]}", silent=True)
        time.sleep(0.8)
        return True
    return False

def type_text(text: str):
    # Use clipboard paste — avoids escaping issues entirely
    sh(f"am broadcast -a clipper.set -e text '{text}'", silent=True)
    time.sleep(0.3)
    sh("input keyevent KEYCODE_PASTE", silent=True)
    time.sleep(0.3)
    # Fallback: direct input if clipper not installed
    safe = re.sub(r"(['\"\\ &;|<>])", r"\\\1", text)
    sh(f"input text '{safe}'", silent=True)
    time.sleep(0.4)

# ═══════════════════════════════════════════════════
#  PACKAGES + LABEL MAPPING
#  CRITICAL: never wipe existing list if pm returns 0
# ═══════════════════════════════════════════════════
def detect_packages(force=False):
    raw   = sh("pm list packages 2>/dev/null | grep -iE 'roblox|delta'", capture=True, timeout=20)
    found = [l.replace("package:", "").strip() for l in raw.splitlines() if l.strip()]
    if found or force:
        cfg["packages"] = found
    # If found is empty and not forced → keep existing list (pm may have timed out)
    return cfg["packages"]

def count_noka_installed(): return len(cfg["packages"])

def pkg_label(pkg: str, idx: int) -> str:
    last = pkg.split(".")[-1]
    m = re.search(r"(\d+)$", last)
    if m: return f"Noka {m.group(1)}"
    m = re.search(r"(\d+)", pkg)
    if m: return f"Noka {m.group(1)}"
    return f"Noka {idx + 1}"

# ═══════════════════════════════════════════════════
#  APK INSTALL
# ═══════════════════════════════════════════════════
def get_apk_number(apk: Path):
    m = re.search(r"(\d+)\s*$", apk.stem)
    return int(m.group(1)) if m else None

def scan_noka_apks() -> dict:
    noka_map: dict[int, Path] = {}
    for apk in Path("/storage/emulated/0/Download").glob("*.apk"):
        n = get_apk_number(apk)
        if n is None: continue
        if n not in noka_map or apk.stat().st_mtime > noka_map[n].stat().st_mtime:
            noka_map[n] = apk
    return noka_map

def install_apks():
    banner(); hdr("Install Noka Delta Lite APKs")
    detect_packages()
    already = count_noka_installed(); can_add = MAX_CLONES - already
    print(W + f"  Installed : {CY+BR}{already}{RS+W}/{MAX_CLONES}")
    print(W + f"  Available : {G+BR}{can_add}{RS} slot(s)")
    print()
    if can_add <= 0: ok("All 10 slots full."); go(); return

    want_raw = input(Y + f"  How many to install? (1–{can_add}): " + W).strip()
    want     = min(int(want_raw) if want_raw.isdigit() else 1, can_add)
    needed_slots = list(range(already + 1, already + 1 + want))

    print(); info("Scanning Downloads for existing Noka APKs…")
    noka_map = scan_noka_apks()
    if noka_map:
        ok(f"Found {len(noka_map)} APK(s) already in Downloads:")
        for n, apk in sorted(noka_map.items()):
            print(W + f"    #{CY}{n}{W}  {DIM}{apk.name}{RS}")
    else:
        warn("No Noka APKs found in Downloads.")

    missing = [s for s in needed_slots if s not in noka_map]
    if missing:
        print(); warn(f"Still need: slot(s) {CY}{missing}")
        if input(Y + "  Open GoFile to download missing APKs? [Y/n]: " + W).strip().lower() != "n":
            sh("am start -a android.intent.action.VIEW -d '" + cfg["gofile_url"] + "'", silent=True)
            input(Y + "  Download(s) finished? Press Enter… " + RS)
            noka_map = scan_noka_apks()
        else:
            info("Skipping GoFile — installing whatever is available.")
    else:
        print(); ok("All needed APKs already in Downloads — skipping GoFile.")

    print()
    installed_any = False
    for idx, slot in enumerate(needed_slots):
        progress_bar(idx, len(needed_slots), label=f"slot {slot}")
        if slot not in noka_map: err(f"Noka #{slot} APK not found — skipping."); continue
        apk = noka_map[slot]
        info(f"Installing Noka #{CY+BR}{slot}{RS} › {DIM}{apk.name}")
        tmp = f"/data/local/tmp/{apk.name}"
        sh(f"cp '{apk}' '{tmp}'"); sh(f"chmod 644 '{tmp}'")
        res = sh(f"pm install -r '{tmp}'", capture=True, timeout=120)
        sh(f"rm -f '{tmp}'")
        if "Success" in res: ok(f"Noka #{slot} installed"); installed_any = True
        else: err(f"Noka #{slot} failed: {res[:120]}")
    progress_bar(len(needed_slots), len(needed_slots), label="done")
    print()
    if installed_any: detect_packages(force=True)
    go()

# ═══════════════════════════════════════════════════
#  WEBVIEW DB HELPERS
# ═══════════════════════════════════════════════════
def db_exists(path: str) -> bool:
    return sh(f"test -f '{path}' && echo YES || echo NO", capture=True) == "YES"

def _find_db_silent(pkg: str) -> str | None:
    for rel in WEBVIEW_DB_ORDERED:
        db = f"/data/data/{pkg}/{rel}"
        if db_exists(db): return db
    return None

# ═══════════════════════════════════════════════════
#  FAST WEBVIEW INIT
# ═══════════════════════════════════════════════════
def fast_init_webview(pkg: str, timeout: int = 30) -> str | None:
    sh("input keyevent KEYCODE_WAKEUP", silent=True)
    sh(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1", silent=True)
    time.sleep(1.5)
    sh(f"am start -a android.intent.action.VIEW -d 'roblox://' {pkg}", silent=True)
    time.sleep(1)

    result = [None]; stop = [False]

    def tapper():
        while not stop[0]:
            tap_element(KW_PERMISSION)
            time.sleep(0.5)

    def poller():
        deadline = time.time() + timeout
        while time.time() < deadline:
            if stop[0]: break
            db = _find_db_silent(pkg)
            if db: result[0] = db; stop[0] = True; return
            time.sleep(0.5)
        stop[0] = True

    t1 = threading.Thread(target=tapper, daemon=True)
    t2 = threading.Thread(target=poller, daemon=True)
    t1.start(); t2.start()
    t2.join(timeout + 3)
    stop[0] = True; t1.join(2)
    return result[0]

# ═══════════════════════════════════════════════════
#  SQLITE3 / COOKIE WRITE
# ═══════════════════════════════════════════════════
def _tmp_path(pkg: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]", "_", pkg)
    return f"/sdcard/Download/.vsphone_{safe}.db"

def _write_cookie(pkg: str, db: str, cookie: str) -> bool:
    tmp = _tmp_path(pkg)
    try:
        if os.path.exists(tmp): os.remove(tmp)
    except: pass

    sh(f"cp '{db}' '{tmp}'", capture=True)
    if not os.path.exists(tmp): return False
    try: os.chmod(tmp, 0o666)
    except: pass

    try:
        con = _sq3.connect(tmp)
        con.isolation_level = None
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
        if "cookies" not in tables:
            con.execute(COOKIES_TABLE_DDL)
        con.execute("DELETE FROM cookies WHERE name=? AND host_key LIKE '%roblox%';", (COOKIE_NAME,))
        con.execute(
            "INSERT OR REPLACE INTO cookies("
            "creation_utc,host_key,name,value,path,"
            "expires_utc,is_secure,is_httponly,last_access_utc,"
            "has_expires,is_persistent,priority,"
            "encrypted_value,samesite,source_scheme"
            ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);",
            (C_UTC, ROBLOX_DOMAIN, COOKIE_NAME, cookie, "/",
             E_UTC, 1, 1, C_UTC, 1, 1, 1, b"", -1, 2))
        count = con.execute("SELECT count(*) FROM cookies WHERE name=?;",
                            (COOKIE_NAME,)).fetchone()[0]
        try: con.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        except: pass
        con.close()
        if count == 1:
            sh(f"cp '{tmp}' '{db}'", capture=True)
            sh(f"chmod 660 '{db}'", capture=True)
            return True
        return False
    except Exception:
        return False
    finally:
        try:
            if os.path.exists(tmp): os.remove(tmp)
        except: pass

# ═══════════════════════════════════════════════════
#  COOKIE READ
# ═══════════════════════════════════════════════════
def read_cookies() -> list:
    path = cfg["cookies_path"]
    if not os.path.exists(path):
        warn("Cookie file not found.")
        path = input(Y + "  Enter full path to cookies.txt: " + W).strip()
        if os.path.exists(path): cfg["cookies_path"] = path; cfg.save()
    cookies = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line and line.startswith(COOKIE_PREFIX):
                    cookies.append(line)
    except Exception as e:
        err(f"Cannot read cookies: {e}")
    return cookies

# ═══════════════════════════════════════════════════
#  COOKIE LOGIN
# ═══════════════════════════════════════════════════
def cookie_login_all(pkgs: list, cookies: list):
    print()

    # Phase 1: DB check
    info("Checking existing WebView databases…")
    db_map: dict[str, str | None] = {}
    for pkg in pkgs:
        db_map[pkg] = _find_db_silent(pkg)

    has_db = [p for p in pkgs if db_map[p]]
    no_db  = [p for p in pkgs if not db_map[p]]

    for p in has_db:
        ok(f"{pkg_label(p, pkgs.index(p))} — DB ready")
    for p in no_db:
        warn(f"{pkg_label(p, pkgs.index(p))} — needs WebView init")

    # Phase 2: init missing (sequential, needs UI)
    for pkg in no_db:
        label = pkg_label(pkg, pkgs.index(pkg))
        print()
        info(f"Initialising {CY}{label}{RS}…")
        sh(f"am force-stop {pkg}", silent=True, timeout=5)
        time.sleep(0.5)
        db = fast_init_webview(pkg, timeout=30)
        sh(f"am force-stop {pkg}", silent=True, timeout=5)
        time.sleep(0.8)
        if db:
            db_map[pkg] = db
            ok(f"{label} — DB initialised")
        else:
            err(f"{label} — WebView never initialised (skipping)")

    # Phase 3: parallel writes
    print()
    info("Writing cookies in parallel…")
    results: dict[str, bool] = {}
    lock = threading.Lock()

    def do_inject(pkg, cookie):
        db = db_map.get(pkg)
        s  = _write_cookie(pkg, db, cookie) if db else False
        with lock: results[pkg] = s

    threads = []
    for i, pkg in enumerate(pkgs):
        if i >= len(cookies): break
        t = threading.Thread(target=do_inject, args=(pkg, cookies[i]), daemon=True)
        threads.append((pkg, i, t)); t.start()

    for pkg, i, t in threads:
        t.join(timeout=30)

    # Phase 4: results (sequential print — no interleaving)
    print()
    for i, pkg in enumerate(pkgs):
        label = pkg_label(pkg, i)
        if i >= len(cookies):
            warn(f"{label} — no cookie available")
            continue
        if results.get(pkg, False): ok(f"{label} — injected")
        else:                       err(f"{label} — failed")

    # Phase 5: close all
    print()
    info("Closing all Roblox tabs…")
    for pkg in pkgs:
        sh(f"am force-stop '{pkg}'", silent=True, timeout=5)
    print()
    ok("Done.")
    sys.stdout.flush()

# ═══════════════════════════════════════════════════
#  DELTA KEY — GRAB FROM CHROME CLIPBOARD
#
#  How it works:
#  1. Key dialog detected → tap "Receive Key"
#  2. Chrome opens a page that shows FREE_xxxxx
#  3. We find the text node via uiautomator, long-press
#     to select-all, then read clipboard via content
#  4. If clipboard has FREE_... → tap input, paste, Continue
# ═══════════════════════════════════════════════════

def _read_clipboard() -> str:
    """Read Android clipboard via content provider."""
    out = sh("content query --uri content://com.android.clipboard/clip", capture=True, timeout=5)
    # Typical line: Row: 0 label=NULL, text=FREE_abc123
    m = re.search(r"text=([^\s,]+)", out)
    if m: return m.group(1).strip()
    # Also try dumping primary clip via ClipboardManager dump
    out2 = sh("service call clipboard 2 i32 1", capture=True, timeout=5)
    return ""

def _find_key_in_xml() -> str:
    """Scan current UI for any text starting with FREE_"""
    xml = get_xml()
    m   = re.search(r"FREE_[A-Za-z0-9_\-]+", xml)
    return m.group(0) if m else ""

def _long_press_and_copy(x: int, y: int):
    """Long-press a coordinate to get Select All → Copy."""
    sh(f"input swipe {x} {y} {x} {y} 800", silent=True)   # long press
    time.sleep(0.8)
    tap_element(["Select all", "SELECT ALL", "select all"])
    time.sleep(0.4)
    tap_element(["Copy", "COPY"])
    time.sleep(0.4)

def grab_key_from_chrome() -> str:
    """
    Try to grab FREE_... key from the Chrome tab opened by Receive Key.
    Returns the key string or ''.
    """
    # Strategy 1: key text already visible in XML
    key = _find_key_in_xml()
    if key.startswith(KEY_PREFIX):
        info(f"Key found in UI: {CY}{key[:20]}…{RS}")
        # Long-press it to copy
        pos = find_element([key[:10]], clickable=False)
        if not pos:
            pos = find_element([KEY_PREFIX], clickable=False)
        if pos:
            _long_press_and_copy(pos[0], pos[1])
            time.sleep(0.5)
        return key

    # Strategy 2: read clipboard (user may have tapped copy themselves)
    clip = _read_clipboard()
    if clip.startswith(KEY_PREFIX):
        info(f"Key from clipboard: {CY}{clip[:20]}…{RS}")
        return clip

    return ""

def has_key_dialog() -> bool:
    xml = get_xml().lower()
    return any(k in xml for k in KW_KEY_DIALOG)

def handle_key_dialog() -> str:
    """
    Full key flow:
    1. If stored key in config → enter it directly.
    2. Else tap Receive Key → wait for Chrome → grab FREE_ key
       → store in config → enter it.
    Returns: 'entered' | 'waiting' | 'none'
    """
    if not has_key_dialog():
        return "none"

    stored = cfg.get("delta_key", "").strip()
    if stored and stored.startswith(KEY_PREFIX):
        return _enter_stored_key(stored)

    # No stored key — tap Receive Key to open Chrome
    info("Tapping Receive Key…")
    tapped = tap_element(KW_KEY_RECEIVE)
    if not tapped:
        tap_element(["receive", "getkey"])
    time.sleep(3)   # wait for Chrome to open and page to load

    # Try to grab key from Chrome for up to 15s
    deadline = time.time() + 15
    key = ""
    while time.time() < deadline:
        key = grab_key_from_chrome()
        if key.startswith(KEY_PREFIX): break
        time.sleep(2)

    if key.startswith(KEY_PREFIX):
        cfg["delta_key"] = key; cfg.save()
        ok(f"Key grabbed and saved: {key[:20]}…")
        # Go back to Roblox and enter key
        sh("input keyevent KEYCODE_BACK", silent=True)
        time.sleep(1.5)
        return _enter_stored_key(key)

    return "waiting"

def _enter_stored_key(key: str) -> str:
    """Type key into the Delta key input and hit Continue."""
    info(f"Entering key: {CY}{key[:20]}…{RS}")
    pos = find_element(KW_KEY_INPUT, clickable=True)
    if pos:
        sh(f"input tap {pos[0]} {pos[1]}", silent=True)
        time.sleep(0.5)
    # Clear field first
    sh("input keyevent KEYCODE_CTRL_A", silent=True)
    time.sleep(0.2)
    # Type via clipboard for safety
    safe = re.sub(r"(['\"])", r"\\\1", key)
    sh(f"am broadcast -a clipper.set -e text '{safe}' 2>/dev/null", silent=True)
    time.sleep(0.3)
    sh("input keyevent KEYCODE_PASTE", silent=True)
    time.sleep(0.5)
    # Fallback direct type
    sh(f"input text '{safe}'", silent=True)
    time.sleep(0.4)
    tap_element(KW_KEY_SUBMIT)
    time.sleep(1)
    return "entered"

# ═══════════════════════════════════════════════════
#  PROCESS / CAPTCHA
# ═══════════════════════════════════════════════════
def is_running(pkg: str) -> bool:
    out = sh(f"pidof '{pkg}' 2>/dev/null", capture=True, timeout=5)
    return bool(out.strip())

def has_captcha() -> bool:
    xml = get_xml().lower()
    return any(k in xml for k in ["captcha", "verify you are", "not a robot", "security check"])

# ═══════════════════════════════════════════════════
#  BEGIN AUTO RELAUNCH
#
#  Status machine per clone:
#    INIT → BOOTING (launch sent, 20s grace, no crash check)
#         → LIVE    (running normally, monitored)
#         → KEY     (key dialog visible)
#         → WAIT    (countdown before relaunch)
#         → BOOTING (after relaunch)
# ═══════════════════════════════════════════════════
def begin_auto_relaunch():
    banner(); hdr("Begin Auto Relaunch")
    pkgs    = cfg["packages"]
    game_id = cfg["game_id"]
    if not pkgs: err("No packages detected."); go(); return

    state: dict[str, dict] = {}
    for i, pkg in enumerate(pkgs):
        state[pkg] = {
            "label":   pkg_label(pkg, i),
            "status":  "INIT",
            "crashes": 0,
            "since":   None,    # boot timestamp
            "until":   None,    # WAIT countdown end
            "key_try": 0,
        }

    def launch(pkg):
        deeplink = f"roblox://experiences/start?placeId={game_id}"
        sh(f"am start -a android.intent.action.VIEW -d '{deeplink}' {pkg}", silent=True)
        # BOOTING: grace period before crash detection starts
        state[pkg].update({"since": time.time(), "status": "BOOTING", "until": None})

    def kill(pkg):
        sh(f"am force-stop '{pkg}'", silent=True, timeout=5)

    def draw():
        clr()
        now = time.time()
        W2  = 52
        print()
        print(CY + f"  ╔{'═'*W2}╗")
        title = f"  AUTO RELAUNCH  ·  {len(pkgs)} clone(s)  ·  Ctrl+C to stop"
        print(CY + "  ║" + Y + BR + title.ljust(W2) + RS + CY + "║")
        print(CY + f"  ╠{'═'*W2}╣")
        print(CY + "  ║" + DIM + W + f"  {'Clone':<12}{'Status':<12}{'Crashes':<10}{'Uptime':<16}" + RS + CY + "║")
        print(CY + f"  ╠{'═'*W2}╣")

        for pkg, s in state.items():
            st  = s["status"]; cr = s["crashes"]; lab = s["label"]

            if st == "BOOTING":
                elapsed = int(now - s["since"]) if s["since"] else 0
                upt     = f"boot {elapsed}s/{BOOT_GRACE}s"
                sc = CY; icon = "○"
            elif st == "LIVE" and s["since"]:
                e   = int(now - s["since"])
                upt = f"{e//3600:02d}:{(e%3600)//60:02d}:{e%60:02d}"
                sc  = G + BR; icon = "●"
            elif st == "WAIT":
                rem = max(0, int(s["until"] - now)) if s["until"] else 0
                upt = f"relaunch {rem}s"
                sc  = Y; icon = "⟳"
            elif st == "KEY":
                upt = "key dialog"; sc = M + BR; icon = "🔑"
            elif st == "CAPTCHA":
                upt = "captcha!"; sc = R + BR; icon = "⚠"
            else:
                upt = "starting…"; sc = DIM; icon = "○"

            row = f"  {lab:<12}{icon} {st:<10}{cr:<10}{upt:<16}"
            print(CY + "  ║" + W + "  " + sc + f"{lab:<12}" + RS + W +
                  f"{icon} " + sc + f"{st:<10}" + RS + W +
                  f"{cr:<10}" + DIM + f"{upt:<16}" + RS + CY + "║")

        print(CY + f"  ╚{'═'*W2}╝")
        print(DIM + f"\n  last check: {time.strftime('%H:%M:%S')}" + RS)

    # Kill all first
    info("Killing all clones…")
    for pkg in pkgs: kill(pkg)
    time.sleep(1)

    # Launch with 1s gap
    info("Launching all clones…")
    for pkg in pkgs:
        info(f"  {state[pkg]['label']}…")
        launch(pkg)
        time.sleep(1)

    captcha_at = 0.0
    key_at     = 0.0

    try:
        while True:
            now = time.time()

            captcha_found = False
            if now - captcha_at > 8:
                captcha_found = has_captcha(); captcha_at = now

            key_found = False
            if now - key_at > 5:
                key_found = has_key_dialog(); key_at = now

            for pkg, s in state.items():
                st = s["status"]

                # ── WAIT: countdown to relaunch ─────────
                if st == "WAIT":
                    if s["until"] and now >= s["until"]:
                        launch(pkg)
                    continue

                # ── BOOTING: grace period ────────────────
                if st == "BOOTING":
                    elapsed = now - (s["since"] or now)
                    if elapsed >= BOOT_GRACE:
                        # Grace done — check if actually alive
                        if is_running(pkg):
                            s["status"] = "LIVE"
                        else:
                            # Crashed before grace ended
                            s["crashes"] += 1
                            s["status"]   = "WAIT"
                            s["until"]    = now + 10
                    continue

                # ── LIVE: normal monitoring ──────────────
                if st == "LIVE":
                    if not is_running(pkg):
                        s["crashes"] += 1; s["status"] = "WAIT"; s["until"] = now + 10
                        continue
                    if key_found:
                        s["status"] = "KEY"; s["key_try"] = 0; continue
                    if captcha_found:
                        s["crashes"] += 1; s["status"] = "WAIT"; s["until"] = now + 10
                        kill(pkg); continue

                # ── KEY: handle key dialog ───────────────
                if st == "KEY":
                    result = handle_key_dialog()
                    if result == "entered":
                        s["status"] = "LIVE"
                    elif result == "none":
                        s["status"] = "LIVE"   # dialog gone
                    else:
                        s["key_try"] += 1
                        if s["key_try"] > 4:
                            warn(f"{s['label']} key failed — restarting")
                            s["crashes"] += 1; s["status"] = "WAIT"
                            s["until"] = now + 15; kill(pkg)
                    continue

            draw()
            time.sleep(3)

    except KeyboardInterrupt:
        print()
        info("Stopping — killing all clones…")
        for pkg in pkgs: kill(pkg)
        ok("All stopped.")
        go()

# ═══════════════════════════════════════════════════
#  MAIN MENU
# ═══════════════════════════════════════════════════
def main():
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    detect_packages()
    while True:
        banner(); noka = count_noka_installed()
        print(CY + "  ┌─────────────────────────────────────────────┐")
        print(CY + "  │  " + Y + BR + "  MAIN MENU" + " " * 35 + RS + CY + "│")
        print(CY + "  ├─────────────────────────────────────────────┤")
        menu_item("1", "Install APKs",         f"slots used: {noka}/{MAX_CLONES}")
        menu_item("2", "Cookie Login",          f"{len(cfg['packages'])} package(s) ready")
        menu_item("3", "Launch All into Game",  f"game {cfg['game_id']}")
        menu_item("4", "Begin Auto Relaunch",   "monitor + crash + key recovery")
        menu_item("5", "Settings",              "configure paths & delays")
        menu_item("0", "Exit",                  "")
        print(CY + "  └─────────────────────────────────────────────┘")
        print()
        c = input(CY + "  › " + W + "Choice: " + RS).strip()

        if c == "1":
            install_apks()

        elif c == "2":
            banner(); hdr("Cookie Login")
            cookies = read_cookies()
            if not cookies: err("No valid cookies found."); go(); continue
            pkgs = cfg["packages"]
            if not pkgs: err("No packages — install APKs first."); go(); continue
            info(f"Found {G+BR}{len(cookies)}{RS} cookie(s)  •  {CY}{len(pkgs)}{RS} package(s)")
            cookie_login_all(pkgs, cookies)
            go()

        elif c == "3":
            banner(); hdr("Launch All into Game")
            for i, pkg in enumerate(cfg["packages"]):
                label = pkg_label(pkg, i)
                info(f"Launching {CY}{label}{RS}…")
                deeplink = f"roblox://experiences/start?placeId={cfg['game_id']}"
                sh(f"am start -a android.intent.action.VIEW -d '{deeplink}' {pkg}", silent=True)
                time.sleep(1)
            ok("All clones launched.")
            go()

        elif c == "4":
            begin_auto_relaunch()

        elif c == "5":
            settings_menu()

        elif c == "0":
            print(); print(M + BR + "  Goodbye! — " + CREATOR + RS); print(); break

# ═══════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════
def settings_menu():
    while True:
        banner(); hdr("Settings"); print()
        ak  = G + BR + "ON"  if cfg.get("auto_key", True)      else R + BR + "OFF"
        ast = G + BR + "ON"  if cfg.get("auto_sort_tabs", True) else R + BR + "OFF"
        dk  = DIM + cfg.get("delta_key", "")[:24] + "…" + RS if cfg.get("delta_key") else R + "(none)"
        print(W + f"  {CY}[1]{W} First Launch Delay  {DIM}→ {BR+Y}{cfg['first_launch_delay']}s")
        print(W + f"  {CY}[2]{W} Relaunch Threshold  {DIM}→ {BR+Y}{cfg['relaunch_threshold']}s")
        print(W + f"  {CY}[3]{W} Auto Key            {DIM}→ {ak}{RS}")
        print(W + f"  {CY}[4]{W} Auto Sort Tabs      {DIM}→ {ast}{RS}")
        print(W + f"  {CY}[5]{W} Cookie File         {DIM}→ {Y}{cfg['cookies_path']}")
        print(W + f"  {CY}[6]{W} GoFile URL          {DIM}→ {Y}{cfg['gofile_url'][:45]}")
        print(W + f"  {CY}[7]{W} Game ID             {DIM}→ {Y}{cfg['game_id']}")
        print(W + f"  {CY}[8]{W} Delta Key           {DIM}→ {dk}{RS}")
        print(W + f"  {CY}[0]{W} Back"); print()
        c = input(CY + "  › " + W + "Choice: " + RS).strip()
        if   c == "1":
            v = input(Y + "  Delay (s): " + W).strip()
            if v.isdigit(): cfg["first_launch_delay"] = int(v); ok("Saved.")
        elif c == "2":
            v = input(Y + "  Threshold (s): " + W).strip()
            if v.isdigit(): cfg["relaunch_threshold"] = int(v); ok("Saved.")
        elif c == "3": cfg["auto_key"] = not cfg.get("auto_key", True); ok("Toggled.")
        elif c == "4": cfg["auto_sort_tabs"] = not cfg.get("auto_sort_tabs", True); ok("Toggled.")
        elif c == "5":
            p = input(Y + "  Path to cookies.txt: " + W).strip()
            if os.path.exists(p): cfg["cookies_path"] = p; ok("Saved.")
            else: err("Not found.")
        elif c == "6": cfg["gofile_url"] = input(Y + "  New URL: " + W).strip(); ok("Saved.")
        elif c == "7": cfg["game_id"] = input(Y + "  New Game ID: " + W).strip(); ok("Saved.")
        elif c == "8":
            print(); info("Paste your FREE_ key below (or leave blank to clear):")
            k = input(Y + "  Delta Key: " + W).strip()
            if k and k.startswith(KEY_PREFIX): cfg["delta_key"] = k; ok("Saved.")
            elif k == "": cfg["delta_key"] = ""; ok("Cleared.")
            else: err(f"Key must start with {KEY_PREFIX}")
        elif c == "0": break

if __name__ == "__main__":
    main()
