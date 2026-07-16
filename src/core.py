from __future__ import annotations
from ast import expr
import math
import itertools
from typing import Any, List, Dict, Callable, Tuple, Type, Set, FrozenSet, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Updated imports to match modifications in parser
from src.parser import NumberLiteral, Statement, PointDecl, ComplexDecl, Assign, Expr, PointLiteral, ComplexLiteral, OpCall, RenderStmt, FunctionDecl, ReturnStmt, FuncCall

# == Core Geometric Data Structures == #
@dataclass(frozen=True)
class Point:
    coords: Tuple[float, ...]

    @property
    def x(self) -> float:
        return self.coords[0] if len(self.coords) > 0 else 0.0

    @property
    def y(self) -> float:
        return self.coords[1] if len(self.coords) > 1 else 0.0

@dataclass
class Complex:
    simplices: Set[FrozenSet[Point]]

    @property
    def vertices(self) -> Set[Point]:
        verts = set()
        for simplex in self.simplices:
            verts.update(simplex)
        return verts

@dataclass
class Closure:
    function: FunctionDecl
    env: Environment

class ReturnException(Exception):
    def __init__(self, value: EVal):
        self.value = value

type Geometric = Point | Complex
type Num = int | float
type EVal = Geometric | Num | Closure | None
type DVal = EVal | Operator | Closure

type Environment = Dict[str, DVal]

# == Environment Management == #
def empty_environment() -> Environment:
    return {}

def bind(env: Environment, name: str, value: DVal) -> Environment:
    new_env = env.copy()
    new_env[name] = value
    return new_env

def lookup(env: Environment, name: str) -> DVal:
    if name in env:
        return env[name]
    raise KeyError(f"Identifier '{name}' not found in environment")

# == Operator Definitions == #
@dataclass(frozen=True)
class Operator(ABC):
    name: str
    fn: Callable
    arg_types: Tuple[Union[Type, Tuple[Type, ...]], ...]
    ret_type: Type

    @abstractmethod
    def apply(self, args: list[Any]) -> Any:
        pass

class ConstructiveOperator(Operator):
    def apply(self, args: List[Any]) -> Union[Point, Complex]:
        if len(args) != len(self.arg_types):
            raise ValueError(f"Operator '{self.name}' expects {len(self.arg_types)} arguments, got {len(args)}")
        return self.fn(*args)

class ObservationalOperator(Operator):
    def apply(self, args: List[Any]) -> int:
        if len(args) != len(self.arg_types):
            raise ValueError(f"Operator '{self.name}' expects {len(self.arg_types)} arguments, got {len(args)}")
        return self.fn(*args)

# == Primitive Geometric Implementations == #
def translate_impl(target: Geometric, offset: Point) -> Geometric:
    def trans_pt(p: Point) -> Point:
        # zip_longest handles dimension mismatches by padding with 0.0
        new_coords = tuple(a + b for a, b in itertools.zip_longest(p.coords, offset.coords, fillvalue=0.0))
        return Point(new_coords)

    if isinstance(target, Point):
        return trans_pt(target)
    elif isinstance(target, Complex):
        new_simplices = {frozenset(trans_pt(p) for p in simplex) for simplex in target.simplices}
        return Complex(new_simplices)
    raise TypeError("translate target must be a Point or Complex")

def scale_impl(target: Geometric, factor: Union[int, float]) -> Union[Point, Complex]:
    s = float(factor)
    def scale_pt(p: Point) -> Point:
        return Point(tuple(c * s for c in p.coords))

    if isinstance(target, Point):
        return scale_pt(target)
    elif isinstance(target, Complex):
        new_simplices = {frozenset(scale_pt(p) for p in simplex) for simplex in target.simplices}
        return Complex(new_simplices)
    raise TypeError("scale target must be a Point or Complex")

