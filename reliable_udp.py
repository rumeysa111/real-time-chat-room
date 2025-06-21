import threading
import queue
import time
import logging
import socket
import json
from collections import deque

class ReliableUDP:
    """UDP üzerinde güvenilir mesajlaşma sağlayan sınıf"""
    
    def __init__(self, sock, window_size=5, timeout=1.0, max_retries=3):
        self.sock = sock
        self.window_size = window_size
        self.timeout = timeout
        self.max_retries = max_retries
        
        self.send_queue = queue.Queue()  # Gönderilecek mesajlar
        self.send_window = {}  # {msg_id: {"data": data, "addr": addr, "sent_time": time, "retries": count}}
        self.ack_events = {}  # {msg_id: threading.Event}
        
        self.recv_buffer = {}  # {(addr, seq): {"data": data, "time": time}}
        self.last_seq = {}  # {addr: last_seq}
        
        self.sequence_number = 0
        self.lock = threading.Lock()
        
        self.should_stop = threading.Event()
        self.sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self.sender_thread.start()
    
    def _get_next_sequence(self):
        """Sıradaki sıra numarasını döndürür"""
        with self.lock:
            seq = self.sequence_number
            self.sequence_number = (self.sequence_number + 1) % 65536  # 16-bit sıra numarası
            return seq
    
    def _sender_loop(self):
        """Mesaj gönderme döngüsü"""
        while not self.should_stop.is_set():
            try:
                # Pencere doluysa bekle
                if len(self.send_window) >= self.window_size:
                    # Herhangi bir ACK gelene veya timeout olana kadar bekle
                    timeout_event = threading.Event()
                    timeout_event.wait(0.1)  # Kısa süre bekle
                    continue
                
                # Sıradaki mesajı al (timeout ile blokla)
                try:
                    msg_data = self.send_queue.get(timeout=0.1)
                    if msg_data is None:
                        continue
                except queue.Empty:
                    continue
                
                msg_id, data, addr, sequence = msg_data
                
                # Bu mesaj için ACK bekleme event'i oluştur
                ack_event = threading.Event()
                with self.lock:
                    self.ack_events[msg_id] = ack_event
                    
                    # Mesajı pencereye ekle
                    self.send_window[msg_id] = {
                        "data": data,
                        "addr": addr,
                        "sent_time": time.time(),
                        "retries": 0,
                        "sequence": sequence
                    }
                
                # Mesajı gönder
                try:
                    self.sock.sendto(data, addr)
                except Exception as e:
                    logging.error(f"Mesaj gönderme hatası: {e}")
                    with self.lock:
                        del self.send_window[msg_id]
                        del self.ack_events[msg_id]
                    continue
                
                self.send_queue.task_done()
            
            except Exception as e:
                logging.error(f"Sender loop hatası: {e}")
            
            # Zamanaşımına uğramış mesajları kontrol et ve yeniden gönder
            self._check_timeouts()
    
    def _check_timeouts(self):
        """Zamanaşımına uğramış mesajları kontrol et ve yeniden gönder"""
        current_time = time.time()
        to_remove = []
        
        with self.lock:
            for msg_id, info in self.send_window.items():
                if current_time - info["sent_time"] > self.timeout:
                    # Zamanaşımı gerçekleşti
                    if info["retries"] < self.max_retries:
                        # Yeniden gönder
                        try:
                            self.sock.sendto(info["data"], info["addr"])
                            info["sent_time"] = current_time
                            info["retries"] += 1
                            logging.info(f"[{msg_id}] yeniden gönderiliyor. Deneme {info['retries']}/{self.max_retries}")
                        except Exception as e:
                            logging.error(f"Yeniden gönderme hatası: {e}")
                    else:
                        # Maksimum deneme sayısına ulaşıldı
                        logging.warning(f"[{msg_id}] mesajı başarısız oldu. Maksimum deneme sayısı aşıldı.")
                        to_remove.append(msg_id)
            
            # Başarısız mesajları temizle
            for msg_id in to_remove:
                if msg_id in self.send_window:
                    del self.send_window[msg_id]
                if msg_id in self.ack_events:
                    del self.ack_events[msg_id]
    
    def send_reliable(self, message, addr, msg_id=None):
        """Güvenilir bir şekilde mesaj gönderir"""
        if not msg_id:
            msg_id = f"msg_{int(time.time() * 1000)}"
        
        # Sıra numarası atama
        sequence = self._get_next_sequence()
        
        # Mesaja sıra numarası ekleme
        try:
            msg_dict = json.loads(message.decode())
            msg_dict["seq"] = sequence
            message = json.dumps(msg_dict).encode()
        except:
            # JSON değilse, ham veri olarak kabul et
            pass
        
        # Gönderme kuyruğuna ekle
        self.send_queue.put((msg_id, message, addr, sequence))
        
        # ACK bekleyici döndür
        return msg_id
    
    def process_ack(self, ack_msg, addr):
        """ACK mesajını işler"""
        try:
            msg_id = ack_msg.get("content")
            
            with self.lock:
                if msg_id in self.ack_events:
                    # ACK event'ini tetikle
                    self.ack_events[msg_id].set()
                    
                    # Pencereden kaldır
                    if msg_id in self.send_window:
                        del self.send_window[msg_id]
                    
                    # Event'i temizle
                    del self.ack_events[msg_id]
                    
                    return True
            
            return False
        except Exception as e:
            logging.error(f"ACK işleme hatası: {e}")
            return False
    
    def process_received(self, message, addr):
        """Alınan mesajı işler ve sıra kontrolü yapar"""
        try:
            # Sıra numarasını çıkar
            sequence = message.get("seq", 0)
            
            with self.lock:
                # Bu adres için son sıra numarasını kontrol et
                last_seq = self.last_seq.get(addr[0], -1)
                
                # İleri düzey sıra kontrolü
                if sequence <= last_seq:
                    # Yinelenen mesaj, yoksay
                    return None
                elif sequence > last_seq + 1:
                    # Sıra atlama var, tamponla
                    self.recv_buffer[(addr[0], sequence)] = {
                        "data": message,
                        "time": time.time()
                    }
                    return None
                else:
                    # Sıralı mesaj, işle
                    self.last_seq[addr[0]] = sequence
                    
                    # Tamponlanmış mesajları kontrol et ve işle
                    next_seq = sequence + 1
                    while (addr[0], next_seq) in self.recv_buffer:
                        # Tampondaki mesajı işle
                        buffered = self.recv_buffer[(addr[0], next_seq)]
                        del self.recv_buffer[(addr[0], next_seq)]
                        self.last_seq[addr[0]] = next_seq
                        next_seq += 1
                        # İşlenecek mesajları döndür
                        yield buffered["data"]
                    
                    # Tampon temizliği (eski mesajlar)
                    current_time = time.time()
                    old_entries = [k for k, v in self.recv_buffer.items() 
                                 if current_time - v["time"] > 30]  # 30 saniye
                    for k in old_entries:
                        del self.recv_buffer[k]
                    
                    # Asıl mesajı işle
                    return message
        except Exception as e:
            logging.error(f"Alınan mesaj işleme hatası: {e}")
            return None
    
    def stop(self):
        """Güvenli bir şekilde durdur"""
        self.should_stop.set()
        self.sender_thread.join(timeout=2.0)