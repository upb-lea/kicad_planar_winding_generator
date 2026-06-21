import wx
import math
from drawing import add_track, add_arc, add_arc_transformed_points
from geometry import v2, validate_rounded_corner_core_clearance, transform_point


# ----------------------Rounded Geometry routines ----------------------
def create_left_center_single(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I",
                               w_length: int, w_height: int, r_corner: int, clearance: int,
                               track_width: int, track_spacing: int, mirror_x = False,
                              mirror_y = False):
    """Draw a single-turn rectangle winding starting from the left-center.
    Handles the left-side start/return segment separation correctly for any
    trace width: the two stub ends are separated centre-to-centre by exactly
    (track_width + track_spacing), so their rounded KiCad caps are
    track_spacing apart with no overlap.

    :param board: Current board instance
    :type: pcbnew.BOARD
    :param layer: Target KiCad layer ID (e.g., pcbnew.F_Cu).
    :type layer: int
    :param center: Center point of the winding on board (internal units, nm)
    :type: pcbnew.VECTOR2I
    :param w_length: Core length (center-leg), diameter for cylindrical cores
    :type: int (internal units, nm)
    :param w_height: Core width (center-leg), diameter for cylindrical cores
    :type: int (internal units, nm)
    :param r_corner: Radius of the arc forming the corners
    :type: int (internal units, nm)
    :param clearance: Spacing between the core center leg and the inner winding
    :type: int (internal units, nm)
    :param track_width: Width of the copper trace
    :type: int (internal units, nm)
    :param track_spacing: Minimum spacing between adjacent trace edges
    :type: int (internal units, nm)
    """

    # Validation for radius to avoid intrusion of the track arc into the core corners
    ok, msg = validate_rounded_corner_core_clearance(r_corner, clearance)

    if not ok:
        wx.MessageBox(
            msg,
            "Rounded Corner Geometry Error",
            wx.OK | wx.ICON_ERROR
        )
        return

    radius = min(r_corner, w_length // 2, w_height // 2)
    t_width = track_width
    Clearance = clearance

    f_length = w_length - 2 * radius  # straight horizontal portion length
    f_height = w_height - 2 * radius  # straight vertical portion length

    ax, ay = center.x, center.y
    radius_now = radius + Clearance + (t_width // 2)  # radius of the single corner arc

    #  Centre-to-centre offset between the two left stubs
    # KiCad caps each segment end with a semicircle of radius t_width/2.
    # For the cap edges to be exactly track_spacing apart the centres must be
    # track_width + track_spacing apart, so each stub shifts t_width//2 + t_spacing//2
    # away from ay.  Using integer division on the full sum avoids the
    # asymmetry that caused the previous half_gap rounding issue.
    half_sep = (t_width + track_spacing) // 2

    # Clamp: the stub must not push the arc centre outside the vertical extent
    # of the winding (it would pull the bottom-left arc off the core corner).
    max_half = (w_height // 2) + Clearance + (t_width // 2) - radius_now
    half_sep = min(half_sep, max(0, max_half))

    angle = 90  # degrees; may be reduced below if track width is large
    #if radius_now > ((w_height // 2) + Clearance + (t_width // 2)):
    # for large trace width adjust the angle to avoid overlap
    if t_width // 2 > w_height // 2 - radius:
        ratio = 1.0 - float(((w_height // 2) + Clearance - (track_spacing // 2))) / float(radius_now)
        ratio = max(-1.0, min(1.0, ratio))
        angle = int(round(180.0 * math.acos(ratio) / math.pi))

    #  Starting coordinates
    # Start stub: centre is at ay + half_sep (below centre-line)
    now_x = ax - (w_length // 2) - Clearance - (t_width // 2)
    now_y = ay + half_sep  # start stub centre-y

    #  Start stub: downward segment to bottom-left arc tangent
    if angle == 90:
        start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_point = transform_point(now_x, now_y + (f_height // 2) - half_sep, center, mirror_x, mirror_y)  # reach arc tangent
        add_track(board, start_point, end_point, layer, t_width)
        now_y = now_y + (f_height // 2) - half_sep

    #  Arc bottom-left
    arc_center = v2(now_x + radius_now, now_y)
    add_arc_transformed_points(board, arc_center, radius_now, 90, 90 + angle, layer, t_width,
                               center, mirror_x, mirror_y)
    now_x = now_x + radius_now
    now_y = now_y + radius_now

    #  Bottom straight
    start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
    end_point = transform_point(now_x + f_length, now_y, center, mirror_x, mirror_y)
    add_track(board, start_point, end_point, layer, t_width)
    now_x = now_x + f_length

    #  Arc bottom-right
    arc_center = v2(now_x, now_y - radius_now)
    add_arc_transformed_points(board, arc_center, radius_now, 0, 90, layer, t_width,
                               center, mirror_x, mirror_y)
    now_x = now_x + radius_now
    now_y = now_y - radius_now

    #  Right vertical straight
    start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
    end_point = transform_point(now_x, now_y - f_height, center, mirror_x, mirror_y)
    add_track(board, start_point, end_point, layer, t_width)
    now_y = now_y - f_height

    #  Arc top-right
    arc_center = v2(now_x - radius_now, now_y)
    add_arc_transformed_points(board, arc_center, radius_now, 270, 360, layer, t_width,
                               center, mirror_x, mirror_y)
    now_x = now_x - radius_now
    now_y = now_y - radius_now

    #  Top straight (rad_inc = 0 for single turn, no length extension)
    start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
    end_point = transform_point(now_x - f_length, now_y, center, mirror_x, mirror_y)
    add_track(board, start_point, end_point, layer, t_width)
    now_x = now_x - f_length

    #  Arc top-left (radius unchanged — single turn, no increment)
    arc_center = v2(now_x, now_y + radius_now)
    add_arc_transformed_points(board, arc_center, radius_now, 270 - angle, 270, layer, t_width,
                               center, mirror_x, mirror_y)
    now_x = now_x - radius_now
    now_y = now_y + radius_now

    #  Return stub: upward segment ending at ay - half_sep
    # Centre-to-centre distance between stubs = 2 * half_sep = t_width + t_spacing
    # Cap edges are therefore exactly track_spacing apart.
    if angle == 90:
        start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_point = transform_point(now_x, ay - half_sep, center, mirror_x, mirror_y)  # return stub centre-y
        add_track(board, start_point, end_point, layer, t_width)

def create_left_center(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I",
                       w_length: int, w_height: int, r_corner: int, clearance: int,
                       track_width: int, track_spacing: int, n: int, mirror_x = False,
                       mirror_y = False):
    """Draw a rectangle spiral starting from the left-center. All internal geometry is integer nanometers.
    For n == 1 delegates to create_left_center_single() which handles the
    left-side stub separation correctly for any trace width.

    :param board: Current board instance
    :type: pcbnew.BOARD
    :param layer: Target KiCad layer ID (e.g., pcbnew.F_Cu).
    :type layer: int
    :param center: Center point of the winding on board (internal units, nm)
    :type: pcbnew.VECTOR2I
    :param w_length: Core length (center-leg), diameter for cylindrical cores
    :type: int (internal units, nm)
    :param w_height: Core width (center-leg), diameter for cylindrical cores
    :type: int (internal units, nm)
    :param r_corner: Radius of the arc forming the corners
    :type: int (internal units, nm)
    :param clearance: spacing between the core center leg and the inner winding
    :type: int (internal units, nm)
    :param track_width: Width of the copper trace
    :type: int (internal units, nm)
    :param track_spacing: Spacing between two adjacent traces
    :type: int (internal units, nm)
    :param n: number of turns
    :type: int (internal units, nm)
    """

    # Validation for radius to avoid intrusion of the track arc into the core corners
    ok, msg = validate_rounded_corner_core_clearance(r_corner, clearance)

    if not ok:
        wx.MessageBox(
            msg,
            "Rounded Corner Geometry Error",
            wx.OK | wx.ICON_ERROR
        )
        return

    # if r_corner == 0:
    #     create_left_center_right_angled(board, layer, center, w_length, w_height, clearance, track_width, track_spacing, n)
    #     return

    if n == 1:
        create_left_center_single(board, layer, center, w_length, w_height, r_corner, clearance,
                                  track_width, track_spacing, mirror_x=mirror_x, mirror_y=mirror_y)
        return

    #  Multi-turn path (n > 1)
    radius = min(r_corner, w_length // 2, w_height // 2)
    t_width = track_width
    Clearance = clearance

    f_length = w_length - 2 * radius
    f_height = w_height - 2 * radius

    t_spacing = track_spacing
    windings = n

    ax, ay = center.x, center.y
    now_x = ax - (w_length // 2) - Clearance - (t_width // 2)
    now_y = ay #TODO adjust the y start point by half the trace width
    radius_now = radius + Clearance + (t_width // 2)

    angle = 90
    rad_inc1 = (t_spacing // 2) + (t_width // 2)
    rad_inc2 = rad_inc1
    #TODO: adopt condition similar to create_left_center_single
    #if radius_now > ((w_height // 2) + Clearance + (t_width // 2)):
    if t_width // 2 > w_height // 2 - radius:
        ratio = 1.0 - float(((w_height // 2) + Clearance - (t_spacing // 2))) / float(radius_now)
        ratio = max(-1.0, min(1.0, ratio))
        angle = int(round(180.0 * math.acos(ratio) / math.pi))

    for _ in range(windings):
        if angle == 90:
            start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
            end_point = transform_point(now_x, now_y + (f_height // 2), center, mirror_x, mirror_y)
            add_track(board, start_point, end_point, layer, t_width)
            now_y = now_y + (f_height // 2)

        # Arc bottom-left
        arc_center = v2(now_x + radius_now, now_y)
        add_arc_transformed_points(board, arc_center, radius_now, 90, 90 + angle, layer, t_width,
                                   center, mirror_x, mirror_y)
        now_x = now_x + radius_now
        now_y = now_y + radius_now

        # Bottom straight
        start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_point = transform_point(now_x + f_length, now_y, center, mirror_x, mirror_y)
        add_track(board, start_point, end_point, layer, t_width)
        now_x = now_x + f_length

        # Arc bottom-right
        arc_center = v2(now_x, now_y - radius_now)
        add_arc_transformed_points(board, arc_center, radius_now, 0, 90, layer, t_width,
                                   center, mirror_x, mirror_y)
        now_x = now_x + radius_now
        now_y = now_y - radius_now

        # Right vertical straight
        start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_point = transform_point(now_x, now_y - f_height, center, mirror_x, mirror_y)
        add_track(board, start_point, end_point, layer, t_width)
        now_y = now_y - f_height

        # Arc top-right
        arc_center = v2(now_x - radius_now, now_y)
        add_arc_transformed_points(board, arc_center, radius_now, 270, 360, layer, t_width,
                                   center, mirror_x, mirror_y)
        now_x = now_x - radius_now
        now_y = now_y - radius_now

        # Top straight
        start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_point = transform_point(now_x - f_length - rad_inc2, now_y, center, mirror_x, mirror_y)
        add_track(board, start_point, end_point, layer, t_width)
        now_x = now_x - f_length - rad_inc2

        radius_now = radius_now + rad_inc1

        # Arc top-left
        arc_center = v2(now_x, now_y + radius_now)
        add_arc_transformed_points(board, arc_center, radius_now, 270 - angle, 270, layer, t_width,
                                   center, mirror_x, mirror_y)
        now_x = now_x - radius_now
        now_y = now_y + radius_now

        if angle == 90:
            start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
            end_point = transform_point(now_x, ay, center, mirror_x, mirror_y)
            add_track(board, start_point, end_point, layer, t_width)
            now_y = ay

        radius_now = radius_now + rad_inc2


def create_left_bottom(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I",
                       w_length: int, w_height: int, r_corner: int, clearance: int,
                       track_width: int, track_spacing: int, n: int, mirror_x = False,
                       mirror_y = False):
    """Draw a rectangle spiral starting from the left-top. All internal geometry is integer nanometers.

    :param board: Current board instance
    :type: pcbnew.BOARD
    :param layer: Target KiCad layer ID (e.g., pcbnew.F_Cu).
    :type layer: int
    :param center: Center point of the winding on board (internal units, nm)
    :type: pcbnew.VECTOR2I
    :param w_length: Core length (center-leg), diameter for cylindrical cores
    :type: int (internal units, nm)
    :param w_height: Core width (center-leg), diameter for cylindrical cores
    :type: int (internal units, nm)
    :param r_corner: Radius of the arc forming the corners
    :type: int (internal units, nm)
    :param clearance: spacing between the core center leg and the inner winding
    :type: int (internal units, nm)
    :param track_width: Width of the copper trace
    :type: int (internal units, nm)
    :param track_spacing: Spacing between two adjacent traces
                          Spacing between two adjacent turns on the same layer
    :type: int (internal units, nm)
    :param n: number of turns
    :type: int (internal units, nm)
    """

    # Validation for radius to avoid intrusion of the track arc into the core corners
    ok, msg = validate_rounded_corner_core_clearance(r_corner, clearance)

    if not ok:
        wx.MessageBox(
            msg,
            "Rounded Corner Geometry Error",
            wx.OK | wx.ICON_ERROR
        )
        return

    # if n == 1:
    #     create_left_center(board, layer, center, w_length, w_height, r_corner, clearance, track_width, track_spacing, n)
    #     return

    # if r_corner == 0:
    #     create_left_bottom_right_angled(board, layer, center, w_length, w_height, clearance, track_width, track_spacing, n)
    #     return

    radius = min(r_corner, w_length // 2, w_height // 2)
    t_width = track_width
    Clearance = clearance

    f_length = w_length - 2 * radius
    f_height = w_height - 2 * radius

    t_spacing = track_spacing
    radius_now = radius + Clearance + (t_width // 2)

    ax, ay = center.x, center.y
    now_x = ax - (f_length // 2)
    now_y = ay + (w_height // 2) + Clearance + (t_width // 2)

    for _ in range(n):
        # add a slight offset for the first turn to prevent overlap
        first_turn_offset = 0
        if _ == 0:
            first_turn_offset = t_width // 2

        # Bottom straight
        start_point = transform_point(now_x + first_turn_offset, now_y, center, mirror_x, mirror_y)
        end_point = transform_point(now_x + f_length, now_y, center, mirror_x, mirror_y)
        add_track(board, start_point,end_point ,layer, t_width)
        now_x = now_x + f_length

        # Arc bottom-right
        arc_center = v2(now_x, now_y - radius_now)
        add_arc_transformed_points(board, arc_center, radius_now, 0, 90, layer, t_width,
                                   center, mirror_x, mirror_y)
        now_x = now_x + radius_now
        now_y = now_y - radius_now

        # Right vertical straight
        start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_point = transform_point(now_x, now_y - f_height, center, mirror_x, mirror_y)
        add_track(board, start_point,end_point ,layer, t_width)
        now_y = now_y - f_height

        # Arc top-right
        arc_center = v2(now_x - radius_now, now_y)
        add_arc_transformed_points(board, arc_center, radius_now, 270, 360, layer, t_width,
                                   center, mirror_x, mirror_y)
        now_x = now_x - radius_now
        now_y = now_y - radius_now

        # Top straight
        start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_point = transform_point(now_x - f_length, now_y, center, mirror_x, mirror_y)
        add_track(board, start_point, end_point, layer, t_width)
        now_x = now_x - f_length

        # Arc top-left
        arc_center = v2(now_x, now_y + radius_now)
        add_arc_transformed_points(board, arc_center, radius_now, 180, 270, layer, t_width,
                                   center, mirror_x, mirror_y)
        now_x = now_x - radius_now
        now_y = now_y + radius_now

        # Left straight
        # Break here for single turn
        if n == 1:
            start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
            end_point = transform_point(now_x, now_y + f_height + t_width // 2 + t_spacing // 2, center, mirror_x, mirror_y)
            add_track(board, start_point, end_point, layer, t_width)
            break

        start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_point = transform_point(now_x, now_y + f_height + t_width + t_spacing, center, mirror_x, mirror_y)
        add_track(board, start_point, end_point, layer, t_width)
        now_y = now_y + f_height + t_width + t_spacing

        arc_center = v2(now_x + radius_now, now_y)
        add_arc_transformed_points(board, arc_center, radius_now, 90, 180, layer, t_width,
                                   center, mirror_x, mirror_y)
        now_x = now_x + radius_now
        now_y = now_y + radius_now

        radius_now = radius_now + t_spacing + t_width


def create_left_top(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I",
                    w_length: int, w_height: int, r_corner: int, clearance: int,
                    track_width: int, track_spacing: int, n: int, mirror_x = False, mirror_y = False):
    """Draw a rectangle spiral starting from the left-bottom. All internal geometry is integer nanometers.

    :param board: Current board instance
    :type: pcbnew.BOARD
    :param layer: Target KiCad layer ID (e.g., pcbnew.F_Cu).
    :type layer: int
    :param center: Center point of the winding on board (internal units, nm)
    :type: pcbnew.VECTOR2I
    :param w_length: Core length (center-leg), diameter for cylindrical cores
    :type: int (internal units, nm)
    :param w_height: Core width (center-leg), diameter for cylindrical cores
    :type: int (internal units, nm)
    :param r_corner: Radius of the arc forming the corners
    :type: int (internal units, nm)
    :param clearance: spacing between the core center leg and the inner winding
    :type: int (internal units, nm)
    :param track_width: Width of the copper trace
    :type: int (internal units, nm)
    :param track_spacing: Spacing between two adjacent traces
                          Spacing between two adjacent turns on the same layer
    :type: int (internal units, nm)
    :param n: number of turns
    :type: int (internal units, nm)
    """

    # Validation for radius to avoid intrusion of the track arc into the core corners
    ok, msg = validate_rounded_corner_core_clearance(r_corner, clearance)

    if not ok:
        wx.MessageBox(
            msg,
            "Rounded Corner Geometry Error",
            wx.OK | wx.ICON_ERROR
        )
        return

    # if n == 1:
    #     create_left_center(board, layer, center, w_length, w_height, r_corner, clearance, track_width, track_spacing, n)
    #     return
    # if r_corner == 0:
    #     create_left_top_right_angled(board, layer, center, w_length, w_height, clearance, track_width, track_spacing, n)
    #     return

    radius = min(r_corner, w_length // 2, w_height // 2)
    t_width = track_width
    Clearance = clearance

    f_length = w_length - 2 * radius
    f_height = w_height - 2 * radius

    track_spacing = track_spacing
    radius_now = radius + Clearance + (t_width // 2)

    ax, ay = center.x, center.y
    now_x = ax - (w_length // 2) - Clearance - (t_width // 2)
    now_y = ay - (f_height // 2)

    for _ in range(n):
        # add a slight offset for the first turn to prevent overlap
        first_turn_offset = 0
        if _ == 0:
            first_turn_offset = t_width // 2

        # Left straight
        start_point = transform_point(now_x, now_y + first_turn_offset, center, mirror_x, mirror_y)
        end_point = transform_point(now_x, now_y + f_height, center, mirror_x, mirror_y)
        add_track(board, start_point, end_point, layer, t_width)
        now_y = now_y + f_height

        # Arc bottom-left
        arc_center = v2(now_x + radius_now, now_y)
        add_arc_transformed_points(board, arc_center, radius_now, 90, 180, layer, t_width,
                                   center, mirror_x, mirror_y)
        now_x = now_x + radius_now
        now_y = now_y + radius_now

        # Bottom straight
        start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_point = transform_point(now_x + f_length, now_y, center, mirror_x, mirror_y)
        add_track(board, start_point, end_point, layer, t_width)
        now_x = now_x + f_length

        # Arc bottom-right
        arc_center = v2(now_x, now_y - radius_now)
        add_arc_transformed_points(board, arc_center, radius_now, 0, 90, layer, t_width,
                                   center, mirror_x, mirror_y)
        now_x = now_x + radius_now
        now_y = now_y - radius_now

        # Right vertical straight
        start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_point = transform_point(now_x, now_y - f_height, center, mirror_x, mirror_y)
        add_track(board, start_point, end_point, layer, t_width)
        now_y = now_y - f_height

        # Arc top-right
        arc_center = v2(now_x - radius_now, now_y)
        add_arc_transformed_points(board, arc_center, radius_now, 270, 360, layer, t_width,
                                   center, mirror_x, mirror_y)
        now_x = now_x - radius_now
        now_y = now_y - radius_now

        # Top straight
        # Break here for single turn
        if n == 1:
            start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
            end_point = transform_point(now_x - f_length - t_width // 2 - track_spacing // 2, now_y, center, mirror_x, mirror_y)
            add_track(board, start_point, end_point, layer, t_width)
            break

        # Top straight
        start_point = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_point = transform_point(now_x - f_length - t_width - track_spacing, now_y, center, mirror_x, mirror_y)
        add_track(board, start_point, end_point, layer, t_width)
        now_x = now_x - f_length - t_width - track_spacing

        # Arc top-left
        arc_center = v2(now_x, now_y + radius_now)
        add_arc_transformed_points(board, arc_center, radius_now, 180, 270, layer, t_width,
                center, mirror_x, mirror_y)
        now_x = now_x - radius_now
        now_y = now_y + radius_now

        radius_now = radius_now + track_spacing + t_width