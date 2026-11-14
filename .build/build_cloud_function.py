"""Build a credential-free FunctionGraph custom-runtime ZIP on Linux."""
import argparse
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def build(output):
    if sys.platform != 'linux':
        raise SystemExit('华为云部署包必须在与目标架构兼容的 Linux 环境构建')
    output = output.resolve()
    archive = output.parent / (output.name + '.zip')
    if output.exists() or archive.exists():
        raise SystemExit('输出目录或 ZIP 已存在，请使用 --output 选择新路径；不会覆盖已有账号文件')
    (ROOT / 'build').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cloud-', dir=ROOT / 'build') as temporary:
        temporary = Path(temporary)
        stage = temporary / 'package'
        stage.mkdir()
        subprocess.run([
            sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--name', 'index',
            '--distpath', str(stage), '--workpath', str(temporary / 'work'),
            '--specpath', str(temporary), str(ROOT / 'src' / 'index.py'),
        ], cwd=ROOT, check=True)
        bootstrap = stage / 'bootstrap'
        bootstrap.write_text((ROOT / 'cloud_functions' / 'bootstrap').read_text(encoding='utf-8'),
                             encoding='utf-8', newline='\n')
        bootstrap.chmod(0o755)
        (stage / 'index' / 'index').chmod(0o755)
        (stage / 'INPUT_HYPERGRYPH_TOKEN.txt').write_text('', encoding='utf-8')
        (stage / 'BUILD_INFO.json').write_text(json.dumps({
            'python': platform.python_version(), 'machine': platform.machine(),
            'libc': platform.libc_ver(), 'credentials': 'not included',
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stage, output)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
        for file in sorted(output.rglob('*')):
            if file.is_file():
                package.write(file, file.relative_to(output).as_posix())
    print(f'部署目录：{output}\n部署 ZIP：{archive}')
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist' / 'cloud_functions')
    build(parser.parse_args().output)
