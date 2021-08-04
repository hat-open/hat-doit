from pathlib import Path
import datetime
import enum
import functools
import itertools
import multiprocessing
import os
import shutil
import subprocess
import sys
import typing

import packaging.requirements
import packaging.version


now = datetime.datetime.now()


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


class StaticWebServer:

    def __init__(self, dir: os.PathLike, port: int):
        self._p = subprocess.Popen([sys.executable,
                                    '-m', 'http.server',
                                    '-b', '127.0.0.1',
                                    '-d', str(dir),
                                    str(port)],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._p.terminate()


def read_pip_requirements(path: os.PathLike
                          ) -> typing.Iterable[packaging.requirements.Requirement]:  # NOQA
    # TODO: implement full format
    #       https://pip.pypa.io/en/stable/cli/pip_install/
    for i in Path(path).read_text().split('\n'):
        i = i.strip()
        if not i or i.startswith('#'):
            continue
        yield packaging.requirements.Requirement(i)


class VersionType(enum.Enum):
    SEMVER = 0
    PIP = 1


@functools.lru_cache
def get_version(version_type: VersionType = VersionType.SEMVER,
                version_path: Path = Path('VERSION')
                ) -> str:
    version = version_path.read_text().strip()

    if version.endswith('dev'):
        version += now.strftime("%Y%m%d")

    if version_type == VersionType.SEMVER:
        return version

    elif version_type == VersionType.PIP:
        return packaging.version.Version(version).public

    raise ValueError()


class SphinxOutputType(enum.Enum):
    HTML = 'html'
    LATEX = 'latex'


def sphinx_build(out_type: SphinxOutputType,
                 src: Path,
                 dest: Path):
    mkdir_p(dest)
    subprocess.run([sys.executable, '-m', 'sphinx', '-q', '-b', out_type.value,
                    str(src), str(dest)],
                   check=True)


def latex_build(src: Path, dest: Path):
    mkdir_p(dest)
    for i in src.glob('*.tex'):
        subprocess.run(['xelatex', '-interaction=batchmode',
                        f'-output-directory={dest.resolve()}', i.name],
                       cwd=src, stdout=subprocess.DEVNULL, check=True)


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
        return {'actions': [(mkdir_p, [lib_path.parent]),
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
                   'actions': [(mkdir_p, [obj_path.parent]),
                               [cc, *self._cpp_flags, *self._cc_flags, '-c',
                                '-o', str(obj_path), str(src_path)]],
                   'file_dep': [src_path, dep_path, *header_paths],
                   'targets': [obj_path]}

    def get_task_deps(self) -> typing.Dict:
        for src_path in self._src_paths:
            dep_path = self._get_dep_path(src_path)
            yield {'name': str(dep_path),
                   'actions': [(mkdir_p, [dep_path.parent]),
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
