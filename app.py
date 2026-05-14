# -*- coding: utf-8 -*-
import streamlit as st
import configparser
import os
import math
from geopy.distance import geodesic

st.set_page_config(page_title="Smart Light Navigation", layout="centered")

PAGE_SIZE     = 5
BTN_HEIGHT    = 50    # px
BTN_GAP       = 8     # px
FOOTER_HEIGHT = 150   # px

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

selected_cat       = st.selectbox("分類", categories, label_visibility="collapsed")
filtered_locations = all_locs if selected_cat == "全部" else [l for l in all_locs if l["category"] == selected_cat]

if "page"         not in st.session_state: st.session_state.page = 0
if "selected_loc" not in st.session_state: st.session_state.selected_loc = None

total_pages = max(1, math.ceil(len(filtered_locations) / PAGE_SIZE))
if st.session_state.page >= total_pages:
    st.session_state.page = 0

start_idx     = st.session_state.page * PAGE_SIZE
current_items = filtered_locations[start_idx : start_idx + PAGE_SIZE]

# ── CSS ──
st.markdown(f"""
<style>
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"] {{
    background-color: #0E1117 !important;
}}
.block-container {{
    max-width: 500px !important;
    padding: 10px !important;
}}
header, footer, [data-testid="stHeader"] {{ visibility: hidden; }}
[data-testid="stVerticalBlock"] > div {{ gap: 0rem !important; }}

/* 頂部標題 */
.nav-header {{
    background: white; border-radius: 10px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    margin-bottom: 10px; padding: 10px 5px;
}}
.nav-header h1 {{ font-size: 40px; color: black; margin: 0; font-weight: 900; }}
.nav-header p  {{ font-size: 20px; color: gray; margin: 5px 0 0 0; font-family: monospace; }}

/* 所有選項按鈕（透過 data-slot 識別，JS 注入） */
[data-slot="nav-btn"] > button {{
    height: {BTN_HEIGHT}px !important;
    min-height: {BTN_HEIGHT}px !important;
    max-height: {BTN_HEIGHT}px !important;
    background: #1E2329 !important;
    border: 1px solid #3E454D !important;
    color: white !important;
    font-size: 40px !important;
    border-radius: 6px !important;
    width: 100% !important;
    margin: 0 !important;
    box-sizing: border-box !important;
}}
[data-slot="nav-btn"] {{
    height: {BTN_HEIGHT}px !important;
    min-height: {BTN_HEIGHT}px !important;
    max-height: {BTN_HEIGHT}px !important;
    overflow: hidden !important;
    margin-bottom: {BTN_GAP}px !important;
    padding: 0 !important;
}}

/* disabled（佔位）按鈕：透明但佔高度 */
[data-slot="nav-btn"] > button:disabled {{
    background: transparent !important;
    border: none !important;
    color: transparent !important;
    pointer-events: none !important;
}}

/* 分頁 */
.page-text {{
    color: white; font-weight: 900; font-size: 16px;
    text-align: center; min-width: 60px;
}}
[data-testid="column"] {{
    display: flex; justify-content: center; align-items: center;
    width: fit-content !important; flex: unset !important; min-width: unset !important;
}}
[data-testid="column"] .stButton > button {{
    width: 50px !important; height: 40px !important;
    margin-bottom: 0 !important; font-size: 16px !important;
}}

/* 底部資訊框 */
.nav-footer {{
    height: {FOOTER_HEIGHT}px; min-height: {FOOTER_HEIGHT}px;
    background: white; border-radius: 12px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    text-align: center; color: black;
    box-sizing: border-box; padding: 10px; margin-top: 8px;
}}
</style>

<script>
// JS 策略：
// 1. 在每個選項按鈕渲染前，先用 st.markdown 插入一個帶 id 的 <script> marker
// 2. JS 找到 marker，往上找到對應的 stButton wrapper，打上 data-slot="nav-btn"
// 3. CSS 用 [data-slot="nav-btn"] 精確鎖定高度
(function() {{
    function tagSlots() {{
        document.querySelectorAll('script[data-nav-marker]').forEach(marker => {{
            // marker 的父鏈往上找到 [data-testid="stButton"]
            let el = marker.parentElement;
            for (let i = 0; i < 10 && el; i++) {{
                if (el.dataset && el.dataset.testid === 'stButton') {{
                    el.setAttribute('data-slot', 'nav-btn');
                    break;
                }}
                // 也找相鄰的下一個 stButton sibling
                el = el.parentElement;
            }}
        }});

        // 備用：直接找 key 含 btn_ 或 empty_ 的按鈕
        document.querySelectorAll('[data-testid="stButton"]').forEach(wrapper => {{
            const btn = wrapper.querySelector('button');
            if (!btn) return;
            const key = wrapper.closest('[data-stale]')?.getAttribute('key') || '';
            // 透過按鈕在 stVerticalBlock 內的位置判斷是否為選項按鈕
            // 選項按鈕的 parent 不含 stHorizontalBlock
            const inHoriz = wrapper.closest('[data-testid="stHorizontalBlock"]');
            if (!inHoriz && !wrapper.hasAttribute('data-slot')) {{
                // 排除分頁按鈕（分頁按鈕在 stHorizontalBlock 裡）
                // 這裡已排除，剩下的就是選項按鈕
                wrapper.setAttribute('data-slot', 'nav-btn');
            }}
        }});
    }}

    setTimeout(tagSlots, 200);
    new MutationObserver(tagSlots).observe(document.body, {{childList: true, subtree: true}});
}})();
</script>
""", unsafe_allow_html=True)

