import sys
import time

import lexer as pascal_lexer
from parser_pascal_ast import parser, SYNTAX_ERRORS  # noqa: F401

from ast_nodes import *

#  SYMBOL TABLE

class SymbolEntry:
    """One record in the symbol table."""
    def __init__(self, name, kind, type_name,
                 params=None, return_type=None,
                 by_ref=False, scope_level=0):
        self.name         = name        # str   – declared identifier
        self.kind         = kind        # 'variable'|'parameter'|'function'|
                                        #  'procedure'|'type'|'constant'
        self.type_name    = type_name   # str   – resolved type ('integer', …)
        self.params       = params      # [SymbolEntry] or None
        self.return_type  = return_type # str or None
        self.by_ref       = by_ref      # True for VAR parameters
        self.scope_level  = scope_level # depth at point of declaration

    def __repr__(self):
        base = f"SymbolEntry({self.kind} {self.name!r}: {self.type_name!r}"
        if self.params is not None:
            sig = ', '.join(
                ('var ' if p.by_ref else '') + p.type_name
                for p in self.params
            )
            base += f"({sig})"
        if self.return_type:
            base += f" -> {self.return_type!r}"
        base += f"  @level {self.scope_level})"
        return base


class SymbolTable:
    """
    Scoped symbol table implemented as a stack of dictionaries.

    Dragon Book §6.1 – "A symbol table is a data structure used by a compiler
    to keep track of scope and binding information about names."

    API
    ───
    enter_scope()         push a new scope frame
    exit_scope()          pop the current scope frame
    define(entry)         add SymbolEntry to current scope
    lookup(name)          search from innermost scope outward → entry or None
    lookup_current(name)  search only the current scope → entry or None
    current_level         depth of the current scope (0 = global)
    """

    def __init__(self):
        # Stack of dicts: index 0 = global, last = innermost
        self._scopes: list[dict] = [{}]
        self._preload_builtins()

    # Scope management

    def enter_scope(self):
        self._scopes.append({})

    def exit_scope(self):
        if len(self._scopes) > 1:
            self._scopes.pop()

    @property
    def current_level(self) -> int:
        return len(self._scopes) - 1

    # Symbol operations

    def define(self, entry: SymbolEntry) -> bool:
        """
        Add entry to the current scope.
        Returns False (duplicate) if the name is already in THIS scope.
        """
        scope = self._scopes[-1]
        key   = entry.name.lower()
        if key in scope:
            return False
        entry.scope_level = self.current_level
        scope[key] = entry
        return True

    def lookup(self, name: str) -> SymbolEntry | None:
        """Search from innermost scope to global. Returns None if not found."""
        key = name.lower()
        for scope in reversed(self._scopes):
            if key in scope:
                return scope[key]
        return None

    def lookup_current(self, name: str) -> SymbolEntry | None:
        """Search only the innermost (current) scope."""
        return self._scopes[-1].get(name.lower())

    # Built-in pre-loading

    def _preload_builtins(self):
        """
        Register Pascal's standard built-in routines and constants so the
        semantic analyzer does not report them as undeclared.
        """
        for name in ('write', 'writeln', 'read', 'readln'):
            self.define(SymbolEntry(name, 'procedure', 'void', params=[]))

        # Standard functions
        builtins = [
            # name          return type
            ('abs',         'number'),
            ('chr',         'char'),
            ('odd',         'boolean'),
            ('ord',         'integer'),
            ('pred',        'ordinal'),
            ('succ',        'ordinal'),
            ('round',       'integer'),
            ('trunc',       'integer'),
            ('sqr',         'real'),
            ('sqrt',        'real'),
            ('sin',         'real'),
            ('cos',         'real'),
            ('arctan',      'real'),
            ('exp',         'real'),
            ('ln',          'real'),
            ('pi',          'real'),
            ('length',      'integer'),
            ('copy',        'string'),
            ('concat',      'string'),
            ('pos',         'integer'),
            ('upcase',      'char'),
            ('lowercase',   'string'),
            ('inttostr',    'string'),
            ('strtoint',    'integer'),
            ('strtofloat',  'real'),
            ('floattostr',  'string'),
            ('high',        'ordinal'),
            ('low',         'ordinal'),
            ('sizeof',      'integer'),
            ('assigned',    'boolean'),
            ('new',         'void'),
            ('dispose',     'void'),
            ('inc',         'void'),
            ('dec',         'void'),
            ('halt',        'void'),
            ('exit',        'void'),
            ('clrscr',      'void'),
            ('gotoxy',      'void'),
            ('random',      'integer'),
            ('randomize',   'void'),
        ]
        for name, ret in builtins:
            kind = 'procedure' if ret == 'void' else 'function'
            self.define(SymbolEntry(name, kind, ret,
                                    params=[], return_type=ret))

        # Boolean constants
        self.define(SymbolEntry('true',  'constant', 'boolean'))
        self.define(SymbolEntry('false', 'constant', 'boolean'))
        self.define(SymbolEntry('nil',   'constant', 'pointer'))
        self.define(SymbolEntry('maxint','constant', 'integer'))
        self.define(SymbolEntry('result','variable', 'unknown'))  # function return

    # Debug dump

    def dump(self) -> str:
        lines = []
        for level, scope in enumerate(self._scopes):
            lines.append(f"\n  ── Nivel {level} {'(global)' if level == 0 else ''} ──")
            if not scope:
                lines.append("    (vacío)")
            for entry in scope.values():
                lines.append(f"    {entry}")
        return "\n".join(lines)


