#!/usr/bin/env python3
"""Exercise recording, replay, workloads, CLI failures, and terminal cleanup."""
import fcntl
import json
import os
import pathlib
import pty
import select
import signal
import struct
import subprocess
import tempfile
import termios
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = ROOT / 'build/process_monitor'


def run(*args, code=0):
    """Run a bounded CLI command and check its exit status."""
    result = subprocess.run([str(BIN), *map(str, args)], capture_output=True, text=True, timeout=15)
    assert result.returncode == code, (args, result.returncode, result.stderr)
    return result


def recording_and_workload(directory):
    """Verify that top-N display limits never filter resource recordings."""
    workload = subprocess.Popen(['python3', '-c', 'data=bytearray(32*1024*1024)\nwhile True: sum(range(10000))'])
    try:
        time.sleep(.15)
        path = directory / 'session.jsonl'
        run('--samples', 4, '--interval', '.15', '--top', 1, '--record', path)
        records = [json.loads(line) for line in path.read_text().splitlines()]
        assert records[0]['type'] == 'session'
        assert len(records) == 5
        samples = records[1:]
        assert all(len(sample['processes']) > 1 for sample in samples)
        rows = [p for sample in samples for p in sample['processes'] if p['pid'] == workload.pid]
        assert rows and max(p['rss'] for p in rows) >= 32 * 1024 * 1024
        assert any(p['cpu'] is not None and p['cpu'] > 5 for p in rows[1:])
        assert rows[0]['cpu'] is None
        assert all(p['memory'] is not None for p in rows)
        run('--replay', path, '--interval', '.1')
        run('--record', path, '--samples', 1, code=1)
        truncated = directory / 'truncated.jsonl'
        truncated.write_text(path.read_text() + '{"version":')
        run('--replay', truncated, '--interval', '.1')
        corrupt = directory / 'corrupt.jsonl'
        corrupt.write_text(path.read_text() + 'broken\n')
        run('--replay', corrupt, '--interval', '.1', code=1)
        return records
    finally:
        workload.terminate()
        workload.wait(timeout=5)


def invalid_options():
    """Reject malformed options before starting a session."""
    for args in [('--top','0'),('--sort','network'),('--interval','nan'),('--interval','0'),
                 ('--history','-2'),('--memory-limit','0'),('--samples','-1'),('--top',),
                 ('--ui','web'),('--unknown','x'),('--record','x','--replay','y')]:
        run(*args, code=1)
    assert 'Usage:' in run('--help').stdout


def terminal_cleanup(directory):
    """Exercise interactive commands, resizing, pause, and signal restoration."""
    for shutdown in ('keyboard', 'signal'):
        master, slave = pty.openpty()
        original = termios.tcgetattr(slave)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 100, 0, 0))
        record = directory / f'pty-{shutdown}.jsonl'
        child = subprocess.Popen([str(BIN), '--interval', '.1', '--record', str(record)], stdin=slave, stdout=slave, stderr=slave)
        output = bytearray()
        try:
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                ready, _, _ = select.select([master], [], [], .1)
                if ready:
                    output.extend(os.read(master, 65536))
            os.write(master, b'm5jk? ')
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 16, 68, 0, 0))
            time.sleep(.1)
            count_before = len(record.read_text().splitlines())
            time.sleep(.3)
            count_after = len(record.read_text().splitlines())
            assert count_after > count_before, 'recording must continue while display is paused'
            os.write(master, b' ')
            if shutdown == 'keyboard':
                os.write(master, b'q')
            else:
                child.send_signal(signal.SIGTERM)
            child.wait(timeout=5)
            while select.select([master], [], [], 0)[0]:
                output.extend(os.read(master, 65536))
            assert child.returncode == 0, output.decode(errors='replace')
            assert termios.tcgetattr(slave) == original
            assert b'\x1b[?1049h' in output and b'\x1b[?1049l' in output
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            os.close(master)
            os.close(slave)


def main():
    """Run integration cases in an isolated temporary directory."""
    invalid_options()
    with tempfile.TemporaryDirectory(prefix='process-monitor-test-') as temporary:
        recording_and_workload(pathlib.Path(temporary))
        terminal_cleanup(pathlib.Path(temporary))
    print('PASS integration: workloads, recording/replay, CLI, terminal restoration')


if __name__ == '__main__':
    main()
