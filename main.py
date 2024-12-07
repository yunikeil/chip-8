import logging

from app import constants
from app.utils import ROMS
from app.core import CPU
from app.display import SimpleDisplay, Display
from app.control import Control


logging.basicConfig(level=logging.INFO)

display = SimpleDisplay(
    width=constants.SCREEN_WIDTH,
    height=constants.SCREEN_HEIGHT,
)

cpu = CPU(
    ram_size=constants.RAM_SIZE,
    font_data=constants.FONT_DATA,
    start_pc=constants.INITIAL_PC,
    display=display,
)

cpu.load(ROMS.BAD_APPLE_LONG)

# cpu.display = Display(
#     width=constants.SCREEN_WIDTH,
#     height=constants.SCREEN_HEIGHT,
#
# )

cpu.run()

