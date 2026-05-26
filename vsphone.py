cat > /mnt/user-data/outputs/vsphone.py << 'ENDOFSCRIPT'
#!/usr/bin/env python3
"""
VSPhone Roblox Auto Relauncher v7.5
Fixes: CPU stats, Delta key (Receive Key tap + Chrome grab), white screen on am start
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
    print("Missing packages. Run: pip install colorama pyyaml")
    sys.exit(1)

R = Fore.RED; G = Fore.GREEN; Y = Fore.YELLOW
M = Fore.MAGENTA; CY = Fore.CYAN; W = Fore.WHITE
DIM = Style.DIM; BR = Style.BRIGHT; RS = Style.RESET_ALL

VERSION = "7.5"
CREATOR = "IWZVC"
CFG_FILE = os.path.expanduser("~/.vsphone.yaml")
AOTR_GAME_ID = "13379208636"
MAX_CLONES = 10
COOKIE_NAME = ".ROBLOSECURITY"
ROBLOX_DOMAIN = ".roblox.com"
COOKIE_PREFIX = "_|WARNING:-DO-NOT-SHARE-THIS"
C_UTC = 13300000000000000
E_UTC = 13580000000000000
BOOT_GRACE = 25
KEY_PREFIX = "FREE_"
KEY_TTL = 86400
MAX_KEY_FAIL = 3
DELTA_AUTOEXEC_PATH = "/storage/emulated/0/delta/autoexec"

# FLAG_ACTIVITY_REORDER_TO_FRONT — brings existing activity to front WITHOUT relaunching
# This is the fix for the white Roblox loading screen caused by am start recreating the activity
AM_FRONT_FLAG = "0x20000000"

CHROME_PKGS = [
    "com.android.chrome",
    "com.brave.browser",
    "com.microsoft.emmx",
    "org.mozilla.firefox",
]

# Chrome URL bar resource IDs across versions/forks
CHROME_URL_BAR_IDS = [
    "com.android.chrome:id/url_bar",
    "com.android.chrome:id/location_bar_edit_text",
    "com.brave.browser:id/url_bar",
    "com.microsoft.emmx:id/url_bar",
    "org.mozilla.firefox:id/url_bar_title",
    "org.mozilla.firefox:id/mozac_browser_toolbar_url_view",
]

KEY_PATTERN = re.compile(r"FREE_[A-Za-z0-9_\-]{10,}")

KW_PERMISSION = ["Continue", "CONTINUE", "Allow", "ALLOW", "Next", "OK", "Ok",
                 "Accept", "Grant", "GOT IT", "Got it", "DONE", "Done",
                 "CLOSE", "Close", "Dismiss", "DISMISS", "Accept & continue",
                 "No thanks", "NO THANKS", "No Thanks"]
# NOTE: "receive key" removed from permission list — it's handled exclusively
# by the key handler. Having it in the background tapper caused it to fire at
# wrong times and open Chrome before the handler was ready.
KW_KEY_RECEIVE  = ["receive key", "getkey", "get key", "receivekey"]
KW_KEY_INPUT    = ["key_example", "enter key", "key example", "paste key"]
KW_KEY_SUBMIT   = ["continue", "submit", "confirm"]

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

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
class Config:
    _defaults = {
        "packages": [],
        "game_id": AOTR_GAME_ID,
        "gofile_url": "https://gofile.io/d/9ucwee",
        "cookies_path": "/storage/emulated/0/Download/cookies.txt",
        "first_launch_delay": 12,
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

# ─────────────────────────────────────────────────────────────────────────────
# System stats  (FIX: read /proc/stat directly — Android top is unreliable)
# ─────────────────────────────────────────────────────────────────────────────
_cpu_prev = None

def get_system_stats() -> str:
    global _cpu_prev
    try:
        # RAM via /proc/meminfo
        mem = sh("cat /proc/meminfo 2>/dev/null | head -5", capture=True, timeout=3)
        total_m = re.search(r'MemTotal:\s+(\d+)', mem)
        avail_m = re.search(r'MemAvailable:\s+(\d+)', mem)
        if total_m and avail_m:
            total = int(total_m.group(1)) // 1024
            free  = int(avail_m.group(1)) // 1024
            used  = total - free
            ram   = f"{used}MB/{total}MB ({int(used/total*100)}%)"
        else:
            ram = "N/A"

        # CPU via /proc/stat delta (works on all Android versions)
        stat = sh("cat /proc/stat 2>/dev/null | head -1", capture=True, timeout=3)
        nums = list(map(int, stat.split()[1:]))
        idle_now  = nums[3]
        total_now = sum(nums)
        if _cpu_prev:
            idle_prev, total_prev = _cpu_prev
            diff_total = total_now - total_prev
            diff_idle  = idle_now  - idle_prev
            if diff_total > 0:
                cpu_pct = int(100 * (diff_total - diff_idle) / diff_total)
            else:
                cpu_pct = 0
            cpu_str = f"{min(cpu_pct, 100)}%"
        else:
            cpu_str = "…"
        _cpu_prev = (idle_now, total_now)
        return f"CPU: {cpu_str}  RAM: {ram}"
    except:
        return "CPU/RAM: N/A"

# ─────────────────────────────────────────────────────────────────────────────
# Key helpers
# ─────────────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
# UI / display helpers
# ─────────────────────────────────────────────────────────────────────────────
W_ = 54
def clr(): os.system("clear")

def banner():
    clr()
    noka  = count_noka_installed()
    bar_n = int((noka / MAX_CLONES) * 20)
    bar   = G + chr(9608)*bar_n + DIM + chr(9617)*(20-bar_n) + RS
    pct   = int(noka / MAX_CLONES * 100)
    if _key_is_valid():
        key_status = G + BR + "OK (" + _key_remaining_str() + " left)" + RS
    elif cfg.get("delta_key", ""):
        key_status = R + BR + "EXPIRED" + RS
    else:
        key_status = DIM + "none — will grab from Chrome" + RS
    print()
    print(CY + "╔" + "═"*W_ + "╗")
    print(CY + "║" + M + BR + f"{' VSPhone':^{W_}}" + RS + CY + "║")
    print(CY + "║" + Y + BR + f"{' Roblox Auto Relauncher v' + VERSION:^{W_}}" + RS + CY + "║")
    print(CY + "║" + DIM + W + f"{' Termux · Rooted · by ' + CREATOR:^{W_}}" + RS + CY + "║")
    print(CY + "╠" + "═"*W_ + "╣")
    print(CY + "║" + f" Clones [{bar}{W}] {CY}{BR}{noka}{W}/{MAX_CLONES}{DIM} ({pct}%)".ljust(W_+30) + CY + "║")
    print(CY + "║" + f" Packages: {BR+CY}{len(cfg['packages'])}{RS+DIM+W} | Slots free: {BR+G}{MAX_CLONES-noka}".ljust(W_+20) + RS + CY + "║")
    print(CY + "║" + f" Delta Key: {key_status}".ljust(W_+20) + CY + "║")
    print(CY + "╚" + "═"*W_ + "╝")
    print()

def section(t):
    print()
    print(CY + "┌" + "─"*W_ + "┐")
    print(CY + "│" + Y + BR + f" ◈ {t}".ljust(W_) + RS + CY + "│")
    print(CY + "└" + "─"*W_ + "┘")

def ok(m):   print(G  + BR + f" ✔ {m}" + RS); sys.stdout.flush()
def err(m):  print(R  + BR + f" ✘ {m}" + RS); sys.stdout.flush()
def info(m): print(CY + f" › {m}" + RS);       sys.stdout.flush()
def warn(m): print(Y  + f" ⚠ {m}" + RS);       sys.stdout.flush()
def hdr(m):  section(m)

def go(p=" Press Enter to continue…"):
    print(); sys.stdout.flush()
    try:
        import termios
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except: pass
    input(DIM + W + p + RS)

def menu_item(key, label, note=""):
    print(CY + BR + f" [{key}]" + RS + W + f" {label}" + DIM + (f"  {note}" if note else "") + RS)

def progress_bar(cur, total, w=30, label=""):
    f   = int(w * cur / max(total, 1))
    bar = G + chr(9608)*f + DIM + chr(9617)*(w-f) + RS
    print(f" [{bar}] {CY}{int(cur/max(total,1)*100)}%{RS} {label}")

# ─────────────────────────────────────────────────────────────────────────────
# Shell
# ─────────────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
# UI Automator helpers
# ─────────────────────────────────────────────────────────────────────────────
def get_xml() -> str:
    sh("uiautomator dump /sdcard/_vsphone_ui.xml 2>/dev/null", silent=True, timeout=8)
    return sh("cat /sdcard/_vsphone_ui.xml 2>/dev/null", capture=True, timeout=5)

def _parse_bounds(node) -> tuple:
    """Return (cx, cy) centre of a node's bounds, or None."""
    nums = re.findall(r"\d+", node.get("bounds", ""))
    if len(nums) == 4:
        return (int(nums[0]) + int(nums[2])) // 2, (int(nums[1]) + int(nums[3])) // 2
    return None

