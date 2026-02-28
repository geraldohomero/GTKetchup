import math
import gi
import subprocess

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo
import cairo

class PomodoroTimer(Gtk.DrawingArea):
    def __init__(self, config):
        super().__init__()
        self.set_size_request(400, 400)
        self.set_hexpand(True)
        self.set_vexpand(True)
        
        self.config = config
        self.apply_config(self.config)
        self.initial_time_seconds = self.time_seconds
        
        self.is_running = False
        self.timer_source = None
        
        self.scroll_accumulator = 0.0

        self.set_draw_func(self.on_draw)

        # Scroll event
        scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES | Gtk.EventControllerScrollFlags.KINETIC)
        scroll.connect('scroll', self.on_scroll)
        self.add_controller(scroll)

        # Click event
        click = Gtk.GestureClick.new()
        click.connect('pressed', self.on_click)
        self.add_controller(click)
        
        # Popover for manual adjustment
        self.popover = Gtk.Popover()
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)

        self.min_spin = Gtk.SpinButton.new_with_range(0, 999, 1)
        self.min_spin.set_value(self.time_seconds // 60)
        self.min_spin.connect("value-changed", self.on_spin_changed)
        box.append(Gtk.Label(label="Min:"))
        box.append(self.min_spin)

        self.sec_spin = Gtk.SpinButton.new_with_range(0, 59, 1)
        self.sec_spin.set_value(self.time_seconds % 60)
        self.sec_spin.connect("value-changed", self.on_spin_changed)
        box.append(Gtk.Label(label="Sec:"))
        box.append(self.sec_spin)
        
        self.popover.set_child(box)
        self.popover.set_parent(self)
        
    def apply_config(self, config):
        self.config = config
        self.time_seconds = self.config["default_time"] * 60
        self.initial_time_seconds = self.time_seconds
        self.scroll_min_step = self.config["scroll_min_step"]
        self.scroll_sec_step = self.config["scroll_sec_step"]
        if hasattr(self, 'queue_draw'):
            self.queue_draw()

    def on_spin_changed(self, spin):
        minutes = self.min_spin.get_value_as_int()
        seconds = self.sec_spin.get_value_as_int()
        self.time_seconds = minutes * 60 + seconds
        self.initial_time_seconds = self.time_seconds
        self.queue_draw()

    def on_scroll(self, controller, dx, dy):
        if not self.is_running:
            state = controller.get_current_event_state()
            is_shift = state & Gdk.ModifierType.SHIFT_MASK if state else False

            # Touchpads send small fractional values for dy, mice send 1.0 or -1.0
            self.scroll_accumulator += dy
            
            # Threshold to trigger a step. 1.0 is a standard mouse wheel click.
            if abs(self.scroll_accumulator) >= 1.0:
                # Determine how many "steps" we crossed
                steps = int(self.scroll_accumulator)
                self.scroll_accumulator -= steps
                
                delta = -steps # Negative because scrolling down (positive dy) should usually decrease time
                
                if is_shift:
                    self.time_seconds += delta * self.scroll_sec_step
                else:
                    self.time_seconds += delta * self.scroll_min_step * 60
                    
                self.time_seconds = max(0, min(self.time_seconds, 999 * 60))
                self.initial_time_seconds = self.time_seconds
                
                # Disconnect the signal temporarily so we don't trigger on_spin_changed
                self.min_spin.handler_block_by_func(self.on_spin_changed)
                self.sec_spin.handler_block_by_func(self.on_spin_changed)
                
                self.min_spin.set_value(self.time_seconds // 60)
                self.sec_spin.set_value(self.time_seconds % 60)
                
                self.min_spin.handler_unblock_by_func(self.on_spin_changed)
                self.sec_spin.handler_unblock_by_func(self.on_spin_changed)
                
                self.queue_draw()
        return True

    def on_click(self, gesture, n_press, x, y):
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2 - 20

        # Define click areas
        play_y = cy + radius * 0.65
        play_x = cx
        
        reset_x = cx - radius * 0.4
        reset_y = play_y
        
        zero_x = cx + radius * 0.4
        zero_y = play_y

        dist_to_play = math.hypot(x - play_x, y - play_y)
        dist_to_reset = math.hypot(x - reset_x, y - reset_y)
        dist_to_zero = math.hypot(x - zero_x, y - zero_y)
        dist_to_center = math.hypot(x - cx, y - cy)

        if dist_to_center < radius * 0.4:
            # Clicked central text area
            if not self.is_running:
                self.min_spin.set_value(self.time_seconds // 60)
                self.sec_spin.set_value(self.time_seconds % 60)
                rect = Gdk.Rectangle()
                rect.x = int(cx)
                rect.y = int(cy)
                rect.width = 1
                rect.height = 1
                self.popover.set_pointing_to(rect)
                self.popover.popup()
        elif dist_to_play < 40:
            self.toggle_timer()
        elif dist_to_reset < 30:
            if not self.is_running:
                self.time_seconds = self.config["default_time"] * 60
                self.initial_time_seconds = self.time_seconds
                self.queue_draw()
        elif dist_to_zero < 30:
            if not self.is_running:
                self.time_seconds = 0
                self.initial_time_seconds = 0
                self.queue_draw()
        else:
            if x < cx - radius * 0.5 and y < cy + radius * 0.4:
                if not self.is_running:
                    self.time_seconds = max(0, self.time_seconds - 5 * 60)
                    self.initial_time_seconds = self.time_seconds
            elif x > cx + radius * 0.5 and y < cy + radius * 0.4:
                if not self.is_running:
                    self.time_seconds = min(999 * 60, self.time_seconds + 5 * 60)
                    self.initial_time_seconds = self.time_seconds
            else:
                self.popover.popdown()
                
        self.queue_draw()

    def toggle_timer(self):
        self.popover.popdown()
        if self.is_running:
            self.is_running = False
            if self.timer_source:
                GLib.source_remove(self.timer_source)
                self.timer_source = None
        else:
            if self.time_seconds > 0:
                self.initial_time_seconds = self.time_seconds
                self.is_running = True
                self.timer_source = GLib.timeout_add(1000, self.tick)

    def notify_finish(self):
        try:
            # Desktop notification
            subprocess.Popen(['notify-send', '-i', 'appointment-soon', 'GTKetchup', 'Time is up!'])
            # Sound notification (Ubuntu/GNOME system sound)
            subprocess.Popen(['paplay', '/usr/share/sounds/freedesktop/stereo/complete.oga'])
        except Exception as e:
            print("Failed to dispatch notification/sound:", e)

    def tick(self):
        if self.time_seconds > 0:
            self.time_seconds -= 1
            self.queue_draw()
            return True
        else:
            self.is_running = False
            self.timer_source = None
            self.notify_finish()
            self.queue_draw()
            return False
            
    def _get_color_for_hours(self, hours):
        # White -> Yellow -> Orange -> Red
        if hours == 0:
            return (1.0, 1.0, 1.0) # White
        elif hours == 1:
            return (1.0, 0.9, 0.2) # Yellow
        elif hours == 2:
            return (1.0, 0.6, 0.1) # Orange
        else:
            return (1.0, 0.2, 0.2) # Red

    def on_draw(self, area, cr, width, height, data=None):
        cx = width / 2
        cy = height / 2
        radius = min(width, height) / 2 - 20

        # Background circular dial
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        pat = cairo.LinearGradient(cx - radius, cy - radius, cx + radius, cy + radius)
        pat.add_color_stop_rgb(0, 0.2, 0.2, 0.2)
        pat.add_color_stop_rgb(1, 0.05, 0.05, 0.05)
        cr.set_source(pat)
        cr.fill_preserve()
        
        # Dial border
        cr.set_source_rgb(0.6, 0.6, 0.6)
        cr.set_line_width(8)
        cr.stroke_preserve()
        
        # Inner dark face
        cr.arc(cx, cy, radius - 8, 0, 2 * math.pi)
        cr.set_source_rgb(0.05, 0.05, 0.05)
        cr.fill()

        num_dots = 60
        dot_radius = radius - 30
        
        minutes = self.time_seconds // 60
        seconds = self.time_seconds % 60
        hours = self.time_seconds // 3600
        
        active_dots = math.ceil((self.time_seconds % 3600) / 60)
        if self.time_seconds > 0 and self.time_seconds % 3600 == 0:
            active_dots = 60
        
        if self.is_running and seconds > 0:
             active_dots = (minutes % 60) + 1

        active_color = self._get_color_for_hours(hours)
        inactive_color = (0.2, 0.2, 0.2)
        
        # luminous dots
        for i in range(num_dots):
            angle = -math.pi / 2 + (i * 2 * math.pi / num_dots)
            dot_x = cx + math.cos(angle) * dot_radius
            dot_y = cy + math.sin(angle) * dot_radius
            
            if i < active_dots or (hours > 0 and self.time_seconds % 3600 == 0):
                 cr.set_source_rgb(*active_color)
            else:
                 cr.set_source_rgb(*inactive_color)
                
            cr.arc(dot_x, dot_y, 4, 0, 2 * math.pi)
            cr.fill()

        hours_view = False
        if self.time_seconds >= 3600:
            hours_view = True
            
        # Draw Time Text
        if hours_view:
            val1 = hours
            val2 = minutes % 60
            small_val = seconds
            
            # Draw HH:MM large
            time_str = f"{int(val1):02d}:{int(val2):02d}"
            layout = self.create_pango_layout(time_str)
            desc = Pango.FontDescription("Sans Bold 70")
            layout.set_font_description(desc)
            
            PangoCairo.update_layout(cr, layout)
            text_width, text_height = layout.get_pixel_size()
            
            # Draw :SS small
            sec_str = f":{int(small_val):02d}"
            sec_layout = self.create_pango_layout(sec_str)
            sec_desc = Pango.FontDescription("Sans Bold 15")
            sec_layout.set_font_description(sec_desc)
            
            PangoCairo.update_layout(cr, sec_layout)
            sec_width, sec_height = sec_layout.get_pixel_size()
            
            total_width = text_width + sec_width
            start_x = cx - total_width / 2
            
            cr.set_source_rgb(1, 1, 1)
            cr.move_to(start_x, cy - text_height / 2 + 10)
            PangoCairo.show_layout(cr, layout)
            
            # The smaller seconds are vertically aligned near the baseline of the larger text
            cr.move_to(start_x + text_width, cy - sec_height / 2 + 10 + (text_height / 2 - sec_height / 2))
            PangoCairo.show_layout(cr, sec_layout)
            
            # Optional small 'H', 'M', 'S' labels below
            h_layout = self.create_pango_layout("H")
            m_layout = self.create_pango_layout("M")
            s_layout = self.create_pango_layout("S")
            small_desc = Pango.FontDescription("Sans Bold 14")
            h_layout.set_font_description(small_desc)
            m_layout.set_font_description(small_desc)
            s_layout.set_font_description(small_desc)
            
            PangoCairo.update_layout(cr, h_layout)
            PangoCairo.update_layout(cr, m_layout)
            PangoCairo.update_layout(cr, s_layout)
            
            col_width = text_width / 2
            cr.set_source_rgb(0.7, 0.7, 0.7)
            
            hw, _ = h_layout.get_pixel_size()
            cr.move_to(start_x + col_width / 2 - hw / 2, cy - text_height / 2 - 25)
            PangoCairo.show_layout(cr, h_layout)
            
            mw, _ = m_layout.get_pixel_size()
            cr.move_to(start_x + col_width + col_width / 2 - mw / 2, cy - text_height / 2 - 25)
            PangoCairo.show_layout(cr, m_layout)

        else:
            val1 = minutes
            val2 = seconds
            
            # Center Time Text MM SS
            time_str = f"{int(val1):02d} {int(val2):02d}"
            if val1 > 99:
                time_str = f"{int(val1):03d} {int(val2):02d}"
                
            layout = self.create_pango_layout(time_str)
            desc = Pango.FontDescription("Sans Bold 80")
            if val1 > 99:
                desc = Pango.FontDescription("Sans Bold 60")
                
            layout.set_font_description(desc)
            
            PangoCairo.update_layout(cr, layout)
            text_width, text_height = layout.get_pixel_size()
            cr.set_source_rgb(1, 1, 1)
            cr.move_to(cx - text_width / 2, cy - text_height / 2 + 10)
            PangoCairo.show_layout(cr, layout)

            # Labels
            m_layout = self.create_pango_layout("M")
            s_layout = self.create_pango_layout("S")
            small_desc = Pango.FontDescription("Sans Bold 16")
            m_layout.set_font_description(small_desc)
            s_layout.set_font_description(small_desc)
            
            PangoCairo.update_layout(cr, m_layout)
            PangoCairo.update_layout(cr, s_layout)
            m_w, m_h = m_layout.get_pixel_size()
            s_w, s_h = s_layout.get_pixel_size()
            
            col_width = text_width / 2
            cr.set_source_rgb(0.7, 0.7, 0.7)
            cr.move_to(cx - col_width / 2 - m_w / 2, cy - text_height / 2 - 30)
            PangoCairo.show_layout(cr, m_layout)
            
            cr.move_to(cx + col_width / 2 - s_w / 2, cy - text_height / 2 - 30)
            PangoCairo.show_layout(cr, s_layout)

        # Play / Pause icon
        play_y = cy + radius * 0.65
        cr.arc(cx, play_y, 18, 0, 2 * math.pi)
        cr.set_source_rgb(0.15, 0.15, 0.15)
        cr.fill()
        
        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(2)
        if self.is_running:
            cr.rectangle(cx - 5, play_y - 6, 3, 12)
            cr.rectangle(cx + 2, play_y - 6, 3, 12)
            cr.fill()
        else:
            cr.move_to(cx - 4, play_y - 6)
            cr.line_to(cx + 6, play_y)
            cr.line_to(cx - 4, play_y + 6)
            cr.close_path()
            cr.fill()
            
        cr.arc(cx, play_y, 12, 0, 2 * math.pi)
        cr.set_source_rgb(0.3, 0.3, 0.3)
        cr.stroke()

        # Reset icon (bottom left)
        if not self.is_running:
             reset_x = cx - radius * 0.4
             reset_y = play_y
             
             cr.arc(reset_x, reset_y, 14, 0, 2 * math.pi)
             cr.set_source_rgb(0.15, 0.15, 0.15)
             cr.fill()
             
             cr.set_source_rgb(0.9, 0.9, 0.9)
             cr.set_line_width(2)
             cr.arc(reset_x, reset_y, 6, -math.pi, math.pi / 2)
             cr.stroke()
             
             cr.move_to(reset_x - 6, reset_y)
             cr.line_to(reset_x - 2, reset_y - 4)
             cr.line_to(reset_x - 10, reset_y - 4)
             cr.fill()

        # Zero icon (bottom right)
        if not self.is_running:
             zero_x = cx + radius * 0.4
             zero_y = play_y
             
             cr.arc(zero_x, zero_y, 14, 0, 2 * math.pi)
             cr.set_source_rgb(0.15, 0.15, 0.15)
             cr.fill()
             
             z_layout = self.create_pango_layout("0")
             z_desc = Pango.FontDescription("Sans Bold 12")
             z_layout.set_font_description(z_desc)
             PangoCairo.update_layout(cr, z_layout)
             z_w, z_h = z_layout.get_pixel_size()
             
             cr.set_source_rgb(0.9, 0.9, 0.9)
             cr.move_to(zero_x - z_w / 2, zero_y - z_h / 2)
             PangoCairo.show_layout(cr, z_layout)
