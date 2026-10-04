import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';

const $ = (id) => document.getElementById(id);
const number = new Intl.NumberFormat('ru-RU');
const state = {packet:null,selected:null,point:null,regions:[],meshes:new Map(),controlChanges:new Map(),wire:false,isolated:false,references:[],tab:'model'};
let renderer,scene,camera,orbit,root,marker,regionRoot,span=1,center=new THREE.Vector3(),renderLoop;

function element(tag, classes, text) { const value=document.createElement(tag);if(classes)value.className=classes;if(text!==undefined)value.textContent=text;return value; }
function toast(text) {$('toast').textContent=text;$('toast').classList.add('visible');clearTimeout(state.toastTimer);state.toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),2600);}
function showTab(tab){state.tab=tab;document.querySelectorAll('.tab').forEach(button=>button.classList.toggle('active',button.dataset.tab===tab));document.querySelectorAll('.pane').forEach(pane=>pane.classList.toggle('active',pane.id===tab+'-pane'));if(tab==='model')requestAnimationFrame(resize);}
document.querySelectorAll('.tab').forEach(button=>button.addEventListener('click',()=>showTab(button.dataset.tab)));
function resize(){if(!renderer)return;const host=$('viewport'),width=host.clientWidth,height=host.clientHeight;if(!width||!height)return;renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();}
function frame(view='iso') {if(!camera)return;const offsets={iso:[1.4,-1.8,1.2],front:[0,-1,.00001],side:[1,0,.00001],top:[0,.00001,1]};camera.position.copy(center).add(new THREE.Vector3(...offsets[view]).normalize().multiplyScalar(span*2.4));camera.near=Math.max(span*.0001,1e-8);camera.far=span*40;camera.updateProjectionMatrix();orbit.target.copy(center);orbit.update();document.querySelectorAll('[data-view]').forEach(button=>button.classList.toggle('active',button.dataset.view===view));}
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>frame(button.dataset.view)));
$('fit-scene').addEventListener('click',()=>frame());window.addEventListener('keydown',event=>{if(event.key.toLowerCase()==='f'&&!['INPUT','TEXTAREA'].includes(event.target.tagName))frame();});
$('wireframe').addEventListener('click',()=>{state.wire=!state.wire;state.meshes.forEach(mesh=>mesh.material.wireframe=state.wire);$('wireframe').setAttribute('aria-pressed',String(state.wire));});

function setup3D(packet){
 THREE.Object3D.DEFAULT_UP.set(0,0,1);scene=new THREE.Scene();scene.background=new THREE.Color('#213139');
 camera=new THREE.PerspectiveCamera(38,1,.00001,1000);renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.3;
 $('viewport').appendChild(renderer.domElement);orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;orbit.dampingFactor=.09;orbit.screenSpacePanning=true;
 const hemisphere=new THREE.HemisphereLight(0xdceae5,0x202c37,2.2);hemisphere.position.set(0,0,1);scene.add(hemisphere);
 const light=new THREE.DirectionalLight(0xe8f3ec,3.1);light.position.set(2,-3,4);scene.add(light);const fill=new THREE.DirectionalLight(0xbed6e8,1.3);fill.position.set(-3,1,1);scene.add(fill);
 root=new THREE.Group();regionRoot=new THREE.Group();scene.add(root,regionRoot);const world=new THREE.Box3();
 for(const part of packet.preview.objects){
   if(!part.indices.length)continue;const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(part.positions_m,3));geometry.setIndex(part.indices);geometry.computeVertexNormals();
   const material=new THREE.MeshStandardMaterial({color:new THREE.Color(...part.color),roughness:Math.max(.18,part.roughness),metalness:part.metallic,side:THREE.DoubleSide});const mesh=new THREE.Mesh(geometry,material);mesh.userData=part;root.add(mesh);state.meshes.set(part.id,mesh);world.expandByObject(mesh);
 }
 if(world.isEmpty())throw new Error('В пакете нет видимой preview-геометрии');world.getCenter(center);span=Math.max(...world.getSize(new THREE.Vector3()).toArray(),.001);
 const grid=new THREE.GridHelper(span*1.7,18,0x3c5258,0x2c4249);grid.rotation.x=Math.PI/2;grid.position.set(center.x,center.y,world.min.z-span*.08);scene.add(grid);
 marker=new THREE.Mesh(new THREE.SphereGeometry(span*.008,16,12),new THREE.MeshBasicMaterial({color:0xa6e5bd}));marker.visible=false;scene.add(marker);
 $('viewport-empty').remove();frame();resize();new ResizeObserver(resize).observe($('viewport'));
 let pointerStart;renderer.domElement.addEventListener('pointerdown',event=>{pointerStart=[event.clientX,event.clientY];});renderer.domElement.addEventListener('pointerup',event=>{if(!pointerStart||Math.hypot(event.clientX-pointerStart[0],event.clientY-pointerStart[1])>5)return;const rect=renderer.domElement.getBoundingClientRect();const pointer=new THREE.Vector2((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);const ray=new THREE.Raycaster();ray.setFromCamera(pointer,camera);const hits=ray.intersectObjects([...state.meshes.values()].filter(mesh=>mesh.visible));if(hits.length)select(hits[0].object.userData,hits[0].point.toArray());});
 function animate(){renderLoop=requestAnimationFrame(animate);orbit.update();renderer.render(scene,camera);}animate();
}

