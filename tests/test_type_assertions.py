"""
Tests for type assertions generation.

Covers:
- Simple types (int, str, float, bool)
- None type
- Optional types (Optional[X], X | None)
- Union types (X | Y, Union[X, Y])
- Union with None (X | Y | None)
- Generic containers (list[X], dict[K, V], set[X])
- Complex unions in containers (list[X | None])
- Unknown/complex types (fallback behavior)
"""

import pytest
from src.generators.evidence.type_assertions import (
    generate_type_assertions,
    parse_type_hint,
    generate_isinstance_expression,
    ParsedType,
)


class TestParseTypeHint:
    """Tests for parse_type_hint function."""
    
    def test_parse_simple_types(self):
        """Test parsing simple types."""
        result = parse_type_hint("str")
        assert result.base_types == ["str"]
        assert result.allows_none is False
        assert result.is_valid is True
        
        result = parse_type_hint("int")
        assert result.base_types == ["int"]
        assert result.allows_none is False
        assert result.is_valid is True
    
    def test_parse_none(self):
        """Test parsing None type."""
        result = parse_type_hint("None")
        assert result.base_types == []
        assert result.allows_none is True
        assert result.is_valid is True
    
    def test_parse_optional(self):
        """Test parsing Optional[X]."""
        result = parse_type_hint("Optional[str]")
        assert result.base_types == ["str"]
        assert result.allows_none is True
        assert result.is_valid is True
        
        result = parse_type_hint("Optional[int]")
        assert result.base_types == ["int"]
        assert result.allows_none is True
        assert result.is_valid is True
    
    def test_parse_union_with_none(self):
        """Test parsing X | None syntax."""
        result = parse_type_hint("str | None")
        assert result.base_types == ["str"]
        assert result.allows_none is True
        assert result.is_valid is True
        
        result = parse_type_hint("int | None")
        assert result.base_types == ["int"]
        assert result.allows_none is True
        assert result.is_valid is True
    
    def test_parse_union_without_none(self):
        """Test parsing X | Y syntax."""
        result = parse_type_hint("int | str")
        assert set(result.base_types) == {"int", "str"}
        assert result.allows_none is False
        assert result.is_valid is True
    
    def test_parse_union_multiple_with_none(self):
        """Test parsing X | Y | None syntax."""
        result = parse_type_hint("int | str | None")
        assert set(result.base_types) == {"int", "str"}
        assert result.allows_none is True
        assert result.is_valid is True
    
    def test_parse_typing_union(self):
        """Test parsing Union[X, Y] syntax."""
        result = parse_type_hint("Union[str, int]")
        assert set(result.base_types) == {"str", "int"}
        assert result.allows_none is False
        assert result.is_valid is True
        
        result = parse_type_hint("Union[str, None]")
        assert result.base_types == ["str"]
        assert result.allows_none is True
        assert result.is_valid is True
    
    def test_parse_unknown_type(self):
        """Test parsing unknown/custom types."""
        result = parse_type_hint("MyClass")
        assert result.base_types == ["MyClass"]
        assert result.allows_none is False
        assert result.is_valid is False  # Can't isinstance check unknown types
    
    def test_parse_with_whitespace(self):
        """Test parsing handles whitespace."""
        result = parse_type_hint("  str  |  None  ")
        assert result.base_types == ["str"]
        assert result.allows_none is True


