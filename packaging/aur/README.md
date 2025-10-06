# pixelpad AUR packaging

This directory contains the metadata needed to publish PixelPad to the Arch User Repository. Adapt it to your upstream hosting (GitHub/GitLab) before pushing to the AUR.

## Checklist before packaging

1. Tag a release in the upstream repository (e.g. `v0.1.0`).
2. Update `pkgver`, `pkgrel`, and the `source` URL in `PKGBUILD` to match the tag.
3. Replace `REPLACE_ME` in `PKGBUILD` and `.SRCINFO` with your actual Git forge namespace.
4. Run `updpkgsums` to compute the real SHA256 sum.
5. Regenerate `.SRCINFO` with `makepkg --printsrcinfo > .SRCINFO`.
6. Test build locally on Arch:
   ```bash
   makepkg -si
   ```
7. Optionally run `namcap PKGBUILD` and `namcap *.pkg.tar.zst` for linting.

## Submitting to the AUR

Follow the [Arch wiki guide](https://wiki.archlinux.org/title/Arch_User_Repository#Sharing_and_maintaining_packages):

1. Create a clean git repository containing, at minimum, `PKGBUILD` and `.SRCINFO`.
2. Add any supplemental files (such as this README) as desired.
3. Commit and push to `ssh://aur@aur.archlinux.org/pixelpad.git` (or `pixelpad-git.git` for a VCS package).
4. Use `git push` to update the package; the AUR web interface will reflect the new version automatically.

## Why ship the sources?

The package installs the Python sources under `/usr/lib/pixelpad/` and installs a tiny wrapper script in `/usr/bin/pixelpad` that launches the application with the system Python. Runtime dependencies (`python` and `python-pyside6`) are declared so pacman pulls in the Qt/6 stack from official repositories.

If you later provide a Python wheel or different build process, adjust the `package()` function accordingly.