def rotate_impl(target: Geometric, angle: Num | Point) -> Geometric:
    deg = float(angle.coords[0] if isinstance(angle, Point) else angle)
    rad = math.radians(deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    
    def rot_pt(p: Point) -> Point:
        if len(p.coords) < 2:
            return p # Cannot rotate 1D points
            
        new_x = round(p.coords[0] * cos_a - p.coords[1] * sin_a, 6)
        new_y = round(p.coords[0] * sin_a + p.coords[1] * cos_a, 6)
        return Point((new_x, new_y) + p.coords[2:])

    if isinstance(target, Point):
        return rot_pt(target)
    elif isinstance(target, Complex):
        new_simplices = {frozenset(rot_pt(p) for p in simplex) for simplex in target.simplices}
        return Complex(new_simplices)
    raise TypeError("rotate target must be a Point or Complex")

def boundary_impl(c: Complex) -> Complex:
    if not isinstance(c, Complex):
        raise TypeError("boundary expects a Complex argument")
    max_dim = dim_impl(c)
    b_simplices = {s for s in c.simplices if len(s) - 1 < max_dim}
    return Complex(b_simplices)

def star_impl(sub_c: Complex, entire_c: Complex) -> Complex:
    star_simplices = set()
    for s_entire in entire_c.simplices:
        for s_sub in sub_c.simplices:
            if s_sub.issubset(s_entire):
                star_simplices.add(s_entire)
                break
    return Complex(star_simplices)

def union_impl(c1: Complex, c2: Complex) -> Complex:
    if not isinstance(c1, Complex) or not isinstance(c2, Complex):
        raise TypeError("union expects two Complex arguments")
    return Complex(c1.simplices | c2.simplices)

def dim_impl(c: Complex) -> int:
    if not isinstance(c, Complex):
        raise TypeError("dim expects a Complex argument")
    if not c.simplices:
        return -1
    return max(len(simplex) - 1 for simplex in c.simplices)

def num_vert_impl(c: Complex) -> int:
    if not isinstance(c, Complex):
        raise TypeError("num_vert expects a Complex argument")
    return len(c.vertices)

def initial_environment() -> Environment:
    env = empty_environment()
    env = bind(env, "translate", ConstructiveOperator("translate", translate_impl, (object, Point), object))
    env = bind(env, "scale", ConstructiveOperator("scale", scale_impl, (object, (int, float, Point)), object))
    env = bind(env, "rotate", ConstructiveOperator("rotate", rotate_impl, (object, (int, float, Point)), object))
    env = bind(env, "union", ConstructiveOperator("union", union_impl, (Complex, Complex), Complex))
    env = bind(env, "boundary", ConstructiveOperator("boundary", boundary_impl, (Complex,), Complex))
    env = bind(env, "star", ConstructiveOperator("star", star_impl, (Complex, Complex), Complex))
    env = bind(env, "dim", ObservationalOperator("dim", dim_impl, (Complex,), int))
    env = bind(env, "num_vert", ObservationalOperator("num_vert", num_vert_impl, (Complex,), int))
    return env

# == EVALUATION ENGINE == #
def evaluate_expr(expr: Expr, env: Environment) -> EVal:
    if isinstance(expr, (int, float)):
        return expr

    if isinstance(expr, str):
        val = lookup(env, expr)
        return val

    if isinstance(expr, PointLiteral):
        eval_coords = [evaluate_expr(c, env) for c in expr.coords]
        if not all(isinstance(c, (int, float)) for c in eval_coords):
            raise TypeError("Point coordinates must evaluate to numeric values.")
        return Point(tuple(float(c) for c in eval_coords))

    if isinstance(expr, NumberLiteral):
        return expr.value

    if isinstance(expr, ComplexLiteral):
        points = []
        for v_name in expr.vertices:
            pt = lookup(env, v_name)
            if not isinstance(pt, Point):
                raise TypeError(f"Identifier '{v_name}' inside simplex list must evaluate to a Point.")
            points.append(pt)
        
        simplices_set = set()
        for r in range(1, len(points) + 1):
            for combo in itertools.combinations(points, r):
                simplices_set.add(frozenset(combo))
                
        return Complex(simplices_set)

    if isinstance(expr, OpCall):
        op = lookup(env, expr.op)
        if not isinstance(op, Operator):
            raise ValueError(f"'{expr.op}' is not an applicable operation.")
            
        arg_vals = [evaluate_expr(arg, env) for arg in expr.args]
        return op.apply(arg_vals)

    if isinstance(expr, FuncCall):
        # 1. Dynamically evaluate the caller to get the callable object
        callable_obj = evaluate_expr(expr.caller, env)
        
        # Support calling system operators via FuncCall syntax as well
        if isinstance(callable_obj, Operator):
            arg_vals = [evaluate_expr(arg, env) for arg in expr.args]
            return callable_obj.apply(arg_vals)
            
        if not isinstance(callable_obj, Closure):
            raise ValueError(f"Expression is not a callable function.")
            
        arg_vals = [evaluate_expr(arg, env) for arg in expr.args]
        if len(arg_vals) != len(callable_obj.function.params):
            raise ValueError(f"Function '{callable_obj.function.name}' expects {len(callable_obj.function.params)} arguments, got {len(arg_vals)}")
            
        local_env = callable_obj.env
        local_env = bind(local_env, callable_obj.function.name, callable_obj)
        for param, val in zip(callable_obj.function.params, arg_vals):
            local_env = bind(local_env, param, val)
            
        try:
            for body_stmt in callable_obj.function.body:
                local_env = execute_statement(body_stmt, local_env)
            return None
        except ReturnException as e:
            return e.value

    raise TypeError(f"Unknown geometric expression node type: {type(expr)}")

def execute_statement(stmt: Statement, env: Environment) -> Environment:
    match stmt:
        case PointDecl(name, coords):
            eval_coords = [evaluate_expr(c, env) for c in coords]
            if not all(isinstance(c, (int, float)) for c in eval_coords):
                raise TypeError("Point coordinates must evaluate to numeric values.")
            return bind(env, name, Point(tuple(float(c) for c in eval_coords)))
        
        case ComplexDecl(name, expr):
            val = evaluate_expr(expr, env)
            if not isinstance(val, Complex):
                raise TypeError(f"Expression for complex declaration '{name}' must evaluate to a Complex.")
            return bind(env, name, val)

        case Assign(name, expr):
            val = evaluate_expr(expr, env)
            return bind(env, name, val)

        case RenderStmt(name):
            if name not in env:
                raise KeyError(f"Render target '{name}' is not defined in the current environment.")
            render_targets = env.get("__render_targets__", set())
            render_targets.add(name)
            return bind(env, "__render_targets__", render_targets)

        case FunctionDecl(name, params, body):
            closure = Closure(stmt, env)
            return bind(env, name, closure)

        case ReturnStmt(expr):
            val = evaluate_expr(expr, env)
            raise ReturnException(val)

        case _:
            raise ValueError(f"Statement configuration '{type(stmt)}' is currently unrecognized.")
        
def eval_program(ast: list[Statement]) -> Environment:
    env = initial_environment()
    for stmt in ast:
        env = execute_statement(stmt, env)
    return env