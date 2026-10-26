#!/usr/bin/env python3
"""Generate Enterprise Internal Architecture on AWS (Frankfurt) draw.io diagram."""
import sys
from xml.sax.saxutils import escape

OUT = sys.argv[1] if len(sys.argv) > 1 else None
F = "fontFamily=Helvetica;"
PTS = "points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],[1,1,0],[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],[1,0.75,0]];"
GPTS = "points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],[1,1],[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];"

CAT = {  # tint, stroke, icon fill
    "net": ("#EDE7F6", "#8C4FFF", "#8C4FFF"),
    "compute": ("#FFF2E8", "#ED7100", "#ED7100"),
    "db": ("#F5E6F7", "#C925D1", "#C925D1"),
    "storage": ("#E8F5E9", "#3F8624", "#7AA116"),
    "sec": ("#FFEBEE", "#DD344C", "#DD344C"),
    "mgmt": ("#FCE4EC", "#E7157B", "#E7157B"),
    "mig": ("#E0F2F1", "#01A88D", "#01A88D"),
    "gen": ("#F5F5F5", "#666666", "#232F3D"),
}

cells = []


def a(s):
    return escape(s, {'"': "&quot;"})


def vertex(cid, value, style, x, y, w, h, parent="1", extra=""):
    cells.append(
        f'<mxCell id="{cid}" value="{a(value)}" style="{a(style)}" vertex="1" parent="{parent}"{extra}>'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def svc(cid, x, y, cat, shape, name, sub="", category="", res=True):
    tint, stroke, fill = CAT[cat]
    vertex(f"grp-{cid}", category,
           f"fillColor={tint};strokeColor={stroke};rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;fontStyle=1;fontSize=11;fontColor={stroke};{F}container=1;collapsible=0;shadow=1;strokeWidth=1.5;spacingTop=-2;",
           x, y, 120, 120)
    label = name + (f"<div><i>{sub}</i></div>" if sub else "")
    if res:
        st = (f"sketch=0;{PTS}outlineConnect=0;fontColor=#232F3E;fillColor={fill};strokeColor=#ffffff;dashed=0;"
              f"verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=10;fontStyle=0;aspect=fixed;"
              f"shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{shape};{F}shadow=1;")
    else:
        st = (f"sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor={fill};strokeColor=none;dashed=0;"
              f"verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=10;fontStyle=0;aspect=fixed;"
              f"pointerEvents=1;shape=mxgraph.aws4.{shape};{F}")
    vertex(cid, label, st, 36, 22, 48, 48, parent=f"grp-{cid}")


EDGE = f"edgeStyle=orthogonalEdgeStyle;html=1;endArrow=block;elbow=vertical;startArrow=none;endFill=1;strokeColor=#545B64;rounded=0;strokeWidth=1.5;{F}"


def edge(cid, src, tgt, label="", pts=(), ex=None, en=None, dashed=False, both=False, lx=0, ly=-10):
    st = EDGE
    if both:
        st = st.replace("startArrow=none;", "startArrow=block;startFill=1;")
    if dashed:
        st += "dashed=1;"
    if ex:
        st += f"exitX={ex[0]};exitY={ex[1]};exitDx=0;exitDy=0;"
    if en:
        st += f"entryX={en[0]};entryY={en[1]};entryDx=0;entryDy=0;"
    src = src if src.startswith("users") else f"grp-{src}"
    tgt = tgt if tgt.startswith("users") else f"grp-{tgt}"
    p = "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in pts)
    arr = f'<Array as="points">{p}</Array>' if pts else ""
    cells.append(f'<mxCell id="{cid}" style="{a(st)}" edge="1" parent="1" source="{src}" target="{tgt}">'
                 f'<mxGeometry relative="1" as="geometry">{arr}</mxGeometry></mxCell>')
    if label:
        cells.append(
            f'<mxCell id="{cid}-label" value="{a(label)}" style="{a("edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];labelBackgroundColor=none;fontSize=10;fontColor=#545B64;" + F)}" connectable="0" vertex="1" parent="{cid}">'
            f'<mxGeometry x="{lx}" y="{ly}" relative="1" as="geometry"><mxPoint as="offset"/></mxGeometry></mxCell>')


def badge(n, x, y):
    vertex(f"step-{n}", str(n),
           f"rounded=1;whiteSpace=wrap;html=1;fillColor=#007CBD;strokeColor=default;fontColor=#FFFFFF;fontStyle=1;fontSize=16;{F}shadow=1;glass=0;strokeWidth=2;align=center;verticalAlign=middle;labelBackgroundColor=none;",
           x, y, 28, 28)


def group(cid, label, kind, x, y, w, h, extra=""):
    styles = {
        "cloud": f"{GPTS}outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=14;fontStyle=1;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_aws_cloud;strokeColor=#232F3E;fillColor=light-dark(#232F3E0D,#232F3E0D);fillStyle=auto;verticalAlign=top;align=left;spacingLeft=30;fontColor=#232F3E;dashed=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;",
        "region": f"{GPTS}outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=14;fontStyle=1;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_region;strokeColor=#00A4A6;fillColor=light-dark(#0C7B7D0D,#0C7B7D0D);fillStyle=auto;verticalAlign=top;align=left;spacingLeft=30;fontColor=#00A4A6;dashed=1;container=0;pointerEvents=0;collapsible=0;recursiveResize=0;",
        "vpc": f"{GPTS}outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=14;fontStyle=1;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_vpc2;strokeColor=#8C4FFF;fillColor=light-dark(#8C4FFF0D,#8C4FFF0D);fillStyle=auto;verticalAlign=top;align=left;spacingLeft=30;fontColor=#8C4FFF;dashed=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;",
        "az": f"fillColor=none;strokeColor=#147EBA;dashed=1;verticalAlign=top;align=left;spacingLeft=10;fontStyle=1;fontSize=13;fontColor=#147EBA;whiteSpace=wrap;html=1;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;",
        "pub": f"{GPTS}outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=11;fontStyle=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_public_subnet;strokeColor=#248814;fillColor=light-dark(#2488140D,#2488140D);fillStyle=auto;verticalAlign=top;align=left;spacingLeft=30;fontColor=#248814;dashed=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;",
        "priv": f"{GPTS}outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=11;fontStyle=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_private_subnet;strokeColor=#147EBA;fillColor=light-dark(#147EBA0D,#147EBA0D);fillStyle=auto;verticalAlign=top;align=left;spacingLeft=30;fontColor=#147EBA;dashed=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;",
        "onprem": f"{GPTS}outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=13;fontStyle=1;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_corporate_data_center;strokeColor=light-dark(#7D8998,#D4D4D4);fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor=light-dark(#5A6C86,#D4D4D4);dashed=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;",
        "aux": f"rounded=0;fillColor=none;dashed=1;verticalAlign=top;align=left;spacingLeft=10;html=1;fontSize=12;fontStyle=1;strokeColor=#666666;fontColor=#666666;whiteSpace=wrap;container=1;pointerEvents=0;collapsible=0;",
    }
    vertex(cid, label, styles[kind] + F + extra, x, y, w, h)


