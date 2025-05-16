#!/usr/bin/env python3
import os
import socket
import threading
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

# --- (Paste your CATPPUCCIN_CSS and all your ClipboardPreview code here) ---
#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango
import subprocess
import os
import re

# --- Catppuccin Macchiato CSS ---
CATPPUCCIN_CSS = b"""
window#ClipboardHistoryWindow { /* Target specific window */
    background-color: #1e1e2e; /* Base */
    color: #cdd6f4; /* Text */
    font-family: "JetBrainsMono Nerd Font", monospace;
    font-size: 10pt;
    border: 2px solid #cba6f7; /* Mauve border for the floating window */
    border-radius: 8px; /* Rounded corners for the floating window */
    box-shadow: 0 4px 12px rgba(0,0,0,0.5); /* Optional shadow */
}

treeview#HistoryTreeView {
    background-color: #181926; /* Mantle */
    border: none; /* Remove internal border, window has one */
    color: #cdd6f4; /* MODIFIED: Explicitly set text color for items */
    /* border-radius: 5px; */ /* Not needed if window has radius */
}

treeview#HistoryTreeView row {
    padding: 6px 8px; /* Slightly more padding */
    border-radius: 4px;
    /* color: #cdd6f4; <- Moved to treeview#HistoryTreeView for default */
}


treeview#HistoryTreeView *:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
}

treeview#HistoryTreeView:focus,
treeview#HistoryTreeView *:focus {
    outline: none;
    box-shadow: none;
}

scrolledwindow {
    border: 1px solid #313244; /* Surface0 */
    border-radius: 5px;
    background-color: #181926; /* Mantle for trough area */
}

scrollbar {
    background-color: transparent;
    border: none;
    min-width: 10px;
    min-height: 10px;
}

scrollbar slider {
    background-color: #45475a; /* Surface1 */
    border-radius: 5px;
    border: 1px solid #585b70; /* Surface2 */
}

scrollbar slider:hover {
    background-color: #6c7086; /* Overlay0 */
}

scrollbar trough {
    background-color: #1e1e2e; /* Base - to match window bg */
    border-radius: 5px;
}

label#PreviewTextLabel {
    color: #cdd6f4; /* Text */
    padding: 8px; /* More padding */
}

box#PreviewContentBox {
    background-color: #181926; /* Mantle for the preview content area */
    border-radius: 5px; /* Rounded corners for the preview box */
    padding: 5px;
}
"""

