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

## Key Features (Phase 2)

- Auto-configures a notes repository on first launch and persists it for future runs (FR1.1).
- Sidebar with search-driven recent notes list for rapid switching (FR2.2, FR2.3, FR2.4).
- Automatically opens your most recent note on launch and prompts for a first note when the repository is empty.
- New note workflow with `.txt` and `.md` support, plus automatic auto-save triggers on note switches and window close (FR1.2, FR1.3, FR2.1).
- Open-repository shortcut that launches the configured folder in the system file explorer (FR1.4).

## Manual Verification Checklist

1. Launch the app without an existing configuration and confirm the repository picker dialog appears; choose a folder and restart to ensure it is remembered.
2. Create a couple of notes via `Ctrl+N`, verify they appear in the sidebar list, and confirm switching between them auto-saves content changes.
3. Filter the recent notes list by typing in the search field and ensure the list updates instantly.
4. Close the window with unsaved edits and verify the changes persist when reopening the note.
5. Click **Open Repository** and confirm the system file explorer opens the configured folder.
