import uuid
import zipfile
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
    supported_formats = ('.avif', '.jpg', '.jpeg', '.png', '.webp')

    def __init__(self, path_in: Path):
        self.path = path_in
        self.output_path = path_in.with_suffix(".mbz.zip")
        self.name = path_in.stem
        self.title = Title(path_in.parent)
        self.uuid = str(uuid.uuid4())
        self._namelist = None

    @property
    def namelist(self):
        if self._namelist is None:
            self._set_namelist()
        return self._namelist

    def get_img_paths(self):
        for path in self.namelist:
            yield path.stem, path

    def _set_namelist(self):
        assert self.path.is_dir()
        self._namelist = natsorted(
            p.resolve() for p in self.path.iterdir()
            if p.is_file() and p.suffix.lower() in Volume.supported_formats
        )

    def __str__(self):
        return f'{self.path} (-)'


class VolumeZip(Volume):

    def get_img_paths(self):
        with zipfile.ZipFile(self.path) as archive:
            for path in self.namelist:
                img_path = zipfile.Path(archive, at=str(path))
                img_path.read = img_path.read_bytes  # a bit of a hack but works
                yield path.stem, img_path

    def _set_namelist(self):
        with zipfile.ZipFile(self.path) as archive:
            paths = natsorted(map(Path, archive.namelist()))
            self._namelist = [
                path for path in paths
                if path.suffix.lower() in Volume.supported_formats
            ]

def volume_from_path(path: Path):
    path = Path(path)
    if path.suffix == '.zip':
        return VolumeZip(path)
    return Volume(path)
