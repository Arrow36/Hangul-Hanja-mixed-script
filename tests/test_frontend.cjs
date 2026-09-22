const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const read = name => fs.readFileSync(path.join(__dirname, '../app/static', name), 'utf8');
const app = read('app.js');
function harness() {
    const pending = [];
    const ctx = {
        AbortController, console,
        state: {sidebarClosed:false, inputRevision:0, selectedSegmentId:0, segments:[]},
        elSidebarContent:{}, openSidebar(){ctx.state.sidebarClosed=false;},
        m:x=>x,t:x=>x,showToast(){},renderResult(){},
        renderSearchResults(data){ctx.rendered=data.query;},
        renderSidebar(data){ctx.rendered='entry:'+ctx.state.sidebarEntry.id;},
        fetch(url,options){return new Promise(resolve=>pending.push({url,options,resolve}));},
    };
    vm.createContext(ctx);
    vm.runInContext(read('requests.js')+'\nconst sidebarGate=new RequestGate(), selectionGate=new RequestGate(), rawGate=new RequestGate();',ctx);
    vm.runInContext(app.slice(app.indexOf('async function lookupEntry('),app.indexOf('async function loadRawEntry(')),ctx);
    return {ctx,pending,respond(i,data){pending[i].resolve({ok:true,json:async()=>data});}};
}

test('late search never replaces a newer search', async()=>{
    const h=harness();const old=h.ctx.searchDictionary('old'),fresh=h.ctx.searchDictionary('new');
    h.respond(1,{query:'new'});await fresh;h.respond(0,{query:'old'});await old;
    assert.equal(h.ctx.rendered,'new');assert.equal(h.pending[0].options.signal.aborted,true);
});
test('search and entry lookup share a generation', async()=>{
    const h=harness();const search=h.ctx.searchDictionary('old'),entry=h.ctx.lookupEntry(2);
    h.respond(1,{id:2});await entry;h.respond(0,{query:'old'});await search;
    assert.equal(h.ctx.rendered,'entry:2');
});
test('guard runs after a slow response body, not just headers',async()=>{
    const h=harness();let body;
    const old=h.ctx.lookupEntry(1);
    h.pending[0].resolve({ok:true,json:()=>new Promise(resolve=>body=resolve)});
    await Promise.resolve();await Promise.resolve();
    const fresh=h.ctx.lookupEntry(2);h.respond(1,{id:2});await fresh;
    body({id:1});await old;assert.equal(h.ctx.rendered,'entry:2');
});
test('closing then reopening does not revive an old search',async()=>{
    const h=harness();const old=h.ctx.searchDictionary('old');
    vm.runInContext('sidebarGate.cancel()',h.ctx);h.ctx.state.sidebarClosed=false;
    h.respond(0,{query:'old'});await old;assert.equal(h.ctx.rendered,undefined);
});
test('candidate result is discarded after input changes',async()=>{
    const h=harness();const segment={segment_id:0,original:'발전',display_text:'발전',candidates:[{entry_id:2}]};
    h.ctx.state.segments=[segment];const request=h.ctx.applyCandidateChoice(0,0);
    h.ctx.state.inputRevision++;
    h.respond(0,{display_text:'發展',matched_entry_id:2,is_reliable:true});await request;
    assert.equal(segment.display_text,'발전');assert.equal(h.pending.length,1);
});
test('candidate result is discarded after segments are replaced',async()=>{
    const h=harness();const old={segment_id:0,original:'발전',display_text:'발전',candidates:[{entry_id:2}]};
    h.ctx.state.segments=[old];const request=h.ctx.applyCandidateChoice(0,0);
    h.ctx.state.segments=[{segment_id:0,original:'경제'}];
    h.respond(0,{display_text:'發展',matched_entry_id:2,is_reliable:true});await request;
    assert.equal(old.display_text,'발전');assert.equal(h.pending.length,1);
});
test('explicit /kr overrides saved language and navigation preserves URL details',()=>{
    const ctx={location:{pathname:'/kr',search:'?source=share',hash:'#text',protocol:'https:'},navigator:{languages:['en-US']},localStorage:{getItem:()=> 'zh',setItem(){}},document:{},history:{pushState(_a,_b,url){ctx.url=url;}}};
    vm.createContext(ctx);vm.runInContext(read('languages.js'),ctx);
    assert.equal(vm.runInContext('LanguageRoutes.initialLanguage()',ctx),'ko');
    vm.runInContext("LanguageRoutes.navigate('en')",ctx);
    assert.equal(ctx.url,'/en?source=share#text');assert.match(ctx.document.cookie,/ui-language=en/);
    assert.match(ctx.document.cookie,/Secure/);
});
