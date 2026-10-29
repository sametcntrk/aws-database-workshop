# DynamoDB (TR) · "Mimar gözüyle" bölümü · okur simülasyonu raporu

Kaynak: `/tmp/ddb_tr_architect.txt` (R1–R5 tablosu, R1 kataloğu, M1, M2'deki 10 kart, M3–M7, checkpoint'ler).
Okur profili: DynamoDB'yi hiç kullanmamış, yalnız temel database fikirlerini bilen biri. Bölüm A'yı (partition key, sort key, TTL, Ö1–Ö8, A2–A10) okudu.

Aritmetik kontrolü: 10 kartın 30 satırında bütün ağırlıklar toplam 100, bütün katkılar (puan × ağırlık / 10), R1 ara toplamları ve 100 üzerinden toplamlar doğru. "Yakın yarış" işareti yalnız kart 7'de (fark 3,6) ve doğru. Aşağıdaki bulguların hiçbiri hesap hatası değildir; hepsi gerekçe, tutarlılık ve anlaşılırlık bulgusudur.

Önem dereceleri: **Y** = yüksek (karar ya da yöntem güvenilirliğini bozar, iki yer çelişir), **O** = orta (bir gerekçe ikna etmez ya da puan kırması tutarsız), **D** = düşük (dil, terim, küçük eksik).

---

## 1. Anlamadığım cümleler ve beklediğim

| # | Yer | Alıntı | Sorun / beklediğim | Önem |
|---|-----|--------|--------------------|------|
| 1.1 | R1–R5 sonrası | "AWS key-value için yalnız ElastiCache sunabilirdi; DynamoDB'yi hiç çıkarmayabilir ya da serverless değil instance modunda çıkarabilirdi." | Varsayımsal cümle zincirini ilk okumada takip edemedim. Beklediğim: "Aynı engine'i bir üretici farklı paketleyebilir; örneğin Valkey ElastiCache'te log'suz, MemoryDB'de log'lu çalışır. Bu fark engine'den değil üreticiden gelir." gibi tek bir somut örnek. | D |
| 1.2 | R1–R5 tablosu | R2 satırının kaynağı "engine'in doğası" | Sonraki paragraf yalnız R1 ve R3–R5'i açıklar; R2'nin neden "engine'in doğası" olduğu söylenmez. Kartlarda R2 puanları çoğunlukla servis paketlemesinden kırılır (instance sınıfı, ACU, pre-warming, shard sayısı). Ya kaynak "ikisi birden" olmalı ya da gerekçe yazılmalı. | O |
| 1.3 | Kart 1, DynamoDB R1.2 | "bir arızada eski sepet kalabilir" | "Eski sepet" ne demek: sipariş yazıldı ama sepet silinmedi, müşteri aynı ürünleri tekrar mı görür? Sonucu bir cümleyle söylenmeli. | D |
| 1.4 | Kart 3, R2 nedeni | "1 ms ile 5 ms arasındaki fark, ürün sayfasının toplam süresinin yüzde 5'idir." | Sayfanın toplam süresi (80 ms?) hiçbir yerde verilmedi; yüzde 5 nereden geliyor anlamadım. | D |
| 1.5 | Kart 4, kafa kafaya | "Fark R2'de, bu kartın en ağır ikinci gereksiniminde açılır." | Tabloda R2 (30) tek başına en ağır satırdır. "İkinci" R1'in toplamından (45) sonra anlamında ise bunu söylemeli. | D |
| 1.6 | Kart 6, DynamoDB R1.3 | "işaretin 24 saatten uzun kalması zararsızdır ama okuma tarafı süreyi bilmelidir" | Zararsızsa okuma tarafı neden süreyi bilmeli? Süresi geçmiş ama silinmemiş işaret yeni bir isteği reddeder mi, reddetmeli mi? Açık değil. | O |
| 1.7 | Kart 10, Karar | "DynamoDB yakın ikincidir" | Fark 7,5; sayfa "yakın yarış"ı ≤ 5 olarak tanımlar. "Yakın ikinci" ile "yakın yarış" okuru karıştırır. | D |
| 1.8 | Kart 10 başlığı | "Reklam ve öneri sorguları" | Kartta reklam yok, yalnız öneri listesi var. | D |
| 1.9 | M6 | "Commit'ten sonra tarayıcı DynamoDB'deki sepeti boşaltır." | Kart 1'de sepeti checkout boşaltır. Boşaltan tarayıcı mı, sunucu mu? Arızada "eski sepet kalabilir" riski kimin sorumluluğunda? | D |
| 1.10 | Giriş | "bir key-value database her isteği key ile, çok hızlı, her boyutta ve her istek hızında cevaplar" | Kart 3, 8 ve 10 DynamoDB'nin "yeterince hızlı olmadığını" gösterir. "Çok hızlı" yerine "her ölçekte sabit, tek haneli milisaniye" beklerdim. | D |

## 2. Anlamını bilmeden önce karşıma çıkan terimler

Bölüm A'da tanımlı olduğunu varsaydıklarım (partition key, sort key, TTL, Ö1–Ö8, hot partition) dışındakiler. Çoğu bir puan kırmanın **tek** gerekçesidir, bu yüzden bilinmeden puan ikna etmez.

