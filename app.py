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

# 定義全局常量
PAGE_SIZE = 5       # 每頁顯示的地點數量
BTN_HEIGHT = 50     # 地點按鈕的高度
FOOTER_HEIGHT = 150 # 底部資訊卡的高度

# ==========================================
# 1. 核心邏輯功能
# ==========================================

def send_to_led(name, distance, angle):
    url = "http://192.168.14.46:18011/api/control"
    payload = {
        "data": {
            "target": name, 
            "dist": f"{distance:.3f}km", 
            "angle": f"{angle:.1f}°"
        }
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print("發送成功！")
        else:
            print(f"發送失敗，錯誤碼：{response.status_code}")
    except Exception as e:
        print(f"連線伺服器出錯：{e}")

def calculate_bearing(start_pos, end_pos):
    phi1 = math.radians(start_pos[0])
    phi2 = math.radians(end_pos[0])
    dl = math.radians(end_pos[1] - start_pos[1])
    x = math.sin(dl) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - (
        math.sin(phi1) * math.cos(phi2) * math.cos(dl)
    )
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def get_direction_text(bearing):
    dirs = [
        ("↑", "北", "N"), ("↗", "東北", "NE"), ("→", "東", "E"), ("↘", "東南", "SE"),
        ("↓", "南", "S"), ("↙", "西南", "SW"), ("←", "西", "W"), ("↖", "西北", "NW")
    ]
    return dirs[int((bearing + 22.5) / 45) % 8]

# ==========================================
# 2. 設定檔載入
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

if "page" not in st.session_state: st.session_state.page = 0
if "selected_loc" not in st.session_state: st.session_state.selected_loc = None

# ==========================================
# 3. 視覺樣式與 CSS 客製化區塊
# ==========================================

st.markdown(f"""
<style>
    /* [全域禁止選取] */
    /* * 代表選取所有標籤，確保無論是 div、按鈕還是純文字都無法被長按或選取 */
    *, html, body, [data-testid="stAppViewContainer"], .white-card, .page-text, button, p, div, h1, span {{
        user-select: none !important;           /* 禁止使用者選取文字 (標準屬性) */
        -webkit-user-select: none !important;   /* 禁止使用者選取文字 (Safari/Chrome 引擎) */
        -webkit-touch-callout: none !important; /* 禁止 iOS 長按彈出系統選單 (如複製、分享) */
        -moz-user-select: none !important;      /* 禁止使用者選取文字 (Firefox 引擎) */
        -ms-user-select: none !important;       /* 禁止使用者選取文字 (IE/Edge 引擎) */
    }}

    /* [隱藏原生 UI 組件] */
    /* 隱藏頁首、工具欄、頁尾、裝飾條、APP 狀態圖示等 Streamlit 內建元素 */
    [data-testid="stHeader"], [data-testid="stToolbar"], footer, #MainMenu, 
    [data-testid="stDecoration"], [class*="viewerBadge"], [data-testid="stStatusWidget"] {{
        display: none !important; /* 強制不顯示 */
    }}

    /* [主容器底色與滾動控制] */
    html, body, [data-testid="stAppViewContainer"] {{ 
        background-color: black !important; /* 設定背景為純黑 */
        overflow-x: hidden !important;     /* 禁止水平滾動條出現 */
    }}
    
    /* [手機版顯示範圍優化] */
    .block-container {{ 
        max-width: 500px !important;    /* 限制最大寬度，模擬手機比例 */
        padding: 40px 15px !important;  /* 設定上下 40px、左右 15px 的內邊距 */
    }}

    /* [白色卡片通用樣式] */
    .white-card {{
        background-color: white !important;   /* 設定背景為純白 */
        color: black !important;             /* 文字顏色為黑 */
        border-radius: 10px !important;      /* 設定圓角 10 像素 */
        padding: 15px;                       /* 內部留白 15 像素 */
        margin-bottom: 12px;                 /* 與下方元素的間距 */
        text-align: center;                  /* 文字置中 */
        border: 1px solid silver !important; /* 設定銀色細邊框 */
    }}

    /* [下拉選單(Selectbox)輸入框修正] */
    [data-testid="stSelectbox"] input {{
        caret-color: transparent !important; /* 隱藏輸入游標 */
        color: transparent !important;       /* 隱藏輸入中的文字內容 */
        pointer-events: none !important;     /* 禁止點擊與觸發輸入行為 */
    }}
    
    /* [下拉選單按鈕外殼] */
    [data-testid="stSelectbox"] div[role="button"] {{
        background-color: white !important;   /* 背景白色 */
        color: black !important;             /* 文字黑色 */
        border-radius: 10px !important;      /* 圓角 10 像素 */
        height: 48px !important;             /* 固定高度 */
        border: 1px solid silver !important; /* 銀色邊框 */
        margin-bottom: 12px !important;      /* 下方間距 */
        cursor: pointer !important;          /* 滑鼠游標顯示為手指 */
    }}
    
    /* [下拉選單選取後的文字呈現] */
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
        color: black !important;        /* 文字黑色 */
        font-weight: bold !important;   /* 加粗字體 */
        font-size: 18px !important;     /* 字體大小 */
    }}

    /* [下拉選單彈出容器禁止選取] */
    [data-baseweb="popover"], [role="listbox"], [role="option"] {{
        user-select: none !important;         /* 禁止選取彈出選項中的文字 */
        -webkit-user-select: none !important; /* Safari 引擎禁止選取 */
    }}

    /* [地點列表按鈕基礎樣式] */
    [data-slot="nav-btn"] button {{
        height: {BTN_HEIGHT}px !important;              /* 使用 Python 變數設定高度 */
        background-color: white !important;            /* 背景白色 */
        color: black !important;                      /* 文字黑色 */
        border: none !important;                      /* 移除預設邊框 */
        border-left: 1px solid silver !important;     /* 左邊框銀色 */
        border-right: 1px solid silver !important;    /* 右邊框銀色 */
        border-bottom: 1px solid gainsboro !important;/* 底線顏色 (較淺的銀) */
        border-radius: 0 !important;                  /* 移除預設圓角 */
        font-size: 20px !important;                   /* 字體大小 */
        font-weight: bold !important;                /* 字體加粗 */
        transition: none !important;                  /* 移除點擊動畫縮放效果 */
    }}
    
    /* [列表第一個按鈕] */
    [data-slot="nav-btn"]:first-of-type button {{ 
        border-radius: 10px 10px 0 0 !important; /* 僅保留上方圓角 */
        border-top: 1px solid silver !important; /* 補回最上方的邊框 */
    }}
    
    /* [列表最後一個按鈕] */
    [data-slot="nav-btn"]:last-of-type button {{ 
        border-radius: 0 0 10px 10px !important;  /* 僅保留下方圓角 */
        border-bottom: 1px solid silver !important; /* 補回最下方的邊框 */
    }}

    /* [分頁控制列容器] */
    [data-testid="stHorizontalBlock"] {{ 
        display: flex !important;           /* 啟動彈性佈局 */
        flex-direction: row !important;      /* 強制橫向排列 */
        flex-wrap: nowrap !important;        /* 絕對不准換行 */
        width: 100% !important;              /* 寬度佔滿 */
        background-color: transparent !important; /* 透明背景 */
        margin: 20px 0 !important;           /* 上下外邊距 20px */
        padding: 0 !important;               /* 移除內邊距 */
        align-items: center !important;      /* 垂直置中 */
    }}
    
    /* [分頁列中的每一欄] */
    [data-testid="stHorizontalBlock"] > div {{ 
        flex: 1 1 auto !important; /* 根據內容自動伸縮 */
        min-width: 0 !important;   /* 防止內容撐開導致換行 */
    }}

    /* [分頁翻頁按鈕 (< 與 >)] */
    [data-testid="stHorizontalBlock"] [data-testid="stButton"] button {{
        background-color: white !important;   /* 背景白色 */
        color: black !important;             /* 文字黑色 */
        border: 1px solid silver !important; /* 銀色邊框 */
        border-radius: 10px !important;      /* 圓角 10 像素 */
        font-weight: 50 !important;          /* 字體權重 (對應你要求的粗細) */
        font-size: 30px !important;          /* 符號放大 */
        height: 50px !important;             /* 固定高度 */
        width: 100% !important;              /* 寬度佔滿欄位 */
    }}

    /* [分頁頁碼文字] */
    .page-text {{ 
        color: white !important;      /* 文字白色 */
        font-weight: bold;           /* 加粗 */
        font-size: 20px;             /* 字體大小 */
        text-align: center;          /* 文字居中 */
        line-height: 50px;           /* 行高與按鈕一致，確保垂直居中 */
        white-space: nowrap;         /* 禁止換行 */
    }}

    /* [按鈕互動保護] */
    /* 確保按鈕在點擊(active)、聚焦(focus)或懸停(hover)時，外觀不變，防止手機點擊變色 */
    [data-testid="stButton"] button:active,
    [data-testid="stButton"] button:focus,
    [data-testid="stButton"] button:hover {{ 
        background-color: white !important; 
        color: black !important; 
        box-shadow: none !important; /* 移除外陰影 */
        outline: none !important;    /* 移除聚焦線 */
    }}

    /* [標題與頁尾自定義類別] */
    .nav-header h1 {{ color: black; margin: 0; font-size: 32px; font-weight: 900; }}
    .nav-footer {{ 
        height: {FOOTER_HEIGHT}px;         /* 使用變數設定高度 */
        display: flex; 
        flex-direction: column;            /* 垂直排列內部資訊 */
        justify-content: center;           /* 垂直居中內容 */
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. 畫面渲染與交互
# ==========================================

selected_cat = st.selectbox("分類", categories, label_visibility="collapsed")
filtered_locations = all_locs if selected_cat == "全部" else [l for l in all_locs if l["category"] == selected_cat]

st.markdown(
    f'<div class="white-card nav-header"><h1>{current_name}</h1>'
    f'<p style="color:black; margin:0; font-size:14px;">座標: {current_pos[0]:.4f}, {current_pos[1]:.4f}</p></div>', 
    unsafe_allow_html=True
)

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
        st.button(" ", key=f"empty_{i}", disabled=True, use_container_width=True)

col_prev, col_num, col_next = st.columns([1, 1.5, 1])
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

if st.session_state.selected_loc:
    t = st.session_state.selected_loc
    d_km = geodesic(current_pos, t["coords"]).kilometers
    b_deg = calculate_bearing(current_pos, t["coords"])
    arr, zh_dir, en_dir = get_direction_text(b_deg)
    
    st.markdown(f"""
        <div class="white-card nav-footer">
            <div style="font-size:26px; font-weight:bold; color:black;">{t['name']}</div>
            <div style="font-size:28px; color:red; font-weight:bold; margin:8px 0;">
                {arr} {zh_dir} {en_dir}
            </div>
            <div style="font-size:16px; color:black; font-weight:bold;">
                距離: {d_km:.3f} 公里(Km) | 方位: {b_deg:.1f}°
            </div>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(
        '<div class="white-card nav-footer"><div style="color:black; font-weight:bold; font-size:20px;">'
        '請選擇目的地</div></div>', 
        unsafe_allow_html=True
    )