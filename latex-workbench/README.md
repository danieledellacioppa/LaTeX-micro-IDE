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

## Intentionally postponed features

- Embedded PDF preview panel
- Neovim integration
- GitHub Copilot integration
- Custom terminal inside the app
- Advanced project/workspace management
