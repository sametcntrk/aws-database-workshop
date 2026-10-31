# Okuyucu raporu: 00 Veri nedir? (2026-10-31)

Okuyucu: hiç veritabanı kullanmamış biri. Kaynak: `/tmp/bub/veri.txt` (baştan sona) ve `app/engine_app/e2e_veri.py` (simülasyonların "say" metinleri). Düz metinde `<code>` parçaları boş görünüyor (örneğin "Bizim verimizde: , , , ."). Bunları `templates/e2e/veri.tr.html` ile karşılaştırdım; sayfada dolular, bu yüzden bulgu olarak saymadım.

Genel izlenim: A ve B bölümleri çok iyi akıyor. "Aklına şu gelebilir" kutuları sorularımın çoğunu cevapladı. Sorunlar birkaç eski ya da şüpheli olgu, iki sayma hatası ve açıklanmayan terimlerde.

## Bulgular

### B1 (yüksek, olgu): S3 nesne sınırı eski
Bölüm: B3 tablosu, "Birim" satırı ve "Daha derine in".
Alıntı: "Nesne: tek bir PUT ile 5 GB'a, parça parça yüklemeyle 5 TB'a kadar."
Sorun: AWS Aralık 2025'te en büyük nesne boyutunu 5 TB'tan 50 TB'a çıkardı (What's New: "Amazon S3 increases the maximum object size to 50 TB"). Tek PUT sınırı 5 GB olarak kalıyor. Doğrusu: "parça parça yüklemeyle 50 TB'a kadar".

### B2 (yüksek, sayı): "Sekiz yol" denen tabloda dokuz model var
Bölüm: A4 başlığı.
Alıntı: "Veri modelleri: veriyi düzenlemenin sekiz yolu".
Sorun: Tabloda dokuz satır var: ilişkisel, key-value, doküman, wide-column, graf, zaman serisi, arama index'i, sütun bazlı, nesne. Saydım ve "hangisini kaçırdım?" diye geri döndüm.

### B3 (yüksek, Türkçe): Simülasyonda ek uyumu bozuk
Bölüm: C3, OLTP/OLAP simülasyonu (`oltp_olap`).
Alıntı: "müşterisi {city}'dan".
Sorun: Ek sabit. O000103 için ekranda "Frankfurt'dan" çıkıyor; doğrusu "Frankfurt'tan". İzmir'li bir müşteri olsaydı "İzmir'dan" çıkardı. Ek şehre göre seçilmeli ya da cümle eksiz kurulmalı ("müşterinin şehri: Frankfurt").

### B4 (orta, tutarsızlık): OLTP ve OLAP sıklıkları üç yerde farklı
Bölüm: C3.
Alıntı: simülasyon "Günde binlerce kez olur"; tablo "Saniyede binlerce"; giriş OLAP için "günde birkaç kez", tablo "Saatte birkaç ile birkaç yüz arası".
Sorun: Hangisinin doğru olduğunu bilemedim. Bir sıklık seçilmeli ve her yerde aynısı kullanılmalı.

### B5 (orta, şüpheli olgu): Kayan nokta hatasının "kuruşlara ulaşması"
Bölüm: A2, "Önce tahmin et" cevabı.
Alıntı: "Milyonlarca satırlık bir toplamda bu küçük farklar kuruşlara ulaşır."
Sorun: double'ın göreli hatası yaklaşık 10⁻¹⁶. Bin liralık bir milyon tutarı toplamak bile kuruşa değil, yaklaşık 10⁻⁷ TL'ye ulaşır. Asıl tehlike eşitlik karşılaştırmasının yanlış dönmesi ve her adımda yuvarlama yapılması. Öneri: "eşitlik karşılaştırmaları ve yuvarlama yanlış çıkar; kuruş farkı, tekrarlanan yuvarlamalarla ortaya çıkar".

### B6 (orta, olgu): SQL'in standart olduğu tarih
Bölüm: C1, "SQL neden bu kadar yaygın?".
Alıntı: "1970'lerden beri standarttır".
Sorun: SQL 1970'lerde IBM'de doğdu; ANSI standardı 1986'da, ISO standardı 1987'de geldi. Doğrusu: "1970'lerde doğdu, 1986'dan beri standarttır".

### B7 (orta, eksik durum): Lale Market'in kendisi `require` kullanıyor
Bölüm: C2, connection string tablosu ve sslmode kutusu.
Alıntı: "Lale Market'in Python kodu … sslmode require" ve "require … araya giren biri kendini veritabanı gibi gösterebilir … Üretimde sertifika doğrulaması açılır."
Sorun: Benim sorum şu: "Peki Lale Market güvensiz mi?" Sayfa bunu cevaplamıyor. Simülasyon da `verify-full` içeren bir JDBC URL'si gösteriyor, ama uygulama Python. Bir cümle yeter: neden workshop'ta `require` kullanılıyor ve gerçek mağaza neyi değiştirir.

