from pathlib import Path
from typing import Iterable
import functools
import importlib.resources
import os
import shlex
import shutil
import subprocess
import sysconfig

from . import clang as hat_doit_clang
from . import common


def get_exe_suffix(platform: common.Platform = common.target_platform
                   ) -> str:
    if platform == common.Platform.WINDOWS_AMD64:
        return '.exe'

    if platform in (common.Platform.DARWIN_X86_64,
                    common.Platform.LINUX_GNU_X86_64,
                    common.Platform.LINUX_GNU_AARCH64,
                    common.Platform.LINUX_GNU_ARMV7L,
                    common.Platform.LINUX_MUSL_X86_64,
                    common.Platform.LINUX_MUSL_AARCH64,
                    common.Platform.LINUX_MUSL_ARMV7L):
        return ''

    raise ValueError('unsupported platform')


def get_lib_suffix(platform: common.Platform = common.target_platform
                   ) -> str:
    if platform == common.Platform.WINDOWS_AMD64:
        return '.dll'

    if platform == common.Platform.DARWIN_X86_64:
        return '.dylib'

    if platform in (common.Platform.LINUX_GNU_X86_64,
                    common.Platform.LINUX_GNU_AARCH64,
                    common.Platform.LINUX_GNU_ARMV7L,
                    common.Platform.LINUX_MUSL_X86_64,
                    common.Platform.LINUX_MUSL_AARCH64,
                    common.Platform.LINUX_MUSL_ARMV7L):
        return '.so'

    raise ValueError('unsupported platform')


def get_py_ext_suffix(platform: common.Platform = common.target_platform,
                      py_version: common.PyVersion = common.target_py_version,
                      py_limited_api: common.PyVersion | None = None
                      ) -> str:
    _, major, minor = (py_limited_api or py_version).value

    if platform == common.Platform.WINDOWS_AMD64:
        suffix = '.pyd'

    elif platform in (common.Platform.DARWIN_X86_64,
                      common.Platform.LINUX_GNU_X86_64,
                      common.Platform.LINUX_GNU_AARCH64,
                      common.Platform.LINUX_GNU_ARMV7L,
                      common.Platform.LINUX_MUSL_X86_64,
                      common.Platform.LINUX_MUSL_AARCH64,
                      common.Platform.LINUX_MUSL_ARMV7L):
        suffix = '.so'

    else:
        raise ValueError('unsupported platform')

    if py_limited_api is not None:
        return f'.abi{major}{suffix}'

    elif platform == common.Platform.WINDOWS_AMD64:
        return f'.cp{major}{minor}-win_amd64{suffix}'

    elif platform == common.Platform.DARWIN_X86_64:
        return f'.cpython-{major}{minor}-darwin{suffix}'

    elif platform == common.Platform.LINUX_GNU_X86_64:
        return f'.cpython-{major}{minor}-x86_64-linux-gnu{suffix}'

    elif platform == common.Platform.LINUX_GNU_AARCH64:
        return f'.cpython-{major}{minor}-aarch64-linux-gnu{suffix}'

    elif platform == common.Platform.LINUX_GNU_ARMV7L:
        # return f'.cpython-{major}{minor}-armv7l-linux-gnu{suffix}'
        return f'.cpython-{major}{minor}-arm-linux-gnueabi{suffix}'

    elif platform == common.Platform.LINUX_MUSL_X86_64:
        # TODO sysconfig.get_config_var("SOABI") returns gnu
        return f'.cpython-{major}{minor}-x86_64-linux-gnu{suffix}'

    elif platform == common.Platform.LINUX_MUSL_AARCH64:
        # TODO sysconfig.get_config_var("SOABI") returns gnu
        return f'.cpython-{major}{minor}-aarch64-linux-gnu{suffix}'

    elif platform == common.Platform.LINUX_MUSL_ARMV7L:
        # TODO sysconfig.get_config_var("SOABI") returns gnu
        return f'.cpython-{major}{minor}-arm-linux-gnu{suffix}'

    raise ValueError('unsupported platform')


local_exe_suffix: str = get_exe_suffix(common.local_platform)
target_exe_suffix: str = get_exe_suffix(common.target_platform)

