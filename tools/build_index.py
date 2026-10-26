"""template3.html(아티팩트용)을 Vercel 배포용 index.html로 바꿉니다.
- Claude 아티팩트 저장소(window.claude) 대신 /api/state 서버 함수를 씁니다.
- 처음 투표·후기·신고할 때 닉네임을 받습니다(가입 없음).
- 홈 화면 추가(PWA)용 매니페스트·아이콘·서비스워커를 연결합니다.
사용법: python3 tools/build_index.py <template3.html> <data.json> <out index.html>
"""
import re
import sys

tpl, data_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
h = open(tpl, encoding='utf-8').read()
data = open(data_path, encoding='utf-8').read().replace('</', '<\\/')


def rep(a, b, count=1):
    global h
    if a not in h:
        raise SystemExit('missing: ' + a[:80])
    h = h.replace(a, b, count)


# ---- write guards: nickname instead of Claude sign-in / edit rights
rep("  if(!me){toast('투표는 Claude에 로그인해야 할 수 있어요');return;}\n  if(!canWrite){toast('보기 전용으로 열려 있어 투표할 수 없어요');return;}",
    "  if(needName(function(){setMyVote(v);}))return;")
rep("function setGone(p,on){if(!(me&&canWrite)){toast('신고는 편집 권한으로 초대받은 사람만 할 수 있어요');return;}",
    "function setGone(p,on){if(needName(function(){setGone(p,on);}))return;")
rep("      if(dis){toast('후기는 편집 권한으로 초대받은 사람만 남길 수 있어요');return;}",
    "      var formEl=e.target;if(needName(function(){formEl.requestSubmit?formEl.requestSubmit():formEl.dispatchEvent(new Event('submit',{cancelable:true}));}))return;")
rep("  var dis=!(me&&canWrite);", "  var dis=false;")
rep("  if(!(me&&canWrite)){toast('집 추가는 편집 권한으로 초대받은 사람만 할 수 있어요');return;}",
    "  if(needName(function(){var f=document.getElementById('addForm');f.requestSubmit?f.requestSubmit():f.dispatchEvent(new Event('submit',{cancelable:true}));}))return;")
rep("disabled:!(me&&canWrite)||null,onclick:function(){setGone(p,!mine);}", "onclick:function(){setGone(p,!mine);}")
rep("acts.appendChild(el('button',{class:'btn',disabled:!canWrite||null,onclick:function(){markBooked(p.id,!iB);}", "acts.appendChild(el('button',{class:'btn',onclick:function(){markBooked(p.id,!iB);}")

# ---- board banners + who am I
board_old = re.search(r"  if\(!shared\)b\.appendChild\(el\('div',\{class:'banner'.*?\n  else if\(!canWrite\)b\.appendChild\(.*?\n", h, re.S).group(0)
h = h.replace(board_old,
    "  if(!shared)b.appendChild(el('div',{class:'banner',text:offlineMsg}));\n"
    "  b.appendChild(el('div',{style:'margin-top:8px;font-size:.78rem;color:var(--muted);display:flex;gap:8px;align-items:center;flex-wrap:wrap'},[\n"
    "    myName?el('span',{text:myName+' 님으로 참여 중'}):el('span',{text:'처음 투표할 때 닉네임만 정하면 돼요. 가입은 없어요.'}),\n"
    "    myName?el('button',{class:'btn',style:'padding:3px 10px;font-size:.76rem',onclick:function(){openNameSheet(null);},text:'닉네임 바꾸기'}):null]));\n")

# ---- footer copy
rep("<p><b>이렇게 써요.</b> 위에서 근무지를 고르고,",
    "<p><b>이렇게 써요.</b> 처음 투표할 때 닉네임만 정하면 되고 가입은 없습니다. 휴대폰에서 ‘홈 화면에 추가’를 누르면 앱처럼 열 수 있어요. 위에서 근무지를 고르고,")

