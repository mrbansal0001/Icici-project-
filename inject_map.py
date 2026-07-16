import json

with open('/Users/tanishbansal/Projects/icici_bank_signals/india_states_simplified.geojson') as f:
    geojson_str = f.read()

with open('/Users/tanishbansal/Projects/icici_bank_signals/dashboard_template.html','r',encoding='utf-8') as f:
    html = f.read()

# 1. Nav button
old_nav = '<button data-view="about"><span class="idx">06</span> Methodology</button>'
new_nav = '<button data-view="map"><span class="idx">06</span> Map</button>\n      <button data-view="about"><span class="idx">07</span> Methodology</button>'
assert old_nav in html
html = html.replace(old_nav, new_nav, 1)

# 2. Leaflet in <head>
old_meta = '<meta charset="UTF-8">'
assert old_meta in html
html = html.replace(old_meta,
    '<meta charset="UTF-8">\n  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>\n  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>', 1)

# 3. Map CSS
map_css = (
    "\n  #map-leaflet{width:100%;height:calc(100vh - 200px);min-height:480px;border-radius:10px;z-index:0;}\n"
    "  .map-wrap{position:relative;}\n"
    "  #map-controls{position:absolute;top:16px;right:16px;z-index:999;background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:14px 16px;min-width:190px;box-shadow:0 4px 20px rgba(0,0,0,.14);}\n"
    "  #map-controls h4{margin:0 0 10px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--slate);}\n"
    "  .map-check-row{display:flex;align-items:center;gap:8px;font-size:13px;margin-bottom:7px;cursor:pointer;user-select:none;}\n"
    "  .map-check-row input{cursor:pointer;accent-color:var(--teal);}\n"
    "  .map-dot{width:10px;height:10px;border-radius:50%;display:inline-block;flex-shrink:0;}\n"
    "  .map-dot-P{background:#C9A227;}.map-dot-G{background:#3D8A7A;}.map-dot-S{background:#4A7AB5;}.map-dot-N{background:#8B93A0;}\n"
    "  #map-state-panel{position:absolute;bottom:24px;left:16px;z-index:999;background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:16px 18px;min-width:220px;box-shadow:0 4px 20px rgba(0,0,0,.14);display:none;}\n"
    "  #map-state-panel .sp-name{font-size:16px;font-weight:700;margin-bottom:8px;}\n"
    "  #map-state-panel .sp-stats{font-size:12.5px;color:var(--slate);line-height:2;}\n"
    "  #map-back-btn{position:absolute;top:16px;left:16px;z-index:999;display:none;}\n"
    "  .leaflet-tip{font-family:'IBM Plex Sans',sans-serif!important;font-size:12.5px;line-height:1.6;border-radius:6px!important;}\n"
)
last_style = html.rfind('</style>')
html = html[:last_style] + map_css + html[last_style:]

