/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * hummer (OnePlus Ace 5 Pro / LineageOS 24, SM8750) build profile.
 *
 * Upstream only activates its recorded GKI releases.  This fork is built
 * against one exact vendor kernel, so the complete uname -r string is pinned
 * at compile time and the loader passes gki=1 after the userspace ABI check.
 *
 * The release is injected by the Makefile as -DDS_HUMMER_RELEASE=... via the
 * HUMMER_RELEASE variable, so an OTA build only changes the CI input.
 */
#ifndef DS_HUMMER_H
#define DS_HUMMER_H

#define DS_HUMMER 1

#endif