class TestGenerateIsinstanceExpression:
    """Tests for generate_isinstance_expression function."""
    
    def test_simple_type(self):
        """Test simple type expression."""
        parsed = ParsedType(base_types=["str"], allows_none=False, is_valid=True)
        result = generate_isinstance_expression(parsed)
        assert result == "isinstance(result, str)"
    
    def test_float_type(self):
        """Test float includes int check."""
        parsed = ParsedType(base_types=["float"], allows_none=False, is_valid=True)
        result = generate_isinstance_expression(parsed)
        assert result == "isinstance(result, (int, float))"
    
    def test_with_none(self):
        """Test expression with None allowed."""
        parsed = ParsedType(base_types=["str"], allows_none=True, is_valid=True)
        result = generate_isinstance_expression(parsed)
        assert result == "result is None or isinstance(result, str)"
    
    def test_only_none(self):
        """Test expression when only None is allowed."""
        parsed = ParsedType(base_types=[], allows_none=True, is_valid=True)
        result = generate_isinstance_expression(parsed)
        assert result == "result is None"
    
    def test_multiple_types(self):
        """Test union of multiple types."""
        parsed = ParsedType(base_types=["int", "str"], allows_none=False, is_valid=True)
        result = generate_isinstance_expression(parsed)
        assert result == "isinstance(result, (int, str))"
    
    def test_multiple_types_with_none(self):
        """Test union of multiple types with None."""
        parsed = ParsedType(base_types=["int", "str"], allows_none=True, is_valid=True)
        result = generate_isinstance_expression(parsed)
        assert result == "result is None or isinstance(result, (int, str))"
    
    def test_invalid_type_returns_none(self):
        """Test invalid type returns None."""
        parsed = ParsedType(base_types=["MyClass"], allows_none=False, is_valid=False)
        result = generate_isinstance_expression(parsed)
        assert result is None
    
    def test_custom_var_name(self):
        """Test custom variable name."""
        parsed = ParsedType(base_types=["str"], allows_none=False, is_valid=True)
        result = generate_isinstance_expression(parsed, "x")
        assert result == "isinstance(x, str)"
        
        parsed = ParsedType(base_types=["str"], allows_none=True, is_valid=True)
        result = generate_isinstance_expression(parsed, "item")
        assert result == "item is None or isinstance(item, str)"


class TestGenerateTypeAssertionsSimple:
    """Tests for generate_type_assertions with simple types."""
    
    def test_int(self):
        """Test int type assertion."""
        assertions = generate_type_assertions("int")
        assert assertions == ["assert isinstance(result, int)"]
    
    def test_str(self):
        """Test str type assertion."""
        assertions = generate_type_assertions("str")
        assert assertions == ["assert isinstance(result, str)"]
    
    def test_float(self):
        """Test float type assertion (accepts int too)."""
        assertions = generate_type_assertions("float")
        assert assertions == ["assert isinstance(result, (int, float))"]
    
    def test_bool(self):
        """Test bool type assertion."""
        assertions = generate_type_assertions("bool")
        assert assertions == ["assert isinstance(result, bool)"]
    
    def test_none(self):
        """Test None type assertion."""
        assertions = generate_type_assertions("None")
        assert assertions == ["assert result is None"]
    
    def test_empty_returns_empty(self):
        """Test empty/None input returns empty list."""
        assert generate_type_assertions(None) == []
        assert generate_type_assertions("") == []


class TestGenerateTypeAssertionsOptional:
    """Tests for Optional and X | None types."""
    
    def test_optional_str(self):
        """Test Optional[str]."""
        assertions = generate_type_assertions("Optional[str]")
        assert assertions == ["assert result is None or isinstance(result, str)"]
    
    def test_optional_int(self):
        """Test Optional[int]."""
        assertions = generate_type_assertions("Optional[int]")
        assert assertions == ["assert result is None or isinstance(result, int)"]
    
    def test_str_or_none(self):
        """Test str | None syntax."""
        assertions = generate_type_assertions("str | None")
        assert assertions == ["assert result is None or isinstance(result, str)"]
    
    def test_int_or_none(self):
        """Test int | None syntax."""
        assertions = generate_type_assertions("int | None")
        assert assertions == ["assert result is None or isinstance(result, int)"]
    
    def test_none_or_str(self):
        """Test None | str syntax (reversed order)."""
        assertions = generate_type_assertions("None | str")
        assert assertions == ["assert result is None or isinstance(result, str)"]


class TestGenerateTypeAssertionsUnion:
    """Tests for Union types without None."""
    
    def test_int_or_str(self):
        """Test int | str union."""
        assertions = generate_type_assertions("int | str")
        assert assertions == ["assert isinstance(result, (int, str))"]
    
    def test_int_str_float(self):
        """Test int | str | float union."""
        assertions = generate_type_assertions("int | str | float")
        # Should deduplicate int from float's (int, float)
        assert len(assertions) == 1
        assert "isinstance(result," in assertions[0]
    
    def test_int_str_none(self):
        """Test int | str | None union."""
        assertions = generate_type_assertions("int | str | None")
        assert assertions == ["assert result is None or isinstance(result, (int, str))"]
    
    def test_union_syntax(self):
        """Test Union[X, Y] syntax."""
        assertions = generate_type_assertions("Union[int, str]")
        assert assertions == ["assert isinstance(result, (int, str))"]
    
    def test_union_with_none_syntax(self):
        """Test Union[X, None] syntax."""
        assertions = generate_type_assertions("Union[str, None]")
        assert assertions == ["assert result is None or isinstance(result, str)"]


