#!/usr/bin/env python3
"""Install checksum-pinned, precompiled Sun artifacts without building sources."""

import hashlib
import json
import pathlib
import platform
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PREFIX = ROOT / '.ci/toolchain'
DOWNLOADS = ROOT / '.ci/downloads'


def download(name, artifact):
    """Fetch a release asset and reject replacement bytes under a rolling tag."""
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    destination = DOWNLOADS / name
    if not destination.exists():
        temporary = destination.with_suffix(destination.suffix + '.part')
        subprocess.run(['curl', '--fail', '--location', '--retry', '3',
                        artifact['url'], '--output', str(temporary)], check=True)
        temporary.replace(destination)
    if hashlib.sha256(destination.read_bytes()).hexdigest() != artifact['sha256']:
        raise RuntimeError(f'{name}: checksum mismatch; review and update toolchain.lock.json')
    return destination


def install_compiler(archive, linux):
    """Extract only the released compiler into a consistent installation layout."""
    with tempfile.TemporaryDirectory() as temporary:
        stage = pathlib.Path(temporary)
        if linux:
            subprocess.run(['dpkg-deb', '--extract', str(archive), str(stage)], check=True)
            executable = stage / 'usr/bin/sun'
        else:
            subprocess.run(['tar', '-xzf', str(archive), '-C', str(stage), 'bin/sun'], check=True)
            executable = stage / 'bin/sun'
        (PREFIX / 'bin').mkdir(parents=True, exist_ok=True)
        shutil.copy2(executable, PREFIX / 'bin/sun')


def main():
    """Install a supported compiler host and its native and cross-target stdlibs."""
    host = (platform.system(), platform.machine())
    if host == ('Linux', 'x86_64'):
        compiler = 'sun_0.dev_amd64.deb'
        native = 'x86_64-linux-gnu'
        targets = [native, 'aarch64-linux-gnu']
    elif host == ('Darwin', 'arm64'):
        compiler = 'sun-0.dev-arm64-apple-darwin.tar.gz'
        native = 'arm64-apple-darwin'
        targets = [native]
    else:
        raise SystemExit('No pinned precompiled Sun compiler for this host; build ARM64 Linux on x86_64')
    lock = json.loads((ROOT / 'toolchain.lock.json').read_text())['sun']
    artifacts = lock['artifacts']
    install_compiler(download(compiler, artifacts[compiler]), host[0] == 'Linux')
    library = PREFIX / 'lib/sun'
    for target in targets:
        name = f'stdlib-{target}.moon'
        bundle = download(name, artifacts[name])
        (library / target).mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundle, library / target / 'stdlib.moon')
    shutil.copy2(library / native / 'stdlib.moon', library / 'stdlib.moon')
    version = subprocess.check_output([str(PREFIX / 'bin/sun'), '--version'], text=True)
    if lock['revision'][:12] not in version:
        raise RuntimeError(f'Released compiler revision does not match lock: {version}')
    print(version.strip())


if __name__ == '__main__':
    main()
