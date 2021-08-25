from pathlib import Path
import enum
import json
import subprocess
import sys
import tempfile

from . import common


class SphinxOutputType(enum.Enum):
    HTML = 'html'
    LATEX = 'latex'


def build_sphinx(out_type: SphinxOutputType,
                 src: Path,
                 dest: Path):
    common.mkdir_p(dest)
    subprocess.run([sys.executable, '-m', 'sphinx', '-q', '-b', out_type.value,
                    str(src), str(dest)],
                   check=True)


def build_latex(src: Path, dest: Path):
    common.mkdir_p(dest)
    for i in src.glob('*.tex'):
        subprocess.run(['xelatex', '-interaction=batchmode',
                        f'-output-directory={dest.resolve()}', i.name],
                       cwd=src, stdout=subprocess.DEVNULL, check=True)


def build_pdoc(module: str, dest: Path):
    common.mkdir_p(dest)
    subprocess.run([sys.executable, '-m', 'pdoc',
                    '--html', '--skip-errors', '-f',
                    '-o', str(dest), module],
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL,
                   check=True)


def build_jsdoc(src: Path,
                dest: Path,
                node_modules_dir: Path = Path('node_modules'),
                template: str = 'node_modules/docdash'):
    common.mkdir_p(dest)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        conf_path = tmpdir / 'jsdoc.json'
        conf_path.write_text(json.dumps({
            "source": {
                "include": str(src)
            },
            "plugins": [
                "plugins/markdown"
            ],
            "opts": {
                "template": template,
                "destination": str(dest),
                "recurse": True
            },
            "templates": {
                "cleverLinks": True
            }
        }), encoding='utf-8')
        subprocess.run([str(node_modules_dir / '.bin/jsdoc'),
                        '-c', str(conf_path)],
                       check=True)
