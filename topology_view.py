import tkinter as tk
from tkinter import ttk
import math
import colorsys

class TopologyView:
    def __init__(self, master, width=400, height=300):
        self.master = master
        self.width = width
        self.height = height
        
        # Ana çerçeve
        self.frame = ttk.Frame(master)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Başlık
        ttk.Label(self.frame, text="Ağ Topolojisi", font=("Segoe UI", 12, "bold")).pack(pady=(0, 10))
        
        # Canvas
        self.canvas = tk.Canvas(self.frame, width=width, height=height, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Düğümler ve bağlantılar
        self.node_radius = 20
        self.nodes = {}  # {username: (x, y, canvas_id)}
    
    def update_topology(self, topology_data):
        """Topoloji görünümünü günceller"""
        self.canvas.delete("all")
        self.nodes = {}
        
        # Düğümlerin pozisyonlarını hesapla
        nodes_data = topology_data.get("nodes", {})
        connections = topology_data.get("connections", [])
        
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
        
        for i, (username, pos) in enumerate(positions.items()):
            x, y = pos
            node_data = nodes_data.get(username, {})
            latency = node_data.get("latency", 0)
            
            # Düğümü çiz
            self._draw_node(username, x, y, latency)
        
        # Bağlantıları çiz
        for conn in connections:
            from_user = conn.get("from")
            to_user = conn.get("to")
            quality = conn.get("quality", 0)
            
            if from_user in self.nodes and to_user in self.nodes:
                from_x, from_y, _ = self.nodes[from_user]
                to_x, to_y, _ = self.nodes[to_user]
                self._draw_connection(from_x, from_y, to_x, to_y, quality)
    
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
        self.canvas.create_line(
            x1, y1, x2, y2,
            fill=color,
            width=thickness,
            dash=(5, 2) if quality < 50 else None
        )