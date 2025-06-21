# hybrid_protocol.py
import json
import time
import hashlib
import base64

class ChatProtocol:
    # Mesaj tipleri
    MSG_AUTH = "AUTH"        # Kullanıcı kimlik doğrulama (TCP)
    MSG_CHAT = "CHAT"        # Sohbet mesajı (UDP)
    MSG_ACK = "ACK"          # Mesaj alındı bildirimi (UDP)
    MSG_USERS = "USERS"      # Kullanıcı listesi (TCP)
    MSG_JOIN = "JOIN"        # Kullanıcı katıldı bildirimi (TCP)
    MSG_LEAVE = "LEAVE"      # Kullanıcı ayrıldı bildirimi (TCP)
    MSG_DIRECT = "DIRECT"    # Özel mesaj (UDP)
    MSG_FILE = "FILE"        # Dosya transferi (TCP)
    MSG_PING = "PING"        # Gecikme ölçümü (UDP)
    MSG_PONG = "PONG"        # Gecikme ölçümü yanıtı (UDP)
    MSG_TOPO = "TOPO"        # Topoloji bilgisi (TCP)
    
    @staticmethod
    def encode(msg_type, username, content, msg_id=None, sequence=None, recipient=None):
        """Mesajı JSON formatında kodlar"""
        if not msg_id:
            msg_id = f"{int(time.time() * 1000)}"
            
        message = {
            "type": msg_type,
            "id": msg_id,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "user": username,
            "content": content
        }
        
        # İsteğe bağlı alanlar
        if sequence is not None:
            message["seq"] = sequence
        
        if recipient is not None:
            message["recipient"] = recipient
        
        # Mesaj bütünlüğü için özet ekle
        message["checksum"] = ChatProtocol._generate_checksum(message)
        
        return json.dumps(message).encode()
    
    @staticmethod
    def decode(data):
        """Mesajı JSON formatından çözer"""
        try:
            message = json.loads(data.decode())
            
            # Mesaj bütünlüğünü kontrol et
            original_checksum = message.get("checksum")
            if original_checksum:
                # Checksum'ı geçici olarak kaldır
                message_copy = {k: v for k, v in message.items() if k != "checksum"}
                calculated_checksum = ChatProtocol._generate_checksum(message_copy)
                
                # Checksum'lar eşleşmiyorsa None döndür
                if original_checksum != calculated_checksum:
                    print(f"Checksum eşleşmedi: {original_checksum} != {calculated_checksum}")
                    return None
                    
            return message
        except Exception as e:
            print(f"Mesaj çözme hatası: {e}")
            return None
    
    @staticmethod
    def _generate_checksum(message):
        """Mesaj özeti oluşturur"""
        # Mesajı sıralı anahtar-değer çiftleri olarak hazırla
        message_str = json.dumps(message, sort_keys=True)
        # SHA-256 özet oluştur
        checksum = hashlib.sha256(message_str.encode()).digest()
        # Base64 olarak kodla ve kısalt
        return base64.b64encode(checksum).decode()[:12]