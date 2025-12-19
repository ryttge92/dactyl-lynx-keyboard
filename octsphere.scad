/*
Geodesic sphere with 3-axis polygon equators
Hemisphere too. Based on an octahedron, for regular polygon equators in all three axis planes
by Alex Matulich, February 2024

On Printables: https://www.printables.com/model/762498
On Thingiverse: https://www.thingiverse.com/thing:6481347

This code is based on my geodesic hemisphere - https://www.printables.com/model/129119 - which was a generalization of the Geodesic Sphere (icosahedral sphere) by Jamie Kawabata - https://www.thingiverse.com/thing:1484333

USAGE
-----
To use this, simply put this file in the directory where you keep .scad files, and include this line in your other .scad files:

use <octsphere.scad>

Modular syntax to make a sphere exactly like OpenSCAD sphere():

octsphere(<radius|r=radius|d=diameter> [, <$fa|$fs|$fn>=number]);

Adding the parameter hemisphere=true creates a hemisphere instead.

Functional syntax: You may call octsphere() as a function, which returns an array of polyhedron vertices and faces, any of the following ways:

ph_array = octsphere(radius);
ph_array = octsphere(r=radius);
ph_array = octsphere(d=diameter);

The parameter hemisphere=true can be included to create a hemisphere instead.

The above examples return an array with ph_array[0] being a list of 3D vertices and ph_array[1] being a list of faces. You can manipulate the vertices (saving everything in another vertex array) and call polyhedron(), passing the new vertex array and original face array as arguments. In this way you can create spheres with distortions.

The number of sides in the sphere's equator is controlled by the $fa, $fs, and $fn special variables; e.g. $fn=32 for a sphere with a 32-sided equator. It should not be necessary to go beyond $fn=128. Other values of $fn result in spheres having the nearest number of sides to 4, 8, 16, 32, 64, 128, ... 4*2^n. 

EXPLANATION
-----------
The default sphere in OpenSCAD is rendered as a circle rotated around a diameter. This results in a globe-shape with longitude and latitude edges, with many wasted facets concentrated at the poles. One can fix this problem by subdividing an icosahedron, resulting in a geodesic sphere with evenly-distributed faces. Such a sphere has no planar polygon equator, so it cannot be matched against other regular polygon shapes.

This code generates a geodesic sphere (or hemisphere) based on an octahedron. Unlike a sphere based on an icosahedron, using an octahedron results in flat equators in all three axis planes. These three equators are regular polygons that can match up with other regular polygon shapes (cylinders etc.).

Both the octahedral sphere and icosahedral sphere are limited in the number of sides available in the polygon equator if you cut it in half. An icosahedral sphere doesn't have an equator, but a horizontal cut results in a slightly smaller equator with 5*2^(n+1) sides (10, 20, 40, 80, 160), where n is the number of subdivision iterations (with n=0 being the original icosahedron). An octahedral sphere equator has the correct size and can have $fn=4*2^n sides (4, 8, 16, 32, 64, 128).

If you need a hemisphere with more flexibility in the number of sides, use my dedicated hemisphere() function instead, available at https://www.printables.com/model/129119
*/

// ---------- demo ----------

$fn=64;
color("lightgreen") octsphere(20);
translate([44, 0, 0]) color("pink") sphere(20);

// ---------- module: octahedral sphere or hemisphere ----------

module octsphere(r=-1, d=-1, hemisphere=false) {
    // get a subdivided octahedron
    os = octsphere(r, d, hemisphere);
    // render the sphere
    polyhedron(points=os[0], faces=os[1]);
}

// ---------- function: octahedral sphere or hemisphere ----------

function octsphere(r=-1, d=-1, hemisphere=false) = let(
    rad = r > 0 ? r : d > 0 ? d/2 : 1, //radius=1 by default
    fn = $fn ? $fn : max(360/$fa, 2*PI*rad/$fs),
    // given fn, figure out best root polygon and number of levels to subdivide
    log2 = log(2.0),
    logfn = log(fn),
    // pn=possible subdivision levels for polygon having number of sides = 4 * 2^pn
    pn = (logfn-log(4))/log2,
    // how far the provided number of vertices deviates from fn
    dpn = [ abs(4 * 2^floor(pn) - fn),
            abs(4 * 2^ceil(pn) - fn) ],
    minidx = floor(argmin(dpn)/2), // get closest match
    npoly = minidx + 4, // sides of root polygon
    levels = floor(pn) + argmin(dpn)%2, // subdivision levels
    nlv = 4 * 2^levels,
    //echo(requested = fn, got = npoly*2^levels, npoly = npoly);

    octahedron = [
        [   [0,0,1],  //0 up
            [0,1,0],    //1 north
            [0,-1,0],   //2 south
            [1,0,0],    //3 east
            [-1,0,0],   //4 west
            if (!hemisphere)
                [0,0,-1] //5 down - omitted if hemisphere=true
            ],
        hemisphere ?
            [[0,1,3], [0,3,2], [0,2,4], [0,4,1]]
            : [[0,1,3], [0,3,2], [0,2,4], [0,4,1], [5,3,1], [5,2,3], [5,4,2], [5,1,4]]
    ],
    divoct = multi_subdiv_pf(octahedron, levels), // subdivided octahedron
    // add bottom if we're doing a hemisphere
    vertices = hemisphere ?
        concat(divoct[0], [for(n=[0:nlv]) let(t=n*360/nlv) [cos(t), sin(t), 0]])
        : divoct[0],
    faces = hemisphere ? let(pstart=len(vertices)-nlv)
        concat(divoct[1], [[ for(n=[0:nlv-1]) pstart+n ]])
        : divoct[1]
    ) [ rad*vertices, faces ];

// ---------- support functions ----------

// adapted from https://www.thingiverse.com/thing:1484333 by Jamie Kawabata

// return the index of the minimum value in an array
function argmin(v, k=0, mem=[-1, ceil(1/0)]) = 
    (k == len(v)) ? mem[0] :
        v[k] < mem[1] ? argmin(v, k+1, [k, v[k]]) : 
        argmin(v, k+1, mem);

// polyhedron subdivision functions

// given two 3D points on the unit sphere, find the half-way point on the great circle (euclidean midpoint renormalized to be 1 unit away from origin)

function midpt(p1, p2) = 
    let(mid = 0.5 * (p1 +p2))
    mid / norm(mid);

// given a "struct" where pf[0] is vertices and pf[1] is faces, subdivide all faces into 4 faces by dividing each edge in half along a great circle (midpt function) and returns a struct of the same format, i.e. pf[0] is a (larger) list of vertices and pf[1] is a larger list of faces.

function subdivpf(pf) =
    let (p=pf[0], faces=pf[1])
    [ // for each face, output six points
        [ for (f=faces) 
            let (p0 = p[f[0]], p1 = p[f[1]], p2=p[f[2]]) 
            each
            [ p0, p1, p2, midpt(p0, p1), midpt(p1, p2), midpt(p0, p2) ]
        ],
    // now, again for each face, output four faces that connect those six points
        [ for (i=[0:len(faces)-1])
            let (base = 6*i)  // points generated in multiples of 6
            each
            [[base, base+3, base+5], 
             [base+3, base+1, base+4],
             [base+5, base+4, base+2],
             [base+3, base+4, base+5]
            ]
        ]
    ];

// recursive wrapper for subdivpf that subdivides "levels" times
function multi_subdiv_pf(pf, levels) =
    levels == 0 ? pf :
    multi_subdiv_pf(subdivpf(pf), levels-1);
