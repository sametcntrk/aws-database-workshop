# Okuyucu simülasyonu: docdb.tr.html (model 2)

Tarih: 2026-10-30

Okuyucu profili: DocumentDB ya da MongoDB'yi hiç kullanmamış biri. Kaynak: /tmp/preview_docdb/tr.txt, /tmp/preview_docdb/tr.html ve sayfanın beş görseli (canlı sunucudan). Hiçbir sayfa dosyası değiştirilmedi. Kartlardaki bütün toplamlar, R1 ara toplamları ve "Fark" sütunu elle yeniden hesaplandı: on kartın hepsinde sayılar tablolarla uyumlu (bulgu yok).

## 1. Anlamadığım cümleler

**B1**
- bölüm: model (A2), "bütün durumlar: bir collection'daki document'ların şekli" tablosu
- alıntı: "Bir kural tanımlandı (örneğin "price zorunlu ve sayı") — Bazı ürünlerde mümkündür: collection'a bir doğrulama şeması (JSON Schema) eklenir"
- sorun: "Bazı ürünlerde" hangi ürünler? DocumentDB'de var mı, yok mu? Sayfa sonra ($jsonSchema, kart 1 kararı) DocumentDB'de var diye kullanıyor, ama burada okuyucu bunu bilemiyor.
- beklenen: "MongoDB'de ve DocumentDB'de mümkündür" gibi ürün adlarıyla bir cümle.

**B2**
- bölüm: index (A5), "Her field'a index koysam her soru hızlı olmaz mı?" kutusu
- alıntı: "64 index sınırına yaklaşılıyorsa sorular gözden geçirilir ... Index'ler bellek ve disk tutar ve bir collection'da sınırlı sayıda index olabilir (DocumentDB'de 64)."
- sorun: 64 sınırı tanıtılmadan önce kullanılıyor; paragrafın cümle sırası ters. Ayrıca aynı paragrafta "primary'nin CPU'su" geçiyor, primary A9'da tanımlanıyor.
- beklenen: önce sınır, sonra sınıra yaklaşınca ne yapılacağı; primary yerine "database sunucusu" ya da A9'a bir bağlantı.

**B3**
- bölüm: index (A5), "Index'i kim seçer?" kutusu
- alıntı: "Lale Market'in kategori sayfasındaki "Collection scan" deneyi tam tersini yapar: aynı listeyi $natural ipucuyla ... index'siz getirir"
- sorun: "deney" nedir, nerede, nasıl açılır, bilmiyorum. Mağazanın bir sayfasında bir düğme mi? C3'te ve "Daha derine in"de yine anılıyor ama hiçbir yerde nasıl kullanılacağı söylenmiyor.
- beklenen: ilk geçtiği yerde tek cümle: "Kitap kategori sayfasında X düğmesi index'i kapatır ve iki planı yan yana gösterir".

**B4**
- bölüm: service (C2)
- alıntı: "bir cluster 0 ile 16 instance arası olabilir: bir primary ve en fazla 15 replica"
- sorun: 0 instance'lı cluster ne demek, kim okur, kim yazar? "Bir primary ve en fazla 15 replica" ile 0 birbiriyle çelişiyor gibi görünüyor.
- beklenen: "instance'ı olmayan bir cluster sadece storage'tır ve sorgu alamaz" gibi bir açıklama ya da 0'ın çıkarılması.

**B5**
- bölüm: decide (M7), giriş paragrafı ve her simülasyonun altındaki renk açıklaması
- alıntı: "bu beş simülasyonda yeşil önde olan adayı, "sonuçta yeni" en uygun servisi gösterir." / açıklama: "okunuyor eşleşti okundu ve atlandı kilitli sonuçta yeni reddedildi ya da yanlış"
- sorun: Cümleyi iki kez okudum, anlamadım: yeşil hangisi, "sonuçta yeni" hangisi? Puanlama simülasyonunda "kilitli" ya da "okundu ve atlandı" ne demek?
- beklenen: karar simülasyonlarına özel, sadece kullanılan renklerin açıklaması ("yeşil: şu adımda önde olan aday; mor: en uygun servis").

**B6**
- bölüm: usecases, uc-profiles, DynamoDB ile kafa kafaya
- alıntı: "DynamoDB sayfasının aynı kartında DynamoDB kazanır." ... "Hangi koşul değişseydi DynamoDB seçilirdi: uygulama sıfırdan yazılsaydı ... DynamoDB sayfasının kart 2'si tam bu durumdur."
- sorun: "Aynı kart" ise iş yükü aynı mı? Aynı iş yükünde iki sayfa iki farklı kazanan verirse puanlama güvenilmez görünür. İkinci cümleden kartın aslında farklı bir hikâye olduğunu anlıyorum, ama ilk cümle "aynı" diyor.
- beklenen: "DynamoDB sayfasının profil kartı farklı bir hikâyedir (sıfırdan uygulama, 100.000 okuma) ve orada DynamoDB kazanır" gibi açık bir cümle.

## 2. Anlamını bilmeden önce karşılaştığım terimler

**B7**
- bölüm: summary (A10), özellik × ürün matrisi
- alıntı: "✗ Key dışı soru Scan ve filtre ya da bir GSI ister", "½ GSI ve LSI", "Change streams (oplog'dan)", "Sunucuda özet: sayılar, ortalamalar, facet'ler" (M1)
- sorun: Scan, GSI, LSI, oplog ve facet A10'da ve M1'de kullanılıyor. Tanımları ancak M2'deki "kartlarda geçen servis terimleri" tablosunda geliyor (oplog ve LSI hiç tanımlanmıyor). Matrisin DynamoDB sütununu okurken bu terimleri bilmiyordum.
- beklenen: terimlerin A10'da ilk geçtiği yerde kısa bir parantez, ya da servis terimleri tablosunun A10'dan önce gelmesi.