function parts(){const query=$('part-search').value.toLocaleLowerCase();$('parts').replaceChildren();for(const part of state.packet.preview.objects){if(!part.name.toLocaleLowerCase().includes(query))continue;const row=element('button','part-row'+(state.selected?.id===part.id?' active':''));row.title=part.name;row.append(element('span','part-icon',part.instance?'↳':'◇'),element('span','part-label',part.name),element('span','part-badge',part.role==='protected'?'●':''));row.addEventListener('click',()=>{select(part);showTab('model');});$('parts').append(row);}}
$('part-search').addEventListener('input',parts);
function metric(label,value){const row=element('div','metric');row.append(element('span',null,label),element('strong',null,value));return row;}
function select(part,point=null){state.selected=part;state.point=point;state.meshes.forEach(mesh=>{mesh.material.emissive.set(mesh.userData.id===part.id?0x184d37:0);mesh.material.emissiveIntensity=mesh.userData.id===part.id ? 0.34 : 0;});$('selected-name').textContent=part.name;$('selected-role').textContent=part.instance?'Instance · текущая поза':part.role==='protected'?'Защищаемая деталь':part.role||'Native source';$('selected-metrics').replaceChildren(metric('Triangles',number.format(part.source_triangles)),metric('Preview',number.format(part.preview_triangles)));if(part.bounds){const size=part.bounds.extent_m.map(value=>(value*1000).toFixed(1));$('selected-metrics').append(metric('Размеры, мм',size.join(' × ')));}const observation=state.packet.inspection.objects.find(item=>item.id===part.source_id);if(observation){$('selected-metrics').append(metric('Tiny triangles',number.format(observation.evaluated["triangles_at_or_below_1e-12_m2"])),metric('Boundary edges',number.format(observation.evaluated.boundary_edges)));}$('selected-point').textContent=point?point.map(value=>(value*1000).toFixed(2)).join(' · ')+' мм':'Нажмите на нужную точку поверхности.';$('protect-region').disabled=!point;$('protect-region-mobile').disabled=!point;$('selected-point-mobile').textContent=$('selected-point').textContent;$('isolate-part').disabled=false;$('selection-hint').textContent=point?part.name+' · точка выбрана':part.name;marker.visible=!!point;if(point)marker.position.set(...point);parts();controlEditor();}
$('isolate-part').addEventListener('click',()=>{if(!state.selected)return;state.isolated=!state.isolated;state.meshes.forEach(mesh=>mesh.visible=!state.isolated||mesh.userData.id===state.selected.id);$('isolate-part').textContent=state.isolated?'Показать все детали':'Изолировать деталь';});

