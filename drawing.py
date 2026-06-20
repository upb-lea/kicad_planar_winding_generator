import pcbnew
import math
from geometry import v2, d2r, transform_point

def add_track(board, p1, p2, layer, width):
    """Add a straight copper TRACK segment on the board.
    :param board: Current board instance.
    :type: pcbnew.BOARD
    :param p1: Start point on board (nm).
    :type: pcbnew.VECTOR2I
    :param p2: End point on board.
    :type: pcbnew.VECTOR2I
    :param layer: Target KiCad layer ID (e.g., pcbnew.F_Cu).
    :type layer: int
    :param width: Width of straight copper TRACK segment (mm).
    :type width: float
    :rtype: None
    """
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(p1); t.SetEnd(p2)
    t.SetLayer(layer); t.SetWidth(max(width, 1))  # ensure nonzero width
    board.Add(t)

def add_arc(board, center, radius, ang_start_deg, ang_end_deg, layer, width):
    """Create a circular arc by start/mid/end points. Angles in degrees (0=+x, CCW positive).
    :param board: Current board instance
    :type: pcbnew.BOARD
    :param center: Center point of the arc on board (internal units, nm)
    :type: pcbnew.VECTOR2I
    :param radius: Radius of the arc measured from the center point (internal units, nm)
    :type: float
    :param ang_start_deg: Start angle of the arc in degrees. O degrees points in the +X direction.
                          Positive angles are counter-clockwise.TODO confirm if ccw or cw
    :type: float
    :param ang_end_deg: End angle of the arc in degrees. O degrees points in the +X direction.
                          Positive angles are counter-clockwise.
    :type: float
    :param layer: Target KiCad layer ID (e.g., pcbnew.F_Cu).
    :type layer: int
    :param width: Width of straight copper TRACK segment (mm).
    :type width: float
    :rtype: None
    """
    a1 = d2r(ang_start_deg)
    a3 = d2r(ang_end_deg)
    a2 = d2r((ang_start_deg + ang_end_deg) / 2.0)
    start = v2(center.x + radius * math.cos(a1), center.y + radius * math.sin(a1))
    mid   = v2(center.x + radius * math.cos(a2), center.y + radius * math.sin(a2))
    end   = v2(center.x + radius * math.cos(a3), center.y + radius * math.sin(a3))
    arc = pcbnew.PCB_ARC(board)
    arc.SetLayer(layer); arc.SetWidth(max(width, 1))
    arc.SetStart(start); arc.SetMid(mid); arc.SetEnd(end)
    board.Add(arc)

def add_rect(board, x, y, w, h, layer):
    """Add a filled polygon rect. All arguments in internal units (nm).

    The rectangle is created as a filled `pcbnew.PCB_SHAPE` polygon using
    four corner points. The point `(x, y)` defines the top-left corner of
    the rectangle in KiCad board coordinates. The rectangle extends in the
    positive X direction by `w` and in the positive Y direction by `h`.

    All coordinate and dimension arguments are expected to be in KiCad
    internal units, nanometers.

    :param board: Current board instance.
    :type board: pcbnew.BOARD
    :param x: X-coordinate of the rectangle's top-left corner, in internal KiCad units.
    :type x: int
    :param y: Y-coordinate of the rectangle's top-left corner, in internal KiCad units.
    :type y: int
    :param w: Width of the rectangle in the X direction, in internal KiCad units.
    :type w: int
    :param h: Height of the rectangle in the Y direction, in internal KiCad units.
    :type h: int
    :param layer: Target KiCad layer ID, for example `pcbnew.F_Cu`.
    :type layer: int
    :rtype: None
    """
    poly = pcbnew.PCB_SHAPE(board)
    poly.SetShape(pcbnew.SHAPE_T_POLY)
    poly.SetFilled(True)
    poly.SetLayer(layer)
    poly.SetWidth(0)
    pts = [v2(x, y),
           v2(x + w, y),
           v2(x + w, y + h),
           v2(x, y + h),
    ]
    poly.SetPolyPoints(pts)
    board.Add(poly)

