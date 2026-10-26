#!/usr/bin/env python3
"""AWS Database Workshop - 2-page draw.io file (aws-arch-diagram-sc style).

Page 1: architecture. Steps are numbered per traffic scenario (both start at 1):
  Scenario 1 (blue, legend left):   participant browser -> Route 53 -> ALB (path rule) -> Engine App -> Engine
  Scenario 2 (orange, legend right): Engine App at boot -> NAT -> IGW -> GitHub/PyPI, and -> Secrets Manager
Layout rules of this page:
  - every Engine App sits straight above its Engine (or its VPC endpoint), so app -> data arrows are vertical
  - one ALB; its arrows fan out on ordered lanes (farthest target on the highest lane), so they never cross
  - endpoints sit next to the resource that uses them; SSM endpoints exist but are not drawn
  - secret retrieval is a red dashed line; a small IAM role icon marks connections authorized by IAM (SigV4)
Page 2: data type -> category -> AWS Engine mapping (from the "How to Choose Database" infographic).

Usage: python3 gen_workshop_diagram.py ../aws-database-workshop.drawio
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diagram_lib as L  # noqa: E402
from diagram_lib import F, cells, group, svc, vertex  # noqa: E402

OUT = sys.argv[1]
SPAN = "color: light-dark(rgb(0,0,0), rgb(255,255,255));"
C_IN, C_EG, C_SEC = "#147EBA", "#ED7100", "#D13212"
B_S1, B_S2 = "#007CBD", "#ED7100"
RIGHT = "align=right;spacingRight=12;"
DOMAIN = "dbworkshop.tdsynnexlab.link"

# example internet addresses (RFC 5737 documentation ranges)
CLIENT_IP, ALB_PUB, R53_NS, GH_IP, NAT_EIP = "203.0.113.10", "198.51.100.20", "192.0.2.53", "192.0.2.80", "198.51.100.50"
ALB_IPS = ["10.20.0.25", "10.20.1.25", "10.20.2.25"]
NAT_IPS = ["10.20.0.50", "10.20.1.50", "10.20.2.50"]
SM_ENI = ["10.20.20.210", "10.20.21.210", "10.20.22.210"]
KS_ENI = "10.20.20.200"

# ---------------------------------------------------------------- geometry
LEFT_X, LP_W = 40, 680
USERS_X = LEFT_X + LP_W + 40
CLOUD_X, CLOUD_Y = USERS_X + 200, 150
R53_X = CLOUD_X + 50
VPC_X, VPC_Y = CLOUD_X + 230, 240
BAND = 240
IGW_Y = VPC_Y + 80
MID = IGW_Y + 60
AZ_Y = VPC_Y + BAND
SLOT = [20, 190, 360, 530, 700]          # x of 120px containers inside a subnet
SUB_W = 1040
AZ_W = SUB_W + 40
AZ_X = [VPC_X + 40 + i * (AZ_W + 40) for i in range(3)]
PUB_H, GAP1, APP_H, GAP2, DATA_H = 260, 120, 230, 70, 250
Y_PUB = AZ_Y + 40
Y_APP = Y_PUB + PUB_H + GAP1
Y_DATA = Y_APP + APP_H + GAP2
AZ_H = 40 + PUB_H + GAP1 + APP_H + GAP2 + DATA_H + 30
Y_GWE = AZ_Y + AZ_H + 30                 # gateway endpoints: VPC level, under the apps that use them
VPC_W = 40 + 3 * AZ_W + 2 * 40 + 40
VPC_H = BAND + AZ_H + 160
Y_REG = VPC_Y + VPC_H + 60               # regional services row (outside the VPC)
CLOUD_W = (VPC_X - CLOUD_X) + VPC_W + 60
CLOUD_H = Y_REG + 160 - CLOUD_Y
DEST_X = CLOUD_X + CLOUD_W + 40
RP_X = DEST_X + 240
RP_W = 680
TOTAL_W = RP_X + RP_W - LEFT_X
SEC_LANE = 1005                          # x (subnet-relative) of the lane from a Secrets endpoint down to Secrets Manager

AZS = ["a", "b", "c"]
CIDR = {"pub": ["10.20.0.0/24", "10.20.1.0/24", "10.20.2.0/24"],
        "app": ["10.20.10.0/24", "10.20.11.0/24", "10.20.12.0/24"],
        "data": ["10.20.20.0/24", "10.20.21.0/24", "10.20.22.0/24"]}

# Engine Apps: id, label, AZ index, slot, fixed private IP (set in the template), ALB priority
APPS = [
    ("dynamodb", "DynamoDB", 0, 0, "10.20.10.11", 30), ("s3", "S3", 0, 1, "10.20.10.12", 90),
    ("keyspaces", "Keyspaces", 0, 2, "10.20.10.13", 50), ("aurora", "Aurora", 0, 3, "10.20.10.14", 10),
    ("neptune", "Neptune", 1, 0, "10.20.11.11", 70), ("docdb", "DocumentDB", 1, 1, "10.20.11.12", 80),
    ("elasticache", "ElastiCache", 1, 2, "10.20.11.13", 40),
    ("opensearch", "OpenSearch", 2, 0, "10.20.12.11", 100), ("redshift", "Redshift", 2, 1, "10.20.12.12", 20),
    ("influxdb", "InfluxDB", 2, 2, "10.20.12.13", 60),
]
APP = {a[0]: a for a in APPS}
# Engines inside the VPC: id, shape, name, sub-label, example IP, container title, category key
VPC_ENGINES = [
    ("aurora", "aurora", "Aurora PostgreSQL", "writer a · reader b", "10.20.20.30", "Relational DB", "db"),
    ("neptune", "neptune", "Neptune", "writer b · reader c", "10.20.21.30", "Graph DB", "db"),
    ("docdb", "documentdb_with_mongodb_compatibility", "DocumentDB", "primary b · replica c", "10.20.21.31", "Document DB", "db"),
    ("elasticache", "elasticache", "ElastiCache Valkey", "Serverless · a/b/c", "10.20.21.32", "In-memory DB", "db"),
    ("opensearch", "elasticsearch_service", "OpenSearch", "3 data nodes a/b/c", "10.20.22.31", "Search + geo DB", "net"),
    ("redshift", "redshift", "Redshift", "Serverless · a/b/c", "10.20.22.30", "Columnar DB", "net"),
    ("influxdb", "timestream", "Timestream InfluxDB", "Multi-AZ standby", "10.20.22.32", "Time-series DB", "db"),
]
# protocol on the Engine App -> data connection
PROTO = {
    "aurora": "PostgreSQL wire<br>TCP 5432 · TLS · password",
    "redshift": "PostgreSQL wire<br>TCP 5439 · TLS · password",
    "elasticache": "RESP (Valkey)<br>TCP 6379 · TLS · ACL user",
    "influxdb": "HTTPS 8086<br>InfluxDB v2 API · password",
    "neptune": "HTTPS 8182 · openCypher<br>IAM SigV4",
    "docdb": "MongoDB wire<br>TCP 27017 · TLS · password",
    "opensearch": "HTTPS 443 · REST API<br>IAM SigV4",
    "dynamodb": "HTTPS 443 · DynamoDB API<br>IAM SigV4",
    "s3": "HTTPS 443 · S3 API<br>IAM SigV4",
    "keyspaces": "CQL native · TCP 9142<br>TLS · IAM SigV4",
}
PASSWORD_APPS = ["aurora", "docdb", "elasticache", "redshift", "influxdb"]   # read a secret at start
IAM_APPS = ["neptune", "opensearch"]                                          # IAM icon on the app -> engine arrow


def ax(azi, slot):
    """absolute x of a slot container in AZ azi"""
    return AZ_X[azi] + 20 + SLOT[slot]


def rt(cid, name, rows, x, y, w=270, h=None, parent="1", note=""):
    trs = "".join(f"<tr><td style='padding-right:10px'>{d}</td><td>→ {t}</td></tr>" for d, t in rows)
    body = (f"<b>Route table: {name}</b>" + (f"<br><i>{note}</i>" if note else "")
            + f"<table style='font-size:10px;margin-top:3px'>{trs}</table>")
    h = h or (34 + 15 * len(rows) + (14 * (1 + len(note) // 44) if note else 0))
    vertex(cid, body, "rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=top;fontSize=10;spacing=6;fillColor=none;"
           "strokeColor=#8C4FFF;dashed=1;" + F, x, y, w, h, parent=parent)


def child_svc(cid, parent, x, y, cat, shape, name, sub, category, res=False):
    n = len(cells)
    svc(cid, x, y, cat, shape, name, sub, category, res=res)
    cells[n] = cells[n].replace('parent="1"', f'parent="{parent}"', 1)


def small_svc(cid, x, y, cat, shape, name, sub, title, parent="1"):
    """Small endpoint box: 120x90 container, 32x32 icon (user request: endpoints take less room)."""
    tint, stroke, fill = L.CAT[cat]
    vertex(f"grp-{cid}", title,
           f"fillColor={tint};strokeColor={stroke};rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fontStyle=1;fontSize=10;fontColor={stroke};{F}container=1;collapsible=0;shadow=1;strokeWidth=1.5;spacingTop=-3;",
           x, y, 120, 90, parent=parent)
    vertex(cid, name + (f"<div><i>{sub}</i></div>" if sub else ""),
           f"sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor={fill};strokeColor=none;dashed=0;"
           f"verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=10;fontStyle=0;aspect=fixed;"
           f"pointerEvents=1;shape=mxgraph.aws4.{shape};{F}", 44, 18, 32, 32, parent=f"grp-{cid}")


def iam(cid, x, y):
    """Small IAM role icon on a connection that is authorized by the Engine App's IAM role."""
    vertex(cid, "", f"sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=#DD344C;strokeColor=none;dashed=0;"
           f"verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=10;aspect=fixed;pointerEvents=1;"
           f"shape=mxgraph.aws4.role;{F}", x, y, 26, 15)


