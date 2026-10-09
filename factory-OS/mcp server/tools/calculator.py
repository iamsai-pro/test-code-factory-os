"""Restricted arithmetic evaluator; never uses eval()."""
import ast
import math
import operator

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}
_FUNCTIONS = {
    "sqrt": math.sqrt, "abs": abs, "round": round, "pow": pow,
    "log": math.log, "log10": math.log10, "exp": math.exp,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "floor": math.floor, "ceil": math.ceil,
    "factorial": math.factorial, "radians": math.radians,
    "degrees": math.degrees,
}


def _evaluate(node):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e100):
            raise ValueError("Exponent/base too large")
        result = _BIN_OPS[type(node.op)](left, right)
        if isinstance(result, (int, float)) and (abs(result) > 1e300):
            raise ValueError("Result too large")
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        if name not in _FUNCTIONS or node.keywords:
            raise ValueError("Function is not allowed or keyword arguments were used")
        args = [_evaluate(arg) for arg in node.args]
        if name == "factorial" and (len(args) != 1 or args[0] > 500):
            raise ValueError("factorial accepts one argument up to 500")
        return _FUNCTIONS[name](*args)
    raise ValueError(f"Unsupported expression element: {type(node).__name__}")


def calculate(expression: str):
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("Expression must be a non-empty string")
    if len(expression) > 500:
        raise ValueError("Expression is too long")
    result = _evaluate(ast.parse(expression, mode="eval").body)
    if isinstance(result, float) and not math.isfinite(result):
        raise ValueError("Result is not finite")
    return result
