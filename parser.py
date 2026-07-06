from lark import Lark, Token, Tree
from dataclasses import dataclass
from typing import List, Union

# Define operations explicitly
defined_operations = {"translate", "rotate", "scale", "dim", "num_vert", "union"}
op_regex = "|".join(defined_operations)

# Parser grammar (Updated)
grammar = fr"""
    program: statement*

    ?statement: point_decl
              | complex_decl
              | assign

    point_decl: "point" IDENT "=" tuple_coord
    complex_decl: "complex" IDENT "=" expr
    assign: IDENT "=" expr

    ?expr: op_call
        | IDENT
        | vertices_list
        | tuple_coord
        | NUMBER              // <--- ADD THIS LINE HERE
        | "(" expr ")"

    op_call: OP "(" arg_list? ")"
    
    tuple_coord: "(" NUMBER "," NUMBER ")"
    vertices_list: "[" id_list "]"
    id_list: IDENT ("," IDENT)*
    arg_list: expr ("," expr)*

    OP: /{op_regex}/
    IDENT: /[A-Za-z_][A-Za-z0-9_]*/
    
    NUMBER: /-?[0-9]+(\.[0-9]+)?/

    COMMENT: "//" /[^\n]/* "\n"
    %ignore COMMENT
    WS: /[ \t\f\r\n]+/
    %ignore WS
"""

# == Abstract Syntax Tree (AST) Nodes == #

type Ref = str

@dataclass
class PointLiteral:
    x: float
    y: float

@dataclass
class ComplexLiteral:
    vertices: List[Ref]  # List of point identifiers making up the complex

@dataclass
class OpCall:
    op: str
    args: List["Expr"]

Expr = Ref | PointLiteral | ComplexLiteral | OpCall

# == Statements == #

@dataclass
class PointDecl:
    name: str
    x: float
    y: float

@dataclass
class ComplexDecl:
    name: str
    expr: Expr

@dataclass
class Assign:
    name: str
    expr: Expr

Statement = PointDecl | ComplexDecl | Assign
Program = List[Statement]

# == Tree Transformers == #

def transform_expr_tree(tree) -> Expr:
    match tree:
        case Tree("tuple_coord", [Token("NUMBER", x), Token("NUMBER", y)]):
            return PointLiteral(float(x), float(y))

        case Tree("vertices_list", [id_list]):
            return ComplexLiteral(
                [tok.value for tok in id_list.children]
            )

        case Tree("op_call", [Token("OP", op), arg_list]):
            args = [transform_expr_tree(a) for a in arg_list.children]
            return OpCall(op, args)
            
        case Tree("op_call", [Token("OP", op)]):
            return OpCall(op, [])

        case Token("IDENT", name):
            return name

        case Token("NUMBER", value):
            return PointLiteral(float(value), 0.0)  # Safe fallback for raw scalar args (e.g. scaling factor)

        case Tree("expr", [sub]):
            return transform_expr_tree(sub)

        case _:
            raise ValueError(f"Unexpected expression tree: {tree}")

        
def transform_statement_tree(tree) -> Statement:
    match tree:
        case Tree("point_decl", [Token("IDENT", name), Tree("tuple_coord", [Token("NUMBER", x), Token("NUMBER", y)])]):
            return PointDecl(name, float(x), float(y))

        case Tree("complex_decl", [Token("IDENT", name), expr]):
            return ComplexDecl(name, transform_expr_tree(expr))

        case Tree("assign", [Token("IDENT", name), expr]):
            return Assign(name, transform_expr_tree(expr))

        case _:
            raise ValueError(f"Unexpected statement tree: {tree}")


def parse_ast(source_code: str) -> Program:
    parser = Lark(grammar, start="program")
    tree = parser.parse(source_code)
    return [
        transform_statement_tree(stmt)
        for stmt in tree.children
    ]