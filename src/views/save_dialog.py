from gi.repository import Gtk, Adw, Gio, Gdk

try:
    from ..constants import app_id, rootdir
except ImportError:
    from constants import app_id, rootdir

try:
    from builtins import _  # provided by gettext.install in launcher
except ImportError:
    from gettext import gettext as _  # fallback when running out of tree

@Gtk.Template(resource_path=f"{rootdir}/ui/save_dialog.ui")
class SaveDialog(Adw.MessageDialog):
    __gtype_name__ = "SaveDialog"

    filename = Gtk.Template.Child()
    file_chooser = Gtk.Template.Child()
    location = Gtk.Template.Child()

    def __init__(self, parent, text, **kwargs):
        super().__init__(**kwargs)

        self.text: str = text
        self.parent = parent

    @Gtk.Template.Callback()
    def handle_response(self, dialog, response, *args, **kwargs):
        if response == "save":
            filename = self.filename.get_text()
            path = f"{self.directory}/{filename}.md"

            toast = Adw.Toast()
            try:
                with open(path, "w") as f:
                    f.write(self.text)
            except FileNotFoundError:
                toast.set_title(_("Unable to save the Thread"))
            else:
                toast.set_title(_("Thread successfully saved!"))
            self.parent.toast_overlay.add_toast(toast)

    @Gtk.Template.Callback()
    def on_location_button_clicked(self, widget, *args):
        self.file_chooser.select_folder(self, None, self.on_filechooser_response)
    
    def on_filechooser_response(self, widget, response):
        try:
            # 파일 선택이 성공한 경우에만 처리
            file = self.file_chooser.select_folder_finish(response)
            if file:
                self.directory = file.get_path()
                self.location.set_subtitle(self.directory)
                self.update_save_status()
        except Exception as e:
            # 사용자가 취소하거나 다른 오류가 발생한 경우 무시
            print(f"File chooser cancelled or error occurred: {e}")
            # 아무것도 하지 않고 그냥 넘어감

    @Gtk.Template.Callback()
    def on_entry_activated(self, widget, *args):
        self.update_save_status()

    def update_save_status(self):
        try:
            self.directory
        except Exception:
            self.set_response_enabled("save", False)
        else:
            if self.filename.get_text().strip():
                self.set_response_enabled("save", True)
            else:
                self.set_response_enabled("save", False)
