/* Arte do story "ao vivo" (1080x1920), no visual do cartão "Ao vivo agora" do site.
   Uso: node scripts/posts/story-live.js <saida.jpg> '<json>'
   json: {casa:'camara'|'senado'|'stf'|'exec', desde:'14h', tipo:'Sessão deliberativa', descricao:'...', canal:'TV Câmara'}
   O Instagram não deixa pôr link clicável em story pela API, por isso a arte manda para o site, onde a transmissão toca. */
const {chromium} = require('playwright');
const esc = s => String(s||'').replace(/[&<>"]/g, c=> ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const CASA = {
  camara:{n:'Câmara', p:'#F2C200', canal:'TV Câmara'},
  senado:{n:'Senado', p:'#F2C200', canal:'TV Senado'},
  stf:{n:'STF', p:'#1F4FB5', canal:'TV Justiça'},
  exec:{n:'Presidência', p:'#009C3B', canal:'Canal Gov'}
};
function html(o){
  const c = CASA[o.casa] || CASA.camara;
  return `<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0}
body{width:1080px;height:1920px;background:#F3F3F3;color:#121417;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;overflow:hidden;display:flex;flex-direction:column;justify-content:center;gap:56px;padding:260px 64px 300px}
.logo{font-size:44px;letter-spacing:-.015em;padding-left:20px}
.h{display:flex;align-items:center;gap:18px;margin:-20px 0 -24px 20px;font-size:34px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:#E0242B}
.logo i{display:inline-block;width:.54em;height:.54em;border-radius:50%;background:${c.p};margin:0 .045em}
.card{border-radius:56px;background:color-mix(in srgb,#E0242B 7%,#F3F3F3);padding:56px 56px 60px;display:flex;flex-direction:column;gap:36px}
.top{display:flex;align-items:center;justify-content:space-between;gap:20px}
.pill{display:inline-flex;align-items:center;gap:18px;padding:16px 32px 16px 26px;border-radius:999px;background:#F3F3F3;font-size:38px;line-height:1;color:#E0242B;white-space:nowrap}
.dot{width:22px;height:22px;border-radius:50%;background:#E0242B;flex:none}
.since{font-size:36px;color:#6E6F73;white-space:nowrap}
.t{margin:0;font-size:64px;line-height:1.1;letter-spacing:-.025em;font-weight:600}
.d{margin:-14px 0 0;font-size:36px;line-height:1.35;color:#55585D;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.video{position:relative;aspect-ratio:16/9;border-radius:34px;background:#121417;display:grid;place-items:center}
.video span{display:inline-flex;align-items:center;gap:24px;font-size:38px;padding:24px 40px;border-radius:999px;background:rgba(243,243,243,.12);color:#F3F3F3}
.video span::before{content:"";border-left:28px solid currentColor;border-top:17px solid transparent;border-bottom:17px solid transparent}
.go{text-align:center;margin-top:8px}
.go b{display:block;font-size:52px;letter-spacing:-.02em;font-weight:600}
.go span{display:block;margin-top:18px;font-size:36px;color:#6E6F73;line-height:1.4}
</style></head><body>
<div class="logo">C<i></i>isa Pública</div>
<p class="h"><span class="dot"></span>Ao vivo agora</p>
<div class="card">
  <div class="top"><span class="pill"><span class="dot"></span>${esc(c.n)} · ao vivo</span>${o.desde ? `<span class="since">desde as ${esc(o.desde)}</span>` : ''}</div>
  <p class="t">${esc(o.tipo || 'Sessão')}</p>
  ${o.descricao ? `<p class="d">${esc(o.descricao)}</p>` : ''}
  <div class="video"><span>${esc(o.canal || c.canal)}</span></div>
</div>
<div class="go"><b>Assista em coisapublica.io</b><span>a transmissão oficial e a pauta do dia<br>estão no site · link na bio</span></div>
</body></html>`;
}
module.exports = {html, CASA};
if (require.main === module) (async ()=>{
  const [out, js] = process.argv.slice(2);
  const b = await chromium.launch(), p = await b.newPage({viewport:{width:1080, height:1920}});
  await p.setContent(html(JSON.parse(js || '{}')));
  await p.screenshot({path: out, type:'jpeg', quality:92});
  await b.close(); console.log('ok', out);
})();
