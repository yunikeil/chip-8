from array import array
from time import time, sleep
import logging

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)


class CPU:
    def __init__(
        self, ram_size, font_data, start_pc, logger = _logger
    ):
        self.__logger = logger
        self.__start_pc = start_pc

        self.ram = bytearray(ram_size)
        self.ram[0x50:0x9F] = font_data # rme.md: it’s become popular to put it at `050`–`09F` ...

        self.stack = array("H")
        self.pc = start_pc

        self.registers = bytearray(16)
        self.index_register = 0

        self.delay_timer = 0
        self.delay_timer_start = 0.0

        self.sound_timer = 0
        self.sound_timer_start = 0.0

    def load(self, data: bytes):
        self.__logger.debug(f"Loaded: {len(data)} data")
        data_slice = self.__start_pc + len(data)
        self.ram[self.__start_pc:data_slice] = data

    def update_timers(self):
        def update_timer(timer: int, timer_start: float):
            if timer != 0: # 60 ups
                elapsed_ticks = int(60 * abs(time() - timer_start))
                return max(0, timer - elapsed_ticks)

            return timer

        self.delay_timer = update_timer(self.delay_timer, self.delay_timer_start)
        self.sound_timer = update_timer(self.sound_timer, self.sound_timer_start)

    def step(self):
        ...

    def run(self):
        ...





