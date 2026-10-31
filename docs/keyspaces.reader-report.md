# Reader simulation: Amazon Keyspaces (keyspaces), Türkçe sayfa, model 2
Tarih: 2026-10-31
Okuyucu: Cassandra'yı, wide-column database'leri ve Keyspaces'i hiç kullanmamış; DynamoDB'yi ve SQL'i adıyla bilen bir geliştirici. Kaynak: `/tmp/preview_keyspaces/keyspaces.tr.txt` (metnin tamamı, parça parça), `/tmp/preview_keyspaces/keyspaces.tr.rendered.html` (beş M7 simülasyonunun JSON'u), üç görsel (`keyspaces-coordinator.jpg`, `keyspaces-cassandra-cluster.png`, `keyspaces-serverless.png`), aritmetiği doğrulamak için `e2e_usecases_w.py` içindeki `KEYSPACES_W`.

## Genel izlenim

Bölüm A güçlü. Partition key, clustering column, token, consistency level, upsert, tombstone ve TTL kavramları her durumuyla tablolarda veriliyor. Önceden hiç bilmediğim halde A1–A9'dan sonra bir CQL table tanımını okuyabiliyorum. Hangi sorunun ucuz, hangisinin imkânsız olduğunu da söyleyebiliyorum. B bölümündeki canlı cevaplar (özellikle ALLOW FILTERING reddi ve `system_schema` çıktıları) kavramları somutlaştırıyor.

Aritmetik temiz. On kartın hepsinin toplamlarını, kart 1, 2, 7, 8, 9 ve 10'u ise hücre hücre kontrol ettim: her hücre puan × ağırlık / 10, R1 ara toplamları ve 100 üzerinden toplamlar doğru. Beş M7 simülasyonunun (sim-w_migration, sim-w_sensor, sim-w_clicks, sim-w_fraud, sim-w_reviews) son adımı kartlardaki toplamları ve sıralamayı birebir veriyor: 95,6 / 74,4 / 73,4; 90,4 / 84,4 / 83; 77 / 75,4 / 62; 98 / 88,2 / 72,8; 95,6 / 80,6 / 50,8.

Zayıf yer, sayfanın kendi koyduğu iki kural: "R1 yalnız engine'i puanlar" ve "bir eksik yalnız bir satırda sayılır". Birkaç kartta bu kurallar delinmiş. Aynı mekanizma (değişiklik akışını okuyan ayrı tüketici, ön ısıtma, ikinci table) bir adayda R1'de, başka bir adayda R4'te sayılıyor ya da aynı adayda iki satırda birden kırılıyor. Sayılar toplamı değiştirecek kadar büyük değil, ama okuyucuya öğretilen yöntemle çelişiyor. İkinci boşluk para: sayfa birim fiyat vermiyor. Kart 6 ise R5 ağırlığını tam olarak birim fiyatla gerekçelendiriyor.

## Bulgular

### R1 (yüksek): Kart 10'da DynamoDB'nin R1 puanları engine'i değil kod çevirisini ölçüyor; aynı iş R4'te bir kez daha kırılıyor
Bölüm: M2 kart 10 (DynamoDB satırları R1.2, R1.3, R1.4 ve R4); M7 sim-w_migration.
Alıntı: "3 puan kırıldı: birden fazla clustering column tek bir sort key metninde birleştirilir ve her sorgu Query'ye çevrilir." / "1 puan kırıldı: IF koşulları condition expression söz dizimine çevrilir." / "USING TTL yerine her item'a bir zaman attribute'u yazılır." / R4: "8 puan kırıldı: bütün Java servisleri CQL'den DynamoDB SDK'sına 6 ay içinde yeniden yazılır".
Sorun: Sayfa (Mimar gözüyle, R1 açıklaması) R1'in "platformdan bağımsız" olduğunu ve yalnız engine'in doğasını puanladığını söylüyor. Kart 10'daki R1.2–R1.4 kırılımları ise engine'in yapamadığı bir şeyi göstermiyor. Gösterdikleri, mevcut kodun başka bir söz dizimine çevrilmesinin emeği. Bu emek R4'te zaten 8 puanla sayılıyor. Böylece aynı göç işi iki kez sayılmış oluyor. Kart 2'de DynamoDB'nin aynı R1.3 (condition expression) ve R1.2 için kırılmaması da tutarsızlığı gösteriyor.
Mimara soru: Göç kartında R1.2 ve R1.3'teki "çevrilir" kırılımları R4'e mi taşınmalı? Taşınmayacaksa R1'in "engine'in doğası" tanımı göç kartında neden farklı?

