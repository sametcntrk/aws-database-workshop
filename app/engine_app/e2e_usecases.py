"""Use cases of the E2E tutorials: the single source of the M2 cards and of the M7 scorecard simulations.

One use case = a story, five requirements (R1-R5), the chosen service plus its two closest alternatives, a score out of 10
for every candidate on every requirement (with the reason for each point that was taken off), a long head-to-head text
for each alternative, and a verdict. The cards in the page and the simulations in M7 are both rendered from this data,
so a score can never differ between the card and the simulation.

Text fields are (en, tr) tuples. While a page is in review, en may be None: T() then falls back to the Turkish text.

Scale (the same on every page):  10 = meets the requirement directly, with no extra work, with room to spare.
8-9 = meets it; a small extra task or a small cost.  5-7 = meets it, but with clear extra work in the application,
sizing, or a limit.  2-4 = partly: a part of the requirement is not met, or it is met at a high price.  0-1 = not met.
A candidate with 0 or 1 on a "must" requirement is disqualified, but stays in the table.
"""

# Short names of the services (SVC in e2e_sims) and the category word that the cards show before the service name.
CATEGORY = {"ddb": ("key-value", "key-value"), "aur": ("relational", "ilişkisel"), "ec": ("in-memory key-value", "bellek içi key-value"),
            "doc": ("document", "document"), "ks": ("wide-column", "wide-column"), "ix": ("time series", "time series"),
            "rs": ("data warehouse", "data warehouse"), "os": ("search engine", "search engine")}
LINK = {"aur": "aurora", "ec": "elasticache", "doc": "documentdb", "ks": "keyspaces", "ix": "influxdb", "rs": "redshift", "os": "opensearch", "ddb": "dynamodb"}

R_AXES = [("R1 Access pattern", "R1 Access pattern"), ("R2 Scale and traffic shape", "R2 Ölçek ve trafik şekli"),
          ("R3 Durability", "R3 Dayanıklılık"), ("R4 Operations and team", "R4 Operasyon ve ekip"), ("R5 Cost model", "R5 Maliyet modeli")]


def _t(tr, en=None):
    return (en, tr)


def req(must, want, why, en_want=None, en_why=None):
    return {"must": must, "want": (en_want, want), "why": (en_why, why)}


def sc(points, reason, en=None):
    return (points, (en, reason))


def usecase(uid, no, title, key, story, reqs, cands, scores, h2h, verdict, sim=None, kind=None):
    """kind: "race" (close race), "win" (clear win), "lose" (clear loss) or None (card only)."""
    assert len(reqs) == 5 and all(len(scores[c]) == 5 for c in cands) and cands[0] in CATEGORY   # the chosen service of the page comes first
    return {"id": uid, "no": no, "sim": sim, "kind": kind, "title": title, "key": key, "story": story,
            "reqs": reqs, "cands": cands, "scores": scores, "h2h": h2h, "verdict": verdict}


