# Veritabanı 101: Sıfırdan Başlayanlar İçin

Bu yazı hiçbir ön bilgi varsaymaz. Amacı, [Keşif Rehberi](KESIF-REHBERI.md)'ni okuyup sitedeki her ekranı anlayabilmenizi sağlamaktır.
Her kavramı önce günlük hayattan bir örnekle, sonra Lale Market'teki karşılığıyla anlatıyor.

Okuma süresi: 40-50 dakika. Acele etmeyin. Her bölümün sonundaki **"Akılda kalsın"** kutusu o bölümün özetidir.

**İçindekiler**

1. Veritabanı nedir?
2. Veriyi okumak ve yazmak
3. Tablolar ve SQL: ilişkisel veritabanı
4. İndeks: kitabın arkasındaki dizin
5. Transaction: ya hep ya hiç
6. Neden tek bir veritabanı yetmiyor?
7. On veritabanı tipi, tek tek
8. Hız, maliyet ve ölçek nasıl ölçülür?
9. Bulut ve AWS'nin temel kavramları
10. Sitedeki sağ paneli okumak
11. Kısa sözlük

---

## 1. Veritabanı nedir?

Bir bakkal düşünün. Bakkal sabah kimin ne aldığını, raflarda ne kaldığını ve kime veresiye yazdığını bir **deftere** yazar.
Sonra "Ayşe Hanım'ın borcu ne kadar?" diye sorulunca deftere bakar.

**Veritabanı**, bu defterin bilgisayardaki halidir: bilgiyi düzenli saklayan ve sorulduğunda hızlıca bulan bir programdır.

Defterle veritabanı arasındaki farklar:
- Defter bir kişinin elindedir. Veritabanına **aynı anda binlerce kişi** yazabilir ve okuyabilir.
- Defter kaybolabilir. Veritabanı bilgiyi birden çok yere kopyalar ve kaybolmaz.
- Defterde 10.000 sayfa olunca bir şeyi bulmak saatler sürer. Veritabanı milyonlarca kayıt içinden **milisaniyeler** içinde bulur.

**Lale Market'te:** Ürünler, müşteriler, sepetler, siparişler, fotoğraflar... Hepsi bir veritabanında durur.
Siz sitede bir şeye tıklayınca, site arka planda bir veritabanına "bana şunu ver" ya da "şunu kaydet" der.

> **Akılda kalsın:** Veritabanı, bilgiyi düzenli saklayan ve sorulduğunda hızlıca bulan programdır. Bir site her tıklamada bir veritabanıyla konuşur.

---

## 2. Veriyi okumak ve yazmak

Bir veritabanıyla yapılan her iş iki türden biridir:

| İş | Günlük hayatta | Lale Market'te |
|---|---|---|
| **Okuma (read)** | Defterden bilgiye bakmak | Ürün sayfasını açmak, sepeti görmek |
| **Yazma (write)** | Deftere yeni bir şey yazmak, silmek veya düzeltmek | Sepete ürün eklemek, sipariş vermek |

Veritabanına gönderilen her "şunu ver" veya "şunu kaydet" isteğine **sorgu (query)** denir.

**Sorguyu kim gönderir?** Siz doğrudan veritabanıyla konuşmazsınız. Arada bir **uygulama** vardır:

```
Siz (tarayıcı)  →  Uygulama (sunucudaki program)  →  Veritabanı
      ←                    ←                             ←
```

Restoran benzetmesi: Siz müşterisiniz, uygulama garson, veritabanı mutfak. Siz garsona söylersiniz, garson mutfağa iletir, yemeği size getirir.
Lale Market'te bu garsonların adı **Engine App**'tir. Her veritabanının kendi garsonu vardır.

> **Akılda kalsın:** Okuma bilgiye bakmak, yazma bilgiyi değiştirmektir. Her isteğe sorgu denir. Tarayıcı veritabanıyla değil, aradaki uygulamayla konuşur.

---

## 3. Tablolar ve SQL: ilişkisel veritabanı

En yaygın veritabanı tipi bilgiyi **tablolarda** tutar. Bir Excel sayfası gibi düşünün:

**müşteriler** tablosu:

| müşteri_no | ad | şehir |
|---|---|---|
| C00001 | Ayşe Yılmaz | İstanbul |
| C00002 | Mert Doğan | Ankara |

**siparişler** tablosu:

| sipariş_no | müşteri_no | tutar |
|---|---|---|
| O000001 | C00001 | 1.250 TL |
| O000002 | C00001 | 300 TL |

- Her yatay sıra bir **satır (row)**, yani bir kayıttır.
- Her dikey sütun bir **sütun (column)**, yani bir özelliktir.
- Her satırı benzersiz tanımlayan sütuna **birincil anahtar (primary key)** denir. Burada müşteri_no ve sipariş_no.

