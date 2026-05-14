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
    page_title="Smart Light Navigation", 
    layout="centered"
)

# 介面常數定義 (分行羅列)
PAGE_SIZE = 5
BTN_HEIGHT = 50
BTN_GAP = 1
FOOTER_HEIGHT = 140

# ==========================================
# 1. 核心功能函式
# ==========================================

def send_to_led(name, distance, angle):
    """發送導航數據至嵌入式設備"""
    url = "http://10.12.4.100:8080/api/control"
    
    # 參數分行排版
    payload = {
        "data": {
            "target": name, 
            "dist": f"{distance:.2f}km", 
            "angle": f"{angle:.1f}°"
        }
    }
    
    try:
        requests.post(
            url, 
            json=payload, 
            timeout=2
        )
    except:
        pass

def calculate_bearing(start_pos, end_pos):
    """計算從起點到終點的方位角"""
    phi1 = math.radians(start_pos[0])
    phi2 = math.radians(end_pos[0])
    dl = math.radians(end_pos[1] - start_pos[1])
    
    x = math.sin(dl) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - (
        math.sin(phi1) * math.cos(phi2) * math.cos(dl)
    )
    
    initial_bearing = math.atan2(x, y)
    bearing_deg = math.degrees(initial_bearing)
    
    return (bearing_deg + 360) % 360

def get_direction_text(bearing):
    """方位角對應之箭頭與文字描述"""
    dirs = [
        ("↑", "北", "North"), 
        ("↗", "東北", "NE"), 
        ("→", "東", "East"), 
        ("↘", "東南", "SE"),
        ("↓", "南", "South"), 
        ("↙", "西南", "SW"), 
        ("←", "西", "West"), 
        ("↖", "西北", "NW")
    ]
    index = int((bearing + 22.5) / 45) % 8
    return dirs[index]

# ==========================================
# 2. 設定檔載入邏輯
# ==========================================

def load_config():
    all_locations = []
    curr_pos = (25.035, 121.567)
    curr_name = "Xinyi Vieshow"
    categories = ["All"]
    
    config = configparser.ConfigParser()
    config.optionxform = str
    
    if os.path.exists('config.ini'):
        config.read('config.ini', encoding='utf-8')
        
        # 讀取 Settings
        if 'Settings' in config:
            curr_lat = config.getfloat('Settings', 'current_lat', fallback=25.035)
            curr_lon = config.getfloat('Settings', 'current_lon', fallback=121.567)
            curr_pos = (curr_lat, curr_lon)
            curr_name = config.get('Settings', 'current_location', fallback="Xinyi Vieshow")
            
        # 讀取 Locations
        if 'Locations' in config:
            for name in config['Locations']:
                try:
                    val = config['Locations'][name]
                    parts = [p.strip() for p in val.split(',')]
                    
                    lat = float(parts[0])
                    lon = float(parts[1])
                    cat = parts[2] if len(parts) > 2 else "Uncategorized"
                    
                    all_locations.append({
                        "name": name.upper(), 
                        "coords": (lat, lon), 
                        "category": cat
                    })
                    
                    if cat not in categories: 
                        categories.append(cat)
                except: 
                    continue
                    
    return curr_pos, curr_name, all_locations, categories

# 執行載入
current_pos, current_name, all_locs, categories = load_config()

# 初始化會話狀態
if "page" not in st.session_state: 
    st.session_state.page = 0

if "selected_loc" not in st.session_state: 
    st.session_state.selected_loc = None

# ==========================================
# 3. 視覺樣式與腳本 (深度換行排版)
# ==========================================

