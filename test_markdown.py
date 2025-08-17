#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, GLib
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, 'src')

try:
    from widgets.markdown_renderer import MarkdownRenderer
except ImportError as e:
    print(f"Import 실패: {e}")
    print("Import를 수정하여 다시 시도합니다...")
    try:
        # markdown_renderer.py를 직접 불러오기
        import importlib.util
        spec = importlib.util.spec_from_file_location("markdown_renderer", "src/widgets/markdown_renderer.py")
        markdown_renderer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(markdown_renderer_module)
        MarkdownRenderer = markdown_renderer_module.MarkdownRenderer
    except Exception as e2:
        print(f"대체 방법도 실패: {e2}")
        sys.exit(1)

class TestApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='test.markdown.renderer')
        
    def do_activate(self):
        # 메인 윈도우 생성
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title("마크다운 렌더링 테스트")
        self.window.set_default_size(800, 600)
        
        # 메인 박스
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        main_box.set_margin_start(10)
        main_box.set_margin_end(10)
        
        # 제목
        title = Gtk.Label()
        title.set_markup("<b>마크다운 렌더링 테스트</b>")
        main_box.append(title)
        
        # 테스트 마크다운 콘텐츠
        test_content = """
# 마크다운 렌더링 테스트

이것은 **마크다운 렌더링** 테스트입니다.

## 기능 테스트

### 텍스트 스타일링
- **볼드 텍스트**
- *이탤릭 텍스트*
- `인라인 코드`

### 코드 블록
```python
def hello_world():
    print("Hello, World!")
    return "success"

# 이것은 Python 코드입니다
for i in range(5):
    print(f"숫자: {i}")
```

### 리스트
1. 첫 번째 아이템
2. 두 번째 아이템
3. 세 번째 아이템

- 언순서 리스트
- 또 다른 아이템
  - 중첩된 아이템
  - 또 다른 중첩 아이템

### 테이블
| 컬럼 1 | 컬럼 2 | 컬럼 3 |
|--------|--------|--------|
| 데이터1 | 데이터2 | 데이터3 |
| 값 A   | 값 B   | 값 C   |

### 링크와 인용문
[GitHub 링크](https://github.com)

> 이것은 인용문입니다.
> 여러 줄로 된 인용문도 가능합니다.

### 수평선
---

마크다운 렌더링이 제대로 작동하면 위의 모든 요소들이 올바르게 표시됩니다.
        """
        
        try:
            # 마크다운 렌더러 생성
            markdown_renderer = MarkdownRenderer()
            markdown_renderer.set_vexpand(True)
            markdown_renderer.set_hexpand(True)
            
            # 마크다운 렌더링
            markdown_renderer.render_markdown(test_content)
            
            main_box.append(markdown_renderer)
            
            print("✓ 마크다운 렌더러 생성 및 렌더링 성공")
            
        except Exception as e:
            print(f"✗ 마크다운 렌더러 오류: {e}")
            import traceback
            traceback.print_exc()
            
            # 오류 메시지 표시
            error_label = Gtk.Label()
            error_label.set_markup(f"<span color='red'>마크다운 렌더링 오류:\n{str(e)}</span>")
            main_box.append(error_label)
        
        self.window.set_child(main_box)
        self.window.present()

def main():
    print("마크다운 렌더링 테스트 시작...")
    
    # GTK 애플리케이션 실행
    app = TestApp()
    app.run(sys.argv)

if __name__ == '__main__':
    main()