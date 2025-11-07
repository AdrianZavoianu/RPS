"""Test how result_types is initialized in EnhancedFolderImporter."""

# Simulate EnhancedFolderImporter.__init__ line 64
result_types_param = None
result_types_set = {rt.strip().lower() for rt in result_types_param} if result_types_param else None

print(f"Input: result_types_param = {result_types_param}")
print(f"Output: result_types_set = {result_types_set}")
print(f"Is falsy: {not result_types_set}")
print()

# Now test with empty list
result_types_param = []
result_types_set = {rt.strip().lower() for rt in result_types_param} if result_types_param else None

print(f"Input: result_types_param = {result_types_param}")
print(f"Output: result_types_set = {result_types_set}")
print(f"Is falsy: {not result_types_set}")
print()

# Now test with list of items
result_types_param = ["Story Drifts", "Floors Displacements"]
result_types_set = {rt.strip().lower() for rt in result_types_param} if result_types_param else None

print(f"Input: result_types_param = {result_types_param}")
print(f"Output: result_types_set = {result_types_set}")
print(f"Is falsy: {not result_types_set}")
