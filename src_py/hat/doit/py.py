from pathlib import Path
import platform
import subprocess
import sys
import typing

import packaging.requirements

from . import common


def build_wheel(src_dir: Path,
                dst_dir: Path,
                src_paths: typing.List[Path],
                name: str,
                description: str,
                url: str,
                license: common.License,
                packages: typing.List[str],
                version_path: Path = Path('VERSION'),
                readme_path: Path = Path('README.rst'),
                license_path: typing.Optional[Path] = Path('LICENSE'),
                requirements_path: typing.Optional[Path] = Path('requirements.pip.runtime.txt'),  # NOQA
                python_tag: str = 'cp38.cp39',
                platform_specific: bool = False,
                console_scripts=[],
                gui_scripts=[]):
    common.rm_rf(dst_dir)
    common.mkdir_p(dst_dir)

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
        readme=repr(readme_path.read_text().strip()),
        url=repr(url),
        license=repr(license.value),
        license_classifier=repr(_get_wheel_license_classifier(license)),
        packages=repr(packages),
        requirements=repr([str(i)
                           for i in _read_pip_requirements(requirements_path)]
                          if requirements_path else []),
        python_tag=repr(python_tag),
        plat_name=repr(_get_wheel_plat_name(platform_specific)),
        console_scripts=repr(console_scripts),
        gui_scripts=repr(gui_scripts)))

    if license_path:
        common.cp_r(license_path, dst_dir / 'LICENSE')

    subprocess.run([sys.executable, 'setup.py', '-q', 'bdist_wheel'],
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


def _read_pip_requirements(path):
    # TODO: implement full format
    #       https://pip.pypa.io/en/stable/cli/pip_install/
    for i in Path(path).read_text().split('\n'):
        i = i.strip()
        if not i or i.startswith('#'):
            continue
        yield packaging.requirements.Requirement(i)


def _get_wheel_license_classifier(license):
    if license == common.License.APACHE2:
        return 'License :: OSI Approved :: Apache Software License'

    if license == common.License.GPL3:
        return ('License :: OSI Approved :: '
                'GNU General Public License v3 (GPLv3)')

    raise ValueError('unsupported license')


def _get_wheel_plat_name(platform_specific):
    if not platform_specific:
        return 'any'

    arch, _ = platform.architecture()
    if sys.platform == 'win32' and arch == '32bit':
        return 'win32'
    if sys.platform == 'win32' and arch == '64bit':
        return 'win_amd64'
    if sys.platform == 'linux' and arch == '64bit':
        return 'manylinux1_x86_64'
    if sys.platform == 'darwin' and arch == '64bit':
        return 'macosx_10_13_x86_64'

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
    license='Apache-2.0',
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
