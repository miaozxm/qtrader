"""全面测试所有页签按钮的可点击性"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from streamlit.testing.v1 import AppTest


def main():
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "app.py")
    at = AppTest.from_file(app_path, default_timeout=90)
    at.run()
    print("首次渲染异常:", [e.value for e in at.exception] or "无")
    print("按钮列表:")
    for i, b in enumerate(at.button):
        print(f"  [{i}] label={b.label!r} key={b.key!r}")

    # 尝试逐个点击每个按钮，观察是否有异常
    for i, b in enumerate(at.button):
        try:
            b.click()
            at.run()
            exc = [e.value for e in at.exception]
            print(f"点击按钮[{i}] {b.label!r} -> 异常: {exc or '无'}")
        except Exception as e:
            print(f"点击按钮[{i}] {b.label!r} -> 触发异常: {e}")


if __name__ == "__main__":
    main()
