
import pytest


# Inspired from pycparser's compare_asts test function
def _compare_asts(first, second):
    if type(first) is not type(second):
        return False

    if isinstance(first, tuple):
        if first[0] != second[0]:
            return False

        return _compare_asts(first[1], second[1])

    for attr in first.attr_names:
        if getattr(first, attr) != getattr(second, attr):
            return False

    for i, c1 in enumerate(first.children()):
        if not _compare_asts(c1, second.children()[i]):
            return False
    return True


def _round_trip_matches(src):
    from pycparserext.ext_c_generator import GnuCGenerator
    from pycparserext.ext_c_parser import GnuCParser

    p = GnuCParser()

    first_ast = p.parse(src)

    gen = GnuCGenerator().visit(first_ast)

    second_ast = p.parse(gen)

    if not _compare_asts(first_ast, second_ast):
        print("First AST:")
        first_ast.show()

        print("Generated code:")
        print(gen)

        print("Second AST:")
        second_ast.show()

        return False
    return True


def test_asm_volatile_1():
    src = """
    void read_tsc(void) {
        long val;
        asm("rdtsc" : "=A" (val));
    }    """
    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_asm_volatile_2():
    src = """
    void read_tsc(void) {
        long val;
        asm volatile("rdtsc" : "=A" (val));
    }    """
    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_asm_volatile_3():
    src = """
    void read_tsc(void) {
        long fpenv;
        asm("mtfsf 255,%0" :: "f" (fpenv));
    }    """
    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_asm_volatile_4():
    src = """
    void barrier(void) {
        __asm__ __volatile__("": : :"memory");
    }    """
    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_asm_label():
    src = """
    int foo asm("renamed_foo");

    unsigned long bar asm("renamed_bar") __attribute__ ((aligned (16)));

    unsigned long bar2 asm("renamed_bar2");

    unsigned int * bar3 asm("renamed_bar3");

    void func() {
        static int var asm("renamed_var") = 5;
    }
    """
    assert _round_trip_matches(src)


def test_register_asm_label():
    from pycparser import c_ast

    from pycparserext.ext_c_parser import GnuCParser, TypeDeclExt
    src = 'register int my_var asm("my_reg");'
    p = GnuCParser()
    ast = p.parse(src)
    decl = ast.ext[0]
    assert isinstance(decl, c_ast.Decl)

    # The asm attribute should be on the TypeDeclExt, not the Decl
    assert not hasattr(decl, "asm")

    # The declarator part of the Decl should be a TypeDeclExt
    # with the asm attribute.
    assert isinstance(decl.type, TypeDeclExt)
    assert hasattr(decl.type, "asm")
    assert decl.type.asm is not None
    assert decl.type.asm.template.value == '"my_reg"'

    # Test round-trip: the main issue in #33 was that no C code was generated
    assert _round_trip_matches(src)

    # Test with __asm__ variant
    src2 = 'register int foo __asm__("bar");'
    assert _round_trip_matches(src2)

    # Test with different types
    src3 = 'register unsigned int counter asm("r0");'
    assert _round_trip_matches(src3)


def test_pointer_with_attr():
    # https://github.com/inducer/pycparserext/issues/86
    src = "typedef float * __attribute__((abc)) b;"
    assert _round_trip_matches(src)


def test_funky_header_code():
    src = """
        extern __inline int __attribute__ ((__nothrow__)) __signbitf (float __x)
         {
           int __m;
           __asm ("pmovmskb %1, %0" : "=r" (__m) : "x" (__x));
           return __m & 0x8;
         }
        """

    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_funky_header_code_2():
    src = """
        extern __inline int __attribute__ ((__nothrow__)) __signbitf (float __x)
         {
           int __m;
           if (__x == 0)
              __asm ("pmovmskb %1, %0" : "=r" (__m) : "x" (__x));
           else
              __asm ("pmovmskb %1, %0" : "=r" (__m) : "x" (__x));
           return __m & 0x8;
         }
        """

    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_funky_header_code_3():
    src = """
        extern __inline int __attribute__ ((__nothrow__)) __signbitf (float __x)
         {
           int __m;
           if (__x == 0)
              __asm ("pmovmskb %1, %0" : "=r" (__m) : "x" (__x));
           return __m & 0x8;
         }
        """

    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_funky_header_code_4():
    src = """
        extern __inline int __attribute__ ((__nothrow__)) __signbitf (float __x)
         {
           int __m;
           if (__x == 0) {
              __asm ("pmovmskb %1, %0" : "=r" (__m) : "x" (__x));
           } else {
              __asm ("pmovmskb %1, %0" : "=r" (__m) : "x" (__x));
           }
           return __m & 0x8;
         }
        """

    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_funky_header_code_5():
    src = """ void  do_foo(void) __asm(__STRING(do_foo));"""

    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


