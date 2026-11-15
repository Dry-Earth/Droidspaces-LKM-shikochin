#!/bin/bash
# Build the upstream src/port66 payload against one exact hummer KDIR and
# extract everything the upstream ABI preflight needs.
#
# Runs inside the pinned DDK image (llvm-objcopy / llvm-nm / pahole present).
set -euo pipefail

ROOT=${ROOT:-/work}
KDIR=${KDIR:-/work/kernel/out}
OUT=${OUT:-/work/out/hummer}
HUMMER_RELEASE=${HUMMER_RELEASE:?HUMMER_RELEASE is required}
JOBS=${JOBS:-$(nproc)}

test -s "$KDIR/Module.symvers"
test -s "$KDIR/vmlinux"
test -s "$KDIR/include/config/kernel.release"
test "$(cat "$KDIR/include/config/kernel.release")" = "$HUMMER_RELEASE"

mkdir -p "$OUT"

if [ -x /work/clang-stock/bin/clang ]; then
	export PATH="/work/clang-stock/bin:$PATH"
fi
export ARCH=arm64
export LLVM=1
export LLVM_IAS=1
export CROSS_COMPILE=aarch64-linux-gnu-
# The payload deliberately calls internal helpers that vendor kernels do not
# export.  KernelSU's ksud relocates them at load time; keep modpost from
# turning those unresolved symbols into a build failure.
export KBUILD_MODPOST_WARN=1

echo "==> make src/port66 for $HUMMER_RELEASE"
make -C "$ROOT" KDIR="$KDIR" OUT="$OUT" HUMMER=1 HUMMER_RELEASE="$HUMMER_RELEASE" \
	TARGET=namespace PORT_DIR=src/port66 GKI_ANDROID=android15 GKI_VERSION=6.6 \
	-j"$JOBS"

test -s "$OUT/droidspaces_ns.ko"
strings "$OUT/droidspaces_ns.ko" > "$OUT/payload.strings"
grep -q "vermagic=$HUMMER_RELEASE " "$OUT/payload.strings"
grep -q "hummer" "$OUT/payload.strings" || true

echo "==> extract kernel BTF / notes / symbols"
cp "$KDIR/.config" "$OUT/kernel.config"
llvm-objcopy --dump-section .BTF="$OUT/kernel.btf" "$KDIR/vmlinux" /tmp/vmlinux-btf-copy
llvm-objcopy --dump-section .notes="$OUT/kernel.notes" "$KDIR/vmlinux" /tmp/vmlinux-notes-copy || true
llvm-nm "$KDIR/vmlinux" > "$OUT/symbols.txt"

echo "==> extract module BTF / imports"
if ! llvm-objcopy --dump-section .BTF="$OUT/module.btf" "$OUT/droidspaces_ns.ko" /tmp/ko-btf-copy 2>/dev/null; then
	pahole -F dwarf --btf_gen_optimized --btf_encode_detached="$OUT/module.btf" "$OUT/droidspaces_ns.ko"
fi
test -s "$OUT/module.btf"
llvm-nm -u "$OUT/droidspaces_ns.ko" > "$OUT/imports.txt"

echo "==> payload"
ls -lh "$OUT/droidspaces_ns.ko" "$OUT/kernel.btf" "$OUT/module.btf"
