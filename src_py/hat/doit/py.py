from pathlib import Path
import base64
import hashlib
import itertools
import os
import subprocess
import sys
import typing
import zipfile

from build import ProjectBuilder
from packaging.requirements import Requirement
import tomli_w

from . import common


def get_task_build_wheel(src_dir: Path,
                         build_dir: Path, *,
                         file_dep=[],
                         task_dep=[],
                         **kwargs):

    def action(whl_dir, whl_name_path, editable):
        build_wheel(src_dir=src_dir,
                    build_dir=build_dir,
                    whl_dir=whl_dir,
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
                        file_dep=[],
                        task_dep=[]):

    def action(cmd_args):
        run_pytest(*itertools.chain(args, cmd_args or []))

    return {'actions': [action],
            'pos_arg': 'cmd_args',
            'file_dep': file_dep,
            'task_dep': task_dep}


def get_task_run_pip_compile(dst_path: Path = Path('requirements.pip.txt')):

    def action(args):
        run_pip_compile(dst_path,
                        args=args or [])

    return {'actions': [action],
            'pos_arg': 'args'}


def build_wheel(src_dir: Path,
                build_dir: Path, *,
                name: str | None = None,
                version: str | None = None,
                description: str | None = None,
                readme_path: Path | None = None,
                requires_python: str | None = None,
                license: common.License | None = None,
                authors: list[dict[str, str]] | None = None,
                maintainers: list[dict[str, str]] | None = None,
                keywords: list[str] | None = None,
                classifiers: list[str] | None = None,
                urls: dict[str, str] | None = None,
                scripts: dict[str, str] | None = None,
                gui_scripts: dict[str, str] | None = None,
                dependencies: list[str] | None = None,
                optional_dependencies: dict[str, list[str]] | None = None,
                whl_dir: Path | None = None,
                whl_name_path: Path | None = None,
                editable: bool = False,
                src_paths: typing.Iterable[Path] | None = None,
                packages: list[str] | None = None,
                py_versions: typing.Iterable[common.PyVersion] = common.PyVersion,  # NOQA
                py_limited_api: common.PyVersion | None = None,
                platform: common.Platform | None = None,
                has_ext_modules: bool = False,
                has_c_libraries: bool = False):
    src_license_path = Path('LICENSE')
    dst_conf_path = build_dir / 'pyproject.toml'
    dst_manifest_path = build_dir / 'MANIFEST.in'
    dst_setup_path = build_dir / 'setup.py'
    dst_license_path = build_dir / 'LICENSE'

    src_conf = common.get_conf()
    src_project_conf = src_conf.get('project', {})

    dst_conf = {'project': {},
                'build-system': {'requires': ['setuptools', 'wheel'],
                                 'build-backend': 'setuptools.build_meta'},
                'tool': {'setuptools': {}}}
    dst_project_conf = dst_conf['project']
    dst_tool_conf = dst_conf['tool']['setuptools']

    if name is not None:
        dst_project_conf['name'] = name
    elif 'name' in src_project_conf:
        dst_project_conf['name'] = src_project_conf['name']
    else:
        Exception('name not provided')

    dst_project_conf['version'] = common.get_version(common.VersionType.PIP,
                                                     version)

    if description is not None:
        dst_project_conf['description'] = description
    elif 'description' in src_project_conf:
        dst_project_conf['description'] = src_project_conf['description']

    if readme_path is not None:
        dst_project_conf['readme'] = str(readme_path)
    elif 'readme' in src_project_conf:
        dst_project_conf['readme'] = src_project_conf['readme']

    if requires_python is not None:
        dst_project_conf['requires-python'] = requires_python
    elif 'requires-python' in src_project_conf:
        dst_project_conf['requires-python'] = \
            src_project_conf['requires-python']

    if license is not None:
        dst_project_conf['license'] = {'text': license.value}
    elif 'license' in src_project_conf:
        license = (common.License(src_project_conf['license']['text'])
                   if 'text' in src_project_conf['license'] else
                   common.License.PROPRIETARY)
        dst_project_conf['license'] = src_project_conf['license']
    else:
        license = common.License.PROPRIETARY
        dst_project_conf['license'] = {'text': license.value}

    if authors is not None:
        dst_project_conf['authors'] = authors
    elif 'authors' in src_project_conf:
        dst_project_conf['authors'] = src_project_conf['authors']

    if maintainers is not None:
        dst_project_conf['maintainers'] = maintainers
    elif 'maintainers' in src_project_conf:
        dst_project_conf['maintainers'] = src_project_conf['maintainers']

    if keywords is not None:
        dst_project_conf['keywords'] = keywords
    elif 'keywords' in src_project_conf:
        dst_project_conf['keywords'] = src_project_conf['keywords']

    if classifiers is not None:
        dst_project_conf['classifiers'] = classifiers
    elif 'classifiers' in src_project_conf:
        dst_project_conf['classifiers'] = src_project_conf['classifiers']
    else:
        dst_project_conf['classifiers'] = [
            'Programming Language :: Python :: 3',
            _get_wheel_license_classifier(license)]

    if urls is not None:
        dst_project_conf['urls'] = urls
    elif 'urls' in src_project_conf:
        dst_project_conf['urls'] = src_project_conf['urls']

    if scripts is not None:
        dst_project_conf['scripts'] = scripts
    elif 'scripts' in src_project_conf:
        dst_project_conf['scripts'] = src_project_conf['scripts']

    if gui_scripts is not None:
        dst_project_conf['gui-scripts'] = gui_scripts
    elif 'gui-scripts' in src_project_conf:
        dst_project_conf['gui-scripts'] = src_project_conf['gui-scripts']

    if dependencies is not None:
        dst_project_conf['dependencies'] = dependencies
    elif 'dependencies' in src_project_conf:
        dst_project_conf['dependencies'] = src_project_conf['dependencies']

    if optional_dependencies is not None:
        dst_project_conf['optional-dependencies'] = optional_dependencies
    elif 'optional-dependencies' in src_project_conf:
        dst_project_conf['optional-dependencies'] = \
            src_project_conf['optional-dependencies']

    common.rm_rf(build_dir)
    common.mkdir_p(build_dir)

    if whl_dir is None:
        whl_dir = build_dir / 'dist'

    if editable:
        pth_path = build_dir / f"{dst_project_conf['name']}.pth"
        src_dir_repr = repr(str(src_dir.resolve()))
        pth_path.write_text(
            f"import sys; "
            f"sys.path = [{src_dir_repr}, "
            f"*(i for i in sys.path if i != {src_dir_repr})]\n")

        dst_manifest_path.write_text(f"include {pth_path.name}\n")

    else:
        if src_paths is None:
            src_paths = [src_dir]
        src_paths = itertools.chain.from_iterable(
            (common.path_rglob(src_path, blacklist={'__pycache__'})
             if src_path.is_dir() else [src_path])
            for src_path in src_paths)

        with open(dst_manifest_path, 'w', encoding='utf-8') as f:
            for src_path in src_paths:
                dst_path = build_dir / src_path.relative_to(src_dir)
                common.mkdir_p(dst_path.parent)
                common.cp_r(src_path, dst_path)
                f.write(f"include {dst_path.relative_to(build_dir)}\n")

        # if packages is None:
        #     packages = setuptools.find_namespace_packages(dst_dir)

        if packages is not None:
            dst_tool_conf['packages'] = packages

    is_pure = not (has_ext_modules or has_c_libraries)
    python_tag = _get_python_tag(py_versions)
    abi_tag = _get_abi_tag(is_pure, py_limited_api, py_versions)
    platform_tag = _get_platform_tag(platform)
    setup_str = _wheel_setup_py.format(python_tag=repr(python_tag),
                                       abi_tag=repr(abi_tag),
                                       platform_tag=repr(platform_tag),
                                       has_ext_modules=repr(has_ext_modules),
                                       has_c_libraries=repr(has_c_libraries))
    dst_setup_path.write_text(setup_str, encoding='utf-8')

    if 'readme' in dst_project_conf:
        common.cp_r(Path(dst_project_conf['readme']),
                    build_dir / dst_project_conf['readme'])

    if 'file' in dst_project_conf['license']:
        common.cp_r(Path(dst_project_conf['license']['file']),
                    build_dir / dst_project_conf['license']['file'])
    elif src_license_path.exists():
        common.cp_r(src_license_path, dst_license_path)

    dst_conf_path.write_text(tomli_w.dumps(dst_conf), encoding='utf-8')

    builder = ProjectBuilder(build_dir, runner=_build_runner)
    whl_path = builder.build('wheel', whl_dir.resolve())
    whl_path = Path(whl_path)

    if editable:
        tmp_whl_path = whl_path.with_suffix('.tmp')

        pth_bytes = pth_path.read_bytes()
        pth_sha256 = hashlib.sha256(pth_bytes).digest()
        pth_sha256_b64 = base64.urlsafe_b64encode(pth_sha256).rstrip(b'=')
        pth_sha256_b64_str = pth_sha256_b64.decode()
        pth_size = len(pth_bytes)
        pth_record = (f"{pth_path.name},"
                      f"sha256={pth_sha256_b64_str},"
                      f"{pth_size}\n")

        with zipfile.ZipFile(whl_path, "r") as whl:
            with zipfile.ZipFile(tmp_whl_path, "w") as tmp_whl:
                for i in whl.namelist():
                    data = whl.read(i)
                    if i.endswith('.dist-info/RECORD'):
                        data += pth_record.encode('utf-8')

                    tmp_whl.writestr(i, data)

                tmp_whl.write(pth_path, pth_path.name)

        whl_path.unlink()
        tmp_whl_path.rename(whl_path)

    if whl_name_path is not None:
        whl_name_path.write_text(whl_path.name)


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


