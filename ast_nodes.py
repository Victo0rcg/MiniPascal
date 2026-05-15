# ast_nodes.py  ──  AST node definitions for the Pascal compiler
# Every node stores only the data needed by later compiler phases
# (semantic analysis, IR generation, code generation).

class Node:
    """Base class for all AST nodes."""
    pass


# ═══════════════════════════════════════════════════════════════
#  PROGRAM STRUCTURE
# ═══════════════════════════════════════════════════════════════

class Program(Node):
    """Root of the AST.

    Attributes:
        name  (str)       – program identifier
        uses  ([str])     – unit names from the USES clause (may be [])
        block (Block)     – the main block
    """
    def __init__(self, name, uses, block):
        self.name  = name
        self.uses  = uses
        self.block = block

    def __repr__(self):
        return f"Program({self.name!r})"


class Block(Node):
    """A block: zero or more declaration sections followed by a compound statement.

    Attributes:
        decls ([Node])       – VarSection | ConstSection | TypeSection |
                               LabelSection | ProcDecl | FuncDecl
        body  (CompoundStmt)
    """
    def __init__(self, decls, body):
        self.decls = decls
        self.body  = body


# ═══════════════════════════════════════════════════════════════
#  DECLARATIONS
# ═══════════════════════════════════════════════════════════════

class LabelSection(Node):
    def __init__(self, labels):
        self.labels = labels  # [str]


class ConstSection(Node):
    def __init__(self, declarations):
        self.declarations = declarations  # [ConstDecl]


class ConstDecl(Node):
    def __init__(self, name, value):
        self.name  = name   # str
        self.value = value  # expression node


class TypeSection(Node):
    def __init__(self, declarations):
        self.declarations = declarations  # [TypeDecl]


class TypeDecl(Node):
    def __init__(self, name, type_def):
        self.name     = name
        self.type_def = type_def  # type node


class VarSection(Node):
    def __init__(self, declarations):
        self.declarations = declarations  # [VarDecl]


class VarDecl(Node):
    def __init__(self, names, type_node):
        self.names     = names      # [str]
        self.type_node = type_node  # type node


# ═══════════════════════════════════════════════════════════════
#  TYPE NODES
# ═══════════════════════════════════════════════════════════════

class SimpleType(Node):
    """A built-in or user-defined type name."""
    def __init__(self, name):
        self.name = name  # 'integer', 'real', 'boolean', 'char', 'string', ID …

    def __repr__(self):
        return f"SimpleType({self.name!r})"


class StringType(Node):
    """string[N]  –  bounded string."""
    def __init__(self, size):
        self.size = size  # int literal or None for plain 'string'


class ArrayType(Node):
    def __init__(self, ranges, element_type):
        self.ranges       = ranges        # [(low_expr, high_expr), ...]
        self.element_type = element_type  # type node


class RecordType(Node):
    def __init__(self, fields):
        self.fields = fields  # [FieldDecl]


class FieldDecl(Node):
    def __init__(self, names, type_node):
        self.names     = names      # [str]
        self.type_node = type_node


class PointerType(Node):
    def __init__(self, base_type):
        self.base_type = base_type  # str or type node


class SubrangeType(Node):
    def __init__(self, low, high):
        self.low  = low   # expression node
        self.high = high  # expression node


class EnumType(Node):
    def __init__(self, names):
        self.names = names  # [str]


# ═══════════════════════════════════════════════════════════════
#  SUBPROGRAMS
# ═══════════════════════════════════════════════════════════════

class ProcDecl(Node):
    def __init__(self, name, params, body):
        self.name   = name    # str
        self.params = params  # [ParamGroup]
        self.body   = body    # Block | 'forward'


class FuncDecl(Node):
    def __init__(self, name, params, return_type, body):
        self.name        = name
        self.params      = params
        self.return_type = return_type  # type node
        self.body        = body         # Block | 'forward'


class ParamGroup(Node):
    def __init__(self, names, type_node, by_ref=False, is_const=False):
        self.names     = names
        self.type_node = type_node
        self.by_ref    = by_ref      # True for VAR params
        self.is_const  = is_const    # True for CONST params


# ═══════════════════════════════════════════════════════════════
#  STATEMENTS
# ═══════════════════════════════════════════════════════════════

class CompoundStmt(Node):
    def __init__(self, stmts):
        self.stmts = stmts  # [stmt node | None]


class AssignStmt(Node):
    def __init__(self, target, value):
        self.target = target  # Var / ArrayAccess / FieldAccess
        self.value  = value   # expression node


class IfStmt(Node):
    def __init__(self, condition, then_branch, else_branch=None):
        self.condition   = condition
        self.then_branch = then_branch
        self.else_branch = else_branch   # None when there is no ELSE


class WhileStmt(Node):
    def __init__(self, condition, body):
        self.condition = condition
        self.body      = body


