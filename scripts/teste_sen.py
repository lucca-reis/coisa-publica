import urllib.request, json
B='https://legis.senado.leg.br/dadosabertos/'
for u in ['composicao/comissao/38.json','composicao/comissao/38','composicao/comissao/atual/38.json','comissao/38.json','comissao/38','composicao/colegiado/38.json','composicao/comissao/38.json?v=4','composicao/lista/comissoes.json','dados/ListaComposicaoComissaov4.xsd','senador/lista/atual.json?participacao=T','comissao/38/composicao.json','composicao/comissao/SF/38.json','composicao/resumoComissao/38.json']:
    for acc in ('application/json',):
        try:
            r=urllib.request.urlopen(urllib.request.Request(B+u,headers={'User-Agent':'coisa-publica','Accept':acc}),timeout=40)
            t=r.read().decode('utf-8','replace'); print('OK',u,len(t),t[:900].replace('\n',' '))
        except urllib.error.HTTPError as e:
            print('ERR',u,e.code,e.read()[:300])
        except Exception as e: print('EXC',u,e)
        print('-----',flush=True)
