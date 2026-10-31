"""Despesa com pessoal de cada órgão federal (Legislativo, Judiciário, Ministério Público, Defensoria e Executivo), do
Relatório de Gestão Fiscal (RGF, Anexo 1) que cada órgão entrega ao Tesouro Nacional a cada quadrimestre.

É a fonte oficial que traz os tribunais, as casas do Congresso, o TCU, o MPU e a DPU separados e no mesmo formato
(o Portal da Transparência só tem o Executivo). Fonte: API de dados abertos do SICONFI (Tesouro Nacional), sem chave:
  https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rgf
Grava data/transparencia/rgf.json (último quadrimestre publicado de cada órgão: despesa bruta com pessoal em 12 meses,
ativos, inativos e pensionistas, mês a mês, despesa total com pessoal e limite da LRF) e
rgf-amostra.json (algumas linhas cruas, para conferir o formato). Só usa a biblioteca padrão."""
import json, re, time, datetime, zoneinfo, pathlib, urllib.request, urllib.parse

API = 'https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rgf'
BR = zoneinfo.ZoneInfo('America/Sao_Paulo')
HOJE = datetime.datetime.now(BR).date()
OUT = pathlib.Path(__file__).resolve().parent.parent / 'data' / 'transparencia'
UA = {'User-Agent': 'quorum (github.com/lucca-reis/quorum)', 'Accept': 'application/json'}
PODERES = {'L': 'leg', 'J': 'jud', 'M': 'mpu', 'D': 'mpu', 'E': 'exec'}
log, amostra = [], {}

def get(**q):
    """Todas as páginas de uma consulta (a API devolve até 5.000 linhas por vez, com hasMore)."""
    out, off = [], 0
    while True:
        url = API + '?' + urllib.parse.urlencode({**q, 'offset': off})
        for n in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                    js = json.loads(r.read().decode('utf-8'))
                break
            except Exception as ex:
                if n == 2: log.append(f'{q}: {ex}'); return out
                time.sleep(5)
        it = js.get('items') or []
        out += it
        if not js.get('hasMore') or not it: return out
        off += len(it); time.sleep(1)

# o quadrimestre mais recente com dados: tenta do mais novo para o mais antigo
alvos = []
for ano in (HOJE.year, HOJE.year - 1):
    for per in (3, 2, 1):
        if ano == HOJE.year and datetime.date(ano, per * 4 - 3, 1) > HOJE: continue
        alvos.append((ano, per))

orgaos = {}
for co_poder, chave in PODERES.items():
    for ano, per in alvos:
        linhas = get(an_exercicio=ano, in_periodicidade='Q', nr_periodo=per, co_tipo_demonstrativo='RGF', co_esfera='U', co_poder=co_poder, id_ente=1)
        if not linhas:
            log.append(f'{co_poder} {ano}/{per}: vazio'); continue
        if co_poder not in amostra: amostra[co_poder] = linhas[:25]
        a1 = [l for l in linhas if '01' in str(l.get('anexo') or '')] or linhas
        novos = 0
        for l in a1:
            # um mesmo relatório pode trazer mais de um órgão (o do MPU traz também o MPDFT), separados por "rotulo"
            rot = (l.get('rotulo') or '').strip()
            inst = rot if rot and rot.lower() not in ('padrão', 'padrao') else (l.get('instituicao') or '').strip()
            if not inst: continue
            o = orgaos.get(inst)
            if o and (o['ano'], o['periodo']) > (ano, per): continue
            if not o or (o['ano'], o['periodo']) != (ano, per):
                o = orgaos[inst] = {'nome': inst, 'poder': chave, 'co_poder': co_poder, 'ano': ano, 'periodo': per, 'anexo': l.get('anexo'), 'linhas': []}
                novos += 1
            cod = re.sub(r'ConsorcioContratoDeRateio$', '', str(l.get('cod_conta') or ''))   # a DPU usa os códigos com esse sufixo
            o['linhas'].append([cod, (l.get('conta') or '').strip(), re.sub(r'\s+', ' ', l.get('coluna') or '').strip(), l.get('valor')])
        log.append(f'{co_poder} {ano}/{per}: {len(linhas)} linhas, {novos} órgãos novos')

# resumo de cada órgão: as linhas do Anexo 1 que o site mostra (12 meses até o fim do quadrimestre)
def resumo(o):
    V = {}
    for cod, conta, col, v in o['linhas']: V[(cod, col)] = v
    tot = lambda cod: V.get((cod, 'TOTAL (ÚLTIMOS 12 MESES) (a)'))
    fim = datetime.date(o['ano'], o['periodo'] * 4, 1)       # mês de referência: abril, agosto ou dezembro
    meses = []
    for k in range(11, -1, -1):
        y, m = fim.year, fim.month - k
        while m < 1: y, m = y - 1, m + 12
        meses.append([f'{y}-{m:02d}', V.get(('DespesaComPessoalBruta', '<MR>' if k == 0 else f'<MR-{k}>'))])
    out = {x: o[x] for x in ('nome', 'poder', 'ano', 'periodo')}
    out.update({'bruta': tot('DespesaComPessoalBruta'), 'ativo': tot('DespesaComPessoalAtivoBruta'),
                'inativo': tot('DespesaComPessoalInativoEPensionistasBruta'), 'liquida': tot('DespesaComPessoalLiquida'),
                'dtp': V.get(('DespesaComPessoalTotal', 'Valor')), 'limite': V.get(('LimiteMaximoDespesaComPessoalTotal', 'Valor')),
                'meses': meses if any(v for _, v in meses) else []})
    return out

OUT.mkdir(parents=True, exist_ok=True)
amostra['stf_linhas'] = next((o['linhas'] for o in orgaos.values() if o['nome'] == 'Supremo Tribunal Federal'), [])
res = {'atualizado': datetime.datetime.now(BR).isoformat(timespec='minutes'), 'orgaos': sorted((resumo(o) for o in orgaos.values()), key=lambda o: (o['poder'], -(o['bruta'] or 0))),
       'fonte': 'https://siconfi.tesouro.gov.br/siconfi/pages/public/consulta_finbra_rgf/finbra_rgf_list.jsf', 'api': API, 'erros': log[:80]}
(OUT / 'rgf.json').write_text(json.dumps(res, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
(OUT / 'rgf-amostra.json').write_text(json.dumps(amostra, ensure_ascii=False, indent=1)[:60000], encoding='utf-8')
print(json.dumps({'orgaos': len(orgaos), 'por_poder': {k: sum(1 for o in orgaos.values() if o['poder'] == k) for k in set(PODERES.values())}, 'log': log[:20]}, ensure_ascii=False))
