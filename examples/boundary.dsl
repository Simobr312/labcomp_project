// Define a triangle
point p1 = (0.0, 0.0)
point p2 = (4.0, 0.0)
point p3 = (0.0, 4.0)
complex solid_triangle = [p1, p2, p3]

// The boundary operator drops the top-dimensional face (the 2D filled area)
// leaving only the 1D edges and 0D vertices.
complex triangle_outline = boundary(solid_triangle)