# ==========================================
# PART 4: pdf_renderer.py (UI & PDF GENERATION)
# ==========================================
from weasyprint import HTML
import time
from astro_data import ZODIAC_SIGNS, VEDIC_MANTRAS, VEDIC_UPAYAS

def get_sacred_svg_symbols():
    return """
    <g transform="translate(320, 200) scale(0.6)">
        <path d="M42.2,46.1c-2.4,0-5.7-0.9-8.4-3.1c-2.7-2.3-4.6-5.8-4.6-10.4c0-5.2,2.4-9.3,5.6-11.8 c3-2.3,6.8-3.4,9.6-3.4c5.8,0,10.6,2.8,13.2,7.3c0.9,1.6,1.4,3.3,1.4,5c0,3.6-2.1,6.8-5.3,8.5v0.2c4.1,1.1,7.2,4.8,7.2,9.3 c0,2.1-0.6,4.3-1.8,6.2c-2.9,4.8-8.6,8.2-15.5,8.2c-5.2,0-10.2-1.9-13.6-5c-2.8-2.5-4.5-6-4.5-9.6c0-2.2,0.6-4.4,1.8-6.1 c0.9-1.4,2.2-2.5,3.7-3.2l2.3,4.4c-0.9,0.5-1.5,1.2-2,2.1c-0.7,1.1-1.1,2.5-1.1,4c0,2.4,1.2,4.7,3.1,6.4c2.4,2.1,6.1,3.4,9.9,3.4 c5,0,9.3-2.4,11.3-5.8c0.8-1.3,1.2-2.8,1.2-4.3c0-3.1-2-5.9-5.1-7.2l-3.3-1.4v-4.8l2.9-1.1c2.6-1.1,4.4-3.5,4.4-6.3 c0-1.2-0.3-2.4-0.9-3.5c-1.8-3.2-5.4-5.2-9.7-5.2c-2.1,0-4.8,0.8-6.9,2.4c-2.2,1.7-3.8,4.5-3.8,8.2c0,3.1,1.2,5.5,3.1,7.1 c1.8,1.5,4,2.2,5.6,2.2l0.2,4.9H42.2z M80.5,23.3c-2.2-3.1-6-5.2-10.4-5.2c-5,0-9.2,2.4-11.4,5.9l4.2,2.6c1.5-2.2,4.2-3.8,7.4-3.8 c3,0,5.5,1.3,7,3.4L80.5,23.3z M71.6,12.7c-2.1,0-3.8-1.7-3.8-3.8s1.7-3.8,3.8-3.8s3.8,1.7,3.8,3.8S73.7,12.7,71.6,12.7z" fill="#B68A3A"/>
        <g transform="translate(100, 5)" stroke="#B68A3A" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 40,10 L 40,50 L 90,50" />
            <path d="M 10,50 L 60,50 L 60,90" />
            <path d="M 60,10 L 60,50" />
            <path d="M 40,50 L 40,90" />
            <circle cx="25" cy="25" r="2" fill="#B68A3A" stroke="none"/>
            <circle cx="75" cy="25" r="2" fill="#B68A3A" stroke="none"/>
            <circle cx="25" cy="75" r="2" fill="#B68A3A" stroke="none"/>
            <circle cx="75" cy="75" r="2" fill="#B68A3A" stroke="none"/>
        </g>
    </g>
    """

