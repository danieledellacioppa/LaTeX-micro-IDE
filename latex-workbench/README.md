# latex-workbench

A minimal Python desktop LaTeX workbench for macOS, built with **PySide6**.

## What this project does

`latex-workbench` is an MVP LaTeX IDE for editing and building `.tex` files with `latexmk` + XeLaTeX.

Current capabilities:
- Open a `.tex` file
- Edit in a simple `QPlainTextEdit` panel
- Save changes
- Build with:
  - `latexmk -xelatex -interaction=nonstopmode -file-line-error <selected_file.tex>`
- Show build stdout/stderr in a log panel
- Open generated PDF in the default macOS viewer after successful build
- Run simple shell commands in an integrated non-PTY console
- Run Git commands (`pull`, `status`, `push`) in the current project directory
- List and checkout branches from `git branch --all`

## Requirements

- Python 3
- `latexmk` available in shell `PATH`
- XeLaTeX available in shell `PATH`
- macOS (first MVP target)

## Install dependencies

From the `latex-workbench` directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Notes on build behavior

- Build runs in the directory of the selected `.tex` file.
- Build output is streamed to the log panel.
- If `latexmk` is missing or fails to start, a clear message is shown in the log.

## Notes on shell/terminal behavior

- The integrated shell panel is currently a **simple subprocess console**, not a PTY terminal emulator.
- This means it **does not** support full terminal UX features like:
  - TAB autocomplete
  - arrow-key command history integration from a real shell TTY
  - fullscreen terminal apps
- For true interactive terminal behavior, a future version should move to a **PTY-based terminal implementation**.

## PDF preview behavior (current implementation)

- PDF preview is currently **external**.
- The app uses `QDesktopServices.openUrl(...)` to ask macOS to open the generated PDF with the system default viewer (typically Preview).
- The PDF is **not embedded** inside the PySide6 window right now.

## Future Copilot integration note

- GitHub Copilot suggestions do **not** work inside the current `QPlainTextEdit` editor panel.
- An intermediate architecture for Copilot support is to replace/complement the editor with embedded Neovim plus Copilot plugins.

Planned architecture:

- PySide6 main app
- embedded Neovim editor
- PDF preview
- build/log/git controls

## Intentionally postponed features

- Embedded PDF preview panel
- Neovim integration
- GitHub Copilot integration
- PTY-based terminal emulator
- Advanced project/workspace management
