import imageio as iio
import logging
import numpy as np

from dataclasses import dataclass
from typing import Dict

from .common import dist2, Vec2


logger = logging.getLogger(__name__)


def preprocess_image(img):
    return np.squeeze(img[:, :, 0] == 0).astype(np.uint8), \
           np.squeeze(img[:, :, 1] > 0).astype(np.uint8)


@dataclass
class Texture:
    width: int
    height: int
    frames: int
    data: np.array
    mask: np.array

    def __str__(self) -> str:
        return f'<Texture: size={self.width}x{self.height}, frames={self.frames}>'


class TextureManager:
    READ_PARAMS = {'pilmode': 'LA'}
    textures = {}

    @classmethod
    def init(cls, config: Dict):
        for key, params in config.items():
            typ = params["type"]
            if typ == "circle":
                size = params["size"]
                texture = TextureManager.from_circle(size)
            elif typ == "png":
                fname = params["filename"]
                texture = TextureManager.from_png(fname)
            elif typ == "gif":
                fname = params["filename"]
                texture = TextureManager.from_gif(fname)
            
            cls.add_texture(key, texture)

        cls.dump()

    @classmethod
    def dump(cls):
        logger.info('TextureManager contents:')
        for key, texture in cls.textures.items():
            logger.info(f'{key} - {str(texture)}')

    @classmethod
    def add_texture(cls, key, texture):
        cls.textures[key] = texture

    @classmethod
    def get(cls, key):
        return cls.textures[key]

    @staticmethod
    def from_circle(diameter: int) -> Texture:
        radius = diameter // 2
        center = Vec2(diameter // 2, diameter // 2)
        data = np.zeros((diameter, diameter), dtype=np.uint8)
        mask = np.zeros((diameter, diameter), dtype=np.uint8)
        for row in range(diameter):
            for col in range(diameter):
                if dist2(Vec2(col, row), center) < radius ** 2:
                    data[row, col] = 1
                    mask[row, col] = 1
        return Texture(width=diameter, height=diameter, frames=1, data=data, mask=mask)

    @staticmethod
    def blank() -> 'Texture':
        return Texture(width=0, height=0, frames=1, data=np.array([]), mask=np.array([]))

    @classmethod
    def from_png(cls, fname: str) -> Texture:
        img = iio.imread(fname, **cls.READ_PARAMS)
        data, mask = preprocess_image(img)
        height, width = data.shape
        logger.info(f'Read PNG texture from {fname} - size {width}x{height}')
        return Texture(width=width, height=height, frames=1, data=data, mask=mask)

    @classmethod
    def from_gif(cls, fname: str, **kwargs: Dict) -> Texture:
        im = iio.get_reader(fname, **cls.READ_PARAMS)
        frames, masks = [], []
        for i in range(len(im)):
            frame_data, frame_mask = preprocess_image(im.get_data(i))
            frames.append(frame_data)
            masks.append(frame_mask)
        data = np.dstack(frames)
        mask = np.dstack(masks)
        height, width, n_frames = data.shape
        logger.info(f'Read GIF texture from {fname} - {n_frames} frames of size {width}x{height}')
        return Texture(width=width, height=height, frames=n_frames, data=data, mask=mask)