@pytest.mark.parametrize("typename", ["int", "uint"])
def test_opencl(typename):
    from pycparserext.ext_c_parser import OpenCLCParser
    src = """
            __kernel void zeroMatrix(__global float *A, int n,  __global float * B)
            {
                %s i = get_global_id(0);
                for (int k=0; k<n; k++)
                    A[i*n+k] = 0;
            }
            """ % typename

    p = OpenCLCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import OpenCLCGenerator
    print(OpenCLCGenerator().visit(ast))


def test_array_attributes():
    src = """
        int x[10] __attribute__((unused));
        int y[20] __attribute((aligned(10)));
        """

    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_func_decl_attribute():
    src = """
    extern void int happy(void) __attribute__((unused));
    int main()
    {
    }
    """

    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_func_ret_ptr_decl_attribute():
    src = """
    extern void* memcpy(const void* src, const void *dst, int len)
    __attribute__((unused));
    """
    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_array_ptr_decl_attribute():
    src = """
    int* __attribute__((weak)) array[256];
    """
    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_gnu_statement_expression():
    src = """
      int func(int a) {
        return (int)({; ; *(int*)&a;});
     }
    """
    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()


def test_empty_gnu_statement_expression():
    # Incase, ASSERTS turn out to be empty statements
    src = """
      int func(int a) {
              ({
                    ; ;
                         });
                }
    """

    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_lvalue_gnu_statement_expression():
    src = """
      int func(int a) {
        int ret=(int)({; ; *(int*)&a;});
        return ret;
     }
    """

    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_gnu_extension_expression():
    src = """
      int func(int a) {
        int i = (4,__extension__ 2);
        char * name = __extension__ __PRETTY_FUNCTION__;
        i = __extension__ i++;
        i = __extension__((__extension__ i)++ + (--(__extension__ i)));
        return __extension__(int)__extension__({; ; i;});
     }
    """
    assert _round_trip_matches(src)


def test_empty_struct_declaration():
    src = """
        typedef struct Foo {
        } Foo_t;
    """

    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    print(GnuCGenerator().visit(ast))


def test_nesty_c_declarator():
    src = """
    struct a {
        int *b[1][1];
    };
    """

    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()


def test_const_ptr_func_arg():
    src = """
    const int *bar;
    void foo(const int *bar, int * const baz);
    """

    from pycparserext.ext_c_parser import GnuCParser
    p = GnuCParser()
    ast = p.parse(src)
    ast.show()

    from pycparserext.ext_c_generator import GnuCGenerator
    src_str = GnuCGenerator().visit(ast)

    assert src_str.count("*") == 3
    print(src_str)


def test_pointer_reproduction():
    src = """
    struct foo {
        const char                      *bar;
        const char                      *baz;
    };

    int main () {
        return 0;
    }
    """
    from pycparserext import ext_c_generator, ext_c_parser

    parser = ext_c_parser.GnuCParser()
    ast = parser.parse(src)
    gen = ext_c_generator.GnuCGenerator()
    print(gen.visit(ast))


def test_no_added_attr():
    src = """
    char* foo() {
        return "";
    }

    int main() {
        return 0;
    }
    """
    from pycparserext import ext_c_generator, ext_c_parser

    parser = ext_c_parser.GnuCParser()
    ast = parser.parse(src)
    gen = ext_c_generator.GnuCGenerator()
    print(gen.visit(ast))
    assert "attr" not in gen.visit(ast)


