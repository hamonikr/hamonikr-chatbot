from gi.repository import Gtk, Adw, Gio, GtkSource, Gdk

from ..constants import app_id, rootdir
from .save_dialog import SaveDialog

GtkSource.init()

@Gtk.Template(resource_path=f"{rootdir}/ui/export_dialog.ui")
class ExportDialog(Adw.MessageDialog):
    __gtype_name__ = "ExportDialog"

    buffer = Gtk.Template.Child()
    source_view = Gtk.Template.Child()

    def __init__(self, parent, chat, **kwargs):
        super().__init__(**kwargs)

        self.text: str = ""
        self.parent = parent
        for i, x in zip(chat, range(len(chat))):
            self.text += f"{i['role']}: {i['content']}\n"

            if (x % 2) != 0:
                self.text += "\n"

        self.text = self.text[:-2]
        self.buffer.set_text(self.text)
        self._apply_sourceview_scheme()
        try:
            Adw.StyleManager.get_default().connect("notify::dark", self._on_style_changed)
        except Exception:
            pass


    @Gtk.Template.Callback()
    def copy(self, *args, **kwargs):
        Gdk.Display.get_default().get_clipboard().set(self.text)

    @Gtk.Template.Callback()
    def handle_response(self, dialog, response, *args, **kwargs):
        if response == "export":
            dialog = SaveDialog(self.parent, self.text)
            dialog.set_transient_for(self.parent)
            dialog.present()

    def _apply_sourceview_scheme(self):
        try:
            is_dark = Adw.StyleManager().get_dark()
        except Exception:
            is_dark = False
        scheme_id = "Adwaita-dark" if is_dark else "Adwaita"
        mgr = GtkSource.StyleSchemeManager()
        self.buffer.set_style_scheme(mgr.get_scheme(scheme_id))

    def _on_style_changed(self, *args):
        self._apply_sourceview_scheme()