DDB_USECASES = [
    # ------------------------------------------------------------------ 1. shopping cart
    usecase("cart", 1, sim="race_cart", kind="race",
        title=_t("Alışveriş sepetleri (Lale Market)"),
        key=_t("Key: sepet, sonra ürün. Value: miktar, fiyat, süre sonu."),
        story=_t("Lale Market'in ürün sayfasında \"Sepete ekle\" düğmesi var. Düğme, tarayıcının cookie'sindeki ziyaretçi id'siyle sepete bir satır ekler ya da var olan satırın miktarını artırır. "
                 "Sepet sayfası bütün satırları fiyat ve miktarla gösterir. Checkout sepeti son hâliyle okur, siparişi stok ve müşteri kayıtlarıyla birlikte Aurora'ya yazar ve sonra sepeti boşaltır. "
                 "Mağazanın kuralı: bir üründen bir sepette en fazla 5 adet. Normal bir günde saniyede 250 sepet yazması olur. Kampanya akşamlarında, saat 20:00'de, trafik on dakika içinde saniyede 5.000 yazmaya çıkar ve üç saat öyle kalır. "
                 "Ziyaretçilerin yüzde 70'i sepeti bırakıp gider; bir gün sonra o sepetlerin hiçbir değeri yoktur. Ekipte üç geliştirici var, database yöneticisi yok."),
        reqs=[
            req(True, "Her istek ziyaretçi id'sini bilir. İki soru vardır: \"bu sepetin bütün satırları, ürün sırasıyla\" ve \"bu sepetteki bu ürüne 2 adet ekle, ama toplam 5'i geçmesin\". "
                      "İkinci soru bir kuraldır ve iki tarayıcı sekmesi aynı anda eklese bile korunmalıdır. Sepetler birbirinden bağımsızdır: hiçbir soru iki sepeti birden okumaz.",
                      "Sepet sayfası her açılışta bütün satırları ister; satır satır okumak sayfayı yavaşlatır. 5 sınırı korunmazsa bir müşteri kampanya ürününden 50 adet alabilir ve stok planı bozulur. "
                      "Kural uygulama tarafında \"önce oku, sonra yaz\" ile korunursa iki sekme arasında yarış olur ve sınır aşılır."),
            req(True, "Normal günde saniyede 250 yazma ve 1.000 okuma. Kampanya akşamı on dakika içinde saniyede 5.000 yazma ve 20.000 okuma; üç saat sürer ve sonra geri iner. "
                      "Tepe anında da her istek 20 ms'nin altında dönmeli. Kampanyadan önce kimse database'i elle büyütmek zorunda kalmamalı.",
                      "Yılın en çok satış yapılan üç saati bunlar. Sepet 20 ms'den yavaşsa ziyaretçi düğmeye ikinci kez basar ya da vazgeçer. Elle büyütme unutulursa ya da geç kalınırsa kampanya tam ortasında çöker."),
            req(False, "Kaybolan bir sepet kabul edilebilir ama istenmez: müşteri ürünleri yeniden ekler ve kızar. Para kaybı yoktur, çünkü sipariş Aurora'da kalıcıdır. "
                       "Yine de bir Availability Zone arızası sepetlerin tamamını kaybetmemeli.",
                       "Sepet bir ön hazırlıktır, resmi kayıt değildir. Bu yüzden dayanıklılık burada bir tercih, ama kampanya gecesi bir AZ arızasında 50.000 sepetin kaybı büyük bir satış kaybıdır."),
            req(False, "Üç geliştirici, database yöneticisi yok. Instance boyutlandırmak, yama geçmek, kampanya öncesi kapasite planı yapmak istenmiyor. Ekip AWS SDK'yı biliyor.",
                       "Küçük bir ekipte operasyon işi doğrudan ürün geliştirmeden çalınan zamandır. Kampanya öncesi kapasite planı her seferinde bir risk toplantısıdır."),
            req(False, "Trafik dalgalı: ayın 27 günü düşük, 3 akşamı çok yüksek. Boş zamanda neredeyse sıfır, dolu zamanda kullanım kadar ödemek istenir. Sepet verisi küçüktür (sepet başına 1 KB'tan az).",
                       "Tepe için boyutlandırılmış ve ay boyu çalışan bir sunucu, ayın yüzde 95'inde boş durur ve ödenir. Küçük veri, GB başına fiyatı önemsiz, istek başına fiyatı belirleyici yapar."),
        ],
        cands=["ddb", "aur", "ec"],
        scores={
            "ddb": [sc(8, "Partition key sepet, sort key ürün (Ö3): sepetin tamamı tek bir Query'dir. \"En fazla 5\" kuralı UpdateItem'a eklenen bir koşulla tek yazmada korunur (Ö5); iki sekme yarışsa bile ikincisi reddedilir. "
                          "2 puan kırıldı: checkout iki adımdır (sepeti oku, siparişi Aurora'ya yaz, sepeti sil) ve bu iki adım tek bir transaction değildir; bir arızada eski bir sepet kalabilir ve uygulama bunu temizlemelidir."),
                    sc(10, "Yazmalar ziyaretçi id'sine göre partition'lara dağılır (Ö2). On-demand mod trafiği takip eder: saniyede 250'den 5.000'e geçiş için hiçbir ayar yapılmaz. Key ile okuma ve yazma tepe anında da tek haneli milisaniyedir. Puan kırılmadı."),
                    sc(8, "Her yazma DynamoDB onaylamadan önce birkaç Availability Zone'da saklanır; bir AZ arızası sepet kaybetmez. 2 puan kırıldı: sepet eventually consistent okunursa bir saniye önceki ekleme görünmeyebilir; checkout'ta strongly consistent okuma gerekir ve bu iki kat okuma birimi tutar."),
                    sc(10, "Serverless: instance yok, yama yok, kapasite planı yok. Ekip zaten kullandığı AWS SDK ile çalışır. Puan kırılmadı."),
                    sc(9, "On-demand modda istek başına ve saklanan GB başına ödenir; boş günlerde maliyet sıfıra yakındır. 1 puan kırıldı: kampanya akşamı strongly consistent okumalar ve koşullu yazmalar normal isteklerden daha fazla birim tüketir; tepe maliyeti hesaplanmalıdır.")],
            "aur": [sc(10, "Sepet, satır ve stok aynı database'te olduğu için \"5 sınırı\" bir CHECK ya da UPDATE … WHERE qty + 2 <= 5 ile, checkout ise sepet + stok + sipariş tek transaction'da korunur. Bütün sorular SQL'dir. Puan kırılmadı; bu gereksinimde Aurora en güçlü adaydır."),
                    sc(8, "Saniyede 5.000 küçük yazma tek bir güçlü writer instance'ının erişimindedir ve Aurora Serverless v2 kapasiteyi (ACU) saniyeler içinde artırır. 2 puan kırıldı: yazmalar tek writer'dan geçer, üst sınır bellidir; on dakikalık sıçrama için minimum ACU'yu yüksek tutmak ya da ölçeklenmeyi önceden test etmek gerekir."),
                    sc(10, "Üç AZ'de altı kopya, sürekli yedek. Puan kırılmadı."),
                    sc(7, "Yönetilen servis: yedek, yama ve failover AWS'te. 3 puan kırıldı: schema, index ve ACU aralığı yine ekibin kararıdır; bir database yöneticisi olmayan üç kişilik ekip için kampanya öncesi kapasite ve bağlantı havuzu (connection pool) ayarı ek iştir."),
                    sc(7, "Serverless v2 ACU-saat olarak ödenir. 3 puan kırıldı: ayın 27 boş gününde de minimum ACU ödenir; sepet gibi küçük ve dalgalı bir iş yükünde istek başına ödemeye göre daha pahalıdır. Sipariş için zaten var olan bir Aurora kullanılıyorsa bu ek maliyet küçülür.")],
            "ec": [sc(6, "Sepet bir hash olarak tutulur: HGETALL sepetin tamamını, HINCRBY bir ürünün miktarını atomik artırır (Ö5'in bellek içi karşılığı). 4 puan kırıldı: \"5'i geçmesin\" koşulu HINCRBY'de yoktur; ya bir Lua script'i ya da WATCH/MULTI ile iki adımlı bir işlem gerekir ve bu kuralı uygulama kodu taşır."),
                   sc(10, "Bellekten mikrosaniyelerde cevap ve Serverless kendi kendine ölçeklenir. Puan kırılmadı."),
                   sc(4, "ElastiCache Serverless veriyi birkaç AZ'de replica olarak tutar, ama her yazmayı diske yazan dayanıklı bir log yoktur; bir arıza son saniyelerin sepetlerini kaybedebilir. 6 puan kırıldı: AZ arızasında sepet kaybı bu iş yükünde istenmeyen ama kabul edilen bir sonuçtur."),
                   sc(9, "Serverless, instance yok. 1 puan kırıldı: Lua script'i ekibin bakımına girer."),
                   sc(7, "Saklanan veri ve istek (ECPU) başına ödenir. 3 puan kırıldı: veri bellekte durduğu için GB başına fiyat diskten çok daha yüksektir; sepet verisi küçük olsa da minimum ücret boş günlerde de ödenir.")],
        },
        h2h={
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinim R1'in kural kısmı ve R2/R5. Aurora'nın gücü checkout'ta görünür: sepet, stok ve sipariş aynı transaction'da yazılır; DynamoDB'de bu iki adımdır ve bir arızada eski sepet kalabilir. "
                      "DynamoDB'nin gücü ise kampanya akşamında görünür: 250'den 5.000 yazmaya geçişte kimse bir şey yapmaz ve boş günlerde ödeme sıfıra yakındır; Aurora'da writer'ın üst sınırı ve minimum ACU vardır. "
                      "Bu iş yükünde key-value seçilir, çünkü sepet bir ön hazırlıktır, resmi kayıt değildir; sipariş zaten Aurora'da kalıcıdır ve sepetin iki adımlı checkout'u kabul edilebilir bir bedeldir. "
                      "Hangi koşul değişseydi Aurora seçilirdi: sepet ile stok aynı anda kilitlenmek zorunda olsaydı (örneğin sepete eklenen ürün stoktan düşülüyorsa) ya da kampanya trafiği tek writer'ın rahat erişiminde kalıp trafik düz olsaydı. Mağaza zaten bir Aurora işletiyorsa ve ek maliyet küçükse Aurora da savunulabilir bir karardır."),
            "ec": _t("Bellek içi key-value (ElastiCache) ile kafa kafaya. Ayrıştığı gereksinim R3 dayanıklılık ve R1'in kural kısmı. ElastiCache'in gücü hız: mikrosaniyeler ve tam anında süre sonu. "
                      "Ama sepet için hız fazlasıyla yeterlidir; 20 ms sınırı DynamoDB'nin tek haneli milisaniyesiyle rahat karşılanır. Fark dayanıklılıkta: ElastiCache Serverless'ta dayanıklı bir yazma log'u yoktur, bir arıza kampanya gecesinin son sepetlerini kaybedebilir. "
                      "\"5 sınırı\" da ElastiCache'te bir Lua script'i ister; DynamoDB'de tek bir koşuldur. Bu yüzden iki key-value store arasında kalıcı olanı seçilir: aynı kategori, aynı hız sınıfı, ama kayıp riski yok. "
                      "Hangi koşul değişseydi ElastiCache seçilirdi: sepet okuması her sayfa isteğinin önünde dursaydı ve bir milisaniyenin altı istenseydi ya da sepet başka bir sistemde zaten kalıcı olsaydı ve buradaki kopya sadece bir cache olsaydı."),
        },
        verdict=_t("Karar: DynamoDB 45, Aurora 42, ElastiCache 36. Üç aday da iş yükünü taşır; fark gereksinimlerin ağırlığındadır. Sepet resmi kayıt olmadığı ve trafik dalgalı olduğu için R2 ve R5 R1'in kural kısmından daha ağır basar ve bu DynamoDB'yi öne geçirir. "
                   "Yine de key-value seçersek artımız: kampanya gecesi kimse database'e dokunmaz, sepet kuralı tek istekte korunur, terk edilen sepetler kendiliğinden gider, boş günlerde neredeyse sıfır maliyet. "
                   "Potansiyel eksimiz: checkout iki adımdır ve bir arızada eski bir sepet kalabilir; uygulama bunu temizlemeli ve checkout'ta strongly consistent okuma kullanmalıdır. Bir koşul değişseydi: sepet ve stok tek transaction'da kilitlenmek zorunda olsaydı Aurora kazanırdı.")),

    # ------------------------------------------------------------------ 2. user profiles
    usecase("profile", 2, sim="race_profile", kind="race",
        title=_t("Kullanıcı profilleri ve tercihleri"),
        key=_t("Key: kullanıcı id'si. Value: ad, dil, adresler, bildirim tercihleri."),
        story=_t("Bir müzik uygulamasının beş milyon kullanıcısı var. Her ekran açılışında uygulama kullanıcının adını, dilini, abonelik durumunu ve bildirim tercihlerini okur; bu okuma her istekte olur. "
                 "Profil ayda bir değişir: adres eklenir, tercih kapatılır. Pazarlama ekibi her çeyrek profile yeni bir alan ekler (\"podcast önerisi ister mi\", \"doğum günü\") ve bu alan sadece yeni kullanıcılarda dolu başlar. "
                 "Saniyede 30.000 profil okuması, 100 yazma. Sabah 9'da ve akşam 21'de tepe, gece düşük. Her okuma 10 ms'nin altında olmalı, çünkü ekran profile göre çizilir. Ekip beş geliştirici, AWS SDK biliyor, sunucu istemiyor."),
        reqs=[
            req(True, "Tek soru: \"bu kullanıcı id'sinin profili\". Uygulama id'yi login'den bilir. Profil tek bir nesnedir: içinde adres listesi ve tercih haritası gibi iç içe alanlar vardır. Bir tercihi değiştirmek profilin tamamını yeniden yazmamalı. "
                      "Profiller birbirinden bağımsızdır: hiçbir soru iki profili birden okumaz.",
                      "Her ekran bu okumayla başlar; yavaşsa her ekran yavaştır. Bir tercih için profilin tamamını yeniden yazmak, aynı anda başka bir cihazdan yapılan değişikliği ezebilir."),
            req(True, "Saniyede 30.000 okuma ve 100 yazma, sabah ve akşam tepe. Her okuma 10 ms'nin altında. Kullanıcı sayısı yılda iki katına çıkıyor; büyüme için yeniden tasarım istenmiyor.",
                      "Okuma hacmi yazmanın 300 katıdır; ölçek okuma tarafındadır. Yılda iki kat büyüme, instance boyutlandıran bir sistemde her yıl bir büyütme projesi demektir."),
            req(False, "Profil kalıcı veridir. Kaybolursa kullanıcı adresini ve tercihlerini yeniden girer; güven kaybı olur, para kaybı olmaz. Bir AZ arızasında kayıp olmamalı.",
                       "Kullanıcı profilinin kaybı destek talebi ve güven kaybıdır; büyük bir uygulamada bir AZ arızası yüz binlerce kullanıcıyı etkiler."),
            req(False, "Çeyrekte bir yeni alan, migration ve kesinti olmadan eklenebilmeli. Ekip sunucu, yama ve index bakımı istemiyor; AWS SDK biliyor, MongoDB API'sini ve SQL'i az biliyor.",
                       "Her çeyrek bir ALTER TABLE ya da bir migration penceresi, pazarlama ekibinin takvimini database ekibine bağlar. Ekip bilmediği bir API'ı öğrenirken hata yapar."),
            req(False, "Okuma ağırlıklı ve düzenli; istek başına ya da kapasite başına ikisi de uyar. Profil küçüktür (4 KB'tan az). Toplam maliyet büyümeyle doğrusal artmalı, sıçramamalı.",
                       "30.000 okuma günün büyük bölümünde sürer; düz trafikte önceden alınan kapasite istek başına ödemeden ucuz olabilir. Büyümede bir instance sınıfı atlamak maliyeti bir gecede iki katına çıkarır."),
        ],
        cands=["ddb", "doc", "aur"],
        scores={
            "ddb": [sc(9, "Simple primary key = kullanıcı id'si; GetItem tek okumadır (Ö1). Tek bir tercih UpdateItem ile bir doküman yolu üzerinden (SET prefs.podcast = :v) değiştirilir, profilin tamamı yeniden yazılmaz. 1 puan kırıldı: adres listesinde \"ikinci adresi değiştir\" gibi liste içi güncellemeler index numarasıyla yapılır ve uygulama bu numarayı bilmelidir."),
                    sc(10, "Okumalar partition'lara dağılır (Ö2); 30.000 okuma on-demand ya da auto scaling ile kendiliğinden karşılanır, tek haneli milisaniye. Yılda iki kat büyüme için hiçbir şey değişmez. Puan kırılmadı."),
                    sc(10, "Her yazma birkaç AZ'de saklanır; point-in-time recovery açılabilir. Puan kırılmadı."),
                    sc(9, "Yeni alan sadece yeni value'lara yazılır (Ö4), migration yoktur; serverless, ekip bildiği SDK'yı kullanır. 1 puan kırıldı: value'nun 400 KB sınırı profil büyürse (örneğin dinleme geçmişi profile eklenirse) tasarımı zorlar; geçmiş ayrı bir table'a alınmalıdır."),
                    sc(9, "Düz trafikte provisioned + auto scaling en ucuz seçenektir; dalgalı başlangıçta on-demand. Maliyet kullanıcı sayısıyla doğrusal artar. 1 puan kırıldı: 4 KB'tan büyük profiller iki okuma birimi tüketir; profil boyutu takip edilmelidir.")],
            "doc": [sc(10, "Profil doğal bir document'tır: find by _id tek okumadır, updateOne ile iç içe bir alan ya da listedeki bir adres ($set, arrayFilters) profilin tamamını yazmadan değiştirilir. Liste içi güncelleme DynamoDB'den daha doğaldır. Puan kırılmadı."),
                    sc(8, "Okumalar en fazla 15 replica'ya dağılır ve 30.000 okuma karşılanır. 2 puan kırıldı: replica sayısını ve instance sınıfını ekip seçer; yılda iki kat büyüme bir büyütme adımıdır ve bütün yazmalar tek primary'den geçer."),
                    sc(10, "Üç AZ'de altı kopya, sürekli yedek. Puan kırılmadı."),
                    sc(7, "Şema serbesttir, yeni alan migration istemez; yedek ve yama yönetilir. 3 puan kırıldı: instance boyutlandırma ve replica yönetimi ekibin işidir ve MongoDB API'si bu ekip için yenidir."),
                    sc(7, "Instance saat başına ve I/O başına ödenir. 3 puan kırıldı: gece düşük trafikte de instance'lar çalışır; büyüme bir instance sınıfı atlatınca maliyet sıçrar.")],
            "aur": [sc(9, "Primary key ile okuma tek bir index aramasıdır; profil JSONB bir kolonda tutulursa iç içe alan jsonb_set ile değiştirilir. 1 puan kırıldı: JSONB güncellemesi satırın tamamını yeniden yazar (MVCC), tek alan için de tam satır maliyeti ödenir."),
                    sc(7, "Reader instance'lar 30.000 okumayı taşır. 3 puan kırıldı: reader sayısı ve sınıfı ekip tarafından seçilir; büyüme bir kapasite projesidir."),
                    sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                    sc(7, "Yönetilen servis. 3 puan kırıldı: JSONB dışında bir alan eklemek ALTER TABLE'dır; ekip SQL'i az biliyor; connection pool ve reader yönlendirmesi uygulama tarafında ayarlanır."),
                    sc(7, "ACU-saat ya da instance-saat. 3 puan kırıldı: düşük trafikte de minimum kapasite ödenir.")],
        },
        h2h={
            "doc": _t("Document (DocumentDB) ile kafa kafaya. Bu, okuyucunun en çok \"neden o değil?\" dediği karşılaştırmadır, çünkü profil tam bir document'tır ve iki store da şemasızdır. Ayrıştığı gereksinimler R2 ve R4. "
                      "DocumentDB'nin gücü R1'de görünür: iç içe alanları, listeleri ve listedeki tek bir elemanı güncellemek ($set, $push, arrayFilters) ve profilin içine göre sorgu (\"dili Türkçe olan kullanıcılar\") doğrudan desteklenir; DynamoDB'de liste içi güncelleme index numarası ister ve value içi sorgu bir GSI ister (Ö7). "
                      "DynamoDB'nin gücü R2 ve R4'te görünür: 30.000 okuma ve yılda iki kat büyüme için hiçbir boyutlandırma yapılmaz, bütün yazmalar tek bir primary instance'tan geçmez ve ekip bildiği SDK ile çalışır; DocumentDB'de replica sayısı, instance sınıfı ve MongoDB API'si ekibin yeni işleridir. "
                      "Bu iş yükünde key-value seçilir, çünkü tek access pattern \"id ile profil\"dir, profilin içine göre sorgu yoktur ve ölçek okuma tarafında kendiliğinden büyümelidir. Document database'in esnek sorgu gücü burada kullanılmayacak bir güçtür ve bedeli operasyondur. "
                      "Hangi koşul değişseydi DocumentDB seçilirdi: profilin içine göre sorular sık ve çeşitli olsaydı (\"İstanbul'da oturan ve podcast isteyen kullanıcılar\"), profilde sık değişen uzun listeler olsaydı ya da ekip zaten MongoDB biliyor ve bir DocumentDB cluster'ı işletiyor olsaydı."),
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinimler R2, R4 ve R5. Aurora'nın gücü, profil başka ilişkisel verilerle (abonelik faturaları, ödeme yöntemleri) birlikte sorgulanacaksa görünür: bir JOIN ile \"abonelik süresi dolan ve bildirim isteyen kullanıcılar\" tek sorgudur. "
                      "DynamoDB'de bu soru ya iki okuma ya da analitik kopyaya taşınan bir iştir. Ama bu iş yükünde profil tek başına okunur ve yazılır; JOIN kullanılmaz. Ölçek okuma tarafındadır ve reader instance'ları boyutlandırmak, yeni alan için ALTER TABLE yapmak ekibin istemediği işlerdir. "
                      "Bu yüzden key-value seçilir. Hangi koşul değişseydi Aurora seçilirdi: profil abonelik ve ödeme verisiyle aynı transaction'da güncellenseydi, raporlar profil alanlarına göre sık sorulsaydı ya da uygulama zaten Aurora üzerinde kurulu olup profil sadece bir table daha olsaydı."),
        },
        verdict=_t("Karar: DynamoDB 47, DocumentDB 42, Aurora 40. Üç aday da R1 ve R3'ü tam karşılar; yarışı R2 ve R4 belirler: boyutlandırmasız okuma ölçeği ve ekibin bildiği SDK. "
                   "Yine de key-value seçersek artımız: büyüme için proje yok, yeni alan için migration yok, 30.000 okuma kendiliğinden karşılanır, maliyet kullanıcı sayısıyla doğrusal. "
                   "Potansiyel eksimiz: profilin içine göre bir soru gelirse (\"dili Türkçe olanlar\") bir GSI kurulur ya da soru analitik kopyaya gider; liste içi güncellemeler index numarası ister; profil 400 KB'a yaklaşırsa geçmiş gibi büyüyen alanlar ayrı table'a alınır. Bir koşul değişseydi: profil içine göre sorular sık ve çeşitli olsaydı DocumentDB kazanırdı.")),

    # ------------------------------------------------------------------ 3. sessions
    usecase("session", 3, sim="race_session", kind="race",
        title=_t("Oturumlar ve login token'ları"),
        key=_t("Key: session id. Value: kullanıcı id'si, rol, son sayfa, süre sonu."),
        story=_t("Bir web mağazasının her HTTP isteği cookie'deki session id ile oturumu okur: kullanıcı kim, rolü ne, sepeti var mı. Oturum 30 dakika hareketsizlikten sonra düşer ve her sayfa görüntülemede süresi yenilenir. "
                 "Saniyede 40.000 sayfa isteği, dolayısıyla saniyede 40.000 oturum okuması ve 40.000 süre yenilemesi. Oturum okuması her isteğin önünde durur: 1 ms gecikme, her sayfaya 1 ms ekler. "
                 "Kaybolan bir oturum sadece yeni bir login demektir; sepet DynamoDB'de, sipariş Aurora'da zaten kalıcıdır. Ekip sunucu istemiyor."),
        reqs=[
            req(True, "Tek soru: \"bu session id'nin oturumu\". Her istekte bir okuma ve bir süre yenileme (yazma). Oturum küçük bir nesnedir (1 KB'tan az). Süresi dolan oturum okunmamalı: 30 dakika 1 saniye sonra istek yeni login'e gitmeli.",
                      "Oturum okuması her isteğin ilk adımıdır. Süresi dolmuş bir oturumun kabul edilmesi bir güvenlik açığıdır: paylaşılan bilgisayarda bir sonraki kişi önceki hesapta kalır."),
            req(True, "Saniyede 40.000 okuma ve 40.000 yazma, gün içinde dalgalı. Her okuma 1 ms'nin altında olmalı, çünkü her sayfa isteğine eklenir; 5 ms bile günde milyonlarca sayfada hissedilir.",
                      "Bu gecikme her sayfaya, her kullanıcıya eklenen sabit bir vergidir. 1 ms ile 5 ms arasındaki fark, ürün sayfasının toplam süresinin yüzde 5'idir."),
            req(False, "Düşük: kaybolan oturum yeni bir login'dir. Bir AZ arızasında bütün kullanıcıların yeniden login olması kabul edilir ama istenmez.",
                       "Oturum türetilmiş bir veridir; kaynağı kullanıcı hesabıdır. Kaybı can sıkıcıdır, zararlı değildir. Bu yüzden dayanıklılık burada hız için feda edilebilir."),
            req(False, "Ekip sunucu, node ve yama istemiyor; serverless tercih. Süre yenileme uygulama kodunda tek satır olmalı.",
                       "Oturum altyapısı ürün değildir; ekibin zamanını almamalıdır. Yenileme karmaşıksa geliştiriciler onu atlar ve oturumlar erken düşer."),
            req(False, "Trafik gün içinde dalgalı; istek ya da kullanım başına ödeme. Oturum verisi küçük ve kısa ömürlüdür; toplam veri hiçbir zaman birkaç GB'ı geçmez.",
                       "Kısa ömürlü küçük veri için GB fiyatı önemsiz, istek fiyatı belirleyicidir; saniyede 80.000 istek aylık faturada görünür."),
        ],
        cands=["ddb", "ec", "ks"],
        scores={
            "ddb": [sc(8, "GetItem ve UpdateItem session id ile tek istektir (Ö1); TTL alanı süresi dolan oturumu siler (Ö6). 2 puan kırıldı: TTL silmesi tam anında değildir, genellikle birkaç gün içinde olur; uygulama her okumada expires_at'i şimdiki zamanla kendisi karşılaştırmalıdır, yoksa süresi dolmuş oturum kabul edilir."),
                    sc(6, "40.000 + 40.000 istek on-demand modda kendiliğinden karşılanır (Ö2). 4 puan kırıldı: gecikme tek haneli milisaniyedir, 1 ms'nin altı değildir; bu gereksinimin katı sınırı karşılanmaz. DAX eklenirse okuma mikrosaniyeye iner ama yazma (yenileme) yine milisaniyedir ve DAX ek bir bileşendir."),
                    sc(10, "Her yazma birkaç AZ'de saklanır; oturum bir arızadan sağ çıkar. Puan kırılmadı; gereksinim düşük olsa da tam karşılanır."),
                    sc(10, "Serverless; yenileme tek bir UpdateItem. Puan kırılmadı."),
                    sc(8, "İstek başına ödeme. 2 puan kırıldı: saniyede 40.000 yazma (yenileme) 40.000 yazma birimidir ve yazma okumadan beş kat pahalıdır; yenilemeyi her istekte değil, kalan sürenin yarısı geçince yapmak maliyeti düşürür ama bu uygulama tarafında bir kuraldır.")],
            "ec": [sc(10, "GET ve SET ya da oturum başına bir hash; EXPIRE her istekte süreyi yeniler ve key tam süre sonunda yok olur: süresi dolmuş oturum hiçbir zaman okunmaz. Puan kırılmadı."),
                   sc(10, "Bellekten mikrosaniyelerde, 1 ms'nin çok altında; Serverless kendi kendine ölçeklenir. Puan kırılmadı."),
                   sc(5, "Serverless replica'ları birkaç AZ'de tutar, ama dayanıklı bir yazma log'u yoktur; bir arıza son oturumları kaybedebilir ve kullanıcılar yeniden login olur. 5 puan kırıldı: kayıp mümkündür, bu iş yükünde kabul edilir."),
                   sc(10, "Serverless; EXPIRE tek komut. Puan kırılmadı."),
                   sc(8, "Veri (GB-saat) ve istek (ECPU) başına ödenir. 2 puan kırıldı: bellek GB başına diskten pahalıdır ve minimum bir ücret vardır; oturum verisi küçük olduğu için fark küçüktür.")],
            "ks": [sc(9, "SELECT ve UPDATE partition key ile tek istektir; row TTL'i oturumu sona erdirir. 1 puan kırıldı: her yenileme row'u yeni bir TTL ile yeniden yazar ve süresi dolan row silinene kadar tombstone olarak kalır."),
                   sc(7, "On-demand kapasite yükü takip eder, tek haneli milisaniye. 3 puan kırıldı: 1 ms'nin altı karşılanmaz."),
                   sc(10, "Üç AZ'de üç kopya. Puan kırılmadı."),
                   sc(6, "Serverless. 4 puan kırıldı: ekip CQL'i, Cassandra driver'ını ve bağlantı ayarlarını öğrenir; oturum gibi basit bir iş için yeni bir API öğrenmek orantısızdır."),
                   sc(9, "Okuma ve yazma isteği başına ödeme. 1 puan kırıldı: yenileme yazmaları saniyede 40.000 yazma birimidir.")],
        },
        h2h={
            "ec": _t("Bellek içi key-value (ElastiCache) ile kafa kafaya. Bu, aynı kategorinin iki üyesi arasındaki yarıştır ve A10 matrisinin Ö6 satırı ile hız sınıfı farkı burada belirleyicidir. Ayrıştığı gereksinimler R2 ve R3. "
                      "ElastiCache'in gücü: mikrosaniye okuma, çünkü veri bellektedir; ve tam anında süre sonu (EXPIRE), yani süresi dolmuş oturum asla okunmaz. DynamoDB tek haneli milisaniyedir ve TTL silmesi birkaç gün sürebilir; süre kontrolü uygulamaya kalır. "
                      "DynamoDB'nin gücü: dayanıklılık; her yazma birkaç AZ'de saklanır ve bir arıza kimseyi login ekranına geri göndermez. Bu iş yükünde R2'deki \"1 ms'nin altı\" sınırı katıdır ve R3 düşüktür; bu iki koşul birlikte ElastiCache'i öne geçirir. "
                      "Hangi koşul değişseydi DynamoDB seçilirdi: oturumun içinde kaybı kabul edilmeyen bir şey olsaydı (örneğin yarım kalmış bir ödeme adımı), gecikme sınırı 1 ms değil 10 ms olsaydı ya da oturumlar birkaç bölgeden okunup global table gerektirseydi. "
                      "Best practice: oturum gibi türetilmiş, küçük, kısa ömürlü ve gecikmeye duyarlı veri bellek içi store'a; oturumun içindeki kalıcı parçalar (sepet, sipariş) kalıcı store'a."),
            "ks": _t("Wide-column (Keyspaces) ile kafa kafaya. Ayrıştığı gereksinimler R2, R4 ve R1'in süre sonu kısmı. Keyspaces de serverless'tır, key ile okur ve row TTL'i vardır; dayanıklılıkta DynamoDB ile eşittir. "
                      "Fark operasyon ve API'dadır: ekip CQL ve bir Cassandra driver'ı öğrenir, bağlantı havuzu ayarlar; DynamoDB'de bildiği SDK ile iki çağrı yazar. Ayrıca her yenileme Keyspaces'te row'u yeniden yazar ve süresi dolan row tombstone bırakır. "
                      "Bu iş yükünde Keyspaces'i seçmek için bir neden yoktur, çünkü Keyspaces'in gücü olan Cassandra uyumluluğu burada kullanılmaz. Hangi koşul değişseydi Keyspaces seçilirdi: ekip zaten Cassandra ve CQL kullanıyor olsaydı ya da oturumlar on-premise bir Cassandra'dan AWS'e taşınıyor ve kod değişmeden kalmalıydı."),
        },
        verdict=_t("Karar: ElastiCache 43, DynamoDB 42, Keyspaces 41. En yakın yarış budur ve kategori (key-value) kesin doğrudur; soru kategori içinde hangi store olduğudur. R2'nin \"1 ms'nin altı\" sınırı ve R3'ün düşük olması ElastiCache'i bir puan öne geçirir. "
                   "Yine de DynamoDB seçersek artımız: oturum bir arızadan sağ çıkar, kapasite ve bellek düşünülmez, ekip diğer table'larla aynı SDK'yı kullanır, global table ile çok bölgeli oturum mümkündür. "
                   "Potansiyel eksimiz: her sayfaya birkaç milisaniye eklenir; süre kontrolünü uygulama her okumada yapmalıdır; saniyede 40.000 yenileme yazma birimi olarak ödenir. Bir koşul değişseydi: kayıp kabul edilmeseydi ya da sınır 10 ms olsaydı DynamoDB kazanırdı.")),

    # ------------------------------------------------------------------ 4. game state
    usecase("game", 4,
        title=_t("Oyun durumu ve oyuncu envanteri"),
        key=_t("Key: oyuncu, sonra nesne türü ve nesne id'si. Value: nesnenin alanları."),
        story=_t("Küçük bir stüdyo bir mobil oyun çıkarıyor. Pazarlama kampanyası ilk gün bir milyon oyuncu getirecek; bir ay sonra günlük oyuncu 100.000'e inecek. Her oyuncunun envanteri 20 ile 500 nesne arasıdır ve nesnelerin alanları türüne göre farklıdır: bir kılıçta hasar ve dayanıklılık, bir iksirde süre ve etki. "
                 "Oyun her açılışta envanterin tamamını, savaş ekranında sadece silahları okur. Bir nesne kazanıldığında envantere eklenir; bir nesne satın alındığında kaybolmaması şarttır. Stüdyoda iki backend geliştirici var, operasyon ekibi yok; lansman gecesi kimse cluster büyütmek istemiyor."),
        reqs=[
            req(True, "Sorular: \"bu oyuncunun bütün envanteri\", \"bu oyuncunun sadece silahları\", \"bu nesneyi bu oyuncuya ekle\", \"bu nesnenin dayanıklılığını 3 azalt\". Oyuncu id'si her istekte bilinir. Oyuncular birbirinden bağımsızdır. Nesnelerin alanları türe göre farklıdır ve yeni nesne türleri her güncellemede gelir.",
                      "Envanter her oyun açılışında okunur; yavaşsa oyun yavaş açılır. Yeni nesne türü için migration gerekiyorsa her oyun güncellemesi bir database projesi olur."),
            req(True, "İlk gün saniyede 200.000 istek, bir ay sonra saniyede 20.000. Her istek dünyanın her yerinden 10 ms'nin altında. Lansman gecesi hiçbir elle müdahale olmamalı.",
                      "Lansman tek seferliktir ve geri alınamaz; o gece bir yavaşlama uygulama mağazası yorumlarına geçer. Bir ay sonra on kat düşük trafik için on kat düşük maliyet istenir."),
            req(False, "Yüksek: satın alınan nesne kaybolursa oyuncu para iadesi ister. Bir AZ arızasında kayıp olmamalı.",
                       "Envanter oyuncunun parasıyla aldığı şeydir; kaybı doğrudan gelir ve itibar kaybıdır."),
            req(False, "İki geliştirici, operasyon ekibi yok. Boyutlandırma, yama ve yedek istenmiyor. Yeni nesne türü için migration istenmiyor.",
                       "İki kişilik bir ekipte operasyon işi oyunun gelişimini durdurur."),
            req(False, "Trafik lansmandan sonra on kat düşer; maliyet de düşmeli. Envanter verisi küçük (oyuncu başına 100 KB'tan az).",
                       "Lansman için boyutlandırılmış bir cluster bir ay sonra yüzde 90 boş çalışır ve ödenir."),
        ],
        cands=["ddb", "doc", "ec"],
        scores={
            "ddb": [sc(10, "Partition key oyuncu, sort key TÜR#id (Ö3): envanterin tamamı tek Query, sadece silahlar begins_with(sk, 'WEAPON#') ile bir dilim. Her nesne kendi alanlarını taşır (Ö4). Dayanıklılık azaltma tek value'da atomik bir ADD'dir (Ö5). Puan kırılmadı."),
                    sc(10, "Yazma ve okuma oyuncu id'sine göre partition'lara dağılır (Ö2); on-demand mod lansman gecesini kendiliğinden karşılar ve bir ay sonra maliyet trafikle düşer. Global table ile birkaç bölgede 10 ms'nin altı mümkündür. Puan kırılmadı."),
                    sc(10, "Her yazma birkaç AZ'de saklanır, point-in-time recovery. Puan kırılmadı."),
                    sc(10, "Serverless; yeni nesne türü için hiçbir değişiklik yok. Puan kırılmadı."),
                    sc(9, "İstek başına ödeme; lansman sonrası maliyet on kat düşer. 1 puan kırıldı: 500 nesnelik bir envanterin tamamını okumak birkaç okuma birimi tutar; sık açılan oyunlarda envanter boyutu maliyeti belirler.")],
            "doc": [sc(9, "Oyuncu belgesi içinde nesne dizisi doğaldır; $push ile ekleme, arrayFilters ile tek nesnenin alanını değiştirme, projection ile sadece silahlar. 1 puan kırıldı: 500 nesnelik dizide tek bir nesneyi değiştirmek document'ın tamamını yeniden yazar."),
                    sc(6, "Okumalar replica'larla ölçeklenir. 4 puan kırıldı: bütün yazmalar tek primary instance'a gider; lansman gecesi için primary önceden büyük boyutlandırılır ve bir ay sonra küçültülür; her ikisi de elle yapılan işlerdir."),
                    sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                    sc(7, "Şema serbest, yedek ve yama yönetilir. 3 puan kırıldı: instance boyutlandırma ekibin işidir ve iki kişilik ekip için lansman gecesi bir risktir."),
                    sc(6, "Instance saat başına. 4 puan kırıldı: lansman için büyütülen instance'lar bir ay sonra elle küçültülmezse boşa ödenir.")],
            "ec": [sc(6, "Oyuncu başına bir hash: HGETALL envanter, HSET nesne. 4 puan kırıldı: \"sadece silahlar\" dilimi hash'te yoktur, uygulama filtreler ya da tür başına ayrı hash tutar; nesne alanlarının atomik azaltılması HINCRBY ile olur ama kural (0'ın altına inmesin) script ister."),
                   sc(10, "Bellekten mikrosaniye; Serverless ölçeklenir. Puan kırılmadı."),
                   sc(4, "Dayanıklı yazma log'u yoktur; bir arıza satın alınan nesneleri kaybedebilir. 6 puan kırıldı: bu iş yükünde kayıp para iadesi demektir."),
                   sc(9, "Serverless. 1 puan kırıldı: script bakımı."),
                   sc(7, "GB-saat ve ECPU. 3 puan kırıldı: bellek GB başına pahalıdır ve lansman gecesinin verisi bir ay boyunca bellekte kalır.")],
        },
        h2h={
            "doc": _t("Document (DocumentDB) ile kafa kafaya. Ayrıştığı gereksinimler R2, R4 ve R5. DocumentDB'nin gücü R1'de: oyuncu bir belge, envanter içinde bir dizi; dizi içinde tek bir nesneyi güncellemek ve projeksiyonla sadece silahları çekmek MongoDB API'sinde doğaldır. "
                      "DynamoDB aynı soruları sort key tasarımıyla cevaplar: her nesne ayrı bir value, silahlar bir önek dilimi; bu da aynı derecede doğrudan ama tasarım önceden yapılmalıdır. Fark lansman gecesinde görünür: DocumentDB'de bütün yazmalar tek primary'den geçer ve o primary'yi önceden büyütmek, bir ay sonra küçültmek iki kişilik ekibin işidir; DynamoDB'de hiçbir şey yapılmaz ve maliyet trafikle birlikte düşer. "
                      "Bu iş yükünde key-value seçilir, çünkü access pattern'ler önceden bellidir ve lansman eğrisi (bir gün tepe, sonra on kat düşüş) boyutlandırmasız bir store'u zorunlu kılar. "
                      "Hangi koşul değişseydi DocumentDB seçilirdi: trafik düz ve önceden bilinir olsaydı, envanter içinde serbest sorgular (\"hasarı 50'den büyük bütün silahlarım\") sık olsaydı ya da ekip MongoDB'yi zaten biliyor olsaydı."),
            "ec": _t("Bellek içi key-value (ElastiCache) ile kafa kafaya. Ayrıştığı gereksinim R3 dayanıklılık. ElastiCache hızda ve ölçekte DynamoDB'nin önündedir, ama envanter oyuncunun parasıyla aldığı nesnelerdir ve dayanıklı bir yazma log'u olmayan bir store'da bir arıza para iadesi demektir. "
                      "Bu yüzden iki key-value store arasında kalıcı olan seçilir. Hızda ve ölçekte ElastiCache'in üstünlüğü bu iş yükünde kullanılmaz: 10 ms sınırı DynamoDB'nin tek haneli milisaniyesiyle karşılanır ve lansman gecesinin 200.000 isteği iki store'da da kendiliğinden ölçeklenir. Fark yalnız dayanıklılıkta kalır ve o da burada zorunlu gereksinimdir. Hangi koşul değişseydi ElastiCache seçilirdi: envanter başka bir yerde kalıcı olsaydı ve buradaki kopya sadece hızlı okuma için bir cache olsaydı (bu durumda ikisi birlikte kullanılır: kalıcı kayıt DynamoDB'de, sıcak kopya ElastiCache'te) ya da liderlik tablosu gibi sıralama soruları (sorted set) ana iş olsaydı."),
        },
        verdict=_t("Karar: DynamoDB 49, DocumentDB 38, ElastiCache 36. Bu bir yakın yarış değildir: lansman eğrisi ve dayanıklılık birlikte DynamoDB'yi açık ara öne geçirir. "
                   "Yine de key-value seçersek artımız: lansman gecesi ve bir ay sonrası aynı table, kimse dokunmaz; envanter kalıcıdır; yeni nesne türü için migration yoktur; birkaç bölgede oyuncu için global table. "
                   "Potansiyel eksimiz: \"en güçlü 100 oyuncu\" gibi sıralama soruları key ile cevaplanmaz; bunun için bir GSI (Ö7) ya da bellek içi sorted set gerekir. Binlerce nesnelik tek bir envanter tek partition'da durur. Bir koşul değişseydi: trafik düz ve envanter içi serbest sorgular sık olsaydı DocumentDB yarışa girerdi.")),

    # ------------------------------------------------------------------ 5. IoT last state
    usecase("iot", 5, sim="win_iot", kind="win",
        title=_t("Her cihazın son durumu (IoT)"),
        key=_t("Key: cihaz id'si. Value: son okuma, zaman, pil, durum."),
        story=_t("Bir enerji şirketinin iki milyon akıllı sayacı var. Her sayaç 30 saniyede bir son değerini, pil seviyesini ve durumunu gönderir; mesajlar AWS IoT Core üzerinden bir Lambda fonksiyonuna gelir. "
                 "Bir operatör panelinde bir sayaca tıklandığında son durumu görünür. Geçmiş değerler ayrı bir time series sisteme gider; burada sadece son durum tutulur ve her mesaj öncekinin üzerine yazar. "
                 "Sıcaklık 80 dereceyi geçen ya da pili yüzde 5'in altına düşen sayaç için bir alarm açılmalıdır. Saniyede 65.000 mesaj, günün her saati, düz. Ekip IoT ve Lambda kullanıyor, sunucu istemiyor."),
        reqs=[
            req(True, "Sorular: \"bu cihazın son durumu\" ve \"bu cihazın son durumunu bu mesajla değiştir\". Cihaz id'si her mesajda ve her tıklamada bilinir. Cihazlar birbirinden bağımsızdır. Geçmiş sorulmaz; sadece son değer.",
                      "Panel tek cihazı gösterir; iki soru dışında hiçbir soru yoktur. Model bundan daha karmaşıksa karmaşıklık boşa ödenir."),
            req(True, "Saniyede 65.000 yazma, düz ve sürekli, günde 5,6 milyar mesaj. Okuma az: saniyede 200. Yazma 50 ms'nin altında onaylanmalı, yoksa Lambda kuyruğu büyür ve mesajlar gecikir.",
                      "Yazma hacmi bu iş yükünün tamamıdır. Yazma yavaşlarsa IoT kuyruğu dolar, mesajlar atılır ve panel eski değer gösterir."),
            req(False, "Orta: kaybolan son durum 30 saniye sonra yeniden gelir. Bir AZ arızasında bile 30 saniyeden eski bir durum gösterilmemeli.",
                       "Veri kendini 30 saniyede yeniler; dayanıklılık burada bir rahatlıktır, zorunluluk değildir."),
            req(False, "Ekip AWS IoT, Lambda ve SDK kullanıyor; sunucu, node ve CQL istemiyor. Alarm mantığı yazan koddan ayrı olmalı.",
                       "Alarm kuralı mesajı yazan Lambda'nın içine girerse her yeni kural o fonksiyonu değiştirir ve yazma yolunu yavaşlatır."),
            req(False, "Yazma sayısı sabit ve yüksek; yazma başına fiyat belirleyicidir. Trafik düz olduğu için kapasite önceden alınabilir ve bu on-demand'den ucuz olmalıdır. Veri küçük (cihaz başına 1 KB).",
                       "Günde 5,6 milyar yazma: yazma birimi fiyatındaki yüzde 10'luk fark ayda binlerce dolardır."),
        ],
        cands=["ddb", "ks", "ix"],
        scores={
            "ddb": [sc(10, "Simple primary key = cihaz id'si; her mesaj PutItem ile son durumu üzerine yazar, panel GetItem ile okur (Ö1). Bundan daha basit bir model yoktur. Puan kırılmadı."),
                    sc(10, "İki milyon farklı key yazmayı partition'lara eşit dağıtır (Ö2); 65.000 yazma tek haneli milisaniyede onaylanır. Puan kırılmadı."),
                    sc(9, "Her yazma birkaç AZ'de saklanır. 1 puan kırıldı: eventually consistent okuma bir saniye eski değer gösterebilir; panel strongly consistent okursa iki kat okuma birimi tutar, ama okuma azdır."),
                    sc(10, "Serverless, bildiği SDK. değişiklik akışı (Ö8; B5'te Streams) her değişikliği ayrı bir Lambda'ya verir; alarm kuralı yazan koddan ayrılır. Puan kırılmadı."),
                    sc(9, "Düz trafikte provisioned kapasite + reserved capacity on-demand'den belirgin ucuzdur. 1 puan kırıldı: 65.000 yazma birimi sürekli ödenir; 1 KB'ı geçen mesajlar iki birim tutar ve mesaj boyutu disiplinle tutulmalıdır.")],
            "ks": [sc(10, "INSERT partition key ile üzerine yazar (Cassandra'da insert = upsert), SELECT partition key ile okur. Puan kırılmadı."),
                   sc(9, "Yazmalar partition'lara dağılır; on-demand ya da provisioned kapasite. 1 puan kırıldı: LWT kullanılmadığı için hızlıdır, ama 65.000 yazma için provisioned kapasite önceden hesaplanmalı ve on-demand'de istek başına fiyat yüksektir."),
                   sc(10, "Üç AZ'de üç kopya. Puan kırılmadı."),
                   sc(5, "Serverless. 5 puan kırıldı: ekip CQL, Cassandra driver'ı ve bağlantı ayarlarını öğrenir; alarm için CDC stream'i vardır ama Lambda'ya bağlamak DynamoDB'nin akışından daha fazla kurulum ister."),
                   sc(8, "Yazma isteği başına ödeme, provisioned mod. 2 puan kırıldı: yazma birimi fiyatı DynamoDB ile benzer ama CDC ayrıca ücretlendirilir ve reserved capacity yoktur.")],
            "ix": [sc(6, "Cihaz bir tag, ölçümler alanlar; \"son değer\" sorgusu (last()) vardır. 4 puan kırıldı: time series database her mesajı bir nokta olarak saklar, üzerine yazmaz; \"son durum\" sorusu zaman serisinin son noktasını bulmaktır ve bu key ile doğrudan okuma kadar ucuz değildir."),
                   sc(9, "Yüksek yazma hızı için yapılmıştır; 65.000 nokta/saniye bir instance'ın erişimindedir. 1 puan kırıldı: instance sınıfı önceden seçilir."),
                   sc(9, "Multi-AZ seçeneği ile replica. 1 puan kırıldı: replica elle seçilir."),
                   sc(6, "Yönetilen instance. 4 puan kırıldı: instance boyutlandırma, disk ve retention ayarı ekibin işidir; alarm için ayrı bir task/alert motoru öğrenilir."),
                   sc(6, "Instance saat başına ve disk başına. 4 puan kırıldı: sadece son durumu tutmak için bir time series instance'ı çalıştırmak, bu verinin geçmişi başka yerde tutulduğu için gereksiz maliyettir.")],
        },
        h2h={
            "ks": _t("Wide-column (Keyspaces) ile kafa kafaya. Ayrıştığı gereksinimler R4 ve R5. Keyspaces veri modelinde ve ölçekte DynamoDB ile neredeyse aynıdır: key ile üzerine yazma, partition'lara dağılım, üç kopya. "
                      "Fark ekipte ve entegrasyonda: Keyspaces CQL ve bir Cassandra driver'ı ister, DynamoDB ekibin IoT ve Lambda ile zaten kullandığı SDK'dır; alarm için DynamoDB'nin değişiklik akışı (Ö8) doğrudan Lambda'ya bağlanır, Keyspaces CDC daha fazla kurulum ister. "
                      "Bu iş yükünde key-value (DynamoDB) seçilir, çünkü Keyspaces'in tek üstünlüğü olan Cassandra uyumluluğu burada bir ihtiyaç değildir. Hangi koşul değişseydi Keyspaces seçilirdi: şirketin mevcut sayaç sistemi Cassandra üzerinde çalışıyor ve AWS'e kod değişmeden taşınıyor olsaydı ya da ekip Cassandra'yı iyi bilip DynamoDB'yi hiç bilmeseydi."),
            "ix": _t("Time series (Timestream for InfluxDB) ile kafa kafaya. Ayrıştığı gereksinimler R1, R4 ve R5. Bu karşılaştırma bir sınırı gösterir: aynı cihaz verisi için \"son durum\" ve \"geçmiş\" iki farklı iş yüküdür. "
                      "Time series database her mesajı bir nokta olarak saklar ve gücü zaman aralıkları, pencereler ve toplamlardır: \"son bir saatin ortalaması\", \"dünkü tepe değer\". Burada sorulan tek soru \"son değer\"dir ve bu soru için her mesajı saklamak, son noktayı aramak ve bunun için bir instance işletmek gereksizdir. "
                      "Bu yüzden son durum için key-value, geçmiş için time series kullanılır; iki store birbirinin alternatifi değil tamamlayıcısıdır. Hangi koşul değişseydi time series seçilirdi: panel son değerin yanında grafik ve ortalama gösterseydi ve ayrı bir geçmiş sistemi olmasaydı; o zaman tek store olarak time series seçilir ve \"son değer\" sorgusu onun içinde cevaplanırdı."),
        },
        verdict=_t("Karar: DynamoDB 48, Keyspaces 42, InfluxDB 36. Net bir kazanma: iş yükü key-value modelinin tam tanımıdır (key ile üzerine yazma, bağımsız cihazlar, düz ve yüksek yazma) ve DynamoDB hiçbir zorunlu gereksinimde puan kaybetmez. "
                   "Yine de key-value seçersek artımız: en basit model, ekibin bildiği SDK, değişiklik akışıyla alarm yazan koddan ayrılır, reserved capacity ile düz trafik en ucuz hâliyle ödenir. "
                   "Potansiyel eksimiz: \"son bir saatin ortalaması\" gibi sorular bu table'da yoktur; geçmiş için time series database ayrıca gerekir. 65.000 yazma biriminin faturası mesaj boyutuna duyarlıdır. Bir koşul değişseydi: geçmiş ve son durum tek store'da istenseydi time series database tek aday olurdu.")),

    # ------------------------------------------------------------------ 6. idempotency keys
    usecase("idem", 6,
        title=_t("Ödemeler ve API'lar için idempotency key'leri"),
        key=_t("Key: request id. Value: sonuç, zaman, süre sonu."),
        story=_t("Bir ödeme API'ı kart çekimi yapar. İstemci bir ağ hatasından sonra isteği aynı request id ile tekrar gönderir. Sistem kartı bir kez çekmeli ve ikinci isteğe ilk isteğin sonucunu döndürmeli. "
                 "Günde 20 milyon istek, yüzde 2'si tekrar. İşaretin 24 saat tutulması yeterlidir. Ödeme kaydının kendisi ayrı bir ilişkisel database'tedir. Ödeme ekibi çoklu AZ şart koşuyor ve sunucu istemiyor."),
        reqs=[
            req(True, "\"Bu request id daha önce işlendi mi; işlenmediyse şimdi işaretle\" tek adımda ve atomik olmalı: aynı id ile iki istek aynı milisaniyede gelse bile sadece biri \"yeni\" cevabını almalı. İşlendiyse ilk sonuç döndürülmeli.",
                      "Kontrol ve işaret iki ayrı adımsa iki eşzamanlı tekrar ikisi de \"yeni\" görür ve kart iki kez çekilir. Bu tam olarak önlenmesi istenen hatadır."),
            req(True, "Saniyede 230 istek ortalama, tepe 3.000. Her kontrol 10 ms'nin altında, çünkü ödeme akışının ilk adımıdır.",
                      "Hacim düşüktür; burada ölçek değil, tepe anında bile hatasızlık ve gecikme önemlidir."),
            req(True, "Çok yüksek: işaret kaybolursa tekrar gelen istek \"yeni\" görünür ve kart iki kez çekilir. Bir AZ arızası bile işaret kaybetmemeli. Bu gereksinim bu kartta zorunludur.",
                       "Çift çekim doğrudan para ve müşteri kaybıdır; bir arızada \"birkaç saniyelik kayıp\" bile kabul edilemez."),
            req(False, "Ödeme ekibi, sunucu istemiyor, çoklu AZ şart. İşaretler 24 saat sonra kendiliğinden silinmeli.",
                       "Ödeme ekibinin uyum (compliance) yükü vardır; işletilecek bir bileşen daha denetim kapsamına girer."),
            req(False, "Düşük hacim; önemli olan istek başına değil, hatasızlıktır. Yine de sırf bunun için pahalı bir cluster istenmez.",
                       "Günde 20 milyon küçük istek için ay boyu çalışan bir cluster orantısızdır."),
        ],
        cands=["ddb", "ec", "aur"],
        scores={
            "ddb": [sc(10, "PutItem + attribute_not_exists(pk) koşulu (Ö5): id yoksa yazar ve \"yeni\" döner; varsa ConditionalCheckFailedException döner ve uygulama ilk sonucu okur. Kontrol ve işaret tek atomik adımdır. Puan kırılmadı."),
                    sc(10, "3.000 istek tek haneli milisaniyede; on-demand mod. Puan kırılmadı."),
                    sc(10, "Her yazma onaylanmadan önce birkaç AZ'de saklanır. Puan kırılmadı."),
                    sc(10, "Serverless; TTL (Ö6) işaretleri 24 saat sonra siler. Puan kırılmadı."),
                    sc(10, "İstek başına ödeme; günde 20 milyon küçük istek düşük bir faturadır. Puan kırılmadı.")],
            "ec": [sc(10, "SET id result NX EX 86400 tam olarak aynı atomik \"yoksa yaz\" işlemidir ve süreyi de tek komutta verir. Puan kırılmadı."),
                   sc(10, "Mikrosaniye. Puan kırılmadı."),
                   sc(1, "Dayanıklı bir yazma log'u yoktur; bir arıza işaretleri kaybedebilir ve tekrar gelen istek kartı ikinci kez çeker. 9 puan kırıldı: bu zorunlu gereksinimde kayıp kabul edilemez; aday diskalifiye olur. (MemoryDB, dayanıklı log'u olan bellek içi seçenek olarak bu puanı alırdı.)"),
                   sc(10, "Serverless, EXPIRE. Puan kırılmadı."),
                   sc(9, "ECPU ve GB-saat. 1 puan kırıldı: minimum ücret.")],
            "aur": [sc(10, "UNIQUE kısıtı ile INSERT: ikinci istek unique violation alır. Aynı garanti. Puan kırılmadı."),
                    sc(9, "3.000 istek tek writer için kolaydır. 1 puan kırıldı: writer boyutu ve bağlantı havuzu önceden ayarlanır."),
                    sc(10, "Altı kopya. Puan kırılmadı."),
                    sc(6, "Yönetilen. 4 puan kırıldı: 24 saat sonra silme için bir temizlik işi (cron ya da partition drop) yazılır ve işletilir; ödeme ekibi sırf bunun için bir cluster'a sahip olur."),
                    sc(6, "ACU-saat. 4 puan kırıldı: düşük hacim için ay boyu minimum kapasite ödenir.")],
        },
        h2h={
            "ec": _t("Bellek içi key-value (ElastiCache) ile kafa kafaya. Ayrıştığı gereksinim tek: R3 dayanıklılık, ve bu kartta R3 zorunludur. ElastiCache'in SET NX EX komutu idempotency için ders kitabı örneğidir: atomik, tek komut, süreli. "
                      "Ama ElastiCache Serverless'ta her yazmayı diske yazan bir log yoktur; bir arıza son işaretleri kaybedebilir ve kaybolan her işaret çift çekim riskidir. Ödeme ekibi bu riski almaz. "
                      "Bu yüzden aynı kategoride kalıcı olan store seçilir: DynamoDB'nin koşullu PutItem'ı aynı atomik garantiyi dayanıklı bir yazma ile verir. Hangi koşul değişseydi ElastiCache seçilirdi: işaretin kaybı sadece bir yeniden deneme demek olsaydı (örneğin bir e-posta gönderimi için idempotency) ya da bellek içi hız şart olup dayanıklı log istenseydi; o zaman ElastiCache değil MemoryDB seçilirdi."),
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinimler R4 ve R5. Aurora'nın UNIQUE kısıtı aynı garantiyi verir ve ödeme kaydı zaten ilişkisel bir database'teyse işaret ile kaydı aynı transaction'da yazmak en güçlü çözümdür: ya ikisi de yazılır ya hiçbiri. "
                      "Bu iş yükünde ödeme kaydı ayrı bir sistemde ve ayrı bir ekiptedir; sırf idempotency için bir Aurora cluster'ı işletmek, 24 saatlik temizlik işi yazmak ve minimum kapasite ödemek orantısızdır. "
                      "Bu yüzden key-value seçilir. Hangi koşul değişseydi Aurora seçilirdi: ödeme kaydı ile işaret aynı database'te olsaydı; o zaman UNIQUE kısıtı + transaction, iki sistem arasındaki tutarlılık sorununu kökten çözer ve best practice budur."),
        },
        verdict=_t("Karar: DynamoDB 50, Aurora 41, ElastiCache R3'te diskalifiye (40). DynamoDB her gereksinimi tam karşılar; bu use case koşullu yazmanın (Ö5) en saf örneğidir. "
                   "Yine de key-value seçersek artımız: tek atomik istek, kalıcı, serverless, kendini temizleyen işaretler. Potansiyel eksimiz: ödeme kaydı başka sistemde olduğu için işaret ile kayıt tek transaction'da yazılamaz; işaretin value'suna sonucun kendisi yazılmalı ve kayıt yazılamazsa işaret geri alınmalıdır. Bir koşul değişseydi: ödeme kaydı aynı database'te olsaydı Aurora'nın UNIQUE + transaction'ı seçilirdi.")),

    # ------------------------------------------------------------------ 7. seat holds
    usecase("seat", 7,
        title=_t("Bilet ve koltuk tutmaları"),
        key=_t("Key: etkinlik, sonra koltuk. Value: tutan kişi, tutma zamanı, süre sonu."),
        story=_t("Bir bilet sitesi 20.000 koltuklu bir konseri satışa açıyor. İlk dakikada 300.000 kişi salon planına bakar ve koltuk seçer. Seçilen koltuk 10 dakika tutulur; ödeme gelmezse serbest kalır. "
                 "İki kişi asla aynı koltuğu tutmamalı. Satış açılışında saniyede 50.000 tutma denemesi olur; beş dakika sonra saniyede 500'e iner. Bu açılış yılda birkaç kez olur. Ekip altı geliştirici, operasyon ekibi küçük."),
        reqs=[
            req(True, "Sorular: \"bu etkinliğin bütün koltukları ve durumları\", \"bu koltuğu sadece boşsa benim için tut\", \"süresi dolan tutmayı serbest bırak\". Tutma işlemi atomik olmalı: iki kişi aynı anda aynı koltuğu isterse tam olarak biri almalı.",
                      "Çift tutma aynı koltuğun iki kez satılması demektir; konser günü kapıda çözülmesi gereken bir skandaldır."),
            req(True, "Açılış anında saniyede 50.000 tutma denemesi, beş dakika sonra 500. Tepe anında bir tutma 50 ms'nin altında onaylanmalı. Açılış saati bilinir ama o an elle müdahale istenmiyor.",
                      "Açılış anı sitenin itibarıdır; yavaşlarsa kullanıcılar aynı koltuğa defalarca basar ve yük katlanır."),
            req(True, "Yüksek: kaybolan bir tutma aynı koltuğun ikinci bir kişiye satılması demektir. Bir AZ arızası tutma kaybetmemeli. Bu kartta zorunlu.",
                       "Tutma, ödeme tamamlanana kadar koltuğun tek kaydıdır; kaybı çift satıştır."),
            req(False, "Açılış öncesi kapasite planı istenmiyor. Süresi dolan tutmalar kendiliğinden serbest kalmalı; bir temizlik işi istenmiyor.",
                       "Temizlik işi gecikirse koltuk boşken satılamaz; erken çalışırsa ödeme sırasındaki tutma silinir."),
            req(False, "Trafik yılda birkaç kez birkaç dakika; geri kalanda düşük. Kullanım kadar ödeme.",
                       "Açılış için boyutlandırılmış bir sistem yılın yüzde 99,9'unda boş durur."),
        ],
        cands=["ddb", "aur", "ec"],
        scores={
            "ddb": [sc(9, "Partition key etkinlik, sort key koltuk (Ö3): salon planı tek Query. Tutma, attribute_not_exists(holder) OR expires_at < :now koşuluyla UpdateItem (Ö5): iki kişi yarışsa tam olarak biri kazanır. 1 puan kırıldı: süresi dolmuş tutma TTL ile hemen silinmediği için koşula süre karşılaştırması uygulama tarafından eklenmelidir."),
                    sc(8, "On-demand mod 50.000 isteği karşılar (Ö2). 2 puan kırıldı: aynı etkinliğin bütün koltukları tek partition key altında olduğu için açılış anında bütün trafik tek bir gruba, yani tek bir partition'a gider ve partition sınırına (saniyede 1.000 yazma) çarpar; koltuklar blok başına ayrı partition key'lere (EVENT#123#BLOCK#A) bölünmelidir. Bu bir tasarım adımıdır."),
                    sc(10, "Her yazma birkaç AZ'de saklanır; koşullu yazma strongly consistent'tır. Puan kırılmadı."),
                    sc(10, "Serverless; TTL (Ö6) süresi dolan tutmayı siler ve koşuldaki süre karşılaştırması silinmeyi beklemez. Puan kırılmadı."),
                    sc(10, "İstek başına; boş günlerde sıfıra yakın. Puan kırılmadı.")],
            "aur": [sc(10, "SELECT … FOR UPDATE ya da UPDATE … WHERE holder IS NULL ile row kilidi: çift tutma kesin engellenir; salon planı tek sorgudur. Puan kırılmadı."),
                    sc(5, "Açılış anındaki saniyede 50.000 yazma tek writer'ı zorlar; aynı etkinliğin row'larında kilit çekişmesi olur. 5 puan kırıldı: writer önceden en büyük sınıfa alınmalı ve yine de 50 ms sınırı tepe anında garanti değildir."),
                    sc(10, "Altı kopya. Puan kırılmadı."),
                    sc(6, "Yönetilen. 4 puan kırıldı: süresi dolan tutmalar için bir temizlik işi yazılır; açılış öncesi writer büyütülür."),
                    sc(6, "ACU-saat ya da instance-saat. 4 puan kırıldı: açılış için büyütülen kapasite yılın geri kalanında boşa ödenir ya da her açılışta elle değiştirilir.")],
            "ec": [sc(9, "SET seat holder NX EX 600: atomik tutma ve tam anında serbest bırakma tek komutta. Salon planı bir hash'tir. 1 puan kırıldı: \"boşsa ya da süresi dolduysa\" koşulu NX ile doğaldır ama koltuk durumu ile tutma iki ayrı key'se tutarlılık için script gerekir."),
                   sc(10, "Mikrosaniye; Serverless ölçeklenir. Puan kırılmadı."),
                   sc(1, "Dayanıklı yazma log'u yoktur; bir arızada tutmalar kaybolur ve koltuklar ikinci kez satılır. 9 puan kırıldı: zorunlu gereksinimde diskalifiye."),
                   sc(10, "Serverless, EXPIRE. Puan kırılmadı."),
                   sc(8, "ECPU ve GB-saat. 2 puan kırıldı: minimum ücret.")],
        },
        h2h={
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinimler R2 ve R5. Aurora'nın row kilidi çift tutmayı en bilinen yolla engeller ve bir satış sistemi (koltuk, sipariş, ödeme) zaten ilişkiselse tutma aynı transaction'da yazılır. "
                      "Fark açılış anındadır: saniyede 50.000 yazma tek writer'a gider ve aynı etkinliğin row'larında kilitler birbirini bekler; DynamoDB'de yazma koşullu ve kilitsizdir, partition'lara dağılır. DynamoDB'nin bedeli hot partition tasarımıdır: koltuklar bloklara bölünmezse açılış anı tek partition'ı yorar. "
                      "Bu iş yükünde key-value seçilir, çünkü açılış anı belirleyicidir ve boyutlandırmasız, istek başına ödenen bir store yılda birkaç dakikalık tepe için en ekonomik olandır. Hangi koşul değişseydi Aurora seçilirdi: açılış trafiği saniyede birkaç bin yazmada kalsaydı ya da tutma, sipariş ve ödeme tek transaction'da yazılmak zorunda olsaydı; o zaman row kilidi en basit ve en doğru çözümdür."),
            "ec": _t("Bellek içi key-value (ElastiCache) ile kafa kafaya. Ayrıştığı gereksinim R3 dayanıklılık ve bu kartta zorunludur. ElastiCache'in SET NX EX komutu koltuk tutma için neredeyse ideal görünür: atomik, hızlı, tam anında süre sonu. "
                      "Ama tutma ödeme tamamlanana kadar koltuğun tek kaydıdır ve dayanıklı log'u olmayan bir store'da bir arıza o kayıtları kaybeder; kaybolan her tutma çift satıştır. Bu yüzden kalıcı key-value seçilir ve tam anında süre sonu yerine koşula süre karşılaştırması eklenir. "
                      "Hangi koşul değişseydi ElastiCache seçilirdi: tutma kalıcı bir kayıt olarak başka yerde de yazılsaydı ve buradaki sadece hızlı bir kilit olsaydı ya da dayanıklı log istenip bellek içi hız şart olsaydı (MemoryDB)."),
        },
        verdict=_t("Karar: DynamoDB 47, Aurora 37, ElastiCache R3'te diskalifiye (38). Koşullu yazma ve istek başına ölçek bu iş yükünün tam karşılığıdır. "
                   "Yine de key-value seçersek artımız: açılış anı kendiliğinden karşılanır, tutma kuralı tek atomik istek, süre sonu ile serbest bırakma, boş günlerde sıfıra yakın maliyet. "
                   "Potansiyel eksimiz: aynı etkinliğin koltukları bloklara bölünmezse açılış anı hot partition yapar; süre sonu tam anında olmadığı için koşula süre karşılaştırması eklenir; tutma, sipariş ve ödeme tek transaction'da değildir. Bir koşul değişseydi: açılış trafiği düşük ve satış sistemi ilişkisel olsaydı Aurora kazanırdı.")),

    # ------------------------------------------------------------------ 8. rate limits
    usecase("rate", 8, sim="lose_rate", kind="lose",
        title=_t("Rate limit'ler ve sayaçlar"),
        key=_t("Key: kullanıcı id'si ve dakika. Value: bir sayaç."),
        story=_t("Bir API gateway her kullanıcıya dakikada 100 istek izni verir. Her istek sayacı artırır; yeni değer 100'ü geçince istek reddedilir. Sayaç dakika bitince değersizdir. "
                 "Saniyede 20.000 artırma, günün her saati. Sayaç kontrolü her API isteğinin önünde durur: 2 ms gecikme her isteğe 2 ms ekler. Kaybolan bir sayaç bir dakikalığına fazladan 100 istek demektir. Platform ekibi serverless tercih eder."),
        reqs=[
            req(True, "\"Bu kullanıcının bu dakikadaki sayacını 1 artır ve yeni değeri döndür\" tek adımda ve atomik olmalı: aynı anda gelen iki istek ikisi de sayılmalı. Eski dakikaların sayaçları kendiliğinden silinmeli.",
                      "Artırma atomik değilse iki istek aynı değeri okur, ikisi de +1 yazar ve biri kaybolur: limit delinir."),
            req(True, "Saniyede 20.000 artırma, düz. Her artırma 2 ms'nin altında, çünkü her API isteğinin önündedir. Bu gereksinimde gecikme sınırı katıdır.",
                      "Sayaç her isteğe eklenen sabit bir gecikmedir; 2 ms ile 8 ms arasındaki fark günde 1,7 milyar istekte toplam saatler eder."),
            req(False, "Düşük: kaybolan sayaç bir dakikalığına fazladan 100 istek demektir; zararsızdır.",
                       "Rate limit bir koruma kalkanıdır, muhasebe kaydı değildir; bir dakikalık boşluk kabul edilir."),
            req(False, "Platform ekibi, serverless tercih eder, sunucu istemiyor. Sayaç mantığı gateway kodunda birkaç satır olmalı.",
                       "Gateway en çok değişen koddur; sayaç karmaşıksa her değişiklik risk taşır."),
            req(False, "Her artırma bir yazmadır: saniyede 20.000 yazma, ayda 52 milyar. Yazma başına fiyat bu iş yükünün tüm maliyetidir.",
                       "Ayda 52 milyar yazma: yazma birimi fiyatındaki küçük bir fark ayda on binlerce dolardır."),
        ],
        cands=["ddb", "ec", "aur"],
        scores={
            "ddb": [sc(9, "UpdateItem ADD count :one ve ReturnValues = UPDATED_NEW tek atomik artırmadır (Ö5); key'e eklenen dakika (C00001#2026-10-28T14:05) her dakikayı ayrı bir value yapar ve TTL (Ö6) eski dakikaları siler. 1 puan kırıldı: TTL silmesi gecikir, ama eski dakika bir daha okunmadığı için bu sadece storage maliyetidir."),
                    sc(5, "20.000 yazma on-demand ya da provisioned modda karşılanır (Ö2). 5 puan kırıldı: gecikme tek haneli milisaniyedir, 2 ms sınırının üstündedir; her API isteğinin önünde bu fark hissedilir. DAX yazmalara yardım etmez."),
                    sc(10, "Kalıcı. Puan kırılmadı; gereksinim düşük olsa da tam karşılanır."),
                    sc(10, "Serverless, birkaç satır SDK. Puan kırılmadı."),
                    sc(4, "Her artırma bir yazma birimidir: ayda 52 milyar yazma birimi, provisioned modda bile bellek içi store'dan belirgin pahalıdır. 6 puan kırıldı: bu iş yükünün tamamı yazmadır ve yazma DynamoDB'nin en pahalı işlemidir.")],
            "ec": [sc(10, "INCR key tek atomik artırmadır ve yeni değeri döndürür; EXPIRE 60 ile dakika sonunda key tam anında gider. Bu komutlar tam olarak bu iş için vardır. Puan kırılmadı."),
                   sc(10, "Bellekten mikrosaniyelerde; Serverless ölçeklenir. Puan kırılmadı."),
                   sc(6, "Dayanıklı log yok; bir arıza sayaçları sıfırlar ve bir dakikalığına limit gevşer. 4 puan kırıldı: kayıp mümkündür, burada zararsızdır."),
                   sc(10, "Serverless; iki komut. Puan kırılmadı."),
                   sc(10, "ECPU başına; 20.000 küçük artırma bellek içi store'da en ucuz iş yükü sınıfıdır ve veri küçüktür. Puan kırılmadı.")],
            "aur": [sc(9, "UPDATE counters SET n = n + 1 WHERE … RETURNING n atomiktir. 1 puan kırıldı: eski dakikalar için silme işi gerekir."),
                    sc(1, "Saniyede 20.000 küçük yazma tek writer'da kilit çekişmesi ve WAL yükü yaratır; her isteğin önünde 2 ms garanti edilemez. 9 puan kırıldı: zorunlu gereksinimde diskalifiye."),
                    sc(10, "Altı kopya. Puan kırılmadı."),
                    sc(6, "Yönetilen. 4 puan kırıldı: writer boyutlandırma ve temizlik işi."),
                    sc(2, "Sürekli yüksek yazma için büyük bir writer ay boyu ödenir. 8 puan kırıldı: bu iş yükü için en pahalı seçenek.")],
        },
        h2h={
            "ec": _t("Bellek içi key-value (ElastiCache) ile kafa kafaya. Ayrıştığı gereksinimler R2 ve R5, ve ikisi de ElastiCache lehinedir. INCR + EXPIRE sayaç ve rate limit için ders kitabı örneğidir: atomik, mikrosaniye, dakika sonunda tam anında silinir ve 20.000 artırma bellek içi store'un en ucuz işidir. "
                      "DynamoDB aynı işi ADD ile atomik yapar ama tek haneli milisaniyede ve her artırma bir yazma birimi olarak ödenir; bu iş yükünün tamamı yazma olduğu için fatura belirgin yüksektir. Dayanıklılık DynamoDB'nin tek üstünlüğüdür ve burada istenmez. "
                      "Bu iş yükünde key-value kategorisi doğrudur ama kategori içinde bellek içi store seçilir; DynamoDB seçmek yanlış değil, pahalı ve yavaştır. Hangi koşul değişseydi DynamoDB seçilirdi: sayaç bir kota muhasebesi olsaydı (aylık faturalandırılan kullanım) ve kaybı kabul edilmeseydi, gecikme sınırı 10 ms olsaydı ya da artırma hacmi saniyede birkaç yüzde kalsaydı."),
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinimler R2 ve R5. Aurora'nın atomik UPDATE'i doğrudur ama saniyede 20.000 küçük yazma tek writer'ın kilit ve WAL yolunu tıkar; 2 ms'lik sınır tepe anında tutulamaz ve bunun için ay boyu büyük bir writer ödenir. "
                      "Bu iş yükünde ilişkisel database'in gücü (JOIN, transaction, raporlama) hiç kullanılmaz; sadece bedeli ödenir. Sayaç tek bir satırdır, başka bir table ile ilişkisi yoktur ve bir dakika sonra değersizdir; bu veri için kilit, WAL ve vacuum mekanizmalarının tamamı gereksiz yüktür. Bu yüzden Aurora bu kartta R2'de diskalifiye olur: yanlış bir araç değil, yanlış yerde bir araçtır. Hangi koşul değişseydi Aurora seçilirdi: sayaçlar fatura kayıtlarıyla aynı transaction'da güncellenseydi (örneğin aylık kota tüketimi faturaya yazılırken), hacim saniyede birkaç yüzde kalsaydı ve 2 ms sınırı 20 ms'ye gevşeseydi; o zaman tek bir UPDATE … RETURNING hem sayaç hem fatura için en basit çözüm olurdu."),
        },
        verdict=_t("Karar: ElastiCache 46, DynamoDB 38, Aurora R2'de diskalifiye (28). Net bir kaybetme: DynamoDB iş yükünü taşır ama R2'nin katı gecikme sınırı ve R5'in yazma hacmi bellek içi store'u açık ara öne geçirir. "
                   "Yine de DynamoDB seçersek artımız: sayaç kalıcıdır, serverless'tır ve ekip başka table'larla aynı SDK'yı kullanır; kota muhasebesine dönüşürse tasarım değişmez. "
                   "Potansiyel eksimiz: her istek birkaç milisaniye yavaşlar ve ayda 52 milyar yazma biriminin faturası bellek içi store'un katlarcasıdır. Bir koşul değişseydi: sayacın kaybı kabul edilmeseydi ve gecikme sınırı gevşeseydi DynamoDB öne geçerdi.")),

    # ------------------------------------------------------------------ 9. file metadata
    usecase("files", 9,
        title=_t("Dosyaların metadata'sı"),
        key=_t("Key: sahip, sonra klasör ve dosya adı. Value: boyut, durum, tag'ler, storage konumu."),
        story=_t("Bir belge uygulamasında kullanıcılar dosya yükler; dosyanın kendisi S3'e gider. Uygulama her kullanıcının dosyalarını klasör klasör listeler, durumunu (yükleniyor, hazır, silindi), boyutunu ve tag'lerini gösterir. "
                 "On milyon kullanıcı, kullanıcı başına 5 ile 5.000 dosya. Saniyede 5.000 liste okuması ve 500 metadata yazması; iş günü mesai saatlerinde tepe. Liste 100 ms'nin altında açılmalı. Metadata kaybolursa dosya S3'te durur ama kullanıcı onu bulamaz. Ürün ekibi AWS SDK biliyor, sunucu istemiyor."),
        reqs=[
            req(True, "Sorular: \"bu kullanıcının bütün dosyaları, klasör ve ada göre sıralı\", \"bu kullanıcının sadece klasör X'teki dosyaları\", \"bu dosyanın durumunu yükleniyor'dan hazır'a geçir\". Kullanıcı id'si her istekte bilinir. Kullanıcılar birbirinden bağımsızdır. Dosya kayıtlarının alanları türe göre farklıdır (görselde çözünürlük, belgede sayfa sayısı).",
                      "Liste ekranı uygulamanın ana ekranıdır. Durum geçişi yanlış sırada olursa (hazır → yükleniyor) kullanıcı dosyayı kaybolmuş sanır."),
            req(True, "Saniyede 5.000 okuma ve 500 yazma; mesai saatlerinde tepe, gece düşük. Liste 100 ms'nin altında. Kullanıcı başına 5.000 dosya bile tek listede açılabilmeli (sayfalı).",
                      "5.000 dosyalık bir listeyi tek tek okumak 100 ms'yi aşar; liste tek bir sıralı okuma olmalıdır."),
            req(False, "Yüksek: metadata kaybolursa dosya S3'te durur ama kullanıcı onu bulamaz; bu, kullanıcı için kayıp demektir. Bir AZ arızasında kayıp olmamalı.",
                       "Metadata dosyanın adresidir; adres kaybolunca dosya pratikte yoktur."),
            req(False, "Ürün ekibi, AWS SDK biliyor, sunucu istemiyor. Yeni dosya türü için migration istenmiyor. Arama (ada göre, tag'e göre) ileride bir arama servisine verilecek; metadata'nın her değişikliği oraya akmalı.",
                       "Arama index'ini uygulama kodundan beslemek her yazma yolunu ikiye böler ve unutulan bir yol index'i eskitir."),
            req(False, "Düzenli trafik; her iki ödeme modeli de uyar. Metadata küçük (dosya başına 1 KB'tan az), ama 10 milyon kullanıcı × ortalama 200 dosya = 2 milyar kayıt.",
                       "2 milyar küçük kayıt: GB başına storage fiyatı ve kayıt başına okuma fiyatı birlikte belirleyicidir."),
        ],
        cands=["ddb", "aur", "doc"],
        scores={
            "ddb": [sc(9, "Partition key kullanıcı, sort key KLASÖR#dosya (Ö3): bütün dosyalar sıralı tek Query, klasör X bir begins_with dilimi, 5.000 dosya sayfalı okunur. Durum geçişi ConditionExpression status = :from ile tek yazmada korunur (Ö5). Alanlar türe göre farklı (Ö4). 1 puan kırıldı: \"ada göre sıralı ama klasörden bağımsız\" ikinci bir sıra ister; bu bir LSI ya da GSI'dır (Ö7)."),
                    sc(10, "Okumalar kullanıcıya göre partition'lara dağılır (Ö2); 2 milyar kayıt için hiçbir şey değişmez. Puan kırılmadı."),
                    sc(10, "Her yazma birkaç AZ'de; point-in-time recovery. Puan kırılmadı."),
                    sc(10, "Serverless, bildiği SDK, migration yok; değişiklik akışı (Ö8; B5'te Streams) her metadata değişikliğini arama servisine akıtır (OpenSearch'e zero-ETL entegrasyonu da vardır). Puan kırılmadı."),
                    sc(9, "2 milyar × 1 KB = 2 TB; GB başına storage ve istek başına ödeme. 1 puan kırıldı: 5.000 dosyalık bir listeyi okumak birçok okuma birimi tutar; büyük kullanıcılar için sayfa boyutu ve projection ile maliyet sınırlanmalıdır.")],
            "aur": [sc(10, "(owner, folder, name) üzerinde bir index aynı listeyi ve klasör dilimini verir; ada göre ikinci bir index tek satırdır; durum geçişi UPDATE … WHERE status = 'uploading'. Paylaşım gibi ilişkiler eklenince JOIN hazırdır. Puan kırılmadı."),
                    sc(8, "5.000 okuma reader'larla, 500 yazma tek writer'la rahat karşılanır. 2 puan kırıldı: 2 milyar satırlık bir table'da index boyutu ve vacuum bakımı büyür; reader sayısı ekip tarafından seçilir."),
                    sc(10, "Altı kopya. Puan kırılmadı."),
                    sc(7, "Yönetilen; arama servisine akış için Aurora zero-ETL ya da CDC kurulur. 3 puan kırıldı: yeni dosya türü için alan eklemek ALTER TABLE'dır (ya da JSONB), instance ve index bakımı ekibin işidir."),
                    sc(7, "Instance ya da ACU-saat + storage. 3 puan kırıldı: gece düşük trafikte de kapasite ödenir; 2 TB'lık table'ın index'leri storage'ı katlar.")],
            "doc": [sc(10, "Dosya metadata'sı doğal bir document; (owner, folder, name) üzerinde compound index liste ve dilimi verir; tag dizisinde arama multikey index ile mümkündür; durum geçişi updateOne filtresiyle. Puan kırılmadı."),
                    sc(7, "Okumalar replica'larla ölçeklenir. 3 puan kırıldı: 2 milyar document için instance ve index belleği boyutlandırılır; bütün yazmalar tek primary'den geçer."),
                    sc(10, "Altı kopya. Puan kırılmadı."),
                    sc(7, "Şema serbest; change stream'ler arama servisini besler. 3 puan kırıldı: cluster boyutlandırma ve MongoDB API'si ekip için yenidir."),
                    sc(7, "Instance saat başına + storage + I/O. 3 puan kırıldı: düşük trafikte de instance'lar çalışır.")],
        },
        h2h={
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinimler R2, R4 ve R5. Aurora'nın gücü, metadata'nın başka ilişkilerle büyümesinde görünür: paylaşım (\"bu dosyayı gören kullanıcılar\"), klasör ağacı, sürüm geçmişi; bunlar JOIN ile tek sorgudur ve key-value'da her biri bir kopya ya da ikinci index tasarımıdır. "
                      "DynamoDB'nin gücü ölçekte ve operasyondadır: 2 milyar kayıt için index bakımı, vacuum ve instance seçimi yoktur; liste ve klasör dilimi her boyutta aynı maliyettedir; Streams arama servisini kod değişmeden besler. "
                      "Bu iş yükünde key-value seçilir, çünkü sorular sabit ve kullanıcıya göre bağımsızdır, ilişki azdır ve ölçek 2 milyar kayıttır. Hangi koşul değişseydi Aurora seçilirdi: paylaşım, izin ve klasör ağacı gibi çok yönlü ilişkiler ana özellik olsaydı ya da raporlar (\"en çok yer kaplayan 100 kullanıcı\") sık sorulsaydı; o zaman ilişkisel model ve SQL bu soruları doğrudan cevaplar."),
            "doc": _t("Document (DocumentDB) ile kafa kafaya. Ayrıştığı gereksinimler R2, R4 ve R5. DocumentDB R1'de DynamoDB kadar iyidir, hatta tag dizisinde arama (multikey index) ve iç içe metadata güncellemede daha doğaldır. "
                      "Fark 2 milyar kayıt ölçeğinde ve operasyondadır: DocumentDB'de instance, index belleği ve replica sayısı ekip tarafından seçilir ve bütün yazmalar tek primary'den geçer; DynamoDB'de bu kararlar yoktur. Ekip MongoDB API'sini bilmez. "
                      "Bu yüzden key-value seçilir. Hangi koşul değişseydi DocumentDB seçilirdi: tag ve iç içe metadata üzerinde esnek sorgular (\"tag'i fatura olan ve sayfa sayısı 10'dan büyük belgelerim\") ana access pattern olsaydı ve arama servisi istenmeseydi; o zaman document database bu soruları tek index'le cevaplar ve ayrı bir arama sistemine gerek kalmaz."),
        },
        verdict=_t("Karar: DynamoDB 48, Aurora 42, DocumentDB 41. Access pattern'ler sabit, kullanıcılar bağımsız ve ölçek büyük; bu üçlü key-value'nun ev sahası. "
                   "Yine de key-value seçersek artımız: liste ve klasör dilimi her boyutta ucuz, 2 milyar kayıt için bakım yok, metadata kalıcı, değişiklik akışı arama servisini besler. "
                   "Potansiyel eksimiz: \"tag'i fatura olan bütün dosyalarım\" gibi value içi sorular GSI ister ya da arama servisine gider; paylaşım iki yönlü bir ilişkidir ve iki kopya olarak tutulur; 5.000 dosyalık listeler sayfalı okunmalıdır. Bir koşul değişseydi: paylaşım ve izin ilişkileri ana özellik olsaydı Aurora kazanırdı.")),

    # ------------------------------------------------------------------ 10. recommendations
    usecase("ads", 10,
        title=_t("Reklam ve öneri sorguları"),
        key=_t("Key: kullanıcı id'si. Value: önceden hesaplanmış 50 ürünlük liste."),
        story=_t("Bir e-ticaret sitesinin öneri modeli her gece her kullanıcı için 50 ürünlük bir liste hesaplar. Ana sayfa açılırken bu liste okunur ve \"sana özel\" bölümünde gösterilir. "
                 "Hesap gece 02:00'de 30 dakikada toplu yapılır: 20 milyon kullanıcı için 20 milyon yazma. Gündüz sadece okuma vardır: saniyede 100.000. Liste 5 ms içinde gelmezse sayfa beklemez, genel bir liste gösterir. Kaybolan liste yarın yeniden hesaplanır. Veri ekibi batch işleri biliyor, sunucu istemiyor."),
        reqs=[
            req(True, "Tek soru: \"bu kullanıcının listesi\". Liste tek bir value'dur (50 ürün id'si, 2 KB). Gece toplu yazma, gündüz sadece okuma. Listeye göre sorgu yoktur.",
                      "Ana sayfa bu okumayla açılır; soru tek ve basittir, model de öyle olmalıdır."),
            req(True, "Gündüz saniyede 100.000 okuma, katı 5 ms sınırı (aşılırsa sayfa genel listeyi gösterir ve öneri boşa gider). Gece 30 dakikada 20 milyon yazma, yani saniyede 11.000 yazma; gündüz sıfır yazma.",
                      "Gecikme sınırı aşıldığında öneri gösterilmez; modelin bütün işi boşa gider. Gece yazma penceresi dar: 30 dakikada bitmezse sabah eski listeler kalır."),
            req(False, "Düşük: liste her gece yeniden hesaplanır; kaybolursa bir gün genel liste gösterilir.",
                       "Türetilmiş veri; kaynağı modeldir ve yarın yeniden üretilir."),
            req(False, "Veri ekibi batch işleri ve AWS SDK biliyor, sunucu istemiyor. Gece toplu yazma için ayrı bir büyütme işi istenmiyor.",
                       "Her gece elle kapasite artırıp sabah düşürmek sürdürülemez; otomatik olmalıdır."),
            req(False, "Okuma çok yüksek ve düz; okuma başına fiyat belirleyicidir. 20 milyon × 2 KB = 40 GB veri. Gece yazma maliyeti ayrıca hesaplanır.",
                       "Günde 8,6 milyar okuma: okuma birimi fiyatı bu iş yükünün faturasıdır."),
        ],
        cands=["ddb", "ec", "aur"],
        scores={
            "ddb": [sc(10, "Simple primary key = kullanıcı id'si; liste tek bir value, GetItem tek okuma (Ö1). Gece her value PutItem ile üzerine yazılır (A6: var olan key, value'nun tamamı); BatchWriteItem 25'lik gruplarla yazar. Puan kırılmadı."),
                    sc(8, "100.000 okuma partition'lara dağılır (Ö2). Gece 11.000 yazma on-demand ya da zamanlanmış auto scaling ile karşılanır. 2 puan kırıldı: tek haneli milisaniye 5 ms sınırına yakındır ve bazı okumalar sınırı aşabilir; DAX eklenirse okuma mikrosaniyeye iner ama DAX ayrı bir cluster'dır."),
                    sc(10, "Kalıcı. Puan kırılmadı."),
                    sc(10, "Serverless; gece yazma için zamanlanmış auto scaling ya da on-demand. Puan kırılmadı."),
                    sc(6, "Günde 8,6 milyar okuma birimi (2 KB value eventually consistent okumada 1 birim); provisioned + reserved capacity ile ödenir. 4 puan kırıldı: bu hacimde okuma birimi faturası bellek içi cache'ten belirgin yüksektir; DAX eklenirse okuma maliyeti düşer ama DAX'ın saat ücreti eklenir.")],
            "ec": [sc(10, "Kullanıcı başına bir key; GET tek okuma; gece SET ile üzerine yazılır. Puan kırılmadı."),
                   sc(10, "Bellekten 1 ms'nin altında; 5 ms sınırı rahat karşılanır. Serverless 100.000 okumayı ölçekler; gece 11.000 yazma sorun değildir. Puan kırılmadı."),
                   sc(6, "Dayanıklı log yok; bir arızada listeler kaybolur ve bir gün genel liste gösterilir. 4 puan kırıldı: kayıp mümkündür, burada kabul edilir."),
                   sc(10, "Serverless. Puan kırılmadı."),
                   sc(7, "ECPU ve GB-saat; okuma bellek içi store'un en ucuz işidir. 3 puan kırıldı: 40 GB verinin bellekte tutulması GB-saat olarak diskten çok daha pahalıdır; bu iş yükünde okuma ucuzluğu bu maliyeti büyük ölçüde telafi eder.")],
            "aur": [sc(9, "Primary key ile okuma, JSONB ya da array kolon. 1 puan kırıldı: gece 20 milyon satırın güncellenmesi büyük bir transaction ya da toplu COPY ister ve vacuum yükü yaratır."),
                    sc(4, "100.000 okuma için birçok reader instance gerekir; her biri önceden boyutlandırılır. 6 puan kırıldı: 5 ms sınırı reader'lar sıcakken tutulur, ama gece toplu yazma sırasında replica gecikmesi ve vacuum okumaları yavaşlatabilir."),
                    sc(10, "Altı kopya. Puan kırılmadı."),
                    sc(6, "Yönetilen. 4 puan kırıldı: reader filosu ve gece toplu yazma penceresi ekibin planlamasıdır."),
                    sc(3, "Saniyede 100.000 okuma için reader filosu saat başına ödenir. 7 puan kırıldı: bu iş yükü için en pahalı seçenek.")],
        },
        h2h={
            "ec": _t("Bellek içi key-value (ElastiCache) ile kafa kafaya. Ayrıştığı gereksinimler R2 ve R5 ElastiCache lehine, R3 DynamoDB lehine. Bu iş yükü bir cache'in tanımıdır: türetilmiş veri, gündüz sadece okuma, katı gecikme sınırı, kayıp kabul edilir. "
                      "ElastiCache 5 ms sınırını rahat karşılar ve okuma başına maliyeti en düşüktür; DynamoDB tek haneli milisaniyeyle sınıra yakındır ve 8,6 milyar okuma birimi pahalıdır. DynamoDB'nin tek üstünlüğü dayanıklılıktır ve burada istenmez. "
                      "Puanlar DynamoDB'yi bir puan önde gösterir, ama fark hata payının içindedir; best practice iki store'u birlikte kullanmaktır: listeler gece DynamoDB'ye yazılır (kalıcı kayıt, kolay toplu yazma), gündüz DAX ya da ElastiCache önünde cache olur. "
                      "Hangi koşul değişseydi ElastiCache tek başına seçilirdi: bellek maliyeti kabul edilir olsaydı ve listelerin kaybı gerçekten önemsiz olsaydı; o zaman gece doğrudan cache'e yazılır ve DynamoDB hiç kullanılmaz."),
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinimler R2 ve R5. Aurora'nın gücü, önerilerin ürün kataloğu ve stokla birlikte sorgulanmasında görünürdü (\"önerilen ve stokta olan ürünler\"); bu iş yükünde liste önceden hesaplanmış bir value'dur ve JOIN yoktur. "
                      "Saniyede 100.000 okuma için reader filosu ve gece 20 milyon satırlık toplu güncelleme Aurora'yı bu iş için en pahalı ve en çok bakım isteyen seçenek yapar: reader sayısı ve sınıfı önceden seçilir, gece toplu yazma sırasında replica gecikmesi ve vacuum okumaları yavaşlatabilir ve bütün bu kapasite gündüz de gece de saat başına ödenir. "
                      "Bu iş yükünde key-value seçilir, çünkü tek soru \"bu kullanıcının listesi\"dir ve listenin içine ya da katalogla ilişkisine göre hiçbir sorgu yoktur; ilişkisel database'in gücü kullanılmaz, sadece bedeli ödenir. "
                      "Hangi koşul değişseydi Aurora seçilirdi: öneri listesi katalog ve stokla aynı sorguda filtrelenseydi (\"önerilen ve stokta olan ürünler\"), okuma hacmi saniyede birkaç binde kalsaydı ve uygulama zaten Aurora üzerinde çalışıyor olsaydı; o zaman öneri listesi bir table daha olur ve JOIN bu soruyu tek sorguda cevaplardı."),
        },
        verdict=_t("Karar: DynamoDB 44, ElastiCache 43, Aurora 32. Bir puanlık fark bir karar değildir; bu iş yükünde doğru cevap \"ikisi birlikte\"dir: kalıcı liste DynamoDB'de, sıcak okuma DAX ya da ElastiCache'te. "
                   "Yine de yalnız DynamoDB seçersek artımız: kalıcı, serverless, gece toplu yazma ve gündüz okuma için kapasite ayrı ayrı ayarlanır, DAX ile mikrosaniye mümkündür. "
                   "Potansiyel eksimiz: 5 ms sınırı tek haneli milisaniyeye yakındır ve bazı okumalar aşabilir; 8,6 milyar okuma biriminin faturası bellek içi cache'ten yüksektir. Bir koşul değişseydi: listelerin kaybı gerçekten önemsiz ve bellek maliyeti kabul edilir olsaydı ElastiCache tek başına seçilirdi.")),
]

