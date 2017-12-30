import mimetypes
import logging
import sys
import contextlib
import pathlib
import tempfile

import click
import diskcache

from duplicate_finder import do_filter_images
from organizer import organize_duplicates, organize_images

logger = logging.getLogger(__name__)

CONTEXT_SETTINGS = dict(
    default_map={'filter': {}, 'organize': {}}
)


@contextlib.contextmanager
def _setup_cache(location: pathlib.Path, **kwargs):
    cache_obj = None
    try:
        if not location:
            # Construct new cache location in temp folder
            location = pathlib.Path(tempfile.gettempdir())
            location = location / 'image-collection-manager'

        cache_obj = diskcache.FanoutCache(str(location), **kwargs)
        yield cache_obj
    finally:
        if cache_obj:
            cache_obj.close()


@click.group(invoke_without_command=False, context_settings=CONTEXT_SETTINGS)
@click.pass_context
def cli(ctx):
    # Initialise logging
    logging.basicConfig(level=logging.WARNING, stream=sys.stdout,
                        # Or use filename='log.txt'
                        format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')

    logging.getLogger('duplicate_finder').setLevel(logging.INFO)
    logging.getLogger('organizer').setLevel(logging.INFO)
    logger.setLevel(logging.INFO)

    # Initialise file kind detection
    mimetypes.init()
    # Create context object for passing data into subcommands
    if ctx.obj is None:
        ctx.obj = {}

    if ctx.invoked_subcommand is not None:
        logger.info('Starting')


@cli.command('filter')
@click.argument('sources', nargs=-1, type=click.Path(exists=True, file_okay=True, dir_okay=True, resolve_path=True))
@click.option('--recurse', '-r', is_flag=True, default=False)
@click.option('--dup_dir', '-d', default=None,
              type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--cache_dir', type=click.Path(exists=False, file_okay=False, dir_okay=True, writable=True,
                                             readable=True, resolve_path=True))
@click.pass_context
def filter_duplicates(ctx, sources, recurse, dup_dir, cache_dir):
    with _setup_cache(cache_dir, tag_index=True) as cache:
        duplicates = do_filter_images(sources, recurse, cache)
        logger.info('Found {} images which have at least one duplicate'.format(len(duplicates)))
        organize_duplicates(duplicates, dup_dir)
        logger.info('Filtering duplicates finished!')


@cli.command('organize')
@click.argument('sources', nargs=-1, type=click.Path(exists=True, file_okay=True, dir_okay=True, resolve_path=True))
@click.argument('target', nargs=1, type=click.Path(exists=False, file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--copy/--move', default=True, help="Only use copy (Default) or move operations.")
@click.option('--recurse', '-r', is_flag=True, default=False)
@click.pass_context
def organize(ctx, sources, target, copy, recurse):
    organize_images(sources, recurse, target, copy)
    logger.info('Organizing images finished!')


if __name__ == "__main__":
    cli()