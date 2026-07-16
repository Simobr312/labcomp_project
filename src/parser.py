from __future__ import annotations
from lark import Lark, Token, Tree
from dataclasses import dataclass
from typing import List, Union

# Define operations explicitly
defined_operations = {"translate", "rotate", "scale", "dim", "num_vert", "union", "boundary", "star"}
op_regex = "|".join(defined_operations)

# Parser grammar
grammar = fr"""
    program: statement*

    ?statement: point_decl
              | complex_decl
              | assign
              | render_stmt
              | func_decl
              | return_stmt

    point_decl: "point" IDENT "=" tuple_coord
    complex_decl: "complex" IDENT "=" expr
    assign: IDENT "=" expr
    render_stmt: "render" IDENT
    func_decl: "function" IDENT "(" param_list ")" "{{" statement* "}}"
    return_stmt: "return" expr

    ?expr: op_call
        | func_call
        | IDENT
        | vertices_list
        | tuple_coord
        | NUMBER 
        | "(" expr ")"

    op_call: OP "(" arg_list? ")"
    func_call: expr "(" call_args ")" 
    
    tuple_coord: "(" expr ("," expr)+ ")"
    vertices_list: "[" id_list "]"
    id_list: IDENT ("," IDENT)*
    arg_list: expr ("," expr)*
    param_list: (IDENT ("," IDENT)*)?
    call_args: (expr ("," expr)*)?

    OP: /\b{op_regex}\b/

    IDENT: /[A-Za-z_][A-Za-z0-9_]*/
    
    NUMBER: /-?[0-9]+(\.[0-9]+)?/

    COMMENT: "//" /[^\n]/* "\n"
    %ignore COMMENT
    WS: /[ \t\f\r\n]+/
    %ignore WS
"""

# == Abstract Syntax Tree == #
type Ref = str

@dataclass
class NumberLiteral:
    value: float

@dataclass
class PointLiteral:
    coords: List[Expr]

@dataclass
class ComplexLiteral:
    vertices: List[Ref]  

@dataclass
class OpCall:
    op: str
    args: List["Expr"]

@dataclass
class FuncCall:
    caller: Expr
    args: List["Expr"]

Expr = Ref | PointLiteral | ComplexLiteral | OpCall | FuncCall | NumberLiteral

# == Statements == #
@dataclass
class PointDecl:
    name: str
    coords: List[Expr]

@dataclass
class ComplexDecl:
    name: str
    expr: Expr

@dataclass
class Assign:
    name: str
    expr: Expr

@dataclass
class RenderStmt:
    name: str

@dataclass
class FunctionDecl:
    name: str
    params: List[str]
    body: List["Statement"]

@dataclass
class ReturnStmt:
    expr: Expr

Statement = PointDecl | ComplexDecl | Assign | RenderStmt | FunctionDecl | ReturnStmt
Program = List[Statement]

# == Tree Transformers == #
def transform_expr_tree(tree) -> Expr:
    match tree:
        case Tree("tuple_coord", coords):
            return PointLiteral([transform_expr_tree(c) for c in coords])
        
        case Tree("vertices_list", [id_list]):
            children = id_list.children if isinstance(id_list, Tree) else id_list
            return ComplexLiteral([tok.value for tok in children])

        case Tree("op_call", [Token("OP", op), arg_list]):
            children = arg_list.children if isinstance(arg_list, Tree) else arg_list
            args = [transform_expr_tree(a) for a in children]
            return OpCall(op, args)
            
        case Tree("op_call", [Token("OP", op)]):
            return OpCall(op, [])

        case Tree("func_call", [caller_node, call_args]):
            # Dynamically transform the caller side of the expression
            caller = transform_expr_tree(caller_node)
            children = call_args.children if isinstance(call_args, Tree) else call_args
            args = [transform_expr_tree(a) for a in children]
            return FuncCall(caller, args)

        case Token("IDENT", name):
            return name

        case Token("NUMBER", value):
            return NumberLiteral(float(value))

        case Tree("expr", [sub]):
            return transform_expr_tree(sub)

        case _:
            raise ValueError(f"Unexpected expression tree: {tree}")

        
def transform_statement_tree(tree) -> Statement:
    match tree:
        case Tree("point_decl", [Token("IDENT", name), Tree("tuple_coord", coords)]):
            return PointDecl(name, [transform_expr_tree(c) for c in coords])

        case Tree("complex_decl", [Token("IDENT", name), expr]):
            return ComplexDecl(name, transform_expr_tree(expr))

        case Tree("assign", [Token("IDENT", name), expr]):
            return Assign(name, transform_expr_tree(expr))

        case Tree("render_stmt", [Token("IDENT", name)]):
            return RenderStmt(name)

        case Tree("func_decl", [Token("IDENT", name), param_list, *body_nodes]):
            children = param_list.children if isinstance(param_list, Tree) else param_list
            params = [tok.value for tok in children if isinstance(tok, Token)]
            body = [transform_statement_tree(b) for b in body_nodes]
            return FunctionDecl(name, params, body)

        case Tree("return_stmt", [expr]):
            return ReturnStmt(transform_expr_tree(expr))

        case _:
            raise ValueError(f"Unexpected statement tree: {tree}")

def parse_ast(source_code: str) -> Program:
    parser = Lark(grammar, start="program", parser="lalr")
    tree = parser.parse(source_code)
    return [transform_statement_tree(stmt) for stmt in tree.children]