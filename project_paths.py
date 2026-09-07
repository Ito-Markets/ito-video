"""Project footage references without machine-specific absolute paths.

Set ITO_FOOTAGE_ROOT or pass --footage-root to the project scripts. The default
is assets/raw under this checkout. Manifests use footage:// paths relative to
that root; generated assets remain relative to the checkout.
"""
from __future__ import annotations

import os
from pathlib import Path


def footage_root(project: Path, configured: str | None = None) -> Path:
    value = configured or os.environ.get('ITO_FOOTAGE_ROOT')
    root = Path(value).expanduser() if value else project / 'assets/raw'
    if not root.is_absolute():
        root = project / root
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(
            'Footage directory is missing. Set ITO_FOOTAGE_ROOT or --footage-root '
            'to an existing folder, or populate assets/raw.'
        )
    return root


def portable_source(path: Path, root: Path) -> str:
    return 'footage://' + path.resolve().relative_to(root.resolve()).as_posix()


def resolve_source(source: str, project: Path, root: Path) -> Path:
    if source.startswith('footage://'):
        path = (root / source[len('footage://'):]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('Footage reference must stay inside the configured root')
    else:
        path = Path(source).expanduser()
        if not path.is_absolute():
            path = project / path
            if not path.is_file():
                path = project / 'assets/raw' / source
        path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError('Source media is missing; check the manifest and footage root')
    return path


def protect_output(path: Path, overwrite: bool) -> None:
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError('Output paths must not be symbolic links')
    if path.exists() and not overwrite:
        raise FileExistsError(f'Output already exists: {path.name}; use --overwrite explicitly')


def manifest_output(path: Path, overwrite: bool) -> None:
    if path.suffix.lower() != '.json':
        raise ValueError('Manifest output must be a JSON file')
    protect_output(path, overwrite)
