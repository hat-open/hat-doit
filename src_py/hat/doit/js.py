from pathlib import Path
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
              dependencies: typing.Dict[str, str] = {}):
    common.rm_rf(dst_dir)
    common.cp_r(src_dir, dst_dir)

    dst_readme_path = dst_dir / readme_path.with_suffix('.md').name
    subprocess.run(['pandoc', str(readme_path), '-o', str(dst_readme_path)],
                   check=True)

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

    (dst_dir / 'package.json').write_text(json.dumps(conf, indent=4))
    subprocess.run(['npm', 'pack', '--silent'],
                   stdout=subprocess.DEVNULL,
                   cwd=str(dst_dir),
                   check=True)


def run_eslint(path: Path,
               node_modules_dir: Path = Path('node_modules')):
    subprocess.run([str(node_modules_dir / '.bin/eslint'), str(path)],
                   check=True)