#  TYPE SYSTEM  (simple string-based compatibility rules)

# Canonical type names (all lower-case)
INTEGER_TYPES = {'integer','longint','shortint','byte','word',
                 'int64','cardinal','qword'}
REAL_TYPES    = {'real','single','double','extended','longreal'}
NUMBER_TYPES  = INTEGER_TYPES | REAL_TYPES | {'number'}
ORDINAL_TYPES = INTEGER_TYPES | {'char','boolean','ordinal'}
ALL_TYPES     = NUMBER_TYPES | {'char','string','boolean',
                                'pointer','pchar','text',
                                'ansistring','widestring','variant',
                                'void','unknown','ordinal'}

def _canon(t: str | None) -> str:
    """Return a canonical (lower-case) type name."""
    return (t or 'unknown').lower()

def types_compatible(left: str, right: str) -> bool:
    """
    Return True if right-hand side type is assignable to left-hand side.
    Follows Pascal's implicit widening rules (integer → real is OK).
    'number' and 'ordinal' are internal super-types used by built-in
    functions (abs, sqr, high, low…) that are compatible with any
    numeric or ordinal type respectively.
    """
    l, r = _canon(left), _canon(right)
    if l == r:                            return True
    if l == 'unknown' or r == 'unknown':  return True   # unresolved – skip
    if l in REAL_TYPES    and r in NUMBER_TYPES:  return True
    if l in INTEGER_TYPES and r in INTEGER_TYPES | {'number'}: return True  # number/int→integer OK
    if l == 'string'      and r in ('string','char'): return True
    if l == 'boolean'     and r == 'boolean': return True
    if l == 'pointer'     and r in ('pointer','pchar','nil'): return True
    if l == 'number'      and r in NUMBER_TYPES:  return True
    if l == 'ordinal'     and r in ORDINAL_TYPES: return True
    return False

def resolve_type_node(type_node) -> str:
    """Extract a canonical type string from a type AST node."""
    if type_node is None:
        return 'unknown'
    if isinstance(type_node, SimpleType):
        return _canon(type_node.name)
    if isinstance(type_node, StringType):
        return 'string'
    if isinstance(type_node, ArrayType):
        return 'array'
    if isinstance(type_node, RecordType):
        return 'record'
    if isinstance(type_node, PointerType):
        return 'pointer'
    if isinstance(type_node, SubrangeType):
        return 'integer'   # subranges are ordinal
    if isinstance(type_node, EnumType):
        return 'integer'
    return 'unknown'



#  SEMANTIC ANALYZER  (AST Visitor)

