# ElastiCache (TR) soğuk okuyucu raporu

Okunan sayfa: `/tmp/elasticache_tr_reader.html`. Sayfanın HTML metnini, `<details class="uc">` kartlarını ve 11 `application/json` simülasyon bloğunu okudum (5 karar simülasyonu ve 6 pratik simülasyonu).
Okuyucu profili: ElastiCache, Valkey ve Redis'i hiç kullanmamış biri.
Not: Sayfa gereksinimleri de "R1–R5" diye adlandırıyor. Karışmasın diye bu rapordaki bulgular **R1, R2, …** diye numaralı, sayfanın gereksinimleri ise "gereksinim R2" diye geçiyor.

---

## 1. Anlamadığım cümleler

**R1 — M2 `#usecases`, kart 1, gereksinim R2.** "1 ms ile 5 ms arasındaki fark, ürün sayfasının toplam süresinin yüzde 5'idir."
Yüzde 5 sonucu, sayfanın toplam süresinin 80 ms olduğunu varsayıyor. 80 ms sayfanın hiçbir yerinde geçmiyor.
Beklediğim: "ürün sayfası toplam X ms sürer" bilgisi, ya da bu cümlenin hiç olmaması.

**R2 — A10 `#summary`, checkpoint cevabı.** "Ö7'nin kalıcı biçimi gerekir."
Sayfa Ö7'yi "kopyalama asenkron olduğu için son yazmalar kaybolabilir" diye tanımlıyor. Bu tanımla "Ö7'nin kalıcı biçimi" çelişiyor. Kalıcı log Ö1–Ö8 listesinde ayrı bir özellik değil.
Beklediğim: Ö7'nin iki biçimi açıkça yazılmalı (asenkron replica ve kalıcı log). Ya da kalıcı log ayrı bir satır olmalı.

**R3 — A6 `#expiry`, TTL kavram kartı.** "'The expire error is from 0 to 1 milliseconds': süresi dolmuş bir key bir okumada görünmez."
Alıntı bir hata payından söz ediyor. Ondan sonraki sonuç ise kesin bir söz veriyor. Arada mantık bağı kurulmamış.
Beklediğim: "süre en fazla 1 ms geç uygulanır; okumada store süreyi kontrol eder, bu yüzden key görünmez."

**R4 — B4 `#slotsb` ve C3 `#lalemarket`.** "ElastiCache Serverless'ta uygulama shard'ları görmez … proxy katmanı her komutu doğru cache node'una gönderir" diyor, ama hemen ardından "Engine App Python'daki RedisCluster istemcisiyle bağlanır; istemci slot hesabını kendisi yapar" diyor.
Proxy topolojiyi gizliyorsa istemci neden slot hesaplıyor? İstemcim cluster istemcisi mi olmalı, yoksa sıradan bir istemci de olur mu?
Beklediğim: Serverless'a hangi tür istemcinin bağlanacağını ve nedenini anlatan tek bir cümle.

**R5 — C2 `#service`, "Serverless ile node'lu cluster arasında nasıl seçerim?"** Sayfa AWS'ten şunu alıntılıyor: "We recommend creating serverless caches … better fault tolerance". Aynı sayfa B8 ve M5'te kalıcı log'un sadece node'lu Valkey 9.0'da olduğunu söylüyor.
Okuyucu olarak "dayanıklılık için Serverless mı, node'lu mu?" diye kaldım.
Beklediğim: "fault tolerance (kesinti kısalığı)" ile "durability (onaylanan yazmanın kaybolmaması)" arasındaki farkı açıkça yazan bir cümle.

**R6 — C2 `#service`, görsel açıklaması.** "Okun üzerinde bir onay yoktur; kopyalama asenkrondur."
Bir diyagramdaki okun üstünde etiket olmamasından asenkron kopyalama sonucu çıkmaz. Bu cümle okuyucuya yanlış bir okuma yöntemi öğretiyor.

**R7 — M2 `#usecases`, kart 6, gereksinim R1.** "Mesajın sırası bir kanal içinde korunmalıdır." Zorunlu bir gereksinim bu, ama hiçbir adayın gerekçesi sıralamadan söz etmiyor.
Pub/Sub sırayı koruyor mu? DynamoDB Streams + Lambda koruyor mu? Puanlar bu konuda hiçbir şey söylemiyor.

---

## 2. Anlamını bilmeden karşılaştığım terimler

**R8 — Sayfa başı, A2, A10.** **Valkey** ne demek, hiç tanımlanmıyor. Başlık "Amazon ElastiCache (Valkey)". A10 "Valkey (Redis OSS ile uyumlu; Redis OSS de seçilebilir)" diyor. Redis'i hiç kullanmamış bir okuyucu Valkey ile Redis arasındaki ilişkiyi (çatallanma, aynı komutlar, lisans) ve neden Valkey seçildiğini öğrenemiyor.

