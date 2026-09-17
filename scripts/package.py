#!/usr/bin/env python3
"""Package and smoke-test a native monitor binary with release provenance."""

import hashlib
import json
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def native_target():
    """Return the supported release target for the machine doing the packaging."""
    targets = {
        ('Linux', 'x86_64'): 'linux-x86_64',
        ('Linux', 'aarch64'): 'linux-arm64',
        ('Darwin', 'arm64'): 'macos-arm64',
    }
    return targets[(platform.system(), platform.machine())]


def stage_payload(directory, version, target, revision):
    """Copy the executable and documentation and describe their build origin."""
    shutil.copy2(ROOT / 'build/process_monitor', directory / 'process_monitor')
    for name in ('README.md', 'LICENSE', 'FOLLOWUP.md', 'toolchain.lock.json'):
        shutil.copy2(ROOT / name, directory / name)
    (directory / 'docs').mkdir()
    shutil.copy2(ROOT / 'docs/GUIDE.md', directory / 'docs/GUIDE.md')
    (directory / 'assets').mkdir()
    shutil.copy2(ROOT / 'assets/screenshot.png', directory / 'assets/screenshot.png')
    metadata = {
        'version': version,
        'revision': revision,
        'target': target,
        'build_os': platform.platform(),
        'sun_revision': json.loads((ROOT / 'toolchain.lock.json').read_text())['sun']['revision'],
    }
    (directory / 'build-info.json').write_text(json.dumps(metadata, indent=2) + '\n')


def smoke_test(binary, revision):
    """Run the extracted executable without depending on the compiler or workspace."""
    version = subprocess.run([str(binary), '--version'], check=True, capture_output=True,
                             text=True, timeout=15, cwd=binary.parent)
    if version.stdout.strip() != f'process_monitor {revision}':
        raise ValueError('Executable commit does not match the release metadata')
    subprocess.run([str(binary), '--help'], check=True, capture_output=True, timeout=15,
                   cwd=binary.parent)
    subprocess.run([str(binary), '--samples', '2', '--interval', '0.1', '--top', '1'],
                   check=True, capture_output=True, timeout=15, cwd=binary.parent)


def package(version, target, revision):
    """Write a native archive and checksum only after its extracted binary runs."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', version):
        raise ValueError('Version must contain only letters, digits, dots, underscores, or hyphens')
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Expected a full source commit SHA')
    if target != native_target():
        raise ValueError('Release packages must be built and tested on their native architecture')
    name = f'process_monitor-{version}-{target}'
    destination = ROOT / 'dist'
    destination.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        work = pathlib.Path(temporary)
        payload = work / name
        payload.mkdir()
        stage_payload(payload, version, target, revision)
        archive = work / f'{name}.tar.gz'
        with tarfile.open(archive, 'w:gz') as output:
            output.add(payload, arcname=name)
        extracted = work / 'extracted'
        # The archive is created above exclusively from our fixed payload files.
        with tarfile.open(archive) as source:
            source.extractall(extracted)
        smoke_test(extracted / name / 'process_monitor', revision)
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        shutil.copy2(archive, destination / archive.name)
        (destination / f'{archive.name}.sha256').write_text(f'{checksum}  {archive.name}\n')
    print(destination / archive.name)


def main():
    """Parse the release metadata supplied by the CI matrix."""
    if len(sys.argv) != 4:
        raise SystemExit('Usage: package.py VERSION TARGET COMMIT_SHA')
    package(*sys.argv[1:])


if __name__ == '__main__':
    main()
