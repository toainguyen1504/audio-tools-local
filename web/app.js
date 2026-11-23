const $ = id => document.getElementById(id);
let current = null, customItems = null, signature = '', polling = false, pageNumber = 0;
let preferences = {engine:'kokoro', voices:{kokoro:'zf_001',melo:'ZH'},speed:1};
try {
  const saved=JSON.parse(localStorage.getItem('pion-audio-settings')||'{}');
  if(['kokoro','melo'].includes(saved.engine))preferences.engine=saved.engine;
  if([0.5,0.75,0.85,1,1.25,1.5].includes(saved.speed))preferences.speed=saved.speed;
  if(saved.voices&&typeof saved.voices==='object')preferences.voices={...preferences.voices,...saved.voices};
} catch { /* Storage is optional. */ }
$('engine').value=preferences.engine;$('speed').value=String(preferences.speed);
function remember(){
  preferences.engine=$('engine').value;preferences.speed=Number($('speed').value);
  if($('voice').value)preferences.voices[preferences.engine]=$('voice').value;
  try{localStorage.setItem('pion-audio-settings',JSON.stringify(preferences));}catch{}
}
function syncVoice(data){
  const engine=$('engine').value,info=data.engines[engine],ids=info.voices||[];
  const optionsKey=JSON.stringify([engine,ids]);
  if($('voice').dataset.optionsKey!==optionsKey){
    $('voice').replaceChildren();
    if(!ids.length){const option=el('option',info.checking?'Đang kiểm tra…':'Chưa có danh sách giọng');option.value='';$('voice').append(option);}
    for(const id of ids){const option=el('option',id+(id===info.default_voice?' · mặc định':''));option.value=id;$('voice').append(option);}
    const remembered=preferences.voices[engine];
    $('voice').value=ids.includes(remembered)?remembered:(ids.includes(info.default_voice)?info.default_voice:'');
    $('voice').dataset.optionsKey=optionsKey;
  }
}
function selectionPayload(){return {engine:$('engine').value,voice:$('voice').value,speed:Number($('speed').value)};}

