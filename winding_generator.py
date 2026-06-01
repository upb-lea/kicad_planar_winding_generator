# Winding Generator – faithful port of Altium CreateLeftCenter/LeftTop/LeftBottom
# KiCad 7/8/9. Units: dialog in mm; pcbnew uses nanometers (FromMM/ToMM).
# """Generating a code for drawing the windings in Kickad, starting from the left top corner, center, or bottom left."""

import pcbnew
import wx
import math
import os

# Set True to draw a short line at the chosen center for verification
debug_test = False

MM = pcbnew.FromMM

def to_mm(v_nm):
    """Converts nm to mm
    :param v_nm: nm to convert
    :type v_nm: str
    """
    return pcbnew.to_mm(v_nm)

def d2r(a):
    """Converts degrees to radians.
    :param a: Degrees to convert to radians
    :type a: float
    """
    return a * math.pi / 180.0

def v2(x, y):
    """Return a KiCad VECTOR2I point from (x, y), casting to ints (nm units).
    :param x: X coordinate
    :type x: float
    :param y: Y coordinate
    :type y: float
    """
    return pcbnew.VECTOR2I(int(x), int(y))

def transform_point(x, y, center, mirror_x=False, mirror_y=False):
    """Return a KiCad VECTOR2I point from (x, y), casting to ints (nm units).
    :param x: X coordinate
    :type x: float
    :param y: Y coordinate
    :type y: float
    """
    if mirror_y:
        x = 2 * center.x - x
    if mirror_x:
        y = 2 * center.y - y
    return pcbnew.VECTOR2I(int(x), int(y))

def transform_angle(a, mirror_x=False, mirror_y=False):
    if mirror_y:
        a = 180 - a
    if mirror_x:
        a = -a
    return a % 360

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

# def add_arc(board, center, radius, ang_start_deg, ang_end_deg, layer, width):
#     """Create a circular arc by start/mid/end points. Angles in degrees (0=+x, CCW positive).
#     :param board: Current board instance
#     :type: pcbnew.BOARD
#     :param center: Center point of the arc on board (internal units, nm)
#     :type: pcbnew.VECTOR2I
#     :param radius: Radius of the arc measured from the center point (internal units, nm)
#     :type: float
#     :param ang_start_deg: Start angle of the arc in degrees. O degrees points in the +X direction.
#                           Positive angles are counter-clockwise.TODO confirm if ccw or cw
#     :type: float
#     :param ang_end_deg: End angle of the arc in degrees. O degrees points in the +X direction.
#                           Positive angles are counter-clockwise.
#     :type: float
#     :param layer: Target KiCad layer ID (e.g., pcbnew.F_Cu).
#     :type layer: int
#     :param width: Width of straight copper TRACK segment (mm).
#     :type width: float
#     :rtype: None
#     """
#     a1 = d2r(ang_start_deg)
#     a3 = d2r(ang_end_deg)
#     a2 = d2r((ang_start_deg + ang_end_deg) / 2.0)
#     start = v2(center.x + radius * math.cos(a1), center.y + radius * math.sin(a1))
#     mid   = v2(center.x + radius * math.cos(a2), center.y + radius * math.sin(a2))
#     end   = v2(center.x + radius * math.cos(a3), center.y + radius * math.sin(a3))
#     arc = pcbnew.PCB_ARC(board)
#     arc.SetLayer(layer); arc.SetWidth(max(width, 1))
#     arc.SetStart(start); arc.SetMid(mid); arc.SetEnd(end)
#     board.Add(arc)

def arc_points_from_center(center, radius, angle_start_deg, angle_end_deg):
    """
    Compute start, mid, and end points for a circular arc.

    Uses KiCad-style board coordinates:
    0 deg = +X/right
    90 deg = +Y/down
    180 deg = left
    270 deg = up

    The midpoint is chosen on the shortest sweep between start and end.
    """

    # Compute shortest signed angular sweep
    delta = (angle_end_deg - angle_start_deg) % 360

    if delta > 180:
        delta -= 360

    angle_mid_deg = angle_start_deg + delta / 2.0

    def point_at(angle_deg):
        angle_rad = math.radians(angle_deg)
        return v2(
            int(round(center.x + radius * math.cos(angle_rad))),
            int(round(center.y + radius * math.sin(angle_rad)))
        )

    start = point_at(angle_start_deg)
    mid   = point_at(angle_mid_deg)
    end   = point_at(angle_end_deg)

    return start, mid, end