def find_element(terms, clickable=False, xml=None):
    if xml is None:
        xml = get_xml()
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

def find_node_by_resource_id(resource_id: str, xml=None):
    """Return the text of a node matched by resource-id, or ''."""
    if xml is None:
        xml = get_xml()
    try:
        root = ET.fromstring(xml)
        for node in root.iter("node"):
            if node.get("resource-id","") == resource_id:
                return node.get("text","").strip()
    except: pass
    return ""

def tap_element(terms, xml=None) -> bool:
    pos = find_element(terms, clickable=True, xml=xml)
    if pos:
        sh(f"input tap {pos[0]} {pos[1]}", silent=True)
        time.sleep(0.6)
        return True
    return False

def read_all_ui_text(xml=None) -> str:
    """Concatenate every text/content-desc from the current UI dump."""
    if xml is None:
        xml = get_xml()
    parts = []
    try:
        root = ET.fromstring(xml)
        for node in root.iter("node"):
            for attr in ("text", "content-desc"):
                v = node.get(attr, "").strip()
                if v: parts.append(v)
    except: pass
    return " ".join(parts)

# ─────────────────────────────────────────────────────────────────────────────
# App-switching helpers
# ─────────────────────────────────────────────────────────────────────────────
def get_foreground_pkg() -> str:
    try:
        out = sh(
            "dumpsys activity activities 2>/dev/null "
            "| grep -E 'mResumedActivity|mFocusedActivity' | head -1",
            capture=True, timeout=4
        )
        m = re.search(r'([a-zA-Z0-9_.]+)/[a-zA-Z0-9_.]+', out)
        return m.group(1) if m else ""
    except:
        return ""

def wait_for_foreground(pkg_fragment: str, timeout: int = 15) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pkg_fragment.lower() in get_foreground_pkg().lower():
            return True
        time.sleep(0.5)
    return False

def bring_to_front(pkg: str):
    """
    Bring an already-running app to the foreground WITHOUT relaunching it.
    FLAG_ACTIVITY_REORDER_TO_FRONT (0x20000000) is the key — it does NOT
    create a new instance or trigger the white Roblox loading screen.
    """
    sh(f"am start -f {AM_FRONT_FLAG} {pkg}", silent=True)
    time.sleep(1.2)

def bring_termux_foreground():
    for cmd in [
        "am start -n com.termux/.HomeActivity",
        "am start -n com.termux/.app.TermuxActivity",
    ]:
        sh(cmd, silent=True)
        time.sleep(0.3)

def get_chrome_pkg() -> str:
    raw = sh("pm list packages 2>/dev/null", capture=True, timeout=10)
    for pkg in CHROME_PKGS:
        if pkg in raw:
            return pkg
    return "com.android.chrome"

# ─────────────────────────────────────────────────────────────────────────────
# Clipboard
# ─────────────────────────────────────────────────────────────────────────────
def _read_clipboard() -> str:
    # Method 1 — content provider
    out = sh("content query --uri content://com.android.clipboard/clip", capture=True, timeout=5)
    m = KEY_PATTERN.search(out)
    if m: return m.group(0)
    m = re.search(r"text=([^\s,\)]+)", out)
    if m and m.group(1).strip(): return m.group(1).strip()
    # Method 2 — termux clipboard
    out = sh("termux-clipboard-get 2>/dev/null", capture=True, timeout=4)
    if out:
        m = KEY_PATTERN.search(out)
        if m: return m.group(0)
        return out.strip()
    return ""

def _set_clipboard(text: str):
    safe = text.replace("'", "\\'")
    sh(f"termux-clipboard-set '{safe}' 2>/dev/null", silent=True, timeout=4)
    sh(f"am broadcast -a clipper.set -e text '{safe}' 2>/dev/null", silent=True, timeout=4)

# ─────────────────────────────────────────────────────────────────────────────
# Background helpers
# ─────────────────────────────────────────────────────────────────────────────
def aggressive_dialog_tapper():
    """
    Tap generic permission / dismiss dialogs.
    Does NOT include 'receive key' — that is handled only by the key handler
    so it doesn't fire Chrome at the wrong time.
    """
    while True:
        try:
            tap_element(KW_PERMISSION + ["OK", "Ok", "GOT IT", "Got it", "CLOSE", "Dismiss", "No thanks"])
            time.sleep(0.35)
        except:
            time.sleep(1)

