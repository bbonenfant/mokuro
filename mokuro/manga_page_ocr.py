import cv2
import numpy as np
from PIL import Image
from loguru import logger
from uuid_utils import uuid7

from mokuro.cache import cache
from mokuro.utils import imread


class InvalidImage(Exception):
    def __init__(self, message="Animation file, Corrupted file or Unsupported type"):
        super().__init__(message)


class MangaPageOcr:
    def __init__(
        self,
        pretrained_model_name_or_path='kha-white/manga-ocr-base',
        force_cpu=False,
        detector_input_size=1024,
        text_height=64,
        max_ratio_vert=16,
        max_ratio_hor=8,
        anchor_window=2,
        disable_ocr=False,
    ):
        self.text_height = text_height
        self.max_ratio_vert = max_ratio_vert
        self.max_ratio_hor = max_ratio_hor
        self.anchor_window = anchor_window
        self.disable_ocr = disable_ocr

        if not self.disable_ocr:
            from .comic_text_detector.inference import TextDetector
            from manga_ocr import MangaOcr, __version__ as __manga_ocr_version__
            logger.info('Initializing text detector')
            self.text_detector = TextDetector(
                model_path=cache.comic_text_detector,
                input_size=detector_input_size,
                device='cpu',
                act='leaky',
            )
            self.mocr = MangaOcr(pretrained_model_name_or_path, force_cpu)
            self.mocr_version = __manga_ocr_version__

    def __call__(self, img_path):
        img = imread(img_path)
        if img is None:
            raise InvalidImage()
        height, width, *_ = img.shape
        result = {'img_width': width, 'img_height': height, 'blocks': []}

        if self.disable_ocr:
            return result

        mask, mask_refined, blk_list = self.text_detector(img, refine_mode=1, keep_undetected_mask=True)
        for blk_idx, blk in enumerate(blk_list):
            result_blk = {
                "uuid": uuid7().hex,
                'box': list(blk.xyxy),
                'vertical': blk.vertical,
                'font_size': int(blk.font_size),  # Font size in pixels should be integer.
                'lines_coords': [],
                'lines': [],
            }

            for line_idx, line in enumerate(blk.lines_array()):
                if blk.vertical:
                    max_ratio = self.max_ratio_vert
                else:
                    max_ratio = self.max_ratio_hor

                line_crops, cut_points = self.split_into_chunks(
                    img,
                    mask_refined,
                    blk,
                    line_idx,
                    textheight=self.text_height,
                    max_ratio=max_ratio,
                    anchor_window=self.anchor_window
                )

                line_text = ''
                for line_crop in line_crops:
                    if blk.vertical:
                        line_crop = cv2.rotate(line_crop, cv2.ROTATE_90_CLOCKWISE)
                    line_text += self.mocr(Image.fromarray(line_crop))
                line_text = (line_text
                    .replace("．．．", "⋯")  # replace triple full stop with proper ellipse
                    .replace("。。。", "⋯")  # replace triple full stop with proper ellipse
                    .replace("！！", "‼︎")  # replace double ! with single character.
                    .replace("？！", "⁈")  # replace ? ! with single character.
                    .replace("！？", "⁉︎")  # replace ! ? with single character.
                )
                result_blk['lines_coords'].append(line.tolist())
                result_blk['lines'].append(line_text)

            result['blocks'].append(result_blk)

        return result

    @staticmethod
    def split_into_chunks(img, mask_refined, blk, line_idx, textheight, max_ratio=16, anchor_window=2):
        line_crop = blk.get_transformed_region(img, line_idx, textheight)

        h, w, *_ = line_crop.shape
        ratio = w / h

        if ratio <= max_ratio:
            return [line_crop], []

        else:
            # I believe this ratio check is due to this usage tip:
            #   github.com/kha-white/manga-ocr/blob/master/README.md#usage-tips
            # If this fork gets to a point where you and modify and edit the
            # OCR output directly, this can probably be removed.
            # An initial test shows that this ratio is usually exceeded for
            # non-relevant manga text.
            #logger.warning(f"ratio too big: {w} / {h} = {ratio}")
            from scipy.signal.windows import gaussian
            k = gaussian(textheight * 2, textheight / 8)

            line_mask = blk.get_transformed_region(mask_refined, line_idx, textheight)
            num_chunks = int(np.ceil(ratio / max_ratio))

            anchors = np.linspace(0, w, num_chunks + 1)[1:-1]

            line_density = line_mask.sum(axis=0)
            line_density = np.convolve(line_density, k, 'same')
            line_density /= line_density.max()

            anchor_window *= textheight

            cut_points = []
            for anchor in anchors:
                anchor = int(anchor)

                n0 = np.clip(anchor - anchor_window // 2, 0, w)
                n1 = np.clip(anchor + anchor_window // 2, 0, w)

                p = line_density[n0:n1].argmin()
                p += n0

                cut_points.append(p)

            return np.split(line_crop, cut_points, axis=1), cut_points
