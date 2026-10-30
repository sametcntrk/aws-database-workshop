# Reader simulation: Aurora PostgreSQL (aurora), Türkçe sayfa, model 2

Tarih: 2026-10-30

Okuyucu: relational database ya da Amazon Aurora kullanmamış biri. Kaynak: `/tmp/preview_aurora/aurora.tr.txt` (baştan sona okundu) ve `/tmp/preview_aurora/aurora.tr.rendered.html` (görseller ve simülasyon JSON'u).

## Genel izlenim

Bölüm A çok iyi: her kavramın "bütün durumlar" tablosu, checkpoint'ler ve "Aklına şu gelebilir" kutuları soruları cevaplanmadan bırakmıyor. B ve C'deki canlı çıktılar (EXPLAIN, constraint hataları, RETURNING) A'daki fikirleri somutlaştırıyor. M2'de on kartın hepsinde aritmetiği tek tek kontrol ettim: her satırın katkısı, R1 alt toplamları, 100 üzerinden toplamlar ve özet tablodaki farklar doğru. Beş M7 simülasyonunun (sim-w_checkout, sim-w_catalog, sim-w_ledger, sim-w_tenant, sim-w_reporting) son adımındaki puan tablosu, toplamlar, sıralama ve karar metni kartlarla birebir aynı. sim-w_ledger'ı adım adım kart 7 ile karşılaştırdım; her hücre ve gerekçe aynı. Head-to-head paragraflarının hepsi farkın nerede olduğunu, rakibin gerçek gücünü ve somut bir "hangi koşul değişseydi" cümlesini veriyor.

Sorunlar çoğunlukla model 2'nin kendi kurallarında: aynı eksiğin birkaç satırda sayılması, servis paketlemesinin R1'e girmesi ve aynı engine'li en yakın rakibin (RDS for PostgreSQL) küçük ve düz iş yüklerinde aday olarak hiç gösterilmemesi.

## Bulgular

### R1 (yüksek): Küçük ve düz iş yüklerinde RDS for PostgreSQL aday değil; "en uygun servis" iddiası kontrol edilmemiş
Bölüm: kart 1, kart 4, kart 9 (M5 ve kart 5 ile karşılaştır).
Alıntı: kart 1 "Veri yılda iki katına çıkıyor ama birkaç GB'ı geçmiyor"; kart 9 R5 "Trafik düşük ve düz; kapasite başına en küçük ödeme istenir"; M5 RDS "iş yükü küçük ya da düzse; en düşük fatura dayanıklılık farkından önemliyse".
Sorun: Kart 5'in kendi mantığına göre (düz trafik, fiyat hassas) RDS kazanır. Kart 1, 4 ve 9 da küçük ve düz iş yükleri; ama ikinci ve üçüncü aday DocumentDB ve DynamoDB. R1'i Aurora ile aynı olan RDS gösterilmiyor. Okuyucu olarak kendi tahminim: kart 1'de RDS yaklaşık 94,5 alır (R1 49,2, R2 12, R3 19,8, R4 7,2, R5 6,3), yani fark 2,4 ve kart "yakın yarış" olur. Kart 9'da da yaklaşık 93,5 alır. Bu kartlarda gerçek ikinci aday görünmüyor.
Mimara soru: Kart 1, 4 ve 9'da RDS for PostgreSQL neden aday değil? Aday olsaydı hangi satır onu Aurora'nın arkasında tutardı?

### R2 (yüksek): Kart 7'de RDS'in aynı eksiği üç satırda sayılıyor
Bölüm: kart 7, RDS for PostgreSQL gerekçesi.
Alıntı: R2 "yazma kapasitesi instance sınıfıyla sabittir"; R4 "ay sonu kapasitesi ve büyüme bir kapasite planıdır"; R5 "ay sonuna göre boyutlanan instance ayın 28 gününde boş durur ve ödenir".
Sorun: Üçü de aynı mekanizma: sabit instance boyutu ile ay sonu tepesi. Sayfanın kuralı şu: "Bir eksik yalnız bir satırda sayılır". R2 ve R4'teki kırılmalar kaldırılırsa RDS yaklaşık 90,6 alır ve Aurora ile fark 1,6 olur. Yani kart "yakın yarış" olmalı ve M7'deki "ay sonu dalgalanması kararı Aurora'ya verir" mesajı zayıflar.
Mimara soru: Bu eksik hangi tek satırda sayılmalı: R2'de (kapasite) mi, R5'te (boşa ödeme) mi?

### R3 (yüksek): Kart 6'da R1'e servis entegrasyonu girmiş (zero-ETL, OpenSearch Ingestion)
Bölüm: kart 6, R1.4 OY satırı.
Alıntı: Redshift R1.4 "Zero-ETL kopyası checkout'un yazmalarını saniyeler içinde getirir"; OpenSearch R1.4 "OpenSearch Ingestion Aurora PostgreSQL'in değişikliklerini akıtabilir"; Aurora R1.4 "Veri zaten burada, checkout'un kendisinde; kopya yoktur".
Sorun: Mimar gözüyle bölümünün kuralı açık: "bir kırılım servisin paketlemesinden geliyorsa (… zero-ETL bağlantısı) R2–R5'e yazılır ve R1'de sayılmaz". Satırın "Ne istiyoruz" cümlesi de ("Checkout'un yazmaları saniyeler içinde rapor tarafına gelmeli") bir boru hattı gereksinimi; engine'in yazma biçimi değil. Pipeline ayrıca R4'te de puanlanıyor ("Zero-ETL kod yazmadan kurulur").
Mimara soru: Bu satırda engine'in kendisi neyi puanlıyor? Columnar storage'a sürekli küçük ekleme yapmak mı? Öyleyse gerekçe zero-ETL'den bahsetmemeli.

### R4 (yüksek): "Bu sayfa fiyat yazmaz" diyor, ama iki yerde fiyat yazıyor
Bölüm: B6, kart 5, M5.
Alıntı: B6 "bu sayfa fiyat yazmaz, çünkü fiyat değişir ve formül değişmez"; kart 5 R5 "db.r6g.large saatte 0,274 USD … 0,313 USD … I/O-Optimized'da ise instance saatte 0,407 USD"; M5 "(on demand, AWS Price List API, 2026-10-29)".
Sorun: Okuyucu hangisine inanacağını bilemiyor. Kart 5'in bütün kararı bu fiyatlara dayanıyor.
Beklenen: Ya B6'daki cümle "kartlar bir tarihteki fiyatı kaynağıyla verir" diye değişsin, ya da kart 5 yüzde fark verip fiyat sayfasına göndersin.

### R5 (yüksek): Kart 9'da R4'ün ağırlığı ve puanı R1'in kuralını tekrar sayıyor
Bölüm: kart 9.
Alıntı: Ağırlıklar "R4 18 ile en ağır ikinci satır: kural tek bir yerde tanımlanmalı ve depo, kargo ve destek programlarının hepsine aynı uygulanmalı"; Aurora R4 "Kural database'de olduğu için her program aynı kuralla çalışır"; DynamoDB R4 "kuralın her programda olması R1'de sayıldı".
Sorun: "Kural tek yerde, her programa" R1.2 ŞE'nin ve R1.1 TA'nın konusu. Burada R4'ün ağırlığını (18) belirliyor ve Aurora'nın R4 puanını açıklıyor. DynamoDB'nin gerekçesi bunun R1'de sayıldığını kabul ediyor; Aurora'nınki kabul etmiyor. Ağırlık operasyon ve ekipten gelmiyor.
Mimara soru: Kural R1'deyse R4 neden 18? Üç geliştirici ve düşük hacim için R4 kaç olmalı?

### R6 (orta): Kart 3'te DynamoDB'nin maliyeti R1'de ve R5'te iki kez sayılıyor
Bölüm: kart 3, DynamoDB R1.2 ve R5.
Alıntı: R1.2 "1 puan kırıldı: transaction'lı yazma iki birim tüketir"; R5 "transaction'lı yazmalar ve zamanlanmış iade işi birim tüketir".
Sorun: Birim tüketimi bir fiyat konusu (R5). R1'de olmamalı, iki kez de sayılmamalı. Kart 1, 4, 7 ve 8'de aynı mekanizma doğru olarak yalnız R5'te sayılıyor.

### R7 (orta): Kart 2'de aynı mekanizma (esnek alanların type'ı denetlenmiyor) bir adayda düşürülüyor, ötekinde düşürülmüyor
Bölüm: kart 2, R1.1 VM ve R1.2 ŞE.
Alıntı: Aurora R1.1 "3 puan kırıldı: … JSONB içindeki alanların type'ını database denetlemez"; DocumentDB R1.1 "Puan kırılmadı" ve R1.2 "Puan kırılmadı".
Sorun: DocumentDB'de de iç içe alanların type'ı ancak $jsonSchema yazılırsa denetlenir. Kural yazmak bir ek iş; JSONB'de de aynı iş CHECK ya da trigger ile yapılabilir. Bir de bu konu ŞE'ye ait ama VM satırında sayılıyor. R1 farkı 1 puan ve kartın ana mesajı ("engine uyumunu DocumentDB 1 puanla kazanır") bu satıra bağlı.
Mimara soru: Type denetimi iki adayda da aynı satırda ve aynı biçimde puanlansa R1'i hangisi kazanırdı?

### R8 (orta): "Aurora zaten çalışıyor" gerekçesi döngüsel; sıfırdan başlayan bir proje için cevap yok
Bölüm: kart 1 R4, kart 2 R4/R5 ve karar.
Alıntı: kart 1 "Lale Market'te Aurora zaten çalışır"; kart 2 "toplamı Aurora R4 ve R5 ile alır, çünkü siparişler zaten Aurora'da".
Sorun: Kart 2'nin kazananı tamamen var olan cluster'a bağlı. Sıfırdan başlayan bir katalog ekibine hangi servisi önermeliyim? Sayfa bunu söylemiyor.
Mimara soru: Var olan bir cluster yoksa kart 2'yi DocumentDB mi kazanır?

### R9 (orta): Kart 10'da OpenSearch'ün "ayrı sistem" olması dört satırda sayılıyor; R4 de sonucu önceden veriyor
Bölüm: kart 10, OpenSearch gerekçesi ve R4 gereksinimi.
Alıntı: R1.4 "fiyat siparişten ayrı bir sistemde hesaplanır"; R3 "siparişler OpenSearch'te resmi kayıt olamaz; kaynak başka bir database'tedir"; R4 "ayrı bir servis, ayrı bir veri kopyası ve onu besleyen bir pipeline"; R5 "domain sipariş database'ine ek olarak gece de çalışır"; R4 gereksinimi "ayrı bir coğrafi servis işletilmek istenmiyor".
Sorun: R1.4 (transaction yok) ve R3 (resmi kayıt değil) aynı nedeni iki kez sayıyor. R4 gereksinimi de bir tercih değil, ayrı servisi baştan eleyen bir cümle.

### R10 (orta): Kart 10'da Amazon Location Service hiç anılmıyor
Bölüm: kart 10.
Alıntı: "bu rotanın uzunluğu"; ST_Length "rota uzunluğunu verir".
Sorun: Geofence ("bu adres hangi bölgede"), yol üstünde rota hesabı ve yer araması için AWS'in Amazon Location Service adlı bir servisi var. ST_Length bir çizginin geometrik uzunluğunu verir, yol üstündeki mesafeyi vermez. Location Service aday olmasa bile en azından "neden aday değil" cümlesi bekledim; ElastiCache için kart 3'te böyle bir cümle var.

### R11 (orta): ACU aralığı seçmek bazı kartlarda iki satırda, bazılarında farklı bir satırda sayılıyor
Bölüm: kart 7, kart 8 (aynı kartın içinde); kart 1–4 (kartlar arasında).
Alıntı: kart 8 R2 "minimum ACU sabahtan önce yeterli olmalıdır", R4 "ACU aralığı ve connection pool ekibin işidir"; kart 7 R2 "maksimum ACU ay sonu yüküne göre seçilmeli ve test edilmelidir", R4 "ACU aralığı ve partition bakımı ekibin işidir"; kart 2 ve 4'te R2 "reader sayısı ve ACU aralığı ekibin seçimidir"; kart 1'de R4 "ACU aralığı, connection pool".
Sorun: Kart 7 ve 8'de aynı eksik iki kez düşülüyor. Kartlar arasında da aynı mekanizma bazen R2'den, bazen R4'ten düşülüyor.

### R12 (orta): Kart 1'de DocumentDB transaction'ı iki kez cezalandırılıyor; Aurora'nın aynı yapısı cezalandırılmıyor
Bölüm: kart 1, DocumentDB R1.1 ve R1.4.
Alıntı: R1.1 "uygulama transaction'ı açar, yeniden deneme hatalarını kendisi işler"; R1.4 "koşullu düşürme ve sipariş yazması ayrı komutlardır ve transaction içinde sıralanmalıdır".
Sorun: Aurora'nın checkout'u da transaction içinde sıralanmış ayrı cümlelerdir (B5), ama R1.4'te bu yüzden puan kaybetmiyor. Transaction konusu R1.1'de zaten sayıldı.

### R13 (orta): Kart 4'te siparişlerin nerede olduğu iki adayda farklı varsayılıyor
Bölüm: kart 4, DocumentDB R1.3 ve DynamoDB R1.3.
Alıntı: DocumentDB "son siparişler başka bir collection'dadır ve $lookup ile birleştirilir"; DynamoDB "ikinci index eventually consistent'tır ve 'son siparişler' başka bir database'tedir".
Sorun: DocumentDB için siparişlerin aynı database'te olduğu varsayılıyor; DynamoDB için başka bir database'te. "Siparişler başka bir sistemde" bir R4 bilgisi; burada yalnız DynamoDB için R1.3'e konmuş.

### R14 (orta): Tek writer'ın sınırı her kartta başka bir sayıyla veriliyor
Bölüm: kart 1, 3, 4, 5, 7, 8, 10; A8.
Alıntı: kart 1 "checkout hacmi saniyede binlere çıksaydı"; kart 3 "saniyede binlere"; kart 4 "login saniyede yüz binlere"; kart 5, 7, 8, 10 "saniyede on binlere"; A8 "Tek writer'ın sınırı için AWS tek bir sayı vermez"; A8 checkpoint "saniyede 50.000 küçük yazma".
Sorun: Okuyucu Aurora'nın nerede yetersiz kaldığını bilemiyor. Kart 1'deki "binler" ile A8'deki 50.000 çelişiyor gibi görünüyor.
Mimara soru: "Saniyede binlerce küçük transaction" Aurora'nın tek writer'ı için sorun mu? Sorunsa hangi ACU'da? Bir pgbench örnek sonucu verilebilir mi?

### R15 (orta): Kart 7'deki maliyet iddiası sayısız; Aurora provisioned düşünülmemiş
Bölüm: kart 7, R5 ve head-to-head.
Alıntı: "Aurora Serverless v2 ay sonunda kapasiteyi kendiliğinden artırır ve sonra düşürür; RDS'te instance ya ay sonuna göre boyutlanır ve 28 gün boş durur".
Sorun: Normal günde saniyede 150 posting de sürekli bir yük. Serverless v2'nin ACU başına fiyatı aynı bellek için provisioned'dan yüksek. Bu ayın toplamı RDS'ten gerçekten ucuz mu? Kart 5'te fiyatlar var, kart 7'de yok. RDS için "her ay büyütüp küçültmek" (zamanlanmış instance değişikliği) ve Aurora provisioned birer seçenek; bu satırlar onları tartmıyor.
Mimara soru: 28 gün düz ve 2 gün on kat yükte iki adayın aylık hesabı nedir?

### R16 (orta): Bazı terimler açıklanmadan önce kullanılıyor
Bölüm: A2, A8, M2 kartları.
Alıntı ve yer:
- A2 "M2'deki kartlarda 'ŞE · şema yazarken uygulanır' dediğimiz şeydir": ŞE'nin ne olduğu ancak R1 kataloğunda açıklanıyor.
- A8 "sınır instance boyutuna (ACU)", "Aurora Limitless", "Aurora DSQL", "Global Database": ACU ilk kez M2'deki terim tablosunda, ötekiler M5'te tanımlanıyor.
- Kart 1 R1.4 "sık değişen stok row'larında VACUUM işi artar": VACUUM B6'da açıklanıyor (A6 yalnız "B6'daki vacuum" diyor).
- Kart 1 R4 "connection pool": B6'da açıklanıyor.
- Kart 1 R1.4 "RETURNING": B5'te açıklanıyor.
- Kart 7 "DEFERRABLE INITIALLY DEFERRED bir constraint trigger'ı": deferrable constraint A10'da var, "constraint trigger" hiçbir yerde yok.
Beklenen: M2'deki terim tablosuna VACUUM, connection pool, RETURNING ve constraint trigger için birer satır.

### R17 (orta): Alternatiflerin birçok terimi terim tablosunda yok
Bölüm: M2 kartları (terim tablosu M2 başında).
Alıntı: "nested alan", "facet", "dynamic mapping", "refresh aralığı", "doc values", "PPL" (OpenSearch); "sort key ve distribution", "base RPU", "workgroup" (Redshift); "eventually consistent", "TransactionCanceledException", "item collection" (DynamoDB); "geohash" (kart 10); "gp3 storage'ın IOPS ve throughput ayarı" (kart 5); "KVKK" (kart 4, açılımı yok).
Sorun: Database'i hiç kullanmamış bir okuyucu bu gerekçelerde puanın neden düştüğünü anlayamıyor. "eventually consistent" iki kartta puan kırma nedeni (kart 4, kart 9), ama sayfada tanımı yok.

### R18 (orta): "Ya şöyle olursa?" Kart 4'te "verimi sil" yedekleri ve kopyaları kapsıyor mu?
Bölüm: kart 4, C2, M6.
Alıntı: "'Verimi sil' müşteriyi, adreslerini, ödeme yöntemlerini ve izinlerini ya hep ya hiç silmeli"; C2 "Sürekli yedek Amazon S3'e gider"; M6 "zero-ETL entegrasyonu dört table'ı … Redshift'e kopyalar".
Soru: Silinen müşterinin verisi point-in-time yedeklerinde ve Redshift kopyasında kalıyor. Hukuki yükümlülük karşılanıyor mu? Yedek saklama süresi bu kararı nasıl etkiler? Sayfa cevap vermiyor.

### R19 (orta): "Ya şöyle olursa?" Point-in-time restore'dan sonra uygulama ne yapar ve bu ne kadar sürer?
Bölüm: kart 1 R3, A6, C2.
Alıntı: kart 1 R3 "Point-in-time restore yanlış bir silmeyi saniye hassasiyetiyle geri alır"; kart 1 gereksinimi "Yedekten geri dönüş saatler sürerse mağaza o saatlerde satış yapamaz"; C2 "point-in-time restore ile belirli bir saniyeye yeni bir cluster olarak dönülür".
Soru: Restore yeni bir cluster açıyor. Kaç dakika sürer? Uygulama yeni endpoint'e mi geçer, yoksa silinen row'lar eski cluster'a geri mi kopyalanır? Bu arada gelen siparişlere ne olur? Kartın kendi korkusu ("saatler sürerse") cevapsız kalıyor.

### R20 (orta): "Ya şöyle olursa?" Serverless v2 ani bir tepeye ne kadar hızlı yetişir?
Bölüm: kart 3 R2, kart 8 R2, M5, C2.
Alıntı: kart 3 "minimum ACU kampanya öncesi yükseltilmelidir"; kart 8 "minimum ACU sabahtan önce yeterli olmalıdır".
Soru: ACU saniyeler içinde mi, dakikalar içinde mi artar? Minimum ne kadar yükseltilmeli? Bağlantı sayısı sınırı ACU'ya bağlı mı (0,5 ACU'da kaç bağlantı)? M5 minimum 0 ACU'yu anlatıyor; kartlar neden 0,5 seçiyor, uyanma ne kadar sürer? Cevaplar yok.