def add_arc_points(board, start, mid, end, layer, width):
    """
    Add a PCB arc using explicit start, mid, and end points.

    :param board: Current board instance.
    :type board: pcbnew.BOARD
    :param start: Arc start point.
    :type start: pcbnew.VECTOR2I
    :param mid: Arc midpoint defining curvature.
    :type mid: pcbnew.VECTOR2I
    :param end: Arc end point.
    :type end: pcbnew.VECTOR2I
    :param layer: Target KiCad layer.
    :type layer: int
    :param width: Arc track width in internal units.
    :type width: int
    """
    arc = pcbnew.PCB_ARC(board)
    arc.SetLayer(layer)
    arc.SetWidth(max(width, 1))
    arc.SetStart(start)
    arc.SetMid(mid)
    arc.SetEnd(end)
    board.Add(arc)

def add_arc_transformed_points(board, center, radius,
                               angle_start_deg, angle_end_deg,
                               layer, width,
                               mirror_center,
                               mirror_x=False,
                               mirror_y=False):
    """
    Add an arc after transforming its start/mid/end points.

    This avoids transforming arc angles directly.
    """

    start, mid, end = arc_points_from_center(
        center, radius, angle_start_deg, angle_end_deg)

    start_transformed = transform_point(start.x, start.y, mirror_center, mirror_x, mirror_y)
    mid_transformed   = transform_point(mid.x,   mid.y,   mirror_center, mirror_x, mirror_y)
    end_transformed   = transform_point(end.x,   end.y,   mirror_center, mirror_x, mirror_y)

    add_arc_points(board, start_transformed, mid_transformed, end_transformed, layer, width)

def layer_id(board, name):
    """Resolve a human-readable layer name to a KiCad layer ID.

    :param board: Current board instance
    :type: pcbnew.BOARD
    :param name: KiCad layer name (e.g "F.Cu", "B.Cu")
    :type: str
    :return: KiCad layer ID
    :rtype: int
    """

    lid = board.GetLayerID(name)
    return lid if lid != -1 else pcbnew.F_Cu


