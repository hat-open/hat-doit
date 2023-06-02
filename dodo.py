from pathlib import Path
import sys

build_dir = Path('build')
src_py_dir = Path('src_py')

sys.path = [str(src_py_dir.resolve()), *sys.path]

from hat.doit import common  # NOQA
from hat.doit.py import build_wheel  # NOQA


DOIT_CONFIG = common.init(python_paths=[src_py_dir],
                          default_tasks=['build'])


def task_clean_all():
    """Clean all"""
    return {'actions': [(common.rm_rf, [build_dir])]}


def task_build():
    """Build"""

    def build():
        build_wheel(
            src_dir=src_py_dir,
            dst_dir=build_dir,
            name='hat-doit',
            description='Hat build utility functions',
            url='https://github.com/hat-open/hat-doit',
            license=common.License.APACHE2)

    return {'actions': [build]}
