/*
Dual ball joint mount - AKA "RAM" mount
by Alex Matulich
March 2023

On Printables: https://www.printables.com/model/807048
On Thingiverse: https://www.thingiverse.com/thing:6534276

I made this because I wanted something that could have a different ball on each end, and structurally stiffer than other designs I've seen. I also included a knob for the bolt, so the mount can be tightened with fingers.
*/

use <octsphere.scad>


// ---------- Customizer parameters ----------

// what to display
display = "print"; //[print, assembly]
// diameter of ball 1
ball1_dia = 18;
// diameter of ball 2
ball2_dia = 18;
// diameter of clamping bolt
bolt_dia = 6;  //[4,5,6,8,10,12,14]
// minimum spacing between ball centers - smaller=stronger, 0=strongest
ball_spacing = 0;
// percent of ball diameter for gap between mount halves
gap_pct = 15;
// handle spacer height
handle_offset = 5;
// clearance around bolt and nut
boltclearance = 0.21;
// total diameter clearance for best fit of ball
ballclearance = 0.15;
// cone to sweep out from end of ball joint for pivoting
end_sweep = 100;    //[80:10:120]
// long channel to sweep from end of ball joint for 1-axis pivot
long_sweep = 100;   //[100:5:140]

// ---------- constants ----------

module dummy(){} // force customizer to stop here

overhang = 45;  // print overhang allowance (can go to 40 but works best at 45)

// ISO metric bolt data
boltheadsize = let(c3=cos(30)) [
// thread size, head corner-to-corner diameter, head height
    [ 4, 7/c3, 2.9 ],
    [ 5, 8/c3, 3.5 ],
    [ 6, 10/c3, 4 ],
    [ 8, 13/c3, 5,3 ],
    [ 10, 16/c3, 6.4 ],
    [ 12, 18/c3, 7.5 ],
    [ 14, 21/c3, 8.8 ]
];


// ---------- initialize ----------

boltdata = getboltdata(bolt_dia);
echo(boltdata);
handleht = boltdata[2] + boltclearance + boltdata[2]/2;
maxballdia = max(ball1_dia, ball2_dia);
ybottom = 0.5*maxballdia + maxballdia/5;
halfwidth = maxballdia/5 + maxballdia/2;
echo(str("MINIMUM BOLT LENGTH: ", round(2*halfwidth+handle_offset+handleht-boltdata[2]), " mm")); 

// ---------- render ----------

if (display == "print") {
    translate([-3*bolt_dia,0,0]) bolt_handle();
    translate([(ball_spacing+maxballdia)/2, 0.8*maxballdia, ybottom]) rod_blank(ball_spacing, bolt_dia, ball1_dia, ball2_dia, hexrecess=false);
    translate([(ball_spacing+maxballdia)/2, -0.8*maxballdia, ybottom]) rod_blank(ball_spacing, bolt_dia, ball1_dia, ball2_dia, hexrecess=true);

} else if (display == "assembly") {
    handleht = boltdata[2]+0.2+boltdata[2]/4;
    rotate([-90,0,0]) {
        rod_blank(ball_spacing, bolt_dia, ball1_dia, ball2_dia, hexrecess=false);
        rotate([180,0,0]) rod_blank(ball_spacing, bolt_dia, ball1_dia, ball2_dia, hexrecess=true);
        translate([0,0,-halfwidth-handleht-handle_offset-0.1]) bolt_handle();
    }
}


// ---------- modules ----------

