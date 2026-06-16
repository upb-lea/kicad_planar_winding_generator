
import wx
import os


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
        #self.radius = row("Radius (mm):", "0.50")    # corner radius
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

        # -------------------------------------------------
        # Winding corner type selector
        # -------------------------------------------------
        hl_corner = wx.BoxSizer(wx.HORIZONTAL)

        hl_corner.Add(wx.StaticText(p, label="Winding Corner Type"), 0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self.corner_choice = wx.Choice(p, choices=["Rounded Corner", "Right Angled"])
        self.corner_choice.SetSelection(0)
        self.corner_choice.Bind(wx.EVT_CHOICE, self.on_corner_type_changed)
        wx.CallAfter(self.update_corner_ui)

        hl_corner.Add(self.corner_choice, 1, wx.EXPAND | wx.RIGHT, 12)
        props.Add(hl_corner, 0, wx.EXPAND | wx.TOP, 4)

        # -------------------------------------------------
        # Radius input
        # -------------------------------------------------
        self.radius_row = wx.BoxSizer(wx.HORIZONTAL)

        self.radius_label = wx.StaticText(p, label="Radius (mm):")
        self.radius_row.Add(self.radius_label, 0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self.radius_size = wx.TextCtrl(p, value="0.5")
        self.radius_row.Add(self.radius_size, 1, wx.EXPAND | wx.RIGHT, 12)

        props.Add(self.radius_row, 0, wx.EXPAND | wx.TOP, 4)

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

    def on_corner_type_changed(self, event):
        self.update_corner_ui()

    def update_corner_ui(self):
        is_rounded = self.corner_choice.GetSelection() == 0

        self.radius_label.Enable(is_rounded)
        self.radius_size.Enable(is_rounded)

        if not is_rounded:
            self.radius_size.SetValue("0.0")

        self.Layout()

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

        corner_type = self.corner_choice.GetStringSelection()

        if corner_type == "Rounded Corner":
            r = float(self.radius_size.GetValue())
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
            corner_type = corner_type,
            start=start,
            layer_name=self.layer_choice.GetStringSelection(),
            center_nm=self.center_nm,  # remains None → Run() uses entered mm
        )