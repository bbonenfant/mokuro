import json
import shutil
import zipfile
from pathlib import Path

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


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def dump_json(obj, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, cls=NumpyEncoder)


def imread(path) -> np.ndarray | None:
    """cv2.imread, but works with unicode paths"""
    image = Image.open(path).convert('RGB')
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def get_path_format(path: Path):
    if path.is_dir():
        return ''
    else:
        return path.suffix.lower()


def unzip(path_src: Path, path_dst: Path, correct_duplicated_root=True):
    with zipfile.ZipFile(path_src, 'r') as zip_ref:
        zip_ref.extractall(path_dst)

    if correct_duplicated_root:
        # check if there's only one directory in the extracted directory and it has the same name as the archive
        extracted_content = list(path_dst.iterdir())
        if len(extracted_content) == 1:
            extracted_dir = extracted_content[0]
            if extracted_dir.is_dir():
                archive_name = path_src.stem  # remove extension
                if archive_name == extracted_dir.name:
                    for item in extracted_dir.iterdir():
                        shutil.move(str(item), str(path_dst))
                    extracted_dir.rmdir()
