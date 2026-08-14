"""用 Streamlit AppTest 验证 app 脚本可无异常渲染"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from streamlit.testing.v1 import AppTest


def main():
    app_path = Path(__file__).resolve().parent.parent / "app" / "app.py"
    at = AppTest.from_file(str(app_path), default_timeout=60)
    at.run()
    # 检查是否有异常
    if at.exception:
        print("!! App 渲染出现异常:")
        for e in at.exception:
            print("  ", e.value)
        sys.exit(1)

    print("App 脚本渲染成功（无异常）")
    print(f"  标题: {at.title[0].value}")
    print(f"  副标题: {at.caption[0].value}")
    print(f"  selectbox 数量: {len(at.selectbox)}")
    print(f"  text_input 数量: {len(at.text_input)}")
    print(f"  button 数量: {len(at.button)}")


if __name__ == "__main__":
    main()