Dikkat edin: siparişler tablosunda müşterinin adı yazmıyor, yalnızca **müşteri_no** yazıyor. Ayşe adını değiştirirse tek bir yeri düzeltirsiniz.
Tablolar birbirine bu numaralarla bağlıdır. Bu yüzden bu tür veritabanlarına **ilişkisel (relational)** denir.

**JOIN:** "Ayşe'nin siparişlerini adıyla birlikte göster" demek için iki tablo müşteri_no üzerinden **birleştirilir**. Buna JOIN denir.

**Foreign key (yabancı anahtar):** siparişler tablosundaki müşteri_no, müşteriler tablosunda gerçekten var olmalıdır.
Veritabanı, var olmayan bir müşteriye sipariş yazılmasını reddeder. Bu kural veriyi tutarlı tutar.

**SQL:** İlişkisel veritabanlarıyla konuşulan dil. Okunuşu İngilizceye yakındır:

```sql
SELECT ad, tutar
FROM siparişler JOIN müşteriler ON siparişler.müşteri_no = müşteriler.müşteri_no
WHERE şehir = 'İstanbul';
```

Türkçesi: "İstanbul'daki müşterilerin adlarını ve sipariş tutarlarını getir."

**Lale Market'te:** **Aurora PostgreSQL** ilişkisel veritabanıdır. Siparişler, sipariş kalemleri, müşteriler ve stoklar oradadır.

> **Akılda kalsın:** İlişkisel veritabanı veriyi birbirine numaralarla bağlı tablolarda tutar. JOIN tabloları birleştirir, SQL bu veritabanlarının dilidir.

---

## 4. İndeks: kitabın arkasındaki dizin

500 sayfalık bir kitapta "veritabanı" kelimesinin geçtiği yerleri arıyorsunuz. İki yol var:

1. Kitabı ilk sayfadan son sayfaya kadar okumak. Buna **tam tarama (full scan)** denir. Yavaştır.
2. Kitabın arkasındaki **dizine** bakmak: "veritabanı: s. 12, 87, 340". Doğrudan o sayfalara gidersiniz.

Veritabanındaki **indeks**, bu dizinin aynısıdır. Belirli bir sütun için hazırlanmış, sıralı bir kısayoldur.

- **Artısı:** Okuma çok hızlanır. Milyonlarca kayıttan birkaçını bulmak milisaniyeler sürer.
- **Eksisi:** Her yazmada dizin de güncellenir, yani yazma biraz yavaşlar ve fazladan yer kaplar.

**Lale Market'te:** Bir kategori sayfasında **Collection scan** deneyini seçtiğinizde indeksi kapatırsınız.
Panelde "docs examined" (incelenen kayıt) sayısı 40'tan 200'e çıkar. Veritabanı bütün kitabı okumak zorunda kalmıştır.

> **Akılda kalsın:** İndeks, aramayı hızlandıran bir kısayoldur. İndeks yoksa veritabanı her şeyi baştan sona tarar.

---

## 5. Transaction: ya hep ya hiç

Bankadan arkadaşınıza 100 TL gönderiyorsunuz. Bu aslında iki iştir:
1. Sizin hesabınızdan 100 TL düş.
2. Arkadaşınızın hesabına 100 TL ekle.

Birinci iş olup ikinci iş olmazsa, örneğin tam o anda elektrik kesilirse, 100 TL kaybolur. Kabul edilemez.

**Transaction**, birden çok işi tek bir paket yapar: **ya hepsi olur ya hiçbiri olmaz.**
- Her şey yolunda giderse paket onaylanır: **COMMIT**.
- Bir şey ters giderse yapılanlar geri alınır: **ROLLBACK**. Sanki hiçbir şey olmamış gibi.

Veritabanlarında bu güvenceye kısaca **ACID** denir. Dört harfin özeti şudur: işler bölünmez, veri kurallara uygun kalır, aynı anda çalışan işler birbirini bozmaz ve onaylanan iş kalıcıdır.

**Lale Market'te:** Sipariş verdiğinizde Aurora üç işi bir paket yapar: stoğu düşür, siparişi yaz, sipariş kalemlerini yaz.
Ödeme sayfasındaki **Make the payment fail** deneyi ödemeyi yarıda bozar. Panelde `ROLLBACK` görürsünüz: stok geri gelir, sipariş oluşmaz.

> **Akılda kalsın:** Transaction birden çok işi "ya hep ya hiç" paketine koyar. COMMIT onaylar, ROLLBACK geri alır. Para ve stok gibi işler bunu gerektirir.

---

## 6. Neden tek bir veritabanı yetmiyor?

Bir mutfakta tek bir alet yoktur: bıçak keser, tencere pişirir, buzdolabı soğutur. Hepsini tek bir aletle yapmaya çalışırsanız hiçbiri iyi olmaz.

