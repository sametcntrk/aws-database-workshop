# Reader simulation: Amazon Timestream for InfluxDB (influxdb), Türkçe sayfa, model 2

Tarih: 2026-10-31

Okuyucu: daha önce hiç time series database ya da InfluxDB kullanmamış, biraz SQL bilen ve aynı sitenin DynamoDB ve Aurora sayfalarını okumuş bir geliştirici. Kaynaklar: `/tmp/ifx_page.txt` (baştan sona okundu), `/tmp/ifx_page.html` (kart tabloları, figcaption'lar, 9 simülasyon JSON'u), `http://localhost:8795/e2etutorial/influxdb` ve görseller (curl ile), `app/engine_app/e2e_usecases_w.py` içindeki `INFLUXDB_W` (sadece okundu), `decisions.md` ve `reader-questions.md` bölüm 1. On kartın bütün R1 ara toplamları, toplamları ve farkları elle yeniden hesaplandı. Kartlardaki ve beş M7 simülasyonundaki tablolar birbirini tutuyor. Sorunlar serbest metinde (kafa kafaya, M2 özeti) ve kartlar arasındaki tutarlılıktadır.

## Genel izlenim

Bölüm A çok iyi kurulmuş. Elektrik faturası analojisi, point'in dört parçası, sarı/mavi/gri renk düzeni ve "bütün durumlar" tabloları sayesinde time series fikrini sıfırdan anladım. A4 (shard group) ile A5 (önce zaman, sonra tag) en net bölümler. Simülasyonlar kartlarla birebir aynı (kart 1, 2, 3, 6, 9). aggregateWindow ve retention simülasyonlarının sayılarını elle doğruladım.

Beni en çok yavaşlatan dört şey oldu:
1. "Series key" kavramı üç yerde üç farklı biçimde tanımlanıyor.
2. Kart 2'nin kafa kafaya paragrafında bir sayı yanlış ve "en anlamlı fark" yanlış satırı gösteriyor.
3. Aynı zayıflık kartlar arasında farklı puanlanıyor: 2 milyon series kart 7'de dört satırda ceza alıyor, kart 9'da hiç almıyor. "Gece de çalışır" bir kartta 1, başka bir kartta 2 puan kırıyor. CloudWatch'un saklama kuralı ise puan ölçeğine uymuyor.
4. Kartlarda okuyucunun hiç görmediği iç kurallar ("Kural 7", "kural 13", "kademe") ve tanımsız terimler (TSI, stateDuration, Seed) geçiyor.

Sayfa sonunda Timestream for InfluxDB'yi ne zaman seçeceğimi çoğu rakibe karşı savunabiliyorum. Eksik kalanlar: CloudWatch'a karşı kırılma noktası (series sayısı), InfluxDB 3'ün aylık fiyatı ve kart 3'te InfluxDB 3'ün neden aday olmadığı.

## Bulgular

### R1 (yüksek): "Series key" üç yerde üç farklı tanımla geçiyor

- **Bölüm:** A3 Series kavram kartı; A6 "bütün durumlar: yazma yolları"; B1 renkli şema.
- **Alıntı:** A3: "Measurement, tag set ve field adı birlikte series key 'dir". A6: "Aynı series key ve aynı timestamp, başka bir field … İki field kümesini birleştirir". B1 şema başlığı: "Series key (field adı hariç)".
- **Tür:** anlaşılmayan cümle / kavram çelişkisi.
- **Sorun:** A3'e göre field adı series key'in parçası. O zaman A6'daki "aynı series key, başka bir field" satırı tanım gereği olamaz: başka bir field başka bir series key demektir. B1 ise field adını series key'den açıkça çıkarıyor, ama hemen altındaki metin series'i yine "…warehouse=IST-1 value" diye field adıyla yazıyor. A6'nın "aynı series key + timestamp bir point'i tanımlar" kuralı da bu yüzden belirsiz kalıyor: kart 4'teki kamyon point'i (üç field) bir point mü, üç point mü? Ben "series key = measurement + tag set" ve "series = series key + field adı" gibi iki ayrı terim bekliyordum. Bu ayrım bir kez yapılıp sayfa boyunca korunmalı. Simülasyon "Satırlardan series'lere" de A3'ün tanımını kullanıyor.
- **Mimara soru:** Sayfada "series key" field adını içeriyor mu, içermiyor mu? Kamyon point'i A6'daki "üzerine yazma" kuralında bir kimlik mi, üç kimlik mi?

### R2 (yüksek): Kart 2'nin kafa kafaya paragrafında yanlış sayı ve yanlış "en anlamlı fark"