def get_cliphist_entries():
    try:
        result = subprocess.run(
            ["cliphist", "list", "--reverse"],
            capture_output=True,
            text=True,  # Keep this for convenience if most output is text
            check=True,
            encoding='utf-8',  # Explicitly state encoding
            errors='replace'   # Replace undecodable bytes with a placeholder (e.g., �)
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running cliphist list: {e}")
        if e.stderr:
            # Also print stderr from cliphist if available, it might have clues
            print(f"cliphist stderr: {e.stderr}")
        return []
    except UnicodeDecodeError as e: # Should be caught by errors='replace' now, but good for debugging
        print(f"UnicodeDecodeError while processing cliphist list output: {e}")
        # Potentially try to get the raw bytes and decode them with replacement manually
        # if subprocess.run with errors='replace' isn't sufficient.
        # For now, just return empty or a specific error message.
        return [] # Or handle more gracefully

    lines_from_cliphist = result.stdout.strip().split("\n")
    processed_entries = []

    for original_line in lines_from_cliphist:
        if not original_line.strip():
            continue
        # The original_line is now text, with bad bytes replaced.
        # The rest of your processing should be fine.
        content_for_display = re.sub(r"^\s*\d+\s+", "", original_line).strip()
        if re.match(r"\[\[ binary data .* (png|jpeg|jpg|webp|gif)", content_for_display, re.IGNORECASE):
            display_text = "🖼️ " + content_for_display
        else:
            short_text_for_display = content_for_display.replace("\n", " ")[:70]
            if len(content_for_display) > 70:
                short_text_for_display += "..."
            display_text = short_text_for_display
        processed_entries.append((original_line, display_text))
    return processed_entries

def decode_entry_content(original_cliphist_line):
    try:
        p = subprocess.Popen(
            ["cliphist", "decode"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = p.communicate(input=original_cliphist_line.encode())
        if p.returncode != 0:
            print(f"cliphist decode error: {err.decode(errors='replace')}")
            return None
        return out
    except Exception as e:
        print(f"Exception in decode_entry_content: {e}")
        return None

def copy_to_clipboard(data_bytes):
    try:
        p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
        p.communicate(input=data_bytes)
    except Exception as e:
        print(f"Error copying to clipboard: {e}")

class ClipboardPreview(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Clipboard History")
        self.set_name("ClipboardHistoryWindow")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)

        self.set_border_width(0)
        self.set_default_size(1000, 600)
        self.set_resizable(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("key-press-event", self.on_key_press)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CATPPUCCIN_CSS)
        screen = Gdk.Screen.get_default()
        style_context = self.get_style_context()
        style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer_box.get_style_context().add_class("window-content-area")
        self.add(outer_box)

        main_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        main_hbox.set_margin_top(10)
        main_hbox.set_margin_bottom(10)
        main_hbox.set_margin_start(10)
        main_hbox.set_margin_end(10)
        outer_box.pack_start(main_hbox, True, True, 0)

        self.entries_data = get_cliphist_entries()
        self.liststore = Gtk.ListStore(str, str)
        for original_line, display_text in self.entries_data:
            self.liststore.append([original_line, display_text])

        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_name("HistoryTreeView")
        renderer = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
        # Note: Text color for renderer is now handled by CSS on HistoryTreeView
        column = Gtk.TreeViewColumn("History", renderer, text=1)
        self.treeview.append_column(column)
        self.treeview.get_selection().connect("changed", self.on_selection_changed)
        self.treeview.set_headers_visible(False)
        self.treeview.set_size_request(380, -1)

        scrolled_list = Gtk.ScrolledWindow()
        scrolled_list.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_list.add(self.treeview)
        main_hbox.pack_start(scrolled_list, False, False, 0)

        self.preview_scrolled_window = Gtk.ScrolledWindow()
        self.preview_scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.preview_scrolled_window.set_hexpand(True)
        self.preview_scrolled_window.set_vexpand(True)
        main_hbox.pack_start(self.preview_scrolled_window, True, True, 0)

        self.preview_content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.preview_content_box.set_name("PreviewContentBox")
        self.preview_scrolled_window.add(self.preview_content_box)

        self.preview_image_widget = Gtk.Image()
        self.preview_image_widget.set_name("PreviewImageWidget")
        self.preview_text_label = Gtk.Label(label="")
        self.preview_text_label.set_name("PreviewTextLabel")
        self.preview_text_label.set_line_wrap(True)
        self.preview_text_label.set_xalign(0.0)
        self.preview_text_label.set_yalign(0.0)
        self.preview_text_label.set_selectable(True)
        
        self.preview_content_box.pack_start(self.preview_image_widget, False, False, 5)
        self.preview_content_box.pack_start(self.preview_text_label, False, False, 5)

        if self.entries_data:
            self.treeview.get_selection().select_path(Gtk.TreePath.new_first())
            GLib.idle_add(self.scroll_to_selected_row)
        else:
            self.preview_text_label.set_text("Clipboard history is empty.")
            self.preview_text_label.show()
            self.preview_image_widget.hide()
        
        # self.grab_focus() # Called on the window. For modal dialogs, GTK often handles this.
                         # If focus is an issue, try self.treeview.grab_focus() after show_all.

    def scroll_to_selected_row(self):
        selection = self.treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            path = model.get_path(treeiter)
            self.treeview.scroll_to_cell(path, None, True, 0.5, 0.0)
        return False


    def on_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter is None:
            self.preview_image_widget.clear(); self.preview_image_widget.hide()
            self.preview_text_label.set_text(""); self.preview_text_label.hide()
            return

        original_line_for_decode = model[treeiter][0]
        decoded_content_bytes = decode_entry_content(original_line_for_decode)

        if decoded_content_bytes is None:
            self.preview_image_widget.clear(); self.preview_image_widget.hide()
            self.preview_text_label.set_text("Error decoding entry."); self.preview_text_label.show()
            return

        display_text_from_list = model[treeiter][1]
        is_likely_image = display_text_from_list.startswith("🖼️")

        if is_likely_image:
            try:
                loader = GdkPixbuf.PixbufLoader()
                loader.write(decoded_content_bytes)
                loader.close()
                pixbuf = loader.get_pixbuf()
                if not pixbuf: raise ValueError("Failed to load pixbuf from loader")
                
                preview_alloc = self.preview_scrolled_window.get_allocation()
                max_width = max(100, preview_alloc.width - 20) # Adjusted padding guess
                max_height = max(100, preview_alloc.height - 20) # Adjusted padding guess
                img_width, img_height = pixbuf.get_width(), pixbuf.get_height()
                if img_width == 0 or img_height == 0: raise ValueError("Image has zero dimensions")

                scale = min(max_width / img_width, max_height / img_height, 1.0)
                scaled_pixbuf = pixbuf.scale_simple(int(img_width * scale), int(img_height * scale), GdkPixbuf.InterpType.BILINEAR)
                self.preview_image_widget.set_from_pixbuf(scaled_pixbuf)
                self.preview_image_widget.show(); self.preview_text_label.hide()
            except GLib.Error as e:
                 print(f"GdkPixbuf Error loading image preview: {e}")
                 self.show_decode_error_fallback(decoded_content_bytes)
            except Exception as e:
                print(f"Generic error loading image preview: {e}")
                self.show_decode_error_fallback(decoded_content_bytes)
        else: 
            self.preview_image_widget.clear(); self.preview_image_widget.hide()
            try:
                text_content = decoded_content_bytes.decode(errors='replace')
                self.preview_text_label.set_text(text_content)
            except Exception as e: self.preview_text_label.set_text(f"Error decoding text: {e}")
            self.preview_text_label.show()

    def show_decode_error_fallback(self, decoded_content_bytes):
        self.preview_image_widget.clear(); self.preview_image_widget.hide()
        try:
            text_content = decoded_content_bytes.decode(errors='replace')
            self.preview_text_label.set_text(f"Could not display image. Raw data (partial):\n{text_content[:500]}")
        except: self.preview_text_label.set_text("Could not display image or its raw data.")
        self.preview_text_label.show()

    def on_key_press(self, widget, event):
        keyval_name = Gdk.keyval_name(event.keyval)
        if keyval_name == "Return":
            selection = self.treeview.get_selection()
            model, treeiter = selection.get_selected()
            if treeiter is not None:
                original_line_for_decode = model[treeiter][0]
                decoded_content_bytes = decode_entry_content(original_line_for_decode)
                if decoded_content_bytes is not None: copy_to_clipboard(decoded_content_bytes)
                #Gtk.main_quit()
                self.destroy()
            return True # MODIFIED: Event handled
        elif keyval_name == "Escape":
            #Gtk.main_quit()
            self.destroy()
            return True # MODIFIED: Event handled
        elif keyval_name in ("j", "Down"):
            self.move_selection(1)
            return True # MODIFIED: Event handled, stop propagation
        elif keyval_name in ("k", "Up"):
            self.move_selection(-1)
            return True # MODIFIED: Event handled, stop propagation
        return False # Allow other handlers if needed (e.g., for typing in a search bar if you add one)

    def move_selection(self, direction):
        selection = self.treeview.get_selection()
        model, treeiter = selection.get_selected()
        if not treeiter: 
            if direction == 1 and len(model) > 0: # If nothing selected and moving down, select first
                new_path = Gtk.TreePath.new_from_string("0")
                self.treeview.set_cursor(new_path, None, False)
                GLib.idle_add(self.scroll_to_selected_row)
            elif direction == -1 and len(model) > 0: # If nothing selected and moving up, select last
                new_path = Gtk.TreePath.new_from_string(str(len(model)-1))
                self.treeview.set_cursor(new_path, None, False)
                GLib.idle_add(self.scroll_to_selected_row)
            return

        current_path = model.get_path(treeiter)
        current_indices = current_path.get_indices() # This returns a list/tuple of indices
        if not current_indices: return # Should not happen if treeiter is valid

        new_row = current_indices[0] + direction # For flat list, first index is the row
        if 0 <= new_row < len(model):
            new_path = Gtk.TreePath.new_from_string(str(new_row))
            self.treeview.set_cursor(new_path, None, False)
            GLib.idle_add(self.scroll_to_selected_row)




# ... (Paste your existing code here, up to and including ClipboardPreview) ...

SOCKET_PATH = "/tmp/clipboard_preview.sock"

def remove_socket():
    try:
        os.unlink(SOCKET_PATH)
    except FileNotFoundError:
        pass

class ClipboardPreviewDaemon:
    def __init__(self):
        self.window = None
        self.server_thread = threading.Thread(target=self.socket_server, daemon=True)
        self.server_thread.start()

    def socket_server(self):
        remove_socket()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SOCKET_PATH)
        server.listen(1)
        while True:
            conn, _ = server.accept()
            data = conn.recv(1024)
            if data == b"show":
                GLib.idle_add(self.show_window)
            conn.close()

    def show_window(self):
        if self.window is not None and self.window.get_visible():
            self.window.present()
            return
        self.window = ClipboardPreview()
        self.window.connect("destroy", self.on_window_destroy)
        self.window.show_all()
        self.window.present()

    def on_window_destroy(self, widget):
        self.window = None

if __name__ == "__main__":
    remove_socket()
    daemon = ClipboardPreviewDaemon()
    Gtk.main()
