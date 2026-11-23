// Optional: node tests/ui-smoke.cjs /path/to/jsdom
const assert=require('node:assert/strict'), fs=require('node:fs');
const {JSDOM}=require(process.argv[2]||'jsdom');
const samples=JSON.parse(fs.readFileSync('samples/mandarin-20.json','utf8'));
const manifest={profile:{voice:'zf_001',speed:1},status:'completed',total:20,items:samples.map((s,i)=>({...s,status:'ready',review:'pending',fingerprint:i.toString(16).padStart(64,'0'),duration:1}))};
const data={token:'test',samples,speeds:[.5,.75,.85,1,1.25,1.5],engines:{
  kokoro:{dependencies_ready:true,ready:true,voices:['zf_001','zf_002','zf_003','zm_009','zm_010'],default_voice:'zf_001',running:false,manifest,preview:{},log:'',exit_code:0,has_input:true},
  melo:{dependencies_ready:true,ready:true,voices:['ZH'],default_voice:'ZH',running:false,manifest:{},preview:{},log:'',exit_code:null,has_input:false}}};
const dom=new JSDOM(fs.readFileSync('web/index.html','utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only'});
const w=dom.window,requests=[];w.setInterval=()=>0;
w.localStorage.setItem('pion-audio-settings',JSON.stringify({engine:'kokoro',speed:1.25,voices:{kokoro:'invalid_saved_voice',melo:'ZH'}}));
w.fetch=async(path,options)=>{if(options){const p=JSON.parse(options.body);requests.push({path,p});if(path==='/api/review')data.engines[p.engine].manifest.items.find(r=>r.id===p.id).review=p.review;return {ok:true,json:async()=>({ok:true})};}return {ok:true,json:async()=>structuredClone(data)};};
w.eval(fs.readFileSync('web/app.js','utf8'));
const tick=()=>new Promise(r=>setTimeout(r,10));
(async()=>{
  await tick();assert.equal(w.document.querySelectorAll('#voice option').length,5);assert.equal(w.document.querySelector('#voice').value,'zf_001');assert.equal(w.document.querySelector('#speed').value,'1.25');
  assert.equal(w.document.querySelectorAll('tbody tr').length,20);assert.equal(w.document.querySelectorAll('audio').length,20);
  assert(w.document.querySelector('#approved-only').checked);assert.equal(w.document.querySelectorAll('#speed option').length,6);
  w.document.querySelector('tbody .review button').click();await tick();assert.equal(data.engines.kokoro.manifest.items[0].review,'approved');
  w.document.querySelector('#engine').value='melo';w.document.querySelector('#engine').onchange();assert.equal(w.document.querySelector('#voice').value,'ZH');assert.equal(w.document.querySelectorAll('#voice option').length,1);
  w.document.querySelector('#preview').click();await tick();assert.equal(requests.at(-1).path,'/api/preview');assert.equal(requests.at(-1).p.voice,'ZH');
  data.engines.melo.running=true;await w.refresh();assert(w.document.querySelector('#start').disabled);assert(w.document.querySelector('#engine').disabled);assert(!w.document.querySelector('#stop').disabled);
  data.engines.melo.running=false;await w.refresh();
  const input=w.document.querySelector('#import');Object.defineProperty(input,'files',{configurable:true,value:[{name:'batch.json',size:100,text:async()=>JSON.stringify(Array.from({length:123},(_,i)=>({id:'new:'+i,text:'你好'})))}]});
  await input.onchange({target:input});assert.equal(w.document.querySelectorAll('tbody tr').length,50);w.document.querySelector('#next').click();w.document.querySelector('#next').click();assert.equal(w.document.querySelectorAll('tbody tr').length,23);
  Object.defineProperty(input,'files',{configurable:true,value:[{name:'bad.json',size:10,text:async()=>'[null]'}]});await input.onchange({target:input});assert(w.document.querySelector('#notice').textContent.includes('không hợp lệ'));
  assert.equal(JSON.parse(w.localStorage.getItem('pion-audio-settings')).engine,'melo');
  console.log('UI smoke passed: real-list selection, safe defaults, six speeds, saved settings, preview, review, busy controls, pagination, invalid imports.');w.close();
})().catch(e=>{console.error(e);w.close();process.exitCode=1;});
