import builtins
import json
import os
import queue
import multiprocessing
from multiprocessing import Queue, Event, Process
import random
import threading
import time
import tkinter as tk
import tkinter.font as tkFont
from datetime import datetime
from tkinter import messagebox, ttk

import sys

# Ensure stdout supports UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─────────────────────────────────────────
#  Bot imports
# ─────────────────────────────────────────
from bot import BOOST_CHOICES, AutoJumper, get_detection_stage_names
from detection import detect_stage, load_templates
from actions import (
    accept_congratulations, accept_daily_checkin, accept_daily_checkin_boost_set,
    accept_daily_new, accept_daily_treasure, accept_enter_league, accept_league_results,
    accept_level_up, accept_mystery_box, accept_overtake_break_score,
    accept_previous_rank_results, accept_relic_claim, accept_too_many_treasures,
    close_announcement_dialog, complete_finish, draw_gifts_loop,
    handle_anti_bot, handle_connection_lost, handle_inactive,
    handle_quick_receive_and_send_lives, handle_send_friend_life, open_relic_complete,
    play_game, purchase_cookie_relay, purchase_desired_random_boost, purchase_fast_start,
    start_game, using_cookie_relay, using_fast_start,
)
from adb import device_capture_screen, device_connect, device_reset_app, remember_game_package
from coin_reader import read_coins
import config as cfg

# ─────────────────────────────────────────
#  Colour palette
# ─────────────────────────────────────────
C = {
    "bg":       "#0F1424",
    "panel":    "#161C30",
    "card":     "#161C30",
    "accent":   "#3ED9C4",
    "accent_fg": "#04342C",
    "green":    "#249A62",
    "green_fg": "#022B18",
    "danger":   "#E63946",
    "danger_fg": "#FFFFFF",
    "text":     "#E8EAF0",
    "muted":    "#9AA3B8",
    "border":   "#252C42",
    "log_bg":   "#0A0C14",
    "log_info": "#3ED9C4",
    "log_warn": "#F4A261",
    "log_err":  "#E63946",
    "log_ok":   "#249A62",
    "log_ts":   "#9AA3B8",
    "accent2":  "#3ED9C4",
}

FONT = "Segoe UI"


def font(size=10, bold=False):
    return tkFont.Font(family=FONT, size=size, weight="bold" if bold else "normal")


def make_styles():
    """Configure ttk styles for the app."""
    s = ttk.Style()
    s.theme_use("clam")

    # Green start button
    s.configure("Start.TButton",
                 background=C["accent"], foreground=C["accent_fg"],
                 font=(FONT, 11, "bold"), relief="flat",
                 borderwidth=0, focusthickness=0, padding=(20, 8))
    s.map("Start.TButton",
          background=[("active", "#2AB3A1"), ("disabled", C["muted"])],
          foreground=[("disabled", "#cccccc")])

    # Red stop button
    s.configure("Stop.TButton",
                 background=C["danger"], foreground=C["danger_fg"],
                 font=(FONT, 11, "bold"), relief="flat",
                 borderwidth=0, focusthickness=0, padding=(20, 8))
    s.map("Stop.TButton",
          background=[("active", "#C22E3A"), ("disabled", C["muted"])],
          foreground=[("disabled", "#cccccc")])

    # Ghost button
    s.configure("Ghost.TButton",
                 background=C["bg"], foreground=C["text"],
                 font=(FONT, 9, "bold"), relief="solid",
                 bordercolor=C["muted"], lightcolor=C["bg"], darkcolor=C["bg"], borderwidth=1,
                 focusthickness=0, padding=(10, 4))
    s.map("Ghost.TButton",
          background=[("active", C["panel"]), ("disabled", C["bg"])],
          foreground=[("active", C["accent"]), ("disabled", C["muted"])],
          bordercolor=[("active", C["accent"]), ("disabled", C["border"])])

    # Small muted button
    s.configure("Muted.TButton",
                 background="#333355", foreground=C["muted"],
                 font=(FONT, 9), relief="flat",
                 borderwidth=0, focusthickness=0, padding=(8, 4))
    s.map("Muted.TButton",
          background=[("active", "#444466")])

    # Combobox
    s.configure("TCombobox",
                 fieldbackground=C["panel"], background=C["panel"],
                 foreground=C["text"], selectbackground=C["accent"],
                 selectforeground="white", arrowcolor=C["text"],
                 bordercolor=C["border"])
    s.map("TCombobox",
          fieldbackground=[("readonly", C["panel"])],
          foreground=[("readonly", C["text"])],
          selectbackground=[("readonly", C["accent"])])

    # Scrollbar
    s.configure("Vertical.TScrollbar",
                 background=C["panel"], troughcolor=C["log_bg"],
                 arrowcolor=C["muted"], bordercolor=C["panel"],
                 relief="flat")


class Toggle(tk.Frame):
    """Pill-shaped toggle using single background container."""

    def __init__(self, parent, var: tk.BooleanVar):
        super().__init__(parent, bg=C["panel"], padx=2, pady=2)
        self._var = var
        self._on  = tk.Label(self, text="ON",
                              font=font(8, bold=True), padx=8, pady=2,
                              cursor="hand2", relief="flat")
        self._off = tk.Label(self, text="OFF",
                              font=font(8, bold=True), padx=8, pady=2,
                              cursor="hand2", relief="flat")
        self._on.pack(side="left")
        self._off.pack(side="left")
        self._disabled = False
        self._on.bind("<Button-1>",  lambda _: self._on_click(True))
        self._off.bind("<Button-1>", lambda _: self._on_click(False))
        var.trace_add("write", lambda *_: self._refresh())
        self._refresh()

    def _on_click(self, val):
        if not self._disabled:
            self._var.set(val)

    def configure(self, state):
        self._disabled = (state == "disabled")
        cursor = "arrow" if self._disabled else "hand2"
        self._on.configure(cursor=cursor)
        self._off.configure(cursor=cursor)
        self._refresh()

    def _refresh(self):
        if getattr(self, "_disabled", False):
            self._on.configure(bg=C["panel"], fg=C["muted"])
            self._off.configure(bg=C["panel"], fg=C["muted"])
            return
        if self._var.get():
            self._on.configure(bg=C["green"], fg=C["green_fg"])
            self._off.configure(bg=C["panel"], fg=C["muted"])
        else:
            self._on.configure(bg=C["panel"], fg=C["muted"])
            self._off.configure(bg=C["danger"], fg=C["danger_fg"])