def generate_cover_page_svg(native_name="Confidential Dossier", birth_str=""):
    sacred_symbols = get_sacred_svg_symbols()
    return f"""
    <svg viewBox="0 0 800 1130" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: 100vh; font-family: 'Georgia', serif;">
        <rect width="800" height="1130" fill="#0b111a" />
        <rect x="40" y="40" width="720" height="1050" fill="none" stroke="#B68A3A" stroke-width="1" />
        <circle cx="400" cy="565" r="300" fill="none" stroke="#B68A3A" stroke-width="0.5" stroke-dasharray="4,8" opacity="0.4"/>
        
        {sacred_symbols}
        
        <text x="400" y="420" font-size="28" fill="#F5F0E6" text-anchor="middle" font-weight="300" letter-spacing="4">THE CELESTIAL STRATEGY</text>
        <text x="400" y="480" font-size="48" fill="#B68A3A" text-anchor="middle" font-weight="bold" letter-spacing="6">DOSSIER</text>
        
        <line x1="300" y1="520" x2="500" y2="520" stroke="#B68A3A" stroke-width="1"/>
        <text x="400" y="560" font-size="12" fill="#71866B" text-anchor="middle" letter-spacing="2" font-family="'Helvetica', sans-serif;">NATAL ARCHITECTURE • LIFE THEMES • TIMING MAP</text>
        
        <text x="400" y="800" font-size="12" fill="#F5F0E6" text-anchor="middle" letter-spacing="1" font-family="'Helvetica', sans-serif;">PREPARED FOR</text>
        <text x="400" y="830" font-size="18" fill="#B68A3A" text-anchor="middle" font-weight="bold" letter-spacing="2">{native_name}</text>
        <text x="400" y="860" font-size="12" fill="#71866B" text-anchor="middle" font-family="'Helvetica', sans-serif;">{birth_str}</text>
    </svg>
    """

def generate_rasi_chart_svg(planet_positions, asc_sign):
    width = 400; height = 400
    asc_idx = ZODIAC_SIGNS.index(asc_sign)
    h_coords = {
        1: (200, 100), 2: (100, 50), 3: (50, 100), 4: (100, 200),
        5: (50, 300), 6: (100, 350), 7: (200, 300), 8: (300, 350),
        9: (350, 300), 10: (300, 200), 11: (350, 100), 12: (300, 50)
    }
    house_planets = {i: [] for i in range(1, 13)}
    for p_name, data in planet_positions.items():
        p_sign_idx = ZODIAC_SIGNS.index(data["sign"])
        h_num = ((p_sign_idx - asc_idx + 12) % 12) + 1
        abbr = p_name.split("/")[0].strip()[:2]
        house_planets[h_num].append(abbr)
        
    svg = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; font-family: Helvetica, sans-serif;">',
        '<rect x="0" y="0" width="400" height="400" fill="#ffffff" stroke="#101827" stroke-width="1"/>',
        '<polygon points="200,0 400,200 200,400 0,200" fill="none" stroke="#101827" stroke-width="1"/>',
        '<line x1="0" y1="0" x2="400" y2="400" stroke="#101827" stroke-width="0.5"/>',
        '<line x1="400" y1="0" x2="0" y2="400" stroke="#101827" stroke-width="0.5"/>',
        '<line x1="0" y1="200" x2="400" y2="200" stroke="#101827" stroke-width="0.5"/>',
        '<line x1="200" y1="0" x2="200" y2="400" stroke="#101827" stroke-width="0.5"/>'
    ]
    for h_num, (x, y) in h_coords.items():
        sign_num = ((asc_idx + h_num - 1) % 12) + 1
        svg.append(f'<text x="{x}" y="{y-12}" font-size="10" fill="#71866B" text-anchor="middle">{sign_num}</text>')
        if house_planets[h_num]:
            svg.append(f'<text x="{x}" y="{y+8}" font-size="11" font-weight="bold" fill="#101827" text-anchor="middle">{", ".join(house_planets[h_num])}</text>')
    svg.append('</svg>')
    return "\n".join(svg)

