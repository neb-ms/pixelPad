📝 Product Requirements Document (PixelPad)

1. Product Vision & Scope
   Field Description Requirement Level
   Product Name PixelPad Fixed
   Goal To create a fast, distraction-free, cross-platform note-taking application focused on quick file access and a unique high-contrast, pixel-art aesthetic. Fixed
   Target Users Amateur developers and power users seeking a lightweight, aesthetic scratchpad. Fixed
   Target Platforms Windows 10/11 and Linux (Arch-based, e.g., CachyOS). Fixed
   Core Technology Python with PySide6 (Qt) for the cross-platform GUI and CSS-like styling (QSS). Fixed

Export to Sheets 2. Functional Requirements (FR)
2.1 File & Repository Management
ID Feature Specification Acceptance Criteria
FR1.1 Initial Repository Setup On the very first launch only, the app must present a modal dialog to select a system folder to serve as the permanent Notes Repository. This path must be saved to a persistent configuration file (config.ini or similar). App detects no config, prompts for a folder via QFileDialog, and successfully saves the absolute path to the config file.
FR1.2 File Format Support Users must have the option to save notes with either the Plain Text (.txt) or Markdown (.md) extension. When creating or saving a note for the first time, the user must explicitly choose or be prompted for the format (.txt is default if none is chosen).
FR1.3 New Note Creation A prominent UI element (Button/Icon) must clear the editor, ready for new input. A new note is assigned a temporary title (e.g., "Untitled Note") until explicitly saved or auto-saved. User clicks the icon/button; the main editor text is cleared; and the status/title bar updates to reflect the unsaved status.
FR1.4 Open Repository Access A persistent button/icon at the base of the sidebar must launch the system's file explorer to the configured Notes Repository path. Clicking the button must execute the correct OS command: os.startfile(path) (Windows) or subprocess.call(['xdg-open', path]) (Linux/Arch).

Export to Sheets
2.2 User Interaction & Quick Access
ID Feature Specification Acceptance Criteria
FR2.1 Auto-Save on Event The content of the currently open note must be automatically saved (overwriting the existing file) when: (a) The user switches to a different note (FR2.3), or (b) The application window is closed (QCloseEvent). A file's modification time must update on an autosave event, and the content must match the editor's text before the switch/close.
FR2.2 Recent Notes Sidebar A dedicated sidebar must list the 10 most recently modified notes from the repository. The list must show only the file name (without extension) and be ordered by the file modification time (most recent at the top). The sidebar is populated on launch and dynamically updates whenever a note is saved or opened.
FR2.3 Quick Note Switching Clicking a note's title in the sidebar list must trigger the auto-save (FR2.1) of the current note, followed by loading the content of the clicked note into the main editor. Switching must be visually instantaneous (under 500ms).
FR2.4 Note Search/Filter A single-line search input must be located at the top of the sidebar. As the user types, the visible list of 10 recent notes must be dynamically filtered by title substring matching. Typing a search query instantly filters the list; clearing the query instantly restores the full list.

Export to Sheets
2.3 Editor Features
ID Feature Specification Acceptance Criteria
FR3.1 Line Number Toggle The text editor must have a line number gutter. A settings icon or context menu option must toggle the visibility of this line number gutter. The line numbers must correctly align with the text content, update on new lines, and appear/disappear instantly upon toggling.

Export to Sheets 3. Non-Functional Requirements (NFR)
3.1 Performance & Aesthetics
ID Requirement Specification Acceptance Criteria
NFR1.1 Startup Speed Time from application execution to a fully loaded and typable state (NFR01) must be under 2.0 seconds. Verified with system profiling tools on both Windows and Linux test environments.
NFR1.2 Default Theme The application must launch in a forced AMOLED Dark Mode. The primary application background color must be pure black (#000000).
NFR1.3 Color Palette The primary text and accent color must be a high-contrast green, with a secondary accent color for interactive states (e.g., hover/selection). Primary Foreground/Text Color: Light Green (e.g., #00FF00 or similar high-luminosity green). Secondary Accent Color: Cyan or a slightly darker green (e.g., #00FFFF or a variant of #00FF00).
NFR1.4 Pixel Art Styling All UI elements, including buttons, list items, borders, and scrollbars, must be styled using Qt Style Sheets (QSS) to enforce a blocky, non-rounded, high-contrast, minimalistic pixel-art aesthetic. Specifics: border-radius: 0px must be used universally. All borders must be a solid, high-contrast line. A mono-spaced font must be used for the text editor.
NFR1.5 Resource Usage The application must minimize its CPU and RAM footprint to maintain a "lightweight" feel consistent with simple text editors like Notepad. On idle, the application must consume minimal resources.

Export to Sheets