USECASES = {"dynamodb": DDB_USECASES}


def apply_en(usecases, en):
    """Merge the English text (e2e_usecases_en.EN) into the (en, tr) tuples of the use cases."""
    for uc in usecases:
        e = en.get(uc["id"])
        if not e:
            continue
        for f in ("title", "key", "story", "verdict"):
            uc[f] = (e[f], uc[f][1])
        for r, (want, why) in zip(uc["reqs"], e["reqs"]):
            r["want"] = (want, r["want"][1])
            r["why"] = (why, r["why"][1])
        for c in uc["cands"]:
            uc["scores"][c] = [(p, (e["scores"][c][i], tr)) for i, (p, (_, tr)) in enumerate(uc["scores"][c])]
        for c, text in e["h2h"].items():
            uc["h2h"][c] = (text, uc["h2h"][c][1])
    return usecases


from .e2e_usecases_en import EN as _EN  # noqa: E402
apply_en(DDB_USECASES, _EN)


# ====================================================================== Aurora PostgreSQL (page id "aurora"), Turkish only
# Sources of the limits and numbers quoted in the reasons below (the hedges are the hedges of the source):
#  - Aurora storage: "copies of the data across three Availability Zones", six storage nodes, volume grows automatically:
#    https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.StorageReliability.html and
#    https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html
#  - Aurora Replicas: "up to 15 Aurora Replicas", replica lag "usually considerably less than 100 milliseconds":
#    https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.Performance.html
#  - Failover: "service is typically restored in less than 60 seconds, and often less than 30 seconds":
#    https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html
#  - Serverless v2: each ACU "approximately 2 GiB of memory", 0.5 to 256 ACU, 0 ACU with auto-pause on supported versions:
#    https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.how-it-works.html
#  - Aurora Standard (pay per I/O request) and Aurora I/O-Optimized (no I/O charge, best when I/O is 25% or more of the spend):
#    https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.StorageReliability.html
#  - Zero-ETL to Redshift: data available in Redshift "within seconds of being written":
#    https://aws.amazon.com/blogs/database/amazon-aurora-postgresql-zero-etl-integration-with-amazon-redshift-is-generally-available/
#  - PostgreSQL row-level security: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
#  - PostgreSQL exclusion constraints and primary key index: https://www.postgresql.org/docs/current/ddl-constraints.html
#  - PostgreSQL VACUUM and dead row versions: https://www.postgresql.org/docs/current/routine-vacuuming.html
#  - RDS Multi-AZ failover "typically 60-120 seconds": https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html
#  - DynamoDB transactions "up to 100 write actions": https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html
#  - DynamoDB TTL deletes "within a few days": https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html
#  - DocumentDB transactions (version 4.0 and later): https://docs.aws.amazon.com/documentdb/latest/developerguide/transactions.html

CATEGORY["rds"] = ("relational", "ilişkisel")
LINK["rds"] = "aurora"

