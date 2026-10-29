# Aurora PostgreSQL E2E (TR) — soğuk okuyucu raporu

Okuyucu profili: daha önce relational database ya da Aurora PostgreSQL kullanmamış biri. Sayfa `/tmp/aurora_tr.html` baştan sona okundu: Bölüm A (A1–A10), Mimar gözüyle (M1–M7, on kart ve beş karar simülasyonunun gömülü adım metinleri), Bölüm B (B1–B7, dokuz simülasyonun adım metinleri), Bölüm C (C1–C3), hatırlama testi, dört görsel ve caption'ları. Hiçbir şey düzeltilmedi; sadece bu rapor yazıldı.

Bölüm kimlikleri: h2 id'leri (ör. A3 `#keys`, M2 `#usecases`, B5 `#locks`).

---

## 1. Anlamadığım cümleler (ve ne beklediğim)

- **A1 `#why`** — "Başarılı dediği her değişikliği önce diskteki bir log'a yazar; elektrik kesintisi 'tamam' denen bir değişikliği kaybettirmez." — "log" nedir, neden diske yazmak kaybı önler? Bir cümlelik tanım bekledim: "log, her değişikliğin sırayla eklendiği bir dosyadır; sunucu yeniden başlayınca bu dosyadan devam eder." Kelime B1/B6'da WAL olarak geri geliyor ama orada da tanım yok.
- **A2 `#model`** — "Koşul NULL'a çıkarsa (NULL >= 0 gibi) CHECK onu kabul eder; bu yüzden NOT NULL ayrıca yazılır." — Bu satır NULL'un ne olduğu anlatılmadan önce geliyor (NULL açıklaması aynı bölümde daha sonra, "Aklına şu gelebilir" kutusunda). "NULL >= 0" neden "kabul" demek, "red" değil? Beklediğim: "Karşılaştırmanın sonucu doğru ya da yanlış değil, 'bilinmiyor'dur; CHECK sadece 'yanlış'ı reddeder."
- **A2 `#model`** — "Type değiştirme | Mümkünse dönüştürür; dönüşmeyen bir değer varsa reddeder ve table yeniden yazılabilir." — "table yeniden yazılabilir" kim tarafından, ne demek? Beklediğim: "database bütün table'ı diskte baştan yazar; büyük table'da bu dakikalar sürer ve table o sürede kilitlidir."
- **A5 `#index`** — "WHERE customer_id = 'C00450' için planner customers_pkey'i seçer: 3 blok okuma." ve "her seviyede bir blok okur" — "blok" nedir? B1'de aynı şeye "page" deniyor. Tek kelime bekledim; sayfa "isimler standarttır ve sayfanın sonuna kadar değişmez" diyor ama burada değişiyor.
- **A5 `#index`** — "order_date BETWEEN ... | Evet, order_date'te | Index aralığı, sonra o row'lar" — "Index aralığı" bir işlem mi, bir yapı mı? Beklediğim: "index'in sıralı listesinde başlangıçtan bitişe kadar bitişik kısım okunur, sonra her entry'nin gösterdiği row."
- **A6 `#tx`** — "Daha katı seviyeler (Repeatable Read, Serializable) bir transaction'ın başından sonuna aynı resmi görmesini sağlar, ama 'applications using this level must be prepared to retry transactions due to serialization failures'" — Bu iki seviye ne zaman gerekir, "serialization failure" nedir? Alıntı çevrilmiş ama neden retry gerektiği anlatılmamış. Beklediğim: bir örnek ("rapor transaction'ı sırasında stok değişirse Serializable ikinciyi iptal eder") ya da "bu sayfada varsayılan seviye yeter" cümlesi.
- **A8 `#replication`** — "bu, key-value database'in A4'teki DynamoDB sayfasında anlattığı partition fikrinin ta kendisidir" — Bu sayfanın A4'ü SQL bölümü; önce oraya baktım, partition bulamadım. Beklediğim: "DynamoDB tutorial'ının A4 bölümünde".
- **B1 `#names`** — "Verinin diskteki birimi | ... | page, 8 kB | PostgreSQL ile aynı; Aurora Standard'da I/O 4 KB birimlerle sayılır" — Page 8 kB ise bir page okumak 2 I/O mu sayılıyor? Bu satırı okuyunca B6'daki I/O ücretini hesaplayamadım. Beklediğim: bir cümle ile ilişki ("bir 8 kB page okuması genellikle 1 okuma I/O'su, yazma 4 KB birimlerle").
- **B2 `#reads`** — "cost=0.28..8.29 rows=1 | Planner'ın çalıştırmadan önceki tahmini: kendi birimiyle bir maliyet ve beklenen 1 row." — İki sayı var (0.28 ve 8.29); neden iki? Beklediğim: "ilk row'a kadar olan maliyet .. bütün row'lara kadar olan maliyet".
- **B4 `#constraints` / B5 `#locks`** — B4: "123 - 100.000 = -99.876 ve CHECK bunu reddetti; stok 123 kaldı." B5: "Stok 124'ten 123'e indi, sonra ROLLBACK onu 124'e geri getirdi". A3'teki öğretici tabloda P0001 stoğu 127. Aynı ürün için üç farklı "canlı" stok. Sayfa öğretici değerlerin örnek olduğunu söylüyor, ama iki canlı ölçüm (123 ve 124) birbirini tutmuyor; hangisi gerçek? Beklediğim: canlı çıktıların aynı anda alınmış olması ya da "iki ölçüm farklı günlerde alındı" notu.
- **C2 `#service`** (caption) — "writer'dan storage'a senkron yazma, reader'lara asenkron replication" — C2 metni ve A8 caption'ı "writer dosyaları reader'lara kopyalamaz, reader aynı storage'ı okur" diyor. Peki reader'lara "replication" nedir? İki cümle birbirini çürütüyor gibi okundu. Beklediğim: "reader'ın belleğindeki eski page'leri geçersiz kılmak için writer küçük bir bilgi gönderir; veri değil."
- **M2 `#usecases` kart 3, R4** — "süresi dolan rezervasyon için zamanlanmış bir temizlik işi yazılır (row başına süre sonu yoktur)" — "row başına süre sonu" ne demek, nerede var? DynamoDB'nin TTL'i kastediliyor ama bu sayfada TTL tanımlanmamış. Beklediğim: "PostgreSQL'de bir row'a 'şu saatte kendini sil' denemez; DynamoDB'de (TTL) denebilir."
- **M2 `#usecases` kart 5, R1** — "database her sorguya tenant filtresini kendisi ekler ... (Ö6, view ve policy)" — A10 özetine göre row-level security Ö8'dir, Ö6 değil. Hangi numaraya döneceğimi bilemedim.
- **M6 `#lalemarket-arch`** — "bir production sisteminde bunlar genellikle event olarak taşınır (transactional outbox deseni ve bir mesaj servisi)" — "transactional outbox" nedir? Tek cümle tanım bekledim ("event'i aynı transaction'da bir outbox table'ına yazıp sonra ayrı bir işle göndermek").