### R21 (orta): M7 simülasyonları R1 alt toplamını göstermiyor; kart 2'nin dersi simülasyonda görünmüyor
Bölüm: M7, sim-w_catalog (ötekiler de aynı biçimde).
Alıntı: simülasyon başlığı "Kart 2: ürün kataloğu, Aurora mı DocumentDB mi? (yakın yarış, R1'i DocumentDB kazanır)"; board sütunları "aday, R1.1, R1.2, R1.3, R1.4, R2, R3, R4, R5, puan /100, sıra".
Sorun: Kartın tablosunda "R1 42,2 / 50" ile "43,2 / 50" yan yana duruyor, simülasyonda bu sütun yok. Okuyucu "R1'i DocumentDB kazanır" sonucunu kendisi toplamak zorunda kalıyor. Bunun dışında beş simülasyonun toplamları, sıraları ve karar metinleri kartlarla tam olarak aynı (hepsini kontrol ettim).

### R22 (düşük): Kazanç ve kayıp listelerinde uygulamanın yapması gereken bazı işler eksik
Bölüm: kart 8 karar, kart 1 karar.
Alıntı: kart 8 R1.1 "Sabah yarışında ikinci istek hata alır"; kart 1 eksiler "bütün yazmalar tek writer'dan geçer; …".
Sorun: Kart 8'in eksilerinde uygulamanın exclusion hatasını yakalayıp hastaya başka bir aralık önermesi gerektiği yazmıyor. Kart 1'in eksilerinde çok ürünlü sepette deadlock ve yeniden deneme yok; B5'te önlem var ("sepet satırlarını product_id'ye göre sıralayıp") ama kart onu anmıyor.

