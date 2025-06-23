# hybrid_chat_client_fixed.py
import socket
import threading
import time
import json
import queue
from hybrid_protocol import ChatProtocol
from network_topology import NetworkTopology

class HybridChatClient:
    def __init__(self, server_ip="127.0.0.1", tcp_port=12345, udp_port=12346):
        self.server_ip = server_ip
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.on_direct_message = None
        # TCP soketi
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # UDP soketi
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(('0.0.0.0', 0))  # Otomatik port
        
        self.username = None
        self.connected = False
        self.pending_acks = {}  # {msg_id: event}
        self.lock = threading.Lock()  # Eklendi
        
        # Callback fonksiyonları
        self.on_message = None
        self.on_user_join = None
        self.on_user_leave = None
        self.on_user_list = None
        
        # Topoloji için ekle
        self.topology = NetworkTopology()
        self.on_topology_data = None
    
    def connect(self, username):
        """Sunucuya bağlanır"""
        self.username = username
        
        try:
            # TCP ile bağlan
            self.tcp_socket.connect((self.server_ip, self.tcp_port))
            
            # Doğrulama mesajı gönder
            auth_msg = ChatProtocol.encode(
                ChatProtocol.MSG_AUTH, 
                username, 
                "Bağlanıyor"
            )
            self.tcp_socket.send(auth_msg)
            
            # Yanıt bekle
            data = self.tcp_socket.recv(1024)
            response = ChatProtocol.decode(data)
            
            if response and response["type"] == ChatProtocol.MSG_AUTH:
                print(f"Sunucuya bağlanıldı: {response['content']}")
                self.connected = True
                
                # Dinleyici thread'leri başlat
                tcp_thread = threading.Thread(target=self._listen_tcp)
                tcp_thread.daemon = True
                tcp_thread.start()
                
                udp_thread = threading.Thread(target=self._listen_udp)
                udp_thread.daemon = True
                udp_thread.start()
                
                return True
            else:
                print("Doğrulama başarısız!")
                self.tcp_socket.close()
                return False
                
        except Exception as e:
            print(f"Bağlantı hatası: {e}")
            return False
    
    def disconnect(self):
        """Sunucudan bağlantıyı keser"""
        self.connected = False
        try:
            self.tcp_socket.close()
            self.udp_socket.close()
        except:
            pass
    
    def send_message(self, content):
        """Sohbet mesajı gönderir (UDP)"""
        if not self.connected:
            return False
        
        msg_id = f"{int(time.time() * 1000)}"
        message = ChatProtocol.encode(
            ChatProtocol.MSG_CHAT, 
            self.username, 
            content, 
            msg_id
        )
        
        # ACK için event oluştur
        ack_event = threading.Event()
        self.pending_acks[msg_id] = ack_event
        
        # Mesajı gönder
        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES):
            self.udp_socket.sendto(message, (self.server_ip, self.udp_port))
            
            # ACK için bekle
            if ack_event.wait(1.0):  # 1 saniye timeout
                del self.pending_acks[msg_id]
                return True
            
            print(f"Deneme {attempt + 1}/{MAX_RETRIES}...")
        
        # ACK alınamadı
        del self.pending_acks[msg_id]
        return False
    
    def send_direct_message(self, recipient, content):
        """Özel mesaj gönderir (UDP)"""
        if not self.connected:
            return False
        
        msg_id = f"{int(time.time() * 1000)}"
        message = ChatProtocol.encode(
            ChatProtocol.MSG_DIRECT, 
            self.username, 
            content, 
            msg_id,
            recipient=recipient
        )
        
        # ACK için event oluştur
        ack_event = threading.Event()
        self.pending_acks[msg_id] = ack_event
        
        # Mesajı gönder
        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES):
            self.udp_socket.sendto(message, (self.server_ip, self.udp_port))
            
            # ACK için bekle
            if ack_event.wait(1.0):  # 1 saniye timeout
                del self.pending_acks[msg_id]
                return True
            
            print(f"Deneme {attempt + 1}/{MAX_RETRIES}...")
        
        # ACK alınamadı
        del self.pending_acks[msg_id]
        return False
    
    def get_user_list(self):
        """Kullanıcı listesini ister (TCP)"""
        if not self.connected:
            return None
        
        request = ChatProtocol.encode(
            ChatProtocol.MSG_USERS, 
            self.username, 
            "Kullanıcı listesi"
        )
        self.tcp_socket.send(request)
        
        # Yanıt callback ile gelecek
    
    def request_topology(self, callback=None):
        """Topoloji verisi ister"""
        if not self.connected:
            return False
        
        # Callback'i kaydet
        if callback:
            self.on_topology_data = callback 
        self.ping_users()       
        # Topoloji isteği gönder
        request = ChatProtocol.encode(
            ChatProtocol.MSG_TOPO, 
            self.username, 
            "GET"
        )
        self.tcp_socket.send(request)
        return True
    
    def ping_users(self):
        """Tüm kullanıcılara ping gönderir"""
        if not self.connected:
            return False
        
        timestamp = str(time.time())
        print(f"[PING] Ping gönderiliyor... timestamp: {timestamp}")
        
        # Ping mesajı gönder
        ping = ChatProtocol.encode(
            ChatProtocol.MSG_PING,
            self.username,
            timestamp  # Timestamp
        )
        
        # UDP üzerinden gönder
        try:
            self.udp_socket.sendto(ping, (self.server_ip, self.udp_port))
            print(f"[PING] Ping gönderildi: {self.server_ip}:{self.udp_port}")
            return True
        except Exception as e:
            print(f"[PING] Ping gönderme hatası: {e}")
            return False
    
    def send_direct_ping(self, target_username):
        """Belirli bir kullanıcıya doğrudan ping gönderir"""
        if not self.connected or target_username == self.username:
            return False
        
        timestamp = str(time.time())
        
        # Hedef kullanıcı için ping mesajı
        direct_ping = ChatProtocol.encode(
            ChatProtocol.MSG_PING,
            self.username,
            timestamp,  # Timestamp
            recipient=target_username  # Hedef kullanıcı adı
        )        
        # Sunucu üzerinden UDP olarak gönder
        try:
            self.udp_socket.sendto(direct_ping, (self.server_ip, self.udp_port))
            print(f"[PING] Doğrudan ping gönderildi: {target_username}")
            return True
        except Exception as e:
            print(f"[PING] Doğrudan ping gönderme hatası: {e}")
            return False
    
    def ping_all_users(self):
        """Tüm kullanıcılara ping gönderir"""
        if not self.connected:
            return False
        
        # Önce sunucuya ping gönder
        self.ping_users()
        
        # Kullanıcı listesini iste
        self.get_user_list()
        
        # Bilinen kullanıcı listesi varsa kullan
        known_users = []
        try:
            # Topolojiden bilinen düğümleri al
            with self.topology.lock:
                known_users = list(self.topology.nodes.keys())
            
            # Kendimizi hariç tut
            if self.username in known_users:
                known_users.remove(self.username)
        except Exception as e:
            print(f"[ERROR] Kullanıcı listesi alma hatası: {e}")
        
        # Diğer kullanıcılara doğrudan ping gönder
        for user in known_users:
            self.send_direct_ping(user)
        
        print(f"[PING] {len(known_users)} kullanıcıya ping gönderildi")
        return True
    
    def _listen_tcp(self):
        """TCP mesajlarını dinler"""
        while self.connected:
            try:
                data = self.tcp_socket.recv(1024)
                if not data:
                    break
                
                message = ChatProtocol.decode(data)

                if message:
                    # Protokolü terminale yazdır
                    print(f"[TCP ALINDI - CLIENT] {json.dumps(message, indent=2, ensure_ascii=False)}")

                
                # Mesaj tipine göre işlem
                if message["type"] == ChatProtocol.MSG_JOIN:
                    if self.on_user_join:
                        self.on_user_join(message["content"])
                
                elif message["type"] == ChatProtocol.MSG_LEAVE:
                    if self.on_user_leave:
                        self.on_user_leave(message["content"])
                
                elif message["type"] == ChatProtocol.MSG_USERS:
                    if self.on_user_list:
                        self.on_user_list(message["content"])
                
                elif message["type"] == ChatProtocol.MSG_TOPO:
                    # Topoloji verisi
                    print(f"[TOPO] Topoloji verisi alındı: {json.dumps(message['content'], indent=2)}")
                    
                    # Önce kendi client topolojisini mesaja entegre et
                    client_topo = self.topology.get_topology_data()
                    server_topo = message['content']
                    
                    # SERVER düğümünü kendi topolojisine ekle
                    if "SERVER" in server_topo["nodes"]:
                        client_topo["nodes"]["SERVER"] = server_topo["nodes"]["SERVER"]
                    
                    # Sunucudan gelen bağlantıları entegre et
                    for conn in server_topo.get("connections", []):
                        conn_found = False
                        for client_conn in client_topo.get("connections", []):
                            if ((conn["from"] == client_conn["from"] and conn["to"] == client_conn["to"]) or 
                                (conn["from"] == client_conn["to"] and conn["to"] == client_conn["from"])):
                                conn_found = True
                                break
                        
                        if not conn_found:
                            client_topo["connections"].append(conn)
                    
                    # Birleştirilmiş topolojiyi kullan 
                    if self.on_topology_data:
                        self.on_topology_data(server_topo)  # server_topo kullan
                    else:
                        print("[TOPO] Uyarı: on_topology_data callback'i ayarlanmamış!")
                
            except Exception as e:
                print(f"TCP dinleme hatası: {e}")
                break
        
        self.connected = False
    
    def _listen_udp(self):
        """UDP mesajlarını dinler"""
        self.udp_socket.settimeout(0.5)  # Kısa timeout
        
        while self.connected:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                message = ChatProtocol.decode(data)
                
                if message:
                    print(f"[UDP ALINDI - CLIENT] {json.dumps(message, indent=2, ensure_ascii=False)}")
                
                if message["type"] == ChatProtocol.MSG_CHAT:
                    # Chat mesajı
                    if self.on_message:
                        self.on_message(
                            message["user"],
                            message["content"],
                            message["time"]
                        )
                
                elif message["type"] == ChatProtocol.MSG_ACK:
                    # ACK mesajı
                    msg_id = message["content"]
                    if msg_id in self.pending_acks:
                        self.pending_acks[msg_id].set()
                
                elif message["type"] == ChatProtocol.MSG_PING:
                    # Ping mesajına PONG ile cevap ver
                    pong = ChatProtocol.encode(
                        ChatProtocol.MSG_PONG,
                        self.username,
                        message["id"]  # Orijinal mesaj ID'sini geri gönder
                    )
                    try:
                        self.udp_socket.sendto(pong, addr)
                    except:
                        pass
                elif message["type"] == ChatProtocol.MSG_PONG:
                    try:
                        # Yanıt mesaj ID'si bizim gönderdiğimiz timestamp
                        ping_time = float(message["id"])
                        now = time.time()
                        
                        # Doğru latency hesaplaması
                        latency = max(0, (now - ping_time) * 1000)  # ms cinsinden, minimum 0
                        
                        print(f"[PONG] Alındı: {message['user']} latency={latency:.2f}ms")

                        if message["user"] != self.username:
                            # Topolojiye bağlantı kalitesi güncelle
                            quality = max(0, min(100, 100 - latency/10))  # Makul bir kalite değeri (0-100)
                            
                            self.topology.update_connection_quality(
                                self.username,
                                message["user"],
                                quality  # latency yerine quality kullan
                            )

                            # Düğüm bilgisi güncelle
                            self.topology.add_or_update_node(
                                message["user"],
                                addr[0],  # IP adresi
                                addr[1],  # Port
                                latency
                            )

                            # Topoloji GUI güncellemesi tetikle
                            if self.on_topology_data:
                                topo_data = self.topology.get_topology_data()
                                self.on_topology_data(topo_data)

                    except Exception as e:
                        print(f"[ERROR] PONG işleme hatası: {str(e)}")
                
                elif message["type"] == ChatProtocol.MSG_DIRECT:
                    # Özel mesaj
                    if message["recipient"] == self.username:
                        # Bana gelen özel mesaj
                        if self.on_direct_message:
                            self.on_direct_message(
                                message["user"],
                                message["content"],
                                message["time"],
                                is_direct=True
                            )
                        
                        # Mesajı aldığımızı bildir
                        ack = ChatProtocol.encode(
                            ChatProtocol.MSG_ACK,
                            self.username,
                            message["id"]
                        )
                        try:
                            self.udp_socket.sendto(ack, addr)
                        except:
                            pass
    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"UDP dinleme hatası: {e}")
