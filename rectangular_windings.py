
import wx
from drawing import add_rect_vertical, add_rect_horizontal

# ----------------------Rectangular Geometry routines ----------------------
def create_left_top_right_angled(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I", w_length: int,
                                 w_height: int, clearance: int, track_width: int, track_spacing: int, n: int):
    """
    Draw a rectangular planar winding with true right-angled corners
    using filled rectangles. Starts from left-top and grows outward.
    All units are internal KiCad units (nm).

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

    if n < 1:
        wx.MessageBox("Number of turns must be >= 1",
                      "Geometry Error",
                      wx.OK | wx.ICON_ERROR)
        return

    t_width = track_width
    outward_increment = track_width + track_spacing

    cx, cy = center.x, center.y
    half_w = w_length // 2
    half_h = w_height // 2

    trace_offset = clearance + (t_width // 2)

    # First turn centerline rectangle
    left   = cx - half_w - trace_offset
    right  = cx + half_w + trace_offset
    top    = cy - half_h - trace_offset
    bottom = cy + half_h + trace_offset

    # Start at left-top inner side
    now_x = left
    now_y = cy - half_h

    for turn in range(n):

        first_turn_offset = 0
        if turn == 0:
            first_turn_offset = t_width // 2

        # ---------------------------------
        # Left vertical
        # ---------------------------------
        y1 = now_y + first_turn_offset
        y2 = bottom
        add_rect_vertical(board, now_x, y1, y2, t_width, layer)
        now_y = bottom

        # ---------------------------------
        # Bottom horizontal
        # ---------------------------------
        add_rect_horizontal(board, now_x, right, now_y, t_width, layer)
        now_x = right

        # ---------------------------------
        # Right vertical
        # ---------------------------------
        add_rect_vertical(board, now_x, now_y, top, t_width, layer)
        now_y = top

        # ---------------------------------
        # Single turn exit
        # ---------------------------------
        if n == 1:
            end_x = left
            add_rect_horizontal(board, now_x, end_x, now_y, t_width, layer)
            break

        # ---------------------------------
        # Top horizontal
        # ---------------------------------
        next_left = left - outward_increment
        if turn == n - 1:
            next_left = left
        add_rect_horizontal(board, now_x, next_left, now_y, t_width, layer)
        now_x = next_left

        # Expand rectangle outward
        left   -= outward_increment
        right  += outward_increment
        top    -= outward_increment
        bottom += outward_increment

def create_left_bottom_right_angled(board: "pcbnew.BOARD",
                                    layer: int,
                                    center: "pcbnew.VECTOR2I",
                                    w_length: int,
                                    w_height: int,
                                    clearance: int,
                                    track_width: int,
                                    track_spacing: int,
                                    n: int):
    """
    Draw a rectangular planar winding with true right-angled corners
    using filled rectangles.

    Start position: left-bottom
    Path order per turn:
        bottom -> right -> top -> left
    The winding grows outward from the inner window.

    All units are internal KiCad units (nm).

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

    if n < 1:
        wx.MessageBox("Number of turns must be >= 1",
                      "Geometry Error",
                      wx.OK | wx.ICON_ERROR)
        return

    t_width = track_width
    outward_increment = track_width + track_spacing

    cx, cy = center.x, center.y
    half_w = w_length // 2
    half_h = w_height // 2

    trace_offset = clearance + (t_width // 2)

    # First-turn centerline rectangle around the core/window
    left   = cx - half_w - trace_offset
    right  = cx + half_w + trace_offset
    top    = cy - half_h - trace_offset
    bottom = cy + half_h + trace_offset

    # Start at left-bottom on the first turn
    now_x = left + trace_offset
    now_y = bottom

    for turn in range(n):

        first_turn_offset = 0
        if turn == 0:
            first_turn_offset = t_width // 2

        # ---------------------------------
        # Bottom horizontal
        # ---------------------------------
        add_rect_horizontal(board, now_x + first_turn_offset, right, now_y, t_width, layer)
        now_x = right

        # ---------------------------------
        # Right vertical
        # ---------------------------------
        add_rect_vertical(board, now_x, now_y, top, t_width, layer)
        now_y = top

        # ---------------------------------
        # Top horizontal
        # ---------------------------------
        # next_left = left - outward_increment
        add_rect_horizontal(board, now_x, left, now_y, t_width, layer)
        now_x = left

        # ---------------------------------
        # Single turn exit
        # ---------------------------------
        if n == 1:
            end_y = bottom
            add_rect_vertical(board, now_x, now_y, end_y, t_width, layer)
            break

        # ---------------------------------
        # Left vertical
        # ---------------------------------
        next_bottom = bottom + outward_increment
        if turn == n - 1:
            next_bottom = bottom
        add_rect_vertical(board, now_x, now_y, next_bottom, t_width, layer)
        now_y = next_bottom

        # Expand outward for next turn
        left   -= outward_increment
        right  += outward_increment
        top    -= outward_increment
        bottom += outward_increment

def create_left_center_right_angled(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I", w_length: int,
                                    w_height: int, clearance: int, track_width: int, track_spacing: int, n: int):
    """
    Draw a rectangular planar winding with true right-angled corners
    using filled rectangles.

    Start position: left-center
    Path order per turn:
        left-down -> bottom -> right-up -> top -> left-down
    The winding grows outward from the inner window.

    All units are internal KiCad units (nm).

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

    if n < 1:
        wx.MessageBox("Number of turns must be >= 1",
                      "Geometry Error",
                      wx.OK | wx.ICON_ERROR)
        return

    t_width = track_width
    outward_increment = track_width + track_spacing

    cx, cy = center.x, center.y
    half_w = w_length // 2
    half_h = w_height // 2

    trace_offset = clearance + (t_width // 2)

    # First-turn centerline rectangle
    left   = cx - half_w - trace_offset
    right  = cx + half_w + trace_offset
    top    = cy - half_h - trace_offset
    bottom = cy + half_h + trace_offset

    # Start at left-center
    now_x = left
    now_y = cy + t_width // 2

    # Separation for single-turn entry/exit
    single_gap = track_spacing // 2

    for turn in range(n):

        # ---------------------------------
        # Left vertical: center -> bottom
        # ---------------------------------
        start_y = now_y
        if n == 1: # and turn == 0:
            start_y = now_y + single_gap

        add_rect_vertical(board, now_x, start_y, bottom, t_width, layer)
        now_y = bottom

        # ---------------------------------
        # Bottom horizontal
        # ---------------------------------
        add_rect_horizontal(board, now_x, right, now_y, t_width, layer)
        now_x = right

        # ---------------------------------
        # Right vertical
        # ---------------------------------
        add_rect_vertical(board, now_x, now_y, top, t_width, layer)
        now_y = top

        # ---------------------------------
        # Top horizontal
        # ---------------------------------
        next_left = left - (0 if n == 1 else outward_increment)
        add_rect_horizontal(board, now_x, next_left, now_y, t_width, layer)
        now_x = next_left

        # ---------------------------------
        # Left vertical: top -> center or next bottom
        # ---------------------------------
        if n == 1 or turn == n - 1:
            end_y = cy - single_gap - t_width // 2
            add_rect_vertical(board, now_x, now_y, end_y, t_width, layer)
            break
        else:
            next_bottom = bottom + outward_increment
            add_rect_vertical(board, now_x, now_y, next_bottom, t_width, layer)
            now_y = next_bottom

        # Expand outward for next turn
        left   -= outward_increment
        right  += outward_increment
        top    -= outward_increment
        bottom += outward_increment