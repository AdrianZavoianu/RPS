# Window Icon Customization Guide

## What This Controls

The window icon appears in **4 places**:

```
┌─[📦 RPS]──────────────────────────┐  ← 1. Title bar (top-left)
│  Results Processing System         │
│                                    │
│  Your content here...              │
│                                    │
└────────────────────────────────────┘

[📦 RPS - Results Processing System]  ← 2. Taskbar

Alt+Tab: [📦 RPS]                      ← 3. Alt+Tab switcher

System Tray: [📦]                      ← 4. System tray (if minimized)
```

## Current State

✅ **Icon system is already implemented and working!**

Right now you're seeing:
- Auto-generated placeholder with "RPS" text
- Dark background matching your design system
- Teal accent color (#4a7d89)

## How to Add Your Own Icon

### Quick Start (3 Steps)

1. **Get an icon file**
   - Download/create a 64x64 or 256x256 PNG
   - Or use a .ICO file for best quality

2. **Save it to the icons folder**
   ```
   C:\SoftDev\RPS\resources\icons\app_icon.png
   ```
   Or:
   ```
   C:\SoftDev\RPS\resources\icons\app_icon.ico
   ```

3. **Restart the app**
   - Your icon will automatically appear!
   - No code changes needed

### Icon File Priority

The app looks for icons in this order:
1. `app_icon.ico` (Windows native - best)
2. `app_icon.png` (cross-platform)
3. Auto-generated placeholder (fallback)

## Icon Design Recommendations

### To Match Your Design System

**Colors:**
- Background: `#161b22` (card background)
- Accent: `#4a7d89` (teal)
- Highlight: `#67e8f9` (cyan)
- Border: `#2c313a`

**Style:**
- Geometric, minimal
- Rounded corners (8px)
- Clean, technical look

**Size:**
- **Recommended**: 256x256 pixels
- **Minimum**: 64x64 pixels
- **ICO format**: Include 16x16, 32x32, 48x48, 64x64, 128x128, 256x256

### Example Ideas

**Option 1: Building Profile**
```
┌──────┐
│ ╱│   │
│╱ │   │  ← Structural analysis theme
│  │   │
└──────┘
```

**Option 2: Letter Badge**
```
┌──────┐
│      │
│ RPS  │  ← Simple, professional
│      │
└──────┘
```

**Option 3: Graph Icon**
```
┌──────┐
│  ╱╲  │
│ ╱  ╲ │  ← Data visualization theme
│╱────╲│
└──────┘
```

## Creating Icons

### Online Tools (Free)
- **Figma**: https://figma.com (design with your exact colors)
- **Canva**: https://canva.com (templates + export as PNG)
- **Favicon.io**: https://favicon.io (quick icon generator)

### AI Generation
Use ChatGPT/DALL-E or Midjourney with this prompt:
```
"Create a minimal, geometric app icon for a structural engineering software
called RPS. Dark background (#161b22), teal accent (#4a7d89),
modern tech aesthetic, 256x256 pixels, flat design"
```

### Convert PNG to ICO
If you have a PNG and want to convert to ICO:

**Online:**
- https://convertio.co/png-ico/
- https://icoconvert.com/

**Using ImageMagick:**
```bash
magick convert app_icon.png -define icon:auto-resize=256,128,64,48,32,16 app_icon.ico
```

## Quick Test

Want to test right now? You can:

1. **Use any PNG you have handy**
   - Even a screenshot or image
   - Save it as `app_icon.png` in `resources/icons/`
   - Restart the app to see it

2. **Download a free icon**
   - Visit https://iconscout.com or https://icons8.com
   - Search for "engineering", "building", or "analytics"
   - Download as PNG (256x256)
   - Save to `resources/icons/app_icon.png`

3. **Keep the placeholder**
   - The auto-generated "RPS" icon already looks professional
   - Matches your design system perfectly
   - No action needed!

## Troubleshooting

**Icon not appearing?**
- ✅ Check file is named exactly `app_icon.png` or `app_icon.ico`
- ✅ Check file is in `C:\SoftDev\RPS\resources\icons\`
- ✅ Restart the application completely
- ✅ Check file isn't corrupted (open it in image viewer)

**Icon looks blurry?**
- Use larger size (256x256 minimum)
- Use .ICO format with multiple sizes
- Ensure icon has sharp edges (not upscaled from small image)

**Want different icons for different windows?**
See `src/gui/icon_utils.py` - you can set per-window icons:
```python
from gui.icon_utils import get_window_icon

class ProjectDetailWindow(QMainWindow):
    def __init__(self, ...):
        super().__init__(parent)
        self.setWindowIcon(get_window_icon("project"))  # Uses project_icon.png
```

## Technical Details

**Implementation:**
- Code: `src/gui/icon_utils.py`
- Main entry: `src/main.py` (line 43: `set_app_icons(app)`)
- Icons folder: `resources/icons/`

**Fallback behavior:**
- If no icon file exists, app generates a placeholder
- Placeholder uses PyQt6 QPainter to draw "RPS" text
- No crashes, no errors - graceful handling

**File formats supported:**
- `.ico` - Windows native (best quality, multi-size)
- `.png` - Cross-platform (works everywhere)
- `.svg` - Scalable vector (via QIcon)
- `.jpg` - Raster (works but not recommended)

---

**Ready to customize?** Just drop your icon file in `resources/icons/` and restart! 🎨
