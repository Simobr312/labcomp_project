point p1 = (0.0, 0.0)
point p2 = (4.0, 0.0)
point p3 = (2.0, 3.464)

complex t1 = [p1, p2, p3]

complex t2 = translate(t1, (4.0, 0.0))
complex t3 = translate(t1, (2.0, 3.464))

complex bottom_row = union(t1, t2)
complex triforce = union(bottom_row, t3)

complex mini_triforce = scale(triforce, 0.4)
complex floating_mini = translate(mini_triforce, (-6.0, 4.0))
complex spun_mini = rotate(floating_mini, 75)

complex entire_scene = union(triforce, spun_mini)