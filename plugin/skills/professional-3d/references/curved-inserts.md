# Openings, bezels and seams on curved surfaces

Use for a framed opening, vent group, inset panel or seam on a curved shell. First identify the host surface, intended contact line, mounting clearance and the visible highlight path. Treat the host's crown and the insert's seating geometry as separate decisions.

## Choose integrated or separate construction

A separate trim/insert is often appropriate when the real part is assembled, has a material boundary, or needs independent replacement. Preserve the host surface underneath only where real assembly permits it. Do not hide an interpenetration beneath trim and call it fitted.

An integrated opening is appropriate when the skin itself is cut, folded or molded. Resolve how the boundary joins the surrounding flow. On a high-curvature reflective surface, route topology around the aperture; avoid placing a pole or abrupt support-density change at its tightest visible corner.

A Boolean may establish the aperture efficiently. Inspect the resulting boundary, small sliver faces and shading before accepting it. Keep the Boolean/cleanup source where the next aperture edit benefits from it. Boolean success alone says nothing about the surrounding highlight.

## Build the interface

Record actual units for thickness, insertion depth, gap and edge radius. Seat the insert on the evaluated host surface. A constant world-height offset does not produce constant spacing on a curved surface. For surface offset construction, check the direction of the local normal and the effect of sharp curvature; offset surfaces can intersect themselves.

Use a continuous rounded corner where the intended shape calls for one. A rectangle with densely subdivided straight edges still has sharp corners. Provide enough transition room around the aperture; if feature spacing is too tight for two radii and a land, adjust the design instead of increasing subdivisions.

Separate the external bezel, actual opening, inner return and any gasket as needed. Make the rear of the part coherent in views where it is visible. Keep a consistent seam treatment across adjacent panels. A curved panel is not a flat sheet with a rectangular object placed at its average height.

## Repeated vents

Establish the group's envelope and pitch on the surface, then create repeats. Preserve the host crown; the repeats should follow the intended placement frame rather than independently projecting into unstable orientations. Verify the first and last vents, the tightest curvature and the wall left between adjacent cuts.

Decide whether vent depth affects silhouette or a likely close-up. A normal/bake may be enough at distance; a through opening needs geometry when the interior is visible. Avoid cutting tiny slits into the primary cage if it causes more visible rippling than the feature contributes.

## Checks and later edits

Inspect clay, wireframe and a grazing reflection along the long edges and corners. Measure seating gap, remaining wall and boundary alignment at several locations, including curvature extrema. Report sampled checks as sampled; they are not exhaustive collision proof.

After a crown change, re-evaluate insert placement and aperture shape. If the rim is protected, drive the crown edit with a weight that dies smoothly outside the permitted zone. If the aperture changes, deliberately propagate it to the bezel, return and dependent fasteners.

Good: a fitted insert whose corners retain the host highlight. Bad: a flat bezel floating above a crowned skin, or a visually smooth close-up hiding sliver triangles around a cut.

Counterexample: a deep, tight corner on a thin, sharply curved shell. Treat excessive offset, collapsed support loops or insufficient remaining wall as design/representation problems. Validate on a rounded enclosure, a shallow double-curved panel and a strongly tapered shroud; include both aperture and crown changes.
