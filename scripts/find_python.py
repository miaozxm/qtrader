"""探测本机哪个 Python 环境能同时运行 streamlit + plotly"""
import importlib.util
import os
import subprocess
import sys


CANDIDATES = [
    os.environ.get("PYTHON") or "",
    sys.executable,
    r"C:\veighna_studio\python.exe",
    r"C:\Users\LiniKeair\miniconda3\python.exe",
    r"C:\Users\LiniKeair\anaconda3\python.exe",
    r"D:\Users\LiniKeair\anaconda3\python.exe",
    r"C:\Users\LiniKeair\AppData\Local\Programs\Python\Python311\python.exe",
    r"D:\Program Files\Python312\python.exe",
    "python",
    "python3",
]


def probe(py: str) -> tuple:
    """返回 (py, version, streamlit, plotly, pandas, error)"""
    code = (
        "import sys; "
        "print(sys.version.split()[0], end='|'); "
        "import importlib.util as u; "
        "def has(m):\n"
        "    try:\n"
        "        mod = __import__(m); print(m + ':' + getattr(mod, '__version__', '?'), end='|')\n"
        "    except Exception as e:\n"
        "        print(m + ':NO', end='|')\n"
        "has('streamlit'); has('plotly'); has('pandas'); has('numpy')"
    )
    try:
        r = subprocess.run(
            [py, "-c", code],
            capture_output=True, text=True, timeout=30,
        )
        return py, r.stdout.strip()
    except Exception as e:
        return py, f"ERR:{type(e).__name__}"


def main():
    seen = set()
    for py in CANDIDATES:
        if not py or py in seen:
            continue
        seen.add(py)
        py_path = py if os.path.isabs(py) else os.path.normpath(py)
        print(f"\n== {py_path} ==")
        try:
            # 规范化路径以便判断存在性
            exists = os.path.exists(py_path)
            if not exists and not os.path.isabs(py):
                # 尝试 which
                which = subprocess.run(["where", "python"], capture_output=True,
                                       text=True).stdout if os.name == "nt" else ""
                print(f"   (which) {which.strip()}")
                continue
            print(f"   存在: {exists}")
        except Exception:
            pass
        name, result = probe(py)
        print(f"   结果: {result}")


if __name__ == "__main__":
    main()
