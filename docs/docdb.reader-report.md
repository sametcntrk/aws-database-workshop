# Okuyucu raporu: Amazon DocumentDB E2E (TR)

Okuyucu profili: daha önce hiç document database ya da DocumentDB kullanmamış biri. Kaynak: /tmp/docdb_tr.html (HTML metni ve simülasyonların JSON adımları). Hiçbir dosya düzeltilmedi.

## 1. Anlamadığım cümleler (ve ne bekliyordum)

- Başlık (üst bilgi): "35 dakika". Sayfada on uzun kart, dokuz simülasyon ve on beşten fazla "bütün durumlar" tablosu var. 35 dakika gerçekçi gelmedi. Bölüm bazında bir süre ya da "ilk okumada A ve M1–M2 yeter" gibi bir yol bekliyordum.
- A5 #index: "beş index'li bir collection'a yapılan her ekleme altı yapıya yazar." Altıncı yapı nedir? Document'ın kendisi mi, yoksa _id index'i mi? _id index'i beşe dahil mi? Açık bir sayım bekliyordum.
- A5 #index: "Lale Market'in kategori sayfasındaki 'Collection scan' deneyi tam tersini yapar: $natural ipucuyla index'i kapatır." Lale Market'te nasıl bir "deney" olduğu burada anlatılmıyor. Bir link ya da bir cümlelik açıklama bekliyordum.
- A7 #pipeline (tablo): "$lookup … Her ürünün her sürümünde aynı biçimler desteklenmez." Burada "ürün" yazılım ürünü (MongoDB/DocumentDB) demek. Ama sayfanın her yerinde "ürün", Lale Market'in sattığı mal anlamında kullanılıyor. İlk okumada "her ürün document'ının sürümü" diye anladım. "Her database ürününün" bekliyordum.
- A7 #pipeline: "Canlı collection'da 200 ürün ve 400 etiket vardır (B4)." 400 farklı etiket var gibi okunuyor. B4'te bunun 400 etiket kullanımı (6 farklı etiket) olduğu anlaşılıyor. "400 etiket ataması" bekliyordum.
- A7 #pipeline (Önce tahmin et): "Sıralama eşit sayıda ise etiket adına göre devam eder: 'yeni' ve 'çevreci' en üstte." Türkçe alfabede "çevreci" "yeni"den önce gelir, ama simülasyon "yeni"yi önce gösteriyor. Ayrıca Q3'te (B4) sadece `{ $sort: { products: -1 } }` var, adla ikinci bir sıralama yok. Bu cümle neye dayanıyor?
- A9 #replicas (görsel altı): "Yeşil kutu tek yazma noktasıdır." Yeşil hangi kutu? A2'de "yeşil = array" denmişti. Kutunun adını ("primary kutusu") bekliyordum.
- A10 #summary: "DynamoDB (… A2'deki 'her field'a göre soru' farkını göstermek için)". "Her field'a göre soru" A4'ün konusu. A2'ye dönünce aradığımı bulamadım.
- A10 #summary: "yeni projelerde en yeni engine sürümü (Lale Market'te 8.0.0)". Aynı tabloda "8.0.2 ve sonrası" geçiyor. O zaman 8.0.0 en yeni değil mi? Engine sürümü ile yama sürümü (8.0 / 8.0.2) arasındaki farkın açıklamasını bekliyordum.
- #architect: "R3 Dayanıklılık … Bir arızada bu verinin kaybı ne demek: yeni bir login mi, çift çekilen bir kart mı?" "Yeni bir login" bir kayıp örneği olarak anlaşılmıyor. "Kullanıcının yeniden giriş yapması mı" bekliyordum.
- #architect: "Alternatiflerin adları (GSI, TTL, ACU, mapping) kendi sayfalarında tanımlıdır." Sadece bu sayfayı okuyorum (İngilizce sayfa yok, diğer sayfalar elimde değil). Bir mini sözlük ya da link bekliyordum. Ayrıca TTL bu sayfada tanımlı (A5), yani liste karışık.
- M2 #usecases kart 4 (DynamoDB kafa kafaya): "Kategori doğru görünür, hacim yanlış yere koyar." Bu cümleyi anlamadım. "Şekil document'a uyuyor ama yazma hacmi onu dışarıda bırakıyor" bekliyordum.
- M2 #usecases kart 4 ve kart 9: DocumentDB satırının başlığı "Document (DocumentDB) · seçilen servis". İki kartta da DocumentDB kaybediyor. "Seçilen servis" ne demek? "Bu sayfanın servisi" ya da "değerlendirilen servis" bekliyordum.
- M2 #usecases kart 2, 3, 5, 7 ("Hangi koşul değişseydi"): "… sorular sabit üç soruya inseydi, array içi güncelleme nadir olsaydı ve okuma hacmi saniyede yüz binlere çıksaydı." "ve" ile bağlanan üç koşul hepsi birlikte mi, yoksa herhangi biri mi gerekiyor? Kartın "Bir koşul değişseydi" cümlesi ise tek bir koşul söylüyor.
- M7 #decide ve B2/B3/B4 simülasyon lejantı: "okunuyor eşleşti okundu ve atlandı kilitli sonuçta yeni reddedildi ya da yanlış". Bu lejant puan tablosu simülasyonlarında da var, ama orada hiçbir şey "kilitli" değil. Puanların önündeki "✓" işareti hiçbir yerde açıklanmıyor (JSON'dan 8 ve üzeri puanlar olduğu anlaşılıyor). Kendi lejantı olan bir puan tablosu bekliyordum.
- B1 #names: "// One document, 12 top-level fields, 406 bytes." B2'de "// 9 documents match the filter. 4.6 ms" ve "// { tags: 'indirim' } matches …". Türkçe sayfada İngilizce yorumlar ve "planner's choice / docs examined" sütun adları var. Türkçe bekliyordum.
- B2 #reads (simülasyon): "FETCH sadece o document'ı okur." FETCH aşaması hiç tanımlanmamış. explain tablosunda da görünmüyor (LIMIT_SKIP → IXSCAN).
- B2 #reads: "İç aşama önce çalışır: aşamaları sağdan sola oku." Sütun başlığı "outer → inner". Sağdan sola okumanın hangi sütun için geçerli olduğu kafamı karıştırdı.
- B5 #ttl (Q4): Kod `cursor = db.products.watch(full_document='updateLookup')` ve `for change in cursor:` Python (pymongo), diğer örnekler mongo shell sözdizimi. Dilin değiştiği söylenmiyor.
- C3 #lalemarket: "replicaSet='rs0'". Sayfa "replica set MongoDB'nin terimidir, DocumentDB'de cluster var" diyordu. DocumentDB'ye neden bir replica set adıyla bağlanılıyor? "rs0" nereden geliyor?
- C3 #lalemarket: "Database'e sadece DocumentDB Engine App'in security group'u ulaşabilir; Engine App private bir subnet'teki bir EC2 instance'ındadır." Engine App'in ne olduğu hiç anlatılmıyor ("Workshop canlı DocumentDB'ye AWS'teki Engine App üzerinden…", B1).

## 2. Anlamını bilmeden karşılaştığım terimler

