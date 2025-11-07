# Qt Stylesheet Transform Property Fix

**Date**: 2024-11-07
**Issue**: "Unknown property transform" warning

---

## Problem

Qt stylesheets don't support CSS `transform` property. The following CSS properties are not valid in Qt:
- `transform: scale(0.98)` ❌
- `text-transform: uppercase` ❌

---

## Changes Made

### Removed `transform: scale(0.98)` from Button Pressed States

**File**: `src/gui/styles.py`

**Lines Modified**:
1. Line 332: Primary button pressed
2. Line 354: Secondary button pressed
3. Line 369: Danger button pressed
4. Line 385: Ghost button pressed

**Before**:
```css
QPushButton:pressed {
    background-color: {COLORS['accent']};
    transform: scale(0.98);  /* Not supported! */
}
```

**After**:
```css
QPushButton:pressed {
    background-color: {COLORS['accent']};
    /* Removed transform - Qt doesn't support it */
}
```

**Alternative Pressed States**:
- **Primary**: Same background (already highlighted)
- **Secondary**: Darker background (`{COLORS['hover']}`)
- **Danger**: Darker red (`#c53030`)
- **Ghost**: Slightly darker overlay (`rgba(127, 139, 154, 0.3)`)

---

### Removed `text-transform: uppercase` from Labels

**Line 250**: Summary metric label

**Before**:
```css
#summaryMetricLabel {
    color: {COLORS['muted']};
    font-size: 13px;
    text-transform: uppercase;  /* Not supported! */
    letter-spacing: 1px;        /* Not supported! */
}
```

**After**:
```css
#summaryMetricLabel {
    color: {COLORS['muted']};
    font-size: 13px;
    font: 13px;
}
```

**Note**: For uppercase text in Qt, use `.toUpper()` on the text string in Python code instead.

---

## Qt Stylesheet Limitations

Qt stylesheets support a **subset** of CSS properties. These are **NOT supported**:

❌ `transform` (scale, rotate, translate)
❌ `text-transform` (uppercase, lowercase, capitalize)
❌ `letter-spacing`
❌ `transition` (use QPropertyAnimation in code)
❌ `box-shadow` (use QGraphicsDropShadowEffect in code)
❌ `flex`, `grid` (use Qt layouts)

**Use these alternatives**:
✅ Margin, padding, border
✅ Background colors
✅ Font properties (size, weight, family)
✅ Color (text color)
✅ Border-radius
✅ Min/max width/height

---

## Result

✅ No more "Unknown property transform" warnings
✅ Buttons still have visual feedback on press (darker background)
✅ Labels display correctly without uppercase transform

---

**Status**: Fixed ✓
