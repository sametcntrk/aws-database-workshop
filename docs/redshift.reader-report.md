# Reader simulation: Amazon Redshift Serverless (redshift), Türkçe sayfa, model 2
Tarih: 2026-10-31
Okuyucu: data warehouse ve Redshift'i hiç kullanmamış, biraz SQL bilen, aynı sitenin DynamoDB ve Aurora sayfalarını okumuş bir geliştirici. Kaynak: /tmp/rs_w/redshift.tr.txt (baştan sona), /tmp/rs_w/page.html (görseller, kart tabloları, simülasyon JSON'u), canlı önizleme http://localhost:8797/e2etutorial/redshift, karşılaştırma için /e2etutorial/aurora (uc-reporting) ve /e2etutorial/keyspaces (uc-clicks); kural referansı decisions.md ve reader-questions.md bölüm 1.

## Genel izlenim

Bölüm A çok iyi okunuyor. Seçim gecesi analojisi, sekiz row'luk öğretici table, zone map blokları ve slice yerleşimi, hiç warehouse görmemiş birine "neden kolon kolon" sorusunu sayılarla cevaplıyor. Ö1–Ö8 listesi ve M1'in "sınırı" sütunu kartlarda gerçekten kullanılıyor. B bölümündeki canlı çıktılar (svv_table_info, pg_table_def, result cache 125 ms → 3 ms, sys_serverless_usage) güven veriyor.