def test_double_pointer():
    src = """
    typedef struct Error {
        int dummy;
    } Error;

    void func_with_p2pp(const char *, Error **);
    """
    from pycparserext import ext_c_generator, ext_c_parser

    parser = ext_c_parser.GnuCParser()
    ast = parser.parse(src)
    gen = ext_c_generator.GnuCGenerator()
    ast.show()
    assert gen.visit(ast).find("func_with_p2pp(const char *, Error **)") != -1


def test_designated_initializers():
    src = """
    int a[6] = { [4] = 29, [2] = 15 };

    int widths[] = { [0 ... 9] = 1, [10 ... 99] = 2, [100] = 3 };

    int v1 = 5, v2 = 6;
    int b[] = { [1] = v1, v2, [4] = v4 };

    struct foo { int x; int y; };
    struct foo bar[10] = { [1].y = 5, [2].x = 1, [0].x = 3 };

    char char_map[256] = { [0 ... 255] = '?', ['0' ... '9'] = 'X' };
    """
    assert _round_trip_matches(src)


def test_case_ranges():
    src = """
    void f() {
        switch (1) {
            case 3:
                break;
            case 0 ... 5:
                break;
            case 'A' ... 'Z':
                break;
        }
    }
    """
    assert _round_trip_matches(src)


@pytest.mark.parametrize("restrict_kw", ["restrict", "__restrict__", "__restrict"])
def test_restrict(restrict_kw):
    src = """
    void f(int n, int * {0} p, int * {0} q)
    {{
    }}
    typedef int *array_t[10];
    {0} array_t a;
    void f(int m, int n, float a[{0} m][n], float b[{0} m][n]);
    """ .format(restrict_kw)
    assert _round_trip_matches(src)


def test_node_visitor():
    from pycparser.c_ast import NodeVisitor

    # key is type of visit, value is [actual #, expected #]
    visits = {
        "TypeList": [0, 1],
        # AttributeSpecifier is part of exprlist, not nodelist
        "AttributeSpecifier": [0, 0],
        "Asm": [0, 1],
        # PreprocessorLine is OpenCL, not GNU
        "PreprocessorLine": [0, 0],
        "TypeOfDeclaration": [0, 6],
        "TypeOfExpression": [0, 1],
        "FuncDeclExt": [0, 1],
    }

    class TestVisitor(NodeVisitor):
        def visit_TypeList(self, node):
            visits["TypeList"][0] += 1
            NodeVisitor.generic_visit(self, node)

        def visit_AttributeSpecifier(self, node):
            visits["AttributeSpecifier"][0] += 1
            NodeVisitor.generic_visit(self, node)

        def visit_Asm(self, node):
            visits["Asm"][0] += 1
            NodeVisitor.generic_visit(self, node)

        def visit_PreprocessorLine(self, node):
            visits["PreprocessorLine"][0] += 1
            NodeVisitor.generic_visit(self, node)

        def visit_TypeOfDeclaration(self, node):
            visits["TypeOfDeclaration"][0] += 1
            NodeVisitor.generic_visit(self, node)

        def visit_TypeOfExpression(self, node):
            visits["TypeOfExpression"][0] += 1
            NodeVisitor.generic_visit(self, node)

        def visit_FuncDeclExt(self, node):
            visits["FuncDeclExt"][0] += 1
            NodeVisitor.generic_visit(self, node)

    src_gnu = """
    int func1(int a, int b) {
        __typeof__(a) _a = __builtin_types_compatible_p(long char, short int);
        __typeof__ (__typeof__ (char *)[4]) y;
        typeof (typeof (char *)[4]) z;
        __typeof (__typeof (char *)[4]) g;
        asm("rdtsc" : "=A" (val));
        __attribute__((unused)) static int c;
    }
    """
    from pycparserext import ext_c_parser

    parser = ext_c_parser.GnuCParser()
    ast = parser.parse(src_gnu)
    ast.show()
    TestVisitor().visit(ast)
    for visit_type, visit_num in visits.items():
        assert_msg = "{}: Should have visited {}, got {}".format(
            visit_type, visit_num[1], visit_num[0])
        assert visit_num[0] == visit_num[1], assert_msg


def test_alignof():
    src = "int x = __alignof__(int);"
    assert _round_trip_matches(src)


