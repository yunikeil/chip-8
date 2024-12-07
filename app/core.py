from array import array
from random import randint
from time import time, sleep
import logging

from app.utils import ROMS

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)


class CPU:
    def __init__(
        self, ram_size, font_data, start_pc, display, logger = _logger
    ):
        self.__display = display
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
    def __parse_instruction(instruction: tuple) -> tuple:
        """Разбивает инструкцию (2 байта на ниблы по 4 бита)"""
        b1, b2 = instruction
        n1, n2 = b1 >> 4, b1 & 0x0F
        n3, n4 = b2 >> 4, b2 & 0x0F
        return n1, n2, n3, n4

    def __execute_instruction(self, nibbles: tuple, instruction: tuple):
        b1, b2 = instruction
        n1, n2, n3, n4 = nibbles

        match (n1, n2, n3, n4):
            case (0, 0, 0xE, 0):
                self.__clear_display()
            case (0, 0, 0xE, 0xE):
                self.__return_from_subroutine()
            case (1, _, _, _):
                self.__jump_to_address(n2, n3, n4, b2)
            case (2, _, _, _):
                self.__call_subroutine(n2, n3, n4, b2)
            case (3, _, _, _):
                self.__skip_if_equal(n2, n3, n4, b2)
            case (4, _, _, _):
                self.__skip_if_not_equal(n2, n3, n4, b2)
            case (5, _, _, 0):
                self.__skip_if_registers_equal(n2, n3, n4, b2)
            case (6, _, _, _):
                self.__set_register(n2, n3, n4, b2)
            case (7, _, _, _):
                self.__add_to_register(n2, n3, n4, b2)
            case (8, _, _, 0):
                self.__set_register_to_register(n2, n3, n4, b2)
            case (8, _, _, 1):
                self.__binary_or(n2, n3, n4, b2)
            case (8, _, _, 2):
                self.__binary_and(n2, n3, n4, b2)
            case (8, _, _, 3):
                self.__binary_xor(n2, n3, n4, b2)
            case (8, _, _, 4):
                self.__add_with_carry(n2, n3, n4, b2)
            case (8, _, _, 5):
                self.__sub_with_carry(n2, n3, n4, b2)
            case (8, _, _, 6):
                self.__shift_right(n2, n3, n4, b2)
            case (8, _, _, 7):
                self.__subn_with_carry(n2, n3, n4, b2)
            case (8, _, _, 0xE):
                self.__shift_left(n2, n3, n4, b2)
            case (9, _, _, 0):
                self.__skip_if_registers_not_equal(n2, n3, n4, b2)
            case (0xA, _, _, _):
                self.__set_index_register(n2, n3, n4, b2)
            case (0xC, _, _, _):
                self.__set_register_to_random(n2, n3, n4, b2)
            case (0xD, vx, vy, n):
                self.__draw_sprite(vx, vy, n, b2)
            case (0xE, _, 9, 0xE):
                # control ..
                ...
            case (0xE, _, 0xA, 1):
                # control ..
                ...
            case (0xF, _, 0x0, 0xA):
                # control ..
                ...
            case (0xF, _, 0, 7):
                self.__set_register_to_delay_timer(n2, n3, n4, b2)
            case (0xF, _, 1, 5):
                self.__set_delay_timer(n2, n3, n4, b2)
            case (0xF, _, 1, 8):
                self.__set_sound_timer(n2, n3, n4, b2)
            case (0xF, _, 2, 9):
                self.__set_index_to_font(n2, n3, n4, b2)
            case (0xF, _, 3, 3):
                self.__binary_coded_decimal(n2, n3, n4, b2)
            case (0xF, _, 1, 0xE):
                self.__add_to_index_register(n2, n3, n4, b2)
            case (0xF, _, 5, 5):
                self.__store_registers(n2, n3, n4, b2)
            case (0xF, _, 6, 5):
                self.__load_registers(n2, n3, n4, b2)
            case _:

                self.__logger.error(f"code: {list(map(hex, instruction))}; {hex((b1 << 8) | b2)}")
                raise ValueError(f"Unknown operation {list(map(hex, (n1, n2, n3, n4)))}")

    def __step(self):
        instruction = self.__get_current_instruction()
        nibbles = self.__parse_instruction(instruction)
        self.__execute_instruction(nibbles, instruction)

    def run(self):
        try:
            while True:
                sleep(0.1)
                self.__step()
        except KeyboardInterrupt:
            self.__logger.info("Interrupted")


    def __clear_display(self):
        self.__display.clear()

    def __return_from_subroutine(self):
        self.pc = self.stack.pop()

    def __jump_to_address(self, n2, n3, n4, b2):
        self.pc = n2 << 8 | b2

    def __call_subroutine(self, n2, n3, n4, b2):
        self.stack.append(self.pc)
        self.pc = n2 << 8 | b2

    def __skip_if_equal(self, n2, n3, n4, b2):
        if self.registers[n2] == b2:
            self.pc += 2

    def __skip_if_not_equal(self, n2, n3, n4, b2):
        if self.registers[n2] != b2:
            self.pc += 2

    def __skip_if_registers_equal(self, n2, n3, n4, b2):
        if self.registers[n2] == self.registers[n3]:
            self.pc += 2

    def __set_register(self, n2, n3, n4, b2):
        self.registers[n2] = b2

    def __add_to_register(self, n2, n3, n4, b2):
        self.registers[n2] = (self.registers[n2] + b2) & 0xFF

    def __set_register_to_register(self, n2, n3, n4, b2):
        self.registers[n2] = self.registers[n3]

    def __binary_or(self, n2, n3, n4, b2):
        self.registers[n2] |= self.registers[n3]

    def __binary_and(self, n2, n3, n4, b2):
        self.registers[n2] &= self.registers[n3]

    def __binary_xor(self, n2, n3, n4, b2):
        self.registers[n2] ^= self.registers[n3]

    def __add_with_carry(self, n2, n3, n4, b2):
        sum_value = self.registers[n2] + self.registers[n3]
        self.registers[0xF] = sum_value >> 8
        self.registers[n2] = sum_value & 0xFF

    def __sub_with_carry(self, n2, n3, n4, b2):
        self.registers[0xF] = 1 if self.registers[n2] > self.registers[n3] else 0
        self.registers[n2] = (self.registers[n2] - self.registers[n3]) & 0xFF

    def __shift_right(self, n2, n3, n4, b2):
        self.registers[0xF] = self.registers[n2] & 1
        self.registers[n2] = self.registers[n2] >> 1

    def __subn_with_carry(self, n2, n3, n4, b2):
        self.registers[0xF] = 1 if self.registers[n3] > self.registers[n2] else 0
        self.registers[n2] = (self.registers[n3] - self.registers[n2]) & 0xFF

    def __shift_left(self, n2, n3, n4, b2):
        self.registers[0xF] = self.registers[n2] & 0x80 >> 7
        self.registers[n2] = (self.registers[n2] << 1) & 0xFF

    def __skip_if_registers_not_equal(self, n2, n3, n4, b2):
        if self.registers[n2] != self.registers[n3]:
            self.pc += 2

    def __set_index_register(self, n2, n3, n4, b2):
        self.index_register = n2 << 8 | b2

    def __set_register_to_random(self, n2, n3, n4, b2):
        self.registers[n2] = randint(0, 0xFF) & b2
        print(123)

    def __draw_sprite(self, vx, vy, n, b2):
        x = self.registers[vx]
        y = self.registers[vy]
        rg = self.__display.draw(x, y, self.ram[self.index_register: self.index_register + n])
        self.registers[0xF] = 1 if rg else 0
        self.__display.show()

    def __skip_if_key_pressed(self, n2):
        # if self.__control.is_pressed(self.registers[n2]):
        #     self.pc += 2
        self.__logger.info(self.registers[n2])

    def __skip_if_key_not_pressed(self, n2):
        # if not self.__control.is_pressed(self.registers[n2]):
        #     self.pc += 2
        self.__logger.info(self.registers[n2])

    def __set_register_to_delay_timer(self, n2, n3, n4, b2):
        self.__update_timers()
        self.registers[n2] = self.delay_timer

    def __set_delay_timer(self, n2, n3, n4, b2):
        self.delay_timer = self.registers[n2]
        self.delay_timer_start = time()

    def __set_sound_timer(self, n2, n3, n4, b2):
        self.sound_timer = self.registers[n2]
        self.sound_timer_start = time()

    def __set_index_to_font(self, n2, n3, n4, b2):
        self.index_register = 0x50 + n2 * 5

    def __binary_coded_decimal(self, n2, n3, n4, b2):
        num = str(int(self.registers[n2]))
        if self.index_register > len(self.registers):
            self.__logger.warning(f"out of range on FX33: {self.index_register} > {len(self.registers)}")
            # input("Next?")
            return
        self.registers[self.index_register] = int(num[0])
        self.registers[self.index_register + 1] = int(num[2])
        self.registers[self.index_register + 2] = int(num[2])

    def __add_to_index_register(self, n2, n3, n4, b2):
        self.index_register = self.index_register + self.registers[n2]

    def __store_registers(self, n2, n3, n4, b2):
        for ri in range(n2 + 1):
            self.ram[self.index_register + ri] = self.registers[ri]

    def __load_registers(self, n2, n3, n4, b2):
        for ri in range(n2 + 1):
            self.registers[ri] = self.ram[self.index_register + ri]


