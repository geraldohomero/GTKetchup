import sys
import json
import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gdk, Gio, Adw, GLib
from pomodoro import PomodoroTimer

CONFIG_PATH = os.path.expanduser("~/.config/gtketchup_gnome.json")

def load_config():
    default_config = {
        "default_time": 25,
        "scroll_min_step": 5,
        "scroll_sec_step": 5,
        "show_tutorial": True
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                return {**default_config, **config}
        except Exception as e:
            print("Failed to load config:", e)
    return default_config

def save_config(config):
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        print("Failed to save config:", e)


class PreferencesWindow(Adw.PreferencesWindow):
    def __init__(self, main_window, config, **kwargs):
        super().__init__(**kwargs)
        self.main_window = main_window
        self.config = config
        
        self.set_title("Preferences")
        self.set_default_size(400, 300)
        
        page = Adw.PreferencesPage()
        
        group = Adw.PreferencesGroup()
        group.set_title("Timer Settings")
        
        self.time_row = Adw.ActionRow()
        self.time_row.set_title("Default Time (minutes)")
        self.time_spin = Gtk.SpinButton.new_with_range(1, 999, 1)
        self.time_spin.set_valign(Gtk.Align.CENTER)
        self.time_spin.set_value(self.config["default_time"])
        self.time_row.add_suffix(self.time_spin)
        group.add(self.time_row)
        
        self.min_step_row = Adw.ActionRow()
        self.min_step_row.set_title("Scroll Minute Step")
        self.min_step_spin = Gtk.SpinButton.new_with_range(1, 60, 1)
        self.min_step_spin.set_valign(Gtk.Align.CENTER)
        self.min_step_spin.set_value(self.config["scroll_min_step"])
        self.min_step_row.add_suffix(self.min_step_spin)
        group.add(self.min_step_row)
        
        self.sec_step_row = Adw.ActionRow()
        self.sec_step_row.set_title("Scroll Second Step")
        self.sec_step_spin = Gtk.SpinButton.new_with_range(1, 60, 1)
        self.sec_step_spin.set_valign(Gtk.Align.CENTER)
        self.sec_step_spin.set_value(self.config["scroll_sec_step"])
        self.sec_step_row.add_suffix(self.sec_step_spin)
        group.add(self.sec_step_row)
        
        page.add(group)
        self.add(page)
        
        self.connect("close-request", self.on_close)
        
    def on_close(self, window):
        self.config["default_time"] = self.time_spin.get_value_as_int()
        self.config["scroll_min_step"] = self.min_step_spin.get_value_as_int()
        self.config["scroll_sec_step"] = self.sec_step_spin.get_value_as_int()
        save_config(self.config)
        
        self.main_window.timer.apply_config(self.config)
        return False


class PomodoroWindow(Adw.ApplicationWindow):
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        
        self.set_title("GTKetchup")
        self.set_default_size(500, 500)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        header = Adw.HeaderBar()
        
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        
        menu_model = Gio.Menu()
        menu_model.append("Preferences", "app.preferences")
        menu_model.append("Show Tutorial", "app.tutorial")
        menu_model.append("About GTKetchup", "app.about")
        menu_button.set_menu_model(menu_model)
        
        header.pack_end(menu_button)
        box.append(header)
        
        self.timer = PomodoroTimer(config)
        
        container = Gtk.CenterBox()
        container.set_center_widget(self.timer)
        container.set_hexpand(True)
        container.set_vexpand(True)
        
        box.append(container)
        self.set_content(box)

class MyApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.github.geraldohomero.GTKetchup',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.config = load_config()

    def do_startup(self):
        Adw.Application.do_startup(self)
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        
        # Add current directory to icon theme search path to find local SVG
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        icon_theme.add_search_path(os.path.dirname(os.path.abspath(__file__)))
        
        action_pref = Gio.SimpleAction.new("preferences", None)
        action_pref.connect("activate", self.on_preferences_action)
        self.add_action(action_pref)
        self.set_accels_for_action("app.preferences", ["<Primary>comma"])

        action_tut = Gio.SimpleAction.new("tutorial", None)
        action_tut.connect("activate", self.on_tutorial_action)
        self.add_action(action_tut)

        action_about = Gio.SimpleAction.new("about", None)
        action_about.connect("activate", self.on_about_action)
        self.add_action(action_about)

    def on_preferences_action(self, action, param):
        win = self.props.active_window
        if win:
            pref_win = PreferencesWindow(win, self.config, transient_for=win)
            pref_win.present()
            
    def on_tutorial_action(self, action, param):
        win = self.props.active_window
        if win:
            self.show_tutorial_if_needed(win, force_show=True)

    def on_about_action(self, action, param):
        win = self.props.active_window
        if win:
            about = Adw.AboutWindow(
                transient_for=win,
                application_name="GTKetchup",
                application_icon="com.github.geraldohomero.gtketchup",
                developer_name="Geraldo Homero",
                version="1.0.1",
                comments="A native GNOME Pomodoro Timer with custom Cairo visuals, formerly known as Pomodoro Timer.",
                website="https://github.com/geraldohomero/GTKetchup"
            )
            about.present()

    def show_tutorial_if_needed(self, win, force_show=False):
        if self.config.get("show_tutorial", True) or force_show:
            dialog = Adw.AlertDialog(heading="Welcome to GTKetchup!",
                                     body="Here are a few tips to get started:\n\n"
                                          "• Scroll your mouse or trackpad anywhere to adjust Minutes.\n"
                                          "• Hold Shift + Scroll to adjust Seconds.\n"
                                          "• Click the timer text in the center to input exact numbers.\n"
                                          "• Click the play button at the bottom to start/pause.")
            
            dialog.add_response("ok", "Got it!")
            dialog.set_default_response("ok")
            dialog.set_close_response("ok")
            
            check_btn = Gtk.CheckButton(label="Do not show this again")
            check_btn.set_active(not self.config.get("show_tutorial", True) and not force_show)
            check_btn.set_margin_top(10)
            check_btn.set_halign(Gtk.Align.CENTER)
            
            dialog.set_extra_child(check_btn)
            
            def on_dialog_response(dlg, response):
                if check_btn.get_active():
                    self.config["show_tutorial"] = False
                else:
                    self.config["show_tutorial"] = True
                save_config(self.config)
            
            dialog.connect("response", on_dialog_response)
            dialog.present(win)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = PomodoroWindow(self.config, application=self)
            self.show_tutorial_if_needed(win)
        win.present()

def main():
    app = MyApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
