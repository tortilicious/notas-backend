#!/usr/bin/env python3
"""
Genera el HTML de apuntes de una rama del roadmap a partir de sus .md.

Uso:
    python3 generar-apuntes.py RAMA "TÍTULO"
Ejemplo:
    python3 generar-apuntes.py linux "Linux y VPS: apuntes"

Junta, en orden de número de bloque, todos los RAMA-bloque-N.md de la carpeta
de origen (por defecto /mnt/project) y escribe RAMA.html en la carpeta de
salida (por defecto /mnt/user-data/outputs). Requiere pandoc.
El texto no se modifica: solo se baja un nivel la jerarquía de títulos para
que cada bloque (h1) contenga sus partes (h2) y secciones (h3).
Estilo: Google Sans Flex para el texto, JetBrains Mono para el código,
índice lateral con filtro, modo oscuro automático.
"""
import argparse, glob, os, re, subprocess, sys, tempfile

TEMPLATE = r'''
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$pagetitle$</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🐧</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Google+Sans+Flex:wght@100..900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{
  --paper:#F5F7FA; --ink:#1C2533; --muted:#5B6678; --rule:#D5DCE6;
  --accent:#1F5F8B; --accent-soft:#E2ECF4; --code-bg:#E9EDF3; --side:#ECF0F5;
  --serif:"Google Sans Flex",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --sans:"Google Sans Flex",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"DejaVu Sans Mono",Consolas,monospace;
}
@media (prefers-color-scheme: dark){
  :root{--paper:#141A23; --ink:#DCE3EC; --muted:#93A0B2; --rule:#2B3542;
  --accent:#7DB4DD; --accent-soft:#1E2C3B; --code-bg:#1C2430; --side:#10151D;}
}
*{box-sizing:border-box}
html{scroll-padding-top:1.5rem;font-size:17px}
body{margin:0;background:var(--paper);color:var(--ink);font:17.5px/1.65 var(--serif);
  display:grid;grid-template-columns:320px minmax(0,1fr);min-height:100vh}
/* Índice lateral */
nav#toc{position:sticky;top:0;height:100vh;overflow-y:auto;background:var(--side);
  border-right:1px solid var(--rule);padding:1.25rem 1rem 3rem;font:15px/1.45 var(--sans)}
nav#toc .brand{font-weight:700;font-size:1.05rem;margin:0 0 .75rem;color:var(--ink)}
#filtro{width:100%;padding:.45rem .6rem;margin-bottom:1rem;border:1px solid var(--rule);
  border-radius:6px;background:var(--paper);color:var(--ink);font:inherit}
nav#toc ul{list-style:none;margin:0;padding:0}
nav#toc ul ul{padding-left:.85rem;border-left:1px solid var(--rule);margin:.15rem 0 .4rem .3rem}
nav#toc a{color:var(--muted);text-decoration:none;display:block;padding:.18rem .4rem;border-radius:4px}
nav#toc a:hover{color:var(--ink);background:var(--accent-soft)}
nav#toc a.activo{color:var(--accent);font-weight:600}
nav#toc > ul > li > a{color:var(--ink);font-weight:700;margin-top:.6rem}
nav#toc > ul > li > ul > li > a{font-weight:600;color:var(--ink)}
nav#toc li.oculto{display:none}
/* Contenido */
main{padding:2.5rem clamp(1.25rem,4vw,4rem) 6rem;max-width:62rem}
main p,main li{max-width:72ch}
h1,h2,h3,h4,h5{font-family:var(--sans);line-height:1.25;color:var(--ink)}
h1{font-size:2.1rem;font-weight:700;letter-spacing:-.01em;margin:4.5rem 0 1rem;padding:1.2rem 0 1.2rem 1.1rem;border-left:6px solid var(--accent);
  background:linear-gradient(90deg,var(--accent-soft),transparent 70%)}
main > h1:first-child{margin-top:0}
h2{font-size:1.55rem;font-weight:650;margin:3rem 0 1rem;padding-bottom:.4rem;border-bottom:2px solid var(--rule)}
h3{font-size:1.2rem;font-weight:650;margin:2.2rem 0 .6rem}
h4{font-size:1rem;font-weight:600;margin:1.6rem 0 .4rem;color:var(--muted)}
a{color:var(--accent)}
hr{border:0;border-top:1px solid var(--rule);margin:2rem 0}
strong{font-weight:600}
code{font-family:var(--mono);font-size:.86em;color:var(--accent);background:var(--code-bg);padding:.1em .35em;border-radius:4px}
pre{background:var(--code-bg);border-left:3px solid var(--accent);padding:1rem 1.1rem;overflow-x:auto;
  border-radius:0 6px 6px 0;line-height:1.5;font-size:.95rem}
pre code{background:none;padding:0;font-size:.95em;color:var(--ink)}
table{display:block;overflow-x:auto;border-collapse:collapse;margin:1.2rem 0;font-size:.93rem;line-height:1.5;max-width:100%}
th,td{border:1px solid var(--rule);padding:.5rem .7rem;text-align:left;vertical-align:top}
th{background:var(--accent-soft);font-family:var(--sans);font-weight:600}
td code{white-space:nowrap}
blockquote{margin:1.2rem 0;padding:.6rem 1rem;border-left:3px solid var(--muted);color:var(--muted)}
a:focus-visible,#filtro:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
/* Móvil */
#abrir{display:none}
@media (max-width:900px){
  body{display:block}
  nav#toc{position:fixed;inset:0 25% 0 0;z-index:10;transform:translateX(-100%);transition:transform .2s}
  body.menu nav#toc{transform:none;box-shadow:0 0 0 100vmax rgba(0,0,0,.35)}
  #abrir{display:block;position:fixed;right:1rem;bottom:1rem;z-index:11;padding:.6rem 1rem;
    border:0;border-radius:6px;background:var(--accent);color:var(--paper);font:600 16px var(--sans)}
  h1{font-size:1.7rem}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
@media print{nav#toc,#abrir{display:none} body{display:block}}
</style>
</head>
<body>
<nav id="toc">
<p class="brand">$pagetitle$</p>
<input id="filtro" type="search" placeholder="Filtrar el índice…" aria-label="Filtrar el índice">
$table-of-contents$
</nav>
<button id="abrir" aria-label="Abrir índice">Índice</button>
<main>
$body$
</main>
<script>
// Filtrar índice
const filtro=document.getElementById('filtro');
const items=[...document.querySelectorAll('#toc li')];
filtro.addEventListener('input',()=>{
  const q=filtro.value.trim().toLowerCase();
  items.forEach(li=>li.classList.add('oculto'));
  items.forEach(li=>{
    const t=li.querySelector(':scope > a').textContent.toLowerCase();
    if(!q||t.includes(q)){let n=li;while(n&&n.tagName==='LI'){n.classList.remove('oculto');n=n.parentElement.closest('li');}
      if(q) li.querySelectorAll('li').forEach(c=>c.classList.remove('oculto'));}
  });
});
// Resaltar sección actual
const enlaces=new Map([...document.querySelectorAll('#toc a')].map(a=>[decodeURIComponent(a.hash.slice(1)),a]));
const obs=new IntersectionObserver(es=>{es.forEach(e=>{if(e.isIntersecting){
  document.querySelectorAll('#toc a.activo').forEach(a=>a.classList.remove('activo'));
  const a=enlaces.get(e.target.id); if(a){a.classList.add('activo');a.scrollIntoView({block:'nearest'});}}})},
  {rootMargin:'0px 0px -75% 0px'});
document.querySelectorAll('main h1[id],main h2[id],main h3[id]').forEach(h=>obs.observe(h));
// Menú móvil
document.getElementById('abrir').onclick=()=>document.body.classList.toggle('menu');
document.querySelectorAll('#toc a').forEach(a=>a.onclick=()=>document.body.classList.remove('menu'));
</script>
</body>
</html>
'''

