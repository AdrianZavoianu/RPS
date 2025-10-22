# 🔥 Hot-Reload Quick Start

Get web-style auto-reload for RPS in 30 seconds!

## ⚡ Quick Setup

1. **Install dependencies** (one-time):
   ```bash
   pipenv install --dev
   ```

2. **Start with hot-reload**:

   **Method A: Cursor/VS Code Task (Easiest)**
   - Press `Ctrl+Shift+B`
   - Select "RPS - Run with Auto-Reload"
   - Done! ✅

   **Method B: Command Line**
   ```bash
   pipenv run python dev_watch.py
   ```

3. **Make changes and save** - app auto-restarts!

## 📝 Example Workflow

Let's test it by changing the table column width:

1. Start hot-reload: `Ctrl+Shift+B`

2. Open `src/gui/results_table_widget.py`

3. Find line ~175:
   ```python
   self.table.setColumnWidth(col_idx, 55)
   ```

4. Change `55` to `60`, save with `Ctrl+S`

5. **Watch the app restart automatically!** (~2-3 seconds)

6. Your table now has 60px columns ✨

## 🎯 Benefits

- **No manual restart** - edit → save → see changes
- **Fast iteration** - ~2-3 second reload cycle
- **Auto-save enabled** - files save 1 second after typing
- **Reliable** - full app restart, no weird state issues

## 📖 Full Documentation

See `DEV_HOTRELOAD.md` for detailed info, tips, and troubleshooting.

---

**TL;DR**: Press `Ctrl+Shift+B`, edit code, save, repeat! 🚀
