from pathlib import Path
p=Path(__file__).parent/'static/index.html'
s=p.read_text()
extra='''<section class="card" style="margin-top:16px" id="networkCard"><h2>☁️ Serverkopplad kassa · Version 2</h2><p class="muted small">Koppla en mobilkamera till det aktuella köpet. Fotot överförs via internet till servern. Bildtolkning är ännu inte ansluten, så registrera lapparna manuellt eller använd det förifyllda testköpet.</p><div class="actions"><button class="primary" id="createSession">+ Starta serverköp</button><button class="secondary" id="pairMobile" disabled>📱 Koppla mobilkamera</button><span id="serverStatus" class="badge">Inte ansluten</span></div><div id="pairView" style="display:none;margin-top:16px"><img id="pairQR" alt="QR-kod till mobilkamera" style="width:190px;max-width:100%"><p><a id="pairLink" target="_blank" rel="noopener">Öppna mobilkameran</a></p><small>Engångslänken gäller fem minuter. Mobilen och datorn kan använda olika internetanslutningar.</small></div><div id="photoStatus" style="margin-top:12px" role="status"></div></section>'''
s=s.replace('<section class="stats">',extra+'<section class="stats">',1)
s=s.replace('PROTOTYP</span>','VERSION 2 · DEMO</span>',1)
s=s.replace('All data lagras enbart lokalt i den här webbläsaren, inte mellan kassor.','Med aktivt serverköp sparas godkända köp centralt. Ingen automatisk bildtolkning eller betalningsverifiering ingår.',1)
script=r'''<script>
(()=>{
let sid=null, seen=new Set(), poll=null;
const el=id=>document.getElementById(id);
const status=s=>el('serverStatus').textContent=s;
async function api(path,options={}){let res=await fetch(path,options);let data=await res.json();if(!res.ok)throw Error(data.detail||'Serverfel');return data}
async function create(){try{let d=await api('/api/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({register_no:el('register').value})});sid=d.session_id;seen.clear();status('Kassa '+d.register_no+' · aktivt serverköp');el('pairMobile').disabled=false;el('pairView').style.display='none';el('photoStatus').textContent='Köp-ID: '+sid.slice(0,8);if(poll)clearInterval(poll);poll=setInterval(check,2500)}catch(e){alert('Kan inte nå servern: '+e.message)}}
async function pair(){if(!sid)return;try{let d=await api('/api/sessions/'+sid+'/pair',{method:'POST'});el('pairQR').src='/api/pair/qr?url='+encodeURIComponent(d.url);el('pairLink').href=d.url;el('pairLink').textContent=d.url;el('pairView').style.display='block';status('Väntar på mobilfoto')}catch(e){alert(e.message)}}
async function check(){if(!sid)return;try{let d=await api('/api/sessions/'+sid+'/photos');for(let p of d.photos){if(seen.has(p.id))continue;seen.add(p.id);let res=await fetch(p.url);let blob=await res.blob();let url=URL.createObjectURL(blob);imageSrc=url;items=[];selected=0;render();el('photoStatus').textContent='✓ Bild mottagen '+new Date().toLocaleTimeString('sv-SE')+' – lägg till lappar manuellt (AI ej ansluten).';status('Bild mottagen')} }catch(e){status('Servern kan inte nås')}}
el('createSession').onclick=create;el('pairMobile').onclick=pair;
// Byt endast slutförande till servern när ett serverköp är aktivt.
const oldFinish=el('finish').onclick;
el('finish').onclick=async()=>{
 if(!sid)return alert('Starta först ett serverköp. Den äldre lokala demon kan användas via originalfilen.');
 if(!items.length||items.some(x=>!/^[0-9]{1,4}$/.test(String(x.seller))||!(Number(x.price)>0)))return alert('Kontrollera att alla lappar har säljnummer och positivt pris.');
 if(items.some(x=>x.uncertain))return alert('Kontrollera alla osäkra lappar först.');
 if(!el('confirmed').checked||!el('recipient').value.trim())return alert('Bekräfta betalningen och ange mottagare.');
 el('finish').disabled=true;
 try{let data=await api('/api/sessions/'+sid+'/sale',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({items:items.map(x=>({seller:String(x.seller),desc:x.desc,price:Number(x.price)})),method:el('method').value,recipient:el('recipient').value.trim(),payment_confirmed:true})});
 alert('✓ Köp sparat på servern. '+data.total+' kr'+(data.already_saved?' (redan registrerat)':''));sid=null;if(poll)clearInterval(poll);el('pairMobile').disabled=true;el('pairView').style.display='none';status('Köp klart – starta nytt serverköp');items=[];imageSrc=defaultImage;el('confirmed').checked=false;el('recipient').value='';render()
 }catch(e){alert('Köpet kunde inte sparas: '+e.message)}finally{el('finish').disabled=false}
};
})();
</script>'''
s=s.replace('</body>',script+'</body>')
p.write_text(s)
