/* Imagem especial "Como funciona a Coisa Pública" (1080x1350): de onde vêm os dados, como são atualizados e como se lê um
   cartão, com um cartão de exemplo do site (dados reais: ADI 6336, julgada no STF em 29/10/2026) e as partes numeradas.
   Uso: node scripts/posts/especiais/como-funciona.js posts/<id> */
const {chromium} = require('playwright');
const path = require('path');
// placar do STF em U: 7 pela validade, 3 contra, 1 cadeira vaga
// mesmas posições do símbolo do Judiciário no site; a ordem enche de baixo para cima
const seats = [[6,10.7],[3.65,10.7],[8.35,10.7],[1.3,9.55],[10.7,9.55],[1.3,6.8],[10.7,6.8],[1.3,4.05],[10.7,4.05],[1.3,1.3],[10.7,1.3]];
const U = `<svg width="150" height="150" viewBox="0 0 12 12">${seats.map(([x,y],i)=>`<circle cx="${x}" cy="${y}" r="1.05" fill="${i<7?'#121417':i<10?'#E24B4A':'#D9D8D3'}"/>`).join('')}</svg>`;
const n = k => `<i class="n">${k}</i>`;
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0}
body{width:1080px;height:1350px;background:#FAFAF7;color:#121417;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;position:relative;overflow:hidden;padding:84px}
.logo{font-size:40px;letter-spacing:-.015em}.logo i{display:inline-block;width:.54em;height:.54em;border-radius:50%;background:#121417;margin:0 .045em}
h1{margin:44px 0 0;font-size:84px;line-height:1.02;letter-spacing:-.035em;font-weight:700}
.flow{margin-top:56px;display:grid;grid-template-columns:1fr 36px 1fr 36px 1fr;align-items:stretch;gap:10px}
.step{background:color-mix(in srgb,#121417 5%,#FAFAF7);border-radius:26px;padding:22px 22px 24px;min-height:160px}
.step b{display:block;font-size:30px;letter-spacing:-.02em;font-weight:600;margin-bottom:8px}
.step span{font-size:23px;line-height:1.3;color:#55585D}
.arr{font-size:34px;color:#9A9DA1;text-align:center;align-self:center}
.card{position:relative;margin-top:56px;background:color-mix(in srgb,#121417 5%,#FAFAF7);border-radius:34px;padding:34px 38px 36px}
.tags{display:flex;gap:12px;align-items:center}
.pill{padding:10px 20px;border-radius:999px;font-size:23px}
.jud{background:color-mix(in srgb,#1F4FB5 14%,#FAFAF7);color:color-mix(in srgb,#1F4FB5 66%,#121417)}
.typ{background:color-mix(in srgb,#4B4F57 14%,#FAFAF7);color:color-mix(in srgb,#4B4F57 78%,#121417)}
.row{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;margin-top:24px}
.t{font-size:38px;line-height:1.15;letter-spacing:-.02em;font-weight:500;margin:0}
.s{font-size:26px;line-height:1.35;color:#55585D;margin:12px 0 0;display:flex;align-items:center;gap:12px}
.ux{display:flex;align-items:center;gap:12px}
.leg{display:flex;gap:14px;justify-content:center;font-size:20px;color:#6E6F73;margin-top:6px}.leg i{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:6px}
.n{display:inline-grid;place-items:center;width:38px;height:38px;border-radius:50%;background:#121417;color:#FAFAF7;font-style:normal;font-size:21px;font-weight:600;flex:none}
.keys{margin-top:48px;display:grid;grid-template-columns:1fr 1fr;gap:26px 34px}
.keys div{display:flex;gap:14px;align-items:center;font-size:27px;line-height:1.3}
.keys .n{width:34px;height:34px;font-size:19px}
.foot{position:absolute;left:84px;right:84px;bottom:56px;display:flex;justify-content:space-between;font-size:22px;color:#8A8D91}
</style></head><body>
<div class="logo">C<i></i>isa Pública</div>
<h1>Como funciona<br>a Coisa Pública</h1>
<div class="flow">
  <div class="step"><b>Fontes oficiais</b><span>Câmara, Senado, Supremo, Planalto e Diário Oficial</span></div><div class="arr">→</div>
  <div class="step"><b>Atualizado</b><span>automaticamente, várias vezes ao dia</span></div><div class="arr">→</div>
  <div class="step"><b>Um cartão</b><span>por proposta, em linguagem simples</span></div>
</div>
<div class="card">
  <div class="tags"><span class="pill jud">STF · em vigor</span>${n(1)}<span class="pill typ">Ação no Supremo</span>${n(2)}</div>
  <div class="row"><div><p class="t">Contribuição de aposentados<br>com doenças graves</p><p class="s">Julgada em 29/10/2026: regra validada ${n(3)}</p></div>
    <div class="ux">${n(4)}<div>${U}<div class="leg"><span><i style="background:#121417"></i>7</span><span><i style="background:#E24B4A"></i>3</span></div></div></div></div>
</div>
<div class="keys">
  <div>${n(1)}<span>Em que poder e em que fase</span></div>
  <div>${n(2)}<span>Que tipo de proposta é</span></div>
  <div>${n(3)}<span>O que aconteceu por último</span></div>
  <div>${n(4)}<span>O placar, cadeira por cadeira</span></div>
</div>
<div class="foot"><span>Exemplo real: ADI 6336, STF</span><span>coisapublica.io</span></div>
</body></html>`;
(async ()=>{
  const dir = process.argv[2]; if (!dir) { console.error('uso: node como-funciona.js posts/<id>'); process.exit(1); }
  const b = await chromium.launch(), p = await b.newPage({viewport:{width:1080, height:1350}});
  await p.setContent(html);
  const over = await p.evaluate(()=> document.querySelector('.keys').getBoundingClientRect().bottom > 1350 - 100);
  await p.screenshot({path: path.join(dir, 'imagem.jpg'), type:'jpeg', quality:92});
  await b.close(); console.log(over ? 'ATENÇÃO: não coube' : 'ok', path.join(dir, 'imagem.jpg'));
})();
