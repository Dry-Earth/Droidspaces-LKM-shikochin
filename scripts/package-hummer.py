#!/usr/bin/env python3
"""Package one hummer payload with the upstream Droidspaces-LKM loader.

This is the upstream packaging contract reduced to a single device target:
the ZIP keeps upstream's KernelSU template (kernelsu/), the pre-load ABI
checker (bin/abi-check) and the KMI manifest, but contains exactly one
payload for the exact hummer build recorded in ``target-release.txt``.
"""
import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'kernelsu'
MODULE_FILES = ('module.prop', 'common.sh', 'customize.sh', 'post-fs-data.sh',
                'service.sh', 'skip_mount')
KMI = 'hummer-6.6'
PAYLOAD_NAME = 'droidspaces_ns-hummer-6.6.ko'
ABI_NAME = 'hummer-6.6.abi'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def arm64(data: bytes, executable: bool = False) -> None:
    if len(data) < 64 or data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', data, 18)[0] != 183:
        raise SystemExit('expected ELF64 little-endian AArch64')
    kind = struct.unpack_from('<H', data, 16)[0]
    if kind not in ((2, 3) if executable else (1,)):
        raise SystemExit('unexpected ELF type')
    if executable:
        offset = struct.unpack_from('<Q', data, 32)[0]
        size, count = struct.unpack_from('<HH', data, 54)
        if size != 56 or offset + size * count > len(data):
            raise SystemExit('invalid program headers')
        for i in range(count):
            if struct.unpack_from('<I', data, offset + i * size)[0] == 3:
                raise SystemExit('abi-check must be static (found PT_INTERP)')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--payload', type=Path, required=True)
    ap.add_argument('--abi', type=Path, required=True)
    ap.add_argument('--abi-check', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--release', required=True)
    ap.add_argument('--kernel-sha', default='')
    ap.add_argument('--config-sha', default='')
    ap.add_argument('--version', default='')
    args = ap.parse_args()

    payload = args.payload.read_bytes()
    arm64(payload)
    if f'vermagic={args.release} '.encode() not in payload:
        raise SystemExit(f'payload vermagic does not target {args.release}')
    if b'parmtype=gki:bool' not in payload:
        raise SystemExit('payload lacks the upstream gki loading interface')
    if args.release.encode() not in payload:
        raise SystemExit('payload does not embed the target release string')

    abi = args.abi.read_bytes()
    if not abi.startswith(b'DSABI1\n'):
        raise SystemExit('ABI constraints have an unexpected format')
    helper = args.abi_check.read_bytes()
    arm64(helper, executable=True)

    module_prop = (TEMPLATE / 'module.prop').read_text()
    version = args.version or re.search(r'^version=(.*)$', module_prop, re.M).group(1).strip()
    module_prop = re.sub(r'^version=.*$', f'version={version}-hummer', module_prop, count=1, flags=re.M)
    module_prop = re.sub(
        r'^description=.*$',
        f'description=[待加载] hummer {args.release}：PID / IPC namespace；'
        '开机加载前校验 ABI。',
        module_prop, count=1, flags=re.M)

    files = {
        'module.prop': module_prop.encode(),
        'bin/abi-check': helper,
        f'kernel/{PAYLOAD_NAME}': payload,
        f'kernel/{ABI_NAME}': abi,
        'kernel/target-release.txt': (args.release + '\n').encode(),
        'kernel/manifest.tsv': f'{KMI}|{PAYLOAD_NAME}|{ABI_NAME}|\n'.encode(),
        'LICENSE': (ROOT / 'LICENSE').read_bytes(),
        'README-HUMMER.md': (ROOT / 'README-HUMMER.md').read_bytes(),
    }
    for name in MODULE_FILES[1:]:
        files[name] = (TEMPLATE / name).read_bytes()

    checksums = ''.join(
        f'{sha(data)}  {name.removeprefix("kernel/")}\n'
        for name, data in sorted(files.items()) if name.startswith('kernel/'))
    checksums += f'{sha(helper)}  ../bin/abi-check\n'
    files['kernel/SHA256SUMS'] = checksums.encode()

    build = {
        'target': KMI,
        'release': args.release,
        'kernel_sha': args.kernel_sha,
        'config_sha256': args.config_sha,
        'payload_sha256': sha(payload),
        'abi_sha256': sha(abi),
        'abi_check_sha256': sha(helper),
        'sources': {
            'makefile': sha((ROOT / 'Makefile').read_bytes()),
            'gki_target': sha((ROOT / 'src/gki-target.h').read_bytes()),
        },
    }
    files['build-info.json'] = (json.dumps(build, indent=2) + '\n').encode()
    files['build-info.txt'] = (
        f'target:      {KMI}\n'
        f'release:     {args.release}\n'
        f'kernel:      {args.kernel_sha}\n'
        f'config:      {args.config_sha}\n'
        f'payload:     {PAYLOAD_NAME}\n'
        f'upstream:    https://github.com/Shikochin/Droidspaces-LKM\n'
        f'loader:      kernelsu/ (upstream), hummer target added\n'
    ).encode()

    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / f'Droidspaces-LKM-KernelSU-{version}-hummer.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 11, 15, 0, 0, 0))
            entry.create_system = 3
            executable = name.endswith('.sh') or name == 'bin/abi-check'
            entry.external_attr = (0o100755 if executable else 0o100644) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(entry, data)

    (args.output / 'SHA256SUMS').write_text(f'{sha(archive.read_bytes())}  {archive.name}\n')
    (args.output / PAYLOAD_NAME).write_bytes(payload)
    print(archive)
    print('sha256:', sha(archive.read_bytes()))


if __name__ == '__main__':
    main()
