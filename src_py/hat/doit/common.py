from pathlib import Path
import datetime
import enum
import functools
import itertools
import multiprocessing
import os
import platform
import shutil
import sys
import typing

import packaging.requirements
import packaging.tags
import packaging.version
import tomli


class Platform(enum.Enum):
    WINDOWS_AMD64 = ('win32', 'amd64')
    DARWIN_X86_64 = ('darwin', 'x86_64')
    LINUX_GNU_X86_64 = ('linux', 'glibc', 'x86_64')
    LINUX_GNU_AARCH64 = ('linux', 'glibc', 'aarch64')
    LINUX_GNU_ARMV7L = ('linux', 'glibc', 'armv7l')
    LINUX_MUSL_X86_64 = ('linux', 'musl', 'x86_64')
    LINUX_MUSL_AARCH64 = ('linux', 'musl', 'aarch64')


class PyVersion(enum.Enum):
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


def init(python_paths: typing.Iterable[os.PathLike] = [],
         default_tasks: list[str] = [],
         verbosity: int = 2
         ) -> dict:
    add_python_paths(*python_paths)
    return {'backend': 'sqlite3',
            'default_tasks': default_tasks,
            'verbosity': verbosity,
            'num_process': _get_num_process()}


def get_conf(path: Path = Path('pyproject.toml')) -> typing.Any:
    conf_str = path.read_text()
    return tomli.loads(conf_str)


def add_python_paths(*paths: os.PathLike):
    paths = [str(Path(path).resolve()) for path in paths]
    if not paths:
        return

    sys.path = [*paths, *sys.path]
    os.environ['PYTHONPATH'] = os.pathsep.join(
        [*paths, os.environ['PYTHONPATH']] if os.environ.get('PYTHONPATH')
        else paths)


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
               patterns: list[str] = ['*'],
               blacklist: set[str] = set()):
    if path.name in blacklist:
        return
    if not path.is_dir():
        yield path
    for i in set(itertools.chain.from_iterable(path.glob(pattern)
                                               for pattern in patterns)):
        yield from path_rglob(i, patterns, blacklist)


@functools.lru_cache
def get_version(version_type: VersionType = VersionType.SEMVER,
                version: str | None = None
                ) -> str:
    if version is None:
        conf = get_conf()
        version = conf['project']['version']

    if version.endswith('dev'):
        version += now.strftime("%Y%m%d")

    if version_type == VersionType.SEMVER:
        return version

    elif version_type == VersionType.PIP:
        return str(packaging.version.Version(version))

    raise ValueError()


def get_task_json_schema_repo(src_paths: typing.Iterable[Path],
                              dst_path: Path,
                              *,
                              file_dep=[],
                              task_dep=[]
                              ) -> dict:
    import hat.json

    src_paths = list(src_paths)

    def generate():
        repo = hat.json.SchemaRepository(*src_paths)
        data = repo.to_json()
        hat.json.encode_file(data, dst_path, indent=None)

    return {'actions': [generate],
            'file_dep': [*src_paths, *file_dep],
            'task_dep': task_dep,
            'targets': [dst_path]}


def get_task_sbs_repo(src_paths: typing.Iterable[Path],
                      dst_path: Path,
                      *,
                      file_dep=[],
                      task_dep=[]
                      ) -> dict:
    import hat.sbs
    import hat.json

    src_paths = list(src_paths)

    def generate():
        repo = hat.sbs.Repository(*src_paths)
        data = repo.to_json()
        hat.json.encode_file(data, dst_path, indent=None)

    return {'actions': [generate],
            'file_dep': [*src_paths, *file_dep],
            'task_dep': task_dep,
            'targets': [dst_path]}


def _get_num_process():
    num_process = os.environ.get('DOIT_NUM_PROCESS')

    if num_process:
        return int(num_process)

    if sys.platform in ('darwin', 'win32'):
        return 0

    return multiprocessing.cpu_count()
