from pathlib import Path
import itertools
import os
import sys
import typing

from . import common


if sys.platform == 'win32':
    lib_suffix = '.dll'
elif sys.platform == 'darwin':
    lib_suffix = '.dylib'
else:
    lib_suffix = '.so'

cpp = os.environ.get('CPP', 'cpp')
cc = os.environ.get('CC', 'cc')
ld = os.environ.get('LD', 'cc')


class CBuild:

    def __init__(self,
                 src_paths: typing.List[Path],
                 src_dir: Path,
                 build_dir: Path, *,
                 cpp: str = cpp,
                 cc: str = cc,
                 ld: str = ld,
                 cpp_flags: typing.List[str] = [],
                 cc_flags: typing.List[str] = [],
                 ld_flags: typing.List[str] = [],
                 libs: typing.List[str] = []):
        self._src_paths = src_paths
        self._src_dir = src_dir
        self._build_dir = build_dir
        self._cpp = cpp
        self._cc = cc
        self._ld = ld
        self._cpp_flags = cpp_flags
        self._cc_flags = cc_flags
        self._ld_flags = ld_flags

    def get_task_lib(self, lib_path: Path) -> typing.Dict:
        obj_paths = [self._get_obj_path(src_path)
                     for src_path in self._src_paths]
        shared_flag = '-mdll' if sys.platform == 'win32' else '-shared'
        return {'actions': [(common.mkdir_p, [lib_path.parent]),
                            [ld, *[str(obj_path) for obj_path in obj_paths],
                             '-o', str(lib_path), shared_flag,
                             *self._ld_flags]],
                'file_dep': obj_paths,
                'targets': [lib_path]}

    def get_task_objs(self) -> typing.Dict:
        for src_path in self._src_paths:
            dep_path = self._get_dep_path(src_path)
            obj_path = self._get_obj_path(src_path)
            header_paths = self._parse_dep(dep_path)
            yield {'name': str(obj_path),
                   'actions': [(common.mkdir_p, [obj_path.parent]),
                               [cc, *self._cpp_flags, *self._cc_flags, '-c',
                                '-o', str(obj_path), str(src_path)]],
                   'file_dep': [src_path, dep_path, *header_paths],
                   'targets': [obj_path]}

    def get_task_deps(self) -> typing.Dict:
        for src_path in self._src_paths:
            dep_path = self._get_dep_path(src_path)
            yield {'name': str(dep_path),
                   'actions': [(common.mkdir_p, [dep_path.parent]),
                               [cpp, *self._cpp_flags, '-MM',
                                '-o', str(dep_path), str(src_path)]],
                   'file_dep': [src_path],
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