# ---------------------- Parameters dialog ----------------------
class ParamsDialog(wx.Dialog):
    """Single dialog. Click 'Use mouse' to capture center; OK to draw."""
    def __init__(self, parent):
        """Initialize and lay out the dialog UI."""
        super().__init__(parent, title="Place Planar Transformer Track",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetMinSize(wx.Size(600, 720))

        # Root panel/sizer for all controls
        p = wx.Panel(self)
        s = wx.BoxSizer(wx.VERTICAL)

        # --- Center rows (X/Y) (mouse capture removed) ---
        grid_c = wx.FlexGridSizer(2, 2, 6, 8)  # 2 cols now
        grid_c.AddGrowableCol(1, 1)
        grid_c.Add(wx.StaticText(p, label="Center X:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.cx = wx.TextCtrl(p, value="0.0", style=wx.TE_RIGHT)
        grid_c.Add(self.cx, 1, wx.EXPAND)
        grid_c.Add(wx.StaticText(p, label="Center Y:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.cy = wx.TextCtrl(p, value="0.0", style=wx.TE_RIGHT)
        grid_c.Add(self.cy, 1, wx.EXPAND)
        s.Add(grid_c, 0, wx.EXPAND | wx.BOTTOM, 8)

        def row(lbl, default):
            """Helper to add a labeled text field aligned in a single row."""
            hs = wx.BoxSizer(wx.HORIZONTAL)
            hs.Add(wx.StaticText(p, label=lbl), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
            tc = wx.TextCtrl(p, value=default, style=wx.TE_RIGHT)
            hs.Add(tc, 1, wx.EXPAND)
            s.Add(hs, 0, wx.EXPAND | wx.BOTTOM, 6)
            return tc

        # Parameter names (all mm)
        self.gap    = row("Turn-Core (mm):", "0.30")       # inner clearance
        #self.radius = row("Radius (mm):", "2.00")    # corner radius
        self.twidth = row("Width (mm):", "0.25")     # track width
        self.guard  = row("Turn-Turn (mm):", "0.25")     # track-to-track spacing

        props = wx.StaticBoxSizer(wx.VERTICAL, p, "Properties")
        grid  = wx.FlexGridSizer(2, 4, 6, 8)
        grid.AddGrowableCol(1, 1); grid.AddGrowableCol(3, 1)
        grid.Add(wx.StaticText(p, label="Turns"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.turns  = wx.TextCtrl(p, value="6", style=wx.TE_RIGHT); grid.Add(self.turns, 1, wx.EXPAND)
        grid.Add(wx.StaticText(p, label="Width <w> (mm)"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.size_x = wx.TextCtrl(p, value="20.0", style=wx.TE_RIGHT); grid.Add(self.size_x, 1, wx.EXPAND)
        grid.Add(wx.StaticText(p, label="Height <h> (mm)"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.size_y = wx.TextCtrl(p, value="16.0", style=wx.TE_RIGHT); grid.Add(self.size_y, 1, wx.EXPAND)
        props.Add(grid, 0, wx.EXPAND | wx.ALL, 4)

        # # Winding corner type selector
        hl_corner = wx.BoxSizer(wx.HORIZONTAL)

        corner_label = wx.StaticText(p, label="Winding Corner Type")
        hl_corner.Add(corner_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self.corner_choice = wx.Choice(p,
                                       choices=["Rounded Corner", "Right Angled Corner"])

        self.corner_choice.SetSelection(0)

        hl_corner.Add(self.corner_choice, 1, wx.EXPAND | wx.RIGHT, 12)

        props.Add(hl_corner, 0, wx.EXPAND | wx.TOP, 4)

        # Radius Input
        self.radius_row = wx.BoxSizer(wx.HORIZONTAL)

        self.radius_label = wx.StaticText(p, label="Radius (mm):")
        self.radius_row.Add(self.radius_label,
                            0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self.radius_ctrl = wx.TextCtrl(p, value="0.0", style = wx.TE_RIGHT)
        self.radius_row.Add(self.radius_ctrl,
                            1, wx.EXPAND | wx.RIGHT, 12)

        props.Add(self.radius_row, 0, wx.EXPAND | wx.TOP, 4)

        self.corner_choice.Bind(wx.EVT_CHOICE, self.on_corner_type_change)
        wx.CallAfter(self.update_corner_ui)

        # Layer selector
        hl = wx.BoxSizer(wx.HORIZONTAL)
        hl.Add(wx.StaticText(p, label="Layer"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.layer_choice = wx.Choice(p, choices=["F.Cu", "B.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"])
        self.layer_choice.SetSelection(0)
        hl.Add(self.layer_choice, 1, wx.EXPAND | wx.RIGHT, 12)
        props.Add(hl, 0, wx.EXPAND | wx.TOP, 4)
        s.Add(props, 0, wx.EXPAND | wx.BOTTOM | wx.TOP, 6)

        # Start position radio buttons (Left Top / Left Center / Left Bottom)
        start_box = wx.StaticBoxSizer(wx.VERTICAL, p, "Winding start position")
        self.rb_top    = wx.RadioButton(p, label="Left Top", style=wx.RB_GROUP)
        self.rb_center = wx.RadioButton(p, label="Left Center")
        self.rb_bottom = wx.RadioButton(p, label="Left Bottom")
        self.rb_center.SetValue(True)
        start_box.Add(self.rb_top); start_box.Add(self.rb_center); start_box.Add(self.rb_bottom)
        s.Add(start_box, 0, wx.EXPAND | wx.BOTTOM, 6)

        # Mirror options check box
        mirror_box = wx.StaticBoxSizer(wx.StaticBox(p, label="Mirror"), wx.HORIZONTAL)

        self.mirror_x_cb = wx.CheckBox(p, label="Mirror X")
        self.mirror_y_cb = wx.CheckBox(p, label="Mirror Y")

        mirror_box.Add(self.mirror_x_cb, 0, wx.RIGHT, 10)
        mirror_box.Add(self.mirror_y_cb, 0)

        s.Add(mirror_box, 0, wx.EXPAND | wx.TOP, 6)

        # ---------------------- Parameter diagram (no scaling) ----------------------
        diag_box = wx.StaticBoxSizer(wx.VERTICAL, p, "Parameter diagram")
        self._diag_bmp = wx.StaticBitmap(p, bitmap=wx.NullBitmap)
        self._diag_bmp.SetMinSize(wx.Size(-1, 100))
        diag_box.Add(self._diag_bmp, 1, wx.EXPAND | wx.ALL, 6)
        s.Add(diag_box, 1, wx.EXPAND | wx.TOP, 4)

        # Load image at native size (no resampling)
        self._orig_img = None
        img_path = os.path.join(os.path.dirname(__file__), "parameter_sketch.png")
        if os.path.isfile(img_path):
            try:
                _img = wx.Image(img_path, wx.BITMAP_TYPE_ANY)
                if _img.IsOk():
                    self._orig_img = _img
                    self._diag_bmp.SetBitmap(wx.Bitmap(self._orig_img))
            except Exception:
                pass
        else:
            diag_box.Add(wx.StaticText(p, label=f"Image not found: {img_path}"), 0, wx.ALL | wx.ALIGN_CENTER, 6)
        # -----------------------------------------------------------------------------------

        p.SetSizer(s)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(p, 1, wx.ALL | wx.EXPAND, 10)
        btns = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(root)

        # Internal state: captured center (removed mouse capture → always None)
        self.center_nm = None

    def _on_dialog_resize(self, evt):
        evt.Skip()

    def _refresh_diagram_bitmap(self):
        return

    def get(self):
        """Return parameters in mm plus the captured center in nm (or None)."""
        def f(v): return float(v)
        start = 1  # default Left-Center
        if self.rb_top.GetValue(): start = 0
        if self.rb_bottom.GetValue(): start = 2
        # r = 0.0
        if self.corner_choice.GetSelection() == 0:
            r = float(self.radius_ctrl.GetValue())
        else:
            r = 0.0

        return dict(
            cx_mm=f(self.cx.GetValue()),
            cy_mm=f(self.cy.GetValue()),
            sx=f(self.size_x.GetValue()),
            sy=f(self.size_y.GetValue()),
            r=r,
            cin=f(self.gap.GetValue()),
            w=f(self.twidth.GetValue()),
            sp=f(self.guard.GetValue()),
            n=int(float(self.turns.GetValue())),
            start=start,
            layer_name=self.layer_choice.GetStringSelection(),
            mirror_x=self.mirror_x_cb.GetValue(),
            mirror_y = self.mirror_y_cb.GetValue(),
            center_nm=self.center_nm,  # remains None → Run() uses entered mm
        )

    def on_corner_type_change(self, event):
        self.update_corner_ui()

    def update_corner_ui(self):
        is_rounded = (self.corner_choice.GetSelection() == 0)

        self.radius_label.Enable(is_rounded)
        self.radius_ctrl.Enable(is_rounded)

        # Optional: force radius to 0 when sharp selected
        if not is_rounded:
            self.radius_ctrl.SetValue("0.0")

        self.Layout()
        self.Fit()

# ---------------------- Geometry routines ----------------------
def create_left_center(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I",
                       w_length: int, w_height: int, r_corner:int, clearance: int,
                       track_width: int, track_spacing: int, n: int, mirror_x = False,
                       mirror_y = False):
    """Draw a rectangle spiral starting from the left-center. All internal geometry is integer nanometers.

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

    #radius = min(r_corner, w_length // 2, w_height // 2)
    trace_width = track_width
    clearance = clearance # spacing between the inner core and inner turn
    trace_spacing = track_spacing  # Spacing between the turns

    turns = n  # number of turns

    center_x, center_y = center.x, center.y  # center point (x,y) of the winding

    trace_offset = clearance + (trace_width  // 2)
    outward_increment = trace_width + trace_spacing
    if turns == 1:
        outward_increment = 0

    half_length = w_length // 2
    half_height = w_height // 2

    # First turn centerline rectangle
    # Edges defining the centerline of the rectangle formed by the first (inner) turn
    left = center_x - half_length - trace_offset
    right = center_x + half_length + trace_offset
    top = center_y - half_height - trace_offset
    bottom = center_y + half_height + trace_offset

    current_length = right -left
    current_height = bottom -top

    radius_now = r_corner + trace_offset
    if (2 * radius_now > current_height or
            2 * radius_now > current_length):
        wx.MessageBox("Corner radius too large. \n"
                      "Reduce radius or trace width.",
                      "Geometry Error",
                      wx.OK | wx.ICON_ERROR)
        return

    now_x = left # Starting point of the trace on the x-axis
    now_y = center_y # Starting point of the trace on the y-axis
    if turns == 1:
        offset = (trace_width + trace_spacing) // 2
        now_y = center_y + offset
        radius_now = min(radius_now, w_height // 2 , w_length // 2)
    #TODO resolve first turn arc clearance issue
    # The arc and the corners of the core touches or lacks correct clearance

    angle = 90

    for turn in range(turns):
        if angle == 90:
            start_position = transform_point(now_x, now_y, center, mirror_x, mirror_y) # Start point for initial straight trace
            end_position = transform_point(now_x, bottom - radius_now, center, mirror_x, mirror_y) # End point for initial straight trace
            # if turns == 1: #TODO maybe also adjust start point
            #     start_position = transform_point(now_x, now_y + 3*trace_width // 4, center, mirror_x, mirror_y) # Adjust start point for single turn
            add_track(board, start_position, end_position, layer, trace_width)
            now_y = bottom - radius_now
            # if windings == 1:
            #     now_y = now_y - (t_width // 2) - (t_spacing // 2)

        # Add arc bottom left
        arc_center = v2(now_x + radius_now, now_y) # center of the first arc
        add_arc_transformed_points(board, arc_center, radius_now, 180, 90,
                                   layer, trace_width, center, mirror_x, mirror_y)
        now_x = now_x + radius_now
        now_y = now_y + radius_now

        # Bottom trace
        # Add straight trace (placed horizontally on the lower side)
        start_position = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_position = transform_point(right - radius_now, now_y, center, mirror_x, mirror_y)
        add_track(board, start_position, end_position, layer, trace_width)

        now_x = right - radius_now

        # Add arc (curved trace) bottom right
        arc_center = v2(now_x, now_y - radius_now)
        add_arc_transformed_points(board, arc_center, radius_now, 90, 0,
                                   layer, trace_width, center, mirror_x, mirror_y)
        now_x = now_x + radius_now
        now_y = now_y - radius_now

        # Right trace
        # Add straight trace (placed vertically on the right side)
        start_position = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_position = transform_point(now_x, top + radius_now, center, mirror_x, mirror_y)
        add_track(board, start_position, end_position, layer, trace_width)
        now_y = top + radius_now

        # Add arc top right
        arc_center = v2(now_x - radius_now, now_y)
        add_arc_transformed_points(board, arc_center, radius_now, 0,
                                   270, layer, trace_width, center, mirror_x, mirror_y)
        now_x = now_x - radius_now
        now_y = now_y - radius_now

        # Top trace
        # Add straight trace (placed horizontally on the upper side)
        next_left = left - outward_increment
        #radius_now = radius_now + outward_increment // 2  # Increment the radius of the arc to space out the next turn

        start_position = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_position = transform_point(next_left + radius_now, now_y, center, mirror_x, mirror_y)
        add_track(board, start_position, end_position, layer, track_width)
        now_x = next_left + radius_now


        #radius_now = radius_now + outward_increment # Increment the radius of the arc to space out the next turn

        # Add arc top left
        arc_center = v2(now_x, now_y + radius_now)
        add_arc_transformed_points(board, arc_center, radius_now, 270,
                                   180, layer, trace_width, center, mirror_x, mirror_y)
        now_x = now_x - radius_now
        now_y = now_y + radius_now
        radius_now += outward_increment // 2
        # Extend the rectangle outward for the next turn
        left -= outward_increment
        right += outward_increment
        top -= outward_increment
        bottom += outward_increment

        if angle == 90:
            start_position = transform_point(now_x, now_y, center, mirror_x, mirror_y)
            end_position = transform_point(now_x, bottom - radius_now, center, mirror_x, mirror_y)
            if turn == turns -1:
                end_position = transform_point(now_x, center_y, center, mirror_x, mirror_y)
            if turns == 1:
                end_position = transform_point(now_x, center_y - offset, center, mirror_x, mirror_y)
            add_track(board, start_position, end_position, layer, track_width)
            now_y = bottom - radius_now

        #radius_now = radius_now + rad_inc2




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
    # if n == 1:
    #     create_left_center(board, layer, center, w_length, w_height, r_corner, clearance, track_width, track_spacing, n)
    #     return

    #radius = min(r_corner, w_length // 2, w_height // 2)
    t_width = track_width
    Clearance = clearance
    track_spacing = track_spacing

    center_x, center_y = center.x, center.y

    rounded = r_corner > 0

    trace_offset = Clearance + (t_width // 2)
    outward_increment = t_width + track_spacing
    if n == 1:
        outward_increment = t_width // 2

    half_length = w_length // 2
    half_height = w_height // 2

    # radius_now = radius + Clearance + (t_width // 2)

    # First turn centerline rectangle
    # Edges defining the centerline of the rectangle formed by the first (inner) turn
    left = center_x - half_length - trace_offset
    right = center_x + half_length + trace_offset
    top = center_y - half_height - trace_offset
    bottom = center_y + half_height + trace_offset

    current_length = right - left
    current_height = bottom - top
    radius_now = 0

    # raise if radius_now is greater than half the length or height
    if rounded:
        radius_now = r_corner + trace_offset
        if (2 * radius_now > current_height or
                2 * radius_now > current_length):
            wx.MessageBox("Corner radius too large. \n"
                          "Reduce radius or trace width.",
                          "Geometry Error",
                          wx.OK | wx.ICON_ERROR)
            return

    # start at left top
    now_x = left + trace_offset
    now_y = bottom

    for turn in range(n):
        # add a slight offset for the first turn to prevent overlap
        first_turn_offset = 0
        if turn == 0:
            first_turn_offset = (t_width // 2)

        # Bottom trace
        # Create trace from left to right on the bottom side
        # add_track(board, v2(now_x + first_turn_offset, now_y), v2(right - radius_now, now_y), layer, t_width)
        start_position = transform_point(now_x + first_turn_offset, now_y, center, mirror_x, mirror_y)
        end_position = transform_point(right - radius_now, now_y, center, mirror_x, mirror_y)
        add_track(board, start_position, end_position, layer, track_width)

        now_x = right - radius_now

        arc_center = v2(now_x, now_y - radius_now)
        add_arc_transformed_points(board, arc_center, radius_now, 90,
                0, layer, t_width, center, mirror_x, mirror_y)
        now_x = now_x + radius_now
        now_y = now_y - radius_now

        # Right trace
        # Create trace from bottom to top on the right side
        #add_track(board, v2(now_x, now_y), v2(now_x, top + radius_now), layer, t_width)
        start_position = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_position = transform_point(now_x, top + radius_now, center, mirror_x, mirror_y)
        add_track(board, start_position, end_position, layer, track_width)
        now_y = top + radius_now

        arc_center = v2(now_x - radius_now, now_y)
        add_arc_transformed_points(board, arc_center, radius_now, 0,
                270, layer, t_width, center, mirror_x, mirror_y)
        now_x = now_x - radius_now
        now_y = now_y - radius_now

        # Top trace
        # Create trace from right to left on the top side
        #add_track(board, v2(now_x, now_y), v2(left + radius_now, now_y), layer, t_width)
        start_position = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_position = transform_point(left + radius_now, now_y, center, mirror_x, mirror_y)
        add_track(board, start_position, end_position, layer, track_width)
        now_x = left + radius_now

        arc_center = v2(now_x, now_y + radius_now)
        add_arc_transformed_points(board, arc_center, radius_now, 270,
                180, layer, t_width, center, mirror_x, mirror_y)
        now_x = now_x - radius_now
        now_y = now_y + radius_now

        # Left trace
        # Create trace at bottom on the left side
        next_bottom = bottom + outward_increment
        #add_track(board, v2(now_x, now_y), v2(now_x, next_bottom - radius_now), layer, t_width)
        start_position = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_position = transform_point(now_x, next_bottom - radius_now, center, mirror_x, mirror_y)
        add_track(board, start_position, end_position, layer, track_width)
        now_y = next_bottom - radius_now

        # exit for single turn
        if n == 1:
            break

        arc_center = v2(now_x + radius_now, now_y)
        add_arc_transformed_points(board, arc_center, radius_now, 180,
                90, layer, t_width, center, mirror_x, mirror_y)
        now_x = now_x + radius_now
        now_y = now_y + radius_now

        # Increment the radius for the next turn
        #radius_now += track_spacing + t_width
        radius_now += outward_increment // 2

        # Extend the rectangle outward for the next turn
        left -= outward_increment
        right += outward_increment
        top -= outward_increment
        bottom += outward_increment

        # # Final extension for Left-Top start
        # if not rounded:
        #     if turn == n - 1:
        #         #add_track(board, v2(now_x, now_y), v2(center_x - half_length, bottom), layer, track_width)
        #         start_position = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        #         end_position = transform_point(center_x - half_length, bottom, center, mirror_x, mirror_y)
        #         add_track(board, start_position, end_position, layer, track_width)



    # for _ in range(n):
    #     # add a slight offset for the first turn to prevent overlap
    #     first_turn_offset = 0
    #     if _ == 0:
    #         first_turn_offset = t_width // 2
    #
    #
    #     add_track(board, v2(now_x + first_turn_offset, now_y), v2(now_x + f_length, now_y), layer, t_width)
    #     now_x = now_x + f_length
    #
    #     add_arc(board, v2(now_x, now_y - radius_now), radius_now, 0, 90, layer, t_width)
    #     now_x = now_x + radius_now
    #     now_y = now_y - radius_now
    #
    #     add_track(board, v2(now_x, now_y), v2(now_x, now_y - f_height), layer, t_width)
    #     now_y = now_y - f_height
    #
    #     add_arc(board, v2(now_x - radius_now, now_y), radius_now, 270, 360, layer, t_width)
    #     now_x = now_x - radius_now
    #     now_y = now_y - radius_now
    #
    #     add_track(board, v2(now_x, now_y), v2(now_x - f_length, now_y), layer, t_width)
    #     now_x = now_x - f_length
    #
    #     add_arc(board, v2(now_x, now_y + radius_now), radius_now, 180, 270, layer, t_width)
    #     now_x = now_x - radius_now
    #     now_y = now_y + radius_now
    #
    #     add_track(board, v2(now_x, now_y), v2(now_x, now_y + f_height + t_width + t_spacing), layer, t_width)
    #     now_y = now_y + f_height + t_width + t_spacing
    #
    #     add_arc(board, v2(now_x + radius_now, now_y), radius_now, 90, 180, layer, t_width)
    #     now_x = now_x + radius_now
    #     now_y = now_y + radius_now
    #
    #     radius_now = radius_now + t_spacing + t_width


def create_left_top(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I",
                    w_length: int, w_height: int, r_corner: int, clearance: int,
                    track_width: int, track_spacing: int, n: int, mirror_x = False,
                    mirror_y = False):
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
    if n == 1:
        create_left_center(board, layer, center, w_length, w_height, r_corner, clearance, track_width, track_spacing, n)
        return

    # radius = min(r_corner, w_length // 2, w_height // 2)
    t_width = track_width
    Clearance = clearance
    track_spacing = track_spacing

    ax, ay = center.x, center.y

    rounded = r_corner > 0

    trace_offset = Clearance + (t_width // 2)
    outward_increment = t_width + track_spacing

    half_length = w_length // 2
    half_height = w_height // 2

    #radius_now = radius + Clearance + (t_width // 2)

    # First turn centerline rectangle
    # Edges defining the centerline of the rectangle formed by the first (inner) turn
    left = ax - half_length - trace_offset
    right = ax + half_length + trace_offset
    top = ay - half_height - trace_offset
    bottom = ay + half_height + trace_offset


    current_length = right - left
    current_height = bottom - top
    radius_now = 0

    # raise if radius_now is greater than half the length or height
    if rounded:
        radius_now = r_corner + trace_offset
        if (2 * radius_now > current_height or
            2 * radius_now > current_length):
            wx.MessageBox("Corner radius too large. \n"
                          "Reduce radius or trace width.",
                          "Geometry Error",
                          wx.OK | wx.ICON_ERROR)
            return

    # start at left top
    now_x = left
    now_y = top + trace_offset

    for turn in range(n):
        # add a slight offset for the first turn to prevent overlap
        first_turn_offset = 0
        if turn == 0:
            first_turn_offset = (t_width // 2)

        # Left trace
        # Create trace from top to bottom on the left side
        start_position = transform_point(now_x, now_y + first_turn_offset, center, mirror_x, mirror_y)
        end_position = transform_point(now_x, bottom - radius_now, center, mirror_x, mirror_y)
        add_track(board, start_position, end_position, layer, track_width)
        now_y = bottom - radius_now

        arc_center = v2(now_x + radius_now, now_y)
        add_arc_transformed_points(board, arc_center, radius_now, 180, 90,
                                   layer, t_width, center, mirror_x, mirror_y)
        now_x = now_x + radius_now
        now_y = now_y + radius_now

        # Bottom trace
        # Create trace from left to right on the bottom side
        start_position = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_position = transform_point(right - radius_now, now_y, center, mirror_x, mirror_y)
        add_track(board, start_position, end_position, layer, track_width)
        now_x = right - radius_now

        arc_center = v2(now_x, now_y - radius_now)
        add_arc_transformed_points(board, arc_center, radius_now, 90,
                                   0, layer, t_width, center, mirror_x, mirror_y)
        now_x = now_x + radius_now
        now_y = now_y - radius_now

        # Right trace
        # Create trace from bottom to top on the right side
        start_position = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_position = transform_point(now_x, top + radius_now, center, mirror_x, mirror_y)
        add_track(board, start_position, end_position, layer, track_width)
        now_y = top + radius_now

        arc_center = v2(now_x - radius_now, now_y)
        add_arc_transformed_points(board, arc_center, radius_now, 0,
                                   270, layer, t_width, center, mirror_x, mirror_y)
        now_x = now_x - radius_now
        now_y = now_y - radius_now

        # Top trace
        # Create trace from right to left on the top side
        next_left = left - outward_increment

        start_position = transform_point(now_x, now_y, center, mirror_x, mirror_y)
        end_position = transform_point(next_left + radius_now, now_y, center, mirror_x, mirror_y)
        add_track(board, start_position, end_position, layer, track_width)
        now_x = next_left + radius_now

        arc_center = v2(now_x, now_y + radius_now)
        add_arc_transformed_points(board, arc_center, radius_now, 270,
                                   180, layer, t_width, center, mirror_x, mirror_y)
        now_x = now_x - radius_now
        now_y = now_y + radius_now

        radius_now += outward_increment // 2  # Increment the radius for the next turn
        # Extend the rectangle outward for the next turn
        left -= outward_increment
        right += outward_increment
        top -= outward_increment
        bottom += outward_increment

        # # Final extension for Left-Top start
        # if not rounded:
        #     if turn == n - 1:
        #         add_track(board, v2(now_x, now_y), v2(now_x, center.y - half_height), layer, track_width)


# ---------------------- Action plugin ----------------------
class PlanarRectSpiralLC(pcbnew.ActionPlugin):
    """Main execution: gather inputs, pick center, convert units, draw."""
    def defaults(self):
        """Initialize plugin metadata and icon for KiCad toolbar"""
        self.name = "Winding Generator"
        self.category = "Add tracks"
        self.description = "Generate planar winding (Left-Top / Left-Center / Left-Bottom)"
        # This is needed to show the button toolbar of the winding generator
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "icon.png")

    def Run(self):
        """Main execution method for the plugin"""
        board = pcbnew.GetBoard()
        if not board:
            return

        # 1) Get parameters
        dlg = ParamsDialog(None)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy(); return
        P = dlg.get(); dlg.Destroy()

        # 2) Center: with mouse capture removed, always use entered mm → nm.
        if P["center_nm"] is not None:
            center = P["center_nm"]
        else:
            center = v2(MM(P["cx_mm"]), MM(P["cy_mm"]))

        # 3) Convert to internal units (nm)
        sx = MM(P["sx"]); sy = MM(P["sy"])
        r  = MM(P["r"]);  cin = MM(P["cin"])
        w  = MM(P["w"]);  sp  = MM(P["sp"])
        n  = max(1, int(P["n"]))
        start = int(P["start"])  # 0=LT, 1=LC, 2=LB
        layer = layer_id(board, P["layer_name"])

        # Optional debug tick at center
        if debug_test:
            add_track(board, v2(center.x - MM(1.0), center.y), v2(center.x + MM(1.0), center.y), layer, w)
        pcbnew.Refresh()

        # 4) Draw spiral
        tx = pcbnew.Transaction(board, "Planar Winding") if hasattr(pcbnew, "Transaction") else None
        try:
            # if start == 2:
            #     create_left_bottom(board, layer, center, sx, sy, r, cin, w, sp, n, mirror_x=P["mirror_x"],
            #     mirror_y=P["mirror_y"])
            if start == 0:
                create_left_top(board, layer, center, sx, sy, r, cin, w, sp, n, mirror_x=P["mirror_x"],
                            mirror_y=P["mirror_y"])
            elif start == 2:
                create_left_bottom(board, layer, center, sx, sy, r, cin, w, sp, n, mirror_x=P["mirror_x"],
                mirror_y=P["mirror_y"])
            else:
                create_left_center(board, layer, center, sx, sy, r, cin, w, sp, n,
                                   mirror_x=P["mirror_x"], mirror_y=P["mirror_y"])
        finally:
            if tx: tx.Commit()
        pcbnew.Refresh()
        # wx.MessageBox("Spiral created.", "Done")


# Register
PlanarRectSpiralLC().register()
