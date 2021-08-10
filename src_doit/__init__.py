from pathlib import Path

from hat.doit import common
from hat.doit.py import build_wheel


__all__ = ['task_clean_all',
           'task_build']


build_dir = Path('build')
src_py_dir = Path('src_py')


def task_clean_all():
    """Clean all"""
    return {'actions': [(common.rm_rf, [build_dir])]}


def task_build():
    """Build"""

    def build():
        build_wheel(
            src_dir=src_py_dir,
            dst_dir=build_dir,
            src_paths=list(common.path_rglob(src_py_dir,
                                             blacklist={'__pycache__'})),
            name='hat-doit',
            description='Hat build utility functions',
            url='https://github.com/hat-open/hat-doit',
            license=common.License.APACHE2,
            packages=['hat'])

    return {'actions': [build]}
