
import pycparser.c_parser
from pycparser import c_ast


try:
    from pycparser.ply import yacc
except ImportError:
    from ply import yacc  # ruff:ignore[unused-import]
from pycparser.plyparser import parameterized, template


class CParserBase(pycparser.c_parser.CParser):
    def __init__(self, **kwds):
        kwds["lexer"] = self.lexer_class
        kwds["lextab"] = "pycparserext.lextab"
        kwds["yacctab"] = "pycparserext.yacctab"
        pycparser.c_parser.CParser.__init__(self, **kwds)

    def parse(self, text, filename="", debuglevel=0,
            initial_type_symbols=frozenset()):
        self.clex.filename = filename
        self.clex.reset_lineno()

        # _scope_stack[-1] is the current (topmost) scope.

        initial_scope = dict.fromkeys(initial_type_symbols, 1)
        initial_scope.update(
                dict.fromkeys(self.initial_type_symbols, 1)
                )
        self._scope_stack = [initial_scope]

        if not text or text.isspace():
            return c_ast.FileAST([])
        else:
            return self.cparser.parse(text, lexer=self.clex, debug=debuglevel)


# {{{ ast extensions

class TypeList(c_ast.Node):
    def __init__(self, types, coord=None):
        self.types = types
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.types or []):
            nodelist.append(("types[%d]" % i, child))
        return tuple(nodelist)

    def __iter__(self):
        yield from (self.types or [])

    attr_names = ()


class AttributeSpecifier(c_ast.Node):
    def __init__(self, exprlist):
        self.exprlist = exprlist

    def __eq__(self, other):
        if not isinstance(other, AttributeSpecifier):
            return False
        # Recursively compare the exprlist nodes
        return self._compare_ast_nodes(self.exprlist, other.exprlist)

    def _compare_ast_nodes(self, node1, node2):
        """Recursively compare two AST nodes for structural equality."""
        if type(node1) is not type(node2):
            return False

        # Compare attributes
        if hasattr(node1, "attr_names"):
            for attr in node1.attr_names:
                val1 = getattr(node1, attr)
                val2 = getattr(node2, attr)
                if val1 != val2:
                    return False

        # Compare children
        if hasattr(node1, "children"):
            children1 = node1.children()
            children2 = node2.children()
            if len(children1) != len(children2):
                return False
            for (name1, child1), (name2, child2) in zip(children1, children2):
                if name1 != name2:
                    return False
                if not self._compare_ast_nodes(child1, child2):
                    return False

        return True

    def children(self):
        return [("exprlist", self.exprlist)]

    def __iter__(self):
        # Do not return anything, but yield is necessary to keep this function
        # a generator
        return
        yield

    attr_names = ()


class Asm(c_ast.Node):
    def __init__(self, asm_keyword, template, output_operands,
            input_operands, clobbered_regs, coord=None):
        self.asm_keyword = asm_keyword
        self.template = template
        self.output_operands = output_operands
        self.input_operands = input_operands
        self.clobbered_regs = clobbered_regs
        self.coord = coord

    def children(self):
        nodelist = []
        if self.template is not None:
            nodelist.append(("template", self.template))
        if self.output_operands is not None:
            nodelist.append(("output_operands", self.output_operands))
        if self.input_operands is not None:
            nodelist.append(("input_operands", self.input_operands))
        if self.clobbered_regs is not None:
            nodelist.append(("clobbered_regs", self.clobbered_regs))
        return tuple(nodelist)

    def __iter__(self):
        if self.template is not None:
            yield self.template
        if self.output_operands is not None:
            yield self.output_operands
        if self.input_operands is not None:
            yield self.input_operands
        if self.clobbered_regs is not None:
            yield self.clobbered_regs

    attr_names = ("asm_keyword",)


class PreprocessorLine(c_ast.Node):
    def __init__(self, contents, coord=None):
        self.contents = contents
        self.coord = coord

    def children(self):
        return ()

    def __iter__(self):
        # Do not return anything, but yield is necessary to keep this function
        # a generator
        return
        yield

    attr_names = ("contents",)


