import math
try:
    import sympy as sp
except ImportError:
    sp = None

class AdvancedMathTool:
    """
    Kalkulator Matematika Tingkat Lanjut J.A.R.V.I.S
    Mendukung evaluasi, penyederhanaan aljabar, turunan, dan pencarian akar.
    """
    ToolName = "AdvancedMathTool"
    Schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["evaluate", "simplify", "derivative", "solve"],
                "description": "Aksi matematika yang ingin dilakukan (evaluate, simplify, derivative, solve)."
            },
            "expression": {
                "type": "string",
                "description": "Ekspresi matematika (contoh: 'x**2 + 2*x + 1' atau 'sin(x)')."
            },
            "variable": {
                "type": "string",
                "description": "Variabel untuk turunan atau penyelesaian persamaan (default: 'x')."
            }
        },
        "required": ["action", "expression"]
    }

    def Execute(self, **kwargs):
        action = kwargs.get("action")
        expr_str = kwargs.get("expression")
        var_str = kwargs.get("variable", "x")

        # Fallback to basic math if sympy is missing
        if sp is None:
            if action == "evaluate":
                try:
                    # Create a safe environment with math functions
                    safe_dict = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
                    result = eval(expr_str, {"__builtins__": {}}, safe_dict)
                    return f"Result (Basic Math): {result}"
                except Exception as e:
                    return f"Error evaluating expression: {e}"
            else:
                return "Error: Pustaka 'sympy' diperlukan untuk fitur simplify, derivative, dan solve. Silakan install dengan 'pip install sympy'."
        
        # Using SymPy for advanced operations
        try:
            # Define the symbol based on user input
            x = sp.Symbol(var_str)
            # Parse the expression
            expr = sp.sympify(expr_str)
            
            if action == "evaluate":
                # Evaluate numerically if possible
                result = expr.evalf()
                return f"Result: {result}"
            elif action == "simplify":
                result = sp.simplify(expr)
                return f"Simplified: {result}"
            elif action == "derivative":
                result = sp.diff(expr, x)
                return f"Derivative (d/d{var_str}): {result}"
            elif action == "solve":
                # Solve expr == 0
                result = sp.solve(expr, x)
                return f"Roots (Solutions for {var_str}): {result}"
            else:
                return f"Error: Aksi '{action}' tidak dikenali."
        except Exception as e:
            return f"Math Error: {e}"