def has_captcha() -> bool:
    return any(k in get_xml().lower() for k in ["captcha","verify you are","not a robot","security check"])

# ─────────────────────────────────────────────────────────────────────────────
# Package detection
# ─────────────────────────────────────────────────────────────────────────────
_pkg_lock = threading.Lock()

def detect_packages(force=False):
    raw = sh("pm list packages 2>/dev/null | grep -iE 'roblox|delta'", capture=True, timeout=20)
    candidates = [l.replace("package:","").strip() for l in raw.splitlines() if l.strip()]
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
    return f"Noka {idx+1}"

def get_installed_noka_numbers():
    raw = sh("pm list packages 2>/dev/null | grep -iE 'roblox|delta'", capture=True, timeout=15)
    pkgs = [l.replace("package:","").strip() for l in raw.splitlines() if l.strip()]
    numbers = []
    for pkg in pkgs:
        m = re.search(r'(\d+)', pkg)
        if m: numbers.append(int(m.group(1)))
    return sorted(set(numbers))

def get_next_available_slots(want):
    installed = get_installed_noka_numbers()
    print(f"[DEBUG] Installed Noka numbers: {installed}")
    missing, i = [], 1
    while len(missing) < want:
        if i not in installed: missing.append(i)
        i += 1
    print(f"[DEBUG] Installing into slots: {missing}")
    return missing

# ─────────────────────────────────────────────────────────────────────────────
# AOTR TrackStat
# ─────────────────────────────────────────────────────────────────────────────
def install_aotr_trackstat():
    folder = Path(DELTA_AUTOEXEC_PATH)
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        err(f"Cannot create autoexec folder: {e}"); return False
    lua_code = '''-- AOTR TrackStat v1.1 auto-installed by VSPhone
local webhook = "https://discord.com/api/webhooks/1505645833075298345/xezkV4n0logucMqxqI0BlW5Inqx0x-sBHOMuYhsG8G-6l8-bYQZSSa03eZy1utL9d9nc"
local function getStats()
    local plr = game.Players.LocalPlayer
    local gold    = (plr:FindFirstChild("leaderstats") and plr.leaderstats:FindFirstChild("Gold")    and plr.leaderstats.Gold.Value)    or 0
    local gems    = (plr:FindFirstChild("leaderstats") and plr.leaderstats:FindFirstChild("Gems")    and plr.leaderstats.Gems.Value)    or 0
    local scrolls = (plr:FindFirstChild("leaderstats") and plr.leaderstats:FindFirstChild("Scrolls") and plr.leaderstats.Scrolls.Value) or 0
    return gold, gems, scrolls, plr.Name
end
local lastGold, lastGems, lastTime = 0, 0, tick()
while true do
    local gold, gems, scrolls, username = getStats()
    local now      = tick()
    local dtHours  = math.max((now - lastTime) / 3600, 0.01)
    local goldPerHour  = (gold - lastGold) / dtHours
    local gemsPerHour  = (gems - lastGems) / dtHours
    local spinsPerHour = (gemsPerHour * 0.01) + ((goldPerHour / 1000000) * 1000 * 0.01)
    local embed = {
        title  = "AOTR Stats — " .. username,
        color  = 0x00FFAA,
        fields = {
            {name="Gold",       value=tostring(gold),                        inline=true},
            {name="Gems",       value=tostring(gems),                        inline=true},
            {name="Scrolls",    value=tostring(scrolls),                     inline=true},
            {name="Gold/hr",    value=string.format("%.0f", goldPerHour),   inline=true},
            {name="Gems/hr",    value=string.format("%.0f", gemsPerHour),   inline=true},
            {name="Spins/hr",   value=string.format("%.1f", spinsPerHour),  inline=true},
        },
        footer    = {text = "VSPhone v7.5 • " .. os.date("%H:%M")},
        timestamp = os.date("!%Y-%m-%dT%H:%M:%SZ"),
    }
    pcall(function()
        (syn and syn.request or http_request or request)({
            Url     = webhook,
            Method  = "POST",
            Headers = {["Content-Type"]="application/json"},
            Body    = game:GetService("HttpService"):JSONEncode({embeds={embed}}),
        })
    end)
    lastGold, lastGems, lastTime = gold, gems, now
    wait(300)
end
'''
    target = folder / "aotr_trackstat.lua"
    try:
        with open(target, "w", encoding="utf-8") as f: f.write(lua_code)
        ok(f"AOTR TrackStat installed → {target}"); return True
    except Exception as e:
        err(f"Failed to write TrackStat: {e}"); return False

# ─────────────────────────────────────────────────────────────────────────────
# APK management
# ─────────────────────────────────────────────────────────────────────────────
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

def delete_downloaded_apks():
    banner(); hdr("Delete Downloaded Noka APKs")
    apks = list(Path("/storage/emulated/0/Download").glob("*.apk"))
    if not apks: err("No APK files found."); go(); return
    for i, apk in enumerate(apks, 1):
        print(f" {CY}[{i}]{W} {apk.name} ({apk.stat().st_size//1024} KB)")
    print()
    print(Y + " [a] Delete ALL  [s] Select  [n] Cancel"); print()
    choice = input(Y + "Choice: " + W).strip().lower()
    to_delete = []
    if   choice == "a": to_delete = apks
    elif choice == "n": info("Cancelled."); go(); return
    elif choice == "s":
        try:
            nums = [int(x) for x in input(Y+"Numbers: "+W).strip().split()]
            to_delete = [apks[n-1] for n in nums if 1 <= n <= len(apks)]
        except: err("Invalid."); go(); return
    else: err("Invalid."); go(); return
    if not to_delete: info("Nothing to delete."); go(); return
    for apk in to_delete:
        try: apk.unlink(); ok(f"Deleted: {apk.name}")
        except Exception as e: err(f"Failed: {apk.name}: {e}")
    ok(f"Deleted {len(to_delete)} file(s)."); go()

