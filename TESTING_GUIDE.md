# RPS Testing Guide

Quick guide for testing the RPS application on a clean computer without development environment.

---

## For Testers (Non-Developers)

### What You'll Need
- A Windows 10/11 computer (64-bit)
- The distribution ZIP file: `RPS_v1.7.0_Windows_x64.zip`
- Sample Excel files from ETABS/SAP2000 (or use `Typical Input/` samples)

### Installation Steps

1. **Download the ZIP file**
   - Get `RPS_v1.7.0_Windows_x64.zip` from the distribution location
   - Size: ~70MB compressed, ~160MB extracted

2. **Extract the files**
   - Right-click the ZIP file
   - Choose "Extract All..."
   - Choose a destination (e.g., `C:\Programs\RPS\`)
   - Click "Extract"

3. **First launch**
   - Navigate to the extracted folder
   - Double-click `RPS.exe`
   - **If Windows shows a warning**:
     - Click "More info"
     - Click "Run anyway"
     - (This is normal for unsigned applications)

4. **Verify installation**
   - The RPS main window should appear
   - You should see the project cards view (empty on first launch)

---

## Testing Checklist

### ✅ Basic Functionality

**Project Management:**
- [ ] Click "New Project" button
- [ ] Enter project details (name, location, description)
- [ ] Click "Create" - project card should appear
- [ ] Click on project card to open project detail view

**File Import:**
- [ ] Click "Import Folder" button
- [ ] Select a folder containing ETABS Excel exports
- [ ] Progress dialog should show import progress
- [ ] Results should appear in the tree browser (left panel)

**Data Visualization:**
- [ ] Click on "Drifts" → "X" in the tree browser
- [ ] Table should display drift values (left panel)
- [ ] Plot should show building profile (right panel)
- [ ] Hover over table rows - plot should highlight corresponding line
- [ ] Click table rows - selection should persist

**Navigation:**
- [ ] Expand/collapse tree sections
- [ ] Switch between different result types
- [ ] Click "Back to Projects" - return to main window
- [ ] Reopen project - data should persist

### ✅ Error Handling

**Invalid Operations:**
- [ ] Try importing a folder with no Excel files - should show error
- [ ] Try creating project with empty name - should prevent creation
- [ ] Try importing invalid Excel file - should show error dialog

**Edge Cases:**
- [ ] Import same folder twice - should handle duplicates
- [ ] Create multiple projects - should manage independently
- [ ] Close and reopen app - projects should persist

### ✅ Performance

**Responsiveness:**
- [ ] Application launches within 5 seconds
- [ ] Importing 10+ files completes without freezing
- [ ] Plotting 100+ data points is smooth
- [ ] Switching between views is instant

**Memory:**
- [ ] Open Task Manager during use
- [ ] Verify memory usage stays under 500MB
- [ ] No memory leaks after extended use

---

## Test Scenarios

### Scenario 1: New User Workflow

**Goal**: Test the complete first-time user experience

1. Launch RPS.exe (first time)
2. Create a new project: "TestBuilding"
3. Import sample Excel files from `Typical Input/`
4. Browse through available results:
   - Story Drifts (X and Y directions)
   - Max/Min Drifts
   - Story Accelerations
   - Story Forces
5. Interact with visualizations:
   - Click table rows
   - Hover over legend items
   - Resize panels
6. Close the application
7. Relaunch and verify project persists

**Expected**: Smooth workflow with no errors or crashes

---

### Scenario 2: Batch Import

**Goal**: Test large-scale data import

1. Create a new project: "BatchTest"
2. Prepare a folder with 20+ Excel files
3. Use "Import Folder" feature
4. Monitor progress dialog
5. Verify all files imported successfully
6. Check that all result types are available
7. Verify data accuracy against source Excel files

**Expected**: All files import correctly, no data loss

---

### Scenario 3: Error Recovery

**Goal**: Test application robustness

1. Create project with empty name → Should prevent
2. Import folder with no Excel files → Should show error
3. Import corrupted Excel file → Should skip with warning
4. Try to open non-existent project → Should handle gracefully
5. Delete database file while app is closed → Should recreate

**Expected**: Graceful error messages, no crashes

---

### Scenario 4: Visual Quality

**Goal**: Verify UI matches design standards

1. Launch application
2. Check for visual issues:
   - [ ] Dark theme applied consistently
   - [ ] Fonts are readable (not too small/large)
   - [ ] Colors are professional (no harsh contrasts)
   - [ ] Spacing is consistent
   - [ ] Icons are clear
   - [ ] Tables are well-formatted
   - [ ] Plots are high-quality

**Expected**: Professional, polished appearance

---

## Common Issues & Solutions

### Issue: "Windows protected your PC" warning
**Cause**: Executable is not digitally signed
**Solution**: Click "More info" → "Run anyway"
**Note**: This is expected for internal apps

### Issue: Application won't start
**Possible causes**:
1. Missing `_internal/` folder → Extract entire ZIP
2. Antivirus blocking → Add exclusion
3. Missing Windows updates → Update Windows
4. 32-bit Windows → Requires 64-bit

**Solution**: Verify complete extraction and Windows compatibility

### Issue: "Can't create project" error
**Cause**: No write permissions to user folder
**Solution**:
1. Run as administrator (right-click → Run as admin)
2. Check antivirus isn't blocking file writes

### Issue: Import fails silently
**Cause**: Invalid Excel file format or structure
**Solution**:
1. Verify Excel file is from ETABS/SAP2000
2. Check sheet names match expected format
3. Try importing sample files from `Typical Input/`

### Issue: Plots don't display
**Possible causes**:
1. Graphics driver issue
2. Missing PyQt6 libraries
3. Data format mismatch

**Solution**: Verify `_internal/` folder contains PyQt6 DLLs

---

## Reporting Issues

When reporting bugs, include:

1. **Environment**:
   - Windows version (10/11)
   - System specs (RAM, CPU)
   - Antivirus software

2. **Steps to reproduce**:
   - What you did before the error
   - Exact actions to trigger the bug

3. **Expected vs actual**:
   - What should have happened
   - What actually happened

4. **Evidence**:
   - Screenshots
   - Error messages (copy full text)
   - Sample files (if relevant)

5. **Logs**:
   - Check `%APPDATA%\RPS\logs\` for error logs
   - Include latest log file

---

## Performance Benchmarks

Expected performance metrics:

| Operation | Expected Time |
|-----------|---------------|
| Application startup | < 5 seconds |
| Project creation | < 1 second |
| Import 1 Excel file | < 2 seconds |
| Import 10 Excel files | < 10 seconds |
| Load visualization | < 1 second |
| Switch result types | Instant |
| Plot 1000 data points | < 0.5 seconds |

If performance is significantly worse, report with system specs.

---

## Success Criteria

The build is ready for deployment if:

✅ All basic functionality tests pass
✅ No crashes during normal use
✅ Error handling is graceful
✅ Performance meets benchmarks
✅ Visual quality is professional
✅ Data accuracy is verified
✅ Projects persist between sessions

---

## Next Steps After Testing

1. **Document findings**:
   - List any bugs discovered
   - Note performance issues
   - Suggest improvements

2. **Verify fixes**:
   - Retest after bug fixes
   - Confirm issues are resolved

3. **Sign off**:
   - Approve for deployment
   - Or request another iteration

4. **Deployment**:
   - Upload to distribution platform
   - Notify end users
   - Provide training if needed

---

**Version**: 1.7.0
**Last Updated**: November 2025
**Test Status**: Ready for validation