AURORA_USECASES = [
    # ------------------------------------------------------------------ 1. checkout: order, stock, payment (clear win)
    usecase("checkout", 1, sim="win_checkout", kind="win",
        title=_t("Sipariş, stok ve ödeme: checkout (Lale Market)"),
        key=_t("Table'lar: products, orders, order_items, payments. Kural: stok sıfırın altına inmez, sipariş stoksuz var olmaz."),
        story=_t("Lale Market'in checkout düğmesi dört şeyi birden yapar: sepetteki her ürünün stoğunu düşürür, siparişi ve line'larını yazar ve ödeme kaydını açar. "
                 "Mağazanın kuralı: bir sipariş hiçbir zaman stok düşmeden var olmaz, stok hiçbir zaman sıfırın altına inmez ve son adedi aynı saniyede isteyen iki müşteriden tam olarak biri alır. "
                 "Normal günde saatte 400 sipariş, kampanya akşamlarında saatte 3.000 sipariş; yani saniyede en fazla birkaç checkout. Ürün sayfası stoğu saniyede 300 kez okur. "
                 "Bugün 5.000 sipariş ve 12.500 line var; yılda iki katına çıkıyor. Sipariş paranın resmi kaydıdır: kaybolan bir sipariş kaybolan paradır. Ekipte üç geliştirici var, hepsi SQL biliyor, database yöneticisi yok."),
        reqs=[
            req(True, "Checkout'un dört yazması (stok, sipariş, line'lar, ödeme) ya hep ya hiç olmalı. Stok için \"stock - qty >= 0\" kuralı yazma anında korunmalı. Son adet için iki eşzamanlı checkout'tan tam olarak biri kazanmalı. "
                      "Bir line var olmayan bir ürünü, bir sipariş var olmayan bir müşteriyi gösterememeli. Sorular: \"bu müşterinin siparişleri\", \"bu siparişin line'ları ürün adlarıyla\", \"stoğu 10'un altındaki ürünler\".",
                      "Ödeme alınıp sipariş yazılmazsa müşteri parasını öder ve ürün gelmez; stok düşüp sipariş yazılmazsa depo var olmayan bir siparişe mal ayırır. Kural uygulama kodunda \"önce oku sonra yaz\" ile korunursa iki sekme aynı son adedi satar."),
            req(True, "Normal günde saniyede 0,1 checkout, kampanya akşamı saniyede 1 ile 3; tepe anında 10. Ürün sayfası saniyede 300 stok okuması, sipariş geçmişi saniyede 50 okuma. Checkout 100 ms'nin altında dönmeli. Veri yılda iki katına çıkıyor ama birkaç GB'ı geçmiyor.",
                      "Yazma hacmi küçüktür; burada ölçek değil doğruluk belirleyicidir. Ama ürün sayfasının stok okuması her ziyaretçinin önündedir ve checkout'u yavaşlatmamalıdır."),
            req(True, "Sipariş paranın resmi kaydıdır. Bir Availability Zone arızasında tek bir commit edilmiş sipariş kaybolmamalı; yanlış bir toplu silme bir saat öncesine geri alınabilmeli. Bu kartta dayanıklılık zorunludur.",
                       "Kaybolan sipariş, ödenmiş ama gönderilmemiş üründür: para iadesi, destek talebi ve muhasebe düzeltmesi. Yedekten geri dönüş saatler sürerse mağaza o saatlerde satış yapamaz."),
            req(False, "Üç geliştirici, SQL biliyor, database yöneticisi yok. Sunucu boyutlandırmak, yama geçmek, yedek almak ve failover kurmak istenmiyor. Yeni bir kolon ya da yeni bir table eklemek bir migration ile yapılabilir; ekip bunu biliyor.",
                       "Küçük ekipte database operasyonu ürün geliştirmeden çalınan zamandır. Bir failover'ı gece üçte elle yapmak zorunda kalan ekip bir sonraki ayı kaybeder."),
            req(False, "Trafik küçük ve çoğunlukla düz, kampanya akşamları birkaç kat. Saat başına ya da kapasite başına ödeme kabul; ama boş gecelerde büyük bir sunucu ödemek istenmiyor. Veri küçük (birkaç GB).",
                       "Yük küçük olduğu için fatura kapasitenin alt sınırıyla belirlenir; alt sınırı yüksek olan bir model boş gecelerde boşa öder."),
        ],
        cands=["aur", "ddb", "doc"],
        scores={
            "aur": [sc(10, "Dört yazma tek transaction'dır (Ö5): BEGIN, UPDATE products ... WHERE stock >= qty, INSERT orders, INSERT order_items, INSERT payments, COMMIT; biri başarısız olursa hepsi geri alınır. CHECK (stock >= 0) ve foreign key'ler (Ö1, Ö2) var olmayan ürünü ve negatif stoğu database'in kendisi reddeder. Koşullu UPDATE row lock altında test eder: son adedi tam olarak bir checkout alır. Bütün sorular SQL'dir (Ö3). Puan kırılmadı."),
                    sc(10, "Saniyede 10 checkout tek writer için küçük bir yüktür; 300 stok okuması primary key ile index araması (Ö4), reader instance'a yönlendirilebilir (Ö7). Serverless v2 kampanya akşamı kapasiteyi 0,5 ACU adımlarıyla artırır; tepe saniyede 10 checkout olduğu için ACU büyüme gecikmesi bu hacimde hissedilmez (kart 3 ve 8'deki yoğun satır yarışı burada yoktur). Puan kırılmadı."),
                    sc(10, "Aurora'nın paylaşılan storage'ı veriyi üç Availability Zone'da altı storage node'a yazar (Ö7); bir AZ arızası commit edilmiş siparişi kaybetmez. Point-in-time restore yanlış bir silmeyi saniye hassasiyetiyle geri alır. Puan kırılmadı."),
                    sc(9, "Yedek, yama, failover ve storage büyümesi yönetilir; ekip bildiği SQL ve psycopg ile çalışır. 1 puan kırıldı: schema, index'ler, ACU aralığı ve bağlantı havuzu yine ekibin kararıdır ve migration disiplini ister."),
                    sc(8, "Serverless v2 ACU-saniye olarak ödenir, boş gecelerde 0,5 ACU'ya iner. 2 puan kırıldı: minimum ACU boş gecede de ödenir ve Aurora Standard'da I/O isteği başına ek ücret vardır; küçük bir mağaza için bu, istek başına ödemeden pahalı olabilir.")],
            "ddb": [sc(5, "TransactWriteItems en fazla 100 item'ı ya hep ya hiç yazar ve stok için ConditionExpression \"stock >= :q\" koşulu tek item'da korunur. 5 puan kırıldı: foreign key yoktur, var olmayan ürünü ya da müşteriyi gösteren bir line database tarafından reddedilmez; \"stoğu 10'un altındaki ürünler\" ve \"siparişin line'ları ürün adlarıyla\" soruları ya ikinci bir index ya da uygulama tarafında birleştirme ister. Kurallar uygulama kodunda yaşar."),
                    sc(10, "On-demand mod saniyede 10 transaction'ı ve 300 okumayı tek haneli milisaniyede karşılar. Puan kırılmadı."),
                    sc(10, "Her yazma birkaç AZ'de saklanır; point-in-time recovery vardır. Puan kırılmadı."),
                    sc(7, "Serverless: yama, yedek, failover yok. 3 puan kırıldı: ekip SQL biliyor, DynamoDB için access pattern'leri önceden listeleyip key tasarlamayı ve JOIN'siz düşünmeyi öğrenir; her yeni rapor sorusu yeni bir tasarım adımıdır."),
                    sc(9, "İstek başına ödeme; boş gecede sıfıra yakın. 1 puan kırıldı: transactional yazma normal yazmanın iki katı birim tüketir.")],
            "doc": [sc(4, "DocumentDB 4.0 ve sonrası birden fazla document üzerinde ACID transaction destekler; sipariş ve line'ları tek document'ta tutmak doğaldır. 6 puan kırıldı: foreign key ve CHECK yoktur, stok kuralı ve ürünün varlığı uygulama kodunda korunur; \"stoğu 10'un altındaki ürünler\" ve müşteri siparişleri soruları için ayrı index'ler kurulur ve JOIN benzeri $lookup sınırlıdır."),
                    sc(9, "Saniyede 10 yazma ve 300 okuma tek primary ve replica'larla rahat karşılanır. 1 puan kırıldı: primary instance sınıfı önceden seçilir."),
                    sc(10, "Üç AZ'de altı kopya, sürekli yedek. Puan kırılmadı."),
                    sc(6, "Yedek ve yama yönetilir. 4 puan kırıldı: instance boyutlandırma ve replica yönetimi ekibin işidir, MongoDB API'si bu SQL ekibi için yenidir ve kurallar database'de değil kodda yaşar."),
                    sc(6, "Instance saat başına ve I/O başına ödenir. 4 puan kırıldı: Multi-AZ için en az iki instance boş gecelerde de çalışır; bu küçük iş yükü için en pahalı seçenektir.")],
        },
        h2h={
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinim R1'in kural kısmı ve R4. DynamoDB'nin gücü R2 ve R5'te görünür: kampanya akşamı için hiçbir şey ayarlanmaz ve boş gecede ödeme sıfıra yakındır; TransactWriteItems ile dört yazma ya hep ya hiç yapılabilir. "
                      "Aurora'nın gücü kuralın yerindedir: stok, sipariş, line ve ödeme dört ayrı table'dır ve aralarındaki kuralları (foreign key, CHECK, koşullu UPDATE) database'in kendisi her yazmada uygular; DynamoDB'de bu kurallar uygulama kodunda yaşar ve ikinci bir program ya da bir bug onları atlayabilir. "
                      "Bu iş yükünde ilişkisel seçilir, çünkü yazma hacmi küçük, kurallar table'lar arası ve veri paranın resmi kaydıdır; DynamoDB'nin ölçek gücü burada kullanılmayacak bir güçtür. "
                      "Hangi koşul değişseydi DynamoDB seçilirdi: checkout hacmi saniyede binlere çıksaydı, sipariş tek bir value olarak yazılıp ilişkisi olmasaydı ve raporlar ayrı bir analitik kopyadan sorulsaydı."),
            "doc": _t("Document (DocumentDB) ile kafa kafaya. Ayrıştığı gereksinimler R1'in kural kısmı, R4 ve R5. DocumentDB'nin gücü siparişin şeklinde görünür: sipariş, line'ları ve adresiyle tek bir document'tır ve tek okumayla gelir; transaction desteği de vardır. "
                      "Aurora'nın gücü kuralların database'de yaşamasıdır: var olmayan ürünü gösteren line, negatif stok ve iki kez satılan son adet database tarafından reddedilir; DocumentDB'de bu kontroller uygulama kodunda yazılır ve her yeni program onları yeniden yazar. "
                      "Ayrıca \"stoğu azalan ürünler\" ve \"bu müşterinin bütün siparişleri ürün adlarıyla\" gibi sorular SQL'de JOIN ile tek sorgudur. Bu iş yükünde ilişkisel seçilir, çünkü sipariş birbiriyle ilişkili dört şeyin kaydıdır, tek bir belge değildir. "
                      "Hangi koşul değişseydi DocumentDB seçilirdi: sipariş iç içe, sık şekil değiştiren ve ilişkisi olmayan bir belge olsaydı, ekip MongoDB API'sini zaten biliyor olsaydı ve stok kuralı başka bir sistemde korunuyor olsaydı."),
        },
        verdict=_t("Karar: Aurora 47, DynamoDB 41, DocumentDB 35. Net bir kazanma: iş yükü ilişkisel modelin tam tanımıdır; dört table arası kural, ya hep ya hiç yazma ve küçük yazma hacmi. Aurora hiçbir zorunlu gereksinimde puan kaybetmez. "
                   "Yine de ilişkisel seçersek artımız: kurallar database'de yaşar ve her programa uygulanır, checkout tek transaction'dır, her yeni rapor sorusu bir SQL cümlesidir, sipariş altı kopyayla kalıcıdır. "
                   "Potansiyel eksimiz: bütün yazmalar tek writer'dan geçer ve saniyede on binlerce checkout'a çıkılırsa tasarım değişir; boş gecelerde minimum ACU ödenir; schema değişiklikleri migration disiplini ister; ödeme dış bir servisse transaction ödeme çağrısı boyunca açık tutulmamalı, ödeme önce yetkilendirilmelidir (B5). Bir koşul değişseydi: checkout hacmi saniyede binlere çıksaydı ve sipariş ilişkisiz tek bir value olsaydı DynamoDB yarışa girerdi.")),

    # ------------------------------------------------------------------ 2. product catalog with relations (race vs DocumentDB)
    usecase("catalog", 2, sim="race_catalog", kind="race",
        title=_t("İlişkileriyle ürün kataloğu: kategori, marka, varyant"),
        key=_t("Table'lar: products, categories, brands, variants, prices. Değişken özellikler JSONB kolonunda."),
        story=_t("Bir pazar yerinin kataloğunda 50.000 ürün ve 300.000 varyant var: bir ayakkabının numarası ve rengi, bir televizyonun ekran boyu. Her ürün tam olarak bir markaya ve bir kategoriye aittir; her varyantın depo başına stoğu ve para birimine göre fiyatı vardır. "
                 "Ürün sayfası saniyede 2.000 kez okunur (önünde bir cache var), satıcılar saniyede 50 değişiklik yapar. Kategori ekibi her ay yeni özellikler tanımlar: \"su geçirmez\", \"ekran yenileme hızı\". "
                 "Sorular: \"bu kategoride, bu markanın, 42 numara ve kırmızı varyantları\", \"fiyatı değişen ürünler\", \"stoğu biten varyantların ürünleri\". Metin araması ayrı bir arama servisine verilecek. Dört geliştirici, SQL biliyor; katalog kaybolursa satıcı beslemelerinden günlerce yeniden kurulur."),
        reqs=[
            req(True, "Ürün id'siyle okuma; kategori + marka + varyant özelliğiyle filtre; ürün, varyant, fiyat ve stok ilişkileri tek sorguda. Kurallar: bir varyant tam olarak bir ürüne aittir, fiyat sıfırdan büyüktür, silinen markanın ürünü kalmaz. Yeni özellik eklemek table'ı yeniden tasarlamamalı.",
                      "Varyantın sahibi olmayan bir ürün sayfası boş bir kutudur; sıfır fiyatlı bir ürün bedava satılır. Her yeni özellik için bir migration penceresi, kategori ekibini database ekibine bağlar."),
            req(True, "Saniyede 2.000 okuma (cache arkasında), 50 yazma. Her okuma 50 ms'nin altında. Katalog yılda iki katına çıkıyor; 100.000 ürün ve 600.000 varyant için tasarım değişmemeli.",
                      "Ürün sayfası mağazanın vitrinidir; yavaş sayfa satış kaybıdır. Yılda iki kat büyüme için her yıl yeniden tasarım yapılamaz."),
            req(False, "Katalog satıcı beslemelerinden yeniden kurulabilir ama bu günler sürer. Bir AZ arızası kayıp yapmamalı.",
                       "Katalog kaybı mağazayı günlerce kapatmaz ama vitrini boşaltır; dayanıklılık burada güçlü bir tercihtir, zorunluluk değildir."),
            req(False, "Dört geliştirici, SQL biliyor. Aylık yeni özellikler migration istemeden eklenebilmeli. Sunucu boyutlandırma, yama ve yedek istenmiyor.",
                       "Her ay bir ALTER TABLE ve bir bakım penceresi kategori ekibinin takvimini kilitler; ekip bilmediği bir API'ı öğrenirken hata yapar."),
            req(False, "Trafik gün içinde düz, okuma ağırlıklı. Kapasite başına ödeme uyar. Veri orta boy (on GB).",
                       "Düz trafikte kapasite başına ödeme istek başına ödemeden ucuz olabilir; büyümede bir instance sınıfı atlamak maliyeti bir gecede katlar."),
        ],
        cands=["aur", "doc", "os"],
        scores={
            "aur": [sc(9, "Ürün, kategori, marka, varyant ve fiyat ayrı table'lar; foreign key'ler (Ö2) bir varyantı tam olarak bir ürüne bağlar, CHECK (price > 0) sıfır fiyatı reddeder (Ö1), ON DELETE kuralları markası silinen ürünü yönetir. Filtreler ve ilişkiler JOIN ile tek sorgudur (Ö3). Değişken özellikler bir JSONB kolonunda durur ve GIN index ile sorgulanır (Ö8). 1 puan kırıldı: JSONB içindeki bir özelliğe göre filtre, normal bir kolona göre filtreden daha az doğaldır; operatörleri ve GIN index'i ekip öğrenir."),
                    sc(9, "2.000 okuma primary key ve index aramalarıdır (Ö4) ve reader instance'lara dağıtılır (Ö7); 50 yazma tek writer için küçüktür. 1 puan kırıldı: reader sayısını ve ACU aralığını ekip seçer."),
                    sc(10, "Üç AZ'de altı kopya, point-in-time restore. Puan kırılmadı."),
                    sc(8, "Yedek, yama ve failover yönetilir; ekip SQL'i biliyor. Yeni özellik JSONB'ye yazılır, migration gerekmez. 2 puan kırıldı: yeni bir ilişki (örneğin \"ürün setleri\") yine bir migration'dır ve instance ya da ACU kararı ekibindir."),
                    sc(8, "ACU-saat ya da instance-saat; düz trafikte öngörülebilir. 2 puan kırıldı: gece düşük trafikte de minimum kapasite ödenir; okuma için reader instance ayrıca ödenir.")],
            "doc": [sc(8, "Ürün bir document, varyantlar içinde bir dizi: tek okumayla ürün sayfası gelir; her alana ve dizi içindeki alanlara index kurulur (multikey). Yeni özellik sadece yeni document'lara yazılır. 2 puan kırıldı: foreign key yoktur, marka ve kategori id olarak yazılır ve varlığı uygulama kontrol eder; \"fiyat > 0\" schema validation ile kısmen korunur; \"stoğu biten varyantların ürünleri\" gibi ilişkili sorular $lookup ile daha zahmetlidir."),
                    sc(9, "Okumalar en fazla 15 replica'ya dağılır; 50 yazma tek primary için küçüktür. 1 puan kırıldı: instance sınıfı ve replica sayısı önceden seçilir; büyüme bir büyütme adımıdır."),
                    sc(10, "Üç AZ'de altı kopya, sürekli yedek. Puan kırılmadı."),
                    sc(8, "Şema serbest, yeni özellik migration istemez; yedek ve yama yönetilir. 2 puan kırıldı: MongoDB API'si bu SQL ekibi için yenidir ve instance boyutlandırma ekibin işidir."),
                    sc(7, "Instance saat başına ve I/O başına. 3 puan kırıldı: Multi-AZ için birkaç instance gece de çalışır; büyümede bir sınıf atlamak maliyeti sıçratır.")],
            "os": [sc(6, "Varyant özelliklerine göre filtre ve facet OpenSearch'ün ana işidir; metin araması da burada olur. 4 puan kırıldı: ilişkiler index'e yazılırken düzleştirilir, transaction ve foreign key yoktur, \"fiyat > 0\" gibi kurallar yoktur; bir markanın adı değişince bütün ürün dokümanları yeniden yazılır."),
                   sc(9, "2.000 okuma ve 50 yazma bir domain için küçüktür; refresh aralığı yüzünden yeni yazma kısa bir süre görünmeyebilir. 1 puan kırıldı: shard sayısı ve node sınıfı önceden seçilir."),
                   sc(5, "Replica shard'lar node arızasını karşılar. 5 puan kırıldı: arama index'i resmi kayıt değildir; mapping değişince index baştan kurulur ve kaynak veri başka bir yerde durmalıdır."),
                   sc(6, "Yönetilen domain. 4 puan kırıldı: mapping tasarımı, reindex ve shard planı ekibin işidir; katalog kuralları kodda yaşar."),
                   sc(6, "Node saat başına. 4 puan kırıldı: üç node'luk bir domain gece de ödenir ve katalog için ayrıca bir kayıt sistemi gerekir.")],
        },
        h2h={
            "doc": _t("Document (DocumentDB) ile kafa kafaya. Bu, okuyucunun en çok \"neden o değil?\" dediği yarıştır, çünkü bir ürün sayfası tam bir document gibi görünür ve varyant özellikleri kategoriye göre değişir. Ayrıştığı gereksinimler R1'in kural kısmı ve R4. "
                      "DocumentDB'nin gücü şekildedir: ürün, varyantları ve özellikleriyle tek bir document'tır, tek okumayla gelir ve yeni özellik hiçbir değişiklik istemez. Aurora aynı esnekliği JSONB kolonuyla verir ama ilişkileri table olarak tutar: bir varyant foreign key ile tam olarak bir ürüne bağlıdır, fiyat kuralı CHECK ile database'de korunur ve \"stoğu biten varyantların ürünleri\" bir JOIN'dir. "
                      "Bu iş yükünde ilişkisel seçilir, çünkü katalog ilişkilerle doludur (marka, kategori, varyant, fiyat, depo) ve bu ilişkilerin doğruluğunu database'in korumasını istiyoruz; esnek özellikler JSONB'ye sığar. İki puanlık fark bir karar değildir; ekip MongoDB biliyorsa DocumentDB de savunulabilir. "
                      "Hangi koşul değişseydi DocumentDB seçilirdi: ürün gerçekten ilişkisiz tek bir belge olsaydı, özelliklerin şekli her ay köklü değişseydi ya da ekip MongoDB API'sini zaten biliyor ve bir DocumentDB cluster'ı işletiyor olsaydı."),
            "os": _t("Search engine (OpenSearch) ile kafa kafaya. Ayrıştığı gereksinimler R1'in kural kısmı, R3 ve R4. OpenSearch'ün gücü filtre ve facet'tedir: \"42 numara, kırmızı, su geçirmez\" sorusunu milisaniyede cevaplar ve metin aramasını, yazım hatası toleransını da verir. "
                      "Ama bir arama index'i resmi kayıt değildir: ilişkiler index'e yazılırken düzleştirilir, marka adı değişince bütün ürün dokümanları yeniden yazılır, transaction ve foreign key yoktur ve mapping değişince index baştan kurulur. "
                      "Bu yüzden bu iki servis birbirinin alternatifi değil tamamlayıcısıdır: katalog ilişkileriyle Aurora'da yaşar, arama kopyası OpenSearch'e akar. Bu iş yükünde ilişkisel seçilir, çünkü kayıt sistemi istenir ve metin araması zaten ayrı bir servise verilecektir. "
                      "Hangi koşul değişseydi OpenSearch seçilirdi: katalog başka bir sistemde zaten kalıcı olsaydı ve buradaki iş sadece facet'li arama ve relevance olsaydı; o zaman OpenSearch tek başına seçilir ve kaynak kayıt oradan beslenir."),
        },
        verdict=_t("Karar: Aurora 44, DocumentDB 42, OpenSearch 32. Yakın bir yarış: iki aday da R2 ve R3'ü karşılar; yarışı R1'in kural kısmı belirler: ilişkilerin doğruluğunu database koruyor mu, uygulama mı. "
                   "Yine de ilişkisel seçersek artımız: varyant ve fiyat kuralları database'de, yeni özellikler JSONB'de migration'sız, her yeni soru bir SQL, arama servisi zero-ETL ya da CDC ile beslenir. "
                   "Potansiyel eksimiz: JSONB içi filtreler GIN index ve özel operatör ister; her yeni ilişki bir migration'dır; metin araması ve facet için OpenSearch ayrıca gerekir. Bir koşul değişseydi: ürün ilişkisiz tek bir belge olsaydı ve ekip MongoDB biliyor olsaydı DocumentDB kazanırdı.")),

    # ------------------------------------------------------------------ 3. inventory with reservations (card only)
    usecase("inventory", 3,
        title=_t("Depo bazlı stok ve rezervasyon"),
        key=_t("Table'lar: stock (sku, warehouse, on_hand, reserved), reservations (sku, warehouse, qty, expires_at)."),
        story=_t("Bir mağazanın üç deposu ve 20.000 ürünü var. Checkout başlarken ürün 15 dakika rezerve edilir; ödeme gelmezse rezervasyon düşer ve stok serbest kalır. "
                 "Kural: bir depoda kullanılabilir stok = eldeki stok - rezerve edilen, ve bu değer hiçbir zaman sıfırın altına inmez. Kampanya anında saniyede 300 rezervasyon denemesi olur ve bunların yarısı aynı on ürüne gider. "
                 "Depo ekibi her sabah \"depo başına eşiğin altındaki ürünler\" raporunu ister ve rezervasyonların süresi dolduğunda stok kendiliğinden geri dönmelidir. Stok muhasebenin resmi kaydıdır; bir rezervasyonun kaybı fazla satıştır. Ekipte dört geliştirici var, SQL biliyor."),
        reqs=[
            req(True, "\"Bu depoda bu üründen 2 adet rezerve et, ama kullanılabilir stok 2'nin altındaysa reddet\" tek adımda ve atomik olmalı; rezervasyon kaydı ile stok sayacı birlikte değişmeli. Süresi dolan rezervasyon stoğu geri vermeli. Depo başına eşik raporu tek sorgu olmalı.",
                      "Rezervasyon yazılıp sayaç artmazsa aynı adet iki kişiye satılır; sayaç artıp rezervasyon yazılmazsa stok sonsuza kadar kilitli kalır. Rapor birçok okuma istiyorsa depo ekibi her sabah bekler."),
            req(True, "Kampanya anında saniyede 300 rezervasyon, yarısı aynı on ürüne; normalde saniyede 10. Her rezervasyon 100 ms'nin altında onaylanmalı.",
                      "Aynı on ürün aynı satırlara gider: bu satırlar bir kuyruk olur. Kuyruk uzarsa checkout yavaşlar ve müşteri düğmeye tekrar basar."),
            req(True, "Stok ve rezervasyon muhasebenin kaydıdır; AZ arızasında kayıp olmamalı. Bu kartta zorunlu.",
                       "Kaybolan rezervasyon fazla satıştır; kaybolan stok sayacı envanter sayımıdır."),
            req(False, "Dört geliştirici, SQL biliyor. Süresi dolan rezervasyonlar için ayrı bir temizlik işi istenmiyor ama kabul edilir. Sunucu boyutlandırma istenmiyor.",
                       "Temizlik işi gecikirse stok boşken satılamaz; erken çalışırsa ödeme sırasındaki rezervasyon düşer."),
            req(False, "Trafik çoğunlukla düz, kampanya anları kısa. Kapasite başına ödeme kabul.",
                       "Kısa tepe için büyütülen kapasite ayın geri kalanında boş durur."),
        ],
        cands=["aur", "ddb", "ec"],
        scores={
            "aur": [sc(10, "UPDATE stock SET reserved = reserved + 2 WHERE sku = ... AND warehouse = ... AND on_hand - reserved >= 2 ve INSERT reservations aynı transaction'dadır (Ö5); koşul row lock altında test edilir ve iki istek yarışsa ikincisi yeni değeri görür. CHECK (reserved <= on_hand) kuralı database'de durur (Ö1). Eşik raporu GROUP BY ile tek sorgudur (Ö3). Puan kırılmadı."),
                    sc(8, "Saniyede 300 kısa transaction tek writer için küçüktür. 2 puan kırıldı: aynı on ürünün satırları tek writer'da birbirini bekler; row başına saniyede 15 kısa UPDATE tek başına sorun değildir (bir UPDATE milisaniyenin altındadır, B2), risk aynı row'u ödeme boyunca kilitli tutan uzun transaction'lardır ve minimum ACU kampanya öncesi yükseltilmelidir; bu bir tahmindir, ölçüm değil."),
                    sc(10, "Altı kopya, üç AZ, point-in-time restore. Puan kırılmadı."),
                    sc(8, "Yönetilen yedek ve failover; ekip SQL biliyor. 2 puan kırıldı: süresi dolan rezervasyon için zamanlanmış bir temizlik işi yazılır (PostgreSQL'de bir row'a \"şu saatte kendini sil\" denemez; DynamoDB'deki TTL bunu yapar) ve ACU aralığı ekibin kararıdır."),
                    sc(8, "ACU-saat. 2 puan kırıldı: kampanya için yükseltilen minimum ACU unutulursa ay boyu ödenir; Aurora Standard'da I/O isteği başına ücret vardır.")],
            "ddb": [sc(6, "Depo + ürün bir item; ConditionExpression \"on_hand - reserved >= :q\" ile atomik rezervasyon tek item'da korunur ve rezervasyon kaydı TransactWriteItems ile aynı anda yazılır. 4 puan kırıldı: transaction iki kat birim tüketir; \"depo başına eşiğin altındaki ürünler\" raporu ya bir GSI ya da bütün table'ın okunmasıdır; rezervasyon ve sayaç iki ayrı item olduğu için ikisi birden ancak transaction ile tutarlı kalır."),
                    sc(10, "On-demand mod 300 isteği tek haneli milisaniyede karşılar; aynı on ürün on ayrı item'dır ve partition sınırının çok altındadır. Puan kırılmadı."),
                    sc(10, "Birkaç AZ'de saklanır, point-in-time recovery. Puan kırılmadı."),
                    sc(8, "Serverless; TTL süresi dolan rezervasyonu siler. 2 puan kırıldı: TTL silmesi genellikle birkaç gün içinde olur, bu yüzden sayacı geri veren mantık Streams ile ayrıca yazılır ve ekip key tasarımını öğrenir."),
                    sc(9, "İstek başına; boş günlerde sıfıra yakın. 1 puan kırıldı: transactional yazmalar iki kat birimdir.")],
            "ec": [sc(6, "DECRBY ile atomik sayaç ve SET NX EX 900 ile tam süreli rezervasyon tek komuttur. 4 puan kırıldı: sayaç ve rezervasyon iki ayrı key'dir, ikisini birden tutarlı değiştirmek Lua script'i ister; eşik raporu için bütün key'ler taranır."),
                   sc(10, "Bellekten mikrosaniye; Serverless ölçeklenir. Puan kırılmadı."),
                   sc(3, "Serverless replica'ları birkaç AZ'de tutar ama her yazmayı diske yazan dayanıklı bir log yoktur; bir arıza son rezervasyonları ve sayaçları kaybedebilir. 7 puan kırıldı: bu kartta kayıp fazla satıştır ve dayanıklılık zorunludur."),
                   sc(8, "Serverless; EXPIRE temizlik işini gereksiz kılar. 2 puan kırıldı: Lua script'i ekibin bakımına girer."),
                   sc(8, "ECPU ve GB-saat. 2 puan kırıldı: bellek GB başına diskten pahalıdır; stok verisi küçük olduğu için fark küçüktür.")],
        },
        h2h={
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinimler R1'in rapor ve süre sonu kısmı ile R2. DynamoDB'nin gücü tepe anındadır: 300 rezervasyon on ayrı item'a dağılır, kimse kapasite ayarlamaz ve koşullu yazma tek item'da atomiktir. "
                      "Aurora'nın gücü kuralın bütünlüğündedir: sayaç ve rezervasyon aynı transaction'da değişir, kullanılabilir stok kuralı CHECK ile database'de durur ve depo başına eşik raporu bir GROUP BY'dır; DynamoDB'de rapor bir GSI ya da tam okuma, süresi dolan rezervasyonun sayacı geri vermesi ise ayrı bir Streams tüketicisidir. "
                      "Bu iş yükünde ilişkisel seçilir, çünkü stok muhasebenin kaydıdır, kurallar iki table'ı birden kapsar ve rapor her sabah sorulur; tepe anındaki satır kuyruğu minimum ACU ile yönetilebilir. "
                      "Hangi koşul değişseydi DynamoDB seçilirdi: rezervasyon hacmi saniyede on binlere çıksaydı, rapor ayrı bir analitik kopyadan sorulsaydı ve süresi dolan rezervasyonun stoğu geri vermesi için zaten bir Streams tüketicisi olsaydı."),
            "ec": _t("Bellek içi key-value (ElastiCache) ile kafa kafaya. Ayrıştığı gereksinim R3 dayanıklılık ve bu kartta zorunludur. ElastiCache'in gücü tam süreli rezervasyondur: SET NX EX 900 ile rezervasyon tam olarak 15 dakika sonra yok olur, temizlik işi gerekmez ve DECRBY sayaçları mikrosaniyede değiştirir. "
                      "Ama her yazmayı diske yazan dayanıklı bir log yoktur; bir arıza son rezervasyonları kaybeder ve kaybolan her rezervasyon fazla satıştır. Sayaç ve rezervasyon iki ayrı key olduğu için ikisini tutarlı değiştirmek de bir Lua script'i ister. "
                      "Bu yüzden bu iş yükünde kalıcı kayıt ilişkisel database'de tutulur; ElastiCache en fazla rezervasyon süresi için bir yardımcı olabilir. Hangi koşul değişseydi ElastiCache seçilirdi: rezervasyon başka bir yerde kalıcı olsaydı ve buradaki kopya sadece hızlı bir kilit ve sayaç olsaydı ya da dayanıklı log istenseydi ve bellek içi hız şart olsaydı (o zaman MemoryDB)."),
        },
        verdict=_t("Karar: Aurora 44, DynamoDB 43, ElastiCache 35. Yakın bir yarış ve kararı R1'in bütünlük kısmı verir: sayaç, rezervasyon ve rapor aynı database'de, aynı transaction'da. "
                   "Yine de ilişkisel seçersek artımız: kullanılabilir stok kuralı database'de, rezervasyon ve sayaç tek transaction'da, eşik raporu tek sorgu, stok altı kopyayla kalıcı. "
                   "Potansiyel eksimiz: kampanya ürününün satırı tek writer'da bir kuyruk olur ve minimum ACU önceden yükseltilir; süresi dolan rezervasyonlar için zamanlanmış bir temizlik işi yazılır (temizlik DELETE ... WHERE expires_at < now() ile onay UPDATE ... WHERE expires_at >= now() aynı row lock sırasına girer; biri kazanır, diğeri yeni değeri görür). Bir koşul değişseydi: rezervasyon hacmi saniyede on binlere çıksaydı DynamoDB kazanırdı; ekip DynamoDB'yi SQL kadar iyi bilseydi R4 eşitlenir ve bu bir puanlık yarış tersine dönebilirdi.")),

    # ------------------------------------------------------------------ 4. customer accounts and addresses (card only)
    usecase("accounts", 4,
        title=_t("Müşteri hesapları, adresler ve izinler"),
        key=_t("Table'lar: customers, addresses, payment_methods, consents. E-posta benzersiz, adres müşteriye bağlı."),
        story=_t("Bir perakende uygulamasının iki milyon müşterisi var. Her müşterinin birkaç adresi, birkaç ödeme yöntemi ve pazarlama izinleri (KVKK) vardır. Login saniyede 500 kez hesabı okur; hesap değişikliği saniyede 20'dir. "
                 "Kurallar: bir e-posta tam olarak bir hesaba aittir; bir adres var olmayan bir müşteriye ait olamaz; \"verimi sil\" isteği müşteriyi, adreslerini, ödeme yöntemlerini ve izinlerini birlikte ve eksiksiz siler. "
                 "Hukuk ekibi her çeyrek yeni bir izin türü tanımlar. Siparişler aynı database'te durur ve müşteriye bağlıdır. Ekipte beş geliştirici var, SQL biliyor; hesap verisinin kaybı güven kaybıdır ve kabul edilmez."),
        reqs=[
            req(True, "Hesabı id ve e-posta ile okuma; e-posta benzersizliği yazma anında korunmalı; adres ve ödeme yöntemi var olan bir müşteriye bağlı olmalı; \"verimi sil\" bütün ilgili kayıtları ya hep ya hiç silmeli. Sorular: \"bu müşterinin adresleri ve son siparişleri\", \"izni geri çeken müşteriler\".",
                      "Aynı e-postayla iki hesap, şifre sıfırlamada yanlış kişiye e-posta demektir. Yarım kalan bir silme, hukuki yükümlülüğün ihlalidir."),
            req(True, "Saniyede 500 hesap okuması ve 20 yazma; sabah ve akşam tepe. Her okuma 20 ms'nin altında. Müşteri sayısı yılda yüzde 30 büyüyor.",
                      "Login her oturumun ilk adımıdır; yavaşsa her şey yavaştır. Büyüme için her yıl yeniden tasarım yapılamaz."),
            req(True, "Hesap verisi kalıcıdır; AZ arızasında kayıp olmamalı; yanlış bir silme geri alınabilmeli. Bu kartta zorunlu.",
                       "Kaybolan hesap kaybolan müşteridir; adresini ve kartını yeniden giren müşteri güvenini kaybeder."),
            req(False, "Beş geliştirici, SQL biliyor. Çeyrekte bir yeni izin türü kesintisiz eklenebilmeli. Sunucu boyutlandırma ve yama istenmiyor.",
                       "Her çeyrek bir bakım penceresi hukuk ekibinin takvimini database ekibine bağlar."),
            req(False, "Düz ve okuma ağırlıklı trafik; kapasite başına ödeme uyar. Veri küçük (birkaç GB).",
                       "Düz trafikte kapasite başına ödeme öngörülebilirdir; önemli olan büyümede sıçrama olmamasıdır."),
        ],
        cands=["aur", "ddb", "doc"],
        scores={
            "aur": [sc(10, "UNIQUE (email) e-posta kuralını yazma anında korur (Ö1); addresses.customer_id REFERENCES customers ON DELETE CASCADE adresi var olan bir müşteriye bağlar ve \"verimi sil\" tek DELETE ile adresleri, ödeme yöntemlerini ve izinleri siler; siparişler muhasebe için kalır: orders.customer_id ON DELETE SET NULL ile müşterisiz kalır ve aynı transaction'da anonimleştirilir (Ö2, Ö5). \"Adresleri ve son siparişleri\" bir JOIN'dir (Ö3); \"izni geri çekenler\" bir WHERE'dir. Yeni izin türü consents table'ına yeni bir row türü olarak girer. Puan kırılmadı."),
                    sc(9, "500 okuma primary key ve e-posta index'i ile aramadır (Ö4); reader instance'lar okumayı taşır (Ö7). 1 puan kırıldı: reader sayısı ve ACU aralığı ekibin kararıdır."),
                    sc(10, "Altı kopya, point-in-time restore yanlış silmeyi geri alır. Puan kırılmadı."),
                    sc(8, "Yönetilen yedek, yama, failover; SQL ekibin dili. 2 puan kırıldı: yeni bir alan (izin türü değil, izin alanı) ALTER TABLE ister ve migration aracı disiplinle kullanılmalıdır."),
                    sc(8, "ACU-saat ya da instance-saat, düz trafikte öngörülebilir. 2 puan kırıldı: gece düşük trafikte de minimum kapasite ödenir.")],
            "ddb": [sc(6, "Hesap kullanıcı id'siyle tek item, adresler ve izinler aynı partition'da sort key ile. 4 puan kırıldı: e-posta benzersizliği ikinci bir item ve bir transaction ister; \"verimi sil\" aynı partition'daki item'ları TransactWriteItems ile (100'e kadar) birlikte siler ama siparişler gibi başka table'lardaki bağlı kayıtları database bilmez, uygulama bulur; \"adresleri ve son siparişleri\" iki table'dan iki okumadır; \"izni geri çekenler\" bir GSI ya da tam okumadır."),
                    sc(10, "Okumalar partition'lara dağılır; büyüme için hiçbir şey değişmez. Puan kırılmadı."),
                    sc(10, "Birkaç AZ, point-in-time recovery. Puan kırılmadı."),
                    sc(8, "Serverless; yeni izin türü yeni bir value. 2 puan kırıldı: benzersizlik deseni ve GSI bakımı ekibin öğreneceği tasarımlardır."),
                    sc(9, "İstek başına; düz trafikte provisioned + auto scaling. 1 puan kırıldı: GSI yazmaları ayrıca ödenir.")],
            "doc": [sc(8, "Müşteri bir document, adresler ve izinler içinde dizi; unique index ile e-posta benzersizdir; \"verimi sil\" tek deleteOne'dır. 2 puan kırıldı: ödeme yöntemleri ve siparişler ayrı collection'larda ise aralarındaki bağ uygulama tarafından kontrol edilir; \"adresleri ve son siparişleri\" $lookup ister."),
                    sc(9, "Okumalar replica'lara dağılır. 1 puan kırıldı: instance sınıfı önceden seçilir."),
                    sc(10, "Altı kopya, sürekli yedek. Puan kırılmadı."),
                    sc(7, "Şema serbest; yedek ve yama yönetilir. 3 puan kırıldı: MongoDB API'si bu ekip için yenidir ve instance boyutlandırma ekibin işidir."),
                    sc(7, "Instance saat başına. 3 puan kırıldı: Multi-AZ için birkaç instance gece de çalışır.")],
        },
        h2h={
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinim R1'in kural ve ilişki kısmı. DynamoDB'nin gücü R2 ve R5'te: 500 okuma ve yılda yüzde 30 büyüme için hiçbir şey yapılmaz, istek başına ödenir. "
                      "Aurora'nın gücü kuralların yerindedir: e-posta benzersizliği bir UNIQUE constraint'tir, adresin sahibi bir foreign key'dir ve \"verimi sil\" ON DELETE CASCADE ile tek bir DELETE'tir; DynamoDB'de benzersizlik bir transaction deseni, silme bir okuma ve item item silme, \"izni geri çekenler\" ise bir GSI'dır. "
                      "Siparişler de aynı database'te müşteriye bağlı olduğu için \"adresleri ve son siparişleri\" tek JOIN'dir. Bu iş yükünde ilişkisel seçilir, çünkü hesap, adres, ödeme yöntemi ve sipariş birbirine bağlı kayıtlardır ve hukuki silme kuralı eksiksiz olmak zorundadır. "
                      "Hangi koşul değişseydi DynamoDB seçilirdi: hesap tek başına okunup yazılan, ilişkisi olmayan bir profil olsaydı, okuma hacmi saniyede on binlere çıksaydı ve siparişler zaten başka bir sistemde olsaydı."),
            "doc": _t("Document (DocumentDB) ile kafa kafaya. Ayrıştığı gereksinimler R1'in ilişki kısmı, R4 ve R5. DocumentDB'nin gücü hesabın şeklidir: müşteri, adresleri ve izinleriyle tek bir document'tır, tek okumayla gelir, unique index e-postayı korur ve \"verimi sil\" tek bir silmedir. "
                      "Fark siparişlerde ve ödeme yöntemlerinde başlar: bunlar ayrı collection'lardır ve aralarındaki bağı database kontrol etmez; \"adresleri ve son siparişleri\" bir $lookup'tır ve ekip MongoDB API'sini bilmez. Aurora'da bu bağlar foreign key, soru bir JOIN'dir. "
                      "Bu iş yükünde ilişkisel seçilir, çünkü hesap tek başına değil, siparişleriyle birlikte yaşar ve ekip SQL biliyor. Hangi koşul değişseydi DocumentDB seçilirdi: hesap, siparişlerden bağımsız bir profil servisi olsaydı, profilin şekli sık ve köklü değişseydi ve ekip MongoDB'yi zaten biliyor olsaydı."),
        },
        verdict=_t("Karar: Aurora 45, DynamoDB 43, DocumentDB 41. Üç aday da R2 ve R3'ü karşılar; yarışı R1'in kural ve ilişki kısmı belirler: benzersizlik, sahiplik ve eksiksiz silme database'de mi, uygulamada mı. "
                   "Yine de ilişkisel seçersek artımız: e-posta benzersizliği ve adres sahipliği database'de, hukuki silme tek DELETE, siparişlerle JOIN, hesap altı kopyayla kalıcı. "
                   "Potansiyel eksimiz: yeni bir izin alanı ALTER TABLE ister; okuma hacmi on binlere çıkarsa reader filosu büyütülür; gece minimum kapasite ödenir. Bir koşul değişseydi: hesap ilişkisiz bir profil olsaydı ve okuma hacmi on katına çıksaydı DynamoDB kazanırdı; ekip DynamoDB'yi SQL kadar iyi bilseydi iki puanlık fark kapanırdı.")),

    # ------------------------------------------------------------------ 5. multi-tenant SaaS with row-level security (card only)
    usecase("tenant", 5,
        title=_t("Çok kiracılı SaaS: row-level security ile tenant ayrımı"),
        key=_t("Her table'da tenant_id kolonu. Policy: bir session sadece kendi tenant_id'sinin row'larını görür."),
        story=_t("Bir faturalama SaaS'ı 800 şirkete hizmet veriyor; hepsi aynı database'i paylaşıyor ve her row bir tenant_id taşıyor. En büyük kural: uygulamada bir bug olsa bile A şirketi B şirketinin faturalarını asla görmemeli. "
                 "Saniyede 2.000 okuma ve 100 yazma; mesai saatlerinde tepe. Fatura verisi bugün 200 GB. Her gece her şirket için bir dışa aktarma çalışır. Yeni bir şirket açılışı bir kayıt eklemektir, yeni bir database değil. "
                 "Faturalar müşterilere, kalemlere ve ödemelere bağlıdır; raporlar şirket başına aylık toplamları ister. Ekipte altı geliştirici ve bir operasyon mühendisi var; ekip PostgreSQL biliyor. Fatura verisi resmi kayıttır."),
        reqs=[
            req(True, "Her sorgu, uygulama kodu unutmuş olsa bile, sadece o session'ın tenant'ının row'larını görmeli ve değiştirmeli. Fatura, kalem, müşteri ve ödeme ilişkileri korunmalı; aylık toplamlar tenant başına tek sorgu olmalı.",
                      "Bir WHERE tenant_id = ... unutulduğunda B şirketinin faturaları A'nın ekranında belirir; bu sözleşme ihlali ve itibar kaybıdır."),
            req(True, "Saniyede 2.000 okuma ve 100 yazma, mesai saatlerinde tepe. Her okuma 30 ms'nin altında. 800 tenant 3.000 tenant'a çıkacak; gürültülü bir tenant diğerlerini yavaşlatmamalı.",
                      "Tek bir büyük tenant'ın gece dışa aktarması diğerlerinin sabah işini yavaşlatırsa 799 şirket şikâyet eder."),
            req(True, "Fatura resmi kayıttır; AZ arızasında kayıp olmamalı. Bu kartta zorunlu.",
                       "Kaybolan fatura, hem müşterinin hem vergi dairesinin kaydıdır."),
            req(False, "Altı geliştirici, bir operasyon mühendisi, PostgreSQL biliyor. Yeni tenant için sunucu ya da database kurulmamalı. Yama, yedek ve failover istenmiyor.",
                       "Tenant başına database kurmak 800 bakım işi demektir; bir operasyon mühendisi bunu taşıyamaz."),
            req(False, "Trafik mesai saatlerine bağlı; gece düşük ama dışa aktarma var. Kapasite başına ödeme uyar; büyümede maliyet tenant sayısıyla doğrusal artmalı.",
                       "3.000 tenant için maliyet sıçrarsa fiyat modeli bozulur."),
        ],
        cands=["aur", "rds", "ddb"],
        scores={
            "aur": [sc(10, "ALTER TABLE invoices ENABLE ROW LEVEL SECURITY ve CREATE POLICY ... USING (tenant_id = current_setting('app.tenant')::int) ile database her sorguya tenant filtresini kendisi ekler; uygulama unutsa da başka tenant'ın row'u dönmez (Ö8, row-level security). Foreign key'ler ilişkileri korur (Ö2), aylık toplamlar GROUP BY'dır (Ö3). Puan kırılmadı."),
                    sc(9, "2.000 okuma index aramalarıdır (Ö4); reader instance'lar okumayı ve gece dışa aktarmalarını writer'dan ayırır (Ö7); Serverless v2 mesai saatinde büyür. 1 puan kırıldı: bütün tenant'lar tek writer'ı paylaşır, gürültülü tenant için uygulama tarafında kota gerekir."),
                    sc(10, "Üç AZ'de altı kopya, failover genellikle 60 saniyenin altında, point-in-time restore. Puan kırılmadı."),
                    sc(9, "Yönetilen yedek, yama, failover ve storage; yeni tenant bir INSERT. 1 puan kırıldı: policy'ler her role için test edilmelidir ve table sahibi policy'yi atlar; bu, uygulamanın sahip olmayan bir role ile bağlanmasını ister."),
                    sc(8, "ACU-saat; gece düşük kapasiteye iner. 2 puan kırıldı: minimum kapasite ve reader instance gece de ödenir; I/O isteği başına ücret Standard yapılandırmada eklenir.")],
            "rds": [sc(10, "Aynı PostgreSQL: row-level security, foreign key ve GROUP BY birebir aynıdır. Puan kırılmadı."),
                    sc(7, "2.000 okuma bir instance ve read replica'larla karşılanır. 3 puan kırıldı: her read replica database'in tam bir kopyasıdır ve kurulması saatler sürer; storage ve IOPS önceden boyutlandırılır; 3.000 tenant için instance sınıfı büyütülür."),
                    sc(8, "Multi-AZ dağıtımında başka bir AZ'de senkron bir standby kopya vardır ve AWS failover süresini genellikle 60 ile 120 saniye olarak verir. 2 puan kırıldı: tek bir standby kopya, Aurora'nın altı kopyasından daha az yedeklidir ve failover daha uzundur."),
                    sc(8, "Yönetilen yedek ve yama; PostgreSQL ekibin bildiği engine. 2 puan kırıldı: storage boyutu, IOPS ve instance sınıfı ekibin kararıdır, 200 GB'lık replica kurulumu uzundur ve policy'ler burada da her role için test edilir."),
                    sc(9, "Instance-saat ve GB-ay. 1 puan kırıldı: mesai dışında da aynı instance ödenir; küçük ve düz yükte Aurora'dan ucuz olabilir, 3.000 tenant'ta bir sınıf atlamak maliyeti sıçratır.")],
            "ddb": [sc(4, "Partition key tenant_id ile her tenant'ın verisi bir arada durur ve IAM policy'sinde dynamodb:LeadingKeys koşulu bir tenant'ı kendi partition key'iyle sınırlar. 6 puan kırıldı: fatura, kalem, müşteri ve ödeme arasındaki ilişkileri database korumaz; aylık toplam bir GROUP BY değil, bütün fatura item'larının okunmasıdır; her yeni rapor sorusu bir key tasarımıdır."),
                    sc(10, "Okumalar partition'lara dağılır; gürültülü tenant kendi partition'larında kalır. Puan kırılmadı."),
                    sc(10, "Birkaç AZ, point-in-time recovery. Puan kırılmadı."),
                    sc(7, "Serverless; yeni tenant yeni bir key. 3 puan kırıldı: ekip PostgreSQL biliyor; fatura toplamları ve dışa aktarma için ayrı bir analitik yol kurulur."),
                    sc(8, "İstek başına. 2 puan kırıldı: her gece 800 tenant'ın tam okuması okuma birimi olarak ödenir.")],
        },
        h2h={
            "rds": _t("İlişkisel (RDS for PostgreSQL) ile kafa kafaya. Bu, aynı kategorinin ve aynı engine'in iki yönetilen biçimi arasındaki yarıştır: row-level security, foreign key ve SQL ikisinde de birebir aynıdır. Ayrıştığı gereksinimler R2 ve R3. "
                      "RDS'in gücü sadeliği ve küçük yükte fiyatıdır: tek bir instance, bildiğin community PostgreSQL, instance-saat olarak öngörülebilir fatura. Aurora'nın gücü storage katmanındadır: veri üç AZ'de altı kopyadır, yeni bir reader dakikalar içinde aynı paylaşılan storage'a bağlanır (kopya alınmaz), failover genellikle 60 saniyenin altındadır ve Serverless v2 mesai saatinde büyüyüp gece küçülür. "
                      "Bu iş yükünde Aurora seçilir, çünkü 800 tenant tek writer'ı paylaşır ve okuma ölçeği reader'larla, dayanıklılık altı kopyayla, mesai dalgası ACU ile karşılanır; RDS'te her reader tam bir kopyadır ve standby tektir. "
                      "Hangi koşul değişseydi RDS seçilirdi: yük küçük ve düz olsaydı (saniyede yüz okuma), tek bir instance yetseydi, ekip belirli bir community sürümüne ya da extension'a ihtiyaç duysaydı ya da maliyetin en küçük olması her şeyden önemli olsaydı."),
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinim R1: ilişkiler ve toplamlar. DynamoDB'nin tenant ayrımı gerçektir: partition key tenant_id ve IAM'de LeadingKeys koşulu, bir tenant'ın başka partition'ı okumasını servis seviyesinde engeller; bu, row-level security'nin key-value karşılığıdır ve R2'de de kimse boyutlandırmaz. "
                      "Ama faturalama ilişkilerle doludur: fatura, kalem, müşteri, ödeme ve aylık toplamlar. Aurora'da bunlar foreign key ve GROUP BY'dır; DynamoDB'de ilişkileri uygulama korur ve toplam, tenant'ın bütün fatura item'larının okunmasıdır. "
                      "Bu iş yükünde ilişkisel seçilir, çünkü tenant ayrımı yalnız başına yetmez; faturanın doğruluğu ve raporları da database'den beklenir. Hangi koşul değişseydi DynamoDB seçilirdi: her tenant'ın verisi ilişkisiz, key ile okunan belgeler olsaydı, raporlar zero-ETL ile analitik bir kopyadan sorulsaydı ve tenant sayısı yüz binlere çıksaydı."),
        },
        verdict=_t("Karar: Aurora 46, RDS 42, DynamoDB 39. Tenant ayrımı üç adayda da mümkündür; yarışı R1'in ilişki kısmı ve R2'nin okuma ölçeği belirler. Aurora ve RDS aynı PostgreSQL'dir; fark storage ve failover modelindedir. "
                   "Yine de Aurora seçersek artımız: policy database'de uygulanır ve unutulamaz, ilişkiler ve toplamlar SQL'dir, reader'lar gece dışa aktarmalarını writer'dan ayırır, altı kopya ve kısa failover. "
                   "Potansiyel eksimiz: bütün tenant'lar tek writer'ı paylaşır ve gürültülü tenant için kota gerekir; policy'ler role bazında test edilir; gece minimum kapasite ödenir; kendi ayrı database'ini isteyen kurumsal bir tenant bu modelin dışındadır ve ayrı bir cluster alır. Bir koşul değişseydi: yük küçük ve düz olsaydı RDS for PostgreSQL daha ucuz bir seçim olurdu.")),

    # ------------------------------------------------------------------ 6. reporting over years of history (clear loss)
    usecase("reporting", 6, sim="lose_reporting", kind="lose",
        title=_t("Raporlama: son 90 günden üç yıllık geçmişe"),
        key=_t("Table'lar: orders, order_items, products, customers; üç yıl, iki milyar row. Sorular ay, şehir ve kategoriye göre toplamlar."),
        story=_t("Finans ekibi checkout database'indeki siparişler üzerinde dashboard istiyor. İlk istek \"son 90 gün, kategoriye göre gelir\" idi ve reader instance'ta saniyeler içinde çalıştı. "
                 "Şimdi gereksinim büyüdü: üç yıllık geçmiş, sipariş ve line'larda iki milyar row, 40 analist, her beş dakikada yenilenen 30 dashboard ve her hafta yeni bir soru: \"şehre, kampanyaya ve cihaz tipine göre iade oranı\". "
                 "Her sorgu geçmişin tamamını tarar ama her row'un sadece üç dört kolonunu okur. Sorgular 10 saniyede dönmeli ve checkout'u yavaşlatmamalı. Veri checkout'tan saniyeler içinde gelmeli. Veri ekibi iki kişi, analistler SQL biliyor; dashboard verisi bir kopyadır, kaynak checkout'tadır."),
        reqs=[
            req(True, "JOIN ve GROUP BY içeren serbest SQL; her hafta yeni bir soru; cevap 10 saniyenin altında. Analistler kolon adlarını bilir, key tasarımı istemez.",
                      "10 saniyeyi aşan dashboard kullanılmaz; her yeni soru için bir mühendis gerekirse finans ekibi beklemeye başlar."),
            req(True, "İki milyar row üzerinde, her sorguda geçmişin tamamını tarayan ama sadece birkaç kolon okuyan 30 eşzamanlı sorgu. Checkout database'i bu taramaları hissetmemeli.",
                      "Tam row'ları okuyan bir tarama iki milyar row'da yüzlerce GB okur; 30 sorgu aynı anda bunu yaparsa disk ve bellek checkout'tan çalınır."),
            req(False, "Veri bir kopyadır; kaybı kaynaktan yeniden yükleme demektir. Yine de günlük yedek istenir.",
                       "Kopya kaybolursa dashboard'lar bir gün kapanır; para kaybolmaz."),
            req(False, "İki kişilik veri ekibi; analistler SQL biliyor. Kopyayı güncel tutan boru hattı kod istemeden kurulabilmeli.",
                       "Elle yazılan bir boru hattı iki kişilik ekibin bütün zamanını alır ve bir hafta sonra eskir."),
            req(False, "Analistler mesai saatinde çalışır; kullanım kadar ödeme istenir, 7/24 çalışan bir filo istenmez. Veri büyük (yüzlerce GB).",
                       "7/24 çalışan reader filosu gece boş durur ve ödenir; yüzlerce GB için GB başına fiyat belirleyicidir."),
        ],
        cands=["aur", "rs", "os"],
        scores={
            "aur": [sc(7, "SQL, JOIN ve GROUP BY tam olarak vardır (Ö3) ve her yeni soru bir cümledir. 3 puan kırıldı: row storage her row'un tamamını okur; iki milyar row'da 10 saniye sınırı index ve partition ile de garanti değildir ve çoğu soru için önceden hesaplanmış özet table'lar yazılır."),
                    sc(4, "Taramalar reader instance'a yönlendirilir (Ö7), writer'ı taşımaz ve SQL değişmez. 6 puan kırıldı: 30 eşzamanlı tam tarama için birkaç büyük reader gerekir; her tarama sadece üç kolon için tam page'leri okur; replica gecikmesi büyük taramalarda artar ve aynı paylaşılan storage'ın I/O'su paylaşılır."),
                    sc(10, "Altı kopya, sürekli yedek. Puan kırılmadı."),
                    sc(7, "Yönetilen; kopya zaten checkout'un kendisidir, boru hattı gerekmez. 3 puan kırıldı: özet table'lar, partition bakımı ve vacuum iki kişilik ekibin işidir; ikinci bir reader filosu yönetilir."),
                    sc(4, "ACU-saat. 6 puan kırıldı: 30 eşzamanlı tarama için büyük reader'lar mesai saatinde çalışır, yüzlerce GB row storage'da index'lerle birlikte katlanır ve Standard'da her tarama I/O olarak ödenir.")],
            "rs": [sc(10, "SQL, JOIN, GROUP BY ve window fonksiyonları; analistler aynı SQL'i yazar. Puan kırılmadı."),
                   sc(10, "Column storage sadece sorulan kolonları okur, MPP taramayı node'lara böler; zero-ETL ile veri checkout'tan ayrı bir sistemde durur ve Aurora taramayı hissetmez. Puan kırılmadı."),
                   sc(9, "Yönetilen storage dayanıklıdır, snapshot alınır. 1 puan kırıldı: veri bir kopyadır ve zero-ETL yeniden tohumlama ister."),
                   sc(8, "Aurora'dan Redshift'e zero-ETL entegrasyonu veriyi yazıldıktan saniyeler içinde kopyalar, boru hattı kodu yoktur. 2 puan kırıldı: kaynak table'larda primary key şarttır; sort key, distribution key ve workload yönetimi ekibin kararıdır."),
                   sc(8, "Serverless RPU-saat: analist çalışmayınca ödeme düşer. 2 puan kırıldı: taban kapasite ve veri kopyasının storage'ı ayrıca ödenir.")],
            "os": [sc(4, "Aggregation'lar toplamları verir ve dashboard araçları bağlanır. 6 puan kırıldı: finans soruları JOIN ister ve JOIN yoktur, veri index'e yazılırken düzleştirilir; SQL desteği sınırlıdır ve her yeni soru mapping'e bağlıdır."),
                   sc(8, "Shard'lara dağılmış aggregation'lar hızlıdır. 2 puan kırıldı: shard sayısı ve node sınıfı önceden seçilir; iki milyar doküman için bellek büyük olmalıdır."),
                   sc(8, "Replica shard'lar ve snapshot. 2 puan kırıldı: kopya; mapping değişince reindex."),
                   sc(5, "Yönetilen domain. 5 puan kırıldı: Aurora'dan OpenSearch'e akış için CDC araçları ve düzleştirme mantığı kurulur; mapping ve reindex ekibin işidir."),
                   sc(6, "Node saat başına, 7/24. 4 puan kırıldı: analistlerin boş saatlerinde de node'lar çalışır.")],
        },
        h2h={
            "rs": _t("Data warehouse (Redshift) ile kafa kafaya. Ayrıştığı gereksinimler R2 ve R5, ve ikisi de Redshift lehinedir. Redshift'in gücü storage biçimindedir: kolonları ayrı ayrı saklar, \"kategoriye göre gelir\" sorusu için sadece üç kolonu okur ve taramayı node'lara böler; Aurora her row'un tamamını page page okur ve iki milyar row'da bu yüzlerce GB'dır. "
                      "Aurora'nın gücü SQL'in aynısını vermesi ve verinin zaten orada olmasıdır; ilk istekteki \"son 90 gün\" sorusu reader'da gerçekten yeterliydi. Ama gereksinim üç yıl, 30 eşzamanlı tarama ve 10 saniye olunca ilişkisel database ya özet table'larla ya da büyük bir reader filosuyla cevap verir ve bu, checkout database'ini bir analitik sisteme dönüştürmektir. "
                      "Bu yüzden bu iş yükünde Aurora kaybeder ve doğru cevap ikisi birliktedir: Aurora kayıt sistemi olarak kalır, zero-ETL kopyayı saniyeler içinde Redshift'e taşır ve analistler orada çalışır. Hangi koşul değişseydi Aurora seçilirdi: soru gerçekten son 90 günle sınırlı kalsaydı, eşzamanlı dashboard sayısı birkaç olsaydı ve 10 saniye sınırı özet table'larla karşılanabilseydi; o zaman bir reader instance yeterdi."),
            "os": _t("Search engine (OpenSearch) ile kafa kafaya. Ayrıştığı gereksinimler R1 ve R4. OpenSearch'ün gücü aggregation'dadır: shard'lara dağılmış toplamlar ve bir dashboard aracı ile \"kategoriye göre gelir\" hızlı çizilir; log analitiği bu yüzden OpenSearch'te yaşar. "
                      "Ama finans soruları JOIN ister: sipariş, line, ürün ve müşteri dört ayrı table'dır ve OpenSearch'te JOIN yoktur; veri index'e yazılırken düzleştirilir ve her yeni soru mapping'e bağlıdır. Aurora bu soruları SQL ile cevaplar ama tarama maliyetiyle; Redshift ikisini de verir. "
                      "Bu iş yükünde OpenSearch, Aurora'nın bir puan gerisinde kalır ve ikisi farklı nedenlerle kaybeder: Aurora ölçekte, OpenSearch ilişkilerde. Hangi koşul değişseydi OpenSearch seçilirdi: veri zaten düz olaylar olsaydı (tıklama, log), sorular JOIN istemeseydi ve dashboard'ın yanında metin araması ve anomali tespiti de istenseydi."),
        },
        verdict=_t("Karar: Redshift 45, Aurora 32, OpenSearch 31. Net bir kaybetme: Aurora gerçek bir adaydır (veri oradadır, SQL aynıdır) ama R2'nin tarama ölçeği ve R5'in 7/24 reader faturası onu sona atar. Doğru cevap \"ikisi birlikte\"dir: kaynak Aurora'da, analiz Redshift'te. "
                   "Yine de Aurora seçersek artımız: boru hattı yok, veri saniye gecikmesiz, analistler aynı database'te çalışır, ilk 90 günlük soru gerçekten çalışır. "
                   "Potansiyel eksimiz: iki milyar row'luk taramalar reader'ları ve paylaşılan storage'ın I/O'sunu doldurur, 10 saniye sınırı özet table'lar ister ve bunların bakımı iki kişilik ekibin işidir, mesai saatinde büyük reader'lar ödenir. Bir koşul değişseydi: soru son 90 günle sınırlı kalsaydı Aurora'nın reader'ı yeterdi.")),

    # ------------------------------------------------------------------ 7. invoices and ledgers (race vs RDS for PostgreSQL)
    usecase("ledger", 7, sim="race_ledger", kind="race",
        title=_t("Faturalar ve çift taraflı defter"),
        key=_t("Table'lar: accounts, journal_entries, postings (debit ve credit row'ları), invoices, invoice_lines."),
        story=_t("Bir fintech, işletmeler için fatura ve muhasebe tutuyor. Her finansal olay bir journal entry'dir ve en az iki posting row'u yazar: bir borç, bir alacak; ikisinin toplamı her zaman sıfırdır. "
                 "Fatura kalemleri, vergi oranları ve ödemeler hesaplara bağlıdır. Normalde saniyede 150 posting, ay sonunda iki gün boyunca on katı. Kayıtlar yedi yıl saklanır ve denetçiler her çeyrek dışa aktarma ister. "
                 "Kural: hiçbir entry dengesiz commit edilemez, hiçbir posting var olmayan bir hesabı gösteremez, commit edilmiş bir kayıt silinmez (ters kayıt yazılır). Kayıp sıfır olmalı. Ekipte beş geliştirici var, biri PostgreSQL'i iyi biliyor."),
        reqs=[
            req(True, "Bir entry'nin bütün posting'leri ya hep ya hiç yazılmalı ve toplamı sıfır olmalı; posting var olan bir hesabı göstermeli; hesap bakiyesi her an posting'lerin toplamına eşit olmalı. Sorular: \"bu hesabın bakiyesi\", \"bu çeyreğin bütün entry'leri\", \"dengesi tutmayan entry var mı\". Yedi yıllık posting için table zamana göre partition'lara bölünür (partition: PostgreSQL'de büyük bir table'ı aya ya da yıla göre ayrı parçalarda tutmak; sorgu ve silme sadece ilgili parçaya dokunur).",
                      "Dengesiz bir entry muhasebenin kendisini bozar; denetçi bulduğunda şirket ceza alır. Bakiye ayrı bir sayaçta tutulup posting'lerle uyuşmazsa hangisi doğrudur, kimse bilmez."),
            req(True, "Saniyede 150 posting, ay sonunda iki gün 1.500. Her entry 50 ms'nin altında commit edilmeli. Yedi yılda milyarlarca posting.",
                      "Ay sonu kapanışı takvime bağlıdır; yavaşlarsa muhasebe ekibi gece kalır. Yedi yıllık veri büyür ve sorgular yavaşlamamalıdır."),
            req(True, "Sıfır kayıp: commit edilmiş posting bir AZ arızasında kaybolmamalı; yedek dakika hassasiyetinde geri yüklenebilmeli. Bu kartta zorunlu.",
                       "Kaybolan posting, kaybolan paradır ve hukuki sorumluluktur."),
            req(False, "Beş geliştirici, biri PostgreSQL uzmanı. Ay sonu için kapasite elle büyütülmek istenmiyor. Yedi yıllık arşiv için partition istenir.",
                       "Her ay sonu elle büyütme ve küçültme bir risk toplantısıdır; unutulursa ya pahalı ya yavaş olur."),
            req(False, "Trafik düz, ay sonunda on kat. Veri büyük ve büyüyor (yedi yıl). Kapasite başına ödeme kabul; ay sonu için ay boyu ödemek istenmiyor.",
                       "Ay sonuna göre boyutlandırılmış sunucu ayın 28 gününde boş durur; yedi yıllık storage GB başına ödenir."),
        ],
        cands=["aur", "rds", "ddb"],
        scores={
            "aur": [sc(10, "Entry ve posting'leri tek transaction'da yazılır (Ö5); DEFERRABLE bir constraint ya da bir trigger fonksiyonu commit anında toplamın sıfır olduğunu doğrular (Ö1, Ö6); posting.account_id REFERENCES accounts (Ö2); bakiye bir view ya da materialized view olarak posting'lerden hesaplanır (Ö6); \"dengesiz entry var mı\" bir GROUP BY HAVING'dir (Ö3). Puan kırılmadı."),
                    sc(9, "Saniyede 1.500 kısa transaction tek writer için erişilebilir; Serverless v2 ay sonunda kapasiteyi kendisi artırır. 1 puan kırıldı: maksimum ACU ay sonuna göre ayarlanmalı ve milyarlarca posting için partition tasarımı yapılmalıdır."),
                    sc(10, "Üç AZ'de altı kopya; point-in-time restore saniye hassasiyetinde. Puan kırılmadı."),
                    sc(9, "Yedek, yama, failover ve storage büyümesi yönetilir; ay sonu kapasitesi kendiliğinden gelir. 1 puan kırıldı: partition'lar ve vacuum ayarı yedi yıllık table'larda ekibin işidir."),
                    sc(7, "ACU-saat, ay sonunda artıp sonra düşer; storage GB-ay. 3 puan kırıldı: yedi yıllık defter büyüdükçe storage ve index'ler katlanır; Aurora Standard'da her posting'in I/O'su ayrıca ödenir ve ay sonu I/O'su yüksektir; I/O-Optimized seçilirse instance fiyatı artar.")],
            "rds": [sc(10, "Aynı PostgreSQL: transaction, deferrable constraint, trigger, view ve partition birebir aynıdır. Puan kırılmadı."),
                    sc(8, "1.500 posting bir instance için erişilebilir. 2 puan kırıldı: instance sınıfı ay sonuna göre seçilir ve ay boyu kalır; sınıf değişikliği yeniden başlatma ister."),
                    sc(9, "Multi-AZ dağıtımında senkron bir standby, otomatik yedek ve point-in-time restore: commit edilmiş posting kaybolmaz. 1 puan kırıldı: fark kayıp değil, kesinti süresi ve kopya sayısıdır; tek standby kopya ve AWS'in genellikle 60 ile 120 saniye verdiği failover süresi."),
                    sc(8, "Yönetilen yedek ve yama; PostgreSQL uzmanı ekip rahat eder. 2 puan kırıldı: storage boyutu ve IOPS ekibin kararıdır ve yedi yılda birkaç kez büyütülür; replica tam kopyadır."),
                    sc(8, "Instance-saat ve GB-ay; I/O ücreti yoktur ve küçük, düz yükte Aurora'dan ucuz olabilir. 2 puan kırıldı: ay sonu için büyük instance ayın geri kalanında da ödenir.")],
            "ddb": [sc(5, "Entry ve posting'leri TransactWriteItems ile ya hep ya hiç yazılır (en fazla 100 item). 5 puan kırıldı: toplamın sıfır olması uygulama kodunda kontrol edilir, var olan hesap foreign key ile değil kodla doğrulanır, bakiye ayrı bir sayaçtır ve posting'lerle uyuşmazlığı database görmez; \"dengesiz entry var mı\" tam bir okumadır."),
                    sc(10, "1.500 yazma partition'lara dağılır. Puan kırılmadı."),
                    sc(10, "Birkaç AZ, point-in-time recovery. Puan kırılmadı."),
                    sc(6, "Serverless. 4 puan kırıldı: denetçi dışa aktarmaları ve çeyrek raporları için ayrı bir analitik yol kurulur; ekip SQL'i bırakıp key tasarlar."),
                    sc(8, "İstek başına. 2 puan kırıldı: her entry transactional yazmadır ve iki kat birim tüketir.")],
        },
        h2h={
            "rds": _t("İlişkisel (RDS for PostgreSQL) ile kafa kafaya. Aynı engine, aynı SQL, aynı constraint ve trigger: R1'de fark yoktur. Ayrıştığı gereksinimler R2, R3 ve R5. RDS'in gücü sadelik ve fiyattır: PostgreSQL uzmanı ekip bildiği community sürümünü tek instance'ta işletir, I/O ücreti yoktur ve küçük, düz bir yükte fatura Aurora'dan düşük olabilir. "
                      "Aurora'nın gücü ay sonunda ve dayanıklılıkta görünür: Serverless v2 iki günlük on katlık yükü kendisi karşılar ve sonra küçülür, veri altı kopyadır, failover genellikle 60 saniyenin altındadır ve storage kendiliğinden büyür; RDS'te instance ay sonuna göre seçilip ay boyu kalır ve standby tek kopyadır. "
                      "Bu iş yükünde Aurora seçilir, çünkü sıfır kayıp ikisinde de sağlanır ama ay sonu dalgası ve kesinti süresi Aurora lehinedir; iki puanlık fark yakın bir yarıştır ve ekip zaten birkaç RDS işletiyorsa RDS savunulabilir. "
                      "Hangi koşul değişseydi RDS seçilirdi: yük düz ve küçük olsaydı, ay sonu dalgası olmasaydı, belirli bir community sürümü ya da extension gerekseydi ya da en düşük fatura dayanıklılık farkından daha önemli olsaydı."),
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinim R1'in denge kuralı ve R4. DynamoDB'nin gücü R2'dedir: ay sonu için hiçbir şey ayarlanmaz ve 1.500 yazma partition'lara dağılır; TransactWriteItems entry ve posting'leri birlikte yazar. "
                      "Ama bir defterin kuralları table'lar arasıdır: posting'lerin toplamı sıfır, hesap var olmalı, bakiye posting'lerin toplamına eşit. Aurora'da bunlar deferrable constraint, foreign key ve view'dır ve her programa uygulanır; DynamoDB'de hepsi uygulama kodunda yaşar ve \"dengesiz entry var mı\" sorusu bütün table'ın okunmasıdır. "
                      "Bu iş yükünde ilişkisel seçilir, çünkü denetlenebilirlik ve kuralın database'de olması paranın kaydı için şarttır. Hangi koşul değişseydi DynamoDB seçilirdi: posting hacmi saniyede on binlere çıksaydı, denge kuralı başka bir sistemde zaten doğrulanıyor olsaydı ve raporlar analitik kopyadan sorulsaydı."),
        },
        verdict=_t("Karar: Aurora 45, RDS 43, DynamoDB 39. Aurora ve RDS aynı PostgreSQL'dir ve R1'de eşittir; yarışı R2'nin ay sonu dalgası ve R3'teki kesinti süresi ile kopya sayısı belirler; sıfır kayıp ikisinde de sağlanır. "
                   "Yine de Aurora seçersek artımız: denge kuralı database'de, ay sonu kapasitesi kendiliğinden, altı kopya ve kısa failover, storage kendiliğinden büyür. "
                   "Potansiyel eksimiz: yedi yıllık defterin storage ve I/O'su faturada büyür ve Standard ile I/O-Optimized arasında seçim yapılır; partition ve vacuum bakımı ekibindir. Bir koşul değişseydi: yük düz ve küçük olsaydı RDS for PostgreSQL seçilirdi.")),

    # ------------------------------------------------------------------ 8. reservations with constraints (race vs DynamoDB)
    usecase("booking", 8, sim="race_booking", kind="race",
        title=_t("Randevu ve rezervasyon: çakışmayan zaman aralıkları"),
        key=_t("Table'lar: doctors, appointments (doctor_id, slot tstzrange, patient_id). Kural: aynı doktorun aralıkları çakışmaz."),
        story=_t("Bir sağlık platformu 300 klinik için randevu veriyor. Her randevu bir doktora ait bir zaman aralığıdır ve aynı doktorun iki aralığı asla çakışmamalı: 09:00-09:30 doluysa 09:15-09:45 alınamaz. "
                 "Sabah 08:00-09:00 arasında saniyede 50 randevu denemesi olur; gün boyunca saniyede 5. Hasta önce aralığı 10 dakika tutar, sonra onaylar; onaylanmayan tutma düşer. "
                 "Sorular: \"bu doktorun yarın boş aralıkları\", \"bu hastanın randevuları\", \"bu kliniğin haftalık doluluğu\". Randevu resmi kayıttır: kaybolan randevu kapıda bekleyen hastadır. Hatırlatma mesajları ayrı bir servistedir. Ekipte dört geliştirici var, SQL biliyor."),
        reqs=[
            req(True, "\"Bu doktor için bu aralığı sadece çakışan başka aralık yoksa yaz\" tek adımda ve atomik olmalı; aralıklar serbest uzunluktadır (15, 30, 45 dakika). Boş aralık sorusu tek sorgu olmalı. Tutma süresi dolunca aralık serbest kalmalı.",
                      "İki hasta aynı doktora çakışan aralık alırsa biri kapıda bekler; kural uygulamada \"önce oku sonra yaz\" ile korunursa sabah yarışında delinir."),
            req(True, "Sabah bir saat boyunca saniyede 50 randevu denemesi, çoğu aynı on klinikteki doktorlara; gün boyu saniyede 5. Her deneme 100 ms'nin altında cevaplanmalı.",
                      "Sabah yarışı platformun itibarıdır; yavaşlarsa hasta aynı düğmeye tekrar basar ve yük katlanır."),
            req(False, "Randevu resmi kayıttır; AZ arızasında kayıp olmamalı. Tutmanın (10 dakika) kaybı kabul edilir.",
                       "Kaybolan randevu kapıda bekleyen hastadır; kaybolan tutma sadece yeniden seçmektir."),
            req(False, "Dört geliştirici, SQL biliyor. Süresi dolan tutmalar için temizlik işi kabul edilir ama istenmez. Sunucu boyutlandırma istenmiyor.",
                       "Temizlik işi gecikirse aralık boşken alınamaz."),
            req(False, "Trafik gün içinde dalgalı, sabah tepe. Kapasite başına ödeme kabul; gece düşük ödeme istenir.",
                       "Sabah bir saat için ay boyu büyük kapasite ödemek israftır."),
        ],
        cands=["aur", "ddb", "ec"],
        scores={
            "aur": [sc(10, "EXCLUDE USING gist (doctor_id WITH =, slot WITH &&) exclusion constraint'i (&&: iki aralık çakışıyor mu) çakışan aralığı database seviyesinde reddeder; bu kural serbest uzunluktaki aralıklar için de geçerlidir (Ö1). Tutma ve onay aynı transaction'da, koşullu UPDATE ile yapılır (Ö5). \"Boş aralıklar\" bir aralık sorgusudur (Ö3); hasta ve klinik ilişkileri foreign key'dir (Ö2). Puan kırılmadı."),
                    sc(8, "Saniyede 50 kısa transaction tek writer için küçüktür; GiST index aralık sorgusunu hızlandırır (Ö4). 2 puan kırıldı: aynı on kliniğin doktorları aynı index page'lerinde yarışır ve sabah tepe için minimum ACU önceden yükseltilmelidir; 100 ms sınırı tepe anında ACU büyürken zorlanabilir."),
                    sc(10, "Altı kopya, üç AZ, point-in-time restore. Puan kırılmadı."),
                    sc(8, "Yönetilen yedek ve failover; SQL ekibin dili. 2 puan kırıldı: btree_gist extension'ı etkinleştirilir ve aralık tipleri öğrenilir; süresi dolan tutmalar için zamanlanmış bir temizlik işi yazılır."),
                    sc(8, "ACU-saat; gece 0,5 ACU'ya iner. 2 puan kırıldı: sabah için yükseltilen minimum ACU unutulursa gün boyu ödenir; Standard'da I/O ayrıca ödenir.")],
            "ddb": [sc(6, "Doktor partition key, aralık başlangıcı sort key; sabit 15 dakikalık hücrelerde attribute_not_exists koşulu çift kaydı tek yazmada engeller. 4 puan kırıldı: \"çakışan aralık yoksa\" koşulu tek bir item'ın koşulu olarak yazılamaz, çünkü koşul sadece yazılan item'ı test eder; 15 dakikanın katı olan aralıklar için uygulama aralığı 15 dakikalık hücrelere böler ve 1 ile 3 item'ı transaction ile yazar (mümkün, ama kural uygulamadadır); \"boş aralıklar\" sorusu için dolu hücreler okunup uygulamada hesaplanır."),
                    sc(10, "On-demand mod sabah tepesini ayarsız karşılar; her doktor ayrı bir partition key'dir. Puan kırılmadı."),
                    sc(10, "Birkaç AZ, point-in-time recovery. Puan kırılmadı."),
                    sc(8, "Serverless; TTL tutmayı siler. 2 puan kırıldı: TTL silmesi genellikle birkaç gün içinde olur, bu yüzden koşula süre karşılaştırması eklenir; hücre tasarımı ve transaction deseni ekibin öğreneceği işlerdir."),
                    sc(9, "İstek başına; gece sıfıra yakın. 1 puan kırıldı: birkaç hücreyi transaction ile yazmak iki kat birim tüketir.")],
            "ec": [sc(5, "Doktor başına bir sorted set ve SET NX EX 600 ile tutma tam süreli ve atomiktir. 5 puan kırıldı: çakışma kontrolü sorted set üzerinde bir Lua script'idir; hasta ve klinik ilişkileri ve haftalık doluluk raporu yoktur."),
                   sc(10, "Bellekten mikrosaniye; Serverless ölçeklenir. Puan kırılmadı."),
                   sc(3, "Replica'lar birkaç AZ'de ama dayanıklı yazma log'u yoktur; bir arıza son randevuları kaybedebilir. 7 puan kırıldı: randevu resmi kayıttır ve kaybı kapıda bekleyen hastadır."),
                   sc(8, "Serverless; EXPIRE temizlik işini gereksiz kılar. 2 puan kırıldı: Lua script'i ekibin bakımına girer."),
                   sc(8, "ECPU ve GB-saat. 2 puan kırıldı: bellek GB başına pahalıdır; randevu verisi küçük olduğu için fark küçüktür.")],
        },
        h2h={
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinim R1'in çakışma kuralı. DynamoDB'nin gücü sabah tepesindedir: her doktor ayrı bir partition key'dir, 50 deneme ayarsız karşılanır ve sabit hücrelerde attribute_not_exists koşulu çift kaydı tek yazmada engeller; DynamoDB sayfasındaki koltuk kartı bu modelin ne kadar güçlü olduğunu gösterir. "
                      "Fark aralığın şeklindedir: randevular serbest uzunluktadır ve \"çakışan aralık yoksa yaz\" kuralı başka row'lara bakmayı gerektirir; DynamoDB'de koşul sadece yazılan item'ı test eder, bu yüzden uygulama aralığı hücrelere böler ve birkaç item'ı transaction ile yazar. Aurora'da aynı kural bir exclusion constraint'tir ve database her yazmada kendisi uygular. "
                      "Bu iş yükünde ilişkisel seçilir, çünkü çakışma kuralı tek bir kaydın içinde değil, kayıtlar arasındadır ve hacim tek writer'ın rahat erişimindedir; bir puanlık fark yakın bir yarıştır. "
                      "Hangi koşul değişseydi DynamoDB seçilirdi: aralıklar sabit 15 dakikalık hücreler olsaydı (koşul tek item'da kalırdı), açılış trafiği saniyede on binlere çıksaydı ve raporlar ayrı bir kopyadan sorulsaydı."),
            "ec": _t("Bellek içi key-value (ElastiCache) ile kafa kafaya. Ayrıştığı gereksinimler R1'in ilişki kısmı ve R3. ElastiCache'in gücü tutmadadır: SET NX EX 600 ile tutma atomiktir ve tam olarak 10 dakika sonra kendiliğinden düşer; temizlik işi gerekmez ve mikrosaniyede cevap verir. "
                      "Ama randevu resmi kayıttır ve dayanıklı yazma log'u olmayan bir store'da bir arıza son randevuları kaybeder; çakışma kontrolü de sorted set üzerinde bir Lua script'idir ve hasta, klinik ve doluluk raporu gibi ilişkiler yoktur. "
                      "Bu yüzden kalıcı kayıt ilişkisel database'de tutulur; ElastiCache en fazla 10 dakikalık tutma için bir yardımcı olabilir ve bu, ikisini birlikte kullanmaktır. Hangi koşul değişseydi ElastiCache seçilirdi: randevu başka bir sistemde zaten kalıcı olsaydı ve buradaki iş sadece kısa süreli tutma ve sayaç olsaydı ya da dayanıklı log istenseydi ve bellek içi hız şart olsaydı (MemoryDB)."),
        },
        verdict=_t("Karar: Aurora 44, DynamoDB 43, ElastiCache 34. En yakın yarış budur ve kararı tek bir kural verir: çakışma kuralı kayıtlar arasındadır ve exclusion constraint onu database'de uygular. "
                   "Yine de ilişkisel seçersek artımız: çakışma kuralı database'de ve her programa uygulanır, boş aralıklar tek sorgu, hasta ve klinik ilişkileri foreign key, randevu altı kopyayla kalıcı. "
                   "Potansiyel eksimiz: sabah tepesi için minimum ACU önceden yükseltilir; süresi dolan tutmalar için temizlik işi yazılır; btree_gist ve aralık tipleri öğrenilir. Bir koşul değişseydi: aralıklar tek bir sabit hücre olsaydı ve trafik lansman gibi sıçrasaydı DynamoDB kazanırdı; ekip DynamoDB'yi SQL kadar iyi bilseydi bu bir puanlık yarış tersine dönebilirdi.")),

    # ------------------------------------------------------------------ 9. workflow state with audit (card only)
    usecase("workflow", 9,
        title=_t("İş akışı durumu ve denetim izi"),
        key=_t("Table'lar: orders (status), order_status_history (from, to, who, when). Geçişler bir states table'ıyla sınırlı."),
        story=_t("Bir sipariş karşılama sistemi her siparişi bir durum makinesinde ilerletir: new, paid, picked, shipped, delivered, cancelled. İzin verilen geçişler bellidir: picked'tan new'e dönülemez. "
                 "Her geçiş kim tarafından, ne zaman, hangi durumdan hangi duruma yapıldıysa kaydedilmeli ve bu kayıt beş yıl saklanmalı. Günde 20.000 geçiş, yani saniyede yarım; kargo entegrasyonu saniyede 20'lik kısa tepeler yapar. "
                 "Operasyon ekibi \"iki günden uzun süredir picked'ta takılı siparişler\" ve \"bu siparişin bütün geçmişi\" sorularını sorar. Geçiş ile denetim kaydı birlikte yazılmalı; biri olmadan diğeri olmamalı. Ekipte üç geliştirici var, SQL biliyor."),
        reqs=[
            req(True, "\"Durumu sadece picked ise shipped yap ve aynı anda denetim row'u yaz\" tek adımda ve atomik olmalı; izin verilmeyen geçiş database tarafından reddedilmeli. Sorular: \"takılı siparişler\" (duruma ve süreye göre), \"bu siparişin geçmişi\" (zaman sırasıyla).",
                      "Geçiş yazılıp denetim kaydı yazılmazsa denetçi boşluk bulur; izin verilmeyen geçiş kabul edilirse teslim edilmiş sipariş yeniden ödeme ister."),
            req(True, "Saniyede yarım geçiş, tepe 20. Her geçiş 50 ms'nin altında. Beş yılda 36 milyon denetim row'u.",
                      "Hacim küçüktür; burada doğruluk ve sorgulanabilirlik belirleyicidir."),
            req(False, "Denetim izi beş yıl saklanır; AZ arızasında kayıp olmamalı.",
                       "Kaybolan denetim kaydı denetçiye açıklanamayan bir boşluktur."),
            req(False, "Üç geliştirici, SQL biliyor. Geçiş kuralı tek bir yerde tanımlanmalı ve her programa uygulanmalı. Sunucu boyutlandırma istenmiyor.",
                       "Kural her programda ayrı yazılırsa bir program eski kuralla çalışır."),
            req(False, "Trafik düşük ve düz; kapasite başına en küçük ödeme istenir.",
                       "Küçük yükte faturayı kapasitenin alt sınırı belirler."),
        ],
        cands=["aur", "ddb", "doc"],
        scores={
            "aur": [sc(10, "UPDATE orders SET status = 'shipped' WHERE order_id = ... AND status = 'picked' ve INSERT order_status_history aynı transaction'dadır (Ö5); bir trigger fonksiyonu geçişi allowed_transitions table'ına göre reddeder ve denetim row'unu kendisi yazar, böylece kural tek yerde durur ve her programa uygulanır (Ö6, Ö2). \"Takılı siparişler\" status ve updated_at üzerinde bir WHERE, \"geçmiş\" bir ORDER BY'dır (Ö3). Puan kırılmadı."),
                    sc(10, "Saniyede 20 kısa transaction tek writer için küçüktür; 36 milyon denetim row'u index ile sorgulanır (Ö4). Puan kırılmadı."),
                    sc(10, "Altı kopya, point-in-time restore. Puan kırılmadı."),
                    sc(9, "Yönetilen; kural trigger'da tek yerde. 1 puan kırıldı: trigger kodu da sürüm kontrolünde tutulmalı ve migration ile dağıtılmalıdır."),
                    sc(8, "ACU-saat; düşük yükte 0,5 ACU. 2 puan kırıldı: minimum ACU düşük yükte de ödenir; sıfır ACU'ya duraklatma desteklenen sürümlerde mümkündür ama ilk bağlantı gecikir.")],
            "ddb": [sc(6, "ConditionExpression status = :from ile geçiş tek yazmada korunur ve denetim item'ı aynı partition'a TransactWriteItems ile yazılır. 4 puan kırıldı: izin verilen geçişler tablosu uygulama kodundadır; \"takılı siparişler\" sorusu status + updated_at üzerinde bir GSI ister ve beş yıllık geçmiş için ayrı bir tasarım yapılır."),
                    sc(10, "Partition'lara dağılır. Puan kırılmadı."),
                    sc(10, "Birkaç AZ, point-in-time recovery. Puan kırılmadı."),
                    sc(8, "Serverless. 2 puan kırıldı: geçiş kuralı her programda ya da bir Lambda'da yaşar; Streams ile denetim izi alternatiftir ama ayrı bir bileşendir."),
                    sc(10, "İstek başına; günde 20.000 yazma neredeyse bedavadır. Puan kırılmadı.")],
            "doc": [sc(8, "Sipariş bir document, geçmiş içinde bir dizi; updateOne filtresi status = picked ile geçiş ve $push ile denetim kaydı tek atomik yazmadır. 2 puan kırıldı: izin verilen geçişler kodda yaşar; beş yıllık geçmiş document içinde büyür ve \"takılı siparişler\" için status + updated_at index'i kurulur."),
                    sc(9, "Küçük yük. 1 puan kırıldı: instance sınıfı önceden seçilir."),
                    sc(10, "Altı kopya. Puan kırılmadı."),
                    sc(7, "Yönetilen. 3 puan kırıldı: MongoDB API'si ekip için yenidir; kural kodda."),
                    sc(7, "Instance saat başına. 3 puan kırıldı: düşük yükte de instance'lar çalışır; bu iş yükü için en pahalı seçenektir.")],
        },
        h2h={
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinimler R1'in kural kısmı ve R4. DynamoDB'nin gücü R5'te açıktır: günde 20.000 yazma istek başına neredeyse bedavadır ve koşullu yazma \"status = picked ise\" kuralını tek item'da korur; denetim item'ı da aynı partition'a transaction ile yazılır. "
                      "Aurora'nın gücü kuralın yerindedir: izin verilen geçişler bir table'dır, trigger fonksiyonu her geçişi ona göre reddeder ve denetim row'unu kendisi yazar; hangi program yazarsa yazsın kural aynıdır. DynamoDB'de bu tablo uygulama kodundadır ve \"takılı siparişler\" sorusu bir GSI tasarımıdır. "
                      "Bu iş yükünde ilişkisel seçilir, çünkü hacim küçüktür, kural tek yerde olmalıdır ve operasyon soruları serbest SQL'dir; DynamoDB'nin maliyet avantajı küçük yükte birkaç dolardır. "
                      "Hangi koşul değişseydi DynamoDB seçilirdi: geçiş hacmi saniyede binlere çıksaydı, kural zaten bir iş akışı motorunda (örneğin Step Functions) yaşasaydı ve denetim izi bir Streams tüketicisiyle başka bir sisteme yazılsaydı."),
            "doc": _t("Document (DocumentDB) ile kafa kafaya. Ayrıştığı gereksinimler R1'in kural kısmı, R4 ve R5. DocumentDB'nin gücü geçmişin şeklidir: sipariş ve geçmişi tek document'tır, updateOne ile geçiş ve $push ile denetim kaydı tek atomik yazmadır ve \"bu siparişin geçmişi\" tek okumadır. "
                      "Fark kuralda ve büyümede başlar: izin verilen geçişler kodda yaşar ve beş yıllık geçmiş document'ın içinde büyür; Aurora'da kural bir table ve bir trigger'dır, geçmiş ayrı bir table'da index'le sorgulanır. "
                      "Bu iş yükünde ilişkisel seçilir, çünkü ekip SQL biliyor, yük küçüktür ve kuralın database'de olması istenir; DocumentDB bu küçük yük için en pahalı seçenektir. Hangi koşul değişseydi DocumentDB seçilirdi: sipariş iç içe ve sık şekil değiştiren bir belge olsaydı, geçmiş kısa olsaydı ve ekip MongoDB API'sini zaten kullanıyor olsaydı."),
        },
        verdict=_t("Karar: Aurora 47, DynamoDB 44, DocumentDB 41. Üç aday da yükü taşır; yarışı R1'in kural kısmı belirler: geçiş kuralı ve denetim kaydı database'de tek yerde mi, uygulama kodunda mı. "
                   "Yine de ilişkisel seçersek artımız: kural trigger'da tek yerde, geçiş ve denetim tek transaction, takılı siparişler tek sorgu, beş yıllık geçmiş index'li ve kalıcı. "
                   "Potansiyel eksimiz: trigger kodu migration disipliniyle dağıtılır; küçük yükte minimum ACU ödenir. Bir koşul değişseydi: hacim saniyede binlere çıksaydı ve kural bir iş akışı motorunda yaşasaydı DynamoDB kazanırdı.")),

    # ------------------------------------------------------------------ 10. geospatial search with PostGIS (card only)
    usecase("geo", 10,
        title=_t("Coğrafi sorular: teslimat bölgeleri ve en yakın nokta (PostGIS)"),
        key=_t("Table'lar: zones (polygon), pickup_points (point), couriers (point, updated_at), orders. GiST index ile."),
        story=_t("Bir teslimat şirketinin 1.200 teslimat bölgesi (çokgen), 3.000 teslim alma noktası ve 400 kuryesi var. Kuryeler konumlarını 10 saniyede bir gönderir: saniyede 40 yazma. "
                 "Sorular: \"bu adres hangi bölgede\" (fiyat buna göre), \"bu adrese en yakın 5 teslim alma noktası\", \"bu bölgedeki açık siparişler ve kuryeler\", \"bu rotanın uzunluğu\". Bölge fiyatı sipariş yazılırken bölgeye göre hesaplanır ve siparişle aynı transaction'da kaydedilir. "
                 "Saniyede 200 konum sorusu, 40 yazma; saat 18:00'de tepe. Bölgeler ayda bir değişir. Konum geçmişi 30 gün saklanır. Ekipte dört geliştirici var, SQL biliyor, coğrafi veri yeni."),
        reqs=[
            req(True, "\"Bu nokta hangi çokgenin içinde\", \"bu noktaya en yakın 5 nokta\", \"bu çokgendeki siparişler\" ve \"rota uzunluğu\" soruları doğrudan sorulabilmeli; bölge fiyatı siparişle aynı transaction'da yazılmalı; sipariş ve kurye ilişkileri korunmalı.",
                      "Yanlış bölge yanlış fiyattır; fiyat siparişten ayrı yazılırsa ikisi uyuşmaz. Çokgen içi sorusu uygulamada hesaplanırsa 1.200 bölge her istekte taranır."),
            req(True, "Saniyede 200 coğrafi soru, 40 konum yazması; 18:00 tepesinde iki katı. Her soru 50 ms'nin altında. Konum geçmişi 30 günde yüz milyon row.",
                      "Teslimat uygulaması sahada çalışır; yavaş cevap kuryeyi bekletir. Konum geçmişi büyür ve sorgular yavaşlamamalıdır."),
            req(False, "Sipariş ve bölge fiyatı resmi kayıttır; konum geçmişi 30 gün sonra silinebilir. AZ arızasında sipariş kaybı olmamalı.",
                       "Kaybolan sipariş kaybolan teslimattır; kaybolan konum geçmişi sadece bir rapor boşluğudur."),
            req(False, "Dört geliştirici, SQL biliyor, coğrafi veri yeni. Coğrafi fonksiyonlar öğrenilebilir olmalı; ayrı bir coğrafi servis işletilmek istenmiyor.",
                       "Ayrı bir coğrafi servis, ayrı bir veri kopyası ve ayrı bir operasyon demektir."),
            req(False, "Trafik gün içinde dalgalı; kapasite başına ödeme kabul. Veri orta boy.",
                       "18:00 tepesi için ay boyu büyük kapasite istenmez."),
        ],
        cands=["aur", "os", "ddb"],
        scores={
            "aur": [sc(10, "PostGIS extension'ı (Ö8) ST_Contains, ST_DWithin, KNN sıralaması ve ST_Length fonksiyonlarını verir; GiST index çokgen ve nokta sorularını hızlandırır (Ö4). Bölge fiyatı siparişle aynı transaction'da yazılır (Ö5) ve sipariş, kurye, bölge ilişkileri foreign key'dir (Ö2); \"bu bölgedeki siparişler\" bir JOIN'dir (Ö3). Puan kırılmadı."),
                    sc(9, "200 soru GiST index ile milisaniyelerdedir, 40 yazma küçüktür; reader instance tepe okumalarını taşır (Ö7). 1 puan kırıldı: yüz milyon konum row'u için partition ve 30 günlük silme işi tasarlanır."),
                    sc(10, "Altı kopya, point-in-time restore. Puan kırılmadı."),
                    sc(8, "Yönetilen; PostGIS tek komutla etkinleştirilir (CREATE EXTENSION postgis), ayrı servis gerekmez. 2 puan kırıldı: coğrafi tipler, projeksiyonlar ve GiST ekibin öğreneceği yeni konulardır."),
                    sc(8, "ACU-saat; gece düşer. 2 puan kırıldı: minimum ACU ve konum geçmişinin storage'ı; Standard'da konum yazmalarının I/O'su ayrıca ödenir.")],
            "os": [sc(7, "geo_point ve geo_shape alanlarıyla \"çokgen içinde mi\" ve \"en yakın noktalar\" soruları doğrudan sorulur. 3 puan kırıldı: bölge fiyatı siparişle aynı transaction'da yazılamaz, sipariş ve kurye ilişkileri index'e düzleştirilir ve rota uzunluğu gibi hesaplar uygulamaya kalır."),
                   sc(9, "Coğrafi sorgular shard'lara dağılır; 40 yazma küçüktür. 1 puan kırıldı: shard ve node sınıfı önceden seçilir; refresh aralığı yeni konumu kısa süre geciktirir."),
                   sc(6, "Replica shard'lar ve snapshot. 4 puan kırıldı: arama index'i resmi kayıt değildir; sipariş ve fiyat başka bir yerde durmalıdır, bu da iki sistem demektir."),
                   sc(7, "Yönetilen domain. 3 puan kırıldı: mapping, shard planı ve Aurora'dan akış ekibin işidir; ayrı bir servis işletilir."),
                   sc(6, "Node saat başına, 7/24. 4 puan kırıldı: coğrafi sorular için ayrı bir domain gece de ödenir ve kayıt sistemi ayrıca gerekir.")],
            "ddb": [sc(3, "Konum, geohash önekli bir sort key ile saklanırsa \"yakındaki noktalar\" bir begins_with dilimiyle yaklaşık olarak bulunur. 7 puan kırıldı: \"bu nokta hangi çokgenin içinde\" sorusu key ile sorulamaz ve 1.200 çokgen uygulamada taranır; rota uzunluğu ve çokgen JOIN'i yoktur; bölge fiyatı ile sipariş TransactWriteItems ile yazılır ama fiyat hesabı önce uygulamada yapılır."),
                    sc(10, "Yazma ve okuma partition'lara dağılır; TTL konum geçmişini 30 gün sonra siler. Puan kırılmadı."),
                    sc(10, "Birkaç AZ, point-in-time recovery. Puan kırılmadı."),
                    sc(6, "Serverless. 4 puan kırıldı: geohash kütüphanesi ve çokgen hesabı uygulama kodunda yaşar; ekip hem key tasarımını hem coğrafi hesabı öğrenir."),
                    sc(9, "İstek başına; TTL silmesi bedavadır. 1 puan kırıldı: her konum sorusu birkaç okuma birimi tüketir.")],
        },
        h2h={
            "os": _t("Search engine (OpenSearch) ile kafa kafaya. Ayrıştığı gereksinimler R1'in transaction kısmı, R3 ve R5. OpenSearch'ün gücü coğrafi sorudadır: geo_point ve geo_shape ile \"çokgen içinde mi\" ve \"en yakın 5 nokta\" milisaniyede cevaplanır ve dashboard araçları haritayı çizer. "
                      "Fark kayıt sistemindedir: bölge fiyatı siparişle aynı transaction'da yazılmalıdır ve sipariş, kurye, bölge ilişkileri korunmalıdır; OpenSearch bir arama index'idir, siparişi ve fiyatı başka bir sistem tutar ve bu, iki sistem ve bir akış demektir. PostGIS aynı coğrafi soruları ilişkisel database'in içinde, siparişin yanında ve GiST index ile cevaplar. "
                      "Bu iş yükünde ilişkisel seçilir, çünkü coğrafi soru siparişin fiyatını belirler ve onunla aynı yazmada kaydedilir; ayrı bir coğrafi servis istenmez. "
                      "Hangi koşul değişseydi OpenSearch seçilirdi: coğrafi sorular siparişten bağımsız bir keşif ve dashboard işi olsaydı (\"haritada kuryeleri göster\"), metin araması da istenseydi ve sipariş zaten başka bir sistemde olsaydı."),
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinim R1. DynamoDB'nin gücü R2 ve R5'te: 40 konum yazması ve yüz milyon row için hiçbir boyutlandırma yoktur ve TTL 30 günlük geçmişi bedavaya siler; konum geçmişi tek başına DynamoDB için iyi bir iş yüküdür. "
                      "Ama coğrafi sorular key ile sorulamaz: \"bu nokta hangi çokgenin içinde\" sorusu için 1.200 çokgen uygulamada taranır, \"en yakın 5 nokta\" geohash önekiyle sadece yaklaşık bulunur ve rota uzunluğu yoktur; PostGIS bunları tek fonksiyon ve bir GiST index ile cevaplar. "
                      "Bu iş yükünde ilişkisel seçilir, çünkü sorular coğrafidir, ilişkilidir ve siparişle aynı transaction'da yazılır. Hangi koşul değişseydi DynamoDB seçilirdi: tek soru \"bu kuryenin son konumu\" olsaydı, bölge hesabı başka bir serviste yapılsaydı ve konum hacmi saniyede on binlere çıksaydı; o zaman konum geçmişi DynamoDB'de, bölgeler ve siparişler Aurora'da tutulur."),
        },
        verdict=_t("Karar: Aurora 45, DynamoDB 38, OpenSearch 35. Yarışı R1 belirler: coğrafi soru siparişin fiyatını belirler ve ilişkisel database PostGIS ile bu soruyu siparişin yanında cevaplar. "
                   "Yine de ilişkisel seçersek artımız: çokgen, en yakın nokta ve rota soruları tek fonksiyon, GiST index ile hızlı, bölge fiyatı siparişle tek transaction'da, ayrı coğrafi servis yok. "
                   "Potansiyel eksimiz: PostGIS ve GiST ekibin öğreneceği yeni konulardır; yüz milyon konum row'u için partition ve silme işi tasarlanır. Bir koşul değişseydi: coğrafi sorular siparişten bağımsız bir dashboard işi olsaydı OpenSearch yarışa girerdi.")),
]

