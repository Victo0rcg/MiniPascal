import ply.yacc as yacc
from lexer import tokens
import lexer as pascal_lexer
from ast_nodes import (
    Program, Block, LabelSection, ConstSection, ConstDecl,
    TypeSection, TypeDecl, VarSection, VarDecl,
    SimpleType, StringType, ArrayType, RecordType, FieldDecl,
    PointerType, SubrangeType, EnumType,
    ProcDecl, FuncDecl, ParamGroup,
    CompoundStmt, AssignStmt, IfStmt, WhileStmt, ForStmt,
    RepeatStmt, CaseStmt, CaseArm, WithStmt,
    GotoStmt, LabeledStmt,
    WriteStmt, WriteArg, ReadStmt, ProcCallStmt,
    BreakStmt, ContinueStmt, ExitStmt,
    BinOp, UnaryOp, Literal, NilLiteral,
    Var, ArrayAccess, FieldAccess, FuncCall,
    SetLiteral, SetRange,
    pretty,
)
import sys
from pathlib import Path
import time

VERBOSE       = True
SYNTAX_ERRORS = 0

#  PROGRAMA PRINCIPAL

def p_program(p):
    'program : PROGRAM ID SEMICOLON uses_section block DOT'
    p[0] = Program(name=p[2], uses=p[4], block=p[5])

# Cláusula USES

def p_uses_section_present(p):
    'uses_section : USES uses_id_list SEMICOLON'
    p[0] = p[2]                         # [str]

def p_uses_section_empty(p):
    'uses_section : empty'
    p[0] = []

def p_uses_id_list_multi(p):
    'uses_id_list : uses_id_list COMMA ID'
    p[0] = p[1] + [p[3]]

def p_uses_id_list_single(p):
    'uses_id_list : ID'
    p[0] = [p[1]]

#  BLOQUE PRINCIPAL

def p_block(p):
    'block : block_decl_list compound_stmt'
    p[0] = Block(decls=p[1], body=p[2])

def p_block_decl_list_many(p):
    'block_decl_list : block_decl_list block_decl'
    p[0] = p[1] + [p[2]]

def p_block_decl_list_empty(p):
    'block_decl_list : empty'
    p[0] = []

def p_block_decl_label(p):
    'block_decl : label_section'
    p[0] = p[1]

def p_block_decl_const(p):
    'block_decl : const_section'
    p[0] = p[1]

def p_block_decl_type(p):
    'block_decl : type_section'
    p[0] = p[1]

def p_block_decl_var(p):
    'block_decl : var_section'
    p[0] = p[1]

def p_block_decl_subprog(p):
    'block_decl : subprogram_declaration'
    p[0] = p[1]

# Bloque de subprograma: mismo esquema que block
def p_subprogram_block(p):
    'subprogram_block : block_decl_list compound_stmt'
    p[0] = Block(decls=p[1], body=p[2])

# Cláusula LABEL

def p_label_section(p):
    'label_section : LABEL label_id_list SEMICOLON'
    p[0] = LabelSection(labels=p[2])

def p_label_id_list_multi(p):
    'label_id_list : label_id_list COMMA ID'
    p[0] = p[1] + [p[3]]

def p_label_id_list_single(p):
    'label_id_list : ID'
    p[0] = [p[1]]

#  SECCIÓN DE CONSTANTES

def p_const_section(p):
    'const_section : CONST const_declaration_list'
    p[0] = ConstSection(declarations=p[2])

def p_const_declaration_list_many(p):
    'const_declaration_list : const_declaration_list const_declaration'
    p[0] = p[1] + [p[2]]

def p_const_declaration_list_one(p):
    'const_declaration_list : const_declaration'
    p[0] = [p[1]]

def p_const_declaration(p):
    'const_declaration : ID EQ const_expr SEMICOLON'
    p[0] = ConstDecl(name=p[1], value=p[3])

def p_const_expr_literal(p):
    'const_expr : literal'
    p[0] = p[1]