### R2 (yüksek): Kart 4'te DynamoDB'nin IAM ile "değişiklik izni kapatılabilir" iddiası ve değiştirilemezliğin iki kez sayılması
Bölüm: M2 kart 4 (Keyspaces R1.3 ve R4; DynamoDB R4; DynamoDB kafa kafaya).
Alıntı: "IAM PutItem'ı UpdateItem ve DeleteItem'dan ayrı izin verir, değişiklik izni kapatılabilir." / Keyspaces R4: "1 puan kırıldı: IAM'in cassandra:Modify izni INSERT, UPDATE ve DELETE'i birlikte verir; silme izni ayrı kapatılamaz". / Kafa kafaya: "Hangi koşul değişseydi DynamoDB seçilirdi: ... IAM ile silme izninin kapatılması denetçinin şartı olsaydı."
Sorun: (a) PutItem var olan bir item'ın üzerine yazar. UpdateItem ve DeleteItem'ı yasaklamak, yazan rolün kaydı PutItem ile değiştirmesini engellemez. Okuyucu olarak bu "değiştirilemezlik" iddiasına güvenemiyorum. Kararın dönme koşulu da bu iddiaya dayanıyor. (b) Keyspaces'te "engine katmanında değiştirilemezlik yok" zayıflığı R1.3'te 5 puan kırıyor. Aynı zayıflık, IAM ile kapatılamaması olarak R4'te bir kez daha sayılıyor.
Mimara soru: DynamoDB'de PutItem'ın üzerine yazmasını IAM ile engellemenin bir yolu var mı? Yoksa kafa kafaya paragrafındaki dönme koşulu doğru mu? cassandra:Modify kırılımı R1.3'teki eksiğin tekrarı değil mi?

### R3 (yüksek): Değişiklik akışını okuyan ayrı tüketici bir adayda R1'de, diğerinde R4'te; bazı adaylarda ikisinde birden sayılıyor
Bölüm: M2 kart 3 (Aurora R1.3, Keyspaces R4), kart 6 (ElastiCache R1.3 ve R4), kart 8 (MemoryDB R1.1, R1.3 ve R4).
Alıntı: Kart 3 Aurora R1.3: "bildirim için değişiklik akışını okuyan ayrı bir bileşen kurulur". Kart 3 Keyspaces R4: "bildirim için KCL ile bir tüketici yazılır ve işletilir". Kart 6 ElastiCache R1.3: "35 derece bildirimi yazan Lambda'nın içinde çalışır"; R4: "bildirim yazma yolunun içinde kalır". Kart 8 MemoryDB R1.1: "90 günden eskiler ZREMRANGEBYSCORE ile kırpılır"; R1.3: "90 günlük kırpma da bir iştir"; R4: "kural motorunun tetiklenmesi ayrıca yazılır".
Sorun: Sayfanın kuralı açık: "değişiklik akışının varlığı R1 · YD'de, onu bir Lambda'nın doğrudan okuyup okuyamaması R4'te sayılır". Aurora'da tüketici bileşeni R1'de, Keyspaces'te R4'te kırılıyor. Yani aynı mekanizma iki adayda farklı satırda. ElastiCache ve MemoryDB'de değişiklik akışının yokluğu hem R1.3'te hem R4'te kırılıyor. MemoryDB'de üye başına süre sonunun yokluğu R1.1'de ve R1.3'te iki kez sayılıyor. Kartlar 6 ve 8'de R4'ün "ne istiyoruz" metni R1.3'ün cümlesini tekrar ediyor ("bildirim yazan koddan ayrı bir fonksiyonda çalışmalı"). Bu yüzden ağırlık da iki kez veriliyor.
Mimara soru: Bir mekanizmanın hangi satırda sayılacağını kart kart değil, katalog düzeyinde bir listeyle sabitlemek gerekmez mi?

### R4 (orta): Kart 2'de sıkıştırma ve "sensörler tampon tutmaz" iki satırda sayılıyor
Bölüm: M2 kart 2 (Keyspaces R1.3 ve R5; Timestream R2 ve R3).
Alıntı: R1.3: "4 puan kırıldı: time series'e özgü bir sıkıştırma yoktur; ... storage row boyutuyla ölçülür." R5: "birkaç TB storage GB-ay olarak ödenir". Timestream R5: "sıkıştırılmış storage küçüktür". Timestream R2: "büyüme bir sınıf değişikliğidir"; R3: "standby'a geçişte ... tampon tutmayan sensörlerin o anki okumaları kaybolur".
Sorun: Sıkıştırmanın olmaması R1.3'te (DA) kırılıyor. Sıkıştırılmamış storage'ın faturası R5'te Keyspaces'ten 2, DynamoDB'den 1 puan daha alıyor; InfluxDB'ye ise R5'te artı olarak yazılıyor. "Sensörler tampon tutmaz" gerekçesi hem R2'nin ağırlığını hem Timestream'in R3 kırılımını taşıyor. Timestream'in R2 kırılımı ("büyüme bir sınıf değişikliğidir") bir kapasite ayarıdır, tepeyi karşılayamamak değildir. Hikâye zaten "90 günlük veri ... sonra sabit kalır" diyor, yani büyüme yok. Bu kırılımlar toplamda InfluxDB'yi 83'te tutuyor. Fark DynamoDB'yle 1,4, Keyspaces'le 7,4 puan.
Mimara soru: Düz ve sabit 4.000 yazma/s'de InfluxDB'nin R2'den 3 puan kaybetmesinin somut nedeni ne? Sıkıştırma R1.3'te sayıldıysa R5'te ikinci kez sayılmalı mı?

