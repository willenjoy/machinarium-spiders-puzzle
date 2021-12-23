"""
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

from typing import List

BRAILLE_OFFSET = 0x2800
H_STEP = 2
V_STEP = 4
PIXEL_MAP = [(0x01, 0x08),
             (0x02, 0x10),
             (0x04, 0x20),
             (0x40, 0x80)]


def braillify(frame: List[List[int]]):
    rows = len(frame)
    cols = len(frame[0])

    braille = []
    for row in range(0, rows, V_STEP):
        braille_row = []
        for col in range(0, cols, H_STEP):
            braille_cell = BRAILLE_OFFSET
            for i in range(V_STEP):
                for j in range(H_STEP):
                    if frame[row + i][col + j] == 1:
                        braille_cell |= PIXEL_MAP[i][j]
            braille_row.append(braille_cell) 
        braille.append(braille_row)
    
    return braille