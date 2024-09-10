import uuid
from enum import Enum, auto
from pathlib import Path

from loguru import logger
from natsort import natsorted

from mokuro.utils import get_path_format, load_json, dump_json, unzip


class VolumeStatus(Enum):
    UNPROCESSED = auto()
    PARTIALLY_PROCESSED = auto()
    PROCESSED = auto()

    def __str__(self):
        return {
            'UNPROCESSED': 'unprocessed',
            'PARTIALLY_PROCESSED': 'partially processed',
            'PROCESSED': 'already processed',
        }[self.name]


class Title:
    def __init__(self, path):
        self.path = path
        self._uuid = None
        self.name = path.name

    @property
    def uuid(self):
        if self._uuid is None:
            self.set_uuid()

        return self._uuid

    def set_uuid(self, update_existing=True):
        existing_title_uuids = set()

        for path_mokuro in self.path.glob('*.mokuro'):
            mokuro_data = load_json(path_mokuro)

            title_uuid = mokuro_data.get('title_uuid')
            if title_uuid is not None:
                existing_title_uuids.add(title_uuid)

        if len(existing_title_uuids) == 0:
            self._uuid = str(uuid.uuid4())
        elif len(existing_title_uuids) == 1:
            self._uuid = existing_title_uuids.pop()
        else:
            logger.warning('Incosistent title uuids; generating a new one')
            self._uuid = str(uuid.uuid4())

        if update_existing:
            for path_mokuro in self.path.glob('*.mokuro'):
                mokuro_data = load_json(path_mokuro)

                if mokuro_data.get('title_uuid') != self._uuid:
                    mokuro_data['title_uuid'] = self._uuid
                    dump_json(mokuro_data, path_mokuro)


class Volume:
    format_preference_order = ['', '.cbz', '.zip']

    def __init__(self, path_in: Path):
        self.path = path_in
        self.output_path = path_in.with_suffix(".mbz.zip")
        self.name = path_in.stem
        self.title = Title(path_in.parent)
        self.uuid = str(uuid.uuid4())

    def get_img_paths(self):
        assert self.path.is_dir()
        img_paths = natsorted(
            p.resolve() for p in self.path.glob('**/*')  # Maybe remove recursive glob.
            if p.is_file() and p.suffix.lower() in ('.avif', '.jpg', '.jpeg', '.png', '.webp')
        )
        img_paths = {p.with_suffix('').name: p for p in img_paths}
        return img_paths

    def __str__(self):
        return f'{self.path} (-)'


def get_path_mokuro(path_in: Path) -> Path:
    if path_in.is_dir():
        return path_in.parent / (path_in.name + '.mokuro')
    if path_in.is_file() and path_in.suffix.lower() in {'.zip', '.cbz'}:
        return path_in.with_suffix('.mokuro')
    raise ValueError(f"expected directory or zip file -- found: {path_in}")
