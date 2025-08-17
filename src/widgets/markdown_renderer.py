# GTK와 WebKit 버전 설정 (독립 실행 가능하도록)
import gi

# 버전이 이미 로드되었는지 확인
try:
    from gi.repository import Gtk
    # GTK가 이미 로드된 경우
except ImportError:
    # GTK가 로드되지 않은 경우 버전 설정
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    gi.require_version('WebKit2', '4.1')
    from gi.repository import Gtk

from gi.repository import GLib, Gio
try:
    from gi.repository import Adw
except ImportError:
    Adw = None
import markdown
import re
import os

# WebKit는 선택적으로 import (없어도 기본 기능 동작)
WEBKIT_AVAILABLE = False
WEBKIT_MODULE = None

# GTK4용 WebKit 6.0 시도 (권장)
try:
    gi.require_version('WebKit', '6.0')
    from gi.repository import WebKit as WebKitModule
    WEBKIT_AVAILABLE = True
    WEBKIT_MODULE = WebKitModule
    pass  # WebKit 6.0 available
except (ImportError, ValueError):
    # GTK3용 WebKit2 4.1 폴백 시도 (GTK4와 호환되지 않음)
    try:
        gi.require_version('WebKit2', '4.1')
        from gi.repository import WebKit2 as WebKitModule
        # GTK 버전 충돌 검사
        from gi.repository import Gtk
        if Gtk.get_major_version() == 4:
            WEBKIT_AVAILABLE = False
        else:
            WEBKIT_AVAILABLE = True
            WEBKIT_MODULE = WebKitModule
    except (ImportError, ValueError):
        WEBKIT_AVAILABLE = False

# Pygments는 선택적으로 import
try:
    from pygments.formatters import HtmlFormatter
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


