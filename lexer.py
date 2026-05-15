import ply.lex as lex
import sys

LEXICAL_ERRORS = 0

#  PALABRAS RESERVADAS

reserved = {
    'program'   : 'PROGRAM',
    'uses'      : 'USES',
    'var'       : 'VAR',
    'begin'     : 'BEGIN',
    'end'       : 'END',
    'if'        : 'IF',
    'then'      : 'THEN',
    'else'      : 'ELSE',
    'while'     : 'WHILE',
    'do'        : 'DO',
    'for'       : 'FOR',
    'to'        : 'TO',
    'downto'    : 'DOWNTO',
    'repeat'    : 'REPEAT',
    'until'     : 'UNTIL',
    'procedure' : 'PROCEDURE',
    'function'  : 'FUNCTION',
    'write'     : 'WRITE',
    'writeln'   : 'WRITELN',
    'read'      : 'READ',
    'readln'    : 'READLN',
    'array'     : 'ARRAY',
    'of'        : 'OF',
    'and'       : 'AND',
    'or'        : 'OR',
    'not'       : 'NOT',
    'div'       : 'DIV',
    'mod'       : 'MOD',
    'true'      : 'TRUE',
    'false'     : 'FALSE',
    'const'     : 'CONST',
    'type'      : 'TYPE',
    'record'    : 'RECORD',
    'nil'       : 'NIL',
    'with'      : 'WITH',
    'in'        : 'IN',
    'xor'       : 'XOR',
    'shl'       : 'SHL',
    'shr'       : 'SHR',
    'goto'      : 'GOTO',
    'label'     : 'LABEL',
    'case'      : 'CASE',
    'otherwise' : 'OTHERWISE',
    'break'     : 'BREAK',
    'continue'  : 'CONTINUE',
    'exit'      : 'EXIT',
    'forward'   : 'FORWARD',
    # Tipos estándar
    'integer'   : 'INTEGER_TYPE',
    'real'      : 'REAL_TYPE',
    'boolean'   : 'BOOLEAN_TYPE',
    'char'      : 'CHAR_TYPE',
    'string'    : 'STRING_TYPE',
    # Tipos extendidos
    'longint'   : 'LONGINT_TYPE',
    'shortint'  : 'SHORTINT_TYPE',
    'byte'      : 'BYTE_TYPE',
    'word'      : 'WORD_TYPE',
    'int64'     : 'INT64_TYPE',
    'single'    : 'SINGLE_TYPE',
    'double'    : 'DOUBLE_TYPE',
    'extended'  : 'EXTENDED_TYPE',
    'longreal'  : 'LONGREAL_TYPE',
    'text'      : 'TEXT_TYPE',
    'cardinal'  : 'CARDINAL_TYPE',
    'qword'     : 'QWORD_TYPE',
    'pointer'   : 'POINTER_TYPE',
    'pchar'     : 'PCHAR_TYPE',
    'ansistring': 'ANSISTRING_TYPE',
    'widestring': 'WIDESTRING_TYPE',
    'variant'   : 'VARIANT_TYPE',
}

#  LISTA DE TOKENS

tokens = list(reserved.values()) + [
    'ID',
    'INTEGER',
    'REAL',
    'STRING',
    'CHAR',
    'PLUS',
    'MINUS',
    'TIMES',
    'DIVIDE',
    'EQ',
    'NEQ',
    'LT',
    'LE',
    'GT',
    'GE',
    'ASSIGN',
    'LPAREN',
    'RPAREN',
    'LBRACKET',
    'RBRACKET',
    'SEMICOLON',
    'COLON',
    'COMMA',
    'DOT',
    'DOTDOT',
    'AT',
    'CARET',
]

#  REGLAS SIMPLES

t_PLUS      = r'\+'
t_MINUS     = r'-'
t_TIMES     = r'\*'
t_DIVIDE    = r'/'
t_EQ        = r'='
t_LPAREN    = r'\('
t_RPAREN    = r'\)'
t_LBRACKET  = r'\['
t_RBRACKET  = r'\]'
t_SEMICOLON = r';'
t_COMMA     = r','
t_AT        = r'@'
t_CARET     = r'\^'

#  REGLAS COMPLEJAS

def t_COMPILER_DIRECTIVE(t):
    r'\{\$[^}]*\}'
    t.lexer.lineno += t.value.count('\n')