def p_const_expr_neg(p):
    'const_expr : MINUS literal'
    p[0] = UnaryOp(op='-', operand=p[2])

def p_const_expr_pos(p):
    'const_expr : PLUS literal'
    p[0] = p[2]                         # unary + is a no-op

def p_const_expr_id(p):
    'const_expr : ID'
    p[0] = Var(name=p[1])

#  SECCIÓN DE TIPOS

def p_type_section(p):
    'type_section : TYPE type_declaration_list'
    p[0] = TypeSection(declarations=p[2])

def p_type_declaration_list_many(p):
    'type_declaration_list : type_declaration_list type_declaration'
    p[0] = p[1] + [p[2]]

def p_type_declaration_list_one(p):
    'type_declaration_list : type_declaration'
    p[0] = [p[1]]

def p_type_declaration(p):
    'type_declaration : ID EQ type_def SEMICOLON'
    p[0] = TypeDecl(name=p[1], type_def=p[3])

# Definiciones de tipo 

def p_type_def_simple(p):
    'type_def : type_specifier'
    p[0] = p[1]

def p_type_def_array(p):
    'type_def : ARRAY LBRACKET range_list RBRACKET OF type_def'
    p[0] = ArrayType(ranges=p[3], element_type=p[6])

def p_type_def_record(p):
    'type_def : RECORD field_list END'
    p[0] = RecordType(fields=p[2])

def p_type_def_record_empty(p):
    'type_def : RECORD END'
    p[0] = RecordType(fields=[])

def p_type_def_pointer_id(p):
    'type_def : CARET ID'
    p[0] = PointerType(base_type=p[2])

def p_type_def_pointer_builtin(p):
    '''type_def : CARET INTEGER_TYPE
                | CARET REAL_TYPE
                | CARET BOOLEAN_TYPE
                | CARET CHAR_TYPE
                | CARET STRING_TYPE
                | CARET LONGINT_TYPE
                | CARET SHORTINT_TYPE
                | CARET BYTE_TYPE
                | CARET WORD_TYPE
                | CARET INT64_TYPE
                | CARET SINGLE_TYPE
                | CARET DOUBLE_TYPE
                | CARET EXTENDED_TYPE
                | CARET LONGREAL_TYPE
                | CARET TEXT_TYPE
                | CARET CARDINAL_TYPE
                | CARET QWORD_TYPE'''
    # p[2] is the token type string (e.g. 'INTEGER_TYPE'); lower for uniformity
    p[0] = PointerType(base_type=p[2].lower().replace('_type', ''))

def p_type_def_enum(p):
    'type_def : LPAREN id_list RPAREN'
    p[0] = EnumType(names=p[2])

def p_type_def_subrange(p):
    'type_def : const_expr DOTDOT const_expr'
    p[0] = SubrangeType(low=p[1], high=p[3])

# Rangos de array

def p_range_list_multi(p):
    'range_list : range_list COMMA range'
    p[0] = p[1] + [p[3]]

def p_range_list_single(p):
    'range_list : range'
    p[0] = [p[1]]

def p_range(p):
    'range : const_expr DOTDOT const_expr'
    p[0] = (p[1], p[3])                 # tuple (low, high)

# Campos de record

def p_field_list_many(p):
    'field_list : field_list field_declaration'
    p[0] = p[1] + [p[2]]

def p_field_list_one(p):
    'field_list : field_declaration'
    p[0] = [p[1]]

def p_field_declaration(p):
    'field_declaration : id_list COLON type_def SEMICOLON'
    p[0] = FieldDecl(names=p[1], type_node=p[3])

# Especificadores de tipo