Veritabanları da böyledir. Her biri belli bir işte çok iyidir:
- Bir **sepet** çok hızlı ve çok sık okunur. Ama hep aynı soruyla: "bu kişinin sepeti ne?"
- Bir **arama** yazım hatalarını tolere etmelidir.
- Bir **satış raporu** milyonlarca satırı tarar.
- Bir **öneri** ("bunu alanlar şunu da aldı") ilişkiler üzerinde gezinir.

Bunların hepsini tek bir ilişkisel veritabanına yüklerseniz, yoğun bir kampanya günü rapor sorguları ödeme sayfasını yavaşlatır.
Lale Market'in hikâyesi tam olarak budur: her işi ona en uygun veritabanına vermek. Buna **amaca uygun veritabanı (purpose-built database)** yaklaşımı denir.

Veritabanları önce iki büyük aileye ayrılır:
- **İlişkisel (SQL):** Tablolar, JOIN, sıkı kurallar. Örnek: Aurora, Redshift.
- **İlişkisel olmayan (NoSQL):** Tablo zorunluluğu yoktur. Her biri farklı bir veri şekline göre tasarlanmıştır. Örnek: DynamoDB, DocumentDB, Neptune.

Ayrıca veri şekline göre üç grup vardır. Bu gruplar sitedeki etiketlerde de geçer:

| Grup | Anlamı | Örnek |
|---|---|---|
| **Structured** (yapılandırılmış) | Her kaydın sütunları aynıdır | Sipariş tablosu |
| **Semi-structured** (yarı yapılandırılmış) | Kayıtların alanları farklı olabilir | Bir kulaklığın "pil ömrü" alanı vardır, bir ceketin "beden" alanı |
| **Unstructured** (yapılandırılmamış) | Belirli bir yapısı yoktur | Fotoğraf, video, serbest metin |

> **Akılda kalsın:** Her veritabanı belli bir işte iyidir. Büyük sistemler birden çok veritabanını birlikte kullanır.

---

## 7. On veritabanı tipi, tek tek

Her biri için: **benzetme**, **ne işe yarar**, **Lale Market'teki görevi** ve **sitede göreceğiniz terimler**.

### 7.1 İlişkisel: Aurora PostgreSQL

- **Benzetme:** Muhasebecinin düzenli, birbirine bağlı defterleri.
- **Ne işe yarar:** Kuralları sıkı, birbirine bağlı veri ve transaction gerektiren işler.
- **Lale Market'te:** Ödeme, siparişler, stok.
- **Terimler:** `BEGIN` (paketi başlat), `UPDATE` (kaydı değiştir), `INSERT` (yeni kayıt ekle), `COMMIT`, `ROLLBACK`, `SELECT` (oku), `JOIN`,
  `EXPLAIN ANALYZE` (veritabanına "bu sorguyu nasıl çalıştırdın, her adım ne kadar sürdü?" diye sormak).

### 7.2 Doküman: DocumentDB

- **Benzetme:** Her ürün için ayrı bir dosya kartı. Kartlara istediğiniz bilgiyi ekleyebilirsiniz; her kartın alanları farklı olabilir.
- **Ne işe yarar:** Yapısı değişken olan ve bir bütün olarak okunan kayıtlar: ürün kataloğu, kullanıcı profili.
- **Lale Market'te:** Ürün kataloğu, yani ana sayfa, kategoriler ve ürün sayfası.
- **Terimler:**
  - **JSON:** Bu kartların yazıldığı biçim. Şöyle görünür: `{ "ad": "Kulaklık", "renk": "siyah" }`.
  - **İç içe alan:** Bir alanın içinde başka alanlar olması. Örnek: `attributes.renk`.
  - **Projection:** Kartın tamamı yerine yalnızca gereken alanları istemek.
  - **find:** Aramak.
  - **aggregate:** Gruplamak ve saymak.

### 7.3 Anahtar-değer: DynamoDB

- **Benzetme:** Vestiyer. Paltonuzu verirsiniz, size bir numara verirler. Numarayı söyleyince paltonuz anında gelir.
  Ne kadar çok palto olursa olsun süre değişmez. Ama "kırmızı paltoları getir" diyemezsiniz; yalnızca numarayla istenir.
- **Ne işe yarar:** Hep aynı anahtarla okunan, çok yüksek trafikli veri: sepet, oturum, oyun skoru.
- **Lale Market'te:** Sepet.
- **Terimler:**
  - **Partition key (bölüm anahtarı):** Vestiyer numarası. Sitede `CART#<sizin kimliğiniz>`.
  - **Query:** Anahtarla okumak.
  - **Scan:** Bütün tabloyu taramak. Pahalıdır, kaçınılır.
  - **ConditionExpression:** "Şu koşul doğruysa yaz" kuralı. Örnek: en fazla 5 adet.
  - **Atomik:** Bölünmeden, tek adımda yapılan iş.
  - **TTL:** Bölüm 7.6'ya bakın.

### 7.4 Bellek içi: ElastiCache (Valkey)

