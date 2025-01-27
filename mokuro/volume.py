import uuid
import zipfile
from pathlib import Path

from filetype import is_image
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
                and is_image(p)
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
        self._namelist = []
        with zipfile.ZipFile(self.path) as archive:
            for name in natsorted(archive.namelist()):
                path = Path(name)
                if path.suffix.lower() not in self.supported_formats:
                    continue
                with archive.open(name) as file:
                    if is_image(file.read(150)):  # Only need the first 150 bytes
                        self._namelist.append(path)


def volume_from_path(path: Path):
    path = Path(path)
    if path.suffix in ('.zip', '.cbz'):
        return VolumeZip(path)
    return Volume(path)
