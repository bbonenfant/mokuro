from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Sequence, Optional, Union

import fire
from loguru import logger

from mokuro import MokuroGenerator
from mokuro.volume import Volume


def run(*paths: str | Path,
        parent_dir: Optional[Union[str, Path]] = None,
        pretrained_model_name_or_path: str = 'kha-white/manga-ocr-base',
        force_cpu: bool = False,
        disable_confirmation: bool = False,
        disable_ocr: bool = False,
        ignore_errors: bool = False,
        no_cache: bool = True,
        unzip: bool = False,
        as_one_file: bool = True,
        ):
    """
    Process manga volumes with mokuro.

    Args:
        paths: Paths to manga volumes. Volume can ba a directory, a zip file or a cbz file.
        parent_dir: Parent directory to scan for volumes. If provided, all volumes inside this directory will be processed.
        pretrained_model_name_or_path: Name or path of the manga-ocr model.
        force_cpu: Force the use of CPU even if CUDA is available.
        disable_confirmation: Disable confirmation prompt. If False, the user will be prompted to confirm the list of volumes to be processed.
        disable_ocr: Disable OCR processing. Generate mokuro/HTML files without OCR results.
        ignore_errors: Continue processing volumes even if an error occurs.
        no_cache: Do not use cached OCR results from previous runs (_ocr directories).
        unzip: Extract volumes in zip/cbz format in their original location.
        disable_html: Disable legacy HTML output. If True, acts as if --unzip is True.
        as_one_file: Applies only to legacy HTML. If False, generate separate CSS and JS files instead of embedding them in the HTML file.
    """

    if disable_ocr:
        logger.info('Running with OCR disabled')

    logger.info('Scanning paths...')

    normalized_paths = []
    for path in paths:
        path_normalized = Path(path).expanduser().absolute()
        if not path_normalized.exists():
            logger.error(f'Invalid path: {path_normalized}')
            return
        normalized_paths.append(path_normalized)

    if parent_dir is not None:
        for p in Path(parent_dir).expanduser().absolute().iterdir():
            if (p not in normalized_paths and
                    (p.is_dir() and p.stem != '_ocr') or
                    (p.is_file() and p.suffix.lower() in {'.zip', '.cbz'})
            ):
                normalized_paths.append(p)

    volumes = [Volume(path) for path in normalized_paths]

    if len(volumes) == 0:
        logger.error('Found no paths to process. Did you set the paths correctly?')
        return

    print(f'\nFound {len(volumes)} volumes:\n')
    for volume in volumes:
        print(volume)

    msg = '\nEach of the paths above will be treated as one volume.\n'
    print(msg)

    if not disable_confirmation:
        inp = input('\nContinue? [yes/no] ')
        if inp.lower() not in ('y', 'yes'):
            return

    mg = MokuroGenerator(
        pretrained_model_name_or_path=pretrained_model_name_or_path,
        force_cpu=force_cpu,
        disable_ocr=disable_ocr,
    )

    num_sucessful = 0
    for i, volume in enumerate(volumes):
        logger.info(f'Processing {i + 1}/{len(volumes)}: {volume.path}')

        try:
            mg.process_volume(volume, ignore_errors=ignore_errors, no_cache=no_cache)
        except Exception:
            logger.exception(f'Error while processing {volume.path}')
        else:
            num_sucessful += 1

    logger.info(f'Processed successfully: {num_sucessful}/{len(volumes)}')


if __name__ == '__main__':
    fire.Fire(run)
