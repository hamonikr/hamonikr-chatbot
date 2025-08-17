from gi.repository import Gtk, Adw, Gio, GLib, Pango, GtkSource, Gdk

import re
import io
import base64

from PIL import Image, UnidentifiedImageError

try:
    from ..constants import app_id, rootdir
    from .code_block import CodeBlock
except ImportError:
    from constants import app_id, rootdir
    from code_block import CodeBlock

try:
    from builtins import _  # provided by gettext.install in launcher
except ImportError:
    from gettext import gettext as _  # fallback when running out of tree


H1="H1"
H2="H2"
H3="H3"
UL="BULLET"
OL="LIST"
CODE="CODE"
BOLD="BOLD"
EMPH="EMPH"
PRE="PRE"
LINK="LINK"
m2p_sections = [
    { "name": H1, "re": re.compile(r"^(#\s+)(.*)(\s*)$"), "sub": r"<big><big><big>\2</big></big></big>" },
    { "name": H2, "re": re.compile(r"^(##\s+)(.*)(\s*)$"), "sub": r"<big><big>\2</big></big>" },
    { "name": H3, "re": re.compile(r"^(###\s+)(.*)(\s*)$"), "sub": r"<big>\2</big>" },
    { "name": UL, "re": re.compile(r"^(\s*[\*\-]\s)(.*)(\s*)$"), "sub": r" • \2" },
    { "name": OL, "re": re.compile(r"^(\s*[0-9]+\.\s)(.*)(\s*)$"), "sub": r" \1\2" },
    { "name": CODE, "re": re.compile(r"^```[a-z_]*$"), "sub": "<tt>" },
]

m2p_styles = [
    { "name": BOLD, "re": re.compile(r"(^|[^\*])(\*\*)(.*)(\*\*)"), "sub": r"\1<b>\3</b>" },
    { "name": BOLD, "re": re.compile(r"(\*\*)(.*)(\*\*)([^\*]|$)"), "sub": r"<b>\3</b>\4" },
    { "name": EMPH, "re": re.compile(r"(^|[^\*])(\*)(.*)(\*)"), "sub": r"\1<i>\3</i>" },
    { "name": EMPH, "re": re.compile(r"(\*)(.*)(\*)([^\*]|$)"), "sub": r"<i>\3</i>\4" }, 
    { "name": PRE, "re": re.compile(r"(`)([^`]*)(`)"), "sub": r"<tt>\2</tt>" },
    # 링크는 아래 안전 처리에서 수행 (href 특수문자 이스케이프)
]

re_comment = re.compile(r"^\s*<!--.*-->\s*$")
re_color = re.compile(r"^(\s*<!--\s*(fg|bg)=(#?[0-9a-z_A-Z-]*)\s*((fg|bg)=(#?[0-9a-z_A-Z-]*))?\s*-->\s*)$")
re_reset = re.compile(r"(<!--\/-->)")
re_uri = re.compile(r"http[s]?:\/\/[^\s']*")
re_href = re.compile(r"href='(http[s]?:\\/\\/[^\\s]*)'")
re_atag = re.compile(r"<a\s.*>.*(http[s]?:\\/\\/[^\\s]*).*</a>")
re_h1line = re.compile(r"^===+\s*$")
re_h2line = re.compile(r"^---+\s*$")

m2p_escapes = [
    [re.compile(r"<!--.*-->"), ''],
    [re.compile(r"&"), '&amp;'],
    [re.compile(r"<"), '&lt;'],
    [re.compile(r">"), '&gt;'],
]


