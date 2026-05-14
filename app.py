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

# 定義 UI 尺寸常量
PAGE_SIZE = 5      
BTN_HEIGHT = 50    
FOOTER_HEIGHT = 140 

# ==========================================
# 1. 核心邏輯功能
# ==========================================

# [功能：硬體通訊] 透過 API 將導航數據傳送至 LED 控制器
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
        requests.post(url, json=payload, timeout=2)
    except:
        pass

# [功能：地理計算] 計算兩點間的精確方位角
def calculate_bearing(start_pos, end_pos):
    phi1 = math.radians(start_pos[0])
    phi2 = math.radians(end_pos[0])
    dl = math.radians(end_pos[1] - start_pos[1])
    x = math.sin(dl) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - (
        math.sin(phi1) * math.cos(phi2) * math.cos(dl)
    )
    return (math.degrees(math.atan2(x, y)) + 360) % 360

# [功能：視覺轉換] 將方位角對應至箭頭符號與方位文字
def get_direction_text(bearing):
    dirs = [
        ("↑", "北", "N"), ("↗", "東北", "NE"), 
        ("→", "東", "E"), ("↘", "東南", "SE"),
        ("↓", "南", "S"), ("↙", "西南", "SW"), 
        ("←", "西", "W"), ("↖", "西北", "NW")
    ]
    return dirs[int((bearing + 22.5) / 45) % 8]

# ==========================================
# 2. 設定檔載入 (從 config.ini 讀取地點與類別)
# ==========================================

def load_config():
    all_locations = []
    curr_pos = (25.035, 121.567) 
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

# 初始化 Session 狀態
if "page" not in st.session_state: st.session_state.page = 0
if "selected_loc" not in st.session_state: st.session_state.selected_loc = None

# ==========================================
# 3. 視覺樣式與 CSS/JS 注入
# ==========================================

