<h1 align="center">Process Monitor</h1>

<p align="center">
  <img src="assets/screenshot.png" alt="Process monitor terminal dashboard">
</p>

<h2 align="center">Written in <a href="https://github.com/namo-robotics/sun">Sun</a></h2>

<p align="center">
  <a href="https://github.com/namo-robotics/process_monitor/actions/workflows/ci.yml">
    <img src="https://github.com/namo-robotics/process_monitor/actions/workflows/ci.yml/badge.svg" alt="CI status">
  </a>
</p>

```sh
curl -fsSL https://raw.githubusercontent.com/namo-robotics/process_monitor/main/scripts/install.sh | bash
```

Installs the latest release to `~/.local/bin` on Linux x86_64/ARM64 or Apple Silicon.
Requires a published release; Linux builds target Ubuntu 24.04+, macOS builds target 14+.

A CPU and memory process monitor written in Sun, with ROS 2 labels, colored top-five
history graphs, and recording/replay. Terminal only; no network monitoring.

```sh
process_monitor --top 5 --sort cpu
process_monitor --record session.jsonl
process_monitor --replay session.jsonl
```

`↑/↓` select · `c/m` CPU/memory · `5/0/a` top 5/10/all · `t/k` terminate/kill ·
Space pause · `?` help · `q` quit. Use `--help` for options.

[Build, usage, and CI details](docs/GUIDE.md) · [Planned work](FOLLOWUP.md) · [Sun feedback](SUN_FEEDBACK.md)