## 2. Anlamını öğrenmeden önce karşıma çıkan terimler

- **A2 `#model`** — "migration" (A7'de "migration ile dağıtılır", M2 kart 1'de "bir migration ile yapılabilir; ekip bunu biliyor") — Sayfada hiç tanımlanmıyor. Ben bilmiyordum: "schema değişikliğini sürümlü bir dosya olarak yazıp sırayla uygulamak" diye bir cümle bekledim; kartların R4 puanları bu kelimeye dayanıyor.
- **A8 `#replication`** — "shard", "Aurora Limitless", "Global Database", "Aurora DSQL" — tabloda tanımsız geçiyor; M5'te kısmen açıklanıyor ama "shard" hiçbir yerde "verinin her biri kendi writer'ı olan parçalara bölünmesi" diye tanımlanmıyor.
- **A8 `#replication` / M2 kart 7** — "partition" iki anlamda kullanılıyor: A8'de DynamoDB'nin veri bölme fikri, kart 7 ve 10'da PostgreSQL'in "table'ı zamana göre parçalara bölme" özelliği. İkincisi hiç tanımlanmıyor (pg_partman tablosunda bile "partition" bilinen bir şey gibi). İkisinin aynı şey olup olmadığını anlamadım.
- **A9 `#ext`** — "GIN index", "GiST index", "HNSW index", "BRIN" (A10) — A5 sadece B-tree'yi anlatıyor. Bu türlerin ne yaptığı yok; B7'de "GIN: belgenin içindeki anahtar ve değerleri index'ler" tek satırı var, GiST için "'içinde mi' sorularını hızlandırır". Önce A9'da birer cümle bekledim.
- **A10 `#summary`** — matris hücreleri: "exclusion constraint", "window fonksiyonları, CTE", "deferrable constraint", "Patroni", "Group Replication", "InnoDB" — Hiçbiri tanımlı değil; soğuk okuyucu olarak matristeki ✓/½ farkını değerlendiremedim. "exclusion constraint" B4'te, "deferrable" hiçbir yerde açıklanmıyor (kart 7 "commit anında doğrular" diyor, bu yetmedi).
- **M1 `#signals` Ö3** — "Redshift; Aurora'dan zero-ETL ile beslenir" — zero-ETL M5'te tanımlanıyor; M1'de ilk kez okudum.
- **M2 `#usecases` kart 1, R2/R5** — "Serverless v2", "0,5 ACU adımlarıyla", "Aurora Standard'da I/O isteği başına ek ücret" — ACU, Serverless v2, Standard/I-O-Optimized M5'te tanımlanıyor; on kartı okurken bu terimlerle puan kırılıyor ve ben henüz ne olduklarını bilmiyordum.
- **M2 `#usecases` (bütün kartlar)** — DynamoDB sözlüğü: "TransactWriteItems", "ConditionExpression", "GSI", "TTL", "Streams", "on-demand", "partition key / sort key", "LeadingKeys", "attribute_not_exists", "geohash" — Bu sayfada hiçbiri tanımlı değil; A1 sadece "bkz. DynamoDB tutorial'ı" diyor. En yakın alternatifin gerekçesi, bilmediğim bir dille yazılmış.
- **M2 `#usecases` (kart 1, 2, 4, 9)** — DocumentDB sözlüğü: "$lookup", "multikey index", "schema validation", "updateOne / $push", "collection" — tanımsız.
- **M2 `#usecases` (kart 3, 8)** — ElastiCache sözlüğü: "SET NX EX 900", "DECRBY", "sorted set", "Lua script", "ECPU", "MemoryDB" — tanımsız.
- **M2 `#usecases` (kart 6)** — Redshift/OpenSearch sözlüğü: "column storage", "MPP", "RPU", "sort key / distribution key", "mapping", "shard", "refresh aralığı", "facet", "reindex" — tanımsız. Yalnız "column storage" kafa kafaya paragrafında açıklanıyor; iyi.
- **M2 `#usecases` kart 8** — "EXCLUDE USING gist (doctor_id WITH =, slot WITH &&)" — "&&" operatörü ve "tstzrange" tipi ancak B1'in type tablosunda ve B4'te kısaca geçiyor; "&&" hiç açıklanmıyor ("çakışıyor mu" anlamı).
- **B1 `#names`** — "writer endpoint'ten 3,4 milisaniyede geldi" — "endpoint" C2'de tanımlanıyor; A8'de "cluster adresi" deniyor. B1'de ilk kez "endpoint" okudum.
- **B1 `#names`** — "InnoDB'de table bu sırayla saklanır (clustered)", "table sırası serbest (heap)" — "clustered", "heap", "InnoDB" tanımsız.
- **B6 `#cost` / M2 kart 1** — "psycopg", "bağlantı havuzu", "RDS Proxy" — tanımsız (Python driver'ı, bağlantı yeniden kullanımı).
- **C2 `#service`** — "rds_superuser rolü", "parameter group", "backtrack" — tanımsız.

## 3. "Ya şöyle olursa?" dediğim ve cevabı olmayan yerler (eksik durumlar)

- **A5 `#index`** — Tablo hep tek column'lu koşullar. Ya WHERE city = 'İstanbul' AND segment = 'premium' ise? İki index mi gerekir, iki column'lu tek index mi, planner hangisini seçer? Lale Market'in order_items'ında iki column'lu primary key var ama "iki column'lu index ile arama" durumu yok.
- **A6 `#tx`** — "Sunucu COMMIT'ten önce durdu" var; ya uygulama (ya da ağ) transaction açıkken çökerse? Row lock'lar sonsuza kadar mı kalır? Beklediğim satır: "bağlantı kopunca database açık transaction'ı geri alır".
- **A6 `#tx`** — "İkinci transaction bekler" deniyor; ya çok uzun beklerse? Bir zaman aşımı var mı (lock_timeout / statement_timeout), uygulama ne görür?
- **A6 `#tx`** — "Transaction içinde bir cümle hata verdi → sadece ROLLBACK kabul edilir." Ya bir sepetteki beş üründen sadece biri stoksuzsa ve diğer dördünü yine de satmak istersem? Bütün transaction mı gider, bir ara nokta (SAVEPOINT) var mı?
- **A6 `#tx` + B5 `#locks` + M2 kart 1** — B5 simülasyonunda ödeme servisi iki stok UPDATE'inden sonra, yani transaction açıkken ve row lock'lar alınmışken çağrılıyor. A6 "uzun açık kalan transaction" ve A7 "dış servis çağrısı database'in işi değildir" diyor. Ya ödeme servisi 5 saniye sürerse: P0001 row'u 5 saniye kilitli mi? Diğer müşteriler bekler mi? Kart 1 bunu puan kırma nedeni olarak saymıyor ve sayfa çelişkiyi çözmüyor.
- **A8 `#replication` / C2 `#service`** — "Failover sırasında açık bağlantı | Bağlantı kopar; uygulama aynı ada yeniden bağlanır." Ya failover anında bir checkout transaction'ı yarıdaydıysa? Geri alınır mı, uygulama baştan mı dener, müşteri iki kez ödeme görebilir mi?
- **M2 `#usecases` kart 3** — "erken çalışırsa ödeme sırasındaki rezervasyon düşer" diyor ama çözümü söylemiyor. Temizlik işi ile onay aynı saniyede yarışırsa ne olur? Koşullu DELETE (expires_at < now()) ve koşullu onay UPDATE yeter mi?
- **M2 `#usecases` kart 4** — "'verimi sil' ... ON DELETE CASCADE ile tek bir DELETE'tir" ve aynı kartta "siparişler aynı database'te müşteriye bağlıdır". Ya müşteri silinince siparişler? CASCADE onları da siler (kart 7 kayıtların yedi yıl saklanması gerektiğini söylüyor); SET NULL mı, anonimleştirme mi? KVKK ile muhasebe saklama kuralı çatışıyor ve sayfa cevap vermiyor.
- **M2 `#usecases` kart 5** — "gürültülü tenant için uygulama tarafında kota gerekir" — ya bir tenant kendi ayrı database'ini isterse (kurumsal müşteri)? RLS modeli bunu nasıl karşılar, hiç karşılamaz mı?
- **M5 `#aws`** — Seçenekler listeleniyor; ya zaten RDS for PostgreSQL işletiyorsam ve Aurora'ya geçmek istersem? Yol var mı, veri nasıl taşınır, kesinti olur mu? Kart 5 ve 7 "RDS savunulabilir" diyor ama geçişi hiç anmıyor.
- **B6 `#cost`** — R5 puanları on kartta "minimum ACU boş gecede de ödenir" ile kırılıyor; ya bu kaç para? Sayfa hiçbir yerde tek bir fiyat ya da formül örneği vermiyor (ör. "0,5 ACU × 24 saat × 30 gün = ..."). Lale Market'in kendi cluster'ı ayda ne tutuyor sorusunun cevabı yok.
- **M4 `#questions`** — "Tek bir cevap ne kadar hızlı olmalı? Milisaniyeler relational için normaldir." Ya "saniyede kaç yazma" sorusunun cevabı tek writer'ın sınırına yakınsa — sınır tam olarak nedir? A8 checkpoint'i 50.000/s, hatırlama testi 40.000/s, kartlar "on binler" diyor; ama "bir Aurora writer'ı kaç kısa transaction/s taşır" sayısı yok. Sınırı bilmeden "yaklaşıyor muyum" sorusuna cevap veremiyorum.

## 4. İkna olmadığım karar gerekçeleri (M2 kartları ve M7 simülasyonları) ve mimara soracağım soru

- **M2 `#usecases` puan ölçeği** — "Zorunlu bir gereksinimde 0 ya da 1 alan aday diskalifiye olur" — On kartta hiçbir aday zorunlu bir gereksinimde 0–1 almıyor (en düşük 3). Kural hiç çalışmıyor ve toplamda zorunlu ile tercihli aynı ağırlıkta toplanıyor. Soru: Zorunlu bir gereksinimde 3 alan aday (kart 6'da Aurora R2, kart 10'da DynamoDB R1) neden toplam puanla yarışmaya devam ediyor; zorunlu gereksinimin ağırlığı yok mu?
- **M2 kart 6 (raporlama) / M7 simülasyon 2** — "Karar: Redshift 45, OpenSearch 32, Aurora 31" — JOIN yapamayan OpenSearch (zorunlu R1'de 5), JOIN yapan Aurora'nın önünde ikinci. Finans soruları JOIN istiyor diye kartın kendisi söylüyor. Soru: Zorunlu gereksinimi karşılamayan bir aday, ölçek puanıyla ikinci olabiliyorsa, toplam puan gerçekten "mimari karar" mı, yoksa sadece bir tablo mu?
- **M2 kart 3, 4, 8 (Aurora 44–43, 45–43, 44–43)** — Her üçünde DynamoDB R4'te "ekip SQL biliyor, key tasarımı öğrenir" diye 2 puan kaybediyor ve fark 1–2 puan. Soru: Ekip DynamoDB bilseydi üç karar da tersine döner miydi? Öyleyse karar "R1'in kural kısmı" değil, ekip bilgisi (tercihli R4) demektir; kart metni ise "yarışı R1 belirler" diyor.
- **M2 kart 1, R2 (Aurora 10)** — "Serverless v2 kampanya akşamı kapasiteyi 0,5 ACU adımlarıyla artırır. Puan kırılmadı." Kart 3 ve 8'de aynı mekanizma ("minimum ACU önceden yükseltilmeli, 100 ms tepe anında zorlanabilir") 2 puan kırıyor. Soru: Saniyede 10 checkout + 300 okuma için ACU büyüme gecikmesi neden sorun değil de saniyede 50 randevu için sorun?
- **M2 kart 1 / B5** — Aurora R1 = 10 "Dört yazma tek transaction'dır ... Puan kırılmadı." Ama B5 simülasyonunda ödeme servisi transaction'ın içinde çağrılıyor ve A6 bunu bir tehlike sayıyor. Soru: Ödeme dış bir servisse "dört yazma tek transaction" gerçekten mümkün mü, yoksa stok kilitlerini ödeme süresince tutmayı kabul mü ediyoruz?
- **M2 kart 7 (defter), R3 (Aurora 10, RDS 9)** — "1 puan kırıldı: tek standby kopya ve ... 60 ile 120 saniye failover süresi." Aynı kartta RDS "senkron standby" diye tanımlanıyor; senkron kopya varsa commit edilmiş posting kaybolmaz. Karar paragrafı ise "sıfır kayıp zorunludur" diye Aurora'yı seçiyor. Soru: RDS Multi-AZ'de commit edilmiş bir posting gerçekten kaybolabilir mi? Kaybolmuyorsa R3'teki fark "kayıp" değil "kesinti süresi"dir ve karar cümlesi yanlış gerekçeye dayanıyor.
- **M2 kart 8 (randevu), DynamoDB R1 = 6** — "'çakışan aralık yoksa' koşulu DynamoDB'de yazılamaz." Kartın kendisi aralıkların 15, 30, 45 dakika olduğunu söylüyor; hepsi 15'in katı. "Bir koşul değişseydi: aralıklar sabit hücreler olsaydı DynamoDB kazanırdı" — ama zaten sabit hücrelere bölünebiliyorlar. Soru: Aralıklar hep 15'in katıysa hücre modeli (2–3 item'lık transaction) neden "yazılamaz" sayılıyor?
- **M2 kart 3 (stok), Aurora R2 = 8** — "aynı on ürünün satırları tek writer'da birbirini bekler; bu kuyruk 100 ms sınırını tepe anında zorlar." Saniyede 300'ün yarısı on ürüne gidiyorsa row başına 15 kısa transaction/s; sayfa B2'de tek bir UPDATE'in milisaniyenin altında sürdüğünü gösteriyor. Soru: Row başına 15/s gerçekten 100 ms'yi zorlar mı? Bir ölçüm var mı, yoksa tahmin mi?
- **M2 kart 3, DynamoDB R1 = 6 ile Aurora R4 = 8** — DynamoDB "süresi dolan rezervasyonun sayacı geri vermesi için ayrı bir Streams tüketicisi gerekir" diye R1'den 4 puan kaybediyor; Aurora da aynı iş için "zamanlanmış temizlik işi yazılır" ama bunu R4'ten 2 puan kaybediyor. Aynı problem, iki adayda farklı gereksinimden ve farklı miktarda kırılıyor. Soru: Neden simetrik puanlanmadı?
- **M2 kart 4 (hesaplar), DynamoDB R1 = 6** — "'verimi sil' grubun okunup her item'ın tek tek silinmesidir." Kart 1 TransactWriteItems'ın 100 item'ı ya hep ya hiç yazdığını söylüyor; bir müşterinin adres+izin+kart item'ları 100'ün çok altında. Soru: Aynı partition'daki item'lar tek transaction ile silinemez mi? Silinebiliyorsa "eksiksiz silme" farkı nerede?
- **M2 kart 5 (SaaS), R4 (Aurora 9, RDS 8)** — Aurora'da "policy'ler her role için test edilmelidir" diye 1 puan kırılıyor; RDS aynı PostgreSQL ve aynı policy'leri ister ama onun puanı storage/IOPS için kırılıyor, policy testi için değil. Soru: Aynı engine'in iki biçiminde aynı iş neden sadece birinde puan kırıyor?
- **M2 kart 5** — R5 "Veri?" verilmemiş (diğer kartlarda "birkaç GB", "on GB" var). RDS R2'de "her read replica tam kopya, kurulması saatler sürer" deniyor. Soru: 800 tenant'ın fatura verisi kaç GB ki replica kurulumu saatler sürüyor?
- **M7 `#decide` checkpoint (sinema)** — Doğru cevap "Transaction ve UNIQUE (showing, seat) ile Aurora"; DynamoDB seçeneği "her koltuk item'ında TTL" diye yazılmış. Kart 1 ve kart 8'in kendi metni DynamoDB'nin koşullu yazma + TransactWriteItems ile "koltuk + ödeme" ikilisini ya hep ya hiç yazabildiğini söylüyor; koltuk sabit bir hücredir. Soru: Saniyede "birkaç yüz" satışta DynamoDB neden yanlış cevap? Bu checkpoint, sayfanın kendi kartlarıyla çelişiyor ve Aurora/DynamoDB sınırını bulandırıyor.
- **M7 `#decide` (beş simülasyon)** — "Oynat'a basmadan önce kartı okuyup kazananı tahmin et." Simülasyon başlıkları kazananı zaten söylüyor: "net bir kazanma", "net bir kaybetme: Redshift kazanır", "Aurora mı DocumentDB mi? (yakın yarış)". Tahmin edecek bir şey kalmıyor. Ayrıca adım metinleri kart metninin birebir kopyası; simülasyon yeni bir şey öğretmiyor, sadece aynı tabloyu beş tıkla dolduruyor.
- **M2 `#usecases` (R5 genel)** — On kartta maliyet 10 üzerinden puanlanıyor ama sayfada tek bir fiyat, birim ya da örnek hesap yok ("DynamoDB boş gecede sıfıra yakın", "minimum ACU ödenir"). Soru: Kart 1 için iki adayın aylık faturası kabaca kaç dolar? Sayı olmadan R5 puanlarını ne savunabilirim ne çürütebilirim.

## 5. EN/TR karşılaştırması

- Sadece Türkçe sayfa verildi; karşılaştırma yapılmadı. Not: sayfada "Ilişkisel (Aurora PostgreSQL)" biçiminde noktasız büyük I ile yazılmış 12 başlık var (puan tablolarında "ilişkisel", gerekçe başlıklarında "Ilişkisel"); Türkçe okuyucu için yazım hatası gibi görünüyor.

## 6. Caption'ı neye bakacağımı söylemeyen görseller

- **A3 `#keys`** (aurora-er-diagram.png) — "Şuna bak: her kutu bir table ... Lale Market'in dört table'ı aynı deseni izler: orders, customers'tan; order_items, orders ve products'tan ödünç alır." — Resim Lale Market'in değil, Wooptoo'nun genel bir şeması; caption'ı okuyunca resimde orders/customers aradım, yok. Caption resimdeki table adlarını ve okun hangi uçta "sahip", hangi uçta "ödünç alan" olduğunu söylemiyor.
- **A8 `#replication` ve C2 `#service`** (aurora-cluster.png, aynı resim iki kez) — A8 caption'ı: "Writer dosyaları reader'lara kopyalamaz: reader'lar aynı storage'ı okur." C2 caption'ı aynı resim için: "reader'lara asenkron replication". İki caption aynı oku iki zıt şekilde anlatıyor; resimde "replication" yazan oku gördüm ama hangi caption'a inanacağımı bilemedim.
- **C2 `#service`** (ikinci kullanım) — "aynı resmî şema, şimdi C2'nin adlarıyla" — Resim birebir aynı; caption yeni bir bakış noktası vermiyor (ör. "altta 'Amazon S3' kutusuna bak, A8'de buradan bahsetmedik"). İkinci kez neden gösterildiğini anlamadım.
- **M7 `#decide` ve B2–C2 simülasyonları** — Her simülasyon kutusunun altında aynı renk açıklaması var: "okunuyor · eşleşti · okundu ve atlandı · kilitli · sonuçta yeni · reddedildi ya da yanlış". Puan simülasyonlarında (M7) "kilitli", "okundu ve atlandı" gibi durumlar yok; hangi rengin ne anlama geldiğini puan tablosunda bulamadım. Puan tablolarının kendi legend'i ("✓" ne demek, "yarışta" ne demek) yok.

---

## Sonuç

**Bir meslektaşıma "ne zaman DynamoDB değil Aurora PostgreSQL" diye açıklayabilir miyim?** Büyük ölçüde evet. Sayfadan çıkan ve savunabileceğim cümle şu: *Veri birbirine bağlı birkaç şeyin resmi kaydıysa (müşteri–sipariş–satır–ürün), kurallar tek bir kaydın içinde kalmayıp kayıtlar arasındaysa (foreign key, CHECK, "çakışan aralık yok", "toplam sıfır"), birkaç table'a yazma ya hep ya hiç olmalıysa, yarın hangi soruların sorulacağı bilinmiyorsa ve yazma hacmi tek bir writer'ın altındaysa Aurora PostgreSQL; erişim hep bilinen tek bir key ile, saniyede on binlerce yazma, kayıtlar arasında kural yok ve istek başına ödeme isteniyorsa DynamoDB.* A1'in dört problemi, A3'ün "sahip/ödünç alan" dili, A6'nın koşullu UPDATE'i ve M3 tablosu bu cümleyi iyi kuruyor.

**Eksik olan ve "neden"i zayıflatan dört şey:**

1. **Sınırın sayısı yok.** "Tek writer'ın sınırı" her yerde "on binler" diye geçiyor ama bir Aurora writer'ının gerçekten kaç kısa transaction/s taşıdığı hiç söylenmiyor. Meslektaşım "bizim yük saniyede 2.000 yazma, hangi taraf?" derse sayfadan cevap üretemem.
2. **DynamoDB tarafı tanımsız bir dille yazılmış.** TransactWriteItems, ConditionExpression, GSI, TTL, Streams bu sayfada hiç açıklanmıyor; on kartın "kafa kafaya" paragraflarını okudum ama karşı tarafın argümanını kendi sözlerimle kuramıyorum. "DynamoDB'de bu kuralları kodda korumak somut olarak ne iş?" sorusuna bir paragraf gerekir.
3. **Yakın yarışlar ekip bilgisine dayanıyor.** Kart 3, 4 ve 8'de 1–2 puanlık fark, DynamoDB'nin "ekip SQL biliyor" diye kaybettiği 2 puanla aynı büyüklükte. DynamoDB bilen bir meslektaşa bu üç kartı savunamam; kart metni "yarışı R1 belirler" dese de puanlar bunu göstermiyor. Sinema checkpoint'i (M7) ve kart 7'nin "sıfır kayıp" gerekçesi de kendi kartlarıyla çelişiyor.
4. **Maliyet puanı sayısız.** R5 on kartta puanlanıyor ama tek bir fiyat ya da örnek fatura yok. "Boş gecede 0,5 ACU ödenir" ile "istek başına sıfıra yakın" arasındaki farkın kaç dolar olduğunu bilmeden maliyeti karara katamam.

Bunlara ek olarak sayfanın kendi içindeki üç tutarsızlık (P0001 stoğu 123/124/127; RLS'nin Ö6 mi Ö8 mi olduğu; reader'lara "replication var / yok" caption'ları) güvenimi azalttı: hangi sayıya ve hangi cümleye dayanacağımı iki kez kontrol etmek zorunda kaldım.

---

## Kapanış (yazarın cevapları, 2026-10-29)

Her bulgu ya sayfada düzeltildi ya da aşağıda bir gerekçeyle kapatıldı. Düzeltmelerden sonra `check_usecases.py` (usecases: OK), `check_page.sh --tr` (clarity: OK) ve simülasyon testi yeniden geçti.

### 1. Anlaşılmayan cümleler
- A1 log: düzeltildi, parantez içinde tanım (log, WAL).
- A2 NULL ve CHECK: düzeltildi, "sonuç bilinmiyor çıkarsa CHECK sadece yanlışı reddeder".
- A2 type değiştirme: düzeltildi, "table diskte baştan yazılır, kilitli kalır".
- A5 blok/page: düzeltildi; "page" A5'te tanımlandı ve sayfanın tamamında tek ad kullanılıyor (kartlar dahil).
- A5 index aralığı: düzeltildi, işlem cümleyle anlatıldı.
- A6 Serializable: düzeltildi, örnek ve "bu sayfadaki örnekler varsayılan seviyeyle çalışır" eklendi.
- A8 A4 referansı: düzeltildi ("DynamoDB tutorial'ının A4 bölümü").
- B1 I/O 4 KB: düzeltildi, okuma ve yazma I/O'su ayrıldı.
- B2 cost iki sayı: düzeltildi (ilk row'a kadar / bütün row'lara kadar).
- B4/B5 stok 123/124/127: düzeltildi; B4'te aritmetik hatası vardı (124 - 100.000), canlı ölçümün ana göre değiştiği ve 127'nin öğretici örnek olduğu yazıldı.
- C2 caption "asenkron replication": düzeltildi; A8 ve C2 caption'ları artık aynı şeyi söylüyor (reader'a giden ok veri değil, bellek kopyasını güncelleyen kayıtlardır).
- Kart 3 "row başına süre sonu": düzeltildi, DynamoDB TTL'ine açık atıf.
- Kart 5 Ö6/Ö8: düzeltildi (Ö8).
- M6 transactional outbox: düzeltildi, tek cümle tanım.

### 2. Tanımsız terimler
- migration: A2'de tanımlandı. shard: A8'de tanımlandı. PostgreSQL partition'ı: kart 7'de ilk geçtiği yerde tanımlandı.
- GIN, GiST, BRIN, HNSW: A5 Index kartında birer cümle.
- A10 matris adları (exclusion, deferrable, window/CTE, InnoDB, Patroni, Group Replication): matrisin altına bir paragraf.
- zero-ETL: M1 Ö3'te parantez; M5'te tam tanım.
- Kartlardaki Aurora terimleri (Serverless v2, ACU, Standard/I/O-Optimized, point-in-time restore) ve alternatiflerin terimleri (TransactWriteItems, ConditionExpression, GSI, TTL, Streams, on-demand, $lookup, multikey, SET NX EX, DECRBY, Lua, ECPU, MPP, RPU, mapping, facet, reindex): M2'nin başına, ölçek tablosunun altına bir sözlük paragrafı eklendi. "&&" operatörü kart 8'de açıklandı.
- B1 endpoint: düzeltildi ("writer adresi"); clustered/heap/InnoDB: düzeltildi. psycopg, bağlantı havuzu, RDS Proxy: B6'da açıklandı. rds_superuser, parameter group, backtrack: C2'de açıklandı.

### 3. Eksik durumlar
- A5 iki column'lu koşul: tabloya satır eklendi (iki column'lu index, bitmap birleştirme).
- A6 bağlantı kopması, SAVEPOINT: tabloya iki satır eklendi. Lock bekleme süresi: lock_timeout / statement_timeout kutuya eklendi.
- Ödeme servisi transaction içinde: B5'te açıkça yazıldı (workshop sadeleştirmesi; üretimde önce yetkilendirme, kısa transaction); kart 1'in karar paragrafına eklendi.
- Failover anında yarım checkout: C2 endpoint tablosuna satır (geri alma, yeniden deneme, istemcide üretilen sipariş id'si).
- Kart 3 temizlik ile onay yarışı: karar paragrafında koşullu DELETE ve koşullu UPDATE'in aynı row lock sırasına girdiği yazıldı.
- Kart 4 KVKK ile muhasebe saklama: R1 gerekçesi düzeltildi (adres, izin, kart CASCADE; sipariş SET NULL ve anonimleştirme).
- Kart 5 kendi database'ini isteyen tenant: karar paragrafına eklendi (ayrı cluster, modelin dışında).
- M5 RDS'ten Aurora'ya geçiş: paragraf ve resmi link eklendi.
- B6 maliyet: ACU-saat formülü (730 saat × 0,5 ACU × 2 instance) eklendi; fiyat yazılmadı, fiyat sayfasına link verildi. Gerekçe: fiyatlar bölgeye göre ve zamanla değişir, sayfa fiyatla eskimemeli.
- Tek writer'ın sayısal sınırı: A8 kutusuna "AWS tek bir sayı vermez; ACU, transaction boyutu ve aynı row'a yarışa bağlıdır; pgbench ile ölç" yazıldı. Gerekçe: resmi dokümantasyonda böyle bir sayı yoktur ve uydurulmaz.

### 4. İkna etmeyen gerekçeler
- Diskalifiye kuralının hiç çalışmaması ve zorunlu/tercihli ağırlığı: gerekçe ile kapatıldı. Ölçek bütün sayfalarda ortaktır (DynamoDB sayfasıyla aynı); diskalifiye yalnız 0–1'de olur ve bu sayfada hiçbir aday zorunlu bir gereksinimde o kadar düşmez. Zorunlu gereksinimde düşük puan toplamda zaten görünür: kart 6'da Aurora (R2 = 4) ve kart 10'da DynamoDB (R1 = 3) sonuncudur.
- Kart 6 OpenSearch'ün Aurora'nın önünde olması: düzeltildi; Aurora R2 3→4 (SQL aynı, reader'a yönlendirme), OpenSearch R1 5→4 (JOIN yok). Yeni karar: Redshift 45, Aurora 32, OpenSearch 31.
- Kart 3, 4, 8'de ekip bilgisi: kabul edildi ve açıkça yazıldı; üç kartın "bir koşul değişseydi" cümlesine "ekip DynamoDB'yi SQL kadar iyi bilseydi yarış tersine dönebilirdi" eklendi. R4 gerçek bir gereksinimdir ve bu iş yüklerinde ekip SQL biliyor; kart metni bunu artık saklamıyor.
- Kart 1 R2 = 10 ile kart 3/8 R2 = 8 farkı: kart 1'in gerekçesine neden eklendi (saniyede 10 checkout, yoğun satır yarışı yok).
- Kart 1 ödeme dış serviste: B5 ve karar paragrafında yazıldı; R1 puanı 10 kaldı, çünkü dört yazmanın tek transaction olması ödemenin yetkilendirme adımıyla mümkündür.
- Kart 7 RDS R3: düzeltildi; "senkron standby ile commit edilmiş posting kaybolmaz; fark kesinti süresi ve kopya sayısıdır". Kafa kafaya ve karar paragrafı buna göre yeniden yazıldı.
- Kart 8 DynamoDB "yazılamaz": düzeltildi ("tek item koşulu olarak yazılamaz; 15 dakikalık hücrelerle 1–3 item'lık transaction mümkündür, kural uygulamadadır").
- Kart 3 Aurora R2 kuyruk: düzeltildi; row başına 15/s'nin tek başına sorun olmadığı, riskin uzun transaction olduğu ve bunun tahmin olduğu yazıldı.
- Kart 3 asimetrik puanlama: düzeltildi; DynamoDB'nin temizlik/Streams noktası R1'den çıkarıldı, R4'te kaldı (Aurora'nın temizlik işi de R4'te).
- Kart 4 DynamoDB silme: düzeltildi (aynı partition'da TransactWriteItems ile silme mümkün; fark diğer table'lardaki bağlı kayıtlar).
- Kart 5 policy testi asimetrisi: düzeltildi (RDS R4 gerekçesine de eklendi). Veri boyutu: hikâyeye 200 GB eklendi.
- M7 sinema checkpoint'i: düzeltildi; DynamoDB seçeneği ve açıklama kartlarla tutarlı hale getirildi.
- Simülasyon başlıklarının kazananı söylemesi: gerekçe ile kapatıldı. Başlık biçimi kabul edilmiş DynamoDB referans sayfasıyla aynıdır; M7 girişine "tahmin edilecek şey hangi gereksinimin kararı verdiğidir" cümlesi eklendi. Simülasyonun kartla aynı veriyi kullanması bir tasarım kuralıdır (kart ve simülasyon farklı şey söyleyemez).
- R5'te fiyat olmaması: bkz. bölüm 3 (formül eklendi, fiyat bilerek yok).

### 5. "Ilişkisel" büyük I
- Gerekçe ile açık bırakıldı: büyük harf ortak `usecase` makrosundaki `capitalize` filtresinden gelir (DynamoDB sayfasında da aynı). Makro paylaşılan bir parçadır ve bu sayfada değiştirilmez; Türkçe'ye duyarlı bir büyük harf filtresi çerçeve için not edildi (sahibe iletilecek tek açık nokta).

### 6. Görseller
- A3 ER diyagramı caption'ı: düzeltildi; resimdeki table adları, PK/FK ve okun yönü yazıldı, Lale Market eşlemesi ayrı cümle.
- A8 ve C2 cluster caption'ları: düzeltildi; C2 caption'ı iki yeni ayrıntıya (reader'a giden ok, S3 kutusu) bakmayı söylüyor.
- Simülasyon renk açıklaması: M7 girişine puan simülasyonlarında renklerin anlamı yazıldı; açıklama kutusu bütün simülasyonlarda ortak olduğu için değiştirilmedi.

### Sonuç bölümündeki dört eksik
1. Sınırın sayısı: A8'de "AWS sayı vermez, ölç" cevabı. 2. DynamoDB sözlüğü: M2 başındaki sözlük paragrafı. 3. Ekip bilgisi: kartlarda açıkça yazıldı. 4. Maliyet: formül ve fiyat sayfası linki.
