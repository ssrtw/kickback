import termios
import sys
import struct
import subprocess
import fcntl


class Color():
    FG_Black = 30
    FG_Red = 31
    FG_Green = 32
    FG_Yellow = 33
    FG_Blue = 34
    FG_Magenta = 35
    FG_Cyan = 36
    FG_White = 37
    Reset = 0
    BG_Black = 40
    BG_Red = 41
    BG_Green = 42
    BG_Yellow = 43
    BG_Blue = 44
    BG_Magenta = 45
    BG_Cyan = 46
    BG_White = 47


class Keycode():
    def setpos(row: int = 1, col: int = 1) -> str:
        if row == 1 and col == 1:
            return Keycode.ESCAPE_STR + 'H'
        return '%s%d;%dH' % (Keycode.ESCAPE_STR,  row, col)

    ESCAPE_STR = "\x1b["
    CLEAN = ESCAPE_STR + "2J"
    UP = ESCAPE_STR + '\x41'
    DOWN = ESCAPE_STR + '\x42'
    RIGHT = ESCAPE_STR + '\x43'
    LEFT = ESCAPE_STR + '\x44'
    CLEAN_SET = CLEAN + ESCAPE_STR + 'H'
    ARROW = [UP, DOWN, RIGHT, LEFT]


class RawDialog():
    DIR = {
        Keycode.UP: (0, -1),
        Keycode.DOWN: (0, 1),
        Keycode.RIGHT: (1, 0),
        Keycode.LEFT: (-1, 0),
    }

    def init_termios(self) -> None:
        fd_in = sys.stdin.fileno()
        # 保留原先的 terminal 設定值
        self.old_settings = termios.tcgetattr(fd_in)
        term = termios.tcgetattr(fd_in)
        # 設定 terminal 的功能
        term[3] &= ~(termios.ICRNL | termios.IXON)
        term[3] &= ~(termios.OPOST)
        term[3] &= ~(termios.ICANON | termios.ECHO |
                     termios.IGNBRK | termios.BRKINT)
        termios.tcsetattr(fd_in, termios.TCSAFLUSH, term)

        s = struct.pack('HHHH', 0, 0, 0, 0)
        t = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, s)
        self.row, self.col, _, _ = struct.unpack('HHHH', t)

    def __init__(self) -> None:
        self.init_termios()
        self.running = True
        self.x = 1
        self.y = 1
        self.x_range = (1, self.col)
        self.y_range = (1, self.row)
        self.send(Keycode.CLEAN)

    def send(self, buf: str | bytes) -> None:
        sys.stdout.write(buf)
        sys.stdout.flush()

    def send_color(self, buf, color) -> None:
        tmp = '%s%dm%s%s%dm' % (
            Keycode.ESCAPE_STR, color, buf, Keycode.ESCAPE_STR, Color.Reset)
        self.send(tmp)

    def send_color256(self, buf, color):
        tmp = '%s48;5;%dm'(
            Keycode.ESCAPE_STR, color, buf, Keycode.ESCAPE_STR, Color.Reset)
        self.send(tmp)

    def flushpos(self) -> None:
        self.send(Keycode.setpos(self.y, self.x))

    def move(self, arrow: str) -> None:
        self.x = max(self.x_range[0], min(
            self.x+RawDialog.DIR[arrow][0], self.x_range[1]))
        self.y = max(self.y_range[0], min(
            self.y+RawDialog.DIR[arrow][1], self.y_range[1]))
        self.flushpos()

    def readchar(self) -> str:
        ch = sys.stdin.read(1)
        return ch

    def readkey(self) -> str:
        c1 = self.readchar()
        if c1 in '\x03':
            raise KeyboardInterrupt
        if c1 != "\x1B":
            return c1
        c2 = self.readchar()
        if c2 not in "\x4F\x5B":
            return c1 + c2
        c3 = self.readchar()
        if c3 not in "\x31\x32\x33\x35\x36":
            return c1 + c2 + c3
        c4 = self.readchar()
        if c4 not in "\x30\x31\x33\x34\x35\x37\x38\x39":
            return c1 + c2 + c3 + c4
        c5 = self.readchar()
        return c1 + c2 + c3 + c4 + c5

    def key_event(self, key: str) -> None:
        if key == 'q':
            raise KeyboardInterrupt
        elif key in Keycode.ARROW:
            self.move(key)

    def display(self) -> None:
        pass

    def run(self) -> None:
        while self.running:
            try:
                key = self.readkey()
                self.key_event(key)
            except KeyboardInterrupt:
                termios.tcsetattr(
                    sys.stdin, termios.TCSADRAIN, self.old_settings)
                break


class Kickback(RawDialog):
    bottom_msg = 'Tip: <Space> select. (S)tart script. Select (A)ll. (R)everse select. (q)uit'

    def __init__(self, menu_list) -> None:
        super().__init__()
        self.menu_list = menu_list
        # show menu
        self.display()
        # set cursor available range
        self.x, self.y = 2, 1
        self.x_range = (2, 2)
        self.y_range = (1, len(menu_list))
        self.display()

    def key_event(self, key: str) -> None:
        super().key_event(key)
        if key == ' ':
            pos = self.y - 1
            self.menu_list[pos][0] = not self.menu_list[pos][0]
            self.send(Keycode.setpos(self.y, 1))
            self.set_line(self.menu_list[pos])
            self.flushpos()
        elif key == 'S':
            if self.run_cmd():
                raise KeyboardInterrupt
        elif key == 'A':
            for item in self.menu_list:
                item[0] = True
            self.display()
        elif key == 'R':
            for item in self.menu_list:
                item[0] = not item[0]
            self.display()

    def run_cmd(self):
        combine_sh = ''
        for item in self.menu_list:
            if item[0] == True:
                combine_sh += item[2]
        self.send(Keycode.CLEAN_SET)
        termios.tcsetattr(
            sys.stdin, termios.TCSADRAIN, self.old_settings)
        # https://stackoverflow.com/a/567687
        proc = subprocess.Popen(['/bin/bash', '-c', combine_sh])
        proc.wait()
        return True

    def set_line(self, item):
        self.send('[%s] ' % ('v' if item[0] else ' '))
        color = Color.BG_Blue if item[0] else Color.BG_Black
        self.send_color('%s\r\n' % (item[1]), color)

    def display(self) -> None:
        self.send(Keycode.CLEAN_SET)
        for item in self.menu_list:
            self.set_line(item)
        # show bottom message
        self.send(Keycode.setpos(999, 1))
        self.send(self.bottom_msg)
        self.flushpos()


if __name__ == '__main__':
    menu: list
    kb = Kickback(menu)
    kb.run()
