import urllib.request, json
B='https://legis.senado.leg.br/dadosabertos/'
for u,f in [('comissao/38.json','a'),('composicao/comissao/38.json?ativas=S','b'),('composicao/comissao/38.json?ativas=true','c')]:
    try:
        t=urllib.request.urlopen(urllib.request.Request(B+u,headers={'User-Agent':'coisa-publica','Accept':'application/json'}),timeout=40).read().decode()
        open(f'out/{f}.json','w').write(t); print('OK',u,len(t))
    except urllib.error.HTTPError as e: print('ERR',u,e.code,e.read()[:300])
