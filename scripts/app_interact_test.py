"""交互测试：通过 AppTest 点击查询 + 运行回测，验证完整交互链路"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from streamlit.testing.v1 import AppTest


def main():
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "app.py")
    at = AppTest.from_file(app_path, default_timeout=90)
    at.run()

    # 默认 A股 600519，输入港股代码并查询
    at.text_input[0].set_value("00700")
    at.run()
    # 点击查询按钮（第一个 button）
    at.button[0].click()
    at.run()

    print("=== 查询港股 00700 后 ===")
    print("异常:", [e.value for e in at.exception] or "无")
    # 收集 metric 组件信息
    print("metric 数量:", len(at.metric))
    for m in at.metric[:6]:
        print("  metric:", m.label, "=", m.value)

    # 点击运行回测按钮（第二个 button）
    if len(at.button) > 1:
        at.button[1].click()
        at.run()
        print("\n=== 运行回测后 ===")
        print("异常:", [e.value for e in at.exception] or "无")
        print("metric 数量:", len(at.metric))
        for m in at.metric:
            print("  metric:", m.label, "=", m.value)
        # dataframe（交易明细）
        print("dataframe 数量:", len(at.dataframe))


if __name__ == "__main__":
    main()
