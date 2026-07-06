from __future__ import annotations
import math
import itertools
from typing import Any, List, Dict, Callable, Tuple, Type, Set, FrozenSet, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

from parser import parse_ast, Statement, PointDecl, ComplexDecl, Assign, Expr, PointLiteral, ComplexLiteral, OpCall

# == Core Geometric Data Structures == #
@dataclass(frozen=True)
class Point:
    x: float
    y: float

@dataclass
class GeometricComplex:
    simplices: Set[FrozenSet[Point]]

    @property
    def vertices(self) -> Set[Point]:
        """Helper to extract all unique 0-simplices (vertices) from the complex."""
        verts = set()
        for simplex in self.simplices:
            verts.update(simplex)
        return verts

type EVal = Union[Point, GeometricComplex, int, float]
type DVal = Union[EVal, Operator]
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
    def apply(self, args: List[Any]) -> Union[Point, GeometricComplex]:
        if len(args) != len(self.arg_types):
            raise ValueError(f"Operator '{self.name}' expects {len(self.arg_types)} arguments, got {len(args)}")
        return self.fn(*args)

class ObservationalOperator(Operator):
    def apply(self, args: List[Any]) -> int:
        if len(args) != len(self.arg_types):
            raise ValueError(f"Operator '{self.name}' expects {len(self.arg_types)} arguments, got {len(args)}")
        return self.fn(*args)

# == Primitive Geometric Implementations == #
def translate_impl(target: Union[Point, GeometricComplex], offset: Point) -> Union[Point, GeometricComplex]:
    if isinstance(target, Point):
        return Point(target.x + offset.x, target.y + offset.y)
    
    elif isinstance(target, GeometricComplex):
        new_simplices = set()
        for simplex in target.simplices:
            new_simplex = frozenset(Point(p.x + offset.x, p.y + offset.y) for p in simplex)
            new_simplices.add(new_simplex)
        return GeometricComplex(new_simplices)
    raise TypeError("translate target must be a Point or GeometricComplex")

def scale_impl(target: Union[Point, GeometricComplex], factor: Union[int, float, Point]) -> Union[Point, GeometricComplex]:
    s = float(factor.x if isinstance(factor, Point) else factor)
    
    if isinstance(target, Point):
        return Point(target.x * s, target.y * s)
    
    elif isinstance(target, GeometricComplex):
        new_simplices = set()
        for simplex in target.simplices:
            new_simplex = frozenset(Point(p.x * s, p.y * s) for p in simplex)
            new_simplices.add(new_simplex)
        return GeometricComplex(new_simplices)
    raise TypeError("scale target must be a Point or GeometricComplex")