const labels = {running:'Đang tạo', stopped:'Đã dừng', completed:'Đã tạo xong', completed_with_errors:'Hoàn tất, có mục lỗi',failed:'Không nạp được model — xem nhật ký'};
function el(tag, text, cls) { const node=document.createElement(tag); if(text!==undefined)node.textContent=text; if(cls)node.className=cls; return node; }
async function post(path, data) {
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Pion-Token':current.token},body:JSON.stringify(data)});
  const result=await response.json(); if(!response.ok)throw new Error(result.error||'Yêu cầu thất bại.'); return result;
}
function notify(message){$('notice').textContent=message;}
function cell(engine, row, running){
  const td=el('td');
  if(!row){td.append(el('span','Chưa tạo','meta'));return td;}
  if(row.status==='error'){td.append(el('p',row.error,'error'));return td;}
  td.append(el('div',`${row.duration}s · ${row.review==='approved'?'Đã duyệt':row.review==='rejected'?'Cần thay':'Chờ duyệt'}${row.reused?' · Dùng lại file':''}`,'meta'));
  const audio=el('audio');audio.controls=true;audio.preload='none';audio.src=`/audio/${engine}/${row.fingerprint}.wav`;td.append(audio);
  const actions=el('div',undefined,'review');
  for(const [value,label] of [['approved','Đạt'],['rejected','Cần thay'],['pending','Để sau']]){
    const button=el('button',label,`${value==='rejected'?'reject ':''}${row.review===value?'active':''}`);
    button.disabled=running;
    button.onclick=async()=>{try{await post('/api/review',{engine,id:row.id,fingerprint:row.fingerprint,review:value});await refresh();}catch(e){notify(e.message);}};
    actions.append(button);
  }
  td.append(actions);return td;
}
function render(data){
  const selected=$('engine').value, chosen=data.engines[selected];
  const anyRunning=Object.values(data.engines).some(e=>e.running);
  syncVoice(data);
  const canGenerate=chosen.ready&&Boolean($('voice').value);
  $('engine').disabled=anyRunning;$('voice').disabled=anyRunning||!(chosen.voices||[]).length;$('speed').disabled=anyRunning;
  $('start').disabled=anyRunning||!canGenerate;
  $('preview').disabled=anyRunning||!canGenerate;
  $('prepare').disabled=anyRunning||!chosen.dependencies_ready;
  $('check').disabled=anyRunning||chosen.checking;
  $('readiness').textContent=chosen.checking?'Đang kiểm tra môi trường…':(chosen.message||'Đang kiểm tra…');
  const existing=chosen.manifest.items||[],errors=existing.filter(r=>r.status==='error').length;
  $('retry').disabled=anyRunning||!canGenerate||!errors||!chosen.has_input;
  $('resume').disabled=anyRunning||!canGenerate||!chosen.has_input||!['stopped','failed','running','completed_with_errors'].includes(chosen.manifest.status);
  $('export').disabled=anyRunning||!existing.some(r=>r.status==='ready');
  const preview=chosen.preview||{},sample=(preview.items||[]).find(r=>r.status==='ready');
  const previewKey=sample?sample.fingerprint:'';
  if($('preview-result').dataset.key!==previewKey){
    $('preview-result').replaceChildren();$('preview-result').dataset.key=previewKey;
    if(sample){
      $('preview-result').append(el('div',`${sample.text} · ${preview.profile.voice} · tốc độ ${preview.profile.speed}`,'meta'));
      const player=el('audio');player.controls=true;player.preload='none';player.src=`/preview/${selected}/${sample.fingerprint}.wav`;$('preview-result').append(player);
    }
  }

  $('stop').disabled=!chosen.running;
  $('start').textContent=`Tạo / tiếp tục ${(customItems||data.samples).length} mẫu`;
  $('manifest').href=`/api/manifest/${selected}`;$('manifest').download=`manifest-${selected}.json`;
  $('log').textContent=chosen.log||'Chưa có nhật ký.';
  $('progress').replaceChildren();
  for(const [name,s] of Object.entries(data.engines)){
    const m=s.manifest, rows=m.items||[],ready=rows.filter(r=>r.status==='ready').length,errors=rows.filter(r=>r.status==='error').length;
    const box=el('div',undefined,'meter');box.append(el('strong',name==='kokoro'?'Kokoro':'MeloTTS'));
    let status=s.running?'Đang xử lý…':(labels[m.status]||'Chưa chạy');
    if(s.running&&s.operation==='prepare')status='Đang tải / chuẩn bị dữ liệu giọng…';
    else if(s.running&&s.operation==='preview')status='Đang tạo mẫu nghe thử…';
    else if(!s.ready&&!s.running)status=s.message||'Đang kiểm tra môi trường…';
    if(s.exit_code!==null&&s.exit_code!==0)status='Có lỗi — xem nhật ký';
    if(!s.running&&m.status==='running')status='Bị gián đoạn — nhấn tiếp tục';
    box.append(el('div',`${status} · ${ready}/${m.total||0} audio · ${errors} lỗi`));
    const progress=el('progress');progress.max=m.total||1;progress.value=rows.length;box.append(progress);
    if(m.profile)box.append(el('div',`${m.profile.voice} · tốc độ ${m.profile.speed}`,'meta'));
    $('head-'+name).textContent=(name==='kokoro'?'Kokoro':'MeloTTS')+(m.profile?` · ${m.profile.voice} / ${m.profile.speed}`:'');
    $('progress').append(box);
  }
  const nextSignature=JSON.stringify([pageNumber,customItems||data.samples,Object.values(data.engines).map(e=>[e.running,e.manifest])]);
  if(signature===nextSignature)return;signature=nextSignature;
  // Keep a playing recording mounted across progress polling updates.
  if([...document.querySelectorAll('audio')].some(a=>!a.paused)){signature='';return;}
  const rows=new Map();for(const sample of customItems||data.samples)rows.set(sample.id,sample);
  if(!customItems)for(const s of Object.values(data.engines))for(const row of s.manifest.items||[])if(!rows.has(row.id))rows.set(row.id,row);
  const allRows=[...rows.values()],pages=Math.max(1,Math.ceil(allRows.length/50));
  pageNumber=Math.min(pageNumber,pages-1);
  $('page').textContent=`Trang ${pageNumber+1}/${pages} · ${allRows.length} mục`;
  $('previous').disabled=pageNumber===0;$('next').disabled=pageNumber>=pages-1;
  const byEngine=Object.fromEntries(['kokoro','melo'].map(name=>[name,new Map((data.engines[name].manifest.items||[]).map(r=>[r.id,r]))]));
  const fragment=document.createDocumentFragment();
  for(const sample of allRows.slice(pageNumber*50,(pageNumber+1)*50)){
    const tr=el('tr'),description=el('td');description.append(el('strong',sample.text,'hanzi'),el('div',sample.pinyin,'pinyin'),el('div',sample.meaning,'meaning'));
    if(sample.note)description.append(el('p',sample.note,'note'));tr.append(description);
    for(const name of ['kokoro','melo']){
      const candidate=byEngine[name].get(sample.id);
      const row=candidate&&candidate.text===sample.text&&candidate.pinyin===(sample.pinyin||'')?candidate:null;
      tr.append(cell(name,row,data.engines[name].running));
    }
    fragment.append(tr);
  }
  $('samples').replaceChildren(fragment);
}
async function refresh(){if(polling)return;polling=true;try{const r=await fetch('/api/state');if(!r.ok)throw new Error('Không kết nối được công cụ local.');current=await r.json();render(current);}catch(e){notify(e.message);}finally{polling=false;}}
$('engine').onchange=()=>{preferences.engine=$('engine').value;if(current)render(current);remember();};
$('voice').onchange=remember;$('speed').onchange=remember;
$('start').onclick=async()=>{notify('');try{await post('/api/start',{...selectionPayload(),items:customItems||current.samples});await refresh();}catch(e){notify(e.message);}};
for(const action of ['prepare','preview','retry','resume','check']){
  $(action).onclick=async()=>{notify('');try{
    const payload={...selectionPayload(),text:$('preview-text').value};
    await post('/api/'+action,payload);
    notify(action==='prepare'?'Đang chuẩn bị. Lần đầu có thể tải thêm dữ liệu, xem Nhật ký xử lý.':action==='preview'?'Đang tạo mẫu nghe thử…':action==='retry'?'Thử lại đợt trước: giữ nguyên cấu hình và dùng lại file đã có.':'');
    await refresh();
  }catch(e){notify(e.message);}};
}
$('export').onclick=async()=>{
  const button=$('export');button.disabled=true;notify('Đang đóng gói kết quả…');
  try{
    const name=$('engine').value;
    const response=await fetch(`/api/export/${name}?approved=${$('approved-only').checked?'1':'0'}`);
    if(!response.ok)throw new Error((await response.json()).error);
    const url=URL.createObjectURL(await response.blob()),link=el('a');
    link.href=url;link.download=`pion-${name}-audio.zip`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
    notify('Đã xuất gói audio và bảng ánh xạ ID.');
  }catch(e){notify(e.message);}finally{button.disabled=false;}
};
$('stop').onclick=async()=>{try{await post('/api/stop',{engine:$('engine').value});notify('Sẽ dừng sau mẫu đang xử lý.');}catch(e){notify(e.message);}};
$('import').onchange=async(event)=>{try{
  const file=event.target.files[0];if(!file)return;if(file.size>8*1024*1024)throw new Error('File tối đa 8 MB.');
  const data=JSON.parse((await file.text()).replace(/^\uFEFF/,''));
  if(!Array.isArray(data)||!data.length||data.length>10000)throw new Error('File cần có 1–10.000 mục.');
  const ids=new Set();
  for(const row of data){
    if(!row||typeof row!=='object'||typeof row.id!=='string'||!/^[A-Za-z0-9_.:-]{1,100}$/.test(row.id)||ids.has(row.id)||typeof row.text!=='string'||!row.text.trim()||[...row.text.trim()].length>300)throw new Error('ID hoặc nội dung không hợp lệ / bị trùng. Xem định dạng trong README.');
    ids.add(row.id);
    for(const key of ['pinyin','meaning','kind','note'])if(row[key]!==undefined&&typeof row[key]!=='string')throw new Error(`Trường ${key} cần là chuỗi.`);
    row.text=row.text.trim().normalize('NFC');
  }
  customItems=data;pageNumber=0;$('selection').textContent=`${file.name} · ${data.length} mục`;if(current)render(current);notify('Danh sách sẽ được kiểm tra trước khi tạo audio.');
}catch(e){notify(e.message);}};
$('reset').onclick=()=>{customItems=null;pageNumber=0;$('import').value='';$('selection').textContent='Bộ mẫu mặc định · 20 mục';if(current)render(current);};
$('previous').onclick=()=>{pageNumber=Math.max(0,pageNumber-1);if(current)render(current);};
$('next').onclick=()=>{pageNumber++;if(current)render(current);};
document.addEventListener('play',event=>{if(event.target.tagName==='AUDIO')document.querySelectorAll('audio').forEach(a=>{if(a!==event.target)a.pause();});},true);
refresh();setInterval(refresh,2000);