class TypeOfDeclaration(c_ast.Node):
    def __init__(self, typeof_keyword, declaration, coord=None):
        self.typeof_keyword = typeof_keyword
        self.declaration = declaration
        self.coord = coord

    def children(self):
        nodelist = []
        if self.declaration is not None:
            nodelist.append(("declaration", self.declaration))
        return tuple(nodelist)

    def __iter__(self):
        if self.declaration is not None:
            yield self.declaration

    attr_names = ("typeof_keyword",)


class TypeOfExpression(c_ast.Node):
    def __init__(self, typeof_keyword, expr, coord=None):
        self.typeof_keyword = typeof_keyword
        self.expr = expr
        self.coord = coord

    def children(self):
        nodelist = []
        if self.expr is not None:
            nodelist.append(("expr", self.expr))
        return tuple(nodelist)

    def __iter__(self):
        if self.expr is not None:
            yield self.expr

    attr_names = ("typeof_keyword",)


class RangeExpression(c_ast.Node):
    def __init__(self, first, last, coord=None):
        self.first = first
        self.last = last
        self.coord = coord

    def children(self):
        nodelist = []
        if self.first is not None:
            nodelist.append(("first", self.first))
        if self.last is not None:
            nodelist.append(("last", self.last))
        return tuple(nodelist)

    def __iter__(self):
        if self.first is not None:
            yield self.first
        if self.last is not None:
            yield self.last

    attr_names = ()


class CompoundExpression(c_ast.Node):
    def __init__(self, stmt, coord=None):
        self.stmt = stmt
        self.coord = coord

    def children(self):
        nodelist = []
        if self.stmt is not None:
            nodelist.append(("stmt", self.stmt))
        return tuple(nodelist)

    def __iter__(self):
        if self.stmt is not None:
            yield self.stmt

    attr_names = ()


# These are the same as pycparser's, but it does *not* declare __slots__--
# so we can poke in attributes at our leisure.
class TypeDeclExt(c_ast.TypeDecl):
    __slots__ = ("asm", "attributes", "init")

    @staticmethod
    def from_pycparser(td):
        assert isinstance(td, c_ast.TypeDecl)

        return TypeDeclExt(
            declname=td.declname,
            quals=td.quals,
            align=td.align,
            type=td.type,
            coord=td.coord
        )


class ArrayDeclExt(c_ast.ArrayDecl):
    __slots__ = ("asm", "attributes", "init")

    @staticmethod
    def from_pycparser(ad):
        assert isinstance(ad, c_ast.ArrayDecl)
        return ArrayDeclExt(
            type=ad.type,
            dim=ad.dim,
            dim_quals=ad.dim_quals,
            coord=ad.coord
        )


class StructExt(c_ast.Struct):
    """Extended Struct that can hold attributes."""
    @staticmethod
    def from_pycparser(st):
        assert isinstance(st, c_ast.Struct)
        return StructExt(
            name=st.name,
            decls=st.decls,
            coord=st.coord
        )


class UnionExt(c_ast.Union):
    """Extended Union that can hold attributes."""
    @staticmethod
    def from_pycparser(un):
        assert isinstance(un, c_ast.Union)
        return UnionExt(
            name=un.name,
            decls=un.decls,
            coord=un.coord
        )


def with_struct_attributes(node, attr_decl):
    """Returns the struct or union *node* with the attributes *attr_decl*."""
    if not attr_decl or not attr_decl.exprs:
        return node
    if not isinstance(node, (StructExt, UnionExt)):
        if isinstance(node, c_ast.Struct):
            node = StructExt.from_pycparser(node)
        else:
            node = UnionExt.from_pycparser(node)
    if getattr(node, "attrib", None):
        node.attrib.exprlist.exprs.extend(attr_decl.exprs)
    else:
        node.attrib = AttributeSpecifier(attr_decl)
    return node


def to_decl_ext(d):
    if isinstance(d, c_ast.TypeDecl):
        return TypeDeclExt.from_pycparser(d)
    elif isinstance(d, c_ast.ArrayDecl):
        return ArrayDeclExt.from_pycparser(d)
    else:
        raise TypeError("unexpected decl type: %s" % type(d).__name__)