USECASES["aurora"] = AURORA_USECASES


# ====================================================================== Amazon DocumentDB (page id "docdb"), Turkish only
# Sources of the limits and numbers quoted in the reasons below (the hedges are the hedges of the source):
#  - Cluster volume "replicate data six ways across three Availability Zones", 0-16 instances, one primary, up to 15 replicas,
#    replica lag "usually less than 100 milliseconds", "Writes to an Amazon DocumentDB cluster are atomic within a single document",
#    "Attempting to write to a reader results in an error": https://docs.aws.amazon.com/documentdb/latest/devguide/how-it-works.html
#  - Failover "up to 30 seconds of downtime for your cluster, but often less time than that":
#    https://docs.aws.amazon.com/whitepapers/latest/get-started-documentdb/amazon-documentdb-architecture.html
#  - Quotas: document size 16 MiB, nesting 200 levels, 64 indexes per collection, 32 keys in a compound index, cluster 256 TiB (8.0):
#    https://docs.aws.amazon.com/documentdb/latest/devguide/limits.html
#  - Transactions (4.0 and later) "across multiple documents, statements, collections, and databases"; one minute execution limit;
#    document-level write locks time out after 1 minute: https://docs.aws.amazon.com/documentdb/latest/devguide/transactions.html
#  - Change streams: default retention three hours, "between 1 hour and 7 days": https://docs.aws.amazon.com/documentdb/latest/devguide/change_streams.html
#  - TTL deletes "are best effort and are not guaranteed within a specific timeframe", each deletion incurs IO costs:
#    https://docs.aws.amazon.com/documentdb/latest/devguide/how-it-works.html (TTL deletes)
#  - Elastic clusters "support workloads with millions of reads/writes per second and petabytes of storage capacity", up to 32 shards:
#    https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-how-it-works.html
#  - Serverless: 0.5-256 DCU, each DCU "approximately 2 gibibytes (GiB) of memory", on 5.0 and 8.0:
#    https://docs.aws.amazon.com/documentdb/latest/devguide/docdb-serverless-how-it-works.html
#  - Pricing components: instance hours, I/O requests per million, storage, backup storage: https://docs.aws.amazon.com/documentdb/latest/devguide/what-is.html
#  - MongoDB API compatibility 3.6, 4.0, 5.0, 8.0; not every operator on every version: https://docs.aws.amazon.com/documentdb/latest/devguide/mongo-apis.html
#  - $jsonSchema validation (4.0 and later, not on elastic clusters): https://docs.aws.amazon.com/documentdb/latest/devguide/json-schema-validation.html
#  - $lookup: equality match (left outer join), correlated subqueries from 8.0.2: https://docs.aws.amazon.com/documentdb/latest/devguide/functional-differences.html
#  - Retryable writes only from 8.0.2: https://docs.aws.amazon.com/documentdb/latest/devguide/retryable-writes.html
#  - Multikey, compound, sparse, partial, TTL, text and vector indexes: https://docs.aws.amazon.com/documentdb/latest/devguide/indexes-multikey.html
#  - DynamoDB item size 400 KB, transactions up to 100 actions, TTL "within a few days": DynamoDB Developer Guide (see the DynamoDB section above)
#  - Aurora: six copies in three AZs, up to 15 replicas, Serverless v2 0.5 ACU minimum: see the Aurora section above
#  - ElastiCache Serverless and EXPIRE: https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/WhatIs.html

