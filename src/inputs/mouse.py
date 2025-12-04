import ctypes
import os
import time
from ctypes import c_int, c_byte

# Константы Win32
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

class InputHandler:
    def __init__(self, dll_name="logitech-cve.dll", use_ghub=True):
        self.ghub = None
        self.use_ghub = False
        self.dll_loaded = False
        
        if use_ghub:
            dll_path = os.path.join(os.getcwd(), dll_name)
            if os.path.exists(dll_path):
                try:
                    self.ghub = ctypes.CDLL(dll_path)
                    self.dll_loaded = True
                    
                    # Настройка сигнатур функций (типы аргументов и возврата)
                    self.ghub.mouse_open.restype = c_int
                    self.ghub.mouse_close.restype = None
                    self.ghub.mouse_move.restype = c_int
                    self.ghub.mouse_move.argtypes = [c_byte, c_byte, c_byte, c_byte]

                    # Попытка инициализации
                    ret = self.ghub.mouse_open()
                    if ret == 1:
                        print(f"✅ [Input] G-Hub драйвер подключен успешно.")
                        self.use_ghub = True
                    else:
                        print(f"⚠️ [Input] mouse_open вернул {ret}. Драйвер не найден или занят.")
                
                except Exception as e:
                    print(f"❌ [Input] Критическая ошибка DLL: {e}")
            else:
                print(f"⚠️ [Input] Файл {dll_name} не найден. Используем Win32 API.")

    def __del__(self):
        """Автоматическая очистка при удалении объекта"""
        self.close()

    def move(self, x, y):
        """
        Умное перемещение с разбивкой на пакеты и проверкой ошибок.
        """
        x = int(x)
        y = int(y)

        if self.use_ghub:
            while x != 0 or y != 0:
                # Ограничиваем шаг байтом (-127..127)
                step_x = max(-127, min(127, x))
                step_y = max(-127, min(127, y))
                
                # Вызываем DLL
                ret = self.ghub.mouse_move(c_byte(0), c_byte(step_x), c_byte(step_y), c_byte(0))
                
                # 1. Проверка ошибок (твое улучшение)
                if ret != 0:
                    print(f"❌ [GHub Error] mouse_move failed with code: {ret}")
                    break

                x -= step_x
                y -= step_y
                if x != 0 or y != 0:
                    time.sleep(0) 
        else:
            # Win32 Fallback
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, x, y, 0, 0)

    def click(self):
        """Безопасный клик"""
        if self.use_ghub:
            # Press
            self.ghub.mouse_move(c_byte(1), c_byte(0), c_byte(0), c_byte(0))
            
            # Рандомная задержка (Humanization)
            # time.sleep(0) тут опасно, клик может быть слишком быстрым для игры.
            # Оставляем минимальную реальную задержку.
            time.sleep(0.01 + (time.time() % 0.01)) 
            
            # Release
            self.ghub.mouse_move(c_byte(0), c_byte(0), c_byte(0), c_byte(0))
        else:
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.01)
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def close(self):
        """Явное закрытие ресурсов"""
        if self.use_ghub and self.dll_loaded:
            try:
                self.ghub.mouse_close()
                self.use_ghub = False # Флаг, чтобы не закрывать дважды
            except:
                pass

    @staticmethod
    def is_key_down(key_code):
        return ctypes.windll.user32.GetAsyncKeyState(key_code) & 0x8000