- #goal: "MongoDB replica set" (tanımı A9'da), "find ve explain", "update operator'ları" (tanımı A6'da), "Secrets Manager" (başlık; tanımı yok).
- A1 #why: "PostgreSQL'in JSONB'si". Burada kısaca açıklanıyor, ama "JSONB" sonraki bütün kartlarda teknik ayrıntıyla (GIN index, jsonb_set, MVCC) kullanılıyor.
- A2 #model: "primary key" (A2'nin sonunda "_id ile primary key aynı şey mi" sorusu var, ama terim önce kullanılıyor), "foreign key", "JSON Schema", "object storage", "S3", "MiB".
- A2 #model (identifier tablosu): "DynamoDB'deki sepet, Aurora'daki sipariş satırları, OpenSearch'teki arama kopyası ve Neptune'daki graph". Dört servis de tanıtılmadan geçiyor.
- A3 #nesting: "ON DELETE kuralları", "zaman sıralı store".
- A4 #query: "key-value database" (ilk kullanım; tanım yok), "relevance", "search engine".
- A5 #index: "B-tree" kısaca anlatılıyor; "planner", "hint" kullanılıyor; "$natural" açıklanmıyor.
- A6 #writes: "matchedCount" (önce tabloda geçiyor, açıklaması sonra), "commit".
- A7 #pipeline: "left outer join", "data warehouse".
- A8 #changes: "cache", "Kinesis, MSK".
- A9 #replicas: Diyagramda "AZ b", "AZ c" geçiyor, "Availability Zone" ise ancak sonraki tabloda açılıyor. Ayrıca "driver" (read preference tanımında), "cluster" (ilk kullanımda tanımsız), "shard" (görsel altı ve tablo; shard'ın kendisi tanımlanmıyor, sadece shard key), "hash", "point-in-time restore", "commit edildi".
- A10 #summary: "GetItem", "Scan", "GSI", "LSI", "attribute", "partition", "UpdateItem", "oplog", "cluster volume", "sparse, partial, wildcard, text, geo, vector" index türleri, "DynamoDB Streams".
- #architect: "instance", "serverless", "DCU", "elastic cluster", "I/O", "Standard model". Hepsi tek bir paragrafta sıkıştırılmış.
- M1 #signals: "migration", "slug", "firmware", "facet", "event", "Lambda", "Redshift", "ElastiCache".
- M2 kart 1: "GIN index", "jsonb_set", "MVCC", "reader instance", "ACU", "CHECK", "domain" (OpenSearch), "refresh aralığı", "mapping", "reindex", "node", "replica shard", "Multi-AZ", "$jsonSchema".
- M2 kart 2: "Simple primary key", "on-demand", "point-in-time recovery" (restore ile farkı?), "birim" ("okuma başına birkaç birim"; hangi birim?).
- M2 kart 3: "CDN", "Node.js", "SDK".
- M2 kart 4: "payload", "drop etmek", "sort key", "Query", "bulk", "rollover", "ISM politikaları", "dashboard", "provisioned kapasite".
- M2 kart 5: "time series database".
- M2 kart 6: "ConditionExpression", "mantıksal replication", "trigger", "I/O-Optimized" (tanımı M5'te, sonra geliyor).
- M2 kart 7: "checkout", "outbox", "list_append".
- M2 kart 9: "Valkey", "hash", "GET / HSET / EXPIRE", "ECPU", "GB-saat", "HTTP".
- M2 kart 10: "feature flag", "A/B varyantları", "mikroservis", "segment", "polling", "AppConfig".
- M3 #away: "Keyspaces", "Timestream for InfluxDB", "Neptune", "Graph database".
- M5 #aws: "global clusters", "working set", "parameter group", "major sürüm".
- M6 #lalemarket-arch: "Seed" (büyük harfli bir özel ad gibi kullanılıyor, ne olduğu anlatılmıyor), "production".
- B1 #names: "BSON" (burada tanımlanıyor, ama "BSON tipleri" tablosundaki "Decimal128" yanında para hesabı neden önemli, kısa), "Engine App", "Workshop", "cluster'ın yazma adresi" (endpoint ancak C2'de tanımlanıyor), "shop database'i" (B2'de ilk kez).
- B6 #cost: "veri transferi", "yedek storage".
- C1 #selfrun: "bölünmüş ağ", "TLS", "roller".
- C2 #service: "DNS", "port", "replica set mode", "instance endpoint".
- C3 #lalemarket: "CloudFormation (cloudformation/workshop.yaml)", "AWS::DocDB::DBCluster", "KMS", "security group", "subnet", "EC2", "CA paketi", "engines/docdb.py" (bir kod dosyası; okuyucu bunu göremez).

## 3. "Ya … olursa?" diye sorup cevap bulamadığım yerler (eksik durumlar)

- A2 #model: Bir field'ın değeri `null` ise ne olur? `{ field: null }` filtresi, field'ı olmayan document'ları da bulur mu? Tabloda "field yok" ve "farklı tip" satırları var, "null" yok.
- A2 #model: Uygulama _id olarak bir sayı verirse ve başka bir document'ta aynı değer metin olarak ("1" ile 1) durursa ikisi çakışır mı?
- A3 #nesting: Bir embedded document'ı birçok document'ta kopya olarak tutuyorsam ("marka adı yüz bin üründe"), bu kopyaları güncellemenin önerilen yolu ne? updateMany mi, change stream mi?
- A4 #query: Bir koşulu "VEYA" ile nasıl sorarım ($or)? Tabloda sadece VE ve $in var.
- A4 #query: Sıralama ve sayfalama (skip/limit) için filtre tablosunda satır yok. Kart 8 "sayfalama" istiyor ama sayfa bunun nasıl yapıldığını ve büyük skip değerlerinin maliyetini göstermiyor.
- A5 #index: Var olan büyük bir collection'a index eklenirken ne olur? Yazmalar bloklanır mı, ne kadar sürer? Kartlarda "her yeni soru için index kurulur" deniyor, ama kurmanın bedeli yok.
- A5 #index: Bir collection'da 64 index sınırına ulaşınca ne yapılır?
- A6 #writes: updateMany yarıda hata verirse "bir kısmı değişmiş kalır". Hangilerinin değiştiğini nasıl anlarım, nasıl tekrar denerim?
- A6 #writes: Transaction 1 dakika sınırını aşarsa ne olur? Otomatik geri mi alınır, uygulama ne hata görür?
- A8 #changes: Tüketici bir kaydı iki kez işlerse (yeniden başlatmada) ne olur? Akış "tam bir kez" mi teslim ediyor?
- A8 #changes: Change stream kayıtları birden çok collection için sıralı mı? Bir transaction'daki iki yazma akışa nasıl düşer?
- A9 #replicas: Failover sırasında yarıda kalan bir yazmanın sonucu ne? Uygulama yazmanın yapılıp yapılmadığını nasıl bilir? (B3'teki retryable writes 8.0.0'da kapalı. O zaman Lale Market'te bu durumda ne olur?)
- A9 #replicas: Bütün replica'lar çökerse secondaryPreferred okumaları primary'ye mi gider (C2 tablosunda geçiyor), primary'yi boğar mı?
- A10 #summary: Desteklenmeyen bir operator'ı kullanan bir uygulamayı geçirirken hangi araçla tarama yapılır? "Listele ve karşılaştır" deniyor, ama nasıl yapılacağı yok.
- M1 #signals Ö8 ve M2 kart 4/6/9: Tek bir primary saniyede kaç yazma taşır? Sayfa "1.500 sınıra yakın", "5.000 ağır", "80.000 aşar" diyor, ama hiçbir instance sınıfı için bir sayı ya da ölçme yolu yok. "Yazma hacmi tek primary'nin sınırında mı?" (M4 #questions) sorusunu bu yüzden cevaplayamıyorum.
- M2 kart 4: Elastic cluster ayrı bir aday olarak puanlansaydı ne olurdu? Kart onu sadece DocumentDB'nin R2 gerekçesinde anıyor. M3 ise "Daha iyi seçim: … ya da DocumentDB elastic cluster" diyor.
- M2 kart 1, 2: Kampanya günü okuma beş katına çıkınca yeni replica kaç dakikada hazır olur ve bu önceden planlanmalı mı? (M5 "dakikalar içinde" diyor; kart "kampanyada replica eklenir" diyor ama ne zaman eklendiğini söylemiyor.)
- M2 kart 6: Cihaz çevrimdışıyken yaptığı değişikliği "version" koşulu reddederse cihazdaki değişiklik ne olur? Kullanıcının değişikliği kaybolur mu, birleştirilir mi? Kart sadece "eski bir yazmayı reddeder" diyor.
- M2 kart 10: Change stream tüketicisi durursa "servisler 30 saniyelik okumayla telafi eder". Ama gereksinim "10 saniye içinde". Bu durumda gereksinim karşılanmıyor mu? Kart bunu söylemiyor.
- M2 kart 10: Cluster paylaşıldığı için başka bir iş yükünün COLLSCAN'i flag okumalarını yavaşlatırsa ne olur?
- M2 kart 7: Outbox tüketicisi saatlerce geride kalırsa "siparişlerim" ekranı ne gösterir? Kullanıcı az önce verdiği siparişi görmezse ne yapılır?
- M5 #aws: DocumentDB serverless ile instance-based arasındaki geçiş nasıl yapılır? Bir cluster'da ikisi karışık olabilir mi?
- B5 #ttl: Change stream açıkken TTL silmeleri akışa "delete" olarak düşüyor (A8 tablosu). Bu, I/O'yu iki kez mi artırır?
- C2 #service: "bir cluster 0 ile 16 instance arası olabilir". Sıfır instance'lı bir cluster ne işe yarar, veri nerede durur, para ödenir mi?
- C2 #service (endpoint tablosu): Uzun rapor "bir replica'nın instance endpoint'i"ne gönderiliyor. Failover'da o replica primary olursa rapor primary'yi yorar. Bu durumda ne yapılır?
- C3 #lalemarket: BackupRetentionPeriod 1 gün. Hafta sonu fark edilen yanlış bir silme geri alınamaz mı? Manuel snapshot'tan hiç söz edilmiyor.

## 4. İkna etmeyen karar gerekçeleri ve mimara soracağım sorular (M2 kartları, M7 simülasyonları)

- Kart 1 (katalog), R4 = 9: Gereksinimde "sunucu boyutlandırmak istenmiyor" yazıyor, ama DocumentDB instance sınıfı ya da DCU aralığı seçtiriyor. Soru: "Boyutlandırma istenmiyorsa, instance-based bir servis bu gereksinimde neden sadece 1 puan kaybediyor?"
- Kart 1, R4 gerekçesi (Neden önemli): "her ay bir bakım penceresi kategori ekibinin takvimini kilitler". DocumentDB'nin de bakım penceresi var (C2 tablosu: "Bakım penceresinde AWS"). Soru: "DocumentDB'nin bakım penceresi bu riski neden ortadan kaldırıyor?"
- Kart 2 (profil), R1: DynamoDB, "haftada değişen sorular için GSI kurulamaz" diye 2 puan kaybediyor. DocumentDB ise R1'de tam puan alıyor, ama haftada değişen her soru için ona da yeni bir index lazım (yoksa üç milyon profilde COLLSCAN). Bu bedel R4'e 1 puan olarak yazılmış. Soru: "Aynı sorun bir adayda R1'den, diğerinde R4'ten neden düşüyor?"
- Kart 2: "Bir puanlık fark bir karar değildir." Bu doğruysa karar neye dayanıyor? Kodun MongoDB driver'ı ile yazılmış olmasına mı? Soru: "Kod zaten MongoDB ile yazılmasaydı bu kart DynamoDB'ye mi dönerdi?"
- Kart 3 (makale), R5: "her yazma dört index'i günceller". Hangi dört index? R1'de slug unique, tags multikey ve status+published_at compound var. "Bu yazarın taslakları" sorusu için index anılmıyor. Soru: "Yazar sorusu index'siz mi çalışıyor?"
- Kart 3, R3 (zorunlu): "eski sürümleri geri getirilebilmeli." DocumentDB bunu "sürümler ayrı collection'da" ile karşılıyor. Bu uygulamanın işi, ama puan kırılmamış. Soru: "Sürüm geçmişini kod tutuyorsa servis R3'te neden 10 alıyor?"
- Kart 4 (event log), R3 = 9: "1 puan kırıldı: bu kartta dayanıklılık istenenden fazladır ve bedeli yazma hızındadır." Puan ölçeğinde 10 "sayıları aşarak karşılar" demek. Fazla dayanıklılık neden puan kaybettiriyor? Bedel yazma hızındaysa R2'den düşmesi gerekmez mi?
- Kart 4, DynamoDB R2 = 10: "on-demand 80.000 yazma/saniyeyi kendiliğinden karşılar". Kampanya gecesi trafik bir anda dört katına çıkıyor. Soru: "On-demand bu ani sıçramayı ısınma olmadan karşılıyor mu, hesap ya da tablo kotası var mı?"
- Kart 4: DocumentDB'nin "en büyük instance sınıfı" 20.000 eklemeyi taşır mı? Gerekçe bunu söylemiyor. Soru: "4 puan, 20.000'i taşıyıp 80.000'i taşımadığı için mi, yoksa hiçbirini taşımadığı için mi?"
- Kart 6 (liste senkronizasyonu), R2 = 9: "1.500 yazma tek primary'nin içindedir". Neden önemli sütunu ise "sınırın içinde ama ona yakındır" diyor. Sınıra yakın bir değer neden sadece 1 puan kaybediyor, oysa kart 9'da 5.000 yazma 3 puan, kart 4'te 20.000 yazma 6 puan kaybediyor? Soru: "Primary'nin sınırı kaç yazma/saniye, puanlar bu sayıya göre mi verildi?"
- Kart 7 (sipariş), R1 = 9: "1 puan kırıldı: ürün adı değişirse eski siparişlerde eski ad kalır; bu istenen davranıştır." İstenen davranış neden puan kaybettiriyor?
- Kart 7: Gereksinimlerde "Ekip bu okuma modelini ayrı bir serviste tutmak istiyor" yazıyor ve karar "çünkü ekip okuma modelini ayrı bir serviste istiyor" diyor. Karar gereksinimin içine yazılmış gibi duruyor. Soru: "Ayrı servis bir gereksinim mi, yoksa sorgulanacak bir tercih mi?"
- Kart 7, R4: Aurora "ek database yok, event taşıma parçası gerekmez" ile 8 alıyor. DocumentDB outbox ve tüketici kurmak zorunda kalıyor ama o da 8 alıyor. Soru: "Fazladan bir boru hattı R4'te neden fark yaratmıyor?"
- Kart 8 (katalog araması), karar: "yarışı R4 ve R5 (ikinci sistemin bedeli) DocumentDB'ye … çeker". Ama DocumentDB ve OpenSearch R4'te 8–8, R5'te 8–8. Fark R3'ten (10 – 7) geliyor, R3 ise bu kartta "tercihli" ve arama katmanı kaybolursa yeniden kurulabiliyor. Soru: "Karar gerçekte R3'e mi dayanıyor ve bu doğru mu?"
- Kart 8, R2 (DocumentDB 9): Facet sayıları her sayfa açılışında $group ile yeniden hesaplanıyor. Kampanyada saniyede 5.000 okuma demek, saniyede 5.000 aggregation demek. Soru: "Bu yük için kaç replica gerekir, 50 ms tutar mı? Bir ölçüm var mı?"
- Kart 9 (oturum), DynamoDB R2 = 10: Gereksinim "okuma 2 ms'nin altında". DynamoDB için yazılan ise "tek haneli milisaniye". Kafa kafaya paragrafı da "2 ms'lik okuma sınırı 10 ms'ye gevşeseydi DynamoDB seçilirdi" diyerek DynamoDB'nin bu sınırı karşılamadığını kabul ediyor. Zorunlu bir gereksinimi karşılamayan aday neden 10 alıyor?
- Kart 9, DocumentDB R2 = 7: Aynı şekilde "2 ms'nin altı okuma disk tabanlı engine için her zaman tutmaz". Zorunlu bir gecikme sınırını tutmayan aday puan ölçeğine göre 2–4 almaz mı?
- Kart 9, DynamoDB kafa kafaya: "kart yine de document sayfasındadır, çünkü ekip ilk olarak 'mevcut cluster'a bir collection' demiştir". Kart 9'un "Gerçek projede" paragrafında böyle bir cümle yok (bu cümle kart 4'te var). Soru: "Bu ekip DocumentDB cluster'ına sahip mi?"
- Kart 10 (feature flag): Kafa kafaya paragrafı "üç puanlık fark mevcut cluster'ın varlığına bağlıdır" diyor. Mevcut cluster R4 ve R5'te zaten puanlanmış. R1 farkı (10'a 7) ise "bütün flag'ler"in 300 item'lık bir Scan olmasından geliyor, ki kart bunu "kabul edilir" diye niteliyor. Soru: "Mevcut cluster olmasa fark kaça iner, R1 farkı gerçekten 3 puan mı?"
- Kart 10, R3 = 10: "history array'i geri almayı verir". A3, zamanla büyüyen bir array'i gömme diyor. Soru: "History hangi büyüklükte ayrı collection'a taşınır, bunu kim izler?"
- Genel (bütün kartlar), R4: "sunucu, yama, yedek istenmiyor" diyen kartlarda instance-based DocumentDB, serverless DynamoDB ile eşit ya da daha yüksek R4 puanı alıyor (kart 1, 2, 3, 5, 6). Bu puanı genelde "ekip API'ı biliyor" taşıyor. Soru: "R4'te ekip bilgisi ile operasyon yükü nasıl tartıldı? Bunlar iki ayrı gereksinim olmamalı mı?"
- Genel, R3: Üç aday R3'te neredeyse her kartta 10 alıyor. R3 bir karar vermiyor. Soru: "R3 bu iş yükleri arasında neden hiç ayrışmıyor? Bölge çapında bir arıza ya da yanlış silme hesaba katıldı mı?"
- M7 #decide: Simülasyonlar kartların birebir kopyası. Bir mimarın yeni bir şey öğrenmesi için bir koşul değiştirildiğinde ("yazma 2.000'e inerse") puanların nasıl değiştiğini görmek isterdim. Soru: "'Hangi koşul değişseydi' cümleleri neden bir simülasyon adımı değil?"

