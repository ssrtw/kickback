import argparse
from argparse import BooleanOptionalAction as boa
import yaml
import zlib
import codecs

COMPRESS_DATA_STR = "compress_data: bytes"

parser = argparse.ArgumentParser(description="Pack Kickback TUI script.")
parser.add_argument("-r", "--run", help="run kickback", action=boa, default=True)
parser.add_argument("-p", "--pack", help="pack kickback", action=boa)


def compress_str(raw_str: str) -> str:
    compress_bytes = zlib.compress(raw_str.encode(), level=9)
    escape_str = codecs.escape_encode(compress_bytes)[0].decode()
    return escape_str.replace('"', '\\"')


def read_script(compress=False) -> dict | bytes:
    with open("script.yml", "r") as file:
        if compress:
            return compress_str(file.read())
        else:
            return yaml.safe_load(file)


def pack_script():
    import python_minifier

    data: bytes = read_script(True)
    with open("./kickback.py", "r") as f:
        kb_src = f.read()
    pos = kb_src.find(COMPRESS_DATA_STR) + len(COMPRESS_DATA_STR)
    kb_src = kb_src[:pos] + f' = b"{data}"' + kb_src[pos:]
    kb_minify = python_minifier.minify(
        kb_src, remove_literal_statements=True, rename_globals=True
    )
    with open("./kb.py", "w") as mini_file:
        mini_file.write(kb_minify)


def run_script():
    from kickback import Kickback

    data: dict = read_script()
    kb = Kickback(data)
    kb.run()


def main():
    args = parser.parse_args()
    if args.pack:
        pack_script()
    elif args.run:
        run_script()


if __name__ == "__main__":
    main()
