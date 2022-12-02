import yaml
import json
import sys

MENU_LIST_STR = 'menu: list'

with open('script.yml', 'r') as file:
    script: dict = yaml.load(file, Loader=yaml.FullLoader)
    menu = [[False, k, v] for k, v in script.items()]

if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'debug':
        import kickback
        kb = kickback.Kickback(menu)
        kb.run()
    else:
        import python_minifier
        with open('./kickback.py', 'r', encoding='utf-8') as f:
            kickback_source = f.read()
            menu_str = json.dumps(menu).replace('false,', 'False,')
            kickback_source = kickback_source.replace(
                MENU_LIST_STR, MENU_LIST_STR + '=' + menu_str)
            kickback_mini = python_minifier.minify(
                kickback_source, rename_globals=True)
            with open('./kb.py', 'w') as mini_file:
                mini_file.write(kickback_mini)