st.markdown(f"""
<style>
    /* [功能：去除 Streamlit 框架外觀] */
    [data-testid="stHeader"], [data-testid="stToolbar"], footer, #MainMenu, 
    [data-testid="stDecoration"], [class*="viewerBadge"], [data-testid="stStatusWidget"] {{
        display: none !important;
    }}

    /* [功能：全域背景設定] 純黑背景，禁止溢出 */
    html, body, [data-testid="stAppViewContainer"] {{ 
        background-color: black !important;
        overflow-x: hidden !important;
    }}
    
    .block-container {{ 
        max-width: 500px !important; 
        padding: 40px 15px !important; 
    }}

    /* [功能：白底區塊禁止選取] 用於標題卡、底部資訊卡 */
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

    /* [功能：目錄下拉選單優化] 隱藏文字輸入游標，防止手機鍵盤彈出 */
    [data-testid="stSelectbox"] input {{
        caret-color: transparent !important;
        color: transparent !important;
        pointer-events: none !important;
    }}
    
    [data-testid="stSelectbox"] div[role="button"] {{
        background-color: white !important;
        color: black !important;
        border-radius: 10px !important;
        height: 48px !important;
        border: 1px solid silver !important;
        margin-bottom: 12px !important;
        user-select: none !important;
    }}

    /* [功能：地點列表按鈕] 堆疊樣式與圓角處理 */
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
        user-select: none !important;
    }}
    
    [data-slot="nav-btn"]:first-of-type button {{ border-radius: 10px 10px 0 0 !important; border-top: 1px solid silver !important; }}
    [data-slot="nav-btn"]:last-of-type button {{ border-radius: 0 0 10px 10px !important; border-bottom: 1px solid silver !important; }}

    /* [核心修正：分頁條強制橫向併排] 確保 < 頁碼 > 比例為 1:1:1 */
    [data-testid="stHorizontalBlock"] {{ 
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        width: 100% !important;
        background-color: transparent !important;
        margin: 20px 0 !important;
        padding: 0 !important;
        align-items: center !important;
        gap: 0 !important; /* 減少間距讓分配更精準 */
    }}
    
    /* 強制 columns 內的 div 平分空間 */
    [data-testid="stHorizontalBlock"] [data-testid="column"] {{
        width: 33.33% !important;
        flex: 1 1 0% !important;
        min-width: 0 !important;
    }}

    /* [功能：分頁符號強化] 設定 < 與 > 的粗細與尺寸 */
    [data-testid="stHorizontalBlock"] [data-testid="stButton"] button {{
        background-color: white !important;
        color: black !important;
        border: 1px solid silver !important;
        border-radius: 10px !important;
        font-weight: 900 !important;
        font-size: 28px !important;
        height: 50px !important;
        padding: 0 !important;
    }}

    /* [功能：頁碼文字美化與禁止選取] */
    .page-text {{ 
        color: white !important; 
        font-weight: bold; 
        font-size: 18px; 
        text-align: center;
        line-height: 50px;
        user-select: none !important;
        -webkit-user-select: none !important;
        -webkit-touch-callout: none !important;
        white-space: nowrap !important;
    }}

    /* [功能：按鈕點擊狀態保護] 防止點擊後變色或出現陰影 */
    [data-testid="stButton"] button:active,
    [data-testid="stButton"] button:focus,
    [data-testid="stButton"] button:hover {{ 
        background-color: white !important; 
        color: black !important; 
        box-shadow: none !important;
        outline: none !important;
    }}

    .nav-header h1 {{ color: black; margin: 0; font-size: 32px; font-weight: 900; }}
    .nav-footer {{ height: {FOOTER_HEIGHT}px; display: flex; flex-direction: column; justify-content: center; }}
</style>

<script>
/* [功能：自定義互動邏輯] */
(function() {{
    const appFixer = () => {{
        // 1. 目錄切換邏輯：點擊已開啟選單時強制關閉 (Toggle 功能)
        const sb = document.querySelector('[data-testid="stSelectbox"] div[role="button"]');
        if (sb && !sb.dataset.bound) {{
            const toggleHandler = (e) => {{
                if (sb.getAttribute('aria-expanded') === 'true') {{
                    setTimeout(() => {{
                        window.dispatchEvent(new KeyboardEvent('keydown', {{ 'key': 'Escape' }}));
                        sb.blur();
                    }}, 10);
                }}
            }};
            sb.addEventListener('mousedown', toggleHandler);
            sb.dataset.bound = 'true';
        }}

        // 2. 按鈕自動失焦修正：防止點擊後殘留聚焦狀態
        document.querySelectorAll('button').forEach(btn => {{
            if (!btn.dataset.blurfix) {{
                const clear = () => {{ setTimeout(() => {{ btn.blur(); }}, 100); }};
                btn.addEventListener('touchend', clear);
                btn.addEventListener('click', clear);
                btn.dataset.blurfix = 'true';
            }}
        }});

        // 3. 列表按鈕類別標記：用於 CSS 列表圓角判斷
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
# 4. UI 渲染渲染區
# ==========================================

# A. 分類選擇器
selected_cat = st.selectbox("分類", categories, label_visibility="collapsed")
filtered_locations = all_locs if selected_cat == "全部" else [l for l in all_locs if l["category"] == selected_cat]

# B. 當前位置標題卡
st.markdown(
    f'<div class="white-card nav-header"><h1>{current_name}</h1>'
    f'<p style="color:gray; margin:0; font-size:14px;">座標: {current_pos[0]:.4f}, {current_pos[1]:.4f}</p></div>', 
    unsafe_allow_html=True
)

# C. 地點列表渲染
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
        # 佔位按鈕，維持高度穩定
        st.button(" ", key=f"empty_{i}", disabled=True, use_container_width=True)

# D. 分頁控制列 (比例調整為 1:1:1，且禁止選取)
col_prev, col_num, col_next = st.columns([1, 1, 1])
with col_prev:
    if st.button("<", key="nav_prev", use_container_width=True):
        st.session_state.page = (st.session_state.page - 1) % total_pages
        st.rerun()
with col_num:
    st.markdown(f'<div class="page-text">{st.session_state.page + 1} / {total_pages}</div>', unsafe_allow_html=True)
with col_next:
    if st.button(">", key="nav_next", use_container_width=True):
        st.session_state.page = (st.session_state.page + 1) % total_pages
        st.rerun()

# E. 底部導航資訊顯示區
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
        '<div class="white-card nav-footer"><div style="color:gray; font-weight:bold; font-size:20px;">'
        '請選擇目的地</div></div>', 
        unsafe_allow_html=True
    )