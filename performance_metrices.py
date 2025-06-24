import tkinter as tk
from tkinter import ttk
import threading
import time
import queue
from collections import deque

# Matplotlib import kontrolü
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    from datetime import datetime, timedelta
    MATPLOTLIB_AVAILABLE = True
    print("[DEBUG] Matplotlib başarıyla import edildi")
except ImportError as e:
    print(f"[WARNING] Matplotlib import edilemedi: {e}")
    MATPLOTLIB_AVAILABLE = False

class PerformanceMetrics:
    def __init__(self):
        # Metrik verileri için veri yapıları
        self.lock = threading.Lock()
        self.max_history = 100  # Kaç veri noktası saklanacak
        
        # Gecikme (Latency) verileri
        self.latency_history = {}  # {username: deque([latency_values])}
        self.latency_timestamps = deque(maxlen=self.max_history)
        
        # Veri aktarım hızı (Throughput) verileri
        self.throughput_history = deque(maxlen=self.max_history)  # [bytes_per_second]
        self.throughput_timestamps = deque(maxlen=self.max_history)
        self.bytes_sent = 0
        self.bytes_received = 0
        self.last_throughput_time = time.time()
        
        # Ölçeklenebilirlik (Scalability) verileri
        self.user_count_history = deque(maxlen=self.max_history)  # [user_count]
        self.user_count_timestamps = deque(maxlen=self.max_history)
        
        # Metrik toplama aralığı (saniye)
        self.collection_interval = 1.0
        self.should_stop = threading.Event()
        
        # Metrik toplama thread'i
        self.collector_thread = threading.Thread(target=self._collector_loop, daemon=True)
        self.collector_thread.start()
        
        print("[DEBUG] PerformanceMetrics başlatıldı")
    
    def _collector_loop(self):
        """Düzenli aralıklarla metrikleri toplar"""
        while not self.should_stop.is_set():
            try:
                self.calculate_throughput()
                time.sleep(self.collection_interval)
            except Exception as e:
                print(f"[ERROR] Metrik toplama hatası: {e}")
                time.sleep(1)
    
    def record_latency(self, username, latency_ms):
        """Kullanıcı gecikmesini kaydeder"""
        with self.lock:
            if username not in self.latency_history:
                self.latency_history[username] = deque(maxlen=self.max_history)
            
            self.latency_history[username].append(latency_ms)
            current_time = time.time()
            
            # Zaman damgası güncelle
            if len(self.latency_timestamps) == 0 or current_time - self.latency_timestamps[-1] > 1:
                self.latency_timestamps.append(current_time)
    
    def record_message_sent(self, size_bytes):
        """Gönderilen mesaj boyutunu kaydeder"""
        with self.lock:
            self.bytes_sent += size_bytes
    
    def record_message_received(self, size_bytes):
        """Alınan mesaj boyutunu kaydeder"""
        with self.lock:
            self.bytes_received += size_bytes
    
    def record_user_count(self, count):
        """Aktif kullanıcı sayısını kaydeder"""
        with self.lock:
            current_time = time.time()
            self.user_count_history.append(count)
            self.user_count_timestamps.append(current_time)
    
    def calculate_throughput(self):
        """Veri aktarım hızını hesaplar"""
        with self.lock:
            current_time = time.time()
            time_diff = current_time - self.last_throughput_time
            
            if time_diff >= 1.0:  # En az 1 saniye geçmiş olsun
                total_bytes = self.bytes_sent + self.bytes_received
                throughput = total_bytes / time_diff if time_diff > 0 else 0
                
                self.throughput_history.append(throughput)
                self.throughput_timestamps.append(current_time)
                
                # Reset counters
                self.bytes_sent = 0
                self.bytes_received = 0
                self.last_throughput_time = current_time
    
    def get_avg_latency(self, username=None):
        """Ortalama gecikme süresini hesaplar"""
        with self.lock:
            if username and username in self.latency_history:
                latencies = list(self.latency_history[username])
                return sum(latencies) / len(latencies) if latencies else 0
            else:
                # Tüm kullanıcıların ortalaması
                all_latencies = []
                for user_latencies in self.latency_history.values():
                    all_latencies.extend(list(user_latencies))
                return sum(all_latencies) / len(all_latencies) if all_latencies else 0
    
    def get_avg_throughput(self):
        """Ortalama veri aktarım hızını hesaplar"""
        with self.lock:
            throughputs = list(self.throughput_history)
            return sum(throughputs) / len(throughputs) if throughputs else 0
    
    def get_peak_throughput(self):
        """En yüksek veri aktarım hızını döndürür"""
        with self.lock:
            throughputs = list(self.throughput_history)
            return max(throughputs) if throughputs else 0
    
    def get_user_count_stats(self):
        """Kullanıcı sayısı istatistiklerini döndürür"""
        with self.lock:
            counts = list(self.user_count_history)
            if not counts:
                return {"avg": 0, "max": 0, "current": 0}
            
            return {
                "avg": sum(counts) / len(counts),
                "max": max(counts),
                "current": counts[-1] if counts else 0
            }
    
    def stop(self):
        """Metrik toplama işlemini durdurur"""
        self.should_stop.set()
        if self.collector_thread.is_alive():
            self.collector_thread.join(timeout=2.0)


