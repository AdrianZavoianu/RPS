# Hot-Reload Development Setup for RPS

This guide explains how to run the RPS application with automatic restart on file changes, similar to web development hot-reload.

## Setup (One-time)

1. **Install watchfiles dependency:**
   ```bash
   pipenv install --dev
   ```

2. **Enable auto-save in Cursor/VS Code** (already configured in `.vscode/settings.json`):
   - Files auto-save after 1 second of inactivity
   - Change `files.autoSaveDelay` if you want a different delay

## Usage

### Option 1: Via Cursor/VS Code Task (Recommended)

1. Press `Ctrl+Shift+P` (Windows) or `Cmd+Shift+P` (Mac)
2. Type "Run Task"
3. Select "RPS - Run with Auto-Reload"

**OR** use the keyboard shortcut:
- `Ctrl+Shift+B` (Windows) - runs default build task

The app will:
- Start immediately
- Watch `src/` folder for changes
- Auto-restart on any `.py` file save
- Show output in dedicated terminal panel

### Option 2: Via Command Line

```bash
# Simple wrapper script
pipenv run python dev_watch.py
# Restarts are debounced so rapid saves only open one window.

# Or direct watchfiles command
pipenv run watchfiles --ignore-paths 'data/*,Old_scripts/*,.git/*' 'pipenv run python src/main.py' src/
```

### Option 3: Normal Run (No Hot-Reload)

```bash
# Standard run
pipenv run python src/main.py

# Or via task: "RPS - Run Normal (No Reload)"
```

## How It Works

1. **watchfiles** monitors the `src/` directory for file changes
2. When you save a `.py` file, it detects the change
3. It kills the current RPS process
4. It starts a new RPS process automatically
5. Your window reopens with the latest code

**Ignored paths** (won't trigger reload):
- `data/*` - Database files
- `Old_scripts/*` - Legacy code
- `tests/*` - Test files
- `__pycache__/*` - Python cache
- `.git/*` - Git files

## Development Workflow

1. Start hot-reload task: `Ctrl+Shift+B`
2. Edit any file in `src/gui/`, `src/processing/`, etc.
3. Save with `Ctrl+S` (auto-saves after 1 second anyway)
4. App restarts automatically (~2-3 seconds)
5. Test your changes immediately

### Example: Tweaking UI Styles

```python
# Edit src/gui/styles.py
COLORS = {
    'accent': '#4a7d89',  # Change this color
}
```

**Save** → App restarts → New color applied instantly!

### Example: Adjusting Table Layout

```python
# Edit src/gui/results_table_widget.py
self.table.setColumnWidth(col_idx, 60)  # Change width
```

**Save** → App restarts → New column width visible!

## Tips for Fast Iteration

1. **Keep a test project open**: Have a project with loaded data so you can see changes immediately after restart

2. **Use the status bar**: App shows project info, helps verify it reloaded correctly

3. **Watch the terminal**: See startup time and any errors during reload

4. **Split screen**: Editor on left, running app on right

5. **Multiple monitors**: Code on one, app on another

## Limitations

- **Full restart** - not live UI patching (app window closes/reopens)
- **Lost state** - navigation, selections reset on restart
- **~2-3 second restart time** - includes DB init, window creation
- **Database changes** - migrations still need manual `alembic upgrade head`

## Advanced: Faster Restarts

If restarts feel slow, you can:

1. **Skip DB init for dev** (add flag in `main.py`):
   ```python
   if not os.environ.get("RPS_SKIP_DB_INIT"):
       init_db()
   ```

2. **Use in-memory SQLite** (loses data on restart):
   ```python
   # In database/base.py
   DATABASE_URL = "sqlite:///:memory:"  # Instead of file
   ```

3. **Cache window geometry** (restore position/size):
   ```python
   # Save/restore window position between restarts
   ```

## Troubleshooting

**"Command not found: watchfiles"**
→ Run `pipenv install --dev` first

**App doesn't restart on save**
→ Check terminal output, may have syntax error preventing restart

**Restart is too slow**
→ Consider the optimizations above, or use "Run Normal" for debugging

**Changes not reflected**
→ Check you saved the file, verify it's in `src/` folder

**Database locked error**
→ Make sure only one instance is running (watchfiles should handle this)

## Comparison with Other Methods

| Method | Restart Speed | State Preserved | Reliability |
|--------|--------------|-----------------|-------------|
| Manual restart | Slow (manual) | No | 100% |
| **watchfiles auto-restart** | **Fast (2-3s)** | **No** | **95%** |
| Live UI reload | Very fast (<1s) | Partial | 60% (fragile) |

**Recommended**: Use watchfiles auto-restart for reliable, fast iteration.

---

**Quick Reference Commands:**

```bash
# Start with hot-reload
pipenv run python dev_watch.py

# Or use Cursor/VS Code task (Ctrl+Shift+B)

# Normal run (no reload)
pipenv run python src/main.py
```

Enjoy web-style development for your PyQt6 app! 🔥