function regions(){regionRoot.clear();$('region-count').textContent=String(state.regions.length);$('protected-regions').replaceChildren();if(!state.regions.length){$('protected-regions').append(element('p','muted','Областей пока нет. Выберите точку на модели.'));return;}state.regions.forEach((region,index)=>{const row=element('div','region-row');const label=element('span',null,region.name);label.append(element('small',null,'Радиус '+(region.radius_m*1000).toFixed(1)+' мм · допуск '+(region.tolerance_m*1000).toFixed(3)+' мм'));const remove=element('button',null,'×');remove.setAttribute('aria-label','Удалить область '+region.name);remove.addEventListener('click',()=>{state.regions.splice(index,1);regions();});row.append(label,remove);$('protected-regions').append(row);const sphere=new THREE.Mesh(new THREE.SphereGeometry(region.radius_m,24,16),new THREE.MeshBasicMaterial({color:0x94d8ab,wireframe:true,transparent:true,opacity:.35,depthWrite:false}));sphere.position.set(...region.center_m);regionRoot.add(sphere);});}
$('protect-region').addEventListener('click',()=>{if(!state.selected||!state.point)return;const radius=Number($('region-radius').value)/1000;if(!Number.isFinite(radius)||radius<=0){toast('Задайте положительный радиус');return;}state.regions.push({id:state.selected.id,name:state.selected.name,center_m:[...state.point],radius_m:radius,tolerance_m:5e-6});regions();toast('Область добавлена в договор правки');});
function controlEditor(){
 const host=$('control-editor');host.replaceChildren();if(!state.selected?.controls.length)return;
 host.append(element('p','muted','Желаемые native-параметры. Изменение будет выполнено и проверено в Blender.'));
 state.selected.controls.forEach((control,index)=>{
  const row=element('div','control-row'),label=element('label',null,control.label),input=element('input');
  input.type='number';input.step='any';input.min=control.minimum;input.max=control.maximum;
  input.value=state.controlChanges.get(state.selected.id+':'+index)?.value??control.value;
  input.dataset.controlIndex=String(index);input.setAttribute('aria-label',control.label);
  input.addEventListener('change',()=>{try{collectControlChanges();}catch(error){toast(error.message);}});
  row.append(label,input);host.append(row);
 });
}
function collectControlChanges(){
 const changes=new Map(state.controlChanges);
 for(const input of $('control-editor').querySelectorAll('input[data-control-index]')){
  const index=Number(input.dataset.controlIndex),control=state.selected.controls[index],raw=input.value.trim(),value=Number(raw);
  if(!raw||!Number.isFinite(value)||value<control.minimum||value>control.maximum)throw new Error('Задайте допустимое значение: '+control.label);
  const key=state.selected.id+':'+index;
  if(value===control.value)changes.delete(key);else changes.set(key,{id:state.selected.id,index,value});
 }
 state.controlChanges=changes;return [...changes.values()];
}
$('save-request').addEventListener('click',async()=>{
 const output=$('request-result');output.classList.remove('error');
 if(!state.selected){showTab('model');toast('Сначала выберите деталь');return;}
 const intent=$('edit-intent').value.trim();
 if(!intent){output.textContent='Опишите желаемое изменение.';output.classList.add('error');return;}
 try{
  const request={source_revision:state.packet.revision,intent,selection:{id:state.selected.id,point_m:state.point},protected_regions:state.regions,control_changes:collectControlChanges()};
  const response=await fetch('/api/requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});
  const result=await response.json();if(!response.ok)throw new Error(result.error);
  output.textContent='Сохранено: '+result.request_path+'\nNative-правка ещё не выполнялась. Запрос готов для Codex.';
  toast('Запрос сохранён с текущей версией сцены');
 }catch(error){output.textContent=error.message;output.classList.add('error');}
});

const viewNames={iso:'Объём',front:'Спереди',side:'Сбоку',back:'Сзади',top:'Сверху'};const modeNames={clay:'Нейтральная форма',reflection:'Поток блика',material:'Материалы',checker:'UV checker',silhouette:'Силуэт',normal:'Нормали'};
function imageCard(path,title,detail,kind){const card=element('article','image-card');const image=element('img');image.src=path;image.alt=title;image.loading='lazy';image.addEventListener('click',()=>{$('full-image').src=path;$('full-image').alt=title;$('full-caption').textContent=title+' · '+detail;$('image-dialog').showModal();});const meta=element('div','image-meta');meta.append(element('strong',null,title),element('small',null,detail),element('span','badge'+(kind==='GENERATED_DRAFT'?' generated':''),kind==='REAL_SCENE_RENDER'?'РЕАЛЬНЫЙ BLENDER RENDER':kind==='GENERATED_DRAFT'?'СГЕНЕРИРОВАННЫЙ ДИЗАЙН':'ИСХОДНЫЙ РЕФЕРЕНС'));card.append(image,meta);return card;}
$('close-image').addEventListener('click',()=>$('image-dialog').close());$('image-dialog').addEventListener('click',event=>{if(event.target===$('image-dialog'))$('image-dialog').close();});
function observations(){const objects=state.packet.inspection.objects;const tiny=objects.reduce((total,item)=>total+item.evaluated["triangles_at_or_below_1e-12_m2"],0);const boundaries=objects.reduce((total,item)=>total+item.evaluated.boundary_edges,0);const instances=state.packet.inspection.instances.length;const host=$('diagnostic-cards');for(const [label,value,note,attention] of [['Tiny triangles',tiny,'Адресный технический сигнал',tiny>0],['Boundary edges',boundaries,'Могут быть намеренной конструкцией',false],['Instances',instances,'Дополнительная evaluated geometry',false]]){const card=element('div','diagnostic-card'+(attention?' attention':''));card.append(element('span','eyebrow',label),element('strong',null,number.format(value)),element('p','muted',note));host.append(card);}for(const render of state.packet.renders){$('render-grid').append(imageCard('/data/'+encodeURIComponent(render.path),viewNames[render.view]+' · '+modeNames[render.mode],'Текущая поза · '+state.packet.blender_version+' · '+render.resolution+' px',render.kind));}}
async function references(){const host=$('reference-grid');host.replaceChildren();let generated=[];try{const result=await fetch('/api/resources');if(result.ok)generated=await result.json();}catch{}for(const resource of generated)host.append(imageCard('/data/'+encodeURIComponent(resource.output),resource.purpose,'Дизайн · '+resource.status,'GENERATED_DRAFT'));for(const reference of state.references)host.append(imageCard(reference.url,reference.name,'Выбранное изображение · '+reference.size+' KB','EXTERNAL_REFERENCE'));if(!generated.length&&!state.references.length){for(const render of state.packet.renders.slice(0,4))host.append(imageCard('/data/'+encodeURIComponent(render.path),viewNames[render.view]+' · '+modeNames[render.mode],'Опора для адресного imagegen',render.kind));}}
$('reference-files').addEventListener('change',event=>{for(const file of event.target.files){if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>20*1024*1024){toast('Используйте PNG, JPEG или WebP до 20 MB');continue;}state.references.push({url:URL.createObjectURL(file),name:file.name,size:Math.round(file.size/1024)});}references();});
$('copy-imagegen').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('imagegen-prompt').textContent);toast('Задание imagegen скопировано');}catch{toast('Выделите и скопируйте спецификацию в карточке');}});