def p_type_specifier_integer(p):    'type_specifier : INTEGER_TYPE'   ; p[0] = SimpleType('integer')
def p_type_specifier_real(p):       'type_specifier : REAL_TYPE'      ; p[0] = SimpleType('real')
def p_type_specifier_boolean(p):    'type_specifier : BOOLEAN_TYPE'   ; p[0] = SimpleType('boolean')
def p_type_specifier_char(p):       'type_specifier : CHAR_TYPE'      ; p[0] = SimpleType('char')
def p_type_specifier_string(p):     'type_specifier : STRING_TYPE'    ; p[0] = SimpleType('string')
def p_type_specifier_longint(p):    'type_specifier : LONGINT_TYPE'   ; p[0] = SimpleType('longint')
def p_type_specifier_shortint(p):   'type_specifier : SHORTINT_TYPE'  ; p[0] = SimpleType('shortint')
def p_type_specifier_byte(p):       'type_specifier : BYTE_TYPE'      ; p[0] = SimpleType('byte')
def p_type_specifier_word(p):       'type_specifier : WORD_TYPE'      ; p[0] = SimpleType('word')
def p_type_specifier_int64(p):      'type_specifier : INT64_TYPE'     ; p[0] = SimpleType('int64')
def p_type_specifier_single(p):     'type_specifier : SINGLE_TYPE'    ; p[0] = SimpleType('single')
def p_type_specifier_double(p):     'type_specifier : DOUBLE_TYPE'    ; p[0] = SimpleType('double')
def p_type_specifier_extended(p):   'type_specifier : EXTENDED_TYPE'  ; p[0] = SimpleType('extended')
def p_type_specifier_longreal(p):   'type_specifier : LONGREAL_TYPE'  ; p[0] = SimpleType('longreal')
def p_type_specifier_text(p):       'type_specifier : TEXT_TYPE'      ; p[0] = SimpleType('text')
def p_type_specifier_cardinal(p):   'type_specifier : CARDINAL_TYPE'  ; p[0] = SimpleType('cardinal')
def p_type_specifier_qword(p):      'type_specifier : QWORD_TYPE'     ; p[0] = SimpleType('qword')
def p_type_specifier_pointer(p):    'type_specifier : POINTER_TYPE'   ; p[0] = SimpleType('pointer')
def p_type_specifier_pchar(p):      'type_specifier : PCHAR_TYPE'     ; p[0] = SimpleType('pchar')
def p_type_specifier_ansistring(p): 'type_specifier : ANSISTRING_TYPE'; p[0] = SimpleType('ansistring')
def p_type_specifier_widestring(p): 'type_specifier : WIDESTRING_TYPE'; p[0] = SimpleType('widestring')
def p_type_specifier_variant(p):    'type_specifier : VARIANT_TYPE'   ; p[0] = SimpleType('variant')

def p_type_specifier_string_n(p):
    'type_specifier : STRING_TYPE LBRACKET INTEGER RBRACKET'
    p[0] = StringType(size=p[3])

def p_type_specifier_id(p):
    'type_specifier : ID'
    p[0] = SimpleType(p[1])             # user-defined type name

#  SECCIÓN DE VARIABLES

def p_var_section(p):
    'var_section : VAR var_declaration_list'
    p[0] = VarSection(declarations=p[2])

def p_var_declaration_list_many(p):
    'var_declaration_list : var_declaration_list var_declaration'
    p[0] = p[1] + [p[2]]

def p_var_declaration_list_one(p):
    'var_declaration_list : var_declaration'
    p[0] = [p[1]]

def p_var_declaration(p):
    'var_declaration : id_list COLON type_def SEMICOLON'
    p[0] = VarDecl(names=p[1], type_node=p[3])

# Lista de identificadores 

def p_id_list_multi(p):
    'id_list : id_list COMMA ID'
    p[0] = p[1] + [p[3]]

def p_id_list_single(p):
    'id_list : ID'
    p[0] = [p[1]]

#  SUBPROGRAMAS

def p_subprogram_declaration_proc(p):
    'subprogram_declaration : procedure_declaration'
    p[0] = p[1]

def p_subprogram_declaration_func(p):
    'subprogram_declaration : function_declaration'
    p[0] = p[1]

# Procedimientos

def p_procedure_declaration_params(p):
    'procedure_declaration : PROCEDURE ID LPAREN param_list RPAREN SEMICOLON proc_body SEMICOLON'
    p[0] = ProcDecl(name=p[2], params=p[4], body=p[7])

