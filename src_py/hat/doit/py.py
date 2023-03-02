from pathlib import Path
import itertools
import subprocess
import sys
import typing

from packaging.requirements import Requirement
import setuptools

from . import common


def build_wheel(src_dir: Path,
                dst_dir: Path,
                name: str,
                description: str,
                url: str,
                license: common.License,
                packages: typing.List[str] = None,
                src_paths: typing.Optional[typing.Iterable[Path]] = None,
                version_path: Path = Path('VERSION'),
                readme_path: Path = Path('README.rst'),
                license_path: typing.Optional[Path] = Path('LICENSE'),
                requirements_path: typing.Optional[Path] = Path('requirements.pip.runtime.txt'),  # NOQA
                py_versions: typing.Iterable[common.PyVersion] = common.PyVersion,  # NOQA
                py_limited_api: typing.Optional[common.PyVersion] = None,
                platform: typing.Optional[common.Platform] = None,
                console_scripts: typing.List[str] = [],
                gui_scripts: typing.List[str] = [],
                zip_safe: bool = True,
                has_ext_modules: bool = False,
                has_c_libraries: bool = False):
    common.rm_rf(dst_dir)
    common.mkdir_p(dst_dir)

    if src_paths is None:
        src_paths = [src_dir]
    src_paths = itertools.chain.from_iterable(
        (common.path_rglob(src_path, blacklist={'__pycache__'})
         if src_path.is_dir() else [src_path])
        for src_path in src_paths)

    is_pure = not (has_ext_modules or has_c_libraries)
    python_tag = _get_python_tag(py_versions)
    abi_tag = _get_abi_tag(is_pure, py_limited_api, py_versions)
    platform_tag = _get_platform_tag(platform)

    with open(dst_dir / 'MANIFEST.in', 'w', encoding='utf-8') as f:
        for src_path in src_paths:
            dst_path = dst_dir / src_path.relative_to(src_dir)
            common.mkdir_p(dst_path.parent)
            common.cp_r(src_path, dst_path)
            f.write(f"include {dst_path.relative_to(dst_dir)}\n")

    if packages is None:
        packages = setuptools.find_namespace_packages(dst_dir)

    (dst_dir / 'setup.py').write_text(_wheel_setup_py.format(
        name=repr(name),
        version=repr(common.get_version(version_type=common.VersionType.PIP,
                                        version_path=version_path)),
        description=repr(description),
        readme=repr(readme_path.read_text('utf-8').strip()),
        url=repr(url),
        license=repr(license.value),
        license_classifier=repr(_get_wheel_license_classifier(license)),
        packages=repr(packages),
        zip_safe=repr(zip_safe),
        requirements=repr([str(i)
                           for i in read_pip_requirements(requirements_path)]
                          if requirements_path else []),
        python_tag=repr(python_tag),
        abi_tag=repr(abi_tag),
        platform_tag=repr(platform_tag),
        console_scripts=repr(console_scripts),
        gui_scripts=repr(gui_scripts),
        has_ext_modules=repr(has_ext_modules),
        has_c_libraries=repr(has_c_libraries)), encoding='utf-8')

    if license_path:
        common.cp_r(license_path, dst_dir / 'LICENSE')

    subprocess.run([sys.executable, '-m', 'build', '--wheel',
                    '--no-isolation'],
                   stdout=subprocess.DEVNULL,
                   cwd=str(dst_dir),
                   check=True)


def run_pytest(pytest_dir: Path, *args: str):
    subprocess.run([sys.executable, '-m', 'pytest',
                    '-s', '-p', 'no:cacheprovider', *args],
                   cwd=str(pytest_dir),
                   check=True)


def run_flake8(path: Path):
    subprocess.run([sys.executable, '-m', 'flake8', str(path)],
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


def get_py_versions(py_limited_api: typing.Optional[common.PyVersion]
                    ) -> typing.List[common.PyVersion]:
    if py_limited_api is None:
        return [common.target_py_version]

    return [version for version in common.PyVersion
            if version.value[0] == py_limited_api.value[0] and
            version.value >= py_limited_api.value]


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


name = {name}
version = {version}
description = {description}
readme = {readme}
url = {url}
license = {license}
license_classifier = {license_classifier}
packages = {packages}
zip_safe = {zip_safe}
requirements = {requirements}
python_tag = {python_tag}
abi_tag = {abi_tag}
platform_tag = {platform_tag}
console_scripts = {console_scripts}
gui_scripts = {gui_scripts}
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


setuptools.setup(
    distclass=Distribution,
    name=name,
    version=version,
    description=description,
    long_description=readme,
    long_description_content_type='text/x-rst',
    url=url,
    license=license,
    classifiers=[
        'Programming Language :: Python :: 3',
        license_classifier],
    packages=packages,
    include_package_data=True,
    zip_safe=zip_safe,
    install_requires=requirements,
    python_requires='>=3.8',
    options={{
        'bdist_wheel': {{
            'python_tag': python_tag,
            'py_limited_api': python_tag,
            'plat_name': platform_tag
        }}
    }},
    entry_points={{
        'console_scripts': console_scripts,
        'gui_scripts': gui_scripts
    }})
"""
