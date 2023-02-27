from pathlib import Path
import datetime
import enum
import functools
import itertools
import multiprocessing
import os
import platform
import shutil
import subprocess
import sys
import typing

import packaging.requirements
import packaging.tags
import packaging.version


class Platform(enum.Enum):
    WINDOWS_AMD64 = ('win32', 'amd64')
    DARWIN_X86_64 = ('darwin', 'x86_64')
    LINUX_GNU_X86_64 = ('linux', 'glibc', 'x86_64')
    LINUX_GNU_AARCH64 = ('linux', 'glibc', 'aarch64')
    LINUX_GNU_ARMV7L = ('linux', 'glibc', 'armv7l')
    LINUX_MUSL_X86_64 = ('linux', 'musl', 'x86_64')
    LINUX_MUSL_AARCH64 = ('linux', 'musl', 'aarch64')


class PyVersion(enum.Enum):
    CP38 = ('cp', 3, 8)
    CP39 = ('cp', 3, 9)
    CP310 = ('cp', 3, 10)
    CP311 = ('cp', 3, 11)


class VersionType(enum.Enum):
    SEMVER = 0
    PIP = 1


class License(enum.Enum):
    APACHE2 = 'Apache-2.0'
    GPL3 = 'GPLv3'
    PROPRIETARY = 'PROPRIETARY'


now: datetime.datetime = datetime.datetime.now()


def _get_local_platform():
    machine = platform.machine().lower()

    if sys.platform == 'linux':
        libc, _ = platform.libc_ver()
        return Platform((sys.platform, libc or 'musl', machine))

    return Platform((sys.platform, machine))


local_platform: Platform = _get_local_platform()
target_platform: Platform = (Platform[os.environ['TARGET_PLATFORM'].upper()]
                             if 'TARGET_PLATFORM' in os.environ
                             else local_platform)

local_py_version: PyVersion = PyVersion((packaging.tags.interpreter_name(),
                                         sys.version_info.major,
                                         sys.version_info.minor))
target_py_version: PyVersion = (
    PyVersion[os.environ['TARGET_PY_VERSION'].upper()]
    if 'TARGET_PY_VERSION' in os.environ else local_py_version)


def init(python_paths: typing.List[os.PathLike] = [],
         default_tasks: typing.List[str] = []
         ) -> typing.Dict:
    python_paths = [str(Path(i).resolve()) for i in python_paths]
    sys.path = [*python_paths, *sys.path]
    os.environ['PYTHONPATH'] = os.pathsep.join(
        (path for path in itertools.chain(python_paths,
                                          [os.environ.get('PYTHONPATH')])
         if path))

    num_process = os.environ.get('DOIT_NUM_PROCESS')
    if num_process:
        num_process = int(num_process)
    elif sys.platform in ('darwin', 'win32'):
        num_process = 0
    else:
        num_process = multiprocessing.cpu_count()

    return {'backend': 'sqlite3',
            'default_tasks': default_tasks,
            'verbosity': 2,
            'num_process': num_process}


def mkdir_p(*paths: os.PathLike):
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def rm_rf(*paths: os.PathLike):
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        if p.is_dir():
            shutil.rmtree(str(p), ignore_errors=True)
        else:
            p.unlink()


def cp_r(src: os.PathLike, dest: os.PathLike):
    src = Path(src)
    dest = Path(dest)
    if src.is_dir():
        shutil.copytree(str(src), str(dest), dirs_exist_ok=True)
    else:
        shutil.copy2(str(src), str(dest))


def path_rglob(path: Path,
               patterns: typing.List[str] = ['*'],
               blacklist: typing.Set[str] = set()):
    if path.name in blacklist:
        return
    if not path.is_dir():
        yield path
    for i in set(itertools.chain.from_iterable(path.glob(pattern)
                                               for pattern in patterns)):
        yield from path_rglob(i, patterns, blacklist)


@functools.lru_cache
def get_version(version_type: VersionType = VersionType.SEMVER,
                version_path: Path = Path('VERSION')
                ) -> str:
    version = version_path.read_text('utf-8').strip()

    if version.endswith('dev'):
        version += now.strftime("%Y%m%d")

    if version_type == VersionType.SEMVER:
        return version

    elif version_type == VersionType.PIP:
        return str(packaging.version.Version(version))

    raise ValueError()


class StaticWebServer:

    def __init__(self, static_dir: os.PathLike, port: int):
        self._p = subprocess.Popen([sys.executable,
                                    '-m', 'http.server',
                                    '-b', '127.0.0.1',
                                    '-d', str(static_dir),
                                    str(port)],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._p.terminate()
