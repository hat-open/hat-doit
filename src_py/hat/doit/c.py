from pathlib import Path
import enum
import itertools
import os
import sys
import typing

from . import common


class Platform(enum.Enum):
    WINDOWS = 'win32'
    DARWIN = 'darwin'
    LINUX = 'linux'


def get_exe_suffix(platform: Platform) -> str:
    if platform == Platform.WINDOWS:
        return '.exe'

    if platform == Platform.DARWIN:
        return ''

    if platform == Platform.LINUX:
        return ''

    raise ValueError('unsupported platform')


def get_lib_suffix(platform: Platform) -> str:
    if platform == Platform.WINDOWS:
        return '.dll'

    if platform == Platform.DARWIN:
        return '.dylib'

    if platform == Platform.LINUX:
        return '.so'

    raise ValueError('unsupported platform')


local_platform: Platform = Platform(sys.platform)
local_exe_suffix: str = get_exe_suffix(local_platform)
local_lib_suffix: str = get_lib_suffix(local_platform)


def get_cpp(platform: Platform) -> str:
    if platform == local_platform:
        return os.environ.get('CPP', 'cpp')

    if (local_platform, platform) == (Platform.LINUX, Platform.WINDOWS):
        return 'x86_64-w64-mingw32-cpp'

    raise ValueError('unsupported platform')


def get_cc(platform: Platform) -> str:
    if platform == local_platform:
        return os.environ.get('CC', 'cc')

    if (local_platform, platform) == (Platform.LINUX, Platform.WINDOWS):
        return 'x86_64-w64-mingw32-cc'

    raise ValueError('unsupported platform')


def get_ld(platform: Platform) -> str:
    return get_cc(platform)


class CBuild:

    def __init__(self,
                 src_paths: typing.List[Path],
                 build_dir: Path, *,
                 src_dir: Path = Path('.'),
                 platform: Platform = local_platform,
                 cpp_flags: typing.List[str] = [],
                 cc_flags: typing.List[str] = [],
                 ld_flags: typing.List[str] = [],
                 task_dep: typing.List[str] = []):
        self._src_paths = src_paths
        self._build_dir = build_dir
        self._src_dir = src_dir
        self._platform = platform
        self._cpp_flags = cpp_flags
        self._cc_flags = cc_flags
        self._ld_flags = ld_flags
        self._task_dep = task_dep

    def get_task_exe(self, exe_path: Path) -> typing.Dict:
        obj_paths = [self._get_obj_path(src_path)
                     for src_path in self._src_paths]
        yield {'name': str(exe_path),
               'actions': [(common.mkdir_p, [exe_path.parent]),
                           [get_ld(self._platform),
                            *(str(obj_path) for obj_path in obj_paths),
                            '-o', str(exe_path),
                            *self._ld_flags]],
               'file_dep': obj_paths,
               'task_dep': self._task_dep,
               'targets': [exe_path]}

    def get_task_lib(self, lib_path: Path) -> typing.Dict:
        obj_paths = [self._get_obj_path(src_path)
                     for src_path in self._src_paths]
        shared_flag = ('-mdll' if self._platform == Platform.WINDOWS
                       else '-shared')
        yield {'name': str(lib_path),
               'actions': [(common.mkdir_p, [lib_path.parent]),
                           [get_ld(self._platform),
                            *(str(obj_path) for obj_path in obj_paths),
                            '-o', str(lib_path), shared_flag,
                            *self._ld_flags]],
               'file_dep': obj_paths,
               'task_dep': self._task_dep,
               'targets': [lib_path]}

    def get_task_objs(self) -> typing.Dict:
        for src_path in self._src_paths:
            dep_path = self._get_dep_path(src_path)
            obj_path = self._get_obj_path(src_path)
            header_paths = self._parse_dep(dep_path)
            yield {'name': str(obj_path),
                   'actions': [(common.mkdir_p, [obj_path.parent]),
                               [get_cc(self._platform),
                                *self._cpp_flags, *self._cc_flags, '-c',
                                '-o', str(obj_path), str(src_path)]],
                   'file_dep': [src_path, dep_path, *header_paths],
                   'task_dep': self._task_dep,
                   'targets': [obj_path]}

    def get_task_deps(self) -> typing.Dict:
        for src_path in self._src_paths:
            dep_path = self._get_dep_path(src_path)
            yield {'name': str(dep_path),
                   'actions': [(common.mkdir_p, [dep_path.parent]),
                               [get_cpp(self._platform),
                                *self._cpp_flags, '-MM',
                                '-o', str(dep_path), str(src_path)]],
                   'file_dep': [src_path],
                   'task_dep': self._task_dep,
                   'targets': [dep_path]}

    def _get_dep_path(self, src_path):
        return (self._build_dir /
                src_path.relative_to(self._src_dir)).with_suffix('.d')

    def _get_obj_path(self, src_path):
        return (self._build_dir /
                src_path.relative_to(self._src_dir)).with_suffix('.o')

    def _parse_dep(self, path):
        if not path.exists():
            return []
        with open(path, 'r') as f:
            content = f.readlines()
        if not content:
            return []
        content[0] = content[0][content[0].find(':')+1:]
        return list(itertools.chain.from_iterable(
            (Path(path) for path in i.replace(' \\\n', '').strip().split(' '))
            for i in content))
