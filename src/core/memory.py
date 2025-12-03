import pymem
import pymem.process
import struct
import logging
from typing import Any, List, Tuple, Optional

class Memory:
    def __init__(self, process_name="cs2.exe", debug=False):

        self.debug = debug
        self.pointer_cache = {}
        self.process_name = process_name
        self.pm = None
        self.client_base = 0
        
        try:
            self.pm = pymem.Pymem(process_name)
            
            client_module = pymem.process.module_from_name(self.pm.process_handle, "client.dll")
            if not client_module:
                raise Exception("client.dll not found")
            self.client_base = client_module.lpBaseOfDll
            
            logging.info(f"Attached to {process_name}. Client Base: {hex(self.client_base)}")
            
        except Exception as e:
            logging.error(f"Failed to attach to {process_name}: {e}")
            raise e

    def clear_cache(self):
        self.pointer_cache = {}

    def read_bytes(self, address: int, length: int) -> Optional[bytes]:
        if not address:
            if self.debug: logging.debug("read_bytes: Address is 0")
            return None
        try:
            return self.pm.read_bytes(address, length)
        except Exception as e:
            if self.debug: logging.debug(f"Failed read_bytes at {hex(address)}: {e}")
            return None

    def read_struct(self, address: int, format_str: str) -> Optional[Tuple]:
        if not address:
            return None
        try:
            size = struct.calcsize(format_str)
            data = self.pm.read_bytes(address, size)
            return struct.unpack(format_str, data)
        except Exception as e:
            if self.debug: logging.debug(f"Failed read_struct at {hex(address)}: {e}")
            return None

# wrappers
    def read_ptr(self, address: int) -> int:
        res = self.read_struct(address, '<Q')
        return res[0] if res else 0

    def read_u32(self, address: int) -> int:
        res = self.read_struct(address, '<I')
        return res[0] if res else 0

    def read_i32(self, address: int) -> int:
        res = self.read_struct(address, '<i')
        return res[0] if res else 0

    def read_float(self, address: int) -> float:
        res = self.read_struct(address, '<f')
        return res[0] if res else 0.0

    def read_vec3(self, address: int) -> Tuple[float, float, float]:
        res = self.read_struct(address, '<fff')
        return res if res else (0.0, 0.0, 0.0)

    def read_matrix(self, address: int) -> List[float]:
        res = self.read_struct(address, '<16f')
        return list(res) if res else []


    def read_string(self, address: int, max_length=128) -> str:
        if not address: return ""
        try:
            data = self.pm.read_bytes(address, max_length)
            null_index = data.find(b'\x00')
            if null_index != -1:
                data = data[:null_index]
            return data.decode('utf-8', errors='ignore')
        except Exception:
            return ""


    def get_pointer(self, base: int, offsets: List[int]) -> int:
        if base == 0:
            return 0
        
        cache_key = (base, tuple(offsets))
        
        if cache_key in self.pointer_cache:
            return self.pointer_cache[cache_key]

        try:
            addr = self.read_ptr(base)

            for offset in offsets[:-1]:
                if addr == 0:
                    self.pointer_cache[cache_key] = 0
                    return 0
                addr = self.read_ptr(addr + offset)

            if addr == 0:
                self.pointer_cache[cache_key] = 0
                return 0
            
            result = addr + offsets[-1]
            self.pointer_cache[cache_key] = result
            return result
            
        except Exception as e:
            if self.debug: logging.debug(f"get_pointer failed: {e}")
            self.pointer_cache[cache_key] = 0
            return 0

    def read_bones_batch(self, bone_matrix_addr: int, max_index=64) -> List[Tuple[float, float, float]]:
        if not bone_matrix_addr:
            return []
        size = (max_index + 1) * 32
        
        buffer = self.read_bytes(bone_matrix_addr, size)
        if not buffer:
            return []

        bones = []
        try:
            for i in range(max_index + 1):
                offset = i * 32
                if offset + 12 <= len(buffer):
                    vec = struct.unpack_from('<fff', buffer, offset)
                    bones.append(vec)
                else:
                    bones.append((0.0, 0.0, 0.0))
        except struct.error as e:
            if self.debug: logging.debug(f"read_bones_batch struct error: {e}")
            pass
            
        return bones