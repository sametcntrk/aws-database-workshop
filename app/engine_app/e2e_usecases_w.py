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
SOURCE = {"R1": (None, "engine'in doğası"), "R2": (None, "engine'in doğası"), "R3": (None, "üreticinin servis tasarımı"),
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
