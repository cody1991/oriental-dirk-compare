// Run: npm ci && npm test
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const fs=require('node:fs');
const data=JSON.parse(fs.readFileSync('data/offers.json'));
async function setup(){
 const dom=new JSDOM('<div id="root"></div>',{runScripts:'outside-only'});
 dom.window.fetch=async()=>({ok:true,json:async()=>data});
 dom.window.eval(fs.readFileSync('app.js','utf8'));
 await new Promise(r=>setImmediate(r));
 return dom.window;
}
test('typing preserves search DOM, focus and mid-string caret',async()=>{
 const w=await setup(),s=w.document.querySelector('input'); s.focus();s.value='Lucky Duck';s.setSelectionRange(3,3);
 s.dispatchEvent(new w.InputEvent('input',{bubbles:true}));
 assert.equal(w.document.querySelector('input'),s);assert.equal(w.document.activeElement,s);assert.equal(s.selectionStart,3);
});
test('IME ignores intermediate pinyin and filters only committed Chinese',async()=>{
 const w=await setup(),s=w.document.querySelector('input');s.focus();
 const before=w.document.querySelectorAll('.offer').length;
 s.dispatchEvent(new w.CompositionEvent('compositionstart'));s.value='kaoya';
 s.dispatchEvent(new w.InputEvent('input',{bubbles:true,isComposing:true}));
 assert.equal(w.document.querySelectorAll('.offer').length,before);
 assert.equal(w.document.querySelector('input'),s);
 s.value='烤鸭';s.dispatchEvent(new w.CompositionEvent('compositionend',{data:'烤鸭'}));
 s.dispatchEvent(new w.InputEvent('input',{bubbles:true}));
 assert.ok(w.document.querySelectorAll('.offer').length>0);assert.ok(w.document.querySelectorAll('.offer').length<before);
 assert.equal(w.document.activeElement,s);assert.equal(s.value,'烤鸭');
});
test('search matches Chinese, original name and brand; clearing restores all',async()=>{
 const w=await setup(),s=w.document.querySelector('input');
 for(const q of ['烤鸭','Lucky Duck','Surasang']){s.value=q;s.dispatchEvent(new w.InputEvent('input'));assert.ok(w.document.querySelectorAll('.offer').length>0,q);}
 s.value='';s.dispatchEvent(new w.InputEvent('input'));assert.equal(w.document.querySelectorAll('.offer').length,data.offers.length);
});

test('composition flag alone defers input; filters and sorting retain committed query',async()=>{
 const w=await setup(),s=w.document.querySelector('input');
 s.value='uncommitted';s.dispatchEvent(new w.InputEvent('input',{isComposing:true}));
 assert.equal(w.document.querySelectorAll('.offer').length,data.offers.length);
 s.value='Surasang';s.dispatchEvent(new w.InputEvent('input'));
 w.document.querySelector('[data-sort="price"]').click();
 assert.equal(w.document.querySelector('input').value,'Surasang');
 assert.ok(w.document.querySelectorAll('.offer').length>0);
 w.document.querySelector('[data-category="Amazing Deals"]').click();
 assert.equal(w.document.querySelector('input').value,'Surasang');
});
test('cards show verified quantities and preserve promo-only wording',async()=>{
 const w=await setup();
 const cards=[...w.document.querySelectorAll('.offer')];
 assert.ok(cards.some(c=>c.textContent.includes('猪肉小笼包') && c.querySelector('.pack').textContent.includes('500 g')));
 for(const o of data.offers.filter(o=>o.sale==null && o.promo)){
   assert.ok(cards.some(c=>c.querySelector('h3').textContent===o.nameZh && c.querySelector('.price').textContent===o.promo));
 }
});