class TestGenerateTypeAssertionsList:
    """Tests for list[X] types."""
    
    def test_list_int(self):
        """Test list[int]."""
        assertions = generate_type_assertions("list[int]")
        assert len(assertions) == 2
        assert assertions[0] == "assert isinstance(result, list)"
        assert "all(isinstance(x, int) for x in result)" in assertions[1]
    
    def test_list_str(self):
        """Test list[str]."""
        assertions = generate_type_assertions("list[str]")
        assert len(assertions) == 2
        assert assertions[0] == "assert isinstance(result, list)"
        assert "all(isinstance(x, str) for x in result)" in assertions[1]
    
    def test_list_str_or_none(self):
        """Test list[str | None] - THE KEY BUG FIX."""
        assertions = generate_type_assertions("list[str | None]")
        assert len(assertions) == 2
        assert assertions[0] == "assert isinstance(result, list)"
        # Should NOT generate invalid isinstance(x, str | None)
        assert "x is None or isinstance(x, str)" in assertions[1]
        # Verify no invalid syntax
        assert "isinstance(x, str | None)" not in assertions[1]
    
    def test_list_int_or_none(self):
        """Test list[int | None]."""
        assertions = generate_type_assertions("list[int | None]")
        assert len(assertions) == 2
        assert "x is None or isinstance(x, int)" in assertions[1]
    
    def test_list_int_or_str(self):
        """Test list[int | str]."""
        assertions = generate_type_assertions("list[int | str]")
        assert len(assertions) == 2
        assert "isinstance(x, (int, str))" in assertions[1]
    
    def test_list_int_or_str_or_none(self):
        """Test list[int | str | None]."""
        assertions = generate_type_assertions("list[int | str | None]")
        assert len(assertions) == 2
        assert "x is None or isinstance(x, (int, str))" in assertions[1]
    
    def test_list_optional(self):
        """Test list[Optional[str]]."""
        assertions = generate_type_assertions("list[Optional[str]]")
        assert len(assertions) == 2
        assert "x is None or isinstance(x, str)" in assertions[1]
    
    def test_list_unknown_type_fallback(self):
        """Test list[MyClass] falls back to container only."""
        assertions = generate_type_assertions("list[MyClass]")
        assert len(assertions) == 1  # Only container check
        assert assertions[0] == "assert isinstance(result, list)"
    
    def test_list_handles_empty(self):
        """Test list assertions handle empty lists."""
        assertions = generate_type_assertions("list[int]")
        # Should have "if result else True" to handle empty lists
        assert "if result else True" in assertions[1]


class TestGenerateTypeAssertionsDict:
    """Tests for dict[K, V] types."""
    
    def test_dict_str_int(self):
        """Test dict[str, int]."""
        assertions = generate_type_assertions("dict[str, int]")
        assert len(assertions) == 3
        assert assertions[0] == "assert isinstance(result, dict)"
        assert "isinstance(k, str)" in assertions[1]
        assert "isinstance(v, int)" in assertions[2]
    
    def test_dict_str_int_or_none(self):
        """Test dict[str, int | None]."""
        assertions = generate_type_assertions("dict[str, int | None]")
        assert len(assertions) == 3
        assert assertions[0] == "assert isinstance(result, dict)"
        assert "isinstance(k, str)" in assertions[1]
        assert "v is None or isinstance(v, int)" in assertions[2]
    
    def test_dict_str_or_none_int(self):
        """Test dict[str | None, int]."""
        assertions = generate_type_assertions("dict[str | None, int]")
        assert len(assertions) == 3
        assert "k is None or isinstance(k, str)" in assertions[1]
        assert "isinstance(v, int)" in assertions[2]
    
    def test_dict_unknown_value_fallback(self):
        """Test dict[str, MyClass] falls back to key check only."""
        assertions = generate_type_assertions("dict[str, MyClass]")
        assert len(assertions) == 2  # Container + key check only
        assert assertions[0] == "assert isinstance(result, dict)"
        assert "isinstance(k, str)" in assertions[1]