- **Benzetme:** Masanızın üstündeki not kâğıdı. Arşiv dolabına gitmekten çok daha hızlıdır ama kalıcı arşiv değildir.
- **Ne işe yarar:** Veriyi diske değil **belleğe (RAM)** yazar, bu yüzden aşırı hızlıdır (mikrosaniyeler). Sayaçlar, sıralamalar, oturumlar ve geçici veriler için kullanılır.
- **Lale Market'te:** Flaş indirim stok sayacı, canlı liderlik tablosu, oturum.
- **Terimler:**
  - **DECR / INCR:** Bir sayıyı tek komutta bir azaltmak veya artırmak.
  - **Sorted set:** Her zaman sıralı duran liste.
  - **HSET / HGETALL:** Bir kaydın alanlarını yazmak ve okumak.
  - **TTL / EXPIRE:** Süre dolunca otomatik silme.

### 7.5 Geniş sütunlu: Keyspaces

- **Benzetme:** Her müşteri için ayrı bir günlük defteri. Her sayfaya yeni olay en üste yazılır.
  "Ayşe'nin son 20 olayı" demek, Ayşe'nin defterini açıp ilk 20 satırı okumaktır.
- **Ne işe yarar:** Çok yüksek hacimli, zamana göre sıralı olaylar: tıklamalar, sensör verisi, loglar.
- **Lale Market'te:** Gezinme geçmişi ("Recently viewed", "My activity").
- **Terimler:**
  - **Partition:** Bir kişinin defteri. Sorgu her zaman hangi defter olduğunu söylemelidir.
  - **Clustering order:** Defterin içindeki sıralama; burada en yeniden en eskiye.
  - **CQL:** Bu veritabanının SQL'e benzeyen dili.
  - **LOCAL_ONE / LOCAL_QUORUM:** Bölüm 8'e bakın.

### 7.6 Zaman serisi: Timestream for InfluxDB

- **Benzetme:** Bir hasta odasındaki monitör. Her birkaç saniyede bir nabız ve ateş ölçülür ve zamanla birlikte kaydedilir.
- **Ne işe yarar:** Zaman damgalı ölçümler: sıcaklık, CPU kullanımı, dakikadaki sipariş sayısı.
- **Lale Market'te:** Operasyon ekranı (depo sıcaklığı, nemi, dakikalık siparişler).
- **Terimler:**
  - **Nokta (point):** Bir ölçüm. Bir zamanı, etiketleri (hangi depo) ve bir değeri vardır.
  - **Pencere (window):** "Her 15 dakikanın ortalaması" gibi zaman dilimleri.
  - **aggregateWindow:** Ham noktaları pencerelere indiren komut.
  - **Flux:** Bu veritabanının sorgu dili.

### 7.7 Graf: Neptune

- **Benzetme:** Bir arkadaşlık ağı haritası. Kişiler noktalar, arkadaşlıklar çizgilerdir. "Arkadaşımın arkadaşları kim?" sorusu çizgileri takip ederek cevaplanır.
- **Ne işe yarar:** İlişkinin kendisinin önemli olduğu veri: öneriler, sosyal ağ, dolandırıcılık tespiti.
- **Lale Market'te:** "Bunu alanlar bunları da aldı" önerileri ve müşteri grafı.
- **Terimler:**
  - **Vertex (düğüm):** Nokta. Burada müşteri veya ürün.
  - **Edge (kenar):** Çizgi. Burada **BOUGHT**, yani "satın aldı".
  - **Traversal (gezinme):** Çizgileri adım adım takip etmek.
  - **openCypher:** Graf sorgu dili.
  - **Soğuk başlangıç (cold start):** Hiç geçmişi olmayan bir kullanıcıya kişisel öneri yapılamaması.

### 7.8 Sütun bazlı analitik: Redshift

- **Benzetme:** Bir okulda "bütün öğrencilerin not ortalaması" lazım.
  Normal düzende her öğrencinin dosyasını açıp nota bakarsınız (adı, adresi, velisi... hepsini elden geçirirsiniz).
  Sütun bazlı düzende bütün notlar zaten **tek bir listede** yan yana durur. Yalnızca o listeyi okursunuz.
- **Ne işe yarar:** Milyonlarca satırı tarayan raporlar ve analizler. Toplamlar, ortalamalar, gruplamalar.
- **Lale Market'te:** Satış raporları.
- **Terimler:**
  - **Columnar:** Sütun bazlı saklama.
  - **GROUP BY:** "Kategoriye göre topla" gibi gruplama.
  - **Zero-ETL:** Bölüm 9.6'ya bakın.

### 7.9 Nesne deposu: S3

