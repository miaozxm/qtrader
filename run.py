"""一键启动量化平台"""
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path


def main():
    # 让 stdout 使用 UTF-8，配合 bat 里的 chcp 65001，避免中文乱码
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    root = Path(__file__).resolve().parent
    app_path = root / "app" / "app.py"
    # 优先使用项目虚拟环境，保证依赖自包含
    venv_py = root / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        py = str(venv_py)
    else:
        py = sys.executable
    cmd = [
        py, "-m", "streamlit", "run", str(app_path),
        "--server.headless", "true",        # 禁用 Email 等交互式订阅提示
        "--server.port", "8501",
        "--browser.gatherUsageStats", "false",
    ]

    url = "http://localhost:8501"
    print("正在启动 QTrader 平台...")
    print(f"浏览器将自动打开 {url}")

    # 后台线程延迟打开浏览器（等 streamlit 就绪）
    def _open_browser():
        time.sleep(3)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open_browser, daemon=True).start()

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        # 实时输出，方便看到启动日志
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                print(line, end="")
    except KeyboardInterrupt:
        print("\n已停止 QTrader 平台")


if __name__ == "__main__":
    main()
