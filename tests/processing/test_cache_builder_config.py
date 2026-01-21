"""Tests for cache builder configuration."""

import pytest

from processing.cache_builder_config import (
    CacheType,
    GroupingStrategy,
    CacheConfig,
    GLOBAL_CACHE_CONFIGS,
    ELEMENT_CACHE_CONFIGS,
    JOINT_CACHE_CONFIGS,
    ALL_CACHE_CONFIGS,
    get_cache_config,
    get_configs_by_cache_type,
    get_configs_by_element_type,
)


class TestCacheType:
    """Tests for CacheType enum."""

    def test_global_cache_type(self):
        """Test GLOBAL cache type."""
        assert CacheType.GLOBAL.value == "global"

    def test_element_cache_type(self):
        """Test ELEMENT cache type."""
        assert CacheType.ELEMENT.value == "element"

    def test_joint_cache_type(self):
        """Test JOINT cache type."""
        assert CacheType.JOINT.value == "joint"


class TestGroupingStrategy:
    """Tests for GroupingStrategy enum."""

    def test_by_story(self):
        """Test BY_STORY grouping."""
        assert GroupingStrategy.BY_STORY.value == "by_story"

    def test_by_element_story(self):
        """Test BY_ELEMENT_STORY grouping."""
        assert GroupingStrategy.BY_ELEMENT_STORY.value == "by_element_story"

    def test_by_element_direction_story(self):
        """Test BY_ELEMENT_DIRECTION_STORY grouping."""
        assert GroupingStrategy.BY_ELEMENT_DIRECTION_STORY.value == "by_element_direction_story"

    def test_by_unique_name(self):
        """Test BY_UNIQUE_NAME grouping."""
        assert GroupingStrategy.BY_UNIQUE_NAME.value == "by_unique_name"


class TestCacheConfig:
    """Tests for CacheConfig dataclass."""

    def test_basic_config_creation(self):
        """Test creating a basic CacheConfig."""
        config = CacheConfig(
            name="test",
            description="Test config",
            cache_type=CacheType.GLOBAL,
            result_type="TestType",
            model_module="database.models",
            model_class="TestModel",
            value_field="value",
        )

        assert config.name == "test"
        assert config.cache_type == CacheType.GLOBAL
        assert config.result_type == "TestType"
        assert config.value_field == "value"

    def test_default_grouping_is_by_story(self):
        """Test that default grouping is BY_STORY."""
        config = CacheConfig(
            name="test",
            description="Test",
            cache_type=CacheType.GLOBAL,
            result_type="Test",
            model_module="database.models",
            model_class="TestModel",
            value_field="value",
        )
        assert config.grouping == GroupingStrategy.BY_STORY

    def test_optional_fields_default_to_none(self):
        """Test that optional fields default to None or empty."""
        config = CacheConfig(
            name="test",
            description="Test",
            cache_type=CacheType.GLOBAL,
            result_type="Test",
            model_module="database.models",
            model_class="TestModel",
            value_field="value",
        )

        assert config.max_value_field is None
        assert config.direction_field is None
        assert config.element_type is None
        assert config.directions == []

    def test_with_all_optional_fields(self):
        """Test creating config with all optional fields."""
        config = CacheConfig(
            name="test",
            description="Test",
            cache_type=CacheType.ELEMENT,
            result_type="WallShears_V2",
            model_module="database.models",
            model_class="WallShear",
            value_field="force",
            max_value_field="max_force",
            direction_field="direction",
            directions=["V2", "V3"],
            element_type="Wall",
            grouping=GroupingStrategy.BY_ELEMENT_DIRECTION_STORY,
            requires_result_category=False,
            requires_result_set=True,
        )

        assert config.max_value_field == "max_force"
        assert config.direction_field == "direction"
        assert config.directions == ["V2", "V3"]
        assert config.element_type == "Wall"
        assert config.grouping == GroupingStrategy.BY_ELEMENT_DIRECTION_STORY
        assert config.requires_result_category is False
        assert config.requires_result_set is True


