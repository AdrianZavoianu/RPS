# Test Resources (Golden Fixtures)

This directory contains golden data fixtures for integration and regression testing.

## Purpose

Golden fixtures provide known-good data for:
- Import/export regression tests
- Parser validation
- Cache verification
- End-to-end workflows

## Structure

```
tests/resources/
├── README.md           # This file
├── nltha/              # NLTHA analysis fixtures
│   ├── sample_des.xlsx # Sample DES result file
│   └── expected/       # Expected parsed outputs
├── pushover/           # Pushover analysis fixtures
│   ├── sample_push.xlsx
│   └── expected/
└── projects/           # Sample project databases
    └── test_project.db
```

## Creating Fixtures

### Excel Fixtures

Minimal Excel files with representative data:
- Include header row and units row
- Include at least 2 stories, 2 load cases
- Include at least 2 elements per type

### Expected Output Fixtures

JSON files with expected parsed results:
- Use `json.dumps(df.to_dict(), indent=2)` for DataFrames
- Include metadata (row counts, column names)

## Usage in Tests

```python
import pytest
from pathlib import Path

RESOURCES = Path(__file__).parent / "resources"

@pytest.fixture
def sample_nltha_file():
    return RESOURCES / "nltha" / "sample_des.xlsx"

def test_parser_produces_expected_output(sample_nltha_file):
    parser = ExcelParser(sample_nltha_file)
    result = parser.parse_story_drifts()

    # Compare against expected
    expected = load_expected("nltha/expected/story_drifts.json")
    assert result.shape == expected["shape"]
```

## Maintenance

- Update fixtures when data format changes
- Keep fixtures minimal (few rows) for fast tests
- Document any special cases in fixture comments
