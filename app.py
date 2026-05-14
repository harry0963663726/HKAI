# -*- coding: utf-8 -*-
import streamlit as st
import configparser
import os
import math
import requests
from geopy.distance import geodesic

# ==========================================
# 0. 基礎頁面配置
# ==========================================
st.set_page_config(
    page_title="智慧路燈導航", 
    layout="centered"
)

# 定義全局常量，方便統一修改尺寸
PAGE_SIZE = 3      # 每頁顯示的地點數量
BTN_HEIGHT = 50    # 地點按鈕的高度
FOOTER_HEIGHT = 140 # 底部資訊卡的高度

# ==========================================
# 1. 核心邏輯功能
# ==========================================

# 傳送導航數據至外部 LED 顯示器的 API
def send_to_led(name, distance, angle):
    url = "http://10.12.4.100:8080/api/control"
    payload = {
        "data": {
            "target": name, 
            "dist": f"{distance:.2f}km", 
            "angle": f"{angle:.1f}°"
        }
    }
    try:
        requests.post(url, json=payload, timeout=0)
    except:
        pass

# 計算兩點間的方位角 (0-360度)
def calculate_bearing(start_pos, end_pos):
    phi1 = math.radians(start_pos[0])
    phi2 = math.radians(end_pos[0])
    dl = math.radians(end_pos[1] - start_pos[1])
    x = math.sin(dl) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - (
        math.sin(phi1) * math.cos(phi2) * math.cos(dl)
    )
    return (math.degrees(math.atan2(x, y)) + 360) % 360

# 將方位角轉換為直觀的箭頭與中英文方向
def get_direction_text(bearing):
    dirs = [
        ("↑", "北", "N"), ("↗", "東北", "NE"), ("→", "東", "E"), ("↘", "東南", "SE"),
        ("↓", "南", "S"), ("↙", "西南", "SW"), ("←", "西", "W"), ("↖", "西北", "NW")
    ]
    return dirs[int((bearing + 22.5) / 45) % 8]

# ==========================================
# 2. 設定檔載入 (解析 config.ini)
# ==========================================

def load_config():
    all_locations = []
    curr_pos = (25.035, 121.567) # 預設位置
    curr_name = "當前位置"
    categories = ["全部"]
    config = configparser.ConfigParser()
    config.optionxform = str
    if os.path.exists('config.ini'):
        config.read('config.ini', encoding='utf-8')
        if 'Settings' in config:
            curr_pos = (
                config.getfloat('Settings', 'current_lat', fallback=25.035), 
                config.getfloat('Settings', 'current_lon', fallback=121.567)
            )
            curr_name = config.get('Settings', 'current_location', fallback="預設起點")
        if 'Locations' in config:
            for name in config['Locations']:
                try:
                    p = [i.strip() for i in config['Locations'][name].split(',')]
                    cat = p[2] if len(p) > 2 else "未分類"
                    all_locations.append({
                        "name": name.upper(), 
                        "coords": (float(p[0]), float(p[1])), 
                        "category": cat
                    })
                    if cat not in categories: 
                        categories.append(cat)
                except: 
                    continue
    return curr_pos, curr_name, all_locations, categories

current_pos, current_name, all_locs, categories = load_config()

# 初始化 Session 狀態，紀錄頁碼與選中的地點
if "page" not in st.session_state: st.session_state.page = 0
if "selected_loc" not in st.session_state: st.session_state.selected_loc = None

# ==========================================
# 3. 視覺樣式與 CSS 客製化區塊
# ==========================================

