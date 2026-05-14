# streamlit run app.py
# -*- coding: utf-8 -*-
import streamlit as st
import configparser
import os
import math
import requests
from geopy.distance import geodesic

# ==========================================
# 1. 核心參數設定與版面常數
# ==========================================
st.set_page_config(page_title="Smart Light Navigation", layout="centered")

PAGE_SIZE     = 5
BTN_HEIGHT    = 50    
BTN_GAP       = 1     
FOOTER_HEIGHT = 150

def send_to_led(name, distance, angle):
    url = "http://10.12.4.100:8080/api/control"
    payload = {"data": {"target": name, "dist": f"{distance:.2f}km", "angle": f"{angle:.1f}°"}}
    try:
        requests.post(url, json=payload, timeout=2)
    except:
        pass

def load_config():
    all_locations, curr_pos, curr_name = [], (25.035, 121.567), "信義威秀"
    categories = ["全部"]
    config = configparser.ConfigParser()
    config.optionxform = str
    if os.path.exists('config.ini'):
        config.read('config.ini', encoding='utf-8')
        if 'Settings' in config:
            curr_pos = (
                config.getfloat('Settings', 'current_lat', fallback=25.035),
                config.getfloat('Settings', 'current_lon', fallback=121.567),
            )
            curr_name = config.get('Settings', 'current_location', fallback="信義威秀")
        if 'Locations' in config:
            for name in config['Locations']:
                try:
                    parts = [p.strip() for p in config['Locations'][name].split(',')]
                    cat = parts[2] if len(parts) > 2 else "未分類"
                    all_locations.append({
                        "name": name.upper(),
                        "coords": (float(parts[0]), float(parts[1])),
                        "category": cat
                    })
                    if cat not in categories:
                        categories.append(cat)
                except:
                    continue
    return curr_pos, curr_name, all_locations, categories

current_pos, current_name, all_locs, categories = load_config()

if "page"         not in st.session_state: st.session_state.page = 0
if "selected_loc" not in st.session_state: st.session_state.selected_loc = None

# ==========================================
# 2. 目錄與排版 CSS (詳細註解)
# ==========================================
st.markdown(f"""
<style>
/* 背景色設定 */
html, body, [data-testid="stAppViewContainer"] {{
    background-color: #0E1117 !important;
}}

/* 📱 主容器：控制 App 在手機螢幕上的安全區域 */
.block-container {{
    max-width: 500px !important;
    padding-left: 10px !important;   /* 左右兩側與手機邊緣距離 */
    padding-right: 10px !important;  
    padding-top: 60px !important;    /* 🛠️ 解決「太上面」問題：頂部下移 60px */
    padding-bottom: 20px !important; /* 底部緩衝 */
}}

/* 👻 隱藏所有官方介面殘留 */
header, footer, [data-testid="stHeader"], [data-testid="stToolbar"] {{
    display: none !important;
}}

/* ── 📂 目錄區塊 (Selectbox) ── */
[data-testid="stSelectbox"] {{
    margin-bottom: 1px !important; /* 目錄與下方標題框的間距 */
}}

/* 🚫 禁用輸入功能：讓 Input 變成透明且不可點擊，防止手機彈出鍵盤 */
[data-testid="stSelectbox"] input {{
    pointer-events: none !important;
    caret-color: transparent !important;
    color: transparent !important; /* 隱藏輸入游標 */
}}

/* 🛠️ 模擬點擊感：讓整個目錄區塊像是一個大按鈕 */
[data-testid="stSelectbox"] > div[role="button"] {{
    cursor: pointer !important;
    -webkit-tap-highlight-color: transparent !important;
}}

/* ── 🏷️ 頂部標題框 ── */
.nav-header {{
    background: white; 
    border-radius: 10px;
    display: flex; 
    flex-direction: column;
    align-items: center; 
    justify-content: center;
    margin-bottom: 10px;   /* 標題框與下方按鈕的間距 */
    padding: 12px 5px;    /* 標題框內部的上下留白 */
}}
.nav-header h1 {{ font-size: 40px; color: black; margin: 0; font-weight: 900; }}
.nav-header p  {{ font-size: 20px; color: gray; margin-top: 4px; font-family: monospace; }}

/* ── 🔘 地點按鈕區 ── */
[data-slot="nav-btn"] {{
    height: {BTN_HEIGHT}px !important;
    margin: 0 !important;
    border-bottom: {BTN_GAP}px solid #0E1117 !important; /* 按鈕間的 1px 黑色分隔線 */
}}
[data-slot="nav-btn"] > button {{
    height: {BTN_HEIGHT}px !important;
    background: #1E2329 !important;
    border: 1px solid #3E454D !important;
    color: white !important;
    font-size: 20px !important;
    font-weight: 700 !important;
    border-radius: 0 !important;
    width: 100% !important;
    -webkit-tap-highlight-color: transparent !important;
}}
/* 圓角處理：僅最上方與最下方按鈕有圓角 */
[data-slot="nav-btn"]:first-of-type > button {{ border-radius: 8px 8px 0 0 !important; }}
[data-slot="nav-btn"]:last-of-type  > button {{ border-radius: 0 0 8px 8px !important; }}

/* ── ↔️ 分頁控制列 ── */
[data-testid="stHorizontalBlock"] {{
    margin-top: 0px !important;    /* 分頁列與上方按鈕間距 */
    margin-bottom: 0px !important; /* 分頁列與下方資訊框間距 */
}}
.page-text {{
    color: white; font-weight: 500; font-size: 18px;
    text-align: center; line-height: 40px;
}}

/* ── ℹ️ 底部資訊框 ── */
.nav-footer {{
    height: {FOOTER_HEIGHT}px; 
    background: white; 
    border-radius: 12px;
    display: flex; 
    flex-direction: column;
    align-items: center; 
    justify-content: center;
    padding: 10px;        /* 資訊框內的留白 */
    margin-top: 5px;      /* 確保不緊貼分頁列 */
}}
</style>

<script>
// 🧠 核心邏輯：控制目錄的點擊開關
(function() {{
    function handleSelectbox() {{
        // 找到 Streamlit 的 Selectbox 容器
        const selectContainer = document.querySelector('[data-testid="stSelectbox"] div[role="button"]');
        
        if (selectContainer && !selectContainer.dataset.clickListener) {{
            selectContainer.addEventListener('click', (e) => {{
                const isExpanded = selectContainer.getAttribute('aria-expanded') === 'true';
                
                // 如果已經是展開狀態，再次點擊時模擬 Escape 鍵關閉選單
                if (isExpanded) {{
                    setTimeout(() => {{
                        window.dispatchEvent(new KeyboardEvent('keydown', {{ 'key': 'Escape' }}));
                    }}, 10);
                }}
            }}, true);
            selectContainer.dataset.clickListener = 'true';
        }}
    }}

    function tagNavBtns() {{
        document.querySelectorAll('[data-testid="stButton"]').forEach(w => {{
            if (!w.closest('[data-testid="stHorizontalBlock"]'))
                w.setAttribute('data-slot', 'nav-btn');
        }});
    }}

    setInterval(() => {{
        handleSelectbox();
        tagNavBtns();
    }}, 400);
}})();
</script>
""", unsafe_allow_html=True)

