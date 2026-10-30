"""Visitor identity (cookie) and the six Personas a Visitor can shop as."""
import re

from flask import request

PERSONAS = [
    {"id": "C00001", "name": "Ayşe Yılmaz", "city": "İstanbul", "segment": "premium",
     "about": "Premium customer in İstanbul. She orders often, so recommendations and the leaderboard have data.",
     "about_tr": "İstanbul'da premium müşteri. Sık sipariş veriyor, bu yüzden öneriler ve liderlik tablosu dolu."},
    {"id": "C00002", "name": "Mert Doğan", "city": "Ankara", "segment": "kurumsal",
     "about": "Corporate buyer in Ankara. He buys in bulk, so his carts and orders are large.",
     "about_tr": "Ankara'da kurumsal alıcı. Toplu alım yapıyor, sepetleri ve siparişleri büyük."},
    {"id": "C00003", "name": "Elif Kaya", "city": "İzmir", "segment": "bireysel",
     "about": "New customer in İzmir. She has almost no history, so you see a cold start.",
     "about_tr": "İzmir'de yeni müşteri. Neredeyse hiç geçmişi yok, bu yüzden \"soğuk başlangıç\" durumunu görürsün."},
    {"id": "C00004", "name": "Lukas Weber", "city": "Frankfurt", "segment": "premium",
     "about": "Book reader in Frankfurt. His purchases cluster in one category of the graph.",
     "about_tr": "Frankfurt'ta kitap okuru. Aldıkları grafın tek bir kategorisinde toplanıyor."},
    {"id": "C00005", "name": "Zeynep Şahin", "city": "İstanbul", "segment": "bireysel",
     "about": "Fashion shopper who browses a lot, so her activity feed is long.",
     "about_tr": "Çok gezinen bir moda alışverişçisi, bu yüzden aktivite akışı uzun."},
    {"id": "C00006", "name": "Can Demir", "city": "Bursa", "segment": "bireysel",
     "about": "Sports fan who hunts flash deals.",
     "about_tr": "Flash deal kovalayan bir spor meraklısı."},
]
PERSONA_IDS = {p["id"] for p in PERSONAS}
_VISITOR = re.compile(r"^[a-f0-9-]{8,40}$")


def visitor_id():
    """The Visitor id from the lm_visitor cookie, or 'anonymous' when the cookie is missing or malformed."""
    v = request.cookies.get("lm_visitor", "")
    return v if _VISITOR.match(v) else "anonymous"


def persona_id():
    p = request.cookies.get("lm_persona", "")
    return p if p in PERSONA_IDS else "C00001"


def persona():
    pid = persona_id()
    return next(p for p in PERSONAS if p["id"] == pid)
