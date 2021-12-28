import json

from curses import wrapper
from src import Game


CONFIG_FILE = 'config.json'


def main(stdscr):
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    game = Game(stdscr, config)
    game.run()
        

if __name__ == "__main__":
    wrapper(main)