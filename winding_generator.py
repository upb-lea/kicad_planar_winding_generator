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
        self.radius = row("Radius (mm):", "2.00")    # corner radius
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
        return dict(
            cx_mm=f(self.cx.GetValue()),
            cy_mm=f(self.cy.GetValue()),
            sx=f(self.size_x.GetValue()),
            sy=f(self.size_y.GetValue()),
            r=f(self.radius.GetValue()),
            cin=f(self.gap.GetValue()),
            w=f(self.twidth.GetValue()),
            sp=f(self.guard.GetValue()),
            n=int(float(self.turns.GetValue())),
            start=start,
            layer_name=self.layer_choice.GetStringSelection(),
            center_nm=self.center_nm,  # remains None → Run() uses entered mm
        )


# ---------------------- Geometry routines ----------------------
def create_left_center_single(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I",
                               w_length: int, w_height: int, r_corner: int, clearance: int,
                               track_width: int, track_spacing: int):
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
        p1 = v2(now_x, now_y)
        p2 = v2(now_x, now_y + (f_height // 2) - half_sep)  # reach arc tangent
        add_track(board, p1, p2, layer, t_width)
        now_y = p2.y

    #  Arc bottom-left
    c1 = v2(now_x + radius_now, now_y)
    add_arc(board, c1, radius_now, 90, 90 + angle, layer, t_width)
    now_x = now_x + radius_now
    now_y = now_y + radius_now

    #  Bottom straight
    add_track(board, v2(now_x, now_y), v2(now_x + f_length, now_y), layer, t_width)
    now_x = now_x + f_length

    #  Arc bottom-right
    c2 = v2(now_x, now_y - radius_now)
    add_arc(board, c2, radius_now, 0, 90, layer, t_width)
    now_x = now_x + radius_now
    now_y = now_y - radius_now

    #  Right vertical straight
    add_track(board, v2(now_x, now_y), v2(now_x, now_y - f_height), layer, t_width)
    now_y = now_y - f_height

    #  Arc top-right
    c3 = v2(now_x - radius_now, now_y)
    add_arc(board, c3, radius_now, 270, 360, layer, t_width)
    now_x = now_x - radius_now
    now_y = now_y - radius_now

    #  Top straight (rad_inc = 0 for single turn, no length extension)
    add_track(board, v2(now_x, now_y), v2(now_x - f_length, now_y), layer, t_width)
    now_x = now_x - f_length

    #  Arc top-left (radius unchanged — single turn, no increment)
    c4 = v2(now_x, now_y + radius_now)
    add_arc(board, c4, radius_now, 270 - angle, 270, layer, t_width)
    now_x = now_x - radius_now
    now_y = now_y + radius_now

    #  Return stub: upward segment ending at ay - half_sep
    # Centre-to-centre distance between stubs = 2 * half_sep = t_width + t_spacing
    # Cap edges are therefore exactly track_spacing apart.
    if angle == 90:
        p3 = v2(now_x, now_y)
        p4 = v2(now_x, ay - half_sep)  # return stub centre-y
        add_track(board, p3, p4, layer, t_width)


def create_left_center(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I",
                       w_length: int, w_height: int, r_corner: int, clearance: int,
                       track_width: int, track_spacing: int, n: int):
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

    if n == 1:
        create_left_center_single(board, layer, center, w_length, w_height,
                                  r_corner, clearance, track_width, track_spacing)
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

    if radius_now > ((w_height // 2) + Clearance + (t_width // 2)):
        ratio = 1.0 - float(((w_height // 2) + Clearance - (t_spacing // 2))) / float(radius_now)
        ratio = max(-1.0, min(1.0, ratio))
        angle = int(round(180.0 * math.acos(ratio) / math.pi))

    for _ in range(windings):
        if angle == 90:
            p1 = v2(now_x, now_y)
            p2 = v2(now_x, now_y + (f_height // 2))
            add_track(board, p1, p2, layer, t_width)
            now_y = now_y + (f_height // 2)

        # Arc bottom-left
        c1 = v2(now_x + radius_now, now_y)
        add_arc(board, c1, radius_now, 90, 90 + angle, layer, t_width)
        now_x = now_x + radius_now
        now_y = now_y + radius_now

        # Bottom straight
        add_track(board, v2(now_x, now_y), v2(now_x + f_length, now_y), layer, t_width)
        now_x = now_x + f_length

        # Arc bottom-right
        c2 = v2(now_x, now_y - radius_now)
        add_arc(board, c2, radius_now, 0, 90, layer, t_width)
        now_x = now_x + radius_now
        now_y = now_y - radius_now

        # Right vertical straight
        add_track(board, v2(now_x, now_y), v2(now_x, now_y - f_height), layer, t_width)
        now_y = now_y - f_height

        # Arc top-right
        c3 = v2(now_x - radius_now, now_y)
        add_arc(board, c3, radius_now, 270, 360, layer, t_width)
        now_x = now_x - radius_now
        now_y = now_y - radius_now

        # Top straight
        add_track(board, v2(now_x, now_y), v2(now_x - f_length - rad_inc2, now_y), layer, t_width)
        now_x = now_x - f_length - rad_inc2

        radius_now = radius_now + rad_inc1

        # Arc top-left
        c4 = v2(now_x, now_y + radius_now)
        add_arc(board, c4, radius_now, 270 - angle, 270, layer, t_width)
        now_x = now_x - radius_now
        now_y = now_y + radius_now

        if angle == 90:
            p3 = v2(now_x, now_y)
            p4 = v2(now_x, ay)
            add_track(board, p3, p4, layer, t_width)
            now_y = ay

        radius_now = radius_now + rad_inc2


def create_left_bottom(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I",
                       w_length: int, w_height: int, r_corner: int, clearance: int,
                       track_width: int, track_spacing: int, n: int):
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
    if n == 1:
        create_left_center(board, layer, center, w_length, w_height, r_corner, clearance, track_width, track_spacing, n)
        return

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


        add_track(board, v2(now_x + first_turn_offset, now_y), v2(now_x + f_length, now_y), layer, t_width)
        now_x = now_x + f_length

        add_arc(board, v2(now_x, now_y - radius_now), radius_now, 0, 90, layer, t_width)
        now_x = now_x + radius_now
        now_y = now_y - radius_now

        add_track(board, v2(now_x, now_y), v2(now_x, now_y - f_height), layer, t_width)
        now_y = now_y - f_height

        add_arc(board, v2(now_x - radius_now, now_y), radius_now, 270, 360, layer, t_width)
        now_x = now_x - radius_now
        now_y = now_y - radius_now

        add_track(board, v2(now_x, now_y), v2(now_x - f_length, now_y), layer, t_width)
        now_x = now_x - f_length

        add_arc(board, v2(now_x, now_y + radius_now), radius_now, 180, 270, layer, t_width)
        now_x = now_x - radius_now
        now_y = now_y + radius_now

        add_track(board, v2(now_x, now_y), v2(now_x, now_y + f_height + t_width + t_spacing), layer, t_width)
        now_y = now_y + f_height + t_width + t_spacing

        add_arc(board, v2(now_x + radius_now, now_y), radius_now, 90, 180, layer, t_width)
        now_x = now_x + radius_now
        now_y = now_y + radius_now

        radius_now = radius_now + t_spacing + t_width


def create_left_top(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I",
                    w_length: int, w_height: int, r_corner: int, clearance: int,
                    track_width: int, track_spacing: int, n: int):
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


        add_track(board, v2(now_x, now_y + first_turn_offset), v2(now_x, now_y + f_height), layer, t_width)
        now_y = now_y + f_height

        add_arc(board, v2(now_x + radius_now, now_y), radius_now, 90, 180, layer, t_width)
        now_x = now_x + radius_now
        now_y = now_y + radius_now

        add_track(board, v2(now_x, now_y), v2(now_x + f_length, now_y), layer, t_width)
        now_x = now_x + f_length

        add_arc(board, v2(now_x, now_y - radius_now), radius_now, 0, 90, layer, t_width)
        now_x = now_x + radius_now
        now_y = now_y - radius_now

        add_track(board, v2(now_x, now_y), v2(now_x, now_y - f_height), layer, t_width)
        now_y = now_y - f_height

        add_arc(board, v2(now_x - radius_now, now_y), radius_now, 270, 360, layer, t_width)
        now_x = now_x - radius_now
        now_y = now_y - radius_now

        add_track(board, v2(now_x, now_y), v2(now_x - f_length - t_width - track_spacing, now_y), layer, t_width)
        now_x = now_x - f_length - t_width - track_spacing

        add_arc(board, v2(now_x, now_y + radius_now), radius_now, 180, 270, layer, t_width)
        now_x = now_x - radius_now
        now_y = now_y + radius_now

        radius_now = radius_now + track_spacing + t_width


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
            if start == 0:
                create_left_top(board, layer, center, sx, sy, r, cin, w, sp, n)
            elif start == 2:
                create_left_bottom(board, layer, center, sx, sy, r, cin, w, sp, n)
            else:
                create_left_center(board, layer, center, sx, sy, r, cin, w, sp, n)
        finally:
            if tx: tx.Commit()
        pcbnew.Refresh()
        # wx.MessageBox("Spiral created.", "Done")


# Register
PlanarRectSpiralLC().register()
