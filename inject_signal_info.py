with open('/Users/tanishbansal/Projects/icici_bank_signals/dashboard_template.html','r',encoding='utf-8') as f:
    html = f.read()

# ── 1. ADD CSS for the expandable signal info card ────────────────────────
signal_css = (
    "\n  /* --- Signal info expand --- */\n"
    "  .raw-item{ display:flex; justify-content:space-between; border-bottom:1px dashed var(--rule); padding-bottom:5px; cursor:pointer; transition:background .15s; border-radius:4px; padding:4px 6px; margin:-4px -6px; }\n"
    "  .raw-item:hover{ background:rgba(var(--teal-rgb,30,130,120),.06); }\n"
    "  .raw-item .rk{ color:var(--slate); display:flex; align-items:center; gap:5px; }\n"
    "  .raw-info-icon{ font-size:10px; color:var(--teal-dim); opacity:.7; transition:opacity .15s; }\n"
    "  .raw-item:hover .raw-info-icon{ opacity:1; }\n"
    "  .raw-expand{ display:none; font-size:11.5px; line-height:1.7; padding:8px 10px 10px; margin-top:4px; "
    "background:rgba(var(--teal-rgb,30,130,120),.05); border-left:3px solid var(--teal-dim); border-radius:0 6px 6px 0; }\n"
    "  .raw-expand.open{ display:block; }\n"
    "  .raw-expand .sig-desc{ color:var(--ink); margin-bottom:4px; }\n"
    "  .raw-expand .sig-why{ color:var(--slate); font-style:italic; }\n"
    "  .raw-expand .sig-why::before{ content:'Why a proxy: '; font-style:normal; font-weight:600; color:var(--teal-dim); }\n"
)
last_style = html.rfind('</style>')
html = html[:last_style] + signal_css + html[last_style:]

# ── 2. REPLACE the rawFields rendering to include info icon + expand panel ─
old_raw_render = (
    '    <div class="raw-grid">\n'
    '      ${rawFields.map(([label,key])=>`\n'
    '        <div class="raw-item"><span class="rk">${label}</span><span class="rv num">${r[key]}</span></div>\n'
    '      `).join(\'\')}\n'
    '    </div>'
)
new_raw_render = (
    '    <div class="raw-grid">\n'
    '      ${rawFields.map(([label,key])=>{\n'
    '        const info = SIGNAL_INFO[key];\n'
    '        const hasInfo = !!info;\n'
    '        return `\n'
    '          <div>\n'
    '            <div class="raw-item" onclick="this.nextElementSibling.classList.toggle(\'open\')">\n'
    '              <span class="rk">${label}${hasInfo ? \'<span class="raw-info-icon">&#9432;</span>\' : \'\'}</span>\n'
    '              <span class="rv num">${r[key]}</span>\n'
    '            </div>\n'
    '            ${hasInfo ? `<div class="raw-expand"><div class="sig-desc">${info.desc}</div><div class="sig-why">${info.why}</div></div>` : \'\'}\n'
    '          </div>\n'
    '        `;\n'
    '      }).join(\'\')}\n'
    '    </div>'
)
assert old_raw_render in html, "Raw render target not found!"
html = html.replace(old_raw_render, new_raw_render, 1)

# ── 3. ADD SIGNAL_INFO constant (before the openDetail function) ───────────
signal_info_js = """
const SIGNAL_INFO = {
  mf: {
    desc: 'Number of AMFI-registered mutual fund distributors actively operating in this pincode.',
    why:  'MF distributors cluster where investable surplus exists — they follow the money. A high count signals financially sophisticated households with assets beyond basic savings.'
  },
  ia: {
    desc: 'Count of SEBI-registered investment advisors (RIAs) serving this pincode catchment.',
    why:  'RIAs operate where clients have significant financial wealth to manage. Their presence is a strong indicator of a dense HNW or upper-middle-income base.'
  },
  ch: {
    desc: 'Number of major corporate offices, IT parks, and business centres in or adjacent to this pincode.',
    why:  'Corporate clusters drive high-income salaried employment, group insurance demand, and discretionary spending — the core ICICI wealth management customer profile.'
  },
  rb: {
    desc: 'Total bank and financial institution branches (private + public sector) in this pincode.',
    why:  'Branch density tracks transaction volumes and wallet size. Premium banks invest in branches only where per-customer revenue justifies it — a strong affluence proxy.'
  },
  rr: {
    desc: 'Ratio of private bank branches to public sector bank branches in this pincode.',
    why:  'A higher private bank share means customers prefer premium, fee-based services over basic banking. This private preference reliably separates middle-income from mass-market segments.'
  },
  ps: {
    desc: "Count of premium retail outlets — Nature's Basket, Apollo Pharmacy, luxury brands, specialty stores — in this pincode.",
    why:  'Premium retailers run rigorous catchment feasibility studies before opening. Their presence is a market-validated signal that disposable income in the area exceeds mass-market thresholds.'
  },
  gc: {
    desc: 'Number of golf courses and golf clubs within or directly adjacent to this pincode.',
    why:  'Golf is one of the strongest lifestyle wealth indicators in India — membership fees run ₹5L to ₹50L+. Even one course flags an ultra-HNW catchment worth prioritising for wealth products.'
  },
  hc: {
    desc: 'Number of NABH-accredited hospitals — India\'s national standard for clinical quality and patient safety.',
    why:  'NABH hospitals charge premium rates and primarily serve cashless, high-value health insurance clients. They locate where paying patients live, directly mapping to income-insured households.'
  },
  ev: {
    desc: 'Number of EV charging stations (public infrastructure + registered residential society chargers) in this pincode.',
    why:  'EV adoption in India remains income-gated — entry-level EVs start at ₹12L–₹15L+. Charging infrastructure density is a forward-looking proxy for early-adopter, high-income households.'
  },
  sch: {
    desc: 'Number of schools affiliated with premium boards (CBSE, ICSE, IB, IGCSE) in this pincode catchment.',
    why:  'Premium education spend — ₹2L to ₹8L+ per year in fees — is one of the clearest early signals of affluence. School density and board type directly reflect the parental income profile of the catchment.'
  },
  est: {
    desc: 'Total registered commercial establishments (shops, offices, factories, service businesses) in this pincode per government records.',
    why:  'Commercial density is a leading indicator of local economic activity, employment generation, and consumer spending power. Higher establishment counts identify economically vibrant urban micro-markets.'
  }
};
"""

# Insert before openDetail function
insert_before = 'function openDetail(pincode){'
assert insert_before in html, "openDetail not found!"
html = html.replace(insert_before, signal_info_js + insert_before, 1)

with open('/Users/tanishbansal/Projects/icici_bank_signals/dashboard_template.html','w',encoding='utf-8') as f:
    f.write(html)
print("Done. Size:", len(html)//1024, "KB")
