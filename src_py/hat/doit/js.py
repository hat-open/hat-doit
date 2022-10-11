from pathlib import Path
import enum
import importlib.resources
import json
import subprocess
import typing

from . import common


def build_npm(src_dir: Path,
              dst_dir: Path,
              name: str,
              description: str,
              license: common.License,
              readme_path: Path = Path('README.rst'),
              version_path: Path = Path('VERSION'),
              main: str = 'index.js',
              homepage: typing.Optional[str] = None,
              repository: typing.Optional[str] = None,
              dependencies_path: typing.Optional[Path] = Path('package.json')):
    common.rm_rf(dst_dir)
    common.cp_r(src_dir, dst_dir)

    dst_readme_path = dst_dir / readme_path.with_suffix('.md').name
    subprocess.run(['pandoc', str(readme_path), '-o', str(dst_readme_path)],
                   check=True)

    dependencies_package = (json.loads(dependencies_path.read_text())
                            if dependencies_path else {})
    dependencies = dependencies_package.get('dependencies')

    conf = {
        'name': name,
        'description': description,
        'license': license.value,
        'version': common.get_version(version_type=common.VersionType.SEMVER,
                                      version_path=version_path),
        'main': main}
    if homepage:
        conf['homepage'] = homepage
    if repository:
        conf['repository'] = repository
    if dependencies:
        conf['dependencies'] = dependencies

    (dst_dir / 'package.json').write_text(json.dumps(conf, indent=4),
                                          encoding='utf-8')
    subprocess.run(['npm', 'pack', '--silent'],
                   stdout=subprocess.DEVNULL,
                   cwd=str(dst_dir),
                   check=True)


class ESLintConf(enum.Enum):
    JS = 'js'
    TS = 'ts'


def run_eslint(path: Path,
               conf: ESLintConf = ESLintConf.JS,
               eslint_path: Path = Path('node_modules/.bin/eslint')):
    if conf == ESLintConf.JS:
        parser = 'espree'

    elif conf == ESLintConf.TS:
        parser = '@typescript-eslint/parser'

    else:
        raise ValueError('unsupported conf')

    # TODO: change 'hat.doit.eslint' with imported module
    with importlib.resources.path('hat.doit.eslint',
                                  f'{conf.value}.yaml') as conf_path:
        subprocess.run([str(eslint_path),
                        '--parser', parser,
                        '--resolve-plugins-relative-to', '.',
                        '-c', str(conf_path),
                        str(path)],
                       check=True)
