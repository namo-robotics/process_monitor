# Sun feedback

Each numbered item below is an independent, issue-ready proposal, ordered by
impact on this project. No GitHub issues have been created. Compiler reproducers
were checked with `sun 0.dev (67560c84f00b)` on Linux x86_64; the first two also
occurred with `9eb5f4ae8f5c`.

## 1. P1 — Diagnose conflicting native symbol signatures before LLVM verification

**Type:** compiler diagnostic/FFI compatibility bug.

Importing stdlib and declaring a correctly typed POSIX signal callback produces
an LLVM verifier error because stdlib already binds `signal` using integers.

```sun
using std;
extern "C" function install(sig: i32, handler: function (i32) void) raw_ptr<u8> as "signal";
function callback(sig: i32) void {}
function main() i32 {
  unsafe { install(2, callback); };
  return 0;
}
manifest { libraries: ["stdlib.moon"] }
```

Run `sun --emit-obj -o repro.o repro.sun`.

**Actual:** `Call parameter type does not match function signature!`, followed by
`Function verification failed: main`.

**Expected:** a source-level diagnostic identifying both conflicting declarations
and the shared native symbol, or supported ABI-compatible signature adaptation.
A typed stdlib signal-registration API would avoid redeclaration entirely.

**Impact/workaround:** terminal shutdown must reliably restore terminal settings.
The monitor currently mirrors stdlib's integer signature and explicitly converts
the callback address at its small unsafe FFI boundary (`src/posix.sun`).

**Acceptance:** the example either compiles with correct ABI behavior or fails
with a precise source diagnostic; incompatible extern declarations imported from
moons are covered by compiler tests.

## 2. P2 — Reject bare returns in value-returning functions during semantic analysis

**Type:** compiler diagnostic bug.

```sun
using std;
function invalid() bool { return; }
function main() i32 {
  if (invalid()) { return 0; }
  return 1;
}
manifest { libraries: ["stdlib.moon"] }
```

Run `sun --emit-obj -o repro.o repro.sun`.

**Actual:** `Function return type does not match operand type of return inst!`,
then an LLVM function-verification failure.

**Expected:** a source diagnostic at `return;` explaining that a Boolean value is
required. Check nested branches and unsafe blocks as well as direct returns.

**Impact/workaround:** changing a terminal input method from `void` to `bool`
exposed this; the application now supplies explicit values on every return path.

**Acceptance:** semantic analysis rejects every reachable bare return in a
non-void function, without relying on LLVM verification.

## 3. P2 — Provide a portable scoped terminal API

**Type:** missing standard-library capability.

The stdlib provides file descriptors and polling, but the monitor must bind
`isatty`, `tcgetattr`, `tcsetattr`, `cfmakeraw`, and `ioctl` itself. Native request
codes and aligned opaque termios storage belong in a shared platform boundary.

**Proposed capability:** scoped raw/cbreak mode with automatic restoration,
terminal-size queries, and nonblocking key reads on Linux and macOS. Keep signal
policy explicit; do not silently install process-wide handlers.

**Impact/workaround:** `src/posix.sun` and `src/terminal.sun` maintain these bindings
and restoration behavior locally.

**Acceptance:** tests cover restoration after normal exit and exceptions, resize,
non-TTY streams, and the documented signal integration on both operating systems.

## 4. P3 — Add bounded buffered line reading for arbitrary files

**Type:** missing standard-library convenience/API.

`std.io.read_line` reads standard input; `File.read_all` reads an entire file.
Streaming recordings need a buffered line reader attached to an arbitrary file,
with a maximum line length and an explicit incomplete-final-line result.

**Proposed capability:** a reusable reader returning complete lines, EOF, and
truncated final data distinctly, while handling short reads and interrupted I/O.

**Impact/workaround:** `Replay` in `src/recording.sun` maintains its own bounded
buffer so a long recording is not loaded into memory at once.

**Acceptance:** tests cover empty files, partial reads, large files, overlong
lines, newline boundaries across buffers, and interrupted final records.