**Y – puan gerekçesinin taşıyıcısı olan, hiç açıklanmayan terimler**
- **okuma birimi / yazma birimi** (kart 2 R5 "4 KB'tan büyük profiller iki okuma birimi", kart 5 R5 "1 KB'tan büyük mesajlar iki yazma birimi", Ö6 "40.000 yazma birimi"): birimin ne olduğu, neden 4 KB ve 1 KB olduğu yok.
- **on-demand / provisioned / reserved capacity**: kart 1'den itibaren kullanılır, tanımı ancak M5'te gelir; reserved capacity hiç tanımlanmaz.
- **ECPU, GB-saat** (ElastiCache Serverless), **ACU, Serverless v2** (Aurora): fiyat satırlarının hepsi bunlara dayanır.
- **MVCC, VACUUM, heap** (kart 1, 2, 4, 9 Aurora satırları): Aurora'nın birçok kırılması bunlara dayanır.
- **warm throughput / ön ısıtma (pre-warming)** (kart 4, 7) ve **elastic cluster** (kart 4 DocumentDB).
- **writer / reader / primary / replica / shard / node**: "tek writer'dan geçer" kararın merkezinde ama tek-writer sınırının ne olduğu yok (bkz. 4.5).
- **eventually consistent / strongly consistent**: Ö5'te geçiyor olabilir; MemoryDB R3 kırmaları bununla yapılır.