Kartlarda aritmetik temiz: on kartın her hücresi, R1 ara toplamları, toplamlar ve özet tablodaki farklar doğru. Beş simülasyonun son adımı kart toplamlarıyla birebir aynı. Kart 1 Aurora sayfasının uc-reporting kartıyla, kart 4 Keyspaces sayfasının uc-clicks kartıyla aynı satırları, ağırlıkları ve puanları taşıyor (48 hücrenin 48'i eşit; gerekçelerde sadece Ö numaraları farklı).

Sorunlar puanlamanın tutarlılığında ve fiyat karşılaştırmasında. Aynı zayıflık bazı kartlarda iki satırda sayılıyor (sort key tasarımı R1 · AO ve R4'te; Athena'nın yeniden taraması R1 ve R5'te; akış katmanı dört satırda). Kart 8'deki fiyat karşılaştırması farklı vadeleri karşılaştırıyor ve bir yüzde yanlış. Birkaç "bir koşul değişseydi" cümlesi, kartın kendi sayılarıyla tutmuyor. Bir görsel altyazısı resimde olmayan bir şeyi tarif ediyor.

## Bulgular

### R1 (yüksek): Kart 8'de Serverless ile provisioned fiyatı farklı vadelerle karşılaştırılıyor ve yüzde yanlış
Bölüm: M2 kart 8 (Redshift R5 gerekçesi, kafa kafaya, karar), M7 checkpoint 3. Alıntı: "bir yıllık rezervasyonla yaklaşık 6.167 USD (0,352 USD/RPU-saat). 3 puan kırıldı: düz yükte saniye başına ödeme bir avantaj getirmez ve provisioned rezervasyondan yaklaşık yüzde 20 pahalıdır."
Tür: sayı / karar gerekçesi
Sorun: 6.167 / 4.946 = 1,247; Serverless yaklaşık yüzde 25 daha pahalıdır (provisioned yüzde 20 daha ucuzdur). Karar paragrafı "yüzde 20 ucuzdur" diye doğru yazıyor ama R5 gerekçesi tersini yanlış yazıyor. Daha önemlisi provisioned üç yıllık, Serverless bir yıllık rezervasyonla karşılaştırılıyor. Okuyucu provisioned'ın bir yıllık rezervasyon fiyatını göremiyor. M5'teki on demand fiyatıyla (3,894 USD/saat) kendisi hesaplayınca dört ra3.4xlarge on demand ayda yaklaşık 11.370 USD tutuyor, yani Serverless on demand'dan (7.902 USD) pahalı. Flip koşulu "üç yıllık taahhüt kabul edilmeseydi" bu yüzden belirsiz kalıyor: bir yıllık taahhütte hangisi kazanır? Ayrıca "aynı bellek (384 GB)" eşdeğerliğinin neden doğru ölçü olduğu söylenmiyor.
Mimara soru: Bir yıllık rezervasyonlu dört ra3.4xlarge ayda ne tutuyor? İki servisi aynı vadede karşılaştırınca fark ve R5 puanları değişiyor mu? Bellek eşitliği yerine hangi ölçüyle (aynı sorgu süresi) eşitlediniz?

### R2 (yüksek): Sort key ve distribution tasarımı aynı kartta hem R1 · AO'da hem R4'te kırılıyor
Bölüm: M2 kart 1, 2, 8, 9 (Redshift gerekçeleri). Alıntı (kart 1): R1.3 "1 puan kırıldı: sort key ve distribution seçimi bir tasarım işidir." ve R4 "1 puan kırıldı: sort key ve workgroup ayarları ekibin işidir."
Tür: zayıflık iki kez sayılıyor (kural 2)
Sorun: Aynı tasarım işi bir kartta iki kez puan kaybettiriyor. Kart 2'de R1.3 -1 ve R4 -2 ("sort key ile workgroup ayarları"), kart 8'de Serverless R1.3 -1 ve R4 -1 ("base RPU, en fazla RPU sınırı ve sort key"), kart 9'da R1.3 -1 ("sort key ve materialized view tasarımı") ve R4 -1 ("materialized view'ların yenileme planı"). Kart 1 Aurora sayfasıyla paylaşıldığı için düzeltme iki sayfaya dokunur. Kart 6'da da aynı gerekçe R1.4 · AO'da duruyor ama orada istek sort key'den hiç söz etmiyor (bkz. R9).
Mimara soru: Sort key tasarımı engine'in bir aracının bedeli mi (R1 · AO), yoksa ekip işi mi (R4)? Hangisiyse diğer satırdan çıkarınca toplamlar ve sıralar değişiyor mu?

### R3 (yüksek): Athena'nın yeniden taraması önce R1'de, sonra R5'te kırılıyor
Bölüm: M2 kart 7, 2, 5 (Athena gerekçeleri ve kafa kafaya). Alıntı (kart 7): R1.1 "inverted index yoktur; her arama yedi günün message kolonunu baştan okur." ve R5 "5 puan kırıldı: olay anındaki her arama yedi günün TB'larını tarar"; kafa kafaya: "her arama yedi günün message kolonunu baştan okur ve her seferinde ödenir (R1.1, R5)."
Tür: zayıflık iki kez sayılıyor (kural 6: R5 sadece fiyat modelini puanlar)
Sorun: Engine'in zorladığı fazla okuma R1'de sayılmış, R5'te de aynı okuma için puan kırılmış. Kart 2'de R1.3 "gün içindeki her kesit sonucu yeniden okur" ve R5 "gün içindeki her kesit yeniden ödenir"; kart 5'te R5 "kampanya sorguları her seferinde TB'larca veriyi yeniden tarar ve ödenir". Kart 2 yakın bir yarış (4,6 puan) olduğu için bu 1,4 puanlık çift sayım sonucu etkileyebilir. Redshift aynı kartlarda tekrar eden sorgu ve 60 saniyelik minimum için R5'te aynı biçimde kırılmıyor.
Mimara soru: TB başına ödeme bu trafiğe kendi başına uymuyor mu, yoksa sadece engine'in fazla okumasının sonucu mu? İkincisiyse R5 puanı 10 olmalı mı?

### R4 (orta): Kart 2'nin yakın yarışını, bu veride zayıf görünen bir mekanizma belirliyor
Bölüm: M2 kart 2 (R1.3 isteği, Athena R1.2 ve R1.3, karar). Alıntı: R1.3 isteği "Tıklamalar ve siparişler customer_id'ye göre aynı yerde durmalı"; Athena R1.2 "2 puan kırıldı: dosyalar müşteriye göre bir arada durmaz; her sabah iki büyük table'ın eşleşen row'ları join için ağ üzerinden yeniden dağıtılır."
Tür: ikna etmeyen gerekçe / isteğin bir adayın mekanizmasıyla yazılması
Sorun: Fark 4,6 puan ve Athena'nın R1.2 ile R1.3'te kaybettiği 5,8 puan sonucu belirliyor. Ama siparişler yılda yaklaşık 7 milyon row; 900 milyon tıklamanın yanında küçük bir table'dır ve bir dağıtık engine onu genellikle her işçiye gönderir (broadcast). "İki büyük table" ifadesi hikâyenin sayılarıyla tutmuyor. Ayrıca ağ üzerinden yeniden dağıtım bir depolama algoritması (DA) sorunu değil, dağıtım sorunu. R1.3'ün isteği bir çözümü yazıyor (aynı yerde durmak, yani Redshift'in DISTKEY'i) ve bir hedef yazmıyor (join 30 dakikalık pencereye sığmalı). Yakın yarışta R5 için aylık sayı da yok.
Mimara soru: 7 milyon siparişin join'i Athena'da 08:30'u gerçekten kaçırtıyor mu? İstek "aynı yerde dursun" değil "join 30 dakikaya sığsın" olsaydı Athena'nın puanı ne olurdu? İki servisin aylık faturası ne?

### R5 (orta): Kart 5'te Athena hikâyede olmayan bir join için ve verinin bugünkü yeri için R1'de kırılıyor
Bölüm: M2 kart 5 (Athena R1.2, R1.4, R4). Alıntı: R1.2 "2 puan kırıldı: dosyalar müşteriye göre bir arada durmaz; büyük join'lerde eşleşen row'lar her sorguda ağ üzerinden yeniden dağıtılır." ve R1.4 "3 puan kırıldı: veri önce Redshift'ten S3'e aktarılır ve tüketici aktarımın son hâlini görür"
Tür: hikâyede olmayan durum için kırılma; R1'de paketleme ya da var olan sistem sayılıyor
Sorun: Kart 5'in R1.2 isteği "iki milyar row'un birkaç kolonunu okuyan taramalar" diyor, join'den söz etmiyor. Gerekçe kart 6'dan kopyalanmış gibi. R1.4'teki kırılmanın nedeni engine değil, verinin bugün Redshift'te durması. Iceberg'in kendisi her commit'te tutarlı bir ân veriyor; bunu gerekçe de söylüyor. Aynı aktarım R4'te bir kez daha 5 puan kaybettiriyor.
Mimara soru: Veri S3'te olsaydı Athena'nın R1.4 puanı 10 mu olurdu? Olursa bu kırılma R1'de değil R4'te mi durmalı?

### R6 (orta): Kart 4 ve 7'de akış katmanı dört satırda sayılıyor ve kart 4'te yeniden yazma iki servise farklı puan kaybettiriyor
Bölüm: M2 kart 4 (Redshift R2, R3, R4, R5; DynamoDB R4), kart 7 (Redshift R2, R3, R4, R5). Alıntı (kart 4): DynamoDB R4 "5 puan kırıldı: sessionization işleri Cassandra connector'ından DynamoDB'ye yeniden yazılır; hikâye bunu iki ay olarak verir." Redshift R4 "4 puan kırıldı: sessionization işleri Spark Cassandra Connector'ından Redshift'e taşınır ve bir akış katmanı işletilir."
Tür: aynı mekanizmaya farklı kırılma; kapasite bilgisinin hem R2 hem R4'te sayılması (kural 3)
Sorun: Redshift iki aylık yeniden yazmanın üstüne bir akış katmanı da işletiyor ama DynamoDB'den daha az puan kaybediyor (6'ya karşı 5). Akış katmanı kart 4'te R2 ("o katman da ölçeklenir"), R3, R4 ve R5'te geçiyor. R2'deki gerekçe tepenin karşılanıp karşılanmadığını söylemiyor; "o katman da ölçeklenir" bir kapasite ayarıdır ve kural 3'e göre R4'e aittir. Okuyucu 40.000 yazma/sn tepesinin Redshift'te karşılanıp karşılanmadığını öğrenemiyor. Kart 7'de aynı yapı var (R2 -5, R4 "akış katmanı işletilir"). Kart 4 Keyspaces sayfasıyla paylaşıldığı için düzeltme iki sayfaya dokunur.
Mimara soru: 40.000 yazma/sn tepesinde Kinesis ile streaming ingestion yetişiyor mu, yetişmiyor mu? Yetişiyorsa R2'deki 5 puan neyin kaybı? Redshift'in R4'ü DynamoDB'ninkinden neden yüksek?

### R7 (orta): Kart 3, A7'deki varsayılan yalıtım seviyesiyle çelişiyor
Bölüm: M2 kart 3 (Redshift R1.4) ve A7 ("Aklına şu gelebilir: İki kişi aynı anda yazarsa"). Alıntı: kart 3 "Transaction'lar serializable seviyededir"; A7 "Redshift'te varsayılan seviye SNAPSHOT, istenirse SERIALIZABLE'dır."
Tür: anlaşılmayan cümle / çelişki
Sorun: Okuyucu hangisinin doğru olduğunu bilemiyor. Ayrıca kart 3'ün asıl sorusu "400 sorgu üç gün boyunca aynı ânı görmeli" ve bunun cevabı yalıtım seviyesinden değil, CREATE TABLE AS kopyasından geliyor. "Serializable" kelimesi bu kartta neden gerekli, anlaşılmıyor. R1.4 gerekçesinde zero-ETL (bir servis paketlemesi) de geçiyor.
Beklenen: "Varsayılan SNAPSHOT'tır; bir düzeltmenin satırları tek transaction'da yazılır" gibi A7 ile aynı bilgi.
Mimara soru: Lale Market'in Serverless workgroup'unda yalıtım seviyesi hangisi, ve kart 3 bunu neden önemsiyor?

### R8 (orta): Kart 3'te Aurora, hikâyede olmayan checkout için R2'de 5 puan kaybediyor
Bölüm: M2 kart 3 (Aurora R2). Alıntı: "5 puan kırıldı: reader'lar checkout ile aynı storage'ı okur ve 400 ağır sorgu storage I/O'sunu paylaşır"
Tür: hikâyede olmayan durum için kırılma
Sorun: Kart 3'ün hikâyesi "muhasebe defteri Aurora'dadır" diyor; defterin checkout cluster'ında olduğunu söylemiyor. R2 isteği de checkout'tan söz etmiyor: "12 kişinin eşzamanlı ağır sorguları beklemeden dönmeli". Kırılma kart 1, 2, 8 ve 9'dan kopyalanmış görünüyor. Kart 3, Aurora'nın R1'i kazandığı "dürüst kart" olduğu için bu kırılma önemli.
Mimara soru: Defter ayrı bir Aurora cluster'ındaysa Aurora'nın R2 puanı ne olur? 12 eşzamanlı sorgu için Serverless v2 reader yeter mi?

### R9 (orta): Kart 6'da model eğitimi bir serviste R1'de, diğerinde R4'te sayılıyor; Redshift'in AO kırılması isteğe uymuyor
Bölüm: M2 kart 6 (R1.4 · AO isteği, Redshift R1.4, Athena R1.4, Aurora R4). Alıntı: istek "basit bir model SQL'den eğitilip SQL içinde tahmin yapabilmeli"; Redshift R1.4 "Redshift ML CREATE MODEL ile SQL'den model eğitir ... 1 puan kırıldı: sort key ve distribution seçimi bir tasarım işidir."
Tür: R1'de paketleme (kural 5) / gerekçe isteğe uymuyor
Sorun: Redshift ML eğitimi SageMaker AI'da çalıştırır; bu bir entegrasyondur, engine'in kendi aracı değildir. R1'de Redshift artı alıyor, Athena "SQL'den model eğitme aracı yoktur" diye kırılıyor, Aurora'nın SageMaker entegrasyonu ise R4'te sayılıyor. Aynı tür özellik üç adayda iki farklı satırda. Redshift'in 1 puanlık kırılması da isteğin iki parçasından (ara sonuç, model) hiçbirine değil, sort key'e bağlanmış.
Mimara soru: SQL'den model eğitimi bir engine uyumu mu, bir entegrasyon mu? Entegrasyonsa üç aday R4'te aynı biçimde puanlanınca sonuç ne olur?

### R10 (orta): Bazı "bir koşul değişseydi" cümleleri kartın kendi sayılarıyla tutmuyor
Bölüm: M2 kart 5 ve kart 6 (kafa kafaya ve karar). Alıntı (kart 5): "Bir koşul değişseydi: veri zaten S3'te Iceberg table'ları olarak dursaydı Athena ile Lake Formation öne geçerdi."
Tür: ikna etmeyen karar gerekçesi (flip koşulu)
Sorun: Okuyucu hesaplıyor. Kart 5'te veri S3'te olsa Athena R4'te en fazla 5 → 9 (+7,2) ve R1.4'te 7 → 10 (+2,4) kazanır: 77,8 → yaklaşık 87,4. Bu, Redshift'in 94,8'inin altında kalıyor; R1.3 (row kuralı) ve R2 değişmiyor. Kart 6'da "kaynak veri S3'te olsaydı ve iş haftada bir çalışsaydı": R4 5 → 9 (+8) ile 78,8 → 86,8, yine 91,4'ün altında; "haftada bir" hangi satırı değiştiriyor, söylenmiyor. Flip cümlesi bir tahmin gibi okunuyor, kartın puanlarından çıkmıyor.
Mimara soru: Bu koşulda hangi satırlar kaç puan değişiyor ve yeni toplam ne? Değişen satırlar yetmiyorsa koşul ne olmalı?

### R11 (orta): Row storage görselinin altyazısı resimde olmayan bir şeyi tarif ediyor
Bölüm: A3, ilk AWS görseli. Alıntı: "Turuncu çerçeve bir disk bloğudur ve üç row'un bütün kolonlarını tutar: SSN, Name, Age, Addr, City, St."
Tür: görsel altyazısı
Sorun: Resimde turuncu çerçeve tek bir row'u (CHIN) ve onun yazıldığı Block 2'yi gösteriyor. Alttaki şeritte her blok tek bir row tutuyor (Block 1, 2, 3). Okuyucu altyazıya göre üç row'luk bir blok arıyor ve bulamıyor. Column storage görselinde ise çerçeve gerçekten birçok row'un SSN değerlerini tutan Block 1'i gösteriyor; iki resmin karşılaştırması tam bu farkı öğretmeliydi.
Beklenen: "Turuncu çerçeve bir row'dur (CHIN) ve bütün kolonlarıyla tek bir blokta (Block 2) durur; her blok bir row tutar."
Mimara soru: (yazara) Altyazı resme göre düzeltilebilir mi, yoksa farklı bir resim mi kastedildi?

### R12 (orta): Sayfanın cevaplamadığı "ya ... ise?" durumları
Bölüm: M2 kart 9, kart 3, kart 4, kart 5; B5.
Tür: eksik durum
- Kart 9 ve B5: "Gece ve hafta sonu compute ödenmez" ve "compute boştayken durur, ilk sorgu geldiğinde yeniden başlar" (A9). Pazartesi 09:00'da hafta sonu boyunca boş duran workgroup'a gelen ilk 300 kutu sorgusu iki saniye sınırının altında mı döner? Boştan başlamanın bir gecikmesi var mı? Sayfa söylemiyor; kartın R2'si tam bu dalgayı puanlıyor.
- Kart 3: "araç bu kayıtları kapanış raporlarının çalıştığı database'e yazar". B4'e göre zero-ETL kopyasına yazılamaz. Redshift'te düzeltmeler nereye yazılıyor (ayrı bir yerel table mı)? Mizan bu table'ı kopya ile nasıl birleştiriyor?
- Kart 4: Redshift'in R1.1 gerekçesi "sort key'i okuyucu ve zaman olan bir table" diyor; R1.2 haftalık raporu kategori ve saate göre gruplayan taramayla 10 alıyor. A5'e göre bir table'ın tek bir sırası var. İki soru aynı table'da hangi sort key ile karşılanıyor?
- Kart 5: "oturumun tedarikçisine göre filtreleyen bir view". 120 tedarikçinin her biri ayrı bir database kullanıcısı mı? View oturumdaki tedarikçiyi nereden biliyor (current_user ile bir eşleme table'ı mı)? Kartın en önemli kuralı (sözleşme ihlali) bu mekanizmaya dayanıyor.
- Genel: en fazla RPU sınırına ulaşan bir sorgu ne olur: bekler mi, hata mı alır? B5 sadece "sınır yoksa durmaz" diyor.
Mimara soru: Bu beş durumun her biri için bir cümle ve bir kaynak eklenebilir mi?

### R13 (düşük): Kart 7'de VM puanları isteğe göre ters sırada
Bölüm: M2 kart 7 (R1.2 · VM, Redshift ve Athena). Alıntı: Redshift "7→ 5,6 ... değişen alanlar ya SUPER içinde kalır ve her sorguda yol ifadesiyle açılır ya da kolon olmaları için ALTER TABLE gerekir"; Athena "8→ 6,4 ... yeni alanlar table tanımına eklenmeden sorgulanamaz."
Tür: ikna etmeyen gerekçe
Sorun: İstek "yeni bir alan hemen sorgulanabilmeli" diyor. Gerekçeye göre Redshift'te SUPER içindeki yeni alan hemen bir yol ifadesiyle sorgulanabiliyor; Athena'da önce table tanımı değişmeli. Okuyucuya göre Redshift isteği daha iyi karşılıyor ama daha az puan alıyor.
Mimara soru: Yol ifadesiyle açmanın bedeli nedir ki Athena'nın tanım değişikliğinden daha ağır sayılıyor?

### R14 (düşük): Kart 3 ve 8'deki kapasite varsayımları açıklanmıyor; bir fiyatın birimi belirsiz
Bölüm: M2 kart 3 (Redshift R5, provisioned R5), kart 8, B5. Alıntı: "3 gün × 10 saat × 32 RPU = 960 RPU-saat" ve "iki ra3.xlplus eu-central-1'de ayda yaklaşık 1.895 USD (1,298 USD/saat)"
Tür: sayı
Sorun: Hesap doğru (960 × 0,451 ≈ 433 USD; 2 × 1,298 × 730 ≈ 1.895 USD). Ama 32 RPU neden seçildi, söylenmiyor: varsayılan base 128, Lale Market 8, kart 8'de 24 RPU. 12 eşzamanlı ağır sorgu için 32 RPU'nun yetip yetmediği belli değil. "1,298 USD/saat" iki düğümün toplamı gibi okunuyor ama düğüm başı fiyat; kart 8'deki "1,6939 USD/saat" da öyle. Okuyucu ilk okumada aylık rakamı tutturamıyor.
Mimara soru: 32 RPU hangi ölçümden ya da kuraldan geliyor? Fiyatların yanına "düğüm başına" yazılabilir mi?

### R15 (düşük): Bazı terimler tanımlanmadan geçiyor
Bölüm: çeşitli. Alıntılar: A4 "sadece genel sıkıştırma (örneğin TOAST)"; A10 matris "(Limitless ayrı bir üründür)"; A6 "kapasite RPU olarak verilir (B5)" (RPU ilk kez burada, tanım M2 terimler tablosunda); B1 "dolu slice sayısı × segment sayısı"; kart 1 OpenSearch "SQL ve PPL desteği vardır"; kart 7 Athena "JSON SerDe"; kart 10 "partition projection"; M5 "SageMaker AI Autopilot"; C2 "ANALYZE", "Elastic resize"; B4 "Redshift namespace'i" (tanım C2'de).
Tür: tanımsız terim
Sorun: Her biri cümleyi bir an durduruyor. Kart 1'de ayrıca "column" kelimesi kullanılıyor, sayfanın geri kalanı "kolon" diyor; okuyucu iki ayrı şey sanabilir.
Beklenen: Terimler tablosuna ya da ilk geçtiği cümleye yarım cümlelik bir tanım; kart 1'de "kolon".

## Aritmetik ve simülasyon kontrolü (madde 5)

- On kartın her hücresinde katkı = puan × ağırlık / 10 doğru. R1 ara toplamları ve toplamlar doğru (örnek: kart 4 Redshift 5,6 + 14 + 4 + 6 = 29,6; + 9 + 5,4 + 10,8 + 7,2 = 62).
- Özet tablodaki farklar doğru: 29,8 / 4,6 / 14,4 / 0,4 / 15 / 12,6 / 23,2 / 3,2 / 22,8 / 5,2. "Yakın yarış" işaretleri (kart 2, 4, 8) doğru; kart 10 5,2 ile sınırın hemen üstünde ve işaretsiz.
- Beş simülasyonun (kart 1, 2, 8, 4, 7) son adımındaki puan tablosu, R1 ara toplamı, toplam ve sıra kartlarla birebir aynı; son adımın metni kartın karar paragrafı.
- Kart 1 = Aurora uc-reporting ve kart 4 = Keyspaces uc-clicks: ağırlıklar ve 48 hücrenin hepsi eşit.
- Fiyat aritmetiği: kart 3 (433 USD, 1.895 USD), kart 8 (4.946, 7.902, 6.167 USD) ve B5 (1,62 USD, 15,58 USD) doğru. Tek yanlış kart 8'deki "yüzde 20 pahalı" (bkz. R1).

## Son soru: bir meslektaşa anlatabilir miyim?

Büyük ölçüde evet.
- **Aurora yerine Redshift:** Sorgu geçmişin tamamını tarıyor, birkaç kolon okuyor ve checkout bunu hissetmemeli. Raporlar son 90 günle sınırlıysa ve analist sayısı azsa Aurora'nın reader'ı yeter. Kurallar (CHECK, foreign key) database'te korunmalıysa yazma tarafı Aurora'da kalır (kart 1, 3). Bunu anlatabilirim.
- **Keyspaces yerine Redshift:** Sadece rapor varsa Redshift. Tek okuyucunun son N kaydı 20 ms'de isteniyorsa bu bir point lookup'tır ve Keyspaces ya da DynamoDB'ye gider; rapor CDC ile Redshift'e akar (kart 4). Anlatabilirim; tek eksik iki sorunun aynı table'da hangi sort key ile çalışacağı.
- **OpenSearch yerine Redshift:** Metin araması yoksa ve iş toplamlar ile satış verisiyle join ise Redshift; kelime araması ve hazır log ekranı istenirse OpenSearch (kart 7, 1, 9). Anlatabilirim.
- **Athena yerine Redshift:** Kural olarak anlatabilirim: sorular seyrek ve veri S3'te kalmalıysa Athena; tekrar eden, panoya dönüşen ya da warehouse table'larıyla join'lenen sorularda Redshift. Ama eşiği sayıyla veremem. Kart 2 ve 10'da aylık fatura yok; "günde yüzlerce soru" ya da "haftada bir" eşiğinin nereden geldiği gösterilmiyor. Kart 2'nin farkını belirleyen join gerekçesi de bu veride zayıf (R4). Eksik: iki servisin aynı iş yükü için aylık maliyeti ve fiyatların kesiştiği sorgu sayısı ya da TB.
- **Redshift provisioned yerine Serverless:** Kural olarak anlatabilirim: boşluklu yükte Serverless, 7/24 düz yükte rezervasyonlu provisioned. Ama kart 8'in sayıları üç yıllık ile bir yıllık rezervasyonu karşılaştırıyor; bir yıllık taahhütte ya da taahhütsüz durumda hangisinin kazandığını söyleyemem (R1). Eksik: aynı vadede iki fiyat ve eşdeğer kapasitenin nasıl seçildiği.

## Kapanış (yazar)
| Bulgu | Durum | Ne yapıldı |
|---|---|---|
| R1 | kapandı | Kart 8 artık aynı vadeleri ayrı ayrı gösterir: Price List API'da Serverless rezervasyonu yalnız bir yıllıktır (0,352 USD/RPU-saat, ayda yaklaşık 6.167 USD); düğümler bir yıllık peşinatsız 2,7258 USD/saat (dört düğüm ayda yaklaşık 7.959 USD), üç yıllık peşinatsız 1,6939 USD/saat (yaklaşık 4.946 USD). Provisioned'ın avantajı sadece üç yıllık taahhütten gelir; bu kartın hikâyesi üç yıllık taahhüdü kabul eder. Yüzdeler düzeltildi: Serverless yaklaşık yüzde 25 pahalı, provisioned yaklaşık yüzde 20 ucuz. Koşul cümlesine "taahhüt bir yılla sınırlı olsaydı" eklendi; M5'e bir yıllık fiyat ve "bir yıllık vadede Serverless daha ucuzdur" yazıldı. Puanlar aynı. |
| R2 | kapandı | Tek kural uygulandı (decisions.md kural 3): tablo tasarımı (sort key, distribution, materialized view) R1 · AO'da, kapasite ayarı (base ve en fazla RPU, COPY zamanlaması) R4'te. Kart 1, 2, 3, 8 ve 9'un Redshift R4 gerekçeleri sadece workgroup kapasitesini sayar ve tasarımın R1'de sayıldığını söyler. Puanlar değişmedi; kart 1'in puanları Aurora sayfasıyla aynı kalır. |
| R3 | kapandı | Kural 6 uygulandı: Athena'nın R5 gerekçeleri artık sadece fiyat birimini (taranan TB başına, tavan yok, sorgu sayısıyla büyür) puanlar; yeniden okuma R1'de kalır. Kart 7'de Athena R5 5'ten 7'ye çıktı (toplam 64,4; sıra değişmedi). Kart 2 ve 5'te gerekçeler yeniden yazıldı, puanlar aynı. |
| R4 | kapandı | Kart 2'de R1.3'ün isteği engine'den bağımsız yazıldı ("join'in ve taramanın maliyeti engine'in araçlarıyla azaltılabilmeli"). Athena'nın R1.2 gerekçesi artık join'i değil dosyaların click_time'a göre sıralı olmamasını sayar; yeniden dağıtım sadece R1.3'te. R5'e kaba aylık rakamlar eklendi: Athena birkaç on USD, Redshift sabah işi yaklaşık 216 USD ve ikinci kopya. R5 bu yarışı belirlemez (Athena R5'te öndedir); yarışı R1.2–R1.3 belirler. |
| R5 | kapandı | Kart 5'te Athena'nın R1.2'si 9'a çıktı (hikâyede join yok; kırılım kart 10 ile aynı: sırasız dosyalar), R1.4'ü 9'a çıktı (Iceberg snapshot'ı engine özelliğidir; verinin bugün Redshift'te durması ve aktarım gecikmesi sadece R4'te). Athena 80,6 ile ikinci oldu, Redshift provisioned 79,8 ile üçüncü; kart, karar ve kafa kafaya metinleri buna göre değişti. |
| R6 | kapandı (gerekçe ve metin) | Kart 4'ün puanları Keyspaces sayfasının 7. kartıyla aynıdır; iki sayfada birlikte değişmeden değiştirilmedi (decisions.md, "The same workload on two pages"). Gerekçeler netleştirildi: R2 artık tepenin akış katmanıyla karşılandığını ve kaybın görünürlüğün materialized view yenilemesine bağlı olmasından geldiğini söyler (kapasite ayarı değil); R4'te Redshift'in DynamoDB'den 1 puan önde olmasının nedeni yazıldı: analistlerin SQL'i aynı sistemde çalışır, DynamoDB'de SQL için yine Redshift'e bir kopya gerekir. Kart 7'nin R2'si aynı kırılımı aynı gerekçeyle taşır. Sahibe not: R3–R5'teki akış katmanı kırılımları farklı yönleri sayar (son saniyelerin yeniden oynatılması, işletme, ödeme); iki sayfada birlikte gözden geçirmek isterse kart 4 ve Keyspaces kart 7 tek değişiklikle güncellenmelidir. **Ortak düzeltme (2026-10-31, "E2E model 2: one reduction per mechanism across pages"):** kart 4 ve Keyspaces kart 7 tek değişiklikle güncellendi. Redshift R2 5 → 8: tepeyi akış katmanı karşılar; kalan kırılım Keyspaces ve DynamoDB ile aynıdır (yeni bir rekor sıçrama on-demand stream'in son 30 günlük tepenin iki katı sınırını aşabilir); şeridin 20 ms'si R1.1'de, akış katmanının işletilmesi R4'te sayılır. Redshift R4 6 → 4: yeniden yazma DynamoDB ile aynı 5 puan, akış katmanının işletilmesi 1 puan; SQL iki adayı ayırmaz (DynamoDB'de de zero-ETL ile kod yazmadan gelir). Redshift toplamı 62 → 63,8, sıra değişmedi. Kart 7'nin R2'si 5 → 8 (yalnız görünürlüğün materialized view yenilemesine bağlı olması, 2 puan); Redshift kart 7'de Athena'nın önüne, ikinciliğe çıkar (67,8 ve 64,4). |
| R7 | kapandı | Kart 3: "SNAPSHOT (varsayılan) ya da SERIALIZABLE izolasyon" yazıldı; A7 ile aynı. |
| R8 | kapandı | Kart 3'ün hikâyesine defterin siparişlerle aynı Aurora cluster'ında olduğu yazıldı; Aurora R2 gerekçesi buna bağlandı. |
| R9 | kapandı | Kart 6: R1.4 (AO) isteği sadece saklanan ve artımlı yenilenen ara sonuçları sorar. Redshift ML R4'e taşındı (servis paketlemesi, eğitim SageMaker AI'da). Redshift'in AO kırılımı artık isteğe bağlı: artımlı yenileme window function'lı tanımları kapsamaz. Athena'nın AO gerekçesinden "model eğitme aracı yok" çıkarıldı. Puanlar aynı. |
| R10 | kapandı | Koşullar yeniden hesaplandı. Kart 5: veri S3'te Iceberg olsa bile Redshift önde kalır (kabaca 95'e 86); Athena ancak paylaşılan veri seyrek sorulan bir veri gölü olduğunda öne geçer (kart 10). Kart 6: veri S3'te ve iş haftada bir olursa fark kabaca 3 puana iner; Athena'yı öne geçirmek için ekipte hiç warehouse olmaması da gerekir (Redshift R4 düşer). Karar ve kafa kafaya metinleri bunu söyler. |
| R11 | kapandı | Altyazı yeniden yazıldı: üstte turuncu çerçeve CHIN'in row'u, altta aynı row Block 2'de bütün kolonlarıyla; her blok tam row'lar tutar. |
| R12 | kapandı | Beş durum eklendi: B5'e "Saatlerce boş duran bir workgroup'a ilk sorgu gelince ne olur?" kutusu (başlama süresi ödenmez, ilk sorgu bekler; kaynak fiyat sayfası) ve kart 9 R2'sine pazartesi ilk sorgusu; kart 3 key satırına düzeltmelerin Redshift'in dev database'inde ayrı bir adjustments table'ına yazıldığı (zero-ETL kopyası salt okunur); kart 4 R1.1'e tek sort key çatışması; kart 5'e view'ın current_user'ı bir eşleme table'ında tedarikçi id'sine çevirdiği; B5 tablosuna en fazla RPU'da compute'un daha fazla büyümediği ve RPU-saat sınırında seçilen eylemin uygulandığı. |
| R13 | kapandı | Kart 7 R1.2: Redshift (SUPER, yeni alan schema değişikliği olmadan) 8, Athena (her yeni alan bir tanım güncellemesi) 7. Toplamlar: Athena 64,4, Redshift 62,4; sıra aynı. |
| R14 | kapandı | Kart 3: 32 RPU'nun kaba bir ortalama varsayımı olduğu yazıldı. Kart 8: 24 RPU = 384 GB = dört ra3.4xlarge × 96 GiB açıklaması duruyor; düğüm fiyatlarının düğüm başına olduğu kart 3, kart 8, M5 ve terimler tablosunda yazıldı. |
| R15 | kapandı | Tanımlar eklendi: TOAST (A4 tablosu), Limitless (A10 ad paragrafı), PPL, SerDe, partition projection, Autopilot, elastic resize (terimler tablosu), segment (B1), ANALYZE (C2), namespace (B4 Q5'in açıklaması), RPU (ilk kullanımı A6'da kısa tanım). Kart 1'in Aurora'dan gelen metinlerinde "column" sayfanın kelimesi "kolon"a çevrildi (puan ve satırlar aynı); OpenSearch gerekçelerinde de. |
