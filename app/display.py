import curses

from app.utils import byte_to_bits


class SimpleDisplay:
    def __init__(self, width, height) -> None:
        self.width = width
        self.height = height
        self.screen = bytearray(width * height)

    def clear(self) -> None:
        for i in range(len(self.screen)):
            self.screen[i] = 0

    def draw(self, x: int, y: int, sprite_data: bytearray) -> bool:
        x %= self.width
        y %= self.height
        did_switch = False

        for yo, sprite_byte in enumerate(sprite_data):
            row = y + yo
            if row >= self.height:
                break

            bits = byte_to_bits(sprite_byte)
            for xo, bit in enumerate(bits):
                col = x + xo
                if col >= self.width:
                    break

                cur_pixel_idx = col + row * self.width

                if bit == 1:
                    current_pixel = self.screen[cur_pixel_idx]
                    self.screen[cur_pixel_idx] = 1 - current_pixel
                    if current_pixel == 1:
                        did_switch = True

        return did_switch

    def show(self) -> None:
        res = ""
        for idx in range(len(self.screen)):
            if idx % self.width == 0:
                res += "\n"
            res += "░" if self.screen[idx] == 0 else "█"
        print(res)


class Display:
    def __init__(self, width, height):
        self.screen = curses.initscr()

    def test(self):
        ...