### B8 (orta, anlaşılmayan cümle): Dosya biçimi simülasyonunun son adımı
Bölüm: B2 simülasyonu (`file_formats`, son adım).
Alıntı: "sütun dosyası sadece gereken sütunları ve min/max'ı uymayan parçaları atlar."
Sorun: Cümle, gereken sütunların atlandığını söylüyor gibi okunuyor. Beklediğim: "sadece gereken sütunları okur ve min/max'ı uymayan parçaları atlar." Ek olarak: istatistik tablosunda sadece total ve order_date var, sorgu ise status'a göre süzüyor. Bu örnekte min/max hiçbir şeyi atlatmıyor; simülasyon bunu söylemeli.

### B9 (orta, çelişki): Key-value'da key'siz arama
Bölüm: A4 tablosu.
Alıntı: "Key'i bilmeden arama: yapılamaz, bütün veri taranır."
Sorun: Bütün veri taranabiliyorsa arama yapılabiliyor demektir. Öneri: "verimli yapılamaz: bütün veri taranır."

### B10 (orta, terimler): Açıklanmadan karşıma çıkanlar
- A4: "şerit" ("şerit DocumentDB'ye sormadan çizilir"). Neyin şeridi olduğunu hiç anlamadım. Ayrıca "partition", "zero-ETL, değişiklik akışı" (C3'ten önce).
- A5: "Soft state", "LOCAL_ONE".
- B3: RAID, EBS, Availability Zone, Hadoop, data locality. NameNode ve DataNode önce tabloda geçiyor, diyagramda ise sonra açıklanıyor.
- B2: stripe, Hive, Snappy/ZSTD.
- C1/C2: planlayıcı, SigV4, RESP, DNS, TCP, TLS. Simülasyonda "kilitli" ("Tek satır, kilitli"); kilit hiçbir yerde anlatılmıyor.
- C3: olgu tablosu, boyut tablosu, star schema, CDC, DMS, Debezium, Glue, Airflow. C4: EMR, Athena, Glue Data Catalog.

### B11 (düşük, anlaşılmayan cümle): Blok depolama tanımı
Bölüm: B3.
Alıntı: "disk numaralı, eşit büyüklükte bloklardan oluşur; bloklara bir anlam veren üst katmandır."
Sorun: Blok depolamanın kendisini üst katman olarak tarif ediyor gibi okunuyor. Beklediğim: "bloklara anlamı üstteki katman (dosya sistemi ya da veritabanı) verir."

### B12 (düşük, eksik durum): HDFS'te küçük dosya
Bölüm: B3 diyagram altı.
Alıntı: "küçük bir dosya için ise bu yapı ağırdır."
Sorun: Neden ağır olduğu söylenmiyor. Benim sorum: "Peki ya 1 KB'lık bir milyon dosyam olursa?" Cevap NameNode'un her dosyayı bellekte tutmasıdır; sayfada bu yok.

### B13 (düşük, çelişki): Bağlantısız HTTPS API
Bölüm: C2.
Alıntı: "açık bir bağlantı oturumu tutulmaz" ve "TLS bağlantısını kütüphane yeniden kullanır."
Sorun: Bağlantı tutuluyor mu, tutulmuyor mu? Ayrım şu: veritabanı oturumu yok ama TCP/TLS bağlantısı yeniden kullanılıyor. Bu açıkça söylenmeli.

### B14 (düşük, eksik durumlar): Bağlantı simülasyonu
Bölüm: C2 simülasyonu.
Alıntı: "Sunucu tek harfle cevap verir: S (evet)."
Sorun: Sunucu N (hayır) derse ne olur? Şifre yanlışsa hangi adımda durulur? Havuzdaki bağlantı kopmuşsa ya da havuz doluysa ne olur? Hiçbiri cevaplanmıyor.

### B15 (düşük, Türkçe): Çeviri kokan ifadeler
- A2: "PostgreSQL'in (Aurora'nın da konuştuğu dil)". PostgreSQL bir dil değil. Öneri: "Aurora PostgreSQL'in de kullandığı tipler".
- B2: "Dosyanın biçimi B1'deki iki dizilimden birini seçer". Öneri: "Her dosya biçimi B1'deki dizilimlerden birini kullanır".
- C2: "Java ile psycopg, Aurora'ya aynı PostgreSQL mesajlarıyla konuşur". Öneri: "JDBC sürücüsü de psycopg de…".
- C4: "üç yaygın cevaba sahiptir". Öneri: "üç yaygın cevabı var".
- A5: "Bir veritabanının bu duruma verdiği söz".
- Simülasyon: "Önce bağlantı yok". Öneri: "Henüz bağlantı yok".
- A3: "herkes içeri girer, koltuklar salonda ayarlanır". Benzetmeyi anlamadım.

### B16 (düşük, tablo ve diyagram): Neye bakılacağı söylenmiyor
- Simülasyon lejandı: "okundu ve atlandı" tek etiket. Okundu mu, atlandı mı? İkisi ayrılmalı. "reddedildi ya da yanlış" bu sayfadaki hiçbir simülasyonda kullanılmıyor.
- A3 tablosu iki ekseni karıştırıyor: "Zamanla gelen ölçümler" ve "İlişkilerin kendisi" bir düzen derecesi değil. Tablo bunu söylemeli.
- B3'teki büyük tablo: hangi satırın asıl fark olduğu (birim, ortasını değiştirmek, kopyalar) söylenmiyor. Checkpoint bunu sonradan söylüyor.
- B1 simülasyonu: sayaç dışında neye bakılacağı (sağda atlanan bloklar) ilk adımda söylenmiyor.

### B17 (düşük, olgu ayrıntısı)
InfluxDB satırında port yok (8086). InfluxDB alan tiplerinde unsigned integer da var. S3'ün "birden fazla AZ" cümlesi One Zone sınıfları için doğru değil.

## Arkadaşıma anlatabilir miyim?

- **OLTP ile OLAP:** Evet. Kasa ve muhasebe benzetmesi, tablo ve simülasyon yeterli. Eksik: sıklık sayıları tutarsız (B4) ve star schema açıklanmadı.
- **Satır ve sütun düzeni:** Evet, en iyi anlaşılan kısım (36'ya karşı 18). Eksik: sıkıştırmanın neden okumayı da hızlandırdığı.
- **NTFS ile HDFS:** Büyük ölçüde evet: tek makine ve 4 KB'a karşı küme, 128 MB ve 3 kopya. Eksik: NameNode ve DataNode'un ne olduğu (önce adları geçiyor), küçük dosya sorunu (B12), neden yazıldıktan sonra değiştirilemediği.
- **JDBC:** Kısmen. "Arayüz aynı, sürücü değişir, protokol aynı" fikrini anladım. Eksik: bir JDBC kodunun nasıl göründüğü (getConnection, executeQuery, ResultSet akışı), sürücünün nereden geldiği (bir jar dosyası) ve simülasyonun neden JDBC gösterirken Lale Market'in Python kullandığı (B7).

## Kapanış (yazar)

| Bulgu | Karar | Yapılan |
|---|---|---|
| B1 | Düzeltildi | S3 en büyük nesne 50 TB (AWS What's New, Aralık 2025) B3 tablosunda ve kaynaklarda; aynı eski bilgi S3 E2E sayfasında ve e2e_sims.py'de de düzeltildi. |
| B2 | Düzeltildi | Başlık "dokuz yolu". |
| B3 | Düzeltildi | Ek kaldırıldı: "Müşterisinin şehri Frankfurt". |
| B4 | Düzeltildi | OLTP: saniyede yüzlerce, binlerce (simülasyon ve tablo). OLAP: saatte birkaç kez (giriş ve tablo). |
| B5 | Düzeltildi | Cümle: eşitlik karşılaştırmasını bozar, yuvarlamada kuruş hatası doğurabilir. |
| B6 | Düzeltildi | 1970'lerde doğdu, 1986'dan beri ANSI ve ISO standardı. |
| B7 | Düzeltildi | sslmode ask kutusu Lale Market'in require kullandığını ve nedenini söylüyor; simülasyon Java örneği olduğunu ve psycopg'nin aynı mesajları gönderdiğini söylüyor. |
| B8 | Düzeltildi | Son cümle yeniden yazıldı; bu örnekte atlanacak parça olmadığı açıkça söylendi. |
| B9 | Düzeltildi | "verimli yapılamaz; ikinci bir index yoksa bütün veri taranır". |
| B10 | Düzeltildi | şerit, LOCAL_ONE, soft state, kilitli, NameNode/DataNode (diyagramdan önce bir paragraf), RAID, EBS, AZ, stripe, Hive, star schema, CDC, DMS, EMR, Athena ilk geçtikleri yerde açıklandı. |
| B11 | Düzeltildi | Blok depolama tanımı yeniden yazıldı. |
| B12 | Düzeltildi | Diyagram açıklamasına NameNode belleği ve küçük dosya sorunu eklendi. |
| B13 | Düzeltildi | "Veritabanında oturum açılmaz; alttaki TLS bağlantısı yeniden kullanılabilir." |
| B14 | Düzeltildi | Yeni ask kutusu: SSL'e hayır, yanlış şifre, dolu havuz, kopmuş bağlantı. |
| B15 | Düzeltildi | Beş ifade yeniden yazıldı. |
| B16 | Kısmen | A3 tablosuna ve B3 tablosuna okuma cümlesi eklendi. Lejant bütün E2E sayfalarında ortak; 00 için değiştirilmedi. |
| B17 | Düzeltildi | InfluxDB port 8086, PostgreSQL'de unsigned yok, S3 Standard ve One Zone ayrımı eklendi. |
