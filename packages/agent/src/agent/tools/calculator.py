"""Safe arithmetic calculator tool using Abstract Syntax Tree (AST) validation."""

import ast
import operator
import uuid
from collections.abc import Callable
from typing import Any

import structlog

from agent.tools.base import BaseTool, ToolResult

logger = structlog.get_logger(__name__)

# Permitted mathematical operations
OPERATORS: dict[type[ast.AST], Callable[..., Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_ast(node: ast.AST) -> float | int:
    """Recursively evaluates an AST node containing only safe arithmetic."""
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")
    elif isinstance(node, ast.BinOp):
        bin_op_type = type(node.op)
        if bin_op_type not in OPERATORS:
            raise ValueError(f"Unsupported operator: {bin_op_type}")
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        if bin_op_type is ast.Pow and right > 1000:
            raise ValueError("Exponent too large")
        if (bin_op_type in (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise ZeroDivisionError("Division by zero")
        bin_fn = OPERATORS[bin_op_type]
        res = bin_fn(left, right)
        return float(res) if isinstance(res, float) else int(res)
    elif isinstance(node, ast.UnaryOp):
        unary_op_type = type(node.op)
        if unary_op_type not in OPERATORS:
            raise ValueError(f"Unsupported unary operator: {unary_op_type}")
        unary_fn = OPERATORS[unary_op_type]
        res = unary_fn(_eval_ast(node.operand))
        return float(res) if isinstance(res, float) else int(res)
    else:
        raise ValueError(f"Disallowed expression syntax: {type(node).__name__}")


class CalculatorTool(BaseTool):
    """Safely evaluates arithmetic expressions (e.g., dosage calculations, unit adjustments)."""

    name = "calculator"
    description = (
        "Safely compute mathematical and dosage expressions (e.g. '100 * 0.5', '(150 / 70) * 1.5'). "
        "Supports addition (+), subtraction (-), multiplication (*), division (/), and exponents (**). "
        "Never attempts arbitrary code execution."
    )
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The mathematical expression string to evaluate (e.g., '50 * 2.5')",
            }
        },
        "required": ["expression"],
    }

    async def execute(self, org_id: uuid.UUID, **kwargs: Any) -> ToolResult:
        expr = kwargs.get("expression", "").strip()
        if not expr:
            return ToolResult(
                tool_name=self.name, success=False, data=None, error="Expression is required"
            )

        try:
            tree = ast.parse(expr, mode="eval")
            result = _eval_ast(tree)
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"expression": expr, "result": result},
            )
        except ZeroDivisionError:
            return ToolResult(
                tool_name=self.name, success=False, data=None, error="Division by zero"
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name, success=False, data=None, error=f"Invalid expression: {e}"
            )
