import tkinter as tk
from tkinter import ttk
import math
import colorsys
import time

class TopologyView:
    def __init__(self, master, width=400, height=300):
        self.master = master
        self.width = width
        self.height = height
        
        # Ana çerçeve
        self.frame = ttk.Frame(master)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Başlık ve zaman bilgisi
        self.header_frame = ttk.Frame(self.frame)
        self.header_frame.pack(fill=tk.X, expand=False, pady=(0, 5))
        
        self.title_label = ttk.Label(
            self.header_frame, 
            text="Ağ Topolojisi", 
            font=("Segoe UI", 12, "bold")
        )
        self.title_label.pack(side=tk.LEFT, pady=(0, 5))
        
        self.timestamp_label = ttk.Label(
            self.header_frame, 
            text="Son Güncelleme: -", 
            font=("Segoe UI", 8)
        )
        self.timestamp_label.pack(side=tk.RIGHT, pady=(0, 5))
        
        # Araç çubuğu
        self.toolbar = ttk.Frame(self.frame)
        self.toolbar.pack(fill=tk.X, expand=False, pady=(0, 5))
        
        # Ping düğmesi
        self.ping_button = ttk.Button(
            self.toolbar, 
            text="Tüm Düğümlere Ping Gönder",
            command=self.on_ping_all
        )
        self.ping_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.on_ping_all_callback = None  # Callback fonksiyonu
        
        # Bilgi etiketi
        self.info_label = ttk.Label(
            self.toolbar, 
            text="Düğüm Sayısı: 0, Bağlantı Sayısı: 0", 
            font=("Segoe UI", 8)
        )
        self.info_label.pack(side=tk.RIGHT)
        
        # Canvas
        self.canvas_frame = ttk.Frame(self.frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(
            self.canvas_frame, 
            width=width, 
            height=height, 
            bg="white"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Düğümler ve bağlantılar
        self.node_radius = 20
        self.nodes = {}  # {username: (x, y, canvas_id)}
        
        # Tooltip için
        self.current_tooltip = None
        self.canvas.bind("<Motion>", self.on_mouse_move)
        
        # Son güncelleme zamanı
        self.last_update = None
    
    def set_on_ping_all_callback(self, callback):
        """Ping düğmesi için callback fonksiyonu ayarla"""
        self.on_ping_all_callback = callback
    
    def on_ping_all(self):
        """Ping düğmesine tıklandığında çağrılır"""
        if self.on_ping_all_callback:
            self.on_ping_all_callback()
    
    def on_mouse_move(self, event):
        """Fare hareketi takibi için"""
        # Fare bir düğümün üzerinde mi kontrol et
        closest_node = None
        closest_distance = self.node_radius
        
        for username, (x, y, _) in self.nodes.items():
            distance = math.sqrt((event.x - x)**2 + (event.y - y)**2)
            if distance <= self.node_radius and (closest_node is None or distance < closest_distance):
                closest_node = username
                closest_distance = distance
        
        # Tooltip güncelle
        if closest_node:
            self.show_tooltip(closest_node, event.x, event.y)
        else:
            self.hide_tooltip()
    
    def show_tooltip(self, username, x, y):
        """Düğüm üzerinde tooltip göster"""
        if self.current_tooltip:
            self.canvas.delete(self.current_tooltip)
        
        # Tooltip metni
        text = f"Kullanıcı: {username}"
        self.current_tooltip = self.canvas.create_text(
            x + self.node_radius + 10, 
            y - self.node_radius - 5,
            text=text,
            anchor=tk.W,
            fill="#333333",
            font=("Segoe UI", 8),
            tags="tooltip"
        )
    
    def hide_tooltip(self):
        """Tooltip'i gizle"""
        if self.current_tooltip:
            self.canvas.delete(self.current_tooltip)
            self.current_tooltip = None
    
    def update_topology(self, topology_data):
        """Topoloji görünümünü günceller"""
        self.canvas.delete("all")
        self.nodes = {}
        
        # Son güncelleme zamanını kaydet
        self.last_update = time.time()
        self.timestamp_label.config(text=f"Son Güncelleme: {time.strftime('%H:%M:%S')}")
        
        # Düğümlerin pozisyonlarını hesapla
        nodes_data = topology_data.get("nodes", {})
        connections = topology_data.get("connections", [])
        
        # Bilgi etiketini güncelle
        self.info_label.config(text=f"Düğüm Sayısı: {len(nodes_data)}, Bağlantı Sayısı: {len(connections)}")
        
        if not nodes_data:
            # Topoloji boşsa bilgi mesajı göster
            self.canvas.create_text(
                self.width / 2,
                self.height / 2,
                text="Topoloji verisi bulunamadı",
                fill="gray"
            )
            return
        
        # Düğüm pozisyonlarını hesapla ve çiz
        positions = self._calculate_node_positions(list(nodes_data.keys()))
        
        # Önce bağlantıları çiz (düğümlerin altında kalsın)
        for conn in connections:
            from_user = conn.get("from")
            to_user = conn.get("to")
            quality = conn.get("quality", 0)
            
            if from_user in positions and to_user in positions:
                from_x, from_y = positions[from_user]
                to_x, to_y = positions[to_user]
                self._draw_connection(from_x, from_y, to_x, to_y, quality)
        
        # Sonra düğümleri çiz
        for username, pos in positions.items():
            x, y = pos
            node_data = nodes_data.get(username, {})
            latency = node_data.get("latency", 0)
            
            # Düğümü çiz
            self._draw_node(username, x, y, latency)
    
    def _calculate_node_positions(self, usernames):
        """Düğümlerin daire üzerindeki pozisyonlarını hesaplar"""
        positions = {}
        
        count = len(usernames)
        if count == 0:
            return positions
        
        # Tek düğüm varsa merkezde olsun
        if count == 1:
            positions[usernames[0]] = (self.width / 2, self.height / 2)
            return positions
        
        # Çoklu düğümler için daire üzerinde yerleştir
        radius = min(self.width, self.height) * 0.35
        center_x = self.width / 2
        center_y = self.height / 2
        
        for i, username in enumerate(usernames):
            angle = i * (2 * math.pi / count)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            positions[username] = (x, y)
        
        return positions
    
    def _draw_node(self, username, x, y, latency=0):
        """Düğüm çizer"""
        # Gecikme süresine göre renk belirle
        if latency == 0:
            color = "#1877f2"  # Varsayılan mavi
        else:
            # Düşük gecikme: yeşil, yüksek gecikme: kırmızı
            normalized_latency = min(1.0, latency / 1000)  # 1 saniye veya fazlası için maksimum kırmızı
            hue = 0.33 * (1 - normalized_latency)  # 0.33 = yeşil, 0 = kırmızı
            r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
            color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        
        # Düğüm dairesi
        node_id = self.canvas.create_oval(
            x - self.node_radius, 
            y - self.node_radius,
            x + self.node_radius, 
            y + self.node_radius,
            fill=color,
            outline=""
        )
        
        # Kullanıcı adı
        self.canvas.create_text(
            x,
            y + self.node_radius + 10,
            text=username,
            fill="#333333",
            font=("Segoe UI", 8)
        )
        
        # Gecikme bilgisi
        if latency > 0:
            self.canvas.create_text(
                x,
                y,
                text=f"{latency:.0f}ms",
                fill="white",
                font=("Segoe UI", 7, "bold")
            )
        
        # Düğüm pozisyonunu kaydet
        self.nodes[username] = (x, y, node_id)
    
    def _draw_connection(self, x1, y1, x2, y2, quality=0):
        """İki düğüm arasındaki bağlantıyı çizer"""
        # Kaliteye göre renk belirle
        normalized_quality = max(0, min(100, quality)) / 100
        hue = 0.33 * normalized_quality  # 0.33 = yeşil, 0 = kırmızı
        r, g, b = colorsys.hsv_to_rgb(hue, 0.7, 0.7)
        color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        
        # Kaliteye göre çizgi kalınlığını belirle
        thickness = 1 + int(normalized_quality * 2)
        
        # Çizgiyi çiz
        line_id = self.canvas.create_line(
            x1, y1, x2, y2,
            fill=color,
            width=thickness,
            dash=(5, 2) if quality < 50 else None,
            tags=("connection",)
        )
        
        # Kalite etiketi
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        self.canvas.create_text(
            mid_x,
            mid_y,
            text=f"{quality:.0f}%",
            fill="#333333",
            font=("Segoe UI", 7),
            tags=("connection_label",)
        )
        
        return line_id
