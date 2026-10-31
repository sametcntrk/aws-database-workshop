"""Weighted use cases of the E2E tutorials (model 2): the single source of the M2 cards and of the M7 simulations
of a page that uses the weighted model. First page: DynamoDB, Turkish only. The English DynamoDB page and the
other pages keep model 1 (e2e_usecases.py) until they are regenerated.

Model 2 in short:
- R1 "Engine uyumu" scores only the nature of the engine: its working principle, its algorithm and the tools it gives
  to the developer. It is split into 3-5 sub-items (R1.1 ... R1.n), each from the fixed catalog R1_CATALOG.
  Platform facts (serverless, Multi-AZ, pricing) belong to R2-R5.
- Every row has a weight. The weights come from the priorities of the workload, before the scores, and sum to 100.
  R2-R5 are never below 5. The weight of R1 is split over its sub-items.
- Every row is scored 0-10 for every candidate; contribution = points x weight / 10; total out of 100.
  There is no "must" row and no disqualification: a weak candidate loses on the weighted total.
- The candidates are the services that really fit the workload. The best fit (the highest total) comes first,
  also when it is not the service of the page. The service of the page always stays in the table.

Text fields are (en, tr) tuples; en is None while the page is Turkish only (T() falls back to Turkish).
"""
import re

from .e2e_usecases import CATEGORY, LINK

CATEGORY.setdefault("mdb", ("durable in-memory key-value", "kalıcı bellek içi key-value"))
LINK.setdefault("mdb", "elasticache")      # MemoryDB has no page of its own; the ElastiCache page compares them

# The fixed R1 catalog of the database domain: code -> (name, the question it asks). A card uses 3-5 of them.
R1_CATALOG = {
    "VM": ((None, "Veri modeli ve value tipi"), (None, "Value'nun yapısı ne: structured, semi-structured, iç içe, blob, graph, zaman serisi? Bir value ne kadar büyük?")),
    "ŞE": ((None, "Şema elverişliliği"), (None, "Şema yazarken mi okurken mi uygulanır? Alanlar kayıttan kayda değişebilir mi, şema nasıl evrilir?")),
    "EY": ((None, "Erişim yolu"), (None, "Soru hangi değerle sorulur: key, aralık, ikincil alan, join ve toplam, metin, coğrafya, ilişki, zaman penceresi?")),
    "OY": ((None, "Okuma/yazma şekli"), (None, "Hacim değil, işlemin biçimi: yerinde güncelleme mi, ekleme mi, oku-değiştir-yaz mı, sayaç mı, toplu yazma mı?")),
    "TA": ((None, "Tutarlılık ve atomiklik"), (None, "Engine hangi garantileri verir: okuma tutarlılığı, koşullu yazma, transaction kapsamı, izolasyon?")),
    "DA": ((None, "Depolama algoritması"), (None, "Engine'in çalışma algoritması bu erişime uyuyor mu: bellek içi hash, B-tree, LSM, columnar, inverted index?")),
    "YD": ((None, "Veri yaşam döngüsü"), (None, "Veri nasıl sona erer, değişikliği nasıl dışarı yayılır: TTL, sürüm, değişiklik akışı?")),
    "AO": ((None, "Ayar ve optimizasyon araçları"), (None, "Engine geliştiriciye hangi sıkılaştırma araçlarını verir: index tipleri, projection, sparse index, sıkıştırma, script?")),
}
R_REST = {"R2": (None, "Ölçek ve trafik şekli"), "R3": (None, "Dayanıklılık"), "R4": (None, "Operasyon ve ekip"), "R5": (None, "Maliyet modeli")}
R1_NAME = (None, "Engine uyumu")
SOURCE = {"R1": (None, "engine'in doğası"), "R2": (None, "ikisi birlikte: engine'in ölçeklenme modeli ve servisin kapasite yönetimi"), "R3": (None, "üreticinin servis tasarımı"),
          "R4": (None, "üreticinin servis tasarımı"), "R5": (None, "üreticinin servis tasarımı")}
PAGE_SVC = {"dynamodb": "ddb"}
RACE_GAP = 5      # a gap of 5 points or less between the first two candidates is a close race (information only)


def _t(tr, en=None):
    return (en, tr)


def row(code, weight, wwhy, want, why):
    """code: an R1 catalog code (VM, ŞE, ...) or R2..R5."""
    assert code in R1_CATALOG or code in R_REST, code
    return {"code": code, "w": weight, "wwhy": (None, wwhy), "want": (None, want), "why": (None, why)}


def sc(points, reason):
    return (points, (None, reason))


def fmt(x):
    """Turkish number: 93.3 -> 93,3; 95.0 -> 95."""
    return f"{x:.1f}".rstrip("0").rstrip(".").replace(".", ",")


def wusecase(uid, no, title, key, story, wnote, rows, cands, scores, h2h, verdict, sim=None):
    """verdict may name totals as {ddb}, {ec}, ... (filled from the scores, so a total can never differ)."""
    r1 = [r for r in rows if r["code"] in R1_CATALOG]
    assert 3 <= len(r1) <= 5 and rows[:len(r1)] == r1, f"{uid}: 3-5 R1 sub-items first"
    assert [r["code"] for r in rows[len(r1):]] == ["R2", "R3", "R4", "R5"], f"{uid}: R2-R5 after R1"
    assert sum(r["w"] for r in rows) == 100, f"{uid}: weights sum to {sum(r['w'] for r in rows)}"
    assert all(r["w"] >= 5 for r in rows[len(r1):]), f"{uid}: R2-R5 weight below 5"
    assert len(cands) == 3 and all(len(scores[c]) == len(rows) for c in cands), uid
    total = {c: round(sum(p * r["w"] / 10 for (p, _), r in zip(scores[c], rows)), 1) for c in cands}
    order = sorted(cands, key=lambda c: -total[c])
    assert order == cands, f"{uid}: candidates must be in the order of the totals {total}"
    assert set(h2h) == set(cands[1:]), f"{uid}: a head-to-head text for every candidate after the best fit"
    for i, r in enumerate(r1):
        r["label"] = f"R1.{i + 1}"
    for r in rows[len(r1):]:
        r["label"] = r["code"]
    return {"id": uid, "no": no, "sim": sim, "title": (None, title), "key": (None, key), "story": (None, story),
            "wnote": (None, wnote), "rows": rows, "cands": cands, "scores": scores, "total": total,
            "h2h": {c: (None, t) for c, t in h2h.items()}, "verdict": (None, verdict.format(**{c: fmt(v) for c, v in total.items()}))}


# The stories and the R2-R5 texts of the ten DynamoDB workloads stay as in model 1; R1 is new.
from .e2e_usecases import DDB_USECASES as _M1  # noqa: E402

_OLD = {uc["id"]: uc for uc in _M1}


def story(uid):
    return _OLD[uid]["story"][1]


def rest(uid, w2, w3, w4, w5, why2, why3, why4, why5):
    """R2-R5 rows with the 'what we need' and 'why it matters' texts of model 1, and the new weights with their reasons."""
    reqs = _OLD[uid]["reqs"]
    strip = lambda t: re.sub(r"\s*(Bu gereksinim bu kartta zorunludur|Bu kartta zorunlu)\.", "", t)   # model 2 has no must rows
    return [row(f"R{i + 2}", w, wy, strip(reqs[i + 1]["want"][1]), strip(reqs[i + 1]["why"][1]))
            for i, (w, wy) in enumerate(((w2, why2), (w3, why3), (w4, why4), (w5, why5)))]


DDB_W = []

# ------------------------------------------------------------------ 1. shopping cart
DDB_W.append(wusecase("cart", 1, sim="w_cart",
    title="Alışveriş sepetleri (Lale Market)",
    key="Key: sepet, sonra ürün. Value: miktar, fiyat, süre sonu.",
    story=story("cart"),
    wnote="R1 toplam 50: sepetin dört engine sorusu (nasıl okunur, kural nasıl korunur, nasıl yazılır, nasıl biter) her istekte çalışır. "
          "R2 25 ile ikinci: kampanya akşamının 20 katlık sıçraması bu iş yükünün en riskli anıdır. Sepet resmi kayıt olmadığı için R3 10'da kalır; "
          "R4 ve R5 önemlidir ama sepet kararını tek başına çevirmez.",
    rows=[
        row("EY", 15, "Sepet sayfası her açılışta bu soruyu sorar; en sık soru budur.",
            "Tek soru: \"bu sepetin bütün satırları, ürün sırasıyla\". Uygulama her istekte ziyaretçi id'sini bilir. Sepetler birbirinden bağımsızdır: hiçbir soru iki sepeti birden okumaz.",
            "Satırlar tek tek okunursa sepet sayfası satır sayısı kadar yavaşlar. Sıra uygulamada kurulursa her istekte aynı sıralama işi tekrarlanır."),
        row("TA", 15, "Kural bozulursa stok planı bozulur; iki sekme yarışı kampanya akşamında gerçek bir durumdur.",
            "\"Bu sepetteki bu ürüne 2 adet ekle, ama toplam 5'i geçmesin\" kuralı iki tarayıcı sekmesi aynı anda eklese bile korunmalı. Checkout sepeti son hâliyle okumalı.",
            "Kural \"önce oku, sonra yaz\" ile korunursa iki sekme arasında yarış olur ve sınır aşılır: bir müşteri kampanya ürününden 50 adet alabilir."),
        row("OY", 10, "Her \"Sepete ekle\" bir yazmadır, ama biçimi basittir: miktar artır ya da satır ekle.",
            "Yazmaların biçimi: miktarı okumadan artırmak, yeni satır eklemek ve checkout'tan sonra sepetin bütün satırlarını silmek.",
            "Her artırma önce okuyup sonra yazarsa istek sayısı ikiye katlanır ve yarış penceresi açılır. Sepeti silmek satır satır yapılırsa checkout uzar."),
        row("YD", 10, "Sepetlerin yüzde 70'i terk edilir; bu veri kendiliğinden gitmezse birikir.",
            "Terk edilen sepet bir gün sonra kendiliğinden silinmeli; uygulama bir temizlik işi işletmemeli.",
            "Temizlenmeyen sepetler storage maliyetini her gün artırır. Bir temizlik işi küçük bir ekip için bir bakım yüküdür ve kampanya gecesi database'e yük bindirir."),
    ] + rest("cart", 25, 10, 8, 7,
             "Kampanya akşamı 10 dakikada 20 kat sıçrama: elle müdahale gerekirse yılın en değerli üç saati riske girer.",
             "Sepet bir ön hazırlıktır, sipariş Aurora'da kalıcıdır; kayıp kızgın bir müşteri demektir ama para kaybı değildir.",
             "Ekip küçük ve database yöneticisi yok; ama bu, engine uyumundan sonra gelir.",
             "Sepet verisi küçüktür; maliyeti asıl belirleyen trafik şeklidir ve bu R2 ile birlikte okunur."),
    cands=["ddb", "ec", "aur"],
    scores={
        "ddb": [sc(10, "Partition key sepet, sort key ürün (Ö3): sepetin bütün satırları tek bir Query ile, ürün sırasıyla gelir. Puan kırılmadı."),
                sc(8, "\"En fazla 5\" kuralı UpdateItem'a eklenen bir koşulla (Ö5) tek yazmada korunur; iki sekme yarışırsa ikincisi reddedilir. Checkout strongly consistent okuma ister. "
                      "2 puan kırıldı: checkout'un \"sepeti oku, siparişi yaz, sepeti sil\" adımları iki ayrı database'tedir; DynamoDB transaction'ı yalnız kendi value'larını kapsar ve bir arızada eski sepet kalabilir."),
                sc(9, "UpdateItem ADD miktarı okumadan artırır (Ö5); yeni satır PutItem'dır. 1 puan kırıldı: partition key ile toplu silme yoktur (A6); checkout'tan sonra her satır ayrı silinir (BatchWriteItem 25'er)."),
                sc(8, "TTL alanı terk edilen sepeti uygulama silmeden temizler (Ö6). 2 puan kırıldı: silme \"genellikle birkaç gün içinde\" olur; süresi dolmuş satırlar o arada okunabilir ve okuma onları expires_at ile elemelidir."),
                sc(10, "Yazmalar ziyaretçi id'sinin hash'iyle partition'lara dağılır (Ö2); on-demand mod saniyede 250'den 5.000 yazmaya ayar olmadan çıkar, key ile okuma tepe anında da tek haneli milisaniyedir. Puan kırılmadı."),
                sc(10, "Her yazma onaydan önce birkaç Availability Zone'da saklanır; bir AZ arızası sepet kaybetmez. Puan kırılmadı."),
                sc(10, "Serverless: instance, yama ve kapasite planı yoktur; ekip bildiği AWS SDK ile çalışır. Puan kırılmadı."),
                sc(9, "On-demand modda istek ve saklanan GB başına ödenir; boş günlerde maliyet sıfıra yakındır. 1 puan kırıldı: strongly consistent okumalar ve koşullu yazmalar kampanya akşamı daha çok birim tüketir; tepe maliyeti hesaplanmalıdır.")],
        "ec": [sc(9, "Sepet bir Valkey hash'idir: HGETALL bütün satırları tek komutta, bellekten getirir. 1 puan kırıldı: hash alanlarının sırası yoktur; ürün sırasını uygulama kurar."),
               sc(6, "Valkey komutları tek thread'de sırayla çalışır, bu yüzden HINCRBY atomiktir. 4 puan kırıldı: HINCRBY'de \"5'i geçmesin\" koşulu yoktur; kural bir Lua script'i ya da WATCH/MULTI ile yazılır ve kuralı uygulama kodu taşır; checkout da DynamoDB'deki gibi iki database'e yayılır."),
               sc(10, "HINCRBY miktarı okumadan artırır, HSET satır ekler, DEL bütün sepeti tek komutta siler. Puan kırılmadı."),
               sc(10, "EXPIRE sepet key'ine süre koyar ve süre dolunca sepet tam anında görünmez olur; bütün sepet birlikte gider, istenen de budur. Puan kırılmadı."),
               sc(9, "Bellekten mikrosaniyelerde cevap; Serverless kendi kendine ölçeklenir. 1 puan kırıldı: Serverless kapasitesini 2-3 dakikada iki katına çıkarır; on dakikada 20 kat için kampanyadan önce minimum ECPU ayarı (pre-scaling) önerilir."),
               sc(4, "Serverless veriyi birkaç AZ'de replica olarak tutar, ama her yazmayı kalıcı bir log'a yazmaz; bir arıza son sepetleri kaybedebilir. 6 puan kırıldı: bu iş yükünde sepet kaybı istenmeyen bir sonuçtur."),
               sc(10, "Serverless, instance yok. Puan kırılmadı: Lua script'i R1.2'de sayıldı."),
               sc(7, "Saklanan veri (GB-saat) ve istek (ECPU) başına ödenir. 3 puan kırıldı: bellekteki GB diskteki GB'tan çok daha pahalıdır; terk edilen sepetler süresi dolana kadar bellekte yer tutar.")],
        "aur": [sc(9, "SELECT … WHERE cart_id = ? ORDER BY product_id, (cart_id, product_id) primary key'inin B-tree index'inden okunur. 1 puan kırıldı: PostgreSQL row'ları index sırasıyla saklamaz; satırlar index'ten sonra heap'ten ayrı ayrı okunur."),
                sc(10, "UPDATE … SET qty = qty + 2 WHERE … AND qty + 2 <= 5 row kilidiyle korunur; sepet, stok ve sipariş aynı database'teyse checkout tek bir transaction'dır. Puan kırılmadı: bu satırda en güçlü aday Aurora'dır."),
                sc(9, "UPDATE miktarı okumadan artırır; DELETE FROM cart WHERE cart_id = ? sepeti tek komutta siler. 1 puan kırıldı: her UPDATE MVCC ile yeni bir row sürümü yazar; sık güncellenen sepetler VACUUM işini artırır."),
                sc(4, "PostgreSQL'de TTL yoktur. 6 puan kırıldı: terk edilen sepetler için zamanlanmış bir DELETE işi (pg_cron) gerekir ve günde milyonlarca satırı silmek VACUUM yükü getirir."),
                sc(6, "Saniyede 5.000 küçük yazma güçlü bir writer'ın erişimindedir; Serverless v2 ACU'yu artırır. 4 puan kırıldı: sepet tablosu siparişlerin writer'ına eklenir ve kampanya akşamının 5.000 yazması checkout tepesiyle aynı andadır (Aurora sayfasının tek writer tablosu: 5.000'e kadar, checkout ile aynı tepede 3 puan); on dakikada 20 kat için minimum ACU da önceden yükseltilir (sabit 1 puan)."),
                sc(10, "Üç AZ'de altı kopya ve sürekli yedek. Puan kırılmadı."),
                sc(7, "Lale Market siparişler için zaten bir Aurora işletir; sepet tablosu oraya eklenir. 3 puan kırıldı: kampanya yükü siparişlerle aynı cluster'a biner ve ACU aralığı ile connection pool ayarı database yöneticisi olmayan ekibin işidir."),
                sc(7, "Var olan Aurora'da sepet tablosu ayrıca ödenmez. 3 puan kırıldı: kampanya akşamı için ACU üst sınırı ve minimum ACU yükseltilir; tepe kapasitesi siparişlerle paylaşılır ve ACU-saat olarak ödenir.")],
    },
    h2h={
        "ec": "Bellek içi key-value (ElastiCache) ile kafa kafaya. R1'de iki engine birbirine çok yakındır: ElastiCache hash'i sepetin doğal şeklidir, DEL sepeti tek komutta siler ve EXPIRE tam anındadır; "
              "DynamoDB ise sıralı satırlarda ve \"en fazla 5\" kuralında öndedir, çünkü kural tek bir koşuldur, Lua script'i değildir. Engine uyumunda fark iki puandan azdır. "
              "Kararı R3 verir: ElastiCache Serverless'ta her yazmayı kalıcı kılan bir log yoktur ve kampanya gecesi bir arıza son sepetleri götürebilir; DynamoDB'de her yazma birkaç AZ'de saklanır. "
              "Bellekteki GB'ın fiyatı da terk edilen sepetler biriktikçe R5'te farkı açar. "
              "Hangi koşul değişseydi ElastiCache seçilirdi: sepet başka bir sistemde zaten kalıcı olsaydı ve buradaki kopya sadece hızlı bir önbellek olsaydı ya da sepet okuması her sayfa isteğinin önünde durup milisaniyenin altını isteseydi.",
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Aurora R1'in kural satırında en güçlü adaydır: sepet, stok ve sipariş aynı database'teyse checkout tek bir transaction'dır ve eski sepet kalma riski yoktur. "
               "Ama R1'in diğer satırları ve R2 DynamoDB'yi öne geçirir: PostgreSQL'de TTL yoktur ve günde milyonlarca terk edilen sepeti silmek bir iş ve VACUUM yüküdür; "
               "kampanya akşamının on dakikada 20 kat sıçraması tek writer'ın ve minimum ACU'nun sınırına dayanır. "
               "Bu iş yükünde sepet resmi kayıt değildir, sipariş zaten Aurora'da kalıcıdır; bu yüzden checkout'un iki adımı kabul edilebilir bir bedeldir. "
               "Hangi koşul değişseydi Aurora seçilirdi: sepete eklenen ürün stoktan anında düşülmek zorunda olsaydı, yani sepet ve stok tek transaction'da kilitlenmeliyse, ya da trafik düz ve tek writer'ın rahat erişiminde olsaydı.",
    },
    verdict="Karar: DynamoDB {ddb}, ElastiCache {ec}, Aurora {aur}. Bu iş yüküne en uygun servis DynamoDB'dir. Engine uyumunda üç aday birbirine yakındır; DynamoDB'yi öne geçiren, sıralı satırları, tek koşullu kuralı ve kendiliğinden giden sepetleri aynı anda vermesi ve kampanya sıçramasını ayarsız karşılamasıdır. "
            "DynamoDB seçtiğimizde artımız: kampanya gecesi kimse database'e dokunmaz, sepet kuralı tek istekte korunur, terk edilen sepetler kendiliğinden gider, boş günlerde maliyet sıfıra yakındır. "
            "Eksimiz: checkout iki database'e yayılır; uygulama arızadan sonra kalan sepeti temizlemeli ve checkout'ta strongly consistent okuma kullanmalıdır. Bir koşul değişseydi: sepet ve stok tek transaction'da kilitlenmek zorunda olsaydı Aurora kazanırdı."))

# ------------------------------------------------------------------ 2. user profiles
DDB_W.append(wusecase("profile", 2,
    title="Kullanıcı profilleri ve tercihleri",
    key="Key: kullanıcı id'si. Value: ad, dil, adresler, bildirim tercihleri.",
    story=story("profile"),
    wnote="R1 toplam 50: profilin şekli (iç içe nesne), her çeyrek değişen alanları ve tek tercihin güncellenmesi, hangi engine'in bu veriyi doğal taşıdığını belirler. "
          "R4 bu kartta 12'dir, çünkü ekip MongoDB API'sini ve SQL'i az biliyor ve sunucu istemiyor; R2 20'dir, çünkü okuma hacmi büyük ama düzenlidir.",
    rows=[
        row("VM", 15, "Profil tek bir iç içe nesnedir; engine'in bu şekli doğal taşıması her okuma ve yazmayı etkiler.",
            "Profil tek bir nesnedir: ad, dil, abonelik durumu, bir adres listesi ve bir tercih haritası. Profil küçüktür (4 KB'tan az).",
            "Nesne parçalara bölünüp birkaç yerde tutulursa her ekran birkaç okuma yapar; iç içe yapı düz bir string'e çevrilirse içindeki tek bir alan değiştirilemez."),
        row("ŞE", 10, "Her çeyrek yeni bir alan gelir; engine buna migration'sız izin vermezse pazarlama takvimi database'e bağlanır.",
            "Pazarlama ekibi her çeyrek yeni bir alan ekler (\"podcast önerisi ister mi\", \"doğum günü\"); alan sadece yeni kullanıcılarda dolu başlar. Migration ve kesinti olmamalı.",
            "Her çeyrek bir ALTER TABLE ya da bir migration penceresi, pazarlama ekibinin takvimini database ekibine bağlar."),
        row("EY", 10, "Her ekran bu soruyla başlar, ama soru basittir: id ile tek bir profil. İş yükünü ayıran bu değil, bu yüzden ağırlığı orta.",
            "Tek soru: \"bu kullanıcı id'sinin profili\". Uygulama id'yi login'den bilir. Profiller birbirinden bağımsızdır.",
            "Her ekran bu okumayla başlar; yavaşsa her ekran yavaştır."),
        row("OY", 15, "Ayda bir küçük değişiklik olur ama doğru yapılmazsa başka cihazdan gelen değişikliği ezer.",
            "Bir tercihi değiştirmek ya da adres listesindeki ikinci adresi güncellemek, profilin tamamını yeniden yazmadan yapılmalı.",
            "Bir tercih için profilin tamamını yeniden yazmak, aynı anda başka bir cihazdan yapılan değişikliği ezebilir."),
    ] + rest("profile", 20, 10, 12, 8,
             "Saniyede 30.000 okuma ve yılda iki kat büyüme; ama trafik düzenlidir, sıçrama yoktur.",
             "Profil kalıcı veridir; kaybı güven kaybıdır, para kaybı değildir.",
             "Beş geliştirici AWS SDK biliyor, MongoDB API'sini ve SQL'i az biliyor, sunucu istemiyor; bilmedikleri bir API ve sunucu boyutlandırma doğrudan hata riskidir.",
             "Okuma ağırlıklı düzenli trafik; iki ödeme modeli de uyar, fark büyümede ortaya çıkar."),
    cands=["ddb", "doc", "aur"],
    scores={
        "ddb": [sc(9, "Profil tek bir value'dur; adresler bir list, tercihler bir map alanıdır (Ö4). 1 puan kırıldı: tarih gibi tipler yoktur (doğum günü string ya da sayı olarak saklanır) ve iç içe alanlar database tarafından doğrulanmaz."),
                sc(10, "Sadece key alanları tanımlanır; yeni alan yalnız yeni value'lara yazılır (Ö4), migration yoktur. Puan kırılmadı."),
                sc(10, "Simple primary key = kullanıcı id'si; GetItem tek okumadır (Ö1). Puan kırılmadı."),
                sc(8, "UpdateItem bir doküman yolunu değiştirir (SET prefs.podcast = :v); profilin tamamı yazılmaz. 2 puan kırıldı: listedeki bir adres yalnız index numarasıyla (addresses[1]) değiştirilir; uygulama numarayı bilmeli ve araya giren bir ekleme numarayı kaydırabilir, bunun için bir koşul (Ö5) eklenmelidir."),
                sc(10, "Okumalar partition'lara dağılır (Ö2); 30.000 okuma ve yılda iki kat büyüme için hiçbir şey değişmez. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır; point-in-time recovery açılabilir. Puan kırılmadı."),
                sc(10, "Serverless; ekip bildiği SDK'yı kullanır. Puan kırılmadı."),
                sc(10, "Düz trafikte provisioned + auto scaling ucuzdur ve maliyet kullanıcı sayısıyla doğrusal artar; 4 KB'tan küçük bir profil tek okuma birimidir. Puan kırılmadı.")],
        "doc": [sc(10, "Profil doğal bir document'tır: iç içe nesneler ve diziler BSON olarak saklanır ve içindeki her alan index'lenebilir ve sorgulanabilir. Puan kırılmadı."),
                sc(10, "Şema serbesttir; yeni alan sadece yeni document'lara yazılır. Puan kırılmadı."),
                sc(10, "find({_id}) tek okumadır. Puan kırılmadı."),
                sc(10, "updateOne ile $set iç içe bir alanı, arrayFilters ise listedeki doğru adresi koşulla bulup değiştirir; profilin tamamı yazılmaz. Puan kırılmadı: bu satırda en doğal aday DocumentDB'dir."),
                sc(7, "Okumalar en fazla 15 replica'ya dağılır ve 30.000 okuma karşılanır; saniyede 100 yazma primary için küçüktür. 3 puan kırıldı: okuma ölçeği replica sayısı ve instance sınıfıyla sağlanır; yılda iki kat büyüme her yıl bir kapasite adımıdır."),
                sc(10, "Üç AZ'de altı kopya ve sürekli yedek. Puan kırılmadı."),
                sc(6, "Yedek ve yama yönetilir. 4 puan kırıldı: instance sınıfı ve replica sayısı ekibin işidir ve MongoDB API'si bu ekip için yenidir."),
                sc(7, "Instance saat başına ve I/O başına ödenir. 3 puan kırıldı: gece düşük trafikte de instance'lar çalışır; büyümede bir sınıf atlamak maliyeti sıçratır.")],
        "aur": [sc(7, "Profil bir JSONB kolonunda tutulabilir ya da tablolara bölünebilir. 3 puan kırıldı: JSONB içindeki alanların tipini database denetlemez; tablolara bölmek ise her okumayı JOIN yapar."),
                sc(7, "JSONB içine alan eklemek migration istemez. 3 puan kırıldı: JSONB dışındaki her yeni alan bir ALTER TABLE'dır ve ekip iki yeri birden yönetir."),
                sc(10, "Primary key ile okuma tek bir B-tree aramasıdır. Puan kırılmadı."),
                sc(6, "jsonb_set iç içe bir alanı değiştirir. 4 puan kırıldı: PostgreSQL'in MVCC'si tek alan için de row'un tamamını yeni sürüm olarak yazar ve listede doğru adresi bulmak bir alt sorgu ister."),
                sc(7, "Reader instance'lar 30.000 okumayı taşır. 3 puan kırıldı: reader sayısı ve sınıfı ekip tarafından seçilir; büyüme bir kapasite projesidir."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(6, "Yönetilen servis. 4 puan kırıldı: ekip SQL'i az biliyor; connection pool ve reader yönlendirmesi uygulama tarafında ayarlanır."),
                sc(7, "Instance ya da ACU saat başına ödenir. 3 puan kırıldı: gece düşük trafikte de kapasite ödenir; büyüme bir sınıf atlatır.")],
    },
    h2h={
        "doc": "Document (DocumentDB) ile kafa kafaya. R1'de DocumentDB kazanır ve bunu açıkça söylemek gerekir: profil doğal bir document'tır, arrayFilters listedeki doğru adresi koşulla bulur, iç içe her alan index'lenebilir. "
               "DynamoDB aynı veriyi map ve list alanlarıyla taşır ama liste içi güncellemede index numarasına bağlıdır. Engine uyumunda fark 4,5 puandır. "
               "Kararı bu kartın öncelikleri verir: ekip MongoDB API'sini bilmiyor ve sunucu istemiyor (R4 12); yılda iki kat büyüme DocumentDB'de replica ve instance sınıfıyla yönetilen bir kapasite adımıdır, DynamoDB'de hiçbir şey değişmez (R2). "
               "Bu iki gereksinim engine uyumundaki farkı kapatır ve DynamoDB'yi öne geçirir. "
               "Hangi koşul değişseydi DocumentDB seçilirdi: ekip MongoDB'yi zaten iyi biliyor olsaydı ya da profilin içindeki alanlara göre sorgular (\"İzmir'de oturan ve podcast isteyenler\") uygulamanın ana işi olsaydı.",
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Aurora profili okumakta hızlıdır, ama R1'in diğer satırlarında geride kalır: iç içe nesne ya bir JSONB kolonunda tipsiz durur ya da tablolara bölünüp her okumada JOIN ister; "
               "her çeyrek gelen alan JSONB dışında bir ALTER TABLE'dır; PostgreSQL'in MVCC'si tek bir tercih için row'un tamamını yeniden yazar. "
               "R2 ve R4'te de reader instance'ları ve connection pool'u küçük ve SQL bilmeyen bir ekibe iş bırakır. "
               "Hangi koşul değişseydi Aurora seçilirdi: profil başka tablolarla (abonelik, fatura, aile hesabı) kurallarla bağlı olsaydı ve bu kurallar database'te korunmak zorunda olsaydı, ya da ekip SQL'i iyi biliyor ve zaten bir Aurora işletiyor olsaydı.",
    },
    verdict="Karar: DynamoDB {ddb}, DocumentDB {doc}, Aurora {aur}. Bu iş yüküne en uygun servis DynamoDB'dir, ama engine uyumunda DocumentDB öndedir; DynamoDB'yi öne geçiren bu ekibin önceliği olan ölçek ve operasyondur. "
            "DynamoDB seçtiğimizde artımız: büyüme için hiçbir şey değişmez, yeni alan migration istemez, ekip bildiği SDK ile çalışır. "
            "Eksimiz: liste içi güncelleme index numarasıyla yapılır ve bir koşulla korunmalıdır; profil 400 KB'a yaklaşırsa büyüyen kısım ayrı table'a taşınmalıdır. Bir koşul değişseydi: ekip MongoDB'yi biliyor olsaydı DocumentDB kazanırdı."))

# ------------------------------------------------------------------ 3. sessions and login tokens
DDB_W.append(wusecase("session", 3, sim="w_session",
    title="Oturumlar ve login token'ları",
    key="Key: session id. Value: kullanıcı, rol, son görülme zamanı.",
    story=story("session"),
    wnote="R1 toplam 55 ve en büyük: oturumun doğası (her istekte oku ve süresini yenile, 30 dakikada tam anında düş, milisaniyenin altında cevap ver) engine'in algoritmasıyla doğrudan ilgilidir. "
          "R3 5'te, en düşük sınırdadır: kaybolan oturum yalnız yeni bir login'dir.",
    rows=[
        row("EY", 10, "Soru her istekte sorulur ama basittir: id ile tek bir oturum. İş yükünü süre sonu ve hız ayırır.",
            "Tek soru: \"bu session id'nin oturumu\". Uygulama session id'yi cookie'den bilir. Oturum küçük bir nesnedir (1 KB'tan az).",
            "Bu okuma her HTTP isteğinin önündedir; key ile doğrudan gidilemezse her sayfa yavaşlar."),
        row("YD", 20, "Oturumun güvenliği süre sonuna bağlıdır: süresi dolan oturum asla okunmamalı.",
            "Oturum 30 dakika hareketsizlikten sonra düşmeli; 30 dakika 1 saniye sonra gelen istek yeni login'e gitmeli. Süre her sayfa görüntülemede yenilenmeli.",
            "Süresi dolmuş bir oturum hâlâ okunabiliyorsa, ortak bir bilgisayarda bırakılan oturum başkası tarafından kullanılabilir. Bu bir güvenlik açığıdır."),
        row("OY", 10, "Her istekte bir okuma ve bir yenileme olur; ikisinin tek işlem olması isteği yarıya indirir.",
            "Her istekte oturumu oku ve süresini yenile; bu, uygulama kodunda tek satır ve mümkünse tek istek olmalı.",
            "Okuma ve yenileme iki ayrı istekse saniyede 40.000 sayfa için 80.000 istek gerekir ve her sayfa iki gidiş-dönüş bekler."),
        row("DA", 15, "1 ms sınırı bir trafik sayısı değil, engine'in veriyi nerede ve nasıl tuttuğunun sonucudur.",
            "Okuma 1 milisaniyenin altında dönmeli, çünkü her sayfa isteğine eklenir.",
            "Disk tabanlı bir engine'in tek haneli milisaniyesi bile günde milyonlarca sayfada hissedilir: 5 ms her sayfaya 5 ms ekler."),
    ] + rest("session", 20, 5, 10, 10,
             "Saniyede 40.000 okuma ve 40.000 yenileme, gün içinde dalgalı.",
             "Kaybolan oturum yalnız yeni bir login'dir; sepet ve sipariş başka yerde kalıcıdır.",
             "Ekip sunucu istemiyor; ama oturum basit bir iş yüküdür ve operasyon farkı küçüktür.",
             "Veri küçük ve kısa ömürlüdür; fark istek başına fiyatta ve sürekli çalışan kapasitededir."),
    cands=["ec", "mdb", "ddb"],
    scores={
        "ec": [sc(10, "GET session:{id} key ile doğrudan okumadır. Puan kırılmadı."),
               sc(10, "EXPIRE süreyi saniyesinde uygular; süresi dolmuş bir key hiçbir zaman döndürülmez. Puan kırılmadı."),
               sc(10, "GETEX session:{id} EX 1800 oturumu okur ve süresini aynı komutta yeniler: tek istek, tek satır. Puan kırılmadı."),
               sc(10, "Valkey bütün veriyi bellekteki bir hash table'da tutar; cevap mikrosaniyelerdedir. Puan kırılmadı."),
               sc(10, "Serverless kendi kendine ölçeklenir ve okumalar milisaniyenin altındadır. Puan kırılmadı."),
               sc(4, "Serverless veriyi birkaç AZ'de replica olarak tutar, ama kalıcı bir yazma log'u yoktur. 6 puan kırıldı: bir arızada kullanıcılar yeniden login olabilir; bu kartta kabul edilen bir sonuçtur."),
               sc(10, "Serverless: node ve yama yoktur. Puan kırılmadı."),
               sc(8, "Saklanan veri ve ECPU başına ödenir. 2 puan kırıldı: bellekteki GB pahalıdır; ama oturum verisi birkaç GB'ı geçmediği için bu fark küçüktür.")],
        "mdb": [sc(10, "Aynı Valkey engine'i: GET key ile doğrudan okumadır. Puan kırılmadı."),
                sc(10, "EXPIRE aynı biçimde saniyesinde çalışır. Puan kırılmadı."),
                sc(10, "GETEX okuma ve yenilemeyi tek komutta yapar. Puan kırılmadı."),
                sc(10, "Veri bellekteki hash table'dadır; okumalar mikrosaniyelerdedir. Puan kırılmadı."),
                sc(7, "Okumalar mikrosaniyede kalır. 3 puan kırıldı: her yenileme bir yazmadır ve MemoryDB yazmayı çoklu AZ log'una işledikten sonra onaylar (tek haneli milisaniye); ayrıca shard ve node sayısını ekip seçer."),
                sc(10, "Her yazma çoklu AZ'li bir transaction log'unda kalıcıdır; bir arıza oturum kaybetmez. Puan kırılmadı."),
                sc(6, "Yama ve failover yönetilir. 4 puan kırıldı: MemoryDB'de serverless seçenek yoktur; node tipi, shard ve replica sayısı ekibin işidir."),
                sc(5, "Node saat başına ve yazılan veri başına ödenir. 5 puan kırıldı: dalgalı trafiğe rağmen node'lar tepe için boyutlanır ve gece de ödenir; bu kartın ihtiyaç duymadığı dayanıklılığa para verilir.")],
        "ddb": [sc(10, "GetItem session id ile doğrudan okumadır (Ö1). Puan kırılmadı."),
                sc(6, "TTL alanı süresi dolan oturumu siler (Ö6) ve okuma bir koşulla süresi dolmuş oturumu reddedebilir. 4 puan kırıldı: silme \"genellikle birkaç gün içinde\" olur; \"süresi dolan asla okunmamalı\" isteği ancak uygulamanın her okumada expires_at'i karşılaştırmasıyla karşılanır."),
                sc(6, "UpdateItem SET expires_at ve ReturnValues = ALL_NEW okuma ve yenilemeyi tek istekte yapar (Ö5). 4 puan kırıldı: böylece her sayfa görüntüleme bir yazma olur; yazma okumadan yavaş ve pahalıdır ve saniyede 40.000 sayfa saniyede 40.000 yazma demektir."),
                sc(5, "Veri SSD'deki partition'lardadır; key ile okuma tek haneli milisaniyedir. 5 puan kırıldı: 1 ms sınırı tek başına karşılanmaz; mikrosaniye için önüne DAX (bellek içi cache) konmalıdır."),
                sc(10, "Partition'lara dağılım (Ö2) 40.000 okumayı ve yazmayı kolayca taşır. Puan kırılmadı: gecikme engine'in depolamasından gelir ve R1.4'te (DA) bir kez sayıldı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı: bu satırda en güçlü aday, ama bu kartta dayanıklılık önemsizdir."),
                sc(10, "Serverless. Puan kırılmadı: süre kontrolünün kodu R1.2'de sayıldı."),
                sc(6, "İstek başına ödenir. 4 puan kırıldı: her sayfada bir yenileme yazması, saniyede 40.000 yazma birimi demektir; bellek içi store'un istek fiyatından çok yüksektir.")],
    },
    h2h={
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. Bu karşılaştırma R1 ile R3–R5'in farkını en net gösteren karşılaştırmadır: iki aday aynı Valkey engine'ini çalıştırır ve R1'de ikisi de tam puan alır. "
               "Fark yalnız üreticinin servis tasarımındadır. MemoryDB her yazmayı çoklu AZ'li bir log'a işler; bu, oturumu bir arızadan korur ama her süre yenilemesini tek haneli milisaniyelik bir yazmaya çevirir. "
               "Serverless seçeneği olmadığı için node'lar tepe için boyutlanır ve gece de ödenir. Bu kartta dayanıklılığın ağırlığı en düşük sınırdadır (5), çünkü kaybolan oturum yalnız yeni bir login'dir. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: oturum kaybı pahalı olsaydı (örneğin bir bankacılık işleminin ortasındaki oturum) ya da oturumda yeniden kurulamayan bir durum (çok adımlı bir başvuru formu) tutulsaydı.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB bu kartta üçüncüdür ve nedeni R1'dedir, yani engine'in doğasındadır. "
               "Oturumun iki temel ihtiyacı DynamoDB'nin algoritmasıyla çelişir: süre sonu tam anında olmalıdır, ama DynamoDB TTL'i arka planda ve günler içinde siler; okuma milisaniyenin altında olmalıdır, ama DynamoDB veriyi SSD'deki partition'larda tutar. "
               "Okuma ve yenileme tek bir UpdateItem olabilir, ama bu her sayfayı bir yazmaya çevirir. DynamoDB'nin güçlü olduğu dayanıklılık ise bu kartta en düşük ağırlıktadır. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: oturum kaybı kabul edilemez olsaydı ve 5–10 ms yeterli olsaydı, ya da oturum okuması her istekte değil yalnız login'de yapılsaydı (örneğin imzalı token kullanan bir mimaride yalnız iptal listesi tutulsaydı).",
    },
    verdict="Karar: ElastiCache {ec}, MemoryDB {mdb}, DynamoDB {ddb}. Bu iş yüküne en uygun servis ElastiCache'tir; DynamoDB bu kartta üçüncüdür. Engine uyumunda iki Valkey servisi eşittir; ElastiCache'i öne geçiren serverless işletimi ve bu kartın istemediği dayanıklılığa para ödetmemesidir. "
            "Yine de DynamoDB seçersek artımız: oturumlar bir arızadan sağ çıkar, ekip tek bir database ile çalışır. "
            "Eksimiz: süre kontrolünü uygulama yazar, her sayfa bir yazma birimi harcar, 1 ms sınırı için DAX eklenmelidir. Bir koşul değişseydi: oturum kaybı pahalı olsaydı MemoryDB kazanırdı."))

# ------------------------------------------------------------------ 4. game state and player inventory
DDB_W.append(wusecase("game", 4,
    title="Oyun durumu ve oyuncu envanteri",
    key="Key: oyuncu, sonra nesne türü ve id'si. Value: türe göre değişen alanlar.",
    story=story("game"),
    wnote="R1 toplam 45 ve yine en büyük: envanterin okunma yolu, türe göre değişen nesneler ve satın almanın atomikliği oyunun her ekranındadır. "
          "R2 bu kartta 30'dur, çünkü lansman günü 200.000 istek/saniye ve bir ay sonra on kat düşüş bu iş yükünün en büyük riskidir.",
    rows=[
        row("EY", 10, "İki okuma sorusu her açılışta ve her savaşta sorulur.",
            "Sorular: \"bu oyuncunun bütün envanteri\" ve \"bu oyuncunun sadece silahları\". Oyuncu id'si her istekte bilinir; oyuncular birbirinden bağımsızdır.",
            "Silahlar için bütün envanteri okuyup filtrelemek, 500 nesnelik envanterde savaş ekranını yavaşlatır."),
        row("VM", 10, "Nesnelerin alanları türe göre farklıdır; engine bu çeşitliliği taşımalı.",
            "Bir kılıçta hasar ve dayanıklılık, bir iksirde süre ve etki vardır. Her nesne küçüktür.",
            "Bütün türler tek bir sabit kolon listesine sıkıştırılırsa kolonların çoğu boş kalır ve her yeni tür bir değişiklik ister."),
        row("ŞE", 10, "Her oyun güncellemesi yeni nesne türü getirir.",
            "Yeni nesne türü migration olmadan eklenebilmeli.",
            "Her güncellemede bir migration, lansman sonrası hızlı güncelleme döngüsünü yavaşlatır."),
        row("TA", 15, "Satın alınan nesnenin kaybolması para iadesi demektir; kural engine'de korunmalı.",
            "\"Bu nesneyi bu oyuncuya ekle ve altınını düş\" tek bir bütün olarak olmalı; \"bu nesnenin dayanıklılığını 3 azalt\" sıfırın altına inmemeli.",
            "Altın düşüp nesne eklenmezse oyuncu para kaybeder; iki istek yarışırsa dayanıklılık eksiye iner."),
    ] + rest("game", 30, 10, 8, 7,
             "Lansman günü saniyede 200.000 istek, bir ay sonra 20.000; lansman gecesi elle müdahale olmamalı. Bu kartın en büyük riski budur.",
             "Satın alınan nesne kaybolmamalı; ama bu, lansman yükünden sonra gelir, çünkü kayıp riski tek bir AZ arızasıyla sınırlıdır.",
             "İki geliştirici, operasyon ekibi yok.",
             "Trafik on kat düşünce maliyet de düşmeli."),
    cands=["ddb", "doc", "aur"],
    scores={
        "ddb": [sc(10, "Partition key oyuncu, sort key WEAPON#…, POTION#… (Ö3): bütün envanter tek Query, silahlar begins_with(sk, \"WEAPON#\") ile tek Query. Puan kırılmadı."),
                sc(10, "Her nesne kendi alanlarını taşır (Ö4); kılıç ve iksir aynı table'da yan yana durur. Puan kırılmadı."),
                sc(10, "Sadece key alanları tanımlanır; yeni tür yeni alanlarla yazılır, migration yoktur (Ö4). Puan kırılmadı."),
                sc(9, "TransactWriteItems nesneyi ekler ve altını bir koşulla (gold >= price) düşer; dayanıklılık ADD -3 ve koşulla (durability >= 3) azalır (Ö5). 1 puan kırıldı: transaction en fazla 100 value kapsar ve aynı value üzerinde yarışan transaction'lar reddedilir; uygulama yeniden denemelidir."),
                sc(8, "Trafik oyuncu id'sinin hash'iyle partition'lara dağılır (Ö2), on-demand mod düşüşü takip eder ve global tables oyuncuya yakın bölgede okuma ve yazma verir. 2 puan kırıldı: yeni bir table 200.000 istek/saniyeyi anında karşılamaz; lansmandan önce warm throughput ile ön ısıtma (pre-warming) yapılmalıdır."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(10, "Serverless. Puan kırılmadı."),
                sc(9, "On-demand modda trafik on kat düşünce fatura da düşer. 1 puan kırıldı: satın alma transaction'ları normal yazmanın iki katı birim tüketir.")],
        "doc": [sc(10, "Envanter bir collection'dır; {player, type} index'i ile iki soru da tek sorgudur. Puan kırılmadı."),
                sc(10, "Her nesne kendi alanlarıyla bir document'tır. Puan kırılmadı."),
                sc(10, "Şema serbesttir. Puan kırılmadı."),
                sc(10, "Çok document'lı ACID transaction ve $inc ile koşullu update; altın ve nesne birlikte yazılır. Puan kırılmadı."),
                sc(5, "Okumalar replica'lara dağılır. 5 puan kırıldı: bütün yazmalar tek primary'den geçer ve global cluster'da da yazmalar tek bölgededir; lansman günü için en büyük instance sınıfı ya da elastic cluster (sharding) gerekir ve bu ekip için bir tasarım projesidir."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(5, "Yedek ve yama yönetilir. 5 puan kırıldı: lansman için büyütme, bir ay sonra küçültme ve replica yönetimi operasyon ekibi olmayan bir stüdyonun işidir."),
                sc(5, "Instance saat başına ödenir. 5 puan kırıldı: trafik düşünce instance'ları küçültmek elle yapılır; yapılmazsa lansman boyutu ödenmeye devam eder.")],
        "aur": [sc(10, "WHERE player_id = ? AND type = 'weapon' bir B-tree index'iyle okunur. Puan kırılmadı."),
                sc(6, "Türe özel alanlar bir JSONB kolonunda tutulur. 4 puan kırıldı: JSONB içindeki alanların tipi denetlenmez ve sabit kolonlarla iki ayrı model oluşur."),
                sc(7, "JSONB içine yeni alan migration istemez. 3 puan kırıldı: sorgulanacak her yeni alan için bir index ya da kolon değişikliği gerekir."),
                sc(10, "ACID transaction ve CHECK (durability >= 0); satın alma tek transaction'dır. Puan kırılmadı."),
                sc(4, "Serverless v2 ACU'yu artırır. 6 puan kırıldı: 200.000 istek/saniyenin yazma kısmı tek writer'dan geçer; bu yük bir sharding tasarımı ister (Aurora sayfasının tek writer tablosu: saniyede 20.000'in üstü 6 puan)."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(5, "Yönetilen servis. 5 puan kırıldı: lansman kapasitesi, connection pool ve sharding operasyon ekibi olmayan bir stüdyonun işidir."),
                sc(5, "ACU-saat ile ödenir. 5 puan kırıldı: lansman için yüksek minimum ACU ayarı unutulursa sonraki aylarda da ödenir.")],
    },
    h2h={
        "doc": "Document (DocumentDB) ile kafa kafaya. Engine uyumunda DocumentDB tam puan alır ve DynamoDB'den bir buçuk puan öndedir: envanter doğal bir document koleksiyonudur ve satın alma çok document'lı bir ACID transaction'dır. "
               "Fark R2'de, bu kartın en ağır ikinci gereksiniminde açılır. Lansman günü 200.000 istek/saniye DocumentDB'de tek primary'nin sınırını aşar; elastic cluster ile sharding gerekir ve bu, iki geliştiricili bir stüdyo için lansmandan önce bir tasarım projesidir. "
               "Bir ay sonra on kat düşüşte instance'ları küçültmek de elle yapılır. DynamoDB'de aynı sıçrama bir ön ısıtma ayarıdır ve düşüşte fatura kendiliğinden iner. "
               "Hangi koşul değişseydi DocumentDB seçilirdi: oyun küçük ve düz bir trafikle başlasaydı ya da envanter üzerinde esnek sorgular (\"bu sezon en çok satılan nesneler\") oyunun ana işi olsaydı.",
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Aurora satın alma kuralında en güçlü adaylardan biridir: CHECK kısıtı ve ACID transaction dayanıklılığın eksiye inmesini ve altının kaybolmasını engeller. "
               "Ama R1'in şema satırlarında geride kalır: her nesne türünün farklı alanları ya JSONB içinde tipsiz durur ya da her güncellemede bir kolon değişikliği ister. "
               "R2'de ise lansman günü yükü tek writer'ın erişimini aşar ve bir sharding tasarımı ister. Bu iki fark, kural satırındaki eşitliği önemsiz kılar. "
               "Hangi koşul değişseydi Aurora seçilirdi: oyunun ekonomisi (pazar yeri, oyuncular arası ticaret, vergiler) birçok tablo arasında kurallar isteseydi ve oyuncu sayısı tek bir writer'ın rahat erişiminde kalsaydı.",
    },
    verdict="Karar: DynamoDB {ddb}, DocumentDB {doc}, Aurora {aur}. Bu iş yüküne en uygun servis DynamoDB'dir. Engine uyumunda DocumentDB ile neredeyse eşittir; kararı lansman günü sıçraması (R2) ve operasyon ekibi olmaması verir. "
            "DynamoDB seçtiğimizde artımız: lansman gecesi kimse cluster büyütmez, fatura trafikle birlikte düşer, yeni nesne türü migration istemez. "
            "Eksimiz: lansmandan önce warm throughput ile ön ısıtma yapılmalıdır, satın alma transaction'ları iki kat birim tüketir. Bir koşul değişseydi: trafik küçük ve düz olsaydı DocumentDB kazanırdı."))

# ------------------------------------------------------------------ 5. last state of each device (IoT)
DDB_W.append(wusecase("iot", 5, sim="w_iot",
    title="Her cihazın son durumu (IoT)",
    key="Key: cihaz id'si. Value: son değer, pil, durum, zaman.",
    story=story("iot"),
    wnote="R1 toplam 45: üzerine yazma biçimi ve alarm için değişiklik akışı bu iş yükünün tanımıdır. R2 25'tir, çünkü saniyede 65.000 sürekli yazma büyük bir yüktür. "
          "R3–R5 10'ar: son durum 30 saniyede bir yeniden gelir, ama ekip ve yazma başına fiyat yine de önemlidir.",
    rows=[
        row("EY", 10, "Panelde arada bir sorulan basit bir soru; iş yükünü yazma biçimi ayırır.",
            "Sorular: \"bu cihazın son durumu\" ve \"bu cihazın son durumunu bu mesajla değiştir\". Cihaz id'si her mesajda ve her tıklamada bilinir. Geçmiş sorulmaz.",
            "Panel bir cihaza tıklandığında key ile doğrudan gidemezse operatör bekler."),
        row("OY", 20, "Bu iş yükünün biçimi \"her mesaj öncekinin üzerine yazar\"dır; engine bunu okumadan yapmalı.",
            "Her mesaj cihazın kaydını okumadan değiştirmeli (upsert). Eski değerler burada tutulmaz.",
            "Her yazmadan önce okumak isteği ikiye katlar; ekleme biçiminde yazan bir engine'de \"son durum\" her seferinde aranmak zorunda kalır ve veri sürekli büyür."),
        row("YD", 15, "Alarm, yazan koddan ayrı olmalı; bu engine'in değişikliği dışarı vermesine bağlıdır.",
            "Sıcaklık 80 dereceyi geçen ya da pili yüzde 5'in altına düşen cihaz için bir alarm açılmalı ve alarm mantığı yazan koddan ayrı olmalı.",
            "Alarm yazma koduna gömülürse her yeni kural yazma yolunu değiştirir; ayrı bir tarayıcı iş ise alarmı geciktirir."),
    ] + rest("iot", 25, 10, 10, 10,
             "Saniyede 65.000 yazma, düz ve sürekli; Lambda kuyruğu büyümemeli.",
             "Kaybolan son durum 30 saniye sonra yeniden gelir.",
             "Ekip IoT, Lambda ve SDK kullanıyor; sunucu ve CQL istemiyor.",
             "Yazma başına fiyat belirleyicidir; trafik düz olduğu için kapasite önceden alınabilir."),
    cands=["ddb", "ks", "ix"],
    scores={
        "ddb": [sc(10, "Simple primary key = cihaz id'si; GetItem tek okumadır (Ö1). Puan kırılmadı."),
                sc(10, "PutItem value'yu okumadan değiştirir: aynı key ile yazmak bir upsert'tür (Ö1). Puan kırılmadı."),
                sc(10, "Streams her değişikliği key başına sırayla verir (Ö8); alarm yazan koddan ayrı bir tüketicide çalışır. Puan kırılmadı."),
                sc(10, "Cihaz id'lerinin hash'i yazmaları partition'lara eşit dağıtır (Ö2). Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(10, "Serverless; IoT kuralı table'a yazar ve Streams bir Lambda'yı filtre kriteriyle (sıcaklık > 80 ya da pil < 5) doğrudan çağırır. Puan kırılmadı."),
                sc(9, "Düz trafikte provisioned kapasite ve reserved capacity en ucuz seçenektir. 1 puan kırıldı: 1 KB'tan büyük mesajlar iki yazma birimi tüketir; mesaj boyutu izlenmelidir.")],
        "ks": [sc(10, "Partition key cihaz id'si; SELECT … WHERE device_id = ? tek okumadır. Puan kırılmadı."),
               sc(10, "Cassandra'da INSERT her zaman bir upsert'tür ve okumadan yazar. Puan kırılmadı."),
               sc(10, "Keyspaces CDC satır düzeyindeki değişiklikleri zaman sıralı bir stream olarak 24 saat tutar. Puan kırılmadı."),
               sc(10, "Serverless; yazmalar partition'lara dağılır. Puan kırılmadı."),
               sc(10, "Veri üç AZ'de üç kopyadır. Puan kırılmadı."),
               sc(5, "Serverless. 5 puan kırıldı: ekip CQL istemiyor ve CDC stream'i Keyspaces Streams API ya da KCL ile okunur; Lambda'yı doğrudan tetikleyen bir bağlantı olmadığı için tüketici uygulamayı ekip işletir."),
               sc(9, "Provisioned kapasite düz trafikte ucuzdur. 1 puan kırıldı: 1 KB'tan büyük satırlar fazla birim tüketir.")],
        "ix": [sc(8, "Son durum, cihaz tag'ine göre last() ile sorgulanır. 2 puan kırıldı: bu bir key okuması değil, cihazın serisi üzerinde bir sorgudur."),
               sc(4, "InfluxDB her mesajı yeni bir zaman noktası olarak ekler; \"son durum\" en yeni noktadır. 6 puan kırıldı: üzerine yazma yoktur, seri sürekli büyür ve bir retention politikası gerekir."),
               sc(5, "Alarm bir InfluxDB task'ı ya da check'i ile zamanlanmış sorgularla yapılır. 5 puan kırıldı: değişiklik akışı yoktur; alarm sorgu aralığı kadar gecikir."),
               sc(5, "Güçlü bir instance saniyede 65.000 noktayı alabilir. 5 puan kırıldı: kapasite instance sınıfıyla sınırlıdır ve ekip boyutlandırır."),
               sc(7, "Multi-AZ seçeneği bir standby tutar. 3 puan kırıldı: standby'a geçişte kısa bir kesinti olur."),
               sc(5, "Yönetilen instance. 5 puan kırıldı: instance ve storage boyutlandırma ekibin işidir ve Flux/InfluxQL yeni bir dildir."),
               sc(5, "Instance saat başına ve storage başına ödenir. 5 puan kırıldı: sürekli büyüyen seri için storage ödenir; burada yalnız son değer gerekir.")],
    },
    h2h={
        "ks": "Wide-column (Keyspaces) ile kafa kafaya. Engine olarak Cassandra bu iş yüküne çok uyar: INSERT her zaman bir upsert'tür, yazma yolu (LSM ağacı) sürekli ve yoğun yazma için tasarlanmıştır ve partition key cihaz id'sidir. "
              "Engine uyumunda Keyspaces DynamoDB ile eşittir: ikisi de upsert yapar, ikisi de değişiklikleri bir stream olarak verir. Fark servis tasarımındadır: Keyspaces CDC stream'i Lambda'yı doğrudan tetiklemez; "
              "alarm için Streams API ya da KCL ile bir tüketici uygulama yazılmalı ve işletilmelidir. DynamoDB'de aynı iş, filtre kriterli bir Lambda bağlantısıdır. "
              "Ekip ayrıca CQL istemiyor. Bu iki fark R4'te toplanır. "
              "Hangi koşul değişseydi Keyspaces seçilirdi: ekip zaten Cassandra ve CQL kullanıyor olsaydı, sayaçların verisi Cassandra'dan taşınıyor olsaydı ya da alarm bir akış yerine toplu bir işle yapılabilseydi.",
        "ix": "Time series (Timestream for InfluxDB) ile kafa kafaya. InfluxDB bu iş yükünün komşusudur, kendisi değil: geçmiş değerler zaten ayrı bir time series sisteme gider ve InfluxDB orası için doğru adaydır. "
              "\"Son durum\" ise engine'in doğasına ters düşer: InfluxDB her mesajı yeni bir nokta olarak ekler, üzerine yazmaz; son değer her seferinde bir sorgudur ve seri sürekli büyür. "
              "Değişiklik akışı olmadığı için alarm, zamanlanmış bir sorguyla ve gecikmeyle çalışır. Instance tabanlı işletim de R2, R4 ve R5'te puan kaybettirir. "
              "Hangi koşul değişseydi InfluxDB seçilirdi: panel son değerle birlikte son bir saatin eğrisini de gösterseydi ve iki iş tek bir sistemde birleştirilmek istenseydi.",
    },
    verdict="Karar: DynamoDB {ddb}, Keyspaces {ks}, InfluxDB {ix}. Bu iş yüküne en uygun servis DynamoDB'dir, ama fark 5 puandır: engine uyumunda Keyspaces ile eşittir, çünkü üzerine yazma, key ile okuma ve değişiklik akışı iki engine'de de vardır. Kararı servis tasarımı verir: filtreli Lambda bağlantısı ve ekibin bildiği API. "
            "DynamoDB seçtiğimizde artımız: IoT kuralı, table ve filtreli Lambda; sunucu yok, alarm yazan koddan ayrı. "
            "Eksimiz: mesajlar 1 KB altında tutulmalı, düz trafik için provisioned kapasite ve reserved capacity planlanmalıdır. Bir koşul değişseydi: ekip Cassandra kullanıyor olsaydı Keyspaces kazanırdı."))

# ------------------------------------------------------------------ 6. idempotency keys
DDB_W.append(wusecase("idem", 6,
    title="Ödemeler ve API'lar için idempotency key'leri",
    key="Key: request id. Value: ilk sonucun özeti, süre sonu.",
    story=story("idem"),
    wnote="R1 toplam 50, ve içinde en ağır satır atomikliktir (25): bu kartın bütün amacı aynı isteği iki kez işlememektir. "
          "R3 bu kartta 25'tir ve R2'den ağırdır, çünkü kaybolan bir işaret çift çekilen bir kart demektir. R2 10'dadır: hacim düşüktür.",
    rows=[
        row("TA", 25, "Bu kartın tanımı: aynı id ile iki istek aynı milisaniyede gelse bile yalnız biri \"yeni\" almalı.",
            "\"Bu request id daha önce işlendi mi; işlenmediyse şimdi işaretle\" tek adımda ve atomik olmalı.",
            "Kontrol ve işaretleme iki adımsa iki istek arasına bir yarış girer ve kart iki kez çekilir."),
        row("OY", 10, "Tekrar gelen isteğe ilk sonucu döndürmek ikinci bir okuma olmamalı.",
            "İşaret zaten varsa, ilk isteğin sonucu aynı işlemde geri dönmeli.",
            "İşaret ve sonuç ayrı okunursa her tekrar iki istek yapar ve arada sonuç henüz yazılmamış olabilir."),
        row("YD", 10, "İşaretler 24 saat sonra gereksizdir.",
            "İşaretler 24 saat sonra kendiliğinden silinmeli.",
            "Silinmeyen işaretler her gün 20 milyon kayıt büyür; bir temizlik işi ise ödeme ekibine bir bakım yüküdür."),
        row("EY", 5, "Soru basittir ve her istekte aynıdır; bu kartın riski soruda değil, kuraldadır.",
            "Tek soru: \"bu request id\". İstek id'yi taşır.",
            "Key ile doğrudan gidilemezse ödeme akışının ilk adımı yavaşlar."),
    ] + rest("idem", 10, 25, 8, 7,
             "Saniyede 230 istek, tepe 3.000: hacim düşüktür.",
             "Kaybolan işaret çift çekilen bir kart demektir; bu kartta dayanıklılık atomiklik kadar önemlidir.",
             "Ödeme ekibi sunucu istemiyor, çoklu AZ şart.",
             "Düşük hacim; önemli olan hatasızlıktır."),
    cands=["ddb", "mdb", "aur"],
    scores={
        "ddb": [sc(9, "PutItem + attribute_not_exists(pk) işareti yalnız yoksa yazar (Ö5); aynı milisaniyedeki ikinci istek ConditionalCheckFailedException alır. 1 puan kırıldı: işaret ve ödeme kaydı iki ayrı database'tedir; işaret yazılıp ödeme yazılamazsa uygulama \"işlemde\" durumunu yönetmelidir (kart 1'deki checkout ile aynı sınır)."),
                sc(10, "ReturnValuesOnConditionCheckFailure = ALL_OLD ile başarısız koşul var olan value'yu, yani ilk sonucu aynı cevapta döndürür; ikinci okuma gerekmez. Puan kırılmadı."),
                sc(9, "TTL alanı işaretleri siler (Ö6). 1 puan kırıldı: silme günler içinde olur; işaretin 24 saatten uzun kalması zararsızdır ama okuma tarafı süreyi bilmelidir."),
                sc(10, "GetItem / PutItem request id ile doğrudan gider (Ö1). Puan kırılmadı."),
                sc(10, "Bu hacim DynamoDB için küçüktür; tepe ayarsız karşılanır. Puan kırılmadı."),
                sc(10, "Yazma onaylanmadan önce birkaç AZ'de saklanır; bir AZ arızası işaret kaybetmez. Puan kırılmadı."),
                sc(10, "Serverless, çoklu AZ varsayılan. Puan kırılmadı."),
                sc(10, "Günde 20 milyon küçük yazma istek başına ödenir ve cluster yoktur. Puan kırılmadı.")],
        "aur": [sc(10, "request_id üzerinde UNIQUE ve INSERT … ON CONFLICT DO NOTHING; ikinci istek satır ekleyemez. İşaret tablosu ödeme database'ine konursa işaret ve ödeme kaydı tek transaction'da yazılır. Puan kırılmadı: bu satırda en güçlü aday Aurora'dır."),
                sc(8, "ON CONFLICT DO NOTHING var olan satırı döndürmez. 2 puan kırıldı: ilk sonucu almak için ikinci bir SELECT gerekir (ya da ON CONFLICT DO UPDATE ile yapay bir güncelleme)."),
                sc(4, "PostgreSQL'de TTL yoktur. 6 puan kırıldı: 24 saatten eski işaretler zamanlanmış bir DELETE işiyle (pg_cron) ya da tarih partition'larını düşürerek silinir."),
                sc(10, "request_id primary key'i bir B-tree aramasıdır. Puan kırılmadı."),
                sc(7, "Ortalama saniyede 230 istek tek writer için küçüktür. 3 puan kırıldı: işaret tablosu ödeme kaydını yazan writer'a eklenir ve tepedeki saniyede 3.000 işaret, ödeme yazmalarıyla aynı anda aynı writer'dan geçer (Aurora sayfasının tek writer tablosu: 5.000'e kadar, paylaşılan writer'da aynı tepede 3 puan; connection pool R4'te sayıldı)."),
                sc(10, "Üç AZ'de altı kopya; commit kalıcıdır. Puan kırılmadı."),
                sc(8, "Ödeme kaydı zaten ilişkisel bir database'tedir; işaret tablosu oraya eklenir ve yeni bir cluster gerekmez. 2 puan kırıldı: ödeme database'inin connection pool'u ve kapasitesi bu ek yükle birlikte izlenmelidir."),
                sc(9, "Var olan database'e eklenen küçük bir tablonun ek maliyeti küçüktür. 1 puan kırıldı: ödeme database'inin storage'ı ve I/O'su biraz büyür.")],
        "mdb": [sc(9, "SET req:{id} … NX EX 86400 tek komuttur; Valkey komutları sırayla çalıştırdığı için iki istekten yalnız biri yazar. 1 puan kırıldı: işaret ve ödeme kaydı iki ayrı database'tedir; DynamoDB'deki gibi \"işlemde\" durumu gerekir."),
                sc(10, "SET … NX GET, key zaten varsa eski değeri, yani ilk sonucu aynı komutta döndürür. Puan kırılmadı."),
                sc(10, "EX 86400 işareti tam 24 saat sonra siler. Puan kırılmadı."),
                sc(10, "Key ile doğrudan okuma. Puan kırılmadı."),
                sc(10, "Bu hacim küçük bir cluster için bile küçüktür. Puan kırılmadı."),
                sc(10, "Her yazma çoklu AZ'li transaction log'una işlendikten sonra onaylanır; kontrol primary'den okunur (replica'lar eventually consistent'tir). Puan kırılmadı."),
                sc(6, "Yama ve failover yönetilir. 4 puan kırıldı: serverless seçenek yoktur; node tipi ve shard sayısı ekibin işidir."),
                sc(5, "Node saat başına ödenir. 5 puan kırıldı: saniyede 230 istek için en küçük çoklu AZ cluster'ı bile sürekli çalışır ve istek başına ödemeden pahalıdır.")],
    },
    h2h={
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Atomiklikte Aurora en güçlü adaydır: UNIQUE kısıtı ve ON CONFLICT aynı id'nin iki kez yazılmasını engeller. Ödeme kaydı zaten ilişkisel bir database'te olduğu için Aurora'nın ciddi bir artısı da vardır: işaret ve ödeme kaydı aynı transaction'da yazılabilir. "
               "Fark R1'in yaşam döngüsü ve okuma satırlarında ve R4–R5'tedir: PostgreSQL'de TTL yoktur, 24 saatlik işaretler için bir temizlik işi gerekir; çakışmada ilk sonucu almak ikinci bir sorgudur; "
               "ödeme database'ine her gün 20 milyon işaret yazmak ve silmek onun yükünü ve VACUUM işini büyütür. "
               "Hangi koşul değişseydi Aurora seçilirdi: işaretin ve ödeme kaydının aynı transaction'da yazılması zorunlu olsaydı, yani \"işaret var ama ödeme kaydı yok\" durumu kabul edilemeseydi. Bu durumda işaret ödeme database'inin bir tablosu olur.",
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. Engine uyumunda MemoryDB DynamoDB'den bir puan öndedir: SET … NX EX tek komutta işaretler, NX GET ilk sonucu döndürür ve süre sonu tam anındadır. "
               "Dayanıklılıkta da güçlüdür: her yazma çoklu AZ'li bir log'a işlenir. Bu, aynı engine'i çalıştıran ElastiCache'in bu kartta neden aday olmadığını da açıklar. "
               "Fark yalnız servis tasarımındadır: MemoryDB'de serverless seçenek yoktur ve saniyede 230 isteklik bir iş yükü için çoklu AZ'li bir cluster sürekli çalışır ve ödenir. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: hacim yüz kat büyük olsaydı ve kontrol milisaniyenin altında yapılmak zorunda olsaydı, ya da ekip zaten başka işler için bir MemoryDB cluster'ı işletiyor olsaydı.",
    },
    verdict="Karar: DynamoDB {ddb}, MemoryDB {mdb}, Aurora {aur}. Bu iş yüküne en uygun servis DynamoDB'dir. Engine uyumunda MemoryDB ve DynamoDB neredeyse eşittir; DynamoDB'yi öne geçiren düşük hacimde istek başına ödeme ve serverless işletimdir. "
            "DynamoDB seçtiğimizde artımız: tek koşullu yazma, aynı cevapta ilk sonuç, çoklu AZ dayanıklılık ve kendiliğinden giden işaretler. "
            "Eksimiz: işaret ve ödeme kaydı ayrı database'lerdedir; işaret yazılıp ödeme yazılamazsa uygulama bunu \"işlemde\" durumuyla yönetmelidir. Bir koşul değişseydi: ikisinin aynı transaction'da olması zorunlu olsaydı Aurora kazanırdı."))

# ------------------------------------------------------------------ 7. ticket and seat holds
DDB_W.append(wusecase("seat", 7, sim="w_seat",
    title="Bilet ve koltuk tutmaları",
    key="Key: etkinlik ve bölüm, sonra koltuk. Value: durum, tutan, tutma süresi sonu.",
    story=story("seat"),
    wnote="R1 toplam 50 ve içinde en ağır satır atomikliktir (25): \"iki kişi asla aynı koltuğu tutmamalı\" bu iş yükünün tek kesin kuralıdır. "
          "R2 20'dir: açılış anındaki saniyede 50.000 deneme gerçektir ama birkaç dakika sürer. R3 15'tir, çünkü kaybolan bir tutma aynı koltuğun iki kez satılmasıdır.",
    rows=[
        row("EY", 10, "Salon planı her ziyaretçide bir kez okunur.",
            "Soru: \"bu etkinliğin bütün koltukları ve durumları\" (20.000 koltuk). Ziyaretçi salon planını bu okumayla görür.",
            "Plan yavaş açılırsa ziyaretçiler sayfayı yeniler ve yük katlanır."),
        row("TA", 25, "Bu kartın tanımı: iki kişi aynı anda aynı koltuğu isterse tam olarak biri almalı.",
            "\"Bu koltuğu sadece boşsa ya da tutmanın süresi dolduysa benim için tut\" tek adımda ve atomik olmalı.",
            "Kontrol ve tutma iki adımsa açılış anındaki yarışta aynı koltuk iki kişiye satılır; bu hem para iadesi hem de salonda bir kavga demektir."),
        row("YD", 15, "Tutmalar 10 dakikalıktır; süre dolunca koltuk hemen satışa dönmeli.",
            "Ödeme gelmeyen tutma 10 dakika sonra serbest kalmalı; bir temizlik işi istenmiyor.",
            "Süresi dolan tutma geç serbest kalırsa en çok aranan koltuklar dakikalarca satılamaz görünür."),
    ] + rest("seat", 20, 15, 8, 7,
             "Açılış anında saniyede 50.000 deneme, beş dakika sonra 500; yılda birkaç kez. Salon 20 bölümdür, her bölümde yaklaşık 1.000 koltuk.",
             "Tutma kaybolursa koltuk boş görünür ve ikinci bir kişi tarafından tutulabilir; ilk kişi ödeme ekranındayken koltuğunu kaybeder.",
             "Altı geliştirici, küçük bir operasyon ekibi.",
             "Trafik yılda birkaç kez birkaç dakika; geri kalanında düşük."),
    cands=["ddb", "mdb", "aur"],
    scores={
        "ddb": [sc(8, "Partition key etkinlik ve bölüm (EVT#42#A), sort key koltuk (Ö3): her bölüm tek bir Query'dir. 2 puan kırıldı: 20.000 koltuk 1 MB'lık sayfalara ve birkaç bölüme yayılır; plan birkaç paralel Query ile toplanır."),
                sc(10, "UpdateItem bir koşulla (attribute_not_exists(holder) OR hold_until < :now) koltuğu yalnız boşsa ya da tutmanın süresi dolduysa tutar (Ö5); yarışan ikinci istek reddedilir. Puan kırılmadı."),
                sc(7, "Süre sonu koşulun içindedir: süresi dolan tutma bir sonraki tutma denemesinde kendiliğinden geçersiz olur, temizlik işi gerekmez. 3 puan kırıldı: koltuk value'su kalır; salon planı her koltuğun hold_until'ini şimdiki zamanla karşılaştırarak göstermelidir. TTL burada kullanılmaz, çünkü günler içinde siler."),
                sc(8, "Koltuklar etkinlik ve bölüm key'iyle partition'lara dağılır (Ö2). 2 puan kırıldı: bir partition saniyede en fazla 1.000 yazma birimi alır ve bütün etkinlik tek partition key'de olursa açılışın ilk saniyelerinde sıcak partition oluşur; key bölüme göre bölünmeli ve table önceden ısıtılmalıdır (warm throughput)."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(10, "Serverless. Puan kırılmadı: ön ısıtma R2'de sayıldı."),
                sc(10, "On-demand modda yalnız açılış dakikaları ödenir. Puan kırılmadı.")],
        "mdb": [sc(8, "Salon planı etkinlik başına bir hash'tir (HGETALL). 2 puan kırıldı: tutmalar ayrı key'lerde süre sonuyla durur; planı göstermek iki yapıyı birleştirir."),
                sc(10, "SET hold:{seat} {user} NX EX 600 tek komuttur; Valkey komutları sırayla çalıştırdığı için yalnız bir kişi tutar. Puan kırılmadı."),
                sc(10, "EX 600 tutmayı tam 10 dakikada siler ve koltuk anında serbesttir. Puan kırılmadı."),
                sc(8, "Bellek içi engine 50.000 komutu kolayca taşır. 2 puan kırıldı: her tutma bir yazmadır ve log'a işlenmesini bekler (tek haneli milisaniye); shard sayısı açılıştan önce seçilir."),
                sc(10, "Her yazma çoklu AZ'li transaction log'unda kalıcıdır; tutma kontrolü primary'den yapılır. Puan kırılmadı."),
                sc(6, "Yama ve failover yönetilir. 4 puan kırıldı: serverless seçenek yoktur; cluster açılış için boyutlanır ve yıl boyu çalışır."),
                sc(4, "Node saat başına ödenir. 6 puan kırıldı: yılda birkaç dakikalık tepe için boyutlanan cluster yıl boyu ödenir.")],
        "aur": [sc(10, "SELECT … WHERE event_id = ? 20.000 satırı tek sorguda, index ile okur. Puan kırılmadı."),
                sc(10, "UPDATE seats SET holder = ? WHERE id = ? AND (holder IS NULL OR hold_until < now()) row kilidiyle atomiktir. Puan kırılmadı."),
                sc(7, "Süre sonu aynı biçimde koşulun içindedir; temizlik işi gerekmez. 3 puan kırıldı: salon planı her satırda hold_until'i karşılaştırır."),
                sc(4, "Saniyede 50.000 tutma denemesi tek writer'dan geçer ve en çok aranan koltuklarda row kilitleri sıraya girer. 6 puan kırıldı: açılış yükü bir kuyruk ya da sharding ister (Aurora sayfasının tek writer tablosu: saniyede 20.000'in üstü 6 puan)."),
                sc(10, "Üç AZ'de altı kopya; commit kalıcıdır. Puan kırılmadı."),
                sc(6, "Yönetilen servis. 4 puan kırıldı: açılış için minimum ACU, connection pool ve kilit beklemesi ayarı ekibin işidir."),
                sc(6, "ACU-saat ile ödenir. 4 puan kırıldı: açılıştan önce yüksek minimum ACU ayarlanmalı ve sonra geri alınmalıdır.")],
    },
    h2h={
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. Engine uyumunda MemoryDB DynamoDB'den öndedir: SET … NX EX hem atomik tutmayı hem de tam 10 dakikalık süre sonunu tek komutta verir ve süresi dolan koltuk anında serbesttir. "
               "DynamoDB'de süre sonu koşulun içinde çalışır ve salon planı her koltuğun süresini karşılaştırmak zorundadır. "
               "Fark servis tasarımında kapanır ve tersine döner: yılda birkaç dakikalık tepe için MemoryDB cluster'ı açılış boyutunda kurulur ve yıl boyu ödenir; serverless seçeneği yoktur. "
               "DynamoDB'de aynı açılış bir ön ısıtma ayarıdır ve yalnız kullanılan istekler ödenir. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: satış her gün ve sürekli olsaydı (örneğin bir sinema zinciri) ve cluster zaten başka işler için çalışıyor olsaydı.",
        "aur": "İlişkisel (Aurora) ile kafa kafaya. R1'de Aurora güçlüdür: salon planı tek bir SQL sorgusudur ve row kilidi atomik tutmayı sağlar; süre sonu DynamoDB'deki gibi koşulun içinde çalışır. "
               "Fark açılış anındadır: saniyede 50.000 deneme tek writer'dan geçer ve en çok aranan koltuklarda row kilitleri sıraya girer; bu, bir kuyruk ya da sharding tasarımı ister. "
               "Yıl boyu düşük trafikte ise minimum kapasite ödenir ve açılıştan önce yükseltilen ACU aralığı sonra geri alınmalıdır. Kural tarafında iki aday eşittir; ayrışma tamamen açılış dakikalarının yükündedir. "
               "Hangi koşul değişseydi Aurora seçilirdi: satış açılışı küçük olsaydı (birkaç yüz kişi) ve tutma, ödeme, fatura ve müşteri kayıtlarıyla aynı transaction'da yazılmak zorunda olsaydı.",
    },
    verdict="Karar: DynamoDB {ddb}, MemoryDB {mdb}, Aurora {aur}. Bu iş yüküne en uygun servis DynamoDB'dir. Engine uyumunda MemoryDB öndedir; DynamoDB'yi öne geçiren yılda birkaç dakikalık tepe için kullanım kadar ödemesidir. "
            "DynamoDB seçtiğimizde artımız: tek koşullu yazma iki kişinin aynı koltuğu tutmasını engeller, temizlik işi yoktur, yalnız açılış dakikaları ödenir. "
            "Eksimiz: key bölüme göre bölünmeli, açılıştan önce ön ısıtma yapılmalı ve salon planı süreyi kendisi karşılaştırmalıdır. Bir koşul değişseydi: satış her gün ve sürekli olsaydı MemoryDB kazanırdı."))

# ------------------------------------------------------------------ 8. rate limits and counters
DDB_W.append(wusecase("rate", 8, sim="w_rate",
    title="Rate limit'ler ve sayaçlar",
    key="Key: kullanıcı ve dakika. Value: sayaç.",
    story=story("rate"),
    wnote="R1 toplam 55 ve en büyük: sayacın biçimi (okumadan artır), engine'in veriyi nerede tuttuğu (2 ms sınırı) ve dakika bitince silinmesi bu iş yükünün kendisidir. "
          "R3 5'te, en düşük sınırdadır: kaybolan sayaç bir dakikalığına fazladan 100 istektir. R5 10'dur, çünkü ayda 52 milyar yazmanın fiyatı belirleyicidir.",
    rows=[
        row("OY", 20, "Her API isteği bir artırmadır; engine bunu okumadan ve atomik yapmalı.",
            "\"Bu kullanıcının bu dakikadaki sayacını 1 artır ve yeni değeri döndür\" tek adımda ve atomik olmalı; aynı anda gelen iki istek ikisi de sayılmalı.",
            "Oku-artır-yaz üç adımsa iki istek aynı değeri okur ve biri kaybolur; sınır aşılır."),
        row("DA", 15, "2 ms sınırı engine'in veriyi bellekte mi diskte mi tuttuğuyla belirlenir.",
            "Her artırma 2 ms'nin altında dönmeli, çünkü her API isteğinin önündedir.",
            "Gecikme her API isteğine eklenir; disk tabanlı bir yazmanın tek haneli milisaniyesi bütün API'ı yavaşlatır."),
        row("YD", 15, "Sayaç dakika bitince değersizdir ve dakikada bir milyonlarca yeni sayaç doğar.",
            "Eski dakikaların sayaçları kendiliğinden silinmeli.",
            "Silinmeyen sayaçlar her dakika birikir; bir temizlik işi bu kadar kaydı silemez."),
        row("EY", 5, "Soru basittir: kullanıcı ve dakika ile tek bir sayaç; bu kartın riski artırma biçiminde ve gecikmededir.",
            "Tek soru: \"bu kullanıcının bu dakikadaki sayacı\".",
            "Key ile doğrudan gidilemezse her API isteği yavaşlar."),
    ] + rest("rate", 20, 5, 10, 10,
             "Saniyede 20.000 artırma, düz; gecikme sınırı katıdır.",
             "Kaybolan sayaç bir dakikalığına fazladan 100 istektir; zararsızdır.",
             "Platform ekibi serverless tercih eder.",
             "Her artırma bir yazmadır; ayda 52 milyar yazmanın fiyatı bu iş yükünün maliyetidir."),
    cands=["ec", "mdb", "ddb"],
    scores={
        "ec": [sc(10, "INCR sayacı okumadan, atomik artırır ve yeni değeri döndürür; Valkey komutları sırayla çalıştırır. Puan kırılmadı."),
               sc(10, "Sayaç bellekteki hash table'dadır; INCR mikrosaniyelerde döner. Puan kırılmadı."),
               sc(10, "İlk INCR'den sonra EXPIRE 60 (ya da bir script'te ikisi birlikte) sayacı dakika sonunda tam anında siler. Puan kırılmadı."),
               sc(10, "Key ile doğrudan erişim. Puan kırılmadı."),
               sc(10, "Serverless kendi kendine ölçeklenir; saniyede 20.000 artırma küçük bir yüktür. Puan kırılmadı."),
               sc(4, "Kalıcı bir yazma log'u yoktur. 6 puan kırıldı: bir arızada sayaçlar sıfırlanabilir; bu kartta zararsızdır."),
               sc(10, "Serverless; INCR ve EXPIRE gateway kodunda iki satırdır. Puan kırılmadı."),
               sc(9, "ECPU başına ödenir ve basit bir INCR yaklaşık 1 ECPU'dur. 1 puan kırıldı: sayaçlar az yer tutsa da Serverless için en az 100 MB saklama ödenir.")],
        "mdb": [sc(10, "Aynı Valkey engine'i: INCR okumadan ve atomik. Puan kırılmadı."),
                sc(10, "Aynı Valkey engine'i: sayaç bellekteki hash table'dadır. Puan kırılmadı: yazmanın log'a işlenmesi engine'in değil servisin tasarımıdır ve R2'de sayılır."),
                sc(10, "EXPIRE aynı biçimde tam anındadır. Puan kırılmadı."),
                sc(10, "Key ile doğrudan erişim. Puan kırılmadı."),
                sc(5, "Shard ekleyerek yazma ölçeklenir. 5 puan kırıldı: MemoryDB her yazmayı çoklu AZ log'una işledikten sonra onaylar; INCR bir yazma olduğu için tek haneli milisaniye 2 ms sınırını aşabilir, ve shard sayısını ekip seçer."),
                sc(10, "Her yazma kalıcıdır. Puan kırılmadı: ama bu kartta dayanıklılık önemsizdir."),
                sc(6, "Yönetilen node'lar. 4 puan kırıldı: serverless seçenek yoktur."),
                sc(6, "Node saat başına ve yazılan GB başına ödenir. 4 puan kırıldı: ayda 52 milyar yazma, yazılan veri ücretini büyütür ve bu kartın istemediği dayanıklılığa para verilir.")],
        "ddb": [sc(9, "UpdateItem ADD count :1 ve ReturnValues = UPDATED_NEW sayacı okumadan artırır ve yeni değeri döndürür (Ö5). 1 puan kırıldı: sınır kontrolü bir koşulla (count < 100) eklenirse reddedilen yazma da birim tüketir."),
                sc(4, "Veri SSD'deki partition'lardadır; yazma tek haneli milisaniyedir. 6 puan kırıldı: 2 ms sınırı yazma yolunda karşılanmaz ve DAX yazmaları hızlandırmaz."),
                sc(6, "Key dakikayı içerdiği için eski sayaçlar okunmaz ve TTL onları siler (Ö6). 4 puan kırıldı: silme günler içinde olur ve o arada her dakikanın milyonlarca sayacı storage'da birikir."),
                sc(10, "Key ile doğrudan erişim (Ö1). Puan kırılmadı."),
                sc(10, "Yazmalar kullanıcı ve dakikaya göre partition'lara dağılır (Ö2). Puan kırılmadı: gecikme engine'in depolamasından gelir ve R1.2'de (DA) bir kez sayıldı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı: ama bu kartta dayanıklılık önemsizdir."),
                sc(10, "Serverless. Puan kırılmadı."),
                sc(4, "Trafik düz olduğu için provisioned kapasite on-demand'den ucuzdur. 6 puan kırıldı: saniyede 20.000 yazma birimi us-east-1 liste fiyatıyla yine de ayda yaklaşık 9.500 dolardır; aynı artırmalar ElastiCache'te ECPU olarak ayda birkaç yüz doları geçmez.")],
    },
    h2h={
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. İki aday aynı Valkey engine'ini çalıştırır: INCR ve EXPIRE ikisinde de aynıdır. Engine uyumunda ikisi eşittir. Fark yalnız servis tasarımındadır: "
               "MemoryDB her yazmayı çoklu AZ'li bir log'a işledikten sonra onaylar; INCR bir yazma olduğu için cevap tek haneli milisaniyeye çıkar ve 2 ms sınırı riske girer. "
               "Bu kartta dayanıklılığın ağırlığı en düşük sınırdadır, çünkü kaybolan sayaç zararsızdır; yani MemoryDB'nin bedelini ödediği şey bu iş yükünün istemediği bir güvencedir. "
               "Serverless seçeneğinin olmaması R4'te de puan kaybettirir. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: sayaç bir kota ya da faturalama sayacı olsaydı (örneğin \"ayda 1 milyon ücretsiz istek\") ve kaybı para demek olsaydı.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB bu kartta üçüncüdür ve bu, sayfanın net kaybetme örneğidir. Atomik sayaç DynamoDB'nin de çekirdek özelliğidir (Ö5): ADD ve UPDATED_NEW aynı işi tek istekte yapar. "
               "Ama R1'in iki satırı DynamoDB'nin doğasına ters düşer: veri SSD'dedir ve yazma tek haneli milisaniyedir, oysa sınır 2 ms'dir; TTL günler içinde siler, oysa dakikada milyonlarca yeni sayaç doğar. "
               "R5'te fark en büyüktür: her artırma bir yazma birimidir ve ayda 52 milyar yazma, aynı artırmaların ElastiCache'teki fiyatının çok katıdır. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: sınır dakika değil gün başına olsaydı (günde 10.000 istek), istek hızı yüz kat düşük olsaydı ve sayaç kaybı kabul edilemeseydi.",
    },
    verdict="Karar: ElastiCache {ec}, MemoryDB {mdb}, DynamoDB {ddb}. Bu iş yüküne en uygun servis ElastiCache'tir ve DynamoDB burada net olarak kaybeder: hem engine uyumunda hem maliyette geridedir. "
            "Yine de DynamoDB seçersek artımız: sayaçlar arızadan sağ çıkar ve ekip tek bir database kullanır. "
            "Eksimiz: her API isteğine milisaniyeler eklenir, eski sayaçlar günlerce birikir ve fatura on kat ve üstü büyür. Bir koşul değişseydi: sayaç günlük ve kaybı pahalı olsaydı DynamoDB ya da MemoryDB öne çıkardı."))

# ------------------------------------------------------------------ 9. file metadata
DDB_W.append(wusecase("files", 9,
    title="Dosyaların metadata'sı",
    key="Key: kullanıcı, sonra klasör ve dosya adı. Value: durum, boyut, tag'ler, türe özel alanlar.",
    story=story("files"),
    wnote="R1 toplam 45: klasör klasör sıralı liste, türe göre değişen alanlar, durum geçişinin kuralı ve arama servisine akan değişiklikler bu iş yükünün engine soruları. "
          "R2 20'dir, çünkü 2 milyar kayıt ve mesai tepesi var. R3 15'tir: metadata kaybolursa dosya S3'te durur ama kullanıcı onu bulamaz.",
    rows=[
        row("EY", 15, "Liste her ekranın ilk okumasıdır ve klasör ile ada göre sıralı olmalı.",
            "Sorular: \"bu kullanıcının bütün dosyaları, klasör ve ada göre sıralı\" ve \"bu kullanıcının sadece klasör X'teki dosyaları\". 5.000 dosya bile sayfalı açılabilmeli.",
            "Sıra uygulamada kurulursa her sayfa bütün dosyaları okur; 5.000 dosyalık kullanıcıda liste yavaşlar."),
        row("VM", 10, "Dosya türleri farklı alanlar taşır.",
            "Dosya kayıtlarının alanları türe göre farklıdır: görselde çözünürlük, belgede sayfa sayısı. Kayıt küçüktür (1 KB'tan az).",
            "Bütün türler sabit kolonlara sıkıştırılırsa kolonların çoğu boş kalır ve her yeni tür bir değişiklik ister."),
        row("TA", 10, "Durum geçişi bir kuraldır: yüklenmemiş dosya \"hazır\" olmamalı.",
            "\"Bu dosyanın durumunu yükleniyor'dan hazır'a geçir\" yalnız durum gerçekten yükleniyor ise yapılmalı.",
            "Koşulsuz bir yazma, silinmiş bir dosyayı yeniden \"hazır\" yapabilir."),
        row("YD", 10, "Arama ileride ayrı bir servise verilecek; her değişiklik oraya akmalı.",
            "Metadata'nın her değişikliği bir arama servisine akmalı; yazan kod bunu bilmemeli.",
            "Değişiklikler akmazsa arama eski veriyi gösterir; yazan kod iki yere yazarsa ikisi zamanla ayrışır."),
    ] + rest("files", 20, 15, 10, 10,
             "Saniyede 5.000 okuma ve 500 yazma, mesai tepesi ve 2 milyar kayıt.",
             "Metadata kaybolursa kullanıcı dosyasını bulamaz; bu, kullanıcı için kayıptır.",
             "Ürün ekibi AWS SDK biliyor, sunucu istemiyor.",
             "Düzenli trafik; 2 milyar küçük kayıt."),
    cands=["ddb", "doc", "aur"],
    scores={
        "ddb": [sc(9, "Partition key kullanıcı, sort key \"klasör/dosya adı\" (Ö3): liste tek Query'dir ve sort key sırasıyla gelir; begins_with(sk, \"faturalar/\") yalnız bir klasörü okur; sayfalama LastEvaluatedKey iledir. 1 puan kırıldı: bir klasörü yeniden adlandırmak sort key'i değiştirir; key güncellenemediği için klasördeki her dosya silinip yeni key ile yeniden yazılır."),
                sc(10, "Her value kendi alanlarını taşır (Ö4); görsel ve belge aynı table'dadır. Puan kırılmadı."),
                sc(10, "UpdateItem ve ConditionExpression status = \"uploading\" geçişi yalnız doğru durumdan yapar (Ö5). Puan kırılmadı."),
                sc(10, "Streams her değişikliği key başına sırayla 24 saat verir (Ö8). Puan kırılmadı."),
                sc(10, "Kullanıcıların hash'i yükü partition'lara dağıtır (Ö2); 2 milyar kayıt bir tasarım sorunu değildir. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır; point-in-time recovery açılabilir. Puan kırılmadı."),
                sc(10, "Serverless, ekip bildiği SDK'yı kullanır; OpenSearch Service'e zero-ETL entegrasyonu arama index'ini tüketici yazmadan, yönetilen bir kopya olarak günceller. Puan kırılmadı."),
                sc(8, "Düzenli trafikte provisioned kapasite ucuzdur. 2 puan kırıldı: 2 milyar value'nun storage'ı ve her value'da alan adlarının da saklanması GB maliyetini büyütür.")],
        "doc": [sc(10, "{user, folder, name} bileşik index'i ile liste sıralı ve sayfalı tek sorgudur. Puan kırılmadı."),
                sc(10, "Her dosya kendi alanlarıyla bir document'tır. Puan kırılmadı."),
                sc(10, "updateOne({_id, status: \"uploading\"}, {$set: {status: \"ready\"}}) geçişi yalnız doğru durumdan yapar. Puan kırılmadı."),
                sc(9, "Change stream'ler her değişikliği sırayla verir. 1 puan kırıldı: varsayılan saklama 3 saattir (7 güne kadar ayarlanır)."),
                sc(6, "Okumalar replica'lara dağılır ve 2 milyar document storage sınırının çok altındadır. 4 puan kırıldı: yazmalar tek primary'den geçer; instance sınıfı ve index'in bellekte kalması ekibin boyutlandırma işidir."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(5, "Yönetilen servis. 5 puan kırıldı: instance ve replica yönetimi, arama servisine aktaran change stream tüketicisinin işletilmesi ve ekip için yeni olan MongoDB API'si."),
                sc(7, "Instance saat başına ve I/O başına ödenir. 3 puan kırıldı: gece düşük trafikte de instance'lar çalışır.")],
        "aur": [sc(10, "(user_id, folder, name) üzerinde bir B-tree index'i ile liste sıralı ve sayfalı tek sorgudur. Puan kırılmadı."),
                sc(6, "Türe özel alanlar bir JSONB kolonunda tutulur. 4 puan kırıldı: JSONB içindeki alanların tipi denetlenmez ve iki model (kolonlar ve JSONB) birlikte yönetilir."),
                sc(10, "UPDATE … WHERE id = ? AND status = 'uploading' geçişi yalnız doğru durumdan yapar. Puan kırılmadı."),
                sc(7, "PostgreSQL'in logical decoding'i değişiklikleri WAL'dan sırayla verir. 3 puan kırıldı: bir replication slot'u gerekir ve okunmayan slot WAL'ın birikmesine yol açar."),
                sc(6, "Bu trafik tek writer için küçüktür. 4 puan kırıldı: 2 milyar satırlık bir table'da index boyutu, VACUUM ve partitioning bir tasarım işidir."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(5, "Yönetilen servis. 5 puan kırıldı: arama servisine aktaran tüketici (örneğin DMS ya da bir pipeline), connection pool ve instance ya da ACU ayarı ekibin işidir."),
                sc(7, "Instance ya da ACU saat başına ödenir. 3 puan kırıldı: gece de kapasite ödenir.")],
    },
    h2h={
        "doc": "Document (DocumentDB) ile kafa kafaya. DocumentDB R1'in iki satırında DynamoDB ile eşittir, erişim yolunda (EY) bir puan öndedir: sıralı liste bir bileşik index ile tek sorgudur, her dosya kendi alanlarını taşır ve durum geçişi koşullu bir updateOne'dır. "
               "Değişiklik akışında da yakındır: change stream'ler vardır, yalnız saklama süresi varsayılan olarak kısadır. Asıl fark servis tasarımındadır: arama servisine aktaran tüketiciyi ekip işletir; DynamoDB'de aynı iş OpenSearch'e zero-ETL entegrasyonudur. "
               "R2'de de tek primary ve instance boyutlandırması, sunucu istemeyen bir ürün ekibine iş bırakır. "
               "Hangi koşul değişseydi DocumentDB seçilirdi: kullanıcılar metadata üzerinde esnek sorgular yapsaydı (\"son bir ayda yüklediğim 10 MB'tan büyük PDF'ler\") ve bu sorgular ayrı bir arama servisine gerek kalmadan database'te cevaplanmak istenseydi.",
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Aurora listede ve durum geçişinde DynamoDB kadar iyidir: B-tree index'i sıralı ve sayfalı listeyi, koşullu UPDATE durum kuralını verir. "
               "Geride kaldığı yerler türe göre değişen alanlar (JSONB içinde tipsiz), arama servisine akış (logical replication ve ayrı bir tüketici) ve 2 milyar satırlık bir table'ın bakımıdır. "
               "Bu iş yükünde ilişki ve rapor yoktur; Aurora'nın en güçlü yanı, yani birçok tablo arasında kural ve serbest SQL, burada kullanılmaz. Bedelini ise R2 ve R4'te büyük table bakımıyla öder. "
               "Hangi koşul değişseydi Aurora seçilirdi: dosyalar paylaşım, izinler ve ekipler gibi birçok tabloyla ilişkili olsaydı ve \"bu ekibin erişebildiği bütün dosyalar\" gibi JOIN'li sorular ana iş olsaydı.",
    },
    verdict="Karar: DynamoDB {ddb}, DocumentDB {doc}, Aurora {aur}. Bu iş yüküne en uygun servis DynamoDB'dir: sıralı liste, türe göre alanlar, koşullu geçiş ve arama servisine akış dördü de DynamoDB'nin çekirdek özellikleridir. "
            "DynamoDB seçtiğimizde artımız: 2 milyar kayıt bir tasarım sorunu değildir, arama index'i yönetilen bir kopyadır, sunucu yoktur. "
            "Eksimiz: \"bu tag'e sahip bütün dosyalarım\" gibi yeni bir soru ya bir GSI ya da arama servisi ister; storage maliyeti kayıt sayısıyla büyür. Bir koşul değişseydi: metadata üzerinde esnek sorgular ana iş olsaydı DocumentDB kazanırdı."))

# ------------------------------------------------------------------ 10. recommendation lists
DDB_W.append(wusecase("ads", 10,
    title="Kişisel öneri listeleri",
    key="Key: kullanıcı id'si. Value: 50 ürünlük liste.",
    story=story("ads"),
    wnote="R1 toplam 50: katı 5 ms sınırı engine'in veriyi nerede tuttuğuyla (20) ve gece toplu yazma biçimiyle (15) ilgilidir. "
          "R5 bu kartta 15'tir, çünkü saniyede 100.000 okumanın fiyatı belirleyicidir. R3 5'te, en düşük sınırdadır: liste her gece yeniden hesaplanır.",
    rows=[
        row("EY", 10, "Soru basittir: kullanıcı id'si ile tek bir liste; bu kartın riski hızda ve okuma fiyatındadır.",
            "Tek soru: \"bu kullanıcının listesi\". Listeye göre sorgu yoktur.",
            "Ana sayfa bu okumayı bekler; key ile doğrudan gidilemezse sayfa genel listeye düşer."),
        row("DA", 20, "5 ms sınırı katıdır ve engine'in veriyi bellekte mi diskte mi tuttuğuyla belirlenir.",
            "Okuma 5 ms içinde dönmeli; dönmezse sayfa beklemez ve genel bir liste gösterir.",
            "Sınırı aşan her okuma boşa giden bir öneridir; disk tabanlı bir engine'in tek haneli milisaniyesi yükte 5 ms'yi zaman zaman aşar."),
        row("OY", 15, "Gece 30 dakikada 20 milyon yazma, gündüz sıfır yazma; bu biçim engine'i zorlar.",
            "Gece 30 dakikada 20 milyon listeyi toplu yazmak (saniyede 11.000), gündüz yalnız okumak.",
            "Toplu yazma yavaşsa gece işi sabaha sarkar ve kullanıcılar dünkü listeyi görür."),
        row("VM", 5, "Value basittir: 2 KB'lık tek bir liste; şekli iş yükünü zorlamaz.",
            "Liste tek bir value'dur: 50 ürün id'si, 2 KB.",
            "Liste parçalara bölünürse her okuma birkaç istek olur."),
    ] + rest("ads", 20, 5, 10, 15,
             "Gündüz saniyede 100.000 okuma; gece saniyede 11.000 yazma.",
             "Liste her gece yeniden hesaplanır; kaybı bir günlük genel listedir.",
             "Veri ekibi batch işleri ve SDK biliyor, sunucu istemiyor.",
             "Okuma çok yüksek ve düz; okuma başına fiyat ve 40 GB verinin bellekteki fiyatı belirleyicidir."),
    cands=["ec", "mdb", "ddb"],
    scores={
        "ec": [sc(10, "GET reco:{user} key ile doğrudan okumadır. Puan kırılmadı."),
               sc(10, "Liste bellekteki hash table'dadır; okuma mikrosaniyelerdedir ve 5 ms sınırının çok altındadır. Puan kırılmadı."),
               sc(9, "Pipeline ile toplu SET saniyede 11.000 yazmayı kolayca taşır. 1 puan kırıldı: gece işi her listeye süre (EX) koymalı ya da eski listeleri üzerine yazmalıdır."),
               sc(10, "2 KB'lık liste tek bir string value'dur. Puan kırılmadı."),
               sc(9, "Serverless saniyede 100.000 okumayı taşır. 1 puan kırıldı: gece yazma sıçraması için minimum ECPU ayarı önerilir."),
               sc(9, "Kalıcı bir yazma log'u yoktur, ama listeler bir kopyadır: gece işi onları 30 dakikada yeniden yazar ve kart kaybı ertesi güne kadar kabul eder. 1 puan kırıldı: bir arızadan sonra listeler yeniden yüklenene kadar genel liste gösterilir (yeniden yükleme dakikalar sürerse 1, bir saat ve üstü 2 puan)."),
               sc(9, "Serverless. 1 puan kırıldı: yeniden yükleme işi bir arıza planına yazılmalıdır."),
               sc(6, "ECPU ve GB-saat başına ödenir. 4 puan kırıldı: 40 GB verinin bellekteki saklama fiyatı diskten çok yüksektir ve faturanın büyük kısmıdır.")],
        "ddb": [sc(10, "GetItem kullanıcı id'si ile doğrudan okumadır (Ö1). Puan kırılmadı."),
                sc(6, "Veri SSD'deki partition'lardadır; okuma tipik olarak tek haneli milisaniyedir. 4 puan kırıldı: yük altında okumaların bir kısmı 5 ms'yi aşabilir; sınırı garanti etmek için önüne DAX gerekir."),
                sc(9, "BatchWriteItem 25'er value yazar ve gece işi paralel çalışır. 1 puan kırıldı: S3'ten import yalnız yeni bir table oluşturur; var olan table'a toplu yükleme yazma birimi harcar."),
                sc(10, "Liste bir list alanıdır (Ö4). Puan kırılmadı."),
                sc(8, "Okumalar partition'lara dağılır (Ö2). 2 puan kırıldı: gece ve gündüz için kapasite ayrı ayrı ayarlanmalıdır (zamanlanmış auto scaling ya da on-demand)."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı: ama bu kartta dayanıklılık önemsizdir."),
                sc(10, "Serverless. Puan kırılmadı."),
                sc(5, "Okuma birimi başına ödenir. 5 puan kırıldı: günde milyarlarca okuma, eventually consistent okumayla bile bellek içi cache'in istek fiyatından çok yüksektir; DAX eklenirse onun node'ları da ödenir.")],
        "mdb": [sc(10, "Aynı Valkey engine'i: GET ile doğrudan okuma. Puan kırılmadı."),
                sc(10, "Okumalar bellekten, mikrosaniyelerde. Puan kırılmadı."),
                sc(9, "Aynı Valkey engine'i: toplu SET pipeline ile yapılır. 1 puan kırıldı: gece işi her listeye süre koymalı ya da eski listeleri üzerine yazmalıdır."),
                sc(10, "Tek bir string value. Puan kırılmadı."),
                sc(7, "Replica ekleyerek okuma ölçeklenir. 3 puan kırıldı: her gece yazması log'a işlendikten sonra onaylanır, 20 milyon yazma daha uzun sürer; node ve replica sayısı ekibin işidir."),
                sc(10, "Her yazma kalıcıdır. Puan kırılmadı: ama bu kartta dayanıklılık önemsizdir."),
                sc(6, "Yönetilen node'lar. 4 puan kırıldı: serverless seçenek yoktur."),
                sc(4, "Node saat başına ve yazılan GB başına ödenir. 6 puan kırıldı: 40 GB veri ve replica'lar için büyük node'lar sürekli çalışır; bu kartın istemediği dayanıklılığa para verilir.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. Fark 10 puandır ve kararı R1'in depolama satırı verir. İki aday da key ile tek okuma yapar ve gece toplu yazmayı taşır; DynamoDB dayanıklılıkta öndedir. "
               "Ama 5 ms sınırı katıdır: ElastiCache listeyi bellekte tutar ve mikrosaniyede döner, DynamoDB ise SSD'deki partition'lardan tek haneli milisaniyede döner ve yük altında okumaların bir kısmı sınırı aşar. "
               "Sınırı garanti etmek için DynamoDB'nin önüne DAX konur; bu durumda mimari zaten bir bellek içi cache içerir. "
               "R5'te de günde milyarlarca okumanın istek başına fiyatı, bellekteki 40 GB'ın fiyatına yaklaşır ya da onu aşar. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: sınır 5 ms değil 20 ms olsaydı, okuma hacmi on kat düşük olsaydı ya da listeler kalıcı bir kayıt olsaydı (örneğin kullanıcının kaydettiği listeler).",
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. MemoryDB ElastiCache ile aynı Valkey engine'ini çalıştırır ve okumada aynı mikrosaniyeleri verir. "
               "Fark servis tasarımındadır ve bu kartta MemoryDB'nin aleyhinedir: her gece 20 milyon yazma log'a işlenir ve yazılan GB ayrıca ödenir; serverless seçenek yoktur ve 40 GB için büyük node'lar sürekli çalışır. "
               "Bütün bunlar, her gece yeniden hesaplanan ve kaybı bir günlük genel liste olan veri için ödenen bir dayanıklılıktır. Engine uyumunda ikisi eşittir; farkın tamamı servis tasarımından gelir. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: listeler yeniden hesaplanamasaydı (örneğin elle düzenlenen kampanya listeleri) ve hem mikrosaniye okuma hem kalıcılık aynı anda istenseydi.",
    },
    verdict="Karar: ElastiCache {ec}, MemoryDB {mdb}, DynamoDB {ddb}. Bu iş yüküne en uygun servis ElastiCache'tir; DynamoDB üçüncüdür ve MemoryDB ile neredeyse eşittir. Kararı R1'deki depolama algoritması verir: katı 5 ms sınırı bellekte tutulan veriyle garanti edilir. "
            "Yine de DynamoDB seçersek artımız: listeler kalıcıdır, gece işi tek bir database'e yazar, sunucu yoktur; DAX eklenirse mikrosaniye okuma da mümkündür. "
            "Eksimiz: DAX olmadan bazı okumalar 5 ms'yi aşar ve öneri boşa gider; okuma faturası yüksektir. Bir koşul değişseydi: sınır 20 ms olsaydı DynamoDB kazanırdı."))

USECASES_W = {"dynamodb": DDB_W}


# ====================================================================== Aurora PostgreSQL (page id "aurora"), Turkish, model 2
# The ten workloads of the model 1 Aurora page (e2e_usecases.AURORA_USECASES), rebuilt: R1 in sub-items from R1_CATALOG,
# weights from the story, the best fit first. The model 1 data stays for the untouched English aurora.html.
# Sources of the limits and numbers in the reasons below (the hedges are the hedges of the source):
#  - Aurora storage, six copies in three AZs, 128 TiB, I/O-Optimized "when I/O spend exceeds 25%":
#    https://aws.amazon.com/blogs/database/is-amazon-rds-for-postgresql-or-amazon-aurora-postgresql-a-better-choice-for-me/
#  - Aurora failover "typically restored in less than 60 seconds, and often less than 30 seconds":
#    https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html
#  - Aurora Replicas up to 15, replica lag "usually considerably less than 100 milliseconds":
#    https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.Performance.html
#  - RDS for PostgreSQL: "up to 15 read replicas for a given source DB instance": https://aws.amazon.com/rds/faqs/
#  - RDS Multi-AZ instance failover "typically complete within one to two minutes": https://aws.amazon.com/rds/features/multi-az/
#  - RDS Multi-AZ DB cluster failover "typically less than 35 seconds":
#    https://docs.aws.amazon.com/cli/latest/reference/rds/failover-db-cluster.html
#  - Instance price, eu-central-1, on demand (AWS Price List API, 2026-10-29): db.r6g.large RDS for PostgreSQL 0.274 USD/h,
#    Aurora PostgreSQL Standard 0.313 USD/h, Aurora PostgreSQL I/O-Optimized 0.407 USD/h.
#  - DynamoDB transaction conflicts (TransactionConflictException, TransactionCanceledException), up to 100 actions:
#    https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html
#  - DynamoDB TTL deletes "within a few days": https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html
#  - DocumentDB $jsonSchema validation (4.0 and later), document size 16 MiB:
#    https://docs.aws.amazon.com/documentdb/latest/devguide/json-schema-validation.html,
#    https://docs.aws.amazon.com/documentdb/latest/devguide/limits.html
#  - Redshift columnar storage in 1 MB blocks, compression encodings:
#    https://aws.amazon.com/blogs/big-data/getting-the-most-out-of-your-analytics-stack-with-amazon-redshift/
#  - Redshift Serverless: RPU-hours per second, 60-second minimum, base 4 to 1024 RPUs: https://aws.amazon.com/redshift/pricing/
#  - OpenSearch Ingestion with Aurora PostgreSQL as a source (CDC): https://docs.aws.amazon.com/opensearch-service/latest/developerguide/configure-client-aurora.html
#  - OpenSearch geo_distance, geo_bounding_box, geo_shape:
#    https://aws.amazon.com/blogs/database/building-search-experiences-for-json-data-with-amazon-opensearch-service/
#  - PostgreSQL exclusion constraints, row-level security, VACUUM: https://www.postgresql.org/docs/current/ddl-constraints.html,
#    https://www.postgresql.org/docs/current/ddl-rowsecurity.html, https://www.postgresql.org/docs/current/routine-vacuuming.html
from .e2e_usecases import AURORA_USECASES as _AM1  # noqa: E402

_AOLD = {uc["id"]: uc for uc in _AM1}


def astory(uid):
    return _AOLD[uid]["story"][1]


AURORA_W = []

# ------------------------------------------------------------------ 1. checkout: order, stock, payment
AURORA_W.append(wusecase("checkout", 1, sim="w_checkout",
    title="Sipariş, stok ve ödeme: checkout (Lale Market)",
    key="Table'lar: products, orders, order_items, payments. Kural: stok sıfırın altına inmez, sipariş stoksuz var olmaz.",
    story=astory("checkout").replace("line'larını", "satırlarını").replace("12.500 line", "12.500 sipariş satırı"),
    wnote="R1 toplam 50: checkout'un dört yazması, kuralları ve soruları engine'in garanti modeline dayanır; en ağır alt madde tutarlılık ve atomikliktir (18). "
          "R3 22 ile ikinci: sipariş paranın resmi kaydıdır ve kaybı doğrudan para kaybıdır. Yazma hacmi küçük olduğu için R2 12'de kalır.",
    rows=[
        row("TA", 18, "Kural bozulursa para kaybolur: ödenmiş ama yazılmamış sipariş ya da iki kez satılan son adet.",
            "Stok düşürme, sipariş, sipariş satırları ve ödeme kaydı ya hep ya hiç yazılmalı. Son adedi aynı saniyede isteyen iki checkout'tan tam olarak biri kazanmalı; \"stock - qty >= 0\" yazma anında korunmalı.",
            "Ödeme alınıp sipariş yazılmazsa müşteri parasını öder ve ürün gelmez. Kural \"önce oku, sonra yaz\" ile korunursa iki sekme aynı son adedi satar."),
        row("ŞE", 12, "Mağazaya birden fazla program yazar (checkout, admin paneli, toplu fiyat işi); kural tek yerde olmalı.",
            "Bir sipariş satırı var olmayan bir ürünü, bir sipariş var olmayan bir müşteriyi gösterememeli. Fiyat ve stok type'ı ve sınırı database'de tanımlı olmalı; her program aynı kurala uymalı.",
            "Kural uygulama kodundaysa ikinci bir program ya da elle yazılan bir SQL onu atlar. Sahipsiz bir satır, kimsenin bulamadığı bir ürüne ait bir siparişe dönüşür."),
        row("EY", 12, "Sipariş geçmişi, sipariş detayı ve depo listesi her gün kullanılan ekranlardır.",
            "Üç soru: \"bu müşterinin siparişleri\", \"bu siparişin satırları ürün adlarıyla\", \"stoğu 10'un altındaki ürünler\". Yeni sorular yıl içinde gelecek ve önceden listelenemez.",
            "Her soru ayrı bir key tasarımı ya da uygulamada birleştirme isterse her yeni ekran bir database projesine dönüşür."),
        row("OY", 8, "Yazmanın biçimi basittir: sayaç gibi bir stok düşürme ve birkaç ekleme; ağırlık bu yüzden düşük.",
            "Stok değeri okunmadan, tek cümlede düşürülmeli; sipariş ve satırları ekleme olarak yazılmalı. Aynı ürünün row'u kampanya akşamı saniyede birkaç kez değişir.",
            "Stok önce okunup sonra yazılırsa istek sayısı ikiye katlanır ve yarış penceresi açılır."),
        row("R2", 12, "Saniyede en fazla 10 checkout; burada ölçek değil doğruluk belirleyicidir.",
            _AOLD["checkout"]["reqs"][1]["want"][1], _AOLD["checkout"]["reqs"][1]["why"][1]),
        row("R3", 22, "Sipariş paranın resmi kaydıdır; kaybı ödenmiş ama gönderilmemiş üründür.",
            "Sipariş paranın resmi kaydıdır. Bir Availability Zone arızasında tek bir commit edilmiş sipariş kaybolmamalı; yanlış bir toplu silme bir saat öncesine geri alınabilmeli.",
            _AOLD["checkout"]["reqs"][2]["why"][1]),
        row("R4", 9, "Üç geliştirici, database yöneticisi yok; ama ekip SQL biliyor ve bu kartta R1'den sonra gelir.",
            _AOLD["checkout"]["reqs"][3]["want"][1], _AOLD["checkout"]["reqs"][3]["why"][1]),
        row("R5", 7, "Veri birkaç GB, yük küçük; fatura kararı tek başına çevirmez.",
            _AOLD["checkout"]["reqs"][4]["want"][1], _AOLD["checkout"]["reqs"][4]["why"][1]),
    ],
    cands=["aur", "doc", "ddb"],
    scores={
        "aur": [sc(10, "Dört yazma tek transaction'dır (Ö5): BEGIN, UPDATE products … WHERE stock >= qty, INSERT orders, INSERT order_items, INSERT payments, COMMIT. Koşullu UPDATE row lock altında test eder; son adedi tam olarak bir checkout alır. Puan kırılmadı."),
                sc(10, "CHECK (stock >= 0), NOT NULL ve foreign key'ler (Ö1, Ö2) her programdan gelen her yazmada çalışır; var olmayan ürünü ve negatif stoğu database reddeder. Puan kırılmadı."),
                sc(10, "Üç soru da SQL'dir (Ö3): JOIN ile ürün adları, WHERE stock < 10, müşteri id'si üzerinde index (Ö4). Yeni soru yeni bir SELECT'tir. Puan kırılmadı."),
                sc(9, "UPDATE … SET stock = stock - 2 değeri okumadan düşürür; RETURNING yeni değeri aynı cümlede verir. 1 puan kırıldı: her UPDATE MVCC ile row'un yeni bir sürümünü yazar; sık değişen stok row'larında VACUUM işi artar."),
                sc(10, "Saniyede 10 checkout tek writer için küçük bir yüktür; 300 stok okuması primary key index'inden gelir ve reader'a yönlendirilebilir (Ö7). Puan kırılmadı."),
                sc(10, "Veri üç Availability Zone'da altı kopyadır (Ö7); commit edilmiş sipariş bir AZ arızasında kaybolmaz. Point-in-time restore yanlış bir silmeyi saniye hassasiyetiyle geri alır. Puan kırılmadı."),
                sc(9, "Lale Market'te Aurora zaten çalışır; yedek, yama ve failover yönetilir ve ekip bildiği SQL ile çalışır. 1 puan kırıldı: ACU aralığı, connection pool ve migration disiplini ekibin işidir."),
                sc(8, "Serverless v2 ACU-saniye olarak ödenir ve boş gecede 0,5 ACU'ya iner. 2 puan kırıldı: minimum ACU iki instance için boş gecede de ödenir ve Aurora Standard'da I/O başına ek ücret vardır.")],
        "doc": [sc(8, "Sipariş ve satırları tek bir document'tır ve tek yazmada atomiktir; stok ayrı bir collection'da olduğu için DocumentDB'nin birkaç document'lık transaction'ı (4.0 ve sonrası) kullanılır. 2 puan kırıldı: uygulama transaction'ı açar, yeniden deneme hatalarını kendisi işler ve son adet kuralını koşullu bir update ile yazar."),
                sc(5, "$jsonSchema ile bir collection'a yazılan document'ın alanları ve type'ları denetlenebilir. 5 puan kırıldı: collection'lar arası kural yoktur; siparişin gösterdiği ürünün ya da müşterinin var olduğunu uygulama kontrol eder."),
                sc(7, "Müşteriye göre siparişler bir index ile, düşük stok bir filtre ile tek sorgudur. 3 puan kırıldı: ürün adları başka bir collection'dadır; $lookup ile birleştirmek SQL'deki JOIN'den sınırlı ve zahmetlidir."),
                sc(10, "$inc stoğu okumadan düşürür; sipariş tek document olarak eklenir. Puan kırılmadı: transaction'ın kendisi R1.1'de sayıldı."),
                sc(9, "Saniyede 10 yazma ve 300 okuma bir primary ve replica'larla rahat karşılanır. 1 puan kırıldı: primary instance sınıfı önceden seçilir."),
                sc(10, "Storage üç AZ'de altı kopya tutar; sürekli yedek vardır. Puan kırılmadı."),
                sc(6, "Yedek ve yama yönetilir. 4 puan kırıldı: yanında yeni bir cluster işletilir, MongoDB API'si bu SQL ekibi için yenidir ve instance boyutlandırma ekibin işidir."),
                sc(6, "Instance saat başına ve I/O başına ödenir. 4 puan kırıldı: Multi-AZ için en az iki instance boş gecelerde de çalışır; bu küçük iş yükü için ayrı bir cluster pahalıdır.")],
        "ddb": [sc(8, "TransactWriteItems en fazla 100 yazmayı ya hep ya hiç yapar; stok için \"stock >= :q\" koşulu her item'da korunur. 2 puan kırıldı: aynı ürüne yarışan iki transaction çakışır ve biri TransactionCanceledException ile iptal olur; uygulama yeniden dener."),
                sc(3, "Value'nun içini database denetlemez. 7 puan kırıldı: foreign key ve CHECK yoktur; var olmayan ürünü gösteren bir satırı ya da negatif fiyatı her programın kodu kendisi engeller."),
                sc(4, "\"Bu müşterinin siparişleri\" bir key tasarımıyla tek Query olur. 6 puan kırıldı: \"satırlar ürün adlarıyla\" için JOIN yoktur, \"stoğu 10'un altındaki ürünler\" ikinci bir index ya da bütün table'ın okunmasını ister; her yeni soru yeni bir tasarımdır."),
                sc(9, "UpdateItem ADD ve bir koşul stoğu okumadan düşürür. 1 puan kırıldı: bir siparişin satırlarını toplu değiştirmek yoktur; her satır ayrı yazılır."),
                sc(10, "On-demand mod saniyede 10 transaction'ı ve 300 okumayı tek haneli milisaniyede karşılar. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır; point-in-time recovery vardır. Puan kırılmadı."),
                sc(6, "Serverless: yama, yedek, failover yoktur. 4 puan kırıldı: ekip SQL biliyor; access pattern'leri önceden listeleyip key tasarlamayı öğrenir ve siparişler mağazanın geri kalanından ayrı bir database'e düşer."),
                sc(9, "İstek başına ödeme; boş gecede sıfıra yakın. 1 puan kırıldı: transaction'lı yazma normal yazmanın iki katı birim tüketir.")],
    },
    h2h={
        "doc": "Document (DocumentDB) ile kafa kafaya. Fark R1'in şema satırında ve R4'tedir. DocumentDB'nin gücü siparişin şeklindedir: sipariş, satırları ve teslimat adresiyle tek bir document'tır, tek okumayla gelir ve tek yazmada atomiktir; birkaç document'lık transaction da vardır. "
               "Ama checkout'un kuralları dört şeyin arasındadır: stok, sipariş, satır ve ödeme. Aurora bu kuralları foreign key, CHECK ve koşullu UPDATE ile database'in içinde, her programa uygular; DocumentDB'de $jsonSchema bir collection'ın içini denetler, collection'lar arası kuralı ise uygulama yazar. "
               "Servis tasarımında da fark vardır: Aurora Lale Market'te zaten çalışır, DocumentDB yeni bir cluster ve ekip için yeni bir API demektir. "
               "Hangi koşul değişseydi DocumentDB seçilirdi: sipariş ilişkisiz, sık şekil değiştiren bir belge olsaydı, stok kuralı başka bir sistemde korunsaydı ve ekip MongoDB API'sini zaten işletiyor olsaydı.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. Fark R1'in şema ve erişim yolu satırlarındadır; R2, R3 ve R5'te DynamoDB eşit ya da biraz öndedir. TransactWriteItems dört yazmayı ya hep ya hiç yapabilir ve koşul stoğu korur; kampanya akşamı için hiçbir şey ayarlanmaz. "
               "Ama foreign key ve CHECK yoktur: var olmayan ürünü gösteren bir satırı database reddetmez. \"Siparişin satırları ürün adlarıyla\" ve \"stoğu azalan ürünler\" soruları JOIN ve serbest filtre ister; DynamoDB'de bunlar ikinci index'ler ya da uygulamada birleştirmedir. "
               "Bu iş yükünde yazma hacmi saniyede 10'dur; DynamoDB'nin partition'lara dağılan ölçeği kullanılmayacak bir güçtür. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: checkout hacmi saniyede binlere çıksaydı, sipariş ilişkisiz tek bir value olarak yazılsaydı ve raporlar ayrı bir analitik kopyadan sorulsaydı.",
    },
    verdict="Karar: Aurora {aur}, DocumentDB {doc}, DynamoDB {ddb}. Kararı R1 verir: dört table arası kural, ya hep ya hiç yazma ve önceden bilinmeyen sorular ilişkisel engine'in tanımıdır; R3'te üç aday da güçlüdür. "
            "Aurora PostgreSQL seçtiğimizde artımız: kurallar database'de yaşar ve her programa uygulanır, checkout tek transaction'dır, her yeni rapor sorusu bir SQL cümlesidir, sipariş altı kopyayla kalıcıdır. "
            "Eksimiz: bütün yazmalar tek writer'dan geçer; boş gecelerde minimum ACU ödenir; schema değişiklikleri migration disiplini ister; ödeme dış bir servisse transaction ödeme çağrısı boyunca açık tutulmamalı, ödeme önce yetkilendirilmelidir (B5); çok ürünlü sepetlerde deadlock olmaması için satırlar product_id sırasıyla düşürülür ve 40P01 hatası alan transaction yeniden denenir. "
            "Aynı engine'i çalıştıran RDS for PostgreSQL bu kartta aday değildir, çünkü R1'i Aurora ile aynıdır ve fark yalnız R2–R5'tedir: Lale Market'te Aurora zaten çalışır ve checkout'u RDS'e taşımak yeni bir cluster işletmek demektir; sıfırdan başlayan düz yüklü küçük bir mağazada RDS kart 5'teki gibi fiyatla yakın bir yarışa girer. "
            "Bir koşul değişseydi: checkout hacmi saniyede binlerce transaction'a çıksaydı ve sipariş ilişkisiz tek bir value olsaydı DynamoDB yarışa girerdi; bu eşik bir büyüklük sırasıdır, A8'deki gibi kendi yükünle ölçülür."))

# ------------------------------------------------------------------ 2. product catalog with relations (DocumentDB wins R1)
AURORA_W.append(wusecase("catalog", 2, sim="w_catalog",
    title="İlişkileriyle ürün kataloğu: kategori, marka, varyant",
    key="Table'lar: products, categories, brands, variants, prices. Değişken özellikler JSONB column'unda.",
    story=astory("catalog").replace("Dört geliştirici, SQL biliyor;", "Siparişler ve stok zaten bu şirketin bir Aurora cluster'ında; dört geliştirici SQL biliyor, MongoDB API'sini bilmiyor;"),
    wnote="R1 toplam 50: ürünün şekli (VM 14) ve aylık yeni özellikler (ŞE 12) bu katalogun günlük işidir, filtre ve ilişki soruları (EY 14) vitrinin kendisidir. "
          "R4 15 ve R2 15 ile ikinci sıradadır: ekip SQL biliyor ve siparişler zaten bir Aurora cluster'ında çalışıyor; vitrin saniyede 2.000 okuma alıyor.",
    rows=[
        row("VM", 14, "Her kategorinin özellikleri farklıdır; ürün sayfası bir ürünü varyantlarıyla birlikte gösterir.",
            "Bir ürün, 6 ile 40 arasında varyantıyla (numara, renk, ekran boyu) ve kategoriye göre değişen özellikleriyle tek bir bütün olarak okunmalı ve yazılmalı.",
            "Ürün ve varyantları ayrı yerlerde dağınık durursa her ürün sayfası birkaç okuma ve birleştirme ister; satıcı bir ürünü güncellerken yarım bir hâl görünebilir."),
        row("ŞE", 12, "Kategori ekibi her ay yeni özellik tanımlıyor; bu iş database ekibini beklememeli.",
            "\"Su geçirmez\" ya da \"ekran yenileme hızı\" gibi yeni bir özellik sadece yeni ürünlere yazılabilmeli; eski ürünler değişmeden kalmalı ve bir bakım penceresi gerekmemeli.",
            "Her yeni özellik bir schema değişikliği ise kategori ekibinin takvimi database ekibinin takvimine bağlanır."),
        row("EY", 14, "Vitrin bu filtrelerle çalışır; yanlış ya da yavaş bir filtre satış kaybıdır.",
            "\"Bu kategoride, bu markanın, 42 numara ve kırmızı varyantları\", \"fiyatı bugün değişen ürünler\", \"stoğu biten varyantların ürünleri\" doğrudan sorulabilmeli; marka ve kategori adları sonuçla birlikte gelmeli.",
            "Bir filtre bütün kataloğu okursa 50.000 ürün ve 300.000 varyantla sayfa yavaşlar; bir ilişki uygulamada kurulursa her ekranda aynı kod tekrarlanır."),
        row("TA", 10, "Sıfır fiyatlı ürün bedava satılır; ama kurallar az ve basittir.",
            "Bir varyant tam olarak bir ürüne aittir, fiyat sıfırdan büyüktür, silinen bir markanın ürünü kalmaz. Bir ürün ve varyantları birlikte değişmeli.",
            "Sahipsiz varyant boş bir kutudur; sıfır fiyat bir kampanya hatasında yüzlerce siparişe dönüşür."),
        row("R2", 15, "Vitrin saniyede 2.000 okuma alır ve katalog yılda iki katına çıkar.",
            _AOLD["catalog"]["reqs"][1]["want"][1], _AOLD["catalog"]["reqs"][1]["why"][1]),
        row("R3", 8, "Katalog satıcı beslemelerinden yeniden kurulabilir; kayıp günler sürer ama para kaybı değildir.",
            _AOLD["catalog"]["reqs"][2]["want"][1], _AOLD["catalog"]["reqs"][2]["why"][1].replace(", zorunluluk değildir", "")),
        row("R4", 15, "Ekip SQL biliyor ve siparişler zaten bir Aurora cluster'ında; ikinci bir database türü yeni bir operasyon işidir.",
            "Dört geliştirici SQL biliyor, MongoDB API'sini bilmiyor. Siparişler ve stok zaten bir Aurora cluster'ında çalışıyor. Sunucu boyutlandırma, yama ve yedek istenmiyor; ikinci bir database türü için ayrı izleme ve nöbet kurulmak istenmiyor.",
            "Yeni bir database türü yeni bir API, yeni bir izleme, yeni bir yedek planı ve yeni bir nöbet demektir; dört kişilik ekipte bu ürün geliştirmeden çalınan zamandır."),
        row("R5", 12, "Katalog orta boydur ve trafik düzdür; ikinci bir cluster'ın sürekli maliyeti hissedilir.",
            _AOLD["catalog"]["reqs"][4]["want"][1], _AOLD["catalog"]["reqs"][4]["why"][1]),
    ],
    cands=["aur", "doc", "os"],
    scores={
        "aur": [sc(7, "Ürün bir row, varyantlar ayrı bir table, değişken özellikler bir JSONB column'u (Ö8). 3 puan kırıldı: ürün sayfası products ve variants'ın bir JOIN'idir ve aynı ürünün bir kısmı column'larda, bir kısmı JSONB'de durur; iki model birlikte yönetilir. Serbest alanların type denetimi iki adayda da ayrı bir kural ister (CHECK ya da $jsonSchema) ve burada puan kırmaz."),
                sc(7, "Yeni özellik JSONB'ye yazılır, migration gerekmez (Ö8). 3 puan kırıldı: sık filtrelenen bir özellik normal bir column'a ya da bir ifade index'ine taşınırsa bu bir schema değişikliğidir."),
                sc(10, "Filtreler, ilişkiler ve adlar tek bir SELECT'tir: JOIN ile marka ve kategori, JSONB üzerinde GIN index ile özellik filtresi (Ö3, Ö4). Puan kırılmadı."),
                sc(10, "Foreign key bir varyantı tam olarak bir ürüne bağlar, CHECK (price > 0) sıfır fiyatı reddeder (Ö1, Ö2), ON DELETE kuralı silinen markanın ürünlerini yönetir; ürün ve varyantları tek transaction'da değişir (Ö5). Puan kırılmadı."),
                sc(10, "2.000 okuma primary key ve index aramalarıdır ve reader instance'lara dağılır (Ö7); 50 yazma tek writer için küçüktür. Puan kırılmadı: reader sayısı ve ACU aralığı seçimi R4'te sayıldı."),
                sc(10, "Üç AZ'de altı kopya, point-in-time restore. Puan kırılmadı."),
                sc(8, "Katalog table'ları var olan Aurora cluster'ına eklenir; ekip SQL'i biliyor ve yeni bir servis işletmez. 2 puan kırıldı: katalog yükü siparişlerle aynı cluster'a biner; reader sayısı, reader yönlendirmesi ve ACU aralığı ekip tarafından seçilir."),
                sc(8, "Var olan cluster'a eklenen table'lar ayrıca bir cluster ücreti doğurmaz. 2 puan kırıldı: vitrin okumaları için bir reader daha ve daha yüksek ACU ödenir.")],
        "doc": [sc(10, "Ürün bir document, varyantlar içinde bir dizi, özellikler iç içe alanlardır; ürün sayfası tek okumadır ve ürün varyantlarıyla tek yazmada değişir. Puan kırılmadı."),
                sc(10, "Yeni özellik sadece yeni document'lara yazılır; eski document'lar değişmez ve schema değişikliği yoktur. Puan kırılmadı."),
                sc(8, "Kategori, marka ve varyant alanları üzerinde index'ler, dizi içindeki alanlar için multikey index ile filtreler tek sorgudur; \"stoğu biten varyantların ürünleri\" dizi içinde bir koşuldur. 2 puan kırıldı: marka ve kategori adları başka collection'larda durur ve $lookup ile birleştirilir."),
                sc(6, "Varyant ürünün içinde olduğu için ona aittir ve birlikte atomik değişir; $jsonSchema \"price > 0\" kuralını yazmada denetleyebilir. 4 puan kırıldı: markanın ve kategorinin var olduğunu uygulama kontrol eder; marka silinince ürünler kendiliğinden değişmez."),
                sc(9, "Okumalar en fazla 15 replica'ya dağılır; 50 yazma tek primary için küçüktür. 1 puan kırıldı: instance sınıfı ve replica sayısı önceden seçilir."),
                sc(10, "Üç AZ'de altı kopya, sürekli yedek. Puan kırılmadı."),
                sc(6, "Yedek ve yama yönetilir. 4 puan kırıldı: yanında yeni bir cluster işletilir ve MongoDB API'si bu SQL ekibi için yenidir."),
                sc(7, "Instance saat başına ve I/O başına ödenir. 3 puan kırıldı: Multi-AZ için en az iki yeni instance sürekli çalışır.")],
        "os": [sc(8, "Ürün varyantlarıyla tek bir JSON document'ı olarak index'lenir; varyantlar nested alan olarak kalır. 2 puan kırıldı: mapping her alanın type'ını sabitler ve iç içe varyantlar nested sorgular ister."),
               sc(8, "Yeni alan dynamic mapping ile index'e eklenir. 2 puan kırıldı: bir alanın type'ı ilk yazmada sabitlenir; yanlış tahmin edilen bir type reindex ister (OpenSearch sayfasının kademesi: yalnız yeni alan gelirse 2, var olan alanların type'ı ya da analizi değişirse 4 puan; bu hikâyede yalnız yeni özellik gelir)."),
               sc(6, "Filtre ve facet bu engine'in ana işidir; \"42 numara, kırmızı, su geçirmez\" milisaniyede döner, metin araması da burada olur. 4 puan kırıldı: ilişkiler index'e yazılırken düzleştirilir ve marka adı değişince o markanın bütün ürün document'ları yeniden yazılır (3); yeni bir yazma aramada bir refresh aralığı (varsayılan 1 saniye) sonra görünür (1)."),
               sc(2, "Bir document'ın yazması kendi içinde atomiktir. 8 puan kırıldı: transaction, foreign key ve CHECK yoktur; varyantın ürüne ait olması ve \"fiyat > 0\" kuralı tamamen uygulamadadır."),
               sc(9, "2.000 okuma ve 50 yazma bir domain için küçüktür. 1 puan kırıldı: kapasite sabittir; büyüme ve tepe için node'lar önceden eklenir. Refresh gecikmesi R1.3'te sayıldı."),
               sc(8, "Replica shard'lar node ve AZ arızasını karşılar, saatlik otomatik snapshot alınır. 2 puan kırıldı: domain kaybolursa katalog satıcı beslemelerinden yeniden yüklenir ve bu bir saatten uzun sürer (OpenSearch sayfasının kuralı: yeniden yükleme dakikalar sürerse 1, bir saat ve üstü sürerse 2 puan)."),
               sc(5, "Yönetilen domain. 5 puan kırıldı: mapping tasarımı ve shard planı ekibin işidir ve ekip yeni bir sorgu dili öğrenir; reindex R1.2'de sayıldı."),
               sc(6, "Node saat başına ödenir. 4 puan kırıldı: üç node'luk bir domain gece de çalışır.")],
    },
    h2h={
        "doc": "Document (DocumentDB) ile kafa kafaya. Bu kartta engine uyumunu DocumentDB kazanır: R1'de 43,2'ye karşı 42,2. Bir ürün sayfası gerçekten bir document gibidir; varyantlar ürünün içinde bir dizi, özellikler kategoriye göre değişen iç içe alanlardır ve yeni özellik hiçbir değişiklik istemez. "
               "Aurora aynı esnekliği JSONB column'uyla verir ama ürün sayfası bir JOIN'dir ve JSONB içindeki type'ları denetlemez; buna karşılık foreign key, CHECK ve JOIN ile marka, kategori ve fiyat kurallarını database'de tutar. "
               "Kararı servis tasarımı ve ekip verir: siparişler zaten bir Aurora cluster'ında, ekip SQL biliyor; DocumentDB yeni bir cluster, yeni bir API ve en az iki yeni instance demektir. Fark 5 puanın altındadır: bu yakın bir yarıştır. "
               "Hangi koşul değişseydi DocumentDB seçilirdi: ekip MongoDB API'sini biliyor ve bir DocumentDB cluster'ı zaten işletiyor olsaydı; o zaman R4 ve R5 eşitlenir ve engine uyumu kararı DocumentDB'ye verir.",
        "os": "Search engine (OpenSearch) ile kafa kafaya. OpenSearch'ün gücü filtre ve facet'tedir: \"42 numara, kırmızı, su geçirmez\" sorusunu milisaniyede cevaplar ve metin aramasını, yazım hatası toleransını da verir. "
              "Ama bir arama index'i resmi kayıt değildir: ilişkiler düzleştirilir, transaction ve foreign key yoktur, bir alanın type'ı değişince index baştan kurulur. R1'in atomiklik satırı ve R4 bu yüzden çok düşüktür. "
              "Bu iki servis birbirinin alternatifi değil tamamlayıcısıdır: katalog ilişkileriyle Aurora'da yaşar, arama kopyası OpenSearch Ingestion ile Aurora'nın değişiklik akışından OpenSearch'e gelir. Metin araması zaten ayrı bir servise verilecek; o servis OpenSearch'tür. "
              "Hangi koşul değişseydi OpenSearch seçilirdi: katalog başka bir sistemde zaten kalıcı olsaydı ve buradaki iş sadece facet'li arama ve relevance olsaydı.",
    },
    verdict="Karar: Aurora {aur}, DocumentDB {doc}, OpenSearch {os}. Yakın bir yarış: engine uyumunu DocumentDB 1 puanla kazanır, toplamı Aurora R4 ve R5 ile alır, çünkü siparişler zaten Aurora'da ve ekip SQL biliyor. "
            "Aurora PostgreSQL seçtiğimizde artımız: varyant ve fiyat kuralları database'de, yeni özellikler JSONB'de migration'sız, her yeni soru bir SQL, katalog ve siparişler aynı cluster'da tek transaction'la bağlanır. "
            "Eksimiz: ürün sayfası bir JOIN'dir; JSONB içi filtreler GIN index ve özel operatörler ister ve type'ları uygulama denetler; metin araması için OpenSearch ayrıca kurulur: ikisi birlikte çalışır. "
            "Var olan bir cluster olmasaydı (sıfırdan başlayan bir proje): Aurora R4'te 7'ye ve R5'te 7'ye iner (yeni bir cluster işletilir), toplam 84,1 olur; DocumentDB 82,1 ile yine 2 puan geridedir, çünkü SQL bilen ekip R4'te kalır. "
            "Bir koşul değişseydi: ekip MongoDB biliyor ve DocumentDB'yi zaten işletiyor olsaydı DocumentDB kazanırdı."))

# ------------------------------------------------------------------ 3. warehouse stock with reservations
AURORA_W.append(wusecase("inventory", 3,
    title="Depo bazlı stok ve rezervasyon",
    key="Table'lar: stock (sku, warehouse, on_hand), reservations (sku, warehouse, qty, expires_at).",
    story=astory("inventory"),
    wnote="R1 toplam 48: rezervasyonun kuralı (TA 16) ve aynı on ürüne yığılan yazmaların biçimi (OY 12) bu iş yükünün kalbidir; süre sonu ve sabah raporu da engine'e sorulan sorulardır. "
          "R3 20 ile en ağır ikinci satır: stok muhasebenin resmi kaydıdır ve kayıp rezervasyon fazla satıştır.",
    rows=[
        row("TA", 16, "Kural bozulursa aynı adet iki kişiye satılır; kampanya anında yarış gerçektir.",
            "\"Bu depoda bu üründen 2 adet rezerve et, ama kullanılabilir stok 2'nin altındaysa reddet\" tek adımda ve atomik olmalı; rezervasyon kaydı ve kullanılabilir stok birlikte değişmeli.",
            "Rezervasyon yazılıp stok düşmezse aynı adet iki kişiye satılır; stok düşüp rezervasyon yazılmazsa adet sonsuza kadar kilitli kalır."),
        row("OY", 12, "Kampanya anındaki 300 denemenin yarısı aynı on ürüne gider; yazmanın biçimi bu yüzden önemlidir.",
            "Aynı row'a saniyede 15 kez yazılır: okumadan düşürme ve iade. Yarışan istekler doğru sırayla uygulanmalı ve hiçbiri kaybolmamalı.",
            "Sıcak bir row'da her yazma bir öncekini bekler ya da reddedilip yeniden denenir; kuyruk uzarsa checkout yavaşlar."),
        row("YD", 10, "Ödemesi gelmeyen rezervasyonların çoğu 15 dakika sonra stoğa dönmelidir.",
            "Süresi dolan rezervasyon kullanılabilir stoğu kendiliğinden geri vermeli; geç dönen bir adet satılamayan bir adettir.",
            "Süre sonu geç uygulanırsa stok varken \"tükendi\" görünür; erken uygulanırsa ödeme sırasındaki müşterinin adedi elinden gider."),
        row("EY", 10, "Depo ekibi raporu her sabah ister; günde bir kez ama işin başlangıcıdır.",
            "\"Depo başına eşiğin altındaki ürünler\" tek bir sorgu olmalı ve ayrı bir kopya istememeli.",
            "Rapor birçok okuma ya da bir dışa aktarma isterse depo ekibi her sabah bekler."),
        row("R2", 15, "Kampanya anında saniyede 300 deneme ve 100 ms sınırı; normalde saniyede 10.",
            _AOLD["inventory"]["reqs"][1]["want"][1], _AOLD["inventory"]["reqs"][1]["why"][1]),
        row("R3", 20, "Stok ve rezervasyon muhasebenin kaydıdır; kayıp fazla satıştır.",
            "Stok ve rezervasyon muhasebenin kaydıdır; bir AZ arızasında commit edilmiş tek bir rezervasyon kaybolmamalı.",
            _AOLD["inventory"]["reqs"][2]["why"][1]),
        row("R4", 9, "Dört geliştirici SQL biliyor; operasyon önemlidir ama kuraldan sonra gelir.",
            "Dört geliştirici, SQL biliyor. Sunucu boyutlandırma ve yama istenmiyor; yeni bir database türü işletmek istenmiyor.",
            "Yeni bir API ve yeni bir servis, dört kişilik ekipte kampanya hazırlığından çalınan zamandır."),
        row("R5", 8, "Trafik çoğunlukla düz, tepeler kısa; fatura kararı tek başına çevirmez.",
            _AOLD["inventory"]["reqs"][4]["want"][1], _AOLD["inventory"]["reqs"][4]["why"][1]),
    ],
    cands=["aur", "ddb", "mdb"],
    scores={
        "aur": [sc(10, "Tek transaction (Ö5): stok row'u SELECT … FOR UPDATE ile kilitlenir, süresi dolmamış rezervasyonların toplamı düşülür, yer varsa rezervasyon eklenir. Yarışan ikinci istek kilidi bekler ve yeni değeri görür. Puan kırılmadı."),
                sc(8, "Yazmalar row lock ile sıraya girer ve hiçbiri kaybolmaz. Birkaç milisaniyelik bir transaction'la saniyede 15 istek, sıcak row'u her saniyenin küçük bir kısmında meşgul eder; 100 ms sınırı bu hızda rahattır, ama kendi yükünle pgbench gibi bir araçla ölçülmelidir. 2 puan kırıldı: sıcak row'da her istek öncekinin commit'ini bekler ve her UPDATE MVCC ile yeni bir row sürümü yazar; on sıcak row VACUUM işini artırır."),
                sc(7, "Süre sonu koşulun içindedir: kullanılabilir stok \"expires_at > now()\" olan rezervasyonlarla hesaplanır; süresi dolan rezervasyon bir sonraki hesapta kendiliğinden sayılmaz. 3 puan kırıldı: PostgreSQL'de TTL yoktur; eski rezervasyon row'ları zamanlanmış bir DELETE işiyle (pg_cron) silinir."),
                sc(10, "GROUP BY warehouse ile eşik raporu tek SQL'dir (Ö3) ve reader'da çalışır. Puan kırılmadı."),
                sc(9, "Saniyede 300 kısa transaction tek writer için küçük bir yüktür. 1 puan kırıldı: Serverless v2 kapasiteyi adım adım artırır ve yüksek kapasitede daha hızlı ölçeklenir; on dakikada gelen kampanya sıçraması için minimum ACU önceden yükseltilir."),
                sc(10, "Üç AZ'de altı kopya; commit kalıcıdır (Ö7). Puan kırılmadı."),
                sc(9, "Ekip SQL biliyor; yedek, yama ve failover yönetilir. 1 puan kırıldı: connection pool ve kilit bekleme süresi (lock_timeout) ekip tarafından ayarlanır."),
                sc(8, "ACU-saat ile ödenir. 2 puan kırıldı: minimum ACU boş saatlerde de ödenir ve Standard yapılandırmada I/O ayrıca ödenir.")],
        "mdb": [sc(8, "Valkey komutları sırayla çalıştırır; bir Lua script'i kullanılabilir stoğu test eder ve rezervasyonu aynı adımda yazar. 2 puan kırıldı: script ortada hata verirse o ana kadarki yazmalar geri alınmaz; script'i uygulama yazar ve test eder."),
                sc(10, "Sayaçlar bellekte, tek thread'de sırayla değişir; sıcak key bir kilit kuyruğu oluşturmaz. Puan kırılmadı."),
                sc(9, "Rezervasyonlar süre sonu skoruyla bir sorted set'te durur; script her denemede süresi dolanları ZREMRANGEBYSCORE ile atar. 1 puan kırıldı: atma işlemi bir sonraki denemede olur; boş bir ürünün adedi o ana kadar listede kalır."),
                sc(3, "Key ile erişim hızlıdır. 7 puan kırıldı: \"depo başına eşiğin altındaki ürünler\" için sorgu dili ve GROUP BY yoktur; bütün key'ler taranır ya da uygulama ikinci bir yapı tutar."),
                sc(9, "Bellek içi engine 300 denemeyi kolayca taşır. 1 puan kırıldı: her yazma çoklu AZ log'una işlendikten sonra onaylanır (tek haneli milisaniye) ve shard sayısını ekip seçer."),
                sc(10, "Her yazma çoklu AZ'li transaction log'unda kalıcıdır. Puan kırılmadı."),
                sc(5, "Yama ve failover yönetilir. 5 puan kırıldı: serverless seçenek yoktur, node tipi ve shard sayısı ekibin işidir ve Valkey komutları bu SQL ekibi için yeni bir API'dir."),
                sc(5, "Node saat başına ödenir. 5 puan kırıldı: küçük bir stok verisi için çoklu AZ'li node'lar ay boyu çalışır.")],
        "ddb": [sc(7, "TransactWriteItems rezervasyonu ekler ve stok item'ını \"available >= :q\" koşuluyla düşürür; ya hep ya hiç. 3 puan kırıldı: aynı on ürüne yarışan transaction'lar çakışır ve TransactionCanceledException ile iptal olur; kampanya anında yeniden denemeler sıktır."),
                sc(10, "UpdateItem ADD ve bir koşul stoğu okumadan düşürür; bir partition saniyede 1.000 yazma birimi alır ve sıcak ürün başına 15 yazma bunun çok altındadır. Puan kırılmadı: transaction'lı yazmanın birim maliyeti R5'te sayıldı."),
                sc(5, "Rezervasyon item'ı bir TTL alanı taşır. 5 puan kırıldı: TTL \"birkaç gün içinde\" siler; 15 dakikada stoğu geri vermek için süresi dolanları bulan ve stok sayacını artıran zamanlanmış bir iş gerekir."),
                sc(4, "Depo ve ürün key'leriyle doğrudan okuma vardır. 6 puan kırıldı: eşik raporu için GROUP BY yoktur; seyrek bir ikinci index ya da bütün table'ın okunması gerekir."),
                sc(10, "On-demand mod 300 denemeyi tek haneli milisaniyede karşılar. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(7, "Serverless. 3 puan kırıldı: ekip SQL biliyor; key tasarımı ve transaction hata kodları yeni bir öğrenmedir."),
                sc(8, "İstek başına ödeme. 2 puan kırıldı: transaction'lı yazmalar ve zamanlanmış iade işi birim tüketir.")],
    },
    h2h={
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. MemoryDB yazmanın biçiminde öndedir: sayaçlar bellekte, tek thread'de sırayla değişir, sıcak ürün bir kilit kuyruğu oluşturmaz ve süre sonu sorted set ile hassastır. Çoklu AZ log'u sayesinde stok kaybolmaz; ElastiCache Serverless'ın bu kartta aday olmamasının nedeni tam olarak budur. "
               "Ama sabah raporu \"depo başına eşiğin altındaki ürünler\" bir GROUP BY'dır; Valkey'de sorgu dili yoktur ve uygulama ikinci bir yapı tutar. Kural bir Lua script'inde yaşar ve ortada hata verirse geri alınmaz. "
               "Servis tasarımında da Aurora öndedir: ekip SQL biliyor, MemoryDB yeni bir API ve sürekli çalışan node'lar demektir. Saniyede 15 yazmalık sıcak row PostgreSQL'in row lock'u için küçük bir kuyruktur. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: sıcak ürün başına yazma saniyede binlere çıksaydı ve rapor ayrı bir analitik kopyadan alınsaydı.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB R2 ve R3'te güçlüdür: on-demand mod kampanya anını ayarsız taşır ve her yazma birkaç AZ'de saklanır; TransactWriteItems rezervasyonu ve stok düşürmeyi ya hep ya hiç yapar. "
               "Ama aynı on ürüne yarışan transaction'lar çakışır ve iptal edilir: uygulama yeniden dener ve kampanya anında bu sık olur. Süre sonu da zayıftır: TTL birkaç gün içinde siler, 15 dakikalık iade için zamanlanmış bir iş gerekir. Sabah raporu için GROUP BY yoktur. "
               "Aurora'da kural tek transaction'dır, süre sonu sorgunun koşuludur ve rapor tek SQL'dir. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: rezervasyon tek bir item'ın koşullu yazması olsaydı (depo yok, tek stok sayacı), trafik saniyede on binlere çıksaydı ve rapor zero-ETL ile Redshift'ten alınsaydı.",
    },
    verdict="Karar: Aurora {aur}, DynamoDB {ddb}, MemoryDB {mdb}. Kararı R1'in atomiklik ve erişim yolu satırları verir: rezervasyon, stok ve sabah raporu aynı modelde, aynı transaction'la korunur. "
            "Aurora PostgreSQL seçtiğimizde artımız: kural tek transaction'dır ve yarışan istek yeni değeri görür; rapor tek SQL'dir; stok altı kopyayla kalıcıdır. "
            "Eksimiz: sıcak row'larda istekler sıraya girer ve VACUUM izlenmelidir; eski rezervasyon row'ları zamanlanmış bir işle silinir; lock_timeout ile bekleme süresi sınırlanmalıdır. "
            "Bir koşul değişseydi: sıcak ürün başına yazma saniyede binlere çıksaydı MemoryDB öne geçerdi."))

# ------------------------------------------------------------------ 4. customer accounts, addresses and consents
AURORA_W.append(wusecase("accounts", 4,
    title="Müşteri hesapları, adresler ve izinler",
    key="Table'lar: customers, addresses, payment_methods, consents. E-posta benzersiz, adres müşteriye bağlı.",
    story=astory("accounts"),
    wnote="R1 toplam 48: benzersiz e-posta ve bağlı adresler (ŞE 14) ile eksiksiz silme (TA 14) hukuki kurallardır; erişim yolu ve verinin şekli de engine'in işidir. "
          "R3 20 ile en ağır ikinci satır: hesap verisinin kaybı güven kaybıdır.",
    rows=[
        row("ŞE", 14, "Aynı e-postayla iki hesap bir güvenlik olayıdır; kural yazma anında korunmalı.",
            "Bir e-posta tam olarak bir hesaba ait olmalı; adres, ödeme yöntemi ve izin var olan bir müşteriye bağlı olmalı. Hukuk ekibinin çeyrekte bir eklediği yeni izin türü kesintisiz eklenebilmeli. KVKK (Kişisel Verilerin Korunması Kanunu) silme ve izin kaydı ister.",
            "Aynı e-postayla iki hesap, şifre sıfırlamada yanlış kişiye giden bir e-postadır. Sahipsiz bir ödeme yöntemi bir denetimde açıklanamaz."),
        row("TA", 14, "\"Verimi sil\" hukuki bir yükümlülüktür; yarım silme bir ihlaldir.",
            "\"Verimi sil\" müşteriyi, adreslerini, ödeme yöntemlerini ve izinlerini ya hep ya hiç silmeli; siparişler müşteriye bağlı kalırken kişisel alanlar boşaltılmalı.",
            "Yarım kalan bir silme hem hukuki bir ihlaldir hem de bir sonraki girişte bozuk bir hesap ekranıdır."),
        row("EY", 12, "Login her oturumun ilk adımıdır; destek ekibi de her gün yeni sorular sorar.",
            "Hesap id ve e-posta ile okunmalı; \"bu müşterinin adresleri ve son siparişleri\" ve \"izni geri çeken müşteriler\" doğrudan sorulabilmeli.",
            "Login yavaşsa her şey yavaştır; destek ekibinin sorusu bir mühendis isterse cevap günler sürer."),
        row("VM", 8, "Verinin şekli sabit ve kurallıdır; ağırlık bu yüzden düşüktür.",
            "Bir müşterinin birkaç adresi, birkaç ödeme yöntemi ve izin geçmişi vardır; alanlar sabittir, sayıları müşteriden müşteriye değişir.",
            "Liste alanları kötü modellenirse bir adresi değiştirmek bütün hesabı yeniden yazmak olur."),
        row("R2", 14, "Saniyede 500 okuma, 20 yazma, yılda yüzde 30 büyüme.",
            _AOLD["accounts"]["reqs"][1]["want"][1], _AOLD["accounts"]["reqs"][1]["why"][1]),
        row("R3", 20, "Hesap verisinin kaybı güven kaybıdır ve kabul edilmez.",
            "Hesap verisi kalıcıdır; AZ arızasında kayıp olmamalı; yanlış bir silme geri alınabilmeli.",
            _AOLD["accounts"]["reqs"][2]["why"][1]),
        row("R4", 10, "Beş geliştirici SQL biliyor; siparişler aynı database'te.",
            "Beş geliştirici SQL biliyor; siparişler aynı database'te. Sunucu boyutlandırma ve yama istenmiyor; ikinci bir database türü işletilmek istenmiyor.", "Ayrı bir sistem ayrı bir yedek, izleme ve nöbet demektir; beş kişilik ekipte bu ürün geliştirmeden çalınan zamandır."),
        row("R5", 8, "Veri küçük ve trafik düz; fatura kararı tek başına çevirmez.",
            _AOLD["accounts"]["reqs"][4]["want"][1], _AOLD["accounts"]["reqs"][4]["why"][1]),
    ],
    cands=["aur", "rds", "doc"],
    scores={
        "aur": [sc(10, "UNIQUE (email) ve foreign key'ler (Ö1, Ö2) her yazmada çalışır; yeni izin türü consents table'ında yeni bir row'dur, schema değişmez. Puan kırılmadı."),
                sc(10, "Silme tek transaction'dır (Ö5); ON DELETE CASCADE adresleri, ödeme yöntemlerini ve izinleri birlikte siler, siparişlerdeki kişisel alanlar aynı transaction'da boşaltılır. Puan kırılmadı."),
                sc(10, "Primary key ve e-posta üzerinde B-tree index (Ö4); adresler ve son siparişler bir JOIN'dir (Ö3). Puan kırılmadı."),
                sc(9, "Adresler ve ödeme yöntemleri müşteriye bağlı ayrı table'lardır; bir adres tek row olarak değişir. 1 puan kırıldı: hesap ekranı dört table'ın JOIN'idir."),
                sc(10, "500 okuma index aramasıdır ve reader'lara dağılır; yeni bir reader dakikalar içinde aynı storage'a bağlanır (Ö7). Puan kırılmadı."),
                sc(10, "Üç AZ'de altı kopya, point-in-time restore. Puan kırılmadı."),
                sc(9, "Siparişler aynı database'te; ekip SQL biliyor ve yeni bir servis gerekmez. 1 puan kırıldı: reader sayısı ve ACU aralığı ekibin seçimidir."),
                sc(8, "ACU-saat ile ödenir. 2 puan kırıldı: minimum ACU boş saatlerde de ödenir.")],
        "doc": [sc(6, "E-posta üzerinde unique index benzersizliği korur. 4 puan kırıldı: foreign key yoktur; siparişlerin gösterdiği müşterinin var olduğunu uygulama kontrol eder."),
                sc(9, "Adresler, ödeme yöntemleri ve izinler müşteri document'ının içindedir; silme tek document'ta atomiktir. 1 puan kırıldı: siparişler ayrı bir collection'dadır ve kişisel alanlarını boşaltmak bir transaction daha ister."),
                sc(8, "Id ve e-posta index'leri ile okuma hızlıdır. 2 puan kırıldı: \"son siparişler\" başka bir collection'dadır ve $lookup ile birleştirilir."),
                sc(10, "Müşteri, içinde adres ve izin dizileriyle tek bir document'tır; tek okumayla gelir. Puan kırılmadı."),
                sc(9, "Okumalar replica'lara dağılır. 1 puan kırıldı: instance sınıfı ve replica sayısı önceden seçilir."),
                sc(10, "Üç AZ'de altı kopya, sürekli yedek. Puan kırılmadı."),
                sc(6, "Yedek ve yama yönetilir. 4 puan kırıldı: yanında yeni bir cluster işletilir ve MongoDB API'si bu SQL ekibi için yenidir."),
                sc(7, "Instance saat başına ödenir. 3 puan kırıldı: en az iki yeni instance sürekli çalışır.")],
        "rds": [sc(10, "Aynı PostgreSQL engine'i: UNIQUE (email) ve foreign key'ler (Ö1, Ö2) aynı çalışır. Puan kırılmadı."),
                sc(10, "Aynı transaction ve ON DELETE CASCADE (Ö5). Puan kırılmadı."),
                sc(10, "Aynı index'ler ve JOIN (Ö3, Ö4). Puan kırılmadı."),
                sc(9, "Aynı table'lar. 1 puan kırıldı: hesap ekranı dört table'ın JOIN'idir."),
                sc(8, "500 okuma bir instance ve read replica'larla karşılanır. 2 puan kırıldı: her read replica kendi storage kopyasıdır ve bir snapshot'tan kurulur; yeni bir replica Aurora'daki gibi dakikalar içinde değil, verinin boyutuna göre daha uzun sürede hazırdır."),
                sc(9, "Multi-AZ senkron standby commit edilmiş hesabı korur; point-in-time restore vardır. 1 puan kırıldı: failover \"typically … one to two minutes\" sürer ve bu sürede login çalışmaz."),
                sc(9, "Yönetilen servis; storage auto scaling vardır. 1 puan kırıldı: instance sınıfı ve gp3 storage'ın IOPS ayarı ekibin seçimidir."),
                sc(9, "eu-central-1'de db.r6g.large saatte 0,274 USD'dir (Aurora Standard'da 0,313 USD) ve I/O isteği başına ücret yoktur; düz trafikte reserved instance alınabilir. 1 puan kırıldı: Multi-AZ standby okuma almaz ama ödenir.")],
    },
    h2h={
        "doc": "Document (DocumentDB) ile kafa kafaya. DocumentDB verinin şeklinde öndedir: müşteri, adresleri, ödeme yöntemleri ve izinleriyle tek bir document'tır ve \"verimi sil\" tek bir document silmesidir. E-posta için unique index de vardır. "
               "Ama siparişler müşteriye bağlıdır ve başka bir collection'dadır: siparişin gösterdiği müşterinin var olduğunu database kontrol etmez, kişisel alanların boşaltılması ikinci bir adımdır, \"son siparişler\" bir $lookup'tır. "
               "Aurora'da bu ilişkiler foreign key ve tek transaction'dır ve siparişler zaten aynı database'tedir. Servis tasarımında da Aurora öndedir: yeni bir cluster ve yeni bir API gerekmez. "
               "Hangi koşul değişseydi DocumentDB seçilirdi: hesaplar siparişlerden ayrı bir sistemde yaşasaydı, profil alanları her ay köklü değişseydi ve ekip MongoDB API'sini biliyor olsaydı.",
        "rds": "Aynı engine'in RDS biçimi (RDS for PostgreSQL) ile kafa kafaya. İki aday aynı PostgreSQL engine'ini çalıştırır: UNIQUE e-posta, foreign key'ler ve ON DELETE CASCADE aynıdır; R1'de ikisi de 47,2 alır ve fark yalnız R2–R5'tedir. "
               "RDS'in gücü fiyattır: düz ve okuma ağırlıklı bu yükte aynı instance sınıfı daha ucuzdur ve I/O ücreti yoktur. Aurora'nın gücü R2 ve R3'tedir: reader'lar aynı storage'ı okur ve dakikalar içinde eklenir, failover genellikle 30 saniyenin altındadır; RDS Multi-AZ'de bir iki dakika boyunca login çalışmaz. "
               "Bu kartta R3 20 ağırlığındadır, çünkü hesap verisi güvendir ve login her oturumun ilk adımıdır; fark bu yüzden küçük ama Aurora'dan yanadır. "
               "Hangi koşul değişseydi RDS for PostgreSQL seçilirdi: bir iki dakikalık login kesintisi kabul edilseydi ve database faturası kararın önüne geçseydi; kart 5'teki gibi düz trafik ve fiyat hassasiyeti RDS'e kazandırır.",
    },
    verdict="Karar: Aurora {aur}, RDS {rds}, DocumentDB {doc}. Kararı R1'in şema ve atomiklik satırları verir: benzersiz e-posta, bağlı adresler ve eksiksiz silme database'in kurallarıdır. "
            "Aurora PostgreSQL seçtiğimizde artımız: kurallar her programa uygulanır, silme tek transaction'dır, siparişlerle JOIN aynı database'tedir, yeni izin türü yeni bir row'dur. "
            "Eksimiz: hesap ekranı birkaç table'ın JOIN'idir; minimum ACU boş saatlerde de ödenir; login çok büyürse reader'lar ve önbellek planlanır. "
            "Silme yedekleri ve kopyaları da ilgilendirir: point-in-time yedekleri silinen müşteriyi saklama süresi (1–35 gün) dolana kadar tutar ve bu süre gizlilik politikasında yazılmalıdır; zero-ETL ile Redshift'e giden bir kopya silmeyi değişiklik olarak alır. "
            "Bir koşul değişseydi: hesaplar siparişlerden ayrı bir sistemde yaşasaydı DocumentDB yarışa girerdi."))

# ------------------------------------------------------------------ 5. multi-tenant SaaS with row-level security (RDS wins)
AURORA_W.append(wusecase("tenant", 5, sim="w_tenant",
    title="Çok kiracılı SaaS: row-level security ile tenant ayrımı",
    key="Her table'da tenant_id column'u. Policy: bir session sadece kendi tenant_id'sinin row'larını görür.",
    story=astory("tenant").replace("Saniyede 2.000 okuma ve 100 yazma; mesai saatlerinde tepe.",
                                   "Saniyede 2.000 okuma ve 100 yazma; trafik mesai saatlerinde düz ve yıllardır öngörülebilir.")
          + " Şirketin fiyat modeli tenant başına sabit bir aylık ücrettir; database faturası tenant başına marjı doğrudan belirler.",
    wnote="R1 toplam 40: tenant ayrımı (AO 16), fatura ilişkileri (ŞE 12) ve aylık toplamlar (EY 12) engine'in işidir ve en ağır gruptur. "
          "R5 20 ile en ağır ikinci satır: fiyat modeli tenant başına sabittir ve database faturası marjı belirler. R2 18: gürültülü bir tenant'ın gece dışa aktarması gündüzü yavaşlatmamalı ve 800 tenant 3.000'e çıkacak; trafik düz olduğu için ani bir tepe beklenmez.",
    rows=[
        row("AO", 16, "En büyük kural budur: bir bug olsa bile bir şirket başkasının faturasını görmemeli.",
            "Her sorgu, uygulama kodu WHERE tenant_id = … yazmayı unutsa bile, sadece o session'ın tenant'ının row'larını görmeli ve değiştirmeli; kural raporlama araçlarına ve elle yazılan SQL'e de uygulanmalı.",
            "Bir WHERE unutulduğunda B şirketinin faturaları A'nın ekranında belirir; bu sözleşme ihlali ve itibar kaybıdır."),
        row("ŞE", 12, "Fatura resmi kayıttır; kalemler, müşteriler ve ödemeler birbirine bağlıdır.",
            "Fatura, kalem, müşteri ve ödeme ilişkileri database'de korunmalı; bir kalem var olmayan bir faturayı gösterememeli.",
            "Sahipsiz bir kalem ya da başka tenant'ın müşterisine bağlı bir fatura bir vergi denetiminde açıklanamaz."),
        row("EY", 12, "Her şirket aylık toplamlarını ister; raporlar ürünün bir parçasıdır.",
            "Şirket başına aylık toplamlar ve fatura listeleri tek sorgu olmalı; 200 GB'lık table'larda bile tek bir tenant'ın verisine dokunmalı.",
            "Rapor bütün tenant'ları tararsa küçük bir şirketin raporu büyük bir şirketin verisi kadar yavaşlar."),
        row("R2", 18, "Saniyede 2.000 okuma, 100 yazma; gece dışa aktarmaları gündüzü etkilememeli.",
            "Saniyede 2.000 okuma ve 100 yazma, mesai saatlerinde düz. Her okuma 30 ms'nin altında. 800 tenant 3.000'e çıkacak; bir tenant'ın gece dışa aktarması diğerlerini yavaşlatmamalı.",
            _AOLD["tenant"]["reqs"][1]["why"][1]),
        row("R3", 12, "Fatura resmi kayıttır ve kaybı kabul edilmez; müşteriler bir iki dakikalık bir kesintiyi tolere eder, saatlerce süreni etmez.",
            "Fatura resmi kayıttır; AZ arızasında commit edilmiş tek bir fatura kaybolmamalı ve servis birkaç dakika içinde dönmeli.",
            _AOLD["tenant"]["reqs"][2]["why"][1]),
        row("R4", 10, "Bir operasyon mühendisi var; ekip PostgreSQL biliyor.",
            _AOLD["tenant"]["reqs"][3]["want"][1], _AOLD["tenant"]["reqs"][3]["why"][1]),
        row("R5", 20, "Fiyat tenant başına sabittir; database faturası marjı doğrudan belirler.",
            "Trafik düz ve öngörülebilir; kapasite rezerve edilebilir. Maliyet tenant sayısıyla doğrusal artmalı; gece dışa aktarmalarının disk okuması faturayı sıçratmamalı.",
            "3.000 tenant için maliyet sıçrarsa fiyat modeli bozulur; her yüzde 10'luk fark yıllık marjın bir parçasıdır."),
    ],
    cands=["rds", "aur", "ddb"],
    scores={
        "rds": [sc(10, "Aynı PostgreSQL engine'i: row-level security policy'si her sorguya tenant koşulunu ekler (Ö8); uygulama sahip olmayan bir role ile bağlanır. Puan kırılmadı."),
                sc(10, "Foreign key ve CHECK (Ö1, Ö2) fatura ilişkilerini korur. Puan kırılmadı."),
                sc(9, "Aylık toplamlar GROUP BY'dır (Ö3). 1 puan kırıldı: 200 GB'ta tek tenant'a dokunmak için (tenant_id, ay) index'i ve aya göre partition tasarımı gerekir."),
                sc(8, "En fazla 15 read replica okumayı taşır; dışa aktarma bir replica'da çalışır. 2 puan kırıldı: her replica kendi storage kopyasıdır, bir snapshot'tan kurulur ve 200 GB için saatler sürebilir; replica gecikmesi Aurora'dakinden yüksek olabilir."),
                sc(9, "Multi-AZ'de senkron bir standby commit edilmiş veriyi korur. 1 puan kırıldı: failover \"typically … one to two minutes\" sürer; iki okunabilir standby'lı Multi-AZ seçeneği alınırsa bu süre 35 saniyenin altına iner ama maliyet artar."),
                sc(8, "Yedek, yama ve failover yönetilir; storage auto scaling vardır. 2 puan kırıldı: gp3 storage'ın IOPS ve throughput ayarı ekibin işidir."),
                sc(9, "eu-central-1'de db.r6g.large saatte 0,274 USD'dir (on demand) ve I/O isteği başına ücret yoktur; reserved instance düz trafiğe uyar. 1 puan kırıldı: Multi-AZ'nin standby'ı okuma almaz ama ödenir.")],
        "aur": [sc(10, "Aynı PostgreSQL engine'i: row-level security (Ö8) RDS ile aynı çalışır. Puan kırılmadı."),
                sc(10, "Foreign key ve CHECK (Ö1, Ö2) aynıdır. Puan kırılmadı."),
                sc(9, "Aylık toplamlar GROUP BY'dır (Ö3). 1 puan kırıldı: aynı index ve partition tasarımı gerekir."),
                sc(9, "En fazla 15 reader aynı storage'ı okur; yeni bir reader dakikalar içinde hazırdır ve gecikme \"usually considerably less than 100 milliseconds\" (Ö7). 1 puan kırıldı: gece dışa aktarması reader'da çalışsa da storage I/O'su paylaşılır."),
                sc(10, "Üç AZ'de altı kopya; failover genellikle 60 saniyenin, çoğu zaman 30 saniyenin altındadır. Puan kırılmadı."),
                sc(9, "Storage kendiliğinden büyür, IOPS ayarı yoktur. 1 puan kırıldı: Standard ile I/O-Optimized arasındaki seçim ve instance sınıfı ekibin işidir."),
                sc(6, "Instance ve storage ödenir. 4 puan kırıldı: eu-central-1'de db.r6g.large saatte 0,313 USD'dir (Standard), yani RDS'ten yüzde 14 pahalıdır; gece dışa aktarmalarının I/O'su Standard'da ayrıca ödenir, I/O-Optimized'da ise instance saatte 0,407 USD'dir.")],
        "ddb": [sc(3, "Partition key'in başına tenant id'si konur. 7 puan kırıldı: engine'de row bazında bir policy yoktur; IAM koşuluyla ayrım servisin bir aracıdır ve her sorgunun doğru key'i kurması yine uygulamanın işidir."),
                sc(4, "Value'nun içini database denetlemez. 6 puan kırıldı: fatura, kalem ve ödeme arasında foreign key yoktur."),
                sc(4, "Tenant'ın faturaları bir Query'dir. 6 puan kırıldı: aylık toplamlar için GROUP BY yoktur; uygulama toplar ya da sayaçlar tutar."),
                sc(10, "On-demand mod her tenant'ı partition'lara dağıtır; gürültülü bir tenant diğerlerini yavaşlatmaz. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(6, "Serverless. 4 puan kırıldı: ekip PostgreSQL biliyor ve bütün fatura modeli key tasarımına yeniden yazılır."),
                sc(7, "İstek başına ödeme. 3 puan kırıldı: gece dışa aktarmaları bütün item'ları okur ve okuma birimi olarak ödenir.")],
    },
    h2h={
        "aur": "Aynı engine'in Aurora biçimi (Aurora PostgreSQL) ile kafa kafaya. İki aday da aynı PostgreSQL engine'ini çalıştırır: row-level security, foreign key ve GROUP BY aynıdır, R1'de ikisi de 38,8 alır. Kararı tamamen servis tasarımı verir. "
               "Aurora R2, R3 ve R4'te öndedir: reader'lar aynı storage'ı okur ve dakikalar içinde eklenir, veri altı kopyadır ve failover genellikle 30 saniyenin altındadır. RDS ise R5'te öndedir: aynı instance sınıfı saatte 0,274 USD'ye karşı 0,313 USD'dir ve dışa aktarmaların I/O'su ayrıca ödenmez. "
               "Bu kartta fiyat modeli tenant başına sabittir ve trafik düzdür; Aurora'nın esnekliği az kullanılır, fiyat farkı her ay ödenir. Fark 2 puandır: bu yakın bir yarıştır ve RDS'ten Aurora'ya geçiş bir read replica ile kısa kesintiyle yapılabilir. "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: trafik gün içinde ya da ay sonunda dalgalı olsaydı, birkaç dakikalık failover sözleşmeye aykırı olsaydı ya da reader sayısı sık değişseydi.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB gürültülü tenant probleminde güçlüdür: her tenant'ın verisi partition'lara dağılır, bir tenant'ın gece dışa aktarması diğerlerini yavaşlatmaz ve kapasite planı yoktur. "
               "Ama bu kartın en büyük kuralı engine'de yoktur: row bazında bir policy yoktur, ayrım partition key tasarımına ve IAM koşullarına dayanır ve her sorgunun doğru key'i kurması uygulamanın işidir. Fatura ilişkileri için foreign key, aylık toplamlar için GROUP BY yoktur. "
               "PostgreSQL'de aynı kurallar bir policy, foreign key'ler ve tek bir SQL'dir; ekip de PostgreSQL biliyor. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: tenant başına veri basit ve ilişkisiz olsaydı (örneğin tenant başına ayar ve sayaçlar), raporlar ayrı bir analitik kopyadan gelseydi ve trafik saniyede on binlere çıksaydı.",
    },
    verdict="Karar: RDS {rds}, Aurora {aur}, DynamoDB {ddb}. Bu iş yüküne en uygun servis RDS for PostgreSQL'dir; Aurora PostgreSQL 2 puan geride ikincidir: yakın bir yarış. Engine aynıdır ve R1 eşittir; kararı düz trafikte R5'teki fiyat farkı verir. "
            "Yine de Aurora PostgreSQL seçersek artımız: reader'lar dakikalar içinde eklenir ve aynı storage'ı okur, failover genellikle 30 saniyenin altındadır, storage ve IOPS ayarı yoktur. "
            "Eksimiz: instance saatte yüzde 14 pahalıdır ve dışa aktarmaların I/O'su Standard'da ayrıca ödenir; uygulama I/O payını izlemeli ve yüzde 25'i geçerse I/O-Optimized'a geçmelidir. "
            "Bir koşul değişseydi: trafik dalgalı olsaydı ya da failover süresi sözleşmede 30 saniye olsaydı Aurora kazanırdı."))

# ------------------------------------------------------------------ 6. reporting: from 90 days to three years (Redshift wins)
AURORA_W.append(wusecase("reporting", 6, sim="w_reporting",
    title="Raporlama: son 90 günden üç yıllık geçmişe",
    key="Table'lar: orders, order_items, products, customers; üç yıl, iki milyar row. Sorular ay, şehir ve kategoriye göre toplamlar.",
    story=astory("reporting"),
    wnote="R1 toplam 48: soru her row'un sadece birkaç column'unu okuyan bir taramadır, bu yüzden depolama algoritması (DA 16) en ağır alt maddedir; serbest SQL (EY 14) analistlerin işidir. "
          "R2 20 ile en ağır ikinci satır: 30 dashboard aynı anda iki milyar row tarar ve checkout bunu hissetmemelidir. Veri bir kopyadır, bu yüzden R3 5'te kalır.",
    rows=[
        row("DA", 16, "Her sorgu geçmişin tamamını tarar ama row başına üç dört column okur; depolama biçimi süreyi belirler.",
            "İki milyar row üzerinde, sadece birkaç column'u okuyan taramalar 10 saniyenin altında dönmeli. Diskten okunan veri sorgunun column'larıyla sınırlı olmalı.",
            "Tam row'ları okuyan bir tarama iki milyar row'da yüzlerce GB okur; dashboard'lar 10 saniyeyi aşar ve kullanılmaz."),
        row("EY", 14, "Analistler her hafta yeni bir soru soruyor; key tasarımı istemiyorlar.",
            "JOIN, GROUP BY ve window fonksiyonları içeren serbest SQL; \"şehre, kampanyaya ve cihaz tipine göre iade oranı\" gibi yeni bir soru bir mühendis beklemeden yazılabilmeli.",
            "Her yeni soru için bir mühendis gerekirse finans ekibi beklemeye başlar ve dashboard'lar eskir."),
        row("AO", 10, "30 dashboard'un hızı engine'in sıkıştırma ve sıralama araçlarına bağlıdır.",
            "Sıkıştırma, sıralama ve ön hesaplanmış özetler engine'in kendi araçlarıyla yapılabilmeli; zamana göre aralık okumaları geçmişin tamamını açmamalı.",
            "Bu araçlar yoksa aynı sonuç için daha büyük ve daha çok makine gerekir."),
        row("OY", 8, "Veri checkout'tan akar: ekleme ve az sayıda güncelleme; biçim basittir.",
            "Engine ekleme ağırlıklı, sürekli bir yazma akışını ve arada gelen güncellemeleri (iade, iptal) kabul etmeli; bir güncelleme taramaları bozmamalı.",
            "Engine sürekli küçük yazmaları kötü karşılarsa veri toplu yüklenmek zorunda kalır ve dashboard saatlerce eski kalır."),
        row("R2", 20, "30 dashboard aynı anda iki milyar row tarar; checkout bunu hissetmemeli.",
            _AOLD["reporting"]["reqs"][1]["want"][1], _AOLD["reporting"]["reqs"][1]["why"][1]),
        row("R3", 5, "Veri bir kopyadır; kaynak checkout'tadır.",
            _AOLD["reporting"]["reqs"][2]["want"][1], _AOLD["reporting"]["reqs"][2]["why"][1]),
        row("R4", 13, "İki kişilik veri ekibi var; boru hattı kod istemeden kurulmalı.",
            _AOLD["reporting"]["reqs"][3]["want"][1], _AOLD["reporting"]["reqs"][3]["why"][1]),
        row("R5", 14, "Analistler mesai saatinde çalışır ve veri yüzlerce GB'tır; ödeme modeli belirleyicidir.",
            _AOLD["reporting"]["reqs"][4]["want"][1], _AOLD["reporting"]["reqs"][4]["why"][1]),
    ],
    cands=["rs", "os", "aur"],
    scores={
        "rs": [sc(10, "Redshift columnar bir store'dur ve veriyi 1 MB'lık bloklarda column column tutar; tarama sadece sorgunun column'larını okur ve bloklar sıkıştırılmıştır. Puan kırılmadı."),
               sc(10, "PostgreSQL'e yakın bir SQL: JOIN, GROUP BY, window fonksiyonları; analistler bildikleri SQL'i yazar. Puan kırılmadı."),
               sc(9, "Column başına sıkıştırma, sort key ve materialized view engine'in araçlarıdır. 1 puan kırıldı: sort key ve distribution seçimi bir tasarım işidir."),
               sc(9, "Columnar engine ekleme akışını blok blok kabul eder. 1 puan kırıldı: tek row'luk bir güncelleme column bloklarında eski değeri silinmiş işaretleyip yenisini ekler; çok güncellenen veride VACUUM ve sıralama bakımı gerekir."),
               sc(10, "MPP: sorgu birçok compute birimine paylaştırılır ve Serverless kapasiteyi eşzamanlı sorgulara göre artırır; checkout ayrı bir database'tedir. Puan kırılmadı."),
               sc(9, "Snapshot'lar alınır. 1 puan kırıldı: kopya kaybolursa zero-ETL entegrasyonu yeniden kurulur ve ilk yükleme sürer."),
               sc(9, "Zero-ETL kod yazmadan kurulur ve checkout'un yazmalarını saniyeler içinde getirir. 1 puan kırıldı: sort key ve workgroup ayarları ekibin işidir."),
               sc(8, "Serverless RPU-saat olarak, saniye başına ve 60 saniye minimumla ödenir; boşta compute ödenmez. 2 puan kırıldı: dashboard'lar her beş dakikada yenilendiği için mesai boyunca kapasite çalışır; base RPU dikkatle seçilmelidir.")],
        "aur": [sc(3, "Index'ler dar aralıkları hızlandırır. 7 puan kırıldı: PostgreSQL row'ları tam olarak saklar; geçmişin tamamını tarayan bir sorgu, sadece üç column gerekse de her row'un tamamını okur."),
                sc(10, "Aynı SQL, JOIN ve GROUP BY (Ö3); analistler kolon adlarını bilir. Puan kırılmadı."),
                sc(6, "Zamana göre partition, BRIN index ve materialized view (Ö4, Ö6) kullanılabilir. 4 puan kırıldı: column bazlı sıkıştırma yoktur ve materialized view'lar elle yenilenir."),
                sc(10, "Row store tek row'luk ekleme ve güncellemeyi doğrudan yapar. Puan kırılmadı."),
                sc(5, "Raporlar reader instance'larda çalışır ve writer'ın CPU'sunu kullanmaz; reader eklenerek eşzamanlılık büyür (Ö7). 5 puan kırıldı: reader'lar checkout ile aynı storage'ı okur ve 30 eşzamanlı tarama storage I/O'sunu checkout ile paylaşır; tarama süresinin kendisi R1 · DA'da sayıldı."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı: ama bu kartta veri bir kopyadır."),
                sc(8, "Boru hattı yoktur, veri checkout'un kendisindedir; reader eklemek dakikalardır. 2 puan kırıldı: partition ve materialized view bakımı iki kişilik ekibin işidir."),
                sc(4, "Reader instance saat başına ödenir. 6 puan kırıldı: büyük reader'lar 7/24 çalışır ve Standard'da her taramanın I/O'su ayrıca ödenir.")],
        "os": [sc(7, "Aggregation'lar column bazlı doc values üzerinde çalışır. 3 puan kırıldı: engine bir arama engine'idir; iki milyar row'luk taramalar shard'lara dağıtılır ama bir warehouse kadar sıkıştırılmaz."),
               sc(4, "SQL ve PPL desteği vardır. 6 puan kırıldı: JOIN ve serbest SQL sınırlıdır; analistlerin yeni sorusu çoğu zaman yeni bir index tasarımı ister."),
               sc(6, "Index şablonları, rollup ve zamana göre index'ler vardır. 4 puan kırıldı: sipariş ve satırlar düzleştirilmeden ilişki soruları sorulamaz."),
               sc(7, "Document ekleme hızlıdır. 3 puan kırıldı: bir güncelleme document'ın yeni bir sürümünü yazar ve sipariş satırları düzleştirildiği için bir iade birçok document'ı değiştirir."),
               sc(9, "Shard'lar ve node'lar okumayı paylaşır. 1 puan kırıldı: kapasite sabittir; 30 dashboard için node'lar önceden eklenir (node ve shard planı R4'te sayıldı)."),
               sc(8, "Replica shard'lar ve snapshot'lar. 2 puan kırıldı: kopya kaybolursa pipeline baştan yükler."),
               sc(4, "Yönetilen domain; OpenSearch Ingestion Aurora PostgreSQL'in değişikliklerini akıtabilir. 6 puan kırıldı: dört table'ı document'lara düzleştiren pipeline, mapping ve shard planı iki kişilik ekip için yeni bir alan ve SQL bilen analistler için yeni bir araçtır."),
               sc(6, "Node saat başına ödenir. 4 puan kırıldı: domain gece de çalışır ve yüzlerce GB için büyük node'lar gerekir.")],
    },
    h2h={
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Bu kartta Aurora net kaybeder ve kaybı R1'in depolama satırından gelir. Aurora'nın gücü gerçektir: veri zaten oradadır, SQL aynıdır ve son 90 günlük sorular reader'da saniyeler içinde döner. "
               "Ama PostgreSQL row'ları tam olarak saklar; üç column isteyen bir sorgu iki milyar row'un tamamını okur. Redshift aynı soruyu column bloklarından, sıkıştırılmış ve birçok compute birimine paylaştırılmış olarak okur. "
               "Servis tasarımı da aynı yöndedir: 30 dashboard için büyük reader'lar 7/24 çalışır ve I/O ödenir; Redshift Serverless boşta compute ödemez. Doğru cevap ikisi birliktedir: Aurora checkout'un kaydıdır, zero-ETL kopyası Redshift'te raporlanır. "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: raporlar son 90 günle sınırlı kalsaydı, birkaç analist günde birkaç sorgu çalıştırsaydı ve ayrı bir servis işletmek istenmeseydi.",
        "os": "Search engine (OpenSearch) ile kafa kafaya. OpenSearch'ün gücü zamana göre index'lenmiş veride hızlı aggregation ve hazır dashboard'lardır; log analizi ve gözlem panoları için doğru araçtır. "
              "Ama bu kartın soruları ilişkiseldir: sipariş, satır, ürün ve müşteri arasında JOIN'ler ve her hafta yeni bir SQL sorusu. OpenSearch'te bu veri önce document'lara düzleştirilir; yeni bir ilişki sorusu yeni bir pipeline ve yeni bir index demektir. SQL bilen analistler için de yeni bir araçtır. "
              "Redshift aynı veriyi zero-ETL ile, table'ları değiştirmeden alır ve SQL ile sorar. "
              "Hangi koşul değişseydi OpenSearch seçilirdi: dashboard'lar ilişkisiz olay verisi üzerinde (loglar, tıklamalar) çalışsaydı ve metin araması ile aggregation birlikte istenseydi.",
    },
    verdict="Karar: Redshift {rs}, OpenSearch {os}, Aurora {aur}. Bu iş yüküne en uygun servis Redshift'tir; OpenSearch ve Aurora PostgreSQL çok geride ve birbirine çok yakındır (0,2 puan), Aurora üçüncüdür. Kararı R1'in depolama satırı ve R2 verir: geçmişin tamamını tarayan sorgular columnar ve MPP bir engine ister. "
            "Yine de Aurora PostgreSQL seçersek artımız: kopya ve boru hattı yoktur, veri gerçek zamanlıdır, SQL aynıdır. "
            "Eksimiz: büyük reader'lar 7/24 ödenir, taramalar storage I/O'sunu checkout ile paylaşır, 10 saniye sınırı iki milyar row'da tutulamaz; uygulama raporları son 90 günle sınırlamak ve özetleri materialized view'larla tutmak zorunda kalır. "
            "Doğru mimari ikisi birliktedir: Aurora kayıt sistemi, zero-ETL ile Redshift rapor tarafı. Bir koşul değişseydi: raporlar 90 günle sınırlı kalsaydı Aurora yeterdi."))

# ------------------------------------------------------------------ 7. invoices and double-entry ledger (R1 equal with RDS)
AURORA_W.append(wusecase("ledger", 7, sim="w_ledger",
    title="Faturalar ve çift taraflı defter",
    key="Table'lar: accounts, journal_entries, postings (borç ve alacak row'ları), invoices, invoice_lines.",
    story=astory("ledger"),
    wnote="R1 toplam 48: dengeli entry kuralı (TA 18) ve hesap ilişkileri (ŞE 12) muhasebenin kendisidir. "
          "R2 18 ve R3 18 ile ikinci sıradadır: ay sonu iki gün on katlık bir yük getirir ve kayıp sıfır olmalıdır.",
    rows=[
        row("TA", 18, "Dengesiz bir entry muhasebenin kendisini bozar; denetçi bulduğunda şirket ceza alır.",
            "Bir entry'nin bütün posting'leri ya hep ya hiç yazılmalı ve toplamları sıfır olmalı; bu kural commit anında database tarafından kontrol edilmeli.",
            "Yarım bir entry ya da toplamı sıfır olmayan bir entry bilançoyu bozar; hatayı bulmak günler sürer."),
        row("ŞE", 12, "Her posting bir hesaba ait olmalı; commit edilmiş kayıt silinmemeli.",
            "Posting var olan bir hesabı göstermeli; commit edilmiş bir kayıt silinemez ve değiştirilemez, düzeltme ters kayıtla yapılır.",
            "Var olmayan bir hesaba yazılmış para kaybolmuş paradır; silinebilen bir defter denetimden geçmez."),
        row("EY", 10, "Bakiye ve çeyrek sorguları her gün ve her denetimde sorulur.",
            "\"Bu hesabın bakiyesi\", \"bu çeyreğin bütün entry'leri\", \"dengesi tutmayan entry var mı\" doğrudan sorulabilmeli.",
            "Bakiye ayrı bir sayaçta tutulup posting'lerle uyuşmazsa hangisi doğrudur, kimse bilmez."),
        row("AO", 8, "Yedi yıllık veri büyür; eski yıllar ayrı tutulmalı.",
            "Posting table'ı zamana göre partition'lara bölünebilmeli; eski yıllar sorguları yavaşlatmamalı ve saklama süresi dolan yıl tek komutla arşivlenebilmeli.",
            "Yedi yılın tek bir table'da durması her sorguyu ve her bakımı yavaşlatır."),
        row("R2", 18, "Ay sonunda iki gün on katlık yük; kapanış takvime bağlıdır.",
            _AOLD["ledger"]["reqs"][1]["want"][1], _AOLD["ledger"]["reqs"][1]["why"][1]),
        row("R3", 18, "Kaybolan posting kaybolan paradır ve hukuki sorumluluktur.",
            "Sıfır kayıp: commit edilmiş posting bir AZ arızasında kaybolmamalı; yedek dakika hassasiyetinde geri yüklenebilmeli; bir arızadan sonra servis birkaç dakika içinde dönmeli.",
            _AOLD["ledger"]["reqs"][2]["why"][1]),
        row("R4", 8, "Ekipte bir PostgreSQL uzmanı var; ay sonu için elle büyütme istenmiyor.",
            _AOLD["ledger"]["reqs"][3]["want"][1], _AOLD["ledger"]["reqs"][3]["why"][1]),
        row("R5", 8, "Ay sonu için ay boyu ödemek istenmiyor; ama doğruluk faturadan önce gelir.",
            _AOLD["ledger"]["reqs"][4]["want"][1], _AOLD["ledger"]["reqs"][4]["why"][1]),
    ],
    cands=["aur", "rds", "ddb"],
    scores={
        "aur": [sc(9, "Bir entry'nin posting'leri tek transaction'dır (Ö5); toplamı sıfır kuralı DEFERRABLE INITIALLY DEFERRED bir constraint trigger'ı ile commit anında kontrol edilir (Ö6). 1 puan kırıldı: kural bir trigger function'ı olarak yazılır ve test edilir."),
                sc(10, "Foreign key posting'i hesaba bağlar (Ö2); uygulama role'üne UPDATE ve DELETE izni verilmez ve bir trigger commit edilmiş kaydı korur (Ö1, Ö6). Puan kırılmadı."),
                sc(9, "Bakiye bir SUM'dır, çeyrek bir aralık sorgusudur (Ö3, Ö4). 1 puan kırıldı: milyarlarca posting'de bakiye, aynı transaction'da güncellenen bir bakiye table'ıyla ya da materialized view ile tutulur."),
                sc(10, "Declarative partitioning ve pg_partman zamana göre partition'ları yönetir; eski yıl tek komutla ayrılır. Puan kırılmadı."),
                sc(10, "Serverless v2 ay sonunda ACU'yu kendiliğinden artırır, sonra düşürür. Puan kırılmadı: ACU aralığını seçmek R4'te sayıldı."),
                sc(10, "Üç AZ'de altı kopya; point-in-time restore. Puan kırılmadı."),
                sc(9, "Yedek, yama ve failover yönetilir; ay sonu için elle büyütme yoktur. 1 puan kırıldı: ACU aralığı ve partition bakımı ekibin işidir."),
                sc(7, "ACU-saat olarak ödenir; ay sonundan sonra kapasite düşer. Örnek hesap (eu-central-1, on demand, bir instance): 28 gün 2 ACU ve 2 gün 16 ACU = 2.112 ACU-saat × 0,14 USD = yaklaşık 296 USD. 3 puan kırıldı: ACU-saat aynı bellek için provisioned instance'tan pahalıdır, Standard'da I/O ayrıca ödenir ve yedi yıllık storage GB-ay olarak büyür.")],
        "rds": [sc(9, "Aynı PostgreSQL engine'i: aynı transaction ve aynı constraint trigger'ı (Ö5, Ö6). 1 puan kırıldı: kural bir trigger function'ı olarak yazılır."),
                sc(10, "Aynı foreign key ve izinler (Ö1, Ö2). Puan kırılmadı."),
                sc(9, "Aynı SQL (Ö3). 1 puan kırıldı: bakiye için aynı ek table ya da materialized view gerekir."),
                sc(10, "Aynı partitioning ve pg_partman. Puan kırılmadı."),
                sc(8, "Instance ay sonu yüküne göre boyutlanırsa 1.500 posting/saniye karşılanır. 2 puan kırıldı: yazma kapasitesi instance sınıfıyla sabittir; yedi yıllık büyümede sınıf değişikliği kısa bir kesinti ister."),
                sc(9, "Multi-AZ senkron standby commit edilmiş veriyi korur; point-in-time restore vardır. 1 puan kırıldı: failover \"typically … one to two minutes\" sürer."),
                sc(9, "Yönetilen servis; storage auto scaling vardır. 1 puan kırıldı: instance sınıfı ve gp3 storage'ın IOPS ayarı ekibin seçimidir; ay sonu kapasitesi R2'de ve R5'te sayıldı."),
                sc(5, "Instance saat başına ödenir ve I/O başına ücret yoktur. Aynı örnekte ay sonuna göre boyutlanan db.r6g.xlarge (32 GiB, 16 ACU'ya denk) 720 saat × 0,549 USD = yaklaşık 395 USD. 5 puan kırıldı: bu instance ayın 28 gününde büyük ölçüde boş durur ve ödenir.")],
        "ddb": [sc(6, "TransactWriteItems en fazla 100 posting'i ya hep ya hiç yazar. 4 puan kırıldı: \"toplam sıfır\" kuralını database kontrol etmez; uygulama hesaplar ve her program aynı kodu taşır."),
                sc(3, "Koşullu yazma \"item yoksa yaz\" ile üzerine yazmayı engeller. 7 puan kırıldı: posting'in hesabı gösterdiğini database kontrol etmez; silme ve değiştirme izni IAM ile sınırlanır, engine'in kuralı değildir."),
                sc(4, "Hesabın posting'leri bir Query'dir. 6 puan kırıldı: bakiye için toplam yoktur, uygulama bir sayaç tutar; \"dengesi tutmayan entry var mı\" bütün table'ın okunmasını ister."),
                sc(5, "Key'e ay eklenerek veri zamana göre ayrılır. 5 puan kırıldı: partition düşürme ve arşivleme engine'in bir aracı değildir; eski yıl item item taşınır."),
                sc(10, "On-demand mod ay sonunun on katını ayarsız taşır. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır; point-in-time recovery. Puan kırılmadı."),
                sc(6, "Serverless. 4 puan kırıldı: ekip PostgreSQL biliyor; muhasebe modeli key tasarımına yeniden yazılır."),
                sc(8, "İstek başına ödeme. 2 puan kırıldı: transaction'lı yazma iki kat birim tüketir.")],
    },
    h2h={
        "rds": "Aynı engine'in RDS biçimi (RDS for PostgreSQL) ile kafa kafaya. İki aday aynı PostgreSQL engine'ini çalıştırır: dengeli entry trigger'ı, foreign key'ler ve partitioning aynıdır, R1'de ikisi de 45,2 alır. Kararı servis tasarımı verir ve bu kartta ay sonu belirleyicidir. "
               "Aurora Serverless v2 ay sonunda kapasiteyi kendiliğinden artırır ve sonra düşürür; RDS'te instance ya ay sonuna göre boyutlanır ve 28 gün boş durur ya da her ay büyütülüp küçültülür. RDS'in gücü fiyattır: düz bir ayda aynı instance sınıfı daha ucuzdur ve I/O ücreti yoktur. "
               "Dayanıklılıkta ikisi de commit edilmiş veriyi korur; Aurora'nın failover'ı genellikle 30 saniyenin altında, RDS Multi-AZ'ninki bir iki dakikadır. "
               "R5'teki örnek hesapta Serverless v2 ayda yaklaşık 296 USD, ay sonuna göre boyutlanan RDS instance'ı yaklaşık 395 USD'dir; Aurora'yı provisioned db.r6g.xlarge ile çalıştırmak (720 × 0,627 = yaklaşık 451 USD) RDS'in sorununu tekrarlar, bu yüzden kart Serverless v2'yi puanlar. RDS'i her ay büyütüp küçültmek de mümkündür, ama her sınıf değişikliği kısa bir kesintidir. "
               "Hangi koşul değişseydi RDS for PostgreSQL seçilirdi: ay sonu tepesi olmasaydı ve yük yıl boyu düz olsaydı; o zaman fiyat farkı kararı RDS'e verir (kart 5).",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB ay sonu yükünde güçlüdür: on-demand mod on katı ayarsız taşır ve her yazma birkaç AZ'de saklanır; TransactWriteItems 100 posting'e kadar ya hep ya hiç yazar. "
               "Ama defterin kuralları engine'de değildir: toplamı sıfır olmayan bir entry'yi, var olmayan bir hesaba yazılan posting'i ve commit edilmiş bir kaydın değiştirilmesini database engellemez. Bakiye ve \"dengesi tutmayan entry\" soruları toplam ve tarama ister. "
               "PostgreSQL'de bu kurallar bir trigger, foreign key'ler ve izinlerle her programa uygulanır; denetçinin sorusu bir SQL'dir. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: entry'ler tek hesaplı basit olaylar olsaydı (örneğin bir cüzdan bakiyesi ve koşullu düşürme), hacim saniyede on binlere çıksaydı ve denetim ayrı bir analitik kopyadan yapılsaydı.",
    },
    verdict="Karar: Aurora {aur}, RDS {rds}, DynamoDB {ddb}. Engine uyumunda Aurora ve RDS eşittir; kararı R2 ve R5 verir: ay sonunun on katı Serverless v2'nin kendiliğinden ölçeklenmesine uyar. "
            "Aurora PostgreSQL seçtiğimizde artımız: kurallar database'de, kapasite ay sonunu kendisi takip eder, failover genellikle 30 saniyenin altındadır, yedi yıllık partition'lar aynı SQL ile yönetilir. "
            "Eksimiz: ay sonu ACU'su ve Standard'da I/O ödenir; dengeli entry kuralı bir trigger kodudur ve test edilmelidir; maksimum ACU ay sonu yüküyle test edilmelidir. "
            "Bir koşul değişseydi: ay sonu tepesi olmasaydı RDS for PostgreSQL daha ucuz olurdu ve kazanırdı."))

# ------------------------------------------------------------------ 8. appointments: non-overlapping time ranges
AURORA_W.append(wusecase("booking", 8,
    title="Randevu ve rezervasyon: çakışmayan zaman aralıkları",
    key="Table'lar: doctors, appointments (doctor_id, slot tstzrange, patient_id, status, hold_until). Kural: aynı doktorun aralıkları çakışmaz.",
    story=astory("booking"),
    wnote="R1 toplam 48: \"çakışan aralık yok\" kuralı (TA 20) bu iş yükünün kendisidir; boş aralık soruları, aralığın veri tipi ve tutmanın süre sonu da engine'e sorulur. "
          "R3 18 ile en ağır ikinci satır: randevu resmi kayıttır ve kaybı kapıda bekleyen bir hastadır.",
    rows=[
        row("TA", 20, "İki hasta aynı doktora çakışan aralık alırsa biri kapıda bekler; sabah yarışı gerçektir.",
            "\"Bu doktor için bu aralığı sadece çakışan başka aralık yoksa yaz\" tek adımda ve atomik olmalı; aralıklar serbest uzunluktadır (15, 30, 45 dakika).",
            "Kural \"önce oku, sonra yaz\" ile korunursa sabah 08:00'deki yarışta iki hasta aynı saati alır."),
        row("EY", 12, "Hasta ekranı ve klinik raporu bu sorularla çalışır.",
            "\"Bu doktorun yarın boş aralıkları\", \"bu hastanın randevuları\", \"bu kliniğin haftalık doluluğu\" doğrudan sorulabilmeli.",
            "Boş aralıklar uygulamada hesaplanırsa her açılışta doktorun bütün günü okunur ve kod her ekranda tekrarlanır."),
        row("VM", 8, "Verinin kendisi bir zaman aralığıdır; ama şekli basittir.",
            "Randevu başlangıcı ve bitişi olan bir aralıktır; \"çakışır mı\" ve \"içinde mi\" soruları aralığın kendisine sorulabilmeli.",
            "Aralık iki ayrı alan olarak tutulursa her çakışma testi elle yazılmış bir koşuldur ve kenar durumlar (bitiş anı) hata üretir."),
        row("YD", 8, "Onaylanmayan tutmalar 10 dakikada düşmeli; ama tutmanın kaybı ucuzdur.",
            "10 dakikalık tutmanın süresi dolunca aralık yeniden alınabilmeli; ayrı bir temizlik işi istenmez ama kabul edilir.",
            "Süresi dolan tutma aralığı kilitlerse boş saat dolu görünür ve randevu kaybedilir."),
        row("R2", 14, "Sabah bir saat saniyede 50 deneme; gün boyu saniyede 5.",
            _AOLD["booking"]["reqs"][1]["want"][1], _AOLD["booking"]["reqs"][1]["why"][1]),
        row("R3", 18, "Kaybolan randevu kapıda bekleyen hastadır.",
            _AOLD["booking"]["reqs"][2]["want"][1], _AOLD["booking"]["reqs"][2]["why"][1]),
        row("R4", 10, "Dört geliştirici SQL biliyor; sunucu boyutlandırma istenmiyor.",
            "Dört geliştirici, SQL biliyor. Sunucu boyutlandırma ve yama istenmiyor; ikinci bir database türü işletilmek istenmiyor.", "Ayrı bir sistem ayrı bir yedek, izleme ve nöbet demektir; dört kişilik ekipte bu ürün geliştirmeden çalınan zamandır."),
        row("R5", 10, "Trafik sabah tepeli; gece düşük ödeme istenir.",
            _AOLD["booking"]["reqs"][4]["want"][1], _AOLD["booking"]["reqs"][4]["why"][1]),
    ],
    cands=["aur", "ddb", "mdb"],
    scores={
        "aur": [sc(10, "EXCLUDE USING gist (doctor_id WITH =, slot WITH &&) çakışan ikinci aralığı database'in kendisi reddeder (Ö1); btree_gist extension'ı eşitlik ve aralığı aynı kuralda birleştirir (Ö8). Sabah yarışında ikinci istek hata alır. Puan kırılmadı."),
                sc(10, "Boş aralıklar generate_series ve aralık operatörleriyle tek SQL'dir; haftalık doluluk bir GROUP BY'dır (Ö3). Puan kırılmadı."),
                sc(10, "tstzrange bir veri tipidir; && (çakışır) ve @> (içerir) operatörleri GiST index ile çalışır. Puan kırılmadı."),
                sc(7, "PostgreSQL'de TTL yoktur ve exclusion constraint zamanı bilmez: süresi dolmuş bir tutma row'u silinene kadar aralığı kilitler. Çözüm yazmanın içindedir: yeni aralık yazılmadan önce aynı transaction'da süresi dolmuş çakışan tutmalar silinir, ayrı bir iş gerekmez. 3 puan kırıldı: bu DELETE her yazma yolunda unutulmadan yazılmalı ve ekran boş aralıkları hold_until ile hesaplamalıdır."),
                sc(10, "Saniyede 50 deneme tek writer için küçüktür ve Serverless v2 sabah tepesinde ACU'yu artırır. Puan kırılmadı: ACU aralığını seçmek R4'te sayıldı."),
                sc(10, "Üç AZ'de altı kopya (Ö7). Puan kırılmadı."),
                sc(9, "Ekip SQL biliyor; yedek ve failover yönetilir. 1 puan kırıldı: ACU aralığı ve connection pool ekibin işidir."),
                sc(8, "ACU-saat ile ödenir. 2 puan kırıldı: gece de minimum ACU ödenir.")],
        "ddb": [sc(4, "Aralık 15 dakikalık sabit dilimlere bölünür ve her dilim bir item'dır; TransactWriteItems bir randevunun bütün dilimlerini \"attribute_not_exists\" koşuluyla birlikte yazar. 6 puan kırıldı: engine'de aralık çakışması koşulu yoktur; serbest uzunluk dilim modeline zorlanır ve kural uygulamanın dilim hesabına bağlıdır."),
                sc(7, "Partition key doktor, sort key dilim zamanı: doktorun günü tek Query'dir. 3 puan kırıldı: boş aralıkları uygulama hesaplar ve haftalık doluluk için toplam yoktur."),
                sc(5, "Dilimler sayı ya da metin olarak saklanır. 5 puan kırıldı: aralık için bir veri tipi yoktur; \"çakışır mı\" sorusu dilimlere çevrilerek cevaplanır."),
                sc(7, "Süre sonu koşulun içindedir: \"hold_until < :now\" olan dilim yeniden tutulabilir. 3 puan kırıldı: dilim item'ı kalır ve ekran her dilimin hold_until'ini şimdiki zamanla karşılaştırır."),
                sc(10, "On-demand mod sabah tepesini ayarsız taşır. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(7, "Serverless. 3 puan kırıldı: ekip SQL biliyor; dilim modeli ve key tasarımı yeni bir öğrenmedir."),
                sc(9, "İstek başına ödeme. 1 puan kırıldı: transaction'lı yazma iki kat birim tüketir.")],
        "mdb": [sc(6, "Doktorun randevuları başlangıç zamanı skoruyla bir sorted set'tedir; bir Lua script'i komşu aralıkları okur, çakışma yoksa ekler; Valkey script'i sırayla çalıştırır. 4 puan kırıldı: çakışma kuralı uygulamanın yazdığı script'tedir ve script ortada hata verirse geri alınmaz."),
                sc(6, "Doktorun günü ZRANGEBYSCORE ile tek komuttur. 4 puan kırıldı: boş aralıkları ve haftalık doluluğu uygulama hesaplar; sorgu dili yoktur."),
                sc(5, "Aralık bir skor ve bir member'dır. 5 puan kırıldı: aralık için bir veri tipi ve çakışma operatörü yoktur."),
                sc(9, "Tutma ayrı bir key'dir ve EX 600 onu tam 10 dakikada siler. 1 puan kırıldı: tutma ve randevu iki ayrı yapıdadır ve script ikisini birlikte okur."),
                sc(9, "Bellek içi engine sabah tepesini kolayca taşır. 1 puan kırıldı: her yazma çoklu AZ log'una işlendikten sonra onaylanır; shard sayısı önceden seçilir."),
                sc(10, "Her yazma çoklu AZ'li transaction log'unda kalıcıdır. Puan kırılmadı."),
                sc(5, "Yama ve failover yönetilir. 5 puan kırıldı: serverless seçenek yoktur, node'lar boyutlanır ve Valkey komutları bu SQL ekibi için yeni bir API'dir."),
                sc(5, "Node saat başına ödenir. 5 puan kırıldı: sabah bir saati için boyutlanan node'lar ay boyu çalışır.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB R2, R3 ve R5'te güçlüdür: sabah tepesi ayarsız karşılanır, her yazma birkaç AZ'de saklanır ve gece ödeme sıfıra yakındır; tutmanın süre sonu koşulun içinde temiz çalışır. "
               "Ama kartın kalbi \"çakışan aralık yok\" kuralıdır ve DynamoDB'de bir aralık çakışması koşulu yoktur. Serbest uzunluktaki randevular 15 dakikalık dilimlere bölünür ve her randevu birkaç dilimin transaction'ıdır; kural uygulamanın dilim hesabına bağlıdır. "
               "PostgreSQL'de aynı kural tek satırlık bir exclusion constraint'tir ve boş aralıklar tek SQL'dir. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: randevular sabit uzunlukta olsaydı (örneğin her biri 30 dakika, tek item), açılış anında saniyede on binlerce deneme gelseydi ve doluluk raporu ayrı bir analitik kopyadan alınsaydı.",
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. MemoryDB süre sonunda öndedir: tutma 10 dakikada tam anında düşer ve aralık hemen serbesttir; çoklu AZ log'u randevuyu kalıcı tutar. "
               "Ama çakışma kuralı bir Lua script'inde yaşar: sorted set'te komşu aralıklar okunur ve uygulama çakışmayı kendisi test eder. Aralık için bir veri tipi, boş aralıklar ve doluluk için bir sorgu dili yoktur. "
               "Servis tasarımı da geride kalır: serverless seçenek yoktur, sabah bir saati için boyutlanan node'lar ay boyu çalışır ve ekip yeni bir API öğrenir. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: tutmalar saniyede binlerce gelseydi, mikrosaniye cevap istenseydi ve kesin randevu ayrı bir kayıt sistemine yazılsaydı.",
    },
    verdict="Karar: Aurora {aur}, DynamoDB {ddb}, MemoryDB {mdb}. Kararı R1'in atomiklik satırı verir: çakışmayan aralık kuralını PostgreSQL bir exclusion constraint ile kendisi korur. "
            "Aurora PostgreSQL seçtiğimizde artımız: kural database'de ve her programa uygulanır, aralık bir veri tipidir, boş aralıklar ve doluluk tek SQL'dir. "
            "Eksimiz: TTL yoktur; süresi dolan tutmalar yazmadan önce aynı transaction'da silinir ve zamanlanmış bir iş eski row'ları temizler; sabah tepesi için minimum ACU ayarlanır; uygulama exclusion hatasını (SQLSTATE 23P01) yakalar ve hastaya en yakın boş aralıkları önerir. "
            "Bir koşul değişseydi: randevular sabit uzunlukta ve açılış trafiği saniyede on binler olsaydı DynamoDB yarışa girerdi."))

# ------------------------------------------------------------------ 9. workflow state with audit trail
AURORA_W.append(wusecase("workflow", 9,
    title="İş akışı durumu ve denetim izi",
    key="Table'lar: orders (status), order_status_history (from, to, who, when), allowed_transitions.",
    story=astory("workflow"),
    wnote="R1 toplam 56: geçiş ile denetim kaydının birlikte yazılması (TA 20), izin verilmeyen geçişin her programa reddi (ŞE 12) ve takılı sipariş soruları (EY 14) bu iş yükünün kendisidir. "
          "R3 16 ile en ağır ikinci satır: denetim izinin kaybı denetçiye açıklanamaz. Hacim küçük olduğu için R2 8'de kalır.",
    rows=[
        row("TA", 20, "Geçiş yazılıp denetim kaydı yazılmazsa denetçi boşluk bulur; depo, kargo ve destek programlarının hepsi yazar.",
            "\"Durumu sadece picked ise shipped yap ve aynı anda denetim row'u yaz\" tek adımda ve atomik olmalı.",
            "Yarım bir geçiş ya teslim edilmiş bir siparişi kayıtsız bırakır ya da yapılmamış bir geçişi kayıtlı gösterir."),
        row("ŞE", 12, "İzin verilmeyen geçiş teslim edilmiş bir siparişi yeniden ödemeye açar.",
            "İzin verilen geçişler bir table'da tanımlıdır; izin verilmeyen geçiş (picked'tan new'e) database tarafından reddedilmeli.",
            "Kural bir programda eksikse o program yanlış bir geçiş yazar ve sipariş akışı bozulur."),
        row("EY", 14, "Operasyon ekibi takılı siparişleri her saat arar; müşteri hizmetleri her gün geçmişe bakar.",
            "\"İki günden uzun süredir picked'ta takılı siparişler\" (duruma ve süreye göre) ve \"bu siparişin bütün geçmişi\" (zaman sırasıyla) doğrudan sorulabilmeli.",
            "Takılı siparişler bulunamazsa müşteri kargoyu beklerken sipariş bir rafta kalır."),
        row("YD", 10, "Denetim izi beş yıl saklanır ve her yıl büyür.",
            "Her geçiş kalıcı bir geçmiş kaydı bırakmalı; beş yıllık geçmiş sorguları yavaşlatmamalı ve süresi dolan yıllar arşivlenebilmeli.",
            "Geçmiş tek bir büyüyen yapıda durursa beş yılda sorgular ve bakım yavaşlar."),
        row("R2", 8, "Saniyede yarım geçiş, tepe 20; hacim küçüktür.",
            _AOLD["workflow"]["reqs"][1]["want"][1], _AOLD["workflow"]["reqs"][1]["why"][1]),
        row("R3", 16, "Kaybolan denetim kaydı denetçiye açıklanamayan bir boşluktur.",
            _AOLD["workflow"]["reqs"][2]["want"][1], _AOLD["workflow"]["reqs"][2]["why"][1]),
        row("R4", 10, "Üç geliştirici var ve database yöneticisi yok; ama yük küçük ve işletme işi azdır.",
            "Üç geliştirici, SQL biliyor. Sunucu boyutlandırma ve yama istenmiyor; ikinci bir database türü işletilmek istenmiyor; kural kodu sürüm kontrolünde ve migration ile dağıtılmalı.",
            "Ayrı bir sistem ayrı bir yedek, izleme ve nöbet demektir; üç kişilik ekipte bu ürün geliştirmeden çalınan zamandır."),
        row("R5", 10, "Küçük ve düz yük; faturayı kapasitenin alt sınırı belirler.",
            _AOLD["workflow"]["reqs"][4]["want"][1], _AOLD["workflow"]["reqs"][4]["why"][1]),
    ],
    cands=["aur", "rds", "ddb"],
    scores={
        "aur": [sc(10, "Bir trigger (Ö6) UPDATE orders ile aynı transaction'da order_status_history'ye yazar (Ö5); biri olmadan diğeri olmaz. Puan kırılmadı."),
                sc(10, "Aynı trigger geçişi allowed_transitions table'ında arar ve izin verilmeyen geçişi hata ile reddeder; status bir foreign key ile durumlar table'ına bağlıdır (Ö2). Puan kırılmadı."),
                sc(10, "(status, updated_at) üzerinde index ile takılı siparişler, (order_id, at) üzerinde index ile geçmiş tek SQL'dir (Ö3, Ö4). Puan kırılmadı."),
                sc(9, "Denetim table'ı yıla göre partition'lara bölünür; eski yıl tek komutla ayrılır. 1 puan kırıldı: partition bakımı (pg_partman) kurulur ve izlenir."),
                sc(10, "Saniyede 20 geçiş tek writer için çok küçüktür. Puan kırılmadı."),
                sc(10, "Üç AZ'de altı kopya, point-in-time restore. Puan kırılmadı."),
                sc(9, "Ekip SQL biliyor; yedek, yama ve failover yönetilir. 1 puan kırıldı: trigger kodu migration ile dağıtılır ve test edilir; ACU aralığı ekibin seçimidir."),
                sc(8, "ACU-saat ile ödenir. 2 puan kırıldı: minimum ACU küçük yükte de ödenir.")],
        "ddb": [sc(8, "TransactWriteItems siparişi \"status = :picked\" koşuluyla günceller ve denetim item'ını aynı transaction'da ekler. 2 puan kırıldı: iki yazmayı birlikte kurmak her programın görevidir."),
                sc(4, "Koşullu yazma tek bir geçişi korur. 6 puan kırıldı: izin verilen geçişlerin listesi engine'de değildir; her program koşulu kendisi kurar."),
                sc(6, "Seyrek bir ikinci index (status, updated_at) takılı siparişleri, sipariş partition'ı geçmişi verir. 4 puan kırıldı: ikinci index eventually consistent'tır ve her yeni operasyon sorusu yeni bir index tasarımıdır."),
                sc(8, "Denetim item'ları kalıcıdır; Streams her değişikliği 24 saat dışarı verir. 2 puan kırıldı: beş yıllık arşiv için yıllara göre ayırma ve taşıma uygulamanın işidir."),
                sc(10, "On-demand mod bu küçük yükü kolayca taşır. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(7, "Serverless. 3 puan kırıldı: ekip SQL biliyor ve key tasarımı yeni bir öğrenmedir; kuralın her programda olması R1'de sayıldı."),
                sc(10, "İstek başına ödeme; bu küçük yük için maliyet çok düşüktür. Puan kırılmadı.")],
        "rds": [sc(10, "Aynı PostgreSQL engine'i: aynı trigger aynı transaction'da denetim row'unu yazar (Ö5, Ö6). Puan kırılmadı."),
                sc(10, "Aynı trigger izin verilmeyen geçişi reddeder; aynı foreign key (Ö2). Puan kırılmadı."),
                sc(10, "Aynı index'ler ve SQL (Ö3, Ö4). Puan kırılmadı."),
                sc(9, "Aynı partitioning. 1 puan kırıldı: partition bakımı (pg_partman) kurulur ve izlenir."),
                sc(10, "Saniyede 20 geçiş en küçük instance'lar için bile küçüktür. Puan kırılmadı."),
                sc(10, "Multi-AZ senkron standby commit edilmiş denetim kaydını korur; point-in-time restore vardır. Puan kırılmadı."),
                sc(8, "Yönetilen servis; storage auto scaling vardır. 2 puan kırıldı: trigger kodu migration ile dağıtılır; instance sınıfı ve gp3 storage ayarı ekibin seçimidir."),
                sc(9, "Küçük ve düz yükte küçük bir instance saat başına ödenir; I/O ücreti yoktur. 1 puan kırıldı: Multi-AZ standby okuma almaz ama ödenir.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB bu kartta maliyette ve ölçekte öndedir: küçük bir yük için istek başına ödeme çok ucuzdur ve TransactWriteItems geçişi ve denetim item'ını birlikte yazar. "
               "Ama kural engine'de değildir: izin verilen geçişlerin listesini database bilmez, her program koşulu ve iki yazmayı kendisi kurar. Depo, kargo ve destek ayrı programlar olduğu için kural üç yerde yazılır ve biri eski kalır. Takılı siparişler için seyrek bir ikinci index ve beş yıllık arşiv için bir taşıma işi gerekir. "
               "PostgreSQL'de aynı kural bir trigger'dır ve her programa uygulanır. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: siparişlere tek bir servis yazsaydı, geçişler saniyede binlere çıksaydı ya da adımları ve beklemeleri olan iş akışı Step Functions'a verilseydi ve database sadece son durumu tutsaydı.",
        "rds": "Aynı engine'in RDS biçimi (RDS for PostgreSQL) ile kafa kafaya. İki aday aynı PostgreSQL engine'ini çalıştırır: trigger, izin verilen geçişler table'ı, index'ler ve partition'lar aynıdır; R1'de ikisi de 55 alır. "
               "Bu küçük ve düz yükte RDS'in fiyatı gerçek bir avantajdır: küçük bir instance ve I/O ücreti olmayan storage, Aurora'nın minimum ACU'suna yakın ya da daha ucuzdur. Aurora'nın farkı işletmededir: storage ve IOPS ayarı yoktur. Toplamlar eşittir (96 ve 96): Aurora'nın R4'teki 1 puanı RDS'in R5'teki 1 puanını dengeler; tablo Aurora'yı ilk yazar, ama bu kart iki servisi eşit bulur ve iki seçim de savunulabilir. "
               "Kararı çoğu zaman sistemin geri kalanı verir: siparişler zaten bir Aurora cluster'ındaysa iş akışı table'ları oraya eklenir, siparişler RDS'teyse oraya. "
               "Hangi koşul değişseydi RDS for PostgreSQL seçilirdi: siparişler zaten bir RDS instance'ında yaşasaydı ya da database faturası her kuruşuyla izlenen bir kalem olsaydı.",
    },
    verdict="Karar: Aurora {aur}, RDS {rds}, DynamoDB {ddb}. Yakın bir yarış: R1'de Aurora ve RDS eşittir ve ikisi de DynamoDB'nin çok önündedir; geçiş kuralı ve denetim kaydı tek bir trigger'da, her programa aynı uygulanır. Toplamlar eşittir: Aurora'nın işletme kolaylığı (R4) RDS'in fiyatını (R5) dengeler ve karar sistemin geri kalanına bağlıdır. "
            "Aurora PostgreSQL seçtiğimizde artımız: geçiş ve denetim row'u tek transaction'dır, izin verilmeyen geçiş reddedilir, takılı siparişler ve geçmiş tek SQL'dir, beş yıllık geçmiş partition'larda durur. "
            "Eksimiz: trigger kodu migration ile dağıtılır ve test edilir; partition bakımı izlenir; minimum ACU küçük yükte de ödenir. "
            "Bir koşul değişseydi: siparişler zaten bir RDS instance'ında yaşasaydı RDS seçilirdi; iş akışının adımları ve beklemeleri büyüseydi Step Functions iş akışını, Aurora son durumu ve denetim izini tutardı: ikisi birlikte."))

# ------------------------------------------------------------------ 10. geospatial: delivery zones and nearest points (PostGIS)
AURORA_W.append(wusecase("geo", 10,
    title="Coğrafi sorular: teslimat bölgeleri ve en yakın nokta (PostGIS)",
    key="Table'lar: zones (polygon), pickup_points (point), couriers (point, updated_at), orders. GiST index ile.",
    story=astory("geo"),
    wnote="R1 toplam 48: \"bu nokta hangi bölgede\" ve \"en yakın 5 nokta\" soruları (EY 18) bu iş yükünün kendisidir; bölge fiyatı siparişle birlikte yazılmalı (TA 10). "
          "R2 15 ve R4 15 ile ikinci sıradadır: saat 18:00 tepesi sahadaki kuryeyi bekletmemeli ve ekip ayrı bir coğrafi servis işletmek istemiyor.",
    rows=[
        row("EY", 18, "Her siparişin fiyatı ve her kuryenin rotası bu sorularla belirlenir.",
            "\"Bu nokta hangi çokgenin içinde\", \"bu noktaya en yakın 5 nokta\", \"bu çokgendeki açık siparişler ve kuryeler\" ve \"bu rotanın uzunluğu\" doğrudan sorulabilmeli.",
            "Çokgen içi sorusu uygulamada hesaplanırsa 1.200 bölge her istekte okunur; yanlış bölge yanlış fiyattır."),
        row("VM", 10, "Veri noktalar, çokgenler ve çizgilerdir.",
            "Nokta, çokgen ve çizgi (rota) veri tipleri ve koordinat sistemi database'de tanımlı olmalı; geçersiz bir çokgen reddedilmeli.",
            "Koordinatlar iki sayı olarak tutulursa her geometrik işlem uygulamada yazılır ve hatalar sahada görünür."),
        row("DA", 10, "Her soru bir mekânsal index'e dayanır; 1.200 bölge ve 3.000 nokta her istekte taranmamalı.",
            "Mekânsal sorular bir index ile birkaç adımda daraltılmalı; konumu her 10 saniyede değişen 400 kurye index'i yavaşlatmamalı.",
            "Index olmadan her soru bütün bölgeleri ve noktaları okur; tepe saatinde cevaplar 50 ms'yi aşar."),
        row("TA", 10, "Bölge fiyatı siparişle birlikte yazılmalı; ikisi uyuşmazsa fatura yanlıştır.",
            "Sipariş yazılırken bölge bulunmalı ve fiyat siparişle aynı transaction'da kaydedilmeli; sipariş ve kurye ilişkileri korunmalı.",
            "Fiyat siparişten ayrı yazılırsa bir arızada ikisi uyuşmaz ve müşteri yanlış ücret öder."),
        row("R2", 15, "Saniyede 200 coğrafi soru ve 40 konum yazması; 18:00'de iki katı.",
            _AOLD["geo"]["reqs"][1]["want"][1], _AOLD["geo"]["reqs"][1]["why"][1]),
        row("R3", 12, "Sipariş resmi kayıttır; konum geçmişi 30 gün sonra silinebilir.",
            _AOLD["geo"]["reqs"][2]["want"][1], _AOLD["geo"]["reqs"][2]["why"][1]),
        row("R4", 15, "Ekip coğrafi veriye yeni; ayrı bir coğrafi servis ve ayrı bir kopya istenmiyor.",
            "Dört geliştirici, SQL biliyor, coğrafi veri yeni. Coğrafi fonksiyonlar öğrenilebilir olmalı; her ek servis ve her ek veri kopyası bir işletme yüküdür.", "Ayrı bir coğrafi servis, ayrı bir veri kopyası, onu besleyen bir pipeline ve ayrı bir nöbet demektir."),
        row("R5", 10, "Trafik gün içinde dalgalı; veri orta boy.",
            _AOLD["geo"]["reqs"][4]["want"][1], _AOLD["geo"]["reqs"][4]["why"][1]),
    ],
    cands=["aur", "os", "ddb"],
    scores={
        "aur": [sc(10, "PostGIS extension'ı (Ö8): ST_Contains bölgeyi, ORDER BY geom <-> nokta LIMIT 5 en yakın noktaları, ST_Within bölgedeki siparişleri, ST_Length kaydedilmiş bir rota çizgisinin uzunluğunu verir; hepsi SQL'dir (Ö3). Puan kırılmadı: yol ağı üzerinde rota hesaplamak bu kartın sorusu değildir ve bir routing servisinin işidir."),
                sc(10, "geometry tipi nokta, çokgen ve çizgiyi koordinat sistemiyle tutar; ST_IsValid ile bir CHECK geçersiz çokgeni reddeder (Ö1). Puan kırılmadı."),
                sc(9, "GiST index mekânsal soruları birkaç adımda daraltır (Ö4). 1 puan kırıldı: kurye konumunun her güncellemesi MVCC ile yeni bir row sürümü ve yeni bir index entry'si yazar; couriers table'ı VACUUM ile izlenir."),
                sc(10, "Bölge araması ve sipariş yazması tek transaction'dır (Ö5); foreign key'ler siparişi ve kuryeyi bağlar (Ö2). Puan kırılmadı."),
                sc(9, "Saniyede 200 soru ve 40 yazma GiST index'iyle tek writer ve bir reader için küçüktür (Ö7). 1 puan kırıldı: konum geçmişi 30 günde yüz milyon row olur; günlük partition'lara bölünmezse sorgular ve silme yavaşlar."),
                sc(10, "Üç AZ'de altı kopya; sipariş kaybolmaz. Puan kırılmadı."),
                sc(8, "Ayrı bir servis yoktur; ekip SQL biliyor. 2 puan kırıldı: PostGIS fonksiyonları, koordinat sistemleri ve GiST yeni bir öğrenmedir."),
                sc(8, "ACU-saat ile ödenir. 2 puan kırıldı: gece de minimum ACU ödenir ve konum yazmaları Standard'da I/O olarak ödenir.")],
        "os": [sc(6, "geo_shape \"bu çokgende\", geo_distance \"5 km içinde\" sorularını cevaplar ve sonuçlar mesafeye göre sıralanır. 4 puan kırıldı: \"bu nokta hangi bölgede\" bölgeleri document olarak index'leyip ters bir sorgu ister ve rota uzunluğu için bir fonksiyon yoktur (3); bir konum güncellemesi aramada bir refresh aralığı sonra görünür (1)."),
               sc(8, "geo_point ve geo_shape alan tipleri vardır. 2 puan kırıldı: koordinat sistemi dönüşümleri ve geometri doğrulaması PostGIS kadar geniş değildir."),
               sc(10, "Mekânsal alanlar ağaç yapılı index'lerde durur ve filtreler önbelleğe alınır. Puan kırılmadı: refresh gecikmesi R1.1'de bir kez sayıldı."),
               sc(2, "Bir document'ın yazması atomiktir. 8 puan kırıldı: sipariş ve bölge fiyatını birlikte yazan bir transaction yoktur; fiyat siparişten ayrı bir sistemde hesaplanır."),
               sc(9, "Saniyede 200 soru bir domain için küçüktür. 1 puan kırıldı: node sayısı önceden seçilir."),
               sc(9, "Replica shard'lar node arızasını karşılar, otomatik snapshot alınır. 1 puan kırıldı: arama katmanı bir kopyadır; domain kaybolursa 1.200 bölge, 3.000 nokta ve kurye konumları Aurora'dan dakikalar içinde yeniden yüklenir (OpenSearch sayfasının kuralı: dakikalar 1 puan)."),
               sc(5, "Yönetilen domain. 5 puan kırıldı: ayrı bir servis, ayrı bir veri kopyası ve onu besleyen bir pipeline işletilir."),
               sc(6, "Node saat başına ödenir. 4 puan kırıldı: domain sipariş database'ine ek olarak gece de çalışır.")],
        "ddb": [sc(2, "Key ile okuma hızlıdır. 8 puan kırıldı: engine'de coğrafi sorgu yoktur; geohash önekleriyle yakınlık uygulamada hesaplanır ve çokgen içi testi uygulama yapar."),
                sc(3, "Koordinatlar sayı alanlarıdır. 7 puan kırıldı: çokgen ve çizgi için veri tipi yoktur; çokgen bir liste olarak saklanır."),
                sc(2, "Partition'lar hash ile dağılır. 8 puan kırıldı: mekânsal bir index yoktur; komşuluk hash'te kaybolur."),
                sc(8, "Sipariş ve fiyat tek item'da ya da bir transaction'da yazılır. 2 puan kırıldı: bölgeyi bulan hesap database'in dışında yapılır."),
                sc(10, "On-demand mod tepeyi ayarsız taşır. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(6, "Serverless. 4 puan kırıldı: coğrafi hesaplar uygulamada ayrı bir kütüphane olarak yazılır ve bakılır."),
                sc(9, "İstek başına ödeme. 1 puan kırıldı: geohash sorguları birkaç komşu hücreyi okur ve birim tüketir.")],
    },
    h2h={
        "os": "Search engine (OpenSearch) ile kafa kafaya. OpenSearch coğrafi aramada güçlüdür: geo_distance ve geo_shape sorguları hızlıdır, sonuçlar mesafeye göre sıralanır ve metinle birlikte aranabilir (\"5 km içinde açık eczaneler\"). "
              "Ama bu kartta fiyat siparişle aynı transaction'da yazılmalıdır ve OpenSearch'te transaction yoktur; siparişler orada resmi kayıt olamaz. \"Bu nokta hangi bölgede\" ters bir sorgu ister ve rota uzunluğu için fonksiyon yoktur. "
              "Servis tasarımı da geride kalır: ayrı bir domain, ayrı bir kopya ve bir pipeline gerekir. PostGIS aynı soruları siparişin yanında, aynı SQL ve aynı transaction ile cevaplar. "
              "Hangi koşul değişseydi OpenSearch seçilirdi: iş bir keşif ekranı olsaydı (\"yakınımdaki mağazalar\", metinle birlikte), sipariş yazmasıyla bağı olmasaydı ve relevance sıralaması istenseydi; o zaman ikisi birlikte çalışır.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB ölçekte ve operasyonda güçlüdür: 18:00 tepesi ayarsız karşılanır ve kurye konum yazmaları partition'lara dağılır. "
               "Ama engine'de coğrafi bir sorgu, veri tipi ve mekânsal index yoktur: yakınlık geohash önekleriyle uygulamada hesaplanır, çokgen içi testi uygulama kodudur ve hash ile dağılan partition'lar komşuluğu bilmez. R1'in dört alt maddesinin üçünde puan çok düşüktür. "
               "PostGIS bu soruların hepsini fonksiyon ve GiST index ile verir. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: sadece kuryenin son konumu key ile okunup yazılsaydı (coğrafi soru yok), konum yazmaları saniyede on binlere çıksaydı ve coğrafi sorular başka bir servise verilseydi.",
    },
    verdict="Karar: Aurora {aur}, OpenSearch {os}, DynamoDB {ddb}. Kararı R1'in erişim yolu ve atomiklik satırları verir: PostGIS bütün coğrafi soruları SQL ile cevaplar ve fiyat siparişle aynı transaction'da yazılır. "
            "Aurora PostgreSQL seçtiğimizde artımız: coğrafi sorular, siparişler ve kuryeler tek database'te, tek SQL'de ve tek transaction'dadır; ayrı bir servis ve kopya yoktur. "
            "Eksimiz: ekip PostGIS'i öğrenir; sık güncellenen konum row'ları VACUUM ile izlenir; konum geçmişi günlük partition'lara bölünür ve 30 günden eski partition düşürülür. "
            "Amazon Location Service bu kartta database adayı değildir: verileri saklayan ve SQL ile sorulan bir database değil, harita, adres arama, geofence ve yol ağı üzerinde rota hesabı veren bir servistir. Yol üstündeki mesafe ve süre (ST_Length'in vermediği şey) gerekirse ikisi birlikte çalışır: rota Location Service'ten hesaplanır, sonuç siparişle birlikte Aurora'ya yazılır. "
            "Bir koşul değişseydi: iş metinle birlikte bir keşif araması olsaydı OpenSearch öne geçerdi."))

USECASES_W["aurora"] = AURORA_W
PAGE_SVC["aurora"] = "aur"


# ====================================================================== Amazon DocumentDB (page id "docdb"), Turkish, model 2
# The ten workloads of the model 1 DocumentDB page (e2e_usecases.DOCDB_USECASES), rebuilt: R1 in sub-items from R1_CATALOG,
# weights from the story, the best fit first. The model 1 data stays for the untouched English docdb.html.
# Twin services of one engine: DocumentDB instance-based cluster ("doc") and DocumentDB elastic cluster ("doce") get the same
# R1 points; what the elastic cluster does not offer (transactions, change streams, point-in-time restore) is service
# packaging and goes to R2-R5.
# Sources of the limits and numbers in the reasons below (the hedges are the hedges of the source):
#  - cluster volume "six ways across three Availability Zones", one primary and up to 15 replicas, writes to a reader fail,
#    replica lag "usually less than 100 milliseconds", TTL deletes "best effort", "each deletion incurs IO costs", time-bucketed
#    collections dropped "without incurring IO costs": https://docs.aws.amazon.com/documentdb/latest/developerguide/how-it-works.html
#  - failover "up to 30 seconds of downtime for your cluster, but often less time than that":
#    https://docs.aws.amazon.com/whitepapers/latest/get-started-documentdb/amazon-documentdb-architecture.html
#  - 16 MiB document, nesting 200 levels, 64 indexes per collection: https://docs.aws.amazon.com/documentdb/latest/developerguide/limits.html
#  - transactions 4.0 and later, "one minute execution limit": https://docs.aws.amazon.com/documentdb/latest/developerguide/transactions.html
#  - change streams, retention "between 1 hour and 7 days", default three hours:
#    https://docs.aws.amazon.com/documentdb/latest/developerguide/change_streams.html
#  - elastic clusters: hash sharding, up to 32 shards, each shard one writer and 0-15 replicas; not supported: ACID transactions,
#    change streams, point-in-time restore, unique, partial, text and vector indexes, multi-field shard key, change shard key:
#    https://docs.aws.amazon.com/documentdb/latest/devguide/elastic-how-it-works.html,
#    https://docs.aws.amazon.com/documentdb/latest/devguide/docdb-using-elastic-clusters.html
#  - pricing: instance hours, I/O per million (Standard) or no I/O charge (I/O-Optimized), elastic clusters per vCPU-hour of every
#    shard instance (US East example 0.132 USD per vCPU-hour), serverless 0.5-256 DCUs: https://aws.amazon.com/documentdb/pricing/
#  - "TTL and change streams incur I/O's when data is written, read, and deleted":
#    https://docs.aws.amazon.com/documentdb/latest/devguide/best_practices.html
#  - DynamoDB: item 400 KB, TTL deletes "within a few days", Streams 24 hours, on-demand "up to double your previous peak":
#    https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html,
#    https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/on-demand-capacity-mode.html
#  - OpenSearch refresh interval 1 second by default, dynamic mapping, field type fixed until a reindex:
#    https://docs.aws.amazon.com/opensearch-service/latest/developerguide/bp.html
#  - ElastiCache Serverless replicates across Availability Zones; Valkey EXPIRE: https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/WhatIs.html
from .e2e_usecases import DOCDB_USECASES as _DM1  # noqa: E402

CATEGORY.setdefault("doce", ("sharded document", "shard'lı document"))
LINK.setdefault("doce", "docdb")          # the elastic cluster is the second form of DocumentDB, taught on this page (C2)

_DOLD = {uc["id"]: uc for uc in _DM1}


def dstory(uid):
    return _DOLD[uid]["story"][1]


def _dstrip(t):
    t = re.sub(r"\s*Bu kartta dayanıklılık zorunludur\.", "", t)
    return t.replace(", zorunluluk değildir", "")


def drest(uid, i, w, wwhy):
    """An R2-R5 row with the 'what we need' and 'why it matters' texts of model 1 (i = 2..5) and a new weight with its reason."""
    r = _DOLD[uid]["reqs"][i - 1]
    return row(f"R{i}", w, wwhy, _dstrip(r["want"][1]), _dstrip(r["why"][1]))


DOCDB_W = []

# ------------------------------------------------------------------ 1. product catalog with variable attributes (DocumentDB wins on its engine)
DOCDB_W.append(wusecase("catalog", 1, sim="w_catalog",
    title="Değişken özellikli ürün kataloğu (Lale Market)",
    key="Collection: products. Document: _id, name, category, price, attributes (iç içe), tags (array).",
    story=dstory("catalog"),
    wnote="R1 toplam 55: ürünün şekli (VM 14), her ay gelen yeni özellik (ŞE 12) ve iç içe field'lara göre filtreler (EY 15) bu kataloğun günlük işidir. "
          "R2 15 ile ikinci: vitrin saniyede 2.000, kampanyada 10.000 okuma alır. Katalog bir günde yeniden kurulabildiği için R3 8'de kalır.",
    rows=[
        row("VM", 14, "Ürün sayfası ürünü bütün özellikleri ve etiketleriyle tek seferde ister; vitrin bu okumayla açılır.",
            "Bir ürün, türüne göre değişen özellikleri (kulaklıkta renk ve garanti ayı, kitapta sayfa ve dil) ve etiket listesiyle tek bir bütün olarak okunmalı ve yazılmalı.",
            "Ürün birkaç yerden toplanırsa her ürün sayfası birkaç okuma ve bir birleştirmedir; bir satıcı ürünü güncellerken yarım bir hâl görünebilir."),
        row("ŞE", 12, "Pazarlama her ay yeni bir özellik ekler; bu iş database ekibini beklememeli.",
            "\"Su geçirmez\" ya da \"enerji sınıfı\" gibi yeni bir özellik sadece yeni ürünlere yazılabilmeli; eski ürünler değişmeden kalmalı ve bir bakım penceresi gerekmemeli.",
            "Her yeni özellik bir schema değişikliğiyse pazarlamanın takvimi database ekibinin takvimine bağlanır."),
        row("EY", 15, "Kategori sayfası mağazanın en çok açılan sayfasıdır; filtreler vitrinin kendisidir.",
            "\"Elektronik ve siyah, rating'e göre\" ve \"garanti_ay >= 24 ve rating >= 4,5\" gibi iç içe field'lara göre filtreler ve \"bu id'nin ürünü\" yeniden tasarım istemeden çalışmalı.",
            "Bir filtre için yeni bir veri tasarımı gerekirse her kampanya filtresi bir database projesidir; filtre bütün kataloğu okursa sayfa yavaşlar."),
        row("OY", 6, "Yazma azdır (saniyede 20) ama iki satıcı aynı ürünü aynı anda değiştirebilir.",
            "Bir ürünün tek bir özelliğini (fiyat, stok, garanti ayı) değiştirmek ürünün tamamını yeniden yazmamalı.",
            "Ürünün tamamını yeniden yazan bir güncelleme, aynı anda başka bir satıcının yaptığı değişikliği ezer."),
        row("AO", 8, "Filtreler hızlı olmalı; hızı engine'in index araçları verir.",
            "İç içe field'lara, array elemanlarına ve \"önce kategori, sonra rating\" sırasına index kurulabilmeli; plan okunabilmeli.",
            "Index'siz bir filtre 200.000 ürünün hepsini okur; kampanya gününde sayfa saniyeler sürer."),
        drest("catalog", 2, 15, "Vitrin saniyede 2.000, kampanyada 10.000 okuma alır ve katalog yılda iki katına çıkar."),
        drest("catalog", 3, 8, "Katalog satıcı beslemelerinden bir günde yeniden kurulur; kayıp para değil bir günlük boş vitrindir."),
        drest("catalog", 4, 12, "Dört geliştirici sunucu istemiyor; ikisi MongoDB API'sini biliyor."),
        drest("catalog", 5, 10, "Veri birkaç GB ve trafik okuma ağırlıklı; fatura kararı tek başına çevirmez."),
    ],
    cands=["doc", "aur", "os"],
    scores={
        "doc": [sc(10, "Ürün tek bir document'tır: attributes bir embedded document, tags bir array; _id ile tek okumada bütün ürün gelir (Ö1, Ö2). Puan kırılmadı."),
                sc(10, "Her document kendi field'larını taşır; yeni özellik sadece yeni document'lara yazılır, eski document'lar değişmez (Ö2). Puan kırılmadı."),
                sc(10, "\"Elektronik ve siyah\" dot notation ile bir filtredir (Ö3); \"garanti_ay >= 24\" aynı biçimde bir aralıktır. Yeni filtre yeni bir tasarım değil, bir find'dır. Puan kırılmadı."),
                sc(10, "updateOne ile $set tek field'ı değiştirir; diğer field'lar dokunulmadan kalır ve yazma tek document'ta atomiktir (Ö5). Puan kırılmadı."),
                sc(9, "Compound, multikey ve embedded field index'leri (Ö4) filtreleri IXSCAN yapar; canlı planda 40 document okundu, 40 döndü (B2). 1 puan kırıldı: compound index'te field sırası soruya uymalıdır; her yeni sık filtre için bir index kurulur."),
                sc(9, "Okumalar en fazla 15 replica'ya dağılır (Ö8); saniyede 20 yazma primary için küçüktür. 1 puan kırıldı: kampanya önceden bilinir, ama beklenmeyen bir tepe yeni bir replica'nın eklenmesini dakikalarca bekler."),
                sc(10, "Cluster volume üç AZ'de altı kopya tutar; sürekli yedek vardır. Puan kırılmadı."),
                sc(8, "Yedek, yama ve failover yönetilir; ekibin ikisi MongoDB API'sini biliyor. 2 puan kırıldı: instance sınıfını ve kampanya replica'larını ekip seçer ve diğer iki geliştirici API'yi yeni öğrenir."),
                sc(8, "Instance saat başına ve I/O başına ödenir (Standard). 2 puan kırıldı: Multi-AZ için en az iki instance sürekli çalışır ve kampanya replica'ları ayrıca ödenir; bu yükte iki instance boş durmaz, bu yüzden kırılım küçük kartlardakinden azdır.")],
        "aur": [sc(7, "Sabit field'lar column, değişken özellikler bir JSONB column'unda durur; ürün tek row'da okunur. 3 puan kırıldı: ürün iki biçime bölünür; type'lı column'lar ve şemasız JSON yan yana yaşar ve uygulama hangisinin nerede olduğunu bilir."),
                sc(8, "JSONB'nin içi serbesttir; yeni özellik migration istemez. 2 puan kırıldı: özellik bir gün column'a taşınacaksa ya da type'ı korunacaksa bu bir migration'dır."),
                sc(9, "SQL her column'da ve JSONB'nin içinde sorar (attributes->>'renk'). 1 puan kırıldı: iç içe field'a göre aralık (garanti_ay >= 24) bir cast ve JSON yolu ister."),
                sc(7, "jsonb_set tek özelliği değiştirir. 3 puan kırıldı: PostgreSQL her UPDATE'te row'un yeni bir sürümünü yazar (MVCC); tek özellik için bütün row ve JSONB değeri yeniden yazılır."),
                sc(7, "GIN index JSONB'deki eşitlik sorularını hızlandırır; expression index tek bir yolu index'ler. 3 puan kırıldı: GIN sıralama ve aralık vermez; aralık ve sıralama isteyen her iç içe field için ayrı bir expression index kurulur."),
                sc(9, "Reader instance'lar okumayı paylaşır. 1 puan kırıldı: beklenmeyen bir tepe yeni reader'ın eklenmesini dakikalarca bekler."),
                sc(10, "Üç AZ'de altı kopya; point-in-time restore. Puan kırılmadı."),
                sc(8, "Aurora Lale Market'te siparişler için zaten çalışır. 2 puan kırıldı: kataloğu oraya taşımak sabit column'lar için migration disiplini ve vitrin okumaları için reader instance'ları ister; ekibin MongoDB bilen ikisi SQL'e geçer."),
                sc(8, "Var olan cluster'a eklenir. 2 puan kırıldı: vitrinin 2.000 okuması için reader instance'ları ve ACU'lar ödenir.")],
        "os": [sc(8, "Ürün bir JSON document'ıdır; iç içe nesneler ve listeler saklanır. 2 puan kırıldı: bir listedeki nesnelerin field'larını birlikte sormak için nested mapping tanımlanır."),
               sc(8, "Dynamic mapping yeni field'ı kendisi tanır. 2 puan kırıldı: bir field'ın type'ı ilk yazmada sabitlenir; yanlış tahmin edilen bir type reindex ister (OpenSearch sayfasının kademesi: yalnız yeni alan gelirse 2, var olan alanların type'ı ya da analizi değişirse 4 puan; bu hikâyede yalnız yeni özellik gelir)."),
               sc(9, "Filtreler, aralıklar ve sıralama bir sorgudur; facet sayıları da aynı sorguda gelir. 1 puan kırıldı: \"bu id'nin ürünü\" kayıt sistemi okuması değildir; yeni yazma refresh aralığından sonra görünür (varsayılan 1 saniye)."),
               sc(7, "Tek field değiştiren bir update isteği vardır. 3 puan kırıldı: engine document'ı içeride baştan yazar ve bütün field'larını yeniden index'ler; saniyede 20 güncelleme orta bir merge yüküdür (OpenSearch sayfasının kademesi: saniyede birkaç güncelleme 1, onlarca 3, yüzlerce 6 puan). Aynı ürüne yarışan iki satıcı için sürüm koşulu (if_seq_no) uygulamanın işidir."),
               sc(9, "Her field kendiliğinden index'lenir; doc values sıralamayı ve facet'i verir. 1 puan kırıldı: mapping ve analyzer bir kez tasarlanır; shard sayısı R4'te sayıldı."),
               sc(9, "Shard'lar ve replica'lar okumayı paylaşır. 1 puan kırıldı: kampanya için node'lar önceden eklenir; yeni node'un shard'ları alması zaman ister."),
               sc(8, "Shard replica'ları başka AZ'dedir; saatlik otomatik snapshot alınır. 2 puan kırıldı: point-in-time restore yoktur; domain kaybolursa katalog satıcı beslemelerinden bir günde yeniden yüklenir (OpenSearch sayfasının kuralı: yeniden yükleme bir saat ve üstü sürerse 2 puan)."),
               sc(5, "Yönetilen domain. 5 puan kırıldı: ekip OpenSearch bilmiyor; mapping, shard boyutu ve node sınıfı ekibin yeni işidir."),
               sc(6, "Node'lar saat başına ödenir. 4 puan kırıldı: kataloğun kayıt sistemi olarak bütün gün çalışan bir domain ve kalıcılık için ek replica'lar.")],
    },
    h2h={
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Fark R1'in veri modeli, okuma/yazma şekli ve index araçları satırlarındadır; R2 ve R3'te iki aday eşittir. Aurora güçlü bir adaydır: JSONB değişken özellikleri migration'sız saklar, SQL her column'da ve JSON'un içinde sorar ve Lale Market'te Aurora zaten siparişler için çalışır. "
               "Ama ürün iki biçime bölünür: sabit field'lar column'larda, değişken olanlar JSON'da. Tek bir özelliği değiştirmek MVCC yüzünden bütün row'un yeni bir sürümüdür ve iç içe bir field'a göre aralık ya da sıralama her field için ayrı bir expression index ister. DocumentDB'de aynı ürün tek bir document'tır ve iç içe her field'a doğrudan index kurulur. "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: ürünler sipariş ve stokla aynı transaction'da değişseydi, özellikler az ve sabit olsaydı ve ekip sadece SQL bilseydi (Aurora sayfasının kart 2'si tam bu koşullarla Aurora'yı öne koyar).",
        "os": "Search engine (OpenSearch) ile kafa kafaya. OpenSearch filtrelerde ve facet'lerde çok güçlüdür ve bu kartın erişim yolu satırında DocumentDB'ye çok yakındır. Ama bu kart kataloğun kendisini, yani kayıt sistemini soruyor: bir ürünün tek özelliğini güvenle değiştirmek, iki satıcının yazmasını ayırmak ve type'ı değişen bir field için index'i baştan kurmadan yaşamak. "
              "OpenSearch'te bir update document'ı içeride baştan yazar, yeni değer refresh aralığından sonra görünür ve type'ı ilk yazmada sabitlenen bir field değişirse reindex gerekir. R3'te de geride kalır: kayıt sistemi değil, bir kopya için tasarlanmıştır. Ekip OpenSearch bilmiyor ve yeni bir domain işletmek istemiyor. "
              "Hangi koşul değişseydi OpenSearch seçilirdi: kayıt sistemi başka yerde olsaydı ve iş yazım hatası toleranslı, relevance sıralı arama olsaydı. O gün doğru cevap ikisi birlikte çalışmaktır: katalog DocumentDB'de kalır, arama kopyası change stream ile OpenSearch'e akar (kart 8).",
    },
    verdict="Karar: DocumentDB {doc}, Aurora PostgreSQL {aur}, OpenSearch {os}. Kararı R1 verir: ürünün iç içe şekli, aylık yeni özellikler ve iç içe field'lara göre filtreler document engine'inin tanımıdır; R1'in 55 puanının 54,2'sini DocumentDB alır. "
            "DocumentDB seçtiğimizde artımız: ürün tek okumadır, yeni özellik migration istemez, her iç içe field bir filtre ve bir index olabilir, okuma replica'larla büyür. "
            "Eksimiz: database field adlarını ve type'larını doğrulamaz, bu yüzden yazmaları tek bir veri katmanından geçiririz ya da collection'a bir $jsonSchema kuralı ekleriz; her yeni sık filtre bir index'tir ve explain ile kontrol edilir; instance sınıfını ve kampanya replica'larını ekip seçer. "
            "Aynı engine'in shard'lı biçimi (elastic cluster) bu kartta aday değildir: R1'i aynıdır ve saniyede 20 yazma tek primary için küçüktür, shard'lamanın kazanacağı bir şey yoktur. "
            "Bir koşul değişseydi: yazım hatası toleranslı arama istenseydi OpenSearch kataloğun yanına bir arama kopyası olarak eklenirdi; ikisi birlikte çalışır."))

# ------------------------------------------------------------------ 2. user profiles with nested preferences (close race with DynamoDB)
DOCDB_W.append(wusecase("profiles", 2, sim="w_profiles",
    title="İç içe tercihleri olan kullanıcı profilleri",
    key="Collection: users. Document: _id, name, locale, addresses (array), prefs (iç içe), devices (array).",
    story=dstory("profiles"),
    wnote="R1 toplam 38: profilin array içi güncellemesi (OY 12) ve id ile okuma ile pazarlamanın soruları (EY 12) engine'e sorulur. "
          "R2 24 ile ikinci: saniyede 12.000 okuma ve yılda yüzde 50 büyüme. R4 16: uygulama zaten MongoDB driver'ı ile yazılmış.",
    rows=[
        row("EY", 12, "Her ekran profil okumasıyla başlar; pazarlamanın soruları haftada birkaç kez gelir.",
            "\"Bu kullanıcı id'sinin profili\" tek okuma olmalı. \"İstanbul'da oturan ve podcast önerisi isteyen\" ve \"iOS cihazı olup bildirimi kapalı olanlar\" gibi, profilin içine göre ve haftada değişen sorular yeni bir tasarım istemeden cevaplanmalı.",
            "Profil okuması yavaşsa her ekran yavaştır. Pazarlamanın her yeni sorusu bir veri projesine dönüşürse kampanya takvimi kayar."),
        row("OY", 12, "Kullanıcı birkaç cihazdan aynı profili değiştirir; değişiklik array'in içindedir.",
            "\"label'ı iş olan adres\" array'deki sırası bilinmeden, tek yazmada ve profilin geri kalanına dokunmadan değişmeli.",
            "Array içi değişiklik için profilin tamamı okunup yeniden yazılırsa başka bir cihazdan aynı anda gelen değişiklik ezilir."),
        row("VM", 8, "Profil iç içe tercihler ve iki liste taşıyan tek bir nesnedir.",
            "Ad, dil, adres listesi, bildirim tercihleri ve cihaz listesi tek bir bütün olarak saklanmalı; profil 10 KB'tan küçüktür.",
            "Profil birkaç yere bölünürse her ekran birkaç okumadır."),
        row("ŞE", 6, "Yeni tercih alanları gelir ama yavaş; ağırlık bu yüzden düşük.",
            "Yeni bir tercih alanı sadece yeni profillere yazılabilmeli.",
            "Her yeni alan bir migration ise küçük bir özellik bir bakım penceresi bekler."),
        drest("profiles", 2, 24, "Saniyede 12.000 okuma, sabah ve akşam tepe, yılda yüzde 50 büyüme: ölçek bu kartın ikinci sorusudur."),
        drest("profiles", 3, 8, "Profil kaybı güven ve destek kaybıdır, para kaybı değildir."),
        drest("profiles", 4, 16, "Uygulamanın veri katmanı zaten MongoDB driver'ı ile yazılmış; beş geliştirici sunucu istemiyor."),
        drest("profiles", 5, 14, "İki tepe arasında trafik düşer; boş kapasite ödemek istenmez."),
    ],
    cands=["doc", "ddb", "aur"],
    scores={
        "doc": [sc(9, "find({ _id }) tek okumadır (Ö1); \"İstanbul'da oturan ve podcast isteyen\" dot notation ile bir filtredir (Ö3) ve addresses.city ile prefs.podcast üzerine index kurulur (Ö4). 1 puan kırıldı: index'i olmayan yeni bir soru üç milyon profilde bir COLLSCAN'dir; index kurulana kadar replica'ya yönlendirilir."),
                sc(10, "updateOne ile $set ve arrayFilters adresi sırasını bilmeden, label değeriyle bulur ve sadece onu değiştirir (Ö5). Puan kırılmadı."),
                sc(10, "Profil iç içe tercihleri ve iki array'iyle tek document'tır (Ö2). Puan kırılmadı."),
                sc(10, "Yeni alan sadece yeni document'lara yazılır (Ö2). Puan kırılmadı."),
                sc(8, "Okumalar en fazla 15 replica'ya dağılır (Ö8); saniyede 150 yazma primary için küçüktür. 2 puan kırıldı: okuma replica'larla büyür ve her replica bir instance'tır; beklenmeyen bir tepe yeni replica'nın eklenmesini dakikalarca bekler."),
                sc(10, "Cluster volume üç AZ'de altı kopya tutar; sürekli yedek vardır. Puan kırılmadı."),
                sc(9, "Kod zaten MongoDB driver'ı ile yazılmış; yedek, yama ve failover yönetilir. 1 puan kırıldı: instance sınıfını ve replica sayısını ekip seçer."),
                sc(7, "Instance saat başına ödenir. 3 puan kırıldı: tepeye göre boyutlanan replica'lar iki tepe arasındaki düşük trafikte de çalışır; I/O ayrıca ödenir (Standard).")],
        "ddb": [sc(6, "Profil id ile GetItem'dır. 4 puan kırıldı: pazarlamanın soruları listelerin içine göredir (addresses içindeki şehir, devices içindeki işletim sistemi) ve list elemanına index kurulamaz; her soru ya ayrı tutulan bir kopya ya da Scan ve dışa aktarmadır (kart 3, 5 ve 7'deki aynı mekanizma)."),
                sc(6, "UpdateItem bir map field'ını yerinde değiştirir. 4 puan kırıldı: bir listenin elemanı değeriyle değil sırasıyla (addresses[1]) güncellenir; uygulama önce okur, sırayı bulur ve araya giren yazmaya karşı bir koşul ekler."),
                sc(10, "Map ve list tipleri profili tek value olarak saklar; 10 KB 400 KB sınırının çok altındadır. Puan kırılmadı."),
                sc(10, "Key dışındaki alanlar serbesttir. Puan kırılmadı."),
                sc(10, "On-demand mod 12.000 okumayı ve büyümeyi kapasite planı olmadan karşılar. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır; point-in-time recovery vardır. Puan kırılmadı."),
                sc(6, "Serverless: sunucu, yama, failover yoktur. 4 puan kırıldı: uygulamanın MongoDB driver'ı ile yazılmış veri katmanı yeni bir API ile yeniden yazılır."),
                sc(9, "İstek başına ödeme iki tepe arasındaki düşük trafiği takip eder. 1 puan kırıldı: okunan her 4 KB bir birimdir; profil okuması çok sık olduğu için en büyük kalem budur.")],
        "aur": [sc(9, "SQL her column'da ve JSONB'nin içinde sorar; id ile okuma primary key'dir. 1 puan kırıldı: JSONB'nin içine göre sorular için yol ifadeleri ve GIN index gerekir."),
                sc(6, "Adresler ayrı bir table'da olursa tek adres tek UPDATE'tir. 4 puan kırıldı: profil bu durumda üç table'a bölünür; JSONB'de kalırsa array elemanı sırasıyla güncellenir ve MVCC bütün row'u yeniden yazar."),
                sc(7, "Profil sabit column'lar ve JSONB ile tek row olabilir. 3 puan kırıldı: listeler ya ayrı table'lardır ya JSON'un içindedir; iki biçim yan yana yaşar."),
                sc(8, "JSONB yeni tercih alanını migration'sız alır. 2 puan kırıldı: sabit column'a dönen alan bir migration'dır."),
                sc(8, "Reader instance'lar okumayı paylaşır. 2 puan kırıldı: okuma reader'larla büyür; beklenmeyen bir tepe yeni reader'ı dakikalarca bekler."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(4, "Yedek ve yama yönetilir. 6 puan kırıldı: MongoDB driver'ı ile yazılmış veri katmanı SQL'e taşınır, yeni bir cluster işletilir ve ACU aralığını ekip seçer."),
                sc(8, "Serverless v2 düşük trafikte küçülür. 2 puan kırıldı: minimum ACU boşta da ödenir.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. Bu, okuyucunun en çok \"neden o değil?\" dediği karşılaştırmadır. DynamoDB sayfasında da bir profil kartı vardır ve orada DynamoDB kazanır; ama o kart farklı bir iş yüküdür (profilin içine göre soru ve array içi güncelleme yoktur, ekip MongoDB driver'ı kullanmaz). Fark R1'in okuma/yazma şekli ve erişim yolu satırlarında ve R4'tedir; R2 ve R5'te DynamoDB öndedir. "
               "DynamoDB'nin gücü ölçektir: on-demand mod 12.000 okumayı ve yılda yüzde 50 büyümeyi kapasite planı olmadan karşılar ve okuma başına ödeme iki tepe arasındaki boşluğu takip eder. "
               "Ama bir listedeki adres değeriyle değil sırasıyla güncellenir, pazarlamanın profilin içine göre soruları ya her soruya bir ikinci index ya da bir Scan ister ve bu uygulamanın veri katmanı zaten MongoDB driver'ı ile yazılmıştır. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: uygulama sıfırdan yazılsaydı, pazarlamanın soruları bir analitik kopyaya gitseydi ve okuma saniyede 100.000'e çıksaydı; DynamoDB sayfasının profil kartı bu koşullara yakındır.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora'nın gücü sorulardadır: SQL pazarlamanın her sorusunu, JSONB'nin içi dahil, yeni bir tasarım olmadan cevaplar ve reader instance'lar okumayı paylaşır. "
               "Ama profil Aurora'da ya üç table'a bölünür ya da listeler JSONB'nin içinde kalır; ikinci durumda bir adres sırasıyla güncellenir ve MVCC her değişiklikte bütün row'u yeniden yazar. R1'in dört satırının üçünde DocumentDB öndedir. "
               "R4'te fark büyüktür: MongoDB driver'ı ile yazılmış veri katmanı SQL'e taşınır ve ekip yeni bir cluster işletir. "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: profil siparişler ve ödemelerle aynı transaction'da değişseydi ve uygulama SQL ile yazılmış olsaydı.",
    },
    verdict="Karar: DocumentDB {doc}, DynamoDB {ddb}, Aurora PostgreSQL {aur}. Kararı R1'in array içi güncelleme ve erişim yolu satırları ile R4 verir; R2 ve R5'te DynamoDB öndedir. "
            "DocumentDB seçtiğimizde artımız: profil tek document'tır, adres arrayFilters ile değeriyle güncellenir, pazarlamanın soruları filtre ve index'tir ve veri katmanı değişmez. "
            "Eksimiz: okuma ölçeği replica'larla ve instance sınıfıyla gelir, bu yüzden tepe günlerinden önce replica'yı biz ekleriz; yeni bir pazarlama sorusu index kurulana kadar replica'ya yönlendirilir; iki tepe arasında boşta kapasite öderiz. "
            "Aynı engine'in shard'lı biçimi (elastic cluster) bu kartta aday değildir: saniyede 150 yazma tek primary için küçüktür ve okuma zaten replica'larla büyür. "
            "Bir koşul değişseydi: okuma saniyede 100.000'e çıksaydı ve uygulama sıfırdan yazılsaydı DynamoDB öne geçerdi."))

# ------------------------------------------------------------------ 3. content management: articles and blocks
DOCDB_W.append(wusecase("cms", 3,
    title="İçerik yönetimi: makale ve blokları",
    key="Collection: articles. Document: _id, title, slug, status, authors (array), blocks (array: paragraf, görsel, alıntı), tags (array).",
    story=dstory("cms"),
    wnote="R1 toplam 46: makalenin sıralı ve türü farklı blokları (VM 14), tek bloğun değişmesi (OY 12) ve üç liste sorusu (EY 12) bir document engine'inin işidir. "
          "R3 20 ile ikinci: yayımlanmış makale kaybolamaz ve yanlış bir silme geri alınabilmeli.",
    rows=[
        row("VM", 14, "Makale sayfası makaleyi bütün bloklarıyla tek seferde ister; editör blokları sürükleyip sıralar.",
            "Bir makale sıralı bloklardan oluşur ve her blok türünün field'ları farklıdır (paragraf metni, görselin S3 key'i, alıntının kaynağı). Makale tek bir bütün olarak okunmalı.",
            "Bloklar ayrı kayıtlarda durursa her makale sayfası birçok okuma ve bir sıralamadır; sıra bilgisi kopabilir."),
        row("OY", 12, "Editör bir bloğu düzenlediğinde iki editör aynı makalede çalışıyor olabilir.",
            "Tek bir blok, array'deki sırası ne olursa olsun, tek yazmada değişmeli; makalenin geri kalanına dokunulmamalı.",
            "Blok için bütün makale yeniden yazılırsa iki editörün değişikliği çarpışır ve biri kaybolur."),
        row("EY", 12, "Üç soru her gün sorulur: okuyucu sayfası, etiket sayfası ve editör listesi.",
            "\"slug ile makale\", \"etiketi ekonomi olan yayımlanmış makaleler, tarihe göre\" ve \"bu yazarın taslakları\" index ile cevaplanmalı; arşiv 2 milyon makale.",
            "Etiket sayfası index'siz çalışırsa 2 milyon makale okunur ve arşiv büyüdükçe yavaşlar."),
        row("YD", 8, "Eski sürümler geri getirilebilmeli; ama bu nadir bir iştir.",
            "Bir makalenin yayımlanmış her sürümü saklanmalı ve bir önceki sürüme dönülebilmeli.",
            "Sürüm yoksa yanlış bir düzenleme geri alınamaz; yayıncı hatalı içeriği elle düzeltir."),
        drest("cms", 2, 10, "Okuma CDN arkasında ve düz, yazma küçük; ölçek bu kartta belirleyici değildir."),
        drest("cms", 3, 20, "Yayımlanmış makale yayıncının ürünüdür; kaybı okuyucuya ve reklam verene karşı yükümlülüktür."),
        drest("cms", 4, 14, "Üç geliştirici Node.js ve MongoDB driver'ı biliyor ve database operasyonu istemiyor."),
        drest("cms", 5, 10, "Veri birkaç on GB ve trafik düz; fatura öngörülebilir olmalı."),
    ],
    cands=["doc", "ddb", "aur"],
    scores={
        "doc": [sc(10, "Makale bir document, bloklar bir array'dir ve her blok kendi field'larını taşır (Ö2); slug ile tek okuma (Ö1). Puan kırılmadı."),
                sc(10, "updateOne ile $set ve arrayFilters bloğu id'siyle bulur ve sadece onu değiştirir; sırası değişmiş olsa da doğru bloğa yazar (Ö5). Puan kırılmadı."),
                sc(10, "slug üzerinde unique index (Ö4), tags üzerinde multikey index, { status: 1, published_at: -1 } compound index ve { authors: 1, status: 1 } üç soruyu IXSCAN yapar (Ö3, Ö4). Puan kırılmadı."),
                sc(6, "Change stream her değişikliği verir (Ö7). 4 puan kırıldı: engine'de makale sürümü yoktur; uygulama her yayında önceki hâli bir article_versions collection'ına kopyalar."),
                sc(10, "Saniyede 3.000 okuma CDN arkasındadır ve replica'larla rahat karşılanır; 5 yazma primary için küçüktür. Puan kırılmadı."),
                sc(10, "Cluster volume üç AZ'de altı kopya tutar; point-in-time restore yanlış bir silmeyi geri alır. Puan kırılmadı."),
                sc(9, "Ekip MongoDB driver'ını biliyor; yedek, yama ve failover yönetilir. 1 puan kırıldı: instance sınıfını ve replica sayısını ekip seçer."),
                sc(7, "Instance saat başına ödenir. 3 puan kırıldı: Multi-AZ için en az iki instance bu küçük ve düz yükte de bütün gün çalışır; kapasitenin çoğu boştadır.")],
        "ddb": [sc(9, "Makale map ve list tipleriyle tek value olabilir. 1 puan kırıldı: blok listesi sıralı bir list'tir ve sıra uygulamanın taşıdığı bir bilgidir; bloğun id'si list'in içinde bir alandır, key değildir."),
                sc(6, "UpdateItem list'in bir elemanını değiştirir. 4 puan kırıldı: eleman değeriyle değil sırasıyla (blocks[3]) bulunur; editör blokları sürükleyince sıra değişir, uygulama önce okur ve bir sürüm koşulu ekler."),
                sc(6, "slug ve \"yazarın taslakları\" ikinci index'lerle Query olur. 4 puan kırıldı: tags bir list'tir ve list elemanına index kurulamaz; her etiket için ayrı bir value yazılır ve uygulama onları güncel tutar."),
                sc(6, "Sürümler sort key'de bir sürüm numarasıyla (v_0, v_1) ayrı value'lar olarak tutulabilir. 4 puan kırıldı: engine sürüm tutmaz; her yayında önceki hâli uygulama ayrı bir value olarak yazar (DocumentDB ile aynı mekanizma)."),
                sc(10, "On-demand mod bu küçük ve düz yükü karşılar. Puan kırılmadı."),
                sc(10, "Birkaç AZ'de saklanır; point-in-time recovery vardır. Puan kırılmadı."),
                sc(6, "Serverless: sunucu yoktur. 4 puan kırıldı: ekip MongoDB driver'ını biliyor; yeni bir API ve access pattern'lere göre key tasarımı öğrenilir."),
                sc(9, "İstek başına ödeme. 1 puan kırıldı: 3.000 okuma/saniye sürekli bir okuma birimi faturasıdır.")],
        "aur": [sc(7, "Makale bir row, bloklar bir JSONB array'i ya da ayrı bir table'dır. 3 puan kırıldı: ayrı table'da her sayfa bir JOIN ve ORDER BY'dır; JSONB'de bloklar şemasızdır ve type'lı column'larla yan yana yaşar."),
                sc(6, "Ayrı table'da tek blok tek UPDATE'tir. 4 puan kırıldı: blokların sırası ayrı bir column'dur ve sürüklemede birçok row değişir; JSONB'de blok sırasıyla güncellenir ve MVCC bütün row'u yeniden yazar."),
                sc(9, "SQL ve index'ler üç soruyu cevaplar; tags için GIN index. 1 puan kırıldı: etiket array'i ve durum sorusu birlikte iki index'in birleşimini ister."),
                sc(8, "Bir trigger her güncellemede eski row'u bir geçmiş table'ına yazar. 2 puan kırıldı: trigger yazılır, sürümlenir ve test edilir."),
                sc(10, "Bu küçük yük tek writer için rahattır. Puan kırılmadı."),
                sc(10, "Üç AZ'de altı kopya, point-in-time restore. Puan kırılmadı."),
                sc(5, "Yedek ve yama yönetilir. 5 puan kırıldı: ekip SQL ve migration disiplini öğrenir, yeni bir cluster işletir ve ACU aralığını seçer."),
                sc(8, "Serverless v2 düz yükte küçük kalır. 2 puan kırıldı: minimum ACU boşta da ödenir.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. Fark R1'in okuma/yazma şekli ve erişim yolu satırlarında ve R4'tedir; R2, R3 ve R5'te DynamoDB eşit ya da biraz öndedir. DynamoDB'nin gücü operasyondadır: sunucu yoktur, istek başına ödenir ve makale map ve list tipleriyle tek value olarak saklanabilir. "
               "Ama editörün işi list'in içindedir: blok değeriyle değil sırasıyla güncellenir ve sürükleme sırayı değiştirdiği için uygulama önce okur, sonra koşulla yazar. Etiket sayfası bir list elemanına göre sorar ve list elemanına index kurulamaz; her etiket için ayrı bir value tutulur. Ekip MongoDB driver'ını biliyor ve DynamoDB'de key tasarımını yeniden öğrenir. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: makaleler değişmeyen bloklarla bir kez yazılsaydı, sorular sadece slug ve yazar olsaydı ve okuma CDN olmadan saniyede on binlere çıksaydı.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora'nın gücü sürüm ve sorulardadır: bir trigger her güncellemede eski row'u bir geçmiş table'ına yazar ve SQL etiket, durum ve yazar sorularını birlikte cevaplar; R3'te iki aday eşittir. "
               "Ama makalenin şekli relational değildir: türü farklı sıralı bloklar ya ayrı bir table'da bir sıra column'uyla durur (her sayfa bir JOIN, her sürükleme birçok UPDATE) ya da JSONB'nin içinde şemasız kalır. R1'in veri modeli ve okuma/yazma şekli satırlarında DocumentDB öndedir. R4'te ekip SQL'i ve migration disiplinini yeni öğrenir. "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: içerik abonelik ve ödeme kayıtlarıyla aynı transaction'da yazılsaydı ve ekip zaten bir PostgreSQL işletiyor olsaydı.",
    },
    verdict="Karar: DocumentDB {doc}, DynamoDB {ddb}, Aurora PostgreSQL {aur}. Kararı R1'in veri modeli, okuma/yazma şekli ve erişim yolu satırları verir: sıralı ve türü farklı bloklar bir array'dir, tek blok değeriyle bulunup değişir ve etiket array'ine index kurulur. "
            "DocumentDB seçtiğimizde artımız: makale tek okumadır, editörlerin değişiklikleri çarpışmaz, üç liste sorusu index'lidir, ekip bildiği driver'la çalışır ve yayımlanmış içerik altı kopyayla kalıcıdır. "
            "Eksimiz: engine sürüm tutmaz, bu yüzden her yayında önceki hâli bir article_versions collection'ına biz yazarız (ya da bir change stream tüketicisi yazar); document 16 MiB'ı geçemez, bu yüzden görseller S3'te kalır; küçük yük için iki instance bütün gün çalışır. "
            "Aynı engine'in shard'lı biçimi (elastic cluster) bu kartta aday değildir: saniyede 5 yazma için shard gerekmez ve elastic cluster'da point-in-time restore yoktur, bu kartın R3'ü onu ister. "
            "Bir koşul değişseydi: içerik ödeme kayıtlarıyla aynı transaction'da yazılsaydı Aurora öne geçerdi."))

# ------------------------------------------------------------------ 4. event logs with a flexible schema (DynamoDB wins, the elastic twin is second)
DOCDB_W.append(wusecase("events", 4, sim="w_events",
    title="Esnek şemalı event log'ları: tıklama ve uygulama olayları",
    key="Her event bir document: event_type, user_id, ts, payload (türe göre farklı). Sadece eklenir, 30 gün saklanır.",
    story=dstory("events"),
    wnote="R1 toplam 50: event'in şekli, iki zaman sorusu, sadece ekleme ve 30 günlük silme engine'e sorulur; en ağır alt maddeler erişim yolu ve yaşam döngüsüdür (12'şer). "
          "R2 25 ile ikinci: saniyede 20.000, kampanya gecesi 80.000 ekleme bu kartın asıl problemidir. Birkaç event kaybı kabul edildiği için R3 5'te kalır.",
    rows=[
        row("VM", 8, "Event küçük ve basittir: 1 KB, türe göre farklı bir payload.",
            "Her event kendi payload'ını taşıyan küçük bir kayıttır; event_type, user_id ve ts her event'te vardır.",
            "Payload için sabit column'lar gerekirse her event türü ayrı bir table ya da boş column'lardır."),
        row("ŞE", 8, "Ürün ekibi her hafta yeni bir event türü ekler.",
            "Yeni bir event türü kodda bir satırla eklenmeli; migration ve bakım penceresi olmamalı.",
            "Her yeni event türü bir schema değişikliği ise analitik ekibi bir hafta bekler."),
        row("EY", 12, "İki soru her gün sorulur: destek ekranı ve izleme paneli.",
            "\"Bu kullanıcının son 100 event'i\" ve \"bu event türünün son bir saati\" zaman sırasıyla, bütün veriyi okumadan cevaplanmalı.",
            "Bu sorular 50 milyar event'i tararsa destek ekranı açılmaz."),
        row("OY", 10, "Bu iş yükünün biçimi saf eklemedir; güncelleme yoktur.",
            "Event yazıldıktan sonra değişmez; her yazma yeni bir event'tir ve diğer event'leri beklememeli.",
            "Ekleme bir okuma ya da kilit beklerse uygulamanın her isteği yavaşlar."),
        row("YD", 12, "30 günlük pencere hem storage'ın hem faturanın sınırıdır.",
            "Event 30 gün sonra kendiliğinden silinmeli; silme uygulamanın bir işi olmamalı ve yazma yolunu yavaşlatmamalı.",
            "Silme elle ya da yavaş yapılırsa storage ve fatura sınırsız büyür; günde 1,7 milyar silme yazmalarla yarışır."),
        drest("events", 2, 25, "Saniyede 20.000, tepe 80.000 ekleme: bu bir yazma ölçeği problemidir."),
        drest("events", 3, 5, "Birkaç event kaybı istatistikte görünmez ve veri zaten 30 gün sonra silinir."),
        drest("events", 4, 10, "Üç geliştirici sunucu boyutlandırmak ve shard yönetmek istemiyor."),
        drest("events", 5, 10, "50 TB'lık pencere ve sürekli yazma faturanın büyük kalemidir."),
    ],
    cands=["ddb", "doce", "doc"],
    scores={
        "ddb": [sc(10, "Event küçük bir value'dur; payload map tipinde serbesttir. Puan kırılmadı."),
                sc(10, "Key dışındaki alanlar serbesttir; yeni event türü kodda bir satırdır. Puan kırılmadı."),
                sc(8, "Partition key user_id, sort key ts ile \"son 100 event\" ters sıralı tek Query'dir. 2 puan kırıldı: \"bu türün son bir saati\" ikinci bir index ister ve event türünün az değeri olduğu için index'in key'i saat ve bir dağıtma sonekiyle tasarlanır (hot partition)."),
                sc(10, "PutItem eklemedir; okuma ve kilit beklemez. Puan kırılmadı."),
                sc(9, "TTL süresi dolan value'yu arka planda, table'ın yazma kapasitesini kullanmadan siler; silmeler eklemelerle yarışmaz. 1 puan kırıldı: silme genellikle süre dolduktan sonra birkaç gün içinde olur; storage 30 günden birkaç gün uzun tutulur."),
                sc(9, "On-demand mod yazmaları partition'lara dağıtır. 1 puan kırıldı: on-demand bir önceki tepenin iki katına kadar anında çıkar; 20.000'den 80.000'e sıçrayan kampanya gecesi için warm throughput önceden yükseltilir."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(6, "Serverless: sunucu ve shard yoktur. 4 puan kırıldı: ekip MongoDB API'sini biliyor; yeni bir API ve key tasarımı öğrenilir."),
                sc(6, "On-demand yazma başına ödenir. 4 puan kırıldı: saniyede 20.000 sürekli yazma her saat aynı birim faturasıdır; provisioned mod ve auto scaling ile düşer, bu da kapasite planıdır.")],
        "doce": [sc(10, "Event bir document'tır, payload serbesttir (Ö2). Engine instance-based cluster ile aynıdır. Puan kırılmadı."),
                 sc(10, "Yeni event türü sadece yeni document'larda görünür (Ö2). Puan kırılmadı."),
                 sc(10, "{ user_id: 1, ts: -1 } ve { event_type: 1, ts: -1 } compound index'leri iki soruyu IXSCAN yapar (Ö4). Puan kırılmadı."),
                 sc(10, "insertMany ekler; event'ler birbirini beklemez. Puan kırılmadı."),
                 sc(6, "TTL index 30 günlük silmeyi yapar. 4 puan kırıldı: TTL silmesi \"best effort\"tür ve belirli bir sürede garanti değildir; günde 1,7 milyar silme aynı storage'da eklemelerle yarışır. Engine'in diğer aracı haftalık collection açıp eskisini düşürmektir (drop), bu da uygulamanın taşıdığı bir rotasyon mantığıdır. Silmelerin ücreti R5'te sayıldı."),
                 sc(8, "Hash ile 32 shard'a kadar bölünür; her shard'ın kendi writer'ı vardır ve yazma shard sayısıyla büyür. 2 puan kırıldı: \"bu türün son bir saati\" shard key'i (user_id) içermez ve bütün shard'lara gider; 80.000'lik tepe için shard'lar önceden eklenir ve ölçeklenme sırasında index ekleme gibi şema komutları çalışmaz."),
                 sc(8, "Storage dağıtık ve kopyalıdır. 2 puan kırıldı: elastic cluster'da point-in-time restore yoktur; geri dönüş snapshot'tandır."),
                 sc(6, "Ekip MongoDB API'sini biliyor; yedek ve yama yönetilir. 4 puan kırıldı: shard key (tek field, hash) ve shard sayısı ekibin kararıdır ve shard key sonradan değişmez."),
                 sc(7, "Shard instance'ları vCPU-saat olarak ödenir ve storage GB-ay. 3 puan kırıldı: tepe için eklenen shard'lar elle küçültülmezse bütün ay ödenir.")],
        "doc": [sc(10, "Event bir document'tır, payload serbesttir (Ö2). Puan kırılmadı."),
                sc(10, "Yeni event türü sadece yeni document'larda görünür (Ö2). Puan kırılmadı."),
                sc(10, "{ user_id: 1, ts: -1 } ve { event_type: 1, ts: -1 } compound index'leri iki soruyu IXSCAN yapar (Ö4). Puan kırılmadı."),
                sc(10, "insertMany ekler; event'ler birbirini beklemez. Puan kırılmadı."),
                sc(6, "TTL index 30 günlük silmeyi yapar. 4 puan kırıldı: TTL silmesi \"best effort\"tür ve belirli bir sürede garanti değildir; günde 1,7 milyar silme aynı storage'da eklemelerle yarışır. Engine'in diğer aracı haftalık collection açıp eskisini düşürmektir (drop), bu da uygulamanın taşıdığı bir rotasyon mantığıdır. Silmelerin ücreti R5'te sayıldı."),
                sc(2, "Okumalar replica'lara dağılır. 8 puan kırıldı: bütün yazmalar tek primary'den geçer (Ö8); saniyede on binlerce ekleme ve üç index tek bir instance'ın taşıyacağı yükün ötesindedir ve replica eklemek yazmayı büyütmez."),
                sc(10, "Cluster volume üç AZ'de altı kopya tutar. Puan kırılmadı."),
                sc(6, "Ekip MongoDB API'sini biliyor; yedek ve yama yönetilir. 4 puan kırıldı: en büyük instance sınıfını seçmek, tepe gecesinden önce büyütmek ve izlemek ekibin işidir; story bunu istemiyor. Tepenin karşılanamaması R2'de sayıldı."),
                sc(5, "Instance saat başına ve I/O başına ödenir. 5 puan kırıldı: en büyük instance bütün ay ödenir; ekleme, index ve TTL silmesinin I/O'su Standard modelde faturanın büyük kalemidir (I/O-Optimized bu kalemi kaldırır, instance fiyatını artırır).")],
    },
    h2h={
        "doce": "Shard'lı document (DocumentDB elastic cluster) ile kafa kafaya. Bu, DynamoDB'ye en yakın adaydır ve kartın en öğretici karşılaştırmasıdır. Engine aynı olduğu için R1 puanları instance-based DocumentDB ile birebir aynıdır: event bir document'tır, iki soru compound index'tir ve tek zayıflık TTL silmesinin \"best effort\" olması ve I/O tüketmesidir. "
                "Elastic cluster'ı instance-based cluster'dan ayıran R2'dir: veri hash ile 32 shard'a kadar bölünür ve her shard'ın kendi writer'ı vardır, yani yazma shard sayısıyla büyür. DynamoDB'nin önünde kalan iki satır R1'in yaşam döngüsü satırı (TTL yazma kapasitesi harcamaz) ve R4'tür: shard key ve shard sayısı ekibin kararıdır ve shard key sonradan değişmez. "
                "Hangi koşul değişseydi DocumentDB elastic cluster seçilirdi: sorular event'in içine göre (payload field'ları) ve sık değişen filtreler olsaydı, ekip DynamoDB öğrenmek istemeseydi ve haftalık collection düşürmeyi uygulamaya koysaydı.",
        "doc": "Document (DocumentDB, instance-based) ile kafa kafaya. Bu kartta bu sayfanın servisi net kaybeder ve nedeni R1 değildir: R1 puanları elastic cluster ile aynıdır ve DynamoDB'nin yalnız 1,2 puan gerisindedir. "
               "Fark R2'dedir: bütün yazmalar tek primary'den geçer ve replica eklemek yazmayı büyütmez. Saniyede 20.000, tepe gecesi 80.000 ekleme ve her eklemede üç index güncellemesi bu sayfanın kaba ölçeğinde tek primary'nin ötesindedir (A9'daki \"Tek bir primary saniyede kaç yazma taşır?\" kutusu). R4'te en büyük instance'ı seçip tepeden önce büyütmek ekibin işidir, R5'te bu instance bütün ay ve I/O ile ödenir; bunlar kapasiteyi ayarlamanın ve ödemenin bedelidir, tepeyi karşılayamamak ise yalnız R2'de sayıldı. "
               "Ekibin ilk tercihi mevcut cluster'a bir collection eklemekti; bu kart o tercihin neden yanlış olduğunu gösterir. "
               "Hangi koşul değişseydi DocumentDB seçilirdi: event hızı saniyede birkaç yüze inseydi ve event'in içine göre sorular ana iş olsaydı.",
    },
    verdict="Karar: DynamoDB {ddb}, DocumentDB elastic cluster {doce}, DocumentDB {doc}. Kararı R2 verir: üç adayın R1'i birbirine çok yakındır, ama yazma ölçeğini tek primary taşıyamaz. Elastic cluster yazmayı shard'larla büyütür ve DynamoDB'ye yakın gelir; DynamoDB yaşam döngüsü satırında (TTL silmeleri eklemelerle yarışmaz) ve R4'te öndedir. "
            "Yine de DocumentDB seçersek artımız: ekip bildiği API ile çalışır ve event'in içine göre sorular filtre ve index'tir; seçim elastic cluster olmalıdır. "
            "Eksimiz: shard key (örneğin user_id, hash) ve shard sayısını biz seçeriz ve shard key sonradan değişmez; TTL yerine haftalık collection açıp eskisini düşürürüz, yoksa silmeler I/O olarak faturalanır ve yazmalarla yarışır; elastic cluster'da point-in-time restore ve change stream yoktur; shard key yanlış seçilirse (çok event üreten birkaç kullanıcı) bir shard ısınır ve shard key değişmediği için çıkış yolu yeni bir collection'a veri taşımaktır. Akış platformu (Kinesis Data Streams) bu kartta aday değildir: \"bu kullanıcının son 100 event'i\" sorusunu bir key ile cevaplamaz; warehouse'a giden günlük kopya için ikisi birlikte kullanılabilir. "
            "Bir koşul değişseydi: event hızı saniyede birkaç yüze inseydi mevcut DocumentDB cluster'ına bir collection eklemek doğru cevap olurdu."))

# ------------------------------------------------------------------ 5. IoT device registry and configuration
DOCDB_W.append(wusecase("devices", 5,
    title="IoT cihaz kayıtları ve konfigürasyonları",
    key="Collection: devices. Document: _id (seri no), model, firmware, settings (modele göre iç içe), sensors (array), location.",
    story=dstory("devices"),
    wnote="R1 toplam 46: modele göre değişen kayıt (VM 12, ŞE 12) ve destek ekibinin önceden bilinmeyen soruları (EY 14) bu iş yükünün kendisidir. "
          "R4 16 ve R5 16 ile ikinci sırada: iki kişilik ekip ve çok küçük bir yük; burada ölçek değil sorgu esnekliği ve sabit maliyet belirleyicidir.",
    rows=[
        row("VM", 12, "Destek ekranı cihazı bütün ayarlarıyla tek seferde gösterir.",
            "Bir cihaz kaydı modele göre farklı ayarları (ısı eğrisi, sensör listesi), kurulum adresini ve sahibini tek bir bütün olarak taşımalı.",
            "Kayıt birkaç yere bölünürse her destek araması birkaç okumadır."),
        row("ŞE", 12, "Ürün ekibi her firmware sürümünde ayar şekline yeni field'lar ekler.",
            "Yeni bir ayar field'ı sadece yeni sürümdeki cihazlara yazılabilmeli; eski cihazlar değişmeden kalmalı.",
            "Her firmware sürümü bir migration ise sürüm takvimi database'e bağlanır."),
        row("EY", 14, "Destek ekibinin soruları önceden bilinmez ve her gün değişir.",
            "\"Firmware'i 2.3'ten eski ve İzmir'de olan cihazlar\" ve \"sensör listesinde nem sensörü olanlar\" gibi her field'a ve iç içe listeye göre sorular yeni bir tasarım istemeden cevaplanmalı.",
            "Destek sorusu için bütün kayıtlar taranırsa 800.000 cihazda destek ekranı yavaşlar; her yeni soru bir veri projesi olursa destek ekibi bekler."),
        row("OY", 8, "Cihaz saatte bir okur; tek bir ayar değişir.",
            "Tek bir ayarı değiştirmek bütün kaydı yeniden yazmamalı.",
            "Bütün kayıt yeniden yazılırsa aynı anda cihazdan gelen bir güncelleme ezilir."),
        drest("devices", 2, 8, "Saniyede 300 okuma ve 20 yazma; ölçek belirleyici değildir."),
        drest("devices", 3, 14, "Kayıt kaybı cihazı fabrika ayarına düşürür ve müşteri arar."),
        drest("devices", 4, 16, "İki geliştirici: her operasyon işi ürün geliştirmeyi durdurur."),
        drest("devices", 5, 16, "Yük çok küçüktür; fatura kapasitenin alt sınırıyla belirlenir."),
    ],
    cands=["doc", "ddb", "aur"],
    scores={
        "doc": [sc(10, "Kayıt bir document'tır: settings modele göre iç içe, sensors bir array (Ö2); seri no _id'dir ve tek okumadır (Ö1). Puan kırılmadı."),
                sc(10, "Yeni ayar field'ı sadece yeni document'lara yazılır (Ö2). Puan kırılmadı."),
                sc(9, "Her field'a ve iç içe listeye göre soru bir find'dır (Ö3); sık sorulara index, sensör listesine multikey index kurulur (Ö4). 1 puan kırıldı: index'i olmayan yeni bir soru 800.000 kayıtta bir COLLSCAN'dir; index kurulana kadar replica'ya yönlendirilir."),
                sc(10, "updateOne ile $set tek ayarı değiştirir (Ö5). Puan kırılmadı."),
                sc(10, "Saniyede 300 okuma ve 20 yazma bir primary ve bir replica için küçüktür. Puan kırılmadı."),
                sc(10, "Cluster volume üç AZ'de altı kopya tutar; sürekli yedek vardır. Puan kırılmadı."),
                sc(9, "Ekip MongoDB API'sini biliyor; yedek ve yama yönetilir. 1 puan kırıldı: instance sınıfını ve replica sayısını ekip seçer."),
                sc(6, "Instance saat başına ödenir; serverless 0,5 DCU'ya iner. 4 puan kırıldı: bu çok küçük yükte de Multi-AZ için iki instance çalışır ve istenen şey en düşük sabit maliyettir.")],
        "ddb": [sc(10, "Kayıt map ve list tipleriyle tek value'dur; seri no partition key'dir. Puan kırılmadı."),
                sc(10, "Key dışındaki alanlar serbesttir. Puan kırılmadı."),
                sc(4, "Seri no ile GetItem tek okumadır. 6 puan kırıldı: destek ekibinin her field'a göre soruları ya her soruya bir ikinci index ya da 800.000 kaydın Scan'idir; sensör listesinin elemanına index kurulamaz."),
                sc(8, "UpdateItem SET settings.x tek ayarı değiştirir. 2 puan kırıldı: sensör listesindeki bir eleman sırasıyla güncellenir."),
                sc(10, "On-demand mod bu küçük yükü karşılar. Puan kırılmadı."),
                sc(10, "Birkaç AZ'de saklanır; point-in-time recovery vardır. Puan kırılmadı."),
                sc(6, "Serverless: sunucu yoktur. 4 puan kırıldı: ekip MongoDB API'sini biliyor; yeni bir API ve key tasarımı öğrenilir."),
                sc(10, "İstek başına ödeme; bu yükte fatura çok küçüktür. Puan kırılmadı.")],
        "aur": [sc(7, "Sabit field'lar column, modele göre değişen ayarlar JSONB'dir. 3 puan kırıldı: kayıt iki biçime bölünür ve sensör listesi ya JSON'dur ya ayrı bir table."),
                sc(7, "JSONB'nin içi serbesttir. 3 puan kırıldı: sabit column'a dönen her ayar bir migration'dır ve firmware takvimine bağlanır."),
                sc(9, "SQL her column'da ve JSONB'nin içinde sorar. 1 puan kırıldı: iç içe listeye göre sorular JSON yolu ve GIN index ister."),
                sc(7, "jsonb_set tek ayarı değiştirir. 3 puan kırıldı: MVCC her UPDATE'te bütün row'u yeniden yazar."),
                sc(10, "Bu küçük yük tek writer için rahattır. Puan kırılmadı."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(5, "Yedek ve yama yönetilir. 5 puan kırıldı: ekip SQL'i ve migration disiplinini öğrenir, yeni bir cluster işletir ve ACU aralığını seçer."),
                sc(7, "Serverless v2 küçük kalır. 3 puan kırıldı: minimum ACU iki instance için boşta da ödenir.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. Fark R1'in erişim yolu satırındadır; R5'te DynamoDB öndedir. DynamoDB'nin gücü bu küçük yükte faturadır: istek başına ödeme ile ayda birkaç dolarlık bir database ve hiç sunucu. Kayıt map ve list tipleriyle tek value olarak saklanır ve seri no ile tek okumadır. "
               "Ama bu iş yükünün kalbi destek ekibinin soruları: \"firmware'i eski ve İzmir'de\", \"nem sensörü olanlar\". DynamoDB bunlar için ya her soruya bir ikinci index ya da 800.000 kaydın Scan'ini ister ve bir listenin elemanına index kurulamaz. Sorular önceden bilinmediği için index'ler de önceden kurulamaz. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: destek soruları birkaç sabit soru olsaydı (seri no, sahip, model), cihaz sayısı on milyonlara çıksaydı ve cihazlar ayarını saniyede bir okusaydı.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora'nın gücü destek sorularındadır: SQL her column'da ve JSONB'nin içinde sorar ve R2 ile R3'te iki aday eşittir. "
               "Ama cihaz kaydı modelden modele farklıdır ve her firmware sürümüyle değişir: Aurora'da kayıt sabit column'lar ve bir JSONB'ye bölünür, sabite dönen her ayar bir migration'dır ve tek bir ayar MVCC ile bütün row'un yeni bir sürümüdür. R1'in dört satırının üçünde DocumentDB öndedir. R4'te iki kişilik ekip SQL'i ve migration disiplinini yeni öğrenir ve yeni bir cluster işletir. "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: cihaz kayıtları faturalama ve sözleşme table'larıyla aynı transaction'da değişseydi ve ekip SQL biliyor olsaydı.",
    },
    verdict="Karar: DocumentDB {doc}, DynamoDB {ddb}, Aurora PostgreSQL {aur}. Kararı R1'in erişim yolu satırı verir: destek ekibinin önceden bilinmeyen soruları iç içe field'lara ve listelere göredir ve document engine'i bunları filtre ve index ile cevaplar. "
            "DocumentDB seçtiğimizde artımız: kayıt tek okumadır, firmware sürümü migration istemez, destek ekibinin her sorusu bir find'dır. "
            "Eksimiz: bu çok küçük yük için de iki instance öderiz; bunu serverless (0,5 DCU'dan başlayan aralık) ya da geliştirme ortamında tek instance ile azaltırız; yeni bir sık soru için index'i biz kurarız. "
            "Telemetri bu kartın dışındadır: saniyede 50.000 ölçüm bir time series database'ine (Timestream for InfluxDB) gider; doğru mimari ikisinin birlikte çalışmasıdır, cihaz kaydı DocumentDB'de, ölçümler time series'te. "
            "Aynı engine'in shard'lı biçimi (elastic cluster) bu kartta aday değildir: saniyede 20 yazma için shard gerekmez. "
            "Bir koşul değişseydi: destek soruları birkaç sabit soruya inseydi DynamoDB'nin faturası öne geçerdi."))

# ------------------------------------------------------------------ 6. mobile app sync: list documents (the elastic twin loses on change streams)
DOCDB_W.append(wusecase("sync", 6,
    title="Mobil uygulama senkronizasyonu: liste document'ları",
    key="Collection: lists. Document: _id, owner, title, items (array), updated_at, version. Change stream ile cihazlara yayın.",
    story=dstory("sync"),
    wnote="R1 toplam 44: sürüm koşullu array içi güncelleme (OY 14), değişikliğin cihazlara akması (YD 12) ve koşulun kendisi (TA 10) bu uygulamanın kalbidir. "
          "R2 18 ile ikinci: saniyede 1.500 yazma ve yılda yüzde 40 büyüme. R3 14 ve R4 14: liste kullanıcının verisidir ve ekip sunucu istemiyor.",
    rows=[
        row("OY", 14, "Her yazma tek bir öğedir ve birkaç cihaz aynı listeye yazar.",
            "Array'deki tek öğe (\"ekmek\") tek yazmada değişmeli; liste okunup baştan yazılmamalı.",
            "Liste baştan yazılırsa iki cihazın değişikliği çarpışır ve biri kaybolur."),
        row("TA", 10, "Çevrimdışı cihaz eski bir sürüme dayanarak yazabilir.",
            "\"version = 7 ise yaz ve 8 yap\" koşulu yazmanın içinde test edilmeli; koşul yanlışsa hiçbir şey yazılmamalı.",
            "Koşulsuz yazma eski bir cihazın yeni değişikliği ezmesine izin verir."),
        row("YD", 12, "Diğer cihazlar değişikliği saniyeler içinde almalıdır.",
            "Her değişiklik saniyeler içinde bir yayın servisine akmalı; servis kesintiden sonra kaldığı yerden devam edebilmeli.",
            "Değişikliği bulmak için 200 milyon document'ı her saniye sorgulamak mümkün değildir."),
        row("EY", 8, "Uygulama açılışında tek soru sorulur.",
            "\"Bu kullanıcının listeleri, son değişikliğe göre\" ve _id ile tek liste.",
            "Bu soru yavaşsa uygulama boş bir ekranla açılır."),
        drest("sync", 2, 18, "Saniyede 1.500 yazma bugün rahattır, ama yılda yüzde 40 büyüme planlanmalıdır."),
        drest("sync", 3, 14, "Kaybolan bir liste uygulamanın silinmesidir."),
        drest("sync", 4, 14, "Altı geliştirici MongoDB driver'ı kullanıyor ve sunucu istemiyor."),
        drest("sync", 5, 10, "Sürekli yazma sürekli I/O demektir; bütçe tahmin edilebilir olmalı."),
    ],
    cands=["doc", "ddb", "doce"],
    scores={
        "doc": [sc(10, "updateOne ile $set: { 'items.$[i].done': true } ve arrayFilters öğeyi değeriyle bulur ve sadece onu değiştirir (Ö5). Puan kırılmadı."),
                sc(10, "Filtredeki version: 7 koşulu ve $inc: { version: 1 } aynı atomik yazmadadır; koşul yanlışsa matchedCount 0 döner ve hiçbir şey yazılmaz (Ö5). Puan kırılmadı."),
                sc(9, "Change stream her değişikliği sırayla verir; tüketici resume token ile kaldığı yerden devam eder (Ö7). 1 puan kırıldı: tutulma süresi varsayılan üç saattir ve en fazla yedi güne ayarlanır."),
                sc(10, "{ owner: 1, updated_at: -1 } compound index ile kullanıcının listeleri sıralı gelir; _id ile tek okuma (Ö1, Ö4). Puan kırılmadı."),
                sc(8, "Saniyede 1.500 yazma tek primary için rahattır. 2 puan kırıldı: bütün yazmalar tek primary'den geçer (Ö8); yılda yüzde 40 büyüme birkaç yılda tek primary'nin sınırına yaklaşır ve o gün elastic cluster'a geçiş gerekir."),
                sc(10, "Cluster volume üç AZ'de altı kopya tutar; point-in-time restore vardır. Puan kırılmadı."),
                sc(8, "Ekip MongoDB driver'ını biliyor; yedek ve yama yönetilir. 2 puan kırıldı: instance sınıfını ekip seçer ve change stream tüketicisi ekibin işlettiği bir süreçtir."),
                sc(7, "Instance saat başına ödenir. 3 puan kırıldı: saniyede 1.500 yazma ve change stream sürekli I/O üretir; Standard modelde fatura I/O ile dalgalanır, I/O-Optimized bunu sabitler ama instance fiyatını artırır.")],
        "ddb": [sc(6, "UpdateItem bir list elemanını değiştirir. 4 puan kırıldı: öğe değeriyle değil sırasıyla (items[3]) bulunur; uygulama önce okur ve sırayı bulur."),
                sc(9, "ConditionExpression \"version = :v\" yazma anında test edilir. 1 puan kırıldı: sıra ile güncellenen öğe için koşul sürüme dayanır; sıra değişirse yazma reddedilir ve uygulama yeniden okur."),
                sc(9, "Streams her değişikliği verir ve Lambda ile doğrudan bağlanır. 1 puan kırıldı: kayıtlar 24 saat tutulur."),
                sc(9, "Partition key owner ile kullanıcının listeleri tek Query'dir. 1 puan kırıldı: son değişikliğe göre sıra için sort key updated_at olamaz (her yazmada değişir); ikinci bir index kurulur."),
                sc(10, "On-demand mod yazmaları partition'lara dağıtır; büyüme bir tasarım değişikliği değildir. Puan kırılmadı."),
                sc(10, "Birkaç AZ'de saklanır; point-in-time recovery vardır. Puan kırılmadı."),
                sc(6, "Serverless: sunucu yoktur ve Streams'i Lambda okur. 4 puan kırıldı: uygulamanın MongoDB driver'ı ile yazılmış veri katmanı yeni bir API ile yeniden yazılır."),
                sc(8, "İstek başına ödeme. 2 puan kırıldı: saniyede 1.500 yazma her saat aynı yazma birimi faturasıdır.")],
        "doce": [sc(10, "Engine aynıdır: updateOne ve arrayFilters öğeyi değeriyle bulur (Ö5). Puan kırılmadı."),
                 sc(10, "Filtredeki sürüm koşulu tek document'ta atomiktir (Ö5). Puan kırılmadı."),
                 sc(9, "Engine change stream verir (Ö7). 1 puan kırıldı: tutulma süresi varsayılan üç saattir. Elastic cluster bu özelliği sunmaz; bu servis tasarımıdır ve R4'te sayıldı."),
                 sc(10, "Compound index aynıdır (Ö4); owner shard key olursa soru tek shard'a gider. Puan kırılmadı."),
                 sc(10, "Yazma shard'larla büyür; yılda yüzde 40 büyüme shard eklemektir. Puan kırılmadı."),
                 sc(8, "Storage dağıtık ve kopyalıdır. 2 puan kırıldı: elastic cluster'da point-in-time restore yoktur."),
                 sc(3, "Yedek ve yama yönetilir. 7 puan kırıldı: elastic cluster change stream'i desteklemez (eksik bir servis özelliği, bu yüzden R1'de değil burada); cihazlara yayın için uygulama her yazmadan sonra değişikliği ayrıca bir kuyruğa ya da topic'e yayımlar, bu da yeni bir parça ve bir tutarsızlık kaynağıdır; shard key ve shard sayısı da ekibin kararıdır."),
                 sc(6, "Shard instance'ları vCPU-saat olarak ödenir. 4 puan kırıldı: en az iki shard ve her shard'da iki instance bugünkü yük için gerekenden büyüktür.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. Fark R1'in okuma/yazma şekli satırında ve R4'tedir; R2'de DynamoDB öndedir. DynamoDB'nin gücü büyümededir: yazmalar partition'lara dağılır ve yılda yüzde 40 büyüme bir tasarım değişikliği değildir; Streams ve Lambda yayını az parçayla yapar ve koşullu yazma sürümü korur. "
               "Ama bu uygulamanın her yazması bir listenin içindeki tek bir öğedir ve DynamoDB'de öğe değeriyle değil sırasıyla bulunur: uygulama önce okur, sırayı bulur, sonra koşulla yazar ve sıra arada değişirse yeniden dener. Veri katmanı zaten MongoDB driver'ı ile yazılmıştır. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: her öğe kendi value'su olsaydı (partition key liste, sort key öğe), yazma saniyede on binlere çıksaydı ve uygulama sıfırdan yazılsaydı.",
        "doce": "Shard'lı document (DocumentDB elastic cluster) ile kafa kafaya. Engine aynı olduğu için R1 puanları birebir aynıdır; bu kart ikizler arasındaki farkı servis tasarımının nasıl verdiğini gösterir. Elastic cluster R2'de öndedir: yazma shard'larla büyür ve yılda yüzde 40 büyüme bir sorun değildir. "
                "Ama bu uygulamanın yayını change stream'e dayanır ve elastic cluster change stream'i desteklemez; uygulama her yazmadan sonra değişikliği ayrıca yayımlar ve iki yazmadan biri başarısız olursa cihazlar eski listeyi görür. Point-in-time restore da yoktur ve bugünkü 1.500 yazma için en az iki shard pahalıdır. R4'te yedi puan bu yüzden kırıldı. "
                "Hangi koşul değişseydi DocumentDB elastic cluster seçilirdi: yazma tek primary'nin sınırına gerçekten ulaşsaydı ve yayın change stream yerine uygulamanın kendi olaylarıyla yapılsaydı.",
    },
    verdict="Karar: DocumentDB {doc}, DynamoDB {ddb}, DocumentDB elastic cluster {doce}. Kararı R1'in okuma/yazma şekli ve yaşam döngüsü satırları ile R4 verir: sürüm koşullu array içi güncelleme ve change stream ile yayın bu uygulamanın tanımıdır. "
            "DocumentDB seçtiğimizde artımız: her yazma tek öğedir ve çarpışmaz, eski bir cihazın yazması reddedilir, yayın servisi change stream'i resume token ile okur, veri katmanı değişmez. Çevrimdışı bir cihazın yazması reddedilince iş kaybolmaz: uygulama listeyi yeniden okur ve bekleyen her değişikliği öğe öğe yeniden uygular; aynı öğe arada başkası tarafından değiştirilmişse kullanıcıya hangisinin kalacağını sorar. "
            "Eksimiz: bütün yazmalar tek primary'den geçer, bu yüzden primary'nin CPU'sunu ve yazma gecikmesini izleriz ve büyüme sınıra yaklaşınca elastic cluster'a geçişi planlarız (o gün yayın change stream'siz yeniden tasarlanır); change stream tüketicisini biz işletiriz ve tutulma süresini tüketicinin en uzun kesintisine göre ayarlarız; I/O faturasına göre I/O-Optimized'ı değerlendiririz. "
            "Bir koşul değişseydi: yazma saniyede on binlere çıksaydı DynamoDB öne geçerdi."))

# ------------------------------------------------------------------ 7. order documents: a read model next to Aurora
DOCDB_W.append(wusecase("orders", 7,
    title="Sipariş document'ları: satırlar, adres ve durum geçmişi",
    key="Collection: orders. Document: _id, customer_id, lines (array), address (iç içe), status, history (array). Checkout Aurora'da kalır.",
    story=dstory("orders"),
    wnote="R1 toplam 46: siparişin şekli (VM 14), üç sorusu (EY 14) ve durum değişikliğinin biçimi (OY 12) okuma modelinin kendisidir. "
          "R4 20 ile ikinci: Lale Market'te Aurora ve DocumentDB zaten çalışır ve okuma modeli checkout'un takviminden bağımsız olmalıdır. R5 16: ikisine de ekleme yapılır, yeni bir database kurulmaz.",
    rows=[
        row("VM", 14, "\"Siparişlerim\", kargo takibi ve destek ekranı siparişin tamamını ister.",
            "Sipariş _id ile tek okumada satırlar, o günkü adres ve durum geçmişiyle gelmeli; adres siparişteki hâliyle saklanmalı.",
            "Sipariş ekranı parçalardan toplanırsa her açılış dört okumadır; adres referansla tutulursa müşteri taşınınca eski siparişin adresi değişir."),
        row("OY", 12, "Her durum değişikliği hem status'u hem geçmişi değiştirir.",
            "Durum değişikliği history array'ine eklenip status field'ını tek yazmada değiştirmeli; yazmalar checkout event'lerinden gelir.",
            "İki yazmadan biri kaybolursa ekran \"kargoda\" der, geçmiş \"hazırlanıyor\"da kalır."),
        row("EY", 14, "Üç soru her gün sorulur: müşteri ekranı, operasyon listesi ve geri çağırma listesi.",
            "\"Bu müşterinin siparişleri, yeniye göre\", \"kargoda ve üç günden eski\" ve \"bu ürünü içeren siparişler\" index ile cevaplanmalı; 5 milyon sipariş.",
            "Index'siz her soru 5 milyon siparişi okur; bir ürün geri çağrıldığında liste saatler sürer."),
        row("ŞE", 6, "Kargo şirketi değişince geçmişe yeni field'lar gelir; ama nadiren.",
            "Yeni bir durum türü ya da satır field'ı migration istemeden eklenmeli.",
            "Her kargo değişikliği bir migration ise okuma modeli checkout ekibinin takvimine bağlanır."),
        drest("orders", 2, 10, "Günde 5.000 sipariş ve saniyede 200 okuma; hacim küçüktür."),
        drest("orders", 3, 8, "Kayıt sistemi Aurora'dır; bu kopya event'lerden yeniden kurulur."),
        row("R4", 20, "İki database de zaten çalışır; soru hangisine eklemenin daha az iş olduğudur ve okuma modeli checkout'tan bağımsız olmalıdır.",
            "Üç geliştirici SQL ve MongoDB biliyor. Okuma modeli var olan bir cluster'a eklenmeli; checkout writer'ını yormamalı ve checkout'un migration takviminden bağımsız değişebilmeli. Yeni bir durum türü migration'sız gelmeli.",
            "Okuma modeli checkout'un cluster'ında ve schema'sında yaşarsa her kargo değişikliği checkout'un migration penceresini bekler ve ekran okumaları checkout writer'ıyla aynı storage'ı paylaşır."),
        row("R5", 16, "İş yükü küçüktür; yeni bir sabit maliyet istenmez.",
            "Var olan bir cluster'a ekleme: yeni bir minimum kapasite ödenmemeli; veri birkaç on GB.",
            "Küçük bir okuma modeli için yeni bir cluster açmak faturaya iş yükünden büyük bir kalem ekler."),
    ],
    cands=["doc", "aur", "ddb"],
    scores={
        "doc": [sc(10, "Sipariş tek document'tır: lines bir array, address bir embedded document, history bir array (Ö2); _id ile tek okuma (Ö1). Adres siparişin içine kopyalanır. Puan kırılmadı."),
                sc(10, "updateOne ile $set: { status } ve $push: { history } tek atomik yazmadır (Ö5). Puan kırılmadı."),
                sc(10, "{ customer_id: 1, created_at: -1 }, { status: 1, updated_at: 1 } compound index'leri ve lines.product_id üzerinde multikey index üç soruyu IXSCAN yapar (Ö3, Ö4). Puan kırılmadı."),
                sc(10, "Yeni durum türü ya da satır field'ı sadece yeni document'lara yazılır (Ö2). Puan kırılmadı."),
                sc(10, "Saniyede birkaç yazma ve 200 okuma var olan cluster için küçüktür. Puan kırılmadı."),
                sc(10, "Cluster volume üç AZ'de altı kopya tutar; kopya kaybolsa event'lerden yeniden kurulur. Puan kırılmadı."),
                sc(8, "Lale Market'in DocumentDB cluster'ına bir collection eklenir; checkout'tan bağımsızdır ve ekip API'yi biliyor. 2 puan kırıldı: checkout event'ini okuyup document'ı yazan tüketici ekibin işlettiği bir süreçtir."),
                sc(8, "Var olan cluster'a bir collection: yeni bir minimum kapasite yoktur. 2 puan kırıldı: ek okuma ve yazma cluster'ın I/O'sunu artırır, belki bir replica daha gerekir.")],
        "aur": [sc(7, "Sipariş orders ve order_items table'larında durur; geçmiş ayrı bir table ya da JSONB'dir. 3 puan kırıldı: sipariş ekranı bir JOIN'dir ya da sipariş bir JSONB document'ı olarak tutulur ve type'lı column'larla yan yana yaşar."),
                sc(9, "UPDATE status ve INSERT history tek transaction'dır. 1 puan kırıldı: iki cümle ve bir transaction; tek yazma değildir."),
                sc(10, "SQL ve index'ler üç soruyu cevaplar; \"bu ürünü içeren\" order_items üzerinde bir JOIN'dir. Puan kırılmadı."),
                sc(7, "Yeni kargo field'ı JSONB'de migration istemez. 3 puan kırıldı: column'a dönen her field bir migration'dır."),
                sc(10, "Okumalar reader instance'a gider; okuma modelinin saniyede birkaç yazması checkout writer'ından geçer ama Aurora sayfasının tek writer tablosunun ilk satırındadır (saniyede 500'e kadar: 0). Puan kırılmadı."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(7, "Aurora zaten çalışır ve ekip SQL biliyor; okuma modeli checkout ile aynı transaction'da yazılabilir, bu yüzden tüketici, ikinci kopya ve sırasız event sorunu yoktur. 3 puan kırıldı: okuma modeli checkout'un schema'sında yaşar ve her kargo field'ı checkout'un migration takvimini bekler; writer yükü R2'nin satırıdır."),
                sc(8, "Var olan cluster'a table eklenir. 2 puan kırıldı: ekran okumaları için bir reader instance ve okuma modelinin yazmaları ACU olarak ödenir.")],
        "ddb": [sc(10, "Sipariş map ve list tipleriyle tek value'dur; adres kopyalanır; dört beş elemanlı geçmiş 400 KB sınırının çok altındadır. Puan kırılmadı."),
                sc(9, "UpdateItem SET status ve list_append tek yazmadır. 1 puan kırıldı: list_append sadece sona ekler; bir geçmiş kaydını düzeltmek sırasıyla yapılır."),
                sc(5, "Partition key müşteri, sort key tarih ile \"müşterinin siparişleri\" tek Query'dir; \"kargoda ve üç günden eski\" bir ikinci index ister. 5 puan kırıldı: \"bu ürünü içeren siparişler\" bir list elemanına göre sorudur ve list elemanına index kurulamaz; her satır ayrı bir value olarak ikinci kez yazılır."),
                sc(10, "Key dışındaki alanlar serbesttir. Puan kırılmadı."),
                sc(10, "On-demand mod bu küçük yükü karşılar. Puan kırılmadı."),
                sc(10, "Birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(5, "Serverless: sunucu yoktur. 5 puan kırıldı: Lale Market'te sepet DynamoDB'dedir ama okuma modeli için yeni bir table, key tasarımı ve satırların ikinci kopyası ekibin işidir."),
                sc(9, "İstek başına ödeme. 1 puan kırıldı: her satırın ikinci kopyası yazma birimi tüketir.")],
    },
    h2h={
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Bu, okuyucunun \"sipariş zaten Aurora'da, neden ikinci bir yer?\" dediği yarıştır. Aurora'nın gücü sorulardadır: üç soru SQL ve index'lerle cevaplanır, durum değişikliği ve geçmiş tek transaction'dır ve Aurora zaten çalışır. "
               "Aurora'nın bir kazancı daha vardır: okuma modeli checkout ile aynı transaction'da yazılabilir, tüketici ve sırasız event sorunu olmaz. Ama story'nin istediği iki şey Aurora'da kaybolur: okuma modeli checkout'un cluster'ında ve schema'sında yaşar, bu yüzden her kargo field'ı checkout'un migration takvimini bekler; okuma modelinin yazmaları checkout writer'ından geçer, ama saniyede birkaç yazma R2'de puan kırdırmaz. R1'de de sipariş ekranı bir JOIN'dir ya da sipariş bir JSONB document'ıdır; DocumentDB'de sipariş, ekranın istediği şekliyle tek bir document'tır. "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: sipariş ekranı checkout ile aynı ekip ve aynı migration takvimiyle yaşasaydı ve okumalar bir reader instance'ı yormayacak kadar az olsaydı. O zaman ayrı bir okuma modeli gereksizdir. Aynı cluster'da ayrı bir schema writer'ı ve storage'ı paylaşır; materialized view ise her yenilemede bütün sorguyu yeniden çalıştırır.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB'nin gücü operasyondadır: sunucu yoktur ve sipariş map ve list tipleriyle tek value olarak saklanır; \"müşterinin siparişleri\" partition key ve sort key ile tek Query'dir. "
               "Ama üçüncü soru, \"bu ürünü içeren siparişler\", bir list elemanına göredir ve DynamoDB list elemanına index kuramaz: her satır ayrı bir value olarak ikinci kez yazılır ve uygulama iki kopyayı güncel tutar. \"Kargoda ve üç günden eski\" de bir ikinci index'tir. R4'te okuma modeli için yeni bir table ve key tasarımı gerekir; DocumentDB'de ise var olan cluster'a bir collection eklenir. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: sorular sadece müşteri ve sipariş id'si olsaydı, okuma saniyede on binlere çıksaydı ve ekip DocumentDB işletmeseydi.",
    },
    verdict="Karar: DocumentDB {doc}, Aurora PostgreSQL {aur}, DynamoDB {ddb}. Kararı R1'in veri modeli satırı ve R4 verir: sipariş ekranının şekli tek bir document'tır ve okuma modeli checkout'tan bağımsız yaşamalıdır. "
            "DocumentDB seçtiğimizde artımız: sipariş tek okumadır, adres o günkü hâliyle saklanır, durum ve geçmiş tek yazmadır, üç soru index'lidir ve checkout writer'ı yorulmaz. "
            "Eksimiz: iki kopya vardır ve kayıt sistemi Aurora'dır; checkout commit'inden sonra bir event'le document'ı yazan tüketiciyi biz işletiriz ve yazmayı tekrar edilebilir yaparız (_id = sipariş id'si, upsert); event'ler sırasız gelebilir, bu yüzden her event bir sıra numarası taşır ve güncelleme filtresi \"seq bu event'ten küçükse\" der, eski bir event yeni bir durumu ezmez; kopya event'lerden yeniden kurulabilmelidir. "
            "Doğru mimari ikisinin birlikte çalışmasıdır: sipariş kaydı ve kurallar Aurora'da, ekranın okuma modeli DocumentDB'de. "
            "Aynı engine'in shard'lı biçimi (elastic cluster) bu kartta aday değildir: günde 5.000 sipariş için shard gerekmez. "
            "Bir koşul değişseydi: okuma modeli checkout ile aynı takvimde yaşayabilseydi Aurora'da bir reader yeterdi."))

# ------------------------------------------------------------------ 8. catalog search by nested fields: OpenSearch wins R1, DocumentDB wins the total
DOCDB_W.append(wusecase("search", 8, sim="w_search",
    title="İç içe field'lara göre katalog araması: filtre ve facet",
    key="Collection: products. Sorgu: category, 'attributes.renk', 'attributes.garanti_ay' ve price üzerinde filtre, sıralama, limit. Facet sayıları $group ile.",
    story=dstory("search"),
    wnote="R1 toplam 42: birçok field'ın serbest birleşimi (EY 14), facet sayıları (AO 12) ve bunu taşıyan algoritma (DA 10) bir arama sorusudur. "
          "R2 22 ile ikinci: saniyede 1.200, kampanyada 5.000 filtreli okuma ve 50 ms. R4 18: ekip ikinci bir sistem ve onu besleyen bir boru hattı istemiyor.",
    rows=[
        row("EY", 14, "Kategori sayfası mağazanın en çok açılan sayfasıdır ve her ziyaretçi farklı bir filtre birleşimi seçer.",
            "Dört beş field'ın (iç içe olanlar dahil) her birleşimiyle filtre, bir field'a göre sıralama ve sayfalama; filtre field'ları 20 tane.",
            "Bir birleşim index'siz çalışırsa 200.000 document taranır ve sayfa saniyeler sürer."),
        row("AO", 12, "Seçenek sayıları her sayfada gösterilir.",
            "Her filtre field'ı için seçenek sayıları (facet: \"siyah (9), lacivert (6)\") her filtre değişiminde hesaplanmalı.",
            "Facet sayıları her açılışta bütün kategoriyi okursa kampanyada sayfa yavaşlar."),
        row("DA", 10, "Serbest birleşimleri ve sayıları hızlı veren şey engine'in index yapısıdır.",
            "Engine'in index yapısı birçok field'ın serbest birleşimini ve sayımı, her birleşime ayrı bir yapı kurmadan karşılamalı.",
            "Her birleşim için ayrı bir sıralı yapı gerekiyorsa 20 field'ın birleşimleri index sınırını ve yazma maliyetini aşar."),
        row("ŞE", 6, "Ayda bir yeni filtre field'ı gelir.",
            "Yeni bir filtre field'ı (iç içe olabilir) migration ve yeniden kurulum istemeden eklenmeli.",
            "Her yeni filtre bir index'in baştan kurulmasını isterse kategori ekibi bekler."),
        drest("search", 2, 22, "Saniyede 1.200, kampanyada 5.000 filtreli okuma ve 50 ms: kategori sayfasının hızı satıştır."),
        drest("search", 3, 6, "Arama katmanı kaybolursa yeniden kurulur; katalog DocumentDB'de kalıcıdır."),
        drest("search", 4, 18, "Dört geliştirici MongoDB biliyor, OpenSearch bilmiyor; ikinci bir sistem istenmiyor."),
        drest("search", 5, 12, "Ek bir servis küçük mağaza için görünür bir sabit maliyettir."),
    ],
    cands=["doc", "os", "aur"],
    scores={
        "doc": [sc(8, "find dot notation ile iç içe field'lara filtreler (Ö3); sık birleşimlere compound index kurulur ({ category: 1, 'attributes.renk': 1, rating: -1 }) (Ö4). 2 puan kırıldı: 20 field'ın her birleşimine index kurulamaz; bazı birleşimler index'in bir kısmını kullanır ve kalan koşulu document üzerinde test eder."),
                sc(6, "Facet sayıları $match ve $group ile bir aggregation pipeline'dır (Ö6) ve başındaki $match index kullanır. 4 puan kırıldı: her filtre değişiminde her facet için bir pipeline çalışır; sayılar sonuç kümesinin document'ları okunarak hesaplanır."),
                sc(6, "B-tree index bir field sırasını hızlı verir. 4 puan kırıldı: her index tek bir sıradır; serbest birleşimler ve sayım için engine birkaç index'i birleştirmez, ya bir index'i kısmen kullanır ya da document okur."),
                sc(10, "Yeni filtre field'ı sadece yeni document'lara yazılır; index'i istenince kurulur (Ö2). Puan kırılmadı."),
                sc(7, "Filtreli okumalar replica'lara dağılır (Ö8). 3 puan kırıldı: kampanyada saniyede 5.000 filtre ve facet pipeline'ı replica'ların CPU'sunu doldurur; 50 ms her birleşimde garanti değildir."),
                sc(10, "Katalog zaten DocumentDB'de ve kalıcıdır; ayrı bir arama katmanı yoktur. Puan kırılmadı."),
                sc(9, "Var olan cluster ve bilinen API; ikinci bir sistem ve boru hattı yoktur. 1 puan kırıldı: facet yükü için replica sayısını ve index'leri ekip seçer."),
                sc(8, "Var olan cluster kullanılır. 2 puan kırıldı: kampanya için eklenen replica'lar instance saati olarak ödenir.")],
        "os": [sc(10, "Bir sorgu her field birleşimini filtreler, sıralar ve sayfalar; iç içe field'lar da aynı biçimdedir. Puan kırılmadı."),
               sc(10, "Aggregation'lar facet sayılarını aynı sorgunun içinde, doc values üzerinden verir. Puan kırılmadı."),
               sc(10, "Inverted index her field'ı ayrı index'ler ve sorgu anında birleştirir; birleşim başına bir yapı gerekmez. Puan kırılmadı."),
               sc(8, "Dynamic mapping yeni field'ı tanır. 2 puan kırıldı: field'ın type'ı ilk yazmada sabitlenir; yanlış tahmin edilen bir type reindex ister."),
               sc(9, "Shard'lar ve replica'lar filtre yükünü paylaşır; 50 ms filtre ve facet için rahattır. 1 puan kırıldı: kampanya için node'lar önceden eklenir; yeni node'un shard'ları alması zaman ister."),
               sc(8, "Shard replica'ları başka AZ'dedir. 2 puan kırıldı: arama kopyası kaybolursa kataloğun tamamı yeniden index'lenir (saatler)."),
               sc(3, "Yönetilen domain. 7 puan kırıldı: ekip OpenSearch bilmiyor; mapping, shard boyutu ve kataloğu change stream'den besleyen boru hattı ekibin yeni işidir ve iki sistem birbirinden kopabilir."),
               sc(5, "Node'lar saat başına ödenir. 5 puan kırıldı: domain katalog cluster'ına ek olarak bütün gün çalışır.")],
        "aur": [sc(9, "SQL her column'da ve JSONB'nin içinde filtreler, sıralar ve sayfalar. 1 puan kırıldı: iç içe field'lara göre aralık JSON yolu ve cast ister."),
                sc(6, "Facet sayıları GROUP BY ile bir sorgudur. 4 puan kırıldı: her filtre değişiminde her facet için bir GROUP BY çalışır ve sonuç row'larını okur."),
                sc(7, "Planner birkaç B-tree index'ini bitmap ile birleştirebilir; GIN JSONB eşitliklerini index'ler. 3 puan kırıldı: sayım yine row'ları okur ve iç içe aralıklar her field için expression index ister."),
                sc(7, "JSONB yeni field'ı migration'sız alır. 3 puan kırıldı: index'lenecek her iç içe field için yeni bir expression index kurulur."),
                sc(7, "Reader instance'lar okumayı paylaşır. 3 puan kırıldı: kampanyada 5.000 filtre ve GROUP BY reader'ların CPU'sunu doldurur."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(4, "Aurora Lale Market'te çalışır. 6 puan kırıldı: katalog DocumentDB'dedir; arama için Aurora'ya bir kopya ve onu besleyen bir boru hattı gerekir ve filtre sorguları JSONB yollarıyla yeniden yazılır."),
                sc(7, "Var olan cluster'a reader eklenir. 3 puan kırıldı: kampanya reader'ları ACU olarak ödenir.")],
    },
    h2h={
        "os": "Search engine (OpenSearch) ile kafa kafaya. Bu kartta R1'i OpenSearch kazanır: inverted index her field'ı ayrı index'ler ve sorgu anında birleştirir, facet sayıları aynı sorgunun içinde gelir ve R1'in 42 puanının 40,8'ini alır; DocumentDB 30,4 alır. Bu, engine'in açık bir üstünlüğüdür ve sayfanın dürüst sonucudur. "
              "Toplamı DocumentDB'ye veren R4 ve R5'tir: katalog zaten DocumentDB'dedir, ekip OpenSearch bilmez ve ikinci bir sistem, onu besleyen bir change stream boru hattı ve bütün gün çalışan node'lar ister; fark sadece 0,8 puandır. Bugün kurulan compound index'ler boşa gitmez: kataloğun kendi ekranları onları kullanmaya devam eder. "
              "Bu yakın yarış bir uyarıdır: metin araması (yazım hatası toleransı, relevance) istendiği gün R1'e yeni bir satır girer, DocumentDB'nin o satırdaki puanı çok düşüktür ve karar çevrilir. "
              "Hangi koşul değişseydi OpenSearch seçilirdi: metin araması bu çeyrekte istenseydi ya da filtre field'ları 50'yi geçseydi; o gün katalog DocumentDB'de kalır ve arama kopyası change stream ile OpenSearch'e akar.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora'nın planner'ı birkaç index'i bir sorguda birleştirebilir (bitmap) ve SQL her filtreyi ve GROUP BY ile facet'i cevaplar; R1'de DocumentDB ile neredeyse eşittir. "
               "Ama katalog Aurora'da değildir: arama için kataloğun bir kopyası Aurora'ya yazılır, bir boru hattı onu güncel tutar ve sorgular JSONB yollarıyla yeniden yazılır. Bu R4'te altı puanlık bir kayıptır ve Aurora'nın engine kazancını siler. Facet sayıları her iki engine'de de sonuç row'larını okur; OpenSearch'ün doc values'u bu işte ikisinden de iyidir. "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: katalog zaten Aurora'da olsaydı (Aurora sayfasının kart 2'sindeki gibi) ve filtreler birkaç sabit field olsaydı.",
    },
    verdict="Karar: DocumentDB {doc}, OpenSearch {os}, Aurora PostgreSQL {aur}. Bu yakın bir yarıştır ve R1'i OpenSearch kazanır; toplamı DocumentDB'ye var olan cluster, ekibin bildiği API ve ikinci bir sistemin olmaması verir (R4, R5). "
            "DocumentDB seçtiğimizde artımız: filtreler kataloğun kendisinde çalışır, kopya ve boru hattı yoktur, yeni filtre field'ı bir index'tir. "
            "Eksimiz: sık birleşimlere compound index kurarız ve 64 index sınırını izleriz; facet pipeline'larını replica'lara göndeririz ve kampanyadan önce replica ekleriz; facet sayılarını birkaç saniye cache'lemek replica yükünü düşürür; 50 ms'yi her birleşimde garanti edemeyiz. "
            "Aynı engine'in shard'lı biçimi (elastic cluster) bu kartta aday değildir: sorun yazma değil filtre ve sayım algoritmasıdır ve shard'lamak onu değiştirmez. "
            "Bir koşul değişseydi: metin araması istendiği gün doğru cevap ikisi birlikte çalışmaktır: katalog DocumentDB'de, arama kopyası change stream ile OpenSearch'te."))

# ------------------------------------------------------------------ 9. session documents (ElastiCache wins, DocumentDB is third)
DOCDB_W.append(wusecase("sessions", 9, sim="w_sessions",
    title="Oturum document'ları: teklif sihirbazının adımları",
    key="Collection: sessions. Document: _id (session id), user_id, wizard (iç içe: araç, sürücüler, teminatlar), expires_at. TTL index.",
    story=dstory("sessions"),
    wnote="R1 toplam 46: tam süre sonu (YD 14) ve 2 ms'nin altında okuma için engine'in depolama algoritması (DA 12) oturumun kendisidir. "
          "R2 20 ile ikinci: saniyede 15.000 okuma ve 5.000 yazma. Oturum kaybı para kaybı olmadığı için R3 10'da kalır.",
    rows=[
        row("EY", 10, "Her HTTP isteği oturumu okur; analiz soruları günde birkaç kezdir.",
            "Session id ile tek okuma; günde birkaç kez \"üçüncü adımda bırakılan oturumlar\" gibi oturumun içine göre bir analiz sorusu.",
            "Oturum okuması yavaşsa her sayfa yavaştır; analiz sorusu cevaplanamazsa pazarlama sihirbazın nerede kaybettiğini bilemez."),
        row("YD", 14, "Süresi dolmuş oturumun kabulü paylaşılan bilgisayarda bir sonraki kişiyi önceki teklifte bırakır.",
            "Oturum 30 dakika hareketsizlikten sonra okunmamalı ve her istekte süresi yenilenmeli.",
            "Süresi dolmuş oturum okunursa bir sonraki ziyaretçi başkasının teklifini görür."),
        row("DA", 12, "Oturum okuması her isteğin önündedir; okumanın her milisaniyesi her sayfanın gecikmesine eklenir.",
            "Okuma 2 ms'nin altında dönmeli; değer bellekten okunmalı.",
            "Diskten gelen her okuma sayfanın gecikmesine eklenir; tepe saatte kuyruk büyür."),
        row("OY", 10, "Sihirbazın her adımı oturumun bir kısmını yazar ve her istek süreyi yeniler.",
            "Sihirbaz adımının iç içe field'ı ve süre tek yazmada değişmeli; oturum baştan yazılmamalı.",
            "Her adımda bütün oturum yeniden yazılırsa iki sekmenin adımları çarpışır."),
        drest("sessions", 2, 20, "Saniyede 15.000 okuma ve 5.000 yazma; tepe öğle ve akşam."),
        drest("sessions", 3, 10, "Kaybolan oturum yeni bir sihirbazdır; müşteri sinirlenir ama para kaybolmaz."),
        drest("sessions", 4, 12, "Oturum kodu küçüktür; ikinci bir sistem kazancı açıksa kabul edilir."),
        drest("sessions", 5, 12, "Saniyede 5.000 süre yenilemesi sürekli bir maliyettir."),
    ],
    cands=["ec", "ddb", "doc"],
    scores={
        "ec": [sc(7, "GET ya da HGETALL session id ile tek okumadır. 3 puan kırıldı: oturumun içine göre analiz sorusu yoktur; bütün key'leri SCAN etmek ya da oturumları ayrıca dışa yazmak gerekir."),
               sc(10, "EXPIRE süreyi tam anında uygular ve her istekte yenilenir; süresi dolmuş oturum okunamaz. Puan kırılmadı."),
               sc(10, "Değer bellektedir; okuma milisaniyenin altındadır. Puan kırılmadı."),
               sc(8, "HSET sihirbazın bir adımını tek field olarak yazar ve EXPIRE aynı pipeline'dadır. 2 puan kırıldı: iç içe sürücü listesi bir hash field'ında JSON metni olarak saklanır ve uygulama onu bütün olarak yazar."),
               sc(9, "Serverless yükle ölçeklenir. 1 puan kırıldı: ani bir tepede ölçeklenme kısa bir gecikmeyle gelir."),
               sc(4, "Serverless veriyi birkaç AZ'de kopyalar; bir node arızası bütün oturumları silmez. 6 puan kırıldı: kalıcı bir yazma log'u yoktur; oturumun tek yeri bellektir ve bir arızada son yazmalar kaybolabilir. Kart bu kaybı kabul ettiği için ElastiCache sayfasının kuralıyla 4 puan."),
               sc(8, "Yönetilen servis; oturum kodu küçüktür. 2 puan kırıldı: MongoDB driver'ı ile yazılmış oturum katmanı yeni bir istemciyle yeniden yazılır ve yanında ikinci bir sistem işletilir."),
               sc(8, "ECPU ve bellekteki GB-saat ödenir. 2 puan kırıldı: 5 KB'lık oturumlar bellekte tutulur ve bellek GB başına diskten pahalıdır.")],
        "ddb": [sc(7, "GetItem session id ile tek okumadır. 3 puan kırıldı: oturumun içine göre analiz sorusu bir Scan ve filtredir ya da bir dışa aktarmadır."),
                sc(6, "TTL alanı süresi dolan value'yu siler. 4 puan kırıldı: silme genellikle birkaç gün içinde olur; \"süresi dolan okunmamalı\" isteği ancak uygulamanın her okumada expires_at'i şimdiki zamanla karşılaştırmasıyla karşılanır (DynamoDB sayfasının oturum kartındaki aynı kırılım)."),
                sc(6, "SSD'den tek haneli milisaniye. 4 puan kırıldı: 2 ms hedefi her okumada tutmaz; DAX bunu düzeltir ama ayrı bir cache katmanıdır (aynı 2 ms sınırında DocumentDB de 6 alır; DynamoDB sayfasında 1 ms sınırı 5, 5 ms sınırı 6 puandır)."),
                sc(10, "UpdateItem SET wizard.step ve expires_at tek yazmadır. Puan kırılmadı."),
                sc(10, "On-demand mod 20.000 isteği partition'lara dağıtır. Puan kırılmadı."),
                sc(10, "Birkaç AZ'de kalıcıdır. Puan kırılmadı."),
                sc(8, "Serverless: sunucu yoktur. 2 puan kırıldı: oturum katmanı yeni bir API ile yeniden yazılır."),
                sc(6, "İstek başına ödeme. 4 puan kırıldı: saniyede 5.000 süre yenilemesi 5 KB'lık value'lar için sürekli bir yazma birimi faturasıdır.")],
        "doc": [sc(10, "find({ _id }) tek okumadır (Ö1); \"üçüncü adımda bırakılan oturumlar\" iç içe field'a göre bir filtredir (Ö3). Puan kırılmadı."),
                sc(4, "TTL index süresi dolan document'ı arka planda siler. 6 puan kırıldı: silme \"best effort\"tür ve belirli bir sürede garanti değildir; uygulama her okumada expires_at'i karşılaştırır."),
                sc(6, "Working set bellekteyse okuma hızlıdır. 4 puan kırıldı: engine disk tabanlıdır; bellekte olmayan bir oturum storage'dan gelir ve 2 ms her okumada tutmaz."),
                sc(10, "updateOne ile $set: { 'wizard.step3': …, expires_at } tek atomik yazmadır (Ö5). Puan kırılmadı; yenilemelerin ve TTL silmelerinin I/O ücreti R5'te sayıldı."),
                sc(4, "Okumalar replica'lara dağılır (Ö8). 6 puan kırıldı: saniyede 5.000 yazma tek primary'den geçer; replica okuması kısa süre geride olabilir ve oturum her istekte kendi yazmasını görmelidir, bu yüzden okumalar da primary'ye gider."),
                sc(10, "Cluster volume üç AZ'de altı kopya tutar. Puan kırılmadı."),
                sc(7, "Var olan cluster ve driver; ikinci bir sistem yoktur. 3 puan kırıldı: saniyede 5.000 yazma için primary'nin instance sınıfını ekip büyütür ve izler (kart 4'teki aynı iş, daha küçük ölçekte); tepenin karşılanması R2'de sayıldı."),
                sc(4, "Instance saat başına ve I/O başına ödenir. 6 puan kırıldı: saniyede 5.000 yenileme ve TTL silmeleri sürekli I/O'dur; Standard modelde oturum katmanı faturanın en büyük kalemi olur.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. Bu bir yakın yarıştır (fark 2,8 puan). DynamoDB kalıcıdır, ölçeği ayarsızdır ve tek yazmada sihirbaz adımını ve süreyi değiştirir; R2 ve okuma/yazma şeklinde ElastiCache'e eşit ya da öndedir, R3'te ise açık farkla öndedir: ElastiCache Serverless'ın kalıcı log'u yoktur. "
               "Ama oturumun iki engine sorusunda geride kalır: süre sonu tam anında değildir (TTL genellikle birkaç gün içinde siler ve uygulama her okumada süreyi kontrol eder) ve SSD'den gelen okuma 2 ms hedefini her zaman tutmaz. R5'te de saniyede 5.000 yenileme sürekli bir yazma faturasıdır. "
               "Bu kartta kalıcılığın ağırlığı düşüktür, çünkü kaybolan oturum para değil yeni bir sihirbazdır. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: oturum kaybı pahalı olsaydı (ödeme adımı oturumda olsaydı), gecikme hedefi 10 ms olsaydı ve ekip bellek içi bir sistem işletmek istemeseydi.",
        "doc": "Document (DocumentDB) ile kafa kafaya. Bu kartta bu sayfanın servisi üçüncüdür ve net kaybeder. DocumentDB'nin tek güçlü satırı erişim yoludur: oturum tek document'tır ve pazarlamanın \"üçüncü adımda bırakılan oturumlar\" sorusu bir filtredir; ElastiCache bunu yapamaz. "
               "Ama oturumun kalbi olan iki engine sorusunda zayıftır: TTL silmesi \"best effort\"tür ve süresi dolmuş oturum okunabilir, engine disk tabanlıdır ve 2 ms her okumada tutmaz. R2'de saniyede 5.000 yazma tek primary'den geçer ve okumalar da kendi yazmasını görmek için primary'ye gider; R5'te bu yenilemeler ve TTL silmeleri sürekli I/O'dur. "
               "Ekibin ilk tercihi mevcut cluster'a bir sessions collection'ı eklemekti; bu kart o tercihin bedelini gösterir. "
               "Hangi koşul değişseydi DocumentDB seçilirdi: oturum sayısı saniyede birkaç yüz isteğe inseydi, süre sonu dakikalar kadar esnek olsaydı ve oturumun içine göre analiz ana iş olsaydı.",
    },
    verdict="Karar: ElastiCache (Valkey) {ec}, DynamoDB {ddb}, DocumentDB {doc}. Bu bir yakın yarıştır. Kararı R1'in yaşam döngüsü ve depolama algoritması satırları verir: tam anında süre sonu ve bellekten okuma bellek içi engine'in tanımıdır; DynamoDB farkın çoğunu R3'te kalıcılığıyla geri alır. "
            "Yine de DocumentDB seçersek artımız: ikinci bir sistem yoktur ve oturumun içine göre analiz bir filtredir. "
            "Eksimiz: her okumada expires_at'i biz karşılaştırırız; primary'yi 5.000 yazma için büyütürüz ve okumaları da primary'ye göndeririz; TTL silmelerinin ve yenilemelerin I/O'sunu öderiz; 2 ms her okumada tutmaz. "
            "Doğru mimari ikisinin birlikte çalışmasıdır: canlı oturum ElastiCache'te, tamamlanan teklif DocumentDB'de bir document olarak; pazarlamanın analiz sorusu tamamlanmayan oturumların DocumentDB'ye yazılan bir özetinden cevaplanır. "
            "Aynı Valkey engine'ini çalıştıran MemoryDB kalıcı bir log ekler; oturum kaybı pahalı olsaydı ElastiCache'in yerine o seçilirdi. "
            "Bir koşul değişseydi: oturum kaybı pahalı olsaydı MemoryDB ya da DynamoDB öne geçerdi."))

# ------------------------------------------------------------------ 10. feature flags and settings
DOCDB_W.append(wusecase("flags", 10,
    title="Feature flag'ler ve uygulama ayarları",
    key="Collection: flags. Document: _id (flag adı), enabled, rules (array: segment, yüzde, ülke), variants (iç içe), version, history.",
    story=dstory("flags"),
    wnote="R1 toplam 40: sürüm koşullu değişiklik ve geçmiş (TA 12) ile 10 saniyede yayılma (YD 12) bu sistemin kurallarıdır. "
          "R3 20 ve R4 20 ile ikinci sırada: yanlış bir flag mağazayı kapatır ve geri alınabilmelidir; şirketin zaten bir DocumentDB cluster'ı var ve en düşük operasyon istenir. Hacim çok küçük olduğu için R2 5'tedir.",
    rows=[
        row("VM", 10, "Her flag'in kuralları farklıdır ve her hafta yeni kural türü gelir.",
            "Bir flag yüzde, ülke listesi ya da segment kurallarından birini ya da birkaçını, varyantlarıyla birlikte tek bir bütün olarak taşımalı; yeni kural türü migration istememeli.",
            "Kural türleri sabit column'lara zorlanırsa her yeni kural türü bir migration ve boş column'lardır."),
        row("TA", 12, "İki kişinin aynı flag'i aynı anda değiştirmesi mağazayı yanlış duruma sokar.",
            "Bir flag \"version = 12 ise\" koşuluyla değişmeli ve aynı yazmada geçmişe eklenmeli; koşul yanlışsa hiçbir şey yazılmamalı.",
            "Koşulsuz yazmada ikinci değişiklik birincisini ezer; geçmiş ayrı yazılırsa \"kim kapattı\" sorusu yanlış cevaplanır."),
        row("YD", 12, "Değişiklik 10 saniye içinde 40 servise ulaşmalı.",
            "Her flag değişikliği 10 saniye içinde servislere bir olay olarak akmalı; geçmiş denetim için saklanmalı.",
            "Değişiklik geç yayılırsa servislerin bir kısmı yeni, bir kısmı eski davranışla çalışır."),
        row("EY", 6, "Sorular basittir: tek flag, bütün flag'ler ve bir segment silinmeden önce sorulan bir denetim sorusu.",
            "Flag adı ile tek okuma, \"bütün flag'ler\" tek sorgu ve \"premium segmentini hedefleyen flag'ler\" (kuralların içine göre) tek sorgu.",
            "Servisler başlangıçta bütün flag'leri okuyamazsa varsayılan davranışla açılır."),
        drest("flags", 2, 5, "Saniyede 500 okuma ve günde 50 yazma; ölçek belirleyici değildir."),
        drest("flags", 3, 20, "Flag'ler mağazanın davranışıdır; kaybı ya da geri alınamayan yanlış değişiklik kesintidir."),
        drest("flags", 4, 20, "Dört kişilik platform ekibi ve var olan bir DocumentDB cluster'ı: en düşük operasyon istenir."),
        drest("flags", 5, 15, "Veri birkaç MB; ayrı bir database'in minimum kapasitesi faturanın tamamıdır."),
    ],
    cands=["doc", "ddb", "aur"],
    scores={
        "doc": [sc(10, "Flag bir document'tır: rules bir array, variants bir embedded document; her kural türü kendi field'larını taşır (Ö2). Puan kırılmadı."),
                sc(9, "Filtredeki version: 12 koşulu, $set ve $inc: { version: 1 } tek atomik yazmadır; koşul yanlışsa matchedCount 0 döner (Ö5). 1 puan kırıldı: geçmiş sınırsız büyüdüğü için flag'in içine gömülmez (A3), flag_history collection'ındadır; değişiklik ve geçmiş kaydı birlikte bir transaction ister."),
                sc(9, "Change stream her değişikliği saniyeler içinde verir (Ö7). 1 puan kırıldı: tutulma süresi varsayılan üç saattir; tüketici daha uzun durursa servisler 30 saniyelik okumalarıyla yetişir."),
                sc(10, "_id ile tek okuma, 300 document'ın find'ı ve { 'rules.segment': 'premium' } filtresi (Ö1, Ö3). Puan kırılmadı."),
                sc(10, "Saniyede 500 okuma var olan cluster için çok küçüktür. Puan kırılmadı."),
                sc(10, "Cluster volume üç AZ'de altı kopya tutar; point-in-time restore yanlış bir toplu değişikliği geri alır ve flag_history her flag'in önceki hâlini taşır. Puan kırılmadı."),
                sc(9, "Var olan cluster'a bir collection eklenir; ekip API'yi biliyor. 1 puan kırıldı: change stream'i servislere yayan tüketici ekibin işlettiği bir süreçtir."),
                sc(9, "Var olan cluster'da bir collection: yeni bir minimum kapasite yoktur. 1 puan kırıldı: change stream açık olduğu sürece küçük bir log I/O'su ödenir.")],
        "ddb": [sc(10, "Flag map ve list tipleriyle tek value'dur. Puan kırılmadı."),
                sc(9, "UpdateItem bir ConditionExpression ile version'ı test eder. 1 puan kırıldı: geçmiş sınırsız büyüdüğü için ayrı value'lardadır; değişiklik ve geçmiş kaydı birlikte TransactWriteItems ister (DocumentDB ile aynı mekanizma)."),
                sc(9, "Streams her değişikliği verir ve Lambda ile servislere yayılır. 1 puan kırıldı: kayıtlar 24 saat tutulur."),
                sc(8, "GetItem tek flag'i, Scan 300 flag'i okur. 2 puan kırıldı: \"bütün flag'ler\" ve segment sorusu bir Scan ve filtredir; list elemanına index kurulamaz, ama 300 value için Scan ucuzdur."),
                sc(10, "On-demand mod bu küçük yükü karşılar. Puan kırılmadı."),
                sc(10, "Birkaç AZ'de saklanır; point-in-time recovery vardır. Puan kırılmadı."),
                sc(6, "Serverless: sunucu yoktur. 4 puan kırıldı: var olan DocumentDB cluster'ının yanına ikinci bir database türü, yeni bir API ve ayrı izleme gelir."),
                sc(10, "İstek başına ödeme; bu yükte fatura neredeyse sıfırdır. Puan kırılmadı.")],
        "aur": [sc(7, "Flag bir row, kurallar JSONB'dir. 3 puan kırıldı: kurallar şemasız JSON olarak type'lı column'ların yanında yaşar."),
                sc(10, "UPDATE … WHERE version = 12 ve INSERT INTO history tek transaction'dır. Puan kırılmadı."),
                sc(6, "LISTEN/NOTIFY ya da logical replication değişikliği dışarı verir. 4 puan kırıldı: NOTIFY kalıcı değildir ve dinleyen yoksa kaybolur; logical replication bir tüketici ve ayar ister."),
                sc(9, "Primary key ile tek okuma, SELECT * ile bütün flag'ler. 1 puan kırıldı: segment sorusu JSONB'nin içinde bir yol ifadesidir."),
                sc(10, "Bu yük tek writer için çok küçüktür. Puan kırılmadı."),
                sc(10, "Üç AZ'de altı kopya, point-in-time restore. Puan kırılmadı."),
                sc(5, "Yedek ve yama yönetilir. 5 puan kırıldı: şirketin Aurora'sı yoktur; flag'ler için yeni bir cluster işletilir."),
                sc(6, "Serverless v2 küçük kalır. 4 puan kırıldı: yeni bir cluster'ın minimum ACU'su bu birkaç MB'lık iş yükünün faturasının tamamıdır.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. R1'de iki aday neredeyse eşittir: DynamoDB'de flag tek bir value'dur, ConditionExpression sürümü korur, geçmiş bir transaction ile ayrı value'lara yazılır ve Streams ile Lambda değişikliği servislere yayar. R5'te DynamoDB öndedir: bu yükte fatura neredeyse sıfırdır. "
               "Kararı R4 verir: şirketin zaten bir DocumentDB cluster'ı vardır ve dört kişilik platform ekibi flag'ler için ikinci bir database türü, yeni bir API ve ayrı izleme istemez. DocumentDB'de flag sistemi var olan cluster'da bir collection'dır. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: şirkette bir DocumentDB cluster'ı olmasaydı ve flag sistemi sıfırdan kurulsaydı; o zaman DynamoDB'nin neredeyse sıfır faturası ve sunucusuz operasyonu öne geçerdi. "
               "AWS AppConfig bu kartta aday değildir: flag'leri ve ayarları aşamalı yayın ve geri almayla sunar, ama bir database değildir; \"premium segmentini hedefleyen flag'ler\" gibi kuralların içine göre denetim sorusunu cevaplamaz.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora'nın gücü kuraldadır: UPDATE … WHERE version = 12 ve geçmişe INSERT tek transaction'dır ve SQL her soruyu cevaplar. "
               "Ama iki satırda geride kalır. Yayılmada NOTIFY kalıcı değildir ve dinleyen servis yoksa kaybolur; logical replication bir tüketici ve ayar ister. Servis tasarımında şirketin Aurora'sı yoktur: birkaç MB'lık bir iş yükü için yeni bir cluster işletilir ve minimum ACU faturanın tamamıdır. Kural türleri de JSONB'de şemasız yaşar ve type'lı column'larla yan yana durur. "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: şirketin ana database'i Aurora olsaydı ve flag değişiklikleri sipariş ya da fiyat kayıtlarıyla aynı transaction'da yazılsaydı.",
    },
    verdict="Karar: DocumentDB {doc}, DynamoDB {ddb}, Aurora PostgreSQL {aur}. Kararı R4 ve R1'in atomiklik satırı verir: sürüm koşullu değişiklik tek atomik yazmadır, geçmiş aynı transaction'dadır ve flag sistemi var olan cluster'da bir collection'dır. "
            "DocumentDB seçtiğimizde artımız: yeni kural türü migration istemez, iki kişinin değişikliği çarpışmaz, geçmiş flag_history'de transaction ile yazılır, segment sorusu bir filtredir, change stream değişikliği saniyeler içinde yayar ve point-in-time restore yanlış bir değişikliği geri alır. "
            "Eksimiz: change stream tüketicisini biz işletiriz; tüketici durursa servisler 30 saniyelik okumalarıyla yetişir, bu yüzden periyodik okumayı kaldırmayız; flag'ler cluster'ı diğer iş yükleriyle paylaşır ve cluster'ın bakım penceresi flag sistemini de etkiler, servisler bu yüzden son okudukları flag'leri bellekte tutar. "
            "Aynı engine'in shard'lı biçimi (elastic cluster) bu kartta aday değildir: 300 document için shard anlamsızdır ve elastic cluster'da change stream yoktur. "
            "Bir koşul değişseydi: şirkette DocumentDB cluster'ı olmasaydı DynamoDB öne geçerdi; segment sorusu gerekmeseydi ve aşamalı yayın istenseydi AWS AppConfig (database değil, yapılandırma servisi) düşünülürdü; o zaman flag'ler AppConfig'te, denetim geçmişi bir database'te, ikisi birlikte çalışır."))

USECASES_W["docdb"] = DOCDB_W
PAGE_SVC["docdb"] = "doc"


# ================================================================ Keyspaces (Amazon Keyspaces for Apache Cassandra), model 2
# The ten M2 cards of the Turkish Keyspaces page in the weighted model. The stories come from model 1 (KS_USECASES in
# e2e_usecases.py, kept for the old English page); every row, weight, point and reason is new. Facts (official sources, hedges kept):
#  - Reads LOCAL_ONE or LOCAL_QUORUM, all writes LOCAL_QUORUM, replication factor three over several AZs:
#    https://docs.aws.amazon.com/keyspaces/latest/devguide/consistency.html, https://aws.amazon.com/keyspaces/pricing/
#  - TTL: expired data "no longer returned in queries", removed from storage "typically within 10 days", expired data counts toward
#    metered storage until removed, "One TTL delete is consumed per KB": https://docs.aws.amazon.com/keyspaces/latest/devguide/TTL.html,
#    https://aws.amazon.com/blogs/database/announcing-amazon-keyspaces-time-to-live-ttl-general-availability/
#  - No CREATE INDEX, no materialized view, no aggregate functions, no UDF, no TRUNCATE; "Security settings: Replaced by IAM";
#    compaction and compression settings "Not applicable": https://docs.aws.amazon.com/keyspaces/latest/devguide/cassandra-apis.html
#  - IAM cassandra:Modify "Grants permission to INSERT, UPDATE or DELETE data in a table" (one action for the three):
#    https://docs.aws.amazon.com/service-authorization/latest/reference/list_keyspaces.html
#  - LWT: no additional charge, a failed condition still consumes write units: https://docs.aws.amazon.com/keyspaces/latest/devguide/lightweight_transactions.html;
#    Apache Cassandra IF NOT EXISTS "non-negligible performance cost, because Paxos is used": https://cassandra.apache.org/doc/latest/cassandra/developing/cql/dml.html
#  - CDC streams: 24 hours, consumed with the Keyspaces Streams API or the KCL: https://docs.aws.amazon.com/keyspaces/latest/devguide/cdc_how-to-use-kcl.html
#  - Per partition 3,000 RCU and 1,000 WCU, sustained hot partitions may be split: https://docs.aws.amazon.com/keyspaces/latest/devguide/bp-partition-key-design.html
#  - On-demand "scales up to any previously reached traffic level instantly"; PITR 35 days: https://aws.amazon.com/keyspaces/pricing/
#  - Timestream for InfluxDB: instance classes db.influx.medium to 24xlarge, storage 20 to 15,360 GiB, SINGLE_AZ or WITH_MULTIAZ_STANDBY:
#    https://docs.aws.amazon.com/ts-influxdb/latest/ts-influxdb-api/API_UpdateDbInstance.html; Timestream for LiveAnalytics is closed to
#    new customers since 2025-06-20: https://docs.aws.amazon.com/timestream/latest/developerguide/AmazonTimestreamForLiveAnalytics-availability-change.html
#  - MemoryDB: microsecond reads, single-digit millisecond writes, Multi-AZ transactional log: https://docs.aws.amazon.com/memorydb/latest/devguide/servicename-feature-overview.html
from .e2e_usecases import KS_USECASES as _KM1  # noqa: E402

_KOLD = {uc["id"]: uc for uc in _KM1}


def kstory(uid):
    return _KOLD[uid]["story"][1]


def kreq(uid, i, part):
    """The model 1 text of R(i+1) of a Keyspaces card, without the model 1 'must' sentences."""
    t = _KOLD[uid]["reqs"][i][part][1]
    return re.sub(r"\s*(Bu yüzden )?R\d bu kartta zorunludur\.|\s*Bu gereksinim bu kartta zorunludur\.", "", t)


KEYSPACES_W = []

# ------------------------------------------------------------------ 1. activity history (Lale Market)
KEYSPACES_W.append(wusecase("activity", 1,
    title="Kullanıcı başına aktivite geçmişi (Lale Market)",
    key="Partition key: user_id. Clustering column: event_time (en yeni önce), event_id. Row: event türü, ürün, detay. Table varsayılan TTL'i 7 gün.",
    story=kstory("activity"),
    wnote="R1 toplam 50: iki ekranın sorusu ve 7 günlük ömür engine'in partition ve sıra modeline dayanır; en ağır alt madde erişim yoludur (18). "
          "R2 20 ile ikinci: kampanya akşamı yazmalar 12 katına çıkar ve yazma sayfa isteğinin içindedir. R4 14: veri ekibinin çalışan gece işi bu karta özgü bir bağdır.",
    rows=[
        row("EY", 18, "\"Son baktıkların\" şeridi her ürün sayfasında, \"Aktivitem\" her açılışta bu soruyu sorar.",
            kreq("activity", 0, "want"), kreq("activity", 0, "why")),
        row("OY", 12, "Saniyede 1.200, tepede 15.000 event yazılır; yazmanın biçimi işin büyük kısmıdır.",
            "Her event bir kez eklenir ve hiç değişmez; yazma önce okumamalı. Aynı milisaniyedeki iki event birbirinin üzerine yazmamalı.",
            "Yazma önce okursa istek sayısı iki katına çıkar. İki event aynı key'e düşerse biri sessizce kaybolur ve geçmiş eksik görünür."),
        row("YD", 12, "Geçmişin değeri 7 gündür; silme işi kimsenin yazmak istemediği bir iştir.",
            "Event'ler 7 gün sonra kendiliğinden kaybolmalı ve 7 günden eski bir event \"Aktivitem\"de görünmemeli; silme için ayrı bir iş yazılmamalı.",
            "Silme işi yazılırsa o da işletilir ve bozulur. Eski event'ler ekranda kalırsa kullanıcı bir hafta önce baktığı ürünü \"son baktıkların\"da görür."),
        row("DA", 8, "Okuma azdır ama her sayfada vardır; ağırlık bu yüzden orta.",
            "Bir kullanıcının en yeni 40 event'i, table iki milyon kullanıcıya büyüse de, sıralama yapmadan tek bir bitişik okuma olmalı.",
            "Event'ler diskte yazma sırasına göre dağınık durursa 40 event 40 ayrı okumadır; sayfa table büyüdükçe yavaşlar."),
        row("R2", 20, "Kampanya akşamı yazma 12 katına çıkar ve yazma sayfa isteğinin içindedir.", kreq("activity", 1, "want"), kreq("activity", 1, "why")),
        row("R3", 8, "Birkaç event'in kaybı önerileri bozmaz; ağırlık bu yüzden düşük.", kreq("activity", 2, "want"), kreq("activity", 2, "why")),
        row("R4", 14, "Veri ekibinin gece işi bugün çalışıyor ve bu karta özgü bir bağdır.", kreq("activity", 3, "want"), kreq("activity", 3, "why")),
        row("R5", 8, "Event küçük ve trafik dalgalı; faturayı model belirler, büyüklük değil.", kreq("activity", 4, "want"), kreq("activity", 4, "why")),
    ],
    cands=["ks", "ddb", "aur"],
    scores={
        "ks": [sc(10, "Partition key user_id, clustering column event_time DESC: \"en yeni N\" partition'ın başı, iki saat arası tek bir dilimdir (Ö1, Ö3). Puan kırılmadı."),
               sc(10, "INSERT okumadan yazar (upsert, Ö1); event_id ikinci clustering column olduğu için aynı milisaniyedeki iki event ayrı row'dur. Puan kırılmadı."),
               sc(10, "Table varsayılan TTL'i 604.800 saniye; süresi dolan row okumada hiç görünmez ve silme işi yoktur (Ö6). Puan kırılmadı."),
               sc(10, "Row'lar partition'ın içinde yazma anında clustering sırasıyla durur; 40 event tek bir bitişik okumadır (Ö3). Puan kırılmadı."),
               sc(10, "On-demand mod daha önce ulaşılan seviyeye anında çıkar ve yazmalar partition'lara dağılır; ısıtılmış bir table kampanya tepesini taşır (Ö2). Puan kırılmadı."),
               sc(10, "Üç kopya, birkaç Availability Zone; point-in-time recovery son 35 gün. Puan kırılmadı."),
               sc(9, "Sunucu yok; veri ekibinin Spark Cassandra Connector ve CQL ile yazdığı gece işi olduğu gibi çalışır. 1 puan kırıldı: canlı table'ın warm throughput'u saniyede 4.000 yazma birimidir; ilk 15.000'lik kampanyadan önce table bir kez ısıtılır (bir kapasite ayarı)."),
               sc(9, "İstek başına ödeme dalgalı trafiğe uyar. 1 puan kırıldı: TTL'in sildiği her event ayrıca bir TTL delete olarak ödenir.")],
        "ddb": [sc(10, "Partition key kullanıcı, sort key zaman; Query en yeni N'i ve zaman aralığını tek istekle verir. Puan kırılmadı."),
                sc(10, "PutItem okumadan yazar; sort key'e event id'si eklenince iki event ayrı kalır. Puan kırılmadı."),
                sc(8, "TTL attribute'u her item'a yazılır ve silme yazma birimi harcamaz. 2 puan kırıldı: süresi dolan item'lar genellikle birkaç gün içinde silinir ve o zamana kadar okumada görünür; \"Aktivitem\" okumada süre alanını kendisi süzmelidir."),
                sc(10, "Aynı partition key'in item'ları sort key sırasıyla bir arada durur; okuma bitişiktir. Puan kırılmadı."),
                sc(10, "On-demand mod ısıtılmış bir table ile tepeyi taşır ve partition'lar yazmaları dağıtır. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır; point-in-time recovery. Puan kırılmadı."),
                sc(5, "DynamoDB Lale Market'te sepet için zaten çalışır; yeni bir servis değildir. 5 puan kırıldı: veri ekibinin Spark Cassandra Connector ve CQL ile yazdığı gece işi DynamoDB'nin API'ına yeniden yazılır ve yeniden test edilir; ilk büyük kampanyadan önce warm throughput yükseltilir."),
                sc(10, "İstek başına ödeme; TTL silmesi ücretsizdir. Puan kırılmadı.")],
        "aur": [sc(10, "(user_id, event_time DESC) üzerinde bir B-tree index ve LIMIT; her iki soru SQL ile sorulur. Puan kırılmadı."),
                sc(7, "INSERT okumadan ekler. 3 puan kırıldı: her event heap'e, index'e ve write-ahead log'a yazılır; her küçük ekleme üç ayrı yazmadır (writer'ın yükü R2'de sayıldı)."),
                sc(6, "Günlük partition'lar ve en eski partition'ın düşürülmesi 7 günü sınırlar. 4 puan kırıldı: kendiliğinden süre sonu yoktur; partition bakımı zamanlanmış bir iştir (pg_partman, pg_cron) ve iş durursa eski event'ler kalır (Aurora sayfasının kademesi: partition düşüren iş 4 puan)."),
                sc(8, "Index en yeni 40 event'i sırayla bulur. 2 puan kırıldı: row'lar heap'te yazma sırasıyla durur, kullanıcıya göre değil; 40 event çoğu zaman 40 ayrı page okumasıdır."),
                sc(5, "Bütün yazmalar checkout'u da taşıyan tek writer'dan geçer. 5 puan kırıldı: kampanya akşamı saniyede 15.000 ekleme aynı writer'da sipariş yazmalarıyla yarışır (Aurora sayfasının tek writer tablosu: 5.000–20.000, checkout ile aynı tepede 5 puan)."),
                sc(10, "Altı kopya, üç AZ. Puan kırılmadı."),
                sc(6, "Aurora Lale Market'te zaten çalışır; yeni bir table eklenir. 4 puan kırıldı: gece işi JDBC'ye yeniden yazılır ve event yükünün checkout cluster'ındaki etkisi izlenir."),
                sc(6, "Var olan cluster'a eklenir. 4 puan kırıldı: kampanya tepesi için ACU aralığı yükseltilir ve günde yaklaşık 100 milyon eklemenin I/O'su ödenir.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. Engine uyumunda iki servis neredeyse eşittir: ikisi de veriyi partition key'in hash'iyle dağıtır, kullanıcının event'lerini zaman sırasıyla bir arada tutar ve yazmadan önce okumaz. "
               "Tek engine farkı süre sonudur: DynamoDB süresi dolan item'ı genellikle birkaç gün içinde siler ve o zamana kadar okumada gösterir, Keyspaces ise süresi dolan row'u hiç döndürmez. "
               "DynamoDB'nin dürüst üstünlüğü servis tarafındadır: Lale Market'te zaten çalışır ve TTL silmesi ücretsizdir. "
               "Kararı R4 verir: veri ekibinin gece işi CQL ile yazılmıştır ve DynamoDB'de yeniden yazılması gerekir. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: gece işi olmasaydı ya da veri ekibi işi zaten yeniden yazmayı planlasaydı; o zaman R4 eşitlenir, ücretsiz TTL silmesi R5'i DynamoDB'ye verir ve fark DynamoDB lehine döner.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora Lale Market'te siparişler için zaten çalışır ve SQL her soruyu sorar; erişim yolunda eksiği yoktur. "
               "Ama bu iş yükünün geri kalanı engine'in doğasına uymaz: her küçük ekleme heap'e, index'e ve log'a yazılır, row'lar kullanıcıya göre değil yazma sırasına göre durur ve süre sonu bir partition bakım işidir. "
               "Servis tarafında da en büyük bedel R2'dedir: kampanya akşamının saniyede 15.000 eklemesi checkout'u taşıyan tek writer'dan geçer ve sipariş yazmalarıyla yarışır. "
               "Hangi koşul değişseydi Aurora seçilirdi: event'ler saniyede birkaç yüz olsaydı, siparişlerle JOIN'li raporlar ana iş olsaydı ve 7 günlük ömür yerine aylarca saklama istenseydi.",
    },
    verdict="Karar: Keyspaces {ks}, DynamoDB {ddb}, Aurora {aur}. Engine uyumunda Keyspaces ile DynamoDB neredeyse eşittir; kararı veri ekibinin CQL ile yazılmış gece işi (R4) verir, süre sonunun okumada görünmemesi de küçük bir artıdır. "
            "Keyspaces seçtiğimizde artımız: iki ekranın sorusu tek partition okuması, 7 günlük ömür table ayarı, gece işi değişmez ve sunucu yoktur. "
            "Eksimiz: TTL silmesi ödenir; ilk büyük kampanyadan önce table ısıtılır; \"bu ürüne kimler baktı\" gibi yeni bir soru gelirse ikinci bir table yazılır (Ö7). "
            "M6'daki dürüst not burada da geçerlidir: CQL bilen veri ekibi olmasaydı DynamoDB öne geçerdi. Bir koşul değişseydi: gece işi DynamoDB'ye taşınsaydı DynamoDB kazanırdı."))

# ------------------------------------------------------------------ 2. sensor readings (wind farm)
KEYSPACES_W.append(wusecase("sensor", 2, sim="w_sensor",
    title="Zaman sıralı sensör okumaları (rüzgâr santrali)",
    key="Partition key: (sensor_id, day). Clustering column: ts (en yeni önce). Row: değer, birim, kalite. TTL 90 gün.",
    story=kstory("sensor"),
    wnote="R1 toplam 50: okumaların şekli, sorusu, saklanma biçimi ve 90 günlük ömrü engine'in işidir; en ağır alt maddeler erişim yolu ve depolama algoritmasıdır (14 ve 14). "
          "R2 18 ile ikinci: sensörler tampon tutmaz, yazma yolu hiç durmamalıdır. R4 14: ekibin Cassandra bilgisi bu kartta gerçek bir girdidir.",
    rows=[
        row("EY", 14, "Mühendisin alarm incelemesi ve arıza servisinin dakikalık kontrolü bu iki soruyu sorar.", kreq("sensor", 0, "want"), kreq("sensor", 0, "why")),
        row("VM", 10, "Bir okuma küçük ve şekli sabittir; model uyumu önemlidir ama soruyu belirlemez.",
            "Bir okuma: zaman, birkaç sayı (titreşim, sıcaklık) ve sensörü tanımlayan etiketler (türbin, birim). Okumalar yazıldıktan sonra değişmez.",
            "Model okumanın şekline uymazsa her okumada etiketler tekrar saklanır ya da okuma birkaç kayda bölünür; storage ve kod büyür."),
        row("DA", 14, "31 milyar row birkaç TB'tır; engine'in onları nasıl sakladığı faturanın ve okuma hızının kaynağıdır.",
            "90 günlük okumalar sensör ve zaman sırasıyla bitişik saklanmalı ve sıkıştırılmalı: sayılar zamanla yavaş değişir, bir time series engine'i onları birkaç kat küçültür.",
            "Sıkıştırma yoksa birkaç TB her ay olduğu gibi ödenir ve bir günün okuması diskte gereğinden büyük bir alanı okur."),
        row("YD", 12, "Ham okumalar 90 gün sonra her gün yaklaşık 345 milyon row olarak düşmelidir.",
            "90 günden eski okumalar kendiliğinden silinmeli; silme bir iş olarak yazılmamalı ve okumayı yavaşlatmamalı.",
            "Silme işi yazılırsa günde 345 milyon row silen bir iş işletilir; durursa storage büyür ve fatura her ay artar."),
        row("R2", 18, "Sensörler tampon tutmaz; yazma yolu durursa okumalar kaybolur.", kreq("sensor", 1, "want"), kreq("sensor", 1, "why")),
        row("R3", 10, "Ham veri garanti anlaşmazlığında kanıttır ama tek okumanın kaybı tolere edilir.", kreq("sensor", 2, "want"), kreq("sensor", 2, "why")),
        row("R4", 14, "Ekip Cassandra'yı işletti ve CQL biliyor; bu bilgi bu kartta gerçek bir girdidir.", kreq("sensor", 3, "want"), kreq("sensor", 3, "why")),
        row("R5", 8, "Trafik düz ve tahmin edilebilir; fiyat modeli önemlidir ama kararı vermez.", kreq("sensor", 4, "want").replace(" Storage birkaç TB'tır ve GB fiyatı önemlidir.", " Silme ayrıca ödenmemeli."), kreq("sensor", 4, "why").replace("Birkaç TB'lık storage'ın fiyat farkı her ay faturada görünür.", "Günde 345 milyon silme ayrıca ödenirse her ay faturada görünür.")),
    ],
    cands=["ks", "ix", "ddb"],
    scores={
        "ks": [sc(9, "Composite partition key (sensor_id, day) bir sensörün bir gününü tek partition yapar; saat aralığı clustering column üzerinde tek dilimdir (Ö1, Ö3). 1 puan kırıldı: \"bu türbinin sensörlerinin son 10 dakikası\" sensör başına bir partition okumasıdır (IN ile birkaç alt sorgu)."),
               sc(9, "Type'lı column'lar bir okumayı tam olarak taşır (Ö4). 1 puan kırıldı: türbin ve birim gibi etiketler her row'da tekrar yazılır; engine'de etiket ve ölçüm ayrımı yoktur."),
               sc(6, "Row'lar partition'ın içinde zaman sırasıyla bitişik durur (Ö3). 4 puan kırıldı: time series'e özgü bir sıkıştırma yoktur; Keyspaces'te compression ayarı uygulanmaz ve storage row boyutuyla ölçülür."),
               sc(10, "USING TTL 7776000 ile her okuma 90 gün sonra kendiliğinden düşer ve okumada görünmez (Ö6). Puan kırılmadı."),
               sc(10, "Düz saniyede 4.000 yazma sensörlerin partition'larına dağılır; her partition kendi sınırının çok altındadır (Ö2). Puan kırılmadı."),
               sc(10, "Üç kopya, birkaç AZ; point-in-time recovery. Puan kırılmadı."),
               sc(10, "Ekip CQL ve query-first tasarımı biliyor; node, compaction ve repair yoktur. Puan kırılmadı."),
               sc(9, "Düz trafikte provisioned kapasite on-demand'den ucuzdur. 1 puan kırıldı: günde 345 milyon row'un TTL silmesi KB başına ayrıca ödenir (storage'ın büyüklüğü R1.3'te sayıldı).")],
        "ddb": [sc(9, "Partition key sensör ve gün, sort key zaman; Query saat aralığını verir. 1 puan kırıldı: türbin sorusu sensör başına bir Query'dir."),
                sc(9, "Item bir okumayı taşır. 1 puan kırıldı: etiketler her item'da tekrar yazılır."),
                sc(6, "Item collection zaman sırasıyla bitişiktir. 4 puan kırıldı: time series'e özgü sıkıştırma yoktur; storage item boyutuyla ölçülür."),
                sc(9, "TTL attribute'u 90 gün sonra item'ı ücretsiz siler. 1 puan kırıldı: silme genellikle birkaç gün içinde olur ve o zamana kadar eski okumalar görünür; bu iş yükünde zararsızdır."),
                sc(10, "Düz yazmalar partition'lara dağılır. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(6, "Serverless. 4 puan kırıldı: ekip CQL biliyor; yeni bir API ve SDK öğrenilir, gece Spark işi DynamoDB connector'ı ile yazılır."),
                sc(10, "Provisioned kapasite ve reserved capacity düz trafiğe uyar; TTL silmesi ücretsizdir. Puan kırılmadı.")],
        "ix": [sc(10, "Bir sensörün bir saati range() ve tag filtresiyle sorulur; türbin tag'i bütün sensörlerini tek sorguda verir. Puan kırılmadı."),
               sc(10, "Point'in kendisi: measurement, tag'ler, field'lar ve zaman damgası. Etiketler serinin bir kez tanımıdır. Puan kırılmadı."),
               sc(10, "Engine okumaları seri seri ve zaman sırasıyla sıkıştırarak saklar; yavaş değişen sayılar birkaç kat küçülür. Puan kırılmadı."),
               sc(10, "Bucket'ın retention süresi 90 gün; süresi dolan veri toplu olarak düşer. Puan kırılmadı."),
               sc(10, "Saniyede 4.000 point, düz ve büyümeyen bir yük olarak, uygun boyutlu bir instance için olağandır; instance sınıfını seçmek R4'te sayıldı. Puan kırılmadı."),
               sc(7, "Multi-AZ standby seçeneği vardır. 3 puan kırıldı: standby'a geçişte kısa bir kesinti olur ve tampon tutmayan sensörlerin o anki okumaları kaybolur."),
               sc(5, "Yönetilen instance. 5 puan kırıldı: instance ve storage boyutlandırma ekibin işidir ve Flux ya da InfluxQL ekip için yeni bir dildir; Cassandra bilgisi kullanılmaz."),
               sc(8, "Düz trafik saat başına ödenen instance'a uyar. 2 puan kırıldı: Multi-AZ standby ikinci bir instance ücretidir ve instance boşken de ödenir.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. Engine uyumunda DynamoDB Keyspaces ile eşittir: iki servis de sensör ve günü partition, zamanı sıralı ikinci parça yapar, okumayı bitişik tutar ve time series'e özgü bir sıkıştırma sunmaz. "
               "DynamoDB'nin dürüst üstünlüğü TTL silmesinin ücretsiz olmasıdır; günde 345 milyon silmede bu fark faturada görünür. "
               "Ayrıştıkları yer R4'tür: ekip Cassandra modellemesini ve CQL'i biliyor; DynamoDB'de API, SDK ve gece Spark işinin connector'ı yenidir. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: ekip CQL yerine DynamoDB biliyor olsaydı ya da ham okumalara değişiklik akışıyla bir Lambda'nın tepki vermesi istenseydi; o zaman R4 DynamoDB'ye geçer ve ücretsiz silme R5'i de ona verir.",
        "ix": "Time series (Timestream for InfluxDB) ile kafa kafaya. Engine uyumunu InfluxDB kazanır: R1'in 50 puanının hepsini alır. Okuma bir point'tir, etiketler bir kez tanımlanır, sayılar seri seri sıkıştırılır ve 90 günlük retention bucket'ın bir ayarıdır; Keyspaces ve DynamoDB'de bu dört alt maddenin en az üçünde eksik vardır. "
              "Ama bu karttaki toplam servis tasarımında ve ekipte kaybedilir: standby'a geçişte tampon tutmayan sensörlerin okumaları kaybolur, ekip instance ve storage boyutlandırması ile yeni bir sorgu dili öğrenir ve standby ikinci bir instance ücretidir. Fark 2,8 puandır, yani yakın bir yarıştır. "
              "Saatlik ortalamaları zaten bir gece Spark işi hesaplar; InfluxDB'nin pencere hesabı bu hikâyede kullanılmaz. "
              "Hangi koşul değişseydi InfluxDB seçilirdi: mühendis ekranı ortalama ve tepe değerleri canlı pencerelerle isteseydi, dashboard'lar ana iş olsaydı ve ekip CQL bilmeseydi. O zaman iki servis birlikte de çalışabilir: ham kanıt Keyspaces'te, canlı pencereler InfluxDB'de.",
    },
    verdict="Karar: Keyspaces {ks}, Timestream {ix}, DynamoDB {ddb}. Yakın bir yarış: engine uyumunu InfluxDB kazanır (50'ye 42), toplamı Keyspaces alır; standby'a geçişte kaybolan okumalar (R3) ve ekibin Cassandra bilgisi (R4) bu kartta engine farkından ağır basar. "
            "Keyspaces seçtiğimizde artımız: (sensor_id, day) partition'ı bir günün okumalarını tek dilim yapar, 90 günlük TTL bir ayardır, düz trafikte provisioned kapasite ucuzdur ve ekip bildiği modeli kullanır. "
            "Eksimiz: okumalar sıkıştırılmadan saklanır ve TTL silmesi ödenir; ortalamalar engine'de hesaplanmaz, gece Spark işi ayrı bir sisteme yazar. "
            "Bir koşul değişseydi: mühendisler canlı pencere hesabı isteseydi InfluxDB öne geçerdi; en dürüst cevap o zaman ikisinin birlikte çalışmasıdır."))

# ------------------------------------------------------------------ 3. messaging inbox (support chats)
KEYSPACES_W.append(wusecase("inbox", 3,
    title="Mesajlaşma kutusu: destek sohbetleri",
    key="Partition key: conversation_id. Clustering column: sent_at, message_id (en yeni önce). İkinci yol: temsilcinin sohbet listesi, en son mesaj alan önce.",
    story=kstory("inbox"),
    wnote="R1 toplam 44: iki ekranın sorusu ve sürekli değişen liste sırası engine'in modeline dayanır; en ağır alt madde erişim yoludur (14). "
          "R4 18 ile ikinci: ekip bildirim yolunu DynamoDB ve Lambda ile kurmuş, aynı kalıbı istiyor. R2 16: şikâyet dalgasında yazma beş katına çıkar.",
    rows=[
        row("EY", 14, "Sohbet ekranı ve temsilci listesi destek uygulamasının iki ana ekranıdır.", kreq("inbox", 0, "want"), kreq("inbox", 0, "why")),
        row("OY", 12, "Temsilci listesinin sırası her mesajda değişir; yazmanın biçimi bu iş yükünün zor kısmıdır.",
            "Her yeni mesaj sohbetin \"en son mesaj\" zamanını değiştirir ve sohbet listede en üste çıkar. Bir mesaj 15 dakika içinde yerinde düzenlenebilir.",
            "Liste sırası her mesajda bir silme ve yeni bir yazma isterse silme izleri birikir ve liste okuması yavaşlar; sıra yanlış kalırsa temsilci yeni mesajı kaçırır."),
        row("YD", 10, "Yeni mesaj bildirimi ve iki yıllık ömür verinin yaşam döngüsüdür.",
            "Yeni bir mesaj yazan koddan ayrı bir tepkiyi (telefona bildirim) tetiklemeli; mesajlar iki yıl sonra kendiliğinden silinmeli.",
            "Bildirim yazma yolunun içinde gönderilirse her yeni kural mesaj yazmayı yavaşlatır. İki yıllık silme bir iş olarak yazılırsa o iş de işletilir."),
        row("AO", 8, "Temsilci listesi ikinci bir yoldur; onu kimin güncel tuttuğu önemlidir.",
            "Temsilci listesinin ikinci yolunu database kendisi güncel tutmalı; uygulama her mesajda iki ayrı yeri elle düzeltmemeli.",
            "İkinci yolu uygulama yazarsa iki yer bir hata sonrası birbirinden ayrılır: mesaj sohbette görünür, listede görünmez."),
        row("R2", 16, "Şikâyet dalgasında yazma beş katına çıkar ve destek o anda durmamalıdır.", kreq("inbox", 1, "want") + " Bir şikâyet dalgasında yazma beş katına, saniyede 12.500 mesaja çıkar.", kreq("inbox", 1, "why")),
        row("R3", 14, "Destek mesajı bir anlaşmazlıkta kanıttır; kaybı hukuki risktir.", kreq("inbox", 2, "want"), kreq("inbox", 2, "why")),
        row("R4", 18, "Ekip bildirim yolunu DynamoDB ve Lambda ile kurmuş, aynı kalıbı istiyor.", kreq("inbox", 3, "want"), kreq("inbox", 3, "why")),
        row("R5", 8, "Mesaj küçük; fatura iki yıllık birikimden ve dalgalı trafikten gelir.", kreq("inbox", 4, "want"), kreq("inbox", 4, "why")),
    ],
    cands=["ddb", "ks", "aur"],
    scores={
        "ddb": [sc(10, "Partition key sohbet, sort key gönderilme zamanı; en yeni 50 ve daha eskiler Query ile sayfalanır. Temsilci listesi bir GSI'dır. Puan kırılmadı."),
                sc(9, "Mesaj eklenir, düzenleme UpdateItem'dır; listedeki sohbet item'ının last_msg_at'i değişince GSI kaydı kendiliğinden yer değiştirir. 1 puan kırıldı: her mesaj sohbet item'ına ikinci bir yazmadır."),
                sc(10, "Streams her yeni mesajı sırayla verir ve bildirim ayrı bir tüketicide çalışır; TTL iki yıl sonra siler. Puan kırılmadı."),
                sc(9, "GSI'ı database güncel tutar. 1 puan kırıldı: GSI eventually consistent'tır; liste bir an geride kalabilir."),
                sc(10, "On-demand mod dalgayı taşır; sohbetler partition'lara dağılır. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır; point-in-time recovery. Puan kırılmadı."),
                sc(10, "Ekibin bildiği SDK; Streams bir Lambda'yı doğrudan tetikler, diğer servislerdeki kalıp aynen kullanılır. Puan kırılmadı."),
                sc(10, "İstek başına ödeme dalgalı trafiğe uyar; ikinci yazmanın kendisi R1.2'de sayıldı. Puan kırılmadı.")],
        "ks": [sc(10, "Sohbet table'ında \"en yeni 50\" partition'ın başıdır; temsilci listesi partition key'i temsilci olan ikinci bir table'dır (Ö1, Ö3). Puan kırılmadı."),
               sc(5, "Mesaj eklemesi ve 15 dakikalık düzenleme upsert'tür. 5 puan kırıldı: listenin sırası clustering column'dadır ve değiştirilemez; her mesajda eski row silinir ve yenisi yazılır, her mesaj bir tombstone bırakır (Ö3'ün sınırı)."),
               sc(10, "CDC stream'i her mesajı sırayla verir (Ö8); TTL iki yıl sonra siler (Ö6). Puan kırılmadı."),
               sc(4, "6 puan kırıldı: Keyspaces'te CREATE INDEX ve materialized view yoktur; ikinci table'ı uygulama her mesajda kendisi yazar ve batch izole değildir (Ö7)."),
               sc(10, "Serverless; sohbetler partition'lara dağılır (Ö2). Puan kırılmadı."),
               sc(10, "Üç kopya, birkaç AZ; point-in-time recovery. Puan kırılmadı."),
               sc(5, "Serverless. 5 puan kırıldı: ekip CQL ve Cassandra driver'ını bilmiyor; CDC stream'i bir Lambda'yı doğrudan tetiklemez, bildirim için KCL ile bir tüketici yazılır ve işletilir."),
               sc(10, "İstek başına ödeme dalgalı trafiğe uyar; silme ve yeniden yazmanın kendisi R1.2'de sayıldı. Puan kırılmadı.")],
        "aur": [sc(10, "SQL; (agent_id, last_msg_at DESC) index'i listeyi, (conversation_id, sent_at) index'i sohbeti verir. Puan kırılmadı."),
                sc(9, "Liste sırası tek bir UPDATE'tir ve index kendiliğinden güncellenir. 1 puan kırıldı: her UPDATE row'un yeni bir sürümünü yazar; sık güncellenen sohbet row'ları VACUUM işini artırır (Aurora sayfasının kademesi: birçok row'a dağılan sık güncelleme 1 puan)."),
                sc(6, "Logical replication değişiklikleri engine'den sırayla dışarı verir. 4 puan kırıldı: kendiliğinden süre sonu yoktur; iki yıllık silme aylık partition'ları düşüren zamanlanmış bir iştir."),
                sc(10, "Index'i database transaction'ın içinde günceller; sohbet ve liste hiç ayrılmaz. Puan kırılmadı."),
                sc(7, "Saniyede 2.500 yazma tek writer için olağandır. 3 puan kırıldı: dalgada beş kat, yani saniyede 12.500 yazma, bütün yazmaları taşıyan tek writer'a gelir (Aurora sayfasının tek writer tablosu: 5.000–20.000, kendi writer'ında 3 puan)."),
                sc(10, "Altı kopya, üç AZ. Puan kırılmadı."),
                sc(5, "Yönetilen cluster. 5 puan kırıldı: DynamoDB ekibi için yeni bir database türü, SQL migration'ları ve ACU aralığı seçimi; değişiklik akışını bildirim Lambda'sına taşıyan bileşen ayrıca kurulur ve işletilir."),
                sc(6, "Serverless v2 ACU saat başına ödenir. 4 puan kırıldı: dalgalara göre seçilen minimum ACU boşta da ödenir ve iki yıllık mesaj storage'ı büyür.")],
    },
    h2h={
        "ks": "Wide-column (Keyspaces) ile kafa kafaya. Keyspaces sohbet ekranında DynamoDB kadar iyidir: sohbet partition key'dir, mesajlar zaman sırasıyla durur ve en yeni 50 partition'ın başıdır. "
              "Kaybettiği yer temsilci listesidir. Listenin sırası her mesajda değişir ve Keyspaces'te sıra clustering column'dadır; değiştirmek bir silme ve yeni bir yazmadır, her mesaj bir tombstone bırakır. Index olmadığı için ikinci table'ı da uygulama yazar ve bir hata sonrası iki table'ın uyumunu yine uygulama düzeltir. "
              "Servis tarafında R4 de geridedir: ekip CQL bilmez ve CDC stream'i bildirim Lambda'sını doğrudan tetiklemez. "
              "Hangi koşul değişseydi Keyspaces seçilirdi: temsilci listesi olmasaydı (sadece sohbet ekranı), ekip CQL bilseydi ve şirketin diğer servisleri Keyspaces'te çalışsaydı.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora engine olarak temsilci listesinde en rahat adaydır: liste bir index'tir, sırayı değiştirmek tek bir UPDATE'tir ve sohbet ile liste aynı transaction'da hiç ayrılmaz. "
              "Zayıf olduğu yer yaşam döngüsüdür: süre sonu yoktur ve yeni mesaja tepki için ayrı bir değişiklik akışı bileşeni kurulur. "
              "Servis tasarımında da geridedir: şikâyet dalgasının saniyede 12.500 yazması tek writer'a gelir, ekip DynamoDB bilir ve ACU minimumu boşta da ödenir. Engine'deki üstünlüğü bu yüzden toplamda üçüncülüğe döner. "
              "Hangi koşul değişseydi Aurora seçilirdi: mesajlar siparişler ve müşteri kayıtlarıyla JOIN'li raporlara girseydi, yazma saniyede birkaç yüzde kalsaydı ve ekip SQL bilseydi.",
    },
    verdict="Karar: DynamoDB {ddb}, Keyspaces {ks}, Aurora {aur}. Keyspaces burada net kaybeder: kararı R1'in yazma şekli (değişen liste sırası) ve ikinci yolun bakımı, sonra R4 verir. "
            "Yine de Keyspaces seçersek artımız: sohbet ekranı tek partition okuması, iki yıllık TTL bir ayar, üç AZ'de kopya. "
            "Eksimiz: temsilci listesini uygulama ikinci bir table'da tutar ve her mesajda eski row'u siler; tombstone'lar izlenir; bildirim için bir KCL tüketicisi yazılır; ekip CQL öğrenir. "
            "Bir koşul değişseydi: temsilci listesi olmasaydı ve ekip CQL bilseydi Keyspaces DynamoDB ile yarışırdı."))

# ------------------------------------------------------------------ 4. audit logs
KEYSPACES_W.append(wusecase("audit", 4,
    title="Denetim kayıtları (audit log)",
    key="İki table: audit_by_account ((account_id), ts, event_id) ve audit_by_operator ((operator_id, day), ts, event_id). Kayıt bir kez yazılır, asla değişmez.",
    story=kstory("audit"),
    wnote="R1 toplam 46: iki sorunun yolu, iki listenin eksiksiz kalması ve kaydın değiştirilemezliği engine'in garantileridir; erişim yolu ve atomiklik en ağırlarıdır (14 ve 14). "
          "R2 18 ile ikinci: yılda 95 milyar kayıt birikir. R3 ve R4 14'er: kayıp ceza demektir ve platform ekibi Keyspaces'i zaten işletiyor.",
    rows=[
        row("EY", 14, "Denetçinin ve güvenlik ekibinin iki sorusu bu sistemin varlık nedenidir.",
            "İki sabit soru: \"bu hesapta son 90 günde kim ne yaptı\", zaman sırasıyla, ve \"bu operatör dün ne yaptı\", gün içinde zaman sırasıyla. Bir hesabın 90 günü birkaç saniyede gelmeli.",
            "Bir soru tam taramaya dönerse denetçinin 90 günlük isteği saatler sürer ve denetim takvimi kayar."),
        row("TA", 14, "\"Kayıt bir listede var, diğerinde yok\" durumu bir denetimde kaydın güvenilirliğini bitirir.",
            "Her kayıt iki soruda da eksiksiz görünmeli: hesaba göre listede olan her kayıt operatöre göre listede de olmalı; biri yazılıp diğeri kaybolmamalı.",
            "İki liste ayrılırsa denetçi hangisine güveneceğini bilemez ve bütün kayıt setinin güvenilirliği sorgulanır."),
        row("AO", 10, "Değiştirilebilen bir denetim kaydı denetim kaydı değildir; kuralı engine'in koruması istenir.",
            "Yazılmış bir kaydın güncellenmesi ya da silinmesi engine'in bir kuralıyla engellenmeli: yazan uygulama bile UPDATE ve DELETE yapamamalı.",
            "Kural yalnız uygulama kodundaysa yetkisi olan bir kişi ya da hatalı bir program kaydı sessizce değiştirir ve denetim izi bozulur."),
        row("OY", 8, "Yazma biçimi basittir: yalnız ekleme; ağırlık bu yüzden düşük.",
            "Her kayıt bir kez eklenir; yazma önce okumamalı ve aynı kayıt tekrar gönderilirse ikinci bir kayıt oluşmamalı.",
            "Tekrar gönderilen bir kayıt iki kez görünürse operatör aynı işlemi iki kez yapmış gibi görünür."),
        row("R2", 18, "Yılda 95 milyar kayıt birikir; büyüdükçe yavaşlayan bir sistem bir yıl sonra işe yaramaz.", kreq("audit", 1, "want"), kreq("audit", 1, "why")),
        row("R3", 14, "Eksik kayıt düzenleyici bir denetimde ceza ve lisans riskidir.", kreq("audit", 2, "want"), kreq("audit", 2, "why")),
        row("R4", 14, "Platform ekibi diğer log servislerini Keyspaces'te işletiyor; aynı araç gece çağrısında doğru kişi demektir.", kreq("audit", 3, "want"), kreq("audit", 3, "why")),
        row("R5", 8, "Trafik düz ve tahmin edilebilir; fiyat modeli önemlidir ama kararı vermez.",
            "Trafik düz: önceden alınan kapasite istek başına ödemeden ucuz olmalı. Gece de çalışan bir sunucu için ödeme istenmez.",
            "Düz trafik için istek başına fiyat boşa ödenen bir esnekliktir; boşta da çalışan bir sunucu her gece ödenir."),
    ],
    cands=["ks", "ddb", "aur"],
    scores={
        "ks": [sc(10, "İki soru iki table'dır; her biri tek partition okumasıdır ve (operator_id, day) partition'ı bir günle sınırlıdır (Ö1, Ö3, Ö7). Puan kırılmadı."),
               sc(8, "Logged batch iki INSERT'in ikisinin de sonunda uygulanmasını sağlar. 2 puan kırıldı: batch izole değildir; bir okuma bir an için kaydı bir table'da görüp diğerinde görmeyebilir ve iki table'ın uyumunu uygulama kurar."),
               sc(5, "INSERT ... IF NOT EXISTS üzerine yazmayı önler (Ö5). 5 puan kırıldı: engine'de \"sadece ekle\" kuralı yoktur; CQL GRANT desteklenmez (\"Security settings: Replaced by IAM\") ve UPDATE ile DELETE'i engine katmanında kapatan bir araç yoktur."),
               sc(10, "Kayıt okumadan eklenir; event_id istemcide bir kez üretilirse tekrar gönderim aynı row'a düşer (Ö1). Puan kırılmadı."),
               sc(10, "Düz saniyede 3.000 yazma hesap ve operatör partition'larına dağılır ve veri büyüdükçe partition okuması aynı kalır (Ö2). Puan kırılmadı."),
               sc(10, "Üç kopya, birkaç AZ; point-in-time recovery yanlışlıkla silinen kaydı son 35 gün içinde geri getirir. Puan kırılmadı."),
               sc(10, "Platform ekibi Keyspaces'i zaten işletiyor; yeni table aynı izleme ve aynı araçlarla çalışır. Değiştirilemezlik eksiği R1.3'te sayıldı. Puan kırılmadı."),
               sc(10, "Düz trafikte provisioned kapasite uygundur; iki table'a yazmanın kendisi model gereğidir ve R1.2'de sayıldı. Puan kırılmadı.")],
        "ddb": [sc(10, "Partition key hesap, sort key zaman; operatör sorusu (operator#day, ts) key'li bir GSI'dır. Puan kırılmadı."),
                sc(9, "GSI kaydı ana item'dan database tarafından türetilir; iki liste hiç kalıcı olarak ayrılmaz. 1 puan kırıldı: GSI eventually consistent'tır; güvenlik sorgusu son birkaç saniyeyi bir an görmeyebilir."),
                sc(5, "attribute_not_exists koşulu üzerine yazmayı önler. 5 puan kırıldı: engine'de \"sadece ekle\" kuralı yoktur; güncelleme ve silme engine katmanında kapatılamaz."),
                sc(10, "PutItem okumadan ekler; koşullu yazma tekrar gönderimi reddeder. Puan kırılmadı."),
                sc(10, "Partition'lar yazmaları dağıtır; veri büyüdükçe Query aynı kalır. Puan kırılmadı."),
                sc(10, "Birkaç AZ; point-in-time recovery. Puan kırılmadı."),
                sc(6, "Serverless. 4 puan kırıldı: platform ekibi için yeni bir servis ve yeni bir API; log servislerinin izleme ve araçları ikiye bölünür."),
                sc(10, "Düz trafikte provisioned kapasite uygundur; GSI'ın ikinci yazması modelin parçasıdır. Puan kırılmadı.")],
        "aur": [sc(10, "İki soru iki B-tree index'tir; SQL yeni bir soruyu da yeni bir table olmadan sorar. Puan kırılmadı."),
                sc(10, "Kayıt tek bir row'dur ve iki index aynı transaction'da güncellenir; iki liste hiç ayrılmaz. Puan kırılmadı."),
                sc(10, "GRANT INSERT, SELECT ve REVOKE UPDATE, DELETE: yazan rol bile kaydı değiştiremez; bir trigger da değişikliği reddedebilir. Puan kırılmadı."),
                sc(9, "INSERT okumadan ekler. 1 puan kırıldı: her kayıt heap'e ve iki index'e yazılır."),
                sc(4, "Saniyede 3.000 ekleme kendi writer'ı için olağandır (Aurora sayfasının tek writer tablosu: 5.000'e kadar, kendi writer'ında 0) ve bir yıllık çevrim içi hacim 128 TiB'lık storage sınırının altındadır. 6 puan kırıldı: 95 milyar row'luk tek bir table ve iki index onlarca TB'tır; bu büyüklükteki B-tree index'lere ekleme row sayısı büyüdükçe yavaşlar ve table partition'lara bölünmeden taşınamaz."),
                sc(10, "Altı kopya, üç AZ; point-in-time restore. Puan kırılmadı."),
                sc(5, "Yönetilen cluster. 5 puan kırıldı: yüz milyarlarca row için partition bakımı, VACUUM ve ANALYZE izlenir; ekip CQL bilir, SQL tarafını bilmez."),
                sc(6, "Instance, storage ve I/O ödenir. 4 puan kırıldı: düz trafikte bile instance'lar gece de çalışır ve Aurora Standard'da her eklemenin I/O'su ayrıca ödenir.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. İki servis engine olarak bu iş yüküne neredeyse aynı derecede uyar: iki soru iki key yoludur, yazma okumadan eklenir ve koşullu yazma tekrarı önler. "
               "DynamoDB'nin dürüst üstünlüğü ikinci yolun bakımındadır: GSI'ı database tutar, iki liste kalıcı olarak hiç ayrılmaz. "
               "Keyspaces'te ikinci table'ı uygulama yazar. Değiştirilemezlikte iki servis eşittir: ikisinin engine'inde de \"sadece ekle\" kuralı yoktur ve IAM de üzerine yazmayı kapatamaz (DynamoDB'de PutItem var olan item'ın üzerine yazar, Keyspaces'te cassandra:Modify INSERT, UPDATE ve DELETE'i birlikte verir). "
               "Kararı R4 verir: platform ekibi Keyspaces'i ve CQL'i zaten işletiyor; yeni bir servis izleme ve gece çağrısı bilgisini ikiye böler. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: platform ekibi log servislerini DynamoDB'de çalıştırsaydı ya da denetçi iki listenin bir an bile farklı görünmemesini şart koşsaydı.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Engine uyumunu Aurora kazanır: kayıt tek row'dur ve iki index aynı transaction'da güncellenir, GRANT ile yazan rol bile kaydı değiştiremez ve yeni bir soru yeni bir table değil bir SQL cümlesidir. "
               "Bu, Keyspaces ve DynamoDB'nin engine'de sunmadığı bir değiştirilemezlik aracıdır. "
               "Ama toplamı ölçek kaybettirir: bir yıllık çevrim içi hacim 95 milyar row ve iki index, yani onlarca TB'tır; bütün yazmalar tek writer'dadır ve bu büyüklükte bir table'ın index'i, VACUUM'u ve ANALYZE'ı bir iştir. "
               "Hangi koşul değişseydi Aurora seçilirdi: kayıt sayısı yılda birkaç milyar olsaydı, denetçiler kayıtları hesap ve işlem table'larıyla JOIN'li sorularla incelemek isteseydi ve ekip SQL bilseydi.",
    },
    verdict="Karar: Keyspaces {ks}, DynamoDB {ddb}, Aurora {aur}. Yakın bir yarış: engine uyumunda DynamoDB biraz öndedir (ikinci yolu database tutar), Aurora en öndedir (değiştirilemezliği engine korur); toplamı ölçek (R2) ve platform ekibinin Keyspaces'i zaten işletmesi (R4) Keyspaces'e verir. "
            "Keyspaces seçtiğimizde artımız: iki soru iki partition okuması, yıllar boyu aynı hız, mevcut platform ve point-in-time recovery. "
            "Eksimiz: iki table'ı uygulama logged batch ile yazar ve bir uyum kontrolü (iki table'ın gecelik sayımı bir analiz kopyasında) çalıştırır; değiştirilemezliği engine değil, IAM ve CloudTrail ile süreç korur; bir yıl sonra S3 arşivine CDC ile akan bir iş yazılır. "
            "Değiştirilemezliğin asıl aracı arşiv tarafındadır: bir yıldan sonra kayıtların gittiği S3'te Object Lock yedi yıl boyunca silmeyi ve değiştirmeyi engeller; S3 ve Athena ise denetçinin \"birkaç saniyede 90 gün\" sorusunu tek bir key okumasıyla cevaplamadığı için çevrim içi yıl için aday değildir. "
            "Bir koşul değişseydi: denetçi engine katmanında değiştirilemezlik isteseydi ve hacim küçük olsaydı Aurora öne geçerdi."))

# ------------------------------------------------------------------ 5. cart in a Cassandra shop
KEYSPACES_W.append(wusecase("cart", 5,
    title="Bir Cassandra mağazasında alışveriş sepeti",
    key="Partition key: cart_id. Clustering column: product_id. Kural: okunan değerle koşullu yazma, örneğin SET qty = 4 IF qty = 2. TTL 24 saat.",
    story=kstory("cart"),
    wnote="R1 toplam 38: kuralın korunması, sepetin okunması ve 24 saatlik ömür engine'e dayanır; en ağır alt madde atomikliktir (16). "
          "R4 28 ile tek başına bir satır olarak en ağırdır ama R1'in toplamından hafiftir: 9 ayda kod değişmeden taşınmalı ve node'ları işleten kişi ayrılıyor.",
    rows=[
        row("TA", 16, "Kural bozulursa bir müşteri kampanya ürününden 50 adet alır.",
            "\"Bir üründen en fazla 5 adet\" kuralı iki sekme aynı anda eklese bile korunmalı: test ve yazma tek adım olmalı.",
            "Kural \"önce oku, sonra yaz\" ile korunursa iki sekme aynı anda geçer ve stok planı bozulur."),
        row("EY", 12, "Sepet sayfası her açılışta sepetin satırlarını okur.",
            "Sorular: \"bu sepetin satırları\" ve \"bu sepetin bu satırı\". Her istek sepet id'sini bilir.",
            "Sepet satırları tek okumayla gelmezse sepet sayfası yavaşlar ve kampanya gecesi terk edilen sepet artar."),
        row("YD", 10, "Sepetler 24 saat sonra değersizdir.",
            "Sepet satırları 24 saat sonra kendiliğinden kaybolmalı ve süresi dolan satır sepet sayfasında görünmemeli.",
            "Süresi dolan satır görünürse müşteri dünkü fiyatla ödeme ekranına gelir; silme işi yazılırsa o da işletilir."),
        row("R2", 14, "Kampanyada yazma on katına çıkar.", kreq("cart", 1, "want"), kreq("cart", 1, "why")),
        row("R3", 10, "Sepet resmi kayıt değildir ama kampanya gecesi kaybı satış kaybıdır.", kreq("cart", 2, "want"), kreq("cart", 2, "why")),
        row("R4", 28, "9 ayda kod değişmeden taşınmalı ve node'ları işleten kişi ayrılıyor; bu kartın ana kısıtı budur.",
            "Java servisinin CQL kodu değişmemeli; node, repair, compaction ve sürüm yükseltme işi kalmamalı. Ekipteki iki geliştirici CQL bilir; yeni bir API öğrenmek için zaman yok.",
            "Kod değişirse dört yıllık testlerin hepsi yeniden yazılır ve 9 ay yetmez. Node'ları işleten kişi ayrılıyor; işletme bilgisi onunla gider."),
        row("R5", 10, "Kampanya dışında trafik düşüktür; tepe için yıl boyu ödeme istenmez.", kreq("cart", 4, "want"), kreq("cart", 4, "why")),
    ],
    cands=["ks", "ddb", "mdb"],
    scores={
        "ks": [sc(10, "UPDATE ... SET qty = 4 IF qty = 2 bir lightweight transaction'dır; test ve yazma tek adımdır ve Keyspaces'te ek ücreti ve performans cezası yoktur (Ö5). Puan kırılmadı."),
               sc(10, "Partition key cart_id, clustering column product_id: sepet tek partition okumasıdır (Ö1, Ö3). Puan kırılmadı."),
               sc(10, "USING TTL 86400 ile satır 24 saat sonra düşer ve okumada görünmez (Ö6). Puan kırılmadı."),
               sc(10, "On-demand mod daha önce ulaşılan seviyeye anında çıkar; ısıtılmış table kampanyayı taşır (Ö2). Puan kırılmadı."),
               sc(10, "Üç kopya, birkaç AZ. Puan kırılmadı."),
               sc(8, "Aynı CQL ve aynı DataStax driver'ı; node, repair ve compaction yoktur. 2 puan kırıldı: driver'ın bağlantı ayarı (TLS 9142, SigV4 plugin'i) değişir, LWT ile TTL testleri Keyspaces'te bir kez koşulur ve ilk kampanyadan önce table ısıtılır."),
               sc(9, "İstek başına ödeme kampanya dışındaki düşük trafiğe uyar. 1 puan kırıldı: süresi dolan her sepet satırının silinmesi TTL delete olarak ödenir.")],
        "ddb": [sc(10, "ConditionExpression aynı kuralı tek adımda korur. Puan kırılmadı."),
                sc(10, "Partition key sepet, sort key ürün; Query sepeti verir. Puan kırılmadı."),
                sc(8, "TTL ücretsiz siler. 2 puan kırıldı: süresi dolan satır genellikle birkaç gün içinde silinir ve o zamana kadar okumada görünür; sepet okuması expires_at'i süzmelidir."),
                sc(10, "On-demand mod ısıtılmış bir table ile tepeyi taşır. Puan kırılmadı."),
                sc(10, "Birkaç AZ. Puan kırılmadı."),
                sc(3, "Serverless; işletme işi biter ve warm throughput bir ayardır. 7 puan kırıldı: Java servisi CQL'den DynamoDB SDK'sına yeniden yazılır ve dört yıllık testler yeniden yazılır; 9 aylık plana sığması zordur."),
                sc(10, "İstek başına ödeme; TTL silmesi ücretsiz. Puan kırılmadı.")],
        "mdb": [sc(9, "Kural sunucuda sırayla çalışan bir Lua script'iyle tek adımda korunur. 1 puan kırıldı: \"5'i geçmesin\" kuralı tek bir komut değildir, script yazılır ve test edilir."),
                sc(10, "Sepet başına bir hash; HGETALL bütün satırları bellekten verir. Puan kırılmadı."),
                sc(10, "EXPIRE sepeti tam 24 saatinde siler; süresi dolan satır okunamaz. Puan kırılmadı."),
                sc(9, "Bilinen kampanya tepesi için shard'lar önceden eklenir. 1 puan kırıldı: tahminin üstündeki bir tepe çevrimiçi yeniden shard'lamayı bekler."),
                sc(10, "Her yazma çoklu AZ'li transaction log'a işlenir. Puan kırılmadı."),
                sc(3, "Yönetilen cluster. 7 puan kırıldı: servis CQL'den Valkey komutlarına ve Lua'ya yeniden yazılır; node tipi ve shard sayısı ekibin seçimidir."),
                sc(6, "Node saat başına ödenir. 4 puan kırıldı: kampanyaya göre seçilen node'lar yıl boyu ödenir ve bellek GB başına pahalıdır.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. Engine olarak DynamoDB bu sepete Keyspaces kadar uyar: kural bir ConditionExpression'dır, sepet bir Query'dir ve TTL ücretsizdir. Tek engine farkı süre sonudur: süresi dolan satır birkaç gün okumada görünebilir ve uygulama süzer. "
               "Kararı bu kartın ana kısıtı R4 verir: Java servisinin bütün CQL kodu DynamoDB SDK'sına, dört yıllık testleri de yeni API'a göre yeniden yazılır ve bu iş 9 aylık taşıma planını doldurur. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: servis zaten yeniden yazılacak olsaydı (örneğin yeni bir sepet modeli için) ya da taşıma için iki yıl olsaydı; o zaman ücretsiz TTL ve ekibin AWS'te öğreneceği tek API DynamoDB'yi öne geçirirdi.",
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. Engine olarak MemoryDB sepete çok iyi uyar: sepet bellekte bir hash'tir, EXPIRE tam 24 saatinde siler ve çoklu AZ'li log sepeti kalıcı yapar. Kuralı bir Lua script'i korur. "
               "R1'de DynamoDB ile aynı seviyededir, Keyspaces'ten biraz geridedir. "
               "Kaybettiği yer servis ve ekip tarafıdır: CQL kodu Valkey komutlarına yeniden yazılır, node ve shard boyutlandırmak ekibin işi olur ve kampanyaya göre seçilen node'lar yıl boyu ödenir. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: sepet okuması bir milisaniyenin altında olmak zorunda olsaydı, servis zaten yeniden yazılacak olsaydı ve trafik yıl boyu düz ve yüksek olsaydı.",
    },
    verdict="Karar: Keyspaces {ks}, DynamoDB {ddb}, MemoryDB {mdb}. Engine uyumunda Keyspaces öndedir (aynı LWT, aynı TTL, okumada görünmeyen süre sonu), ama asıl farkı R4 yaratır: kod değişmeden taşınır ve node işletme işi biter. "
            "Keyspaces seçtiğimizde artımız: aynı CQL ve aynı lightweight transaction'lar, kampanya için node ekleme yok, 24 saatlik TTL aynı. "
            "Eksimiz: driver'ın bağlantı ayarı değişir ve LWT'lerin Keyspaces'teki davranışı bir kez test edilir; TTL silmesi ödenir; Keyspaces'in desteklemediği bir özelliğe (secondary index, materialized view) bağlı başka bir servis varsa o önce değiştirilir. "
            "Kendi işlettiğin Cassandra (EC2 üzerinde) bu kartta aday değildir: node'ları işleten kişi ayrılıyor ve R4 tam olarak bu işin bitmesini istiyor; ikiz servisin karşılaştırması kart 10'dadır. "
            "Bir koşul değişseydi: servis zaten yeniden yazılacak olsaydı DynamoDB öne geçerdi."))

# ------------------------------------------------------------------ 6. device state with TTL
KEYSPACES_W.append(wusecase("device", 6,
    title="TTL ile cihaz durumu (akıllı termostatlar)",
    key="Partition key: device_id (tek parça). Row: son sıcaklık, mod, pil. Her yazma 24 saatlik bir ömürle; 35 derecede bildirim.",
    story=kstory("device"),
    wnote="R1 toplam 42: tek key'li üzerine yazma, 24 saatlik ömür ve yazan koddan ayrı alarm engine'in modeline ve yaşam döngüsüne dayanır; en ağır alt madde yaşam döngüsüdür (18). "
          "R2 20 ile ikinci: saniyede 25.000 sürekli yazma. R4 18 ve R5 14: ekip IoT Core, Lambda ve DynamoDB ile çalışıyor ve günde iki milyardan fazla yazma faturayı belirler.",
    rows=[
        row("EY", 10, "Soru tek bir cihazın durumudur; basittir ama her açılışta sorulur.",
            "Sorular: \"bu cihazın son durumu\" ve \"bu cihazın son durumunu bu mesajla değiştir\". Cihaz id'si her mesajda ve her uygulama açılışında bilinir.",
            "Model bundan karmaşıksa karmaşıklık boşa ödenir; okuma yavaşlarsa uygulama açılışta bekler."),
        row("OY", 14, "Dakikada bir, cihaz başına bir üzerine yazma; yazmanın biçimi iş yükünün kendisidir.",
            "Her mesaj cihazın kaydını okumadan üzerine yazmalı (upsert). Eski değerler burada tutulmaz.",
            "Yazma önce okursa saniyede 25.000 yazma 50.000 isteğe çıkar ve Lambda süresi uzar."),
        row("YD", 18, "\"Çevrim dışı\" gösterimi ve 35 derece bildirimi bu ürünün iki özelliğidir.",
            "24 saat mesaj göndermeyen cihazın durumu kendiliğinden yok olmalı ve okumada görünmemeli. Sıcaklık 35 dereceyi geçince bildirim yazan koddan ayrı bir tüketicide tetiklenmeli.",
            "Durum kendiliğinden yok olmazsa uygulama aylarca önce sökülmüş bir termostatı \"çevrim içi\" gösterir. Bildirim yazan Lambda'nın içindeyse her yeni kural yazma yolunu yavaşlatır."),
        row("R2", 20, "Saniyede 25.000 sürekli yazma; yazma yavaşlarsa Lambda kuyruğu büyür.", kreq("device", 1, "want"), kreq("device", 1, "why")),
        row("R3", 6, "Kaybolan bir durum bir dakika sonra yeniden gelir; dayanıklılık burada bir rahatlıktır.", kreq("device", 2, "want"), kreq("device", 2, "why")),
        row("R4", 18, "Ekip IoT Core, Lambda ve DynamoDB ile çalışıyor; Lambda'dan uzun ömürlü bağlantı istemiyor.",
            "Ekip IoT Core, Lambda ve DynamoDB SDK'sı kullanıyor; CQL ve Cassandra driver'ı istemiyor. Değişiklikler bildirim fonksiyonuna kod yazmadan ulaşmalı ve Lambda'dan uzun ömürlü TLS bağlantıları yönetilmemeli.",
            "Değişiklik akışını okuyan bir tüketiciyi ekip yazar ve işletirse beş kişilik ekibin işi büyür. Lambda'dan uzun ömürlü TLS bağlantıları yönetmek ayrı bir iştir ve bağlantı sınırlarına dayanır."),
        row("R5", 14, "Günde iki milyardan fazla yazma: fiyat modelinin her ayrıntısı (önceden alınan kapasite, silme ücreti) faturada görünür.", kreq("device", 4, "want"), kreq("device", 4, "why")),
    ],
    cands=["ddb", "ks", "ec"],
    scores={
        "ddb": [sc(10, "Simple primary key cihaz id'si; GetItem tek okumadır. Puan kırılmadı."),
                sc(10, "PutItem okumadan üzerine yazar. Puan kırılmadı."),
                sc(8, "Streams 35 derece bildirimini filtreli bir Lambda'ya verir; TTL attribute'u her yazmada 24 saat ileri alınır. 2 puan kırıldı: süresi dolan item genellikle birkaç gün içinde silinir ve o zamana kadar okumada görünür; uygulama \"çevrim dışı\" kararını expires_at ile kendisi verir."),
                sc(10, "Cihaz id'lerinin hash'i yazmaları partition'lara eşit dağıtır. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(10, "IoT kuralı table'a yazar, Streams bir Lambda'yı filtre kriteriyle doğrudan çağırır; Lambda'dan bağlantı yönetimi yoktur. Puan kırılmadı."),
                sc(9, "Düz trafikte provisioned kapasite ve reserved capacity; TTL silmesi ücretsiz. 1 puan kırıldı: 1 KB'tan büyük mesajlar iki yazma birimi tüketir.")],
        "ks": [sc(10, "Partition key device_id; SELECT ... WHERE device_id = ? tek okumadır (Ö1). Puan kırılmadı."),
               sc(10, "INSERT her zaman bir upsert'tür ve okumadan yazar (Ö1). Puan kırılmadı."),
               sc(10, "USING TTL 86400 her mesajda ömrü yeniler ve süresi dolan durum okumada hiç görünmez (Ö6); CDC stream'i 35 derece değişikliğini sırayla verir (Ö8). Puan kırılmadı."),
               sc(10, "Yazmalar cihaz partition'larına dağılır (Ö2). Puan kırılmadı."),
               sc(10, "Üç kopya, birkaç AZ. Puan kırılmadı."),
               sc(4, "Serverless. 6 puan kırıldı: ekip CQL ve Cassandra driver'ını istemiyor; Lambda'dan TLS bağlantı havuzu yönetilir ve CDC stream'i bir Lambda'yı doğrudan tetiklemez, bildirim için KCL ile bir tüketici yazılır ve işletilir."),
               sc(8, "Düz trafikte provisioned kapasite ucuzdur. 2 puan kırıldı: çevrim dışı kalan cihazların TTL silmesi ayrıca ödenir; hikâye silmenin ödenmemesini istiyor.")],
        "ec": [sc(10, "Key cihaz id'si; GET bellekten mikrosaniyede döner. Puan kırılmadı."),
               sc(10, "SET ... EX okumadan üzerine yazar. Puan kırılmadı."),
               sc(6, "EXPIRE durumu tam 24 saatinde siler. 4 puan kırıldı: yazmaların değişiklik akışı yoktur; keyspace notification kalıcı değildir, 35 derece bildirimi yazan Lambda'nın içinde çalışır."),
               sc(10, "Serverless yazma hızını izler. Puan kırılmadı."),
               sc(4, "Kopyalar birkaç AZ'dedir. 6 puan kırıldı: kalıcı bir yazma log'u yoktur; son durumun tek yeri bellektir ve bir arızada kaybolabilir. Kart bu kaybı kabul eder (durum bir dakika içinde yeniden gelir); ElastiCache sayfasının kuralıyla 4 puan."),
               sc(6, "Serverless. 4 puan kırıldı: ekip için yeni bir API ve Lambda VPC'nin içinde çalışır (değişiklik akışının yokluğu R1.3'te sayıldı)."),
               sc(7, "1,5 milyon küçük durum bellekte küçüktür. 3 puan kırıldı: her yazma ECPU olarak istek başına ödenir; düz ve yüksek yazmada önceden alınan kapasite indirimi yoktur.")],
    },
    h2h={
        "ks": "Wide-column (Keyspaces) ile kafa kafaya. Engine uyumunu Keyspaces kazanır: tek key'li upsert iki serviste de aynıdır, ama süresi dolan durum Keyspaces'te okumada hiç görünmez; DynamoDB'de birkaç gün görünebilir ve uygulama \"çevrim dışı\" kararını kendisi verir. "
              "Toplamı servis tasarımı ve ekip kaybettirir: ekip CQL istemiyor, Lambda'dan uzun ömürlü TLS bağlantıları yönetilir ve CDC stream'i bildirim Lambda'sını doğrudan tetiklemez, bir KCL tüketicisi yazılır. Bu, DynamoDB sayfasındaki IoT kartının aynı mekanizmasıdır. "
              "Çevrim dışı cihazların TTL silmesinin ödenmesi de R5'te küçük bir kayıptır. "
              "Hangi koşul değişseydi Keyspaces seçilirdi: ekip Cassandra kullanıyor olsaydı, yazan servis uzun ömürlü bir container olsaydı (Lambda değil) ve bildirim kuralları zaten ayrı bir akış işleyicisinde çalışsaydı.",
        "ec": "Bellek içi key-value (ElastiCache) ile kafa kafaya. ElastiCache durumu mikrosaniyede okur ve EXPIRE tam 24 saatinde siler; hikâye kaybı da kabul eder, çünkü durum bir dakikada yeniden gelir. "
              "Ama engine'de yazmaların değişiklik akışı yoktur: 35 derece bildirimi yazan Lambda'nın içine girer ve her yeni kural yazma yolunu değiştirir. "
              "Servis tarafında ekip yeni bir API öğrenir, Lambda VPC'de çalışır ve her yazma ECPU olarak ödenir. "
              "Hangi koşul değişseydi ElastiCache seçilirdi: bildirim olmasaydı, mobil uygulama durumu bir milisaniyenin altında isteseydi ve kalıcı kopya başka bir yerde dursaydı; o zaman ElastiCache bir cache olarak DynamoDB'nin önünde de durabilir.",
    },
    verdict="Karar: DynamoDB {ddb}, Keyspaces {ks}, ElastiCache {ec}. Keyspaces net kaybeder, ama engine uyumunda öndedir (42'ye 38,4): okumada görünmeyen süre sonu bu iş yükünün tam ihtiyacıdır. Kararı R4 verir: IoT kuralı, table ve filtreli Lambda bağlantısı ekibin bildiği kalıptır. "
            "Yine de Keyspaces seçersek artımız: \"çevrim dışı\" kararı TTL'in kendisidir, uygulama süre karşılaştırmaz. "
            "Eksimiz: Lambda'dan bağlantı havuzu yönetilir, bildirim için bir KCL tüketicisi yazılır ve işletilir, ekip CQL öğrenir, TTL silmesi ödenir. "
            "AWS IoT Core'un Device Shadow'u da her cihazın son durumunu tutar ve bağlantı yaşam döngüsü olayları cihazın çevrim dışı olduğunu bildirir; ama bir database değildir: cihazlar arası soru, değişiklik akışı ve TTL vermez. Uygulama cihaza istenen ayarı da gönderecekse doğru cevap ikisinin birlikte çalışmasıdır: shadow cihazla senkron için, DynamoDB uygulamanın okuduğu durum ve bildirim için. "
            "Bir koşul değişseydi: ekip Cassandra bilseydi ve yazan servis uzun ömürlü olsaydı Keyspaces kazanırdı."))

# ------------------------------------------------------------------ 7. click streams (news site)
KEYSPACES_W.append(wusecase("clicks", 7, sim="w_clicks",
    title="Tıklama akışı: kaldığın yerden devam et",
    key="Partition key: user_id. Clustering column: clicked_at (en yeni önce). TTL 30 gün. Haftalık rapor için analiz kopyası: CDC ile S3 ve Redshift.",
    story=kstory("clicks"),
    wnote="R1 toplam 46: kişi başına şerit ve haftalık rapor iki farklı soru türüdür ve ikisi de engine'e sorulur; erişim yolu ve depolama algoritması en ağırlarıdır (14 ve 14). "
          "R2 18 ve R4 18 ile ikinci: son dakika haberinde yazma beş katına çıkar ve çalışan Spark işleri bu karta özgü bir bağdır.",
    rows=[
        row("EY", 14, "\"Kaldığın yerden devam et\" şeridi her ana sayfa açılışında görünür.",
            "Okuyucu başına soru: \"bu okuyucunun son 100 tıklaması, en yeni önce\". Her istek okuyucu id'sini bilir ve cevap 20 ms'nin altında olmalı.",
            "Şerit yavaş olursa ana sayfa yavaşlar; günde 6 milyon okuyucu bunu her açılışta görür."),
        row("DA", 14, "Yayın yönetmenlerinin haftalık raporu ikinci bir soru türüdür ve engine'in tarama biçimine dayanır.",
            "Haftalık rapor bütün okuyucuların geçen haftasını tarar ve kategoriye ve saate göre gruplar; tarama şeridi yavaşlatmamalı.",
            "Rapor her row'u okuyan bir tarama olursa pazartesi sabahı ana sayfa yavaşlar ya da rapor saatler sürer ve yayın planı gecikir."),
        row("OY", 8, "Yazma yalnız eklemedir; ağırlık bu yüzden düşük.",
            "Her tıklama bir kez eklenir ve değişmez; yazma önce okumamalı.",
            "Yazma önce okursa son dakika haberinde istek sayısı iki katına çıkar."),
        row("YD", 10, "Tıklamalar 30 gün sonra silinmeli ve rapor tarafına bir kopya akmalıdır.",
            "Tıklamalar 30 gün sonra kendiliğinden silinmeli. Her yeni tıklama raporun okuyacağı bir kopyaya yazan koddan ayrı olarak akmalı.",
            "Silme işi yazılırsa o da işletilir. Kopya gece bir tam taramayla alınırsa tarama şeridi yavaşlatır ve rapor bir gün eski kalır."),
        row("R2", 18, "Son dakika haberinde yazma birkaç dakikada beş katına çıkar.", kreq("clicks", 1, "want"), kreq("clicks", 1, "why")),
        row("R3", 6, "Tıklamalar istatistik içindir; tek tek değerli değildir.", kreq("clicks", 2, "want"), kreq("clicks", 2, "why")),
        row("R4", 18, "Çalışan sessionization işleri iki aylık bir yeniden yazmadır ve analistler SQL ister.", kreq("clicks", 3, "want"), kreq("clicks", 3, "why")),
        row("R5", 12, "Trafik çok dalgalı ve ayda milyarlarca tıklama yazılıp silinir; fiyat modeli belirgin bir kalemdir.",
            "Trafik çok dalgalı: istek başına ödeme isteniyor. 30 günlük silme kendiliğinden olmalı ve ayrıca ödenmemeli.",
            "Tepeye göre boyutlanan kapasite günün çoğunda boş durur ve ödenir. Silme ayrıca ödenirse ayda milyarlarca silme faturada görünür."),
    ],
    cands=["ks", "ddb", "rs"],
    scores={
        "ks": [sc(10, "Partition key user_id, clustering column clicked_at DESC: son 100 tıklama partition'ın başıdır (Ö1, Ö3). Puan kırılmadı."),
               sc(3, "Spark tam taramayı token aralıklarına bölerek okur. 7 puan kırıldı: aggregate fonksiyon ve GROUP BY yoktur, bütün partition'lar okunur ve gruplama Spark'ta yapılır; tarama aynı table'ın kapasitesini kullanır."),
               sc(10, "INSERT okumadan ekler (Ö1). Puan kırılmadı."),
               sc(10, "TTL 30 gün (Ö6); CDC stream'i her tıklamayı sırayla verir ve analiz kopyasını table'ı taramadan besler (Ö8). Puan kırılmadı."),
               sc(8, "On-demand mod daha önce ulaşılan seviyeye anında çıkar (Ö2). 2 puan kırıldı: son dakika haberi yeni bir rekor tepeyse birkaç dakikalık sıçrama önceden ısıtılmış kapasiteyi aşabilir."),
               sc(10, "Üç kopya, birkaç AZ. Puan kırılmadı."),
               sc(6, "Spark Cassandra Connector ile yazılmış sessionization işleri değişmez. 4 puan kırıldı: analistlerin SQL'i Keyspaces'te yoktur; CDC'yi okuyan bir KCL tüketicisi, S3'e yazan bir iş ve Redshift tarafı ayrıca kurulur ve işletilir."),
               sc(8, "İstek başına ödeme dalgalı trafiğe uyar. 2 puan kırıldı: ayda milyarlarca tıklamanın TTL silmesi KB başına ödenir.")],
        "ddb": [sc(10, "Partition key okuyucu, sort key zaman; Query son 100'ü verir. Puan kırılmadı."),
                sc(3, "Scan paralel okunabilir. 7 puan kırıldı: GROUP BY yoktur, bütün item'lar okunur ve gruplama dışarıda yapılır."),
                sc(10, "PutItem okumadan ekler. Puan kırılmadı."),
                sc(9, "TTL ücretsiz siler; Streams ve Redshift'e zero-ETL kopyayı besler. 1 puan kırıldı: süresi dolan item birkaç gün daha görünebilir; şeritte zararsızdır."),
                sc(8, "On-demand mod tepeyi taşır. 2 puan kırıldı: yeni bir rekor sıçrama önceden ısıtılmış kapasiteyi aşabilir."),
                sc(10, "Birkaç AZ. Puan kırılmadı."),
                sc(5, "Analistlerin SQL'i zero-ETL ile Redshift'te kod yazmadan gelir. 5 puan kırıldı: sessionization işleri Cassandra connector'ından DynamoDB'ye yeniden yazılır; hikâye bunu iki ay olarak verir."),
                sc(10, "İstek başına ödeme; TTL silmesi ücretsiz. Puan kırılmadı.")],
        "rs": [sc(4, "Sort key okuyucu ve zaman olan bir table son 100'ü bulur. 6 puan kırıldı: her ana sayfa açılışında bir point lookup columnar ve MPP bir engine'in işi değildir; 20 ms'nin altı garanti edilmez."),
               sc(10, "Columnar storage ve MPP, haftanın bütün tıklamalarını kategoriye ve saate göre gruplamanın kendisidir. Puan kırılmadı."),
               sc(5, "Streaming ingestion tıklamaları mikro-batch'lerle ekler. 5 puan kırıldı: saniyede binlerce tek tek küçük ekleme columnar bloklara uymaz; yazma toplu olmalıdır."),
               sc(6, "Eski veri tarih aralığıyla silinir. 4 puan kırıldı: süre sonu yoktur; silme zamanlanmış bir DELETE ve VACUUM işidir."),
               sc(8, "Tıklamalar bir akış katmanından (Kinesis) streaming ingestion ile gelir. 2 puan kırıldı: on-demand bir stream son 30 günün tepesinin iki katına kadar kendiliğinden uyar; yeni bir rekor sıçrama bunu aşabilir (Keyspaces ve DynamoDB ile aynı kırılım). Şeridin 20 ms'lik okuması R1.1'de, akış katmanının işletilmesi R4'te sayıldı."),
               sc(9, "Veri S3'te yedeklenir. 1 puan kırıldı: akış katmanındaki son saniyeler bir arızada yeniden oynatılır."),
               sc(4, "Analistlerin SQL'i doğrudan çalışır. 6 puan kırıldı: sessionization işleri Spark connector'ından Redshift'e yeniden yazılır, DynamoDB'deki gibi iki ay (5); akış katmanı (Kinesis) ayrıca işletilir (1)."),
               sc(6, "RPU-saat ve akış katmanı ödenir. 4 puan kırıldı: istek başına ödeme yoktur; sürekli sorgu yükü varken sunucusuz kapasite gün boyu açık kalır.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. Engine olarak iki servis bu iş yüküne aynı yerden uyar ve aynı yerden uymaz: şerit iki serviste tek partition okumasıdır, haftalık rapor iki serviste de bir tam taramadır. "
               "DynamoDB'nin dürüst üstünlüğü servis tarafındadır: zero-ETL tıklamaları Redshift'e kod yazmadan taşır, analistler SQL'i hemen alır ve TTL silmesi ücretsizdir. "
               "Keyspaces'in üstünlüğü ekip tarafındadır: sessionization işleri Spark Cassandra Connector ile yazılmıştır ve değişmez. Fark küçüktür ve yakın bir yarıştır; iki serviste de rapor ayrı bir analiz kopyasında çalışır. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: sessionization işleri zaten yeniden yazılacak olsaydı ya da analiz kopyası için bir KCL tüketicisi işletecek kimse olmasaydı.",
        "rs": "Data warehouse (Redshift) ile kafa kafaya. Redshift haftalık raporda rakipsizdir: columnar storage ve MPP, bütün okuyucuların bir haftasını gruplamanın kendisidir ve analistler SQL'i doğrudan kullanır. "
              "Ama bu kartın diğer yarısı ana sayfa şerididir: her açılışta tek bir okuyucunun son 100 tıklaması 20 ms'nin altında istenir ve bu bir point lookup'tır; columnar engine bunun için tasarlanmamıştır. Tek tek küçük eklemeler de mikro-batch ister. "
              "Bu yüzden Redshift bu kartta bir rakip değil, bir tamamlayıcıdır. "
              "Hangi koşul değişseydi Redshift seçilirdi: şerit olmasaydı ve iş yalnız rapor olsaydı. Doğru mimari ikisinin birlikte çalışmasıdır: şerit Keyspaces'te, rapor CDC ile beslenen Redshift'te.",
    },
    verdict="Karar: Keyspaces {ks}, DynamoDB {ddb}, Redshift {rs}. Yakın bir yarış: engine uyumunda Keyspaces ile DynamoDB neredeyse eşittir ve ikisi de haftalık raporda zayıftır; kararı çalışan Spark işleri (R4) verir. "
            "En dürüst cevap ikisinin birlikte çalışmasıdır: şerit Keyspaces'te, haftalık rapor Redshift'te; CDC stream'i (Ö8) tıklamaları bir KCL tüketicisiyle S3'e ve oradan Redshift'e taşır. "
            "Keyspaces seçtiğimizde artımız: şerit tek partition okuması, 30 günlük TTL bir ayar, sessionization işleri değişmez. "
            "Eksimiz: rapor yolu (KCL tüketicisi, S3, Redshift) ayrıca kurulur ve işletilir; TTL silmesi ödenir; rapor taraması asla bu table'da çalışmaz. "
            "Bir koşul değişseydi: sessionization işleri yeniden yazılacak olsaydı DynamoDB ve zero-ETL öne geçerdi."))

# ------------------------------------------------------------------ 8. fraud signals per account
KEYSPACES_W.append(wusecase("fraud", 8, sim="w_fraud",
    title="Hesap başına dolandırıcılık sinyalleri",
    key="Partition key: account_id. Clustering column: ts (en yeni önce). Row: sinyal türü, cihaz, ülke, risk puanı. TTL 90 gün.",
    story=kstory("fraud"),
    wnote="R1 toplam 42: son 200 sinyalin yolu, okumanın hızı ve yeni cihaza tepki engine'in modeline ve depolamasına dayanır. "
          "R4 18 ile ikinci: kural motoru yazan koddan ayrı ve ekip Lambda ile çalışıyor. R2 ve R3 16: 10 ms'lik bütçe ve kaybolmaması gereken sinyaller.",
    rows=[
        row("EY", 12, "Her kart işlemi bu soruyu sorar.", kreq("fraud", 0, "want"), kreq("fraud", 0, "why")),
        row("DA", 12, "Okuma 50 ms'lik yetkilendirme bütçesinin içinde 10 ms'yi geçmemeli.",
            "Bir hesabın son 200 sinyali engine'in depolamasından tek bir bitişik okumayla, p99'da 10 ms'nin altında gelmeli.",
            "Okuma 10 ms'yi aşarsa yetkilendirme 50 ms'yi geçer, kart ağı işlemi reddeder ve müşteri kasada bekler."),
        row("YD", 12, "Yeni cihaz sinyali birkaç saniyede kural motorunu tetiklemeli; sinyaller 90 gün yaşar.",
            "Yeni bir cihaz sinyali yazan koddan ayrı bir tüketiciye sırayla ve birkaç saniye içinde ulaşmalı. Sinyaller 90 gün sonra kendiliğinden silinmeli.",
            "Tepki yazma yolunun içindeyse her yeni kural yetkilendirmeyi yavaşlatır. Tepki dakikalar sürerse çalınmış hesap o arada ödeme yapar."),
        row("OY", 6, "Yazma yalnız eklemedir.",
            "Her sinyal bir kez eklenir; yazma önce okumamalı.",
            "Yazma önce okursa saniyede 20.000 sinyal 40.000 isteğe çıkar."),
        row("R2", 16, "Saniyede 20.000 yazma ve 6.000 okuma, kampanyada iki kat.", kreq("fraud", 1, "want"), kreq("fraud", 1, "why")),
        row("R3", 16, "Kaybolan bir sinyal bir dolandırıcılığı gizler.", kreq("fraud", 2, "want"), kreq("fraud", 2, "why")),
        row("R4", 18, "Kural motoru Lambda ile çalışacak ve ekip Lambda ile DynamoDB'yi biliyor.",
            "Kural motoru ekibin bildiği Lambda ile çalışmalı ve değişiklikleri kod yazmadan almalı; ekip Lambda ve DynamoDB SDK'sını biliyor.",
            "Değişiklik akışını okuyan bir tüketiciyi ekip yazar ve işletirse altı kişilik ekibin işi büyür; yeni bir API öğrenmek teslimi geciktirir."),
        row("R5", 8, "Sürekli yazma ve 90 günlük birikim faturayı belirler.", kreq("fraud", 4, "want"), kreq("fraud", 4, "why")),
    ],
    cands=["ddb", "ks", "mdb"],
    scores={
        "ddb": [sc(10, "Partition key hesap, sort key zaman; ters sırada Limit 200 ile Query. Puan kırılmadı."),
                sc(9, "Item collection bitişiktir; okuma tek haneli milisaniyedir. 1 puan kırıldı: p99'da 10 ms'nin altı sağlanır ama pay küçüktür."),
                sc(10, "Streams yeni cihaz sinyalini key başına sırayla verir; TTL 90 gün sonra ücretsiz siler. Puan kırılmadı."),
                sc(10, "PutItem okumadan ekler. Puan kırılmadı."),
                sc(10, "On-demand mod kampanya gününün iki katını taşır. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır; point-in-time recovery. Puan kırılmadı."),
                sc(10, "Ekibin bildiği SDK; Streams kural motoru Lambda'sını filtre kriteriyle doğrudan tetikler. Puan kırılmadı."),
                sc(10, "İstek başına ödeme dalgalı trafiğe uyar; TTL silmesi ücretsizdir. Puan kırılmadı.")],
        "ks": [sc(10, "Partition key account_id, clustering column ts DESC: son 200 sinyal partition'ın başıdır (Ö1, Ö3). Puan kırılmadı."),
               sc(9, "Row'lar partition'da bitişik ve sıralıdır; okuma tek haneli milisaniyedir (Ö3). 1 puan kırıldı: p99'da 10 ms'nin altı sağlanır ama pay küçüktür."),
               sc(10, "CDC stream'i yeni cihaz sinyalini sırayla verir (Ö8); TTL 90 gün sonra siler (Ö6). Puan kırılmadı."),
               sc(10, "INSERT okumadan ekler (Ö1). Puan kırılmadı."),
               sc(10, "Serverless; hesaplar partition'lara dağılır (Ö2). Puan kırılmadı."),
               sc(10, "Üç kopya, birkaç AZ; point-in-time recovery. Puan kırılmadı."),
               sc(5, "Serverless. 5 puan kırıldı: ekip CQL bilmiyor; CDC stream'i kural motoru Lambda'sını doğrudan tetiklemez, KCL ile bir tüketici yazılır ve işletilir."),
               sc(8, "İstek başına ödeme. 2 puan kırıldı: saniyede 20.000 sinyalin 90 gün sonraki TTL silmesi KB başına ayrıca ödenir.")],
        "mdb": [sc(10, "Hesap başına bir sorted set; ZREVRANGE son 200'ü verir. Puan kırılmadı."),
                sc(10, "Bütün veri bellektedir; okuma mikrosaniyedir. Puan kırılmadı."),
                sc(4, "6 puan kırıldı: yazmaların değişiklik akışı yoktur; pub/sub kalıcı değildir, kural motoru yazma yolundan ayrı ve sıralı beslenemez. 90 günlük kırpma da bir iştir."),
                sc(10, "ZADD okumadan ekler. Puan kırılmadı."),
                sc(9, "Bilinen kampanya tepesi için shard'lar önceden eklenir. 1 puan kırıldı: tahminin üstündeki tepe çevrimiçi yeniden shard'lamayı bekler."),
                sc(10, "Her yazma çoklu AZ'li transaction log'a işlenir. Puan kırılmadı."),
                sc(5, "Yönetilen cluster. 5 puan kırıldı: ekip için yeni bir API; node tipi ve shard sayısı ekibin seçimidir (değişiklik akışının yokluğu R1.3'te sayıldı)."),
                sc(2, "Node saat başına ödenir. 8 puan kırıldı: 90 günlük sinyal birikimi on TB'ın üstündedir ve hepsi bellekte, GB başına en pahalı yerde durur.")],
    },
    h2h={
        "ks": "Wide-column (Keyspaces) ile kafa kafaya. Engine uyumunda Keyspaces DynamoDB ile eşittir: son 200 sinyal iki serviste de bir partition'ın başıdır, okuma tek haneli milisaniyedir ve iki engine de yeni sinyali bir değişiklik akışıyla verir. "
              "Bu kart, R1 eşitken kararı servis tasarımının verdiği yerdir. DynamoDB'de Streams kural motoru Lambda'sını filtreyle doğrudan tetikler ve ekip bu kalıbı biliyor; Keyspaces'te CDC'yi bir KCL tüketicisi okur, ekip onu yazar ve işletir. TTL silmesinin ödenmesi de R5'te küçük bir kayıptır. "
              "Hangi koşul değişseydi Keyspaces seçilirdi: ekip Cassandra bilseydi, kural motoru zaten bir akış işleyicisinde (örneğin KCL ya da Flink) çalışsaydı ve şirketin diğer servisleri Keyspaces'te olsaydı.",
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. MemoryDB okuma hızında rakipsizdir: son 200 sinyal bellekteki bir sorted set'tir ve mikrosaniyede gelir; çoklu AZ'li log sinyali kalıcı yapar. "
               "Ama engine'de yazmaların değişiklik akışı yoktur ve kural motoru yazma yolundan ayrı beslenemez; üye başına süre sonu da yoktur, 90 günden eski sinyaller bir işle kırpılır. "
               "Asıl kayıp maliyettedir: saniyede 20.000 sinyalin 90 günü on TB'ın üstündedir ve hepsi bellekte durur. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: bütçe 10 ms değil 1 ms olsaydı ve yalnız son birkaç günün sinyali tutulsaydı. O zaman ikisi birlikte çalışır: son günler MemoryDB'de, 90 günlük kayıt DynamoDB'de.",
    },
    verdict="Karar: DynamoDB {ddb}, Keyspaces {ks}, MemoryDB {mdb}. Engine uyumunda DynamoDB ile Keyspaces eşittir (40,8 ve 40,8); kararı servis tasarımı verir: Streams'in kural motoru Lambda'sını doğrudan tetiklemesi ve ekibin bildiği API (R4). "
            "Yine de Keyspaces seçersek artımız: son 200 sinyal tek partition okuması, süresi dolan sinyal okumada görünmez, üç AZ'de kopya. "
            "Eksimiz: kural motoru için bir KCL tüketicisi yazılır ve işletilir; ekip CQL öğrenir; TTL silmesi ödenir. "
            "Bir koşul değişseydi: ekip Cassandra bilseydi ve kural motoru zaten bir akış işleyicisinde çalışsaydı Keyspaces kazanırdı."))

# ------------------------------------------------------------------ 9. product reviews per product
KEYSPACES_W.append(wusecase("reviews", 9, sim="w_reviews",
    title="Ürün başına yorumlar",
    key="Partition key: product_id. Clustering column: created_at. \"En faydalı\" sırası, yıldız filtresi, ortalama ve moderasyon kuyruğu ek yollar ister.",
    story=kstory("reviews"),
    wnote="R1 toplam 52: üç sıra, bir filtre, analistlerin yeni soruları, ortalamalar ve sürekli değişen oylar engine'in sorgu ve güncelleme modeline dayanır; en ağır alt madde erişim yoludur (22). "
          "R4 18 ile ikinci: ekip ve analistler SQL biliyor.",
    rows=[
        row("EY", 22, "Ürün sayfası yorumları üç biçimde gösterir, moderatör ayrı bir liste görür ve analistler her ay yeni sorular sorar.",
            "Sorular: ürüne göre en yeni önce, en faydalı önce, yıldıza göre filtre, moderasyon durumuna göre bekleyenler (en eskisi önce) ve analistlerin her ay yeni, siparişlerle ve iadelerle birleştirilen soruları.",
            "Bir sıra ya da filtre yoksa ürün sayfası eksik görünür; moderasyon listesi yavaşsa yorumlar günlerce yayınlanmaz. Her yeni analist sorusu bir veri projesine dönüşürse sorular haftalarca bekler."),
        row("AO", 12, "Ortalama puan ve yıldız sayıları her ürün sayfasının üstündedir.",
            "Engine ürün başına ortalamayı ve yıldız başına sayıyı vermeli (aggregate); uygulama sayıları ayrı bir kopyada elle tutmamalı.",
            "Sayılar uygulamada ayrı tutulursa yorumlardan ayrılır ve ortalama yanlış görünür; müşteri güveni kaybolur."),
        row("OY", 10, "\"Faydalı\" oyları ve moderasyon durumu yazıldıktan sonra sürekli değişir.",
            "Bir oy, yorumun faydalı sayısını yerinde artırmalı ve \"en faydalı\" sırası kendiliğinden güncellenmeli; moderasyon durumu yerinde değişmeli.",
            "Sıra değişimi her oyda silme ve yeniden yazma isterse silme izleri birikir ve ürün sayfası yavaşlar."),
        row("TA", 8, "Ortalama ile yorumlar birbirini tutmalıdır.",
            "Yeni bir yorum ve ürünün yıldız sayıları birlikte değişmeli; biri yazılıp diğeri kalmamalı.",
            "Sayılar yorumlarla tutmazsa \"12 yorum\" yazan sayfada 11 yorum görünür."),
        row("R2", 10, "Trafik orta; ağırlık bu yüzden düşük.", kreq("reviews", 1, "want"), kreq("reviews", 1, "why")),
        row("R3", 8, "Yorumlar kullanıcıların emeğidir ama tek bir yorumun kaybı para değildir.", kreq("reviews", 2, "want"), kreq("reviews", 2, "why")),
        row("R4", 18, "Ekip ve analistler SQL biliyor; araç değiştirmek her ay yeni soruların hızını belirler.",
            "Ekip ve analistler SQL biliyor ve yeni bir sorgu dili ya da veri modeli öğrenmek istemiyor.",
            "Yeni bir dil ve model ekibin her değişikliğini yavaşlatır; analistler soruları bir geliştiriciye yazdırmak zorunda kalır."),
        row("R5", 12, "Veri küçük; en basit model en ucuz modeldir.", kreq("reviews", 4, "want"), kreq("reviews", 4, "why")),
    ],
    cands=["aur", "doc", "ks"],
    scores={
        "aur": [sc(10, "(product_id, created_at DESC), (product_id, helpful DESC) ve (product_id, stars) index'leri, bekleyenler için partial index; analistlerin yeni soruları siparişlerle JOIN'li SQL'dir. Puan kırılmadı."),
                sc(10, "GROUP BY ortalamayı ve yıldız sayılarını verir. Puan kırılmadı."),
                sc(8, "Oy tek bir UPDATE ... SET helpful = helpful + 1'dir ve index kendiliğinden güncellenir. 2 puan kırıldı: her UPDATE row'un yeni bir sürümünü yazar; çok oylanan yorumlar VACUUM işini artırır."),
                sc(10, "Yorum ve ürünün sayıları tek transaction'dadır. Puan kırılmadı."),
                sc(10, "Saniyede 2.000 okuma reader'lara dağılır. Puan kırılmadı."),
                sc(10, "Altı kopya, üç AZ. Puan kırılmadı."),
                sc(10, "Ekip ve analistler SQL biliyor. Puan kırılmadı."),
                sc(8, "Küçük veri için küçük bir instance ya da düşük bir ACU aralığı. 2 puan kırıldı: instance boşken de ödenir.")],
        "doc": [sc(7, "Alan index'leri her sırayı ve filtreyi verir. 3 puan kırıldı: siparişler ve iadeler bir relational database'tedir; analistlerin JOIN'li soruları iki sistemi birleştiren bir iştir."),
                sc(9, "Aggregation pipeline ortalamayı ve yıldız sayılarını verir. 1 puan kırıldı: her sayfada hesaplanmaz, sayılar ürün document'ında tutulur."),
                sc(9, "$inc oyu yerinde artırır ve index güncellenir. 1 puan kırıldı: çok oylanan document'lar sık güncellenir."),
                sc(8, "Çok document'lı transaction vardır. 2 puan kırıldı: yorum ve ürün sayıları iki document'tır ve transaction gerektirir."),
                sc(10, "Okumalar replica'lara dağılır. Puan kırılmadı."),
                sc(10, "Storage üç AZ'de altı kopya. Puan kırılmadı."),
                sc(5, "Yönetilen cluster. 5 puan kırıldı: SQL bilen ekip ve analistler MongoDB API'ını ve aggregation pipeline'ı öğrenir."),
                sc(7, "Instance saat başına. 3 puan kırıldı: küçük veri için bile en az bir instance sürekli ödenir.")],
        "ks": [sc(3, "\"En yeni önce\" partition'ın sırasıdır (Ö3). 7 puan kırıldı: index ve materialized view olmadığı için her ek sıra ve filtre uygulamanın yazdığı ayrı bir table'dır (yıldız filtresi, en faydalı, moderasyon kuyruğu); her yeni analist sorusu yeni bir table ve geçmişin doldurulmasıdır ve siparişlerle JOIN yoktur (Ö7'nin sınırı)."),
               sc(4, "6 puan kırıldı: aggregate fonksiyon yoktur; ortalama ve yıldız sayıları uygulamanın tuttuğu counter table'larıdır."),
               sc(4, "Oy ve moderasyon durumu yazılabilir. 6 puan kırıldı: \"en faydalı\" sırası bir clustering column'dur ve değiştirilemez; her oy eski row'u silip yenisini yazar ve bir tombstone bırakır (Ö3'ün sınırı; kart 3'teki gibi 5 puan). Moderasyon kuyruğunun sırası da ikinci bir clustering column'dur ve her onayda aynı silme ve yazma tekrarlanır (1)."),
               sc(4, "6 puan kırıldı: counter table'ları ve dört yorum table'ı tek bir ya hep ya hiç yazmada değişemez; logged batch izole değildir ve counter'lar ayrı bir batch ister (Ö5'in sınırı)."),
               sc(10, "Okumalar partition'lara dağılır (Ö2). Puan kırılmadı."),
               sc(10, "Üç kopya, birkaç AZ. Puan kırılmadı."),
               sc(5, "Serverless. 5 puan kırıldı: SQL bilen ekip ve analistler CQL'i ve soru başına table tasarımını öğrenir."),
               sc(10, "İstek başına ödeme küçük trafiğe uyar; ek table'ların ve oyların yazmaları R1'de sayıldı. Puan kırılmadı.")],
    },
    h2h={
        "doc": "Document (DocumentDB) ile kafa kafaya. DocumentDB engine olarak yorumlara çok yakındır: alan index'leri her sırayı ve filtreyi verir, oy $inc ile yerinde artar, aggregation pipeline ortalamayı hesaplar. R1'de Aurora'nın 8,4 puan gerisindedir: siparişlerle JOIN'li analist soruları iki sistemi birleştirir. "
               "Ayrıştıkları yer ekip ve sistemdir: ekip SQL biliyor, analistler yorumları siparişlerle ve iadelerle birleştirir ve siparişler bir relational database'tedir. DocumentDB'de bu sorular iki sistemi birleştiren bir işe dönüşür ve ekip yeni bir sorgu dili öğrenir. "
               "Hangi koşul değişseydi DocumentDB seçilirdi: yorumlar fotoğraf, cevap ve yan yana alanlarla iç içe ve şekli sık değişen document'lar olsaydı, ekip MongoDB API'ını bilseydi ve siparişler de document database'te dursaydı.",
        "ks": "Wide-column (Keyspaces) ile kafa kafaya. Keyspaces bu kartta net kaybeder ve nedeni engine'dir: R1'de 52 puanın 18,6'sını alır. "
              "Tek bir sıra (en yeni önce) partition'ın kendisidir; ama her ek sıra ve filtre ayrı bir table'dır, index ve aggregate fonksiyon yoktur, \"en faydalı\" sırası her oyda bir silme ve tombstone demektir ve sayılar yorumlarla birlikte ya hep ya hiç yazılamaz. "
              "Ekip tarafında da her yeni analist sorusu yeni bir table ve geçmişin doldurulmasıdır. "
              "Hangi koşul değişseydi Keyspaces seçilirdi: yorum ekranı yalnız \"en yeni önce\" olsaydı, oylama ve analist soruları olmasaydı ve yazma saniyede on binlere çıksaydı; o zaman bile sayılar ayrı tutulurdu.",
    },
    verdict="Karar: Aurora {aur}, DocumentDB {doc}, Keyspaces {ks}. Keyspaces net kaybeder ve üçüncüdür: kararı R1 verir (erişim yolu, ayar araçları, değişen sıra) ve R4 kaybı büyütür. "
            "Yine de Keyspaces seçersek artımız: \"en yeni önce\" tek partition okuması ve trafik büyürse aynı hız. "
            "Eksimiz: dört yorum table'ı ve counter table'ları uygulamada tutulur, her oy bir tombstone bırakır, ortalamalar zaman zaman yorumlardan yeniden hesaplanır ve her analist sorusu bir veri kopyası ister (CDC ile S3'e). "
            "Bir koşul değişseydi: yorumlar iç içe ve şekli serbest document'lar olsaydı ve ekip MongoDB API'ını bilseydi DocumentDB öne geçerdi."))

# ------------------------------------------------------------------ 10. migration of an on-premises Cassandra
KEYSPACES_W.append(wusecase("migration", 10, sim="w_migration",
    title="Kendi veri merkezindeki bir Cassandra'nın AWS'e taşınması",
    key="Mevcut 50 table, aynı CQL ve aynı primary key'ler. Değişen: driver bağlantı ayarı (TLS 9142, SigV4).",
    story=kstory("migration") + " Okumalar LOCAL_QUORUM ve LOCAL_ONE, yazmalar LOCAL_QUORUM kullanıyor.",
    wnote="R1 toplam 46: 50 table'ın şeması, sorguları, koşullu yazmaları ve TTL'leri engine'in aynı davranmasını ister; dört alt madde neredeyse eşit önemdedir. "
          "R4 20 ile ikinci: yönetimin asıl isteği işletme yükünün bitmesidir. R2 14: ay sonu fatura döneminde yazma iki katına çıkar.",
    rows=[
        row("ŞE", 12, "50 table'ın şeması altı yıllık iş kurallarının taşıyıcısıdır.",
            "50 table'ın column'ları, type'ları, kullanıcı tanımlı type'ları ve primary key'leri aynen kurulmalı; yeni bir column eklemek bugünkü gibi anında olmalı.",
            "Şema farklı bir modele çevrilirse her table'ın okuma ve yazma kodu değişir ve altı yıllık kurallar yeniden test edilir."),
        row("EY", 12, "Servislerin bütün sorguları bugünkü partition key ve clustering column'lara göre yazılmıştır.",
            "Bütün CQL sorguları aynı partition key ve clustering column koşullarıyla, aynı sırada ve aynı sayfalamayla çalışmalı.",
            "Bir sorgu biçimi desteklenmezse o servis yeniden tasarlanır ve 6 aylık plan kayar."),
        row("TA", 12, "Lightweight transaction'lar faturalandırmanın kurallarını korur.",
            "IF NOT EXISTS ve IF ile yazılan koşullar aynı garantiyle çalışmalı; okumalar LOCAL_QUORUM ve LOCAL_ONE ile aynı tutarlılığı vermeli.",
            "Koşul farklı davranırsa bir kayıt iki kez faturalanır ya da hiç faturalanmaz."),
        row("YD", 10, "Kayıtların ömrü TTL ile yasal saklama süresine bağlıdır.",
            "Bugünkü TTL'ler aynen çalışmalı ve süresi dolan kayıt okumada görünmemeli.",
            "TTL farklı davranırsa yasal süresi dolan kayıt faturada görünür ya da süresi dolmayan kayıt kaybolur."),
        row("R2", 14, "Ay sonu fatura döneminde yazma iki katına çıkar.", kreq("migration", 1, "want"), kreq("migration", 1, "why")),
        row("R3", 10, "Arama kayıtları faturanın kaynağıdır ve yasal olarak saklanır.", kreq("migration", 2, "want"), kreq("migration", 2, "why")),
        row("R4", 20, "Yönetimin asıl isteği işletme yükünün bitmesi ve kodun yeniden yazılmamasıdır.", kreq("migration", 3, "want"), kreq("migration", 3, "why")),
        row("R5", 10, "Bugün tepeye göre boyutlanan 24 node yıl boyu ödeniyor.", kreq("migration", 4, "want"), kreq("migration", 4, "why")),
    ],
    cands=["ks", "ddb", "cas"],
    scores={
        "ks": [sc(10, "Aynı CREATE TABLE, aynı type'lar ve UDT'ler; ALTER TABLE ADD anında (Ö4). Compaction ve compression ayarları gönderilirse yok sayılır. Puan kırılmadı."),
               sc(10, "Aynı partition key ve clustering column koşulları, aynı sayfalama (Ö1, Ö3); ekip kullanmadığı secondary index ve materialized view'ın eksikliğini zaten kontrol etti. Puan kırılmadı."),
               sc(10, "LWT aynı söz dizimiyle çalışır ve Keyspaces'te performans cezası yoktur (Ö5); LOCAL_QUORUM ve LOCAL_ONE desteklenir (Ö2). Puan kırılmadı."),
               sc(10, "Aynı TTL'ler; süresi dolan kayıt okumada görünmez (Ö6). Puan kırılmadı."),
               sc(10, "On-demand ya da auto scaling'li provisioned kapasite ay sonunu izler (Ö2). Puan kırılmadı."),
               sc(10, "Üç kopya, birkaç AZ; point-in-time recovery yanlış bir silmeyi son 35 gün içinde geri alır. Puan kırılmadı."),
               sc(8, "Node, repair, compaction ve sürüm yükseltme işi biter; kod aynı kalır. 2 puan kırıldı: driver'ın bağlantı ayarı (TLS 9142, SigV4) ve bağlantı havuzu (bağlantı başına saniyede en fazla 3.000 CQL sorgusu) ayarlanır, 40 TB veri bir kez taşınır ve ilk ay sonundan önce table'lar ısıtılır."),
               sc(9, "Kapasite trafiği izler; boş duran node yoktur. 1 puan kırıldı: TTL'in sildiği her KB ayrıca ödenir.")],
        "cas": [sc(10, "Aynı Apache Cassandra; şema olduğu gibi kopyalanır. Puan kırılmadı."),
                sc(10, "Aynı sorgular. Puan kırılmadı."),
                sc(9, "Aynı LWT ve aynı consistency level'lar. 1 puan kırıldı: Cassandra'da LWT bir Paxos turu çalıştırır; belge bunun için \"non-negligible performance cost\" der."),
                sc(9, "Aynı TTL. 1 puan kırıldı: sona eren veri tombstone olur ve compaction ile gc_grace_seconds'u bekler; okumalar o zamana kadar işi artırır."),
                sc(9, "Bilinen ay sonu için node'lar önceden eklenir. 1 puan kırıldı: tahminin üstündeki bir büyüme node ekleme ve saatler süren veri akışı ister."),
                sc(8, "Node'lar üç AZ'e yerleştirilir ve snapshot'lar S3'e alınır. 2 puan kırıldı: yerleşimi, snapshot'ı ve geri yükleme testini ekip kurar ve işletir."),
                sc(2, "8 puan kırıldı: node değiştirme, repair, compaction ayarı, sürüm yükseltme ve kapasite ekleme işi aynen kalır; yönetimin bitirmek istediği iş tam olarak budur."),
                sc(6, "EC2 ve EBS saat başına ödenir. 4 puan kırıldı: ay sonuna göre boyutlanan node'lar ayın 25 günü yarı boş ödenir.")],
        "ddb": [sc(6, "Key alanları tanımlanır, diğer alanlar serbesttir. 4 puan kırıldı: type'lı column'lar ve UDT'ler attribute'lara ve map'lere çevrilir; şema kuralı engine'de değil uygulamada kalır."),
                sc(8, "Partition key ve sort key aynı erişim yolunu verir. 2 puan kırıldı: engine'de tek bir sort key vardır; birden fazla clustering column tek bir sort key metninde birleştirilir ve her parçanın type'ı kaybolur."),
                sc(10, "ConditionExpression koşullu yazmanın aynı garantisini verir; söz dizimine çevirmek R4'te sayıldı. Puan kırılmadı."),
                sc(8, "TTL ücretsiz siler. 2 puan kırıldı: süresi dolan item genellikle birkaç gün içinde silinir ve o zamana kadar okumada görünür; hikâye süresi dolan kaydın görünmemesini istiyor."),
                sc(10, "On-demand mod ay sonunu ayarsız taşır. Puan kırılmadı."),
                sc(10, "Birkaç AZ; point-in-time recovery. Puan kırılmadı."),
                sc(2, "Serverless; işletme işi biter. 8 puan kırıldı: bütün Java servisleri CQL'den DynamoDB SDK'sına 6 ay içinde yeniden yazılır ve altı yıllık iş kuralları yeniden test edilir."),
                sc(10, "İstek başına ödeme; TTL silmesi ücretsiz. Puan kırılmadı.")],
    },
    h2h={
        "cas": "Kendi işlettiğin wide-column (Apache Cassandra, EC2 üzerinde) ile kafa kafaya. Bu, Keyspaces'in ikizidir: aynı CQL, aynı şema ve aynı sorgular, ve Keyspaces'in desteklemediği özellikler (secondary index, materialized view, UDF) de oradadır. Ama Keyspaces Cassandra'nın kendisi değil, aynı API'ı sunan ayrı bir engine'dir; bu yüzden R1'leri birebir eşit değildir: Cassandra'da LWT'nin Paxos maliyeti ve tombstone'ların compaction'ı bekleyen işi küçük kayıplardır. "
               "Asıl fark servis tasarımındadır: node, repair, compaction, sürüm yükseltme ve kapasite ekleme işi aynen kalır ve tepeye göre boyutlanan node'lar yıl boyu ödenir. "
               "Hangi koşul değişseydi Cassandra on EC2 seçilirdi: kod secondary index, materialized view ya da UDF kullansaydı, ALL ya da EACH_QUORUM gerekseydi ve işletme ekibi kalsaydı.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB aynı partition fikrini, ücretsiz TTL'i ve ayarsız ölçeği verir; servis tasarımında Keyspaces kadar güçlüdür. "
               "Engine farkı R1'de görünür: type'lı column'lar ve UDT'ler şemasız attribute'lara, birden fazla clustering column tek bir sort key metnine dönüşür ve süresi dolan kayıt birkaç gün görünebilir. Kodun çevrilmesi ise ayrı bir iştir ve R4'te neredeyse tam bir kayıptır: bütün servisler 6 ayda yeniden yazılır ve donanım garantisi bitmeden bu iş tamamlanmaz. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: kod zaten yeniden yazılacak olsaydı, taşıma için iki yıl olsaydı ve ekip AWS'te tek bir key-value API'ı öğrenmek isteseydi.",
    },
    verdict="Karar: Keyspaces {ks}, DynamoDB {ddb}, Apache Cassandra {cas}. Net bir kazanma; ikinci ve üçüncü arasındaki fark yalnız 0,4 puandır: Keyspaces R1'in 46 puanının hepsini alır (aynı şema, sorgular, LWT ve TTL) ve işletme yükünü bitirir (R4). "
            "Keyspaces seçtiğimizde artımız: kod değişmez, sadece bağlantı ayarı değişir; node, repair ve compaction biter; ay sonu tepesi için node eklenmez; point-in-time recovery 35 gün. "
            "Eksimiz: taşıma desteklenmeyen özellikler listesiyle başlar (bu ekip kontrol etti); 40 TB veri bir kez taşınır; bağlantı havuzu bağlantı başına saniyede 3.000 sorgu sınırına göre ayarlanır; TTL silmesi ödenir. "
            "Bir koşul değişseydi: kod secondary index ya da materialized view kullansaydı ve işletme ekibi kalsaydı Cassandra on EC2 yarışa girerdi."))

USECASES_W["keyspaces"] = KEYSPACES_W
PAGE_SVC["keyspaces"] = "ks"


# ====================================================================== ElastiCache (Valkey) (page id "elasticache"), Turkish, model 2
# The ten workloads of the model 1 ElastiCache page (e2e_usecases.EC_USECASES), rebuilt: R1 in sub-items from R1_CATALOG,
# weights from the story, the best fit first. The model 1 data stays for the untouched English elasticache.html.
# Twins: ElastiCache and MemoryDB run the same Valkey engine, so they get the same R1 points on every card; only R2-R5
# separate them. The cards "session", "rate" and "reco" are the same workloads as the DynamoDB cards "session", "rate" and
# "ads": same rows, weights and points (the reasons name this page's features). The same mechanism gets the same reduction:
# ElastiCache R3 4 when a loss is accepted (no durable log in Serverless), 1 when the row wants "never lost";
# MemoryDB R4 6 (no serverless option, node type and shard count), R5 4-6 (node-hours for a small or peaky load);
# MemoryDB R2: the log commit of a write (single-digit ms) only where writes meet a latency limit.
# Sources of the limits and numbers in the reasons below (the hedges are the hedges of the source):
#  - Valkey: single-threaded command execution https://valkey.io/topics/latency/ ; transactions without rollback
#    https://valkey.io/topics/transactions/ ; expire error 0-1 ms https://valkey.io/commands/expire/ ; sorted sets O(log N)
#    https://valkey.io/topics/sorted-sets/ ; HyperLogLog 12 KB, 0.81% https://valkey.io/topics/hyperloglogs/ ; Pub/Sub
#    at-most-once https://valkey.io/topics/pubsub/ ; asynchronous replication and the lost-write window, lock release by a
#    script https://valkey.io/topics/cluster-spec/ , https://valkey.io/topics/distlock/ ; GEOSEARCH https://valkey.io/commands/geosearch/
#  - ElastiCache Serverless: 30,000 ECPU/s on an empty cache, doubling every 2-3 minutes, minimum ECPU ready within 60 minutes
#    https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Scaling-serverless.html ; ECPU per KB, 100 MB minimum for Valkey
#    https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/WhatIs.corecomponents.html ; 99.99% SLA, Multi-AZ
#    https://aws.amazon.com/elasticache/faqs/ ; supported commands (EVAL, SPUBLISH, GEOSEARCH yes; KEYS not on Serverless)
#    https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/SupportedCommands.html ; node-based Valkey 9.0 durability
#    https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/durability.html
#  - MemoryDB: Multi-AZ transaction log, microsecond reads, single-digit millisecond writes, node-based clusters
#    https://docs.aws.amazon.com/memorydb/latest/devguide/what-is-memorydb.html
#  - SQS: at-least-once delivery, messages stored in multiple AZs before the acknowledgement
#    https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues.html ; long polling up to
#    20 seconds https://aws.amazon.com/sqs/faqs/ ; dead-letter queue after maxReceiveCount
#    https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html
#  - DynamoDB TTL "within a few days", partition 3,000 read / 1,000 write units per second, conditional writes: see the
#    DynamoDB block above. Aurora MVCC, readers, PostGIS: see the Aurora block above.
from .e2e_usecases import EC_USECASES as _EM1  # noqa: E402

_EOLD = {uc["id"]: uc for uc in _EM1}
CATEGORY.setdefault("sqs", ("message queue", "mesaj kuyruğu"))
LINK.setdefault("sqs", "elasticache")      # SQS has no page yet; the ElastiCache page (card 8, M3) compares them
CATEGORY.setdefault("sns", ("publish-subscribe", "yayın-abone servisi"))
LINK.setdefault("sns", "elasticache")      # SNS has no page yet; the ElastiCache page (card 6) compares them


def estory(uid):
    return _EOLD[uid]["story"][1]


ELASTICACHE_W = []

# ------------------------------------------------------------------ 1. sessions (the DynamoDB card "session": same rows, weights, points)
ELASTICACHE_W.append(wusecase("session", 1, sim="w_session",
    title="Oturumlar ve login token'ları",
    key="Key: session id. Value: kullanıcı id'si, rol, son sayfa; bir hash ve bir TTL.",
    story=estory("session"),
    wnote="R1 toplam 55 ve en büyük: oturumun doğası (her istekte oku ve süresini yenile, 30 dakikada tam anında düş, milisaniyenin altında cevap ver) engine'in algoritmasıyla doğrudan ilgilidir. "
          "R2 20 ile ikinci: saniyede 40.000 okuma ve yenileme gün içinde dalgalanır. R3 5'te, en düşük sınırdadır: kaybolan oturum yalnız yeni bir login'dir.",
    rows=[
        row("EY", 10, "Soru her istekte sorulur ama basittir: id ile tek bir oturum. İş yükünü süre sonu ve hız ayırır.",
            "Tek soru: \"bu session id'nin oturumu\". Uygulama session id'yi cookie'den bilir. Oturum küçük bir nesnedir (1 KB'tan az).",
            "Bu okuma her HTTP isteğinin önündedir; key ile doğrudan gidilemezse her sayfa yavaşlar."),
        row("YD", 20, "Oturumun güvenliği süre sonuna bağlıdır: süresi dolan oturum asla okunmamalı.",
            "Oturum 30 dakika hareketsizlikten sonra düşmeli; 30 dakika 1 saniye sonra gelen istek yeni login'e gitmeli. Süre her sayfa görüntülemede yenilenmeli.",
            "Süresi dolmuş bir oturum hâlâ okunabiliyorsa, ortak bir bilgisayarda bırakılan oturum başkası tarafından kullanılabilir. Bu bir güvenlik açığıdır."),
        row("OY", 10, "Her istekte bir okuma ve bir yenileme olur; ikisinin tek işlem olması isteği yarıya indirir.",
            "Her istekte oturumu oku ve süresini yenile; bu, uygulama kodunda tek satır ve mümkünse tek istek olmalı.",
            "Okuma ve yenileme iki ayrı istekse saniyede 40.000 sayfa için 80.000 istek gerekir ve her sayfa iki gidiş-dönüş bekler."),
        row("DA", 15, "1 ms sınırı bir trafik sayısı değil, engine'in veriyi nerede ve nasıl tuttuğunun sonucudur.",
            "Okuma 1 milisaniyenin altında dönmeli, çünkü her sayfa isteğine eklenir.",
            "Disk tabanlı bir engine'in tek haneli milisaniyesi bile günde milyonlarca sayfada hissedilir: 5 ms her sayfaya 5 ms ekler."),
        row("R2", 20, "Saniyede 40.000 okuma ve 40.000 yenileme, gün içinde dalgalı.",
            "Saniyede 40.000 okuma ve 40.000 süre yenilemesi; öğle ve akşam tepeleri gece trafiğinin birkaç katı. Tepe anında da cevap aynı hızda kalmalı.",
            "Tepe anında yavaşlayan bir oturum store'u bütün sayfaları birlikte yavaşlatır; kampanya akşamı en çok ziyaretçi en yavaş sayfayı görür."),
        row("R3", 5, "Kaybolan oturum yalnız yeni bir login'dir; sepet ve sipariş başka yerde kalıcıdır.",
            "Düşük: kaybolan oturum yeni bir login'dir. Bir arızada bütün kullanıcıların yeniden login olması kabul edilir ama istenmez.",
            "Oturum türetilmiş bir veridir; kaynağı kullanıcı hesabıdır. Kaybı can sıkıcıdır, zararlı değildir."),
        row("R4", 10, "Ekip sunucu istemiyor; ama oturum basit bir iş yüküdür ve operasyon farkı küçüktür.",
            "Ekip sunucu, node ve yama istemiyor; serverless tercih. Süre yenileme uygulama kodunda tek satır olmalı.",
            "Oturum altyapısı ürün değildir; ekibin zamanını almamalıdır. Yenileme karmaşıksa geliştiriciler onu atlar ve oturumlar erken düşer."),
        row("R5", 10, "Veri küçük ve kısa ömürlüdür; fark istek başına fiyatta ve sürekli çalışan kapasitededir.",
            "Trafik dalgalı; istek ya da kullanım başına ödeme. Toplam oturum verisi birkaç GB'ı geçmez.",
            "Kısa ömürlü küçük veri için GB fiyatı az etkilidir, istek fiyatı belirleyicidir; saniyede 80.000 istek aylık faturada görünür."),
    ],
    cands=["ec", "mdb", "ddb"],
    scores={
        "ec": [sc(10, "GET ya da HGETALL lm:session:{id} key ile doğrudan, bellekten okumadır (Ö1). Puan kırılmadı."),
               sc(10, "EXPIRE süreyi milisaniye hassasiyetle uygular; süresi dolmuş bir key hiçbir okumada dönmez (Ö4). Puan kırılmadı."),
               sc(10, "GETEX lm:session:{id} EX 1800 oturumu okur ve süresini aynı komutta yeniler; tek istek, tek satır (Ö3). Puan kırılmadı."),
               sc(10, "Valkey bütün veriyi bellekteki bir hash table'da tutar; komut mikrosaniyelerdedir ve AWS'e göre Serverless'ta okumaların yarısı (p50) 1 ms'nin altında döner (Ö1). Puan kırılmadı: Lale Market'in 1,3–1,8 ms ölçümü (B1–B5) Python istemcisi ve TLS dahil uçtan uca süredir; bu satır engine'in kendi süresini puanlar."),
               sc(10, "Serverless belleği ve trafiği izleyip kendisi büyür; okumalar tepe anında da milisaniyenin altındadır (Ö6). Puan kırılmadı."),
               sc(4, "Serverless veriyi birkaç AZ'de replica olarak tutar ve failover yapar (Ö7), ama her yazmayı kalıcı bir log'a yazmaz. 6 puan kırıldı: bir arızada son oturumlar kaybolabilir ve kullanıcılar yeniden login olur; bu kartta kabul edilen bir sonuçtur."),
               sc(10, "Serverless: node, yama ve kapasite planı yoktur. Puan kırılmadı."),
               sc(8, "Saklanan veri (GB-saat) ve istek (ECPU) başına ödenir. 2 puan kırıldı: bellekteki GB pahalıdır; ama oturum verisi birkaç GB'ı geçmediği için fark küçüktür.")],
        "mdb": [sc(10, "Aynı Valkey engine'i: key ile doğrudan, bellekten okuma. Puan kırılmadı."),
                sc(10, "EXPIRE aynı biçimde milisaniye hassasiyetle çalışır. Puan kırılmadı."),
                sc(10, "GETEX okuma ve yenilemeyi tek komutta yapar; engine aynıdır. Puan kırılmadı: MemoryDB'de bu komutun bir yazma olarak log'u beklemesi servisin tasarımıdır ve R2'de sayılır."),
                sc(10, "Veri bellekteki hash table'dadır; okumalar mikrosaniyelerdedir. Puan kırılmadı."),
                sc(7, "Okumalar mikrosaniyede kalır. 3 puan kırıldı: süre yenilemesi bir yazmadır ve MemoryDB yazmayı çoklu AZ'li log'a işledikten sonra onaylar (tek haneli milisaniye). 1 ms sınırı için okuma GET ile yapılır ve süre her istekte değil, kalan süre yarıya indiğinde ayrı bir komutla yenilenir (B5); o isteklerde gecikme milisaniyelere çıkar. Kart 3'te her istek bir INCR yazmasıdır ve kırılım bu yüzden daha büyüktür (5)."),
                sc(10, "Her yazma çoklu AZ'li bir transaction log'unda kalıcıdır; bir arıza oturum kaybetmez. Puan kırılmadı."),
                sc(6, "Yama ve failover yönetilir. 4 puan kırıldı: MemoryDB'de serverless seçenek yoktur; node tipi, shard ve replica sayısı ekibin işidir."),
                sc(5, "Node saat başına ödenir. 5 puan kırıldı: dalgalı trafiğe rağmen node'lar tepe için boyutlanır ve gece de ödenir; bu kartın istemediği dayanıklılığa para verilir.")],
        "ddb": [sc(10, "GetItem session id ile doğrudan okumadır. Puan kırılmadı."),
                sc(6, "TTL alanı süresi dolan oturumu siler ve okuma bir koşulla süresi dolmuş oturumu reddedebilir. 4 puan kırıldı: silme \"genellikle birkaç gün içinde\" olur; \"süresi dolan asla okunmamalı\" isteği ancak uygulamanın her okumada expires_at'i karşılaştırmasıyla karşılanır."),
                sc(6, "UpdateItem SET expires_at ve ReturnValues = ALL_NEW okuma ve yenilemeyi tek istekte yapar. 4 puan kırıldı: böylece her sayfa görüntüleme bir yazma olur ve yazma okumadan yavaştır (fiyatı R5'te sayıldı)."),
                sc(5, "Veri SSD'deki partition'lardadır; key ile okuma tek haneli milisaniyedir. 5 puan kırıldı: 1 ms sınırı tek başına karşılanmaz; mikrosaniye için önüne DAX (DynamoDB'nin bellek içi cache'i) konmalıdır."),
                sc(10, "Partition'lara dağılım 40.000 okumayı ve yazmayı kolayca taşır. Puan kırılmadı: gecikme engine'in depolamasından gelir ve R1.4'te (DA) bir kez sayıldı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı: bu satırda en güçlü aday, ama bu kartta dayanıklılık en düşük ağırlıktadır."),
                sc(10, "Serverless. Puan kırılmadı: süre kontrolünün kodu R1.2'de sayıldı."),
                sc(6, "İstek başına ödenir. 4 puan kırıldı: her sayfada bir yenileme yazması, saniyede 40.000 yazma birimi demektir; bellek içi store'un istek fiyatından çok yüksektir.")],
    },
    h2h={
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. Bu karşılaştırma R1 ile R3–R5'in farkını en net gösteren karşılaştırmadır: iki aday aynı Valkey engine'ini çalıştırır ve R1'in dört alt maddesinde ikisi de tam puan alır. "
               "Fark yalnız üreticinin servis tasarımındadır. MemoryDB her yazmayı çoklu AZ'li bir log'a işler; bu, oturumu bir arızadan korur ama her süre yenilemesini tek haneli milisaniyelik bir yazmaya çevirir (R2). "
               "Serverless seçeneği olmadığı için node'lar tepe için boyutlanır ve gece de ödenir (R4, R5). Bu kartta dayanıklılığın ağırlığı en düşük sınırdadır (5), çünkü kaybolan oturum yalnız yeni bir login'dir. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: oturum kaybı pahalı olsaydı (örneğin bir bankacılık işleminin ortasındaki oturum) ya da oturumda yeniden kurulamayan bir durum (çok adımlı bir başvuru formu) tutulsaydı.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB bu kartta üçüncüdür ve nedeni R1'dedir, yani engine'in doğasındadır. "
               "Oturumun iki temel ihtiyacı DynamoDB'nin algoritmasıyla çelişir: süre sonu tam anında olmalıdır, ama DynamoDB TTL'i arka planda ve günler içinde siler; okuma milisaniyenin altında olmalıdır, ama DynamoDB veriyi SSD'deki partition'larda tutar. "
               "Okuma ve yenileme tek bir UpdateItem olabilir, ama bu her sayfayı bir yazmaya çevirir ve R5'te faturayı büyütür. DynamoDB'nin güçlü olduğu dayanıklılık ise bu kartta en düşük ağırlıktadır. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: oturum kaybı kabul edilemez olsaydı ve 5–10 ms yeterli olsaydı, ya da oturum okuması her istekte değil yalnız login'de yapılsaydı (imzalı token kullanan bir mimaride yalnız iptal listesi tutulsaydı).",
    },
    verdict="Karar: ElastiCache {ec}, MemoryDB {mdb}, DynamoDB {ddb}. Bu iş yüküne en uygun servis ElastiCache'tir. Engine uyumunda iki Valkey servisi eşittir (55'te 55); ElastiCache'i öne geçiren serverless işletimi ve bu kartın istemediği dayanıklılığa para ödetmemesidir. "
            "ElastiCache seçtiğimizde artımız: tek komutla oku ve yenile, saniyesinde düşen oturum, mikrosaniye okuma ve sunucusuz işletim. "
            "Eksimiz: bir arızada son oturumlar kaybolabilir; uygulama \"oturum yok\" durumunu login'e yönlendirerek sakin karşılamalı ve sepet gibi değerli durumu oturumda değil kalıcı store'da tutmalıdır. Bir koşul değişseydi: oturum kaybı pahalı olsaydı MemoryDB kazanırdı."))

# ------------------------------------------------------------------ 2. live leaderboard (Lale Market)
ELASTICACHE_W.append(wusecase("board", 2, sim="w_board",
    title="Canlı liderlik tabloları (Lale Market)",
    key="Key: lm:leaderboard. Value: bir sorted set; member müşteri id'si, score gelir.",
    story=estory("board"),
    wnote="R1 toplam 45: tablonun üç engine sorusu (ilk 10 ve \"kaçıncı sıradayım\" nasıl sorulur, bir sipariş skora nasıl eklenir, sıra nerede tutulur) her okumada ve her checkout'ta çalışır. "
          "R2 20 ile ikinci: kampanya akşamı en çok sipariş ve en çok okuma aynı anda gelir. R3 15'tir: tablo yeniden kurulabilir, ama 4 dakikalık boş bir vitrin görünür bir kesintidir.",
    rows=[
        row("EY", 20, "Ana sayfayı açan her müşteri kendi sırasını sorar; saniyede 3.000 sıra sorgusu bu iş yükünün en sık sorusudur.",
            "İki soru: \"ilk 10, skorlarıyla\" ve \"bu müşteri 2 milyon müşteri arasında kaçıncı sırada\". İkisi de her okumada güncel olmalı.",
            "Sıra sorusunun ucuz bir yolu yoksa her sorgu, müşterinin üstündeki herkesi saymak demektir; 2 milyon müşteride bu her okumada binlerce satır okumaktır."),
        row("OY", 15, "Her checkout bir ekleme yapar ve aynı müşterinin iki siparişi aynı anda gelebilir.",
            "\"Bu müşterinin skoruna şu tutarı ekle\" okumadan ve atomik olmalı; aynı anda gelen iki siparişin ikisi de sayılmalı ve müşteri hemen yeni sırasına geçmeli.",
            "Önce okuyup sonra yazan bir ekleme bir siparişi kaybeder; ay sonu hediyesi yanlış kişiye gider."),
        row("DA", 10, "Sıranın yazma anında korunması engine'in veri yapısına bağlıdır; okumanın 10 ms sınırı da buradan gelir.",
            "Sıra yazma anında korunmalı, okuma anında sıralama yapılmamalı. Okuma 10 ms'nin altında dönmeli.",
            "Okuma anında 2 milyon müşteriyi sıralamak saniyede 3.000 okumada imkânsızdır; ana sayfa tablonun gelmesini bekler."),
        row("R2", 20, "Kampanya akşamı saniyede 400 sipariş ve 3.000 okuma aynı anda gelir.",
            "Normal günde saniyede 20, kampanyada 400 ekleme; her zaman saniyede yaklaşık 3.000 okuma. Tepe anında da okuma 10 ms'nin altında kalmalı.",
            "Ana sayfa tabloyu bekler; tepe anında yavaşlayan tablo kampanya akşamının bütün ana sayfalarını yavaşlatır."),
        row("R3", 15, "Tablo siparişlerden yeniden kurulur, ama 4 dakikalık boş bir vitrin müşteriye görünür.",
            "Orta: tablo Aurora'daki siparişlerden 4 dakikada yeniden hesaplanır. Bir arızada bu 4 dakika kabul edilir; ay sonu hediyesi tablodan değil siparişlerden verilir.",
            "Kayıp bir vitrin kesintisidir, para kaybı değildir; ama kampanya akşamı boş bir tablo \"bir şey bozuk\" izlenimi verir."),
        row("R4", 10, "İki geliştirici sunucu istemiyor; yeniden kurma işi (Seed) zaten var.",
            "İki geliştirici, sunucu istemiyor. Yeniden hesap işi zaten var (Admin Console'daki Seed); başka bir iş yazılmamalı.",
            "Küçük ekipte her yeni bileşen bir nöbet listesi demektir."),
        row("R5", 10, "Veri küçüktür; belirleyici olan okuma fiyatı ve boş saatlerde ödenen minimumdur.",
            "2 milyon member birkaç yüz MB tutar. Okuma hacmi yüksek, yazma hacmi düşük; trafik kampanya akşamlarında sıçrar.",
            "Küçük veride GB fiyatı az etkilidir; boş saatlerde sürekli çalışan kapasite ve okuma başına fiyat faturayı belirler."),
    ],
    cands=["ec", "mdb", "ddb"],
    scores={
        "ec": [sc(10, "ZREVRANGE lm:leaderboard 0 9 WITHSCORES ilk 10'u, ZREVRANK bir müşterinin sırasını tek komutla verir (Ö2). Puan kırılmadı."),
               sc(10, "ZINCRBY skoru okumadan ve atomik artırır, member'ı hemen yeni yerine taşır; komutlar sırayla çalıştığı için iki sipariş de sayılır (Ö3). Puan kırılmadı."),
               sc(10, "Sorted set sırayı her yazmada O(log N) ile korur ve bellektedir; okuma anında sıralama yoktur, cevap mikrosaniyelerdedir (Ö1, Ö2). Puan kırılmadı."),
               sc(10, "Serverless saniyede 3.000 okumayı ve 400 eklemeyi kendisi taşır (Ö6). Puan kırılmadı."),
               sc(9, "Replica'lar bir node arızasında tabloyu ayakta tutar (Ö7) ve kalıcı log yoktur, ama tablo bir kopyadır: her skor Aurora'daki siparişlerde vardır ve Seed tabloyu 4 dakikada yeniden kurar; kart bu 4 dakikayı kabul eder. 1 puan kırıldı: bir arızadan sonra tablo yeniden kurulana kadar eksik görünür (yeniden kurma dakikalar sürerse 1, bir saat ve üstü 2 puan)."),
               sc(10, "Serverless; ZINCRBY checkout kodunda tek satırdır ve yeniden kurma işi zaten vardır. Puan kırılmadı."),
               sc(9, "GB-saat ve ECPU başına ödenir: birkaç yüz MB yaklaşık 22 dolar, saniyede 3.000 okuma ve eklemenin yaklaşık 6.000 ECPU'su ayda yaklaşık 43 dolar; toplam yaklaşık 65 dolar. 1 puan kırıldı: sorted set komutları basit bir GET'ten daha fazla ECPU harcar ve kampanya akşamı fatura büyür.")],
        "mdb": [sc(10, "Aynı Valkey engine'i: ZREVRANGE ve ZREVRANK. Puan kırılmadı."),
                sc(10, "Aynı Valkey engine'i: ZINCRBY okumadan ve atomik. Puan kırılmadı."),
                sc(10, "Aynı sorted set, bellekte. Puan kırılmadı."),
                sc(9, "Okumalar mikrosaniyededir. 1 puan kırıldı: her ZINCRBY çoklu AZ'li log'a işlendikten sonra onaylanır (tek haneli milisaniye); 10 ms sınırının içindedir ama checkout biraz daha bekler."),
                sc(10, "Her ekleme transaction log'unda kalıcıdır; bir arıza tabloyu boşaltmaz ve 4 dakikalık boş vitrin olmaz. Puan kırılmadı."),
                sc(6, "Yama ve failover yönetilir. 4 puan kırıldı: serverless seçenek yoktur; node tipi, shard ve replica sayısı ekibin işidir."),
                sc(7, "Node saat başına ödenir; Valkey'de ayda 10 TB'a kadar yazılan veri ücretsizdir. 3 puan kırıldı: birkaç yüz MB için iki küçük node (db.t4g.small, primary ve replica) ayda yaklaşık 55 dolardır ve ElastiCache'in yaklaşık 65 dolarına yakındır; ama t4g bir burstable node'dur ve kampanya akşamı için güvenli boy (iki db.r7g.large) ayda yaklaşık 380 dolardır.")],
        "ddb": [sc(4, "\"İlk 10\", skoru sort key olan bir ikinci index'te (GSI) ters sırayla ve Limit 10 ile tek bir okumadır. 6 puan kırıldı: \"kaçıncı sıradayım\" sorusunun yolu yoktur; müşterinin üstündeki bütün value'lar sayılır ve 2 milyon müşteride bu binlerce okumadır."),
                sc(7, "UpdateItem ADD skoru okumadan ve atomik artırır. 3 puan kırıldı: sırayı tutan ikinci index asenkron güncellenir; müşteri yeni sırasını bir an geç görebilir ve aynı anda okunan ilk 10 eski olabilir."),
                sc(8, "Index sırayı yazma anında korur; okuma SSD'den tek haneli milisaniyedir. 2 puan kırıldı: 10 ms sınırının içindedir ama payı küçüktür."),
                sc(7, "On-demand mod sıçramayı izler. 3 puan kırıldı: bütün müşteriler index'te tek bir partition key altında durur ve bir partition saniyede yaklaşık 3.000 okuma ve 1.000 yazma birimi için tasarlanmıştır; kampanya akşamı key'i bölmek ve ilk 10'ları birleştirmek gerekir."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(10, "Serverless. Puan kırılmadı: key'in bölünmesi R2'de sayıldı."),
                sc(8, "İstek başına ödenir. 2 puan kırıldı: her ekleme table'a ve index'e iki yazma birimidir (sıra sorgusunun okumaları R1.1'de sayıldı).")],
    },
    h2h={
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. İkiz servisler: aynı Valkey engine'i, aynı sorted set ve aynı komutlar; R1'de ikisi de 45'te 45 alır, bu yüzden kararı yalnız servis tasarımı verir. "
               "MemoryDB'nin log'u R3'te bir artıdır: bir arıza tabloyu boşaltmaz. Ama tablo bir kopyadır: her skor Aurora'daki siparişlerde vardır ve Seed tabloyu 4 dakikada yeniden kurar; kopya kuralıyla bu artı yalnız 1,5 puandır (10'a 9). "
               "Geri kalan satırlar ElastiCache'e döner: her ZINCRBY'nin log'a işlenmesi R2'de 2 puan, serverless seçeneğin olmaması ve node tipi ile replica sayısının ekibe kalması R4'te 4 puan, kampanya akşamı için güvenli node boyu R5'te 2 puan farkla ElastiCache'i öne geçirir; fark 6,5 puandır. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: tablo siparişlerden yeniden hesaplanamasaydı, yani skorlar başka hiçbir yerde olmasaydı ve ay sonu hediyesi doğrudan tablodan verilseydi, ya da yeniden kurma saatler sürseydi; o zaman tablo bir kopya değil tek yer olurdu, ElastiCache R3'te 4 alırdı ve MemoryDB 91'e 90 kazanırdı.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. Bu kart Valkey engine'inin özelliklerinin iş yükünün kendisi olduğu karttır: R1'de iki Valkey servisi DynamoDB'nin 18,5 puan önündedir. "
               "DynamoDB ilk 10'u bir ikinci index ile verebilir, ama \"kaçıncı sıradayım\" sorusunu soramaz: sıra bir sayımdır ve 2 milyon müşteride her sorgu binlerce okumadır. Sorted set ise sırayı yazma anında tutar ve ZREVRANK onu tek adımda verir. "
               "DynamoDB'nin dayanıklılığı bu kartta küçük bir artıdır, çünkü tablo bir kopyadır (R3'te 10'a 9), ama bütün müşterilerin tek bir index partition key'inde durması kampanya akşamı key'i bölmeyi ve ilk 10'ları birleştirmeyi ister. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: kimse kendi sırasını sormasaydı (yalnız ilk 10 gösterilseydi), sıra saatte bir hesaplansaydı ve skorlar başka hiçbir yerde olmayan kalıcı bir kayıt olsaydı.",
    },
    verdict="Karar: ElastiCache {ec}, MemoryDB {mdb}, DynamoDB {ddb}. Bu iş yüküne en uygun servis ElastiCache'tir. Engine uyumunda iki Valkey servisi eşittir ve DynamoDB'nin çok önündedir; kararı servis tasarımı verir: tablo 4 dakikada yeniden kurulan bir kopyadır, bu yüzden MemoryDB'nin log'u R3'te yalnız 1,5 puan getirir, ElastiCache'in sunucusuz işletimi ve faturası ise R2, R4 ve R5'te 8 puan getirir. "
            "ElastiCache seçtiğimizde artımız: ilk 10 ve kişisel sıra tek komut, eklemede yarış yok, node yok; Lale Market bugün bunu yapar. "
            "Eksimiz: bir arızada tablo eksik ya da boş görünebilir; uygulama Seed'i bir arıza adımı olarak yazmalı, ay sonu hediyesini tablodan değil Aurora'daki siparişlerden hesaplamalı ve her ay için yeni bir key (lm:leaderboard:2026-10) açıp eski aya süre vermelidir. Bir koşul değişseydi: tablo siparişlerden yeniden kurulamasaydı ve tek yer bellek olsaydı MemoryDB kazanırdı."))

# ------------------------------------------------------------------ 3. rate limits (the DynamoDB card "rate": same rows, weights, points)
ELASTICACHE_W.append(wusecase("rate", 3,
    title="Rate limit'ler ve sayaçlar",
    key="Key: kullanıcı id'si ve dakika. Value: bir sayı (string), TTL 60 saniye.",
    story=estory("rate"),
    wnote="R1 toplam 55 ve en büyük: sayacın biçimi (okumadan artır), engine'in veriyi nerede tuttuğu (2 ms sınırı) ve dakika bitince silinmesi bu iş yükünün kendisidir. "
          "R2 20 ile ikinci: saniyede 20.000 artırma günün her saatinde gelir. R3 5'te, en düşük sınırdadır: kaybolan sayaç bir dakikalığına fazladan 100 istektir. R5 10'dur, çünkü ayda 52 milyar yazmanın fiyatı belirleyicidir.",
    rows=[
        row("OY", 20, "Her API isteği bir artırmadır; engine bunu okumadan ve atomik yapmalı.",
            "\"Bu kullanıcının bu dakikadaki sayacını 1 artır ve yeni değeri döndür\" tek adımda ve atomik olmalı; aynı anda gelen iki istek ikisi de sayılmalı.",
            "Oku-artır-yaz üç adımsa iki istek aynı değeri okur ve biri kaybolur; sınır aşılır."),
        row("DA", 15, "2 ms sınırı engine'in veriyi bellekte mi diskte mi tuttuğuyla belirlenir.",
            "Her artırma 2 ms'nin altında dönmeli, çünkü her API isteğinin önündedir.",
            "Gecikme her API isteğine eklenir; disk tabanlı bir yazmanın tek haneli milisaniyesi bütün API'ı yavaşlatır."),
        row("YD", 15, "Sayaç dakika bitince değersizdir ve dakikada bir milyonlarca yeni sayaç doğar.",
            "Eski dakikaların sayaçları kendiliğinden silinmeli.",
            "Silinmeyen sayaçlar her dakika birikir; bir temizlik işi bu kadar kaydı silemez."),
        row("EY", 5, "Soru basittir: kullanıcı ve dakika ile tek bir sayaç; bu kartın riski artırma biçiminde ve gecikmededir.",
            "Tek soru: \"bu kullanıcının bu dakikadaki sayacı\".",
            "Key ile doğrudan gidilemezse her API isteği yavaşlar."),
        row("R2", 20, "Saniyede 20.000 artırma, düz; gecikme sınırı katıdır.",
            "Saniyede 20.000 artırma, günün her saati; 12 gateway sunucusu aynı sayacı paylaşır. Artırma tepe anında da 2 ms'nin altında kalmalı.",
            "Sayaç her isteğe eklenen sabit bir gecikmedir; 2 ms ile 8 ms arasındaki fark günde 1,7 milyar istekte toplam saatler eder."),
        row("R3", 5, "Kaybolan sayaç bir dakikalığına fazladan 100 istektir; zararsızdır.",
            "Düşük: kaybolan sayaç bir dakikalığına fazladan 100 istek demektir.",
            "Rate limit bir koruma kalkanıdır, muhasebe kaydı değildir; bir dakikalık boşluk kabul edilir."),
        row("R4", 10, "Platform ekibi serverless tercih eder.",
            "Platform ekibi sunucu istemiyor. Sayaç mantığı gateway kodunda birkaç satır olmalı.",
            "Gateway en çok değişen koddur; sayaç karmaşıksa her değişiklik risk taşır."),
        row("R5", 10, "Her artırma bir yazmadır; ayda 52 milyar yazmanın fiyatı bu iş yükünün maliyetidir.",
            "Saniyede 20.000 yazma, ayda 52 milyar. Yazma başına fiyat bu iş yükünün bütün maliyetidir.",
            "Yazma birimi fiyatındaki küçük bir fark ayda on binlerce dolardır."),
    ],
    cands=["ec", "mdb", "ddb"],
    scores={
        "ec": [sc(10, "INCR sayacı okumadan, atomik artırır ve yeni değeri döndürür; Valkey komutları sırayla çalıştırır (Ö3). Puan kırılmadı."),
               sc(10, "Sayaç bellekteki hash table'dadır; INCR mikrosaniyelerde döner (Ö1). Puan kırılmadı."),
               sc(10, "INCR ve EXPIRE 60 tek bir MULTI/EXEC'te gönderilir, böylece arada bir çökme sayacı süresiz bırakmaz; sayaç dakika sonunda tam anında gider (Ö4). Puan kırılmadı."),
               sc(10, "Key ile doğrudan erişim (Ö1). Puan kırılmadı."),
               sc(10, "Serverless kendi kendine ölçeklenir; saniyede 20.000 artırma küçük bir yüktür (Ö6). Puan kırılmadı."),
               sc(4, "Kalıcı bir yazma log'u yoktur. 6 puan kırıldı: bir arızada sayaçlar sıfırlanabilir; bu kartta zararsızdır."),
               sc(10, "Serverless; INCR ve EXPIRE gateway kodunda iki satırdır. Puan kırılmadı."),
               sc(9, "ECPU başına ödenir ve basit bir INCR yaklaşık 1 ECPU'dur. 1 puan kırıldı: sayaçlar az yer tutsa da Serverless'ta en az 100 MB saklama ödenir.")],
        "mdb": [sc(10, "Aynı Valkey engine'i: INCR okumadan ve atomik. Puan kırılmadı."),
                sc(10, "Aynı Valkey engine'i: sayaç bellekteki hash table'dadır. Puan kırılmadı: yazmanın log'a işlenmesi engine'in değil servisin tasarımıdır ve R2'de sayılır."),
                sc(10, "EXPIRE aynı biçimde tam anındadır. Puan kırılmadı."),
                sc(10, "Key ile doğrudan erişim. Puan kırılmadı."),
                sc(5, "Shard ekleyerek yazma ölçeklenir. 5 puan kırıldı: MemoryDB her yazmayı çoklu AZ'li log'a işledikten sonra onaylar; INCR bir yazma olduğu için tek haneli milisaniye 2 ms sınırını birçok istekte aşar."),
                sc(10, "Her yazma kalıcıdır. Puan kırılmadı: ama bu kartta dayanıklılık önemsizdir."),
                sc(6, "Yönetilen node'lar. 4 puan kırıldı: serverless seçenek yoktur; node tipi ve shard sayısı ekibin işidir."),
                sc(6, "Node saat başına ödenir; Valkey'de ayda 10 TB'a kadar yazılan veri ücretsizdir. 4 puan kırıldı: node'lar saniyede 20.000 yazmanın log gecikmesini taşıyacak shard sayısıyla sürekli çalışır ve bu kartın istemediği dayanıklılığa para verilir.")],
        "ddb": [sc(9, "UpdateItem ADD count :1 ve ReturnValues = UPDATED_NEW sayacı okumadan artırır ve yeni değeri döndürür. 1 puan kırıldı: ADD sınırı bilmez; \"en fazla 100\" kuralı bir koşulla (count < 100) eklenirse koşul yanlış çıktığında yeni değer dönmez ve uygulama ayrı bir hata yolunu işler."),
                sc(4, "Veri SSD'deki partition'lardadır; yazma tek haneli milisaniyedir. 6 puan kırıldı: 2 ms sınırı yazma yolunda karşılanmaz ve DAX yazmaları hızlandırmaz."),
                sc(6, "Key dakikayı içerdiği için eski sayaçlar okunmaz ve TTL onları siler. 4 puan kırıldı: silme günler içinde olur ve o arada her dakikanın milyonlarca sayacı storage'da birikir."),
                sc(10, "Key ile doğrudan erişim. Puan kırılmadı."),
                sc(10, "Yazmalar kullanıcı ve dakikaya göre partition'lara dağılır. Puan kırılmadı: gecikme engine'in depolamasından gelir ve R1.2'de (DA) bir kez sayıldı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı: ama bu kartta dayanıklılık önemsizdir."),
                sc(10, "Serverless. Puan kırılmadı."),
                sc(4, "Trafik düz olduğu için provisioned kapasite on-demand'den ucuzdur. 6 puan kırıldı: saniyede 20.000 yazma birimi us-east-1 liste fiyatıyla yine de ayda yaklaşık 9.500 dolardır; aynı artırmalar ElastiCache'te ECPU olarak ayda birkaç yüz doları geçmez.")],
    },
    h2h={
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. İki aday aynı Valkey engine'ini çalıştırır: INCR ve EXPIRE ikisinde de aynıdır ve R1'de ikisi de 55'te 55 alır. Fark yalnız servis tasarımındadır: "
               "MemoryDB her yazmayı çoklu AZ'li bir log'a işledikten sonra onaylar; INCR bir yazma olduğu için cevap tek haneli milisaniyeye çıkar ve 2 ms sınırı riske girer (R2). "
               "Bu kartta dayanıklılığın ağırlığı en düşük sınırdadır, çünkü kaybolan sayaç zararsızdır; yani MemoryDB'nin bedelini ödediği şey bu iş yükünün istemediği bir güvencedir. "
               "Serverless seçeneğinin olmaması R4'te de puan kaybettirir. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: sayaç bir kota ya da faturalama sayacı olsaydı (örneğin \"ayda 1 milyon ücretsiz istek\") ve kaybı para demek olsaydı.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB bu kartta üçüncüdür. Atomik sayaç DynamoDB'nin de çekirdek özelliğidir: ADD ve UPDATED_NEW aynı işi tek istekte yapar. "
               "Ama R1'in iki satırı DynamoDB'nin doğasına ters düşer: veri SSD'dedir ve yazma tek haneli milisaniyedir, oysa sınır 2 ms'dir; TTL günler içinde siler, oysa dakikada milyonlarca yeni sayaç doğar. "
               "R5'te fark en büyüktür: her artırma bir yazma birimidir ve ayda 52 milyar yazma, aynı artırmaların ElastiCache'teki fiyatının çok katıdır. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: sınır dakika değil gün başına olsaydı (günde 10.000 istek), istek hızı yüz kat düşük olsaydı ve sayaç kaybı kabul edilemeseydi.",
    },
    verdict="Karar: ElastiCache {ec}, MemoryDB {mdb}, DynamoDB {ddb}. Bu iş yüküne en uygun servis ElastiCache'tir ve bu kart sayfanın en net kazanmasıdır: engine uyumunda MemoryDB ile eşittir, DynamoDB'nin önündedir; MemoryDB'yi geride bırakan log'un yazma gecikmesi ve node işletimidir. "
            "ElastiCache seçtiğimizde artımız: tek komutta atomik artırma, mikrosaniye cevap, dakika sonunda kendiliğinden giden sayaçlar ve düşük fatura. "
            "Eksimiz: bir arızada sayaçlar sıfırlanabilir; uygulama bunu \"bir dakikalık fazladan izin\" olarak kabul etmeli, sayacı faturalamada kullanmamalı ve cache'e hiç ulaşılamazsa ne yapılacağına önceden karar vermelidir: istekleri geçirmek (fail-open) ya da gateway sunucusunda kaba bir yerel sınır uygulamak. Bir koşul değişseydi: sayaç günlük ve kaybı pahalı olsaydı DynamoDB ya da MemoryDB öne çıkardı."))

# ------------------------------------------------------------------ 4. cache-aside for the product page (both together: ElastiCache in front of Aurora)
ELASTICACHE_W.append(wusecase("cache", 4,
    title="Ürün sayfası için cache-aside (Lale Market)",
    key="Key: product:P0001. Value: ürün sayfasının JSON'u, TTL 300 saniye.",
    story=estory("cache"),
    wnote="R1 toplam 50: sayfa verisinin nasıl sorulduğu (hazır cevap mı, her seferinde bir JOIN mi), cevabın kaynağa göre ne kadar eski olabileceği, nerede tutulduğu ve kopyanın nasıl bittiği. "
          "R2 20 ile ikinci: kampanya akşamı okuma on kat artar ve Aurora writer'ı checkout için serbest kalmalıdır. Diğer üç satır 10'dur: cache bir kopyadır, ekip küçüktür, sıcak veri küçüktür.",
    rows=[
        row("EY", 15, "Her ürün sayfası açılışı bu soruyu sorar; aynı 50 ürün saniyede binlerce kez istenir.",
            "Tek soru: \"bu ürünün sayfa verisi\" (ürün, stok durumu, ortalama puan). Uygulama ürün id'sini URL'den bilir. Aynı cevap her açılışta yeniden hesaplanmamalı.",
            "Sayfa her açılışta üç table'lı aynı JOIN'i çalıştırırsa aynı 50 ürün için saniyede binlerce kez aynı cevap hesaplanır."),
        row("TA", 10, "Fiyat değişikliği müşteriye en geç 5 dakikada görünmelidir; daha eski bir fiyat bir şikâyettir.",
            "Cevap kaynağa göre en fazla 5 dakika eski olabilir. Fiyat değişince eski kopya hemen silinebilmeli. Checkout fiyatı ve stoğu yine Aurora'dan kontrol eder.",
            "5 dakikadan eski bir fiyat bir müşteri şikâyetidir; kopyanın ne zaman yenileneceği bilinmiyorsa eski veri hataları bulunması zor hatalara dönüşür."),
        row("DA", 15, "10 ms sınırı ve writer'ın yükü, cevabın hazır mı yoksa hesaplanarak mı geldiğiyle belirlenir.",
            "Sayfa verisi 10 ms içinde gelmeli. Okuma hazır bir cevabın okunması olmalı, bir sorgunun çalıştırılması değil.",
            "Her açılışta çalışan bir sorgu 8 ms sürer ve CPU harcar; kampanya akşamı saniyede 6.000 kez çalışırsa checkout ile aynı kaynakları paylaşır."),
        row("YD", 10, "Kopyalar kendiliğinden bitmezse soğuyan ürünlerin kopyaları birikir ve eski veri kalır.",
            "Her kopya 5 dakika sonra kendiliğinden gitmeli; bir temizlik işi olmamalı.",
            "Biten kopyalar silinmezse soğuk ürünlerin eski sayfaları yer tutar ve bir gün eski fiyatla geri döner."),
        row("R2", 20, "Kampanya akşamı on kat okuma; writer checkout'u yapar ve yavaşlamamalıdır.",
            "Kampanya akşamı saniyede 6.000 görüntüleme, yüzde 80'i 50 ürüne. Aurora writer'ının yükü kampanya akşamı normal günden fazla olmamalı.",
            "Okuma yükü writer'a binerse checkout yavaşlar; kampanyanın en değerli işlemi en çok zarar gören işlem olur."),
        row("R3", 10, "Kopya veri kaybı değildir, ama boşalan bir cache bütün yükü Aurora'ya taşır.",
            "Düşük: cache bir kopyadır, kaynak Aurora'dadır. Ama cache bir anda boşalırsa bütün okumalar aynı anda Aurora'ya gider; bu \"soğuk cache\" anı Aurora'yı yormamalı.",
            "Kaybolan kopya veri kaybı değildir, ama boş bir cache kampanya akşamında Aurora'ya saniyede 6.000 JOIN demektir."),
        row("R4", 10, "Üç geliştirici; cache kodu birkaç satır olmalı.",
            "Üç geliştirici. Cache kodu birkaç satır olmalı; fiyat değişikliğinde silme tek bir yerde yazılmalı. Lale Market'te ElastiCache ve Aurora zaten çalışır.",
            "Cache kodu her okuma yoluna dağılırsa eski veri hataları bulunması zor hatalara dönüşür."),
        row("R5", 10, "Sıcak veri 50 MB'tan azdır; kampanya için ek bir okuma instance'ı istenmiyor.",
            "Sayfa verisi küçük (2 KB) ve sıcak ürün sayısı az; toplam sıcak veri 50 MB'tan az. Kampanya akşamı için Aurora'ya ayrıca reader eklemek istenmiyor.",
            "Her ek reader saat başına ödenir; cache ise sadece sıcak ürünleri bellekte tutar."),
    ],
    cands=["ec", "ddb", "aur"],
    scores={
        "ec": [sc(10, "GET product:P0001 hazır sayfa verisini key ile, bellekten okur (Ö1); cevap bir kez hesaplanır, binlerce kez okunur (Ö8). Puan kırılmadı."),
               sc(8, "TTL eski verinin üst sınırını 300 saniyede tutar; fiyat değişince DEL kopyayı hemen siler (Ö8). 2 puan kırıldı: cevap 5 dakikaya kadar eskiyebilir ve silme kodu \"önce Aurora, sonra DEL\" sırasıyla, fiyatı yazan her yolda yazılmalıdır."),
               sc(10, "Hazır cevap bellekteki hash table'dadır; okuma mikrosaniyelerdedir ve sorgu çalışmaz (Ö1). Puan kırılmadı."),
               sc(10, "SET … EX 300 kopyaya yazarken süreyi verir; kopya tam süresinde gider (Ö4). Puan kırılmadı."),
               sc(10, "Saniyede 6.000 GET Serverless için küçük bir yüktür; görüntülemelerin çoğu hit olduğu için Aurora writer'ı neredeyse hiç okuma görmez (Ö6, Ö8). Puan kırılmadı."),
               sc(7, "Bir node arızasında replica'lar kopyayı sıcak tutar (Ö7). 3 puan kırıldı: bir shard'ın kaybı ya da yeniden kurulan bir cache soğuk başlar ve okumalar birkaç dakika Aurora'ya gider; aynı key'in eşzamanlı miss'leri kısa bir SET NX kilidiyle tek okumaya indirilmelidir. Bu kartta bellekteki veri yalnız bir kopyadır ve her değeri o anda Aurora'da tam olarak vardır; kaybolan bir şey yoktur, bu yüzden \"verinin tek yeri bellek\" olan kartlardaki 4 puan burada verilmez."),
               sc(10, "Cache zaten çalışır; cache-aside birkaç satırdır. Puan kırılmadı: silme kodu R1.2'de sayıldı."),
               sc(9, "Sıcak veri 50 MB'tır ve ECPU başına ödenir. 1 puan kırıldı: Serverless'ta en az 100 MB saklama ödenir, kullanılan yerin iki katı.")],
        "ddb": [sc(10, "Hazır sayfa verisi product id key'iyle bir item'dır; GetItem tek okumadır, JOIN çalışmaz. Puan kırılmadı."),
                sc(8, "Kopya aynı biçimde 5 dakikada yenilenir ya da fiyat değişince silinir. 2 puan kırıldı: ElastiCache'teki gibi silme kodu her fiyat yazan yolda yazılmalıdır."),
                sc(8, "Okuma SSD'deki partition'dan tek haneli milisaniyedir. 2 puan kırıldı: 10 ms sınırının içindedir ama payı küçüktür."),
                sc(6, "TTL alanı eski kopyaları siler. 4 puan kırıldı: silme günler içinde olur; \"5 dakikadan eski kopyayı kullanma\" kuralını okuma her seferinde expires_at ile kendisi kontrol eder."),
                sc(9, "On-demand mod on kat okumayı taşır ve Aurora writer'ı okuma görmez. 1 puan kırıldı: önceki tepenin iki katından hızlı bir sıçrama için table önceden ısıtılmalıdır."),
                sc(10, "Her yazma birkaç AZ'de saklanır; kopya bir arızada kaybolmaz ve soğuk başlangıç yoktur. Puan kırılmadı."),
                sc(8, "Lale Market DynamoDB'yi sepet için zaten kullanır. 2 puan kırıldı: yeni bir table ve onu dolduran kod ürün sayfasının okuma yoluna eklenir."),
                sc(6, "İstek başına ödenir. 4 puan kırıldı: kampanya akşamı saniyede 6.000 okuma, saniyede 6.000 okuma isteğidir; aynı okumalar bellekte ECPU olarak çok daha ucuzdur.")],
        "aur": [sc(7, "Sayfa verisi üç table'ın JOIN'idir ve index'lerle yaklaşık 8 ms sürer. 3 puan kırıldı: aynı cevap her açılışta yeniden hesaplanır; hazır bir cevap yoktur."),
                sc(10, "Cevap her zaman kaynaktır: fiyat değiştiği anda sayfada görünür. Puan kırılmadı: bu satırda en güçlü aday Aurora'dır."),
                sc(8, "Sık okunan page'ler buffer cache'tedir. 2 puan kırıldı: cevap bellekteki hazır bir değerden değil, index ve page zincirinden okunur; 8 ms 10 ms sınırının içindedir ama payı küçüktür (JOIN'in her seferinde yeniden çalışması R1.1'de sayıldı)."),
                sc(10, "Kopya yoktur, bu yüzden biten ya da eskiyen kopya da yoktur. Puan kırılmadı."),
                sc(5, "Okumalar reader instance'lara gönderilirse writer korunur. 5 puan kırıldı: on katlık sıçrama her görüntülemede yeniden çalışan bir JOIN olarak cluster'a biner; \"writer'ın yükü normal günden fazla olmasın\" isteği ancak bütün okumalar reader'lara giderse karşılanır ve reader'lar storage'ı writer ile paylaşır. Reader eklemek ve yönlendirmek R4'te sayıldı."),
                sc(10, "Kaynak zaten Aurora'dır; üç AZ'de altı kopya. Puan kırılmadı."),
                sc(7, "Var olan cluster'a bir reader eklenir. 3 puan kırıldı: reader'ın boyutu ve kampanya öncesi eklenmesi, okuma yolunun reader endpoint'ine yönlendirilmesi ekibin işidir."),
                sc(5, "Reader instance saat başına ödenir. 5 puan kırıldı: kampanya akşamı için eklenen reader, hikâyenin istemediği bir maliyettir.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB hazır sayfa verisini aynı biçimde key ile tutabilir ve dayanıklılıkta öndedir: bir arızada kopya kaybolmaz, soğuk başlangıç olmaz (R3). "
               "Ama bu kart bir kopya iş yüküdür ve bir kopyanın değeri hızında ve ucuzluğundadır. R1'de iki fark vardır: DynamoDB'nin TTL'i günler içinde siler ve 5 dakika kuralını okuma kendisi kontrol eder; okuma SSD'den tek haneli milisaniyedir, bellekten mikrosaniye değil. "
               "R5'te her görüntüleme bir okuma isteğidir. Dayanıklılık burada bir kopyayı korur, bir kaydı değil. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: sayfa verisi başka bir yerden yeniden hesaplanamasaydı (örneğin satıcının elle yazdığı bir vitrin metni) ya da soğuk cache anını Aurora hiç taşıyamasaydı.",
        "aur": "İlişkisel (Aurora) ile kafa kafaya: cache'siz seçenek. Aurora'nın gücü tazeliktir: cevap her zaman kaynaktır ve fiyat değiştiği anda görünür (R1.2'de tek tam puan). "
               "Ama aynı cevabı her açılışta yeniden hesaplar: saniyede 6.000 JOIN, kampanya akşamı bir reader ve okuma yönlendirmesi demektir (R2, R4, R5). "
               "Bu kartın doğru cevabı ikisinin birlikte çalışmasıdır: Aurora kaynak ve checkout'un database'i olarak kalır, ElastiCache onun önünde hazır cevapları tutar. Cache Aurora'nın yerine geçmez; Aurora olmadan cache'in dolduracağı bir kaynak yoktur. "
               "Sayfa herkese aynı olsaydı önünde bir CDN (CloudFront) ilk katman olurdu; bu kart uygulamanın kendi okuduğu sayfa verisini önbellekler: kişiye göre birleşen sayfa ve CDN'in miss'leri yine bu katmana gelir. Hangi koşul değişseydi yalnız Aurora seçilirdi: eski fiyat hiç kabul edilmeseydi (örneğin anlık değişen bir borsa fiyatı), görüntülemeler ürünlere eşit dağılsaydı (sıcak küme olmasaydı) ya da trafik bir reader'ın rahat erişiminde kalsaydı.",
    },
    verdict="Karar: ElastiCache {ec}, DynamoDB {ddb}, Aurora {aur}. Bu iş yüküne en uygun servis ElastiCache'tir, ama tek başına değil: doğru mimari Aurora'nın önünde ElastiCache'tir. Kararı R1'in erişim ve depolama satırları ve R2 verir: hazır cevap bellekten gelir ve writer kampanya akşamı okuma görmez. "
            "ElastiCache seçtiğimizde artımız: görüntülemelerin çoğu bellekten, Aurora'ya ek reader yok, kopya 5 dakikada kendiliğinden gider. "
            "Eksimiz: cevap 5 dakikaya kadar eskiyebilir; uygulama fiyatı yazan her yolda kopyayı silmeli, checkout'ta fiyatı ve stoğu Aurora'dan yeniden kontrol etmeli ve soğuk cache anı için SET NX ile stampede'i önlemelidir. Bir koşul değişseydi: eski fiyat hiç kabul edilmeseydi Aurora tek başına kalırdı."))

# ------------------------------------------------------------------ 5. real-time counters: views and unique visitors
ELASTICACHE_W.append(wusecase("counters", 5,
    title="Gerçek zamanlı sayaçlar: görüntüleme ve tekil ziyaretçi",
    key="Key: views:2026-10-28T14:<n> (saat ve 0–15 arası bir parça numarası; her olay rastgele bir parçaya yazılır, ekran 16 hash'i toplar). Value: bir hash; field ürün id'si, değer sayı. Tekil ziyaretçi için ürün başına bir HyperLogLog.",
    story=estory("counters"),
    wnote="R1 toplam 50: sayacın biçimi (okumadan artır, sıcak ürünlerde yarış), tekil sayımın veri yapısı, ekranın sorusu ve saatin bitişi bu iş yükünün kendisidir. "
          "R2 20 ile ikinci: kampanya akşamı 50.000 olay ve yarısı aynı 10 ürüne. R4 15'tir, çünkü iki geliştirici ve bir analist yeni bir sistem öğrenmek istemiyor. R3 5'tir: kalıcı rapor Redshift'tedir.",
    rows=[
        row("OY", 20, "Her görüntüleme bir artırmadır ve olayların yarısı aynı 10 ürüne gider.",
            "\"Bu ürünün bu saatteki sayacını 1 artır\" okumadan ve atomik olmalı; aynı ürüne aynı anda gelen yüzlerce olayın hepsi sayılmalı.",
            "Atomik olmayan artırma kampanya akşamı en çok bakılan ürünlerin sayılarını kaybeder; ekran yanlış \"en çok bakılan\" gösterir."),
        row("VM", 10, "Tekil ziyaretçi sayısı bir veri yapısı sorusudur; yüzde 1 hata kabul edilir.",
            "\"Bu ziyaretçiyi bu ürünün tekil ziyaretçilerine ekle\" ve \"kaç tekil ziyaretçi\"; yüzde 1 hata kabul edilir, ürün başına bellek küçük kalmalı.",
            "Her ziyaretçi id'si tek tek saklanırsa milyonlarca id bellekte ya da diskte yer tutar; aynı ziyaretçi iki kez sayılırsa sayı şişer."),
        row("EY", 10, "Ekran her 2 saniyede bu saatin bütün ürünlerini ve ilk 20'yi sorar.",
            "Okuma: \"bu saatin bütün ürünleri ve sayıları\" ve \"şu an en çok bakılan 20 ürün\". Ekran her 2 saniyede okur.",
            "İlk 20 her okumada bütün ürünler sıralanarak bulunursa ekranın her açılışı ağır bir sorgu olur."),
        row("YD", 10, "Her saat sonunda sayılar Redshift'e yazılır ve bellekteki saat gitmelidir.",
            "Saat bitince sayılar Redshift'e (data warehouse) yazılır ve o saatin key'leri kendiliğinden silinir.",
            "Silinmeyen saatler her gün birikir ve bellek ya da storage dolar."),
        row("R2", 20, "Saniyede 15.000, kampanya akşamı 50.000 olay; yarısı aynı 10 ürüne.",
            "Saniyede 15.000, kampanya akşamı 50.000 artırma; yarısı aynı 10 ürüne. Ekran her 2 saniyede okur.",
            "Olayların yarısı aynı birkaç key'e gider; bu key'leri tutan yer bu yükü tek başına taşımalıdır."),
        row("R3", 5, "Son saatin sayıları kaybolursa ekran o saati eksik gösterir; kalıcı rapor Redshift'tedir.",
            "Düşük: son saatin sayıları kaybolursa ekran o saati eksik gösterir. Muhasebe ve faturalama bu sayılara dayanmaz.",
            "Sayılar bir vitrin ve bir eğilim göstergesidir; kalıcı rapor Redshift'tedir."),
        row("R4", 15, "İki geliştirici ve bir analist yeni bir sistem öğrenmek istemiyor.",
            "İki geliştirici; sunucu istenmiyor. Saat sonunda Redshift'e yazan bir iş kabul edilir.",
            "Küçük ekipte zaman serisi database'i gibi yeni bir sistem öğrenmek bir çeyrek demektir."),
        row("R5", 10, "Her olay bir yazmadır: ayda 40 milyar artırma.",
            "Her olay bir yazmadır: ayda 40 milyar artırma. Veri küçüktür: bir saatin sayaçları birkaç MB.",
            "Yazma başına fiyat bu iş yükünün faturasıdır."),
    ],
    cands=["ec", "ddb", "ix"],
    scores={
        "ec": [sc(10, "HINCRBY views:…:<n> P0001 1 sayacı okumadan ve atomik artırır; komutlar sırayla çalıştığı için aynı ürüne gelen her olay sayılır (Ö3). Puan kırılmadı."),
               sc(10, "PFADD ve PFCOUNT tekil ziyaretçiyi ürün başına en fazla 12 KB ile, yüzde 0,81 standart hatayla sayar (Ö2). Puan kırılmadı."),
               sc(9, "HGETALL bu saatin bütün ürünlerini tek komutta verir (Ö2). 1 puan kırıldı: \"en çok bakılan 20\" için aynı pipeline'da bir sorted set'e de ZINCRBY yazılır; iki yapı birlikte güncellenir."),
               sc(9, "Saatin key'lerine EXPIRE verilir ve saat bitince tam anında giderler (Ö4). 1 puan kırıldı: Redshift'e yazan iş key'ler gitmeden önce çalışmalıdır; süre bunun için saatten biraz uzun seçilir."),
               sc(8, "Valkey tek bir key'e gelen komutları tek shard'da sırayla çalıştırır (Ö6). 2 puan kırıldı: kampanya akşamı 25.000 olay saniyede aynı 10 ürüne, yani tek bir saat key'ine gider; o shard'ın payını korumak için key 16 parçaya bölünür ve ekran 16 hash'i toplar. Ayrıca boş bir Serverless cache saniyede 30.000 ECPU ile başlar; 50.000 olaylık kampanya için minimum ECPU önceden ayarlanır."),
               sc(4, "Kalıcı bir yazma log'u yoktur. 6 puan kırıldı: bir arızada son saatin sayıları kaybolabilir; bu kartta kabul edilen bir sonuçtur."),
               sc(10, "Cache zaten çalışır; HINCRBY, PFADD ve saat sonu işi birkaç satırdır. Puan kırılmadı."),
               sc(9, "ECPU başına ödenir ve bir artırma yaklaşık 1 ECPU'dur. 1 puan kırıldı: PFADD ve sorted set komutları basit bir artırmadan biraz daha fazla ECPU harcar.")],
        "ddb": [sc(9, "UpdateItem ADD sayacı okumadan ve atomik artırır. 1 puan kırıldı: her artırma item'ın tamamını yeniden yazar; item büyüdükçe bir artırmanın yazdığı veri de büyür."),
                sc(3, "Tekil sayım için hazır bir veri yapısı yoktur. 7 puan kırıldı: ya her ziyaretçi id'si bir item ya da bir set alanı olarak saklanır (milyonlarca kayıt), ya da uygulama bir HyperLogLog'u binary alan olarak okuyup koşullu yazmayla günceller."),
                sc(7, "\"Bu saatin bütün ürünleri\" saat partition key'i ile tek bir okumadır. 3 puan kırıldı: \"en çok bakılan 20\" için bütün ürünler okunur ve uygulamada sıralanır."),
                sc(6, "TTL eski saatleri siler. 4 puan kırıldı: silme günler içinde olur; okuma eski saatleri key'den ayırt eder."),
                sc(5, "Yazmalar partition'lara dağılır. 5 puan kırıldı: 25.000 olay saniyede 10 item'a gider ve bir partition saniyede yaklaşık 1.000 yazma birimi için tasarlanmıştır; ElastiCache'te bölme bir pay önlemidir, burada zorunludur: her sıcak item onlarca parçaya bölünmeli ve okumada toplanmalıdır."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(10, "Serverless. Puan kırılmadı: sayacın bölünmesi R2'de, tekil sayım kodu R1.2'de sayıldı."),
                sc(4, "İstek başına ödenir. 6 puan kırıldı: ayda 40 milyar yazma birimi, aynı artırmaların ECPU fiyatının çok katıdır.")],
        "ix": [sc(6, "Her olay bir point olarak yazılır ve sayı pencere toplamıyla hesaplanır. 4 puan kırıldı: engine artırmaz, ekler; saniyede 50.000 point saklanır ve sayı her okumada yeniden toplanır."),
               sc(4, "Tekil ziyaretçi bir pencerede distinct sayımıdır. 6 puan kırıldı: ziyaretçi id'si tag olursa seri sayısı (cardinality) patlar, field olursa her okumada bütün point'ler taranır; yaklaşık sayım için hazır bir yapı yoktur."),
               sc(8, "Ürüne göre saatlik pencere toplamı engine'in doğal sorusudur. 2 puan kırıldı: \"ilk 20\" her 2 saniyede bir gruplama ve sıralama sorgusudur."),
               sc(10, "Retention süresi eski point'leri kendisi siler; downsampling task'ları saatlik özetleri tutar. Puan kırılmadı."),
               sc(6, "Engine saniyede on binlerce point yazmayı taşıyabilir. 4 puan kırıldı: kampanya tepesinde 50.000 point/saniye yazma ile her 2 saniyede bir saatlik toplam aynı makinede yarışır ve ekranın sorgu süresi uzar (boyutlandırma R4'te sayıldı)."),
               sc(9, "Multi-AZ instance seçeneği vardır. 1 puan kırıldı: yedek instance seçilmezse bir arıza son point'leri götürebilir."),
               sc(5, "Yönetilen instance. 5 puan kırıldı: ekip için yeni bir sistem, yeni bir sorgu dili (Flux ya da InfluxQL) ve instance boyutlandırma; analist yine Redshift'te çalışır."),
               sc(6, "Instance saat başına ödenir. 4 puan kırıldı: instance kampanya akşamı için boyutlanır ve gece de çalışır.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB atomik artırmayı ElastiCache kadar iyi yapar, ama bu iş yükünün diğer iki engine sorusunda geride kalır. "
               "Tekil ziyaretçi sayımı için hazır bir yapı yoktur: ya milyonlarca id saklanır ya da uygulama bir HyperLogLog'u kendisi yazar (R1.2). Sıcak ürünlerin sayaçları tek bir item'da kalırsa bir partition'ın yazma sınırına dayanır ve bölünmesi gerekir (R2). "
               "R5'te ayda 40 milyar yazma birimi faturanın büyük kısmıdır. DynamoDB'nin dayanıklılığı bu kartta önemsizdir, çünkü kalıcı rapor zaten Redshift'tedir. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: sayılar faturalamaya dayansaydı ve kaybolmamalı olsaydı, olay hızı yüz kat düşük olsaydı ve tekil sayım istenmeseydi.",
        "ix": "Time series (Timestream for InfluxDB) ile kafa kafaya. Timestream for InfluxDB zaman pencereleri ve retention'da güçlüdür: saatlik özet ve eski verinin silinmesi onun doğal işidir (R1.4). "
              "Ama bu kart bir sayaç iş yüküdür, bir ölçüm geçmişi değil: engine artırmaz, her olayı bir point olarak saklar ve sayıyı her okumada yeniden toplar; tekil ziyaretçi ise yüksek cardinality tuzağına düşer. "
              "Ekip için yeni bir sistem ve yeni bir sorgu dili R4'te de puan kaybettirir. "
              "Hangi koşul değişseydi Timestream for InfluxDB seçilirdi: ekran son saati değil son 30 günü dakika dakika gösterseydi ve sorgular zaman pencereleri üzerinde değişken olsaydı; o zaman bellek yerine bir zaman serisi engine'i doğru yer olurdu.",
    },
    verdict="Karar: ElastiCache {ec}, DynamoDB {ddb}, Timestream for InfluxDB {ix}. Bu iş yüküne en uygun servis ElastiCache'tir ve doğru mimari iki parçalıdır: canlı saat ElastiCache'te, saatlik geçmiş Redshift'te. Kararı R1 verir: atomik artırma, HyperLogLog ve hazır ilk 20 tek komutlardır. "
            "ElastiCache seçtiğimizde artımız: kampanya akşamı da doğru sayılar, ürün başına 12 KB'lık tekil sayım, saat sonunda kendiliğinden giden key'ler. "
            "Eksimiz: son saat bir arızada kaybolabilir; uygulama Redshift'e yazan işi key'ler gitmeden çalıştırmalı ve ekran eksik saati \"veri yok\" olarak göstermelidir. Bir koşul değişseydi: sayılar faturalamaya dayansaydı, olay hızı yüz kat düşük olsaydı ve tekil sayım istenmeseydi DynamoDB öne geçerdi; tek başına bu koşullardan biri farkı kapatmaz."))

# ------------------------------------------------------------------ 6. pub/sub for live updates
ELASTICACHE_W.append(wusecase("pubsub", 6,
    title="Canlı güncellemeler için pub/sub",
    key="Channel: order:<id> ve stock:<ürün>. Message: yeni durum ya da yeni stok sayısı.",
    story=estory("pubsub"),
    wnote="R1 toplam 40: bir olayın aboneleri bilmeden bütün sunuculara gitmesi, bunun milisaniyelerde olması ve mesajın saklanmaması bu iş yükünün tanımıdır. "
          "R2 25 ile ikinci: 150.000 bağlı tarayıcıya saniyede 10.000 olay ve 500 ms sınırı. R4 ve R5 15'tir: ekip yeni bir mesajlaşma sistemi istemiyor ve mesajlar saklanmadığı için fiyatı mesaj başına ödeme belirler.",
    rows=[
        row("EY", 20, "Bir olayın hangi sunucudaki tarayıcıya gideceği bilinmez; yayının yolu bu iş yükünün kendisidir.",
            "Bir olay bir kez yayınlanır ve o channel'a abone olan her WebSocket sunucusuna gider (fan-out). Yayınlayan, abonelerin kim olduğunu bilmez.",
            "Her olay 20 sunucuya ayrı ayrı gönderilirse yayınlayan kod sunucu listesini bilmek zorunda kalır ve her yeni sunucu bir kod değişikliğidir."),
        row("DA", 10, "500 ms sınırı mesajın bir yere yazılıp sonra okunmasıyla değil, doğrudan iletilmesiyle rahat karşılanır.",
            "Olay yayınlandığı anda bağlı abonelere iletilmeli; arada bir yazma, bir okuma ve bir bekleme olmamalı.",
            "Mesaj önce saklanıp sonra okunursa her olaya bir yazma ve bir okuma gecikmesi eklenir; \"3 adet kaldı\" geç gelir."),
        row("YD", 10, "Mesaj geçmişi istenmez; kalıcı kayıt zaten Aurora'daki sipariş ve stok row'larıdır.",
            "Mesaj iletildikten sonra hiçbir yerde kalmamalı; geçmiş tutulmaz, temizlik işi olmaz.",
            "Saklanan her mesaj bir yazma ve bir silme demektir; saniyede 10.000 olay günde 860 milyon gereksiz kayıt üretir."),
        row("R2", 25, "150.000 bağlı tarayıcıya saniyede 10.000 olay; tepe kampanya akşamıdır.",
            "Saniyede 2.000, kampanya akşamı 10.000 olay; her olay 500 ms içinde tarayıcıda. Aynı anda 150.000 tarayıcı 20 sunucuya bağlıdır.",
            "\"3 adet kaldı\" mesajı geç gelirse müşteri tükenmiş bir ürünü sepete ekler ve checkout'ta hayal kırıklığı yaşar."),
        row("R3", 5, "Kaçan bir mesaj zararsızdır; sayfa yeniden bağlanınca son durumu okur.",
            "Düşük: kaçan bir mesaj zararsızdır; sayfa yeniden bağlanınca son durumu Aurora'dan okur. Mesaj geçmişi istenmez.",
            "Olay kaynağı Aurora'daki sipariş ve stoktur; mesaj sadece bir bildirimdir."),
        row("R4", 15, "Üç geliştirici yeni bir mesajlaşma sistemi öğrenmek istemiyor.",
            "Üç geliştirici, sunucu istemiyor; WebSocket sunucuları zaten var. Yeni bir mesajlaşma sistemi öğrenmek istenmiyor.",
            "Mesajlaşma altyapısı ürünün kendisi değildir; ekibin zamanını almamalıdır."),
        row("R5", 15, "Mesajlar küçüktür ve saklanmaz; fiyatı mesaj başına ödeme ve boşta çalışan kapasite belirler.",
            "Mesajlar küçük (200 byte), saklanmaz. İstek başına ödeme tercih edilir.",
            "Saklanmayan küçük mesajlarda belirleyici olan mesaj başına fiyattır."),
    ],
    cands=["ec", "mdb", "sns"],
    scores={
        "ec": [sc(10, "PUBLISH order:O1 … bir kez gönderilir ve SUBSCRIBE ile bağlı her WebSocket sunucusuna gider; yayınlayan aboneleri bilmez (Ö5). Puan kırılmadı."),
               sc(10, "Mesaj bellekte, bağlı bağlantılara doğrudan iletilir; arada yazma yoktur (Ö1, Ö5). Puan kırılmadı."),
               sc(10, "Pub/Sub mesajı hiçbir yerde saklamaz; istenen de budur (Ö5). Puan kırılmadı."),
               sc(9, "Serverless saniyede 10.000 yayını taşır (Ö6). 1 puan kırıldı: klasik Pub/Sub'da mesaj cluster'ın node'ları arasında dolaşır; sipariş başına channel'larda sharded Pub/Sub (SPUBLISH) trafiği tek shard'da tutar ve abone kodu buna göre yazılır."),
               sc(8, "Replica'lar bir node arızasında servisi sürdürür (Ö7). 2 puan kırıldı: bir failover abone bağlantılarını koparır ve o andaki mesajlar kaçar; sayfa yeniden bağlanıp son durumu okur. Bellekte saklanan bir veri yoktur (mesaj iletilir ve gider), bu yüzden \"verinin tek yeri bellek\" olan kartlardaki 4 puan burada verilmez."),
               sc(10, "Cache zaten çalışır; SUBSCRIBE ve PUBLISH WebSocket sunucusunda birkaç satırdır. Puan kırılmadı."),
               sc(9, "ECPU başına ödenir ve mesajlar saklanmadığı için GB-saat neredeyse yoktur. 1 puan kırıldı: her yayın ve her teslim aktarılan veriye göre ECPU harcar.")],
        "mdb": [sc(10, "Aynı Valkey engine'i: PUBLISH ve SUBSCRIBE. Puan kırılmadı."),
                sc(10, "Aynı engine: mesaj bellekte, doğrudan iletilir. Puan kırılmadı."),
                sc(10, "Pub/Sub mesajı aynı biçimde saklanmaz. Puan kırılmadı."),
                sc(9, "Yayın bir yazma değildir ve log'a işlenmez; hız aynıdır. 1 puan kırıldı: aynı biçimde sharded Pub/Sub tasarımı gerekir."),
                sc(8, "Log key'lerdeki veriyi korur, Pub/Sub mesajlarını değil. 2 puan kırıldı: ElastiCache'teki gibi failover'daki mesajlar kaçar; log bu kartta bir şey eklemez."),
                sc(6, "Yönetilen node'lar. 4 puan kırıldı: serverless seçenek yoktur ve Lale Market'te zaten çalışan cache'in yanına ikinci bir bellek içi sistem eklenir."),
                sc(4, "Node saat başına ödenir. 6 puan kırıldı: hiç saklanmayan mesajlar için gece gündüz çalışan node'lar ve kullanılmayan bir dayanıklılık ödenir.")],
        "sns": [sc(9, "Bir topic'e bir kez yayınlanan mesaj, topic'e abone olan her WebSocket sunucusunun HTTPS endpoint'ine gider; yayınlayan aboneleri bilmez. 1 puan kırıldı: her yeni sunucu bir abonelik olarak kaydedilir ve onaylanır; kapanan sunucunun aboneliği silinir."),
                sc(7, "Mesaj servisin içinden her aboneye ayrı bir HTTPS isteğiyle teslim edilir. 3 puan kırıldı: açık bir bağlantıya yazmak yerine her teslim bir istek ve bir cevaptır; 500 ms sınırının içindedir ama payı ElastiCache'ten küçüktür."),
                sc(10, "Teslim edilen mesaj tutulmaz; geçmiş ve temizlik işi yoktur. Puan kırılmadı."),
                sc(8, "Servis yayınları kendisi ölçekler. 2 puan kırıldı: saniyede 10.000 yayın 20 sunucuya saniyede 200.000 HTTPS teslimi demektir; tepe anında bu istekleri WebSocket sunucuları da karşılamalıdır."),
                sc(10, "Yayınlanan mesajlar birden fazla veri merkezinde saklanır; ulaşılamayan bir sunucuya teslim yeniden denenir. Puan kırılmadı."),
                sc(8, "Serverless, node yok. 2 puan kırıldı: ekip için yeni bir servis; topic, abonelikler ve sunucuların HTTPS endpoint'leri kurulur."),
                sc(4, "Yayın ve teslim başına ödenir. 6 puan kırıldı: saniyede 200.000 teslim ayda yüz milyarlarca teslimdir; aynı mesajlar ElastiCache'te ECPU olarak bunun çok küçük bir kısmına mal olur.")],
    },
    h2h={
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. İkiz servisler aynı Pub/Sub'ı çalıştırır ve R1'de ikisi de 40'ta 40 alır. "
               "Bu kart ikizlerin farkının bile sıfıra indiği bir durumu gösterir: MemoryDB'nin asıl artısı olan log key'lerdeki veriyi korur, Pub/Sub mesajlarını değil; failover'da kaçan mesaj iki serviste de kaçar (R3 eşit). "
               "Geriye yalnız servis tasarımının bedeli kalır: serverless seçenek yoktur, Lale Market'te zaten çalışan cache'in yanına ikinci bir sistem eklenir ve hiç saklanmayan mesajlar için node'lar gece gündüz ödenir (R4, R5). "
               "Hangi koşul değişseydi MemoryDB seçilirdi: mesajlar Pub/Sub yerine bir stream'e yazılsaydı ve kaçan mesaj zarar verseydi (örneğin \"kargoya verildi\" olayından bir e-posta doğsaydı); o zaman log stream key'ini korurdu.",
        "sns": "Yayın-abone servisi (SNS) ile kafa kafaya. SNS bu iş yükünün en yakın yönetilen alternatifidir: bir yayını abonelere dağıtmak onun işidir, mesajları birden fazla veri merkezinde saklar ve ulaşılamayan aboneye teslimi yeniden dener (R3). "
               "Fark teslim biçimindedir: Valkey mesajı WebSocket sunucularının açık bağlantılarına doğrudan yazar; SNS her sunucuya ayrı bir HTTPS isteği gönderir. Saniyede 10.000 olay ve 20 sunucu, saniyede 200.000 teslim demektir; bu hem gecikme payını küçültür (R1.2) hem de teslim başına ödenen faturayı büyütür (R5). "
               "Bu kartta mesaj bir bildirimdir ve kaybı zararsızdır; SNS'in dayanıklılığı bedelini geri almaz. "
               "Hangi koşul değişseydi SNS seçilirdi: aboneler WebSocket sunucuları değil, birkaç arka plan servisi (e-posta, stok, analitik) olsaydı ve her olayın her aboneye kesin ulaşması gerekseydi. Ekip WebSocket sunucularını hiç işletmek istemeseydi ise önce yönetilen bir WebSocket servisi (API Gateway WebSocket API ya da AppSync Events) değerlendirilirdi; bu hikâyede sunucular zaten çalıştığı için aday değildir.",
    },
    verdict="Karar: ElastiCache {ec}, MemoryDB {mdb}, SNS {sns}. Bu iş yüküne en uygun servis ElastiCache'tir. Engine uyumunda iki Valkey servisi eşittir; ElastiCache'i öne geçiren zaten çalışan bir cache'te sunucusuz işletim ve saklanmayan mesajlar için node ödememesidir. "
            "ElastiCache seçtiğimizde artımız: bir PUBLISH bütün sunuculara, milisaniyeler içinde; geçmiş ve temizlik yok. "
            "Eksimiz: mesajlar at-most-once'tır; uygulama bağlantı koptuğunda son durumu Aurora'dan yeniden okumalı ve kaçan mesajın zarar verdiği bir olay için Pub/Sub değil stream ya da yönetilen bir kuyruk kullanmalıdır. Bu kartın mimarisi de ikisi birliktedir: kayıt Aurora'da, bildirim ElastiCache'te. Bir koşul değişseydi: kaçan mesaj zarar verseydi stream ve MemoryDB öne çıkardı."))

# ------------------------------------------------------------------ 7. distributed lock for the seller payout (the clear loss)
ELASTICACHE_W.append(wusecase("lock", 7, sim="w_lock",
    title="Dağıtık kilitler: satıcı ödemesi tam bir kez çalışsın",
    key="Key: lock:payout:2026-10-28. Value: kilidi alan worker'ın rastgele değeri; süre 15 dakika.",
    story=estory("lock"),
    wnote="R1 toplam 45 ve en ağır grup; içinde en ağır satır atomikliktir (25): \"iki worker asla aynı kilidi tutmamalı\" bu iş yükünün tanımıdır. "
          "R3 30 ile ikinci ve R2'den çok ağırdır: kaybolan bir kilit bir gecenin çift ödemesidir, yani 4 milyon TL. R2 5'te, en düşük sınırdadır: günde bir kilit alınır.",
    rows=[
        row("TA", 25, "Bu kartın tanımı: altı worker aynı saniyede denerse tam olarak biri kilidi almalı.",
            "\"Bu gecenin kilidi kimsede değilse bana ver, 15 dakika süreyle\" tek atomik adım olmalı. Kilit onaylandıktan sonra başka bir worker onu alamamalı.",
            "İki worker aynı anda \"kilit boş\" görürse ikisi de ödeme yapar ve her satıcıya iki kez ödenir."),
        row("YD", 10, "Worker ölürse kilit kendiliğinden düşmeli, yoksa o gecenin ödemesi hiç yapılmaz.",
            "Kilidi tutan worker ölürse kilit 15 dakika sonra kendiliğinden düşmeli ve başka bir worker işi devralabilmeli.",
            "Süresi olmayan bir kilit, ölen bir worker'la sonsuza kadar kalır; satıcılar o gece ödeme almaz."),
        row("OY", 5, "Bırakma ve uzatma günde bir kez olur, ama yanlış yapılırsa başkasının kilidi silinir.",
            "Kilidi sadece alan worker bırakabilmeli ve iş uzarsa süresini uzatabilmeli; her biri tek bir istek olmalı.",
            "Başka bir worker'ın kilidini silmek, iki worker'ın aynı anda çalışmasıyla aynı sonucu verir."),
        row("EY", 5, "Soru basittir: tarihli tek bir key.",
            "Tek soru: \"bu gecenin kilidi\". Key tarih ile bilinir.",
            "Key ile doğrudan gidilemezse kilit alma yavaşlar; bu kartta hız önemli değildir."),
        row("R2", 5, "Günde bir kilit; hız bu iş yükünde önemli değildir.",
            "Günde bir kilit alma ve bir bırakma; altı worker aynı saniyede dener. Kilit 1 saniye içinde alınmalı.",
            "Hız bu iş yükünde önemli değildir; asıl ölçek \"altı worker aynı anda\" yarışıdır."),
        row("R3", 30, "Kaybolan kilit bir gecenin çift ödemesidir: 4 milyon TL ve haftalar süren bir banka süreci.",
            "Onaylanan bir kilit hiçbir arızada kaybolmamalı. Kilit kaybolursa ikinci bir worker onu alır ve aynı gece iki ödeme yapılır.",
            "Bir gecenin çift ödemesi 4 milyon TL'dir ve geri almak haftalar süren bir banka sürecidir; bu kartta dayanıklılık bir iş kuralıdır."),
        row("R4", 15, "İki geliştirici; kilit kodu birkaç satır olmalı ve hikâye yalnız kilit için yeni bir sistem istemediğini açıkça söyler.",
            "İki geliştirici; sunucu istenmiyor; kilit kodu birkaç satır olmalı. Lale Market zaten ElastiCache ve DynamoDB kullanıyor.",
            "Kilit kodu karmaşıksa hatası gece 02:00'de, kimse bakmazken ortaya çıkar."),
        row("R5", 5, "Maliyet hikâyede önemsizdir; satır en düşük ağırlıktadır.",
            "Günde birkaç istek; maliyet önemsizdir.",
            "Maliyet kararı tek başına çevirmez; ama günde iki istek için yıl boyu ödenen bir cluster yine de görünür bir kalemdir."),
    ],
    cands=["ddb", "mdb", "ec"],
    scores={
        "ddb": [sc(10, "PutItem attribute_not_exists(pk) OR expires_at < :now kilidi yalnız boşsa ya da süresi dolduysa yazar; aynı saniyedeki diğer beş istek ConditionalCheckFailedException alır. Puan kırılmadı."),
                sc(7, "Süre sonu koşulun içindedir: ölen worker'ın kilidi expires_at geçince bir sonraki denemede geçersiz olur. 3 puan kırıldı: item kalır ve TTL onu günler içinde siler; her deneme süreyi kendisi karşılaştırır."),
                sc(10, "DeleteItem ve UpdateItem bir koşulla (owner = :me) kilidi yalnız sahibine bıraktırır ve uzattırır; her biri tek istektir. Puan kırılmadı."),
                sc(10, "GetItem ve PutItem tarihli key ile doğrudan gider. Puan kırılmadı."),
                sc(10, "Günde bir istek DynamoDB için önemsizdir. Puan kırılmadı."),
                sc(10, "Koşullu yazma onaylanmadan önce birkaç AZ'de saklanır; failover penceresi yoktur. Puan kırılmadı."),
                sc(10, "Lale Market DynamoDB'yi zaten kullanır; serverless ve birkaç satır. Puan kırılmadı."),
                sc(10, "Günde birkaç istek, birkaç kuruş. Puan kırılmadı.")],
        "mdb": [sc(10, "SET lock:payout:… <rastgele değer> NX PX 900000 tek komuttur; Valkey komutları sırayla çalıştırdığı için yalnız bir worker kilidi alır. Puan kırılmadı."),
                sc(10, "PX 900000 kilidi tam 15 dakikada siler. Puan kırılmadı."),
                sc(8, "Bırakma \"değer benimse sil\" kuralıdır. 2 puan kırıldı: kural tek komut değildir; küçük bir Lua script'i (EVAL) değeri karşılaştırıp siler ya da uzatır."),
                sc(10, "Key ile doğrudan erişim. Puan kırılmadı."),
                sc(10, "Günde bir istek; log'a işlenen yazmanın milisaniyesi önemsizdir. Puan kırılmadı."),
                sc(10, "Kilit çoklu AZ'li transaction log'una işlendikten sonra onaylanır; failover'da kaybolmaz. Puan kırılmadı."),
                sc(6, "Yama ve failover yönetilir. 4 puan kırıldı: serverless seçenek yoktur; yalnız bu kilit için node tipi seçilen yeni bir cluster işletilir."),
                sc(4, "Node saat başına ödenir. 6 puan kırıldı: günde iki istek için en küçük çoklu AZ'li cluster bile yıl boyu çalışır.")],
        "ec": [sc(10, "SET … NX PX 900000 test ve yazmayı tek adımda yapar; altı worker'dan yalnız biri kilidi alır (Ö3). Puan kırılmadı."),
               sc(10, "PX süreyi milisaniye hassasiyetle uygular; ölen worker'ın kilidi tam 15 dakikada düşer (Ö4). Puan kırılmadı."),
               sc(8, "Bırakma ve uzatma küçük bir Lua script'idir (EVAL, Serverless'ta desteklenir) (Ö3). 2 puan kırıldı: \"değer benimse sil\" tek komut değildir; script yazılır ve test edilir."),
               sc(10, "Key ile doğrudan erişim (Ö1). Puan kırılmadı."),
               sc(10, "Günde bir istek; önemsiz bir yük. Puan kırılmadı."),
               sc(1, "Replica'lar failover yapar (Ö7), ama kopyalama asenkrondur ve Serverless'ta kalıcı log yoktur. 9 puan kırıldı: \"OK\" alınmış kilit, primary kopyalamadan düşerse yeni primary'de yoktur ve ikinci worker onu alır (B8). Bu satırın isteği \"hiçbir arızada kaybolmamalı\"dır; kaybın kabul edildiği kartlardaki 4 puan burada verilemez."),
               sc(10, "Cache zaten çalışır; kilit birkaç satırdır. Puan kırılmadı: Lua script'i R1.3'te sayıldı."),
               sc(10, "Var olan cache'te günde birkaç komut; ek maliyet yoktur. Puan kırılmadı.")],
    },
    h2h={
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. MemoryDB R1'de DynamoDB'den öndedir: SET NX PX hem atomik kilidi hem de tam 15 dakikalık süre sonunu tek komutta verir; DynamoDB'de süre koşulun içinde karşılaştırılır. "
               "Dayanıklılıkta da DynamoDB kadar güçlüdür: kilit log'a işlendikten sonra onaylanır. Fark servis tasarımında kapanır ve tersine döner: günde iki istek için serverless olmayan, yıl boyu çalışan yeni bir cluster işletilir (R4, R5). "
               "Hangi koşul değişseydi MemoryDB seçilirdi: kilit günde bir kez değil saniyede binlerce kez alınsaydı ve milisaniyenin altında alınmak zorunda olsaydı, ya da ekip zaten başka işler için bir MemoryDB cluster'ı işletiyor olsaydı.",
        "ec": "Bellek içi key-value (ElastiCache) ile kafa kafaya: bu sayfanın net kaybı. ElastiCache R1'de MemoryDB ile eşittir, çünkü aynı engine'i çalıştırırlar: kilit atomik, süre sonu tam, bırakma küçük bir script. "
              "Kararı tek bir satır verir ve o satır bu kartın ikinci en ağır satırıdır: R3. Kopyalama asenkrondur ve Serverless'ta her yazmayı kalıcı kılan bir log yoktur; primary \"OK\" deyip replica'ya kopyalamadan düşerse kilit yeni primary'de yoktur ve ikinci worker aynı gece ikinci ödemeyi yapar (B8'deki simülasyon). "
              "Atomik olmak kalıcı olmak değildir. Kilidi ElastiCache'te bırakıp asıl korumayı ödeme talimatının DynamoDB'ye koşullu yazılmasına taşımak da bir çözümdür; ama o zaman kilit sadece bir verimlilik aracıdır. "
              "Bu karttaki ElastiCache adayı Lale Market'in kullandığı Serverless'tır. Node'lu bir Valkey 9.0 cluster'ında senkron kalıcılık açılsaydı R3 MemoryDB gibi tam puan alırdı, ama R4 ve R5 de MemoryDB'ninki gibi olurdu (yalnız kilit için node'lu bir cluster); sonuç MemoryDB'nin yanında, DynamoDB'nin gerisinde kalırdı. Hangi koşul değişseydi ElastiCache seçilirdi: kilidin kaybı zararsız olsaydı (örneğin bir cache'in stampede kilidi, B6) ya da korunan iş idempotent olsaydı, yani iki kez çalışması aynı sonucu verseydi.",
    },
    verdict="Karar: DynamoDB {ddb}, MemoryDB {mdb}, ElastiCache {ec}. Bu iş yüküne en uygun servis DynamoDB'dir ve ElastiCache burada net olarak kaybeder: üçüncüdür. Engine uyumunda üç aday birbirine yakındır; kararı R3 verir: onaylanan kilit hiçbir arızada kaybolmamalıdır. "
            "Yine de ElastiCache seçersek artımız: kilit zaten çalışan cache'te, birkaç satır ve tam süre sonuyla. "
            "Eksimiz: bir failover'da kilit kaybolabilir ve satıcılara iki kez ödenebilir; ElastiCache seçilirse uygulama ödeme talimatını satıcı ve gün başına benzersiz bir id ile DynamoDB'ye koşullu yazmalı, yani asıl korumayı kalıcı bir store'a taşımalıdır. Hangi servis seçilirse seçilsin süreli bir kilit, takılan bir worker'ın süresi dolunca ikinci bir worker'a geçebilir; bu yüzden ödeme talimatı her durumda satıcı ve gün başına benzersiz bir id ile koşullu yazılır (B8): kilit verimliliği, benzersiz id doğruluğu sağlar. Bir koşul değişseydi: korunan iş idempotent olsaydı ElastiCache yeterdi."))

# ------------------------------------------------------------------ 8. job queue for image thumbnails (SQS wins, also on R1)
ELASTICACHE_W.append(wusecase("queue", 8, sim="w_queue",
    title="İş kuyruğu: ürün görseli küçültme",
    key="ElastiCache'te key: jobs:thumbs; value bir stream ve onun consumer group'u (thumbs-workers). SQS'te bir queue ve bir dead-letter queue.",
    story="Satıcılar ürün görsellerini S3'e yükler. Her yükleme, görselin dört boyutta küçültülmesi için bir iş üretir; 8 worker işleri alır ve sonucu S3'e yazar. "
          "Normal günde saniyede 30 iş, yeni sezon başında saniyede 500 iş gelir ve iki saat sürer. İş 5 saniye içinde başlamalıdır. "
          "Bozuk bir görsel küçültmeyi her seferinde çökertebilir: üç kez başarısız olan iş kuyruktan ayrılmalı ve bir ekranda gösterilmelidir, yoksa worker'ları sonsuza kadar meşgul eder. "
          "Bir iş kaybolursa görsel küçültülmeden kalır, ama gece çalışan bir kontrol S3'teki küçültülmemiş görselleri bulur ve işi yeniden üretir. Bir işin iki kez yapılması zararsızdır (aynı dosya yeniden yazılır). "
          "Ekip iki geliştirici; Lale Market'te ElastiCache zaten var ve ekip kuyruğu oraya koymayı düşünüyor.",
    wnote="R1 toplam 40 ve en ağır grup: bir işin nasıl eklenip alındığı, çöken worker'ın işinin geri gelmesi ve üç kez başarısız olan işin ayrılması bu iş yükünün kurallarıdır. "
          "R2 20 ile ikinci: sezon başında on altı kat iş ve 5 saniyelik başlama sınırı. R3 ve R4 15'tir: kaybolan iş bir gece gecikir, ekip ise iki kişidir.",
    rows=[
        row("OY", 15, "Her iş bir ekleme ve bir alma; worker'lar boşken sürekli sormamalı.",
            "Üretici işi kuyruğun sonuna ekler; bir worker kuyruğun başından bir iş alır. Kuyruk boşken worker sürekli sormamalı, iş gelince uyanmalı.",
            "Yoklama yapan 8 worker saniyede binlerce boş istek demektir; geç başlayan iş satıcının ürün sayfasını görselsiz bırakır."),
        row("TA", 15, "İki worker aynı işi almamalı ve çöken worker'ın işi kaybolmamalı.",
            "İki worker aynı işi almamalı. Worker işi alırken ya da işlerken çökerse iş bir süre sonra kendiliğinden kuyruğa dönmeli.",
            "Çöken worker'ın işi hiçbir yerde kalmazsa görsel küçültülmez; iki worker aynı işi alırsa iş boşa tekrarlanır."),
        row("AO", 10, "Üç kez başarısız olan iş ayrılmazsa bozuk bir görsel worker'ları sonsuza kadar meşgul eder.",
            "Her işin kaç kez denendiği sayılmalı; üç kez başarısız olan iş otomatik olarak ayrı bir yere taşınmalı ve orada incelenebilmeli.",
            "Bozuk bir iş sonsuza kadar yeniden denenirse sezon başında 8 worker'ın biri sürekli aynı işle meşgul olur."),
        row("R2", 20, "Sezon başında saniyede 500 iş iki saat sürer; iş 5 saniye içinde başlamalı.",
            "Saniyede 30, sezon başında 500 iş; her iş 5 saniye içinde başlamalı.",
            "Kuyruk tepe anında yavaşlarsa iş birikir ve satıcıların görselleri saatlerce küçültülmeden kalır."),
        row("R3", 15, "Kaybolan iş gece kontrolüyle geri gelir; ama satıcı o gün görselini küçük boyutta görmez.",
            "Orta: kaybolan iş gece kontrolüyle yeniden üretilir, ama satıcı o gün görselini küçük boyutta görmez.",
            "Kayıp bir gecikmedir, veri kaybı değildir; asıl dosya S3'te kalıcıdır."),
        row("R4", 15, "İki geliştirici; sunucu ve yeni bir bakım işi istenmiyor.",
            "İki geliştirici; sunucu istenmiyor. Kuyruğun kendisi için ayrı bir bakım işi yazılmamalı.",
            "Küçük ekipte kuyruğun etrafına yazılan her yardımcı iş (temizlik, geri koyma) bir nöbet listesi demektir."),
        row("R5", 10, "İşler küçüktür; istek başına ödeme ve boşta sıfıra yakın maliyet istenir.",
            "İşler küçük (200 byte); kuyruk tepe anında bile birkaç MB. İstek başına ödeme tercih edilir.",
            "Küçük işlerde belirleyici olan istek başına fiyattır."),
    ],
    cands=["sqs", "ec", "mdb"],
    scores={
        "sqs": [sc(10, "SendMessage ekler, ReceiveMessage alır ve long polling ile 20 saniyeye kadar bekler: worker iş gelince uyanır, boş yoklama yapmaz. Puan kırılmadı."),
                sc(9, "Alınan mesaj visibility timeout boyunca diğer worker'lardan gizlenir; worker silmeden çökerse mesaj süre bitince kuyruğa kendiliğinden döner. 1 puan kırıldı: standard queue at-least-once'tır ve bir iş seyrek olarak iki kez gelebilir; bu iş yükünde zararsızdır."),
                sc(10, "Her mesajın alınma sayısı tutulur; redrive policy maxReceiveCount = 3 ile üç kez başarısız olan işi dead-letter queue'ya kendisi taşır. Puan kırılmadı."),
                sc(10, "Standard queue saniyede neredeyse sınırsız istek kabul eder; saniyede 500 iş ayarsız karşılanır. Puan kırılmadı."),
                sc(10, "SQS mesajı onaylamadan önce birkaç AZ'de saklar. Puan kırılmadı."),
                sc(9, "Serverless: kapasite ve node yoktur. 1 puan kırıldı: ekip için yeni bir servis; queue, dead-letter queue ve IAM izni bir kez kurulur."),
                sc(10, "İstek başına ödenir ve boşta maliyet sıfıra yakındır; long polling boş istekleri azaltır. Puan kırılmadı.")],
        "ec": [sc(9, "XADD işi stream'e ekler, XREADGROUP … BLOCK işi bekleyerek alır ve worker iş gelince uyanır (Ö5). 1 puan kırıldı: iş bitince XACK ile onaylanır ve stream XADD … MAXLEN ile kırpılmalıdır."),
               sc(8, "Consumer group bir mesajı yalnız bir worker'a verir; çöken worker'ın onaylanmamış mesajı bekleyenler listesinde kalır (Ö5). 2 puan kırıldı: mesaj kendiliğinden geri dönmez; bir worker belirli aralıklarla XAUTOCLAIM … <min-idle> çalıştırıp uzun süre bekleyen mesajları sahiplenmelidir."),
               sc(6, "Stream her mesajın kaç kez teslim edildiğini tutar (XPENDING) (Ö5). 4 puan kırıldı: dead-letter taşıması yoktur; üç kez teslim edilip onaylanmayan işi ayrı bir \"failed\" stream'ine yazıp onaylayan kodu uygulama yazar."),
               sc(10, "Bekleyen worker'lar saniyede 500 işi gecikmesiz alır; Serverless yükü taşır (Ö6). Puan kırılmadı."),
               sc(4, "Kalıcı bir yazma log'u yoktur. 6 puan kırıldı: bir arızada kuyruktaki son işler kaybolabilir; gece kontrolü onları yeniden üretir ve bu kartta kabul edilen bir sonuçtur."),
               sc(10, "Cache zaten çalışır; serverless. Puan kırılmadı: XAUTOCLAIM ve bozuk iş kodu R1.2 ve R1.3'te sayıldı."),
               sc(9, "ECPU başına ödenir ve kuyruk birkaç MB'tır. 1 puan kırıldı: kuyruk birkaç MB olsa da Serverless'ta en az 100 MB saklama ödenir.")],
        "mdb": [sc(9, "Aynı Valkey engine'i: XADD, XREADGROUP, XACK. 1 puan kırıldı: iş onaylanmalı ve stream kırpılmalıdır."),
                sc(8, "Aynı engine: consumer group ve bekleyenler listesi. 2 puan kırıldı: XAUTOCLAIM aynı biçimde uygulamanın işidir."),
                sc(6, "Aynı engine: teslim sayısı var, dead-letter taşıması yok. 4 puan kırıldı: aynı uygulama kodu gerekir."),
                sc(9, "Bekleyen worker'lar işi hemen alır. 1 puan kırıldı: her XADD, XREADGROUP ve XACK bir yazmadır ve log'a işlendikten sonra onaylanır; 5 saniyenin çok içindedir ama iş başına birkaç milisaniye ekler."),
                sc(10, "Her yazma çoklu AZ'li log'da kalıcıdır; kuyruktaki iş arızada kaybolmaz. Puan kırılmadı."),
                sc(6, "Yönetilen node'lar. 4 puan kırıldı: serverless seçenek yoktur ve zaten çalışan cache'in yanına node'lu ikinci bir sistem gelir."),
                sc(4, "Node saat başına ödenir. 6 puan kırıldı: yılda birkaç kez yoğun bir kuyruk için cluster yıl boyu çalışır.")],
    },
    h2h={
        "ec": "Bellek içi key-value (ElastiCache) ile kafa kafaya. Bu kartta kaybın büyük kısmı R1'dedir, yani engine'in doğasındadır. Valkey'in en iyi kuyruk aracı consumer group'lu bir stream'dir: XREADGROUP işi bir worker'a verir ve worker'ı iş gelince uyandırır, onaylanmamış iş bekleyenler listesinde kalır ve teslim sayısı tutulur. "
              "Ama bir kuyruğun iki aracı yine uygulamaya kalır: uzun süre bekleyen işi başka bir worker'a veren XAUTOCLAIM'i biri periyodik çalıştırmalıdır (SQS'te görünürlük süresi bunu kendisi yapar) ve üç denemeden sonra işi ayıran bir dead-letter taşıması yoktur. "
              "R1'deki 7 puanlık fark bu iki satırdan gelir; geri kalan fark R3'tedir: kalıcı log olmadan kuyruktaki son işler arızada kaybolabilir. ElastiCache'in zaten çalışıyor olması R4'te artıdır, ama SQS de sunucusuzdur ve kurulumu bir kerelik iştir. "
              "Hangi koşul değişseydi ElastiCache seçilirdi: işler milisaniyenin altında başlamak zorunda olsaydı, yeniden deneme ve bozuk iş ayrımı gerekmeseydi (örneğin kaybı ve tekrarı zararsız bir önbellek ısıtma işi) ya da kuyruk aynı key'lerle birlikte bir Lua script'inde atomik işlenmek zorunda olsaydı.",
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. MemoryDB ElastiCache'in ikizidir ve R1'de onunla aynı puanı alır: aynı stream, aynı eksik araçlar. "
               "Tek artısı R3'tür: log stream'deki işi bir arızada korur. Ama bu kartta kaybolan iş gece kontrolüyle geri gelir; dayanıklılığın değeri sınırlıdır. Buna karşılık serverless seçenek yoktur ve zaten çalışan cache'in yanına node'lu bir sistem gelir (R4, R5). "
               "SQS ise hem dayanıklılığı hem kuyruğun araçlarını (görünürlük süresi, dead-letter queue) hem de sunucusuz işletimi aynı anda verir. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: kuyruk zaten MemoryDB'de duran verilerle aynı Lua script'inde işlenmek zorunda olsaydı ve iş kaybı kabul edilmeseydi.",
    },
    verdict="Karar: SQS {sqs}, ElastiCache {ec}, MemoryDB {mdb}. Bu iş yüküne en uygun servis Amazon SQS'tir; ElastiCache ikincidir ve farkın büyük kısmı R1'den gelir: görünürlük süresi ve dead-letter queue bir kuyruğun engine araçlarıdır; Valkey'in stream'i teslim sayısını ve bekleyenler listesini verir, ama geri vermeyi ve ayırmayı uygulama yazar. "
            "Yine de ElastiCache seçersek artımız: kuyruk zaten çalışan cache'te, XREADGROUP ile iş gelince uyanan worker'lar ve milisaniyelik başlama. "
            "Eksimiz: uygulama XAUTOCLAIM'i periyodik çalıştıran bir iş ve üç kez teslim edilen işi bir \"failed\" stream'ine taşıyan kodu yazmalıdır; bir arızada kuyruğun son işleri kaybolabilir ve gece kontrolü onları yeniden üretmelidir. Bir koşul değişseydi: yeniden deneme ve bozuk iş ayrımı gerekmeseydi ElastiCache yeterdi."))

# ------------------------------------------------------------------ 9. recommendation cache (the DynamoDB card "ads": same rows, weights, points)
ELASTICACHE_W.append(wusecase("reco", 9,
    title="Öneri listeleri için cache",
    key="Key: reco:<kullanıcı id'si>. Value: önceden hesaplanmış 50 ürünlük liste (string, 2 KB).",
    story=estory("reco"),
    wnote="R1 toplam 50: katı 5 ms sınırı engine'in veriyi nerede tuttuğuyla (20) ve gece toplu yazma biçimiyle (15) ilgilidir. "
          "R2 20 ile ikinci: gündüz saniyede 100.000 okuma. R5 bu kartta 15'tir, çünkü saniyede 100.000 okumanın ve 40 GB'ın fiyatı belirleyicidir. R3 5'te, en düşük sınırdadır: liste her gece yeniden hesaplanır.",
    rows=[
        row("EY", 10, "Soru basittir: kullanıcı id'si ile tek bir liste; bu kartın riski hızda ve okuma fiyatındadır.",
            "Tek soru: \"bu kullanıcının listesi\". Listeye göre sorgu yoktur.",
            "Ana sayfa bu okumayı bekler; key ile doğrudan gidilemezse sayfa genel listeye düşer."),
        row("DA", 20, "5 ms sınırı katıdır ve engine'in veriyi bellekte mi diskte mi tuttuğuyla belirlenir.",
            "Okuma 5 ms içinde dönmeli; dönmezse sayfa beklemez ve genel bir liste gösterir.",
            "Sınırı aşan her okuma boşa giden bir öneridir; disk tabanlı bir engine'in tek haneli milisaniyesi yükte 5 ms'yi zaman zaman aşar."),
        row("OY", 15, "Gece 30 dakikada 20 milyon yazma, gündüz sıfır yazma; bu biçim engine'i zorlar.",
            "Gece 30 dakikada 20 milyon listeyi toplu yazmak (saniyede 11.000), gündüz yalnız okumak.",
            "Toplu yazma yavaşsa gece işi sabaha sarkar ve kullanıcılar dünkü listeyi görür."),
        row("VM", 5, "Value basittir: 2 KB'lık tek bir liste; şekli iş yükünü zorlamaz.",
            "Liste tek bir value'dur: 50 ürün id'si, 2 KB.",
            "Liste parçalara bölünürse her okuma birkaç istek olur."),
        row("R2", 20, "Gündüz saniyede 100.000 okuma; gece saniyede 11.000 yazma.",
            "Gündüz saniyede 100.000 okuma; gece 30 dakikada saniyede 11.000 yazma, gündüz sıfır yazma.",
            "Gece yazma penceresi dar: 30 dakikada bitmezse sabah eski listeler kalır; gündüz okuma yavaşlarsa öneriler gösterilmez."),
        row("R3", 5, "Liste her gece yeniden hesaplanır; kaybı bir günlük genel listedir.",
            "Düşük: liste her gece yeniden hesaplanır; kaybolursa bir gün genel liste gösterilir.",
            "Türetilmiş veri; kaynağı modeldir ve yarın yeniden üretilir."),
        row("R4", 10, "Veri ekibi batch işleri ve SDK biliyor, sunucu istemiyor.",
            "Veri ekibi batch işleri ve AWS SDK biliyor, sunucu istemiyor. Gece toplu yazma için ayrı bir büyütme işi istenmiyor.",
            "Her gece elle kapasite artırıp sabah düşürmek sürdürülemez; otomatik olmalıdır."),
        row("R5", 15, "Okuma çok yüksek ve düz; okuma başına fiyat ve 40 GB verinin bellekteki fiyatı belirleyicidir.",
            "Okuma çok yüksek ve düz; okuma başına fiyat belirleyicidir. 20 milyon × 2 KB = 40 GB veri.",
            "Günde 8,6 milyar okuma: okuma birimi fiyatı bu iş yükünün faturasıdır; bellekte 40 GB her saat ödenir."),
    ],
    cands=["ec", "mdb", "ddb"],
    scores={
        "ec": [sc(10, "GET reco:{user} key ile doğrudan okumadır (Ö1). Puan kırılmadı."),
               sc(10, "Liste bellekteki hash table'dadır; okuma mikrosaniyelerdedir ve 5 ms sınırının çok altındadır (Ö1). Puan kırılmadı."),
               sc(9, "Pipeline (komutları cevap beklemeden art arda göndermek) ile toplu SET saniyede 11.000 yazmayı kolayca taşır. 1 puan kırıldı: gece işi her listeye süre (EX, Ö4) koymalı ya da eski listeleri üzerine yazmalıdır."),
               sc(10, "2 KB'lık liste tek bir string value'dur (Ö2). Puan kırılmadı."),
               sc(9, "Serverless saniyede 100.000 okumayı taşır (Ö6). 1 puan kırıldı: gece yazma sıçraması için minimum ECPU ayarı önerilir."),
               sc(9, "Kalıcı bir yazma log'u yoktur, ama listeler bir kopyadır: gece işi onları 30 dakikada yeniden yazar ve kart kaybı ertesi güne kadar kabul eder. 1 puan kırıldı: bir arızadan sonra listeler yeniden yüklenene kadar genel liste gösterilir (yeniden yükleme dakikalar sürerse 1, bir saat ve üstü 2 puan)."),
               sc(9, "Serverless. 1 puan kırıldı: yeniden yükleme işi bir arıza planına yazılmalıdır."),
               sc(6, "ECPU ve GB-saat başına ödenir. 4 puan kırıldı: 40 GB verinin bellekteki saklama fiyatı diskten çok yüksektir ve faturanın büyük kısmıdır (B9).")],
        "mdb": [sc(10, "Aynı Valkey engine'i: GET ile doğrudan okuma. Puan kırılmadı."),
                sc(10, "Okumalar bellekten, mikrosaniyelerde. Puan kırılmadı."),
                sc(9, "Aynı Valkey engine'i: toplu SET pipeline ile yapılır. 1 puan kırıldı: gece işi her listeye süre koymalı ya da eski listeleri üzerine yazmalıdır."),
                sc(10, "Tek bir string value. Puan kırılmadı."),
                sc(7, "Replica ekleyerek okuma ölçeklenir. 3 puan kırıldı: gündüz okumaları etkilenmez, ama her gece yazması log'a işlendikten sonra onaylanır; 30 dakikalık pencere ancak daha çok paralel bağlantı ve pipeline ile tutar ve bunun bir yük testiyle doğrulanması gerekir. Bu, DynamoDB sayfasının aynı kartındaki kırılımdır."),
                sc(10, "Her yazma kalıcıdır. Puan kırılmadı: ama bu kartta dayanıklılık önemsizdir."),
                sc(6, "Yönetilen node'lar. 4 puan kırıldı: serverless seçenek yoktur; node ve replica sayısı ekibin işidir."),
                sc(4, "Node saat başına ödenir; gecelik 40 GB yazma ayda 10 TB'lık ücretsiz yazma payının içindedir. 6 puan kırıldı: 40 GB veri ve replica'lar için büyük node'lar sürekli çalışır; bu kartın istemediği dayanıklılığa para verilir.")],
        "ddb": [sc(10, "GetItem kullanıcı id'si ile doğrudan okumadır. Puan kırılmadı."),
                sc(6, "Veri SSD'deki partition'lardadır; okuma tipik olarak tek haneli milisaniyedir. 4 puan kırıldı: yük altında okumaların bir kısmı 5 ms'yi aşabilir; sınırı garanti etmek için önüne DAX gerekir."),
                sc(9, "BatchWriteItem 25'er value yazar ve gece işi paralel çalışır. 1 puan kırıldı: S3'ten import yalnız yeni bir table oluşturur; var olan table'a toplu yükleme yazma birimi harcar."),
                sc(10, "Liste bir list alanıdır. Puan kırılmadı."),
                sc(8, "Okumalar partition'lara dağılır. 2 puan kırıldı: gece yazmadan gündüz okumaya geçiş bir sıçramadır; on-demand mod bir önceki tepenin iki katına kadar anında uyum sağlar, daha hızlı bir sıçramada kısa bir throttling olabilir."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı: ama bu kartta dayanıklılık önemsizdir."),
                sc(10, "Serverless. Puan kırılmadı."),
                sc(5, "Okuma birimi başına ödenir. 5 puan kırıldı: günde milyarlarca okuma, eventually consistent okumayla bile bellek içi cache'in istek fiyatından çok yüksektir; DAX eklenirse onun node'ları da ödenir.")],
    },
    h2h={
        "mdb": "Kalıcı bellek içi key-value (MemoryDB) ile kafa kafaya. MemoryDB ElastiCache ile aynı Valkey engine'ini çalıştırır ve okumada aynı mikrosaniyeleri verir; R1'de ikisi de 48,5 alır. "
               "Fark servis tasarımındadır ve bu kartta MemoryDB'nin aleyhinedir: her gece 20 milyon yazma log'a işlenir ve yazılan GB ayrıca ödenir; serverless seçenek yoktur ve 40 GB için büyük node'lar sürekli çalışır. "
               "Bütün bunlar, her gece yeniden hesaplanan ve kaybı bir günlük genel liste olan veri için ödenen bir dayanıklılıktır. Farkın tamamı servis tasarımından gelir. "
               "Hangi koşul değişseydi MemoryDB seçilirdi: listeler yeniden hesaplanamasaydı (örneğin elle düzenlenen kampanya listeleri) ve hem mikrosaniye okuma hem kalıcılık aynı anda istenseydi.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB üçüncüdür ama MemoryDB'ye yarım puan uzaktadır ve kararı R1'in depolama satırı verir. İki aday da key ile tek okuma yapar ve gece toplu yazmayı taşır; DynamoDB dayanıklılıkta öndedir. "
               "Ama 5 ms sınırı katıdır: ElastiCache listeyi bellekte tutar ve mikrosaniyede döner, DynamoDB ise SSD'deki partition'lardan tek haneli milisaniyede döner ve yük altında okumaların bir kısmı sınırı aşar. "
               "Sınırı garanti etmek için DynamoDB'nin önüne DAX konur; bu durumda mimari zaten bir bellek içi cache içerir. R5'te de günde milyarlarca okumanın istek başına fiyatı yüksektir. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: sınır 5 ms değil 20 ms olsaydı, okuma hacmi on kat düşük olsaydı ya da listeler kalıcı bir kayıt olsaydı (kullanıcının kendisinin kaydettiği listeler).",
    },
    verdict="Karar: ElastiCache {ec}, MemoryDB {mdb}, DynamoDB {ddb}. Bu iş yüküne en uygun servis ElastiCache'tir; MemoryDB ve DynamoDB neredeyse eşittir. Kararı R1'deki depolama algoritması verir: katı 5 ms sınırı bellekte tutulan veriyle garanti edilir. "
            "ElastiCache seçtiğimizde artımız: mikrosaniye okuma, gece işi için pipeline, sunucusuz işletim. "
            "Eksimiz: 40 GB her saat bellek fiyatıyla ödenir ve bir arızada listeler yeniden yüklenmelidir; uygulama bir yükleme işini arıza planına yazmalı, liste yoksa genel listeyi göstermeli ve gece işini yarıda kalmaya karşı korumalıdır: yeni listeler yeni bir sürüm key'ine (reco:v2026-10-31:<id>) yazılır ve iş bitince okunan sürüm değiştirilir. Bir koşul değişseydi: sınır 20 ms olsaydı DynamoDB kazanırdı."))

# ------------------------------------------------------------------ 10. nearby couriers: geospatial lookups (Aurora wins R1, ElastiCache wins the total)
ELASTICACHE_W.append(wusecase("geo", 10, sim="w_geo",
    title="Yakındaki kuryeler: konum araması",
    key="Key: couriers:istanbul. Value: konum index'i (koordinatı score olarak saklayan bir sorted set); member kurye id'si.",
    story=estory("geo"),
    wnote="R1 toplam 50: arama sorusunun kendisi, 30 saniyelik eskime kuralı, konumların sürekli üzerine yazılması ve aramanın nerede çalıştığı. "
          "R2 20 ile ikinci: kampanya akşamı saniyede 2.000 arama ve 800 yazma. R4 15'tir: ekip üç kişidir ve coğrafi sorgu için yeni bir sistem öğrenmek istemiyor. R3 5'tir: konumlar 5 saniyede bir yeniden gelir.",
    rows=[
        row("EY", 15, "Her sipariş bu soruyu sorar; kurye atanmadan sipariş ekranı ilerlemez.",
            "\"Şu noktaya 3 km içindeki boş kuryeler, yakından uzağa, ilk 5\". Sorunun elinde bir koordinat ve bir yarıçap vardır, kurye id'si yoktur.",
            "Arama yanlış ya da eksik kurye verirse kurye 10 km uzaktan çağrılır ve aynı gün teslimat sözü tutulmaz."),
        row("YD", 15, "Telefonu kapanan bir kurye çağrılırsa sipariş bekler; bu kural her aramada geçerli olmalı.",
            "Konumu 30 saniyedir gelmeyen kurye (telefonu kapanmış, tünelde) aramada çıkmamalı; eskiyen konum kendiliğinden geçersiz olmalı.",
            "Eski bir konumla çağrılan kurye cevap vermez; sipariş ikinci bir aramayı bekler ve müşteri dakikalar kaybeder."),
        row("OY", 10, "Saniyede 800 konum yazması bir üzerine yazmadır; biçimi basit ama sürekli.",
            "\"Bu kuryenin konumu şu\": her 5 saniyede bir üzerine yazma; geçmiş tutulmaz (S3'e ayrıca yazılır).",
            "Her yazma eski bir sürüm bırakıyorsa sürekli üzerine yazılan 4.000 kurye bir temizlik yükü üretir."),
        row("DA", 10, "20 ms sınırı aramanın bellekte mi, diskteki bir index'te mi çalıştığıyla ilgilidir.",
            "Arama 20 ms içinde dönmeli, çünkü sipariş ekranı bekler.",
            "Yavaş arama her siparişi yavaşlatır; kampanya akşamı en çok sipariş en yavaş atamayı görür."),
        row("R2", 20, "Kampanya akşamı saniyede 2.000 arama ve 800 yazma checkout tepesiyle aynı anda gelir.",
            "Saniyede 800 konum yazması, kampanyada saniyede 2.000 arama; her arama 20 ms içinde. Tepe checkout tepesiyle aynı akşamdır.",
            "Sipariş ekranı kurye atanana kadar bekler; yavaş arama ya da yorulan bir database her siparişi yavaşlatır."),
        row("R3", 5, "Konumlar 5 saniyede bir yeniden gelir; kayıp 5 saniyede geri dolar.",
            "Düşük: konumlar 5 saniyede bir yeniden gelir; kaybolan konumlar 5 saniyede geri dolar.",
            "Konum tablosu bir anlık durumdur; geçmiş S3'te ayrıca kalıcıdır."),
        row("R4", 15, "Üç geliştirici; coğrafi sorgu için yeni bir sistem öğrenmek istenmiyor.",
            "Üç geliştirici; sunucu istenmiyor; coğrafi sorgu için yeni bir sistem öğrenmek istenmiyor. Teslimat bölgeleri Aurora'da (PostGIS) zaten vardır.",
            "Coğrafi sistemler projeksiyon, index türü ve sıralama gibi yeni kavramlar ister."),
        row("R5", 10, "Veri küçüktür; yazma ve arama süreklidir.",
            "Veri küçüktür: 4.000 kurye. Yazma ve arama sürekli; istek başına ödeme tercih edilir.",
            "Küçük ve sürekli değişen veride belirleyici olan istek fiyatıdır."),
    ],
    cands=["ec", "aur", "os"],
    scores={
        "ec": [sc(9, "GEOSEARCH couriers:istanbul FROMLONLAT … BYRADIUS 3 km ASC COUNT 5 soruyu tek komutta, yakından uzağa cevaplar (Ö2). 1 puan kırıldı: \"boş\" koşulu index'te yoktur; meşgul kuryeler ayrı bir set'tedir ve uygulama ilk sonuçları onunla eler (ya da bir Lua script'i birlikte yapar)."),
               sc(5, "Süre key başınadır, member başına değildir (Ö4). 5 puan kırıldı: 30 saniyedir susan kurye konum index'inde kalır; son görülme zamanı ikinci bir sorted set'te tutulur ve eski member'ları ZREMRANGEBYSCORE (score'u bir aralıkta olan member'ları silen komut) ve ZREM ile silen periyodik bir iş yazılır."),
               sc(10, "GEOADD var olan member'ın konumunu yerinde değiştirir; eski sürüm kalmaz (Ö2). Puan kırılmadı."),
               sc(10, "Konum index'i bellekteki bir sorted set'tir; arama milisaniyenin altındadır (Ö1). Puan kırılmadı."),
               sc(10, "Saniyede 2.000 arama ve 800 yazma Serverless için küçük bir yüktür ve Aurora'ya dokunmaz (Ö6). Puan kırılmadı."),
               sc(4, "Kalıcı bir yazma log'u yoktur. 6 puan kırıldı: bir arızada son konumlar kaybolabilir; 5 saniye sonra yeniden dolarlar ve bu kartta kabul edilen bir sonuçtur."),
               sc(10, "Cache zaten çalışır; GEOADD ve GEOSEARCH birkaç satırdır. Puan kırılmadı: eskiyen kuryeleri silen iş R1.2'de sayıldı."),
               sc(9, "ECPU başına ödenir ve veri çok küçüktür. 1 puan kırıldı: GEOSEARCH basit bir GET'ten daha fazla ECPU harcar.")],
        "aur": [sc(10, "ST_DWithin ile 3 km, ORDER BY konum <-> nokta LIMIT 5 ile en yakın beş ve WHERE status = 'free' tek bir SQL sorgusudur; GiST index'i kullanılır. Puan kırılmadı."),
                sc(10, "WHERE last_seen > now() - interval '30 seconds' aynı sorgudadır; eskiyen konum doğruluk için bir temizlik işi istemez. Puan kırılmadı."),
                sc(6, "UPDATE couriers SET pos = … her 5 saniyede bir yapılır. 4 puan kırıldı: PostgreSQL her UPDATE'te row'un yeni bir sürümünü yazar (MVCC) ve GiST index'ini günceller; saniyede 800 güncelleme sürekli bir VACUUM yükü üretir."),
                sc(8, "GiST index'i buffer cache'te durur ve arama birkaç milisaniyedir. 2 puan kırıldı: 20 ms sınırının içindedir, ama arama bellekten değil bir index sayfa zincirinden gelir."),
                sc(7, "Okumalar reader'lara gönderilebilir. 3 puan kırıldı: saniyede 800 güncelleme checkout'u yapan tek writer'dan geçer ve kampanya akşamı checkout tepesiyle aynı anda gelir; tepe anında konum yazmaları ile siparişler aynı writer'ı bekler (Aurora sayfasının tek writer tablosu: 500–5.000, checkout ile aynı tepede 3 puan)."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(8, "Aurora ve PostGIS zaten çalışır ve ekip bölgeleri orada sorgular. 2 puan kırıldı: kampanya için bir reader eklemek ve aramaları reader endpoint'ine yönlendirmek ekibin işidir; VACUUM yükü R1.3'te sayıldı."),
                sc(6, "Var olan cluster'a eklenir. 4 puan kırıldı: kampanya akşamı için bir reader ve daha yüksek bir minimum ACU ödenir.")],
        "os": [sc(9, "geo_distance filtresi, mesafeye göre sıralama ve status filtresi tek bir sorgudur. 1 puan kırıldı: sonuç bir sonraki refresh'e kadar en yeni konumu görmeyebilir."),
               sc(10, "last_seen üzerinde bir range filtresi aynı sorgudadır; 30 saniyedir susan kurye temizlik işi olmadan sorgudan düşer. Puan kırılmadı: refresh gecikmesi R1.1'de bir kez sayıldı."),
               sc(4, "Her konum güncellemesi document'ın yeniden index'lenmesidir. 6 puan kırıldı: saniyede 800 yeniden index'leme segment birleştirme yükü ve silinmiş document'lar üretir."),
               sc(7, "Konumlar diskteki bir geo index'indedir ve sık okunan kısmı bellekte tutulur. 3 puan kırıldı: arama onlarca milisaniyeye çıkabilir ve 20 ms sınırına yaklaşır."),
               sc(6, "Data node'ları eklenerek ölçeklenir. 4 puan kırıldı: kampanya tepesinde 800 yeniden index'leme ve segment birleştirmesi 2.000 aramayla aynı node'larda yarışır (node boyutlandırması R4'te sayıldı)."),
               sc(9, "Replica shard'ları bir node arızasını karşılar. 1 puan kırıldı: kayıt sistemi değildir; konumlar 5 saniyede yeniden gelir."),
               sc(4, "Yönetilen domain. 6 puan kırıldı: ekip için yeni bir sistem; node sayısı ve tipi, mapping, shard ve refresh ayarı üç kişilik ekibin işidir."),
               sc(5, "Data node'ları saat başına ödenir. 5 puan kırıldı: 4.000 kuryelik küçük bir veri için node'lar gece gündüz çalışır.")],
    },
    h2h={
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Bu kartta engine uyumunu Aurora kazanır ve bunu açıkça söylemek gerekir: PostGIS tek bir SQL sorgusunda yarıçapı, en yakın beşi, \"boş\" koşulunu ve 30 saniyelik eskime kuralını birlikte uygular; ElastiCache'te son ikisi ikinci bir yapı ve bir temizlik işidir. "
               "Ama Aurora'nın engine'i sürekli üzerine yazmayı sevmez: her UPDATE yeni bir row sürümü bırakır ve saniyede 800 güncelleme bir VACUUM yüküdür (R1.3). "
               "Toplamı R2 ve R5 çevirir: bu yazmalar checkout'u yapan tek writer'dan, kampanya akşamı checkout tepesiyle aynı anda geçer. "
               "Doğru mimari ikisi birliktedir: bölgelerin çokgenleri ve fiyatları Aurora'da (PostGIS), canlı konumlar ElastiCache'te. "
               "Hangi koşul değişseydi Aurora seçilirdi: kurye sayısı ve konum sıklığı on kat düşük olsaydı ya da arama her seferinde bölge çokgenleriyle aynı sorguda birleştirilmek zorunda olsaydı.",
        "os": "Search engine (OpenSearch) ile kafa kafaya. OpenSearch'ün geo sorguları güçlüdür: mesafe, sıralama ve filtreler tek bir sorguda birleşir ve konumu metinle ya da başka alanlarla birlikte aramak onun işidir. "
              "Ama bu iş yükü bir arama değil, saniyede 800 kez değişen küçük bir anlık durumdur. Her konum değişikliği bir yeniden index'lemedir ve yeni konum ancak refresh'ten sonra görünür (R1.3, R1.1). "
              "Üç kişilik ekip için yeni bir sistem ve gece gündüz çalışan data node'ları R4 ve R5'te de puan kaybettirir. "
              "Hangi koşul değişseydi OpenSearch seçilirdi: kurye aramasıyla birlikte metin araması istenseydi (örneğin \"yakındaki ve yorumunda 'hızlı' geçen restoranlar\") ve konumlar dakikada bir değişseydi.",
    },
    verdict="Karar: ElastiCache {ec}, Aurora {aur}, OpenSearch {os}. Bu iş yüküne en uygun servis ElastiCache'tir, ama engine uyumunda Aurora öndedir: PostGIS bütün kuralı tek sorguda uygular. ElastiCache'i öne geçiren R2'dir: sürekli yazmalar ve kampanya aramaları checkout'un writer'ından uzak kalır. "
            "ElastiCache seçtiğimizde artımız: tek komutla en yakın beş, yerinde üzerine yazma, milisaniyenin altında arama ve Aurora'ya sıfır yük. "
            "Eksimiz: 30 saniyelik kural ikinci bir sorted set ve periyodik bir silme işiyle uygulanır, \"boş\" kuryeler uygulamada elenir; bölge ve fiyat soruları için Aurora'ya gidilir, yani mimari ikisi birliktedir. Bir koşul değişseydi: kampanya aramaları checkout tepesiyle çakışmasaydı Aurora'nın R2'si tek writer tablosunun ilk sütununa geçer ve iki aday 87'de eşitlenirdi; konumlar da on kat seyrek gelseydi Aurora tek başına yeterdi."))

USECASES_W["elasticache"] = ELASTICACHE_W
PAGE_SVC["elasticache"] = "ec"


# ====================================================================== Amazon Neptune (page id "neptune"), model 2, Turkish only
# The ten M2 cards of templates/e2e/neptune.tr.html and the five M7 simulations (weighted_scorecard). en = None.
# Candidates: "np" = Neptune Database (SVC "Neptune", the page's service), "npa" = Neptune Analytics. They share the property
# graph model and openCypher but are different engines (disk-based cluster volume with three quad indexes and OLTP isolation,
# versus one memory-optimized instance with built-in algorithms and a vector index): NOT twins, R1 is scored separately.
# Neptune Serverless and provisioned instances are two deployments of the same Neptune Database (R2, R4, R5 only).
# Sources (hedges as in the source; full list in docs/neptune.scope.md):
#   one primary and up to 15 replicas, replicas on the same cluster volume, failover "generally less than 30 seconds":
#       https://docs.aws.amazon.com/prescriptive-guidance/latest/neptune-well-architected-framework/reliability-pillar.html
#   copies in three AZs, replication independent of the instances: https://docs.aws.amazon.com/neptune/latest/userguide/storage.html
#   six copies of each 10 GB chunk in three AZs, backups up to 35 days: https://aws.amazon.com/documentation-overview/neptune/
#   read-only queries SNAPSHOT, mutations READ COMMITTED with range locks, lock wait up to 60 s, replica lag:
#       https://docs.aws.amazon.com/neptune/latest/userguide/transactions-neptune.html
#   three default indexes SPOG, POGS, GPSO; OSGP only on an empty cluster: https://docs.aws.amazon.com/neptune/latest/userguide/feature-overview-storage-indexing.html
#   openCypher in Neptune: shortestPath() and CALL not supported, VLP: https://docs.aws.amazon.com/neptune/latest/userguide/feature-opencypher-compliance.html
#   no TTL in the engine (TTL is built with Lambda + DynamoDB): https://aws.amazon.com/blogs/database/implement-time-to-live-in-amazon-neptune-part-1-property-graph/
#   full-text search through OpenSearch replication: https://docs.aws.amazon.com/neptune/latest/userguide/full-text-search.html
#   Streams 1-90 days, default 7: https://docs.aws.amazon.com/neptune/latest/userguide/streams-using-enabling.html
#   Neptune Analytics: one memory-optimized instance, replicas are passive failover targets, priced per m-NCU:
#       https://docs.aws.amazon.com/prescriptive-guidance/latest/neptune-analytics-well-architected-framework/reliability-pillar.html
#   Neptune Analytics: 25+ algorithms as openCypher procedures, vector search (HNSW):
#       https://docs.aws.amazon.com/neptune-analytics/latest/userguide/algorithms.html ; one vector index: https://aws.amazon.com/neptune/faqs/
#   Neptune Analytics mutation reads under snapshot isolation: https://docs.aws.amazon.com/neptune-analytics/latest/userguide/query-isolation-level.html
#   Neptune Database vs Analytics: https://docs.aws.amazon.com/neptune-analytics/latest/userguide/neptune-analytics-vs-neptune-database.html
#   Prices, Price List API, eu-central-1, 2026-10-31: Serverless 0.1941 USD per NCU-hour; storage 0.119 USD per GB-month;
#       0.22 USD per million I/O; Analytics 32 m-NCU 1.162 USD per hour, 128 m-NCU 4.647 USD per hour, a stopped graph 10 %.
#   Redshift recursive CTE: https://docs.aws.amazon.com/redshift/latest/dg/r_WITH_clause.html
CATEGORY.setdefault("np", ("graph", "graph"))
LINK.setdefault("np", "neptune")
CATEGORY.setdefault("npa", ("in-memory graph analytics", "bellek içi graph analitiği"))
LINK.setdefault("npa", "neptune")          # Neptune Analytics has no page of its own; this page (A9, M5, C2) compares them

NEPTUNE_W = []

# ------------------------------------------------------------------ 1. social graph: people you may know (Neptune wins on its engine)
NEPTUNE_W.append(wusecase("social", 1, sim="w_social",
    title="Sosyal graph: tanıyor olabileceğin kişiler",
    key="Vertex: User. Edge: FRIEND. Soru: bu kullanıcıdan iki hop uzaktaki, henüz arkadaşı olmayan kişiler, ortak arkadaş sayısına göre.",
    story="Bir kitap kulübü uygulamasının 2 milyon kullanıcısı ve 60 milyon arkadaşlık bağlantısı var. Ana sayfadaki \"Tanıyor olabileceğin kişiler\" kutusu kullanıcının arkadaşlarının arkadaşlarını ortak arkadaş sayısına göre sıralar ve zaten arkadaş olanları çıkarır. "
          "Kutu her ana sayfa açılışında hesaplanır: akşam saatlerinde saniyede 3.000 istek, her biri 100 ms bütçeyle; gece trafik onda birine düşer. Bir kullanıcının ortalama 30 arkadaşı var, ama 40 yazar hesabının her birinin 50.000'den fazla takipçisi var. "
          "Yeni bir arkadaşlık bir sonraki açılışta öneriyi değiştirmeli. Ekip dört geliştiriciden oluşuyor ve SQL biliyor, graph dili bilmiyor. Kullanıcı profilleri bugün Aurora PostgreSQL'de duruyor; arkadaşlıklar yeni bir özellik olarak yazılacak.",
    wnote="R1 toplam 50: sorunun kendisi iki hop'luk bir yol (20) ve bu yolun her istekte, yazar hesaplarına rağmen bütçede kalması (15) bu kartın riskidir. "
          "R2 20 ile ikinci: akşam saniyede 3.000 öneri. R4 12'dir, çünkü ekip graph dili bilmiyor ve küçük; R5 8'dir, çünkü trafik akşam ve gece çok farklıdır.",
    rows=[
        row("EY", 20, "Kutu her ana sayfa açılışında bu soruyu sorar; sorunun şekli iş yükünün kendisidir.",
            "\"Bu kullanıcının arkadaşlarının arkadaşları, ortak arkadaş sayısına göre, zaten arkadaş olanlar ve kendisi hariç, ilk 20.\" Sorunun elinde bir kullanıcı id'si var; cevap iki hop uzaktadır.",
            "Soru tek bir istekte cevaplanamazsa uygulama arkadaş listesini çekip her arkadaş için ayrı istek gönderir; 30 arkadaşta 31 istek olur ve 100 ms bütçesi aşılır."),
        row("DA", 15, "40 yazar hesabı 50.000'den fazla takipçiyle her akşam binlerce isteğin yolunda durur.",
            "Bir isteğin maliyeti 2 milyon kullanıcıya değil, yalnız bu kullanıcının komşularına bağlı olmalı. Yazar hesapları (supernode) bir isteği bütçenin dışına taşımamalı.",
            "Maliyet graph'ın boyutuyla büyürse her yeni kullanıcı her isteği yavaşlatır; bir yazar hesabından geçen tek istek saniyeler sürerse akşam kuyruğu büyür."),
        row("OY", 10, "Her yeni arkadaşlık bir yazmadır, ama biçimi basittir: iki kullanıcı arasına bir bağlantı.",
            "Bir arkadaşlık tek bir yazmayla eklenir ya da silinir ve bir sonraki öneri onu hemen sayar; iki yöne ayrı ayrı yazmak gerekmemeli.",
            "Bağlantı iki kayıt olarak yazılırsa bir arızada yalnız biri kalabilir ve öneri tek taraflı bir arkadaşlığı sayar."),
        row("VM", 5, "Veri doğası gereği bir ağdır, ama şekli basittir: tek tür vertex, tek tür edge.",
            "Veri: kullanıcılar ve aralarındaki arkadaşlıklar; bağlantının kendisi veridir (ne zaman kuruldu).",
            "Bağlantılar başka bir şeklin içine gömülürse (bir dizi alan) her ilişki iki yerde tutulur ve senkron kalmaz."),
        row("R2", 20, "Akşam saniyede 3.000 istek; trafik bu iş yükünün en riskli anıdır.",
            "Akşam saniyede 3.000 öneri isteği, her biri 100 ms içinde; gece trafik onda birine düşer. Saniyede 50 yeni arkadaşlık yazılır.",
            "Akşam kutu yavaşlarsa ana sayfa beklemez ve kutuyu boş gösterir; büyüme kanalı tepe saatinde durur."),
        row("R3", 10, "Arkadaşlık kullanıcının kendi kurduğu bir kayıttır; öneri kutusu ise yeniden hesaplanabilir.",
            "Onaylanan bir arkadaşlık bir arızada kaybolmamalı.",
            "Kaybolan bir arkadaşlığı kullanıcı tekrar kurmak zorunda kalır ve güven kaybolur."),
        row("R4", 12, "Dört kişilik ekip graph dili bilmiyor; yeni bir sistem ürün geliştirmeden zaman çalar.",
            "Dört geliştirici SQL biliyor; yeni bir sorgu dili öğrenmek kabul edilir, sunucu boyutlandırmak istenmiyor. Profiller Aurora'da kalır.",
            "Küçük bir ekipte ikinci bir database ikinci bir yedekleme, izleme ve veri akışı işidir."),
        row("R5", 8, "Akşam ile gece arasında on kat fark var; ödeme modeli bu farkı takip etmeli.",
            "Trafik akşam yoğun, gece çok düşük. Veri birkaç on GB'tır.",
            "Akşam tepesine göre boyutlanmış kapasite gecenin büyük kısmında boş durur ve ödenir."),
    ],
    cands=["np", "aur", "ddb"],
    scores={
        "np": [sc(10, "User vertex'leri ve FRIEND edge'leri (Ö1); öneri openCypher'da tek bir pattern'dir (Ö4): (me)-[:FRIEND]-()-[:FRIEND]-(fof) WHERE NOT (me)-[:FRIEND]-(fof) AND fof <> me, sonra count() ile sıralama. Puan kırılmadı."),
               sc(9, "Başlangıç vertex'i ~id ile bulunur (Ö2) ve traversal yalnız bu kullanıcının komşularını okur (Ö3); iş 2 milyon kullanıcıya değil, yaklaşık 900 edge'e bağlıdır. 1 puan kırıldı: yazar hesapları supernode'dur; önceden bilindikleri için sorgu onları bir label ile (:Author) dışarıda bırakmalıdır (A4)."),
               sc(10, "Tek bir CREATE (a)-[:FRIEND]->(b) arkadaşlığı yazar; yönsüz sorgu (-[:FRIEND]-) edge'i iki yönde de okur, ikinci kayıt gerekmez (Ö1, Ö6). Puan kırılmadı."),
               sc(10, "Veri doğrudan vertex ve edge'tir; since gibi bir property edge'in üzerinde durur (Ö1). Puan kırılmadı."),
               sc(9, "Okumalar 15'e kadar read replica'ya dağılır ve Serverless instance'ları akşam yükle büyür; saniyede 50 yazma writer için küçüktür. 1 puan kırıldı: bütün yazmalar tek writer'dan geçer ve replica'lar writer'ın birkaç milisaniye gerisindedir; yeni arkadaşlık replica'dan okunan bir öneride o kadar geç görünür."),
               sc(10, "Cluster volume her 10 GB'ı üç AZ'de altı kopya olarak tutar; onaylanan yazma kaybolmaz. Puan kırılmadı."),
               sc(7, "Yönetilen cluster; yedek, yama ve failover servistir. 3 puan kırıldı: ekip openCypher öğrenir (2) ve replica sayısı ile NCU aralığını akşam tepesine göre ayarlar (1)."),
               sc(7, "Serverless NCU-saat başına ödenir. 3 puan kırıldı: kapasite sıfıra inmez; gece de writer ve reader'ın en az 1'er NCU'su ödenir (eu-central-1'de NCU-saat 0,1941 USD, instance başına ayda yaklaşık 142 USD).")],
        "aur": [sc(8, "Arkadaşlık bir edge table'ıdır; öneri iki self-join, NOT EXISTS ve GROUP BY ile tek bir SQL sorgusudur. 2 puan kırıldı: her hop FROM'da table'ın bir kopyası daha demektir ve sorgu bir pattern değil bir join planıdır."),
                sc(7, "(user_id, friend_id) B-tree index'i ile her hop index aramasıdır; yazar hesapları Neptune'deki gibi bir koşulla (is_author = false) dışarıda bırakılır. 3 puan kırıldı: her hop bir birleştirmedir ve ara sonuç çoğalır (30 × 30 = 900 row her istekte birleştirilip gruplanır); akşam saniyede 3.000 istekte bu, komşuluğu bir index aralığı olarak okuyan graph'tan pahalıdır."),
                sc(9, "INSERT tek row yazar. 1 puan kırıldı: yönsüz arkadaşlık ya iki row (iki yön) olarak yazılır ya da her sorgu iki kolonu OR ile arar."),
                sc(9, "Edge table'ı bir ağı taşır. 1 puan kırıldı: ilişki row'lardaki iki id'dir; graph'ın kendisi değil, onun bir tablosudur."),
                sc(7, "Okumalar reader'lara gider ve Serverless v2 ACU'yu artırır. 3 puan kırıldı: akşam saniyede 3.000 birleştirme ve gruplama sorgusu reader'ları yorar; tepe için birkaç reader gerekir."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(9, "Profiller zaten Aurora'da; ekip SQL biliyor ve yeni sistem yok. 1 puan kırıldı: akşam tepesi için reader sayısı ve ACU aralığı ayarlanır."),
                sc(7, "Var olan cluster'a bir table eklenir. 3 puan kırıldı: akşam için eklenen reader'lar ve yüksek ACU saat başına ödenir ve kapasite gece de sıfıra inmez.")],
        "ddb": [sc(3, "Adjacency list deseni: partition key kullanıcı, sort key arkadaş; bir Query arkadaşları verir. 7 puan kırıldı: ikinci hop için uygulama 30 Query daha gönderir, sonuçları birleştirir, sayar, sıralar ve zaten arkadaş olanları kendisi çıkarır; 31 istek bir pattern değildir."),
                sc(6, "Her Query bir partition'a gider ve tek haneli milisaniyedir. 4 puan kırıldı: bir yazar hesabının 50.000 takipçisi tek bir büyük item collection'dır; onu okuyan istekler hem büyük hem aynı partition'a yığılır (hot partition)."),
                sc(9, "PutItem bağlantıyı yazar. 1 puan kırıldı: iki yönde okunabilmesi için iki item yazılır (ya da GSI ile ters yön); ikisi birlikte transaction ile yazılmalıdır."),
                sc(6, "Bağlantı bir item'dır. 4 puan kırıldı: graph partition key ve sort key çiftlerine düzleştirilir; bağlantının iki ucu ayrı item'larda tekrarlanır."),
                sc(10, "Okumalar partition'lara dağılır; on-demand mod akşam tepesini ayarsız karşılar. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(8, "Serverless, sunucu yok. 2 puan kırıldı: ekip DynamoDB API'ını ve key tasarımını öğrenir; birleştirme kodu R1.1'de sayıldı."),
                sc(9, "On-demand modda istek başına ödenir; gece maliyet düşer. 1 puan kırıldı: tepe saatin birim tüketimi önceden hesaplanmalıdır.")],
    },
    h2h={
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Aurora bu soruyu yazabilir: iki self-join, NOT EXISTS ve GROUP BY tek bir SQL sorgusudur ve profiller zaten oradadır, bu yüzden R4'te öndedir. "
               "Fark R1'in depolama satırındadır: bir graph engine'i bir vertex'ten başlar ve yalnız onun edge'lerini okur; ilişkisel engine her hop'ta index'te arar ve ara sonucu çoğaltır. "
               "Yazar hesabından geçen bir istekte bu 50.000 row'luk bir birleştirme ve gruplamadır ve akşam saniyede 3.000 istek reader'ları yorar (R2). "
               "Hangi koşul değişseydi Aurora seçilirdi: trafik saniyede birkaç yüz isteğe inseydi, supernode olmasaydı ve öneri her gece toplu hesaplanıp bir table'a yazılsaydı; o zaman ikinci bir database'in bedeli kazancından büyük olurdu.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB ölçekte ve işletimde rakipsizdir: on-demand mod akşam tepesini ayarsız karşılar ve gece neredeyse hiç ödenmez (R2, R5). "
               "Ama engine iki hop'u bilmez: adjacency list deseninde bir Query arkadaşları verir, arkadaşların arkadaşları için uygulama 30 Query daha gönderir ve sonuçları kendisi birleştirir, sayar ve eler (R1.1). "
               "Yazar hesapları büyük item collection'lardır ve aynı partition'a yığılır (R1.2). Kaybın tamamı R1'dedir: 27'ye 48,5. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: soru tek hop olsaydı (\"bu kullanıcının arkadaşları\", \"beni takip edenler\") ya da öneriler gece başka bir yerde hesaplanıp kullanıcı başına bir liste olarak saklansaydı.",
    },
    verdict="Karar: Neptune {np}, Aurora {aur}, DynamoDB {ddb}. Bu iş yüküne en uygun servis Neptune'dür ve farkın neredeyse tamamı R1'dedir: iki hop'luk öneri bir pattern'dir ve maliyeti graph'ın boyutuna değil komşulara bağlıdır. "
            "Neptune seçtiğimizde artımız: öneri tek bir sorgudur, yeni arkadaşlık hemen sayılır, üçüncü bir hop eklemek pattern'e bir parça eklemektir ve okumalar replica'larla büyür. "
            "Eksimiz: ekip openCypher öğrenir, yazar hesaplarını sorgudan bir label ile dışarıda bırakır ve gece de iki instance'ın en düşük NCU'su ödenir; profiller Aurora'da kalır ve uygulama kullanıcı silinince vertex'i de siler. Bir koşul değişseydi: öneriler gecelik bir toplu işle hesaplansaydı Aurora yeterdi."))

# ------------------------------------------------------------------ 2. fraud ring check at payment time (R1 equal with Neptune Analytics, service design decides)
NEPTUNE_W.append(wusecase("fraud", 2, sim="w_fraud",
    title="Ödeme anında dolandırıcılık halkası kontrolü",
    key="Vertex: Card, Device, Address, Phone, Account. Edge: USED, LIVES_AT, OWNS. Soru: bu ödemenin kartı ya da cihazı, en fazla üç hop'ta işaretli bir hesaba bağlı mı?",
    story="Lale Market'in ödeme ortağı her kartlı ödemede bir dolandırıcılık kontrolü yapar. Graph'ta 30 milyon vertex (kart, cihaz, adres, telefon, hesap) ve 120 milyon edge var; 2.000 hesap dolandırıcılık nedeniyle işaretli. "
          "Her ödemede soru şudur: bu kart, bu cihaz ya da bu teslimat adresi en fazla üç hop'ta işaretli bir hesaba bağlı mı? Cevap 50 ms içinde gelmeli, yoksa ödeme kontrolsüz geçer. "
          "Gündüz saniyede 800, kampanya akşamı saniyede 2.400 ödeme olur; her ödeme iki ya da üç yeni edge yazar (kart bu cihazı kullandı) ve bir sonraki ödeme bu edge'i görmelidir. "
          "Bazı adresler (bir alışveriş merkezi, bir kargo deposu) on binlerce karta bağlıdır. Altı kişilik veri ekibi bir pilot projede openCypher kullandı. Edge'ler denetim kanıtıdır ve kaybolmamalıdır.",
    wnote="R1 toplam 50: üç hop'luk soru (15), her ödemede 50 ms (15), ödeme başına yeni edge'ler (10) ve yeni edge'in bir sonraki kontrolde görünmesi (10). "
          "R2 20 ile ikinci: kampanya akşamı saniyede 2.400 kontrol ve 7.000'den fazla edge yazması. R3, R4 ve R5 10'ar: kanıt kaybolmamalı, ekip küçük, trafik gün boyu süreklidir.",
    rows=[
        row("EY", 15, "Her ödeme bu soruyu sorar; cevap gelmezse ödeme kontrolsüz geçer.",
            "\"Bu kartın, cihazın ya da adresin en fazla üç hop'ta işaretli bir hesaba yolu var mı?\" Hop sayısı 1 ile 3 arasındadır ve edge türü dörttür. Cevap evet ise yol da dönmeli (inceleme için).",
            "Soru birkaç ayrı isteğe bölünürse 50 ms bütçesi aşılır; yol dönmezse analist neden reddedildiğini göremez."),
        row("DA", 15, "50 ms her ödemede geçerlidir; ortak adresler on binlerce karta bağlıdır.",
            "Kontrolün maliyeti 30 milyon vertex'e değil, ödemenin komşularına bağlı olmalı. Bilinen ortak adresler (supernode) kontrolü bütçenin dışına taşımamalı.",
            "Bir alışveriş merkezi adresinden geçen kontrol saniyeler sürerse o ödeme ya bekler ya da kontrolsüz geçer."),
        row("OY", 10, "Her ödeme iki ya da üç edge yazar; biçimi basit ama süreklidir.",
            "Ödeme anında \"bu kart bu cihazı kullandı\" edge'i eklenir; cihaz ilk kez görülüyorsa vertex'i de oluşturulur (yoksa oluştur).",
            "Cihaz vertex'i iki kez oluşturulursa halka iki parçaya bölünür ve bağlantı görünmez."),
        row("TA", 10, "Dolandırıcı aynı cihazla art arda ödeme dener; ikinci ödeme ilkinin edge'ini görmelidir.",
            "Onaylanan bir edge bir sonraki kontrolde görünmeli; kontrol yarım yazılmış bir ödemeyi görmemeli.",
            "Yeni edge görünmezse aynı cihazla yapılan ikinci ve üçüncü ödeme de temiz görünür."),
        row("R2", 20, "Kampanya akşamı saniyede 2.400 kontrol ve yazma aynı anda gelir.",
            "Gündüz saniyede 800, kampanya akşamı saniyede 2.400 kontrol; her biri 50 ms içinde. Saniyede 7.200'e kadar edge yazması.",
            "Tepe anında kontrol yavaşlarsa ödemeler ya bekler ya da kontrolsüz geçer; ikisi de para kaybıdır."),
        row("R3", 10, "Edge'ler denetim kanıtıdır; bir itirazda geri istenir.",
            "Onaylanan hiçbir edge bir arızada kaybolmamalı; geçmişe dönük geri yükleme mümkün olmalı.",
            "Kanıt kaybolursa bir itiraz kaybedilir ve halkanın geçmişi kurulamaz."),
        row("R4", 10, "Altı kişilik ekip openCypher'ı pilot projeden biliyor; sunucu işletmek istemiyor.",
            "Altı veri mühendisi openCypher'ı bir pilotta kullandı. Sunucu, yama ve failover işi istenmiyor.",
            "Kapasite ve failover işi ekibin kural geliştirme zamanını yer."),
        row("R5", 10, "Trafik gün boyu süreklidir; fiyat birimi bunu takip etmeli.",
            "Trafik gün boyu süreklidir, akşam üç katına çıkar. Graph 120 milyon edge'tir.",
            "Graph'ın tamamı için gece gündüz büyük bir kapasite ödenirse kontrol başına maliyet büyür."),
    ],
    cands=["np", "npa", "aur"],
    scores={
        "np": [sc(10, "Değişken uzunlukta bir pattern (Ö5): MATCH p = (c:Card {`~id`: $card})-[:USED|LIVES_AT|OWNS*1..3]-(a:Account {flagged: true}) RETURN p LIMIT 1. Yol da döner. Puan kırılmadı."),
               sc(9, "Kontrol kartın vertex'inden başlar ve yalnız komşuları okur (Ö2, Ö3). 1 puan kırıldı: bilinen ortak adresler supernode'dur; önceden işaretlenir ve sorgu onlardan geçmez (A4)."),
               sc(10, "MERGE cihaz vertex'ini yoksa oluşturur, CREATE edge'i yazar; ikisi bir transaction'dır (Ö6). Puan kırılmadı."),
               sc(10, "Okuma sorguları snapshot isolation ile çalışır: yarım yazılmış bir ödemeyi görmez, commit edilmiş edge'i görür (Ö6). Puan kırılmadı."),
               sc(8, "Kontroller 15'e kadar replica'ya dağılır. 2 puan kırıldı: kampanya akşamı saniyede 7.200 edge yazması tek writer'dan geçer; AWS tek bir writer için bir yazma sayısı vermez, bu hız bir yük testiyle doğrulanmalıdır. Replica'lar writer'ın birkaç milisaniye gerisindedir; aynı cihazla milisaniyeler içinde gelen ikinci ödeme ilkinin edge'ini görmeyebilir ve bu küçük pencere kabul edilir."),
               sc(10, "Altı kopyalı cluster volume; 35 güne kadar point-in-time restore. Puan kırılmadı."),
               sc(9, "Yönetilen cluster; ekip openCypher biliyor. 1 puan kırıldı: replica sayısı ve NCU aralığı kampanya akşamına göre ayarlanır."),
               sc(8, "NCU-saat ya da instance-saat başına ödenir; sürekli trafiğe uyar. 2 puan kırıldı: akşamın üç katı için replica'lar ve NCU'lar saat başına ödenir.")],
        "npa": [sc(10, "Aynı property graph ve aynı openCypher pattern'i (Ö5); yol döner. Puan kırılmadı."),
                sc(9, "Graph bellekte durur ve kontrol yalnız komşuları okur. 1 puan kırıldı: ortak adresler supernode'dur; burada da önceden işaretlenir ve sorgu onlardan geçmez."),
                sc(10, "openCypher MERGE ve CREATE yazar; MERGE eşzamanlı yazmalarda tek vertex oluşturur. Puan kırılmadı."),
                sc(10, "Okuma sorguları snapshot isolation ile çalışır; commit edilmiş edge'i görür. Puan kırılmadı: mutation okumalarının daha gevşek izolasyonu bu iş yükünde bir koşula bağlı yazma olmadığı için fark yaratmaz."),
                sc(5, "Graph tek bir bellek odaklı instance'tır. 5 puan kırıldı: AWS'e göre replica'lar pasif failover hedefidir ve okuma ölçeklemez; saniyede 2.400 kontrol ve 7.200 yazma tek instance'ın işidir ve kapasite yalnız bir yönetim işlemiyle dikey büyür."),
                sc(8, "Graph verisi durdurup başlatmada korunur; AWS'e göre hot standby başka bir AZ'de bekler ve failover saniyeler sürer, standby yoksa kapasite dakikalar içinde yeniden kurulur. 2 puan kırıldı: geri dönüş kullanıcının aldığı snapshot'lardan yeni bir graph kurmaktır; Neptune Database'in 35 güne kadar herhangi bir ana dönen point-in-time restore'u Neptune Analytics için aynı biçimde belgelenmiş değildir, bu yüzden kanıt için bir saniyeye dönüş garanti edilmez."),
                sc(9, "Sunucusuz bir graph; algoritmalar ve notebook'lar hazır. 1 puan kırıldı: m-NCU boyutu graph'ın büyüklüğüne göre seçilir; büyütmenin bir yönetim işlemi olması R2'de sayıldı."),
                sc(5, "m-NCU-saat başına ödenir. 5 puan kırıldı: graph'ın tamamı için bellek gece gündüz ödenir (128 m-NCU eu-central-1'de saatte 4,647 USD, ayda yaklaşık 3.400 USD) ve bir standby aynı fiyatı ikinci kez öder.")],
        "aur": [sc(5, "Dört edge türü bir edges table'ında; WITH RECURSIVE en fazla üç seviye iner ve yolu bir dizide taşır. 5 puan kırıldı: değişken derinlik recursive bir sorgu, döngü kontrolü ve yol dizisi ister; bu bir pattern değil, elle yazılmış bir aramadır."),
                sc(4, "Her seviye bir index araması ve birleştirmedir. 6 puan kırıldı: bir alışveriş merkezi adresinde ara sonuç on binlerce row'a çıkar; 50 ms bütçesi her ödemede tutmaz."),
                sc(9, "INSERT edge row'ları ve INSERT … ON CONFLICT DO NOTHING ile cihaz. 1 puan kırıldı: her edge yönü için index güncellemesi ve MVCC row sürümleri yazmayı büyütür."),
                sc(10, "Transaction'lar ve snapshot okumalar; commit edilmiş edge görünür. Puan kırılmadı."),
                sc(2, "Okumalar reader'lara gider. 8 puan kırıldı: saniyede 2.400 recursive sorgu reader'ları yorar (3 puan) ve kampanya akşamı saniyede 7.200 edge yazması checkout'u yapan tek writer'dan checkout tepesiyle aynı anda geçer (Aurora sayfasının tek writer tablosu: 5.000–20.000, checkout ile aynı tepede 5 puan)."),
                sc(10, "Üç AZ'de altı kopya ve sürekli yedek. Puan kırılmadı."),
                sc(9, "Ekip SQL biliyor ve Aurora zaten çalışıyor. 1 puan kırıldı: kampanya akşamı için reader sayısı ve ACU aralığı ayarlanır; sorgunun yazılışı R1.1'de sayıldı."),
                sc(8, "Var olan cluster'a eklenir. 2 puan kırıldı: akşam için reader'lar ve ACU saat başına ödenir.")],
    },
    h2h={
        "npa": "Bellek içi graph analitiği (Neptune Analytics) ile kafa kafaya. İki servis aynı property graph modelini ve aynı openCypher pattern'ini kullanır; bu iş yükünde R1'leri eşittir (48,5'e 48,5). "
               "Neptune Analytics graph'ı bellekte tutar ve bütün graph algoritmalarında Neptune Database'ten çok güçlüdür, ama bu kartın sorusu bir algoritma değil, her ödemede bir vertex'ten başlayan kısa bir yoldur. "
               "Kararı servis tasarımı verir: Neptune Analytics tek bir instance'tır ve replica'ları okuma ölçeklemez (R2), graph'ın tamamının belleği gece gündüz ödenir (R5) ve kalıcılığı tek instance'a dayanır (R3). "
               "Hangi koşul değişseydi Neptune Analytics seçilirdi: soru her ödemede değil gece bir kez sorulsaydı, yani bütün graph üzerinde halkaları (community detection) bulup işaretlemek isteseydik; doğru mimari çoğunlukla ikisi birliktedir.",
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Aurora'da edge'ler bir table'dır ve WITH RECURSIVE üç seviyeye kadar arayabilir; transaction ve dayanıklılık güçlüdür ve ekip SQL bilir. "
               "Ama engine bu soruyu bir arama olarak çalıştırır: her seviye bir index araması ve birleştirmedir ve bir alışveriş merkezi adresinde ara sonuç on binlerce row'a çıkar (R1.2). "
               "Recursive sorgu, döngü kontrolü ve yol dizisi elle yazılır (R1.1) ve saniyede 2.400 kontrol reader'ları yorar; kampanya akşamının saniyede 7.200 edge yazması da checkout'un writer'ına gelir (R2'de 10 puanın 2'si). "
               "Hangi koşul değişseydi Aurora seçilirdi: kontrol yalnız tek hop olsaydı (\"bu kart işaretli bir hesapla aynı cihazı kullandı mı?\") ya da saniyede birkaç kontrol yapılsaydı ve bütçe 50 ms değil birkaç saniye olsaydı.",
    },
    verdict="Karar: Neptune {np}, Neptune Analytics {npa}, Aurora {aur}. Bu iş yüküne en uygun servis Neptune'dür. Engine uyumunda Neptune ile Neptune Analytics eşittir; kararı servis tasarımı verir: okuma ölçekleyen replica'lar, altı kopyalı volume ve sürekli trafiğe uyan fiyat. "
            "Neptune seçtiğimizde artımız: üç hop'luk kontrol tek bir sorgudur, yol inceleme için döner, yeni edge bir sonraki kontrolde görünür ve okumalar replica'larla büyür. "
            "Eksimiz: ortak adresler önceden işaretlenip sorgudan çıkarılır, replica gecikmesi kadar küçük bir pencere kabul edilir, tek writer'ın kampanya akşamındaki yazma hızı bir yük testiyle doğrulanır ve replica ile NCU ayarlanır. "
            "Doğru mimari ikisi birliktedir: ödeme anı Neptune'de, gece halka taraması Neptune Analytics'te (A9). Bir koşul değişseydi: kontrol gerçek zamanlı olmasaydı Neptune Analytics yeterdi."))

# ------------------------------------------------------------------ 3. recommendations by graph (Lale Market; close race with Aurora)
NEPTUNE_W.append(wusecase("reco", 3, sim="w_reco",
    title="Graph ile öneri: bunu alanlar şunları da aldı (Lale Market)",
    key="Vertex: Customer, Product. Edge: BOUGHT (müşteriden ürüne). Soru: bu ürünü alanların aldığı diğer ürünler; kişisel öneride bir hop daha.",
    story="Lale Market'in ürün sayfası \"Bunu alanlar şunları da aldı\" kutusunu, ana sayfa ise persona'ya göre kişisel öneriyi gösterir. Bugün bu iş Neptune'dedir ve küçük bir graph'tır; bu kart mağaza büyüdüğündeki hâlini puanlar: "
          "400.000 müşteri, 20.000 ürün ve 6 milyon BOUGHT edge'i. Ürün sayfası tepe anında saniyede 1.500, ana sayfa saniyede 300 kez açılır; kutu 80 ms içinde gelmelidir. "
          "En çok satan ürünlerin her biri 30.000'den fazla alıcıya sahiptir ve öneri tam da onlardan başlar. Yeni bir sipariş öneriyi hemen değiştirmelidir. "
          "Siparişlerin resmi kaydı Aurora'dadır; graph onların bir kopyasıdır. Ekip dört geliştiriciden oluşur ve SQL bilir; Aurora zaten çalışmaktadır.",
    wnote="R1 toplam 45: iki ve üç hop'luk soru (15) ve en çok satan ürünlerden geçen her istek (15) bu kartın riskidir. "
          "R2 20 ve R4 20 ile ikinci sıradadır: tepe anında saniyede 1.800 öneri ve Aurora'nın zaten çalışıyor olması. R3 5'tir: graph siparişlerin bir kopyasıdır.",
    rows=[
        row("EY", 15, "Her ürün sayfası ve her ana sayfa bu soruyu sorar.",
            "Ürün sayfası: \"bu ürünü alanların aldığı diğer ürünler, ortak alıcı sayısına göre, ilk 6\" (iki hop). Ana sayfa: \"benim aldıklarımı alanların aldıkları, benim almadıklarım\" (üç hop).",
            "Soru tek istekte cevaplanamazsa öneri her sayfa açılışında birkaç istek olur ve 80 ms bütçesi aşılır."),
        row("DA", 15, "Öneri en çok satan ürünlerden başlar; onların 30.000 alıcısı her istekte yoldadır.",
            "Bir isteğin maliyeti 6 milyon edge'e değil, başlangıç ürününün komşularına bağlı olmalı; en çok satan ürünler (supernode) bütçeyi aşmamalı.",
            "En çok satan ürünün sayfası en çok açılan sayfadır; orada yavaşlayan öneri en çok satışı kaçırır."),
        row("OY", 10, "Her sipariş satırı bir yazmadır ve öneriyi hemen değiştirmelidir.",
            "Her sipariş satırı müşteriden ürüne bir BOUGHT edge'i olarak eklenir; aynı ürün tekrar alınırsa ikinci bir edge yazılır.",
            "Yazma toplu ve gecikmeli olursa yeni siparişler öneriye ertesi gün girer."),
        row("VM", 5, "Veri iki tür vertex ve tek tür edge'tir; şekli basittir.",
            "Müşteriler, ürünler ve aralarındaki satın almalar; edge üzerinde sipariş id'si ve adet.",
            "İlişki bir dizi alana gömülürse her satın alma iki yerde tutulur."),
        row("R2", 20, "Tepe anında saniyede 1.800 öneri checkout tepesiyle aynı akşamdır.",
            "Tepe anında saniyede 1.500 ürün sayfası ve 300 ana sayfa önerisi, her biri 80 ms içinde.",
            "Öneri yavaşlarsa sayfa beklemez ve kutuyu boş gösterir; kampanya akşamı en değerli kutu boş kalır."),
        row("R3", 5, "Graph siparişlerin bir kopyasıdır; kaybı yeniden yüklemedir.",
            "Düşük: graph Aurora'daki siparişlerden yeniden kurulabilir.",
            "Kopya kaybolursa birkaç saat genel bir liste gösterilir."),
        row("R4", 20, "Ekip dört kişidir ve Aurora zaten çalışır; ikinci bir database bu ekip için büyük bir iştir.",
            "Dört geliştirici SQL biliyor; Aurora siparişleri zaten tutuyor. İkinci bir database ve bir kopyalama hattı ancak gerekiyorsa kurulmalı.",
            "Kopyalama hattı bozulursa öneri sessizce eskir ve kimse fark etmez."),
        row("R5", 10, "Öneri bir satış aracıdır; maliyeti satıştan küçük olmalı.",
            "Tepe akşamdadır; gündüz ve gece trafik üçte birdir.",
            "İkinci bir database'in saat başı faturası öneri kutusunun getirisini aşabilir."),
    ],
    cands=["np", "aur", "ddb"],
    scores={
        "np": [sc(10, "Ürün sayfası iki hop'luk, ana sayfa üç hop'luk tek bir openCypher pattern'idir (Ö4); Lale Market'in canlı sorguları budur (B2). Puan kırılmadı."),
               sc(8, "Traversal başlangıç ürününden başlar ve yalnız komşuları okur (Ö3). 2 puan kırıldı: en çok satan ürünler supernode'dur ve öneri tam onlardan başladığı için dışarıda bırakılamaz; sorgu alıcıları örneklemeli ya da hop başına bir LIMIT koymalıdır (A4). Workshop'un canlı ölçümü (B2: en düşük kapasitede, ağ ve imza dahil 205 ms) 80 ms'yi kanıtlamaz; bütçe sınırlı sorguyla bir yük testinde doğrulanır."),
               sc(10, "Her sipariş satırı bir CREATE ile BOUGHT edge'idir ve bir sonraki öneri onu hemen sayar (Ö6); canlı mağaza bunu yapar. Puan kırılmadı."),
               sc(10, "Customer ve Product vertex'leri, BOUGHT edge'i üzerinde order_id ve qty (Ö1). Puan kırılmadı."),
               sc(9, "Okumalar replica'lara dağılır ve Serverless instance'ları yükle büyür; yazma hacmi küçüktür. 1 puan kırıldı: bütün yazmalar tek writer'dan geçer ve replica'lar writer'ın birkaç milisaniye gerisindedir; yeni sipariş replica'dan okunan bir öneride o kadar geç görünür."),
               sc(10, "Altı kopyalı cluster volume. Puan kırılmadı."),
               sc(5, "Yönetilen cluster. 5 puan kırıldı: ekip openCypher öğrenir (2), siparişleri Aurora'dan Neptune'e taşıyan kopyalama hattını kurar ve izler (2) ve replica ile NCU aralığını akşam tepesine göre ayarlar (1)."),
               sc(6, "NCU-saat başına ödenir. 4 puan kırıldı: Aurora'nın yanında ikinci bir database'in en az iki instance'ı gece gündüz ödenir (en düşük kapasitede ayda yaklaşık 283 USD), trafik ise akşamdadır.")],
        "aur": [sc(7, "Ürün sayfası iki self-join ve GROUP BY ile tek SQL sorgusudur; siparişler zaten oradadır. 3 puan kırıldı: üç hop'luk kişisel öneri üç self-join ve NOT EXISTS ister; her hop table'ın bir kopyası daha demektir."),
                sc(6, "(product_id) ve (customer_id) index'leri ile her hop bir index aramasıdır. 4 puan kırıldı: en çok satan bir ürünün 30.000 alıcısı ve onların satırları her istekte birleştirilip gruplanır; ara sonuç 80 ms bütçesini zorlar."),
                sc(10, "Siparişler checkout tarafından zaten yazılıyor; öneri için ayrıca yazma yoktur ve yeni sipariş hemen görünür. Puan kırılmadı."),
                sc(9, "order_items table'ı satın almaları taşır. 1 puan kırıldı: ilişki row'lardaki iki id'dir; graph'ın kendisi değil, onun bir tablosudur."),
                sc(7, "Öneri sorguları reader'lara gider. 3 puan kırıldı: tepe anında saniyede 1.800 birleştirme ve gruplama sorgusu reader'ları yorar; checkout ile aynı akşamdır."),
                sc(10, "Kaynak zaten burada. Puan kırılmadı."),
                sc(9, "Yeni sistem ve kopyalama hattı yok; ekip SQL biliyor. 1 puan kırıldı: akşam tepesi için reader sayısı ve ACU aralığı ayarlanır."),
                sc(8, "Var olan cluster'a reader eklenir. 2 puan kırıldı: akşam için reader'lar ve ACU saat başına ödenir.")],
        "ddb": [sc(2, "Adjacency list: ürünün alıcıları bir Query, her alıcının ürünleri birer Query. 8 puan kırıldı: en çok satan ürün için 30.000 Query gerekir; sayma, sıralama ve eleme uygulamadadır ve üç hop'luk öneri pratikte yapılamaz."),
                sc(6, "Her Query bir partition'a gider. 4 puan kırıldı: en çok satan ürünün alıcıları tek büyük bir item collection'dır ve onu okuyan istekler aynı partition'a yığılır (hot partition)."),
                sc(9, "Her sipariş satırı bir item'dır. 1 puan kırıldı: iki yönde okumak için iki item (ya da ters yön için bir GSI) yazılır."),
                sc(6, "Satın alma bir item'dır. 4 puan kırıldı: graph partition key ve sort key çiftlerine düzleştirilir; ilişki iki yönde tekrarlanır."),
                sc(10, "On-demand mod tepeyi ayarsız karşılar. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(6, "Serverless. 4 puan kırıldı: ekip DynamoDB API'ını öğrenir (2) ve siparişleri Aurora'dan kopyalayan hattı kurar (2)."),
                sc(9, "İstek başına ödenir. 1 puan kırıldı: tepe saatin birim tüketimi önceden hesaplanmalıdır.")],
    },
    h2h={
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Bu kartın en yakın yarışıdır. Aurora'nın güçlü yanı R4'tedir: siparişler zaten oradadır, kopyalama hattı yoktur, yeni sipariş öneride hemen görünür ve ekip SQL bilir. "
               "Neptune'ü öne geçiren R1'dir: iki ve üç hop'luk öneri bir pattern'dir ve maliyeti başlangıç ürününün komşularına bağlıdır; Aurora'da her hop bir self-join'dir ve en çok satan ürünlerde ara sonuç 30.000 alıcı ve onların satırlarına büyür (R1.1, R1.2). R1'de Neptune 8 puan önde, R4'te Aurora 8 puan öndedir; R2 Neptune'e 4 puan kazandırır, R5 Aurora'ya 2 puan geri verir ve net fark 2 puandır. "
               "Hangi koşul değişseydi Aurora seçilirdi: kişisel üç hop'luk öneri istenmeseydi ve ürün sayfası önerisi her gece toplu hesaplanıp bir table'a yazılsaydı; bugünkü küçük Lale Market'te (11.887 edge) de Aurora yeterli olurdu.",
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB ölçekte ve işletimde güçlüdür ve tepe trafiği ayarsız karşılar (R2). Ama bu iş yükü bir key ile okuma değil, bir yolun hesaplanmasıdır: en çok satan bir ürünün önerisi 30.000 alıcının ürünlerini okumayı ister ve DynamoDB'de bu 30.000 ayrı Query'dir (R1.1). "
               "Aynı alıcılar tek bir büyük item collection'da durur ve hot partition olur (R1.2); siparişler de Aurora'dan kopyalanmalıdır (R4). "
               "Hangi koşul değişseydi DynamoDB seçilirdi: öneri listeleri gece başka bir sistemde hesaplanıp ürün başına bir value olarak saklansaydı; o zaman soru bir GetItem olurdu (DynamoDB sayfasındaki öneri kartı ve ElastiCache sayfasının kart 9'u bu iş yüküdür).",
    },
    verdict="Karar: Neptune {np}, Aurora {aur}, DynamoDB {ddb}. Bu iş yüküne en uygun servis Neptune'dür, ama fark yakın bir yarıştır. Engine uyumunu Neptune açıkça kazanır; Aurora işletimde öndedir, çünkü siparişler zaten oradadır. "
            "Neptune seçtiğimizde artımız: iki ve üç hop'luk öneri tek bir sorgudur, yeni sipariş öneride hemen görünür ve okumalar replica'larla büyür. "
            "Eksimiz: siparişleri Aurora'dan Neptune'e taşıyan bir kopyalama hattı (seed ve sipariş başına yazma) kurulur ve izlenir, en çok satan ürünler için sorgu alıcıları sınırlar ve ikinci bir database ödenir. "
            "Doğru mimari ikisi birliktedir: kayıt Aurora'da, öneri Neptune'de; çok sık açılan sayfalarda hesaplanmış liste bir cache'te. Bir koşul değişseydi: kişisel üç hop'luk öneri istenmeseydi Aurora kazanırdı."))

# ------------------------------------------------------------------ 4. product knowledge graph for an assistant (GraphRAG): Neptune Analytics wins, Neptune third
NEPTUNE_W.append(wusecase("knowledge", 4,
    title="Ürün bilgi graph'ı ve alışveriş asistanı (GraphRAG)",
    key="Vertex: Product, Brand, Category, Feature, Chunk. Edge: COMPATIBLE_WITH, PART_OF, HAS_FEATURE, DESCRIBES. Soru: bu soruya anlamca en yakın metin parçaları ve onlardan bir-iki hop uzaktaki ürünler.",
    story="Lale Market bir alışveriş asistanı kuruyor: müşteri \"bu kulaklığa uyan bir şarj aleti\" diye yazar. Asistan sorunun embedding'ine anlamca en yakın 10 metin parçasını bulur, sonra onlardan iki hop uzaktaki ürünlere (uyumlu aksesuar, aynı marka, aynı kategori) gider ve bu bağlamı bir dil modeline verir. "
          "Graph'ta 20.000 ürün, 2 milyon ilişki ve embedding'li 500.000 metin parçası var. Saniyede 30 soru gelir ve getirme adımı 300 ms içinde bitmelidir. "
          "Graph her hafta katalogdan (S3'teki dışa aktarım) yeniden kurulur, gün içinde küçük güncellemeler olur. Ekip üç veri bilimcidir, Python ve notebook kullanır ve tek bir sistem ister. Graph kaybolursa S3'ten yeniden yüklenir.",
    wnote="R1 toplam 50: vector benzerliği ile hop'un aynı sorguda olması (15), bunun bellek hızında çalışması (15), graph ile embedding'in tek modelde durması (10) ve engine'in araçları (10). "
          "R4 20 ile ikinci: üç kişilik ekip tek bir sistem istiyor. R5 15'tir, çünkü asistan yeni bir denemedir; R3 5'tir, çünkü graph S3'ten yeniden kurulur.",
    rows=[
        row("EY", 15, "Her soru bu iki adımı birlikte ister: anlamca yakın parçalar ve onlardan ürünlere yol.",
            "Önce embedding'e en yakın 10 metin parçası (vector benzerliği), sonra her parçadan iki hop'a kadar ürünler; ikisi tek bir sorguda.",
            "İki adım iki sistemde olursa her soru iki ağ isteği ve uygulamada bir birleştirme olur; 300 ms bütçesi zorlanır."),
        row("DA", 15, "Getirme adımı 300 ms içinde bitmeli; dil modeli ondan sonra çalışır.",
            "Vector araması ve hop'lar bellek hızında çalışmalı; 500.000 embedding bir yaklaşık en yakın komşu index'inde durmalı.",
            "Getirme yavaşlarsa asistan geç cevap verir ve müşteri sayfayı kapatır."),
        row("VM", 10, "Veri hem ilişki hem embedding'dir; ikisi ayrı yerlerde tutulursa senkron kalmaz.",
            "Ürünler, markalar, özellikler ve metin parçaları vertex; ilişkiler edge; her parçanın bir embedding'i (1.024 sayı) var.",
            "Embedding'ler başka bir sistemde dururken ürün silinirse asistan var olmayan bir ürünü önerir."),
        row("AO", 10, "Ekip en yakın komşu araması, benzerlik ve bağlam için hazır araçlar istiyor.",
            "Hazır vector index'i, benzerlik ve topluluk algoritmaları; notebook'tan çağrılabilen araçlar.",
            "Her aracı ekip kendisi yazarsa üç kişilik ekip asistanı değil altyapıyı geliştirir."),
        row("R2", 10, "Saniyede 30 soru küçük ve düzenli bir yüktür.",
            "Saniyede 30 soru; kampanya günü iki katı.",
            "Yük küçük olduğu için ölçek bu kartı belirlemez, ama getirme her soruda bütçede kalmalıdır."),
        row("R3", 5, "Graph S3'teki dışa aktarımdan yeniden kurulur; kaybı birkaç saatlik yeniden yüklemedir.",
            "Düşük: graph haftalık dışa aktarımdan yeniden kurulabilir.",
            "Kayıp asistanı birkaç saat kapatır, veri kaybı değildir."),
        row("R4", 20, "Üç veri bilimci tek bir sistem istiyor; ikinci bir sistem bu ekip için en büyük risktir.",
            "Üç veri bilimci Python ve notebook kullanır; graph ve vector için tek bir yönetilen sistem istenir, sunucu boyutlandırılmaz.",
            "İki sistemi senkron tutmak (graph ve ayrı bir vector store) küçük ekibin bütün zamanını alır."),
        row("R5", 15, "Asistan yeni bir denemedir; sabit bir fatura denemeyi durdurabilir.",
            "Deneme döneminde maliyet düşük olmalı; kullanılmadığında kapatılabilmeli.",
            "Büyük bir sabit fatura denemeyi bitmeden durdurur."),
    ],
    cands=["npa", "os", "np"],
    scores={
        "npa": [sc(10, "openCypher'da vector araması (topK) ve iki hop'luk pattern aynı sorgudadır (Ö4, Ö8). Puan kırılmadı."),
                sc(10, "Graph ve HNSW vector index'i bellekte durur; arama ve hop'lar bellek hızındadır. Puan kırılmadı."),
                sc(10, "Embedding vertex'in kendisine bağlıdır; graph ve vector tek modeldedir. Puan kırılmadı."),
                sc(9, "Vector index'i, benzerlik ve topluluk algoritmaları openCypher prosedürleridir (Ö8). 1 puan kırıldı: AWS'e göre graph başına tek bir vector index vardır; ikinci bir embedding türü ayrı bir graph ister."),
                sc(9, "Saniyede 30 soru bir graph instance'ı için küçüktür. 1 puan kırıldı: kapasite yalnız bir yönetim işlemiyle büyür; kampanya günü önceden büyütülür."),
                sc(10, "Graph S3'ten yeniden yüklenir ve durdurup başlatmada korunur; istenen bu kadardır. Puan kırılmadı."),
                sc(7, "Tek sistem, notebook desteği ve S3'ten yükleme. 3 puan kırıldı: ekip openCypher öğrenir (2) ve m-NCU boyutu graph'ın büyüklüğüne göre seçilir (1)."),
                sc(7, "m-NCU-saat başına ödenir. 3 puan kırıldı: graph açıkken saat başına ödenir (32 m-NCU eu-central-1'de saatte 1,162 USD, ayda yaklaşık 850 USD); durdurulan graph fiyatın onda birini öder.")],
        "os": [sc(6, "k-NN araması en yakın parçaları verir. 4 puan kırıldı: ilişkiler document'larda id dizileridir; iki hop için ikinci ve üçüncü bir sorgu gönderilir ve uygulama birleştirir."),
               sc(10, "HNSW index'i ve filtreler hızlıdır. Puan kırılmadı: hop'ların ayrı sorgular olması R1.1'de sayıldı."),
               sc(6, "Ürünler ve parçalar document'tır, embedding bir alandır. 4 puan kırıldı: ilişki bir graph değil, document'lara gömülmüş id listeleridir ve iki yönde tekrarlanır."),
               sc(10, "k-NN, metin ve vector'ü birlikte kullanan hibrit arama, filtreler. Puan kırılmadı: arama araçlarında en güçlü aday budur."),
               sc(10, "Saniyede 30 soru küçük bir yüktür. Puan kırılmadı."),
               sc(10, "Index S3'ten yeniden kurulur. Puan kırılmadı."),
               sc(6, "Yönetilen domain ya da serverless collection. 4 puan kırıldı: mapping, shard ve kapasite ekip için yeni işlerdir ve ilişkileri document'lara yazan bir hat gerekir."),
               sc(7, "Saat başına ödenir. 3 puan kırıldı: en düşük kapasite deneme döneminde de ödenir.")],
        "np": [sc(5, "İki hop'luk ürün yolu bir pattern'dir (Ö4). 5 puan kırıldı: Neptune Database'de vector araması yoktur; ilk adım başka bir sistemde (OpenSearch) yapılır ve id'ler Neptune'e ikinci istekle gönderilir."),
               sc(10, "Hop'lar komşuları okur (Ö3) ve küçük graph buffer cache'e sığar. Puan kırılmadı: vector adımının başka bir sistemde olması R1.1'de sayıldı."),
               sc(10, "Ürünler ve ilişkiler doğrudan vertex ve edge'tir (Ö1). Puan kırılmadı: embedding'in Neptune Database'te saklanıp aranamaması R1.1'de sayıldı."),
               sc(7, "Index'ler (SPOG, POGS, GPSO) ve Streams var (Ö2, Ö7). 3 puan kırıldı: benzerlik ve topluluk algoritmaları Neptune Database'te yoktur ve metin araması OpenSearch entegrasyonuyla yapılır; vector eksikliği R1.1'de sayıldı."),
               sc(10, "Saniyede 30 soru küçüktür. Puan kırılmadı."),
               sc(10, "Altı kopyalı cluster volume. Puan kırılmadı."),
               sc(5, "Yönetilen cluster. 5 puan kırıldı: graph için Neptune, vector için OpenSearch; iki sistem ve aralarında bir hat (2), ekip openCypher öğrenir (2) ve NCU aralığını ayarlar (1)."),
               sc(6, "NCU-saat başına ödenir. 4 puan kırıldı: kapasite sıfıra inmez; deneme döneminde de en az iki instance'ın en düşük NCU'su ödenir (ayda yaklaşık 283 USD); Neptune Analytics ise fiyatın onda birine durdurulabilir. İkinci sistemin işletimi R4'te sayıldı.")],
    },
    h2h={
        "os": "Search engine (OpenSearch) ile kafa kafaya. OpenSearch'ün vector araması güçlüdür ve metinle vector'ü birlikte kullanan hibrit arama onun işidir (R1.4'te tam puan). "
              "Ama bu iş yükünün ikinci adımı bir yoldur: bir parçadan uyumlu aksesuara, oradan markaya. OpenSearch'te ilişkiler document'lara gömülmüş id listeleridir; her hop ikinci bir sorgu ve uygulamada bir birleştirmedir (R1.1, R1.3). "
              "Üç kişilik ekip için yeni bir sistem ve ilişkileri document'lara yazan bir hat R4'te de puan kaybettirir. "
              "Hangi koşul değişseydi OpenSearch seçilirdi: asistan yalnız benzer metin parçalarını getirseydi ve ürünler arası ilişkiler cevaba girmeseydi, ya da metin araması (yazım hatası, relevance) vector kadar önemli olsaydı.",
        "np": "Graph (Neptune) ile kafa kafaya. Bu sayfanın servisi bu kartta üçüncüdür ve nedeni açıktır: Neptune Database'te vector araması yoktur. İki hop'luk ürün yolu Neptune'de de bir pattern'dir, ama sorunun ilk adımı (anlamca en yakın parçalar) başka bir sistemde yapılır (R1.1, R1.4). "
              "Neptune Analytics aynı property graph'ı ve openCypher'ı kullanır, ama graph'ı bellekte tutar, vector index'i ve algoritmaları engine'inde taşır; bu kart tam olarak onun için tasarlanmıştır. "
              "Neptune Database'in güçlü yanları (replica'larla okuma ölçeği, altı kopyalı volume) bu kartta ağırlığı düşük satırlardadır. "
              "Hangi koşul değişseydi Neptune seçilirdi: asistan yalnız ilişkileri sorsaydı (\"bu kulaklığa uyan aksesuarlar\") ve saniyede binlerce soruyla okuma ölçeği gerekseydi.",
    },
    verdict="Karar: Neptune Analytics {npa}, OpenSearch {os}, Neptune {np}. Bu iş yüküne en uygun servis Neptune Analytics'tir: vector araması ve hop'lar aynı engine'de, aynı sorguda ve bellekte çalışır. Kararı R1 verir. "
            "Yine de Neptune seçersek artımız: okuma replica'larla büyür, veri altı kopyalı volume'dadır ve ürün ilişkileri için güçlü bir kayıt sistemi olur. "
            "Eksimiz: vector araması için ayrı bir sistem (OpenSearch) ve aralarında bir hat gerekir; uygulama iki isteği birleştirir. "
            "Doğru mimari çoğunlukla ikisi birliktedir: ürün ilişkilerinin kaydı katalogda (ya da Neptune Database'te), asistanın getirme graph'ı Neptune Analytics'te. Bir koşul değişseydi: vector adımı istenmeseydi Neptune Database öne geçerdi."))

# ------------------------------------------------------------------ 5. identity graph (Neptune Analytics wins R1, Neptune wins the total)
NEPTUNE_W.append(wusecase("identity", 5,
    title="Identity graph: bir kişinin bütün identifier'ları",
    key="Vertex: Cookie, Device, Email, Phone, LoyaltyCard. Edge: SEEN_WITH (aynı oturumda görüldü). Soru: bu cookie'ye bağlı bütün identifier'lar (en fazla 6 hop).",
    story="Lale Market'in pazarlama ekibi aynı kişinin cookie'lerini, cihazlarını, e-postalarını, telefon özetlerini ve sadakat kartını tek bir kişi olarak görmek istiyor. "
          "Graph'ta 50 milyon identifier ve 200 milyon bağlantı var. Her login ya da checkout iki identifier'ı aynı oturumda görür ve bir bağlantı yazar: saniyede 2.000 olay. "
          "Kişiselleştirme servisi her sayfa açılışında \"bu cookie'ye bağlı bütün identifier'lar\" sorusunu sorar: saniyede 1.000 istek, 50 ms bütçe, en fazla 6 hop. "
          "Bazı identifier'lar milyonlarca kişiyle paylaşılır (bir mağaza tableti, test@ adresi) ve önceden bilinmez. Aynı identifier iki olayda aynı anda ilk kez görülebilir. Ekip beş kişidir; bir kişinin silinme talebi (KVKK) bütün identifier'larını silmelidir.",
    wnote="R1 toplam 50: değişken derinlikli soru (15), saniyede 2.000 olayın \"yoksa oluştur\" yazması (15), paylaşılan identifier'larla çalışma (10) ve aynı anda gelen iki olay (10). "
          "R2 20 ile ikinci: saniyede 1.000 okuma ve 2.000 yazma birlikte. R3, R4 ve R5 10'ar.",
    rows=[
        row("EY", 15, "Her sayfa açılışı bu soruyu sorar; derinlik önceden bilinmez.",
            "\"Bu cookie'ye en fazla 6 hop'ta bağlı bütün identifier'lar.\" Derinlik kişiden kişiye değişir; cevap bir küme ve kişinin kimliğidir.",
            "Soru her hop için ayrı istek olursa 6 hop 50 ms'ye sığmaz ve kişiselleştirme varsayılan sayfaya düşer."),
        row("OY", 15, "Saniyede 2.000 olayın her biri \"yoksa oluştur, sonra bağla\" yazmasıdır.",
            "Her olay iki identifier'ı yoksa oluşturur ve aralarına bir bağlantı yazar; aynı bağlantı iki kez yazılmamalı. Silme talebi bir kişinin bütün identifier'larını ve bağlantılarını siler.",
            "Aynı identifier iki kez oluşturulursa kişi iki parçaya bölünür; silme eksik kalırsa yasal bir yükümlülük ihlal edilir."),
        row("DA", 10, "Paylaşılan identifier'lar önceden bilinmez; bir istek onlara rastlarsa milyonlarca vertex'e yayılır.",
            "Paylaşılan identifier'lar (supernode) aramayı bütün graph'a yaymamalı; arama bir derecenin üstündeki vertex'te durmalı.",
            "Bir istek mağaza tabletinden geçerse milyonlarca identifier'ı okur, bütçeyi aşar ve yanlış kişileri birleştirir."),
        row("TA", 10, "Aynı identifier iki olayda aynı anda ilk kez görülebilir; kural yarışta da korunmalı.",
            "İki olay aynı identifier'ı aynı anda oluşturmak isterse tek bir vertex oluşmalı.",
            "İki vertex oluşursa kişi iki parçaya bölünür ve kişiselleştirme yarım kalır."),
        row("R2", 20, "Saniyede 1.000 okuma ve 2.000 yazma aynı graph'a gelir.",
            "Saniyede 1.000 okuma, 50 ms içinde; saniyede 2.000 olay ve her biri iki-üç yazma.",
            "Okuma yavaşlarsa sayfa varsayılan içeriğe düşer; yazma birikirse yeni bağlantılar saatler sonra görünür."),
        row("R3", 10, "Bağlantılar aylar içinde birikir; kaybı yeniden kurulamaz.",
            "Onaylanan bağlantılar kaybolmamalı.",
            "Kaybolan bağlantılar olayların kendisi tekrar gelmedikçe geri gelmez."),
        row("R4", 10, "Beş kişilik ekip sunucu işletmek istemiyor.",
            "Beş geliştirici; sunucu ve failover işi istenmiyor. Ekip AWS SDK'yı biliyor, graph dili bilmiyor.",
            "İşletme işi ekibin kişiselleştirme kurallarına ayıracağı zamanı yer."),
        row("R5", 10, "Trafik gün boyu süreklidir.",
            "Gün boyu sürekli trafik; graph 200 milyon edge'tir.",
            "Graph'ın tamamı için bellek gece gündüz ödenirse fatura büyür."),
    ],
    cands=["np", "ddb", "npa"],
    scores={
        "np": [sc(10, "MATCH (c:Cookie {`~id`: $id})-[:SEEN_WITH*1..6]-(x) RETURN DISTINCT x; değişken uzunlukta path (Ö5). Puan kırılmadı."),
               sc(10, "MERGE identifier'ı yoksa oluşturur, ikinci bir MERGE bağlantıyı yoksa yazar; silme talebi DETACH DELETE ile kişinin bütün vertex ve edge'lerini siler (Ö6). Puan kırılmadı."),
               sc(7, "Traversal komşuları okur (Ö3). 3 puan kırıldı: paylaşılan identifier'lar önceden bilinmez; sorgu edge sayısı bir sınırı aşan vertex'te durmalı ve bu sayı ayrı bir property olarak tutulmalı (2, her önceden bilinmeyen supernode'da olduğu gibi); 6 hop'ta buffer cache'te olmayan sayfalar diskten okunur ve 50 ms bütçesini zorlar (1)."),
               sc(9, "Mutation'lar range lock alır; aynı ~id için iki MERGE tek vertex oluşturur (Ö6). 1 puan kırıldı: yarışan iki yazmadan biri çakışma hatası alabilir ve uygulama yeniden dener."),
               sc(8, "Okumalar replica'lara dağılır. 2 puan kırıldı: saniyede 2.000 olayın 4.000-6.000 yazması (range lock alan MERGE'ler) tek writer'dan geçer; AWS tek bir writer için bir yazma sayısı vermez, bu hız bir yük testiyle doğrulanmalıdır. Replica'lar writer'ın birkaç milisaniye gerisindedir."),
               sc(10, "Altı kopyalı cluster volume. Puan kırılmadı."),
               sc(7, "Yönetilen cluster. 3 puan kırıldı: ekip openCypher öğrenir (2) ve NCU ile replica aralığını ayarlar (1)."),
               sc(8, "NCU-saat başına ödenir; sürekli trafiğe uyar. 2 puan kırıldı: replica'lar ve tepe NCU'su saat başına ödenir.")],
        "ddb": [sc(3, "Adjacency list ile her identifier'ın komşuları bir Query'dir. 7 puan kırıldı: 6 hop'luk arama uygulamanın yazdığı bir breadth-first search'tür; her seviye onlarca Query ve 50 ms bütçesi tutmaz."),
                sc(9, "Koşullu PutItem (attribute_not_exists) identifier'ı yoksa yazar; silme için kişinin item'ları okunup tek tek silinir. 1 puan kırıldı: her bağlantı iki yönde iki item'dır."),
                sc(6, "Her Query bir partition'a gider. 4 puan kırıldı: paylaşılan identifier'ın milyonlarca bağlantısı tek bir item collection'dır ve hot partition olur."),
                sc(10, "Koşullu yazma (attribute_not_exists) yarışta tek item bırakır. Puan kırılmadı: iki yönlü bağlantının iki item olması R1.2'de sayıldı."),
                sc(10, "On-demand mod okuma ve yazmayı ayarsız karşılar. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(10, "Serverless ve ekip SDK'yı biliyor. Puan kırılmadı: arama kodu R1.1'de sayıldı."),
                sc(9, "İstek başına ödenir. 1 puan kırıldı: tepe saatin birim tüketimi hesaplanmalıdır.")],
        "npa": [sc(10, "Aynı değişken uzunlukta pattern; ayrıca bağlı bileşenler (WCC) bir algoritma olarak hazırdır (Ö5, Ö8). Puan kırılmadı."),
                sc(10, "openCypher MERGE ve DETACH DELETE çalışır; AWS'e göre MERGE eşzamanlı yazmalarda tek vertex bırakır. Puan kırılmadı."),
                sc(8, "Graph bellekte durur ve 6 hop'luk arama disk okumaz. 2 puan kırıldı: paylaşılan identifier'lar önceden bilinmez; arama burada da bir derece sınırında durmalıdır."),
                sc(9, "Okumalar snapshot isolation ile çalışır. 1 puan kırıldı: mutation okumaları da snapshot üzerindedir; yarışan iki yazmadan biri çakışma hatası alabilir ve yeniden dener."),
                sc(5, "Tek bir bellek odaklı instance. 5 puan kırıldı: AWS'e göre replica'lar pasif failover hedefidir ve okuma ölçeklemez; saniyede 1.000 okuma ve 2.000 olay tek instance'ın işidir."),
                sc(8, "Graph verisi korunur ve hot standby başka bir AZ'dedir. 2 puan kırıldı: kalıcılık tek instance'a ve snapshot'lara dayanır."),
                sc(7, "Sunucusuz graph. 3 puan kırıldı: ekip openCypher öğrenir (2) ve m-NCU boyutu seçilir (1); büyütmenin bir yönetim işlemi olması R2'de sayıldı."),
                sc(5, "m-NCU-saat başına ödenir. 5 puan kırıldı: 200 milyon edge'in belleği gece gündüz ödenir ve standby aynı fiyatı ikinci kez öder.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB işletimde ve ölçekte en güçlü adaydır: saniyede 2.000 olay ve 1.000 okuma on-demand modda ayarsız çalışır, ekip SDK'yı bilir ve koşullu yazma \"yoksa oluştur\" kuralını tek istekte korur (R2, R4). "
               "Ama soru bir yoldur: 6 hop'luk arama DynamoDB'de uygulamanın yazdığı bir breadth-first search'tür ve her seviye onlarca Query'dir (R1.1); paylaşılan identifier'lar hot partition olur (R1.3). "
               "Hangi koşul değişseydi DynamoDB seçilirdi: kişiler gece bir algoritmayla (bağlı bileşenler) hesaplansaydı ve gündüz soru yalnız \"bu cookie hangi kişiye ait?\" olsaydı; o zaman soru bir GetItem'dır ve doğru mimari Neptune ya da Neptune Analytics ile DynamoDB birliktedir.",
        "npa": "Bellek içi graph analitiği (Neptune Analytics) ile kafa kafaya. Bu kartta engine uyumunu Neptune Analytics kazanır ve bunu söylemek gerekir: graph bellekte durur, 6 hop'luk arama disk okumaz ve bağlı bileşenler hazır bir algoritmadır (R1'de 47'ye 46). "
               "Ama toplamı servis tasarımı çevirir: Neptune Analytics tek bir instance'tır, replica'ları okuma ölçeklemez ve saniyede 1.000 okuma ile 2.000 olay o tek instance'a biner (R2); 200 milyon edge'in belleği gece gündüz ödenir (R5). "
               "Hangi koşul değişseydi Neptune Analytics seçilirdi: kişiler gerçek zamanlı değil gece toplu hesaplansaydı; o zaman WCC algoritması bütün graph'ı bir kerede böler ve sonuç DynamoDB'ye yazılır.",
    },
    verdict="Karar: Neptune {np}, DynamoDB {ddb}, Neptune Analytics {npa}. Bu iş yüküne en uygun servis Neptune'dür. Engine uyumunda Neptune Analytics bir puan öndedir; Neptune'ü öne geçiren R2 ve R5'tir: okumalar replica'larla büyür ve 200 milyon edge'in belleği gece gündüz ödenmez; R3'te altı kopyalı volume da yardım eder. "
            "Neptune seçtiğimizde artımız: değişken derinlikli arama tek bir sorgudur, MERGE yarışta tek identifier bırakır ve silme talebi tek bir DETACH DELETE'tir. "
            "Eksimiz: paylaşılan identifier'lar için bir derece sınırı tutulur ve sorgu orada durur, çakışan yazmalar yeniden denenir, ekip openCypher öğrenir. "
            "Bir koşul değişseydi: kişiler gece toplu hesaplansaydı doğru mimari Neptune Analytics (hesap) ile DynamoDB (gündüz okuma) birlikte olurdu."))

# ------------------------------------------------------------------ 6. network topology and impact analysis (Neptune wins R1, Aurora wins the total)
NEPTUNE_W.append(wusecase("network", 6, sim="w_network",
    title="Ağ topolojisi: bu switch düşerse ne düşer?",
    key="Vertex: Switch, Server, Service, Endpoint. Edge: CONNECTED_TO, RUNS_ON, DEPENDS_ON. Soru: bir parçadan, herhangi bir derinlikte, ona bağlı bütün müşteri servisleri.",
    story="Lale Market'in platform ekibi 3.000 sunucu, 400 servis ve 120 switch'ten oluşan bir altyapı işletir; aralarında 15.000 bağımlılık var. Nöbetçi mühendis bir arızada şunu sorar: \"bu switch düşerse hangi müşteri servisleri düşer?\" "
          "Cevap 1 ile 8 hop arasındadır ve yol da gösterilmelidir. Soru günde yaklaşık 200 kez sorulur, bir arıza sırasında dakikada birkaç kez; birkaç saniyelik bir cevap yeterlidir. "
          "Envanter (CMDB) bugün Aurora PostgreSQL'de üç table'dır ve her gece Terraform hattı tarafından güncellenir. Veri 50 MB'tır. Ekip iki SRE'den oluşur ve SQL bilir; bütçe sıkıdır ve yeni bir sistem istemezler.",
    wnote="R1 toplam 45: değişken derinlikli bağımlılık sorusu (20) bu kartın kendisidir. R4 20 ve R5 20 ile ikinci sıradadır: iki SRE'lik ekip yeni bir sistem istemiyor ve trafik o kadar küçüktür ki her sabit fatura belirleyicidir. "
          "R2 5'te, en düşük sınırdadır: günde 200 soru. R1 grup olarak yine en ağırdır.",
    rows=[
        row("EY", 20, "Arıza anında sorulan tek soru budur ve derinliği önceden bilinmez.",
            "\"Bu switch'e herhangi bir derinlikte (1-8 hop) bağımlı bütün müşteri servisleri, yollarıyla.\" Bağımlılıklarda döngü olabilir.",
            "Soru yanlış ya da eksik cevaplanırsa nöbetçi etkilenen bir servisi atlar ve müşteriye duyuru geç yapılır."),
        row("DA", 10, "Cevap birkaç saniyede yeterlidir ve graph küçüktür.",
            "Sorgu birkaç saniye içinde dönmeli; graph 50 MB'tır ve tamamı belleğe sığar.",
            "Arıza anında dakikalar süren bir sorgu kararı geciktirir."),
        row("VM", 10, "Birçok tür parça ve birçok tür bağlantı aynı soruda geçer.",
            "Dört tür parça ve üç tür bağlantı; yeni türler (yük dengeleyici, kuyruk) ekleneceği bilinir.",
            "Her yeni tür bir şema değişikliği olursa envanter gerçeğin gerisinde kalır."),
        row("OY", 5, "Envanter her gece toplu güncellenir; gün içinde az değişiklik olur.",
            "Her gece Terraform hattı envanterin farkını yazar; gün içinde birkaç elle değişiklik.",
            "Gece güncellemesi yarım kalırsa sabah yanlış bir topoloji sorgulanır."),
        row("R2", 5, "Günde 200 soru; ölçek bu kartı belirlemez.",
            "Günde yaklaşık 200 soru, arızada dakikada birkaç.",
            "Bu yük her aday için küçüktür; bir arızada da artmaz."),
        row("R3", 10, "Envanter bir arıza anında en çok gereken veridir.",
            "Envanter kaybolmamalı; bir arıza sırasında da okunabilmeli.",
            "Envanter arıza anında okunamazsa nöbetçi kör kalır."),
        row("R4", 20, "İki SRE yeni bir sistem istemiyor; envanter zaten Aurora'da.",
            "İki SRE SQL biliyor; envanter Aurora'da üç table'dır ve Terraform hattı oraya yazar. Yeni bir database ve kopyalama hattı istenmiyor.",
            "İkinci bir sistem iki kişilik ekibe bir nöbet, bir yedek ve bir senkron işi ekler."),
        row("R5", 20, "Günde 200 soru için her sabit fatura sorunun kendisinden pahalıdır.",
            "Bütçe sıkıdır; soru başına değil, ay başına bakılır. Var olan bir sisteme ek maliyet tercih edilir.",
            "Günde 200 soru için ayda yüzlerce dolarlık sabit bir fatura savunulamaz."),
    ],
    cands=["aur", "np", "npa"],
    scores={
        "aur": [sc(5, "WITH RECURSIVE bağımlılıkları sekiz seviyeye kadar takip eder ve yolu bir dizide taşır. 5 puan kırıldı: değişken derinlik recursive bir sorgu, döngü kontrolü (CYCLE ya da dizi kontrolü) ve yol dizisi ister; bu bir pattern değil, elle yazılmış bir aramadır."),
                sc(8, "Graph küçüktür ve buffer cache'te durur; sorgu milisaniyelerdir. 2 puan kırıldı: her seviye bir index araması ve birleştirmedir; derinlik arttıkça ara sonuç büyür."),
                sc(8, "Parçalar ve bağlantılar table'lardır. 2 puan kırıldı: yeni bir parça türü ya yeni bir table ya da genel bir nodes table'ında bir type kolonudur."),
                sc(10, "Terraform hattı bu table'lara zaten yazıyor; gece farkı bir transaction'dır. Puan kırılmadı."),
                sc(10, "Günde 200 soru Aurora için önemsizdir. Puan kırılmadı."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(10, "Yeni sistem yok, kopyalama yok; ekip SQL biliyor. Puan kırılmadı."),
                sc(10, "Var olan cluster; üç küçük table için ek fatura yoktur. Puan kırılmadı.")],
        "np": [sc(10, "MATCH p = (s:Switch {`~id`: $sw})<-[:CONNECTED_TO|RUNS_ON|DEPENDS_ON*1..8]-(svc:Service {customer_facing: true}) RETURN p; değişken uzunlukta path (Ö5) ve openCypher her edge'i bir çözümde en fazla bir kez geçerek döngüyü engeller. Puan kırılmadı."),
               sc(10, "50 MB'lık graph buffer cache'te durur; traversal yalnız ilgili komşuları okur (Ö3). Puan kırılmadı."),
               sc(10, "Yeni bir parça türü yeni bir label'dır; şema değişikliği yoktur (Ö1). Puan kırılmadı."),
               sc(9, "Gece farkı bulk loader ya da UNWIND ile MERGE olarak yazılır (Ö7). 1 puan kırıldı: Terraform'da silinen parçaları bulup DETACH DELETE eden bir fark adımı yazılır."),
               sc(10, "Günde 200 soru küçüktür. Puan kırılmadı."),
               sc(10, "Altı kopyalı cluster volume. Puan kırılmadı."),
               sc(5, "Yönetilen cluster. 5 puan kırıldı: ekip openCypher öğrenir (2), envanteri Aurora'dan Neptune'e taşıyan bir hat kurar (2) ve ikinci bir cluster'ın NCU, parametre ve sürüm işi gelir (1)."),
               sc(3, "NCU-saat başına ödenir. 7 puan kırıldı: kapasite sıfıra inmez; bir writer ve bir reader en düşük kapasitede ayda yaklaşık 283 USD'dir (eu-central-1, NCU-saat 0,1941 USD, 2026-10-31) ve bu günde 200 sorunun bütün faturasıdır. Tek instance (ayda yaklaşık 142 USD) da seçilebilir, ama arıza anında envanterin okunabilmesi (R3 satırı) bir replica ister; tek instance'la da puan değişmez: 142 USD yine günde 200 sorunun sabit faturasıdır.")],
        "npa": [sc(10, "Aynı değişken uzunlukta pattern; ayrıca BFS hazır bir algoritmadır (Ö8). Puan kırılmadı."),
                sc(10, "Graph bellekte durur. Puan kırılmadı."),
                sc(10, "Yeni tür yeni bir label'dır. Puan kırılmadı."),
                sc(8, "Graph S3'ten ya da openCypher ile güncellenir. 2 puan kırıldı: gece farkı için bir yükleme ya da MERGE adımı ve silinenleri bulan bir fark adımı yazılır."),
                sc(10, "Günde 200 soru küçüktür. Puan kırılmadı."),
                sc(8, "Graph verisi korunur. 2 puan kırıldı: kalıcılık tek instance'a ve snapshot'lara dayanır."),
                sc(5, "Sunucusuz graph. 5 puan kırıldı: ekip openCypher öğrenir (2), envanteri taşıyan bir hat kurar (2) ve m-NCU boyutu seçilir (1)."),
                sc(2, "m-NCU-saat başına ödenir. 8 puan kırıldı: en küçük graph da saat başına ödenir (32 m-NCU saatte 1,162 USD, ayda yaklaşık 850 USD); durdurmak mümkündür ama arıza anında açık olması gerekir.")],
    },
    h2h={
        "np": "Graph (Neptune) ile kafa kafaya. Bu kartta engine uyumunu Neptune kazanır ve bunu açıkça söylemek gerekir: \"bu switch düşerse ne düşer\" değişken uzunlukta tek bir pattern'dir, döngüleri openCypher kendisi engeller ve yeni bir parça türü yeni bir label'dır (R1'de 44,5'e 31). "
              "Ama toplamı R4 ve R5 çevirir: envanter zaten Aurora'dadır ve Terraform hattı oraya yazar; Neptune için ikinci bir cluster, bir kopyalama hattı ve yeni bir dil gerekir ve en düşük kapasitesi ayda yaklaşık 283 USD'dir, bu günde 200 sorunun bütün faturasıdır. "
              "Hangi koşul değişseydi Neptune seçilirdi: altyapı on kat büyüseydi (yüz binlerce parça), soru her deploy'da otomatik olarak saniyede birçok kez sorulsaydı ya da envanterin kaydı baştan Neptune'de tutulsaydı.",
        "npa": "Bellek içi graph analitiği (Neptune Analytics) ile kafa kafaya. Engine olarak Neptune Analytics de bu soruyu tek bir pattern ya da hazır bir BFS ile cevaplar ve graph bellekte durur; R1'de Neptune'e yakındır. "
               "Kaybı servis tasarımındadır: en küçük graph da saat başına ödenir (32 m-NCU ayda yaklaşık 850 USD) ve arıza anında açık olması gerektiği için durdurulamaz (R5); ekip için de yeni bir sistem ve bir kopyalama hattıdır (R4). "
               "Hangi koşul değişseydi Neptune Analytics seçilirdi: soru arıza anında değil haftalık bir risk analizi olsaydı (\"en çok servisi taşıyan tek nokta hangisi?\", merkezilik algoritmaları) ve graph analizden sonra durdurulabilseydi.",
    },
    verdict="Karar: Aurora {aur}, Neptune {np}, Neptune Analytics {npa}. Bu iş yüküne en uygun servis Aurora'dır, ama engine uyumunda Neptune 13,5 puan öndedir. Aurora'yı öne geçiren R4 ve R5'tir: envanter zaten oradadır ve günde 200 soru için ikinci bir database'in sabit faturası savunulamaz. "
            "Yine de Neptune seçersek artımız: sorgu tek bir pattern'dir, döngüler kendiliğinden engellenir, yeni parça türleri şema değişikliği istemez. "
            "Eksimiz: envanteri Aurora'dan taşıyan bir hat, ikinci bir cluster'ın işletimi ve ayda yaklaşık 283 USD; uygulama gece farkında silinen parçaları da siler. Bir koşul değişseydi: altyapı on kat büyüseydi ve soru saniyede birçok kez sorulsaydı Neptune kazanırdı."))

# ------------------------------------------------------------------ 7. supply chain risk analysis over the whole graph (Neptune Analytics wins)
NEPTUNE_W.append(wusecase("supply", 7,
    title="Tedarik zinciri: tek nokta riskleri (bütün graph analizi)",
    key="Vertex: Supplier, Part, Product. Edge: SUPPLIES, PART_OF. Soru: her tedarikçi için ona herhangi bir derinlikte bağlı ürün sayısı ve merkezilik; bir tedarikçi çıkarılırsa kaynaksız kalan ürünler.",
    story="Lale Market'in kendi markalı ürünleri için 900 tedarikçi, 40.000 parça ve 12.000 ürün var; aralarında 300.000 SUPPLIES ve PART_OF edge'i bulunuyor. Satın alma ekibi her hafta bir risk analizi yapar: "
          "her tedarikçi için ona herhangi bir derinlikte bağlı ürün sayısı ve PageRank ile merkezilik; amaç tek nokta risklerini bulmaktır. Bir kriz haftasında (bir liman kapanır) analistler \"bu üç tedarikçi çıkarsa hangi ürünler kaynaksız kalır?\" sorusunu saatte 50 kez farklı senaryolarla sorar. "
          "Veri her gece ERP'den S3'e dışa aktarılır. Ekip iki analisttir ve Python ile notebook kullanır. Graph kaybolursa S3'ten yeniden yüklenir.",
    wnote="R1 toplam 45: soru bir vertex'ten değil bütün graph'tan başlar (10), algoritmanın bütün graph üzerinde çalışması (15) ve hazır algoritmalar (15) bu kartın kendisidir. "
          "R4 20 ve R5 20 ile ikinci sıradadır: iki analist sistem işletmez ve analiz haftada bir yapılır, sürekli açık bir sistem savunulamaz. R3 5'tir: graph S3'ten yeniden kurulur.",
    rows=[
        row("EY", 10, "Soru her tedarikçiden başlar; bir başlangıç vertex'i yoktur.",
            "\"Her tedarikçi için ona herhangi bir derinlikte bağlı ürünler\" ve \"bu tedarikçiler çıkarsa kaynaksız kalan ürünler\": soru bütün graph üzerindedir.",
            "Soru 900 ayrı sorguya bölünürse analiz saatler sürer ve senaryolar karşılaştırılamaz."),
        row("DA", 15, "Algoritma her vertex'i ve her edge'i birkaç kez gezer.",
            "PageRank ve erişilebilirlik bütün graph'ı birkaç tur okur; bir senaryo birkaç saniyede dönmeli.",
            "Her senaryo dakikalar sürerse kriz haftasında analistler tahmine döner."),
        row("AO", 15, "İki analist algoritmaları kendileri yazmamalı.",
            "PageRank, bağlı bileşenler, en kısa yol ve benzerlik hazır algoritmalar olarak çağrılmalı.",
            "Algoritmalar Python'da elle yazılırsa veri her seferinde dışarı taşınır ve sonuçlar doğrulanamaz."),
        row("VM", 5, "Veri doğası gereği bir bağımlılık ağıdır.",
            "Tedarikçi, parça ve ürün vertex'leri; tedarik ve parça olma edge'leri.",
            "Ağ table'lara düzleştirilirse her derinlik bir birleştirme daha olur."),
        row("R2", 10, "Haftada bir analiz ve kriz haftasında saatte 50 senaryo.",
            "Normal haftada tek bir analiz; kriz haftasında saatte 50 senaryo.",
            "Kriz haftasında yavaşlayan sistem en çok gerektiği anda yetmez."),
        row("R3", 5, "Graph her gece S3'e dışa aktarılan veriden yeniden kurulur.",
            "Düşük: graph S3'teki dışa aktarımdan yeniden yüklenir.",
            "Kayıp birkaç saatlik yeniden yüklemedir."),
        row("R4", 20, "İki analist sistem işletmez ve notebook'tan çalışır.",
            "İki analist Python ve notebook kullanır; sunucu, kapasite ve sürüm işi istenmez.",
            "İşletme işi analizi geciktirir; analistler sonuçlar yerine altyapıyla uğraşır."),
        row("R5", 20, "Analiz haftada bir yapılır; sistem geri kalan zamanda kapalı kalabilmeli.",
            "Haftada birkaç saat kullanım; kullanılmadığında fatura neredeyse sıfır olmalı.",
            "Haftada birkaç saatlik iş için gece gündüz açık bir sistem ödenirse analizin maliyeti değerini aşar."),
    ],
    cands=["npa", "rs", "np"],
    scores={
        "npa": [sc(10, "Algoritmalar bütün graph üzerinde çalışır; erişilebilirlik ve senaryo sorguları openCypher'dır (Ö8). Puan kırılmadı."),
                sc(10, "Graph bellekte durur; algoritmalar birçok iş parçacığıyla bütün graph'ı gezer. Puan kırılmadı."),
                sc(10, "PageRank, bağlı bileşenler, BFS, en kısa yol ve benzerlik openCypher prosedürleri olarak hazırdır (Ö8). Puan kırılmadı."),
                sc(10, "Tedarik ağı doğrudan vertex ve edge'tir. Puan kırılmadı."),
                sc(9, "Kriz haftasında saatte 50 senaryo küçüktür. 1 puan kırıldı: kapasite yalnız bir yönetim işlemiyle büyür."),
                sc(10, "Graph S3'ten yeniden yüklenir; istenen bu kadardır. Puan kırılmadı."),
                sc(7, "Sunucusuz graph, notebook desteği, S3'ten yükleme. 3 puan kırıldı: analistler openCypher öğrenir (2) ve m-NCU boyutu graph'ın büyüklüğüne göre seçilir (1)."),
                sc(7, "m-NCU-saat başına ödenir. 3 puan kırıldı: graph açıkken saat başına ödenir (32 m-NCU saatte 1,162 USD); analizler arasında durdurulan graph fiyatın onda birini öder.")],
        "rs": [sc(5, "Recursive CTE ile erişilebilirlik yazılır. 5 puan kırıldı: her tedarikçi için recursive bir sorgu ve döngü kontrolü gerekir; AWS recursion derinliğini sınırlamayı önerir."),
               sc(6, "Columnar tarama ve paralel birleştirme bütün table'ı hızla okur. 4 puan kırıldı: her derinlik bir birleştirme turudur ve PageRank gibi tekrarlı bir algoritma her turda bütün edge table'ını yeniden birleştirir."),
               sc(4, "Window fonksiyonları ve toplamlar var. 6 puan kırıldı: graph algoritması yoktur; PageRank tekrarlı SQL ya da dışarıda Python ile yazılır."),
               sc(7, "Edge'ler bir table'dır. 3 puan kırıldı: ağ row'lardaki id çiftleridir; derinlik birleştirme sayısıdır."),
               sc(9, "Serverless RPU'lar sorgu başına büyür. 1 puan kırıldı: ilk sorgularda kapasite ısınır."),
               sc(10, "Veri S3'ten yeniden yüklenir. Puan kırılmadı."),
               sc(7, "Serverless workgroup. 3 puan kırıldı: analistler için yeni bir sistem; recursive SQL ve algoritma kodu onların işidir."),
               sc(8, "Serverless'ta kullanıldıkça RPU-saat ödenir. 2 puan kırıldı: her sorgu en düşük RPU kapasitesiyle ve en az birkaç dakika olarak faturalanır.")],
        "np": [sc(6, "Erişilebilirlik değişken uzunlukta bir pattern'dir (Ö5). 4 puan kırıldı: soru bir vertex'ten başlamaz; 900 tedarikçi için 900 traversal ya da bütün graph'ı tarayan tek bir sorgu gerekir."),
               sc(5, "Traversal komşuları okur (Ö3). 5 puan kırıldı: AWS'e göre Neptune Database \"optimized for transactional type queries that start at a single node or set of nodes and fan out\"; bütün graph'ı birkaç tur okumak bu tasarımın dışındadır; sorgu süresi sınırı R2'de sayıldı."),
               sc(4, "Index'ler ve değişken uzunlukta path var (Ö2, Ö5). 6 puan kırıldı: Neptune Database'te PageRank, merkezilik ve topluluk algoritmaları yoktur; graph Neptune Analytics'e ya da dışarı taşınır."),
               sc(10, "Tedarik ağı doğrudan vertex ve edge'tir (Ö1). Puan kırılmadı."),
               sc(8, "Serverless instance'ları büyür. 2 puan kırıldı: uzun analiz sorguları için sorgu süresi sınırı yükseltilir ve kapasite önceden büyütülür."),
               sc(10, "Altı kopyalı cluster volume. Puan kırılmadı."),
               sc(7, "Yönetilen cluster. 3 puan kırıldı: analistler openCypher öğrenir (2) ve NCU aralığı ayarlanır (1)."),
               sc(6, "NCU-saat başına ödenir. 4 puan kırıldı: haftada birkaç saatlik iş için en az bir instance gece gündüz ödenir.")],
    },
    h2h={
        "rs": "Data warehouse (Redshift) ile kafa kafaya. Redshift büyük tabloları tarar, birleştirir ve toplar ve recursive CTE ile bir ağı aşağı inebilir; kullanıldıkça ödenen serverless modu da bu haftalık iş yüküne uyar (R5). "
              "Ama bu kartın sorusu bir toplam değil bir graph algoritmasıdır: PageRank birçok tur ister ve her tur bütün edge table'ının yeniden birleştirilmesidir; erişilebilirlik her tedarikçi için recursive bir sorgudur (R1.1–R1.3). Algoritmaları analistler kendileri yazar. "
              "Hangi koşul değişseydi Redshift seçilirdi: soru \"tedarikçi başına toplam harcama ve geciken teslimat oranı\" gibi bir toplam olsaydı ve derinlik bir ya da iki seviyede kalsaydı; o zaman ağ değil bir tablo sorgulanır.",
        "np": "Graph (Neptune) ile kafa kafaya. Neptune Database aynı property graph'ı tutar ve tek bir senaryoyu (\"bu tedarikçi çıkarsa ne olur?\") bir pattern olarak cevaplayabilir. "
              "Ama bu iş yükünün ağırlığı bütün graph üzerindeki algoritmalardadır ve Neptune Database bir vertex'ten başlayıp yayılan sorgular için tasarlanmıştır; PageRank ve merkezilik onun engine'inde yoktur (R1.2, R1.3). "
              "Haftada birkaç saatlik iş için gece gündüz açık bir cluster da R5'te kaybettirir. Neptune Analytics aynı veri modeliyle bu işi bellekte ve hazır algoritmalarla yapar. "
              "Hangi koşul değişseydi Neptune seçilirdi: soru haftalık analiz değil, her satın alma siparişinde \"bu parçanın alternatif tedarikçisi var mı?\" gibi bir vertex'ten başlayan, saniyede birçok kez sorulan bir kontrol olsaydı.",
    },
    verdict="Karar: Neptune Analytics {npa}, Redshift {rs}, Neptune {np}. Bu iş yüküne en uygun servis Neptune Analytics'tir: soru bütün graph üzerindedir, algoritmalar hazırdır ve graph analizler arasında durdurulabilir. Kararı R1 verir. "
            "Yine de Neptune seçersek artımız: tek bir senaryo bir pattern'dir ve veri altı kopyalı volume'dadır. "
            "Eksimiz: PageRank ve merkezilik için graph dışarı taşınır, uzun sorgular sorgu süresi sınırına çarpar ve cluster haftanın geri kalanında da ödenir. "
            "Doğru mimari çoğunlukla ikisi birliktedir: günlük kontroller Neptune Database'te, haftalık analiz aynı veriden yüklenen bir Neptune Analytics graph'ında. Bir koşul değişseydi: soru her siparişte bir vertex'ten başlasaydı Neptune kazanırdı."))

# ------------------------------------------------------------------ 8. access control graph with nested groups
NEPTUNE_W.append(wusecase("access", 8,
    title="Erişim kontrolü graph'ı: iç içe gruplar ve klasörler",
    key="Vertex: User, Group, Folder, Document. Edge: MEMBER_OF, CAN_READ, IN. Soru: bu kullanıcının, herhangi bir grup ve klasör zinciri üzerinden, bu belgeyi okuma hakkı var mı?",
    story="Lale Market'in tedarikçi portalında 20.000 kullanıcı, 6 seviyeye kadar iç içe 3.000 grup ve 200.000 klasör ile belge var; haklar klasörden alt klasörlere miras kalır. "
          "Her belge açılışında soru şudur: \"bu kullanıcının, herhangi bir grup zinciri ve klasör zinciri üzerinden, bu belgeyi okuma hakkı var mı?\" Saniyede 2.000 kontrol yapılır ve her biri 20 ms içinde dönmelidir. "
          "Yöneticiler dakikada 100 üyelik değiştirir; bir hakkın geri alınması saniyeler içinde etkili olmalıdır, çünkü ayrılan bir çalışanın erişimi sürmemelidir. \"Bütün çalışanlar\" grubunun 20.000 üyesi var. "
          "Haklar denetim kaydıdır ve kaybolmamalıdır. Ekip dört geliştiriciden oluşur ve SQL bilir; Aurora sistemde zaten çalışır.",
    wnote="R1 toplam 50: iki zincirli yol sorusu (20), geri alınan hakkın hemen etkili olması (10), üyelik değişikliklerinin biçimi (10) ve 20 ms (10). "
          "R2 15 ve R3 15: saniyede 2.000 kontrol ve denetim kaydı. R4 ve R5 10'ar.",
    rows=[
        row("EY", 20, "Her belge açılışı bu soruyu sorar; iki zincirin derinliği önceden bilinmez.",
            "\"Kullanıcıdan, 0-6 seviye grup üzerinden, bir hakka; haktan, 0-10 seviye klasör üzerinden, bu belgeye bir yol var mı?\" Cevap evet ya da hayırdır; ilk yol yeterlidir.",
            "Soru her seviye için ayrı istek olursa 20 ms'ye sığmaz; yanlış cevap ya bir erişimi engeller ya da bir sızıntıdır."),
        row("DA", 10, "20 ms her belge açılışında geçerlidir; \"bütün çalışanlar\" grubu 20.000 üyelidir.",
            "Kontrol yalnız bu kullanıcının gruplarına ve bu belgenin klasörlerine bakmalı; büyük gruplar kontrolü yavaşlatmamalı.",
            "Kontrol yavaşlarsa her belge açılışı yavaşlar; portalın bütün ekranları bekler."),
        row("TA", 10, "Ayrılan bir çalışanın erişimi sürmemelidir.",
            "Bir üyelik silindiğinde bir sonraki kontrol onu görmeli; yarım yazılmış bir değişiklik görülmemeli.",
            "Eski bir üyelik görünmeye devam ederse ayrılan çalışan belge okumaya devam eder."),
        row("OY", 10, "Dakikada 100 üyelik değişikliği; biri en üst gruptaysa binlerce kullanıcıyı etkiler.",
            "Bir üyelik tek bir yazmayla eklenir ya da silinir, bir klasör tek yazmayla taşınır; etkilenen kullanıcı sayısı yazmayı büyütmemeli.",
            "Bir üst grup değişikliği binlerce kaydı yeniden yazdırırsa değişiklik dakikalar sürer ve o arada haklar yanlıştır."),
        row("R2", 15, "Saniyede 2.000 kontrol portalın bütün trafiğidir.",
            "Saniyede 2.000 kontrol, her biri 20 ms içinde; dakikada 100 değişiklik.",
            "Kontrol tepe anında yavaşlarsa portal yavaşlar."),
        row("R3", 15, "Haklar denetim kaydıdır; bir denetimde geriye dönük sorulur.",
            "Onaylanan hiçbir hak değişikliği kaybolmamalı; geriye dönük geri yükleme mümkün olmalı.",
            "Kaybolan bir geri alma işlemi, bir sızıntının kanıtını da siler."),
        row("R4", 10, "Dört geliştirici SQL biliyor; sunucu işletmek istemiyor.",
            "Dört geliştirici SQL biliyor; yeni bir sorgu dili kabul edilir, sunucu boyutlandırmak istenmez.",
            "İşletme işi küçük ekibin portal geliştirme zamanını yer."),
        row("R5", 10, "Trafik iş saatlerinde yoğun, gece düşüktür.",
            "Trafik iş saatlerinde yoğun, gece onda birdir.",
            "Gece boş duran kapasite ödenirse kontrol başına maliyet büyür."),
    ],
    cands=["np", "ddb", "aur"],
    scores={
        "np": [sc(10, "MATCH (u:User {`~id`: $u})-[:MEMBER_OF*0..6]->(:Group)-[:CAN_READ]->(:Folder)<-[:IN*0..10]-(d:Document {`~id`: $d}) RETURN true AS allowed LIMIT 1; LIMIT 1 ilk bulunan yolda durur ve iki değişken uzunlukta parça tek pattern'dedir (Ö4, Ö5). Puan kırılmadı."),
               sc(9, "Kontrol kullanıcının ve belgenin vertex'lerinden başlar (Ö2, Ö3). 1 puan kırıldı: \"bütün çalışanlar\" grubu supernode'dur; önceden bilindiği için o gruba verilen haklar ayrı bir property ile kısa yoldan kontrol edilir (A4)."),
               sc(10, "Okuma sorguları snapshot isolation ile commit edilmiş son durumu görür; silinen üyelik bir sonraki kontrolde yoktur (Ö6). Puan kırılmadı."),
               sc(10, "Bir üyelik tek bir edge'tir; ekleme ya da silme tek yazmadır ve etkilenen kullanıcı sayısından bağımsızdır (Ö1). Puan kırılmadı."),
               sc(9, "Kontroller replica'lara dağılır. 1 puan kırıldı: bütün yazmalar tek writer'dan geçer ve replica'lar birkaç milisaniye geridedir; bir geri alma o kadar geç görünür."),
               sc(10, "Altı kopyalı cluster volume ve 35 güne kadar point-in-time restore. Puan kırılmadı."),
               sc(7, "Yönetilen cluster. 3 puan kırıldı: ekip openCypher öğrenir (2) ve replica ile NCU aralığını iş saatlerine göre ayarlar (1)."),
               sc(7, "NCU-saat başına ödenir. 3 puan kırıldı: kapasite gece sıfıra inmez; writer ve reader'ın en düşük NCU'su gece de ödenir.")],
        "ddb": [sc(6, "Her kullanıcının bütün grupları (iç içe olanlar açılmış hâlde) ve her belgenin bütün hak sahibi grupları önceden düzleştirilir; kontrol iki GetItem ve bir kesişimdir. 4 puan kırıldı: yol sorusu bir kesişime çevrilir ve düzleştirmeyi uygulama tutar."),
                sc(10, "İki GetItem tek haneli milisaniyedir. Puan kırılmadı."),
                sc(6, "Her item strongly consistent okunabilir. 4 puan kırıldı: bir üst grup değişikliği binlerce düzleştirilmiş item'ı yeniden yazar; bu bir transaction'a (en fazla 100 item) sığmaz ve yayılma bitene kadar haklar karışıktır."),
                sc(4, "Tek bir üyelik değişikliği bir item'dır. 6 puan kırıldı: düzleştirme yüzünden \"bütün çalışanlar\" ya da bir üst grup değişikliği 20.000'e kadar item'ı yeniden yazdırır."),
                sc(10, "On-demand mod kontrolleri ayarsız karşılar. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır; point-in-time recovery. Puan kırılmadı."),
                sc(8, "Serverless. 2 puan kırıldı: ekip DynamoDB API'ını ve key tasarımını öğrenir; düzleştirme kodu R1'de sayıldı."),
                sc(9, "İstek başına ödenir; gece maliyet düşer. 1 puan kırıldı: yeniden yazma dalgaları yazma birimi tüketir ve önceden hesaplanmalıdır.")],
        "aur": [sc(5, "İki WITH RECURSIVE (grup zinciri ve klasör zinciri) ve bir kesişim tek SQL sorgusudur. 5 puan kırıldı: değişken derinlik recursive sorgu ve döngü kontrolü ister; bu bir pattern değil, elle yazılmış bir aramadır."),
                sc(6, "Her seviye bir index araması ve birleştirmedir. 4 puan kırıldı: saniyede 2.000 recursive sorgu 20 ms bütçesini zorlar; derin klasörlerde ara sonuç büyür."),
                sc(10, "Transaction'lar; silinen üyelik bir sonraki sorguda yoktur. Puan kırılmadı."),
                sc(10, "Bir üyelik bir row'dur; ekleme ya da silme tek yazmadır. Puan kırılmadı."),
                sc(7, "Kontroller reader'lara gider. 3 puan kırıldı: iş saatlerinde saniyede 2.000 recursive sorgu reader'ları yorar."),
                sc(10, "Üç AZ'de altı kopya ve sürekli yedek. Puan kırılmadı."),
                sc(9, "Aurora zaten çalışıyor; ekip SQL biliyor. 1 puan kırıldı: iş saatleri için reader sayısı ve ACU aralığı ayarlanır; sorgunun yazılışı R1.1'de sayıldı."),
                sc(8, "Var olan cluster'a eklenir. 2 puan kırıldı: iş saatleri için reader'lar ve ACU saat başına ödenir.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB bu kontrolü çok hızlı yapabilir: her kullanıcının bütün grupları ve her belgenin bütün hak sahibi grupları önceden düzleştirilirse kontrol iki GetItem ve bir kesişimdir (R1.2'de tam puan), ölçek ve işletim de rakipsizdir. "
               "Ama düzleştirmenin bedeli yazma tarafındadır: bir üst grup değişikliği binlerce item'ı yeniden yazdırır, bu bir transaction'a sığmaz ve yayılma bitene kadar ayrılan bir çalışanın erişimi sürebilir (R1.3, R1.4). "
               "Hangi koşul değişseydi DynamoDB seçilirdi: gruplar iç içe olmasaydı ya da en fazla bir seviye olsaydı ve haklar nadiren değişseydi; o zaman düzleştirme ucuzdur ve kontrol tek bir GetItem olur.",
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Aurora bu kuralı doğru korur: transaction'lar, sürekli yedek ve SQL bilen bir ekip; üyelik bir row'dur ve değişiklik tek yazmadır (R1.3, R1.4 tam). "
               "Ama soru iki değişken derinlikli zincirdir ve Aurora'da bu iki WITH RECURSIVE ve bir kesişimdir; saniyede 2.000 kontrolde her seviye bir index araması ve birleştirmedir ve 20 ms bütçesi zorlanır (R1.1, R1.2, R2). Aurora'nın R4'teki üstünlüğü (zaten çalışıyor, ekip SQL biliyor) bu farkı kapatmaz, çünkü kontrol her belge açılışında ve iş saatlerinin bütün trafiğinde çalışır. "
               "Hangi koşul değişseydi Aurora seçilirdi: kontrol saniyede birkaç yüze inseydi ve grup derinliği iki seviyeyle sınırlansaydı; o zaman iki sabit join yeterlidir ve ikinci bir database gerekmez.",
    },
    verdict="Karar: Neptune {np}, DynamoDB {ddb}, Aurora {aur}. Bu iş yüküne en uygun servis Neptune'dür: iki değişken derinlikli zincir tek bir pattern'dir ve bir üyelik değişikliği tek bir edge'tir. DynamoDB ile Aurora neredeyse eşittir. "
            "Neptune seçtiğimizde artımız: kontrol tek bir sorgudur, geri alınan hak bir sonraki kontrolde yoktur ve bir üst grup değişikliği binlerce kaydı yeniden yazdırmaz. "
            "Eksimiz: ekip openCypher öğrenir, \"bütün çalışanlar\" gibi büyük gruplar için kısa yol tutulur, kritik bir geri almadan sonraki kontrol writer endpoint'inden okunur ve gece de en düşük kapasite ödenir. Bir koşul değişseydi: gruplar iç içe olmasaydı DynamoDB kazanırdı."))

# ------------------------------------------------------------------ 9. customer 360 for the call center (Aurora wins, Neptune third: a clear loss)
NEPTUNE_W.append(wusecase("c360", 9, sim="w_c360",
    title="Customer 360: çağrı merkezi ekranı",
    key="Tek ekranda: müşteri profili, son 20 sipariş, açık destek talepleri, adresler, sadakat puanı. Soru: müşteri id'si ya da telefonla bu müşterinin bütün kayıtları.",
    story="Lale Market'in çağrı merkezinde 300 temsilci çalışır. Temsilci müşteri id'sini ya da telefon numarasını yazar ve tek bir ekranda profili, son 20 siparişi (tarihe göre), açık destek taleplerini, adresleri ve sadakat puanını görür. "
          "Saniyede 50 ekran açılır; ekran 500 ms içinde gelmelidir. Siparişler ve müşteriler Aurora PostgreSQL'dedir; destek talepleri her gece destek aracından dışa aktarılır. Finans aynı verilerden aylık rapor alır. "
          "Bir ürün yöneticisi \"customer 360 bir graph use case'idir\" diyerek Neptune önerdi. İlişkiler tek hop'tur: müşteriden siparişlere, taleplere ve adreslere. Ekip dört geliştiricidir ve SQL bilir.",
    wnote="R1 toplam 45: id ya da telefonla bulup tek hop'luk listeleri tarihe göre getirmek (15), sabit alanlı kayıtlar (10), az önceki siparişin ekranda görünmesi (10) ve sıralama ile arama araçları (10). "
          "R4 25 ile ikinci: veri zaten Aurora'dadır ve ekip ikinci bir sistem istemez. R5 15, R2 5: saniyede 50 ekran küçük bir yüktür.",
    rows=[
        row("EY", 15, "Her ekran bu soruyla açılır; ilişkiler tek hop'tur.",
            "Müşteri id'si ya da telefonla müşteri; ondan tek hop'ta siparişler (son 20, tarihe göre), açık talepler ve adresler.",
            "Ekran birkaç ayrı sorguya bölünür ve yavaşlarsa temsilci müşteriyi bekletir."),
        row("VM", 10, "Kayıtların alanları sabittir; sipariş, adres ve talep birer tablodur.",
            "Profil, sipariş, adres ve talep sabit alanlı kayıtlardır; tutarlar ve tarihler tiplidir.",
            "Alanlar doğrulanmazsa ekranda eksik ya da yanlış tipli değerler görünür."),
        row("TA", 10, "Müşteri az önce verdiği siparişi soruyor olabilir.",
            "Ekran checkout'un birkaç saniye önce yazdığı siparişi göstermeli.",
            "Sipariş ekranda görünmezse temsilci müşteriye yanlış bilgi verir."),
        row("AO", 10, "Telefonla arama ve tarihe göre sıralama her ekranda kullanılır.",
            "Telefon numarasıyla arama, sipariş tarihine göre sıralama ve LIMIT; bunları destekleyen index'ler.",
            "Arama ya da sıralama bir tam taramaya dönerse ekran yavaşlar."),
        row("R2", 5, "Saniyede 50 ekran küçük bir yüktür.",
            "Saniyede 50 ekran, 500 ms içinde.",
            "Bu yük her aday için küçüktür."),
        row("R3", 10, "Siparişler resmi kayıttır, ama bu ekran onları yalnız okur.",
            "Ekranın okuduğu veri kaybolmamalı.",
            "Ekran yanlış ya da eksik veri gösterirse temsilci yanlış işlem yapar."),
        row("R4", 25, "Veri zaten Aurora'da; ikinci bir sistem bu ekran için en büyük risktir.",
            "Dört geliştirici SQL biliyor; siparişler ve müşteriler Aurora'da, talepler her gece içeri alınıyor. İkinci bir sistem ve kopyalama hattı ancak bir kazanç varsa kurulmalı.",
            "Kopyalama hattı bozulursa ekran eski siparişleri gösterir ve hata kimse fark etmeden sürer."),
        row("R5", 15, "Ekran bir iç araçtır; maliyeti küçük olmalı.",
            "İç bir ekran için ek maliyet en düşük olmalı.",
            "İkinci bir database'in sabit faturası ekranın değerinden büyük olabilir."),
    ],
    cands=["aur", "doc", "np"],
    scores={
        "aur": [sc(10, "WHERE customer_id = ? ya da phone = ? ile müşteri; JOIN ve ORDER BY order_date DESC LIMIT 20 ile siparişler; hepsi index'lerle. Puan kırılmadı."),
                sc(10, "Sabit alanlar, tipler ve kısıtlar şemadadır. Puan kırılmadı."),
                sc(10, "Siparişi yazan database'in kendisi; writer'dan okuma son siparişi görür. Puan kırılmadı."),
                sc(9, "B-tree index'leri (customer_id, order_date) sıralamayı ve LIMIT'i ucuz yapar. 1 puan kırıldı: telefon için normalleştirilmiş bir kolon ve index eklenir."),
                sc(10, "Saniyede 50 ekran Aurora için küçüktür. Puan kırılmadı."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(9, "Yeni sistem yok; ekip SQL biliyor. 1 puan kırıldı: destek taleplerinin gecelik içeri alma işi yazılır."),
                sc(10, "Var olan cluster; ekran için ek fatura yok denecek kadar azdır. Puan kırılmadı.")],
        "doc": [sc(8, "Müşteri document'ı adresleri ve sadakat puanını gömer; siparişler ayrı collection'da. 2 puan kırıldı: siparişler ve talepler için ikinci ve üçüncü bir sorgu ya da $lookup gerekir."),
                sc(8, "Document esnek alanlar taşır. 2 puan kırıldı: sabit alanlı kayıtlarda şema doğrulaması isteğe bağlıdır ve uygulamanın işidir."),
                sc(10, "Okumalar primary'den commit edilmiş güncel durumu görür. Puan kırılmadı: siparişlerin Aurora'dan kopyalanması ve gecikmesi R4'te sayıldı (Neptune için de)."),
                sc(9, "Compound index'ler sıralama ve LIMIT'i destekler. 1 puan kırıldı: telefon için bir index eklenir."),
                sc(10, "Saniyede 50 ekran küçüktür. Puan kırılmadı."),
                sc(10, "Üç AZ'de kopyalanan volume. Puan kırılmadı."),
                sc(5, "Yönetilen cluster. 5 puan kırıldı: ikinci bir database, Aurora'dan siparişleri ve müşterileri taşıyan ve gecikmesi izlenen bir hat ve MongoDB API'ı ekip için yenidir."),
                sc(6, "Instance-saat başına ödenir. 4 puan kırıldı: Aurora'nın yanında ikinci bir cluster yalnız bu ekran için ödenir.")],
        "np": [sc(8, "Müşteri vertex'i ~id ile ya da phone property'siyle bulunur (Ö2) ve siparişler tek hop'tur (Ö3). 2 puan kırıldı: \"son 20 sipariş\" müşterinin bütün sipariş edge'leri okunduktan sonra ORDER BY ile sıralanır; tek hop'ta graph'ın bir kazancı yoktur."),
               sc(6, "Kayıtlar property'li vertex'lerdir (Ö1). 4 puan kırıldı: sabit alanlı ve tipli kayıtlar için şema ve kısıt yoktur; tutar, tarih ve zorunlu alanları uygulama doğrular."),
               sc(10, "Okuma sorguları snapshot isolation ile commit edilmiş son durumu görür (Ö6). Puan kırılmadı."),
               sc(7, "Üç varsayılan index (SPOG, POGS, GPSO) id ve property araması verir (Ö2). 3 puan kırıldı: kullanıcının tanımladığı bir index yoktur ve telefonun bir kısmıyla ya da normalleştirilmiş bir biçimiyle arama OpenSearch entegrasyonu ister; sıralama R1.1'de, şema R1.2'de sayıldı."),
               sc(10, "Saniyede 50 ekran küçüktür. Puan kırılmadı."),
               sc(10, "Altı kopyalı cluster volume. Puan kırılmadı."),
               sc(4, "Yönetilen cluster. 6 puan kırıldı: ekip openCypher öğrenir (2), siparişleri ve müşterileri Aurora'dan taşıyan bir hat kurar (2), talepleri ayrıca içeri alır (1) ve NCU aralığını ayarlar (1)."),
               sc(4, "NCU-saat başına ödenir. 6 puan kırıldı: Aurora'nın yanında en az iki instance yalnız bu ekran için gece gündüz ödenir (en düşük kapasitede ayda yaklaşık 283 USD).")],
    },
    h2h={
        "doc": "Document (DocumentDB) ile kafa kafaya. DocumentDB müşteri profilini, adresleri ve sadakat puanını tek bir document'ta tutabilir; esnek alanlar ve compound index'ler bu ekran için yeterlidir (R1'de 37). "
               "Ama veri Aurora'dan gelir: siparişler ve müşteriler kopyalanır, ekran kopyanın gecikmesi kadar geride kalabilir ve sabit alanlı kayıtlarda şema doğrulaması uygulamanın işidir. "
               "Kaybın büyük kısmı R4 ve R5'tedir: ikinci bir database, bir kopyalama hattı ve yeni bir API yalnız bu ekran için kurulur ve ödenir. "
               "Hangi koşul değişseydi DocumentDB seçilirdi: müşteri verisi baştan bir document database'te tutulsaydı (her ülkede farklı alanlar, iç içe tercihler) ve siparişler de orada yaşasaydı.",
        "np": "Graph (Neptune) ile kafa kafaya. Neptune bu ekranı yapabilir: müşteri vertex'i id ya da telefonla bulunur ve siparişler tek hop'tur. Ama graph'ın gücü çok hop'lu yollardadır ve bu ekranın bütün ilişkileri tek hop'tur; Neptune burada bir kazanç vermez. "
              "Sabit alanlı kayıtlar için şema ve kısıt yoktur, \"son 20 sipariş\" için bileşik bir index yoktur (R1.2, R1.4). Veri de Aurora'dadır: ikinci bir database, bir kopyalama hattı ve yeni bir dil yalnız bu ekran için kurulur ve ödenir (R4, R5). "
              "\"Customer 360 bir graph use case'idir\" cümlesi, müşterinin kayıtları arasında çok hop'lu sorular varsa doğrudur. Hangi koşul değişseydi Neptune seçilirdi: ekran \"bu müşteriyle aynı adresi ya da kartı paylaşan diğer müşteriler ve onların iadeleri\" gibi iki üç hop'luk sorular sorsaydı.",
    },
    verdict="Karar: Aurora {aur}, DocumentDB {doc}, Neptune {np}. Bu iş yüküne en uygun servis Aurora'dır ve fark büyüktür: ilişkiler tek hop'tur, veri zaten oradadır ve sabit alanlı kayıtlar için şema bir güvencedir. "
            "Yine de Neptune seçersek artımız: ileride çok hop'lu sorular (ortak adres, ortak kart, aile hesapları) için graph hazır olur. "
            "Eksimiz: ikinci bir database, siparişleri ve müşterileri taşıyan bir hat, yeni bir dil ve ayda yaklaşık 283 USD; uygulama alanları kendisi doğrular ve ekran kopyanın gecikmesi kadar geride kalabilir. "
            "Bir koşul değişseydi: ekran çok hop'lu ilişki soruları sorsaydı Neptune, Aurora'nın yanında ikinci bir database olarak anlam kazanırdı; doğru mimari o zaman ikisi birliktedir."))

# ------------------------------------------------------------------ 10. drug interaction graph (RDF and SPARQL)
NEPTUNE_W.append(wusecase("drugs", 10,
    title="İlaç etkileşim graph'ı (RDF ve SPARQL)",
    key="RDF üçlüleri: ilaç, sınıf (rdfs:subClassOf), enzim, etkileşim. Soru: bu reçetedeki ilaçlar arasında doğrudan, sınıf üzerinden ya da ortak enzim üzerinden bir etkileşim var mı ve neden?",
    story="Lale Market'in eczane ortağı her reçete sepetinde bir etkileşim kontrolü yapar. Hastanın kullandığı ilaçlar (ortalama 6) ve yeni ilaç için soru şudur: aralarında doğrudan bir etkileşim, bir üst sınıf düzeyinde tanımlı bir etkileşim ya da ortak bir enzim üzerinden dolaylı bir etkileşim var mı? "
          "Bilgi kamuya açık bir ontolojiden RDF olarak gelir: 50.000 ilaç ve 2 milyon üçlü; sınıf hiyerarşisi 8 seviyeye kadar iner. Ontoloji her ay yeni bir sürümle güncellenir ve yeni ilişki türleri (predicate) ekleyebilir. "
          "Saniyede 40 kontrol yapılır, her biri 200 ms içinde; cevap etkileşimin nedenini (yolunu) da göstermelidir. Ekipteki iki eczacı-bilişimci SPARQL bilir.",
    wnote="R1 toplam 50: verinin RDF ontolojisi olması (15), sınıf hiyerarşisinden ve enzimden geçen soru (15), her ay değişen predicate'ler (10) ve sorgu araçları (10). "
          "R4 20 ile ikinci: ekip SPARQL bilir. R5 15: kontrol bir hizmet maliyetidir. R2 5: saniyede 40 kontrol.",
    rows=[
        row("VM", 15, "Bilgi standart bir RDF ontolojisi olarak gelir; şekli iş yükünün kendisidir.",
            "Veri RDF üçlüleridir: IRI'li ilaçlar, sınıflar, enzimler; rdfs:subClassOf hiyerarşisi. Kaynak ontolojinin kimlikleri korunmalı.",
            "Ontoloji başka bir şekle çevrilirse kaynakla bağ kopar ve her ay çeviri yeniden yapılır."),
        row("EY", 15, "Her reçete sepeti bu soruyu sorar ve cevap nedenini de göstermelidir.",
            "İlaç çiftleri için: doğrudan etkileşim; bir üst sınıf düzeyinde tanımlı etkileşim (hiyerarşi 8 seviye); bir ilaç bir enzimi engelliyor, diğeri o enzimle işleniyor (iki hop). Yol döner.",
            "Sınıf düzeyindeki bir etkileşim kaçarsa tehlikeli bir kombinasyon onaylanır."),
        row("ŞE", 10, "Ontoloji her ay yeni predicate'ler ekleyebilir.",
            "Yeni bir ilişki türü (ör. yeni bir enzim ilişkisi) şema değişikliği olmadan yüklenmeli.",
            "Her ay bir şema değişikliği gerekirse güncel ontoloji haftalarca gecikir."),
        row("AO", 10, "Ekip hiyerarşi ve yol sorgularını standart araçlarla yazmak istiyor.",
            "Hiyerarşi gezintisi (property path), adlandırılmış graph'lar (her ontoloji sürümü ayrı) ve standart bir sorgu dili.",
            "Bu araçlar yoksa ekip hiyerarşiyi uygulama kodunda gezer ve kontrol doğrulanamaz."),
        row("R2", 5, "Saniyede 40 kontrol küçük ve düzenlidir.",
            "Saniyede 40 kontrol, her biri 200 ms içinde.",
            "Bu yük her aday için küçüktür."),
        row("R3", 10, "Ontoloji yeniden yüklenebilir, ama yerel notlar ve onaylar kaybolmamalı.",
            "Eczacıların eklediği yerel etkileşim notları kaybolmamalı.",
            "Yerel notlar kaybolursa bilinen bir risk yeniden onaylanır."),
        row("R4", 20, "İki kişilik ekip SPARQL bilir; başka bir dil öğrenmek istemez.",
            "İki eczacı-bilişimci SPARQL biliyor; sunucu işletmek istemiyorlar.",
            "Bilinen dilden vazgeçmek bilgiyi ve doğrulanmış sorguları kaybettirir."),
        row("R5", 15, "Kontrol her reçetede yapılan bir hizmet maliyetidir.",
            "Gün boyu düzenli trafik; maliyet reçete başına küçük olmalı.",
            "Büyük bir sabit fatura küçük bir eczane ortağı için kontrolü pahalı yapar."),
    ],
    cands=["np", "ddb", "aur"],
    scores={
        "np": [sc(10, "Neptune RDF üçlülerini (quad) doğrudan saklar ve SPARQL 1.1 ile sorgular; IRI'ler korunur (Ö1). Puan kırılmadı."),
               sc(10, "SPARQL property path (rdfs:subClassOf*) hiyerarşiyi her derinlikte gezer ve enzim yolu iki üçlüdür; değişken uzunlukta yol (Ö5) yolu da döndürür. Puan kırılmadı."),
               sc(10, "Yeni bir predicate yeni bir üçlüdür; şema yoktur, bulk loader yeni sürümü yükler (Ö7). Puan kırılmadı."),
               sc(9, "Property path, adlandırılmış graph'lar ve SPARQL; index'ler (SPOG, POGS, GPSO) her pozisyonda arar (Ö2). 1 puan kırıldı: hiyerarşi her kontrolde property path ile yeniden gezilir; sık kullanılan genişletmeler yükleme sırasında önceden yazılabilir."),
               sc(10, "Saniyede 40 kontrol küçüktür. Puan kırılmadı."),
               sc(10, "Altı kopyalı cluster volume; yerel notlar ayrı bir adlandırılmış graph'ta. Puan kırılmadı."),
               sc(9, "Yönetilen cluster ve ekip SPARQL biliyor. 1 puan kırıldı: NCU aralığı ve replica ayarlanır."),
               sc(8, "NCU-saat başına ödenir; düzenli trafiğe uyar. 2 puan kırıldı: en az iki instance gece gündüz ödenir.")],
        "ddb": [sc(4, "Bütün ilaç çiftlerinin etkileşimleri her ay dışarıda hesaplanıp item olarak yazılır. 6 puan kırıldı: ontoloji düzleştirilir; IRI'ler ve hiyerarşi kaybolur, yalnız sonuç kalır."),
                sc(8, "Reçetedeki çiftler BatchGetItem ile tek istekte okunur. 2 puan kırıldı: \"neden\" yolu ayrıca hesaplanıp item'a yazılmazsa cevapta yoktur."),
                sc(7, "Item'lar şemasızdır. 3 puan kırıldı: yeni predicate bir kolon değil, dışarıdaki hesaplama kodunda bir değişikliktir."),
                sc(5, "Key ile okuma. 5 puan kırıldı: hiyerarşi ve yol araçları yoktur; genişletme her ay başka bir araçla yapılır."),
                sc(10, "On-demand mod küçük yükü kolayca karşılar. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(5, "Serverless. 5 puan kırıldı: ekip SPARQL bilgisinden vazgeçer ve aylık genişletme hattını yeni bir araçla yazar."),
                sc(10, "İstek başına ödenir; saniyede 40 kontrol çok ucuzdur. Puan kırılmadı.")],
        "aur": [sc(5, "Üçlüler (subject, predicate, object) table'ında saklanır. 5 puan kırıldı: IRI'ler ve tipler metin olur; RDF'in modeli bir genel table'a sıkıştırılır."),
                sc(5, "WITH RECURSIVE hiyerarşiyi, iki join enzim yolunu gezer. 5 puan kırıldı: değişken derinlik recursive bir sorgu ve döngü kontrolü ister; bu bir pattern değil, elle yazılmış bir aramadır."),
                sc(6, "Genel üçlü table'ı yeni predicate'i kabul eder. 4 puan kırıldı: ya bu genel table'da tip ve kısıt kaybolur ya da her yeni predicate bir şema değişikliğidir."),
                sc(6, "Index'ler ve recursive SQL var. 4 puan kırıldı: property path, adlandırılmış graph ve RDF yükleyici yoktur; sürümler bir kolonla ayrılır."),
                sc(10, "Saniyede 40 kontrol küçüktür. Puan kırılmadı."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(6, "Yönetilen ve tanıdık. 4 puan kırıldı: ekip SPARQL sorgularını SQL'e yeniden yazar ve bir RDF yükleme işi kurar."),
                sc(9, "Serverless v2 ACU-saat başına ödenir ve düşük trafikte küçülür. 1 puan kırıldı: en düşük ACU gece de ödenir.")],
    },
    h2h={
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB'nin cevabı akıllıcadır: bütün ilaç çiftlerinin etkileşimleri her ay dışarıda hesaplanıp item olarak yazılırsa kontrol tek bir BatchGetItem'dır, hızlı ve çok ucuzdur (R2, R5). "
               "Ama ontoloji bu şekilde düzleştirilir: IRI'ler, sınıf hiyerarşisi ve nedeni gösteren yol kaybolur, yalnız sonuç kalır (R1.1, R1.2). Her ay genişletmeyi yapan başka bir araç ve onun hattı gerekir ve ekip SPARQL bilgisinden vazgeçer (R4). Bir sınıf düzeyinde yeni bir etkileşim eklendiğinde bütün çiftler yeniden hesaplanana kadar kontrol eski bilgiyle çalışır. "
               "Hangi koşul değişseydi DynamoDB seçilirdi: kontrol saniyede binlerce olsaydı ve \"neden\" yolu gerekmeseydi; o zaman doğru mimari ikisi birliktedir: ontoloji Neptune'de, gecelik genişletilmiş çiftler DynamoDB'de.",
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Aurora RDF üçlülerini bir table'da tutabilir ve WITH RECURSIVE hiyerarşiyi gezebilir; dayanıklılık ve işletim güçlüdür. "
               "Ama RDF'in modeli genel bir üçlü table'ına sıkıştırılır: tipler ve kısıtlar kaybolur, property path, adlandırılmış graph ve RDF yükleyici yoktur, her yeni predicate ya tipsizdir ya da bir şema değişikliğidir (R1). "
               "Ekip SPARQL sorgularını SQL'e yeniden yazar ve her ay bir RDF dosyasını table'lara çeviren bir yükleme işi kurar (R4); Aurora'nın tanıdık işletimi bu farkı kapatmaz. "
               "Hangi koşul değişseydi Aurora seçilirdi: etkileşimler bir ontolojiden değil, sabit bir ilaç çifti listesinden gelseydi ve hiyerarşi iki seviyede kalsaydı; o zaman iki table ve iki join yeterlidir.",
    },
    verdict="Karar: Neptune {np}, DynamoDB {ddb}, Aurora {aur}. Bu iş yüküne en uygun servis Neptune'dür ve fark büyüktür: veri bir RDF ontolojisidir, Neptune onu doğrudan saklar ve SPARQL ile hiyerarşiyi ve enzim yolunu tek sorguda gezer. "
            "Neptune seçtiğimizde artımız: ontoloji her ay olduğu gibi yüklenir, yeni predicate'ler şema değişikliği istemez, cevap nedenini gösterir ve ekip bildiği dili kullanır. "
            "Eksimiz: en az iki instance gece gündüz ödenir ve hiyerarşi her kontrolde yeniden gezilir; uygulama sık kullanılan genişletmeleri yükleme sırasında önceden yazabilir. Bir koşul değişseydi: kontrol saniyede binlerce olsaydı ve yol gerekmeseydi genişletilmiş çiftler DynamoDB'de durur, Neptune onların kaynağı olurdu."))

USECASES_W["neptune"] = NEPTUNE_W
PAGE_SVC["neptune"] = "np"


# ====================================================================== Amazon OpenSearch Service (page id "opensearch"), Turkish, model 2
# The ten M2 cards of templates/e2e/opensearch.tr.html. The five M7 simulations are built from the cards (sim="w_...").
# "os" is an OpenSearch Service managed domain (the Lale Market form: dbws-search); "oss" is OpenSearch Serverless. They are
# twins of one engine: the same R1 points on every card; only R2-R5 separate them. A feature that the engine has but
# Serverless leaves out (Alerting, Anomaly Detection, Security Analytics, ISM) is packaging and is counted in R4 (decisions.md rule 5).
# Card "facets" is the same workload as DocumentDB card 8 ("search"): the same story, rows, weights and points (asserted below);
# only the reasons name this page's features.
# The same mechanism gets the same reduction on this page:
#  - a search copy that must be rebuilt from the system of record: R3 8 when the rebuild takes hours, 9 when it takes minutes;
#    Serverless keeps the data in managed storage: R3 10; a store that holds the record itself: 10.
#  - the peak of a managed domain (data nodes are added before a campaign and take shards in minutes): R2 9; node sizing is R4.
#  - node-hours of a domain that runs day and night for a small or new load: R5 5-6; added to the existing dbws-search domain: 8.
#  - an update re-indexes the whole document (Ö8): OY 9 at about one update per second; 4 at hundreds per second (ElastiCache card 10).
#  - Aurora as a second copy of a catalog that lives in DocumentDB: R4 4 (DocumentDB card 8).
# Sources (the hedges are the hedges of the source):
#  - inverted index, BM25, 5 primary shards and 1 replica by default on OpenSearch Service, "you can't easily change the number of
#    primary shards", shard size "10-30 GiB ... search latency" and "30-50 GiB for write-heavy workloads such as log analytics":
#    https://docs.opensearch.org/latest/getting-started/intro/ , https://docs.aws.amazon.com/opensearch-service/latest/developerguide/bp-sharding.html
#  - refresh "The default refresh interval is one second", "eventual read consistency":
#    https://docs.aws.amazon.com/opensearch-service/latest/developerguide/bp.html
#  - fuzziness AUTO (0-2 characters exact, 3-5 one edit, 6+ two edits): https://docs.opensearch.org/latest/query-dsl/fuzziness/
#  - a field type cannot change after the first mapping: https://docs.opensearch.org/latest/mappings/
#  - hourly automated snapshots, "retains up to 336 of them for 14 days":
#    https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-snapshots.html
#  - UltraWarm, cold storage, ISM: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ism.html
#  - Serverless: refresh "approximately 10 seconds", shards and refresh not modifiable, some plugins and APIs not supported
#    https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-overview.html ; the supported API list
#    (no _plugins/_alerting, _anomaly_detection, _security_analytics, _ism) https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-genref.html ;
#    NextGen collections "scale to zero after 10 minutes of inactivity", data in managed storage https://aws.amazon.com/opensearch-service/pricing/
#  - Anomaly detection with Random Cut Forest: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ad.html
#  - Security Analytics, Sigma rules, detectors, findings: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/security-analytics.html
#  - OpenSearch Ingestion from Aurora (CDC): https://docs.aws.amazon.com/opensearch-service/latest/developerguide/configure-client-aurora.html
#  - CloudWatch: metric retention (under 60 s for 3 hours, 1 min 15 days, 5 min 63 days, 1 hour 455 days)
#    https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html ; Logs Insights is priced by the data
#    scanned https://aws.amazon.com/cloudwatch/faqs/ ; field indexes for equality https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatchLogs-Field-Indexing.html
#  - pgvector HNSW and IVFFlat on Aurora PostgreSQL: https://docs.aws.amazon.com/prescriptive-guidance/latest/retrieval-augmented-generation-options/rag-custom-retrievers.html
#  - Prices, Price List API, eu-central-1, 2026-10-26: r6g.large.search $0.202/h, m6g.large.search $0.153/h, gp3 $0.1452/GB-month;
#    Serverless OCU $0.339/OCU-hour, hot storage $0.36/GB-month, warm $0.026/GB-month; CloudWatch Logs ingestion $0.63/GB,
#    Logs Insights $0.0063/GB scanned, custom metric $0.30/metric-month (first 10,000); Timestream for InfluxDB
#    db.influx.medium Multi-AZ $0.289/h.
#  - DocumentDB text index ("Only English language is supported with text index"): https://docs.aws.amazon.com/documentdb/latest/devguide/text-search.html
CATEGORY.setdefault("oss", ("serverless search engine", "sunucusuz search engine"))
LINK.setdefault("oss", "opensearch")       # OpenSearch Serverless is the twin of the managed domain, taught on this page (M5, C2)
CATEGORY.setdefault("cw", ("monitoring service (logs and metrics)", "izleme servisi (log ve metrik)"))
LINK.setdefault("cw", "opensearch")        # CloudWatch has no page; this page (cards 5, 7, 10, M5) compares it

OPENSEARCH_W = []

# ------------------------------------------------------------------ 1. product search with typos (OpenSearch wins on its engine)
OPENSEARCH_W.append(wusecase("search", 1, sim="w_search",
    title="Yazım hatalarına dayanıklı ürün araması (Lale Market)",
    key="Index: products. Document: _id ürün id'si; name ve description text (tr_folded analyzer), category ve brand keyword, price ve rating sayı.",
    story="Lale Market'in arama kutusuna günde 400.000 arama yazılır; kampanya akşamı saniyede 300 aramaya çıkar, normalde saniyede 30'dur. Ziyaretçiler telefondan yazar: \"kulaklk\" (bir harf eksik), \"kablosuz kulaklik\" (Türkçe harfsiz), \"alpen kulaklık siyah\". "
          "Arama kelimelerin sırasından bağımsız olmalı ve en uygun ürünü önce göstermelidir. Katalog DocumentDB'de yaşar ve kayıt sistemi odur; bugün 200 ürün var, iki yıl içinde 200.000 ürün hedefleniyor. "
          "Günde yaklaşık 2.000 ürün değişikliği olur ve her biri birkaç saniye içinde aramada görünmelidir. Arama katmanı kaybolursa katalogdan bir saatte yeniden kurulabilir. "
          "İki backend geliştiricisi var; biri önceki işinde Elasticsearch kullandı. Ürün yöneticisi \"sıfır sonuç\" oranını yüzde 2'nin altına indirmek istiyor; bugün yazım hatalı aramaların çoğu boş sayfa veriyor.",
    wnote="R1 toplam 46: aramanın kendisi (EY 18), onu her katalog boyutunda hızlı tutan algoritma (DA 14) ve Türkçe harf ve yazım hatası kurallarını ayarlayan araçlar (AO 14) bu iş yükünün tanımıdır. "
          "R2 20 ile ikinci: kampanya akşamı on kat trafik ve 100 ms sınırı. R4 15: iki kişilik ekip. Arama katmanı bir kopya olduğu için R3 7'de kalır.",
    rows=[
        row("EY", 18, "Arama kutusu mağazanın girişidir ve her ziyaretçi onu kullanır; boş sonuç doğrudan kayıp satıştır.",
            "\"kulaklk\" (bir harf eksik) ve \"kulaklik\" (Türkçe harfsiz) aramaları \"Kablosuz Kulaklık\" ürünlerini bulmalı. Kelime sırası önemli olmamalı. Adında iki kelime geçen ürün, açıklamasında bir kelime geçen üründen önce gelmeli.",
            "Boş sonuç sayfası satış kaybıdır: ürün vardır ama ziyaretçi onu bulamaz ve siteyi terk eder. Sonuçlar alfabetik ya da rastgele sıralanırsa ziyaretçi aradığını ilk ekranda görmez."),
        row("DA", 14, "Katalog bin kat büyüyecek; arama süresi bu büyümeye dayanmalı.",
            "Bir aramanın süresi katalogdaki ürün sayısıyla doğrusal artmamalı: 200 üründe de 200.000 üründe de sadece aranan kelimeleri içeren ürünler okunmalı ve sıralanmalı.",
            "Her aramada bütün ürünleri okuyan bir yöntem 200 üründe hızlıdır, 200.000 üründe saniyeler sürer ve kampanya akşamı sunucuyu doldurur."),
        row("AO", 14, "Türkçe harf kuralı ve yazım hatası toleransı bir kez doğru kurulmalı; her sorguda kodla çözülürse hatalar tekrar tekrar çıkar.",
            "ı/i, ş/s, ğ/g eşleşmesi, yazım hatası toleransı, ad alanının açıklamadan ağır sayılması ve \"neden bu sıra\" sorusunun cevabı engine'in kendi ayarlarıyla yapılabilmeli.",
            "Bu kurallar uygulama kodunda yazılırsa her yeni kural bir kod değişikliğidir ve sıralamanın nedeni görünmez; ürün yöneticisi sıfır sonuç oranını ölçemez ve düzeltemez."),
        row("R2", 20, "Kampanya akşamı on kat trafik ve 100 ms sınırı: yavaş arama, ziyaretçinin ikinci harfi yazmadan vazgeçmesidir.",
            "Normalde saniyede 30, kampanya akşamı saniyede 300 arama. Her cevap 100 ms'nin altında. Katalog 200 üründen 200.000 ürüne büyüyecek; tasarım değişmemeli.",
            "Arama ziyaretçinin yazarken beklediği ekrandır; tepe anında yavaşlarsa kampanyanın en değerli saati kaybolur."),
        row("R3", 7, "Arama katmanı katalogun bir kopyasıdır; kaybı vitrini bir süre boşaltır ama veri kaybı değildir.",
            "Arama katmanı kaybolursa katalogdan bir saatte yeniden kurulabilir. Bir Availability Zone arızası aramayı durdurmamalı.",
            "Bir saatlik boş arama kutusu satış kaybıdır; ama kayıt sistemi DocumentDB'de olduğu için hiçbir ürün kaybolmaz."),
        row("R4", 15, "İki kişilik backend ekibi; ama bu, engine uyumundan sonra gelir.",
            "İki backend geliştiricisi; biri Elasticsearch biliyor. Sunucu yaması, yedek ve node değişimi istenmiyor. Katalogdaki değişiklikler aramaya kod yazmadan akmalı.",
            "Küçük bir ekipte arama altyapısını işletmek ürün geliştirmeden çalınan zamandır; elle yazılmış bir kopyalama işi her katalog değişikliğinde kırılabilir."),
        row("R5", 12, "Arama gelir getiren bir özelliktir; sabit bir aylık bütçe kabul edilir.",
            "Gün içinde düz, kampanya akşamı tepe. Arama katmanı için aylık sabit bir bütçe kabul edilir; katalog büyüdükçe maliyet öngörülebilir artmalı.",
            "Sabit maliyet kabul edilir, ama büyüme sürpriz bir fatura yaratmamalı ve küçük katalog için büyük bir sunucu filosu ödenmemeli."),
    ],
    cands=["os", "aur", "doc"],
    scores={
        "os": [sc(10, "Analyzer \"kulaklik\"i ve \"kulaklık\"ı aynı token'a çevirir (Ö1), fuzziness AUTO \"kulaklk\"i bir edit farkla eşleştirir (Ö4) ve BM25 iki kelimeli adı öne koyar (Ö3); canlı index'te \"kulaklk\" fuzziness ile 5, onsuz 0 ürün buldu (B2). Puan kırılmadı."),
               sc(10, "Inverted index her token için posting list'i hazır tutar (Ö2): \"kablosuz kulaklik\" iki index entry'si okur, ürün adlarını okumaz; 200.000 üründe de aynı iki entry okunur. Puan kırılmadı."),
               sc(9, "Custom analyzer (lowercase turkish + asciifolding), alan ağırlığı (name^3), synonym filtresi ve explain engine'in araçlarıdır (Ö1, Ö3). 1 puan kırıldı: Türkçe harf kuralı hazır gelmez, custom analyzer olarak bir kez tasarlanır ve ağırlıklar ölçülerek ayarlanır."),
               sc(9, "Shard'lar ve replica'lar arama yükünü data node'lara paylaştırır (Ö7); 100 ms 300 arama için rahattır. 1 puan kırıldı: kampanya için data node'lar önceden eklenir; yeni node'un shard'ları alması dakikalar sürer."),
               sc(8, "Replica shard'lar başka AZ'dedir; bir node ya da AZ arızasında arama sürer (Ö7). 2 puan kırıldı: domain kaybolursa katalog OpenSearch Ingestion ile baştan yüklenir ve bu yaklaşık bir saat sürer (bir saat ve üstü: 2 puan)."),
               sc(6, "Yönetilen domain: yama ve yedek AWS'tedir; DocumentDB'deki değişiklikler OpenSearch Ingestion ile index'e akar. 4 puan kırıldı: mapping, analyzer, shard sayısı ve node tipi ekibin işidir ve ekibin yalnız biri bu engine'i biliyor."),
               sc(6, "Data node'lar saat başına ödenir; gün içinde yük düzdür ve node'lar boş durmaz, kampanya tepesi için kapasite R2'de sayıldı. 4 puan kırıldı: üç AZ'lik bir domain gece de çalışır ve küçük katalog için fatura sabittir.")],
        "aur": [sc(6, "to_tsvector('turkish', ...) ve tsquery kelime araması yapar, pg_trgm benzerliği yazım hatasını yakalar, unaccent harfleri sadeleştirir. 4 puan kırıldı: yazım hatası ve kelime araması iki ayrı mekanizmadır; ikisini tek bir sıralamada birleştiren sorgu elle yazılır."),
                sc(7, "GIN index tsvector'ü ve trigram'ları index'ler; aday row'lar hızlı bulunur. 3 puan kırıldı: ts_rank her eşleşen row için ayrı hesaplanır; \"kulaklık\" gibi sık bir kelime 200.000 üründe binlerce row'u sıralamaya sokar."),
                sc(6, "Text search configuration, setweight ile A-D ağırlıkları ve ts_rank'in normalizasyon seçenekleri vardır. 4 puan kırıldı: alan ağırlıkları dört harfle (A-D) sınırlıdır, eş anlamlı sözlüğü hazır gelmez ve \"neden bu sıra\" sorusunu açıklayan bir araç yoktur. Yazım hatasının ayrı bir mekanizma olması R1.1'de sayıldı."),
                sc(9, "Reader instance'lar arama yükünü paylaşır. 1 puan kırıldı: beklenmeyen bir tepe yeni reader'ın eklenmesini dakikalarca bekler."),
                sc(10, "Aurora'daki kopya üç AZ'de altı kopya olarak saklanır. Puan kırılmadı."),
                sc(4, "Aurora Lale Market'te siparişler için çalışır. 6 puan kırıldı: katalog DocumentDB'dedir; arama için Aurora'ya bir kopya ve onu besleyen bir boru hattı gerekir ve tsvector, pg_trgm ve unaccent ekibin yeni işidir."),
                sc(7, "Var olan cluster'a reader eklenir. 3 puan kırıldı: kampanya reader'ları ve arama sorgularının CPU'su ACU olarak ödenir.")],
        "doc": [sc(3, "DocumentDB'nin text index'i $text ile kelime araması yapar. 7 puan kırıldı: AWS'e göre text index \"Only English language\" destekler, Türkçe harf kuralı yoktur ve yazım hatası toleransı yoktur; \"kulaklk\" hiçbir şey bulmaz."),
                sc(5, "Text index kelimelerden document'lara giden bir index'tir. 5 puan kırıldı: collection başına tek bir text index kurulur ve sıralama yalnız terim sıklığına dayanır."),
                sc(3, "$meta textScore ile skor okunur, alan ağırlığı verilebilir. 7 puan kırıldı: custom analyzer, synonym ve yazım hatası ayarı yoktur; kurallar uygulamada yazılır."),
                sc(9, "Okumalar replica'lara dağılır. 1 puan kırıldı: beklenmeyen bir tepe yeni replica'nın eklenmesini dakikalarca bekler."),
                sc(10, "Katalog zaten DocumentDB'de ve kalıcıdır; ayrı bir kopya yoktur. Puan kırılmadı."),
                sc(9, "Var olan cluster ve bilinen API; ikinci bir sistem ve boru hattı yoktur. 1 puan kırıldı: text index ve arama sorguları için replica sayısını ekip seçer."),
                sc(8, "Var olan cluster kullanılır. 2 puan kırıldı: kampanya için eklenen replica'lar instance saati olarak ödenir.")],
    },
    h2h={
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora gerçek bir adaydır: PostgreSQL'in tam metin araması Türkçe bir text search configuration ile kelimeleri köklerine indirir, pg_trgm yazım hatasını benzerlikle yakalar ve GIN index ikisini de hızlandırır. "
               "Ama bu iki ayrı mekanizmadır: kelime araması bir yerde, yazım hatası başka bir yerde çalışır ve ikisini tek bir sıralamada birleştiren sorgu elle yazılır; ts_rank her eşleşen row'u ayrı puanlar. R1'de 46 puanın 29'unu alır, OpenSearch 44,6'sını. "
               "Servis tasarımında da geridedir: katalog DocumentDB'de olduğu için Aurora'ya ikinci bir kopya ve onu besleyen bir boru hattı gerekir (R4). "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: katalog zaten Aurora'da olsaydı, aramalar az (saniyede birkaç) ve kelimeler tam yazılmış olsaydı ve ekip ikinci bir servis işletmek istemeseydi; o zaman bir tsvector column'u yeterdi.",
        "doc": "Document (DocumentDB) ile kafa kafaya. DocumentDB'nin artısı kataloğun zaten orada olmasıdır: kopya, boru hattı ve ikinci bir sistem yoktur ve ekip API'yi bilir; R3, R4 ve R5'te öndedir. "
               "Ama bu kartın sorusu bir metin arama sorusudur ve DocumentDB'nin text index'i AWS'e göre yalnız İngilizceyi destekler, yazım hatası toleransı ve custom analyzer yoktur, collection başına tek bir text index kurulur. \"kulaklk\" ve \"kulaklik\" aramaları boş döner, yani ürün yöneticisinin hedefi karşılanmaz. R1'de 46 puanın 16,6'sını alır. "
               "Bu yüzden doğru mimari ikisi birliktedir: katalog DocumentDB'de kayıt sistemi olarak kalır, arama kopyası OpenSearch'te yaşar. "
               "Hangi koşul değişseydi DocumentDB seçilirdi: arama yalnız İngilizce ürün kodları ve tam kelimelerle yapılsaydı ve sıralama önemli olmasaydı.",
    },
    verdict="Karar: OpenSearch {os}, Aurora PostgreSQL {aur}, DocumentDB {doc}. Kararı R1 verir: analyzer, inverted index, fuzziness ve BM25 bu iş yükünün kendisidir ve R1'in 46 puanının 44,6'sını OpenSearch alır. "
            "OpenSearch seçtiğimizde artımız: yazım hatalı ve Türkçe harfsiz aramalar bulur, en uygun ürün önce gelir, 200.000 üründe de arama aynı sayıda index entry'si okur. "
            "Eksimiz: ikinci bir sistem işletiriz; DocumentDB'den gelen değişiklikleri OpenSearch Ingestion ile akıtırız ve kopyanın kopabileceğini izleriz; analyzer ve shard sayısını baştan doğru seçeriz, çünkü bir alanın analyzer'ı değişirse index yeniden kurulur. "
            "Doğru mimari ikisi birliktedir: katalog DocumentDB'de, arama kopyası OpenSearch'te. "
            "Bir koşul değişseydi: aramalar yalnız tam kelimeyle ve az sayıda yapılsaydı kataloğun bulunduğu database'in kendi araması yeterdi."))

# ------------------------------------------------------------------ 2. faceted navigation: the same workload as DocumentDB card 8 (OpenSearch wins R1, DocumentDB the total)
_DS = next(uc for uc in DOCDB_W if uc["id"] == "search")
OPENSEARCH_W.append(wusecase("facets", 2, sim="w_facets",
    title=_DS["title"][1],
    key=_DS["key"][1],
    story=_DS["story"][1].replace("(kart 1)", "(DocumentDB sayfasının kart 1'i)"),
    wnote=_DS["wnote"][1] + " Bu kart DocumentDB sayfasının kart 8'iyle aynı iş yüküdür ve aynı satırları, ağırlıkları ve puanları taşır. Hikâye kart 1'den önceki durumdur: henüz bir OpenSearch domain'i yoktur ve ekip OpenSearch bilmez.",
    rows=[row(r["code"], r["w"], r["wwhy"][1], r["want"][1], r["why"][1]) for r in _DS["rows"]],
    cands=["doc", "os", "aur"],
    scores={
        "doc": [sc(8, "find dot notation ile iç içe field'lara filtreler; sık birleşimlere compound index kurulur ({ category: 1, 'attributes.renk': 1, rating: -1 }). 2 puan kırıldı: 20 field'ın her birleşimine index kurulamaz; bazı birleşimler index'in bir kısmını kullanır ve kalan koşulu document üzerinde test eder."),
                sc(6, "Facet sayıları $match ve $group ile bir aggregation pipeline'dır ve başındaki $match index kullanır. 4 puan kırıldı: her filtre değişiminde her facet için bir pipeline çalışır; sayılar sonuç kümesinin document'ları okunarak hesaplanır."),
                sc(6, "B-tree index bir field sırasını hızlı verir. 4 puan kırıldı: her index tek bir sıradır; serbest birleşimler ve sayım için engine birkaç index'i birleştirmez, ya bir index'i kısmen kullanır ya da document okur."),
                sc(10, "Yeni filtre field'ı sadece yeni document'lara yazılır; index'i istenince kurulur. Puan kırılmadı."),
                sc(7, "Filtreli okumalar replica'lara dağılır. 3 puan kırıldı: kampanyada saniyede 5.000 filtre ve facet pipeline'ı replica'ların CPU'sunu doldurur; 50 ms her birleşimde garanti değildir."),
                sc(10, "Katalog zaten DocumentDB'de ve kalıcıdır; ayrı bir arama katmanı yoktur. Puan kırılmadı."),
                sc(9, "Var olan cluster ve bilinen API; ikinci bir sistem ve boru hattı yoktur. 1 puan kırıldı: facet yükü için replica sayısını ve index'leri ekip seçer."),
                sc(8, "Var olan cluster kullanılır. 2 puan kırıldı: kampanya için eklenen replica'lar instance saati olarak ödenir.")],
        "os": [sc(10, "Bir bool sorgusu her field birleşimini filtre olarak uygular, sıralar ve sayfalar; iç içe field'lar da aynı biçimdedir (Ö2). Puan kırılmadı."),
               sc(10, "Aggregation'lar facet sayılarını aynı sorgunun içinde, doc values üzerinden verir (Ö5); canlı index'te bir sorgu 20 ürünü ve 8 kova sayısını birlikte döndürdü (B4). Puan kırılmadı."),
               sc(10, "Inverted index her field'ı ayrı index'ler ve sorgu anında posting list'leri kesiştirerek birleştirir (Ö2); birleşim başına bir yapı gerekmez. Puan kırılmadı."),
               sc(8, "Dynamic mapping yeni field'ı tanır (A2). 2 puan kırıldı: field'ın type'ı ilk yazmada sabitlenir; yanlış tahmin edilen bir type reindex ister."),
               sc(9, "Shard'lar ve replica'lar filtre yükünü paylaşır (Ö7); 50 ms filtre ve facet için rahattır. 1 puan kırıldı: kampanya için node'lar önceden eklenir; yeni node'un shard'ları alması zaman ister."),
               sc(8, "Shard replica'ları başka AZ'dedir (Ö7). 2 puan kırıldı: arama kopyası kaybolursa kataloğun tamamı yeniden index'lenir (saatler)."),
               sc(3, "Yönetilen domain. 7 puan kırıldı: ekip OpenSearch bilmiyor; mapping, shard boyutu ve kataloğu change stream'den besleyen boru hattı ekibin yeni işidir ve iki sistem birbirinden kopabilir."),
               sc(5, "Node'lar saat başına ödenir. 5 puan kırıldı: domain katalog cluster'ına ek olarak bütün gün çalışır.")],
        "aur": [sc(9, "SQL her column'da ve JSONB'nin içinde filtreler, sıralar ve sayfalar. 1 puan kırıldı: iç içe field'lara göre aralık JSON yolu ve cast ister."),
                sc(6, "Facet sayıları GROUP BY ile bir sorgudur. 4 puan kırıldı: her filtre değişiminde her facet için bir GROUP BY çalışır ve sonuç row'larını okur."),
                sc(7, "Planner birkaç B-tree index'ini bitmap ile birleştirebilir; GIN JSONB eşitliklerini index'ler. 3 puan kırıldı: sayım yine row'ları okur ve iç içe aralıklar her field için expression index ister."),
                sc(7, "JSONB yeni field'ı migration'sız alır. 3 puan kırıldı: index'lenecek her iç içe field için yeni bir expression index kurulur."),
                sc(7, "Reader instance'lar okumayı paylaşır. 3 puan kırıldı: kampanyada 5.000 filtre ve GROUP BY reader'ların CPU'sunu doldurur."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(4, "Aurora Lale Market'te çalışır. 6 puan kırıldı: katalog DocumentDB'dedir; arama için Aurora'ya bir kopya ve onu besleyen bir boru hattı gerekir ve filtre sorguları JSONB yollarıyla yeniden yazılır."),
                sc(7, "Var olan cluster'a reader eklenir. 3 puan kırıldı: kampanya reader'ları ACU olarak ödenir.")],
    },
    h2h={
        "os": "Search engine (OpenSearch) ile kafa kafaya. Bu kartta R1'i OpenSearch kazanır: inverted index her field'ı ayrı index'ler ve sorgu anında birleştirir, facet sayıları aynı sorgunun içinde gelir ve R1'in 42 puanının 40,8'ini alır; DocumentDB 30,4 alır. Bu, engine'in açık bir üstünlüğüdür. "
              "Toplamı DocumentDB'ye veren R4 ve R5'tir: katalog zaten DocumentDB'dedir, ekip OpenSearch bilmez ve ikinci bir sistem, onu besleyen bir change stream boru hattı ve bütün gün çalışan node'lar ister; fark sadece 0,8 puandır. "
              "Bu yakın yarış bir uyarıdır: metin araması (yazım hatası toleransı, relevance) istendiği gün iş yükü kart 1'e döner; orada DocumentDB'nin text index'i çok zayıftır ve OpenSearch net kazanır. O gün kurulan OpenSearch domain'i facet'leri de taşır. "
              "Hangi koşul değişseydi OpenSearch seçilirdi: metin araması bu çeyrekte istenseydi ya da filtre field'ları 50'yi geçseydi; o gün katalog DocumentDB'de kalır ve arama kopyası change stream ile OpenSearch'e akar.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora'nın planner'ı birkaç index'i bir sorguda birleştirebilir (bitmap) ve SQL her filtreyi ve GROUP BY ile facet'i cevaplar; R1'de DocumentDB ile neredeyse eşittir. "
               "Ama katalog Aurora'da değildir: arama için kataloğun bir kopyası Aurora'ya yazılır, bir boru hattı onu güncel tutar ve sorgular JSONB yollarıyla yeniden yazılır. Bu R4'te altı puanlık bir kayıptır ve Aurora'nın engine kazancını siler. Facet sayıları her iki engine'de de sonuç row'larını okur; OpenSearch'ün doc values'u bu işte ikisinden de iyidir. "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: katalog zaten Aurora'da olsaydı (Aurora sayfasının kart 2'sindeki gibi) ve filtreler birkaç sabit field olsaydı.",
    },
    verdict="Karar: DocumentDB {doc}, OpenSearch {os}, Aurora PostgreSQL {aur}. Bu yakın bir yarıştır ve R1'i OpenSearch kazanır; toplamı DocumentDB'ye var olan cluster, ekibin bildiği API ve ikinci bir sistemin olmaması verir (R4, R5). "
            "Yine de OpenSearch seçersek artımız: her filtre birleşimi ve facet sayıları tek bir sorguda, kampanyada da 50 ms'nin altında gelir ve metin araması geldiği gün altyapı hazırdır. "
            "Eksimiz: ekip yeni bir engine öğrenir; kataloğu DocumentDB'den OpenSearch'e akıtan boru hattını işletiriz ve kopyanın kopmadığını izleriz; domain bütün gün ödenir. "
            "Bu kart DocumentDB sayfasının kart 8'iyle aynı iş yüküdür ve aynı puanları taşır. "
            "Bir koşul değişseydi: metin araması istendiği gün doğru cevap ikisi birlikte çalışmaktır: katalog DocumentDB'de, arama kopyası change stream ile OpenSearch'te."))
for _c in ("doc", "os", "aur"):   # same workload on two pages: same points (decisions.md)
    assert [p for p, _ in OPENSEARCH_W[-1]["scores"][_c]] == [p for p, _ in _DS["scores"][_c]], _c

# ------------------------------------------------------------------ 3. autocomplete (OpenSearch wins; ElastiCache wins speed)
OPENSEARCH_W.append(wusecase("suggest", 3,
    title="Arama kutusunda otomatik tamamlama",
    key="Index: suggest. Document: bir öneri (ürün adı ya da popüler arama), alanları text (search_as_you_type, tr_folded) ve popularity (sayı).",
    story="Ziyaretçi arama kutusuna iki harf yazdığı andan itibaren her tuş vuruşunda en fazla 8 öneri görmelidir. Bir arama ortalama beş tuş vuruşu olduğu için öneri trafiği aramanın beş katıdır: normalde saniyede 1.500, kampanya akşamı saniyede 6.000 istek. "
          "Öneriler iki kaynaktan gelir: 200.000 ürün adı ve son 30 günün en popüler 50.000 araması; liste her gece yeniden kurulur. Ziyaretçi \"kabl\", \"kulakl\" ya da \"kablsz\" yazabilir; Türkçe harfsiz ve bir harf hatalı önekler de doğru öneriyi bulmalı ve popüler öneri önce gelmelidir. "
          "Her öneri sunucuda 50 ms içinde dönmelidir. Kart 1'in OpenSearch domain'i zaten çalışıyor; ElastiCache oturumlar için, Aurora siparişler için çalışıyor. Ekip iki backend geliştiricisidir.",
    wnote="R1 toplam 44: öneki ve yazım hatasını birlikte bulmak (EY 18), her tuş vuruşunda cevap süresi (DA 14) ve popülerliğe göre sıralamak (AO 12) bu iş yükünün tanımıdır. "
          "R2 22 ile ikinci: öneri trafiği aramanın beş katıdır. Öneri listesi her gece yeniden kurulduğu için R3 5'te kalır.",
    rows=[
        row("EY", 18, "Öneri kutusu her ziyaretçinin her tuş vuruşunda çalışır; yanlış ya da boş öneri ziyaretçiyi yanlış aramaya götürür.",
            "\"kabl\", \"kablosuz kul\" ve \"kablsz\" (bir harf hatalı) önekleri \"Kablosuz Kulaklık\" önerisini bulmalı; Türkçe harfsiz yazım da eşleşmeli. Önek kelimenin başında ya da ikinci kelimede olabilir.",
            "Yalnız tam önek eşleşirse telefondan yazan ziyaretçi bir harf hatasıyla hiçbir öneri görmez; öneri kutusu tam ihtiyaç olduğu anda boş kalır."),
        row("DA", 14, "Her tuş vuruşu bir istektir; öneri yazmaktan yavaşsa işe yaramaz.",
            "Bir öneri isteği sunucuda 50 ms içinde dönmeli; süre öneri listesinin büyüklüğünden (250.000 öneri) bağımsız olmalı.",
            "Öneri 50 ms'den geç gelirse ziyaretçi bir sonraki harfi çoktan yazmıştır; eski öneri ekranda titrer ve yanlış öneriye tıklanır."),
        row("AO", 12, "Popüler öneri önce gelmezse öneri kutusu satış getirmez.",
            "Öneriler popülerliğe göre sıralanmalı: aynı önekle \"kablosuz kulaklık\" (günde 3.000 arama) \"kablo kanalı\"ndan (günde 10 arama) önce gelmeli. Kampanya ürünü bir hafta öne alınabilmeli.",
            "Alfabetik öneri en çok aranan ürünü sona iter; kampanya ürünü öne alınamazsa pazarlama ekibi öneri kutusunu kullanamaz."),
        row("R2", 22, "Öneri trafiği aramanın beş katıdır ve kampanya akşamı dört kat sıçrar.",
            "Normalde saniyede 1.500, kampanya akşamı saniyede 6.000 öneri isteği; her biri 50 ms içinde.",
            "Tepe anında yavaşlayan öneri kutusu kampanya akşamının bütün aramalarını yavaşlatır."),
        row("R3", 5, "Öneri listesi her gece ürünlerden ve arama günlüğünden yeniden kurulur; kaybı yalnız birkaç dakikalık öneri yokluğudur.",
            "Öneri verisi kaybolursa birkaç dakikada yeniden yüklenebilir; o sürede arama kutusu önerisiz çalışabilir.",
            "Önerisiz birkaç dakika satış kaybı değildir; arama yine çalışır."),
        row("R4", 15, "İki kişilik ekip yeni bir sistem işletmek istemiyor; üç servis zaten çalışıyor.",
            "Öneri özelliği zaten çalışan bir servisin üzerine kurulmalı; yeni bir sunucu ve yeni bir sorgu dili istenmiyor.",
            "Yeni bir sistem iki kişilik ekibe nöbet, izleme ve yedek işi ekler."),
        row("R5", 14, "Öneri trafiği büyüktür ama her istek küçüktür; maliyet istek sayısıyla büyümemeli.",
            "Her tuş vuruşu bir istektir; ayda yaklaşık 4 milyar istek. Fiyat bu istek sayısıyla patlamamalı.",
            "İstek başına pahalı bir model öneri kutusunu arama kutusundan daha pahalı yapar."),
    ],
    cands=["os", "ec", "aur"],
    scores={
        "os": [sc(10, "search_as_you_type alanı her kelimenin öneklerini index'ler, fuzziness \"kablsz\"i bir edit farkla eşleştirir (Ö4) ve tr_folded analyzer Türkçe harfleri sadeleştirir (Ö1). Puan kırılmadı."),
               sc(8, "Önekler index zamanında token olarak hazırlanır, sorgu posting list okur (Ö2). 2 puan kırıldı: yazım hatası ve popülerlik birlikte istendiği için öneri search_as_you_type ile skorlanan tam bir aramadır ve bellekteki bir yapıdan okumaya göre milisaniyeler fazladır. Bellekte duran completion suggester daha hızlıdır ama yazım hatalı önekte ve filtrede sınırlıdır."),
               sc(9, "function_score popularity alanıyla skoru çarpar ve kampanya ürünü bir boost ile öne alınır (Ö3). 1 puan kırıldı: metin skoru ile popülerliği dengeleyen formül ölçülerek ayarlanır."),
               sc(9, "Replica'lar öneri yükünü paylaşır (Ö7). 1 puan kırıldı: kampanya için node'lar önceden eklenir; yeni node'un shard'ları alması dakikalar sürer."),
               sc(9, "Replica shard'lar node arızasını karşılar (Ö7). 1 puan kırıldı: domain kaybolursa öneri index'i birkaç dakikada yeniden yüklenir."),
               sc(9, "Kart 1'in domain'i zaten çalışır ve ekip onu işletir; öneri bir index daha demektir. 1 puan kırıldı: search_as_you_type mapping'i ve gece yükleme işi yeni bir index tasarımıdır."),
               sc(8, "Domain zaten ödenir; istek başına ücret yoktur. 2 puan kırıldı: saniyede 6.000 öneri için domain'e bir replica ya da daha büyük node'lar eklenir.")],
        "ec": [sc(5, "Bir sorted set'te bütün öneriler score 0 ile tutulur ve ZRANGEBYLEX önekle başlayanları sırayla verir; Türkçe harfler yazarken sadeleştirilmiş bir key ile çözülür. 5 puan kırıldı: yazım hatası toleransı yoktur, \"kablsz\" hiçbir şey bulmaz; ikinci kelimedeki önek için her kelime ayrıca yazılır."),
               sc(10, "Sorted set bellektedir; önek aralığı okuması milisaniyenin altındadır ve süre listenin büyüklüğünden neredeyse bağımsızdır. Puan kırılmadı."),
               sc(6, "Popülerlik ikinci bir sorted set'in score'udur. 4 puan kırıldı: önek araması score'ları eşit tutmayı ister; popülerliğe göre sıralamak için önek başına ayrı listeler önceden hesaplanır ya da sonuçlar uygulamada yeniden sıralanır."),
               sc(10, "ElastiCache Serverless saniyede 6.000 küçük komutu kendisi karşılar. Puan kırılmadı."),
               sc(9, "Bellekteki liste yalnız bir kopyadır ve birkaç dakikada yeniden yüklenir. 1 puan kırıldı: bir arızadan sonra liste yeniden yüklenene kadar öneri yoktur (yeniden yükleme dakikalar sürerse 1, bir saat ve üstü 2 puan)."),
               sc(9, "Cache oturumlar için zaten çalışır; ekip Valkey komutlarını bilir. 1 puan kırıldı: öneri key'leri oturumlarla aynı cache'in belleğini ve ECPU'sunu paylaşır ve ikisi birlikte izlenir."),
               sc(9, "ECPU ve GB-saat başına ödenir; bir ZRANGEBYLEX küçük bir istektir. 1 puan kırıldı: her tuş vuruşu ayrı bir istektir ve fatura öneri trafiğiyle doğrusal büyür.")],
        "aur": [sc(6, "LIKE 'kabl%' bir B-tree index'iyle (text_pattern_ops) önek arar; pg_trgm yazım hatasını, unaccent Türkçe harfleri ele alır. 4 puan kırıldı: önek ve yazım hatası iki ayrı operatördür ve ikinci kelimedeki önek ayrı bir kelime tablosu ister."),
                sc(7, "B-tree önek araması birkaç sayfa okur. 3 puan kırıldı: trigram benzerliği birçok adayı okuyup puanlar; hatalı öneklerde süre on milisaniyelere çıkar."),
                sc(7, "ORDER BY popularity DESC bir index'le hızlıdır. 3 puan kırıldı: benzerlik ile popülerliği birleştiren formül SQL'de elle yazılır."),
                sc(7, "Öneri sorguları reader'lara gider. 3 puan kırıldı: kampanyada saniyede 6.000 sorgu reader'ların CPU'sunu doldurur ve reader eklemek dakikalar sürer."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(7, "Aurora çalışır ve ekip SQL bilir. 3 puan kırıldı: öneri sorguları siparişlerin cluster'ına bir reader ve pg_trgm ile unaccent extension'larını ekler."),
                sc(7, "Var olan cluster'a reader eklenir. 3 puan kırıldı: öneri trafiği için reader'lar ve ACU'lar bütün gün ödenir.")],
    },
    h2h={
        "ec": "Bellek içi key-value (ElastiCache) ile kafa kafaya. ElastiCache'in gücü hızdadır ve bu kartta açıktır: sorted set bellektedir, ZRANGEBYLEX önekle başlayan önerileri milisaniyenin altında verir ve Serverless saniyede 6.000 küçük isteği ayarsız taşır; R1 · DA'yı ve R2'yi o kazanır. "
              "Ama öneri kutusunun asıl sorusu \"ziyaretçi ne yazmak istedi\" sorusudur. Valkey'de yazım hatası toleransı yoktur, \"kablsz\" boş döner; ikinci kelimedeki önek ve popülerlik sırası için önek başına listeler önceden hesaplanır. R1 · EY'de 5, AO'da 6 alır; fark buradan gelir. "
              "Hangi koşul değişseydi ElastiCache seçilirdi: öneriler yalnız tam öneklerle (ürün kodu, şehir adı) sorulsaydı ve listeler küçük olsaydı; ya da öneri trafiği saniyede on binlere çıkıp 50 ms sınırı 5 ms'ye inseydi. "
              "O durumda ikisi birlikte de çalışabilir: en sık 1.000 önek ElastiCache'te, geri kalanı OpenSearch'te.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora önekleri B-tree ile, yazım hatalarını pg_trgm ile ve popülerliği bir ORDER BY ile verebilir; her parça çalışır ve ekip SQL bilir. "
               "Ama parçalar ayrı mekanizmalardır ve onları tek bir öneri sırasında birleştiren sorgu elle yazılır; hatalı öneklerde trigram araması birçok adayı okur. "
               "Asıl kayıp R2'dedir: öneri trafiği aramanın beş katıdır ve saniyede 6.000 küçük sorgu siparişleri taşıyan cluster'ın reader'larını doldurur. Bu, mağazanın en önemli database'ine en hafif işi yüklemektir. "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: öneri listesi birkaç bin kayıtlık bir yönetim ekranı olsaydı (saniyede birkaç istek) ve yazım hatası toleransı istenmeseydi; o zaman ayrı bir servis gereksizdir.",
    },
    verdict="Karar: OpenSearch {os}, ElastiCache {ec}, Aurora PostgreSQL {aur}. Kararı R1 · EY verir: önek, yazım hatası ve Türkçe harf kuralı birlikte yalnız search engine'de tek bir sorgudur. ElastiCache hızda ve tepe trafikte öndedir ama \"kablsz\" yazan ziyaretçiye öneri veremez. "
            "OpenSearch seçtiğimizde artımız: öneri, kart 1'in domain'inde yeni bir index'tir; aynı analyzer'lar ve aynı ekip. "
            "Eksimiz: her tuş vuruşu bir arama isteğidir; kampanyadan önce replica ekleriz, istemcide 100 ms'lik bir bekleme (debounce) koyarak istek sayısını düşürürüz ve popülerlik ağırlığını ölçerek ayarlarız. "
            "Bir koşul değişseydi: öneriler yalnız tam öneklerle sorulsaydı ElastiCache'in sorted set'i daha hızlı ve daha ucuz olurdu."))

# ------------------------------------------------------------------ 4. store finder: geo + text + filters (OpenSearch wins, close race with Aurora)
OPENSEARCH_W.append(wusecase("stores", 4,
    title="Mağaza ve teslim noktası bulucu: konum, metin ve filtre birlikte",
    key="Index: pickup_points. Document: _id nokta id'si; location geo_point, service_area geo_shape, name ve address text, services keyword listesi, open_now boolean.",
    story="Lale Market 3 mağazadan 120 mağazaya ve 2.000 kargo teslim noktasına büyüyor. Uygulamadaki \"yakınımda\" ekranı tek bir kutuda üç soruyu birlikte sorar: konum (\"5 km içinde, en yakın önce\"), metin (\"kadıköy kargo\", \"bağdat caddesi\") ve filtre (\"şimdi açık\", \"soğuk zincir hizmeti var\"). "
          "Her noktanın bir hizmet bölgesi (çokgen) vardır: \"bu adrese hangi nokta teslim eder\". Normalde saniyede 40, kampanya akşamı saniyede 400 arama; her biri 100 ms içinde. Noktaların açılış saatleri ve hizmetleri günde bir kez değişir. "
          "Noktaların kayıt sistemi Aurora'daki points table'ıdır. Kart 1'in OpenSearch domain'i zaten çalışıyor ve ekip onu işletiyor.",
    wnote="R1 toplam 40: konum, metin ve filtreyi tek bir sıralı soruda birleştirmek (EY 18), nokta ve çokgen tipleri (VM 10) ve bunu taşıyan index yapısı (DA 12). "
          "R4 18 ile ikinci: ekip mevcut sistemlerin üzerine kurmak istiyor ve yeni bir beceri öğrenmek istemiyor. R5 17: 2.000 noktalık küçük bir veri için büyük bir fatura istenmiyor.",
    rows=[
        row("EY", 18, "\"Yakınımda\" ekranının her araması üç soruyu birlikte sorar; biri eksikse ekran yanlış nokta gösterir.",
            "\"5 km içinde, şimdi açık, soğuk zincir hizmeti olan ve adında ya da adresinde 'kadıköy' geçen noktalar, en yakın önce\" tek bir sorgu olmalı; metin eşleşmesi Türkçe harfsiz de çalışmalı.",
            "Konum bir sistemde, metin başka bir sistemde aranırsa uygulama iki sonucu birleştirir ve sayfalama bozulur; Türkçe harfsiz \"kadikoy\" boş dönerse ziyaretçi noktayı bulamaz."),
        row("VM", 10, "Teslim kuralı bir çokgenle tanımlanır; nokta tek başına yetmez.",
            "Nokta (konum) ve çokgen (hizmet bölgesi) veri tipleri olmalı; \"bu adres hangi noktanın bölgesinde\" sorusu sorulabilmeli.",
            "Çokgen bir liste olarak saklanırsa \"bölgenin içinde mi\" testi uygulama kodudur ve her aramada bütün bölgeler okunur."),
        row("DA", 12, "Arama 100 ms içinde dönmeli; nokta sayısı 2.000'den 20.000'e çıkabilir.",
            "Mekânsal sorular ve metin koşulları index'lerle birkaç adımda daraltılmalı; süre nokta sayısıyla doğrusal artmamalı.",
            "Her aramada bütün noktalara mesafe hesaplanırsa 20.000 noktada ve kampanya akşamında 100 ms tutulamaz."),
        row("R2", 15, "Kampanya akşamı on kat arama; ziyaretçi kapıda bekliyor olabilir.",
            "Normalde saniyede 40, kampanya akşamı saniyede 400 arama; her biri 100 ms içinde.",
            "Tepe anında yavaşlayan bulucu, mağazaya yönelen ziyaretçiyi kaybettirir."),
        row("R3", 10, "Noktaların kaydı Aurora'dadır; arama katmanı bir kopyadır.",
            "Arama katmanı kaybolursa Aurora'dan dakikalar içinde yeniden kurulabilmeli. Bir AZ arızası aramayı durdurmamalı.",
            "Boş bir bulucu ekranı dakikalarca sürerse kampanya akşamı teslim noktası seçilemez; ama kayıt kaybolmaz."),
        row("R4", 18, "Ekip mevcut sistemlerin üzerine kurmak istiyor ve yeni bir coğrafi beceri öğrenmek istemiyor.",
            "Kart 1'in OpenSearch domain'i ve Aurora zaten çalışıyor; bulucu bunlardan birinin üzerine kurulmalı. Noktaların değişiklikleri kod yazmadan akmalı.",
            "Yeni bir sistem ya da yeni bir coğrafi beceri iki kişilik ekibe aylar ekler; elle yazılmış bir kopyalama işi açılış saatlerini eskitir."),
        row("R5", 17, "2.000 noktalık küçük bir veri için ayrı bir fatura istenmiyor.",
            "Veri küçüktür (birkaç MB); trafik dalgalıdır. Var olan bir servisin kapasitesi kullanılmalı.",
            "Küçük bir özellik için gece gündüz çalışan yeni bir filo, özelliğin getirisinden pahalıdır."),
    ],
    cands=["os", "aur", "ec"],
    scores={
        "os": [sc(10, "geo_distance filtresi, _geo_distance sıralaması, bir match sorgusu ve term filtreleri tek bir bool sorgusudur (Ö6, Ö1, Ö3); tr_folded \"kadikoy\"u \"Kadıköy\"e eşler. Puan kırılmadı."),
               sc(7, "geo_point ve geo_shape alan tipleri vardır (Ö6). 3 puan kırıldı: koordinat sistemi dönüşümleri ve geometri doğrulaması PostGIS kadar geniş değildir; \"bu adres hangi bölgede\" sorusu hizmet bölgelerini ayrı bir index'te document olarak tutan ters bir sorgu ister (Aurora sayfasının kart 10'undaki aynı kırılım)."),
               sc(10, "Mekânsal alanlar ağaç yapılı index'lerde durur ve metin koşulları posting list'lerle daraltılır (Ö2, Ö6); her iki koşul da index'ten okunur. Puan kırılmadı."),
               sc(9, "Replica'lar arama yükünü paylaşır (Ö7). 1 puan kırıldı: kampanya için node'lar önceden eklenir; yeni node'un shard'ları alması dakikalar sürer."),
               sc(9, "Replica shard'lar AZ arızasını karşılar (Ö7). 1 puan kırıldı: domain kaybolursa 2.000 nokta Aurora'dan dakikalar içinde yeniden yüklenir."),
               sc(7, "Kart 1'in domain'i çalışır ve ekip onu bilir; OpenSearch Ingestion Aurora PostgreSQL'in değişikliklerini akıtır. 3 puan kırıldı: Aurora'dan akış için logical replication açılır ve pipeline işletilir; geo mapping'i yeni bir index tasarımıdır."),
               sc(8, "Domain zaten ödenir. 2 puan kırıldı: kampanya akşamının 400 araması için domain'e kapasite eklenir.")],
        "aur": [sc(8, "ST_DWithin, ORDER BY konum <-> nokta, tsvector araması ve WHERE koşulları tek bir SQL'dir. 2 puan kırıldı: metin skoru ile mesafe sırasını birlikte veren bir sıralama elle yazılır ve Türkçe harfsiz eşleşme unaccent ister."),
                sc(10, "PostGIS geometry tipi noktayı ve çokgeni koordinat sistemiyle tutar; ST_Contains \"bu adres hangi bölgede\" sorusunu cevaplar ve geçersiz çokgen reddedilebilir. Puan kırılmadı."),
                sc(9, "GiST index mekânsal soruyu, GIN index metni daraltır. 1 puan kırıldı: planner iki index'ten birini seçer, diğer koşulu row'lar üzerinde test eder."),
                sc(9, "Arama reader'lara gider. 1 puan kırıldı: beklenmeyen bir tepe yeni reader'ın eklenmesini dakikalarca bekler."),
                sc(10, "Kayıt sistemi Aurora'dır; üç AZ'de altı kopya. Puan kırılmadı."),
                sc(7, "Noktalar zaten Aurora'dadır; kopya ve boru hattı yoktur. 3 puan kırıldı: PostGIS, GiST ve tsvector ekibin yeni becerileridir ve kampanya için bir reader eklenir."),
                sc(8, "Var olan cluster kullanılır. 2 puan kırıldı: kampanya reader'ı ve arama CPU'su ACU olarak ödenir.")],
        "ec": [sc(4, "GEOSEARCH yarıçap içindeki noktaları en yakından uzağa verir. 6 puan kırıldı: metin araması yoktur; \"şimdi açık\" ve \"soğuk zincir\" filtreleri ayrı set'lerle uygulamada kesiştirilir."),
               sc(5, "Konum index'i noktaları tutar. 5 puan kırıldı: çokgen tipi yoktur; \"bu adres hangi bölgede\" testi uygulama kodudur."),
               sc(10, "Konum index'i bellekteki bir sorted set'tir; arama milisaniyenin altındadır. Puan kırılmadı."),
               sc(10, "Serverless saniyede 400 aramayı ayarsız karşılar. Puan kırılmadı."),
               sc(9, "Bellekteki liste bir kopyadır ve 2.000 nokta Aurora'dan dakikalar içinde yeniden yüklenir. 1 puan kırıldı: bir arızadan sonra noktalar yeniden yüklenene kadar bulucu boştur (yeniden yükleme dakikalar sürerse 1, bir saat ve üstü 2 puan)."),
               sc(7, "Cache çalışır ve ekip Valkey bilir. 3 puan kırıldı: noktaları ve hizmetlerini Aurora'dan cache'e taşıyan iş yazılır ve günlük değişiklikleri o iş günceller."),
               sc(9, "ECPU ve GB-saat başına ödenir; veri çok küçüktür. 1 puan kırıldı: GEOSEARCH ve set kesişimleri basit bir GET'ten fazla ECPU harcar.")],
    },
    h2h={
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Bu yakın bir yarıştır ve Aurora güçlü bir adaydır: PostGIS nokta ve çokgen tiplerinde, \"bu adres hangi bölgede\" sorusunda ve coğrafi doğrulukta OpenSearch'ten öndedir (R1 · VM 10'a 7), noktaların kaydı zaten Aurora'dadır ve kopya gerekmez (R3). "
               "Farkı R1 · EY yapar: bu ekranın sorusu konum, metin ve filtreyi tek bir sıralı cevapta birleştirmektir. OpenSearch bunu tek bir bool sorgusunda, Türkçe harfsiz metin eşleşmesiyle yapar; Aurora'da metin skoru ile mesafeyi birlikte sıralayan formül elle yazılır ve planner iki index'ten birini seçer. "
               "R4'te iki aday eşittir (7'ye 7): OpenSearch'te Aurora'dan akış ve yeni bir geo mapping'i, Aurora'da PostGIS ve tsvector öğrenmek ekibin işidir. "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: metin araması istenmeseydi ve soru yalnız \"bu adres hangi bölgede\" ile \"en yakın 5 nokta\" olsaydı; ya da sonuç bir siparişle aynı transaction'da yazılmak zorunda olsaydı (Aurora sayfasının kart 10'u).",
        "ec": "Bellek içi key-value (ElastiCache) ile kafa kafaya. ElastiCache'in GEOSEARCH komutu yarıçap içindeki noktaları en yakından uzağa milisaniyenin altında verir ve tepe trafiği ayarsız taşır; DA'da ve R2'de öndedir. "
              "Ama bu ekranın sorusu yalnız \"en yakın\" değildir: metin, hizmet filtreleri ve çokgen içi testi de aynı sorudadır. Valkey'de metin araması ve çokgen tipi yoktur; filtreler ayrı set'lerle uygulamada kesiştirilir. R1'de 40 puanın 24,2'sini alır. "
              "Noktalar günde bir değişir; ElastiCache'in asıl gücü olan saniyede yüzlerce konum güncellemesi bu kartta yoktur. "
              "Hangi koşul değişseydi ElastiCache seçilirdi: noktalar hareket etseydi (ElastiCache sayfasının kart 10'undaki kuryeler gibi) ve soru yalnız \"en yakın 5\" olsaydı.",
    },
    verdict="Karar: OpenSearch {os}, Aurora PostgreSQL {aur}, ElastiCache {ec}. Bu yakın bir yarıştır ve kararı R1 · EY verir: konum, metin ve filtre tek bir sıralı sorguda yalnız search engine'de birleşir. Aurora coğrafi tiplerde ve kayıt sisteminin kendisi olmakta öndedir. "
            "OpenSearch seçtiğimizde artımız: tek sorgu, Türkçe harfsiz metin eşleşmesi, mesafeye göre sıra ve kart 1'in domain'i. "
            "Eksimiz: noktaları Aurora'dan OpenSearch Ingestion ile akıtırız ve logical replication açarız; çokgen doğrulamasını Aurora'da yaparız, çünkü kayıt oradadır. Doğru mimari ikisi birliktedir: kayıt ve teslim kuralı Aurora'da (PostGIS), \"yakınımda\" araması OpenSearch'te. "
            "Bir koşul değişseydi: metin araması istenmeseydi Aurora tek başına yeterdi."))

# ------------------------------------------------------------------ 5. application log analytics (twins: Serverless wins on service design)
OPENSEARCH_W.append(wusecase("logs", 5, sim="w_logs",
    title="Uygulama log analizi: request id, hata metni ve dakika başına grafikler",
    key="Index: logs-YYYY.MM.DD (günlük) ya da bir time series collection. Document: bir log satırı; @timestamp, service, level, request_id keyword, message text, latency_ms sayı.",
    story="Lale Market'in on Engine App'i, load balancer'ı ve Guided uygulaması JSON log yazar: günde 40 GB, akşam üç kat tepe. Üç kişilik nöbet ekibi bir olayda request id ile bir isteğin bütün satırlarını ve hata metniyle (\"ConditionalCheckFailedException\", \"timeout\") satırları arar. "
          "Duvardaki panolar dakika başına hata oranını ve p95 gecikmeyi gece gündüz gösterir ve dakikada bir yenilenir; hata oranı yüzde 2'yi geçince nöbetçiye alarm gitmelidir. Bir log 30 saniye içinde aranabilir olmalıdır. "
          "Son 30 gün aranabilir kalır; boru hattı her satırı ayrıca S3'e bir yıllık arşiv olarak yazar. Ekip OpenSearch Dashboards'u önceki işinden biliyor ve sunucu işletmek istemiyor.",
    wnote="R1 toplam 44: metinle ve id ile arama (EY 14), ekleme biçimi (OY 10), 30 günlük ömür (YD 10) ve arama ile grafikleri taşıyan yapı (DA 10). "
          "R4 18 ile ikinci: üç kişilik ekip sunucu işletmek istemiyor ve alarm şart. R2 16 ve R5 16: log akışı ve panolar hiç durmaz. Loglar S3'te de arşivlendiği için R3 6'da kalır.",
    rows=[
        row("EY", 14, "Bir olayda ilk soru \"bu isteğe ne oldu\", ikinci soru \"bu hata başka nerede var\" sorusudur.",
            "request_id ile bir isteğin bütün satırları, message içinde bir kelime ya da hata adı ve bir zaman aralığı tek bir sorgu olmalı; dakika başına hata sayısı ve p95 gecikme aynı veriden hesaplanmalı.",
            "Kelimeyle arama bütün satırları tarıyorsa olay sırasında her arama dakikalar sürer ve nöbetçi kör kalır."),
        row("OY", 10, "Loglar yalnız eklenir, hiç güncellenmez; yazma biçimi buna uymalı.",
            "Günde 40 GB yalnız ekleme: satırlar toplu olarak yazılır, hiçbiri değişmez.",
            "Her satırı tek tek yazan ya da güncelleme için tasarlanmış bir yöntem akşam tepesinde geride kalır."),
        row("YD", 10, "30 günden eski loglar kendiliğinden gitmezse depo her gün büyür.",
            "30 günden eski veri kendiliğinden ve ucuzca silinmeli; satır satır silme olmamalı.",
            "Satır satır silme bir günlük veride milyonlarca silme demektir ve aramayla yarışır."),
        row("DA", 10, "Panolar dakikada bir son saat üzerinde, olay aramaları 30 gün üzerinde çalışır; yapının bunu taşıması gerekir.",
            "Kelime araması ve dakika başına toplama, taranan GB'tan bağımsız olarak index'ten okunmalı.",
            "Her pano yenilemesi son saatin bütün loglarını tararsa panolar gecikir ve tarama başına ödenen bir modelde fatura büyür."),
        row("R2", 16, "Akış ve panolar hiç durmaz; olay anında arama yükü aniden artar.",
            "Günde 40 GB, akşam üç kat tepe; bir olay anında beş kişi aynı anda ağır aramalar yapar. Log 30 saniye içinde aranabilir olmalı ve olay aramaları yazmayı yavaşlatmamalı.",
            "Olay anında arama yazmayı yavaşlatırsa en çok ihtiyaç duyulan son loglar geç gelir."),
        row("R3", 6, "Her satır S3'te bir yıl arşivlenir; aranabilir kopyanın kaybı bir yeniden yüklemedir.",
            "Aranabilir 30 gün kaybolursa S3 arşivinden yeniden yüklenebilir; bir AZ arızası aramayı durdurmamalı.",
            "Olay sırasında aranabilir logların kaybı nöbetçiyi kör bırakır; ama arşiv kaybolmaz."),
        row("R4", 18, "Üç kişilik nöbet ekibi sunucu işletmek istemiyor ve alarm şart.",
            "Node, shard ve yama işi istenmiyor. Hata oranı alarmı aynı veriden kurulabilmeli. Ekip OpenSearch Dashboards biliyor.",
            "Log sistemi bozulduğunda onu da nöbet ekibi düzeltir; işletme yükü olayları uzatır. Alarm başka bir sistemde kurulursa iki sistem birbirinden kopar."),
        row("R5", 16, "Log hacmi büyüktür ve sürekli akar; fiyat modeli buna uymalı.",
            "Ayda 1.200 GB yeni log, panolar dakikada bir sorgu atar, olaylar ayda birkaç kez. Aylık fatura öngörülebilir olmalı.",
            "Sorgu başına taranan GB'a ödenen bir modelde dakikada bir yenilenen panolar faturayı katlar."),
    ],
    cands=["oss", "os", "cw"],
    scores={
        "oss": [sc(10, "Aynı engine: request_id bir term sorgusudur, message analyzer'la index'lenir (Ö1, Ö2) ve dakika başına toplama bir date_histogram'dır (Ö5). Puan kırılmadı."),
                sc(10, "Satırlar _bulk ile toplu eklenir; log hiç güncellenmez (Ö8). Puan kırılmadı."),
                sc(9, "Eski veri index bazında silinir (Ö7). 1 puan kırıldı: süre document başına değil index başınadır; günlük index ya da collection'ın saklama kuralı kurulur."),
                sc(10, "Inverted index kelimeyi, doc values toplamayı taramadan okur (Ö2, Ö5). Puan kırılmadı."),
                sc(9, "Indexing ve search OCU'ları ayrı ölçeklenir; olay aramaları yazmayı yavaşlatmaz. Refresh yaklaşık 10 saniyedir ve 30 saniye sınırının içindedir. 1 puan kırıldı: yeni OCU'lar veriyi S3'ten kopyaladıktan sonra cevap verir; ani bir sıçramada ilk dakikalar yavaştır."),
                sc(10, "Veri managed storage'da (S3) saklanır; bir node ya da AZ arızası veri kaybettirmez. Puan kırılmadı."),
                sc(7, "Node, shard ve yama yoktur; ekip aynı Dashboards'u kullanır. 3 puan kırıldı: Serverless'ın desteklenen API listesinde Alerting yoktur; hata oranı alarmı ayrı bir yoldan kurulur: uygulamalar hata sayısını ayrıca bir CloudWatch metric'i olarak yayınlar ve alarm orada kurulur (bir metric ayda yaklaşık 0,30 dolar)."),
                sc(6, "OCU-saat ve GB-ay başına ödenir. 4 puan kırıldı: akış ve panolar hiç durmadığı için indexing ve search OCU'ları gece de çalışır; ayda yaklaşık 1.100 dolar (Frankfurt, 2 indexing ve 2 search OCU, 7 gün sıcak ve 23 gün warm veri).")],
        "os": [sc(10, "request_id bir term sorgusudur, message analyzer'la index'lenir (Ö1, Ö2) ve dakika başına toplama bir date_histogram'dır (Ö5). Puan kırılmadı."),
               sc(10, "Satırlar _bulk ile toplu eklenir; log hiç güncellenmez (Ö8). Puan kırılmadı."),
               sc(9, "Eski veri index bazında silinir (Ö7). 1 puan kırıldı: süre document başına değil index başınadır; günlük index ve rollover düzeni kurulur."),
               sc(10, "Inverted index kelimeyi, doc values toplamayı taramadan okur (Ö2, Ö5). Puan kırılmadı."),
               sc(8, "Data node'lar yazmayı ve aramayı paylaşır (Ö7); refresh 1 saniyedir. 2 puan kırıldı: olay anında ağır aramalar yazmayla aynı node'larda yarışır ve sabit kapasite tepe anında yazmayı geciktirebilir."),
               sc(8, "Replica shard'lar node arızasını karşılar ve saatlik otomatik snapshot alınır. 2 puan kırıldı: domain kaybolursa 30 günlük veri S3 arşivinden saatler içinde yeniden yüklenir."),
               sc(6, "Yönetilen domain; Alerting ve ISM vardır, ekip Dashboards'u bilir. 4 puan kırıldı: data node tipi ve sayısı, master node'lar, 30-50 GiB shard planı ve ISM politikası ekibin işidir."),
               sc(6, "Node-saat ve gp3 GB-ay başına ödenir. 4 puan kırıldı: üç data node, üç master ve iki kopyalı 2,6 TB disk gece de çalışır; ayda yaklaşık 1.160 dolar (Frankfurt, r6g.large.search).")],
        "cw": [sc(6, "Logs Insights request_id gibi alanlarda field index kullanır ve stats count(*) by bin(1m) ile dakika başına sayar. 4 puan kırıldı: message içinde kelime araması bir filter'dır ve zaman aralığındaki her satırı tarar."),
               sc(10, "Log satırları log group'lara eklenir; güncelleme yoktur. Puan kırılmadı."),
               sc(10, "Saklama süresi log group başına bir ayardır; eski satırlar kendiliğinden gider. Puan kırılmadı."),
               sc(6, "Field index eşitlik sorgularında taramayı azaltır. 4 puan kırıldı: kelime araması ve toplamalar taranan veriyle büyür; dakikada bir yenilenen panolar son saati her seferinde yeniden tarar."),
               sc(10, "Yazma ve sorgu kapasitesi servisindir; akşam tepesi ve olay aramaları ayar istemez. Puan kırılmadı."),
               sc(10, "Loglar servis tarafından kalıcı saklanır. Puan kırılmadı."),
               sc(8, "Sunucu yoktur; metric filter ve alarm aynı serviste kurulur. 2 puan kırıldı: ekip Dashboards'u bilir, Logs Insights sorgu dili ve panoları yenidir."),
               sc(3, "GB başına alma, saklama ve sorgunun taradığı GB başına ödenir. 7 puan kırıldı: alma ayda yaklaşık 760 dolardır ve dakikada bir yenilenen 10 pano son saati her seferinde taradığı için sorgu ücreti ayda birkaç bin dolara çıkar (Frankfurt; alma 0,63 dolar/GB, sorgu 0,0063 dolar/taranan GB).")],
    },
    h2h={
        "os": "Aynı engine'in yönetilen domain'i (OpenSearch Service) ile kafa kafaya. İkisi aynı engine'i çalıştırır, bu yüzden R1'leri eşittir: 44'te 43. Kararı yalnız servis tasarımı verir. "
              "Domain'in artısı gerçektir: Alerting ve ISM onun içindedir, hata oranı alarmı aynı veriden kurulur; refresh 1 saniyedir. Serverless'ta Alerting API'si yoktur ve alarm ayrı bir yoldan kurulur (R4'te 3 puan). "
              "Ama domain'de data node'ların, master'ların, shard planının ve ISM politikasının sahibi ekiptir ve sabit kapasite olay anında ağır aramalarla yazmayı aynı node'larda yarıştırır (R2). Serverless'ta indexing ve search ayrı ölçeklenir ve veri S3'te saklanır (R3). Fatura iki biçimde de ayda yaklaşık 1.100-1.200 dolardır. "
              "Hangi koşul değişseydi yönetilen domain seçilirdi: Alerting, Anomaly Detection ya da Security Analytics bu veride şart olsaydı (kart 6), ya da log hacmi günde birkaç yüz GB'a çıkıp reserved instance ve UltraWarm faturayı belirgin düşürseydi.",
        "cw": "İzleme servisi (CloudWatch Logs) ile kafa kafaya. CloudWatch'un artısı sıfır işletmedir: loglar zaten oraya akabilir, saklama süresi bir ayardır, metric filter ve alarm aynı serviste kurulur ve kapasite servisindir; R2, R3 ve YD'de tam puan alır. "
              "Ama engine'i bir tarama motorudur: field index eşitlik sorgularını hızlandırır, kelime araması ve toplamalar ise zaman aralığındaki satırları tarar (R1 · EY ve DA'da 6). Taranan GB'a ödenen bir modelde dakikada bir yenilenen panolar faturayı katlar (R5 3). "
              "Hangi koşul değişseydi CloudWatch seçilirdi: panolar dakikada bir değil, olay anında açılsaydı, aramalar çoğunlukla request id ile yapılsaydı ve günlük hacim birkaç GB olsaydı; o zaman ayrı bir arama servisi gereksizdir. "
              "Birlikte de çalışırlar: loglar önce CloudWatch'a yazılır, bir abonelik onları OpenSearch'e aktarır.",
    },
    verdict="Karar: OpenSearch Serverless {oss}, OpenSearch {os}, CloudWatch {cw}. Bu yakın bir yarıştır ve iki OpenSearch servisi aynı engine'i çalıştırdığı için R1'de eşittir; kararı servis tasarımı verir: node ve shard işi yoktur, indexing ve search ayrı ölçeklenir, veri S3'te durur. "
            "Yine de yönetilen domain'i (bu sayfanın servisi) seçersek artımız: Alerting ve ISM aynı domain'dedir, refresh 1 saniyedir ve ileride Anomaly Detection ya da Security Analytics eklenebilir. "
            "Eksimiz: data node, master ve shard planı ekibin işidir; olay anında ağır aramalar için kapasite payı bırakırız; ISM ile günlük index'leri 30 günde sileriz ve UltraWarm'ı fiyatı düşürmek için değerlendiririz. "
            "Serverless seçersek hata oranı alarmını uygulamaların ayrıca yayınladığı bir CloudWatch metric'i üzerinde kurarız; loglar CloudWatch'a gitmediği için bir metric filter yeterli olmaz. "
            "Bir koşul değişseydi: bu loglar üzerinde Alerting ya da Security Analytics şart olsaydı yönetilen domain kazanırdı (kart 6)."))

# ------------------------------------------------------------------ 6. security analytics (managed domain wins; Serverless lacks the plugins)
OPENSEARCH_W.append(wusecase("security", 6,
    title="Güvenlik analitiği: CloudTrail, VPC Flow Logs ve WAF logları",
    key="Index: security-* (log türü başına). Document: bir olay; @timestamp, src_ip ve user keyword, event_name, action, message text. Detector'lar Sigma kurallarını belirli aralıklarla çalıştırır.",
    story="Lale Market'in iki kişilik güvenlik ekibi AWS hesabındaki CloudTrail olaylarını, VPC Flow Logs'u ve WAF loglarını izler: günde 15 GB, gün boyu düz. Analistler bir IP adresinin ya da bir kullanıcının son 90 gündeki bütün izini arar ve olay adlarında kelime arar (\"DeleteBucket\", \"ConsoleLogin failure\"). "
          "Hazır tehdit kuralları (örneğin \"başarısız login'lerden sonra başarılı bir admin login'i\") her beş dakikada çalışmalı ve bulgu üretince nöbetçiye haber vermelidir. "
          "Uyum kuralı bir yıl saklama ister: 90 gün hızlı aranabilir, geri kalanı ucuz bir katmanda. Ham loglar S3'te de durur. Ekip SQL bilir ama hazır kuralları kendisi yazmak istemez.",
    wnote="R1 toplam 44: iz sürme araması (EY 14), hazır tespit kuralları ve korelasyon (AO 12), arama ile uzun taramayı taşıyan yapı (DA 10) ve bir yıllık katmanlı ömür (YD 8). "
          "R4 16 ile ikinci: iki kişilik ekip kural motoru yazmak istemiyor. Güvenlik olayları kanıt olduğu için R3 12'dir.",
    rows=[
        row("EY", 14, "Bir güvenlik olayında ilk iş bir IP'nin ya da kullanıcının izini sürmektir.",
            "Bir IP ya da kullanıcı için 90 günün bütün olayları, olay adlarında kelime araması ve bir zaman aralığı tek bir sorguda; sonuçlar saniyeler içinde.",
            "İz sürme her seferinde saatler sürerse saldırgan o sürede hesapta kalır."),
        row("AO", 12, "Kuralları ekip yazarsa kapsam iki kişinin zamanıyla sınırlı kalır.",
            "Hazır tehdit kuralları (Sigma) log türüne göre çalışmalı, birkaç log türündeki olayları birleştiren korelasyon kurulabilmeli ve bulgu bir bildirime dönmeli.",
            "Kural motoru elle yazılırsa bilinen saldırı kalıpları kaçırılır ve her yeni kalıp bir yazılım projesidir."),
        row("DA", 10, "Aynı veride hem nokta araması hem 90 günlük tarama yapılır.",
            "Bir IP için arama index'ten okunmalı; uyum raporu için 90 gün üzerinde toplama da çalışmalı.",
            "Nokta araması her seferinde bütün veriyi tararsa 90 günlük iz sürme dakikalar sürer."),
        row("YD", 8, "Uyum kuralı bir yıl ister ama yalnız 90 günü hızlı aranır.",
            "90 gün hızlı aranabilir, 91. günden bir yıla kadar ucuz bir katmanda kalmalı ve gerektiğinde aranabilmeli; bir yıldan eski veri silinmeli.",
            "Bütün yıl sıcak katmanda tutulursa disk faturası dört katına çıkar; silinmezse uyum kuralı çiğnenir."),
        row("R2", 14, "Akış düzdür ama bulgular beş dakika içinde çıkmalıdır.",
            "Günde 15 GB, düz. Bir olay en geç bir dakikada aranabilir olmalı ve kurallar beş dakikada bir çalışmalı.",
            "Geç gelen olay geç gelen bulgudur; bir saldırı beş dakikada büyüyebilir."),
        row("R3", 12, "Güvenlik olayları kanıttır; aranabilir kopyanın kaybı soruşturmayı durdurur.",
            "Bir AZ arızası veri kaybettirmemeli. Ham loglar S3'te de durur; aranabilir kopya kaybolursa yeniden yüklenebilir ama bu saatler sürer.",
            "Bir soruşturma sırasında aranabilir verinin kaybı ekibi saatlerce kör bırakır."),
        row("R4", 16, "İki kişilik ekip kural motoru ve sunucu işletmek istemiyor.",
            "Hazır kurallar, bulgu ekranı ve bildirim servisin içinde olmalı; ekip SQL bilir, tespit kuralı yazmak istemez.",
            "Kural motoru, zamanlayıcı ve bildirim ayrı ayrı kurulursa iki kişilik ekibin bütün zamanı altyapıya gider."),
        row("R5", 14, "Bir yıllık veri büyüktür; katmanlı fiyat önemlidir.",
            "Ayda 450 GB yeni veri, bir yılda 5,4 TB. Eski verinin ucuz bir katmanda ödenmesi istenir.",
            "Bütün yılı sıcak disk fiyatıyla ödemek güvenlik bütçesini aşar."),
    ],
    cands=["os", "oss", "rs"],
    scores={
        "os": [sc(10, "src_ip ve user term sorgusudur, event_name analyzer'la index'lenir (Ö1, Ö2); 90 günlük iz bir bool sorgusudur. Puan kırılmadı."),
               sc(9, "Security Analytics, log türüne göre hazır Sigma kurallarıyla detector'lar çalıştırır, korelasyon kurallarını ve bulguları verir (Ö5 üzerine kurulu). 1 puan kırıldı: kurallar kendi alan adlarımıza eşlenir ve gürültülü kurallar ayarlanır."),
               sc(9, "Inverted index nokta aramasını, doc values 90 günlük toplamayı taşır (Ö2, Ö5). 1 puan kırıldı: bir yıllık uyum raporu birçok shard'ı tarar ve columnar bir warehouse'tan yavaştır."),
               sc(8, "Zamana göre index'ler eski veriyi index bazında siler ve ucuz katmana taşınır (Ö7). 2 puan kırıldı: süre document başına değil index başınadır ve ucuz katmana taşınan eski veri sıcak veriden yavaş aranır."),
               sc(9, "Data node'lar 15 GB'lık düz akışı rahat taşır, refresh 1 saniyedir (Ö8). 1 puan kırıldı: ağır bir soruşturma araması ile detector'lar aynı node'larda çalışır."),
               sc(8, "Replica shard'lar ve saatlik snapshot'lar. 2 puan kırıldı: domain kaybolursa 90 günlük veri S3'teki ham loglardan saatler içinde yeniden yüklenir."),
               sc(6, "Security Analytics, Alerting ve ISM domain'in içindedir. 4 puan kırıldı: data node, UltraWarm ve cold katmanı boyutlandırma ve ISM politikası ekibin işidir; cold katmandaki bir index aranmadan önce geri bağlanır."),
               sc(6, "Node-saat ve disk; UltraWarm ve cold katmanı eski veriyi ucuzlatır. 4 puan kırıldı: sıcak katmanın node'ları gece de çalışır ve UltraWarm node'ları ayrıca ödenir.")],
        "oss": [sc(10, "Aynı engine: src_ip ve user term sorgusudur, event_name analyzer'la index'lenir (Ö1, Ö2). Puan kırılmadı."),
                sc(9, "Engine'in Security Analytics araçları aynıdır (Ö5). 1 puan kırıldı: kurallar kendi alan adlarımıza eşlenir. Serverless'ın bu aracı sunmaması bir paketleme farkıdır ve R4'te sayılır."),
                sc(9, "Inverted index ve doc values aynıdır (Ö2, Ö5). 1 puan kırıldı: bir yıllık uyum raporu birçok shard'ı tarar."),
                sc(8, "Zamana göre index'ler eski veriyi index bazında siler ve ucuz katmana taşınır (Ö7). 2 puan kırıldı: süre document başına değil index başınadır ve ucuz katmana taşınan eski veri sıcak veriden yavaş aranır."),
                sc(9, "OCU'lar akışa göre ölçeklenir; refresh yaklaşık 10 saniyedir. 1 puan kırıldı: yeni OCU'lar veriyi S3'ten kopyaladıktan sonra cevap verir."),
                sc(10, "Veri managed storage'da (S3) saklanır. Puan kırılmadı."),
                sc(2, "Node ve shard işi yoktur. 8 puan kırıldı: Serverless'ın desteklenen API listesinde Security Analytics, Alerting ve ISM yoktur; detector'lar, zamanlayıcı ve bildirim başka bir yerde kurulur ve kurallar ekibin yazdığı sorgulara döner."),
                sc(6, "OCU-saat ve GB-ay; time series collection'da eski veri kendiliğinden warm katmana geçer (0,026 dolar/GB-ay, sıcak katman 0,36). 4 puan kırıldı: indexing ve search OCU'ları gece de çalışır; aylık fatura yönetilen domain'inkine yakındır, bu yüzden bu kartta R5 iki biçimi ayırmaz.")],
        "rs": [sc(6, "SQL src_ip ve user column'larında hızlıdır. 4 puan kırıldı: olay adlarında kelime araması LIKE ile column'u tarar; relevance yoktur."),
               sc(3, "Zamanlanmış SQL sorguları kural gibi çalıştırılabilir. 7 puan kırıldı: hazır tehdit kuralı, korelasyon ve bulgu ekranı yoktur; her kural ekibin yazdığı bir sorgudur."),
               sc(8, "Columnar depolama 90 günlük ve bir yıllık taramalarda çok güçlüdür. 2 puan kırıldı: tek bir IP'nin araması bir index'ten değil, sort key ve blok özetleriyle daraltılan bir taramadan gelir."),
               sc(8, "Zamana göre sıralı table'lar ve S3'teki veriye Spectrum ile sorgu ucuz bir katman verir. 2 puan kırıldı: eski row'ları silmek DELETE ve VACUUM ister."),
               sc(8, "Veri S3'ten COPY ya da streaming ingestion ile gelir. 2 puan kırıldı: toplu yüklemede olaylar dakikalar sonra sorgulanabilir; bulgular gecikir."),
               sc(10, "Redshift managed storage ve otomatik snapshot'lar. Puan kırılmadı."),
               sc(5, "Serverless Redshift'te node yoktur. 5 puan kırıldı: yükleme işleri, kural sorguları, zamanlayıcı ve bildirim ekibin yazdığı parçalardır."),
               sc(7, "RPU-saat sorgu çalıştıkça ödenir; Spectrum eski veriyi S3 fiyatıyla tutar. 3 puan kırıldı: beş dakikada bir çalışan kurallar RPU'ları gün boyu uyanık tutar.")],
    },
    h2h={
        "oss": "Aynı engine'in sunucusuz biçimi (OpenSearch Serverless) ile kafa kafaya. R1'leri eşittir: aynı inverted index, aynı analyzer ve engine'in aynı Security Analytics araçları. Kart 5'te Serverless node işini kaldırdığı için kazanmıştı; bu kartta kaybeder. "
               "Neden: Serverless'ın desteklenen API listesinde Security Analytics, Alerting ve ISM yoktur. Engine'in sahip olduğu ama servisin dışarıda bıraktığı bir özellik paketleme farkıdır ve bu kartta R4'ün kendisidir: detector'lar, zamanlayıcı ve bildirim başka bir yerde yazılır (R4'te 2). "
               "Serverless'ın artıları da gerçektir: veri S3'te durur (R3 10) ve kapasite servisindir. Toplam fark 4 puandır, yani yakın bir yarıştır. "
               "Hangi koşul değişseydi OpenSearch Serverless seçilirdi: tespit kuralları başka bir serviste (örneğin GuardDuty) çalışsaydı ve OpenSearch'e yalnız analistlerin iz sürme araması kalsaydı; o zaman kart 5'in koşulları geçerli olur.",
        "rs": "Data warehouse (Redshift) ile kafa kafaya. Redshift'in gücü uzun taramalardadır: bir yıllık uyum raporu ya da \"geçen çeyrekte en çok reddedilen 100 IP\" columnar depolamada çok hızlıdır, Spectrum eski veriyi S3'te ucuz tutar ve ekip SQL bilir. "
              "Ama bu kartın günlük işi iz sürme ve tespittir: bir IP'nin 90 günlük izi, olay adlarında kelime araması ve hazır Sigma kuralları. Redshift'te kelime araması bir taramadır, hazır kural ve bulgu ekranı yoktur; her kural ekibin yazdığı ve zamanladığı bir SQL'dir (R1 · AO'da 3, R4'te 5). "
              "Hangi koşul değişseydi Redshift seçilirdi: iş tespit değil uyum raporlaması olsaydı (aylık ve yıllık raporlar), tespit başka bir serviste yapılsaydı ve analistler yalnız SQL ile çalışsaydı. "
              "Büyük bir şirkette ikisi birlikte de çalışır: son 90 gün OpenSearch'te tespit ve iz sürme için, bütün yıl S3 ve Redshift'te rapor için.",
    },
    verdict="Karar: OpenSearch {os}, OpenSearch Serverless {oss}, Redshift {rs}. Bu yakın bir yarıştır: iki OpenSearch servisi R1'de eşittir ve kararı R4 verir, çünkü hazır kurallar, bulgular ve bildirim yalnız yönetilen domain'dedir. "
            "OpenSearch seçtiğimizde artımız: Sigma kuralları, korelasyon ve bildirim kurulu gelir; iz sürme araması saniyelerdir; UltraWarm ve cold katmanı bir yılı ucuz tutar. "
            "Eksimiz: data node'lar, UltraWarm ve ISM politikası ekibin işidir; kuralları kendi alan adlarımıza eşler ve gürültülü kuralları ayarlarız; soğuk index'leri aramadan önce geri bağlarız. "
            "Bir koşul değişseydi: tespit başka bir serviste yapılsaydı OpenSearch Serverless'ın sıfır node işi öne geçerdi (kart 5)."))

# ------------------------------------------------------------------ 7. metrics dashboards (Timestream for InfluxDB wins, OpenSearch clearly third)
OPENSEARCH_W.append(wusecase("metrics", 7, sim="w_metrics",
    title="Uygulama metrikleri panosu: 10 saniyelik ölçümler, 13 ay geçmiş",
    key="Ölçüm: host ve metric etiketleri, value ve zaman. 60 host × 40 metrik = 2.400 seri, her biri 10 saniyede bir nokta.",
    story="Lale Market'in 60 sunucusu ve container'ı her 10 saniyede 40 ölçüm gönderir: CPU, bellek, istek gecikmesinin p95'i, dakikadaki sipariş sayısı. Bu 2.400 seri ve saniyede 240 noktadır. "
          "Panolar son 6 saati 10 saniyelik çözünürlükle, son 30 günü dakikalık, son 13 ayı saatlik ortalamayla gösterir; eski veri kendiliğinden özetlenmeli ve silinmelidir. "
          "Üç kişilik nöbet ekibi Grafana kullanır ve eşik alarmları kurar. EC2 ve load balancer metrikleri zaten CloudWatch'a kendiliğinden gelir. Metin araması yoktur; her soru \"şu serinin şu zaman aralığında ortalaması\" sorusudur.",
    wnote="R1 toplam 42: veri bir zaman serisidir (VM 14), soru zaman penceresinde toplama (EY 14) ve eski veri özetlenip silinir (YD 14). "
          "R4 18 ve R5 18 ile ikinci sıradadır: üç kişilik ekip yeni bir sistem işletmek istemiyor ve 2.400 serinin aylık faturası seçimde belirleyicidir.",
    rows=[
        row("VM", 14, "Her nokta bir zaman, birkaç etiket ve bir sayıdır; model bunu doğrudan taşımalı.",
            "Nokta = zaman + etiketler (host, metric) + sayı. Aynı etiketli noktalar bir seri olarak saklanmalı; etiket adları her noktada tekrar yazılmamalı.",
            "Her nokta etiket adlarıyla ayrı bir kayıt olarak saklanırsa depo ve okuma bir seri modeline göre katlanır."),
        row("EY", 14, "Her pano isteği \"şu serinin şu aralıktaki ortalaması\" sorusudur.",
            "Bir zaman aralığında, seriler üzerinde 10 saniyelik ya da dakikalık pencerelerle ortalama, maksimum ve p95; birkaç seriyi bir grafikte birleştirmek.",
            "Pencere hesabı uygulamada yapılırsa her pano bütün noktaları çeker ve yavaşlar."),
        row("YD", 14, "13 ay 10 saniyelik çözünürlükte tutulursa veri gereksiz büyür.",
            "10 saniyelik veri 6 saat, dakikalık özet 30 gün, saatlik özet 13 ay tutulmalı; özetleme ve silme kendiliğinden olmalı.",
            "Özetleme elle yapılırsa unutulur; silinmeyen veri her ay büyür ve sorgular yavaşlar."),
        row("R2", 14, "Saniyede 240 nokta küçüktür; panolar düz bir okuma yüküdür.",
            "Saniyede 240 nokta yazma, 20 kullanıcının panoları dakikada bir yenilenir.",
            "Yazma geride kalırsa pano son dakikayı göstermez ve alarm geç çalışır."),
        row("R3", 8, "Bir metrik kaybı grafikte bir boşluktur; kayıt kaybı değildir.",
            "Bir AZ arızasında metrik kaybı olmamalı; birkaç dakikalık boşluk kabul edilir.",
            "Olay anında grafikte boşluk nöbetçiyi yanıltır."),
        row("R4", 18, "Üç kişilik nöbet ekibi yeni bir sistem işletmek istemiyor.",
            "Instance, depolama ve ajan işi en az olmalı. EC2 ve load balancer metrikleri ayrıca taşınmadan aynı panoda görünmeli.",
            "Metrik sistemi bozulduğunda onu da nöbet ekibi düzeltir; AWS metrikleri ayrı bir yerde kalırsa iki pano izlenir."),
        row("R5", 18, "2.400 serinin aylık faturası bu iş yükünün en görünür maliyetidir.",
            "Ayda 620 milyon nokta, birkaç GB veri. Seri sayısı yılda iki katına çıkabilir; fatura buna göre öngörülebilir olmalı.",
            "Seri başına ödenen bir modelde her yeni host ve metrik faturayı doğrudan büyütür."),
    ],
    cands=["ix", "cw", "os"],
    scores={
        "ix": [sc(10, "Point = measurement + tag set + field + timestamp; aynı tag set'li noktalar bir seridir ve seri olarak sıkıştırılır. Puan kırılmadı."),
               sc(10, "aggregateWindow (Flux) ya da GROUP BY time (InfluxQL) pencere başına ortalama, maksimum ve yüzdelik verir. Puan kırılmadı."),
               sc(9, "Bucket'ın saklama süresi eski veriyi siler; downsampling bir task'tır. 1 puan kırıldı: dakikalık ve saatlik özetleri yazan task'ları ekip yazar."),
               sc(9, "Saniyede 240 nokta bir instance için küçüktür. 1 puan kırıldı: bütün yazmalar tek bir instance'tan geçer; seri sayısı on kat büyürse instance büyütülür."),
               sc(8, "Multi-AZ seçeneği bir standby tutar. 2 puan kırıldı: failover sırasında birkaç dakikalık yazma boşluğu olabilir."),
               sc(6, "Yönetilen instance; Grafana doğrudan bağlanır. 4 puan kırıldı: instance sınıfı ve depolama ekibin seçimidir, ajanlar (Telegraf) kurulur ve EC2 ile load balancer metrikleri ayrıca taşınır."),
               sc(8, "Instance-saat ve depolama ödenir; seri sayısı faturayı doğrudan büyütmez. 2 puan kırıldı: Multi-AZ db.influx.medium ayda yaklaşık 210 dolar gece de çalışır (Frankfurt).")],
        "cw": [sc(9, "Bir metric namespace, ad ve dimension'larla tanımlanır ve zamanlı sayılar tutar. 1 puan kırıldı: her dimension birleşimi ayrı bir metric'tir; host × endpoint birleşimleri metric sayısını katlar."),
               sc(9, "İstatistikler (Average, Maximum, p95) her periyot için hesaplanır ve math expression'lar serileri birleştirir. 1 puan kırıldı: 10 saniyelik çözünürlük için high-resolution metric yayınlanır."),
               sc(3, "Özetleme ve silme kendiliğindendir: dakikalık veri 15 gün, 5 dakikalık 63 gün, saatlik 455 gün tutulur. 7 puan kırıldı: AWS'e göre 60 saniyeden kısa periyotlu veri 3 saat tutulur; isteğin üç parçasından ikisi karşılanmaz (10 saniyelik veri 6 değil 3 saat, dakikalık veri 30 değil 15 gün), bu yüzden ölçeğin 0–3 bandındadır; yalnız 13 aylık saatlik özet karşılanır."),
               sc(10, "Yazma ve okuma kapasitesi servisindir. Puan kırılmadı."),
               sc(10, "Metrikler servis tarafından kalıcı saklanır. Puan kırılmadı."),
               sc(9, "Sunucu yoktur; EC2 ve load balancer metrikleri zaten oradadır ve alarm aynı servistedir. 1 puan kırıldı: uygulama metrikleri PutMetricData ya da gömülü metric formatı ile koddan yayınlanır."),
               sc(5, "Custom metric başına ödenir. 5 puan kırıldı: 2.400 metric ayda yaklaşık 720 dolardır (Frankfurt, ilk 10.000 metric için 0,30 dolar) ve her yeni seri faturayı büyütür.")],
        "os": [sc(6, "Bir nokta bir JSON document'ıdır; etiketler keyword, değer sayı alanıdır. 4 puan kırıldı: engine'de seri kavramı yoktur; her nokta etiket adlarıyla ayrı bir document olarak saklanır."),
               sc(8, "date_histogram ve terms aggregation'ları pencere başına ortalama, maksimum ve yüzdelik verir (Ö5). 2 puan kırıldı: oran ve türev gibi hesaplar pipeline aggregation'larla yazılır ve her pano isteği bütün document'ları toplar."),
               sc(7, "Zamana göre index'ler index bazında silinir (Ö7) ve index rollup işi özet index'ler üretir. 3 puan kırıldı: dakikalık ve saatlik özetler ayrı rollup işleri ve ayrı index'lerdir; panolar hangi index'i soracağını bilir."),
               sc(9, "Saniyede 240 document küçüktür (Ö7). 1 puan kırıldı: kapasite sabittir ve büyüme için node eklenir."),
               sc(8, "Replica shard'lar ve saatlik snapshot. 2 puan kırıldı: bir domain kaybında snapshot'tan sonraki noktalar kaybolur."),
               sc(5, "Yönetilen domain. 5 puan kırıldı: node, shard ve rollup işleri ekibin işidir ve EC2 metrikleri ayrıca taşınır."),
               sc(5, "Node-saat ödenir. 5 puan kırıldı: birkaç GB'lık bir veri için üç data node'luk bir domain ayda yaklaşık 440 dolar gece de çalışır (Frankfurt, r6g.large.search; küçük bir domain'de ayrı master node yoktur, disk hariç).")],
    },
    h2h={
        "cw": "İzleme servisi (CloudWatch) ile kafa kafaya. Fark 8,2 puandır; yakın bir yarış değildir. CloudWatch'un artısı sıfır işletmedir: EC2 ve load balancer metrikleri zaten oradadır, özetleme ve silme kendiliğindendir, alarm aynı servistedir ve kapasite servisindir; R2, R3 ve R4'te öndedir ve orada 8,4 puan geri alır. "
              "Timestream for InfluxDB'yi öne geçiren R1 (11,2 puan) ve R5'tir (5,4 puan). En büyük fark R1 · YD'dedir (8,4 puan): CloudWatch'un saklama kuralı sabittir; AWS'e göre 60 saniyeden kısa periyotlu veri 3 saat, dakikalık veri 15 gün tutulur, yani 6 saatlik 10 saniyelik pano ve 30 günlük dakikalık pano karşılanmaz; isteğin üç parçasından ikisi eksik kaldığı için puan 0–3 bandındadır. R1'in diğer iki alt maddesi 1,4'er puan getirir. R5: CloudWatch seri başına öder; 2.400 seri ayda yaklaşık 720 dolardır ve seri sayısıyla büyür, InfluxDB instance'ı ise yaklaşık 210 dolardır. "
              "Hangi koşul değişseydi CloudWatch seçilirdi: 10 saniyelik veri 3 saat ve dakikalık veri 15 gün yetseydi; R1 · YD tam karşılanır ve CloudWatch 86,4'e 84,8 öne geçerdi. Seri sayısının birkaç yüz olması tek başına farkı kapatmaz.",
        "os": "Search engine (OpenSearch) ile kafa kafaya. Bu kartta OpenSearch net kaybeder ve kaybın büyük kısmı R1'dedir: engine bir metin ve document engine'idir, zaman serisi engine'i değildir. Her nokta etiket adlarıyla ayrı bir document olur, seri kavramı yoktur, özetler ayrı rollup işleri ve ayrı index'lerdir. R1'in 42 puanının 29,4'ünü alır; Timestream for InfluxDB 40,6'sını. "
              "Servis tasarımında da geridedir: birkaç GB'lık metrik için üç node'luk bir domain ve rollup işleri işletilir. "
              "OpenSearch'ün güçlü olduğu yer metriklerin yanında metin olduğu yerdir: log satırları ve izler (kart 5). "
              "Hangi koşul değişseydi OpenSearch seçilirdi: metrikler logların içinden çıkarılsaydı (her log satırının gecikmesi gibi) ve aynı panoda log araması da istenseydi; o zaman ayrı bir metrik sistemi yerine aynı domain kullanılır.",
    },
    verdict="Karar: Timestream for InfluxDB {ix}, CloudWatch {cw}, OpenSearch {os}. Bu iş yüküne en uygun servis zaman serisi engine'idir: seri modeli, pencere sorguları ve saklama kuralı engine'in kendisidir. CloudWatch ikincidir ve işletmede öndedir, ama sabit saklama kuralı isteğin iki parçasını karşılamaz. "
            "Yine de OpenSearch seçersek artımız: loglar ve metrikler aynı domain'de ve aynı Dashboards'ta olur. "
            "Eksimiz: her nokta bir document olur ve depo bir seri modeline göre büyür; dakikalık ve saatlik özetleri rollup işleriyle üretiriz ve panoları doğru index'e yönlendiririz; birkaç GB için bir domain işletir ve öderiz. Bu kart OpenSearch'ün net kaybettiği karttır. "
            "Bir koşul değişseydi: 10 saniyelik veri 3 saat ve dakikalık veri 15 gün yetseydi CloudWatch kazanırdı."))

# ------------------------------------------------------------------ 8. knowledge base search with vectors (Aurora wins; OpenSearch wins R1 but is third)
OPENSEARCH_W.append(wusecase("kb", 8, sim="w_kb",
    title="Yardım merkezi araması ve destek asistanı: kelime ve anlam birlikte",
    key="Yardım makaleleri 60.000 parçaya bölünür; her parça metin ve 1.024 boyutlu bir vektör (embedding) taşır. Sorgu: kelime araması + vektör benzerliği, tek bir sıralı liste.",
    story="Lale Market'in yardım merkezinde 4.000 Türkçe makale var; makaleler 60.000 parçaya bölünür ve her parçanın bir embedding'i (anlamını temsil eden 1.024 sayılık bir vektör) vardır. Yardım merkezindeki arama kutusu ve destek asistanı (bir RAG uygulaması) aynı aramayı kullanır: "
          "\"kargom nerede\" sorusu \"sipariş takibi\" başlıklı makaleyi bulmalı (anlam), \"iade kodu RT-204\" sorusu tam o kodu içeren parçayı bulmalı (kelime). Gündüz saniyede 5, kampanya günü saniyede 30 arama olur; gece neredeyse sıfırdır. Günde 50 makale değişir. "
          "Siparişler zaten Aurora PostgreSQL'de çalışıyor; üç geliştirici SQL biliyor ve yeni bir servis işletmek istemiyor. Makalelerin kaynağı CMS'tir; index kaybolursa bir saatte yeniden kurulur.",
    wnote="R1 toplam 38: kelime ve anlamı tek bir sıralı listede birleştirmek (EY 16), yaklaşık en yakın komşu araması (DA 12) ve skorları dengeleyen araçlar (AO 10). "
          "R4 20 ve R5 20 ile R1'in her alt maddesinden ağırdır, ama R1 grup olarak yine en ağırdır: trafik küçüktür ve gece sıfırdır, ekip yeni bir servis istemiyor.",
    rows=[
        row("EY", 16, "Destek asistanının cevabı bulduğu parçalar kadar doğrudur.",
            "Kelime araması (tam kod, ürün adı) ve anlam araması (eş anlamlı sorular) tek bir sorguda, tek bir sıralı listede birleşmeli; kategoriye göre filtre de aynı sorguda olmalı.",
            "Yalnız kelime araması \"kargom nerede\" sorusunu kaçırır; yalnız anlam araması \"RT-204\" kodunu kaçırır. İki ayrı sonuç uygulamada birleştirilirse sıralama tutarsızdır."),
        row("DA", 12, "60.000 vektör her sorguda tek tek karşılaştırılmamalı.",
            "Vektör araması yaklaşık en yakın komşu index'iyle (HNSW) yapılmalı; süre parça sayısıyla doğrusal artmamalı.",
            "Her sorguda 60.000 vektörü karşılaştırmak kampanya günü saniyede 30 aramada yavaşlar."),
        row("AO", 10, "İki skor farklı ölçeklerdedir; dengelemek bir ayar işidir.",
            "Kelime skoru ile vektör benzerliğini normalleştiren ve ağırlıklandıran bir araç olmalı; ağırlık kod değişmeden değiştirilebilmeli.",
            "Skorlar elle toplanırsa biri diğerini ezer ve ayar her seferinde bir kod değişikliğidir."),
        row("R2", 10, "Trafik küçüktür; kampanya günü altı kat.",
            "Gündüz saniyede 5, kampanya günü saniyede 30 arama; her biri 200 ms içinde. Gece neredeyse sıfır.",
            "Kampanya günü yavaşlayan asistan müşteri hizmetleri kuyruğunu büyütür."),
        row("R3", 12, "Makalelerin kaynağı CMS'tir; index'in kaybı bir yeniden kurulumdur.",
            "Index kaybolursa CMS'ten bir saatte yeniden kurulabilir (embedding'ler yeniden hesaplanır). Bir AZ arızası aramayı durdurmamalı.",
            "Bir saatlik boş yardım merkezi müşteri hizmetlerine yük bindirir; ama makaleler kaybolmaz."),
        row("R4", 20, "Üç SQL geliştiricisi yeni bir servis işletmek istemiyor ve Aurora zaten çalışıyor.",
            "Arama zaten çalışan bir sistemin üzerine kurulmalı; yeni bir sorgu dili ve yeni bir nöbet istenmiyor.",
            "Yeni bir servis üç kişilik ekibe nöbet, izleme ve yeni bir sorgu dili ekler."),
        row("R5", 20, "Trafik küçük ve gece sıfır; 60.000 parça için sabit bir filo ödemek israftır.",
            "Birkaç GB veri, günde birkaç bin arama. Boştayken neredeyse sıfır ödenmeli.",
            "Gece gündüz çalışan bir sunucu filosu bu küçük özelliğin getirisini aşar."),
    ],
    cands=["aur", "oss", "os"],
    scores={
        "aur": [sc(9, "pgvector'ün <=> operatörü anlam araması, tsvector kelime araması yapar ve WHERE kategoriyi filtreler; ikisi tek bir SQL'de birleşir. 1 puan kırıldı: Türkçe harfsiz yazım için unaccent ayrıca kurulur. İki skoru tek sıraya koyan formül R1.3'te sayıldı."),
                sc(9, "pgvector HNSW ve IVFFlat index'lerini destekler; arama yaklaşık en yakın komşu ile yapılır. 1 puan kırıldı: filtreli vektör aramasında HNSW parametreleri (ef_search) ölçülerek ayarlanır."),
                sc(7, "setweight ve ts_rank kelime skorunu, mesafe vektör skorunu verir. 3 puan kırıldı: iki skoru normalleştiren hazır bir araç yoktur; ağırlıklar sorgunun içinde yazılır."),
                sc(10, "Saniyede 30 arama bir reader için küçüktür. Puan kırılmadı."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(9, "Aurora çalışır, ekip SQL bilir; yeni bir servis yoktur. 1 puan kırıldı: pgvector extension'ı ve HNSW index ayarları ekibin yeni işidir."),
                sc(9, "Birkaç GB var olan cluster'a eklenir. 1 puan kırıldı: HNSW index'inin belleği için daha yüksek bir minimum ACU gerekebilir.")],
        "oss": [sc(10, "Aynı engine: bir hybrid sorgusu match (BM25) ve knn sorgusunu tek bir sıralı listede birleştirir ve filtre aynı sorgudadır (Ö3, Ö9). Puan kırılmadı."),
                sc(10, "k-NN index'i HNSW grafiğiyle yaklaşık en yakın komşuyu bulur (Ö9). Puan kırılmadı."),
                sc(9, "Normalization processor'lı bir search pipeline iki skoru normalleştirir ve ağırlıklandırır; ağırlık bir ayardır (Ö9). 1 puan kırıldı: ağırlıklar ölçülerek ayarlanır."),
                sc(9, "OCU'lar trafiğe göre ölçeklenir. 1 puan kırıldı: NextGen koleksiyonu boşta sıfıra indiyse ilk sorgu, OCU'lar veriyi yüklerken bekler."),
                sc(10, "Veri managed storage'da (S3) saklanır. Puan kırılmadı."),
                sc(6, "Node ve shard işi yoktur. 4 puan kırıldı: ekip için yeni bir servis, yeni bir sorgu dili ve embedding'leri index'e yazan yeni bir boru hattıdır."),
                sc(6, "OCU-saat ve GB-ay ödenir; NextGen koleksiyonu 10 dakika boşta kalınca sıfıra iner. 4 puan kırıldı: gündüz saatlerinde OCU'lar çalışır; AWS'in benzer bir örneği ayda yaklaşık 250 dolardır.")],
        "os": [sc(10, "Bir hybrid sorgusu match (BM25) ve knn sorgusunu tek bir sıralı listede birleştirir ve filtre aynı sorgudadır (Ö3, Ö9). Puan kırılmadı."),
               sc(10, "k-NN index'i HNSW grafiğiyle yaklaşık en yakın komşuyu bulur (Ö9). Puan kırılmadı."),
               sc(9, "Normalization processor'lı bir search pipeline iki skoru normalleştirir ve ağırlıklandırır (Ö9). 1 puan kırıldı: ağırlıklar ölçülerek ayarlanır."),
               sc(10, "Saniyede 30 arama küçük bir domain için de rahattır (Ö7). Puan kırılmadı."),
               sc(8, "Replica shard'lar ve saatlik snapshot. 2 puan kırıldı: domain kaybolursa embedding'ler yeniden hesaplanarak bir saatte yeniden kurulur."),
               sc(4, "Yönetilen domain. 6 puan kırıldı: ekip için yeni bir servis, yeni bir sorgu dili, node ve shard seçimi ve embedding boru hattıdır."),
               sc(3, "Node-saat ödenir. 7 puan kırıldı: üretim için üç AZ'lik, üç data node'luk bir domain ayda yaklaşık 440 dolardır (küçük bir domain'de ayrı master node yoktur, disk hariç) ve gece boş çalışır; saniyede 5 arama için büyük bir sabit faturadır.")],
    },
    h2h={
        "oss": "Sunucusuz search engine (OpenSearch Serverless) ile kafa kafaya. R1'i OpenSearch kazanır: hybrid sorgusu kelime ve vektör skorunu normalleştirip tek bir listede birleştirir; Aurora'da bu formül elle yazılır. R1'de 38 puanın 37'sini alır, Aurora 32,2'sini. "
               "Toplamı Aurora'ya veren R4 ve R5'tir: Aurora zaten çalışır, ekip SQL bilir ve birkaç GB'lık veri var olan cluster'a eklenir. Serverless'ın NextGen koleksiyonu gece sıfıra iner ve node işi yoktur; bu yüzden yönetilen domain'in önündedir, ama yine de yeni bir servis ve yeni bir sorgu dilidir. "
               "Hangi koşul değişseydi OpenSearch Serverless seçilirdi: makale sayısı milyonlara çıksaydı ve arama kalitesi (hibrit ağırlıklar, rerank) bir ürün hedefi olsaydı; ya da ekip Bedrock Knowledge Bases kullansaydı, çünkü o servis vektör deposunu sunucusuz bir koleksiyon olarak kendisi kurabilir.",
        "os": "Search engine (OpenSearch) ile kafa kafaya. Engine'i Serverless ile aynıdır, R1'i de aynıdır: 38'de 37. Bu kart, R1'i kazanan bir servisin toplamda üçüncü olabileceğini gösterir. "
              "Kaybı servis tasarımından gelir: saniyede 5 arama ve birkaç GB veri için üç AZ'lik bir domain ayda yaklaşık 440 dolardır ve gece boş çalışır (R5'te 3); node, shard ve embedding boru hattı üç kişilik SQL ekibinin yeni işidir (R4'te 4). Serverless aynı engine'i gece sıfıra inen bir faturayla verir; Aurora ise hiçbir yeni servis istemez. "
              "Hangi koşul değişseydi yönetilen domain seçilirdi: Lale Market'in kart 1 domain'i zaten çalıştığı için yardım merkezi bir index daha olsaydı (o zaman R4 ve R5 kart 3'teki gibi 9 ve 8 olur) ya da trafik gün boyu düz ve yüksek olsaydı.",
    },
    verdict="Karar: Aurora PostgreSQL {aur}, OpenSearch Serverless {oss}, OpenSearch {os}. Engine uyumunu iki OpenSearch servisi kazanır; toplamı Aurora alır, çünkü bu küçük ve gece sıfıra inen iş yükünde R4 ve R5 ağırdır ve Aurora zaten çalışır. "
            "Yine de OpenSearch seçersek artımız: kelime ve anlam araması tek bir hybrid sorgusunda, skorlar hazır bir araçla dengelenir ve arama kalitesi büyüdükçe aynı engine yeter. "
            "Eksimiz: üç kişilik SQL ekibi yeni bir servis ve sorgu dili öğrenir, embedding boru hattını işletir ve küçük bir trafik için gece gündüz çalışan bir domain öder; bu yüzden OpenSearch seçilecekse Serverless biçimi ya da kart 1'in var olan domain'i seçilir. "
            "Bir koşul değişseydi: Lale Market'in OpenSearch domain'i bu ekip tarafından zaten işletilseydi yardım merkezi bir index daha olurdu ve OpenSearch kazanırdı."))

# ------------------------------------------------------------------ 9. e-commerce relevance tuning (OpenSearch wins on its engine tools)
OPENSEARCH_W.append(wusecase("relevance", 9,
    title="Arama sıralamasını ayarlamak: stok, satış, kampanya ve eş anlamlılar",
    key="Index: products (kart 1). Ek alanlar: in_stock (boolean), sales_30d (sayı), campaign (keyword). Sorgu: function_score ile metin skoru × satış ve stok sinyali.",
    story="Kart 1'in araması çalışıyor; şimdi pazarlama ekibi sıralamayı iş kurallarıyla ayarlamak istiyor. Stokta olmayan ürün geriye düşmeli, son 30 günde çok satan ürün öne çıkmalı, kampanya ürünü bir hafta öne alınmalı. "
          "Eş anlamlılar tanımlanmalı: \"telefon kılıfı\" ile \"kapak\", \"powerbank\" ile \"taşınabilir şarj\". Her hafta iki sıralama A/B testiyle karşılaştırılır; ekip 200 örnek aramanın \"doğru sonuçlarını\" işaretledi ve her değişikliği bu listeyle ölçmek istiyor. "
          "Stok ve satış sinyalleri saatte 5.000 ürün için değişir. Arama trafiği kart 1'deki gibidir: kampanya akşamı saniyede 300. Katalog DocumentDB'dedir, arama kopyası kart 1'in domain'indedir.",
    wnote="R1 toplam 46: sıralamayı ayarlayan araçlar (AO 16), metin ve sayısal sinyallerin tek skorda birleşmesi (EY 12), sinyallerin güncellenme biçimi (OY 10) ve bunu taşıyan algoritma (DA 8). "
          "R2 16 ve R4 16 ile ikinci sıradadır: trafik kart 1'inkidir ve ekip var olan sistemin üzerine kurmak istiyor.",
    rows=[
        row("AO", 16, "Bu kartın işi sıralamayı ayarlamaktır; araçlar engine'de değilse her ayar bir kod değişikliğidir.",
            "Alan ağırlığı, sayısal sinyalle skor çarpımı, belirli ürünü öne alma, eş anlamlılar ve işaretlenmiş 200 arama üzerinde sıralama ölçümü engine'in araçlarıyla yapılabilmeli.",
            "Sıralama kodda yazılırsa pazarlama ekibi her hafta bir geliştiriciyi bekler ve bir değişikliğin sıralamayı iyileştirip iyileştirmediği ölçülemez."),
        row("EY", 12, "Her arama metin ve iş sinyallerini aynı anda sorar.",
            "Metin skoru, stok durumu, son 30 günün satışı ve kampanya etiketi tek bir sorguda, tek bir skorda birleşmeli.",
            "Sinyaller sonuç geldikten sonra uygulamada uygulanırsa yalnız ilk sayfa yeniden sıralanır; ikinci sayfadaki iyi ürün hiç görünmez."),
        row("OY", 10, "Stok ve satış sinyalleri saatte binlerce ürün için değişir.",
            "Saatte 5.000 ürünün in_stock ve sales_30d alanı değişir; değişiklik bir dakika içinde sıralamaya yansımalı.",
            "Sinyal geç yansırsa stokta olmayan ürün saatlerce ilk sırada kalır ve tıklayan ziyaretçi boş sayfa görür."),
        row("DA", 8, "Skor her aramada eşleşen ürünler üzerinde hesaplanır; yapı bunu taşımalı.",
            "Skor yalnız eşleşen ürünlerde hesaplanmalı ve en iyi 20 ürün bütün eşleşmeleri sıralamadan bulunmalı.",
            "Her aramada bütün eşleşmeleri sıralamak kampanya akşamı yavaşlar."),
        row("R2", 16, "Trafik kart 1'in trafiğidir.",
            "Kampanya akşamı saniyede 300 arama, her biri 100 ms içinde; sıralama kuralları süreyi belirgin artırmamalı.",
            "Sıralama kuralı aramayı yavaşlatırsa kazanılan dönüşüm kaybedilen sabırla gider."),
        row("R3", 6, "Arama katmanı bir kopyadır.",
            "Arama kopyası kaybolursa katalogdan yeniden kurulabilir; sıralama ayarları kaybolmamalı.",
            "Kaybolan ayarlar haftalarca ölçülerek bulunmuş ağırlıklardır."),
        row("R4", 16, "Ekip var olan sistemin üzerine kurmak istiyor.",
            "Sıralama kart 1'in arama sisteminin üzerine kurulmalı; A/B testi ve ölçüm yeni bir sistem istememeli.",
            "Sıralama için ikinci bir arama sistemi, iki sistemin sonuçlarının birbirinden kopması demektir."),
        row("R5", 16, "Sıralama ayarı bir özelliktir; ek bir filo istemez.",
            "Var olan kapasite kullanılmalı; ek maliyet küçük olmalı.",
            "Sıralama için ayrı bir sistem ödemek pazarlama bütçesini aşar."),
    ],
    cands=["os", "aur", "doc"],
    scores={
        "os": [sc(10, "function_score skoru sales_30d ve in_stock ile çarpar, pinned sorgusu kampanya ürününü öne alır, synonym filtresi eş anlamlıları ekler (Ö1, Ö3) ve _rank_eval işaretlenmiş 200 aramada sıralamayı ölçer. Puan kırılmadı."),
               sc(10, "Metin skoru ve sayısal sinyaller tek bir sorguda tek bir skordur (Ö3); sayfalama bu skorla yapılır. Puan kırılmadı."),
               sc(9, "Partial update isteği sinyal alanlarını gönderir; refresh 1 saniye sonra görünür ve bir dakikalık hedef rahatça tutulur (Ö8). 1 puan kırıldı: engine her güncellemede document'ı içeride baştan yazar ve yeniden index'ler; saniyede yaklaşık 1,4 güncelleme küçük ama sıfır olmayan bir merge yüküdür."),
               sc(10, "Skor yalnız posting list'lerdeki eşleşmeler için hesaplanır ve en iyi 20 ürün bir öncelik kuyruğuyla bulunur (Ö2). Puan kırılmadı."),
               sc(9, "Replica'lar arama yükünü paylaşır (Ö7). 1 puan kırıldı: kampanya için node'lar önceden eklenir; yeni node'un shard'ları alması dakikalar sürer."),
               sc(8, "Replica shard'lar başka AZ'dedir (Ö7). 2 puan kırıldı: domain kaybolursa katalog yeniden index'lenir; sıralama ayarları ve eş anlamlılar bu yüzden kodda ya da bir depoda da tutulur."),
               sc(9, "Kart 1'in domain'i ve ekip vardır; A/B testi iki sorgu şablonudur. 1 puan kırıldı: _rank_eval listelerini ve search pipeline sürümlerini ekip saklar."),
               sc(8, "Domain zaten ödenir. 2 puan kırıldı: function_score ve sinyal güncellemeleri için biraz daha CPU, yani daha büyük node'lar gerekebilir.")],
        "aur": [sc(5, "setweight ve ts_rank alan ağırlığı verir; ORDER BY bir ifadeyle satış ve stok sinyallerini ekler. 5 puan kırıldı: eş anlamlılar, ürün öne alma ve sıralama ölçümü için hazır araç yoktur; hepsi SQL ve uygulama kodudur."),
                sc(7, "ORDER BY ts_rank(...) * log(sales_30d) gibi bir ifade metin ve sinyalleri tek bir sırada birleştirir. 3 puan kırıldı: formül her sorguda elle yazılır ve Türkçe harf ve yazım hatası kuralları kart 1'deki gibi ayrı mekanizmalardır."),
                sc(10, "Bir UPDATE sinyal column'unu değiştirir ve commit'te görünür. Puan kırılmadı."),
                sc(7, "GIN index eşleşen row'ları bulur. 3 puan kırıldı: ifadeyle sıralama her eşleşen row'un skorunu hesaplar; sık bir kelimede binlerce row sıralanır."),
                sc(9, "Reader'lar arama yükünü paylaşır. 1 puan kırıldı: beklenmeyen bir tepe yeni reader'ın eklenmesini dakikalarca bekler."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(4, "Aurora çalışır. 6 puan kırıldı: katalog DocumentDB'dedir; arama ve sıralama için Aurora'ya bir kopya ve onu besleyen bir boru hattı gerekir."),
                sc(7, "Var olan cluster'a reader eklenir. 3 puan kırıldı: arama ve sıralama CPU'su reader ACU'su olarak ödenir.")],
        "doc": [sc(2, "$text sorgusu ve $meta textScore ile skor okunur, alan ağırlığı verilebilir. 8 puan kırıldı: eş anlamlı, öne alma, sinyalle skor çarpımı ve sıralama ölçümü yoktur. Türkçe dil desteğinin yokluğu R1.2'de sayıldı."),
                sc(4, "Aggregation pipeline textScore'u satış ve stokla birleştirip $sort ile sıralayabilir. 6 puan kırıldı: Türkçe kelime araması yoktur; birleştirme her sorguda pipeline aşamalarıyla elle yazılır."),
                sc(10, "$set sinyal field'ını yerinde değiştirir. Puan kırılmadı."),
                sc(5, "Text index eşleşen document'ları bulur. 5 puan kırıldı: pipeline'da skorla sıralama bütün eşleşmeleri okur."),
                sc(9, "Okumalar replica'lara dağılır. 1 puan kırıldı: beklenmeyen bir tepe yeni replica'nın eklenmesini dakikalarca bekler."),
                sc(10, "Katalog zaten DocumentDB'dedir. Puan kırılmadı."),
                sc(9, "Var olan cluster ve bilinen API; ikinci bir sistem yoktur. 1 puan kırıldı: sıralama pipeline'larının yükü için replica sayısını ekip seçer. Sıralama kodunun kendisi R1 · AO'da sayıldı."),
                sc(8, "Var olan cluster kullanılır. 2 puan kırıldı: sıralama pipeline'ları için replica eklenir.")],
    },
    h2h={
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora'nın artısı sinyal güncellemesindedir: bir UPDATE stok ve satış column'larını yerinde değiştirir ve commit'te görünür; R1 · OY'de OpenSearch'ün önündedir (10'a 9). ORDER BY içinde bir ifade metin skorunu satışla birleştirebilir. "
               "Ama bu kartın asıl işi sıralamayı ayarlamaktır ve araçlar Aurora'da yoktur: eş anlamlılar, belirli ürünü öne alma ve işaretlenmiş aramalarla sıralama ölçümü SQL ve uygulama koduna döner (AO'da 5). Katalog Aurora'da olmadığı için bir kopya ve boru hattı da gerekir (R4'te 4). "
               "Hangi koşul değişseydi Aurora PostgreSQL seçilirdi: katalog Aurora'da olsaydı ve sıralama kuralı yalnız \"stokta olan önce, sonra satışa göre\" gibi sabit bir ORDER BY olsaydı; ölçüm ve eş anlamlı istenmeseydi.",
        "doc": "Document (DocumentDB) ile kafa kafaya. DocumentDB'nin artısı kataloğun orada olmasıdır: sinyaller $set ile yerinde değişir, kopya ve boru hattı yoktur, ekip API'yi bilir; R3, R4 ve R5'te iyi puan alır. "
               "Ama sıralama bir arama engine'i işidir: DocumentDB'nin text index'i AWS'e göre yalnız İngilizceyi destekler, eş anlamlı, öne alma ve sıralama ölçümü yoktur ve skorla sıralama bütün eşleşmeleri okuyan bir pipeline'dır. R1'de 46 puanın 22'sini alır. Bu yüzden katalog DocumentDB'de kalır ve sıralama arama kopyasında yapılır; kart 1'deki gibi ikisi birlikte çalışır. "
               "Hangi koşul değişseydi DocumentDB seçilirdi: \"sıralama\" yalnız bir kategori sayfasında \"satışa göre sırala\" düğmesi olsaydı (metin araması olmadan); o zaman bir compound index ve bir sort yeterdi.",
    },
    verdict="Karar: OpenSearch {os}, Aurora PostgreSQL {aur}, DocumentDB {doc}. Kararı R1 · AO verir: function_score, pinned sorgusu, synonym filtresi ve _rank_eval sıralamayı ayarlamanın ve ölçmenin araçlarıdır ve engine'in içindedir. "
            "OpenSearch seçtiğimizde artımız: pazarlama ekibinin kuralları kod değil sorgu şablonudur, her değişiklik 200 işaretli aramayla ölçülür ve kart 1'in domain'i kullanılır. "
            "Eksimiz: her sinyal güncellemesi document'ı yeniden index'ler; güncellemeleri toplu (bulk) göndeririz ve refresh'i bir dakikalık hedefe göre ayarlarız; ağırlıkları ve eş anlamlıları bir depoda saklarız, çünkü index yeniden kurulabilir. "
            "Bir koşul değişseydi: sıralama yalnız sabit bir \"satışa göre\" düzeni olsaydı kataloğun database'i yeterdi."))

# ------------------------------------------------------------------ 10. anomaly detection per category and city (OpenSearch wins on its engine tool)
OPENSEARCH_W.append(wusecase("anomaly", 10,
    title="Sipariş akışında anomali tespiti: kategori ve şehir başına",
    key="Index: order-events (Aurora'dan OpenSearch Ingestion ile). Document: bir sipariş olayı; @timestamp, category ve city keyword, amount sayı. Detector: 5 dakikalık aralık, category ve city kırılımı.",
    story="Bir ödeme sağlayıcısı bir şehirde çöktüğünde ya da bir kategorinin fiyatı yanlış yüklendiğinde sipariş akışı birden düşer ya da sıçrar; Lale Market bunu bugün ertesi gün fark ediyor. "
          "Hedef: 5 kategori × 81 şehir = 405 kırılımın her biri için sipariş sayısı ve tutarı 5 dakikalık aralıklarla izlensin, normal dalgalanmayı (gece düşüşü, öğle tepesi) öğrensin ve gerçek bir sapmada 10 dakika içinde nöbetçiye haber versin; kırılım sayısı franchise planıyla 4.000'e çıkacak. "
          "Sipariş olayları Aurora'dan OpenSearch Ingestion ile zaten Lale Market'in OpenSearch domain'ine akıyor ve analistler onları Dashboards'ta inceliyor. Ekip iki analist ve bir SRE; makine öğrenmesi modeli yazmak istemiyorlar.",
    wnote="R1 toplam 42: kırılım başına normali öğrenen bir tespit aracı (AO 18), kırılım ve pencere sorusu (EY 14) ve olay verisinin biçimi (VM 10). "
          "R4 20 tek başına R1'in her alt maddesinden ağırdır, ama R1 grup olarak (42) en ağırdır: ekip model yazmak istemiyor ve yeni bir sistem işletmek istemiyor. R5 18: kırılım sayısı faturayı belirler.",
    rows=[
        row("AO", 18, "Bu kartın işi \"normal\"i öğrenen bir araçtır; ekip model yazmak istemiyor.",
            "Her kırılım için normal dalgalanmayı kendisi öğrenen, bir sapmaya bir skor veren ve skoru bir bildirime bağlayan bir araç engine'de olmalı.",
            "Sabit eşik (\"saatte 10 siparişin altı\") gece her gün yanlış alarm verir, öğle tepesinde gerçek düşüşü kaçırır; model elle yazılırsa iki analist onu bakımla geçirir."),
        row("EY", 14, "Soru her zaman \"bu kırılımın son 5 dakikası\"dır.",
            "Kategori ve şehir kırılımında, 5 dakikalık pencerelerde sipariş sayısı ve tutar; aynı veride analist bir sapmanın siparişlerine inebilmeli.",
            "Pencere hesabı her kırılım için ayrı bir sorgu olursa 4.000 kırılım 4.000 sorgu demektir."),
        row("VM", 10, "Veri sipariş olaylarıdır; sayılara çevrilmeden saklanması analiste iniş yolu verir.",
            "Her sipariş bir olaydır (kategori, şehir, tutar, ödeme sağlayıcısı); sayılar bu olaylardan hesaplanmalı ve olayların kendisi aranabilmeli.",
            "Olaylar yalnız önceden hesaplanmış sayılara çevrilirse \"hangi ödeme sağlayıcısı\" sorusu sorulamaz."),
        row("R2", 14, "Kampanya günü sipariş akışı on kat; tespit 10 dakika içinde olmalı.",
            "Normalde saniyede 5, kampanya günü saniyede 50 sipariş olayı; her kırılım 5 dakikada bir değerlendirilir ve bildirim 10 dakika içinde gider.",
            "Tespit gecikirse ödeme sağlayıcısı çöktüğü sürece satış kaybolur."),
        row("R3", 6, "Siparişlerin kaydı Aurora'dadır; tespit verisi bir kopyadır.",
            "Olay kopyası kaybolursa Aurora'dan yeniden yüklenebilir; detector'ların öğrendiği model kaybolursa yeniden öğrenir.",
            "Kopya kaybı birkaç saatlik tespit boşluğudur; sipariş kaybı değildir."),
        row("R4", 20, "İki analist ve bir SRE; ekip yeni bir sistem ve model bakımı istemiyor.",
            "Olayların zaten aktığı sistemin üzerine kurulmalı; detector ve bildirim bir ayar olmalı, kod olmamalı.",
            "Yeni bir sistem ya da her kırılım için elle kurulan alarm üç kişilik ekibin bütün zamanını alır."),
        row("R5", 18, "Kırılım sayısı 405'ten 4.000'e çıkacak; fatura kırılım sayısıyla patlamamalı.",
            "4.000 kırılımda da fatura öngörülebilir kalmalı.",
            "Kırılım başına ödenen bir modelde franchise planı faturayı on katına çıkarır."),
    ],
    cands=["os", "ix", "cw"],
    scores={
        "os": [sc(9, "Anomaly Detection, Random Cut Forest ile her kırılımın normalini kendisi öğrenir, bir anomaly grade ve confidence verir ve Alerting ile bildirime bağlanır; category ve city kırılım alanı (high cardinality) olarak seçilir (Ö5 üzerine kurulu). 1 puan kırıldı: detector'ın özellikleri (count, sum) tasarlanır ve model ısınana kadar bir süre veri ister."),
               sc(10, "date_histogram ve terms aggregation'ları kırılım ve pencereyi tek bir sorguda verir (Ö5); analist aynı index'te bir sapmanın siparişlerini arar. Puan kırılmadı."),
               sc(10, "Her sipariş bir document'tır; alanlar keyword ve sayıdır ve olayların kendisi aranır (Ö2). Puan kırılmadı."),
               sc(9, "Detector'lar 5 dakikada bir çalışır ve olaylar saniyeler içinde aranabilir (Ö8). 1 puan kırıldı: detector'lar Dashboards sorgularıyla aynı node'larda çalışır."),
               sc(8, "Replica shard'lar ve saatlik snapshot. 2 puan kırıldı: domain kaybolursa olaylar Aurora'dan yeniden yüklenir ve modeller yeniden ısınır."),
               sc(8, "Olaylar domain'e zaten akar; detector ve monitor bir ayardır. 2 puan kırıldı: kırılım sayısı büyüdükçe Anomaly Detection'ın bellek sınırı izlenir ve node'lar büyütülür."),
               sc(8, "Domain zaten ödenir; kırılım başına ücret yoktur. 2 puan kırıldı: 4.000 kırılımın modelleri için daha büyük data node'lar gerekebilir.")],
        "ix": [sc(4, "Task'lar zamanlanmış Flux ya da InfluxQL sorgularıdır ve bir eşik hesabı yapabilir. 6 puan kırıldı: engine'de normali öğrenen bir tespit aracı yoktur; mevsimsellik ve eşikler ekibin yazdığı istatistik koduyla hesaplanır."),
               sc(10, "Kategori ve şehir tag'leri ile 5 dakikalık aggregateWindow kırılım ve pencereyi tek bir sorguda verir. Puan kırılmadı."),
               sc(7, "Bir nokta tag'ler ve field'larla saklanır; sayılar serilerden hesaplanır. 3 puan kırıldı: olay bir sipariş kaydı olarak değil bir ölçüm olarak saklanır; analistin bir sapmanın siparişlerine inişi başka bir sistemdedir."),
               sc(9, "Saniyede 50 nokta bir instance için küçüktür. 1 puan kırıldı: bütün yazmalar tek bir instance'tan geçer."),
               sc(8, "Multi-AZ standby. 2 puan kırıldı: failover sırasında birkaç dakikalık boşluk olabilir ve veri Aurora'dan yeniden yüklenir."),
               sc(5, "Yönetilen instance. 5 puan kırıldı: yeni bir sistemdir; instance sınıfı, Aurora'dan akış ve bildirim kanalı ekibin işidir. Tespit kodu R1 · AO'da sayıldı."),
               sc(8, "Instance-saat ve depolama ödenir; kırılım sayısı faturayı doğrudan büyütmez. 2 puan kırıldı: Multi-AZ db.influx.medium ayda yaklaşık 210 dolar gece de çalışır (Frankfurt).")],
        "cw": [sc(7, "Anomaly detection bir metric ve istatistik için normali öğrenir (saatlik, günlük ve haftalık desenler) ve bir alarm bandı verir. 3 puan kırıldı: model metric başınadır; 4.000 kırılım 4.000 ayrı model ve alarm demektir ve kırılımlar arasında öğrenme yoktur."),
               sc(7, "Dimension'lı metric'ler kırılımı verir; 5 dakikalık periyotla Sum ve SampleCount okunur. 3 puan kırıldı: her kategori ve şehir birleşimi uygulamadan ayrı bir metric olarak yayınlanır."),
               sc(6, "Metric bir sayıdır; olayın kendisi saklanmaz. 4 puan kırıldı: siparişler yayından önce sayılara çevrilir; \"hangi ödeme sağlayıcısı\" sorusu için olaylara başka bir sistemde inilir."),
               sc(10, "Metric yazma ve alarm değerlendirme kapasitesi servisindir. Puan kırılmadı."),
               sc(10, "Metrikler servis tarafından kalıcı saklanır. Puan kırılmadı."),
               sc(7, "Sunucu yoktur ve alarm aynı servistedir. 3 puan kırıldı: 4.000 alarmın kurulması ve bakımı (örneğin altyapı kodu ile) ekibin işidir. Metric'leri yayınlayan kod R1 · EY'de sayıldı."),
               sc(4, "Metric ve alarm başına ödenir. 6 puan kırıldı: 4.000 custom metric ayda yaklaşık 1.200 dolardır (Frankfurt, 0,30 dolar) ve buna her kırılımın alarmı eklenir.")],
    },
    h2h={
        "ix": "Zaman serisi (Timestream for InfluxDB) ile kafa kafaya. InfluxDB'nin artısı pencere sorusudur: kategori ve şehir tag'leriyle 5 dakikalık toplam tek bir sorgudur ve seri sayısı faturayı büyütmez (R5). Kart 7'de bu yüzden kazanmıştı. "
              "Ama bu kartın işi \"normal\"i öğrenmektir ve engine'de bunu yapan bir araç yoktur: task'lar zamanlanmış sorgulardır, gece düşüşünü ve öğle tepesini öğrenen istatistik ekibin yazacağı koddur (AO'da 4). Yeni bir sistem olarak instance, Aurora'dan akış ve bildirim de ekibin işidir (R4'te 5). "
              "Hangi koşul değişseydi Timestream for InfluxDB seçilirdi: kırılımlar sabit eşiklerle izlenebilseydi (\"saatte 10 siparişin altı\") ve ekipte zaman serisi istatistiği bilen biri olsaydı; ya da metrikler zaten InfluxDB'de olsaydı.",
        "cw": "İzleme servisi (CloudWatch) ile kafa kafaya. CloudWatch'un anomaly detection'ı gerçek bir aracıdır: bir metric'in saatlik, günlük ve haftalık desenlerini öğrenir ve bir alarm bandı verir; kapasite ve kalıcılık servisindir (R2, R3). Birkaç kırılım için en basit cevaptır. "
              "Ama model metric başınadır: 405 kırılım bugün 405, yarın 4.000 ayrı metric, model ve alarm demektir; her kırılımı uygulama ayrı bir metric olarak yayınlar ve olayların kendisi saklanmaz. Bu R1'de üç alt maddede, R4'te ve R5'te kayıptır: 4.000 metric ayda yaklaşık 1.200 dolardır. "
              "Hangi koşul değişseydi CloudWatch seçilirdi: yalnız toplam sipariş akışı ve birkaç ödeme sağlayıcısı izlenseydi (on kadar metric) ve olaylar zaten OpenSearch'e akmasaydı.",
    },
    verdict="Karar: OpenSearch {os}, Timestream for InfluxDB {ix}, CloudWatch {cw}. Kararı R1 · AO verir: Random Cut Forest ile kırılım başına normali öğrenen bir detector ve Alerting engine'in içindedir ve olaylar zaten domain'dedir. "
            "OpenSearch seçtiğimizde artımız: 405 kırılım tek bir detector'dır, model yazılmaz, analist sapmanın siparişlerine aynı Dashboards'ta iner. "
            "Eksimiz: detector özelliklerini tasarlarız ve modellerin ısınmasını bekleriz; kırılım sayısı büyüdükçe Anomaly Detection'ın bellek sınırını izler ve node'ları büyütürüz; bu araç yönetilen domain'dedir, Serverless'ın API listesinde yoktur. "
            "Bir koşul değişseydi: yalnız birkaç toplam metric izlenseydi CloudWatch'un anomaly detection alarmı daha basit olurdu."))

USECASES_W["opensearch"] = OPENSEARCH_W
PAGE_SVC["opensearch"] = "os"


# ====================================================================== Amazon Redshift Serverless (page id "redshift"), Turkish, model 2
# Ten weighted cards of the Redshift page. "rs" is Redshift Serverless (the page's service); "rsp" is a Redshift provisioned
# cluster: the same engine (twin rule), so the two always get the same R1 points and only R2-R5 separate them.
# Card 1 repeats Aurora card 6 ("reporting") and card 4 repeats Keyspaces card 7 ("clicks"): rows, weights and points are
# copied from those cards in code (decisions.md, "The same workload on two pages"); only the Redshift reasons are rewritten
# with the feature numbers of this page, and the feature numbers of the other pages are removed from the borrowed reasons.
# Sources of the limits and numbers in the reasons (the hedges are the hedges of the source), all read on 2026-10-31:
#  - Columnar store, 1 MB blocks, compression encodings (AZ64, LZO, ZSTD): https://aws.amazon.com/blogs/big-data/getting-the-most-out-of-your-analytics-stack-with-amazon-redshift/
#  - Zone map: min and max per 1 MB block, sort key: https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-sort-key.html,
#    https://aws.amazon.com/blogs/big-data/amazon-redshift-engineerings-advanced-table-design-playbook-compound-and-interleaved-sort-keys/
#  - Distribution styles AUTO, EVEN, KEY, ALL; "Your fact table can have only one distribution key":
#    https://docs.aws.amazon.com/redshift/latest/dg/c_choosing_dist_sort.html, https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-best-dist-key.html
#  - "Using individual INSERT statements to populate a table might be prohibitively slow": https://docs.aws.amazon.com/redshift/latest/dg/r_INSERT_30.html
#  - Deleted rows are "marked for deletion, but not removed"; automatic VACUUM DELETE: https://docs.aws.amazon.com/redshift/latest/dg/t_Reclaiming_storage_space202.html
#  - Unique, primary key and foreign key constraints are informational, "not enforced"; NOT NULL is enforced:
#    https://docs.aws.amazon.com/redshift/latest/dg/t_Defining_constraints.html
#  - SNAPSHOT (default) and SERIALIZABLE isolation: https://docs.aws.amazon.com/redshift/latest/dg/c_serial_isolation.html
#  - Materialized views, incremental refresh: https://docs.aws.amazon.com/redshift/latest/dg/materialized-view-refresh.html
#  - Result cache on the leader node, invalidated by INSERT, DELETE, UPDATE, COPY: https://docs.aws.amazon.com/redshift/latest/dg/c_challenges_achieving_high_performance_queries.html
#  - Serverless: one RPU = 16 GB, default base 128 RPU, base from 4 RPU: https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-capacity.html;
#    RPU-hours "on a per-second basis (with a 60-second minimum charge)", Spectrum and concurrency scaling included: https://aws.amazon.com/redshift/pricing/;
#    "When no queries are running, you aren't billed for compute capacity": https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-billing-on-demand.html
#  - Recovery points every 30 minutes, kept 24 hours: https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-snapshots-recovery-points.html
#  - Price List API, eu-central-1, 2026-10-31: Serverless 0.451 USD per RPU-hour on demand, 0.352 USD with a 1-year reservation;
#    ra3.4xlarge (12 vCPU, 96 GiB) 3.894 USD/h on demand, 1.6939 USD/h with a 3-year reservation (no upfront); ra3.large 0.649 USD/h;
#    managed storage 0.0256 USD per GB-month.
#  - Zero-ETL from Aurora: "within seconds of being written" (https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/zero-etl.html); in this
#    workshop a new order reached aurora_live in about 30 seconds (two measurements, 2026-10-31); source tables need a primary key:
#    https://docs.aws.amazon.com/redshift/latest/mgmt/zero-etl.reqs-lims.html
#  - Data sharing of live data across workgroups, accounts and Regions: https://docs.aws.amazon.com/redshift/latest/dg/datashare-overview.html
#  - Streaming ingestion from Kinesis Data Streams and MSK into a materialized view: https://docs.aws.amazon.com/redshift/latest/dg/materialized-view-streaming-ingestion.html
#  - Redshift ML: CREATE MODEL in SQL, trained with SageMaker AI Autopilot: https://docs.aws.amazon.com/redshift/latest/gsg/machine-learning.html
#  - Athena: "$5 per TB of data scanned", 10 MB minimum per query, columnar formats and partitions reduce the scan:
#    https://docs.aws.amazon.com/whitepapers/latest/big-data-analytics-options/amazon-athena.html
CATEGORY.setdefault("ath", ("query engine on S3", "S3 üzerinde sorgu motoru"))
LINK.setdefault("ath", "redshift")     # Athena has no page yet; the Redshift page (cards 2, 5, 6, 7, 10) compares them
CATEGORY.setdefault("rsp", ("data warehouse", "data warehouse"))
LINK.setdefault("rsp", "redshift")     # the provisioned cluster is the twin of Redshift Serverless, taught on this page (M5, C2)

_RS_A6 = next(u for u in AURORA_W if u["id"] == "reporting")
_RS_K7 = next(u for u in KEYSPACES_W if u["id"] == "clicks")


def _rsx(t):
    """Remove the feature numbers of another page (Ö3 of Aurora is not Ö3 of Redshift) and use the page's word "kolon"."""
    t = re.sub(r"\s*\((?:Ö\d(?:, )?)+\)", "", t)
    for a, c in (("column'unu", "kolonunu"), ("column'u", "kolonu"), ("column'ları", "kolonları"), ("column bazlı", "kolon bazlı"), (" column ", " kolon ")):
        t = t.replace(a, c)
    return t


def _rcopy(uc):
    return [row(r["code"], r["w"], _rsx(r["wwhy"][1]), _rsx(r["want"][1]), _rsx(r["why"][1])) for r in uc["rows"]]


def _rborrow(uc, c):
    return [sc(p, _rsx(w[1])) for p, w in uc["scores"][c]]


def _rsame(uc, c, mine):
    assert [p for p, _ in mine] == [p for p, _ in uc["scores"][c]], f"{uc['id']}: {c} must keep the points of the other page"
    return mine


REDSHIFT_W = []

# ------------------------------------------------------------------ 1. sales reporting over three years (= Aurora card 6)
REDSHIFT_W.append(wusecase("reporting", 1, sim="w_reporting",
    title="Yıllar boyu satış raporları: son 90 günden üç yıllık geçmişe",
    key="Fact table: sipariş satırları (order_date, customer_id, category, amount); sort key order_date, distribution key customer_id. Kaynak Aurora, kopya zero-ETL ile.",
    story=_rsx(_RS_A6["story"][1]),
    wnote=_RS_A6["wnote"][1],
    rows=_rcopy(_RS_A6),
    cands=["rs", "os", "aur"],
    scores={
        "rs": _rsame(_RS_A6, "rs", [
            sc(10, "Kolon bazlı saklama (Ö1): veri 1 MB'lık bloklarda kolon kolon durur ve tarama sadece sorgunun üç dört kolonunu okur; bloklar sıkıştırılmıştır (Ö2). Puan kırılmadı."),
            sc(10, "Analitik SQL (Ö5): JOIN, GROUP BY ve window function'lar; analistler bildikleri SQL'i yazar ve yeni bir soru yeni bir cümledir. Puan kırılmadı."),
            sc(9, "Kolon başına sıkıştırma (Ö2), sort key ile blok atlama (Ö3) ve materialized view (Ö6) engine'in kendi araçlarıdır. 1 puan kırıldı: sort key ve distribution seçimi bir tasarım işidir."),
            sc(9, "Columnar engine ekleme akışını blok blok kabul eder (Ö7). 1 puan kırıldı: tek row'luk bir güncelleme eski row'u silinmiş işaretleyip yenisini ekler; çok güncellenen veride arka plandaki VACUUM ve sıralama işi artar."),
            sc(10, "MPP (Ö4): sorgu bütün slice'lara paylaştırılır ve Serverless kapasiteyi eşzamanlı sorgulara göre artırır (Ö8); checkout ayrı bir database'tedir ve taramayı hissetmez. Puan kırılmadı."),
            sc(9, "Recovery point'ler 30 dakikada bir alınır ve 24 saat tutulur; elle snapshot da alınır. 1 puan kırıldı: kopya kaybolursa zero-ETL entegrasyonu yeniden kurulur ve ilk yükleme sürer."),
            sc(9, "Zero-ETL (Ö7) kod yazmadan kurulur; AWS kopyanın \"within seconds of being written\" güncellendiğini söyler, bu workshop'ta yeni bir sipariş yaklaşık 30 saniyede görünür. 1 puan kırıldı: workgroup'un base ve en fazla RPU ayarları ekibin işidir; sort key ve distribution tasarımı R1.3'te sayıldı."),
            sc(8, "Serverless RPU-saat olarak, saniye başına ve 60 saniye minimumla ödenir; sorgu yokken compute ödenmez (Ö8). 2 puan kırıldı: dashboard'lar her beş dakikada yenilendiği için mesai boyunca kapasite çalışır; base RPU dikkatle seçilmelidir.")]),
        "aur": _rborrow(_RS_A6, "aur"),
        "os": _rborrow(_RS_A6, "os"),
    },
    h2h={"aur": _rsx(_RS_A6["h2h"]["aur"][1]), "os": _rsx(_RS_A6["h2h"]["os"][1])},
    verdict="Karar: Redshift {rs}, OpenSearch {os}, Aurora {aur}. OpenSearch ile Aurora birbirine çok yakındır (0,2 puan). Kararı R1'in depolama satırı ve R2 verir: geçmişin tamamını tarayan ama birkaç kolon okuyan sorgular columnar (Ö1) ve MPP (Ö4) bir engine ister. Bu kart Aurora sayfasının 6. kartıyla aynı iş yüküdür ve aynı puanları taşır. "
            "Redshift seçtiğimizde artımız: checkout taramayı hiç hissetmez, analistler aynı SQL'i yazar, kopya zero-ETL ile kod yazmadan gelir, boşta compute ödenmez. "
            "Eksimiz: ikinci bir sistem ve verinin ikinci kopyası; kopya Aurora'dan yaklaşık 30 saniye geridedir, uygulama dashboard'da \"veri şu ana kadar\" saatini göstermelidir; sort key ve distribution kararları ekibin işidir. "
            "Doğru mimari ikisi birliktedir: Aurora kayıt sistemi, Redshift rapor tarafı. Bir koşul değişseydi: raporlar son 90 günle sınırlı kalsaydı ve birkaç analist günde birkaç sorgu çalıştırsaydı Aurora'nın reader'ı yeterdi."))

# ------------------------------------------------------------------ 2. marketing attribution (close race with Athena)
REDSHIFT_W.append(wusecase("attribution", 2, sim="w_attribution",
    title="Pazarlama attribution'ı: hangi reklam tıklaması satışı getirdi",
    key="Fact table'lar: ad_clicks (S3'te Parquet, her gece) ve orders. Ortak kolon customer_id: distribution key; ad_clicks'in sort key'i click_time.",
    story="Lale Market üç reklam ağında kampanya yürütüyor. Ağlar tıklama dosyalarını her gece S3'e Parquet olarak bırakıyor: yılda 900 milyon tıklama. Siparişler Aurora'da, ayda 600.000 sipariş; veri ekibi siparişleri zaten her gece S3'e de yazıyor. "
          "Pazarlama her sabah 08:00'de \"son tıklama, 7 gün penceresi\" modeliyle her siparişi aynı müşterinin siparişten önceki son tıklamasına bağlamak istiyor. İş en geç 08:30'da bitmeli. "
          "Sonra gün boyunca üç analist sonucu kampanyaya, kanala ve cihaza göre kesiyor; haftada bir \"ilk tıklama\" ve \"eşit pay\" modelleriyle karşılaştırma yapılıyor. "
          "Ekip SQL biliyor; yarı zamanlı bir veri mühendisi var. Sonuçlar kaynaklardan yeniden hesaplanabilir.",
    wnote="R1 toplam 46: işin kendisi büyük bir JOIN ve \"son olanı seç\" sorusudur (EY 16) ve 900 milyon tıklamanın birkaç kolonunu tarar (DA 14). "
          "R4 18 ile en ağır ikinci satır: yarı zamanlı tek bir mühendis var ve veri iki yerde duruyor. R3 6'dır, çünkü sonuçlar kaynaktan yeniden hesaplanır.",
    rows=[
        row("EY", 16, "Attribution'ın kendisi bir JOIN ve bir window sorusudur; her model değişikliği bu satırı değiştirir.",
            "Her siparişi aynı müşterinin 7 gün içindeki son tıklamasına bağlayan tek bir SQL: müşteriye göre JOIN, zamana göre sıralama, ROW_NUMBER ya da LAST_VALUE ile \"son olanı seç\". Model değişince SQL değişmeli, kod değil.",
            "Attribution yanlışsa bütçe yanlış kanala gider. Her model değişikliği bir yazılım projesi olursa pazarlama yeni modeli hiç denemez."),
        row("DA", 14, "Her sabah bir yılın tıklamaları taranır ama her tıklamanın dört kolonu okunur.",
            "900 milyon tıklamanın sadece customer_id, click_time, campaign ve channel kolonları okunmalı; tarama 30 dakikalık pencereye sığmalı.",
            "Tam row'ları okuyan bir tarama her sabah yüzlerce GB okur ve 08:30 sınırı kaçar."),
        row("AO", 10, "İki büyük table aynı müşteri kolonu üzerinden birleşir; birlikte durmaları süreyi belirler.",
            "Engine'in kendi araçlarıyla join'in ve taramanın maliyeti azaltılabilmeli: veri yerleşimi ayarlanabilmeli, tarih aralığı dışındaki veri hiç açılmamalı, gün içindeki kesitler için ara sonuç saklanabilmeli.",
            "Bu araçlar yoksa her sabah aynı join ve aynı tarama baştan yapılır ve süre ile fatura büyür."),
        row("OY", 6, "Yazma şekli basittir: gecede bir kez yeni dosyalar ve ara sıra bir iade.",
            "Her gece yeni tıklamalar toplu eklenmeli; bir iade siparişin durumunu değiştirdiğinde bir sonraki sabah hesaba girmeli.",
            "Toplu ekleme yavaşsa sabah işi başlamadan gecikir; iade görünmezse iade edilen siparişler kampanyalara sayılır."),
        row("R2", 16, "Sabah 30 dakikalık ağır bir iş, gün içinde hafif kesitler: iki farklı yük.",
            "08:00–08:30 arasında tek bir ağır join; gün içinde üç analistin kesitleri saniyeler içinde dönmeli. Checkout bu işleri hissetmemeli.",
            "Sabah işi 08:30'u geçerse günlük bütçe kararı eski rakamla verilir."),
        row("R3", 6, "Sonuçlar kaynaklardan yeniden hesaplanabilir.",
            "Kaynaklar S3'te ve Aurora'dadır; sonuç table'ı kaybolursa bir sabah işiyle geri gelir. Günlük yedek yeterlidir.",
            "Kayıp bir günlük rapor gecikmesidir; para kaybı değildir."),
        row("R4", 18, "Yarı zamanlı tek bir mühendis var ve veri iki yerde duruyor.",
            "Yeni bir boru hattı yazılmadan kurulmalı; tıklama dosyaları her gece kendiliğinden okunmalı; analistler SQL dışında bir araç öğrenmemeli.",
            "Elle yazılan her iş tek mühendisin zamanını alır; o tatildeyken rapor durur."),
        row("R5", 14, "Günde bir ağır iş ve hafif kesitler: ödeme modeli bu şekle uymalı.",
            "Ağır iş günde 30 dakika sürer; günün geri kalanında az sorgu vardır. Kullanım kadar ödeme isteniyor; aynı veriyi iki kez saklamak istenmiyor.",
            "7/24 çalışan kapasite günün 23 saati boş durur. Tıklamaların ikinci bir kopyası her ay storage faturasına eklenir."),
    ],
    cands=["rs", "ath", "aur"],
    scores={
        "rs": [sc(10, "Analitik SQL (Ö5): JOIN ve ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY click_time DESC) tek cümlede; model değişince sadece SQL değişir. Puan kırılmadı."),
               sc(10, "Tıklamalar her gece COPY ile kolon bazlı bloklara yüklenir (Ö1, Ö7); sorgu dört kolonu okur ve click_time sort key'i aralık dışındaki blokları atlar (Ö3). Puan kırılmadı."),
               sc(9, "İki table da DISTKEY customer_id ile aynı slice'larda durur ve join yerel çalışır (Ö4); ara sonuç materialized view olarak saklanır (Ö6). 1 puan kırıldı: sort key ve distribution seçimi bir tasarım işidir."),
               sc(9, "Gecelik COPY toplu eklemenin kendisidir (Ö7); iadeler zero-ETL ile gelir. 1 puan kırıldı: güncellenen row eskisini silinmiş işaretler ve arka plandaki VACUUM işi artar."),
               sc(10, "MPP (Ö4) sabah işini bütün slice'lara böler; Serverless kapasiteyi işin süresince artırır (Ö8); checkout ayrı database'tedir. Puan kırılmadı."),
               sc(9, "Recovery point'ler 30 dakikada bir alınır ve 24 saat tutulur. 1 puan kırıldı: kopya kaybolursa COPY ve zero-ETL ile yeniden yükleme sürer."),
               sc(8, "Siparişler zero-ETL ile, tıklamalar zamanlanmış bir COPY cümlesiyle gelir; ikisi de kod değil SQL'dir (Ö7). 2 puan kırıldı: gecelik COPY'nin zamanlaması ve hata takibi ile workgroup'un base RPU ayarı ekibin işidir; sort key ve distribution tasarımı R1.3'te sayıldı."),
               sc(7, "RPU-saat, saniye başına ödenir ve sorgu yokken compute ödenmez (Ö8). Kaba tahmin: 32 RPU ile sabah 30 dakika, ayda yaklaşık 480 RPU-saat, yani 216 USD (0,451 USD/RPU-saat); gün içi kesitler bunun üstüne eklenir. 3 puan kırıldı: tıklamalar hem S3'te hem managed storage'da saklanır ve ikinci kopya GB başına ödenir; günde bir saatten az iş için bile kapasite-saat ödenir.")],
        "ath": [sc(10, "Athena'nın SQL engine'i (Trino) JOIN ve window function'ları tam olarak destekler; aynı SQL çalışır. Puan kırılmadı."),
                sc(8, "Parquet kolon bazlı bir dosya biçimidir; sorgu dört kolonu ve tarih partition'larını okur. 2 puan kırıldı: dosyaları reklam ağları yazar ve içleri click_time'a göre sıralı değildir; Parquet'in row group istatistikleri bir günün içindeki aralığı az eler."),
                sc(7, "Tarihe göre partition ve müşteriye göre bucketing yapılabilir. 3 puan kırıldı: materialized view yoktur ve verinin yerleşimi engine'in değil dosyaları yazan işin kararıdır; join'de eşleşen row'lar her sorguda ağ üzerinden yeniden dağıtılır."),
                sc(9, "Yeni gece dosyaları S3'e eklenir ve table hemen görür; siparişler her gece tam bir snapshot olarak yazıldığı için iadeler de girer. 1 puan kırıldı: gecelik snapshot her gün bütün sipariş dosyalarını yeniden yazar."),
                sc(8, "Serverless; sorgu başına kapasite servisindir. 2 puan kırıldı: büyük join'ler hesap başına eşzamanlı sorgu kotasına ve sorgu kaynak sınırlarına takılabilir; sabah işi bir kez yeniden denenirse 08:30 kaçar."),
                sc(10, "Veri S3'te birden fazla Availability Zone'da durur. Puan kırılmadı."),
                sc(8, "Veri zaten S3'tedir; table tanımları Glue Data Catalog'dadır ve yeni bir boru hattı gerekmez. 2 puan kırıldı: dosya boyutu, partition ve bucketing düzeni ekibin işidir."),
                sc(9, "Taranan TB başına ödenir (yaklaşık 5 USD/TB); boş saatler sıfırdır. Kaba tahmin: dört kolonun bir yılı Parquet'te birkaç on GB'tır, sabah işi ayda 1 TB'ın altında, yani birkaç on USD. 1 puan kırıldı: ödeme sorgu sayısıyla büyür; gün içindeki her kesit ayrı bir ödemedir.")],
        "aur": [sc(10, "PostgreSQL SQL'i JOIN ve window function'ları tam olarak destekler. Puan kırılmadı."),
                sc(3, "Index dar aralıkları hızlandırır. 7 puan kırıldı: PostgreSQL row'ları tam saklar; bir yılın tıklamalarını tarayan sorgu, dört kolon gerekse de her row'un tamamını okur."),
                sc(6, "Zamana göre partition, BRIN index ve materialized view kullanılabilir. 4 puan kırıldı: kolon bazlı sıkıştırma yoktur ve materialized view'lar elle yenilenir."),
                sc(8, "aws_s3 extension'ı ile dosyalar her gece table'a yüklenir; iadeler zaten Aurora'dadır. 2 puan kırıldı: 900 milyon row'luk table'a her gece toplu yazma index'leri de günceller."),
                sc(5, "Sabah işi bir reader instance'ta çalışır ve writer'ın CPU'sunu kullanmaz. 5 puan kırıldı: reader'lar checkout ile aynı storage'ı okur ve büyük tarama storage I/O'sunu checkout ile paylaşır; tarama süresinin kendisi R1 · DA'da sayıldı."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(6, "Siparişler zaten oradadır. 4 puan kırıldı: tıklamaları her gece yükleyen iş, partition bakımı ve materialized view yenilemesi yarı zamanlı mühendisin işidir."),
                sc(4, "Reader instance saat başına ödenir. 6 puan kırıldı: sabah işini 30 dakikada bitirecek büyük bir reader 7/24 çalışır ve tıklamalar row storage'da index'leriyle birlikte saklanır.")],
    },
    h2h={
        "ath": "S3 üzerinde sorgu motoru (Athena) ile kafa kafaya. Bu kart yakın bir yarıştır ve iki servis aynı SQL'i yazar: JOIN ve window function ikisinde de vardır (R1.1 eşit). Farkı R1'in depolama satırları verir. "
               "Redshift tıklamaları her gece kendi kolon bloklarına yükler, müşteriye göre aynı slice'lara dağıtır ve join yerel çalışır; Athena her sabah dosyaları S3'ten yeniden okur ve iki büyük table'ı join için ağ üzerinden yeniden dağıtır. "
               "Athena'nın dürüst üstünlüğü servis tarafındadır: veri zaten S3'tedir, ikinci bir kopya yoktur ve boş saatler sıfıra iner (R5). Redshift ise tıklamaların ikinci bir kopyasını tutar ve yükleme zamanlamasını işletir. "
               "Hangi koşul değişseydi Athena seçilirdi: attribution haftada bir çalışsaydı, gün içi kesitler olmasaydı ya da sabah işinin bir saatlik penceresi olsaydı; o zaman veriyi yerinde sorgulamanın sadeliği depolama farkından ağır basardı.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora'nın gücü gerçektir: siparişler zaten oradadır, SQL aynıdır ve iadeler anında görünür. "
               "Ama attribution her sabah bir yılın 900 milyon tıklamasını tarar ve PostgreSQL row'ları tam olarak saklar; dört kolon isteyen sorgu her row'un tamamını okur (R1.2). Büyük tarama checkout'un storage'ını paylaşan bir reader'da çalışır (R2) ve 30 dakikalık pencereyi garanti etmek için büyük bir reader 7/24 ödenir (R5). "
               "Tıklamaları her gece Aurora'ya yükleyen iş de yarı zamanlı mühendisin işidir. "
               "Hangi koşul değişseydi Aurora seçilirdi: tıklama verisi yılda 900 milyon değil birkaç milyon olsaydı ve attribution son 30 günle sınırlı kalsaydı; o zaman checkout'un yanındaki bir reader yeterdi.",
    },
    verdict="Karar: Redshift {rs}, Athena {ath}, Aurora {aur}. Yakın bir yarış: iki servis de aynı SQL'i yazar; kararı R1'in depolama satırları verir, yani kolon blokları, sort key ve aynı müşterinin row'larının aynı slice'ta durması (Ö1, Ö3, Ö4). "
            "Redshift seçtiğimizde artımız: sabah işi yerel bir join'dir ve 08:30'a rahat yetişir, gün içi kesitler materialized view'dan saniyeler içinde döner, siparişler zero-ETL ile kod yazmadan gelir. "
            "Eksimiz: tıklamaların ikinci bir kopyası managed storage'da ödenir ve gecelik COPY zamanlanmalıdır; uygulama COPY başarısız olursa sabah işini başlatmamalı ve dashboard'da \"dünün verisi eksik\" uyarısını göstermelidir. "
            "Bir koşul değişseydi: attribution haftada bir çalışsaydı ve gün içi kesitler olmasaydı Athena öne geçerdi; tıklamalar yerinde kalır ve sadece taranan veri ödenirdi."))

# ------------------------------------------------------------------ 3. financial close (Aurora wins R1, Redshift wins on service design; twin)
REDSHIFT_W.append(wusecase("finclose", 3,
    title="Ay sonu finansal kapanış: üç yoğun gün, yirmi yedi sakin gün",
    key="Fact table: journal_lines (account_id, cost_center, period, amount), Aurora'dan zero-ETL ile; düzeltme kayıtları Redshift'in dev database'inde ayrı bir table'da (adjustments), çünkü zero-ETL kopyası salt okunurdur. Sort key period, distribution key account_id.",
    story="Lale Market'in muhasebe defteri siparişlerle aynı Aurora cluster'ındadır ve zero-ETL ile Redshift'e kopyalanır: yılda 80 milyon defter satırı. Her ayın ilk üç iş günü 12 muhasebeci kapanış yapar: 09:00–19:00 arasında yaklaşık 400 ağır sorgu (mizan, masraf merkezine göre dağılım, kur farkı). "
          "Kapanış sırasında muhasebeciler kapanış aracından birkaç bin düzeltme kaydı girer; araç bu kayıtları kapanış raporlarının çalıştığı database'e yazar. Her düzeltme kaydının borç ve alacağı eşit olmalı ve hesap kodu var olmalı. "
          "Bütün kapanış raporları ayın son gününün 23:59 hâlini görmeli. Ayın geri kalan 27 gününde günde birkaç sorgu çalışır. Ekipte bir finans BI geliştiricisi var; finans müdürü öngörülebilir bir fatura istiyor.",
    wnote="R1 toplam 42: soruların biçimi (EY 10), bir yılın defterini taramak (DA 10), düzeltme kaydının kuralları (ŞE 14) ve kapanışın tek bir ânı görmesi (TA 8). "
          "R5 20 ve R2 18 ile hemen arkasında: yük ayın üç gününde toplanır ve ödeme modeli bu şekle uymalıdır.",
    rows=[
        row("EY", 10, "Kapanış soruları değişmez ama karmaşıktır: hesap ağacı, masraf merkezi, kur.",
            "Mizan, masraf merkezine göre dağılım ve kur farkı SQL ile yazılmalı: JOIN, GROUP BY ve dönem sonu bakiyesi için window function.",
            "Bir rapor SQL ile yazılamazsa muhasebeci veriyi Excel'e indirir ve kapanışın izi kaybolur."),
        row("DA", 10, "Her rapor bir dönemin ya da bir yılın defter satırlarını tarar.",
            "Bir yılın 80 milyon satırından birkaç kolonu okuyan tarama bir dakikanın altında dönmeli.",
            "Rapor dakikalar sürerse 400 sorgu üç güne sığmaz ve kapanış gecikir."),
        row("ŞE", 14, "Düzeltme kayıtları bu database'e yazılır ve kuralları yazma anında korunmalı.",
            "Database bir düzeltme kaydını borç ve alacak eşit değilse ya da hesap kodu yoksa reddetmeli: CHECK, foreign key ve satırları birlikte denetleyen kural.",
            "Dengesiz bir düzeltme mizanı bozar; hata ancak denetimde bulunursa kapanış yeniden yapılır."),
        row("TA", 8, "400 sorgu üç gün boyunca aynı ânı görmeli; bir düzeltmenin satırları birlikte yazılmalı.",
            "Bir düzeltme kaydının satırları ya hep ya hiç yazılmalı; kapanış raporları ayın son gününün 23:59 hâlini görmeli, kaynak değişmeye devam etse de.",
            "İki rapor iki farklı ânı görürse mizan ile masraf merkezi raporu birbirini tutmaz."),
        row("R2", 18, "Yük ayın üç gününde toplanır: 400 ağır sorgu, 12 kişi aynı anda.",
            "Üç gün boyunca 12 kişinin eşzamanlı ağır sorguları beklemeden dönmeli; ayın geri kalanında günde birkaç sorgu.",
            "Sorgular kuyrukta beklerse 12 muhasebeci aynı anda bekler; kapanış bir gün kayarsa yönetim raporu gecikir."),
        row("R3", 8, "Kapanış sonuçları denetim için yeniden üretilebilmeli.",
            "Bir kapanışın verisi aylar sonra aynı hâliyle açılabilmeli; düzeltme kayıtları kaybolmamalı.",
            "Denetçi bir rakamın kaynağını sorduğunda aynı rakam yeniden üretilemezse kapanış tekrar açılır."),
        row("R4", 12, "Tek bir BI geliştiricisi var; kapasite planlamak istemiyor.",
            "Ay başı için kapasite elle eklenmemeli; sunucu, düğüm sayısı ve bakım penceresi planlanmamalı.",
            "Kapasite planı unutulursa kapanışın ilk sabahı yavaş başlar ve tek geliştirici bunu çözmeye çalışır."),
        row("R5", 20, "Yük ayın 3 gününde, fatura 30 günde: fiyat modeli bu kartın kararıdır.",
            "Ödeme yoğun üç güne göre olmalı; sakin 27 günde neredeyse sıfır. Finans müdürü öngörülebilir bir fatura istiyor.",
            "Üç güne göre boyutlanan kapasite 27 gün boş durur ve ödenir."),
    ],
    cands=["rs", "aur", "rsp"],
    scores={
        "rs": [sc(10, "Analitik SQL (Ö5): JOIN, GROUP BY ve SUM() OVER ile dönem sonu bakiyesi tek cümlededir. Puan kırılmadı."),
               sc(10, "Kolon bazlı saklama (Ö1) ve period sort key'i (Ö3): sorgu sadece dönemin bloklarını ve birkaç kolonu okur. Puan kırılmadı."),
               sc(5, "NOT NULL uygulanır. 5 puan kırıldı: Redshift unique, primary key ve foreign key kurallarını \"not enforced\" olarak, yani sadece bilgi olarak tutar; CHECK yoktur. Dengesiz kaydı ve olmayan hesap kodunu kapanış aracı ya da bir kontrol sorgusu yakalamalıdır."),
               sc(9, "Transaction'lar SNAPSHOT (varsayılan) ya da SERIALIZABLE izolasyonla çalışır; bir düzeltmenin satırları tek transaction'da yazılır (Ö7). 1 puan kırıldı: kaynak zero-ETL ile değişmeye devam eder; 23:59 hâli için kapanış başında bir CREATE TABLE AS kopyası alınır."),
               sc(10, "Serverless (Ö8) üç gün boyunca kapasiteyi eşzamanlı sorgulara göre artırır ve MPP (Ö4) her sorguyu slice'lara böler. Puan kırılmadı."),
               sc(9, "Recovery point'ler 30 dakikada bir alınır ve 24 saat tutulur; her kapanışın snapshot'ı elle alınır ve tutulur. 1 puan kırıldı: defter bir kopyadır; kaybolursa zero-ETL entegrasyonu yeniden kurulur ve ilk yükleme sürer."),
               sc(9, "Düğüm planı yoktur; kapasite yükle gelir (Ö8). 1 puan kırıldı: base RPU ve en fazla RPU sınırı ekibin işidir; tablo tasarımı R1'de sayıldı."),
               sc(9, "Sorgu yokken compute ödenmez; 12 kişinin ağır sorguları için ortalama 32 RPU varsayımıyla (kaba tahmin) yoğun üç gün 3 gün × 10 saat × 32 RPU = 960 RPU-saat, yani eu-central-1'de yaklaşık 433 USD (0,451 USD/RPU-saat, Price List API, 2026-10-31); sakin günler birkaç dolardır. 1 puan kırıldı: her sorgu en az 60 saniye ödenir.")],
        "aur": [sc(10, "PostgreSQL SQL'i JOIN, GROUP BY ve window function'ları tam olarak destekler. Puan kırılmadı."),
                sc(4, "Dönem partition'ı ve index'ler taramayı bir aya daraltır. 6 puan kırıldı: PostgreSQL row'ları tam saklar; yıllık raporlar 80 milyon row'un tamamını okur. Bu kartın verisi raporlama kartının iki milyar row'undan küçüktür, bu yüzden 7 değil 6 puan."),
                sc(10, "CHECK, foreign key ve commit anında denetlenen bir constraint trigger dengesiz düzeltmeyi ve olmayan hesap kodunu reddeder. Puan kırılmadı."),
                sc(9, "Ya hep ya hiç transaction ve row lock. 1 puan kırıldı: üç gün boyunca aynı ânı görmek için kapanış başında bir kopya table ya da dönem kilidi gerekir; tek bir transaction üç gün açık tutulamaz."),
                sc(5, "Raporlar bir reader'da çalışır ve Serverless v2 ACU'su artar. 5 puan kırıldı: defter siparişlerle aynı cluster'dadır; reader'lar checkout'un yazdığı storage'ı okur ve 400 ağır sorgu storage I/O'sunu checkout ile paylaşır; tarama süresinin kendisi R1 · DA'da sayıldı."),
                sc(10, "Üç AZ'de altı kopya ve point-in-time restore. Puan kırılmadı."),
                sc(8, "Boru hattı yoktur, defter zaten oradadır. 2 puan kırıldı: dönem partition'larının ve materialized view'ların bakımı tek geliştiricinin işidir."),
                sc(6, "Serverless v2 reader ACU-saat olarak ödenir ve sakin günlerde küçülür. 4 puan kırıldı: minimum ACU her gün ödenir ve Standard yapılandırmada her taramanın I/O'su ayrıca ödenir.")],
        "rsp": [sc(10, "Aynı engine: analitik SQL (Ö5) Serverless ile aynıdır. Puan kırılmadı."),
                sc(10, "Aynı kolon bazlı saklama ve sort key (Ö1, Ö3). Puan kırılmadı."),
                sc(5, "Aynı engine, aynı kural: unique, primary key ve foreign key uygulanmaz, CHECK yoktur. 5 puan kırıldı: kontrol kapanış aracındadır."),
                sc(9, "Aynı transaction modeli. 1 puan kırıldı: 23:59 hâli için CREATE TABLE AS kopyası gerekir."),
                sc(7, "Concurrency scaling kuyruktaki sorgular için geçici cluster'lar açar. 3 puan kırıldı: ana cluster'ın düğüm sayısı sabittir; ağır sorgular önce kuyrukta bekler ve concurrency scaling her cluster için günde bir saatlik ücretsiz kredinin ötesinde ayrıca ödenir."),
                sc(9, "Otomatik ve elle snapshot'lar. 1 puan kırıldı: defter bir kopyadır; kaybolursa entegrasyon yeniden kurulur."),
                sc(6, "Yönetilen cluster. 4 puan kırıldı: düğüm tipi ve sayısı seçilir, ay başında resize ya da pause/resume zamanlaması tek geliştiricinin işidir."),
                sc(5, "Düğüm saat başına ödenir. 5 puan kırıldı: üç güne göre seçilen düğümler ayın tamamında çalışır, örneğin iki ra3.xlplus eu-central-1'de ayda yaklaşık 1.895 USD (düğüm başına 1,298 USD/saat); pause/resume bunu azaltır ama elle planlanır.")],
    },
    h2h={
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Bu kart sayfanın dürüst bir kartıdır: engine uyumunu (R1) Aurora 1 puanla kazanır, toplamı Redshift alır. "
               "Aurora'nın üstünlüğü kural satırıdır (R1.3): CHECK, foreign key ve commit anında denetlenen kural dengesiz bir düzeltmeyi database'in kendisinde reddeder; Redshift primary key ve foreign key'i sadece planner için bilgi olarak tutar ve kontrol kapanış aracına kalır. "
               "Redshift'in üstünlüğü tarama ve servis satırlarındadır: yılın defterini kolon bloklarından okur (R1.2), yoğun üç günde kapasiteyi kendisi artırır (R2) ve sakin 27 günde compute ödemez (R5). "
               "Hangi koşul değişseydi Aurora seçilirdi: kapanış raporları sadece bir ayı okusaydı ve yük ay boyunca düz olsaydı; o zaman kurallar ve var olan cluster ağır basardı. Düzeltme kayıtlarını Aurora'da tutup raporları Redshift'te çalıştırmak da doğru bir \"ikisi birlikte\" tasarımıdır.",
        "rsp": "Data warehouse, provisioned cluster (Redshift provisioned) ile kafa kafaya. İki servis aynı engine'i çalıştırır: R1 puanları aynıdır ve farkı sadece servis tasarımı verir. "
               "Provisioned cluster'ın dürüst üstünlüğü düz ve sürekli yükte görünür: düğümler önceden ayrılır, rezervasyonla saat fiyatı düşer ve bakım penceresi bilinir (kart 8). "
               "Bu kartta yük ayın üç gününde toplanır. Provisioned cluster ya üç güne göre boyutlanır ve 27 gün boş durur ya da daha küçük seçilir ve kapanışın ilk sabahı sorgular kuyrukta bekler; concurrency scaling bunu kısmen çözer ama ayrıca ödenir. Serverless kapasiteyi yükle getirir ve sakin günlerde compute ödemez. "
               "Hangi koşul değişseydi Redshift provisioned seçilirdi: kapanış ayın tamamına yayılsaydı, cluster başka işlerle 7/24 dolu olsaydı ya da ekipte cluster işleten deneyimli bir DBA olsaydı.",
    },
    verdict="Karar: Redshift {rs}, Aurora {aur}, Redshift provisioned {rsp}. Kararı R5 ve R2 verir: yük ayın üç gününde toplanır ve Serverless kapasiteyi yükle getirip sakin günlerde compute ödemez (Ö8). R1'de Aurora 1 puan öndedir, çünkü düzeltme kaydının kurallarını database'in kendisi korur. "
            "Redshift seçtiğimizde artımız: 400 ağır sorgu üç günde beklemeden döner, fatura üç güne göre çıkar, aynı SQL ve aynı engine. "
            "Eksimiz: Redshift düzeltme kaydının dengesini ve hesap kodunu denetlemez; kapanış aracı her kaydı yazmadan önce doğrulamalı ve kapanış başında bir kontrol sorgusu dengesiz kayıt aramalıdır. 23:59 hâli için kapanış başında bir CREATE TABLE AS kopyası alınmalıdır. "
            "Bir koşul değişseydi: kapanış ayın tamamına yayılsaydı ve cluster 7/24 dolu olsaydı provisioned cluster öne geçerdi; düzeltmeler başka bir sistemden doğrulanmadan gelseydi Aurora'da kalmaları gerekirdi."))

# ------------------------------------------------------------------ 4. click stream: "continue where you left off" (= Keyspaces card 7; Redshift third)
REDSHIFT_W.append(wusecase("clicks", 4, sim="w_clicks",
    title="Tıklama akışı: kaldığın yerden devam et, haftalık okuma raporu",
    key="Kişi başına şerit için partition key user_id, clustering column clicked_at (en yeni önce), TTL 30 gün. Haftalık rapor için analiz kopyası: Redshift.",
    story=_RS_K7["story"][1],
    wnote=_RS_K7["wnote"][1],
    rows=_rcopy(_RS_K7),
    cands=["ks", "ddb", "rs"],
    scores={
        "ks": _rborrow(_RS_K7, "ks"),
        "ddb": _rborrow(_RS_K7, "ddb"),
        "rs": _rsame(_RS_K7, "rs", [
            sc(4, "Sort key'i okuyucu ve zaman olan bir table son 100 tıklamayı bulur (Ö3). 6 puan kırıldı: her ana sayfa açılışında tek bir okuyucunun row'larını getiren bir point lookup columnar ve MPP bir engine'in işi değildir; her sorgu leader node'da planlanır ve 20 ms'nin altı garanti edilmez. Table'ın tek bir sırası vardır: okuyucuya göre sıralanırsa haftalık rapor tarih aralığını daha az eler."),
            sc(10, "Kolon bazlı saklama (Ö1) ve MPP (Ö4), haftanın bütün tıklamalarını kategoriye ve saate göre gruplamanın kendisidir. Puan kırılmadı."),
            sc(5, "Streaming ingestion tıklamaları mikro-batch'lerle bir materialized view'a ekler (Ö7). 5 puan kırıldı: saniyede binlerce tek tek küçük ekleme columnar bloklara uymaz; AWS tek tek INSERT için \"prohibitively slow\" der, yazma toplu olmalıdır."),
            sc(6, "Eski veri tarih aralığıyla silinir. 4 puan kırıldı: süre sonu yoktur; silme zamanlanmış bir DELETE işidir ve silinen row'lar arka plandaki VACUUM'a kadar yer tutar."),
            sc(8, "Streaming ingestion (Ö7) tepeyi bir akış katmanı (Kinesis) üzerinden mikro-batch'lerle karşılar; AWS her yenilemenin saniyede yüzlerce MB alabildiğini söyler. 2 puan kırıldı: on-demand bir stream son 30 günün tepesinin iki katına kadar kendiliğinden uyar; yeni bir rekor sıçrama bunu aşabilir (Keyspaces ve DynamoDB ile aynı kırılım). Şeridin 20 ms'lik okuması R1.1'de, akış katmanının işletilmesi R4'te sayıldı."),
            sc(9, "Recovery point'ler ve akış katmanındaki saklama. 1 puan kırıldı: akış katmanındaki son saniyeler bir arızada yeniden oynatılır."),
            sc(4, "Analistlerin SQL'i aynı sistemde, ikinci bir kopya olmadan çalışır (Ö5); DynamoDB'de de SQL zero-ETL ile kod yazmadan gelir, bu yüzden SQL iki adayı ayırmaz. 6 puan kırıldı: sessionization işleri Spark Cassandra Connector'ından Redshift'e yeniden yazılır, DynamoDB'deki gibi iki ay (5); akış katmanı (Kinesis ve streaming ingestion) ayrıca işletilir (1)."),
            sc(6, "RPU-saat ve akış katmanı ödenir. 4 puan kırıldı: istek başına ödeme yoktur; şerit sorguları gün boyu geldiği için Serverless kapasite gün boyu açık kalır.")]),
    },
    h2h={"ddb": _rsx(_RS_K7["h2h"]["ddb"][1]), "rs": _rsx(_RS_K7["h2h"]["rs"][1])},
    verdict="Karar: Keyspaces {ks}, DynamoDB {ddb}, Redshift {rs}. Redshift bu kartı net kaybeder ve kaybı R1'in erişim yolundan gelir: ana sayfa şeridi her açılışta tek bir okuyucunun son 100 tıklamasını 20 ms'nin altında ister, bu bir point lookup'tır ve columnar bir engine'in işi değildir. Bu kart Keyspaces sayfasının 7. kartıyla aynı iş yüküdür ve aynı puanları taşır. "
            "Yine de Redshift seçersek artımız: haftalık rapor tek bir SQL'dir ve bütün okuyucuları saniyeler içinde gruplar (Ö1, Ö4). "
            "Eksimiz: şerit için ayrı bir cache ya da key-value store gerekir; tıklamalar bir akış katmanından mikro-batch'lerle gelir; 30 günlük silme zamanlanmış bir DELETE işidir. "
            "Doğru mimari ikisi birliktedir: şerit Keyspaces'te, haftalık rapor Redshift'te; CDC stream'i tıklamaları S3 üzerinden Redshift'e taşır. Bir koşul değişseydi: şerit olmasaydı ve iş yalnız haftalık rapor olsaydı Redshift en uygun servis olurdu."))

# ------------------------------------------------------------------ 5. data sharing between teams and accounts
REDSHIFT_W.append(wusecase("datashare", 5,
    title="Ekipler ve hesaplar arası veri paylaşımı: tek kopya, ayrı compute",
    key="Üretici: satış table'ları (iki milyar row) tek bir workgroup'ta. Tüketiciler: finans, pazarlama ve başka bir AWS hesabındaki tedarikçi portalı; her biri kendi compute'uyla.",
    story="Lale Market büyüdü ve üç ekip aynı satış verisine bakıyor: finans, pazarlama ve ayrı bir AWS hesabında çalışan tedarikçi portalı. Bugün veri ekibi her gece satış table'larını CSV olarak dışa aktarıyor ve her ekip kendi kopyasını yüklüyor; sabahları üç ekip üç farklı rakam söylüyor. "
          "Satış geçmişi iki milyar row ve Redshift'te. Pazarlama kampanya akşamları ağır sorgular çalıştırıyor ve finansın raporlarını yavaşlatmamalı. Tedarikçi portalının 120 tedarikçisi var; her tedarikçi sadece kendi ürünlerinin satışını görmeli. "
          "Yeni bir satış bütün ekiplere aynı anda görünmeli. Veri ekibi iki kişi; her ekip kendi sorgularının faturasını ödemek istiyor.",
    wnote="R1 toplam 44: paylaşılan table'lar üzerinde serbest SQL (EY 12), büyük taramalar (DA 12), tedarikçinin sadece kendi row'larını görmesi (AO 12) ve herkesin aynı commit'i görmesi (TA 8). "
          "R4 18 ile ikinci: tek kopya ve hesaplar arası yetki işin kendisidir. R2 ve R5 16'şar: her ekip kendi compute'unu ve faturasını istiyor.",
    rows=[
        row("EY", 12, "Her ekip kendi sorularını SQL ile soruyor.",
            "Paylaşılan table'lar üzerinde JOIN ve GROUP BY içeren serbest SQL; her ekip kendi view'larını ve table'larını yanına ekleyebilmeli.",
            "Paylaşılan veri sadece hazır raporlarla açılırsa ekipler yine kendi kopyalarını çıkarır."),
        row("DA", 12, "Pazarlamanın kampanya sorguları iki milyar row'u tarar.",
            "İki milyar row'un birkaç kolonunu okuyan taramalar saniyeler içinde dönmeli.",
            "Tarama yavaşsa pazarlama veriyi yine kendi tarafına kopyalar."),
        row("AO", 12, "120 tedarikçi aynı table'ı görür ama sadece kendi row'larını.",
            "Engine'in kendi aracıyla row bazında erişim kuralı: tedarikçi T042 sadece supplier_id = T042 olan satışları görür; kural her sorguya kendiliğinden uygulanır.",
            "Kural uygulamada kalırsa bir hata bir tedarikçiye rakibinin satışlarını gösterir; bu bir sözleşme ihlalidir."),
        row("TA", 8, "Üç ekip sabah aynı rakamı söylemeli.",
            "Yeni bir satış commit edildiği anda bütün tüketicilere görünmeli; her tüketici tutarlı bir ân görmeli.",
            "Kopyalar farklı saatlerde güncellenirse ekipler yine farklı rakam söyler."),
        row("R2", 16, "Pazarlamanın kampanya akşamı finansı yavaşlatmamalı.",
            "Her ekip kendi compute'unda çalışmalı; bir ekibin ağır sorgusu diğerinin kuyruğuna girmemeli.",
            "Tek bir compute paylaşılırsa kampanya akşamı finansın kapanış raporu bekler."),
        row("R3", 6, "Satış geçmişi Aurora'dan gelen bir kopyadır.",
            "Paylaşılan veri kaybolursa kaynaktan yeniden yüklenebilir; günlük yedek yeterlidir.",
            "Kayıp birkaç saatlik bir rapor kesintisidir."),
        row("R4", 18, "Tek kopya ve hesaplar arası yetki bu işin kendisidir; veri ekibi iki kişi.",
            "Gece CSV aktarımı kalkmalı; başka bir AWS hesabına veri kopyalamadan erişim verilmeli; yetki tek yerden yönetilmeli.",
            "Her ekip için ayrı bir kopya ve ayrı bir aktarım işi iki kişilik ekibin her sabahını alır."),
        row("R5", 16, "Her ekip kendi sorgularının faturasını istiyor.",
            "Her tüketici kendi compute'unu öder; verinin ikinci kopyası için storage ödenmez.",
            "Bütün sorgular tek bir faturada toplanırsa pazarlamanın kampanyası finansın bütçesinden ödenir."),
    ],
    cands=["rs", "ath", "rsp"],
    scores={
        "rs": [sc(10, "Analitik SQL (Ö5); tüketici paylaşılan table'ların yanına kendi view ve table'larını ekler. Puan kırılmadı."),
               sc(10, "Kolon bazlı saklama, sort key ve MPP (Ö1, Ö3, Ö4) tüketicinin compute'unda da aynı şekilde çalışır. Puan kırılmadı."),
               sc(9, "Datashare yalnız seçilen nesneleri açar (Ö8); tedarikçi workgroup'unda paylaşılan table üzerine bir view kurulur: view, oturumun kullanıcısını (current_user) bir eşleme table'ında tedarikçi id'sine çevirir ve sadece o supplier_id'nin row'larını döndürür; tedarikçiye ana table değil sadece view açılır. AWS data sharing'de ince erişim için view'ları önerir; üretici tarafında row-level security policy'leri de vardır. 1 puan kırıldı: view'lar, role'ler ve datashare izinleri bir tasarım işidir."),
               sc(10, "Data sharing canlı veriyi paylaşır: AWS'e göre veri \"live and available to all warehouses as soon as a write transaction is committed\" (Ö8). Puan kırılmadı."),
               sc(10, "Her tüketici kendi Serverless workgroup'unda çalışır ve kendi kapasitesi yüküyle artar (Ö8); pazarlamanın akşamı finansın kuyruğuna girmez. Puan kırılmadı."),
               sc(9, "Recovery point'ler ve snapshot'lar üretici tarafındadır. 1 puan kırıldı: veri bir kopyadır; kaybolursa yeniden yükleme sürer."),
               sc(9, "Tek kopya; hesaplar ve Region'lar arası paylaşım bir datashare ile kurulur, CSV aktarımı kalkar (Ö8). 1 puan kırıldı: hesaplar arası paylaşımda iki hesapta da yetkilendirme adımları vardır."),
               sc(9, "Her tüketici kendi RPU-saatini öder; paylaşılan veri için ikinci storage ödenmez. 1 puan kırıldı: her sorgu en az 60 saniye ödenir.")],
        "rsp": [sc(10, "Aynı engine: analitik SQL (Ö5). Puan kırılmadı."),
                sc(10, "Aynı kolon bazlı saklama, sort key ve MPP (Ö1, Ö3, Ö4). Puan kırılmadı."),
                sc(9, "Aynı datashare ve aynı view'lar (Ö8). 1 puan kırıldı: view'lar, role'ler ve izinler bir tasarım işidir."),
                sc(10, "RA3 cluster'ları aynı canlı data sharing'i kullanır (Ö8). Puan kırılmadı."),
                sc(8, "Her tüketici kendi cluster'ında çalışır. 2 puan kırıldı: her cluster'ın düğüm sayısı sabittir; pazarlamanın kampanya akşamı kendi cluster'ının tepesine çarpar."),
                sc(9, "Otomatik ve elle snapshot'lar. 1 puan kırıldı: veri bir kopyadır."),
                sc(6, "Aynı datashare kurulumu. 4 puan kırıldı: her ekip bir cluster işletir; düğüm tipi, sayı ve resize üç ayrı ekip için iki kişilik veri ekibinin işidir."),
                sc(5, "Her tüketici kendi cluster'ını öder. 5 puan kırıldı: üç cluster 7/24 saat başına ödenir; tedarikçi portalının seyrek sorguları için de bütün ay düğüm çalışır.")],
        "ath": [sc(10, "Athena'nın SQL engine'i (Trino) JOIN ve GROUP BY'ı tam olarak destekler. Puan kırılmadı."),
                sc(9, "Parquet kolon bazlıdır ve partition'lar taramayı daraltır. 1 puan kırıldı: dosyaların içi sıralı değilse row group istatistikleri az şey atlatır."),
                sc(7, "View'lar ve partition'lar engine'in araçlarıdır. 3 puan kırıldı: row bazında kural engine'de değil Lake Formation'ın veri filtresindedir; materialized view yoktur."),
                sc(9, "Iceberg table'larında her commit bir snapshot'tır ve okuyan commit edilmiş tutarlı bir ân görür. 1 puan kırıldı: düz Parquet table'larında transaction yoktur; paylaşım Iceberg biçimini gerektirir. Verinin bugün Redshift'te durması ve aktarım gecikmesi R4'te sayıldı."),
                sc(9, "Her hesap kendi workgroup'unda sorgular; kapasite servisindir. 1 puan kırıldı: hesap başına eşzamanlı sorgu kotası vardır."),
                sc(10, "Veri S3'te birden fazla Availability Zone'da durur. Puan kırılmadı."),
                sc(5, "Lake Formation hesaplar arası yetkiyi tek yerden verir. 5 puan kırıldı: satış verisi Redshift'tedir; S3'e Iceberg olarak düzenli aktarım yeni bir boru hattıdır, CSV işinin yerine başka bir aktarım gelir ve tüketiciler satışın commit anını değil aktarımın son hâlini görür."),
                sc(8, "Her hesap taradığı TB başına öder (yaklaşık 5 USD/TB); boş saatler sıfırdır. 2 puan kırıldı: birim sorgu başına olduğu için fatura sorgu sayısıyla sınırsız büyür; kampanya akşamlarının yoğun sorgularında kapasite-saat modeli gibi bir tavan yoktur.")],
    },
    h2h={
        "rsp": "Data warehouse, provisioned cluster (Redshift provisioned) ile kafa kafaya. Aynı engine, aynı data sharing: R1 puanları birebir aynıdır. Fark tüketici tarafındaki compute'un servis tasarımındadır. "
               "Provisioned cluster ile her ekip bir cluster seçer, boyutlandırır ve 7/24 öder; tedarikçi portalı gibi seyrek bir tüketici için de düğümler bütün ay çalışır. Serverless'ta her tüketici bir workgroup'tur, kapasitesi yüküyle gelir ve sorgu yokken compute ödenmez. "
               "Provisioned'ın dürüst üstünlüğü yoğun ve düz bir tüketicide görünür: rezervasyonla saat fiyatı düşer ve kapasite her an hazırdır. "
               "Hangi koşul değişseydi Redshift provisioned seçilirdi: tüketicilerden biri 7/24 düz ve yoğun çalışsaydı (örneğin bütün gün dolu bir operasyon ekranı); o tüketici bir rezervasyonlu cluster, diğerleri Serverless olurdu. Data sharing ikisini karıştırmaya izin verir.",
        "ath": "S3 üzerinde sorgu motoru (Athena) ile kafa kafaya. Athena'nın gücü veri gölü paylaşımıdır: veri S3'te bir kez durur, Lake Formation hesaplar arası yetkiyi ve row filtresini verir, her hesap taradığı kadar öder. Veri zaten S3'te olsaydı bu güçlü bir tasarımdır. "
               "Bu kartta satış geçmişi Redshift'tedir. Athena ile paylaşmak için önce düzenli bir S3 aktarımı gerekir (R4); tüketiciler satışın commit anını değil aktarımın son hâlini görür (R4); row kuralı engine'de değil ayrı bir serviste durur (R1.3). Data sharing ise aynı veriyi kopyasız ve commit anında açar. "
               "Veri zaten S3'te Iceberg olarak dursaydı fark kabaca 95'e 86'ya inerdi; Redshift yine önde kalırdı, çünkü kolon blokları, view'lar ve kopyasız commit anı R1'de kalır. "
               "Hangi koşul değişseydi Athena seçilirdi: paylaşılan veri seyrek sorulan bir veri gölü olsaydı, yani veri S3'te Iceberg, tüketiciler haftada birkaç soru soruyor ve kampanya akşamı gibi bir yük yok (kart 10'daki gibi).",
    },
    verdict="Karar: Redshift {rs}, Athena {ath}, Redshift provisioned {rsp}. Kararı R4, R2 ve R1'in tutarlılık satırı verir: data sharing aynı veriyi kopyasız ve commit anında açar (Ö8) ve her tüketici kendi Serverless compute'unda çalışır. "
            "Redshift seçtiğimizde artımız: gece CSV işi kalkar, üç ekip aynı rakamı görür, tedarikçi sadece kendi satışlarını görür, her ekip kendi faturasını öder. "
            "Eksimiz: tedarikçi view'ları, role'ler ve datashare izinleri doğru tasarlanmalıdır; yeni bir tedarikçi eklenince uygulama onun role eşleşmesini de eklemelidir ve tedarikçiye ana table değil sadece view açılmalıdır; üretici workgroup'u bir arızada kapanırsa tüketiciler de veriyi göremez. "
            "Bir koşul değişseydi: veri zaten S3'te Iceberg table'ları olarak dursa bile Redshift önde kalırdı (kabaca 95'e 86); Athena ancak paylaşılan veri seyrek sorulan bir veri gölü olduğunda öne geçer (kart 10)."))

# ------------------------------------------------------------------ 6. ML feature preparation (both together with SageMaker)
REDSHIFT_W.append(wusecase("mlfeatures", 6,
    title="Machine learning için feature hazırlığı: churn modeli",
    key="Feature table: customer_features (customer_id, 140 kolon), her gece CREATE TABLE AS ile; kaynak üç yıllık satış ve tıklama table'ları.",
    story="İki veri bilimci müşterinin ayrılma (churn) olasılığını tahmin eden bir model kuruyor. Her gece 2 milyon müşteri için 140 feature hesaplanmalı: son 30, 90 ve 365 günün harcaması, sipariş aralıklarının ortalaması, iade oranı, kategori dağılımı, son tıklamadan bu yana geçen gün. "
          "Kaynak üç yıllık satış geçmişi (iki milyar row) ve tıklamalar; ikisi de Redshift'te. İş 02:00–04:00 arasında bitmeli; sabah CRM her müşterinin skorunu okur. "
          "Model haftada bir yeniden eğitilir. Veri bilimciler SQL ve Python biliyor; özel modellerini Python'da yazmak istiyorlar. Feature'lar kaynaktan yeniden hesaplanabilir.",
    wnote="R1 toplam 44: feature'ların kendisi müşteri başına window ve aggregate sorularıdır (EY 14) ve üç yılı tarar (DA 14); gece sonucu toplu yazılır (OY 8) ve tekrar eden ara sonuçlar saklanır (AO 8). "
          "R4 20 ile en ağır ikinci satır: iki kişilik ekip hem SQL hem Python ile çalışıyor ve modeli bir yerde eğitmesi gerekiyor.",
    rows=[
        row("EY", 14, "Her feature müşteri başına bir pencere ya da toplam sorusudur.",
            "Müşteri başına 30/90/365 günlük toplamlar, sipariş aralıklarının ortalaması (LAG), kategori payları: hepsi SQL'de window function ve GROUP BY ile yazılabilmeli.",
            "Feature'lar SQL'de yazılamazsa veri bilimciler iki milyar row'u Python'a çeker ve iş gece penceresine sığmaz."),
        row("DA", 14, "Her gece üç yılın birkaç kolonu taranır.",
            "İki milyar row'un customer_id, order_date, amount ve category kolonları okunmalı; tarama gece penceresinin küçük bir kısmını almalı.",
            "Tam row'ları okuyan bir tarama gece penceresini doldurur ve sabah skorları eksik kalır."),
        row("OY", 8, "Sonuç her gece bir kez, toplu olarak yazılır.",
            "2 milyon row × 140 kolonluk feature table'ı her gece tek bir toplu yazmayla yeniden oluşturulmalı.",
            "Feature'lar row row yazılırsa yazma saatler sürer."),
        row("AO", 8, "Tekrar eden ara sonuçlar ve modelin kendisi engine'in araçlarıyla tutulabilmeli.",
            "Tekrar eden ara sonuçlar (müşteri başına aylık toplam) engine'in kendi aracıyla saklanabilmeli ve yeni satışlarla artımlı yenilenebilmeli.",
            "Her gece aynı aylık toplamlar baştan hesaplanırsa iş iki katı sürer."),
        row("R2", 14, "İki saatlik gece penceresi; gündüz yük yok.",
            "02:00–04:00 arasında ağır bir iş; gündüz neredeyse hiç sorgu yok. Checkout bunu hissetmemeli.",
            "İş 04:00'ü geçerse CRM sabah eski skorlarla çalışır."),
        row("R3", 6, "Feature'lar kaynaktan yeniden hesaplanır.",
            "Feature table'ı kaybolursa bir gece işiyle geri gelir; günlük yedek yeterlidir.",
            "Kayıp bir günlük eski skordur."),
        row("R4", 20, "İki kişilik ekip hem SQL hem Python ile çalışıyor.",
            "Feature'lar SQL'de; özel modeller Python'da. Veri bilimciler veriyi dışa aktarma işi yazmadan notebook'tan okuyabilmeli; model eğitimi ve skorların CRM'e dönüşü kurulabilmeli.",
            "Her adım için ayrı bir aktarım işi yazılırsa iki kişilik ekip model yerine boru hattıyla uğraşır."),
        row("R5", 16, "Günde iki saatlik iş: ödeme modeli bu şekle uymalı.",
            "Günde iki saat ödeme; gündüz sıfıra yakın. Model eğitiminin maliyeti ayrıca görünmeli.",
            "7/24 çalışan kapasite günün 22 saati boş durur."),
    ],
    cands=["rs", "ath", "aur"],
    scores={
        "rs": [sc(10, "Analitik SQL (Ö5): SUM() OVER, LAG ve GROUP BY ile 140 feature tek bir CREATE TABLE AS cümlesinde yazılır. Puan kırılmadı."),
               sc(10, "Kolon bazlı saklama ve sort key (Ö1, Ö3): tarama dört kolonu okur; MPP (Ö4) işi slice'lara böler. Puan kırılmadı."),
               sc(10, "CREATE TABLE AS feature table'ını bütün slice'larda paralel ve toplu yazar (Ö7). Puan kırılmadı."),
               sc(9, "Müşteri başına aylık toplamlar materialized view olarak artımlı yenilenir (Ö6). 1 puan kırıldı: artımlı yenileme SELECT, JOIN, GROUP BY ve aggregate'li tanımlar içindir; window function'lı bir ara sonuç tam yenilenir, bu yüzden ara sonuçlar aggregate olarak tasarlanır."),
               sc(10, "Serverless gece işi için kapasiteyi artırır ve MPP işi böler (Ö4, Ö8); checkout ayrı database'tedir. Puan kırılmadı."),
               sc(9, "Recovery point'ler 30 dakikada bir. 1 puan kırıldı: kopya kaybolursa yeniden yükleme sürer."),
               sc(8, "Veri bilimciler Data API ile notebook'tan SQL çalıştırır; feature table'ı UNLOAD ile S3'e Parquet olarak yazılır; Redshift ML basit modelleri CREATE MODEL ile SQL'den eğitir. 2 puan kırıldı: Redshift ML'in eğitimi SageMaker AI'da çalışır; Python'daki özel modeller için SageMaker ayrıca kurulur ve işletilir."),
               sc(8, "Gece iki saat RPU-saat; gündüz compute ödenmez (Ö8). 2 puan kırıldı: model eğitimi SageMaker'da ayrıca ödenir ve feature table'ı managed storage'da ikinci bir kopya olarak durur.")],
        "ath": [sc(10, "Athena'nın SQL engine'i (Trino) window function'ları ve GROUP BY'ı tam olarak destekler. Puan kırılmadı."),
                sc(8, "Parquet kolon bazlıdır ve partition'lar taramayı daraltır. 2 puan kırıldı: dosyalar müşteriye göre bir arada durmaz; büyük join'lerde eşleşen row'lar her sorguda ağ üzerinden yeniden dağıtılır."),
                sc(8, "CTAS sonucu S3'e Parquet olarak yazar. 2 puan kırıldı: her gece feature table'ının dosyaları baştan yazılır; eski dosyaların temizliği ayrıca yapılır."),
                sc(7, "Partition ve bucketing engine'in araçlarıdır. 3 puan kırıldı: materialized view yoktur; ara sonuç her gece bir CTAS ile baştan yazılır."),
                sc(8, "Serverless. 2 puan kırıldı: büyük join'ler hesap başına eşzamanlı sorgu kotasına ve sorgu kaynak sınırlarına takılabilir."),
                sc(10, "Sonuç S3'te birden fazla Availability Zone'da durur. Puan kırılmadı."),
                sc(5, "SageMaker notebook'ları S3'teki Parquet'i doğrudan okur. 5 puan kırıldı: satış ve tıklamalar Redshift'tedir; S3'e düzenli aktarım yeni bir boru hattıdır."),
                sc(9, "Taranan TB başına ödenir (yaklaşık 5 USD/TB); gündüz sıfırdır. 1 puan kırıldı: model eğitimi yine SageMaker'da ayrıca ödenir.")],
        "aur": [sc(10, "PostgreSQL SQL'i window function'ları ve GROUP BY'ı tam olarak destekler. Puan kırılmadı."),
                sc(3, "Index dar aralıkları hızlandırır. 7 puan kırıldı: PostgreSQL row'ları tam saklar; üç yılı tarayan sorgu her row'un tamamını okur."),
                sc(8, "INSERT INTO ... SELECT tek bir cümledir. 2 puan kırıldı: her gece 2 milyon row'un yeniden yazılması eski row sürümleri bırakır ve VACUUM işi artar."),
                sc(6, "Materialized view ve partition kullanılabilir. 4 puan kırıldı: kolon bazlı sıkıştırma yoktur ve materialized view'lar elle yenilenir."),
                sc(5, "Taramalar bir reader'da çalışabilir; 2 milyon row'luk feature table'ı gece writer'a yazılır, ama bu checkout tepesinin dışındadır (Aurora sayfasının tek writer tablosu: 0). 5 puan kırıldı: reader'lar checkout ile aynı storage'ı okur ve üç yılı tarayan gece işi storage I/O'sunu checkout ile paylaşır; tarama süresinin kendisi R1 · DA'da sayıldı."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(6, "Aurora'nın SageMaker entegrasyonu SQL'den tahmin çağırır. 4 puan kırıldı: satış geçmişini Redshift'ten Aurora'ya getirmek, partition ve materialized view bakımı ekibin işidir."),
                sc(4, "Instance saat başına ödenir. 6 puan kırıldı: gece işini iki saatte bitirecek büyük bir instance 7/24 çalışır.")],
    },
    h2h={
        "ath": "S3 üzerinde sorgu motoru (Athena) ile kafa kafaya. İki servis de feature SQL'ini yazar (R1.1 eşit) ve ikisi de sonucu Parquet olarak bırakabilir. Athena'nın dürüst üstünlüğü veri S3'teyken görünür: SageMaker notebook'ları aynı dosyaları okur, aktarım yoktur ve sadece taranan veri ödenir. "
               "Bu kartta satış ve tıklamalar Redshift'tedir. Athena için önce düzenli bir S3 aktarımı gerekir (R4), dosyalar müşteriye göre bir arada durmaz (R1.2) ve tekrar eden aylık toplamlar için materialized view yoktur (R1.4). "
               "Redshift aynı işi verinin durduğu yerde, kolon bloklarından ve paralel bir CREATE TABLE AS ile yapar; sonucu UNLOAD ile S3'e bırakır. "
               "Kaynak veri S3'te olsaydı ve iş haftada bir çalışsaydı fark kabaca 3 puana inerdi. Hangi koşul değişseydi Athena seçilirdi: kaynak veri S3'te bir veri gölünde dursaydı, feature işi haftada bir çalışsaydı ve ekipte hiç warehouse olmasaydı; o zaman Redshift için yeni bir sistem kurmak R4'ü düşürürdü.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora SQL'i aynı biçimde yazar ve SageMaker'dan SQL içinde tahmin çağırabilir. Ama feature işi her gece üç yılı tarar: PostgreSQL row'ları tam okur (R1.2) ve gece taraması storage I/O'sunu checkout ile paylaşır (R2); 2 milyon row'luk sonucun writer'a yazılması ise checkout tepesinin dışında olduğu için tek writer tablosunda puan kırdırmaz. "
               "Büyük bir instance'ı iki saatlik bir gece işi için 7/24 ödemek de R5'te kaybettirir. Aurora'nın dürüst yeri burada skorların kendisidir: sabah CRM'in okuyacağı 2 milyon skor küçük bir table'dır ve Aurora'ya ya da DynamoDB'ye yazılabilir. "
               "Hangi koşul değişseydi Aurora seçilirdi: feature'lar son 90 günden hesaplansaydı, müşteri sayısı 50.000 olsaydı ve ayrı bir analiz servisi istenmeseydi.",
    },
    verdict="Karar: Redshift {rs}, Athena {ath}, Aurora {aur}. Kararı R1 verir: 140 feature müşteri başına window ve aggregate sorularıdır, üç yılı tarar ve sonuç toplu yazılır; bunların hepsi columnar ve MPP bir engine'in doğal işidir (Ö1, Ö4, Ö5, Ö7). "
            "Doğru mimari ikisi birliktedir: feature'lar Redshift'te hesaplanır, özel Python modelleri SageMaker AI'da eğitilir; basit modeller için Redshift ML aynı SageMaker'ı SQL'den çağırır. "
            "Redshift seçtiğimizde artımız: veri yerinden çıkmaz, gece işi tek bir SQL'dir, gündüz compute ödenmez. "
            "Eksimiz: model eğitimi ayrı bir serviste ve ayrı bir faturadadır; uygulama UNLOAD ile S3'e yazılan feature dosyalarının tarihini kontrol etmeli ve eski dosyayla eğitim yapmamalıdır. "
            "Bir koşul değişseydi: kaynak veri S3'te olsaydı, iş haftada bir çalışsaydı ve ekipte hiç warehouse olmasaydı Athena öne geçerdi; bu koşullardan yalnız biri farkı kapatmaz."))

# ------------------------------------------------------------------ 7. log analytics (OpenSearch wins on its engine)
REDSHIFT_W.append(wusecase("logs", 7, sim="w_logs",
    title="Log toplama ve arama: olay anında bir hata mesajını bulmak",
    key="Her log satırı bir JSON: time, service, level, request_id, message ve değişen alanlar. Son 30 gün sıcak, 13 ay arşiv.",
    story="Lale Market'in on Engine App'i ve load balancer'ı günde 600 GB log üretiyor: normalde saniyede 7.000 satır, bir olay anında beş katı. Üç kişilik SRE ekibinin üç sorusu var. "
          "Birincisi, olay anında son yedi günde bir hata mesajını ya da bir request id'yi saniyeler içinde bulmak: \"payment\" yakınında \"timeout\" geçen satırlar. İkincisi, servis başına dakikalık 5xx oranını gösteren canlı bir pano; en fazla bir dakika gecikmeyle. "
          "Üçüncüsü, ayda bir 13 aylık kapasite raporu. Log'ların alanları servisten servise değişiyor ve her sürümde yeni alan geliyor. Log'lar 30 gün sıcak tutulur, sonra 13 ay arşivde kalır; tek tek log satırları değerli değildir.",
    wnote="R1 toplam 44: işin merkezi metin içinde aramadır (EY 16); değişen JSON alanları (VM 8), 30 günlük ömür (YD 10) ve panonun toplamları (DA 10). "
          "R2 18 ve R4 18 ile ikinci: sürekli bir yazma akışı, olay anında beş kat; SRE ekibi hazır bir arama ve pano aracı istiyor.",
    rows=[
        row("EY", 16, "Olay anındaki ilk soru metin içinde bir aramadır.",
            "Son yedi günün log'larında bir kelimeyi, bir kelime yakınındaki başka bir kelimeyi ya da bir request id'yi saniyeler içinde bulmak; sonuçlar zamana göre sıralı.",
            "Arama dakikalar sürerse olay süresi uzar ve müşteri ödeme ekranında bekler."),
        row("VM", 8, "Her servisin log'u farklı alanlar taşır ve her sürümde yeni alan gelir.",
            "Yarı yapılandırılmış JSON satırları alan listesi önceden tanımlanmadan kabul edilmeli; yeni bir alan hemen sorgulanabilmeli.",
            "Her yeni alan için bir schema değişikliği gerekirse ekip o alanı olay anında sorgulayamaz."),
        row("YD", 10, "Sıcak log'lar 30 gün sonra gitmeli.",
            "30 günden eski log'lar sıcak katmandan kendiliğinden silinmeli ya da arşive geçmeli; silme bir iş yazmadan olmalı.",
            "Silme işi unutulursa disk dolar ve yeni log'lar yazılamaz."),
        row("DA", 10, "Canlı pano ve aylık rapor toplamlardır.",
            "Servis başına dakikalık 5xx oranı ve 13 aylık kapasite raporu: zaman pencereli toplamlar hızlı dönmeli.",
            "Pano yavaşsa olay geç fark edilir."),
        row("R2", 18, "Saniyede 7.000 satır, olay anında beş katı; pano en fazla bir dakika geride.",
            "Saniyede 7.000, olay anında 35.000 satır yazma; yeni satır bir dakika içinde aranabilir ve panoda görünür olmalı.",
            "Olay anında log'lar geride kalırsa ekip tam o anda kör kalır."),
        row("R3", 6, "Tek tek log satırları değerli değildir.",
            "Birkaç dakikalık log kaybı kabul edilir; bir AZ arızası 30 günlük sıcak log'u silmemeli.",
            "Bütün sıcak log'lar kaybolursa son bir ayın olayları incelenemez."),
        row("R4", 18, "Üç kişilik SRE ekibi hazır bir arama ve pano aracı istiyor.",
            "Log'ları toplayan bir boru hattı, bir arama ekranı ve panolar hazır gelmeli; ekip yeni bir sorgu dili öğrenmeye razı ama araç yazmaya değil.",
            "Arama ekranını ve panoları ekip kendisi yazarsa üç kişinin bir çeyreği gider."),
        row("R5", 14, "Günde 600 GB yazılır ve sürekli sorgulanır.",
            "Sürekli yazma ve dakikada bir pano yenilemesi; 30 günlük sıcak veri için storage ve compute öngörülebilir olmalı.",
            "Her pano yenilemesi ya da her arama veriyi baştan tarayıp ödenirse fatura olay sayısıyla büyür."),
    ],
    cands=["os", "rs", "ath"],
    scores={
        "os": [sc(10, "Inverted index her kelimenin hangi satırlarda geçtiğini tutar; kelime, yakınlık ve request id araması doğrudan bir index okumasıdır. Puan kırılmadı."),
               sc(9, "Dynamic mapping yeni JSON alanını yazma anında tanır ve index'ler. 1 puan kırıldı: alan sayısı sınırlanmazsa mapping büyür; index şablonu bir tasarım işidir."),
               sc(10, "Index State Management zamana göre index'leri 30 gün sonra siler ya da taşır. Puan kırılmadı."),
               sc(9, "Aggregation'lar kolon bazlı doc values üzerinde çalışır; dakikalık 5xx oranı hızlıdır. 1 puan kırıldı: 13 aylık rapor için eski index'ler sıcak katmanda değildir."),
               sc(8, "Shard'lar ve node'lar yazmayı paylaşır; yeni satır refresh ile yaklaşık bir saniyede aranır. 2 puan kırıldı: olay anında ağır aramalar yazmayla aynı node'larda yarışır ve sabit kapasite tepe anında yazmayı geciktirebilir (OpenSearch sayfasının log kartıyla aynı kırılım); günde 600 GB için node ve shard planı R4'te sayıldı."),
               sc(8, "Replica shard'lar ve snapshot'lar. 2 puan kırıldı: bir node kaybında replica'sı olmayan index'ler yeniden yüklenir."),
               sc(8, "OpenSearch Dashboards arama ekranını ve panoları hazır verir; OpenSearch Ingestion log'ları toplar. 2 puan kırıldı: index şablonları ve shard planı ekibin işidir."),
               sc(7, "Node saat başına ödenir; eski veri daha ucuz katmanlara taşınır. 3 puan kırıldı: domain 30 günlük sıcak veriye göre boyutlanır ve 7/24 çalışır.")],
        "ath": [sc(4, "LIKE ve regexp ile arama yapılır. 6 puan kırıldı: inverted index yoktur; her arama yedi günün message kolonunu baştan okur."),
                sc(7, "Schema okurken uygulanır: JSON SerDe (satırı kolonlara çeviren okuyucu) değişen alanları okur. 3 puan kırıldı: yeni alanlar table tanımına eklenmeden sorgulanamaz ve her yeni alan bir tanım güncellemesidir."),
                sc(8, "Tarihe göre partition'lar düşürülür; dosyaların silinmesi S3 lifecycle kuralıyla olur. 2 puan kırıldı: süre sonu engine'de değil S3'tedir ve table tanımı ayrıca güncellenir."),
                sc(7, "Parquet'e çevrilen log'lar kolon kolon okunur. 3 puan kırıldı: ham JSON satırlar row bazlı dosyalardır; Parquet'e çevirme ayrı bir iştir ve çevrilmeyen her sorgu bütün satırları okur."),
                sc(6, "Firehose dosyaları birkaç dakikada bir S3'e yazar. 4 puan kırıldı: yeni satır dosya yazılana kadar görünmez ve dakikada bir pano yenilemesi hesap başına eşzamanlı sorgu kotasına dayanır."),
                sc(10, "Log'lar S3'te birden fazla Availability Zone'da durur. Puan kırılmadı."),
                sc(6, "Firehose, Glue table'ları ve Athena hazır servislerdir. 4 puan kırıldı: arama ekranı ve canlı pano hazır gelmez; Parquet çevirme ve partition düzeni ekibin işidir."),
                sc(7, "Taranan TB başına ödenir; boş saatler sıfırdır. 3 puan kırıldı: birim sorgu başınadır ve bu iş yükü sürekli sorgudur: dakikalık pano günde 1.440 sorgu; fatura sorgu sayısıyla büyür ve bir tavanı yoktur. Aramanın her seferinde bütün veriyi okuması R1.1'de sayıldı.")],
        "rs": [sc(4, "LIKE ve SIMILAR TO ile metin araması yapılır (Ö5). 6 puan kırıldı: inverted index yoktur; her arama message kolonunun bütün bloklarını okur ve zone map metin içindeki bir kelimeyi atlatamaz."),
               sc(8, "SUPER tipi şemasız JSON'u bir kolonda tutar ve yeni bir alan schema değişikliği olmadan hemen sorgulanır (PartiQL, Ö5). 2 puan kırıldı: alanlar her sorguda yol ifadesiyle açılır; sık filtrelenen bir alanın blok atlaması için ayrı bir kolon ve ALTER TABLE gerekir."),
               sc(6, "Eski log'lar tarih aralığıyla silinir. 4 puan kırıldı: süre sonu yoktur; silme zamanlanmış bir DELETE işidir ve silinen row'lar arka plandaki VACUUM'a kadar yer tutar."),
               sc(10, "Kolon bazlı saklama, sort key ve MPP (Ö1, Ö3, Ö4) zaman pencereli toplamların kendisidir: dakikalık 5xx ve 13 aylık rapor hızlı döner. Puan kırılmadı."),
               sc(8, "Streaming ingestion log'ları Kinesis'ten bir materialized view'a mikro-batch'lerle alır (Ö7) ve olay anındaki 35.000 satır/sn tepeyi akış katmanı karşılar. 2 puan kırıldı: yeni satır aramada ve panoda ancak materialized view yenilendiğinde görünür; otomatik yenileme ile bu genellikle saniyelerdir ama bir dakikalık sınır tepe anında yenileme sıklığına bağlıdır. Akış katmanının işletilmesi R4'te, ödenmesi R5'te sayıldı."),
               sc(9, "Recovery point'ler ve akış katmanındaki saklama. 1 puan kırıldı: akış katmanındaki son saniyeler bir arızada yeniden oynatılır."),
               sc(6, "SQL panoları (örneğin QuickSight) çalışır (Ö5). 4 puan kırıldı: log arama ekranı yoktur ve bir akış katmanı işletilir."),
               sc(6, "RPU-saat ve akış katmanı ödenir. 4 puan kırıldı: dakikada bir yenilenen pano ve sürekli yazma yüzünden Serverless kapasite gün boyu açık kalır.")],
    },
    h2h={
        "ath": "S3 üzerinde sorgu motoru (Athena) ile kafa kafaya. Athena log'ların arşivi için iyi bir yerdir: 13 aylık log S3'te durur, schema okurken uygulanır ve aylık rapor sadece taradığı kadar ödenir. "
               "Ama bu kartın ilk sorusu olay anında metin içinde aramadır ve Athena'da inverted index yoktur: her arama yedi günün message kolonunu baştan okur ve her seferinde ödenir (R1.1, R5). Yeni satırlar da dosya yazılana kadar görünmez (R2). "
               "OpenSearch kelimeyi index'ten bulur ve yeni satırı yaklaşık bir saniyede aranabilir yapar. "
               "Doğru mimari ikisi birliktedir: 30 günlük sıcak log OpenSearch'te, 13 aylık arşiv S3'te ve aylık rapor Athena ile. Hangi koşul değişseydi Athena seçilirdi: canlı arama ve pano istenmeseydi ve iş yalnız aylık rapor olsaydı.",
        "rs": "Data warehouse (Redshift) ile kafa kafaya. Redshift bu kartın toplam sorularında güçlüdür: dakikalık 5xx oranı ve 13 aylık kapasite raporu kolon bloklarından saniyeler içinde döner (R1.4). "
              "Ama işin merkezi metin aramasıdır ve columnar bir engine'de inverted index yoktur: \"timeout\" kelimesini bulmak message kolonunun bütün bloklarını okumaktır; zone map metin içindeki bir kelimeyi atlatamaz (R1.1). Değişen JSON alanları SUPER tipinde kalır (R1.2), 30 günlük silme bir DELETE işidir (R1.3) ve log'lar bir akış katmanından mikro-batch'lerle gelir; yeni satır panoda materialized view yenilendiğinde görünür (R2). "
              "Hangi koşul değişseydi Redshift seçilirdi: log'lar metin araması için değil sadece toplamlar ve raporlar için toplansaydı (örneğin istek sayıları ve süreleri) ve analistler bunları satış verisiyle SQL'de birleştirmek isteseydi.",
    },
    verdict="Karar: OpenSearch {os}, Redshift {rs}, Athena {ath}. Bu iş yüküne en uygun servis OpenSearch'tür ve kararı R1'in erişim yolu verir: olay anındaki soru metin içinde aramadır ve bunu inverted index yapar. Redshift açık farkla ikincidir; toplam sorularında güçlüdür ama metin aramasında her bloğu okur. "
            "Yine de Redshift seçersek artımız: 13 aylık kapasite raporu ve dakikalık 5xx oranı tek bir SQL'dir ve log'lar satış verisiyle aynı yerde birleşir (Ö1, Ö5). "
            "Eksimiz: arama ekranı yoktur ve her arama bütün message bloklarını okur; uygulama aramayı request id ve zaman aralığıyla daraltmalı, 30 günlük silmeyi zamanlanmış bir DELETE ile yapmalı ve bir akış katmanı işletmelidir. "
            "Doğru mimari ikisi birliktedir: sıcak log OpenSearch'te, arşiv S3'te; aylık rapor Athena ile ya da Redshift Spectrum ile. Bir koşul değişseydi: metin araması istenmeseydi ve iş yalnız toplamlar olsaydı Redshift öne geçerdi."))

# ------------------------------------------------------------------ 8. inventory forecasting inputs, flat 24/7 (the provisioned twin wins)
REDSHIFT_W.append(wusecase("forecast", 8, sim="w_forecast",
    title="Stok tahmini girdileri: 7/24 düz bir yük",
    key="Fact table'lar: daily_sales (product_id, warehouse_id, day) ve stock (zero-ETL ile Aurora'dan). Materialized view: ürün ve depo başına 90 günlük hareketli ortalama.",
    story="Lale Market'in otomatik stok yenileme servisi 6 depo ve 4.000 ürün için her beş dakikada bir aynı soruları soruyor: son 90 günün günlük satışları, hareketli ortalama, Aurora'daki anlık stok ve tedarikçi teslim süresi. "
          "Servis gece gündüz çalışıyor; depo planlamacıları da gün boyunca aynı ekranlara bakıyor. Yük yıllardır düz: haftada 7 gün, günde 24 saat, kabaca aynı sorgu sayısı. "
          "Veri 1,5 TB. Ekipte daha önce Redshift cluster'ı işletmiş iki DBA var. Finans müdürü üç yıllık bir bütçe planı yaptı ve öngörülebilir, en düşük aylık faturayı istiyor.",
    wnote="R1 toplam 46: 90 günlük pencerelerin taranması (DA 14) ve sorguların kendisi (EY 14), her beş dakikada yenilenen ara sonuçlar (AO 10) ve Aurora'dan gelen sürekli değişiklikler (OY 8). "
          "R5 22 ile hemen arkasında: yük düz ve bütçe üç yıllık; bu kartı fiyat modeli ayırır.",
    rows=[
        row("EY", 14, "Her beş dakikada aynı pencere ve join soruları sorulur.",
            "Ürün ve depo başına 90 günlük hareketli ortalama (AVG() OVER), anlık stok ile JOIN ve teslim süresine göre filtre SQL ile yazılmalı.",
            "Sorgu yazılamazsa yenileme servisi veriyi kendi belleğine çeker ve her beş dakikada baştan hesaplar."),
        row("DA", 14, "Her sorgu 90 günlük bir pencereyi tarar.",
            "90 günlük satışların birkaç kolonu okunmalı; sorgu beş dakikalık döngünün küçük bir kısmını almalı.",
            "Sorgu döngüden uzun sürerse siparişler eski tahminle verilir."),
        row("AO", 10, "Aynı ara sonuç her beş dakikada lazım.",
            "Hareketli ortalama gibi ara sonuçlar saklanmalı ve yeni satışlarla artımlı yenilenmeli.",
            "Her döngüde 90 gün baştan hesaplanırsa kapasite boşa harcanır."),
        row("OY", 8, "Stok Aurora'da sürekli değişir ve kopyaya akar.",
            "Aurora'daki stok değişiklikleri kopyaya sürekli eklenmeli ve güncellenmeli; güncellemeler taramayı bozmamalı.",
            "Stok kopyası geride kalırsa servis olmayan stoğa göre sipariş verir."),
        row("R2", 14, "Yük yıllardır düz; tepe yok.",
            "Gece gündüz aynı yük; her beş dakikalık döngü aynı kapasiteyle zamanında bitmeli.",
            "Bir döngü gecikirse o döngünün siparişleri bir sonrakine kayar."),
        row("R3", 6, "Satışlar ve stok kaynaktan yeniden yüklenebilir.",
            "Kopya kaybolursa kaynaktan yeniden yüklenir; günlük yedek yeterlidir.",
            "Kayıp birkaç saatlik bir tahmin kesintisidir; siparişler elle verilir."),
        row("R4", 12, "Ekipte cluster işletmiş iki DBA var.",
            "Kapasite bir kez seçilebilir; bakım penceresi ve resize planlanabilir. Ekip bunu biliyor.",
            "Ekip bilmediği bir aracı işletirse ilk arıza uzun sürer."),
        row("R5", 22, "Yük düz ve bütçe üç yıllık: en düşük öngörülebilir fatura bu kartın kararıdır.",
            "Üç yıl boyunca 7/24 düz yük için en düşük ve öngörülebilir aylık fatura; uzun dönemli taahhüt kabul edilir.",
            "Düz bir yükte saniye başına ödeme bir avantaj getirmez; taahhütsüz fiyat üç yılda belirgin bir fark yapar."),
    ],
    cands=["rsp", "rs", "aur"],
    scores={
        "rsp": [sc(10, "Aynı engine: analitik SQL (Ö5) ile AVG() OVER ve JOIN tek cümlededir. Puan kırılmadı."),
                sc(10, "Kolon bazlı saklama ve day sort key'i (Ö1, Ö3) sorguyu 90 günün bloklarıyla sınırlar. Puan kırılmadı."),
                sc(9, "Materialized view artımlı yenilenir (Ö6). 1 puan kırıldı: sort key ve distribution seçimi bir tasarım işidir."),
                sc(9, "Zero-ETL stok değişikliklerini sürekli getirir (Ö7). 1 puan kırıldı: güncellenen row eskisini silinmiş işaretler ve arka plandaki VACUUM işi artar."),
                sc(10, "Düz yük sabit düğümlere tam oturur; kapasite her an hazırdır. Puan kırılmadı."),
                sc(9, "Otomatik ve elle snapshot'lar. 1 puan kırıldı: veri bir kopyadır; kaybolursa yeniden yükleme sürer."),
                sc(8, "Düğüm tipi ve sayısı bir kez seçilir; iki DBA bunu biliyor. 2 puan kırıldı: resize ve bakım penceresi ekibin işidir."),
                sc(9, "Aynı bellek (384 GB) varsayımıyla kaba bir karşılaştırma: dört ra3.4xlarge düğümü (her biri 96 GiB) üç yıllık peşinatsız rezervasyonla düğüm başına 1,6939 USD/saat, ayda yaklaşık 4.946 USD (eu-central-1, Price List API, 2026-10-31). Price List API'da Serverless rezervasyonu yalnız bir yıllıktır; bir yıllık vadede düğümler (peşinatsız 2,7258 USD/saat, ayda yaklaşık 7.959 USD) Serverless'tan pahalıdır. 1 puan kırıldı: fiyat avantajı üç yıllık taahhüde bağlıdır.")],
        "rs": [sc(10, "Analitik SQL (Ö5): AVG() OVER ve JOIN tek cümlededir. Puan kırılmadı."),
               sc(10, "Kolon bazlı saklama ve day sort key'i (Ö1, Ö3). Puan kırılmadı."),
               sc(9, "Materialized view artımlı yenilenir (Ö6). 1 puan kırıldı: sort key ve distribution seçimi bir tasarım işidir."),
               sc(9, "Zero-ETL stok değişikliklerini sürekli getirir (Ö7). 1 puan kırıldı: güncellenen row eskisini silinmiş işaretler ve arka plandaki VACUUM işi artar."),
               sc(10, "Serverless düz yükte aynı kapasiteyi tutar (Ö8). Puan kırılmadı."),
               sc(9, "Recovery point'ler 30 dakikada bir. 1 puan kırıldı: veri bir kopyadır."),
               sc(9, "Düğüm planı yoktur (Ö8). 1 puan kırıldı: base RPU ve en fazla RPU sınırı ekibin işidir; tablo tasarımı R1'de sayıldı."),
               sc(7, "Aynı bellek için 24 RPU (24 × 16 GB) 7/24: on demand ayda yaklaşık 7.902 USD (0,451 USD/RPU-saat), bir yıllık rezervasyonla yaklaşık 6.167 USD (0,352 USD/RPU-saat). 3 puan kırıldı: düz yükte saniye başına ödeme bir avantaj getirmez; Serverless'ın en uzun rezervasyonu bir yıldır ve bu fiyat, provisioned düğümlerin üç yıllık rezervasyonundan yaklaşık yüzde 25 pahalıdır (6.167'ye karşı 4.946 USD).")],
        "aur": [sc(10, "PostgreSQL SQL'i window function'ları ve JOIN'i tam olarak destekler. Puan kırılmadı."),
                sc(3, "Index dar aralıkları hızlandırır. 7 puan kırıldı: PostgreSQL row'ları tam saklar; 90 günlük pencereyi tarayan her sorgu her row'un tamamını okur."),
                sc(6, "Materialized view ve partition kullanılabilir. 4 puan kırıldı: kolon bazlı sıkıştırma yoktur ve materialized view'lar elle yenilenir."),
                sc(10, "Stok zaten Aurora'dadır; row store tek row'luk güncellemeyi doğrudan yapar. Puan kırılmadı."),
                sc(5, "Sorgular reader'larda çalışır. 5 puan kırıldı: reader'lar checkout ile aynı storage'ı okur ve her beş dakikadaki tarama storage I/O'sunu checkout ile paylaşır; tarama süresinin kendisi R1 · DA'da sayıldı."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(8, "Boru hattı yoktur, stok zaten oradadır. 2 puan kırıldı: partition ve materialized view bakımı ekibin işidir."),
                sc(6, "Reader instance'lar rezervasyonla ucuzlar. 4 puan kırıldı: 1,5 TB'ı her beş dakikada tarayacak büyük reader'lar gerekir ve Standard yapılandırmada her taramanın I/O'su ayrıca ödenir.")],
    },
    h2h={
        "rs": "Data warehouse (Redshift Serverless) ile kafa kafaya. Bu kart bu sayfanın servisinin ikizine kaybettiği karttır: iki servis aynı engine'i çalıştırır ve R1 puanları birebir aynıdır (44,2). Kararı R5 verir. "
              "Serverless'ın gücü boş saatlerde compute ödememesidir; bu kartta boş saat yoktur. Yük 7/24 düzdür, bu yüzden saniye başına ödeme bir avantaj getirmez. Aynı bellek varsayımıyla provisioned cluster üç yıllık rezervasyonla ayda yaklaşık 4.946 USD, Serverless kendi en uzun vadesi olan bir yıllık rezervasyonla yaklaşık 6.167 USD'dir; bir yıllık vadeyle düğümler 7.959 USD tutar, yani avantaj sadece üç yıllık taahhütten gelir. "
              "Serverless'ın dürüst üstünlükleri yine de vardır: düğüm planı ve resize yoktur (R4) ve yük bir gün değişirse kapasite kendisi gelir. Fark 3,2 puandır, yani yakın bir yarış. "
              "Hangi koşul değişseydi Redshift Serverless seçilirdi: yük gece düşseydi ya da hafta sonları dursaydı, ekipte cluster işletecek kimse olmasaydı ya da taahhüt bir yılla sınırlı olsaydı.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora'nın gücü stoğun kendisidir: anlık stok zaten oradadır, kopyalanmaz ve bir güncelleme hemen görünür (R1.4). "
               "Ama her beş dakikalık döngü 90 günlük satışları tarar ve PostgreSQL row'ları tam olarak okur (R1.2); bu tarama checkout ile aynı storage'ı paylaşan reader'larda çalışır (R2). Hareketli ortalamayı tutan materialized view'lar da elle yenilenir (R1.3). "
               "Hangi koşul değişseydi Aurora seçilirdi: ürün sayısı 400, pencere 14 gün olsaydı; o zaman tarama küçük kalır ve stoğun yanında çalışmak en sade tasarım olurdu. Bu kartta da doğru mimari ikisi birliktedir: stok Aurora'da kalır, zero-ETL onu warehouse'a taşır.",
    },
    verdict="Karar: Redshift provisioned {rsp}, Redshift {rs}, Aurora {aur}. Yakın bir yarış ve R1'de tam eşitlik: iki servis aynı engine'i çalıştırır. Kararı R5 verir: 7/24 düz bir yükte üç yıllık rezervasyonlu düğümler, bir yıllık rezervasyonlu Serverless'tan yaklaşık yüzde 20 ucuzdur; Serverless'ın üç yıllık rezervasyonu yoktur, bir yıllık vadelerde ise Serverless daha ucuzdur. "
            "Yine de Redshift Serverless seçersek artımız: düğüm planı, resize ve bakım penceresi yoktur; yük değişirse kapasite kendisi gelir. "
            "Eksimiz: ayda yaklaşık 1.200 USD daha yüksek bir fatura; base RPU'yu düz yüke göre ayarlamak ve bir yıllık rezervasyonu satın almak ekibin işidir. "
            "Bir koşul değişseydi: yük gece ya da hafta sonu düşseydi ya da finans üç yıl yerine bir yıllık taahhüt isteseydi Serverless öne geçerdi. Bu kart \"aynı engine, farklı servis\" kararının bir örneğidir: provisioned cluster'dan Serverless'a ya da tersine geçiş bir snapshot geri yüklemesidir."))

# ------------------------------------------------------------------ 9. executive dashboards (materialized views and result cache)
REDSHIFT_W.append(wusecase("dashboards", 9,
    title="Yönetim panosu: 12 KPI kutusu, dakikada bir yenileme",
    key="Materialized view'lar: bugünün geliri ve dönüşümü (zero-ETL kopyası üzerinde), geçen yılın aynı günü ve 13 aylık eğilim (satış geçmişi üzerinde).",
    story="Lale Market'in 25 yöneticisi telefonlarında bir pano açıyor: 12 KPI kutusu. Bugünün geliri ve geçen yılın aynı günü, saatlik dönüşüm oranı, en çok satan 10 kategori, 13 aylık gelir eğilimi. "
          "Pano mesai saatinde dakikada bir yenileniyor ve her kutu iki saniyenin altında açılmalı. Pazartesi 09:00'da herkes aynı anda açıyor: bir dakikada yaklaşık 300 kutu sorgusu. "
          "Bugünün verisi Aurora'dan zero-ETL ile gelir, geçmiş Redshift'teki satış table'ındadır. Ekipte bir BI geliştiricisi var; pano için ayrı bir sistem işletmek istemiyor. Pano verisi bir kopyadır.",
    wnote="R1 toplam 44: kutuların hızı en çok ön hesaplamaya bağlıdır (AO 14); sorguların kendisi (EY 12) ve 13 aylık tarama (DA 12), sürekli gelen değişiklikler (OY 6). "
          "R2 18 ve R5 18 ile ikinci: pazartesi 09:00 dalgası ve mesai boyunca dakikalık yenileme.",
    rows=[
        row("EY", 12, "Her kutu bugünü geçmişle karşılaştıran bir SQL'dir.",
            "Bugünün geliri ile geçen yılın aynı günü, kategoriye göre ilk 10 ve 13 aylık eğilim SQL ile yazılmalı: JOIN, GROUP BY, window function.",
            "Bir kutu SQL ile yazılamazsa BI geliştiricisi onu uygulamada hesaplar ve panonun rakamları raporlarla tutmaz."),
        row("DA", 12, "Eğilim kutusu 13 ayı tarar.",
            "13 aylık eğilim ve geçen yılın aynı günü birkaç kolonu okuyan taramalarla saniyeler içinde hesaplanmalı.",
            "Eğilim kutusu yavaşsa pano iki saniye sınırını aşar."),
        row("AO", 14, "Aynı 12 sorgu dakikada bir tekrar eder; ön hesaplama hızı belirler.",
            "Kutuların ara sonuçları saklanmalı ve yeni veriyle artımlı yenilenmeli; aynı sorgu tekrar gelince sonuç yeniden hesaplanmadan dönmeli.",
            "Her yenileme 13 ayı baştan tararsa 25 yöneticinin panosu kapasitenin çoğunu alır."),
        row("OY", 6, "Bugünün siparişleri sürekli gelir.",
            "Aurora'daki yeni siparişler ve iadeler kopyaya sürekli eklenmeli; güncellemeler kutuları bozmamalı.",
            "Bugünün kutusu geride kalırsa yönetim yanlış rakamla karar verir."),
        row("R2", 18, "Pazartesi 09:00'da bir dakikada 300 kutu sorgusu.",
            "Pazartesi 09:00 dalgasında da her kutu iki saniyenin altında açılmalı.",
            "Dalga anında kutular yavaşlarsa yöneticiler panoyu bırakır ve analiste telefon eder."),
        row("R3", 5, "Pano verisi bir kopyadır.",
            "Kopya kaybolursa kaynaktan yeniden yüklenir; pano birkaç saat kapanabilir.",
            "Kayıp bir pano kesintisidir; para kaybı değildir."),
        row("R4", 15, "Tek bir BI geliştiricisi var; pano için ayrı bir sistem istemiyor.",
            "Pano var olan warehouse'ta çalışmalı; ayrı bir cache ya da yeni bir veri boru hattı istenmiyor.",
            "Ayrı bir sistem tek geliştiricinin işletme yükünü ikiye katlar."),
        row("R5", 18, "Mesai boyunca dakikada bir yenileme: ödeme modeli belirgin bir kalemdir.",
            "Mesai saatinde dakikada bir yenileme; gece ve hafta sonu neredeyse sıfır. Fatura kullanımla orantılı olmalı.",
            "Panoya göre boyutlanan kapasite gece ve hafta sonu boş durur ve ödenir."),
    ],
    cands=["rs", "os", "aur"],
    scores={
        "rs": [sc(10, "Analitik SQL (Ö5): bugün ile geçen yıl tek bir JOIN, ilk 10 bir window function. Puan kırılmadı."),
               sc(10, "Kolon bazlı saklama ve order_date sort key'i (Ö1, Ö3): eğilim kutusu sadece gereken kolonları okur. Puan kırılmadı."),
               sc(9, "Materialized view'lar artımlı yenilenir ve aynı sorgu tekrar gelince result cache sonucu planlamadan döndürür (Ö6). 1 puan kırıldı: sort key ve materialized view tasarımı bir tasarım işidir."),
               sc(9, "Zero-ETL bugünün siparişlerini sürekli getirir (Ö7). 1 puan kırıldı: güncellenen row eskisini silinmiş işaretler ve arka plandaki VACUUM işi artar."),
               sc(8, "Serverless dalgada kapasiteyi artırır (Ö8); geçmiş kutuları result cache'ten milisaniyede döner. 2 puan kırıldı: zero-ETL'in her değişikliği bugünün table'larının cache girişlerini geçersiz kılar; bugünün kutuları her dalgada yeniden hesaplanır. Hafta sonu boş duran workgroup'un pazartesi ilk sorgusu compute'un başlamasını da bekler (AWS başlama süresini ücretlendirmez)."),
               sc(9, "Recovery point'ler 30 dakikada bir. 1 puan kırıldı: kopya kaybolursa zero-ETL yeniden kurulur."),
               sc(9, "Pano var olan workgroup'ta çalışır; yeni sistem yoktur. 1 puan kırıldı: base RPU ve en fazla RPU sınırı ekibin işidir; materialized view tasarımı R1.3'te sayıldı."),
               sc(8, "RPU-saat; gece ve hafta sonu compute ödenmez (Ö8). 2 puan kırıldı: dakikalık yenileme yüzünden mesai boyunca kapasite çalışır.")],
        "os": [sc(6, "Aggregation'lar ve tarih histogramı kutuların çoğunu hesaplar. 4 puan kırıldı: bugün ile geçmişin JOIN'i ve serbest SQL sınırlıdır; karşılaştırma iki ayrı sorgu ve uygulamada birleştirmedir."),
               sc(8, "Aggregation'lar kolon bazlı doc values üzerinde çalışır. 2 puan kırıldı: 13 aylık sipariş satırları düzleştirilmiş document'lar olarak büyür."),
               sc(7, "Rollup ve transform job'ları özet index'ler üretir. 3 puan kırıldı: özetlerin yenilenmesi zamanlanmış job'lardır, artımlı bir view değildir."),
               sc(7, "Document ekleme hızlıdır. 3 puan kırıldı: bir güncelleme document'ın yeni bir sürümünü yazar ve sipariş satırları düzleştirildiği için bir iade birçok document'ı değiştirir."),
               sc(9, "Shard'lar ve node'lar okumayı paylaşır. 1 puan kırıldı: kapasite sabittir; pazartesi dalgası için node'lar önceden eklenir (node ve shard planı R4'te sayıldı)."),
               sc(8, "Replica shard'lar ve snapshot'lar. 2 puan kırıldı: kopya kaybolursa pipeline baştan yükler."),
               sc(4, "OpenSearch Ingestion Aurora'nın değişikliklerini akıtabilir ve Dashboards hazırdır. 6 puan kırıldı: dört table'ı document'lara düzleştiren pipeline, mapping ve shard planı tek geliştirici için ayrı bir sistemdir."),
               sc(6, "Node saat başına ödenir. 4 puan kırıldı: domain gece ve hafta sonu da çalışır.")],
        "aur": [sc(10, "PostgreSQL SQL'i JOIN, GROUP BY ve window function'ları tam olarak destekler. Puan kırılmadı."),
                sc(4, "Bugünün kutuları index ile birkaç bin row okur. 6 puan kırıldı: 13 aylık eğilim her row'un tamamını okur; diğer kartlardaki üç yıllık taramadan küçüktür, bu yüzden 7 değil 6 puan."),
                sc(6, "Materialized view ve partition kullanılabilir. 4 puan kırıldı: kolon bazlı sıkıştırma yoktur ve materialized view'lar elle yenilenir."),
                sc(10, "Siparişler zaten oradadır; row store ekleme ve güncellemeyi doğrudan yapar. Puan kırılmadı."),
                sc(5, "Kutular reader'larda çalışır. 5 puan kırıldı: reader'lar checkout ile aynı storage'ı okur ve dalga anındaki taramalar storage I/O'sunu checkout ile paylaşır; tarama süresinin kendisi R1 · DA'da sayıldı."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(8, "Boru hattı yoktur. 2 puan kırıldı: partition ve materialized view bakımı tek geliştiricinin işidir."),
                sc(4, "Reader instance saat başına ödenir. 6 puan kırıldı: dalgaya göre seçilen reader 7/24 çalışır ve Standard yapılandırmada her taramanın I/O'su ayrıca ödenir.")],
    },
    h2h={
        "os": "Search engine (OpenSearch) ile kafa kafaya. OpenSearch'ün gücü hazır panolar ve hızlı aggregation'lardır; log ve olay verisi üzerinde canlı bir pano için çok iyi bir araçtır. "
              "Bu panonun kutuları ise ilişkiseldir: bugünün geliri geçen yılın aynı günüyle karşılaştırılır, kategoriler ürün table'ından gelir. OpenSearch'te bu veri önce document'lara düzleştirilir (R4) ve karşılaştırma iki sorgu ile uygulamada birleştirmedir (R1.1). "
              "Redshift aynı veriyi zero-ETL ile table'ları değiştirmeden alır, ara sonuçları materialized view'larda tutar ve tekrar eden sorguyu result cache'ten döndürür. "
              "Hangi koşul değişseydi OpenSearch seçilirdi: pano satış değil uygulama olayları (tıklama, hata, gecikme) üzerinde olsaydı ve kutuların yanında metin araması da istenseydi.",
        "aur": "İlişkisel (Aurora PostgreSQL) ile kafa kafaya. Aurora'nın gücü tazeliktir: bugünün siparişleri kopyasız ve gecikmesiz oradadır, bugünün kutuları index ile birkaç bin row okur. "
               "Ama 13 aylık eğilim ve geçen yılın günleri row store'da her row'un tamamını okur (R1.2), materialized view'lar elle yenilenir (R1.3) ve pazartesi dalgası checkout ile aynı storage'ı paylaşan reader'larda çalışır (R2). Dalgaya göre seçilen reader 7/24 ödenir (R5). "
               "Aurora'nın dürüst yeri bu panonun canlı yarısıdır: bir kutu saniyesinde doğru olmak zorundaysa, örneğin ödeme hatalarının sayısı, onu Aurora'nın reader'ından okumak zero-ETL'in yaklaşık 30 saniyelik gecikmesini ortadan kaldırır. "
               "Hangi koşul değişseydi Aurora seçilirdi: pano sadece bugünün ve son yedi günün kutularından oluşsaydı ve 30 saniyelik zero-ETL gecikmesi kabul edilmeseydi.",
    },
    verdict="Karar: Redshift {rs}, OpenSearch {os}, Aurora {aur}. Kararı R1'in ön hesaplama satırı ve R5 verir: aynı 12 sorgu dakikada bir tekrar eder; materialized view'lar ve result cache (Ö6) bunu ucuz yapar ve gece compute ödenmez. "
            "Redshift seçtiğimizde artımız: pano var olan warehouse'ta çalışır, geçmiş kutuları cache'ten milisaniyede döner, rakamlar raporlarla aynı SQL'den gelir. "
            "Eksimiz: bugünün kutuları zero-ETL'in yaklaşık 30 saniyelik gecikmesiyle gelir ve her değişiklik cache'i geçersiz kılar; uygulama kutunun altında \"veri şu saate kadar\" bilgisini göstermeli ve yenilemeyi dakikada birden sık yapmamalıdır. "
            "Bir koşul değişseydi: pano uygulama olayları üzerinde olsaydı OpenSearch, sadece bugünün kutuları olsaydı Aurora öne geçerdi."))

# ------------------------------------------------------------------ 10. ad-hoc analyst queries on S3 data (Athena wins, R1 equal)
REDSHIFT_W.append(wusecase("adhoc", 10,
    title="S3'teki veri gölünde ara sıra sorulan analist soruları",
    key="Veri gölü: 40 TB Parquet, dt=YYYY-MM-DD partition'ları, table tanımları Glue Data Catalog'da. Kopya yok; sorgu dosyaların durduğu yerde.",
    story="Lale Market'in veri gölünde 40 TB ham veri var: partner dosyaları, web olayları ve dışa aktarılmış sistem table'ları; hepsi S3'te Parquet ve tarihe göre partition'lı. "
          "Altı analist haftada yaklaşık 30 farklı soru soruyor ve her soru farklı: \"geçen salı Hamburg'daki partner iadeleri\", \"kampanya haftasında mobil oturum süresi\". Soruların çoğu bir ile üç günlük veriye bakıyor; ayda bir de bir çeyreği tarayan ağır bir soru var. "
          "Pano yok, cevabın bir dakikada gelmesi yeterli. Partnerler dosyalarına ara sıra yeni alan ekliyor. Veri ekibi 40 TB'ın ikinci bir kopyasını istemiyor ve bütçe küçük.",
    wnote="R1 toplam 42: serbest SQL (EY 14), dosyaların kolon kolon ve sadece gereken partition'larının okunması (DA 12), okurken uygulanan şema (ŞE 8) ve partition budama (AO 8). "
          "R5 22 ve R4 20 ile hemen arkasında: haftada 30 sorgu için kapasite tutulmamalı ve veri yerinden çıkmamalı.",
    rows=[
        row("EY", 14, "Her soru farklıdır ve önceden bilinmez.",
            "Her soru bir mühendis beklemeden SQL ile yazılabilmeli: JOIN, GROUP BY, window function, tarih aralığı.",
            "Soru yazılamazsa analist dosyaları indirir ve kendi makinesinde işler."),
        row("DA", 12, "Soruların çoğu birkaç günün birkaç kolonunu okur.",
            "Sorgu sadece ilgili tarih partition'larını ve sadece gereken kolonları okumalı; 40 TB'ın tamamına dokunmamalı.",
            "Her soru bütün dosyaları okursa bir sorgu saatler sürer ve TB'larca veri taranır."),
        row("ŞE", 8, "Partnerler dosyalarına ara sıra yeni alan ekliyor.",
            "Schema okurken uygulanmalı; yeni bir alan eski dosyaları bozmadan table tanımına eklenebilmeli.",
            "Her yeni alan bir yükleme işinin değişmesi demekse partner verisi haftalarca eksik kalır."),
        row("AO", 8, "Hız en çok partition budamasına bağlıdır.",
            "Partition'lar ve dosya istatistikleri ile taranacak dosyalar sorgudan önce elenmeli.",
            "Budama yoksa en küçük soru bile bütün veri gölünü tarar."),
        row("R2", 10, "Haftada 30 soru, ayda bir ağır soru.",
            "Ara sıra gelen sorular ve ayda bir çeyreği tarayan sorgu bir dakika içinde dönmeli; eşzamanlı yük çok küçüktür.",
            "Ağır soru saatler sürerse çeyrek raporu gecikir."),
        row("R3", 6, "Veri S3'te kalır; sonuçlar yeniden hesaplanır.",
            "Kaynak S3'tedir ve sorgu sonucu yeniden üretilebilir.",
            "Kayıp bir sorgu sonucudur; yeniden çalıştırılır."),
        row("R4", 20, "Veri yerinden çıkmamalı; ekip ikinci bir sistem işletmek istemiyor.",
            "40 TB S3'te kalmalı; yükleme işi, kopya ve ayrı bir sistem olmadan sorgulanmalı; table tanımları ortak bir katalogda durmalı.",
            "Kopya ve yükleme işi küçük ekibin bütün zamanını alır ve iki versiyon doğar."),
        row("R5", 22, "Haftada 30 sorgu: boş zaman neredeyse bütün haftadır.",
            "Sadece çalışan sorgular ödenmeli; boş saatler sıfır olmalı; sorgu başına minimum ücret küçük kalmalı.",
            "Kapasite için ödenen her saat neredeyse hiç kullanılmaz."),
    ],
    cands=["ath", "rs", "rsp"],
    scores={
        "ath": [sc(10, "Athena'nın SQL engine'i (Trino) JOIN, GROUP BY ve window function'ları tam olarak destekler. Puan kırılmadı."),
                sc(9, "Parquet kolon bazlıdır; sorgu sadece gereken kolonları ve tarih partition'larını okur. 1 puan kırıldı: dosyaların içi sıralı değilse row group istatistikleri az şey atlatır."),
                sc(9, "Schema okurken uygulanır: table tanımı Glue Data Catalog'dadır ve yeni alan tanıma eklenir. 1 puan kırıldı: yeni alan table tanımına eklenmeden sorgulanamaz."),
                sc(8, "Partition budama ve partition projection. 2 puan kırıldı: index ve materialized view yoktur."),
                sc(9, "Serverless; ara sıra gelen sorgu için kapasite servisindir. 1 puan kırıldı: ayda bir ağır sorgu hesap başına kaynak sınırlarına takılabilir."),
                sc(10, "Veri S3'te birden fazla Availability Zone'da durur. Puan kırılmadı."),
                sc(10, "Veri yerinde sorgulanır; partition düzeni ve Glue table'ları veri gölünde zaten vardır; kurulacak bir sistem yoktur, sadece bir Athena workgroup'u. Puan kırılmadı."),
                sc(10, "Taranan TB başına ödenir (yaklaşık 5 USD/TB), sorgu başına en az 10 MB; boş saatler sıfırdır. Puan kırılmadı.")],
        "rs": [sc(10, "Analitik SQL (Ö5) external table'lar üzerinde de aynıdır. Puan kırılmadı."),
               sc(9, "Spectrum (Ö8) Parquet'in kolonlarını ve tarih partition'larını okur. 1 puan kırıldı: dosyalar S3'tedir; yerel table'ların zone map'leri (Ö3) burada yoktur ve row group istatistikleri az şey atlatır."),
               sc(9, "External table'ların tanımı aynı Glue Data Catalog'dan gelir. 1 puan kırıldı: yeni alan table tanımına eklenmeden sorgulanamaz."),
               sc(8, "Partition budama. 2 puan kırıldı: external table'larda index yoktur ve materialized view S3 verisini yerel bir kopyaya çevirir."),
               sc(10, "Serverless kapasiteyi ağır sorguya göre artırır ve Spectrum katmanı taramayı paylaşır (Ö8). Puan kırılmadı."),
               sc(10, "Veri S3'te kalır. Puan kırılmadı."),
               sc(8, "Veri yerinde kalır; Glue kataloğundan bir external schema yeter (Ö8). 2 puan kırıldı: bu ekip için yeni bir Redshift workgroup'u, ağı ve IAM role'ü kurulur ve işletilir."),
               sc(9, "Sorgu yokken compute ödenmez; Spectrum Serverless'a dahildir (Ö8). 1 puan kırıldı: her sorgu base RPU ile en az 60 saniye ödenir.")],
        "rsp": [sc(10, "Aynı engine: analitik SQL (Ö5). Puan kırılmadı."),
                sc(9, "Aynı Spectrum katmanı (Ö8). 1 puan kırıldı: dosyalar S3'tedir; zone map'ler burada yoktur."),
                sc(9, "Aynı Glue kataloğu. 1 puan kırıldı: yeni alan table tanımına eklenmeden sorgulanamaz."),
                sc(8, "Partition budama. 2 puan kırıldı: external table'larda index yoktur."),
                sc(8, "Sabit düğümler ağır sorguyu taşır. 2 puan kırıldı: düğüm sayısı sabittir; ayda bir ağır sorgu kendi cluster'ının sınırına çarpar."),
                sc(10, "Veri S3'te kalır. Puan kırılmadı."),
                sc(6, "Yönetilen cluster. 4 puan kırıldı: düğüm tipi ve sayısı seçilir, resize ve pause/resume zamanlaması ekibin işidir."),
                sc(3, "Düğüm saat başına ödenir ve Spectrum taranan TB başına ayrıca ödenir. 7 puan kırıldı: haftada 30 sorgu için düğümler bütün hafta çalışır.")],
    },
    h2h={
        "rs": "Data warehouse (Redshift Serverless) ile kafa kafaya. Bu kartta iki servis S3'teki aynı Parquet dosyalarını aynı biçimde okur: Redshift'in Spectrum katmanı ve Athena kolonları ve partition'ları okur, table tanımları aynı Glue kataloğundadır. R1 puanları eşittir (38,4). "
              "Farkı servis tasarımı verir: Athena'da kurulacak bir sistem yoktur ve sorgu taradığı TB kadar ödenir; Redshift Serverless'ta bir workgroup kurulur ve her sorgu base RPU ile en az 60 saniye ödenir (R4, R5). "
              "Redshift'in dürüst üstünlüğü ağır sorgu ve yerel veriyle birleştirmededir: Serverless kapasiteyi artırır (R2) ve aynı sorgu S3 dosyalarını warehouse'taki table'larla JOIN'ler. "
              "Hangi koşul değişseydi Redshift seçilirdi: sorular günde yüzlerce olsaydı, aynı sorular panolara dönüşseydi ya da veri gölündeki dosyalar warehouse'taki satış table'larıyla sık sık birleştirilseydi.",
        "rsp": "Data warehouse, provisioned cluster (Redshift provisioned) ile kafa kafaya. Aynı engine ve aynı Spectrum katmanı: R1 puanları Athena ve Serverless ile eşittir. "
               "Ama haftada 30 sorgu için düğümler bütün hafta çalışır (R5) ve düğüm planı ekibin işidir (R4). Pause/resume ile cluster sorgu olmayan saatlerde durdurulabilir; bu fatura farkını azaltır ama analistlerin ne zaman soru soracağı önceden bilinmez. "
               "Provisioned cluster'ın dürüst üstünlüğü düz ve sürekli yüktedir (kart 8). "
               "Hangi koşul değişseydi Redshift provisioned seçilirdi: aynı cluster zaten 7/24 başka bir iş için çalışıyor olsaydı; o zaman ara sıra gelen Spectrum sorguları sadece taranan TB kadar ek fatura doğururdu.",
    },
    verdict="Karar: Athena {ath}, Redshift {rs}, Redshift provisioned {rsp}. R1'de üç aday eşittir; kararı R4 ve R5 verir: ara sıra gelen sorular için veri yerinde kalmalı ve sadece çalışan sorgu ödenmelidir. "
            "Yine de Redshift seçersek artımız: aynı SQL, ağır sorguda daha fazla kapasite ve veri gölünü warehouse'taki satış table'larıyla tek sorguda birleştirme (Ö8). "
            "Eksimiz: bir workgroup kurulur ve işletilir, her sorgu en az 60 saniye ödenir; uygulama ya da analist sorguları partition filtresiyle yazmalı ve sık sorulan soruları bir yerel table'a almalıdır. "
            "Doğru mimari çoğu zaman ikisi birliktedir: ham veri gölü Athena ile, düzenli raporlar Redshift'te. Bir koşul değişseydi: sorular günde yüzlerce olsaydı ya da panolara dönüşseydi Redshift öne geçerdi."))

USECASES_W["redshift"] = REDSHIFT_W
PAGE_SVC["redshift"] = "rs"


# ================================================================ Timestream for InfluxDB (time series), model 2, Turkish
# Candidates: "ix" = Timestream for InfluxDB 2 DB instance (SVC "Timestream for InfluxDB", the page's service; Single-AZ, Multi-AZ
# and the read replica cluster are deployment options of the same engine, not separate services). "ix3" = Timestream for
# InfluxDB 3 (Enterprise edition in the cards). InfluxDB 2 and InfluxDB 3 share the data model (line protocol: measurement,
# tags, fields, timestamp) but not the engine (TSM files with Flux against Arrow/DataFusion/Parquet on S3 with SQL): they are
# NOT twins and their R1 is scored separately (decisions.md, "Same data model, different engine").
# Five cards repeat a workload of an accepted page and keep its rows, weights and points (decisions.md, "The same workload on
# two pages"): 2 = OpenSearch card 7, 3 = Keyspaces card 2, 8 = OpenSearch card 10, 9 = DynamoDB card 5, 10 = ElastiCache card 5.
# Their points are read from the source card at import time (_same), so the two pages can never drift; the reasons of the
# other candidates are the source reasons without the feature numbers of the other page; the reasons of "ix" are new.
# Facts and prices: docs/influxdb.scope.md.
CATEGORY.setdefault("ix3", ("columnar time series (InfluxDB 3)", "columnar time series (InfluxDB 3)"))
LINK.setdefault("ix3", "influxdb")         # InfluxDB 3 has no page of its own; this page (A10, M5, C2) compares it


def _src(page, uid):
    return next(uc for uc in USECASES_W[page] if uc["id"] == uid)


_OTHER_NO = re.compile(r"\s*\((?:[ÖF]\d(?:[^()]*)?)\)|\s*\([^()]*\b[ÖF]\d\b[^()]*\)")


def _strip(t):
    """A reason of another page without that page's feature numbers (Ö1 ... Ö8 belong to the other page)."""
    return re.sub(r"\s{2,}", " ", _OTHER_NO.sub("", t)).replace(" .", ".").strip()


def _same(src, c, reasons=None):
    """The points of candidate c on the source card, with new reasons (or the source reasons without feature numbers)."""
    pts = [p for p, _ in src["scores"][c]]
    if reasons is None:
        reasons = [_strip(w[1]) for _, w in src["scores"][c]]
    assert len(reasons) == len(pts), (src["id"], c)
    return [sc(p, r) for p, r in zip(pts, reasons)]


def _rows(src):
    return [row(r["code"], r["w"], r["wwhy"][1], r["want"][1], r["why"][1]) for r in src["rows"]]


INFLUXDB_W = []

# ------------------------------------------------------------------ 1. Lale Market warehouses and stores
INFLUXDB_W.append(wusecase("warehouse", 1, sim="w_warehouse",
    title="Depo ve mağaza ortam izleme (Lale Market)",
    key="Measurement: env. Tag'ler: site (40 değer) ve sensor (25 değer). Field: value. 10 saniyede bir point; 1.000 series.",
    story="Lale Market bugün 4 deposunun sıcaklık ve nemini 5 dakikada bir Operations sayfasında çizer. Franchise planıyla 40 depo ve mağazaya, "
          "her birinde 25 sensöre çıkıyor: 1.000 sensör 10 saniyede bir okuma gönderir, yani saniyede 100 point; mağaza başına iki kanalın (web, mobil) dakikalık sipariş "
          "sayıları da aynı ekrana gelir: 80 series daha. Operations sayfası ve Grafana \"son 6 saat, mağaza başına 1 dakikalık ortalama\" ve \"son 24 saat, 15 dakikalık\" "
          "sorularını sorar. Nem 30 dakika boyunca yüzde 70'in üstünde kalırsa (kitap ve elektronik rafları) 5 dakika içinde nöbetçiye haber gitmelidir. "
          "Ham okumalar 30 gün, saatlik ortalamalar 2 yıl tutulur. Sensörler bir mağaza gateway'ine bağlıdır ve gateway bir saatlik okumayı tampon tutar. "
          "Ekip üç geliştiriciden oluşur ve SQL ile Grafana bilir. Siparişler zaten Aurora'dadır; EC2 metrikleri zaten CloudWatch'a gelir.",
    wnote="R1 toplam 48: veri bir zaman serisidir (VM 10), her soru bir zaman penceresidir (EY 12), 30 günlük ham veri sıkıştırılarak saklanmalıdır (DA 8), "
          "eski veri özetlenip silinir (YD 10) ve nem kuralı bir eşik kontrolüdür (AO 8). R4 15 ve R5 15 ile ikinci sıradadır: üç kişilik ekip "
          "yeni bir sistemi işletecek ve 1.000 series'in aylık faturası franchise planıyla büyür.",
    rows=[
        row("VM", 10, "Her okuma bir zaman, iki etiket ve bir sayıdır; model bunu doğrudan taşımalı.",
            "Okuma = zaman + etiketler (site, sensor) + sayı. Aynı etiketli okumalar bir series olarak saklanmalı; etiketler her okumada tekrar yazılmamalı.",
            "Her okuma etiketleriyle ayrı bir kayıt olursa storage ve okuma bir series modeline göre katlanır."),
        row("EY", 12, "Operations sayfası ve Grafana her yenilemede bu soruyu sorar.",
            "\"Son 6 saat, mağaza başına 1 dakikalık ortalama\", \"son 24 saat, 15 dakikalık maksimum\": zaman aralığı + tag filtresi + pencere toplamı, birkaç yüz milisaniyede.",
            "Pencere hesabı uygulamada yapılırsa her grafik bütün ham okumaları çeker; 1.000 series'te sayfa saniyelerce bekler."),
        row("DA", 8, "30 günlük ham veri yaklaşık 260 milyon okumadır; engine'in saklama biçimi diski ve okuma hızını belirler.",
            "30 günlük ham okumalar series ve zaman sırasıyla bitişik ve sıkıştırılmış saklanmalı; bir pencere sadece kendi zaman aralığını okumalı.",
            "Okumalar sıkıştırılmadan ve zamana göre gruplanmadan saklanırsa 260 milyon row'luk bir table her grafikte büyük bir index taraması olur."),
        row("YD", 10, "30 gün sonra her gün yaklaşık 8,6 milyon okuma düşmeli ve saatlik özet 2 yıl kalmalıdır.",
            "Ham okumalar 30 gün sonra kendiliğinden silinmeli; saatlik ortalamalar ayrı tutulmalı ve 2 yıl kalmalı.",
            "Silme ve özetleme elle yapılırsa unutulur; silinmeyen veri her ay büyür ve grafikler yavaşlar."),
        row("AO", 8, "Nem kuralı rafları korur ve bu kartın tek otomatik tepkisidir.",
            "\"Nem 30 dakika boyunca yüzde 70'in üstünde\" kuralı database'in yanında bir ayar ya da kısa bir tanım olmalı ve 5 dakika içinde haber vermeli.",
            "Kural uygulama koduna gömülürse her yeni kural bir deploy'dur; kural yanlış çalışırsa ıslanan kitaplar satılamaz."),
    ] + [
        row("R2", 12, "Saniyede 100 okuma küçüktür ama franchise planıyla on kat büyüyebilir.",
            "Saniyede 100 okuma yazma, düz; Operations sayfası ve Grafana'da 15 kullanıcı. Plan 3 yılda 400 mağazaya çıkmak, yani saniyede 1.000 okuma yazma.",
            "Yazma geride kalırsa grafik son dakikayı göstermez ve nem alarmı geç çalışır."),
        row("R3", 10, "Gateway bir saatlik tampon tuttuğu için kısa bir kesinti veri kaybettirmez.",
            "Bir AZ arızasında okumalar kaybolmamalı; gateway bir saat tampon tuttuğu için birkaç dakikalık yazma kesintisi kabul edilir.",
            "Okumalar kaybolursa nem olayının ne zaman başladığı bilinmez ve raf hasarı kanıtlanamaz."),
        row("R4", 15, "Üç geliştirici yeni bir sistemi işletecek; zaman ayıracakları her iş satıştan gider.",
            "Sunucu, yedek ve yama işi en az olmalı. Ekip SQL ve Grafana biliyor; yeni bir sorgu dili öğrenmek bir maliyettir.",
            "Metrik sistemi bozulduğunda onu da aynı üç kişi düzeltir; bilinmeyen bir sistem gece arızasını uzatır."),
        row("R5", 15, "Fatura series sayısıyla büyümemeli; franchise planı series sayısını on katına çıkarır.",
            "1.080 series (1.000 sensör + 80 sipariş series'i), ayda yaklaşık 260 milyon okuma, birkaç GB. Series sayısı 3 yılda on katına çıkabilir; fatura buna göre öngörülebilir olmalı.",
            "Series başına ödenen bir modelde her yeni mağaza faturayı doğrudan büyütür."),
    ],
    cands=["ix", "cw", "aur"],
    scores={
        "ix": [sc(10, "Point = measurement + tag set + field + timestamp (Ö1); aynı site ve sensor tag'li okumalar bir series'tir ve tag'ler series key'de bir kez durur (Ö2). Puan kırılmadı."),
               sc(10, "range() + tag filtresi sadece istenen zaman aralığının shard'larını okur (Ö4); aggregateWindow mağaza başına 1 dakikalık ortalamayı tek sorguda verir (Ö5). Puan kırılmadı."),
               sc(10, "Okumalar series key'e göre gruplanır, zamana göre sıralanır ve TSM dosyalarında delta kodlamasıyla sıkıştırılır; günlük shard group'lar sorgunun aralığını sınırlar (Ö3). Puan kırılmadı."),
               sc(9, "Bucket'ın retention period'u 30 günü geçen shard group'u bütün olarak düşürür (Ö7). 1 puan kırıldı: saatlik ortalamaları ikinci bucket'a yazan downsampling task'ını ekip yazar."),
               sc(9, "Bir check her dakika son 30 dakikayı sorar ve eşik aşılınca notification endpoint'e haber verir (Ö8). 1 puan kırıldı: \"30 dakika boyunca\" koşulu check'in Flux sorgusuna yazılır (stateDuration, bir durumun ne kadar sürdüğünü sayan fonksiyon); haber check aralığı kadar gecikir."),
               sc(9, "Saniyede 100 point db.influx.medium için çok küçüktür. 1 puan kırıldı: bütün yazmalar tek instance'tan geçer; 400 mağazada instance sınıfı büyütülür."),
               sc(9, "Multi-AZ standby senkron replikadır; AWS'e göre failover genellikle 60–120 saniye sürer. 1 puan kırıldı: o sürede yazmalar başarısız olur, gateway tamponu okumaları sonra gönderir."),
               sc(5, "Yönetilen instance: yama, yedek ve failover AWS'tedir. 5 puan kırıldı: instance sınıfı ve storage tipi ekibin seçimidir ve Flux ekip için yeni bir dildir; Grafana'nın paneli Flux ya da InfluxQL ile yazılır."),
               sc(8, "Instance-saat ve storage ödenir; series sayısı faturayı doğrudan büyütmez (Ö2). 2 puan kırıldı: Multi-AZ standby ikinci bir instance ücretidir; db.influx.medium Multi-AZ ayda yaklaşık 211 USD, 20 GiB storage yaklaşık 4,8 USD (Frankfurt, Price List API, 2026-10-31).")],
        "cw": [sc(9, "Bir metric namespace, ad ve dimension'larla tanımlanır ve zamanlı sayılar tutar. 1 puan kırıldı: her dimension birleşimi ayrı bir metric'tir; site × sensor birleşimleri metric sayısını katlar."),
               sc(9, "Her periyot için Average ve Maximum hesaplanır; math expression'lar serileri birleştirir. 1 puan kırıldı: 10 saniyelik çözünürlük için high-resolution metric yayınlanır."),
               sc(10, "Metrik verisini servis saklar ve bir zaman aralığının istatistiklerini doğrudan okur; saklama biçimi ekibin işi değildir. Puan kırılmadı: ham verinin ne kadar tutulduğu R1.4'te sayılır."),
               sc(3, "Özetleme ve silme kendiliğindendir. 7 puan kırıldı: AWS'e göre 60 saniyeden kısa periyotlu veri 3 saat, dakikalık veri 15 gün, saatlik veri 455 gün tutulur; isteğin iki parçası karşılanmaz (30 günlük ham verinin 3 saati kalır, 2 yıllık özet 15 ayda biter), bu yüzden ölçeğin 0–3 bandındadır."),
               sc(10, "Bir alarm \"6 periyodun 6'sı\" gibi bir kuralla 30 dakikalık koşulu ayar olarak tanımlar ve SNS ile haber verir. Puan kırılmadı."),
               sc(10, "Yazma ve okuma kapasitesi servisindir. Puan kırılmadı."),
               sc(10, "Metrikler servis tarafından kalıcı saklanır. Puan kırılmadı."),
               sc(9, "Sunucu yoktur; EC2 metrikleri zaten oradadır ve alarm aynı servistedir. 1 puan kırıldı: gateway'ler okumaları PutMetricData ya da gömülü metric formatı ile yayınlar."),
               sc(6, "Custom metric başına ödenir. 4 puan kırıldı: 1.080 metric ayda yaklaşık 324 USD'dir (Frankfurt, ilk 10.000 metric için 0,30 USD) ve her yeni mağaza faturayı büyütür.")],
        "aur": [sc(9, "Bir okuma bir row'dur: (ts, site, sensor, value). 1 puan kırıldı: engine'de series kavramı yoktur; site ve sensor her row'da tekrar yazılır."),
                sc(9, "date_bin ile GROUP BY ve window function'lar her pencere sorusunu SQL ile cevaplar. 1 puan kırıldı: boş pencereler için generate_series ile ayrıca join yazılır."),
                sc(5, "(site, sensor, ts) üzerinde B-tree index bir aralığı bulur. 5 puan kırıldı: PostgreSQL row'ları sıkıştırmaz ve zamana göre bitişik tutmaz; 260 milyon row ve index'i diskte birkaç kat yer tutar. Aurora sayfası bütün geçmişi tarayan sorgulara 6–7 puan kırar; burada pencere index ile bulunur ve kayıp sadece storage boyutundadır."),
                sc(4, "PostgreSQL'de retention yoktur. 6 puan kırıldı: 30 günden eski row'lar için zamanlanmış bir DELETE işi (ya da günlük partition'ları düşüren bir iş) ve saatlik özet için ikinci bir iş gerekir; DELETE VACUUM yükü getirir."),
                sc(5, "Engine'de eşik kontrolü ya da bildirim yoktur. 5 puan kırıldı: kural pg_cron ile zamanlanmış bir sorgu ve haber veren bir uygulama kodudur."),
                sc(7, "Saniyede 100 küçük INSERT var olan writer için küçüktür. 3 puan kırıldı: yazmalar siparişlerle aynı writer'dan geçer ve trafik düz olduğu için checkout tepesinde de oradadır; 400 mağazada saniyede 1.000 yazma olur (Aurora sayfasının tek writer tablosu: 500–5.000, checkout ile aynı tepede 3 puan)."),
                sc(10, "Üç AZ'de altı kopya ve sürekli yedek. Puan kırılmadı."),
                sc(9, "Aurora zaten işletiliyor ve ekip SQL biliyor; Grafana PostgreSQL'e doğrudan bağlanır. 1 puan kırıldı: sensör yükü sipariş cluster'ı ile paylaşılır ve ayrıca izlenir."),
                sc(8, "Var olan cluster'da ayrı bir instance ödenmez. 2 puan kırıldı: sıkıştırılmamış row'lar ve index'leri storage ve I/O olarak ödenir ve 400 mağazada ACU üst sınırı yükselir.")],
    },
    h2h={
        "cw": "İzleme servisi (CloudWatch) ile kafa kafaya. Bu yakın bir yarıştır. CloudWatch'un artısı sıfır işletmedir: EC2 metrikleri zaten oradadır, nem kuralı \"6 periyodun 6'sı\" gibi bir alarm ayarıdır, kapasite ve kalıcılık servisindir; R2, R3, R4 ve R1 · AO'da öndedir. "
              "Timestream for InfluxDB'yi öne geçiren iki şeydir. Birincisi R1 · YD: CloudWatch'un saklama kuralı sabittir; AWS'e göre 60 saniyeden kısa periyotlu veri 3 saat, dakikalık veri 15 gün, saatlik veri 455 gün tutulur, yani 30 günlük ham veri ve 2 yıllık saatlik özet karşılanmaz. "
              "İkincisi R5: CloudWatch series başına öder; 1.080 metric ayda yaklaşık 324 USD'dir ve 400 mağazada on katına çıkar, InfluxDB instance'ı ise yaklaşık 211 USD'dir ve büyük ölçüde sabit kalır. "
              "Hangi koşul değişseydi CloudWatch seçilirdi: ham veri 3 saat, özet 15 ay yetseydi ve mağaza sayısı 40'ta kalsaydı; o zaman işletmesiz bir servis fark yaratırdı.",
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Aurora bu kartta var olan bir sistemdir: ayrı bir instance ödenmez, ekip SQL biliyor ve Grafana PostgreSQL'e doğrudan bağlanır; R3, R4 ve R5'te öndedir. 400 mağazada saniyede 1.000 yazma checkout'u da taşıyan writer'a gelir ve R2'de 3 puan kaybettirir. "
               "Ama R1'in üç alt maddesinde geride kalır. PostgreSQL okumaları sıkıştırmaz ve zamana göre bitişik tutmaz; 260 milyon row ve index'i diskte birkaç kat yer tutar (DA). Retention yoktur; 30 günden eski row'lar zamanlanmış bir DELETE ya da partition düşüren bir işle gider ve saatlik özet ikinci bir iştir (YD). "
               "Nem kuralı için engine'de bir kontrol ve bildirim aracı yoktur (AO). Bu üç satırın ağırlığı 26'dır: Aurora 12 alır, Timestream for InfluxDB 24,2. "
               "Hangi koşul değişseydi Aurora seçilirdi: sadece 4 deponun 8 sensörü kalsaydı (bugünkü workshop verisi), ham veri birkaç gün tutulsaydı ve sensör verisi siparişlerle aynı SQL'de join'lenmek istenseydi.",
    },
    verdict="Karar: Timestream for InfluxDB {ix}, CloudWatch {cw}, Aurora {aur}. Yakın bir yarış: bu iş yüküne en uygun servis Timestream for InfluxDB'dir, çünkü series modeli, pencere sorusu, sıkıştırılmış saklama ve retention engine'in kendisidir (R1'de 48'in 46,2'si). "
            "CloudWatch işletmede ve alarmda öndedir; saklama kuralı ve series başına fiyat onu geride bırakır. "
            "Timestream for InfluxDB seçtiğimizde artımız: 1.000 series tek bir instance'ta, grafik başına tek bir Flux sorgusu, ham veri 30 gün sonra kendiliğinden gider ve fatura mağaza sayısıyla patlamaz. "
            "Eksimiz: instance sınıfını ve storage'ı biz seçeriz; ekip Flux öğrenir; downsampling task'ını ve nem check'ini biz yazarız. "
            "Bir koşul değişseydi: ham veri 3 saat yetseydi ve mağaza sayısı büyümeseydi CloudWatch kazanırdı."))

# ------------------------------------------------------------------ 2. application metrics (= OpenSearch card 7)
_s = _src("opensearch", "metrics")
INFLUXDB_W.append(wusecase("metrics", 2, sim="w_metrics",
    title=_s["title"][1], key=_s["key"][1], story=_s["story"][1], wnote=_s["wnote"][1], rows=_rows(_s),
    cands=["ix", "cw", "os"],
    scores={
        "ix": _same(_s, "ix", [
            "Point = measurement + tag set + field + timestamp (Ö1); aynı host ve metric tag'li point'ler bir series'tir ve series olarak sıkıştırılır (Ö2, Ö3). Puan kırılmadı.",
            "aggregateWindow (Flux) ya da GROUP BY time (InfluxQL) pencere başına ortalama, maksimum ve yüzdelik verir (Ö5). Puan kırılmadı.",
            "Bucket'ın retention period'u eski veriyi siler; downsampling bir task'tır (Ö7). 1 puan kırıldı: dakikalık ve saatlik özetleri yazan task'ları ekip yazar.",
            "Saniyede 240 point bir instance için küçüktür. 1 puan kırıldı: bütün yazmalar tek bir instance'tan geçer; series sayısı on kat büyürse instance büyütülür.",
            "Multi-AZ seçeneği bir standby tutar. 2 puan kırıldı: failover sırasında (AWS'e göre genellikle 60–120 saniye) birkaç dakikalık yazma boşluğu olabilir.",
            "Yönetilen instance; Grafana doğrudan bağlanır. 4 puan kırıldı: instance sınıfı ve storage ekibin seçimidir, ajanlar (Telegraf) kurulur ve EC2 ile load balancer metrikleri ayrıca taşınır.",
            "Instance-saat ve storage ödenir; series sayısı faturayı doğrudan büyütmez (Ö2). 2 puan kırıldı: Multi-AZ standby ikinci bir instance ücretidir; db.influx.medium Multi-AZ ayda yaklaşık 211 USD (Frankfurt, Price List API, 2026-10-31)."]),
        "cw": _same(_s, "cw"), "os": _same(_s, "os")},
    h2h={"cw": "İzleme servisi (CloudWatch) ile kafa kafaya. Fark 8,2 puandır; yakın bir yarış değildir. CloudWatch'un artısı sıfır işletmedir: EC2 ve load balancer metrikleri zaten oradadır, özetleme ve silme kendiliğindendir, alarm aynı servistedir ve kapasite servisindir. R2, R3 ve R4'te birlikte 8,4 puan önde olur (1,4 + 1,6 + 5,4). Timestream for InfluxDB R1'de 11,2 puan ve R5'te 5,4 puan önde olur. Tek satırda en büyük fark R1 · YD'dedir (8,4 puan): CloudWatch'un saklama kuralı sabittir; AWS'e göre 60 saniyeden kısa periyotlu veri 3 saat, dakikalık veri 15 gün tutulur, yani isteğin üç parçasından ikisi (6 saatlik 10 saniyelik veri ve 30 günlük dakikalık veri) karşılanmaz ve puan 0–3 bandındadır (kart 1'deki gibi 3). R5'te CloudWatch series başına öder; 2.400 series ayda yaklaşık 720 USD'dir ve series sayısıyla büyür, InfluxDB instance'ı ise yaklaşık 211 USD'dir. Hangi koşul değişseydi CloudWatch seçilirdi: 10 saniyelik veri 3 saat ve dakikalık veri 15 gün yetseydi (R1 · YD tam karşılanır, 86,4'e 84,8); series sayısının birkaç yüz olması (yaklaşık 700 series'te iki fatura eşitlenir) tek başına farkı kapatmaz.", "os": _strip(_s["h2h"]["os"][1]).replace("(kart 5)", "(OpenSearch sayfasının 5. kartı)")},
    verdict="Karar: Timestream for InfluxDB {ix}, CloudWatch {cw}, OpenSearch {os}. Bu iş yüküne en uygun servis bir time series engine'idir, çünkü series modeli, pencere sorusu ve retention engine'in kendisidir. "
            "CloudWatch işletmede öndedir; isteğin iki parçasını karşılamayan sabit saklama kuralı ve series başına fiyat onu 8,2 puan geride bırakır. Bu kart OpenSearch sayfasının 7. kartıyla aynı iş yüküdür ve aynı puanları taşır. "
            "Timestream for InfluxDB seçtiğimizde artımız: 2.400 series tek bir instance'ta, pano başına tek bir sorgu, eski veri kendiliğinden gider ve fatura series sayısıyla büyümez. "
            "Eksimiz: instance'ı ve storage'ı biz seçeriz, Telegraf ajanlarını kurarız, downsampling task'larını yazarız ve EC2 metriklerini ayrıca taşırız. "
            "Bir koşul değişseydi: 10 saniyelik veri 3 saat ve dakikalık veri 15 gün yetseydi CloudWatch kazanırdı."))

# ------------------------------------------------------------------ 3. wind farm sensors (= Keyspaces card 2)
_s = _src("keyspaces", "sensor")
INFLUXDB_W.append(wusecase("sensor", 3, sim="w_sensor",
    title=_s["title"][1], key=_s["key"][1], story=_s["story"][1], wnote=_s["wnote"][1], rows=_rows(_s),
    cands=["ks", "ix", "ddb"],
    scores={
        "ks": _same(_s, "ks"),
        "ix": _same(_s, "ix", [
            "Bir sensörün bir saati range() ve tag filtresiyle sorulur (Ö4); türbin tag'i bütün sensörlerini tek sorguda verir. Puan kırılmadı.",
            "Point'in kendisi: measurement, tag'ler, field'lar ve timestamp (Ö1). Etiketler series key'de bir kez durur (Ö2). Puan kırılmadı.",
            "Engine okumaları series series ve zaman sırasıyla, delta kodlamasıyla sıkıştırarak saklar; yavaş değişen sayılar birkaç kat küçülür (Ö3). Puan kırılmadı.",
            "Bucket'ın retention period'u 90 gün; süresi dolan shard group bütün olarak düşer (Ö7). Puan kırılmadı.",
            "Saniyede 4.000 point, düz ve büyümeyen bir yük olarak, uygun boyutlu bir instance için olağandır; instance sınıfını seçmek R4'te sayıldı. Puan kırılmadı.",
            "Multi-AZ standby seçeneği vardır. 3 puan kırıldı: standby'a geçişte (AWS'e göre genellikle 60–120 saniye) yazmalar başarısız olur ve tampon tutmayan sensörlerin o anki okumaları kaybolur.",
            "Yönetilen instance. 5 puan kırıldı: instance ve storage boyutlandırma ekibin işidir ve Flux ya da InfluxQL ekip için yeni bir dildir; Cassandra bilgisi kullanılmaz.",
            "Düz trafik saat başına ödenen instance'a uyar. 2 puan kırıldı: Multi-AZ standby ikinci bir instance ücretidir ve instance boşken de ödenir."]),
        "ddb": _same(_s, "ddb")},
    h2h={"ix": "Time series (Timestream for InfluxDB) ile kafa kafaya. Engine uyumunu Timestream for InfluxDB kazanır: R1'in 50 puanının hepsini alır. Okuma bir point'tir (Ö1), etiketler series key'de bir kez durur (Ö2), sayılar series series sıkıştırılır (Ö3) ve 90 günlük retention bucket'ın bir ayarıdır (Ö7); Keyspaces bu dört alt maddede 42 alır. "
                "Toplamı servis tasarımı ve ekip kaybettirir. Sensörler tampon tutmaz; standby'a geçişin 60–120 saniyesinde gelen okumalar kaybolur (R3). Ekip Cassandra'yı ve CQL'i bilir; Flux ve instance boyutlandırma yenidir (R4). Standby ikinci bir instance ücretidir (R5). Fark 2,8 puandır. "
                "Saatlik ortalamaları bu hikâyede gece bir Spark işi hesaplar; engine'in pencere hesabı kullanılmaz. "
                "Hangi koşul değişseydi Timestream for InfluxDB seçilirdi: mühendis ekranı canlı pencereler isteseydi, sensörlerin bir tamponu olsaydı ve ekip CQL bilmeseydi. En dürüst cevap o zaman ikisinin birlikte çalışmasıdır: ham kanıt Keyspaces'te, canlı pencereler InfluxDB'de.",
         "ddb": _strip(_s["h2h"]["ddb"][1])},
    verdict="Karar: Keyspaces {ks}, Timestream for InfluxDB {ix}, DynamoDB {ddb}. Yakın bir yarış: engine uyumunu Timestream for InfluxDB kazanır (50'ye 42), toplamı Keyspaces alır; tampon tutmayan sensörlerin failover'da kaybolan okumaları (R3) ve ekibin Cassandra bilgisi (R4) bu kartta engine farkından ağır basar. "
            "Bu kart Keyspaces sayfasının 2. kartıyla aynı iş yüküdür ve aynı puanları taşır. "
            "Yine de Timestream for InfluxDB seçersek artımız: okumalar sıkıştırılır, 90 günlük retention bir ayardır ve saatlik ortalamalar gece işi olmadan bir task ile hesaplanır. "
            "Eksimiz: sensörlerin önüne bir tampon (örneğin gateway'de Telegraf'ın buffer'ı) koymalıyız ki failover'da okuma kaybolmasın; ekip Flux öğrenir ve instance'ı boyutlandırır. "
            "Bir koşul değişseydi: sensörlerin önünde bir tampon olsaydı (R3 7'den 9'a) ve ekip CQL bilmeseydi (Keyspaces R4'ü düşer) Timestream for InfluxDB öne geçerdi; tek başına tampon yetmez (90,4'e 91,2). Mühendisler canlı pencere isterse ikisinin birlikte çalışması en dürüst cevaptır."))

# ------------------------------------------------------------------ 4. fleet telemetry
INFLUXDB_W.append(wusecase("fleet", 4,
    title="Filo telemetrisi: 5.000 kamyonun son değeri ve geçmişi",
    key="Measurement: truck. Tag: truck_id (5.000 değer), region. Field'lar: speed, fuel, engine_temp, lat, lon. 10 saniyede bir point.",
    story="Bir lojistik şirketinin 5.000 kamyonu her 10 saniyede bir telemetri gönderir: hız, yakıt, motor sıcaklığı ve konum. Bu saniyede 500 point ve 5.000 series demektir; "
          "iki yılda filo 20.000 kamyona çıkacak. Sevk ekranı 10 saniyede bir her kamyonun son değerini gösterir; bir kamyona tıklanınca son 24 saatin 5 dakikalık motor sıcaklığı "
          "maksimumu çizilir; haftalık rapor kamyon başına yakıt tüketimini toplar. Ham veri 90 gün tutulur, sonra silinir. Kamyonların cihazları bağlantı koptuğunda okumaları "
          "tamponlar ve sonra gönderir. Dört kişilik ekip SQL biliyor; şirketin başka bir time series sistemi yok.",
    wnote="R1 toplam 46: son değer ve pencere soruları (EY 14) bu iş yükünün ekranıdır; series modeli (VM 10), 90 günlük ham verinin saklanması (DA 12) ve retention (YD 10) onu tamamlar. "
          "R4 15 ve R5 15: dört kişilik ekip yeni bir sistemi işletecek ve filo dört katına çıkarken fatura öngörülebilir kalmalı.",
    rows=[
        row("EY", 14, "Sevk ekranı 10 saniyede bir 5.000 son değeri ister; bu kartın en sık sorusu budur.",
            "\"Her kamyonun son değeri\" (5.000 series, 10 saniyede bir) ve \"bu kamyonun son 24 saati, 5 dakikalık maksimum\"; ikisi de bir saniyenin altında dönmeli.",
            "Son değer her seferinde ham veriden aranırsa sevk ekranı yavaşlar; dispeçer bir kamyonun durduğunu geç görür."),
        row("VM", 10, "Bir okuma zaman, iki etiket ve beş sayıdır.",
            "Okuma = zaman + etiketler (truck_id, region) + birkaç sayı. Aynı kamyonun okumaları bir series olmalı.",
            "Okumalar etiketleriyle ayrı kayıtlar olursa storage katlanır ve kamyon başına okuma birçok kayda dağılır."),
        row("DA", 12, "90 günlük ham veri yaklaşık 3,9 milyar point'tir; engine'in saklama biçimi diski ve sorgu süresini belirler.",
            "90 günlük ham veri series ve zaman sırasıyla sıkıştırılmış saklanmalı; 20.000 series'e çıkınca da sorgu süresi aynı kalmalı.",
            "Series sayısı büyüdükçe index belleğe sığmazsa sorgular yavaşlar ve instance büyütülmek zorunda kalır."),
        row("YD", 10, "90 gün sonra her gün yaklaşık 43 milyon point düşmeli.",
            "90 günden eski veri kendiliğinden silinmeli; silme bir iş olarak yazılmamalı.",
            "Silme unutulursa storage her ay büyür ve fatura artar."),
    ] + [
        row("R2", 14, "Saniyede 500 point bugün küçüktür, iki yılda 2.000'e çıkar.",
            "Saniyede 500, iki yılda 2.000 point; sevk ekranında 30 kullanıcı.",
            "Yazma geride kalırsa sevk ekranı eski konum gösterir."),
        row("R3", 10, "Cihazlar tampon tuttuğu için kısa bir kesinti veri kaybettirmez.",
            "Bir AZ arızasında veri kaybolmamalı; cihazlar tamponladığı için birkaç dakikalık yazma kesintisi kabul edilir.",
            "Kaybolan okumalar bir kaza ya da yakıt hırsızlığı incelemesinde eksik kalır."),
        row("R4", 15, "Dört kişilik ekip ilk time series sistemini işletecek.",
            "Sunucu ve yama işi en az olmalı; ekip SQL biliyor, yeni bir sorgu dili bir maliyettir.",
            "Bilinmeyen bir dil ve elle boyutlandırılan bir sistem gece arızalarını uzatır."),
        row("R5", 15, "Filo dört katına çıkarken fatura doğrusal ve öngörülebilir kalmalı.",
            "Bugün 5.000, iki yılda 20.000 series; 90 günlük veri birkaç yüz GB. Fatura series sayısıyla patlamamalı.",
            "Fatura series ya da storage ile hızlı büyürse filo büyümesi bir maliyet sorununa döner."),
    ],
    cands=["ix3", "ix", "ddb"],
    scores={
        "ix3": [sc(10, "Last Value Cache her series'in son değerini bellekte tutar; AWS'e göre last-value sorguları 10 ms'nin altındadır. Pencere sorusu SQL'de date_bin ile tek sorgudur. Puan kırılmadı."),
                sc(10, "Aynı line protocol: measurement, tag'ler, field'lar ve timestamp; truck_id tag'i bir series tanımlar. Puan kırılmadı."),
                sc(10, "Veri Parquet dosyalarında kolon kolon sıkıştırılır; Enterprise'ın compactor'ı eski dosyaları birleştirir ve AWS'e göre high-cardinality veride daha iyi performans verir. Puan kırılmadı."),
                sc(10, "Enterprise database başına retention period verir; süresi dolan veri sorgulardan çıkar ve silinir. Puan kırılmadı."),
                sc(10, "Enterprise'da yazma ve sorgu node'ları ayrıdır; filo büyüyünce node eklenir. Puan kırılmadı."),
                sc(10, "Veri Amazon S3 üzerindeki object storage'dadır (AWS'e göre 11 dokuz dayanıklılık) ve çok node'lu cluster node'larını AZ'lere dağıtır. Puan kırılmadı."),
                sc(7, "Yönetilen cluster ve SQL; ekip bildiği dili kullanır. 3 puan kırıldı: node sınıfı, node rolleri ve parameter group ekibin seçimidir ve servis ekip için yenidir."),
                sc(6, "Node-saat, kullanılan GB (en az 200 GB) ve Enterprise lisansı ödenir. 4 puan kırıldı: iki node'luk bir cluster (db.influx.large node'u 0,289 USD/saat, ayda yaklaşık 422 USD) ve vCPU başına InfluxData lisansı (AWS Marketplace'ten ayrı bir kalem) Multi-AZ InfluxDB 2 instance'ından pahalıdır.")],
        "ix": [sc(8, "Son değer tag'e göre last() ile, pencere aggregateWindow ile sorulur (Ö4, Ö5, Ö6). 2 puan kırıldı: son değer bir önbellek değil, 5.000 series üzerinde her 10 saniyede çalışan bir sorgudur."),
               sc(10, "Point = measurement + tag set + field'lar + timestamp (Ö1); truck_id tag'i bir series'tir (Ö2). Puan kırılmadı."),
               sc(9, "TSM dosyaları series'i zaman sırasıyla, delta kodlamasıyla sıkıştırır (Ö3). 1 puan kırıldı: series index'i (TSI) series sayısıyla büyür; 20.000 series engine için olağandır ama bellek izlenir (instance seçimi R4'te)."),
               sc(10, "Bucket'ın retention period'u 90 günü geçen shard group'u düşürür (Ö7). Puan kırılmadı."),
               sc(9, "Saniyede 2.000 point tek instance için küçüktür. 1 puan kırıldı: bütün yazmalar tek instance'tan geçer; filo büyüyünce instance sınıfı değişir (kısa bir kesintiyle)."),
               sc(9, "Multi-AZ standby senkron replikadır. 1 puan kırıldı: failover genellikle 60–120 saniyedir; cihazlar tamponladığı için okuma kaybolmaz, sadece gecikir."),
               sc(5, "Yönetilen instance. 5 puan kırıldı: instance ve storage boyutlandırma ekibin işidir ve ekip SQL biliyor; InfluxDB 2'nin dilleri Flux ve InfluxQL'dir, ikisi de ekip için yenidir."),
               sc(8, "Instance-saat ve storage ödenir; series sayısı faturayı doğrudan büyütmez. 2 puan kırıldı: Multi-AZ db.influx.large ayda yaklaşık 421 USD ve SSD storage (0,238 USD/GB-ay, Multi-AZ) önceden ayrılır.")],
        "ddb": [sc(6, "Kamyon başına son değer bir item'dır ve key ile okunur. 4 puan kırıldı: \"son 24 saat, 5 dakikalık maksimum\" engine'de hesaplanmaz; uygulama okumaları Query ile çeker ve pencereyi kendisi hesaplar."),
                sc(8, "Bir okuma bir item'dır; partition key kamyon, sort key zaman. 2 puan kırıldı: etiketler her item'da tekrar yazılır ve son değer için ikinci bir item yazılır."),
                sc(6, "Item collection zaman sırasıyla bitişiktir. 4 puan kırıldı: time series'e özgü sıkıştırma yoktur; 3,9 milyar item item boyutuyla saklanır."),
                sc(9, "TTL attribute'u 90 gün sonra item'ı yazma kapasitesi harcamadan siler. 1 puan kırıldı: silme genellikle birkaç gün içinde olur; o zamana kadar eski okumalar görünür."),
                sc(10, "Yazmalar kamyonların partition'larına dağılır. Puan kırılmadı."),
                sc(10, "Her yazma birkaç AZ'de saklanır. Puan kırılmadı."),
                sc(8, "Serverless. 2 puan kırıldı: ekip SQL biliyor; DynamoDB API'si yenidir ve pencere hesabını uygulama kodu taşır (hesabın kendisi R1.1'de sayıldı)."),
                sc(6, "İstek ve GB başına ödenir. 4 puan kırıldı: saniyede 2.000 yazma ve son değer için ikinci yazma ayda yaklaşık 10 milyar yazma birimidir; sıkıştırılmamış storage da büyür.")],
    },
    h2h={"ix": "Time series (Timestream for InfluxDB) ile kafa kafaya. Fark 6,4 puandır; iki aday aynı veri modelini, aynı line protocol'ü kullanır, ama engine'leri farklıdır. "
                "InfluxDB 2 son değeri her seferinde ham series'ten bir sorguyla bulur (last(), Ö6); InfluxDB 3'ün Last Value Cache'i onu bellekte hazır tutar. R1.1'de 2 puan kırılır (katkıda 2,8). Series sayısı 20.000'e çıkarken TSI index'i büyür (R1.3'te 1 puan, katkıda 1,2). "
                "Ekip SQL biliyor; InfluxDB 3 SQL konuşur, InfluxDB 2 Flux ve InfluxQL konuşur (R4). InfluxDB 2'nin dürüst üstünlüğü fiyattır: Multi-AZ db.influx.large ayda yaklaşık 421 USD'dir; iki node'luk bir InfluxDB 3 cluster'ı (db.influx.large) yaklaşık 422 USD artı vCPU başına Enterprise lisansıdır (R5). "
                "Hangi koşul değişseydi Timestream for InfluxDB seçilirdi: ekip Flux ya da InfluxQL bilseydi ve var olan Flux task'ları ve Grafana panoları taşınacak olsaydı; o zaman R4 InfluxDB 2'ye geçer (kabaca 4,5 puan) ve filo 5.000'de kalırsa R1.3 farkı da kapanır.",
         "ddb": "Key-value (DynamoDB) ile kafa kafaya. DynamoDB son değerde güçlüdür: kamyon başına bir item key ile tek okumadır ve servis kapasite ve dayanıklılıkta (R2, R3) tam puan alır. "
                "Ama bu kartın ikinci sorusu bir zaman penceresidir: \"son 24 saat, 5 dakikalık maksimum\" engine'de hesaplanmaz, uygulama okumaları çeker ve kendisi toplar. 3,9 milyar okuma sıkıştırılmadan item boyutuyla saklanır ve her okuma bir yazma birimidir; R1'de ve R5'te kayıp büyüktür. "
                "Hangi koşul değişseydi DynamoDB seçilirdi: ekran sadece son değeri gösterseydi ve geçmiş başka bir sisteme gitseydi (DynamoDB sayfasının 5. kartı, bu sayfanın 9. kartı). Doğru mimari o zaman ikisinin birlikte çalışmasıdır: son değer DynamoDB'de, geçmiş bir time series engine'inde.",
         },
    verdict="Karar: Timestream for InfluxDB 3 {ix3}, Timestream for InfluxDB {ix}, DynamoDB {ddb}. Fark 6,4 puan: iki InfluxDB aynı veri modelini taşır, ama InfluxDB 3'ün son değer önbelleği, Parquet saklaması ve SQL'i bu ekrana ve bu ekibe daha iyi uyar; InfluxDB 2 fiyatta öndedir. "
            "Yine de Timestream for InfluxDB seçersek artımız: lisanssız ve sabit bir fatura, olgun bir engine ve Grafana ile doğrudan bağlantı. "
            "Eksimiz: sevk ekranının son değer sorgusunu 10 saniyede bir çalıştırırız ve sonucunu uygulamada önbellekleriz; ekip Flux öğrenir; filo büyüdükçe instance sınıfını değiştiririz. "
            "Bir koşul değişseydi: ekip Flux ya da InfluxQL bilseydi ve var olan panolar taşınacak olsaydı Timestream for InfluxDB kazanırdı."))

# ------------------------------------------------------------------ 5. factory monitoring with checks and downsampling
INFLUXDB_W.append(wusecase("factory", 5,
    title="Fabrika makine izleme: eşik alarmları ve downsampling (var olan InfluxDB'den taşıma)",
    key="Measurement: machine. Tag'ler: line, machine_id (2.000 değer). Field'lar: vibration_rms, temp, current, … 10 saniyede bir. Bucket'lar: raw (14 gün), 1m (1 yıl), 1h (5 yıl).",
    story="Bir otomotiv yan sanayi fabrikasının 2.000 makinesi var; her makine 10 saniyede bir altı ölçüm gönderir: saniyede 1.200 point, 12.000 series, gece gündüz düz. "
          "Fabrika bunu beş yıldır kendi sunucusunda açık kaynak InfluxDB 2 ile işletiyor: üç bucket (ham 14 gün, dakikalık 1 yıl, saatlik 5 yıl), onları dolduran Flux downsampling task'ları "
          "ve \"titreşim 2 dakika boyunca eşiğin üstünde\" gibi 40 check. Bakım panoları Grafana'dadır. Sunucunun diski doldu ve iki kişilik ekip yönetilen bir servise geçmek istiyor; "
          "task'ları ve panoları yeniden yazmak istemiyor. Makineler hattaki bir Telegraf'a yazar ve Telegraf bağlantı koptuğunda okumaları tamponlar. Bir alarm 1 dakika içinde bakım ekibine düşmelidir.",
    wnote="R1 toplam 46: series modeli (VM 10), pencere soruları (EY 10), üç kademeli retention ve downsampling (YD 13) ve eşik check'leri (AO 13) bu fabrikanın işidir. "
          "R4 16 ile ikinci: iki kişilik ekip 40 check'i, task'ları ve panoları taşıyacak; yeniden yazmak aylar sürer.",
    rows=[
        row("VM", 10, "Her ölçüm bir zaman, iki etiket ve bir sayıdır.",
            "Ölçüm = zaman + etiketler (line, machine_id) + sayılar; 12.000 series.",
            "Model ölçüme uymazsa her okuma etiketleriyle ayrı bir kayıt olur ve storage katlanır."),
        row("EY", 10, "Bakım panoları pencere sorusu sorar; ama bu kartı ayıran soru değil, alarm ve retention'dır.",
            "\"Bu hattın son 8 saati, 1 dakikalık titreşim ortalaması\" ve \"bu makinenin son bir yılı, saatlik maksimum\".",
            "Pencere hesabı uygulamaya kalırsa her pano bütün ham noktaları çeker."),
        row("YD", 13, "Üç kademeli saklama fabrikanın beş yıllık geçmişinin tek yoludur.",
            "Ham veri 14 gün, dakikalık özet 1 yıl, saatlik özet 5 yıl; özetleme ve silme kendiliğinden.",
            "Özetleme bozulursa beş yıllık trend kaybolur; silme bozulursa disk yine dolar."),
        row("AO", 13, "40 check fabrikanın güvenlik ağıdır; kırık bir rulman geç fark edilirse hat durur.",
            "\"Titreşim 2 dakika boyunca eşiğin üstünde\" gibi 40 kural database'in yanında tanımlı olmalı ve 1 dakika içinde haber vermeli.",
            "Kural geç çalışırsa bir rulman kırılır ve hat saatlerce durur."),
    ] + [
        row("R2", 12, "Saniyede 1.200 point gece gündüz düzdür; büyüme yok.",
            "Saniyede 1.200 point, düz; 25 kullanıcının panosu dakikada bir yenilenir.",
            "Yazma geride kalırsa alarm geç çalışır."),
        row("R3", 10, "Telegraf tamponladığı için kısa bir kesinti veri kaybettirmez.",
            "Bir AZ arızasında veri kaybolmamalı; Telegraf tamponladığı için birkaç dakikalık yazma kesintisi kabul edilir.",
            "Ölçümler kaybolursa bir arızanın nedeni geriye dönük bulunamaz."),
        row("R4", 16, "İki kişilik ekip 40 check'i, task'ları ve panoları taşıyacak.",
            "Var olan Flux task'ları, check'ler ve Grafana panoları değişmeden çalışmalı; disk ve sunucu işi bitmeli.",
            "Yeniden yazmak iki kişi için aylar demektir ve taşıma sırasında alarmlar eksik kalır."),
        row("R5", 16, "Fabrika gece gündüz çalışır; yük düzdür ve fatura 5 yıllık bütçeye uymalı.",
            "Düz bir yük; birkaç yüz GB veri. Fatura sabit ve öngörülebilir olmalı.",
            "Series ya da alarm başına ödenen bir modelde 12.000 series faturayı patlatır."),
    ],
    cands=["ix", "ix3", "cw"],
    scores={
        "ix": [sc(10, "Point = measurement + tag set + field'lar + timestamp (Ö1); makine başına series (Ö2). Puan kırılmadı."),
               sc(10, "range() + tag filtresi ve aggregateWindow her pano sorusunu tek sorguda verir (Ö4, Ö5). Puan kırılmadı."),
               sc(10, "Üç bucket'ın üç retention period'u vardır ve var olan downsampling task'ları özetleri yazar (Ö7). Puan kırılmadı."),
               sc(9, "40 check zamanlanmış Flux sorgularıdır ve notification endpoint'lere haber verir (Ö8). 1 puan kırıldı: check'ler değişikliğe değil zamana göre çalışır; haber check aralığı (örneğin 30 saniye) kadar gecikir."),
               sc(10, "Saniyede 1.200 point, düz ve büyümeyen bir yük, AWS'in boyutlandırma tablosunda db.influx.large'ın çok altındadır. Puan kırılmadı."),
               sc(9, "Multi-AZ standby senkron replikadır. 1 puan kırıldı: failover genellikle 60–120 saniyedir; Telegraf tamponladığı için okuma kaybolmaz, sadece gecikir."),
               sc(8, "Aynı açık kaynak API: Flux task'ları, check'ler, Telegraf ve Grafana değişmeden bağlanır. 2 puan kırıldı: instance sınıfı ve storage seçilir ve beş yıllık veri bir kez taşınır."),
               sc(8, "Instance-saat ve storage ödenir; düz yük instance-saat modeline uyar. 2 puan kırıldı: Multi-AZ standby ikinci bir instance ücretidir (kart 1, 2 ve 3 ile aynı kırılım).")],
        "ix3": [sc(10, "Aynı line protocol; makine başına series. Puan kırılmadı."),
                sc(10, "SQL'de date_bin ya da InfluxQL'de GROUP BY time pencere sorusunu tek sorguda verir. Puan kırılmadı."),
                sc(9, "Enterprise database başına retention period verir. 1 puan kırıldı: dakikalık ve saatlik özetleri bir Processing Engine plugin'i (Python) yazar; Flux task'ı yoktur."),
                sc(7, "Processing Engine zamanlanmış Python plugin'leri çalıştırır ve bir eşik hesabı yapabilir. 3 puan kırıldı: InfluxDB 2'deki gibi hazır check ve notification endpoint yoktur; \"2 dakika boyunca\" kuralı ve bildirim plugin kodudur."),
                sc(10, "Yazma ve sorgu node'ları ayrı ölçeklenir. Puan kırılmadı."),
                sc(10, "Veri S3 üzerindeki object storage'dadır ve node'lar AZ'lere dağılır. Puan kırılmadı."),
                sc(3, "Yönetilen cluster. 7 puan kırıldı: Flux InfluxDB 3'te desteklenmez; InfluxData'ya göre Flux task'ları yeniden yazılmalıdır. 40 check, task'lar ve Grafana panoları SQL ya da InfluxQL ile yeniden yazılır."),
                sc(6, "Node-saat, kullanılan GB (en az 200 GB) ve vCPU başına Enterprise lisansı ödenir. 4 puan kırıldı: iki node ve lisans tek bir Multi-AZ instance'tan pahalıdır; S3 storage'ının ucuzluğu birkaç yüz GB'ta fark yaratmaz.")],
        "cw": [sc(9, "Bir metric namespace, ad ve dimension'larla tanımlanır. 1 puan kırıldı: her makine ve ölçüm birleşimi ayrı bir metric'tir."),
               sc(9, "Her periyot için Average ve Maximum hesaplanır. 1 puan kırıldı: 10 saniyelik çözünürlük için high-resolution metric yayınlanır."),
               sc(2, "Özetleme ve silme kendiliğindendir. 8 puan kırıldı: AWS'e göre 60 saniyeden kısa periyotlu veri 3 saat, dakikalık veri 15 gün, saatlik veri 455 gün tutulur; üç kademenin üçü de karşılanmaz (14 günlük ham veri, 1 yıllık dakikalık, 5 yıllık saatlik özet), kart 1'den bir kademe fazla."),
               sc(10, "Bir alarm \"2 dakika boyunca\" kuralını periyot ve veri noktası sayısıyla ayar olarak tanımlar. Puan kırılmadı."),
               sc(10, "Yazma ve alarm değerlendirme kapasitesi servisindir. Puan kırılmadı."),
               sc(10, "Metrikler servis tarafından kalıcı saklanır. Puan kırılmadı."),
               sc(4, "Sunucu yoktur. 6 puan kırıldı: Telegraf'ın çıkışı CloudWatch'a çevrilir, 40 check makine başına alarmlara (binlerce alarm) dönüşür ve Grafana panoları yeniden yazılır."),
               sc(2, "Metric ve alarm başına ödenir. 8 puan kırıldı: 12.000 custom metric ayda yaklaşık 3.200 USD'dir (Frankfurt, ilk 10.000 için 0,30, sonrası 0,10 USD) ve buna binlerce alarm eklenir.")],
    },
    h2h={"ix3": "Columnar time series (Timestream for InfluxDB 3) ile kafa kafaya. InfluxDB 3 aynı veri modelini ve aynı line protocol'ü yazar, yazma ve sorgu node'larını ayırır ve veriyi S3'te tutar; R2 ve R3'te tam puan alır. "
                 "Ama bu kartın iki engine sorusunda geride kalır: InfluxDB 2'deki hazır check'ler ve notification endpoint'ler yoktur, \"2 dakika boyunca\" kuralı bir Python plugin'idir (AO), downsampling de plugin kodudur (YD). "
                 "Asıl kayıp R4'tedir: InfluxData'ya göre Flux InfluxDB 3'te desteklenmez; 40 check, task'lar ve panolar yeniden yazılır. Var olan kodu yeniden yazmak engine'in değil ekibin işidir, bu yüzden R4'te sayılır, R1'de değil. "
                 "Hangi koşul değişseydi Timestream for InfluxDB 3 seçilirdi: fabrika sıfırdan kurulsaydı, ekip SQL bilseydi ve series sayısı milyonlara çıksaydı; o zaman hazır check'lerin yokluğu küçük bir bedel olurdu.",
         "cw": "İzleme servisi (CloudWatch) ile kafa kafaya. CloudWatch'un alarmı bu kartın en temiz aracıdır: \"2 dakika boyunca\" bir ayardır ve kapasite ile kalıcılık servisindir (R1 · AO, R2, R3). "
               "Ama bu fabrikanın geçmişi CloudWatch'un sabit saklama kuralına sığmaz: AWS'e göre 60 saniyeden kısa periyotlu veri 3 saat, dakikalık veri 15 gün, saatlik veri 455 gün tutulur; 14 günlük ham veri ve 5 yıllık trend kaybolur (YD). "
               "Series başına fiyat 12.000 series'te ayda yaklaşık 3.200 USD'dir ve alarmlar makine başına çoğalır (R5); Telegraf çıkışı, check'ler ve panolar yeniden kurulur (R4). "
               "Hangi koşul değişseydi CloudWatch seçilirdi: fabrikada birkaç yüz series olsaydı, ham veri 3 saat yetseydi ve var olan bir InfluxDB taşınmasaydı.",
         },
    verdict="Karar: Timestream for InfluxDB {ix}, Timestream for InfluxDB 3 {ix3}, CloudWatch {cw}. Bu iş yüküne en uygun servis Timestream for InfluxDB'dir: R1'de 46'nın 44,7'sini alır ve var olan Flux task'ları, check'ler ve panolar değişmeden taşınır. "
            "Timestream for InfluxDB seçtiğimizde artımız: disk ve sunucu işi biter, beş yıllık üç kademeli saklama aynen çalışır, 40 check ilk gün çalışır. "
            "Eksimiz: instance sınıfını ve storage'ı seçeriz, beş yıllık veriyi bir kez taşırız ve check'ler zaman aralığıyla çalıştığı için bir alarmın 30 saniyeye kadar gecikmesini kabul ederiz. "
            "Bir koşul değişseydi: fabrika sıfırdan kurulsaydı ve ekip SQL bilseydi Timestream for InfluxDB 3 öne geçerdi."))

# ------------------------------------------------------------------ 6. financial tick data
INFLUXDB_W.append(wusecase("ticks", 6, sim="w_ticks",
    title="Borsa tick verisi: 3.000 enstrüman, 3 yıllık geçmiş",
    key="Measurement: trade. Tag: symbol (3.000 değer), venue. Field'lar: price, qty. Timestamp: nanosaniye. Referans table: instruments (sektör, lot).",
    story="Bir aracı kurumun veri ekibi 3.000 enstrümanın her işlemini (tick) saklar. Gün içinde saniyede ortalama 3.000, açılışta 30.000 tick gelir; günde yaklaşık 80 milyon tick. "
          "Trader ekranı son 5 dakikanın 1 dakikalık OHLC (açılış, en yüksek, en düşük, kapanış) değerlerini saniyede bir yeniler. Analistler sektöre göre VWAP (hacim ağırlıklı ortalama fiyat) "
          "hesaplar; bunun için tick'ler enstrüman referans table'ıyla join'lenir. Model ekibi geriye dönük testlerde 3 yıllık tick'leri tarar. Mevzuat gereği tick'ler 3 yıl saklanır, kaybolmamalıdır. "
          "Ekip SQL biliyor; borsa beslemesi bir saatlik tekrar oynatma sunar.",
    wnote="R1 toplam 44: SQL ile join'li pencere soruları (EY 14) ve 3 yıllık, yaklaşık 60 milyar tick'in saklanması (DA 14) bu iş yükünün kendisidir; VM 8 ve YD 8 tamamlar. "
          "R2 16 ve R5 16: açılışın 10 katlık sıçraması ve 3 yıllık storage'ın faturası; R3 12, çünkü mevzuat kaybı kabul etmez.",
    rows=[
        row("EY", 14, "Trader ekranı, VWAP raporu ve geriye dönük testler her gün bu soruları sorar.",
            "\"Bu sembolün son 5 dakikası, 1 dakikalık OHLC\" (trader ekranı en yeni tick'i bir saniye içinde görmeli) ve \"sektöre göre günlük VWAP\" (instruments table'ı ile join); analistler soruyu SQL ile yazar.",
            "Join ve pencere uygulamada yapılırsa her rapor milyonlarca tick'i çeker ve analist bekler."),
        row("DA", 14, "3 yılda yaklaşık 60 milyar tick birikir; engine'in saklama biçimi faturanın ve tarama süresinin kaynağıdır.",
            "3 yıllık tick'ler kolon kolon sıkıştırılmış ve zamana göre düzenli saklanmalı; geriye dönük test bir yılın price ve qty kolonlarını taramalı.",
            "Geçmiş hızlı ve pahalı diskte durursa fatura her ay büyür; tarama bütün kolonları okursa testler saatler sürer."),
        row("VM", 8, "Bir tick zaman, iki etiket ve iki sayıdır.",
            "Tick = nanosaniye timestamp + etiketler (symbol, venue) + price ve qty.",
            "Model tick'e uymazsa etiketler her tick'te tekrar saklanır."),
        row("YD", 8, "3 yıldan eski tick'ler mevzuat süresinden sonra gider.",
            "3 yıldan eski tick'ler kendiliğinden silinmeli.",
            "Silme unutulursa storage her yıl yüzde 33 büyür."),
    ] + [
        row("R2", 16, "Açılışın ilk dakikalarında yük 10 katına çıkar.",
            "Saniyede ortalama 3.000, açılışta 30.000 tick; trader ekranı saniyede bir yenilenir.",
            "Açılışta yazma geride kalırsa trader ekranı eski fiyat gösterir."),
        row("R3", 12, "Mevzuat tick'lerin kaybını kabul etmez.",
            "Bir AZ arızasında tick kaybolmamalı; besleme bir saati tekrar oynatabilir ama 3 yıllık geçmiş geri gelmez.",
            "Eksik tick bir denetimde ceza demektir."),
        row("R4", 12, "Ekip SQL biliyor ve küçük; yeni bir dil bir maliyettir.",
            "Analistler SQL kullanmalı; sunucu ve yama işi en az olmalı.",
            "Yeni bir sorgu dili analistleri veri ekibine bağımlı yapar."),
        row("R5", 16, "3 yıllık geçmişin storage faturası bu iş yükünün en büyük kalemidir.",
            "3 yılda birkaç TB sıkıştırılmış veri; storage GB başına ucuz olmalı, compute gün içi yüke uymalı.",
            "Geçmiş SSD fiyatıyla ödenirse fatura her ay büyür."),
    ],
    cands=["ix3", "rs", "ix"],
    scores={
        "ix3": [sc(10, "SQL (DataFusion) join, date_bin ve window function'larla OHLC ve VWAP'ı tek sorguda verir; InfluxQL de vardır. Puan kırılmadı."),
                sc(10, "Parquet dosyaları kolon kolon sıkıştırılır ve S3'te durur; Enterprise'ın compactor'ı eski dosyaları birleştirir, sorgu sadece istediği kolonları okur. Puan kırılmadı."),
                sc(10, "Aynı line protocol, nanosaniye timestamp. Puan kırılmadı."),
                sc(10, "Enterprise database başına retention period verir. Puan kırılmadı."),
                sc(9, "Yazma node'ları 4'e kadar çoğaltılır. 1 puan kırıldı: yazma node'larının sınıfı açılış tepesine göre seçilir ve gün içinde boşta durur."),
                sc(10, "Veri S3 üzerindeki object storage'dadır (AWS'e göre 11 dokuz dayanıklılık); node'lar AZ'lere dağılır. Puan kırılmadı."),
                sc(7, "Yönetilen cluster ve SQL. 3 puan kırıldı: node rolleri, node sınıfı ve parameter group ekibin seçimidir ve servis ekip için yenidir."),
                sc(8, "Kullanılan GB ödenir (Frankfurt 0,0245 USD/GB-ay, en az 200 GB). 2 puan kırıldı: node'lar ve vCPU başına Enterprise lisansı gece de ödenir.")],
        "ix": [sc(6, "aggregateWindow OHLC'yi verir (Ö5); join() ve pivot() ile referans table'ına bağlanır. 4 puan kırıldı: InfluxDB 2'nin SQL'i yoktur; sektöre göre VWAP Flux'ta join, map ve pivot zinciridir ve InfluxQL'de join yoktur."),
               sc(5, "TSM dosyaları series'i zaman sırasıyla sıkıştırır (Ö3). 5 puan kırıldı: TSM dosyaları yerel diskte series series durur, kolon bazlı ve kolon seçen bir tarama yoktur; 3 yıllık geriye dönük test binlerce shard group'u açar ve uzun aralıklı sorgular belleğe yüklenir."),
               sc(10, "Point = measurement + tag set + field'lar + timestamp, nanosaniye hassasiyetiyle (Ö1, Ö2). Puan kırılmadı."),
               sc(10, "Bucket'ın 3 yıllık retention period'u eski shard group'ları düşürür (Ö7). Puan kırılmadı."),
               sc(8, "Saniyede 30.000 point AWS'in boyutlandırma tablosunda db.influx.large'ın sınırları içindedir. 2 puan kırıldı: bütün yazmalar tek instance'tan geçer ve açılış tepesi aynı instance'ta sorgularla yarışır."),
               sc(7, "Multi-AZ standby senkron replikadır; AWS bloguna göre failover veri kaybı olmadan yapılır. 3 puan kırıldı: failover'ın 60–120 saniyesinde yazmalar başarısız olur ve besleme tekrar oynatılır; mevzuat kaydı için kullanıcının kendi başlattığı bir geri yükleme yoktur (iç yedekler 24 saat, AWS Support üzerinden)."),
               sc(5, "Yönetilen instance. 5 puan kırıldı: instance ve storage boyutlandırma ekibin işidir ve analistler için Flux yeni bir dildir."),
               sc(4, "Instance-saat ve ayrılmış SSD storage ödenir. 6 puan kırıldı: 3 yıllık geçmiş Multi-AZ Influx IO Included storage'ında GB başına 0,238–0,834 USD/ay öder; S3 tabanlı storage 0,0245 USD'dir.")],
        "rs": [sc(6, "SQL join, date_trunc ve window function'lar OHLC ve VWAP'ı verir. 4 puan kırıldı: tick'ler streaming ingestion ile bir materialized view'a gelir ve trader ekranı en yeni tick'i ancak bir sonraki yenilemeden sonra görür (tazelik gecikmesi, sadece bu satırda sayılır); boş dakikalar için ayrıca bir zaman table'ı join'lenir."),
               sc(9, "Kolon bazlı, sıkıştırılmış bloklar ve zamana göre sort key; geriye dönük test sadece price ve qty kolonlarını okur. 1 puan kırıldı: akıştan gelen küçük yazmalar sıralanmamış bölge bırakır ve arka plan sıralaması bekler."),
               sc(9, "Bir tick bir row'dur. 1 puan kırıldı: engine'de series kavramı yoktur; symbol ve venue her row'da tekrar durur (kolon sıkıştırması bunu küçültür)."),
               sc(6, "Eski tick'ler tarih aralığıyla silinir. 4 puan kırıldı: süre sonu yoktur; silme zamanlanmış bir DELETE işidir ve silinen row'lar arka plandaki VACUUM'a kadar yer tutar (Redshift sayfasındaki kartlarla aynı kırılım)."),
               sc(9, "Streaming ingestion Kinesis'ten saniyede 30.000 tick'i alır; Serverless kapasite yükle büyür. 1 puan kırıldı: açılış tepesi için base RPU önceden yükseltilir (önceden eklenen sabit kapasite her serviste 1 puandır); tazelik R1.1'de sayıldı."),
               sc(10, "Managed storage ve recovery point'ler. Puan kırılmadı."),
               sc(8, "Analistler bildiği SQL'i kullanır. 2 puan kırıldı: Kinesis akışı ayrıca işletilir (1) ve materialized view'ların yenileme planı ile workgroup kapasitesi ekibin işidir (1)."),
               sc(7, "Managed storage GB başına ucuzdur. 3 puan kırıldı: saniyede bir yenilenen ekran Serverless compute'u gün boyunca açık tutar ve RPU-saat olarak ödenir.")],
    },
    h2h={"ix": "Time series (Timestream for InfluxDB) ile kafa kafaya. İki InfluxDB aynı tick'i aynı line protocol ile yazar ve ikisi de 3 yıllık retention'ı bir ayarla yapar; VM ve YD'de eşittir. "
                "Fark engine'in kendisindedir. InfluxDB 2'nin SQL'i yoktur: sektöre göre VWAP Flux'ta join ve pivot zinciridir (EY). TSM dosyaları instance'ın SSD'sindedir; 3 yıllık geriye dönük test binlerce shard group'u açar (DA). "
                "InfluxDB 3 aynı veriyi Parquet olarak S3'te tutar ve SQL ile sorar. Servis tasarımı farkı büyütür: 3 yıllık geçmiş SSD fiyatıyla ödenir (R5) ve analistler için Flux yeni bir dildir (R4). "
                "Hangi koşul değişseydi Timestream for InfluxDB seçilirdi: tick'ler sadece 30 gün tutulsaydı, sorular join'siz pencere soruları olsaydı ve ekip zaten Flux kullansaydı; o zaman küçük bir instance ve lisanssız fiyat öne geçerdi.",
         "rs": "Data warehouse (Redshift) ile kafa kafaya. Redshift analistin sorusunda güçlüdür: SQL join, window function, kolon bazlı sıkıştırma ve sort key 3 yıllık geriye dönük testi iyi karşılar (EY, DA). "
               "Ama bu kartın iki şeyi ona uymaz. Trader ekranı en yeni tick'i bir saniye içinde ister; tick'ler Kinesis'ten streaming ingestion ile bir materialized view'a gelir ve ekran onları ancak bir sonraki yenilemeden sonra görür (EY). Yenileme gün boyunca çalıştığı için compute da gün boyunca ödenir (R5). Warehouse'ta retention yoktur; 3 yıldan eski tick'ler DELETE ve VACUUM ister (YD). "
               "Hangi koşul değişseydi Redshift seçilirdi: canlı ekran olmasaydı ve tick'ler gün sonunda dosya olarak yüklenseydi; o zaman doğru mimari ikisinin birlikte çalışmasıdır: canlı pencere bir time series engine'inde, geçmiş ve VWAP raporu Redshift'te.",
         },
    verdict="Karar: Timestream for InfluxDB 3 {ix3}, Redshift {rs}, Timestream for InfluxDB {ix}. Bu iş yüküne en uygun servis Timestream for InfluxDB 3'tür: SQL ile join'li pencere soruları ve 3 yıllık geçmişin S3'te Parquet olarak saklanması engine'in kendisidir. "
            "Timestream for InfluxDB bu kartta net kaybeder ve kaybı R1'den gelir: SQL'i yoktur ve uzun geçmiş instance'ın SSD'sinde durur. "
            "Yine de Timestream for InfluxDB seçersek artımız: tek bir instance, lisans yok, açılış tepesi bir instance'ın sınırları içinde. "
            "Eksimiz: VWAP'ı Flux'ta join ve pivot ile yazarız, geçmişi kısa tutup eski tick'leri S3'e aktarırız ve geriye dönük testleri başka bir engine'de (Athena ya da Redshift) çalıştırırız. "
            "Bir koşul değişseydi: tick'ler 30 gün tutulsaydı ve sorular join'siz olsaydı Timestream for InfluxDB öne geçerdi."))

# ------------------------------------------------------------------ 7. energy meter billing analytics
INFLUXDB_W.append(wusecase("energy", 7,
    title="Akıllı sayaç faturalama analitiği: 2 milyon sayaç",
    key="Gecelik dosya: meter_id, ts (15 dakika), kwh. Tarife table'ı: zaman dilimi, birim fiyat. Rapor: hane ve ay başına tarife dilimine göre tüketim.",
    story="Bir elektrik dağıtım şirketinin 2 milyon akıllı sayacı 15 dakikada bir tüketim ölçer; sayaç merkezi sistemi okumaları her gece S3'e bir CSV dosyası olarak bırakır: "
          "günde 192 milyon okuma, 3 yılda yaklaşık 210 milyar. Faturalama ekibi her ay hane başına tüketimi tarife dilimlerine (gündüz, puant, gece) göre hesaplar; bunun için okumalar "
          "tarife ve müşteri table'larıyla join'lenir. Bölge yöneticileri ilçe ve ay bazında raporlar ister, düzenleyici kurum 3 yıllık geçmişi denetler. Sayaç sistemi bazen bir günü düzeltilmiş "
          "bir dosyayla yeniden gönderir. Canlı bir ekran yoktur; her soru en az bir günlük veriye bakar. Ekip altı analistten oluşur ve SQL ile bir BI aracı kullanır.",
    wnote="R1 toplam 46: tarife ve müşteri table'larıyla join'li toplam (EY 16) ve 210 milyar okumanın taranması (DA 12) bu iş yükünün kendisidir; gecelik dosya ve düzeltme dosyası (OY 10) ile okumanın şekli (VM 8) tamamlar. "
          "R5 16 ve R4 14: aylık fatura dönemi dışında yük düşüktür ve altı analist SQL ile çalışır.",
    rows=[
        row("EY", 16, "Her fatura dönemi ve her rapor bu sorudur.",
            "\"Hane ve ay başına tarife dilimine göre kWh\" ve \"ilçe ve ay başına toplam\": okumalar tarife ve müşteri table'larıyla join'lenir ve gruplanır; yeni rapor yeni bir SQL cümlesidir.",
            "Join ve gruplama uygulamaya kalırsa fatura dönemi günler sürer."),
        row("DA", 12, "210 milyar okuma birkaç TB'tır; tarama birkaç kolon okur.",
            "Okumalar kolon kolon sıkıştırılmış saklanmalı; bir aylık rapor sadece meter_id, ts ve kwh kolonlarını ve sadece o ayın bloklarını okumalı.",
            "Tarama bütün kolonları ya da bütün geçmişi okursa ay sonu raporu saatler sürer."),
        row("OY", 10, "Veri gece bir dosya olarak gelir ve bazen düzeltilmiş olarak yeniden gelir.",
            "Gecelik CSV dosyası toplu yüklenmeli; düzeltilmiş bir günün dosyası o günün okumalarının yerine geçmeli.",
            "Toplu yükleme yoksa 192 milyon okuma tek tek yazılır; düzeltme yerine geçmezse fatura yanlış çıkar."),
        row("VM", 8, "Bir okuma sayaç, zaman ve bir sayıdır; 2 milyon sayaç vardır.",
            "Okuma = meter_id + ts + kwh; 2 milyon farklı sayaç.",
            "Sayaç id'si bir etiket olarak her series'i tanımlarsa 2 milyon series doğar."),
    ] + [
        row("R2", 14, "Yük ay sonunda birkaç gün yoğun, diğer günler düşüktür.",
            "Gecelik yükleme 192 milyon okuma; ay sonunda birkaç gün altı analistin ağır sorguları.",
            "Ay sonu sorguları geride kalırsa faturalar gecikir."),
        row("R3", 10, "Ham dosyalar S3'te zaten durur; database bir kopyadır.",
            "Database kaybolursa S3'teki dosyalardan yeniden yüklenebilir; fatura dönemi ise kaybolmamalı.",
            "Fatura dönemi ortasında kayıp, yeniden yükleme süresi kadar gecikmedir."),
        row("R4", 14, "Altı analist SQL ve BI aracıyla çalışır.",
            "Analistler SQL ile yeni raporlar yazmalı; BI aracı doğrudan bağlanmalı; sunucu işi olmamalı.",
            "Analistler yeni bir dil öğrenmek zorunda kalırsa her rapor veri ekibini bekler."),
        row("R5", 16, "Yük ayda birkaç gün yoğun; geri kalan zamanda database boş durur.",
            "Fatura dönemi dışında compute ödenmemeli; birkaç TB storage ucuz olmalı.",
            "Ay boyunca çalışan bir cluster ayın çoğunda boşa ödenir."),
    ],
    cands=["rs", "ix3", "ix"],
    scores={
        "rs": [sc(10, "SQL join, GROUP BY ve window function'lar her raporu bir cümle olarak verir. Puan kırılmadı."),
               sc(10, "Kolon bazlı sıkıştırılmış bloklar, ts sort key'i ve zone map'ler bir ayın sadece üç kolonunu okur. Puan kırılmadı."),
               sc(9, "COPY gecelik dosyayı slice'lara paralel yükler. 1 puan kırıldı: düzeltilmiş bir gün, o günün row'larını DELETE edip yeniden yükleyerek yerine konur ve arkasından VACUUM çalışır."),
               sc(10, "Bir okuma bir row'dur; 2 milyon sayaç bir kolonun değerleridir ve series sayısı diye bir sınır yoktur. Puan kırılmadı."),
               sc(10, "Serverless kapasite ay sonu sorgularına göre artar ve boş günlerde düşer. Puan kırılmadı: base ve en fazla RPU ayarı R4'te sayıldı."),
               sc(10, "Managed storage ve recovery point'ler; ham dosyalar S3'te de durur. Puan kırılmadı."),
               sc(9, "Analistler SQL ve BI aracıyla doğrudan çalışır, sunucu yoktur. 1 puan kırıldı: workgroup'un base ve en fazla RPU ayarı ve COPY zamanlaması ekibin işidir."),
               sc(9, "Sorgu çalıştığı saniye ödenir; boş günlerde compute ödenmez. 1 puan kırıldı: gecelik yükleme her gün compute kullanır.")],
        "ix3": [sc(8, "SQL (DataFusion) join ve GROUP BY ile raporu verir. 2 puan kırıldı: engine bir time series engine'idir, MPP warehouse değildir; 2 milyon haneyi tarife table'ıyla join'leyen ay sonu sorgusu sorgu node'unun belleğine yüklenir."),
                sc(8, "Parquet dosyaları kolon kolon sıkıştırılır ve sorgu sadece istediği kolonları okur. 2 puan kırıldı: dosyalar zamana göre düzenlidir; bir hane ya da ilçe filtresi bütün ayın dosyalarını okur."),
                sc(6, "Line protocol ile toplu yazma; aynı series ve timestamp ile yazılan okuma eskisinin yerine geçer. 4 puan kırıldı: CSV dosyasını S3'ten doğrudan yükleyen bir komut yoktur; gecelik dosya line protocol'e çevrilip API ile yazılır."),
                sc(9, "Aynı veri modeli; AWS'e göre InfluxDB 3 high-cardinality veride daha iyi performans verir. 1 puan kırıldı: meter_id bir tag olarak 2 milyon series tanımlar ve series başına metadata tutulur."),
                sc(9, "Sorgu node'ları eklenebilir. 1 puan kırıldı: ay sonu için node'lar önceden eklenir (önceden eklenen sabit kapasite her serviste 1 puandır); node planı R4'te sayıldı."),
                sc(10, "Veri S3 üzerindeki object storage'dadır. Puan kırılmadı."),
                sc(7, "Analistler SQL kullanır; BI aracı Flight SQL (Arrow tabanlı SQL bağlantı protokolü) ya da InfluxQL ile bağlanır. 3 puan kırıldı: cluster ve node rolleri ekibin işidir ve gecelik dönüştürme işi ekip tarafından işletilir."),
                sc(6, "Kullanılan GB ucuzdur (0,0245 USD/GB-ay). 4 puan kırıldı: node'lar ve vCPU başına Enterprise lisansı ay boyunca ödenir; yük ayda birkaç gündür.")],
        "ix": [sc(4, "aggregateWindow aylık toplamı verir (Ö5); join() referans table'ına bağlar. 6 puan kırıldı: SQL yoktur; tarife dilimlerine göre join ve gruplama Flux'ta uzun bir zincirdir ve her yeni rapor bir Flux programıdır."),
               sc(4, "TSM dosyaları series'i sıkıştırır (Ö3). 6 puan kırıldı: dosyalar series'e göre düzenlidir, bir ilçenin bir ayı her sayacın series'ini ayrı açar ve 3 yıllık tarama binlerce shard group'a dokunur (series sayısının kendisi R1.4'te sayıldı)."),
               sc(5, "Point'ler toplu yazılır; aynı series ve timestamp ile yazılan point eskisinin yerine geçer (Ö1). 5 puan kırıldı: CSV dosyasını yükleyen bir komut yoktur; gecelik 192 milyon okuma line protocol'e çevrilip API ile batch'ler hâlinde yazılır."),
               sc(6, "Point = measurement + tag set + field + timestamp (Ö2). 4 puan kırıldı: meter_id tag'i 2 milyon series doğurur ve engine her series için bellekte ve index'te bir kayıt tutar (cardinality, bu kartta sadece bu satırda sayılır)."),
               sc(6, "Tek instance gecelik yüklemeyi alır. 4 puan kırıldı: ay sonu sorguları ve gecelik yazma aynı instance'ta yarışır; sorgular yükleme bitene kadar yavaşlar (instance seçimi R4'te sayıldı)."),
               sc(8, "Multi-AZ standby; ham dosyalar S3'te durur. 2 puan kırıldı: failover sırasında yükleme durur ve yeniden başlatılır."),
               sc(4, "Yönetilen instance. 6 puan kırıldı: analistler SQL biliyor, Flux yeni bir dildir; BI aracı doğrudan bağlanamaz ve büyük bir instance boyutlandırılır."),
               sc(3, "Instance-saat ve ayrılmış storage ödenir. 7 puan kırıldı: ödeme birimi bu yüke uymaz: yük ayda birkaç gündür ama instance-saat gece gündüz ödenir (Multi-AZ db.influx.4xlarge ayda yaklaşık 3.370 USD) ve birkaç TB 12K IOPS storage GB başına 0,834 USD/ay ile önceden ayrılır.")],
    },
    h2h={"ix3": "Columnar time series (Timestream for InfluxDB 3) ile kafa kafaya. InfluxDB 3 bu kartın verisini taşıyabilir: SQL konuşur, Parquet ile kolon kolon sıkıştırır ve 2 milyon sayacı InfluxDB 2'den çok daha rahat taşır. "
                 "Ama iş yükü bir time series işi değil, bir rapor işidir. Soru canlı bir pencere değil, tarife ve müşteri table'larıyla join'li aylık bir toplamdır; ay sonu sorgusu tek bir sorgu node'unun belleğine yüklenir, Redshift ise işi slice'lara böler (EY). "
                 "Veri gece bir CSV dosyası olarak gelir; COPY'nin karşılığı yoktur, dosya line protocol'e çevrilir (OY). Yük ayda birkaç gündür; node'lar ve lisans ay boyunca ödenir (R5). "
                 "Hangi koşul değişseydi Timestream for InfluxDB 3 seçilirdi: okumalar canlı bir ekrana saniyeler içinde gelseydi (şebeke izleme) ve raporlar join'siz olsaydı.",
         "ix": "Time series (Timestream for InfluxDB) ile kafa kafaya. Bu kart Timestream for InfluxDB'nin net kaybettiği kartlardan biridir ve kayıp R1'dedir. "
               "SQL yoktur; tarife dilimlerine göre join'li rapor Flux'ta uzun bir programdır (EY). meter_id tag'i 2 milyon series doğurur ve series index'i büyür; uzun aralıklı tarama binlerce shard group açar (VM, DA). "
               "CSV dosyasını yükleyen bir komut yoktur (OY). Servis tasarımı da uymaz: ayda birkaç gün çalışan bir yük için büyük bir Multi-AZ instance ve 12K IOPS storage gece gündüz ödenir (R5); analistler Flux öğrenir (R4). "
               "Hangi koşul değişseydi Timestream for InfluxDB seçilirdi: sayaç sayısı birkaç bin olsaydı, okumalar canlı gelseydi ve soru \"son 24 saatin 15 dakikalık tüketimi\" gibi join'siz bir pencere olsaydı. O zaman doğru mimari ikisinin birlikte çalışmasıdır: canlı şebeke ekranı bir time series engine'inde, faturalama Redshift'te.",
         },
    verdict="Karar: Redshift {rs}, Timestream for InfluxDB 3 {ix3}, Timestream for InfluxDB {ix}. Bu iş yüküne en uygun servis Redshift'tir: gecelik dosya, join'li aylık toplam ve ayda birkaç günlük yük bir data warehouse işidir. "
            "Timestream for InfluxDB bu kartta net kaybeder; kaybın çoğu R1'dedir. "
            "Yine de Timestream for InfluxDB seçersek artımız: okumaların kendisi kompakt bir series modelinde durur ve canlı bir pencere istenirse hazırdır. "
            "Eksimiz: sayaç id'sini tag'e koyduğumuz için 2 milyon series taşırız; raporları Flux'ta yazarız; gecelik dosyayı line protocol'e çeviririz ve büyük bir instance'ı ay boyunca öderiz. "
            "Bir koşul değişseydi: okumalar canlı bir şebeke ekranına gitseydi bir time series engine'i kartın ikinci parçası olurdu."))

# ------------------------------------------------------------------ 8. anomaly detection (= OpenSearch card 10)
_s = _src("opensearch", "anomaly")
INFLUXDB_W.append(wusecase("anomaly", 8,
    title=_s["title"][1], key=_s["key"][1], story=_s["story"][1], wnote=_s["wnote"][1], rows=_rows(_s),
    cands=["os", "ix", "cw"],
    scores={
        "os": _same(_s, "os"),
        "ix": _same(_s, "ix", [
            "Task'lar ve check'ler zamanlanmış Flux sorgularıdır ve bir eşik hesabı yapabilir (Ö8). 6 puan kırıldı: engine'de normali öğrenen bir tespit aracı yoktur; mevsimsellik ve eşikler ekibin yazdığı istatistik koduyla hesaplanır.",
            "Kategori ve şehir tag'leri ile 5 dakikalık aggregateWindow kırılım ve pencereyi tek bir sorguda verir (Ö2, Ö5). Puan kırılmadı.",
            "Bir point tag'ler ve field'larla saklanır; sayılar series'lerden hesaplanır (Ö1). 3 puan kırıldı: olay bir sipariş kaydı olarak değil bir ölçüm olarak saklanır; analistin bir sapmanın siparişlerine inişi başka bir sistemdedir.",
            "Saniyede 50 point bir instance için küçüktür. 1 puan kırıldı: bütün yazmalar tek bir instance'tan geçer.",
            "Multi-AZ standby. 2 puan kırıldı: failover sırasında birkaç dakikalık boşluk olabilir ve veri Aurora'dan yeniden yüklenir.",
            "Yönetilen instance. 5 puan kırıldı: yeni bir sistemdir; instance sınıfı, Aurora'dan akış ve bildirim kanalı ekibin işidir. Tespit kodu R1.1'de sayıldı.",
            "Instance-saat ve storage ödenir; kırılım sayısı faturayı doğrudan büyütmez (Ö2). 2 puan kırıldı: Multi-AZ standby ikinci bir instance ücretidir; db.influx.medium Multi-AZ ayda yaklaşık 211 USD (Frankfurt, Price List API, 2026-10-31)."]),
        "cw": _same(_s, "cw")},
    h2h={"ix": "Time series (Timestream for InfluxDB) ile kafa kafaya. Timestream for InfluxDB'nin artısı pencere sorusudur: kategori ve şehir tag'leriyle 5 dakikalık toplam tek bir sorgudur (Ö5) ve series sayısı faturayı büyütmez (R5); 2. kartta bu yüzden kazanır. "
                "Ama bu kartın işi \"normal\"i öğrenmektir ve engine'de bunu yapan bir araç yoktur: check'ler ve task'lar zamanlanmış sorgulardır (Ö8), gece düşüşünü ve öğle tepesini öğrenen istatistik ekibin yazacağı koddur (R1.1'de 4). "
                "Yeni bir sistem olarak instance, Aurora'dan akış ve bildirim de ekibin işidir (R4'te 5). Olaylar bir ölçüm olarak saklandığı için analist sapmanın siparişlerine başka bir sistemde iner. "
                "Hangi koşul değişseydi Timestream for InfluxDB seçilirdi: tek bir koşul yetmez. Kırılımlar sabit eşiklerle izlenebilseydi (\"saatte 10 siparişin altı\") R1.1 bir check olurdu (kabaca 9) ve olaylar zaten InfluxDB'ye akıyor olsaydı R4 yükselirdi; ikisi birlikte farkı birkaç puana indirir.",
         "cw": _strip(_s["h2h"]["cw"][1])},
    verdict="Karar: OpenSearch {os}, Timestream for InfluxDB {ix}, CloudWatch {cw}. Kararı R1 · AO verir: kırılım başına normali öğrenen bir detector (Random Cut Forest) ve Alerting OpenSearch engine'inin içindedir ve olaylar zaten domain'dedir. "
            "Bu kart OpenSearch sayfasının 10. kartıyla aynı iş yüküdür ve aynı puanları taşır; Timestream for InfluxDB burada net kaybeder. "
            "Yine de Timestream for InfluxDB seçersek artımız: 405 kırılımın 5 dakikalık toplamı tek bir sorgudur ve fatura kırılım sayısıyla büyümez. "
            "Eksimiz: normali öğrenen istatistiği kendimiz yazarız (örneğin geçen haftanın aynı saatiyle karşılaştıran bir task), Aurora'dan akışı kurarız ve analistin olaylara inişi için ikinci bir sistem tutarız. "
            "Bir koşul değişseydi: kırılımlar sabit eşiklerle izlenebilseydi Timestream for InfluxDB öne geçerdi."))

# ------------------------------------------------------------------ 9. last state of IoT devices (= DynamoDB card 5)
_s = _src("dynamodb", "iot")
INFLUXDB_W.append(wusecase("laststate", 9, sim="w_laststate",
    title=_s["title"][1], key=_s["key"][1], story=_s["story"][1], wnote=_s["wnote"][1], rows=_rows(_s),
    cands=["ddb", "ks", "ix"],
    scores={
        "ddb": _same(_s, "ddb"), "ks": _same(_s, "ks"),
        "ix": _same(_s, "ix", [
            "Son durum, cihaz tag'ine göre last() ile sorgulanır (Ö6). 2 puan kırıldı: bu bir key okuması değil, cihazın series'i üzerinde bir sorgudur.",
            "Engine her mesajı series'in sonuna yeni bir point olarak ekler (Ö1); \"son durum\" en yeni point'tir. 6 puan kırıldı: üzerine yazma yoktur (sadece aynı timestamp'li point'in yerine geçme), series sürekli büyür ve bir retention politikası gerekir.",
            "Alarm bir check ile zamanlanmış sorgularla yapılır (Ö8). 5 puan kırıldı: değişiklik akışı yoktur; alarm sorgu aralığı kadar gecikir.",
            "Güçlü bir instance saniyede 65.000 point'i alabilir. 5 puan kırıldı: bütün yazma tek instance'tan geçer; 2 milyon cihaz tag olursa 2 milyon series demektir (Ö2) ve AWS'in örneğine göre bu yük 4xlarge sınıfı ister (boyutlandırma R4'te).",
            "Multi-AZ seçeneği bir standby tutar. 3 puan kırıldı: standby'a geçişte (genellikle 60–120 saniye) kısa bir kesinti olur.",
            "Yönetilen instance. 5 puan kırıldı: instance ve storage boyutlandırma ekibin işidir ve Flux/InfluxQL yeni bir dildir.",
            "Instance saat başına ve storage başına ödenir. 5 puan kırıldı: ödeme birimi yalnız son değer isteyen bir işe uymaz: büyük bir instance gece gündüz ve geçmiş için ayrılmış storage önceden ödenir (series'in büyümesi R1.2'de sayıldı)."])},
    h2h={"ks": _strip(_s["h2h"]["ks"][1]),
         "ix": "Time series (Timestream for InfluxDB) ile kafa kafaya. Bu kart Timestream for InfluxDB'nin en net kaybıdır ve nedeni engine'in doğasıdır. "
               "\"Son durum\" bir üzerine yazma iş yüküdür; InfluxDB her mesajı series'in sonuna yeni bir point olarak ekler (Ö1). Son değer her seferinde bir sorgudur (Ö6), series sürekli büyür ve bir retention gerekir; değişiklik akışı olmadığı için alarm zamanlanmış bir check'tir ve gecikir (Ö8). "
               "Saniyede 65.000 yazma tek bir instance'ın sınıfıyla sınırlıdır (R2) ve ekip boyutlandırır (R4). "
               "Hikâyede geçmiş değerler zaten ayrı bir time series sistemine gider; InfluxDB orası için doğru adaydır. "
               "Hangi koşul değişseydi Timestream for InfluxDB seçilirdi: panel son değerle birlikte son bir saatin eğrisini de gösterseydi ve iki iş tek bir sistemde birleştirilmek istenseydi; o zaman bile en dürüst cevap ikisinin birlikte çalışmasıdır.",
         },
    verdict="Karar: DynamoDB {ddb}, Keyspaces {ks}, Timestream for InfluxDB {ix}. Bu iş yüküne en uygun servis DynamoDB'dir; Timestream for InfluxDB üçüncüdür ve R1'in 45 puanının 23,5'ini alır. "
            "Bu kart DynamoDB sayfasının 5. kartıyla aynı iş yüküdür ve aynı puanları taşır. "
            "Yine de Timestream for InfluxDB seçersek artımız: son değer ve geçmiş aynı series'tedir; panel bir cihazın son bir saatini de çizebilir. "
            "Eksimiz: son değeri her tıklamada last() ile sorarız, series'i bir retention ile sınırlarız, alarmı bir check aralığıyla geciktiririz ve saniyede 65.000 yazma için büyük bir instance seçer ve öderiz. "
            "Bir koşul değişseydi: panel son bir saatin eğrisini de isteseydi doğru mimari ikisinin birlikte çalışmasıdır: son durum DynamoDB'de, geçmiş Timestream for InfluxDB'de."))

# ------------------------------------------------------------------ 10. real-time counters (= ElastiCache card 5)
_s = _src("elasticache", "counters")
INFLUXDB_W.append(wusecase("counters", 10,
    title=_s["title"][1], key=_s["key"][1], story=_s["story"][1], wnote=_s["wnote"][1], rows=_rows(_s),
    cands=["ec", "ddb", "ix"],
    scores={
        "ec": _same(_s, "ec"), "ddb": _same(_s, "ddb"),
        "ix": _same(_s, "ix", [
            "Her olay bir point olarak yazılır (Ö1) ve sayı pencere toplamıyla hesaplanır (Ö5). 4 puan kırıldı: engine artırmaz, ekler; saniyede 50.000 point saklanır ve sayı her okumada yeniden toplanır.",
            "Tekil ziyaretçi bir pencerede distinct sayımıdır. 6 puan kırıldı: ziyaretçi id'si tag olursa series sayısı (cardinality, Ö2) patlar, field olursa her okumada bütün point'ler taranır; yaklaşık sayım için hazır bir yapı yoktur.",
            "Ürüne göre saatlik pencere toplamı engine'in doğal sorusudur (Ö5). 2 puan kırıldı: \"ilk 20\" her 2 saniyede bir gruplama ve sıralama sorgusudur.",
            "Retention period eski point'leri kendisi siler; downsampling task'ları saatlik özetleri tutar (Ö7). Puan kırılmadı.",
            "Engine saniyede on binlerce point yazmayı taşıyabilir. 4 puan kırıldı: kampanya tepesinde 50.000 point/saniye yazma ile her 2 saniyede bir saatlik toplam aynı makinede yarışır ve ekranın sorgu süresi uzar (boyutlandırma R4'te sayıldı).",
            "Multi-AZ instance seçeneği vardır. 1 puan kırıldı: standby seçilmezse bir arıza son point'leri götürebilir; bu kartta kayıp kabul edilir.",
            "Yönetilen instance. 5 puan kırıldı: ekip için yeni bir sistem, yeni bir sorgu dili (Flux ya da InfluxQL) ve instance boyutlandırma; analist yine Redshift'te çalışır.",
            "Instance saat başına ödenir. 4 puan kırıldı: instance kampanya akşamı için boyutlanır ve gece de çalışır."])},
    h2h={"ddb": _strip(_s["h2h"]["ddb"][1]),
         "ix": "Time series (Timestream for InfluxDB) ile kafa kafaya. Timestream for InfluxDB zaman pencereleri ve retention'da güçlüdür: saatlik özet ve eski verinin silinmesi onun doğal işidir (R1.4'te 10, Ö7). "
               "Ama bu kart bir sayaç iş yüküdür, bir ölçüm geçmişi değil: engine artırmaz, her olayı bir point olarak saklar (Ö1) ve sayıyı her okumada yeniden toplar (Ö5); tekil ziyaretçi ise yüksek cardinality tuzağına düşer (Ö2). "
               "Kampanya tepesinde yazma ve her 2 saniyelik sorgu aynı instance'ta yarışır (R2). Ekip için yeni bir sistem ve yeni bir sorgu dili R4'te de puan kaybettirir. "
               "Hangi koşul değişseydi Timestream for InfluxDB seçilirdi: ekran son saati değil son 30 günü dakika dakika gösterseydi ve sorgular zaman pencereleri üzerinde değişken olsaydı; o zaman bellek yerine bir time series engine'i doğru yer olurdu.",
         },
    verdict="Karar: ElastiCache {ec}, DynamoDB {ddb}, Timestream for InfluxDB {ix}. Bu iş yüküne en uygun servis ElastiCache'tir ve doğru mimari iki parçalıdır: canlı saat ElastiCache'te, saatlik geçmiş Redshift'te. "
            "Bu kart ElastiCache sayfasının 5. kartıyla aynı iş yüküdür ve aynı puanları taşır; Timestream for InfluxDB üçüncüdür. "
            "Yine de Timestream for InfluxDB seçersek artımız: saatlik özet ve eski verinin silinmesi bir ayardır ve son 30 günü dakika dakika gösteren bir ekran aynı sistemden çizilir. "
            "Eksimiz: her olayı bir point olarak saklarız ve sayıyı her okumada toplarız; tekil ziyaretçiyi yaklaşık sayamayız; kampanya akşamına göre büyük bir instance seçer ve gece de öderiz. "
            "Bir koşul değişseydi: ekran son 30 günü dakika dakika gösterseydi Timestream for InfluxDB öne geçerdi."))

USECASES_W["influxdb"] = INFLUXDB_W
PAGE_SVC["influxdb"] = "ix"


# ====================================================================== Amazon S3 (page id "s3"), Turkish, model 2
# Ten weighted cards of the S3 page. "s3" is an S3 general purpose bucket (the page's service). Twin decision (docs/s3.scope.md):
#  - The storage classes of a general purpose bucket (Standard, Standard-IA, Intelligent-Tiering, Glacier Instant Retrieval,
#    Glacier Flexible Retrieval, Glacier Deep Archive) are ONE engine: same bucket, key, API, consistency, versions, lifecycle,
#    Object Lock. The class decides only where the bytes rest, how fast they come back and the price: packaging (R2, R3, R5).
#    They are twins and get the same R1 points (card 2: "s3gda", "s3gfr"). On the other cards the "s3" candidate uses the class
#    that the story needs through a lifecycle rule (Ö6); card 2 compares the classes themselves from the first day.
#  - S3 Express One Zone ("s3x") is NOT a twin: a directory bucket has a hierarchical namespace, unsorted listing, append and
#    rename, and no versioning, Object Lock, event notifications, lifecycle transitions or object tags. R1 is scored separately.
#  - S3 Tables ("s3t") is NOT a twin: a table bucket stores Apache Iceberg tables (rows and snapshots), not objects as written.
#  - S3 Vectors is not a candidate on this page (no workload of the ten cards asks for a similarity search); M5 names it.
# Card 10 repeats DynamoDB card 9 ("files"): rows, weights and the points of DynamoDB and DocumentDB are copied in code
# (decisions.md, "The same workload on two pages"); Aurora (77 on the DynamoDB page) gives its place to S3, the page's service.
# Graded reductions of S3 (written once, M2 summary): no search inside objects (R1 · EY): 0 when the question is a date or a
# prefix, -3 when a field is sometimes needed, -5 when text and field search is the work itself. No append and no in-place
# write (R1 · OY): -1 when the stream is written as batch files, -2 when a live log is appended, -8 when in-place writes,
# rename and append are the work itself. S3 Express One Zone single AZ (R3): -6 when it holds the only copy, -1 when a
# full copy stays in S3 Standard.
# Sources (read on 2026-10-31; hedges are the hedges of the source):
#  - Objects 0 B to 50 TB, single PUT up to 5 GB, multipart up to 10,000 parts: https://aws.amazon.com/s3/faqs/,
#    https://docs.aws.amazon.com/AmazonS3/latest/userguide/upload-objects.html, https://docs.aws.amazon.com/AmazonS3/latest/userguide/qfacts.html
#  - Strong read-after-write consistency for GET, PUT, LIST, tags and metadata; concurrent writes: last writer wins:
#    https://aws.amazon.com/s3/consistency/, https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
#  - Conditional writes If-None-Match / If-Match for PutObject, CompleteMultipartUpload, CopyObject; 412 Precondition Failed:
#    https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-requests.html, https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html
#  - "at least 3,500 PUT/COPY/POST/DELETE or 5,500 GET/HEAD requests per second per partitioned Amazon S3 prefix", 503 SlowDown while
#    scaling: https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance-design-patterns.html
#  - User-defined metadata ~2 KB, fixed at upload; up to 10 tags per object: https://aws.amazon.com/s3/faqs/
#  - Object Lock compliance and governance modes, legal hold: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
#  - Lifecycle transitions and expirations are asynchronous; objects under 128 KB do not transition by default:
#    https://docs.aws.amazon.com/AmazonS3/latest/userguide/troubleshoot-lifecycle.html, https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html
#  - Event notifications "designed to be delivered at least once", "typically ... in seconds but can sometimes take a minute or longer":
#    https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventNotifications.html
#  - Deep Archive: minimum 180 days, "default retrieval time of 12 hours", at least three AZs; Glacier Instant Retrieval: milliseconds,
#    minimum 90 days: https://aws.amazon.com/s3/cost-optimization/, https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_s3.StorageClass.html
#  - S3 Express One Zone: single AZ, "single-digit millisecond", "up to 10x faster than S3 Standard", 200,000 reads and 100,000 writes
#    per second per directory bucket by default; append (write offset) and RenameObject; features not supported by directory buckets:
#    https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-performance.html, https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-differences.html
#  - S3 Tables: Iceberg tables, automatic compaction (Parquet, Avro, ORC): https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables-maintenance.html
#  - S3 Metadata journal and live inventory tables: https://aws.amazon.com/s3/faqs/
#  - Amazon EFS: NFS v4, close-to-open consistency, advisory locking: https://docs.aws.amazon.com/efs/latest/ug/features.html
#  - Price List API, eu-central-1, 2026-10-31: S3 Standard 0.0245 USD/GB-month (first 50 TB), 0.0235 (next 450 TB); Standard-IA 0.0135;
#    Glacier Instant Retrieval 0.005 (+0.03 USD/GB retrieved); Glacier Deep Archive 0.0018 (standard retrieval 0.024 USD/GB);
#    Express One Zone 0.118; S3 Tables 0.0282; PUT/COPY/POST/LIST 0.0054 USD per 1,000; GET 0.0043 USD per 10,000;
#    Express One Zone GET 0.0000323 USD per 1,000; EFS Standard 0.36 USD/GB-month, Infrequent Access 0.0266, elastic
#    throughput reads 0.04 USD/GB; CloudWatch Logs ingestion 0.63 USD/GB, storage 0.0324 USD/GB-month.
for _k, _cat in (("s3", ("object storage", "object storage")), ("efs", ("shared file system", "paylaşılan dosya sistemi")),
                 ("s3gda", ("object storage, archive class", "object storage, arşiv sınıfı")),
                 ("s3gfr", ("object storage, archive class", "object storage, arşiv sınıfı")),
                 ("s3x", ("single-AZ object storage (directory bucket)", "tek AZ'li object storage (directory bucket)")),
                 ("s3t", ("Iceberg table storage", "Iceberg table storage'ı"))):
    CATEGORY.setdefault(_k, _cat)
    LINK.setdefault(_k, "s3")       # EFS, the S3 classes, S3 Express One Zone and S3 Tables have no page of their own; this page compares them

_S3_D9 = next(u for u in DDB_W if u["id"] == "files")


def _s3x(t):
    """Remove the feature numbers of another page (Ö3 of DynamoDB is not Ö3 of S3)."""
    return re.sub(r"\s*\((?:Ö\d(?:, )?)+\)", "", t)


def _s3same(uc, c, mine):
    assert [p for p, _ in mine] == [p for p, _ in uc["scores"][c]], f"{uc['id']}: {c} must keep the points of the other page"
    return mine


S3_W = []

# 1 ---------------------------------------------------------------- product images
S3_W.append(wusecase("images", 1, sim="w_images",
    title="Ürün görselleri: bir kez yüklenir, milyonlarca kez gösterilir",
    key="Key: products/<ürün id>/<boyut>.jpg. Değer: görselin byte'ları, Content-Type ve kullanıcı metadata'sı. Önünde CloudFront.",
    story="Lale Market'te 20.000 ürün var ve her ürünün 3 ile 8 arası fotoğrafı, her fotoğrafın dört boyutu bulunuyor: yaklaşık 600.000 dosya, toplam 120 GB. "
          "Bir dosya 50 KB ile 5 MB arasıdır. Ürün sayfaları tepe anında saniyede 3.000 görsel ister; CloudFront bunların yüzde 95'ini kendi önbelleğinden verir, "
          "kaynağa saniyede yaklaşık 150 istek gelir. Satıcılar günde 2.000 yeni fotoğraf yükler ve her yüklemeden sonra küçük boyutları üreten bir iş çalışmalıdır. "
          "Satıcılar orijinal dosyalarını saklamıyor: kaybolan bir görsel yeniden çekim demektir. Yanlış bir görselin üstüne yazılırsa eski görsel 30 gün geri getirilebilmeli. "
          "Ürün kayıtları Aurora'da durur ve her ürün satırı görselin key'ini tutar. Ekip üç geliştiriciden oluşur, sunucu işletecek kimse yok.",
    wnote="R1 toplam 42: değer bir dosyadır (VM 12), tarayıcı onu key ile ve bir URL üzerinden ister (EY 12), yükleme sonrası iş ve eski sürümler yaşam döngüsünün parçasıdır (YD 10). "
          "R3 18 ile R1'den sonra en ağır satırdır: satıcının elinde ikinci bir kopya yoktur.",
    rows=[row("VM", 12, "Değer bir fotoğraftır: 50 KB ile 5 MB arası binary dosya.",
              "Her türden binary dosya (JPEG, PNG, WebP) 50 KB ile 5 MB arasında, olduğu gibi saklanmalı; Content-Type ve birkaç kısa etiket dosyayla birlikte durmalı.",
              "Dosya parçalanıp başka bir biçime çevrilirse her görüntülemede yeniden birleştirilir ve tarayıcı yanlış türde byte alır."),
          row("EY", 12, "Ürün sayfası görseli ürün id'sinden kurduğu key ile ister; başka bir soru yoktur.",
              "Görsel ürün id'sinden kurulan key ile, bir HTTP URL'si olarak okunmalı; bir tarayıcı ya da bir CDN onu bu URL'den doğrudan alabilmeli.",
              "Key ile okunamayan bir görsel için önce bir arama gerekir ve her sayfa açılışı bir istek daha bekler."),
          row("OY", 8, "Görsel bir kez yazılır ve binlerce kez okunur; düzenleme yoktur.",
              "Bir kez yaz, çok kez oku. Yeni bir fotoğraf eskisinin tamamının yerine geçer; dosyanın bir parçası hiç değişmez.",
              "Okuma yolu bir yazma kilidini beklerse kampanya anında görseller geç açılır."),
          row("YD", 10, "Yüklemeden sonra küçük boyutlar üretilmeli ve eski görsel 30 gün geri getirilebilmeli.",
              "Yeni dosya geldiğinde boyutlandırma işi kendiliğinden başlamalı; üstüne yazılan görselin eski sürümü 30 gün kalmalı, sonra kendiliğinden silinmeli.",
              "Tetikleyici yoksa uygulama her yüklemede işi kendisi çağırır ve unutulan bir yol küçük boyutsuz ürün bırakır; eski sürüm yoksa yanlış yükleme geri alınamaz."),
          row("R2", 15, "Tepe anında saniyede 3.000 görsel, kaynağa 150 istek; 600.000 dosya.",
              "Tepe anında CloudFront arkasında saniyede 150 kaynak isteği ve günde 2.000 yazma; dosya sayısı yılda iki katına çıkabilir, kapasite planlanmamalı.",
              "Kaynak tepe anında yavaşlarsa CloudFront önbelleğinde olmayan her görsel geç gelir."),
          row("R3", 18, "Satıcının orijinali yoktur: kaybolan görsel yeniden çekimdir.",
              "Bir disk ya da bir Availability Zone kaybında hiçbir görsel kaybolmamalı.",
              "Kaybolan bir görsel bir ürünün satıştan kalkması ve satıcıya yeniden çekim demektir."),
          row("R4", 13, "Üç geliştirici var, sunucu işletecek kimse yok.",
              "Sunucu, disk ve yama olmadan çalışmalı; ekip AWS SDK biliyor.",
              "Bir web sunucusu katmanı ekip için gece nöbeti demektir."),
          row("R5", 12, "120 GB az okunan değil, çok okunan veri; istekler CDN'den geçer.",
              "120 GB her ay saklanır: GB başına saklama ucuz olmalı; istek ücreti CloudFront arkasında küçük kalmalı; sunucu saati ödenmemeli.",
              "Saat başına ödenen sunucular gece de çalışır; pahalı disk 120 GB'ı her ay pahalı tutar.")],
    cands=["s3", "efs", "aur"],
    scores={
        "s3": [sc(10, "Bir nesne her türden byte'tır ve 50 TB'a kadar olabilir (Ö1); Content-Type ve kullanıcı metadata'sı nesneyle birlikte saklanır (Ö3). Puan kırılmadı."),
               sc(10, "GET products/P0001/800.jpg tek bir HTTP isteğidir (Ö1); bir tarayıcı ya da CDN nesneyi bu URL'den alır. Puan kırılmadı."),
               sc(10, "PUT nesnenin tamamını yazar, okumalar kilit beklemez; güçlü tutarlılık yeni görseli hemen gösterir (Ö1, Ö4). Puan kırılmadı."),
               sc(10, "Yeni nesne bir olay bildirimiyle boyutlandırma işini başlatır (Ö8); versioning eski görseli tutar (Ö5) ve lifecycle kuralı onu 30 gün sonra siler (Ö6). Puan kırılmadı."),
               sc(10, "Prefix başına saniyede en az 5.500 GET; kapasite planı yoktur. Puan kırılmadı."),
               sc(10, "Nesne bir Region'daki en az üç Availability Zone'da saklanır; 11 dokuzluk dayanıklılık için tasarlanmıştır. Puan kırılmadı."),
               sc(9, "Sunucusuz; ekip SDK ile çalışır. 1 puan kırıldı: CloudFront için origin access control ve bucket policy yazılır."),
               sc(10, "120 GB × 0,0245 USD yaklaşık 2,9 USD/ay; GET 10.000 istekte 0,0043 USD (Price List API, eu-central-1, 2026-10-31). Puan kırılmadı.")],
        "efs": [sc(10, "Bir dosya sistemi her türden dosyayı olduğu gibi saklar. Puan kırılmadı."),
                sc(7, "Dosya bir yol ile okunur. 3 puan kırıldı: dosya bir HTTP URL'si değildir; tarayıcıya ve CloudFront'a bir web sunucusu (örneğin nginx) üzerinden gider."),
                sc(10, "Dosya bir kez yazılır, okumalar paralel çalışır. Puan kırılmadı."),
                sc(3, "7 puan kırıldı: dosya sisteminde sürüm ve olay bildirimi yoktur; uygulama eski dosyayı kendisi saklar ve boyutlandırma işini kendisi tetikler."),
                sc(9, "Elastic throughput yükle büyür. 1 puan kırıldı: her kaynak isteği bir web sunucusundan geçer ve web sunucuları tepe için önceden eklenen sabit kapasitedir (sunucuların işletilmesi R4'te)."),
                sc(10, "Regional EFS veriyi birden fazla Availability Zone'da saklar. Puan kırılmadı."),
                sc(4, "6 puan kırıldı: EC2 web sunucuları, mount target'lar, yamalar ve sunucu sayısı ekibin işidir."),
                sc(3, "7 puan kırıldı: Standard storage GB-ay 0,36 USD, S3 Standard'ın yaklaşık 15 katı; web sunucuları ayrıca saat başına ödenir.")],
        "aur": [sc(3, "bytea kolonu bir görseli tutabilir. 7 puan kırıldı: 5 MB'lık binary değerler table'ı, WAL'ı, yedekleri ve replica'ları büyütür."),
                sc(7, "SELECT ile key'e göre okunur. 3 puan kırıldı: tarayıcıya bir URL değil, uygulama sunucusunun aktardığı byte'lar döner (EFS'in web sunucusuyla aynı kırılım)."),
                sc(9, "Bir kez INSERT edilir. 1 puan kırıldı: görselin değişmesi row'un yeni bir sürümünü yazar ve eski sürüm VACUUM'a kalır (Aurora sayfasının kademesi: seyrek güncelleme 1 puan)."),
                sc(4, "6 puan kırıldı: eski görsel için ayrı bir tarih table'ı, yeni görsel için bir trigger ya da kuyruk tetikleyicisi uygulamada yazılır."),
                sc(5, "5 puan kırıldı: saniyede 150 görsel × ortalama 500 KB yaklaşık 75 MB/s'yi instance'lardan geçirir ve checkout ile aynı kaynağı paylaşır."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(6, "Aurora zaten çalışıyor; table eklemek kolaydır. 4 puan kırıldı: görselleri sunan uygulama yolu ve büyüyen database'in yedek ve geri yükleme süresi ekibin işidir."),
                sc(4, "6 puan kırıldı: database storage'ı ve I/O, dosya saklamak için object storage'ın katlarıdır; okuma trafiği instance kapasitesi ister.")],
    },
    h2h={
        "efs": "Paylaşılan dosya sistemi (EFS) ile kafa kafaya. EFS de dosyayı olduğu gibi saklar ve birden fazla Availability Zone'da tutar; görsel kaybolmaz (R3 eşit). "
               "Ayrıştığı yer erişim ve yaşam döngüsüdür: EFS bir NFS dosya sistemidir, tarayıcı ona doğrudan ulaşamaz. Her görsel bir web sunucusundan geçer (R1 · EY ve R4), "
               "sürüm ve olay bildirimi yoktur (R1 · YD), Standard storage GB-ay 0,36 USD ile S3 Standard'ın yaklaşık 15 katıdır (R5). "
               "EFS'in dürüst üstünlüğü dosyayı yerinde değiştiren, kilit kullanan ve yolu bekleyen programlardadır (kart 6). "
               "Hangi koşul değişseydi EFS seçilirdi: görselleri tarayıcı değil, aynı dosyaları yerinde düzenleyen ve yeniden adlandıran eski bir görsel işleme uygulaması kullansaydı ve kod değişemeseydi.",
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Aurora bu sistemde zaten çalışıyor ve ürün kaydı onda; görseli de aynı row'a koymak tek bir yedek ve tek bir transaction gibi görünür. "
               "Ama engine bir dosya deposu değildir: 5 MB'lık bytea değerleri table'ı, WAL'ı ve replica'ları büyütür (R1 · VM), tarayıcıya byte'ları bir uygulama sunucusu taşır (R1 · EY) "
               "ve saniyede 75 MB'lık görsel trafiği checkout ile aynı instance'ları kullanır (R2). "
               "Aurora'nın doğru rolü görselin key'ini ve ürünün iş verisini tutmaktır; dosya S3'te kalır. "
               "Hangi koşul değişseydi Aurora seçilirdi: görseller birkaç KB'lık ikonlar olsaydı, sayıları birkaç bin olsaydı ve ürün row'uyla aynı transaction'da yazılmaları bir kural olsaydı.",
    },
    verdict="Karar: S3 {s3}, EFS {efs}, Aurora {aur}. S3 R1'in 42 puanının tamamını alır: dosya bir nesnedir, key ile bir URL'den okunur, yükleme bir olay bildirimi üretir, eski sürüm versioning ile kalır. "
            "S3 seçtiğimizde artımız: sunucu yoktur, CloudFront doğrudan bucket'tan okur, yanlış yükleme 30 gün geri alınır. "
            "Eksimiz: ürün adı ve fiyat gibi aranan alanlar S3'te değil Aurora'da kalır; uygulama key'i Aurora'daki ürün row'unda tutar. "
            "Doğru mimari ikisi birliktedir: dosya S3'te, key ve iş verisi Aurora'da, önünde CloudFront. Bir koşul değişseydi: dosyaları yerinde düzenleyen eski bir program kullansaydı EFS öne geçerdi."))

# 2 ---------------------------------------------------------------- backups: the storage class itself (twins)
S3_W.append(wusecase("backups", 2, sim="w_backups",
    title="Veritabanı yedek dosyaları: yedi yıllık saklama, hangi depolama sınıfı?",
    key="Key: backups/<database>/<yıl>/<ay>.dump. Aylık tam yedek, 1,2 TB. Aday satırları burada aynı bucket'ın üç depolama sınıfıdır.",
    story="Lale Market her ayın son günü bütün veritabanlarının tam bir mantıksal yedeğini alır: tek bir 1,2 TB'lık dosya. Muhasebe kuralı bu dosyaları yedi yıl istiyor; "
          "yedi yıl dolunca silinmeleri de gerekiyor. Yedi yılın sonunda 84 dosya, yaklaşık 100 TB birikir. Günlük geri yükleme bu dosyalardan yapılmaz; "
          "onu veritabanının kendi sürekli yedeği karşılar. Bu dosyalar yılda bir ya da iki kez, bir denetim ya da hukuk talebi için açılır; talep yazılı gelir ve "
          "cevap için 48 saat vardır, bazen aynı gün istenir. Dosya yüklendikten sonra değişmez ve kimse onu süresinden önce silememeli. "
          "Bütçe sahibi bu arşiv için ayda 500 USD'ı aşmak istemiyor. Ekip S3 kullanıyor ve yeni bir servis öğrenmek istemiyor.",
    wnote="R1 toplam 36 ve en ağır gruptur; ama üç aday aynı engine'dir ve R1'de eşittir. Kararı R5 (26) verir: 100 TB'ın yedi yıllık faturası bu iş yükünün asıl sorusudur. "
          "R2 14: dosyanın ne kadar sürede geri geldiği de bir servis tasarımıdır.",
    rows=[row("VM", 10, "Değer tek bir 1,2 TB'lık dosyadır.",
              "1,2 TB'lık tek bir dosya parçalara bölünmeden tek bir değer olarak saklanmalı; yükleme gece bitecek kadar paralel olmalı.",
              "Dosya parçalara bölünüp ayrı ayrı saklanırsa geri yüklemede bir parçanın eksik olması fark edilmeyebilir."),
          row("OY", 8, "Dosya bir kez yazılır, yedi yıl hiç değişmez.",
              "Bir kez yaz, hiç değiştirme; yılda bir ya da iki kez bütün dosyayı oku.",
              "Değişebilen bir yedek kanıt değeri taşımaz."),
          row("YD", 12, "Yedi yıl kural gereği saklanır ve sonra silinmelidir; süresinden önce silinmemelidir.",
              "Dosya yedi yıl boyunca kimse tarafından silinememeli ya da üstüne yazılamamalı; yedi yıl dolunca kendiliğinden silinmeli.",
              "Erken silinen bir yedek denetimde eksik kayıt, geç silinen bir yedek saklama kuralının ihlalidir."),
          row("EY", 6, "Dosya yılda bir ya da iki kez, adıyla bulunur.",
              "Dosya veritabanı adı ve ay ile kurulan key ile bulunmalı; içinde arama yoktur.",
              "Key ile bulunamayan bir yedek için bütün arşiv listelenir."),
          row("R2", 14, "Yazılı talep 48 saat verir; bazen aynı gün istenir.",
              "Ayda bir 1,2 TB gece içinde yüklenmeli; geri yükleme 48 saat içinde, mümkünse aynı gün hazır olmalı.",
              "Geri yükleme günler sürerse hukuk talebine zamanında cevap verilemez."),
          row("R3", 14, "Yedek, veritabanı kaybolduğunda son çaredir.",
              "Bir Availability Zone kaybında hiçbir yedek kaybolmamalı.",
              "Kaybolan bir yedek, ihtiyaç anında hiç yedek olmaması demektir."),
          row("R4", 10, "Ekip S3 biliyor ve yeni servis öğrenmek istemiyor.",
              "Aynı bucket, aynı API ve aynı araçlar; ayrı bir arşiv sistemi işletilmemeli.",
              "Ayrı bir arşiv sistemi yılda bir kullanılan bir runbook ve unutulan bir parola demektir."),
          row("R5", 26, "100 TB yedi yıl boyunca her ay ödenir; bütçe ayda 500 USD.",
              "Yedi yılın sonunda 100 TB (84 dosya × 1,2 TB) her ay saklanır: GB-ay fiyatı en düşük olmalı; yılda bir ya da iki 1,2 TB'lık geri getirme ücreti kabul edilir; dosya en az yedi yıl kalacağı için en kısa saklama süresi sorun değildir.",
              "Yanlış sınıf seçilirse arşivin faturası yedi yıl boyunca her ay katlanır.")],
    cands=["s3gda", "s3gfr", "s3"],
    scores={
        "s3gda": [sc(10, "Aynı S3 engine'i: tek nesne 50 TB'a kadar, çok parçalı yükleme paraleldir. Puan kırılmadı."),
                  sc(10, "Nesne bir kez yazılır ve değişmez. Puan kırılmadı."),
                  sc(10, "Object Lock compliance modu yedi yıl silmeyi ve üstüne yazmayı engeller; lifecycle kuralı (Expiration ve NoncurrentVersionExpiration birlikte, B4) kilit bitince siler. Sınıf bu özellikleri değiştirmez. Puan kırılmadı."),
                  sc(10, "Key ile bulunur. Puan kırılmadı."),
                  sc(7, "3 puan kırıldı: nesne önce RestoreObject ile geri getirilir; varsayılan geri getirme süresi 12 saattir, aynı gün istenen bir talepte pay az kalır."),
                  sc(10, "En az üç Availability Zone'da saklanır, 11 dokuzluk dayanıklılık için tasarlanmıştır. Puan kırılmadı."),
                  sc(10, "Aynı bucket ve aynı API; sınıf PUT isteğinde ya da bir lifecycle kuralında seçilir. Puan kırılmadı."),
                  sc(10, "100 TB × 0,0018 USD yaklaşık 184 USD/ay; 1,2 TB'lık bir geri getirme yaklaşık 30 USD (Price List API, eu-central-1, 2026-10-31). En kısa saklama süresi 180 gündür ve yedi yıllık dosyaya dokunmaz. Puan kırılmadı.")],
        "s3gfr": [sc(10, "Aynı S3 engine'i. Puan kırılmadı."),
                  sc(10, "Nesne bir kez yazılır ve değişmez. Puan kırılmadı."),
                  sc(10, "Object Lock ve lifecycle bu sınıfta da aynıdır. Puan kırılmadı."),
                  sc(10, "Key ile bulunur. Puan kırılmadı."),
                  sc(9, "1 puan kırıldı: nesne önce RestoreObject ile geri getirilir; geri getirme dakikalar ile saatler sürer ve aynı gün istenen bir talep için yeter."),
                  sc(10, "Birden fazla Availability Zone'da saklanır. Puan kırılmadı."),
                  sc(10, "Aynı bucket ve aynı API. Puan kırılmadı."),
                  sc(8, "2 puan kırıldı: 100 TB × 0,00405 USD yaklaşık 415 USD/ay, Deep Archive'ın (184 USD) 2,25 katı; geri getirme ayrıca ödenir.")],
        "s3": [sc(10, "Bir nesne 50 TB'a kadar olabilir ve çok parçalı yüklenir (Ö1). Puan kırılmadı."),
               sc(10, "PUT nesnenin tamamını yazar ve nesne değişmez (Ö1). Puan kırılmadı."),
               sc(10, "Object Lock compliance modu (Ö7) silmeyi engeller; lifecycle (Ö6, Expiration ve NoncurrentVersionExpiration birlikte) kilit bitince siler. Puan kırılmadı."),
               sc(10, "Key ile bulunur (Ö1). Puan kırılmadı."),
               sc(10, "Nesne milisaniyelerde okunur. Puan kırılmadı."),
               sc(10, "En az üç Availability Zone. Puan kırılmadı."),
               sc(10, "Varsayılan sınıftır; ek ayar yoktur. Puan kırılmadı."),
               sc(1, "9 puan kırıldı: 100 TB'ın ilk 50 TB'ı 0,0245, sonrası 0,0235 USD ile yaklaşık 2.458 USD/ay, Deep Archive'ın 13 katı; bu dosyalar yılda bir ya da iki kez okunur.")],
    },
    h2h={
        "s3gfr": "Arşiv sınıfı, esnek geri getirmeli (S3 Glacier Flexible Retrieval) ile kafa kafaya. Aynı engine, aynı bucket, aynı Object Lock ve aynı lifecycle: R1'de iki aday eşittir (36). "
                 "Fark iki servis satırındadır. Flexible Retrieval dosyayı dakikalar ile saatler içinde geri getirir ve aynı gün gelen bir talebi karşılar (R2 9'a 7); Deep Archive'ın varsayılan geri getirmesi 12 saattir. "
                 "Buna karşılık 100 TB'ın aylık faturası 415 USD'a karşı 184 USD'dır (R5); bu kartta talep yazılı ve 48 saat süreli olduğu için R5 kazanır, fark 2,4 puandır ve yakın bir yarıştır. "
                 "Aynı engine'in milisaniye erişimli sınıfı Glacier Instant Retrieval da değerlendirildi: R2'de 10 alır ama 512 USD/ay ile 500 USD'lık bütçeyi aşar ve R5'te 7 ile 92,2 toplar; yılda bir açılan dosya için milisaniyeye ödenen fark gereksizdir. "
                 "Hangi koşul değişseydi Glacier Flexible Retrieval seçilirdi: talepler çoğunlukla aynı gün cevap isteseydi; dosyalar ayda birkaç kez ve dakikalar içinde okunsaydı Glacier Instant Retrieval seçilirdi.",
        "s3": "Object storage, varsayılan sınıf (S3 Standard) ile kafa kafaya. Bu sayfanın servisi burada varsayılan sınıfında yarışır: dosyayı yükleyip hiçbir sınıf ya da lifecycle kuralı seçmeyen bir ekibin durumu. "
              "Engine aynıdır ve R1 eşittir; Standard dosyayı milisaniyelerde verir (R2) ve hiçbir ayar istemez. "
              "Ama yılda bir ya da iki kez okunan 100 TB için ayda yaklaşık 2.458 USD ödenir; Deep Archive'ın 13 katı (R5). "
              "Bu kart bir mimarın en ucuz kararını gösterir: aynı nesneyi yükleme anında doğru sınıfa koymak ya da bir lifecycle kuralıyla oraya taşımak. "
              "Hangi koşul değişseydi S3 Standard seçilirdi: dosyalar birkaç gün tutulup silinseydi, her gün okunsaydı ya da sayıları ve boyutları faturayı önemsiz kılacak kadar küçük olsaydı.",
    },
    verdict="Karar: S3 Glacier Deep Archive {s3gda}, S3 Glacier Flexible Retrieval {s3gfr}, S3 {s3}. Üç aday aynı engine'dir ve R1'de eşittir; kararı R5 verir, R2 farkı daraltır (yakın yarış). "
            "Yine de S3 Standard'da bırakırsak artımız: dosya her an milisaniyelerde açılır ve hiçbir ayar yoktur (Ö1). "
            "Eksimiz: aynı arşiv için ayda yaklaşık 2.270 USD fazla ödenir; uygulama yüklemede sınıfı DEEP_ARCHIVE seçmeli ya da bir lifecycle kuralı (Ö6) yazmalı, geri yükleme runbook'u RestoreObject ile başlamalıdır. "
            "Bir koşul değişseydi: talepler çoğunlukla aynı gün cevap isteseydi Glacier Flexible Retrieval kazanırdı."))

# 3 ---------------------------------------------------------------- data lake raw zone
S3_W.append(wusecase("datalake", 3,
    title="Veri gölünün ham bölgesi: dosyalar geldiği gibi, yıllarca",
    key="Key: raw/<kaynak>/dt=YYYY-MM-DD/<dosya>. CSV, JSON, gzip ve Parquet olduğu gibi. Athena ve Redshift Spectrum yerinde okur.",
    story="Lale Market'in veri gölünde 40 TB ham veri var ve her ay 2 TB büyüyor. Partnerler günde yaklaşık 3.000 dosya gönderiyor: CSV ve JSON, 1 KB ile 2 GB arası; "
          "web olayları beş dakikada bir gzip'li JSON dosyaları olarak geliyor. Ham dosyalar olduğu gibi kalmalı: bir dönüştürme işi hatalı çıkarsa her şey ham dosyadan yeniden üretilir. "
          "Bir dosya geldiğinde temizleme işi kendiliğinden başlamalı. Partnerler dosyalarına ara sıra yeni bir alan ekliyor. "
          "90 günden eski dosyalar nadiren okunur; beş yıl sonra silinmeleri gerekir. Analistler Athena ile, raporlar Redshift Spectrum ile aynı dosyaları yerinde okur "
          "(Redshift sayfasının 10. kartı bu okuma tarafını puanlar). Veri ekibi üç kişi ve bir cluster işletmek istemiyor.",
    wnote="R1 toplam 42: değer olduğu gibi saklanan bir dosyadır (VM 12), şema okurken uygulanır (ŞE 10), yeni dosya bir işi başlatır ve eski dosya ucuzlar ve silinir (YD 12). "
          "R5 18 ile ikinci: 40 TB her ay büyür.",
    rows=[row("VM", 12, "Kaynaklar CSV, JSON, gzip ve Parquet gönderir; ham dosya olduğu gibi kalmalıdır.",
              "Her dosya biçimi, 1 KB ile 2 GB arası, byte byte olduğu gibi saklanmalı; bir dönüştürme hatasında ham dosyadan yeniden üretim yapılabilmeli.",
              "Dosya saklanmadan önce başka bir biçime çevrilirse çevirideki bir hata ham veriyi de bozar ve geri dönülemez."),
          row("ŞE", 10, "Partnerler dosyalarına ara sıra yeni alan ekliyor.",
              "Yazarken şema istenmemeli; şema okurken (Athena ve Spectrum'un table tanımında) uygulanmalı ve yeni bir alan eski dosyaları bozmamalı.",
              "Yazarken şema isteyen bir depo yeni alanlı dosyayı reddeder ve partner verisi eksik kalır."),
          row("OY", 8, "Dosyalar sürekli eklenir; ara sıra aynı dosya yeniden gönderilir.",
              "Yeni dosya yeni bir key'dir; aynı dosya yeniden gelirse eskisi kaybolmadan yenisi yazılmalı; dosyanın içi hiç düzenlenmez.",
              "Yeniden gönderim eski dosyayı sessizce silerse hatalı bir partner dosyası doğru olanı yok eder."),
          row("YD", 12, "Yeni dosya bir işi başlatmalı; beş yıl sonra silinmeli.",
              "Dosya geldiği anda temizleme işi tetiklenmeli; beş yıl sonra kendiliğinden silinmeli. Eski dosyaların daha ucuz bir sınıfa geçmesinin fiyatı R5'te sayılır.",
              "Tetikleyici yoksa bir zamanlayıcı bütün dosyaları tarar; silme kuralı yoksa saklama süresi kaçar."),
          row("R2", 12, "Ayda 2 TB, günde 3.000 dosya, birçok paralel okuyucu.",
              "Günde 3.000 dosya ve beş dakikada bir olay dosyası yazılmalı; Athena ve Spectrum aynı anda yüzlerce dosyayı paralel okuyabilmeli.",
              "Paralel okuma sınırlanırsa çeyrek raporu saatler sürer."),
          row("R3", 14, "Ham dosya tek kopyadır ve her şeyin yeniden üretim kaynağıdır.",
              "Bir Availability Zone kaybında hiçbir ham dosya kaybolmamalı.",
              "Kaybolan ham dosya, ondan üretilen bütün table'ların doğrulanamaması demektir."),
          row("R4", 14, "Üç kişilik veri ekibi cluster işletmek istemiyor.",
              "Sunucu ve cluster olmamalı; Athena ve Spectrum dosyaları yerinde okumalı; Glue Data Catalog zaten kullanılıyor.",
              "Bir yükleme cluster'ı küçük ekibin bütün zamanını alır."),
          row("R5", 18, "40 TB her ay 2 TB büyüyor; eski dosyalar nadiren okunur.",
              "40 TB, her ay 2 TB büyür; dosyaların bir kısmı 128 KB'tan küçüktür: GB-ay fiyatı düşük olmalı; eski veri kendiliğinden daha ucuz sınıfa geçmeli; okuma için compute saati ödenmemeli.",
              "Pahalı bir depoda 40 TB her ay pahalıdır ve büyüdükçe katlanır.")],
    cands=["s3", "s3t", "rs"],
    scores={
        "s3": [sc(10, "Bir nesne her biçimden byte'tır ve olduğu gibi saklanır (Ö1). Puan kırılmadı."),
               sc(10, "Object storage şema bilmez; şema Glue table tanımında, okurken uygulanır. Puan kırılmadı."),
               sc(10, "Yeni dosya yeni key'dir; versioning yeniden gönderilen dosyanın eskisini tutar (Ö5). Puan kırılmadı."),
               sc(10, "Yeni nesne bir olay bildirimiyle işi başlatır (Ö8); lifecycle kuralı beş yıl sonra siler (Ö6). Puan kırılmadı."),
               sc(10, "Prefix başına saniyede en az 3.500 yazma ve 5.500 okuma; prefix sayısında sınır yoktur (Ö2). Puan kırılmadı."),
               sc(10, "En az üç Availability Zone, 11 dokuzluk dayanıklılık için tasarlanmış. Puan kırılmadı."),
               sc(10, "Athena ve Spectrum dosyaları yerinde okur; Glue kataloğu zaten vardır; sunucu yoktur. Puan kırılmadı."),
               sc(9, "40 TB Standard'da ayda yaklaşık 1.000 USD, 90 gün sonra Standard-IA'da GB-ay 0,0135 USD. 1 puan kırıldı: 128 KB'tan küçük partner dosyaları varsayılan olarak sınıf değiştirmez ve her dosya istek başına ödenir.")],
        "s3t": [sc(4, "Table bucket Apache Iceberg table'ları tutar. 6 puan kırıldı: ham CSV ve JSON dosyaları olduğu gibi saklanmaz; önce Parquet, Avro ya da ORC'ye çevrilip bir table'a yazılır."),
                sc(6, "Iceberg şeması evrilebilir: kolon eklemek eski dosyaları bozmaz. 4 puan kırıldı: şema yazarken uygulanır; yeni alanlı dosya önce table şemasına eklenir."),
                sc(9, "Her yükleme bir append commit'idir; eski snapshot'lar kalır. 1 puan kırıldı: küçük commit'ler compaction çalışana kadar küçük dosyalar bırakır."),
                sc(6, "Snapshot'lar ve otomatik compaction vardır. 4 puan kırıldı: dosya bazında olay bildirimi yerine yükleme işinin kendisi commit eder; ham dosyanın beş yıllık saklaması table snapshot'larıyla değil ayrı bir bucket'la yapılır."),
                sc(9, "Yüksek istek hızı için tasarlanmıştır. 1 puan kırıldı: günde 3.000 küçük commit compaction'ı sürekli meşgul eder."),
                sc(10, "Birden fazla Availability Zone'da saklanır. Puan kırılmadı."),
                sc(6, "Bakım (compaction, snapshot silme) yönetilir. 4 puan kırıldı: her kaynak için bir dönüştürme ve yükleme işi (Glue ya da Firehose) kurulur ve işletilir."),
                sc(7, "3 puan kırıldı: GB-ay 0,0282 USD, S3 Standard'dan (0,0245) yüksektir ve daha ucuz bir sınıfa geçiş yoktur; compaction ayrıca ödenir.")],
        "rs": [sc(3, "Redshift row'lar ve kolonlar saklar; JSON için SUPER tipi vardır. 7 puan kırıldı: dosya olarak saklama yoktur; ham dosya yüklemeden sonra kaybolur."),
               sc(4, "6 puan kırıldı: yerel table'larda şema yazarken uygulanır; yeni alan bir ALTER ve yükleme işinin değişmesidir (okurken şema sadece S3'teki external table'larda vardır)."),
               sc(6, "COPY toplu yüklemeyi iyi yapar. 4 puan kırıldı: yeniden gönderilen dosya için silme ve yeniden yükleme uygulamanın işidir."),
               sc(3, "7 puan kırıldı: süre sonu silmesi yoktur, silme bir DELETE ve VACUUM'dur; yeni dosya bir işi tetiklemez."),
               sc(9, "Serverless kapasiteyi yükle artırır. 1 puan kırıldı: günde 3.000 küçük dosyanın her biri ayrı bir COPY olursa yükleme kuyruğu uzar."),
               sc(10, "Managed storage kalıcıdır. Puan kırılmadı."),
               sc(5, "5 puan kırıldı: her kaynak için şema ve COPY işi yazılır ve işletilir; bu ekip için bir workgroup kurulur."),
               sc(5, "Managed storage GB-ay 0,0256 USD ile S3'e yakındır. 5 puan kırıldı: her yükleme RPU-saat harcar ve eski veri daha ucuz bir sınıfa geçmez.")],
    },
    h2h={
        "s3t": "Iceberg table storage'ı (S3 Tables) ile kafa kafaya. S3 Tables da S3'tür ama nesne değil table tutar: Iceberg table'ları, snapshot'ları ve otomatik compaction'ı vardır. "
               "Bu yüzden R1'de ayrı puanlanır ve ham bölgede geride kalır: dosya olduğu gibi saklanmaz, önce bir table'a çevrilir (R1 · VM), şema yazarken uygulanır (R1 · ŞE) "
               "ve dosya bazında olay bildirimi yerine yükleme işi commit eder (R1 · YD). Bir dönüştürme işi kurulur (R4) ve GB fiyatı biraz yüksektir (R5). "
               "S3 Tables'ın dürüst üstünlüğü temizlenmiş bölgededir: satır bazında güncelleme, silme ve compaction'lı sorgular. "
               "Hangi koşul değişseydi S3 Tables seçilirdi: iş ham dosyaları değil, temizlenmiş, şeması sabit ve satır bazında güncellenen table'ları tutmak olsaydı; o zaman VM ve ŞE satırları S3 Tables'ın lehine döner. Doğru mimaride ham bölge S3'te, temiz bölge S3 Tables'ta durur.",
        "rs": "Data warehouse (Redshift) ile kafa kafaya. Redshift bu verinin raporlarını en iyi çalıştıran engine'dir, ama ham bölge bir rapor deposu değil bir dosya arşividir. "
              "Redshift dosyayı row ve kolonlara çevirir ve ham dosya kaybolur (R1 · VM), yeni alan bir ALTER ve yükleme değişikliğidir (R1 · ŞE), "
              "yaşa göre ucuzlama ve süre sonu silmesi yoktur (R1 · YD). Her kaynak için bir COPY işi işletilir (R4) ve her yükleme compute harcar (R5). "
              "Redshift'in dürüst üstünlüğü bu dosyalardan beslenen düzenli raporlardadır; Spectrum aynı dosyaları S3'te yerinde de okur. "
              "Hangi koşul değişseydi Redshift seçilirdi: ham dosyalar saklanmak zorunda olmasaydı ve her gün aynı raporlar aynı kolonlar üzerinde çalışsaydı.",
    },
    verdict="Karar: S3 {s3}, S3 Tables {s3t}, Redshift {rs}. Ham bölgenin işi dosyayı olduğu gibi, yıllarca ve ucuz saklamak ve her yeni dosyada bir işi başlatmaktır: S3 R1'in 42 puanının tamamını alır. "
            "S3 seçtiğimizde artımız: her biçim kabul edilir (Ö1), şema okurken uygulanır, yeni dosya bir olay üretir (Ö8), lifecycle 90 gün sonra ucuzlatır ve beş yıl sonra siler (Ö6). "
            "Eksimiz: dosyanın içi sorgulanamaz; okuma için Athena ya da Spectrum gerekir ve sorgular partition prefix'iyle yazılmalıdır; küçük dosyalar istek başına ödenir. "
            "Doğru mimari üçü birliktedir: ham bölge S3'te, temiz table'lar S3 Tables'ta, düzenli raporlar Redshift'te. Bir koşul değişseydi: iş ham dosyaları değil, temizlenmiş, şeması sabit ve satır bazında güncellenen table'ları tutmak olsaydı S3 Tables öne geçerdi."))

# 4 ---------------------------------------------------------------- log archive
S3_W.append(wusecase("logs", 4, sim="w_logs",
    title="Uygulama log'larının iki yıllık arşivi: nadiren sorulan sorular",
    key="Key: logs/<servis>/yyyy/mm/dd/hh/<parça>.json.gz. Son 14 gün CloudWatch Logs'ta, arşiv iki yıl.",
    story="Lale Market'in bütün servisleri günde yaklaşık 50 GB log üretir. Son 14 günün log'ları olay anında CloudWatch Logs'ta aranır; bu kısım bugün çalışıyor ve değişmeyecek. "
          "Yeni kural log'ların iki yıl saklanmasını istiyor: iki yılın sonunda yaklaşık 36 TB. Arşive ayda yaklaşık beş soru gelir: güvenlik ekibi "
          "\"14 Mart'ta bu request id'nin bütün satırları\" ya da \"mart ayında bu IP'nin bütün 5xx cevapları\" diye sorar; cevabın birkaç dakikada gelmesi yeterlidir. "
          "Log'lar sadece eklenir, hiç değiştirilmez; iki yıl dolunca silinmelidir. Platform ekibi iki kişidir ve arşiv için yeni bir cluster istemiyor.",
    wnote="R1 toplam 40: arşivin sorusu tarih ve metin içinde aramadır (EY 12) ve iki yıllık yaşam döngüsü kuraldır (YD 12). R5 22 ile ikinci: 36 TB nadiren okunan veri iki yıl boyunca ödenir. "
          "R4 14: arşiv için yeni bir cluster istenmiyor.",
    rows=[row("VM", 8, "Log satırları metin ya da JSON'dır ve sıkıştırılmış saklanır.",
              "Satırlar JSON ya da düz metin olarak, sıkıştırılmış, kaybolmadan saklanmalı.",
              "Satırların biçimi değişirse eski satırlar yeni araçlarla okunamaz."),
          row("OY", 8, "Log sadece eklenir ve hiç değiştirilmez.",
              "Saniyede binlerce satır sürekli eklenmeli; yazılan satır değişmemeli.",
              "Ekleme yavaşsa log'lar uygulamada birikir ve bir çökmede kaybolur."),
          row("EY", 12, "Arşivin sorusu bir gün ya da ay içinde request id, IP ya da hata metni aramaktır.",
              "Soru tarih aralığı artı bir alan ya da metin içerir (request id, IP, \"5xx\"); ayda beş soru, cevap birkaç dakikada.",
              "Metin ve alan araması yapılamazsa güvenlik ekibi dosyaları indirir ve kendi makinesinde arar."),
          row("YD", 12, "İki yıl saklanmalı ve sonra silinmeli.",
              "Log iki yıl dolunca kendiliğinden silinmeli; silme kuralı log'u yazan uygulamadan bağımsız çalışmalı. 30 günden eski log'un daha ucuz bir sınıfa geçmesinin fiyatı R5'te sayılır.",
              "Silme kuralı yoksa saklama süresi aşılır ve bir temizlik işi yazılır."),
          row("R2", 12, "Günde 50 GB, iki yılda 36 TB.",
              "Günde 50 GB sürekli yazılmalı; bir aylık aralıktaki bir soru birkaç dakikada cevaplanmalı.",
              "Bir aylık sorgu saatler sürerse olay incelemesi gecikir."),
          row("R3", 12, "Denetim kanıtıdır; ama son 14 gün CloudWatch'ta ayrıca durur.",
              "Bir Availability Zone kaybında arşivden log kaybolmamalı.",
              "Kayıp log, denetimde boşluk demektir."),
          row("R4", 14, "İki kişilik platform ekibi yeni cluster istemiyor; CloudWatch Logs zaten çalışıyor.",
              "Arşiv için sunucu ya da cluster işletilmemeli; mevcut log akışına eklenmeli.",
              "Yeni bir cluster iki kişilik ekibin nöbet yükünü ikiye katlar."),
          row("R5", 22, "36 TB iki yıl boyunca her ay ödenir, ayda beş soru için.",
              "İki yılın sonunda 36 TB saklanır: GB-ay fiyatı düşük olmalı; sorgu sadece çalıştığında ödenmeli; ingestion zaten ödendiği için fark saklamada aranmalı.",
              "Arşiv sıcak fiyattan saklanırsa yılda binlerce dolar neredeyse hiç okunmayan veriye gider.")],
    cands=["s3", "cw", "os"],
    scores={
        "s3": [sc(10, "Sıkıştırılmış JSON dosyaları olduğu gibi saklanır (Ö1). Puan kırılmadı."),
               sc(9, "Firehose akışı beş dakikalık dosyalara böler ve her dosya yeni bir nesnedir. 1 puan kırıldı: object storage'da nesneye ekleme yoktur; akış dosya parçalarına bölünür."),
               sc(5, "Tarih prefix'i bir günü ya da ayı doğrudan seçer (Ö2). 5 puan kırıldı: object storage nesnenin içinde aramaz; request id ve metin araması Athena gibi ayrı bir sorgu motorunun dosyaları taramasıdır."),
               sc(10, "Lifecycle kuralı iki yıl sonra siler ve 30 gün sonra Glacier Instant Retrieval'a taşır (Ö6). Puan kırılmadı."),
               sc(10, "Günde 50 GB küçük bir yazma yüküdür; Athena aylık prefix'i paralel tarar. Puan kırılmadı."),
               sc(10, "En az üç Availability Zone. Puan kırılmadı."),
               sc(8, "Sunucu yoktur. 2 puan kırıldı: CloudWatch'tan Firehose'a bir subscription filter, Firehose teslimi, bir Glue table'ı ve bir Athena workgroup'u kurulur."),
               sc(10, "36 TB Glacier Instant Retrieval'da GB-ay 0,005 USD ile ayda yaklaşık 184 USD; Athena taranan TB başına yaklaşık 5 USD (Price List API ve Athena belgesi, 2026-10-31). Puan kırılmadı.")],
        "cw": [sc(10, "Log olayları metin ya da JSON olarak saklanır. Puan kırılmadı."),
               sc(10, "Log olayları log stream'e doğrudan eklenir. Puan kırılmadı."),
               sc(6, "Logs Insights request_id gibi alanlarda field index kullanır ve alanla sorgular. 4 puan kırıldı: message içinde kelime araması bir filter'dır ve zaman aralığındaki her satırı tarar; aralık iki yıla yaklaştıkça sorgu uzar (OpenSearch sayfasının log kartıyla aynı kırılım)."),
               sc(10, "Saklama süresi log group başına seçilir ve süre dolunca silinir. Puan kırılmadı; eski log'un daha ucuz bir yere geçmemesi R5'te sayıldı."),
               sc(10, "Günde 50 GB zaten bu servise yazılıyor. Puan kırılmadı."),
               sc(10, "Yönetilen servis, kalıcı saklama. Puan kırılmadı."),
               sc(10, "Zaten çalışıyor: saklama süresini 14 günden iki yıla çıkarmak bir ayardır. Puan kırılmadı."),
               sc(4, "Ingestion (GB başına 0,63 USD) zaten ödenir. 6 puan kırıldı: saklama GB-ay 0,0324 USD, Glacier Instant Retrieval'ın 6 katı; iki yılın sonunda ayda bin doların üzerindedir.")],
        "os": [sc(8, "Log satırları JSON document olur. 2 puan kırıldı: bir alanın type'ı ilk yazmada sabitlenir; yanlış tahmin edilen bir type reindex ister (OpenSearch sayfasının kademesi: yalnız yeni alan gelirse 2 puan; log'lara yeni alanlar eklenir)."),
               sc(9, "Toplu ekleme (bulk) iyi çalışır. 1 puan kırıldı: log'lar günlük index'lere döndürülür (rollover); shard planı R4'te sayıldı."),
               sc(10, "Inverted index metin ve alan aramasını saniyelerde yapar. Puan kırılmadı."),
               sc(10, "Index State Management index'leri yaşına göre siler. Puan kırılmadı; daha ucuz bir katman (UltraWarm, cold storage) ve iki yıllık index'lerin bedeli R5'te sayıldı."),
               sc(9, "1 puan kırıldı: kapasite sabittir; iki yılda 36 TB'a büyüyen veri için node'lar önceden eklenir (OpenSearch sayfasının kuralı; node ve shard planı R4'te sayıldı)."),
               sc(9, "Replica shard'lar ve saatlik otomatik snapshot. 1 puan kırıldı: domain kaybolursa son saatin log'ları CloudWatch'taki 14 günlük kopyadan dakikalar içinde yeniden yüklenir (OpenSearch sayfasının kuralı: dakikalar 1 puan)."),
               sc(5, "5 puan kırıldı: arşiv için yeni bir domain, düğüm tipleri, shard'lar ve ISM politikaları kurulur ve işletilir."),
               sc(1, "9 puan kırıldı: 36 TB'ı aranabilir tutan düğümler ve diskler saat başına ödenir; ayda beş soru için bütün yıl çalışır.")],
    },
    h2h={
        "cw": "İzleme servisi (CloudWatch Logs) ile kafa kafaya. CloudWatch Logs bu kartta engine uyumunda öndedir: satırlar doğrudan eklenir, Logs Insights alan ve metinle arar, "
              "saklama süresi bir ayardır (R1 35,2'ye 33,2; metin araması onda da zaman aralığını tarar). Sorgu ücretleri benzerdir: Athena TB başına yaklaşık 5 USD, Logs Insights GB başına 0,0063 USD, yani TB başına yaklaşık 6,5 USD. Zaten çalıştığı için R4'te de tam puan alır. Kaybettiği yer R5'tir: iki yıllık arşiv GB-ay 0,0324 USD ile saklanır, "
              "S3'te Glacier Instant Retrieval'a geçen aynı log 0,005 USD'dır; iki yılın sonunda fark ayda bin dolar civarındadır. "
              "Doğru mimari ikisi birliktedir: son 14 gün CloudWatch'ta aranır, kopyası Firehose ile S3'e akar ve iki yıl orada kalır. "
              "Hangi koşul değişseydi CloudWatch seçilirdi: saklama süresi birkaç ay olsaydı; o zaman saklanan veri ve R5 farkı küçülür, Firehose, Glue ve Athena kurma işi (R4) ise S3'ün tarafında kalırdı.",
        "os": "Search engine (OpenSearch) ile kafa kafaya. OpenSearch metin aramasında rakipsizdir: inverted index request id'yi ve hata metnini saniyelerde bulur (R1 · EY 10) ve bu kartta engine uyumunu kazanır (37,6). "
              "Ama bu kartın sorusu ayda beştir ve cevap için birkaç dakika yeterlidir. 36 TB'ı aranabilir tutmak önceden eklenen node'lar ister (R2), bir domain'in ve shard planının işletilmesi iki kişilik ekibe yük olur (R4) "
              "ve fatura ayda beş soru için bütün yıl ödenir (R5). OpenSearch'ün yeri son günlerin olay incelemesidir (OpenSearch sayfasının log kartları); iki yıllık arşivi aranabilir tutmak, nadiren açılan bir dolabı her gün aydınlatmaya benzer. "
              "Hangi koşul değişseydi OpenSearch seçilirdi: arşivde günde yüzlerce arama yapılsaydı ve cevabın saniyelerde gelmesi bir kural olsaydı.",
    },
    verdict="Karar: S3 {s3}, CloudWatch {cw}, OpenSearch {os}. Engine uyumunda OpenSearch (37,6) ve CloudWatch Logs (35,2) S3'ün (33,2) önündedir, ama iki yıllık arşivde kararı R5 verir. "
            "S3 seçtiğimizde artımız: lifecycle 30 gün sonra arşiv sınıfına taşır ve iki yıl sonra siler (Ö6), tarih prefix'i bir günü doğrudan seçer (Ö2), sorgu sadece çalıştığında ödenir. "
            "Eksimiz: S3 nesnenin içinde aramaz; uygulama Firehose, bir Glue table'ı ve Athena kurmalı ve sorguları tarih partition'ıyla yazmalıdır. "
            "Doğru mimari ikisi birliktedir: son 14 gün CloudWatch'ta, iki yıllık arşiv S3'te. Bir koşul değişseydi: saklama süresi birkaç ay olsaydı CloudWatch öne geçerdi."))

# 5 ---------------------------------------------------------------- seller uploads with presigned URLs
S3_W.append(wusecase("uploads", 5,
    title="Satıcı yüklemeleri: tarayıcıdan doğrudan, imzalı URL ile",
    key="Key: incoming/<satıcı id>/<yükleme id>/<dosya adı>. Tarayıcı imzalı bir PUT URL'siyle yükler; tarama sonrası media/ prefix'ine taşınır.",
    story="8.000 satıcı panelden fotoğraf, video ve PDF fatura yüklüyor: günde 30.000 dosya, kampanya açılışlarında saniyede 50 yükleme. Dosya 100 KB ile 2 GB arasıdır. "
          "Uygulama sunucusu dosyanın byte'larını taşımamalı: tarayıcı dosyayı doğrudan depoya yazmalı, uygulama sadece kısa ömürlü bir izin vermeli. "
          "Aynı adla ikinci bir yükleme ilkinin üstüne yazmamalı. Yüklenen dosya önce bir karantina prefix'ine (incoming/) düşer; virüs taraması dosya gelir gelmez başlamalı ve "
          "taranmamış dosyalar yedi gün sonra kendiliğinden silinmeli. Büyük videolar kesilirse kaldığı yerden devam etmeli. Satıcı dosyasının başka kopyası yoktur. "
          "Panel ekibi dört geliştiricidir; sunucu işletmek istemiyor.",
    wnote="R1 toplam 40: tarayıcının doğrudan yazıp okuması (EY 10), üstüne yazmama kuralı (TA 10) ve yüklemenin bir işi başlatması (YD 12) bu iş yükünün özüdür. "
          "R3 16 ile ikinci: satıcının dosyasının başka kopyası yoktur.",
    rows=[row("EY", 10, "Tarayıcı dosyayı uygulama sunucusundan geçirmeden yazmalı ve okumalı.",
              "Tarayıcı bir dosyayı kısa ömürlü bir izinle doğrudan depoya yazmalı ve indirmeli; izin tek bir key ve tek bir işlemle sınırlı olmalı.",
              "Byte'lar uygulama sunucusundan geçerse 2 GB'lık videolar sunucunun belleğini ve bant genişliğini doldurur."),
          row("TA", 10, "Aynı adla ikinci yükleme ilkinin üstüne yazmamalı; tarayıcı yazdığı dosyayı hemen görmeli.",
              "Yazma 'key yoksa yaz' koşuluyla yapılmalı; yazma biter bitmez tarama işi ve satıcı aynı dosyayı görmeli.",
              "Sessiz bir üstüne yazma bir satıcının faturasını başka bir dosyayla değiştirir."),
          row("OY", 8, "Videolar 2 GB'a kadar; kesilen yükleme baştan başlamamalı.",
              "Büyük dosya parçalar hâlinde, paralel ve kaldığı yerden devam ederek yüklenmeli; dosyanın içi sonradan değişmez.",
              "Kesilen 2 GB'lık bir yükleme baştan başlarsa satıcı paneli terk eder."),
          row("YD", 12, "Tarama dosya gelir gelmez başlamalı; taranmamış dosya yedi gün sonra silinmeli.",
              "Yeni dosya bir olayla tarama işini başlatmalı; karantinada kalan dosya yedi gün sonra kendiliğinden silinmeli.",
              "Tetikleyici yoksa bir zamanlayıcı karantinayı tarar ve taranmamış bir dosya müşteriye ulaşabilir."),
          row("R2", 14, "Günde 30.000 dosya, kampanya anında saniyede 50 yükleme.",
              "Saniyede 50 eşzamanlı yükleme ve 2 GB'lık dosyalar; kapasite planlanmamalı.",
              "Tepe anında yüklemeler reddedilirse satıcılar kampanyaya geç kalır."),
          row("R3", 16, "Satıcının dosyasının başka kopyası yoktur.",
              "Bir Availability Zone kaybında hiçbir yüklenen dosya kaybolmamalı.",
              "Kaybolan bir fatura ya da ürün videosu satıcının yeniden yüklemesi ve güven kaybıdır."),
          row("R4", 15, "Dört geliştirici sunucu işletmek istemiyor.",
              "Sunucusuz çalışmalı; tarayıcı yüklemesi için gereken ayar az olmalı.",
              "Yükleme sunucuları ekibin nöbet listesini uzatır."),
          row("R5", 15, "Günde 30.000 dosya ve sürekli büyüyen bir arşiv.",
              "Günde 30.000 PUT ve büyüyen bir arşiv: GB başına ve istek başına ödenmeli; sunucu saati ödenmemeli.",
              "Saat başına ödenen yükleme sunucuları gece boş durur.")],
    cands=["s3", "s3x", "efs"],
    scores={
        "s3": [sc(10, "Uygulama tek bir key ve tek bir işlem için imzalı bir PUT ya da GET URL'si üretir; tarayıcı doğrudan bucket'a yazar ve okur (Ö9). Puan kırılmadı."),
               sc(10, "PUT If-None-Match: * key varsa 412 ile reddedilir; güçlü tutarlılık yeni nesneyi hemen gösterir (Ö4). Puan kırılmadı."),
               sc(10, "Çok parçalı yükleme parçaları paralel ve kaldığı yerden yükler (Ö1). Puan kırılmadı."),
               sc(10, "Yeni nesne bir olay bildirimiyle taramayı başlatır (Ö8); lifecycle kuralı incoming/ prefix'ini yedi gün sonra siler (Ö6). Puan kırılmadı."),
               sc(10, "Prefix başına saniyede en az 3.500 yazma; saniyede 50 yükleme küçük bir yüktür. Puan kırılmadı."),
               sc(10, "En az üç Availability Zone. Puan kırılmadı."),
               sc(9, "Sunucusuz. 1 puan kırıldı: tarayıcı yüklemesi için bucket'a bir CORS kuralı yazılır."),
               sc(10, "GB-ay 0,0245 USD ve 1.000 PUT için 0,0054 USD; sunucu yoktur. Puan kırılmadı.")],
        "s3x": [sc(6, "Directory bucket aynı S3 API'sini kullanır. 4 puan kırıldı: istekler CreateSession ile alınan oturum yetkisiyle Zonal endpoint'e gider; bu sayfa directory bucket için tarayıcıya verilecek imzalı URL'yi belgede doğrulamadı ve kısa ömürlü izin bu oturum modeline göre kurulur."),
                sc(10, "Koşullu yazma ve güçlü tutarlılık vardır. Puan kırılmadı."),
                sc(10, "Çok parçalı yükleme vardır. Puan kırılmadı."),
                sc(5, "Lifecycle süre sonu silmesi vardır. 5 puan kırıldı: directory bucket'ta S3 Event Notifications yoktur; tarama işi yeni dosyayı başka bir yoldan öğrenir."),
                sc(10, "Directory bucket varsayılan olarak saniyede 100.000 yazmaya kadar ölçeklenir. Puan kırılmadı."),
                sc(4, "6 puan kırıldı: veri tek bir Availability Zone'dadır; o AZ'nin kaybında satıcının tek kopyası kaybolabilir."),
                sc(9, "Sunucusuz. 1 puan kırıldı: bucket bir AZ'de oluşturulur ve istemciler o AZ'nin Zonal endpoint'ini kullanır (oturum yetkisi R1.1'de sayıldı)."),
                sc(4, "6 puan kırıldı: GB-ay 0,118 USD, S3 Standard'ın yaklaşık 5 katı; hız bu iş yükünde bir şey kazandırmaz.")],
        "efs": [sc(2, "8 puan kırıldı: tarayıcı bir NFS dosya sistemine yazamaz ve imzalı bir izin yoktur; yazma da okuma da bir uygulama sunucusundan geçer (kademe: sadece okuma bir sunucudan geçiyorsa 3, tarayıcının doğrudan yazması isteniyorsa 8)."),
                sc(8, "O_CREAT ve O_EXCL ile 'yoksa oluştur' yapılır. 2 puan kırıldı: başka bir istemci dosyayı ancak yazan onu kapattıktan sonra tam görür (close-to-open)."),
                sc(6, "4 puan kırıldı: dosya sisteminde parça parça, kaldığı yerden devam eden bir yükleme işlemi yoktur; kesilen 2 GB'lık yüklemenin devam mantığını uygulama yazar."),
                sc(2, "8 puan kırıldı: dosya sisteminde olay bildirimi ve süre sonu silmesi yoktur; tarama tetikleyicisi ve temizlik işi uygulamada yazılır."),
                sc(9, "Elastic throughput yükle büyür. 1 puan kırıldı: her yükleme bir web sunucusundan geçer ve web sunucuları tepe için önceden eklenen sabit kapasitedir (sunucuların işletilmesi R4'te)."),
                sc(10, "Regional EFS birden fazla Availability Zone'da saklar. Puan kırılmadı."),
                sc(4, "6 puan kırıldı: yükleme sunucuları, mount target'lar, yamalar ve sunucu sayısı ekibin işidir."),
                sc(3, "7 puan kırıldı: Standard storage GB-ay 0,36 USD, S3 Standard'ın yaklaşık 15 katı; yükleme sunucuları saat başına ödenir.")],
    },
    h2h={
        "s3x": "Tek AZ'li object storage (S3 Express One Zone) ile kafa kafaya. S3 Express One Zone aynı S3 API'sini kullanır ve tek haneli milisaniyelerde cevap verir; "
               "koşullu yazma ve çok parçalı yükleme onda da vardır. Ama farklı bir bucket türüdür: olay bildirimi yoktur (R1 · YD), istekler oturum tabanlı yetkiyle Zonal endpoint'e gider (R1 · EY) "
               "ve veri tek bir Availability Zone'da durur; satıcının tek kopyası için bu ciddi bir risktir (R3). GB fiyatı da yaklaşık beş katıdır (R5). "
               "Bu iş yükü hız istemez, dayanıklılık ve tetikleyici ister. "
               "Hangi koşul değişseydi S3 Express One Zone seçilirdi: yüklenen dosyalar aynı AZ'deki bir işlem kümesinin saniyede binlerce kez okuduğu geçici ara dosyalar olsaydı ve kaynağı başka yerde dursaydı.",
        "efs": "Paylaşılan dosya sistemi (EFS) ile kafa kafaya. EFS dosyayı kalıcı ve birden fazla AZ'de saklar (R3 eşit) ve 'yoksa oluştur' kuralını O_EXCL ile verir. "
               "Ama bu kartın özü tarayıcının doğrudan yazmasıdır ve bir NFS dosya sistemine tarayıcı yazamaz: her byte bir uygulama sunucusundan geçer (R1 · EY 2). "
               "Olay bildirimi ve süre sonu silmesi yoktur (R1 · YD), sunucuları ekip işletir (R4) ve GB fiyatı yaklaşık 15 katıdır (R5). EFS'in dürüst üstünlüğü, dosyayı açıp yerinde değiştiren sunucu programlarıdır (kart 6). "
               "Hangi koşul değişseydi EFS seçilirdi: dosyaları tarayıcı değil, aynı VPC'deki sunucularda çalışan ve dosya yolu bekleyen bir program yükleseydi ve dosyayı yerinde düzenleseydi.",
    },
    verdict="Karar: S3 {s3}, S3 Express One Zone {s3x}, EFS {efs}. S3 R1'in 40 puanının tamamını alır: imzalı URL tarayıcıya tek bir key için kısa bir izin verir, If-None-Match üstüne yazmayı engeller, "
            "yeni nesne taramayı başlatır ve lifecycle karantinayı temizler. "
            "S3 seçtiğimizde artımız: uygulama sunucusu byte taşımaz (Ö9), kesilen video kaldığı yerden devam eder (Ö1), sunucu yoktur. "
            "Eksimiz: imzalı URL'yi taşıyan herkes onu süresi dolana kadar kullanabilir; uygulama süreyi dakikalarla sınırlamalı, URL'yi log'lamamalı ve dosya türünü tarama sonrası kendisi doğrulamalıdır. "
            "Bir koşul değişseydi: dosyalar aynı AZ'deki bir işlem kümesinin geçici ara dosyaları olsaydı S3 Express One Zone öne geçerdi."))

# 6 ---------------------------------------------------------------- shared working directory (clear loss)
S3_W.append(wusecase("shared", 6, sim="w_shared",
    title="Görsel düzenleme sunucularının ortak çalışma klasörü",
    key="Yol: /work/<iş id>/<dosya>. Dosya açılır, ortasından değiştirilir, sonuna eklenir, geçici adla yazılıp yeniden adlandırılır, kilitlenir.",
    story="Lale Market eski bir görsel düzenleme uygulamasını devraldı: altı EC2 sunucusunda çalışan bir PHP ve ImageMagick programı. Program dosyaları bir yol ile açar, "
          "büyük TIFF dosyalarının ortasındaki katmanları yerinde değiştirir, iş günlüğünü bir dosyanın sonuna ekler, sonucu geçici bir adla yazıp yeniden adlandırır "
          "ve iki sunucunun aynı dosyayı aynı anda düzenlemesini bir dosya kilidiyle önler. Çalışma kümesi 2 TB'tır; dosyalar 1 MB ile 200 MB arasıdır. "
          "Bir günün düzenlemeleri kaybolursa tasarım ekibi o günü yeniden yapar. Kodun yeniden yazılması için altı ay bütçe yok; ekip programı olduğu gibi taşımak istiyor.",
    wnote="R1 toplam 42: programın yaptığı yerinde yazma, ekleme ve yeniden adlandırma (OY 14) ve dosya kilidi (TA 12) bu iş yükünün özüdür. "
          "R4 20 ile ikinci: kod değişemez, bu yüzden programın beklediği arayüz (yol ve POSIX çağrıları) bir operasyon şartıdır.",
    rows=[row("OY", 14, "Program dosyanın ortasını değiştirir, sonuna ekler ve yeniden adlandırır.",
              "Bir dosyanın ortasındaki byte'lar yerinde değişmeli, sonuna ekleme yapılmalı, geçici dosya tek adımda yeniden adlandırılmalı.",
              "Her küçük değişiklik bütün dosyanın yeniden yazılması olursa 200 MB'lık bir TIFF'in bir katmanı için 200 MB yazılır."),
          row("TA", 12, "İki sunucu aynı dosyayı aynı anda düzenlememeli.",
              "Bir sunucu dosyayı kilitleyebilmeli; diğer sunucu kilidi görmeli; kapatılan dosyanın son hâli diğer sunucularda görünmeli.",
              "Kilit yoksa iki sunucunun değişikliği birbirini ezer ve düzenleme kaybolur."),
          row("EY", 10, "Program dosyaları bir yol ve klasör listesiyle bulur.",
              "Dosyalar /work/<iş id>/ gibi bir yolla açılmalı; klasör listelenmeli ve yeniden adlandırılabilmeli.",
              "Yol yoksa programın her dosya çağrısı değişir."),
          row("VM", 6, "Dosyalar 1 MB ile 200 MB arası TIFF ve PNG'dir.",
              "200 MB'a kadar binary dosyalar olduğu gibi saklanmalı.",
              "Dosya boyutu sınırlanırsa büyük işler bölünür."),
          row("R2", 12, "Altı sunucu, 2 TB çalışma kümesi, gün içinde sürekli okuma ve yazma.",
              "Altı sunucu aynı anda okuyup yazmalı; küçük okumalar düşük gecikmeli olmalı.",
              "Her küçük okuma yavaşsa bir düzenleme dakikalar sürer."),
          row("R3", 12, "Bir günün düzenlemeleri kaybolursa o gün yeniden yapılır.",
              "Bir Availability Zone kaybında çalışma dosyaları kaybolmamalı.",
              "Kayıp bir gün, tasarım ekibinin bir günü demektir."),
          row("R4", 20, "Kod altı ay değişemez; program olduğu gibi taşınmalı.",
              "Program kod değişmeden çalışmalı: aynı yollar, aynı dosya çağrıları, aynı kilitler.",
              "Kodun yeniden yazılması altı aylık bir projedir ve bütçesi yoktur."),
          row("R5", 14, "2 TB çalışma kümesi; eski işler nadiren açılır.",
              "2 TB her ay saklanır: GB-ay fiyatı makul olmalı; nadiren açılan eski işler daha ucuz bir sınıfa geçebilmeli.",
              "Pahalı bir depo 2 TB'ı her ay pahalı tutar.")],
    cands=["efs", "s3", "s3x"],
    scores={
        "efs": [sc(10, "NFS dosyanın ortasına yazmayı, sonuna eklemeyi ve tek adımda yeniden adlandırmayı verir. Puan kırılmadı."),
                sc(9, "NFS v4 dosya kilitleri ve close-to-open tutarlılık vardır. 1 puan kırıldı: kilitler advisory'dir; kilidi kontrol etmeyen bir program onu görmez."),
                sc(10, "Yol, klasör listesi ve klasör yeniden adlandırma vardır. Puan kırılmadı."),
                sc(10, "Dosya boyutu bu iş yükü için sınır değildir. Puan kırılmadı."),
                sc(9, "Altı sunucu aynı dosya sistemini paylaşır ve throughput yükle büyür. 1 puan kırıldı: çok sayıda küçük metadata işlemi gecikmeyi büyütür."),
                sc(10, "Regional EFS birden fazla Availability Zone'da saklar. Puan kırılmadı."),
                sc(10, "Altı sunucu dosya sistemini mount eder; kod değişmez. Puan kırılmadı."),
                sc(6, "4 puan kırıldı: 2 TB Standard'da GB-ay 0,36 USD ile ayda yaklaşık 737 USD; lifecycle eski dosyaları Infrequent Access'e (0,0266) taşıyarak bunu azaltır.")],
        "s3": [sc(2, "8 puan kırıldı: object storage'da nesnenin ortasına yazma, sonuna ekleme ve yeniden adlandırma yoktur; her değişiklik bütün nesnenin yeniden yazılmasıdır (Ö1), yeniden adlandırma kopyala ve sil'dir."),
               sc(4, "Güçlü tutarlılık ve koşullu yazma (If-Match) vardır (Ö4). 6 puan kırıldı: dosya kilidi yoktur; iki yazıcının yarışını uygulama ETag ile kendisi çözer."),
               sc(6, "Prefix ile listeleme sıralıdır (Ö2). 4 puan kırıldı: klasör gerçek değildir; klasörü yeniden adlandırmak altındaki her nesneyi kopyalayıp silmektir."),
               sc(10, "Nesne 50 TB'a kadar olabilir (Ö1). Puan kırılmadı."),
               sc(8, "Bucket yükle ölçeklenir. 2 puan kırıldı: her küçük okuma ayrı bir HTTP isteğidir; çok sayıda küçük okuma dosya sistemine göre yavaştır."),
               sc(10, "En az üç Availability Zone. Puan kırılmadı."),
               sc(2, "8 puan kırıldı: program S3 API'sine yeniden yazılmalıdır; bir mount aracı yerinde yazmayı ve kilidi vermez."),
               sc(9, "2 TB × 0,0245 USD ayda yaklaşık 50 USD. 1 puan kırıldı: her küçük okuma ve yazma istek başına ödenir.")],
        "s3x": [sc(5, "Directory bucket'ta nesneye ekleme (write offset) ve tek adımda RenameObject vardır. 5 puan kırıldı: nesnenin ortasına yazma yoktur; katman değişikliği bütün nesnenin yeniden yazılmasıdır."),
                sc(4, "Güçlü tutarlılık ve koşullu yazma vardır. 6 puan kırıldı: dosya kilidi yoktur."),
                sc(7, "Directory bucket klasörleri hiyerarşik tutar. 3 puan kırıldı: POSIX izinleri ve yol semantiği yoktur; liste sıralı da değildir."),
                sc(10, "Dosya boyutu sınır değildir. Puan kırılmadı."),
                sc(10, "Tek haneli milisaniye gecikme, aynı AZ'deki sunucular için tasarlanmış. Puan kırılmadı."),
                sc(4, "6 puan kırıldı: veri tek bir Availability Zone'dadır; o AZ'nin kaybında çalışma dosyalarının tek kopyası kaybolabilir."),
                sc(3, "7 puan kırıldı: program S3 API'sine ya da bir mount aracının sınırlı semantiğine göre değiştirilir; kilit kodda yeniden yazılır."),
                sc(7, "3 puan kırıldı: 2 TB × 0,118 USD ayda yaklaşık 242 USD; eski işler daha ucuz bir sınıfa geçmez.")],
    },
    h2h={
        "s3": "Object storage (S3) ile kafa kafaya. Bu sayfanın servisi burada net kaybeder ve kaybı engine'den gelir: nesne bir bütündür. Ortasına yazma, sonuna ekleme, "
              "yeniden adlandırma ve dosya kilidi yoktur (R1 · OY 2, TA 4). Programın her çağrısı değişmek zorundadır (R4 2). "
              "S3'ün dürüst üstünlükleri burada da geçerlidir: 2 TB ayda yaklaşık 50 USD'dır (R5), veri üç AZ'de durur (R3) ve sınırsız büyür. "
              "Ama bu iş yükü bir dosya sistemi bekliyor ve kod değişemiyor. "
              "Hangi koşul değişseydi S3 seçilirdi: program yeniden yazılsaydı ve her işi 'oku, işle, sonucu yeni bir nesne olarak yaz' biçiminde yapsaydı; o zaman S3 daha ucuz ve daha dayanıklı olurdu.",
        "s3x": "Tek AZ'li object storage (S3 Express One Zone) ile kafa kafaya. S3 Express One Zone S3'ün dosya sistemine en yakın biçimidir: hiyerarşik klasörler, nesneye ekleme ve tek adımda yeniden adlandırma vardır, "
               "gecikme tek haneli milisaniyedir (R2). Ama nesnenin ortasına yazma ve dosya kilidi yine yoktur (R1 · OY, TA), kod değişir (R4) "
               "ve çalışma dosyaları tek bir AZ'de durur (R3). Bu yüzden toplamda S3 ile neredeyse eşittir ve EFS'in çok gerisindedir. "
               "Hangi koşul değişseydi S3 Express One Zone seçilirdi: program yeni yazılsaydı, dosyaları sadece sonuna ekleyip yeniden adlandırsaydı, kilide ihtiyaç duymasaydı ve hız ana şart olsaydı.",
    },
    verdict="Karar: EFS {efs}, S3 {s3}, S3 Express One Zone {s3x}. EFS R1'in 42 puanının 40,8'ini alır: yerinde yazma, ekleme, yeniden adlandırma ve dosya kilidi bir dosya sisteminin çekirdeğidir. "
            "Yine de S3 seçersek artımız: 2 TB ayda yaklaşık 50 USD (Ö1), sınırsız büyüme, üç AZ, sürümler (Ö5). "
            "Eksimiz: program yeniden yazılır; her katman değişikliği bütün dosyanın yeniden yazılmasıdır; kilidi uygulama ETag ve koşullu yazma (Ö4) ile kendisi kurar. "
            "Bir koşul değişseydi: program 'oku, işle, yeni nesne yaz' biçiminde yeniden yazılsaydı S3 öne geçerdi."))

# 7 ---------------------------------------------------------------- product videos with lifecycle
S3_W.append(wusecase("videos", 7,
    title="Ürün videoları: ilk ay çok izlenir, sonra soğur",
    key="Key: videos/<ürün id>/<çözünürlük>.mp4. Oynatıcı byte aralıklarıyla okur. Intelligent-Tiering ya da yaşa göre lifecycle; ürün silinince video silinir.",
    story="Lale Market'te 15.000 ürün videosu var: her biri 30 MB ile 300 MB arası, toplam yaklaşık 1,8 TB; her ay 600 yeni video ekleniyor. "
          "Bir video ilk 30 gün çok izlenir, 90 günden sonra nadiren açılır. Oynatıcı videoyu baştan sona indirmez; byte aralıklarıyla parça parça okur ve kullanıcı ileri sardığında ortadan başlar. "
          "Önünde CloudFront vardır; kampanya günlerinde izlenme on katına çıkar. Satıcının videosunun başka kopyası yoktur. "
          "Bir ürün katalogdan kaldırılınca videosu da silinmeli. Hangi videonun ne zaman soğuyacağı önceden bilinmiyor. Ekip sunucu işletmek istemiyor.",
    wnote="R1 toplam 42: videonun yaşa göre kendiliğinden ucuzlaması ve silinmesi (YD 14) ve byte aralığıyla okunması (EY 12) bu iş yükünün engine sorularıdır. "
          "R5 18 ile ikinci: ilk aydan sonra videoların çoğu soğuktur.",
    rows=[row("VM", 10, "Değer 30 MB ile 300 MB arası bir video dosyasıdır.",
              "300 MB'a kadar video dosyaları olduğu gibi saklanmalı.",
              "Dosya bölünerek saklanırsa oynatıcı parçaları kendisi birleştirir."),
          row("EY", 12, "Oynatıcı videoyu byte aralıklarıyla okur ve ortadan başlayabilir.",
              "Video key ile bir URL'den, istenen byte aralığı kadar okunmalı; ileri sarmada ortadan başlanabilmeli.",
              "Aralık okuması yoksa her ileri sarmada bütün dosya iner."),
          row("YD", 14, "Video ilk ay sıcak, sonra soğuk; ne zaman soğuyacağı bilinmiyor; silinen videonun izi kalmamalı.",
              "Okunmayan video bir kuralla kendiliğinden başka bir katmana geçmeli ve okununca geri gelmeli; uygulama bir ürünün videosunu silince eski sürümü de bir kuralla temizlenmeli. Katmanlar arasındaki fiyat farkı R5'te sayılır.",
              "Kural yoksa uygulama her videonun okunma zamanını izler ve taşır; eski sürümler birikir."),
          row("OY", 6, "Video bir kez yüklenir, değişmez.",
              "Bir kez yaz, çok kez oku.",
              "Okuma yolu yazma kilidi beklerse oynatıcı takılır."),
          row("R2", 14, "Kampanya günlerinde izlenme on katına çıkar.",
              "CloudFront arkasında kampanya anında on kat okuma karşılanmalı; kapasite planlanmamalı.",
              "Kaynak tepe anında yavaşlarsa önbellekte olmayan videolar takılır."),
          row("R3", 14, "Satıcının videosunun başka kopyası yoktur.",
              "Bir Availability Zone kaybında hiçbir video kaybolmamalı.",
              "Kaybolan bir video ürün sayfasının boş kalmasıdır."),
          row("R4", 12, "Ekip sunucu işletmek istemiyor.",
              "Sunucusuz; CloudFront doğrudan depodan okumalı.",
              "Bir video sunucu katmanı ekibe nöbet getirir."),
          row("R5", 18, "1,8 TB'ın çoğu ilk aydan sonra soğuktur.",
              "1,8 TB saklanır ve her ay 600 video eklenir: soğuk video düşük GB-ay fiyatından ödenmeli; sıcak video için ek ücret küçük olmalı.",
              "Bütün videolar sıcak fiyattan saklanırsa fatura gereksiz yere katlanır.")],
    cands=["s3", "efs", "s3x"],
    scores={
        "s3": [sc(10, "Nesne 50 TB'a kadar olabilir (Ö1). Puan kırılmadı."),
               sc(10, "GET isteği Range başlığıyla istenen byte aralığını döndürür (Ö1). Puan kırılmadı."),
               sc(10, "Intelligent-Tiering okunmayan nesneyi kendiliğinden ucuz katmana taşır ve okununca geri getirir (Ö6); uygulamanın sildiği videonun eski sürümünü lifecycle kuralı temizler (Ö5, Ö6). Puan kırılmadı."),
               sc(10, "Bir kez yazılır; okumalar kilit beklemez (Ö1). Puan kırılmadı."),
               sc(10, "Prefix başına saniyede en az 5.500 GET; CloudFront önbelleği kaynağı korur. Puan kırılmadı."),
               sc(10, "En az üç Availability Zone. Puan kırılmadı."),
               sc(9, "Sunucusuz. 1 puan kırıldı: CloudFront için origin access control ve bucket policy yazılır."),
               sc(10, "1,8 TB Standard'da ayda yaklaşık 45 USD'dır; Intelligent-Tiering soğuyan videoları daha ucuz katmana taşır. Puan kırılmadı.")],
        "efs": [sc(10, "Dosya olduğu gibi saklanır. Puan kırılmadı."),
                sc(7, "Dosyanın ortasından okumak dosya sisteminin temel işidir. 3 puan kırıldı: dosya bir HTTP URL'si değildir; tarayıcıya ve CloudFront'a bir web sunucusu üzerinden gider."),
                sc(10, "EFS lifecycle okunmayan dosyayı Infrequent Access ve Archive sınıflarına taşır ve okununca geri getirir; sürüm olmadığı için uygulamanın sildiği dosya hemen gider. Puan kırılmadı."),
                sc(10, "Bir kez yazılır. Puan kırılmadı."),
                sc(9, "Elastic throughput yükle büyür. 1 puan kırıldı: her kaynak isteği bir web sunucusundan geçer ve web sunucuları tepe için önceden eklenen sabit kapasitedir (sunucuların işletilmesi R4'te)."),
                sc(10, "Regional EFS birden fazla AZ'de saklar. Puan kırılmadı."),
                sc(4, "6 puan kırıldı: EC2 web sunucuları, mount target'lar, yamalar ve sunucu sayısı ekibin işidir."),
                sc(4, "6 puan kırıldı: sıcak dosyalar GB-ay 0,36 USD'dan ödenir, soğuyanlar Infrequent Access'e geçer; web sunucuları saat başına ödenir.")],
        "s3x": [sc(10, "Nesne olarak saklanır. Puan kırılmadı."),
                sc(10, "Byte aralığıyla okuma tek haneli milisaniyededir. Puan kırılmadı."),
                sc(4, "6 puan kırıldı: directory bucket'ta okunmaya ya da yaşa göre katman geçişi yoktur; sadece yaşa göre süre sonu silmesi vardır."),
                sc(10, "Bir kez yazılır. Puan kırılmadı."),
                sc(9, "Yüksek istek hızı için tasarlanmıştır. 1 puan kırıldı: veri tek AZ'dedir; diğer AZ'lerden gelen okumalar AZ'ler arası trafiktir."),
                sc(4, "6 puan kırıldı: veri tek bir Availability Zone'dadır; o AZ'nin kaybında satıcının tek kopyası kaybolabilir."),
                sc(9, "Sunucusuz. 1 puan kırıldı: bucket bir AZ'de oluşturulur ve istemciler o AZ'nin Zonal endpoint'ini kullanır."),
                sc(3, "7 puan kırıldı: 1,8 TB × 0,118 USD ayda yaklaşık 217 USD, Standard'ın yaklaşık 5 katı; soğuyan video ucuzlamaz.")],
    },
    h2h={
        "efs": "Paylaşılan dosya sistemi (EFS) ile kafa kafaya. EFS dosyanın ortasından okumayı doğal olarak yapar ve kendi lifecycle'ıyla okunmayan dosyayı ucuz sınıflara taşır; "
               "veri birden fazla AZ'dedir (R3 eşit). Ama tarayıcı ve CloudFront bir dosya sistemine doğrudan ulaşamaz: her istek bir web sunucusundan geçer (R1 · EY, R2, R4). "
               "R1 · YD'de iki aday eşittir: ikisi de okunmayan dosyayı bir kuralla ucuz katmana taşır. Sıcak dosyalar ise EFS'te GB-ay 0,36 USD'dan ödenir (R5). Toplamda fark S3'ün çekirdek özelliklerinden değil, tarayıcıya giden yoldan ve fiyattan gelir. "
               "Hangi koşul değişseydi EFS seçilirdi: videoları tarayıcılar değil, aynı VPC'deki bir transcode programı yerinde düzenleseydi ve program dosya yolu bekleseydi.",
        "s3x": "Tek AZ'li object storage (S3 Express One Zone) ile kafa kafaya. S3 Express One Zone byte aralıklarını en hızlı okuyan S3 biçimidir. "
               "Ama video için hız CloudFront'un önbelleğinden gelir; kaynakta milisaniyeler kazandırmaz. Directory bucket'ta okunmaya ya da yaşa göre katman geçişi yoktur (R1 · YD), "
               "veri tek bir AZ'dedir ve satıcının tek kopyası için risktir (R3), GB fiyatı Standard'ın yaklaşık beş katıdır (R5). Hızın kendisi doğru bir özelliktir, ama bu iş yükünün darboğazı değildir. "
               "Hangi koşul değişseydi S3 Express One Zone seçilirdi: videolar aynı AZ'deki bir işleme kümesinin saniyede binlerce kez okuduğu geçici kareler olsaydı ve asıl kopya S3 Standard'da dursaydı.",
    },
    verdict="Karar: S3 {s3}, EFS {efs}, S3 Express One Zone {s3x}. S3 R1'in 42 puanının tamamını alır: byte aralığıyla okuma ve okunmayan nesneyi kendiliğinden ucuzlatan sınıf yönetimi S3'ün çekirdeğidir. "
            "S3 seçtiğimizde artımız: CloudFront doğrudan bucket'tan okur (Ö1), Intelligent-Tiering ne zaman soğuyacağı bilinmeyen videoları kendisi taşır (Ö6), silinen videonun eski sürümünü lifecycle temizler (Ö5). "
            "Eksimiz: Intelligent-Tiering nesne başına küçük bir izleme ücreti alır; uygulama ürün silinince videoyu silmeyi bir olay işleyicisine bağlamalıdır. "
            "Bir koşul değişseydi: videoları bir dosya yolu bekleyen bir program düzenleseydi EFS öne geçerdi."))

# 8 ---------------------------------------------------------------- compliance archive (WORM)
S3_W.append(wusecase("compliance", 8,
    title="Denetim kayıtlarının değiştirilemez arşivi: yedi yıl, kimse silemez",
    key="Key: audit/dt=YYYY-MM-DD/<parça>.parquet. Object Lock compliance modu, yedi yıl. İlk yıl Keyspaces'te çevrim içi (Keyspaces sayfası kart 4).",
    story="Lale Market'in denetim kayıtları ilk yıl Keyspaces'te çevrim içi tutulur ve denetçi \"bu hesabın son 90 günü\" sorusunu orada saniyeler içinde sorar (Keyspaces sayfasının 4. kartı). "
          "Bir yılı geçen kayıtlar her gece bir Parquet dosyası olarak arşive taşınır: yılda yaklaşık 3 TB, yedi yılda 21 TB. Düzenleyici kurum yedi yıl boyunca kayıtların "
          "hiç kimse tarafından, yönetici hesabı dahil, silinememesini ve değiştirilememesini istiyor; yedi yıl dolunca silinmeleri gerekiyor. Bir soruşturma açılırsa ilgili günler "
          "soruşturma bitene kadar silinmemeli. Denetçi yılda yaklaşık on kez bir tarih aralığı ister, bazen içinde bir hesap id'si arar; cevap için 24 saat vardır.",
    wnote="R1 toplam 40: yedi yıllık saklama, süre sonu silmesi ve soruşturma kilidi (YD 16) ve kimsenin silememesi (TA 10) bu arşivin engine sorularıdır. "
          "R5 22 ile ikinci: 21 TB yedi yıl ödenir ve nadiren okunur.",
    rows=[row("YD", 16, "Yedi yıl saklama, sonra silme; soruşturmada süresiz kilit.",
              "Her dosya yedi yıl saklanmalı ve sonra kendiliğinden silinmeli; soruşturma açılan günler süresi dolsa bile silinmemeli.",
              "Erken silinen kayıt bir düzenleme ihlali, geç silinen kayıt bir saklama kuralı ihlalidir."),
          row("TA", 10, "Yönetici dahil hiç kimse kaydı silememeli ya da değiştirememeli.",
              "Yazılan dosya saklama süresi boyunca hiçbir kullanıcı, yönetici hesabı dahil, tarafından silinememeli ya da üstüne yazılamamalı; kuralı engine uygulamalı.",
              "Yetkisi olan bir kişinin silebildiği bir arşiv denetimde kanıt sayılmaz."),
          row("EY", 8, "Denetçi bir tarih aralığı ister, bazen bir hesap id'si arar.",
              "Bir tarih aralığı doğrudan seçilmeli; o aralıkta bir hesap id'si birkaç dakikada bulunmalı; yılda on soru.",
              "Tarih aralığı seçilemezse her soru bütün arşivi okur."),
          row("VM", 6, "Kayıtlar günlük Parquet dosyalarıdır.",
              "Günlük dosyalar olduğu gibi saklanmalı; içindeki şema yıllar içinde değişebilir.",
              "Dosya biçimi değişince eski yıllar okunamaz hâle gelir."),
          row("R2", 8, "Yılda 3 TB yazma, yılda on soru.",
              "Gece bir dosya yazılmalı; on soru 24 saat içinde cevaplanmalı.",
              "Arşivin yavaş olması 24 saatlik sürede sorun değildir; yazılamaması sorundur."),
          row("R3", 16, "Arşiv denetimin tek kanıtıdır.",
              "Bir Availability Zone kaybında hiçbir dosya kaybolmamalı.",
              "Kaybolan kayıt denetimde açıklanamayan bir boşluktur."),
          row("R4", 14, "Ekip Keyspaces ile S3'ü zaten işletiyor; yeni bir sistem istemiyor.",
              "Arşiv sunucu ve cluster olmadan işletilmeli; kuralın kurulması bir kez yapılmalı.",
              "Yeni bir arşiv sistemi yedi yıl boyunca işletilecek bir sistem daha demektir."),
          row("R5", 22, "21 TB yedi yıl boyunca ödenir ve yılda on kez okunur.",
              "Yedi yılda 21 TB saklanır: GB-ay fiyatı en düşük sınıflardan olmalı; okuma ücreti yılda on soru için kabul edilir.",
              "Çevrim içi bir database'in fiyatıyla saklanan arşiv yedi yıl boyunca bütçeyi yer.")],
    cands=["s3", "ks", "aur"],
    scores={
        "s3": [sc(10, "Lifecycle süre dolunca siler (Ö6): sürümler açık olduğu için Expiration bir silme işareti koyar, NoncurrentVersionExpiration retention'ı bitmiş sürümü kalıcı siler; legal hold soruşturma boyunca silmeyi durdurur (Ö7). Puan kırılmadı."),
               sc(10, "Compliance modunda kilitli bir nesne sürümünü root kullanıcı dahil hiç kimse silemez ve üstüne yazamaz; süre kısaltılamaz (Ö7). Puan kırılmadı."),
               sc(7, "Tarih prefix'i bir aralığı doğrudan seçer (Ö2). 3 puan kırıldı: object storage nesnenin içinde aramaz; hesap id'si için Athena dosyaları tarar."),
               sc(10, "Parquet dosyaları olduğu gibi saklanır (Ö1). Puan kırılmadı."),
               sc(10, "Gecelik bir dosya ve yılda on sorgu küçük bir yüktür. Puan kırılmadı."),
               sc(10, "En az üç Availability Zone, 11 dokuzluk dayanıklılık için tasarlanmış. Puan kırılmadı."),
               sc(9, "Sunucusuz. 1 puan kırıldı: Object Lock bucket oluşturulurken açılır ve versioning ister; Athena table'ı bir kez kurulur."),
               sc(10, "Lifecycle dosyaları Glacier Instant Retrieval'a taşır: 21 TB × 0,005 USD ayda yaklaşık 108 USD. Daha ucuz Deep Archive seçilmez, çünkü Athena varsayılan olarak Flexible Retrieval ve Deep Archive'daki nesneleri okumaz; denetçi sorusu geri getirme beklemeden sorulur. Puan kırılmadı.")],
        "ks": [sc(9, "Row TTL'i yedi yıl sonra siler. 1 puan kırıldı: soruşturma günlerinin row'ları süresi dolmasın diye yeni bir TTL ile yeniden yazılır (değiştirilemezlik R1.2'de sayıldı)."),
               sc(3, "7 puan kırıldı: yetkisi olan her istemci UPDATE ve DELETE yapabilir; değiştirilemezlik engine'de değil, IAM ve CloudTrail süreciyle korunur."),
               sc(10, "Partition key gün, clustering column hesap: aralık ve hesap tek sorguda bulunur. Puan kırılmadı."),
               sc(9, "Kolon şeması tanımlanır. 1 puan kırıldı: kayıt şeması değişince yeni kolonlar eklenir."),
               sc(10, "Serverless yazma ve okuma. Puan kırılmadı."),
               sc(10, "Üç AZ'de üç kopya. Puan kırılmadı."),
               sc(9, "Ekip Keyspaces'i ilk yıl için zaten işletir. 1 puan kırıldı: yedi yıllık ikinci bir table ve kapasite modu ayrıca izlenir."),
               sc(2, "8 puan kırıldı: 21 TB çevrim içi bir database'in GB-ay fiyatından ödenir; arşiv sınıfı yoktur.")],
        "aur": [sc(6, "Partition'lar zamanlanmış bir işle yedi yıl sonra düşürülür; iş soruşturma günlerini atlar. 4 puan kırıldı: kendiliğinden süre sonu yoktur; silme zamanlanmış bir iştir ve iş durursa eski kayıtlar kalır (Aurora sayfasının kademesi: partition düşüren iş 4 puan)."),
                sc(4, "Bir trigger ya da yetki kuralı UPDATE ve DELETE'i engelleyebilir. 6 puan kırıldı: yeterli yetkili bir kullanıcı trigger'ı kapatabilir; değiştirilemezlik süreçle korunur."),
                sc(10, "Tarih ve hesap üzerinde bir index ile SQL sorgusu. Puan kırılmadı."),
                sc(8, "Kolon tipleri tanımlanır. 2 puan kırıldı: şema değişikliği bir migration'dır."),
                sc(7, "3 puan kırıldı: yedi yılda milyarlarca row; table partitioning ve VACUUM bir tasarım işidir."),
                sc(10, "Üç AZ'de altı kopya. Puan kırılmadı."),
                sc(7, "3 puan kırıldı: arşiv table'ları, partition'lar ve silme işi yedi yıl boyunca ekibin bakımındadır."),
                sc(2, "8 puan kırıldı: 21 TB database storage'ında ve instance kapasitesiyle ödenir; arşiv sınıfı yoktur.")],
    },
    h2h={
        "ks": "Wide-column (Keyspaces) ile kafa kafaya. Keyspaces bu kayıtların ilk yılında en iyi yerdir: denetçinin \"son 90 gün\" sorusu tek bir partition okumasıdır (Keyspaces sayfası kart 4). "
              "Arşivde ise eksik engine'den gelir: saklama süresi boyunca silmeyi engelleyen bir kilit yoktur (R1 · TA); soruşturma günleri TTL'leri yenilenerek korunur (R1 · YD, küçük bir iş). "
              "Yetkili bir istemci UPDATE ve DELETE yapabilir; değiştirilemezliği süreç korur. Yedi yıllık 21 TB çevrim içi fiyattan ödenir (R5). "
              "Doğru mimari ikisi birliktedir: ilk yıl Keyspaces'te, sonra her gece S3'e ve Object Lock altında yedi yıl. "
              "Hangi koşul değişseydi Keyspaces seçilirdi: düzenleme WORM istemeseydi ve denetçi yedi yılın tamamında saniyelik hesap sorguları yapsaydı.",
        "aur": "İlişkisel (Aurora) ile kafa kafaya. Aurora tarih ve hesap sorgusunu bir index ile en rahat cevaplayan adaydır (R1 · EY 10) ve trigger'larla silmeyi zorlaştırabilir. "
               "Ama yeterli yetkili bir kullanıcı trigger'ı kapatabilir: değiştirilemezlik engine'in değil sürecin garantisidir (R1 · TA). "
               "TTL yoktur ve silme zamanlanmış bir iştir (R1 · YD), milyarlarca row'luk table yedi yıl bakım ister (R2, R4) ve fatura arşiv sınıfı olmadan ödenir (R5). Aurora'nın bu sistemdeki yeri arşiv değil, siparişlerin kayıt sistemidir. "
               "Hangi koşul değişseydi Aurora seçilirdi: arşiv birkaç milyon kayıt olsaydı, düzenleme WORM istemeseydi ve kayıtlar başka table'larla JOIN'li raporlarda her gün kullanılsaydı.",
    },
    verdict="Karar: S3 {s3}, Keyspaces {ks}, Aurora {aur}. Arşivin özü kimsenin silememesi ve süresi dolunca silinmesidir: S3 R1'de 37,6 alır; Keyspaces 30,8, Aurora 26,4'te kalır. "
            "S3 seçtiğimizde artımız: compliance modu root kullanıcıya bile silme izni vermez (Ö7), legal hold soruşturmayı korur, lifecycle yedi yıl sonra siler ve arşiv sınıfına taşır (Ö6). "
            "Eksimiz: dosyanın içinde arama yoktur; uygulama Athena table'ını kurmalı ve soruları tarih prefix'iyle yazmalıdır; compliance modunda yanlış bir süre bile kısaltılamaz, ilk kurulum dikkatle test edilmelidir. "
            "Doğru mimari ikisi birliktedir: ilk yıl Keyspaces, sonrası S3. Bir koşul değişseydi: düzenleme WORM istemeseydi Keyspaces tek başına yeterdi."))

# 9 ---------------------------------------------------------------- ML training data (S3 Express One Zone wins)
S3_W.append(wusecase("training", 9, sim="w_training",
    title="Görsel arama modelinin eğitim verisi: 20 milyon küçük dosya, her epoch'ta yeniden",
    key="Key: train/<shard>/<görsel id>.jpg. Asıl kopya S3 Standard'da; eğitim kopyası GPU'larla aynı AZ'de. Checkpoint 30 dakikada bir.",
    story="Lale Market'in ML ekibi her hafta bir görsel arama modelini yeniden eğitiyor: 64 GPU, tek bir Availability Zone'da. Eğitim verisi 20 milyon ürün görselidir, "
          "ortalama 100 KB, toplam 2 TB. Her epoch bütün dosyaları rastgele sırayla okur ve bir eğitim 10 epoch sürer; tepe anında saniyede yaklaşık 60.000 küçük okuma yapılır. "
          "GPU'lar beklerse saatlik maliyet boşa gider. Verinin asıl kopyası zaten S3 Standard'dadır; eğitim kopyası kaybolursa oradan yeniden kopyalanır. "
          "Eğitim 30 dakikada bir 5 GB'lık bir checkpoint yazar ve her dakika bir eğitim günlüğüne satır ekler. Ekip AWS SDK ve PyTorch biliyor; sunucu işletmek istemiyor.",
    wnote="R1 toplam 36 ve en ağır gruptur; içinde en ağır satır küçük dosyaların ilk byte gecikmesidir (DA 14). R2 22 ile ikinci: saniyede 60.000 okuma GPU'ların beklemeden çalışmasının şartıdır. "
          "R3 8 ile hafiftir: eğitim kopyasının asıl kopyası S3 Standard'dadır.",
    rows=[row("DA", 14, "Her epoch 20 milyon küçük dosyayı okur; her okumanın ilk byte gecikmesi GPU'yu bekletir.",
              "100 KB'lık bir dosyanın ilk byte'ı tek haneli milisaniyelerde gelmeli; rastgele sırada okuma yavaşlamamalı.",
              "Her okuma onlarca milisaniye sürerse 64 GPU zamanının bir kısmını veri bekleyerek geçirir."),
          row("EY", 8, "Dosyalar bir listedeki key ile rastgele sırayla okunur.",
              "Her dosya key'i ile doğrudan okunmalı; liste bir kez çıkarılır.",
              "Key ile okunamayan bir dosya için arama gerekir."),
          row("OY", 8, "Okuma ağırlıklı; checkpoint yazılır ve günlüğe her dakika satır eklenir.",
              "20 milyon dosya okunur; 30 dakikada bir 5 GB checkpoint yazılır; eğitim günlüğüne her dakika bir satır eklenir.",
              "Günlüğe ekleme yapılamazsa her dakika bütün günlük yeniden yazılır."),
          row("VM", 6, "Değer 100 KB'lık bir JPEG'dir.",
              "Küçük binary dosyalar olduğu gibi saklanmalı.",
              "Dosyalar başka biçime çevrilirse eğitim kodu değişir."),
          row("R2", 22, "Tepe anında saniyede 60.000 okuma, 64 GPU.",
              "Saniyede 60.000 okuma (100 KB ile yaklaşık 6 GB/s) ilk dakikadan itibaren karşılanmalı; eğitim başladığında ısınma beklenmemeli.",
              "Okuma hızı sınıra çarparsa GPU'lar bekler ve eğitim günler uzar."),
          row("R3", 8, "Eğitim kopyası kaybolursa asıl kopyadan yeniden üretilir.",
              "Bir arızada eğitim kopyası kaybolabilir ama checkpoint kaybolmamalı; asıl veri S3 Standard'da kalır.",
              "Kaybolan checkpoint bir eğitim gününün tekrarıdır."),
          row("R4", 14, "Ekip SDK ve PyTorch biliyor; sunucu istemiyor.",
              "Sunucusuz; veri hazırlığı bir kopyalama işinden ibaret olmalı.",
              "Bir dosya sunucusu katmanı ML ekibine altyapı işi verir."),
          row("R5", 20, "Ayda dört eğitim × 10 epoch × 20 milyon okuma: 800 milyon GET.",
              "2 TB saklanır ve ayda 800 milyon GET yapılır: istek başına fiyat düşük olmalı; GPU'ların boşta beklediği saat de bir maliyettir.",
              "Okuma başına yüksek fiyat 800 milyon okumada faturayı büyütür.")],
    cands=["s3x", "s3", "efs"],
    scores={
        "s3x": [sc(10, "Tek haneli milisaniye ilk byte gecikmesi, S3 Standard'dan 10 kata kadar hızlı: AWS bunu directory bucket'ın kendi mimarisine, yüksek performanslı donanımına ve sadeleştirilmiş protokolüne bağlar. Puan kırılmadı."),
                sc(10, "Key ile doğrudan okuma. Puan kırılmadı."),
                sc(10, "Checkpoint yeni bir nesnedir; günlüğe nesneye ekleme (write offset) ile satır eklenir. Puan kırılmadı."),
                sc(10, "Küçük dosyalar olduğu gibi saklanır. Puan kırılmadı."),
                sc(10, "Directory bucket varsayılan olarak saniyede 200.000 okumaya kadar ölçeklenir; prefix'e göre ısınma yoktur. Puan kırılmadı."),
                sc(9, "1 puan kırıldı: veri tek AZ'dedir; asıl kopya S3 Standard'da durduğu için kayıp bir yeniden kopyalamadır, checkpoint'ler ayrıca S3 Standard'a kopyalanır."),
                sc(8, "2 puan kırıldı: S3 Standard'dan bir import ya da kopyalama işi çalıştırılır; istemciler Zonal endpoint'i kullanacak şekilde yapılandırılır."),
                sc(10, "Storage 2 TB × 0,118 USD yaklaşık 242 USD/ay; 800 milyon GET 1.000'de 0,0000323 USD ile yaklaşık 26 USD; toplam S3 Standard'dan düşüktür ve GPU beklemesi azalır. Puan kırılmadı.")],
        "s3": [sc(6, "4 puan kırıldı: küçük bir nesnenin ilk byte gecikmesi S3 Express One Zone'un 10 katına kadar çıkabilir; rastgele okumada GPU'lar bekler."),
               sc(10, "Key ile doğrudan okuma (Ö1). Puan kırılmadı."),
               sc(8, "Checkpoint yeni bir nesnedir (Ö1). 2 puan kırıldı: nesneye ekleme yoktur; günlük her dakika ya yeniden yazılır ya da dakika başına yeni bir nesne olur."),
               sc(10, "Küçük dosyalar olduğu gibi saklanır (Ö1). Puan kırılmadı."),
               sc(8, "2 puan kırıldı: prefix başına saniyede en az 5.500 GET; 60.000 okuma için key'ler en az 11 prefix'e yayılır ve S3 ölçeklenirken 503 SlowDown dönebilir (Ö2)."),
               sc(10, "Asıl kopya zaten burada, en az üç AZ'de. Puan kırılmadı."),
               sc(10, "Veri zaten S3 Standard'dadır; ek iş yoktur. Puan kırılmadı."),
               sc(8, "Storage 2 TB × 0,0245 USD yaklaşık 50 USD/ay. 2 puan kırıldı: 800 milyon GET 10.000'de 0,0043 USD ile yaklaşık 344 USD/ay, toplamı S3 Express One Zone'dan yüksektir.")],
        "efs": [sc(7, "Dosya sistemi küçük okumalarda düşük gecikmelidir. 3 puan kırıldı: 20 milyon dosyanın her açılışı NFS üzerinden ayrı bir metadata isteğidir."),
                sc(10, "Yol ile doğrudan okuma. Puan kırılmadı."),
                sc(10, "Dosyaya ekleme ve yazma doğaldır. Puan kırılmadı."),
                sc(10, "Küçük dosyalar olduğu gibi saklanır. Puan kırılmadı."),
                sc(10, "Frankfurt'ta bir dosya sisteminin varsayılan elastic okuma sınırı 60 GiB/s ve sık okunan veride 250.000 okuma IOPS'tur; 6 GB/s ve saniyede 60.000 okuma bunun içindedir. Puan kırılmadı."),
                sc(10, "Regional EFS birden fazla AZ'de saklar. Puan kırılmadı."),
                sc(8, "2 puan kırıldı: S3'ten kopyalama işi ve eğitim sunucularında mount target'lar kurulur."),
                sc(2, "8 puan kırıldı: 2 TB Standard'da ayda yaklaşık 737 USD; elastic throughput okumaları GB başına 0,04 USD ile ayda 80 TB okumada yaklaşık 3.300 USD.")],
    },
    h2h={
        "s3": "Object storage (S3) ile kafa kafaya. S3 Standard bu verinin asıl evidir ve en dayanıklı yeridir (R3); veri zaten orada olduğu için hiçbir iş gerektirmez (R4). "
              "Ama bu kartta asıl soru küçük dosyaların ilk byte gecikmesidir: S3 Express One Zone aynı AZ'de ve tek haneli milisaniyelerde cevap verir, S3 Standard 10 kata kadar yavaş olabilir (R1 · DA 6). "
              "Saniyede 60.000 okuma için key'ler prefix'lere yayılmalıdır (R2) ve 800 milyon GET'in fiyatı daha yüksektir (R5). "
              "Hangi koşul değişseydi S3 Standard seçilirdi: dosyalar büyük olsaydı (örneğin 100 MB'lık shard'lar), okuma sıralı olsaydı ve GPU'lar veriyi önceden belleğe alabilseydi; o zaman gecikme önemini yitirir.",
        "efs": "Paylaşılan dosya sistemi (EFS) ile kafa kafaya. EFS eğitim kodunun beklediği yolu ve dosyaya eklemeyi doğal olarak verir ve veriyi birden fazla AZ'de tutar. "
               "Ama 20 milyon küçük dosyanın her açılışı NFS üzerinden bir metadata isteğidir (R1 · DA); okuma hızı varsayılan sınırların içindedir (R2 eşit). "
               "Asıl fark faturadadır: 2 TB'ın saklaması ve her epoch'ta okunan 2 TB elastic throughput ücretiyle ayda binlerce dolar tutar (R5). Kod tarafında EFS en az değişikliği ister; bu kartta o avantaj fiyatı karşılamaz. "
               "Hangi koşul değişseydi EFS seçilirdi: eğitim verisi birkaç GB olsaydı, birkaç sunucu aynı dosyaları yerinde güncelleseydi ve kod S3 API'sine hiç dokunamasaydı.",
    },
    verdict="Karar: S3 Express One Zone {s3x}, S3 {s3}, EFS {efs}. Kararı küçük dosyaların ilk byte gecikmesi (R1 · DA) ve saniyede 60.000 okuma (R2) verir. "
            "Yine de S3 Standard'dan okursak artımız: veri zaten oradadır, en az üç AZ'de durur ve hiçbir kopyalama işi yoktur (Ö1). "
            "Eksimiz: GPU'lar her küçük okumada daha uzun bekler; uygulama key'leri prefix'lere yaymalı, dosyaları büyük shard'lara paketlemeli ya da önceden okumalı (prefetch) ve günlüğü dakika başına yeni nesnelere yazmalıdır. "
            "Doğru mimari ikisi birliktedir: asıl kopya S3 Standard'da, eğitim kopyası S3 Express One Zone'da, checkpoint'ler S3 Standard'a. "
            "Bir koşul değişseydi: veri büyük shard dosyalarına paketlenseydi S3 Standard öne geçerdi."))

# 10 --------------------------------------------------------------- file metadata (repeats DynamoDB card 9)
S3_W.append(wusecase("metadata", 10,
    title=_S3_D9["title"][1] + ": S3'ün nesne metadata'sı yeter mi?",
    key=_S3_D9["key"][1] + " Dosyanın kendisi S3'te.",
    story=_S3_D9["story"][1],
    wnote=_S3_D9["wnote"][1] + " Bu kart DynamoDB sayfasının 9. kartıyla aynı iş yüküdür ve aynı satırları, ağırlıkları ve DynamoDB ile DocumentDB puanlarını taşır; "
          "orada üçüncü olan Aurora (77) burada yerini bu sayfanın servisine bırakır.",
    rows=[row(r["code"], r["w"], _s3x(r["wwhy"][1]), _s3x(r["want"][1]), _s3x(r["why"][1])) for r in _S3_D9["rows"]],
    cands=["ddb", "doc", "s3"],
    scores={
        "ddb": _s3same(_S3_D9, "ddb", [sc(p, _s3x(w[1])) for p, w in _S3_D9["scores"]["ddb"]]),
        "doc": _s3same(_S3_D9, "doc", [sc(p, _s3x(w[1])) for p, w in _S3_D9["scores"]["doc"]]),
        "s3": [sc(7, "Key \"kullanıcı/klasör/dosya adı\" olursa ListObjectsV2 Prefix ile bir klasörü sıralı ve 1.000'erlik sayfalarla döndürür (Ö2). 3 puan kırıldı: liste sadece key, boyut ve tarih verir; durum ve tag gibi alanlar her nesne için ayrı bir HEAD ya da tag okumasıdır ve klasörü yeniden adlandırmak her nesneyi kopyalayıp silmektir."),
               sc(7, "Kullanıcı metadata'sı ve en fazla 10 tag nesneyle birlikte durur (Ö3). 3 puan kırıldı: kullanıcı metadata'sı yaklaşık 2 KB'tır ve sadece metin taşır; türe özel sayılar ve listeler metne çevrilir (değiştirmenin bedeli R1.3'te)."),
               sc(5, "CopyObject If-Match ile koşullu yapılır (Ö4). 5 puan kırıldı: durum metadata'daysa geçiş nesnenin kopyalanmasıdır; 5 GB'tan büyük dosyada çok parçalı kopya gerekir ve tag güncellemesinin koşulu yoktur."),
               sc(9, "Olay bildirimleri oluşturma, silme ve tag değişikliklerini verir (Ö8); S3 Metadata journal table'ı değişiklikleri yakın gerçek zamanda tutar. 1 puan kırıldı: olaylar en az bir kez teslim edilir ve bazen bir dakika sürer."),
               sc(6, "4 puan kırıldı: her liste sayfası ayrı bir HTTP isteğidir ve 5.000 dosyalık bir kullanıcının listesi beş istek ister; 100 ms'nin altında kalması garanti değildir."),
               sc(10, "Metadata nesneyle birlikte en az üç AZ'de saklanır. Puan kırılmadı."),
               sc(8, "Sunucusuz ve ekip SDK biliyor. 2 puan kırıldı: arama servisine aktaran bir olay işleyicisi (Lambda) ya da S3 Metadata tablosundan okuyan bir iş kurulur."),
               sc(2, "8 puan kırıldı: LIST 1.000 istekte 0,0054 USD; mesai saatlerinde saniyede 5.000 liste (günde 10 saat, ayda 22 iş günü) ayda yaklaşık 4 milyar istek ve 21.000 USD'tır, gece trafiği buna eklenir.")],
    },
    h2h={
        "doc": "Document (DocumentDB) ile kafa kafaya. DocumentDB R1'in iki satırında DynamoDB ile eşittir: her dosya kendi alanlarını taşır ve durum geçişi koşullu bir updateOne'dır. "
               "Sıralı listede öndedir (10'a 9): bileşik index klasör adı değişince key'i yeniden yazmaz. Değişiklik akışında DynamoDB öndedir (10'a 9): change stream'lerin varsayılan saklaması kısadır. "
               "R1'de DocumentDB 44'e 43,5 öndedir; kararı servis tasarımı verir: arama servisine aktaran tüketiciyi ekip işletir, DynamoDB'de aynı iş OpenSearch'e zero-ETL entegrasyonudur (R4), "
               "tek primary ve instance boyutlandırması sunucu istemeyen bir ürün ekibine iş bırakır (R2). S3'e karşı DocumentDB'nin üstünlüğü metadata üzerinde esnek, birden çok alanlı sorgulardır; S3 metadata'ya göre hiç sorgulamaz. "
               "Hangi koşul değişseydi DocumentDB seçilirdi: kullanıcılar metadata üzerinde esnek sorgular yapsaydı (\"son bir ayda yüklediğim 10 MB'tan büyük PDF'ler\") ve bu sorgular ayrı bir arama servisine gerek kalmadan database'te cevaplanmak istenseydi.",
        "s3": "Object storage (S3) ile kafa kafaya. Dosyanın kendisi zaten S3'te; metadata'yı da nesnenin yanında tutmak tek bir yer gibi görünür. S3 bunun bir kısmını gerçekten yapar: "
              "key'i \"kullanıcı/klasör/dosya\" olarak kurarsan prefix ile sıralı liste gelir, değişiklikler olay bildirimi ve S3 Metadata ile dışarı akar, veri en az üç AZ'dedir. "
              "Ama nesne metadata'sı bir kayıt değildir: yükleme anında sabitlenir, değişmesi kopyalamadır (R1 · VM, TA) ve liste alanları getirmez (R1 · EY). "
              "Asıl kayıp fiyattadır: saniyede 5.000 liste isteği ayda on binlerce dolar tutar (R5). "
              "Hangi koşul değişseydi S3 seçilirdi: liste günde birkaç yüz kez açılsaydı, metadata yükleme anında belli olup hiç değişmeseydi ve analiz S3 Metadata tablosundan yapılsaydı.",
    },
    verdict="Karar: DynamoDB {ddb}, DocumentDB {doc}, S3 {s3}. Dosyanın baytları S3'e, onu anlatan kayıt bir database'e aittir: metadata sık değişir, sıralı listelenir ve saniyede binlerce kez okunur. "
            "Yine de metadata'yı S3'te tutarsak artımız: tek bir yer, prefix ile sıralı liste (Ö2), olay bildirimiyle dışarı akan değişiklikler (Ö8). "
            "Eksimiz: durum değişikliği nesnenin kopyalanmasıdır, liste alanları getirmez ve LIST istek başına ödenir; uygulama metadata'yı yükleme anında sabitlemeli ve sık okunan listeyi bir önbellekte tutmalıdır. "
            "Doğru mimari ikisi birliktedir: dosya S3'te, metadata DynamoDB'de, ikisini aynı key bağlar. Bir koşul değişseydi: liste günde birkaç yüz kez açılsaydı, metadata yüklemeden sonra hiç değişmeseydi ve ayrı bir database istenmeseydi, liste yükü ve durum geçişi satırları düşer ve S3 tek başına yeterdi."))

USECASES_W["s3"] = S3_W
PAGE_SVC["s3"] = "s3"
