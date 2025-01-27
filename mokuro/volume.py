import uuid
import zipfile
from pathlib import Path

from natsort import natsorted


class Volume:
    supported_formats = ('.avif', '.jpg', '.jpeg', '.png', '.webp')

    def __init__(self, path_in: Path):
        self.path = path_in
        self.output_path = path_in.with_suffix(".mbz.zip")
        self.name = path_in.stem
        self.title = path_in.parent.name
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
        formats = {p.suffix for p in self.namelist}
        return f'{self.path} | {len(self.namelist)} images | Format: {"/".join(formats)}'


class VolumeZip(Volume):

    def get_img_paths(self):
        with zipfile.ZipFile(self.path) as archive:
            for path in self.namelist:
                img_path = zipfile.Path(archive, at=str(path))
                img_path.read = img_path.read_bytes  # a bit of a hack but works
                yield path.stem, img_path

    def _set_namelist(self):
        with zipfile.ZipFile(self.path) as archive:
            paths = natsorted(
                Path(name) for name in archive.namelist()
                if not name.startswith('__MACOSX/')  # Filter out bad files
            )
            self._namelist = [
                path for path in paths
                if path.suffix.lower() in Volume.supported_formats
                   and len(path.parts) == 1  # Only look for "root" files
            ]

def volume_from_path(path: Path):
    path = Path(path)
    if path.suffix == '.zip':
        return VolumeZip(path)
    return Volume(path)