# ---- replace storage section
start = h.index('/* ---- storage ---- */')
end = h.rindex('})();\n</script>')
storage = r"""/* ---- storage (Vercel /api/state + 기기별 닉네임) ---- */
var LKEY='menuboard.local',IDKEY='menuboard.id',NAMEKEY='menuboard.name',API='/api/state';
var offlineMsg='공유 저장소에 연결되지 않아 내 표·후기가 이 기기에만 남아요. 잠시 뒤 다시 열어 보세요.';
function lsGet(k){try{return localStorage.getItem(k);}catch(e){return null;}}
function lsSet(k,v){try{localStorage.setItem(k,v);}catch(e){}}
function rid(n){var a=new Uint8Array(n);(window.crypto||window.msCrypto).getRandomValues(a);return Array.prototype.map.call(a,function(b){return ('0'+b.toString(16)).slice(-2);}).join('');}
var ident=null;try{ident=JSON.parse(lsGet(IDKEY)||'null');}catch(e){}
if(!ident||!/^u[0-9a-f]{16}$/.test(ident.uid||'')||!/^[0-9a-f]{32}$/.test(ident.key||'')){ident={uid:'u'+rid(8),key:rid(16)};lsSet(IDKEY,JSON.stringify(ident));}
var myName=lsGet(NAMEKEY)||'';
me=ident.uid;canWrite=true;
function loadLocal(){try{var o=JSON.parse(lsGet(LKEY)||'{}');votes={};votes[me]=o.vote||{};reviews={};reviews[me]={items:o.items||{},gone:o.gone||{}};extra=o.extra||{};}catch(e){}}
function saveLocal(){lsSet(LKEY,JSON.stringify({vote:votes[me]||{},items:(reviews[me]||{}).items||{},gone:(reviews[me]||{}).gone||{},extra:extra}));return Promise.resolve();}
var lastSig='';
function sheetBusy(){var a=document.activeElement;return !!(a&&(a.tagName==='TEXTAREA'||a.tagName==='INPUT')&&a.closest&&a.closest('#sheet,#addForm,.namebox'));}
function applyState(j){
  if(!j||!j.ok)return;
  var sig=JSON.stringify([j.votes,j.reviews,j.extra,j.users]);
  var wasShared=shared;shared=true;
  if(sig===lastSig&&wasShared)return;lastSig=sig;
  votes=j.votes||{};reviews=j.reviews||{};names=j.users||{};extra={};
  Object.keys(j.extra||{}).forEach(function(k){extra[k]=Object.assign({s:'sejong'},j.extra[k]);});
  if(sheetBusy()){renderSites();renderBoard();renderTiles();renderPlaces();}else renderAll();
}
function pull(){return fetch(API,{cache:'no-store'}).then(function(r){if(!r.ok)throw new Error(r.status);return r.json();}).then(applyState);}
function post(body){
  body.uid=ident.uid;body.key=ident.key;body.name=myName;
  return fetch(API,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)})
    .then(function(r){return r.json().catch(function(){return {};}).then(function(j){if(!r.ok)throw new Error(j.error||r.status);return j;});})
    .then(applyState);
}
var writeVote=function(doc){return shared?post({op:'vote',doc:doc}):saveLocal();};
var writeReviews=function(doc){return shared?post({op:'reviews',doc:doc}):saveLocal();};
var writeExtra=function(id,p){return shared?post({op:'extra',id:id,place:p}):saveLocal();};
var removeExtra=function(id){delete extra[id];S.sel=null;closeSheet();renderAll();return shared?post({op:'extra_del',id:id}):saveLocal();};

/* ---- nickname sheet ---- */
function needName(after){if(myName)return false;openNameSheet(after);return true;}
function openNameSheet(after){
  var old=document.querySelector('.namebox');if(old)old.remove();
  var inp=el('input',{id:'nick',maxlength:'12',placeholder:'예: 예산총괄 김사무관, 점심요정',value:myName,autocomplete:'nickname'});
  var err=el('div',{style:'color:var(--chili);font-size:.8rem;min-height:1.1em'});
  function close(){box.remove();}
  var form=el('form',{class:'sheet',style:'width:100%;max-width:420px;display:grid;gap:10px',onsubmit:function(e){e.preventDefault();
      var v=inp.value.replace(/[<>]/g,'').trim().slice(0,12);
      if(v.length<2){err.textContent='두 글자 이상 적어 주세요.';inp.focus();return;}
      myName=v;lsSet(NAMEKEY,v);close();renderAll();
      if(shared)post({op:'hello'}).catch(function(){});
      toast(v+' 님, 반가워요');if(after)after();
    }},[el('h3',{text:'닉네임을 정해 주세요'}),
    el('p',{style:'margin:0;color:var(--muted);font-size:.86rem',text:'투표판과 후기에 이 이름으로 보여요. 가입은 없고, 이름 말고는 아무것도 저장하지 않아요. 실명 대신 별명도 괜찮아요.'}),
    inp,err,
    el('div',{style:'display:flex;gap:8px;justify-content:flex-end'},[el('button',{class:'btn',type:'button',onclick:close,text:'나중에'}),el('button',{class:'btn dark',type:'submit',text:'시작하기'})])]);
  var box=el('div',{class:'namebox',style:'position:fixed;inset:0;z-index:50;display:flex;align-items:center;justify-content:center;padding:16px;background:color-mix(in srgb,var(--ink) 45%,transparent)',onclick:function(e){if(e.target===box)close();}},[form]);
  document.body.appendChild(box);setTimeout(function(){inp.focus();},30);
}

loadLocal();renderAll();
document.getElementById('side').hidden=matchMedia('(max-width:959px)').matches;
pull().catch(function(){shared=false;renderBoard();});
try{fetch('/api/stats',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({vid:ident.uid,site:S.site})}).catch(function(){});}catch(e){}
setInterval(function(){if(document.visibilityState==='visible')pull().catch(function(){});},20000);
document.addEventListener('visibilitychange',function(){if(document.visibilityState==='visible')pull().catch(function(){});});
if('serviceWorker' in navigator&&location.protocol==='https:'){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js').catch(function(){});});}

/* ---- 홈 화면에 추가 안내 ---- */
(function(){
  var ua=navigator.userAgent||'';
  var standalone=(window.matchMedia&&matchMedia('(display-mode: standalone)').matches)||navigator.standalone===true;
  var isKakao=/KAKAOTALK/i.test(ua), isInApp=isKakao||/NAVER\(inapp|Line\/|BAND\/|Instagram|FBAN|FBAV|DaumApps|everytimeApp|; wv\)/i.test(ua);
  var isIOS=/iPhone|iPad|iPod/i.test(ua)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  var isAndroid=/Android/i.test(ua), isMobile=isIOS||isAndroid;
  var deferred=null, DKEY='menuboard.installHide';
  function hidden(){var t=+(lsGet(DKEY)||0);return t&&Date.now()-t<14*864e5;}
  function bar(msg,btns){
    var old=document.getElementById('installBar');if(old)old.remove();
    var b=el('div',{id:'installBar',role:'region','aria-label':'홈 화면에 추가',style:'display:flex;gap:10px;align-items:center;flex-wrap:wrap;background:var(--chili-soft);border:1px solid color-mix(in srgb,var(--chili) 35%,transparent);color:var(--ink);border-radius:14px;padding:10px 12px;margin:0 0 12px;font-size:.88rem;line-height:1.45'},
      [el('div',{style:'flex:1 1 220px'},msg)].concat(btns).concat([el('button',{class:'btn',type:'button','aria-label':'안내 닫기',text:'닫기',onclick:function(){lsSet(DKEY,String(Date.now()));b.remove();}})]));
    var w=document.querySelector('.wrap');w.insertBefore(b,w.firstChild);
  }
  function guide(){
    if(isKakao){
      bar([el('b',{text:'카카오톡 안에서는 앱 설치가 안 돼요. '}),'‘다른 브라우저로 열기’를 눌러 크롬·사파리에서 연 뒤 홈 화면에 추가해 주세요.'],
        [el('a',{class:'btn dark',href:'kakaotalk://web/openExternal?url='+encodeURIComponent(location.href),text:'다른 브라우저로 열기'})]);
    }else if(isInApp){
      bar([el('b',{text:'앱 안의 브라우저에서는 설치가 안 돼요. '}),'오른쪽 위 ⋯ 메뉴에서 ‘다른 브라우저로 열기’(또는 ‘Safari/Chrome으로 열기’)를 눌러 주세요.'],[]);
    }else if(deferred){
      bar([el('b',{text:'홈 화면에 앱처럼 깔아 두세요. '}),'다음부터 아이콘 한 번으로 열려요.'],
        [el('button',{class:'btn dark',type:'button',text:'홈 화면에 추가',onclick:function(){var d=deferred;deferred=null;d.prompt();(d.userChoice||Promise.resolve({})).then(function(c){var x=document.getElementById('installBar');if(x)x.remove();if(c.outcome==='accepted')toast('홈 화면에 추가했어요');});}})]);
    }else if(isIOS){
      bar([el('b',{text:'홈 화면에 앱처럼 깔아 두세요. '}),'Safari 아래쪽 공유 버튼(네모에 ↑) → ‘홈 화면에 추가’ → ‘추가’.'],[]);
    }else if(isAndroid){
      bar([el('b',{text:'홈 화면에 앱처럼 깔아 두세요. '}),'브라우저 오른쪽 위 ⋮ 메뉴 → ‘홈 화면에 추가’ 또는 ‘앱 설치’.'],[]);
    }
  }
  window.showInstallGuide=function(){lsSet(DKEY,'0');if(standalone){toast('이미 홈 화면 앱으로 쓰고 있어요');return;}if(!isMobile&&!deferred){location.href='/install';return;}guide();window.scrollTo({top:0,behavior:'smooth'});};
  window.addEventListener('beforeinstallprompt',function(e){e.preventDefault();deferred=e;if(!standalone&&!hidden())guide();});
  window.addEventListener('appinstalled',function(){var x=document.getElementById('installBar');if(x)x.remove();});
  if(!standalone&&isMobile&&!hidden())setTimeout(function(){if(!document.getElementById('installBar'))guide();},1200);
  var f=document.querySelector('footer');
  if(f&&!standalone)f.insertBefore(el('p',{},[el('b',{text:'휴대폰 홈 화면에 추가. '}),el('a',{href:'/install',onclick:function(e){if(isMobile){e.preventDefault();window.showInstallGuide();}},text:'설치 방법 보기 · 동료에게 보여줄 QR 코드'})]),f.firstChild);
})();
"""
h = h[:start] + storage + h[end:]
h = h.replace("var me=null,canWrite=false,votes={},reviews={},extra={},names={},shared=false,db=null,userCap=null;",
              "var me=null,canWrite=false,votes={},reviews={},extra={},names={},shared=false;")

# ---- full HTML document
head_end = h.index('<div class="wrap">')
head, body = h[:head_end], h[head_end:]
head = head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
head = head.replace('<style>', '<style>\n[hidden]{display:none!important}\n:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}\nimg{max-width:100%}', 1)
doc = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
       '<meta name="description" content="세종·반포·여의도·서울역 근무지별 점심 메뉴와 회식 장소를 함께 고르는 앱">\n'
       '<meta name="theme-color" content="#d4451a">\n'
       '<link rel="manifest" href="/manifest.webmanifest">\n'
       '<link rel="icon" href="/icons/icon-192.png">\n'
       '<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">\n'
       '<meta name="apple-mobile-web-app-capable" content="yes">\n'
       '<meta name="apple-mobile-web-app-title" content="뭐 먹지">\n'
       + head + '</head>\n<body>\n' + body.replace('__DATA__', data) + '\n</body>\n</html>\n')
open(out, 'w', encoding='utf-8').write(doc)
print('wrote', out, len(doc))
