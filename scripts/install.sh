#!/usr/bin/env bash
# Install the latest published native binary after verifying its release checksum.
set -euo pipefail

# Select the archive matching the current operating system and CPU architecture.
case "$(uname -s):$(uname -m)" in
  Linux:x86_64) target=linux-x86_64 ;;
  Linux:aarch64|Linux:arm64) target=linux-arm64 ;;
  Darwin:arm64) target=macos-arm64 ;;
  *) echo 'Supported targets: Linux x86_64/ARM64 and Apple Silicon macOS.' >&2; exit 1 ;;
esac

# Prefer a stable release and use the development build when none exists.
repository=https://github.com/namo-robotics/process_monitor
response=$(curl --silent --show-error --location --output /dev/null --write-out '%{http_code} %{url_effective}' "$repository/releases/latest")
status=${response%% *}
release_url=${response#* }
if [[ "$status" == 404 || ( "$status" == 200 && "$release_url" == "$repository/releases" ) ]]; then
  version=dev
elif [[ "$status" == 200 ]]; then
  version=${release_url##*/}
else
  echo "Could not resolve the latest release (HTTP $status)." >&2
  exit 1
fi
if [[ "$version" != dev && ! "$version" =~ ^v[0-9][A-Za-z0-9._-]*$ ]]; then
  echo 'No supported published release was found.' >&2
  exit 1
fi
archive="process_monitor-$version-$target.tar.gz"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
curl --fail --silent --show-error --location "$repository/releases/download/$version/$archive" -o "$work/$archive"
curl --fail --silent --show-error --location "$repository/releases/download/$version/SHA256SUMS" -o "$work/SHA256SUMS"

# Verify just the selected archive using the checksum utility available on the host.
expected=$(awk -v name="$archive" '$2 == name {print $1}' "$work/SHA256SUMS")
if command -v sha256sum >/dev/null; then
  actual=$(sha256sum "$work/$archive")
else
  actual=$(shasum -a 256 "$work/$archive")
fi
if [[ ! "$expected" =~ ^[0-9a-f]{64}$ || "${actual%% *}" != "$expected" ]]; then
  echo 'Release checksum verification failed.' >&2
  exit 1
fi

# Extract only the executable and install it without requiring elevated privileges.
binary="process_monitor-$version-$target/process_monitor"
tar -xzf "$work/$archive" -C "$work" "$binary"
install_dir="${PREFIX:-$HOME/.local}/bin"
mkdir -p "$install_dir"
install -m 755 "$work/$binary" "$install_dir/process_monitor"
printf 'Installed %s\nRun: %s/process_monitor\n' "$version" "$install_dir"
case ":$PATH:" in
  *":$install_dir:"*) ;;
  *) printf 'Add to your shell PATH: export PATH="%s:$PATH"\n' "$install_dir" ;;
esac