def p_procedure_declaration_no_params(p):
    'procedure_declaration : PROCEDURE ID SEMICOLON proc_body SEMICOLON'
    p[0] = ProcDecl(name=p[2], params=[], body=p[4])

def p_proc_body_block(p):
    'proc_body : subprogram_block'
    p[0] = p[1]

def p_proc_body_forward(p):
    'proc_body : FORWARD'
    p[0] = 'forward'

# Funciones

def p_function_declaration_params(p):
    'function_declaration : FUNCTION ID LPAREN param_list RPAREN COLON type_specifier SEMICOLON func_body SEMICOLON'
    p[0] = FuncDecl(name=p[2], params=p[4], return_type=p[7], body=p[9])

def p_function_declaration_no_params(p):
    'function_declaration : FUNCTION ID COLON type_specifier SEMICOLON func_body SEMICOLON'
    p[0] = FuncDecl(name=p[2], params=[], return_type=p[4], body=p[6])

def p_func_body_block(p):
    'func_body : subprogram_block'
    p[0] = p[1]

def p_func_body_forward(p):
    'func_body : FORWARD'
    p[0] = 'forward'

# Lista de parámetros

def p_param_list_multi(p):
    'param_list : param_list SEMICOLON param_group'
    p[0] = p[1] + [p[3]]

def p_param_list_single(p):
    'param_list : param_group'
    p[0] = [p[1]]

def p_param_list_empty(p):
    'param_list : empty'
    p[0] = []

def p_param_group_plain(p):
    'param_group : id_list COLON type_specifier'
    p[0] = ParamGroup(names=p[1], type_node=p[3])

def p_param_group_var(p):
    'param_group : VAR id_list COLON type_specifier'
    p[0] = ParamGroup(names=p[2], type_node=p[4], by_ref=True)

def p_param_group_const(p):
    'param_group : CONST id_list COLON type_specifier'
    p[0] = ParamGroup(names=p[2], type_node=p[4], is_const=True)

#  SENTENCIAS

def p_compound_stmt(p):
    'compound_stmt : BEGIN statement_list END'
    p[0] = CompoundStmt(stmts=p[2])

# Lista de sentencias separadas por ';'
def p_statement_list_multi(p):
    'statement_list : statement_list SEMICOLON statement'
    p[0] = p[1] + ([p[3]] if p[3] is not None else [])

def p_statement_list_single(p):
    'statement_list : statement'
    p[0] = [p[1]] if p[1] is not None else []

# Recuperación de errores: ';' faltante entre sentencias
def p_statement_list_missing_semi(p):
    'statement_list : statement_list error statement'
    global SYNTAX_ERRORS
    SYNTAX_ERRORS += 1
    line = pascal_lexer.lexer.lineno
    if VERBOSE:
        print(f"ERROR SINTÁCTICO [línea {line}]: falta ';' entre sentencias")
    p[0] = p[1] + ([p[3]] if p[3] is not None else [])

def p_statement(p):
    '''statement : assignment_stmt
                 | compound_stmt
                 | if_stmt
                 | while_stmt
                 | for_stmt
                 | repeat_stmt
                 | case_stmt
                 | with_stmt
                 | goto_stmt
                 | labeled_stmt
                 | write_stmt
                 | writeln_stmt
                 | read_stmt
                 | readln_stmt
                 | break_stmt
                 | continue_stmt
                 | exit_stmt
                 | call_stmt
                 | empty
    '''
    p[0] = p[1]                         # pass the node (or None) upward

# Asignación

def p_assignment_stmt(p):
    'assignment_stmt : variable ASSIGN expression'
    p[0] = AssignStmt(target=p[1], value=p[3])

# IF 

def p_if_stmt_else(p):
    'if_stmt : IF expression THEN statement ELSE statement'
    p[0] = IfStmt(condition=p[2], then_branch=p[4], else_branch=p[6])

def p_if_stmt_simple(p):
    'if_stmt : IF expression THEN statement'
    p[0] = IfStmt(condition=p[2], then_branch=p[4])

