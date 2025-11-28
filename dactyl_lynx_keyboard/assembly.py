from collections.abc import Iterable
from itertools import chain, pairwise
from typing import Tuple, Optional

#from solid2 import cube, hull, sphere, union
from solid2 import *
from solid2.core.object_base import OpenSCADObject
from solid2.extensions.bosl2 import screws

from spkb.switch_plate import (
    mx_plate_with_backplate,
)

from spkb.board_mount import stm32_blackpill
from spkb.board_mount import BoardMount
from spkb.keycaps import sa_double_length
from spkb.keyswitch import Keyswitch, MX
from spkb.single_key_pcb import single_key_board
from spkb.utils import cylinder_outer, fudge_radius, nothing

from .layouts.layout import ShapeForLocationCallback
from .layouts.finger_well import FingerWellLayout
from .layouts.thumb_well import ThumbWellLayout, ThumbWellLayout9key, ThumbWellLayout11key, ThumbWellLayout12key
from .mini_din_connector_mount import MiniDINConnectorMount
from .trackpoint_mount import TrackPointMount


# Custom board mount

CustomBoard = BoardMount(
    34, #width
    57, #length
    1.64, #thickness
    front_mounting_post_separation=22,
    back_mounting_post_separation=27 
)


class KeyboardAssembly:
    def __init__(
        self,
        columns: int = 6,
        rows: int = 5,
        use_1_5u_keys: bool = False,
        use_color: bool = False,
        socket_shape: Optional[ShapeForLocationCallback] = None,
        keyswitch: Keyswitch = MX(),
        board_type: str = "stm32",              # "stm32" or "custom"
        connector_mount_enabled: bool = True,  # Enable Mini-DIN connector
        magnet_mount_enabled: bool = True,      # True = magnets, False = holes
        nine_key_enabled: bool = False,               # True = 9 key thumb cluster false = 8 key
        eleven_key_enabled: bool = False,               # True = 11 key thumb cluster false = 8 key
        twelve_key_enabled: bool = False               # True = 12 key thumb cluster false = 8 key
    ):
        self.use_color = use_color
        self.socket_shape = socket_shape
        self.board_type = board_type
        self.connector_mount_enabled = connector_mount_enabled
        self.magnet_mount_enabled = magnet_mount_enabled
        self.nine_key_enabled = nine_key_enabled
        self.eleven_key_enabled = eleven_key_enabled
        self.twelve_key_enabled = twelve_key_enabled

        self.finger_layout = FingerWellLayout(
            columns=columns,
            rows=rows,
            use_1_5u_keys=use_1_5u_keys,
            keyswitch=keyswitch,
        )

        if self.nine_key_enabled:
            self.thumb_layout = ThumbWellLayout9key(keyswitch=keyswitch)
        elif self.eleven_key_enabled:
            self.thumb_layout = ThumbWellLayout11key(keyswitch=keyswitch)
        elif self.twelve_key_enabled:
            self.thumb_layout = ThumbWellLayout12key(keyswitch=keyswitch)
        else:
            self.thumb_layout = ThumbWellLayout(keyswitch=keyswitch)

        if socket_shape is None:
            self.socket_shape = lambda _column, _row: self.finger_layout.keyswitch.plate()

        self.connector_mount = MiniDINConnectorMount()
        self.trackpoint_mount = TrackPointMount()
        # Select board mount based on parameter
        if self.board_type == "custom":
            self.board_mount = CustomBoard
        else:
            self.board_mount = stm32_blackpill

        self.screen_size = (27.75, 39.25)
        self.screen_hole_centers = (22.5, 34.05)

        self.tenting_nut = (
            cube((10, 10, 10), center=True)
            - screws.screw_hole("M6x1", length=10.01, thread=True, bevel=True, blunt_start=True, _fn=32)
        )

        self.tenting_nut_unthreaded = (
            cube((10, 10, 10), center=True)
            - screws.screw_hole("M6x1", length=10.01, thread=False, bevel=True, blunt_start=True, _fn=32)
        )

        self.left_side = False

        self.enable_trackpoint = True
        # changed
        self.enable_nuts = True
        # changed
        self.bottom_thumb_nuts = True

        self.edge_vertical_offset = 8
        self.bottom_cover_offset = 11
        self.bottom_cover_edge_protusion = self.finger_layout.keyswitch.keyswitch_length - 1
        self.bottom_cover_thickness = 3
        self.bottom_cover_post_size = 0.2
        self.bottom_cover_magnet_mount_thickness = 1.5
        self.bottom_cover_magnet_radius = 2.5
        self.bottom_cover_magnet_thickness = 3
        self.bottom_cover_magnet_offset = 13.7

    @property
    def wall_thickness(self):
        return self.finger_layout.keyswitch.wall_thickness

    def transform_finger_nut1(self, shape):
        """Place the given shape at the position and orientation of the first finger nut.

        This is the nut at the top outside corner of the finger well. (above column 5, row 0)

        :param shape: the shape to place
        """
        return shape \
            .rotate(20, (1, 0, 0)) \
            .translate((70, 37, 45))

    def transform_finger_nut2(self, shape):
        """Place the given shape at the position and orientation of the second finger nut.

        This is the nut at the bottom outside corner of the finger well. (next to column 5, row 4)

        :param shape: the shape to place
        """
        return shape \
            .rotate(-15, (1, 0, 0)) \
            .rotate(-5, (0, 1, 0)) \
            .translate((81, -64, 6))

    def transform_finger_nut3(self, shape):
        """Place the given shape at the position and orientation of the third finger nut.

        This is the nut in the middle of the inside edge of the finger well. (next to column 0, row 1)

        :param shape: the shape to place
        """
        return shape \
            .rotate(15, (0, 1, 0)) \
            .rotate(9, (1, 0, 0)) \
            .translate((-57, 16, 49))

    def transform_board(self, shape):
        """Place the given shape at the position and orientation of the microcontroller board mount.

        :param shape: the shape to place
        """
        return self.finger_layout.key_place(
            2,
            -1,
            shape
            .rotate(90, (0, 0, 1))
            .rotate(160, (1, 0, 0))
            .translate((-26, -2.5, -6))
        )

    def transform_connector_mount(self, shape):
        """Place the given shape at the position and orientation of the Mini-DIN connector mount.

        :param shape: the shape to place
            """
        return self.finger_layout.key_place(
            0,
            0,
            shape
            .rotate(-90, (0, 1, 0))
            .translate((
                (self.finger_layout.keyswitch.keyswitch_width + self.connector_mount.outerFrameThickness) / -2 - 1.5,
                0,
                -self.connector_mount.outerRadius() - 2
            ))
        )


    def transform_trackpoint_mount(self, shape):
        """Place the given shape at the position and orientation of the TrackPoint module.

        :param shape: the shape to place
        """
        return self.finger_layout.key_place(0.5, 2.5, shape)

    def transform_thumb_nut1(self, shape):
        """Place the given shape at the position and orientation of the first thumb nut.

        This is the nut in the bottom outside corner of the thumb well. (at the corner of column 0, row 0.5)

        :param shape: the shape to place
        """
        return shape \
            .rotate(-10, (1, 0, 0)) \
            .rotate(5, (0, 1, 0)) \
            .rotate(48, (0, 0, 1)) \
            .translate((20, -25, 9)) \
            .rotate(10, (1, 1, 1)) \
            .translate(self.thumb_layout.placement_transform)

    def transform_thumb_nut2(self, shape):
        """Place the given shape at the position and orientation of the second thumb nut.

        This is the nut in the bottom inside corner of the thumb well. (next to column 0, row -1)

        :param shape: the shape to place
        """
        return shape \
            .rotate(10, (1, 0, 0)) \
            .rotate(68, (0, 0, 1)) \
            .translate((-32, 30, 4)) \
            .rotate(10, (1, 1, 1)) \
            .translate(self.thumb_layout.placement_transform)

    def transform_thumb_nut3(self, shape):
        """Place the given shape at the position and orientation of the third thumb nut.

        This is the nut behind the thumb well. (to attach to the web between column 1, row -1 and column 2, row -1)

        :param shape: the shape to place
        """
        return shape \
            .rotate(-15, (1, 0, 0)) \
            .rotate(-20, (0, 0, 1)) \
            .rotate(-10, (0, 1, 0)) \
            .translate((-3, 57, 33.2)) \
            .rotate(10, (1, 1, 1)) \
            .translate(self.thumb_layout.placement_transform)


    def thumb_mounting_holes(self):
        """Place holes for screwing the thumbcluster to the main body, can be separated in the slicer then screwed together for easier printing
        
        """
        hole_diameter = 2.0
        hole_depth = 18.0

        holes = union()()  # Start with an empty union

        # First hole
        hole1 = cylinder_outer(hole_diameter / 2, hole_depth, center=True) \
            .rotate(-67, (1, 0, 0)) \
            .rotate(110, (0, 1, 0)) \
            .rotate(0, (0, 0, 1)) \
            .down(hole_depth / 2) \
            .translate(-11, 43, 51.5)

        holes += self.thumb_layout.web_corner(2, 0, left=True, top=True)(hole1)

        # Second hole
        hole2 = cylinder_outer(hole_diameter / 2, hole_depth, center=True) \
            .rotate(-67, (1, 0, 0)) \
            .rotate(110, (0, 1, 0)) \
            .rotate(0, (0, 0, 1)) \
            .down(hole_depth / 2) \
            .translate(-3, 41, 51.5)

        holes += self.thumb_layout.web_corner(1, 0, left=False, top=True)(hole2)

        return holes

    def thumb_mount_separator(self):

        separator_cube = cube([25, 0.1, 9], center=True) \
            .rotate(-14.5, (1, 0, 0)) \
            .rotate(0, (0, 1, 0)) \
            .rotate(-11, (0, 0, 1)) \
            .translate(-60, -37.88, 50)

        return separator_cube
    
    #balljoint v1
    def balljoint_ball(self):

        
        ball_dia = 15          # diameter of the ball
        ball = sphere(ball_dia / 2)

        return ball
    
    def transform_balljoint_ball(self, geom):
        return (
            geom
            .translate(-57, -26, 50)
        )
    
    def balljoint_ball_anchor(self):
        """
        A thin disk anchored on the socket's flat mouth (threaded side).
        Uses the same geometry params as balljoint_socket().
        """
        ball_dia = 9


        outer_r = (ball_dia / 2)

        anchor_d = outer_r * 2 
        anchor_h = 0.8                 # thin

        disk = cylinder(h=anchor_h, d=anchor_d, center=True)\
            .rotate(11, (1, 0, 0)) \
            .rotate(90, (0, 1, 0)) \
            .rotate(90, (0, 0, 1)) \
            .translate(-1, -6, 0)
            
        return disk
    
    def balljoint_socket(self):
        ball_dia = 15
        socket_clearance = +0.1
        socket_thickness = 1.5

        outer_r = (ball_dia / 2) + socket_clearance + socket_thickness
        inner_r = (ball_dia / 2) + socket_clearance

        # Outer shell 
        shell_height = outer_r * 2  # full height of socket
        socket_outer = cylinder(h=shell_height, d=outer_r * 2, center=True)

        # Inner spherical cavity for the ball
        socket_inner = sphere(inner_r)

        # Hollow shell: cylinder minus sphere
        socket_shell = difference()(socket_outer, socket_inner)

        # Remove top portion
        cut_height = shell_height
        top_cut = cube([outer_r * 2, outer_r * 2, cut_height], center=False).translate(-outer_r, -outer_r, 4)

        socket = difference()(socket_shell, top_cut)

        socket_screw1 = cube([10, 7, 13.5], center=True) \
            .rotate(0, (1, 0, 0)) \
            .rotate(0, (0, 1, 0)) \
            .rotate(-101, (0, 0, 1)) \
            .translate(10.5, -2, -2.8)
        
        socket += socket_screw1()

        socket_screw2 = cube([10, 7, 13.5], center=True) \
            .rotate(0, (1, 0, 0)) \
            .rotate(0, (0, 1, 0)) \
            .rotate(-101, (0, 0, 1)) \
            .translate(-10.5, 2, -2.8)
        
        socket += socket_screw2()

        socket_hole1 = cylinder_outer(3 / 2, 20, center=True) \
            .rotate(90, (1, 0, 0)) \
            .rotate(0, (0, 1, 0)) \
            .rotate(-11, (0, 0, 1)) \
            .translate(10.5, 0, -2.8)
        socket -= socket_hole1()

        socket_hole2 = cylinder_outer(3 / 2, 20, center=True) \
            .rotate(90, (1, 0, 0)) \
            .rotate(0, (0, 1, 0)) \
            .rotate(-11, (0, 0, 1)) \
            .translate(-10.5, 0, -2.8)
        socket -= socket_hole2()

        socket_slit= cube([2, 40, 40], center=True) \
            .rotate(0, (1, 0, 0)) \
            .rotate(0, (0, 1, 0)) \
            .rotate(-101, (0, 0, 1)) \
            .translate(0, 0, -10)
        
        socket -= socket_slit()

        return socket

        
    
    def balljoint_socket_slit(self):
        """ 
        Does not remove web geometry if not called on it's own, does the same thing as the socket_slit above, man i suck at this
        """

        slit= cube([2, 40, 10], center=True) \
            .rotate(0, (1, 0, 0)) \
            .rotate(0, (0, 1, 0)) \
            .rotate(-101, (0, 0, 1)) \
            .translate(0, 0, -10)
        
        return slit

    
    def balljoint_socket_anchor(self):
        """
        A thin disk anchored on the socket's flat mouth (threaded side).
        Uses the same geometry params as balljoint_socket().
        """
        ball_dia = 15
        socket_clearance = 0.1
        socket_thickness = 1.5

        outer_r = (ball_dia / 2) + socket_clearance + socket_thickness 

        anchor_d = outer_r * 2 
        anchor_h = 0.8                 # thin

        disk = cylinder(h=anchor_h, d=anchor_d, center=True)
        return translate(0, 0, -9)(disk)
    
    def transform_balljoint_socket(self, geom):
        return (
            geom
            .rotate(90, (1, 0, 0))
            .rotate(90, (0, 1, 0))
            .translate(-57, -26, 52)
        )

    def switch_socket(self, column, row) -> OpenSCADObject:
        """Generate the switch plate socket for the given keyswitch.

        :param column: the column of the keyswitch
        :type column: number

        :param row: the row of the keyswitch
        :type row: number
        """
        if self.socket_shape is None:
            shape = self.finger_layout.keyswitch.plate()
        else:
            shape = self.socket_shape(column, row)

        if isinstance(row, float) and not row.is_integer():
            plate_height = (sa_double_length - self.finger_layout.keyswitch.keyswitch_length + 0.4) / 2
            # TODO: Subtract stabilizer mount holes; see dactyl.clj line 348
            stabilizer_mount = cube(
                self.finger_layout.keyswitch.keyswitch_width + self.wall_thickness * 2,
                plate_height,
                self.thumb_layout.web_thickness,
                center=True
            ).translate(
                0,
                (plate_height + self.finger_layout.keyswitch.keyswitch_length) / 2 + self.wall_thickness,
                -self.thumb_layout.web_thickness / 2
            )
            shape = (
                shape
                + stabilizer_mount
                + stabilizer_mount.mirror(0, 1, 0)
            )
        elif isinstance(column, float) and not column.is_integer():
            plate_width = (sa_double_length - self.finger_layout.keyswitch.keyswitch_width + 0.4) / 2
            # TODO: Subtract stabilizer mount holes; see dactyl.clj line 348
            stabilizer_mount = cube(
                plate_width,
                self.finger_layout.keyswitch.keyswitch_length + self.wall_thickness * 2,
                self.thumb_layout.web_thickness,
                center=True
            ).translate(
                (plate_width + self.finger_layout.keyswitch.keyswitch_width) / 2 + self.wall_thickness,
                0,
                -self.thumb_layout.web_thickness / 2
            )
            shape = (
                shape
                + stabilizer_mount
                + stabilizer_mount.mirror(0, 1, 0)
            )

        if self.left_side:
            return shape.mirror((1, 0, 0))
        return shape

    def bottom_cover_size_adjust(self, column: float, row: float) -> Tuple[float, float]:
        """Adjust the size of the bottom cover element at the given column and row.
        """
        if column == 2:
            return 2, 0
        elif column == 4:
            return -2, 0
        return 0, 0

    def bottom_cover_position_adjust(self, column: float, row: float) -> Tuple[float, float]:
        """Adjust the position of the bottom cover element at the given column and row.
        """
        if column == 1:
            return -2, 0
        elif column in (3, 4):
            return 2, 0
        return 0, 0

    def switch_bottom_cover(self, column, row):
        """Generate the portion of the bottom cover below the given keyswitch.

        :param column: the column of the keyswitch
        :type column: number

        :param row: the row of the keyswitch
        :type row: number
        """
        extra_width, extra_length = self.bottom_cover_size_adjust(column, row)
        x_shift, y_shift = self.bottom_cover_position_adjust(column, row)

        if isinstance(row, float) and not row.is_integer():
            return cube(
                self.finger_layout.keyswitch.keyswitch_width + self.wall_thickness * 2 + extra_width,
                sa_double_length + extra_length,
                self.bottom_cover_thickness,
                center=True
            ).translate(
                x_shift,
                y_shift,
                -self.bottom_cover_offset - self.bottom_cover_thickness / 2
            )

        elif isinstance(column, float) and not column.is_integer():
            return cube(
                sa_double_length + extra_width,
                self.finger_layout.keyswitch.keyswitch_length + self.wall_thickness * 2 + extra_length,
                self.bottom_cover_thickness,
                center=True
            ).translate(
                x_shift,
                y_shift,
                -self.bottom_cover_offset - self.bottom_cover_thickness / 2
            )

        return cube(
            self.finger_layout.keyswitch.keyswitch_width + self.wall_thickness * 2 + extra_width,
            self.finger_layout.keyswitch.keyswitch_length + self.wall_thickness * 2 + extra_length,
            self.bottom_cover_thickness,
            center=True
        ).translate(x_shift, y_shift, -self.bottom_cover_offset - self.bottom_cover_thickness / 2)

    def finger_part(self):
        """Generate the finger part of the assembly.

        This includes the finger well, the board mount, and the Mini-DIN connector mount.
        """
        shape = (
            self.finger_layout.place_all(self.switch_socket)
            + self.finger_layout.web_all()

            + self.transform_board(self.board_mount.render(distance_from_surface=8))
            + hull()(
                self.transform_board(
                    cube((60, 120, 8), center=True)
                    & self.board_mount.back_mounting_posts(distance_from_surface=8)
                ),
                self.finger_layout.web_corner(3, 0, left=False, top=True),
                self.finger_layout.web_corner(3, 0, left=True, top=True),
            )
            + hull()(
                self.transform_board(
                    cube((60, 120, 6), center=True)
                    & self.board_mount.front_mounting_posts(distance_from_surface=8)
                ),
                self.finger_layout.web_corner(1, 0, left=True, top=True),
                self.finger_layout.web_corner(1, 0, left=False, top=True),
            )
        )
        if self.board_type == "stm32":
            shape += self.transform_board(
                hull()(
                    cube((60, 120, 2), center=True)
                    & self.board_mount.back_mounting_posts(distance_from_surface=8),
                    cube((60, 120, 2), center=True)
                    & self.board_mount.front_mounting_posts(distance_from_surface=8)
                )
                + cube((11, 2.9, 13), center=True)
                .translate((0, 3 / 2, 13 / 2))
                - self.board_mount.board_profile(distance_from_surface=8)
            )
            shape -= self.transform_board(
                # Holes for buttons on RP2040 TYPE-C 16MB
                cube((4, 6, 40), center=True)
                .translate((-5 if self.left_side else 5, -22, 0))
                + cube((4, 6, 40), center=True)
                .translate((-6, -46, 0))
                + cube((4, 6, 40), center=True)
                .translate((6, -46, 0))
            )
        else: 
            shape += self.transform_board(
                hull()(
                    cube((60, 120, 2), center=True)
                    & self.board_mount.back_mounting_posts(distance_from_surface=8),
                    cube((60, 120, 2), center=True)
                    & self.board_mount.front_mounting_posts(distance_from_surface=8)
                )
            )


        if self.connector_mount_enabled:
            shape += hull() (
                self.transform_connector_mount(self.connector_mount.frame()),
                self.finger_layout.web_corner(0, 0, left=True, top=False),
                self.finger_layout.web_corner(0, 0, left=True, top=True),
                self.cover_edge_corner(side=True, column=0, row=1, left=True, top=True, top_shell=True, offset_along_edge=self.bottom_cover_post_size),
                self.finger_layout.web_corner(column=0, row=1, left=True, top=True),
             )
            shape += self.finger_cover_edge(top_shell=True)
            shape -= self.place_cover_magnets(self.cover_magnet_hole(top_shell=True))
            shape -= self.transform_connector_mount(self.connector_mount.hole())
        else:
            shape += hull() (
                self.finger_layout.web_corner(0, 0, left=True, top=False),
                self.finger_layout.web_corner(0, 0, left=True, top=True),
                self.cover_edge_corner(side=True, column=0, row=0, left=True, top=True, top_shell=True, offset_along_edge=4.4),
                self.cover_edge_corner(side=True, column=0, row=1, left=True, top=True, top_shell=True, offset_along_edge=self.bottom_cover_post_size),
                self.finger_layout.web_corner(column=0, row=1, left=True, top=True),
            )
            shape += self.finger_cover_edge(top_shell=True)
            shape -= self.place_cover_magnets(self.cover_magnet_hole(top_shell=True))

        if self.enable_trackpoint and not self.left_side:
            shape += self.transform_trackpoint_mount(self.trackpoint_mount.trackpoint_mount())
            shape -= self.transform_trackpoint_mount(self.trackpoint_mount.trackpoint_holes())

        shape -= self.finger_layout.place_all(single_key_board(simple=True, extra_spacing=0.02))

        if self.use_color:
            return shape.color((0.1, 0.1, 0.1))

        return shape

    def cover_magnet_mount(self, top_shell):
        """Create the mounting shape for a magnet to attach the bottom cover.

        :param top_shell: whether this is for the top shell (True) or for the bottom cover (False)
        :type top_shell: bool
        """
        radius = self.bottom_cover_magnet_radius + self.bottom_cover_magnet_mount_thickness

        # Fudge the sphere radius as if it had 12 segments instead of 16, in order to make it line up a bit better with
        # the cylinder. It's still not perfect.
        sphere_radius = fudge_radius(radius, segments=12)
        sphere_radii = {}
        if isinstance(sphere_radius, (int, float)):
            sphere_radii['r'] = sphere_radius
        elif isinstance(sphere_radius, (tuple, list)):
            sphere_radii['r1'], sphere_radii['r2'] = sphere_radius

        if self.magnet_mount_enabled:
            shape = (
                cylinder_outer(radius, self.bottom_cover_magnet_thickness, center=True)
                .up(self.bottom_cover_magnet_thickness / 2)
                + (sphere(_fn=16, **sphere_radii) - cube(radius * 2, radius * 2, radius * 2, center=True).down(radius))
                .up(self.bottom_cover_magnet_thickness)
            )
        else:
            shape = cylinder_outer(radius, self.bottom_cover_magnet_thickness * 2, center=True).up(self.bottom_cover_magnet_thickness )

        if not top_shell:
            return shape.mirror((0, 0, 1))
        return shape

    def cover_magnet_hole(self, top_shell):
        """Create the hole for a magnet to attach the bottom cover.

        :param top_shell: whether this is for the top shell (True) or for the bottom cover (False)
        :type top_shell: bool
        """
        if self.magnet_mount_enabled:
            hex_radius = self.bottom_cover_magnet_radius * 0.99
            hex_chamfer_width = 0.3
            end_groove_depth = 0.5
            end_groove_radius = hex_radius + end_groove_depth
            end_groove_height = 0.5

            return (
                cylinder_outer(  # Top end groove
                    end_groove_radius,
                    end_groove_height,
                    segments=6,
                    center=True,
                ).up(self.bottom_cover_magnet_thickness - end_groove_height / 2)
                + cylinder_outer(  # Top end groove chamfer
                    [hex_radius, end_groove_radius],
                    end_groove_depth,
                    segments=6,
                    center=True,
                ).up(self.bottom_cover_magnet_thickness - end_groove_height - end_groove_depth / 2)
                + cylinder_outer(  # Top main hole chamfer
                    [hex_radius, hex_radius + hex_chamfer_width],
                    end_groove_depth,
                    segments=6,
                    center=True,
                ).down(end_groove_depth / 2)
                + cylinder_outer(  # Main hole
                    hex_radius,
                    self.bottom_cover_magnet_thickness * 2,
                    segments=6,
                    center=True,
                )
                + cylinder_outer(  # Bottom main hole chamfer
                    [hex_radius + hex_chamfer_width, hex_radius],
                    end_groove_depth,
                    segments=6,
                    center=True,
                ).up(end_groove_depth / 2)
                + cylinder_outer(  # Bottom end groove chamfer
                    [end_groove_radius, hex_radius],
                    end_groove_depth,
                    segments=6,
                    center=True,
                ).down(self.bottom_cover_magnet_thickness - end_groove_height - end_groove_depth / 2)
                + cylinder_outer(  # Bottom end groove
                    end_groove_radius,
                    end_groove_height,
                    segments=6,
                    center=True,
                ).down(self.bottom_cover_magnet_thickness - end_groove_height / 2)
            )
        else:
            clearance_radius = 3.2 / 2  # M3 screw clearance
            hole_depth = self.bottom_cover_magnet_thickness * 6  # Full depth through both parts
            radius = self.bottom_cover_magnet_radius + self.bottom_cover_magnet_mount_thickness

            hole = cylinder_outer(
            clearance_radius,
            hole_depth,
            center=True
            ).up(self.bottom_cover_magnet_thickness  / 2)

            if top_shell:
                clearance = cylinder_outer(radius, 10, center=True).up(self.bottom_cover_magnet_thickness + 8)
                clearance_under = cylinder_outer(radius, 10, center=True).up(self.bottom_cover_magnet_thickness -8)  
                hole += clearance + clearance_under   

            return hole 



    def place_cover_magnets(self, shape):
        """Place the given shape at the location of each cover attachment magnet.

        :param shape: the shape to place
        """
        shape = shape.down(self.edge_vertical_offset)
        offset = self.bottom_cover_magnet_offset

        return (
            self.finger_layout.key_place(column=0, row=0, shape=shape.forward(offset))
            + self.finger_layout.key_place(column=0, row=2, shape=shape.left(offset))
            + self.finger_layout.key_place(column=1, row=4, shape=shape.back(offset))
            + self.finger_layout.key_place(column=5, row=4, shape=shape.back(offset))
            + self.finger_layout.key_place(column=5, row=2, shape=shape.right(offset))
            + self.finger_layout.key_place(column=5, row=0, shape=shape.forward(offset).left(1.5))
        )

    def cover_edge_corner(self,
                          side: bool,
                          column: float,
                          row: float,
                          left: bool,
                          top: bool,
                          top_shell: bool,
                          offset_along_edge: float = 0,
                          outer: bool = False,
                          ):
        """Generate a corner post for generating the edges of the top shell or bottom cover.

        :param side: whether to create a block for the left or right edge (True), or for the top or bottom edge (False)
        :type side: bool
        :param column: the column of the key to create the corner block at
        :type column: number
        :param row: the row of the key to create the corner block at
        :type row: number
        :param left: whether to create the block on the left side (True) or the right side (False)
        :type left: bool
        :param top: whether to create the block on the top side (True) or the bottom side (False)
        :type top: bool
        :param top_shell: whether to create a block for the top shell (True) or for the bottom cover (False)
        :type top_shell: bool
        :param offset_along_edge: the offset along the edge (either X or Y depending on whether `side` is True)
        :type offset_along_edge: number
        :param outer: whether to create a tiny block at the very outer edge of the edge (True) or one that is the full
        thickness of the edge (False)
        :type outer: bool

        :param top_shell: whether this is for the top shell (True) or for the bottom cover (False)
        :type top_shell: bool
        """
        vertical_offset = self.edge_vertical_offset + self.bottom_cover_post_size / (-2 if top_shell else 2)

        edge_post = cube(
            self.bottom_cover_thickness if side and not outer else self.bottom_cover_post_size,
            self.bottom_cover_thickness if not side and not outer else self.bottom_cover_post_size,
            self.bottom_cover_post_size,
            center=True
        ).down(vertical_offset)

        if side:
            post = (
                edge_post
                .left(
                    (
                        self.bottom_cover_edge_protusion
                        + ((self.bottom_cover_thickness - self.bottom_cover_post_size) / 2 if outer else 0)
                    )
                    * (1 if left else -1)
                )
                .forward((10 if top else -10) + offset_along_edge)
            )
        else:
            post = (
                edge_post
                .forward(
                    (
                        self.bottom_cover_edge_protusion
                        + ((self.bottom_cover_thickness - self.bottom_cover_post_size) / 2 if outer else 0)
                    )
                    * (1 if top else -1)
                )
                .left((10 if left else -10) + offset_along_edge)
            )

        return self.finger_layout.key_place(column, row, post)

    def bottom_cover_web_kwargs(self):
        """Generate kwargs for passing to Layout.web_*() when generating the bottom cover.

        This includes the Z offset to put the corners at the depth of the bottom cover shell, and the adjusted
        thickness of the cover.
        """
        return {
            'z_offset': -self.bottom_cover_offset,
            'thickness': self.bottom_cover_thickness,
            'size_adjust': self.bottom_cover_size_adjust,
            'position_adjust': self.bottom_cover_position_adjust,
        }

    def generate_cover_edge_corners(self, top_shell):
        """Generate the nested tuple of corners used with `hull()` to generate the edges of the top shell or bottom
        cover.

        :param top_shell: whether this is for the top shell (True) or for the bottom cover (False)
        :type top_shell: bool
        """
        web_kwargs = {}
        if not top_shell:
            web_kwargs = self.bottom_cover_web_kwargs()

        return (
            (
                (
                    self.cover_edge_corner(side=True, column=0, row=1, left=True, top=True, top_shell=top_shell),
                    self.finger_layout.web_corner(column=0, row=1, left=True, top=True, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=0, row=1, left=True, top=False, top_shell=top_shell),
                    self.finger_layout.web_corner(column=0, row=1, left=True, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=0, row=2, left=True, top=True, top_shell=top_shell),
                    self.finger_layout.web_corner(column=0, row=2, left=True, top=True, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=0, row=2, left=True, top=False, top_shell=top_shell),
                    self.finger_layout.web_corner(column=0, row=2, left=True, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=0, row=3, left=True, top=True, top_shell=top_shell),
                    self.finger_layout.web_corner(column=0, row=3, left=True, top=True, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=0, row=3, left=True, top=False, offset_along_edge=7, top_shell=top_shell),
                    self.finger_layout.web_corner(column=0, row=3, left=True, top=False, **web_kwargs),
                ),
            ),
            (
                (
                    self.cover_edge_corner(side=False, column=1, row=4, left=True, top=False, offset_along_edge=-7, top_shell=top_shell),
                    self.finger_layout.web_corner(column=1, row=4, left=True, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=1, row=4, left=False, top=False, offset_along_edge=-3, top_shell=top_shell),
                    self.finger_layout.web_corner(column=1, row=4, left=False, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=2, row=4, left=True, top=False, offset_along_edge=-3, top_shell=top_shell),
                    self.finger_layout.web_corner(column=2, row=4, left=True, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=2, row=4, left=False, top=False, offset_along_edge=3, top_shell=top_shell),
                    self.finger_layout.web_corner(column=2, row=4, left=False, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=3, row=4, left=True, top=False, offset_along_edge=3, top_shell=top_shell),
                    self.finger_layout.web_corner(column=3, row=4, left=True, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=3, row=4, left=False, top=False, offset_along_edge=3, top_shell=top_shell),
                    self.finger_layout.web_corner(column=3, row=4, left=False, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=4, row=4, left=True, top=False, offset_along_edge=3, top_shell=top_shell),
                    self.finger_layout.web_corner(column=4, row=4, left=True, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=4, row=4, left=False, top=False, top_shell=top_shell),
                    self.finger_layout.web_corner(column=4, row=4, left=False, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=5, row=4, left=True, top=False, top_shell=top_shell),
                    self.finger_layout.web_corner(column=5, row=4, left=True, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=5, row=4, left=False, top=False, offset_along_edge=-2, top_shell=top_shell),
                    self.finger_layout.web_corner(column=5, row=4, left=False, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=5, row=4, left=False, top=False, offset_along_edge=-2, top_shell=top_shell),
                    self.finger_layout.web_corner(column=5, row=4, left=False, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=5, row=4, left=False, top=True, top_shell=top_shell),
                    self.finger_layout.web_corner(column=5, row=4, left=False, top=True, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=5, row=3, left=False, top=False, top_shell=top_shell),
                    self.finger_layout.web_corner(column=5, row=3, left=False, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=5, row=3, left=False, top=True, top_shell=top_shell),
                    self.finger_layout.web_corner(column=5, row=3, left=False, top=True, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=5, row=2, left=False, top=False, top_shell=top_shell),
                    self.finger_layout.web_corner(column=5, row=2, left=False, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=5, row=2, left=False, top=True, top_shell=top_shell),
                    self.finger_layout.web_corner(column=5, row=2, left=False, top=True, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=5, row=1, left=False, top=False, top_shell=top_shell),
                    self.finger_layout.web_corner(column=5, row=1, left=False, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=5, row=1, left=False, top=True, top_shell=top_shell),
                    self.finger_layout.web_corner(column=5, row=1, left=False, top=True, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=5, row=0, left=False, top=False, top_shell=top_shell),
                    self.finger_layout.web_corner(column=5, row=0, left=False, top=False, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=True, column=5, row=0, left=False, top=True, top_shell=top_shell, offset_along_edge=2),
                    self.finger_layout.web_corner(column=5, row=0, left=False, top=True, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=5, row=0, left=False, top=True, top_shell=top_shell, offset_along_edge=-2),
                    self.finger_layout.web_corner(column=5, row=0, left=False, top=True, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=5, row=0, left=True, top=True, top_shell=top_shell),
                    self.finger_layout.web_corner(column=5, row=0, left=True, top=True, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=4, row=0, left=False, top=True, top_shell=top_shell),
                    self.finger_layout.web_corner(column=4, row=0, left=False, top=True, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=4, row=0, left=True, top=True, top_shell=top_shell, offset_along_edge=-0.3),
                    self.finger_layout.web_corner(column=4, row=0, left=True, top=True, **web_kwargs),
                ),
            ),
            (
                (
                    self.cover_edge_corner(side=False, column=0, row=0, left=False, top=True, top_shell=top_shell, offset_along_edge=0 if top_shell else 2),
                    self.finger_layout.web_corner(column=0, row=0, left=False, top=True, **web_kwargs),
                ),
                (
                    self.cover_edge_corner(side=False, column=0, row=0, left=True, top=True, top_shell=top_shell, offset_along_edge=(3 if top_shell else (0 if self.connector_mount_enabled else 3)) ),
                    self.finger_layout.web_corner(column=0, row=0, left=True, top=True, **web_kwargs),
                ),
            ),
        )

    def finger_cover_edge(self, top_shell):
        """Create the edge pieces of the top shell or bottom cover.

        :param top_shell: whether this is for the top shell (True) or for the bottom cover (False)
        :type top_shell: bool
        """
        edge_groups = self.generate_cover_edge_corners(top_shell=top_shell)

        return (
            union()(
                *chain(
                    *(
                        (hull()(*edge1, *edge2) for (edge1, edge2) in pairwise(edges))
                        for edges in edge_groups
                    )
                )
            )
            + self.place_cover_magnets(self.cover_magnet_mount(top_shell=top_shell))
        )

    def finger_bottom_cover(self):
        """Generate the bottom cover.
        """
        web_kwargs = self.bottom_cover_web_kwargs()

        if self.connector_mount_enabled:
            return (
                self.finger_layout.place_all(self.switch_bottom_cover)
                + self.finger_layout.web_all(**web_kwargs)
                + hull()(
                    self.transform_connector_mount(
                        cylinder_outer(self.connector_mount.outerRadius(), 10 + self.bottom_cover_thickness, center=True)
                        .down((10 + self.bottom_cover_thickness) / 2 + 0.3)
                    )
                    - self.finger_layout.key_place(
                        0, 0,
                        cube(
                            30,
                            30,
                            20,
                            center=True
                        ).up(10 - self.bottom_cover_offset)
                    ),
                    self.finger_layout.web_corner(column=1, row=0, left=True, top=True, **web_kwargs),
                    self.finger_layout.web_corner(column=1, row=0, left=True, top=False, **web_kwargs),
                )
                + self.finger_cover_edge(top_shell=False)
                - self.place_cover_magnets(self.cover_magnet_hole(top_shell=False))
                - hull()(
                    self.transform_connector_mount(
                        cylinder_outer(self.connector_mount.outerRadius() - self.connector_mount.outerFrameWidth, 20, center=True)
                    ),
                    self.finger_layout.web_corner(column=1, row=0, left=True, top=True, **web_kwargs),
                    self.finger_layout.web_corner(column=1, row=0, left=True, top=False, **web_kwargs),
                )
                - self.finger_layout.key_place(
                    2, -1,
                    cube(
                        60,
                        37,
                        30,
                        center=True
                    ).translate((3, 0, 10 - self.bottom_cover_offset))
                )
            )
        else:
            return (
                self.finger_layout.place_all(self.switch_bottom_cover)
                + self.finger_layout.web_all(**web_kwargs)
                + hull()(
                    self.finger_layout.web_corner(column=0, row=0, left=True, top=True, **web_kwargs),
                    self.cover_edge_corner(side=True, column=0, row=0, left=True, top=True, top_shell=False, offset_along_edge=4.4),
                    self.finger_layout.web_corner(column=0, row=1, left=True, top=True, **web_kwargs),
                    self.cover_edge_corner(side=True, column=0, row=1, left=True, top=True, top_shell=False, offset_along_edge=0),
                )
                + self.finger_cover_edge(top_shell=False)
                - self.place_cover_magnets(self.cover_magnet_hole(top_shell=False))
                - hull()(
                )
                - self.finger_layout.key_place(
                    2, -1,
                    cube(
                        60,
                        37,
                        30,
                        center=True
                    ).translate((3, 0, 10 - self.bottom_cover_offset))
                )
            )

    def finger_bottom_cover_nuts(self):
        """Generate tenting nuts for M6 bolts to union with the bottom cover.
        """
        web_kwargs = self.bottom_cover_web_kwargs()

        return (
            self.transform_finger_nut1(self.tenting_nut)
            + hull()(
                self.transform_finger_nut1(cube(10, 0.1, 10, center=True).translate((0, -5, 0))),
                self.finger_layout.web_corner(column=5, row=0, left=False, top=True, **web_kwargs),
                self.finger_layout.web_corner(column=5, row=0, left=True, top=True, **web_kwargs),
            )
            + self.transform_finger_nut2(self.tenting_nut)
            + hull()(
                self.transform_finger_nut2(cube(0.1, 10, 10, center=True).translate((-5, 0, 0))),
                self.finger_layout.web_corner(column=5, row=4, left=False, top=True, **web_kwargs),
                self.finger_layout.web_corner(column=5, row=4, left=False, top=False, **web_kwargs),
            )
            + self.transform_finger_nut3(self.tenting_nut)
            + hull()(
                self.transform_finger_nut3(cube(0.1, 10, 10, center=True).translate((5, 0, 0))),
                self.finger_layout.web_corner(column=0, row=1, left=True, top=True, **web_kwargs),
                self.finger_layout.web_corner(column=0, row=1, left=True, top=False, **web_kwargs),
            )
        )

    def finger_bottom_cover_feet(self):
        """Generate fixed feet to union with the bottom cover.
        """
        bottom_cover_attachment_spot = cube(
            self.finger_layout.keyswitch.keyswitch_width + self.wall_thickness * 2,
            self.finger_layout.keyswitch.keyswitch_length + self.wall_thickness * 2,
            0.1,
            center=True
        ).up(
            self.finger_layout.keyswitch.plate_thickness - self.thumb_layout.web_thickness / 2 - self.bottom_cover_offset - self.bottom_cover_thickness / 2
        )

        return (
            hull()(
                self.finger_layout.key_place(0, 1, bottom_cover_attachment_spot),
                cube(10, 10, 0.1, center=True).translate((-60, 45, 0.05)),
            )
            + hull()(
                self.finger_layout.key_place(0, 3, bottom_cover_attachment_spot),
                cube(10, 10, 0.1, center=True).translate((-60, -45, 0.05)),
            )
            + hull()(
                self.finger_layout.key_place(5, 0, bottom_cover_attachment_spot),
                cube(10, 10, 0.1, center=True).translate((70, 45, 0.05)),
            )
            + hull()(
                self.finger_layout.key_place(5, 4, bottom_cover_attachment_spot),
                cube(10, 10, 0.1, center=True).translate((70, -65, 0.05)),
            )
        )

    def finger_bottom_cover_with_tripod_mount(self):
        """Generate bottom cover with 40mm 1/4"-20 tripod mount.

        Use this tripod mount, style 2:
        https://www.aliexpress.com/item/1005006363751688.html
        """
        web_kwargs = self.bottom_cover_web_kwargs()

        z_offset = self.bottom_cover_offset + self.bottom_cover_thickness + 2

        mount_cylinder = cylinder_outer(r=50 / 2, h=8, center=True)

        mount_column = 2
        mount_row = 1.8

        finger = self.finger_layout
        tripod_mount = (
            hull()(
                finger.key_place(mount_column, mount_row, (
                    mount_cylinder & cube(100, 100, 100, center=True).left(50)
                ).down(z_offset)),
                finger.web_corner(column=mount_column - 1, row=round(mount_row) - 1, left=True, top=False, **web_kwargs),
                finger.web_corner(column=mount_column - 1, row=round(mount_row), left=True, top=True, **web_kwargs),
            )
            + hull()(
                finger.key_place(mount_column, mount_row, (
                    mount_cylinder & cube(100, 100, 100, center=True).right(50)
                ).down(z_offset)),
                finger.web_corner(column=mount_column + 1, row=round(mount_row) - 1, left=False, top=False, **web_kwargs),
                finger.web_corner(column=mount_column + 1, row=round(mount_row), left=False, top=True, **web_kwargs),
            )
            + hull()(
                finger.key_place(mount_column, mount_row, (
                    mount_cylinder & cube(100, 100, 100, center=True).forward(50)
                ).down(z_offset)),
                finger.web_corner(column=mount_column, row=round(mount_row) - 1, left=True, top=True, **web_kwargs),
                finger.web_corner(column=mount_column, row=round(mount_row) - 1, left=False, top=True, **web_kwargs),
            )
            + hull()(
                finger.key_place(mount_column, mount_row, (
                    mount_cylinder & cube(100, 100, 100, center=True).back(50)
                ).down(z_offset)),
                finger.web_corner(column=mount_column, row=round(mount_row) + 1, left=True, top=False, **web_kwargs),
                finger.web_corner(column=mount_column, row=round(mount_row) + 1, left=False, top=False, **web_kwargs),
            )
        )

        prong = cylinder_outer(r=4.1 / 2, h=6, center=True).down(z_offset - 1)
        tripod_mount_holes = (
            cylinder_outer(r=20 / 2, h=14, center=True)
            + cylinder_outer(r=40.2 / 2, h=12, center=True).up(6)
        ).down(z_offset)

        return (
            self.finger_bottom_cover()
            + tripod_mount
            - finger.key_place(mount_column, mount_row, tripod_mount_holes)
            + finger.key_place(mount_column, mount_row, (
                prong.right(15)
                + prong.left(15)
                + prong.forward(15)
                + prong.back(15)
            ))
        )

    def finger_bottom_cover_with_t_nut(self):
        """Generate bottom cover with 1/4"-20 carpentry T nut for tripod mounting.
        (e.g., https://www.amazon.de/-/en/gp/product/B0DK1HGGKM/ref=sw_img_1?smid=A301WKE65PGVT5&psc=1)
        """
        web_kwargs = self.bottom_cover_web_kwargs()

        z_offset = self.bottom_cover_offset + self.bottom_cover_thickness + 4

        mount_cylinder = cylinder_outer(r=26 / 2, h=10, center=True)

        tripod_mount = (
            hull()(
                self.finger_layout.key_place(2, 3, (
                    mount_cylinder & cube(100, 100, 100, center=True).left(50)
                ).down(z_offset)),
                self.finger_layout.web_corner(column=1, row=2, left=True, top=False, **web_kwargs),
                self.finger_layout.web_corner(column=1, row=3, left=True, top=True, **web_kwargs),
            )
            + hull()(
                self.finger_layout.key_place(2, 3, (
                    mount_cylinder & cube(100, 100, 100, center=True).right(50)
                ).down(z_offset)),
                self.finger_layout.web_corner(column=3, row=2, left=False, top=False, **web_kwargs),
                self.finger_layout.web_corner(column=3, row=3, left=False, top=True, **web_kwargs),
            )
            + hull()(
                self.finger_layout.key_place(2, 3, (
                    mount_cylinder & cube(100, 100, 100, center=True).forward(50)
                ).down(z_offset)),
                self.finger_layout.web_corner(column=2, row=2, left=True, top=True, **web_kwargs),
                self.finger_layout.web_corner(column=2, row=2, left=False, top=True, **web_kwargs),
            )
            + hull()(
                self.finger_layout.key_place(2, 3, (
                    mount_cylinder & cube(100, 100, 100, center=True).back(50)
                ).down(z_offset)),
                self.finger_layout.web_corner(column=2, row=4, left=True, top=False, **web_kwargs),
                self.finger_layout.web_corner(column=2, row=4, left=False, top=False, **web_kwargs),
            )
        )

        prong_hole = cylinder_outer(r=3 / 2, h=11, center=True).up(3)
        tripod_mount_holes = (
            cylinder_outer(r=7.9 / 2, h=14, center=True)
            + cylinder_outer(r=19 / 2, h=10, center=True).up(10)
            + prong_hole.right(7.5)
            + prong_hole.left(7.5)
            + prong_hole.forward(7.5)
            + prong_hole.back(7.5)
        ).down(z_offset)

        return (
            self.finger_bottom_cover()
            + tripod_mount
            - self.finger_layout.key_place(2, 3, tripod_mount_holes)
        )
    
    def thumb_part(self):
        """Generate the thumb part of the assembly.

        This includes the thumb well and the thumb nuts.
        """
        shape = (
            self.thumb_layout.place_all(self.switch_socket)
            + self.thumb_layout.web_all()

            + (
                (
                    #self.transform_thumb_nut1(self.tenting_nut)
                    #+ hull()(
                    #    self.transform_thumb_nut1(
                    #        cube((10, 0.1, 10), center=True)
                    #        .translate((0, 5, 0))
                    #    ),
                    #    self.thumb_layout.web_corner(0, 1, left=True, top=False),
                    #    self.thumb_layout.web_corner(0, 1, left=True, top=True),
                    #)
                    #+ hull()(
                    #    self.transform_thumb_nut1(
                    #        cube((0.1, 10, 10), center=True)
                    #        .translate((5, 0, 0))
                    #    ),
                    #    self.thumb_layout.web_corner(0, 1, left=False, top=False),
                    #    self.thumb_layout.web_corner(0, 1, left=True, top=False),
                    #)

                      self.transform_thumb_nut2(self.tenting_nut)
                     + hull()(
                         self.transform_thumb_nut2(
                             cube((10, 0.1, 10), center=True)
                             .translate((0, -5, 0))
                         ),
                         self.thumb_layout.web_corner(0, -1, left=True, top=True,),
                         self.thumb_layout.web_corner(0, -1, left=False, top=True,),
                     )

                ) if self.enable_nuts and self.bottom_thumb_nuts else nothing
            )
        )
        
        if self.use_color:
            return shape.color((0.1, 0.1, 0.1))

        return shape
    
    def thumb_part_balljoint(self):
        """Generate the thumb part of the assembly.

        This includes the thumb well and the thumb nuts.
        """
        shape = (
            self.thumb_layout.place_all(self.switch_socket)
            + self.thumb_layout.web_all()

            + (
                (
                    #self.transform_thumb_nut1(self.tenting_nut)
                    #+ hull()(
                    #    self.transform_thumb_nut1(
                    #        cube((10, 0.1, 10), center=True)
                    #        .translate((0, 5, 0))
                    #    ),
                    #    self.thumb_layout.web_corner(0, 1, left=True, top=False),
                    #    self.thumb_layout.web_corner(0, 1, left=True, top=True),
                    #)
                    #+ hull()(
                    #    self.transform_thumb_nut1(
                    #        cube((0.1, 10, 10), center=True)
                    #        .translate((5, 0, 0))
                    #    ),
                    #    self.thumb_layout.web_corner(0, 1, left=False, top=False),
                    #    self.thumb_layout.web_corner(0, 1, left=True, top=False),
                    #)

                      self.transform_thumb_nut2(self.tenting_nut)
                     + hull()(
                         self.transform_thumb_nut2(
                             cube((10, 0.1, 10), center=True)
                             .translate((0, -5, 0))
                         ),
                         self.thumb_layout.web_corner(0, -1, left=True, top=True,),
                         self.thumb_layout.web_corner(0, -1, left=False, top=True,),
                     )
                    + hull()(
                        self.transform_balljoint_ball(self.balljoint_ball_anchor()),
                        self.thumb_layout.web_corner(2, 0, left=True, top=True),
                        self.thumb_layout.web_corner(2, -1, left=True, top=True),
                     )

                ) if self.enable_nuts and self.bottom_thumb_nuts else nothing
            )

            #- self.thumb_layout.place_all(single_key_board(simple=True, extra_spacing=0.02))
            + self.transform_balljoint_ball(self.balljoint_ball())
        )
        

        if self.use_color:
            return shape.color((0.1, 0.1, 0.1))

        return shape

    def connector(self):
        """Generate the separate connector piece between the finger and thumb wells.
        """
        return (
            self.transform_finger_nut3(
                self.tenting_nut_unthreaded.down(10)
            )
            + self.transform_thumb_nut3(
                self.tenting_nut_unthreaded.down(10)
            )
            + hull()(
                self.transform_finger_nut3(
                    cube((10, 0.1, 10), center=True)
                    .translate((0, -5, -10))
                ),
                self.transform_thumb_nut3(
                    cube((10, 0.1, 10), center=True)
                    .translate((0, 5, -10))
                ),
            )
        )
    
    def single_piece(self):
        """Generate the single-piece upper assembly.

        This includes the finger part (finger well, board mount, and Mini-DIN connector mount) and thumb part (thumb
        well and thumb nuts), as well as mounts for magnets to attach the bottom cover.
        """
        return (
            self.finger_part()
            + hull()(
                self.finger_layout.web_corner(0, 2, left=True, top=False),
                self.finger_layout.web_corner(0, 3, left=True, top=True),
                self.thumb_layout.web_corner(2, -1, left=True, top=True),
                self.thumb_layout.web_corner(2, -1, left=True, top=False),
                self.thumb_layout.web_corner(1, -1, left=False, top=False),
                self.thumb_layout.web_corner(1, -1, left=False, top=True),
            )
            + hull()(
                self.finger_layout.web_corner(0, 3, left=True, top=True),
                self.finger_layout.key_place(
                    column=0,
                    row=3,
                    shape=cube(
                        (self.finger_layout.web_post_size, self.finger_layout.web_post_size, self.finger_layout.web_thickness),
                        center=True
                    ).translate((
                        -(
                            (self.finger_layout.keyswitch.keyswitch_width - self.finger_layout.web_post_size) / 2
                            + self.wall_thickness
                        ),
                        0,
                        -self.finger_layout.web_thickness / 2,
                    ))
                ),
                self.thumb_layout.web_corner(2, 0, left=True, top=True),
                self.thumb_layout.web_corner(2, -1, left=True, top=False),
                self.thumb_layout.web_corner(1, -1, left=False, top=False),
                self.thumb_layout.web_corner(1, 0, left=False, top=True),
            )
            + hull()(
                self.finger_layout.web_corner(0, 2, left=True, top=False),
                self.cover_edge_corner(side=True, column=0, row=2, left=True, top=True, top_shell=True, outer=True),
                self.thumb_layout.web_corner(2, -1, left=True, top=True),
                self.thumb_layout.web_corner(1, -1, left=False, top=True),
            )
            + self.thumb_part()
            - self.place_cover_magnets(self.cover_magnet_hole(top_shell=False))
        )


    def finger_balljoint(self):
        """Generate the single-piece upper assembly.

        This includes the finger part (finger well, board mount, and Mini-DIN connector mount) and thumb part (thumb
        well and thumb nuts), as well as mounts for magnets to attach the bottom cover.
        """
        return (
            self.finger_part()
            + hull()(
                self.transform_balljoint_socket(self.balljoint_socket_anchor()),
                self.finger_layout.web_corner(0, 2, left=True, top=True),
                self.finger_layout.web_corner(0, 3, left=True, top=True),
                self.cover_edge_corner(side=True, column=0, row=2, left=True, top=True, top_shell=True, outer=True),
            )
            + self.transform_balljoint_socket(self.balljoint_socket())
            - self.place_cover_magnets(self.cover_magnet_hole(top_shell=True))
            - self.transform_balljoint_socket(self.balljoint_socket_slit())
        )
    
    def single_piece_FDM(self):
        """Generate the single-piece upper assembly.

        This includes the finger part (finger well, board mount, and Mini-DIN connector mount) and thumb part (thumb
        well and thumb nuts), as well as mounts for magnets to attach the bottom cover.
        """
        return (
            self.finger_part()
            + hull()(
                self.finger_layout.web_corner(0, 2, left=True, top=False),
                self.finger_layout.web_corner(0, 3, left=True, top=True),
                self.thumb_layout.web_corner(2, -1, left=True, top=True),
                self.thumb_layout.web_corner(2, -1, left=True, top=False),
                self.thumb_layout.web_corner(1, -1, left=False, top=False),
                self.thumb_layout.web_corner(1, -1, left=False, top=True),
            )
            + hull()(
                self.finger_layout.web_corner(0, 3, left=True, top=True),
                self.finger_layout.key_place(
                    column=0,
                    row=3,
                    shape=cube(
                        (self.finger_layout.web_post_size, self.finger_layout.web_post_size, self.finger_layout.web_thickness),
                        center=True
                    ).translate((
                        -(
                            (self.finger_layout.keyswitch.keyswitch_width - self.finger_layout.web_post_size) / 2
                            + self.wall_thickness
                        ),
                        0,
                        -self.finger_layout.web_thickness / 2,
                    ))
                ),
                self.thumb_layout.web_corner(2, 0, left=True, top=True),
                self.thumb_layout.web_corner(2, -1, left=True, top=False),
                self.thumb_layout.web_corner(1, -1, left=False, top=False),
                self.thumb_layout.web_corner(1, 0, left=False, top=True),
            )
            + hull()(
                self.finger_layout.web_corner(0, 2, left=True, top=False),
                self.cover_edge_corner(side=True, column=0, row=2, left=True, top=True, top_shell=True, outer=True),
                self.thumb_layout.web_corner(2, -1, left=True, top=True),
                self.thumb_layout.web_corner(1, -1, left=False, top=True),
            )
            + self.thumb_part()
            - self.place_cover_magnets(self.cover_magnet_hole(top_shell=False))
            - self.thumb_mounting_holes() 
            - self.thumb_mount_separator()
        )