### R23 (düşük): MVCC ve VACUUM eksiği kartlar arasında farklı alt maddeye yazılıyor
Bölüm: kart 1 (R1.4 OY), kart 3 (R1.2 OY), kart 10 (R1.3 DA).
Alıntı: kart 10 "kurye konumunun her güncellemesi MVCC ile yeni bir row sürümü … couriers table'ı VACUUM ile izlenir".
Sorun: Aynı mekanizma iki kartta OY'den, bir kartta DA'dan düşülüyor. Her kartta yalnız bir kez sayılıyor, ama kartları karşılaştıran okuyucu kafası karışıyor.

### R24 (düşük): R1 kataloğunun girişi "beş alt madde" diyor; hiçbir kartta beş yok
Bölüm: Mimar gözüyle, R1 kataloğu girişi.
Alıntı: "kimisinde üç alt madde, kimisinde beş".
Sorun: Kart 5'te üç, öteki dokuz kartta dört alt madde var.

### R25 (düşük): Anlamadığım cümle: "projeksiyon"
Bölüm: M1, Ö8 bloğu, "Sınırı".
Alıntı: "Extension'lar öğrenme ister (projeksiyon, GiST)".
Beklenen: "projeksiyon" ile harita projeksiyonunun (koordinat sistemi) kastedildiğini tahmin ediyorum. Ama R1 kataloğunun AO satırında "projection" başka bir anlamda kullanılıyor. Beklenen cümle: "koordinat sistemi (SRID) ve GiST index".

