"""搜索与热榜交互测试"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from streamlit.testing.v1 import AppTest


def main():
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "app.py")
    at = AppTest.from_file(app_path, default_timeout=90)
    at.run()

    # 在搜索框输入代码
    at.text_input[1].set_value("159915")
    at.run()
    # 点击搜索按钮
    for b in at.button:
        if b.label == "搜索":
            b.click()
            at.run()
            break

    print("搜索后异常:", [e.value for e in at.exception] or "无")
    print("metric 数量:", len(at.metric))
    for m in at.metric[:2]:
        print("  ", m.label, "=", m.value)


if __name__ == "__main__":
    main()
