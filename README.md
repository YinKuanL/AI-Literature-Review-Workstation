# 📝 AI 文獻分級工作站 Pro (v3.9.7)

這是一個基於 Streamlit 開發的專業文獻分析工具，結合 Ollama 本地端大語言模型（LLM），旨在協助研究人員快速提取、分類並比較學術論文（PDF/TXT）中的核心資訊。

## ✨ 核心功能

* **🚀 AI 自動化整理**：批次上傳 PDF 或 TXT，自動提取研究主題、目標、方法、發現與侷限性。
* **📊 關鍵指標矩陣**：自動生成文獻對照表，支持一鍵匯出 CSV 格式。
* **💬 文獻深度對話**：基於全專案文獻內容進行 RAG 知識庫問答。
* **🗃️ 專案管理系統**：支持多專案切換、自動存檔、手動編輯與雙重確認刪除功能。
* **⏱️ 效能追蹤**：即時顯示系統時間與每篇文獻的 AI 處理耗時。

## 🛠️ 環境需求

本工具使用 **Ollama** 作為本地運算引擎，確保文獻隱私不外洩。

1.  **安裝 Ollama**: 請至 [Ollama 官網](https://ollama.com/) 下載並安裝。
2.  **下載模型**: 開啟終端機並執行以下指令：
    ```bash
    ollama pull llama3:8b-instruct-q4_0
    ```
    *(註：亦可於介面中切換 phi3 或 llava 模型)*

## 🚀 快速開始 (開發者模式)

1.  **複製儲存庫**:
    ```bash
    git clone [https://github.com/YinKuanL/AI-Literature-Review-Workstation.git](https://github.com/YinKuanL/AI-Literature-Review-Workstation.git)
    cd AI-Literature-Review-Workstation
    ```

2.  **安裝依賴套件**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **啟動應用程式**:
    ```bash
    streamlit run app.py
    ```

## 📦 下載執行檔 (.exe)

如果你不具備 Python 環境，可以直接前往 [Releases](https://github.com/YinKuanL/AI-Literature-Review-Workstation/releases) 頁面下載打包好的 `run_app.exe`。
*注意：下載後仍須安裝 Ollama 方可進行 AI 分析。*

## 📁 資料夾結構說明

* `app.py`: 主程式邏輯與 UI 介面。
* `projects/`: 存放專案 JSON 資料與對話紀錄（自動生成）。
* `requirements.txt`: 專案所需的 Python 套件清單。
* `run_app.py`: 用於 PyInstaller 打包的啟動腳本。

## ⚠️ 注意事項

* **PDF 解析**: 對於掃描形式的 PDF（圖片型），解析效果取決於 `pdfplumber` 的表現。
* **電腦效能**: 本地模型運算速度取決於您的 CPU/GPU 效能，建議配置 16GB 以上記憶體。

## ⚖️ 免責聲明
本工具生成的摘要僅供研究參考，AI 輸出可能存在幻覺，請務必親自核對原始文獻。

---
Created by [YinKuanL](https://github.com/YinKuanL)