- **Benzetme:** Dev bir emanet dolabı. Her dosya bir kutuya konur. Kutunun üstünde bir **etiket** (anahtar) ve bir **not kâğıdı** (metadata) vardır.
- **Ne işe yarar:** Fotoğraf, video, yedek, log gibi dosyalar. Neredeyse sınırsız büyür.
- **Lale Market'te:** Ürün fotoğrafları, satıcı paneli.
- **Terimler:**
  - **Bucket:** Dolabın kendisi.
  - **Object:** Dosya.
  - **Key:** Dosyanın tam adı, örneğin `products/P0001.jpg`.
  - **Prefix:** Anahtarın baş kısmı. Klasör gibi görünür ama gerçek bir klasör değildir.
  - **Metadata:** Dosyanın yanındaki bilgiler (yazar, lisans).
  - **Versioning:** Üzerine yazılan dosyanın eski halini saklamak.
  - **Presigned URL:** Bölüm 9.5'e bakın.

### 7.10 Arama motoru: OpenSearch

- **Benzetme:** Bir kütüphanecinin kafasındaki kelime dizini. "kulaklik" diye yanlış yazsanız da ne demek istediğinizi anlar.
- **Ne işe yarar:** Metin araması, yazım hatası toleransı, sonuçları alakaya göre sıralama, konum araması.
- **Lale Market'te:** Arama sayfası, arama önerileri, mağaza bulucu.
- **Terimler:**
  - **Index:** Aranabilir metin kopyası.
  - **Fuzziness:** Bir-iki harf hatasını tolere etmek.
  - **Analyzer:** Metni kelimelere bölüp normalleştiren kural. Örneğin "Kulaklık"ı "kulaklik"e çevirir.
  - **Score:** Alaka puanı.
  - **Facet / aggregation:** "Elektronik (5)" gibi sayımlar.
  - **geo_point / geo_distance:** Konum ve mesafe sorgusu.

> **Akılda kalsın:**
>
> | Soru | Veritabanı |
> |---|---|
> | Para ve sipariş mi? | Aurora |
> | Esnek yapılı kart mı? | DocumentDB |
> | Tek anahtarla ışık hızında mı? | DynamoDB |
> | Geçici ve çok hızlı mı? | ElastiCache |
> | Kişi başına zaman sıralı olay mı? | Keyspaces |
> | Ölçüm akışı mı? | InfluxDB |
> | İlişki ağı mı? | Neptune |
> | Büyük rapor mu? | Redshift |
> | Dosya mı? | S3 |
> | Metin araması mı? | OpenSearch |

---

## 8. Hız, maliyet ve ölçek nasıl ölçülür?

### Gecikme (latency) ve milisaniye

- **ms (milisaniye):** Saniyenin binde biri. Göz kırpmak yaklaşık 100-150 ms sürer.
  - 1-10 ms: çok hızlı.
  - 100 ms: fark edilmez.
  - 1.000 ms (1 saniye): kullanıcı beklediğini hisseder.
- **p50, p95, p99:** Simülasyon sonuçlarında görürsünüz. 1.000 isteği hızlıdan yavaşa sıraladığınızı düşünün:
  - **p50 (medyan):** Tam ortadaki isteğin süresi. "Tipik" süre.
  - **p95:** İsteklerin %95'i bundan hızlıdır.
  - **p99:** En yavaş %1'lik dilimin başladığı nokta. Büyük sitelerde en mutsuz müşteriyi bu gösterir.

### Throughput (verim)

Saniyede kaç işin yapıldığı. Örneğin "saniyede 400 yazma". Simülasyonlar bunu ölçer.

### Kapasite birimleri ve maliyet

DynamoDB ve Keyspaces her okumayı ve yazmayı **birim** olarak sayar ve birim başına ücret alır:
- **RRU (read request unit):** Bir okuma birimi.
- **WRU (write request unit):** Bir yazma birimi.

Paneldeki **Cost** satırı her çağrının yaklaşık maliyetini gösterir. Rakamlar çok küçüktür (bir kuruşun milyonda biri gibi), ama milyarlarca istekte önemli hale gelir.

### Tutarlılık (consistency)

Veritabanları verinizi kaybetmemek için **birden çok kopya** tutar. Bir yazma önce bir kopyaya gider, sonra diğerlerine yayılır. Bu yayılma çok kısa sürer ama sıfır değildir.

- **Strongly consistent (güçlü tutarlı) okuma:** Her zaman en son yazılanı görürsünüz. Daha pahalıdır.
- **Eventually consistent (sonunda tutarlı) okuma:** Çok kısa bir an için eski veriyi görebilirsiniz. Yarı fiyattır.

Keyspaces'teki karşılıkları:
- **LOCAL_ONE:** Tek bir kopyaya sor. Ucuz ve hızlı.
- **LOCAL_QUORUM:** Kopyaların çoğunluğuna sor. Kesin sonuç verir.

### Yarış durumu (race condition) ve atomiklik