def test_alignof_in_attribute():
    src = "long long z __attribute__((aligned(__alignof__(long long))));"
    assert _round_trip_matches(src)


def test_typeof_reproduction():
    src = """
    int func(int a, int b) {
        __typeof__(a) _a = a;
        typeof(b) _b = b;
        __typeof(c) _c = c;

        __typeof__ (__typeof__ (char *)[4]) y;
        typeof (typeof (char *)[4]) z;
        __typeof (__typeof (char *)[4]) g;
    }
    """
    assert _round_trip_matches(src)

    from pycparser.c_ast import NodeVisitor

    from pycparserext import ext_c_parser

    # key is type of visit, value is
    # [actual # __typeof__, expected # __typeof__,
    #   actual # typeof, expected # typeof,
    #   actual # __typeof, expected # __typeof
    # ]
    visits = {
        "TypeOfDeclaration": [0, 2, 0, 4],
        "TypeOfExpression": [0, 1, 0, 2],
    }

    class TestVisitor(NodeVisitor):
        def visit_TypeOfDeclaration(self, node):
            idx = 0 if node.typeof_keyword == "__typeof__" else 2
            visits["TypeOfDeclaration"][idx] += 1
            NodeVisitor.generic_visit(self, node)

        def visit_TypeOfExpression(self, node):
            idx = 0 if node.typeof_keyword == "__typeof__" else 2
            visits["TypeOfExpression"][idx] += 1
            NodeVisitor.generic_visit(self, node)

    parser = ext_c_parser.GnuCParser()
    ast = parser.parse(src)
    ast.show()
    TestVisitor().visit(ast)
    for visit_type, visit_num in visits.items():
        assert_msg = "{}: Should have visited ({}, {}), got ({}, {})".format(
            visit_type,
            visit_num[1], visit_num[3],
            visit_num[0], visit_num[2])
        assert visit_num[0] == visit_num[1] and \
               visit_num[2] == visit_num[3], assert_msg


def test_typedef():
    from pycparser import c_ast

    from pycparserext.ext_c_generator import GnuCGenerator
    from pycparserext.ext_c_parser import GnuCParser

    p = GnuCParser()

    first_ast = p.parse("typedef int foo;").ext[0]
    assert isinstance(first_ast, c_ast.Typedef)

    gen = GnuCGenerator().visit(first_ast.type)

    assert gen == "int"


def test_pointer_to_function_with_attribute():
    # https://github.com/inducer/pycparserext/issues/66
    src = "void (*f)(void) __attribute__((unused));"
    assert _round_trip_matches(src)


def test_packed_anonymous_struct_in_struct():
    from pycparser import c_ast

    from pycparserext.ext_c_parser import GnuCParser
    parser = GnuCParser()
    code = """
    struct foo_t {
        struct __attribute__((packed)) {
            int a;
            char b;
        };
    };
    """
    ast = parser.parse(code)
    assert isinstance(ast, c_ast.FileAST)
    assert len(ast.ext) == 1
    decl = ast.ext[0]
    assert isinstance(decl, c_ast.Decl)
    struct_foo = decl.type
    assert isinstance(struct_foo, c_ast.Struct)
    assert struct_foo.name == "foo_t"
    assert len(struct_foo.decls) == 1
    anon_struct_decl = struct_foo.decls[0]
    assert isinstance(anon_struct_decl, c_ast.Decl)
    anon_struct = anon_struct_decl.type
    assert isinstance(anon_struct, c_ast.Struct)
    assert anon_struct.name is None
    assert hasattr(anon_struct, "attrib")
    assert anon_struct.attrib is not None

    # Verify round-trip code generation
    assert _round_trip_matches(code)


