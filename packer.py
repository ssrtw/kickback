import argparse
import json
import yaml

MENU_LIST_STR = 'menu: list'


def load_script() -> dict:
    with open('script.yml', 'r') as file:
        script: dict = yaml.load(file, Loader=yaml.FullLoader)
    return script


def main():
    parser = argparse.ArgumentParser(description='init linux TUI tool.')
    parser.add_argument('-d', '--debug', help='debug script', type=bool, default=True)
    parser.add_argument('-b', '--build', help='build minifier script', type=bool)
    args = parser.parse_args()
    menu: dict = load_script()

    if args.debug == True:
        from kickback import Kickback
        kb = Kickback(menu)
        kb.run()
    else:
        import python_minifier

        with open('./kickback.py', 'r', encoding='utf-8') as f:
            kickback_source = f.read()
            menu_str = json.dumps(menu).replace('false,', 'False,')
            kickback_source = kickback_source.replace(MENU_LIST_STR, MENU_LIST_STR + '=' + menu_str)
            kickback_mini = python_minifier.minify(kickback_source, rename_globals=True)
            with open('./kb.py', 'w') as mini_file:
                mini_file.write(kickback_mini)


if __name__ == '__main__':
    main()
