# Process monitor

A Sun CLI for finding processes that consume CPU and resident memory. It provides
an interactive process table, top-N rankings, colored history plots, best-effort ROS 2
names, and JSON Lines recording/replay. No elevated privileges are required.

Network monitoring and web hosting are **not included in v1**. The released
`sun_serve` archive contains a static-file server but no precompiled library for
our live handlers. Future stages are recorded in [FOLLOWUP.md](../FOLLOWUP.md).

## Build and run

Install the Sun toolchain identified in [toolchain.lock.json](../toolchain.lock.json),
a native C linker/toolchain, Bash, and Python 3. Python is used by build checks and
tests; the monitor itself is entirely Sun with platform FFI bindings.

```sh
scripts/build.sh
build/process_monitor
build/process_monitor --top 5 --sort memory
build/process_monitor --top all --interval 0.5 --history 300
```

The build checks the compiler revision. `SUN_BIN=/path/to/sun` selects another
installation; `ALLOW_UNTESTED_SUN=1` explicitly permits an untested revision.
Builds use native dynamic linking. On macOS the build also links libproc.
`process_monitor --version` prints the source commit embedded during the build.
When building without Git metadata, set `BUILD_REVISION` to the full commit SHA;
otherwise the version is reported as `unknown`.

| Target | Implementation | Validation in this workspace |
| --- | --- | --- |
| Linux x86_64 | `/proc` collector and terminal | Native build, unit tests, workload and PTY tests |
| Linux ARM64 | Same collector, target-specific Sun stdlib | Cross-compiled object; native execution pending |
| Apple Silicon macOS | libproc/sysctl collector and terminal | Cross-compiled object; native execution pending |

ARM64 and macOS runtime support remains provisional until the native acceptance
checks in `FOLLOWUP.md` pass. Cross-compilation is not a substitute for those checks.

## CI and binary releases

[The GitHub Actions workflow](../.github/workflows/ci.yml) downloads released Sun
compilers and stdlibs, checking every artifact against `toolchain.lock.json`.
It never builds the compiler or stdlib from source. LLVM 20 is a binary runtime
dependency. Downloads are cached, but checksums are verified on every run.

The release currently supplies Linux x86_64 and Apple Silicon compilers. Linux
ARM64 uses the released x86_64 compiler, ARM64 stdlib, and a GNU cross linker.
A separate native ARM64 job runs the resulting unit, workload, recording/replay,
and PTY tests. The other two platforms also run their tests natively, without
installing Sun in test jobs. Pushes, pull requests, and manual runs are supported.

The upstream `dev` tag moves. If its artifacts change, CI fails checksum validation
instead of silently upgrading. Review the new release, update its revision and
artifact hashes in the lock, and rerun compatibility tests. No `sun_serve` artifacts
are required.