class MarkdownRenderer(Gtk.Box):
    """WebKit 기반 마크다운 렌더러 위젯"""
    
    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        
        self.webview = None
        
        if WEBKIT_AVAILABLE:
            try:
                pass  # Initializing WebView
                # WebView 설정
                self.webview = WEBKIT_MODULE.WebView()
                self.webview.set_hexpand(True)
                self.webview.set_vexpand(True)
                
                # 웹 설정 (WebKit 6.0 호환)
                settings = self.webview.get_settings()
                settings.set_enable_javascript(True)  # 높이 측정을 위해 필요
                settings.set_enable_page_cache(False)
                settings.set_enable_offline_web_application_cache(False)
                settings.set_enable_html5_database(False)
                settings.set_enable_html5_local_storage(False)
                settings.set_enable_webgl(False)
                settings.set_enable_webaudio(False)
                settings.set_enable_media(False)
                settings.set_enable_mediasource(False)
                settings.set_enable_encrypted_media(False)
                settings.set_enable_media_stream(False)
                
                # 하드웨어 가속 정책 설정 (WebKit 6.0에서 변경되었을 수 있음)
                try:
                    settings.set_hardware_acceleration_policy(WEBKIT_MODULE.HardwareAccelerationPolicy.NEVER)
                except AttributeError:
                    # WebKit 6.0에서 하드웨어 가속 정책이 제거되었을 수 있음
                    pass
                
                # WebView를 직접 추가하고 확장 가능하게 설정
                self.webview.set_hexpand(True)
                self.webview.set_vexpand(True)
                
                # 기본 크기 설정 (더 큰 높이)
                self.webview.set_size_request(-1, 300)  # 기본 300px 높이
                
                self.append(self.webview)
                
                # 내용 로드 완료 시 높이 조정
                self.webview.connect('load-changed', self._on_load_changed)
                
                pass  # WebView initialized
            except Exception:
                self.webview = None
        
        # WebKit를 사용할 수 없으면 폴백 표시
        if self.webview is None:
            self.fallback_label = Gtk.Label()
            self.fallback_label.set_text("WebKit를 사용할 수 없어 마크다운 렌더링이 제한됩니다.")
            self.fallback_label.set_wrap(True)
            self.fallback_label.set_use_markup(True)
            self.fallback_label.set_selectable(True)
            
            # 스크롤 가능한 컨테이너에 넣기
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_child(self.fallback_label)
            scrolled.set_min_content_height(100)
            
            self.append(scrolled)
        
        # 마크다운 확장 설정 (안전한 방식)
        self.markdown_extensions = []
        
        # 안전한 기본 확장들만 사용 (확장 없이 수동 테이블 처리)
        try:
            # 기본 마크다운만 사용 (확장 없이)
            test_md = markdown.Markdown()
            test_md.convert("test")
            pass  # Basic markdown available
        except Exception:
            pass
        
        # 코드 하이라이트 설정
        self.codehilite_config = {}
        
        # CSS 스타일 생성
        self.css_style = self._generate_css()
        
    def _generate_css(self):
        """GTK 테마에 맞는 CSS 스타일 생성"""
        
        # 현재 다크 모드 상태 확인
        is_dark = False
        if Adw:
            try:
                style_manager = Adw.StyleManager.get_default()
                is_dark = style_manager.get_dark()
                pass  # Dark mode status detected
            except Exception:
                pass
        
        # 다크/라이트 모드에 따른 색상 설정
        if is_dark:
            # 다크 모드 색상
            bg_color = "#242424"  # 더 자연스러운 다크 배경
            text_color = "#ffffff"
            border_color = "#555753"
            table_bg = "#2a2a2a"
            table_header_bg = "#3a3a3a"
            table_alt_bg = "#252525"
            code_bg = "#2d2d2d"
            blockquote_bg = "rgba(85, 87, 83, 0.2)"
            blockquote_border = "#555753"
            link_color = "#729fcf"
        else:
            # 라이트 모드 색상
            bg_color = "#ffffff"
            text_color = "#2e3436"
            border_color = "#d3d7cf"
            table_bg = "#ffffff"
            table_header_bg = "rgba(114, 159, 207, 0.15)"
            table_alt_bg = "rgba(114, 159, 207, 0.05)"
            code_bg = "rgba(46, 52, 54, 0.05)"
            blockquote_bg = "rgba(114, 159, 207, 0.1)"
            blockquote_border = "#729fcf"
            link_color = "#204a87"
        
        # Pygments CSS 생성 (선택적)
        pygments_css = ""
        if PYGMENTS_AVAILABLE:
            try:
                formatter = HtmlFormatter(style='github-dark', cssclass='highlight')
                pygments_css = formatter.get_style_defs('.highlight')
            except Exception:
                pygments_css = ""
        
        return f"""
        <style>
        body {{
            font-family: -gtk-system-font, system-ui, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: {text_color} !important;
            background-color: {bg_color} !important;
            margin: 0;
            padding: 12px 12px 20px 12px;
            word-wrap: break-word;
            overflow-x: hidden;
            overflow-y: auto;
            min-height: 100vh;
        }}
        
        html {{
            overflow-x: hidden;
            overflow-y: auto;
            height: auto;
            min-height: 100vh;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 16px;
            margin-bottom: 8px;
            font-weight: 600;
            line-height: 1.25;
        }}
        
        h1 {{ font-size: 1.8em; }}
        h2 {{ font-size: 1.5em; }}
        h3 {{ font-size: 1.25em; }}
        h4 {{ font-size: 1.1em; }}
        h5 {{ font-size: 1em; }}
        h6 {{ font-size: 0.9em; }}
        
        p {{
            margin-bottom: 12px;
        }}
        
        ul, ol {{
            margin: 8px 0;
            padding-left: 24px;
        }}
        
        li {{
            margin: 4px 0;
        }}
        
        blockquote {{
            margin: 12px 0;
            padding: 8px 16px;
            border-left: 4px solid {blockquote_border};
            background-color: {blockquote_bg};
            font-style: italic;
        }}
        
        code {{
            background-color: {code_bg};
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Source Code Pro', 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            color: {text_color};
        }}
        
        pre {{
            background-color: {code_bg};
            border: 1px solid {border_color};
            border-radius: 6px;
            padding: 12px;
            overflow-x: auto;
            margin: 12px 0;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
            border-radius: 0;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 12px 0;
            border: 2px solid {border_color};
            font-family: -gtk-system-font, system-ui, sans-serif;
            font-size: 14px;
            background-color: {table_bg};
        }}
        
        th, td {{
            border: 1px solid {border_color};
            padding: 10px 14px;
            text-align: left;
            vertical-align: top;
            word-wrap: break-word;
            max-width: 300px;
        }}
        
        th {{
            background-color: {table_header_bg};
            font-weight: 600;
            border-bottom: 2px solid {border_color};
        }}
        
        tr:nth-child(even) {{
            background-color: {table_alt_bg};
        }}
        
        a {{
            color: {link_color};
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            margin: 8px 0;
        }}
        
        hr {{
            border: none;
            border-top: 1px solid {border_color};
            margin: 16px 0;
        }}
        
        /* 코드 하이라이트 스타일 */
        {pygments_css}
        
        /* 커스텀 코드 블록 스타일 */
        .highlight {{
            background-color: rgba(46, 52, 54, 0.05) !important;
            border-radius: 6px;
            padding: 12px !important;
            margin: 12px 0;
            overflow-x: auto;
        }}
        
        @media (prefers-color-scheme: dark) {{
            .highlight {{
                background-color: rgba(46, 52, 54, 0.8) !important;
            }}
        }}
        
        /* 스크롤바 스타일링 */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: transparent;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: rgba(136, 138, 133, 0.5);
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: rgba(136, 138, 133, 0.7);
        }}
        </style>
        """
    
    def render_markdown(self, content):
        """마크다운 콘텐츠를 HTML로 변환하여 렌더링"""
        if not content or not content.strip():
            if self.webview:
                self.webview.load_html("<html><body></body></html>", None)
            elif hasattr(self, 'fallback_label'):
                self.fallback_label.set_text("")
            return
        
        # 현재 콘텐츠 저장 (높이 계산용)
        self.current_content = content
        
        # WebView가 없으면 폴백 Label 사용
        if not self.webview:
            if hasattr(self, 'fallback_label'):
                # 간단한 마크다운 to Pango 변환
                pango_text = self._markdown_to_pango(content)
                self.fallback_label.set_markup(pango_text)
            return
        
        try:
            # 마크다운을 HTML로 변환 (수동 처리)
            # 1. 코드블록을 HTML로 변환
            processed_content = self._process_code_blocks_to_html(content)
            # 2. 테이블을 HTML로 변환
            processed_content = self._process_markdown_tables_to_html(processed_content)
            
            # 3. 기본 마크다운 변환
            md = markdown.Markdown()
            html_content = md.convert(processed_content)
            
            # 완성된 HTML 문서 생성
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                {self.css_style}
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            # WebView에 로드
            self.webview.load_html(full_html, None)
            
        except Exception as e:
            # 오류 발생 시 플레인 텍스트로 표시
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                {self.css_style}
            </head>
            <body>
                <p style="color: #cc0000;">Markdown rendering error:</p>
                <pre>{str(e)}</pre>
                <hr>
                <h4>Original content:</h4>
                <pre>{content}</pre>
            </body>
            </html>
            """
            self.webview.load_html(error_html, None)
    
    def _markdown_to_pango(self, content):
        """간단한 마크다운을 Pango 마크업으로 변환"""
        # HTML 엔티티 이스케이프
        content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # 기본적인 마크다운 변환
        content = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', content)  # 볼드
        content = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', content)      # 이탤릭
        content = re.sub(r'`([^`]+)`', r'<tt>\1</tt>', content)      # 인라인 코드
        content = re.sub(r'^# (.+)$', r'<big><b>\1</b></big>', content, flags=re.MULTILINE)  # H1
        content = re.sub(r'^## (.+)$', r'<big>\1</big>', content, flags=re.MULTILINE)        # H2
        
        # 테이블은 단순 텍스트로 표시
        lines = content.split('\n')
        processed_lines = []
        for line in lines:
            if '|' in line and line.strip().startswith('|') and line.strip().endswith('|'):
                # 테이블 행을 단순 텍스트로 변환
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                processed_lines.append(' | '.join(cells))
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _process_code_blocks_to_html(self, content):
        """마크다운 코드블록을 HTML로 수동 변환"""
        lines = content.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 코드블록 시작인지 확인 (```)
            if line.strip().startswith('```'):
                # 언어 정보 추출
                language = line.strip()[3:].strip() if len(line.strip()) > 3 else ""
                
                # 코드블록 내용 수집
                i += 1
                code_lines = []
                
                # 코드블록 끝까지 수집
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                
                # 코드블록 HTML로 변환
                code_content = '\n'.join(code_lines)
                # HTML 특수문자 이스케이프
                code_content = code_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                if language:
                    html_code = f'<pre><code class="language-{language}">{code_content}</code></pre>'
                else:
                    html_code = f'<pre><code>{code_content}</code></pre>'
                
                result_lines.append(html_code)
            else:
                result_lines.append(line)
            
            i += 1
        
        return '\n'.join(result_lines)
    
    def _process_markdown_tables_to_html(self, content):
        """마크다운 테이블을 HTML로 수동 변환"""
        lines = content.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 테이블 행인지 확인 (|로 시작하고 끝남)
            if line.startswith('|') and line.endswith('|') and line.count('|') >= 3:
                # 테이블 시작
                table_lines = []
                
                # 테이블 행들 수집
                while i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                    table_lines.append(lines[i].strip())
                    i += 1
                i -= 1  # 루프에서 1 증가하므로 보정
                
                # 테이블 HTML로 변환
                if len(table_lines) >= 1:  # 최소 1행 필요
                    html_table = self._convert_markdown_table_to_html(table_lines)
                    result_lines.append(html_table)
                else:
                    # 테이블이 아니면 원본 추가
                    result_lines.extend(table_lines)
            else:
                result_lines.append(lines[i])
            
            i += 1
        
        return '\n'.join(result_lines)
    
    def _convert_markdown_table_to_html(self, table_lines):
        """마크다운 테이블 행들을 HTML 테이블로 변환"""
        if len(table_lines) < 1:
            return '\n'.join(table_lines)
        
        # 첫 번째 행이 헤더인지 확인
        has_header = False
        header_line = ""
        separator_line = ""
        data_lines = table_lines
        
        if len(table_lines) >= 2:
            potential_separator = table_lines[1]
            # 구분자 행인지 확인 (-, :, | 만 포함)
            if all(c in '-:|' for c in potential_separator.replace(' ', '')):
                has_header = True
                header_line = table_lines[0]
                separator_line = table_lines[1]
                data_lines = table_lines[2:]
        
        # HTML 생성
        html = ["<table>"]
        
        # 헤더 처리
        if has_header and header_line:
            headers = [cell.strip() for cell in header_line.split('|')[1:-1]]  # 양쪽 끝 | 제거
            html.append("<thead><tr>")
            for header in headers:
                html.append(f"<th>{header}</th>")
            html.append("</tr></thead>")
        
        # 데이터 행 처리
        if data_lines:
            html.append("<tbody>")
            for line in data_lines:
                if line.strip():  # 빈 줄 건너뛰기
                    cells = [cell.strip() for cell in line.split('|')[1:-1]]  # 양쪽 끝 | 제거
                    html.append("<tr>")
                    for cell in cells:
                        html.append(f"<td>{cell}</td>")
                    html.append("</tr>")
            html.append("</tbody>")
        
        html.append("</table>")
        
        return ''.join(html)
    
    def _on_load_changed(self, webview, load_event):
        """WebView 로드 완료 시 내용에 따른 높이 조정"""
        if load_event == WEBKIT_MODULE.LoadEvent.FINISHED:
            try:
                if hasattr(self, 'current_content') and self.current_content:
                    content = self.current_content
                    
                    # 간단한 높이 추정
                    lines = content.count('\n')
                    
                    # 테이블과 코드블록 감지
                    has_table = '|' in content and content.count('|') >= 6  # 테이블이 있는지 간단 체크
                    has_code = '```' in content
                    
                    # 기본 높이 계산
                    if has_table or has_code or lines > 10:
                        # 복잡한 콘텐츠는 더 큰 높이
                        estimated_height = max(400, lines * 25 + 100)
                    elif lines > 5:
                        # 중간 길이 콘텐츠
                        estimated_height = max(300, lines * 22 + 80)
                    else:
                        # 짧은 콘텐츠
                        estimated_height = max(150, lines * 20 + 60)
                    
                    # 최대 높이 제한
                    estimated_height = min(estimated_height, 800)
                    
                    self.webview.set_size_request(-1, estimated_height)
                    pass  # Height adjusted
                else:
                    # 콘텐츠가 없으면 기본 높이
                    self.webview.set_size_request(-1, 300)
                    pass  # Default height set
                    
            except Exception:
                # 실패시 기본 높이
                self.webview.set_size_request(-1, 300)
    
    def set_content_height(self, height):
        """콘텐츠 최소 높이 설정"""
        scrolled = self.get_first_child()
        if scrolled and hasattr(scrolled, 'set_min_content_height'):
            scrolled.set_min_content_height(height)
    
    def get_webview(self):
        """WebView 위젯 반환"""
        return self.webview