def install_apks(pause=True):
    banner(); hdr("Install Noka Delta Lite APKs")
    detect_packages()
    already = count_noka_installed(); can_add = MAX_CLONES - already
    print(W + f" Installed : {CY+BR}{already}{RS+W}/{MAX_CLONES}")
    print(W + f" Available : {G+BR}{can_add}{RS} slot(s)"); print()
    if can_add <= 0: ok("All 10 slots full."); go() if pause else None; return False
    want_raw = input(Y + f" How many to install? (1-{can_add}): " + W).strip()
    want = min(int(want_raw) if want_raw.isdigit() else 1, can_add)
    needed_slots = get_next_available_slots(want)
    print(); info("Scanning Downloads…")
    noka_map = scan_noka_apks()
    if noka_map:
        ok(f"Found {len(noka_map)} APK(s):")
        for n, apk in sorted(noka_map.items()): print(W + f" #{CY}{n}{W} {DIM}{apk.name}{RS}")
    else: warn("No Noka APKs found in Downloads.")
    missing = [s for s in needed_slots if s not in noka_map]
    if missing:
        print(); warn(f"Need slot(s): {CY}{missing}")
        c = input(Y + " Open GoFile? [Y/n]: " + W).strip().lower()
        if c == "y":
            sh("termux-open-url 'https://gofile.io/d/9ucwee'", silent=True); time.sleep(4)
            input(Y + "\nDownload done? Press Enter… "); bring_termux_foreground()
        elif c == "n": info("Skipping GoFile.")
        else: info("Invalid. Returning."); return False
    else: print(); ok("All APKs already in Downloads.")
    print(); installed_any = False
    for idx, slot in enumerate(needed_slots):
        progress_bar(idx, len(needed_slots), label=f"slot {slot}")
        if slot not in noka_map: err(f"Noka #{slot} not found — skipping."); continue
        apk = noka_map[slot]
        info(f"Installing Noka #{CY+BR}{slot}{RS} › {DIM}{apk.name}")
        tmp = f"/data/local/tmp/{apk.name}"
        sh(f"cp '{apk}' '{tmp}'"); sh(f"chmod 644 '{tmp}'")
        res = sh(f"pm install -r '{tmp}'", capture=True, timeout=120)
        sh(f"rm -f '{tmp}'")
        if "Success" in res: ok(f"Noka #{slot} installed"); installed_any = True
        else: err(f"Noka #{slot} failed: {res[:120]}")
    progress_bar(len(needed_slots), len(needed_slots), label="done"); print()
    if installed_any: detect_packages(force=True)
    if pause: go()
    return True

def uninstall_apks():
    banner(); hdr("Uninstall Noka Delta Lite APKs")
    detect_packages(); pkgs = cfg["packages"]
    if not pkgs: err("No packages to uninstall."); go(); return
    for i, pkg in enumerate(pkgs): print(f" {CY}[{i+1}]{W} {pkg_label(pkg,i)} — {DIM}{pkg}{RS}")
    print()
    sel = input(Y + "Numbers or 'all': " + W).strip().lower()
    to_uninstall = pkgs[:] if sel=="all" else [pkgs[n-1] for n in [int(x) for x in sel.split() if x.isdigit()] if 1<=n<=len(pkgs)]
    if not to_uninstall: info("Nothing selected."); go(); return
    for pkg in to_uninstall:
        info(f"Uninstalling {CY}{pkg_label(pkg, pkgs.index(pkg))}{RS}…")
        sh(f"pm uninstall '{pkg}'", silent=True, timeout=30)
    detect_packages(force=True); ok(f"Uninstalled {len(to_uninstall)}."); go()

def apk_menu():
    while True:
        banner(); hdr("APK Management"); noka = count_noka_installed()
        menu_item("1","Install APKs",f"slots: {noka}/{MAX_CLONES}")
        menu_item("2","Uninstall APKs",f"{noka} installed")
        menu_item("3","Delete Downloaded APKs","")
        menu_item("0","Back")
        print(); c = input(CY+" › "+W+"Choice: "+RS).strip()
        if   c=="1": install_apks()
        elif c=="2": uninstall_apks()
        elif c=="3": delete_downloaded_apks()
        elif c=="0": break

# ─────────────────────────────────────────────────────────────────────────────
# WebView / Cookie
# ─────────────────────────────────────────────────────────────────────────────
def db_exists(path: str) -> bool:
    return sh(f"test -f '{path}' && echo YES || echo NO", capture=True) == "YES"

def _find_db_silent(pkg: str):
    for rel in WEBVIEW_DB_ORDERED:
        db = f"/data/data/{pkg}/{rel}"
        if db_exists(db): return db
    return None

def fast_init_webview(pkg: str, timeout: int = 30):
    sh("input keyevent KEYCODE_WAKEUP", silent=True)
    sh(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1", silent=True)
    time.sleep(1.5)
    sh(f"am start -a android.intent.action.VIEW -d 'roblox://' {pkg}", silent=True)
    time.sleep(1)
    result=[None]; stop=[False]
    def tapper():
        while not stop[0]: tap_element(KW_PERMISSION); time.sleep(0.5)
    def poller():
        deadline = time.time()+timeout
        while time.time()<deadline:
            if stop[0]: break
            db = _find_db_silent(pkg)
            if db: result[0]=db; stop[0]=True; return
            time.sleep(0.5)
        stop[0]=True
    t1=threading.Thread(target=tapper,daemon=True)
    t2=threading.Thread(target=poller,daemon=True)
    t1.start(); t2.start(); t2.join(timeout+3); stop[0]=True; t1.join(2)
    return result[0]

def _tmp_path(pkg: str) -> str:
    return f"/sdcard/Download/.vsphone_{re.sub(r'[^a-zA-Z0-9]','_',pkg)}.db"

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
        con = _sq3.connect(tmp); con.isolation_level=None
        tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
        if "cookies" not in tables: con.execute(COOKIES_TABLE_DDL)
        con.execute("DELETE FROM cookies WHERE name=? AND host_key LIKE '%roblox%';",(COOKIE_NAME,))
        con.execute(
            "INSERT OR REPLACE INTO cookies("
            "creation_utc,host_key,name,value,path,expires_utc,is_secure,is_httponly,"
            "last_access_utc,has_expires,is_persistent,priority,encrypted_value,samesite,source_scheme"
            ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);",
            (C_UTC,ROBLOX_DOMAIN,COOKIE_NAME,cookie,"/",E_UTC,1,1,C_UTC,1,1,1,b"",-1,2))
        count=con.execute("SELECT count(*) FROM cookies WHERE name=?;",(COOKIE_NAME,)).fetchone()[0]
        try: con.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        except: pass
        con.close()
        if count==1:
            sh(f"cp '{tmp}' '{db}'",capture=True); sh(f"chmod 660 '{db}'",capture=True); return True
        return False
    except: return False
    finally:
        try:
            if os.path.exists(tmp): os.remove(tmp)
        except: pass

def read_cookies() -> list:
    path = cfg["cookies_path"]
    if not os.path.exists(path):
        warn("Cookie file not found.")
        path = input(Y+" Enter full path to cookies.txt: "+W).strip()
        if os.path.exists(path): cfg["cookies_path"]=path; cfg.save()
    cookies=[]
    try:
        with open(path,encoding="utf-8",errors="ignore") as f:
            for line in f:
                line=line.strip()
                if line and line.startswith(COOKIE_PREFIX): cookies.append(line)
    except Exception as e: err(f"Cannot read cookies: {e}")
    return cookies