class SemanticAnalyzer:
    """
    Walks the AST produced by parser_pascal.py and:
      • Builds the symbol table (enter/exit scope per block/subprogram)
      • Checks every name reference is declared
      • Checks type compatibility in assignments and expressions
      • Checks function/procedure call arity
      • Reports all errors without stopping on the first one
    """

    def __init__(self, verbose=True):
        self.table          = SymbolTable()
        self.errors: list   = []
        self.warnings: list = []
        self.verbose        = verbose
        self._current_func  = None  # name of the function being compiled

    # Error / warning reporting

    def _error(self, msg: str, node=None):
        self.errors.append(msg)
        if self.verbose:
            print(f"  ERROR SEMÁNTICO: {msg}")

    def _warning(self, msg: str):
        self.warnings.append(msg)
        if self.verbose:
            print(f"  ADVERTENCIA:     {msg}")

    # Public entry point

    def analyze(self, tree: Program) -> bool:
        """
        Run semantic analysis on the AST root.
        Returns True if no errors were found.
        """
        self._visit(tree)
        return len(self.errors) == 0

    # Generic visitor dispatcher

    def _visit(self, node, expected_type: str = None) -> str:
        """
        Visit a node, return its resolved type (or 'unknown').
        expected_type is passed down for assignment / call checking.
        """
        if node is None:
            return 'unknown'
        method = '_visit_' + type(node).__name__
        visitor = getattr(self, method, self._generic_visit)
        return visitor(node) or 'unknown'

    def _generic_visit(self, node):
        if isinstance(node, list):
            for item in node:
                self._visit(item)
        return 'unknown'

    #  PROGRAM / BLOCK

    def _visit_Program(self, node: Program):
        # Register the program name itself (optional, good practice)
        self.table.define(
            SymbolEntry(node.name, 'program', 'void')
        )
        self._visit_Block(node.block)

    def _visit_Block(self, node: Block):
        # Process declarations first so forward references within the
        # same block are visible (e.g. mutually recursive procedures)
        for decl in node.decls:
            self._visit(decl)
        self._visit(node.body)

    #  DECLARATIONS

    def _visit_VarSection(self, node: VarSection):
        for decl in node.declarations:
            self._visit(decl)

    def _visit_VarDecl(self, node: VarDecl):
        type_str = resolve_type_node(node.type_node)
        for name in node.names:
            entry = SymbolEntry(name, 'variable', type_str)
            if not self.table.define(entry):
                self._error(f"Variable '{name}' ya declarada en este ámbito")

    def _visit_ConstSection(self, node: ConstSection):
        for decl in node.declarations:
            self._visit(decl)

    def _visit_ConstDecl(self, node: ConstDecl):
        val_type = self._visit(node.value)
        entry = SymbolEntry(node.name, 'constant', val_type)
        if not self.table.define(entry):
            self._error(f"Constante '{node.name}' ya declarada en este ámbito")

    def _visit_TypeSection(self, node: TypeSection):
        for decl in node.declarations:
            self._visit(decl)

    def _visit_TypeDecl(self, node: TypeDecl):
        type_str = resolve_type_node(node.type_def)
        entry = SymbolEntry(node.name, 'type', type_str)
        if not self.table.define(entry):
            self._error(f"Tipo '{node.name}' ya declarado en este ámbito")

    def _visit_LabelSection(self, node: LabelSection):
        for lbl in node.labels:
            self.table.define(SymbolEntry(lbl, 'label', 'void'))

    # Subprograms

    def _visit_ProcDecl(self, node: ProcDecl):
        param_entries = self._build_param_entries(node.params)

        existing = self.table.lookup_current(node.name)
        if existing and getattr(existing, 'is_forward', False):
            # This is the implementation of a FORWARD-declared procedure — OK
            existing.is_forward = False
        else:
            entry = SymbolEntry(node.name, 'procedure', 'void',
                                params=param_entries)
            entry.is_forward = (node.body == 'forward')
            if not self.table.define(entry):
                self._error(
                    f"Procedimiento '{node.name}' ya declarado en este ámbito")

        if node.body == 'forward':
            return

        prev_func          = self._current_func
        self._current_func = node.name
        self.table.enter_scope()

        for pe in param_entries:
            if not self.table.define(pe):
                self._error(f"Parámetro duplicado '{pe.name}' en '{node.name}'")

        if isinstance(node.body, Block):
            self._visit_Block(node.body)

        self.table.exit_scope()
        self._current_func = prev_func

    def _visit_FuncDecl(self, node: FuncDecl):
        ret_type      = resolve_type_node(node.return_type)
        param_entries = self._build_param_entries(node.params)

        existing = self.table.lookup_current(node.name)
        if existing and getattr(existing, 'is_forward', False):
            # This is the implementation of a FORWARD-declared function — OK
            existing.is_forward = False
        else:
            entry = SymbolEntry(node.name, 'function', ret_type,
                                params=param_entries, return_type=ret_type)
            entry.is_forward = (node.body == 'forward')
            if not self.table.define(entry):
                self._error(
                    f"Función '{node.name}' ya declarada en este ámbito")

        if node.body == 'forward':
            return

        prev_func          = self._current_func
        self._current_func = node.name
        self.table.enter_scope()

        for pe in param_entries:
            if not self.table.define(pe):
                self._error(f"Parámetro duplicado '{pe.name}' en '{node.name}'")

        # 'Result' is Pascal's implicit return variable
        self.table.define(
            SymbolEntry('result', 'variable', ret_type,
                        scope_level=self.table.current_level)
        )

        if isinstance(node.body, Block):
            self._visit_Block(node.body)

        self.table.exit_scope()
        self._current_func = prev_func

    def _build_param_entries(self, param_groups: list) -> list:
        entries = []
        for group in param_groups:
            t = resolve_type_node(group.type_node)
            for name in group.names:
                entries.append(
                    SymbolEntry(name, 'parameter', t, by_ref=group.by_ref)
                )
        return entries

    #  STATEMENTS

    def _visit_CompoundStmt(self, node: CompoundStmt):
        for stmt in node.stmts:
            self._visit(stmt)

    def _visit_AssignStmt(self, node: AssignStmt):
        target_type = self._visit(node.target)
        value_type  = self._visit(node.value)

        # Special case: assigning to Result inside a function
        if (isinstance(node.target, Var) and
                node.target.name.lower() == 'result' and
                self._current_func):
            func_entry = self.table.lookup(self._current_func)
            if func_entry and func_entry.return_type:
                target_type = func_entry.return_type

        if (target_type != 'unknown' and value_type != 'unknown'
                and not types_compatible(target_type, value_type)):
            self._error(
                f"Tipo incompatible en asignación: "
                f"no se puede asignar '{value_type}' a '{target_type}'"
            )

    def _visit_IfStmt(self, node: IfStmt):
        cond_type = self._visit(node.condition)
        if cond_type not in ('boolean', 'unknown'):
            self._error(
                f"La condición del IF debe ser boolean, "
                f"se obtuvo '{cond_type}'"
            )
        self._visit(node.then_branch)
        if node.else_branch:
            self._visit(node.else_branch)

    def _visit_WhileStmt(self, node: WhileStmt):
        cond_type = self._visit(node.condition)
        if cond_type not in ('boolean', 'unknown'):
            self._error(
                f"La condición del WHILE debe ser boolean, "
                f"se obtuvo '{cond_type}'"
            )
        self._visit(node.body)

    def _visit_ForStmt(self, node: ForStmt):
        # Control variable must be declared and ordinal
        var_entry = self.table.lookup(node.var)
        if var_entry is None:
            self._error(f"Variable de control '{node.var}' no declarada")
        elif var_entry.type_name not in ORDINAL_TYPES | {'unknown'}:
            self._error(
                f"Variable de control '{node.var}' debe ser de tipo ordinal, "
                f"es '{var_entry.type_name}'"
            )
        self._visit(node.start)
        self._visit(node.stop)
        self._visit(node.body)

    def _visit_RepeatStmt(self, node: RepeatStmt):
        for stmt in node.body:
            self._visit(stmt)
        cond_type = self._visit(node.condition)
        if cond_type not in ('boolean', 'unknown'):
            self._error(
                f"La condición del REPEAT..UNTIL debe ser boolean, "
                f"se obtuvo '{cond_type}'"
            )

    def _visit_CaseStmt(self, node: CaseStmt):
        self._visit(node.expr)
        for arm in node.arms:
            self._visit(arm)
        if node.otherwise:
            self._visit(node.otherwise)

    def _visit_CaseArm(self, node: CaseArm):
        self._visit(node.stmt)

    def _visit_WithStmt(self, node: WithStmt):
        for var in node.variables:
            self._visit(var)
        self._visit(node.body)

    def _visit_GotoStmt(self, node: GotoStmt):
        if self.table.lookup(node.label) is None:
            self._error(f"Etiqueta '{node.label}' no declarada")

    def _visit_LabeledStmt(self, node: LabeledStmt):
        self._visit(node.stmt)

    def _visit_WriteStmt(self, node: WriteStmt):
        for arg in node.args:
            self._visit(arg)

    def _visit_ReadStmt(self, node: ReadStmt):
        for arg in node.args:
            if isinstance(arg, Var):
                if self.table.lookup(arg.name) is None:
                    self._error(f"Variable no declarada: '{arg.name}'")

    def _visit_ProcCallStmt(self, node: ProcCallStmt):
        entry = self.table.lookup(node.name)
        if entry is None:
            self._error(f"Procedimiento o función no declarada: '{node.name}'")
            return
        if entry.kind not in ('procedure', 'function', 'program'):
            self._error(f"'{node.name}' no es un procedimiento")
            return
        self._check_call_args(node.name, entry, node.args)

    def _visit_BreakStmt(self, node):    pass
    def _visit_ContinueStmt(self, node): pass
    def _visit_ExitStmt(self, node: ExitStmt):
        if node.value:
            self._visit(node.value)

    #  EXPRESSIONS

    def _visit_Literal(self, node: Literal) -> str:
        return node.kind   # already 'integer'|'real'|'string'|'char'|'boolean'

    def _visit_NilLiteral(self, node) -> str:
        return 'pointer'

    def _visit_Var(self, node: Var) -> str:
        entry = self.table.lookup(node.name)
        if entry is None:
            self._error(f"Variable no declarada: '{node.name}'")
            return 'unknown'
        return entry.type_name

    def _visit_BinOp(self, node: BinOp) -> str:
        lt = self._visit(node.left)
        rt = self._visit(node.right)
        op = node.op

        # Relational operators always produce boolean
        if op in ('=', '<>', '<', '<=', '>', '>=', 'in'):
            return 'boolean'

        # Logical operators require boolean operands
        if op in ('and', 'or', 'xor'):
            if lt not in ('boolean', 'unknown'):
                self._error(
                    f"Operando izquierdo de '{op}' debe ser boolean, "
                    f"se obtuvo '{lt}'"
                )
            if rt not in ('boolean', 'unknown'):
                self._error(
                    f"Operando derecho de '{op}' debe ser boolean, "
                    f"se obtuvo '{rt}'"
                )
            return 'boolean'

        # Arithmetic operators
        if op in ('+', '-', '*'):
            if lt in REAL_TYPES or rt in REAL_TYPES:
                return 'real'
            if lt in NUMBER_TYPES and rt in NUMBER_TYPES:
                return 'integer'
            if op == '+' and 'string' in (lt, rt):
                return 'string'   # string concatenation

        if op == '/':
            return 'real'         # real division always returns real

        if op in ('div', 'mod', 'shl', 'shr'):
            if lt not in INTEGER_TYPES | {'unknown'}:
                self._error(
                    f"Operador '{op}' requiere enteros, "
                    f"operando izquierdo es '{lt}'"
                )
            if rt not in INTEGER_TYPES | {'unknown'}:
                self._error(
                    f"Operador '{op}' requiere enteros, "
                    f"operando derecho es '{rt}'"
                )
            return 'integer'

        return 'unknown'

    def _visit_UnaryOp(self, node: UnaryOp) -> str:
        t = self._visit(node.operand)
        if node.op == '-':
            if t not in NUMBER_TYPES | {'unknown'}:
                self._error(f"Operador unario '-' requiere número, se obtuvo '{t}'")
            return t
        if node.op == 'not':
            if t not in ('boolean', 'unknown'):
                self._error(f"Operador 'not' requiere boolean, se obtuvo '{t}'")
            return 'boolean'
        if node.op == '@':
            return 'pointer'
        if node.op == '^':
            return 'unknown'   # pointer dereference – base type unknown here
        return 'unknown'

    def _visit_FuncCall(self, node: FuncCall) -> str:
        entry = self.table.lookup(node.name)
        if entry is None:
            self._error(f"Función no declarada: '{node.name}'")
            return 'unknown'
        if entry.kind not in ('function', 'procedure', 'program'):
            self._error(f"'{node.name}' no es una función")
            return 'unknown'
        self._check_call_args(node.name, entry, node.args)
        return entry.return_type or 'unknown'

    def _visit_ArrayAccess(self, node: ArrayAccess) -> str:
        base_type = self._visit(node.base)
        for idx in node.indices:
            idx_type = self._visit(idx)
            if idx_type not in ORDINAL_TYPES | {'unknown'}:
                self._error(
                    f"El índice de arreglo debe ser de tipo ordinal, "
                    f"se obtuvo '{idx_type}'"
                )
        # We return 'unknown' because element type needs full type resolution
        return 'unknown'

    def _visit_FieldAccess(self, node: FieldAccess) -> str:
        self._visit(node.base)
        return 'unknown'   # full record type tracking is left for later phases

    def _visit_SetLiteral(self, node: SetLiteral) -> str:
        for elem in node.elements:
            self._visit(elem)
        return 'set'

    def _visit_SetRange(self, node: SetRange) -> str:
        self._visit(node.low)
        self._visit(node.high)
        return 'set'

    def _visit_WriteArg(self, node: WriteArg) -> str:
        return self._visit(node.expr)

    # Call arity check

    def _check_call_args(self, name: str, entry: SymbolEntry, args: list):
        """
        Check the number of arguments against the declared parameter count.
        If params=[] it means "variadic / built-in" – skip the check.
        """
        if not entry.params:   # variadic built-in or no declared params
            return
        n_params = len(entry.params)
        n_args   = len(args)
        if n_args != n_params:
            self._error(
                f"'{name}' espera {n_params} argumento(s), "
                f"se proporcionaron {n_args}"
            )
        # Check individual argument types where possible
        for i, (param, arg) in enumerate(zip(entry.params, args)):
            arg_type = self._visit(arg)
            if not types_compatible(param.type_name, arg_type):
                self._error(
                    f"Argumento {i+1} de '{name}': "
                    f"se esperaba '{param.type_name}', "
                    f"se obtuvo '{arg_type}'"
                )


