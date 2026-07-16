with open('/Users/tanishbansal/Projects/icici_bank_signals/dashboard_template.html','r',encoding='utf-8') as f:
    html = f.read()

# 1. Add CSS for documentary style
doc_css = """
  /* --- Documentary Style Methodology --- */
  .doc-hero { padding: 40px 0 60px; border-bottom: 1px solid var(--rule); margin-bottom: 40px; }
  .doc-hero h1 { font-size: 42px; letter-spacing: -1px; margin: 10px 0 20px; color: var(--ink); }
  .doc-hero .lead { font-size: 18px; line-height: 1.6; color: var(--slate); max-width: 800px; }
  .doc-hero .lead strong { color: var(--teal); font-weight: 600; }
  
  .doc-section { margin-bottom: 60px; }
  .doc-section h2 { font-size: 24px; border-bottom: 2px solid var(--teal-dim); padding-bottom: 10px; margin-bottom: 24px; display: inline-block; color: var(--ink); }
  
  /* Scoring Steps */
  .scoring-card { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; background: rgba(var(--teal-rgb,30,130,120), 0.03); border: 1px solid var(--rule); border-radius: 8px; padding: 24px; }
  .scoring-step { position: relative; }
  .scoring-step .step-num { font-size: 48px; font-weight: 800; color: rgba(var(--teal-rgb,30,130,120), 0.1); position: absolute; top: -15px; left: -10px; z-index: 0; }
  .scoring-step h4 { font-size: 16px; font-weight: 700; color: var(--ink); margin-bottom: 8px; position: relative; z-index: 1; }
  .scoring-step p { font-size: 14px; line-height: 1.5; color: var(--slate); position: relative; z-index: 1; }
  
  /* Pillar Grid */
  .pillar-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
  .pillar-card { border: 1px solid var(--rule); border-radius: 8px; padding: 24px; background: white; transition: box-shadow 0.2s; }
  .pillar-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
  .pillar-card h3 { color: var(--teal); font-size: 18px; margin-bottom: 12px; }
  .pillar-card p { font-size: 14px; color: var(--slate); line-height: 1.5; }
  .pillar-tags { margin-top: 16px; display: flex; flex-wrap: wrap; gap: 8px; }
  .pillar-tags span { background: var(--paper); border: 1px solid var(--rule); padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 500; color: var(--ink); }

  /* Signal Masonry (Populated by JS) */
  .signal-masonry { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
  .sig-card { background: white; border: 1px solid var(--rule); border-radius: 8px; padding: 20px; border-top: 4px solid var(--gold-soft); }
  .sig-card h4 { font-size: 15px; margin-bottom: 10px; color: var(--ink); }
  .sig-card .s-desc { font-size: 13px; color: var(--slate); margin-bottom: 12px; line-height: 1.5; }
  .sig-card .s-why { font-size: 13px; color: var(--ink); font-style: italic; background: rgba(var(--gold-rgb, 212,175,55), 0.08); padding: 10px; border-radius: 4px; }
  .sig-card .s-why::before { content: 'Strategic Proxy: '; font-style: normal; font-weight: 600; color: var(--gold); }
  
  /* Playbook */
  .playbook-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
  .play-card { background: var(--ink); color: white; padding: 24px; border-radius: 8px; }
  .play-card h4 { color: var(--gold); font-size: 16px; margin-bottom: 12px; }
  .play-card p { font-size: 14px; line-height: 1.6; opacity: 0.9; }
"""
# inject CSS right before </style>
last_style = html.rfind('</style>')
html = html[:last_style] + doc_css + html[last_style:]