def cookie_login_all(pkgs: list, cookies: list):
    print(); info("Checking existing WebView databases…")
    db_map={pkg:_find_db_silent(pkg) for pkg in pkgs}
    has_db=[p for p in pkgs if db_map[p]]; no_db=[p for p in pkgs if not db_map[p]]
    for p in has_db: ok(f"{pkg_label(p,pkgs.index(p))} — DB ready")
    for p in no_db:  warn(f"{pkg_label(p,pkgs.index(p))} — needs WebView init")
    for pkg in no_db:
        label=pkg_label(pkg,pkgs.index(pkg)); print()
        info(f"Initialising {CY}{label}{RS}…"); sh(f"am force-stop {pkg}",silent=True,timeout=5)
        time.sleep(0.5); db=fast_init_webview(pkg,timeout=30)
        sh(f"am force-stop {pkg}",silent=True,timeout=5); time.sleep(0.8)
        if db: db_map[pkg]=db; ok(f"{label} — DB initialised")
        else:  err(f"{label} — WebView never initialised (skipping)")
    print(); info("Writing cookies in parallel…")
    results={}; lock=threading.Lock()
    def do_inject(pkg,cookie):
        db=db_map.get(pkg)
        s=_write_cookie(pkg,db,cookie) if db else False
        with lock: results[pkg]=s
    threads=[]
    for i,pkg in enumerate(pkgs):
        if i>=len(cookies): break
        t=threading.Thread(target=do_inject,args=(pkg,cookies[i]),daemon=True)
        threads.append((pkg,i,t)); t.start()
    for pkg,i,t in threads: t.join(timeout=30)
    print()
    for i,pkg in enumerate(pkgs):
        label=pkg_label(pkg,i)
        if i>=len(cookies): warn(f"{label} — no cookie"); continue
        if results.get(pkg,False): ok(f"{label} — injected")
        else: err(f"{label} — failed")
    print(); info("Closing all Roblox tabs…")
    for pkg in pkgs: sh(f"am force-stop '{pkg}'",silent=True,timeout=5)
    print(); ok("Done.")

def cookie_logout(pkg: str) -> bool:
    db=_find_db_silent(pkg)
    if not db: return False
    tmp=_tmp_path(pkg)
    sh(f"cp '{db}' '{tmp}'",capture=True)
    try:
        con=_sq3.connect(tmp)
        con.execute("DELETE FROM cookies WHERE name=? AND host_key LIKE '%roblox%';",(COOKIE_NAME,))
        con.commit(); sh(f"cp '{tmp}' '{db}'",capture=True); return True
    except: return False
    finally:
        try: os.remove(tmp)
        except: pass

def cookie_logout_all(pkgs: list):
    print(); info("Logging out…")
    for pkg in pkgs:
        label=pkg_label(pkg,pkgs.index(pkg))
        if cookie_logout(pkg): ok(f"{label} — cookie cleared")
        else: err(f"{label} — logout failed")
    print(); ok("Logout complete."); go()

def manual_cookie_login():
    banner(); hdr("Manual Cookie Login")
    pkgs=cfg["packages"]
    if not pkgs: err("No packages installed."); go(); return
    cookies=read_cookies()
    if not cookies: err("No cookies found."); go(); return
    for i,pkg in enumerate(pkgs): print(f" {CY}[{i+1}]{W} {pkg_label(pkg,i)}")
    print()
    sel=input(Y+"Numbers or 'all': "+W).strip().lower()
    to_login=pkgs[:] if sel=="all" else [pkgs[n-1] for n in [int(x) for x in sel.split() if x.isdigit()] if 1<=n<=len(pkgs)]
    if not to_login: info("Nothing selected."); go(); return
    for i,pkg in enumerate(to_login):
        if i>=len(cookies): break
        db=_find_db_silent(pkg)
        if not db: warn(f"{pkg_label(pkg,pkgs.index(pkg))} — no DB"); continue
        if _write_cookie(pkg,db,cookies[i]): ok(f"{pkg_label(pkg,pkgs.index(pkg))} — injected")
        else: err(f"{pkg_label(pkg,pkgs.index(pkg))} — failed")
    go()

def manual_cookie_logout():
    banner(); hdr("Manual Cookie Logout")
    pkgs=cfg["packages"]
    if not pkgs: err("No packages."); go(); return
    for i,pkg in enumerate(pkgs): print(f" {CY}[{i+1}]{W} {pkg_label(pkg,i)}")
    print()
    sel=input(Y+"Numbers or 'all': "+W).strip().lower()
    to_logout=pkgs[:] if sel=="all" else [pkgs[n-1] for n in [int(x) for x in sel.split() if x.isdigit()] if 1<=n<=len(pkgs)]
    if not to_logout: info("Nothing selected."); go(); return
    for pkg in to_logout:
        if cookie_logout(pkg): ok(f"{pkg_label(pkg,pkgs.index(pkg))} — cleared")
        else: err(f"{pkg_label(pkg,pkgs.index(pkg))} — failed")
    go()

def cookie_menu():
    banner(); hdr("Cookie Login / Logout")
    menu_item("1","Login All packages")
    menu_item("2","Logout All packages")
    menu_item("3","Manual Login")
    menu_item("4","Manual Logout")
    menu_item("0","Back")
    print(); c=input(CY+" › "+W+"Choice: "+RS).strip()
    if c=="1":
        cookies=read_cookies()
        if not cookies: err("No valid cookies."); go(); return
        pkgs=cfg["packages"]
        if not pkgs: err("No packages."); go(); return
        cookie_login_all(pkgs,cookies); go()
    elif c=="2":
        pkgs=cfg["packages"]
        if not pkgs: err("No packages."); go(); return
        cookie_logout_all(pkgs)
    elif c=="3": manual_cookie_login()
    elif c=="4": manual_cookie_logout()

# ─────────────────────────────────────────────────────────────────────────────
# Delta Key System  (complete rewrite)
# ─────────────────────────────────────────────────────────────────────────────

def has_key_dialog() -> bool:
    """
    BUG FIX: original code did get_xml().lower() then checked for "Receive Key"
    with capital R — that never matched. All checks are now lowercase.
    """
    xml = get_xml().lower()
    return any(k in xml for k in [
        "receive key", "enter key", "key system", "welcome back",
        "getkey", "whitelisted", "successfully whitelisted",
    ])

