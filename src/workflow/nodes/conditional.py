"""
Conditional Node for GG Workflow Framework

Implements if/else branching logic based on conditions.
Supports multiple conditions, operators, and custom evaluators.

Author: Grokputer Team
Date: 2025-11-16
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .base import BaseNode, NodeContext


class ComparisonOperator(Enum):
    """Supported comparison operators."""

    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


class LogicOperator(Enum):
    """Logic operators for combining conditions."""

    AND = "and"
    OR = "or"


class ConditionalNode(BaseNode):
    """
    Node for conditional branching (if/else logic).

    The node evaluates conditions and sets a "branch" value in the output context.
    The workflow engine uses this to determine which path to follow.

    Configuration:
        conditions: List of condition dicts with:
            - field: Field name to check (uses dot notation for nested)
            - operator: Comparison operator
            - value: Value to compare against (can use {{variables}})
        logic: How to combine conditions ("and" or "or", default: "and")
        custom_evaluator: Optional callable for custom condition logic

    Example:
        node = ConditionalNode(
            "check_status",
            config={
                "conditions": [
                    {"field": "status", "operator": "==", "value": "active"},
                    {"field": "count", "operator": ">", "value": 10}
                ],
                "logic": "and"
            }
        )

        # Output context will have:
        # context.data["branch"] = "true" or "false"
    """

    def __init__(self, node_id: str, name: Optional[str] = None, config: Optional[Dict] = None):
        super().__init__(node_id, name, config)

        # Validate config
        if not self.config.get("conditions") and not self.config.get("custom_evaluator"):
            raise ValueError(
                f"ConditionalNode {node_id} requires 'conditions' or 'custom_evaluator' in config"
            )

        # Set defaults
        self.config.setdefault("logic", "and")

    async def execute(self, context: NodeContext) -> NodeContext:
        """
        Evaluate conditions and set branch.

        Args:
            context: Input context

        Returns:
            Output context with "branch" field set to "true" or "false"
        """
        # Use custom evaluator if provided
        if "custom_evaluator" in self.config:
            evaluator = self.config["custom_evaluator"]
            result = evaluator(context)
        else:
            # Evaluate conditions
            result = self._evaluate_conditions(context)

        # Set branch in output
        output_context = NodeContext(
            data=context.data.copy(),
            metadata=context.metadata,
            state=context.state,
        )
        output_context.set("branch", "true" if result else "false")
        output_context.set_state(f"{self.node_id}_result", result)

        return output_context

    def _evaluate_conditions(self, context: NodeContext) -> bool:
        """Evaluate all conditions according to logic operator."""
        conditions = self.config["conditions"]
        logic = LogicOperator[self.config["logic"].upper()]

        results = []
        for condition in conditions:
            result = self._evaluate_single_condition(condition, context)
            results.append(result)

        # Combine results
        if logic == LogicOperator.AND:
            return all(results)
        else:  # OR
            return any(results)

    def _evaluate_single_condition(self, condition: Dict, context: NodeContext) -> bool:
        """Evaluate a single condition."""
        field = condition["field"]
        operator = ComparisonOperator(condition["operator"])
        expected_value = condition.get("value")

        # Get actual value from context (supports dot notation)
        actual_value = self._get_nested_value(context.data, field)

        # Evaluate based on operator
        if operator == ComparisonOperator.EQUALS:
            return actual_value == expected_value

        elif operator == ComparisonOperator.NOT_EQUALS:
            return actual_value != expected_value

        elif operator == ComparisonOperator.GREATER_THAN:
            return actual_value > expected_value

        elif operator == ComparisonOperator.GREATER_EQUAL:
            return actual_value >= expected_value

        elif operator == ComparisonOperator.LESS_THAN:
            return actual_value < expected_value

        elif operator == ComparisonOperator.LESS_EQUAL:
            return actual_value <= expected_value

        elif operator == ComparisonOperator.CONTAINS:
            return expected_value in actual_value

        elif operator == ComparisonOperator.NOT_CONTAINS:
            return expected_value not in actual_value

        elif operator == ComparisonOperator.IN:
            return actual_value in expected_value

        elif operator == ComparisonOperator.NOT_IN:
            return actual_value not in expected_value

        elif operator == ComparisonOperator.IS_EMPTY:
            return not actual_value or len(actual_value) == 0

        elif operator == ComparisonOperator.IS_NOT_EMPTY:
            return bool(actual_value) and len(actual_value) > 0

        else:
            raise ValueError(f"Unknown operator: {operator}")

    def _get_nested_value(self, data: Dict, field: str) -> Any:
        """
        Get value from nested dict using dot notation.

        Example:
            data = {"user": {"profile": {"name": "John"}}}
            _get_nested_value(data, "user.profile.name") -> "John"
        """
        keys = field.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value
