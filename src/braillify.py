"""
Braille unicode for refining console graphics

http://www.alanwood.net/unicode/braille_patterns.html
https://github.com/asciimoo/drawille

dots:
   ,___,
   |1 4|
   |2 5|
   |3 6|
   |7 8|
   `````
"""

import numpy as np

from typing import List


BRAILLE_OFFSET = 0x2800
H_STEP = 2
V_STEP = 4
PIXEL_MAP = np.array([
    [0x01, 0x08],
    [0x02, 0x10],
    [0x04, 0x20],
    [0x40, 0x80]
])


def braille_cell(cell: np.array, inverse: bool) -> str:
    value = np.sum(cell * PIXEL_MAP)
    if inverse:
        value = 255 - value
    return chr(BRAILLE_OFFSET + value)


def braillify(frame: np.array, inverse: bool) -> str:
    rows, cols = frame.shape    

    braille = []
    for row in range(0, rows, V_STEP):
        braille_row = ''
        for col in range(0, cols, H_STEP):
            braille_row += braille_cell(frame[row:row+V_STEP, col:col+H_STEP], inverse)
        braille.append(braille_row)

    return braille