class StatusBadge(tk.Label):
    """Coloured status pill label."""

    STATES = {
        "idle":    (C["muted"],   "●  Idle"),
        "running": (C["accent"],   "● Running"),
        "error":   (C["danger"],  "●  Error"),
        "stopped": (C["danger"], "●  Stopped"),
    }

    def __init__(self, parent):
        super().__init__(parent, text="●  Idle", bg=C["muted"], fg="white",
                         font=font(9, bold=True), padx=10, pady=3, relief="flat")
        self._anim_id = None

    def set_state(self, state: str):
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None
        color, text = self.STATES.get(state, (C["muted"], state))
        self.configure(bg=color, text=text)
        if state == "running":
            self._pulse()

    def _pulse(self):
        alt = ["#00c97a", "#009960"]
        cur = self.cget("bg")
        nxt = alt[0] if cur == alt[1] else alt[1]
        self.configure(bg=nxt)
        self._anim_id = self.after(600, self._pulse)


# ─────────────────────────────────────────────────────────────────

def bot_process_runner(mode, ip, port, options, log_q, stat_q, stop_event):
    import builtins
    from datetime import datetime
    import sys
    import random, time
    from adb import device_capture_screen, device_connect, device_reset_app
    from coin_reader import read_coins
    import config as cfg
    from detection import detect_stage, load_templates
    from bot import BOOST_CHOICES, AutoJumper, get_detection_stage_names
    from actions import (
        accept_congratulations, accept_daily_checkin, accept_daily_checkin_boost_set,
        accept_daily_new, accept_daily_treasure, accept_enter_league, accept_league_results,
        accept_level_up, accept_mystery_box, accept_overtake_break_score,
        accept_previous_rank_results, accept_relic_claim, accept_too_many_treasures,
        close_announcement_dialog, complete_finish, draw_gifts_loop,
        handle_anti_bot, handle_inactive,
        handle_quick_receive_and_send_lives, handle_send_friend_life, open_relic_complete,
        play_game, purchase_cookie_relay, purchase_desired_random_boost, purchase_fast_start,
        start_game, using_cookie_relay, using_fast_start,
    )

    _original_print = builtins.print
    def _mp_print(*args, **kwargs):
        msg = " ".join(str(a) for a in args)
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_q.put(f"[{timestamp}] {msg}")
        try:
            _original_print(f"[{timestamp}]", *args, **kwargs)
        except:
            pass
    builtins.print = _mp_print

    try:
        cfg.DEVICE_IP = ip
        cfg.DEVICE_PORT = port
        
        device_connect(ip, port)
        if mode == "gift":
            print("🎁 เริ่มโหมดสุ่มของขวัญอัตโนมัติ...")
            draw_gifts_loop(stop_event, on_drawn=lambda c: stat_q.put(("stat", "gifts", str(c))))
            print("🛑 จบโหมดสุ่มของขวัญ")
        elif mode == "hearts":
            print("💖 เริ่มโหมดส่งหัวใจ (Leaderboard)...")
            handle_send_friend_life(stop_event)
            print("🛑 จบโหมดส่งหัวใจ")
        elif mode == "quick_hearts":
            print("✉️ เริ่มโหมดรับและส่งหัวใจจากกล่องจดหมาย...")
            handle_quick_receive_and_send_lives()
            print("🛑 จบโหมดรับและส่งหัวใจจากกล่องจดหมาย")
        else:
            bot_loop_func(ip, port, options, stop_event, stat_q)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error: {e}")
        stat_q.put(("state", "error", None))
    finally:
        stat_q.put(("state", "stopped", None))
        print("🛑 Bot process exited.")

