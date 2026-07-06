# Geometric DSL

A Domain-Specific Language (DSL) and interactive web-based environment for defining, transforming, and visualizing 2D geometric simplicial complexes. 

This project consists of a Python-based backend that parses and evaluates custom geometric syntax, alongside a frontend web IDE powered by Monaco Editor and Three.js for rendering the resulting topologies.

---

## Features

* **Custom Geometric Language:** Define points, construct simplicial complexes, and apply transformations using a clean, declarative syntax.
* **AST & Evaluator:** Built with `Lark` for parsing, featuring an execution engine that automatically generates downward closure topologies (subset faces) for simplices.
* **Constructive Operations:** Apply geometric transformations including `translate`, `scale`, `rotate`, and `union`.
* **Observational Operations:** Query topological properties like dimension (`dim`) and vertex count (`num_vert`).
* **Web IDE:** An in-browser editor using Monaco (the engine behind VS Code) with a built-in output panel.

---

## Language Syntax

The DSL allows you to declare points, group them into complexes, and apply functional transformations.

### Basic Example
```text
// Define points in 2D space
point p1 = (0.0, 0.0)
point p2 = (4.0, 0.0)
point p3 = (0.0, 3.0)

// Create a shape (simplicial complex)
complex triangle = [p1, p2, p3]

// Apply transformations
complex moved = translate(triangle, (5, 2))
complex scaled = scale(moved, 1.5)
```

### Supported Operation

* `translate(complex, (dx, dy))` - Move the complex by `(dx, dy)`.
* `scale(complex, factor)` - Scale the complex by a given factor.
* `rotate(complex, angle)` - Rotate the complex by a specified angle (in radians).
* `union(complex1, complex2)` - Combine two complexes into one.
* `difference(complex1, complex2)` - Subtract one complex from another.
* `num_vert(complex)` - Returns the number of unique vertices in the complex.

## Project Structure

### DSL 
* `core.py` - Contains the core logic for geometric operations and the evaluator.
* `parser.py` - Defines the grammar and parsing logic for the DSL.

### Frontend
* `index.html` - The main HTML file for the web IDE.
* `editor.js` - JavaScript logic for the Monaco Editor integration and output rendering.
* `visualization.js` - Handles the rendering of geometric complexes using Three.js.

## Setup and Installation

### Prerequisites
* Python 3.10+
* lark parsing library

### Installation

1. Clone the repository:
   ```bash
   git clone labcomp_project.git
    cd labcomp_project
```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the web server:
   ```bash
   uvicorn server:app --reload
   ```
