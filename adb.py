import os
import random
import subprocess
import time

import cv2
import numpy as np

_cached_adb_path = None

def get_adb_path() -> str:
    """Dynamically discover adb.exe from common LDPlayer installation paths across all drives,
    matching the original program's detection algorithm.
    """
    global _cached_adb_path
    if _cached_adb_path and os.path.exists(_cached_adb_path):
        return _cached_adb_path

    roots = [
        r"D:\LDPlayer", r"C:\LDPlayer", r"E:\LDPlayer", r"F:\LDPlayer",
        r"C:\Program Files\LDPlayer", r"C:\Program Files (x86)\LDPlayer",
        r"D:\Program Files\LDPlayer", r"C:\ChangZhi", r"D:\ChangZhi",
        os.path.expanduser(r"~\LDPlayer")
    ]
    subs = ["LDPlayer14", "LDPlayer9", "LDPlayer64", "LDPlayer4", ""]

    candidates = []
    for r in roots:
        for s in subs:
            candidates.append(os.path.join(r, s, "adb.exe"))

    for path in candidates:
        if os.path.exists(path):
            _cached_adb_path = path
            return path

    # Fallback to system adb if no specific LDPlayer path found
    _cached_adb_path = "adb"
    return _cached_adb_path


def device_connect(ip: str, port: int):
    adb_bin = get_adb_path()
    result = subprocess.run(
        [adb_bin, "connect", f"{ip}:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print(f"🔌 {result.stdout.strip().capitalize()}")
    if "connected" not in result.stdout and "already connected" not in result.stdout:
        raise Exception(f"❌ Failed to connect to {ip}:{port}\n{result.stderr.strip()}")


import struct


def device_capture_screen(ip: str, port: int):
    adb_bin = get_adb_path()
    # Try ultra-fast raw screencap decoding first (~15-18ms)
    try:
        proc = subprocess.Popen(
            [adb_bin, "-s", f"{ip}:{port}", "exec-out", "screencap"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        try:
            header = proc.stdout.read(12)
            if len(header) == 12:
                width, height, fmt = struct.unpack("<III", header)
                size = width * height * 4
                raw_data = proc.stdout.read(size)
                if len(raw_data) == size:
                    arr = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, 4))
                    return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        finally:
            try:
                proc.stdout.close()
            except Exception:
                pass
            try:
                proc.kill()
                proc.wait()
            except Exception:
                pass
    except Exception:
        pass

    # Fallback to standard PNG screencap if raw read encounters any format anomaly
    try:
        result = subprocess.run(
            [adb_bin, "-s", f"{ip}:{port}", "exec-out", "screencap", "-p"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=8.0
        )
        if result.stdout:
            img = np.frombuffer(result.stdout, dtype=np.uint8)
            return cv2.imdecode(img, cv2.IMREAD_COLOR)
    except Exception:
        pass
    return None


def device_tap(ip: str, port: int, x: int, y: int):
    adb_bin = get_adb_path()
    try:
        subprocess.run(
            [adb_bin, "-s", f"{ip}:{port}", "shell", "input", "tap", str(x), str(y)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8.0
        )
    except Exception:
        pass


def safe_device_tap(ip: str, port: int, x: int, y: int):
    adb_bin = get_adb_path()
    jitter_x = x + random.randint(-15, 15)
    jitter_y = y + random.randint(-15, 15)
    try:
        subprocess.run(
            [adb_bin, "-s", f"{ip}:{port}", "shell", "input", "tap", str(jitter_x), str(jitter_y)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8.0
        )
    except Exception:
        pass


def safe_device_scroll(ip: str, port: int, x: int, y: int, direction: str = "up", distance: int = 500, duration: int = 300):
    adb_bin = get_adb_path()
    jx = x + random.randint(-15, 15)
    jy = y + random.randint(-15, 15)
    direction_map = {
        "up":    (jx, jy + distance, jx, jy - distance),
        "down":  (jx, jy - distance, jx, jy + distance),
        "left":  (jx + distance, jy, jx - distance, jy),
        "right": (jx - distance, jy, jx + distance, jy),
    }
    if direction not in direction_map:
        raise ValueError(f"Invalid direction '{direction}'. Use: up, down, left, right.")
    x1, y1, x2, y2 = direction_map[direction]
    try:
        subprocess.run(
            [adb_bin, "-s", f"{ip}:{port}", "shell", "input", "swipe",
             str(x1), str(y1), str(x2), str(y2), str(duration)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10.0
        )
    except Exception:
        pass


_GAME_PKG = [None]


def get_focused_package(ip: str, port: int) -> str:
    """Detect currently focused Android package name via ADB dumpsys."""
    adb_bin = get_adb_path()
    sources = [
        ("window", ["mCurrentFocus", "mFocusedApp"]),
        ("activity", ["mResumedActivity", "ResumedActivity", "topResumedActivity"]),
    ]
    ignored = {"launcher", "systemui", "settings", "inputmethod", "ime", "permission", "packageinstaller"}
    for svc, keys in sources:
        try:
            r = subprocess.run(
                [adb_bin, "-s", f"{ip}:{port}", "shell", "dumpsys", svc],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            out = r.stdout.decode("utf-8", "replace") if r.stdout else ""
            for line in out.splitlines():
                if any(k in line for k in keys) and "null" not in line:
                    clean = line.replace("}", " ").replace("{", " ")
                    for tok in clean.split():
                        if "/" in tok and "." in tok.split("/")[0]:
                            pkg = tok.split("/")[0]
                            if pkg.count(".") >= 1 and " " not in pkg:
                                low = pkg.lower()
                                if not any(ig in low for ig in ignored):
                                    return pkg
        except Exception:
            pass
    return None


def remember_game_package(ip: str, port: int):
    """Save the running game's package name when verified game screen is active."""
    global _GAME_PKG
    if _GAME_PKG[0] is not None:
        return
    pkg = get_focused_package(ip, port)
    if pkg:
        _GAME_PKG[0] = pkg
        print(f"📌 [net] จำชื่อแอปเกมไว้แล้ว: {pkg} (ไว้ใช้ตอนต้องเปิดเกมใหม่)")


def device_is_app_running(ip: str, port: int, package: str = None) -> bool:
    if package is None:
        package = _GAME_PKG[0]
    if not package:
        return False
    adb_bin = get_adb_path()
    try:
        r = subprocess.run(
            [adb_bin, "-s", f"{ip}:{port}", "shell", "ps", "-A"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        out = r.stdout.decode("utf-8", "replace") if r.stdout else ""
        return package in out
    except Exception:
        return False


def device_reset_app(ip: str, port: int, package: str = None, max_retries: int = 3) -> bool:
    """Safely restart the game application matching prototype bot.py _restart_game."""
    global _GAME_PKG
    pkg = package or _GAME_PKG[0]
    if not pkg:
        print("[net] ยังไม่รู้ว่าแอปเกมชื่ออะไร (ยังไม่เคยเห็นหน้าจอเกมที่ยืนยันได้) -> ไม่ปิดแอปใดทั้งสิ้น")
        return False

    adb_bin = get_adb_path()
    print(f"🔄 [net] เกมค้าง/หลุด -> กำลังรีสตาร์ทแอป {pkg}...")
    subprocess.run(
        [adb_bin, "-s", f"{ip}:{port}", "shell", "am", "force-stop", pkg],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=15,
    )
    time.sleep(2)

    for attempt in range(1, max_retries + 1):
        print(f"📱 [net] เปิดแอป {pkg} (ครั้งที่ {attempt}/{max_retries})...")
        subprocess.run(
            [adb_bin, "-s", f"{ip}:{port}", "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        time.sleep(4)
        if device_is_app_running(ip, port, pkg):
            print(f"✅ [net] แอป {pkg} เปิดทำงานเรียบร้อยแล้ว")
            return True

    print(f"❌ [net] ไม่สามารถเปิดแอป {pkg} ใหม่ได้")
    return False

