import os
import sys
import termios
import abc
import subprocess
from enum import Enum
import yaml
import zlib


class Color:
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


class Key:
    def readchar() -> str:
        ch = sys.stdin.read(1)
        return ch

    def readkey() -> str:
        c1 = Key.readchar()
        if c1 in "\x03":
            raise KeyboardInterrupt
        if c1 != "\x1B":
            return c1
        c2 = Key.readchar()
        if c2 not in "\x4F\x5B":
            return c1 + c2
        c3 = Key.readchar()
        if c3 not in "\x31\x32\x33\x35\x36":
            return c1 + c2 + c3
        c4 = Key.readchar()
        if c4 not in "\x30\x31\x33\x34\x35\x37\x38\x39":
            return c1 + c2 + c3 + c4
        c5 = Key.readchar()
        return c1 + c2 + c3 + c4 + c5

    def send(buf: str | bytes, flush: bool = False) -> None:
        sys.stdout.write(buf)
        if flush:
            sys.stdout.flush()

    def send_color(buf, color) -> None:
        tmp = "%s%dm%s%s%dm" % (Key.ESCAPE_STR, color, buf, Key.ESCAPE_STR, Color.Reset)
        Key.send(tmp)

    def send_color256(buf, color) -> None:
        tmp = "%s48;5;%dm%s%s%dm" % (
            Key.ESCAPE_STR,
            color,
            buf,
            Key.ESCAPE_STR,
            Color.Reset,
        )
        Key.send(tmp)

    def setpos(row: int = 1, col: int = 1) -> str:
        if row <= 1 and col <= 1:
            tmp = Key.ESCAPE_STR + "H"
        tmp = "%s%d;%dH" % (Key.ESCAPE_STR, row, col)
        Key.send(tmp, True)

    ESCAPE_STR = "\x1b["
    CLEAN = ESCAPE_STR + "2J"
    UP = ESCAPE_STR + "\x41"
    DOWN = ESCAPE_STR + "\x42"
    RIGHT = ESCAPE_STR + "\x43"
    LEFT = ESCAPE_STR + "\x44"
    CLEAN_SET = CLEAN + ESCAPE_STR + "H"
    ARROW = [UP, DOWN, RIGHT, LEFT]


class SelectType(Enum):
    Empty = (" ", Color.Reset)
    Some = ("+", Color.BG_Cyan)
    Full = ("*", Color.BG_Blue)


class Card:
    def __init__(self, name: str = "", value: dict = None) -> None:
        self.parent: Card = None
        self._select: SelectType = SelectType.Empty
        self.name: str = name
        self.children: list[Card] = []
        self.script: str = value.get("script", "")
        self.prologue: str = value.get("prologue", "")

    def generate(self) -> tuple[str]:
        """Generate the script content."""
        return (self.prologue, self.script)

    @property
    def select(self) -> SelectType:
        return self._select

    @select.setter
    def select(self, new_type: SelectType) -> None:
        self._select = new_type


class Cassette(Card):
    def parse(name, value: dict) -> "Cassette":
        if value != None and "children" in value:
            curr = Cassette(name=name, value=value)
            for sub_name, sub_val in value["children"].items():
                child = Cassette.parse(sub_name, sub_val)
                child.parent = curr
                curr.children.append(child)
        else:
            if value == None:
                value = {}
            curr = Card(name=name, value=value)
        return curr

    def __init__(self, name, value) -> None:
        super().__init__(name, value)

    def generate(self) -> tuple[str]:
        """Generate the script content, first expanding the script from children."""
        run_prologue = self.prologue
        run_script = ""
        for child in self.children:
            if child.select != SelectType.Empty:
                child_prologue, child_script = child.generate()
                run_prologue += child_prologue
                run_script += child_script
        run_script += self.script
        return (run_prologue, run_script)

    @property
    def select(self) -> SelectType:
        cnt = sum([1 for item in self.children if item.select != SelectType.Empty])
        if cnt == len(self.children):
            self._select = SelectType.Full
        elif cnt == 0:
            self._select = SelectType.Empty
        else:
            self._select = SelectType.Some
        return self._select

    @select.setter
    def select(self, new_type: SelectType) -> None:
        self._select = new_type
        for card in self.children:
            card.select = new_type