- **Bölüm:** M2 kart 2, "Timestream for InfluxDB ile kafa kafaya, CloudWatch".
- **Alıntı:** "CloudWatch R2, R3 ve R4'te 6,8 puan geri alır. En anlamlı fark R1 · YD'dedir".
- **Tür:** karar gerekçesi / sayı tutmuyor.
- **Sorun:** Kart verisine göre CloudWatch'un R2'deki farkı 14 − 12,6 = 1,4, R3'teki 8 − 6,4 = 1,6, R4'teki 16,2 − 10,8 = 5,4. Toplam 8,4 eder, 6,8 değil. Kontrol: InfluxDB R1'de 4,2 ve R5'te 5,4 olmak üzere 9,6 önde. 9,6 − 8,4 = 1,2, bu da kartın farkıyla tutuyor. 6,8 ile hesap tutmuyor. Ayrıca YD farkı (12,6 − 11,2 = 1,4) VM ve EY farklarıyla aynı büyüklükte. En büyük fark R5'te (5,4). "En anlamlı fark R1 · YD" cümlesi tablodan çıkmıyor. Bu metin OpenSearch sayfasının 7. kartıyla ortak (`e2e_usecases_w.py` satır ~5079), bu yüzden hata iki sayfada birden var.
- **Mimara soru:** 6,8 hangi satırların toplamı? Kartı YD mi kazandırıyor, R5 (series başına fiyat) mı? YD 1 puanlık bir farksa "en anlamlı" neden o?

### R3 (yüksek): 2 milyon series kart 7'de dört satırda ceza alıyor, kart 9'da hiç almıyor

- **Bölüm:** M2 kart 7 (Timestream for InfluxDB R1.2, R1.4, R4, R5) ve M2 kart 9 (Timestream for InfluxDB, bütün satırlar).
- **Alıntı:** Kart 7 R1.4: "meter_id tag'i 2 milyon series doğurur; AWS'in boyutlandırma tablosu 1–5 milyon series için db.influx.4xlarge ve 12K IOPS storage önerir". Kart 9 R2: "Güçlü bir instance saniyede 65.000 point'i alabilir."
- **Tür:** karar gerekçesi / zayıflık her kartta aynı sayılmıyor.
- **Sorun:** Kart 9'da da iki milyon sayaç var. Her biri değer, pil ve durum gönderiyor. Cihaz id'si tag olursa 2 milyon ya da daha fazla series doğar. Bu, kart 7'deki durumun aynısı ve B5 tablosuna göre 4xlarge ile 12K storage ister. Kart 9'da cardinality ve instance sınıfı hiç anılmıyor. Ayrıca saniyede 65.000 point B5 tablosundaki large satırının (~50.000) da üstünde. Ters yönde de sorun var: kart 7'de aynı zayıflık (2 milyon series) R1.2'de (TSI büyük), R1.4'te (AWS tablosu), R4'te ("büyük bir instance boyutlandırılır") ve R5'te (4xlarge fiyatı) dört kez sayılıyor. reader-questions 1.4'e göre bir eksik bir kez sayılmalı.
- **Mimara soru:** Kart 9'da cihaz id'si tag mı? Tag ise 2 milyon series neden R1'de ve R5'te görünmüyor? Kart 7'de 2 milyon series'in cezası hangi tek satırda olmalı?

### R4 (orta): Kart 4 "yakın yarış" deniyor ama fark 6,4

- **Bölüm:** M2 kart 4: kafa kafaya, Karar, ayrıca M2 özet paragrafı.
- **Alıntı:** Kafa kafaya: "Bu bir yakın yarıştır ve iki aday aynı veri modelini…". Karar: "Yakın bir yarış: iki InfluxDB…". Özet: "son değer önbelleği ve SQL (kart 4, yakın yarış)".
- **Tür:** sayı tutmuyor.
- **Sorun:** Sayfanın kendi kuralı şöyle: "İlk iki aday arasındaki fark 5 puan ya da daha azsa kart 'yakın yarış' işaretini taşır". Kart 4'te fark 89,5 − 83,1 = 6,4. Kart başlığında ve özet tablosunda işaret yok, ama üç metin parçası karta "yakın yarış" diyor. Okuyucu olarak hangisinin doğru olduğunu bilemiyorum.
- **Mimara soru:** Kart 4 yakın yarış mı? Değilse metinler neden öyle diyor? Yakın yarışsa 5 puanlık eşik neden bu kartta geçerli değil?

### R5 (orta): CloudWatch'un saklama kuralı kartlarda farklı ve puan ölçeğine aykırı puanlanıyor