Bir sinemada son bir koltuk kaldı. İki kişi aynı anda ekrana bakıyor, ikisi de "boş" görüyor, ikisi de satın alıyor. Aynı koltuk iki kez satıldı.
Bu bir **yarış durumu**dur: "önce kontrol et, sonra yaz" arasındaki kısa anda başka biri araya girer.

Çözüm **atomik** bir işlemdir. "Koltuk boşsa al" kontrolü ve satın alma tek bir bölünmez adım olur.
Lale Market'teki flaş indirim deneyi tam olarak bunu gösterir.

### Ölçeklenme ve "serverless"

- **Ölçeklenme:** Trafik artınca sistemin büyüyebilmesi.
- **Serverless / on-demand:** Sunucu sayısını veya kapasiteyi siz ayarlamazsınız. Servis trafiğe göre kendisi büyür ve küçülür; siz kullandığınız kadar ödersiniz.
  Lale Market'te Aurora, Redshift, ElastiCache, Neptune ve DynamoDB böyle çalışır.

> **Akılda kalsın:** ms süredir; p99 en yavaş müşterinin deneyimidir. RRU/WRU ödenen birimlerdir. Güçlü tutarlılık kesin ama pahalıdır. Atomik işlem yarış durumunu engeller.

---

## 9. Bulut ve AWS'nin temel kavramları

**AWS (Amazon Web Services):** İnternet üzerinden kiralanan bilgisayarlar, veritabanları ve servisler. Kendi sunucunuzu almak yerine kullandığınız kadar ödersiniz.

### 9.1 Region ve Availability Zone (AZ)

- **Region:** Bir şehirdeki veri merkezleri bölgesi. Lale Market **Frankfurt** (`eu-central-1`) bölgesindedir.
- **Availability Zone (AZ):** Region'ın içindeki birbirinden ayrı veri merkezleri. Frankfurt'ta üç AZ kullanıyoruz: a, b, c.
- **Neden üç?** Bir veri merkezinde yangın veya elektrik kesintisi olursa diğerleri çalışmaya devam eder.
  **Multi-AZ** demek, bir şeyin birden çok AZ'de kopyasının olmasıdır.
- **Replica (kopya) / standby (yedek):** Ana veritabanının başka bir AZ'deki kopyası. Sitede "writer a, reader b" diye görürsünüz:
  yazmalar a'ya gider, okumalar b'deki kopyadan da yapılabilir.

### 9.2 VPC, subnet ve IP adresi

- **VPC (Virtual Private Cloud):** Bulutta size ayrılmış, dışarıdan kapalı özel bir ağ. Bir sitenin kendi içindeki yolları gibi düşünün.
- **Subnet:** VPC'nin bölümleri. Lale Market'te üç kat var:
  - **public:** İnternete açık kapı. Yük dengeleyici burada durur.
  - **app:** Uygulamalar (garsonlar) burada durur.
  - **data:** Veritabanları burada durur, internete hiç çıkmaz.
- **IP adresi:** Ağdaki her makinenin adresi, örneğin `10.20.10.14`. Paneldeki **Network** satırı paketin hangi IP'den çıkıp nereye gittiğini gösterir.

### 9.3 EC2 ve Load Balancer

- **EC2:** Kiralık bir sanal bilgisayar. Lale Market'te her Engine App ayrı bir EC2'de çalışır, toplam on tane.
- **Load Balancer (ALB, yük dengeleyici):** Sitenin girişindeki karşılama görevlisi. Gelen isteğin adresine bakar ve doğru uygulamaya yönlendirir:
  `/cart` DynamoDB uygulamasına, `/search` OpenSearch uygulamasına gider.

### 9.4 Endpoint ve NAT

- **Endpoint:** Bir servise ulaşmak için kullanılan kapı veya adres.
  - **VPC endpoint:** Özel ağınızdan bir AWS servisine **internete çıkmadan** giden özel bir kapı. Paneldeki "gateway endpoint" ve "interface endpoint" ifadeleri bunlardır.
  - **Gateway endpoint** ağ yönlendirmesiyle çalışır.
  - **Interface endpoint** ağınızın içine konmuş bir ağ kartıdır.
- **NAT Gateway:** Özel ağdaki makinelerin internete **yalnızca dışarı doğru** çıkabilmesini sağlar. Uygulamalar kodlarını GitHub'dan bu yolla indirir. Dışarıdan içeri giriş yoktur.

### 9.5 Güvenlik: IAM, şifreler ve imzalı adresler

- **IAM (Identity and Access Management):** Kimin neye erişebileceğini belirleyen sistem.
  - **IAM role:** Bir uygulamaya verilen kimlik kartı. Örneğin "bu uygulama yalnızca sepet tablosunu okuyup yazabilir".
- **SigV4:** Bu kimlik kartıyla her isteği **dijital olarak imzalamak**. Şifre gönderilmez; AWS imzayı kontrol eder.
  Paneldeki **Auth: IAM role (SigV4)** bunu anlatır.