class ForStmt(Node):
    def __init__(self, var, start, stop, downto, body):
        self.var    = var     # str
        self.start  = start   # expression node
        self.stop   = stop    # expression node
        self.downto = downto  # True → DOWNTO, False → TO
        self.body   = body


class RepeatStmt(Node):
    def __init__(self, body, condition):
        self.body      = body       # [stmt node]
        self.condition = condition  # expression node


class CaseStmt(Node):
    def __init__(self, expr, arms, otherwise=None):
        self.expr      = expr       # expression node
        self.arms      = arms       # [CaseArm]
        self.otherwise = otherwise  # stmt node or None


class CaseArm(Node):
    def __init__(self, labels, stmt):
        self.labels = labels  # [expr | (lo_expr, hi_expr)]
        self.stmt   = stmt


class WithStmt(Node):
    def __init__(self, variables, body):
        self.variables = variables  # [Var / FieldAccess]
        self.body      = body


class GotoStmt(Node):
    def __init__(self, label):
        self.label = label  # str


class LabeledStmt(Node):
    def __init__(self, label, stmt):
        self.label = label  # str
        self.stmt  = stmt


class WriteStmt(Node):
    def __init__(self, args, newline=False):
        self.args    = args     # [WriteArg]
        self.newline = newline  # True → writeln


class WriteArg(Node):
    """expression with optional :width:decimals formatting."""
    def __init__(self, expr, width=None, decimals=None):
        self.expr     = expr
        self.width    = width
        self.decimals = decimals


class ReadStmt(Node):
    def __init__(self, args, newline=False):
        self.args    = args     # [variable node]
        self.newline = newline  # True → readln


class ProcCallStmt(Node):
    def __init__(self, name, args):
        self.name = name  # str
        self.args = args  # [expression node]


class BreakStmt(Node):
    pass


class ContinueStmt(Node):
    pass


class ExitStmt(Node):
    def __init__(self, value=None):
        self.value = value  # expression node or None


# ═══════════════════════════════════════════════════════════════
#  EXPRESSIONS
# ═══════════════════════════════════════════════════════════════

class BinOp(Node):
    """Binary operation.

    op is a string: '+' '-' '*' '/' 'div' 'mod' 'and' 'or' 'xor'
                    'shl' 'shr' '=' '<>' '<' '<=' '>' '>=' 'in'
    """
    def __init__(self, op, left, right):
        self.op    = op
        self.left  = left
        self.right = right

    def __repr__(self):
        return f"BinOp({self.op!r})"


class UnaryOp(Node):
    """Unary operation.  op: '-'  'not'  '@'  '^' (pointer deref)"""
    def __init__(self, op, operand):
        self.op      = op
        self.operand = operand


class Literal(Node):
    """Scalar literal value.

    kind: 'integer' | 'real' | 'string' | 'char' | 'boolean'
    """
    def __init__(self, value, kind):
        self.value = value
        self.kind  = kind

    def __repr__(self):
        return f"Literal({self.value!r}, {self.kind!r})"


class NilLiteral(Node):
    pass


class Var(Node):
    """Simple variable reference."""
    def __init__(self, name):
        self.name = name  # str

    def __repr__(self):
        return f"Var({self.name!r})"


class ArrayAccess(Node):
    def __init__(self, base, indices):
        self.base    = base     # Var | ArrayAccess | FieldAccess
        self.indices = indices  # [expression node]


class FieldAccess(Node):
    def __init__(self, base, field):
        self.base  = base   # Var | FieldAccess
        self.field = field  # str


class FuncCall(Node):
    """Function call used as an expression."""
    def __init__(self, name, args):
        self.name = name  # str
        self.args = args  # [expression node]


class SetLiteral(Node):
    def __init__(self, elements):
        # Each element is either an expression node (single value)
        # or a SetRange node.
        self.elements = elements


class SetRange(Node):
    def __init__(self, low, high):
        self.low  = low
        self.high = high


# ═══════════════════════════════════════════════════════════════
#  PRETTY PRINTER  (useful while debugging)
# ═══════════════════════════════════════════════════════════════

def pretty(node, indent=0):
    """Return a human-readable multi-line string of the AST."""
    pad = "  " * indent
    if node is None:
        return f"{pad}None"
    if isinstance(node, list):
        if not node:
            return f"{pad}[]"
        return "\n".join(pretty(n, indent) for n in node)
    if not isinstance(node, Node):
        return f"{pad}{node!r}"
    name  = type(node).__name__
    lines = [f"{pad}{name}"]
    for key, val in vars(node).items():
        if isinstance(val, list):
            lines.append(f"{pad}  {key}:")
            for item in val:
                lines.append(pretty(item, indent + 2))
        elif isinstance(val, Node):
            lines.append(f"{pad}  {key}:")
            lines.append(pretty(val, indent + 2))
        else:
            lines.append(f"{pad}  {key}: {val!r}")
    return "\n".join(lines)