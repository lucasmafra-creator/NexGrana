(()=>{
const W='https://commons.wikimedia.org/wiki/Special:Redirect/file/';
const files={
 balsa:'Théodore_géricault,_la_zattera_della_medusa,_1819.jpg',
 saturno:'Saturno_devorando_a_sus_hijos_por_Goya.jpg',
 grito:'Edvard-Munch-The-Scream.jpg',
 revolucao:'Prise_de_la_Bastille.jpg',
 roma:'Rome_colosseum_at_night.jpg',
 freud:'Sigmund_Freud.jpg',
 nietzsche:'Portrait_of_Friedrich_Nietzsche.jpg',
 egito:'Great_Pyramid_Giza.jpg',
 estrangeiro:'Camus3.jpg',
 prometeu:'Rubens_-_Prometheus_Bound.jpg'
};
const urls=Object.fromEntries(Object.entries(files).map(([k,v])=>[k,W+encodeURIComponent(v)+'?width=960']));
function keyFrom(src=''){const m=src.match(/assets\/(balsa|saturno|grito|revolucao|roma|freud|nietzsche|egito|estrangeiro|prometeu)_ios\.jpg/);return m&&m[1]}
function fix(img){const k=keyFrom(img.getAttribute('src')||'');if(k){img.onerror=null;img.src=urls[k]}}
function scan(root=document){root.querySelectorAll?.('img').forEach(fix)}
scan();
const hero=document.querySelector('.hero-bg');if(hero)hero.style.backgroundImage=`url("${urls.balsa}")`;
new MutationObserver(ms=>ms.forEach(m=>{
 if(m.type==='attributes'&&m.target.tagName==='IMG')fix(m.target);
 m.addedNodes.forEach(n=>{if(n.nodeType===1){if(n.tagName==='IMG')fix(n);scan(n)}})
})).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['src']});
window.EntrelinhasHostedAssets=urls;
})();