"""组合监控页签交互测试"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from streamlit.testing.v1 import AppTest


def main():
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "app.py")
    at = AppTest.from_file(app_path, default_timeout=120)
    at.run()

    # 切到组合监控 tab（第三个）
    try:
        at.tabs[2].click()
        at.run()
    except Exception as e:
        print("切换 tab 异常:", e)

    # 添加自选
    at.text_input[1].set_value("600519")
    at.run()
    # 点击"添加"按钮
    add_btn = None
    for b in at.button:
        if "添加" in b.label:
            add_btn = b
            break
    if add_btn:
        add_btn.click()
        at.run()
        print("添加自选后异常:", [e.value for e in at.exception] or "无")

    # 点击"计算组合净值"
    calc_btn = None
    for b in at.button:
        if "计算组合净值" in b.label:
            calc_btn = b
            break
    if calc_btn:
        calc_btn.click()
        at.run()
        print("计算组合后异常:", [e.value for e in at.exception] or "无")
        print("metric 数量:", len(at.metric))
        for m in at.metric[-3:]:
            print("  ", m.label, "=", m.value)


if __name__ == "__main__":
    main()
