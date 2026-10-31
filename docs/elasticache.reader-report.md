# Reader simulation: Amazon ElastiCache (elasticache), Türkçe sayfa, model 2
Tarih: 2026-10-31
Okuyucu: bellek içi bir key-value store (Redis/Valkey) ya da ElastiCache hiç kullanmamış, DynamoDB ve Aurora sayfalarını okumuş bir geliştirici (soğuk okuyucu). Kaynak: /tmp/ec_w/elasticache.tr.txt (baştan sona), /tmp/ec_w/page.html (resim altyazıları, kart tabloları, beş simülasyonun JSON'u), karşılaştırma için http://localhost:8797/e2etutorial/dynamodb (kartlar uc-session, uc-rate, uc-ads). Kural referansı: e2e-tech-tutorial/references/decisions.md (yalnız kuralları bilmek için).

## Genel izlenim
Bölüm A çok iyi bir temel veriyor: "bu veri kaybolursa ne olur?" sorusu baştan sona taşınıyor, her kavramın bütün durumları tabloda, canlı ölçümler (59 satışlık yarış, 5 saniyelik TTL) ikna edici. On kartın aritmetiği doğru: her hücre, her R1 ara toplamı, her toplam, özet tablosundaki farklar (10, 1, 14, 11, 24, 13,5, 8, 19, 7, 10) ve beş simülasyonun son adımları (sim-w_board 90/89/73,5, sim-w_session 95/85/76,5, sim-w_geo 87/77/64, sim-w_queue 97/78/74, sim-w_lock 97/89/72) kartlarla aynı. Oturum, rate limit ve öneri kartlarının puanları DynamoDB sayfasındaki uc-session, uc-rate ve uc-ads kartlarıyla birebir aynı. Yedi kartta MemoryDB'nin R1'i ElastiCache ile eşit. Her kafa kafaya paragrafında farkın yeri, öbür adayın dürüst gücü ve bir koşul var; her kararda artı, eksi ve uygulamanın yapması gereken iş yazılı.

Sorunlar puanların tutarlılığında ve aday seçiminde: aynı mekanizma kartlara göre farklı puan kaybettiriyor (R3'teki "kalıcı log yok", MemoryDB'nin log gecikmesi, sıcak key'i bölmek). Bazı zayıflıklar birden fazla satırda sayılıyor (fiyat R1'de ve R5'te, boyutlandırma R2'de ve R4'te). İki kartta daha güçlü bir AWS alternatifi tabloda yok (kart 6, kart 4). Kart 8'de ElastiCache aynı engine'in daha uygun aracıyla (stream) değil, list ile puanlanıyor. Kart 2'nin "yakın yarış" sonucu ölçülmemiş bir maliyet iddiasına dayanıyor.

## Bulgular

### R1 (yüksek): Kart 6'da gerçek alternatifler yok; ikinci ve üçüncü adaylar zayıf seçilmiş
Bölüm: M2 kart 6 (uc-pubsub, "Canlı güncellemeler için pub/sub"). Alıntı: "key-value (DynamoDB) … 19 / 40 | 56,5" ve "DynamoDB'nin değişiklik akışı bir olay kaynağıdır, ama bir yayın kanalı değildir."
Tür: ikna etmeyen gerekçe (en uygun servis gerçekten en uygun mu).
Sorun: Sayfa Ö5'te kendisi "fan-out servisi (Amazon SNS)" diyor, ama kart SNS'i, AWS AppSync Events'i ve API Gateway WebSocket API'ı aday yapmıyor. Bu servisler "20 WebSocket sunucusuna yayın" ve "150.000 tarayıcıya canlı mesaj" işini yönetilen olarak yapar; AppSync Events ya da API Gateway WebSocket, WebSocket sunucularını bile ortadan kaldırabilir. Tabloda bunların yerine DynamoDB Streams + Lambda + bağlantı table'ı var. Bu zinciri kimse bu iş için seçmez, bu yüzden 95'e 56,5 sonucu bir şey öğretmiyor. İkinci aday MemoryDB de aynı engine olduğu için gerçek bir alternatif değil. Okuyucu "ElastiCache Pub/Sub'ı SNS ya da AppSync'e karşı ne zaman seçerim?" sorusunun cevabını bulamıyor.
Mimara soru: Bu iş yüküne en yakın AWS servisi hangisi: SNS mi, AppSync Events mi, API Gateway WebSocket mi? Tabloya bunlardan biri girse ElastiCache yine birinci mi olur, ve hangi satırda kazanır?

### R2 (yüksek): Aynı mekanizma (kalıcı log yok, kayıp kabul edilir) R3'te kartlara göre 4, 7 ya da 8 alıyor
Bölüm: M2 kartlar 1, 2, 3, 4, 5, 6, 8, 9, 10, satır R3. Alıntı: kart 1 "R3 | 4 … bu kartta kabul edilen bir sonuçtur"; kart 4 "R3 | 7 … Bu kartta kopya kaybı zararsızdır, bu yüzden kırılım diğer kartlardan küçüktür"; kart 6 "R3 | 8".
Tür: ikna etmeyen gerekçe (aynı mekanizma aynı biçimde mi düşürülüyor).
Sorun: Puan ölçeğine göre puan, satırdaki "ne istiyoruz" cümlesinin ne kadar karşılandığını ölçer. Kart 1'in R3 isteği "Düşük: … yeniden login olması kabul edilir", kart 3'ünki "bir dakikalık boşluk kabul edilir". ElastiCache bu istekleri karşılıyor ama 4 alıyor. Kart 4'ün isteği de "Düşük", orada 7 alıyor. Kart 2'nin isteği "Orta" (4 dakikalık boş vitrin), orada da 4 alıyor. Yani puan bazı kartlarda mutlak dayanıklılığı, bazı kartlarda isteğin karşılanmasını ölçüyor. "Kopya kaybı zararsızdır" gerekçesi kart 1, 3, 5, 9 ve 10 için de geçerli (oturum, sayaç, öneri, konum, hepsi yeniden kurulur ya da yeniden gelir). Bu, yakın yarışı da etkiliyor: kart 2'de ElastiCache, kart 4'teki mantıkla 7 alsaydı 94,5'e 89 olurdu ve yarış artık yakın olmazdı.
Mimara soru: R3 puanı mutlak dayanıklılığı mı ölçüyor, yoksa bu kartın R3 isteğinin karşılanmasını mı? Hangisiyse, dokuz kartta aynı kural uygulanınca hangi puanlar değişir?

### R3 (yüksek): MemoryDB'nin log gecikmesi kartlara göre farklı düşüyor; kart 1'de iki tam puan birlikte doğru olamaz
Bölüm: M2 kart 1 (MemoryDB R1.3, R1.4, R2), kart 3 (MemoryDB R2), kart 9 (MemoryDB R2). Alıntı: kart 1 "R1.3 | 10 → 10 | GETEX okuma ve yenilemeyi tek komutta yapar" ve "R1.4 | 10 → 15 | … okumalar mikrosaniyelerdedir" ve "R2 | 7 … 3 puan kırıldı: her süre yenilemesi bir yazmadır …"; kart 3 "R2 | 5 … 5 puan kırıldı"; kart 9 "R2 | 7 … 20 milyon yazma daha uzun sürer".
Tür: ikna etmeyen gerekçe (aynı mekanizma aynı biçimde mi düşürülüyor).
Sorun: GETEX … EX süreyi değiştirdiği için bir yazmadır. MemoryDB'de yazma log'a işlendikten sonra onaylanır, bu yüzden her sayfa isteği tek haneli milisaniye bekler. Kartın 1 ms isteği (R1.4) ile tek komut isteği (R1.3) MemoryDB'de aynı anda karşılanamaz. Ya GETEX kullanılır ve okuma milisaniyelere çıkar, ya da GET ile ayrı bir EXPIRE gönderilir ve iki istek olur. Bu durum yalnız tepe anlarında değil, her istekte olur; ama kart bunu yalnız R2'de, "tepe anında" diye 3 puanla sayıyor. Aynı mekanizma kart 3'te (her API isteğinin önünde bir INCR, 2 ms sınırı) 5 puan kırıyor, kart 9'da ise kritik yolda olmayan gece toplu yazmasında yine 3 puan kırıyor. Kritik yolda her istekte olan gecikme (kart 1) ile hiçbir isteği bekletmeyen gece yazması (kart 9) aynı indirimi almamalı.
Mimara soru: Kart 1'de MemoryDB'de 1 ms sınırı hangi komut dizisiyle karşılanıyor? Log gecikmesi kritik yoldaysa (kart 1 ve 3) ve değilse (kart 2 ve 9) R2'de kaç puan kırılır? Bunun kuralı nedir?

### R4 (orta): Kart 2'nin yakın yarışı ölçülmemiş bir maliyet iddiasına dayanıyor
Bölüm: M2 kart 2 (uc-board), R4 ve R5. Alıntı: MemoryDB "R5 | 5 … node'lar kampanya akşamı için boyutlanır ve boş saatlerde de çalışır"; ElastiCache "R5 | 9 … sorted set komutları basit bir GET'ten daha fazla ECPU harcar".
Tür: ikna etmeyen gerekçe.
Sorun: Fark tek puan; R4 ile R5'teki 8 puanlık fark kararı veriyor. Veri birkaç yüz MB ve trafik saniyede yaklaşık 3.000 okuma. İki küçük MemoryDB node'unun aylık fiyatı ile saniyede 3.000 sorted set komutunun aylık ECPU fiyatı birbirine yakın olabilir. Kart aylık bir rakam vermiyor. MemoryDB R5'te 5 yerine 7 alsaydı kazanan değişirdi. Kart 3'te ve B9'da sayfa rakam veriyor (ayda 9.500 $, ayda 900 $), bu kartta vermiyor.
Mimara soru: Bu iş yükünde iki servisin aylık faturası kaç dolar? R5'teki 5'e 9'luk farkı hangi rakam taşıyor?

### R5 (orta): 1 ms ve 2 ms sınırları, sayfanın kendi ölçümüyle çelişiyor
Bölüm: A1, Ö1, B1–B5, C3 ve kart 1 (R1.4, R2), kart 3 (R1.2). Alıntı: A1 "Engine App'in ölçümünde cevap 1–2 milisaniyede gelir"; B3 "her biri 1,4–1,8 milisaniye"; kart 1 "Okuma 1 milisaniyenin altında dönmeli" ve ElastiCache "Puan kırılmadı".
Tür: anlaşılmayan cümle / ikna etmeyen gerekçe.
Sorun: Sayfanın kendi canlı ölçümü 1,3–1,8 ms. Kart 1 her okumanın 1 ms'nin altında olmasını istiyor ve ElastiCache tam puan alıyor. Kanıt olarak yalnız AWS'in p50 değeri ("okumaların yarısı") veriliyor; p99 hakkında bilgi yok. R1 · DA'nın komutun kendi süresini, R2'nin ise uçtan uca süreyi ölçtüğü söylenmiyor. Okuyucu, ölçülen 1,4 ms ile 1 ms isteğini nasıl uzlaştıracağını bilmiyor.
Mimara soru: 1 ms sınırı komutun süresi mi, yoksa uygulamanın gördüğü gidiş-dönüş mü? Lale Market'in 1,4 ms ölçümü bu kartta neden bir puan kırmıyor?

### R6 (orta): Kart 7'de ElastiCache'in kendi kalıcılık seçeneği hesaba katılmıyor
Bölüm: M2 kart 7 (uc-lock), M5, B8. Alıntı: M5 "ElastiCache node'lu Valkey 9.0, kalıcılık açık … 'designed for zero data loss'"; kart 7 ElastiCache "R3 | 1 … Serverless'ta kalıcı log yoktur".
Tür: eksik durum.
Sorun: Sayfa birçok yerde ElastiCache'te senkron kalıcı log seçeneği olduğunu söylüyor (A9, Ö7, M5, B8). Ama kartlardaki "ElastiCache (Valkey)" adayı her zaman Serverless olarak puanlanıyor ve bu hiçbir yerde açıkça yazmıyor. Kart 7'nin kafa kafaya paragrafındaki koşul ("kilidin kaybı zararsız olsaydı … ya da korunan iş idempotent olsaydı") bu seçeneği anmıyor. Okuyucu şunu soruyor: zaten node'lu bir ElastiCache çalıştırsaydık ve kalıcılığı açsaydık ElastiCache kazanır mıydı?
Mimara soru: Kartlardaki "ElastiCache" adayı Serverless mı? Node'lu Valkey 9.0 ve senkron kalıcılıkla kart 7'nin sonucu ne olur, ve bu bir "koşul değişseydi" cümlesi olmamalı mı?

### R7 (orta): Kart 7'de süreli kilit DynamoDB'de de "tam bir kez" garanti etmiyor
Bölüm: M2 kart 7, DynamoDB R1.1 ve karar paragrafı. Alıntı: "Kilit onaylandıktan sonra başka bir worker onu alamamalı" ve DynamoDB "R1.1 | 10 … Puan kırılmadı"; karar: "ElastiCache seçilirse uygulama ödeme talimatını … DynamoDB'ye koşullu yazmalı".
Tür: ikna etmeyen gerekçe / eksik durum.
Sorun: Kilit 15 dakikalık bir süreyle alınıyor. Worker A takılırsa (uzun bir GC duraklaması, yavaş bir banka çağrısı) ve süre dolarsa, worker B koşullu yazmayla kilidi meşru olarak alır ve iki worker birlikte ödeme yapar. Bu durum DynamoDB'de de olur. Sayfanın B8'de gösterdiği gerçek koruma (gün ve satıcı başına benzersiz id ile koşullu yazma, yani idempotency) yalnız ElastiCache seçildiğinde öneriliyor. DynamoDB'nin TA satırında 10 alması, okuyucuya "DynamoDB kilidi çift ödemeyi kesin önler" izlenimini veriyor.
Mimara soru: DynamoDB kilidiyle de süre dolduğunda iki worker çalışabilir mi? Çalışabiliyorsa idempotent ödeme talimatı her adayın kararında olmalı değil mi?

### R8 (orta): Kart 8'de ElastiCache list ile puanlanıyor; aynı engine'in stream aracı eksikleri kapatıyor
Bölüm: M2 kart 8 (uc-queue), A8, B7. Alıntı: kart 8 ElastiCache "R1.2 | 7 … çöken worker'ın işi kendi 'işleniyor' listesinde kalır" ve "R1.3 | 4 … Engine'de deneme sayacı, görünürlük süresi ve bozuk iş kuyruğu yoktur"; A8 "Onaylanmamış mesaj bekleyenler listesinde kalır; başka okuyucu sahiplenebilir".
Tür: ikna etmeyen gerekçe.
Sorun: Valkey stream'inin consumer group'u, onaylanmamış mesajı bir süre sonra başka bir okuyucuya verir (XAUTOCLAIM ile, bir min-idle süresiyle; görünürlük süresine benzer) ve her mesajın teslim sayısını tutar (XPENDING). Bu araçlarla "üç kez başarısız olan iş" ayrılabilir. Kart en zayıf yapıyı (list) puanlıyor ve "engine'de yok" diyor. Stream ile R1.2 ve R1.3 daha yüksek olurdu. Bu, SQS'in kazanmasını değiştirmeyebilir (dead-letter queue taşıması yine kod ister), ama farkın "tamamı R1'den" cümlesi olduğundan büyük görünür.
Mimara soru: Bu iş yükünde list yerine consumer group'lu bir stream kullanılsa R1.2 ve R1.3 kaç alır, ve fark yine 19 puan mı olur?

### R9 (orta): Kapasite boyutlandırma birden fazla satırda sayılıyor
Bölüm: kart 5 (Timestream for InfluxDB), kart 10 (OpenSearch), kart 9 (DynamoDB). Alıntı: Timestream "R2 | 6 … Instance yazma hızına göre boyutlanır. 4 puan kırıldı", "R4 | 5 … instance boyutlandırma", "R5 | 6 … instance kampanya akşamı için boyutlanır"; OpenSearch "R2 | 6 … node sayısı ve tipi önceden boyutlanır"; DynamoDB kart 9 "R2 | 8 … on-demand ya da zamanlanmış auto scaling bir ayardır".
Tür: ikna etmeyen gerekçe (bir zayıflık birden fazla satırda).
Sorun: Sayfanın kendi kuralı "node tipi ve shard sayısı seçmek R4'tür, tepeyi karşılamak R2". Timestream'de boyutlandırma hem R2'de hem R4'te puan kırıyor, R5'te de üçüncü kez geçiyor. OpenSearch'te R2'deki kırılım gerekçesi bir boyutlandırma işi, yani R4'ün konusu. DynamoDB kart 9'da bir ayar işi R2'de sayılıyor. Kartlar kazananı değiştirmiyor, ama okuyucu kuralı kartlardan öğrenemiyor.
Mimara soru: Timestream ve OpenSearch R2'de tepeyi karşılayamadığı için mi puan kaybediyor, yoksa boyutlandırma iş olduğu için mi? İkincisiyse R2'deki kırılım neden R4'teki ile aynı şey değil?

### R10 (orta): Fiyat R1'in içinde ve aynı maliyet iki kez sayılıyor
Bölüm: kart 1 (DynamoDB R1.3 ve R5), kart 2 (DynamoDB R1.1 ve R5), kart 3 (DynamoDB R1.1), kart 5 (DynamoDB R1.1 ve R5), kart 8 (ElastiCache ve MemoryDB R1.1 ve R5). Alıntı: kart 3 "1 puan kırıldı: … reddedilen yazma da birim tüketir"; kart 5 "1 puan kırıldı: her artırma item'ın tamamını yeniden yazan bir yazma birimidir"; kart 1 "her sayfa görüntüleme bir yazma olur; yazma okumadan yavaş ve pahalıdır" ve R5 "her sayfada bir yenileme yazması"; kart 8 R1.1 "bir iş üç komuttur" ve R5 "bir iş üç komut".
Tür: ikna etmeyen gerekçe (R1 yalnız engine'i mi puanlıyor; bir zayıflık birden fazla satırda).
Sorun: Sayfa "R1 satırları yalnız engine'in kendisini puanlar; … ECPU ya da node-saat fiyatı … R1'de sayılmaz" diyor. Ama "birim tüketir", "yazma birimidir" ve "pahalıdır" faturalama gerekçeleri ve R1'de puan kırıyorlar. Aynı yazma birimleri R5'te ikinci kez sayılıyor. Kart 2'de "kaçıncı sıradayım" sayımı R1.1'de, okuma birimleri R5'te. Kart 8'de "üç komut" hem R1.1'de hem R5'te bir puan kırıyor.
Mimara soru: Bu R1 kırılımları engine'in hangi davranışını ölçüyor? Fiyat kısmı R5'e taşınırsa R1.1 kaç olur?

### R11 (orta): Kart 5'te sıcak key'i bölmek ElastiCache'te bedelsiz, DynamoDB'de 5 puan
Bölüm: M2 kart 5 (uc-views), R1.1 ve R2. Alıntı: ElastiCache "HINCRBY views:…:{n} P0001 1" ve "R2 | 9 … Key 16 parçaya bölündüğü için sıcak ürünlerin yükü birkaç shard'a dağılır … 1 puan kırıldı: boş bir Serverless cache …"; DynamoDB "R2 | 5 … sıcak sayaçlar N parçaya bölünmeli ve okumada toplanmalıdır".
Tür: ikna etmeyen gerekçe (aynı mekanizma) ve erken terim.
Sorun: Gerçek projede key'in 16 parçaya bölündüğü yazmıyor. R1.1'de "{n}" açıklanmadan görünüyor ve R2'de bölmenin yapılmış olduğu varsayılıyor. ElastiCache'teki tek kırılım ön ölçeklendirme için; bölmenin kodu ve okumada 16 hash'i birleştirmek (ilk 20 için de) hiçbir satırda sayılmıyor. DynamoDB'de aynı iş 5 puan kırıyor. B4 ise "Bir bellek içi node için saniyede binlerce DECR küçük bir yüktür" diyor; bu doğruysa ElastiCache'te bölmeye hiç gerek yok, o zaman "16 parça" cümlesi neden var?
Mimara soru: ElastiCache'te 25.000 olay/saniyelik sıcak bir key bölünmeli mi? Bölünmeliyse bu iş hangi satırda ve kaç puan? Bölünmemeliyse R2 cümlesi neden bölmeyi anlatıyor?

### R12 (orta): Kart 4'te CloudFront aday değil; Aurora'nın JOIN'i üç satırda sayılıyor
Bölüm: M2 kart 4 (uc-cache). Alıntı: "Fiyat değişince en geç 5 dakika içinde sayfada görünmesi kabul edilir; stok … da 5 dakika eski olabilir"; Aurora "R1.1 | 7 … aynı cevap her açılışta yeniden hesaplanır", "R1.3 | 7 … her okuma bir sorgu planı ve bir JOIN çalıştırır", "R2 | 5 … her görüntülemede yeniden çalışan bir JOIN".
Tür: ikna etmeyen gerekçe (daha iyi bir AWS servisi eksik mi; bir zayıflık birden fazla satırda).
Sorun: Herkes için aynı olan ve 5 dakika eski olabilen bir ürün sayfası, ilk akla gelen bir CDN önbelleği işidir (CloudFront, TTL 300). İstek uygulamaya bile gelmez. Kart CloudFront'u ne aday yapıyor ne de neden dışarıda bıraktığını söylüyor. İkinci aday DynamoDB'nin Aurora'nın önünde bir kopya store'u olarak kullanılması doğal bir seçim değil (kart 1'deki DAX gibi). Ayrıca "her açılışta JOIN" Aurora'da R1.1, R1.3 ve R2'de üç kez puan kırıyor.
Mimara soru: Sayfa kişiye özel değilse CloudFront bu iş yükünde nerede durur? ElastiCache'i CloudFront'a karşı seçtiren koşul nedir (kişisel fiyat, oturuma bağlı içerik, API cevabı)?

### R13 (orta): A10 matrisi MemoryDB'ye ½ veriyor, kartlar R1'de hep tam puan veriyor
Bölüm: A10 özellik × ürün matrisi ve M2'deki yedi MemoryDB kartı. Alıntı: matris "Ö1 … ½ Okuma mikrosaniye, yazma tek haneli milisaniye", "Ö4 … ½ … eviction istenmez", "Ö8 … ½"; kart 1 "R1'in dört alt maddesinde ikisi de tam puan alır".
Tür: anlaşılmayan cümle.
Sorun: Matris engine özelliği ile servis tasarımını karıştırıyor. Okuyucu A10'da "MemoryDB'de Ö1 yarım" diye öğreniyor, sonra M2'de "aynı engine, R1 aynı" okuyor. Sayfanın hiçbir yerinde matrisin servisi, kartların R1'inin ise engine'i ölçtüğü söylenmiyor.
Mimara soru: Matrisin "½"leri engine farkı mı, servis farkı mı? Servis farkıysa matrise bunu söyleyen bir not girmeli mi?

### R14 (orta): R3–R5 ağırlığının gerekçesi, ağırlık kuralıyla çelişiyor
Bölüm: Mimar gözüyle, "Neden R1 en ağır, R3–R5 neden daha hafif ama silinmez?" ve hemen altındaki ağırlık paragrafı. Alıntı: "AWS bu ikisini tek serviste birleştirebilir ya da yalnız birini çıkarabilirdi. Bu yüzden R3–R5'in ağırlığı R1 kadar yüksek olamaz." ve "Ağırlık puanlardan önce, iş yükünün önceliğinden belirlenir".
Tür: anlaşılmayan cümle.
Sorun: İlk cümle ağırlığı üreticinin tasarımının değişebilir olmasına bağlıyor, ikinci cümle iş yükünün önceliğine. Kart 7'de R3 30 alıyor, R1'in her alt maddesinden ve R2'den ağır. Okuyucu hangi kuralın geçerli olduğunu anlamıyor. "AWS birleştirebilirdi" bir iş yükünün dayanıklılığa ne kadar ihtiyaç duyduğunu değiştirmez.
Mimara soru: Bir iş yükünde dayanıklılık en önemli şeyse (kart 7) R3 R1'den ağır olabilir mi? Olabiliyorsa "R1 kadar yüksek olamaz" cümlesi ne anlatıyor?

### R15 (düşük): Kart 6'da DynamoDB'nin fan-out zinciri altı satırda sayılıyor
Bölüm: M2 kart 6, DynamoDB. Alıntı: "R1.1 … fan-out uygulama kodudur", "R1.2 … Yol bir yazma, bir değişiklik akışı kaydı ve bir fonksiyon çağrısıdır", "R2 … fonksiyon eşzamanlılığı", "R4 … üç yeni parça … ve aralarındaki hata yönetimi ekibe kalır", "R5 … saklanmaması gereken mesajlar için üç kez ödenir".
Tür: ikna etmeyen gerekçe (ek kod hem R1'de hem R4'te).
Sorun: Aynı tasarım (akış + fonksiyon + bağlantı table'ı) R1.1, R1.2, R1.3, R2, R4 ve R5'te puan kırıyor. Diğer kartlarda sayfa "R1.x'te sayıldı" notuyla çift saymayı önlüyor; bu kartta bu not yok.
Mimara soru: Fonksiyon ve bağlantı table'ının kodu R1.1'de mi, R4'te mi sayılır?

### R16 (düşük): Kart 7'de R5 ağırlığı hikâyeyle uyuşmuyor
Bölüm: M2 kart 7, R5. Alıntı: "Günde birkaç istek; maliyet önemsizdir, ama sadece kilit için yeni bir sistem işletmek istenmez" ve ağırlık 10; MemoryDB "R4 | 6 … yalnız bu kilit için … yeni bir cluster işletilir" ve "R5 | 4 … en küçük çoklu AZ'li cluster bile yıl boyu çalışır".
Tür: ikna etmeyen gerekçe (ağırlık hikâyeden mi geliyor).
Sorun: Hikâye maliyetin önemsiz olduğunu söylüyor, ama R5 10 ağırlık alıyor. "Yeni bir sistem işletmek" R4'ün konusu, ve MemoryDB'de hem R4'te hem R5'te puan kırıyor.
Mimara soru: Maliyet önemsizse R5 neden en düşük sınırda (5) değil?

### R17 (düşük): Kart 9'da MemoryDB'nin gece yazma penceresi iddiası kanıtsız
Bölüm: M2 kart 9 (uc-reco), MemoryDB R2. Alıntı: "3 puan kırıldı: her gece yazması log'a işlendikten sonra onaylanır; 20 milyon yazma daha uzun sürer ve 30 dakikalık pencereyi zorlar."
Tür: ikna etmeyen gerekçe.
Sorun: Saniyede 11.000 yazma, pipeline ve birkaç shard ile birçok bağlantıdan gönderilir. Tek haneli milisaniye gecikme, bu hızın 30 dakikada bitmesini neden engellesin, bir hesap yok. Bu bir verim sorusu, gecikme sorusu değil.
Mimara soru: Kaç shard ve kaç paralel bağlantıyla MemoryDB 20 milyon yazmayı 30 dakikada bitiremez?

### R18 (düşük): Bazı terimler tanımlanmadan önce kullanılıyor
Bölüm: başlık, A1, R1 kataloğu, kart 5, kart 10. Alıntı: başlık "Lale Market'teki yeri: Flash deal and live data · Kimlik doğrulama: Password (Secrets Manager, ACL user)"; A1 "Engine App'in ölçümünde"; katalog "pipeline toplu yazar (A5)"; katalog "GETEX okur ve süreyi yeniler"; kart 5 "views:…:{n}" ve "Redshift"; kart 10 "ZREMRANGEBYSCORE"; R1–R5 paragrafı "bir kırılım servisin paketlemesinden geliyorsa".
Tür: erken terim.
Sorun: "Engine App" C3'e kadar açıklanmıyor. "pipeline" kataloğun gösterdiği A5'te yok; tanımı M2'nin terim tablosunda ve B5'te. "ACL user" B1'de açıklanıyor. "{n}" hiç açıklanmıyor. "Redshift" kart 5'te açıklanmadan geçiyor (M3'te "data warehouse"). "ZREMRANGEBYSCORE" B5'e kadar açıklanmıyor. "kırılım" puan kaybı anlamında bir jargon. Başlık satırı İngilizce.
Mimara soru: Bu terimler ilk göründükleri yerde tek cümleyle açıklanabilir mi, ve katalog pipeline için doğru bölüme mi gönderiyor?

### R19 (düşük): A4 resim altyazısında HTML etiketi metin olarak görünüyor
Bölüm: A4, ElastiCache User Guide'dan alınan cluster mode resmi. Alıntı: "Soldaki tek shard'lı düzen <b>cluster mode disabled</b>'dır".
Tür: resim altyazısı.
Sorun: page.html'de "&lt;b&gt;cluster mode disabled&lt;/b&gt;" olarak kaçışlı yazılmış. Okuyucu kalın yazı yerine "<b>" etiketlerini görüyor. Altyazının geri kalanı neye bakılacağını iyi anlatıyor. Diğer beş "Şuna bak" altyazısında sorun yok.
Mimara soru: —

### R20 (düşük): Bazı "ya şöyle olursa?" durumları cevapsız
Bölüm: kart 3, kart 2, kart 9, A9, M5. Alıntı: kart 3 "İlk INCR'den sonra EXPIRE 60 (ya da bir script'te ikisi birlikte)"; kart 2 "ayın en çok alışveriş yapan 10 müşterisi"; kart 9 "Hesap gece 02:00'de 30 dakikada toplu yapılır".
Tür: eksik durum.
Sorun: (a) Cache'e hiç ulaşılamazsa gateway ne yapar: istekleri geçirir mi (fail-open), reddeder mi (fail-closed)? Kart 3 ve kart 1 bunu söylemiyor. (b) INCR ile EXPIRE arasında gateway çökerse key süresiz kalır; tam puan veren R1.3 bunu anmıyor. (c) Aylık sıralama ay sonunda nasıl sıfırlanır: ay başına bir key mi, TTL mi? (d) Gece toplu yüklemesi yarıda kalırsa kullanıcıların bir kısmı eski, bir kısmı yeni listeyi görür; ne yapılır? (e) Kullanıcılar iki Bölgedeyse ne olur? Global Datastore ya da MemoryDB Multi-Region hiç geçmiyor.
Mimara soru: Bu beş durumun hangisi bu sayfanın kapsamında, ve kapsamdaysa hangi bölümde cevaplanmalı?

### R21 (düşük): İki kararın "bir koşul değişseydi" cümlesi kafa kafaya paragrafından zayıf
Bölüm: kart 5 kararı, kart 10 kararı. Alıntı: kart 5 karar "sayılar faturalamaya dayansaydı DynamoDB öne geçerdi" ve kafa kafaya "sayılar faturalamaya dayansaydı …, olay hızı yüz kat düşük olsaydı ve tekil sayım istenmeseydi"; kart 10 karar "konumlar on kat seyrek gelseydi Aurora tek başına yeterdi".
Tür: ikna etmeyen gerekçe.
Sorun: Kart 5'te karar üç koşulun yalnız birini veriyor; 24 puanlık fark yalnız R3 ile kapanmıyor gibi görünüyor. Kart 10'da Aurora'nın R2 kırılımının bir kısmı saniyede 2.000 aramadan geliyor; konumlar on kat seyrek gelse de bu kırılım kalır, ve 10 puanlık farkın kapandığı hesapla gösterilmiyor.
Mimara soru: Yalnız bu koşul değişince yeni puanlar ne olur, kazanan gerçekten değişir mi?

## Sonuç: bir meslektaşa anlatabilir miyim?
Büyük ölçüde evet.

- DynamoDB'ye karşı: Evet. Sorunun her isteğin önünde durduğu, 1–5 ms sınırının katı olduğu, TTL'in saniyesinde uygulanması gerektiği (oturum, dakikalık sayaç) ya da değerin bir veri yapısı olduğu (sorted set ile "kaçıncı sıradayım", HyperLogLog) durumlarda ElastiCache. Çok sık artırmanın yazma birimi fiyatı da ElastiCache lehine (kart 3: ayda yaklaşık 9.500 $'a karşı birkaç yüz $). Kayıt kalıcı olmalıysa, birkaç milisaniye yetiyorsa ya da kaybın bedeli para ise (kart 7) DynamoDB. Eksik olan: kaynak zaten DynamoDB ise DAX'a karşı ElastiCache sorusu yalnız Ö8'de bir cümle; kart yok. Kart 7'deki "DynamoDB kilidi kesin korur" izlenimi de düzeltilmeli (R7).
- SQS'e karşı: Kısmen. "Görünürlük süresi ve dead-letter queue gerekiyorsa SQS, işler milisaniyenin altında başlamalıysa ya da kayıp ve tekrar zararsızsa ElastiCache" diyebilirim. Ama aynı engine'in stream ve consumer group aracı puanlanmadığı için (R8), "ElastiCache stream'i SQS'e karşı ne zaman yeter?" sorusunu cevaplayamam.
- MemoryDB'ye karşı: Kavram olarak evet: aynı engine, fark kalıcı log (R3) ile serverless işletim ve fiyat (R4, R5). Onaylanan yazma kaybolmamalıysa MemoryDB, kayıp kabul ediliyorsa ElastiCache Serverless. Ama farkı sayıyla savunamam. Kart 2'deki yakın yarış aylık bir rakama dayanmıyor (R4). Log gecikmesinin indirimi kartlara göre değişiyor (R3). ElastiCache'in kendi Valkey 9.0 kalıcılık seçeneği kartların dışında kalıyor (R6). "Kalıcı log'lu node'lu ElastiCache mi, MemoryDB mi?" sorusunun cevabı M5'te tek bir hücre.
- Aurora'ya karşı: Evet. Ürün sayfasında ElastiCache Aurora'nın önünde bir kopyadır, onun yerine geçmez; sıcak küme varsa, 5 dakikalık eskime kabul ediliyorsa ve okuma writer'ı yoruyorsa. Konumda PostGIS engine uyumunu kazanır, ama saniyede 800 güncelleme writer'ı ve VACUUM'u yorar. Eksik olan: kart 4'te CloudFront karşılaştırması (R12), ve kart 6'da gerçek bir yayın servisi (SNS, AppSync Events, API Gateway WebSocket) karşısında ElastiCache Pub/Sub'ın yeri (R1).

## Kapanış (yazar)
| Bulgu | Durum | Ne yapıldı |
|---|---|---|
| R1 Kart 6'da gerçek alternatifler yok | kapandı | Kart 6'da DynamoDB çıkarıldı, en yakın yönetilen alternatif SNS aday oldu (SVC/CATEGORY/LINK'e yalnız ekleme). Sonuç ElastiCache 95, MemoryDB 81,5, SNS 78. SNS'in kafa kafaya paragrafı API Gateway WebSocket ve AppSync Events'i de anar: WebSocket sunucuları hiç istenmeseydi önce onlar değerlendirilirdi; bu hikâyede sunucular zaten çalıştığı için aday değiller. |
| R2 R3'te aynı mekanizma 4, 7 ya da 8 | kapandı | Tek kural yazıldı (mimar gözüyle, ağırlık paragrafından sonra): verinin o anki tek yeri bellekse ve kayıp kabul ediliyorsa 4; "hiç kaybolmamalı" ise 1; bellekte yalnız kaynağı tam olan bir kopya varsa (kart 4) ya da hiç veri yoksa (kart 6) kaybolan bir şey yoktur ve puan yalnız soğuk cache ya da kopan bağlantılar için kırılır. Kart 4 ve 6'nın gerekçeleri bu kurala bağlandı. Kart 2'nin isteği "Orta" ama veri yalnız bellektedir ve 4 dakika görünür bir boşluk vardır, bu yüzden 4 kaldı. |
| R3 MemoryDB log gecikmesi kartlara göre farklı; kart 1'de iki tam puan çelişiyor | kapandı | Kart 1'de MemoryDB'nin R1.3 gerekçesi, GETEX'in log'u beklemesinin servis tasarımı olduğunu ve R2'de sayıldığını söyler; R2 gerekçesi 1 ms için okumanın GET ile yapılıp sürenin yarı ömürde ayrıca yenilendiğini yazar (B5). Kart 3'te her istek bir yazma olduğu için kırılım 5'tir; gerekçe bunu söyler. Kart 9'un gerekçesi gecikme değil yazma penceresi olarak yeniden yazıldı. Kart 1, 3 ve 9'un puanları DynamoDB sayfasındaki aynı kartlarla aynı kalır (görevin tutarlılık kuralı). |
| R4 Kart 2 yakın yarışı ölçülmemiş maliyete dayanıyor | kapandı | Price List API'dan eu-central-1 fiyatları alındı: Serverless Valkey 0,101 $/GB-saat ve milyon ECPU 0,0027 $; MemoryDB Valkey db.t4g.small 0,0378 $/saat, db.r7g.large 0,2597 $/saat, 10 TB'a kadar yazılan veri ücretsiz. Kart 2'de ElastiCache yaklaşık 65 $, iki küçük MemoryDB node'u yaklaşık 55 $ (güvenli boy yaklaşık 380 $). MemoryDB R5 5'ten 7'ye çıktı ve kartı 91'e 90 kazandı: ElastiCache'in ikizine kaybettiği kart. Özet, M7 ve checkpoint ec-a1 buna göre değişti. Kart 3 ve 9'da "yazılan GB ücreti" yanlış gerekçesi düzeltildi (puan aynı). |
| R5 1 ms ve 2 ms sınırları sayfanın kendi ölçümüyle çelişiyor | kapandı | Kart 1 R1.4 gerekçesi: satır engine'in kendi süresini puanlar; AWS'e göre p50 1 ms'nin altındadır; Lale Market'in 1,3–1,8 ms ölçümü Python istemcisi ve TLS dahil uçtan uca süredir. |
| R6 Kart 7'de ElastiCache Valkey 9.0 kalıcılık seçeneği yok | kapandı | M2 girişine "kartlardaki ElastiCache adayı Serverless'tır" cümlesi eklendi. Kart 7'nin ElastiCache kafa kafaya paragrafı node'lu Valkey 9.0 senkron kalıcılığını puanlar: R3 tam olur ama R4–R5 MemoryDB'ninki gibi olur, sonuç DynamoDB'nin gerisinde kalır. |
| R7 Kart 7'de süreli kilit DynamoDB'de de tam bir kez değil | kapandı | Kart 7'nin kararına eklendi: hangi servis seçilirse seçilsin süreli kilit takılan worker'dan sonra ikinci worker'a geçebilir; ödeme talimatı her durumda satıcı ve gün başına benzersiz id ile koşullu yazılır (B8). Puan değişmedi, çünkü bu her aday için aynıdır; TA satırı kilidin alınmasının atomikliğini puanlar. |
| R8 Kart 8'de list puanlanıyor, stream değil | kapandı | Kart 8'de ElastiCache ve MemoryDB consumer group'lu stream ile puanlandı: R1.2 8 (XAUTOCLAIM uygulama işi), R1.3 6 (teslim sayısı var, dead-letter taşıması yok). ElastiCache 81,5, MemoryDB 77,5, SQS 97; R1 farkı 7. Key satırı, kafa kafaya, karar, checkpoint ec-a2, terim tablosu ve B7'deki kod (XAUTOCLAIM satırı) güncellendi. |
| R9 Boyutlandırma birden fazla satırda | kapandı | Timestream ve OpenSearch R2 gerekçeleri yalnız tepe anındaki yarışı sayar, boyutlandırma R4'te kalır (OpenSearch R4 gerekçesine node sayısı ve tipi eklendi). Kart 9 DynamoDB R2 gerekçesi on-demand'in bir önceki tepenin iki katına kadar uyumu olarak yeniden yazıldı. |
| R10 Fiyat R1'de ve iki kez | kapandı | R1'deki fiyat ifadeleri çıkarıldı: kart 3 DynamoDB R1.1 (koşulun hata yolu), kart 5 DynamoDB R1.1 (item'ın tamamını yeniden yazma), kart 1 DynamoDB R1.3 (fiyat R5'te), kart 2 DynamoDB R5 (sayım okumaları R1.1'de), kart 8 R5 (en az 100 MB). Puanlar aynı kaldı; kırılımın engine nedeni yazıldı. |
| R11 Kart 5'te sıcak key bölme ElastiCache'te bedelsiz | kapandı | Kart 5'in key satırı parçalamayı açıkça anlatır (<n>, 16 parça, ekran 16 hash'i toplar). ElastiCache R2 9'dan 8'e indi: bölme ve toplama işi orada sayıldı; DynamoDB'nin gerekçesi bölmenin orada partition sınırı yüzünden zorunlu olduğunu söyler. ElastiCache 90. |
| R12 Kart 4'te CloudFront yok; JOIN üç satırda | kapandı | Kart 4'ün Aurora kafa kafaya paragrafına CloudFront eklendi: sayfa herkese aynıysa ilk katman CDN'dir; bu kart uygulamanın okuduğu sayfa verisini ve CDN miss'lerini önbellekler. Aurora R1.3 gerekçesi JOIN'i R1.1'e bıraktı (7'den 8'e, Aurora 74,5). |
| R13 A10 matrisi ile kartların R1'i çelişiyor | kapandı | A10 matrisinin altına not eklendi: MemoryDB'nin ½'leri engine farkı değil, log ve kayıt olmasından gelen servis farkıdır; bu yüzden M2'de R1 eşittir. |
| R14 R3–R5 ağırlık gerekçesi ağırlık kuralıyla çelişiyor | kapandı | Callout yeniden yazıldı: R3–R5 çoğu kartta R1'den hafiftir, ağırlığı her kartta iş yükünün önceliği belirler; dayanıklılık bir iş kuralıysa R3 R1'in her alt maddesinden ağır olabilir (kart 7, R3 30); R1 grup olarak en ağırdır. |
| R15 Kart 6 DynamoDB zinciri altı satırda | kapandı | Kart 6'da DynamoDB zinciri artık aday değil (R1'deki SNS değişikliği). |
| R16 Kart 7 R5 ağırlığı hikâyeyle uyuşmuyor | kapandı | Kart 7'de R4 15, R5 5 oldu; R5'in gerekçesi "maliyet önemsiz"dir ve "yeni sistem" yalnız R4'te sayılır. MemoryDB 90. |
| R17 Kart 9 MemoryDB gece yazma iddiası kanıtsız | kapandı | Gerekçe yeniden yazıldı: gündüz okumaları etkilenmez; pencere ancak daha çok paralel bağlantı ve pipeline ile tutar ve yük testiyle doğrulanmalıdır. Puan DynamoDB sayfasındaki aynı kartla aynı kaldı. |
| R18 Terimler tanımdan önce | kapandı | Engine App A1'de, pipeline ve GETEX katalogda (A5, B5), ZREMRANGEBYSCORE kart 10'da, Redshift kart 5'te ilk kullanımda açıklandı; {n} kaldırıldı; "kırılım" ağırlık paragrafında tanımlandı. Başlıktaki İngilizce satır ("Flash deal and live data", "ACL user") ortak çerçevenin index verisinden gelir; ortak parça olduğu için bu sayfada değiştirilmedi. |
| R19 A4 altyazısında kaçışlı HTML | kapandı | A4 altyazısındaki <b> etiketi kaldırıldı; render edilen sayfada kaçışlı etiket yok. |
| R20 Cevapsız "ya şöyle olursa" durumları | kapandı | (a) kart 3 kararına fail-open / yerel sınır kararı; (b) INCR ve EXPIRE tek MULTI/EXEC'te (kart 3 R1.3); (c) kart 2 kararına aylık key ve eski aya süre; (d) kart 9 kararına sürüm key'i ile yarıda kalmaya karşı yükleme; (e) M5'e Global Datastore satırı (iki ek Region, AWS FAQ ve features sayfası). |
| R21 İki kararın koşul cümlesi zayıf | kapandı | Kart 5'in kararı üç koşulu birlikte verir ve tek koşulun farkı kapatmadığını söyler; kart 10'un kararı iki koşulu birlikte verir (konum sıklığı ve kampanya aramalarının checkout tepesiyle çakışmaması). |
