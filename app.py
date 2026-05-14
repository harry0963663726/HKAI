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
    /* 問題1：下移一個 selectbox 高度（約 50px）*/
    padding-top: 60px !important;
}}

/* 問題4：完全隱藏 Streamlit 工具列、頁尾、右下角標誌 */
header, footer,
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
#MainMenu,
.viewerBadge_container__1QSob,
.styles_viewerBadge__1yB5_,
[class*="viewerBadge"],
iframe[title="streamlit_components"] {{
    visibility: hidden !important;
    display: none !important;
    height: 0 !important;
    width: 0 !important;
}}

[data-testid="stVerticalBlock"] > div {{ gap: 0rem !important; }}

/* 問題1：selectbox 往下推（用 margin-top）*/
[data-testid="stSelectbox"] {{
    margin-top: 0px !important;
}}

/* 頂部標題 */
.nav-header {{
    background: white; border-radius: 10px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    margin-bottom: 10px; padding: 10px 5px;
}}
.nav-header h1 {{ font-size: 40px; color: black; margin: 0; font-weight: 900; }}
.nav-header p  {{ font-size: 20px; color: gray; margin: 5px 0 0 0; font-family: monospace; }}

/* 選項按鈕（JS 會標上 data-slot="nav-btn"） */
[data-slot="nav-btn"] {{
    height: {BTN_HEIGHT}px !important;
    min-height: {BTN_HEIGHT}px !important;
    max-height: {BTN_HEIGHT}px !important;
    overflow: hidden !important;
    margin-bottom: {BTN_GAP}px !important;
    padding: 0 !important;
}}
[data-slot="nav-btn"] > button {{
    height: {BTN_HEIGHT}px !important;
    min-height: {BTN_HEIGHT}px !important;
    background: #1E2329 !important;
    border: 1px solid #3E454D !important;
    color: white !important;
    font-size: 40px !important;
    border-radius: 6px !important;
    width: 100% !important;
    margin: 0 !important;
    box-sizing: border-box !important;
    /* 問題2：取消 active/focus 變色，按下後立即恢復 */
    transition: none !important;
    -webkit-tap-highlight-color: transparent !important;
}}
[data-slot="nav-btn"] > button:active,
[data-slot="nav-btn"] > button:focus,
[data-slot="nav-btn"] > button:focus-visible {{
    background: #1E2329 !important;
    border: 1px solid #3E454D !important;
    color: white !important;
    outline: none !important;
    box-shadow: none !important;
}}
[data-slot="nav-btn"] > button:disabled {{
    background: transparent !important;
    border: none !important;
    color: transparent !important;
    pointer-events: none !important;
}}

/* 問題3：分頁列 — 三個元素同一行置中緊靠 */
.pager-row {{
    display: flex !important;
    flex-direction: row !important;
    justify-content: center !important;
    align-items: center !important;
    gap: 10px !important;
    margin: 8px 0 !important;
    width: 100% !important;
}}
.pager-row [data-testid="stButton"] > button,
.pager-row .stButton > button {{
    width: 50px !important;
    height: 40px !important;
    font-size: 18px !important;
    font-weight: 900 !important;
    background: #1E2329 !important;
    border: 1px solid #3E454D !important;
    color: white !important;
    border-radius: 6px !important;
    padding: 0 !important;
    margin: 0 !important;
    transition: none !important;
    -webkit-tap-highlight-color: transparent !important;
}}
.pager-row [data-testid="stButton"] > button:active,
.pager-row [data-testid="stButton"] > button:focus {{
    background: #1E2329 !important;
    outline: none !important;
    box-shadow: none !important;
}}
.page-text {{
    color: white; font-weight: 900; font-size: 18px;
    white-space: nowrap; line-height: 40px;
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
(function() {{
    // 選項按鈕標記（排除分頁按鈕）
    function tagNavBtns() {{
        document.querySelectorAll('[data-testid="stButton"]').forEach(wrapper => {{
            if (wrapper.closest('[data-testid="stHorizontalBlock"]')) return;
            if (wrapper.closest('.pager-row')) return;
            wrapper.setAttribute('data-slot', 'nav-btn');
        }});
    }}

    // 問題3：把分頁列的三個 Streamlit 元件收進 .pager-row flex 容器
    function buildPagerRow() {{
        const pagerDiv = document.querySelector('.pager-row');
        if (!pagerDiv) return;
        // 找 pagerDiv 之後的兄弟 stHorizontalBlock
        const horiz = pagerDiv.nextElementSibling;
        if (!horiz) return;
        // 已整理過就跳過
        if (pagerDiv.dataset.built) return;

        // 把 horiz 內的按鈕和頁碼文字移進 pagerDiv
        const children = Array.from(horiz.children);
        children.forEach(c => pagerDiv.appendChild(c));
        horiz.style.display = 'none';
        pagerDiv.dataset.built = '1';
    }}

    function run() {{
        tagNavBtns();
        // buildPagerRow();  // 備用，目前分頁用純 HTML 渲染
    }}

    setTimeout(run, 200);
    new MutationObserver(run).observe(document.body, {{childList: true, subtree: true}});
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

# ── 選項按鈕區（JS 標記 data-slot="nav-btn"） ──
for i in range(PAGE_SIZE):
    if i < len(current_items):
        loc = current_items[i]
        if st.button(loc["name"], key=f"btn_{i}", use_container_width=True):
            st.session_state.selected_loc = loc
            st.rerun()
    else:
        st.button("　", key=f"empty_{i}", disabled=True, use_container_width=True)

# ── 問題3：分頁列用純 HTML + st.button 並排放在同一個 st.columns ──
# 用 columns 讓三個元素在同一行，比例讓按鈕緊靠頁碼
_, lc, mc, rc, _ = st.columns([3, 1, 2, 1, 3])
with lc:
    if st.button("❮", key="prev"):
        st.session_state.page = (st.session_state.page - 1) % total_pages
        st.rerun()
with mc:
    st.markdown(
        f'<div class="page-text" style="text-align:center;">'
        f'{st.session_state.page + 1} / {total_pages}</div>',
        unsafe_allow_html=True
    )
with rc:
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