### R5 (orta): Ön ısıtma R2'de kırılıyor; "kapasite ayarı R4'tür" kuralı sayfada yazılı değil
Bölüm: Mimar gözüyle (R1–R5 tablosu), M2 kart 1, 5, 10 (R2), kart 10 Apache Cassandra R2 ve R4.
Alıntı: Kart 1 R2: "1 puan kırıldı: ... ilk 15.000'lik kampanyadan önce table bir kez ısıtılır." Kart 1 R2 "ne istiyoruz": "tek seferlik bir kapasite ayarı kabul edilir". Kart 10 Cassandra R2: "tahminin üstündeki bir büyüme node ekleme ... ister"; R4: "kapasite ekleme işi aynen kalır".
Sorun: Bir okuyucu olarak R2 ile R4 arasındaki çizgiyi sayfadan çıkaramadım. Table'ı ön ısıtmak bir yapılandırma işidir ve R4'ün sorusuna ("sunucu boyutlandırmak isteniyor mu?") girer. Kartlarda ise R2'den kırılıyor ve R2'nin "ne istiyoruz" metni kapasite ayarını kabul edilebilir sayıyor. Kart 10'da Cassandra'nın node ekleme işi hem R2'de hem R4'te sayılıyor.
Mimara soru: "Tepeyi karşılamak R2, kapasiteyi ayarlamak R4" kuralı sayfaya yazılacak mı? Yazılırsa kart 1, 5 ve 10'daki ön ısıtma kırılımı R4'e mi gider?

### R6 (orta): Kart 6'da R5 ağırlığının nedeni birim fiyat, ama puan birim fiyata bakmıyor; ayrıca daha uygun bir AWS servisi olabilir
Bölüm: M2 kart 6 (R5 satırı, Keyspaces R5); M2 giriş ("R5 puanları birim fiyat değil fiyat modelini karşılaştırır").
Alıntı: R5 ağırlık nedeni: "Günde iki milyardan fazla yazma: birim fiyattaki küçük bir fark ayda binlerce dolardır." Keyspaces R5: "2 puan kırıldı: çevrim dışı kalan cihazların TTL silmesi ayrıca ödenir".
Sorun: Ağırlık 14 olarak birim fiyat farkıyla gerekçelendiriliyor. Puanlar ise birim fiyatı karşılaştırmıyor ve Keyspaces'i yalnız az sayıdaki çevrim dışı cihazın TTL silmesi için kırıyor. Günde 2,16 milyar yazmada asıl fark, iki servisin yazma birimi fiyatıdır (us-east-1 liste fiyatlarında belirgin biçimde farklı). Okuyucu bu farkı sayfadan öğrenemiyor. Ayrıca termostatın "son durumu" ve "çevrim dışı" bilgisi için AWS IoT Core'un Device Shadow'u ve bağlantı yaşam döngüsü olayları doğal bir aday. Kartta bu adaydan söz edilmiyor.
Mimara soru: Bu kartta R5, birim fiyatı karşılaştırmadan nasıl puanlanıyor? IoT Device Shadow neden aday değil?

### R7 (orta): Kart 4'te Aurora'nın R2 gerekçesi hikâyedeki bir yıllık saklama süresiyle çelişiyor; değiştirilemezlik için başka bir AWS servisi düşünülmemiş
Bölüm: M2 kart 4 (Aurora R2; hikâye).
Alıntı: Hikâye: "Bir yıl çevrim içi saklanır, sonra yedi yıllık arşive (S3) gider." Aurora R2: "tek bir cluster'ın storage sınırına (128 TiB) birkaç yılda yaklaşılır".
Sorun: Veri bir yıldan sonra arşive gidiyorsa çevrim içi hacim bir yıllık kayıtta sabitlenir; "birkaç yılda" büyüme olmaz. R2'deki 7 puanlık kırılım yakın yarışın (89,2 / 86,4 / 75,6) arkasındaki ana gerekçe. Ayrıca kartın ana gereksinimi engine katmanında değiştirilemezlik. AWS'te bu iş için tasarlanmış seçenekler var (örneğin CloudTrail Lake'in özel olayları ya da S3 Object Lock ve Athena). Hiçbiri aday olarak tartışılmıyor.
Mimara soru: Bir yıllık sabit hacimde Aurora'nın R2 puanı ne olur? Değiştirilemez denetim kaydı için bu kartta neden yalnız üç database var?

### R8 (orta): Kart 9'da index eksikliği (Ö7) üç satırda; engine sorusu R4 ağırlığını büyütüyor
Bölüm: M2 kart 9 (Keyspaces R1.1, R1.2, R1.4, R4, R5; R4 ağırlık nedeni).
Alıntı: R1.1: "her ek sıra ve filtre ayrı bir table'dır ... (Ö7'nin sınırı)". R1.2: "index, materialized view ve aggregate fonksiyon yoktur ... (Ö7)". R5: "her yorum dört table'a ve her oy bir silme ve iki yazmaya dönüşür". R4 ağırlık nedeni: "Analistler her ay yeni sorular soruyor ve yorumları siparişlerle birleştiriyor." Keyspaces R4: "her yeni analist sorusu yeni bir table ... siparişlerle JOIN yoktur".
Sorun: "Index yok, her sıra bir table" eksiği R1.1, R1.2 ve R5'te üç kez kırılıyor; tombstone eksiği de R1.3'te ve R5'te ikinci kez. Önceden bilinmeyen sorular ve JOIN'ler, sayfanın kendi kataloğunda R1 · EY'dir (engine'in doğası). Burada ise R4'ün ağırlığını 24'e çıkarıyor ve R4'te 7 puan kırıyor. Keyspaces'in kaybetmesine itirazım yok, ama 50,8'in ne kadarı çift sayımdan geliyor, bilemiyorum.
Mimara soru: Aynı eksik tek satırda sayılsaydı Keyspaces'in toplamı ne olurdu? Analistlerin yeni sorusu R4'te mi, R1 · EY'de mi?