@Gtk.Template(resource_path=f"{rootdir}/ui/item.ui")
class Item(Gtk.Box):
    __gtype_name__ = "Item"

    user = Gtk.Template.Child()
    content = Gtk.Template.Child()
    timestamp = Gtk.Template.Child()
    popover = Gtk.Template.Child()
    avatar = Gtk.Template.Child()
    message_bubble = Gtk.Template.Child()
    copy_button = Gtk.Template.Child()
    model = Gtk.Template.Child()

    def __init__(self, parent, chat, item, **kwargs):
        super().__init__(**kwargs)

        self.chat = chat
        self.item = item

        self.content_text = self.item["content"]

        self.parent = parent
        self.settings = parent.settings

        self.app = self.parent.get_application()
        self.win = self.app.get_active_window()

        try:
            if not isinstance(self.content_text, Image.Image):
                if isinstance(self.content_text, bytes):
                    self.image = Image.open(io.BytesIO(self.content_text))
                else:
                    self.image = Image.open(io.BytesIO(base64.b64decode(self.content_text)))
            else:
                self.image = self.content_text
        except Exception:
            # 어시스턴트 메시지이고 마크다운 콘텐츠가 있으면 WebView 렌더링 사용
            role = self.item["role"].lower()
            if (role == self.app.bot_name.lower() or role == "assistant") and self._has_markdown_content():
                self._render_with_webview()
            else:
                # 기존 방식으로 렌더링 (사용자 메시지 또는 단순 텍스트)
                self._render_with_pango()
        else:
            # 이미지인 경우의 처리
            picture = Gtk.Picture()
            picture.set_halign(Gtk.Align.CENTER)
            picture.set_can_shrink(True)
            picture.set_content_fit(Gtk.ContentFit.FILL)
            picture.set_visible(True)
            picture.add_css_class("card")
            picture.set_margin_start(12)
            picture.set_margin_end(12)
            picture.set_size_request(270, 270)
            self.image.save("/tmp/image.png")
            picture.set_file(Gio.File.new_for_path("/tmp/image.png"))
            self.content.append(picture)
                
    def _has_markdown_content(self):
        """마크다운 콘텐츠가 포함되어 있는지 확인"""
        if not self.content_text or not isinstance(self.content_text, str):
            return False
        
        markdown_indicators = [
            r'```',  # 코드 블록
            r'`[^`]+`',  # 인라인 코드
            r'#{1,6}\s',  # 헤딩
            r'\*\*[^*]+\*\*',  # 볼드
            r'\*[^*]+\*',  # 이탤릭
            r'\[[^\]]+\]\([^)]+\)',  # 링크
            r'^\s*[\*\-\+]\s',  # 리스트
            r'^\s*\d+\.\s',  # 번호 목록
            r'^\s*>',  # 인용문
            r'^\s*\|.*\|\s*$',  # 테이블 행
            r'^\s*\|[\s\-\:]*\|\s*$',  # 테이블 구분자
        ]
        
        content = str(self.content_text)
        for pattern in markdown_indicators:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False
    
    def _render_with_webview(self):
        """개선된 마크다운 렌더링 (WebKit 사용 가능시만)"""
        try:
            # WebKit 사용 가능한지 확인
            try:
                from gi.repository import WebKit2
                webkit_available = True
            except ImportError:
                webkit_available = False
            
            if webkit_available:
                # WebKit 기반 렌더링은 일단 비활성화하고 개선된 Pango 사용
                self._render_enhanced_pango()
            else:
                # WebKit 사용 불가시 개선된 Pango 렌더링 사용
                self._render_enhanced_pango()
            
        except Exception as e:
            # 모든 실패 시 기존 방식으로 폴백
            print(f"Enhanced rendering failed, falling back to basic Pango: {e}")
            self._render_with_pango()
    
    def _render_enhanced_pango(self):
        """개선된 Pango 마크업 렌더링 (마크다운 기본 지원)"""
        try:
            # 마크다운 테이블을 먼저 수동으로 처리
            processed_content = self._process_markdown_tables(self.content_text)
            
            import markdown
            
            # 기본 마크다운만 사용 (확장 사용 시 오류 발생)
            md = markdown.Markdown()
            html_content = md.convert(processed_content)
            
            # HTML을 간단한 Pango 마크업으로 변환
            pango_markup = self._html_to_pango(html_content)
            
            # 라벨 생성
            label = Gtk.Label()
            label.set_use_markup(True)
            label.set_wrap(True)
            label.set_xalign(0)
            label.set_wrap_mode(Pango.WrapMode.WORD)
            label.set_markup(pango_markup)
            label.set_justify(Gtk.Justification.LEFT)
            label.set_valign(Gtk.Align.START)
            label.set_hexpand(True)
            label.set_halign(Gtk.Align.START)
            label.set_selectable(True)
            label.add_css_class("message-content")
            
            self.content.append(label)
            
        except Exception as e:
            print(f"Enhanced Pango rendering failed: {e}")
            # 최종 폴백
            self._render_with_pango()
    
    def _html_to_pango(self, html_content):
        """HTML을 간단한 Pango 마크업으로 변환"""
        # 기본적인 HTML to Pango 변환
        content = html_content
        
        # 테이블 처리 (먼저 처리해야 함)
        content = self._process_tables(content)
        
        # HTML 태그를 Pango 마크업으로 변환
        content = re.sub(r'<h[1-6]>(.*?)</h[1-6]>', r'<big><b>\1</b></big>', content)
        content = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', content)
        content = re.sub(r'<b>(.*?)</b>', r'<b>\1</b>', content)
        content = re.sub(r'<em>(.*?)</em>', r'<i>\1</i>', content)
        content = re.sub(r'<i>(.*?)</i>', r'<i>\1</i>', content)
        content = re.sub(r'<code>(.*?)</code>', r'<tt>\1</tt>', content)
        content = re.sub(r'<pre><code>(.*?)</code></pre>', r'<tt>\1</tt>', content, flags=re.DOTALL)
        
        # 리스트 처리
        content = re.sub(r'<ul>', '', content)
        content = re.sub(r'</ul>', '', content)
        content = re.sub(r'<ol>', '', content)
        content = re.sub(r'</ol>', '', content)
        content = re.sub(r'<li>(.*?)</li>', r'• \1', content)
        
        # 단락 처리
        content = re.sub(r'<p>(.*?)</p>', r'\1\n', content)
        
        # 링크 처리 (기본적인 텍스트만)
        content = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', content)
        
        # 나머지 HTML 태그 제거
        content = re.sub(r'<[^>]+>', '', content)
        
        # HTML 엔티티 디코딩
        content = content.replace('&lt;', '<')
        content = content.replace('&gt;', '>')
        content = content.replace('&quot;', '"')
        content = content.replace('&amp;', '&')  # &amp;는 마지막에 처리
        
        # Pango 마크업을 위한 특수문자 이스케이프 (중요!)
        content = self._escape_pango_markup(content)
        
        return content.strip()
    
    def _escape_pango_markup(self, text):
        """Pango 마크업에서 안전하게 사용할 수 있도록 특수문자 이스케이프"""
        # Pango 마크업에서 문제가 되는 문자들을 이스케이프
        # 주의: 이미 마크업 태그는 처리된 상태이므로 내용만 이스케이프
        
        # 텍스트를 마크업 태그와 일반 텍스트로 분리하여 처리
        parts = []
        current_pos = 0
        
        # 마크업 태그 패턴 (<b>, <i>, <tt>, <big> 등)
        markup_pattern = r'<(/?(b|i|tt|big|small|u|s|sub|sup|span[^>]*))>'
        
        for match in re.finditer(markup_pattern, text):
            # 태그 이전의 텍스트 (이스케이프 필요)
            before_text = text[current_pos:match.start()]
            if before_text:
                escaped_text = before_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                parts.append(escaped_text)
            
            # 태그 자체 (이스케이프 불필요)
            parts.append(match.group(0))
            current_pos = match.end()
        
        # 마지막 남은 텍스트 (이스케이프 필요)
        remaining_text = text[current_pos:]
        if remaining_text:
            escaped_text = remaining_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            parts.append(escaped_text)
        
        return ''.join(parts)
    
    def _process_markdown_tables(self, content):
        """마크다운 테이블을 HTML 테이블로 변환"""
        lines = content.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 테이블 행인지 확인 (|로 시작하고 끝남)
            if line.startswith('|') and line.endswith('|'):
                # 테이블 시작
                table_lines = []
                
                # 테이블 행들 수집
                while i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                    table_lines.append(lines[i].strip())
                    i += 1
                
                # 테이블 HTML로 변환
                if len(table_lines) >= 2:  # 최소 헤더와 구분자 필요
                    html_table = self._convert_table_to_html(table_lines)
                    result_lines.append(html_table)
                else:
                    # 테이블이 아니면 원본 추가
                    result_lines.extend(table_lines)
                
                continue
            else:
                result_lines.append(lines[i])
                i += 1
        
        return '\n'.join(result_lines)
    
    def _convert_table_to_html(self, table_lines):
        """마크다운 테이블 행들을 HTML 테이블로 변환"""
        if len(table_lines) < 2:
            return '\n'.join(table_lines)
        
        # 헤더 행 파싱
        header_line = table_lines[0]
        headers = [cell.strip() for cell in header_line.split('|')[1:-1]]  # 양쪽 끝 | 제거
        
        # 구분자 행 확인 (선택적)
        separator_line = table_lines[1] if len(table_lines) > 1 else ""
        is_separator = all(c in '-:|' for c in separator_line.replace(' ', ''))
        
        # 데이터 행들
        data_start = 2 if is_separator else 1
        data_lines = table_lines[data_start:]
        
        # HTML 생성
        html = ["<table>"]
        
        # 헤더
        if headers:
            html.append("<thead><tr>")
            for header in headers:
                html.append(f"<th>{header}</th>")
            html.append("</tr></thead>")
        
        # 데이터
        if data_lines:
            html.append("<tbody>")
            for line in data_lines:
                cells = [cell.strip() for cell in line.split('|')[1:-1]]  # 양쪽 끝 | 제거
                html.append("<tr>")
                for cell in cells:
                    html.append(f"<td>{cell}</td>")
                html.append("</tr>")
            html.append("</tbody>")
        
        html.append("</table>")
        
        return ''.join(html)
    
    def _process_tables(self, content):
        """HTML 테이블을 텍스트 형태로 변환"""
        import re
        
        # 테이블 패턴 찾기
        table_pattern = r'<table[^>]*>(.*?)</table>'
        
        def format_table(match):
            table_content = match.group(1)
            
            # 테이블 헤더와 행 추출
            headers = []
            rows = []
            
            # 헤더 추출 (thead 또는 첫 번째 tr)
            thead_match = re.search(r'<thead[^>]*>(.*?)</thead>', table_content, re.DOTALL)
            if thead_match:
                header_content = thead_match.group(1)
                th_matches = re.findall(r'<th[^>]*>(.*?)</th>', header_content, re.DOTALL)
                headers = [re.sub(r'<[^>]+>', '', th).strip() for th in th_matches]
            else:
                # thead가 없으면 첫 번째 tr에서 th 찾기
                first_tr = re.search(r'<tr[^>]*>(.*?)</tr>', table_content, re.DOTALL)
                if first_tr:
                    th_matches = re.findall(r'<th[^>]*>(.*?)</th>', first_tr.group(1), re.DOTALL)
                    if th_matches:
                        headers = [re.sub(r'<[^>]+>', '', th).strip() for th in th_matches]
            
            # 데이터 행 추출
            tbody_content = table_content
            tbody_match = re.search(r'<tbody[^>]*>(.*?)</tbody>', table_content, re.DOTALL)
            if tbody_match:
                tbody_content = tbody_match.group(1)
            
            tr_matches = re.findall(r'<tr[^>]*>(.*?)</tr>', tbody_content, re.DOTALL)
            for tr in tr_matches:
                td_matches = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
                if td_matches:  # td가 있는 행만 (헤더 행 제외)
                    row_data = [re.sub(r'<[^>]+>', '', td).strip() for td in td_matches]
                    rows.append(row_data)
            
            # 테이블 포맷팅
            if not headers and not rows:
                return ""
            
            # 컬럼 너비 계산
            all_data = [headers] + rows if headers else rows
            if not all_data:
                return ""
            
            max_cols = max(len(row) for row in all_data) if all_data else 0
            col_widths = []
            
            for col in range(max_cols):
                max_width = 0
                for row in all_data:
                    if col < len(row):
                        max_width = max(max_width, len(str(row[col])))
                col_widths.append(min(max_width, 20))  # 최대 20자로 제한
            
            # 테이블 텍스트 생성
            result = []
            
            # 헤더
            if headers:
                header_line = "┌" + "┬".join("─" * (w + 2) for w in col_widths) + "┐"
                result.append(header_line)
                
                header_cells = []
                for i, header in enumerate(headers):
                    if i < len(col_widths):
                        cell = f" {header:<{col_widths[i]}} "
                        header_cells.append(cell)
                result.append("│" + "│".join(header_cells) + "│")
                
                separator = "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤"
                result.append(separator)
            
            # 데이터 행
            for row_idx, row in enumerate(rows):
                row_cells = []
                for i, cell in enumerate(row):
                    if i < len(col_widths):
                        # 긴 텍스트는 잘라내기
                        cell_text = str(cell)
                        if len(cell_text) > col_widths[i]:
                            cell_text = cell_text[:col_widths[i]-1] + "…"
                        cell_formatted = f" {cell_text:<{col_widths[i]}} "
                        row_cells.append(cell_formatted)
                
                if not headers and row_idx == 0:
                    # 헤더가 없으면 첫 번째 행 전에 상단 경계
                    top_line = "┌" + "┬".join("─" * (w + 2) for w in col_widths) + "┐"
                    result.append(top_line)
                
                result.append("│" + "│".join(row_cells) + "│")
            
            # 하단 경계
            bottom_line = "└" + "┴".join("─" * (w + 2) for w in col_widths) + "┘"
            result.append(bottom_line)
            
            return "\n".join(result) + "\n"
        
        # 모든 테이블 변환
        content = re.sub(table_pattern, format_table, content, flags=re.DOTALL)
        
        return content
    
    def _render_with_pango(self):
        """기존 Pango 마크업을 사용한 렌더링"""
        self.convert_content_to_pango()

        result = ""
        is_code = False
        for line in self.content_markup:
            if isinstance(line, str):
                if  "<tt></tt>`" in line.strip():
                    if is_code:
                        is_code = False
                    else:
                        is_code = True
                    continue
            if is_code or not isinstance(line, str):
                label = Gtk.Label()
                label.set_use_markup(True)
                label.set_wrap(True)
                label.set_xalign(0)
                label.set_wrap_mode(Pango.WrapMode.WORD)
                label.set_markup(result)
                label.set_justify(Gtk.Justification.LEFT)
                label.set_valign(Gtk.Align.START)
                label.set_hexpand(True)
                label.set_halign(Gtk.Align.START)
                label.set_selectable(True)  # 텍스트 선택 가능하게 설정
                label.add_css_class("message-content")  # 폰트 설정을 위한 CSS 클래스 추가
                self.content.append(label)

                if not isinstance(line, str):
                    result = "\n".join(line)
                else:
                    result = line.strip()

                self.content.append(CodeBlock(result))
                result = ""
            else: 
                result += f"{line}\n"
            
        else:
            if not result.strip() == "<tt></tt>`":
                label = Gtk.Label()
                label.set_use_markup(True)
                label.set_wrap(True)
                label.set_xalign(0)
                label.set_wrap_mode(Pango.WrapMode.WORD)
                label.set_markup(result)
                label.set_justify(Gtk.Justification.LEFT)
                label.set_valign(Gtk.Align.START)
                label.set_hexpand(True)
                label.set_halign(Gtk.Align.START)
                label.set_selectable(True)  # 텍스트 선택 가능하게 설정
                label.add_css_class("message-content")  # 폰트 설정을 위한 CSS 클래스 추가
                self.content.append(label)

        t = self.item["role"].lower()

        if t == self.app.user_name.lower() or t == "user": # User
            self.message_bubble.add_css_class("message-bubble-user")
            self.avatar.add_css_class("avatar-user")
            role = self.app.user_name
            # 사용자 메시지에는 복사 버튼과 모델 정보 숨김
            self.copy_button.set_visible(False)
            self.model.set_visible(False)
        elif t == self.app.bot_name.lower() or t == "assistant": # Assistant
            self.avatar.set_icon_name("bot-symbolic")
            self.user.add_css_class("warning")
            role = self.app.bot_name
            # Assistant 메시지에만 복사 버튼과 모델 정보 표시
            self.copy_button.set_visible(True)
            self.model.set_visible(True)
            # 모델 라벨이 확실히 보이도록 강제 설정
            self.model.set_opacity(1.0)
            self.model.set_sensitive(True)
        else:
            role = t
            self.copy_button.set_visible(False)
            self.model.set_visible(False)

        self.timestamp.set_text(self.item.get("time", ""))
        model_text = self.item.get("model", "")
        
        self.model.set_text(model_text)

        self.avatar.set_text(role)
        self.user.set_text(role)

        self.setup()

    def setup(self):
        self.setup_signals()

        evk = Gtk.GestureClick.new()
        evk.connect("pressed", self.show_menu)
        evk.set_button(3)
        self.add_controller(evk)

    def show_menu(self, gesture, data, x, y):
        self.popover.set_parent(self)
        self.popover.popup()

    def setup_signals(self):
        self.action_group = Gio.SimpleActionGroup()
        self.create_action("delete", self.on_delete)
        self.create_action("edit", self.on_edit)
        self.create_action("save", self.on_save)
        self.create_action("copy", self.on_copy)
        self.insert_action_group("event", self.action_group);

    def create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.action_group.add_action(action)

        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    def on_delete(self, *args, **kwargs):
        self.chat["content"].remove(self.item)
        self.win.threads_row_activated_cb()

    def on_edit(self, *args):
        self.win.message_entry.get_buffer().set_text(self.content_text)

    def on_save(self, *args):
        def on_save_response(dialog, response):
            if response == Gtk.ResponseType.OK:
                toast = Adw.Toast()
                try:
                    self.image.save(dialog.get_file().get_path())
                except Exception as e:
                    toast.set_title(_("Failed to save the image"))
                else:
                    toast.set_title(_("Image saved"))
                finally:
                    self.parent.toast_overlay.add_toast(toast)

            dialog.destroy()

        try:
            self.image
        except AttributeError:
            toast = Adw.Toast()
            toast.set_title(_("No image to save"))
            self.parent.toast_overlay.add_toast(toast)
        else:
            dialog = Gtk.FileChooserDialog(
                title=_("Save message"),
                action=Gtk.FileChooserAction.SAVE,
                modal=True,
                transient_for=self.win,
            )
            dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
            dialog.add_button(_("Save"), Gtk.ResponseType.OK)

            dialog.connect('response', on_save_response)
            dialog.present()

        
    def on_copy(self, *args):
        Gdk.Display.get_default().get_clipboard().set(self.content_text)

    @Gtk.Template.Callback()
    def on_copy_button_clicked(self, *args):
        """복사 버튼 클릭 시 실행되는 메소드"""
        # 클립보드에 텍스트 복사
        Gdk.Display.get_default().get_clipboard().set(self.content_text)
        
        # 시각적 피드백 - 버튼 아이콘을 잠시 체크마크로 변경
        original_icon = self.copy_button.get_icon_name()
        self.copy_button.set_icon_name("check-round-outline2-symbolic")
        self.copy_button.set_tooltip_text(_("Copied!"))
        
        # 토스트 메시지 표시
        toast = Adw.Toast()
        toast.set_title(_("Message copied to clipboard"))
        toast.set_timeout(2)
        self.parent.toast_overlay.add_toast(toast)
        
        # 1.5초 후 원래 아이콘으로 복원
        def restore_icon():
            self.copy_button.set_icon_name(original_icon)
            self.copy_button.set_tooltip_text(_("Copy message"))
            return False  # GLib.timeout_add에서 False 반환하면 타이머 종료
        
        GLib.timeout_add(1500, restore_icon)



    def convert_content_to_pango(self):
        lines = self.content_text.split("\n")

        is_code = False
        code_lines = []

        output = []
        self.color_span_open = False
        tt_must_close = False

        def try_close_span():
            if self.color_span_open:
                output.append('</span>')
                self.color_span_open = False
            
        def try_open_span():
            if not self.color_span_open:
                output.append('</span>')
                self.color_span_open = False

        def escape_line(line):
            for escape in m2p_escapes:
                line = re.sub(escape[0], escape[1], line)
            return line

        def escape_attr(s: str) -> str:
            return (
                s.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace("'", "&apos;")
                 .replace('"', "&quot;")
            )

        re_md_link = re.compile(r"\[(?P<text>[^\]]+)\]\((?P<url>[^\s)]+)\)")

        # def pad(lines, start=1, end=1):
        #     length = 0
        #     for line in lines:
        #         if len(line) > 0:
        #             length += len(line)
        #         else:
        #             length += 0
        #     for line in lines:
        #         line.rjust()
        #     return lines.map((l) => l.padEnd(len + end, ' ').padStart(len + end + start, ' '))


        for line in lines:
            if not is_code:
                colors = re_color.match(line)
                if colors or re_reset.match(line):
                    try_close_span()
                

                if colors:
                    try_close_span()
                    if self.color_span_open:
                        try_close_span()

                    if colors[2] == 'fg':
                        fg = colors[3]
                    elif colors[5] == 'fg':
                        fg = colors[6]
                    else:
                        fg = ""
                    
                    if colors[2] == 'bg':
                        fg = colors[3]
                    elif colors[5] == 'bg':
                        fg = colors[6]
                    else:
                        fg = ""
                    
                    attrs = ''

                    if fg != '':
                        attrs += f" foreground='{fg}'"
                    

                    if bg != '':
                        attrs += f" background='{bg}'"

                    if attrs != '':
                        output.append("<span {attrs}>")
                        self.color_span_open = True
            
            if re_comment.match(line):
                continue

            code_start = False

            if is_code:
                result = line
            else:
                result = escape_line(line)

            for exp in m2p_sections:
                name = exp["name"]
                regexp = exp["re"]
                sub = exp["sub"]
                if regexp.match(line):
                    if name == CODE:
                        if not is_code:
                            code_start = True
                            is_code = True

                            result = ""

                            #if self.color_span_open:
                            #    result = '<tt>'
                            #    tt_must_close = False
                            #else:
                            #    result = "<span foreground='#bbb' background='#222'>" + '<tt>'
                            #    tt_must_close = True
                        else:
                            is_code = False
                            #output.append(...pad(code_lines).map(escape_line))
                            output.append(code_lines)
                            code_lines = []
                            #result = '</tt>'
                            if tt_must_close:
                                result += '</span>'
                                tt_must_close = False
                    else:
                        if is_code:
                            result = line
                        else:
                            # 섹션 치환은 이스케이프된 문자열(result)에 적용해야 &/< />가 보존됩니다.
                            result = re.sub(regexp, sub, result)

            if is_code and not code_start:
                code_lines.append(result)
                continue
            

            if re_h1line.match(line):
                output.append(re.sub(m2p_sections[0]["re"], m2p_sections[0]["sub"], f"# {output.pop()}"))
                continue
            

            if re_h2line.match(line):
                output.append(re.sub(m2p_sections[1]["re"], m2p_sections[1]["sub"], f"# {output.pop()}"))
                continue
            
            for style in m2p_styles:
                regexp = style["re"]
                sub = style["sub"]
                result = re.sub(regexp, sub, result)
            

            # 마크다운 링크 [text](url) → 안전한 앵커로 변환 (텍스트도 이스케이프)
            result = re_md_link.sub(lambda m: f"<a href='{escape_attr(m.group('url'))}'>{escape_line(m.group('text'))}</a>", result)

            # 벌거벗은 URL을 안전하게 감싸기 (이미 링크 포함이면 패스)
            if not (re_href.search(result) or re_atag.search(result)):
                for m in re.finditer(re_uri, result):
                    u = m.group(0)
                    result = result.replace(u, f"<a href='{escape_attr(u)}'>{escape_line(u)}</a>")

            output.append(result)

        try_close_span()

        self.content_markup = output
