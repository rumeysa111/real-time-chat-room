import time
import threading
import json
import socket
import math

class NetworkTopology:
    def __init__(self):
        self.nodes = {}  # {username: {"ip": ip, "port": port, "latency": avg_latency}}
        self.connections = []  # [{"from": user1, "to": user2, "quality": quality}]
        self.lock = threading.Lock()
        self.inactive_timeout = 60  # 60 saniye boyunca görünmeyen düğümler inactive sayılacak
    
    def add_or_update_node(self, username, ip, port, latency=None):
        """Düğüm ekler veya günceller"""
        with self.lock:
            if username in self.nodes:
                # Düğüm zaten var, güncelle
                self.nodes[username]["last_seen"] = time.time()
                self.nodes[username]["ip"] = ip
                self.nodes[username]["port"] = port
                
                if latency is not None:
                    # Ortalama gecikmeyi güncelle
                    old_latency = self.nodes[username].get("latency", latency)
                    new_latency = (old_latency + latency) / 2
                    self.nodes[username]["latency"] = new_latency
                    print(f"[TOPO] Düğüm güncellendi: {username}, latency={new_latency:.2f}ms")
            else:
                self.nodes[username] = {
                    "ip": ip,
                    "port": port,
                    "latency": latency,
                    "last_seen": time.time()
                }
                print(f"[TOPO] Yeni düğüm eklendi: {username}, ip={ip}:{port}")

    def update_connection_quality(self, from_user, to_user, quality):
        """İki düğüm arasındaki bağlantı kalitesini günceller"""
        with self.lock:
            try:
                # Quality değerini sınırla (0-100)
                quality = max(0, min(100, float(quality)))
                
                # Mevcut bağlantıyı ara ve güncelle
                connection_found = False
                for conn in self.connections:
                    if (conn["from"] == from_user and conn["to"] == to_user) or \
                       (conn["from"] == to_user and conn["to"] == from_user):
                        # Ortalama değer yerine en güncel değeri kullan
                        conn["quality"] = quality
                        connection_found = True
                        print(f"[TOPO] Bağlantı güncellendi: {from_user} <-> {to_user}, quality={quality:.1f}%")
                        break
                
                # Bağlantı yoksa yeni ekle
                if not connection_found:
                    self.connections.append({
                        "from": from_user,
                        "to": to_user,
                        "quality": quality
                    })
                    print(f"[TOPO] Yeni bağlantı eklendi: {from_user} <-> {to_user}, quality={quality}%")
            except Exception as e:
                print(f"[ERROR] Bağlantı kalitesi güncelleme hatası: {e}")
    
    def clean_inactive_nodes(self):
        """Belirli bir süre görünmeyen düğümleri temizler"""
        with self.lock:
            current_time = time.time()
            inactive_nodes = []
            
            # İnaktif düğümleri belirle
            for username, node in list(self.nodes.items()):
                if current_time - node["last_seen"] > self.inactive_timeout:
                    inactive_nodes.append(username)
            
            # İnaktif düğümleri kaldır
            for username in inactive_nodes:
                del self.nodes[username]
                print(f"[TOPO] İnaktif düğüm kaldırıldı: {username}")
            
            # İnaktif düğümlerin bağlantılarını da kaldır
            if inactive_nodes:
                self.connections = [conn for conn in self.connections 
                                   if conn["from"] not in inactive_nodes and conn["to"] not in inactive_nodes]
                print(f"[TOPO] İnaktif düğümlerin {len(inactive_nodes)} bağlantısı kaldırıldı")
    
    def get_topology_data(self):
        """Topoloji verilerini döndürür"""
        # Önce inaktif düğümleri temizle
        self.clean_inactive_nodes()
        
        with self.lock:
            data = {
                "nodes": self.nodes,
                "connections": self.connections
            }
            print(f"[TOPO] Topoloji verisi oluşturuldu: {len(self.nodes)} düğüm, {len(self.connections)} bağlantı")
            return data
    
    def to_json(self):
        """Topoloji verilerini JSON formatında döndürür"""
        with self.lock:
            return json.dumps({
                "nodes": self.nodes,
                "connections": self.connections
            })