def add_rect_mirrored(board, x, y, w, h, layer, center=None, mirror_x=False, mirror_y=False):
    """
    Add a filled rectangular polygon with optional mirroring.

    The input rectangle is defined by top-left corner `(x, y)` and
    dimensions `w` and `h`. If mirroring is enabled, two opposite corners
    are transformed about `center`, then the resulting rectangle is
    normalized before being added to the board.

    :param board: Current board instance.
    :type board: pcbnew.BOARD
    :param x: Rectangle left/top X coordinate in internal units.
    :type x: int
    :param y: Rectangle left/top Y coordinate in internal units.
    :type y: int
    :param w: Rectangle width in internal units.
    :type w: int
    :param h: Rectangle height in internal units.
    :type h: int
    :param layer: Target KiCad layer ID.
    :type layer: int
    :param center: Mirror reference point. Required if mirroring is enabled.
    :type center: pcbnew.VECTOR2I | None
    :param mirror_x: Mirror about X-axis through center.
    :type mirror_x: bool
    :param mirror_y: Mirror about Y-axis through center.
    :type mirror_y: bool
    :rtype: None
    """

    if not mirror_x and not mirror_y:
        add_rect(board, x, y, w, h, layer)
        return

    if center is None:
        raise ValueError("center must be provided when mirroring rectangles")

    # Original opposite corners
    x1, y1 = x, y
    x2, y2 = x + w, y + h

    # Transform opposite corners
    tx1, ty1 = transform_point(x1, y1, center, mirror_x, mirror_y)
    tx2, ty2 = transform_point(x2, y2, center, mirror_x, mirror_y)

    # Normalize back to top-left + positive width/height
    nx = min(tx1, tx2)
    ny = min(ty1, ty2)
    nw = abs(tx2 - tx1)
    nh = abs(ty2 - ty1)

    add_rect(board, nx, ny, nw, nh, layer)

def add_rect_vertical(board, x, y1, y2, width, layer, center=None, mirror_x=False, mirror_y=False):
    """
    Add a filled vertical rectangular copper segment to the board.

    This helper creates a vertical copper rectangle from a centerline-style
    definition. The segment centerline is located at X-coordinate `x` and
    extends vertically from `y1` to `y2`. The copper rectangle is expanded
    by `width / 2` on both sides of the centerline.

    The rectangle is also extended by `width / 2` beyond both vertical
    endpoints. This intentional extension allows adjacent horizontal
    rectangular segments to overlap at corners, producing fully filled
    right-angled corners without gaps or chamfered-looking edges.

    All coordinate and dimension arguments are expected to be in KiCad
    internal units, nanometers.

    :param board: Current board instance.
    :type board: pcbnew.BOARD
    :param x: X-coordinate of the vertical segment centerline, in internal KiCad units.
    :type x: int
    :param y1: Y-coordinate of one endpoint of the vertical centerline, in internal KiCad units.
    :type y1: int
    :param y2: Y-coordinate of the other endpoint of the vertical centerline, in internal KiCad units.
    :type y2: int
    :param width: Width of the copper segment, in internal KiCad units.
    :type width: int
    :param layer: Target KiCad layer ID, for example `pcbnew.F_Cu`.
    :type layer: int
    :param center: Mirror reference point. Required if mirroring is enabled.
    :type center: pcbnew.VECTOR2I | None
    :param mirror_x: Mirror about X-axis through center.
    :type mirror_x: bool
    :param mirror_y: Mirror about Y-axis through center.
    :type mirror_y: bool
    :rtype: None
    """
    half_width = width // 2
    x0 = x - half_width
    y0 = min(y1, y2) - half_width
    h  = abs(y2 - y1) + width
    add_rect_mirrored(board, x0, y0, width, h, layer, center = center,
                      mirror_x = mirror_x, mirror_y = mirror_y)

def add_rect_horizontal(board, x1, x2, y, width, layer, center=None, mirror_x=False, mirror_y=False):
    """
    Add a filled horizontal rectangular copper segment to the board.

    This helper creates a horizontal copper rectangle from a centerline-style
    definition. The segment centerline is located at Y-coordinate `y` and
    extends horizontally from `x1` to `x2`. The copper rectangle is expanded
    by `width / 2` on both sides of the centerline.

    The rectangle is also extended by `width / 2` beyond both horizontal
    endpoints. This intentional extension allows adjacent vertical
    rectangular segments to overlap at corners, producing fully filled
    right-angled corners without gaps or chamfered-looking edges.

    All coordinate and dimension arguments are expected to be in KiCad
    internal units, nanometers.

    :param board: Current board instance.
    :type board: pcbnew.BOARD
    :param x1: X-coordinate of one endpoint of the horizontal centerline, in internal KiCad units.
    :type x1: int
    :param x2: X-coordinate of the other endpoint of the horizontal centerline, in internal KiCad units.
    :type x2: int
    :param y: Y-coordinate of the horizontal segment centerline, in internal KiCad units.
    :type y: int
    :param width: Width of the copper segment, in internal KiCad units.
    :type width: int
    :param layer: Target KiCad layer ID, for example `pcbnew.F_Cu`.
    :type layer: int
    :param center: Mirror reference point. Required if mirroring is enabled.
    :type center: pcbnew.VECTOR2I | None
    :param mirror_x: Mirror about X-axis through center.
    :type mirror_x: bool
    :param mirror_y: Mirror about Y-axis through center.
    :type mirror_y: bool
    :rtype: None
    """
    half_width = width // 2
    x0 = min(x1, x2) - half_width
    y0 = y - half_width
    w  = abs(x2 - x1) + width
    add_rect_mirrored(board, x0, y0, w, width, layer, center = center,
                      mirror_x = mirror_x, mirror_y = mirror_y)