# 2. Replace the HTML section
new_about_html = """    <section class="view" id="view-about">
      <div class="doc-hero">
        <div class="eyebrow">Decoding India's Micro-Wealth</div>
        <h1>The Affluence Index</h1>
        <p class="lead">Wealth in India isn't just about stated income; it's about <strong>footprints</strong>. Where do people invest, shop, educate, and heal? This index aggregates 11 distinct commercial and lifestyle signals to reveal true purchasing power at the pincode level.</p>
      </div>

      <div class="doc-section">
        <h2>How the Score is Calculated</h2>
        <div class="scoring-card">
          <div class="scoring-step">
            <div class="step-num">1</div>
            <h4>Normalize</h4>
            <p>Every raw signal (e.g., number of MF distributors) is converted to a <strong>percentile rank (0–100)</strong> across all pincodes. This prevents a single extreme outlier from distorting the entire scale.</p>
          </div>
          <div class="scoring-step">
            <div class="step-num">2</div>
            <h4>Aggregate into Pillars</h4>
            <p>The percentiles of underlying signals are averaged to create four distinct <strong>Pillar Scores (0–100)</strong>.</p>
          </div>
          <div class="scoring-step">
            <div class="step-num">3</div>
            <h4>Final Composite</h4>
            <p>The final Affluence Score is a perfectly balanced weighted sum: <strong>25% per Pillar</strong>. This ensures a holistic view rather than skewing toward just one type of wealth. Pincodes are then bucketed into Platinum (Top 2%), Gold (Top 10%), Silver (Top 30%), and Standard tiers based on this final score.</p>
          </div>
        </div>
      </div>

      <div class="doc-section">
        <h2>The Four Pillars of Wealth</h2>
        <div class="pillar-grid">
           <div class="pillar-card">
             <h3>Financial Penetration</h3>
             <p>Tracks the density of wealth management professionals. Financial service providers operate strictly where investable surplus exists.</p>
             <div class="pillar-tags"><span>MF Distributors</span><span>Investment Advisors</span></div>
           </div>
           <div class="pillar-card">
             <h3>Commercial Vibrancy</h3>
             <p>Measures economic activity and corporate presence, which drive high-income salaried employment and discretionary spending.</p>
             <div class="pillar-tags"><span>Corporate Hubs</span><span>Retail Branches</span><span>Private:Public Bank Ratio</span></div>
           </div>
           <div class="pillar-card">
             <h3>Lifestyle & Premium</h3>
             <p>Captures luxury consumption patterns. Premium retailers and exclusive clubs locate only in highly affluent catchments.</p>
             <div class="pillar-tags"><span>Premium Stores</span><span>Golf Courses</span></div>
           </div>
           <div class="pillar-card">
             <h3>Infrastructure & Scale</h3>
             <p>Evaluates the built environment catering to upper-middle and high-income households, including premium healthcare and early-adopter tech.</p>
             <div class="pillar-tags"><span>NABH Hospitals</span><span>EV Charging Points</span><span>Premium Schools</span><span>Commercial Establishments</span></div>
           </div>
        </div>
      </div>

      <div class="doc-section">
        <h2>The 11 Signals Deep Dive</h2>
        <div class="signal-masonry" id="signal-cards-container">
           <!-- Populated by JS on load -->
        </div>
      </div>
      
      <div class="doc-section">
        <h2>Agent Playbook</h2>
        <div class="playbook-grid">
          <div class="play-card">
            <h4>Play 1: The Cold Start</h4>
            <p>Opening a new territory? Don't guess. Sort by Affluence Score in the Explorer tab to instantly identify the top 5 micro-markets in any tier-2 city.</p>
          </div>
          <div class="play-card">
            <h4>Play 2: The Lookalike Strategy</h4>
            <p>Have a pincode that performs exceptionally well? Identify which pillars drive its wealth, and look for other pincodes with similar pillar signatures.</p>
          </div>
          <div class="play-card">
            <h4>Play 3: Prospecting Context</h4>
            <p>Before calling a high-value prospect, check their pincode's signals. Knowing they live in a hub of premium stores and corporate offices changes your pitch.</p>
          </div>
        </div>
      </div>
    </section>"""

start_marker = '<section class="view" id="view-about">'
end_marker = '</section>'
start_idx = html.find(start_marker)
if start_idx != -1:
    end_idx = html.find(end_marker, start_idx) + len(end_marker)
    html = html[:start_idx] + new_about_html + html[end_idx:]
    print("Methodology section replaced!")
else:
    print("Could not find methodology section!")

# 3. Add JS to populate the signal masonry on init
js_code = """
  // Populate methodology signals
  function initMethodologySignals() {
    const container = document.getElementById('signal-cards-container');
    if(!container || container.children.length > 0) return;
    
    const sigMap = {
      'MF Distributors': 'mf', 'Investment Advisors': 'ia', 'Corporate Hubs': 'ch', 'Retail Branches': 'rb',
      'Private:Public Bank Ratio': 'rr', 'Premium Stores': 'ps', 'Golf Courses': 'gc', 'NABH Hospitals': 'hc',
      'EV Charging Points': 'ev', 'Premium Schools': 'sch', 'Commercial Establishments': 'est'
    };
    
    let cardsHtml = '';
    for(const [label, key] of Object.entries(sigMap)) {
      const info = SIGNAL_INFO[key];
      if(info) {
        cardsHtml += `
          <div class="sig-card">
            <h4>${label}</h4>
            <div class="s-desc">${info.desc}</div>
            <div class="s-why">${info.why}</div>
          </div>
        `;
      }
    }
    container.innerHTML = cardsHtml;
  }
"""
init_call = "\n  initMethodologySignals();\n"

# insert js_code before const ROWS
rows_idx = html.find('const ROWS')
html = html[:rows_idx] + js_code + html[rows_idx:]

# call it inside renderTable(ROWS) or at the end of the script
end_script_idx = html.rfind('renderTable(ROWS);')
html = html[:end_script_idx] + init_call + html[end_script_idx:]

with open('/Users/tanishbansal/Projects/icici_bank_signals/dashboard_template.html','w',encoding='utf-8') as f:
    f.write(html)
print("Done injecting HTML & JS!")
