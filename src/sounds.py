import logging
import pygame

logger = logging.getLogger(__name__)

class SoundManager:
    sounds = {}

    @classmethod
    def init(cls, sound_config):
        pygame.mixer.init()

        for name, path in sound_config.items():
            cls.add(name, path)
            logger.info(f'Added sound {name}:' + 
                        f' length={cls.sounds[name].get_length():.3f},' +
                        f' volume={cls.sounds[name].get_volume()}')

    @classmethod
    def add(cls, name, path):
        cls.sounds[name] = pygame.mixer.Sound(path)

    @classmethod
    def play(cls, name):
        logger.info(f'Playing sound {name}')
        ch = cls.sounds[name].play()
