# -*- coding: utf-8 -*-
"""scene3d — POI 로 3D 웹 (v1.15).

선언형 씬 그래프 → 자체 완결 HTML (Three.js r160 은 cdnjs 에서, 셋업 JS 는 인라인).
서버 불필요. `webapp{}` 의 `html ...`, `render()` 템플릿, 또는 `file.write` 로 바로 쓴다.

    장면 = scene3d.scene({ bg: "#0b0e14" })
    scene3d.box(장면, { color: "#5b9dff", spin: true })
    scene3d.sphere(장면, { pos: [2, 0, 0], color: "#37d39b", float: true })
    scene3d.light(장면, "sun")
    scene3d.orbit(장면)
    html scene3d.render(장면, { height: 480 })

한국어 별칭: `삼차원` · `입체`.
"""
from __future__ import annotations

import json as _json
from types import SimpleNamespace

_CDN = "https://cdnjs.cloudflare.com/ajax/libs/three.js/0.160.0/three.module.min.js"
_CDN_ORBIT = ("https://cdnjs.cloudflare.com/ajax/libs/three.js/0.160.0/"
              "examples/jsm/controls/OrbitControls.min.js")  # (fallback: 인라인 미니 orbit)


class Scene(dict):
    """씬 그래프. dict 이므로 JSON 직렬화 그대로 된다."""

    def __init__(self, opts=None):
        super().__init__()
        o = dict(opts or {})
        self["bg"] = o.get("bg", "#0b0e14")
        self["camera"] = o.get("camera", [3, 3, 6])
        self["fov"] = o.get("fov", 55)
        self["orbit"] = o.get("orbit", False)
        self["autorotate"] = o.get("autorotate", False)
        self["grid"] = o.get("grid", False)
        self["shadows"] = o.get("shadows", True)
        self["nodes"] = []


def scene(opts=None):
    return Scene(opts)


def _add(sc, kind, opts):
    o = dict(opts or {})
    o["kind"] = kind
    o.setdefault("pos", [0, 0, 0])
    o.setdefault("color", "#8ea2c6")
    sc["nodes"].append(o)
    return sc


def box(sc, opts=None):      return _add(sc, "box", opts)
def sphere(sc, opts=None):   return _add(sc, "sphere", opts)
def plane(sc, opts=None):    return _add(sc, "plane", opts)
def cylinder(sc, opts=None): return _add(sc, "cylinder", opts)
def cone(sc, opts=None):     return _add(sc, "cone", opts)
def torus(sc, opts=None):    return _add(sc, "torus", opts)
def dodeca(sc, opts=None):   return _add(sc, "dodeca", opts)


def model(sc, url, opts=None):
    o = dict(opts or {})
    o["url"] = str(url)
    return _add(sc, "model", o)


def light(sc, kind="sun", opts=None):
    o = dict(opts or {})
    o["light"] = str(kind)
    sc["nodes"].append({"kind": "light", **o})
    return sc


def orbit(sc, on=True):
    sc["orbit"] = bool(on)
    return sc


def autorotate(sc, on=True):
    sc["autorotate"] = bool(on)
    return sc


def grid(sc, on=True):
    sc["grid"] = bool(on)
    return sc