async function boot(){try{const response=await fetch('/data/packet.json');if(!response.ok)throw new Error('Visual packet недоступен');const packet=await response.json();if(packet.kind!=='CONTOUR_VISUAL_PACKET'||packet.schema_version!==2)throw new Error('Неподдерживаемый пакет');state.packet=packet;$('scene-name').textContent=packet.source_file||'Текущая сцена';$('revision').textContent='revision '+packet.revision.slice(0,12)+' · Blender '+packet.blender_version;$('part-count').textContent=String(packet.preview.objects.length);$('triangle-count').textContent=number.format(packet.preview.source_triangles);$('imagegen-question').textContent=packet.question||'В этом пакете генерация не запрашивалась.';$('status').textContent='Текущая версия · '+packet.preview.objects.length+' деталей · '+packet.renders.length+' реальных рендеров';if(packet.preview.objects.some(item=>item.preview_sampled))$('preview-warning').textContent='Preview ограничен выборкой triangles. Проверяйте целую поверхность на реальных рендерах.';parts();setup3D(packet);observations();references();try{$('imagegen-prompt').textContent=await (await fetch('/data/imagegen-prompt.txt')).text();}catch{}window.__contourReady={revision:packet.revision,objects:packet.preview.objects.length,renders:packet.renders.length};}catch(error){$('status').textContent=error.message;$('viewport-empty').textContent=error.message;console.error(error);}}
boot();

$('protect-region-mobile').addEventListener('click',()=>{$('region-radius').value=$('region-radius-mobile').value;$('protect-region').click();});
