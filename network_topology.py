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
    
    def add_or_update_node(self, username, ip, port, latency=None):
        """Düğüm ekler veya günceller"""
        with self.lock:
            if username in self.nodes:
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
    
    def get_topology_data(self):
        """Topoloji verilerini döndürür"""
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