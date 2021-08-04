from pathlib import Path
import subprocess
import sys

from hat.doit import common


__all__ = ['task_clean_all',
           'task_build']


build_dir = Path('build')
src_py_dir = Path('src_py')
requirements_path = Path('requirements.pip.runtime.txt')
license_path = Path('LICENSE')


def task_clean_all():
    """Clean all"""
    return {'actions': [(common.rm_rf, [build_dir])]}


def task_build():
    """Build"""

    def build():
        common.rm_rf(build_dir)
        build_dir.mkdir(parents=True, exist_ok=True)

        common.cp_r(src_py_dir, build_dir)
        common.rm_rf(*build_dir.rglob('__pycache__'))

        manifest_path = build_dir / 'MANIFEST.in'
        paths = [path for path in build_dir.rglob('*') if not path.is_dir()]
        with open(manifest_path, 'w', encoding='utf-8') as f:
            for path in paths:
                f.write(f"include {path.relative_to(manifest_path.parent)}\n")

        readme = Path('README.rst').read_text().strip()
        requirements = [
            str(i) for i in common.read_pip_requirements(requirements_path)]
        version = common.get_version(common.VersionType.PIP)
        setup_py = _setup_py.format(readme=repr(readme),
                                    requirements=repr(requirements),
                                    version=repr(version))
        (build_dir / 'setup.py').write_text(setup_py)

        common.cp_r(license_path, build_dir / 'LICENSE')

        subprocess.run([sys.executable, 'setup.py', '-q', 'bdist_wheel'],
                       cwd=str(build_dir),
                       check=True)

    return {'actions': [build]}


_setup_py = r"""
from setuptools import setup

readme = {readme}
requirements = {requirements}
version = {version}

setup(
    name='hat-doit',
    version=version,
    description='Hat build utility functions',
    long_description=readme,
    long_description_content_type='text/x-rst',
    url='https://github.com/hat-open/hat-doit',
    license='Apache-2.0',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License'],
    packages=['hat'],
    include_package_data=True,
    install_requires=requirements,
    python_requires='>=3.8',
    options={{
        'bdist_wheel': {{
            'python_tag': 'cp38.cp39',
            'py_limited_api': 'cp38.cp39',
            'plat_name': 'any'
        }}
    }},
    zip_safe=False)
"""
