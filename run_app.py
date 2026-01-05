import streamlit.web.cli as stcli
import os, sys

def resolve_path(path):
    # 判斷是否為 PyInstaller 封裝後的環境
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, path)
    return os.path.abspath(os.path.join(os.getcwd(), path))

if __name__ == "__main__":
    # 指向你的主程式檔名
    target_file = resolve_path("app.py") 
    
    sys.argv = [
        "streamlit",
        "run",
        target_file,
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())