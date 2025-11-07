# Conflict Dialog Layout Optimization

**Date**: 2024-11-07
**File**: `src/gui/load_case_conflict_dialog.py`

---

## Changes Made

### ✅ Layout Structure Improvements

**Before**: Splitter with vertical border between panels
**After**: Horizontal layout with 8px gap

```python
# Before
content_splitter = QSplitter(Qt.Orientation.Horizontal)
content_splitter.setHandleWidth(1)

# After
content_layout = QHBoxLayout()
content_layout.setSpacing(8)  # Gap between panels
```

**Benefit**: Cleaner visual separation, matches folder import dialog design

---

### ✅ Background Structure Matching Import Dialog

**Applied**: Same gray-on-dark structure
- Main background: `#0a0c10` (dark)
- GroupBoxes: `#161b22` (gray card)
- Inner areas: `#0a0c10` (dark background)

**Consistency**: Both dialogs now use identical color hierarchy

---

### ✅ Simplified Conflict Widgets

**Before**: Card-style containers with borders and backgrounds
```python
widget.setStyleSheet(f"""
    QWidget {{
        background-color: {COLORS['card']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
    }}
""")
layout.setContentsMargins(10, 10, 10, 10)
```

**After**: Flat design with bottom borders only
```python
widget.setStyleSheet(f"""
    QWidget {{
        background-color: transparent;
        border-bottom: 1px solid {COLORS['border']};
        padding: 4px 0px;
    }}
""")
layout.setContentsMargins(0, 8, 0, 8)
```

**Benefits**:
- Less visual clutter
- More content visible in same space
- Cleaner, more modern appearance
- Matches minimalist design principles

---

### ✅ Result Type Selection States

**Added**: Visual feedback for selected result type
```python
QPushButton[selected="true"] {{
    background-color: {COLORS['background']};
    color: {COLORS['accent']};
}}
```

**Method**: Property-based dynamic styling
```python
def _select_result_type(self, sheet: str) -> None:
    for sheet_name, btn in self.result_type_buttons.items():
        is_selected = sheet_name == sheet
        btn.setProperty("selected", "true" if is_selected else "false")
        btn.style().unpolish(btn)
        btn.style().polish(btn)
```

**Benefit**: Clear visual indication of currently selected result type

---

### ✅ Reduced Visual Weight

**Font Sizes**:
- Load case labels: 13px → 12px
- Result type title: 15px → 13px
- Radio buttons: 13px → 12px
- Skip option: 12px → 11px

**Padding Reductions**:
- GroupBox padding: 12px → 8px
- Load case label spacing: 10px → 8px
- Button padding: 8px 12px → 6px 8px
- Radio button padding: 4px 8px → 3px 4px

**Benefit**: More compact, space-efficient design

---

### ✅ Tighter Spacing

**Container Layout**:
```python
# Before
container_layout.setSpacing(8)
container_layout.setContentsMargins(0, 0, 0, 0)

# After
container_layout.setSpacing(0)  # Borders handle separation
container_layout.setContentsMargins(8, 8, 8, 8)
```

**Result Type List**:
```python
# Before
layout.setSpacing(4)

# After
layout.setSpacing(2)
```

**Benefit**: Denser information display without feeling cramped

---

### ✅ Scroll Area Styling

**Before**: Transparent, borderless
```python
QScrollArea {{
    border: none;
    background-color: transparent;
}}
```

**After**: Dark background with border (matches load case section in import dialog)
```python
QScrollArea {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    background-color: {COLORS['background']};
}}
```

**Benefit**: Clear visual containment, consistent with other list areas

---

## Visual Comparison

### Before:
```
┌─────────────────────────────────────────────┐
│ Resolve Load Case Conflicts                │
│ Found 3 duplicate load case(s)...           │
├─────────────┬───────────────────────────────┤
│ Result Types│Conflicts                      │
│ ┌─────────┐│┌─────────────────────────────┐│
│ │Story    ││││ ╔═══════════════════════╗  ││
│ │Drifts(2)│││  ║ DES_X                ║  ││
│ │         ││││ ║ ○ file1.xlsx         ║  ││
│ │Story    ││││ ║ ● file2.xlsx         ║  ││
│ │Forces(1)││││ ║ ○ Skip               ║  ││
│ └─────────┘│││ ╚═══════════════════════╝  ││
│            │││                             ││
│            ││└─────────────────────────────┘│
└─────────────┴───────────────────────────────┘
```

### After:
```
┌─────────────────────────────────────────────┐
│ Resolve Load Case Conflicts                │
│ Found 3 duplicate load case(s).             │
├─────────────┬───────────────────────────────┤
│┌───────────┐│┌─────────────────────────────┐│
││Result Types│││Story Drifts                 ││
││            ││├─────────────────────────────┤│
││Story       │││DES_X                        ││
││Drifts (2)  │││○ file1.xlsx                 ││
││            │││● file2.xlsx                 ││
││Story       │││○ Skip (don't import)        ││
││Forces (1)  ││├─────────────────────────────┤│
││            │││MCE_X                        ││
│└───────────┘││○ file1.xlsx                 ││
│            │││● file3.xlsx                 ││
│            ││└─────────────────────────────┘│
└─────────────┴───────────────────────────────┘
```

---

## Design Principles Applied

✅ **Flatten hierarchy**: Removed nested card containers
✅ **Consistent spacing**: 8px gap matches import dialog
✅ **Background structure**: Gray panels on dark background
✅ **Minimal borders**: Only where needed for separation
✅ **Compact sizing**: Smaller fonts and tighter padding
✅ **Visual feedback**: Selected state for result types
✅ **Border-based separation**: Instead of cards with spacing

---

## Files Changed

- `src/gui/load_case_conflict_dialog.py` (389 lines)

## Lines Changed

- Main layout: Lines 99-111 (splitter → horizontal layout)
- Result types panel: Lines 140-178 (selection state tracking)
- Conflict widgets: Lines 248-329 (flattened design)
- Styling methods: Lines 331-379 (updated styles)

---

## Testing Checklist

- [ ] Dialog opens with correct layout
- [ ] 8px horizontal gap visible between panels
- [ ] Result type buttons show selection state (cyan background/text)
- [ ] Conflict items have bottom borders (no card backgrounds)
- [ ] Scroll area has dark background with border
- [ ] Radio buttons are properly sized (14px indicators)
- [ ] Skip option is subtle (gray, italic, 11px)
- [ ] Overall appearance matches folder import dialog

---

**Status**: Code changes complete, ready for testing
