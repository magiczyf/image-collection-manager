import logging
from pathlib import Path
from math import isclose
import shutil

from PIL import Image

from util import collect_images

DEFAULT_RATIOS = (
    (1.0 / 1, 'square'),
    (5.0 / 4, 'ratio 1.25'),
    (4.0 / 3, 'ratio 1.33'),
    (8.0 / 5, 'ratio 1.6'),
    (16.0 / 9, 'widescreen')
)

DEFAULT_HEIGHTS = (
    480, 720,
    1080,  # HD
    1440,  # QHD
    2160,  # 4K
    4320,  # 8k
)

logger = logging.getLogger(__name__)


def organize_duplicates(items: list, target_dir: Path = None):
    if target_dir and not target_dir.is_dir():
        raise ValueError('Target_dir must be a directory')

    for tup in items:
        tup = sorted(tup, key=lambda p: str(p).lower(), reverse=True)
        dups = enumerate(tup)
        # Take item with the shortest path as subject.
        # The subject will remain location invariant and it's name will be used
        # to rename duplicates.
        _, item_subj = next(dups)
        subj_name = item_subj.stem
        subj_suffix = item_subj.suffix
        # Use parent dir of subject if no duplicate directory is provided
        dup_dir = (item_subj.parent / 'dups') if target_dir is None else target_dir
        dup_dir.mkdir(exist_ok=True)

        # Move all duplicates into the dup_dir (including a rename)
        # This iterator will process all elements after the first (see next(..) when assigning item_subj
        for i, dup_path in dups:
            target_path = Path(dup_dir) / (subj_name + '_dup_' + str(i) + subj_suffix)
            old_path = str(dup_path)
            # Move the duplicate image into the dup folder
            dup_path.rename(target_path)
            logger.warning('Moved duplicate `{}` to `{}`'.format(old_path, str(dup_path)))


def _retrieve_output_path(dirs: dict, ratio: float, img_height: int, def_ratios: tuple, def_heights: tuple):
    # Calculate ratio and height to use (rounded upwards)
    # For example: height 480<X<=720 will be organized into height 720
    target_ratio, ratio_name = next((i for i in reversed(def_ratios) if isclose(i[0], ratio)), None)
    target_height = next((i for i in def_heights if i >= img_height), None)

    # Find the precalculated path, if any..
    # The paths are constructed by the following template:
    # [BASE]/[RATIO]/[HEIGHT]
    target_ratio_path = dirs.get(target_ratio, None)
    if not target_ratio_path:
        target_ratio_path = {
            '_base': Path(dirs['_base']) / ratio_name,
        }
        dirs[target_ratio] = target_ratio_path

    target_height_path = target_ratio_path.get(target_height, None)
    if not target_height_path:
        target_height_path = Path(target_ratio_path['_base']) / ('w' + str(target_height))
        target_ratio_path[target_height] = target_height_path
        # Make sure this directory exists!
        target_height_path.mkdir(parents=True, exist_ok=True)

    return target_height_path


def organize_images(path_list: list, recurse: bool, target_dir: Path, copy):
    images = collect_images(path_list, recurse)
    ratios = DEFAULT_RATIOS
    heights = DEFAULT_HEIGHTS

    # Will contain all path objects used to organize your images into
    output_directories = {
        '_base': target_dir,
    }

    # Will contain all move operations
    move_ops = []

    # Process all images
    for img_path in images:
        img = Image.open(img_path)
        img_width = img.width
        img_height = img.height
        img.close()
        img_ratio = float(img_width) / img_height
        target_path = _retrieve_output_path(output_directories, img_ratio, img_height,
                                            ratios, heights)
        img_name = img_path.name
        old_path = str(img_path)
        new_path = target_path / img_name
        move_ops.append((old_path, new_path))

    logger.info('Attempting to move {} images'.format(len(move_ops)))

    # Move all images
    for op in move_ops:
        old_path = op[0]
        new_path = op[1]
        # Move image to new_path
        img_path = Path(old_path)
        if not img_path.exists() or not img_path.is_file():
            logger.error('Path `{}` doesn\'t point to a valid image'.format(old_path))
            continue

        if copy:
            shutil.copy(old_path, new_path)
            logger.info('Copied image `{}` to `{}`'.format(old_path, new_path))
        else:
            img_path.rename(new_path)
            logger.warning('Moved image `{}` to `{}`'.format(old_path, new_path))