# 4. Map HTML section
map_html = (
    "\n    <section class=\"view\" id=\"view-map\">\n"
    "      <div class=\"view-head\">\n"
    "        <div class=\"eyebrow\">Geo Intelligence</div>\n"
    "        <h1>India Affluence Map</h1>\n"
    "        <p>Hover a state to see its stats. Click a state to zoom in and reveal pincode markers. Click any marker to open the full pincode detail.</p>\n"
    "      </div>\n"
    "      <div class=\"map-wrap\">\n"
    "        <div id=\"map-leaflet\"></div>\n"
    "        <button class=\"btn ghost\" id=\"map-back-btn\">&larr; All India</button>\n"
    "        <div id=\"map-controls\">\n"
    "          <h4>Show tiers</h4>\n"
    "          <label class=\"map-check-row\"><input type=\"checkbox\" id=\"mc-P\" checked><span class=\"map-dot map-dot-P\"></span>Platinum</label>\n"
    "          <label class=\"map-check-row\"><input type=\"checkbox\" id=\"mc-G\" checked><span class=\"map-dot map-dot-G\"></span>Gold</label>\n"
    "          <label class=\"map-check-row\"><input type=\"checkbox\" id=\"mc-S\" checked><span class=\"map-dot map-dot-S\"></span>Silver</label>\n"
    "          <label class=\"map-check-row\"><input type=\"checkbox\" id=\"mc-N\"><span class=\"map-dot map-dot-N\"></span>Standard</label>\n"
    "          <hr style=\"border:none;border-top:1px solid var(--rule);margin:10px 0;\">\n"
    "          <label class=\"map-check-row\" style=\"font-size:12px;color:var(--slate);\"><input type=\"checkbox\" id=\"mc-top-only\"> Top 25 per state</label>\n"
    "        </div>\n"
    "        <div id=\"map-state-panel\">\n"
    "          <div class=\"sp-name\" id=\"sp-name\">&#8212;</div>\n"
    "          <div class=\"sp-stats\" id=\"sp-stats\"></div>\n"
    "          <button class=\"btn\" id=\"sp-explorer-btn\" style=\"margin-top:10px;font-size:12px;\">View in Explorer &rarr;</button>\n"
    "        </div>\n"
    "      </div>\n"
    "    </section>\n"
)
html = html.replace('</body>', map_html + '</body>', 1)

# 5. GeoJSON const + map JS
geojson_js = '\nconst INDIA_GEO = ' + geojson_str + ';\n'

