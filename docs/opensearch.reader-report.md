# Reader simulation: Amazon OpenSearch Service (opensearch), Türkçe sayfa, model 2

Tarih: 2026-10-31

Okur: daha önce hiç search engine kullanmamış, DynamoDB ve Aurora sayfalarını okumuş bir geliştirici. Kaynaklar: /tmp/os_reader/opensearch.tr.txt (baştan sona), /tmp/os_reader/page.html (görsel alt yazıları, kart tabloları, 12 simülasyonun JSON'u), canlı sayfa ve karşılaştırma için DocumentDB uc-search, Aurora uc-catalog, uc-reporting, uc-geo ve ElastiCache uc-geo kartları, decisions.md ve reader-questions.md bölüm 1.

## Genel izlenim

Bölüm A çok iyi okunuyor. Kitap dizini analojisi, altı document'lık öğretici index, canlı _analyze ve term cevapları ve "kulaklk" örneği search engine'i ilk kez gören biri için açık. Her kavramın "bütün durumlar" tablosu ve "Yapamaz" satırları soruların çoğunu önceden cevaplıyor. Aritmetik temiz: on kartın bütün hücreleri (puan × ağırlık / 10), R1 ara toplamları, toplamlar ve özet tablosundaki farklar doğru. Beş karar simülasyonunun son adımı kartlarla birebir aynı (84,4 / 77,6 / 85,6 / 84,8 / 87). Kart 2 DocumentDB sayfasının kart 8'iyle (uc-search) aynı satırları, ağırlıkları ve puanları taşıyor. OpenSearch ile OpenSearch Serverless'ın R1'i 5, 6 ve 8. kartlarda eşit.

Asıl sorunlar kartların içindeki tutarlılıkta. Lale Market'te zaten çalışan OpenSearch domain'i bazı kartlarda hesaba katılıyor, bazılarında katılmıyor ve kart 2'nin kazananı buna bağlı. Aynı mekanizma (nested field, type değişince reindex, "bu nokta hangi bölgede" sorgusu, refresh gecikmesi, kopyanın yeniden yüklenmesi) bu sayfada ve Aurora ile ElastiCache sayfalarında farklı satırlarda ve farklı puanlarla kırılıyor. Birkaç kartta aynı zayıflık iki satırda sayılıyor ve iki kartta açıklama metni tabloyla çelişiyor. Kartlarda tanımlanmadan kullanılan terimler de var (NextGen, Sigma, RAG, Lucene).

## Bulgular

### R1 (yüksek): Zaten çalışan OpenSearch domain'i kartların bir kısmında sayılıyor, bir kısmında sayılmıyor
Bölüm: M2 kart 2, 5, 7, 8 ve kart 3, 4, 9, 10; M6
Alıntı: Kart 3 R5 "Domain zaten ödenir; istek başına ücret yoktur." Kart 2 R5 "5 puan kırıldı: domain katalog cluster'ına ek olarak bütün gün çalışır." M6 "products (200 ürün, arama kutusu ve kategori sayıları)". Kart 7 R5 "birkaç GB'lık bir veri için üç node'luk bir domain ayda yaklaşık 440 dolar".
Tür: karar gerekçesi (reader-questions 1.4 ve 1.10)
Sorun: Kart 3, 4, 9 ve 10 kart 1'in domain'inin Lale Market'te çalıştığını kabul ediyor ve OpenSearch'e R4'te 7–9, R5'te 8 veriyor. Kart 2, 5, 7 ve 8 aynı şirkette domain yokmuş gibi puanlıyor. Kart 2 en açık örnek: M6'ya göre canlı domain kategori sayılarını zaten veriyor, ama kart 2 "ekip OpenSearch bilmiyor, ikinci bir sistem istenmiyor" diye R4 3, R5 5 veriyor. Domain kart 3'teki gibi sayılsaydı (R4 9, R5 8) OpenSearch 91,2 alırdı ve kartı kazanırdı. Kart 8 bunu bir koşul olarak yazıyor ("bu ekip tarafından zaten işletilseydi"), ama kart 2, 5 ve 7 hiçbir şey söylemiyor.
Mimara soru: Hangi kartlarda var olan domain sayılıyor ve neden? Kart 2'de "metin araması bir sonraki çeyrekte" deniyor; kart 1 ve M6'ya göre bugün çalışıyor. Hangisi doğru? Ekip farklıysa bunu her kartın hikâyesine yazmak gerekmez mi?

### R2 (yüksek): Nested field ve type değişikliği iki sayfada farklı kırılıyor
Bölüm: M2 kart 2 R1.1 ve R1.4; Aurora sayfası uc-catalog OpenSearch satırları; A2 type tablosu
Alıntı: Kart 2 R1.1 "iç içe field'lar da aynı biçimdedir (Ö2). Puan kırılmadı." Aurora uc-catalog R1.1 "2 puan kırıldı: mapping her alanın type'ını sabitler ve iç içe varyantlar nested sorgular ister." Kart 2 R1.4 (ŞE) "2 puan kırıldı: ... yanlış tahmin edilen bir type reindex ister." Aurora uc-catalog R1.2 (ŞE) "5 puan kırıldı: bir alanın type'ı değişirse ... index baştan kurulur (reindex)."
Tür: karar gerekçesi (aynı mekanizma, farklı kırılım)
Sorun: A2'ye göre "42 numara ve kırmızı aynı varyantta" sorusu için nested type gerekiyor. Kart 2'nin isteği de "iç içe olanlar dahil" filtre. Bu sayfa nested için puan kırmıyor, Aurora sayfası aynı mekanizma için 2 puan kırıyor. Type değişince reindex gerekmesi bu sayfada 2, Aurora sayfasında 5 puan kaybettiriyor ve iki kartın gerekçesi de isteklerin farklı olduğunu söylemiyor. DocumentDB uc-search aynı 10 ve 8 puanları kullandığı için fark üç sayfaya yayılıyor.
Mimara soru: Nested filtre ve nested aggregation ek bir sorgu ve mapping işi mi, değil mi? Değilse Aurora sayfası neden 2 puan kırıyor? Reindex riski kart 2'de neden 5 değil de 2?

### R3 (yüksek): "Bu nokta hangi bölgede" sorgusu bu sayfada tam puan, Aurora sayfasında 3 puan kırık
Bölüm: M2 kart 4 R1.1 ve R1.2; Aurora sayfası uc-geo R1.1
Alıntı: Kart 4 R1.1 "geo_distance filtresi, _geo_distance sıralaması, bir match sorgusu ve term filtreleri tek bir bool sorgusudur ... Puan kırılmadı." Aurora uc-geo R1.1 "3 puan kırıldı: 'bu nokta hangi bölgede' bölgeleri document olarak index'leyip ters bir sorgu ister".
Tür: karar gerekçesi
Sorun: Kart 4'ün isteği açıkça "bu adres hangi noktanın bölgesinde" sorusunu içeriyor. Aurora sayfası bunu ters sorgu diye cezalandırıyor, bu sayfa ise hiç anmıyor ve OpenSearch'e EY'de 10 veriyor. Kart 4 bir yakın yarış (fark 1,8). 3 puanlık bir EY kırılımı (5,4 katkı) Aurora'yı öne geçirirdi.
Mimara soru: Ters geo_shape sorgusu bir ek iş mi? Değilse Aurora sayfası neden kırıyor? Öyleyse kart 4'ün kazananı değişmez mi?

### R4 (orta): Refresh gecikmesi kartlarda farklı satırlarda ve bazen iki kez sayılıyor
Bölüm: R1 kataloğu (TA satırı); ElastiCache uc-geo; Aurora uc-catalog ve uc-geo
Alıntı: Katalog TA "arama bir refresh geriden gelir (A10)". ElastiCache uc-geo R1.1 "1 puan kırıldı: sonuç bir sonraki refresh'e kadar en yeni konumu görmeyebilir" ve R1.2 "2 puan kırıldı: refresh aralığı yüzünden '30 saniye' sınırı yaklaşık bir saniye geç uygulanır". Aurora uc-catalog R2 "refresh aralığı yüzünden yeni yazma kısa bir süre aramada görünmez". Aurora uc-geo R1.3 (DA) "konum güncellemeleri refresh aralığından sonra görünür".
Tür: karar gerekçesi (zayıflık bir kez sayılır kuralı)
Sorun: Aynı bir saniyelik refresh bir sayfada EY'de, bir sayfada DA'da, bir sayfada R2'de kırılıyor ve ElastiCache kartında iki R1 satırında iki kez sayılıyor. Sayfanın kendi kuralı ("Bir eksik yalnız bir satırda sayılır") ve kataloğun TA satırı bununla çelişiyor. Bu sayfanın kartlarında refresh hiç kırılmıyor.
Mimara soru: Refresh gecikmesi hangi katalog satırına ait (TA mı, OY mu)? Bir saniyelik gecikme hangi isteklerde puan kaybettirir ve kaç puan?

### R5 (orta): R3 kuralı (kopya ise 1 ya da 2 puan) tutarsız uygulanıyor
Bölüm: "OpenSearch'ün R3 puanı tek bir kurala uyar" paragrafı; kart 1, 2, 3, 4, 8; Aurora uc-catalog ve uc-geo
Alıntı: Kural "yükleme dakikalar sürüyorsa 1, saatler sürüyorsa 2 puan kırılır". Kart 1 R3 "2 puan kırıldı: ... bir saate yakın sürer". Kart 2 R3 "kataloğun tamamı yeniden index'lenir (saatler)". Kart 3 ElastiCache R3 "2 puan kırıldı: ... liste yeniden yüklenene kadar öneri yoktur". Kart 8 Aurora R3 "Üç AZ'de altı kopya. Puan kırılmadı."
Tür: karar gerekçesi
Sorun: (a) "Bir saate yakın" süre kurala göre dakikadır, ama 2 puan kırılıyor. (b) Kart 1 ve kart 2 aynı 200.000 ürünlük kataloğu anlatıyor; biri "bir saat", diğeri "saatler" diyor. (c) Kart 3 ve 4'te OpenSearch dakikalık yeniden yükleme için 1 puan, ElastiCache aynı dakikalık yeniden yükleme için 2 puan kaybediyor. (d) Kart 1 ve 8'de Aurora da bir kopya (kayıt DocumentDB'de ya da CMS'te), ama "kayıt sistemi olan Aurora" kuralıyla 10 alıyor. (e) Aurora sayfası, Aurora'nın kaydını tutan bir OpenSearch kopyasına 3 (uc-geo) ve 4 (uc-catalog) puan kırıyor, bu sayfanın kuralı en fazla 2.
Mimara soru: Kural yalnız OpenSearch için mi? Kopya tutan Aurora ve ElastiCache aynı kurala neden uymuyor? Kart 1'de "dakikalar" mı, "saatler" mi?

### R6 (orta): Aynı zayıflık bir kartta iki satırda sayılıyor
Bölüm: M2 kart 8 Aurora, kart 9 DocumentDB, kart 1 Aurora, kart 4 Aurora
Alıntı: Kart 8 Aurora R1.1 "3 puan kırıldı: iki sonucu tek bir sırada birleştiren formül ... SQL'de elle yazılır" ve R1.3 "3 puan kırıldı: iki skoru normalleştiren hazır bir araç yoktur; ağırlıklar sorgunun içinde yazılır". Kart 9 DocumentDB R1.1 "AWS'e göre text index yalnız İngilizceyi destekler" ve R1.2 "6 puan kırıldı: Türkçe kelime araması yoktur". Kart 4 Aurora R2 "yeni reader'ın eklenmesini dakikalarca bekler", R4 "kampanya için bir reader eklenir", R5 "kampanya reader'ı ... ödenir".
Tür: karar gerekçesi (reader-questions 1.4)
Sorun: Kart 8'de aynı "skorları elle birleştirme" eksiği EY'de ve AO'da toplam 6 puan kaybettiriyor. Kart 9'da Türkçe desteğin olmaması iki R1 satırında sayılıyor; ayrıca kart 9 Aurora R1.2 "Türkçe harf ve yazım hatası kuralları" diye kart 9'un hikâyesinde olmayan bir şey için puan kırıyor. Kart 1 Aurora R1.1 ve R1.3 "iki ayrı mekanizma" eksiğini iki kez sayıyor. Kart 4'te kampanya reader'ı R2, R4 ve R5'te sayılıyor (R5'teki fiyat kabul edilebilir, R4'teki değil).
Mimara soru: Kart 8'de EY ve AO hangi farklı iki eksiği ölçüyor? Biri kaldırılırsa Aurora'nın farkı 5'ten fazla olur ve "yakın yarış" etiketi düşer.

### R7 (orta): Kart 4'ün kafa kafaya metni tabloyla çelişiyor
Bölüm: M2 kart 4, "OpenSearch ile kafa kafaya, Aurora PostgreSQL"
Alıntı: "R4'te de küçük bir fark vardır: OpenSearch domain'i ve ekibin becerisi zaten vardır, PostGIS ise yeni bir beceridir."
Tür: anlaşılmayan cümle
Sorun: Tabloda iki aday da R4'te 7 alıyor (12,6 ve 12,6). Fark yok. Okur metne mi, tabloya mı inanacağını bilemiyor.
Mimara soru: R4 eşit mi? Değilse hangi puan değişiyor ve toplam ne oluyor?

### R8 (orta): Kart 10'un ağırlık notu tabloyla çelişiyor
Bölüm: M2 kart 10, "Ağırlıklar"
Alıntı: "R4 20 ve R5 18 R1'in her alt maddesinden hafif ya da eşittir"
Tür: anlaşılmayan cümle
Sorun: R1'in en ağır alt maddesi AO 18. R4 20 ondan ağır. Cümle yanlış. Kart 8'in notu ("R1'in her alt maddesinden ağırdır") doğru biçimdi.
Beklenen: "R4 20, R1'in her alt maddesinden ağırdır, ama R1 grup olarak en ağırdır" gibi tabloya uyan bir cümle.

### R9 (orta): Kart 9'da saatte 5.000 güncelleme için 3 puan kırılması orantısız
Bölüm: M2 kart 9 R1.3 (OY); A10 tablosu; ElastiCache uc-geo R1.3
Alıntı: "3 puan kırıldı: engine her güncellemede document'ı içeride baştan yazar ve yeniden index'ler; saatte 5.000 güncelleme segment birleştirme yükü üretir."
Tür: karar gerekçesi
Sorun: Saatte 5.000 güncelleme saniyede yaklaşık 1,4 güncellemedir. A10 ve M3 pahalı durumu "saniyede yüzlerce güncelleme" diye tanımlıyor. ElastiCache sayfası saniyede 800 yeniden index'leme için 6 puan kırıyor. Saniyede 1,4 güncellemenin ondan yarı kadar puan kaybettirmesi ölçeğe uymuyor. Kart 9'un istediği gecikme (bir dakika) refresh'in (1 saniye) çok üstünde.
Mimara soru: Saniyede 1,4 güncelleme bu domain'de ölçülebilir bir merge yükü mü? Puan sayıya bağlı değilse kırılım neyi ölçüyor?

### R10 (orta): Kart 5'te Serverless'ın alarmının nasıl kurulacağı açık değil
Bölüm: M2 kart 5 (Serverless R4, Karar); M7 checkpoint 2
Alıntı: "hata oranı alarmı ayrı bir yoldan (örneğin bir CloudWatch metric filter) kurulur". "Serverless seçersek hata oranı alarmını bir CloudWatch metric filter'ı ile kurarız."
Tür: eksik durum ("ya ... olursa?")
Sorun: Metric filter CloudWatch Logs'taki loglar üzerinde çalışır. Kartın hikâyesinde loglar boru hattıyla OpenSearch'e ve S3'e gidiyor, CloudWatch'a değil. Okur şunu soruyor: loglar CloudWatch'a da yazılacaksa ayda yaklaşık 760 dolar alma ücreti (aynı kartın CloudWatch satırındaki rakam) Serverless'ın R5'ine eklenmez mi? Eklenmeyecekse alarm hangi yoldan kurulur? Kafa kafaya bölümündeki "loglar önce CloudWatch'a yazılır, bir abonelik onları OpenSearch'e aktarır" cümlesinde de iki faturanın toplamı yok.
Mimara soru: Serverless kartında alarm yolu ve maliyeti tam olarak ne? Bu maliyet R5'te sayılırsa 4,6 puanlık fark kalır mı?

### R11 (orta): Kart 3'te completion suggester hiç anılmıyor
Bölüm: M2 kart 3 R1.2 (DA); A6 "öneki bulmanın yolları" tablosu
Alıntı: Kart 3 R1.2 "2 puan kırıldı: her tuş vuruşu skorlanan tam bir arama isteğidir; bellekteki bir yapıdan okumaya göre milisaniyeler fazladır." A6 "Completion suggester | Öneriler için bellekte duran özel bir yapı; çok hızlıdır."
Tür: karar gerekçesi
Sorun: A6, engine'in bellekte duran hızlı bir öneri yapısı olduğunu söylüyor. Kart 3 OpenSearch'ün DA puanını "bellekteki bir yapı yok" diye kırıyor ve ElastiCache'in DA üstünlüğünü bununla açıklıyor. Okur completion suggester'ın neden seçilmediğini (fuzzy desteği, filtre sınırı, popülerlik ağırlığı) bilmiyor.
Mimara soru: Completion suggester ve fuzzy birlikte DA'daki 2 puanı geri verir mi? Vermiyorsa neden?

### R12 (orta): Terimler tanımlanmadan kullanılıyor
Bölüm: A1, A6, A10, M2 (kart 3, 5, 6, 7, 8, 10), B3
Alıntı: "Fikirler her search engine'de aynıdır (Lucene, Elasticsearch, OpenSearch)"; "NextGen collection'lar 10 dakika boşta kalınca sıfır OCU'ya iner"; "destek asistanı (bir RAG uygulaması)"; "hazır Sigma kurallarıyla"; "Random Cut Forest ile"; "category ve city kırılım alanı (high cardinality)"; "reciprocal rank fusion"; "HNSW parametreleri (ef_search)"; "OpenSearch Dashboards'u önceki işinden biliyor"; "Grafana kullanır", "ajanlar (Telegraf)"; "OpenSearch sıralı token listesi üzerinde bir otomat çalıştırır"; A10 akışında "bellekteki tampon ve translog"; B3'te "k1 * (1 - b + b * dl / avgdl)"; "zero-ETL"; "Makalelerin kaynağı CMS'tir".
Tür: tanımlanmadan kullanılan terim
Sorun: Lucene hiç tanımlanmıyor; okur Elasticsearch, OpenSearch ve Lucene arasındaki ilişkiyi (kütüphane ve onun üzerindeki engine'ler) bilmiyor. NextGen ile NextGen olmayan collection farkı yok, ama kart 5 ve 8'in R2 ve R5 gerekçeleri ona dayanıyor. Sigma, RAG, Random Cut Forest, Dashboards, metric filter ve abonelik kart terimleri tablosunda yok. Translog, tanımından ("Aklına şu gelebilir") önce akışta geçiyor. B3'teki k1, b, dl, avgdl açıklanmıyor; okur tf'nin 0,4588 olduğunu doğrulayamıyor.
Beklenen: Bu terimlerin her biri için kart terimleri tablosunda ya da ilk geçtiği yerde tek cümlelik bir tanım.

### R13 (düşük): Domain maliyeti kartlar arasında farklı hesaplanıyor
Bölüm: M2 kart 5, 7, 8 R5; B6; M5 "Multi-AZ ve dedicated master"
Alıntı: Kart 5 "üç data node, üç master ve iki kopyalı 2,6 TB disk ... ayda yaklaşık 1.160 dolar". Kart 8 "üretim için üç AZ'lik bir domain ayda yaklaşık 440 dolardır". M5 "Üretimde her zaman" (üç master).
Tür: karar gerekçesi
Sorun: 440 dolar yalnız üç data node'dur (B6: "disk ve master hariç"). Kart 5 master'ları (yaklaşık 335 dolar) sayıyor, kart 7 ve 8 saymıyor; ama kart 8 "üretim için" diyor ve M5 üretimde üç master istiyor. Sıra değişmiyor, ama okur hangi rakamın doğru olduğunu bilemiyor.
Mimara soru: Kart 7 ve 8'deki domain master'sız mı düşünüldü? Öyleyse bunu yazmak gerekmez mi?

### R14 (düşük): Kart 5'te pano süresi ve CloudWatch fiyatı karışık
Bölüm: M2 kart 5, R1.4 isteği ve CloudWatch R5
Alıntı: R1.4 "Panolar dakikada bir 30 gün üzerinde çalışır". CloudWatch R5 "dakikada bir yenilenen 10 pano son saati her seferinde taradığı için ... (Frankfurt, 0,0063 dolar/GB)". Hikâye: "dakika başına hata oranını ve p95 gecikmeyi gece gündüz gösterir".
Tür: anlaşılmayan cümle
Sorun: Panolar 30 günü mü, son saati mi tarıyor? 30 gün olsaydı CloudWatch'un sorgu ücreti "birkaç bin" değil, yüz binler olurdu. Ayrıca parantezdeki 0,0063 dolar/GB, hemen önündeki "alma ayda yaklaşık 760 dolar" rakamına değil, sorgu ücretine ait (760 dolar = 1.200 GB × 0,63 dolar). Okur hesabı doğrulayamıyor.
Beklenen: Pano penceresi tek bir yerde ve alma ile sorgu fiyatı ayrı ayrı.

### R15 (düşük): Kart 1'in R5 gerekçesi hikâyeyle çelişiyor
Bölüm: M2 kart 1, OpenSearch R5
Alıntı: "Data node'lar saat başına ödenir; yük düz olduğu için node'lar boş durmaz."
Tür: anlaşılmayan cümle
Sorun: Hikâye "kampanya akşamı saniyede 300, normalde saniyede 30" diyor; R5 isteği de "Gün içinde düz, kampanya akşamı tepe". On katlık bir tepe varken yük "düz" değil; aynı satır "üç AZ'lik bir domain gece de çalışır" diye de kırılıyor.
Beklenen: Tepe için boyutlanan node'ların normal saatlerde ne kadar boş durduğunu söyleyen bir gerekçe.

### R16 (düşük): Kart 6'da Serverless'ın "ucuz katmanı" açıklanmıyor
Bölüm: M2 kart 6, Serverless R1.4 ve R5; M5; C2
Alıntı: Serverless R1.4 "eski veriyi index bazında siler ve ucuz katmana taşınır (Ö7)". R5 "eski veri warm katmanda ucuzdur". C2 "Alerting, Anomaly Detection, Security Analytics, ISM yok".
Tür: eksik durum
Sorun: Sayfa UltraWarm, cold ve ISM'i yalnız domain'e ait bir özellik olarak anlatıyor. Okur Serverless'ta eski verinin hangi mekanizmayla ucuz katmana geçtiğini bilmiyor (B6'da yalnız "time series için warm 0,026 $/GB-ay" fiyatı var). Ayrıca kart 6'nın R5'inde, kart 5'ten farklı olarak, hiçbir aylık rakam yok; 5,4 TB'lık bir yıl için iki modelin faturası karşılaştırılmıyor.
Mimara soru: Serverless'ta 91. günden bir yıla kadar veri nerede ve nasıl tutulur? İki biçimin yıllık faturası nedir?

### R17 (düşük): Kart 7'nin kafa kafaya metni farkın kaynağını eksik veriyor
Bölüm: M2 kart 7, "Timestream for InfluxDB ile kafa kafaya, CloudWatch"
Alıntı: "Timestream for InfluxDB'yi öne geçiren iki satırdır. R1 · YD ... R5"
Tür: karar gerekçesi
Sorun: Tabloda Timestream VM, EY ve YD'nin üçünde de CloudWatch'tan 1,4 puan önde; YD'nin VM ve EY'den farkı yok. Farkın büyük kısmı R5'te (5,4). "İki satır" demek okuru yanıltıyor.
Beklenen: "Farkın büyük kısmı R5'tir; R1'in üç satırında da 1'er puan önde."

### R18 (düşük): Katalog kodu yanlış satırda kullanılıyor
Bölüm: M2 kart 10 R1.3 (VM); kart 2 R1.2 (AO)
Alıntı: Kart 10 VM "1 puan kırıldı: mapping önceden tanımlanır; ödeme sağlayıcısı gibi yeni bir alan sonradan eklenir." Kart 2 AO "Seçenek sayıları her sayfada gösterilir."
Tür: karar gerekçesi
Sorun: Yeni bir alanın eklenmesi kataloğa göre ŞE'dir, VM değil. Facet sayıları bir erişim yolu ya da doc values (DA) işidir; katalog AO'yu "sıkılaştırma araçları" diye tanımlıyor. Okur kodun bir anlam taşıdığına inanıyor ve burada kafası karışıyor.
Beklenen: Kırılımın ait olduğu katalog satırı ya da bu kodun neden seçildiğini anlatan bir cümle.

### R19 (düşük): Beş shard'ın sıralamayı değiştirmesi bir "ya ... olursa?" sorusu bırakıyor
Bölüm: B2 "Önce tahmin et", B3, A5
Alıntı: "Skorların farkı shard'lardan gelir ... P0001 ve P0196 aynı skoru alır, çünkü aynı istatistikle hesaplanmıştır."
Tür: eksik durum
Sorun: Okur 200 ürünlük bir index'te aynı adların shard'a göre farklı skor aldığını öğreniyor ve şunu soruyor: bu üretimde sıralamayı bozar mı, ne yapılır? Sayfa çözüm vermiyor (tek shard ya da idf'i bütün shard'larda hesaplayan arama tipi). P0001 ile P0196'nın aynı shard'da olduğu da gösterilmiyor.
Beklenen: Bir cümlelik çözüm ve iki document'ın shard'ı.

### R20 (düşük): Token offset görselinin alt yazısı bitiş numarasını açıklamıyor
Bölüm: A3, "Let's contribute to OpenSearch!" görseli
Alıntı: "'contribute' 6'da başlar, 16'da biter."
Tür: görsel alt yazısı
Sorun: Görselde 16 numaralı karakter bir boşluk; "e" harfi 15'te. Bitiş numarasının son harften sonraki konum olduğu söylenmiyor, bu yüzden okur görsel ile alt yazının uyuşmadığını düşünüyor.
Beklenen: "Bitiş numarası son harften bir sonraki konumdur (15 'e', 16 boşluk)."

## Son soru

Kısmen evet. Bir meslektaşıma şunları anlatabilirim:
- **DocumentDB'ye karşı:** Metin araması (yazım hatası, Türkçe harf, relevance) isteniyorsa OpenSearch seçilir (kart 1, 9). Yalnız filtre ve facet isteniyorsa ve ekip MongoDB biliyorsa DocumentDB yeterli (kart 2). Ama kart 2'nin sonucu, Lale Market'te zaten çalışan domain'in sayılıp sayılmamasına bağlı (R1). Bu çözülmeden "kart 2'de neden DocumentDB" sorusunu savunamam.
- **OpenSearch Serverless'a karşı:** Engine aynı, R1 eşit. Alerting, Anomaly Detection, Security Analytics ya da ISM şartsa yönetilen domain; node işletmek istenmiyorsa ve trafik gece sıfıra iniyorsa Serverless (kart 5, 6, 8). Bu açık. Yalnız Serverless'ta alarmın yolu ve maliyeti (R10) ile ucuz katman (R16) eksik.
- **Timestream for InfluxDB'ye karşı:** Veri saf bir sayısal zaman serisiyse InfluxDB; metrikler logların içinden geliyorsa ve aynı panoda log araması isteniyorsa OpenSearch (kart 7). Kırılım başına normali öğrenmek gerekiyorsa OpenSearch'ün Anomaly Detection'ı (kart 10). Bu açık.
- **CloudWatch'a karşı:** Panolar sürekli yenileniyorsa ve kelime araması yapılıyorsa OpenSearch (tarama başına ödeme pahalı); aramalar seyrek ve id ile yapılıyorsa CloudWatch (kart 5). Binlerce kırılım varsa OpenSearch (kart 10). Mantık açık, ama kart 5'in rakamları (R14) ve CloudWatch ile birlikte çalışmanın maliyeti eksik.
- **Aurora PostgreSQL'e karşı:** Konum, metin ve filtre tek bir sıralı cevapta isteniyorsa OpenSearch (kart 4); küçük bir arama, veri zaten Aurora'da ve ekip ikinci bir servis istemiyorsa Aurora (kart 8). Ama kart 4'ün farkı küçük (1,8) ve Aurora sayfasıyla puanlama tutarsız (R3, R7). Kart 8'deki fark çift sayılan bir eksiğe dayanıyor (R6).
- **ElastiCache'e karşı:** Yazım hatalı önek, ikinci kelimedeki önek ya da popülerlik sırası isteniyorsa OpenSearch (kart 3). Konum saniyede yüzlerce kez değişiyorsa ElastiCache (ElastiCache kart 10). Bu açık, ama completion suggester'ın neden hesaba katılmadığı eksik (R11).

Eksik olan iki şey var. Birincisi, var olan domain'in hangi kartta ve neden sayıldığını söyleyen tek bir kural. İkincisi, OpenSearch'ün aynı mekanizmalarının (nested, reindex, ters geo sorgusu, refresh, kopyanın yeniden yüklenmesi) bütün sayfalarda aynı satırda ve aynı puanla kırılması. Bu ikisi olmadan yakın yarışları (kart 2 ve 4) savunamam.

## Kapanış (yazar)
| Bulgu | Durum | Ne yapıldı |
|---|---|---|
| R1 Var olan domain bazı kartlarda sayılıyor, bazılarında sayılmıyor | kapandı | Kural yazıldı ve sayfada bir callout oldu (mimar gözüyle, "Kartların başlangıç durumu"): kart 1, 3, 4, 9, 10 aynı Lale Market sistemini büyütür ve kart 1'in domain'i var sayılır; kart 2 DocumentDB sayfasının hikâyesidir ve kart 1'den önceki durumdur (domain yok, ekip OpenSearch bilmez); kart 5–8 başka ekiplerin sıfırdan işidir. Kart 2'nin ağırlık notu bunu söyler. Kart 2'de domain sayılsaydı sonuç değişirdi; bu, kafa kafaya paragrafındaki "bir koşul değişseydi" cümlesidir ve puanlar DocumentDB kart 8 ile aynı kalmak zorundadır. |
| R2 Nested ve type değişikliği iki sayfada farklı kırılıyor | kapandı (gerekçe) + sahibine not | Kart 2'deki iç içe field'lar (attributes.renk, attributes.garanti_ay) bir dizinin içindeki nesneler değil, tek bir gömülü nesnedir; OpenSearch object field'ları nested type olmadan düzleştirerek doğru sorar. Aurora uc-catalog'un VM satırı ise varyant dizisini ("42 numara ve kırmızı aynı varyantta") sorar ve nested ister; kırılım bu farktan gelir. Reindex kırılımı (2'ye 5) için iki kartın isteği farklıdır: kart 2 yeni filtre field'ını, Aurora kartı aylık yeni özelliklerin type'ını ve analizini sorar. Yine de Aurora sayfasındaki 5'lik kırılım bu sayfanın kuralına göre büyüktür; kabul edilmiş bir sayfanın puanı olduğu için değiştirilmedi ve hand-over'da sahibine açık bir tutarlılık notu olarak yazıldı. |
| R3 Ters geo sorgusu bu sayfada tam puan, Aurora sayfasında 3 kırık | kapandı | Kart 4'te "bu adres hangi bölgede" sorusu R1.2 (VM) satırının isteğindedir; OpenSearch VM 8'den 7'ye indi ve gerekçe ters sorguyu Aurora kart 10'daki aynı kırılım olarak adlandırır. Toplam OpenSearch 85,7, Aurora 84,9: kazanan değişmedi, yakın yarış 0,8 puana indi. Kafa kafaya paragrafı VM 10'a 7'yi ve ters sorguyu yazar. |
| R4 Refresh gecikmesi farklı satırlarda ve iki kez sayılıyor | kapandı (gerekçe) + sahibine not | Bu sayfada refresh hiçbir kartta puan kırmaz: her kartın isteği birkaç saniyelik görünürlüğe izin verir ve refresh R1 kataloğunda TA (tutarlılık) satırına yazılıdır. ElastiCache uc-geo'nun refresh'i EY ve YD'de iki kez sayması ve Aurora kartlarının onu R2 ya da DA'da sayması o sayfaların konusudur; kabul edilmiş sayfalar değiştirilmedi, hand-over'da sahibine tutarlılık notu olarak yazıldı. |
| R5 R3 kuralı tutarsız uygulanıyor | kapandı | (a) Kural "dakikalar 1, bir saat ve üstü 2" olarak yeniden yazıldı; kart 1'in gerekçesi "yaklaşık bir saat (bir saat ve üstü: 2 puan)" der. (b) Kart 2 DocumentDB sayfasının hikâyesidir (iç içe özellikli, 200.000 ürünlük gelecek katalog, "saatler"); kart 1 bugünkü katalogu ve bir saatlik yeniden kurulumu anlatır; iki hikâye farklıdır. (c) ElastiCache'in kopyası ElastiCache sayfasının kuralıyla puanlanır (soğuk ya da boş liste 2 puan); kural sayfadaki R3 paragrafına eklendi. (d) Aurora bir kopyayı tutsa da kopya üç AZ'de altı kopyadır ve AZ ya da node arızasında yeniden yükleme gerekmez; paragraf bunu söyler. (e) Aurora sayfasındaki 3 ve 4 o sayfanın kayıt sistemi isteğinden gelir; sahibine not. |
| R6 Aynı zayıflık bir kartta iki satırda sayılıyor | kapandı | Kart 8: Aurora EY 7'den 9'a çıktı, iki skoru birleştirmek yalnız AO'da sayılır (toplam Aurora 90,2). Kart 9: DocumentDB AO gerekçesinden Türkçe kırılımı çıkarıldı (EY'de sayılır), puan aynı (kalan eksikler 8 puanı taşır). Kart 1: Aurora AO gerekçesi yazım hatasını artık saymaz (EY'de sayılır), kırılım A-D ağırlıkları, eş anlamlı sözlüğü ve açıklama aracıdır. Kart 4: Aurora R2 tepeyi karşılamaktır, R4 reader'ı eklemek ekibin işidir, R5 fiyattır; decisions.md kural 3 bu ayrımı ister, çift sayım değildir. |
| R7 Kart 4 kafa kafaya metni tabloyla çelişiyor | kapandı | Kart 4 kafa kafaya metni: "R4'te iki aday eşittir (7'ye 7)" ve her birinin işi yazıldı. |
| R8 Kart 10 ağırlık notu tabloyla çelişiyor | kapandı | Kart 10 ağırlık notu: "R4 20 tek başına R1'in her alt maddesinden ağırdır, ama R1 grup olarak (42) en ağırdır". |
| R9 Kart 9 OY kırılımı orantısız | kapandı | Kart 9 OpenSearch OY 7'den 9'a çıktı (1 puan: saniyede yaklaşık 1,4 güncellemenin merge yükü); toplam 91,4. Aurora kafa kafaya metni 10'a 9 diyor; kaynak bloğunun mekanizma notu güncellendi. |
| R10 Kart 5 Serverless alarm yolu açık değil | kapandı | Kart 5'te Serverless'ın R4 gerekçesi, karar ve checkpoint os-a2: loglar CloudWatch'a gitmediği için metric filter yetmez; uygulamalar hata sayısını ayrıca bir CloudWatch metric'i olarak yayınlar ve alarm orada kurulur (ayda yaklaşık 0,30 dolar). |
| R11 Kart 3 completion suggester anılmıyor | kapandı | Kart 3 DA gerekçesi completion suggester'ı anar: daha hızlıdır ama yazım hatalı önekte ve filtrede sınırlıdır; yazım hatası ve popülerlik birlikte istendiği için öneri search_as_you_type ile skorlanan bir aramadır. Puan aynı (8). |
| R12 Terimler tanımlanmadan kullanılıyor | kapandı | Lucene A'nın girişinde tanımlandı; translog A10'un akış kutusunda; k1, b, dl, avgdl ve freq B3'te; OpenSearch Dashboards, RAG, Classic ve NextGen collection, Sigma ve Random Cut Forest M2'nin terim tablosunda. Metric filter kart 5'ten çıkarıldı. |
| R13 Domain maliyeti kartlar arasında farklı | kapandı | Kart 7 ve 8'in gerekçeleri artık "üç data node, küçük bir domain'de ayrı master yok, disk hariç, yaklaşık 440 dolar" der; kart 5 büyük log domain'i için üç master ve diski sayar. Fark bilinçlidir ve yazılıdır. |
| R14 Kart 5 pano süresi ve CloudWatch fiyatı karışık | kapandı | Kart 5: panolar dakikada bir son saat üzerinde, olay aramaları 30 gün üzerinde çalışır (DA ağırlık nedeni ve CloudWatch DA gerekçesi); CloudWatch R5 gerekçesi alma ücretini (0,63 dolar/GB) ve sorgu ücretini (0,0063 dolar/taranan GB) ayrı yazar. |
| R15 Kart 1 R5 gerekçesi hikâyeyle çelişiyor | kapandı | Kart 1 OpenSearch R5: gün içinde yük düzdür, kampanya tepesinin kapasitesi R2'de sayıldı. |
| R16 Kart 6 Serverless ucuz katmanı açıklanmıyor | kapandı | Kart 6 Serverless R5: time series collection'da eski veri warm katmana geçer (0,026 dolar/GB-ay, sıcak 0,36); aylık fatura domain'inkine yakındır, bu kartta R5 iki biçimi ayırmaz ve yarışı R4 verir (decisions.md kural 6'daki aylık rakam şartı R5'in karar verdiği yarışlar içindir). |
| R17 Kart 7 kafa kafaya farkın kaynağını eksik veriyor | kapandı | Kart 7 kafa kafaya: Timestream for InfluxDB R1'in üç alt maddesinde birer puan (toplam 4,2) ve R5'te öndedir; CloudWatch R2, R3, R4'te 6,8 puan geri alır; en anlamlı fark YD'dedir. |
| R18 Katalog kodu yanlış satırda | kapandı | Kart 10: yeni alan kırılımı VM'den çıkarıldı (OpenSearch VM 10, toplam 88). Kart 2'nin facet satırı DocumentDB kart 8 ile aynı iş yükü kuralı gereği aynı kalır; AO ("index tipleri ve araçlar") orada facet hesaplamasının engine aracını sorar ve iki sayfada aynıdır. |
| R19 Beş shard'ın sıralamayı değiştirmesi | kapandı | B2'nin "Önce tahmin et" cevabı çözümü verir: küçük index tek primary shard'la kurulur ya da sorgu search_type=dfs_query_then_fetch ile bütün shard'ların ortak istatistiğiyle skorlanır. |
| R20 Token offset görselinin alt yazısı | kapandı | Alt yazı: "contribute" 6 numaralı c'de başlar; bitiş numarası son harften (15 numaralı e) sonraki konumdur, yani 16, kelimeden sonraki boşluk. |
