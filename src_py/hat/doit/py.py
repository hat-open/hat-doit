from pathlib import Path
import itertools
import subprocess
import sys
import typing

from packaging.requirements import Requirement

from . import common


def build_wheel(src_dir: Path,
                dst_dir: Path,
                name: str,
                description: str,
                url: str,
                license: common.License,
                packages: typing.List[str],
                src_paths: typing.Optional[typing.Iterable[Path]] = None,
                version_path: Path = Path('VERSION'),
                readme_path: Path = Path('README.rst'),
                license_path: typing.Optional[Path] = Path('LICENSE'),
                requirements_path: typing.Optional[Path] = Path('requirements.pip.runtime.txt'),  # NOQA
                py_versions: typing.Iterable[common.PyVersion] = common.PyVersion,  # NOQA
                platform: typing.Optional[common.Platform] = None,
                console_scripts: typing.List[str] = [],
                gui_scripts: typing.List[str] = []):
    common.rm_rf(dst_dir)
    common.mkdir_p(dst_dir)

    if src_paths is None:
        src_paths = [src_dir]
    src_paths = itertools.chain.from_iterable(
        (common.path_rglob(src_path, blacklist={'__pycache__'})
         if src_path.is_dir() else [src_path])
        for src_path in src_paths)

    python_tag = '.'.join(''.join(str(i) for i in py_version.value)
                          for py_version in py_versions)

    with open(dst_dir / 'MANIFEST.in', 'w', encoding='utf-8') as f:
        for src_path in src_paths:
            dst_path = dst_dir / src_path.relative_to(src_dir)
            common.mkdir_p(dst_path.parent)
            common.cp_r(src_path, dst_path)
            f.write(f"include {dst_path.relative_to(dst_dir)}\n")

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
        requirements=repr([str(i)
                           for i in read_pip_requirements(requirements_path)]
                          if requirements_path else []),
        python_tag=repr(python_tag),
        plat_name=repr(_get_wheel_plat_name(platform)),
        console_scripts=repr(console_scripts),
        gui_scripts=repr(gui_scripts)), encoding='utf-8')

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
        yield Requirement(i)


def _get_wheel_license_classifier(license):
    if license == common.License.APACHE2:
        return 'License :: OSI Approved :: Apache Software License'

    if license == common.License.GPL3:
        return ('License :: OSI Approved :: '
                'GNU General Public License v3 (GPLv3)')

    if license == common.License.PROPRIETARY:
        return 'License :: Other/Proprietary License'

    raise ValueError('unsupported license')


def _get_wheel_plat_name(platform):
    if not platform:
        return 'any'

    if platform == common.Platform.WINDOWS:
        return 'win_amd64'

    if platform == common.Platform.DARWIN:
        return 'macosx_10_13_x86_64'

    if platform == common.Platform.LINUX:
        return 'manylinux1_x86_64'

    raise NotImplementedError()


_wheel_setup_py = r"""
from setuptools import setup

name = {name}
version = {version}
description = {description}
readme = {readme}
url = {url}
license = {license}
license_classifier = {license_classifier}
packages = {packages}
requirements = {requirements}
python_tag = {python_tag}
plat_name = {plat_name}
console_scripts = {console_scripts}
gui_scripts = {gui_scripts}

setup(
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
    zip_safe=False,
    install_requires=requirements,
    python_requires='>=3.8',
    options={{
        'bdist_wheel': {{
            'python_tag': python_tag,
            'py_limited_api': python_tag,
            'plat_name': plat_name
        }}
    }},
    entry_points={{
        'console_scripts': console_scripts,
        'gui_scripts': gui_scripts
    }})
"""
