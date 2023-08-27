from pathlib import Path
import collections
import itertools
import json
import subprocess
import sys
import tempfile
import typing

import mkwhl

from . import common


def get_task_build_wheel(src_dir: Path,
                         build_dir: Path,
                         *,
                         file_dep=[],
                         task_dep=[],
                         **kwargs
                         ) -> dict:

    def action(whl_dir, whl_name_path, editable):
        build_wheel(src_dir=src_dir,
                    build_dir=whl_dir or build_dir,
                    whl_name_path=whl_name_path,
                    editable=editable,
                    **kwargs)

    return {'actions': [action],
            'params': [{'name': 'whl_dir',
                        'long': 'whl-dir',
                        'type': Path,
                        'default': None},
                       {'name': 'whl_name_path',
                        'long': 'whl-name-path',
                        'type': Path,
                        'default': None},
                       {'name': 'editable',
                        'long': 'editable',
                        'type': bool,
                        'default': False}],
            'file_dep': file_dep,
            'task_dep': task_dep}


def get_task_run_pytest(args=[],
                        *,
                        file_dep=[],
                        task_dep=[]
                        ) -> dict:

    def action(cmd_args):
        run_pytest(*itertools.chain(args, cmd_args or []))

    return {'actions': [action],
            'pos_arg': 'cmd_args',
            'file_dep': file_dep,
            'task_dep': task_dep}


def get_task_create_pip_requirements(dst_path: Path = Path('requirements.pip.txt'),  # NOQA
                                     *,
                                     freeze: bool = False,
                                     src_path: Path = Path('pyproject.toml'),
                                     file_dep=[],
                                     task_dep=[],
                                     **kwargs
                                     ) -> dict:

    def action():
        create_pip_requirements(dst_path,
                                freeze=freeze,
                                src_path=src_path,
                                **kwargs)

    return {'actions': [action],
            'file_dep': [src_path, *file_dep],
            'task_dep': task_dep,
            'targets': [dst_path],
            **({'uptodate': [False]} if freeze else {})}


def build_wheel(src_dir: Path,
                build_dir: Path,
                *,
                whl_name_path: Path | None = None,
                py_versions: typing.Iterable[common.PyVersion] = common.PyVersion,  # NOQA
                py_limited_api: common.PyVersion | None = None,
                platform: common.Platform | None = None,
                is_purelib: bool = True,
                **kwargs):
    python_tag = _get_python_tag(py_versions)
    abi_tag = _get_abi_tag(is_purelib, py_limited_api, py_versions)
    platform_tag = _get_platform_tag(platform)

    whl_name = mkwhl.create_wheel(src_dir=src_dir,
                                  build_dir=build_dir,
                                  python_tag=python_tag,
                                  abi_tag=abi_tag,
                                  platform_tag=platform_tag,
                                  is_purelib=is_purelib,
                                  **kwargs)

    if whl_name_path is not None:
        whl_name_path.write_text(whl_name)


def run_pytest(*args: str):
    subprocess.run([sys.executable, '-m', 'pytest',
                    '--capture', 'no',
                    '-p', 'hat.doit.pytest',
                    '-p', 'no:cacheprovider',
                    *args],
                   check=True)


def run_flake8(path: Path):
    subprocess.run([sys.executable, '-m', 'flake8', str(path)],
                   check=True)


def create_pip_requirements(dst_path: Path,
                            *,
                            freeze: bool = False,
                            extras: list[str] | None = None,
                            src_path: Path = Path('pyproject.toml')):
    project_conf = common.get_conf(src_path).get('project', {})

    dependencies = collections.deque(project_conf.get('dependencies', []))
    for k, v in project_conf.get('optional-dependencies', {}).items():
        if extras is None or k in extras:
            dependencies.extend(v)

    if freeze:
        # TODO alternative implementation
        with tempfile.TemporaryDirectory() as tmp_dir:
            requirements_path = Path(tmp_dir) / 'requirements.txt'
            report_path = Path(tmp_dir) / 'report.json'

            requirements_path.write_text(
                ''.join(f"{i}\n" for i in dependencies))

            # TODO platform and constaints
            subprocess.run([sys.executable, '-m', 'pip', '--quiet',
                            'install', '--dry-run', '--ignore-installed',
                            '--quiet', '--report', str(report_path),
                            '-r', str(requirements_path)],
                           check=True)

            report = json.loads(report_path.read_text())

        # TODO fix
        dependencies = [f"{i['metadata']['name']}=={i['metadata']['version']}"
                        for i in report.get('install', [])]

    dependencies = sorted(dependencies)
    dst_path.write_text(''.join(f"{i}\n" for i in dependencies))


def get_py_versions(py_limited_api: common.PyVersion | None
                    ) -> list[common.PyVersion]:
    if py_limited_api is None:
        return [common.target_py_version]

    return [version for version in common.PyVersion
            if version.value[0] == py_limited_api.value[0] and
            version.value >= py_limited_api.value]


def _get_python_tag(py_versions):
    return '.'.join(''.join(str(i) for i in py_version.value)
                    for py_version in py_versions)


def _get_abi_tag(is_purelib, py_limited_api, py_versions):
    if is_purelib:
        return 'none'

    if py_limited_api:
        return 'abi3'

    return _get_python_tag(py_versions)


def _get_platform_tag(platform):
    if not platform:
        return 'any'

    if platform == common.Platform.WINDOWS_AMD64:
        return 'win_amd64'

    if platform == common.Platform.DARWIN_X86_64:
        return 'macosx_10_13_x86_64'

    if platform == common.Platform.LINUX_GNU_X86_64:
        return 'manylinux_2_24_x86_64'

    if platform == common.Platform.LINUX_GNU_AARCH64:
        return 'manylinux_2_24_aarch64'

    if platform == common.Platform.LINUX_GNU_ARMV7L:
        return 'manylinux_2_24_armv7l'

    if platform == common.Platform.LINUX_MUSL_X86_64:
        return 'musllinux_1_2_x86_64'

    if platform == common.Platform.LINUX_MUSL_AARCH64:
        return 'musllinux_1_2_aarch64'

    raise NotImplementedError()