### R9 (orta): Kart 7'de haftalık rapor satırı sayfanın kendi kararıyla çelişiyor; maliyet satırında performans şartı var
Bölüm: M2 kart 7 (R1.2 DA, R5 "ne istiyoruz", DynamoDB R5, Redshift R1.1 ve R5).
Alıntı: R1.2: "Haftalık rapor bütün okuyucuların geçen haftasını tarar ve kategoriye ve saate göre gruplar". Karar: "rapor taraması asla bu table'da çalışmaz". R5 "ne istiyoruz": "Rapor taraması okuyucu şeridini yavaşlatmamalı." DynamoDB R5: "1 puan kırıldı: dalgalı yüksek yazmada istek başına fiyat provisioned'dan pahalıdır." Redshift R5: "şerit sorguları kapasiteyi gün boyu açık tutar".
Sorun: R1.2 (ağırlık 14), operasyon database'inden raporu tarayıp gruplamasını istiyor. Sayfa ise bunun asla bu table'da yapılmayacağını söylüyor. Keyspaces ile DynamoDB ikisi de 3 alıyor, yani satır aralarındaki farkı değiştirmiyor; sadece Redshift'i yarışta tutuyor. "Doğru mimari ikisi birlikte" deniyor ama "Keyspaces + Redshift" bir aday değil. R5'in "ne istiyoruz" metni bir maliyet değil bir performans şartı. İstek başına fiyat DynamoDB'den kırılıyor, aynı on-demand modu kullanan Keyspaces'ten kırılmıyor. Redshift'in point lookup zayıflığı R1.1'de ve R5'te iki kez sayılıyor.
Mimara soru: Rapor her zaman CDC ile Redshift'e taşınıyorsa R1.2 bu kartta ne ölçüyor? İstek başına fiyat kırılımı neden yalnız DynamoDB'de?

### R10 (orta): Kart 3'te ikinci yazma ve tombstone R1'de ve R5'te iki kez sayılıyor
Bölüm: M2 kart 3 (Keyspaces R1.2 ve R5; DynamoDB R1.2 ve R5).
Alıntı: Keyspaces R1.2: "her mesajda eski row silinir ve yenisi yazılır, her mesaj bir tombstone bırakır". R5: "her mesaj bir ekleme, listede bir silme ve bir yazmadır; tombstone'lar silinene kadar storage'da sayılır." DynamoDB R1.2: "her mesaj sohbet item'ına ikinci bir yazmadır"; R5: "her mesaj iki yazma ve bir GSI yazmasıdır".
Sorun: Aynı yazma biçimi önce OY'de, sonra faturası olarak R5'te kırılıyor. İki adayda da yapılıyor, yani sıralama değişmiyor. Ama okuyucuya öğretilen "bir eksik yalnız bir satırda sayılır" kuralı burada görünür biçimde delinmiş. Kart 4'te iki table'a yazma da R1.2 ve R5'te sayılıyor.
Mimara soru: Bir yazma biçiminin maliyeti R5'te ayrıca sayılacaksa, kuralın metni "davranış R1'de, faturası R5'te" diye mi değişmeli?

### R11 (orta): "Partition boyutu pratikte sınırsız" ise partition'ın büyümesi Keyspaces'te neden sorun?
Bölüm: A3 (Kavram Partition), A10 matris Ö3, B4 (partition büyümesine karşı tasarım), M4 soru 3.
Alıntı: A3: "Keyspaces'te bir partition'ın boyutu pratikte sınırsızdır, ama trafik sınırı vardır (A4)." B4: "TTL 7 gün olmasaydı ve kullanıcı yıllarca aktif kalsaydı tek bir partition milyonlarca row olurdu. İki önlem vardır".
Sorun: Apache Cassandra'da büyük partition'ın neden kötü olduğunu anladım. Keyspaces'te ise sayfa boyutun sınırsız olduğunu söylüyor, sonra büyümeyi önlemek için composite key öneriyor. Keyspaces'te büyük ama sakin bir partition'ın somut zararı ne (gecikme, maliyet, "son N" okuması, silme)? Bunu bulamadım. Kart 2, 4 ve 7'deki (sensor_id, day) ve (operator_id, day) tasarımları da bu gerekçeye dayanıyor.
Mimara soru: Keyspaces'te büyük bir partition'ın ölçülebilir bedeli nedir? Yalnız trafik sınırı ise B4'teki birinci önlem neden "büyüme" diye adlandırılıyor?