**B8**
- bölüm: nesting (A3), query (A4), index (A5), replicas (A9)
- alıntı: "bir updateMany ; A6'ya göre ..." (A3); "relevance search engine'in işidir" (A4); "Planner COLLSCAN'i seçebilir" (A5 tablosu, planner 233. satırda tanımlanıyor); "Geri dönüş sadece yedekten (point-in-time restore)" (A9; C2'de tanımlanıyor)
- sorun: updateMany, relevance, planner ve point-in-time restore tanımlanmadan kullanılıyor. Relevance hiçbir yerde tanımlanmıyor.
- beklenen: ilk geçtiği yerde bir yan cümle ("relevance: sonucun aranan kelimeye ne kadar uyduğuna göre sıralanması").

**B9**
- bölüm: usecases, kart gerekçeleri
- alıntı: "hot partition" (uc-events, DynamoDB R1.3), "ölçeklenme sırasında DDL komutları çalışmaz" (uc-events, elastic R2), "if_seq_no", "analyzer" (uc-catalog, OpenSearch), "DAX", "Working set" (uc-sessions), "bitmap" (uc-search, Aurora), "logical replication" (uc-flags, Aurora), "Multi-AZ" (birçok kartın R5'i), "okuma modeli" (uc-orders)
- sorun: Bu terimlerin hiçbiri servis terimleri tablosunda yok. Gerekçeyi okuyorum ama puanın neden kırıldığını anlayamıyorum (örneğin DDL'in çalışmaması ne zaman önemli?).
- beklenen: terimleri servis terimleri tablosuna eklemek ya da gerekçede düz dille söylemek ("index ekleme gibi şema komutları").

**B10**
- bölüm: lalemarket-arch (M6), names (B1), ttl (B5)
- alıntı: "Bu kopyaları Lale Market'te Seed bir kez yazar"; "color ile attributes.renk aynı bilgiyi iki yerde taşır: Seed'in eski sürümünden kalan bir kopya"
- sorun: "Seed" nedir (bir script mi, bir servis mi)? Sayfada hiç tanımlanmıyor. Aynı biçimde "Neptune'daki graph" (model, A2) hiç açıklanmıyor.
- beklenen: "Seed: workshop verisini bir kez yükleyen script" gibi bir yan cümle.

## 3. Cevabını bulamadığım "ya şöyle olursa?" soruları

**B11**
- bölüm: usecases, uc-sync
- alıntı: "Cihaz çevrimdışıyken değişiklik yapar, bağlanınca gönderir; sunucu sürüm numarasına bakarak eski bir yazmayı reddeder"
- sorun: Saatlerce çevrimdışı kalan cihazın değişikliği reddedilirse kullanıcının yaptığı iş kaybolur mu? "B listeyi yeniden okur ve tekrar dener" tek bir öğe için anlaşılır, ama birçok çevrimdışı değişiklik birleştirilir mi? Sayfa çakışmanın sadece "reddedildi" kısmını gösteriyor.
- beklenen: birleştirme stratejisi için bir cümle (öğe bazlı koşul, yeniden okuyup değişikliği tekrar uygulama) ya da "bu kartın kapsamı dışında" notu.

**B12**
- bölüm: usecases, uc-orders
- alıntı: "her sipariş tek bir document, checkout commit'inden sonra bir event ile yazılır, her durum değişikliği history array'ine eklenir" / karar: "yazmayı tekrar edilebilir yaparız (_id = sipariş id'si, upsert)"
- sorun: Upsert, tekrar gelen event'i çözüyor. Ama event'ler sırasız gelirse ne olur ("kargoda" event'i "hazırlanıyor"dan önce gelirse)? Status yanlış değerde kalır mı?
- beklenen: sıra için bir koşul (örneğin event sıra numarası filtrede) ya da kısıtın açıkça yazılması.

**B13**
- bölüm: service (C2) ile usecases (uc-devices, uc-flags, uc-cms)
- alıntı: C2: "tek instance'lı bir cluster ile üç instance'lı bir cluster aynı dayanıklılıktadır. Instance sayısı kullanılabilirliği değiştirir." / uc-devices R5: "bu çok küçük yükte de Multi-AZ için iki instance çalışır" / karar: "serverless (0,5 DCU'dan başlayan aralık) ya da geliştirme ortamında tek instance ile azaltırız"
- sorun: Production'da tek instance kabul edilebilir mi (failover dakikalar sürer, A9)? Serverless de iki instance ister mi? uc-devices'ta serverless R5 gerekçesinde anılıyor ama puan hâlâ iki instance'a göre kırılıyor. Hangisi geçerli?
- beklenen: küçük iş yükleri için tek instance / serverless / iki instance seçeneklerinin kullanılabilirlik ve maliyet farkı, bir tabloda.

**B14**
- bölüm: aws (M5), usecases (uc-events)
- alıntı: "shard key tek bir field'dır, hash ile çalışır ve sonradan değişmez"
- sorun: Shard key yanlış seçilirse ne olur (bir kullanıcının çok fazla event'i, sıcak bir shard)? Sonradan değişmiyorsa çıkış yolu nedir (yeni cluster ve veri taşıma mı)? Shard key'i olmayan bir sorunun maliyeti (bütün shard'lar) A9'da bir satırda geçiyor, kartta hesaba katılmıyor.
- beklenen: yanlış shard key durumu için bir satır ve çıkış yolu.

**B15**
- bölüm: summary (A10), architect
- alıntı: "Bir geçişten önce uygulamanın kullandığı operator listesi bu iki sayfayla karşılaştırılır." / "Aynı MongoDB API'si başka bir üreticide (örneğin MongoDB Atlas) başka bir fiyat ve operasyon modeliyle gelir."
- sorun: Var olan bir MongoDB'den DocumentDB'ye verinin nasıl taşınacağı (kesinti, araç) hiç söylenmiyor. MongoDB Atlas'ın ne zaman daha iyi olacağı da yok; kartların çoğunda "ekip MongoDB driver'ı biliyor" bir puan nedeni, okuyucunun aklına hemen Atlas geliyor.
- beklenen: geçiş için bir cümle ve bir kaynak; Atlas'ın neden bu sayfada aday olmadığına dair bir cümle.

## 4. İkna etmeyen karar gerekçeleri

**B16**
- bölüm: architect, "Neden R1 en ağır..." kutusu ve puan ölçeği paragrafı
- alıntı: "Bir document engine'inin ... bütün yazmaları tek bir primary'den geçirmesi, engine hangi bulutta ya da hangi makinede çalışırsa çalışsın aynıdır." / "yazmaların tek primary'den geçmesinden geliyorsa R2'de."
- sorun: İlk cümle tek primary'yi engine'in doğası, yani R1 sayıyor. İkinci cümle onu R2'ye yazıyor. Aynı engine elastic cluster'da shard'larla yazıyor; o zaman tek primary engine değil servis paketlemesidir. Okuyucu kuralın hangisi olduğunu bilemiyor.
- beklenen: "tek primary instance-based cluster'ın servis tasarımıdır, bu yüzden R2'dedir" ve ilk cümleden tek primary'nin çıkarılması.
- mimara soru: Tek primary engine özelliği mi, servis özelliği mi? Engine ise neden kartlarda hiçbir R1 alt maddesinde görünmüyor?

**B17**
- bölüm: usecases, uc-events (R1.5) ve ttl (B5)
- alıntı: R1.5: "TTL silmesi "best effort"tür ve her silme bir I/O'dur" / DynamoDB R1.5: "TTL süresi dolan value'yu yazma kapasitesi harcamadan siler" / karar: "TTL ücretsizdir" / B5: "M2'deki event log kartının R1 ve R5 puanları bu iki cümleden gelir."
- sorun: I/O ücreti ve "yazma kapasitesi harcamamak" fiyatlandırmadır, yani servis paketlemesi. Sayfanın kendi kuralı ("I/O ücreti ... R2–R5'e yazılır ve R1'de sayılmaz") bunu R1'de yasaklıyor. Aynı I/O R5'te de sayılıyor ("TTL silmesinin I/O'su ... faturanın büyük kalemidir"), yani aynı eksik iki kez kırılıyor. DynamoDB'nin R1.5'teki 1,2 puanlık önü, kartın R1 kıyasını taşıyor.
- beklenen: R1.5'te yalnız engine davranışı (silme zamanı garanti değil, silmeler yazmalarla yarışır); I/O ve "kapasite harcamaz" R5'te.
- mimara soru: I/O R1'den çıkınca DynamoDB ile elastic cluster arasındaki R1 farkı ne kadar kalır?

**B18**
- bölüm: usecases, uc-events, DocumentDB (instance-based) gerekçesi
- alıntı: R2: "8 puan kırıldı: bütün yazmalar tek primary'den geçer" / R4: "7 puan kırıldı: en büyük instance sınıfında bile tepe gecesi için büyütme, izleme ve sonra elastic cluster'a geçiş" / R5: "5 puan kırıldı: en büyük instance bütün ay çalışır" / kafa kafaya: "R4 ve R5 de aynı nedenden geride kalır"
- sorun: Sayfanın kuralı "Bir eksik yalnız bir satırda sayılır". Burada tek primary eksiği üç satırda kırılıyor ve paragraf bunu açıkça "aynı nedenden" diye söylüyor. Aynı mekanizma uc-sessions'ta (saniyede 5.000 yazma, primary büyütülür) R4'te sadece 1 puan kırıyor.
- beklenen: tek primary bir kez R2'de; R4 ve R5 sadece kendi bağımsız nedenleriyle. Kartlar arasında aynı mekanizma için aynı kırılım.
- mimara soru: Bu üçlü sayım çıkarılınca DocumentDB 63,2'den kaça çıkar ve sıra değişir mi?

**B19**
- bölüm: usecases, uc-sync, elastic cluster gerekçesi
- alıntı: R1.3: "9 → 10,8 Engine change stream verir (Ö7). 1 puan kırıldı: tutulma süresi varsayılan üç saattir." / R4: "7 puan kırıldı: elastic cluster change stream'i desteklemez"
- sorun: Kartın kendi ağırlık gerekçesi "değişikliğin cihazlara akması (YD 12) ... bu uygulamanın kalbidir" diyor. Elastic cluster bu satırda 9/10 alıyor, ama satırın istediğini yapamıyor. Kural gereği eksik R2–R5'e yazılmış (doğru), ama "operasyon ve ekip" satırına yazılması tuhaf: eksik bir özellik bir ekip sorunu değildir. Okuyucu tabloya bakınca elastic cluster'ın yayın satırında güçlü olduğunu sanıyor.
- beklenen: R1.3 gerekçesinde bir not ("engine verir; elastic cluster servisi sunmaz, bu eksik R4'te sayıldı") ve eksiğin neden R4'te sayıldığının açıklaması (R2 ya da R3 değil).

**B20**
- bölüm: usecases, uc-sessions, DocumentDB gerekçesi
- alıntı: R1.2: "her yenileme TTL index'ini de günceller" / R1.4: "1 puan kırıldı: her yenileme document'ı ve TTL index'ini birlikte yazar" / R5: "saniyede 5.000 yenileme ve TTL silmeleri sürekli I/O'dur"
- sorun: Her yenilemede TTL index'inin yazılması iki R1 satırında ve R5'te sayılıyor.
- beklenen: bir kez (R1.4 ya da R5).

**B21**
- bölüm: usecases, uc-search ve signals (M1, Ö4 ve Ö6)
- alıntı: Ö4: "Onlarca filtre field'ının her birleşimi ve facet sayıları gerekiyorsa search engine her field'ı index'ler." / Ö6: "Facet sayıları her sayfada ve kampanyada binlerce kez gerekiyorsa search engine'in aggregation'ı." / uc-search: "filtre field'ları 20 tane" ... "Hangi koşul değişseydi OpenSearch seçilirdi: ... filtre field'ları 50'yi geçseydi"
- sorun: Kartın iş yükü (20 filtre field'ı, her sayfada facet, saniyede 1.200–5.000) M1'in "alternatif daha iyi" cümleleriyle tam olarak eşleşiyor, ama DocumentDB kazanıyor. OpenSearch R1'i 40,8 / 30,4 ile, R2'yi 19,8 / 15,4 ile alıyor; DocumentDB sadece "ekip bilmiyor" (R4) ve "ek servis" (R5) ile 0,8 puan önde. Hikâye metin aramasının bir sonraki çeyrekte geleceğini söylüyor, yani OpenSearch zaten gelecek. Gerçekten en uygun servis bu mu?
- beklenen: M1 cümleleri ile kartın uyumlu olması (eşik "onlarca" mı, "50" mi?), ve kararda "bu seçim geçicidir, bir çeyrek sonra OpenSearch eklenir" açıkça.
- mimara soru: Bir çeyrek sonra OpenSearch zaten kurulacaksa, bugün DocumentDB'de facet pipeline'ları ve compound index'ler kurmak boşa giden iş değil mi? R4'ü bugünkü ekip bilgisine göre puanlamak doğru mu?

**B22**
- bölüm: usecases, uc-flags
- alıntı: "Bu kartın dışında bir seçenek daha vardır: AWS AppConfig ... flag'lerin içine göre sorgu gerekmiyorsa bir database yerine o düşünülür."
- sorun: Hikâyede flag'lerin içine göre bir sorgu yok: EY satırı "Flag adı ile tek okuma ve "bütün flag'ler" tek sorgu". Hikâyenin istekleri (aşamalı yayılma, 10 saniyede yayılma, geri alma, denetim geçmişi) AppConfig'in amacı. Sayfanın kendi koşuluna göre AppConfig düşünülmeli, ama kartta aday değil.
- beklenen: AppConfig'in neden aday olmadığına dair açık bir neden ya da üçüncü aday olarak puanlanması.
- mimara soru: Bu hikâyede AppConfig'i eleyen tek gereksinim hangisi?

**B23**
- bölüm: usecases, uc-flags (DocumentDB ve DynamoDB R1.2) ile nesting (A3)
- alıntı: DocumentDB R1.2: "$push: { history } tek atomik yazmadır ... Puan kırılmadı." / DynamoDB R1.2: "1 puan kırıldı: geçmiş list'i büyüdükçe value büyür" / A3: "Sınırsız büyüyen array — Yapamaz"
- sorun: Her flag değişikliği history array'ine ekleniyor ve geçmiş "denetim için saklanmalı". Bu, A3'ün "sınırsız büyüyen array gömülmez" kuralına aykırı. DynamoDB büyüme için kırılıyor, DocumentDB kırılmıyor (16 MiB, 400 KB'tan büyük, ama sınır yine var).
- beklenen: iki adayda aynı mekanizma için kırılım, ya da tasarımın "son N değişiklik gömülü, hepsi ayrı collection'da" (A3'ün beşinci satırı) olarak yazılması.

**B24**
- bölüm: usecases, uc-orders
- alıntı: "Ekip bu okuma modelini ayrı bir serviste tutmak istiyor" / Aurora R2: "okuma modelinin yazmaları checkout writer'ından geçer" / Aurora R4: "story'nin istediği bağımsız migration takvimi ve writer'dan ayrılık kaybolur"
- sorun: (a) Kararın sonucu hikâyenin içine yazılmış: "ayrı bir servis" isteniyor, sonra Aurora ayrı olmadığı için kırılıyor. (b) "Writer'dan ayrılık" R2'de ve R4'te iki kez sayılıyor. (c) Aurora'nın bir kazancı hiç sayılmıyor: okuma modeli Aurora'da ise checkout aynı transaction'da yazabilir; tüketici yok, iki kopya yok, sırasız event yok. DocumentDB'nin eksik listesindeki "iki kopya vardır ... tüketiciyi biz işletiriz" tam olarak bu.
- beklenen: Aurora'nın "tüketici gerekmez" kazancı bir satırda; aynı eksik tek satırda.
- mimara soru: Ayrı bir Aurora schema'sı ya da bir materialized view neden yetmiyor? "Ayrı servis" isteği hangi ölçülmüş sorundan geliyor?

**B25**
- bölüm: usecases, uc-orders, DynamoDB R1.1 ile nesting (A3)
- alıntı: DynamoDB R1.1: "2 puan kırıldı: geçmiş list'i büyüdükçe value büyür; uzun geçmiş ayrı value'lara bölünür." / A3: "Durum geçmişi en fazla birkaç eleman büyür, bu yüzden gömülebilir."
- sorun: Sayfa geçmişin sınırlı olduğunu söylüyor (alındı, hazırlanıyor, kargoda, teslim). Dört elemanlı bir liste 400 KB sınırına yaklaşmaz. Kırılım uydurma bir zayıflığa dayanıyor.
- beklenen: kırılmamış puan ya da gerçek bir neden.

**B26**
- bölüm: usecases, uc-profiles, DynamoDB R1.1
- alıntı: "8 → 9,6 ... 2 puan kırıldı: profilin içine göre haftada değişen sorular için ya her soruya bir ikinci index kurulur ya da Scan"
- sorun: Pazarlamanın soruları "İstanbul'da oturan" (adres listesinin içi) ve "iOS cihazı olup" (cihaz listesinin içi). İkisi de list elemanı; sayfa "list elemanına index kurulamaz" diyor. Aynı mekanizma uc-cms'te 4, uc-devices'ta 6, uc-orders'ta 5 puan kırıyor. Burada sadece 2 kırılıyor ve DynamoDB'yi yakın yarışa sokan farkın bir parçası bu.
- beklenen: aynı mekanizmaya aynı kırılım (en az 4), ya da neden daha az kırıldığının açıklaması.

**B27**
- bölüm: usecases, uc-cms, R1.4 YD (DocumentDB ve DynamoDB)
- alıntı: DocumentDB: "6 → 4,8 ... 4 puan kırıldı: engine'de makale sürümü yoktur; uygulama ... article_versions collection'ına kopyalar." / DynamoDB: "7 → 5,6 ... 3 puan kırıldı: sürüm kopyasını uygulama yazar ve Streams kayıtları 24 saat tutulur."
- sorun: İki adayda da sürümü uygulama yazıyor; DocumentDB'nin change stream'i 7 güne kadar, DynamoDB'ninki 24 saat. Yine de DynamoDB daha yüksek puan alıyor. Ayrıca DynamoDB Streams 24 saat aynı kartta 3 puan, uc-sync ve uc-flags'te 1 puan kırıyor.
- beklenen: iki adaya eşit ya da DocumentDB'ye daha yüksek puan; "24 saat" için kartlar arasında aynı kırılım.

**B28**
- bölüm: usecases, DocumentDB'nin R4 ve R5 satırları (uc-catalog, uc-profiles, uc-cms, uc-devices)
- alıntı: R5 "Multi-AZ için en az iki instance": uc-catalog "2 puan kırıldı" (kampanya replica'ları da ekli), uc-cms "3 puan kırıldı", uc-devices "4 puan kırıldı". R4 "instance sınıfını ve replica sayısını ekip seçer": uc-profiles "1 puan kırıldı", uc-cms ve uc-devices "2 puan kırıldı ... seçer ve izler".
- sorun: Aynı mekanizma kartlara göre farklı kırılıyor; uc-catalog'da daha fazla neden var ama daha az kırılım. Puan ölçeği "her satırda ve her kartta aynı" diyor.
- beklenen: aynı nedene aynı kırılım, ya da farkı açıklayan bir cümle (örneğin "bu kartta R5 en düşük sabit maliyeti istiyor").

**B29**
- bölüm: usecases, uc-catalog, DocumentDB R4
- alıntı: "Lale Market'te katalog zaten bu cluster'dadır; yedek, yama ve failover yönetilir."
- sorun: Kart kataloğun nerede duracağına karar veriyor; "zaten orada" bir gerekçe olamaz (döngüsel). Aurora R4 de "Aurora Lale Market'te siparişler için zaten çalışır" alıyor; ikisi de 8.
- beklenen: R4 gerekçesi ekip ve operasyon üzerinden; "zaten orada" çıkarılmalı.

**B30**
- bölüm: usecases, uc-sessions, gereksinimler
- alıntı: hikâye: "Oturum okuması her isteğin önündedir: 1 ms gecikme her sayfaya eklenir." / R1.3: "Okuma 2 ms'nin altında dönmeli"
- sorun: Hedef 1 ms mi, 2 ms mi? DynamoDB'nin R1.3'ü (tek haneli milisaniye) bu sayıya göre kırılıyor.
- beklenen: tek bir sayı.

**B31**
- bölüm: usecases, uc-events
- alıntı: "analiz ekibi günlük kopyayı data warehouse'a alır" / A8: "Olayların günlerce saklanması ve birçok tüketici tarafından baştan okunması gerekiyorsa bir akış platformu (Kinesis, MSK) kullanılır."
- sorun: Saniyede 80.000 eklenen, hiç güncellenmeyen, 30 gün tutulan ve warehouse'a giden clickstream için bir akış platformu (Kinesis + S3) okuyucunun ilk sorusudur. Kartta aday değil ve neden aday olmadığı yazılmıyor.
- beklenen: "son 100 event" sorusunun bir akış platformunda neden zor olduğunu söyleyen bir cümle.

## 5. Sayfanın iki yerinin farklı söylediği şeyler

**B32**
- bölüm: goal
- alıntı: "35 dakika"
- sorun: Sayfa yaklaşık 35.000 kelime, on kart ve on bir simülasyon. Okuması saatler sürüyor. 35 dakika ile metin uyumlu değil.
- beklenen: gerçekçi bir süre ya da "Bölüm A 35 dakika" gibi bölüm başına süreler.

**B33**
- bölüm: replicas (A9), "Tek bir primary saniyede kaç yazma taşır?" kutusu
- alıntı: "saniyede birkaç yüz ile 1.500 yazma orta bir instance için rahattır (kart 6, 7), birkaç bin yazma büyük bir instance ister (kart 9)"
- sorun: Kart 7'de yazma "günde 5.000 sipariş (saniyede birkaç yazma)", birkaç yüz değil. Kart 9'da 5.000 yazma "büyük bir instance" ile anlatılıyor, ama kartın R2'si 4 ve R4 sadece 1 puan kırıyor; kart 4'te aynı büyütme R4'te 7 puan kırıyor.
- beklenen: doğru kart örnekleri (örneğin kart 2: 150, kart 6: 1.500) ve kart 4 ile kart 9 arasında aynı mantık.

**B34**
- bölüm: summary (A10), matris ve uyumluluk tablosu
- alıntı: matris Ö6: "Çoğu aşama var; bazıları sadece 8.0'da" / tablo: "$graphLookup ve $facet sadece 8.0.2 ve sonrası" / names ve lalemarket: Lale Market "8.0.0"
- sorun: Matris "8.0'da" diyor, Lale Market 8.0'da ama bu aşamalar yok. Okuyucu 8.0 ile 8.0.2'yi aynı sanıyor.
- beklenen: matriste de "8.0.2 ve sonrası".

**B35**
- bölüm: usecases (servis terimleri tablosu), architect, aws (M5)
- alıntı: terimler: "transaction, change stream, point-in-time restore ve unique index sunmaz" / architect: "transaction, change stream ve point-in-time restore sunmaz" / M5: "ACID transaction'lar, change stream, point-in-time restore, unique, partial ve text index'leri"
- sorun: Elastic cluster'ın eksik listesi üç yerde üç farklı uzunlukta.
- beklenen: bir yerde tam liste, diğerlerinde ona bağlantı.

## 6. Neye bakacağımı söylemeyen görseller ve diyagramlar

**B36**
- bölüm: replicas (A9), sharding görseli
- alıntı: "görsel hash değerlerini göstermez ve shard'lardaki adlar örnektir (bazıları üstteki listede yok). Görsel basitleştirilmiştir: gerçekte isteği bir yönlendirici doğru shard'a verir"
- sorun: Görsel bir çalışan veri setidir (Sam, Gustav...), Lale Market değil. Shard'lardaki adların yarısı (Priya, Vijay, Charl...) listede yok, ve dağıtımı "Application" kutusu yapıyor. Altyazı görselin üç hatasını sayıyor; bu durumda neye bakmam gerektiğini bulamıyorum: hangi document hangi shard'a gitti?
- beklenen: Lale Market verisiyle (örneğin user_id'li event'ler) ve doğru bir router ile çizilmiş bir diyagram, ya da altyazının tek bir şeye işaret etmesi ("her shard ayrı bir yazma noktasıdır").

**B37**
- bölüm: service (C2), endpoint görseli
- alıntı: "Altta compute'tan ayrı, dağıtık storage volume: aynı renkli kareler aynı veri bloğunun üç bölümdeki kopyalarıdır."
- sorun: Görselde her renk her bölümde bir kez var, yani üç kopya. Hemen önceki görsel ve metin "üç AZ × 2 = altı kopya" diyor. İki görsel art arda farklı kopya sayısı gösteriyor ve altyazı bu farkı açıklamıyor.
- beklenen: "bu görsel kopyaları basitleştirir; gerçekte her AZ'de iki kopya vardır (önceki görsel)" gibi bir cümle.

**B38**
- bölüm: decide (M7) ile reads (B2), updates (B3), aggregate (B4)
- alıntı: her simülasyonun altında: "okunuyor eşleşti okundu ve atlandı kilitli sonuçta yeni reddedildi ya da yanlış"
- sorun: Aynı altı renkli açıklama her simülasyonda var; hangi renklerin o simülasyonda kullanıldığını söylemiyor. Karar simülasyonlarında "kilitli" ve "okundu ve atlandı" anlamsız (B5 ile bağlantılı).
- beklenen: her simülasyonun altında sadece kullanılan renkler, ya da giriş cümlesinde "bu simülasyonda şu üç renge bak".

## Son cevap: Bir meslektaşıma, kazanan ya da kazanmaya yakın her servis yerine DocumentDB'yi ne zaman seçeceğimi anlatabilir miyim?

**DynamoDB (kart 2, 4, 10; kart 3, 5, 6, 7'de ikinci):** Evet, büyük ölçüde. DocumentDB'yi şu durumlarda seçerim: sorular document'ın içine göre (iç içe field, list elemanı) ve önceden bilinmiyorsa; değişiklik bir array'in içindeyse ve eleman değeriyle bulunmalıysa (arrayFilters, DynamoDB'de sıra ile); ekibin kodu MongoDB driver'ıyla yazılmışsa ve yazma tek primary'nin sınırındaysa. DynamoDB'yi şu durumlarda seçerim: yazma on binlerse, erişim hep bilinen bir key iseyse, istek başına ödeme isteniyorsa ya da uygulama sıfırdan yazılıyorsa. Eksik: kart 2'de list elemanı sorusunun kırılımı az (B26) ve DynamoDB sayfasıyla ilişki karışık (B6). Bu yüzden "yakın yarış"ın gerçekten yakın olup olmadığından emin değilim.

**ElastiCache (kart 9):** Evet. DocumentDB'yi, oturum süre sonu dakikalar kadar esnek olabiliyorsa, gecikme hedefi milisaniyelerce ise, yük birkaç yüz istekse ve oturumun içine göre analiz ana iş ise seçerim. Bellek içi engine'in tam anında süre sonu ve bellekten okuma avantajı açık anlatılmış. Eksik: 1 ms / 2 ms belirsizliği (B30), ve "ikisi birlikte" mimarisinde tamamlanmayan oturumların özetini DocumentDB'ye kimin, ne zaman yazdığı.

**OpenSearch (kart 1'de üçüncü, kart 8'de ikinci):** Kısmen. Kayıt sistemi için DocumentDB, metin araması için OpenSearch ayrımını anlatabilirim. Ama kart 8'i anlatamam: R1'i ve R2'yi OpenSearch kazanıyor, M1'in kendi cümleleri bu iş yükü için search engine diyor, ve DocumentDB sadece ekip bilgisi ve ek servis maliyetiyle kazanıyor (B21). Meslektaşım "facet her sayfada ve 20 filtre varsa neden OpenSearch değil?" diye sorarsa, sayfadaki cevap "ekip bilmiyor" olur; bu teknik bir cevap değil. Eksik: DocumentDB'de facet'in hangi ölçekte yetmediğine dair bir eşik (field sayısı, istek/saniye) ve M1 ile kart 8'in aynı eşiği kullanması.

**Aurora PostgreSQL (kart 1, 3, 7'de ikinci):** Evet, büyük ölçüde. DocumentDB'yi şu durumlarda seçerim: nesne kendi içinde bütünse, şekli türden türe değişiyorsa ve tek parçası sık değişiyorsa (JSONB + MVCC tüm row'u yazar). Aurora'yı şu durumlarda seçerim: kurallar birçok table'ı kapsıyorsa ve aynı transaction'da değişiyorsa. Eksik: kart 7'de Aurora'nın "aynı transaction'da yazar, tüketici gerekmez" kazancı sayılmamış ve karar hikâyeye yazılmış (B24). Bu kartı bir meslektaşa savunamam.

**DocumentDB elastic cluster (kart 4'te ikinci, kart 6'da üçüncü):** Evet. Engine aynıdır, R1 aynıdır. Elastic cluster'ı yazma tek primary'yi aşınca seçerim; transaction, change stream ya da point-in-time restore gerekiyorsa instance-based cluster'da kalırım. Eksik: geçişin ne zaman gerektiğine dair ölçü sadece "yük testi yap" (A9); yanlış shard key ve çıkış yolu (B14); tek primary'nin R1'de mi R2'de mi sayıldığı sorusu (B16); kart 4'te tek primary'nin üç kez sayılması (B18). Bu yüzden kart 4'te DynamoDB ile instance-based DocumentDB arasındaki 22,7 puanlık farkın ne kadarının gerçek olduğunu söyleyemem.

## Kapanış (yazar)

| Bulgu | Karar | Ne yapıldı |
|---|---|---|
| B1 | Düzeltildi | A2 satırı ürün adlarıyla: "MongoDB'de ve DocumentDB'de (4.0 ve sonrası, $jsonSchema) mümkündür". |
| B2 | Düzeltildi | A5 kutusunda önce 64 sınırı, sonra sınıra yaklaşınca yapılacak iş; primary yerine "yazmaları alan sunucu (A9'daki primary)". |
| B3 | Düzeltildi | İlk geçtiği yerde deneyin kategori sayfasındaki "Use the index" / "Collection scan" düğmeleri olduğu yazıldı. |
| B4 | Düzeltildi | C2'ye "instance'ı olmayan bir cluster yalnız storage'dır ve sorgu almaz" eklendi. |
| B5 | Düzeltildi | M7 girişi karar simülasyonlarında kullanılan dört rengi tek tek açıklıyor; kullanılmayan iki renk adıyla belirtildi. |
| B6 | Düzeltildi | Kart 2 kafa kafaya: DynamoDB sayfasının profil kartının farklı bir iş yükü olduğu ve neden farklı olduğu açıkça yazıldı. |
| B7 | Düzeltildi | A10 matrisinin önüne DynamoDB terimleri (GSI, LSI, Scan, GetItem, UpdateItem) cümlesi; oplog ve facet ilk geçtikleri yerde parantezle tanımlandı. |
| B8 | Düzeltildi | updateMany, relevance, planner ve point-in-time restore ilk geçtikleri yerde yan cümleyle tanımlandı. |
| B9 | Düzeltildi | Servis terimleri tablosuna okuma modeli, Multi-AZ, working set, shard'ı ısıtmak, şema komutu (DDL), DAX, bitmap, logical replication, analyzer, if_seq_no eklendi; elastic gerekçesinde DDL düz dille yazıldı. |
| B10 | Düzeltildi | Seed (örnek veriyi bir kez yükleyen script) M6'da ve Neptune satın alma graph'ı A2'de tanımlandı. |
| B11 | Düzeltildi | Kart 6 kararı: reddedilen çevrimdışı yazmada uygulama listeyi yeniden okur, değişiklikleri öğe öğe yeniden uygular, aynı öğe çakışırsa kullanıcıya sorar. |
| B12 | Düzeltildi | Kart 7 kararı: her event bir sıra numarası taşır ve güncelleme filtresi eski event'in yeni durumu ezmesini engeller. |
| B13 | Düzeltildi | M5'e küçük iş yükleri paragrafı: tek instance (dayanıklılık aynı, failover yok, geliştirme için), iki instance (üretim), serverless (yine iki instance, boşta 0,5 DCU). |
| B14 | Düzeltildi | Kart 4: elastic R2'ye shard key'i içermeyen sorunun bütün shard'lara gitmesi eklendi (9 → 8); karara yanlış shard key ve çıkış yolu (yeni collection'a taşıma) yazıldı. |
| B15 | Düzeltildi | M5'e AWS DMS ile geçiş (tam yükleme + sürekli kopya, kaynak linkli) ve MongoDB Atlas'ın neden aday olmadığı yazıldı. |
| B16 | Düzeltildi | Callout'tan tek primary engine özelliği olarak çıkarıldı; "tek primary instance-based cluster'ın ölçeklenme modelidir ve R2'de sayılır" eklendi. |
| B17 | Düzeltildi | Kart 4 R1.5 gerekçeleri yalnız engine davranışı (best effort zamanlama, silmeler eklemelerle yarışır / yarışmaz); I/O ücreti yalnız R5'te. Puanlar aynı kaldı çünkü kırılım zaten engine davranışındandı. |
| B18 | Düzeltildi | Kart 4 DocumentDB R4 3 → 6: yalnız boyutlandırma işi; tepenin karşılanamaması sadece R2'de. Kart 9 R4 9 → 7: aynı boyutlandırma işi daha küçük ölçekte. Toplam 63,2 → 66,2; sıra değişmedi. |
| B19 | Düzeltildi | Kart 6 elastic R1.3 gerekçesine "elastic cluster bu özelliği sunmaz; servis tasarımıdır ve R4'te sayıldı", R4'e neden orada sayıldığı eklendi (uygulamanın yazıp işlettiği yeni parça). |
| B20 | Düzeltildi | Kart 9 DocumentDB: TTL index güncellemesi R1.2 ve R1.4'ten çıkarıldı (R1.4 9 → 10), yalnız R5'te sayılıyor. |
| B21 | Gerekçeli kabul + düzeltme | Kart kalır: metin araması bugün istenmiyor ve 20 field M1'deki eşiğin altında. M1 Ö4 ve Ö6 aynı eşiği kullanıyor (20 sınır, 50+ ya da metin araması search engine); kafa kafaya bugünkü index'lerin boşa gitmediğini ve karar çevrilme koşulunu yazıyor. Kart açıkça yakın yarış ve R1'i OpenSearch kazanır diyor. |
| B22 | Düzeltildi | Story'ye segment denetim sorusu eklendi (EY satırı: "premium segmentini hedefleyen flag'ler"); AppConfig'in neden aday olmadığı (database değil, içine göre soru yok) ve ikisi birlikte koşulu kafa kafaya ve karara yazıldı. |
| B23 | Düzeltildi | Geçmiş artık flag'e gömülmüyor (A3 kuralı): flag_history collection'ı ve transaction; DocumentDB TA 10 → 9, DynamoDB aynı mekanizma 9. |
| B24 | Düzeltildi | Aurora R4 6 → 7 ve gerekçesi: aynı transaction'da yazma, tüketici ve sırasız event yok; writer yükü yalnız R2'de. Kafa kafaya ayrı schema ve materialized view sorusunu cevaplıyor. |
| B25 | Düzeltildi | Kart 7 DynamoDB R1.1 8 → 10: sınırlı geçmiş için uydurma kırılım kaldırıldı. |
| B26 | Düzeltildi | Kart 2 DynamoDB R1.1 8 → 6: list elemanına index yok, kart 3, 5, 7 ile aynı mekanizma. Fark 3,2 → 5,6; kart artık yakın yarış değil, M7 başlığı ve okunuş güncellendi. |
| B27 | Düzeltildi | Kart 3 YD: iki aday aynı mekanizma, aynı puan (6); 24 saatlik Streams kırılımı kaldırıldı (kart 6 ve 10'da 1 puan, tutarlı). |
| B28 | Düzeltildi | R4 "instance sınıfını ekip seçer" her kartta 1 puan (kart 3, 5 düzeltildi); R5 kırılımı boş kalan kapasiteyle orantılı ve kuralı M2 özet paragrafında ve kart 1 gerekçesinde yazıldı. |
| B29 | Düzeltildi | Kart 1 DocumentDB R4'ten "katalog zaten bu cluster'dadır" çıkarıldı; gerekçe ekip ve operasyon. |
| B30 | Düzeltildi | Kart 9 DA ağırlık nedeni "okumanın her milisaniyesi her sayfaya eklenir"; hedef tek sayı: 2 ms. |
| B31 | Düzeltildi | Kart 4 kararına Kinesis Data Streams'in neden aday olmadığı (son 100 event'i key ile cevaplamaz) ve warehouse kopyası için ikisi birlikte yazıldı. |
| B32 | Düzeltildi | e2e/index.yaml'da docdb okuma süresi 35 → 150 dakika. |
| B33 | Düzeltildi | A9 kutusunun kart örnekleri sayılarıyla düzeltildi (kart 2: 150, kart 6: 1.500, kart 9: 5.000, kart 4: 20.000/80.000); kart 4 ve 9 R4 aynı mantıkta (B18). |
| B34 | Düzeltildi | Matris Ö6: "bazıları sadece 8.0.2 ve sonrasında". |
| B35 | Düzeltildi | Tam liste yalnız M5'te; callout ve terimler tablosu "bazı index türleri, tam liste M5'te" diyor. |
| B36 | Düzeltildi | Görsel AWS'in resmî görseli (lisanslı, images.yaml); altyazı tek bir şeye işaret ediyor (shard key'e göre dağılım, her shard kendi yazmalarını karşılar) ve adların temsilî olduğunu söylüyor. |
| B37 | Düzeltildi | Endpoint görseli altyazısına "kopyaları basitleştirir, gerçekte her AZ'de iki kopya vardır" eklendi. |
| B38 | Gerekçeli kabul | Renk açıklaması bütün sayfaların ortak JS bloğudur (e2e.js); skill paylaşılan parçayı değiştirmeyi yasaklıyor. Karar simülasyonları için M7 girişi kullanılan renkleri açıklıyor (B5). Simülasyon başına renk listesi skill için bir öneri olarak hand-over'a yazıldı. |

Sonraki kontrol (yazar, 2026-10-31): check_usecases.py `usecases: OK`, clarity TR `OK`, 9 simülasyon son adıma kadar oynadı, 20 checkpoint cevaplandı, 420 px pencerede yatay taşma yok. Yeni toplamlar: kart 2 DocumentDB 88,2 / DynamoDB 82,6; kart 3 92,4; kart 4 DynamoDB 85,9 / elastic 82,2 / DocumentDB 66,2; kart 5 90,6; kart 7 92,8 / Aurora 82,6 / DynamoDB 80,2; kart 9 DocumentDB 64,0; kart 10 94,1 / 88,4 / 75,6.