class FuncDeclExt(c_ast.Node):
    def __init__(self, args, type, attributes, asm, coord=None):
        self.args = args
        self.type = type
        self.attributes = attributes
        self.asm = asm
        self.coord = coord

    def children(self):
        nodelist = []
        if self.args is not None:
            nodelist.append(("args", self.args))
        if self.type is not None:
            nodelist.append(("type", self.type))
        if self.attributes is not None:
            nodelist.append(("attributes", self.attributes))
        if self.asm is not None:
            nodelist.append(("asm", self.asm))
        return tuple(nodelist)

    def __iter__(self):
        if self.args is not None:
            yield self.args
        if self.type is not None:
            yield self.type
        if self.attributes is not None:
            yield self.attributes
        if self.asm is not None:
            yield self.asm

    attr_names = ()

# }}}


# {{{ attributes

class _AttributesMixin:
    def p_attributes_opt_1(self, p):
        """ attributes_opt : attribute_decl attributes_opt
        """
        p[1].exprs.extend(p[2].exprs)
        p[0] = p[1]

    def p_attributes_opt_2(self, p):
        """ attributes_opt : empty
        """
        p[0] = c_ast.ExprList([], self._coord(p.lineno(1)))

    def p_attribute_decl(self, p):
        """ attribute_decl : __ATTRIBUTE__ LPAREN LPAREN attribute_list RPAREN RPAREN
                           | __ATTRIBUTE LPAREN LPAREN attribute_list RPAREN RPAREN
        """
        p[0] = p[4]

    def p_attribute_list_1(self, p):
        """ attribute_list : attribute
        """
        p[0] = c_ast.ExprList([p[1]], self._coord(p.lineno(1)))

    def p_attribute_list_2(self, p):
        """ attribute_list : attribute_list COMMA attribute
        """
        p[1].exprs.append(p[3])
        p[0] = p[1]

    def p_attribute_1(self, p):
        """ attribute : CONST
        """
        p[0] = c_ast.ID(name="const", coord=self._coord(p.lineno(1)))

    def p_attribute_3(self, p):
        """ attribute : assignment_expression
        """
        p[0] = p[1]

    def p_function_specifier_attr(self, p):
        """ function_specifier : attribute_decl
        """
        p[0] = AttributeSpecifier(p[1])

# }}}


# {{{ asm

class _AsmMixin:
    def p_asm_opt_1(self, p):
        """ asm_opt : empty
        """
        p[0] = None

    def p_asm_opt_2(self, p):
        """ asm_opt : asm_no_semi
        """
        p[0] = p[1]

    def p_asm_1(self, p):
        """ asm_no_semi : asm_keyword LPAREN asm_argument_expression_list RPAREN
        """
        p[0] = Asm(p[1], p[3], None, None, None, coord=self._coord(p.lineno(2)))

    def p_asm_2(self, p):
        """ asm_no_semi : asm_keyword LPAREN asm_argument_expression_list COLON \
                asm_argument_expression_list RPAREN
        """
        p[0] = Asm(p[1], p[3], p[5], None, None, coord=self._coord(p.lineno(2)))

    def p_asm_3(self, p):
        """ asm_no_semi : asm_keyword LPAREN asm_argument_expression_list COLON \
                asm_argument_expression_list COLON asm_argument_expression_list \
                RPAREN
        """
        p[0] = Asm(p[1], p[3], p[5], p[7], None, coord=self._coord(p.lineno(2)))

    def p_asm_4(self, p):
        """ asm_no_semi : asm_keyword LPAREN asm_argument_expression_list COLON \
                asm_argument_expression_list COLON asm_argument_expression_list \
                COLON asm_argument_expression_list RPAREN
        """
        p[0] = Asm(p[1], p[3], p[5], p[7], p[9], coord=self._coord(p.lineno(2)))

    def p_asm_keyword(self, p):
        """ asm_keyword : __ASM__ asm_volatile_opt
                        | __ASM asm_volatile_opt
                        | ASM asm_volatile_opt
        """
        p[0] = p[1]
        if p[2]:
            p[0] += " " + p[2]

    def p_asm_volatile_opt(self, p):
        """ asm_volatile_opt : unified_volatile
                             | empty
        """
        p[0] = p[1]

    def p_asm_argument_expression_list(self, p):
        """asm_argument_expression_list : argument_expression_list
                                        | empty
        """
        p[0] = p[1]

    def p_statement_asm(self, p):
        """ statement : asm_no_semi
                      | asm_no_semi SEMI
        """
        p[0] = p[1]

    def p_asm_label_opt(self, p):
        """ asm_label_opt : asm_keyword LPAREN unified_string_literal RPAREN
                          | empty
        """
        if p[1] is None:
            p[0] = None
        else:
            p[0] = Asm(p[1], p[3], None, None, None, coord=self._coord(p.lineno(2)))

