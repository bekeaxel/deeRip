from PyInstaller.utils.hooks import collect_submodules

# Collect all submodules from textual.widgets to avoid lazy-import issues
hiddenimports = collect_submodules("textual.widgets")
