"""Publica no Bluesky e no Instagram os posts aprovados (os que chegaram à branch main em posts/AAAA-MM-DD-periodo/).

Cada post tem post.json (textos por rede e o texto alternativo da imagem) e imagem.jpg (gerada por render.js).
Depois de publicar, grava publicado.json na mesma pasta, para nunca publicar duas vezes.
Roda em .github/workflows/publicar.yml. As chaves ficam nos segredos do GitHub, nunca no código:
  BLUESKY_HANDLE e BLUESKY_APP_PASSWORD  (senha de app criada nas configurações do Bluesky)
  IG_USER_ID e IG_TOKEN                  (conta profissional do Instagram, API da Meta)
Rede sem chave configurada é pulada, e o post fica esperando até ela ser configurada. Só usa a biblioteca padrão."""
import json, os, re, sys, time, datetime, pathlib, urllib.request, urllib.parse, urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[2]
POSTS = ROOT / 'posts'
SITE = 'https://lucca-reis.github.io/quorum/'
UA = {'User-Agent': 'quorum (github.com/lucca-reis/quorum)'}
BSKY_H, BSKY_P = os.environ.get('BLUESKY_HANDLE', '').strip(), os.environ.get('BLUESKY_APP_PASSWORD', '').strip()
IG_ID, IG_TOKEN = os.environ.get('IG_USER_ID', '').strip(), os.environ.get('IG_TOKEN', '').strip()
GRAPH = 'https://graph.facebook.com/v21.0/'

def req(url, data=None, headers=None, method=None):
    h = {**UA, **(headers or {})}
    if isinstance(data, (dict, list)):
        data = json.dumps(data).encode(); h['Content-Type'] = 'application/json'
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            b = resp.read()
            return json.loads(b) if b else {}
    except urllib.error.HTTPError as ex:
        raise RuntimeError(f'{url.split("?")[0]}: HTTP {ex.code} {ex.read().decode("utf-8", "replace")[:400]}')

# ---------- Bluesky ----------
def bluesky(post, img):
    s = req('https://bsky.social/xrpc/com.atproto.server.createSession', {'identifier': BSKY_H, 'password': BSKY_P})
    auth = {'Authorization': 'Bearer ' + s['accessJwt']}
    blob = req('https://bsky.social/xrpc/com.atproto.repo.uploadBlob', img.read_bytes(), {**auth, 'Content-Type': 'image/jpeg'})['blob']
    text = post['textos']['bluesky']
    # links no texto viram links clicáveis (facets, com posições em bytes UTF-8)
    facets = []
    for m in re.finditer(r'https?://[^\s]+|lucca-reis\.github\.io/quorum[^\s]*', text):
        a, b = len(text[:m.start()].encode()), len(text[:m.end()].encode())
        uri = m.group(0) if m.group(0).startswith('http') else 'https://' + m.group(0)
        facets.append({'index': {'byteStart': a, 'byteEnd': b}, 'features': [{'$type': 'app.bsky.richtext.facet#link', 'uri': uri}]})
    rec = {'$type': 'app.bsky.feed.post', 'text': text, 'createdAt': datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z'),
           'langs': ['pt'], 'embed': {'$type': 'app.bsky.embed.images', 'images': [{'alt': post.get('alt', ''), 'image': blob, 'aspectRatio': {'width': 1080, 'height': 1350}}]}}
    if facets: rec['facets'] = facets
    r = req('https://bsky.social/xrpc/com.atproto.repo.createRecord', {'repo': s['did'], 'collection': 'app.bsky.feed.post', 'record': rec}, auth)
    return r.get('uri')

# ---------- Instagram (a imagem precisa estar num endereço público: o GitHub Pages do site) ----------
def instagram(post, pid):
    url = f'{SITE}posts/{pid}/imagem.jpg'
    for _ in range(40):                      # espera o GitHub Pages publicar a imagem (até ~10 min)
        try:
            urllib.request.urlopen(urllib.request.Request(url, headers=UA, method='HEAD'), timeout=30); break
        except Exception: time.sleep(15)
    q = urllib.parse.urlencode({'image_url': url, 'caption': post['textos']['instagram'], 'alt_text': post.get('alt', ''), 'access_token': IG_TOKEN}).encode()
    c = req(GRAPH + f'{IG_ID}/media', q)['id']
    for _ in range(30):                      # o Instagram processa a imagem antes de publicar
        st = req(GRAPH + f'{c}?' + urllib.parse.urlencode({'fields': 'status_code', 'access_token': IG_TOKEN})).get('status_code')
        if st == 'FINISHED': break
        if st == 'ERROR': raise RuntimeError('Instagram recusou a imagem')
        time.sleep(5)
    r = req(GRAPH + f'{IG_ID}/media_publish', urllib.parse.urlencode({'creation_id': c, 'access_token': IG_TOKEN}).encode())
    return r.get('id')

redes = {'bluesky': (bool(BSKY_H and BSKY_P), bluesky), 'instagram': (bool(IG_ID and IG_TOKEN), instagram)}
falhas = 0
for d in sorted(p for p in POSTS.iterdir() if p.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}-(manha|tarde|noite)$', p.name)):
    post, img, feito_f = d / 'post.json', d / 'imagem.jpg', d / 'publicado.json'
    if not post.exists() or not img.exists(): continue
    P = json.loads(post.read_text(encoding='utf-8'))
    # post velho (mais de 2 dias) não sai: as redes só recebem o que ainda é notícia
    try:
        if (datetime.date.today() - datetime.date.fromisoformat(P.get('data') or d.name[:10])).days > 2: continue
    except ValueError: pass
    feito = json.loads(feito_f.read_text(encoding='utf-8')) if feito_f.exists() else {}
    for nome, (ok, fn) in redes.items():
        if nome in feito or not ok or not (P.get('textos') or {}).get(nome): continue
        try:
            ref = fn(P, img) if nome == 'bluesky' else fn(P, d.name)
            feito[nome] = {'ref': ref, 'quando': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='minutes')}
            print(f'{d.name}: publicado no {nome} ({ref})')
        except Exception as ex:
            falhas += 1; print(f'{d.name}: erro no {nome}: {ex}', file=sys.stderr)
    if feito: feito_f.write_text(json.dumps(feito, ensure_ascii=False, indent=1), encoding='utf-8')
print('redes configuradas:', [n for n, (ok, _) in redes.items() if ok] or 'nenhuma')
sys.exit(1 if falhas else 0)
