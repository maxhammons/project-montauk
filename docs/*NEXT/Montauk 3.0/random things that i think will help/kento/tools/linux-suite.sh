#!/bin/sh
# Runs Kento's suite inside a Linux container as a non-root user.
#
#   docker run --rm -v "$PWD":/src:ro -v "$PWD/tools/linux-suite.sh":/s.sh:ro \
#       rust:1.97 sh /s.sh
#   docker run --rm -v "$PWD":/src:ro -v "$PWD/tools/linux-suite.sh":/s.sh:ro \
#       rust:1.97-alpine sh /s.sh
#
# Non-root is not incidental: lock_directory and lock_file panic rather than
# skip when mode bits are not enforced, so a root run fails the very tests that
# depend on a denied write.
#
# Both images are worth running. glibc and musl differ in path resolution, in
# the error kinds the standard library reports, and most of all in locale
# support, which this suite exercises deliberately.
set -e

# ShellCheck is a hard requirement, not a nicety: Kento refuses to report clean
# on a shell file it could not check, so the suite cannot run without it.
if command -v apk >/dev/null 2>&1; then
    apk add --no-cache git shellcheck >/dev/null
    adduser -D kento
else
    apt-get update -qq >/dev/null && apt-get install -y -qq shellcheck >/dev/null
    useradd -m kento
fi

mkdir -p /work
# The repo is copied, never written in place, so the container cannot leave
# root-owned files in the host tree. target/ and .git/ are host state.
tar -C /src --exclude=./target --exclude=./.git -cf - . | tar -xf - -C /work
chown -R kento:kento /work

PATH=/usr/local/cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH
RUSTUP_HOME=/usr/local/rustup
export RUSTUP_HOME

as_kento() {
    su kento -s /bin/sh -c "cd /work && PATH=$PATH RUSTUP_HOME=$RUSTUP_HOME \
        HOME=/home/kento CARGO_HOME=/home/kento/.cargo \
        CARGO_TARGET_DIR=/work/target $1"
}

echo "=== platform ==="
sed -n '1,2p' /etc/os-release
ldd --version 2>&1 | head -1 || true
as_kento "id && cargo --version && rustc --version && git --version"

echo "=== full suite ==="
as_kento "cargo test --quiet"

echo "=== kento lints itself ==="
as_kento "cargo run --quiet --release -- all"
echo "self-lint exit: $?"