### R26 (düşük): Anlamadığım cümle: "Bu dört sözün kısaltması ACID'dir"
Bölüm: A6, Transaction kavramı.
Alıntı: "BEGIN onu başlatır; COMMIT …; ROLLBACK hepsini geri alır. … Bu dört sözün kısaltması ACID'dir".
Sorun: Hemen önceki cümlede üç anahtar kelime var, "dört söz" hangileri diye arıyorum. Ancak aşağıdaki tablonun başlığı ("bir transaction'ın dört sözü") açıklıyor. Beklenen: "Transaction dört söz verir; baş harfleri ACID'dir".

### R27 (düşük): Head-to-head başlıkları kendini tekrar ediyor
Bölüm: bütün M2 kartları.
Alıntı: "Aurora PostgreSQL ile kafa kafaya, DocumentDB: Document (DocumentDB) ile kafa kafaya."
Sorun: Aynı ifade bir cümlede iki kez geçiyor; okurken takılıyorum.

### R28 (düşük): Page sayısı iki yerde farklı
Bölüm: B1.
Alıntı: page kavramı "1.000 müşteri yaklaşık 15 page"; canlı plan "1.000 müşteri 20 page".
Sorun: Küçük bir fark, ama "yaklaşık 70 row bir page'e sığar" hesabı canlı ölçümle uyuşmuyor. Row başına ek alan (header, boş yer) bir cümleyle açıklanabilir.

