from pycparser import c_ast
from pycparser.c_generator import CGenerator as CGeneratorBaseBuggy

from pycparserext.ext_c_parser import (
    Asm,
    CompoundExpression,
    FuncDeclExt,
    TypeDeclExt,
)


class CGeneratorBase(CGeneratorBaseBuggy):
    # bug fix
    def visit_UnaryOp(self, n):
        operand = self._parenthesize_unless_simple(n.expr)
        if n.op == "p++":
            return "%s++" % operand
        elif n.op == "p--":
            return "%s--" % operand
        elif n.op == "sizeof":
            # Always parenthesize the argument of sizeof since it can be
            # a name.
            return "sizeof(%s)" % self.visit(n.expr)
        elif n.op == "__alignof__":
            return "__alignof__(%s)" % self.visit(n.expr)
        else:
            # avoid merging of "- - x" or "__real__varname"
            return "%s %s" % (n.op, operand)


class AsmAndAttributesMixin:
    def visit_Asm(self, n):
        components = [
                n.template,
                n.output_operands,
                n.input_operands,
                n.clobbered_regs,
                ]
        while len(components) > 1 and components[-1] is None:
            components.pop()

        return " %s(%s)" % (
                n.asm_keyword,
                " : ".join(
                    self.visit(c) for c in components))

    def _generate_stmt(self, n, add_indent=False):
        if not isinstance(n, (Asm, CompoundExpression)):
            return super()._generate_stmt(n, add_indent)
        if add_indent:
            self.indent_level += 2
        indent = self._make_indent()
        if add_indent:
            self.indent_level -= 2
        return indent + self.visit(n).lstrip() + ";\n"

    def _generate_type(self, n, modifiers=None, emit_declname=True):
        """ Recursive generation from a type node. n is the type node.
            modifiers collects the PtrDecl, ArrayDecl and FuncDecl modifiers
            encountered on the way down to a TypeDecl, to allow proper
            generation from it.
        """
        if modifiers is None:
            modifiers = []
        typ = type(n)
        # print(n, modifiers)

        if typ in (c_ast.TypeDecl, TypeDeclExt):
            s = ""
            if n.quals:
                s += " ".join(n.quals) + " "
            s += self.visit(n.type)

            nstr = n.declname if n.declname and emit_declname else ""
            # Resolve modifiers.
            # Wrap in parens to distinguish pointer to array and pointer to
            # function syntax.
            #
            for i, modifier in enumerate(modifiers):
                if isinstance(modifier, c_ast.ArrayDecl):
                    if i != 0 and isinstance(modifiers[i - 1], c_ast.PtrDecl):
                        nstr = "(" + nstr + ")"

                    # BUG FIX: pycparser ignores quals
                    dim_quals = (" ".join(modifier.dim_quals) + " "
                                 if modifier.dim_quals else "")

                    nstr += "[" + dim_quals + self.visit(modifier.dim) + "]"

                elif isinstance(modifier, c_ast.FuncDecl):
                    if i != 0 and isinstance(modifiers[i - 1], c_ast.PtrDecl):
                        nstr = "(" + nstr + ")"
                    nstr += "(" + self.visit(modifier.args) + ")"

                elif isinstance(modifier, FuncDeclExt):
                    if i != 0 and isinstance(modifiers[i - 1], c_ast.PtrDecl):
                        nstr = "(" + nstr + ")"
                    nstr += "(" + self.visit(modifier.args) + ")"

                    if modifier.asm is not None:
                        nstr += " " + self.visit(modifier.asm)

                    if modifier.attributes.exprs:
                        nstr += (
                                " __attribute__(("
                                + self.visit(modifier.attributes)
                                + "))")

                elif isinstance(modifier, c_ast.PtrDecl):
                    # BUG FIX: pycparser ignores quals
                    quals = " ".join(modifier.quals)
                    if quals:
                        quals = quals + " "
                    nstr = "*" + quals + nstr

            if hasattr(n, "asm") and n.asm:
                nstr += self.visit(n.asm)

            if hasattr(n, "attributes") and n.attributes.exprs:
                attributes = "__attribute__((" + self.visit(n.attributes) + "))"
                if n.declname:
                    nstr += " " + attributes
                else:
                    # Abstract declarators have no name to follow
                    nstr = attributes + (" " + nstr if nstr else "")

            if nstr:
                s += " " + nstr
            return s

        elif typ == c_ast.Decl:
            return self._generate_decl(n.type)

        elif typ == c_ast.Typename:
            return self._generate_type(n.type, emit_declname=emit_declname)

        elif typ == c_ast.IdentifierType:
            return " ".join(n.names) + " "

        elif typ in (c_ast.ArrayDecl, c_ast.PtrDecl, c_ast.FuncDecl, FuncDeclExt):
            return self._generate_type(
                    n.type, [*modifiers, n], emit_declname=emit_declname)

        else:
            return self.visit(n)

    def visit_AttributeSpecifier(self, n):
        return "__attribute__((" + self.visit(n.exprlist) + "))"

    def visit_NamedAsmOperand(self, n):
        return "[%s] %s" % (n.name, self.visit(n.operand))


