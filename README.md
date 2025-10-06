# pixelPad

pixelPad is a lightweight scratchpad for quick notes, snippets, and reminders. It keeps your notes as plain text on disk so you can sync or edit them with whatever tooling you prefer, while giving you a polished desktop experience built with PySide6.

## Highlights

- Plain-text note storage you can browse directly from your file manager
- Recent notes sidebar with type-to-filter search
- Automatic saving when you switch notes or close the window
- Keyboard-friendly workflow with shortcuts for creating, deleting, and opening notes
- Works anywhere Python 3.10+ and PySide6 are available

## Install on Arch Linux

pixelPad is published on the Arch User Repository (AUR).

- With an AUR helper (recommended):

  ```bash
  yay -S pixelpad
  ```

  Replace `yay` with your preferred helper such as `paru`.

- Manual build with the AUR tools:
  ```bash
  git clone https://aur.archlinux.org/pixelpad.git
  cd pixelpad
  makepkg -Csi
  ```
  The `-C` flag clears any previous build artifacts so the generated source tree matches the package you are installing.

## Windows Installer

If you are on Windows, use the installer included with each release:

1. Download the latest `PixelPad-Setup.exe` from the project releases (or build it locally with `build\windows\build_release.bat`).
2. Run the installer to deploy pixelPad to `%ProgramFiles%\pixelPad` and create a Start Menu entry.
3. Launch pixelPad from the Start Menu or by running `pixelPad.exe` from the installation directory.

If you build locally, the PyInstaller bundle lives in `dist\PixelPad`, and the Inno Setup installer is written to `build\windows\installer\PixelPad-Setup.exe`.

## Run from Source

Prefer to run pixelPad directly from the repository? Install dependencies and start the app with Python:

```bash
pip install -r requirements.txt
python main.py
```

On first launch, pixelPad asks you to select (or create) the folder where your notes will live.

## Thanks!

Feedback, bug reports, and contributions keep this project improving. If you have ideas or requests, please open an issue or pull request. Thank you for helping shape pixelPad.
