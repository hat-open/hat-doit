from pathlib import Path

from hat.doit import common
from hat.doit.py import (get_task_build_wheel,
                         get_task_create_pip_requirements,
                         run_flake8)


__all__ = ['task_clean_all',
           'task_build',
           'task_check',
           'task_pip_requirements']


build_dir = Path('build')
src_py_dir = Path('src_py')


def task_clean_all():
    """Clean all"""
    return {'actions': [(common.rm_rf, [build_dir])]}


def task_build():
    """Build"""
    return get_task_build_wheel(src_dir=src_py_dir,
                                build_dir=build_dir)


def task_check():
    """Check"""
    return {'actions': [(run_flake8, [src_py_dir])]}


def task_pip_requirements():
    """Create pip requirements"""
    return get_task_create_pip_requirements()
