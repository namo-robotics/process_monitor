# Follow-up stages

This file preserves stages deferred from the implementation plan. CPU/memory
terminal monitoring and recording/replay are implemented. Network monitoring is
outside the agreed v1 scope and is not required to complete these stages.

## 1. Native Linux ARM64 validation

**Prerequisite:** an ARM64 Linux host, native linker, and the pinned Sun compiler
with an architecture-matched stdlib. This workspace only provides x86_64 runtime
validation; ARM64 object generation has been checked.

- Run `scripts/test.sh` natively. Include a multithreaded CPU workload and a known
  resident-memory allocation; verify one-core CPU semantics, process churn, PID
  identity, permissions, history eviction, and recording/replay.
- Exercise terminal resize, display pause while recording, keyboard quit, and
  SIGTERM restoration on a real terminal.
- Measure overhead with the expected robot process count and history duration.
- Record OS, kernel, architecture, compiler revision, and results in this file.

**Acceptance:** native build and all tests pass, memory stays bounded by retained
history plus documented working buffers, and terminal settings restore reliably.
Only then mark Linux ARM64 runtime support verified in the README.

## 2. Native Apple Silicon validation

**Prerequisite:** a native Apple Silicon Mac, Xcode command-line tools, and a
matching Sun toolchain. Mach-O object generation passes here; no Mac runtime is
available.

- Build with `scripts/build.sh`; verify libproc linkage and the BSD identity layout
  against the installed SDK. Confirm CPU counters use the expected Mach timebase.
- Run unit and integration tests natively. Compare controlled CPU and RSS workloads
  against Activity Monitor or native system tools, allowing for sampling timing.
- Verify process enumeration under churn, protected-process behavior, argv parsing
  without environment leakage, stable start identifiers, and ROS labels.
- Exercise terminal settings and resize handling, signals, recording, and replay.
- Record the macOS release, chip, compiler revision, and results here.

**Acceptance:** native runtime tests pass and CPU percentages match controlled
workloads. Update the README's validation status only after these checks.

## 3. Web dashboard using released sun_serve artifacts

**Current blocker:** the inspected rolling `dev` release includes only
`sun_serve-dev-linux-x86_64/{sun_serve,README.md,LICENSE}`. It contains no
`sun_serve.moon` library. The binary serves static files but cannot host the
planned application handlers directly. Per the revised user instruction, v1 does
not rebuild sun_serve or maintain a compiler-compatibility patch for it.

**Prerequisite:** a released precompiled library compatible with the selected Sun
compiler and target architecture, or an explicitly agreed static-file publication
architecture. Pin an immutable release/artifact digest; do not depend on a moving
`dev` tag for reproducible builds.

- Add `--ui web|both` only when a usable artifact is available. Keep terminal mode
  independent of web dependencies.
- Reuse the same collector and bounded history. Publish immutable snapshots so
  server workers neither collect processes nor hold long history locks.
- Expose versioned read-only status, snapshot, and identity-scoped history APIs.
  Preserve nulls, recording identities, replay timestamps, and exited histories.
- Bundle an offline HTML/CSS/JavaScript dashboard with top-5/top-10/custom/all
  controls, CPU/memory ranking, stable colors, and separate history scales.
- Bind to `127.0.0.1:8080` by default for local access or SSH tunneling. Validate
  API inputs and render process names as text.
- Test multiple clients, reconnects, selected-process exit, simultaneous terminal
  and browser views, replay, and graceful shutdown.

**Acceptance:** live browser graphs and filters work without changing collection
or recordings. Linux ARM64 web support additionally requires a released ARM64
artifact and native tests. Native macOS web hosting remains a separate stage,
requiring upstream server support and a released compatible artifact.

## 4. Optional ROS discovery improvements

Best-effort unscoped ROS remaps and explicit labels are implemented. If live ROS
graph discovery or node-scoped remaps are needed, agree the supported ROS
distributions and PID-mapping strategy first. Preserve process-level accounting:
multiple nodes in one process must not be presented as independently measured.

**Acceptance:** discovery handles multiple nodes per process, renamed nodes,
namespaces, process exits, and absent ROS installations without blocking sampling.
