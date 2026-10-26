# Lale Market Keşif Rehberi

> **Veritabanı konusunda altyapınız yoksa** önce [Veritabanı 101](VERITABANI-101.md) yazısını okuyun. Bu rehberde geçen her terim orada günlük hayattan örneklerle anlatılıyor.

Bu rehber sizi Lale Market sitesinde adım adım gezdirir. Her durakta üç şey var:

- **Yap:** nereye gidip neye tıklayacağınız
- **Bak:** ekranda ve sağdaki panelde neye dikkat edeceğiniz
- **Ne anlama geliyor:** gördüğünüzün arkasındaki veritabanı fikri

Rehberi baştan sona yaklaşık 60-75 dakikada bitirirsiniz. Durakları sırayla yapmanızı öneririm, çünkü sonraki duraklar öncekilerde oluşturduğunuz veriyi (sepet, sipariş, gezinme geçmişi) kullanır.

**Adres:** https://dbworkshop.tdsynnexlab.link/

---

## Durak 0 - Hazırlık: ekranı tanıyın (5 dk)

**Yap**
1. Siteyi açın. Açılan pencerede **Ayşe Yılmaz**'ı seçin. Siteyi onun gözünden gezeceksiniz.
2. Ekranı inceleyin. Dört bölge var:

| Bölge | Ne işe yarar |
|---|---|
| Üst lacivert bar | Arama kutusu, seçili persona, sepet sayısı, **Tutorial** düğmesi |
| Beyaz Tutorial kutusu | "Step 1 of 5" diye o sayfada ne yapacağınızı anlatır. **Next** ile ilerler, **Close** ile kapanır |
| Ortadaki mağaza | Gerçek bir e-ticaret sitesi gibi kullanılır |
| Sağdaki koyu panel: **Behind the scenes** | Bu sayfanın veritabanlarına yaptığı **her** çağrı |

**Bak: paneli okumayı öğrenin.** Paneldeki her kart bir çağrıdır. En yeni çağrı en üsttedir.

