# Soğuk okuyucu raporu: Amazon Keyspaces E2E (TR)

Okunan: `/tmp/keyspaces_tr.html` (tüm metin, 3 görsel, 9 simülasyonun JSON adımları). Okuyucu profili: Cassandra ve Keyspaces'i hiç kullanmamış, DynamoDB'yi adıyla bilen bir geliştirici.

Genel izlenim: Bölüm A çok iyi. Partition key, clustering column, token, tombstone ve TTL kavramları anlaşılır, tablolar "ya şöyle olursa?" sorularının çoğunu cevaplıyor. En zayıf yer M2/M7: puanlar birkaç yerde kartın kendi zorunlu gereksinimiyle çelişiyor. Keyspaces ile DynamoDB arasındaki farkların hiçbiri sayıyla verilmiyor.

## 1. Anlamadığım cümleler

| Bölüm | Alıntı | Beklediğim |
|---|---|---|
| üst bilgi | "35 dakika" | Sayfa 10 kart, 9 simülasyon ve 3 bölümden oluşuyor; 35 dakika gerçekçi değil. Ya süre "A için 35 dk" gibi bölüm bölüm verilmeli ya da daha uzun bir süre yazılmalı. |
| A2 `#model` | "en fazla 225 normal column'u değiştirir (TTL açıksa 166)" | TTL'in sınırı neden düşürdüğünü tek cümleyle açıklamak ya da bu satırı kaldırmak. |
| A4 `#tokens` | "Yazma ONE ya da ANY · 1 (ya da hiçbiri, sonra iletilir)" | "Sonra iletilir" ne demek (hint)? Bir yan cümleyle açıklanmalı. |
| A6 `#writepaths` | "1 Temmuz 2026'dan sonra asenkron çalışır" | Bugün bu tarih geçmiş mi, yoksa bu gelecekteki bir değişiklik mi? "Temmuz 2026'dan beri asenkron" gibi açık bir zaman ifadesi. |
| A7 `#expiry` | `8 gün önceki event \"Aktivitem\"de görünmez` | Ters bölü işareti sayfada görünüyor. Bu bir render hatası. |
| A7 `#expiry` / B5 | "silinen **ya da güncellenen** her KB için bir TTL delete" | Güncelleme de TTL delete harcıyor mu? Harcıyorsa kart 6'da dakikada bir yenilenen her durum ücretli olur. Bunu açıklayan bir cümle. |
| A7 akış şeması | "Sarı kutu ile kırmızı kutu arasındaki aralık" | A2'de "partition key sarı" kuralı konmuştu. Burada sarı "süre doldu" anlamında kullanılıyor ve renk kuralı bozuluyor. |
| M2 kart 2 R3, kart 3 R3 | "kabul edilmez değil ama istenmez" / "kabul edilmez değil ama ciddidir" | Çift olumsuz, iki kez okumak zorunda kaldım. "Kabul edilebilir ama istenmez" gibi düz bir cümle. |
| M2 kart 3, 6, 8, 9 | "Wide-column (Keyspaces) · **seçilen servis**" | Bu kartlarda Keyspaces kaybediyor ama yine "seçilen servis" deniyor. "Bu sayfanın servisi" ya da "değerlendirilen servis" demek. |
| M2 giriş | Terim listesi paragrafı ("on-demand ve provisioned mod … $lookup") | Tek paragrafta 20'den fazla terim var ve çoğu ileri bölümlere işaret ediyor. Liste ya da açılır sözlük olmalı. |
| M7 `#decide` | "yeşil 'eşleşti' önde olan adayı, 'sonuçta yeni' kazananı gösterir" | Puan hücrelerindeki "✓" işareti açıklanmıyor (JSON'a göre 8 ve üstü puan). R1 adımında iki aday birlikte "eşleşti" oluyor, R2'de tek aday. Ne zaman yeşil olduğu belli değil. |
| B2 `#reads` | "Sayfalama: Keyspaces bir sayfada okuduğu row sayısına ve 1 MB okuma sonrası sayfaya böler" | Cümleyi çözemedim. "Bir sayfa en fazla N row ya da 1 MB okumadır" gibi bir kural cümlesi. |
| B4 `#design` | "Son baktıkların (en yeni 8 görüntüleme) · LIMIT 40, uygulama view'ları ayıklar" | Kart 1 "en yeni 8 event" diyor, burada "8 görüntüleme" ve LIMIT 40 var. Hangisi doğru? 40 event'te 8 görüntüleme yoksa ne olur? |
| B3 sim (sepet) | "İstek 1 … SET qty = 6 IF qty <= 1" | Kural koşulu `<=` ile, ikinci istek ise `=` ile yazılmış. `SET qty = 6` sabit bir değer: qty 0 olsaydı 6 yazılırdı. Sim "aynı anda iki istek" diyor ama istek 1 yarış yüzünden değil kural yüzünden reddediliyor, yani eşzamanlılık gösterilmiyor. Kart 5'teki "IF qty <= 3" de aynı belirsizliği taşıyor: SET hangi değeri yazıyor? Artırma (qty + 2) LWT ile nasıl yapılır? |
| C3 `#lalemarket` | "Driver'ın varsayılan seviyesi LOCAL_QUORUM'dur" | B2 checkpoint'i "Son baktıkların" için LOCAL_ONE'ı doğru cevap sayıyor. Lale Market bugün hangisini kullanıyor? |

## 2. Anlamını bilmeden karşılaştığım terimler

| Terim | İlk geçtiği yer | Tanımlandığı yer |
|---|---|---|
| IAM role (SigV4) | üst bilgi | C3 (M2 girişinde kısa not var) |
| hash | A1 akış şeması | A4 (token) |
| Availability Zone / AZ | A4 Replica | hiç tanımlanmıyor |
| compaction | A6 Tombstone (sadece parantez içinde) | C1'de görev olarak geçiyor, tanımı yok |
| **repair** | M2 kart 2, 5, 10 (R4), M5 | C1 (sayfanın sonuna yakın) |
| nodetool | A4 | hiç tanımlanmıyor |
| SAI | A8 | açılımı hiç verilmiyor |
| commit log | A9 | hiç tanımlanmıyor |
| on-demand mod | M1 Ö2 | M2 girişi ve M5 |
| warm throughput / "önceden ısıtılır" | M1 Ö2, kart 1 | M2 girişi "C3" diyor, gerçek açıklama B5'te |
| idempotent | M1 Ö5 | B3 (idempotency) |
| bağlantı havuzu (connection pool), DataStax driver | kart 1, 2, 5 | hiç tanımlanmıyor |
| Spark Cassandra Connector, sessionization | kart 1, 7 | hiç tanımlanmıyor |
| p99, GB-ay, relevance, facet, outbox table, vacuum, streaming ingestion | M2 kartları | hiç tanımlanmıyor |
| RCU/WCU | M5 | Sayfanın geri kalanı RRU/WRU diyor; B2'de RCU ile ilişki kuruluyor ama terimler karışık |
| Engine App, seed işi | A7 checkpoint, B1 | hiç tanımlanmıyor (workshop iç terimleri) |
| shard (CDC), ARN, VPC interface endpoint, round robin | B5, C2, C3 | hiç tanımlanmıyor |
| frozen, timeuuid | B1 type tablosu | sadece tabloda geçiyor |

## 3. Cevabını bulamadığım "ya şöyle olursa?" soruları

- **A4 / M5, on-demand:** Trafik "daha önce ulaşılan seviyeyi" aşarsa Keyspaces ne yapar? Kart 7'de DynamoDB için "önceki tepenin iki katı" kuralı var, Keyspaces için böyle bir sayı verilmiyor. Uygulama hangi hatayı alır (throttling), driver yeniden dener mi?
- **A4, hot partition:** Bir partition 1.000 WRU'yu aşınca istemci ne görür? "Servis ikiye bölebilir" deniyor: bölme ne kadar sürer?
- **A4:** Yazma sırasında bir AZ düşerse ya da LOCAL_QUORUM sağlanamazsa uygulamaya ne döner?
- **A6:** Aynı row'a hem LWT hem normal yazma gönderilirse ne olur? Karışık kullanım güvenli mi?
- **A6 / A8, logged batch:** Batch zaman aşımına uğrarsa istemci ne görür? Yeniden denemeli mi?
- **A8 / M1 Ö7:** İkinci table geçmiş veriyle nasıl doldurulur (backfill)? Bunun aracı ya da maliyeti nedir? Sayfa "geçmişin doldurulması" diyor ama nasıl yapıldığını söylemiyor.
- **A9 / Ö8:** CDC'den Lambda'ya hiç yol yok mu (örneğin KCL'yi Lambda'da çalıştırmak ya da Kinesis üzerinden geçmek)? Kart 3, 6 ve 8'in kaybı bu cevaba dayanıyor.
- **A5:** Rapor için bütün table'ı dışa aktarmak gerekirse Keyspaces'te bir export özelliği var mı, yoksa sadece CDC ve Spark mı var?
- **M5, Multi-Region:** İki bölge aynı row'a yazarsa hangi yazma kazanır? LWT çok bölgede çalışır mı?
- **A2 / B1:** Keyspaces'te bir row 1 MB, DynamoDB'de bir item 400 KB. Bu fark ve partition boyutunun "pratikte sınırsız" olması bir seçim nedeni mi? Sayfa iki servisi bu açıdan karşılaştırmıyor.
- **Kart 10:** 40 TB veri, saniyede 30.000 yazma sürerken nasıl taşınır (araç, çift yazma, geçiş günü)? Kaynak cluster 3.11 değil de 4.x ya da 5.x olsaydı ne olurdu?
- **Kart 4:** 1 yıl tutulan bir denetim kaydı 40. günde yanlışlıkla silinirse ne olur? PITR sadece 35 gün geriye gidiyor.
- **B5:** Seed row'ları 2 Kasım'da kaybolunca B1'deki canlı örnekler ne olacak? Bu soru cevaplanmış. Ama sayfa bu tarihten sonra da yayında kalırsa okuyucu boş tablo görür.

## 4. İkna etmeyen karar gerekçeleri (M2 kartları ve M7 simülasyonları)

1. **Kart 1, R2 (zorunlu): "Kampanyadan önce kimse kapasiteyi elle büyütmek zorunda kalmamalı."** Kendi gerekçesine göre Keyspaces de DynamoDB de ilk kampanyada warm throughput ile önceden ısıtılmalı. Bu, zorunlu gereksinimi doğrudan çiğniyor, yine de iki aday 9 alıyor. *Mimara soru:* Bu zorunlu gereksinim karşılanmıyorsa neden 9 puan? Yoksa gereksinimin metni mi yanlış?
2. **Kart 1, R4 farkı (8 ve 6).** Üç kişilik uygulama ekibinin CQL ve driver öğrenmesi 2 puan kırdırıyor. İki kişilik veri ekibinin tek bir gece işini yeniden yazması 4 puan kırdırıyor. 44'e 43'lük kararın tamamı bu iki sayıya dayanıyor. *Soru:* Bu ağırlıklar nasıl seçildi? Ağırlıklar ters olsaydı DynamoDB kazanırdı; karar bu kadar kırılgan mı?
3. **Kart 2, R4.** Keyspaces'ten "aggregate yok, ortalamalar gece Spark işiyle hesaplanır" diye 1 puan kırılıyor. Oysa aynı cümle "planlanan bu" diyor ve DynamoDB'den aynı neden için puan kırılmıyor. *Soru:* Her iki adayın da yapamadığı bir şey neden sadece birinde sayılıyor?
4. **Kart 4, R1 (zorunlu): "Kayıt değiştirilemez olmalı."** A6, INSERT'in var olan row'un üzerine hata vermeden yazdığını öğretiyor. Yani bir denetim kaydı sessizce ezilebilir. Keyspaces R1'de 9 alıyor ve bu risk hiç anılmıyor (DynamoDB için de anılmıyor). *Soru:* Değiştirilemezlik nasıl sağlanıyor? IF NOT EXISTS mi, IAM ile UPDATE izni vermemek mi? Bunun maliyeti puana girmeli değil mi?
5. **Kart 6, R5: "Süresi dolan durumların silinmesi ayrıca ödenmemeli."** Keyspaces bu açık şartı çiğniyor (TTL delete ücretli), DynamoDB çiğnemiyor. Yine de ikisi de 7 alıyor. *Soru:* Keyspaces'in puanı neden daha düşük değil? Dakikada bir yapılan "güncelleme" de TTL delete harcıyor mu?
6. **Kart 8, R2 ve R3 (zorunlu).** Keyspaces "p99 10 ms için LOCAL_ONE seçilir, bir an önce yazılmış sinyal görünmeyebilir" diyor. Ama R3 "kaybolan bir 'şifre sıfırlandı' sinyali bir dolandırıcılığı gizler" diye zorunlu. Sayfa hiçbir yerde LOCAL_ONE'ın daha *hızlı* olduğunu söylemiyor, sadece daha ucuz olduğunu söylüyor. *Soru:* LOCAL_QUORUM 10 ms bütçesini gerçekten aşıyor mu? Aşmıyorsa dolandırıcılık okumasında neden eski cevap kabul ediliyor?
7. **Kart 10, R1 (zorunlu): "50 table'ın şeması … aynen çalışmalı."** İki table'da secondary index var ve Keyspaces CREATE INDEX desteklemiyor. Yine de R1 10 alıyor ("iki secondary index R4'te sayıldı"). TRUNCATE, UDF ve trigger kullanımı kontrol edilmemiş. *Soru:* Zorunlu bir gereksinimin açığı neden tercihli bir gereksinime taşındı? Şema "aynen" çalışmıyorsa R1 en fazla 7 olmalı değil mi?
8. **Kart 10, R5 = 9: "uzun süreli saklama ucuz olmalı".** 40 TB için ne Keyspaces'in ne de DynamoDB'nin GB fiyatı veriliyor. *Soru:* 40 TB Keyspaces'te ayda kaça mal oluyor, kendi işletilen Cassandra'ya göre fark ne?
9. **Bütün kartlar, R5.** Hiçbir kartta istek başına, GB başına ya da TTL delete başına fiyat yok. "TTL silmesi KB başına ölçülür" tekrar tekrar söyleniyor ama tutarı hiç söylenmiyor. *Soru:* Kart 6'da (günde 2 milyar yazma) fiyat farkı aylık kaç dolar?
10. **Kart 4, R5 (Keyspaces 6, DynamoDB 7).** DynamoDB'nin GSI'ı da her kaydı ikinci kez yazıyor ve saklıyor. 1 puanlık fark sadece TTL ücretinden mi geliyor? Bu açıkça söylenmeli.
11. **Kart 3, R1.** Keyspaces'teki "sil ve yeniden yaz" bedeli kırılıyor. Oysa DynamoDB'de GSI sort key'inin güncellenmesi de index'te bir silme ve bir yazma demek. Sadece "eventually consistent" diye 1 puan kırılıyor. Karşılaştırma eşit tutulmamış.
12. **M7 simülasyonları** kart verisini adım adım gösteriyor ama kartın sorunlarını da aynen taşıyor (yukarıdaki 1, 5, 6, 7). Simülasyon "hangi R kararı verdi?" diye sorduruyor; beş simülasyonun dördünde cevap aynı: R4. Tahmin etmenin öğretici bir değeri kalmıyor.

## 5. İngilizce sayfa

Sadece Türkçe sayfa verildi.

## 6. Neye bakılacağını söylemeyen görsel ve şema altyazıları

- **A4, coordinator görseli (keyspaces-coordinator.jpg):** Altyazı "kesikli oklar … partition'ın replica'larını tutan diğer node'lara" diyor. Görselde kesikli oklar *bütün* beş node'a gidiyor; RF 3 ile sadece ikisine gitmesi gerekirdi. Okuyucu hangi okların replica olduğunu çıkaramıyor. Yeşil ve turuncu düz okların (istek ve cevap) anlamı da altyazıda yok.
- **A4, node yerleşimi kutusu (node 0/1/2):** Altyazı iyi, ama "her node her partition'ın bir kopyasını tutar" cümlesi şemada görünmüyor. Sadece ilk replica çizilmiş, bu yüzden şema ile metin çelişiyor gibi duruyor.
- **A7, ömür akışı:** Altyazı sadece renkle işaret ediyor ("sarı kutu … kırmızı kutu"). Sarı, sayfanın kendi kuralına göre partition key'in rengi (bkz. 1. bölüm). Kutu adıyla işaret edilmeli: "süre doldu" ile "storage'dan silindi" arası.
- **M7 skor simülasyonları:** Gösterge "kilitli" ve "okundu ve atlandı" durumlarını listeliyor ama skor simülasyonlarında bunlar kullanılmıyor. "✓" işareti açıklanmıyor. Yeşil vurgunun neyi gösterdiği adımdan adıma değişiyor.
- **B5, CDC akışı (INSERT → stream → KCL → S3):** Altyazısı yok.
- **C2, serverless görseli:** Altyazı iyi ("kilitli oklar = TLS", "üç storage = üç kopya").
- **A4, Cassandra cluster görseli:** Altyazı yeterli.

## Son soru: Bir meslektaşıma Keyspaces'i DynamoDB yerine ne zaman seçeceğini ve nedenini anlatabilir miyim?

**Kısmen.** Sayfanın verdiği kuralı tekrarlayabilirim:
- "Veri modeli iki serviste aynı (partition key ile sort key ya da clustering column). Elinde çalışan CQL kodu, bir Cassandra cluster'ı, Spark Cassandra Connector işleri ya da CQL bilen bir ekip varsa Keyspaces'i seç, çünkü kod değişmez ve node işletmesi biter (kart 5, 10; kart 1, 2, 4, 7'de R4).
- Yeni bir projede, ekip CQL bilmiyorsa ya da değişikliklere Lambda ile tepki vermek gerekiyorsa DynamoDB'yi seç: Streams doğrudan Lambda'ya bağlanır, TTL silmesi ücretsizdir, GSI vardır, zero-ETL vardır (kart 3, 6, 8; M3; M4'ün 9. sorusu)."

**Eksik olan, yani savunurken takılacağım yerler:**
1. **Ekipten bağımsız teknik bir neden yok.** Sayfa M6'da kendisi kabul ediyor: CQL bilen ekip olmasaydı "DynamoDB de aynı derecede iyi olurdu". Sıfırdan başlanan bir projede Keyspaces'in kazandığı bir durum var mı? Birden fazla clustering column, type'lı şema, 1 MB row, sınırsız partition, okumada filtrelenen TTL, ücretsiz LWT, IN ile birden fazla partition okuma gibi farklar dağınık anlatılıyor ama hiçbir kartı tek başına kazandırmıyor. Bunları bir arada gösteren bir "Keyspaces ve DynamoDB" tablosu yok.
2. **Hiç fiyat yok.** RRU/WRU, GB-ay ve TTL delete'in birim fiyatı ya da örnek bir aylık hesap verilmiyor. Bütün R5 puanları bu yüzden doğrulanamıyor.
3. **Zorunlu gereksinimler tutarlı uygulanmıyor** (kart 1 R2, kart 4 R1, kart 10 R1). Yakın yarışlar 1–2 puanla kazanılıyor, bu yüzden bir meslektaş "puanlar keyfî" derse savunamam.
4. **CDC'den Lambda'ya tek yolun KCL olup olmadığı belirsiz.** Üç kayıp bu noktaya bağlı.
5. **Sayfa bir karar tablosu ya da akış vermiyor.** M4'ün 9. sorusu en yakın cevap. Ama "Cassandra kodu yok, ekip CQL bilmiyor, ancak X özelliği gerekli → yine de Keyspaces" türünden bir istisna hiç verilmiyor.

---

## Yazarın kapanışı (2026-10-29)

Her bulgu ya düzeltildi ya da neden kusur olmadığı yazıldı. Düzeltmelerden sonra: `check_usecases.py` → usecases: OK, `check_page.sh --tr` → clarity: OK, `t_page_keyspaces.py` TR → sim-errors [], jserr boş.

### 1. Anlaşılmayan cümleler

| Bulgu | Kapanış |
|---|---|
| "35 dakika" | Düzeltildi: `e2e/index.yaml` keyspaces süresi 60 dakika. |
| 225 / 166 column | Düzeltildi: TTL açık table'da her column ek süre bilgisi taşıdığı için sınırın 166 olduğu yazıldı (A2). |
| "sonra iletilir" | Düzeltildi: ANY ve hinted handoff yan cümlesi (A4 tablosu). |
| 1 Temmuz 2026 | Düzeltildi: "1 Temmuz 2026'dan beri asenkron" (A6, B3). |
| `\"Aktivitem\"` | Düzeltildi: düz tırnak (A7). |
| TTL delete ve güncelleme | Düzeltildi: A7 tablosu TTL'in sildiği ya da kısmen sona erdirdiği veri ile uygulamanın yeniden yazmasını ayırır; yeniden yazma normal bir yazmadır. |
| A7 renk dili | Düzeltildi: altyazı kutuları adıyla gösterir ("süre doldu", "storage'dan silindi"). |
| "kabul edilmez değil" | Düzeltildi: kart 2 ve kart 3 R3 düz cümle. |
| "seçilen servis" kaybedilen kartlarda | Kusur değil: etiket paylaşılan `usecase` macro'sunun ve `ui.yaml`'ın etiketidir (değiştirilemez, sadece eklenir); anlamı "bu sayfanın servisi"dir ve DynamoDB ile Aurora sayfalarında da kaybedilen kartlarda aynıdır. M2 girişi dört kaybı açıkça söyler. |
| M2 terim paragrafı | Kısmen: paragraf Aurora pilotundaki biçimle aynı kaldı; eksik terimler (bağlantı havuzu, Spark Cassandra Connector, sessionization, p99, GB-ay) eklendi. |
| M7 ✓ ve yeşil | Düzeltildi: M7 girişi ✓ = 8 ve üstü, ✗ = 0–1, yeşil = o ana kadar önde olan aday, kullanılmayan açıklama kutularını söyler. |
| B2 sayfalama cümlesi | Düzeltildi: "sayfa boyutu kadar row ya da 1 MB, hangisi önce; sayılan okunan row". |
| B4 "8 ve LIMIT 40" | Düzeltildi: kart 1 hikâyesi ve B4 aynı kuralı söyler (son 40 event'ten en yeni 8 farklı ürün görüntülemesi; azsa şerit kısa). |
| B3 LWT simülasyonu | Düzeltildi: simülasyon yeniden yazıldı; iki sekme qty = 2 okur, A `SET qty = 4 IF qty = 2` ile kazanır, B `SET qty = 5 IF qty = 2` ile reddedilir ve cevaptaki 4 ile kuralı yeniden test eder. Kart 5 kuralı da okunan değerle koşul olarak yazıldı. |
| C3 varsayılan seviye | Düzeltildi: Lale Market bugün LOCAL_QUORUM ile okur; B2 checkpoint'i bir iyileştirme önerisidir. |

### 2. Tanımsız terimler

| Terim | Kapanış |
|---|---|
| AZ, repair | Düzeltildi: A4 Replica kartında tanım (repair `dfn`). |
| compaction, nodetool, SAI, commit log | Düzeltildi: ilk kullanımlarında yan cümle tanımı (A6, A4, A8, A9). |
| on-demand, warm throughput (M1) | Düzeltildi: M1 Ö2'de parantez içinde tanım. |
| bağlantı havuzu, Spark Cassandra Connector, sessionization, p99, GB-ay | Düzeltildi: M2 terim paragrafına eklendi; kart 2'de bağlantı havuzu ayrıca açıklandı. |
| hash (A1) | Kusur değil: A1'deki kutu "etiketin hash'i: hangi makine bu grubu tutuyor?" der; A4 tanımlar. |
| IAM role (üst bilgi), Engine App, seed işi | Kusur değil: üst bilgi ve Engine App bütün workshop sayfalarının ortak çerçevesidir; seed işi B5 ve A7 checkpoint'inde bağlamıyla açıklanır. |
| idempotent, RCU/WCU | Kısmen: B2 tablosu RCU'yu RRU'nun provisioned karşılığı olarak tanımlar; idempotency B3'te örnekle açıklanır. |
| relevance, facet, outbox, vacuum, streaming ingestion, DataStax driver, frozen, timeuuid, shard (CDC), ARN, round robin | Kusur değil: alternatiflerin ya da ileri pratik terimleridir; cümlelerin anlamı onlarsız da kurulur ve her biri kendi tutorial'ında tanımlıdır. timeuuid ve frozen B1 tablosunda tanımlıdır. |

### 3. Cevapsız "ya şöyle olursa?" soruları

| Soru | Kapanış |
|---|---|
| On-demand önceki tepeyi aşınca | Düzeltildi (sınırla): M1 Ö2 bloğu belgenin bunun üstü için süre vermediğini ve ilk büyük tepe için warm throughput önerdiğini söyler; kaynakta olmayan bir sayı yazılmadı. |
| Hot partition'da istemci ne görür, bölme ne kadar sürer | Kaynakta yok: belge "may automatically split" der ve süre vermez; sayfa bu hedge'i korur ve tasarım önlemini (write sharding, B4) verir. |
| LOCAL_QUORUM sağlanamazsa | Kaynakta sayfa düzeyinde açıklama yok; A4 tablosu ALL satırında "bir replica düşerse istek başarısız olur" der; üç AZ'den biri düşerse LOCAL_QUORUM iki replica ile sürer. |
| LWT ve normal yazma karışık | Kısmen: AWS blogu LWT ve normal yazmanın birlikte kullanılabildiğini söyler; sayfa LWT'yi sadece gerçek bir kural için önerir (A6 ask). |
| Batch zaman aşımı, backfill aracı, export | Kapsam dışı: bunlar operasyon ayrıntılarıdır; A8 backfill'in bir maliyet olduğunu söyler, M2 kart 4 ve M1 Ö7 yeni sorunun bedelini sayar. |
| CDC'den Lambda'ya yol | Düzeltildi (sınırla): A9 ask ve M5 karşılaştırma tablosu, Keyspaces belgesinin Streams API ve KCL'yi gösterdiğini ve doğrudan Lambda tetikleyicisinin kaynaklarda olmadığını söyler. |
| Multi-Region çakışması | Kısmen: M5 aktif-aktif ve asenkron replikasyonu ve gecikmeyi verir; çakışma çözümünü servis üstlenir ("no longer have the difficult work of resolving conflicts"). |
| 1 MB ve 400 KB, sınırsız partition | Düzeltildi: M5'e "Keyspaces ve DynamoDB: ekipten bağımsız farklar" tablosu eklendi. |
| Kart 10'da 40 TB'ın taşınması, 4.x/5.x | Kapsam dışı: kart karar kartıdır; uyumluluk CQL 3.11 olarak verilir ve desteklenmeyen özellik listesi M5'tedir. |
| Kart 4'te 40. günde silinen kayıt | Düzeltildi: kart 4 R3 gerekçesi 35 günden eski kaybı CDC ile yazılan S3 arşivinin karşıladığını söyler. |
| Seed verisi kaybolunca | Cevaplandı (B5 ask). |

### 4. İkna etmeyen gerekçeler

| No | Kapanış |
|---|---|
| 1 (kart 1 R2) | Düzeltildi: gereksinim "node eklemek ya da sunucu büyütmek gerekmemeli; tek seferlik bir kapasite ayarı kabul edilir" oldu; iki adayın 9'u bununla tutarlı. |
| 2 (kart 1 R4 ağırlıkları) | Kusur değil, açıkça söylendi: kart bir yakın yarıştır ve kafa kafaya paragrafı "R4 tersine dönerse DynamoDB iki puan öne geçer" der. Kırılganlık kartın öğrettiği şeydir (M7 girişi). |
| 3 (kart 2 R4) | Düzeltildi: aggregate gerekçesi Keyspaces'ten çıkarıldı (iki adayda da yok); 1 puan driver ayarı içindir. |
| 4 (kart 4 değiştirilemezlik) | Düzeltildi: Keyspaces ve DynamoDB gerekçeleri değiştirilemezliği IAM izni ve IF NOT EXISTS / attribute_not_exists ile sağlar. |
| 5 (kart 6 R5) | Düzeltildi: Keyspaces R5 6'ya indi ("silme ayrıca ödenmemeli" şartı karşılanmaz); toplam 39. |
| 6 (kart 8 LOCAL_ONE) | Düzeltildi: kart 8'de okuma LOCAL_QUORUM (DynamoDB'de strongly consistent); A4 kartı LOCAL_ONE'ın daha hızlı ve erişilebilir olduğunu belgeyle söyler. |
| 7 (kart 10 R1) | Düzeltildi: hikâye secondary index, materialized view ve UDF kullanılmadığını (ekibin kontrol ettiğini) söyler; R4 bakım script'lerindeki TRUNCATE ve nodetool değişikliğini sayar. |
| 8, 9 (fiyat yok) | Kusur değil, açıkça söylendi: M2 girişi R5'in birim fiyat değil fiyat modelini karşılaştırdığını ve güncel fiyatın fiyat sayfasında olduğunu (link) söyler; Aurora sayfasıyla aynı karar. |
| 10 (kart 4 R5 farkı) | Düzeltildi: gerekçe 1 puanlık farkın TTL silme ücreti olduğunu söyler. |
| 11 (kart 3 GSI) | Düzeltildi: DynamoDB gerekçesi GSI'ın eski entry'yi kendisi silip yazdığını ve bunun R5'te sayıldığını söyler. |
| 12 (simülasyonlarda hep R4) | Kusur değil: bu, domain'in gerçek sonucudur (DynamoDB sayfası da aynı sonucu verir) ve M7 girişi bunu açıkça söyler; win ve lose simülasyonlarında kararı R1/R4 ve R5 birlikte verir. |

### 6. Görseller

| Bulgu | Kapanış |
|---|---|
| Coordinator görseli | Düzeltildi: altyazı yeşil ve turuncu okları, kesikli okların genel çizim olduğunu ve RF 3'te sadece üç replica'ya gidildiğini söyler. |
| Node yerleşimi | Kusur değil: altyazı sadece ilk replica'nın çizildiğini açıkça söyler. |
| A7 akışı | Düzeltildi (yukarıda). |
| M7 göstergesi | Düzeltildi (yukarıda). |
| B5 CDC akışı | Düzeltildi: altyazı eklendi. |

### Son soru

Düzeltildi: M5'teki yeni karşılaştırma tablosu ekipten bağımsız farkları (birden fazla clustering column, 1 MB row, okumada filtrelenen TTL, ücretli TTL delete, index yok, CDC tüketicisi, LWT kapsamı, zero-ETL) tek yerde verir ve hangisinin kimin lehine olduğunu söyler. Sıfırdan bir projede Keyspaces'i seçtirecek dürüst koşullar: 400 KB'ı aşan row'lar, çok seviyeli clustering sırası ve süresi dolan verinin okumada asla görünmemesi şartı; diğer durumlarda sayfa dürüstçe DynamoDB'yi önerir.
