# hummer 分支说明（OnePlus Ace 5 Pro / LineageOS 24 / SM8750）

这是 [Shikochin/Droidspaces-LKM](https://github.com/Shikochin/Droidspaces-LKM) 的
**单机型构建分支**。上游的六个 GKI 载荷只接受 `*-androidNN-*` 形式的内核版本，
hummer 的内核是：

```text
6.6.144-4k-g01ee97578159
```

其中没有 `androidNN` 段，所以上游通用 ZIP 在这台机器上会直接显示
`[不支持] 无法从内核版本识别 GKI KMI`，**根本不会加载**——这就是“刷入后只差
PID / IPC namespace 几项”的原因。

本分支做三件事：

1. 把 hummer 的完整 `uname -r` 编进 `src/port66` 载荷（`DS_HUMMER_RELEASE`），
   并且仍然保留上游的 `gki=1` 加载开关；
2. 用**该机型自己的 boot.img** 编出精确 KDIR，再从 vmlinux / .ko 的 BTF 生成
   `hummer-6.6.abi` 约束；
3. 保留上游的 KernelSU 模板、`bin/abi-check` 和 KMI 清单，只把载荷换成
   hummer 版本；开机加载前仍然做一次 ABI 校验，OTA 换了内核就拒绝加载。

## 构建

GitHub → Actions → **`[hummer] Build from OTA`** → Run workflow：

| 输入 | 说明 |
|---|---|
| `boot_img_url` | OTA 的 `boot.img` |
| `manifest_url` | 同一 OTA 的 `build-manifest.xml` |
| `publish_release` | 成功后自动发 Release |

流程与上游一致：解析 manifest 里 kernel / modules / clang 的精确 revision →
从 `boot.img` 提取真实 config / release / 编译器 → 原厂 clang 编 KDIR →
用上游 `Makefile` 编 `src/port66` → 生成 BTF 约束 → `kernelsu/` 模板打包。

产物：`Droidspaces-LKM-KernelSU-v0.2.0-hummer.zip`、独立 `.ko`、`SHA256SUMS`。

## 安装

1. 确认没有同时启用其它 namespace 模块（本仓库的 `droidspaces_lkm` 与
   phDroid / `droidspaces_hummer` 互斥），有的话先停用并重启。
2. KernelSU 管理器安装 ZIP → 重启。
3. 开机后简介应显示 `[已加载]`；日志在
   `/data/adb/modules/droidspaces_lkm/load.log`。
4. 验证：

```sh
su -c 'droidspaces check'
su -c 'ls -l /proc/self/ns'
```

## 限制

- **没有在真机上验证过**：只完成精确 KDIR 构建、BTF 约束生成和上游加载器的
  静态检查。第一次刷入请保留 stock boot / 可回滚手段。
- 只支持 `target-release.txt` 里记录的完整内核版本；OTA 后需要重跑工作流。
- 不包含 devtmpfs、netfilter、USER_NS 沙箱（上游这些扩展来自 PLZ110 专用
  6.12 分支，不是通用 `src/port66` 的一部分）。
- `CONFIG_CFS_BANDWIDTH`（CPU limit）属于内核编译配置，模块无法补充。

## 来源

- 上游：`Shikochin/Droidspaces-LKM`（GPL-2.0），本分支只改了
  `src/gki-target.h`、新增 `src/ds-hummer.h`、`Makefile` 的 `HUMMER` 开关、
  `kernelsu/common.sh` 的 hummer KMI 识别，以及 `ci/`、`scripts/package-hummer.py`、
  `.github/workflows/build-hummer.yml`。
- 载荷源码、加载器、ABI 检查器均来自上游，未改写其验证逻辑。