# WHILE

def p_while_stmt(p):
    'while_stmt : WHILE expression DO statement'
    p[0] = WhileStmt(condition=p[2], body=p[4])

# FOR 

def p_for_stmt_to(p):
    'for_stmt : FOR ID ASSIGN expression TO expression DO statement'
    p[0] = ForStmt(var=p[2], start=p[4], stop=p[6], downto=False, body=p[8])

def p_for_stmt_downto(p):
    'for_stmt : FOR ID ASSIGN expression DOWNTO expression DO statement'
    p[0] = ForStmt(var=p[2], start=p[4], stop=p[6], downto=True, body=p[8])

# REPEAT UNTIL 

def p_repeat_stmt(p):
    'repeat_stmt : REPEAT statement_list UNTIL expression'
    p[0] = RepeatStmt(body=p[2], condition=p[4])

# CASE 

def p_case_stmt(p):
    'case_stmt : CASE expression OF case_list END'
    p[0] = CaseStmt(expr=p[2], arms=p[4])

def p_case_stmt_otherwise(p):
    'case_stmt : CASE expression OF case_list OTHERWISE statement SEMICOLON END'
    p[0] = CaseStmt(expr=p[2], arms=p[4], otherwise=p[6])

def p_case_stmt_else(p):
    'case_stmt : CASE expression OF case_list ELSE statement SEMICOLON END'
    p[0] = CaseStmt(expr=p[2], arms=p[4], otherwise=p[6])

def p_case_list_many(p):
    'case_list : case_list case_element'
    p[0] = p[1] + [p[2]]

def p_case_list_one(p):
    'case_list : case_element'
    p[0] = [p[1]]

def p_case_element(p):
    'case_element : case_label_list COLON statement SEMICOLON'
    p[0] = CaseArm(labels=p[1], stmt=p[3])

def p_case_label_list_multi(p):
    'case_label_list : case_label_list COMMA case_label'
    p[0] = p[1] + [p[3]]

def p_case_label_list_single(p):
    'case_label_list : case_label'
    p[0] = [p[1]]

def p_case_label_single(p):
    'case_label : const_expr'
    p[0] = p[1]

def p_case_label_range(p):
    'case_label : const_expr DOTDOT const_expr'
    p[0] = (p[1], p[3])                 # tuple signals a range

# WITH 

def p_with_stmt(p):
    'with_stmt : WITH variable_list DO statement'
    p[0] = WithStmt(variables=p[2], body=p[4])

# GOTO / etiqueta 

def p_goto_stmt(p):
    'goto_stmt : GOTO ID'
    p[0] = GotoStmt(label=p[2])

def p_labeled_stmt(p):
    'labeled_stmt : ID COLON statement'
    p[0] = LabeledStmt(label=p[1], stmt=p[3])

# WRITE / WRITELN 

def p_write_stmt_args(p):
    'write_stmt : WRITE LPAREN arg_list RPAREN'
    p[0] = WriteStmt(args=p[3], newline=False)

def p_write_stmt_no_args(p):
    'write_stmt : WRITE LPAREN RPAREN'
    p[0] = WriteStmt(args=[], newline=False)

def p_writeln_stmt_args(p):
    'writeln_stmt : WRITELN LPAREN arg_list RPAREN'
    p[0] = WriteStmt(args=p[3], newline=True)

def p_writeln_stmt_no_args_paren(p):
    'writeln_stmt : WRITELN LPAREN RPAREN'
    p[0] = WriteStmt(args=[], newline=True)

def p_writeln_stmt_no_args(p):
    'writeln_stmt : WRITELN'
    p[0] = WriteStmt(args=[], newline=True)

# READ / READLN 

def p_read_stmt_args(p):
    'read_stmt : READ LPAREN variable_list RPAREN'
    p[0] = ReadStmt(args=p[3], newline=False)

def p_read_stmt_no_args(p):
    'read_stmt : READ LPAREN RPAREN'
    p[0] = ReadStmt(args=[], newline=False)