class TestGlobalCacheConfigs:
    """Tests for GLOBAL_CACHE_CONFIGS."""

    def test_contains_drifts(self):
        """Test that drifts config exists."""
        assert "drifts" in GLOBAL_CACHE_CONFIGS
        config = GLOBAL_CACHE_CONFIGS["drifts"]
        assert config.cache_type == CacheType.GLOBAL
        assert config.model_class == "StoryDrift"
        assert config.value_field == "drift"

    def test_contains_accelerations(self):
        """Test that accelerations config exists."""
        assert "accelerations" in GLOBAL_CACHE_CONFIGS
        config = GLOBAL_CACHE_CONFIGS["accelerations"]
        assert config.model_class == "StoryAcceleration"

    def test_contains_forces(self):
        """Test that forces config exists."""
        assert "forces" in GLOBAL_CACHE_CONFIGS
        config = GLOBAL_CACHE_CONFIGS["forces"]
        assert config.model_class == "StoryForce"

    def test_contains_displacements(self):
        """Test that displacements config exists."""
        assert "displacements" in GLOBAL_CACHE_CONFIGS
        config = GLOBAL_CACHE_CONFIGS["displacements"]
        assert config.model_class == "StoryDisplacement"

    def test_all_global_configs_use_by_story_grouping(self):
        """Test that all global configs use BY_STORY grouping."""
        for name, config in GLOBAL_CACHE_CONFIGS.items():
            assert config.grouping == GroupingStrategy.BY_STORY, f"{name} should use BY_STORY"

    def test_all_global_configs_have_direction_field(self):
        """Test that all global configs have direction_field set."""
        for name, config in GLOBAL_CACHE_CONFIGS.items():
            assert config.direction_field == "direction", f"{name} should have direction_field"


class TestElementCacheConfigs:
    """Tests for ELEMENT_CACHE_CONFIGS."""

    def test_contains_wall_shears(self):
        """Test that wall shear configs exist."""
        assert "wall_shears_v2" in ELEMENT_CACHE_CONFIGS
        assert "wall_shears_v3" in ELEMENT_CACHE_CONFIGS

    def test_contains_column_shears(self):
        """Test that column shear configs exist."""
        assert "column_shears_v2" in ELEMENT_CACHE_CONFIGS
        assert "column_shears_v3" in ELEMENT_CACHE_CONFIGS

    def test_contains_column_rotations(self):
        """Test that column rotation configs exist."""
        assert "column_rotations_r2" in ELEMENT_CACHE_CONFIGS
        assert "column_rotations_r3" in ELEMENT_CACHE_CONFIGS

    def test_contains_beam_rotations(self):
        """Test that beam rotation config exists."""
        assert "beam_rotations" in ELEMENT_CACHE_CONFIGS

    def test_contains_quad_rotations(self):
        """Test that quad rotation config exists."""
        assert "quad_rotations" in ELEMENT_CACHE_CONFIGS

    def test_wall_shear_config_properties(self):
        """Test wall shear config has correct properties."""
        config = ELEMENT_CACHE_CONFIGS["wall_shears_v2"]
        assert config.cache_type == CacheType.ELEMENT
        assert config.element_type == "Wall"
        assert config.directions == ["V2"]
        assert config.grouping == GroupingStrategy.BY_ELEMENT_DIRECTION_STORY

    def test_rotation_configs_have_max_value_field(self):
        """Test that rotation configs have max_value_field."""
        rotation_configs = [
            "column_rotations_r2",
            "column_rotations_r3",
            "beam_rotations",
            "quad_rotations",
        ]
        for name in rotation_configs:
            config = ELEMENT_CACHE_CONFIGS[name]
            assert config.max_value_field is not None, f"{name} should have max_value_field"


class TestJointCacheConfigs:
    """Tests for JOINT_CACHE_CONFIGS."""

    def test_contains_soil_pressures(self):
        """Test that soil pressures config exists."""
        assert "soil_pressures" in JOINT_CACHE_CONFIGS
        config = JOINT_CACHE_CONFIGS["soil_pressures"]
        assert config.cache_type == CacheType.JOINT
        assert config.model_class == "SoilPressure"

    def test_contains_vertical_displacements(self):
        """Test that vertical displacements config exists."""
        assert "vertical_displacements" in JOINT_CACHE_CONFIGS
        config = JOINT_CACHE_CONFIGS["vertical_displacements"]
        assert config.model_class == "VerticalDisplacement"

    def test_joint_configs_use_by_unique_name_grouping(self):
        """Test that joint configs use BY_UNIQUE_NAME grouping."""
        for name, config in JOINT_CACHE_CONFIGS.items():
            assert config.grouping == GroupingStrategy.BY_UNIQUE_NAME

    def test_joint_configs_require_result_set(self):
        """Test that joint configs require result set."""
        for name, config in JOINT_CACHE_CONFIGS.items():
            assert config.requires_result_set is True