class TestGenerateTypeAssertionsSet:
    """Tests for set[X] types."""
    
    def test_set_int(self):
        """Test set[int]."""
        assertions = generate_type_assertions("set[int]")
        assert len(assertions) == 2
        assert assertions[0] == "assert isinstance(result, set)"
        assert "isinstance(x, int)" in assertions[1]
    
    def test_set_str_or_none(self):
        """Test set[str | None]."""
        assertions = generate_type_assertions("set[str | None]")
        assert len(assertions) == 2
        assert "x is None or isinstance(x, str)" in assertions[1]


class TestGenerateTypeAssertionsTuple:
    """Tests for tuple types (complex - fallback to container only)."""
    
    def test_tuple_simple(self):
        """Test tuple[int, str] - falls back to container check."""
        assertions = generate_type_assertions("tuple[int, str]")
        assert assertions == ["assert isinstance(result, tuple)"]
    
    def test_tuple_homogeneous(self):
        """Test tuple[int, ...] - still falls back."""
        assertions = generate_type_assertions("tuple[int, ...]")
        assert assertions == ["assert isinstance(result, tuple)"]


class TestGenerateTypeAssertionsEdgeCases:
    """Tests for edge cases and special scenarios."""
    
    def test_unknown_type_returns_empty(self):
        """Test unknown type returns empty list."""
        assertions = generate_type_assertions("MyCustomClass")
        assert assertions == []
    
    def test_nested_generic_fallback(self):
        """Test nested generics fall back to container only."""
        assertions = generate_type_assertions("list[list[int]]")
        # Inner type "list[int]" is not in SIMPLE_TYPES, so falls back
        assert len(assertions) == 1
        assert assertions[0] == "assert isinstance(result, list)"
    
    def test_whitespace_handling(self):
        """Test handles extra whitespace."""
        assertions = generate_type_assertions("  str  ")
        assert assertions == ["assert isinstance(result, str)"]
        
        assertions = generate_type_assertions("  str   |   None  ")
        assert assertions == ["assert result is None or isinstance(result, str)"]
    
    def test_typing_optional(self):
        """Test typing.Optional[X] syntax."""
        assertions = generate_type_assertions("typing.Optional[str]")
        assert assertions == ["assert result is None or isinstance(result, str)"]
    
    def test_typing_union(self):
        """Test typing.Union[X, Y] syntax."""
        assertions = generate_type_assertions("typing.Union[int, str]")
        assert assertions == ["assert isinstance(result, (int, str))"]


class TestGenerateTypeAssertionsNoInvalidCode:
    """Tests to ensure we NEVER generate invalid isinstance checks."""
    
    def test_no_isinstance_with_none_type(self):
        """Ensure isinstance never includes None directly."""
        test_cases = [
            "str | None",
            "int | None",
            "int | str | None",
            "Optional[str]",
            "Optional[int]",
            "list[str | None]",
            "list[int | None]",
            "dict[str, int | None]",
            "set[str | None]",
        ]
        
        for type_hint in test_cases:
            assertions = generate_type_assertions(type_hint)
            for assertion in assertions:
                # These patterns would be invalid Python
                assert "isinstance(result, None)" not in assertion
                assert "isinstance(x, None)" not in assertion
                assert ", None)" not in assertion  # isinstance tuple with None
                # The | syntax in isinstance is only valid for actual types, not None
                assert "| None)" not in assertion
    
    def test_always_handles_none_separately(self):
        """Ensure None is always handled with 'is None' check."""
        test_cases = [
            ("str | None", "result is None or"),
            ("int | None", "result is None or"),
            ("list[str | None]", "x is None or"),
            ("dict[str, int | None]", "v is None or"),
        ]
        
        for type_hint, expected_fragment in test_cases:
            assertions = generate_type_assertions(type_hint)
            found = any(expected_fragment in a for a in assertions)
            assert found, f"Expected '{expected_fragment}' in assertions for {type_hint}: {assertions}"
