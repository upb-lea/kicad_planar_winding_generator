# Winding Generator – faithful port of Altium CreateLeftCenter/LeftTop/LeftBottom
# KiCad 7/8/9. Units: dialog in mm; pcbnew uses nanometers (FromMM/ToMM).
"""Generating a code for drawing the windings in Kickad, starting from the left top corner, center, or bottom left."""

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
    :param board: Current board instance.
    :type: pcbnew.BOARD
    :param center: Center point (nm).
    :type: pcbnew.VECTOR2I
    :param radius: Radius of arc (mm).
    :type radius: float
    :param ang_start_deg: Start angle in degrees.
    :type ang_start_deg: float
    :param ang_end_deg: End angle in degrees.
    :type ang_end_deg: float
    :param layer: Target KiCad layer ID (e.g., pcbnew.F_Cu).
    :param width: WArc line width (mm).
    :type width: float
    :type width: float
    :type layer: int
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

    :param board: Current board instance.
    :type board: pcbnew.BOARD
    :param name: Layer name (e.g., "F.Cu", "B.Cu", "In1.Cu").
    :type name: str
    :return: Layer ID if found; otherwise defaults to pcbnew.F_Cu.
    :rtype: int
    """
    lid = board.GetLayerID(name)
    return lid if lid != -1 else pcbnew.F_Cu


# ---------------------- Parameters dialog ----------------------

class ParamsDialog(wx.Dialog):
    """Single dialog. Click 'Use mouse' to capture center; OK to draw."""
    def __init__(self, parent):
        """Initialize and lay out the dialog UI.

        :param parent: Parent window (usually None for a top-level dialog).
        :type parent: wx.Window | None
        """
        super().__init__(parent, title="Place Planar Transformer Track", style=wx.DEFAULT_DIALOG_STYLE)

        # Root panel/sizer for all controls
        p = wx.Panel(self)
        s = wx.BoxSizer(wx.VERTICAL)

        # --- Center row (X/Y) with a capture button ---
        grid_c = wx.FlexGridSizer(2, 3, 6, 8)
        grid_c.AddGrowableCol(1, 1)

        grid_c.Add(wx.StaticText(p, label="Center  X:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.cx = wx.TextCtrl(p, value="0.0", style=wx.TE_RIGHT)
        grid_c.Add(self.cx, 1, wx.EXPAND)
        # capture mouse → center_nm
        self.btn_capture = wx.Button(p, label="Use mouse")
        grid_c.Add(self.btn_capture, 0)

        # spacer in the grid's last cell
        grid_c.Add(wx.StaticText(p, label="Center  Y:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.cy = wx.TextCtrl(p, value="0.0", style=wx.TE_RIGHT)
        grid_c.Add(self.cy, 1, wx.EXPAND)
        grid_c.Add((1,1))

        s.Add(grid_c, 0, wx.EXPAND | wx.BOTTOM, 8)

        def row(lbl, default):
            """Helper to add a labeled text field aligned in a single row.
            :param lbl: Label to add.
            :type lbl: str
            :param default: Default value to add.
            :type default: str
            """
            hs = wx.BoxSizer(wx.HORIZONTAL)
            hs.Add(wx.StaticText(p, label=lbl), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
            tc = wx.TextCtrl(p, value=default, style=wx.TE_RIGHT)
            hs.Add(tc, 1, wx.EXPAND)
            s.Add(hs, 0, wx.EXPAND | wx.BOTTOM, 6)
            return tc

        # Parameter names (all mm)
        self.gap    = row("Gap (mm):",    "0.30")  # inner clearance
        self.radius = row("Radius (mm):", "2.00")  # corner radius
        self.twidth = row("Width (mm):",  "0.25")  # track width
        self.guard  = row("Guard (mm):",  "0.25")  # track-to-track spacing

        props = wx.StaticBoxSizer(wx.VERTICAL, p, "Properties")
        grid = wx.FlexGridSizer(2, 4, 6, 8)
        grid.AddGrowableCol(1, 1); grid.AddGrowableCol(3, 1)

        # --- Properties group: Turns, overall Width/Height, and Layer selection ---
        grid.Add(wx.StaticText(p, label="Turns"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.turns = wx.TextCtrl(p, value="6", style=wx.TE_RIGHT);       grid.Add(self.turns, 1, wx.EXPAND)
        grid.Add(wx.StaticText(p, label="Width (mm)"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.size_x = wx.TextCtrl(p, value="20.0", style=wx.TE_RIGHT);   grid.Add(self.size_x, 1, wx.EXPAND)
        grid.Add(wx.StaticText(p, label="Height (mm)"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.size_y = wx.TextCtrl(p, value="16.0", style=wx.TE_RIGHT);   grid.Add(self.size_y, 1, wx.EXPAND)
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
        # Little tip for the capture workflow
        s.Add(wx.StaticText(p, label="Tip: click 'Use mouse', then hover on canvas and release."), 0, wx.TOP | wx.BOTTOM, 4)
        # OK/Cancel buttons
        btns = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        p.SetSizer(s)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(p, 1, wx.ALL | wx.EXPAND, 10)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(root)
        # Internal state: captured center (pcbnew.VECTOR2I in nm), None until captured.
        self.center_nm = None
        # Wire the capture button
        self.btn_capture.Bind(wx.EVT_BUTTON, self.on_capture_center)

    def on_capture_center(self, _evt):
        """Capture the current pcbnew mouse/crosshair position and reflect it in the dialog.

        :param _evt: Event to handle.
        :type _evt: wx.Event"""
        self.Hide()
        wx.YieldIfNeeded()
        try:
            kfrm = pcbnew.GetPIFrame()
            if kfrm:
                kfrm.Raise(); kfrm.SetFocus()
        except Exception:
            pass
        wx.MilliSleep(500)  # short settle
        pos = pcbnew.GetMousePosition()
        self.center_nm = pos
        # Show coordinates in mm for the user
        self.cx.SetValue(f"{to_mm(pos.x):.3f}")
        self.cy.SetValue(f"{to_mm(pos.y):.3f}")
        self.Show()
        self.Raise()

    def get(self):
        """Return parameters in mm plus the captured center in nm (or None)."""
        def f(v): return float(v)

        start = 1  # default Left-Center
        if self.rb_top.GetValue():    start = 0
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
            center_nm=self.center_nm,
        )


# ---------------------- Geometry routines ----------------------

def create_left_center(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I", w_length: int, w_height: int, r_corner:int, clearance: int,
                       track_width: int, track_spacing: int, n: int):
    """Draw a rectangle spiral starting from the left-center. All internal geometry is integer nanometers.

    :param board: pcbnew.Board
    :type board: pcbnew.Board
    :param layer: layer number
    :type layer: int
    :param center: Spiral centre in board coordinates (nm)
    :type center: int
    :param w_length: Outer rectangle width, it means total width of the rounded-rectangle the winding runs around.
    :type w_length: int
    :param w_height: outer rectangle height. it means total height of the rounded-rectangle.
    :type w_height: int
    :param r_corner:corner radius.
    :type r_corner: int
    :param clearance: Inner clearance / gap from window to first turn (nm).
    :type clearance: int
    :param track_width: Track width.
    :type track_width: int
    :param track_spacing: spacing.
    :type track_spacing: int
    :param n: Number of turns.
    :type n: int
    """
    # WLength, WHeight = w_length, w_height
    radius = min(r_corner, w_length // 2, w_height // 2)

    t_width = track_width
    Clearance = clearance
    # straight span (X) between corner arcs.
    f_length = w_length - 2 * radius
    # straight span (X) between corner arcs.
    f_height = w_height - 2 * radius
    t_spacing = track_spacing
    windings = n
    radius_now = radius + Clearance + (t_width // 2)

    ax, ay = center.x, center.y
    # current pen position while drawing.
    now_x = ax - (w_length // 2) - Clearance - (t_width // 2)
    now_y = ay

    # increments/angle logic from the original VB for the left-center start case.
    angle = 90
    rad_inc1 = t_spacing + t_width
    rad_inc2 = rad_inc1
    limit = (w_height // 2) + Clearance + (t_width // 2)
    if (radius_now + rad_inc1) > limit:
        rad_inc1 = limit - radius_now
    rad_inc2 = rad_inc2 - rad_inc1

    if windings == 1:
        now_y = now_y + (t_width // 2) + (t_spacing // 2)
        rad_inc1 = 0; rad_inc2 = 0
        if radius_now > ((w_height // 2) + Clearance - (t_spacing // 2)):
            ratio = 1.0 - float(((w_height // 2) + Clearance - (t_spacing // 2))) / float(radius_now)
            ratio = max(-1.0, min(1.0, ratio))
            angle = int(round(180.0 * math.acos(ratio) / math.pi))

    for _ in range(windings):
        if angle == 90:
            p1 = v2(now_x, now_y)
            p2 = v2(now_x, now_y + (f_height // 2))
            if windings == 1:
                p2 = v2(p2.x, p2.y - ((t_width // 2) - (t_spacing // 2)))
            add_track(board, p1, p2, layer, t_width)

        now_y = now_y + (f_height // 2)
        if windings == 1:
            now_y = now_y - (t_width // 2) - (t_spacing // 2)

        c1 = v2(now_x + radius_now, now_y)
        add_arc(board, c1, radius_now, 90, 90 + angle, layer, t_width)

        now_x = now_x + radius_now
        now_y = now_y + radius_now

        add_track(board, v2(now_x, now_y), v2(now_x + f_length, now_y), layer, t_width)
        now_x = now_x + f_length

        c2 = v2(now_x, now_y - radius_now)
        add_arc(board, c2, radius_now, 0, 90, layer, t_width)

        now_x = now_x + radius_now
        now_y = now_y - radius_now

        add_track(board, v2(now_x, now_y), v2(now_x, now_y - f_height), layer, t_width)
        now_y = now_y - f_height

        c3 = v2(now_x - radius_now, now_y)
        add_arc(board, c3, radius_now, 270, 360, layer, t_width)

        now_x = now_x - radius_now
        now_y = now_y - radius_now

        add_track(board, v2(now_x, now_y), v2(now_x - f_length - rad_inc2, now_y), layer, t_width)
        now_x = now_x - f_length - rad_inc2

        radius_now = radius_now + rad_inc1

        c4 = v2(now_x, now_y + radius_now)
        add_arc(board, c4, radius_now, 270 - angle, 270, layer, t_width)

        now_x = now_x - radius_now
        now_y = now_y + radius_now

        if angle == 90:
            p3 = v2(now_x, now_y)
            p4 = v2(now_x, ay)
            if windings == 1:
                p4 = v2(p4.x, p4.y - ((t_width // 2) + (t_spacing // 2)))
            add_track(board, p3, p4, layer, t_width)

        now_y = ay
        radius_now = radius_now + rad_inc2


def create_left_bottom(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I", w_length: int, w_height: int, r_corner: int, clearance: int,
                       track_width: int, track_spacing: int, n: int):
    """Draw a rectangle spiral starting from the left-top. All internal geometry is integer nanometers.

    :param board: pcbnew.Board
    :type board: pcbnew.Board
    :param layer: layer number
    :param center: int
    :param center: center point of the rectangle.
    :type center: int
    :param w_length: Outer rectangle width, it means total width of the rounded-rectangle the winding runs around.
    :type w_length: int
    :param w_height: outer rectangle height. it means total height of the rounded-rectangle.
    :type w_height: int
    :param r_corner: outer rectangle corner.
    :type r_corner: int
    :param clearance: Inner clearance / gap from window to first turn (nm).
    :type clearance: int
    :param track_width: Track width of the rounded-rectangle.
    :type track_width: int
    :param track_spacing: Track spacing of the rounded-rectangle.
    :type track_spacing: int
    :param n: number of windings.
    :type n: int
    """
    if n == 1:
        create_left_center(board, layer, center, w_length, w_height, r_corner, clearance, track_width, track_spacing, n)
        return

    # WLength, WHeight = w_length, w_height
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
        # top horizontal
        add_track(board, v2(now_x, now_y), v2(now_x + f_length, now_y), layer, t_width)
        now_x = now_x + f_length

        # top-right corner 0->90
        add_arc(board, v2(now_x, now_y - radius_now), radius_now, 0, 90, layer, t_width)
        now_x = now_x + radius_now
        now_y = now_y - radius_now

        # right vertical down
        add_track(board, v2(now_x, now_y), v2(now_x, now_y - f_height), layer, t_width)
        now_y = now_y - f_height

        # bottom-right 270->360
        add_arc(board, v2(now_x - radius_now, now_y), radius_now, 270, 360, layer, t_width)
        now_x = now_x - radius_now
        now_y = now_y - radius_now

        # bottom horizontal to left  << fixed: include y
        add_track(board, v2(now_x, now_y), v2(now_x - f_length, now_y), layer, t_width)
        now_x = now_x - f_length

        # bottom-left 180->270
        add_arc(board, v2(now_x, now_y + radius_now), radius_now, 180, 270, layer, t_width)
        now_x = now_x - radius_now
        now_y = now_y + radius_now

        # left vertical up with step (f_height + width + spacing)
        add_track(board, v2(now_x, now_y),
                  v2(now_x, now_y + f_height + t_width + t_spacing), layer, t_width)
        now_y = now_y + f_height + t_width + t_spacing

        # top-left 90->180
        add_arc(board, v2(now_x + radius_now, now_y), radius_now, 90, 180, layer, t_width)
        now_x = now_x + radius_now
        now_y = now_y + radius_now

        radius_now = radius_now + t_spacing + t_width



def create_left_top(board: "pcbnew.BOARD", layer: int, center: "pcbnew.VECTOR2I", w_length: int, w_height: int, r_corner: int, clearance: int,
                    track_width: int, track_spacing: int, n: int):
    """Draw a rectangle spiral starting from the left-bottom. All internal geometry is integer nanometers.

    :param board: pcbnew.BOARD
    :type board: pcbnew.BOARD
    :param layer: layer number
    :type layer: int
    :param center: center point of the rectangle.
    :type center: int
    :param w_length: outer rectangle width.
    :type w_length: int
    :param w_height: outer rectangle height.
    :type w_height: int
    :param r_corner: outer rectangle corner.
    :type r_corner: int
    :param clearance: Inner clearance / gap from window to first turn (nm).
    :type clearance: int
    :param track_width: Track width of the rounded-rectangle.
    :type track_width: int
    :param track_spacing: Track spacing of the rounded-rectangle.
    :type track_spacing: int
    :param n: number of turns.
    :type n: int
    """
    if n == 1:
        create_left_center(board, layer, center, w_length, w_height, r_corner, clearance, track_width, track_spacing, n)
        return

    # WLength, WHeight = w_length, w_height
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
        # left vertical up
        add_track(board, v2(now_x, now_y), v2(now_x, now_y + f_height), layer, t_width)
        now_y = now_y + f_height

        # top-left 90->180
        add_arc(board, v2(now_x + radius_now, now_y), radius_now, 90, 180, layer, t_width)
        now_x = now_x + radius_now
        now_y = now_y + radius_now

        # top horizontal right  << fixed: include y
        add_track(board, v2(now_x, now_y), v2(now_x + f_length, now_y), layer, t_width)
        now_x = now_x + f_length

        # top-right 0->90
        add_arc(board, v2(now_x, now_y - radius_now), radius_now, 0, 90, layer, t_width)
        now_x = now_x + radius_now
        now_y = now_y - radius_now

        # right vertical down
        add_track(board, v2(now_x, now_y), v2(now_x, now_y - f_height), layer, t_width)
        now_y = now_y - f_height

        # bottom-right 270->360
        add_arc(board, v2(now_x - radius_now, now_y), radius_now, 270, 360, layer, t_width)
        now_x = now_x - radius_now
        now_y = now_y - radius_now

        # bottom horizontal left with step  << fixed: include y
        add_track(board, v2(now_x, now_y),
                  v2(now_x - f_length - t_width - track_spacing, now_y), layer, t_width)
        now_x = now_x - f_length - t_width - track_spacing

        # bottom-left 180->270
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

        # 2) Center: prefer captured mouse (nm). If None, use entered mm → nm.
        if P["center_nm"] is not None:
            center = P["center_nm"]
        else:
            center = v2(MM(P["cx_mm"]), MM(P["cy_mm"]))

        # 3) Convert to internal units (nm)
        sx  = MM(P["sx"]); sy  = MM(P["sy"])
        r   = MM(P["r"]);  cin = MM(P["cin"])
        w   = MM(P["w"]);  sp  = MM(P["sp"])
        n   = max(1, int(P["n"]))
        start = int(P["start"])  # 0=LT, 1=LC, 2=LB
        layer = layer_id(board, P["layer_name"])

        # Optional debug tick at center
        if debug_test:
            add_track(board, v2(center.x - MM(1.0), center.y),
                             v2(center.x + MM(1.0), center.y), layer, w)
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

        wx.MessageBox("Spiral created.", "Done")


# Register
PlanarRectSpiralLC().register()
