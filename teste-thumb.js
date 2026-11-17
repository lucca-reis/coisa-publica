// test: live thumbnails on the home page with real YouTube ids
const {chromium}=require('playwright');const fs=require('fs');
(async()=>{
  let ids=[];
  try{ const r=await fetch('https://dadosabertos.camara.leg.br/api/v2/eventos?dataInicio='+new Date().toISOString().slice(0,10)+'&itens=100',{headers:{Accept:'application/json'}});
    const d=(await r.json()).dados; for(const e of d){ const m=/(?:v=|youtu\.be\/|\/live\/)([\w-]{11})/.exec(e.urlRegistro||''); fs.appendFileSync('out/log.txt',`${e.situacao} | ${e.orgaos?.[0]?.sigla} | ${e.urlRegistro}\n`); if(m&&/Andamento/i.test(e.situacao)) ids.push(['camara',e.orgaos?.[0]?.sigla,m[1]]); } }catch(e){fs.appendFileSync('out/log.txt','camara '+e+'\n')}
  ids.push(['camara','OLD1','IVpY0_LiYxY'],['senado','OLD2','JXqKF3LnTw0'],['camara','PLEN','qTcOGuWH7CQ']);
  ids=ids.slice(-6);
  for(const [,,id] of ids) for(const f of ['mqdefault_live.jpg','hqdefault_live.jpg','hqdefault.jpg','mqdefault.jpg']){
    const r=await fetch(`https://i.ytimg.com/vi/${id}/${f}`); const b=Buffer.from(await r.arrayBuffer());
    let w=0; for(let i=2;i<b.length-9;){ if(b[i]!==0xFF)break; const m=b[i+1],L=b.readUInt16BE(i+2); if(m===0xC0||m===0xC2){w=b.readUInt16BE(i+7)+'x'+b.readUInt16BE(i+5);break} i+=2+L; }
    fs.appendFileSync('out/log.txt',`${id} ${f} ${r.status} ${b.length}B ${w}\n`);
  }
  const b=await chromium.launch();const p=await b.newPage({viewport:{width:1440,height:900}});
  const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
  await p.addInitScript(()=>{try{localStorage.setItem('cp-tour-v1','1')}catch(e){}});
  const now=new Date(), hh=String((now.getUTCHours()+21)%24).padStart(2,'0')+':00';
  await p.route('**/data/aovivo.json*',r=>r.fulfill({contentType:'application/json',body:JSON.stringify({atualizado:now.toISOString(),itens:ids.filter(x=>x[1]!=='PLEN').map(([casa,s,id])=>({casa,plenario:false,sigla:s,nome:'Comissão '+s,desde:hh,video:'https://www.youtube.com/watch?v='+id}))})}));
  p.on('response',r=>{ if(r.url().includes('ytimg')) fs.appendFileSync('out/log.txt','page '+r.status()+' '+r.url()+'\n'); });
  await p.goto('http://localhost:8765/index.html');await p.waitForTimeout(6000);
  fs.appendFileSync('out/log.txt','bg: '+JSON.stringify(await p.evaluate(()=>[...document.querySelectorAll('[data-yt]')].map(e=>[e.dataset.yt,e.style.backgroundImage,getComputedStyle(e).backgroundImage.slice(0,90)])))+'\nerrs: '+errs.join(' | ')+'\n');
  await p.screenshot({path:'out/home.png'});
  const el=await p.$('#feed-live'); if(el) await el.screenshot({path:'out/live.png'});
  await b.close();
})();