# Comentario con llaves { … }
def t_COMMENT_BRACE(t):
    r'\{[^}]*\}'
    t.lexer.lineno += t.value.count('\n')

# Comentario de llave no cerrado
def t_UNCLOSED_COMMENT_BRACE(t):
    r'\{[^}]*'
    global LEXICAL_ERRORS
    start_line = t.lexer.lineno
    t.lexer.lineno += t.value.count('\n')
    LEXICAL_ERRORS += 1
    print(f"Error léxico [línea {start_line}]: comentario '{{' no cerrado")

# Comentario (* … *)
def t_COMMENT_PAREN(t):
    r'\(\*(.|\n)*?\*\)'
    t.lexer.lineno += t.value.count('\n')

# Comentario (* no cerrado
def t_UNCLOSED_COMMENT_PAREN(t):
    r'\(\*(.|\n)*'
    global LEXICAL_ERRORS
    start_line = t.lexer.lineno
    t.lexer.lineno += t.value.count('\n')
    LEXICAL_ERRORS += 1
    print(f"Error léxico [línea {start_line}]: comentario '(*' no cerrado")

# Comentario de línea //
def t_COMMENT_SLASH(t):
    r'//[^\n]*'
    pass

# Asignación := 
def t_ASSIGN(t):
    r':='
    return t

# Rango ..  
def t_DOTDOT(t):
    r'\.\.'
    return t

# Punto simple
def t_DOT(t):
    r'\.'
    return t

# Dos puntos simple
def t_COLON(t):
    r':'
    return t

# Relacionales compuestos
def t_LE(t):
    r'<='
    return t

def t_GE(t):
    r'>='
    return t

def t_NEQ(t):
    r'<>'
    return t

def t_LT(t):
    r'<'
    return t

def t_GT(t):
    r'>'
    return t

# Número inválido: dígitos pegados a letra
def t_INVALID_NUMBER(t):
    r'\d+(\.\d+)?[a-zA-Z_]\w*'
    global LEXICAL_ERRORS
    LEXICAL_ERRORS += 1
    print(f"Error léxico [línea {t.lexer.lineno}]: "
          f"token inválido '{t.value}' — número seguido de identificador")

# Número real
def t_REAL(t):
    r'\d+\.\d+([eE][+-]?\d+)?'
    t.value = float(t.value)
    return t

# Número entero
def t_INTEGER(t):
    r'\d+'
    t.value = int(t.value)
    return t

# Número hexadecimal
def t_HEX(t):
    r'\$[0-9A-Fa-f]+'
    t.type  = 'INTEGER'
    t.value = int(t.value[1:], 16)
    return t

# Cadena / carácter
def t_STRING(t):
    r"'([^'\n]|'')*'"
    inner   = t.value[1:-1].replace("''", "'")
    t.value = inner
    t.type  = 'CHAR' if len(inner) == 1 else 'STRING'
    return t

# Cadena no cerrada
def t_UNCLOSED_STRING(t):
    r"'[^'\n]*"
    global LEXICAL_ERRORS
    LEXICAL_ERRORS += 1
    print(f"Error léxico [línea {t.lexer.lineno}]: "
          f"cadena de texto no cerrada → {t.value!r}")

# Identificadores y palabras reservadas
def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.value = t.value.lower()
    t.type  = reserved.get(t.value, 'ID')
    return t

# Saltos de línea
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

t_ignore = ' \t\r'

#  ERRORES LÉXICOS

def t_error(t):
    global LEXICAL_ERRORS
    LEXICAL_ERRORS += 1
    print(f"Error léxico [línea {t.lexer.lineno}]: "
          f"carácter no reconocido '{t.value[0]}'")
    t.lexer.skip(1)


def reset_lexer_state():
    global LEXICAL_ERRORS
    LEXICAL_ERRORS = 0
    lexer.lineno = 1

def has_lexical_errors():
    return LEXICAL_ERRORS > 0

def test(data, lx):
    lx.input(data)
    while True:
        tok = lx.token()
        if not tok:
            break
        print(tok)

lexer = lex.lex()

if __name__ == '__main__':
    fin = sys.argv[1] if len(sys.argv) > 1 else 'programa.pas'
    with open(fin, 'r') as f:
        data = f.read()
    print(data)
    print('-' * 50)
    test(data, lexer)