def note(cid, html_text, x, y, w, h, color="#232F3E", align="left", size=10):
    vertex(cid, html_text, f"text;html=1;align={align};verticalAlign=top;fontSize={size};whiteSpace=wrap;fontColor={color};"
           "labelBackgroundColor=none;spacing=0;" + F, x, y, w, h)


def edge(cid, src, tgt, color, pts=(), ex=None, en=None, both=True, raw=False, dashed=False, width=2):
    st = (f"edgeStyle=orthogonalEdgeStyle;html=1;endArrow=block;endFill=1;strokeColor={color};rounded=0;strokeWidth={width};" + F
          + ("startArrow=block;startFill=1;" if both else "startArrow=none;") + ("dashed=1;dashPattern=8 4;" if dashed else ""))
    if ex:
        st += f"exitX={ex[0]};exitY={ex[1]};exitDx=0;exitDy=0;"
    if en:
        st += f"entryX={en[0]};entryY={en[1]};entryDx=0;entryDy=0;"
    if not raw:
        src = src if src.startswith(("users", "dest")) else f"grp-{src}"
        tgt = tgt if tgt.startswith(("users", "dest")) else f"grp-{tgt}"
    p = "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in pts)
    arr = f'<Array as="points">{p}</Array>' if pts else ""
    cells.append(f'<mxCell id="{cid}" style="{L.a(st)}" edge="1" parent="1" source="{src}" target="{tgt}">'
                 f'<mxGeometry relative="1" as="geometry">{arr}</mxGeometry></mxCell>')


def tag(label):
    n, c = label[:-1], label[-1]
    return f"{n}-Con-{c.upper()}" if c.isalpha() else label


def badge(cid, label, x, y, fill):
    vertex(cid, tag(label),
           f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor=default;fontColor=#FFFFFF;fontStyle=1;fontSize=15;{F}"
           "shadow=1;glass=0;strokeWidth=2;align=center;verticalAlign=middle;labelBackgroundColor=none;", x, y, 76, 28)


