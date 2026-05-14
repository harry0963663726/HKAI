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

PAGE_SIZE = 5
BTN_HEIGHT = 50
BTN_GAP = 1
FOOTER_HEIGHT = 140

# ==========================================
# 1. 核心功能函式
# ==========================================

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

def calculate_bearing(start_pos, end_pos):
    phi1 = math.radians(start_pos[0])
    phi2 = math.radians(end_pos[0])
    dl = math.radians(end_pos[1] - start_pos[1])
    x = math.sin(dl) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - (math.sin(phi1) * math.cos(phi2) * math.cos(dl))
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def get_direction_text(bearing):
    dirs = [
        ("↑", "北", "North"), ("↗", "東北", "NE"), 
        ("→", "東", "East"), ("↘", "東南", "SE"),
        ("↓", "南", "South"), ("↙", "西南", "SW"), 
        ("←", "西", "West"), ("↖", "西北", "NW")
    ]
    return dirs[int((bearing + 22.5) / 45) % 8]

# ==========================================
# 2. 設定檔載入
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
        if 'Settings' in config:
            curr_pos = (config.getfloat('Settings', 'current_lat'), config.getfloat('Settings', 'current_lon'))
            curr_name = config.get('Settings', 'current_location')
        if 'Locations' in config:
            for name in config['Locations']:
                try:
                    p = [i.strip() for i in config['Locations'][name].split(',')]
                    all_locations.append({"name": name.upper(), "coords": (float(p[0]), float(p[1])), "category": p[2] if len(p)>2 else "Misc"})
                    if len(p)>2 and p[2] not in categories: categories.append(p[2])
                except: continue
    return curr_pos, curr_name, all_locations, categories

current_pos, current_name, all_locs, categories = load_config()

if "page" not in st.session_state: st.session_state.page = 0
if "selected_loc" not in st.session_state: st.session_state.selected_loc = None

# ==========================================
# 3. 視覺樣式與互動腳本 (排版穩定性修正)
# ==========================================

st.markdown(f"""
<style>
    /* --- 基礎環境鎖定 --- */
    [data-testid="stHeader"], [data-testid="stToolbar"], footer, #MainMenu, 
    [data-testid="stDecoration"], [class*="viewerBadge"], [data-testid="stStatusWidget"] {{
        display: none !important;
    }}

    html, body, [data-testid="stAppViewContainer"] {{ 
        background-color: black !important;
        overflow-x: hidden !important; /* 禁止橫向滾動 */
    }}
    
    .block-container {{ 
        max-width: 500px !important; 
        padding: 40px 15px !important; 
    }}

    /* --- 目錄修正 --- */
    [data-testid="stSelectbox"] input {{
        opacity: 0 !important;
        position: absolute !important;
        pointer-events: none !important;
    }}
    
    [data-testid="stSelectbox"] div[role="button"] {{
        background-color: white !important;
        color: black !important;
        border-radius: 10px !important;
        height: 48px !important;
        -webkit-tap-highlight-color: transparent !important;
    }}
    
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
        color: black !important;
        font-weight: bold !important;
    }}

    /* --- 按鈕防變黑與焦點還原 --- */
    button {{ 
        -webkit-tap-highlight-color: transparent !important; 
        outline: none !important;
        transition: none !important;
    }}
    
    /* 強制按鈕在選中/焦點/點擊時維持 darkslategrey，不變黑 */
    [data-testid="stButton"] button,
    [data-testid="stButton"] button:active,
    [data-testid="stButton"] button:focus,
    [data-testid="stButton"] button:hover,
    [data-testid="stButton"] button:focus-visible {{ 
        background-color: darkslategrey !important; 
        color: white !important; 
        box-shadow: none !important;
        border: 1px solid dimgray !important;
    }}

    /* --- 分頁導航列強硬派排版 (33/33/33 分散) --- */
    [data-testid="stHorizontalBlock"] {{ 
        display: flex !important; 
        flex-direction: row !important; 
        flex-wrap: nowrap !important; 
        width: 100% !important;
        justify-content: space-between !important;
        align-items: center !important;
        margin: 15px 0 !important;
    }}
    
    [data-testid="stHorizontalBlock"] > div {{ 
        width: 33% !important; /* 強制各占三分之一 */
        flex: 1 1 33% !important;
        min-width: 0 !important;
    }}
    
    .page-text {{ 
        color: white; 
        font-weight: bold; 
        font-size: 18px; 
        text-align: center;
        white-space: nowrap;
    }}

    /* --- 地點列表樣式 --- */
    [data-slot="nav-btn"] {{ 
        height: {BTN_HEIGHT}px !important; 
        border-bottom: {BTN_GAP}px solid black !important; 
    }}
    
    [data-slot="nav-btn"] button {{
        height: {BTN_HEIGHT}px !important; 
        font-size: 20px !important; 
        font-weight: bold !important;
        border-radius: 0 !important;
    }}
    
    [data-slot="nav-btn"]:first-of-type button {{ border-radius: 10px 10px 0 0 !important; }}
    [data-slot="nav-btn"]:last-of-type button {{ border-radius: 0 0 10px 10px !important; }}

    .nav-header {{ background: white; border-radius: 10px; padding: 12px; margin-bottom: 8px; text-align: center; }}
    .nav-header h1 {{ color: black; margin: 0; font-size: 32px; font-weight: 900; }}
    .nav-footer {{ background: white; border-radius: 15px; height: {FOOTER_HEIGHT}px; padding: 15px; margin-top: 10px; text-align: center; display: flex; flex-direction: column; justify-content: center; }}
</style>

<script>
(function() {{
    const appFixer = () => {{
        // 1. 目錄點擊二次關閉
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

        // 2. 徹底消除按鈕焦點狀態
        document.querySelectorAll('button').forEach(btn => {{
            if (!btn.dataset.blurfix) {{
                const clear = () => {{ 
                    setTimeout(() => {{ 
                        btn.blur(); 
                        window.getSelection()?.removeAllRanges(); // 移除可能的選取陰影
                    }}, 100); 
                }};
                btn.addEventListener('touchend', clear);
                btn.addEventListener('click', clear);
                btn.dataset.blurfix = 'true';
            }}
        }});

        // 3. 標記地點按鈕
        document.querySelectorAll('[data-testid="stButton"]').forEach(w => {{
            if (!w.closest('[data-testid="stHorizontalBlock"]')) w.setAttribute('data-slot', 'nav-btn');
        }});
    }};
    setInterval(appFixer, 400);
}})();
</script>
""", unsafe_allow_html=True)