_RUNTIME_JS = r"""
import * as THREE from "%CDN%";

function boot(canvas, S){
  const rr = new THREE.WebGLRenderer({canvas, antialias:true, alpha:false});
  rr.setPixelRatio(Math.min(devicePixelRatio,2));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(S.bg);
  const cam = new THREE.PerspectiveCamera(S.fov, 1, 0.1, 200);
  cam.position.set(S.camera[0], S.camera[1], S.camera[2]);
  cam.lookAt(0,0,0);

  if(S.grid){ const g = new THREE.GridHelper(20, 20, 0x334, 0x223); g.position.y=-1.2; scene.add(g); }

  let haveLight = false;
  const spinners = [], floaters = [], pulsers = [];

  function mat(c){ return new THREE.MeshStandardMaterial({color:c, roughness:.45, metalness:.15}); }
  function geom(n){
    const s = n.size || 1;
    if(n.kind==="box")      return new THREE.BoxGeometry(s,s,s);
    if(n.kind==="sphere")   return new THREE.SphereGeometry(s*.7, 48, 32);
    if(n.kind==="plane")    return new THREE.PlaneGeometry(s*3, s*3);
    if(n.kind==="cylinder") return new THREE.CylinderGeometry(s*.6, s*.6, s*1.4, 40);
    if(n.kind==="cone")     return new THREE.ConeGeometry(s*.7, s*1.4, 40);
    if(n.kind==="torus")    return new THREE.TorusGeometry(s*.7, s*.26, 24, 64);
    if(n.kind==="dodeca")   return new THREE.DodecahedronGeometry(s*.8);
    return new THREE.BoxGeometry(s,s,s);
  }

  for(const n of S.nodes){
    if(n.kind==="light"){
      haveLight = true;
      if(n.light==="ambient"){ scene.add(new THREE.AmbientLight(0xffffff, n.intensity ?? .6)); }
      else if(n.light==="point"){ const L=new THREE.PointLight(0xffffff, n.intensity ?? 1.2, 0); L.position.set(...(n.pos||[3,4,3])); scene.add(L); }
      else { const L=new THREE.DirectionalLight(0xffffff, n.intensity ?? 1.1); L.position.set(...(n.pos||[4,6,3])); scene.add(L); scene.add(new THREE.AmbientLight(0xffffff,.35)); }
      continue;
    }
    if(n.kind==="model"){ continue; }  // glTF loader 는 선택 기능 — 자리표시
    const m = new THREE.Mesh(geom(n), mat(n.color));
    m.position.set(...(n.pos||[0,0,0]));
    if(n.rotate) m.rotation.set(...(n.rotate.map ? n.rotate : [n.rotate,n.rotate,0]));
    const sc = n.scale || 1; m.scale.setScalar(sc);
    scene.add(m);
    if(n.spin)  spinners.push([m, n.spinSpeed || 1]);
    if(n.float) floaters.push([m, m.position.y]);
    if(n.pulse) pulsers.push([m, sc]);
  }
  if(!haveLight){
    const L = new THREE.DirectionalLight(0xffffff, 1.1); L.position.set(4,6,3); scene.add(L);
    scene.add(new THREE.AmbientLight(0xffffff,.4));
  }

  // 미니 오빗 (외부 의존 없이)
  let drag=false, px=0, py=0, theta=Math.atan2(cam.position.x,cam.position.z), phi=Math.acos(cam.position.y/cam.position.length()), rad=cam.position.length();
  function place(){ cam.position.set(rad*Math.sin(phi)*Math.sin(theta), rad*Math.cos(phi), rad*Math.sin(phi)*Math.cos(theta)); cam.lookAt(0,0,0); }
  if(S.orbit){
    canvas.style.cursor="grab";
    canvas.addEventListener("pointerdown", e=>{drag=true;px=e.clientX;py=e.clientY;canvas.style.cursor="grabbing";});
    addEventListener("pointerup", ()=>{drag=false;canvas.style.cursor="grab";});
    addEventListener("pointermove", e=>{ if(!drag) return; theta -= (e.clientX-px)*.008; phi = Math.max(.15, Math.min(Math.PI-.15, phi - (e.clientY-py)*.008)); px=e.clientX;py=e.clientY; place(); });
    canvas.addEventListener("wheel", e=>{ e.preventDefault(); rad = Math.max(2, Math.min(40, rad + Math.sign(e.deltaY)*.6)); place(); }, {passive:false});
  }

  function resize(){
    const w = canvas.clientWidth || canvas.parentElement.clientWidth || 640;
    const h = canvas.clientHeight || 420;
    rr.setSize(w, h, false); cam.aspect = w/h; cam.updateProjectionMatrix();
  }
  addEventListener("resize", resize); resize();

  const t0 = performance.now();
  function frame(){
    const t = (performance.now()-t0)/1000;
    for(const [m,sp] of spinners){ m.rotation.y = t*sp; m.rotation.x = t*sp*.4; }
    for(const [m,y0] of floaters){ m.position.y = y0 + Math.sin(t*1.6)*.35; }
    for(const [m,s0] of pulsers){ const k = s0*(1+Math.sin(t*3)*.12); m.scale.setScalar(k); }
    if(S.autorotate && !drag){ theta += .004; place(); }
    rr.render(scene, cam);
    requestAnimationFrame(frame);
  }
  frame();
}

document.querySelectorAll("canvas[data-poi3d]").forEach(c=>{
  try { boot(c, JSON.parse(c.getAttribute("data-poi3d"))); }
  catch(e){ console.error("scene3d", e); }
});
"""


def render(sc, opts=None):
    """씬 → 자체 완결 HTML 조각 (canvas + module script)."""
    o = dict(opts or {})
    h = int(o.get("height", 420))
    import hashlib as _hl
    cid = "poi3d_" + _hl.md5(
        _json.dumps(sc, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:8]
    data = _json.dumps(dict(sc), ensure_ascii=False).replace('"', "&quot;")
    js = _RUNTIME_JS.replace("%CDN%", _CDN)
    return (
        f'<div style="width:100%;height:{h}px;border-radius:14px;overflow:hidden;'
        f'background:{sc["bg"]}">'
        f'<canvas id="{cid}" data-poi3d="{data}" '
        f'style="width:100%;height:100%;display:block"></canvas></div>\n'
        f'<script type="module">{js}</script>'
    )


def page(sc, opts=None):
    """씬 → 완전한 HTML 문서 (file.write 로 바로 배포 가능)."""
    o = dict(opts or {})
    title = o.get("title", "POI 3D")
    return (
        "<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title>"
        "<style>*{margin:0}html,body{height:100%}body{background:" + sc["bg"] +
        ";display:flex;align-items:center;justify-content:center}"
        "#wrap{width:min(960px,94vw)}</style></head><body>"
        f"<div id=wrap>{render(sc, {'height': o.get('height', 560)})}</div>"
        "</body></html>"
    )


scene3d = SimpleNamespace(
    scene=scene, box=box, sphere=sphere, plane=plane, cylinder=cylinder,
    cone=cone, torus=torus, dodeca=dodeca, model=model, light=light,
    orbit=orbit, autorotate=autorotate, grid=grid, render=render, page=page,
)
