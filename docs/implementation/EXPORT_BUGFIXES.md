# Export Project Bug Fixes

## Issue 1: Story 'height' AttributeError

**Error**: `'Story' object has no attribute 'height'`

**Cause**: The Story model uses `elevation` field, not `height`

**Fix**: Changed all references from `s.height` to `s.elevation`

**Files Modified**:
- `src/services/export_service.py` line 450
- `src/services/export_service.py` line 571

**Changes**:
```python
# Before
"Height": s.height or 0.0
{"name": s.name, "sort_order": s.sort_order, "height": s.height or 0.0}

# After
"Elevation": s.elevation or 0.0
{"name": s.name, "sort_order": s.sort_order, "elevation": s.elevation or 0.0}
```

---

## Issue 2: Element 'description' AttributeError

**Error**: `'Element' object has no attribute 'description'`

**Cause**: The Element model doesn't have a `description` field, it has `unique_name` instead

**Fix**: Changed to use `e.unique_name` instead of `e.description`

**Files Modified**:
- `src/services/export_service.py` line 461
- `src/services/export_service.py` line 575

**Changes**:
```python
# Before
{
    "Name": e.name,
    "Element Type": e.element_type,
    "Description": e.description or "",
}
{"name": e.name, "element_type": e.element_type, "description": e.description or ""}

# After
{
    "Name": e.name,
    "Unique Name": e.unique_name or "",
    "Element Type": e.element_type,
}
{"name": e.name, "unique_name": e.unique_name or "", "element_type": e.element_type}
```

---

## Database Model Reference

For future reference, here are the actual model fields:

### Story Model (lines 68-91 in models.py)
```python
class Story(Base):
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String(100))
    elevation = Column(Float, nullable=True)  # ✅ Use this, not 'height'
    sort_order = Column(Integer, nullable=True)
```

### Element Model (lines 216-241 in models.py)
```python
class Element(Base):
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    element_type = Column(String(50))  # 'Wall', 'Column', 'Beam'
    name = Column(String(100))
    unique_name = Column(String(100), nullable=True)  # ✅ Use this, not 'description'
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=True)
```

---

## Status

✅ Both issues fixed
✅ Documentation updated
✅ Ready for testing

Please try exporting again - it should work now!
