import argparse
import json
import logging
import sys

from curses import wrapper
from src import Game
from typing import Dict


logging.basicConfig(level=logging.INFO, 
                    format='[%(levelname)s] %(filename)s:%(lineno)s - %(message)s', 
                    filemode='w', filename='log.txt')


CONFIG_FILE = 'config.json'


def merge_args_into_config(config: Dict, args: argparse.Namespace):
    if args.use_colors is not None:
        config['canvas']['colors']['use_colors'] = bool(args.use_colors)
    config['canvas']['inverse'] = args.inverse
    config['debug'] = args.debug
    return config


def launch_game(stdscr, config):
    game = Game(stdscr, config)
    return game.run()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--use-colors', type=int, choices=[0, 1])
    parser.add_argument('--inverse', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--config-file', type=str, default=CONFIG_FILE)
    args = parser.parse_args(sys.argv[1:])

    with open(args.config_file, 'r') as f:
        config = json.load(f)
    config = merge_args_into_config(config, args)
    
    config_str = json.dumps(config, indent=4)
    logging.info(f'Starting the game with the following config:\n{config_str}')

    result = wrapper(launch_game, config)
    print("Congrats, you won! :)" if result else "Game over :(")
        

if __name__ == "__main__":
    main()