def p_readln_stmt_args(p):
    'readln_stmt : READLN LPAREN variable_list RPAREN'
    p[0] = ReadStmt(args=p[3], newline=True)

def p_readln_stmt_no_args_paren(p):
    'readln_stmt : READLN LPAREN RPAREN'
    p[0] = ReadStmt(args=[], newline=True)

def p_readln_stmt_no_args(p):
    'readln_stmt : READLN'
    p[0] = ReadStmt(args=[], newline=True)

# BREAK / CONTINUE / EXIT 

def p_break_stmt(p):
    'break_stmt : BREAK'
    p[0] = BreakStmt()

def p_continue_stmt(p):
    'continue_stmt : CONTINUE'
    p[0] = ContinueStmt()

def p_exit_stmt_no_args(p):
    'exit_stmt : EXIT'
    p[0] = ExitStmt()

def p_exit_stmt_args(p):
    'exit_stmt : EXIT LPAREN expression RPAREN'
    p[0] = ExitStmt(value=p[3])

# Llamada a procedimiento 

def p_call_stmt_with_args(p):
    'call_stmt : ID LPAREN func_arg_list RPAREN'
    p[0] = ProcCallStmt(name=p[1], args=p[3])

def p_call_stmt_no_args(p):
    'call_stmt : ID LPAREN RPAREN'
    p[0] = ProcCallStmt(name=p[1], args=[])

# Sin paréntesis: clrscr; halt; etc.
def p_call_stmt_bare(p):
    'call_stmt : ID'
    p[0] = ProcCallStmt(name=p[1], args=[])

# Listas de variables / argumentos 

def p_variable_list_multi(p):
    'variable_list : variable_list COMMA variable'
    p[0] = p[1] + [p[3]]

def p_variable_list_single(p):
    'variable_list : variable'
    p[0] = [p[1]]

# arg_list: exclusivo para write/writeln (soporta expr:ancho:decimales) ──

def p_arg_list_multi(p):
    'arg_list : arg_list COMMA arg_item'
    p[0] = p[1] + [p[3]]

def p_arg_list_single(p):
    'arg_list : arg_item'
    p[0] = [p[1]]

# Argumento con formato opcional  expr:ancho  o  expr:ancho:decimales
def p_arg_item_plain(p):
    'arg_item : expression'
    p[0] = WriteArg(expr=p[1])

def p_arg_item_width(p):
    'arg_item : expression COLON expression'
    p[0] = WriteArg(expr=p[1], width=p[3])

def p_arg_item_width_dec(p):
    'arg_item : expression COLON expression COLON expression'
    p[0] = WriteArg(expr=p[1], width=p[3], decimals=p[5])

# func_arg_list: para llamadas a función/procedimiento (expresiones puras) ─
# Separado de arg_list para que FuncCall.args nunca contenga WriteArg.

def p_func_arg_list_multi(p):
    'func_arg_list : func_arg_list COMMA expression'
    p[0] = p[1] + [p[3]]

def p_func_arg_list_single(p):
    'func_arg_list : expression'
    p[0] = [p[1]]

def p_func_arg_list_empty(p):
    'func_arg_list : empty'
    p[0] = []

#  EXPRESIONES

def p_expression_relop(p):
    'expression : simple_expression relop simple_expression'
    p[0] = BinOp(op=p[2], left=p[1], right=p[3])

def p_expression_in(p):
    'expression : simple_expression IN set_literal'
    p[0] = BinOp(op='in', left=p[1], right=p[3])

def p_expression_simple(p):
    'expression : simple_expression'
    p[0] = p[1]

# Operadores relacionales (devuelven string)

def p_relop_eq(p):  'relop : EQ'  ; p[0] = '='
def p_relop_neq(p): 'relop : NEQ' ; p[0] = '<>'
def p_relop_lt(p):  'relop : LT'  ; p[0] = '<'
def p_relop_le(p):  'relop : LE'  ; p[0] = '<='
def p_relop_gt(p):  'relop : GT'  ; p[0] = '>'
def p_relop_ge(p):  'relop : GE'  ; p[0] = '>='

