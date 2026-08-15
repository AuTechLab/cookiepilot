import config
import random
import threading
import time

from adb import device_capture_screen, device_connect, device_reset_app, device_tap, safe_device_tap, remember_game_package
from coin_reader import read_coins
from actions import (
    accept_congratulations,
    accept_daily_checkin,
    accept_daily_checkin_boost_set,
    accept_daily_new,
    accept_daily_treasure,
    accept_enter_league,
    accept_league_results,
    accept_level_up,
    accept_mystery_box,
    accept_overtake_break_score,
    accept_previous_rank_results,
    accept_relic_claim,
    accept_too_many_treasures,
    close_announcement_dialog,
    complete_finish,
    draw_gifts_loop,
    handle_anti_bot,
    handle_connection_lost,
    handle_inactive,
    handle_quick_receive_and_send_lives,
    handle_send_friend_life,
    open_relic_complete,
    play_game,
    purchase_cookie_relay,
    purchase_desired_random_boost,
    purchase_fast_start,
    start_game,
    using_cookie_relay,
    using_fast_start,
)
from config import (
    BOOST_17P_BASE_SPEED_TEMPLATE,
    BOOST_15P_SCORE_BONUS_TEMPLATE,
    BOOST_20P_HP_FROM_POTIONS_TEMPLATE,
    BOOST_2PIT_LIFTS_TEMPLATE,
    BOOST_70P_CRUSH_CHANCE_TEMPLATE,
    BOOST_DOUBLE_COINS_TEMPLATE,
    BOOST_GOLD_COIN_MAGIC_TEMPLATE,
    BOOST_M15P_HP_DRAIN_TEMPLATE,
    BOOST_M30P_COLLISION_DAMAGE_TEMPLATE,
    BOOST_MAGNETIC_AURA_TEMPLATE,
    BOOST_REVIVE_ONCE_WITH_80HP_TEMPLATE,
    DETECTION_ALWAYS_STAGES,
    DETECTION_GROUPS,
    DETECTION_RECOVERY_SCAN_INTERVAL,
    JUMP_BUTTON,
)
from detection import detect_stage, load_templates
from debug import save_debug_screen

# -------------------
# BOT OPTIONS
# -------------------
BOOST_CHOICES = [
    ("Double Coins",            BOOST_DOUBLE_COINS_TEMPLATE),
    ("+15% Score Bonus",        BOOST_15P_SCORE_BONUS_TEMPLATE),
    ("-15% HP Drain",           BOOST_M15P_HP_DRAIN_TEMPLATE),
    ("Revive Once with 80 HP",  BOOST_REVIVE_ONCE_WITH_80HP_TEMPLATE),
    ("70% Crush Chance",        BOOST_70P_CRUSH_CHANCE_TEMPLATE),
    ("+17% Base Speed",         BOOST_17P_BASE_SPEED_TEMPLATE),
    ("Gold Coin Magic",         BOOST_GOLD_COIN_MAGIC_TEMPLATE),
    ("-30% Collision Damage",   BOOST_M30P_COLLISION_DAMAGE_TEMPLATE),
    ("+20% HP from Potions",    BOOST_20P_HP_FROM_POTIONS_TEMPLATE),
    ("Magnetic Aura",           BOOST_MAGNETIC_AURA_TEMPLATE),
    ("2 Pit Lifts",             BOOST_2PIT_LIFTS_TEMPLATE),
]


class AutoJumper:
    """Background thread that taps the screen during gameplay to make the cookie jump."""

    def __init__(self):
        self._active = threading.Event()
        self._thread = None

    def is_active(self):
        return self._active.is_set()

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._active.set()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            print("🦘 Auto-jump started!")

    def stop(self):
        if self._active.is_set():
            self._active.clear()
            print("🦘 Auto-jump stopped.")

    def _loop(self):
        while self._active.is_set():
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, JUMP_BUTTON[0], JUMP_BUTTON[1])
            time.sleep(random.uniform(0.3, 1.2))


def get_detection_stage_names(group_name):
    stage_names = []
    # For non-in-game groups, always stages have higher priority
    if group_name != "IN_GAME":
        for stage_name in DETECTION_ALWAYS_STAGES:
            if stage_name not in stage_names:
                stage_names.append(stage_name)
    # Add stages from the specified detection group
    for stage_name in DETECTION_GROUPS[group_name]:
        if stage_name not in stage_names:
            stage_names.append(stage_name)
    # For in-game, always stages are appended last (original behavior)
    if group_name == "IN_GAME":
        for stage_name in DETECTION_ALWAYS_STAGES:
            if stage_name not in stage_names:
                stage_names.append(stage_name)
    return stage_names