# ==========================================
# 4. UI 介面渲染
# ==========================================

selected_cat = st.selectbox("Category", categories, label_visibility="collapsed")
filtered_locations = all_locs if selected_cat == "All" else [l for l in all_locs if l["category"] == selected_cat]

st.markdown(f'<div class="nav-header"><h1>{current_name}</h1><p style="color:gray; margin:0; font-size:14px;">GPS: {current_pos[0]:.4f}, {current_pos[1]:.4f}</p></div>', unsafe_allow_html=True)

total_pages = max(1, math.ceil(len(filtered_locations) / PAGE_SIZE))
if st.session_state.page >= total_pages: st.session_state.page = 0
start_idx = st.session_state.page * PAGE_SIZE
current_items = filtered_locations[start_idx : start_idx + PAGE_SIZE]

for i in range(PAGE_SIZE):
    if i < len(current_items):
        item = current_items[i]
        if st.button(item["name"], key=f"loc_{i}", use_container_width=True):
            st.session_state.selected_loc = item
            dist_val = geodesic(current_pos, item["coords"]).kilometers
            bear_val = calculate_bearing(current_pos, item["coords"])
            send_to_led(item["name"], dist_val, bear_val)
            st.rerun()
    else:
        st.button(" ", key=f"empty_{i}", disabled=True, use_container_width=True)

# 分頁控制列 (使用穩定的比例分配)
col_prev, col_num, col_next = st.columns([1, 1, 1])
with col_prev:
    if st.button("❮", key="nav_prev", use_container_width=True):
        st.session_state.page = (st.session_state.page - 1) % total_pages
        st.rerun()
with col_num:
    st.markdown(f'<div class="page-text">{st.session_state.page + 1} / {total_pages}</div>', unsafe_allow_html=True)
with col_next:
    if st.button("❯", key="nav_next", use_container_width=True):
        st.session_state.page = (st.session_state.page + 1) % total_pages
        st.rerun()

if st.session_state.selected_loc:
    t = st.session_state.selected_loc
    d_km = geodesic(current_pos, t["coords"]).kilometers
    b_deg = calculate_bearing(current_pos, t["coords"])
    arr, z_dir, e_dir = get_direction_text(b_deg)
    st.markdown(f"""
        <div class="nav-footer">
            <div style="font-size:26px; font-weight:bold; color:black;">{t['name']}</div>
            <div style="font-size:24px; color:red; font-weight:bold; margin:6px 0;">{arr} {z_dir} {e_dir}</div>
            <div style="font-size:14px; color:gray;">{d_km:.3f} km | {b_deg:.1f}°</div>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown('<div class="nav-footer"><div style="color:gray; font-weight:bold; font-size:20px;">Please Select</div></div>', unsafe_allow_html=True)