def actor(cid, title, icon, x, y, w, h, lines=""):
    vertex(cid, title,
           "fillColor=#f5f5f5;strokeColor=light-dark(#666666,#D4D4D4);rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fontStyle=1;fontSize=11;"
           "fontColor=#333333;" + F + "container=1;collapsible=0;shadow=1;strokeWidth=1;", x, y, w, h)
    vertex(f"{cid}-icon", "", f"sketch=0;{L.PTS}outlineConnect=0;fontColor=#232F3E;fillColor=#232F3D;strokeColor=#ffffff;dashed=0;"
           "verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=12;fontStyle=0;aspect=fixed;"
           f"shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{icon};" + F, (w - 48) // 2, 36, 48, 48, parent=cid)
    if lines:
        vertex(f"{cid}-text", lines, "text;html=1;align=center;verticalAlign=top;fontSize=10;whiteSpace=wrap;fontColor=#333333;" + F,
               6, 88, w - 12, h - 92, parent=cid)


def legend_panel(sfx, x, y, w, h, head, sub, steps, fill, boxes, step_h=92, head_h=130):
    vertex(f"legend-bg-{sfx}", "", "verticalLabelPosition=bottom;verticalAlign=top;html=1;shape=mxgraph.basic.rect;fillColor2=none;strokeWidth=1;"
           f"size=20;indent=5;fillColor=light-dark(#EDF3FF,#305363);strokeColor={fill};", x, y, w, h)
    cw = w - 40
    vertex(f"legend-container-{sfx}", "", "group", x + 20, y + 20, cw, h - 40, extra=' connectable="0"')
    vertex(f"legend-head-{sfx}", f'<div style="font-size:17px;color:{fill}"><b>{head}</b></div><div style="{SPAN}">{sub}</div>',
           "text;html=1;align=left;verticalAlign=top;spacingTop=-4;fontSize=12;labelBackgroundColor=none;whiteSpace=wrap;" + F,
           0, 0, cw, head_h, parent=f"legend-container-{sfx}")
    yy = head_h + 12
    for lab, tt, d in steps:
        hh = step_h
        g = f"step-{sfx}-{lab}-legend"
        vertex(g, "", "group;" + F, 0, yy, cw, hh, parent=f"legend-container-{sfx}", extra=' connectable="0"')
        vertex(f"step-{sfx}-{lab}-badge-legend", tag(lab),
               f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor=default;fontColor=#FFFFFF;fontStyle=1;fontSize=16;"
               "labelBackgroundColor=none;" + F + "shadow=1;glass=0;strokeWidth=2;", 0, 2, 92, 34, parent=g)
        vertex(f"step-{sfx}-{lab}-desc-legend", f'<div><b>{tt}</b></div><div><span style="{SPAN}">{d}</span></div>',
               "text;html=1;align=left;verticalAlign=top;spacingTop=-4;fontSize=12;labelBackgroundColor=none;whiteSpace=wrap;" + F,
               104, 0, cw - 104, hh, parent=g)
        yy += hh + 6
    for bid, txt, stroke, bh in boxes:
        vertex(f"legend-{bid}-{sfx}", f'<div style="{SPAN}">{txt}</div>',
               f"text;html=1;align=left;verticalAlign=top;fontSize=12;labelBackgroundColor=none;whiteSpace=wrap;rounded=1;strokeColor={stroke};"
               "dashed=1;spacing=8;" + F, 0, yy + 6, cw, bh, parent=f"legend-container-{sfx}")
        yy += bh + 16


def packet_walk(sfx, x, y, w, color, fill, title, hops):
    H = 210
    vertex(f"frame-walk-{sfx}", "", f"rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeColor={color};dashed=1;" + F, x, y, w, H)
    vertex(f"walk-{sfx}-title", f'<b style="color:{color}">{title}</b>',
           "text;html=1;align=left;verticalAlign=top;fontSize=13;labelBackgroundColor=none;whiteSpace=wrap;" + F,
           x + 14, y + 8, w - 28, 24)
    nodes, segs = hops[0::2], hops[1::2]
    NW, NH = 150, 46
    gap = (w - 40 - len(nodes) * NW) / (len(nodes) - 1)
    ny = y + 130
    ids = []
    for i, n in enumerate(nodes):
        nx = x + 20 + i * (NW + gap)
        nid = f"walk-{sfx}-n{i}"
        vertex(nid, n, f"rounded=1;whiteSpace=wrap;html=1;fillColor=light-dark(#FFFFFF,#1E1E1E);strokeColor={color};strokeWidth=2;"
               "fontSize=11;fontStyle=1;" + F, round(nx), ny, NW, NH)
        ids.append((nid, nx))
    for i, s in enumerate(segs):
        (a_id, axx), (b_id, _) = ids[i], ids[i + 1]
        cx, cw = axx + NW + 8, gap - 16
        if s[0] == "|":
            vertex(f"walk-{sfx}-brk{i}", f"<b>{s[1]}</b>",
                   f"text;html=1;align=center;verticalAlign=middle;fontSize=11;whiteSpace=wrap;rounded=1;dashed=1;strokeColor={color};"
                   f"fillColor=none;fontColor={color};" + F, round(cx), y + 40, round(cw), 128)
            continue
        lab, src, dst, nt = s
        edge(f"walk-{sfx}-e{i}", a_id, b_id, color, ex=(1, 0.5), en=(0, 0.5), both=False, raw=True)
        vertex(f"walk-{sfx}-hdr{i}",
               f"<b>src</b> {src}<br><b>dst</b> {dst}" + (f"<br><i style='font-size:10px'>{nt}</i>" if nt else ""),
               "text;html=1;align=left;verticalAlign=top;fontSize=11;whiteSpace=wrap;rounded=1;strokeColor=#545B64;"
               "fillColor=light-dark(#FFFFFF,#1E1E1E);spacing=5;" + F, round(cx), y + 40, round(cw), 80)
        if lab:
            badge(f"walk-{sfx}-b{i}", lab, round(axx + NW + 10), ny + NH + 2, fill)
    return H


def title_block(t, s, width):
    vertex("title-group", "", "group;" + F, LEFT_X, 30, width, 90, extra=' connectable="0"')
    vertex("title-text", t, "text;html=1;resizable=1;points=[];autosize=1;align=left;verticalAlign=top;spacingTop=-4;fontSize=30;fontStyle=1;" + F,
           0, 0, 1600, 42, parent="title-group")
    vertex("subtitle-text", s, "text;html=1;resizable=0;points=[];autosize=1;align=left;verticalAlign=top;spacingTop=-4;fontSize=16;" + F,
           5, 42, 2400, 25, parent="title-group")
    vertex("title-separator", "", "line;strokeWidth=2;html=1;fontSize=14;strokeColor=#FF9900;" + F,
           5, 72, width - 10, 10, parent="title-group")


def page_architecture():
    cells.clear()
    title_block("AWS Database Workshop - one Engine App per data type (Frankfurt)",
                f"https://{DOMAIN}/&lt;engine&gt;/ → one HTTPS ALB → ten EC2 Engine Apps. Each app seeds its own e-commerce data into its own Engine, "
                "reads it back and shows both on a web page.", TOTAL_W)
    group("aws-cloud", "AWS Cloud", "cloud", CLOUD_X, CLOUD_Y, CLOUD_W, CLOUD_H)
    group("region", "Europe (Frankfurt) eu-central-1", "region", CLOUD_X + 20, CLOUD_Y + 40, CLOUD_W - 40, CLOUD_H - 60)
    group("vpc", "VPC dbws-vpc 10.20.0.0/16", "vpc", VPC_X, VPC_Y, VPC_W, VPC_H)

    actor("users-container", "Workshop participants", "users", USERS_X, MID - 65, 140, 130, f"browser · {CLIENT_IP} (example)")
    actor("dest-internet", "Internet: code &amp; packages", "internet_alt2", DEST_X, MID - 80, 200, 160,
          f"github.com (Engine App code)<br>pypi.org (Python packages)<br>AL2023 dnf repos<br><i>example: {GH_IP}:443</i>")
    svc("r53", R53_X, CLOUD_Y + 75, "net", "route_53", "Route 53", f"A alias → ALB", "DNS", res=True)

    # ---------------- VPC level
    alb_x = ax(1, 2)
    igw_x = alb_x
    svc("igw", igw_x, IGW_Y, "net", "internet_gateway", "Internet gateway", "DNAT in · 1:1 NAT", "Internet gateway", res=False)

    for i, az in enumerate(AZS):
        x0 = AZ_X[i] + 20
        group(f"az-{az}", f"Availability Zone eu-central-1{az}", "az", AZ_X[i], AZ_Y, AZ_W, AZ_H, extra=RIGHT)
        # public subnet
        sid = f"sn-pub-{az}"
        group(sid, f"dbws-public-{az} (public) {CIDR['pub'][i]}", "pub", x0, Y_PUB, SUB_W, PUB_H if i == 1 else 180, extra=RIGHT)
        if i != 1:
            small_svc(f"albnode-{az}", SLOT[2], 40, "net", "application_load_balancer", f"dbws-alb node {az}", ALB_IPS[i],
                      "Load balancer node", parent=sid)
            note(f"pub-note-{az}", f"<b>Public subnet {az}</b>: only the ALB node ({ALB_IPS[i]}) and NAT GW {az} "
                 f"({NAT_IPS[i]} + Elastic IP) have addresses here. Engine Apps and Engines have no public IP.",
                 x0 + SLOT[3], Y_PUB + 50, 460, 60, size=11)
        child_svc(f"nat-{az}", sid, SLOT[0], 40, "net", "nat_gateway", f"NAT GW {az}", f"{NAT_IPS[i]} + EIP", "NAT gateway")
        rt(f"rt-pub-{az}", f"dbws-rt-public-{az}", [("10.20.0.0/16", "local"), ("0.0.0.0/0", "IGW")], SLOT[1], 40, w=160, parent=sid)
        # app subnet
        sid = f"sn-app-{az}"
        group(sid, f"dbws-app-{az} (private) {CIDR['app'][i]}", "priv", x0, Y_APP, SUB_W, APP_H, extra=RIGHT)
        for eid, lab, azi, slot, ip, _ in APPS:
            if azi == i:
                child_svc(f"app-{eid}", sid, SLOT[slot], 40, "compute", "ec2", f"{lab} App", f"{ip}:8000", "Engine App", res=True)
        rt(f"rt-app-{az}", f"dbws-rt-app-{az}",
           [("10.20.0.0/16", "local"), ("0.0.0.0/0", f"NAT GW {az}"), ("pl-s3", "S3 gateway endpoint"), ("pl-dynamodb", "DynamoDB gateway endpoint")],
           SLOT[4], 40, parent=sid)
        # data subnet
        sid = f"sn-data-{az}"
        group(sid, f"dbws-data-{az} (private) {CIDR['data'][i]}", "priv", x0, Y_DATA, SUB_W, DATA_H, extra=RIGHT)
        for eid, shape, name, sub, ip, title, cat in VPC_ENGINES:
            if APP[eid][2] == i:
                child_svc(f"db-{eid}", sid, SLOT[APP[eid][3]], 40, cat, shape, name, f"{sub}<br>{ip}", title, res=True)
        small_svc(f"vpce-sm-{az}", x0 + SLOT[4], Y_DATA + 40, "net", "endpoints", "Secrets Manager", SM_ENI[i], "Interface endpoint")
        rt(f"rt-data-{az}", f"dbws-rt-data-{az}", [("10.20.0.0/16", "local")], SLOT[4], 150, parent=sid,
           note="no internet route")
    # the ALB is one resource with a node in each public subnet; drawn once in AZ-b
    svc("alb", alb_x, Y_PUB + 40, "net", "application_load_balancer", "dbws-alb (HTTPS 443)",
        f"node b · {ALB_IPS[1]}", "Load balancer", res=False)
    rules = "".join(f"<tr><td>{prio}</td><td>/{eid}/*</td><td>tg-{eid}</td><td>{lab} App {ip}:8000</td></tr>"
                    for eid, lab, _, _, ip, prio in sorted(APPS, key=lambda a: a[5]))
    vertex("alb-rules", f"<b>ALB listener HTTPS :443 → path rules</b> <i>(HTTP :80 redirects to 443)</i>"
           "<table style='font-size:10px;margin-top:4px' cellpadding='1'>"
           "<tr style='color:#545B64'><td><b>prio</b></td><td><b>path</b></td><td><b>target group</b></td><td><b>target (EC2 IP:port)</b></td></tr>"
           f"{rules}<tr><td>default</td><td>/</td><td>fixed-response</td><td>Dashboard HTML</td></tr></table>",
           "rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=top;fontSize=10;spacing=6;fillColor=none;strokeColor=#8C4FFF;" + F,
           ax(1, 3), Y_PUB + 24, 500, 228)
    # Keyspaces interface endpoint next to the Keyspaces App; gateway endpoints under the DynamoDB and S3 Apps
    small_svc("vpce-ks", ax(0, 2), Y_DATA + 40, "net", "endpoints", "Keyspaces", f"{KS_ENI} (+ ENIs b, c)", "Interface endpoint")
    small_svc("gwe-ddb", ax(0, 0), Y_GWE, "net", "endpoints", "DynamoDB", "route target in dbws-rt-app-*", "Gateway endpoint")
    small_svc("gwe-s3", ax(0, 1), Y_GWE, "net", "endpoints", "S3", "route target in dbws-rt-app-*", "Gateway endpoint")

    # ---------------- regional services (outside the VPC)
    note("reg-title", "<b>Regional services outside the VPC</b> - reached only through VPC endpoints, never through the NAT gateway",
         ax(0, 3), Y_REG - 34, 900, 20, color="#00A4A6", size=12)
    svc("ddb", ax(0, 0), Y_REG, "db", "dynamodb", "DynamoDB", "dbws-cart", "Key-value DB", res=True)
    svc("s3", ax(0, 1), Y_REG, "storage", "s3", "Amazon S3", "dbws-images-*", "Object store", res=True)
    svc("keyspaces", ax(0, 2), Y_REG, "db", "keyspaces", "Keyspaces", "dbws.activity_by_user", "Wide-column DB", res=True)
    sm_cx = AZ_X[1] + 20 + SEC_LANE
    svc("secrets", sm_cx - 60, Y_REG, "sec", "secrets_manager", "Secrets Manager", "dbws/* secrets", "Secrets store", res=True)

    # ================================================================ Scenario 1
    edge("e-dns", "users-container", "r53", C_IN, ex=(0.5, 0), en=(0, 0.5), pts=[(USERS_X + 70, CLOUD_Y + 135)])
    badge("step-s1-1a", "1a", USERS_X + 80, MID - 110, B_S1)
    edge("e-in", "users-container", "igw", C_IN, ex=(1, 0.5), en=(0, 0.5))
    badge("step-s1-2b", "2b", R53_X + 150, MID - 40, B_S1)
    edge("e-igw-alb", "igw", "alb", C_IN, ex=(0.5, 1), en=(0.5, 0))
    badge("step-s1-3b", "3b", igw_x + 66, AZ_Y - 60, B_S1)
    # ALB -> Engine Apps: exits sorted by target x; on each side the farthest target takes the highest lane
    targets = sorted(APPS, key=lambda a: ax(a[2], a[3]))
    alb_cx = alb_x + 60
    lane0 = Y_PUB + PUB_H + 20
    left = [t for t in targets if ax(t[2], t[3]) + 60 < alb_cx - 30]
    right = [t for t in targets if ax(t[2], t[3]) + 60 > alb_cx + 30]
    for k, t in enumerate(targets):
        eid, lab, azi, slot, ip, prio = t
        exx = round((6 + k * 12) / 120, 3)
        sx = alb_x + round(120 * exx)
        tx = ax(azi, slot) + 60
        if t in left:
            lane = lane0 + left.index(t) * 12
        elif t in right:
            lane = lane0 + (len(right) - 1 - right.index(t)) * 12
        else:
            lane = None
        if lane is None:            # straight below the ALB
            enx = round((sx - ax(azi, slot)) / 120, 3)
            edge(f"e-alb-{eid}", "alb", f"app-{eid}", C_IN, ex=(exx, 1), en=(enx, 0))
            tx = sx
        else:
            edge(f"e-alb-{eid}", "alb", f"app-{eid}", C_IN, ex=(exx, 1), en=(0.5, 0), pts=[(sx, lane), (tx, lane)])
        if eid == "dynamodb":     # the orange NAT line runs on the right of this arrow
            note(f"path-{eid}", f"<b>/{eid}/*</b>", tx - 88, Y_APP + 6, 84, 16, color=C_IN, align="right")
        else:
            note(f"path-{eid}", f"<b>/{eid}/*</b>", tx + 5, Y_APP + 6, 120, 16, color=C_IN)
    badge("step-s1-4c", "4c", alb_x - 82, Y_PUB + 168, B_S1)

    # Engine App -> data (vertical, protocol label on the right of the line, step badge above the target)
    for eid, lab, azi, slot, ip, _ in APPS:
        cx = ax(azi, slot) + 60
        tgt = {"dynamodb": "gwe-ddb", "s3": "gwe-s3", "keyspaces": "vpce-ks"}.get(eid, f"db-{eid}")
        edge(f"e-app-{eid}", f"app-{eid}", tgt, C_IN, ex=(0.5, 1), en=(0.5, 0))
        note(f"proto-{eid}", PROTO[eid], cx + 16, Y_APP + APP_H + 6, 150, 40)
        badge(f"step-s1-5d-{eid}", "5d", cx + 6, Y_DATA + 8, B_S1)
        if eid in IAM_APPS:
            iam(f"iam-{eid}", cx - 13, Y_APP + APP_H + 30)
    # endpoint -> regional service (6-Con-D), IAM checked by the service
    for src, tgt, slot in (("gwe-ddb", "ddb", 0), ("gwe-s3", "s3", 1), ("vpce-ks", "keyspaces", 2)):
        cx = ax(0, slot) + 60
        edge(f"e-{src}-{tgt}", src, tgt, C_IN, ex=(0.5, 1), en=(0.5, 0))
        badge(f"step-s1-6d-{tgt}", "6d", cx + 18, Y_REG - 70, B_S1)
        iam(f"iam-{tgt}", cx - 13, Y_REG - 64)

    # ================================================================ Scenario 2
    nat_a_x = ax(0, 0)
    edge("e-boot-nat", "app-dynamodb", "nat-a", C_EG, ex=(0.85, 0), en=(0.85, 1))
    badge("step-s2-1a", "1a", nat_a_x + 108, Y_PUB + 168, B_S2)
    edge("e-nat-igw", "nat-a", "igw", C_EG, ex=(0.5, 0), en=(0.15, 1), pts=[(nat_a_x + 60, AZ_Y - 20), (igw_x + 18, AZ_Y - 20)])
    badge("step-s2-2a", "2a", nat_a_x + 70, AZ_Y - 54, B_S2)
    edge("e-igw-dest", "igw", "dest-internet", C_EG, ex=(1, 0.5), en=(0, 0.5))
    badge("step-s2-3a", "3a", igw_x + 150, MID - 40, B_S2)
    # secrets: password apps -> Secrets Manager interface endpoint in the same AZ (red dashed)
    for i, az in enumerate(AZS):
        users = [a for a in APPS if a[0] in PASSWORD_APPS and a[2] == i]
        vx = ax(i, 4)
        for k, (eid, lab, azi, slot, ip, _) in enumerate(users):
            lane = Y_APP + 180 + k * 18
            entry = [0.3, 0.6][k]
            edge(f"e-sec-{eid}", f"app-{eid}", f"vpce-sm-{az}", C_SEC, ex=(0.9, 1), en=(entry, 0), dashed=True, width=2,
                 pts=[(ax(azi, slot) + 108, lane), (vx + round(120 * entry), lane)])
        badge(f"step-s2-4b-{az}", "4b", vx - 84, Y_APP + 186, B_S2)
        lane_x = AZ_X[i] + 20 + SEC_LANE
        if i == 1:
            pts, en = [(lane_x, Y_DATA + 85)], (0.5, 0)
        else:
            yy = Y_REG + (30 if i == 0 else 90)
            pts, en = [(lane_x, Y_DATA + 85), (lane_x, yy)], ((0, 0.25) if i == 0 else (1, 0.75))
        edge(f"e-vpce-sm-{az}", f"vpce-sm-{az}", "secrets", C_SEC, ex=(1, 0.5), en=en, pts=pts, dashed=True, width=2)
        iam(f"iam-sm-{az}", lane_x - 13, VPC_Y + VPC_H + 12)
    badge("step-s2-5b", "5b", sm_cx + 18, VPC_Y + VPC_H + 8, B_S2)

    # ================================================================ legends
    LY, LH = CLOUD_Y, CLOUD_H
    s1 = [
        ("1a", "DNS lookup", f"The browser asks Route 53 for {DOMAIN} (Con-A, UDP 53 to {R53_NS} (Route 53 name server, example)). The alias A record returns the three ALB node public IPs, e.g. {ALB_PUB} (ALB node b public IP)."),
        ("2b", "Browser to IGW (HTTPS 443)", f"The browser opens Con-B to {ALB_PUB}:443. The IGW does DNAT: dst → {ALB_IPS[1]} (ALB node b private IP). dbws-rt-public-b 10.20.0.0/16 → local delivers it."),
        ("3b", "IGW to ALB", f"The ALB terminates Con-B (TLS, ACM certificate for {DOMAIN}). HTTP :80 only redirects to HTTPS."),
        ("4c", "ALB path rule to Engine App", "The listener rule matches the path and forwards to that app's target group: /dynamodb/* → tg-dynamodb → DynamoDB App 10.20.10.11:8000. The ALB opens Con-C (HTTP 8000). Cross-zone is on: any ALB node reaches any app. sg-app-&lt;engine&gt; allows 8000 only from sg-alb."),
        ("5d", "Engine App to its Engine", "The app opens Con-D to its own Engine only, with the protocol written on the arrow (PostgreSQL wire, MongoDB wire, RESP, CQL, HTTPS API). Each engine SG allows its port only from that one app's SG. TLS everywhere."),
        ("6d", "Through a VPC endpoint", f"DynamoDB and S3: dbws-rt-app-a pl-dynamodb / pl-s3 → gateway endpoint (no ENI, no IP). Keyspaces: cassandra.eu-central-1.amazonaws.com resolves to {KS_ENI} (interface endpoint ENI a private IP). The service checks the request against the app's IAM role (SigV4)."),
    ]
    s2 = [
        ("1a", "Engine App to NAT GW (boot)", f"UserData clones the Engine App code and installs packages: Con-A from 10.20.10.11 (DynamoDB App private IP) to {GH_IP}:443 (github.com, example). dbws-rt-app-a 0/0 → NAT GW a. SNAT by NAT GW: src → {NAT_IPS[0]} (NAT GW a private IP)."),
        ("2a", "NAT GW to IGW", "dbws-rt-public-a 0/0 → IGW. The NAT GW rewrites the source but does not terminate the connection, so it stays Con-A."),
        ("3a", "IGW to github.com / pypi.org", f"IGW 1:1 NAT: src {NAT_IPS[0]} → {NAT_EIP} (NAT GW a Elastic IP). Return: IGW DNAT back, then the NAT GW reverses its SNAT."),
        ("4b", "Engine App to Secrets endpoint", f"Apps that log in with a password (Aurora, Redshift, DocumentDB, ElastiCache, InfluxDB) read their secret at start: Con-B to secretsmanager.eu-central-1.amazonaws.com:443, which private DNS resolves to the endpoint ENI in the same AZ, e.g. {SM_ENI[0]} (Secrets endpoint ENI a private IP)."),
        ("5b", "Endpoint to Secrets Manager", "PrivateLink carries Con-B to Secrets Manager; no NAT, no internet. The app role may read only its own dbws/&lt;engine&gt; secret."),
    ]
    sgtxt = ("<b>Security groups</b><br>sg-alb: in 443, 80 from AllowedCidr<br>"
             "sg-app-&lt;engine&gt;: in 8000 from sg-alb<br>"
             "sg-db-&lt;engine&gt;: in engine port from sg-app-&lt;engine&gt; only (5432, 5439, 6379-6380, 8086, 8182, 27017, 443)<br>"
             "sg-vpce: in 443, 9142 from the three app subnets<br>"
             "<b>Who translates</b><br>IGW = DNAT on the way in, the reverse on the way out (1:1 per public IP). NAT GW = SNAT for outbound connections.<br>"
             "<b>IP addresses</b><br>EC2 IPs are fixed in the template. Engine, ALB, NAT and endpoint IPs are examples from the subnet ranges; "
             "internet IPs are RFC 5737 examples.")
    legend_panel("s1", LEFT_X, LY, LP_W, LH, "Scenario 1 - Participant-initiated (inbound)",
                 "A participant opens an Engine App page and presses Seed or Read.<br>"
                 "<b>Connection A (Con-A)</b> = browser ↔ Route 53 (DNS)<br>"
                 "<b>Connection B (Con-B)</b> = browser ↔ ALB (the ALB terminates TLS)<br>"
                 "<b>Connection C (Con-C)</b> = ALB ↔ Engine App (new connection)<br>"
                 "<b>Connection D (Con-D)</b> = Engine App ↔ its Engine (new connection)",
                 s1, B_S1, [("sg", sgtxt, "#666666", 270)], step_h=104)
    key = ("<b>How to read this page</b><br>"
           "• <b>Box titles</b> = resource type: Internet gateway, NAT gateway, Load balancer, Interface endpoint, Gateway endpoint, "
           "Engine App, Secrets store; data layer = &lt;data category&gt; DB (Relational DB, Graph DB, …) or Object store.<br>"
           "• <b>Path label</b> above an Engine App = the ALB rule that sends traffic to it.<br>"
           "• <b>Text on a data arrow</b> = protocol, port and how the app authenticates.<br>"
           "• <b style='color:#DD344C'>IAM role icon</b> on a line = the Engine App's IAM role authorizes this call (SigV4); no password.<br>"
           "• <b style='color:#D13212'>Red dashed</b> = secret retrieval through the Secrets Manager interface endpoint of the same AZ.<br>"
           "• SSM endpoints (ssm, ssmmessages, ec2messages) exist in the data subnets for Session Manager but are not drawn.<br>"
           "• One Engine App talks to exactly one Engine; its IAM role and security group allow nothing else.")
    legend_panel("s2", RP_X, LY, RP_W, LH, "Scenario 2 - Engine App-initiated (outbound, at boot)",
                 "Every Engine App downloads its code at boot (drawn for the DynamoDB App).<br>"
                 "<b>Connection A (Con-A)</b> = Engine App ↔ github.com / pypi.org. The NAT gateway rewrites the source address but does not terminate the connection.<br>"
                 "<b>Connection B (Con-B)</b> = Engine App ↔ Secrets Manager through the interface endpoint (red dashed).",
                 s2, B_S2, [("key", key, "#DD344C", 330)], step_h=104)

    # ================================================================ packet walks
    WY = CLOUD_Y + CLOUD_H + 40
    walk1 = ["Browser", ("1a", f"{CLIENT_IP}:53001", f"{R53_NS}:53 (Route 53 NS)", "answer: ALB public IPs"),
             "Route 53", ("|", "Con-A ends · the browser opens Con-B to the ALB"),
             "Browser", ("2b", f"{CLIENT_IP}:51514", f"{ALB_PUB}:443 (ALB node b public)", "as sent by the browser"),
             "Internet gateway", ("3b", f"{CLIENT_IP}:51514", f"{ALB_IPS[1]}:443 (ALB node b private)", "DNAT by IGW: dst public → private"),
             "ALB node b", ("|", "Con-B ends at the ALB (TLS) · rule /aurora/* → tg-aurora"),
             "ALB node b", ("4c", f"{ALB_IPS[1]}:40112", "10.20.10.14:8000 (Aurora App)", "cross-zone b → a, local route"),
             "Aurora App (EC2)", ("|", "the app opens Con-D to its Engine"),
             "Aurora App (EC2)", ("5d", "10.20.10.14:44120", "10.20.20.30:5432 (Aurora writer)", "PostgreSQL wire, TLS, local route"),
             "Aurora writer"]
    walk2 = ["DynamoDB App (EC2)", ("1a", "10.20.10.11:43210", f"{GH_IP}:443 (github.com)", "dbws-rt-app-a 0/0 → NAT GW a"),
             "NAT GW a", ("2a", f"{NAT_IPS[0]}:1024 (NAT GW a private)", f"{GH_IP}:443", "SNAT by NAT GW: src = NAT GW private IP"),
             "Internet gateway", ("3a", f"{NAT_EIP}:1024 (NAT GW a EIP)", f"{GH_IP}:443", "IGW 1:1 NAT: src private → EIP"),
             "github.com", ("|", "code installed · the Aurora App starts and opens Con-B"),
             "Aurora App (EC2)", ("4b", "10.20.10.14:45000", f"{SM_ENI[0]}:443 (Secrets endpoint ENI a)", "private DNS → interface endpoint"),
             "Secrets endpoint a", ("5b", "10.20.10.14:45000", "Secrets Manager", "PrivateLink, not terminated"),
             "Secrets Manager"]
    h1 = packet_walk("s1", LEFT_X, WY, TOTAL_W, C_IN, B_S1,
                     "Scenario 1 packet walk - request direction (replies swap src and dst and take the same hops back)", walk1)
    h2 = packet_walk("s2", LEFT_X, WY + h1 + 24, TOTAL_W, C_EG, B_S2,
                     "Scenario 2 packet walk - request direction (replies swap src and dst; each NAT reverses its own rewrite)", walk2)
    pw, ph = LEFT_X + TOTAL_W + 40, WY + h1 + 24 + h2 + 40
    return (f'<diagram name="Architecture" id="architecture">'
            f'<mxGraphModel dx="{pw}" dy="{ph}" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="{pw}" pageHeight="{ph}" math="0" shadow="0">'
            '<root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(cells) + '</root></mxGraphModel></diagram>')


# ---------------------------------------------------------------- page 2: data type mapping
MAP = [  # (data type, category, shape, cat, engine, sub, Domain slice, Read pattern, status)
    ("Structured", "Relational", "aurora", "db", "Aurora PostgreSQL", "Serverless v2", "customers &amp; orders", "SQL JOIN orders ↔ customers: top customers by revenue", "ok"),
    ("Structured", "Columnar", "redshift", "net", "Redshift Serverless", "8 RPU base", "sales analytics", "GROUP BY month, category over the sales fact table", "ok"),
    ("Semi-structured", "Key-value", "dynamodb", "db", "DynamoDB", "on-demand", "shopping cart", "Query by partition key CART#&lt;user&gt;", "ok"),
    ("Semi-structured", "In-memory", "elasticache", "db", "ElastiCache", "Serverless Valkey", "sessions &amp; leaderboard", "ZREVRANGE top 10 + session hash with TTL", "ok"),
    ("Semi-structured", "Wide column", "keyspaces", "db", "Keyspaces", "Cassandra (CQL)", "user activity feed", "last 20 events of one user (clustering by time DESC)", "ok"),
    ("Semi-structured", "Time-series", "timestream", "db", "Timestream for<br>InfluxDB", "InfluxDB v2", "sensor &amp; metric data", "Flux aggregateWindow: hourly mean per warehouse. Timestream for LiveAnalytics is closed to new customers.", "ok"),
    ("Semi-structured", "Immutable ledger", "quantum_ledger_database", "gen", "QLDB", "end of support", "-", "", "gone"),
    ("Semi-structured", "Geospatial", "elasticsearch_service", "net", "OpenSearch", "geo_point", "store locations", "geo_distance: stores within 25 km. The infographic lists Keyspaces here, but it has no geo queries.", "ok"),
    ("Semi-structured", "Graph", "neptune", "db", "Neptune", "Serverless", "bought-together graph", "openCypher: customers who bought X also bought Y", "ok"),
    ("Semi-structured", "Document", "documentdb_with_mongodb_compatibility", "db", "DocumentDB", "MongoDB API", "product catalog", "find by nested attribute + aggregate by category", "ok"),
    ("Unstructured", "Blob", "s3", "storage", "Amazon S3", "SSE · versioning", "product images", "list a prefix, GET an object with its metadata", "ok"),
    ("Unstructured", "Text search", "elasticsearch_service", "net", "OpenSearch", "Service", "product search", "multi_match with fuzziness. CloudSearch is closed to new customers.", "ok"),
]
TYPE_COLOR = {"Structured": "#248814", "Semi-structured": "#C925D1", "Unstructured": "#147EBA"}


def page_mapping():
    cells.clear()
    ROW, TOP = 150, 260
    X_TYPE, X_CAT, X_ENG, X_SLICE = 80, 460, 860, 1060
    W = 1500
    title_block("How to choose a database on AWS - data type → category → Engine",
                "The AWS column of the \"How to Choose Database\" infographic, mapped to the ten Engines and the e-commerce Domain of the workshop.", W + 740)
    for lab, x, w in (("1 Data type", X_TYPE, 260), ("2 Category", X_CAT, 220), ("3 Engine + Domain slice", X_ENG, 600)):
        vertex(f"col-{lab[0]}", f"<b>{lab[2:]}</b>", "text;html=1;align=left;verticalAlign=middle;fontSize=14;fontStyle=1;fontColor=#232F3E;" + F,
               x + 40, TOP - 70, w, 28)
        vertex(f"step-col-{lab[0]}", lab[0], f"rounded=1;whiteSpace=wrap;html=1;fillColor={B_S1};strokeColor=default;fontColor=#FFFFFF;fontStyle=1;fontSize=16;{F}"
               "shadow=1;glass=0;strokeWidth=2;align=center;verticalAlign=middle;labelBackgroundColor=none;", x, TOP - 70, 28, 28)
    types = []
    for t in TYPE_COLOR:
        rows = [i for i, m in enumerate(MAP) if m[0] == t]
        y0, y1 = TOP + rows[0] * ROW, TOP + rows[-1] * ROW + 120
        types.append((t, rows, (y0 + y1) // 2))
    for t, rows, cy in types:
        c = TYPE_COLOR[t]
        vertex(f"type-{t}", f"<b>{t}</b>", f"rounded=1;whiteSpace=wrap;html=1;fillColor=light-dark(#FFFFFF,#1E1E1E);strokeColor={c};strokeWidth=3;"
               f"fontSize=18;fontColor={c};shadow=1;" + F, X_TYPE, cy - 40, 260, 80)
    for i, (t, cat, shape, catk, eng, sub, slice_, read, status) in enumerate(MAP):
        y = TOP + i * ROW
        c = TYPE_COLOR[t]
        vertex(f"cat-{i}", f"<b>{cat}</b>", f"rounded=1;whiteSpace=wrap;html=1;fillColor=light-dark(#FFFFFF,#1E1E1E);strokeColor={c};strokeWidth=2;"
               f"fontSize=13;fontColor={c};" + F, X_CAT, y + 35, 220, 50)
        edge(f"m-type-cat-{i}", f"type-{t}", f"cat-{i}", c, ex=(1, 0.5), en=(0, 0.5), both=False, raw=True)
        svc(f"eng-{i}", X_ENG, y, catk, shape, eng, sub, f"{cat} DB" if cat not in ("Blob",) else "Object store", res=True)
        gone = status == "gone"
        edge(f"m-cat-eng-{i}", f"cat-{i}", f"grp-eng-{i}", "#D13212" if gone else c, ex=(1, 0.5), en=(0, 0.5), both=False, raw=True)
        if gone:
            cells[-1] = cells[-1].replace("strokeWidth=2;", "strokeWidth=2;dashed=1;")
        txt = (f"<b style='color:#D13212'>✗ Not available</b><br>QLDB reached end of support on 31 July 2025. "
               "Ledger-style needs: Aurora PostgreSQL with an append-only, hash-chained audit table.") if gone else \
              f"<b>Domain slice:</b> {slice_}<br><b>Read:</b> {read}"
        vertex(f"slice-{i}", txt, "text;html=1;align=left;verticalAlign=middle;fontSize=12;whiteSpace=wrap;rounded=1;"
               f"strokeColor={'#D13212' if gone else '#545B64'};dashed={1 if gone else 0};fillColor=none;spacing=8;" + F,
               X_SLICE, y + 30, 400, 60)
    LX, LYY = X_SLICE + 400 + 60, 150
    LH = TOP + len(MAP) * ROW - LYY
    steps = [
        ("1", "Data type", "What shape does the data have? Structured (fixed schema, rows and columns), semi-structured (flexible keys, documents, graphs, series) or unstructured (files, free text)."),
        ("2", "Category", "Which access pattern dominates? Joins and transactions, scans over columns, lookups by key, microsecond reads, time windows, relationships, full-text and geo queries."),
        ("3", "Engine + Domain slice", "The AWS Engine used in the workshop and the part of the e-commerce Domain its Engine App seeds and reads. One Engine App per Engine."),
    ]
    vertex("legend-bg", "", "verticalLabelPosition=bottom;verticalAlign=top;html=1;shape=mxgraph.basic.rect;fillColor2=none;strokeWidth=1;"
           f"size=20;indent=5;fillColor=light-dark(#EDF3FF,#305363);strokeColor=#6c8ebf;", LX, LYY, 640, LH)
    vertex("legend-container", "", "group", LX + 20, LYY + 30, 600, LH - 60, extra=' connectable="0"')
    yy = 0
    for n, tt, d in steps:
        g = f"step-{n}-legend"
        vertex(g, "", "group;" + F, 0, yy, 600, 110, parent="legend-container", extra=' connectable="0"')
        vertex(f"step-{n}-badge-legend", n, f"rounded=1;whiteSpace=wrap;html=1;fillColor={B_S1};strokeColor=default;fontColor=#FFFFFF;fontStyle=1;fontSize=22;"
               "labelBackgroundColor=none;" + F + "shadow=1;glass=0;strokeWidth=2;", 0, 2, 40, 38, parent=g)
        vertex(f"step-{n}-desc-legend", f'<div><b>{tt}</b></div><div><span style="{SPAN}">{d}</span></div>',
               "text;html=1;align=left;verticalAlign=top;spacingTop=-4;fontSize=14;labelBackgroundColor=none;whiteSpace=wrap;" + F,
               52, 0, 548, 110, parent=g)
        yy += 120
    vertex("legend-notes", f'<div style="{SPAN}"><b>Not in the workshop (closed or gone)</b><br>'
           "• QLDB - end of support 31 July 2025<br>"
           "• CloudSearch - closed to new customers; use OpenSearch Service<br>"
           "• Timestream for LiveAnalytics - closed to new customers; use Timestream for InfluxDB<br><br>"
           "<b>Infographic corrections</b><br>"
           "• Keyspaces is listed under Geospatial, but it has no geo queries; the workshop uses OpenSearch geo_point.<br>"
           "• The infographic labels the time-series row as \"Graph\"; it is Time-series.<br><br>"
           "<b>Colors</b><br><font color='#248814'>━━</font> Structured · <font color='#C925D1'>━━</font> Semi-structured · "
           "<font color='#147EBA'>━━</font> Unstructured · <font color='#D13212'>┅┅</font> not available</div>",
           "text;html=1;align=left;verticalAlign=top;fontSize=13;labelBackgroundColor=none;whiteSpace=wrap;rounded=1;strokeColor=#666666;dashed=1;spacing=10;" + F,
           0, yy + 10, 600, 250, parent="legend-container")
    pw, ph = LX + 640 + 40, TOP + len(MAP) * ROW + 40
    return (f'<diagram name="Data type mapping" id="data-type-mapping">'
            f'<mxGraphModel dx="{pw}" dy="{ph}" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="{pw}" pageHeight="{ph}" math="0" shadow="0">'
            '<root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(cells) + '</root></mxGraphModel></diagram>')


xml = '<mxfile host="Electron" version="29.6.1">' + page_architecture() + page_mapping() + '</mxfile>'
open(OUT, "w").write(xml)
print("written", OUT)
