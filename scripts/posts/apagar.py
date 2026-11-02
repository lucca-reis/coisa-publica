"""Apaga do Instagram os posts listados em posts/apagar.json (lista de {"pasta": "...", "instagram": "<id da mídia>"}),
antes de publicar. Serve para refazer posts: a pasta perde o publicado.json no mesmo commit e é publicada de novo.
Se alguma remoção falhar, para com erro, e a publicação não roda (para não deixar o post duplicado no perfil).
Precisa da permissão instagram_manage_contents no IG_TOKEN. Roda em .github/workflows/publicar.yml."""
import json, os, sys, pathlib, urllib.request, urllib.parse, urllib.error

ARQ = pathlib.Path(__file__).resolve().parents[2] / 'posts' / 'apagar.json'
TOKEN = os.environ.get('IG_TOKEN', '').strip()
if not ARQ.exists(): sys.exit(0)
lista = json.loads(ARQ.read_text(encoding='utf-8'))
falhas = []
for it in lista:
    mid = it.get('instagram')
    if not mid: continue
    url = f'https://graph.facebook.com/v21.0/{mid}?' + urllib.parse.urlencode({'access_token': TOKEN})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method='DELETE'), timeout=60) as r:
            print(f"{it.get('pasta')}: apagado do Instagram ({mid}): {r.read().decode()[:100]}")
    except urllib.error.HTTPError as ex:
        corpo = ex.read().decode('utf-8', 'replace')[:300]
        # mídia que já não existe conta como apagada
        if 'does not exist' in corpo:
            print(f"{it.get('pasta')}: já não existia ({mid})"); continue
        falhas.append(it); print(f"{it.get('pasta')}: erro ao apagar ({mid}): HTTP {ex.code} {corpo}", file=sys.stderr)
if falhas:
    ARQ.write_text(json.dumps(falhas, ensure_ascii=False, indent=1), encoding='utf-8'); sys.exit(1)
ARQ.unlink()
