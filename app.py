import streamlit as st
import ollama
import pdfplumber
import json
import os
import re
import time
import io
import pandas as pd
from datetime import datetime

# --- 設定與初始化 ---
SAVE_DIR = "projects"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

st.set_page_config(page_title="AI 文獻分級工作站 Pro v3.9.7", page_icon="📝", layout="wide")

# CSS 樣式優化
st.markdown("""
    <style>
    /* 右上角系統時間樣式 */
    .system-time-container {
        position: fixed;
        top: 3.5rem;
        right: 1.5rem;
        background-color: rgba(255, 255, 255, 0.9);
        padding: 6px 16px;
        border-radius: 20px;
        border: 1px solid #d1d5db;
        z-index: 999999;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        color: #1f2937;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        font-weight: bold;
    }
    
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    
    /* 強制按鈕文字不換行 */
    .stButton > button { 
        padding: 2px 10px; 
        font-size: 0.85rem; 
        white-space: nowrap; /* 確保文字在同一行 */
    }
    
    /* 修正 Toggle 標籤同一行 */
    .stWidget label {
        white-space: nowrap !important;
    }

    .doc-meta { 
        font-size: 1.05rem !important; 
        font-weight: 500;
        color: #1E1E1E; 
        background-color: #f0f2f6;
        padding: 10px 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 5px solid #007bff;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; }
    .stProgress > div > div > div > div { background-color: #007bff; }
    .instant-report {
        padding: 15px;
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        background-color: #ffffff;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .time-tag {
        font-size: 0.8rem;
        color: #6c757d;
        font-family: monospace;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 顯示動態時間 ---
time_placeholder = st.empty()
current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
time_placeholder.markdown(f'<div class="system-time-container">⏳ 系統時間：{current_time_str}</div>', unsafe_allow_html=True)

# --- 輔助函式庫 ---
def clean_author_info(author_data):
    if not author_data: return "未知"
    if isinstance(author_data, list):
        items = [clean_author_info(i) for i in author_data]
        return ", ".join(items)
    if isinstance(author_data, dict):
        return author_data.get('name', str(author_data))
    return str(author_data)

def ensure_str(val):
    if val is None: return "無資料"
    if isinstance(val, list):
        cleaned_list = [str(i).strip().strip("'").strip('"') for i in val if i]
        return "\n".join([f"• {item}" for item in cleaned_list]) if cleaned_list else "無資料"
    if isinstance(val, dict):
        cleaned_vals = [ensure_str(v) for v in val.values()]
        return "\n".join(cleaned_vals)
    s = str(val).strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        s = s[1:-1].strip()
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        try:
            import ast
            parsed = ast.literal_eval(s)
            if isinstance(parsed, dict):
                return "\n".join([f"• {v}" if isinstance(v, str) else ensure_str(v) for v in parsed.values()])
            if isinstance(parsed, list):
                return ensure_str(parsed)
        except:
            s = re.sub(r"['\"]?\w+['\"]?\s*:\s*", "", s) 
            s = s.strip("{}[]").replace("'", "").replace('"', "").strip()
    return s

def save_project_data(name, data):
    data["last_accessed"] = time.time()
    with open(os.path.join(SAVE_DIR, f"{name}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_project_data(name):
    path = os.path.join(SAVE_DIR, f"{name}.json")
    default_data = {"messages": [], "documents": {}, "last_accessed": time.time()}
    if not os.path.exists(path): return default_data
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "documents" not in data: data["documents"] = {}
            if "messages" not in data: data["messages"] = []
            return data
    except: return default_data

def ask_ai_json(content, model):
    system_prompt = """你是一個專業的研究助理。請分析文獻內容並嚴格按照 JSON 格式回答。
    你必須提取並總結出以下『五個主題』，每個欄位必須是『單一純文字字串』：
    1. topic: 研究主題
    2. goals: 研究目標
    3. method: 研究方法
    4. findings: 摘要與發現
    5. limitations: 侷限性與建議
    - author: 作者姓名
    - year: 出版年份
    語系：繁體中文。"""
    user_prompt = f"分析以下文獻內容，直接輸出 JSON 物件：\n\n{content[:10000]}"
    try:
        response = ollama.chat(model=model, messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ])
        raw_content = response['message']['content']
        clean_json = re.sub(r'```json|```', '', raw_content).strip()
        json_match = re.search(r'\{.*\}', clean_json, re.DOTALL)
        if json_match:
            res = json.loads(json_match.group())
            return {k: ensure_str(v) for k, v in res.items()}
        return None
    except: return None

# --- 初始化 Session State ---
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = "請選擇"

# --- 側邊欄 ---
with st.sidebar:
    st.title("🚀 系統控制台")
    selected_model = st.selectbox("核心模型", ["llama3:8b-instruct-q4_0", "llava", "phi3"], index=0)
    st.divider()
    
    project_files = []
    for f in os.listdir(SAVE_DIR):
        if f.endswith(".json"):
            name = f.replace(".json", "")
            data = load_project_data(name)
            project_files.append({"name": name, "last_accessed": data.get("last_accessed", 0)})
    
    project_files.sort(key=lambda x: x['last_accessed'], reverse=True)
    recent_names = [p['name'] for p in project_files]

    if recent_names:
        st.subheader("🕒 最近使用的專案")
        for i, proj_name in enumerate(recent_names[:3]):
            if st.button(f"📁 {proj_name}", key=f"recent_{i}", use_container_width=True):
                st.session_state.selected_project = proj_name
                st.rerun()
    st.divider()

    selected = st.selectbox("選擇專案", ["請選擇"] + recent_names, index=0 if st.session_state.selected_project == "請選擇" else recent_names.index(st.session_state.selected_project)+1 if st.session_state.selected_project in recent_names else 0)
    if selected != st.session_state.selected_project:
        st.session_state.selected_project = selected
        st.rerun()

    # --- 刪除專案功能 (雙重確認) ---
    if st.session_state.selected_project != "請選擇":
        with st.popover("🗑️ 刪除目前專案", use_container_width=True):
            st.warning(f"確定要永久刪除專案「{st.session_state.selected_project}」嗎？這將無法復原。")
            if st.button("🔥 確定刪除", use_container_width=True, type="primary"):
                file_path = os.path.join(SAVE_DIR, f"{st.session_state.selected_project}.json")
                if os.path.exists(file_path):
                    os.remove(file_path)
                    st.session_state.selected_project = "請選擇"
                    st.success("專案已刪除")
                    time.sleep(1)
                    st.rerun()

    st.divider()
    new_p_name = st.text_input("✨ 建立新專案")
    if st.button("確認新增", use_container_width=True) and new_p_name:
        save_project_data(new_p_name, {"messages": [], "documents": {}, "last_accessed": time.time()})
        st.session_state.selected_project = new_p_name
        st.rerun()

# --- 主畫面 ---
current_p = st.session_state.selected_project
if current_p != "請選擇":
    project_data = load_project_data(current_p)
    st.header(f"🗃️ 專案：{current_p}")
    docs = project_data.get("documents", {})

    tab_manage, tab_matrix, tab_chat = st.tabs(["📂 自動整理文獻", "📊 比較矩陣", "💬 深度對話"])

    with tab_manage:
        uploaded_files = st.file_uploader("📥 批次上傳文獻", type=['pdf', 'txt'], accept_multiple_files=True)
        
        if uploaded_files:
            files_to_process = [f for f in uploaded_files if f.name not in docs]
            if files_to_process:
                st.markdown("### ⚡ AI 即時分析進度")
                pb = st.progress(0)
                status_text = st.empty()
                live_output = st.container() 
                for idx, f in enumerate(files_to_process):
                    start_time = time.time()
                    status_text.text(f"正在處理: {f.name}...")
                    content = ""
                    if f.name.endswith(".pdf"):
                        try:
                            with pdfplumber.open(io.BytesIO(f.read())) as pdf:
                                content = "\n".join([p.extract_text() for p in pdf.pages[:10] if p.extract_text()])
                        except: st.error(f"讀取失敗: {f.name}")
                    else:
                        content = f.read().decode("utf-8")
                    if content:
                        meta = ask_ai_json(content, selected_model)
                        process_duration = round(time.time() - start_time, 2)
                        doc_entry = {
                            "content": content,
                            "metadata": {
                                "title": f.name,
                                "author": meta.get('author', '未知') if meta else '未知',
                                "year": meta.get('year', '未知') if meta else '未知',
                                "timestamp": time.time(),
                                "duration": process_duration
                            },
                            "full_report": meta if meta else {}
                        }
                        project_data["documents"][f.name] = doc_entry
                        save_project_data(current_p, project_data)
                        with live_output:
                            st.markdown(f"""
                            <div class="instant-report">
                                <div style="display: flex; justify-content: space-between;">
                                    <h4 style="color:#007bff; margin:0;">✅ 已完成：{f.name}</h4>
                                    <span class="time-tag">⏱️ 耗時: {process_duration}s</span>
                                </div>
                                <hr style="margin:10px 0;">
                                <b>📌 研究發現摘要：</b><br>{ensure_str(meta.get('findings'))[:300]}...
                            </div>
                            """, unsafe_allow_html=True)
                    pb.progress((idx + 1) / len(files_to_process))
                st.success("🎉 所有檔案處理完畢！")
                time.sleep(1)
                st.rerun()

        st.divider()
        
        sorted_docs = sorted(docs.items(), key=lambda x: x[1].get("metadata", {}).get("timestamp", 0), reverse=True)
        
        if not sorted_docs:
            st.warning("目前暫無文獻，請從上方上傳檔案以啟動 AI 自動整理。")
        else:
            search_query = st.text_input("🔍 關鍵字搜尋...", key="search_bar").lower()
            for doc_id, info in sorted_docs:
                m = info.get("metadata", {})
                r = info.get("full_report") or {}
                if search_query and search_query not in doc_id.lower() and search_query not in str(r).lower():
                    continue

                doc_date = datetime.fromtimestamp(m.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M')
                
                with st.expander(f"📄 {m.get('title', doc_id)} - {doc_date} (⏱️{m.get('duration', '?')}s)"):
                    c_edit, c_del, c_space = st.columns([1.5, 1.5, 7])
                    with c_edit:
                        is_editing = st.toggle("📝 編輯", key=f"edit_toggle_{doc_id}")
                    with c_del:
                        if st.button("🗑️ 刪除", key=f"del_{doc_id}", use_container_width=True):
                            del project_data["documents"][doc_id]
                            save_project_data(current_p, project_data)
                            st.rerun()

                    if is_editing:
                        new_author = st.text_input("👤 作者", value=m.get('author', '未知'), key=f"in_auth_{doc_id}")
                        new_year = st.text_input("📅 年份", value=m.get('year', '未知'), key=f"in_year_{doc_id}")
                        col1, col2 = st.columns(2)
                        with col1:
                            new_topic = st.text_area("📚 研究主題", value=r.get('topic', ''), key=f"in_topic_{doc_id}")
                            new_goals = st.text_area("🎯 研究目標", value=r.get('goals', ''), key=f"in_goals_{doc_id}")
                        with col2:
                            new_method = st.text_area("🧪 研究方法", value=r.get('method', ''), key=f"in_method_{doc_id}")
                            new_limit = st.text_area("⚠️ 侷限性與建議", value=r.get('limitations', ''), key=f"in_limit_{doc_id}")
                        new_findings = st.text_area("💡 摘要與發現", value=r.get('findings', ''), key=f"in_find_{doc_id}")
                        
                        if st.button("💾 儲存修改", key=f"save_edit_{doc_id}", type="primary"):
                            project_data["documents"][doc_id]["metadata"]["author"] = new_author
                            project_data["documents"][doc_id]["metadata"]["year"] = new_year
                            project_data["documents"][doc_id]["full_report"] = {
                                "topic": new_topic, "goals": new_goals, "method": new_method,
                                "findings": new_findings, "limitations": new_limit,
                                "author": new_author, "year": new_year
                            }
                            save_project_data(current_p, project_data)
                            st.success("更新成功！")
                            time.sleep(0.5)
                            st.rerun()
                    else:
                        st.markdown(f"<div class='doc-meta'>👤 作者：{clean_author_info(m.get('author'))} | 年份：{m.get('year','未知')}</div>", unsafe_allow_html=True)
                        col1, col2 = st.columns(2)
                        with col1:
                            st.info(f"**📚 研究主題**\n\n{ensure_str(r.get('topic'))}")
                            st.info(f"**🎯 研究目標**\n\n{ensure_str(r.get('goals'))}")
                        with col2:
                            st.warning(f"**🧪 研究方法**\n\n{ensure_str(r.get('method'))}")
                            st.error(f"**⚠️ 侷限性與建議**\n\n{ensure_str(r.get('limitations'))}")
                        st.success(f"**💡 摘要與發現**\n\n{ensure_str(r.get('findings'))}")

    with tab_matrix:
        st.subheader("📊 關鍵指標對照矩陣")
        if docs:
            matrix_list = []
            for d in docs.values():
                fr = d.get("full_report", {})
                matrix_list.append({
                    "文獻標題": d['metadata'].get("title"),
                    "研究主題": ensure_str(fr.get("topic")),
                    "研究方法": ensure_str(fr.get("method")),
                    "摘要發現": ensure_str(fr.get("findings")),
                    "侷限建議": ensure_str(fr.get("limitations")),
                    "作者": clean_author_info(d['metadata'].get("author")),
                    "年份": d['metadata'].get("year")
                })
            df = pd.DataFrame(matrix_list)
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 下載矩陣 (CSV)", df.to_csv(index=False).encode('utf-8-sig'), f"{current_p}_matrix.csv", "text/csv")
        else: st.info("尚無數據。")

    with tab_chat:
        c1, c2 = st.columns([8, 2])
        with c1:
            st.subheader("💬 與 AI 深度對話")
        with c2:
            if st.button("🧹 清除對話歷史", use_container_width=True):
                project_data["messages"] = []
                save_project_data(current_p, project_data)
                st.rerun()
        
        for msg in project_data.get("messages", []):
            with st.chat_message(msg["role"]): st.write(msg["content"])
            
        if prompt := st.chat_input("詢問有關本專案文獻的細節..."):
            with st.chat_message("user"): st.write(prompt)
            knowledge = "\n".join([f"檔案:{k}\n內容重點:{str(v.get('full_report',''))}" for k, v in docs.items()])
            with st.chat_message("assistant"):
                res_box = st.empty(); full_res = ""
                for chunk in ollama.chat(model=selected_model, messages=[{'role': 'user', 'content': f"你是一個研究助理，根據文獻回答：\n{knowledge}\n問題：{prompt}"}], stream=True):
                    full_res += chunk['message']['content']; res_box.markdown(full_res + "▌")
                res_box.markdown(full_res)
            project_data["messages"].append({"role": "user", "content": prompt})
            project_data["messages"].append({"role": "assistant", "content": full_res})
            save_project_data(current_p, project_data)
else:
    st.info("💡 請從左側側邊欄選擇專案或建立新專案以開始工作。")