class TestAllCacheConfigs:
    """Tests for ALL_CACHE_CONFIGS combined dict."""

    def test_contains_all_global_configs(self):
        """Test that all global configs are in combined dict."""
        for name in GLOBAL_CACHE_CONFIGS:
            assert name in ALL_CACHE_CONFIGS

    def test_contains_all_element_configs(self):
        """Test that all element configs are in combined dict."""
        for name in ELEMENT_CACHE_CONFIGS:
            assert name in ALL_CACHE_CONFIGS

    def test_contains_all_joint_configs(self):
        """Test that all joint configs are in combined dict."""
        for name in JOINT_CACHE_CONFIGS:
            assert name in ALL_CACHE_CONFIGS

    def test_total_count(self):
        """Test total config count."""
        expected = (
            len(GLOBAL_CACHE_CONFIGS) +
            len(ELEMENT_CACHE_CONFIGS) +
            len(JOINT_CACHE_CONFIGS)
        )
        assert len(ALL_CACHE_CONFIGS) == expected


class TestGetCacheConfig:
    """Tests for get_cache_config function."""

    def test_returns_config_for_valid_name(self):
        """Test that valid name returns config."""
        config = get_cache_config("drifts")
        assert config.name == "drifts"
        assert config.model_class == "StoryDrift"

    def test_raises_key_error_for_unknown_name(self):
        """Test that KeyError is raised for unknown name."""
        with pytest.raises(KeyError) as exc_info:
            get_cache_config("unknown_config")

        assert "Unknown cache config" in str(exc_info.value)

    def test_error_message_lists_available_configs(self):
        """Test that error message shows available configs."""
        with pytest.raises(KeyError) as exc_info:
            get_cache_config("nonexistent")

        error_msg = str(exc_info.value)
        assert "Available:" in error_msg


class TestGetConfigsByCacheType:
    """Tests for get_configs_by_cache_type function."""

    def test_returns_global_configs(self):
        """Test getting global cache configs."""
        configs = get_configs_by_cache_type(CacheType.GLOBAL)
        assert len(configs) == len(GLOBAL_CACHE_CONFIGS)
        for config in configs.values():
            assert config.cache_type == CacheType.GLOBAL

    def test_returns_element_configs(self):
        """Test getting element cache configs."""
        configs = get_configs_by_cache_type(CacheType.ELEMENT)
        assert len(configs) == len(ELEMENT_CACHE_CONFIGS)
        for config in configs.values():
            assert config.cache_type == CacheType.ELEMENT

    def test_returns_joint_configs(self):
        """Test getting joint cache configs."""
        configs = get_configs_by_cache_type(CacheType.JOINT)
        assert len(configs) == len(JOINT_CACHE_CONFIGS)
        for config in configs.values():
            assert config.cache_type == CacheType.JOINT


class TestGetConfigsByElementType:
    """Tests for get_configs_by_element_type function."""

    def test_returns_wall_configs(self):
        """Test getting wall element configs."""
        configs = get_configs_by_element_type("Wall")
        assert len(configs) >= 2  # At least V2 and V3
        for config in configs.values():
            assert config.element_type == "Wall"

    def test_returns_column_configs(self):
        """Test getting column element configs."""
        configs = get_configs_by_element_type("Column")
        assert len(configs) >= 4  # V2, V3 shears + R2, R3 rotations
        for config in configs.values():
            assert config.element_type == "Column"

    def test_returns_beam_configs(self):
        """Test getting beam element configs."""
        configs = get_configs_by_element_type("Beam")
        assert len(configs) >= 1
        for config in configs.values():
            assert config.element_type == "Beam"

    def test_returns_quad_configs(self):
        """Test getting quad element configs."""
        configs = get_configs_by_element_type("Quad")
        assert len(configs) >= 1
        for config in configs.values():
            assert config.element_type == "Quad"

    def test_returns_empty_for_unknown_type(self):
        """Test that unknown element type returns empty dict."""
        configs = get_configs_by_element_type("UnknownType")
        assert configs == {}
