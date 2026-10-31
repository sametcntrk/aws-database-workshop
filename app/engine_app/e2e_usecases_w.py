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
                sc(6, "Saniyede 5.000 küçük yazma güçlü bir writer'ın erişimindedir; Serverless v2 ACU'yu artırır. 4 puan kırıldı: bütün yazmalar tek writer'dan geçer; on dakikada 20 kat için minimum ACU yüksek tutulmalı ya da ölçeklenme önceden test edilmelidir."),
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
                sc(4, "Serverless v2 ACU'yu artırır. 6 puan kırıldı: 200.000 istek/saniyenin yazma kısmı tek writer'dan geçer; bu yük bir sharding tasarımı ister."),
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
                sc(9, "Bu hacim tek writer için küçüktür. 1 puan kırıldı: bağlantı sayısı ödeme API'ının ölçeğiyle birlikte izlenmelidir."),
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
                sc(4, "Saniyede 50.000 tutma denemesi tek writer'dan geçer ve en çok aranan koltuklarda row kilitleri sıraya girer. 6 puan kırıldı: açılış yükü bir kuyruk ya da sharding ister."),
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
        "doc": "Document (DocumentDB) ile kafa kafaya. DocumentDB R1'in üç satırında DynamoDB ile eşittir: sıralı liste bir bileşik index ile tek sorgudur, her dosya kendi alanlarını taşır ve durum geçişi koşullu bir updateOne'dır. "
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
               sc(4, "Kalıcı bir yazma log'u yoktur. 6 puan kırıldı: bir arızada listeler yeniden yüklenmelidir; bu kartta kabul edilen bir sonuçtur."),
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
        "ddb": "Key-value (DynamoDB) ile kafa kafaya. Fark 7,5 puandır ve kararı R1'in depolama satırı verir. İki aday da key ile tek okuma yapar ve gece toplu yazmayı taşır; DynamoDB dayanıklılıkta öndedir. "
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
               sc(5, "Yeni alan dynamic mapping ile index'e eklenir. 5 puan kırıldı: bir alanın type'ı değişirse ya da analiz biçimi değişirse index baştan kurulur (reindex)."),
               sc(7, "Filtre ve facet bu engine'in ana işidir; \"42 numara, kırmızı, su geçirmez\" milisaniyede döner, metin araması da burada olur. 3 puan kırıldı: ilişkiler index'e yazılırken düzleştirilir; marka adı değişince o markanın bütün ürün document'ları yeniden yazılır."),
               sc(2, "Bir document'ın yazması kendi içinde atomiktir. 8 puan kırıldı: transaction, foreign key ve CHECK yoktur; varyantın ürüne ait olması ve \"fiyat > 0\" kuralı tamamen uygulamadadır."),
               sc(9, "2.000 okuma ve 50 yazma bir domain için küçüktür. 1 puan kırıldı: refresh aralığı yüzünden yeni yazma kısa bir süre aramada görünmez; shard sayısı önceden seçilir."),
               sc(6, "Replica shard'lar node arızasını karşılar, otomatik snapshot alınır. 4 puan kırıldı: snapshot'lar arasındaki yazmalar bir felakette kaynak sistemden yeniden yüklenir."),
               sc(5, "Yönetilen domain. 5 puan kırıldı: mapping tasarımı, reindex ve shard planı ekibin işidir ve ekip yeni bir sorgu dili öğrenir."),
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
    cands=["rs", "aur", "os"],
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
               sc(8, "Shard'lar ve node'lar okumayı paylaşır. 2 puan kırıldı: 30 dashboard için node sayısı önceden boyutlanır."),
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
    verdict="Karar: Redshift {rs}, Aurora {aur}, OpenSearch {os}. Bu iş yüküne en uygun servis Redshift'tir; Aurora PostgreSQL net bir farkla ikincidir. Kararı R1'in depolama satırı ve R2 verir: geçmişin tamamını tarayan sorgular columnar ve MPP bir engine ister. "
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
        "os": [sc(7, "geo_shape \"bu çokgende\", geo_distance \"5 km içinde\" sorularını cevaplar ve sonuçlar mesafeye göre sıralanır. 3 puan kırıldı: \"bu nokta hangi bölgede\" bölgeleri document olarak index'leyip ters bir sorgu ister ve rota uzunluğu için bir fonksiyon yoktur."),
               sc(8, "geo_point ve geo_shape alan tipleri vardır. 2 puan kırıldı: koordinat sistemi dönüşümleri ve geometri doğrulaması PostGIS kadar geniş değildir."),
               sc(9, "Mekânsal alanlar ağaç yapılı index'lerde durur ve filtreler önbelleğe alınır. 1 puan kırıldı: konum güncellemeleri refresh aralığından sonra görünür."),
               sc(2, "Bir document'ın yazması atomiktir. 8 puan kırıldı: sipariş ve bölge fiyatını birlikte yazan bir transaction yoktur; fiyat siparişten ayrı bir sistemde hesaplanır."),
               sc(9, "Saniyede 200 soru bir domain için küçüktür. 1 puan kırıldı: node sayısı önceden seçilir."),
               sc(7, "Replica shard'lar node arızasını karşılar, otomatik snapshot alınır. 3 puan kırıldı: snapshot'lar arasındaki yazmalar bir felakette kaynaktan yeniden yüklenir."),
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
                sc(7, "INSERT okumadan ekler. 3 puan kırıldı: her event heap'e, index'e ve write-ahead log'a yazılır; saniyede on binlerce küçük ekleme tek writer'da yazma işini katlar."),
                sc(4, "Günlük partition'lar ve en eski partition'ın düşürülmesi 7 günü sınırlar. 6 puan kırıldı: kendiliğinden süre sonu yoktur; partition bakımı zamanlanmış bir iştir (pg_partman, pg_cron) ve iş durursa eski event'ler kalır."),
                sc(8, "Index en yeni 40 event'i sırayla bulur. 2 puan kırıldı: row'lar heap'te yazma sırasıyla durur, kullanıcıya göre değil; 40 event çoğu zaman 40 ayrı page okumasıdır."),
                sc(4, "Bütün yazmalar checkout'u da taşıyan tek writer'dan geçer. 6 puan kırıldı: kampanya akşamı saniyede 15.000 ekleme aynı writer'da sipariş yazmalarıyla yarışır."),
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
        row("R2", 16, "Şikâyet dalgasında yazma beş katına çıkar ve destek o anda durmamalıdır.", kreq("inbox", 1, "want"), kreq("inbox", 1, "why")),
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
                sc(8, "Liste sırası tek bir UPDATE'tir ve index kendiliğinden güncellenir. 2 puan kırıldı: her UPDATE row'un yeni bir sürümünü yazar; sık güncellenen sohbet row'ları VACUUM işini artırır."),
                sc(6, "Logical replication değişiklikleri engine'den sırayla dışarı verir. 4 puan kırıldı: kendiliğinden süre sonu yoktur; iki yıllık silme aylık partition'ları düşüren zamanlanmış bir iştir."),
                sc(10, "Index'i database transaction'ın içinde günceller; sohbet ve liste hiç ayrılmaz. Puan kırılmadı."),
                sc(7, "Saniyede 2.500 yazma tek writer için olağandır. 3 puan kırıldı: dalgada beş kat, yani saniyede 12.500 yazma, bütün yazmaları taşıyan tek writer'a gelir."),
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
                sc(4, "Saniyede 3.000 ekleme tek writer için olağandır ve bir yıllık çevrim içi hacim 128 TiB'lık storage sınırının altındadır. 6 puan kırıldı: 95 milyar row'luk tek bir table ve iki index onlarca TB'tır; bütün yazmalar tek writer'dadır ve bu büyüklükteki B-tree index'lere ekleme, row sayısı büyüdükçe yavaşlar."),
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
               sc(8, "Kopyalar birkaç AZ'dedir. 2 puan kırıldı: kalıcı bir yazma log'u yoktur; bir arızada kaybolan durumlar bir dakika içinde yeniden gelir."),
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
               sc(5, "Serverless RPU'lar sorgu yüküyle büyür. 5 puan kırıldı: saniyede 40.000 tıklama bir akış katmanından (Kinesis) streaming ingestion ile gelir; o katman da ölçeklenir."),
               sc(9, "Veri S3'te yedeklenir. 1 puan kırıldı: akış katmanındaki son saniyeler bir arızada yeniden oynatılır."),
               sc(6, "Analistlerin SQL'i doğrudan çalışır. 4 puan kırıldı: sessionization işleri Spark connector'ından Redshift'e taşınır ve bir akış katmanı işletilir."),
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
               sc(2, "8 puan kırıldı: \"en faydalı\" sırası bir clustering column'dur ve değiştirilemez; her oy eski row'u silip yenisini yazar ve bir tombstone bırakır (Ö3'ün sınırı)."),
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
        "ks": "Wide-column (Keyspaces) ile kafa kafaya. Keyspaces bu kartta net kaybeder ve nedeni engine'dir: R1'de 52 puanın 16,6'sını alır. "
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