def generate_sav_heatmap_svg(sav_dict):
    width = 600; height = 250; margin_top = 30; margin_bottom = 45
    chart_height = height - margin_top - margin_bottom; y_scale = chart_height / 50 
    baseline_y = height - margin_bottom - (28 * y_scale)
    
    svg_parts = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; font-family: sans-serif;">',
        '<rect width="100%" height="100%" fill="#ffffff" rx="4" stroke="#e0e0e0" stroke-width="1" />',
        f'<line x1="30" y1="{baseline_y:.2f}" x2="{width-30}" y2="{baseline_y:.2f}" stroke="#B68A3A" stroke-width="1.5" stroke-dasharray="4,4" />',
        f'<text x="{width-35}" y="{baseline_y-6:.2f}" font-size="9" fill="#B68A3A" text-anchor="end" font-weight="bold">Karmic Baseline (28)</text>'
    ]
    for i in range(1, 13):
        score = sav_dict.get(i, 0)
        bar_height = max(0, min(score, 50)) * y_scale
        x = 35 + ((i - 1) * 44); y = height - margin_bottom - bar_height
        color = "#71866B" if score >= 28 else "#A95D45"
        svg_parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="34" height="{bar_height:.2f}" fill="{color}" rx="2" ry="2" />')
        svg_parts.append(f'<text x="{x + 17:.2f}" y="{y - 5:.2f}" font-size="10" font-weight="bold" fill="#101827" text-anchor="middle">{score}</text>')
        svg_parts.append(f'<text x="{x + 17:.2f}" y="{height - margin_bottom + 18}" font-size="10" fill="#71866B" text-anchor="middle">H{i}</text>')
    svg_parts.append('</svg>')
    return "\n".join(svg_parts)

def build_infographic_module(data_dict, is_forecast=False):
    # Using specific classes that prevent page-break mangling
    if is_forecast:
        return f"""
        <div class="infographic-module">
            <div class="info-content">
                <h4 style="color:#71866B;">STRATEGIC WINDOWS</h4>
                {data_dict.get('strategic_windows', '')}
            </div>
            <div class="info-content">
                <h4 style="color:#A95D45;">STRUCTURAL THREATS</h4>
                {data_dict.get('structural_threats', '')}
            </div>
            <div class="info-pivot">
                <h4 style="color:#F5F0E6;">EXECUTIVE SUMMARY</h4>
                {data_dict.get('executive_summary', '')}
            </div>
        </div>"""
    else:
        return f"""
        <div class="infographic-module">
            <div class="info-content">
                <h4 style="color:#71866B;">STRATEGIC ASSET</h4>
                {data_dict.get('asset', '')}
            </div>
            <div class="info-content">
                <h4 style="color:#A95D45;">STRUCTURAL VULNERABILITY</h4>
                {data_dict.get('vulnerability', '')}
            </div>
            <div class="info-pivot">
                <h4 style="color:#F5F0E6;">EXECUTIVE PIVOT</h4>
                {data_dict.get('executive_pivot', '')}
            </div>
        </div>"""

