import config
import random
import time

from adb import safe_device_tap, safe_device_scroll, device_capture_screen
from config import (
    ACCEPT_ALL_LIVES_RECEIVED_AND_SENT_BUTTON,
    ACCEPT_CONGRATULATIONS_BUTTON,
    ACCEPT_DAILY_CHECKIN_BOOST_SET_BUTTON,
    ACCEPT_DAILY_CHECKIN_BUTTON,
    ACCEPT_DAILY_TREASURE_BUTTON,
    ACCEPT_DAILY_NEW_BUTTON,
    ACCEPT_ENTER_LEAGUE_BUTTON,
    ACCEPT_LEAGUE_RESULTS_BUTTON,
    ACCEPT_LEVEL_UP_BUTTON,
    ACCEPT_MYSTERY_BOX_BUTTON,
    ACCEPT_OVERTAKE_BREAK_SCORE_BUTTON,
    ACCEPT_PREVIOUS_RANK_RESULTS_BUTTON,
    ACCEPT_TOO_MANY_TREASURES_BUTTON,
    ALL_LIVES_RECEIVED_AND_SENT_REGION,
    ALL_LIVES_RECEIVED_AND_SENT_TEMPLATE,
    CLOSE_ANNOUNCEMENT_DIALOG_BUTTON,
    CLOSE_SEND_LIFE_DIALOG_BUTTON,
    COMPLETE_FINISH_BUTTON,
    CONFIRM_SEND_LIFE_BUTTON,
    CONFIRM_SEND_LIFE_REGION,
    CONFIRM_SEND_LIFE_TEMPLATE,
    COOKIE_RELAY_ITEM,
    COOKIE_RELAY_USE_BUTTON,
    EXIT_GAME_SETTINGS_BUTTON,
    EXIT_PARTY_RUN_MODE_BUTTON,
    FAST_START_ITEM,
    FAST_START_USE_BUTTON,
    FRIEND_BOTTOM_LEADERBOARD_REGION,
    FRIEND_BOTTOM_LEADERBOARD_TEMPLATE,
    FRIEND_SEND_LIFE_REGION,
    FRIEND_SEND_LIFE_TEMPLATE,
    FRIEND_TOP_LEADERBOARD_REGION,
    FRIEND_TOP_LEADERBOARD_TEMPLATE,
    INACTIVE_RELOAD_BUTTON,
    LEADERBOARD_BOTTOM_POSITION,
    LEADERBOARD_TOP_POSITION,
    MAIL_BOX_BUTTON,
    MAIL_BOX_LIVES_TAB_BUTTON,
    MAIL_BOX_CLOSE_BUTTON,
    MULTI_BUY_BUTTON,
    MULTI_PURCHASE_BUTTON,
    NO_LIVES_TO_RECEIVE_REGION,
    NO_LIVES_TO_RECEIVE_TEMPLATE,
    NO_LIVES_TO_RECEIVE_TEMPLATE,
    PLAY_BUTTON,
    PURCHASE_BUTTON,
    QUICK_RECEIVE_AND_SEND_LIVES_BUTTON,
    RANDOM_BOOST_ITEM,
    RANDOM_BOOST_REGION,
    RELIC_CLAIM_BUTTON,
    RELIC_CLOSE_BUTTON,
    RELIC_COMPLETE_BUTTON,
    START_BUTTON,
    CONNECTION_LOST_RELOAD_BUTTON,
)
from detection import detect_templates, detect_anti_bot_odd_cards, detect_stage
from config import (
    ANTI_BOT_CARD_POS_1, ANTI_BOT_CARD_POS_2, ANTI_BOT_CARD_POS_3,
    ANTI_BOT_CARD_POS_4, ANTI_BOT_CARD_POS_5, ANTI_BOT_CARD_POS_6,
    ANTI_BOT_CARD_WIDTH, ANTI_BOT_CARD_HEIGHT,
)
from config import (
    GIFT_DRAW_TITLE_TEMPLATE, GIFT_DRAW_TITLE_REGION,
    GIFT_PICK_TEMPLATE,       GIFT_PICK_REGION,
    GIFT_DRAW_THRESHOLD,      GIFT_DRAW_MAX,
    GIFT_ICON_BUTTON,  GIFT_DRAW_BUTTON, GIFT_BOX_BUTTON,
    GIFT_SKIP_BUTTON,  GIFT_AGAIN_BUTTON,
    GIFT_CONFIRM_BUTTON, GIFT_PET_BUTTON,
    GIFT_CLOSE_BUTTON, GIFT_ESC_BUTTON,
)