# PRINT SYMBOL TABLE

def print_symbol_table(table: SymbolTable):
    print("\n" + "═" * 52)
    print("  TABLA DE SÍMBOLOS")
    print("═" * 52)

    headers = ["Nombre", "Clase", "Tipo", "Nivel"]
    rows    = []

    for level, scope in enumerate(table._scopes):
        for entry in scope.values():
            sig = entry.name
            if entry.params is not None and entry.kind in ('function','procedure'):
                param_str = ', '.join(
                    ('var ' if p.by_ref else '') + f"{p.name}:{p.type_name}"
                    for p in entry.params
                )
                sig += f"({param_str})"
            ret = f" → {entry.return_type}" if entry.return_type else ""
            rows.append([sig + ret, entry.kind, entry.type_name, str(level)])

    col_w = [max(len(h), max((len(r[i]) for r in rows), default=0))
             for i, h in enumerate(headers)]

    def fmt(row):
        return "  " + "  ".join(cell.ljust(col_w[i])
                                 for i, cell in enumerate(row))

    sep = "  " + "  ".join("-" * w for w in col_w)
    print(fmt(headers))
    print(sep)
    for row in rows:
        print(fmt(row))
    print()


#  STANDALONE ENTRY POINT

if __name__ == '__main__':
    fin = sys.argv[1] if len(sys.argv) > 1 else 'programa.pas'

    pascal_lexer.reset_lexer_state()
    with open(fin, 'r', encoding='utf-8') as f:
        source = f.read()

    ast = parser.parse(source, lexer=pascal_lexer.lexer)

    lex_errors    = pascal_lexer.LEXICAL_ERRORS
    syntax_errors = SYNTAX_ERRORS

    if lex_errors + syntax_errors > 0:
        print(f"\nAnálisis semántico omitido "
              f"({lex_errors} léxicos, {syntax_errors} sintácticos).\n")
        sys.exit(1)

    print("\n" + "═" * 52)
    print("  ANÁLISIS SEMÁNTICO")
    print("═" * 52)

    t0       = time.perf_counter()
    analyzer = SemanticAnalyzer(verbose=True)
    ok       = analyzer.analyze(ast)
    elapsed  = time.perf_counter() - t0

    print_symbol_table(analyzer.table)

    print("═" * 52)
    print(f"  Tiempo            : {elapsed:.6f} s")
    print(f"  Errores semánticos: {len(analyzer.errors)}")
    print(f"  Advertencias      : {len(analyzer.warnings)}")
    print("═" * 52)
    print("  Análisis semántico OK ✓" if ok else
          "  Análisis semántico FALLIDO ✗")
    print()