local_lib_suffix: str = get_lib_suffix(common.local_platform)
target_lib_suffix: str = get_lib_suffix(common.target_platform)


@functools.lru_cache
def get_cc(platform: common.Platform = common.target_platform
           ) -> str:
    candidates = []

    if platform == common.local_platform:
        if 'CC' in os.environ:
            candidates.append(os.environ['CC'])
        candidates.append('cc')
        candidates.append('gcc')

    if platform == common.Platform.WINDOWS_AMD64:
        candidates.append('x86_64-w64-mingw32-gcc')

    elif platform == common.Platform.LINUX_GNU_AARCH64:
        candidates.append('aarch64-linux-gnu-gcc')

    elif platform == common.Platform.LINUX_GNU_ARMV7L:
        candidates.append('arm-linux-gnueabihf-gcc')

    elif platform == common.Platform.LINUX_MUSL_X86_64:
        candidates.append('musl-gcc')

    for candidate in candidates:
        cmd = shutil.which(candidate)
        if cmd:
            return cmd

    raise ValueError('unsupported platform')


def get_c_flags(platform: common.Platform = common.target_platform
                ) -> Iterable[str]:
    yield from shlex.split(os.environ.get('CFLAGS', ''))

    if platform != common.local_platform:
        if platform == common.Platform.LINUX_GNU_ARMV7L:
            yield '-march=armv7'


def get_ld_flags(platform: common.Platform = common.target_platform,
                 shared: bool = False
                 ) -> Iterable[str]:
    if shared:
        if platform == common.Platform.WINDOWS_AMD64:
            yield '-mdll'
            yield '-Wl,--export-all'

        else:
            yield '-shared'

    yield from shlex.split(os.environ.get('LDFLAGS', ''))


def get_py_c_flags(platform: common.Platform = common.target_platform,
                   py_version: common.PyVersion = common.target_py_version,
                   py_limited_api: common.PyVersion | None = None
                   ) -> Iterable[str]:
    _, major, minor = py_version.value

    yield '-DPY_SSIZE_T_CLEAN'

    if py_limited_api:
        _, limited_major, limited_minor = py_limited_api.value
        yield f'-DPy_LIMITED_API=0x{limited_major:02X}{limited_minor:02X}0000'

    if platform == common.local_platform:
        if py_version == common.local_py_version:
            include_path = sysconfig.get_path('include')
            if include_path:
                yield f'-I{include_path}'

        elif common.local_platform == common.Platform.LINUX_GNU_X86_64:
            yield f'-I/usr/include/python{major}.{minor}'

        else:
            raise ValueError('unsupported version')

    elif common.local_platform == common.Platform.LINUX_GNU_X86_64:
        if platform == common.Platform.WINDOWS_AMD64:
            yield f'-I/usr/x86_64-w64-mingw32/include/python{major}{minor}'

        elif platform in (common.Platform.LINUX_GNU_AARCH64,
                          common.Platform.LINUX_MUSL_X86_64,
                          common.Platform.LINUX_MUSL_AARCH64):
            yield f'-I/usr/include/python{major}.{minor}'

        elif platform == common.Platform.LINUX_GNU_ARMV7L:
            # TODO use correct python version
            # yield f'-I/usr/lib32/python{major}.{minor}/include/python{major}.{minor}'  # NOQA
            # yield '-I/usr/lib32/python3.10/include/python3.10'
            pass

        else:
            raise ValueError('unsupported platform')

    else:
        raise ValueError('unsupported platform')


def get_py_ld_flags(platform: common.Platform = common.target_platform,
                    py_version: common.PyVersion = common.target_py_version,
                    py_limited_api: common.PyVersion | None = None
                    ) -> Iterable[str]:
    _, major, minor = py_version.value

    if platform == common.local_platform:
        if common.local_platform == common.Platform.DARWIN_X86_64:
            stdlib_path = (Path(sysconfig.get_path('stdlib')) /
                           f'config-{major}.{minor}-darwin')
            yield f"-L{stdlib_path}"

        elif common.local_platform == common.Platform.WINDOWS_AMD64:
            data_path = sysconfig.get_path('data')
            yield f"-L{data_path}"