st.markdown(f"""
<style>
    /* 隱藏 Streamlit 預設的所有導航欄、頁首、頁尾與選單 */
    [data-testid="stHeader"], [data-testid="stToolbar"], footer, #MainMenu, 
    [data-testid="stDecoration"], [class*="viewerBadge"], [data-testid="stStatusWidget"] {{
        display: none !important;
    }}

    /* 設定全網頁背景為純黑色，並禁止左右橫向滾動 */
    html, body, [data-testid="stAppViewContainer"] {{ 
        background-color: black !important;
        overflow-x: hidden !important;
    }}
    
    /* 限制手機顯示區域的寬度與上下邊距 */
    .block-container {{ 
        max-width: 500px !important; 
        padding: 40px 15px !important; 
    }}

    /* 定義通用白色卡片樣式：白底黑字、圓角、禁止文字選取(防長按選單) */
    .white-card {{
        background-color: white !important;
        color: black !important;
        border-radius: 10px !important;
        padding: 15px;
        margin-bottom: 12px;
        text-align: center;
        border: 1px solid silver !important;
        user-select: none !important;
        -webkit-user-select: none !important;
        -webkit-touch-callout: none !important;
    }}

    /* 修正下拉目錄：隱藏輸入文字功能，只允許點擊挑選 */
    [data-testid="stSelectbox"] input {{
        caret-color: transparent !important; /* 隱藏游標 */
        color: transparent !important;       /* 隱藏輸入文字 */
        pointer-events: none !important;     /* 禁止直接點擊 input */
    }}
    
    [data-testid="stSelectbox"] div[role="button"] {{
        background-color: white !important;
        color: black !important;
        border-radius: 10px !important;
        height: 48px !important;
        border: 1px solid silver !important;
        margin-bottom: 12px !important;
        cursor: pointer !important;
        user-select: none !important;
    }}
    
    /* 設定下拉清單內的選項文字為粗體黑字 */
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
        color: black !important;
        font-weight: bold !important;
        font-size: 18px !important;
    }}

    /* 地點列表按鈕樣式：組成一個連續的列表感 */
    [data-slot="nav-btn"] button {{
        height: {BTN_HEIGHT}px !important; 
        background-color: white !important;
        color: black !important;
        border: none !important;
        border-left: 1px solid silver !important;
        border-right: 1px solid silver !important;
        border-bottom: 1px solid gainsboro !important;
        border-radius: 0 !important;
        font-size: 20px !important;
        font-weight: bold !important;
        transition: none !important;
        user-select: none !important;
    }}
    
    /* 列表最上方按鈕補回上方圓角 */
    [data-slot="nav-btn"]:first-of-type button {{ 
        border-radius: 10px 10px 0 0 !important; 
        border-top: 1px solid silver !important;
    }}
    
    /* 列表最下方按鈕補回下方圓角 */
    [data-slot="nav-btn"]:last-of-type button {{ 
        border-radius: 0 0 10px 10px !important; 
        border-bottom: 1px solid silver !important;
    }}

    /* 分頁控制器：強制水平併排不換行 */
    [data-testid="stHorizontalBlock"] {{ 
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        width: 100% !important;
        background-color: transparent !important;
        margin: 20px 0 !important;
        padding: 0 !important;
        align-items: center !important;
    }}
    
    [data-testid="stHorizontalBlock"] > div {{ 
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }}

    /* 修改 < 與 > 符號按鈕的粗細與尺寸 */
    [data-testid="stHorizontalBlock"] [data-testid="stButton"] button {{
        background-color: white !important;
        color: black !important;
        border: 1px solid silver !important;
        border-radius: 10px !important;
        font-weight: 50 !important; /* 這裡改粗細：900 是最粗 */
        font-size: 30px !important; /* 調大符號尺寸 */
        height: 50px !important;
        width: 100% !important;
    }}

    /* 頁碼中間文字樣式 */
    .page-text {{ 
        color: white !important; 
        font-weight: bold; 
        font-size: 20px; 
        text-align: center;
        line-height: 50px;
        white-space: nowrap;
        user-select: none;
    }}

    /* 防止所有按鈕在點擊或聚焦時變黑或出現陰影 */
    [data-testid="stButton"] button:active,
    [data-testid="stButton"] button:focus,
    [data-testid="stButton"] button:hover {{ 
        background-color: white !important; 
        color: black !important; 
        box-shadow: none !important;
        outline: none !important;
    }}

    /* 標題與頁首文字細節 */
    .nav-header h1 {{ color: black; margin: 0; font-size: 32px; font-weight: 900; }}
    .nav-footer {{ height: {FOOTER_HEIGHT}px; display: flex; flex-direction: column; justify-content: center; }}
</style>

<script>
/* JS 腳本：處理手機瀏覽器的一些交互細節 */
(function() {{
    const appFixer = () => {{
        // 強制按鈕點擊後失焦，防止點擊後按鈕顏色卡住
        document.querySelectorAll('button').forEach(btn => {{
            if (!btn.dataset.blurfix) {{
                const clear = () => {{ setTimeout(() => {{ btn.blur(); }}, 100); }};
                btn.addEventListener('touchend', clear);
                btn.addEventListener('click', clear);
                btn.dataset.blurfix = 'true';
            }}
        }});
        // 為地點按鈕標記屬性，以便 CSS 抓取圓角處理
        document.querySelectorAll('[data-testid="stButton"]').forEach(w => {{
            if (!w.closest('[data-testid="stHorizontalBlock"]')) 
                w.setAttribute('data-slot', 'nav-btn');
        }});
    }};
    setInterval(appFixer, 400);
}})();
</script>
""", unsafe_allow_html=True)