class RawDialog(abc.ABC):
    def init_termios(self) -> None:
        fd_in = sys.stdin.fileno()
        # 保留原先的 terminal 設定值
        self.old_settings = termios.tcgetattr(fd_in)
        term = termios.tcgetattr(fd_in)
        # 設定 terminal 的功能
        term[3] &= ~(termios.ICRNL | termios.IXON)
        term[3] &= ~(termios.OPOST)
        term[3] &= ~(termios.ICANON | termios.ECHO | termios.IGNBRK | termios.BRKINT)
        termios.tcsetattr(fd_in, termios.TCSAFLUSH, term)

    def __init__(self) -> None:
        self.init_termios()
        self.x, self.y = 1, 1
        term_size = os.get_terminal_size()
        self.size = (term_size.columns, term_size.lines)

    def flushpos(self) -> None:
        Key.setpos(self.y, self.x)

    def run(self) -> None:
        """TUI main loop"""
        while True:
            self.display()
            try:
                key = Key.readkey()
                self.key_event(key)
            except KeyboardInterrupt:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
                break

    @abc.abstractmethod
    def display(self):
        pass

    @abc.abstractmethod
    def key_event(self, key: Key):
        pass


class Kickback(RawDialog):
    banner: str = """ _      _         _        _                    _
| |    (_)       | |      | |                  | |
| |  _  _   ____ | |  _   | |__   _____   ____ | |  _
| |_/ )| | / ___)| |_/ )  |  _ \ (____ | / ___)| |_/ )
|  _ ( | |( (___ |  _ (   | |_) )/ ___ |( (___ |  _ (
|_| \_)|_| \____)|_| \_)  |____/ \_____| \____)|_| \_)

"""
    offset_y = banner.count("\n")
    bottom_msg: str = (
        "Tip: <Space> select. (S)tart script. (C)heck current script. (q)uit~"
    )

    def __init__(self, data: dict) -> None:
        super().__init__()
        self.root: Card = Cassette.parse("", data)
        self.curr: Card = self.root
        self.update_area()

    def update_area(self) -> None:
        """Set cursor available area"""
        self.x, self.y = 2, 1
        self.max_y = len(self.curr.children)

    def key_event(self, key: str) -> None:
        """Kickback TUI keydown event"""
        if key == "q":
            raise KeyboardInterrupt
        elif key == " ":
            if self.curr_card.select == SelectType.Empty:
                self.curr_card.select = SelectType.Full
            else:
                self.curr_card.select = SelectType.Empty
        elif key == "S":
            self.run_cmd()
        elif key == "C":
            Key.send(Key.CLEAN_SET, True)
            combine_sh = "".join(self.root.generate())
            print(combine_sh)
            Key.readkey()
        # maybe the arrow command cat be more OO.
        elif key == Key.UP:
            self.y = max(1, self.y - 1)
        elif key == Key.DOWN:
            self.y = min(self.y + 1, self.max_y)
        elif key == Key.LEFT:
            if self.curr.parent != None:
                self.curr = self.curr.parent
                self.update_area()
        elif key == Key.RIGHT:
            if len(self.curr_card.children) != 0:
                self.curr = self.curr_card
                self.update_area()

    @property
    def curr_card(self) -> Card:
        return self.curr.children[self.y - 1]

    def run_cmd(self):
        """Run script from root node"""
        combine_sh = "".join(self.root.generate())
        Key.send(Key.CLEAN_SET, True)
        # https://stackoverflow.com/a/567687
        proc = subprocess.Popen(["/bin/bash", "-c", combine_sh])
        proc.wait()
        raise KeyboardInterrupt

    def show_card(self, card: Card) -> None:
        """Print the card info"""
        Key.send("[%s] " % card.select.value[0])
        Key.send_color("%s" % (card.name), card.select.value[1])
        if len(card.children) != 0:
            Key.send(" >")
        Key.send("\r\n", True)

    def display(self) -> None:
        """Clean the screen and print a list of cards from the current cassette"""
        # clean screen and print the banner
        Key.send(Key.CLEAN_SET + Kickback.banner)
        for card in self.curr.children:
            self.show_card(card)
        # print bottom message
        Key.setpos(999, 1)
        Key.send(self.bottom_msg)
        self.flushpos()

    def flushpos(self) -> None:
        Key.setpos(self.y + Kickback.offset_y, self.x)


if __name__ == "__main__":
    compress_data: bytes
    if "compress_data" in globals():
        raw_data = yaml.safe_load(zlib.decompress(compress_data))
        Kickback(raw_data).run()
