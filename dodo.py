from pathlib import Path
import sys

root_dir = Path(__file__).parent.resolve()
src_py_dir = root_dir / 'src_py'

sys.path = [str(src_py_dir), *sys.path]

from src_doit import *  # NOQA
import hat.doit.common  # NOQA

DOIT_CONFIG = hat.doit.common.init(python_paths=[src_py_dir],
                                   default_tasks=['build'])