def start_game():
    print("🏁 Starting the game...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, START_BUTTON[0], START_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


def play_game():
    print("🎮 Playing the game...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, PLAY_BUTTON[0], PLAY_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


def purchase_fast_start():
    print("🛒 Purchasing Fast Start...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, FAST_START_ITEM[0], FAST_START_ITEM[1])
    time.sleep(random.uniform(0.8, 1.4))
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, PURCHASE_BUTTON[0], PURCHASE_BUTTON[1])
    time.sleep(random.uniform(1, 2))


def purchase_cookie_relay():
    print("🛒 Purchasing Cookie Relay...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, COOKIE_RELAY_ITEM[0], COOKIE_RELAY_ITEM[1])
    time.sleep(random.uniform(0.8, 1.4))
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, PURCHASE_BUTTON[0], PURCHASE_BUTTON[1])
    time.sleep(random.uniform(1, 2))


def purchase_random_boost():
    print("🛒 Purchasing Random Boost...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, RANDOM_BOOST_ITEM[0], RANDOM_BOOST_ITEM[1])
    time.sleep(random.uniform(0.8, 1.4))
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, PURCHASE_BUTTON[0], PURCHASE_BUTTON[1])
    time.sleep(random.uniform(1, 2))


def _boost_checked_green(screen, pos, sample_size=36):
    """Check if a boost checkbox in the Multi-Buy dialog is green (checked)."""
    import cv2
    import numpy as np
    if screen is None:
        return False
    cx, cy = pos
    half = sample_size // 2
    x1 = max(0, cx - half)
    y1 = max(0, cy - half)
    x2 = min(screen.shape[1], cx + half)
    y2 = min(screen.shape[0], cy + half)
    roi = screen[y1:y2, x1:x2]
    if roi.size == 0:
        return False
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([35, 90, 90]), np.array([75, 255, 255]))
    green_ratio = float(mask.mean()) / 255.0
    return green_ratio > 0.09


def purchase_desired_random_boost(desired_template, desired_name):
    """Purchase desired random boost by selecting its checkbox on the in-game Multi-Buy popup dialog (reverse-engineered from CookieGame_Multi)."""
    from bot import BOOST_CHOICES

    # 1. Determine target boost index (0..10)
    target_idx = 0
    if desired_name or desired_template:
        for idx, (b_name, b_template) in enumerate(BOOST_CHOICES):
            if (desired_name and b_name == desired_name) or (desired_template and b_template == desired_template):
                target_idx = idx
                break

    target_info = config.MULTI_BOOST_CHECKBOXES[target_idx]
    print(f"🛒 Purchasing Desired Random Boost: {target_info['name']}...")

    # 2. Tap Random Boost item box
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, RANDOM_BOOST_ITEM[0], RANDOM_BOOST_ITEM[1])
    time.sleep(random.uniform(0.8, 1.2))

    # 3. Tap Multi-Buy popup dialog inside game
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, MULTI_PURCHASE_BUTTON[0], MULTI_PURCHASE_BUTTON[1])
    time.sleep(random.uniform(1.0, 1.5))

    # 4. Read checkboxes state and toggle to match target_idx
    screen = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
    for b in config.MULTI_BOOST_CHECKBOXES:
        idx = b["index"]
        want = (idx == target_idx)
        checked = _boost_checked_green(screen, b["pos"])
        if checked != want:
            act_str = "ติ๊กเลือก" if want else "ปลดออก"
            print(f"   [{b['name']}] → {act_str}")
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, b["pos"][0], b["pos"][1])
            time.sleep(random.uniform(0.3, 0.5))

    # 5. Tap Multi Buy button to start automatic in-game rolling
    print(f"🎲 [Multi-Buy] เริ่มสุ่มซื้อบูสต์อัตโนมัติ จนกว่าจะได้: {target_info['name']}")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, MULTI_BUY_BUTTON[0], MULTI_BUY_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.2))

    # 6. Wait for rolling animation to finish (stop button appears and then disappears, or detected template)
    timeout = 40.0
    start_time = time.time()
    saw_rolling = False

    while time.time() - start_time < timeout:
        time.sleep(0.5)
        scr = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
        if scr is None:
            continue

        # Check if rolling stop button is visible
        is_stop_visible = len(detect_templates(scr, config.STAGE_MULTIBUY_STOP_TEMPLATE, threshold=0.8)) > 0
        if is_stop_visible:
            saw_rolling = True
            continue

        if saw_rolling:
            print(f"✅ [Multi-Buy] สุ่มบูสต์เสร็จสิ้น → ได้รับ {target_info['name']} เรียบร้อย!")
            break

        # Backup template check if screen returned to pre-game
        if desired_template and detect_templates(scr, desired_template, RANDOM_BOOST_REGION):
            print(f"✅ [Multi-Buy] ตรวจพบบูสต์ {target_info['name']} บนหน้าจอแล้ว!")
            break

    time.sleep(random.uniform(0.5, 1.0))