### R12 (orta): Cevapsız "ya şöyle olursa?" soruları
Bölüm: A4, A8, B4, B5, M2 kart 10, M5, giriş (öğrenme hedefleri).
Alıntı: Giriş: "Bir okuma için doğru tutarlılık seviyesini seçmek ve maliyetini hesaplamak." / A4: "Keyspaces'te bir partition saniyede 3.000 okuma birimi ve 1.000 yazma birimiyle sınırlıdır". / Kart 10: "40 TB veri bir kez taşınır".
Sorun: Şunları sayfadan cevaplayamadım:
- Bir istek warm throughput'u ya da partition sınırını aşınca client ne görür? Hangi hata döner, driver yeniden dener mi? B5 yalnız yük simülasyonunun "geri çekilerek yeniden dener" dediğini söylüyor.
- 40 TB nasıl taşınır? Hangi araç kullanılır, dual write mı yapılır, kesinti olur mu? Kartın en büyük eksisi bu, ama yolu yok.
- "Geçmişin doldurulması" (A8, M1 Ö7) somut olarak nasıl yapılır? Yeni bir soru table'ını mevcut veriden kim doldurur?
- Multi-Region keyspace'te iki bölge aynı row'a yazarsa hangisi kazanır? LWT çok bölgede çalışır mı?
- Aynı row'a aynı anda iki upsert gelirse hangisi kalır? Zaman damgası client'tan mı, sunucudan mı gelir?
- Maliyet para olarak hiç hesaplanmıyor. Öğrenme hedefi "maliyetini hesaplamak" diyor, ama okuyucu yalnız birim sayısını hesaplayabiliyor.
Mimara soru: Bu maddelerden hangileri sayfanın kapsamında? En azından throttling davranışı ve taşıma yolu için birer satır eklenebilir mi?

### R13 (düşük): Kart 1'de süresi dolmuş verinin storage'da sayılması yalnız Keyspaces'ten kırılıyor
Bölüm: M2 kart 1 (Keyspaces R5, DynamoDB R5).
Alıntı: Keyspaces R5: "süresi dolan veri silinene kadar (genellikle 10 gün içinde) storage'da sayılır". DynamoDB R5: "TTL silmesi ücretsizdir. Puan kırılmadı."
Sorun: DynamoDB de süresi dolan item'ı silinene kadar (sayfaya göre "birkaç gün") saklıyor ve storage'ı faturalıyor. Bu mekanizma yalnız bir adayda kırılıyor. Kart 3'te tombstone storage'ı için de aynı soru geçerli.
Mimara soru: Bekleme süresindeki storage DynamoDB için de sayılmalı mı, yoksa Keyspaces'teki kırılım yalnız TTL delete ücretine mi indirilmeli?

### R14 (düşük): Tanımından önce kullanılan terimler
Bölüm: başlık, A10, Mimar gözüyle (R1–R5 tablosu, R1 kataloğu), M2 kart 1, B1, B3.
Alıntı: Başlık: "Kimlik doğrulama: IAM role (SigV4)". R1 tablosu: "Access pattern bu gereksinimin bir parçasıdır (R1 · EY)". R1 kataloğu AO: "Secondary index, materialized view, UDF ve CQL GRANT yok". Kart 1 DynamoDB R1.4: "Bir item collection sort key sırasıyla bir arada durur". Kart 1 DynamoDB R1.3: "\"Aktivitem\" okumada expires_at'i süzmelidir". B1: "Workshop canlı table'a Engine App üzerinden bir SELECT gönderdi". B3 checkpoint: "WCU ya da WRU tüketir".
Sorun: "R1 · EY" kodu, katalog tablosundan önce geliyor. UDF ve GRANT, M5'e ve Aurora terim satırına kadar açıklanmıyor. "item collection" kartlarda geçiyor, ama B1'deki karşılaştırma tablosuna kadar tanımlanmıyor. "expires_at" hiç tanımlanmıyor. "Engine App" hiç tanıtılmıyor. RRU, WRU, RCU ve WCU kısaltmaları B2'de ilk kez geçiyor; WCU hiç açılmıyor. SigV4, M2 terim tablosunda yarım açıklanıyor.

### R15 (düşük): C3'teki "driver'ın varsayılan seviyesi" ifadesi yanıltıcı
Bölüm: C3.
Alıntı: "Driver'ın varsayılan seviyesi LOCAL_QUORUM'dur ve \"Son baktıkların\" şeridi bugün bu varsayılanla okur".
Sorun: Python Cassandra driver'ının kendi varsayılanı LOCAL_ONE'dır. LOCAL_QUORUM, uygulamanın `engines/keyspaces.py` içinde ExecutionProfile ile açıkça seçtiği seviyedir. Okuyucu kendi projesinde driver'ın LOCAL_QUORUM ile başlayacağını sanabilir.
Mimara soru: Cümle "uygulamanın ayarladığı varsayılan" olarak mı düzeltilmeli?

### R16 (düşük): Türkçe dil sorunları
Bölüm: M2 (her kart), A7, A9, Kart 4 ağırlıkları, alıntılar.
Alıntı: "Keyspaces ile kafa kafaya, DynamoDB: Key-value (DynamoDB) ile kafa kafaya." / "DynamoDB ile kafa kafaya, Keyspaces: Wide-column (Keyspaces) ile kafa kafaya." / "Karar. Karar: Keyspaces 97,2 ..." / "Bu iş yüküne en uygun servis: Keyspaces" hemen ardından "Bu iş yüküne en uygun servis: Wide-column (Keyspaces), 97,2 / 100" / Kart 4: "R3 ve R4 14" / A7: "(TTL bir row'un sadece bazı column'larını sona erdirirse o güncelleme de sayılır)" / A9: "Bu sayfanın kaynakları Keyspaces CDC'nin Streams API'si ve Kinesis Client Library (KCL) ile okunduğunu söyler".
Sorun: Kafa kafaya başlıkları aynı ifadeyi iki kez, ters sırayla söylüyor. Hangi adayın hangisine karşı anlatıldığını her seferinde yeniden çözmem gerekti. "Karar. Karar:" ve en uygun servis satırının tekrarı da gereksiz. "R3 ve R4 14" yerine "R3 ve R4 14'er" olmalı. A7'deki parantez cümlesinde "o güncelleme"nin neyi kastettiği belirsiz. A9'daki cümle bir bilgiyi kaynak üzerinden dolaylı veriyor ve "Lambda doğrudan tetiklenmez" sonucunu açıkça söylemiyor. Bazı İngilizce belge alıntıları ("non-negligible performance cost", "scales up to any previously reached traffic level instantly") Türkçe karşılıkları olmadan duruyor.

