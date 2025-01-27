import json

import cv2
import numpy as np
import pillow_avif
from PIL import Image


class NumpyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.generic):
            return o.item()
        return json.JSONEncoder.default(self, o)


def imread(path) -> np.ndarray | None:
    """cv2.imread, but works with Unicode paths"""
    image = Image.open(path).convert('RGB')
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