- **Secrets Manager:** Şifrelerin saklandığı kasa. Bazı veritabanları kullanıcı adı ve şifre ister. Uygulama şifreyi koduna yazmaz, kasadan okur.
  Paneldeki **Auth: Password (Secrets Manager)** bunu anlatır.
- **Security group:** Bir makinenin güvenlik duvarı. "Bu veritabanına yalnızca şu uygulama bağlanabilir" der.
- **TLS:** Ağdaki trafiğin şifrelenmesi. Adres çubuğundaki kilit ikonunun anlamı budur.
- **Presigned URL:** Süreli, imzalı bir indirme bağlantısı. Dosya gizli kalır ama bu bağlantıya sahip olan birkaç dakika boyunca indirebilir.

### 9.6 Replikasyon, ETL ve zero-ETL

- **Replikasyon:** Verinin bir yerden başka bir yere sürekli kopyalanması.
- **ETL (Extract, Transform, Load):** Veriyi bir sistemden çıkar, dönüştür ve başka bir sisteme yükle. Genellikle elle yazılan, bakımı zor işlerdir.
- **Zero-ETL:** AWS'nin bu kopyalamayı **kod yazmadan** kendisinin yapması. Aurora'da verilen bir sipariş birkaç saniye içinde Redshift'e kendiliğinden gelir.
  Böylece ödeme veritabanı ağır raporlarla yorulmaz.
- **CDC (Change Data Capture):** "Yalnızca değişenleri yakala ve gönder." Sitede `CdcRefreshState` diye görürsünüz.

### 9.7 API ve "seed"

- **API:** Programların birbirleriyle konuştuğu kapı. Tarayıcı uygulamaya `GET /dynamodb/api/cart` gibi API çağrıları yapar.
  - **GET:** Okumak için kullanılır.
  - **POST:** Göndermek veya yazmak için kullanılır.
  - **DELETE:** Silmek için kullanılır.
- **Seed:** Veritabanına başlangıç verisini yüklemek. Lale Market'teki 200 ürün ve 1.000 müşteri sahte (sentetik) veridir ve Admin Console'dan yüklenir.

> **Akılda kalsın:**
> - Region bir şehir, AZ o şehirdeki ayrı bir veri merkezidir.
> - VPC sizin özel ağınızdır, subnet'ler onun katlarıdır.
> - EC2 kiralık bilgisayar, ALB karşılama görevlisidir.
> - IAM role kimlik kartıdır, SigV4 o kartla atılan imzadır.
> - Zero-ETL, veriyi kod yazmadan rapor veritabanına kopyalar.

---

## 10. Sitedeki sağ paneli okumak

Artık paneldeki bir kartı baştan sona okuyabilirsiniz. Gerçek bir örnek:

```
2. Read the cart                                        234 ms
GET /dynamodb/api/cart?consistent=true → DynamoDB Engine App

Query                                Amazon DynamoDB · 164.8 ms
  table.query(KeyConditionExpression=Key('pk').eq('CART#e0d4...'),
              ConsistentRead=True, ReturnConsumedCapacity='TOTAL')
  Parameters  ConsistentRead = true, pk = CART#e0d4...
  Result      0 item(s)
  Capacity    1.0 RRU
  Cost        ≈ $0.0000001525
  Network     EC2 10.20.10.11 → S3/DynamoDB gateway endpoint → DynamoDB
  Auth        IAM role (SigV4)
  Strongly consistent read: you see your last write. It costs 2x an eventually consistent read.
```

Satır satır Türkçesi:

| Satır | Anlamı |
|---|---|
| `2. Read the cart`, `234 ms` | Sayfanın yaptığı ikinci çağrı: "sepeti oku". Tarayıcıdan bakınca 234 ms sürdü. |
| `GET /dynamodb/api/cart ... → DynamoDB Engine App` | Tarayıcı DynamoDB'nin garsonuna (uygulamasına) "sepeti getir" dedi. |
| `Query ... 164.8 ms` | Garson DynamoDB'ye bir **Query** gönderdi. Bu kısım 164.8 ms sürdü. |
| `table.query(...)` | Gönderilen sorgunun kendisi: "partition key'i CART#... olan kayıtları getir". |
| `ConsistentRead=True` | Güçlü tutarlı okuma istendi. |
| `Result 0 item(s)` | Sepet boş. |
| `Capacity 1.0 RRU`, `Cost ≈ $0.0000001525` | Bir okuma birimi harcandı. Bedeli yaklaşık 0,00000015 dolar. |
| `Network EC2 10.20.10.11 → gateway endpoint → DynamoDB` | Paket, adresi 10.20.10.11 olan uygulama makinesinden çıktı ve internete uğramadan özel kapıdan DynamoDB'ye gitti. |
| `Auth IAM role (SigV4)` | Şifre yok. Uygulama kimlik kartıyla imzaladı. |
| Sarı cümle | Bu çağrıdan çıkarılacak ders. |