### R29 (düşük): Kart ve simülasyonun dili ile A10 matrisinde küçük kaymalar
Bölüm: M7 simülasyon metni, Mimar gözüyle, A10.
Alıntı: simülasyon "Diskalifiye yoktur … katkı = puan x ağırlık / 10"; kural metni "Zorunlu satır ve eleme yoktur … puan × ağırlık / 10"; A10 Ö4 Aurora hücresi "PostgreSQL ile aynı; reader instance'lar okumayı taşır".
Sorun: Aynı kural iki kelimeyle anlatılıyor ("diskalifiye" ve "eleme"). Ö4 hücresi de Ö7'nin konusunu (reader) taşıyor.

### R30 (düşük): Görseller: dört görselin hepsinde "Şuna bak" var; alt metinler İngilizce
Bölüm: A3 (ER diyagramı), A5 (B-tree), A8 ve C2 (Aurora cluster şeması).
Alıntı: alt metin "Entity-relationship diagram: tables with primary keys (PK) …".
Sorun: Bütün görsellerin ve HTML akış şemalarının açıklaması neye bakılacağını söylüyor; bu bölümde ciddi bir eksik bulmadım. Yalnız `<img>` alt metinleri Türkçe sayfada İngilizce.

## 1. Anlamadığım cümleler ve beklediğim
R25 ("projeksiyon"), R26 ("dört söz"), R27 (tekrar eden başlık), R24 ("beş alt madde"), R28 (15 ve 20 page).

## 2. Anlamını bilmeden önce kullanılan terimler
R16 (ŞE, ACU, Limitless, DSQL, Global Database, VACUUM, connection pool, RETURNING, constraint trigger), R17 (OpenSearch, Redshift ve DynamoDB terimleri, eventually consistent, geohash, gp3, KVKK).

## 3. Sayfanın cevaplamadığı "Ya şöyle olursa?" soruları
R18 (verimi sil ve yedekler), R19 (point-in-time restore sonrası uygulama), R20 (Serverless v2 tepe hızı ve bağlantı sınırı), R14 (tek writer'ın sınırı nerede), R22 (exclusion hatası ve deadlock'ta uygulama ne yapar), R8 (var olan cluster yoksa kart 2).

## 4. İkna etmeyen karar gerekçeleri ve mimara sorum
R1, R2, R3, R5, R6, R7, R9, R10, R11, R12, R13, R15 (sorular her bulgunun içinde).
Kontrol listesine göre durum:
- En uygun servis gerçekten en uygun mu: kart 6 (Redshift), kart 5 (RDS), kart 3 ve 8 ikna edici. Kart 1, 4 ve 9'da RDS aday olmadığı için kontrol edilemiyor (R1). Kart 10'da Location Service anılmıyor (R10).
- Ağırlıklar hikâyeden geliyor mu: çoğunlukla evet. Kart 9 R4 (R5), kart 10 R4 (R9) ve kart 2/4'te R4 gereksiniminin ŞE'yi tekrar etmesi ("aylık yeni özellikler migration istemeden eklenebilmeli", "çeyrekte bir yeni izin türü kesintisiz eklenebilmeli") istisna.
- R1 yalnız engine'i mi puanlıyor: kart 6 R1.4 (R3) ve kart 3 DynamoDB R1.2 (R6) hariç evet. Multi-AZ, Serverless ve fiyat genelde R2–R5'te.
- Her eksik bir kez mi sayılıyor: R2, R6, R9, R11, R12 ihlal; R7, R13 ve R23 tutarsızlık.
- Gerekçeler somut mu: evet; komut adları, sayılar ve sınırlar var.
- Head-to-head'ler: hepsinde fark, rakibin gerçek gücü ve somut bir dönüşme koşulu var. Yalnız sayısal eşik tutarsız (R14).
- Aurora'nın kazanç ve kayıpları: her kartta var; uygulamanın yapacağı iş çoğunda yazılı (B5'e atıf, lock_timeout, I/O payını izlemek). Küçük eksikler R22'de.
- Karar, özet tablosu ve simülasyonlar: toplamlar her yerde aynı; özet tablosundaki on fark da doğru.

