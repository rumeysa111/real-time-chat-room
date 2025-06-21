# hybrid_server.py
import socket
import threading
import json
import time
from hybrid_protocol import ChatProtocol
from network_topology import NetworkTopology

class HybridChatServer:
    def __init__(self, tcp_port=12345, udp_port=12346):
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        
        # TCP soketi
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.bind(('0.0.0.0', tcp_port))
        
        # UDP soketi
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(('0.0.0.0', udp_port))
        
        # Bağlı istemcileri takip etme
        self.clients = {}  # {username: {"tcp_socket": socket, "udp_addr": (ip, port)}}
        self.lock = threading.Lock()
        
        # Topoloji verisi için
        self.topology = NetworkTopology()
        
        print(f"Sunucu başlatıldı. TCP port: {tcp_port}, UDP port: {udp_port}")
    
    def start(self):
        """Sunucuyu başlatır"""
        # TCP bağlantı dinleyicisi
        self.tcp_socket.listen(5)
        print("Bağlantılar bekleniyor...")
        
        # UDP dinleyici thread
        udp_thread = threading.Thread(target=self._handle_udp)
        udp_thread.daemon = True
        udp_thread.start()
        
        # TCP bağlantıları kabul etme
        while True:
            try:
                client_socket, addr = self.tcp_socket.accept()
                print(f"Yeni bağlantı: {addr}")
                
                # İstemci işleme thread'i
                client_thread = threading.Thread(target=self._handle_tcp_client, 
                                                args=(client_socket, addr))
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                print(f"Bağlantı hatası: {e}")
    
    def _handle_tcp_client(self, client_socket, addr):
        """TCP istemcisini işler"""
        username = None

        try:
            # Doğrulama mesajı bekle
            data = client_socket.recv(1024)
            message = ChatProtocol.decode(data)
            
            if message:
                print(f"[TCP ALINDI - SERVER] {json.dumps(message, indent=2, ensure_ascii=False)}")

            if message and message["type"] == ChatProtocol.MSG_AUTH:
                username = message["user"]

                with self.lock:
                    # İstemciyi kaydet
                    self.clients[username] = {
                        "tcp_socket": client_socket,
                        "udp_addr": None,  # UDP adresi henüz bilinmiyor
                        "last_seen": time.time()
                    }

                # Hoşgeldin mesajı gönder
                welcome = ChatProtocol.encode(
                    ChatProtocol.MSG_AUTH,
                    "SERVER",
                    f"Hoş geldin {username}! UDP port: {self.udp_port}"
                )
                client_socket.send(welcome)

                # Diğer kullanıcılara bildir
                self._broadcast_tcp(
                    ChatProtocol.MSG_JOIN,
                    "SERVER",
                    f"{username} sohbete katıldı",
                    exclude=username
                )

                # Mesajları işlemeye devam et
                while True:
                    data = client_socket.recv(1024)
                    if not data:
                        break

                    message = ChatProtocol.decode(data)
                    if message:
                        print(f"[TCP ALINDI - SERVER] {json.dumps(message, indent=2)}")
                    else:
                        continue

                    # Mesaj tipine göre işlem yap
                    if message["type"] == ChatProtocol.MSG_USERS:
                        # Kullanıcı listesini gönder
                        with self.lock:
                            users = list(self.clients.keys())

                        response = ChatProtocol.encode(
                            ChatProtocol.MSG_USERS,
                            "SERVER",
                            users
                        )
                        client_socket.send(response)

                    elif message["type"] == ChatProtocol.MSG_TOPO:
                        # İstemci topoloji verisi istedi
                        print(f"[TOPO] Topoloji isteği alındı: {username}")
                        topo_data = self.topology.get_topology_data()
                        print(f"[TOPO] Mevcut topoloji: {json.dumps(topo_data, indent=2)}")
                        
                        # Her istemci için geçici topoloji verisi oluştur
                        with self.lock:
                            for client_name, client_info in self.clients.items():
                                client_sock = client_info["tcp_socket"]
                                client_addr = client_sock.getpeername()
                                
                                print(f"[TOPO] Düğüm ekleniyor: {client_name}")
                                # Topolojiye düğüm ekle
                                self.topology.add_or_update_node(
                                    client_name,
                                    client_addr[0],
                                    client_addr[1]
                                )
                                
                                # Eğer UDP adresi varsa, topoloji bağlantıları oluştur
                                if client_info.get("udp_addr"):
                                    for other_name, other_info in self.clients.items():
                                        if client_name != other_name:
                                            print(f"[TOPO] Bağlantı ekleniyor: {client_name} -> {other_name}")
                                            # Rastgele bir kalite değeri (gerçek değer ping ile hesaplanmalı)
                                            quality = 50  # Varsayılan değer
                                            self.topology.update_connection_quality(
                                                client_name,
                                                other_name,
                                                quality
                                            )
                        
                        # Güncellenmiş topoloji verisini al
                        topo_data = self.topology.get_topology_data()
                        print(f"[TOPO] Güncellenmiş topoloji: {json.dumps(topo_data, indent=2)}")
                        
                        # Topoloji verisini gönder
                        response = ChatProtocol.encode(
                            ChatProtocol.MSG_TOPO,
                            "SERVER",
                            topo_data
                        )
                        client_socket.send(response)
                        print(f"[TOPO] Topoloji verisi gönderildi: {username}")

        except Exception as e:
            print(f"TCP istemci hatası: {e}")

        finally:
            # Temizlik
            if username:
                with self.lock:
                    if username in self.clients:
                        del self.clients[username]

                # Diğer kullanıcılara bildir
                self._broadcast_tcp(
                    ChatProtocol.MSG_LEAVE,
                    "SERVER",
                    f"{username} ayrıldı"
                )

            client_socket.close()

    
    def _handle_udp(self):
        """UDP mesajlarını işler"""
        print(f"UDP dinleyici başlatıldı, port: {self.udp_port}")

        while True:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                message = ChatProtocol.decode(data)

                if message:
                    print(f"[UDP ALINDI - SERVER] {json.dumps(message, indent=2, ensure_ascii=False)}")
                else:
                    continue

                username = message.get("user")

                # İlk UDP mesajında, istemcinin UDP adresini kaydet
                if username in self.clients:
                    with self.lock:
                        self.clients[username]["udp_addr"] = addr
                        self.clients[username]["last_seen"] = time.time()

                # Latency hesapla
                if "timestamp" in message:
                    try:
                        send_time = float(message["timestamp"])
                        latency = time.time() - send_time
                        self.topology.add_or_update_node(
                            username,
                            addr[0],
                            addr[1],
                            latency * 1000  # milisaniye cinsinden
                        )
                    except:
                        pass

                # Mesaj tipine göre işlem yap
                if message["type"] == ChatProtocol.MSG_CHAT:
                    msg_id = message["id"]

                    # Gönderene ACK yolla
                    ack = ChatProtocol.encode(
                        ChatProtocol.MSG_ACK,
                        "SERVER",
                        msg_id
                    )
                    self.udp_socket.sendto(ack, addr)

                    # Mesajı diğer istemcilere yayınla
                    self._broadcast_udp(message, exclude=username)
                
                elif message["type"] == ChatProtocol.MSG_DIRECT:
                    msg_id = message["id"]
                    recipient = message.get("recipient")

                    # Gönderene ACK yolla
                    ack = ChatProtocol.encode(
                        ChatProtocol.MSG_ACK,
                        "SERVER",
                        msg_id
                    )
                    self.udp_socket.sendto(ack, addr)

                    # Alıcıya mesajı ilet
                    if recipient and recipient in self.clients:
                        recipient_addr = self.clients[recipient].get("udp_addr")
                        if recipient_addr:
                            try:
                                self.udp_socket.sendto(data, recipient_addr)
                                print(f"[DIRECT] {username} -> {recipient}: {message.get('content')}")
                            except Exception as e:
                                print(f"[ERROR] Özel mesaj iletme hatası: {e}")
                
                elif message["type"] == ChatProtocol.MSG_PING:
                    # Ping mesajı alındı, PONG ile yanıt ver
                    print(f"[PING] Alındı: {username} kullanıcısından")
                    
                    # Topolojiyi güncelleyelim - kullanıcıyı ekle
                    self.topology.add_or_update_node(
                        username,
                        addr[0],  # IP adresi
                        addr[1],  # Port
                        0  # Başlangıç gecikmesi
                    )
                    
                    # Diğer kullanıcılarla bağlantı oluştur
                    with self.lock:
                        for other_name, other_info in self.clients.items():
                            if username != other_name:
                                # Varsayılan bağlantı kalitesi
                                quality = 50
                                self.topology.update_connection_quality(
                                    username, 
                                    other_name,
                                    quality
                                )
                    
                    # PONG yanıtı gönder
                    pong_response = ChatProtocol.encode(
                        ChatProtocol.MSG_PONG,
                        "SERVER",
                        message["id"]  # Orijinal mesaj ID'sini geri gönder
                    )
                    try:
                        self.udp_socket.sendto(pong_response, addr)
                        print(f"[PONG] Gönderildi: {username} kullanıcısına")
                    except Exception as e:
                        print(f"[PONG] Gönderme hatası: {e}")
                
                elif message["type"] == ChatProtocol.MSG_PONG:
                    print(f"[PONG] Alındı: {username} kullanıcısından")

            except Exception as e:
                print(f"UDP hatası: {e}")

    
    def _broadcast_tcp(self, msg_type, username, content, exclude=None):
        """TCP üzerinden tüm istemcilere mesaj yayınlar"""
        message = ChatProtocol.encode(msg_type, username, content)
        
        with self.lock:
            for client_name, client_info in self.clients.items():
                if exclude and client_name == exclude:
                    continue
                
                try:
                    client_info["tcp_socket"].send(message)
                except:
                    # Bu istemci bağlantısı kopmuş olabilir
                    # İstemci handler'ı bunu temizleyecek
                    pass
    
    def _broadcast_udp(self, message, exclude=None):
        """UDP üzerinden tüm istemcilere mesaj yayınlar"""
        data = json.dumps(message).encode()
        
        with self.lock:
            for client_name, client_info in self.clients.items():
                if exclude and client_name == exclude:
                    continue
                
                # UDP adresi kaydedilmiş mi kontrol et
                if client_info["udp_addr"]:
                    try:
                        self.udp_socket.sendto(data, client_info["udp_addr"])
                    except Exception as e:
                        print(f"UDP yayın hatası: {e}")

if __name__ == "__main__":
    server = HybridChatServer()
    server.start()