# ── 頂部標題 ──
st.markdown(f"""
<div class="nav-header">
    <h1>{current_name}</h1>
    <p>GPS: {current_pos[0]:.3f}, {current_pos[1]:.3f}</p>
</div>
""", unsafe_allow_html=True)

# ── 按鈕區（PAGE_SIZE 顆，不足補透明佔位） ──
for i in range(PAGE_SIZE):
    if i < len(current_items):
        loc = current_items[i]
        if st.button(loc["name"], key=f"btn_{i}", use_container_width=True):
            st.session_state.selected_loc = loc
            st.rerun()
    else:
        st.button("　", key=f"empty_{i}", disabled=True, use_container_width=True)

# ── 分頁列 ──
c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1, 0.4, 2])
with c2:
    if st.button("❮", key="prev"):
        st.session_state.page = (st.session_state.page - 1) % total_pages
        st.rerun()
with c3:
    st.markdown(f'<div class="page-text">{st.session_state.page + 1} / {total_pages}</div>',
                unsafe_allow_html=True)
with c4:
    if st.button("❯", key="next"):
        st.session_state.page = (st.session_state.page + 1) % total_pages
        st.rerun()

# ── 底部資訊 ──
def get_direction_text(bearing):
    dirs = [("↑","北","North"),("↗","東北","NE"),("→","東","East"),("↘","東南","SE"),
            ("↓","南","South"),("↙","西南","SW"),("←","西","West"),("↖","西北","NW")]
    return dirs[int((bearing + 22.5) / 45) % 8]

if st.session_state.selected_loc:
    loc  = st.session_state.selected_loc
    dist = geodesic(current_pos, loc["coords"]).kilometers
    phi1 = math.radians(current_pos[0])
    phi2 = math.radians(loc["coords"][0])
    dl   = math.radians(loc["coords"][1] - current_pos[1])
    bear = (math.degrees(math.atan2(
        math.sin(dl) * math.cos(phi2),
        math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dl)
    )) + 360) % 360
    arrow, zh, en = get_direction_text(bear)
    footer_content = f"""
        <div style="font-size:28px;font-weight:900;">{loc['name']}</div>
        <div style="font-size:28px;font-weight:900;color:red;margin:5px 0;">{arrow} {zh} {en}</div>
        <div style="font-size:16px;color:#555;">距離 {dist:.3f} km | 方位角 {bear:.1f}°</div>
    """
else:
    footer_content = '<div style="font-size:20px;font-weight:900;color:#888;">請選擇目的地</div>'

st.markdown(f'<div class="nav-footer">{footer_content}</div>', unsafe_allow_html=True)