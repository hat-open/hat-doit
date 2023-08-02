from pathlib import Path
import enum
import importlib.resources
import json
import subprocess
import sys
import tempfile
import typing

import sphinx.application

from . import common
from . import sphinx as hat_doit_sphinx


class SphinxOutputType(enum.Enum):
    HTML = 'html'
    LATEX = 'latex'


def build_sphinx(src_dir: Path,
                 dst_dir: Path,
                 project: str,
                 out_type: SphinxOutputType = SphinxOutputType.HTML,
                 extensions: typing.Iterable[str] = [],
                 version: str | None = None,
                 copyright: str = '2020-2023, Hat Open AUTHORS',
                 static_paths: typing.Iterable[Path] = [],
                 conf: dict[str, typing.Any] = {}):
    common.mkdir_p(dst_dir)
    version = common.get_version(common.VersionType.PIP, version)

    package = importlib.resources.files(hat_doit_sphinx)
    with importlib.resources.as_file(package / 'static') as static_path:
        conf = {'extensions': ['sphinx.ext.todo',
                               *extensions],
                'version': version,
                'project': project,
                'copyright': copyright,
                'html_theme': 'furo',
                'html_static_path': [str(static_path),
                                     *(str(i) for i in static_paths)],
                'html_css_files': ['hat.css'],
                'html_use_index': False,
                'html_show_sourcelink': False,
                'html_show_sphinx': False,
                'html_sidebars': {'**': ['sidebar/brand.html',
                                         'sidebar/scroll-start.html',
                                         'sidebar/navigation.html',
                                         'sidebar/scroll-end.html']},
                'todo_include_todos': True,
                **conf}

        app = sphinx.application.Sphinx(srcdir=str(src_dir),
                                        confdir=None,
                                        outdir=str(dst_dir),
                                        doctreedir=str(dst_dir / '.doctrees'),
                                        buildername=out_type.value,
                                        confoverrides=conf,
                                        status=None)
        app.build()


def build_latex(src_dir: Path,
                dst_dir: Path,
                n_passes: int = 1):
    common.mkdir_p(dst_dir)
    for _ in range(n_passes):
        for i in src_dir.glob('*.tex'):
            subprocess.run(['xelatex',
                            '-interaction=batchmode',
                            f'-output-directory={dst_dir.resolve()}',
                            i.name],
                           cwd=src_dir,
                           stdout=subprocess.DEVNULL,
                           check=True)


def build_pdoc(module: str,
               dst_dir: Path,
               exclude: list[str] = []):
    common.mkdir_p(dst_dir)
    subprocess.run([sys.executable, '-m', 'pdoc',
                    '-d', 'google',
                    '-o', str(dst_dir),
                    module,
                    *(f'!{i}' for i in exclude)],
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL,
                   check=True)


def build_jsdoc(src_dir: Path,
                dst_dir: Path,
                node_modules_dir: Path = Path('node_modules'),
                template: str = 'node_modules/docdash'):
    common.mkdir_p(dst_dir)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        conf_path = tmpdir / 'jsdoc.json'
        conf_path.write_text(json.dumps({
            "source": {
                "include": str(src_dir)
            },
            "plugins": [
                "plugins/markdown"
            ],
            "opts": {
                "template": template,
                "destination": str(dst_dir),
                "recurse": True
            },
            "templates": {
                "cleverLinks": True
            }
        }), encoding='utf-8')
        subprocess.run([str(node_modules_dir / '.bin/jsdoc'),
                        '-c', str(conf_path)],
                       check=True)