def rotate_impl(target: Union[Point, GeometricComplex], angle: Union[int, float, Point]) -> Union[Point, GeometricComplex]:
    deg = float(angle.x if isinstance(angle, Point) else angle)
    rad = math.radians(deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    
    def rot_pt(p: Point) -> Point:
        return Point(
            round(p.x * cos_a - p.y * sin_a, 6),
            round(p.x * sin_a + p.y * cos_a, 6)
        )

    if isinstance(target, Point):
        return rot_pt(target)
    
    elif isinstance(target, GeometricComplex):
        new_simplices = set()
        for simplex in target.simplices:
            new_simplex = frozenset(rot_pt(p) for p in simplex)
            new_simplices.add(new_simplex)
        return GeometricComplex(new_simplices)
    raise TypeError("rotate target must be a Point or GeometricComplex")

def union_impl(c1: GeometricComplex, c2: GeometricComplex) -> GeometricComplex:
    if not isinstance(c1, GeometricComplex) or not isinstance(c2, GeometricComplex):
        raise TypeError("union expects two GeometricComplex arguments")
    return GeometricComplex(c1.simplices | c2.simplices)

def dim_impl(c: GeometricComplex) -> int:
    if not isinstance(c, GeometricComplex):
        raise TypeError("dim expects a GeometricComplex argument")
    if not c.simplices:
        return -1
    return max(len(simplex) - 1 for simplex in c.simplices)

def num_vert_impl(c: GeometricComplex) -> int:
    if not isinstance(c, GeometricComplex):
        raise TypeError("num_vert expects a GeometricComplex argument")
    return len(c.vertices)

def initial_environment() -> Environment:
    env = empty_environment()

    # Constructive Transforms
    env = bind(env, "translate", ConstructiveOperator("translate", translate_impl, (object, Point), object))
    env = bind(env, "scale", ConstructiveOperator("scale", scale_impl, (object, (int, float, Point)), object))
    env = bind(env, "rotate", ConstructiveOperator("rotate", rotate_impl, (object, (int, float, Point)), object))
    env = bind(env, "union", ConstructiveOperator("union", union_impl, (GeometricComplex, GeometricComplex), GeometricComplex))

    # Observational Topologies
    env = bind(env, "dim", ObservationalOperator("dim", dim_impl, (GeometricComplex,), int))
    env = bind(env, "num_vert", ObservationalOperator("num_vert", num_vert_impl, (GeometricComplex,), int))

    env = bind(env, "difference", ConstructiveOperator("difference", difference_impl, (GeometricComplex, GeometricComplex), GeometricComplex))

    return env

# == EVALUATION ENGINE == #
def evaluate_expr(expr: Expr, env: Environment) -> EVal:
    """Evaluates geometric expressions down to raw runtime mathematical values."""
    
    # Primitive Numbers
    if isinstance(expr, (int, float)):
        return expr

    if isinstance(expr, str):
        val = lookup(env, expr)
        if isinstance(val, Operator):
            raise ValueError(f"Identifier '{expr}' references a system operator, not a value.")
        return val

    # Coordinate Tuples -> Point
    if isinstance(expr, PointLiteral):
        return Point(expr.x, expr.y)

    # Complex Simplices Literal List -> GeometricComplex
    if isinstance(expr, ComplexLiteral):
        points = []
        for v_name in expr.vertices:
            pt = lookup(env, v_name)
            if not isinstance(pt, Point):
                raise TypeError(f"Identifier '{v_name}' inside simplex list must evaluate to a Point.")
            points.append(pt)
        
        # Generate downward closure topology (every subset face of the simplex)
        simplices_set = set()
        for r in range(1, len(points) + 1):
            for combo in itertools.combinations(points, r):
                simplices_set.add(frozenset(combo))
                
        return GeometricComplex(simplices_set)

    # Operator Execution Matrix
    if isinstance(expr, OpCall):
        op = lookup(env, expr.op)
        if not isinstance(op, Operator):
            raise ValueError(f"'{expr.op}' is not an applicable operation.")
            
        arg_vals = [evaluate_expr(arg, env) for arg in expr.args]
        return op.apply(arg_vals)

    raise TypeError(f"Unknown geometric expression node type: {type(expr)}")

def execute_statement(stmt: Statement, env: Environment) -> Environment:
    """Executes a single declarative command line and safely re-binds the environment."""
    match stmt:
        case PointDecl(name, x, y):
            return bind(env, name, Point(x, y))

        case ComplexDecl(name, expr):
            val = evaluate_expr(expr, env)
            if not isinstance(val, GeometricComplex):
                raise TypeError(f"Expression for complex declaration '{name}' must evaluate to a GeometricComplex.")
            return bind(env, name, val)

        case Assign(name, expr):
            val = evaluate_expr(expr, env)
            return bind(env, name, val)

        case _:
            raise ValueError(f"Statement configuration '{type(stmt)}' is currently unrecognized.")


def eval_program(ast: list[Statement]) -> Environment:
    env = initial_environment()
    for stmt in ast:
        env = execute_statement(stmt, env)
    return env

# == API SERIALIZATION HELPER == #
def serialize_environment(env: Environment) -> dict:
    """Converts the active environment to the exact JSON schema the JS frontend expects."""
    complexes_json = {}
    
    for name, val in env.items():
        if isinstance(val, GeometricComplex):
            # 1. Map python Point objects to unique string identifiers (v0, v1, etc.)
            verts = list(val.vertices)
            pt_to_id = {pt: f"v{i}" for i, pt in enumerate(verts)}
            
            # 2. Extract coordinates
            coords_dict = {pt_to_id[pt]: [pt.x, pt.y] for pt in verts}
            
            # 3. Map frozen sets back to arrays of strings for JSON
            simplices_list = []
            for simplex in val.simplices:
                simplices_list.append([pt_to_id[pt] for pt in simplex])
                
            complexes_json[name] = {
                "coords": coords_dict,
                "simplices": simplices_list
            }
            
    return {"success": True, "complexes": complexes_json}