st.markdown(f"""
<style>
    /* --- 全域隱藏與背景 --- */
    [data-testid="stHeader"], 
    [data-testid="stToolbar"], 
    footer, 
    #MainMenu, 
    [data-testid="stDecoration"], 
    [class*="viewerBadge"], 
    [data-testid="stStatusWidget"] {{
        display: none !important;
        visibility: hidden !important;
    }}

    html, body, [data-testid="stAppViewContainer"] {{ 
        background-color: black !important; 
    }}
    
    .block-container {{ 
        max-width: 500px !important; 
        padding: 60px 10px 10px 10px !important; 
    }}

    /* --- 目錄區塊 (Selectbox) 修正 --- */
    /* 讓輸入框透明化，僅作為背景按鈕觸發層 */
    [data-testid="stSelectbox"] input {{
        opacity: 0 !important;
        position: absolute !important;
        pointer-events: none !important;
    }}
    
    /* 目錄主按鈕條 */
    [data-testid="stSelectbox"] div[role="button"] {{
        background-color: white !important;
        color: black !important;
        border-radius: 10px !important;
        height: 48px !important;
        display: flex !important;
        align-items: center !important;
        padding-left: 12px !important;
        cursor: pointer !important;
        -webkit-tap-highlight-color: transparent !important;
        user-select: none !important;
    }}
    
    /* 修正選中的文字顏色 */
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
        color: black !important;
        font-weight: bold !important;
        font-size: 18px !important;
    }}

    /* --- 按鈕通用防反黑機制 --- */
    button {{ 
        -webkit-tap-highlight-color: transparent !important; 
        outline: none !important; 
    }}
    
    button:active, 
    button:focus {{ 
        background-color: darkslategrey !important; 
        color: white !important; 
        box-shadow: none !important; 
    }}

    /* --- 分頁導航列 --- */
    [data-testid="stHorizontalBlock"] {{ 
        display: flex !important; 
        flex-direction: row !important; 
        flex-wrap: nowrap !important; 
        align-items: center !important; 
        justify-content: center !important; 
        margin: 10px 0 !important;
    }}
    
    [data-testid="stHorizontalBlock"] > div {{ 
        flex: none !important; 
        width: auto !important; 
    }}
    
    .page-text {{ 
        color: white; 
        font-weight: bold; 
        font-size: 18px; 
        margin: 0 15px; 
    }}

    /* --- 地點列表按鈕樣式 --- */
    [data-slot="nav-btn"] {{ 
        height: {BTN_HEIGHT}px !important; 
        border-bottom: {BTN_GAP}px solid black !important; 
    }}
    
    [data-slot="nav-btn"] button {{
        height: {BTN_HEIGHT}px !important; 
        background: darkslategrey !important;
        color: white !important; 
        font-size: 22px !important; 
        font-weight: bold !important;
        border: 1px solid dimgray !important; 
        border-radius: 0 !important;
    }}
    
    [data-slot="nav-btn"]:first-of-type button {{ 
        border-radius: 10px 10px 0 0 !important; 
    }}
    
    [data-slot="nav-btn"]:last-of-type button {{ 
        border-radius: 0 0 10px 10px !important; 
    }}

    /* --- 標題與底部資訊卡 --- */
    .nav-header {{ 
        background: white; 
        border-radius: 10px; 
        padding: 15px; 
        margin-bottom: 10px; 
        text-align: center; 
    }}
    
    .nav-header h1 {{ 
        color: black; 
        margin: 0; 
        font-size: 36px; 
        font-weight: 900; 
    }}
    
    .nav-footer {{ 
        background: white; 
        border-radius: 15px; 
        height: {FOOTER_HEIGHT}px; 
        padding: 20px; 
        margin-top: 10px; 
        text-align: center; 
        display: flex; 
        flex-direction: column; 
        justify-content: center; 
    }}
</style>

<script>
(function() {{
    const appFixer = () => {{
        // 1. 目錄點擊二次關閉邏輯
        const sb = document.querySelector('[data-testid="stSelectbox"] div[role="button"]');
        if (sb && !sb.dataset.bound) {{
            const toggle = (e) => {{
                if (sb.getAttribute('aria-expanded') === 'true') {{
                    setTimeout(() => {{
                        window.dispatchEvent(new KeyboardEvent('keydown', {{ 'key': 'Escape' }}));
                        sb.blur();
                    }}, 10);
                }}
            }};
            sb.addEventListener('touchstart', toggle, {{passive: true}});
            sb.addEventListener('mousedown', toggle);
            sb.dataset.bound = 'true';
        }}

        // 2. 按鈕點擊後解除焦點 (防反黑)
        document.querySelectorAll('button').forEach(btn => {{
            if (!btn.dataset.blurfix) {{
                const clear = () => {{ 
                    setTimeout(() => {{ btn.blur(); }}, 120); 
                }};
                btn.addEventListener('touchend', clear);
                btn.addEventListener('click', clear);
                btn.dataset.blurfix = 'true';
            }}
        }});

        // 3. 標記地點導覽按鈕
        document.querySelectorAll('[data-testid="stButton"]').forEach(w => {{
            if (!w.closest('[data-testid="stHorizontalBlock"]')) {{
                w.setAttribute('data-slot', 'nav-btn');
            }}
        }});
    }};
    
    setInterval(appFixer, 400);
}})();
</script>
""", unsafe_allow_html=True)