**O – bir kez geçen, anlamadan geçebildiğim ama bir açıklama beklediğim terimler**
- Valkey (ilk kez R1 gerekçesinde, ElastiCache ile ilişkisi M5'e kadar belirsiz), Lua script, WATCH/MULTI, HGETALL, HINCRBY, GETEX, SET … NX GET, pipeline.
- BSON, arrayFilters, `$set`, `$inc`, change stream.
- CDC, Keyspaces Streams API, KCL, CQL, LSM ağacı.
- Flux/InfluxQL, InfluxDB task/check, `last()`.
- JSONB, `jsonb_set`, pg_cron, `ON CONFLICT`, CHECK, UNIQUE, logical replication, replication slot, DMS, connection pool.
- DAX (kart 3'te parantezle kısaca açıklanır, ayrıntı M5'te).
- zero-ETL (kart 9 R1.4 ve Ö7'de; tanımı M5'te).
- TransactWriteItems, BatchWriteItem, ConditionalCheckFailedException, ReturnValuesOnConditionCheckFailure, ReturnValues = UPDATED_NEW, LastEvaluatedKey, "1 MB'lık sayfalar", "S3'ten import".
- R1 kataloğundaki DA örnekleri: B-tree, LSM, columnar, inverted index.
- point-in-time recovery, Global tables (M5'te alıntıyla).

**D**
- R1–R5 tablosunda "(R1 · EY)" kodu, katalogdan önce geçer.
- "GSI" kısaltması katalogda açılmadan kullanılır (Ö7 "ikinci index" ile aynı şey olduğu söylenmeli).

## 3. "Peki ya … ?" diye sorduğum ve cevap bulamadığım yerler

| # | Yer | Soru | Önem |
|---|-----|------|------|
| 3.1 | Kart 9 (dosya metadata) | Sort key "klasör/dosya adı". **Kullanıcı bir klasörün adını değiştirirse ya da bir dosyayı başka klasöre taşırsa ne olur?** Key değişmez; bu her dosya için sil + yaz demek (5.000 dosya). DocumentDB ve Aurora'da bu bir alan güncellemesi. DynamoDB R1.1 yine de 10 almış. | Y |
| 3.2 | Kart 6 (idempotency) | İlk istek kartı **hâlâ çekerken** aynı id ile ikinci istek gelirse ne döner? Gereksinim bunu söylüyor ("arada sonuç henüz yazılmamış olabilir") ama hiçbir aday satırı cevaplamıyor; Karar yalnız arızadaki "işlemde" durumunu anıyor. | O |
| 3.3 | Kart 4 (oyun) | R2: "Her istek **dünyanın her yerinden** 10 ms'nin altında." Tek bölgedeki bir table bunu nasıl verir? Global tables gerekir mi, maliyeti ve tutarlılığı ne olur? Hiçbir adayın puanı bunu anmıyor. | O |
| 3.4 | Kart 1 ↔ kart 4 | On-demand kart 1'de 250 → 5.000 yazmaya "ayar olmadan" çıkıyor, kart 4'te 200.000'e çıkmak için ön ısıtma gerekiyor. **Eşik nerede?** "Ayarsız" ne zaman yeterli, ne zaman değil? | O |
| 3.5 | Kart 7 (koltuk) | Tek partition key saniyede 1.000 yazma birimi alıyorsa 50.000 deneme için **en az kaç bölüm** gerekir? En çok aranan ön sıralar tek bölümdeyse ne olur? | O |
| 3.6 | Kart 5 (IoT) | Saniyede 65.000 sürekli yazma: table başına bir üst sınır var mı, kota artırmak gerekir mi? Kart 7'de partition sınırı anlatılıyor ama table düzeyi hiç anılmıyor. | D |
| 3.7 | Kart 8 (ElastiCache R1.3) | "İlk INCR'den sonra EXPIRE 60": iki komut arasında bağlantı koparsa sayaç **hiç silinmez mi**? Script seçeneği parantez içinde, risk söylenmiyor. | D |
| 3.8 | Kart 7 | ElastiCache neden aday değil? Kart 6 bunu açıklıyor, kart 7 açıklamıyor (cevap muhtemelen R3, ama okur tahmin ediyor). | D |
| 3.9 | Kart 10 R5 | Günde 8,6 milyar okumanın DynamoDB fiyatı ile 40 GB belleğin fiyatı **kaç dolar**? Kart 8 sayı veriyor ("on binlerce dolar"), kart 10 vermiyor ("yaklaşır ya da onu aşar"). 6 ile 5 puan arasındaki küçük fark rakamsız ikna etmiyor. | O |
| 3.10 | Genel | Bir şirket birden fazla engine işletirse (zaten Aurora var) ikinci bir servis eklemenin **operasyon maliyeti** nerede puanlanıyor? Kart 3 ve 8'de "ekip tek bir database ile çalışır" artısı anılıyor ama hiçbir satırda puan değil. | O |

## 4. İkna etmeyen karar gerekçeleri ve mimara soracağım sorular

### 4.1 [Y] R1 "yalnız engine'in doğası" kuralı birçok kartta delinmiş
Sayfa: "R1'in cevabı platformdan bağımsızdır". Ama şu R1 puanları servis paketlemesinden ya da operasyondan kırılıyor/kazanılıyor:
- **Kart 8, MemoryDB R1.2 · DA (6)**: kırma nedeni çoklu AZ log'u. Kafa kafaya paragraf bunu kendisi söylüyor: "Engine uyumundaki tek fark depolama satırındadır ve **o da servis tasarımından gelir**". Aynı engine (Valkey), R1'de farklı puan.
- **Kart 10, MemoryDB R1.3 · OY (7)**: yine log'a yazma beklemesi ve "yazılan GB ayrıca ödenir" (R5 konusu).
- **Kart 5, Keyspaces R1.3 · YD (7)**: "Lambda'yı doğrudan tetikleyen bir bağlantı yoktur, tüketici uygulama işletilmelidir" → AWS entegrasyonu ve operasyon (R4). DynamoDB'nin 10'u da "Lambda filtre kriteri"ne, yani AWS paketlemesine dayanıyor.
- **Kart 9, R1.4 · YD**: DynamoDB 10 "OpenSearch'e zero-ETL entegrasyonu" (AWS ürünü), DocumentDB 8 "tüketiciyi ekip işletir" (R4), Aurora 6 "DMS ya da pipeline kurulur ve işletilir" (R4).
- **Kart 4, DynamoDB R1.4 · TA (9)**: "transaction normal yazmanın iki katı birim tüketir" → bu maliyettir (R5). "En fazla 100 value" sınırı satın almada (2 value) hiç devreye girmiyor.

Soru: "R1'i engine'in doğası diye tanımladın. Aynı Valkey engine'i kart 3'te R1'de iki serviste eşitken kart 8 ve 10'da neden farklı? Log, Lambda bağlantısı ve zero-ETL R3/R4'e taşınırsa kart 5 ve 9'daki R1 farkları kalır mı?"

### 4.2 [Y] Kart 6: kart 1'de cezalandırılan "iki database" sorunu burada cezasız; Aurora'nın gerçek avantajı puanlanmıyor
- Kart 1, DynamoDB R1.2 · TA: **2 puan kırıldı** çünkü "checkout'un adımları iki ayrı database'tedir".
- Kart 6, DynamoDB R1.1 · TA: **10, kırma yok**; oysa Karar'ın kendisi "Eksimiz: işaret ve ödeme kaydı ayrı database'lerdedir" diyor. Aurora'nın "işaret ve ödeme kaydı aynı transaction'da yazılabilir" artısı kafa kafaya paragrafında "ciddi bir artı" diye geçiyor ama hiçbir satırda puan değil.
- Ayrıca hikâyede ödeme kaydı **zaten** ilişkisel bir database'te. Aurora R4 (−3) ve R5 (−3) "düşük hacim için sürekli çalışan minimum kapasite ödenir" diye kırılıyor; oysa o kapasite ödeme için zaten çalışıyor, işaret tablosunun ek maliyeti yaklaşık sıfır.
- Soru: "Ödeme database'i zaten varsa idempotency işareti oraya bir tablo olarak neden konmasın? Kart 1'deki kuralı kart 6'ya uygularsan ve Aurora'nın marjinal maliyetini sıfıra yakın sayarsan fark 12,5'ten kaç puana iner?" (Kaba hesabım: DynamoDB R1.1 8 → 94; Aurora R4 9, R5 10 → yaklaşık 90. Kazanan değişmeyebilir ama kart "yakın yarış" olur ve okur başka bir ders alır.)

### 4.3 [Y] Kart 1: Aurora zaten var, ama maliyeti sıfırdan kurulmuş gibi puanlanıyor
Hikâye: "siparişi stok ve müşteri kayıtlarıyla birlikte Aurora'ya yazar". Aurora R5 (6): "minimum ACU ayın 27 boş gününde de ödenir"; R4 (6): ACU aralığı, connection pool, VACUUM. Bunların hepsi sipariş için zaten ödeniyor ve yapılıyor. Kart 2'nin kafa kafaya paragrafı "zaten bir Aurora işletiyor olsaydı" koşulunu Aurora lehine sayıyor; kart 1'de bu koşul gerçekleşmiş ama sayılmamış.
Soru: "Var olan Aurora'ya bir `cart` tablosu eklemenin marjinal maliyeti nedir ve neden R5'te görünmüyor?"

### 4.4 [Y] Aynı mekanizma için kırılan puan 1 ile 6 arasında değişiyor; önem puana karışıyor
"TTL günler içinde siler, uygulama okumada `expires_at`'i karşılaştırır" mekanizması:
- Kart 1 R1.4 (YD): −2
- Kart 3 R1.2 (YD): **−6**
- Kart 6 R1.3 (YD): −1
- Kart 7 R1.3 (YD, TTL yerine koşul): −3 (DynamoDB ve Aurora)
- Kart 8 R1.3 (YD): −4

Kart 3'teki ağır kırmanın gerekçesi "güvenlik açığı", yani bu iş yükünde **önemli** olması. Ama önem zaten ağırlıkta (20). Sayfa ağırlığı "önem", puanı "karşılama derecesi" diye ayırıyor; burada önem iki kez sayılıyor.
Aynı sızıntı: ElastiCache Serverless R3 kart 1'de **3** ("bu iş yükünde sepet kaybı istenmeyen bir sonuçtur"), kart 3, 8 ve 10'da **4**. Aynı servis, aynı log'suz tasarım.
Soru: "Puan servisin yeteneğini mi, iş yükü için önemini mi ölçüyor? İkincisiyse ağırlık neden var?"

### 4.5 [Y] "Tek writer / tek primary sınırı" kartlar arasında çelişiyor
- Kart 1 Aurora R2: "Saniyede **5.000** küçük yazma güçlü bir writer'ın erişimindedir."
- Kart 9 Aurora R2: "**500** yazma tek writer için küçüktür."
- Kart 2 DocumentDB R2 (−3) ve kafa kafaya paragrafı: saniyede **100** yazmada "yılda iki kat büyüme DocumentDB'de **tek primary'nin** ve instance sınıfının sınırına dayanır". Okumalar 15 replica'ya dağılıyor; 100 yazma iki katına çıksa da 200.
Kart 2'nin Karar'ı DynamoDB'yi öne geçireni "ölçek ve operasyon" diye söylüyor; ölçek kısmı bu çelişkiye dayanıyor.
Soru: "100 yazma/saniye bir primary için gerçekten sınır mı? Değilse kart 2'de R2 farkının gerekçesi nedir?"

### 4.6 [Y] "Zorunlu satır ve diskalifiye yoktur" kuralı kartlarda bozuluyor
Yöntem: "Zorunlu satır ve diskalifiye yoktur." Ama:
- Kart 6 R3: "Bu gereksinim bu kartta **zorunludur**."
- Kart 7 R3: "Bu kartta **zorunlu**."
- Kart 6 kafa kafaya: MemoryDB'nin log'u "aynı engine'i çalıştıran ElastiCache'in bu kartta neden **aday olmadığını** da açıklar", yani ElastiCache fiilen diskalifiye.
Soru: "Zorunlu ise yöntemde bir eşik mi var? Yoksa 'zorunlu' kelimesi yalnız yüksek ağırlık mı demek?"

### 4.7 [Y] Ağırlık nedenleri "puanlardan önce" belirlenmemiş görünüyor
Yöntem: "Ağırlık puanlardan önce, iş yükünün önceliğinden belirlenir." Ama birçok neden adaylara bakıyor:
- Kart 2 R1.3: "her aday bunu iyi yapar, **bu yüzden ağırlığı orta**."
- Kart 3 R1.1, kart 6 R1.4, kart 8 R1.4, kart 10 R1.1, kart 10 R1.4: "her aday yapar / her aday taşır".
- Kart 4 R3: "ama **üç aday da bunu sağlar**."
- Kart 2 R4 (12): "ekip **MongoDB API'sini** ve SQL'i az biliyor"; kart 5 R4: "sunucu ve **CQL** istemiyor". Bu bilgi hikâye paragrafında yok, yalnız gereksinim satırında var ve tam rakip adayın API'ını işaret ediyor. Okur olarak "bu ağırlık sonucu bilerek mi yazıldı?" diye sordum.
Soru: "Ağırlıkları adayları görmeden yazsaydın kart 2'de R4 yine 12 mi olurdu?"

### 4.8 [Y] Kart 3: DynamoDB R1.3 kırması sayfanın kendi bilgisiyle çelişiyor; MemoryDB R1.4 tutarsız
- DynamoDB R1.3 (−4): "okuma ve yenileme iki ayrı istektir". Kart 8'de sayfa `UpdateItem … ReturnValues = UPDATED_NEW` ile "artır ve yeni değeri döndür"ü **tek istekte** yapıyor. Aynı biçimde `UpdateItem SET expires_at … ReturnValues = ALL_NEW` oturumu okur ve süresini tek istekte yeniler. Kalan bedel bir yazma birimidir, o da R5'te zaten kırılmış.
- MemoryDB R1.4 · DA (10): "okumalar mikrosaniyelerde". Ama R1.3'te önerilen `GETEX` süreyi yeniler, yani **her okuma bir yazmadır** ve MemoryDB'de log'u bekler (sayfanın kendi R2 gerekçesi: "her yenileme bir yazmadır … tek haneli milisaniye"). Kart 8'de aynı durum (INCR = yazma) DA satırında −4 aldı; kart 3'te DA satırı 10.
Soru: "Kart 3'te DynamoDB tek istekle okuyup yenileyemez mi? MemoryDB'de GETEX'in gecikmesi kart 3'te neden DA'da değil, R2'de?"

### 4.9 [O] Aynı gecikme iki satırda sayılıyor (kart 3 ve 8), kart 10'da sayılmıyor
- Kart 3: DynamoDB R1.4 · DA (−5, "1 ms sınırı") **ve** R2 (−4, "gecikme sınırı DAX olmadan karşılanmaz").
- Kart 8: DynamoDB R1.2 · DA (−6, "2 ms sınırı") **ve** R2 (−4, "gecikme sınırı karşılanmaz").
- Kart 10: DynamoDB R1.2 · DA (−4, "5 ms") ama R2 (−2) yalnız kapasite ayarı için; gecikme ikinci kez sayılmamış.
R2'nin "Ne istiyoruz" metni de kart 3 ve 8'de DA satırının cümlesini kelimesi kelimesine tekrarlıyor.
Soru: "Gecikme sınırı DA'da mı, R2'de mi puanlanıyor? İkisindeyse kart 10'da neden değil?"

### 4.10 [O] Diğer çift sayımlar
- Kart 1 ElastiCache R4 (−1): "Lua script'i ekibin bakımına girer" = R1.2'deki −4'ün tekrarı.
- Kart 3 DynamoDB R4 (−1): "süre kontrolü uygulama koduna eklenir" = R1.2'deki −6'nın tekrarı.
- Kart 5 Keyspaces R4 (−4): "stream tüketicisini işletmek ek iştir" = R1.3'teki −3'ün tekrarı.
- Kart 2 R4 ve kart 9 R4 "Ne istiyoruz": "migration olmadan" (R1 ŞE ile aynı), kart 9 R4 ayrıca "arama servisine akmalı" (R1.4 ile aynı), kart 6 R4 "24 saat sonra silinmeli" (R1.3 ile aynı).

### 4.11 [O] Aynı ön ısıtma kart 4'te bedava, kart 7'de 1 puan
Kart 4 DynamoDB R4: "Serverless. Puan kırılmadı." (warm throughput gerekli). Kart 7 DynamoDB R4: "1 puan kırıldı: açılıştan önce ön ısıtma bir kez ayarlanır."

### 4.12 [O] Kart 5 ve kart 8: düz trafikte DynamoDB fiyatı iki farklı modelle hesaplanmış
- Kart 5 (65.000 yazma/sn, düz): R5 = 9, "provisioned kapasite ve reserved capacity en ucuz seçenektir".
- Kart 8 (20.000 yazma/sn, düz, "günün her saati"): R5 = 3, "us-east-1 **on-demand** liste fiyatıyla ayda on binlerce dolar".
Kart 8'de de trafik düz; provisioned ile hesaplanırsa fatura birkaç kat küçülür. Kart 8 DynamoDB'nin "net kaybetme örneği"; ama maliyet kısmı adaletsiz bir varsayıma dayanıyor. (Sonuç muhtemelen değişmez, çünkü R1'deki fark yeterli; ama okur "üç kat daha az yazan iş yükü neden üç kat daha kötü puan alıyor?" diye takılır.)
Soru: "Kart 8'de provisioned kapasite ile hesap yapınca DynamoDB'nin R5 puanı ne olur?"

### 4.13 [O] Kart 2: DynamoDB'nin puanı hikâyede olmayan durumlar için kırılmış
- R1.1 · VM (−2): "value'nun içindeki alanlara göre sorgu index olmadan yapılamaz" (bu EY konusu ve hikâyede böyle bir soru yok) ve "value 400 KB ile sınırlıdır" (profil 4 KB'tan az).
- R5 (−1): "4 KB'tan büyük profiller iki okuma birimi tüketir" (hikâye: profil 4 KB'tan az).
Kart 2'nin Ağırlıklar paragrafı ayrıca "R2 20'dir, çünkü okuma hacmi büyük ama **düzenlidir**" diyor, Karar ise "DynamoDB'yi öne geçiren bu ekibin **önceliği olan ölçek** ve operasyondur". Ölçek önce "öncelik değil", sonra "öncelik".

### 4.14 [O] Kart 7: R3 ağırlığının gerekçesi zayıf
"Kaybolan bir tutma aynı koltuğun ikinci bir kişiye **satılmasıdır**." Tutma kaybolursa ikinci kişi koltuğu **tutar**; satış ödemede olur. Ödeme anında koltuk yeniden kontrol edilmiyor mu? Edilmiyorsa bu bir tasarım hatasıdır, dayanıklılık gereksinimi değildir. Gerekçe "çift satış" yerine "müşteri ödeme ekranında koltuğunu kaybeder" olmalı ya da ödeme adımı anlatılmalı.

### 4.15 [O] MemoryDB R3: aynı neden bazen kırılıyor, bazen kırılmıyor; neden de yanlış satırda
Kart 6 ve 7: R3 = 9, "replica'lar eventually consistent'tir; kontrol primary'den okunmalıdır". Kart 3, 8, 10: R3 = 10, kırma yok. "Replica tutarlılığı" dayanıklılık (R3) değil tutarlılık (R1 · TA) konusudur.

### 4.16 [D] Küçük gerekçe soruları
- Kart 1 ElastiCache R5 (7, "bellekteki GB pahalı") ile kart 3 ElastiCache R5 (8, "veri birkaç GB'ı geçmediği için fark küçüktür"): sepet de < 1 KB ve bir günde gidiyor; neden 1 puan fark?
- Kart 10 ElastiCache R1.3 (−1): "gece işi her listeye süre koymalı ya da üzerine yazmalı". DynamoDB de aynı şeyi yapmalı ama kırılmıyor.
- Kart 4 Ağırlıklar: 200.000 istek/saniye hikâye paragrafında yok (orada "bir milyon oyuncu"); sayının nereden geldiği söylenmiyor.

### 4.17 Kartların en üstündeki "en uygun servis" doğru mu?
- Kart 3, 8, 10 (ElastiCache): ikna edici. Gerekçe engine'in doğasında (bellek, tam anında süre sonu).
- Kart 5, 9 (DynamoDB): ikna edici; ama kart 9'da klasör taşıma/yeniden adlandırma (3.1) cevaplanmalı.
- Kart 1 (DynamoDB): kazanan muhtemelen doğru; ama Aurora'nın "zaten var" durumu (4.3) ve M7'deki çelişki (5.1) yüzünden ikinci sıradaki fark ve ders belirsiz.
- Kart 2 (DynamoDB): R2 farkı (4.5) ve R4 ağırlığı (4.7) düzeltilirse fark daralır; okur olarak DocumentDB'nin kazanabileceğini düşündüm. Bu kart, kazananı en zayıf gerekçelenen karttır.
- Kart 4 (DynamoDB): ikna edici, ama küresel 10 ms (3.3) cevapsız.
- Kart 6 (DynamoDB): kazanan muhtemelen kalır, ama "yakın yarış" olmalıydı (4.2).
- Kart 7 (DynamoDB, yakın yarış): ikna edici; "yakın yarış" işareti doğru.

## 5. İki yer arasındaki çelişkiler

| # | Yer A | Yer B | Çelişki | Önem |
|---|-------|-------|---------|------|
| 5.1 | M7 giriş: "Sepette engine uyumu yakın, **kararı R2 verir**." | Kart 1, ElastiCache ile kafa kafaya: "**Kararı R3 verir**" | İkinci aday ElastiCache'e karşı R2 farkı yalnız 2,5 puan, R3 farkı 7 puan. M7'nin cümlesi yalnız üçüncü aday Aurora için doğru. | Y |
| 5.2 | M5 DynamoDB "Ne zaman seç": "**Veri resmi kayıt**, trafik büyük ya da dalgalı …" | Kart 1: "Sepet **resmi kayıt değildir**" ve kazanan DynamoDB; kart 6: işaretler türetilmiş veri, kazanan DynamoDB | M5'in ana kuralı sayfanın vitrin kartıyla çelişiyor. | Y |
| 5.3 | Yöntem: "R1'in cevabı platformdan bağımsızdır" | Kart 8 MemoryDB kafa kafaya: "Engine uyumundaki tek fark … servis tasarımından gelir" | Bkz. 4.1. | Y |
| 5.4 | Yöntem: "Zorunlu satır ve diskalifiye yoktur" | Kart 6/7 R3 "zorunlu"; kart 6'da ElastiCache "aday değil" | Bkz. 4.6. | Y |
| 5.5 | Kart 1 DynamoDB R1.2: iki database → −2 | Kart 6 DynamoDB R1.1: iki database → 0 | Bkz. 4.2. | Y |
| 5.6 | Kart 1 Aurora R2: 5.000 yazma/sn "güçlü bir writer'ın erişiminde" | Kart 2 DocumentDB R2: 100 yazma/sn "tek primary'nin sınırına dayanır" | Bkz. 4.5. | Y |
| 5.7 | Kart 8 DynamoDB R1.1: `UpdateItem … ReturnValues` tek istekte yazar ve döndürür | Kart 3 DynamoDB R1.3: "okuma ve yenileme iki ayrı istektir" | Bkz. 4.8. | Y |
| 5.8 | Kart 5 DynamoDB R5: düz trafik → provisioned, 9 | Kart 8 DynamoDB R5: düz trafik → on-demand liste fiyatı, 3 | Bkz. 4.12. | O |
| 5.9 | Kart 4 DynamoDB R4: ön ısıtma → 10 | Kart 7 DynamoDB R4: ön ısıtma → 9 | Bkz. 4.11. | O |
| 5.10 | Kart 3, 8: gecikme DA'da ve R2'de | Kart 10: gecikme yalnız DA'da | Bkz. 4.9. | O |
| 5.11 | ElastiCache Serverless R3: kart 1 = 3 | Kart 3, 8, 10 = 4 | Aynı servis, aynı neden. | O |
| 5.12 | MemoryDB R3: kart 6, 7 = 9 | Kart 3, 8, 10 = 10 | Aynı neden yalnız iki kartta kırılıyor. | O |
| 5.13 | Kart 2 Ağırlıklar: R2 "düzenli", öncelik değil | Kart 2 Karar: "bu ekibin önceliği olan ölçek" | Bkz. 4.13. | O |
| 5.14 | Ö2: "Kampanya gecesinin **50 katlık** sıçraması", "indirim gecesi üç saat boyunca **60.000** okuma/saniye" | Kart 1 (aynı mağaza tipi): 20 kat, 20.000 okuma | M1'in örneği Lale Market'e benziyor ama sayılar farklı. | D |
| 5.15 | M6: sepeti "tarayıcı" boşaltır | Kart 1: sepeti checkout boşaltır | Bkz. 1.9. | D |

## 6. Bu bölümden sonra bir meslektaşıma "DynamoDB'yi ne zaman seçerim" diye anlatabilir miyim?

**Kısmen evet.** Kartlardan çıkardığım ve rahatça anlatabileceğim kurallar:

- **DynamoDB mi, ElastiCache mi?** Veri yeniden kurulabiliyorsa (oturum, sayaç, gece hesaplanan liste), milisaniyenin altı gerekiyorsa ya da süre sonu saniyesinde kesin olmalıysa ElastiCache. Veri kaybolmamalıysa ve tek haneli milisaniye yetiyorsa DynamoDB. Kart 1, 3, 8 ve 10 bunu iyi gösteriyor. Sınır somut: 1–5 ms altı bellek ister.
- **DynamoDB mi, MemoryDB mi?** İkisi de kalıcı. MemoryDB bellek hızı ve kalıcılık **birlikte** gerektiğinde ve trafik sürekli olduğunda (node'lar her saat ödenir). Trafik düşük ya da yılda birkaç dakika sıçrıyorsa DynamoDB (kart 6, 7). Bu en iyi anlatılan ayrım.
- **DynamoDB mi, Aurora mı?** Birçok tablo arasında kural, aynı transaction'da sipariş/stok/ödeme, değişken ve JOIN'li sorular ya da raporlar varsa Aurora (M3, kart 1 ve 6'nın "koşul değişseydi" cümleleri). Soruları önceden bilinen, büyük ya da dalgalı, sunucusuz istenen iş yükleri DynamoDB.
- **DynamoDB mi, DocumentDB mi?** Belgenin içindeki alanlara göre esnek sorgular ana işse ya da ekip MongoDB biliyorsa DocumentDB; ölçek sıçrıyorsa ya da ekip sunucu istemiyorsa DynamoDB.

**Eksik olanlar (meslektaşıma güvenle anlatmamı engelleyenler):**

1. **Bir özet tablo yok.** M5 yalnız key-value servislerini (DynamoDB, ElastiCache, MemoryDB, Keyspaces, DAX) karşılaştırıyor; **DocumentDB ve Aurora M5'te yok**. Bu iki ayrımı 10 kartın kafa kafaya paragraflarından kendim toplamak zorunda kaldım. "Servis × hangi sinyal × hangi koşulda kazanır" diye 10 kartın sonuçlarını toplayan bir tablo beklerdim.
2. **DocumentDB ve Aurora'nın kazandığı tek bir kart yok.** 10 kartın 7'sini DynamoDB, 3'ünü ElastiCache kazanıyor. Sınırı yalnız "koşul değişseydi" cümlelerinden görüyorum; DynamoDB'nin **kaybettiği** ve kazananın Aurora ya da DocumentDB olduğu bir kart, sınırı çok daha net gösterirdi.
3. **DocumentDB'ye karşı ders güvenilir değil.** Kart 2'de kararı veren R2 farkı çelişkili bir tek-primary iddiasına (4.5), R4 ağırlığı ise hikâyede olmayan "ekip MongoDB bilmiyor" bilgisine (4.7) dayanıyor. Meslektaşıma "DynamoDB burada ekip MongoDB bilmediği için kazandı" demek zorunda kalırım; bu genellenebilir bir mimari kural değil.
4. **Sayısal eşikler eksik.** "Tek writer'ın erişimi" kaç yazma/saniye? On-demand kaç kata kadar ayarsız? Kaç dolardan sonra bellek, disk tabanlı istek fiyatından ucuzdur? Kartlar bu sayıları birbirine çelişen biçimde veriyor (4.5, 3.4, 4.12).
5. **"Zaten işletilen database" etkisi yok.** Gerçek kararlarda en sık durum "Aurora zaten var". Bu bölüm her adayı sıfırdan kuruluyormuş gibi puanlıyor (4.3, 4.2). Ders: "yeni bir servis eklemek ne zaman değer?" sorusu cevapsız.
6. **M5'in DynamoDB kuralı ("veri resmi kayıt") kartlarla çelişiyor** (5.2). Meslektaşıma M5'i özet diye gösteremem.

---

## Önceliklendirilmiş düzeltme listesi (yazar için)

1. R1'deki servis paketleme ve operasyon gerekçelerini R3/R4/R5'e taşı (kart 4, 5, 8, 9, 10) ve R2'nin kaynak sütununu düzelt.
2. Kart 6'yı kart 1 ile tutarlı yap (iki database, Aurora'nın aynı-transaction artısı, var olan ödeme DB'sinin marjinal maliyeti); kart 1'de var olan Aurora'nın marjinal maliyetini hesaba kat.
3. Aynı mekanizma için aynı kırmayı uygula (`expires_at` karşılaştırması, ön ısıtma, ElastiCache/MemoryDB R3); önemi yalnız ağırlıkta tut.
4. Kart 2'nin R2 gerekçesini ve R4 ağırlık nedenini yeniden yaz ya da sonucu yeniden hesapla.
5. Kart 3 DynamoDB R1.3'ü (`ReturnValues` ile tek istek) ve MemoryDB R1.4'ü (GETEX = yazma) düzelt.
6. M7'nin kart 1 cümlesini ("kararı R2 verir") ve M5'in DynamoDB satırını ("veri resmi kayıt") kartlarla uyumlu yap.
7. "Zorunlu" kelimesini kaldır ya da yönteme bir eşik ekle; ağırlık nedenlerinden aday adlarını ve "her aday yapar" ifadesini çıkar.
8. Çift sayımları kaldır (gecikme R1 DA + R2; R4'teki tekrarlar).
9. Kart 8'i provisioned fiyatla da hesapla; kart 10'a maliyet rakamı ekle.
10. Kart 9'a klasör taşıma/yeniden adlandırma, kart 4'e küresel gecikme, kart 6'ya "işlemde" durumu, kart 7'ye bölüm sayısı ve ödeme anı kontrolü ekle.
11. M5'e DocumentDB ve Aurora satırları ya da 10 kartı özetleyen bir karar tablosu ekle.
12. Bölüm 2'deki "Y" terimleri için kısa tanımlar (yazma/okuma birimi, on-demand/provisioned, ECPU, ACU, MVCC/VACUUM, warm throughput, writer/primary/replica) ekle ya da bir sözlüğe bağla.

---

## Kapanış (yazar, 2026-10-29)

Her bulgu kapatıldı. Kontrolün sonucu: `tools/check_usecases_w.py app dynamodb` OK, `check_page.sh --tr` clarity OK.

| Bulgu | Durum | Ne yapıldı |
|---|---|---|
| Y1 R1'de servis kaynaklı kırılımlar | düzeltildi | Kart 8 MemoryDB DA 10 (log gecikmesi R2'ye), kart 10 MemoryDB OY 9 (log R2'ye), kart 5 YD: Keyspaces 10, Lambda bağlantısı R4'e; kart 9 YD: DynamoDB yalnız Streams, zero-ETL R4'e; DocumentDB YD 9, Aurora YD 7 (logical decoding), tüketici R4'e; kart 4 TA: maliyet R5'e, TA'da yalnız 100 value ve transaction çakışması. R2 "Kaynağı" sütunu: "ikisi birlikte: engine'in ölçeklenme modeli ve servisin kapasite yönetimi". Callout'a kural eklendi: servis kaynaklı kırılım R1'de sayılmaz. |
| Y2 Kart 1 ve 6 tutarsız; var olan Aurora | düzeltildi | Kart 6'da DynamoDB ve MemoryDB TA'dan 1 puan ("iki ayrı database", kart 1 ile aynı sınır); Aurora TA gerekçesine aynı transaction artısı yazıldı. Kart 1 ve 6'da Aurora R4/R5 var olan database'e göre yeniden puanlandı. |
| Y3 Aynı mekanizmaya farklı kırılım | düzeltildi | Puan = "ne istiyoruz"un karşılanma derecesi, ağırlık = önem kuralı sayfaya yazıldı. Kart 3 DynamoDB YD 6 (4 kırıldı); ElastiCache R3 her kartta 4. Kalan farklar satırın isteğinden gelir (oturumda "asla okunmamalı", sepette "kendiliğinden gitsin"). |
| Y4 Tek writer çelişkisi | düzeltildi | Kart 2 DocumentDB R2: 100 yazma/sn primary için küçük; kırılım okuma ölçeğinin replica ve instance sınıfıyla yönetilmesinden. Kafa kafaya metni aynı biçimde. |
| Y5 Kart 3 "iki istek"; GETEX bir yazma | düzeltildi | DynamoDB OY: UpdateItem + ReturnValues tek istek, kırılım "her sayfa bir yazma". MemoryDB'de GETEX'in log gecikmesi R2'de (7), DA'da değil; kart 8 ile aynı kural. |
| Y6 "Zorunlu" ifadeleri | düzeltildi | Model 1'den gelen "bu kartta zorunlu" cümleleri R3 metinlerinden çıkarıldı (rest() içinde); checker "diskalifiye" ve "zorunlu gereksinim"i yasaklı terim olarak tarar. ElastiCache'in kart 6'da aday olmaması aday seçim kuralıdır (MemoryDB kafa kafaya metni açıklar). |
| Y7 Ağırlık nedenleri adaylara bakıyor | düzeltildi | Bütün "her aday yapar" / "üç aday da sağlar" nedenleri iş yükünün hikâyesinden yeniden yazıldı. MongoDB ve CQL zaten R4 "ne istiyoruz" metninde (hikâye). |
| Y8 Kart 1 M7 vs kafa kafaya; M5 "resmi kayıt" | düzeltildi | M7: "ElastiCache'e karşı R3, Aurora'ya karşı süre sonu satırı ve R2". M5: "veri kalıcı olmalı (resmi kayıt ya da kaybı istenmeyen ön hazırlık)". |
| O Gecikme ve R4 çift sayımı | düzeltildi | Gecikme bir kez: engine kaynaklıysa DA, servis kaynaklıysa R2 (kart 3 ve 8 DynamoDB R2 10). R4'ten Lua, süre kontrolü ve ön ısıtma çıkarıldı (R1/R2'de sayılıyor). |
| O Ön ısıtma, fiyat modeli, MemoryDB R3 | düzeltildi | Kart 7 R4 10; kart 8 DynamoDB R5 provisioned fiyatla (~9.500 $/ay, 4 puan); MemoryDB R3 her kartta 10 (replica tutarlılığı dayanıklılık değildir). |
| O Kart 2 hikâye dışı kırılımlar | düzeltildi | 400 KB ve >4 KB kırılımları kaldırıldı; VM 9 (tarih tipi yok, iç içe alan doğrulaması yok). |
| O "Peki ya" soruları | düzeltildi / bilinçli | Kart 9: klasör yeniden adlandırma sort key'i değiştirir (EY 9). Kart 4: global tables ve DocumentDB global cluster yazma bölgesi. Kart 7: 20 bölüm × ~1.000 koltuk. Kart 6: ilk istek sürerken gelen tekrar karar metnindeki "işlemde" durumu ile cevaplanır. Kart 10 maliyet rakamı: bilinçli olarak yok (veri boyutu ve okuma hızı verildi; fiyat bölgeye göre değişir). |
| D Terimler | düzeltildi | Kartlardan önce "kartlarda geçen servis terimleri" tablosu (okuma/yazma birimi, on-demand/provisioned, warm throughput, ECPU, ACU, writer/primary/replica, MVCC/VACUUM). |
| D Küçük dil sorunları | düzeltildi / bilinçli | Kart 10 başlığı "Kişisel öneri listeleri"; "yakın ikinci" kaldırıldı. M6 ile kart 1 arasında sepeti kimin boşalttığı farkı: M6 Lale Market'in gerçek akışını anlatır (tarayıcı commit'ten sonra siler), kart 1 aynı akışın "checkout" adımıdır; çelişki değil. Ö2'deki 50 kat bir örnektir. |
| Son soru: özet ve M5 | düzeltildi | Kartlardan sonra on kartın özet tablosu ve okunuşu (ne zaman DynamoDB, ne zaman Valkey, MemoryDB ve ElastiCache ayrımı, DocumentDB ve Aurora'nın engine olarak güçlü yanları). |

Puan değişiklikleri sonrası sonuçlar: kart 5 (IoT) artık yakın yarış (fark 5), kart 10'da MemoryDB DynamoDB'nin önüne geçti (79,5 / 79). Diğer kartların en uygun servisi değişmedi.