def preparar(rutas):
    out = []
    for ruta in rutas:
        primero, codigo = True, False
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                if linea.startswith("```"):
                    codigo = not codigo
                    out.append(linea)
                    continue
                m = re.match(r"^(#{1,5}) ", linea)
                if m and not codigo:
                    if primero and len(m.group(1)) == 1:
                        primero = False      # título del bloque: se queda en h1
                    else:
                        linea = "#" + linea  # el resto baja un nivel
                out.append(linea)
        out.append("\n\n")
    return "".join(out)

def main():
    p = argparse.ArgumentParser(description="Genera el HTML de apuntes de una rama.")
    p.add_argument("rama", help="prefijo de los ficheros: linux, redes, postgresql…")
    p.add_argument("titulo", help="título del documento, p. ej. 'Linux y VPS: apuntes'")
    p.add_argument("--origen", default="/mnt/project")
    p.add_argument("--salida", default="/mnt/user-data/outputs")
    a = p.parse_args()

    rutas = glob.glob(os.path.join(a.origen, f"{a.rama}-bloque-*.md"))
    num = lambda r: int(re.search(r"-bloque-(\d+)\.md$", r).group(1))
    rutas = sorted((r for r in rutas if re.search(r"-bloque-\d+\.md$", r)), key=num)
    if not rutas:
        sys.exit(f"No hay ficheros {a.rama}-bloque-N.md en {a.origen}")

    os.makedirs(a.salida, exist_ok=True)
    destino = os.path.join(a.salida, f"{a.rama}.html")
    with tempfile.TemporaryDirectory() as tmp:
        md, plantilla, meta = (os.path.join(tmp, n) for n in ("in.md", "t.html", "meta.yaml"))
        open(md, "w", encoding="utf-8").write(preparar(rutas))
        open(plantilla, "w", encoding="utf-8").write(TEMPLATE.lstrip("\n"))
        open(meta, "w", encoding="utf-8").write(f'---\npagetitle: "{a.titulo}"\n---\n')
        env = dict(os.environ, LANG="C.UTF-8", LC_ALL="C.UTF-8")
        subprocess.run(["pandoc", meta, md, "-f", "gfm+yaml_metadata_block", "-t", "html5",
                        "-s", "--template", plantilla, "--toc", "--toc-depth=3",
                        "--no-highlight", "-o", destino], check=True, env=env)
    print(f"{destino}  ←  " + ", ".join(os.path.basename(r) for r in rutas))

if __name__ == "__main__":
    main()
