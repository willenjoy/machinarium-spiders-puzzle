from curses import wrapper
from src import Game


CONFIG = {
    'sounds': {
        'shoot': 'assets/sounds/shoot.wav',
        'block_hit': 'assets/sounds/block_hit.wav',
        'player_hit': 'assets/sounds/player_hit.wav',
        'spider_hit': 'assets/sounds/spider_hit.wav'
    }
}


def main(stdscr):
    game = Game(stdscr, CONFIG['sounds'])
    game.run()
        


if __name__ == "__main__":
    wrapper(main)