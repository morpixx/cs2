import struct
import math
import collections
from typing import List, Tuple, Dict, Optional, Deque
from src.core.offsets import Offsets
from src.core.memory import Memory

class Entity:
    # 1. ОПТИМИЗАЦИЯ ПАМЯТИ
    __slots__ = (
        'mem', 'address', 'health', 'team', 'pos', 'view_offset', 'velocity',
        'dormant', 'spotted', 'scoped', 'flash_duration', 'shots_fired',
        'weapon_id', 'game_scene_node', 'bone_matrix', 'bone_cache',
        'pos_history', 'shots_history'
    )

    HISTORY_SIZE = 12
    
    # 2. ПРЕДКОМПИЛЯЦИЯ СТРУКТУР (Ускорение парсинга)
    _ST_INT = struct.Struct('<i')
    _ST_UINT = struct.Struct('<I')
    _ST_FLOAT = struct.Struct('<f')
    _ST_BOOL = struct.Struct('<?')
    _ST_QWORD = struct.Struct('<Q')
    _ST_VEC3 = struct.Struct('<fff')

    def __init__(self, memory: Memory, address: int):
        self.mem = memory
        self.address = address
        
        # Данные
        self.health = 0
        self.team = 0
        self.pos = (0.0, 0.0, 0.0)
        self.view_offset = (0.0, 0.0, 0.0)
        self.velocity = (0.0, 0.0, 0.0)
        
        # Состояния
        self.dormant = True
        self.spotted = False
        self.scoped = False
        self.flash_duration = 0.0
        self.shots_fired = 0
        self.weapon_id = 0
        
        # Указатели
        self.game_scene_node = 0
        self.bone_matrix = 0
        
        # Кэш и История
        self.bone_cache: Dict[int, Tuple[float, float, float]] = {}
        self.pos_history: Deque[Tuple[float, float, float]] = collections.deque(maxlen=self.HISTORY_SIZE)
        self.shots_history: Deque[int] = collections.deque(maxlen=5)

    def update(self, lite: bool = False) -> bool:
        if not self.address:
            return False
        
        # 3. АДАПТИВНОЕ ЧТЕНИЕ
        # Если нам нужно только проверить HP и позицию, читаем меньше (например 0x600 байт),
        # так как m_iHealth, m_iTeamNum и m_vOldOrigin обычно находятся в начале структуры Pawn.
        # Но если оффсеты далеко, лучше оставить 0x5000 или настроить SIZE под свои оффсеты.
        # Для надежности оставим 0x5000, но это место для тюнинга.
        read_size = 0x5000 
        
        buffer = self.mem.read_bytes(self.address, read_size)
        if not buffer:
            self.dormant = True
            self.health = 0
            return False

        buf_len = len(buffer)

        # --- Helpers (Inline для скорости) ---
        # Мы используем методы struct напрямую, избегая создания лишних функций
        
        try:
            # Health
            if Offsets.m_iHealth + 4 <= buf_len:
                self.health = self._ST_INT.unpack_from(buffer, Offsets.m_iHealth)[0]
            else:
                self.health = 0

            # Dead check
            if self.health <= 0:
                self.dormant = True
                self.pos_history.clear()
                self.shots_history.clear()
                return False

            # Team
            if Offsets.m_iTeamNum + 4 <= buf_len:
                self.team = self._ST_INT.unpack_from(buffer, Offsets.m_iTeamNum)[0]
            
            # Position (Origin)
            if Offsets.m_vOldOrigin + 12 <= buf_len:
                self.pos = self._ST_VEC3.unpack_from(buffer, Offsets.m_vOldOrigin)
            else:
                self.pos = (0.0, 0.0, 0.0)

            # Если нужен только Lite апдейт - выходим
            if lite:
                self.bone_cache = {} 
                return True

            # --- Full Update ---
            
            # Shots Fired
            if Offsets.m_iShotsFired + 4 <= buf_len:
                self.shots_fired = self._ST_INT.unpack_from(buffer, Offsets.m_iShotsFired)[0]
                self.shots_history.append(self.shots_fired)
            
            # Flash Duration
            if Offsets.m_flFlashDuration + 4 <= buf_len:
                self.flash_duration = self._ST_FLOAT.unpack_from(buffer, Offsets.m_flFlashDuration)[0]
            
            # Scoped
            if Offsets.m_bIsScoped + 1 <= buf_len:
                self.scoped = self._ST_BOOL.unpack_from(buffer, Offsets.m_bIsScoped)[0]
            
            # Physics
            if Offsets.m_vecViewOffset + 12 <= buf_len:
                self.view_offset = self._ST_VEC3.unpack_from(buffer, Offsets.m_vecViewOffset)
            
            if Offsets.m_vecAbsVelocity + 12 <= buf_len:
                self.velocity = self._ST_VEC3.unpack_from(buffer, Offsets.m_vecAbsVelocity)
            
            self.pos_history.append(self.pos)
            
            # --- Bones Logic ---
            if Offsets.m_pGameSceneNode + 8 <= buf_len:
                self.game_scene_node = self._ST_QWORD.unpack_from(buffer, Offsets.m_pGameSceneNode)[0]
                
                if self.game_scene_node:
                    # Читаем ноду
                    node_buffer = self.mem.read_bytes(self.game_scene_node, 0x220)
                    if node_buffer:
                        if Offsets.m_bDormant < len(node_buffer):
                            self.dormant = self._ST_BOOL.unpack_from(node_buffer, Offsets.m_bDormant)[0]
                        
                        if Offsets.m_modelState + 8 <= len(node_buffer):
                            model_state_addr = self._ST_QWORD.unpack_from(node_buffer, Offsets.m_modelState)[0]
                            if model_state_addr:
                                # Читаем указатель на кости (0x80 offset fix)
                                self.bone_matrix = self.mem.read_ptr(model_state_addr + 0x80)
                            else:
                                self.bone_matrix = 0
                    else:
                        self.dormant = True
            
            self.bone_cache = {} # Сбрасываем кэш костей на новый тик
            return True

        except Exception:
            self.health = 0
            return False

    def update_bones(self, bone_indices: List[int]):
        """Обновляет только запрошенные кости."""
        if not self.bone_matrix or not bone_indices:
            return
            
        max_idx = max(bone_indices)
        # read_bones_batch уже оптимизирован в memory.py, это отлично
        bones_list = self.mem.read_bones_batch(self.bone_matrix, max_index=max_idx)
        
        if not bones_list: return

        # Быстрое обновление словаря
        for idx in bone_indices:
            if idx < len(bones_list):
                self.bone_cache[idx] = bones_list[idx]
    
    def get_bone_pos(self, index: int) -> Tuple[float, float, float]:
        # Самый быстрый путь - вернуть из кэша
        return self.bone_cache.get(index) or self._read_bone_direct(index)

    def _read_bone_direct(self, index: int) -> Tuple[float, float, float]:
        """Фолбэк: прямое чтение, если кость не обновлена в батче."""
        if self.bone_matrix:
            return self.mem.read_vec3(self.bone_matrix + index * 32)
        return (0.0, 0.0, 0.0)

    # --- Math Helpers ---
    # Эти методы вызываются часто, их стоит держать чистыми
    
    def get_head_pos(self):
        return self.get_bone_pos(6) # 6 = Head

    def get_eye_pos(self) -> Tuple[float, float, float]:
        return (
            self.pos[0] + self.view_offset[0],
            self.pos[1] + self.view_offset[1],
            self.pos[2] + self.view_offset[2]
        )

    def is_enemy(self, local_team: int) -> bool:
        return self.team != 0 and self.team != local_team

    def get_distance(self, other_pos: Tuple[float, float, float]) -> float:
        # Евклидово расстояние (оптимизация: для проверки "ближе чем X" лучше использовать dist_sqr, чтобы не извлекать корень)
        dx = self.pos[0] - other_pos[0]
        dy = self.pos[1] - other_pos[1]
        dz = self.pos[2] - other_pos[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)