def _read_chrome_url_bar() -> str:
    """
    Read Chrome's address bar text via uiautomator resource-id.
    No coordinates needed — works on any screen size.
    """
    xml = get_xml()
    for rid in CHROME_URL_BAR_IDS:
        val = find_node_by_resource_id(rid, xml=xml)
        if val: return val
    # Fallback: dumpsys window sometimes has the URL in the window title
    out = sh("dumpsys window windows 2>/dev/null | grep -i 'mCurrentFocus' | head -3", capture=True, timeout=5)
    m = KEY_PATTERN.search(out)
    if m: return m.group(0)
    return ""

def grab_key_from_chrome() -> str:
    """
    Grab the FREE_ key from Chrome.
    Since VSPhone auto-solves the key, it will be sitting in the URL bar
    or visible as text on the page — no ads to click through.

    Strategy (no hardcoded coordinates):
      1. Read URL bar by resource-id
      2. Scan all visible UI text
      3. Check clipboard
      4. Tap any visible Copy button (found via text in XML)
      5. Scroll down and retry
    """
    chrome_pkg = get_chrome_pkg()

    for attempt in range(30):
        # 1 — URL bar (most reliable — key often appears here as a redirect)
        url_text = _read_chrome_url_bar()
        if url_text:
            m = KEY_PATTERN.search(url_text)
            if m:
                info(f"[Chrome] Key found in URL bar (attempt {attempt+1})")
                return m.group(0)

        # 2 — Scan every text node on screen
        all_text = read_all_ui_text()
        m = KEY_PATTERN.search(all_text)
        if m:
            key = m.group(0)
            info(f"[Chrome] Key found in page text (attempt {attempt+1}): {key[:18]}…")
            # Try tapping Copy so it also lands in clipboard
            tap_element(["Copy","COPY","copy key"])
            time.sleep(0.5)
            clip = _read_clipboard()
            return clip if clip.startswith(KEY_PREFIX) else key

        # 3 — Clipboard (Chrome may have auto-copied it)
        clip = _read_clipboard()
        if clip.startswith(KEY_PREFIX):
            info(f"[Chrome] Key in clipboard (attempt {attempt+1})")
            return clip

        # 4 — Tap a Copy button if visible, then re-check clipboard
        if tap_element(["Copy","COPY","copy key","copy"]):
            time.sleep(0.8)
            clip = _read_clipboard()
            if clip.startswith(KEY_PREFIX):
                info(f"[Chrome] Key copied via button (attempt {attempt+1})")
                return clip

        # 5 — Scroll down to reveal more of the page
        sh("input keyevent KEYCODE_PAGE_DOWN", silent=True)
        time.sleep(1.5)

        if attempt % 5 == 4:
            info(f"[Chrome] Still searching… {attempt+1}/30")

    warn("[Chrome] Key not found after 30 attempts.")
    return ""


def _enter_stored_key(key: str) -> str:
    info(f"Entering key: {CY}{key[:20]}…{RS}")
    # Focus the key input field
    if not tap_element(KW_KEY_INPUT):
        # Try broader terms if exact labels not found
        tap_element(["edit","input","field","text"])
    time.sleep(0.5)
    # Select all existing text and replace
    sh("input keyevent KEYCODE_CTRL_A", silent=True); time.sleep(0.2)
    # Put key in clipboard then paste — most reliable on Android
    _set_clipboard(key); time.sleep(0.4)
    sh("input keyevent KEYCODE_PASTE", silent=True); time.sleep(0.6)
    # Tap submit
    tap_element(KW_KEY_SUBMIT)
    time.sleep(1.5)
    return "entered"


def handle_key_dialog(pkg: str = None, force_fresh: bool = False) -> str:
    label = pkg_label(pkg, 0) if pkg else "unknown"
    info(f"[{label}] Key handler started…")

    # Use stored key if valid — no need to hit Chrome
    if not force_fresh and _key_is_valid():
        stored = cfg.get("delta_key","").strip()
        info(f"[{label}] Using stored key ({_key_remaining_str()} left)")
        # Bring floating window to front WITHOUT relaunching (no white screen)
        if pkg:
            bring_to_front(pkg)
        return _enter_stored_key(stored)

    warn(f"[{label}] {'Forcing fresh key grab' if force_fresh else 'No valid key — grabbing from Chrome'}…")

    # ── Step 1: Bring Delta floating window to front (no white screen) ─────
    if pkg:
        bring_to_front(pkg)
        time.sleep(0.5)

    # ── Step 2: Confirm the key dialog is actually visible ─────────────────
    if not has_key_dialog():
        warn(f"[{label}] Key dialog not visible after bring_to_front — skipping")
        return "waiting"

    # ── Step 3: Tap "Receive Key" found via uiautomator text search ────────
    info(f"[{label}] Looking for 'Receive Key' button in UI…")
    tapped = False
    for attempt in range(8):
        xml = get_xml()
        pos = find_element(KW_KEY_RECEIVE + ["receive","get key"], clickable=True, xml=xml)
        if pos:
            sh(f"input tap {pos[0]} {pos[1]}", silent=True)
            info(f"[{label}] Tapped 'Receive Key' at {pos} (attempt {attempt+1})")
            tapped = True
            break
        time.sleep(0.6)

    if not tapped:
        warn(f"[{label}] 'Receive Key' button not found in XML. Is the dialog visible and focused?")
        return "waiting"

    # ── Step 4: Wait for Chrome to open ───────────────────────────────────
    chrome_pkg = get_chrome_pkg()
    info(f"[{label}] Waiting for Chrome ({chrome_pkg}) to open…")
    chrome_opened = wait_for_foreground(chrome_pkg.split(".")[1], timeout=12)
    if chrome_opened:
        info(f"[{label}] Chrome is in front — good")
    else:
        warn(f"[{label}] Chrome didn't come to front — trying to open it manually…")
        sh(f"monkey -p {chrome_pkg} -c android.intent.category.LAUNCHER 1", silent=True)
        time.sleep(2)

    # Give the key page a moment to fully render
    time.sleep(3)

    # ── Step 5: Grab the key from Chrome ──────────────────────────────────
    key = grab_key_from_chrome()

    if not key.startswith(KEY_PREFIX):
        warn(f"[{label}] Failed to grab key — will retry next cycle.")
        # Bring Delta back so we don't leave Chrome in front
        if pkg: bring_to_front(pkg)
        return "waiting"

    # ── Step 6: Save key ──────────────────────────────────────────────────
    _save_key(key)
    ok(f"[{label}] Key saved (24h): {key[:18]}…")

    # ── Step 7: Return to Delta floating window (no relaunch) ─────────────
    if pkg:
        info(f"[{label}] Returning to Delta floating window…")
        bring_to_front(pkg)
        # Wait until Delta's key input field is visible
        for _ in range(10):
            if find_element(KW_KEY_INPUT + ["enter key","key system","whitelisted"]):
                break
            time.sleep(0.7)

    # ── Step 8: Enter the key ─────────────────────────────────────────────
    result = _enter_stored_key(key)
    ok(f"[{label}] Key entered!")

    # ── Step 9: Apply same key to all other clones ────────────────────────
    for other_pkg in cfg.get("packages", []):
        if other_pkg == pkg:
            continue
        bring_to_front(other_pkg)
        time.sleep(1.2)
        if has_key_dialog():
            info(f"Applying key to {pkg_label(other_pkg, 0)}…")
            _enter_stored_key(key)

    return result

