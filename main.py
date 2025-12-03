import logging
import time
import os
import sys

# Добавляем путь к src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.offsets import Offsets
from src.core.memory import Memory
from src.game.manager import GameManager

# Настройка цветов для консоли
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format=f'{Colors.YELLOW}[%(asctime)s]{Colors.RESET} %(message)s',
        datefmt='%H:%M:%S'
    )
    logging.getLogger('pymem').setLevel(logging.WARNING)

def run_debug_loop():
    logger = logging.getLogger("Debug")
    logger.info("Запуск медленного режима отладки...")

    if not Offsets.update_offsets():
        logger.error("Ошибка оффсетов.")
        return

    try:
        mem = Memory("cs2.exe")
        game = GameManager(mem)
    except Exception as e:
        logger.error(f"Игра не найдена: {e}")
        return

    logger.info("Успешное подключение. Логи обновляются каждые 1.5 сек...")
    
    # Переменные для отслеживания изменений (чтобы видеть разницу)
    last_hp = -1
    last_enemy_count = -1

    try:
        while True:
            # 1. Обновляем данные
            game.update_local_player()
            
            if game.local_player:
                game.update_view_matrix()
                game.update_entities() # Работает LOD и кэш

                me = game.local_player
                enemies = game.entities
                
                # --- Логика отображения изменений ---
                
                # Формируем строку статуса
                hp_color = Colors.GREEN if me.health > 50 else Colors.RED
                hp_status = f"{hp_color}HP: {me.health}{Colors.RESET}"
                
                # Если HP изменилось, пишем об этом явно
                if me.health != last_hp:
                    hp_status += f" {Colors.BOLD}(CHANGED! was {last_hp}){Colors.RESET}"
                    last_hp = me.health

                count_status = f"Enemies: {len(enemies)}"
                if len(enemies) != last_enemy_count:
                    count_status += f" {Colors.CYAN}(Count CHANGED!){Colors.RESET}"
                    last_enemy_count = len(enemies)

                # Выводим блок информации (без очистки экрана!)
                print(f"\n{Colors.CYAN}--- SNAPSHOT ---{Colors.RESET}")
                print(f"ME: {hp_status} | Team: {me.team} | Pos: {int(me.pos[0])}, {int(me.pos[1])}")
                print(f"DATA: {count_status}")
                
                if enemies:
                    print("List:")
                    for i, e in enumerate(enemies):
                        dist = int(me.get_distance(e.pos) / 100) # Дистанция в метрах (примерно)
                        
                        # Проверка костей
                        head = e.get_head_pos()
                        has_bones = head != (0.0, 0.0, 0.0)
                        
                        bone_str = f"{Colors.GREEN}BONES OK{Colors.RESET}" if has_bones else f"{Colors.RED}NO BONES (Far){Colors.RESET}"
                        
                        print(f"  [{i}] HP: {e.health:<3} | Dist: {dist}m | {bone_str} | Head: {int(head[0])}, {int(head[1])}")
                else:
                    print(f"{Colors.YELLOW}  No enemies visible/alive.{Colors.RESET}")

            else:
                print(f"\n{Colors.YELLOW}[WAITING] LocalPlayer not found... (In Lobby?){Colors.RESET}")

            # Ждем 1.5 секунды, чтобы ты успел прочитать
            time.sleep(1.5)

    except KeyboardInterrupt:
        print("\nСтоп.")

if __name__ == "__main__":
    setup_logging()
    run_debug_loop()