map_js = r"""
/* === MAP (Leaflet) === */
var mapInitialized=false,leafletMap=null,stateGeoLayer=null,markerLG=null,currentMapState=null;
var TIER_COLOR={P:'#C9A227',G:'#3D8A7A',S:'#4A7AB5',N:'#8B93A0'};
var TIER_RADIUS={P:7,G:5.5,S:4.5,N:3.5};

function mapStateStats(n){
  var rows=ROWS.filter(function(r){return STATES[r.s]===n;});
  return {rows:rows,
    plat:rows.filter(function(r){return r.t==='P';}).length,
    gold:rows.filter(function(r){return r.t==='G';}).length,
    silv:rows.filter(function(r){return r.t==='S';}).length,
    std:rows.filter(function(r){return r.t==='N';}).length,
    avg:rows.length?(rows.reduce(function(s,r){return s+r.sc;},0)/rows.length).toFixed(1):'N/A'};
}
function mapTiers(){
  return ['P','G','S','N'].filter(function(t){var e=document.getElementById('mc-'+t);return e&&e.checked;});
}
function choroplethCol(score){
  var t=Math.max(0,Math.min(1,(score-30)/65));
  return 'rgb('+Math.round(240-t*180)+','+Math.round(230-t*90)+','+Math.round(200-t*80)+')';
}
function renderMapMarkers(stateName){
  if(!leafletMap) return;
  if(!markerLG){markerLG=L.layerGroup().addTo(leafletMap);}
  markerLG.clearLayers();
  var tiers=mapTiers(),topOnly=document.getElementById('mc-top-only').checked;
  var cands=ROWS.filter(function(r){
    return r.lat!=null&&r.lon!=null&&tiers.indexOf(r.t)>=0&&(!stateName||STATES[r.s]===stateName);
  });
  if(topOnly){
    if(stateName){
      cands=cands.sort(function(a,b){return b.sc-a.sc;}).slice(0,25);
    } else {
      var ps={},out=[];
      cands.sort(function(a,b){return b.sc-a.sc;}).forEach(function(r){
        ps[r.s]=(ps[r.s]||0)+1; if(ps[r.s]<=5) out.push(r);
      });
      cands=out;
    }
  }
  cands.forEach(function(r){
    var m=L.circleMarker([r.lat,r.lon],{radius:TIER_RADIUS[r.t],fillColor:TIER_COLOR[r.t],
      color:'#fff',weight:1.2,opacity:1,fillOpacity:0.88});
    m.bindTooltip('<b>'+r.p+'</b> &nbsp;'+STATES[r.s]+'<br>Score: <b>'+r.sc.toFixed(1)+'</b> &middot; <b>'+TIER_NAME[r.t]+'</b>',
      {direction:'top',offset:[0,-4],className:'leaflet-tip'});
    m.on('click',function(){openDetail(r.p);});
    markerLG.addLayer(m);
  });
}
function showMapStatePanel(name){
  var s=mapStateStats(name);
  document.getElementById('sp-name').textContent=name;
  document.getElementById('sp-stats').innerHTML=
    'Avg score: <b>'+s.avg+'</b><br>'+
    '<span style="color:#C9A227;">&#9679;</span> Platinum: <b>'+s.plat+'</b> &nbsp; '+
    '<span style="color:#3D8A7A;">&#9679;</span> Gold: <b>'+s.gold+'</b><br>'+
    '<span style="color:#4A7AB5;">&#9679;</span> Silver: <b>'+s.silv+'</b> &nbsp; '+
    '<span style="color:#8B93A0;">&#9679;</span> Standard: <b>'+s.std+'</b>';
  document.getElementById('map-state-panel').style.display='block';
  document.getElementById('sp-explorer-btn').onclick=function(){
    document.querySelector('[data-view="explorer"]').click();
    setTimeout(function(){var sel=document.getElementById('f-state');if(sel){sel.value=name;sel.dispatchEvent(new Event('input'));}},200);
  };
}
function initLeafletMap(){
  if(mapInitialized) return;
  mapInitialized=true;
  leafletMap=L.map('map-leaflet',{center:[22.5,82.5],zoom:5,minZoom:4,maxZoom:14,preferCanvas:true});
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',
    {attribution:'&copy; OpenStreetMap &copy; CARTO',subdomains:'abcd',opacity:0.45}).addTo(leafletMap);
  var ssm={};
  STATE_SUMMARY.forEach(function(s){ssm[s.state]=s.avg_score;});
  stateGeoLayer=L.geoJSON(INDIA_GEO,{
    style:function(f){return{fillColor:choroplethCol(ssm[f.properties.name]||0),weight:1.5,color:'#5B6472',fillOpacity:0.72};},
    onEachFeature:function(f,layer){
      var name=f.properties.name,score=ssm[name];
      var stats=mapStateStats(name);
      layer.bindTooltip('<b>'+name+'</b><br>Avg score: '+(score?score.toFixed(1):'N/A')+'<br>Platinum: '+stats.plat+' of '+stats.rows.length,
        {sticky:true,className:'leaflet-tip'});
      layer.on({
        mouseover:function(e){e.target.setStyle({weight:2.5,color:'#1A2740',fillOpacity:0.92});},
        mouseout:function(e){stateGeoLayer.resetStyle(e.target);},
        click:function(e){
          currentMapState=name;
          leafletMap.fitBounds(e.target.getBounds(),{padding:[40,40]});
          renderMapMarkers(name);
          showMapStatePanel(name);
          document.getElementById('map-back-btn').style.display='block';
        }
      });
    }
  }).addTo(leafletMap);
  document.getElementById('mc-top-only').checked=true;
  renderMapMarkers(null);
  ['mc-P','mc-G','mc-S','mc-N','mc-top-only'].forEach(function(id){
    document.getElementById(id).addEventListener('change',function(){renderMapMarkers(currentMapState);});
  });
  document.getElementById('map-back-btn').addEventListener('click',function(){
    currentMapState=null;
    leafletMap.setView([22.5,82.5],5);
    document.getElementById('map-state-panel').style.display='none';
    document.getElementById('map-back-btn').style.display='none';
    renderMapMarkers(null);
  });
}
document.querySelector('[data-view="map"]').addEventListener('click',function(){setTimeout(initLeafletMap,100);});
"""

last_idx = html.rfind('</script>')
html = html[:last_idx] + geojson_js + map_js + '\n</script>' + html[last_idx+len('</script>'):]

with open('/Users/tanishbansal/Projects/icici_bank_signals/dashboard_template.html','w',encoding='utf-8') as f:
    f.write(html)
print('Done. Size:', len(html)//1024, 'KB')
