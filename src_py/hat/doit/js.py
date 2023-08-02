from pathlib import Path
import enum
import importlib.resources
import itertools
import json
import subprocess

from . import common
from . import eslint as hat_doit_eslint


def get_task_build_npm(src_dir: Path,
                       build_dir: Path,
                       name: str, *,
                       file_dep=[],
                       task_dep=[],
                       **kwargs):

    def action():
        build_npm(src_dir=src_dir,
                  build_dir=build_dir,
                  name=name,
                  **kwargs)

    return {'actions': [action],
            'file_dep': file_dep,
            'task_dep': task_dep}


def build_npm(src_dir: Path,
              build_dir: Path,
              name: str, *,
              version: str | None = None,
              description: str | None = None,
              keywords: list[str] | None = None,
              homepage: str | None = None,
              license: common.License | None = None,
              author: dict[str, str] | None = None,
              contributors: list[dict[str, str]] | None = None,
              main: str | None = 'index.js',
              browser: str | None = None,
              bin: str | dict[str, str] | None = None,
              man: str | list[str] | None = None,
              repository: str | dict[str, str] | None = None,
              dependencies_path: Path | None = Path('package.json'),
              readme_path: Path | None = None):
    src_conf = common.get_conf()
    src_project_conf = src_conf.get('project', {})

    version = common.get_version(common.VersionType.SEMVER, version)
    dst_conf = {'name': name,
                'version': version}

    if description is None:
        description = src_project_conf.get('description')
    if description is not None:
        dst_conf['description'] = description

    if keywords is not None:
        dst_conf['keywords'] = keywords

    if homepage is None:
        homepage = src_project_conf.get('urls', {}).get('Homepage')
    if homepage is not None:
        dst_conf['homepage'] = homepage

    if license is None:
        license = (common.License(src_project_conf['license']['text'])
                   if ('license' in src_project_conf and
                       'text' in src_project_conf['license'])
                   else common.License.PROPRIETARY)
    dst_conf['license'] = license.value

    if author is None and src_project_conf.get('authors'):
        author = src_project_conf['authors'][0]
    if author is not None:
        dst_conf['author'] = author

    if contributors is None:
        contributors = [
            i for i in itertools.chain(src_project_conf.get('authors', []),
                                       src_project_conf.get('maintainers', []))
            if i != author]
        contributors = contributors or None
    if contributors is not None:
        dst_conf['contributors'] = contributors

    if main is not None:
        dst_conf['main'] = main

    if browser is not None:
        dst_conf['browser'] = browser

    if bin is not None:
        dst_conf['bin'] = bin

    if man is not None:
        dst_conf['man'] = man

    if repository is None:
        repository = src_project_conf.get('urls', {}).get('Repository')
    if repository is not None:
        dst_conf['repository'] = repository

    if dependencies_path is not None:
        dependencies_package = json.loads(dependencies_path.read_text())
        dependencies = dependencies_package.get('dependencies')
        if dependencies:
            dst_conf['dependencies'] = dependencies

    common.rm_rf(build_dir)
    common.cp_r(src_dir, build_dir)

    if readme_path is None and 'readme' in src_project_conf:
        readme_path = Path(src_project_conf['readme'])
    if readme_path is not None:
        dst_readme_path = build_dir / readme_path.with_suffix('.md').name
        subprocess.run(['pandoc',
                        str(readme_path),
                        '-o', str(dst_readme_path)],
                       check=True)

    dst_conf_path = build_dir / 'package.json'
    dst_conf_path.write_text(json.dumps(dst_conf, indent=4),
                             encoding='utf-8')

    subprocess.run(['npm', 'pack', '--silent'],
                   stdout=subprocess.DEVNULL,
                   cwd=str(build_dir),
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

    package = importlib.resources.files(hat_doit_eslint)
    with importlib.resources.as_file(package /
                                     f'{conf.value}.yaml') as conf_path:
        subprocess.run([str(eslint_path),
                        '--parser', parser,
                        '--resolve-plugins-relative-to', '.',
                        '-c', str(conf_path),
                        str(path)],
                       check=True)
