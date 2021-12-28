import logging
import pygame

logger = logging.getLogger(__name__)

class SoundManager:
    def __init__(self, sound_config):
        pygame.mixer.init()

        self.sounds = {}
        for name, path in sound_config.items():
            self.add(name, path)
            logger.info(f'Added sound {name}:' + 
                        f' length={self.sounds[name].get_length():.3f},' +
                        f' volume={self.sounds[name].get_volume()}')

    def add(self, name, path):
        self.sounds[name] = pygame.mixer.Sound(path)

    def play(self, name):
        logger.info(f'Playing sound {self.sounds[name]}')
        ch = self.sounds[name].play()
        # TODO: is it ok to leave channel open? otherwise blocks some animations
        # while ch.get_busy():
        #     pygame.time.delay(100)