## 5. Dil
yalnız Türkçe sayfa

## 6. Neye bakılacağını söylemeyen görseller
Yok. Bütün görsellerde "Şuna bak" açıklaması var; alt metin dili için R30.

## Aurora PostgreSQL'i ne zaman seçerim: bir meslektaşa anlatabilir miyim?

- **RDS for PostgreSQL yerine:** Yük gün içinde ya da ay sonunda dalgalıysa (Serverless v2), failover 30 saniyenin altında olmalıysa, reader'lar sık ve hızlı eklenecekse ya da veri büyükse (storage ve IOPS ayarı yok) Aurora. Düz ve fiyat hassas yükte RDS (kart 5 ve 7). Eksik: kart 7'de aylık maliyet hesabı yok (R15). Küçük ve düz yüklerde (kart 1, 4, 9) RDS'in neden kaybettiği gösterilmiyor (R1).
- **Redshift yerine:** Raporlar yakın geçmişle (örneğin 90 gün) sınırlıysa, analist sayısı ve sorgu sayısı azsa ve ayrı servis istenmiyorsa Aurora'nın reader'ı yeter. Aksi durumda Aurora ve zero-ETL ile Redshift birlikte. Bunu açıkça anlatabilirim. Eksik: geçişin row sayısı ya da GB cinsinden kabaca bir eşiği.
- **DocumentDB yerine:** Kurallar birkaç collection'a ya da table'a yayılıyorsa (foreign key, CHECK, tek transaction), ekip SQL biliyorsa ve ilişkisel bir cluster zaten varsa Aurora. Eksik: sıfırdan başlayan bir katalogda cevap (R8) ve kart 2'deki R1 farkının tutarsız puanlamaya bağlı olması (R7).
- **DynamoDB yerine:** Table'lar arası kural, önceden bilinmeyen sorular (JOIN, GROUP BY) ve aralık ya da coğrafi kurallar varsa Aurora. Yalnız key ile erişim ve çok yüksek yazma hacmi varsa DynamoDB. Eksik: "çok yüksek"in sayısı; kartlar binler, on binler ve yüz binler arasında değişiyor (R14).
- **MemoryDB yerine:** Kural geri alınabilir bir transaction olmalıysa ve aynı veri üzerinde rapor (GROUP BY) gerekiyorsa Aurora. Sıcak bir key'e saniyede binlerce yazma ya da mikrosaniye cevap gerekiyorsa MemoryDB. Anlatabilirim; eşik yine belirsiz (R14).
- **OpenSearch yerine:** Veri resmi kayıtsa ve transaction ile ilişki gerekiyorsa Aurora. Metin araması, relevance ve keşif ekranı için OpenSearch, Aurora'nın yanında bir tamamlayıcı. Bunu açıkça anlatabilirim. Eksik: kart 10'da Location Service ile karşılaştırma (R10).

Sonuç: Evet, büyük ölçüde anlatabilirim. Eksik olanlar sayısal eşikler (tek writer'ın sınırı, Redshift'e geçiş, Serverless ile provisioned maliyeti) ve küçük yüklerde aynı engine'li RDS ile yapılmış dürüst bir karşılaştırma.

## Kapanış (yazar)

Tarih 2026-10-30. Her bulgu ya sayfada / kart verisinde düzeltildi ya da yazılı bir gerekçeyle kapatıldı. Kontroller düzeltmelerden sonra yeniden çalıştı: `check_usecases.py --app app aurora` → `usecases: OK`; `check_page.sh --tr` → `clarity: OK`; simülasyon testi 14 simülasyon, 0 hata; 26 checkpoint'in hepsi açılıyor; `dynamodb` hâlâ `usecases: OK`.