# Expresión simple

def p_simple_expression_addop(p):
    'simple_expression : simple_expression addop term'
    p[0] = BinOp(op=p[2], left=p[1], right=p[3])

def p_simple_expression_or(p):
    'simple_expression : simple_expression OR term'
    p[0] = BinOp(op='or', left=p[1], right=p[3])

def p_simple_expression_xor(p):
    'simple_expression : simple_expression XOR term'
    p[0] = BinOp(op='xor', left=p[1], right=p[3])

def p_simple_expression_term(p):
    'simple_expression : term'
    p[0] = p[1]

# Signo unario: +x  -x
def p_simple_expression_sign(p):
    'simple_expression : addop term'
    if p[1] == '-':
        p[0] = UnaryOp(op='-', operand=p[2])
    else:
        p[0] = p[2]                     # unary + is a no-op

def p_addop_plus(p):  'addop : PLUS'  ; p[0] = '+'
def p_addop_minus(p): 'addop : MINUS' ; p[0] = '-'

# Término

def p_term_mulop(p):
    'term : term mulop factor'
    p[0] = BinOp(op=p[2], left=p[1], right=p[3])

def p_term_and(p):
    'term : term AND factor'
    p[0] = BinOp(op='and', left=p[1], right=p[3])

def p_term_shl(p):
    'term : term SHL factor'
    p[0] = BinOp(op='shl', left=p[1], right=p[3])

def p_term_shr(p):
    'term : term SHR factor'
    p[0] = BinOp(op='shr', left=p[1], right=p[3])

def p_term_factor(p):
    'term : factor'
    p[0] = p[1]

def p_mulop_times(p):  'mulop : TIMES'  ; p[0] = '*'
def p_mulop_divide(p): 'mulop : DIVIDE' ; p[0] = '/'
def p_mulop_div(p):    'mulop : DIV'    ; p[0] = 'div'
def p_mulop_mod(p):    'mulop : MOD'    ; p[0] = 'mod'

# Factor

def p_factor_paren(p):
    'factor : LPAREN expression RPAREN'
    p[0] = p[2]                         # parentheses carry no AST node

def p_factor_variable(p):
    'factor : variable'
    p[0] = p[1]

def p_factor_call(p):
    'factor : ID LPAREN func_arg_list RPAREN'
    p[0] = FuncCall(name=p[1], args=p[3])

def p_factor_call_no_args(p):
    'factor : ID LPAREN RPAREN'
    p[0] = FuncCall(name=p[1], args=[])

def p_factor_literal(p):
    'factor : literal'
    p[0] = p[1]

def p_factor_not(p):
    'factor : NOT factor'
    p[0] = UnaryOp(op='not', operand=p[2])

def p_factor_nil(p):
    'factor : NIL'
    p[0] = NilLiteral()

def p_factor_addr(p):
    'factor : AT variable'
    p[0] = UnaryOp(op='@', operand=p[2])

def p_factor_deref(p):
    'factor : factor CARET'
    p[0] = UnaryOp(op='^', operand=p[1])

def p_factor_set(p):
    'factor : set_literal'
    p[0] = p[1]

# Conjuntos literales  [a, b, c..z]

def p_set_literal_empty(p):
    'set_literal : LBRACKET RBRACKET'
    p[0] = SetLiteral(elements=[])

def p_set_literal_elems(p):
    'set_literal : LBRACKET set_element_list RBRACKET'
    p[0] = SetLiteral(elements=p[2])

def p_set_element_list_multi(p):
    'set_element_list : set_element_list COMMA set_element'
    p[0] = p[1] + [p[3]]

def p_set_element_list_single(p):
    'set_element_list : set_element'
    p[0] = [p[1]]

def p_set_element_single(p):
    'set_element : expression'
    p[0] = p[1]

def p_set_element_range(p):
    'set_element : expression DOTDOT expression'
    p[0] = SetRange(low=p[1], high=p[3])

# Variables

