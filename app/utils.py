from enum import Enum

def byte_to_bits(b: int) -> list[int]:
    return [(b >> (7 - p) & 1) for p in range(8)]


class ROMS(str, Enum):
    TEST_OPCODE = "test_opcode.ch8"
    PONG = "Pong (alt).ch8"
    DELAY_TEST = "delay_timer_test.ch8"
    RANDOM_TEST = "random_number_test.ch8"
    IBM = "IBM Logo.ch8"

    def load(self) -> bytes:
        with open(f"roms/{self.value}", "rb") as rom_file:
            return rom_file.read()