### R17 (düşük): Cassandra cluster görselinin altyazısı oklarda neye bakılacağını yanlış yönlendiriyor; node sayıları uzlaştırılmamış
Bölüm: A4 (`keyspaces-cassandra-cluster.png` ve `keyspaces-coordinator.jpg`).
Alıntı: "Şuna bak: dört node'luk bir Apache Cassandra cluster'ı. ... Node'lar arasındaki oklar replica'lar arasındaki trafiktir."
Sorun: Görselde oklar yalnız halkadaki komşu node'ları bağlıyor. Replication factor 3 ile dört node'da coordinator, komşu olmayan bir replica'ya da gider. Altyazı okuyucuya trafiğin yalnız komşulara gittiğini düşündürüyor. Öğretici halka 3 node, coordinator görseli 6 node, cluster görseli 4 node. Hiçbir altyazı bu farkı ve görseli A4'teki hangi kurala bağlayarak okumam gerektiğini söylemiyor. Görsel, token bölümünden uzakta, consistency tablosunun altında duruyor.

### R18 (düşük): M7'deki renk açıklaması ve öğretici/canlı veri farkı kafa karıştırıyor
Bölüm: M7 giriş, B1, B2 (Q1 tahmin kutusu).
Alıntı: M7: "Simülasyonun altındaki renk açıklaması bütün simülasyonlarda ortaktır; bu beş simülasyonda yeşil önde olan adayı, \"sonuçta yeni\" en uygun servisi gösterir." Lejant: "okunuyor eşleşti okundu ve atlandı kilitli sonuçta yeni reddedildi ya da yanlış". B2 tahmin cevabı: "16:37 wishlist, 16:18 wishlist, 15:02 view".
Sorun: Bir karar simülasyonunda "eşleşti", "kilitli" ve "okundu ve atlandı" ne demek? Simülasyon JSON'unda ikinci aday "match" işaretli, ama bu işaretin anlamı açıklanmıyor. B2'deki tahmin cevabı öğretici kopyadan geliyor (15:02 view). Hemen altındaki canlı cevapta üçüncü row 14:48 wishlist. İki farklı C00005 partition'ı yan yana duruyor ve farkı söylenmiyor.

## Keyspaces'i ne zaman seçerim: bir meslektaşa anlatabilir miyim?

Büyük ölçüde evet. Sayfadan sonra şunu anlatabilirim:

- **DynamoDB yerine:** İki servisin modeli aynı: partition key'in hash'i, partition içinde sıra, okumadan yazma. R1'de çoğu zaman eşit ya da çok yakınlar. Keyspaces'i ekip CQL biliyorsa ya da mevcut bir Cassandra/Spark Cassandra Connector kodu korunacaksa seçerim. Bunlar olmadan da birkaç teknik neden Keyspaces'i öne çıkarabilir: birden fazla type'lı clustering column, 400 KB'ı aşan row (1 MB'a kadar) ve süresi dolan verinin okumada hiç görünmemesi. DynamoDB'yi Lambda ile az kodla tepki (Streams), GSI, zero-ETL, ücretsiz TTL silmesi ve birkaç item'lık transaction gerektiğinde seçerim (M5 tablosu).
- **Aurora yerine:** Erişim tek sahibe göre ve sorular önceden biliniyorsa, yazma saniyede binlerle ve on binlerle ölçülüyorsa, veri TTL ile kendiliğinden ölüyorsa Keyspaces. Sorular değişkense, JOIN, toplam ya da birkaç table'lık transaction gerekiyorsa ya da sık değişen bir alana göre sıralama varsa Aurora (kart 3, 9, M3).
- **Timestream for InfluxDB yerine:** Ham zaman serisi tek sahibe göre okunuyorsa, yazma yolu hiç durmamalıysa ve ekip CQL biliyorsa Keyspaces. Pencere hesabı (ortalama, tepe, aşağı örnekleme), dashboard ve sıkıştırma ana işse InfluxDB. Gerekirse ikisi birlikte (kart 2).
- **EC2'de Apache Cassandra yerine:** Kod secondary index, materialized view, UDF, ALL ya da EACH_QUORUM kullanmıyorsa ve işletme yükü (node, repair, compaction, sürüm) istenmiyorsa Keyspaces. Bu özelliklere gerçekten bağlıysan ve işletme ekibin varsa EC2 (kart 10, M5).
- **Redshift yerine:** Hiçbir zaman "yerine" değil, "yanında". Kişi başına okuma Keyspaces'te, tüm veri üzerindeki rapor CDC ile beslenen Redshift'te (kart 7, M4 soru 8).

