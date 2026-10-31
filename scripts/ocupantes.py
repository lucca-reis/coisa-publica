"""Quem ocupa hoje cada cadeira do Congresso: deputados e senadores em exercício e os presidentes das duas Casas.

Fontes (dados abertos, sem chave):
  - Câmara: https://dadosabertos.camara.leg.br/api/v2/deputados (deputados em exercício) e a Mesa Diretora;
  - Senado: https://legis.senado.leg.br/dadosabertos/senador/lista/atual (senadores em exercício) e a Mesa do Senado.
A lista muda sozinha quando muda a legislatura (1º de fevereiro de 2027) ou quando um suplente assume.
Grava data/ocupantes.json e data/ocupantes.js (o mesmo conteúdo como "window.OCUPANTES = ...", que o site carrega
antes de desenhar os plenários). Roda uma vez por dia (.github/workflows/ocupantes.yml). Só usa a biblioteca padrão."""
import json, re, time, datetime, zoneinfo, pathlib, unicodedata, urllib.request

BR = zoneinfo.ZoneInfo('America/Sao_Paulo')
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'data'
UA = {'Accept': 'application/json', 'User-Agent': 'quorum (github.com/lucca-reis/quorum)'}
CAM = 'https://dadosabertos.camara.leg.br/api/v2/'
SEN = 'https://legis.senado.leg.br/dadosabertos/'
log = []

def get(url):
    for n in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as ex:
            if n == 3: log.append(f'{url}: {ex}'); return None
            time.sleep(5 + 5 * n)

def norm(t):
    t = unicodedata.normalize('NFD', str(t or ''))
    return ''.join(c for c in t if not unicodedata.combining(c)).upper().strip()

# as siglas do site (index.html, PARTY); o que não estiver aqui fica com a sigla oficial
PARTIDOS = {'PT': 'PT', 'PL': 'PL', 'UNIAO': 'União', 'PP': 'PP', 'PSD': 'PSD', 'MDB': 'MDB', 'REPUBLICANOS': 'Republicanos',
            'PDT': 'PDT', 'PSB': 'PSB', 'PSDB': 'PSDB', 'PODE': 'Podemos', 'PODEMOS': 'Podemos', 'PSOL': 'PSOL', 'PCDOB': 'PCdoB',
            'AVANTE': 'Avante', 'SOLIDARIEDADE': 'Solidariedade', 'NOVO': 'Novo', 'PV': 'PV', 'REDE': 'Rede', 'PRD': 'PRD',
            'MISSAO': 'Missão', 'CIDADANIA': 'Cidadania', 'S.PART.': 'NC', 'S/PARTIDO': 'NC', 'SEM PARTIDO': 'NC', '': 'NC'}
def partido(s):
    k = norm(s)
    return PARTIDOS.get(k, s.strip() if s else 'NC')

def lista(x):
    return x if isinstance(x, list) else ([x] if x else [])

def dig(o, *ks):
    for k in ks:
        if not isinstance(o, dict): return None
        o = o.get(k)
    return o

# ---------- Câmara ----------
camara = []
js = get(CAM + 'deputados?ordem=ASC&ordenarPor=nome&itens=1000')
for d in (js or {}).get('dados') or []:
    camara.append({'n': d.get('nome', '').strip(), 'p': partido(d.get('siglaPartido')), 'uf': d.get('siglaUf'), 'id': d.get('id'), 'leg': d.get('idLegislatura')})
leg = max((d['leg'] or 0 for d in camara), default=0)
leg_info = (get(CAM + f'legislaturas/{leg}') or {}).get('dados') or {} if leg else {}

mesa_cam = None
orgs = (get(CAM + 'orgaos?sigla=MESA&itens=10') or {}).get('dados') or []
for o in orgs:
    mem = (get(CAM + f"orgaos/{o['id']}/membros?itens=100") or {}).get('dados') or []
    for m in mem:
        if norm(m.get('titulo')) == 'PRESIDENTE' and not m.get('dataFim'):
            mesa_cam = {'n': m.get('nome'), 'p': partido(m.get('siglaPartido')), 'uf': m.get('siglaUf'), 'desde': (m.get('dataInicio') or '')[:10]}
    if mesa_cam: break

# ---------- Senado ----------
senado = []
js = get(SEN + 'senador/lista/atual.json')
for p in lista(dig(js, 'ListaParlamentarEmExercicio', 'Parlamentares', 'Parlamentar')):
    i = p.get('IdentificacaoParlamentar') or {}
    m = p.get('Mandato') or {}
    ini = dig(m, 'PrimeiraLegislaturaDoMandato', 'DataInicio') or ''
    fim = dig(m, 'SegundaLegislaturaDoMandato', 'DataFim') or dig(m, 'PrimeiraLegislaturaDoMandato', 'DataFim') or ''
    senado.append({'n': (i.get('NomeParlamentar') or '').strip(), 'p': partido(i.get('SiglaPartidoParlamentar')), 'uf': i.get('UfParlamentar'),
                   'id': i.get('CodigoParlamentar'), 'ini': ini[:10], 'fim': fim[:10], 'part': m.get('DescricaoParticipacao') or ''})

mesa_sen = None
js = get(SEN + 'composicao/mesaSF.json')
for c in lista(dig(js, 'MesaSenado', 'Colegiados', 'Colegiado')) or [dig(js, 'MesaSenado', 'Colegiados', 'Colegiado')]:
    for m in lista(dig(c, 'Cargos', 'Cargo')):
        if norm(m.get('DescricaoCargo')) == 'PRESIDENTE':
            mesa_sen = {'n': (m.get('NomeParlamentar') or '').strip(), 'p': partido(m.get('SiglaPartido') or m.get('SiglaPartidoParlamentar') or ''), 'uf': m.get('SiglaUf') or m.get('UfParlamentar') or ''}
if not mesa_sen: log.append('mesa do Senado: presidente não encontrado; amostra: ' + json.dumps(js, ensure_ascii=False)[:600])

res = {'atualizado': datetime.datetime.now(BR).isoformat(timespec='minutes'),
       'legislatura': {'numero': leg, 'inicio': (leg_info.get('dataInicio') or '')[:10], 'fim': (leg_info.get('dataFim') or '')[:10]},
       'camara': camara, 'senado': senado, 'mesa': {'camara': mesa_cam, 'senado': mesa_sen},
       'fontes': {'camara': CAM + 'deputados', 'senado': SEN + 'senador/lista/atual'}, 'erros': log[:20]}
# só grava se as duas listas vieram completas o bastante (para um erro da API não esvaziar o plenário)
if len(camara) >= 480 and len(senado) >= 75:
    OUT.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(res, ensure_ascii=False, separators=(',', ':'))
    (OUT / 'ocupantes.json').write_text(txt, encoding='utf-8')
    (OUT / 'ocupantes.js').write_text('window.OCUPANTES = ' + txt + ';\n', encoding='utf-8')
else:
    log.append(f'listas incompletas: {len(camara)} deputados, {len(senado)} senadores; nada gravado')
print(json.dumps({'camara': len(camara), 'senado': len(senado), 'leg': res['legislatura'], 'mesa': res['mesa'],
                  'partidos': sorted({x['p'] for x in camara + senado}), 'erros': log[:6]}, ensure_ascii=False))
