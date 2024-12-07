from array import array
from random import randint
from time import time, sleep
import logging

from app.utils import ROMS

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)


class CPU:
    def __init__(
        self, ram_size, font_data, start_pc, logger = _logger
    ):
        self.__logger = logger
        self.__start_pc = start_pc

        self.ram = bytearray(ram_size)
        self.ram[0x50:0x9F] = font_data # rme.md: it’s become popular to put it at `050`–`09F` ([80:159]) ...

        self.stack = array("H")
        self.pc = start_pc

        self.registers = bytearray(16)
        self.index_register = 0

        self.delay_timer = 0
        self.delay_timer_start = 0.0

        self.sound_timer = 0
        self.sound_timer_start = 0.0

        self.INSTRUCTION_MAP = {
            (0, 0, 0xE, 0): self.clear_display,
            (0, 0, 0xE, 0xE): self.return_from_subroutine,
            (1, None, None, None): self.jump_to_address,
            (2, None, None, None): self.call_subroutine,
            (3, None, None, None): self.skip_if_equal,
            (4, None, None, None): self.skip_if_not_equal,
            (5, None, None, 0): self.skip_if_registers_equal,
            (6, None, None, None): self.set_register,
            (7, None, None, None): self.add_to_register,
            (8, None, None, 0): self.set_register_to_register,
            (8, None, None, 1): self.binary_or,
            (8, None, None, 2): self.binary_and,
            (8, None, None, 3): self.binary_xor,
            (8, None, None, 4): self.add_with_carry,
            (8, None, None, 5): self.sub_with_carry,
            (8, None, None, 6): self.shift_right,
            (8, None, None, 7): self.subn_with_carry,
            (8, None, None, 0xE): self.shift_left,
            (9, None, None, 0): self.skip_if_registers_not_equal,
            (0xA, None, None, None): self.set_index_register,
            (0xC, None, None, None): self.set_register_to_random,
            (0xD, None, None, None): self.draw_sprite,
            (0xF, None, 0, 7): self.set_register_to_delay_timer,
            (0xF, None, 1, 5): self.set_delay_timer,
            (0xF, None, 1, 8): self.set_sound_timer,
            (0xF, None, 2, 9): self.set_index_to_font,
            (0xF, None, 3, 3): self.binary_coded_decimal,
            (0xF, None, 1, 0xE): self.add_to_index_register,
            (0xF, None, 5, 5): self.store_registers,
            (0xF, None, 6, 5): self.load_registers,
        }


    def load(self, data: bytes | ROMS):
        if isinstance(data, ROMS):
            data = data.load()

        self.__logger.debug(f"Loaded: {len(data)} data")
        data_slice = self.__start_pc + len(data)
        self.ram[self.__start_pc:data_slice] = data

    def __update_timers(self):
        def update_timer(timer: int, timer_start: float):
            if timer != 0: # 60 ups
                elapsed_ticks = int(60 * abs(time() - timer_start))
                return max(0, timer - elapsed_ticks)

            return timer

        self.delay_timer = update_timer(self.delay_timer, self.delay_timer_start)
        self.sound_timer = update_timer(self.sound_timer, self.sound_timer_start)

    def __get_current_instruction(self) -> tuple:
        [b1, b2] = self.ram[self.pc: self.pc + 2] # 2 байта инструкций
        self.pc += 2  # переход к следующей инструкции
        return b1, b2

    @staticmethod
    def __parce_instruction(instruction: tuple) -> tuple:
        """Разбивает инструкцию (2 байта на ниблы по 4 бита)"""
        b1, b2 = instruction
        n1, n2 = b1 >> 4, b1 & 0x0F
        n3, n4 = b2 >> 4, b2 & 0x0F
        return n1, n2, n3, n4

    def generate_key(self, n1, n2, n3, n4):
        if (n1, None, None, None) in self.INSTRUCTION_MAP:
            return n1, None, None, None
        if (n1, n2, None, None) in self.INSTRUCTION_MAP:
            return n1, n2, None, None
        if (n1, n2, n3, None) in self.INSTRUCTION_MAP:
            return n1, n2, n3, None
        return n1, n2, n3, n4

    def __execute_instruction(self, nibbles: tuple, instruction: tuple):
        b1, b2 = instruction
        n1, n2, n3, n4 = nibbles
        key = self.generate_key(n1, n2, n3, n4)
        print(key)
        if key in self.INSTRUCTION_MAP:
            self.INSTRUCTION_MAP[key](n1, n2, n3, n4, b1, b2)
        else:
            raise ValueError(f"Unknown operation {tuple(map(hex, (n1, n2, n3, n4, b1, b2)))}")

    def __step(self):
        instruction = self.__get_current_instruction()
        nibbles = self.__parce_instruction(instruction)
        self.__execute_instruction(nibbles, instruction)

    def run(self):
        while True:
            sleep(0.001)
            self.__step()


    def clear_display(self, n1, n2, n3, n4, b1, b2):
        self.display.clear()

    def return_from_subroutine(self, n1, n2, n3, n4, b1, b2):
        self.pc = self.stack.pop()

    def jump_to_address(self, n1, n2, n3, n4, b1, b2):
        self.pc = n2 << 8 | b2

    def call_subroutine(self, n1, n2, n3, n4, b1, b2):
        self.stack.append(self.pc)
        self.pc = n2 << 8 | b2

    def skip_if_equal(self, n1, n2, n3, n4, b1, b2):
        if self.registers[n2] == b2:
            self.pc += 2

    def skip_if_not_equal(self, n1, n2, n3, n4, b1, b2):
        if self.registers[n2] != b2:
            self.pc += 2

    def skip_if_registers_equal(self, n1, n2, n3, n4, b1, b2):
        if self.registers[n2] == self.registers[n3]:
            self.pc += 2

    def set_register(self, n1, n2, n3, n4, b1, b2):
        self.registers[n2] = b2

    def add_to_register(self, n1, n2, n3, n4, b1, b2):
        self.registers[n2] = (self.registers[n2] + b2) & 0xFF

    def set_register_to_register(self, n1, n2, n3, n4, b1, b2):
        self.registers[n2] = self.registers[n3]

    def binary_or(self, n1, n2, n3, n4, b1, b2):
        self.registers[n2] |= self.registers[n3]

    def binary_and(self, n1, n2, n3, n4, b1, b2):
        self.registers[n2] &= self.registers[n3]

    def binary_xor(self, n1, n2, n3, n4, b1, b2):
        self.registers[n2] ^= self.registers[n3]

    def add_with_carry(self, n1, n2, n3, n4, b1, b2):
        sum_value = self.registers[n2] + self.registers[n3]
        self.registers[0xF] = sum_value >> 8
        self.registers[n2] = sum_value & 0xFF

    def sub_with_carry(self, n1, n2, n3, n4, b1, b2):
        self.registers[0xF] = 1 if self.registers[n2] > self.registers[n3] else 0
        self.registers[n2] = (self.registers[n2] - self.registers[n3]) & 0xFF

    def shift_right(self, n1, n2, n3, n4, b1, b2):
        self.registers[0xF] = self.registers[n2] & 1
        self.registers[n2] = self.registers[n2] >> 1

    def subn_with_carry(self, n1, n2, n3, n4, b1, b2):
        self.registers[0xF] = 1 if self.registers[n3] > self.registers[n2] else 0
        self.registers[n2] = (self.registers[n3] - self.registers[n2]) & 0xFF

    def shift_left(self, n1, n2, n3, n4, b1, b2):
        self.registers[0xF] = self.registers[n2] & 0x80 >> 7
        self.registers[n2] = (self.registers[n2] << 1) & 0xFF

    def skip_if_registers_not_equal(self, n1, n2, n3, n4, b1, b2):
        if self.registers[n2] != self.registers[n3]:
            self.pc += 2

    def set_index_register(self, n1, n2, n3, n4, b1, b2):
        self.index_register = n2 << 8 | b2

    def set_register_to_random(self, n1, n2, n3, n4, b1, b2):
        self.registers[n2] = randint(0, 0xFF) & b2

    def draw_sprite(self, vx, vy, n, n4, b1, b2):
        x = self.registers[vx]
        y = self.registers[vy]
        self.registers[0xF] = 1 if self.display.draw(x, y,
                                                     self.ram[self.index_register: self.index_register + n]) else 0
        self.display.show()

    def set_register_to_delay_timer(self, n1, n2, n3, n4, b1, b2):
        self.__update_timers()
        self.registers[n2] = self.delay_timer

    def set_delay_timer(self, n1, n2, n3, n4, b1, b2):
        self.delay_timer = self.registers[n2]
        self.delay_timer_start = time()

    def set_sound_timer(self, n1, n2, n3, n4, b1, b2):
        self.sound_timer = self.registers[n2]
        self.sound_timer_start = time()

    def set_index_to_font(self, n1, n2, n3, n4, b1, b2):
        self.index_register = 0x50 + n2 * 5

    def binary_coded_decimal(self, n1, n2, n3, n4, b1, b2):
        num = str(int(self.registers[n2]))
        if self.index_register > len(self.registers):
            print("WARNING: out of range on FX33: ", self.index_register)
            return
        self.registers[self.index_register] = int(num[0])
        self.registers[self.index_register + 1] = int(num[2])
        self.registers[self.index_register + 2] = int(num[2])

    def add_to_index_register(self, n1, n2, n3, n4, b1, b2):
        self.index_register = self.index_register + self.registers[n2]

    def store_registers(self, n1, n2, n3, n4, b1, b2):
        for ri in range(n2 + 1):
            self.ram[self.index_register + ri] = self.registers[ri]

    def load_registers(self, n1, n2, n3, n4, b1, b2):
        for ri in range(n2 + 1):
            self.registers[ri] = self.ram[self.index_register + ri]



