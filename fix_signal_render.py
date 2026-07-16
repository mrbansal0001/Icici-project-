with open('/Users/tanishbansal/Projects/icici_bank_signals/dashboard_template.html','r',encoding='utf-8') as f:
    html = f.read()

# ── 1. Replace the broken nested-template rawFields.map with a clean call ─
old_raw = (
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
new_raw = (
    '    <div class="raw-grid">\n'
    '      ${buildRawGrid(r, rawFields)}\n'
    '    </div>'
)
assert old_raw in html, "old_raw not found — checking template..."
html = html.replace(old_raw, new_raw, 1)

# ── 2. Add helper function (before SIGNAL_INFO const) ─────────────────────
helper_fn = """
function buildRawGrid(r, rawFields) {
  return rawFields.map(function(pair) {
    var label = pair[0], key = pair[1];
    var info = SIGNAL_INFO[key];
    var infoIcon = info ? '<span class="raw-info-icon">&#9432;</span>' : '';
    var expandDiv = info
      ? '<div class="raw-expand"><div class="sig-desc">' + info.desc + '</div><div class="sig-why">' + info.why + '</div></div>'
      : '';
    return '<div>'
      + '<div class="raw-item" onclick="this.nextElementSibling.classList.toggle(\'open\')">'
      + '<span class="rk">' + label + infoIcon + '</span>'
      + '<span class="rv num">' + r[key] + '</span>'
      + '</div>'
      + expandDiv
      + '</div>';
  }).join('');
}

"""

insert_before = 'const SIGNAL_INFO = {'
assert insert_before in html
html = html.replace(insert_before, helper_fn + insert_before, 1)

with open('/Users/tanishbansal/Projects/icici_bank_signals/dashboard_template.html','w',encoding='utf-8') as f:
    f.write(html)
print("Fixed. Size:", len(html)//1024, "KB")