| Kart alanı | Anlamı |
|---|---|
| Başlık, örneğin **"2. Load the home page"** ve sağında `81 ms` | Tarayıcının yaptığı istek ve toplam süresi |
| Gri satır, örneğin `GET /docdb/api/home → DocumentDB Engine App` | İsteğin hangi uygulamaya gittiği |
| Koyu kutudaki kod | Veritabanına giden **gerçek** sorgu ya da komut |
| **Parameters** | Sorguya verilen değerler |
| **Result** | Kaç kayıt döndüğü |
| **Explain** | Veritabanının sorguyu nasıl çalıştırdığı (yalnızca bazı engine'lerde) |
| **Capacity / Cost** | Harcanan kapasite birimi ve yaklaşık maliyeti (DynamoDB, Keyspaces) |
| **Network** | Paketin yolu: hangi EC2'den çıkıp hangi endpoint üzerinden nereye gittiği |
| **Auth** | Kimlik doğrulama: **IAM role (SigV4)** ya da **Password (Secrets Manager)** |
| Sarı yazı | Bu çağrıdan çıkarılacak ders |

**Deneyin:** Fareyi paneldeki bir kartın üzerine getirin. Mağazada o çağrıyı yapan bölüm turkuaz bir çerçeveyle vurgulanır.

**Ne anlama geliyor:** Bu site **on farklı veritabanı** kullanır ve her parçası işine en uygun olanı seçer. Paneldeki soluk kartlar "arka plan" çağrılarıdır. Örneğin her sayfada ElastiCache'e giden **Update the session** çağrısı oturumunuzu günceller.

---

## Durak 1 - Ana sayfa: doküman veritabanı ve önbellek (5 dk)

**Yap:** Ana sayfada kalın. Tutorial'ı **Next** ile sonuna kadar okuyun.

**Bak**
- Panelde **Load the home page** kartında iki çağrı var:
  - `aggregate`: kategorileri sayar.
  - `find ... .limit(8)`: en yüksek puanlı 8 ürünü getirir.
- **Flash deal** kartı ElastiCache'e iki komut gönderir: `HGETALL lm:deal` ve `GET lm:deal:stock`. Sürelerine bakın: genellikle 2 ms civarı.
- **Recently viewed** kartı Keyspaces'e gider. İlk ziyarette `0 item(s)` döner, çünkü henüz hiç ürün gezmediniz.

**Ne anlama geliyor**
- **DocumentDB** her ürünü tek bir JSON doküman olarak saklar. Kategori menüsünü uygulama değil, veritabanı hesaplar (`$group`).
- **ElastiCache** veriyi bellekte tutar. Bu yüzden milisaniyenin altında, en çok birkaç milisaniyede cevap verir. Flaş indirim gibi sık okunan ve hızlı değişen veri için idealdir.
- **Bir sayfa birden çok veritabanından beslenir.** Gerçek büyük e-ticaret siteleri de böyle çalışır.

---

## Durak 2 - Kategori: indeksin değeri (5 dk)

**Yap:** Ana sayfada **Elektronik** kategorisine tıklayın.

**Bak**
1. Panelde **find + explain** kartındaki **Explain** satırını okuyun: `docs examined: 40, returned: 40`.
2. **Experiment** kutusunda **Collection scan** seçin. **Explain** satırı şimdi `docs examined: 200` gösterir.
3. Kartın altındaki plan metninde `IXSCAN` (indeksle arama) yerine `COLLSCAN` (koleksiyonun tamamını tarama) görünür.
4. **Colour** listesinden `siyah` seçin. Sorgudaki filtre `"attributes.renk": "siyah"` olur. Bu, dokümanın **içindeki** bir alandır.

**Ne anlama geliyor**
- **İndeks**, veritabanının yalnızca gereken kayıtlara gitmesini sağlar. 200 ürünle fark küçüktür; 20 milyon üründe sorgu milisaniyeler yerine dakikalar sürer.
- Doküman veritabanları **iç içe alanları** da indeksleyebilir ve sorgulayabilir. İlişkisel bir veritabanında bunun için ayrı bir tablo ve JOIN gerekirdi.

---

## Durak 3 - Arama: yazım hatası ve Türkçe karakter (7 dk)

**Yap:** Üst menüden **Search**'e gidin.

**Bak**
1. **kulaklk (typo)** örneğine tıklayın. Kelime yanlış yazıldığı halde kulaklıklar bulunur. Panelde `"fuzziness": "AUTO"` satırına bakın.
2. **Typo tolerance** bölümünde **Exact words** seçin. Aynı arama artık **0 sonuç** verir.
3. **Fuzziness AUTO**'ya dönün. "kablosuz kulaklik" arayın (ı yerine i). Sonuçları sayın.
4. **Analyzer** bölümünde **standard** seçin ve aynı aramayı yapın. Daha az sonuç gelir.
5. Soldaki **Category** listesinde bir kategoriye tıklayın. Sonuçlar filtrelenir. Panelde `aggs` (aggregation) bölümünü bulun.
6. Üstteki arama kutusuna yavaşça `kabl` yazın. Bir öneri listesi açılır. Panelde **Search suggestions** kartı görünür (`match_phrase_prefix`).

**Ne anlama geliyor**
- **OpenSearch** bir veritabanı değil, bir **arama indeksidir**. Asıl katalog DocumentDB'dedir; OpenSearch metnin aranabilir bir kopyasını tutar.
- **Fuzziness**, kullanıcının bir-iki harf hatasını tolere eder.
- **Analyzer**, metnin nasıl parçalanıp normalleştirileceğini belirler. `tr_folded` analyzer'ı "ı"yı "i"ye, "ş"yi "s"ye çevirir. Türkçe kullanıcıların klavyesinde bu çok önemlidir.
- **Facet** sayıları ("Elektronik (5)") aynı sorguda ek bir sorgu yapmadan hesaplanır.

---

## Durak 4 - Ürün sayfası: dört veritabanı tek sayfada (8 dk)

**Yap:** Arama sonuçlarından **Kablosuz Kulaklık 1**'e (P0001) tıklayın.

**Bak**
1. Panelde dört farklı engine'e giden kartları ayırt edin:
   - **Read the product** → DocumentDB
   - **Record a view event** → Keyspaces
   - **Recommendations** → Neptune
   - **Recently viewed** → Keyspaces
2. **Product read** bölümünde **Card fields only** seçin. Ürün açıklaması kaybolur. Paneldeki sarı notta doküman boyutunun küçüldüğünü görün.
3. **Recommendations** bölümünde **For my persona** seçin. Öneri listesi değişir. Paneldeki openCypher sorgusunun uzadığına bakın (2 adım yerine 3 adım).
4. **Quantity** alanına `5` yazıp **Add to cart** düğmesine basın. Sonra `1` yazıp tekrar basın. İkincisi kırmızı uyarıyla reddedilir: **"You can add at most 5 pieces of one product."**
5. Panelde iki **UpdateItem** kartını karşılaştırın. İkincisinde `ConditionExpression` vardır ve sarı not neden reddedildiğini açıklar.

**Ne anlama geliyor**
- **DocumentDB:** Ürünün bütün bilgisi tek okumada gelir. **Projection** ile yalnızca gereken alanları çekmek ağ trafiğini azaltır.
- **Neptune (graf):** "Bu ürünü alanlar başka ne aldı?" bir **ilişki gezinmesidir**. Ürün → onu alan müşteriler → onların aldığı diğer ürünler. İlişkisel modelde her adım büyük bir JOIN olurdu.
- **Keyspaces:** Sayfayı açtığınız an bir "view" olayı yazıldı. Hemen altındaki "Recently viewed" şeridi aynı olayı okur.
- **DynamoDB koşullu yazma:** "En fazla 5 adet" kontrolü ve yazma **tek ve bölünmez (atomik) bir adımdır**. İki sekmeden aynı anda eklense bile kural bozulmaz.

---

## Durak 5 - Sepet: tutarlılık, TTL ve ölçek (7 dk)

**Yap:** Üst bardaki **Cart**'a tıklayın.

**Bak**
1. Panelde **Read the cart** kartında **Capacity: 1.0 RRU** ve yanında maliyeti görün.
2. **Read consistency** bölümünde **Eventually consistent** seçin. Kapasite **0.5 RRU** olur.
3. Tablodaki **Expires** sütununa bakın. Her kalem 24 saat sonra silinecek.
4. **Load Simulation** bölümünde **1000** seçip **Start the simulation** düğmesine basın. Sonuçta saniyedeki yazma sayısı ve gecikme yüzdelikleri (p50, p95, p99) görünür.

**Ne anlama geliyor**
- **Strongly consistent** okuma son yazdığınızı kesin görür. **Eventually consistent** okuma yarı fiyattır ama son bir saniyedeki bir yazmayı kaçırabilir. Sepet için güçlü tutarlılık, ürün listesi için zayıf tutarlılık mantıklıdır.
- **TTL (Time to Live):** DynamoDB süresi dolan kalemleri **kendisi ve ücretsiz** siler. Terk edilmiş sepetler için temizlik işi yazmanız gerekmez.
- **On-demand kapasite:** Kapasite planlamadan ani 1.000-2.000 yazmalık patlamayı karşılar.
- Maliyete bakın: 1.000 yazma bir sentin çok küçük bir kesridir. Simülasyon tavanı (2.000 istek, saatte 3 kez) maliyeti korur.

---

## Durak 6 - Ödeme: ACID transaction ve geri alma (8 dk)

**Yap:** Sepette ürün varken **Go to checkout** düğmesine basın.

**Bak**
1. Sağdaki **What happens** listesi altı adımı gösterir. **Place the order** düğmesine basın ve adımların yeşile döndüğünü izleyin.
2. Panelde **Place the order (Aurora transaction)** kartını açın. Sırayla şu satırları görürsünüz: `BEGIN` → `UPDATE (stock)` → `INSERT (order)` → `INSERT (order item)` → `COMMIT`.
3. Sonraki kartlar diğer beş engine'e gider: sepeti boşaltma, liderlik tablosu, satın alma olayı, sipariş metriği, graf kenarı.
4. **Hata deneyi:** Bir ürünü tekrar sepete ekleyin ve ödemeye dönün. **Make the payment fail after the stock update** kutusunu işaretleyip siparişi verin.
   - Panelde `BEGIN` → `UPDATE (stock)` → **`ROLLBACK`** görünür.
   - Ekranda kırmızı bir mesaj çıkar: sipariş oluşmadı, stok geri geldi, sepet aynı kaldı.

**Ne anlama geliyor**
- **ACID transaction:** Stok düşürme, sipariş yazma ve kalem yazma **ya hep birlikte olur ya hiç olmaz**. Ödeme yarıda kalırsa veritabanı her şeyi geri alır. Para ve stokla ilgili işler için ilişkisel veritabanı (Aurora) bu yüzden seçilir.
- `UPDATE ... WHERE stock >= qty` koşulu ve satır kilidi, iki kişinin son ürünü aynı anda almasını engeller.
- Altı adımı burada tarayıcı sırayla çağırır, böylece her birini görebilirsiniz. Gerçek sistemlerde bu güncellemeler bir olay kuyruğuyla (SQS, EventBridge) yapılır. Notu okuyun.

---

## Durak 7 - Siparişlerim ve sipariş raporu (5 dk)

**Yap:** Üst menüden **My orders**'a, sonra **Reports → Order report**'a gidin.

**Bak**
- **My orders:** Panelde üç tabloyu birleştiren tek bir `SELECT ... JOIN ... JOIN` sorgusu var.
- **Order report:** "Revenue by segment" grafiği. **Show the query plan (EXPLAIN ANALYZE)** kutusunu işaretleyin. Altta PostgreSQL'in sorguyu hangi adımlarla çalıştırdığı ve her adımın süresi çıkar.

**Ne anlama geliyor**
- İlişkisel veritabanı veriyi tekrarsız, ayrı tablolarda tutar ve **JOIN** ile birleştirir. **Foreign key**'ler olmayan bir ürüne sipariş yazılmasını engeller.
- **EXPLAIN ANALYZE**, yavaş bir sorgunun nedenini bulmanın ilk aracıdır.
- Aurora güncel ve operasyonel raporlar için iyidir. Yıllarca veriyi tarayan raporlar ise ödeme trafiğini yavaşlatır. Bir sonraki durak bu yüzden Redshift.

---

## Durak 8 - Satış raporları: sütun bazlı depo ve zero-ETL (8 dk)

**Yap:** **Reports → Sales reports**.

**Bak**
1. Grafik ayları gösterir. **Group by** bölümünde **Category**, sonra **City** seçin. Her seferinde panelde sorgunun yalnızca birkaç sütun kullandığına dikkat edin.
2. **Data** bölümünde **Live from Aurora (zero-ETL)** seçin. Grafik kırmızıya döner ve Aurora'daki canlı veriyi gösterir.
3. Sağdaki **Zero-ETL replication** kutusunu okuyun: integration durumu (`CdcRefreshState`), kopyalanan tablo sayısı, **Newest workshop order**.
4. Yeni bir sekmede bir sipariş verin. Bu sayfaya dönüp **Refresh the status** düğmesine basın. **Newest workshop order** satırı siparişinizi yaklaşık 15-20 saniye içinde gösterir.

**Ne anlama geliyor**
- **Redshift** her sütunu ayrı saklar. "Kategoriye göre toplam gelir" sorgusu yalnızca kategori ve tutar sütunlarını okur, diğer sütunlar diskte kalır. Analitik için bu çok hızlıdır.
- **Zero-ETL:** Aurora'daki her değişiklik **kod yazmadan** Redshift'e kopyalanır. Klasik yöntemde bunun için bir veri boru hattı (ETL işi) yazıp işletmeniz gerekirdi.
- **İş yükü ayrımı:** Ödeme Aurora'da hızlı kalır, ağır raporlar Redshift'te çalışır.

---

## Durak 9 - Flaş indirim: atomik sayaç ve yarış durumu (8 dk)

**Yap:** Üst menüden **Flash deal**'e gidin.

**Bak**
1. **Buy one now** düğmesine basın. Panelde tek bir komut görünür: `DECR lm:deal:stock`. Stok bir azalır.
2. **Load Simulation: 300 buyers, 10 pieces** bölümünde **Atomic DECR** seçiliyken **Start the rush** düğmesine basın.
   Sonuç: 300 alıcıdan **tam 10'u** ürün alır, **pieces oversold = 0** (yeşil).
3. **Read, then write** seçip tekrar basın. Bu kez **pieces oversold** kırmızı ve büyük bir sayı olur. Mağaza elinde olmayan yüzlerce ürünü satmıştır.
4. **Your session** bölümünde TTL'i **30 seconds** yapın, **Refresh the session**'a basın. Ardından birkaç kez **Read the session**'a basın. `ttl` değeri geri sayar.

**Ne anlama geliyor**
- **Yarış durumu (race condition):** "Önce oku, sonra yaz" yönteminde iki alıcı aynı stok değerini okur ve ikisi de satın aldığını sanır. Yüksek trafikte bu, gerçek para kaybıdır.
- **Atomik komut:** `DECR` okuma ve yazmayı tek adımda yapar. Valkey komutları sırayla işlediği için iki alıcı asla aynı parçayı alamaz.
- **TTL:** Oturum hareketsiz kalınca kendiliğinden silinir; temizlik işi gerekmez.

---

## Durak 10 - Canlı liderlik tablosu (4 dk)

**Yap:** **Reports → Live leaderboard**. Sayfayı açık bırakın.

**Bak**
1. Üstte iki sayaç var: bu workshop'taki sipariş sayısı ve son 5 dakikada aktif ziyaretçiler.
2. Tablo, ciroya göre ilk 10 müşteriyi gösterir.
3. Başka bir sekmede Ayşe ile bir sipariş verin. Bu sekmeye dönün: 5 saniye içinde sipariş sayacı artar ve Ayşe'nin cirosu güncellenir.

**Ne anlama geliyor**
- **Sorted set (ZSET):** Valkey üyeleri her yazmada puana göre sıralı tutar. "İlk 10" sorusu her an hazırdır ve hesaplama gerektirmez.
- **INCR** ile atomik sayaç: binlerce kişi aynı anda sipariş verse de sayı doğru kalır.

---

## Durak 11 - Aktivite geçmişi: geniş sütunlu veritabanı (5 dk)

**Yap:** Üst menüden **My activity**'e gidin.

**Bak**
1. Bu tarayıcıda gezdiğiniz ürünler en yeniden en eskiye sıralı görünür. Satın alma olayınız da listededir.
2. **My persona (seeded)** seçin. Ayşe'nin önceden yüklenmiş geçmişi görünür.
3. **LOCAL_ONE** seçin. Paneldeki sarı not okuma maliyetinin yarıya indiğini açıklar.
4. **Start the burst** düğmesine basın. **writes retried** değerine bakın.

**Ne anlama geliyor**
- **Keyspaces (Cassandra uyumlu)** veriyi **partition key**'e göre gruplar; burada partition key tarayıcı kimliğinizdir. Bir partition'ın içindeki satırlar diskte zaten zamana göre sıralıdır, bu yüzden `ORDER BY` gerekmez.
- Çok yüksek hacimli olaylar için uygundur: tıklamalar, IoT verisi, loglar. Sorguda her zaman partition key bulunmalıdır; serbest filtre ve JOIN yoktur.
- **Tutarlılık seviyesi** kapasite maliyetini doğrudan etkiler.
- **Yeniden deneme:** Yeni bir on-demand tablo kapasitesini adım adım artırır. İyi bir istemci kısıtlanan istekleri bekleyip tekrar dener.

---

## Durak 12 - Mağaza bulucu: coğrafi sorgu (3 dk)

**Yap:** Üst menüden **Stores**'a gidin.

**Bak**
1. Haritada İstanbul merkezli bir daire ve içindeki mağazalar görünür.
2. Haritada başka bir yere tıklayın. Liste ve daire değişir.
3. **Radius** bölümünde 10, 25 ve 100 km arasında geçiş yapın. **Frankfurt** düğmesini deneyin.

**Ne anlama geliyor**
- OpenSearch'ün **geo_point** alanı "bu noktaya 25 km içindekiler, yakından uzağa" sorusunu tek sorguda yanıtlar (`geo_distance`).
- İnfografik bu iş için Keyspaces'i önerir, ama Keyspaces'te coğrafi sorgu yoktur. Bu yüzden workshop OpenSearch'ü kullanır.

---

## Durak 13 - Satıcı paneli: nesne deposu (5 dk)

**Yap:** Üst menüden **Seller panel**'e gidin.

**Bak**
1. **Objects** tablosunda `products/` önekindeki fotoğrafları ve **Metadata** sütununu görün: `author`, `license`, `source`. Bunlar dosyanın yanında saklanan bilgilerdir.
2. Bilgisayarınızdan küçük bir görsel seçip **Upload**'a basın. Panelde `PutObject` ve yeni bir **version id** görünür. Tablo `uploads/` önekine geçer.
3. Aynı dosyayı tekrar yükleyin. Yeni bir version id oluşur; eski sürüm silinmez.
4. **Through the Engine App** ve **Presigned URL, straight from S3** düğmelerini karşılaştırın. İkincisinde URL'nin adresi doğrudan S3'tür.

**Ne anlama geliyor**
- **S3** dosyaları veritabanında değil, **nesne deposunda** tutar. Her nesnenin bir anahtarı ve metadata'sı vardır. "Klasör" diye gördüğünüz şey yalnızca anahtarın ön ekidir.
- **Versioning:** Yanlışlıkla üzerine yazılan dosya geri getirilebilir.
- **Presigned URL:** Bucket private kalır. Uygulama yalnızca süreli bir imza üretir ve büyük dosyayı tarayıcı doğrudan S3'ten indirir. Böylece uygulama sunucusu dosya trafiğini taşımaz.

---

## Durak 14 - Operasyon ekranı: zaman serisi (4 dk)

**Yap:** **Reports → Operations**.

**Bak**
1. Üç grafik var: dakikalık siparişler, depo sıcaklığı ve depo nemi.
2. **Window** bölümünde **1 minute** seçin. Grafik çok noktalı ve dalgalı olur.
3. **1 hour** seçin. Grafik yumuşar. Paneldeki **Result** sayısının düştüğüne bakın.
4. Bir sipariş verin ve sipariş grafiğinin son dakikasına bakın.

**Ne anlama geliyor**
- **Zaman serisi veritabanı (InfluxDB)** zaman damgalı ölçümleri sıralı saklar.
- `aggregateWindow` ham noktaları "her X dakikanın ortalaması" gibi pencerelere indirir. SQL'de bunun için tarih gruplaması ve GROUP BY gerekirdi.
- İzleme panoları, IoT ve metrikler için tipik bir seçimdir.

---

## Durak 15 - Müşteri grafı ve soğuk başlangıç (4 dk)

**Yap:** **Reports → Customer graph**.

**Bak**
1. Kırmızı nokta Ayşe'dir. Lacivert kutular onun aldığı ürünlerdir. Turkuaz noktalar aynı ürünleri alan diğer müşterilerdir.
2. **Customer** listesinden **Lukas Weber**'i seçin. Neredeyse yalnızca kitap aldığı için grafı dardır.
3. **Elif Kaya**'yı seçin. Hiç siparişi olmadığı için grafı boştur.

**Ne anlama geliyor**
- Graf veritabanında ilişkiler (**BOUGHT** kenarları) birinci sınıf veridir.
- **Soğuk başlangıç (cold start):** Geçmişi olmayan bir kullanıcıya kişisel öneri yapılamaz. Bunu sitede de görün: personayı **Elif Kaya** yapın, bir ürün sayfasında **For my persona** seçin. Liste boş gelir, ama **Bought with this product** çalışmaya devam eder.

---

## Durak 16 - Persona değiştirince ne değişir? (3 dk)

**Yap:** Üst bardaki persona düğmesine tıklayıp **Mert Doğan**'ı (kurumsal, toplu alım) seçin.

**Bak**
- Ürün sayfasında **For my persona** önerileri değişir.
- **My activity** sayfasında **My persona** seçeneği Mert'in geçmişini gösterir.
- Sepet ve siparişler değişmez. Bunlar persona'ya değil, bu **tarayıcıya** aittir.

**Ne anlama geliyor:** Paylaşılan katalog (ürünler, müşteriler, geçmiş siparişler) herkes için aynıdır. Sizin oluşturduğunuz veri (sepet, sipariş, gezinme) yalnızca size aittir. Birden çok kişinin aynı sistemi kullandığı her uygulamada bu ayrım temel bir tasarım kararıdır.

---

## Durak 17 - Rehberli yolculuk (isteğe bağlı, 10 dk)

Ana sayfadaki **Start the guided journey** düğmesi yedi durağı sırayla gezdirir. Üstte bir ilerleme şeridi ve **Next stop** linki çıkar.
Workshop katılımcılarına göstermek veya kısa bir tekrar yapmak için kullanışlıdır.

---

## Özet: hangi iş için hangi veritabanı?

| İş | Engine | Neden | Hangi durakta gördünüz |
|---|---|---|---|
| Ürün kataloğu | DocumentDB | Esnek şema, iç içe alanlar, tek okumada tüm ürün | 1, 2, 4 |
| Arama | OpenSearch | Yazım hatası toleransı, alaka sıralaması, facet | 3 |
| Mağaza bulma | OpenSearch (geo_point) | Mesafe sorgusu | 12 |
| Öneri | Neptune | İlişki gezinmesi | 4, 15 |
| Sepet | DynamoDB | Anahtarla milisaniye erişim, TTL, sınırsız ölçek | 4, 5 |
| Ödeme, sipariş | Aurora PostgreSQL | ACID transaction, JOIN, foreign key | 6, 7 |
| Flaş indirim, oturum, liderlik | ElastiCache (Valkey) | Bellekte, atomik komutlar, TTL | 1, 9, 10 |
| Gezinme geçmişi | Keyspaces | Yüksek yazma hacmi, partition başına sıralı veri | 4, 11 |
| Ürün görselleri, dosyalar | S3 | Nesne deposu, versioning, presigned URL | 13 |
| Satış analitiği | Redshift | Sütun bazlı tarama, zero-ETL ile canlı veri | 8 |
| Metrikler, sensörler | InfluxDB | Zaman serisi, pencere hesapları | 14 |

## Kendinizi sınayın

Rehberi bitirince bu sorulara cevap verebiliyor olmalısınız:

1. Bir sorgunun indeks kullanıp kullanmadığını DocumentDB'de nereden anlarsınız?
2. Sepet okumasında eventually consistent seçmenin faydası ve riski nedir?
3. Ödeme yarıda kalınca Aurora stoku neden geri getirir?
4. Flaş indirimde "önce oku, sonra yaz" yöntemi neden fazla satış yapar?
5. Raporları neden Aurora yerine Redshift'te çalıştırırız? Zero-ETL bu işe ne katar?
6. Keyspaces'te bir sorguda neden her zaman partition key bulunmalıdır?
7. Presigned URL, bucket'ı public yapmadan dosya indirmeyi nasıl sağlar?
8. Elif Kaya'ya kişisel öneri neden çıkmaz?

Takıldığınız yerde ilgili durağa dönün ve paneldeki sarı notları okuyun. Her notta o çağrının dersi yazar.
