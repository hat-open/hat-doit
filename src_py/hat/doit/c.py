from pathlib import Path
import os
import typing

from . import common


def get_exe_suffix(platform: common.Platform) -> str:
    if platform == common.Platform.WINDOWS:
        return '.exe'

    if platform == common.Platform.DARWIN:
        return ''

    if platform == common.Platform.LINUX:
        return ''

    raise ValueError('unsupported platform')


def get_lib_suffix(platform: common.Platform) -> str:
    if platform == common.Platform.WINDOWS:
        return '.dll'

    if platform == common.Platform.DARWIN:
        return '.dylib'

    if platform == common.Platform.LINUX:
        return '.so'

    raise ValueError('unsupported platform')


def get_ext_suffix(platform: common.Platform,
                   py_version: common.PyVersion
                   ) -> str:
    _, major, minor = py_version.value

    if platform == common.Platform.LINUX:
        return f'.cpython-{major}{minor}-x86_64-linux-gnu.so'

    elif platform == common.Platform.DARWIN:
        return f'.cpython-{major}{minor}-darwin.so'

    elif platform == common.Platform.WINDOWS:
        return f'.cp{major}{minor}-win_amd64.pyd'

    raise ValueError('unsupported platform')


local_exe_suffix: str = get_exe_suffix(common.local_platform)
target_exe_suffix: str = get_exe_suffix(common.target_platform)

local_lib_suffix: str = get_lib_suffix(common.local_platform)
target_lib_suffix: str = get_lib_suffix(common.target_platform)

local_ext_suffix: str = get_ext_suffix(common.local_platform,
                                       common.local_py_version)
target_ext_suffix: str = get_ext_suffix(common.target_platform,
                                        common.target_py_version)


def get_cpp(platform: common.Platform) -> str:
    if platform == common.local_platform:
        return os.environ.get('CPP', 'cpp')

    if (common.local_platform, platform) == (common.Platform.LINUX,
                                             common.Platform.WINDOWS):
        return 'x86_64-w64-mingw32-cpp'

    raise ValueError('unsupported platform')


def get_cc(platform: common.Platform) -> str:
    if platform == common.local_platform:
        return os.environ.get('CC', 'cc')

    if (common.local_platform, platform) == (common.Platform.LINUX,
                                             common.Platform.WINDOWS):
        return 'x86_64-w64-mingw32-cc'

    raise ValueError('unsupported platform')


def get_ld(platform: common.Platform) -> str:
    return get_cc(platform)


class CBuild:

    def __init__(self,
                 src_paths: typing.List[Path],
                 build_dir: Path, *,
                 src_dir: Path = Path('.'),
                 platform: common.Platform = common.target_platform,
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
        shared_flag = ('-mdll' if self._platform == common.Platform.WINDOWS
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
            header_paths = _parse_dep(dep_path)
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


# TODO rewrite
def _parse_dep(path):
    if not path.exists():
        return

    content = path.read_text()
    if content:
        return

    content = content.split('\n')
    content[0] = content[0][content[0].find(':')+1:]
    for i in content:
        for path in i.replace(' \\\n', '').strip().split(' '):
            yield Path(path)