# }}}


@template
class _AsmAndAttributesMixin(_AsmMixin, _AttributesMixin):
    # {{{ /!\ names must match C parser to override

    @parameterized(("id", "ID"), ("typeid", "TYPEID"), ("typeid_noparen", "TYPEID"))
    def p_xxx_declarator_1(self, p):
        """ xxx_declarator  : direct_xxx_declarator asm_label_opt attributes_opt
        """
        p[0] = self._attach_asm_and_attributes(p[1], p[2], p[3])

    @parameterized(("id", "ID"), ("typeid", "TYPEID"), ("typeid_noparen", "TYPEID"))
    def p_xxx_declarator_2(self, p):
        """ xxx_declarator  : pointer direct_xxx_declarator asm_label_opt \
                                attributes_opt
                            | pointer attributes_opt direct_xxx_declarator \
                                asm_label_opt
        """
        if hasattr(p[4], "exprs"):
            decl = self._attach_asm_and_attributes(p[2], p[3], p[4])
        else:
            decl = self._attach_asm_and_attributes(p[3], p[4], p[2])

        p[0] = self._type_modify_decl(decl, p[1])

    @parameterized(("id", "ID"), ("typeid", "TYPEID"))
    def p_direct_xxx_declarator_attr(self, p):
        """ direct_xxx_declarator   : LPAREN attribute_decl attributes_opt \
                                            xxx_declarator RPAREN
        """
        # Attributes at the start of a nested declarator, e.g.
        # void (__attribute__((noreturn)) *f)(void);
        p[2].exprs.extend(p[3].exprs)
        p[0] = self._attach_asm_and_attributes(p[4], None, p[2])

    @staticmethod
    def _attach_asm_and_attributes(decl, asm_label, attr_decl):
        """Attaches the asm label and the attributes to the declared name,
        keeping the pointers, arrays, and functions of *decl*.
        """
        if not asm_label and not attr_decl.exprs:
            return decl

        parent = None
        innermost_decl = decl
        while not isinstance(innermost_decl, c_ast.TypeDecl):
            if not hasattr(innermost_decl, "type"):
                raise NotImplementedError(
                    "cannot attach asm or attributes to nodes of type '%s'"
                    % type(innermost_decl))
            parent, innermost_decl = innermost_decl, innermost_decl.type

        if isinstance(innermost_decl, TypeDeclExt):
            decl_ext = innermost_decl
        else:
            decl_ext = to_decl_ext(innermost_decl)
        if asm_label:
            decl_ext.asm = asm_label
        if attr_decl.exprs:
            attributes = getattr(decl_ext, "attributes", None)
            if attributes is not None and attributes.exprs:
                attributes.exprs.extend(attr_decl.exprs)
            else:
                decl_ext.attributes = attr_decl

        if parent is None:
            return decl_ext
        parent.type = decl_ext
        return decl

    def _build_declarations(self, spec, decls, typedef_namespace=False):
        # Typedefs have no function specifiers, so their attributes belong to
        # the declarators
        attributes = [a for a in spec["function"]
                      if isinstance(a, AttributeSpecifier)]
        if "typedef" in spec["storage"] and attributes:
            spec["function"] = [a for a in spec["function"]
                                if not isinstance(a, AttributeSpecifier)]
            for decl in decls:
                if decl["decl"] is not None:
                    decl["decl"] = self._attach_asm_and_attributes(
                        decl["decl"], None, c_ast.ExprList(
                            [e for a in attributes for e in a.exprlist.exprs],
                            attributes[0].exprlist.coord))

        declarations = super()._build_declarations(
            spec, decls, typedef_namespace)

        # Attributes after the declarator of a function are invalid in
        # definitions and not supported by all tools, so they become
        # declaration specifiers
        for declaration in declarations:
            if not isinstance(declaration, c_ast.Decl) or not isinstance(
                    declaration.type, (c_ast.FuncDecl, FuncDeclExt)):
                continue
            innermost_decl = declaration.type
            while not isinstance(innermost_decl, c_ast.TypeDecl):
                innermost_decl = innermost_decl.type
            attributes = getattr(innermost_decl, "attributes", None)
            if attributes is not None and attributes.exprs:
                declaration.funcspec = [
                    *declaration.funcspec, AttributeSpecifier(attributes)]
                innermost_decl.attributes = c_ast.ExprList(
                    [], attributes.coord)

        return declarations

    @parameterized(("id", "ID"), ("typeid", "TYPEID"), ("typeid_noparen", "TYPEID"))
    def p_direct_xxx_declarator_6(self, p):
        """ direct_xxx_declarator   : direct_xxx_declarator \
                                            LPAREN parameter_type_list RPAREN \
                                            asm_opt attributes_opt
                                    | direct_xxx_declarator \
                                            LPAREN identifier_list_opt RPAREN \
                                            asm_label_opt attributes_opt
        """
        func = FuncDeclExt(
            args=p[3],
            type=None,
            attributes=p[6],
            asm=p[5],
            coord=p[1].coord)

        # As in pycparser, the parameters of a function definition must be in
        # scope before the lexer reads the body, since they may hide typedefs
        if (self._get_yacc_lookahead_token().type == "LBRACE"
                and func.args is not None):
            for param in func.args.params:
                if isinstance(param, c_ast.EllipsisParam):
                    break
                self._add_identifier(param.name, param.coord)

        p[0] = self._type_modify_decl(decl=p[1], modifier=func)

    def p_type_name_attr(self, p):
        """ type_name   : specifier_qualifier_list attribute_decl attributes_opt \
                                abstract_declarator_opt
        """
        # E.g. in casts like (char __attribute__((deprecated)) *)p
        p[2].exprs.extend(p[3].exprs)
        typename = c_ast.Typename(
            name="",
            quals=p[1]["qual"][:],
            align=None,
            type=self._attach_asm_and_attributes(
                p[4] or c_ast.TypeDecl(None, None, None, None), None, p[2]),
            coord=self._token_coord(p, 2))

        p[0] = self._fix_decl_name_type(typename, p[1]["type"])

    def p_direct_abstract_declarator_6(self, p):
        """ direct_abstract_declarator  : direct_abstract_declarator \
                LPAREN parameter_type_list_opt RPAREN asm_label_opt attributes_opt
        """
        func = FuncDeclExt(
            args=p[3],
            type=None,
            attributes=p[6],
            asm=p[5],
            coord=p[1].coord)

        p[0] = self._type_modify_decl(decl=p[1], modifier=func)

    # }}}