- **Bölüm:** Kart 1, 2 ve 5'te CloudWatch'un YD satırı; puan ölçeği tablosu; M2 özetinin son paragrafı.
- **Alıntı:** Ölçek: "0–3 Kısmen ya da hiç: satırın bir parçası karşılanmaz". Özet: "CloudWatch'un saklama kuralı istenen süreye göre 2, 4 ya da 5 puan (kart 2, 1, 5)".
- **Tür:** karar gerekçesi / sayı tutmuyor.
- **Sorun:**
  1. Kart 1'de CloudWatch YD 4 aldı, yani 6 puan kırıldı. Özet ise kart 1 için 4 diyor. Aynı paragraf Aurora ve Redshift için "kırılan puanı" yazıyor, bu yüzden 4 sayısı yanlış.
  2. Üç kartta da isteğin en az bir parçası karşılanmıyor. Kart 2'de 6 saatlik ham veri ve 30 günlük dakikalık veri, kart 1'de 30 günlük ham veri ve 2 yıllık özet, kart 5'te üç kademenin üçü de karşılanmıyor. Yine de puanlar 8, 4 ve 5. Ölçeğe göre üçü de 0–3 aralığında olmalı.
  3. Kart 5'te karşılanmayan kademe sayısı kart 1'dekinden fazla, ama kart 5 daha az ceza alıyor (5 kırık, kart 1'de 6).
- **Mimara soru:** "Satırın bir parçası karşılanmaz" için 0–3 kuralı CloudWatch YD satırlarında neden uygulanmadı? Kart 5'te üç kademenin üçü de kaçarken kırılan puan neden kart 1'dekinden az?

### R6 (orta): R1'de servis paketlemesi puanlanıyor, bazı zayıflıklar iki kez sayılıyor

- **Bölüm:** Kart 4 R1.3 (InfluxDB 2); kart 6 R1.2 (InfluxDB 2); kart 7 R1.4; kart 3 R1.3 (Keyspaces); kart 9 R1.2 ve R5 (InfluxDB 2).
- **Alıntı:** Kart 4 R1.3: "AWS'in boyutlandırma tablosu 100.000 series'e kadar db.influx.large önerir". Kart 6 R1.2: "veri instance'ın SSD'sindedir (en fazla 16 TiB)". Kart 9 R1.2: "series sürekli büyür ve bir retention politikası gerekir", R5: "sürekli büyüyen series için storage ödenir".
- **Tür:** karar gerekçesi (R1 sadece engine'i mi puanlıyor; zayıflık bir kez mi sayılıyor).
- **Sorun:** Sayfa R1 için "Multi-AZ, instance boyutlandırma, lisans, fiyat … R2–R5'e yazılır ve R1'de sayılmaz" diyor. AWS'in instance tablosu, 16 TiB disk sınırı ve "Keyspaces'te compression ayarı uygulanmaz" servis kararlarıdır, ama R1 gerekçelerinde geçiyorlar. Kart 9'da "series büyür" engine davranışı R1.2'de ve R5'te iki kez cezalandırılıyor. decisions.md kural 6'ya göre engine'in zorladığı ek veri R1'de sayılır ve R5'te yeniden kesilmez.
- **Mimara soru:** Bu R1 kırılımları servis paketlemesi çıkarılınca da geçerli mi, yani kendi sunucumdaki InfluxDB 2'de de aynı puanı alır mı? Kart 9'da storage büyümesi hangi tek satırın cezası?

### R7 (orta): "Gece de çalışan instance" kartlar arasında farklı fiyatlanıyor, karşılaştırma eksik

- **Bölüm:** Kart 1, 2 ve 3 R5 (2 puan kırık), kart 5 R5 (1 puan kırık), M2 özetinin "Fiyat (R5)" cümlesi.
- **Alıntı:** Kart 5: "düz yükte instance gece de çalışır ve bu iş yükü gece de çalışır. 1 puan kırıldı". Kart 1: "Multi-AZ db.influx.medium ayda yaklaşık 211 USD gece de çalışır". Kart 2: "yaklaşık 210 USD".
- **Tür:** karar gerekçesi / sayı.
- **Sorun:**
  1. Kart 1'deki sensörler 7/24 her 10 saniyede, kart 3'teki sensörler "günün her saati düz" yazıyor, yani bu iş yükleri de gece çalışıyor. Yine de bu kartlarda "gece de çalışır" 2 puan, kart 5'te 1 puan kırıyor. Özet bu farkı "yük düz ve gece de çalışıyorsa 1" diye açıklıyor, ama bu tanıma kart 1 ve 3 de uyuyor.
  2. Aynı instance kart 1'de 211, kart 2'de 210 USD.
  3. Kart 1'deki CloudWatch karşılaştırması (324 USD ve 211 USD) storage'ı dışarıda bırakıyor. Kart 1 ve 2'de R5 bir yakın yarışı belirliyor, ama fiyat cümlesinde tarih yok (Price List tarihi sadece M5 ve B5'te var).
- **Mimara soru:** Kart 1 ve 3'teki yük kart 5'tekinden neden daha "boşta"? Storage eklendiğinde kart 1'de CloudWatch'a karşı R5 farkı nedir? CloudWatch hangi series sayısında daha ucuz olur (kırılma noktası)?

### R8 (orta): Kart 3'te ağırlığın nedeni R2'de, cezası R3'te; InfluxDB 3 aday değil; kırılma koşulu iki yerde farklı

- **Bölüm:** M2 kart 3: Ağırlıklar, Keyspaces ile kafa kafaya, Karar.
- **Alıntı:** Ağırlıklar: "R2 18 ile ikinci: sensörler tampon tutmaz, yazma yolu hiç durmamalıdır". Karar: "Bir koşul değişseydi: mühendisler canlı pencere hesabı isteseydi Timestream for InfluxDB öne geçerdi".
- **Tür:** karar gerekçesi / koşul somut değil / en uygun servis gerçekten en uygun mu.
- **Sorun:**
  1. R2'nin ağırlığı "yazma yolu durmamalı" ile gerekçelendiriliyor. Ama yazma yolunun failover'da durması R3'te cezalandırılıyor (InfluxDB 7), R2'de InfluxDB 10 alıyor. Ağırlığın nedeni ile cezanın satırı ayrışıyor.
  2. Kafa kafaya paragrafı üç koşul birlikte değişirse sonucun döneceğini söylüyor (canlı pencere, tampon, CQL bilinmemesi). Karar ise tek koşul yetiyormuş gibi yazıyor ve bu koşul (canlı pencere) kartta bir satır değil, puanı değiştirmiyor. Hesap: sadece tampon olsa R3 7'den 9'a çıkar, InfluxDB 90,4 alır ve 91,2'nin altında kalır.
  3. InfluxDB 3 Enterprise bu kartta hiç aday değil. Oysa InfluxDB 2'yi kaybettiren üç şeye doğrudan cevap veriyor: S3'te dayanıklılık ve çok node (R3), birkaç TB için ucuz storage (R5), standby ücreti yok.
- **Mimara soru:** Kart 3'te InfluxDB 3 Enterprise neden üç adaydan biri değil? Puanlansaydı Keyspaces'in 91,2'sini geçer miydi? Tek başına hangi koşul kararı çevirir?

### R9 (orta): Kart 4'te hikâyede olmayan bir iş cezalandırılıyor ve artı olarak sayılıyor

- **Bölüm:** M2 kart 4, Timestream for InfluxDB R4 ve Karar.
- **Alıntı:** R4: "Flux ekip için yeni bir dildir (InfluxQL de vardır ama task'lar Flux'tır)". Karar: "artımız: daha düşük ve sabit bir fatura, olgun Flux task'ları ve check'leri (Ö8)".
- **Tür:** karar gerekçesi (story'de olmayan bir durum için puan).
- **Sorun:**
  1. Kart 4'ün hikâyesinde task, check ya da downsampling yok. Ham veri 90 gün tutuluyor ve retention ile siliniyor. Ekip SQL biliyor ve panolar InfluxQL ile yazılabilir. "Task'lar Flux'tır" cezası hikâyeden çıkmıyor. Aynı şekilde "olgun Flux task'ları" bu iş yükü için bir artı değil.
  2. InfluxDB 3'ün R5'i "iki küçük instance'tan pahalıdır" diyor ama bir sayı vermiyor (InfluxDB 2 için 421 USD var). Okuyucu olarak farkın 50 USD mi, 2.000 USD mi olduğunu bilemiyorum.
- **Mimara soru:** Kart 4'te Flux hangi iş için gerekli? İki node'lu InfluxDB 3 Enterprise ve lisans ayda kaç USD tutar?

### R10 (orta): Terimler tanımlanmadan önce geçiyor, bazı cümleler belirsiz

- **Bölüm:** Birçok yer.
- **Alıntı ve sorun (bölümüyle):**
  - A2 "bütün durumlar" tablosu: "bir field'ın tipi **shard** içinde sabittir". Shard tanımlanmamış, A4 sadece "shard group"u tanımlıyor.
  - A3: "aynı **tag set**'e". Tag set ilk kez B2'de tanımlanıyor.
  - A5 tablosu: "**InfluxQL**'de join yoktur". Tanımı M2 terim tablosunda ve B3'te.
  - A3: "**db.influx.large**". Tanımı B5'te.
  - R1 kataloğu ve kartlar: "series index'i (**TSI**)". Açılımı ve ne olduğu hiç yazılmıyor.
  - Kart 1: "**delta kodlaması**", "check'in Flux sorgusuna (**stateDuration**)". İkisi de açıklanmıyor.
  - Kart 5 kafa kafaya: "**Kural 7**'ye göre bu R4'te sayılır". Kart 6 ve 7: "sabit kapasite, **kural 13**". Okuyucu bu kuralları hiç görmedi.
  - Kart 1 Aurora R1.3: "Aurora sayfasının **tarama kademeleri (6–7)**". Kart 6 Redshift R1.4: "Redshift sayfasının **kademesi**". Anlamı belirsiz.
  - B1: "**Seed**'in yazdığı web siparişleri". Seed nedir, belirsiz.
  - M Bölümü girişi: "Apache **Arrow**, **DataFusion**". Kart 7: "**Flight SQL**". Kart 10: "**ECPU**". Hiçbiri tanımlanmıyor.
  - Kart 1 R5: "**1.080 series**". Hikâyede 1.000 sensör var. 80 fazla series'in nereden geldiği yazılmıyor (sipariş series'leri mi?).
  - A1 ve A girişi: "Fikirler **her zaman serisi** database'inde aynıdır". İlk okumada "her zaman" ("always") diye okudum. "her time series database'inde" bekliyordum.
- **Tür:** önce geçen terim / anlaşılmayan cümle.
- **Mimara soru:** Kartlarda geçen iç kural numaraları okuyucuya açıklanacak mı, yoksa metinden çıkarılacak mı?

### R11 (orta): Disk dolarsa ne olur ve yedekler kartlardaki R3 puanında yok

- **Bölüm:** B1 T1 açıklaması; C2 tablosu (Yedek satırı); kart 3, 6 ve 7'nin R3 satırları.
- **Alıntı:** B1: "Bucket'ın retention'ı burada verilmez; varsayılanı sonsuzdur." ve "AllocatedStorage: 20". C2: "servis iç yedekleri 24 saat tutar … kullanmak için AWS Support'a başvurulur". B4: "Geri alınamaz."
- **Tür:** eksik durum ("ya şöyle olursa?").
- **Sorun:**
  1. Lale Market'in `metrics` bucket'ının retention'ı sonsuz ve diski 20 GiB. 20 GiB dolunca ne olur: yazmalar reddedilir mi, storage kendiliğinden büyür mü, büyütmek kesinti ister mi? Sayfa bunu söylemiyor. Kart 5'in hikâyesi tam olarak "disk doldu" diye başlıyor.
  2. Yanlışlıkla silinen bir bucket ya da yanlış kısaltılan bir retention, sahibin kendisinin yapabileceği bir point-in-time restore ile geri gelmiyor. Kartların R3 satırı sadece failover'ı puanlıyor. Garanti kanıtı (kart 3) ve mevzuat (kart 6) olan iş yüklerinde bu bir risk, ama puanda görünmüyor. Keyspaces ise PITR ile tam puan alıyor.
- **Mimara soru:** Ayrılan storage dolunca servis ne yapar? Yedeğin sadece AWS Support üzerinden ve 24 saatlik olması R3'te neden sayılmıyor?

### R12 (düşük): Geç gelen veri, saat dilimi, yarım batch ve cardinality ölçümü cevapsız

- **Bölüm:** A6, A7, A8/B4 (T2 task), A3.
- **Alıntı:** A6: "bir batch'in yarısı yazılabilir". T2: "range(start: -2h) Son iki saati okur". A1: "bu ay gündüz saatlerinde ne kadar harcadım?".
- **Tür:** eksik durum.
- **Sorun:**
  - Downsampling task'ı bir saati özetledikten sonra o saate geç bir point gelirse (gateway bir saat tamponluyor, kart 1) özet eski mi kalır? -2h her durumu yakalar mı?
  - Batch'in yarısı yazıldıysa yeniden göndermek güvenli mi? (Aynı timestamp yerine geçtiği için güvenli olmalı, ama sayfa bunu söylemiyor.)
  - Günlük pencere UTC'de mi, İstanbul saatinde mi hizalanır? "Gündüz saatleri" sorusu bunu gerektiriyor.
  - Bugünkü cardinality'mi nasıl ölçerim? Hangi sorgu ya da metrik bunu gösterir?
- **Mimara soru:** Downsampling'in geç veriyle nasıl başa çıktığını ve batch yeniden denemenin idempotent olduğunu bir "Aklına şu gelebilir" kutusunda yazabilir miyiz?

### R13 (düşük): Kart 8'de task dili çelişkili, kırılma koşulu tek başına yetmiyor

- **Bölüm:** M2 kart 8, Timestream for InfluxDB R1.1 ve kafa kafaya; B3.
- **Alıntı:** Kart 8: "Task'lar ve check'ler zamanlanmış Flux ya da InfluxQL sorgularıdır". B3: "InfluxQL de vardır ve SQL'e benzer, ama join ve task yoktur". Kafa kafaya: "kırılımlar sabit eşiklerle izlenebilseydi …, ekipte zaman serisi istatistiği bilen biri olsaydı ya da metrikler zaten InfluxDB'de olsaydı".
- **Tür:** anlaşılmayan cümle / koşul somut değil.
- **Sorun:**
  1. InfluxQL ile task yazılabilir mi? Sayfanın iki yeri birbirine zıt söylüyor. Aynı metin OpenSearch sayfasının 10. kartında da var.
  2. Kafa kafaya paragrafı üç koşulu "ya da" ile bağlıyor. Ama "metrikler zaten InfluxDB'de olsaydı" AO'yu (InfluxDB 4/10) değiştirmiyor, 18 puanlık farkı tek başına kapatamaz.
- **Mimara soru:** Hangi koşul tek başına 18 puanı kapatır? InfluxDB 2'de InfluxQL ile task yazılabilir mi?

### R14 (düşük): Örneklerde tip ve sayı tutarsızlıkları

- **Bölüm:** A6 şeması; A2 "bütün durumlar" tablosu; B1 canlı overview.
- **Alıntı:** A6: "yazma 1 orders,channel=web count=65 1793354411". A2: "Aynı field önce sayı, sonra metin … value="sıcak" sonra value=26.1". B1: "10 series, 2278 ham point (24 saatte)".
- **Tür:** anlaşılmayan örnek.
- **Sorun:**
  - B1'e göre `count=65` float yazar ve integer bir series'e sonra gelen yazma reddedilir. A6'daki örnek bu yüzden canlı `orders` series'ine (integer) yazılırsa reddedilmesi gereken bir yazma.
  - A2'deki satırın başlığı "önce sayı, sonra metin" diyor, örnek ise önce metin, sonra sayı.
  - 8 depo series'i × 288 = 2.304 point yapar. Sadece depo verisi 2.278'den fazla, siparişler henüz eklenmedi bile. Sayfa seed'in sadece günün bir kısmını kapsadığını söylemiyor. Bugün endpoint 1.330 döndürüyor ve "sample data ends at the time of the load" diyor.
- **Mimara soru:** 2.278 hangi zaman aralığının sayısı? A6 örneği `count=65i` mi olmalı?

### R15 (düşük): Görsellerin altyazıları neye bakacağımı tam söylemiyor

- **Bölüm:** A3 "Şuna bak: tek bir series"; A7 "Şuna bak: aynı series bir dakikalık pencerelere bölünmüş"; A7 "Şuna bak: bir yıllık series'ten türetilen iki series".
- **Alıntı:** A3: "dört dakika boyunca bellek kullanımı. Her köşe bir point'tir … beş timestamp". A7: "aynı series … beş pencere, beş değer". Türetilmiş series: "Ortadaki ve alttaki grafik, değişim hızı satırının yaptığı hesaptır".
- **Tür:** görsel ve altyazı.
- **Sorun:**
  - A3'teki görselde 5 point var. A7'deki "aynı series" görselinde her pencerede yaklaşık 6 point, toplamda yaklaşık 30 point ve farklı değerler (66–69) var. İkisi aynı series değil, ya da ilk görsel zaten dakikalık bir özet. Altyazı bunu söylemiyor.
  - Pencere görselinde "tek değer" çizilmemiş. Neye bakacağımı bilemiyorum.
  - Üçüncü görsel ABD'deki tüberküloz ölümlerini gösteriyor. Altyazı verinin ne olduğunu ve birimini söylemiyor. Alttaki yüzde değişim, tablodaki "fark ÷ süre" (derivative) değil.
  - Ayrıca A3 altyazısındaki "measurement mem, bir host tag'i" görselde görünmüyor.
- **Mimara soru:** A7 görseli A3'teki series'in ham hâli mi? Yüzde değişim grafiği derivative satırını mı göstermek için konuldu?

## Cevap

Kısmen evet. Sayfadan sonra bir meslektaşıma şunları anlatabilirim.

- **CloudWatch'a karşı:** Saklama ihtiyacım CloudWatch'un sabit kademelerini aşıyorsa Timestream for InfluxDB'yi seçerim. Bu kademeler: 60 saniyeden kısa veri 3 saat, dakikalık veri 15 gün, saatlik veri 455 gün. Series sayısı binlere çıkıyorsa da Timestream for InfluxDB'yi seçerim: metric başına 0,30 USD ödemek yerine yaklaşık 211 USD'lik sabit bir instance öderim (kart 1, 2, 5). **Eksik:** kırılma noktası açıkça yok. Yaklaşık 700 metric'te ücretler eşitleniyor, ama bunu ben hesapladım; storage ise hesapta yok. Kart 2'nin kafa kafaya paragrafındaki yanlış sayı (R2) bu anlatımı zayıflatıyor.
- **Keyspaces'e karşı:** Kaynaklar tampon tutuyorsa, ekip CQL bilmiyorsa ve canlı pencere ya da downsampling isteniyorsa Timestream for InfluxDB'yi seçerim. Sensörler tampon tutmuyorsa ve ekip Cassandra biliyorsa Keyspaces'i seçerim (kart 3). **Eksik:** kart 3'te InfluxDB 3'ün neden aday olmadığı, sıkıştırılmış verinin TB olarak boyutu ve tek başına kararı çeviren koşul (R8).
- **InfluxDB 3'e karşı:** Var olan Flux task'ları ve check'leri taşınacaksa, series sayısı on binlerde kalacaksa ve lisanssız düşük fiyat önemliyse InfluxDB 2'yi seçerim (kart 5). SQL ile join, yıllarca geçmiş, son değer önbelleği ya da milyonlarca series gerekiyorsa InfluxDB 3'ü seçerim (kart 4, 6). **Eksik:** InfluxDB 3 Enterprise'ın aylık fiyatı (lisans dahil) hiçbir kartta sayı olarak yok, Core'un hangi durumda yeterli olduğu da sadece M5'te bir cümle.
- **Redshift'e karşı:** Soru canlı, join'siz bir zaman penceresiyse ve geçmiş kısaysa Timestream for InfluxDB'yi seçerim. Join'li aylık rapor, gecelik dosya ve ayda birkaç günlük yük varsa Redshift'i seçerim. Çoğu zaman cevap ikisi birlikte olur (kart 6, 7). Bu net.
- **OpenSearch'e karşı:** Sabit eşik kontrolleri yeterliyse ve olayların metni aranmıyorsa Timestream for InfluxDB'yi seçerim. "Normal"i öğrenen bir tespit ya da log araması gerekiyorsa OpenSearch'ü seçerim (kart 2, 8). Bu net. Kart 8'in kırılma koşulu ise zayıf (R13).
- **DynamoDB'ye karşı:** Son değerle birlikte geçmiş ve pencere gerekiyorsa Timestream for InfluxDB'yi seçerim. Sadece son durum ve anında tepki gerekiyorsa DynamoDB'yi seçerim (kart 4, 9). **Eksik:** kart 9'da 2 milyon series'in Timestream for InfluxDB'ye maliyeti hiç anılmıyor (R3). Bu yüzden "ne kadar kötü" sorusunu cevaplayamıyorum.
- **ElastiCache'e karşı:** Ekran uzun bir aralığı (30 gün dakika dakika) gösteriyorsa Timestream for InfluxDB'yi seçerim. Saniyede binlerce artırma ve tekil sayım varsa ElastiCache'i seçerim (kart 10). Bu net.

Toparlarsak, en çok iki şey eksik:
1. Sayılarla verilmiş iki kırılma noktası: CloudWatch'a karşı series sayısı ve InfluxDB 3'e karşı aylık fark.
2. Kartlar arasında tutarlı ceza: cardinality, "gece çalışır" ve CloudWatch saklama kuralı aynı ölçekle puanlanmalı. Bunlar düzeltilmeden bir karar kaydında puanları savunmakta zorlanırım.

## Kapanış (yazar)

| Bulgu | Durum | Ne yapıldı |
|---|---|---|
| R1 | kapandı | Tek tanım: series key = measurement + tag set + field adı (InfluxData'nın tanımı); bir point'i measurement + tag set + timestamp tanımlar ve aynı anda yazılan birkaç field tek point'in field'larıdır (A3 kartı). A6 tablosu, A6 akışı, A6 kutusu, ix-q5, B1 şeması ve B4 cümlesi bu ikinci ifadeyi kullanır. |
| R2 | kapandı (bu sayfada) / ortak düzeltme için listelendi | Kart 2'nin CloudWatch kafa kafaya metni bu sayfada yeniden yazıldı: R2+R3+R4 = 8,4 (1,4 + 1,6 + 5,4), InfluxDB R1'de 4,2 ve R5'te 5,4 önde, fark 1,2; en büyük fark R5; kırılma noktası yaklaşık 700 series. Aynı metin OpenSearch sayfasının 7. kartında duruyor; puanlar değişmediği için o sayfanın metni ortak düzeltme için sahibine listelendi (bu commit OpenSearch bloğuna dokunmaz). |
| R3 | kapandı | Kart 7: cardinality tek satırda sayılır (R1.4 · VM: 2 milyon series, index kaydı); DA gerekçesi series sayısını değil series başına açılan dosyaları ve shard group taramasını sayar; R5 gerekçesi sadece ödeme biriminin aylık birkaç günlük yüke uymamasını sayar. Kart 9'un puanları DynamoDB sayfasının 5. kartından gelir ve değişmez; R2 gerekçesi artık 2 milyon cihazın 2 milyon series olduğunu ve AWS örneğine göre 4xlarge sınıfı istediğini söyler (kırılım aynı, 5). |
| R4 | kapandı | Kart 4'ün kafa kafaya, karar ve M2 özetindeki "yakın yarış" ifadeleri "fark 6,4" oldu. |
| R5 | kapandı (bu sayfa) / kart 2 ortak düzeltme için listelendi | Ölçeğin 0–3 bandı uygulandı: kart 1 CloudWatch YD 4→3 (7 kırık, toplam 83,3), kart 5 2'ye indi (8 kırık, bir kademe fazla; toplam 65,2). M2 özeti doğru kırılımları yazar. Kart 2'nin 8'i OpenSearch sayfasından gelir ve iki sayfada birlikte değişmeli; özette bu açıkça yazılı. |
| R6 | kapandı | Kart 4 R1.3 ve kart 6 R1.2 gerekçelerinden AWS boyutlandırma tablosu ve 16 TiB çıkarıldı; engine davranışı (TSI büyümesi, yerel diskte series bazlı dosyalar, shard group taraması) kaldı, puanlar aynı. Kart 9'da storage büyümesi R1.2'de sayılır; R5 gerekçesi sadece ödeme birimini anlatır. Kart 3'teki Keyspaces gerekçesi Keyspaces sayfasından gelir; o sayfada kalır. |
| R7 | kapandı | R5'te tek mekanizma: Multi-AZ standby ikinci instance ücretidir, 2 puan (kart 1, 2, 3, 5, 8). Kart 5 9→8 (toplam 91,3). Kart 1'e storage (4,8 USD) ve Price List tarihi, kart 2 ve 8'e 211 USD eklendi. CloudWatch'a karşı kırılma noktası (yaklaşık 700 series) kart 2'nin kafa kafayasında. |
| R8 | kapandı | Kart 3'ün kararı artık somut ve kafa kafaya ile aynı: tampon (R3 7→9) ve ekibin CQL bilmemesi birlikte; tek başına tampon 90,4'e 91,2 ile yetmez. M2 özetine InfluxDB 3'ün neden aday olmadığı (kart Keyspaces sayfasından) ve kabaca 89 alacağı yazıldı. Ağırlık metni Keyspaces sayfasınındır; puanlar ve ağırlıklar iki sayfada aynı kalır. |
| R9 | kapandı | Kart 4 R4 gerekçesi hikâyeden: ekip SQL biliyor, InfluxDB 2'nin dilleri Flux ve InfluxQL. Karar'dan "olgun Flux task'ları" çıkarıldı. InfluxDB 3 fiyatı: iki db.influx.large node ayda yaklaşık 422 USD artı vCPU başına lisans; InfluxDB 2 Multi-AZ large 421 USD. |
| R10 | kapandı | shard yerine shard group / zaman parçası; tag set (A2 kartında dfn), InfluxQL (A5'te dfn), TSI (A4 kartında dfn), stateDuration açıklandı, "kural 7/13" yerine düz cümle, Aurora ve Redshift kademeleri düz cümleyle, Seed, Arrow, DataFusion, Parquet, Flight SQL açıklandı, A3'te instance adı yerine "orta boy sınıf", 1.080 series = 1.000 sensör + 80 sipariş series'i. "her zaman serisi" kaldırıldı. ECPU kart 10'da ElastiCache sayfasının teriminin içinde kalır; terimler tablosu diğer servis terimlerini kendi sayfalarına yönlendirir. |
| R11 | kapandı | B1 T1 açıklamasına eklendi: sonsuz retention ile 20 GiB dolar; storage UpdateDbInstance allocatedStorage ile büyütülür (en fazla 15.360 GiB, API referansı), doğru çözüm retention'dır; belgeler kendiliğinden büyümeden söz etmez. Kart 6 R3 8→7: mevzuat kaydı için kullanıcı başlatan geri yükleme yok (iç yedekler 24 saat, Support). Kart 3'ün R3'ü Keyspaces sayfasının puanıdır, değişmedi. |
| R12 | kapandı | B4'e bir "Aklına şu gelebilir" kutusu: geç point ve -2h/-3h aralığı, yarım batch'i yeniden göndermenin güvenli olması (aynı measurement, tag set, timestamp yerine geçer), UTC hizası ve yerel saat, influxdb.cardinality() ile ölçüm. |
| R13 | kapandı | Kart 8 R1.1: task'lar ve check'ler Flux sorgularıdır (InfluxQL değil). Kafa kafaya: tek koşul yetmez; sabit eşik (AO kabaca 9) ve olayların zaten InfluxDB'de olması birlikte farkı birkaç puana indirir. |
| R14 | kapandı | A6 örnekleri count=65i / 66i; A2 satırının örneği önce sayı, sonra metin; B1'de 2.278'in sorgu anından geriye 24 saat olduğu ve Seed verisinin yükleme anında bittiği yazıldı. |
| R15 | kapandı | Üç altyazı yeniden yazıldı: ilk görselde dakikada bir point ve görselde görünmeyen isim iddiası kaldırıldı; pencere görseli "aynı türden, daha sık point'li bir series" ve tek değerin çizilmediği; üçüncü görselin verisi (ABD yıllık tüberküloz ölümleri), ortadaki grafiğin yıllık fark, alttakinin yüzde değişim olduğu. |

Ortak düzeltme listesi (sahip sayfalar, bu commit dokunmaz): OpenSearch kart 7'nin CloudWatch kafa kafaya metnindeki 6,8 ve "en anlamlı fark R1 · YD" (doğrusu 8,4 ve R5); OpenSearch kart 7 CloudWatch R1 · YD = 8, isteğin bir parçası karşılanmadığı için ölçeğe göre 0–3 bandında olmalı.
