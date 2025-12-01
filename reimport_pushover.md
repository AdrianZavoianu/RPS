# Re-import Pushover Global Results with Debug Logging

## Steps

1. **Delete existing pushover result set** in project t2 (it has corrupted cache)

2. **Re-import** using the "Typical Pushover Results\160Will_Global_Resp.xlsx" file

3. **Select ALL load cases** for both X and Y directions during import

4. **Check the logs** - the console will show:
   - How many load cases are in the cache when building
   - What load case names are included
   - How many database records are found
   - What directions/stories are in those records
   - How many cache entries are created

This will help us identify where the cache building is failing.

## Expected Output

The logs should show something like:
```
Building cache for Drifts: 16 load cases
Load case names: ['Push_Mod_X+Ecc+', 'Push_Mod_X+Ecc-', ..., 'Push_Uni_Y-Ecc-']
Query returned 192 records for Drifts
Directions in records: {'X', 'Y'}
Stories in records: {'L01', 'L02', 'L03', 'L04', 'L05', 'L06'}
Creating 6 cache entries for Drifts
  L01: 32 load cases (16 X + 16 Y)
  L02: 32 load cases
  ...
```

If the numbers are different, we'll know where the problem is.