| Bulgu | Durum | Nasıl kapandı |
|---|---|---|
| R1 | düzeltildi | RDS for PostgreSQL kart 4'te (DynamoDB yerine) ve kart 9'da (DocumentDB yerine) aday oldu: kart 4 Aurora 96,6, RDS 92,6; kart 9 Aurora 96, RDS 96 (eşit, yakın yarış; karar sistemin geri kalanına bağlı). Kart 1'in kararına RDS'in neden aday olmadığı yazıldı (R1 eşit; Aurora Lale Market'te zaten çalışır; sıfırdan düz yükte RDS yakın yarışa girer). M2 özeti RDS'in hangi kartlarda gösterildiğini ve kart 1, 2, 3, 8, 10'da neden gösterilmediğini söyler. |
| R2 | düzeltildi | Kart 7'de RDS'in R4'ü 8'den 9'a çıktı ve gerekçesi yalnız gp3/instance ayarıdır ("ay sonu kapasitesi R2'de ve R5'te sayıldı"). R2 (sabit yazma kapasitesi, büyümede sınıf değişikliği) ve R5 (tepe boyutunun boşa ödenmesi) ayrı mekanizmalardır. Aurora'nın R2'si de 10 oldu (aşağıda R11). Yeni toplam Aurora 94, RDS 87. |
| R3 | düzeltildi | Kart 6 R1.4 OY artık yalnız engine'i puanlar: Redshift columnar güncelleme maliyeti, Aurora row store, OpenSearch document sürümü. Zero-ETL ve OpenSearch Ingestion R4 gerekçelerine taşındı; satırın "ne istiyoruz" cümlesi boru hattı değil engine'in yazma biçimidir. |
| R4 | düzeltildi | B6'daki cümle değişti: sayfanın fiyatları tek bir tarihin fiyatlarıdır (eu-central-1, on demand, Price List API, 2026-10-29), ACU-saat 0,14 USD; karar öncesi güncel fiyat kullanılır. |
| R5 | düzeltildi | Kart 9'da R4 18'den 10'a indi ve artık operasyon ve ekibi puanlar (yeni database türü, migration); "kural tek yerde" R1'de kaldı (TA 20, EY 14, YD 10; R1 toplam 56). Weight note yeniden yazıldı. |
| R6 | düzeltildi | Kart 3 DynamoDB R1.2 10 oldu ("transaction'lı yazmanın birim maliyeti R5'te sayıldı"). DynamoDB ikinci sıraya çıktı (79,9; MemoryDB 78,8); kartın aday sırası ve kararı güncellendi. |
| R7 | düzeltildi | Kart 2 Aurora R1.1 gerekçesinden type denetimi çıkarıldı; iki adayda da serbest alanların type denetimi ayrı bir kural ister (CHECK ya da $jsonSchema) ve puan kırmaz. 3 puan JOIN ve iki model için kırılır. R1 sonucu değişmedi (42,2 / 43,2). |
| R8 | düzeltildi | Kart 2'nin kararına sıfırdan başlayan proje hesabı eklendi: Aurora R4 7, R5 7, toplam 84,1; DocumentDB 82,1 ile yine 2 puan geride (SQL ekibi). Döngüsellik açıkça hesaplandı. |
| R9 | düzeltildi | Kart 10 OpenSearch R3 artık snapshot aralığını puanlar ("resmi kayıt değil" çıkarıldı; transaction R1.4'te, ayrı servis R4'te, ayrı maliyet R5'te). R4'ün "ne istiyoruz" cümlesi ayrı servisi yasaklamaz, bedelini söyler. |
| R10 | düzeltildi | Kart 10 kararına Amazon Location Service eklendi: database değildir, geofence ve yol ağı üzerinde rota verir; yol mesafesi gerekirse ikisi birlikte çalışır. Aurora R1.1 gerekçesi ST_Length'in geometrik uzunluk olduğunu söyler. Terim tablosuna eklendi; scope dosyasında "neden aday değil" var. |
| R11 | düzeltildi | Kural: ACU aralığını seçmek R4'te, bilinen bir tepeden önce minimumu yükseltmek R2'de sayılır. Kart 2, 4, 7, 8'de R2 10'a çıktı, ACU seçimi R4'e taşındı (kart 2 R4 8, kart 4 R4 9). Kart 3 R2 bir sıçrama davranışı olarak kaldı ve gerekçesi kaynaklı ("scale faster at higher capacities"). Kart 10 R2 artık konum geçmişinin büyüklüğünü puanlar. |
| R12 | düzeltildi | Kart 1 DocumentDB R1.4 10 oldu ("transaction'ın kendisi R1.1'de sayıldı"). |
| R13 | düzeltildi | Kart 4'te DynamoDB yerine RDS aday oldu; siparişlerin yeri iki PostgreSQL adayında aynıdır, DocumentDB'de başka collection olarak yazılı. |
| R14 | düzeltildi | A8'deki "Okuma ölçeği…" kutusuna ve M2 özetine cümle eklendi: kartlardaki "saniyede binlerce / on binlerce" bir eşik değil büyüklük sırasıdır, sınır instance ve transaction'a bağlıdır ve pgbench ile ölçülür; checkpoint'teki 50.000 bir örnektir. Kart 1 kararında da aynı not var. |
| R15 | düzeltildi | Kart 7 R5 gerekçelerine kaynaklı örnek hesap: Serverless v2 2.112 ACU-saat × 0,14 = ~296 USD; RDS db.r6g.xlarge 720 × 0,549 = ~395 USD; head-to-head'e Aurora provisioned (720 × 0,627 = ~451 USD) ve RDS'i her ay büyütüp küçültme seçeneği eklendi. |
| R16 | düzeltildi | A2 caption'ından "ŞE" çıktı; A8'de ACU yerine "bellek ve CPU boyutu", Global Database, Limitless ve DSQL yerinde kısa tanımlandı; A6'da VACUUM tanımlandı; terim tablosuna VACUUM, connection pool, RETURNING, constraint trigger / DEFERRABLE, partition (PostgreSQL), gp3 ve reserved instance eklendi. clarity: OK. |
| R17 | düzeltildi | Terim tablosuna eventually consistent, transaction çakışması, nested, dynamic mapping, refresh, facet, doc values, PPL, sort key, distribution, base RPU, workgroup, geohash, KVKK ve Amazon Location Service eklendi; kart 4'te KVKK açıldı. |
| R18 | düzeltildi | Kart 4 kararı: point-in-time yedekleri silinen müşteriyi saklama süresi (1–35 gün) dolana kadar tutar ve bu süre gizlilik politikasında yazılmalıdır; zero-ETL kopyası silmeyi değişiklik olarak alır. |
| R19 | düzeltildi | C2'ye "Point-in-time restore ne kadar sürer ve uygulama sonra ne yapar?" kutusu: yeni cluster açılır, süre veri boyutuna bağlıdır ve tatbikatla ölçülür, saklama 1–35 gün, uygulamanın iki yolu (row'ları geri yazmak ya da adresi değiştirmek). Kaynak: restore-db-cluster-to-point-in-time. |
| R20 | düzeltildi | C2'deki Serverless v2 kutusu: yüksek kapasitede daha hızlı ölçeklenme (kaynaklı), 0 ACU'da en az 5 dakikalık boşluktan sonra duraklama ve ilk bağlantının uyanmayı beklemesi, max_connections'ın maksimum ACU'ya göre olması ve minimum 0/0,5 ACU'da en fazla 2.000. Terim tablosu kartların neden 0,5 varsaydığını söyler. |
| R21 | gerekçe + düzeltme | Simülasyonun puan tablosu `weighted_scorecard` (paylaşılan kod) tarafından çizilir; R1 alt toplam sütunu eklemek paylaşılan bir değişikliktir ve bu işte yasaktır. M7 lead'ine "R1 katkılarını topla ya da karttaki R1 sütununa bak (42,2 / 43,2)" cümlesi eklendi. Beceri için bir boşluk olarak raporlandı. |
| R22 | düzeltildi | Kart 8 eksilerine exclusion hatasını (SQLSTATE 23P01) yakalayıp en yakın boş aralığı önermek; kart 1 eksilerine product_id sırasıyla düşürme ve 40P01'de yeniden deneme eklendi. |
| R23 | gerekçe | Kart 1 ve 3'te MVCC yazmanın biçimidir (OY). Kart 10'da OY satırı yoktur ve sorun GiST index'ine her güncellemede yazılan yeni entry'dir; bu depolama algoritmasının (DA) maliyetidir ve gerekçe bunu söyler. Her kartta bir kez sayılır. |
| R24 | düzeltildi | Katalog girişi: "katalog üç ile beş arası alt maddeye izin verir; bu sayfanın kartlarında üç ya da dört alt madde vardır". |
| R25 | düzeltildi | M1 Ö8: "PostGIS'te koordinat sistemleri ve GiST index'i". |
| R26 | düzeltildi | A6 Transaction kartı: "Bir transaction dört söz verir ve bu sözlerin baş harfleri ACID'dir … (aşağıdaki tablo dördünü açar)". |
| R27 | gerekçe | Başlık satırı ("<en uygun> ile kafa kafaya, <aday>:") paylaşılan `wusecase` macro'sundan, paragrafın ilk cümlesi ise beceri kuralından gelir (writing-rules.md: "<Kategori> (<Servis>) ile kafa kafaya." ile başla). İkisini değiştirmek paylaşılan parçaları değiştirir; DynamoDB sayfasıyla aynıdır. Beceriye bildirildi. |
| R28 | düzeltildi | B1 Page kartı: row başlıkları ve boş yer sayıyı artırır; canlı table 1.000 müşteri için 20 page'tir. |
| R29 | kısmen düzeltildi | A10 Ö4 Aurora hücresi "PostgreSQL ile aynı planner ve index türleri" oldu. "Diskalifiye" ve "x" paylaşılan `weighted_scorecard` metnidir (DynamoDB sayfasında da aynı); değiştirilmedi, beceriye bildirildi. |
| R30 | gerekçe | `img` alt metinleri paylaşılan `e2e/images.yaml` kayıtlarından gelir (var olan kayıtlar, başka sayfalar da kullanır); caption'lar Türkçedir ve neye bakılacağını söyler. Paylaşılan kayıtları değiştirmek bu işin kısıtı dışındadır. |

Aynı gün çalışan ikinci bir soğuk okuyucunun (aynı sayfa) bu raporda olmayan ek bulguları da kapatıldı:

| Bulgu | Durum | Nasıl kapandı |
|---|---|---|
| E1 (yüksek) bağlantı havuzunda önceki tenant'ın `app.tenant` değeri kalırsa | düzeltildi | B7 RLS clause tablosu: `SET LOCAL` ya da havuza dönüşte `RESET`; değer yoksa `current_setting` hata verir ve row dönmez. |
| E2 (orta) "minimum ACU boşta ödenir" ile M5/C2'deki 0 ACU çelişkisi | düzeltildi | Terim tablosu ve C2 kutusu: 0 ACU duraklama ve uyanma bekleme; canlı sistem için 0,5 ACU ve üstü varsayımı. |
| E3 (orta) failover süresi R3'te puanlanıyor ama R3 "kayıp" diye tanımlı | düzeltildi | R1–R5 tablosunda R3'ün sorusu "kaybı ya da bir süre erişilemez olması" oldu; kart 7'nin R3 isteğine "servis birkaç dakika içinde dönmeli" eklendi (kart 4 ve 5'te zaten vardı). |
| E4 (orta) kart 5'in ağırlık notu R2 hakkında kendisiyle çelişiyor; R3'ün ağırlık nedeni adaylara bakıyor | düzeltildi | Weight note R5 20 ve R2 18'i ayrı nedenlerle açıklar; R3 nedeni hikâyeye bakar ("bir iki dakikalık kesinti tolere edilir, kayıp edilmez"). |
| E5 (orta) kart 5'te Aurora provisioned fiyatla puanlanıyor ama ACU'dan kırılıyor | düzeltildi | Kart 5 Aurora R4: "Standard / I/O-Optimized seçimi ve instance sınıfı". |
| E6 (orta) kart 8 R1.4 gerekçesi kendisiyle çelişiyor | düzeltildi | Gerekçe önce sorunu (TTL yok, constraint zamanı bilmez), sonra yazmanın içindeki çözümü, sonra 3 puanın nedenini söyler. |
| E7 (orta) kart 2, 4, 8'de R4 isteği R1 ihtiyaçlarını tekrar ediyor | düzeltildi | Üç kartın R4 "ne istiyoruz / neden önemli" metni operasyon ve ekibe indirildi (yeni database türü, izleme, nöbet). |
| E8 (orta) A6, kart 7'de bir Serializable örneği vaat ediyor | düzeltildi | A6 cümlesi kart 7'nin constraint trigger yolunu söyler. |
| E9 (orta) kart 3: kilitli rezervasyon toplamı sıcak row'da 100 ms altında kalır mı | düzeltildi | Kart 3 Aurora R1.2 gerekçesi: saniyede 15 istek ve birkaç ms'lik transaction ile sınır rahattır, pgbench ile ölçülmelidir. |
| E10 (orta) "partition" iki anlamda, PostgreSQL anlamı tanımsız | düzeltildi | Terim tablosuna "Partition (PostgreSQL)" ve DynamoDB anlamıyla farkı eklendi. |
| E11 (düşük) M7'deki renk açıklaması başka simülasyon türüne ait | gerekçe + düzeltme | Açıklama kutusu paylaşılan JS'dir; M7 lead'i bu beş simülasyonda renklerin anlamını söyler. |
