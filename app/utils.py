from enum import Enum

def byte_to_bits(b: int) -> list[int]:
    return [(b >> (7 - p) & 1) for p in range(8)]


class ROMS(str, Enum):
    TEST_OPCODE = "roms/test_opcode.ch8"
    PONG = "roms/Pong (alt).ch8"

    def load(self) -> bytes:
        with open(self.value, "rb") as rom_file:
            return rom_file.read()

