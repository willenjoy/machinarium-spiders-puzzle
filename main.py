import argparse
import json
import sys

from curses import wrapper
from src import Game
from typing import Dict


CONFIG_FILE = 'config.json'


def merge_args_into_config(config: Dict, args: argparse.Namespace):
    if args.use_colors is not None:
        config['canvas']['colors']['use_colors'] = bool(args.use_colors)
    return config


def main(stdscr):
    parser = argparse.ArgumentParser()
    parser.add_argument('--use-colors', type=int, choices=[0, 1])
    parser.add_argument('--config-file', type=str, default=CONFIG_FILE)
    args = parser.parse_args(sys.argv[1:])

    with open(args.config_file, 'r') as f:
        config = json.load(f)
    config = merge_args_into_config(config, args)
    
    game = Game(stdscr, config)
    game.run()
        

if __name__ == "__main__":
    wrapper(main)