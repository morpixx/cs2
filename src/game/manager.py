import logging
from typing import List, Optional

from src.core.memory import Memory
from src.core.offsets import Offsets
from src.game.entity import Entity

class GameManager:
    def __init__(self, memory: Memory):
        self.mem = memory
        self.logger = logging.getLogger("GameManager")
        
        self.local_player: Optional[Entity] = None
        self.entities: List[Entity] = []
        self.view_matrix: List[float] = []
        
        self.entity_cache = {} 

    def update_view_matrix(self):
        try:
            matrix = self.mem.read_matrix(self.mem.client_base + Offsets.dwViewMatrix)
            self.view_matrix = matrix if matrix else []
        except Exception:
            self.view_matrix = []

    def update_local_player(self) -> bool:
        try:
            local_pawn_addr = self.mem.read_ptr(self.mem.client_base + Offsets.dwLocalPlayerPawn)
            
            if not local_pawn_addr:
                self.local_player = None
                return False

            if self.local_player is None or self.local_player.address != local_pawn_addr:
                self.local_player = Entity(self.mem, local_pawn_addr)

            return self.local_player.update(lite=False)
            
        except Exception as e:
            self.logger.error(f"Error updating local player: {e}")
            return False

    def update_entities(self):
        if not self.local_player:
            return

        current_entities = []
        entity_list = self.mem.read_ptr(self.mem.client_base + Offsets.dwEntityList)
        
        if not entity_list:
            return

        for i in range(1, 64):
            try:
                list_entry = self.mem.read_ptr(entity_list + (8 * (i >> 9)) + 16)
                if not list_entry: continue
                
                controller_ptr = self.mem.read_ptr(list_entry + 112 * (i & 0x1FF))
                if not controller_ptr: continue

                pawn_handle = self.mem.read_u32(controller_ptr + Offsets.m_hPawn)
                if not pawn_handle: continue

                pawn_index = pawn_handle & 0x7FFF
                
                list_entry_pawn = self.mem.read_ptr(entity_list + (8 * (pawn_index >> 9)) + 16)
                if not list_entry_pawn: continue

                pawn_ptr = self.mem.read_ptr(list_entry_pawn + 112 * (pawn_index & 0x1FF))
                if not pawn_ptr or pawn_ptr == self.local_player.address:
                    continue

                if i in self.entity_cache and self.entity_cache[i].address == pawn_ptr:
                    entity = self.entity_cache[i]
                else:
                    entity = Entity(self.mem, pawn_ptr)
                    self.entity_cache[i] = entity


                if not entity.update(lite=True):
                    continue

                if entity.health <= 0 or not entity.is_enemy(self.local_player.team):
                    continue
                
                distance = entity.get_distance(self.local_player.pos)
                if distance < 6000: 
                    entity.update(lite=False) # Догружаем velocity, shots_fired
                    entity.update_bones(bone_indices=[6, 5, 4, 2, 0, 8, 9, 10, 13, 14, 15, 22, 23, 24, 25, 26, 27])
                else:
                    pass

                current_entities.append(entity)

            except Exception:
                continue

        self.entities = current_entities