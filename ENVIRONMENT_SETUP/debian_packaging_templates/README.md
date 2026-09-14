# MX Linux Debian Packaging Templates

These scripts represent the verified, bulletproof maintainer scripts (`postinst`, `prerm`, `postrm`) required to package PyQt5/GUI applications for MX Linux (like the SSH Monitor).

## Why are these here?
During the `mx-ssh-monitor` deployment, we encountered an issue where the package would successfully install and appear in the MX Tools menu, but would **fail to uninstall** (`dpkg -r`) because rigid `set -e` flags in the maintainer scripts caused them to crash and halt the removal process if a desktop database update failed.

## Key Rules for MX Linux GUI Packaging:
1. **Never use `set -e` in `prerm` or `postrm`** when modifying system UI states. If a command fails during removal, we still want the package to be removed from the `dpkg` database!
2. Always suffix update commands with `|| true` so they silently fail rather than blocking the package manager.
3. Always include `pkill -f <app_name> || true` in `prerm` to kill the running singleton daemon *before* the files are deleted from the disk.
4. `.desktop` files must use `Categories=System;MX-Setup;` to appear in the MX Tools section.