# ==========================================
# 3. UI 渲染部分
# ==========================================

# 1. 目錄選擇
selected_cat = st.selectbox("分類", categories, label_visibility="collapsed")
filtered_locations = all_locs if selected_cat == "全部" else [l for l in all_locs if l["category"] == selected_cat]

# 2. 標題框
st.markdown(f'<div class="nav-header"><h1>{current_name}</h1><p>GPS: {current_pos[0]:.3f}, {current_pos[1]:.3f}</p></div>', unsafe_allow_html=True)

# 3. 按鈕邏輯
total_pages = max(1, math.ceil(len(filtered_locations) / PAGE_SIZE))
if st.session_state.page >= total_pages: st.session_state.page = 0
start_idx = st.session_state.page * PAGE_SIZE
current_items = filtered_locations[start_idx : start_idx + PAGE_SIZE]

for i in range(PAGE_SIZE):
    if i < len(current_items):
        loc = current_items[i]
        if st.button(loc["name"], key=f"btn_{i}", use_container_width=True):
            st.session_state.selected_loc = loc
            dist = geodesic(current_pos, loc["coords"]).kilometers
            phi1, phi2, dl = math.radians(current_pos[0]), math.radians(loc["coords"][0]), math.radians(loc["coords"][1]-current_pos[1])
            angle = (math.degrees(math.atan2(math.sin(dl)*math.cos(phi2), math.cos(phi1)*math.sin(phi2)-math.sin(phi1)*math.cos(phi2)*math.cos(dl)))+360)%360
            send_to_led(loc["name"], dist, angle) # 這裡保留您的 LED 發送函式
            st.rerun()
    else:
        st.button("　", key=f"empty_{i}", disabled=True, use_container_width=True)

# 4. 分頁
_, lc, mc, rc, _ = st.columns([3, 1, 2, 1, 3])
with lc:
    if st.button("❮", key="prev"):
        st.session_state.page = (st.session_state.page - 1) % total_pages
        st.rerun()
with mc:
    st.markdown(f'<div class="page-text">{st.session_state.page+1} / {total_pages}</div>', unsafe_allow_html=True)
with rc:
    if st.button("❯", key="next"):
        st.session_state.page = (st.session_state.page + 1) % total_pages
        st.rerun()

# 5. 底部資訊框
def get_direction_text(bearing):
    dirs = [("↑","北","North"),("↗","東北","NE"),("→","東","East"),("↘","東南","SE"),("↓","南","South"),("↙","西南","SW"),("←","西","West"),("↖","西北","NW")]
    return dirs[int((bearing + 22.5) / 45) % 8]

if st.session_state.selected_loc:
    loc = st.session_state.selected_loc
    dist = geodesic(current_pos, loc["coords"]).kilometers
    phi1, phi2, dl = math.radians(current_pos[0]), math.radians(loc["coords"][0]), math.radians(loc["coords"][1]-current_pos[1])
    bear = (math.degrees(math.atan2(math.sin(dl)*math.cos(phi2), math.cos(phi1)*math.sin(phi2)-math.sin(phi1)*math.cos(phi2)*math.cos(dl)))+360)%360
    arrow, zh, en = get_direction_text(bear)
    footer_content = f"""
        <div style="font-size:25px;color: black;font-weight:900;">{loc["name"]}</div>
        <div style="font-size:25px;font-weight:900;color:red;margin:4px 0;">{arrow} {zh} {en}</div>
        <div style="font-size:20px;color: gray;">距離 {dist:.3f} km | 方位角 {bear:.1f}°</div>"""
else:
    footer_content = '<div style="font-size:18px;font-weight:900;color: black;">請選擇目的地</div>'
st.markdown(f'<div class="nav-footer">{footer_content}</div>', unsafe_allow_html=True)