def run_pip_compile(dst_path: Path, *,
                    extras: list[str] | None = None,
                    args: list[str] = [],
                    src_path: Path = Path('pyproject.toml')):
    extras = (['--all-extras'] if extras is None else
              itertools.chain.from_iterable(('--extra', i) for i in extras))

    conf = common.get_conf(src_path)
    if not conf.get('project', {}).get('optional-dependencies'):
        extras = []

    subprocess.run([sys.executable, '-m', 'piptools', 'compile',
                    '--quiet',
                    '--no-emit-index-url',
                    '-o', str(dst_path),
                    *extras,
                    *args,
                    str(src_path)],
                   check=True)


def read_pip_requirements(path: Path) -> typing.Iterable[Requirement]:
    # TODO: implement full format
    #       https://pip.pypa.io/en/stable/cli/pip_install/
    for i in Path(path).read_text('utf-8').split('\n'):
        i = i.strip()
        if not i or i.startswith('#'):
            continue
        if i.startswith('-r'):
            for arg in i.split(' ')[1:]:
                if arg:
                    yield from read_pip_requirements(Path(arg))
                    break
            continue
        yield Requirement(i)


def get_py_versions(py_limited_api: common.PyVersion | None
                    ) -> list[common.PyVersion]:
    if py_limited_api is None:
        return [common.target_py_version]

    return [version for version in common.PyVersion
            if version.value[0] == py_limited_api.value[0] and
            version.value >= py_limited_api.value]


