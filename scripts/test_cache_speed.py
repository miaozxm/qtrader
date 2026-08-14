"""验证缓存生效：连续点击按钮的耗时"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from streamlit.testing.v1 import AppTest


def main():
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "app.py")
    at = AppTest.from_file(app_path, default_timeout=90)

    # 首次渲染（冷启动，含网络）
    t0 = time.time()
    at.run()
    t1 = time.time() - t0
    print(f"首次渲染: {t1:.1f}s")

    # 连续 rerun（点击回测按钮，应命中缓存）
    times = []
    for b in at.button:
        if "运行回测" in b.label:
            for _ in range(3):
                t0 = time.time()
                b.click()
                at.run()
                times.append(time.time() - t0)
            break

    if times:
        print(f"回测按钮连续点击耗时: {[f'{t:.1f}s' for t in times]}")
        print(f"平均: {sum(times)/len(times):.1f}s")


if __name__ == "__main__":
    main()