def bot_loop_func(ip: str, port: int, options: dict, stop_event, stat_q):
    games = 0
    try:
        print(f"🚀 CookiePilot Started")
        print(f"📱 Connecting to {ip}:{port}…")
        device_connect(ip, port)
        load_templates()

        auto_jumper = AutoJumper() if options.get("use_auto_jump", True) else None

        last_stage         = None
        is_first_game      = True
        detection_group    = "PRE_GAME"
        last_detected_time = time.time()
        
        def get_lives_interval():
            base_min = options.get("hearts_interval", 30)
            base_sec = base_min * 60
            return random.uniform(base_sec * 0.8, base_sec * 1.2)

        lives_interval     = get_lives_interval()
        last_lives_time    = time.time()
        conn_lost_streak   = 0

        coin_total  = 0
        coin_rounds = 0
        box_total   = 0

        # Reset UI labels on start
        stat_q.put(("stat", "games", "0"))
        stat_q.put(("stat", "coin_last", "0"))
        stat_q.put(("stat", "coin_total", "0"))
        stat_q.put(("stat", "boxes", "0"))
        stat_q.put(("stat", "gifts", "0"))

        while not stop_event.is_set():
            screen = device_capture_screen(ip, port)
            stage  = detect_stage(screen, get_detection_stage_names(detection_group))

            if stage is None:
                recovery = cfg.DETECTION_RECOVERY_SCAN_INTERVAL[detection_group]
                if time.time() - last_detected_time >= recovery:
                    stage = detect_stage(screen)
                    last_detected_time = time.time()
            else:
                last_detected_time = time.time()

            stat_q.put(("stat", "stage", stage or "Scanning…"))
            stat_q.put(("stat", "group", detection_group))

            # Remember running game package dynamically when verified stage is detected
            if stage in ("MAINMENU", "PURCHASE_ITEM", "GAME_START", "GAME_RELAY", "GAME_COMPLETE", "MYSTERY_BOX"):
                remember_game_package(ip, port)
                conn_lost_streak = 0

            if stage == last_stage:
                time.sleep(0.1)
                continue
            last_stage = stage

            # ── Stage handlers ──
            if stage == "MAINMENU":
                print("🎮 Detected Stage: MAINMENU")
                time.sleep(1)

                # Check max rounds limit
                max_r = options.get("max_rounds", 0)
                if max_r > 0 and games >= max_r:
                    print(f"🎉 เล่นครบตามจำนวนรอบที่กำหนดแล้ว ({games}/{max_r} รอบ) → หยุดบอทอัตโนมัติ")
                    break

                lives_elapsed = time.time() - last_lives_time
                if options.get("use_auto_hearts", True) and lives_elapsed >= lives_interval:
                    print(f"💌 ~{options.get('hearts_interval', 30)} min passed ({lives_elapsed/60:.1f} min) — receiving mailbox lives & sending leaderboard hearts…")
                    # 1. Receive all lives from Mailbox & send quick replies
                    handle_quick_receive_and_send_lives(stop_event, max_hearts=options.get("max_hearts_send", 0))
                    time.sleep(1.5)
                    # 2. Send hearts to all friends on Leaderboard
                    handle_send_friend_life(stop_event, max_hearts=options.get("max_hearts_send", 0), on_sent=lambda c: stat_q.put(("stat", "hearts", str(c))))
                    last_lives_time = time.time()
                    lives_interval  = get_lives_interval()
                    last_stage      = None
                    continue

                if detection_group == "POST_GAME":
                    detection_group = "PRE_GAME"
                    last_stage      = None
                    continue

                # ── Gift Draw (before each game)
                if options.get("use_gift_draw"):
                    print("🎁 Running Auto Gift Draw...")
                    draw_gifts_loop(stop_event, on_drawn=lambda c: stat_q.put(("stat", "gifts", str(c))))
                    last_stage = None
                    continue

                if not is_first_game:
                    min_d = options.get("min_delay", 30)
                    max_d = options.get("max_delay", 60)
                    d = random.uniform(min_d, max_d)
                    print(f"⏳ Waiting {d:.1f}s before next game…")
                    time.sleep(d)

                is_first_game = False
                start_game()
                games += 1
                stat_q.put(("stat", "games", str(games)))
                detection_group = "PRE_GAME"

            elif stage == "PURCHASE_ITEM":
                print("🛒 Detected Stage: PURCHASE_ITEM")
                if options.get("use_fast_start"):   purchase_fast_start()
                if options.get("use_cookie_relay"):  purchase_cookie_relay()
                if options.get("use_desired_random_boost"):
                    purchase_desired_random_boost(
                        options.get("desired_boost_template"), options.get("desired_boost_name"))
                play_game()
                detection_group = "IN_GAME"
                time.sleep(0.2)
                last_stage = None

            elif stage == "GAME_START":
                print("🏁 Detected Stage: GAME_START")
                if options.get("use_fast_start"): using_fast_start()
                detection_group = "IN_GAME"

            elif stage == "GAME_RELAY":
                print("🔄 Detected Stage: GAME_RELAY")
                if options.get("use_cookie_relay"): using_cookie_relay()
                detection_group = "IN_GAME"

            elif stage == "GAME_COMPLETE":
                print("✅ Detected Stage: GAME_COMPLETE")
                print("⏳ Waiting for score animation to settle...")
                time.sleep(6.5)
                final_screen = device_capture_screen(ip, port)
                
                # ── Read coins from result screen
                from coin_reader import read_coins
                coins = read_coins(final_screen)
                if coins is not None:
                    coin_total += coins
                    coin_rounds += 1
                    avg = int(coin_total / coin_rounds)
                    stat_q.put(("stat", "coin_last", f"{coins:,}"))
                    stat_q.put(("stat", "coin_total", f"{coin_total:,}"))
                    print(f"🪙 เหรียญรอบนี้: {coins:,}  (รวม {coin_total:,}, ค่าเฉลี่ย {avg:,}/รอบ)")
                else:
                    print("⚠️ ไม่สามารถอ่านตัวเลขเหรียญได้ (ภาพอาจยังไม่นิ่งหรือไม่มีตัวเลข)")

                complete_finish()
                detection_group = "POST_GAME"

            elif stage == "MYSTERY_BOX":
                print("🎁 Detected Stage: MYSTERY_BOX")
                box_total += 1
                stat_q.put(("stat", "boxes", str(box_total)))
                print(f"📦 รับกล่องปริศนาเรียบร้อย (รวม {box_total} กล่อง)")
                accept_mystery_box()
                time.sleep(3)
                detection_group = "POST_GAME"
                last_stage = None

            elif stage == "CONGRATULATIONS":
                print("🎉 Detected Stage: CONGRATULATIONS")
                accept_congratulations()
                detection_group = "POST_GAME"
                last_stage = None

            elif stage == "LEVEL_UP":
                print("⬆️ Detected Stage: LEVEL_UP")
                accept_level_up()
                detection_group = "PRE_GAME"

            elif stage == "DAILY_CHECKIN":
                print("📅 Detected Stage: DAILY_CHECKIN")
                accept_daily_checkin()
                detection_group = "PRE_GAME"

            elif stage == "DAILY_CHECKIN_BOOST_SET":
                print("📅 Detected Stage: DAILY_CHECKIN_BOOST_SET")
                accept_daily_checkin_boost_set()
                detection_group = "PRE_GAME"

            elif stage == "DAILY_TREASURE":
                print("💎 Detected Stage: DAILY_TREASURE")
                accept_daily_treasure()
                detection_group = "PRE_GAME"

            elif stage == "DAILY_NEW":
                print("📰 Detected Stage: DAILY_NEW")
                accept_daily_new()
                detection_group = "PRE_GAME"

            elif stage == "ENTER_LEAGUE":
                print("🏆 Detected Stage: ENTER_LEAGUE")
                accept_enter_league()
                detection_group = "PRE_GAME"

            elif stage == "LEAGUE_RESULTS":
                print("🏆 Detected Stage: LEAGUE_RESULTS")
                accept_league_results()
                detection_group = "PRE_GAME"

            elif stage == "PREVIOUS_RANK_RESULTS":
                print("🏆 Detected Stage: PREVIOUS_RANK_RESULTS")
                accept_previous_rank_results()
                detection_group = "PRE_GAME"

            elif stage == "OVERTAKE_BREAK_SCORE":
                print("🏆 Detected Stage: OVERTAKE_BREAK_SCORE")
                accept_overtake_break_score()
                detection_group = "POST_GAME"
                last_stage = None

            elif stage == "TOO_MANY_TREASURES":
                print("💎 Detected Stage: TOO_MANY_TREASURES")
                accept_too_many_treasures()
                detection_group = "PRE_GAME"

            elif stage == "RELIC_COMPLETE":
                print("🏺 Detected Stage: RELIC_COMPLETE")
                open_relic_complete()
                detection_group = "PRE_GAME"

            elif stage == "RELIC_CLAIM":
                print("🏺 Detected Stage: RELIC_CLAIM")
                accept_relic_claim(stop_event)
                detection_group = "PRE_GAME"

            elif stage == "ANTI_BOT":
                print("⚠️ Detected Stage: ANTI_BOT")
                handle_anti_bot(screen)
                last_stage = None

            elif stage == "CONNECTION_LOST":
                conn_lost_streak += 1
                print(f"🔌 Detected Stage: CONNECTION_LOST (ครั้งที่ {conn_lost_streak}) -> กดเชื่อมใหม่ในเกม")
                handle_connection_lost()
                if conn_lost_streak >= 3:
                    print(f"⚠️ หลุดการเชื่อมต่อซ้ำ {conn_lost_streak} ครั้ง -> กำลังเปิดเกมใหม่ด้วยแพ็กเกจที่จำไว้...")
                    device_reset_app(ip, port)
                    time.sleep(5)
                    close_announcement_dialog()
                    conn_lost_streak = 0
                detection_group = "PRE_GAME"
                last_stage      = None

            elif stage == "INACTIVE":
                print("💤 Detected Stage: INACTIVE")
                handle_inactive()
                last_stage = None

            # Auto-jump
            if auto_jumper is not None:
                if detection_group == "IN_GAME" and not auto_jumper.is_active():
                    auto_jumper.start()
                elif detection_group != "IN_GAME" and auto_jumper.is_active():
                    auto_jumper.stop()

            time.sleep(0.25)
    except Exception as e:
        print(f"❌ Error in bot loop: {e}")
    finally:
        print("🛑 Bot loop ended.")