# ─────────────────────────────────────────────────────────────────────────────
# Auto-sort tabs
# ─────────────────────────────────────────────────────────────────────────────
def auto_sort_tabs():
    if not cfg.get("auto_sort_tabs", True): return
    try:
        sh("input keyevent KEYCODE_APP_SWITCH", silent=True); time.sleep(0.8)
        sh("input keyevent KEYCODE_APP_SWITCH", silent=True); time.sleep(0.5)
    except: pass

# ─────────────────────────────────────────────────────────────────────────────
# Auto Relaunch
# ─────────────────────────────────────────────────────────────────────────────
def begin_auto_relaunch():
    banner(); hdr("Begin Auto Relaunch (Background Mode)")
    pkgs = cfg["packages"]; game_id = cfg["game_id"]
    if not pkgs: err("No packages detected."); go(); return

    state = {}
    for i, pkg in enumerate(pkgs):
        state[pkg] = {"label":pkg_label(pkg,i),"status":"INIT","crashes":0,
                      "since":None,"until":None,"key_try":0,"force_fresh":False}

    def launch(pkg):
        sh(f"am start -a android.intent.action.VIEW "
           f"-d 'roblox://experiences/start?placeId={game_id}' {pkg}", silent=True)
        state[pkg].update({"since":time.time(),"status":"BOOTING","until":None})

    def kill(pkg):
        sh(f"am force-stop '{pkg}'", silent=True, timeout=5)

    def draw():
        now=time.time(); W2=62
        stats=get_system_stats()
        print()
        print(CY+f" ╔{'═'*W2}╗")
        print(CY+" ║"+Y+BR+f" AUTO RELAUNCH · {len(pkgs)} clone(s) · Ctrl+C to stop".ljust(W2)+RS+CY+"║")
        print(CY+f" ╠{'═'*W2}╣")
        print(CY+" ║"+DIM+W+f" {stats}".ljust(W2)+RS+CY+"║")
        print(CY+f" ╠{'═'*W2}╣")
        kline = G+f" Key OK — expires in {_key_remaining_str()}" if _key_is_valid() else Y+" Key EXPIRED / missing — will re-grab"
        print(CY+" ║"+kline.ljust(W2+12)+CY+"║")
        print(CY+f" ╠{'═'*W2}╣")
        print(CY+" ║"+DIM+W+f" {'Clone':<12}{'Status':<11}{'Crashes':<9}{'Info':<22}"+RS+CY+"║")
        print(CY+f" ╠{'═'*W2}╣")
        for pkg, s in state.items():
            st=s["status"]; cr=s["crashes"]; lab=s["label"]
            if st=="BOOTING":
                elapsed=int(now-s["since"]) if s["since"] else 0
                upt=f"boot {elapsed}s/{BOOT_GRACE}s"; sc=CY; icon="○"
            elif st=="LIVE" and s["since"]:
                e=int(now-s["since"])
                upt=f"{e//3600:02d}:{(e%3600)//60:02d}:{e%60:02d}"; sc=G+BR; icon="●"
            elif st=="WAIT":
                rem=max(0,int(s["until"]-now)) if s["until"] else 0
                upt=f"relaunch {rem}s"; sc=Y; icon="~"
            elif st=="KEY":
                upt="key dialog"; sc=M+BR; icon="K"
            elif st=="CAPTCHA":
                upt="captcha!"; sc=R+BR; icon="!"
            else:
                upt="starting…"; sc=DIM; icon="○"
            print(CY+" ║"+W+" "+sc+f"{lab:<12}"+RS+W+f"{icon} "+sc+f"{st:<10}"+RS+W+f"{cr:<9}"+DIM+f"{upt:<22}"+RS+CY+"║")
        print(CY+f" ╚{'═'*W2}╝")
        print(DIM+f"\n last check: {time.strftime('%H:%M:%S')}"+RS)

    info("Killing all clones…")
    for pkg in pkgs: kill(pkg)
    time.sleep(2)
    info("Launching all clones…")
    for pkg in pkgs:
        info(f" {state[pkg]['label']}…"); launch(pkg); time.sleep(1.5)

    captcha_at=key_at=sort_at=key_full_check_at=0.0

    try:
        while True:
            now=time.time()

            # Captcha check
            if now-captcha_at>8:
                if has_captcha():
                    for pkg,s in state.items():
                        if s["status"]=="LIVE":
                            s["crashes"]+=1; s["status"]="WAIT"; s["until"]=now+15; kill(pkg)
                captcha_at=now

            # Key dialog check (foreground only)
            if now-key_at>5:
                if has_key_dialog():
                    fg=get_foreground_pkg()
                    if fg in state and state[fg]["status"]!="KEY":
                        state[fg]["status"]="KEY"; state[fg]["key_try"]=0; state[fg]["force_fresh"]=False
                key_at=now

            # Periodic check: bring each LIVE clone to front and look for hidden key dialogs
            if now-key_full_check_at>20:
                for p in pkgs:
                    if state[p]["status"]=="LIVE":
                        bring_to_front(p); time.sleep(1.0)
                        if has_key_dialog():
                            info(f"[{state[p]['label']}] Hidden key dialog found — handling…")
                            handle_key_dialog(p)
                key_full_check_at=now

            if cfg.get("auto_sort_tabs",True) and now-sort_at>45:
                auto_sort_tabs(); sort_at=now

            for pkg,s in state.items():
                st=s["status"]
                if st=="WAIT":
                    if s["until"] and now>=s["until"]: launch(pkg)
                    continue
                if st=="BOOTING":
                    elapsed=now-(s["since"] or now)
                    if elapsed>=BOOT_GRACE:
                        if sh(f"pidof '{pkg}' 2>/dev/null",capture=True,timeout=4).strip():
                            s["status"]="LIVE"
                        else:
                            s["crashes"]+=1; s["status"]="WAIT"; s["until"]=now+15
                    continue
                if st=="LIVE":
                    if not sh(f"pidof '{pkg}' 2>/dev/null",capture=True,timeout=4).strip():
                        s["crashes"]+=1; s["status"]="WAIT"; s["until"]=now+15
                    continue
                if st=="KEY":
                    result=handle_key_dialog(pkg=pkg,force_fresh=s["force_fresh"])
                    s["force_fresh"]=False
                    if result in ("entered","none"):
                        s["status"]="LIVE"; s["key_try"]=0
                    else:
                        s["key_try"]+=1
                        if s["key_try"]>=MAX_KEY_FAIL:
                            s["key_try"]=0; warn(f"{s['label']} failed 3× — forcing new key")
                            _clear_key(); s["force_fresh"]=True
                    continue

            draw()
            time.sleep(3.5)

    except KeyboardInterrupt:
        print(); info("Stopping…")
        for pkg in pkgs: kill(pkg)
        ok("All stopped."); go()