# ==========================================
# 4. UI 介面渲染 (Python 分行排版)
# ==========================================

# A. 分類選擇器
selected_cat = st.selectbox(
    "Category", 
    categories, 
    label_visibility="collapsed"
)

# 過濾地點
filtered_locations = (
    all_locs if selected_cat == "All" 
    else [l for l in all_locs if l["category"] == selected_cat]
)

# B. 當前位置標題
st.markdown(
    f'<div class="nav-header">'
    f'<h1>{current_name}</h1>'
    f'<p style="color:gray; margin:6px 0 0 0; font-family:monospace; font-size:16px;">'
    f'GPS: {current_pos[0]:.4f}, {current_pos[1]:.4f}'
    f'</p></div>', 
    unsafe_allow_html=True
)

# C. 地點清單與分頁邏輯
total_pages = max(1, math.ceil(len(filtered_locations) / PAGE_SIZE))

if st.session_state.page >= total_pages: 
    st.session_state.page = 0
    
start_idx = st.session_state.page * PAGE_SIZE
current_items = filtered_locations[start_idx : start_idx + PAGE_SIZE]

# 渲染按鈕
for i in range(PAGE_SIZE):
    if i < len(current_items):
        item = current_items[i]
        btn_label = item["name"]
        
        if st.button(btn_label, key=f"loc_{i}", use_container_width=True):
            st.session_state.selected_loc = item
            
            # 數據處理與傳輸
            dist_val = geodesic(current_pos, item["coords"]).kilometers
            bear_val = calculate_bearing(current_pos, item["coords"])
            
            send_to_led(item["name"], dist_val, bear_val)
            st.rerun()
    else:
        # 填充空白按鈕以維持排版高度一致
        st.button(
            " ", 
            key=f"empty_{i}", 
            disabled=True, 
            use_container_width=True
        )

# D. 分頁控制器
col_prev, col_num, col_next = st.columns([1, 1, 1])

with col_prev:
    if st.button("❮", key="nav_prev"):
        st.session_state.page = (st.session_state.page - 1) % total_pages
        st.rerun()
        
with col_num:
    page_display = f"{st.session_state.page + 1} / {total_pages}"
    st.markdown(
        f'<div class="page-text">{page_display}</div>', 
        unsafe_allow_html=True
    )
    
with col_next:
    if st.button("❯", key="nav_next"):
        st.session_state.page = (st.session_state.page + 1) % total_pages
        st.rerun()

# E. 底部資訊顯示卡
if st.session_state.selected_loc:
    target = st.session_state.selected_loc
    
    # 即時計算顯示數據
    d_km = geodesic(current_pos, target["coords"]).kilometers
    b_deg = calculate_bearing(current_pos, target["coords"])
    arr, z_dir, e_dir = get_direction_text(b_deg)
    
    st.markdown(f"""
        <div class="nav-footer">
            <div style="font-size:30px; font-weight:bold; color:black;">
                {target['name']}
            </div>
            <div style="font-size:28px; color:red; font-weight:bold; margin:10px 0;">
                {arr} {z_dir} {e_dir}
            </div>
            <div style="font-size:15px; color:gray; font-family:monospace;">
                {d_km:.3f} km | Bearing: {b_deg:.1f}°
            </div>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(
        '<div class="nav-footer">'
        '<div style="color:gray; font-weight:bold; font-size:22px;">'
        'Please Select Destination'
        '</div></div>', 
        unsafe_allow_html=True
    )