def _build_runner(cmd, cwd, extra_environ):
    subprocess.run(cmd,
                   stdout=subprocess.DEVNULL,
                   cwd=cwd,
                   env={**os.environ, **extra_environ},
                   check=True)


def _get_wheel_license_classifier(license):
    if license == common.License.APACHE2:
        return 'License :: OSI Approved :: Apache Software License'

    if license == common.License.GPL3:
        return ('License :: OSI Approved :: '
                'GNU General Public License v3 (GPLv3)')

    if license == common.License.PROPRIETARY:
        return 'License :: Other/Proprietary License'

    raise ValueError('unsupported license')


def _get_python_tag(py_versions):
    return '.'.join(''.join(str(i) for i in py_version.value)
                    for py_version in py_versions)


def _get_abi_tag(is_pure, py_limited_api, py_versions):
    if is_pure:
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


_wheel_setup_py = r"""
import setuptools
import wheel.bdist_wheel


python_tag = {python_tag}
abi_tag = {abi_tag}
platform_tag = {platform_tag}
has_ext_modules = {has_ext_modules}
has_c_libraries = {has_c_libraries}


wheel_tag = python_tag, abi_tag, platform_tag
wheel.bdist_wheel.bdist_wheel.get_tag = lambda self: wheel_tag


class Distribution(setuptools.Distribution):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.libraries = [] if has_c_libraries else None

    def has_ext_modules(self):
        return has_ext_modules

    def has_c_libraries(self):
        return has_c_libraries


setup_args = {{
    'distclass': Distribution,
    'options': {{
        'bdist_wheel': {{
            'python_tag': python_tag,
            'py_limited_api': python_tag,
            'plat_name': platform_tag
        }}
    }},
}}


setuptools.setup(**setup_args)
"""