**R9 — A4 `#slots` (ve M5'ten önceki bütün metin).** "**node'lu cluster**" ve "**node**" A4'teki bir FAQ'da ilk kez geçiyor ("Kendi çalıştırdığın ya da node'lu bir cluster'da"). Tanımı ancak M5 ve C2'de dolaylı olarak geliyor. "Serverless ile node'lu" ayrımı A bölümünün tamamında açıklanmadan kullanılıyor.

**R10 — A5 `#atomic`.** **Lua script'i (EVAL)** tablonun içinde ve Ö3'ün adında geçiyor, ama tanımı hiçbir yerde yok. Script nerede yazılır, nasıl gönderilir, ne kadar uzun olabilir: bunlar yok. Aynı tabloda `SET lock:payout worker-A NX PX 900000`: **PX** (milisaniye cinsinden süre) açıklanmıyor. EX, B2'de açıklanıyor.

**R11 — A3 `#types`.** **BLMOVE** ilk kez A3 tablosunda geçiyor. Açıklaması B7'de geliyor.

**R12 — M1 `#signals`, Ö6 bloğu.** "saniyede 30.000 **ECPU**" geçiyor ama ECPU'nun tanımı M2'deki terim tablosunda ve B9'da. Aynı yerde Ö1 bloğu **DAX**'tan söz ediyor, onun tanımı da M2'deki terim tablosunda.

**R13 — M2, kart 7.** "**fencing token**" ve "**idempotent**" tanımsız. Kilit kartının bütün dersi bu iki kavrama dayanıyor.

**R14 — A8, B1, C1–C3.** Tanımsız altyapı terimleri: **WebSocket** (A8), **TLS**, **VPC / subnet / security group**, **ACL** (sayfa başındaki "Kimlik doğrulama: Password (Secrets Manager, ACL user)" satırında ve C1'de), **AOF** (C2 tablosu: "AOF açabilirsin"), **SLA** (M1 Ö7). Bunlardan AOF içeriğe en çok etki ediyor, çünkü kalıcılık karşılaştırmasının bir parçası.

**R15 — A4 `#slots`, görsel; A9 `#replicas`, görsel.** "**cluster mode disabled**" yalnızca görselde ve açıklamasında geçiyor. Metin sadece cluster mode'u tanımlıyor. Cluster mode kapalı bir kurulum ne zaman var, Serverless'ta seçilebilir mi: bunlar yok.

**R16 — M2, kartlar 1 ve 4.** "**global table**" (DynamoDB) tanımsız. Ayrıca terim tablosunda yok.

**R17 — B1 `#names`, M2 kart 2, M6.** "**ElastiCache Engine App**", "**Admin Console'daki Seed**", "**Live leaderboard sayfası**" workshop'a özgü isimler. İlk geçtikleri yerde ne oldukları söylenmiyor.

---

## 3. "Ya … olursa?" sorularım, sayfanın cevaplamadığı durumlar

**R18 — A6 `#expiry`, B5 `#expiryb`.** **ElastiCache Serverless hangi eviction politikasını kullanıyor, değiştirebilir miyim?** Sayfa node'lu cluster'larda varsayılanın volatile-lru olduğunu ve bunun parametre ile değiştirildiğini söylüyor. Lale Market'in kullandığı Serverless için bunu hiç söylemiyor. Oysa A6'daki örnek tam olarak "süresiz lm:leaderboard yanlış bir politikayla silinebilir" riski.

**R19 — A9 `#replicas` / C2 port tablosu.** **Süresi dolmuş bir oturum 6380 portundan (replica) okunursa ne olur?** A6, kopyaların süreyi kendileri uygulamadığını ve ana node'un silmesini beklediklerini söylüyor. Kart 1 "süresi dolmuş oturum asla okunmaz" diye 10 puan veriyor. Replica okumasında bu söz geçerli mi?

**R20 — M5 `#aws`, B8 `#failure`.** **Serverless'ta bir failover ne kadar sürer?** MemoryDB için "under 20 seconds" verilmiş. Serverless için sadece B8 simülasyonundaki "saniyeler içinde" var. Ayrıca kart 7'de MemoryDB için "birkaç saniyelik yazma kesintisi" deniyor, M5 ise 20 saniyeye kadar diyor.

**R21 — M2, kart 1 ve 4; M5.** **Uygulama birkaç Region'dan çalışırsa ne olur?** DynamoDB için global table bir "koşul değişseydi" nedeni olarak geçiyor. ElastiCache'in Region'lar arası bir seçeneği olup olmadığı hiç söylenmiyor, bu yüzden karşılaştırma tek taraflı kalıyor.

**R22 — A5 `#atomic`.** **MULTI/EXEC ve Lua, cluster mode'da farklı slot'lardaki key'lere dokunursa ne olur?** A5 bundan söz etmiyor. Kural yalnızca A4'te MGET için ve M1'de genel bir cümleyle veriliyor. (Bkz. R34: A5'in kendi örneği bu kurala takılıyor.)

**R23 — B5 `#expiryb`.** **lm:active sorted set'inden eski ziyaretçiler nasıl silinir?** Her sayfa `ZADD lm:active <şimdi> id` gönderiyor ve sorgu ZCOUNT ile yapılıyor. Silme (ZREMRANGEBYSCORE) yok. Set süresiz büyüyor mu?

**R24 — M2, kart 1, karar.** **Bütün cache bir süre erişilemezse oturumlara ne olur?** Kart "oturum bulunamazsa login'e yönlendir" diyor. Bu durumda bütün kullanıcılar aynı anda çıkış yapmış olur, ve sayfa bunu "kabul edilir ama istenmez" diye geçiyor. Kart 3 için fail-open önerisi var. Kart 1 için ise bir yedek plan (örneğin imzalı cookie) tartışılmıyor.

**R25 — M2, kart 4; A7.** **Kampanya akşamı cache soğuk başlarsa Aurora writer saniyede 6.000 JOIN'i kaç dakika taşır?** M4'ün ikinci sorusu tam olarak bunu sordurtuyor, ama kart bu soruyu cevaplamıyor (bkz. R41).

**R26 — M5 `#aws`, M2.** **MemoryDB'nin sunucusuz bir seçeneği var mı?** Bütün kartlarda MemoryDB'nin puanı "node'lu cluster" olduğu için gereksinim R4 ve R5'te kırılıyor. Okuyucu bunun her durumda doğru olup olmadığını bilemiyor.

---

## 4. İkna etmeyen karar gerekçeleri ve mimara sorum

**R27 — M2 `#usecases`, puan ölçeği; M7 simülasyonları.** Ölçek şöyle diyor: "Zorunlu bir gereksinimde 0 ya da 1 alan aday diskalifiye olur." Ama kartlarda zorunlu sınırı karşılamayan adaylar 5–7 alıyor:
- kart 1: DynamoDB, gereksinim R2 = 6 ("1 ms'nin altı … karşılanmaz")
- kart 3: DynamoDB, gereksinim R2 = 5 ve MemoryDB, gereksinim R2 = 6 ("2 ms sınırı … tutulamaz")
- kart 6: DynamoDB, gereksinim R2 = 7, oysa "olaylar saniyeler içinde gelir" ve sınır 500 ms
- kart 7: ElastiCache, zorunlu gereksinim R3 = 2

Bütün simülasyonlarda "diskalifiye: 0" çıkıyor. Kural hiç tetiklenmiyor.
Mimara sorum: "Zorunlu bir sınırı karşılamamak neden 0–1 değil de 5–7? Bu kural ne zaman uygulanıyor?"

**R28 — M2, kart 7 ve M7 ödeme kilidi simülasyonu.** Sonuç: ElastiCache 39 ile ikinci, MemoryDB 38 ile üçüncü. Kafa kafaya paragrafı ise MemoryDB için "ElastiCache'ten farklı olarak doğru bir cevaptır" diyor.
Toplam puan, zorunlu gereksinimi karşılamayan adayı doğru adayın önüne koyuyor.
Sorum: "Yanlış cevap neden ikinci sırada?"

**R29 — M2, kart 1.** Karar 43'e 42, yani bir puanlık fark ve gerekçesi "1 ms'nin altı". Sayfanın kendi canlı ölçümü ise ElastiCache için 1–2 ms (A1, M1 Ö1, C3; bkz. R35).
Sorum: "Ölçülen gecikme 1–2 ms ise ElastiCache bu zorunlu sınırı nasıl karşılıyor? Bu kart ElastiCache'i neden seçiyor?"

**R30 — M2, kart 9.** Karar şöyle bitiyor: "listelerin kaybı gerçekten önemsiz olsaydı ElastiCache tek başına seçilirdi." Ama gereksinim R3 zaten "Düşük: kaybolursa bir gün genel liste gösterilir" diyor.
Ayrıca ElastiCache'in R5 gerekçesi DynamoDB'nin okuma faturası için "belirgin yüksek" diyor, buna rağmen R5 farkı sadece 1 puan.
Kartın önerdiği çözüm ("ikisi birlikte") hiç puanlanmıyor ve maliyeti verilmiyor.
Sorum: "İki store birlikte kaç para tutar ve DynamoDB tek başına kaç para tutar?"

**R31 — M2, kart 4, ElastiCache gereksinim R3 = 9.** Zorunlu gereksinim R2 "Aurora writer'ının yükü kampanya akşamı normal günden fazla olmamalı" diyor. Soğuk cache ise saniyede 6.000 JOIN'in writer'a gitmesi demek. Bu durum için sadece 1 puan kırılıyor. Serverless'ta snapshot da kapalı.
Sorum: "Soğuk cache zorunlu gereksinim R2'yi bozuyorsa neden sadece 1 puan kırılıyor?"

**R32 — M2, kart 6, karar.** "Her olayın kesin işlenmesi gerekseydi DynamoDB Streams ya da bir Valkey stream'i seçilirdi."
A8 ve M3 ise kaybı kabul edilmeyen akışlar için SQS / Kinesis / MSK diyor. Kalıcı log olmadan Valkey stream'i de arızada kaybedebilir (A8 tablosu).
Sorum: "Kesin işleme gerekiyorsa Valkey stream'i nasıl bir cevap olabilir?"

**R33 — A1 `#why` FAQ ve A3 giriş cümlesi; M2 kartlar 3, 5, 7.** A1 şöyle diyor: "sayaç, sıralı liste ve kuyruk gibi value tipleri disk tabanlı bir key-value database'te yoktur." A3 şöyle diyor: "Disk tabanlı bir key-value database value'nun içine bakmaz."
Kartlarda ise DynamoDB UpdateItem ADD ile atomik sayaç yapıyor, kısmi değiştirme yapıyor ve koşullu yazma yapıyor. Okuyucu DynamoDB'yi A bölümünden yanlış tanıyor.
Sorum: "DynamoDB'nin sayaç ve koşullu yazması varsa, gerçek fark tam olarak hangi tiplerde (sorted set, HLL, list, geo)?"

---

## 5. TR / EN farkları ve sayfanın kendi içindeki çelişkiler

TR/EN karşılaştırması: **uygulanamaz** (sadece Türkçe sayfa var). Sayfanın kendi içindeki çelişkiler şunlar:

**R34 — A5 `#atomic` ve A4 `#slots`.** A5'teki MULTI örneği: "MULTI; DEL lm:deal; SET lm:deal:stock 0; EXEC: iki değişiklik birlikte görünür."
A4, B4 ve B4 simülasyonu ise lm:deal'i slot 3299'a, lm:deal:stock'u slot 1725'e koyuyor ve farklı slot'lara giden çok key'li komutun CROSSSLOT ile reddedildiğini söylüyor. B4 de "ElastiCache Serverless her zaman cluster mode'da çalışır" diyor.
Bu örnek Lale Market'in kendi cache'inde çalışmaz.

**R35 — M2 kart 1 / M1 Ö1 / A1 / C3.** Kart 1 ElastiCache için "1 ms'nin çok altı" diyerek gereksinim R2'ye 10 puan veriyor. Aynı sayfa canlı ölçümü "1–2 milisaniye" olarak veriyor (A1 "Bizim verimizde", M1 Ö1, C3). B1'deki komutlar 1,4 ms ve B2'dekiler 1,3–1,6 ms. Sayfanın kendi ölçtüğü değer, kendi koyduğu zorunlu sınırın üstünde.

**R36 — M2, kart 2.** "Tabloyu 300 ekran her 5 saniyede okur ve her müşteri kendi sırasını görür …: saniyede 3.000 okuma."
300 ekranın 5 saniyede bir okuması saniyede 60 okuma eder. 3.000 sayısının nereden geldiği (müşterilerin kendi sıra sorguları mı?) yazılmamış.

**R37 — M2, kart 5.** Key tasarımı şöyle: saat başına **tek bir hash** (`views:2026-10-28T14`), field ürün id'si. Bu tasarımda saniyede 50.000 artırmanın hepsi aynı key'e, dolayısıyla tek shard'a gidiyor.
Gereksinim R2 gerekçesi ise "tek bir key'e saniyede 25.000 artırma" diyor, yani yarısını hesaba katıyor. A4 ve B4 "tek bir sıcak key tek shard'a yüklenir; daha fazla shard yardım etmez" diyor.
Sayı yanlış ve sıcak key riski bu kartta hiç tartışılmıyor.

**R38 — B1 `#names`, Keyspace kavram kartı.** "lm: ile başlayan **altı** tür key vardır: kampanya, kampanya stoğu, oturumlar, sıralama, aktif ziyaretçiler, sipariş sayacı ve müşteri adları." Sayılan tür sayısı yedi.

**R39 — B3 `#structures`.** Q4 ve "öğretici tablo" aynı key'i kullanıyor: `lm:leaderboard`. Orada C00002 (Mert) 98.210,10 puanda ve tabloda 5 member var.
Aynı bölümde ve A3'te gerçek `lm:leaderboard`'da C00002 1.168.114,91 puanda ve ZCARD 994.
Okuyucu Q4'ü çalıştırmanın gerçek sıralamayı değiştirip değiştirmediğini ve öğretici tablonun hangi key'de durduğunu anlayamıyor.

**R40 — M2, kart 8.** Puan tablosu ve karar sırası şöyle: "ElastiCache 40, DynamoDB 37, MemoryDB 38". Diğer bütün kartlarda adaylar puana göre sıralı. Burada 37 puanlık aday 38 puanlığın önünde. Hangisinin "en yakın alternatif" olduğu belirsiz kalıyor.

**R41 — M4 `#questions` ve M2 kart 4.** M4 "cache boşken database bu yükü kaç dakika taşır?" sorusunu öğretiyor. Sayfanın tek cache-aside kartı bu soruyu cevaplamıyor (bkz. R25, R31).

**R42 — M2 kart 7, gereksinim R3 (MemoryDB) ve M5.** Kart 7 failover sırasında "birkaç saniyelik bir yazma kesintisi" diyor, M5 ise "typically … under 20 seconds" diyor (bkz. R20).

**R43 — A9 `#replicas`, "Kalıcı log" kavramı ve tablo.** Kavram kartı asenkron kalıcılıkta "son birkaç saniye kaybolabilir" diyor. Tablo, M5 ve B8 ise "up to 10 seconds" diyor. Küçük bir fark ama sayı bir yerde belirsiz, başka yerde kesin.

**R44 — C3 `#lalemarket`.** "B1–B5'teki canlı cevaplar bu yoldan 1–2 milisaniyede geldi." B1'deki ilk komut ise 300 ms sürdü (yeni TLS bağlantısı). Küçük bir tutarsızlık.

---

## 6. Ne görmem gerektiğini söylemeyen görsel açıklamaları

**R45 — A2 `#model`, hash table görseli.** Açıklama, görseldeki numaralı yerlere "slot" diyor ("sağdaki tek bir numaralı yere (slot) düşer"). Hemen sonra A4 "hash slot"u bambaşka bir kavram olarak tanımlıyor (16.384 parça, CRC16, shard).
Açıklama bu iki "slot"un aynı şey olmadığını söylemiyor. Okuyucu ikisini karıştırır.

**R46 — A1 `#why`, bellek hiyerarşisi görseli.** Piramidin tepesinde "cache" katı var (CPU cache). Açıklama bu "cache"in ElastiCache'teki "cache" kelimesiyle ilgisi olmadığını söylemiyor. Yeni okuyucu "ElastiCache en üst katta mı?" diye sorar.

**R47 — A4 `#slots`, node group görseli.** Görselde iki node group ve "Redis OSS Cluster" yazıyor, ama metin ve simülasyon üç shard kullanıyor. Açıklama görselin neden iki shard gösterdiğini ve "Redis OSS" ile "Valkey" arasındaki ilişkiyi söylemiyor.
Ayrıca açıklama primary ve replica'ya bakmayı söylüyor, ama bu kavramlar A9'da geliyor. Okuyucu o noktada neye bakacağını bilmiyor.

**R48 — A9 `#replicas`, "cluster mode disabled / enabled" görseli.** Açıklama iki tarafı tarif ediyor ama ne zaman hangisinin seçileceğini ve Lale Market'in Serverless cache'inin hangi tarafta olduğunu söylemiyor (B4'e göre her zaman "enabled"). Asenkron kopyalama sonucunun okun etiketsiz olmasından çıkarılması da yanlış bir okuma yöntemi (R6).

**R49 — C2 `#service`, Serverless mimari görseli.** Açıklama "'A' yazan node'lar aynı verinin kopyalarıdır" diyor, ama shard'ların görselde nerede olduğunu göstermiyor ("bu sağ kutunun içindedir" deniyor ve orada bitiyor). Ayrıca "Service VPC" ve "VPC Endpoint" terimleri tanımsız (R14).

---

## 7. Son soru: bu sayfadan sonra bir meslektaşıma anlatabilir miyim?

**ElastiCache mi, DynamoDB mi: büyük ölçüde evet.** Şu kuralları sayfadan çıkarabildim:
- Veri kaybolabiliyorsa ya da yeniden kurulabiliyorsa (oturum, rate limit, sıralama, kopya) ElastiCache: mikrosaniye, tam anında TTL, sorted set / HLL / list / geo, yoğun ve küçük yazmalarda daha ucuz.
- Veri resmi kayıtsa ya da kaybı para demekse (kilit, sipariş, ödeme) DynamoDB: koşullu yazma kalıcı, büyük ve soğuk veride daha ucuz.
- Kart 7 ve B8'deki kilit örneği bu ayrımı çok iyi gösteriyor.

Eksik olanlar:
- Gecikme iddiası sayfanın kendi ölçümüyle çelişiyor (R29, R35). "1 ms'nin altı" sınırı ayrımın ana gerekçesi olduğu için bu ayrımı savunmak zorlaşıyor.
- DynamoDB ile ElastiCache arasında **sayısal bir maliyet karşılaştırması yok**. B9 sadece ElastiCache için örnek veriyor. Kart 3, 5 ve 9'daki "belirgin pahalı" ifadeleri rakamsız (R30).
- DynamoDB'nin yetenekleri A bölümünde olduğundan az gösteriliyor (R33).
- DAX ile ElastiCache arasında ne zaman seçim yapılacağı tek cümleyle geçiyor (M1 Ö8, M5). Kaynak DynamoDB olduğunda hangisinin seçileceği bir kartla gösterilmiyor.
- Diskalifiye kuralı tetiklenmediği için toplam puanlar kararı her zaman açıklamıyor (R27, R28).

**ElastiCache mi, MemoryDB mi: kısmen.** Ana kuralı çıkarabildim: "onaylanan yazmanın kaybı kabul edilmiyorsa ve bellek hızı da gerekiyorsa MemoryDB; kayıp kabul ediliyorsa ElastiCache. Bunun bedeli tek haneli milisaniye yazma ve node-saat."

Eksik olanlar:
- **MemoryDB'nin kazandığı hiçbir kart yok.** On kartın hepsinde MemoryDB ikinci ya da üçüncü. "MemoryDB seçilirdi" durumları sadece varsayım olarak geçiyor (A10 checkpoint'indeki oyun, kartlardaki "koşul değişseydi" cümleleri). MemoryDB'nin kazandığı tek bir kart, kararı gösterirdi.
- **ElastiCache'in node'lu Valkey 9.0 kalıcılık seçeneği ile MemoryDB arasında ayrım yapılmıyor.** M5 birine "cache ile aynı cluster'da kaybı kabul edilmeyen veri", diğerine "cache + database yerine tek store" diyor. Bu iki tarif okuyucuya aynı şey gibi geliyor. Bu seçenek hiçbir kartta aday olarak da puanlanmıyor (örneğin kart 7'de).
- MemoryDB için fiyat (node-saat rakamı), sunucusuz seçenek olup olmadığı (R26) ve failover süresiyle ilgili tutarlı bir bilgi (R20, R42) yok.
- "Fault tolerance" ile "durability" arasındaki ayrım net değil (R5). Bu ayrım tam olarak ElastiCache Serverless ile MemoryDB arasındaki farkın kendisi.

---

## Özet: kategori başına bulgu sayısı

| Kategori | Bulgular | Sayı |
|---|---|---|
| 1. Anlaşılmayan cümleler | R1–R7 | 7 |
| 2. Tanımından önce geçen terimler | R8–R17 | 10 |
| 3. Cevaplanmayan "ya … olursa?" soruları | R18–R26 | 9 |
| 4. İkna etmeyen karar gerekçeleri | R27–R33 | 7 |
| 5. TR/EN farkı (uygulanamaz) / iç çelişkiler | R34–R44 | 11 |
| 6. Neye bakılacağını söylemeyen görseller | R45–R49 | 5 |
| **Toplam** | | **49** |

Önce kapatılması gerekenler: R34 (MULTI örneği CROSSSLOT'a takılıyor), R35/R29 (1 ms sınırı ile ölçülen 1–2 ms çelişiyor), R27/R28 (diskalifiye kuralı tetiklenmiyor, yanlış cevap ikinci sırada), R37 (kart 5'te sıcak key sayısı yanlış), R18 (Serverless eviction politikası), son sorudaki MemoryDB ile Valkey 9.0 kalıcılık seçeneğinin ayrımı.

---

## Yazarın kapatmaları (her bulgu: düzeltildi ya da neden kusur olmadığı)

Düzeltmelerden sonra: `check_usecases.py` usecases: OK, `clarity.py` clarity: OK, simülasyon testi TR `sim-errors []`, `jserr` boş.

| No | Durum | Ne yapıldı |
|---|---|---|
| R1 | Düzeltildi | Kart 1 gereksinim R2: "yüzde 5" cümlesi çıkarıldı; "1 ms ile 5 ms arasındaki fark her sayfaya 4 ms ekler" oldu. |
| R2 | Düzeltildi | A10 checkpoint açıklaması: Ö7'nin iki biçimi (asenkron replica ve kalıcı log, A9) açıkça yazıldı. |
| R3 | Düzeltildi | TTL kartı: "süre en fazla 1 ms geç uygulanır; okumada store süreye bakar ve dolmuş key'i yok sayar". |
| R4 | Düzeltildi | B4: Serverless cluster mode'da çalıştığı için cluster mode'u destekleyen TLS'li bir istemci gerektiği, proxy'nin yeniden keşfi gereksiz kıldığı yazıldı. |
| R5 | Düzeltildi | C2 "Serverless mı node'lu mu" kutusu: fault tolerance ile durability ayrımı tanımlandı; kalıcılık için Valkey 9.0 ya da MemoryDB. |
| R6 | Düzeltildi | A9 görsel açıklaması: "okun üzerinde onay yok" çıkarımı silindi; asenkronluğun kaynağı Valkey belgesidir. |
| R7 | Düzeltildi | Kart 6 gereksinim R1'den puanlanmayan sıralama cümlesi çıkarıldı. |
| R8 | Düzeltildi | A1'e Valkey'in tanımı eklendi (Redis OSS'un çatalı, aynı komutlar; ElastiCache onu çalıştıran servis). |
| R9 | Düzeltildi | A4 Shard kartında "node" tanımlandı; A4 kutusunda "node'lu cluster" (Serverless'ın karşıtı) açıklandı. |
| R10 | Düzeltildi | A5 tablosu: Lua script'i bir cümleyle tanımlandı; PX (milisaniye, 900.000 ms = 15 dakika) açıklandı. |
| R11 | Düzeltildi | A3 tablosunda LPUSH, RPOP ve BLMOVE kısa açıklamalarıyla. |
| R12 | Düzeltildi | M1'de ECPU ve DAX ilk geçtikleri yerde açıklandı. |
| R13 | Düzeltildi | Kart 7'de fencing token ve idempotent tanımlandı. |
| R14 | Kısmen düzeltildi | WebSocket (A8), AOF (C2), SLA (M1) tanımlandı. TLS, VPC, subnet, security group ve ACL bu workshop'un genel altyapı terimleridir ve diğer tutorial'larda da tanımsız kullanılır; sözlük sayfası (/e2etutorial/glossary) onları taşır. Kusur sayılmadı. |
| R15 | Düzeltildi | A4 görsel açıklaması: cluster mode disabled'ın ne olduğu, sadece node'lu cluster'da seçilebildiği, Serverless'ın her zaman cluster mode'da olduğu. |
| R16 | Düzeltildi | M2 terim tablosuna global table (ve ElastiCache'in Global Datastore'u) eklendi. |
| R17 | Düzeltildi | M2 terim tablosuna Engine App, Admin Console, Seed, Live leaderboard eklendi. |
| R18 | Düzeltildi | A6 "Serverless'ta bellek dolar mı" kutusu: AWS'in Serverless belgesi seçilebilir bir maxmemory-policy listelemez; eviction sadece bir üst sınırda başlar; Lale Market'te üst sınır yok. |
| R19 | Düzeltildi | A9 kutusu: süresi saniyesinde önemli okumalar (oturum, kilit) 6379'dan; replica'lar silmeyi primary'den bekler. Kart 1'in oturumları 6379'dan okunur. |
| R20 | Düzeltildi | A9 soğuk cache kutusu: node'lu failover "usually takes just a few seconds", MemoryDB "under 20 seconds"; Serverless için AWS süre yayınlamaz. |
| R21 | Düzeltildi | Terim tablosu: ElastiCache'in çok Region'lı karşılığı node'lu Global Datastore'dur, Serverless'ta yoktur (AWS FAQ). |
| R22 | Düzeltildi | A5 MULTI kartı: cluster mode'da transaction ve Lua'nın bütün key'leri aynı slot'ta olmalı. |
| R23 | Düzeltildi | B5: lm:active member'ları kendiliğinden gitmez; workshop sıfırlaması siler, üretimde ZREMRANGEBYSCORE. |
| R24 | Kusur değil | Kart 1 gereksinim R3 bunu açıkça kabul eder ("bütün kullanıcıların yeniden login olması kabul edilir ama istenmez") ve puanı 5'e indirir; karar "oturuma kaybı kabul edilmeyen veri koyma" der. |
| R25 | Düzeltildi | Kart 4 R3 gerekçesi: stampede kilidiyle soğuk cache saniyede 6.000 JOIN değil, sıcak 50 ürün için birkaç saniyede yaklaşık 50 JOIN demektir. |
| R26 | Kusur değil | MemoryDB'nin AWS belgelerinde (What is MemoryDB, FAQ) bir sunucusuz biçimi anlatılmaz; sayfa MemoryDB'yi belgedeki gibi node'lu bir cluster olarak puanlar. |
| R27 | Düzeltildi | M2'ye ölçek notu eklendi: 0–1 "hiç karşılamaz" demektir; sınırı aşan ama işi taşıyan aday 5–7 alır. Kart 7'de ElastiCache R3 = 1 ve diskalifiye (DynamoDB sayfasının idempotency kartıyla aynı mantık). Kart 1, 3, 9'daki DynamoDB puanları DynamoDB sayfasıyla tutarlı kalmak için değişmedi. |
| R28 | Düzeltildi | Kart 7: DynamoDB 48, MemoryDB 38, ElastiCache R3'te diskalifiye (38). Yanlış cevap artık ikinci değil. |
| R29 | Düzeltildi | Kart 1 R2 gerekçesi: AWS'in ölçümüne göre Serverless'ta p50 okuma 1 ms'nin altında; Engine App'in 1–2 ms ölçümü Python istemcisini ve izleme kodunu içerir. A1 kavram kartı ve M1 Ö1 aynı açıklamayı kaynakla verir. |
| R30 | Kusur değil | Kart 9 DynamoDB sayfasındaki öneri kartıyla aynı puanları kullanır (tutarlılık şartı). Doğru cevap "ikisi birlikte"dir ve kart bunu söyler; iki servisin aylık fiyat karşılaştırması Bölge'ye ve sözleşmeye bağlıdır, bu sayfanın kapsamı dışında bırakıldı (B9 ElastiCache tarafının hesabını verir). |
| R31 | Düzeltildi | R25 ile aynı düzeltme. |
| R32 | Düzeltildi | Kart 6 kararı: kesin işleme için DynamoDB Streams ya da SQS; Valkey stream'i ancak kalıcı log'lu store'da (MemoryDB). |
| R33 | Düzeltildi | A1 kutusu ve A3 girişi: DynamoDB'de atomik sayaç ve koşullu yazma olduğu, eksik olanın sıralı küme, kuyruk, konum ve tekil sayım tipleri olduğu yazıldı. |
| R34 | Düzeltildi | A5 MULTI örneği hash tag'li key'lerle yeniden yazıldı ({lm:deal}:info, {lm:deal}:stock) ve CROSSSLOT nedeni açıklandı. |
| R35 | Düzeltildi | R29 ile aynı. |
| R36 | Düzeltildi | Kart 2: 300 ekran saniyede 60 okuma + müşterilerin kendi sıra sorguları saniyede yaklaşık 3.000. |
| R37 | Düzeltildi | Kart 5: saat hash'i 16 parçaya bölündü (views:<saat>:{0..15}); R1 1 puan kırıldı (16 HGETALL); R2 gerekçesi slot dağılımını ve en sıcak 10 ürünü anlatır. Toplam 44'ten 43'e. |
| R38 | Düzeltildi | B1: "yedi tür key". |
| R39 | Düzeltildi | Öğretici sıralama simülasyonu ve canlı deneme lm:tut:board key'ini kullanır; B3'te gerçek lm:leaderboard'a dokunulmadığı yazıldı. |
| R40 | Düzeltildi | Kart 8 adayları puana göre sıralandı: ElastiCache, MemoryDB, DynamoDB. |
| R41 | Düzeltildi | R25 ile aynı. |
| R42 | Düzeltildi | Kart 7 MemoryDB R3: "AWS'e göre planlanmamış failover genellikle 20 saniyenin altında". |
| R43 | Düzeltildi | Kalıcı log kartı: "AWS'e göre en fazla 10 saniye". |
| R44 | Düzeltildi | C3: ilk komutun 300 ms'si (yeni TLS bağlantısı) ayrıca belirtildi. |
| R45 | Düzeltildi | A2 hash table açıklaması: resimdeki "slot" ile A4'teki 16.384 parçalık slot'un farklı olduğu yazıldı. |
| R46 | Düzeltildi | A1 piramit açıklaması: "processor cache" ElastiCache'in cache'i değildir. |
| R47 | Düzeltildi | A4 görsel açıklaması: iki shard ile üç shard farkı, Redis OSS ile Valkey ilişkisi. |
| R48 | Düzeltildi | A9 görsel açıklaması: Lale Market'in Serverless cache'i sağdaki (cluster mode enabled) düzendedir. |
| R49 | Düzeltildi | C2 görsel açıklaması: Customer VPC, Service VPC ve VPC Endpoint tanımlandı. |
| Son soru: MemoryDB'nin kazandığı kart yok | Kusur değil (bilinçli) | On kart domain-map'in ElastiCache use case listesidir ve bu listede bellek içi kategorinin ilk seçim olduğu iş yükleri vardır. MemoryDB'nin kazandığı durum A10 checkpoint'inde (oyun puanları tek kayıt) ve kart 2, 3, 7, 8'in "hangi koşul değişseydi MemoryDB seçilirdi" cümlelerinde verilir; kart 7'de MemoryDB ElastiCache'in kaybettiği R3'ü kazanır. |
| Son soru: Valkey 9.0 kalıcılık ile MemoryDB ayrımı | Düzeltildi | M5 tablosu: Valkey 9.0 kalıcılığı ElastiCache'in node'lu cluster'ında bir özelliktir (asenkron seçeneğiyle); MemoryDB baştan kalıcı birincil database olarak tasarlanmış ayrı bir servistir. |

Açık bulgu yoktur.