class PerformanceViewer:
    def __init__(self, master, metrics):
        self.master = master
        self.metrics = metrics
        self.after_id = None
        
        print("[DEBUG] PerformanceViewer başlatılıyor...")
        
        # Ana çerçeve
        self.frame = ttk.Frame(master)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Başlık
        self.title_label = ttk.Label(
            self.frame, 
            text="Performans Metrikleri", 
            font=("Segoe UI", 14, "bold")
        )
        self.title_label.pack(pady=(0, 10))
        
        # Veri durumu bilgisi
        self.info_label = ttk.Label(
            self.frame, 
            text="Gerçek zamanlı veriler bekleniyor...", 
            font=("Segoe UI", 10),
            foreground="gray"
        )
        self.info_label.pack(pady=(0, 10))
        
        if not MATPLOTLIB_AVAILABLE:
            # Matplotlib yoksa sadece metin tabanlı görünüm
            self.create_text_view()
        else:
            # Matplotlib varsa grafik görünümü
            self.create_graph_view()
        
        print("[DEBUG] PerformanceViewer başarıyla oluşturuldu")
    
    def create_text_view(self):
        """Matplotlib olmadığında metin tabanlı görünüm"""
        # Bilgi paneli
        info_frame = ttk.LabelFrame(self.frame, text="Performans İstatistikleri", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        # İstatistik etiketleri
        self.avg_latency_label = ttk.Label(info_frame, text="Ortalama Gecikme: Veri yok")
        self.avg_latency_label.pack(anchor=tk.W, pady=2)
        
        self.avg_throughput_label = ttk.Label(info_frame, text="Ortalama Veri Hızı: Veri yok")
        self.avg_throughput_label.pack(anchor=tk.W, pady=2)
        
        self.peak_throughput_label = ttk.Label(info_frame, text="En Yüksek Veri Hızı: Veri yok")
        self.peak_throughput_label.pack(anchor=tk.W, pady=2)
        
        self.user_count_label = ttk.Label(info_frame, text="Kullanıcı Sayısı: Veri yok")
        self.user_count_label.pack(anchor=tk.W, pady=2)
        
        # Veri sayısı bilgisi
        self.data_count_label = ttk.Label(info_frame, text="Toplam Veri Noktası: 0")
        self.data_count_label.pack(anchor=tk.W, pady=2)
        
        # Kontrol paneli
        control_frame = ttk.Frame(self.frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        # Yenile düğmesi
        self.refresh_btn = ttk.Button(
            control_frame,
            text="Yenile",
            command=self.update_text_stats
        )
        self.refresh_btn.pack(side=tk.LEFT)
        
        # Otomatik yenile
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_cb = ttk.Checkbutton(
            control_frame,
            text="Otomatik Yenile",
            variable=self.auto_refresh_var,
            onvalue=True,
            offvalue=False
        )
        auto_refresh_cb.pack(side=tk.LEFT, padx=10)
        
        # İlk güncelleme
        self.update_text_stats()
        self.start_auto_refresh()
    
    def create_graph_view(self):
        """Matplotlib ile grafik görünümü"""
        # Grafik panelleri için notebook
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Gecikme (Latency) grafik paneli
        self.latency_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.latency_frame, text="Gecikme (Latency)")
        
        # Veri aktarım hızı (Throughput) grafik paneli
        self.throughput_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.throughput_frame, text="Veri Aktarım Hızı")
        
        # Ölçeklenebilirlik (Scalability) grafik paneli
        self.scalability_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.scalability_frame, text="Ölçeklenebilirlik")
        
        # Kontrol paneli
        self.control_frame = ttk.Frame(self.frame)
        self.control_frame.pack(fill=tk.X, pady=10)
        
        # Yenileme aralığı
        ttk.Label(self.control_frame, text="Yenileme aralığı:").pack(side=tk.LEFT, padx=(0, 5))
        self.refresh_var = tk.StringVar(value="2 sn")
        refresh_combo = ttk.Combobox(
            self.control_frame,
            values=["1 sn", "2 sn", "5 sn", "10 sn"],
            textvariable=self.refresh_var,
            width=6,
            state="readonly"
        )
        refresh_combo.pack(side=tk.LEFT, padx=5)
        
        # Yenile düğmesi
        self.refresh_btn = ttk.Button(
            self.control_frame,
            text="Grafikleri Yenile",
            command=self.update_graphs
        )
        self.refresh_btn.pack(side=tk.RIGHT)
        
        # Otomatik yenile
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_cb = ttk.Checkbutton(
            self.control_frame,
            text="Otomatik Yenile",
            variable=self.auto_refresh_var,
            onvalue=True,
            offvalue=False
        )
        auto_refresh_cb.pack(side=tk.RIGHT, padx=10)
        
        # Grafikleri oluştur
        self.create_latency_graph()
        self.create_throughput_graph()
        self.create_scalability_graph()
        
        # Otomatik yenileme için
        self.start_auto_refresh()
    
    def create_latency_graph(self):
        """Gecikme grafiği oluştur"""
        try:
            # Matplotlib figure oluştur
            self.latency_fig = Figure(figsize=(8, 6), dpi=100)
            self.latency_ax = self.latency_fig.add_subplot(111)
            
            # Canvas oluştur
            self.latency_canvas = FigureCanvasTkAgg(self.latency_fig, self.latency_frame)
            self.latency_canvas.draw()
            self.latency_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # İlk boş grafik
            self.latency_ax.set_title('Gecikme Süresi (Latency)')
            self.latency_ax.set_xlabel('Zaman')
            self.latency_ax.set_ylabel('Gecikme (ms)')
            self.latency_ax.text(0.5, 0.5, 'Veri bekleniyor...', 
                               horizontalalignment='center', verticalalignment='center',
                               transform=self.latency_ax.transAxes)
            self.latency_ax.grid(True)
            
            print("[DEBUG] Gecikme grafiği oluşturuldu")
        except Exception as e:
            print(f"[ERROR] Gecikme grafiği oluşturulurken hata: {e}")
    
    def create_throughput_graph(self):
        """Veri aktarım hızı grafiği oluştur"""
        try:
            self.throughput_fig = Figure(figsize=(8, 6), dpi=100)
            self.throughput_ax = self.throughput_fig.add_subplot(111)
            
            self.throughput_canvas = FigureCanvasTkAgg(self.throughput_fig, self.throughput_frame)
            self.throughput_canvas.draw()
            self.throughput_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # İlk boş grafik
            self.throughput_ax.set_title('Veri Aktarım Hızı (Throughput)')
            self.throughput_ax.set_xlabel('Zaman')
            self.throughput_ax.set_ylabel('Hız (B/s)')
            self.throughput_ax.text(0.5, 0.5, 'Veri bekleniyor...', 
                                  horizontalalignment='center', verticalalignment='center',
                                  transform=self.throughput_ax.transAxes)
            self.throughput_ax.grid(True)
            
            print("[DEBUG] Veri aktarım hızı grafiği oluşturuldu")
        except Exception as e:
            print(f"[ERROR] Veri aktarım hızı grafiği oluşturulurken hata: {e}")
    
    def create_scalability_graph(self):
        """Ölçeklenebilirlik grafiği oluştur"""
        try:
            self.scalability_fig = Figure(figsize=(8, 6), dpi=100)
            self.scalability_ax = self.scalability_fig.add_subplot(111)
            
            self.scalability_canvas = FigureCanvasTkAgg(self.scalability_fig, self.scalability_frame)
            self.scalability_canvas.draw()
            self.scalability_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # İlk boş grafik
            self.scalability_ax.set_title('Kullanıcı Sayısı (Scalability)')
            self.scalability_ax.set_xlabel('Zaman')
            self.scalability_ax.set_ylabel('Kullanıcı Sayısı')
            self.scalability_ax.text(0.5, 0.5, 'Veri bekleniyor...', 
                                   horizontalalignment='center', verticalalignment='center',
                                   transform=self.scalability_ax.transAxes)
            self.scalability_ax.grid(True)
            
            print("[DEBUG] Ölçeklenebilirlik grafiği oluşturuldu")
        except Exception as e:
            print(f"[ERROR] Ölçeklenebilirlik grafiği oluşturulurken hata: {e}")
    
    def update_latency_graph(self):
        """Gecikme grafiğini güncelle"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        try:
            self.latency_ax.clear()
            self.latency_ax.set_title('Gecikme Süresi (Latency)')
            self.latency_ax.set_xlabel('Zaman')
            self.latency_ax.set_ylabel('Gecikme (ms)')
            
            # Gecikme verilerini çiz
            has_data = False
            with self.metrics.lock:
                for username, latencies in self.metrics.latency_history.items():
                    if latencies:
                        times = list(range(len(latencies)))
                        self.latency_ax.plot(times, list(latencies), label=username, marker='o')
                        has_data = True
            
            if has_data:
                self.latency_ax.legend()
            else:
                self.latency_ax.text(0.5, 0.5, 'Henüz gecikme verisi yok', 
                                   horizontalalignment='center', verticalalignment='center',
                                   transform=self.latency_ax.transAxes)
            
            self.latency_ax.grid(True)
            self.latency_canvas.draw()
            
        except Exception as e:
            print(f"[ERROR] Gecikme grafiği güncellenirken hata: {e}")
    
    def update_throughput_graph(self):
        """Veri aktarım hızı grafiğini güncelle"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        try:
            self.throughput_ax.clear()
            self.throughput_ax.set_title('Veri Aktarım Hızı (Throughput)')
            self.throughput_ax.set_xlabel('Zaman')
            self.throughput_ax.set_ylabel('Hız (B/s)')
            
            has_data = False
            with self.metrics.lock:
                if self.metrics.throughput_history:
                    times = list(range(len(self.metrics.throughput_history)))
                    throughputs = list(self.metrics.throughput_history)
                    self.throughput_ax.plot(times, throughputs, 'b-', marker='o')
                    has_data = True
            
            if not has_data:
                self.throughput_ax.text(0.5, 0.5, 'Henüz veri aktarım hızı verisi yok', 
                                      horizontalalignment='center', verticalalignment='center',
                                      transform=self.throughput_ax.transAxes)
            
            self.throughput_ax.grid(True)
            self.throughput_canvas.draw()
            
        except Exception as e:
            print(f"[ERROR] Veri aktarım hızı grafiği güncellenirken hata: {e}")
    
    def update_scalability_graph(self):
        """Ölçeklenebilirlik grafiğini güncelle"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        try:
            self.scalability_ax.clear()
            self.scalability_ax.set_title('Kullanıcı Sayısı (Scalability)')
            self.scalability_ax.set_xlabel('Zaman')
            self.scalability_ax.set_ylabel('Kullanıcı Sayısı')
            
            has_data = False
            with self.metrics.lock:
                if self.metrics.user_count_history:
                    times = list(range(len(self.metrics.user_count_history)))
                    user_counts = list(self.metrics.user_count_history)
                    self.scalability_ax.plot(times, user_counts, 'g-', marker='o')
                    has_data = True
            
            if not has_data:
                self.scalability_ax.text(0.5, 0.5, 'Henüz kullanıcı sayısı verisi yok', 
                                       horizontalalignment='center', verticalalignment='center',
                                       transform=self.scalability_ax.transAxes)
            
            self.scalability_ax.grid(True)
            self.scalability_canvas.draw()
            
        except Exception as e:
            print(f"[ERROR] Ölçeklenebilirlik grafiği güncellenirken hata: {e}")
    
    def update_text_stats(self):
        """Metin tabanlı istatistikleri güncelle"""
        try:
            avg_latency = self.metrics.get_avg_latency()
            avg_throughput = self.metrics.get_avg_throughput()
            peak_throughput = self.metrics.get_peak_throughput()
            user_stats = self.metrics.get_user_count_stats()
            
            # Veri var mı kontrol et
            has_latency_data = any(len(latencies) > 0 for latencies in self.metrics.latency_history.values())
            has_throughput_data = len(self.metrics.throughput_history) > 0
            has_user_data = len(self.metrics.user_count_history) > 0
            
            # Toplam veri noktası sayısı
            total_data_points = (sum(len(latencies) for latencies in self.metrics.latency_history.values()) + 
                               len(self.metrics.throughput_history) + 
                               len(self.metrics.user_count_history))
            
            if has_latency_data:
                self.avg_latency_label.config(text=f"Ortalama Gecikme: {avg_latency:.2f} ms")
            else:
                self.avg_latency_label.config(text="Ortalama Gecikme: Veri yok")
                
            if has_throughput_data:
                self.avg_throughput_label.config(text=f"Ortalama Veri Hızı: {avg_throughput:.2f} B/s")
                self.peak_throughput_label.config(text=f"En Yüksek Veri Hızı: {peak_throughput:.2f} B/s")
            else:
                self.avg_throughput_label.config(text="Ortalama Veri Hızı: Veri yok")
                self.peak_throughput_label.config(text="En Yüksek Veri Hızı: Veri yok")
                
            if has_user_data:
                self.user_count_label.config(text=f"Kullanıcı Sayısı: {user_stats['current']}")
            else:
                self.user_count_label.config(text="Kullanıcı Sayısı: Veri yok")
            
            self.data_count_label.config(text=f"Toplam Veri Noktası: {total_data_points}")
            
            # Ana bilgi etiketini güncelle
            if total_data_points > 0:
                self.info_label.config(text=f"Gerçek zamanlı veriler görüntüleniyor ({total_data_points} veri noktası)")
            else:
                self.info_label.config(text="Gerçek zamanlı veriler bekleniyor...")
            
        except Exception as e:
            print(f"[ERROR] Metin istatistikleri güncellenirken hata: {e}")
    
    def update_graphs(self):
        """Tüm grafikleri güncelle"""
        if MATPLOTLIB_AVAILABLE:
            self.update_latency_graph()
            self.update_throughput_graph()
            self.update_scalability_graph()
        else:
            self.update_text_stats()
    
    def start_auto_refresh(self):
        """Otomatik yenileme döngüsü"""
        def refresh_loop():
            try:
                # Pencere hala var mı kontrol et
                if not self.master.winfo_exists():
                    return
                
                if self.auto_refresh_var.get():
                    self.update_graphs()
                    
                    # Seçilen aralığa göre zamanla
                    interval_text = self.refresh_var.get() if hasattr(self, 'refresh_var') else "2 sn"
                    if interval_text == "1 sn":
                        interval = 1000
                    elif interval_text == "2 sn":
                        interval = 2000
                    elif interval_text == "5 sn":
                        interval = 5000
                    else:
                        interval = 10000
                    
                    # after_id'yi saklayarak daha sonra iptal edebiliriz
                    self.after_id = self.master.after(interval, refresh_loop)
                else:
                    # Otomatik yenileme kapalıysa 500ms sonra tekrar kontrol et
                    self.after_id = self.master.after(500, refresh_loop)
                    
            except Exception as e:
                print(f"[ERROR] Otomatik yenileme hatası: {e}")
        
        # İlk yenilemeyi başlat
        refresh_loop()
    
    def stop_auto_refresh(self):
        """Otomatik yenilemeyi durdur"""
        if self.after_id:
            try:
                self.master.after_cancel(self.after_id)
            except:
                pass
        
        # Metrikleri durdur
        if hasattr(self.metrics, 'stop'):
            self.metrics.stop()
    
    def on_close(self):
        """Pencere kapatıldığında"""
        self.stop_auto_refresh()


# Test için basit örnek (gerçek uygulamada kullanılmayacak)
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Performans Metrikleri - Gerçek Zamanlı")
    root.geometry("900x700")
    
    metrics = PerformanceMetrics()
    viewer = PerformanceViewer(root, metrics)
    
    def on_closing():
        viewer.on_close()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    print("Performans metrikleri penceresi açıldı. Gerçek veriler için chat uygulamasını kullanın.")
    root.mainloop()