def prompt_user_options():
    desired_boost_template = None

    print("⚙️ --- Bot Options ---")
    use_auto_jump = input("🦸 Auto Jump during gameplay? [Y/n]: ").strip().lower() != "n"
    use_fast_start = input("⚡ Use Fast Start (buy + use)? [y/n]: ").strip().lower() == "y"
    use_cookie_relay = input("🍪 Use Cookie Relay (buy + use)? [y/n]: ").strip().lower() == "y"
    use_desired_random_boost = input("🎲 Use Desired Random Boost (buy + use)? [y/n]: ").strip().lower() == "y"
    if use_desired_random_boost:
        print("  Select desired boost (must match the boost option configured in-game):")
        for i, (name, _) in enumerate(BOOST_CHOICES, 1):
            print(f"  {i:2}. {name}")
        while True:
            choice = input("  Enter number: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(BOOST_CHOICES):
                desired_boost_template = BOOST_CHOICES[int(choice) - 1][1]
                desired_boost_name = BOOST_CHOICES[int(choice) - 1][0]
                print(f"  ✅ Selected: {desired_boost_name}")
                break
            print(f"  ⚠️ Please enter a number between 1 and {len(BOOST_CHOICES)}.")
    print("---------------------")

    return {
        "use_auto_jump": use_auto_jump,
        "use_fast_start": use_fast_start,
        "use_cookie_relay": use_cookie_relay,
        "use_desired_random_boost": use_desired_random_boost,
        "desired_boost_template": desired_boost_template,
        "desired_boost_name": desired_boost_name if use_desired_random_boost else None,
    }


# -------------------
# MAIN LOOP
# -------------------
def main():
    try:
        print("🚀 CookiePilot Started")
        print("⚠️ Screen must be 1280x720 resolution for the bot to work properly.")
        print(f"📱 Connecting to device at {config.DEVICE_IP}:{config.DEVICE_PORT}...")

        device_connect(config.DEVICE_IP, config.DEVICE_PORT)
        load_templates()

        # * for debugging *
        # device_screen = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
        # save_debug_screen(device_screen)

        print("⚙️ --- Bot Mode ---")
        print("1) 🏃 Auto Run Mode (โหมดวิ่งปกติ)")
        print("2) 🎁 Auto Gift Draw Mode (โหมดสุ่มของขวัญ)")
        mode_choice = input("Select Mode [1/2]: ").strip()
        bot_mode = "gift" if mode_choice == "2" else "run"

        if bot_mode == "gift":
            print("🎁 เริ่มโหมดสุ่มของขวัญอัตโนมัติ...")
            _never_stop = threading.Event()
            draw_gifts_loop(_never_stop)
            print("🛑 จบการสุ่มของขวัญ")
            return

        options = prompt_user_options()
        auto_jumper = AutoJumper() if options["use_auto_jump"] else None

        last_stage = None
        is_first_game = True
        detection_group = "PRE_GAME"
        last_detected_time = time.time()

        def get_lives_interval():
            base_min = options.get("hearts_interval", 30)
            base_sec = base_min * 60
            return random.uniform(base_sec * 0.8, base_sec * 1.2)

        lives_interval = get_lives_interval()
        last_lives_time = time.time()
        stop_event = threading.Event()

        coin_total = 0
        coin_rounds = 0
        conn_lost_streak = 0

        while True:
            device_screen = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
            stage = detect_stage(device_screen, get_detection_stage_names(detection_group))
            if stage is None:
                if time.time() - last_detected_time >= DETECTION_RECOVERY_SCAN_INTERVAL[detection_group]:
                    stage = detect_stage(device_screen)
                    last_detected_time = time.time()
            else:
                last_detected_time = time.time()

            # Remember running game package dynamically when verified stage is detected
            if stage in ("MAINMENU", "PURCHASE_ITEM", "GAME_START", "GAME_RELAY", "GAME_COMPLETE", "MYSTERY_BOX"):
                remember_game_package(config.DEVICE_IP, config.DEVICE_PORT)
                conn_lost_streak = 0

            if stage == last_stage:
                time.sleep(0.1)
                continue

            last_stage = stage

            if stage == "MAINMENU":
                print("🎮 Detected Stage: MAINMENU")
                # Wait screen refresh
                print("⏳ Waiting 5 seconds for screen refresh...")
                time.sleep(5)
                lives_elapsed = time.time() - last_lives_time
                if options.get("use_auto_hearts", True) and lives_elapsed >= lives_interval:
                    print(f"💌 ~{options.get('hearts_interval', 30)} min passed ({lives_elapsed / 60:.1f} min) — receiving and sending lives...")
                    handle_quick_receive_and_send_lives(stop_event, max_hearts=options.get("max_hearts_send", 0))
                    last_lives_time = time.time()
                    lives_interval = get_lives_interval()
                    last_stage = None
                    continue
                if detection_group == "POST_GAME":
                    detection_group = "PRE_GAME"
                    last_stage = None
                    continue
                if not is_first_game:
                    delay = random.uniform(30, 60)
                    print(f"⏳ Waiting for {delay:.2f} seconds before starting the next game...")
                    time.sleep(delay)
                is_first_game = False
                start_game()
                detection_group = "PRE_GAME"
            elif stage == "PURCHASE_ITEM":
                print("🛒 Detected Stage: PURCHASE_ITEM")
                if options.get("use_fast_start"):
                    purchase_fast_start()
                if options.get("use_cookie_relay"):
                    purchase_cookie_relay()
                if options.get("use_desired_random_boost"):
                    purchase_desired_random_boost(options.get("desired_boost_template"), options.get("desired_boost_name"))
                play_game()
                detection_group = "IN_GAME"
                time.sleep(0.2)
                last_stage = None
            elif stage == "GAME_START":
                print("🏁 Detected Stage: GAME_START")
                if options.get("use_fast_start"):
                    using_fast_start()
                detection_group = "IN_GAME"
            elif stage == "GAME_RELAY":
                print("🔄 Detected Stage: GAME_RELAY")
                if options.get("use_cookie_relay"):
                    using_cookie_relay()
                detection_group = "IN_GAME"
            elif stage == "GAME_COMPLETE":
                print("✅ Detected Stage: GAME_COMPLETE")
                
                # ── Read coins from result screen
                coins = read_coins(device_screen)
                if coins is not None:
                    coin_total += coins
                    coin_rounds += 1
                    avg = int(coin_total / coin_rounds)
                    print(f"🪙 เหรียญรอบนี้: {coins:,}  (รวม {coin_total:,}, ค่าเฉลี่ย {avg:,}/รอบ)")
                else:
                    print("⚠️ ไม่สามารถอ่านตัวเลขเหรียญได้")

                complete_finish()
                detection_group = "POST_GAME"
            elif stage == "MYSTERY_BOX":
                print("🎁 Detected Stage: MYSTERY_BOX")
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
                accept_relic_claim()
                detection_group = "PRE_GAME"
            elif stage == "ANTI_BOT":
                print("⚠️ Detected Stage: ANTI_BOT")
                handle_anti_bot(device_screen)
                last_stage = None
            elif stage == "CONNECTION_LOST":
                conn_lost_streak += 1
                print(f"🔌 Detected Stage: CONNECTION_LOST (ครั้งที่ {conn_lost_streak}) -> กดเชื่อมใหม่ในเกม")
                handle_connection_lost()
                if conn_lost_streak >= 3:
                    print(f"⚠️ หลุดการเชื่อมต่อซ้ำ {conn_lost_streak} ครั้ง -> กำลังเปิดเกมใหม่ด้วยแพ็กเกจที่จำไว้...")
                    device_reset_app(config.DEVICE_IP, config.DEVICE_PORT)
                    time.sleep(5)
                    close_announcement_dialog()
                    conn_lost_streak = 0
                detection_group = "PRE_GAME"
                last_stage = None
            elif stage == "INACTIVE":
                print("💤 Detected Stage: INACTIVE")
                handle_inactive()
                last_stage = None
            # Auto-jump management
            if auto_jumper is not None:
                if detection_group == "IN_GAME" and not auto_jumper.is_active():
                    auto_jumper.start()
                elif detection_group != "IN_GAME" and auto_jumper.is_active():
                    auto_jumper.stop()
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("🛑 Bot stopped by user.")
    except Exception as e:
        print(f"❌ An error occurred: {e}")
