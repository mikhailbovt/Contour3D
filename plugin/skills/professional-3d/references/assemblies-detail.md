# Assemblies, interfaces and purposeful detail

Use for technical assemblies, furniture, architectural props and repeated detail groups. Start with a part/interface map: which pieces carry structure, which mate, which move, and which are cosmetic. The model should explain its construction at the requested viewing distance.

## Interface before ornament

Set datums, mating dimensions, fastening planes and clearances. Choose a specific reference for each interface. A panel can change crown while its mounting plane stays fixed; those are separate constraints. Keep related dependencies in shared sources or explicit relationships rather than recomputing them from scattered world coordinates.

Build a seam from two coherent neighboring edges and a purposeful gap. Do not substitute a dark strip over overlapping surfaces. Decide whether a joint is welded, molded, fastened or assembled, and use the resulting edge radius, part boundary and thickness consistently. Visual plausibility does not certify an engineering design.

For furniture, check load path, joinery, support thickness and attachment of secondary pieces. For architectural trim, check how a repeated profile terminates at corners and openings. For technical panels, check access, assembly sequence and visible fastening logic to the degree the brief needs.

## Repeats that survive edits

Define the repeat group in a useful placement coordinate system: surface coordinates, an available curve, a host transform or an existing procedural node input. Use linked geometry/instances where beneficial; make individual geometry unique only when an individual change requires it.

Pitch, end margins and count are different design decisions. Decide which is fixed when the host changes size. For a tapered or curved host, inspect orientation and penetration at both ends and the highest-curvature position. A regular pattern in world XY can look irregular on the visible surface.

Use screen/physical scale to choose bolt, cable and trim resolution. Small rounds on a distant prop do not need the same density as a silhouette-critical grip. If the brief includes a game budget, allocate it across primary silhouette, visible secondary forms and close-up detail before tessellation. Low triangle count is not intrinsically a good model.

## Sources and sharing

Keep the main cage/curve, repeat source and important parameter controls. Label construction sources according to their actual role; unnecessary naming of every minor part burdens later work. Do not flatten useful modifiers just to obtain a preview or export copy.

Inspect shared materials and node groups before a local detail change. A color or roughness edit on one assembly can propagate to every linked user. A protected neighbor requires either an intentional shared change or a local single-user copy, followed by checks.

## Acceptance and changes

Inspect fit, seam continuity, panel thickness, contact and moving envelopes where relevant. Test one change to the host shape and another to repeat pitch or interface dimensions. Include the extremes of the changed assembly rather than only its middle.

Good: a repeated fastening group remains seated when the host changes. Bad: floating bolts, arbitrary glowing strips and hidden overlapping flanges counted as greater detail.

Counterexamples: closely packed fasteners on a short edge; a curved gasket whose offset self-intersects; an assembly with intentionally open sheet edges. Do not demand manifold closure of every construction surface. Development coverage should include a service panel, a bracketed assembly and a furniture joint rather than three sizes of one box.
