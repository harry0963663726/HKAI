# -*- coding: utf-8 -*-
import collections
if not hasattr(collections, 'Mapping'):
    import collections.abc
    collections.Mapping = collections.abc.Mapping
    collections.MutableMapping = collections.abc.MutableMapping

import tkinter as tk
from tkinter import ttk
import configparser
import os
from geopy.distance import geodesic
import math

class GoogleStyleNavigationUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Light Navigation")
        self.root.geometry("450x850") 
        
        # --- 色彩定義：全面使用英文名稱 ---
        self.COLOR_BG = "white"
        self.COLOR_HEADER_BG = "white"
        self.COLOR_TITLE_TEXT = "black"
        self.COLOR_SUB_TEXT = "dim gray"
        self.COLOR_BTN_BG = "whitesmoke"
        self.COLOR_BTN_TEXT = "black"
        self.COLOR_PRIMARY = "royalblue"
        self.COLOR_INFO_BG = "ghostwhite"
        self.COLOR_SEP = "lightgray"
        self.COLOR_BTN_HOVER = "gainsboro"

        self.root.configure(bg=self.COLOR_BG) 

        # --- 初始化變數 ---
        self.all_locations = []       
        self.filtered_locations = []  
        self.categories = ["全部"]    
        self.current_position = (0.0, 0.0)
        self.current_location_name = "未讀取位置" 
        self.page_index = 0
        self.page_size = 7
        self.selected_category = tk.StringVar(value="全部")
        
        # --- 載入設定檔 ---
        self.load_config()

        # --- UI 組件佈置 ---
        # 1. Header (標題區) - 改為直接顯示目前位置與座標
        self.header_frame = tk.Frame(self.root, bg=self.COLOR_HEADER_BG, pady=25)
        self.header_frame.pack(fill="x")
        
        # 直接用原本的標題位置顯示路燈名稱
        self.header_title = tk.Label(
            self.header_frame, 
            text=f"{self.current_location_name}", 
            fg=self.COLOR_TITLE_TEXT, 
            bg=self.COLOR_HEADER_BG, 
            font=("Microsoft JhengHei", 18, "bold")
        )
        self.header_title.pack()
        
        # 顯示座標
        self.pos_info = tk.Label(
            self.header_frame, 
            text=f"經緯度：{self.current_position[0]:.3f}, {self.current_position[1]:.3f}", 
            fg=self.COLOR_SUB_TEXT, 
            bg=self.COLOR_HEADER_BG, 
            font=("Arial", 10)
        )
        self.pos_info.pack(pady=(5, 0))

        # 2. 分類選擇區
        self.filter_frame = tk.Frame(self.root, bg=self.COLOR_BG, pady=10)
        self.filter_frame.pack(fill="x")
        
        self.cat_menu = ttk.Combobox(self.filter_frame, textvariable=self.selected_category, 
                                     values=self.categories, state="readonly", font=("Microsoft JhengHei", 10))
        self.cat_menu.pack(padx=40, fill="x")
        self.cat_menu.bind("<<ComboboxSelected>>", self.on_category_change)

        # 3. 按鈕容器 (核心選擇區)
        self.menu_frame = tk.Frame(self.root, bg=self.COLOR_BG)
        self.menu_frame.pack(fill="both", expand=True, padx=40)
        self.buttons = []

        # 4. 分頁控制區
        self.page_control_frame = tk.Frame(self.root, bg=self.COLOR_BG, pady=10)
        self.page_control_frame.pack(fill="x")

        self.page_inner_frame = tk.Frame(self.page_control_frame, bg=self.COLOR_BG)
        self.page_inner_frame.pack(anchor="center")

        self.prev_btn = tk.Button(self.page_inner_frame, text="❮", font=("Arial", 18), bg=self.COLOR_BG, fg=self.COLOR_PRIMARY, bd=0, command=self.prev_page)
        self.prev_btn.pack(side="left", padx=8)

        self.page_label = tk.Label(self.page_inner_frame, text="1 / 1", fg=self.COLOR_SUB_TEXT, bg=self.COLOR_BG, font=("Arial", 11))
        self.page_label.pack(side="left", padx=8)

        self.next_btn = tk.Button(self.page_inner_frame, text="❯", font=("Arial", 18), bg=self.COLOR_BG, fg=self.COLOR_PRIMARY, bd=0, command=self.next_page)
        self.next_btn.pack(side="left", padx=8)

        # 5. 下方資訊顯示卡片 (固定高度)
        self.separator = tk.Frame(self.root, height=1, bg=self.COLOR_SEP)
        self.separator.pack(fill="x")
        self.info_frame = tk.Frame(self.root, height=160, bg=self.COLOR_INFO_BG)
        self.info_frame.pack_propagate(False)
        self.info_frame.pack(fill="x", side="bottom")
        
        self.result_label = tk.Label(
            self.info_frame, 
            text="請選擇目的地\nPlease select a destination", 
            fg=self.COLOR_SUB_TEXT, bg=self.COLOR_INFO_BG,
            font=("Microsoft JhengHei", 12),
            padx=40, pady=22, justify="left", anchor="nw"
        )
        self.result_label.pack(fill="both", expand=True)

        self.on_category_change()

    def load_config(self):
        """讀取 config.ini 資訊"""
        config = configparser.ConfigParser()
        if os.path.exists('config.ini'):
            config.read('config.ini', encoding='utf-8')
            if 'Settings' in config:
                self.current_location_name = config.get('Settings', 'current_location', fallback='未命名路燈')
                lat = config.getfloat('Settings', 'current_lat', fallback=25.035)
                lon = config.getfloat('Settings', 'current_lon', fallback=121.567)
                self.current_position = (lat, lon)
            
            if 'Locations' in config:
                for name in config['Locations']:
                    val = config['Locations'][name]
                    try:
                        parts = [p.strip() for p in val.split(',')]
                        lat, lon = float(parts[0]), float(parts[1])
                        cat = parts[2] if len(parts) > 2 else "未分類"
                        self.all_locations.append({"name": name.upper(), "coords": (lat, lon), "category": cat})
                        if cat not in self.categories: self.categories.append(cat)
                    except: continue
        
        if not self.all_locations:
            self.all_locations = [{"name": "DEFAULT", "coords": (25.0, 121.0), "category": "未分類"}]

    def on_category_change(self, event=None):
        cat = self.selected_category.get()
        if cat == "全部":
            self.filtered_locations = self.all_locations
        else:
            self.filtered_locations = [l for l in self.all_locations if l["category"] == cat]
        self.page_index = 0
        self.refresh_menu()

    def refresh_menu(self):
        """刷新清單，若地點不足則填充空白框"""
        for btn in self.buttons: btn.destroy()
        self.buttons = []
        
        total_items = len(self.filtered_locations)
        tp = max(1, math.ceil(total_items / self.page_size))
        start = self.page_index * self.page_size
        
        for i in range(self.page_size):
            item_idx = start + i
            if item_idx < total_items:
                loc = self.filtered_locations[item_idx]
                btn = tk.Button(self.menu_frame, text=loc["name"], font=("Microsoft JhengHei", 12),
                    bg=self.COLOR_BTN_BG, fg=self.COLOR_BTN_TEXT, bd=0, relief="flat", height=2,
                    command=lambda l=loc: self.select_location(l))
                btn.pack(fill="x", pady=5)
                btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=self.COLOR_BTN_HOVER))
                btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=self.COLOR_BTN_BG))
                self.buttons.append(btn)
            else:
                # 空選項框：確保高度與按鈕一致 (約 52 像素)
                placeholder = tk.Frame(self.menu_frame, bg=self.COLOR_BG, height=52)
                placeholder.pack_propagate(False)
                placeholder.pack(fill="x", pady=5)
                self.buttons.append(placeholder)
        
        self.page_label.config(text=f"{self.page_index + 1} / {tp}")

    def prev_page(self):
        tp = max(1, math.ceil(len(self.filtered_locations) / self.page_size))
        self.page_index = (self.page_index - 1) % tp
        self.refresh_menu()

    def next_page(self):
        tp = max(1, math.ceil(len(self.filtered_locations) / self.page_size))
        self.page_index = (self.page_index + 1) % tp
        self.refresh_menu()

    def select_location(self, loc):
        """核心計算與結果顯示"""
        dist_km = geodesic(self.current_position, loc["coords"]).kilometers
        bearing = self.calculate_bearing(self.current_position[0], self.current_position[1], 
            loc["coords"][0], loc["coords"][1])
        arrow, dir_zh, dir_en = self.get_direction_text(bearing)

        display_text = (
            f"{loc['name']}\n"
            f"{arrow} {dir_zh} {dir_en} ({bearing:.1f}°)\n"
            f"距離：{dist_km:.3f} 公里(Km)\n"
        )
        self.result_label.config(text=display_text, fg=self.COLOR_PRIMARY)

    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_lambda = math.radians(lon2 - lon1)
        y = math.sin(delta_lambda) * math.cos(phi2)
        x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    def get_direction_text(self, bearing):
        directions = [
            ("↑", "北", "North"), ("↗", "東北", "NE"), ("→", "東", "East"), ("↘", "東南", "SE"),
            ("↓", "南", "South"), ("↙", "西南", "SW"), ("←", "西", "West"), ("↖", "西北", "NW")
        ]
        return directions[int((bearing + 22.5) / 45) % 8]

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam') 
    app = GoogleStyleNavigationUI(root)
    root.mainloop()