## 5. Sayfa içinde birbiriyle çelişen olgular, sayılar ya da id'ler

- A2 #model: "Renkler bütün sayfada aynı kalır: _id için sarı, embedded document için mavi, array için yeşil." Ama A9'da "Yeşil kutu tek yazma noktasıdır" (primary), B5'te "Sarı kutu belirsiz bir süredir" (TTL), C2 görselinde "sarı oklar" yazmalar, endpoints ve elastic görsellerinde ise yeşil/sarı kareler storage blokları.
- A3 #nesting: "Bu, M3'teki 'koleksiyonlar arası kural' sinyalinin nedenidir." M3'te bu adla bir satır yok ("Birçok ilişkili kayıt arasında kurallar"). Ayrıca sayfa genelde "collection" diyor, burada ve B2 simülasyonunda ("koleksiyondaki") "koleksiyon" deniyor.
- A7 #pipeline ile B4 simülasyonu: A7 eşitlikte "etiket adına göre devam eder" diyor, ama B4'teki Q3'ün `$sort` aşaması sadece `products: -1`. B4 simülasyonu "yeni"yi "çevreci"nin önüne koyuyor. Türkçe alfabetik sırada bu tersi olurdu.
- B4 simülasyonu, "yeni" etiketinin ortalama fiyatı "2346.0" olarak görünüyor. Öğretici kopyadan hesap 2345,75 (3884,10 + 84,61 + 2721,65 + 2693,65 = 9383,01 / 4). Diğer satırlar iki ondalık basamakla doğru.
- A10 #summary ile B3 #updates ve C3 #lalemarket: A10 "yeni projelerde en yeni engine sürümü (Lale Market'te 8.0.0)" diyor. B3 ve C3 ise retryable writes, $graphLookup ve $facet için 8.0.2 ve sonrası gerektiğini söylüyor. Lale Market en yeni sürümde değil.
- A2 #model ve A10 matrisi: "iç içe yapı en fazla 200 seviyedir … MongoDB'de ve DocumentDB'de". Matriste bu sınır sadece DocumentDB hücresinde var, MongoDB hücresinde yok. (Okuyucu olarak doğrulayamıyorum. Bu sayı sayfa dışından kontrol edilmeli.)
- A9 #replicas görseli (shard key) ile C2 #service elastic görseli: İlki "Uygulama her document'ı user_id'nin hash'ine göre bir shard'a gönderir" diyor ve uygulamayı doğrudan shard'lara bağlıyor. C2 ise "bir istek yönlendiricisi her isteği … doğru shard'a gönderir" diyor ve araya request router koyuyor. Shard'ı kim seçiyor?
- A9 #replicas görsel altı: "her shard kendi primary'siyle yazmaları ayrı karşılar". Görselde primary yok, shard'larda sadece isimler var. Ayrıca shard'lardaki isimlerin çoğu (Priya, Vijay, Emma, Charl, Bowen, Arjun, Henry, Mary) üstteki veri setinde yok.
- B2 #reads explain notu: "200.000'de COLLSCAN bin kat daha fazla document inceler, index'li yol yine 40." 200.000 üründe Kitap kategorisinde 40 değil yaklaşık 40.000 ürün olur. Sorgu `limit(48)` ile 48 document inceler. "Yine 40" sayısı tutmuyor.
- B2 Q1 ile B2 COLLSCAN simülasyonu: Q1'in projection'ı dört field (name, price, attributes.renk, attributes.garanti_ay). Aynı filtreyi oynattığı söylenen simülasyon sonunda üç field'lık projection diyor ({ name, price, attributes.renk }).
- Canlı çıktı başlıklarındaki id'ler: B2'deki find "(Engine App, /docdb/api/e2e/M2)", B4'teki pipeline "(/docdb/api/e2e/M5)". Bu sorgular M2 ya da M5 bölümünde değil, B2 ve B4'te.
- M2 #usecases giriş: "Kartların ikisinde (4 ve 9) DocumentDB kaybeder; üçünde (7, 8, 9) dürüst cevap 'ikisi birlikte'dir." Kart 5 ("iki servis birlikte doğru cevaptır: kayıt DocumentDB'de, ölçümler time series database'inde") ve kart 1 ("iki servis rakip değil tamamlayıcıdır: katalog DocumentDB'de, arama kopyası … OpenSearch'e") da "ikisi birlikte" diyor. Kart 8 ise bugünkü cevabın tek başına DocumentDB olduğunu, "ikisi birlikte"nin metin araması gelince geçerli olacağını söylüyor.
- Kart 1, OpenSearch kafa kafaya: "(kart 8 bu ikiliyi puanlar)". Kart 8 iki servisi birlikte değil, rakip olarak puanlıyor.
- Kart 4, DynamoDB kafa kafaya: "DocumentDB'nin gücü R1'de görünür". Puan tablosunda R1'de DynamoDB 8, DocumentDB 7. DocumentDB R1'de geride.
- Kart 6, DynamoDB kafa kafaya: "Ayrıştığı gereksinimler R1 ve R4." R4'te ikisi de 8. Asıl ayrışma R1 ve R2'de (9'a 10).
- Kart 7, Aurora kafa kafaya: "Ayrıştığı gereksinimler R1'in şekil kısmı, R4 ve R5." R4'te ikisi de 8.
- Kart 8, karar ve kafa kafaya: "yarışı R4 ve R5 … DocumentDB'ye çeker" ve "Ayrıştığı gereksinimler R1'in facet kısmı, R3 ve R4". R4 ve R5'te puanlar eşit (8–8, 8–8). Fark sadece R1'de (8'e 10) ve R3'te (10'a 7).
- Kart 9, DynamoDB kafa kafaya: "ekip ilk olarak 'mevcut cluster'a bir collection' demiştir". Kart 9'un iş yükü metninde bu bilgi yok (kart 4'te var).
- Kart 9, DynamoDB R2 = 10 ile aynı kartın kafa kafaya cümlesi ("2 ms'lik okuma sınırı 10 ms'ye gevşeseydi DynamoDB seçilirdi") birbirini tutmuyor. Puan ölçeğine göre 10, gereksinimi "sayıları aşarak" karşılamak demek.
- Kart 6 R2 ("1.500 yazma … sınırın içinde ama ona yakındır") ile kart 9 R2 (5.000 yazma: 7 puan, "Karşılar, ama … boyutlandırma") ve kart 4 R2 (20.000 yazma: 4 puan, "en büyük instance sınıfı ya da elastic cluster"): 1.500 sınıra yakınsa, 5.000 sınırın üstünde olmalı. Üç kart aynı sınırı farklı yerlere koyuyor.
- M5 #aws: DynamoDB satırı "Serverless key-value ve document database" diyor. A10 ise DynamoDB'yi "key-value modelinde çalışan servis" olarak ayırıyor ve matriste Ö3/Ö6'yı "✗" yapıyor.
- C2 #service: "Bunu C1'deki yedi işle karşılaştır". C1'deki yedi iş arasında "Şifreleme ve erişim" var. C2 tablosunda bu yok, yerine C1'de olmayan "API ve driver'lar" var.
- C3 #lalemarket: describe çıktısı "AvailabilityZones: eu-central-1a, eu-central-1b, eu-central-1c" diyor, ama instance'lar sadece 1b ve 1c'de. Ayrıca A9 diyagramı "primary (AZ b)", C2 görseli "primary (AZ 1)" diyor. Neyin neye karşılık geldiği açıklanmıyor (çelişki değil, ama kafa karıştırıyor).

## 6. Neye bakacağımı söylemeyen görsel ve diyagram altyazıları

- A5 #index, B-tree görseli (docdb-btree.png): Altyazı kökü ve yaprağı iyi anlatıyor. Ama yapraklardaki küçük noktaların (her girişin document'ı gösteren işaretçisi) ne olduğunu ve 1–21 sayılarının category_1_rating_-1 girişleriyle nasıl eşleştiğini söylemiyor. İndex girişinin document'a nasıl gittiğini (FETCH) görselden çıkaramadım.
- A9 #replicas, shard key görseli (docdb-shard-key.png): Altyazı "user_id'nin hash'ine göre" diyor, ama görselde hash değeri yok. Fred'in (user_id 12) neden Shard0'a, Sam'in (9) neden Shard1'e gittiği anlaşılmıyor. Shard'lardaki fazladan isimler açıklanmıyor. Ne bekliyordum: "Kang ve Fred aynı shard'da, çünkü hash'leri aynı aralıkta" gibi bir yönlendirme.
- A9 #replicas, rol diyagramı (h4 kutuları): "Yeşil kutu tek yazma noktasıdır". Hangi kutunun yeşil olduğu metinde yok. Renk, A2'deki renk sözleşmesiyle çelişiyor (yeşil = array).
- B5 #ttl, TTL akış diyagramı: "Sarı kutu belirsiz bir süredir". Dört kutudan hangisinin sarı olduğu adla söylenmiyor ("süre doldu" kutusu olduğunu tahmin ettim). Sarı, A2'de _id'nin rengi.
- C2 #service, cluster görseli (docdb-cluster.png): Altyazı okları açıklıyor. Ama görselin ana mesajını, her AZ'de iki veri kopyası olduğunu ve toplamın altı kopya ettiğini göstermiyor. "Data copies" kutularını saymamı söylemiyor. Replica'ların değişikliği nasıl öğrendiği (C2 metni: "yazmanın durumunu bildirir") görselde yok, altyazı da bunu söylemiyor.
- C2 #service, endpoints görseli (docdb-endpoints.png): Storage'daki yeşil ve sarı karelerin ne olduğu (veri blokları? kopyalar?) söylenmiyor. Primary'deki sarı "Writes" oku ile mavi okların farkı da açıklanmıyor.
- C2 #service, elastic cluster görseli (docdb-elastic.png): Görseldeki kod parçaları (db.foo.find order_id 1, Db.foo.insert order_id 2, "inserted_id": 2) ve bunların hangi shard'a gittiği altyazıda yok. Shard key'in burada order_id olduğu söylenmiyor. Shard'ların altındaki gri oklar ve yeşil/sarı kareler açıklanmıyor.
- M7 #decide ve B2/B3/B4 simülasyonları: Ortak lejant ("okunuyor, eşleşti, okundu ve atlandı, kilitli, sonuçta yeni, reddedildi ya da yanlış") puan tablosu simülasyonlarında neye bakacağımı söylemiyor. Puanların yanındaki "✓" işaretinin anlamı hiçbir yerde yazmıyor.
- A1 #why, "Aynı ekranın iki yolu" diyagramı: Altyazı iyi. Ama ok başlarındaki sayılara ("tek okuma" ile üç tablo) bakmamı açıkça söylemiyor. (Küçük bir not.)

## Son soru: Bu sayfadan sonra bir iş arkadaşıma DocumentDB'yi DynamoDB yerine (ve Aurora yerine) ne zaman seçeceğini ve nedenini anlatabilir miyim?

Kısmen anlatabilirim.

Anlatabildiğim:
- DynamoDB yerine DocumentDB: Nesne iç içe ve array'li bir yapıysa ve uygulama bu nesnenin içine göre önceden bilinmeyen ya da sık değişen sorular soruyorsa DocumentDB seçilir. Örnekler: "firmware'i eski ve İzmir'de", "label'ı iş olan adres", "etiketi ekonomi olan, tarihe göre". Array içinde tek bir elemanı değeriyle bulup bir sürüm koşuluyla tek atomik yazmada değiştirmek gerekiyorsa da DocumentDB öne çıkar. Ekip zaten MongoDB API'sini kullanıyorsa bu daha da güçlenir. DynamoDB'de her yeni soru bir GSI ya da Scan'dir, liste elemanı ancak numarasıyla güncellenir ve item 400 KB ile sınırlıdır.
- Tersi, DynamoDB: Erişim hep bilinen bir key ile oluyorsa, yazma hacmi saniyede on binlere çıkıyorsa, otomatik süre sonu ya da "gece sıfıra yakın ödeme" gerekiyorsa DynamoDB seçilir (kart 4, 9, M3). Çünkü DocumentDB'de bütün yazmalar tek primary'den geçer.
- Aurora yerine DocumentDB: Veri çoğunlukla kendi içinde bütün nesnelerden oluşuyorsa, aynı türün öğeleri farklı field'lar taşıyorsa ve şekil sık değişiyorsa, nesneler arasında database'in koruması gereken kurallar (foreign key, CHECK, birkaç tabloyu kapsayan transaction) azsa DocumentDB seçilir. Tersine, stok/sipariş/ödeme gibi kurallı ilişkiler varsa Aurora seçilir.

Eksik olanlar (bunlar olmadan iş arkadaşımın "peki sınır nerede?" sorusunu cevaplayamıyorum):
1. Tek primary'nin yazma sınırı için hiçbir sayı ya da ölçme yolu yok. Kartlar 1.500'ü "sınıra yakın", 5.000'i "ağır", 20.000'i "aşıyor" diye farklı yerlere koyuyor. Bu yüzden "kaç yazmada DynamoDB'ye geçerim?" sorusunu cevaplayamıyorum.
2. Puanlamada tutarsızlıklar var: kart 9'daki 2 ms gereksinimi, kart 8'de karar veren gereksinimin eşit puanlı çıkması, kart 2'de index bedelinin bir adayda R1'den, diğerinde R4'ten düşmesi, "ayrıştığı gereksinimler" cümlelerinin tabloyla tutmaması. Bu yüzden yakın yarışların (kart 2, 7, 8) gerçekten neye dayandığını savunamıyorum. Kartlar kararın çoğunu "ekip MongoDB API'sini biliyor" ve "mevcut cluster var" cümlelerine bağlıyor gibi duruyor. "Ekip MongoDB bilmeseydi?" diye sorulsa, kart 2, 6 ve 10'un büyük ihtimalle DynamoDB'ye döneceğini söylemek zorunda kalırım.
3. DocumentDB elastic cluster hiçbir kartta aday olarak puanlanmıyor. Ama M3 onu, DynamoDB'nin yerine geçebilecek bir "daha iyi seçim" olarak gösteriyor. "Yazma hacmi yüksek ama sorgular document'ın içine göre" durumunu (kart 4'ün tersi) kim kazanıyor, bilmiyorum.
4. DynamoDB ile DocumentDB arasındaki maliyet karşılaştırması sayısal değil. B6'da sadece DocumentDB serverless için bir örnek var. Aynı iş yükü için iki servisin aylık tahmini maliyeti verilmemiş. Bu yüzden R5 puanlarını doğrulayamıyorum.
5. Aurora ile karşılaştırmada JSONB'nin sınırları ("daha az doğal", "zahmetli", "row'un tamamı yeniden yazılır") somut bir örnek ya da ölçümle gösterilmemiş. Terimler (GIN, MVCC, jsonb_set) bu sayfada tanımlanmadığı için "Aurora'nın JSONB'si neden yetmez?" sorusunu kendi cümlelerimle açıklayamıyorum.

Bunlar eklenirse (bir yazma sınırı ya da ölçme yolu, tutarlı puan gerekçeleri, elastic cluster'ın bir kartta aday olması, iki servis için kaba bir maliyet karşılaştırması ve JSONB'nin somut sınırı), bu sayfadan sonra kararı bir iş arkadaşıma güvenle savunabilirim.

---

# Kapanış (yazar): her bulgu için düzeltme ya da gerekçe

Durum: bütün bulgular kapatıldı. "Düzeltildi" sayfada ya da kart verisinde değiştirildi demektir; "Gerekçe" bulgunun neden kusur sayılmadığını ya da kapsam dışı olduğunu yazar. Kart toplamları değişti (aşağıda); `check_usecases.py` yeniden `usecases: OK` verdi.

## 1. Anlaşılmayan cümleler

- 35 dakika: Gerekçe. Süre `e2e/index.yaml`'daki ortak katalog alanıdır ve bütün engine sayfalarında aynı ölçekle tutulur; bu iş sadece DocumentDB sayfasını kapsar. Sahibine not: yeni yapıdaki sayfalar için süre ölçeğinin toplu güncellenmesi önerilir.
- "altı yapıya yazar": Düzeltildi (A5: "_id dahil beş index … document'ın kendisine ve beş index'e").
- "Collection scan deneyi": Düzeltildi (A5: deneyin ne yaptığı ve `$natural`'ın anlamı yazıldı).
- "$lookup … her ürünün her sürümü": Düzeltildi ("MongoDB'nin ve DocumentDB'nin her sürümünde").
- "400 etiket": Düzeltildi ("400 etiket ataması, altı farklı etiket", A7 ve B4).
- Eşit sayılarda sıralama: Düzeltildi. Yanlış cümle kaldırıldı; A7 eşitlerde sıranın garanti olmadığını ve `{ products: -1, _id: 1 }` çözümünü yazıyor.
- "Yeşil kutu": Düzeltildi (A9: "Yeşil çerçeveli 'primary' kutusu", rengin anlamı ayrıca belirtildi).
- "A2'deki her field'a göre soru": Düzeltildi (A4).
- 8.0.0 en yeni mi: Düzeltildi (A10: major 8.0, minor 8.0.2 farkı ve Lale Market'in neden 8.0.0'da olduğu).
- R3 "yeni bir login": Gerekçe. R1–R5 tablosu bütün sayfalarda ortak ve değiştirilmez (SKILL.md kural 7); DynamoDB ve Aurora sayfalarıyla aynı metin.
- "Alternatiflerin adları kendi sayfalarında": Düzeltildi. Mimar gözüyle girişine "kartlarda geçen alternatif adları" tablosu eklendi (GSI, TTL, on-demand, JSONB, GIN, MVCC, ACU, mapping, refresh, facet, EXPIRE vb.).
- Kart 4 "Kategori doğru görünür …": Düzeltildi ("Şekil document'a uyar, ama yazma hacmi onu dışarıda bırakır").
- "Seçilen servis": Düzeltildi (M2 girişi etiketin anlamını yazıyor; etiketin kendisi ortak `usecase` macro'sudur).
- "ve" ile bağlı koşullar: Düzeltildi (M2 girişi: "ve" ile bağlı koşullar birlikte gerekir; kararın son cümlesi en etkili tek koşulu söyler).
- Simülasyon lejantı ve ✓: Düzeltildi (M7 girişi ✓'nin 8 ve üzeri olduğunu ve kullanılmayan renkleri yazıyor). Lejantın kendisi ortak JS'tir.
- İngilizce yorumlar ve sütun adları: Gerekçe. Canlı çıktılar olduğu gibi gösterilir (writing-rules: "quoted console output stays unchanged"); B1 bunu bir cümleyle söylüyor.
- FETCH: Düzeltildi (B2'de tanım cümlesi).
- "Sağdan sola": Düzeltildi (B2 clause satırı dıştan içe yazımı ve çalışma sırasını açıkça veriyor).
- Python kod örneği: Düzeltildi (Q4 başlığı "shell" ve "Python, pymongo" diyor).
- `replicaSet='rs0'`: Düzeltildi (C3).
- Engine App: Düzeltildi (B1'de bir cümlelik tanım, C3'e bağlantı).

## 2. Anlamı bilinmeden karşılaşılan terimler

- Alternatif servislerin terimleri (DynamoDB, Aurora, OpenSearch, ElastiCache sözlüğü; kart 1–10): Düzeltildi, yeni terim tablosu Mimar gözüyle girişinde, kartlardan önce.
- `{ field: null }`, `$or`, sıralama ve sayfalama gibi eksikler bölüm 3'te kapatıldı.
- "primary key", "foreign key", "key-value database", "relevance", "search engine", "data warehouse", "cache", "driver", "cluster", "AZ", "TLS", "DNS", "port", "EC2", "subnet", "security group", "KMS", "CloudFormation", "CDN", "SDK", "Node.js", "HTTP", "mikroservis", "feature flag", "slug", "firmware", "payload", "dashboard": Gerekçe. Bu sayfanın kavramı değildir; workshop'un hedef okuyucusu (yazılım geliştirici) bunları bilir ve önceki iki sayfa (DynamoDB, Aurora) bunları aynı biçimde tanımsız kullanır. Kategoriye ait terimler (document, field, collection, _id, embedded document, array, reference, filtre, projection, index, transaction, aggregation pipeline, change stream, primary, replica, failover, read preference, shard key, BSON, ObjectId, endpoint) concept kartı ya da `dfn` ile tanımlıdır ve `clarity.py` "defined before used" kontrolünden geçer.
- "MongoDB replica set" (Başlarken): Gerekçe. Başlarken bölümü yol haritasıdır; terim A9'da tanımlanır ve başlıktaki kullanımı clarity kuralının izin verdiği "lead" kullanımıdır.
- "matchedCount": Gerekçe. A6 tablosunda parantez içinde anlamıyla ("hiçbir şey yazılmaz") geçer, hemen altındaki akış diyagramı açıklar.
- "shard": Düzeltildi. A9'daki `dfn` shard key'i tanımlar, flow-cap ve yeni "tek primary kaç yazma" kutusu shard'ın "verinin, her biri yazmayı ayrı karşılayan parçaları" olduğunu söyler.
- "point-in-time recovery" (DynamoDB) ve "point-in-time restore" (DocumentDB): Gerekçe. Aynı işin iki servisteki resmî adlarıdır; C2 restore'u tanımlar.
- "Seed", "production": Gerekçe. Seed, workshop'un veri yükleyicisidir ve M6'da "kopyaları Seed bir kez yazar" cümlesiyle rolü verilir; bütün Lale Market sayfalarında aynı ad.

## 3. Cevapsız "ya … olursa?" durumları

- `null` field: Düzeltildi (A2 tablosuna satır).
- `_id` 1 ve "1": Düzeltildi (A2 `_id` tablosuna satır).
- Gömülü kopyaların güncellenmesi: Düzeltildi (A3 "Aklına şu gelebilir" cevabı: updateMany ve change stream).
- `$or`: Düzeltildi (A4 tablosuna satır, öğretici sonuçla).
- Sıralama, sayfalama, büyük skip: Düzeltildi (A4 tablosuna satır).
- Büyük collection'a index eklemek, 64 sınırı: Düzeltildi (A5 "her field'a index" cevabı).
- updateMany yarıda hata: Düzeltildi (A6 tablosu: tekrar edilebilir yazma).
- Transaction 1 dakikayı aşarsa: Düzeltildi (A6 tablosu: iptal, geri alma, uygulama hatası).
- Bir kaydı iki kez işlemek: Düzeltildi (A8 tablosuna satır).
- Birden çok collection'da sıra, transaction'daki iki yazma: Gerekçe. AWS dokümanında DocumentDB için collection'lar arası sıra garantisi bulunamadı; kaynaksız bir cümle yazılmadı (reader-questions.md "Facts with sources").
- Failover anında yarıda kalan yazma: Düzeltildi (A9 tablosuna satır; retryable writes ile bağ).
- Bütün replica'lar çökerse: Gerekçe. A9 tablosunun ilk satırı ve C2 endpoint tablosu "replica yoksa primary" der; primary'nin bu durumda yük alması `secondaryPreferred`'ın tanımıdır.
- Desteklenmeyen operator'ı bulmak için araç: Gerekçe. Bir araç adı kaynakla doğrulanmadı; sayfa resmî yöntemi (desteklenen API listesi ile karşılaştırma ve hata dönüşü) yazar.
- Tek primary'nin yazma sınırı: Düzeltildi (A9'a yeni kutu: AWS sabit sayı vermez, yük testi ve CloudWatch; kartların kullandığı kaba ölçek açıkça "bu sayfanın kabulü" olarak yazıldı ve kart 6, 9, 4 gerekçeleri bu ölçekle hizalandı).
- Elastic cluster aday olarak: Gerekçe. Aday listesi domain-map'teki üç ürünle sınırlı (DynamoDB, Aurora, OpenSearch); elastic cluster DocumentDB'nin bir biçimidir ve kart 4'ün R2 gerekçesinde, M3'te ve M5'te seçeneğin kendisi olarak geçer. Yüksek yazma + document içi sorgu durumu kart 4'ün "Hangi koşul değişseydi" cümlesi ve M3'ün ilk satırıyla cevaplanır.
- Kampanya için replica zamanı: Gerekçe. M5 "dakikalar içinde" der (AWS: "regardless of the storage volume size"); kampanyadan önce ekleme, kart 1'in R2 gerekçesinin ("kampanyada replica eklenir") olağan okumasıdır.
- Kart 6 reddedilen çevrimdışı değişiklik: Gerekçe. Çakışma çözümü (birleştirme) uygulamanın iş kuralıdır; kart database'in verdiği aracı (sürüm koşulu ve yeniden okuma) puanlar, B3 simülasyonu yeniden okuma ve tekrar denemeyi gösterir.
- Kart 10 tüketici durursa 10 saniye: Düzeltildi (karar paragrafı: gereksinim o sürede karşılanmaz, alarm kurulur).
- Kart 10 paylaşılan cluster'da COLLSCAN: Gerekçe. B6'daki "COLLSCAN'leri replica'ya gönder" ve C2 endpoint tablosu bunu cevaplar.
- Kart 7 outbox geride kalırsa: Gerekçe. Kart kararı bu riski "potansiyel eksi" olarak yazar ("gecikirse 'siparişlerim' ekranı geride kalır"); R4 artık bu boru hattı için 3 puan kırıyor.
- Serverless ile instance-based geçiş: Gerekçe. Kaynakla doğrulanmış bir geçiş adımı bu çalışmada alınmadı; M5 iki seçeneği ve ne zaman seçileceğini verir.
- TTL silmesi change stream'de iki kez I/O: Gerekçe. B6 iki kalemi ayrı ayrı listeler ("TTL silmesi", "change stream açık"); toplam I/O ikisinin toplamıdır.
- Sıfır instance'lı cluster: Gerekçe. AWS'in "0–16 instances" ifadesi alıntıdır; sıfır instance'ta veri cluster volume'da durur, okuma ve yazma yapılamaz. Konu karar için önemsiz olduğu için sayfaya eklenmedi.
- Rapor replica'sı failover'da primary olursa: Gerekçe. Instance endpoint'in tanımı budur; C2 tablosu raporu instance endpoint'e yönlendirir ve failover tablosu (A9) kısa kesintiyi verir. Üretimde bu, failover tier'ı düşük bir replica seçerek çözülür; kaynakla doğrulanmış ayrıntı eklenmedi.
- BackupRetentionPeriod 1: Düzeltildi (C3: hafta sonu riski ve elle snapshot).

## 4. İkna etmeyen karar gerekçeleri

- Kart 1 R4 (boyutlandırma istenmiyor): Düzeltildi. DocumentDB R4 8 (2 puan kırıldı, boyutlandırma açıkça yazıldı). Toplam 46. "Bakım penceresi" ifadesi "schema değişikliği ve migration penceresi" oldu.
- Kart 2 index bedeli asimetrisi: Düzeltildi. DocumentDB R1 9 (index kurulana kadar COLLSCAN), R4 gerekçesi replica ve DCU izlemesi. DynamoDB R4 7 (veri katmanını yeniden yazmak, Aurora ile aynı gerekçe). Toplamlar DocumentDB 44, DynamoDB 43, Aurora 39.
- Kart 2 "MongoDB ile yazılmasaydı": Düzeltildi (kafa kafaya: o durumda DynamoDB bir puanla öne geçer ve karar R2'ye kalır).
- Kart 3 dört index: Düzeltildi (beş index sayıldı, yazar sorusu için `{ authors: 1, status: 1 }` eklendi).
- Kart 3 R3 sürüm geçmişi: Düzeltildi. Üç adayda da R3 9 (sürüm geçmişini uygulama tutar). Toplamlar 44, 41, 39.
- Kart 4 R3 9: Düzeltildi. R3 10; bedel R5'e taşındı (R5 4, index ve TTL I/O'su). Toplam 31 değişmedi.
- Kart 4 on-demand ani sıçrama: Gerekçe. DynamoDB on-demand davranışı DynamoDB sayfasının konusudur; bu kartın R2 gerekçesi DynamoDB sayfasıyla aynı düzeydedir.
- Kart 4 "en büyük instance 20.000'i taşır mı": Düzeltildi (A9'daki yeni kutu kartların ölçeğini yazar: on binlerce yazma tek primary'nin ötesinde).
- Kart 6 1.500 "sınıra yakın" ile kart 9 ve 4: Düzeltildi. Kart 6'nın "neden önemli" metni "rahat taşıdığı bir hacim, büyüme sınıra taşır" oldu; üç kart artık aynı ölçekte.
- Kart 7 "istenen davranış puan kaybettiriyor": Düzeltildi (puan, güncel ürün adıyla rapor için gereken `$lookup` için kırılıyor).
- Kart 7 "ayrı servis gereksinim mi": Düzeltildi (hikâyeye nedeni eklendi: writer'ı yormamak ve migration takviminden bağımsızlık; karar artık R1 ve R2'ye dayanıyor).
- Kart 7 boru hattı R4'te fark yaratmıyor: Düzeltildi. DocumentDB R4 7; Aurora R1 7 ("bu ürünü içeren siparişler" JOIN ve tekilleştirme). Toplamlar DocumentDB 42, Aurora 41, DynamoDB 41.
- Kart 8 karar R4 ve R5'e dayanıyor ama puanlar eşit: Düzeltildi. OpenSearch R4 7 ve R5 7 (ikinci sistem ve sabit maliyet), R3 8 (bu kartta R3 tercihli, kısa kesinti kabul); DocumentDB R2 8 (facet pipeline yükü ve yük testi). Toplamlar DocumentDB 42, OpenSearch 41, Aurora 36; karar metni R3, R4, R5 ile R1'i doğru adlandırıyor.
- Kart 8 R2 facet yükü: Düzeltildi (yukarıda, 2 puan kırıldı ve ölçüm şartı).
- Kart 9 zorunlu 2 ms: Düzeltildi. DynamoDB R2 6, DocumentDB R2 5 (ikisi de zorunlu sınırı her istekte tutmaz). Toplamlar ElastiCache 45, DynamoDB 40, DocumentDB 39.
- Kart 9 "ekip mevcut cluster dedi": Düzeltildi (hikâyeye eklendi).
- Kart 10 "üç puan, mevcut cluster": Düzeltildi. R3 9 (history büyümesi), toplam 46; kafa kafaya "iki puanlık fark, bir kısmı mevcut cluster'dan" diyor.
- Kart 10 R3 history büyümesi: Düzeltildi (yukarıda).
- R4'te ekip bilgisi ile operasyon yükü: Gerekçe. R1–R5 ortak ve değiştirilemez (SKILL.md kural 7); R4'ün sorusu ikisini birlikte sorar ("Kim işletecek, ekip hangi API'ı biliyor"). Kartlar gerekçede hangisinin puan kırdığını ayrı yazar.
- R3'ün hiç ayrışmaması: Gerekçe. Üç aday da çoklu AZ'de kalıcı yazan yönetilen servislerdir; R3 ancak bellek içi ya da arama index'i aday olduğunda ayrışır (kart 1, 4, 8, 9'da ayrışıyor).
- M7 simülasyonları kartın kopyası: Gerekçe. Bu, kural 6'nın amacıdır (kart ve simülasyon aynı veriden gelir ve hiç ayrışmaz). Koşul değiştiren simülasyon sahibin onayı gereken yeni bir blok olurdu.

## 5. Sayfa içi çelişkiler

- Renk sözleşmesi: Düzeltildi (A2: renkler document anatomileri içindir; A9 ve B5 kutuları adla anılır). Resmî AWS görsellerinin renkleri kendi altyazılarında açıklandı.
- "koleksiyonlar arası kural" ve "koleksiyon" yazımı: Düzeltildi (A3 M3 satırının adını kullanıyor; simülasyon metinlerinde "collection").
- A7 eşitlik sırası ile B4: Düzeltildi (yanlış cümle kaldırıldı).
- "yeni" ortalaması 2346.0: Gerekçe, çelişki yok. Öğretici fiyatlar 3884,10 + 84,61 + 2721,65 + 2693,65 = 9384,01; 9384,01 / 4 = 2346,00. Raporun toplamı (9383,01) bir toplama hatasıdır.
- 8.0.0 ile 8.0.2: Düzeltildi (A10 major ve minor).
- İç içe 200 seviye MongoDB'de: Düzeltildi. MongoDB'nin sınırı 100 seviyedir (MongoDB Limits and Thresholds: "Nested Depth for BSON Documents"); A2 ve matris düzeltildi.
- Shard key görseli ile elastic görseli: Düzeltildi (A9 altyazısı görselin basitleştirildiğini ve yönlendiriciyi söylüyor; "primary" iddiası kaldırıldı).
- Shard görselindeki fazla adlar: Düzeltildi (altyazı adların örnek olduğunu söylüyor).
- "Index'li yol yine 40": Düzeltildi (B2 clause satırı: limit 48'e kadar dönen sayı, COLLSCAN 200.000).
- Q1 dört field, simülasyon üç field: Düzeltildi (B2 metni simülasyonun daha kısa bir projection kullandığını söylüyor).
- Canlı başlıklarda M2, M5 yolları: Düzeltildi (yollar kaldırıldı, "Engine App üzerinden").
- M2 girişindeki "ikisi birlikte" listesi: Düzeltildi (kart 1, 5, 7, 8, 9 ve kart 8'in koşulu).
- Kart 1 "kart 8 bu ikiliyi puanlar": Düzeltildi.
- Kart 4 "gücü R1'de": Düzeltildi.
- Kart 6 "R1 ve R4": Düzeltildi ("R1 ve R2").
- Kart 7 "R4 ve R5": Düzeltildi (R4 artık farklı ve metin hangi adayın önde olduğunu söylüyor).
- Kart 8 eşit R4/R5: Düzeltildi (bölüm 4).
- Kart 9 hikâyede cluster yok: Düzeltildi.
- Kart 9 DynamoDB R2 10 ile 2 ms: Düzeltildi (bölüm 4).
- Kart 6, 9, 4 yazma ölçeği: Düzeltildi (bölüm 4 ve A9 kutusu).
- M5 DynamoDB "document database": Düzeltildi ("key-value database; value'lar JSON olabilir").
- C1 yedi iş ile C2 tablosu: Düzeltildi ("Şifreleme ve erişim" satırı eklendi; "API ve driver'lar" iki tarafta aynı olanı gösteren ek satırdır).
- AZ listesi: Düzeltildi (C3: volume üç AZ'de, instance'lar 1b ve 1c'de).

## 6. Altyazılar

- B-tree noktaları: Gerekçe. Altyazı kökten yaprağa yolu ve category_1_rating_-1 bağını söyler; noktaların ayrıntısı (işaretçi) B2'deki FETCH cümlesiyle verilir.
- Shard key görseli: Düzeltildi.
- A9 rol diyagramı: Düzeltildi.
- B5 TTL diyagramı: Düzeltildi.
- Cluster görseli (altı kopya, durum bildirimi): Düzeltildi.
- Endpoints görseli (kareler ve oklar): Düzeltildi.
- Elastic görseli (kod parçaları, shard key): Düzeltildi.
- Simülasyon lejantı ve ✓: Düzeltildi (M7 girişi).
- A1 iki yol diyagramı: Gerekçe. Raporun kendisi "altyazı iyi" diyor; flow-cap "fark kaç yere bakıldığındadır" ile bakılacak şeyi söylüyor.

## Son soru

Okuyucunun beş eksiğinden 1 (yazma sınırı), 2 (puan tutarsızlıkları) ve 5'in terim kısmı (JSONB, GIN, MVCC terim tablosunda) düzeltildi. 3 (elastic cluster aday değil) ve 4 (sayısal maliyet karşılaştırması) gerekçeyle kapatıldı: aday listesi domain-map'te sabittir ve iki servisin aylık fiyatı bölgeye ve iş yüküne göre değişir; sayfa AWS'in kendi fiyat örneğini kaynağıyla verir (B6) ve kartlar maliyet modelinin uyumunu puanlar.