# ─────────────────────────────────────────────────────────────────────────────
# AIO
# ─────────────────────────────────────────────────────────────────────────────
def aio():
    banner(); hdr("AIO — Full Setup & Auto Relaunch")
    info("Step 1/4: Installing APKs…")
    if not install_apks(pause=False): warn("AIO stopped."); go(); return
    print(); info("Step 2/4: Cookie Login…")
    cookies=read_cookies(); pkgs=cfg["packages"]
    if cookies and pkgs: cookie_login_all(pkgs, cookies)
    else: warn("Skipping login.")
    print(); info("Step 3/4: Installing AOTR TrackStat…")
    install_aotr_trackstat()
    print(); info("Step 4/4: Starting Auto Relaunch…")
    time.sleep(2); begin_auto_relaunch()

# ─────────────────────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────────────────────
def settings_menu():
    while True:
        banner(); hdr("Settings"); print()
        ak   = G+BR+"ON"  if cfg.get("auto_key",True)       else R+BR+"OFF"
        sort = G+BR+"ON"  if cfg.get("auto_sort_tabs",True)  else R+BR+"OFF"
        key  = cfg.get("delta_key","")
        if key and key.startswith(KEY_PREFIX):
            dk=G+key[:22]+"… "+(DIM+f"({_key_remaining_str()} left)" if _key_is_valid() else R+"EXPIRED")
        else:
            dk=R+"(none — will grab from Chrome)"+RS
        print(W+f" {CY}[1]{W} First Launch Delay  {DIM}-> {BR+Y}{cfg['first_launch_delay']}s")
        print(W+f" {CY}[2]{W} Relaunch Threshold  {DIM}-> {BR+Y}{cfg['relaunch_threshold']}s")
        print(W+f" {CY}[3]{W} Auto Key            {DIM}-> {ak}{RS}")
        print(W+f" {CY}[4]{W} Cookie File         {DIM}-> {Y}{cfg['cookies_path']}")
        print(W+f" {CY}[5]{W} GoFile URL          {DIM}-> {Y}{cfg['gofile_url'][:40]}")
        print(W+f" {CY}[6]{W} Game ID             {DIM}-> {Y}{cfg['game_id']}")
        print(W+f" {CY}[7]{W} Delta Key           {DIM}-> {dk}{RS}")
        print(W+f" {CY}[8]{W} Force re-grab key now")
        print(W+f" {CY}[9]{W} Install AOTR TrackStat (manual)")
        print(W+f" {CY}[10]{W} Auto Sort Tabs     {DIM}-> {sort}{RS}")
        print(W+f" {CY}[0]{W} Back"); print()
        c=input(CY+" › "+W+"Choice: "+RS).strip()
        if c=="1":
            v=input(Y+" Delay (s): "+W).strip()
            if v.isdigit(): cfg["first_launch_delay"]=int(v); ok("Saved.")
        elif c=="2":
            v=input(Y+" Threshold (s): "+W).strip()
            if v.isdigit(): cfg["relaunch_threshold"]=int(v); ok("Saved.")
        elif c=="3": cfg["auto_key"]=not cfg.get("auto_key",True); ok("Toggled.")
        elif c=="4":
            p=input(Y+" Path: "+W).strip()
            if os.path.exists(p): cfg["cookies_path"]=p; ok("Saved.")
            else: err("Not found.")
        elif c=="5": cfg["gofile_url"]=input(Y+" New URL: "+W).strip(); ok("Saved.")
        elif c=="6": cfg["game_id"]=input(Y+" New Game ID: "+W).strip(); ok("Saved.")
        elif c=="7":
            print(); info(f"Paste your {KEY_PREFIX} key (blank to clear):")
            k=input(Y+" Delta Key: "+W).strip()
            if k and k.startswith(KEY_PREFIX): _save_key(k); ok("Saved with 24h timer.")
            elif k=="": _clear_key(); ok("Cleared.")
            else: err(f"Key must start with {KEY_PREFIX}")
        elif c=="8":
            _clear_key(); ok("Key cleared — will re-grab on next KEY event.")
        elif c=="9":
            install_aotr_trackstat(); go()
        elif c=="10":
            cfg["auto_sort_tabs"]=not cfg.get("auto_sort_tabs",True); ok("Toggled.")
        elif c=="0": break

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    signal.signal(signal.SIGINT, lambda s,f: sys.exit(0))
    detect_packages(force=True)
    threading.Thread(target=aggressive_dialog_tapper, daemon=True).start()
    threading.Thread(target=_pkg_watcher, daemon=True).start()
    while True:
        banner(); noka=count_noka_installed()
        print(CY+" ┌─────────────────────────────────────────────┐")
        print(CY+" │ "+Y+BR+" MAIN MENU"+" "*35+RS+CY+"│")
        print(CY+" ├─────────────────────────────────────────────┤")
        menu_item("1","Install / Uninstall APKs",f"slots: {noka}/{MAX_CLONES}")
        menu_item("2","Cookie Login / Logout",f"{len(cfg['packages'])} package(s) ready")
        menu_item("3","AIO — Full Setup & Relaunch","install+login+trackstat+auto")
        menu_item("4","Begin Auto Relaunch","background mode + stats")
        menu_item("5","Settings","configure")
        menu_item("0","Exit","")
        print(CY+" └─────────────────────────────────────────────┘")
        print(); c=input(CY+" › "+W+"Choice: "+RS).strip()
        if   c=="1": apk_menu()
        elif c=="2": cookie_menu()
        elif c=="3": aio()
        elif c=="4": begin_auto_relaunch()
        elif c=="5": settings_menu()
        elif c=="0": print(); print(M+BR+" Goodbye! — "+CREATOR+RS); print(); break

if __name__ == "__main__":
    main()
