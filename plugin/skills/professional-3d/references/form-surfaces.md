# Form, sections and surface flow

Use for broad shells, asymmetric housings, tapered transitions or swept profiles. Inspect the reference silhouette, principal sections and likely next edit before choosing construction. A high resolution parameter grid is not automatically a good control surface.

## Choose a source

- **Section/guide construction:** when dimensions or an explicit section change control the design. Use a small set of informative stations at extrema, inflections and interface changes. Keep the station definitions and point correspondence. Blender has no assumed universal `loft` operator; use an available curve/node route or build a mesh with ordinary Python when that is the best fit.
- **Subdivision cage:** when a few broad shape decisions dominate. Start with even surface flow and enough rows to control the silhouette. Plan feature boundaries before poles. Keep high valence junctions away from visible high-curvature transitions when possible. A useful triangle or ngon on an appropriate flat region is preferable to forced quads that distort the surface.
- **Curve/sweep:** for a rail, seal, handle or cable whose section follows a path. Inspect orientation through bends, thickness, end attachments and a closed seam. Preserve the curve/profile and local orientation control.
- **Imported mesh:** edit its real topology or use a limited deformation. Do not pretend it has a procedural source. Rebuilding a whole surface is justified only when the existing representation cannot support the requested result.

## Section construction

Orient all profiles consistently in the same frame. Match their semantic landmarks, not just vertex counts: upper/lower extrema, seam positions and seating features should correspond. Check cyclic offset and winding explicitly. Uniform index pairing between a circle and a rounded rectangle can twist or bunch the transition even when both have the same sample count.

Interpolate shape with enough continuity for the intended surface. A tangent-continuous broad highlight is a separate question from positional continuity at a seam. Make the transition length large enough for the required change in section; adding loops to a physically abrupt contraction will not remove the fold. Retain a sparse source and derive denser geometry from it when useful.

Look at intermediate sections before generating the complete skin. Check order, local radii and the smallest distance between neighboring sections. A reversed ring, zero-radius station or collapsed correspondence is an input defect to correct before joining.

## Broad curvature and support

Build the crown and taper before openings and trim. Use smooth spacing changes; a sudden jump in edge spacing near a support loop often creates a visible dip. Derive support distance from the intended transition radius and subdivision result. Avoid extremely narrow double support loops merely to make a rendered edge sharp.

For a later crown change with a fixed rim, a smooth deformation weight that vanishes at the rim can preserve both position and boundary slope. Validate that behavior on the actual evaluated result, including thickness and dependent details. The [original enclosure example](../assets/curved_housing.py) uses a squared smooth implicit superellipse field, evaluated in retained Geometry Nodes. Its source supports build/edit in an existing Blender process and saves a separate native file. Study it when this representation fits the task; it is a development example, not an independently approved reference solution or a universal modeling API.

For a sweep, inspect how the profile rotates, especially near a path tangent parallel to its chosen up direction. Use the available curve tilt or node orientation controls. On a closed path, inspect the last/first frame seam; a locally smooth transport may still leave a closure twist.

## Observe, then accept

Use a neutral silhouette from at least two relevant orthographic directions, key sections and a grazing/highlight view. Check the evaluated mesh at the intended subdivision level. For a circular arc, chord error is `r * (1 - cos(theta / 2))`; use the required physical or screen-space error to choose density, rather than a fixed large segment count.

Good evidence: stable highlights, controlled section progression and a source that accepts the next shape change. Bad evidence: a beautiful material on a rippled shell or thousands of applied triangles with no retained shape control.

Development counterexamples: a short round-to-square contraction, an asymmetric shell with an offset crown, and a closed sweeping profile that accumulates twist. Test a crown/section change and an interface-size change separately. Do not use a global remesh on a dimension-critical thin shell without evaluating what it removes.
