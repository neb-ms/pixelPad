# pixelPad

PixelPad is a cross-platform scratchpad built with Python and PySide6. Phase 2 delivers the functional MVP with a connected UI and the file-system logic established in Phase 1.

## Getting Started

1. Create a virtual environment and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Launch the application:
   ```bash
   python main.py
   ```

The first launch prompts for a notes repository. Choose an existing folder (or create a new one) that will hold all PixelPad notes.

## Windows Packaging

1. Ensure the runtime dependencies are installed (PySide6 is required at build time):
   ```powershell
   python -m pip install -r requirements.txt
   ```
2. Build the standalone bundle with PyInstaller:
   ```powershell
   python -m pip install pyinstaller
   build\windows\package_pixelpad.bat
   ```
   This creates `dist\PixelPad`, which contains `PixelPad.exe` and all runtime dependencies.
3. (Optional) Wrap the bundle in an installer using Inno Setup (download from [jrsoftware.org](https://jrsoftware.org/isinfo.php) and ensure `iscc.exe` is on `PATH`):
   ```powershell
   build\windows\build_installer.bat
   ```
   The script compiles `build\windows\pixelpad-installer.iss` and writes `PixelPad-Setup.exe` to `build\windows\installer`. Distribute that executable to provide a standard Windows setup experience; the uninstaller is registered automatically. Signed installers reduce SmartScreen warnings when sharing outside your organization.
4. To run both stages in one shot (or to regenerate all artifacts before a release), use:
   ```powershell
   build\windows\build_release.bat
   ```
   This orchestrates the PyInstaller build and Inno Setup compilation, leaving the portable bundle, single-file executable, and installer ready for distribution.

## Key Features (Phase 2)

- Auto-configures a notes repository on first launch and persists it for future runs (FR1.1).
- Sidebar with search-driven recent notes list for rapid switching (FR2.2, FR2.3, FR2.4).
- Automatically opens your most recent note on launch and prompts for a first note when the repository is empty.
- Toggleable editor line numbers to match FR3.1 requirements.
- New note workflow with `.txt` and `.md` support, plus automatic auto-save triggers on note switches and window close (FR1.2, FR1.3, FR2.1).
- Open-repository shortcut that launches the configured folder in the system file explorer (FR1.4).

## Manual Verification Checklist

1. Launch the app without an existing configuration and confirm the repository picker dialog appears; choose a folder and restart to ensure it is remembered.
2. Create a couple of notes via `Ctrl+N`, verify they appear in the sidebar list, and confirm switching between them auto-saves content changes.
3. Filter the recent notes list by typing in the search field and ensure the list updates instantly.
4. Close the window with unsaved edits and verify the changes persist when reopening the note.
5. Click **Open Repository** and confirm the system file explorer opens the configured folder.
6. Select a note and use the toolbar delete action (or Ctrl+Shift+D) to remove it; verify the file is gone and another note (or the new-note prompt) appears.
7. Toggle line numbers off and back on using the toolbar button (or shortcut, if configured) and confirm the gutter disappears/reappears immediately.
