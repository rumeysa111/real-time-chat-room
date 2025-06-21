import tkinter as tk
import json
from tkinter import scrolledtext, simpledialog, ttk
import threading
from hybrid_chat_client import HybridChatClient
import time
from datetime import datetime
from topology_view import TopologyView

class ModernChatGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Hibrit Chat")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Renk şeması
        self.colors = {
            "bg": "#f0f2f5",
            "sidebar": "#e9eaed",
            "primary": "#1877f2",
            "secondary": "#3a3b3c",
            "text": "#050505",
            "text_light": "#65676b",
            "input_bg": "#ffffff",
            "my_message": "#dcf8c6",
            "other_message": "#ffffff",
            "my_message_text": "#000000",
            "other_message_text": "#000000",
            "status": "#42b72a"
        }
        
        # İstemci oluştur
        self.client = HybridChatClient()
        
        # Callback'leri ayarla
        self.client.on_message = self.on_message
        self.client.on_user_join = self.on_user_join
        self.client.on_user_leave = self.on_user_leave
        self.client.on_user_list = self.on_user_list
        self.client.on_direct_message = self.on_direct_message
        
        # Oturum durumu
        self.is_logged_in = False

        self.protocol_logs = []  # Protokol mesajlarını burada saklarız

        
        # GUI elemanları
        self.create_widgets()
        
        # Kullanıcı adı al ve bağlan
        self.login()
        
        # Özel sohbet pencereleri için sözlük
        self.private_chats = {}  # {username: PrivateChatWindow}

        self.root.mainloop()
    
    def create_widgets(self):
        # Ana frame
        self.main_frame = tk.Frame(self.root, bg=self.colors["bg"])
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sol panel (sohbet alanı)
        self.chat_frame = tk.Frame(self.main_frame, bg=self.colors["bg"])
        self.chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Sohbet başlık çubuğu
        self.chat_header = tk.Frame(self.chat_frame, bg=self.colors["input_bg"], height=50)
        self.chat_header.pack(fill=tk.X, pady=(0, 10))
        
        self.header_title = tk.Label(
            self.chat_header, 
            text="Hibrit Chat Odası", 
            font=("Segoe UI", 14, "bold"),
            bg=self.colors["input_bg"], 
            fg=self.colors["text"]
        )
        self.header_title.pack(side=tk.LEFT, padx=15, pady=10)
        
        self.connection_status = tk.Label(
            self.chat_header, 
            text="•", 
            font=("Segoe UI", 24),
            bg=self.colors["input_bg"], 
            fg=self.colors["text_light"]
        )
        self.connection_status.pack(side=tk.RIGHT, padx=15)
        
        # Mesaj alanı (kaydırma çubuğu ile)
        self.messages_frame = tk.Frame(self.chat_frame, bg=self.colors["bg"])
        self.messages_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas ve scrollbar ile kaydırılabilir mesaj alanı
        self.canvas = tk.Canvas(self.messages_frame, bg=self.colors["bg"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.messages_frame, orient="vertical", command=self.canvas.yview)
        
        self.messages_container = tk.Frame(self.canvas, bg=self.colors["bg"])
        self.messages_container_id = self.canvas.create_window((0, 0), window=self.messages_container, anchor="nw", width=self.canvas.winfo_width())
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.messages_container.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Mesaj giriş alanı
        self.input_frame = tk.Frame(self.chat_frame, bg=self.colors["bg"], height=60)
        self.input_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.msg_input = tk.Entry(
            self.input_frame, 
            font=("Segoe UI", 11),
            bg=self.colors["input_bg"],
            fg=self.colors["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#cccccc",
            highlightcolor=self.colors["primary"]
        )
        self.msg_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=8, padx=(0, 10))
        self.msg_input.bind("<Return>", self.send_message)
        
        # Gönder butonu
        self.send_btn = tk.Button(
            self.input_frame, 
            text="Gönder", 
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["primary"],
            fg="white",
            relief=tk.FLAT,
            padx=15,
            command=self.send_message,
            cursor="hand2"
        )
        self.send_btn.pack(side=tk.RIGHT, ipady=8)
        
        # Sağ panel (kullanıcı listesi)
        self.sidebar_frame = tk.Frame(self.main_frame, bg=self.colors["sidebar"], width=200)
        self.sidebar_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        
        # Panel genişliğini koru
        self.sidebar_frame.pack_propagate(False)
        
        # Kullanıcılar başlığı
        tk.Label(
            self.sidebar_frame, 
            text="Aktif Kullanıcılar", 
            font=("Segoe UI", 12, "bold"),
            bg=self.colors["sidebar"], 
            fg=self.colors["text"]
        ).pack(fill=tk.X, padx=10, pady=10)
        
        # Kullanıcı listesi
        self.users_frame = tk.Frame(self.sidebar_frame, bg=self.colors["sidebar"])
        self.users_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Yenile butonu
        self.refresh_btn = tk.Button(
            self.sidebar_frame, 
            text="Kullanıcıları Yenile", 
            font=("Segoe UI", 10),
            bg=self.colors["primary"],
            fg="white",
            relief=tk.FLAT,
            padx=5,
            pady=5,
            command=self.refresh_users,
            cursor="hand2"
        )
        self.refresh_btn.pack(fill=tk.X, padx=10, pady=10)
        
        # Topoloji görüntüleme düğmesi
        self.topo_btn = tk.Button(
            self.sidebar_frame,
            text="Ağ Topolojisini Göster",
            font=("Segoe UI", 10),
            bg=self.colors["primary"],
            fg="white",
            relief=tk.FLAT,
            padx=5,
            pady=5,
            command=self.show_topology,
            cursor="hand2"
        )
        self.topo_btn.pack(fill=tk.X, padx=10, pady=(0, 5))
        # Protocol Göster butonu
        self.protocol_btn = tk.Button(
            self.sidebar_frame,
            text="Protocol Göster",
            font=("Segoe UI", 10),
            bg=self.colors["primary"],
            fg="white",
            relief=tk.FLAT,
            padx=5,
            pady=5,
            command=self.show_protocol_log,
            cursor="hand2"
        )
        self.protocol_btn.pack(fill=tk.X, padx=10, pady=(0, 5))

        # Sağ tık menüsü için
        self.user_menu = tk.Menu(self.root, tearoff=0)
        self.user_menu.add_command(label="Özel Mesaj Gönder", command=self.send_direct_message_selected)

    
    def on_frame_configure(self, event=None):
        """Mesaj alanı boyutu değiştiğinde scrollbar'ı güncelle"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_configure(self, event=None):
        """Canvas boyutu değiştiğinde içerik genişliğini güncelle"""
        # İçerik genişliğini canvas genişliğine ayarla
        if event:
            canvas_width = event.width
            self.canvas.itemconfig(self.messages_container_id, width=canvas_width)
    
    def login(self):
        """Kullanıcı girişi diyalog kutusu"""
        username = simpledialog.askstring("Giriş", "Kullanıcı adınız:")
        if not username:
            self.root.destroy()
            return
        
        # Bağlantı için thread başlat
        def connect():
            self.connection_status.config(fg="#f39c12")  # Bağlanıyor (sarı)
            
            if self.client.connect(username):
                self.is_logged_in = True
                self.connection_status.config(fg=self.colors["status"])  # Bağlandı (yeşil)
                self.header_title.config(text=f"Hibrit Chat - {username}")
                self.add_system_message(f"{username} olarak bağlandınız")
                self.refresh_users()
                
                # Otomatik ping göndermek için
                self.start_ping_timer()
            else:
                self.connection_status.config(fg="#e74c3c")  # Bağlantı hatası (kırmızı)
                self.add_system_message("Bağlantı hatası! Lütfen daha sonra tekrar deneyin.")
        
        threading.Thread(target=connect).start()

    def start_ping_timer(self):
        """Düzenli aralıklarla ping gönderir"""
        def ping_loop():
            if self.is_logged_in:
                self.client.ping_users()
                # Her 10 saniyede bir ping gönder
                self.root.after(10000, ping_loop)
        
        # İlk ping'i başlat
        ping_loop()
    
    def send_message(self, event=None):
        """Mesaj gönderme işlemi"""
        if not self.is_logged_in:
            return
            
        message = self.msg_input.get().strip()
        if not message:
            return
        
        self.msg_input.delete(0, tk.END)
        self.log_protocol("UDP GÖNDERİLDİ", {
            "type": "CHAT",
            "user": self.client.username,
            "content": message
        })

        
        # Gönderme işlemi için thread başlat
        def send():
            success = self.client.send_message(message)
            if success:
                # Mesaj başarıyla gönderildi
                current_time = time.strftime("%H:%M:%S")
                self.add_my_message(message, current_time)
            else:
                self.add_system_message("Mesaj gönderilemedi! Bağlantınızı kontrol edin.")
        
        threading.Thread(target=send).start()
    
    def refresh_users(self):
        """Kullanıcı listesini yenileme"""
        if self.is_logged_in:
            self.client.get_user_list()
    
    def add_my_message(self, content, timestamp=None):
        """Kendi mesajımı ekle"""
        if not timestamp:
            timestamp = time.strftime("%H:%M:%S")
            
        # Mesaj konteyneri
        message_frame = tk.Frame(self.messages_container, bg=self.colors["bg"])
        message_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Mesaj balonu içeren frame
        bubble_frame = tk.Frame(message_frame, bg=self.colors["bg"])
        bubble_frame.pack(side=tk.RIGHT)
        
        # Mesaj içeriği
        message_content = tk.Label(
            bubble_frame,
            text=content,
            font=("Segoe UI", 10),
            bg=self.colors["my_message"],
            fg=self.colors["my_message_text"],
            justify=tk.LEFT,
            wraplength=400,
            padx=10,
            pady=8
        )
        message_content.pack(fill=tk.X)
        
        # Zaman etiketi
        time_label = tk.Label(
            bubble_frame,
            text=timestamp,
            font=("Segoe UI", 7),
            bg=self.colors["bg"],
            fg=self.colors["text_light"]
        )
        time_label.pack(side=tk.RIGHT, padx=5, pady=(0, 2))
        
        # Scroll'u aşağı kaydır
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)
    
    def add_other_message(self, username, content, timestamp=None):
        """Başka bir kullanıcının mesajını ekle"""
        if not timestamp:
            timestamp = time.strftime("%H:%M:%S")
            
        # Mesaj konteyneri
        message_frame = tk.Frame(self.messages_container, bg=self.colors["bg"])
        message_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Mesaj balonu içeren frame
        bubble_frame = tk.Frame(message_frame, bg=self.colors["bg"])
        bubble_frame.pack(side=tk.LEFT)
        
        # Kullanıcı adı
        username_label = tk.Label(
            bubble_frame,
            text=username,
            font=("Segoe UI", 8, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["primary"]
        )
        username_label.pack(anchor=tk.W, padx=5)
        
        # Mesaj içeriği
        message_content = tk.Label(
            bubble_frame,
            text=content,
            font=("Segoe UI", 10),
            bg=self.colors["other_message"],
            fg=self.colors["other_message_text"],
            justify=tk.LEFT,
            wraplength=400,
            padx=10,
            pady=8
        )
        message_content.pack(fill=tk.X)
        
        # Zaman etiketi
        time_label = tk.Label(
            bubble_frame,
            text=timestamp,
            font=("Segoe UI", 7),
            bg=self.colors["bg"],
            fg=self.colors["text_light"]
        )
        time_label.pack(side=tk.LEFT, padx=5, pady=(0, 2))
        
        # Scroll'u aşağı kaydır
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)
    
    def add_system_message(self, content):
        """Sistem mesajı ekle"""
        # Mesaj konteyneri
        message_frame = tk.Frame(self.messages_container, bg=self.colors["bg"])
        message_frame.pack(fill=tk.X, pady=5)
        
        # Sistem mesajı
        system_label = tk.Label(
            message_frame,
            text=content,
            font=("Segoe UI", 9, "italic"),
            bg=self.colors["bg"],
            fg=self.colors["text_light"]
        )
        system_label.pack(pady=2)
        
        # Scroll'u aşağı kaydır
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)
    
    def update_user_list(self, users):
        """Kullanıcı listesini güncelle"""
        # Kullanıcı listesini temizle
        for widget in self.users_frame.winfo_children():
            widget.destroy()
            
        # Kullanıcıları ekle
        for user in users:
            if user == self.client.username or user == "SERVER":
                continue  # Kendimizi veya sunucuyu listelemeyelim
            
            user_frame = tk.Frame(self.users_frame, bg=self.colors["sidebar"])
            user_frame.pack(fill=tk.X, pady=4, padx=2)
            
            # Ana kullanıcı çerçevesi
            user_info_frame = tk.Frame(user_frame, bg=self.colors["sidebar"])
            user_info_frame.pack(fill=tk.X, expand=True)
            
            # Kullanıcı durumu göstergesi
            status_indicator = tk.Label(
                user_info_frame, 
                text="•", 
                font=("Segoe UI", 14), 
                fg=self.colors["status"],
                bg=self.colors["sidebar"]
            )
            status_indicator.pack(side=tk.LEFT, padx=(0, 5))
            
            # Kullanıcı adı
            username_label = tk.Label(
                user_info_frame, 
                text=user, 
                font=("Segoe UI", 10),
                bg=self.colors["sidebar"],
                fg=self.colors["text"],
                anchor=tk.W
            )
            username_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Sağ tıklama ile özel menü
            username_label.bind("<Button-3>", lambda event, username=user: self.show_user_menu(event, username))
            
            # Özel mesaj butonu
            dm_btn = tk.Button(
                user_info_frame,
                text="DM",
                font=("Segoe UI", 7),
                bg="#9c27b0",  # Mor
                fg="white",
                relief=tk.FLAT,
                padx=5,
                pady=1,
                cursor="hand2",
                command=lambda u=user: self.get_or_create_private_chat(u)  # Bu satırı değiştirdik
            )
            dm_btn.pack(side=tk.RIGHT, padx=(0, 5))

    # Kullanıcıya sağ tıklama
    def show_user_menu(self, event, username):
        self.selected_user = username
        self.user_menu.post(event.x_root, event.y_root)

    # Callback fonksiyonları
    def on_message(self, username, content, timestamp):
        """Mesaj alındığında çağrılır"""
        # Timestamp formatını dönüştür
        try:
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            formatted_time = dt.strftime("%H:%M:%S")
        except:
            formatted_time = timestamp
            
        # Diğer kullanıcıdan gelen mesajı ekle
        # Diğer kullanıcıdan gelen mesajı ekle
        self.add_other_message(username, content, timestamp)
        
        # Debug (JSON içeriği)
        debug_info = f"[DEBUG] {username} mesaj gönderdi: {content}"
        self.add_system_message(debug_info)
    
    def on_user_join(self, message):
        """Kullanıcı katıldığında çağrılır"""
        self.add_system_message(message)
        self.refresh_users()
    
    def on_user_leave(self, message):
        """Kullanıcı ayrıldığında çağrılır"""
        self.add_system_message(message)
        self.refresh_users()
    
    def on_user_list(self, users):
        """Kullanıcı listesi geldiğinde çağrılır"""
        self.update_user_list(users)
        self.log_protocol("TCP ALINDI", {
            "type": "USERS",
            "user": "SERVER",
            "content": users
        })

    def on_direct_message(self, username, content, timestamp, is_direct=True):
        """Özel mesaj alındığında çağrılır"""
        try:
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            formatted_time = dt.strftime("%H:%M:%S")
        except:
            formatted_time = timestamp
        
        # Debug
        self.log_protocol("UDP ALINDI", {
            "type": "DIRECT",
            "user": username,
            "recipient": self.client.username,
            "content": content
        })
        
        # Eğer bu kullanıcıyla özel sohbet penceresi yoksa, bildirim göster
        if username not in self.private_chats or not self.private_chats[username].window.winfo_exists():
            self.add_system_message(f"🔔 {username} kullanıcısından özel mesaj aldınız!")
        
        # Özel sohbet penceresini göster ve mesajı ekle
        chat_window = self.get_or_create_private_chat(username)
        chat_window.receive_message(content, formatted_time)

    def log_protocol(self, direction, message):
        """Gelen/giden protokol mesajlarını JSON formatında saklar"""
        import json
        formatted = f"[{direction}] {json.dumps(message, indent=2, ensure_ascii=False)}"
        self.protocol_logs.append(formatted)

    
    def show_topology(self):
        """Ağ topolojisini görüntüler"""
        import json  # json modülünü ekleyin
        if not self.is_logged_in:
            return
            
        # Topoloji penceresi
        topo_window = tk.Toplevel(self.root)
        topo_window.title("Ağ Topolojisi")
        topo_window.geometry("700x600")
        topo_window.transient(self.root)
        topo_window.protocol("WM_DELETE_WINDOW", lambda: self.close_topology_window(topo_window))
        
        # Topoloji görünümü
        topo_view = TopologyView(topo_window, width=680, height=500)
        
        # Debug bilgisi etiketi
        debug_frame = ttk.Frame(topo_window)
        debug_frame.pack(fill=tk.X, pady=5)
        
        debug_label = ttk.Label(debug_frame, text="Topoloji bilgisi bekleniyor...", foreground="blue")
        debug_label.pack(side=tk.LEFT, padx=10)
        
        # Otomatik yenileme seçeneği ve süre seçici
        control_frame = ttk.Frame(debug_frame)
        control_frame.pack(side=tk.RIGHT, padx=10)
        
        auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_cb = ttk.Checkbutton(
            control_frame, 
            text="Otomatik Yenile", 
            variable=auto_refresh_var,
            onvalue=True,
            offvalue=False
        )
        auto_refresh_cb.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(control_frame, text="Yenileme Sıklığı:").pack(side=tk.LEFT)
        refresh_options = ["3 sn", "5 sn", "10 sn", "30 sn"]
        refresh_var = tk.StringVar(value="5 sn")
        refresh_combo = ttk.Combobox(
            control_frame,
            values=refresh_options,
            textvariable=refresh_var,
            width=6,
            state="readonly"
        )
        refresh_combo.pack(side=tk.LEFT, padx=5)
        
        # Callback fonksiyonu
        def on_topology_data(data):
            try:
                topo_view.update_topology(data)
                node_count = len(data.get("nodes", {}))
                conn_count = len(data.get("connections", []))
                debug_label.config(text=f"Topoloji: {node_count} düğüm, {conn_count} bağlantı")
                
                # Debug amaçlı topoloji verisini yazdır
                print(f"[DEBUG] Alınan topoloji verisinin içeriği: {json.dumps(data, indent=2)}")
            except Exception as e:
                print(f"[ERROR] Topoloji güncellenirken hata: {str(e)}")
    
        # Topoloji penceresine başvuruyu sakla
        self.topo_window = topo_window
        self.client.on_topology_data = on_topology_data
        
        # Güncelleme düğmesi
        update_frame = ttk.Frame(topo_window, padding=10)
        update_frame.pack(fill=tk.X)
        
        # Yenileme düğmesi
        update_btn = ttk.Button(
            update_frame,
            text="Topolojiyi Güncelle",
            command=lambda: self.request_topology()
        )
        update_btn.pack(side=tk.LEFT, pady=5, padx=5)
        
        # Ping gönderme düğmesi
        ping_btn = ttk.Button(
            update_frame,
            text="Ping Gönder (Sunucu)",
            command=self.send_ping
        )
        ping_btn.pack(side=tk.LEFT, pady=5, padx=5)
        
        # Tüm Kullanıcılara Ping düğmesi
        ping_all_btn = ttk.Button(
            update_frame,
            text="Tüm Kullanıcılara Ping",
            command=lambda: self.send_ping_all_users()
        )
        ping_all_btn.pack(side=tk.LEFT, pady=5, padx=5)
        
        # Düzenli güncelleme fonksiyonu
        def refresh_topology():
            if not topo_window.winfo_exists():
                return
                
            if auto_refresh_var.get():
                # Seçilen süreye göre yenileme sıklığını belirle
                interval_text = refresh_var.get()
                if interval_text == "3 sn":
                    interval = 3000
                elif interval_text == "10 sn":
                    interval = 10000
                elif interval_text == "30 sn":
                    interval = 30000
                else:
                    interval = 5000  # Varsayılan 5 sn
                
                # Tüm kullanıcılara ping gönder
                self.send_ping_all_users()
                
                # Topoloji verisini iste
                self.root.after(500, self.request_topology)
                
                # Bir sonraki yenileme için zamanla
                self.root.after(interval, refresh_topology)
        
        # İlk yükleme
        self.send_ping()  # Önce sunucuya ping gönder
        self.root.after(1000, self.send_ping_all_users)  # Sonra tüm kullanıcılara ping gönder
        self.root.after(1500, self.request_topology)  # Topoloji verisi iste
        
        # Düzenli güncelleme başlat
        self.root.after(5000, refresh_topology)

    def close_topology_window(self, window):
        """Topoloji penceresini kapatır"""
        # Callback'i temizle
        self.client.on_topology_data = None
        window.destroy()
    
    def send_ping(self):
        """Tüm kullanıcılara ping gönderir"""
        if not self.is_logged_in:
            return
        
        if self.client.ping_users():
            self.add_system_message("Ping gönderildi. Topoloji bilgisi güncelleniyor...")
        else:
            self.add_system_message("Ping gönderilemedi! Bağlantınızı kontrol edin.")

    def send_ping_all_users(self):
        """Tüm kullanıcılara ping gönderir"""
        if not self.is_logged_in:
            return
        
        if self.client.ping_all_users():
            self.add_system_message("Tüm kullanıcılara ping gönderildi. Topoloji bilgisi güncelleniyor...")
        else:
            self.add_system_message("Ping gönderilemedi! Bağlantınızı kontrol edin.")

    def show_protocol_log(self):
        """Protocol mesajlarını gösteren pencere"""
        log_window = tk.Toplevel(self.root)
        log_window.title("Protokol Mesajları")
        log_window.geometry("700x500")

        text_area = tk.Text(log_window, wrap=tk.WORD, font=("Courier", 9))
        text_area.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(text_area)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_area.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=text_area.yview)

        for entry in self.protocol_logs:
            text_area.insert(tk.END, entry + "\n\n")
    
    def request_topology(self, view=None):
        """Sunucudan topoloji verisi ister"""
        if not self.is_logged_in:
            return
        
        # Topoloji verisi iste
        if self.client.request_topology():
            self.add_system_message("Topoloji verisi istendi...")
        else:
            self.add_system_message("Topoloji verisi isteği başarısız!")

    def send_direct_message_selected(self):
        """Seçili kullanıcıya özel mesaj gönder"""
        if not hasattr(self, "selected_user") or not self.selected_user:
            return
        
        if self.selected_user == self.client.username:
            self.add_system_message("Kendinize özel mesaj gönderemezsiniz.")
            return
        
        # Direkt özel sohbet penceresini aç
        self.get_or_create_private_chat(self.selected_user)

    def send_direct_message(self, recipient, content):
        """Özel mesaj gönderme"""
        if not self.is_logged_in:
            return
        
        # Özel sohbet penceresini al veya oluştur
        chat_window = self.get_or_create_private_chat(recipient)
        
        # Mesajı giriş alanına ekle ve gönder
        if content:
            chat_window.msg_input.insert(0, content)
            chat_window.send_message()

    def get_or_create_private_chat(self, recipient):
        """Özel sohbet penceresini alır veya oluşturur"""
        if recipient in self.private_chats and self.private_chats[recipient].window.winfo_exists():
            # Mevcut pencereyi öne getir
            window = self.private_chats[recipient].window
            window.deiconify()  # Minimize edilmişse geri getir
            window.lift()  # Öne getir
            return self.private_chats[recipient]
        
        # Yeni pencere oluştur
        chat_window = PrivateChatWindow(self.root, self.client.username, recipient, self.client)
        self.private_chats[recipient] = chat_window
        return chat_window

    def close_private_chat(self, recipient):
        """Özel sohbet penceresini kapatır"""
        if recipient in self.private_chats:
            del self.private_chats[recipient]

# chat_gui.py dosyasına ekleyin

class PrivateChatWindow:
    def __init__(self, parent, username, recipient, client):
        """Özel sohbet penceresi"""
        self.parent = parent
        self.username = username
        self.recipient = recipient
        self.client = client
        self.message_history = []  # Mesaj geçmişi
        
        # Pencere oluştur
        self.window = tk.Toplevel(parent)
        self.window.title(f"Özel Sohbet: {recipient}")
        self.window.geometry("500x400")
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Pencere içeriği
        self.create_widgets()
        
    def create_widgets(self):
        """Pencere içeriğini oluştur"""
        # Ana çerçeve
        self.main_frame = tk.Frame(self.window, bg="#f0f2f5")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Başlık çubuğu
        self.header = tk.Frame(self.main_frame, bg="#e3f2fd", height=40)
        self.header.pack(fill=tk.X)
        
        self.title_label = tk.Label(
            self.header, 
            text=f"Özel Sohbet: {self.recipient}", 
            font=("Segoe UI", 12, "bold"),
            bg="#e3f2fd", 
            fg="#333333"
        )
        self.title_label.pack(side=tk.LEFT, padx=10, pady=8)
        
        # Mesaj alanı
        self.messages_frame = tk.Frame(self.main_frame, bg="#f0f2f5")
        self.messages_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollable mesaj alanı
        self.canvas = tk.Canvas(self.messages_frame, bg="#f0f2f5", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.messages_frame, orient="vertical", command=self.canvas.yview)
        
        self.messages_container = tk.Frame(self.canvas, bg="#f0f2f5")
        self.messages_container_id = self.canvas.create_window(
            (0, 0), window=self.messages_container, anchor="nw", width=self.canvas.winfo_width()
        )
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.messages_container.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Mesaj giriş alanı
        self.input_frame = tk.Frame(self.main_frame, bg="#f0f2f5", height=60)
        self.input_frame.pack(fill=tk.X, pady=(5, 10), padx=10)
        
        self.msg_input = tk.Entry(
            self.input_frame, 
            font=("Segoe UI", 11),
            bg="white",
            fg="#333333",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#cccccc",
            highlightcolor="#1877f2"
        )
        self.msg_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=8, padx=(0, 10))
        self.msg_input.bind("<Return>", self.send_message)
        
        # Gönder butonu
        self.send_btn = tk.Button(
            self.input_frame, 
            text="Gönder", 
            font=("Segoe UI", 10, "bold"),
            bg="#1877f2",
            fg="white",
            relief=tk.FLAT,
            padx=15,
            command=self.send_message,
            cursor="hand2"
        )
        self.send_btn.pack(side=tk.RIGHT, ipady=8)
        
        # Geçmiş mesajları yükle
        self.load_message_history()
    
    def on_frame_configure(self, event=None):
        """Mesaj alanı boyutu değiştiğinde scrollbar'ı güncelle"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_configure(self, event=None):
        """Canvas boyutu değiştiğinde içerik genişliğini güncelle"""
        if event:
            canvas_width = event.width
            self.canvas.itemconfig(self.messages_container_id, width=canvas_width)
    
    def load_message_history(self):
        """Mesaj geçmişini yükle"""
        for msg in self.message_history:
            if msg["sender"] == self.username:
                self.add_my_message(msg["content"], msg["timestamp"])
            else:
                self.add_other_message(msg["content"], msg["timestamp"])
    
    def add_message_to_history(self, sender, content, timestamp):
        """Mesaj geçmişine ekle"""
        self.message_history.append({
            "sender": sender,
            "content": content,
            "timestamp": timestamp
        })
    
    def add_my_message(self, content, timestamp=None):
        """Kendi mesajımı ekle"""
        if not timestamp:
            timestamp = time.strftime("%H:%M:%S")
            
        # Mesaj konteyneri
        message_frame = tk.Frame(self.messages_container, bg="#f0f2f5")
        message_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Mesaj balonu içeren frame
        bubble_frame = tk.Frame(message_frame, bg="#f0f2f5")
        bubble_frame.pack(side=tk.RIGHT)
        
        # Mesaj içeriği
        message_content = tk.Label(
            bubble_frame,
            text=content,
            font=("Segoe UI", 10),
            bg="#e3f2fd",  # Açık mavi
            fg="#000000",
            justify=tk.LEFT,
            wraplength=300,
            padx=10,
            pady=8
        )
        message_content.pack(fill=tk.X)
        
        # Zaman etiketi
        time_label = tk.Label(
            bubble_frame,
            text=timestamp,
            font=("Segoe UI", 7),
            bg="#f0f2f5",
            fg="#65676b"
        )
        time_label.pack(side=tk.RIGHT, padx=5, pady=(0, 2))
        
        # Scroll'u aşağı kaydır
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)
    
    def add_other_message(self, content, timestamp=None):
        """Karşı tarafın mesajını ekle"""
        if not timestamp:
            timestamp = time.strftime("%H:%M:%S")
            
        # Mesaj konteyneri
        message_frame = tk.Frame(self.messages_container, bg="#f0f2f5")
        message_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Mesaj balonu içeren frame
        bubble_frame = tk.Frame(message_frame, bg="#f0f2f5")
        bubble_frame.pack(side=tk.LEFT)
        
        # Mesaj içeriği
        message_content = tk.Label(
            bubble_frame,
            text=content,
            font=("Segoe UI", 10),
            bg="#f3e5f5",  # Açık mor
            fg="#000000",
            justify=tk.LEFT,
            wraplength=300,
            padx=10,
            pady=8
        )
        message_content.pack(fill=tk.X)
        
        # Zaman etiketi
        time_label = tk.Label(
            bubble_frame,
            text=timestamp,
            font=("Segoe UI", 7),
            bg="#f0f2f5",
            fg="#65676b"
        )
        time_label.pack(side=tk.LEFT, padx=5, pady=(0, 2))
        
        # Scroll'u aşağı kaydır
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)
    
    def send_message(self, event=None):
        """Mesaj gönder"""
        content = self.msg_input.get().strip()
        if not content:
            return
        
        self.msg_input.delete(0, tk.END)
        
        # Mesajı gönder
        timestamp = time.strftime("%H:%M:%S")
        
        def send():
            success = self.client.send_direct_message(self.recipient, content)
            if success:
                # Mesaj geçmişine ekle
                self.add_message_to_history(self.username, content, timestamp)
            else:
                # Hata mesajı
                error_frame = tk.Frame(self.messages_container, bg="#f0f2f5")
                error_frame.pack(fill=tk.X, pady=5)
                
                error_label = tk.Label(
                    error_frame,
                    text="❌ Mesaj gönderilemedi!",
                    font=("Segoe UI", 9, "italic"),
                    bg="#f0f2f5",
                    fg="#e74c3c"  # Kırmızı
                )
                error_label.pack()
        
        # Mesajı UI'da göster
        self.add_my_message(content, timestamp)
        
        # Asenkron olarak gönder
        threading.Thread(target=send).start()
    
    def receive_message(self, content, timestamp):
        """Karşı taraftan gelen mesajı göster"""
        # Mesaj geçmişine ekle
        self.add_message_to_history(self.recipient, content, timestamp)
        
        # Mesajı göster
        self.add_other_message(content, timestamp)
        
        # Pencere odaklanmamışsa dikkat çek
        if not self.window.focus_get():
            self.window.bell()  # Sesli uyarı
            
            # Eğer pencere minimize edilmişse veya arkadaysa
            if self.window.state() == 'iconic':
                self.window.deiconify()  # Pencereyi öne getir
                self.window.lift()  # Üste çıkar
    
    def on_close(self):
        """Pencere kapatıldığında"""
        # Ana uygulamaya bildir
        if hasattr(self.parent, 'close_private_chat'):
            self.parent.close_private_chat(self.recipient)
        self.window.destroy()



if __name__ == "__main__":
    ModernChatGUI()