# ==========================================
# 4. 畫面渲染與交互
# ==========================================

# A. 目錄分類
selected_cat = st.selectbox("分類", categories, label_visibility="collapsed")
filtered_locations = all_locs if selected_cat == "全部" else [l for l in all_locs if l["category"] == selected_cat]

# B. 起點標題區 (White Card)
st.markdown(
    f'<div class="white-card nav-header"><h1>{current_name}</h1>'
    f'<p style="color:black; margin:0; font-size:14px;">座標: {current_pos[0]:.4f}, {current_pos[1]:.4f}</p></div>', 
    unsafe_allow_html=True
)

# C. 地點清單列表
total_pages = max(1, math.ceil(len(filtered_locations) / PAGE_SIZE))
if st.session_state.page >= total_pages: st.session_state.page = 0
start_idx = st.session_state.page * PAGE_SIZE
current_items = filtered_locations[start_idx : start_idx + PAGE_SIZE]

for i in range(PAGE_SIZE):
    if i < len(current_items):
        item = current_items[i]
        if st.button(item["name"], key=f"loc_{i}", use_container_width=True):
            st.session_state.selected_loc = item
            d = geodesic(current_pos, item["coords"]).kilometers
            b = calculate_bearing(current_pos, item["coords"])
            send_to_led(item["name"], d, b)
            st.rerun()
    else:
        # 當列表不足 5 個時，顯示空按鈕維持高度一致
        st.button(" ", key=f"empty_{i}", disabled=True, use_container_width=True)

# D. 分頁控制列 (獨立按鈕 + 中間白字頁碼)
col_prev, col_num, col_next = st.columns([1, 1.5, 1])
with col_prev:
    if st.button("上一頁", key="nav_prev", use_container_width=True):
        st.session_state.page = (st.session_state.page - 1) % total_pages
        st.rerun()
with col_num:
    st.markdown(f'<div class="page-text">{st.session_state.page + 1} / {total_pages}</div>', unsafe_allow_html=True)
with col_next:
    if st.button("下一頁", key="nav_next", use_container_width=True):
        st.session_state.page = (st.session_state.page + 1) % total_pages
        st.rerun()

# E. 底部導航資訊顯示區 (White Card)
if st.session_state.selected_loc:
    t = st.session_state.selected_loc
    d_km = geodesic(current_pos, t["coords"]).kilometers
    b_deg = calculate_bearing(current_pos, t["coords"])
    arr, zh_dir, en_dir = get_direction_text(b_deg)
    
    st.markdown(f"""
        <div class="white-card nav-footer">
            <div style="font-size:26px; font-weight:bold; color:black;">{t['name']}</div>
            <div style="font-size:28px; color:red; font-weight:bold; margin:8px 0;">
                {arr} {zh_dir} ({en_dir})
            </div>
            <div style="font-size:16px; color:black; font-weight:bold;">
                距離: {d_km:.3f} km | 方位: {b_deg:.1f}°
            </div>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(
        '<div class="white-card nav-footer"><div style="color:black; font-weight:bold; font-size:20px;">'
        '請選擇目的地</div></div>', 
        unsafe_allow_html=True
    )