module rod_blank(ballspacing, boltdia, dball1, dball2, gappct = gap_pct, hexrecess=false) {
    length = max(4*boltdia, maxballdia+boltdia+4, ballspacing);
    ball1wall = max(2, dball1/5);
    ball2wall = max(2, dball2/5);
    wdball1 = dball1+2*ball1wall;
    wdball2 = dball2+2*ball2wall;
    dmax = maxballdia + 2*max(ball1wall,ball2wall);
    gap1 = 0.01*gappct*dball1/2;
    gap2 = 0.01*gappct*dball2/2;
    maxgap = max(gap1,gap2);
    gapdiff = gap2-gap1;
    avggap = 0.5*(gap1+gap2);
    gapsurfaceangle = atan(gapdiff/(length+0.5*(dball1+dball2)));
    bdata = getboltdata(boltdia);
    difference() {
        union() {
            hull() 
            difference() {
                // all parts to hull together
                union() {
                    zcone1 = -0.5*wdball1/cos(overhang);
                    zcone2 = -0.5*wdball2/cos(overhang);
                    zrect = -0.5*dmax/cos(overhang);
                    x1 = zcone1-zrect-length/2-1.5;
                    x2 = length/2-(zcone2-zrect)+1.5;
                    translate([-0.5*(length), 0, 0]) halfballcone(wdball1);
                    translate([0.5*(length), 0, 0]) halfballcone(wdball2);
                    translate([(dball1-length)/2,0,0]) rotate([0,90,0]) cylinder(length-0.5*(dball1+dball2), d=dmax, $fn=64);
                    translate([x1,-1.5,zrect]) cube([x2-x1,3,1]);
                }
                // subtract top surface
                translate([-0.5*(length+dball1),0,/*-gap1*/-avggap])
                //rotate([0,gapsurfaceangle,0])
                    translate([-dmax,-dmax,0])
                    cube([length+0.5*(dball1+dball2)+2*dmax, 2*dmax, dmax]);
            }
            // add bolt hole body (diameter of bolt head, or with 2mm wall around nut)
            translate([0,0,-dmax/2-1]) cylinder(dmax/2-maxgap, d=bdata[1]+2*boltclearance+(hexrecess?4:0), $fn=32);
        }
        // subtract bottom surface
        translate([0,0,-ybottom-0.5*dmax]) cube([length+maxballdia*1.1, dmax+2, dmax], center=true);
        // subtract ball 1 cutouts
        translate([-0.5*(length), 0, 0]) {
            // subtract ball
            rotate([180,0,0]) octsphere(d=dball1+ballclearance, hemisphere=true, $fn=64);
            // subtract end_sweep (max 120°) cone from the end
            rotate([0,-90,0]) cylinder(dmax, d1=0, d2=2*dmax*tan(end_sweep/2), $fn=32);
            // subract long_sweep (max 140°) swept cone
            conesweep(dball1, dball1/2, sweep=long_sweep);
        }
        // subtract ball 2 cutouts
        translate([0.5*(length), 0, 0]) {
            rotate([180,0,0]) octsphere(d=dball2+ballclearance, hemisphere=true, $fn=64);
            rotate([0,90,0]) cylinder(dmax, d1=0, d2=2*dmax*tan(end_sweep/2), $fn=32);
            mirror([1,0,0]) conesweep(dball2, dball2/2, sweep=long_sweep);
        }
        // subtract bolt hole
        cylinder(dmax+3, d=boltdia+2*boltclearance, center=true, $fn=32);
        // subtract hex recess if needed
        if (hexrecess)
            translate([0,0,-ybottom-1]) bolt(boltdia, boltclearance, add_height=1+2*boltclearance);
    }
}

module halfballcone(dia) {
    rotate([180,0,0]) {
        octsphere(d=dia, hemisphere=true, $fn=64);
        cylinder(0.5*dia/cos(overhang), d=3, $fn=6);
    }
}

module conesweep(dia, shaftdia, sweep=135) {
    s2 = sqrt(2);
    dfsd = dia*cos(45);
    scl = shaftdia/dfsd;
    rotate([0,0,180-sweep/2]) union() {
        rotate_extrude(angle=sweep, convexity=4, $fn=32) translate([s2*dia,0]) scale([1,scl]) rotate([0,0,45]) square(2*dia, center=true);
        rotate([0,90,0]) cylinder(2*dia, d1=0, d2=2*scl*2*dia, $fn=32);
        rotate([0,-90,sweep-180]) cylinder(2*dia, d1=0, d2=2*scl*2*dia, $fn=32);
    }
}