# }}}


# {{{ gnu parser

class GnuCParser(_AsmAndAttributesMixin, CParserBase):
    from pycparserext.ext_c_lexer import (
        GnuCLexer as lexer_class,  # ruff:ignore[camelcase-imported-as-lowercase]
    )

    initial_type_symbols = frozenset({"__builtin_va_list"})

    def parse(self, text, filename="", debuglevel=0,
            initial_type_symbols=frozenset(), physical_coords=False):
        """Parses *text*. With *physical_coords*, line markers and ``#line``
        directives do not change the coordinates, which are then the lines
        and columns in *text*.
        """
        self.clex.physical_coords = physical_coords
        return super().parse(text, filename, debuglevel, initial_type_symbols)

    def p_function_specifier_gnu(self, p):
        """ function_specifier  : __INLINE
                                | __INLINE__
        """
        p[0] = p[1]

    def p_type_qualifier_gnu(self, p):
        """ type_qualifier  : __CONST
                            | __RESTRICT
                            | __RESTRICT__
                            | __VOLATILE
                            | __VOLATILE__
        """
        p[0] = p[1]

    def p_type_specifier_gnu_typeof_expr(self, p):
        """ type_specifier  : __TYPEOF__ LPAREN expression RPAREN
                            | TYPEOF LPAREN expression RPAREN
                            | __TYPEOF LPAREN expression RPAREN
        """
        p[0] = TypeOfExpression(p[1], p[3])

    def p_type_specifier_gnu_typeof_decl(self, p):
        """ type_specifier  : __TYPEOF__ LPAREN parameter_declaration RPAREN
                            | TYPEOF LPAREN parameter_declaration RPAREN
                            | __TYPEOF LPAREN parameter_declaration RPAREN
        """
        p[0] = TypeOfDeclaration(p[1], p[3])

    def p_unary_operator_gnu(self, p):
        """ unary_operator  : __REAL__
                            | __IMAG__
        """
        p[0] = p[1]

    def p_postfix_expression_gnu_tcp(self, p):
        """ postfix_expression  : __BUILTIN_TYPES_COMPATIBLE_P \
                LPAREN parameter_declaration COMMA parameter_declaration RPAREN
        """
        p[0] = c_ast.FuncCall(c_ast.ID(p[1], self._coord(p.lineno(1))),
                TypeList([p[3], p[5]], self._coord(p.lineno(2))))

    def p_gnu_statement_expression(self, p):
        """ gnu_statement_expression : LPAREN compound_statement RPAREN
        """
        p[0] = p[2]

    def p_gnu_primary_expression_6(self, p):
        """ primary_expression : gnu_statement_expression """
        p[0] = p[1]

    def p_gnu_unary_expression(self, p):
        """ unary_expression : __ALIGNOF__ LPAREN type_name RPAREN
                             | __ALIGNOF__ unary_expression
        """
        p[0] = c_ast.UnaryOp(
            p[1],
            p[2] if len(p) == 3 else p[3],
            self._token_coord(p, 1))

    def p_specifier_qualifier_list_fs(self, p):
        """ specifier_qualifier_list : function_specifier specifier_qualifier_list
        """
        self._p_specifier_qualifier_list_left_recursion(p)

    def _p_specifier_qualifier_list_left_recursion(self, p):
        # The PLY documentation says that left-recursive rules are supported,
        # but it keeps complaining about reduce/reduce conflicts.
        #
        # See `_p_specifier_qualifier_list_right_recursion` for a non-complaining
        # version.
        spec = p[1]
        spec_dict = p[2]

        if isinstance(spec, AttributeSpecifier):
            spec_dict["function"].append(spec)
        elif isinstance(spec, str):
            spec_dict["qual"].append(spec)
        elif isinstance(spec, c_ast.Node):
            if "type" not in spec_dict:
                spec_dict["type"] = []
            spec_dict["type"].append(spec)
        else:
            raise TypeError(f"Unknown specifier {spec!r} of type {type(spec)}")

        p[0] = spec_dict

    def p_statement(self, p):
        """ statement   : labeled_statement
                        | expression_statement
                        | compound_statement
                        | selection_statement
                        | iteration_statement
                        | jump_statement
                        | pppragma_directive
                        | gnu_statement_expression
        """
        p[0] = p[1]

    def p_attribute_const(self, p):
        """ attribute : __CONST
        """
        p[0] = c_ast.ID(name="__const", coord=self._coord(p.lineno(1)))

    def p_struct_declaration_list_1(self, p):
        """ struct_declaration_list : empty """
        p[0] = None

    # Support attributes on anonymous struct/union declarations
    # e.g., struct { int a; } __attribute__((packed));
    def p_struct_declaration_anonymous_with_attr(self, p):
        """ struct_declaration : specifier_qualifier_list attributes_opt SEMI
        """
        spec = p[1]
        attr_decl = p[2]
        assert "typedef" not in spec["storage"]

        # Anonymous struct/union with attributes
        if len(spec["type"]) == 1:
            node = spec["type"][0]
            if isinstance(node, (c_ast.Struct, c_ast.Union)):
                decl_type = with_struct_attributes(node, attr_decl)
            elif isinstance(node, c_ast.Node):
                decl_type = node
            else:
                decl_type = c_ast.IdentifierType(node)

            decls = self._build_declarations(
                spec=spec,
                decls=[{"decl": decl_type}])
        elif self._declares_nothing(spec):
            decls = None
        else:
            # Structure/union members can have the same names as typedefs
            decls = self._build_declarations(
                spec=spec,
                decls=[{"decl": None, "init": None}])

        p[0] = decls

    def _add_declaration_specifier(self, declspec, newspec, kind, append=False):
        # GCC applies attributes after a struct or union definition to its type
        types = declspec["type"] if declspec else []
        if (append and isinstance(newspec, AttributeSpecifier) and types
                and isinstance(types[-1], (c_ast.Struct, c_ast.Union))
                and types[-1].decls is not None):
            types[-1] = with_struct_attributes(types[-1], newspec.exprlist)
            return declspec
        return super()._add_declaration_specifier(
            declspec, newspec, kind, append)

    # struct { int a; } __attribute__((packed)) s;
    def p_struct_declaration_with_attr(self, p):
        """ struct_declaration : specifier_qualifier_list attribute_decl \
                attributes_opt struct_declarator_list SEMI
        """
        attr_decl = p[2]
        attr_decl.exprs.extend(p[3].exprs)
        spec = self._add_declaration_specifier(
            p[1], AttributeSpecifier(attr_decl), "function", append=True)
        p[0] = self._build_declarations(spec=spec, decls=p[4])

    def p_struct_declaration_1(self, p):
        """ struct_declaration : specifier_qualifier_list \
                struct_declarator_list_opt SEMI
        """
        if p[2] is None and len(p[1]["type"]) != 1 and self._declares_nothing(p[1]):
            p[0] = None
        else:
            super().p_struct_declaration_1(p)

    def _declares_nothing(self, spec):
        """Whether a member without declarator, like `unsigned char ;`,
        declares nothing, such that GCC ignores it. Otherwise, the last type
        name is the name of the member.
        """
        types = spec["type"]
        names = getattr(types[-1], "names", []) if types else []
        return (len(types) < 2
                or len(names) != 1
                or not self._is_type_in_scope(names[0]))

    def p_range_designator(self, p):
        """ designator  : LBRACKET constant_expression \
                            ELLIPSIS constant_expression RBRACKET
        """
        p[0] = RangeExpression(p[2], p[4], coord=self._coord(p.lineno(1)))

    def p_labeled_statement_4(self, p):
        """ labeled_statement : CASE constant_expression \
                                    ELLIPSIS constant_expression \
                                    COLON pragmacomp_or_statement
        """
        p[0] = c_ast.Case(
                RangeExpression(p[2], p[4], coord=self._coord(p.lineno(1))),
                [p[6]],
                self._coord(p.lineno(1)))

    def p_unified_volatile_gnu(self, p):
        """ unified_volatile : VOLATILE
                             | __VOLATILE
                             | __VOLATILE__
        """
        p[0] = p[1]

    # Support attributes on struct/union types
    # struct __attribute__((packed)) { int a; };
    def p_struct_or_union_specifier_with_attr_1(self, p):
        """struct_or_union_specifier  : struct_or_union attributes_opt \
                brace_open struct_declaration_list brace_close
                                      | struct_or_union attributes_opt \
                brace_open brace_close
        """
        klass = self._select_struct_union_class(p[1])
        attr_decl = p[2]

        if len(p) == 5:
            # Empty struct/union
            struct = klass(
                name=None,
                decls=[],
                coord=self._token_coord(p, 1))
        else:
            struct = klass(
                name=None,
                decls=p[4],
                coord=self._token_coord(p, 1))

        p[0] = with_struct_attributes(struct, attr_decl)

    # struct __attribute__((packed)) s { int a; };
    def p_struct_or_union_specifier_with_attr_3(self, p):
        """struct_or_union_specifier  : struct_or_union attribute_decl \
                attributes_opt ID
                                      | struct_or_union attribute_decl \
                attributes_opt TYPEID
                                      | struct_or_union attribute_decl \
                attributes_opt ID brace_open struct_declaration_list brace_close
                                      | struct_or_union attribute_decl \
                attributes_opt ID brace_open brace_close
                                      | struct_or_union attribute_decl \
                attributes_opt TYPEID brace_open struct_declaration_list \
                brace_close
                                      | struct_or_union attribute_decl \
                attributes_opt TYPEID brace_open brace_close
        """
        klass = self._select_struct_union_class(p[1])
        attr_decl = p[2]
        attr_decl.exprs.extend(p[3].exprs)

        if len(p) == 5:
            # None means no list of members
            decls = None
        elif len(p) == 7:
            decls = []
        else:
            decls = p[6]
        struct = klass(name=p[4], decls=decls, coord=self._token_coord(p, 4))
        p[0] = with_struct_attributes(struct, attr_decl)