class GnuCGenerator(AsmAndAttributesMixin, CGeneratorBase):
    def __init__(self, reduce_parentheses=False, brace_on_declaration_line=False):
        """With *brace_on_declaration_line*, the opening brace of a function
        body is on the line of the declaration, as tools with line-based
        rewriting of functions expect.
        """
        super().__init__(reduce_parentheses=reduce_parentheses)
        self.brace_on_declaration_line = brace_on_declaration_line

    def visit_FuncDef(self, n):
        if not self.brace_on_declaration_line or n.param_decls:
            return super().visit_FuncDef(n)
        decl = self.visit(n.decl)
        self.indent_level = 0
        return decl + " " + self.visit(n.body) + "\n"

    def _generate_decl(self, n):
        """ Generation from a Decl node.
        """
        s = ""

        def funcspec_to_str(i):
            if isinstance(i, c_ast.Node):
                return self.visit(i)
            else:
                return i

        if n.funcspec:
            s = " ".join(funcspec_to_str(i) for i in n.funcspec) + " "
        if n.storage:
            s += " ".join(n.storage) + " "
        s += self._generate_type(n.type)
        return s

    def visit_TypeOfDeclaration(self, n):
        return "%s(%s)" % (n.typeof_keyword, self.visit(n.declaration))

    def visit_TypeOfExpression(self, n):
        return "%s(%s)" % (n.typeof_keyword, self.visit(n.expr))

    def visit_TypeList(self, n):
        return ", ".join(self.visit(ch) for ch in n.types)

    def visit_RangeExpression(self, n):
        return "%s ... %s" % (self.visit(n.first), self.visit(n.last))

    def visit_CompoundExpression(self, n):
        return "(%s)" % self.visit(n.stmt).strip()

    def visit_Struct(self, n):
        """Generate code for struct, handling attributes if present."""
        return self._generate_struct_union_with_attributes(n, "struct")

    def visit_StructExt(self, n):
        """Generate code for StructExt with attributes."""
        return self.visit_Struct(n)

    def visit_Union(self, n):
        return self._generate_struct_union_with_attributes(n, "union")

    def visit_UnionExt(self, n):
        return self.visit_Union(n)

    def _generate_struct_union_with_attributes(self, n, keyword):
        s = self._generate_struct_union_enum(n, keyword)
        if hasattr(n, "attrib") and n.attrib:
            # Only after the keyword, the attributes belong to the type in
            # definitions as well as in references
            s = keyword + " " + self.visit(n.attrib) + s[len(keyword):]
        return s


class GNUCGenerator(GnuCGenerator):
    def __init__(self):
        from warnings import warn
        warn("GNUCGenerator is now called GnuCGenerator",
                DeprecationWarning, stacklevel=2)


class OpenCLCGenerator(AsmAndAttributesMixin, CGeneratorBase):
    def visit_FileAST(self, n):
        s = ""
        from pycparserext.ext_c_parser import PreprocessorLine
        for ext in n.ext:
            if isinstance(ext, (c_ast.FuncDef, PreprocessorLine)):
                s += self.visit(ext)
            else:
                s += self.visit(ext) + ";\n"
        return s

    def visit_PreprocessorLine(self, n):
        return n.contents

# vim: fdm=marker