def test_packed_anonymous_struct_in_struct_after():
    from pycparser import c_ast

    from pycparserext.ext_c_parser import GnuCParser
    parser = GnuCParser()
    code = """
    struct foo_t {
        struct {
            int a;
            char b;
        } __attribute__((packed));
    };
    """
    ast = parser.parse(code)
    assert isinstance(ast, c_ast.FileAST)
    assert len(ast.ext) == 1
    decl = ast.ext[0]
    assert isinstance(decl, c_ast.Decl)
    struct_foo = decl.type
    assert isinstance(struct_foo, c_ast.Struct)
    assert struct_foo.name == "foo_t"
    assert len(struct_foo.decls) == 1
    anon_struct_decl = struct_foo.decls[0]
    assert isinstance(anon_struct_decl, c_ast.Decl)
    anon_struct = anon_struct_decl.type
    assert isinstance(anon_struct, c_ast.Struct)
    assert anon_struct.name is None
    assert hasattr(anon_struct, "attrib")
    assert anon_struct.attrib is not None

    # Verify round-trip code generation
    assert _round_trip_matches(code)


def test_attribute_in_struct():
    # https://github.com/inducer/pycparserext/issues/75
    src = """
    typedef struct {
        __attribute__((__deprecated__)) int test1;
    } test2;
    """
    assert _round_trip_matches(src)


def _generate(src):
    from pycparserext.ext_c_generator import GnuCGenerator
    from pycparserext.ext_c_parser import GnuCParser

    return GnuCGenerator().visit(GnuCParser().parse(src))


def _generation_is_stable(src):
    gen = _generate(src)
    return _generate(gen) == gen


def test_attributes_between_struct_tag_and_declarator():
    # GCC rejects attributes between a tag and the members
    src = """
    struct s { int a; };
    static struct s __attribute__((aligned(8))) d;
    """
    assert _generation_is_stable(src)
    assert "__attribute__((aligned(8))) static struct s d;" in _generate(src)


def test_attributes_keep_arrays_and_functions():
    src = """
    int a[4] __attribute__((aligned(8)));
    char * __attribute__((deprecated)) f(char *buf);
    """
    assert _generation_is_stable(src)
    gen = _generate(src)
    assert "int a[4] __attribute__((aligned(8)));" in gen
    assert "char *f(char *buf)" in gen
    assert "__attribute__((deprecated))" in gen


def test_attributes_at_start_of_nested_declarators():
    src = """
    extern void *(__attribute__((__leaf__)) malloc)(unsigned long size);
    struct s { int (__attribute__((__cdecl__)) *read)(void *); };
    """
    assert _generation_is_stable(src)
    gen = _generate(src)
    assert "void *malloc(unsigned long size)" in gen
    assert "__attribute__((__leaf__))" in gen
    assert "int (*read)(void *) __attribute__((__cdecl__));" in gen


def test_attributes_of_functions_are_declaration_specifiers():
    # GCC rejects attributes after the declarator of a function definition
    src = """
    extern char *(__attribute__((__artificial__)) f)(char *buf);
    static void (__attribute__((always_inline)) g)(int x) { }
    """
    assert _generation_is_stable(src)
    gen = _generate(src)
    assert "__attribute__((__artificial__)) extern char *f(char *buf);" in gen
    assert "__attribute__((always_inline)) static void g(int x)" in gen


def test_attributes_of_unions_and_before_struct_tags():
    src = """
    union __attribute__((aligned(16))) u { int a; };
    typedef union __attribute__((aligned(16))) { int a; } v;
    struct __attribute__((packed)) s;
    """
    assert _generation_is_stable(src)
    gen = _generate(src)
    assert gen.count("union __attribute__((aligned(16)))") == 2
    assert "struct __attribute__((packed)) s;" in gen


def test_parameters_hide_typedefs_in_function_bodies():
    src = """
    typedef int T;
    int *f(int *T) { return T; }
    """
    assert _round_trip_matches(src)


def test_members_that_declare_nothing_are_ignored():
    from pycparserext.ext_c_parser import GnuCParser

    src = """
    typedef int T;
    struct s { int a; unsigned char ; unsigned T; };
    """
    ast = GnuCParser().parse(src)
    assert [d.name for d in ast.ext[1].type.decls] == ["a", "T"]


def test_attributes_after_struct_definitions_belong_to_type():
    src = """
    struct s { char c; int i; } __attribute__((packed)) x;
    """
    assert _generation_is_stable(src)
    assert "struct __attribute__((packed)) s" in _generate(src)


