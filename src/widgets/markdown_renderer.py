# GTK 버전은 main.py에서 이미 설정되었으므로 여기서는 설정하지 않음
from gi.repository import Gtk, GLib, Gio
import markdown
import re
import os

# WebKit2는 선택적으로 import (없어도 기본 기능 동작)
try:
    from gi.repository import WebKit2
    WEBKIT_AVAILABLE = True
except ImportError:
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
                # WebView 설정
                self.webview = WebKit2.WebView()
                self.webview.set_hexpand(True)
                self.webview.set_vexpand(True)
                
                # 웹 설정
                settings = self.webview.get_settings()
                settings.set_enable_javascript(False)
                settings.set_enable_plugins(False)
                settings.set_enable_java(False)
                settings.set_enable_page_cache(False)
                settings.set_enable_offline_web_application_cache(False)
                settings.set_enable_html5_database(False)
                settings.set_enable_html5_local_storage(False)
                settings.set_hardware_acceleration_policy(WebKit2.HardwareAccelerationPolicy.NEVER)
                
                # 스크롤 가능한 컨테이너
                scrolled = Gtk.ScrolledWindow()
                scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
                scrolled.set_child(self.webview)
                scrolled.set_min_content_height(100)
                
                self.append(scrolled)
            except Exception as e:
                print(f"WebKit 초기화 실패: {e}")
                self.webview = None
        
        # WebKit를 사용할 수 없으면 폴백 표시
        if self.webview is None:
            label = Gtk.Label()
            label.set_text("WebKit를 사용할 수 없어 마크다운 렌더링이 제한됩니다.")
            label.set_wrap(True)
            self.append(label)
        
        # 마크다운 확장 설정 (안전한 방식)
        self.markdown_extensions = []
        
        # 사용 가능한 확장들을 하나씩 확인하여 추가
        available_extensions = ['tables', 'fenced_code', 'nl2br', 'sane_lists']
        for ext in available_extensions:
            try:
                # 테스트해보고 문제없으면 추가
                test_md = markdown.Markdown(extensions=[ext])
                self.markdown_extensions.append(ext)
            except Exception:
                # 해당 확장을 사용할 수 없으면 건너뜀
                pass
        
        # 코드 하이라이트 설정
        self.codehilite_config = {}
        
        # CSS 스타일 생성
        self.css_style = self._generate_css()
        
    def _generate_css(self):
        """GTK 테마에 맞는 CSS 스타일 생성"""
        
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
            color: #2e3436;
            background-color: transparent;
            margin: 0;
            padding: 12px;
            word-wrap: break-word;
        }}
        
        @media (prefers-color-scheme: dark) {{
            body {{
                color: #eeeeec;
                background-color: transparent;
            }}
            
            blockquote {{
                border-left-color: #555753;
                background-color: rgba(85, 87, 83, 0.1);
            }}
            
            code {{
                background-color: rgba(85, 87, 83, 0.2);
                color: #eeeeec;
            }}
            
            pre {{
                background-color: rgba(46, 52, 54, 0.8);
                border-color: #555753;
            }}
            
            table {{
                border-color: #555753;
            }}
            
            th, td {{
                border-color: #555753;
            }}
            
            th {{
                background-color: rgba(85, 87, 83, 0.2);
            }}
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
            border-left: 4px solid #729fcf;
            background-color: rgba(114, 159, 207, 0.1);
            font-style: italic;
        }}
        
        code {{
            background-color: rgba(114, 159, 207, 0.2);
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Source Code Pro', 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
        }}
        
        pre {{
            background-color: rgba(46, 52, 54, 0.05);
            border: 1px solid #d3d7cf;
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
            border: 1px solid #d3d7cf;
        }}
        
        th, td {{
            border: 1px solid #d3d7cf;
            padding: 8px 12px;
            text-align: left;
        }}
        
        th {{
            background-color: rgba(114, 159, 207, 0.1);
            font-weight: 600;
        }}
        
        a {{
            color: #204a87;
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
            border-top: 1px solid #d3d7cf;
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
            return
        
        # WebView가 없으면 아무것도 하지 않음
        if not self.webview:
            return
        
        try:
            # 마크다운을 HTML로 변환 (안전한 방식)
            try:
                md = markdown.Markdown(extensions=self.markdown_extensions)
            except Exception:
                # 확장 없이 기본 마크다운 사용
                md = markdown.Markdown()
            
            html_content = md.convert(content)
            
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
    
    def set_content_height(self, height):
        """콘텐츠 최소 높이 설정"""
        scrolled = self.get_first_child()
        if scrolled:
            scrolled.set_min_content_height(height)
    
    def get_webview(self):
        """WebView 위젯 반환"""
        return self.webview