def get_py_ld_libs(platform: common.Platform = common.target_platform,
                   py_version: common.PyVersion = common.target_py_version,
                   py_limited_api: common.PyVersion | None = None
                   ) -> Iterable[str]:
    _, major, minor = py_version.value

    if platform == common.Platform.WINDOWS_AMD64:
        if py_limited_api:
            yield f"-lpython{major}"
        else:
            yield f"-lpython{major}{minor}"

    elif platform == common.Platform.DARWIN_X86_64:
        if py_limited_api:
            yield f"-lpython{major}"
        else:
            yield f"-lpython{major}.{minor}"


def get_task_clang_format(src_paths: Iterable[Path]
                          ) -> Iterable[dict]:

    def clang_format(src_path):
        package = importlib.resources.files(hat_doit_clang)
        with importlib.resources.as_file(package /
                                         'clang-format.yaml') as style_path:
            subprocess.run(['clang-format', '-i',
                            f'-style=file:{style_path}',
                            str(src_path)],
                           check=True)

    for src_path in src_paths:
        yield {'name': str(src_path),
               'actions': [(clang_format, [src_path])],
               'file_dep': [src_path]}


class CBuild:

    def __init__(self,
                 src_paths: list[Path],
                 build_dir: Path, *,
                 src_dir: Path = Path('.'),
                 platform: common.Platform = common.target_platform,
                 c_flags: list[str] = [],
                 ld_flags: list[str] = [],
                 ld_libs: list[str] = [],
                 task_dep: list[str] = []):
        self._src_paths = src_paths
        self._build_dir = build_dir
        self._src_dir = src_dir
        self._platform = platform
        self._c_flags = c_flags
        self._ld_flags = ld_flags
        self._ld_libs = ld_libs
        self._task_dep = task_dep

    def get_task_exe(self, exe_path: Path) -> dict:
        obj_paths = [self._get_obj_path(src_path)
                     for src_path in self._src_paths]
        yield {'name': str(exe_path),
               'actions': [(common.mkdir_p, [exe_path.parent]),
                           [get_cc(self._platform),
                            *get_ld_flags(self._platform, False),
                            *self._ld_flags,
                            '-o', str(exe_path),
                            *(str(obj_path) for obj_path in obj_paths),
                            *self._ld_libs]],
               'file_dep': obj_paths,
               'task_dep': self._task_dep,
               'targets': [exe_path]}

    def get_task_lib(self, lib_path: Path) -> dict:
        obj_paths = [self._get_obj_path(src_path)
                     for src_path in self._src_paths]
        yield {'name': str(lib_path),
               'actions': [(common.mkdir_p, [lib_path.parent]),
                           [get_cc(self._platform),
                            *get_ld_flags(self._platform, True),
                            *self._ld_flags,
                            '-o', str(lib_path),
                            *(str(obj_path) for obj_path in obj_paths),
                            *self._ld_libs]],
               'file_dep': obj_paths,
               'task_dep': self._task_dep,
               'targets': [lib_path]}

    def get_task_objs(self) -> dict:
        for src_path in self._src_paths:
            dep_path = self._get_dep_path(src_path)
            obj_path = self._get_obj_path(src_path)
            header_paths = _parse_dep(dep_path)
            yield {'name': str(obj_path),
                   'actions': [(common.mkdir_p, [obj_path.parent]),
                               [get_cc(self._platform),
                                '-c',
                                *get_c_flags(self._platform),
                                *self._c_flags,
                                '-o', str(obj_path),
                                str(src_path)]],
                   'file_dep': [src_path, dep_path, *header_paths],
                   'task_dep': self._task_dep,
                   'targets': [obj_path]}

    def get_task_deps(self) -> dict:
        for src_path in self._src_paths:
            dep_path = self._get_dep_path(src_path)
            yield {'name': str(dep_path),
                   'actions': [(common.mkdir_p, [dep_path.parent]),
                               [get_cc(self._platform),
                                '-MM',
                                *get_c_flags(self._platform),
                                *self._c_flags,
                                '-o', str(dep_path),
                                str(src_path)]],
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