# }}}


class OpenCLCParser(_AsmAndAttributesMixin, CParserBase):
    from pycparserext.ext_c_lexer import (
        OpenCLCLexer as lexer_class,  # ruff:ignore[camelcase-imported-as-lowercase]
    )

    INT_BIT_COUNTS = (8, 16, 32, 64)
    initial_type_symbols = (
            {
                "%s%d" % (base_name, count)
                for base_name in [
                    "char", "uchar", "short", "ushort", "int", "uint",
                    "long", "ulong", "float", "double", "half"]
                for count in [2, 3, 4, 8, 16]
                }
            | {
                "intptr_t", "uintptr_t",
                "intmax_t", "uintmax_t",
                "size_t", "ptrdiff_t",
                "uint", "ulong", "ushort", "uchar",
                "half", "bool"}
            | {"int%d_t" % bc for bc in INT_BIT_COUNTS}
            | {"uint%d_t" % bc for bc in INT_BIT_COUNTS}
            | {"int_least%d_t" % bc for bc in INT_BIT_COUNTS}
            | {"uint_least%d_t" % bc for bc in INT_BIT_COUNTS}
            | {"int_fast%d_t" % bc for bc in INT_BIT_COUNTS}
            | {"uint_fast%d_t" % bc for bc in INT_BIT_COUNTS}
            | {
                "image1d_t", "image1d_array_t", "image1d_buffer_t",
                "image2d_t", "image2d_array_t",
                "image3d_t",
                "sampler_t", "event_t"
                }
            | {"cfloat_t", "cdouble_t"}  # PyOpenCL extension
            )

    def p_pp_directive(self, p):
        """ pp_directive  : PPHASH
        """
        p[0] = [PreprocessorLine(p[1], coord=self._coord(p.lineno(1)))]

    def p_external_declaration_comment(self, p):
        """ external_declaration    : LINECOMMENT
        """
        p[0] = None

    def p_statement_comment(self, p):
        """ statement    : LINECOMMENT
        """
        p[0] = None

    def p_type_qualifier_cl(self, p):
        """ type_qualifier  : __GLOBAL
                            | GLOBAL
                            | __LOCAL
                            | LOCAL
                            | __CONSTANT
                            | CONSTANT
                            | __PRIVATE
                            | PRIVATE
                            | __READ_ONLY
                            | READ_ONLY
                            | __WRITE_ONLY
                            | WRITE_ONLY
                            | __READ_WRITE
                            | READ_WRITE
        """
        p[0] = p[1]

    def p_function_specifier_cl(self, p):
        """ function_specifier  : __KERNEL
                                | KERNEL
        """
        p[0] = p[1]

    def p_unified_volatile_cl(self, p):
        """ unified_volatile : VOLATILE
        """
        p[0] = p[1]

# vim: fdm=marker
