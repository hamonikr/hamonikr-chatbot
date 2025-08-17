from gi.repository import Gtk, GtkSource, Adw, Xdp

try:
    from ..constants import app_id, rootdir
except ImportError:
    from constants import app_id, rootdir

import subprocess
from subprocess import SubprocessError, CompletedProcess
import os
import gettext

# gettext 설정
_ = gettext.gettext

GtkSource.init()

@Gtk.Template(resource_path=f"{rootdir}/ui/code_block.ui")
class CodeBlock(Gtk.Widget):
    __gtype_name__ = "CodeBlock"

    buffer = Gtk.Template.Child()
    source_view = Gtk.Template.Child()
    output_buffer = Gtk.Template.Child()
    output_source_view = Gtk.Template.Child()
    view = Gtk.Template.Child()
    box = Gtk.Template.Child()
    output = Gtk.Template.Child()

    def __init__(self, result, **kwargs):
        super().__init__(**kwargs)

        self.command = result

        self.buffer.set_text(self.command)
        
        # CSS 클래스 추가로 폰트 설정 적용
        self.source_view.add_css_class("code-block")
        self.output_source_view.add_css_class("code-block")

        self._apply_sourceview_scheme()

        # 테마 변경 시 즉시 반영
        try:
            Adw.StyleManager.get_default().connect("notify::dark", self._on_style_changed)
        except Exception:
            pass
        

    @Gtk.Template.Callback()
    def run(self, widget, *args):
        command_text = self.buffer.props.text.strip()
        if not command_text:
            return
        
        # $ 기호로 시작하는 경우 제거
        if command_text.startswith("$"):
            command_text = command_text[1:].strip()
        
        # 주석이나 빈 줄 무시
        if command_text.startswith("#") or not command_text:
            self.output_buffer.set_text("# 주석은 실행할 수 없습니다.")
            self.output.set_visible(True)
            return
        
        command = command_text.split()
        if not command:
            return

        portal = Xdp.Portal()
        is_sandboxed = portal.running_under_sandbox()
        output = self._run(command, allow_escaping=is_sandboxed)
        self.output_buffer.set_text(output)
        self.output.set_visible(True)

    def _run(self, command: list, timeout: int = None, allow_escaping: bool = False) -> CompletedProcess:
        if allow_escaping and os.environ.get('FLATPAK_ID'):
            command = ['flatpak-spawn', '--host'] + command

        try:
            process = subprocess.run(command, capture_output=True, text=True)
            if process.returncode != 0:
                output = process.stderr
            else:
                if process.stdout == "":
                    output = _("Done")
                else:
                    output = process.stdout
        except SubprocessError as e:
            output = e.stdout if hasattr(e, 'stdout') else str(e)
        except FileNotFoundError as e:
            output = f"명령어를 찾을 수 없습니다: {command[0]}"
        except Exception as e:
            output = f"실행 오류: {str(e)}"

        o = ""

        for line in output.split("\n"):
            if line == "":
                continue
            elif line.strip().startswith("** (flatpak-spawn:"):
                continue
            elif line.strip().startswith("(flatpak-spawn:"):
                continue
            else:
                if line.strip() == "":
                    o += _("Done") + "\n"
                else:
                    o += line + "\n"

        return o

    def _apply_sourceview_scheme(self):
        try:
            is_dark = Adw.StyleManager().get_dark()
        except Exception:
            is_dark = False
        scheme_id = "Adwaita-dark" if is_dark else "Adwaita"
        mgr = GtkSource.StyleSchemeManager()
        self.buffer.set_style_scheme(mgr.get_scheme(scheme_id))
        self.output_buffer.set_style_scheme(mgr.get_scheme(scheme_id))

    def _on_style_changed(self, *args):
        self._apply_sourceview_scheme()