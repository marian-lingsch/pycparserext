from typing import NamedTuple

from pycparser.c_lexer import CLexer as CLexerBase
from pycparser.plyparser import ParseError


try:
    from pycparser.ply.lex import TOKEN
except ImportError:
    from ply.lex import TOKEN


class GnuCLexer(CLexerBase):
    #: If true, line markers and ``#line`` directives do not change the
    #: coordinates, which are then the lines and columns in the given text.
    physical_coords = False

    # support '3i' for imaginary literal
    floating_constant = (
            "(((("
            + CLexerBase.fractional_constant+")"
            + CLexerBase.exponent_part+"?)|([0-9]+"
            + CLexerBase.exponent_part+"))i?[FfLl]?)")

    @TOKEN(floating_constant)
    def t_FLOAT_CONST(self, t):
        return t

    # Comments are skipped like whitespace. These rules replace the ones of
    # pycparser, which reject comments.
    def t_UNSUPPORTED_C_STYLE_COMMENT(self, t):
        r"/\*[^*]*\*+([^/*][^*]*\*+)*/"
        t.lexer.lineno += t.value.count("\n")

    def t_UNSUPPORTED_CXX_STYLE_COMMENT(self, t):
        r"//(\\\n|[^\n])*"
        t.lexer.lineno += t.value.count("\n")

    def t_UNTERMINATED_COMMENT(self, t):
        r"/\*"
        self._error("Unterminated comment", t)

    def t_ppline_NEWLINE(self, t):
        r"\n"
        if self.physical_coords:
            t.lexer.lineno += 1
            t.lexer.begin("INITIAL")
        else:
            super().t_ppline_NEWLINE(t)

    t_pppragma_ignore = " \t<>.-{}();+-*/$%@&^~!?:,0123456789="

    def token(self):
        token = super().token()
        if token is not None and token.value in _KEYWORD_SPELLINGS:
            token.value = _KEYWORD_SPELLINGS[token.value]
        return token


class GNUCLexer(GnuCLexer):
    def __init__(self, *args, **kwargs):
        from warnings import warn
        warn("GNUCLexer is now called GnuCLexer",
                DeprecationWarning, stacklevel=2)

        GnuCLexer.__init__(self, *args, **kwargs)


class OpenCLCLexer(CLexerBase):
    tokens = (*CLexerBase.tokens, "LINECOMMENT")
    states = (
            # ('comment', 'exclusive'),
            # ('preproc', 'exclusive'),
            ("ppline", "exclusive"),  # unused
            ("pppragma", "exclusive"),  # unused
            )

    def t_LINECOMMENT(self, t):
        r"\/\/([^\n]+)\n"
        t.lexer.lineno += t.value.count("\n")

    # overrides pycparser, must have same name
    def t_PPHASH(self, t):
        r"[ \t]*\#([^\n]|\\\n)+[^\n\\]\n"
        t.lexer.lineno += t.value.count("\n")
        return t


def add_lexer_keywords(cls, keywords):
    cls.keywords = cls.keywords + tuple(
            kw.upper() for kw in keywords)

    cls.keyword_map = cls.keyword_map.copy()
    cls.keyword_map.update({kw: kw.upper() for kw in keywords})

    cls.tokens = cls.tokens + tuple(
            kw.upper() for kw in keywords)


_COMMON_KEYWORDS = [
    "__attribute__", "__attribute",
    "__asm__", "__asm", "asm"]

_GNU_KEYWORDS = [
    "__typeof__", "typeof", "__typeof",
    "__real__", "__imag__",
    "__builtin_types_compatible_p",
    "__const",
    "__restrict__", "__restrict",
    "__inline__", "__inline",
    "__extension__",
    "__volatile", "__volatile__",
    "__alignof__"]

add_lexer_keywords(GnuCLexer, _COMMON_KEYWORDS + _GNU_KEYWORDS)

# Other GNU spellings of keywords, which the lexer replaces by the usual ones
_KEYWORD_SPELLINGS = {
    "__signed__": "signed",
    "__signed": "signed",
    "__alignof": "__alignof__",
}
GnuCLexer.keyword_map.update({
    spelling: GnuCLexer.keyword_map[keyword]
    for spelling, keyword in _KEYWORD_SPELLINGS.items()})
# Thread-local storage, kept as written
GnuCLexer.keyword_map["__thread"] = "_THREAD_LOCAL"

# These will be added as unadorned keywords and keywords with '__' prepended
_CL_BASE_KEYWORDS = [
    "kernel", "constant", "global", "local", "private",
    "read_only", "write_only", "read_write"]

_CL_KEYWORDS = _COMMON_KEYWORDS
_CL_KEYWORDS += _CL_BASE_KEYWORDS + ["__"+kw for kw in _CL_BASE_KEYWORDS]

add_lexer_keywords(OpenCLCLexer, _CL_KEYWORDS)


class Token(NamedTuple):
    """A token and the position of its first character."""
    type: str
    value: str
    line: int
    column: int


def tokenize(text, physical_coords=True):
    """Yields the tokens of the GNU C code *text* as the parser sees them,
    e.g. without comments and line markers. With *physical_coords*, the
    positions are the lines and columns in *text*. Identifiers are never
    ``TYPEID``, since only the parser knows the names of types.

    :raises ParseError: if *text* contains an invalid token.
    """
    def error(msg, line, column):
        raise ParseError(f":{line}:{column}: {msg}")

    lexer = GnuCLexer(error, lambda: None, lambda: None, lambda name: False)
    lexer.build(optimize=False)
    lexer.physical_coords = physical_coords
    lexer.input(text)
    while True:
        token = lexer.token()
        if token is None:
            return
        yield Token(token.type, token.value, token.lineno,
                    lexer.find_tok_column(token))


# vim: fdm=marker
