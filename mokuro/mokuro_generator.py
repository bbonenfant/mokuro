from datetime import datetime
import json
from zipfile import ZipFile, ZIP_DEFLATED

from loguru import logger
from tqdm.autonotebook import tqdm

from mokuro import __version__, __comic_text_detector_version__
from mokuro.manga_page_ocr import MangaPageOcr
from mokuro.utils import NumpyEncoder
from mokuro.volume import Volume


class MokuroGenerator:
    def __init__(
        self,
        pretrained_model_name_or_path='kha-white/manga-ocr-base',
        force_cpu=False,
        disable_ocr=False,
        **kwargs
    ):
        self.pretrained_model_name_or_path = pretrained_model_name_or_path
        self.force_cpu = force_cpu
        self.disable_ocr = disable_ocr
        self.kwargs = kwargs
        self._mpocr: MangaPageOcr | None = None

    def init_models(self) -> MangaPageOcr:
        if self._mpocr is None:
            self._mpocr = MangaPageOcr(
                self.pretrained_model_name_or_path,
                force_cpu=self.force_cpu,
                disable_ocr=self.disable_ocr,
                **self.kwargs
            )
        return self._mpocr

    def process_volume(self, volume: Volume, ignore_errors=False, no_cache=False):
        mpocr_model = self.init_models()
        timestamp = datetime.now().isoformat()
        metadata = {
            'version': (
                f"mokuro:{__version__};"
                f"comic_text_detector: {__comic_text_detector_version__};"
                f"manga_ocr: {mpocr_model.mocr_version};"
            ),
            'created_at': timestamp,
            'modified_at': timestamp,
            'series': volume.title.name,
            'title': volume.name,
            'volume': volume.name,
            'volume_uuid': volume.uuid,
            'pages': [],
        }
        with ZipFile(volume.output_path, "w", ZIP_DEFLATED, compresslevel=9) as output:
            for img_path in tqdm(volume.get_img_paths().values(), desc="Processing pages..."):
                try:
                    result = mpocr_model(img_path)
                except Exception as e:
                    if not ignore_errors:
                        raise e
                    logger.error(e)
                else:
                    ocr_path = f"_ocr/{img_path.with_suffix('.json').name}"
                    output.writestr(ocr_path, safe_json_dumps(result))
                    output.writestr(img_path.name, img_path.read_bytes())
                    metadata['pages'].append((img_path.name, ocr_path))
            output.writestr("mokuro-metadata.json", json.dumps(metadata))


def safe_json_dumps(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, cls=NumpyEncoder)
