# Hibrit Sohbet Uygulaması

Bu proje, hem TCP hem de UDP protokollerini kullanarak çalışan hibrit bir sohbet uygulamasıdır. TCP protokolü kullanıcı kimlik doğrulama, kullanıcı listesi ve topoloji bilgisi gibi güvenilir iletişim gerektiren işlemlerde kullanılırken, UDP protokolü düşük gecikme süreleri ile anlık mesajlaşma ve ping gibi işlemlerde kullanılır.

## Özellikler

- **Hibrit Protokol**: TCP güvenilirliği ve UDP hızı bir arada
- **Grup Sohbeti**: Tüm kullanıcılarla anlık mesajlaşma
- **Özel Mesajlaşma**: Kullanıcılar arasında bire bir özel sohbet
- **Ağ Topolojisi Görselleştirme**: Ağ yapısını görsel olarak izleme
- **Ping ve Gecikme Ölçümü**: Kullanıcılar arası bağlantı kalitesini ölçme
- **Güvenilir UDP**: Kritik mesajlar için onay mekanizması
- **Modern Kullanıcı Arayüzü**: Kullanıcı dostu ve estetik arayüz

## Dosyalar ve Açıklamaları

- **chat_gui.py**: Grafik kullanıcı arayüzü
- **hybrid_chat_client_fixed.py**: İstemci sınıfı
- **hybrid_protocol.py**: Protokol tanımı ve mesaj formatları
- **hybrid_server.py**: Sunucu uygulaması
- **network_topology.py**: Ağ topolojisi yönetimi
- **reliable_udp.py**: Güvenilir UDP uygulaması
- **topology_view_fixed.py**: Topoloji görselleştirme
- **topology_tester.py**: Topoloji test aracı

## Kurulum ve Çalıştırma

### Gereksinimler
- Python 3.6 veya üzeri
- Tkinter (GUI için)

### Sunucuyu Başlatma
```bash
python hybrid_server.py
```

### İstemciyi Başlatma
```bash
python chat_gui.py
```

### Topoloji Test Aracını Başlatma
```bash
python topology_tester.py
```

## Protokol Detayları

Uygulama, özel bir mesajlaşma protokolü kullanır:

- **AUTH**: Kullanıcı kimlik doğrulama (TCP)
- **CHAT**: Genel sohbet mesajı (UDP)
- **DIRECT**: Özel mesaj (UDP)
- **ACK**: Mesaj alındı bildirimi (UDP)
- **PING/PONG**: Gecikme ölçümü (UDP)
- **USERS**: Kullanıcı listesi (TCP)
- **JOIN/LEAVE**: Kullanıcı giriş/çıkış bildirimi (TCP)
- **TOPO**: Ağ topolojisi bilgisi (TCP)

## Katkıda Bulunma

1. Bu depoyu fork edin
2. Yeni bir özellik dalı oluşturun (`git checkout -b yeni-ozellik`)
3. Değişikliklerinizi işleyin (`git commit -am 'Yeni özellik eklendi'`)
4. Dalınızı ana depoya gönderin (`git push origin yeni-ozellik`)
5. Bir Pull Request oluşturun

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır - detaylar için LICENSE dosyasına bakın.
