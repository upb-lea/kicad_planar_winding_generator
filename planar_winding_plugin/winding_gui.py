
import wx
import os


# ---------------------- Parameters dialog ----------------------
class ParamsDialog(wx.Dialog):
    """Single dialog. Click 'Use mouse' to capture center; OK to draw."""
    def __init__(self, parent):
        """
        Initialize and lay out the dialog UI for the Winding Generator.

        This method creates the graphical interface that allows the user to:
        - Define the winding center.
        - Set physical parameters (width, height, clearance, spacing).
        - Choose corner types (Rounded vs. Right Angled).
        - Select the copper layer and start position.
        - Enable mirroring options.

        :param parent: The parent window for this dialog (usually None).
        :type parent: wx.Dialog
        """

        # ---------------------------------------------------------
        # 1. Window Initialization
        # ---------------------------------------------------------
        super().__init__(parent, title="Place Planar Transformer Track",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        # Set minimum size to ensure the UI is usable and readable
        self.SetMinSize(wx.Size(600, 720))

        # Root panel/sizer for all controls
        p = wx.Panel(self)
        s = wx.BoxSizer(wx.VERTICAL)

        # ---------------------------------------------------------
        # 2. Helper Function for Input Rows
        # ---------------------------------------------------------
        def row(lbl, default):
            """
            Helper to add a labeled text field aligned in a single row.

            :param lbl: The label text (e.g., "Width (mm):").
            :param default: The default value pre-filled in the text box.
            :return: The TextCtrl widget for later value retrieval.
            """
            hs = wx.BoxSizer(wx.HORIZONTAL)
            hs.Add(wx.StaticText(p, label=lbl), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
            tc = wx.TextCtrl(p, value=default, style=wx.TE_RIGHT)
            hs.Add(tc, 1, wx.EXPAND)
            s.Add(hs, 0, wx.EXPAND | wx.BOTTOM, 6)
            return tc

        # ---------------------------------------------------------
        # 3. Center Coordinates Section
        # ---------------------------------------------------------
        # Uses a 2-column grid to neatly align X and Y inputs
        grid_c = wx.FlexGridSizer(2, 2, 6, 8)
        grid_c.AddGrowableCol(1, 1) # Allow the text columns to expand
        grid_c.Add(wx.StaticText(p, label="Center X:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.cx = wx.TextCtrl(p, value="0.0", style=wx.TE_RIGHT)
        grid_c.Add(self.cx, 1, wx.EXPAND)
        grid_c.Add(wx.StaticText(p, label="Center Y:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.cy = wx.TextCtrl(p, value="0.0", style=wx.TE_RIGHT)
        grid_c.Add(self.cy, 1, wx.EXPAND)
        s.Add(grid_c, 0, wx.EXPAND | wx.BOTTOM, 8)

        # ---------------------------------------------------------
        # 4. Physical Parameters Section
        # ---------------------------------------------------------
        # Using the helper function defined above
        self.gap    = row("Turn-Core (mm):", "0.30")       # inner clearance
        self.twidth = row("Width (mm):", "0.25")     # track width
        self.guard  = row("Turn-Turn (mm):", "0.25")     # track-to-track spacing

        # ---------------------------------------------------------
        # 5. Properties Box (Turns, Core Size, Layer, Corner Type)
        # ---------------------------------------------------------
        props = wx.StaticBoxSizer(wx.VERTICAL, p, "Properties")
        grid  = wx.FlexGridSizer(2, 4, 6, 8)
        grid.AddGrowableCol(1, 1); grid.AddGrowableCol(3, 1)
        # Turn count
        grid.Add(wx.StaticText(p, label="Turns"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.turns  = wx.TextCtrl(p, value="6", style=wx.TE_RIGHT)
        grid.Add(self.turns, 1, wx.EXPAND)
        # Core Width <w>
        grid.Add(wx.StaticText(p, label="Width <w> (mm)"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.size_x = wx.TextCtrl(p, value="20.0", style=wx.TE_RIGHT)
        grid.Add(self.size_x, 1, wx.EXPAND)
        # Core Height <h>
        grid.Add(wx.StaticText(p, label="Height <h> (mm)"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.size_y = wx.TextCtrl(p, value="16.0", style=wx.TE_RIGHT)
        grid.Add(self.size_y, 1, wx.EXPAND)
        props.Add(grid, 0, wx.EXPAND | wx.ALL, 4)

        # -------------------------------------------------
        # Winding corner type selector
        # -------------------------------------------------
        hl_corner = wx.BoxSizer(wx.HORIZONTAL)
        hl_corner.Add(wx.StaticText(p, label="Winding Corner Type"), 0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.corner_choice = wx.Choice(p, choices=["Rounded Corner", "Right Angled"])
        self.corner_choice.SetSelection(0) # Default to Rounded
        self.corner_choice.Bind(wx.EVT_CHOICE, self.on_corner_type_changed)
        wx.CallAfter(self.update_corner_ui) # Ensure correct state on startup
        hl_corner.Add(self.corner_choice, 1, wx.EXPAND | wx.RIGHT, 12)
        props.Add(hl_corner, 0, wx.EXPAND | wx.TOP, 4)

        # -------------------------------------------------
        # Radius input (Dynamically hidden based on selection)
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

        # ---------------------------------------------------------
        # 6. Winding Start Position
        # ---------------------------------------------------------
        # Start position radio buttons (Left Top / Left Center / Left Bottom)
        start_box = wx.StaticBoxSizer(wx.VERTICAL, p, "Winding start position")
        self.rb_top    = wx.RadioButton(p, label="Left Top", style=wx.RB_GROUP)
        self.rb_center = wx.RadioButton(p, label="Left Center")
        self.rb_bottom = wx.RadioButton(p, label="Left Bottom")
        self.rb_center.SetValue(True)
        start_box.Add(self.rb_top)
        start_box.Add(self.rb_center)
        start_box.Add(self.rb_bottom)
        s.Add(start_box, 0, wx.EXPAND | wx.BOTTOM, 6)

        # ---------------------------------------------------------
        # 7. Mirror Options (Checkboxes)
        # ---------------------------------------------------------
        mirror_box = wx.StaticBoxSizer(wx.StaticBox(p, label="Mirror"), wx.HORIZONTAL)
        self.mirror_x_cb = wx.CheckBox(p, label="Mirror X")
        self.mirror_y_cb = wx.CheckBox(p, label="Mirror Y")
        mirror_box.Add(self.mirror_x_cb, 0, wx.RIGHT, 10)
        mirror_box.Add(self.mirror_y_cb, 0)
        s.Add(mirror_box, 0, wx.EXPAND | wx.TOP, 6)

        # ---------------------------------------------------------
        # 8. Parameter Diagram (Image Display)
        # ---------------------------------------------------------
        diag_box = wx.StaticBoxSizer(wx.VERTICAL, p, "Parameter diagram")
        self._diag_bmp = wx.StaticBitmap(p, bitmap=wx.NullBitmap)
        self._diag_bmp.SetMinSize(wx.Size(-1, 100))
        diag_box.Add(self._diag_bmp, 1, wx.EXPAND | wx.ALL, 6)
        #s.Add(diag_box, 1, wx.EXPAND | wx.TOP, 4)

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

        s.Add(diag_box, 1, wx.EXPAND | wx.TOP, 4)

        # ---------------------------------------------------------
        # 9. Final Layout Assembly
        # ---------------------------------------------------------
        p.SetSizer(s)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(p, 1, wx.ALL | wx.EXPAND, 10)

        # Add OK and Cancel buttons
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
        """
        Retrieve and format all user parameters from the dialog controls.

        This method reads the current values from all UI widgets (TextCtrl,
        Choice, RadioButton, CheckBox) and returns them as a structured dictionary.

        Physical dimensions are returned in millimeters (mm) for the action plugin
        to convert into internal units (nm). The start position is encoded as an
        integer, and mirroring options are provided as boolean flags.

        :return: A dictionary containing all plugin parameters.
        :rtype: dict
        """

        # Helper function to safely convert widget string values to floats
        def f(v):
            return float(v)

        # --- Determine Start Position ---
        # Map RadioButton selection to an integer code:
        # 0 = Left Top, 1 = Left Center, 2 = Left Bottom
        start = 1  # Default to Left-Center
        if self.rb_top.GetValue():
            start = 0
        if self.rb_bottom.GetValue():
            start = 2

        # --- Determine Corner Type & Radius ---
        corner_type = self.corner_choice.GetStringSelection()

        if corner_type == "Rounded Corner":
            # If rounded, use the user-entered radius value
            r = float(self.radius_size.GetValue())
        else:
            # If Right Angled, radius is effectively 0
            r = 0.0

        # --- Return Formatted Parameter Dictionary ---
        return dict(
            # Center coordinates (mm)
            cx_mm=f(self.cx.GetValue()),
            cy_mm=f(self.cy.GetValue()),
            # Core dimensions (mm)
            sx=f(self.size_x.GetValue()), # Width <w>
            sy=f(self.size_y.GetValue()), # Height <h>
            # Geometry specifics (mm)
            r=r, # Corner radius
            cin=f(self.gap.GetValue()), # Turn-Core clearance
            w=f(self.twidth.GetValue()), # Track width
            sp=f(self.guard.GetValue()), # Turn-turn spacing
            # Configurations
            n=int(float(self.turns.GetValue())), # Number of turns
            corner_type = corner_type, # "Rounded" or "Sharp"
            start=start, # 0, 1 or 2
            layer_name=self.layer_choice.GetStringSelection(), # e.g "F.Cu"
            # Mirroring flags
            mirror_x=self.mirror_x_cb.GetValue(),
            mirror_y=self.mirror_y_cb.GetValue(),
            # Optional: Mouse-captured center point (nm)
            # Currently unused
            center_nm=self.center_nm,  # remains None → Run() uses entered mm
        )