def build_and_render_pdf(session_data, eng_data, timeline_data, pdf_path):
    cover_svg = generate_cover_page_svg(native_name="Confidential Profile", birth_str=session_data.get("birth_str", ""))
    rasi_svg = generate_rasi_chart_svg(session_data['planet_data'], session_data['asc_sign'])
    sav_svg = generate_sav_heatmap_svg(session_data['sav'])
    
    # We load the sacred symbols into a specific running element to prevent layout collision
    sacred_header = f'<div class="sacred-header"><svg height="40" width="120" viewBox="0 0 160 40">{get_sacred_svg_symbols()}</svg></div>'

    eph_rows = ""
    for p_name, data in session_data['planet_data'].items():
        deg = f"{int(data['lon'] % 30)}° {int((data['lon'] % 1) * 60)}'"
        cond = [data['dignity'].split('/')[0].strip()] if data['dignity'] != "Neutral" else []
        if data.get('combust'): cond.append("Combust")
        eph_rows += f"<tr><td><strong>{p_name}</strong></td><td>{data['sign']}</td><td>{deg}</td><td>{data['nak']}</td><td>{','.join(cond) or 'Neutral'}</td></tr>"
    
    dasha_rows = "".join([f"<tr><td><strong>{r[0]}</strong></td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>" for r in timeline_data])
    
    mantra_rows = ""
    targets = set([{"Aries": "Mars / Mangal", "Taurus": "Venus / Shukra", "Gemini": "Mercury / Budh", "Cancer": "Moon / Chandra", "Leo": "Sun / Surya", "Virgo": "Mercury / Budh", "Libra": "Venus / Shukra", "Scorpio": "Mars / Mangal", "Sagittarius": "Jupiter / Guru", "Capricorn": "Saturn / Shani", "Aquarius": "Saturn / Shani", "Pisces": "Jupiter / Guru"}.get(session_data['asc_sign'])])
    for p, d in session_data['planet_data'].items():
        if d.get('combust') or d.get('dignity', '').startswith('Debilitated') or 'Rahu' in p or 'Ketu' in p: targets.add(p)
    for p in [t for t in targets if t and t in VEDIC_MANTRAS]:
        mantra_rows += f"<tr><td><strong>{p}</strong></td><td><em>{VEDIC_MANTRAS[p]}</em></td><td>{VEDIC_UPAYAS[p]}</td></tr>"

    lk_rows = ""
    for r in session_data.get('remedies', []):
        parts = r.split(':')
        if len(parts) == 2: lk_rows += f"<tr><td><strong>{parts[0].strip()}</strong></td><td>{parts[1].strip()}</td><td style='text-align:center;'><div class='checkbox'></div></td></tr>"
    if not lk_rows: lk_rows = '<tr><td colspan="3">No major structural Lal Kitab afflictions detected.</td></tr>'

    html_body = f"""
    <div class="cover-page">{cover_svg}</div>
    {sacred_header}
    
    <div class="content">
        <h2 class="section-title">01 — The Planetary Matrix</h2>
        <div class="grid-2col">
            <div class="chart-box" style="margin-top: 10px;">{rasi_svg}</div>
            <div class="chart-box" style="margin-top: 10px;">
                <table class="data-table" style="margin-top:0;"><tr><th>Planet / Graha</th><th>Sign</th><th>Degree</th><th>Nakshatra</th><th>Condition</th></tr>{eph_rows}</table>
            </div>
        </div>
        <div class="synopsis"><strong>Curator's Note:</strong> The D-1 chart (left) is the geometric snapshot of the heavens. Numbers represent Zodiac Signs (1=Aries).</div>

        <div class="page-break"></div>
        <h2 class="section-title">02 — Inner Operating System</h2>
        {build_infographic_module(eng_data.get('psychology', {}))}

        <div class="page-break"></div>
        <h2 class="section-title">03 — Career & Wealth Canvas</h2>
        {build_infographic_module(eng_data.get('career_wealth', {}))}
        
        <h3 class="sub-title" style="margin-top: 30px;">Sarvashtakavarga (SAV) Karmic Heatmap</h3>
        <div class="sav-box">{sav_svg}</div>
        <div class="synopsis"><strong>Curator's Note:</strong> Houses scoring above 28 can absorb and manifest positive transit energies. Below 28 indicates structural reinforcement is required.</div>

        <div class="page-break"></div>
        <h2 class="section-title">04 — Relational Dynamics</h2>
        {build_infographic_module(eng_data.get('relational_karma', {}))}

        <div class="page-break"></div>
        <h2 class="section-title">05 — Tactical Forecast</h2>
        <h3 class="sub-title">Vimshottari Timeline</h3>
        <table class="data-table"><tr><th>Phase</th><th>Ruling Lords</th><th>Start Date</th><th>End Date</th></tr>{dasha_rows}</table>
        <div style="margin-top:20px;">{build_infographic_module(eng_data.get('forecast', {}), is_forecast=True)}</div>

        <div class="page-break"></div>
        <h2 class="section-title">06 — Ayurvedic & Vitality Reflection</h2>
        <div style="margin-top:20px;">{build_infographic_module(eng_data.get('ayurvedic_audit', {}))}</div>

        <div class="page-break"></div>
        <h2 class="section-title">07 — Holistic Remediation Planner</h2>
        <h3 class="sub-title">I. Vedic Mantras & Spiritual Upayas</h3>
        <table class="data-table"><tr><th>Afflicted / Key Planet</th><th>Vedic Beej Mantra (Chant 108x)</th><th>Traditional Spiritual Upaya</th></tr>{mantra_rows}</table>
        
        <h3 class="sub-title" style="margin-top: 30px;">II. Lal Kitab Behavioral Protocols</h3>
        <table class="data-table"><tr><th>Karmic Friction</th><th>Lal Kitab Behavioral Protocol</th><th style="width: 50px; text-align:center;">Done</th></tr>{lk_rows}</table>
    </div>
    """

    css = """
    @page { 
        size: letter; 
        margin: 2.54cm; 
        margin-top: 3.5cm;
        @top-center { content: element(sacred-header); }
        @bottom-right { content: counter(page); font-family: 'Helvetica', sans-serif; font-size: 9pt; color: #71866B; }
    }
    
    body { font-family: 'Helvetica', 'Arial', sans-serif; font-size: 10pt; line-height: 1.5; color: #101827; margin: 0; padding: 0; }
    
    .cover-page { height: 100vh; margin-top: -3.5cm; }
    
    /* Native WeasyPrint Running Header (Prevents Overlap) */
    .sacred-header { position: running(sacred-header); text-align: center; }
    
    .page-break { page-break-before: always; }
    
    h1, h2.section-title { font-family: 'Georgia', serif; color: #101827; font-size: 18pt; text-transform: uppercase; letter-spacing: 2px; border-bottom: 1px solid #B68A3A; padding-bottom: 5px; margin-bottom: 20px; }
    h3.sub-title { font-family: 'Georgia', serif; color: #B68A3A; font-size: 13pt; text-transform: uppercase; letter-spacing: 1px; margin-top: 15px; margin-bottom: 10px; }
    
    /* Floating layout for D1 / Ephemeris to prevent flexbox glitches */
    .grid-2col { display: block; width: 100%; clear: both; overflow: hidden; margin-bottom: 20px; }
    .grid-2col > div { float: left; width: 48%; box-sizing: border-box; }
    .grid-2col > div:last-child { float: right; }
    
    /* ENHANCED INFOGRAPHIC CSS - Explicit block layout to prevent text mangling */
    .infographic-module { display: block; margin-bottom: 20px; page-break-inside: avoid; }
    .info-content { display: block; background: #ffffff; padding: 15px; border-left: 3px solid #101827; border-bottom: 1px solid #f0f0f0; margin-bottom: 10px; }
    .info-pivot { display: block; background: #0b111a; color: #F5F0E6; padding: 15px; border-left: 3px solid #B68A3A; }
    .info-content h4, .info-pivot h4 { margin: 0 0 10px 0; font-family: 'Helvetica', sans-serif; font-size: 10pt; letter-spacing: 1px; }
    .info-content ul, .info-pivot ul { margin: 0; padding-left: 20px; }
    .info-content li, .info-pivot li { margin-bottom: 6px; }
    
    .synopsis { font-size: 9pt; color: #58708C; background: #fdfbf7; padding: 10px; border-left: 3px solid #B68A3A; margin-top: 15px; margin-bottom: 20px; font-style: italic; clear: both; }
    
    table.data-table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 9pt; }
    table.data-table th { background-color: #0b111a; color: #B68A3A; padding: 8px; text-align: left; text-transform: uppercase; letter-spacing: 1px; }
    table.data-table td { padding: 8px; border-bottom: 1px solid #e0e0e0; vertical-align: middle; }
    table.data-table tr:nth-child(even) { background-color: #fdfbf7; }
    .checkbox { width:12px; height:12px; border:1px solid #101827; margin:auto;}
    
    .chart-box { text-align: center; }
    .sav-box { text-align: center; margin-bottom: 10px; }
    """
    try:
        HTML(string=f"<html><head><style>{css}</style></head><body>{html_body}</body></html>").write_pdf(pdf_path)
        return True
    except Exception as e:
        print(f"PDF ERROR: {e}")
        return False
