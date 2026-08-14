"""诊断 AppTest 运行时的 Python 环境"""
import os
import sys
import importlib.util

from streamlit.testing.v1 import AppTest


def main():
    print("当前进程 executable:", sys.executable)
    print("当前进程 version:", sys.version)
    print("user site:", __import__("site").getusersitepackages())
    print("sys.path:")
    for p in sys.path:
        if "site-packages" in p:
            print("  ", p)

    for mod in ("plotly", "streamlit", "pandas"):
        spec = importlib.util.find_spec(mod)
        print(f"find_spec({mod}):", spec.origin if spec else "NOT FOUND")

    # 直接跑 AppTest
    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "app", "app.py")
    print("app_path:", app_path)
    at = AppTest.from_file(app_path, default_timeout=60)
    at.run()
    if at.exception:
        print("App 渲染异常:")
        for e in at.exception:
            print("  ", e.value)
    else:
        print("App 渲染成功")


if __name__ == "__main__":
    main()