Eksik olanlar:
1. **Para:** Meslektaşım "DynamoDB yerine Keyspaces kaça mal olur?" diye sorarsa cevap veremem. Sayfa birim fiyat ve örnek bir aylık hesap vermiyor. Kart 6 tam bu farka dayanıyor (R6).
2. **Taşıma yolu:** Kart 10'u savunabilirim, ama 40 TB'ın nasıl taşınacağını, hangi aracın kullanılacağını ve kesinti olup olmayacağını söyleyemem (R12).
3. **Sınıra dayanınca ne olur:** Throttling'in client'ta nasıl göründüğünü ve neyin yapılacağını söyleyemem. Multi-Region'da çakışmanın nasıl çözüldüğünü de bilmiyorum (R12).
4. **Puanların güvenilirliği:** Çift sayımlar ve satır karışıklıkları (R1–R5, R8–R10) yüzünden "Keyspaces şu kartta kaç puan farkla kazanır" cümlesini tam güvenle kuramam. Hangi tarafın kazandığına ise güvenirim.

## Kapanış (yazar)

Tarih 2026-10-31. Her bulgu ya sayfada / kart verisinde düzeltildi ya da yazılı bir gerekçeyle kapatıldı. Kontroller düzeltmelerden sonra yeniden çalıştı: `check_usecases.py --app <worktree>/app keyspaces` → `usecases: OK`; `check_page.sh --tr` → `clarity: OK`; simülasyon testi 9 simülasyon, 0 hata; 22 checkpoint'in hepsi açılıyor; 420 px pencerede yatay taşma yok; `dynamodb` ve `aurora` hâlâ `usecases: OK`. Yeni toplamlar: 1: 97,8 / 90,6 / 66,8 · 2: 91,2 / 88,4 / 85,2 (yakın yarış) · 3: 98 / 80,2 / 76,6 · 4: 92,2 / 88 / 78,2 · 5: 93,4 / 78,4 / 73,4 · 6: 95 / 86,4 / 80,2 · 7: 77 / 76,6 / 62 · 8: 98,8 / 88,2 / 75,8 · 9: 95,6 / 77 / 55,6 · 10: 95 / 74,8 / 74,4.