def p_variable_simple(p):
    'variable : ID'
    p[0] = Var(name=p[1])

def p_variable_array(p):
    'variable : variable LBRACKET expression_list RBRACKET'
    p[0] = ArrayAccess(base=p[1], indices=p[3])

def p_variable_field(p):
    'variable : variable DOT ID'
    p[0] = FieldAccess(base=p[1], field=p[3])

# a[i, j]
def p_expression_list_multi(p):
    'expression_list : expression_list COMMA expression'
    p[0] = p[1] + [p[3]]

def p_expression_list_single(p):
    'expression_list : expression'
    p[0] = [p[1]]

# Literales 

def p_literal_integer(p): 'literal : INTEGER'; p[0] = Literal(p[1], 'integer')
def p_literal_real(p):    'literal : REAL'   ; p[0] = Literal(p[1], 'real')
def p_literal_string(p):  'literal : STRING' ; p[0] = Literal(p[1], 'string')
def p_literal_char(p):    'literal : CHAR'   ; p[0] = Literal(p[1], 'char')
def p_literal_true(p):    'literal : TRUE'   ; p[0] = Literal(True,  'boolean')
def p_literal_false(p):   'literal : FALSE'  ; p[0] = Literal(False, 'boolean')

# Producción vacía 

def p_empty(p):
    'empty :'
    p[0] = None

#  MANEJO DE ERRORES SINTÁCTICOS

_STMT_STARTERS = {
    'ID', 'IF', 'WHILE', 'FOR', 'REPEAT', 'BEGIN',
    'WRITE', 'WRITELN', 'READ', 'READLN',
    'BREAK', 'CONTINUE', 'EXIT', 'CASE', 'WITH', 'GOTO',
}

def p_error(p):
    global SYNTAX_ERRORS
    SYNTAX_ERRORS += 1

    if p is None:
        if VERBOSE:
            print("ERROR SINTÁCTICO: fin de archivo inesperado")
        return

    if VERBOSE:
        line = p.lineno if hasattr(p, 'lineno') else pascal_lexer.lexer.lineno
        if p.type in _STMT_STARTERS:
            print(f"ERROR SINTÁCTICO [línea {line}]: "
                  f"falta ';' antes de '{p.value}'")
        else:
            print(f"ERROR SINTÁCTICO [línea {line}]: "
                  f"token inesperado '{p.value}' (tipo: {p.type})")

    while True:
        tok = parser.token()
        if tok is None:
            break
        if tok.type in ('SEMICOLON', 'END'):
            parser.errok()
            break

#  CONSTRUCCIÓN DEL PARSER

parser = yacc.yacc()

#  PUNTO DE ENTRADA

if __name__ == '__main__':

    if len(sys.argv) > 1:
        fin = sys.argv[1]
    else:
        fin = Path(__file__).resolve().parent / 'programa.pas'

    SYNTAX_ERRORS = 0
    pascal_lexer.reset_lexer_state()

    with open(fin, 'r', encoding='utf-8') as f:
        data = f.read()

    inicio = time.perf_counter()
    ast = parser.parse(data, lexer=pascal_lexer.lexer)
    fin_tiempo = time.perf_counter()

    lexical_errors = pascal_lexer.LEXICAL_ERRORS
    total_errors   = lexical_errors + SYNTAX_ERRORS
    duracion       = fin_tiempo - inicio

    print()
    print("\n        RESUMEN DE COMPILACIÓN\n")
    print(f"  Tiempo total       : {duracion:.6f} s")
    print(f"  Errores léxicos    : {lexical_errors}")
    print(f"  Errores sintácticos: {SYNTAX_ERRORS}")
    print(f"  Errores totales    : {total_errors}")
    print("=" * 50)

    if total_errors == 0:
        print("Compilación finalizada sin errores.")
        print()
        if ast is not None:
            print("═" * 50)
            print("  ÁRBOL SINTÁCTICO ABSTRACTO (AST)")
            print("═" * 50)
            print(pretty(ast))
    else:
        print("Compilación finalizada con errores.")
    print()