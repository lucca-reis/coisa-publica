const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const errs=[];
const now=new Date().toISOString().slice(0,16)+'Z';
const data={atualizado:now,itens:[
 {casa:'stf',plenario:true,sigla:'',nome:'STF',tipo:'Audiência pública',descricao:'',desde:'10h',video:'https://www.youtube.com/watch?v=JoyPHsA_u_0'},
 {casa:'senado',plenario:false,sigla:'CE',nome:'Comissão de Educação e Cultura',tipo:'',descricao:'CE analisa criação de piso salarial para profissionais da educação básica',desde:'9h30',video:'https://www.youtube.com/watch?v=benusxlHUpc'},
 {casa:'senado',plenario:false,sigla:'CAE',nome:'Comissão de Assuntos Econômicos',tipo:'',descricao:'CAE vota permissão para contribuição previdenciária de estudante bolsista',desde:'10h40',video:'https://www.youtube.com/watch?v=eSNhv3THZFQ'},
 {casa:'camara',plenario:false,sigla:'CCJC',nome:'Comissão de Constituição e Justiça e de Cidadania',tipo:'',descricao:'Reunião deliberativa: discussão e votação de propostas',desde:'11h',video:null}]};
for (const [w,h] of [[1440,900],[390,844]]){const p=await b.newPage({viewport:{width:w,height:h},deviceScaleFactor:w<500?2:1});p.on('pageerror',e=>errs.push(e.message));
await p.clock.setFixedTime(new Date('2026-11-03T11:15:00-03:00'));
await p.route('**/data/aovivo.json',r=>r.fulfill({contentType:'application/json',body:JSON.stringify({...data,atualizado:'2026-11-03T14:10Z'})}));
await p.addInitScript(()=>{try{localStorage.setItem('cp-tour-v1','1')}catch(e){}});
await p.goto('http://localhost:8765/index.html');await p.waitForTimeout(3500);
let el=await p.$('.lvs'); await el.screenshot({path:`${process.argv[2]}/abas-${w}-a.png`});
await p.click('.lvs-row.acc > .lvc:not(.on) >> nth=1'); await p.waitForTimeout(700);
el=await p.$('.lvs'); await el.screenshot({path:`${process.argv[2]}/abas-${w}-b.png`});}
console.log(errs.join('\n')||'sem erros');await b.close()})();