module bolt_handle(arms=4, washer_offset=handle_offset, showboltlen=0) {
    armrad = 2*bolt_dia;           // radius to tip of arm (total diameter is 4 shaft diameters)
    wdia = boltdata[1]+2*boltclearance;    // washer diameter
    bevel = boltdata[2] / 4;           // amount to bevel (1/4 head height)
    wallthick = max(2.4, bevel+1,boltdata[1]/7);    // minimum wall thickness around bolt head
    wallht = max(4, boltdata[2]);
    hrad = boltdata[1]/2 + boltclearance + wallthick;  // minimum radius around bolt head
    armlen = armrad - hrad;         // net length of arm
    hpts = [                        // stack of polygon points to make beveled arm shape
        handle_outline(0, arms, hrad, armlen, -bevel),
        handle_outline(bevel, arms, hrad, armlen, 0),
        handle_outline(bevel+wallht+boltclearance, arms, hrad, armlen, 0),
        handle_outline(wallht+boltclearance+2*bevel, arms, hrad, armlen, -bevel)
    ];
    difference() {
        union() {
            polyhedron_stack(hpts);
            translate([0,0,wallht+2*bevel+boltclearance-1]) cylinder(1+washer_offset, d=wdia, $fn=32);
        }
        rotate([180,0,0]) translate([0,0,-boltdata[2]-boltclearance])
            bolt(bolt_dia, 2*boltclearance, add_height=1, shaft_len=boltdata[2]+washer_offset);
    }
}

module bolt(shaft_dia = bolt_dia, clearance = 0.2, add_height = 0, shaft_len = 0) {
    bdata = getboltdata(shaft_dia);
    shd = bdata[0];
    bhd = bdata[1];
    bhh = bdata[2];
    union() {
        cylinder(bhh+add_height, d=bhd+clearance, $fn=6);
        if (shaft_len > 0)
            translate([0,0,-shaft_len]) cylinder(shaft_len+0.2, d=shd+clearance+0.2, $fn=32);
        translate([0,0,bhh+add_height-0.1]) cylinder(0.33, d=bhd+clearance, $fn=3);
        translate([0,0,-0.23]) cylinder(0.33, d=bhd+clearance, $fn=3);
    }
}

// ---------- utility ----------

// Build a polyhedron object from a stack of polygons. It is assumed that each polygon has [x,y,z] coordinates as its vertices, and the ordering of vertices follows the right-hand-rule with respect to the direction of propagation of each successive polygon.
module polyhedron_stack(stack) {
    nz = len(stack); // number of z layers
    np = len(stack[0]); // number of polygon vertices
    facets = [
        // close first opening
        [ for(j=[0:np-1]) j ],
        // define quads for polyhedron body
        for(i=[0:nz-2])
            for(j=[0:np-1]) let(k1=i*np+j, k4=i*np+((j+1)%np), k2=k1+np, k3=k4+np)
                [k1, k2, k3, k4],
        // close last opening
        [ for(j=[np*nz-1:-1:np*nz-np]) j ] 
    ];
    polyhedron(flatten(stack), facets, convexity=6);
}

// ---------- functions ----------

// flatten an array of arrays
function flatten(l) = [ for (a = l) for (b = a) b ] ;

function getboltdata(shaft_dia=10) = let(
    ni = search(shaft_dia, boltheadsize, 1),
    lni = len(ni),
    idx = lni>0 ? ni[0] : echo(str("getboltdata(): Arg must be a valid metric diameter; defaulting to M", boltheadsize[3][0])) 3
    ) boltheadsize[idx];

function handle_outline(z, arms, rmin, armlen, roffset=0, twist=10) = [
    for(a=[0:3:359]) let(a2=arms*a, c = pow((1+cos(a2))/2,2), r=rmin+armlen*c+roffset)
        [ r*cos(a-twist*c), r*sin(a-twist*c), z ]
];