def using_fast_start():
    print("⚡ Using Fast Start...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, FAST_START_USE_BUTTON[0], FAST_START_USE_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.2))


def using_cookie_relay():
    print("🍪 Using Cookie Relay...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, COOKIE_RELAY_USE_BUTTON[0], COOKIE_RELAY_USE_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.2))


def complete_finish():
    print("🏆 Completing the game...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, COMPLETE_FINISH_BUTTON[0], COMPLETE_FINISH_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


def accept_mystery_box():
    print("🎁 Accepting Mystery Box...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, ACCEPT_MYSTERY_BOX_BUTTON[0], ACCEPT_MYSTERY_BOX_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


def accept_congratulations():
    print("🎉 Accepting Congratulations...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, ACCEPT_CONGRATULATIONS_BUTTON[0], ACCEPT_CONGRATULATIONS_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


def accept_level_up():
    print("⬆️ Accepting Level Up...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, ACCEPT_LEVEL_UP_BUTTON[0], ACCEPT_LEVEL_UP_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


def accept_daily_checkin():
    print("📅 Accepting Daily Check-in...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, ACCEPT_DAILY_CHECKIN_BUTTON[0], ACCEPT_DAILY_CHECKIN_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


def accept_daily_checkin_boost_set():
    print("📅 Accepting Daily Check-in Boost Set...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, ACCEPT_DAILY_CHECKIN_BOOST_SET_BUTTON[0], ACCEPT_DAILY_CHECKIN_BOOST_SET_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


def accept_daily_treasure():
    print("💎 Accepting Daily Treasure...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, ACCEPT_DAILY_TREASURE_BUTTON[0], ACCEPT_DAILY_TREASURE_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


def accept_daily_new():
    print("📰 Accepting Daily New...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, ACCEPT_DAILY_NEW_BUTTON[0], ACCEPT_DAILY_NEW_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


def accept_enter_league():
    print("🏆 Accepting Enter League...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, ACCEPT_ENTER_LEAGUE_BUTTON[0], ACCEPT_ENTER_LEAGUE_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


def accept_league_results():
    print("🏆 Accepting League Results...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, ACCEPT_LEAGUE_RESULTS_BUTTON[0], ACCEPT_LEAGUE_RESULTS_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


def accept_previous_rank_results():
    print("🏆 Accepting Previous Rank Results...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, ACCEPT_PREVIOUS_RANK_RESULTS_BUTTON[0], ACCEPT_PREVIOUS_RANK_RESULTS_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))

def accept_too_many_treasures():
    print("💎 Accepting Too Many Treasures...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, ACCEPT_TOO_MANY_TREASURES_BUTTON[0], ACCEPT_TOO_MANY_TREASURES_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))

def accept_overtake_break_score():
    print("🏆 Accepting Overtake Break Score...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, ACCEPT_OVERTAKE_BREAK_SCORE_BUTTON[0], ACCEPT_OVERTAKE_BREAK_SCORE_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))

def open_relic_complete():
    print("🏺 [Relic] เจอป้าย Get!/โบราณวัตถุครบ -> เข้าไปรับรางวัล...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, RELIC_COMPLETE_BUTTON[0], RELIC_COMPLETE_BUTTON[1])
    time.sleep(random.uniform(1.8, 2.5))
    accept_relic_claim()


def accept_relic_claim(stop_event=None):
    print("🏺 [Relic] กำลังเปิดกล่องสมบัติ/รับรางวัล Relic...")
    taps = 0
    misses = 0
    max_taps = 8

    for _ in range(max_taps * 2):
        if stop_event and stop_event.is_set():
            break
        screen = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
        if screen is None:
            time.sleep(0.5)
            continue

        if _green_ratio(screen, RELIC_CLAIM_BUTTON):
            taps += 1
            misses = 0
            print(f"   👆 กดปุ่มเปิดรางวัล Relic (ครั้งที่ {taps}/{max_taps})...")
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, RELIC_CLAIM_BUTTON[0], RELIC_CLAIM_BUTTON[1])
            if taps >= max_taps:
                print("   ✅ กดเปิดรางวัลครบจำนวนสูงสุดแล้ว")
                break
            time.sleep(random.uniform(1.0, 1.6))
        else:
            misses += 1
            if (taps == 0 and misses >= 3) or misses >= 4:
                break
            time.sleep(random.uniform(0.8, 1.2))

    print(f"🏺 [Relic] รับรางวัลเสร็จเรียบร้อย (กดเปิด {taps} ครั้ง) -> กดปิดกลับสู่ล็อบบี้")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, RELIC_CLOSE_BUTTON[0], RELIC_CLOSE_BUTTON[1])
    time.sleep(random.uniform(1.2, 1.8))


def handle_anti_bot(screen):
    print("🤖 Solving Anti-Bot captcha...")
    card_coords = [
        ANTI_BOT_CARD_POS_1, ANTI_BOT_CARD_POS_2, ANTI_BOT_CARD_POS_3,
        ANTI_BOT_CARD_POS_4, ANTI_BOT_CARD_POS_5, ANTI_BOT_CARD_POS_6,
    ]

    odd_indices = detect_anti_bot_odd_cards(screen)
    card_nums = [i + 1 for i in odd_indices]
    print(f"🃏 Found odd cards: Card {card_nums[0]} and Card {card_nums[1]}")

    for idx in odd_indices:
        cx, cy = card_coords[idx]
        # random tap position inside the card, with a small margin
        margin = 20
        tx = random.randint(cx + margin, cx + ANTI_BOT_CARD_WIDTH - margin)
        ty = random.randint(cy + margin, cy + ANTI_BOT_CARD_HEIGHT - margin)
        print(f"  👆 Tapping Card {idx + 1} at ({tx}, {ty})")
        safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, tx, ty)
        time.sleep(random.uniform(10, 15))

    print("✅ Anti-Bot captcha solved!")
    time.sleep(random.uniform(0.8, 1.4))


def handle_connection_lost():
    print("🔌 Handling Connection Lost...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, CONNECTION_LOST_RELOAD_BUTTON[0], CONNECTION_LOST_RELOAD_BUTTON[1])
    time.sleep(random.uniform(10, 15))


def handle_inactive():
    print("💤 Handling Inactive state...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, INACTIVE_RELOAD_BUTTON[0], INACTIVE_RELOAD_BUTTON[1])
    time.sleep(random.uniform(10, 15))


def handle_send_friend_life(stop_event=None, on_sent=None, max_hearts=0):
    print("💌 Handling Send Friend Life...")
    sent_count = 0
    screen = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
    # Scroll leaderboard to top stop when find the "FRIEND LEADERBOARD" template
    while True:
        if stop_event and stop_event.is_set():
            return
        if detect_templates(screen, FRIEND_TOP_LEADERBOARD_TEMPLATE, FRIEND_TOP_LEADERBOARD_REGION):
            print("✅ Top of Friend Leaderboard reached.")
            break
        print("🔄 Scrolling up to find Send Friend Life...")
        safe_device_scroll(config.DEVICE_IP, config.DEVICE_PORT, LEADERBOARD_BOTTOM_POSITION[0], LEADERBOARD_BOTTOM_POSITION[1], direction="down", distance=300, duration=150)
        time.sleep(random.uniform(0.8, 1.4))
        screen = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
    # Scroll down, tap all send life buttons, stop when bottom leaderboard detected
    no_button_scroll_count = 0
    while True:
        if stop_event and stop_event.is_set():
            print(f"🛑 [Send Hearts] หยุด → ส่งหัวใจไป {sent_count} คน")
            break
        screen = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
        if detect_templates(screen, FRIEND_BOTTOM_LEADERBOARD_TEMPLATE, FRIEND_BOTTOM_LEADERBOARD_REGION):
            print("✅ Bottom of Friend Leaderboard reached. Done sending lives.")
            break
        send_life_button_coords = detect_templates(screen, FRIEND_SEND_LIFE_TEMPLATE, FRIEND_SEND_LIFE_REGION)
        if send_life_button_coords:
            no_button_scroll_count = 0
            for x, y, w, h in send_life_button_coords:
                if stop_event and stop_event.is_set():
                    break
                if max_hearts > 0 and sent_count >= max_hearts:
                    print(f"✅ ส่งหัวใจครบ {max_hearts} ดวงตามที่ตั้งไว้แล้ว ไปต่อเลย!")
                    return

                sent_count += 1
                if on_sent: on_sent(sent_count)
                print(f"💌 Sending life ({sent_count}) to friend...")
                safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, x + w // 2, y + h // 2)
                time.sleep(random.uniform(0.8, 1.4))
                print("💌 Confirming send life...")
                safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, CONFIRM_SEND_LIFE_BUTTON[0], CONFIRM_SEND_LIFE_BUTTON[1])
                time.sleep(random.uniform(0.8, 1.4))
                print("💌 Closing send life dialog...")
                safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, CLOSE_SEND_LIFE_DIALOG_BUTTON[0], CLOSE_SEND_LIFE_DIALOG_BUTTON[1])
                time.sleep(random.uniform(0.8, 1.4))
        else:
            no_button_scroll_count += 1
            if no_button_scroll_count >= 30:
                print("⚠️ No send life buttons found for 30 consecutive scrolls. Giving up.")
                break
            print(f"🔄 No send life buttons found, scrolling down... ({no_button_scroll_count}/30)")
            safe_device_scroll(config.DEVICE_IP, config.DEVICE_PORT, LEADERBOARD_TOP_POSITION[0], LEADERBOARD_TOP_POSITION[1], direction="up", distance=70, duration=150)
            time.sleep(random.uniform(0.8, 1.4))


def handle_quick_receive_and_send_lives(stop_event=None, max_hearts=0):
    print("✉️ Handling Quick Receive and Send Lives...")
    time.sleep(random.uniform(0.8, 1.4))
    # Tap the "Mail" button
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, MAIL_BOX_BUTTON[0], MAIL_BOX_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))
    # Tap the "Lives" tab
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, MAIL_BOX_LIVES_TAB_BUTTON[0], MAIL_BOX_LIVES_TAB_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))
    screen = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
    # No lives to receive
    if detect_templates(screen, NO_LIVES_TO_RECEIVE_TEMPLATE, NO_LIVES_TO_RECEIVE_REGION):
        print("✉️ No lives to receive. Proceeding to send lives...")
        # Close the mail dialog
        safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, MAIL_BOX_CLOSE_BUTTON[0], MAIL_BOX_CLOSE_BUTTON[1])
        return
    # Receive all lives
    print("✉️ Receiving all lives...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, QUICK_RECEIVE_AND_SEND_LIVES_BUTTON[0], QUICK_RECEIVE_AND_SEND_LIVES_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))
    # Tap all send life buttons
    while True:
        # Check if all lifes received and sent!, so break the loop
        screen = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
        all_lives_received_and_sent = detect_templates(screen, ALL_LIVES_RECEIVED_AND_SENT_TEMPLATE, ALL_LIVES_RECEIVED_AND_SENT_REGION)
        if all_lives_received_and_sent:
            print("✉️ All lives received and sent. Done!")
            # Tap the "Confirm" button
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, ACCEPT_ALL_LIVES_RECEIVED_AND_SENT_BUTTON[0], ACCEPT_ALL_LIVES_RECEIVED_AND_SENT_BUTTON[1])
            time.sleep(random.uniform(0.8, 1.4))
            # Close the mail dialog
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, MAIL_BOX_CLOSE_BUTTON[0], MAIL_BOX_CLOSE_BUTTON[1])
            time.sleep(random.uniform(0.8, 1.4))
            break
        # Send lifes to friends
        confirm_send_life_button_coords = detect_templates(screen, CONFIRM_SEND_LIFE_TEMPLATE, CONFIRM_SEND_LIFE_REGION)
        if confirm_send_life_button_coords:
            print("✉️ Sending lives to friends...")
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, CONFIRM_SEND_LIFE_BUTTON[0], CONFIRM_SEND_LIFE_BUTTON[1])
            time.sleep(random.uniform(0.8, 1.4))
    print("✉️ Quick Receive and Send Lives completed.")


def close_announcement_dialog():
    print("🖱️ Closing announcement dialog...")
    for i in range(5):
        print(f"🖱️ Tapping close announcement dialog button {i+1}/5")
        safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, CLOSE_ANNOUNCEMENT_DIALOG_BUTTON[0], CLOSE_ANNOUNCEMENT_DIALOG_BUTTON[1])
        time.sleep(random.uniform(0.8, 1.4))
    time.sleep(random.uniform(0.8, 1.4))
    device_screen = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
    if detect_stage(device_screen, ["PARTY_RUN"]) == "PARTY_RUN":
        close_party_run_mode()
    elif detect_stage(device_screen, ["GAME_SETTINGS"]) == "GAME_SETTINGS":
        close_game_settings()


def close_party_run_mode():
    print("🖱️ Closing Party Run mode...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, EXIT_PARTY_RUN_MODE_BUTTON[0], EXIT_PARTY_RUN_MODE_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


def close_game_settings():
    print("🖱️ Closing Game Settings...")
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, EXIT_GAME_SETTINGS_BUTTON[0], EXIT_GAME_SETTINGS_BUTTON[1])
    time.sleep(random.uniform(0.8, 1.4))


# -------------------
# GIFT DRAW
# -------------------
def _match_gift_template(screen, templates, region, threshold):
    """Return True if any of the templates is found in the given region."""
    if screen is None:
        return False
    matches = detect_templates(screen, templates, region=region, threshold=threshold)
    return len(matches) > 0


def _green_ratio(screen, btn_xy, sample_w=40, sample_h=40):
    """Estimate the ratio of green pixels around a button centre (reverse-engineered from CookieGame_Multi).
    Used to decide whether CONFIRM / PET button is active (green).
    Returns a float 0.0-1.0.
    """
    import cv2
    import numpy as np
    if screen is None:
        return 0.0
    x, y = btn_xy
    half = sample_w // 2
    x1 = max(0, x - half)
    y1 = max(0, y - half)
    x2 = min(screen.shape[1], x + half)
    y2 = min(screen.shape[0], y + half)
    roi = screen[y1:y2, x1:x2]
    if roi.size == 0:
        return 0.0
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lower = np.array([35, 90, 90])
    upper = np.array([75, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    return float(mask.mean()) / 255.0


def draw_gifts_loop(stop_event, on_drawn=None):
    """Auto Gift Draw loop (reverse-engineered from CookieGame_Multi).

    Workflow:
        1. Tap the Gift icon in Lobby.
        2. Verify the Gift Draw title is visible.
        3. Loop up to GIFT_DRAW_MAX times:
           - "Pick a gift box!" screen   → tap box → skip animation
           - Confirm button green (item)  → tap Draw Again
           - Pet button green             → tap Pet button
           - Gift Draw title visible      → tap Draw button
           - Lobby visible                → break
           - Unknown screen > 8 ticks    → exit
        4. Try to return to Lobby.
    """
    print("░▓ ===== [Gift Draw] สุ่มกล่องของขวัญ (กดหยุดเพื่อจบ) ===== ▓░")

    # Tap Gift icon in Lobby
    safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, GIFT_ICON_BUTTON[0], GIFT_ICON_BUTTON[1])
    time.sleep(random.uniform(1.5, 2.2))

    # Verify Gift Draw title appeared
    screen = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
    if not _match_gift_template(screen, GIFT_DRAW_TITLE_TEMPLATE,
                                 GIFT_DRAW_TITLE_REGION, GIFT_DRAW_THRESHOLD):
        print("❌ [Gift Draw] เปิดหน้า Gift Draw ไม่สำเร็จ → ยกเลิก")
        return

    drawn   = 0
    unknown = 0

    for _ in range(GIFT_DRAW_MAX):
        if stop_event.is_set():
            print(f"🛑 [Gift Draw] หยุด → สุ่มไป {drawn} กล่อง")
            break

        screen = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
        if screen is None:
            time.sleep(0.5)
            continue

        # ── Case 1: "Pick a gift box!" screen
        if _match_gift_template(screen, GIFT_PICK_TEMPLATE,
                                 GIFT_PICK_REGION, GIFT_DRAW_THRESHOLD):
            unknown = 0
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, GIFT_BOX_BUTTON[0], GIFT_BOX_BUTTON[1])
            time.sleep(random.uniform(0.8, 1.3))
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, GIFT_SKIP_BUTTON[0], GIFT_SKIP_BUTTON[1])
            time.sleep(random.uniform(1.0, 1.5))
            continue

        # ── Case 2: Confirm button is green (got item) → tap Draw Again
        if _green_ratio(screen, GIFT_CONFIRM_BUTTON) > 0.35:
            unknown = 0
            drawn += 1
            if on_drawn: on_drawn(drawn)
            if stop_event.is_set():
                break
            print(f"🎁 [Gift Draw] ได้กล่องที่ {drawn} → Draw Again")
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, GIFT_AGAIN_BUTTON[0], GIFT_AGAIN_BUTTON[1])
            time.sleep(random.uniform(1.2, 1.8))
            continue

        # ── Case 3: Pet button is green (got pet) → tap Pet button
        if _green_ratio(screen, GIFT_PET_BUTTON) > 0.35:
            unknown = 0
            drawn += 1
            if on_drawn: on_drawn(drawn)
            print(f"🎁 [Gift Draw] ได้กล่องที่ {drawn} (สัตว์เลี้ยง) → Confirm")
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, GIFT_PET_BUTTON[0], GIFT_PET_BUTTON[1])
            time.sleep(random.uniform(1.2, 1.8))
            continue

        # ── Case 4: Gift Draw title visible again → tap Draw button
        if _match_gift_template(screen, GIFT_DRAW_TITLE_TEMPLATE,
                                 GIFT_DRAW_TITLE_REGION, GIFT_DRAW_THRESHOLD):
            unknown = 0
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, GIFT_DRAW_BUTTON[0], GIFT_DRAW_BUTTON[1])
            time.sleep(random.uniform(1.2, 1.8))
            continue

        # ── Case 5: Returned to Lobby
        if detect_templates(screen, config.STAGE_MAINMENU_TEMPLATE, threshold=GIFT_DRAW_THRESHOLD):
            print("🏠 [Gift Draw] กลับถึง Lobby แล้ว")
            break

        # ── Case 6: Unknown screen / Points run out
        unknown += 1
        if unknown >= 8:
            print("⚠️ [Gift Draw] แต้มหมดหรือค้างนานเกิน → สิ้นสุดการสุ่ม")
            break
        # Try skip / escape to get unstuck
        safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, GIFT_SKIP_BUTTON[0], GIFT_SKIP_BUTTON[1])
        time.sleep(random.uniform(0.6, 1.0))
        safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, GIFT_ESC_BUTTON[0], GIFT_ESC_BUTTON[1])
        time.sleep(random.uniform(0.8, 1.2))

    print(f"✅ [Gift Draw] สุ่มเสร็จ — ได้กล่องทั้งหมด {drawn} ใบ")

    # Try to close Gift Draw and return to Lobby (max 10 retries)
    for _ in range(10):
        screen = device_capture_screen(config.DEVICE_IP, config.DEVICE_PORT)
        if screen is None:
            time.sleep(1.0)
            continue

        if detect_templates(screen, config.STAGE_MAINMENU_TEMPLATE, threshold=GIFT_DRAW_THRESHOLD):
            print("🏠 [Gift Draw] กลับถึง Lobby เรียบร้อย")
            break

        if _match_gift_template(screen, GIFT_PICK_TEMPLATE,
                                 GIFT_PICK_REGION, GIFT_DRAW_THRESHOLD):
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, GIFT_BOX_BUTTON[0], GIFT_BOX_BUTTON[1])
            time.sleep(random.uniform(0.8, 1.2))
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, GIFT_SKIP_BUTTON[0], GIFT_SKIP_BUTTON[1])
            time.sleep(random.uniform(1.0, 1.4))
            continue

        if _green_ratio(screen, GIFT_CONFIRM_BUTTON) > 0.35:
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, GIFT_CONFIRM_BUTTON[0], GIFT_CONFIRM_BUTTON[1])
            time.sleep(random.uniform(1.0, 1.4))
            continue

        if _green_ratio(screen, GIFT_PET_BUTTON) > 0.35:
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, GIFT_PET_BUTTON[0], GIFT_PET_BUTTON[1])
            time.sleep(random.uniform(1.0, 1.4))
            continue

        if _match_gift_template(screen, GIFT_DRAW_TITLE_TEMPLATE,
                                 GIFT_DRAW_TITLE_REGION, GIFT_DRAW_THRESHOLD):
            safe_device_tap(config.DEVICE_IP, config.DEVICE_PORT, GIFT_CLOSE_BUTTON[0], GIFT_CLOSE_BUTTON[1])
            time.sleep(random.uniform(1.0, 1.4))
            continue

        time.sleep(1.0)