Each successful job uploads a `.tar.gz` archive and SHA-256 checksum as workflow
artifacts. After all three native jobs pass, every branch push updates the same
[`dev` prerelease](https://github.com/namo-robotics/process_monitor/releases/tag/dev),
replacing its archives and `SHA256SUMS`. The `dev` tag and release notes identify
the packaged commit. Publication is serialized across branches to prevent mixed
uploads. Pull requests and manual runs only upload workflow artifacts.

Pushing a version tag such as `v0.1.0` publishes a separate GitHub Release.
Versioned uploads stay in a draft until all assets arrive; a rerun can resume a
draft but will not replace an already published versioned release. Each release
includes all three archives and `SHA256SUMS`. The installer selects the latest
stable release; development builds are available from the `dev` prerelease.

Extract the archive for your architecture and run `./process_monitor`. Sun is not
needed at runtime. Linux packages target Ubuntu 24.04's system libraries; older
distributions may not provide the required glibc/libstdc++. macOS packages target
macOS 14 or later on Apple Silicon and are not Developer ID signed or notarized.
Each archive includes the license, documentation, compiler lock, and build metadata.
CI smoke-tests the extracted executable before uploading it.

The binary-only workflow has not yet completed a run on GitHub. The native support status above remains
provisional until those jobs and the remaining manual checks pass.

## Controls and options

| Key | Action |
| --- | --- |
| `c` / `m` | Rank by CPU / memory |
| `5` / `0` / `a` | Show top 5 / top 10 / all |
| `↓` / `↑` | Select the next / previous ranked process; scroll as needed |
| `t` / `k` | Send SIGTERM / SIGKILL to the selected live process |
| Space | Pause/resume display; collection and recording continue |
| `?` or `h` | Toggle help |
| `q` or Ctrl-C | Quit and restore the terminal |

Process actions run immediately and report success or failure above the table.
`t` requests graceful shutdown; `k` forcibly stops the process. Replay disables
both actions. PID 1, process groups, and the monitor itself are protected.
Linux uses a PID handle and rechecks the start time to prevent signalling a reused
PID. macOS rechecks the start time immediately before `kill`; its POSIX API still
has a small race between that check and signalling. OS permissions apply, and
Linux signalling requires kernel PID-handle support and glibc 2.36 or later.

The highlighted row keeps its identity as rankings change. The history panel is
independent of that selection: it plots the **current top five processes** for the
ranked resource, even if `--top` shows fewer or more rows. Press `c` for CPU or `m`
for resident memory. CPU uses percent of one core; memory uses RSS MiB.

The panel uses colored filled dot areas, a shared vertical scale, and elapsed time on the
horizontal axis (oldest at left, newest at right). A matching legend identifies
processes by PID and name. Colors stay attached to identities while they remain
in the graph, including when their ranks change. Newly entering processes show
their visible history; missing samples leave gaps. The graph grows left to right
over a fixed 60-second span, then scrolls older samples left. Use `--graph-window`
to change that span independently of history retention. The time axis shows
seconds since the first sample; unfilled future time stays blank. Each plotted column fills down to the baseline. Shorter columns appear in front
of taller ones at each time position, including where histories cross. A terminal
cell has one foreground color, so boundaries within a cell use the shorter area’s color. With fewer than five available measurements, only
those processes are plotted. The first CPU sample waits for a counter baseline.

Interactive mode uses cyan table borders and column dividers, a blue selected-row
highlight, and a separate bordered top-five history plot. An asterisk marks the sorted
column. Names are clipped with `~` when space is limited. The layout needs at least
65 columns and 17 rows and scrolls the selected row into view. Redirected output
prints aligned tables and monochrome dot plots without terminal control sequences.

```text
--ui terminal          only terminal mode is available in v1
--top N|all             default: 10
--sort cpu|memory       default: cpu
--interval SECONDS     default: 1; range: 0.1 through 604800
--graph-window SECONDS default: 60; same range as interval
--history SECONDS      default: 600; same range as interval
--memory-limit MiB     estimated retained-history budget; default: 64; range: 1..4096
--record FILE          create a new recording; existing files are refused
--replay FILE          stream a recording at the configured display interval
--labels FILE          explicit live-process labels
--samples N            exit after N samples
--help                 show usage
--version              show the build's source commit
```

## Measurements and retention

- CPU is a counter delta divided by actual monotonic elapsed time. **100% means
  one logical core**, so multithreaded processes can exceed 100%. The first sample,
  counter resets, and unavailable counters appear as `N/A`.
- Memory is resident set size (RSS), in MiB and as a percentage of physical RAM.
  It is not private memory: shared pages can be counted in multiple processes.
- Collection always visits every visible process; rankings only affect display.
  Identity combines PID and start time to prevent history crossing PID reuse.
- Processes that exit during reads or whose identity cannot be read are counted
  as skipped. Unavailable measurements within an otherwise readable process stay
  unknown, distinct from zero. Processes hidden completely by the OS cannot be counted.
- History evicts oldest complete frames by duration and a conservative storage
  estimate. The displayed retention window reflects available history. Exited
  processes remain in retained frames. An individual frame larger than the budget
  is displayed and recorded but not retained.
- The memory budget governs estimated retained sample storage, **not total program
  RSS**. Current/baseline frames, vector capacity, parsing, terminal rendering, and
  recording buffers use additional memory.

Visibility follows the current process namespace and OS permissions. A monitor
inside a container sees the processes exposed to that container, not necessarily
all host processes. Processes shorter than the sampling interval can be missed.
Process actions apply only to selected live processes on the local machine.

## ROS 2 labels

The default label is the executable basename. Inside `--ros-args`, unscoped
`__node:=`, `__name:=`, and `__ns:=` remaps provide a best-effort fully qualified
node label. Executables containing `component_container` are marked as shared
containers: their measurements cover the entire process, not individual nodes.
Live graph discovery and node-scoped remaps are deferred.

For ambiguous processes, supply a JSON object:

```json
{"1234": "/robot/camera", "5678": "navigation container"}
```

```sh
build/process_monitor --labels labels.json
```

Overrides bind only to matching process identities in the first live sample.
An absent PID or a later reuse of that PID will not inherit the override. Labels
are not hot-reloaded. Both the PID and derived label remain visible; full
executable paths are preserved in recordings.

## Recording and replay

```sh
build/process_monitor --record session.jsonl --top 5
build/process_monitor --replay session.jsonl --interval 0.2
```

Recordings contain a versioned session header followed by one `sample` object per
line. Samples include wall-clock milliseconds, monotonic elapsed milliseconds,
physical memory, skipped count, and all visible processes. Each process includes
its stable `id`, PID, string start marker, executable, label, CPU percentage, RSS
bytes, and memory percentage. Unknown measurements are JSON `null`. Raw command
arguments and environment variables are not recorded.

Replay uses recorded timestamps and measurements without querying live processes.
`--interval` controls playback cadence. History limits still apply. An unfinished
final line is ignored; malformed complete lines and unsupported versions are
errors. Each input line is limited to 64 MiB. At EOF an interactive replay remains
open for inspection; redirected replay exits. Replay and recording cannot be
combined, and replay uses the labels stored in the recording.

## Development and tests

```sh
scripts/test.sh
scripts/check-targets.sh  # requires target stdlib bundles under SUN_LIB_ROOT
sun fmt --check src tests
```

`src/main.sun` exposes the CLI boundary. Internal code lives in the
`process_monitor` module, separated into focused source units: OS collectors,
sample model and metrics, history, ranking, labels, recording codec and streaming,
CLI options, terminal management, and pure chart formatting. `Session` owns the
lifecycle; collectors do not know about the UI or recording. Block comments
explain every module, class, function, and method.

[SUN_FEEDBACK.md](../SUN_FEEDBACK.md) contains prioritized issue-ready Sun feedback.
No issues or pull requests are created by this repository's build or test scripts.
