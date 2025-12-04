import logging
import time
import os
import sys
import ctypes
import math
import winsound

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.offsets import Offsets
from src.core.memory import Memory
from src.game.manager import GameManager
from game.geometry import world_to_screen
from inputs.mouse import InputHandler

# --- Настройки ---
user32 = ctypes.windll.user32
SCREEN_WIDTH = user32.GetSystemMetrics(0)
SCREEN_HEIGHT = user32.GetSystemMetrics(1)
CENTER_X = SCREEN_WIDTH // 2
CENTER_Y = SCREEN_HEIGHT // 2

TRIGGER_KEY = 0x12  # ALT
AIM_KEY = 0x06      # XBUTTON2 (Боковая кнопка мыши)
TRIGGER_FOV = 180    # маленькая зона вокруг прицела
SHOT_COOLDOWN = 0.8 # секунда между выстрелами
AIM_SMOOTH = 7.0
AIM_Z_OFFSET = 2.0

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

def run_full_test():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    if not Offsets.update_offsets(): return

    try:
        mem = Memory("cs2.exe")
        game = GameManager(mem)
        input_handler = InputHandler(use_ghub=False)
    except Exception:
        print("CS2 не найден.")
        return

    triggerbot_enabled = False
    trigger_key_was_pressed = False
    last_shot_time = 0

    print(f"{Colors.GREEN}--- ONE-TAP MACHINE READY ---{Colors.RESET}")
    print(f"Press [ALT] to toggle Triggerbot.")

    try:
        while True:
            # --- Toggle Triggerbot ---
            key_is_down = input_handler.is_key_down(TRIGGER_KEY)
            if key_is_down and not trigger_key_was_pressed:
                triggerbot_enabled = not triggerbot_enabled
                status_msg = f"{Colors.GREEN}ON{Colors.RESET}" if triggerbot_enabled else f"{Colors.RED}OFF{Colors.RESET}"
                winsound.Beep(1500 if triggerbot_enabled else 600, 100)
                print(f"\n[!] Triggerbot: {status_msg}")
                last_shot_time = 0
                trigger_key_was_pressed = True
            elif not key_is_down:
                trigger_key_was_pressed = False

            # --- Обновление игры ---
            if not game.update_local_player(): 
                time.sleep(0.5)
                continue
            game.update_view_matrix()
            game.update_entities()

            me = game.local_player
            target_entity = None
            min_crosshair_dist = float('inf')

            # --- Поиск цели ---
            for e in game.entities:
                head_pos = e.get_head_pos()
                if not head_pos or head_pos == (0.0, 0.0, 0.0): continue
                w2s = world_to_screen(game.view_matrix, head_pos, SCREEN_WIDTH, SCREEN_HEIGHT)
                if w2s:
                    dist = math.sqrt((w2s[0] - CENTER_X)**2 + (w2s[1] - CENTER_Y)**2)
                    if dist < min_crosshair_dist:
                        min_crosshair_dist = dist
                        target_entity = e

            # --- Triggerbot ---
            current_time = time.time()
            if triggerbot_enabled and target_entity and min_crosshair_dist < TRIGGER_FOV:
                if current_time - last_shot_time >= SHOT_COOLDOWN:
                    input_handler.click()
                    last_shot_time = current_time
                    print(f"{Colors.GREEN}[ONE TAP] HP={target_entity.health}{Colors.RESET}")

            # --- Aimbot ---
            if target_entity and input_handler.is_key_down(AIM_KEY):
                aim_pos = (
                    target_entity.get_head_pos()[0],
                    target_entity.get_head_pos()[1],
                    target_entity.get_head_pos()[2] + AIM_Z_OFFSET
                )
                w2s_target = world_to_screen(game.view_matrix, aim_pos, SCREEN_WIDTH, SCREEN_HEIGHT)
                if w2s_target:
                    delta_x = w2s_target[0] - CENTER_X
                    delta_y = w2s_target[1] - CENTER_Y
                    move_x = math.ceil(delta_x / AIM_SMOOTH) if delta_x > 0 else math.floor(delta_x / AIM_SMOOTH)
                    move_y = math.ceil(delta_y / AIM_SMOOTH) if delta_y > 0 else math.floor(delta_y / AIM_SMOOTH)
                    input_handler.move(move_x, move_y)

            # --- Статус ---
            status_line = f"Target HP: {target_entity.health} | Dist: {int(min_crosshair_dist)}px" if target_entity else "No target"
            trigger_status = f"{Colors.GREEN}ON{Colors.RESET}" if triggerbot_enabled else f"{Colors.RED}OFF{Colors.RESET}"
            sys.stdout.write(f"\rHP: {me.health} | Trigger: {trigger_status} | {status_line}{' '*20}")
            sys.stdout.flush()

            time.sleep(0.005)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        if 'input_handler' in locals(): input_handler.close()


if __name__ == "__main__":
    run_full_test()
