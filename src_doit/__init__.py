from pathlib import Path

from hat.doit import common
from hat.doit.py import get_task_build_wheel


__all__ = ['task_clean_all',
           'task_build']


build_dir = Path('build')
src_py_dir = Path('src_py')


def task_clean_all():
    """Clean all"""
    return {'actions': [(common.rm_rf, [build_dir])]}


def task_build():
    """Build"""
    return get_task_build_wheel(src_dir=src_py_dir,
                                build_dir=build_dir)