def test_attributes_of_struct_members():
    src = """
    struct o {
        struct { char c; int i; } __attribute__((packed)) a;
        int __attribute__((aligned(8))) b;
    };
    """
    assert _generation_is_stable(src)
    gen = _generate(src)
    assert "struct __attribute__((packed))" in gen
    assert "__attribute__((aligned(8))) int b;" in gen


def test_attributes_of_typedefs():
    src = """
    struct s { int a; };
    typedef struct s __attribute__((aligned(16))) t;
    """
    assert _generation_is_stable(src)
    assert "typedef struct s t __attribute__((aligned(16)));" in _generate(src)


def test_attributes_in_type_names():
    src = """
    char *f(void *p) { return (char __attribute__((deprecated)) *)p; }
    """
    assert _generation_is_stable(src)
    assert "(char __attribute__((deprecated)) *) p" in _generate(src)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        exec(sys.argv[1])
    else:
        from py.test.cmdline import main
        main([__file__])


def test_comments_are_skipped():
    from pycparserext.ext_c_parser import GnuCParser
    src = (
        "/* a\n"
        "   b */ int x; // c\n"
        "int y = 1 /* d */ + 2; // e \\\n"
        "continued\n"
        "int z;\n")
    x, y, z = GnuCParser().parse(src).ext
    assert (x.coord.line, x.coord.column) == (2, 13)
    assert (y.coord.line, y.coord.column) == (3, 5)
    assert (z.coord.line, z.coord.column) == (5, 5)

    with pytest.raises(Exception, match="Unterminated comment"):
        GnuCParser().parse("int x; /* a\n")


def test_physical_coords_ignore_line_markers():
    from pycparserext.ext_c_parser import GnuCParser
    src = (
        '# 1 "foo.c"\n'
        "int x;\n"
        '# 10 "bar.h" 1 3 4\n'
        "int y;\n"
        "#line 20\n"
        "int z;\n")
    x, y, z = GnuCParser().parse(src, filename="a.i", physical_coords=True).ext
    assert [d.coord.line for d in (x, y, z)] == [2, 4, 6]
    assert {d.coord.file for d in (x, y, z)} == {"a.i"}

    x, y, z = GnuCParser().parse(src, filename="a.i").ext
    assert [d.coord.line for d in (x, y, z)] == [1, 10, 20]
    assert [d.coord.file for d in (x, y, z)] == ["foo.c", "bar.h", "bar.h"]


def test_tokens_have_physical_positions():
    from pycparserext.ext_c_lexer import tokenize
    src = 'int /* c */ x = sizeof(y);\n# 5 "f.c"\n  return;'
    assert list(tokenize(src)) == [
        ("INT", "int", 1, 1),
        ("ID", "x", 1, 13),
        ("EQUALS", "=", 1, 15),
        ("SIZEOF", "sizeof", 1, 17),
        ("LPAREN", "(", 1, 23),
        ("ID", "y", 1, 24),
        ("RPAREN", ")", 1, 25),
        ("SEMI", ";", 1, 26),
        ("RETURN", "return", 3, 3),
        ("SEMI", ";", 3, 9),
    ]
    assert [t.line for t in tokenize(src, physical_coords=False)][-1] == 5


def test_gnu_spellings_of_keywords():
    from pycparserext.ext_c_generator import GnuCGenerator
    from pycparserext.ext_c_parser import GnuCParser
    src = (
        "__signed__ char a;\n"
        "__signed int b;\n"
        "int c = __alignof(long long) + __alignof__ b;\n")
    ast = GnuCParser().parse(src)
    a, b, c = ast.ext
    assert a.type.type.names == ["signed", "char"]
    assert b.type.type.names == ["signed", "int"]
    assert c.init.left.op == c.init.right.op == "__alignof__"
    code = GnuCGenerator().visit(ast)
    assert "__alignof__(long long)" in code
    assert "__alignof__(b)" in code
    assert _round_trip_matches(src)


def test_thread_local_storage():
    from pycparserext.ext_c_generator import GnuCGenerator
    from pycparserext.ext_c_parser import GnuCParser
    src = "static __thread int t;\nextern __thread int u;\n"
    ast = GnuCParser().parse(src)
    assert [d.storage for d in ast.ext] == [["static", "__thread"],
                                           ["extern", "__thread"]]
    assert GnuCGenerator().visit(ast) == src