---

## 11. Kısa sözlük

| Terim | Kısa anlamı |
|---|---|
| ACID | Transaction'ın güvenceleri: bölünmez, tutarlı, birbirini bozmayan, kalıcı |
| aggregate / aggregation | Gruplamak ve saymak, toplamak |
| analyzer | Arama motorunun metni kelimelere bölme ve normalleştirme kuralı |
| API | Programların konuştuğu kapı |
| atomik | Bölünmeden tek adımda yapılan |
| AZ | Region içindeki ayrı veri merkezi |
| bucket | S3'teki dosya dolabı |
| cache | Hızlı erişim için geçici kopya |
| CDC | Yalnızca değişen veriyi yakalayıp göndermek |
| cold start (soğuk başlangıç) | Geçmişi olmayan kullanıcıya kişisel öneri yapılamaması |
| COMMIT / ROLLBACK | Transaction'ı onaylamak / geri almak |
| consistency (tutarlılık) | Okumanın en son yazılanı görme güvencesi |
| EC2 | Kiralık sanal bilgisayar |
| edge / vertex | Graf'ta çizgi / nokta |
| endpoint | Bir servise ulaşılan kapı |
| facet | Arama sonuçlarındaki kategori sayımları |
| foreign key | Başka bir tablodaki kaydın var olmasını zorunlu kılan kural |
| fuzziness | Yazım hatası toleransı |
| IAM role | Bir uygulamanın kimlik kartı |
| index (indeks) | Aramayı hızlandıran kısayol |
| JOIN | İki tabloyu ortak bir sütun üzerinden birleştirmek |
| JSON | `{ "alan": "değer" }` biçimindeki veri yazımı |
| latency (gecikme) | Bir işin süresi |
| load balancer (ALB) | Gelen isteği doğru uygulamaya yönlendiren giriş |
| metadata | Bir verinin yanındaki açıklayıcı bilgi |
| ms | Milisaniye, saniyenin binde biri |
| Multi-AZ | Birden çok veri merkezinde kopya |
| NAT Gateway | Özel ağdan internete yalnızca dışarı çıkış |
| NoSQL | İlişkisel olmayan veritabanları |
| on-demand / serverless | Kapasiteyi servis kendisi ayarlar, kullandığınız kadar ödersiniz |
| p50 / p95 / p99 | Gecikme yüzdelikleri: tipik, yavaşça, en yavaş %1 |
| partition key | Verinin hangi bölümde duracağını belirleyen anahtar |
| presigned URL | Süreli, imzalı indirme bağlantısı |
| primary key | Bir kaydı benzersiz tanımlayan sütun |
| projection | Kaydın yalnızca gereken alanlarını istemek |
| query (sorgu) | Veritabanına gönderilen istek |
| race condition (yarış durumu) | "Kontrol et, sonra yaz" arasında başkasının araya girmesi |
| region | Veri merkezlerinin bulunduğu şehir bölgesi |
| replica | Veritabanının kopyası |
| RRU / WRU | Okuma / yazma birimi (ücretlendirme) |
| scan | Bütün veriyi baştan sona taramak |
| secret | Kasada saklanan şifre |
| security group | Makine düzeyinde güvenlik duvarı |
| seed | Başlangıç verisini yüklemek |
| SigV4 | AWS isteklerinin dijital imzası |
| SQL | İlişkisel veritabanlarının dili |
| subnet | VPC içindeki ağ bölümü |
| throughput | Saniyedeki iş sayısı |
| TLS | Ağ trafiğinin şifrelenmesi |
| transaction | "Ya hep ya hiç" iş paketi |
| TTL | Süresi dolan verinin otomatik silinmesi |
| versioning | Dosyanın eski sürümlerini saklamak |
| VPC | Buluttaki özel ağ |
| zero-ETL | Veriyi kod yazmadan başka bir veritabanına kopyalamak |

---

## Hazır mısınız?

Şu soruları kendi cümlelerinizle cevaplayabiliyorsanız [Keşif Rehberi](KESIF-REHBERI.md)'ne geçebilirsiniz:

1. Veritabanı ile uygulama arasındaki fark nedir? (Mutfak ve garson)
2. İndeks neden aramayı hızlandırır? (Kitabın arkasındaki dizin)
3. Transaction'da ROLLBACK ne zaman olur? (Banka transferi yarıda kalınca)
4. Sepet için neden DynamoDB, rapor için neden Redshift? (Vestiyer ve not listesi)
5. Yarış durumu nedir? (Sinemadaki son koltuk)
6. AZ nedir ve neden üç tane kullanıyoruz? (Bir veri merkezi çökerse)
7. Paneldeki "Auth: IAM role (SigV4)" ne demek? (Şifre yerine kimlik kartıyla imza)

Keşif rehberinde takıldığınız bir terim olursa bu yazının sonundaki sözlüğe dönün.