| Bulgu | Durum | Nasıl kapandı |
|---|---|---|
| R1 | düzeltildi | Kart 10'da DynamoDB'nin R1'i yalnız engine'i puanlar: R1.2 8 (tek sort key, clustering column'ların type'ı kaybolur), R1.3 10 ("söz dizimine çevirmek R4'te sayıldı"), R1.4 8 (süresi dolan item birkaç gün görünür; hikâye görünmemesini istiyor). Kod çevirisi yalnız R4'te. DynamoDB 74,8 ile ikinciye çıktı, ikiz Cassandra on EC2 74,4 ile üçüncü; kart sırası, karar ve M2 özeti / M7 metni güncellendi. Kural kapsam dosyasına yazıldı. |
| R2 | düzeltildi | DynamoDB'nin IAM iddiası kaldırıldı (PutItem üzerine yazar). Kafa kafaya paragrafı iki servisin değiştirilemezlikte eşit olduğunu ve nedenini söyler; dönme koşulu "denetçi iki listenin bir an bile farklı görünmemesini şart koşsaydı" oldu. Keyspaces R4'teki cassandra:Modify kırılımı kaldırıldı (R1.3'te sayılır). |
| R3 | düzeltildi | Kural: değişiklik akışının yokluğu yalnız R1 · YD'de, Lambda'ya bağlanması yalnız R4'te. Kart 3 Aurora R1.3 yalnız süre sonunu puanlar (6), tüketici bileşeni R4'e taşındı (5). Kart 6 ElastiCache R4 6 ("akışın yokluğu R1.3'te sayıldı"); kart 6 ve 8'in R4 "ne istiyoruz" metni yeniden yazıldı (Lambda bağlantısı, R1.3'ün cümlesini tekrar etmez). Kart 8 MemoryDB R1.1 10 (kırpma yalnız R1.3'te), R4 5. |
| R4 | düzeltildi | Kart 2: storage'ın büyüklüğü yalnız R1.3'te; R5 yalnız TTL delete (Keyspaces 9, DynamoDB 10), R5'in metni storage fiyatını artık istemez. InfluxDB R2 10 ("instance sınıfı R4'te sayıldı"); "tampon tutmaz" yalnız R3'te. InfluxDB 88,4 ile ikinciye çıktı, kart yakın yarış oldu; karar, kafa kafaya, M7 ve M2 özeti güncellendi. |
| R5 | düzeltildi | Kural sayfaya yazıldı (Mimar gözüyle, ağırlık paragrafı): kapasiteyi ayarlamak (ön ısıtma, instance sınıfı, node sayısı) R4, tepeyi karşılamak R2. Kart 1, 5, 10'da ön ısıtma R2'den R4'e taşındı (iki adayda da). Kart 7'deki kırılım beklenmeyen bir rekor sıçramadır ve R2'de kaldı. Kart 10 Cassandra'nın R2'si tahminin üstündeki büyümeyi karşılamaktır, R4'ü node ekleme işidir: ayrı mekanizmalar. |
| R6 | düzeltildi | Kart 6 R5 ağırlık nedeni fiyat modeline çevrildi; sayfa bilerek birim fiyat yazmaz (M2 girişi, bölgeye göre değişir, fiyat sayfası linkli). IoT Device Shadow karara eklendi: database değildir (cihazlar arası soru, akış, TTL yok), cihazla senkron için DynamoDB ile birlikte çalışır; M2 özetinde "ikisi birlikte" örneği. |
| R7 | düzeltildi | Aurora R2 gerekçesi bir yıllık sabit hacme göre yeniden yazıldı (128 TiB'ın altında; sorun tek writer ve 95 milyar row'luk B-tree), 3 → 4; R5 4 → 6 (yalnız fiyat modeli). Karara S3 Object Lock eklendi (arşivde değiştirilemezliğin asıl aracı) ve S3 + Athena'nın çevrim içi yıl için neden aday olmadığı yazıldı; CloudTrail Lake'i iç uygulamaların özel olayları için kapsam dışı bıraktım (kart bir database kararıdır). |
| R8 | düzeltildi | Kart 9 yeniden yapılandı: analistlerin JOIN'li yeni soruları R1 · EY'de (EY 22), R4 yalnız ekibin dilini puanlar (18). Index yokluğu yalnız EY'de, aggregate yokluğu yalnız AO'da, tombstone yalnız OY'de; R5'te ikinci kırılım yok. Keyspaces 55,6, DocumentDB 77 (EY'de JOIN kaybı). |
| R9 | düzeltildi / gerekçe | R5 "ne istiyoruz" metni performans şartı içermez; istek başına fiyat kırılımı DynamoDB'den kaldırıldı (iki on-demand aday eşit). Redshift R5 yalnız fiyat modeli. R1.2 (rapor) kaldı, gerekçesi: iş yükü bu soruyu sorar ve engine'in onu kendisi cevaplayamaması "ikisi birlikte" kararının nedenidir; karar ve M2 özeti bunu söyler. Fark 0,4'e indi (yakın yarış). |
| R10 | düzeltildi | Kural: R5 yalnız fiyat modelini puanlar, modelin ek yazmaları R1'de bir kez sayılır (sayfaya ve kapsam dosyasına yazıldı). Kart 3 ve 4'te R5 kırılımları kaldırıldı; kart 4'ün R5 metni yeniden yazıldı. |
| R11 | düzeltildi | B4'e "Keyspaces'te partition boyutu pratikte sınırsızsa büyük bir partition neden sorun?" kutusu eklendi: partition başına trafik sınırı (bölme trafiğe göredir), bütün partition'ı okuma / silme (range delete 1.000 row), taşımada 1.000 row'dan büyük partition'ların hot key yaratması; (x, day) tasarımının nedeni. |
| R12 | düzeltildi / kapsam | Eklenen kutular: B4 "geçmiş veriyi yeni table'a kim yazar" (çift yazma + Glue/Spark ile doldurma), B5 throttling (WriteTimeout/ReadTimeout, throttle metrikleri, backoff ile yeniden deneme), C2 40 TB taşıma (çevrim dışı Glue/S3, çevrim içi çift yazma ve ZDM proxy, kaynaklı) ve "aynı row'a iki yazma / çok bölge" (last writer wins, client-side timestamp, kaynaklı). Para hesabı kapsam dışı bırakıldı: sayfa birim fiyat yazmaz (bölgeye göre değişir), öğrenme hedefi birim sayısının hesabıdır; fiyat sayfası M2'de linkli. |
| R13 | düzeltildi | Kart 1 Keyspaces R5'ten storage cümlesi çıkarıldı; kırılım yalnız TTL delete ücretidir. |
| R14 | düzeltildi | R1 tablosunda EY kodunun katalogda olduğu söylendi; katalog AO hücresinde UDF ve CQL GRANT açıldı; kartlarda "item collection" ve "expires_at" yerine açık ifadeler; B1'de Engine App tanımlandı; terim tablosunda RRU/WRU/RCU/WCU ve SigV4 açıldı. clarity: OK. |
| R15 | düzeltildi | C3: seviye uygulamanın ExecutionProfile ayarıdır; Python driver'ının kendi varsayılanının LOCAL_ONE olduğu yazıldı (engines/keyspaces.py ile doğrulandı). |
| R16 | kısmen düzeltildi / gerekçe | "R3 ve R4 14'er", A7 parantezi, A9 cümlesi ("Hayır. … doğrudan tetiklemez") ve iki İngilizce alıntının Türkçesi düzeltildi. "X ile kafa kafaya, Y: Y ile kafa kafaya" başlığı ve "Karar. Karar:" ortak `wusecase` makrosunun etiketinden ve skill'in zorunlu cümle başlarından gelir (writing-rules: head-to-head "<Kategori> (<Servis>) ile kafa kafaya." ile, verdict "Karar:" ile başlar); paylaşılan parçalar bu görevde değiştirilemez. Skill boşluğu olarak raporlandı. |
| R17 | düzeltildi | A4 cluster görseli altyazısı: okların halkayı gösterdiği, replica'ların komşu olmak zorunda olmadığı ve node sayılarının (3, 6, 4) örnek olduğu yazıldı. |
| R18 | düzeltildi | M7 renk açıklaması: bu simülasyonlarda yalnız "eşleşti" ve "sonuçta yeni" kullanılır, diğer işaretler mekanizma simülasyonları içindir. B2 tahmin cevabı öğretici kopya ile canlı partition farkını söyler. |
