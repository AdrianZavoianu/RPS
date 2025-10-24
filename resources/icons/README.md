# RPS Application Icons

This directory contains icons for the RPS application.

## Icon Files

Place your custom icon files here:

- **app_icon.png** - Main application icon (shown in taskbar, title bar, Alt+Tab)
- **project_icon.png** - Project detail windows
- **import_icon.png** - Import dialogs
- **settings_icon.png** - Settings windows

## Icon Specifications

### Recommended Sizes
- **64x64 pixels** - Standard size for Windows applications
- **256x256 pixels** - High resolution for Windows 10/11
- **32x32, 48x48, 64x64, 128x128, 256x256** - Multi-size ICO format

### Design Guidelines

To match the RPS modern minimalist design system:

1. **Style**: Geometric, clean, minimal
2. **Colors**: Use design system colors
   - Background: `#161b22` (card)
   - Border: `#2c313a`
   - Accent: `#4a7d89` (teal)
   - Text: `#67e8f9` (cyan)
3. **Format**: PNG with transparency or SVG
4. **Shape**: Rounded rectangle or circle, 8px border radius

### Example Design Ideas

**Option 1: Initials Badge**
```
┌──────────┐
│          │
│   RPS    │  ← Teal text on dark background
│          │
└──────────┘
```

**Option 2: Graph/Chart Symbol**
```
┌──────────┐
│  ╱│      │
│ ╱ │      │  ← Building profile outline
│╱  │      │
└──────────┘
```

**Option 3: Structural Element**
```
┌──────────┐
│  ┬───┬   │
│  │   │   │  ← Column symbol
│  ┴───┴   │
└──────────┘
```

## Creating Icons

### Using Online Tools
- **Figma**: figma.com (free, design system colors)
- **Canva**: canva.com (templates available)
- **IconScout**: iconscout.com/icon-editor

### Using Code (Python/PIL)
See `src/gui/icon_utils.py` - the `create_placeholder_icon()` function generates a basic icon programmatically.

### Converting to ICO (Windows)
If you have a PNG, convert to ICO for better Windows integration:
```bash
# Online: convertio.co/png-ico/
# Or using ImageMagick:
magick convert app_icon.png -define icon:auto-resize=256,128,64,48,32,16 app_icon.ico
```

## Current Status

Currently using **auto-generated placeholder** icon with "RPS" text.

To use a custom icon:
1. Create/download your icon file
2. Save as `app_icon.png` in this directory
3. Restart the application
4. Icon will automatically load

## Fallback Behavior

If no icon file is found, the application will:
1. Generate a placeholder icon with "RPS" text
2. Use design system colors (teal accent on dark background)
3. Display properly in Windows taskbar and title bar

No crashes or errors - the app handles missing icons gracefully.