#  Main Application
# ─────────────────────────────────────────────────────────────────
class BotTab(ttk.Frame):

    def __init__(self, parent, port="5555"):
        super().__init__(parent)
        self.port = port
        self.pack(fill="both", expand=True)

        # Process state
        self._bot_process = None
        self._stop_event = Event()
        self._log_q = Queue()
        self._stat_q = Queue()
        self._bot_running = False
        self._uptime_start: float = 0

        # Option variables
        self.var_ip              = tk.StringVar(value=cfg.DEVICE_IP)
        self.var_port            = tk.StringVar(value=str(self.port))
        self.var_auto_jump       = tk.BooleanVar(value=True)
        self.var_fast_start      = tk.BooleanVar(value=False)
        self.var_cookie_relay    = tk.BooleanVar(value=False)
        self.var_random_boost    = tk.BooleanVar(value=False)
        self.var_auto_hearts     = tk.BooleanVar(value=True)
        self.var_hearts_interval = tk.StringVar(value="30")
        self.var_max_hearts_send = tk.StringVar(value="0")
        self.var_max_rounds      = tk.StringVar(value="0")
        self.var_min_delay       = tk.StringVar(value="30")
        self.var_max_delay       = tk.StringVar(value="60")
        self.var_bot_mode        = tk.StringVar(value="run")

        self._build_ui()
        self._load_user_settings()
        self._poll_logs()
        

        # Auto-save traces whenever options change
        for var in [self.var_ip, self.var_port, self.var_auto_jump, self.var_fast_start,
                    self.var_cookie_relay, self.var_random_boost, self.var_auto_hearts,
                    self.var_hearts_interval, self.var_max_hearts_send, self.var_max_rounds, self.var_min_delay,
                    self.var_max_delay, self.var_bot_mode]:
            var.trace_add("write", lambda *_: self._save_user_settings())
        self._boost_combo.bind("<<ComboboxSelected>>", lambda _: self._save_user_settings())

    # ── User Settings ──────────────────────────────────────────────
    def _get_settings_filename(self):
        port_val = self.var_port.get().strip()
        port = port_val if port_val.isdigit() else "5555"
        return f"user_settings_{port}.json"

    def _load_user_settings(self):
        filename = self._get_settings_filename()
        if not os.path.exists(filename):
            if os.path.exists("user_settings.json"):
                filename = "user_settings.json"
            else:
                return
        try:
            self._loading_settings = True
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "ip" in data: self.var_ip.set(data["ip"])
            if "auto_jump" in data: self.var_auto_jump.set(bool(data["auto_jump"]))
            if "fast_start" in data: self.var_fast_start.set(bool(data["fast_start"]))
            if "cookie_relay" in data: self.var_cookie_relay.set(bool(data["cookie_relay"]))
            if "random_boost" in data: self.var_random_boost.set(bool(data["random_boost"]))
            if "boost_index" in data and hasattr(self, "_boost_combo"):
                idx = data["boost_index"]
                if 0 <= idx < len(BOOST_CHOICES):
                    self._boost_combo.current(idx)
                    boost_names = [f"{i+1:2}. {name}" for i, (name, _) in enumerate(BOOST_CHOICES)]
                    if hasattr(self, "_boost_var"):
                        self._boost_var.set(boost_names[idx])
            if "auto_hearts" in data: self.var_auto_hearts.set(bool(data["auto_hearts"]))
            if "hearts_interval" in data: self.var_hearts_interval.set(str(data["hearts_interval"]))
            if "max_hearts_send" in data: self.var_max_hearts_send.set(str(data["max_hearts_send"]))
            if "max_rounds" in data: self.var_max_rounds.set(str(data["max_rounds"]))
            if "min_delay" in data: self.var_min_delay.set(str(data["min_delay"]))
            if "max_delay" in data: self.var_max_delay.set(str(data["max_delay"]))
            if "bot_mode" in data: self.var_bot_mode.set(data["bot_mode"])
        except Exception as e:
            print(f"⚠️ Warning loading {filename}: {e}")
        finally:
            self._loading_settings = False

    def _save_user_settings(self):
        if getattr(self, "_loading_settings", False):
            return
        try:
            filename = self._get_settings_filename()
            idx = self._boost_combo.current() if hasattr(self, "_boost_combo") else 0
            boost_names = [f"{i+1:2}. {name}" for i, (name, _) in enumerate(BOOST_CHOICES)]
            if idx < 0 or idx >= len(BOOST_CHOICES):
                val = getattr(self, "_boost_var", tk.StringVar()).get()
                idx = boost_names.index(val) if val in boost_names else 0

            data = {
                "ip": self.var_ip.get(),
                "port": self.var_port.get(),
                "auto_jump": self.var_auto_jump.get(),
                "fast_start": self.var_fast_start.get(),
                "cookie_relay": self.var_cookie_relay.get(),
                "random_boost": self.var_random_boost.get(),
                "boost_index": idx,
                "auto_hearts": self.var_auto_hearts.get(),
                "hearts_interval": self.var_hearts_interval.get(),
                "max_hearts_send": self.var_max_hearts_send.get(),
                "max_rounds": self.var_max_rounds.get(),
                "min_delay": self.var_min_delay.get(),
                "max_delay": self.var_max_delay.get(),
                "bot_mode": self.var_bot_mode.get(),
            }
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            if hasattr(self, "_shared_options") and self._shared_options is not None:
                try:
                    self._shared_options.update(self._get_options())
                except Exception:
                    pass
        except Exception as e:
            print(f"⚠️ Error saving {filename}: {e}")

    # ── UI BUILD ──────────────────────────────────────────────────
    def _build_ui(self):
        # ── Body
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=8, pady=4)

        # Left panel (360px wide for controls)
        left = tk.Frame(body, bg=C["bg"], width=360)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        # Right panel (Compact Log)
        right = tk.Frame(body, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)

        self._build_left(left)
        self._build_right(right)


    def _build_left(self, p):
        self._card(p, "📱  Device Connection", self._device_content)
        # ── Options card
        self._card(p, "⚙️  Bot Options", self._options_content)
        # ── Buttons
        self._build_buttons(p)

    def _card(self, parent, title, content_fn):
        frame = tk.Frame(parent, bg=C["card"],
                         highlightthickness=1, highlightbackground=C["border"])
        frame.pack(fill="x", pady=(0, 5))
        # Title bar
        tbar = tk.Frame(frame, bg=C["card"])
        tbar.pack(fill="x")
        tk.Label(tbar, text=title, bg=C["card"], fg=C["text"],
                 font=font(9, bold=True), anchor="w",
                 padx=8, pady=3).pack(fill="x")
        tk.Frame(frame, bg=C["border"], height=1).pack(fill="x")
        # Content
        inner = tk.Frame(frame, bg=C["card"], padx=8, pady=4)
        inner.pack(fill="x")
        content_fn(inner)

    def _device_content(self, p):
        # IP Row
        r_ip = tk.Frame(p, bg=C["card"])
        r_ip.pack(fill="x", pady=2)
        tk.Label(r_ip, text="IP Address", bg=C["card"], fg=C["muted"], font=font(9), width=10, anchor="w").pack(side="left")
        
        self._status_badge = StatusBadge(r_ip)
        self._status_badge.pack(side="right")
        
        tk.Entry(r_ip, textvariable=self.var_ip, width=16, bg=C["panel"], fg=C["text"], insertbackground=C["text"], relief="flat", bd=4, font=font(10), highlightthickness=1, highlightbackground=C["border"], highlightcolor=C["accent2"]).pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Port Row
        r_port = tk.Frame(p, bg=C["card"])
        r_port.pack(fill="x", pady=2)
        tk.Label(r_port, text="LDPlayer Port", bg=C["card"], fg=C["muted"], font=font(9), width=10, anchor="w").pack(side="left")
        
        self._port_combo = ttk.Combobox(r_port, textvariable=self.var_port, values=["5555", "5557", "5559", "5561", "5563", "5565"], width=8, state="readonly", font=font(10))
        self._port_combo.pack(side="left")
        
        

    def _mode_content(self, p):
        self._rb_modes = {}
        modes = [
            ("run", "🏃 Auto Run Mode"),
            ("gift", "🎁 Auto Gift Draw Mode"),
            ("hearts", "💖 Send Hearts (Leaderboard)"),
            ("quick_hearts", "📩 Quick Receive Lives (Mail)")
        ]
        for val, text in modes:
            rb = tk.Radiobutton(p, text=text, variable=self.var_bot_mode,
                           value=val, bg=C["card"], fg=C["text"], selectcolor=C["card"],
                           font=font(10), activebackground=C["card"], activeforeground=C["text"],
                           command=self._on_mode_change)
            rb.pack(anchor="w", pady=2)
            self._rb_modes[val] = rb
        self.after(50, self._on_mode_change)

    def _options_content(self, p):
        self._opt_widgets = []
        self._opt_labels = []
        top_opts = [
            ("🦘  Auto Jump",            self.var_auto_jump),
            ("⚡  Fast Start",            self.var_fast_start),
            ("🍪  Cookie Relay",          self.var_cookie_relay),
        ]
        for label, var in top_opts:
            row = tk.Frame(p, bg=C["card"])
            row.pack(fill="x", pady=2)
            lbl = tk.Label(row, text=label, bg=C["card"], fg=C["text"], font=font(9), anchor="w")
            lbl.pack(side="left", fill="x", expand=True)
            t = Toggle(row, var)
            t.pack(side="right")
            self._opt_labels.append(lbl)
            self._opt_widgets.append(t)

        # ── Auto Hearts Section (Toggle + Interval Entry attached together)
        sep1 = tk.Frame(p, bg=C["border"], height=1)
        sep1.pack(fill="x", pady=(5, 3))

        h_row = tk.Frame(p, bg=C["card"])
        h_row.pack(fill="x", pady=2)
        lbl_h = tk.Label(h_row, text="💌  Auto Hearts Timer", bg=C["card"], fg=C["text"], font=font(9), anchor="w")
        lbl_h.pack(side="left", fill="x", expand=True)
        t_h = Toggle(h_row, self.var_auto_hearts)
        t_h.pack(side="right")
        self._opt_labels.append(lbl_h)
        self._opt_widgets.append(t_h)

        r_hi = tk.Frame(p, bg=C["card"])
        r_hi.pack(fill="x", pady=2)
        self._lbl_hi = tk.Label(r_hi, text="⏱️ Hearts Interval (min):", bg=C["card"], fg=C["muted"], font=font(8), anchor="w")
        self._lbl_hi.pack(side="left")
        self._e_hi = tk.Entry(r_hi, textvariable=self.var_hearts_interval, width=6, bg=C["panel"], fg=C["text"],
                              insertbackground=C["text"], relief="flat", bd=3, font=font(9, bold=True), justify="center")
        self._e_hi.pack(side="right")

        r_mh = tk.Frame(p, bg=C["card"])
        r_mh.pack(fill="x", pady=2)
        self._lbl_mh = tk.Label(r_mh, text="🎯 Max Hearts (0=All):", bg=C["card"], fg=C["muted"], font=font(8), anchor="w")
        self._lbl_mh.pack(side="left")
        self._e_mh = tk.Entry(r_mh, textvariable=self.var_max_hearts_send, width=6, bg=C["panel"], fg=C["text"],
                              insertbackground=C["text"], relief="flat", bd=3, font=font(9, bold=True), justify="center")
        self._e_mh.pack(side="right")
        self.var_auto_hearts.trace_add("write", self._on_hearts_toggle)
        self._on_hearts_toggle()

        # ── Random Boost Section (Toggle + Dropdown attached together)
        sep2 = tk.Frame(p, bg=C["border"], height=1)
        sep2.pack(fill="x", pady=(5, 3))

        rb_row = tk.Frame(p, bg=C["card"])
        rb_row.pack(fill="x", pady=2)
        lbl_rb = tk.Label(rb_row, text="🎲  Desired Random Boost", bg=C["card"], fg=C["text"], font=font(9), anchor="w")
        lbl_rb.pack(side="left", fill="x", expand=True)
        t_rb = Toggle(rb_row, self.var_random_boost)
        t_rb.pack(side="right")
        self._opt_labels.append(lbl_rb)
        self._opt_widgets.append(t_rb)

        tk.Label(p, text="Select boost (must match in-game setting):",
                 bg=C["card"], fg=C["muted"], font=font(8), anchor="w").pack(fill="x", pady=(2, 0))

        boost_names = [f"{i+1:2}. {name}" for i, (name, _) in enumerate(BOOST_CHOICES)]
        self._boost_var = tk.StringVar(value=boost_names[0])
        self._boost_combo = ttk.Combobox(p, textvariable=self._boost_var,
                                          values=boost_names, state="disabled",
                                          font=font(9))
        self._boost_combo.pack(fill="x", pady=(2, 4))
        self._boost_combo.current(0)
        self.var_random_boost.trace_add("write", self._on_boost_toggle)

        # ── Advanced Run Settings (Max Rounds & Rest Delay)
        sep3 = tk.Frame(p, bg=C["border"], height=1)
        sep3.pack(fill="x", pady=(4, 3))

        # Max Rounds
        r_mr = tk.Frame(p, bg=C["card"])
        r_mr.pack(fill="x", pady=2)
        tk.Label(r_mr, text="🔢 Max Rounds (0=∞):", bg=C["card"], fg=C["muted"], font=font(8), anchor="w").pack(side="left")
        e_mr = tk.Entry(r_mr, textvariable=self.var_max_rounds, width=6, bg=C["panel"], fg=C["text"],
                        insertbackground=C["text"], relief="flat", bd=3, font=font(9, bold=True), justify="center")
        e_mr.pack(side="right")

        # Rest Delay (Min - Max sec)
        r_rd = tk.Frame(p, bg=C["card"])
        r_rd.pack(fill="x", pady=2)
        tk.Label(r_rd, text="⏱️ Rest Delay (sec):", bg=C["card"], fg=C["muted"], font=font(8), anchor="w").pack(side="left")
        e_max = tk.Entry(r_rd, textvariable=self.var_max_delay, width=4, bg=C["panel"], fg=C["text"],
                         insertbackground=C["text"], relief="flat", bd=3, font=font(9), justify="center")
        e_max.pack(side="right")
        tk.Label(r_rd, text="~", bg=C["card"], fg=C["muted"], font=font(9)).pack(side="right", padx=2)
        e_min = tk.Entry(r_rd, textvariable=self.var_min_delay, width=4, bg=C["panel"], fg=C["text"],
                         insertbackground=C["text"], relief="flat", bd=3, font=font(9), justify="center")
        e_min.pack(side="right")

    def _stats_content(self, p):
        self._stat_labels = {}
        items = [
            ("games",      "🎮 Games Played",    "0"),
            ("coin_last",  "💰 Last Round",       "0"),
            ("uptime",     "⏱️ Uptime",           "00:00:00"),
            ("coin_total", "🪙 Total Coins",      "0"),
            ("stage",      "📍 Current Stage",    "—"),
            ("boxes",      "📦 Mystery Boxes",    "0"),
            ("group",      "🗂️ Detection Group",  "—"),
            ("gifts",      "🎁 Gifts Opened",     "0"),
        ]

        grid = tk.Frame(p, bg=C["card"])
        grid.pack(fill="x")

        for idx, (key, label, default) in enumerate(items):
            r, c = divmod(idx, 2)
            cell = tk.Frame(grid, bg=C["card"], padx=6, pady=2)
            cell.grid(row=r, column=c, sticky="ew")

            tk.Label(cell, text=label, bg=C["card"], fg=C["muted"],
                     font=font(8), anchor="w").pack(side="left", fill="x", expand=True)
            lbl = tk.Label(cell, text=default, bg=C["card"], fg=C["text"],
                           font=font(9, bold=True), anchor="e")
            lbl.pack(side="right")
            self._stat_labels[key] = lbl

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

    def _build_buttons(self, p):
        row = tk.Frame(p, bg=C["bg"])
        row.pack(fill="x", pady=6, padx=4)
        self._start_btn = ttk.Button(row, text="▶  Start Bot", style="Start.TButton",
                                      command=self._start_bot)
        self._start_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self._stop_btn = ttk.Button(row, text="⏹  Stop Bot", style="Stop.TButton",
                                     command=self._stop_bot, state="disabled")
        self._stop_btn.pack(side="left", fill="x", expand=True)

    def _build_right(self, p):
        # ── Top Right: Bot Mode
        self._card(p, "🎮  Bot Mode", self._mode_content)

        # ── Dashboard / Session Stats Card
        self._card(p, "📊  Session Dashboard", self._stats_content)

        # ── Bottom Right: Activity Log
        log_card = tk.Frame(p, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        log_card.pack(fill="both", expand=True, pady=(4, 0))

        hdr = tk.Frame(log_card, bg=C["card"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="📋  Activity Log", bg=C["card"], fg=C["text"],
                 font=font(9, bold=True), padx=10, pady=6).pack(side="left")
        ttk.Button(hdr, text="🗑  Clear", style="Ghost.TButton",
                    command=self._clear_log).pack(side="right", padx=8, pady=4)
        tk.Frame(log_card, bg=C["border"], height=1).pack(fill="x")

        log_wrap = tk.Frame(log_card, bg=C["log_bg"])
        log_wrap.pack(fill="both", expand=True, padx=4, pady=4)

        self._log = tk.Text(log_wrap, bg=C["log_bg"], fg=C["text"], height=8,
                             font=tkFont.Font(family="Consolas", size=9),
                             wrap="word", state="disabled", bd=0, relief="flat",
                             padx=8, pady=6, insertbackground=C["text"],
                             selectbackground=C["accent"])
        scroll = ttk.Scrollbar(log_wrap, orient="vertical", command=self._log.yview)
        self._log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self._log.pack(side="left", fill="both", expand=True)

        self._log.tag_config("ts",     foreground=C["log_ts"])
        self._log.tag_config("ok",     foreground=C["log_ok"])
        self._log.tag_config("err",    foreground=C["log_err"])
        self._log.tag_config("warn",   foreground=C["log_warn"])
        self._log.tag_config("info",   foreground=C["log_info"])
        self._log.tag_config("normal", foreground=C["text"])

    # ── Log helpers ───────────────────────────────────────────────
    def _log_write(self, msg: str, add_time=True):
        if add_time:
            pass # handled above
        self._log.configure(state="normal")
        ts = ""
        if msg.startswith("[") and "]" in msg:
            idx = msg.index("]") + 1
            ts, msg = msg[:idx], msg[idx:].strip()
            self._log.insert("end", ts + " ", "ts")

        if any(k in msg for k in ["✅", "started", "stable", "passed", "connected", "🦘"]):
            tag = "ok"
        elif any(k in msg for k in ["❌", "error", "Error", "Failed", "failed", "crash"]):
            tag = "err"
        elif any(k in msg for k in ["⚠️", "Waiting", "warn", "Warning"]):
            tag = "warn"
        elif any(k in msg for k in ["🔌", "📱", "🚀", "Detected", "Stage", "💌", "🔄"]):
            tag = "info"
        else:
            tag = "normal"

        self._log.insert("end", msg + "\n", tag)

        # ── Capping Log Buffer to max 500 lines to prevent RAM memory leaks during 24/7 continuous operation!
        try:
            line_count = int(self._log.index("end-1c").split(".")[0])
            if line_count > 500:
                self._log.delete("1.0", f"{line_count - 500 + 1}.0")
        except Exception:
            pass

        self._log.see("end")
        self._log.configure(state="disabled")

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def _poll_logs(self):
        while True:
            try:
                msg = self._log_q.get_nowait()
                self._log_write(msg, add_time=False)
            except queue.Empty:
                break
        while True:
            try:
                msg_type, key, val = self._stat_q.get_nowait()
                if msg_type == "stat":
                    self._update_stat(key, val)
                elif msg_type == "state":
                    self._bot_running = False
                    self._set_running(False)
                    if key == "error":
                        self._status_badge.set_state("error")
            except queue.Empty:
                break
        self.after(100, self._poll_logs)

    # ── Boost & Hearts toggles ────────────────────────────────────
    def _on_boost_toggle(self, *_):
        self._boost_combo.configure(
            state="readonly" if self.var_random_boost.get() and self.var_bot_mode.get() == "run" else "disabled"
        )

    def _on_hearts_toggle(self, *_):
        state = "normal" if self.var_auto_hearts.get() and self.var_bot_mode.get() == "run" else "disabled"
        if hasattr(self, "_e_hi"):
            self._e_hi.configure(state=state)
            if hasattr(self, "_lbl_hi"):
                self._lbl_hi.configure(fg=C["text"] if state == "normal" else C["muted"])
        if hasattr(self, "_e_mh"):
            self._e_mh.configure(state=state)
            if hasattr(self, "_lbl_mh"):
                self._lbl_mh.configure(fg=C["text"] if state == "normal" else C["muted"])

    def _on_mode_change(self, *_):
        mode = self.var_bot_mode.get()
        if hasattr(self, "_rb_modes"):
            for val, rb in self._rb_modes.items():
                if val == mode:
                    rb.configure(fg=C["accent"])
                else:
                    rb.configure(fg=C["text"])
        state = "normal" if mode == "run" else "disabled"
        for w in self._opt_widgets:
            if isinstance(w, Toggle):
                w.configure(state=state)
        for lbl in getattr(self, "_opt_labels", []):
            lbl.configure(fg=C["text"] if state == "normal" else C["muted"])
        self._on_boost_toggle()
        self._on_hearts_toggle()

    # ── Bot control ───────────────────────────────────────────────
    def _get_options(self):
        idx = self._boost_combo.current() if hasattr(self, "_boost_combo") else 0
        boost_names = [f"{i+1:2}. {name}" for i, (name, _) in enumerate(BOOST_CHOICES)]
        if idx < 0 or idx >= len(BOOST_CHOICES):
            val = self._boost_var.get() if hasattr(self, "_boost_var") else ""
            idx = boost_names.index(val) if val in boost_names else 0

        use = self.var_random_boost.get()

        try: max_r = max(0, int(self.var_max_rounds.get().strip()))
        except ValueError: max_r = 0

        try: min_d = max(1, int(self.var_min_delay.get().strip()))
        except ValueError: min_d = 30

        try: max_d = max(min_d, int(self.var_max_delay.get().strip()))
        except ValueError: max_d = max(min_d, 60)

        try: hearts_int = max(1, int(self.var_hearts_interval.get().strip()))
        except ValueError: hearts_int = 30
        try: max_hearts = max(0, int(self.var_max_hearts_send.get().strip()))
        except: max_hearts = 0

        return {
            "use_auto_jump":            self.var_auto_jump.get(),
            "use_fast_start":           self.var_fast_start.get(),
            "use_cookie_relay":         self.var_cookie_relay.get(),
            "use_desired_random_boost": use,
            "desired_boost_template":   BOOST_CHOICES[idx][1] if use else None,
            "desired_boost_name":       BOOST_CHOICES[idx][0] if use else None,
            "use_auto_hearts":          self.var_auto_hearts.get(),
            "hearts_interval":          hearts_int,
            "max_hearts_send":          max_hearts,
            "max_rounds":               max_r,
            "min_delay":                min_d,
            "max_delay":                max_d,
        }

    def _start_bot(self):
        if self._bot_running:
            return
        ip   = self.var_ip.get().strip()
        port = self.var_port.get().strip()
        if not ip or not port.isdigit():
            self._log_write("❌ Invalid IP or Port.")
            return
        self._stop_event.clear()
        import config
        config.DEVICE_IP = ip
        config.DEVICE_PORT = int(port)
        mode = self.var_bot_mode.get()

        if not hasattr(self, "_manager") or self._manager is None:
            self._manager = multiprocessing.Manager()
        self._shared_options = self._manager.dict(self._get_options())

        self._bot_running = True
        self._set_running(True)
        self._bot_process = Process(
            target=bot_process_runner, args=(mode, ip, int(port), self._shared_options, self._log_q, self._stat_q, self._stop_event), daemon=True)
        self._bot_process.start()
        self._tick_uptime()

    def _stop_bot(self):
        self._stop_event.set()
        if hasattr(self, "_bot_process") and self._bot_process and self._bot_process.is_alive():
            self._bot_process.terminate()
            self._bot_process.join(timeout=1)
            self._log_write("🛑 Bot process terminated immediately.")
        else:
            self._log_write("🛑 Stop requested...")
        
        if getattr(self, "_bot_running", False):
            self._bot_running = False
            self._set_running(False)

    def _set_running(self, running: bool):
        if running:
            self._status_badge.set_state("running")
            self._start_btn.configure(state="disabled")
            self._stop_btn.configure(state="normal")
            self._uptime_start = time.time()
        else:
            self._status_badge.set_state("idle")
            self._start_btn.configure(state="normal")
            self._stop_btn.configure(state="disabled")
            self._on_mode_change()  # Restore option states based on mode
            self._stat_labels["stage"].configure(text="—")
            self._stat_labels["group"].configure(text="—")
            self._stat_labels["uptime"].configure(text="00:00:00")

    def _tick_uptime(self):
        if not self._bot_running:
            return
        e = int(time.time() - self._uptime_start)
        self._stat_labels["uptime"].configure(
            text=f"{e//3600:02d}:{(e%3600)//60:02d}:{e%60:02d}")
        self.after(1000, self._tick_uptime)

    def _update_stat(self, key, val):
        if key in self._stat_labels:
            self._stat_labels[key].configure(text=val)

    # ── Bot loop ──────────────────────────────────────────────────
    def _on_close(self):
        self._save_user_settings()
        self._stop_event.set()
        if self._bot_process and self._bot_process.is_alive():
            self._bot_process.terminate()



class BotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🍪 CookiePilot v1.0.0")
        self.configure(bg=C["bg"])
        self.geometry("850x700")
        self.minsize(850, 700)
        make_styles()
        
        # ── App Title Header
        app_hdr = tk.Frame(self, bg=C["panel"], height=48)
        app_hdr.pack(fill="x")
        app_hdr.pack_propagate(False)
        tk.Label(app_hdr, text="🍪", font=font(20), bg=C["panel"], fg=C["accent"]).pack(side="left", padx=(14, 4), pady=4)
        tk.Label(app_hdr, text="CookiePilot v1.0.0", font=font(14, bold=True), bg=C["panel"], fg=C["text"]).pack(side="left", pady=4)
        tk.Frame(self, bg=C["accent"], height=2).pack(fill="x")
        
        tb = tk.Frame(self, bg=C["panel"])
        tb.pack(fill="x", pady=2)
        ttk.Button(tb, text="➕ เพิ่มบอทจอใหม่", style="Ghost.TButton", command=self.add_tab).pack(side="left", padx=10)
        ttk.Button(tb, text="❌ ปิดจอปัจจุบัน", style="Ghost.TButton", command=self.close_current_tab).pack(side="left", padx=10)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=4, pady=4)
        
        self.tabs = []
        self.add_tab("5555")
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
    def add_tab(self, port=None):
        if port is None:
            ports = ["5555", "5557", "5559", "5561", "5563", "5565"]
            port = ports[len(self.tabs) % len(ports)]
        tab = BotTab(self.notebook, port=port)
        self.tabs.append(tab)
        # Default name when opening tab, wait for load_settings to rename it properly
        self.notebook.add(tab, text=f" LDPlayer {len(self.tabs)} ")
        self.notebook.select(tab)

    def close_current_tab(self):
        current_tab_id = self.notebook.select()
        if not current_tab_id: return
        tab = self.notebook.nametowidget(current_tab_id)
        tab._on_close()
        self.notebook.forget(current_tab_id)
        if tab in self.tabs:
            self.tabs.remove(tab)
        tab.destroy()

    def _on_close(self):
        for tab in self.tabs:
            tab._on_close()
        self.destroy()

if __name__ == "__main__":
    app = BotApp()
    app.mainloop()