DOCDB_USECASES = [
    # ------------------------------------------------------------------ 1. product catalog with variable attributes (clear win)
    usecase("catalog", 1, sim="win_catalog", kind="win",
        title=_t("Değişken özellikli ürün kataloğu (Lale Market)"),
        key=_t("Collection: products. Document: _id, name, category, price, attributes (iç içe), tags (array)."),
        story=_t("Lale Market'in kataloğunda 200 ürün var, gerçek bir pazar yerinde 200.000 olur. Her ürün türünün özellikleri farklıdır: kulaklıkta renk ve garanti ayı, kitapta sayfa sayısı ve dil, kazakta beden ve kumaş. "
                 "Ürün sayfası ürünü bütün özellikleri ve etiketleriyle tek seferde ister; kategori sayfası \"Elektronik, siyah, rating'e göre\" filtreler. Pazarlama ekibi her ay yeni bir özellik ekler (\"su geçirmez\", \"enerji sınıfı\") ve bu özellik sadece yeni ürünlerde dolu başlar. "
                 "Saniyede 2.000 okuma (önünde bir cache var), saniyede 20 yazma; kampanya gününde okuma beş katına çıkar. Katalog kaybolursa satıcı beslemelerinden bir günde yeniden kurulur. Dört geliştirici, ikisi MongoDB API'sini önceki işinden biliyor; sunucu boyutlandırmak istenmiyor. Metin araması ayrı bir arama servisine verilecek."),
        reqs=[
            req(True, "\"Bu ürün id'sinin tamamı\" tek okumada gelmeli. \"Elektronik ve siyah, rating'e göre\" ve \"garanti_ay >= 24 ve rating >= 4,5\" gibi iç içe field'lara göre filtreler yeniden tasarım istemeden çalışmalı. Her ürün türü kendi field'larını taşımalı; yeni özellik migration istememeli. Bir ürünün tek bir özelliğini değiştirmek bütün ürünü yeniden yazmamalı.",
                      "Ürün sayfası mağazanın vitrinidir: ürün birkaç parçadan toplanırsa her sayfa birkaç okumadır. Yeni özellik için bir schema değişikliği pazarlama takvimini database ekibine bağlar. Ürünün tamamını yeniden yazan bir güncelleme, aynı anda başka bir satıcının değişikliğini ezer."),
            req(True, "Saniyede 2.000 okuma, kampanyada 10.000; saniyede 20 yazma. Ürün sayfası 20 ms'nin altında dönmeli. Katalog yılda iki katına çıkıyor; 400.000 ürün için tasarım değişmemeli.",
                      "Yavaş ürün sayfası satış kaybıdır. Okuma hacmi yazmanın yüz katıdır; ölçek okuma tarafındadır ve okumayı yazmayı yormadan büyütmek gerekir."),
            req(False, "Katalog satıcı beslemelerinden bir günde yeniden kurulabilir. Bir Availability Zone arızasında kayıp ve uzun kesinti olmamalı.",
                       "Katalog kaybı mağazayı kapatmaz ama vitrini bir gün boşaltır; dayanıklılık güçlü bir tercihtir, zorunluluk değildir."),
            req(False, "Dört geliştirici, ikisi MongoDB API'sini biliyor. Yedek, yama ve failover istenmiyor. Aylık yeni özellik kodda tek satırla eklenmeli.",
                       "Bilmediği bir API'ı öğrenen ekip hata yapar; her ay bir schema değişikliği ve migration penceresi kategori ekibinin takvimini kilitler."),
            req(False, "Okuma ağırlıklı, gün içinde düz, kampanyada tepe. Kapasite başına ya da kullanım başına ödeme, ikisi de uyar. Veri orta boy (birkaç GB).",
                       "Düz trafikte kapasite başına ödeme öngörülebilirdir; kampanya tepesi için bütün yıl büyük sunucu ödemek istenmez."),
        ],
        cands=["doc", "aur", "os"],
        scores={
            "doc": [sc(10, "Ürün tek bir document'tır: attributes embedded document, tags bir array; _id ile tek okuma (Ö1, Ö2). \"Elektronik ve siyah\" filtresi dot notation ile iç içe field'a gider (Ö3) ve { category: 1, rating: -1 } compound index'i ile IXSCAN olur (Ö4). Yeni özellik sadece yeni document'lara yazılır; updateOne ile $set tek field'ı değiştirir (Ö5). Puan kırılmadı."),
                    sc(10, "Okumalar en fazla 15 replica'ya dağılır (Ö8) ve kampanyada replica ya da serverless kapasite eklenir; 20 yazma tek primary için küçüktür. Index'li okuma milisaniyelerdedir. Puan kırılmadı."),
                    sc(10, "Cluster volume veriyi üç Availability Zone'da altı kopya tutar; failover \"up to 30 seconds\", çoğu zaman daha kısa; sürekli yedek ve point-in-time restore. Puan kırılmadı."),
                    sc(8, "Yedek, yama, failover ve storage büyümesi yönetilir; iki geliştirici MongoDB API'sini zaten biliyor. 2 puan kırıldı: ekip boyutlandırma istemiyor ama instance sınıfı ya da DCU aralığı yine seçilir; index tasarımı ekibin kararıdır ve her yeni filtre için index planlanır."),
                    sc(8, "Instance saat başına ve I/O başına ya da serverless DCU-saat (0,5 DCU minimum) ödenir; düz okuma trafiğinde öngörülebilir. 2 puan kırıldı: Multi-AZ için en az iki instance gece de çalışır ve her COLLSCAN I/O olarak faturaya yansır.")],
            "aur": [sc(8, "Ürün bir row, değişken özellikler JSONB kolonunda; GIN index ile iç içe field filtresi çalışır; tek field jsonb_set ile değişir. 2 puan kırıldı: JSONB içindeki özelliğe göre filtre ve sıralama normal kolona göre daha az doğaldır, operatörleri ekip öğrenir; JSONB güncellemesi row'un tamamını yeniden yazar (MVCC)."),
                    sc(9, "2.000 okuma index aramasıdır ve reader instance'lara dağıtılır; 20 yazma küçüktür. 1 puan kırıldı: reader sayısı ve ACU aralığı ekip tarafından seçilir."),
                    sc(10, "Üç AZ'de altı kopya, point-in-time restore. Puan kırılmadı."),
                    sc(7, "Yedek ve yama yönetilir. 3 puan kırıldı: ekibin SQL ve JSONB operatörlerini öğrenmesi gerekir; JSONB dışına çıkan her field ALTER TABLE'dır; migration disiplini ister."),
                    sc(7, "ACU-saat ya da instance-saat, 0,5 ACU minimum. 3 puan kırıldı: gece de minimum kapasite ödenir; reader instance ayrıca ödenir; Aurora Standard'da I/O ayrıca sayılır.")],
            "os": [sc(6, "Özelliklere göre filtre ve facet OpenSearch'ün ana işidir; metin araması da buradadır. 4 puan kırıldı: kısmi güncelleme yerine document yeniden index'lenir; mapping değişince index baştan kurulur; bir arama index'i kataloğun kayıt sistemi değildir."),
                   sc(9, "2.000 okuma küçük bir domain için rahattır. 1 puan kırıldı: refresh aralığı yüzünden yeni yazma kısa süre görünmeyebilir; shard sayısı önceden seçilir."),
                   sc(5, "Replica shard node arızasını karşılar. 5 puan kırıldı: arama index'i kaynak veri değildir; kaynak başka bir yerde durmalı ve index oradan yeniden kurulabilmelidir."),
                   sc(6, "Yönetilen domain. 4 puan kırıldı: mapping tasarımı, reindex ve shard planı ekibin işidir; ekip OpenSearch bilmiyor."),
                   sc(6, "Node saat başına. 4 puan kırıldı: üç node'luk domain gece de ödenir ve katalog için ayrıca bir kayıt sistemi gerekir.")],
        },
        h2h={
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinimler R1 ve R4. Aurora'nın gücü ilişkilerdedir: marka, kategori ve varyant ayrı table'lar olsaydı foreign key ve CHECK ile database onları korurdu ve \"stoğu biten varyantların ürünleri\" bir JOIN olurdu; JSONB kolonu değişken özellikleri de taşır. "
                      "Bu iş yükünde ilişki yok denecek kadar azdır: marka bir metin field'ıdır, stok başka bir sistemdedir ve özellikler ürün türüne göre değişir. Document database'in gücü tam buradadır: ürün tek bir document'tır, iç içe field ve array index'lenir, yeni özellik bir migration değildir ve ekip API'ı biliyor. "
                      "Aurora sayfasındaki katalog kartı bu kararın tersini verdi; orada katalog marka, kategori, varyant ve fiyat ilişkileriyle doluydu ve ilişkilerin doğruluğunu database korumalıydı. Fark ürünün şeklinde değil ilişkilerin sayısındadır. "
                      "Hangi koşul değişseydi Aurora seçilirdi: varyant, fiyat ve depo stoğu aynı database'de ilişki olarak tutulsaydı, \"fiyat sıfırdan büyük\" gibi kurallar database'de korunmak istenseydi ya da ekip sadece SQL biliyor olsaydı."),
            "os": _t("Search engine (OpenSearch) ile kafa kafaya. Ayrıştığı gereksinimler R1'in güncelleme kısmı, R3 ve R4. OpenSearch'ün gücü aramadadır: \"siyah, 24 ay garanti, 1.000 TL altı\" sorusunu facet sayılarıyla milisaniyede cevaplar ve yazım hatası toleranslı metin aramasını verir. "
                      "Ama bir arama index'i kayıt sistemi değildir: özelliğin tek bir field'ını değiştirmek document'ı yeniden index'lemektir, mapping değişince index baştan kurulur ve kaynak veri başka bir yerde durmalıdır. "
                      "Bu yüzden iki servis rakip değil tamamlayıcıdır: katalog DocumentDB'de yaşar, arama kopyası change stream ile OpenSearch'e akar (kart 8 ikisini aynı arama sorusu için yarıştırır ve metin araması gelince ikisinin birlikte doğru cevap olduğunu yazar). Bu iş yükünde document database seçilir, çünkü kayıt sistemi istenir ve metin araması zaten ayrı bir servise verilecektir. "
                      "Hangi koşul değişseydi OpenSearch seçilirdi: katalog başka bir sistemde zaten kalıcı olsaydı ve buradaki tek iş facet'li, relevance sıralı arama olsaydı."),
        },
        verdict=_t("Karar: DocumentDB 46, Aurora 41, OpenSearch 32. Net bir kazanma: iş yükü document modelinin tam tanımıdır; türe göre değişen özellikler, iç içe field'lara göre filtre, tek okumada bütün ürün ve ilişki yok. DocumentDB hiçbir zorunlu gereksinimde puan kaybetmez. "
                   "Yine de document seçersek artımız: ürün tek document, yeni özellik migration'sız, iç içe field ve array index'li, okuma replica'larla büyür, ekip bildiği API ile çalışır. "
                   "Potansiyel eksimiz: index planı ekibin işidir ve index'siz her yeni filtre COLLSCAN'dir; kurallar (fiyat > 0) $jsonSchema ile kısmen, çoğu kodda korunur; bütün yazmalar tek primary'den geçer; metin araması için OpenSearch ayrıca gerekir. Bir koşul değişseydi: varyant, fiyat ve stok ilişki olarak aynı database'de tutulsaydı Aurora yarışa girerdi.")),

    # ------------------------------------------------------------------ 2. user profiles with nested preferences (race vs DynamoDB)
    usecase("profiles", 2, sim="race_profiles", kind="race",
        title=_t("İç içe tercihleri olan kullanıcı profilleri"),
        key=_t("Collection: users. Document: _id, name, locale, addresses (array), prefs (iç içe), devices (array)."),
        story=_t("Bir podcast uygulamasının üç milyon kullanıcısı var. Profil tek bir nesnedir: ad, dil, adres listesi, bildirim tercihleri, cihaz listesi. Her ekran açılışında uygulama profili okur; kullanıcı ayda birkaç kez bir tercihi ya da bir adresi değiştirir. "
                 "Pazarlama ekibi profilin içine göre sorular sorar: \"İstanbul'da oturan ve podcast önerisi isteyen kullanıcılar\", \"iOS cihazı olup bildirimi kapalı olanlar\"; bu sorular haftada birkaç kez değişir. Ekip bir adresi array'in içinde, sırasını bilmeden güncellemek ister. "
                 "Saniyede 12.000 profil okuması, 150 yazma; sabah ve akşam tepe. Her okuma 10 ms'nin altında olmalı. Beş geliştirici, uygulama zaten MongoDB driver'ı ile yazılmış; sunucu istenmiyor."),
        reqs=[
            req(True, "\"Bu kullanıcı id'sinin profili\" tek okuma. Array'in içindeki bir adresi (\"label'ı iş olan adres\") sırasını bilmeden tek yazmada değiştirmek. Profilin içine göre, haftada birkaç kez değişen sorular (\"İstanbul'da oturan ve podcast isteyen\") yeni tasarım istemeden cevaplanmalı.",
                      "Her ekran bu okumayla başlar. Array içi güncelleme için profilin tamamını yeniden yazmak başka bir cihazdan gelen değişikliği ezer. Pazarlamanın her yeni sorusu için bir index projesi açılırsa kampanya takvimi kayar."),
            req(True, "Saniyede 12.000 okuma ve 150 yazma; sabah 8 ve akşam 21 tepe. Okuma 10 ms'nin altında. Kullanıcı sayısı yılda yüzde 50 artıyor.",
                      "Okuma hacmi yazmanın seksen katıdır; ölçek okuma tarafındadır. Büyüme için her yıl yeniden tasarım yapılamaz."),
            req(False, "Profil kalıcıdır; kaybı kullanıcıyı adres ve tercihlerini yeniden girmeye zorlar. Bir AZ arızasında kayıp olmamalı.",
                       "Profil kaybı destek talebi ve güven kaybıdır; para kaybı değildir."),
            req(False, "Beş geliştirici, kod zaten MongoDB driver'ı ile yazılmış. Yeni field migration istemeden eklenmeli. Sunucu, yama ve failover istenmiyor.",
                       "Driver'ı ve sorgu dilini değiştirmek uygulamanın veri katmanını yeniden yazmaktır; küçük ekipte bu aylarca sürer."),
            req(False, "Okuma ağırlıklı, gün içinde iki tepe. Kapasite başına ya da istek başına ikisi de uyar. Profil küçük (10 KB'tan az).",
                       "İki tepe arasında düşük trafikte boş kapasite ödemek istenmez; büyümede maliyet sıçramamalı."),
        ],
        cands=["doc", "ddb", "aur"],
        scores={
            "doc": [sc(9, "Profil tek bir document (Ö2), _id ile tek okuma (Ö1). \"label'ı iş olan adres\" updateOne ile $set ve arrayFilters kullanılarak array'in sırası bilinmeden değiştirilir (Ö5). \"İstanbul'da oturan ve podcast isteyen\" dot notation ile bir filtredir (Ö3) ve addresses.city ile prefs.podcast üzerine index kurulur (Ö4). 1 puan kırıldı: haftada değişen her yeni soru için bir index kurulur; index kurulana kadar soru üç milyon profilde bir COLLSCAN'dir ve replica'ya yönlendirilmelidir."),
                    sc(8, "12.000 okuma replica'lara dağılır (Ö8), serverless DCU tepe saatlerde büyür. 2 puan kırıldı: replica sayısı ve DCU aralığı ekip tarafından seçilir; bütün yazmalar tek primary'den geçer ve yüzde 50 büyüme her yıl bir gözden geçirmedir."),
                    sc(10, "Üç AZ'de altı kopya, sürekli yedek, otomatik failover. Puan kırılmadı."),
                    sc(9, "Kod değişmez: aynı driver, aynı sorgular. Yeni field migration istemez. Yedek, yama, failover yönetilir. 1 puan kırıldı: replica sayısını, DCU aralığını ve index'lerin büyüklüğünü ekip izler."),
                    sc(8, "Serverless DCU-saat tepe saatlerde büyür, gece 0,5 DCU'ya iner; ya da iki instance saat başına. 2 puan kırıldı: gece de minimum kapasite ve I/O ödenir; profil içi her yeni index yazma I/O'sunu artırır.")],
            "ddb": [sc(8, "Simple primary key = kullanıcı id'si, GetItem tek okumadır; UpdateItem bir document yolunu (SET prefs.podcast = :v) değiştirir. 2 puan kırıldı: \"label'ı iş olan adres\" liste içinde index numarasıyla güncellenir, uygulama önce okuyup sırayı bulur; \"İstanbul'da oturan ve podcast isteyen\" gibi value içi sorular her biri için bir GSI ister ve haftada değişen sorular için GSI kurulamaz."),
                    sc(10, "Okumalar partition'lara dağılır; 12.000 okuma on-demand ile kendiliğinden karşılanır, tek haneli milisaniye. Puan kırılmadı."),
                    sc(10, "Birkaç AZ'de saklanır, point-in-time recovery. Puan kırılmadı."),
                    sc(7, "Serverless, migration yok. 3 puan kırıldı: kod MongoDB driver'ı ile yazılmış; DynamoDB'ye geçmek sorguları ve veri erişim katmanını yeniden yazmaktır (gereksinim: \"aylarca sürer\"); bu, Aurora'nın aynı gerekçeyle kaybettiği 3 puandır."),
                    sc(8, "İstek başına ödeme, gece sıfıra yakın. 2 puan kırıldı: 10 KB'a yaklaşan profil okuma başına birkaç birim tüketir; GSI'lar her yazmaya birim ekler.")],
            "aur": [sc(8, "Profil JSONB bir kolonda; jsonb_set iç içe field'ı değiştirir; GIN index içine göre sorguyu karşılar. 2 puan kırıldı: array içindeki tek bir elemanı koşula göre değiştirmek JSONB'de zahmetlidir ve row'un tamamı yeniden yazılır; adresler ayrı table olursa profil bir JOIN'dir."),
                    sc(7, "Reader instance'lar 12.000 okumayı taşır. 3 puan kırıldı: reader sayısı ve ACU aralığı ekibin kararıdır; büyüme bir kapasite projesidir."),
                    sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                    sc(7, "Yönetilen servis. 3 puan kırıldı: kodun driver'ı ve sorgu dili değişir; JSONB dışı field ALTER TABLE'dır."),
                    sc(7, "ACU-saat, 0,5 ACU minimum. 3 puan kırıldı: gece de minimum kapasite; reader ayrıca ödenir.")],
        },
        h2h={
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Bu, okuyucunun en çok \"neden o değil?\" dediği yarıştır, çünkü DynamoDB sayfasındaki profil kartı tam tersini verdi: orada DynamoDB 47, DocumentDB 42 idi. Fark iş yükündedir. Orada tek access pattern \"id ile profil\" idi ve profilin içine göre soru yoktu; burada pazarlama profilin içine göre haftada değişen sorular soruyor ve ekip array'in içindeki bir adresi sırasını bilmeden değiştirmek istiyor. "
                      "DynamoDB'nin gücü R2'de görünür: 12.000 okuma ve büyüme için hiçbir boyutlandırma yoktur ve bütün yazmalar tek bir primary'den geçmez. DocumentDB'nin gücü R1'dedir: arrayFilters ile array içi güncelleme, dot notation ile içe göre filtre ve o filtreye index. "
                      "Bu iş yükünde document seçilir, çünkü profilin içine göre sorular ana iştir ve kod zaten MongoDB driver'ı ile yazılmıştır. Bir puanlık fark tek başına bir karar değildir: kod MongoDB ile yazılmamış olsaydı DynamoDB'nin R4'ü 9 olurdu, DynamoDB bir puanla öne geçerdi ve karar R2'nin boyutlandırmasız ölçeğine kalırdı. "
                      "Hangi koşul değişseydi DynamoDB seçilirdi: profilin içine göre sorular sabit üç soruya inseydi (her biri bir GSI), array içi güncelleme nadir olsaydı ve okuma hacmi saniyede yüz binlere çıksaydı."),
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinimler R1'in array kısmı, R2 ve R4. Aurora'nın gücü profil başka ilişkisel verilerle birlikte sorgulanacaksa görünür: abonelik faturaları ve ödeme yöntemleri aynı database'de ise \"aboneliği biten ve bildirim isteyen kullanıcılar\" bir JOIN'dir; JSONB kolonu profilin esnek kısmını taşır ve GIN index içine göre sorguyu karşılar. "
                      "Ama bu iş yükünde profil tek başına okunup yazılır; array içindeki bir adresi koşula göre değiştirmek JSONB'de zahmetlidir ve row'un tamamı yeniden yazılır; kod MongoDB driver'ı ile yazılmıştır ve SQL'e geçiş uygulamanın veri katmanını yeniden yazmaktır. "
                      "Bu yüzden document seçilir. Hangi koşul değişseydi Aurora seçilirdi: profil abonelik ve ödeme verisiyle aynı transaction'da güncellenseydi, raporlar profil field'larına JOIN ile sorulsaydı ya da uygulama zaten SQL üzerinde kurulu olsaydı."),
        },
        verdict=_t("Karar: DocumentDB 44, DynamoDB 43, Aurora 39. Yakın bir yarış: iki aday da R3'ü tam karşılar; yarışı R1 (profilin içine göre değişen sorular ve array içi güncelleme) ve R4 (kod MongoDB driver'ı ile yazılmış) DocumentDB'ye, R2 DynamoDB'ye çeker. "
                   "Yine de document seçersek artımız: kod değişmez, arrayFilters ile array içi güncelleme, içe göre her soru bir filtre ve bir index, yeni field migration'sız. "
                   "Potansiyel eksimiz: replica ve DCU aralığı ekibin kararıdır; pazarlamanın index'siz sorusu COLLSCAN'dir ve primary'yi yorar, bu sorular replica'ya yönlendirilmelidir; bütün yazmalar tek primary'den geçer. Bir koşul değişseydi: içe göre sorular üç sabit soruya inseydi DynamoDB kazanırdı.")),

    # ------------------------------------------------------------------ 3. content management: articles with blocks (card only)
    usecase("cms", 3,
        title=_t("İçerik yönetimi: makale ve blokları"),
        key=_t("Collection: articles. Document: _id, title, slug, status, authors (array), blocks (array: paragraf, görsel, alıntı), tags (array)."),
        story=_t("Bir yayın sitesinin editör ekibi günde 300 makale yayımlar; arşivde 2 milyon makale var. Bir makale sıralı bloklardan oluşur: paragraf, görsel, alıntı, gömülü video; her blok türünün field'ları farklıdır ve editör blokları sürükleyip sıralar. "
                 "Makale sayfası makaleyi bütün bloklarıyla tek seferde ister; editör bir bloğu düzenlediğinde sadece o blok değişmeli. Sorular: \"slug ile makale\", \"etiketi ekonomi olan yayımlanmış makaleler, tarihe göre\", \"bu yazarın taslakları\". "
                 "Saniyede 3.000 okuma (önünde CDN var), saniyede 5 yazma. Makale resmi içeriktir; yayımlanmış bir makale kaybolamaz ve eski sürümleri geri getirilebilmeli. Üç geliştirici, Node.js ve MongoDB driver'ı biliyor; görseller S3'te, makalede sadece key'i var."),
        reqs=[
            req(True, "slug ile tek okumada makale ve bütün blokları. Tek bir bloğu, array'deki sırası ne olursa olsun, tek yazmada değiştirmek. Etiket (array) ve durum field'ına göre, tarihe göre sıralı liste. Blok türleri farklı field'lar taşır; yeni blok türü migration istememeli.",
                      "Makale parçalardan toplanırsa her sayfa birkaç okumadır; blok için bütün makaleyi yeniden yazmak iki editörün değişikliğini çarpıştırır. Yeni blok türü için schema değişikliği ürün takvimini kilitler."),
            req(True, "Saniyede 3.000 okuma (CDN arkasında), 5 yazma. Makale sayfası 30 ms'nin altında. Arşiv 2 milyon makale, yılda 100.000 artıyor.",
                      "Okuma hacmi küçük ve düz; ölçek burada belirleyici değildir ama arşiv büyüdükçe etiket sorgusu yavaşlamamalıdır."),
            req(True, "Yayımlanmış makale kaybolamaz; bir AZ arızasında kayıp olmamalı ve yanlış bir silme geri alınabilmeli. Eski sürümler saklanmalı. Bu kartta dayanıklılık zorunludur.",
                       "Yayımlanmış içerik yayıncının ürünüdür; kaybolan makale okuyucuya ve reklam verene karşı yükümlülüktür."),
            req(False, "Üç geliştirici, Node.js ve MongoDB driver'ı biliyor. Yeni blok türü kodda eklenmeli. Sunucu, yama, yedek istenmiyor.",
                       "Küçük ekipte database operasyonu ürün geliştirmeden çalınan zamandır."),
            req(False, "Düz, okuma ağırlıklı, küçük yazma. Kapasite başına ödeme uyar; veri birkaç on GB (görseller hariç).",
                       "Düz trafikte sabit kapasite öngörülebilir ve ucuzdur; sıçrama istenmez."),
        ],
        cands=["doc", "ddb", "aur"],
        scores={
            "doc": [sc(10, "Makale bir document, bloklar bir array (Ö2); slug üzerinde unique index ile tek okuma (Ö1, Ö4). Tek blok updateOne ile $set ve arrayFilters ile değişir (Ö5). tags array'i multikey index alır (Ö4), { status: 1, published_at: -1 } compound index listeyi sıralı verir (Ö3), { authors: 1, status: 1 } \"bu yazarın taslakları\" sorusunu karşılar. Yeni blok türü sadece yeni document'larda görünür. Puan kırılmadı."),
                    sc(9, "3.000 okuma replica'lara dağılır (Ö8); 5 yazma küçüktür. 1 puan kırıldı: instance sınıfı ve replica sayısı önceden seçilir."),
                    sc(9, "Üç AZ'de altı kopya, point-in-time restore; sürümler ayrı bir collection'da saklanır (büyüyen array için ayrı collection, A3). 1 puan kırıldı: sürüm geçmişini database değil uygulama yazar ve korur."),
                    sc(8, "Aynı driver, aynı dil; yedek, yama ve failover yönetilir. 2 puan kırıldı: index planı ve instance boyutu ekibin işidir; 16 MiB sınırı için sürüm geçmişi makalenin içinde değil ayrı collection'da tutulur."),
                    sc(8, "İki instance saat başına ya da serverless, I/O ayrıca. 2 puan kırıldı: gece de minimum kapasite ödenir; her yazma beş index'i (_id, slug, tags, status ve published_at, authors ve status) günceller ve I/O olarak sayılır.")],
            "ddb": [sc(6, "Partition key slug, item makale; bloklar bir liste attribute'u. 4 puan kırıldı: tek bloğu güncellemek liste index numarası ister, uygulama önce okur; \"etiketi ekonomi olan, tarihe göre\" her etiket için ayrı item'lar ve bir GSI ister; 400 KB item sınırı bloklu uzun makaleyi zorlar."),
                    sc(10, "Okuma ve yazma kendiliğinden ölçeklenir. Puan kırılmadı."),
                    sc(9, "Birkaç AZ, point-in-time recovery. 1 puan kırıldı: sürüm geçmişini uygulama ayrı item'larda yazar ve korur."),
                    sc(8, "Serverless, migration yok. 2 puan kırıldı: ekip SDK'yı ve key tasarımını öğrenir; etiket sorguları için tasarım adımı gerekir."),
                    sc(8, "İstek başına, düşük. 2 puan kırıldı: 400 KB'a yaklaşan makale okuma başına çok birim tüketir; etiket GSI'ları yazma birimi ekler.")],
            "aur": [sc(7, "articles, blocks, article_tags table'ları ya da JSONB bloklar. 3 puan kırıldı: bloklar ayrı table ise makale bir JOIN ve sıralama işidir; JSONB ise tek blok güncellemesi row'un tamamını yeniden yazar; yeni blok türü table modelinde migration'dır."),
                    sc(9, "3.000 okuma index ile; 5 yazma küçük. 1 puan kırıldı: reader ve ACU kararı ekibindir."),
                    sc(9, "Üç AZ'de altı kopya, point-in-time restore. 1 puan kırıldı: sürüm geçmişini uygulama ayrı bir table'da yazar."),
                    sc(7, "Yönetilen. 3 puan kırıldı: ekip SQL'i az biliyor; driver ve sorgular değişir; migration disiplini."),
                    sc(7, "ACU-saat, 0,5 minimum. 3 puan kırıldı: gece de minimum; reader ayrıca.")],
        },
        h2h={
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinim R1. DynamoDB'nin gücü R2 ve R5'te: 3.000 okuma ve 2 milyon makale için hiçbir boyutlandırma yoktur, gece ödeme sıfıra yakındır. "
                      "Ama makale derin bir yapıdır: sıralı bloklar, her blokta farklı field'lar, etiket listesi. DynamoDB'de bir bloğu değiştirmek listedeki numarasını bilmeyi ister; \"etiketi ekonomi olan, tarihe göre\" sorusu için etiketler ayrı item'lara açılır ve bir GSI kurulur; 400 KB sınırı uzun makaleleri parçalamaya zorlar. DocumentDB'de blok arrayFilters ile bulunur, tags multikey index alır ve 16 MiB sınırı rahattır. "
                      "Bu iş yükünde document seçilir, çünkü içerik iç içe ve array'li bir belgedir ve ekip MongoDB driver'ı ile çalışıyor. "
                      "Hangi koşul değişseydi DynamoDB seçilirdi: makale düz bir metin ve birkaç field olsaydı, etiket sorgusu arama servisine verilseydi ve okuma hacmi saniyede yüz binlere çıksaydı."),
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinimler R1 ve R4. Aurora'nın gücü, makale yazar, abonelik ve ödeme gibi ilişkili verilerle aynı database'de sorgulanacaksa görünür; blocks ve article_tags table'ları ile her soru bir SQL'dir ve foreign key yazarın varlığını korur. "
                      "Ama bloklar sıralı ve türe göre farklı field'lıdır: table modelinde her blok türü için kolon ya da migration gerekir, JSONB modelinde tek blok güncellemesi row'un tamamını yeniden yazar ve array içi koşullu güncelleme zahmetlidir. Ekip SQL'i az biliyor. "
                      "Bu yüzden document seçilir. Hangi koşul değişseydi Aurora seçilirdi: makale abonelik ve ödeme verisiyle aynı transaction'da güncellenseydi, editöryal raporlar JOIN ile sorulsaydı ya da ekip SQL ekibi olsaydı."),
        },
        verdict=_t("Karar: DocumentDB 44, DynamoDB 41, Aurora 39. Yarışı R1 belirler: sıralı ve türe göre farklı bloklar, array içi tek blok güncellemesi, etiket array'ine index. "
                   "Yine de document seçersek artımız: makale tek document, blok arrayFilters ile değişir, tags multikey index'li, yeni blok türü migration'sız, sürümler ayrı collection'da. "
                   "Potansiyel eksimiz: sürüm geçmişi makale içinde tutulursa document büyür (16 MiB); instance ve index kararları ekibindir; görsel dosyaları S3'te kalmalıdır. Bir koşul değişseydi: makale düz metin ve birkaç field olsaydı DynamoDB yarışa girerdi.")),

    # ------------------------------------------------------------------ 4. event logs with flexible schema (clear loss: DynamoDB wins)
    usecase("events", 4, sim="lose_events", kind="lose",
        title=_t("Esnek şemalı event log'ları: tıklama ve uygulama olayları"),
        key=_t("Her event bir document: event_type, user_id, ts, payload (türe göre farklı). Sadece eklenir, 30 gün saklanır."),
        story=_t("Bir mobil uygulama her kullanıcı eyleminde bir event yazar: ekran açıldı, ürün görüntülendi, sepete eklendi. Her event türünün payload'ı farklıdır ve ürün ekibi her hafta yeni bir event türü ekler. "
                 "Saniyede 20.000 event, kampanya gecesi 80.000; her event 1 KB. Event hiç güncellenmez, sadece eklenir; 30 gün sonra silinmelidir. Sorular: \"bu kullanıcının son 100 event'i\", \"bu event türünün son bir saati\"; analiz ekibi günlük kopyayı data warehouse'a alır. "
                 "Kaybolan birkaç event kabul edilir (istatistik), ama toplu kayıp kabul edilmez. Üç geliştirici, MongoDB API'sini biliyor ve ilk tercihleri mevcut DocumentDB cluster'ına bir collection eklemek; sunucu boyutlandırmak istemiyorlar."),
        reqs=[
            req(True, "Yazma: saniyede 20.000 ekleme, türe göre farklı payload, yeni tür migration'sız. Okuma: \"bu kullanıcının son 100 event'i\" ve \"bu türün son bir saati\" zaman sırasıyla. 30 gün sonra otomatik silme. Güncelleme yok.",
                      "Event yazması uygulamanın her isteğinin içindedir; yavaşlarsa uygulama yavaşlar. Silme işlemi elle yapılırsa storage ve fatura sınırsız büyür."),
            req(True, "Saniyede 20.000 yazma, tepe 80.000; günde 1,7 milyar event, 30 günde 50 milyar event ve 50 TB. Yazma 10 ms'nin altında. Okumalar seyrek (saniyede 200).",
                      "Bu bir yazma ölçeği problemidir: tek bir yazma düğümünün sınırı aşılır. Tepe gecesi yazma reddedilirse event'ler kaybolur."),
            req(False, "Birkaç event kaybı kabul; toplu kayıp (bir saat) kabul değil. Veri 30 gün sonra zaten silinir.",
                       "İstatistik için tek tek kayıp görünmez; bir saatlik boşluk raporları bozar."),
            req(False, "Üç geliştirici, MongoDB API'sini biliyor. Sunucu boyutlandırmak ve shard yönetmek istenmiyor. Yeni event türü kodda bir satır olmalı.",
                       "Yazma tepesi için instance büyütmek bir gece operasyonudur; ekip bunu istemiyor."),
            req(False, "Yazma ağırlıklı, 30 günlük pencere, kampanya tepesi. Kullanım başına ödeme ve silmenin bedava olması istenir.",
                       "50 TB'lık pencere için storage ve silme I/O'su faturanın büyük kalemidir; tepe için bütün ay kapasite ödenmek istenmez."),
        ],
        cands=["doc", "ddb", "os"],
        scores={
            "doc": [sc(7, "Event bir document, payload serbest (Ö2); { user_id: 1, ts: -1 } compound index ile \"son 100 event\" IXSCAN'dir (Ö4); TTL index 30 günlük silmeyi yapar. 3 puan kırıldı: TTL silmesi \"best effort\", belirli bir sürede garanti değildir ve her silme I/O olarak faturalanır; AWS bu iş yükü için TTL yerine haftalık collection'lar açıp drop etmeyi önerir, bu da uygulama tarafında ek iştir."),
                    sc(4, "Bütün yazmalar tek primary instance'tan geçer (Ö8'in sınırı); saniyede 20.000 ve tepe 80.000 ekleme için en büyük instance sınıfı ya da elastic cluster (shard) gerekir. 6 puan kırıldı: instance-based cluster bu hacimde tek primary ile sınırlıdır; elastic cluster shard yönetimi ve shard key tasarımı ister; 50 TB storage ve her ekleme için index yazması I/O olarak sayılır."),
                    sc(10, "Üç AZ'de altı kopya; yazma çoğunluğa kalıcı yazılmadan onaylanmaz. Dayanıklılık istenenden fazladır; bedeli R2 ve R5'te sayıldı. Puan kırılmadı."),
                    sc(6, "Ekip API'ı biliyor; yedek ve yama yönetilir. 4 puan kırıldı: tepe için instance büyütme ya da elastic cluster'da shard sayısı ekibin operasyonudur; TTL yerine collection döndürme işi kodda yaşar."),
                    sc(4, "Instance saat başına, I/O ve storage ayrıca. 6 puan kırıldı: tepe gecesi için büyük instance bütün ay ödenir; 50 TB storage, her ekleme için index I/O'su ve TTL silme I/O'su faturayı büyütür; silme bedava değildir.")],
            "ddb": [sc(8, "Partition key user_id, sort key ts; \"son 100 event\" ters sıralı bir Query; value şemasızdır, payload serbesttir; TTL attribute'u 30 günü işaretler. 2 puan kırıldı: \"bu türün son bir saati\" için event_type üzerine bir GSI gerekir ve TTL silmesi \"within a few days\", kesin değildir; süresi dolan event okuma filtresi ister."),
                    sc(10, "Yazmalar partition'lara dağılır; on-demand 80.000 yazma/saniyeyi kendiliğinden karşılar, tek haneli milisaniye. Puan kırılmadı."),
                    sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                    sc(9, "Serverless: sunucu, shard, yama yok; yeni event türü sadece yeni item'a yazılır. 1 puan kırıldı: ekip MongoDB API'sinden SDK'ya geçer ve key tasarımını öğrenir."),
                    sc(9, "İstek başına ödeme, TTL silmesi yazma kapasitesi tüketmez, storage GB başına. 1 puan kırıldı: 80.000 yazma/saniyede on-demand birimleri faturanın ana kalemidir; düz kısım için provisioned kapasite düşünülür.")],
            "os": [sc(9, "Event bir JSON document; zaman sıralı sorgular ve türe göre filtre index'in doğal işidir; index'ler günlük döner (rollover) ve 30 gün sonra index silinir, bedava. 1 puan kırıldı: \"bu kullanıcının son 100 event'i\" index'ler arası arama ister ve refresh aralığı yüzünden event birkaç saniye geç görünür."),
                   sc(8, "20.000 yazma/saniye bulk ile karşılanır; shard'lar yazmayı dağıtır. 2 puan kırıldı: tepe için node ve shard sayısı önceden planlanır; 50 TB için büyük bir domain gerekir."),
                   sc(6, "Replica shard'lar node arızasını karşılar. 4 puan kırıldı: arama index'i kayıt sistemi değildir; domain kaybı event'lerin kaybıdır ve kaynak başka yerde durmalıdır."),
                   sc(7, "Yönetilen domain, rollover ve ISM politikaları. 3 puan kırıldı: mapping, shard planı ve node boyutu ekibin işidir; ekip OpenSearch bilmiyor."),
                   sc(7, "Node saat başına, storage node'da. 3 puan kırıldı: 50 TB için büyük domain bütün ay ödenir; silme bedavadır.")],
        },
        h2h={
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinimler R2, R4 ve R5. DocumentDB'nin gücü şekilde ve ekipte görünür: event serbest payload'lı bir document'tır, payload içine göre sorgu doğrudan mümkündür, ekip API'ı biliyor ve mevcut cluster'a bir collection eklemek bir günlük iştir; ama R1'de bile TTL silmesinin zamanı garanti olmadığı için DynamoDB'nin bir puan gerisindedir. "
                      "Ama bu iş yükü bir yazma ölçeği problemidir: saniyede 20.000, tepe 80.000 ekleme. Instance-based cluster'da bütün yazmalar tek primary'den geçer; elastic cluster yazmayı shard'lara dağıtır ama shard key ve shard sayısı ekibin operasyonudur. DynamoDB yazmayı partition'lara kendiliğinden dağıtır, TTL silmesi yazma kapasitesi tüketmez ve istek başına öder. "
                      "Bu kart document kategorisinin sınırını gösterir: esnek şema document database'i çağırır, ama yazma hacmi ve otomatik silme key-value'yu seçtirir. Şekil document'a uyar, ama yazma hacmi onu dışarıda bırakır. "
                      "Hangi koşul değişseydi DocumentDB seçilirdi: yazma hacmi saniyede birkaç bine inseydi, event'ler payload içine göre sorgulansaydı (\"ödeme hatası veren event'lerin cihaz modeli\") ve 30 günlük silme haftalık collection'larla kabul edilseydi."),
            "os": _t("Search engine (OpenSearch) ile kafa kafaya. Ayrıştığı gereksinimler R1'in sorgu kısmı, R3 ve R4. OpenSearch'ün gücü log'lardadır: event'ler günlük index'lere yazılır, 30 gün sonra index bedavaya silinir, \"bu türün son bir saati\" ve payload içinde herhangi bir field'a göre filtre index'in doğal işidir ve dashboard'lar hazırdır. "
                      "Ama kayıt sistemi değildir: domain kaybı event'lerin kaybıdır ve kaynak başka bir yerde durmalıdır; mapping ve shard planı ekibin işidir; \"bu kullanıcının son 100 event'i\" birçok günlük index'te arama ister. DynamoDB kalıcı kayıt, kendiliğinden ölçek ve TTL verir. "
                      "Bu iş yükünde OpenSearch ikinci sıradadır ve çoğu zaman DynamoDB'nin yanında bir analiz kopyası olarak durur. "
                      "Hangi koşul değişseydi OpenSearch seçilirdi: ana iş payload içinde serbest arama ve dashboard olsaydı, event'ler başka bir kalıcı yerde (S3) zaten saklansaydı ve kullanıcı başına zaman sıralı okuma istenmeseydi."),
        },
        verdict=_t("Karar: DynamoDB 46, OpenSearch 37, DocumentDB 31. Net bir kaybetme: DocumentDB gerçek bir adaydır (esnek payload, ekip API'ı biliyor) ama R2 belirler: tek primary'den geçen yazmalar saniyede 80.000 eklemeyi taşımaz ve TTL silmesi I/O olarak ödenir. "
                   "Yine de document seçersek artımız: mevcut cluster'a bir collection, aynı driver, payload içine göre sorgu. "
                   "Potansiyel eksimiz: en büyük instance ya da elastic cluster shard yönetimi, 50 TB storage ve silme I/O'su, tepe gecesi reddedilen yazmalar. Bir koşul değişseydi: yazma hacmi saniyede birkaç bine inseydi ve payload içine göre sorgu ana iş olsaydı DocumentDB yarışa girerdi.")),

    # ------------------------------------------------------------------ 5. IoT device configurations (card only)
    usecase("devices", 5,
        title=_t("IoT cihaz kayıtları ve konfigürasyonları"),
        key=_t("Collection: devices. Document: _id (seri no), model, firmware, settings (modele göre iç içe), sensors (array), location."),
        story=_t("Bir akıllı termostat üreticisinin sahada 800.000 cihazı var. Her cihazın bir kayıt document'ı vardır: model, firmware sürümü, modele göre farklı ayarlar (ısı eğrisi, sensör listesi), kurulum adresi, sahip. "
                 "Destek ekibi herhangi bir field'a göre arar: \"firmware'i 2.3'ten eski ve İzmir'de olan cihazlar\", \"sensör listesinde nem sensörü olanlar\". Cihaz kendi ayarını saatte bir okur; ürün ekibi her sürümde ayar şekline yeni field'lar ekler. "
                 "Saniyede 300 okuma, 20 yazma; telemetri (saniyede 50.000 ölçüm) bu kartın dışında, bir time series database'inde. İki geliştirici, MongoDB API'sini biliyor. Kayıt kaybolursa cihaz fabrika ayarına döner ve müşteri arar."),
        reqs=[
            req(True, "Seri no ile tek okumada bütün kayıt. Destek ekibinin herhangi bir field'a ve iç içe listeye göre, önceden bilinmeyen soruları. Modele göre farklı ayar şekli; yeni sürümde yeni field'lar migration'sız. Tek bir ayarı değiştirmek bütün kaydı yeniden yazmamalı.",
                      "Destek sorusu için bütün kaydı okuyan bir tarama 800.000 cihazda yavaştır; migration her firmware sürümünü database projesine çevirir."),
            req(True, "Saniyede 300 okuma, 20 yazma; cihaz sayısı yılda iki katına çıkıyor. Okuma 20 ms'nin altında.",
                      "Hacim küçüktür; burada ölçek değil sorgu esnekliği belirleyicidir."),
            req(False, "Kayıt kalıcıdır; kaybı cihazı fabrika ayarına düşürür. Bir AZ arızasında kayıp olmamalı.",
                       "Kayıp destek çağrısı ve müşteri memnuniyetsizliğidir; para kaybı dolaylıdır."),
            req(False, "İki geliştirici, MongoDB API'sini biliyor. Sunucu, yama, yedek istenmiyor. Yeni ayar field'ı kodda eklenmeli.",
                       "İki kişilik ekipte operasyon ürünü durdurur."),
            req(False, "Düşük ve düz trafik. En düşük sabit maliyet istenir; veri küçük (birkaç GB).",
                       "Küçük iş yükünde fatura kapasitenin alt sınırıyla belirlenir."),
        ],
        cands=["doc", "ddb", "aur"],
        scores={
            "doc": [sc(10, "Kayıt bir document, settings modele göre iç içe (Ö2); _id = seri no ile tek okuma (Ö1). Destek ekibinin önceden bilinmeyen soruları find ile her field'da çalışır (Ö3); sık olanlara index kurulur, sensör listesi multikey index alır (Ö4). Tek ayar $set ile değişir (Ö5). Puan kırılmadı."),
                    sc(9, "300 okuma ve 20 yazma tek primary ve bir replica ile rahattır (Ö8). 1 puan kırıldı: index'siz destek sorusu COLLSCAN'dir ve replica'ya yönlendirilmelidir; büyüme bir instance kararıdır."),
                    sc(10, "Üç AZ'de altı kopya, point-in-time restore. Puan kırılmadı."),
                    sc(9, "Aynı API, yedek ve yama yönetilir, yeni field migration'sız. 1 puan kırıldı: instance sınıfı ve index planı ekibindir."),
                    sc(8, "Serverless 0,5 DCU'ya iner ya da iki küçük instance. 2 puan kırıldı: iki instance gece de ödenir; küçük iş yükünde istek başına ödemeden pahalı olabilir.")],
            "ddb": [sc(7, "Partition key seri no, GetItem tek okuma; value şemasız. 3 puan kırıldı: destek ekibinin önceden bilinmeyen soruları key ile sorulamaz; her sık soru için GSI, nadir soru için Scan gerekir; iç içe listeye göre filtre Scan + filter'dır."),
                    sc(10, "Ölçek kendiliğinden. Puan kırılmadı."),
                    sc(10, "Birkaç AZ. Puan kırılmadı."),
                    sc(8, "Serverless. 2 puan kırıldı: ekip API değiştirir ve destek soruları için tasarım adımı gerekir."),
                    sc(9, "İstek başına, düşük trafikte sıfıra yakın. 1 puan kırıldı: destek Scan'leri okunan her item için öder.")],
            "aur": [sc(8, "devices table'ı, settings JSONB; her soru SQL'dir, GIN index içe göre sorguyu karşılar. 2 puan kırıldı: modele göre farklı ayarlar JSONB'de yaşar ve JSONB içi filtre özel operatör ister; tek ayar güncellemesi row'u yeniden yazar."),
                    sc(9, "Küçük hacim. 1 puan kırıldı: ACU aralığı ekibin kararıdır."),
                    sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                    sc(7, "Yönetilen. 3 puan kırıldı: ekip SQL'e geçer; driver değişir."),
                    sc(7, "0,5 ACU minimum. 3 puan kırıldı: gece de minimum kapasite; I/O ayrıca.")],
        },
        h2h={
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinim R1'in sorgu kısmı. DynamoDB'nin gücü R2 ve R5'te görünür: 800.000 kayıt ve yılda iki kat büyüme için hiçbir boyutlandırma yoktur ve düşük trafikte ödeme sıfıra yakındır; cihazın kendi ayarını seri no ile okuması tam bir key-value işidir. "
                      "Ama destek ekibi önceden bilinmeyen sorular sorar ve iç içe listeye göre filtreler; DynamoDB'de her yeni soru bir GSI ya da bir Scan'dir, DocumentDB'de bir filtredir ve gerekirse bir index. "
                      "Bu iş yükünde document seçilir, çünkü sorgu esnekliği ana iştir ve hacim küçüktür. Telemetri bu kartın dışındadır; iki servis birlikte doğru cevaptır: kayıt DocumentDB'de, ölçümler time series database'inde. "
                      "Hangi koşul değişseydi DynamoDB seçilirdi: tek soru \"seri no ile kayıt\" olsaydı, destek soruları ayrı bir arama servisine verilseydi ve cihaz sayısı on milyonlara çıksaydı."),
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinimler R1'in şekil kısmı ve R4. Aurora'nın gücü, cihaz kaydı müşteri, sözleşme ve servis talebi gibi ilişkili verilerle aynı database'de sorgulanacaksa görünür; JSONB ve GIN index ayar şeklinin esnek kısmını da taşır ve her destek sorusu bir SQL'dir. "
                      "Ama ayarlar modele göre farklıdır ve her sürümde yeni field gelir; bu veri JSONB'ye yığılınca schema'nın avantajı kalmaz ve iç içe filtreler özel operatör ister. Ekip MongoDB API'sini biliyor, SQL'e geçiş driver ve sorgu değişikliğidir. "
                      "Bu yüzden document seçilir. Hangi koşul değişseydi Aurora seçilirdi: cihaz kaydı müşteri ve sözleşme table'larıyla JOIN ile sorulsaydı, ayarlar modele göre değil sabit kolonlar olsaydı ya da ekip SQL ekibi olsaydı."),
        },
        verdict=_t("Karar: DocumentDB 46, DynamoDB 44, Aurora 41. Yarışı R1'in sorgu kısmı belirler: önceden bilinmeyen, iç içe field'lara göre destek soruları. "
                   "Yine de document seçersek artımız: kayıt tek document, modele göre ayar şekli serbest, her soru bir filtre, aynı API. "
                   "Potansiyel eksimiz: index'siz destek sorusu COLLSCAN'dir ve primary'yi yorabilir (replica'ya yönlendirilir); iki instance gece de ödenir; telemetri bu database'e yazılmamalıdır. Bir koşul değişseydi: destek soruları ayrı bir arama servisine verilseydi DynamoDB kazanırdı.")),

    # ------------------------------------------------------------------ 6. mobile app sync (card only)
    usecase("sync", 6,
        title=_t("Mobil uygulama senkronizasyonu: liste document'ları"),
        key=_t("Collection: lists. Document: _id, owner, title, items (array), updated_at, version. Change stream ile cihazlara yayın."),
        story=_t("Bir alışveriş listesi uygulamasının 2 milyon kullanıcısı var; her kullanıcı birkaç cihazdan aynı listeyi düzenler. Liste bir document'tır: başlık, öğeler array'i (metin, işaretli mi, sıra), son değişiklik zamanı, sürüm numarası. "
                 "Cihaz çevrimdışıyken değişiklik yapar, bağlanınca gönderir; sunucu sürüm numarasına bakarak eski bir yazmayı reddeder ve öğeyi array'in içinde değiştirir. Diğer cihazlar değişikliği saniyeler içinde almalıdır. "
                 "Saniyede 4.000 okuma, 1.500 yazma (her yazma tek öğe); 200 milyon document. Uygulamanın API'si JSON'dur ve ekip MongoDB driver'ı kullanıyor. Kaybolan bir liste kullanıcı için kayıp veridir. Altı geliştirici, sunucu istemiyor."),
        reqs=[
            req(True, "\"Bu kullanıcının listeleri, son değişikliğe göre\" ve _id ile tek liste. Array'deki tek öğeyi \"version = 7 ise\" koşuluyla tek yazmada değiştirmek; koşul yanlışsa yazmamak. Değişiklikler diğer cihazlara saniyeler içinde akmalı.",
                      "Koşulsuz yazma iki cihazın değişikliğini çarpıştırır ve biri kaybolur. Değişikliğin akışı için collection'ı her saniye sorgulamak 200 milyon document'ta mümkün değildir."),
            req(True, "Saniyede 4.000 okuma, 1.500 yazma; 200 milyon document, yılda yüzde 40 artıyor. Yazma 15 ms'nin altında.",
                      "1.500 yazma tek bir primary'nin rahat taşıdığı bir hacimdir; ama yılda yüzde 40 büyüme bunu birkaç yılda tek primary'nin sınırına taşır ve büyüme planlanmalıdır."),
            req(True, "Liste kullanıcının verisidir; kayıp kabul edilmez. Bir AZ arızasında kayıp ve uzun kesinti olmamalı. Bu kartta dayanıklılık zorunludur.",
                       "Kaybolan alışveriş listesi uygulamanın silinmesidir; dayanıklılık burada ürünün kendisidir."),
            req(False, "Altı geliştirici, MongoDB driver'ı. Sunucu, yama, failover istenmiyor; yazma büyümesi için kolay bir yol istenir.",
                       "Yazma sınırına yaklaşan bir cluster'ı gece büyütmek ekibin istemediği operasyondur."),
            req(False, "Gün içinde düz, akşam tepe; yazma ağırlıklı. Kullanım başına ya da kapasite başına; büyümede sıçrama istenmez.",
                       "1.500 yazma/saniye sürekli I/O üretir; I/O başına ödeme bütçeyi tahmin edilemez yapar."),
        ],
        cands=["doc", "ddb", "aur"],
        scores={
            "doc": [sc(10, "Liste bir document, öğeler array (Ö2); { owner: 1, updated_at: -1 } compound index ile kullanıcının listeleri (Ö3, Ö4). Filtresinde version: 7 olan bir updateOne, $set ile 'items.$[i].done' alanını değiştirir ve $inc ile version'ı artırır; koşul ve array içi güncelleme tek atomik yazmadır, matchedCount 0 ise eski yazma reddedilmiştir (Ö5). Change stream değişikliği saniyeler içinde yayın servisine verir (Ö7). Puan kırılmadı."),
                    sc(9, "1.500 yazma tek primary'nin içindedir; okumalar replica'lara dağılır (Ö8). 1 puan kırıldı: yüzde 40 büyüme birkaç yıl içinde en büyük instance'a ya da elastic cluster'a geçiş demektir ve bu bir plan ister."),
                    sc(10, "Üç AZ'de altı kopya; yazma çoğunluğa kalıcı yazılmadan onaylanmaz; point-in-time restore. Puan kırılmadı."),
                    sc(8, "Aynı driver; yedek, yama, failover yönetilir; change stream yerleşiktir. 2 puan kırıldı: instance ve replica kararları ekibindir; change stream tüketicisi ve retention (varsayılan üç saat, en fazla yedi gün) ekibin kurduğu bir parçadır."),
                    sc(8, "I/O-Optimized seçeneği ile I/O ücreti kalkar, instance fiyatı yükselir; yazma ağırlıklı iş yükünde öngörülebilir. 2 puan kırıldı: Multi-AZ instance'lar gece de ödenir; büyüme instance sınıfı atlatır.")],
            "ddb": [sc(6, "Partition key owner, sort key list id; ConditionExpression version = :v ile koşullu yazma; Streams değişikliği akıtır. 4 puan kırıldı: array'deki tek öğeyi koşula göre bulmak index numarası ister, uygulama önce okur; \"son değişikliğe göre listeler\" için GSI gerekir; kod MongoDB driver'ı ile yazılmıştır."),
                    sc(10, "Yazma ve okuma kendiliğinden ölçeklenir. Puan kırılmadı."),
                    sc(10, "Birkaç AZ, point-in-time recovery. Puan kırılmadı."),
                    sc(8, "Serverless, Streams ve Lambda yerleşik. 2 puan kırıldı: veri erişim katmanı yeniden yazılır; key tasarımı öğrenilir."),
                    sc(8, "İstek başına. 2 puan kırıldı: 1.500 yazma/saniye ve GSI yazmaları sürekli birim tüketir; büyük listeler birkaç birim.")],
            "aur": [sc(7, "lists ve items table'ları; UPDATE ... WHERE version = 7 koşullu yazma; mantıksal replication ya da trigger ile değişiklik akışı. 3 puan kırıldı: liste bir JOIN'dir ya da JSONB'de tutulur ve tek öğe için row yeniden yazılır; değişiklik akışı için ek bir parça kurulur."),
                    sc(8, "1.500 yazma tek writer için rahattır; okumalar reader'lara. 2 puan kırıldı: reader ve ACU kararları; büyüme kapasite projesi."),
                    sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                    sc(7, "Yönetilen. 3 puan kırıldı: ekip SQL'e geçer; değişiklik akışı ek bir mekanizmadır."),
                    sc(7, "ACU-saat; I/O-Optimized seçeneği var. 3 puan kırıldı: minimum kapasite; reader ayrıca.")],
        },
        h2h={
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinimler R1 ve R2. DynamoDB'nin gücü R2'de görünür: 1.500 yazma ve yüzde 40 büyüme için hiçbir boyutlandırma yoktur, ConditionExpression sürüm kontrolünü yapar ve Streams ile Lambda değişikliği yayar; dayanıklılıkta ikisi eşittir. "
                      "DocumentDB'nin gücü R1'in array kısmındadır: tek öğe arrayFilters ile koşulla birlikte tek atomik yazmada değişir; DynamoDB'de öğenin liste numarası bilinmeli ya da her öğe ayrı item olmalıdır. Ekip MongoDB driver'ı ile çalışıyor ve uygulamanın JSON'u document'ın kendisidir. "
                      "Bu iş yükünde document seçilir, çünkü değişiklik array'in içindedir ve kod hazırdır. Fark üç puandır ve büyüme sürdükçe azalır. "
                      "Hangi koşul değişseydi DynamoDB seçilirdi: her liste öğesi ayrı bir kayıt olarak modellenseydi (partition key liste, sort key öğe), yazma hacmi saniyede on binlere çıksaydı ya da ekip SDK ile başlıyor olsaydı."),
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinimler R1 ve R4. Aurora'nın gücü, listeler paylaşım, abonelik ve fatura gibi ilişkili verilerle aynı database'de ise görünür; UPDATE ... WHERE version = 7 koşullu yazmayı yapar ve transaction birkaç table'ı birlikte değiştirir. "
                      "Ama liste bir document'tır: öğeler table olursa her okuma bir JOIN, JSONB olursa tek öğe için row yeniden yazılır; değişiklik akışı için mantıksal replication ya da trigger kurulur. DocumentDB'de change stream yerleşiktir ve ekip API'ı biliyor. "
                      "Bu yüzden document seçilir. Hangi koşul değişseydi Aurora seçilirdi: liste paylaşımı ve ödeme aynı transaction'da yazılsaydı, raporlar JOIN isteseydi ya da ekip SQL ekibi olsaydı."),
        },
        verdict=_t("Karar: DocumentDB 45, DynamoDB 42, Aurora 39. Yarışı R1 belirler: array içi koşullu güncelleme ve yerleşik change stream; R2'de DynamoDB öndedir. "
                   "Yine de document seçersek artımız: liste tek document, arrayFilters ile tek öğe, sürüm koşulu aynı yazmada, change stream yayın servisini besler, kod hazır. "
                   "Potansiyel eksimiz: yazmalar tek primary'den geçer ve büyüme planlanır; change stream retention en fazla yedi gündür, tüketici daha uzun durursa değişiklik kaybolur; I/O ücreti için I/O-Optimized seçilir. Bir koşul değişseydi: yazma hacmi saniyede on binlere çıksaydı DynamoDB kazanırdı.")),

    # ------------------------------------------------------------------ 7. order documents with line items (race vs Aurora, both together)
    usecase("orders", 7, sim="race_orders", kind="race",
        title=_t("Sipariş document'ları: satırlar, adres ve durum geçmişi"),
        key=_t("Collection: orders. Document: _id, customer_id, lines (array), address (iç içe), status, history (array). Checkout Aurora'da kalır."),
        story=_t("Lale Market'in checkout'u stok ve ödemeyi Aurora'da tek transaction ile yazar. Sipariş onaylandıktan sonra \"siparişlerim\" ekranı, kargo takibi ve destek ekibi siparişin tamamını ister: satırlar ürün adlarıyla, teslimat adresi o günkü hâliyle, durum geçmişi (alındı, hazırlanıyor, kargoda, teslim). "
                 "Ekip bu okuma modelini ayrı bir serviste tutmak istiyor, çünkü sipariş ekranı okumaları checkout writer'ını yormamalı ve okuma modeli checkout'un migration takviminden bağımsız değişmeli: her sipariş tek bir document, checkout commit'inden sonra bir event ile yazılır, her durum değişikliği history array'ine eklenir. Sorular: \"bu müşterinin siparişleri, yeniye göre\", \"kargoda olan ve üç günden eski siparişler\", \"bu ürünü içeren siparişler\". "
                 "Günde 5.000 sipariş, saniyede 200 okuma; 3 yıl, 5 milyon sipariş. Üç geliştirici, SQL ve MongoDB ikisini de biliyor. Sipariş kaydı Aurora'da zaten kalıcıdır; bu kopya kaybolursa event'lerden yeniden kurulur."),
        reqs=[
            req(True, "Sipariş _id ile tek okumada satırlar, adres ve geçmişle gelmeli. Durum değişikliği geçmiş array'ine eklenip status field'ını tek yazmada değiştirmeli. \"Müşterinin siparişleri, yeniye göre\", \"kargoda ve üç günden eski\", \"bu ürünü içeren\" soruları index ile cevaplanmalı. Adres siparişteki hâliyle saklanmalı (müşteri adresini değiştirince sipariş değişmez).",
                      "Sipariş ekranı parçalardan toplanırsa her açılış dört okumadır. Adres referansla tutulursa müşteri adresini değiştirince eski siparişin adresi değişir ve kargo yanlış yere gider."),
            req(True, "Günde 5.000 sipariş (saniyede birkaç yazma), saniyede 200 okuma; 5 milyon document, yılda 1,8 milyon artıyor. Okuma 20 ms'nin altında.",
                      "Hacim küçüktür; ölçek belirleyici değildir. Belirleyici olan okuma modelinin şekli ve ekibin işidir."),
            req(False, "Kopya kaybolursa checkout event'lerinden yeniden kurulur (saatler). Bir AZ arızasında kesinti kısa olmalı.",
                       "Kayıp para kaybı değildir; sipariş Aurora'da kalıcıdır. Yeniden kurulum saatlerinde \"siparişlerim\" ekranı boştur."),
            req(False, "Üç geliştirici, SQL ve MongoDB. Sunucu, yama, yedek istenmiyor. Yeni durum türü ya da satır field'ı migration'sız gelmeli.",
                       "Kargo şirketi değişince geçmişe yeni field'lar gelir; her biri için migration istenmez."),
            req(False, "Düz ve küçük trafik. En düşük sabit maliyet; veri birkaç on GB.",
                       "Küçük iş yükünde minimum kapasite faturayı belirler."),
        ],
        cands=["doc", "aur", "ddb"],
        scores={
            "doc": [sc(9, "Sipariş tek document: lines array, address embedded document, history array (Ö2); _id ile tek okuma (Ö1). Durum değişikliği updateOne ile $set ve $push tek atomik yazmadır (Ö5). { customer_id: 1, created_at: -1 } ve { status: 1, updated_at: 1 } compound index'leri ve lines.product_id üzerinde multikey index soruları IXSCAN yapar (Ö3, Ö4). Adres document'ın içine kopyalanır. 1 puan kırıldı: \"ürünlerin güncel adıyla sipariş raporu\" gibi bir soru gelirse kopyalanan ad yetmez ve products collection'ından $lookup gerekir."),
                    sc(10, "Saniyede birkaç yazma ve 200 okuma bir primary ve bir replica için küçüktür (Ö8). Puan kırılmadı."),
                    sc(10, "Üç AZ'de altı kopya, point-in-time restore. Puan kırılmadı."),
                    sc(7, "Ekip API'ı biliyor; yedek ve yama yönetilir; yeni field migration'sız. 3 puan kırıldı: Aurora'dan bu collection'a event taşıyan parça (outbox ve tüketici) ekibin kurduğu ve işlettiği ek bir boru hattıdır; index planı ekibindir."),
                    sc(6, "Serverless 0,5 DCU'ya iner ya da iki küçük instance. 4 puan kırıldı: Aurora zaten ödenirken ikinci bir yönetilen database'in minimum kapasitesi eklenir; küçük iş yükünde bu, faturanın görünür bir kalemidir.")],
            "aur": [sc(7, "orders, order_items ve order_status_history table'ları zaten var; sipariş bir JOIN ile ya da JSONB kolonunda tutulan bir okuma modeli ile gelir; bütün sorular SQL'dir. 3 puan kırıldı: üç table'lı okuma her açılışta JOIN'dir; JSONB okuma modelinde history eklemek row'un tamamını yeniden yazar; adres kopyası ayrıca tasarlanır; \"bu ürünü içeren siparişler\" order_items üzerinden JOIN ve tekilleştirme ister."),
                    sc(9, "Hacim küçük; aynı cluster taşır. 1 puan kırıldı: okuma modeli checkout ile aynı writer'da yaşar; raporlar reader'a yönlendirilir."),
                    sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                    sc(8, "Ek database yok, aynı ekip, aynı SQL; event taşıma parçası gerekmez (aynı transaction'da yazılır). 2 puan kırıldı: yeni durum field'ları için migration; JSONB okuma modeli kullanılırsa operatörler öğrenilir."),
                    sc(7, "Ek bir database ödenmez; mevcut Aurora kapasitesi kullanılır. 3 puan kırıldı: okuma modeli checkout cluster'ının ACU'sunu tüketir ve reader instance eklenirse o ödenir; I/O ayrıca.")],
            "ddb": [sc(6, "Partition key customer_id, sort key sipariş zamanı; item sipariş, satırlar liste, adres map; \"müşterinin siparişleri\" bir Query. 4 puan kırıldı: \"kargoda ve üç günden eski\" ve \"bu ürünü içeren\" için GSI ve satırların ayrı item'lara açılması gerekir; history listesine ekleme list_append ile olur ama koşul ve sorgu sınırlıdır; ekip SDK öğrenir."),
                    sc(10, "Kendiliğinden ölçek. Puan kırılmadı."),
                    sc(10, "Birkaç AZ. Puan kırılmadı."),
                    sc(7, "Serverless. 3 puan kırıldı: key tasarımı ve GSI planı; event taşıma parçası yine gerekir; ekip SDK'ya geçer."),
                    sc(8, "İstek başına, küçük hacimde sıfıra yakın. 2 puan kırıldı: GSI yazmaları ve büyük sipariş item'ları birim tüketir.")],
        },
        h2h={
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Bu yarış \"ikinci bir database'e değer mi?\" sorusudur, çünkü sipariş Aurora'da zaten vardır. Ayrıştığı gereksinimler R1'in şekil kısmı, R4 ve R5 (R4'te Aurora bir puan önde, çünkü boru hattı yok). Aurora'nın gücü: ek database yok, event taşıma parçası yok, sipariş checkout ile aynı transaction'da yazılır ve her soru bir SQL'dir; JSONB kolonu okuma modelini de taşıyabilir. "
                      "DocumentDB'nin gücü: sipariş ekranı tek document ve tek okumadır, durum geçmişi $push ile eklenir, adres siparişin içinde donar, yeni field'lar migration'sız gelir ve okuma yükü checkout cluster'ından ayrılır. "
                      "Bu iş yükünde document bir puanla seçilir, çünkü sipariş ekranı bir belgedir (R1) ve okuma yükü checkout writer'ından ayrılır (R2); ama doğru cevap ikisi birliktedir: checkout ve stok Aurora'da (kayıt sistemi), sipariş document'ı DocumentDB'de (okuma modeli), arada bir event. Ekip ikinci database'in minimum maliyetini kabul etmezse Aurora'nın JSONB okuma modeli savunulabilir. "
                      "Hangi koşul değişseydi Aurora seçilirdi: okuma hacmi checkout cluster'ını yormayacak kadar küçük kalsaydı, ekip tek database isteseydi ve sipariş ekranı JSONB kolonundan tek okumayla gelseydi."),
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinimler R1 ve R4. DynamoDB'nin gücü R2 ve R5'te: 5 milyon sipariş ve büyüme için boyutlandırma yoktur, küçük trafikte ödeme sıfıra yakındır ve \"müşterinin siparişleri, yeniye göre\" partition key ve sort key ile tam bir key-value sorusudur. "
                      "Ama \"kargoda ve üç günden eski\" ve \"bu ürünü içeren siparişler\" key ile sorulamaz; GSI ve satırların ayrı item'lara açılması gerekir; durum geçmişine koşullu ekleme ve liste içi sorgu sınırlıdır. DocumentDB'de bunlar birer filtre ve index'tir. Ekip SDK'yı bilmiyor. "
                      "Bu iş yükünde document seçilir, çünkü sorular sipariş document'ının içine göredir ve hacim küçüktür. "
                      "Hangi koşul değişseydi DynamoDB seçilirdi: tek soru \"müşterinin siparişleri\" olsaydı, ürün ve durum soruları arama servisine verilseydi ve okuma hacmi saniyede on binlere çıksaydı."),
        },
        verdict=_t("Karar: DocumentDB 42, Aurora 41, DynamoDB 41. Yakın bir yarış: üç aday da R2 ve R3'ü karşılar; yarışı R1'in şekli (tek document, array içi geçmiş) ve R5 (ikinci database'in maliyeti) iki yöne çeker. Dürüst cevap ikisi birliktedir: kayıt Aurora'da, okuma modeli DocumentDB'de. "
                   "Yine de document seçersek artımız: sipariş ekranı tek okuma, durum geçmişi $push, adres siparişte donmuş, index'li üç soru, okuma yükü checkout'tan ayrı. "
                   "Potansiyel eksimiz: ikinci database'in minimum kapasitesi; Aurora'dan event taşıyan parça (outbox ve tüketici) ekibin kurduğu bir parçadır ve gecikirse \"siparişlerim\" ekranı geride kalır; ürün adı kopyası eski siparişlerde eski kalır. Bir koşul değişseydi: ekip tek database isteseydi ve okuma modeli JSONB'den tek okumayla gelseydi Aurora kazanırdı.")),

    # ------------------------------------------------------------------ 8. catalog search by nested fields (race vs OpenSearch, both together later)
    usecase("search", 8, sim="race_search", kind="race",
        title=_t("İç içe field'lara göre katalog araması: filtre ve facet"),
        key=_t("Collection: products. Sorgu: category, 'attributes.renk', 'attributes.garanti_ay' ve price üzerinde filtre, sıralama, limit. Facet sayıları $group ile."),
        story=_t("Lale Market'in kategori sayfasında ziyaretçi filtre seçer: \"Elektronik, siyah, garanti 24 ay ve üzeri, 2.000 TL altı, rating'e göre\". Sayfa her filtre için seçenek sayılarını da gösterir (\"siyah (9), lacivert (6)\"). "
                 "Katalog zaten DocumentDB'de (kart 1); soru bu filtrelerin ve facet sayılarının nereden geleceğidir. Metin araması (\"kablosz kulaklk\" gibi yazım hatalı) ayrı bir ihtiyaçtır ve bu kartta istenmiyor; ürün ekibi bunu bir sonraki çeyreğe bıraktı. "
                 "Saniyede 1.200 filtreli okuma, kampanyada 5.000; 200.000 ürün; filtre field'ları 20 tane ve her ay bir yenisi geliyor. Cevap 50 ms'nin altında olmalı. Dört geliştirici, MongoDB biliyor, OpenSearch bilmiyor."),
        reqs=[
            req(True, "Dört beş field'ın (iç içe olanlar dahil) birleşimiyle filtre, bir field'a göre sıralama ve sayfalama. Her filtre field'ı için seçenek sayıları (facet). Yeni filtre field'ı ayda bir geliyor. Metin araması ve relevance istenmiyor (bu çeyrek).",
                      "Filtre index'siz çalışırsa 200.000 document taranır ve sayfa saniyeler sürer; facet sayıları her sayfa açılışında bütün kategoriyi okuyorsa aynı şey olur."),
            req(True, "Saniyede 1.200 filtreli okuma, kampanyada 5.000; cevap 50 ms'nin altında. 200.000 ürün.",
                      "Kategori sayfası mağazanın en çok açılan sayfasıdır; kampanyada yavaşlarsa satış kaybıdır."),
            req(False, "Katalog DocumentDB'de kalıcıdır; arama katmanı kaybolursa yeniden kurulur. Kısa kesinti kabul.",
                       "Arama katmanının kaybı vitrini boşaltır ama veri kaybı değildir."),
            req(False, "Dört geliştirici, MongoDB. İkinci bir sistem ve onu besleyen bir boru hattı istenmiyor; ama metin araması gelince bu değişebilir.",
                       "İkinci sistem iki şema, iki deploy ve bir senkronizasyon hatası kaynağı demektir."),
            req(False, "Okuma ağırlıklı, kampanyada tepe. Mevcut cluster'ın kapasitesi kullanılmak istenir.",
                       "Ek bir servis ek bir sabit maliyettir; küçük mağaza için görünür bir kalemdir."),
        ],
        cands=["doc", "os", "aur"],
        scores={
            "doc": [sc(8, "Filtre find ile dot notation kullanır (Ö3); { category: 1, 'attributes.renk': 1, rating: -1 } gibi compound index'ler IXSCAN verir (Ö4); facet sayıları $match ve $group ile bir aggregation pipeline'dır (Ö6) ve kategori başına index'li çalışır. 2 puan kırıldı: 20 filtre field'ının her birleşimi için index kurulamaz (collection başına 64 index sınırı ve yazma maliyeti), bazı birleşimler index'in bir kısmını kullanıp kalan koşulu document üzerinde test eder; facet sayıları her filtre değişiminde yeniden hesaplanır; relevance sıralı metin araması yoktur."),
                    sc(8, "1.200 ve kampanyada 5.000 okuma replica'lara dağılır (Ö8); index'li filtre milisaniyelerdedir. 2 puan kırıldı: facet pipeline'ları her sayfada çalışır, kampanyada saniyede binlerce $group replica sayısını artırmayı ister ve 50 ms'nin tutup tutmadığı bir yük testiyle ölçülmelidir."),
                    sc(10, "Katalog zaten burada; üç AZ'de altı kopya. Puan kırılmadı."),
                    sc(8, "İkinci sistem yok, aynı API, aynı cluster. 2 puan kırıldı: her yeni filtre field'ı için index kararı ve bazen bir compound index'in yeniden tasarımı; index'siz birleşim COLLSCAN'dir."),
                    sc(8, "Mevcut cluster kullanılır; ek servis yok. 2 puan kırıldı: kampanyada replica ya da DCU eklenir; facet pipeline'ları I/O üretir.")],
            "os": [sc(10, "Filtre, sıralama, sayfalama ve facet sayıları (aggregation) tek istekte ve index'in doğal işidir; yeni filtre field'ı mapping'e eklenir; metin araması ve relevance gelince hazırdır. Puan kırılmadı."),
                   sc(9, "5.000 okuma küçük bir domain için rahattır; facet'ler milisaniyelerdedir. 1 puan kırıldı: shard ve node sayısı önceden seçilir; yeni ürün refresh aralığı kadar geç görünür."),
                   sc(8, "Arama index'i kataloğun kopyasıdır ve DocumentDB'den yeniden kurulur; bu kartta kısa kesinti kabul edilir. 2 puan kırıldı: yeniden kurulum saatler sürer; mapping değişince index baştan kurulur; kopya DocumentDB'nin gerisinde kalabilir."),
                   sc(7, "Yönetilen domain; facet ve filtre için ayar yok. 3 puan kırıldı: ikinci bir sistem, onu besleyen change stream tüketicisi ve ekibin bilmediği mapping dili; gereksinim ikinci sistemi açıkça istemiyor."),
                   sc(7, "Node saat başına; küçük domain. 3 puan kırıldı: mevcut cluster'a ek bir sabit maliyet (en az iki node, Multi-AZ) ve boru hattının bedeli.")],
            "aur": [sc(7, "Katalog Aurora'ya kopyalansaydı: JSONB ve GIN index ile filtre, GROUP BY ile facet. 3 puan kırıldı: katalog burada değil, kopyalanması gerekir; JSONB içi birleşik filtreler ve facet'ler büyük kategoride yavaştır; metin araması sınırlıdır."),
                    sc(8, "5.000 okuma reader'larla. 2 puan kırıldı: reader sayısı ve ACU; facet GROUP BY'ları ACU tüketir."),
                    sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                    sc(6, "Yönetilen. 4 puan kırıldı: ikinci sistem ve SQL'e geçiş; ekip bilmiyor."),
                    sc(5, "0,5 ACU minimum ve reader. 5 puan kırıldı: sadece arama için ikinci bir ilişkisel database en pahalı seçenektir.")],
        },
        h2h={
            "os": _t("Search engine (OpenSearch) ile kafa kafaya. Bu yarış \"ne zaman ikinci sistem?\" sorusudur. Ayrıştığı gereksinimler R1'in facet kısmı (OpenSearch iki puan önde), R3, R4 ve R5 (DocumentDB önde). OpenSearch'ün gücü tam bu iş yükündedir: filtre, sıralama, sayfalama ve facet sayıları tek istekte, yeni field mapping'e bir satır, metin araması ve yazım hatası toleransı gelince hazır. "
                      "DocumentDB'nin gücü ikinci sistemin olmamasıdır: aynı cluster, aynı API, index'li filtreler ve $group ile facet'ler bu hacimde yeter; kayıt sistemi zaten burada. "
                      "Bu iş yükünde document bir puanla seçilir, çünkü metin araması bu çeyrek istenmiyor, ekip OpenSearch bilmiyor ve facet'ler index'li pipeline ile 50 ms'nin altında kalıyor. Ama bu karar geçicidir: metin araması gelince doğru cevap ikisi birliktedir; katalog DocumentDB'de, arama kopyası change stream ile OpenSearch'te. Kart bunu karar kaydına yazar. "
                      "Hangi koşul değişseydi OpenSearch seçilirdi: relevance sıralı ve yazım hatası toleranslı metin araması istenseydi, facet sayıları kampanyada replica'ları yormaya başlasaydı ya da filtre field'ı sayısı index'lenemeyecek kadar artsaydı."),
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinimler R1, R4 ve R5. Aurora'nın gücü, katalog zaten ilişkisel bir database'de olsaydı görünürdü: JSONB ve GIN index filtreyi, GROUP BY facet'leri verir ve ikinci sistem gerekmezdi. "
                      "Ama katalog DocumentDB'dedir; Aurora'yı sadece arama için eklemek ikinci bir database, bir kopyalama boru hattı ve SQL öğrenmek demektir; JSONB içi birleşik filtreler ve büyük kategoride facet GROUP BY'ları da OpenSearch kadar hızlı değildir. "
                      "Bu iş yükünde document seçilir, çünkü arama katmanı ya mevcut cluster'da ya da bir search engine'de olmalıdır; ilişkisel database bu soruda üçüncü sıradadır. "
                      "Hangi koşul değişseydi Aurora seçilirdi: katalog zaten Aurora'da olsaydı (Aurora sayfasının katalog kartı) ve arama JSONB ve GIN index ile bu hacimde yeterli olsaydı."),
        },
        verdict=_t("Karar: DocumentDB 42, OpenSearch 41, Aurora 36. Yakın bir yarış: yarışı R3, R4 ve R5 (kayıt sistemi aynı yerde, ikinci sistemin bedeli yok) DocumentDB'ye, R1'in facet kısmı OpenSearch'e çeker. "
                   "Yine de document seçersek artımız: tek sistem, aynı API, index'li filtreler, $group ile facet, kayıt sistemi aynı yerde. "
                   "Potansiyel eksimiz: her filtre birleşimi index'lenemez ve bazı sayfalar document üzerinde ek test yapar; facet pipeline'ları kampanyada replica ister; relevance ve yazım hatası toleransı yoktur. Bir koşul değişseydi: metin araması istendiği çeyrek OpenSearch eklenir ve change stream ile beslenir; o zaman ikisi birlikte doğru cevaptır.")),

    # ------------------------------------------------------------------ 9. session documents (card only; ElastiCache wins)
    usecase("sessions", 9,
        title=_t("Oturum document'ları: teklif sihirbazının adımları"),
        key=_t("Collection: sessions. Document: _id (session id), user_id, wizard (iç içe: araç, sürücüler, teminatlar), expires_at. TTL index."),
        story=_t("Bir sigorta satış sitesinde ziyaretçi beş adımlık bir teklif sihirbazından geçer; her adımın cevapları oturum document'ında iç içe tutulur (araç, sürücüler listesi, seçilen teminatlar). Oturum 30 dakika hareketsizlikten sonra düşmeli ve her istekte süresi yenilenmeli. "
                 "Her HTTP isteği oturumu okur; sihirbazın her adımı oturumun bir kısmını yazar. Pazarlama ekibi günde birkaç kez \"üçüncü adımda bırakılan oturumlar\" gibi sorular sorar. "
                 "Saniyede 15.000 okuma, 5.000 yazma; oturum 5 KB. Oturum okuması her isteğin önündedir: 1 ms gecikme her sayfaya eklenir. Kaybolan bir oturum sihirbazı baştan başlatır; müşteri sinirlenir ama para kaybolmaz. Uygulama MongoDB driver'ı ile yazılmış ve ekip ilk olarak mevcut DocumentDB cluster'ına bir sessions collection'ı eklemeyi düşünüyor; sunucu istenmiyor."),
        reqs=[
            req(True, "Session id ile tek okuma; her istekte süre yenileme; sihirbaz adımının iç içe field'ını tek yazmada değiştirmek. 30 dakika sonra oturum okunmamalı. Günde birkaç kez oturumun içine göre analiz sorusu.",
                      "Süresi dolmuş oturumun kabul edilmesi paylaşılan bilgisayarda bir sonraki kişiyi önceki teklifte bırakır. Her istekte bir okuma ve bir yazma olduğu için gecikme doğrudan sayfaya eklenir."),
            req(True, "Saniyede 15.000 okuma ve 5.000 yazma (süre yenileme dahil); okuma 2 ms'nin altında. Tepe öğle ve akşam.",
                      "Oturum okuması her isteğin ilk adımıdır; 5.000 yazma/saniye tek bir yazma düğümü için ağır bir yüktür."),
            req(False, "Kaybolan oturum yeni bir sihirbaz demektir; kabul edilir ama sık olmamalı. Bir instance arızası bütün oturumları silmemeli.",
                       "Toplu oturum kaybı o saatteki bütün teklifleri baştan başlatır; müşteri kaybıdır, para kaybı değil."),
            req(False, "Kod MongoDB driver'ı ile yazılmış; ekip sunucu istemiyor. İkinci bir sistem kabul edilebilir, eğer kazancı açıksa.",
                       "Oturum kodu küçüktür; değiştirmek bir haftalık iştir, uygulamanın geri kalanı değişmez."),
            req(False, "Yazma ağırlıklı ve sürekli. 5 KB'lık oturumlar için bellek ya da I/O maliyeti öngörülebilir olmalı.",
                       "Saniyede 5.000 süre yenilemesi I/O olarak faturalanırsa oturum katmanı en pahalı kalem olur."),
        ],
        cands=["doc", "ec", "ddb"],
        scores={
            "doc": [sc(9, "Oturum bir document, sihirbaz cevapları iç içe (Ö2); _id ile okuma (Ö1); adım $set ile tek yazmada değişir (Ö5); \"üçüncü adımda bırakılanlar\" wizard.step üzerinde bir filtre (Ö3). TTL index expires_at üzerinde silmeyi yapar. 1 puan kırıldı: TTL silmesi \"best effort\" ve zamanı garanti değildir; uygulama expires_at'i okumada kendisi karşılaştırır."),
                    sc(5, "15.000 okuma replica'lara dağılır (Ö8). 5 puan kırıldı: zorunlu \"2 ms'nin altında okuma\" disk tabanlı motor ve ağ gidiş dönüşüyle her istekte tutmaz; 5.000 yazma/saniye tek primary'den geçer ve büyük bir instance ister."),
                    sc(10, "Üç AZ'de altı kopya; instance arızası oturumları silmez. Puan kırılmadı."),
                    sc(8, "Aynı driver, kod değişmez; yedek ve yama yönetilir. 2 puan kırıldı: yazma yükü için instance boyutlandırma ekibindir."),
                    sc(7, "Instance saat başına ve I/O başına. 3 puan kırıldı: saniyede 5.000 süre yenilemesi ve TTL silmeleri sürekli I/O'dur; I/O-Optimized ile instance fiyatı yükselir.")],
            "ec": [sc(10, "Oturum bir hash; GET ve HSET bellekten, mikrosaniyelerdedir; EXPIRE tam anında uygular ve süresi dolan oturum okunamaz; tek field HSET ile değişir. Puan kırılmadı."),
                   sc(10, "15.000 okuma ve 5.000 yazma bellek içi store için küçüktür; serverless kendiliğinden ölçeklenir. Puan kırılmadı."),
                   sc(6, "Serverless birkaç AZ'de replika tutar. 4 puan kırıldı: kalıcı bir yazma log'u yoktur; bir arızada son saniyelerin oturumları kaybolabilir; bu kartta kabul edilir ama sık olmamalıdır."),
                   sc(9, "Serverless, sunucu yok. 1 puan kırıldı: oturum kodu Valkey komutlarına taşınır (bir hafta); \"üçüncü adımda bırakılanlar\" için key'ler taranır ya da ayrı bir sayaç tutulur."),
                   sc(10, "GB-saat ve ECPU başına; 5 KB'lık oturumlar için bellek küçüktür. Puan kırılmadı.")],
            "ddb": [sc(8, "Simple primary key session id, GetItem ve UpdateItem; TTL attribute'u. 2 puan kırıldı: TTL \"within a few days\", uygulama expires_at'i filtreler; iç içe sihirbaz field'ı document yolu ile değişir ama analiz sorusu Scan ya da GSI ister."),
                    sc(6, "Yazma ve okuma kendiliğinden ölçeklenir. 4 puan kırıldı: okuma tek haneli milisaniyedir ve zorunlu 2 ms sınırını her istekte tutmaz; DAX gibi bir cache bunu çözer ama ikinci bir parçadır."),
                    sc(10, "Birkaç AZ. Puan kırılmadı."),
                    sc(8, "Serverless. 2 puan kırıldı: kod SDK'ya taşınır."),
                    sc(8, "İstek başına. 2 puan kırıldı: 5.000 süre yenilemesi/saniye yazma birimi tüketir; 5 KB oturum okuma başına iki birim.")],
        },
        h2h={
            "ec": _t("Bellek içi key-value (ElastiCache) ile kafa kafaya. Ayrıştığı gereksinimler R1'in süre sonu kısmı, R2 ve R5. ElastiCache'in gücü oturumun tanımıdır: bellekten mikrosaniyede okuma, EXPIRE ile tam anında süre sonu, saniyede 5.000 yazmanın bellek için küçük olması ve GB-saat ile öngörülebilir maliyet. "
                      "DocumentDB'nin gücü oturumun içinde görünür: sihirbaz cevapları iç içe bir document'tır, \"üçüncü adımda bırakılanlar\" bir filtredir ve kod değişmez; dayanıklılıkta DocumentDB açık ara öndedir. "
                      "Ama bu iş yükünde kategori bellek içidir: oturum geçicidir, kaybı kabul edilir ve her isteğin önünde durur. DocumentDB bu kartta kaybeder ve kart bunu söylemek için vardır: document şekli tek başına document database'i seçtirmez. Dürüst cevap ikisi birliktedir: oturum ElastiCache'te, tamamlanan teklif DocumentDB'de. "
                      "Hangi koşul değişseydi DocumentDB seçilirdi: oturum kaybı kabul edilmeseydi (teklif oturumda tamamlanıp ödeme alınıyorsa), yazma hacmi saniyede birkaç yüze inseydi ve oturumun içine göre sorular ana iş olsaydı."),
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinimler R2 ve R5. DynamoDB'nin gücü: 15.000 okuma ve 5.000 yazma için boyutlandırma yoktur, oturum kalıcıdır ve TTL attribute'u silmeyi yapar; DocumentDB'de 5.000 yazma tek primary'den geçer ve instance boyutu ekibin işidir. "
                      "DocumentDB'nin gücü: iç içe sihirbaz cevapları ve içe göre analiz sorusu doğrudan desteklenir, kod değişmez. İkisinde de süre sonu kesin değildir ve uygulama expires_at'i okumada karşılaştırır. "
                      "Bu kartta DynamoDB de DocumentDB'nin bir puan önündedir, çünkü yazma hacmi ve maliyet oturum iş yükünü key-value'ya çeker; ama ikisi de zorunlu 2 ms sınırını tutmaz. Kart yine de document sayfasındadır, çünkü ekip ilk olarak \"mevcut cluster'a bir collection\" demiştir ve bu kart o cevabın bedelini gösterir. "
                      "Hangi koşul değişseydi DynamoDB (ElastiCache yerine) seçilirdi: oturum kaybı kabul edilmeseydi ve 2 ms'lik okuma sınırı 10 ms'ye gevşeseydi."),
        },
        verdict=_t("Karar: ElastiCache 45, DynamoDB 40, DocumentDB 39. DocumentDB bu kartı kaybeder: yarışı zorunlu R2 belirler (2 ms'nin altında okuma ve 5.000 yazma/saniye tek primary'den), R5 (süre yenilemesi I/O olarak) farkı büyütür; R3'te DocumentDB en iyisidir ama bu kartta dayanıklılık tercihlidir. "
                   "Yine de document seçersek artımız: kod değişmez, sihirbaz cevapları iç içe, içe göre analiz sorusu bir filtre, oturum kalıcı. "
                   "Potansiyel eksimiz: büyük bir primary instance, sürekli I/O faturası, TTL silmesinin zamanı garanti değil, 2 ms'nin altı okuma garanti değil. Bir koşul değişseydi: oturum kaybı kabul edilmeseydi ve yazma hacmi birkaç yüze inseydi DocumentDB yarışa girerdi; bugünkü dürüst cevap \"oturum ElastiCache'te, tamamlanan teklif DocumentDB'de\".")),

    # ------------------------------------------------------------------ 10. feature flags and settings (card only)
    usecase("flags", 10,
        title=_t("Feature flag'ler ve uygulama ayarları"),
        key=_t("Collection: flags. Document: _id (flag adı), enabled, rules (array: segment, yüzde, ülke), variants (iç içe), version, history."),
        story=_t("Bir e-ticaret şirketinin 40 mikroservisi 300 feature flag ve ayar okur: \"yeni checkout açık mı\", \"kargo bedava eşiği\", \"A/B varyantları\". Her flag'in kuralları farklıdır: bazıları yüzdeyle, bazıları ülke listesiyle, bazıları müşteri segmentiyle açılır; ürün ekibi her hafta yeni kural türü ister. "
                 "Servisler flag'leri 30 saniyede bir okur ve bellekte tutar; değişiklik 10 saniye içinde bütün servislere yayılmalı. Kim neyi ne zaman değiştirdi sorusu denetim için saklanmalı. "
                 "Saniyede 500 okuma, günde 50 yazma; veri birkaç MB. Yanlış bir flag değişikliği mağazayı kapatabilir; geri alınabilmeli. Platform ekibi dört kişi, MongoDB ve SQL ikisini de biliyor; şirketin zaten bir DocumentDB cluster'ı var ve en düşük operasyon istenir."),
        reqs=[
            req(True, "Flag adı ile tek okuma ve \"bütün flag'ler\" tek sorgu. Kural türüne göre farklı şekil, yeni kural türü migration'sız. Bir flag'i \"version = 12 ise\" koşuluyla değiştirip geçmişe eklemek. Değişiklik 10 saniye içinde servislere ulaşmalı.",
                      "İki kişinin aynı flag'i aynı anda değiştirmesi mağazayı yanlış duruma sokar; geçmiş olmadan \"kim kapattı\" sorusu cevapsız kalır."),
            req(True, "Saniyede 500 okuma, günde 50 yazma; 300 document, birkaç MB. Okuma 10 ms'nin altında.",
                      "Hacim çok küçüktür; ölçek belirleyici değildir. Belirleyici olan şekil esnekliği, yayılma ve operasyondur."),
            req(True, "Flag'ler mağazanın davranışını belirler; kayıp ya da geri alınamayan yanlış değişiklik kabul edilmez. Bu kartta dayanıklılık zorunludur.",
                       "Flag'lerin kaybı bütün servisleri varsayılan davranışa düşürür; yanlış bir değişikliğin geri alınamaması kesintidir."),
            req(False, "Dört kişilik platform ekibi; en düşük operasyon; yeni kural türü kodda eklenmeli. Mevcut DocumentDB cluster'ı paylaşılabilir.",
                       "Flag sistemi için ayrı bir cluster işletmek ekibin istemediği bir iştir."),
            req(False, "Çok küçük veri ve trafik; en düşük sabit maliyet. Mevcut bir cluster'da bir collection idealdir.",
                       "Küçük iş yükünde ayrı bir database'in minimum kapasitesi faturanın tamamıdır."),
        ],
        cands=["doc", "ddb", "aur"],
        scores={
            "doc": [sc(10, "Flag bir document, kurallar türe göre farklı şekilli bir array (Ö2); _id ile okuma ve find({}) ile hepsi (Ö1, Ö3). Filtresinde version: 12 olan bir updateOne, $set, $inc ve history'ye $push ile koşulu ve geçmişi tek atomik yazmada yapar (Ö5). Change stream değişikliği saniyeler içinde servislere yayan bir tüketiciye verir (Ö7). Puan kırılmadı."),
                    sc(10, "500 okuma ve günde 50 yazma mevcut cluster için görünmez bir yüktür (Ö8). Puan kırılmadı."),
                    sc(9, "Üç AZ'de altı kopya, point-in-time restore; history array'i geri almayı verir. 1 puan kırıldı: history array'i sınırsız büyüyemez (A3); belirli bir boyuttan sonra eski kayıtlar ayrı bir collection'a taşınır ve bunu ekip izler."),
                    sc(9, "Mevcut cluster'a bir collection; aynı API; yeni kural türü migration'sız. 1 puan kırıldı: change stream tüketicisi (yayın) ekibin kurduğu bir parçadır."),
                    sc(8, "Mevcut cluster'da ek maliyet yaklaşık sıfır. 2 puan kırıldı: change stream açık olduğunda log I/O ve storage tüketir; cluster paylaşıldığı için flag sistemi diğer iş yükleriyle aynı faturadadır.")],
            "ddb": [sc(7, "Partition key flag adı; value şemasız, kurallar bir liste; ConditionExpression version = :v; Streams değişikliği yayar. 3 puan kırıldı: \"bütün flag'ler\" bir Scan'dir (300 item, kabul edilir ama key-value'nun doğal sorusu değildir); geçmişe koşullu ekleme list_append ile olur ve item 400 KB'ı aşmamalıdır; ekip bir SDK daha öğrenir."),
                    sc(10, "Kendiliğinden ölçek. Puan kırılmadı."),
                    sc(10, "Birkaç AZ, point-in-time recovery. Puan kırılmadı."),
                    sc(8, "Serverless, cluster yok; Streams ve Lambda yerleşik. 2 puan kırıldı: ikinci bir veri erişim katmanı ve key tasarımı."),
                    sc(9, "İstek başına; bu hacimde sıfıra yakın. 1 puan kırıldı: Streams tüketicisi ve Scan okumaları birim tüketir.")],
            "aur": [sc(8, "flags table'ı, rules JSONB, UPDATE ... WHERE version = 12, flag_history table'ı; her soru SQL. 2 puan kırıldı: türe göre farklı kurallar JSONB'de yaşar; değişiklik yayını için mantıksal replication ya da polling kurulur."),
                    sc(10, "Görünmez yük. Puan kırılmadı."),
                    sc(10, "Üç AZ'de altı kopya; point-in-time restore. Puan kırılmadı."),
                    sc(7, "Mevcut Aurora varsa bir table. 3 puan kırıldı: değişiklik akışı için ek parça; migration disiplini."),
                    sc(6, "Mevcut cluster'da sıfıra yakın; yoksa 0,5 ACU minimum. 4 puan kırıldı: sadece flag için ayrı Aurora en pahalı seçenektir.")],
        },
        h2h={
            "ddb": _t("Key-value (DynamoDB) ile kafa kafaya. Ayrıştığı gereksinimler R1'in şekil kısmı ve R4. DynamoDB'nin gücü: cluster yok, 300 item için ödeme sıfıra yakın, ConditionExpression sürüm kontrolünü yapar ve Streams ile Lambda değişikliği 10 saniyede yayar; AWS'in kendi AppConfig servisi de bu iş için vardır ve bu kartın dışındadır. "
                      "DocumentDB'nin gücü: kurallar türe göre farklı şekilli bir array'dir, koşullu güncelleme ve geçmişe ekleme tek atomik yazmadır, \"bütün flag'ler\" bir find'dır ve mevcut cluster'a bir collection eklemek sıfır operasyondur. "
                      "Bu iş yükünde document seçilir, çünkü ekibin elinde bir DocumentDB cluster'ı vardır (R4, R5) ve flag şekli serbesttir (R1); iki puanlık farkın bir kısmı mevcut cluster'dan gelir ve cluster olmasaydı fark kapanırdı. "
                      "Hangi koşul değişseydi DynamoDB seçilirdi: ekibin DocumentDB cluster'ı olmasaydı (ayrı cluster'ın minimumu bu iş için büyüktür), flag'ler sabit birkaç field olsaydı ya da ekip tamamen serverless bir platform istiyor olsaydı."),
            "aur": _t("İlişkisel (Aurora) ile kafa kafaya. Ayrıştığı gereksinimler R1'in şekil kısmı, R4 ve R5. Aurora'nın gücü: flag_history table'ı denetim için doğaldır, UPDATE ... WHERE version koşulu çalışır ve ekip SQL biliyor; mevcut bir Aurora varsa flag'ler bir table'dır. "
                      "Ama kurallar türe göre farklıdır ve her hafta yeni tür gelir; bu veri JSONB'ye yığılır ve schema'nın avantajı kalmaz; değişiklik yayını için mantıksal replication ya da polling kurulur, DocumentDB'de change stream yerleşiktir. "
                      "Bu yüzden document seçilir. Hangi koşul değişseydi Aurora seçilirdi: ekibin elinde Aurora olup DocumentDB olmasaydı, flag kuralları sabit kolonlar olsaydı ve denetim raporları JOIN ile sorulsaydı."),
        },
        verdict=_t("Karar: DocumentDB 46, DynamoDB 44, Aurora 41. Yarışı R1'in şekli (türe göre kurallar, koşul ve geçmiş tek yazmada) ve R4 (mevcut cluster'a bir collection) belirler. "
                   "Yine de document seçersek artımız: flag tek document, kural türü serbest, koşullu güncelleme ve history tek yazmada, change stream ile yayın, sıfır ek operasyon. "
                   "Potansiyel eksimiz: change stream tüketicisi ekibin parçasıdır ve durursa yayın durur; servisler 30 saniyelik okumayla telafi eder ama o süre boyunca \"10 saniye\" gereksinimi karşılanmaz, bu yüzden tüketiciye bir alarm kurulur; history array'i büyürse ayrı collection'a alınır; mevcut cluster yoksa minimum kapasite bu iş için büyüktür. Bir koşul değişseydi: mevcut DocumentDB cluster'ı olmasaydı DynamoDB kazanırdı.")),
]

USECASES["docdb"] = DOCDB_USECASES
