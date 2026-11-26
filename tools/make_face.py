"""Rain Comb watch face generator: writes res/raw/watchface.xml and res/values/strings.xml.

Usage: .venv/bin/python tools/make_face.py proj
Env:   RC_SHIFT=<hours>  test only: layout conditions behave as if it were N hours later
                         (the clock itself still shows the real time).

WFF v2 cannot read list settings inside expressions, so each setting-dependent part is wrapped in a
<ListConfiguration> with one variant per option (per()).
"""
import math, os, sys
from xml.sax.saxutils import escape, quoteattr
from PIL import ImageFont

PROJ = sys.argv[1]
RES = os.path.join(PROJ, 'res')
C = 225
SHIFT = int(os.environ.get('RC_SHIFT', '0'))
INTER = ImageFont.truetype(os.path.join(RES, 'font/inter_medium.ttf'), 100)
OUTFIT = ImageFont.truetype(os.path.join(RES, 'font/outfit_light.ttf'), 100)
FT, FD = 'inter_medium', 'outfit_light'
RED, AMBER, GREEN = '#ffff5a4e', '#ffffb44d', '#ff8fd67c'
ACC, NEU, TINT, FULL, HAND = ('[CONFIGURATION.theme4.%d]' % i for i in range(5))

# type scale (watch pixels)
S_TOP, S_TIME, S_ROW, S_LAB_H, S_LAB_T, S_TOM, S_AOD = 24, 118, 23, 15, 18, 21, 19

HOUR = '(([HOUR_0_23] + %d) %% 24)' % SHIFT if SHIFT else '[HOUR_0_23]'


def tw(s, size, font=INTER):
    return font.getlength(s) * size / 100


# ---------------------------------------------------------------- settings
PRESETS = [
    ('ocean', 'Ocean', 'shade', '#06141f', '#79c3e6'),
    ('midnight', 'Midnight + Champagne', 'pair', '#0b1020', '#e6cf9c'),
    ('graphite', 'Graphite + Copper', 'pair', '#131313', '#d4875a'),
    ('navy', 'Navy + Ivory', 'pair', '#0a1528', '#efe7d4'),
    ('forest', 'Forest + Brass', 'pair', '#0b1711', '#c8a457'),
    ('signal', 'Black + Signal', 'pair', '#060606', '#ff7a1f'),
    ('slate', 'Slate', 'shade', '#10161d', '#a3b6ca'),
    ('ember', 'Ember', 'shade', '#1a0907', '#ff8b6a'),
    ('sage', 'Sage', 'shade', '#0c140f', '#a9c8a0'),
    ('mono', 'Mono', 'shade', '#0b0b0b', '#cfcfcf'),
]

DEFAULT_THEME = 'sage'  # update test: should arrive on the watch via a GitHub release


def mix(a, b, t):
    A = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    B = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join('%02x' % round(x + (y - x) * t) for x, y in zip(A, B))


def theme_colors(g, dial, acc):
    neutral = mix(acc, '#ffffff', .55) if g == 'shade' else mix('#f1eee8', acc, .12)
    hand = mix(neutral, '#000000', .18)
    return ['#ff' + c[1:] for c in (acc, neutral, dial, mix(dial, acc, .24), hand)]


PCT = '％'  # full-width percent sign: a plain % in a label crashes the watch's string formatter
LISTS = {  # id: (label, default option, [(option id, label)])
    'dial2': ('Dial', '0', [('0', 'Black (best battery)'), ('1', 'Dark tint'), ('2', 'Full color')]),
    'mend': ('Morning ends', '11', [(str(h), '%d AM' % h if h < 12 else '12 PM') for h in (8, 9, 10, 11, 12)]),
    'eve23': ('Evening starts', '19', [(str(h), '%d PM' % (h - 12)) for h in (17, 18, 19, 20, 21, 22, 23)]),
    'uvt': ('UV alert at', '5', [(u, 'UV ' + u) for u in ('3', '5', '6', '8')]),
    'rth': ('Rain alert at', '35', [(r, r + PCT) for r in ('25', '35', '50', '70')]),
    'blow': ('Low battery at', '15', [(b, b + PCT) for b in ('10', '15', '20', '25')]),
    'clock': ('Clock', '12', [('12', '12-hour (AM/PM)'), ('24', '24-hour')]),
    'tunit': ('Temperature', 'w', [('w', 'Follow watch'), ('c', 'Celsius'), ('f', 'Fahrenheit')]),
}
STRINGS = {'app_name': 'Rain Comb', 'cfg_theme': 'Color pair', 'cfg_event': 'Next event',
           'cfg_energy': 'Energy score', 'cfg_sleep': 'Sleep'}


def user_configurations():
    default = [p[0] for p in PRESETS].index(DEFAULT_THEME)
    out = ['<UserConfigurations>', '<ColorConfiguration id="theme4" displayName="cfg_theme" defaultValue="%d">' % default]
    for i, (pid, name, g, dial, acc) in enumerate(PRESETS):
        STRINGS['theme_' + pid] = name
        out.append('<ColorOption id="%d" displayName="theme_%s" colors="%s"/>' % (i, pid, ' '.join(theme_colors(g, dial, acc))))
    out.append('</ColorConfiguration>')
    for lid, (label, default, opts_) in LISTS.items():
        STRINGS['cfg_' + lid] = label
        out.append('<ListConfiguration id="%s" displayName="cfg_%s" defaultValue="%s">' % (lid, lid, default))
        for oid, olabel in opts_:
            STRINGS['opt_%s_%s' % (lid, oid)] = olabel
            out.append('<ListOption id="%s" displayName="opt_%s_%s"/>' % (oid, lid, oid))
        out.append('</ListConfiguration>')
    out.append('</UserConfigurations>')
    return '\n'.join(out)


def opts(lid):
    return [o for o, _ in LISTS[lid][2]]


def box(content):
    return '<Group name="b" x="0" y="0" width="450" height="450">%s</Group>' % content


def per(lid, fn):
    body = ''.join('<ListOption id="%s">%s</ListOption>' % (o, box(fn(o))) for o in opts(lid))
    return '<ListConfiguration id="%s">%s</ListConfiguration>' % (lid, body)


# ---------------------------------------------------------------- primitives
_n = [0]


def cond(cases, default=''):
    """cases: [(expression, content)]; first match wins."""
    names = []
    for _ in cases:
        _n[0] += 1
        names.append('c%d' % _n[0])
    ex = ''.join('<Expression name="%s"><![CDATA[%s]]></Expression>' % (n, e) for n, (e, _) in zip(names, cases))
    cmp_ = ''.join('<Compare expression="%s">%s</Compare>' % (n, box(c)) for n, (_, c) in zip(names, cases))
    dflt = '<Default>%s</Default>' % box(default) if default else ''
    return '<Condition><Expressions>%s</Expressions>%s%s</Condition>' % (ex, cmp_, dflt)


def text(x, y, w, h, template, params=(), size=S_ROW, color=None, align='CENTER', alpha=None, font=FT, spacing=None, ellipsis=False):
    color = color or NEU
    if not params:
        template, params = '%s', ['"%s"' % template]
    a = '' if alpha is None else ' alpha="%d"' % alpha
    sp = '' if spacing is None else ' letterSpacing="%s"' % spacing
    el = ' ellipsis="TRUE" maxLines="1"' if ellipsis else ''
    ps = ''.join('<Parameter expression=%s/>' % quoteattr(p) for p in params)
    return ('<PartText x="%d" y="%d" width="%d" height="%d"%s><Text align="%s"%s><Font family="%s" size="%s" color="%s"%s>'
            '<Template><![CDATA[%s]]>%s</Template></Font></Text></PartText>') % (int(x), int(y), int(w), int(h), a, align, el, font, size, color, sp, template, ps)


def icon_font(x, y, s, expr, night_expr=None, tint=None, alpha=None):
    """Weather icon via one bitmap font: codes 0-15 day icons, 16-31 night icons."""
    a = '' if alpha is None else ' alpha="%d"' % alpha
    idx = '((%s) <= 15 ? (%s) : 0)' % (expr, expr)
    if night_expr is not None:
        idx = '(%s + ((%s) ? 0 : 16))' % (idx, night_expr)
    return ('<PartText x="%d" y="%d" width="%d" height="%d" tintColor="%s"%s><Text><BitmapFont family="wx" size="%d">'
            '<Template><![CDATA[%%s]]><Parameter expression=%s/></Template></BitmapFont></Text></PartText>') % (
        int(x), int(y), s, s, tint or ACC, a, s, quoteattr(idx))


def image(x, y, s, res, tint=None, alpha=None):
    a = '' if alpha is None else ' alpha="%d"' % alpha
    return '<PartImage x="%d" y="%d" width="%d" height="%d" tintColor="%s"%s><Image resource="%s"/></PartImage>' % (
        int(x), int(y), s, s, tint or ACC, a, res)


def draw(inner, alpha=None, extra=''):
    a = '' if alpha is None else ' alpha="%d"' % alpha
    return '<PartDraw x="0" y="0" width="450" height="450"%s>%s%s</PartDraw>' % (a, extra, inner)


def stroke(color, w, cap='ROUND'):
    return '<Stroke color="%s" thickness="%s" cap="%s"/>' % (color, w, cap)


def line(x1, y1, x2, y2, color, w, alpha=None, extra=''):
    return draw('<Line startX="%.1f" startY="%.1f" endX="%.1f" endY="%.1f">%s</Line>' % (x1, y1, x2, y2, stroke(color, w)), alpha, extra)


def dot(x, y, r, color, alpha=None):
    return draw('<Ellipse x="%.1f" y="%.1f" width="%.1f" height="%.1f"><Fill color="%s"/></Ellipse>' % (x - r, y - r, 2 * r, 2 * r, color), alpha)


def rect(x, y, w, h, color):
    return draw('<Rectangle x="%d" y="%d" width="%d" height="%d"><Fill color="%s"/></Rectangle>' % (x, y, w, h, color))


def group(name, content, variant=None):
    v = '' if variant is None else '<Variant mode="AMBIENT" target="alpha" value="%d"/>' % variant
    return '<Group name="%s" x="0" y="0" width="450" height="450">%s%s</Group>' % (name, v, content)


# ---------------------------------------------------------------- expressions
DAYS = '"SUNMONTUEWEDTHUFRISAT"'
MONTHS = '"JANFEBMARAPRMAYJUNJULAUGSEPOCTNOVDEC"'
DOW = 'subText(%s, ([DAY_OF_WEEK] - 1) * 3, ([DAY_OF_WEEK] - 1) * 3 + 3)' % DAYS
DOW_TOMORROW = 'subText(%s, ([DAY_OF_WEEK] %% 7) * 3, ([DAY_OF_WEEK] %% 7) * 3 + 3)' % DAYS
MON = 'subText(%s, ([MONTH] - 1) * 3, ([MONTH] - 1) * 3 + 3)' % MONTHS
RAINY = lambda c: '(%s == 4 || %s == 6 || %s == 9 || %s == 10 || %s == 12)' % (c, c, c, c, c)
HEAVY = lambda c: '(%s == 4 || %s == 9)' % (c, c)
MED = lambda c: '(%s == 6 || %s == 10)' % (c, c)
LIGHT = lambda c: '(%s == 12)' % c
WX_OK = '[WEATHER.IS_AVAILABLE]'
H_OK = lambda k: '[WEATHER.HOURS.%d.IS_AVAILABLE]' % k
UV_NOW = '[WEATHER.HOURS.1.UV_INDEX]'  # WFF v2 has no reliable current-UV source; next hour stands in
TODAY_RAIN = '(%s < 18 ? [WEATHER.DAYS.0.CHANCE_OF_PRECIPITATION] : [WEATHER.DAYS.0.CHANCE_OF_PRECIPITATION_NIGHT])' % HOUR


def hour_label(k, clk):
    h = '((%s + %s) %% 24)' % (HOUR, k)
    if clk == '24':
        return '%s', [h]
    return '%s%s', ['(%s %% 12 == 0 ? 12 : %s %% 12)' % (h, h), '(%s < 12 ? "a" : "p")' % h]


def temp(expr, unit):
    if unit == 'c':
        return '([WEATHER.TEMPERATURE_UNIT] == 2 ? round(((%s) - 32) * 5 / 9) : (%s))' % (expr, expr)
    if unit == 'f':
        return '([WEATHER.TEMPERATURE_UNIT] == 1 ? round((%s) * 9 / 5 + 32) : (%s))' % (expr, expr)
    return '(%s)' % expr


def temp_text(x, y, w, h, expr, size, align='START', alpha=None):
    return per('tunit', lambda u: text(x, y, w, h, '%s°', [temp(expr, u)], size, None, align, alpha))


# ---------------------------------------------------------------- main screen
def dial_color(o):
    return '#ff000000' if o == '0' else (TINT if o == '1' else FULL)


def background():
    return per('dial2', lambda o: rect(0, 0, 450, 450, dial_color(o)))


def battery_ring():
    r = 214

    def arc(color, alpha):
        return draw('<Arc centerX="225" centerY="225" width="%d" height="%d" startAngle="-180" endAngle="180">%s'
                    '<Transform target="startAngle" value="-1.8 * [BATTERY_PERCENT]"/>'
                    '<Transform target="endAngle" value="1.8 * [BATTERY_PERCENT]"/></Arc>' % (2 * r, 2 * r, stroke(color, 4)), alpha)
    track = draw('<Ellipse x="%d" y="%d" width="%d" height="%d">%s</Ellipse>' % (C - r, C - r, 2 * r, 2 * r, stroke(ACC, 4)), 15)
    return track + per('blow', lambda b: cond([
        ('[BATTERY_PERCENT] <= %s && ![BATTERY_CHARGING_STATUS]' % b, arc(RED, 230)),
        ('[BATTERY_CHARGING_STATUS]', arc(GREEN, 140)),
    ], arc(ACC, 77)))


def runs_text(y, h, runs, align='CENTER'):
    """One centred line mixing text and icon runs, so nothing can overlap whatever the values."""
    body = ''
    for r in runs:
        kind, tmpl, params, color, size = r
        if kind != 'icon' and not params:
            tmpl, params = '%s', ['"%s"' % tmpl]
        ps = ''.join('<Parameter expression=%s/>' % quoteattr(p) for p in params)
        if kind == 'icon':
            body += '<BitmapFont family="wx" size="%d" color="%s"><Template><![CDATA[%%s]]>%s</Template></BitmapFont>' % (size, color, ps)
        else:
            body += '<Font family="%s" size="%d" color="%s"><Template><![CDATA[%s]]>%s</Template></Font>' % (FT, size, color, tmpl, ps)
    return '<PartText x="0" y="%d" width="450" height="%d"><Text align="%s">%s</Text></PartText>' % (y, h, align, body)


def top_line():
    """Row 1: date. Row 2: sky icon, temperature, then one item: rain soon > UV alert > today's rain > UV."""
    S = S_TOP
    IS = round(S * 1.2)
    date = text(0, 50, 450, 30, '%s %s', [DOW, '[DAY]'], 21, NEU, 'CENTER', 190, spacing='0.12')
    sky_idx = '(([WEATHER.CONDITION] <= 15 ? [WEATHER.CONDITION] : 0) + ([WEATHER.IS_DAY] ? 0 : 16))'
    sep = ('t', '  ·  ', [], NEU, S)
    rain_ic = ('icon', '', ['32'], ACC, IS - 2)

    def line(tail, u='w'):
        runs = [('icon', '', [sky_idx], ACC, IS), ('t', ' %s°', [temp('[WEATHER.TEMPERATURE]', u)], NEU, S)] + (([sep] + tail) if tail else [])
        return runs_text(82, 34, runs)

    def per_unit(tail_fn):
        return per('tunit', lambda u: line(tail_fn(), u))

    def with_hour(prefix_runs, k, color):
        """tail = prefix runs + 'hour k from now' (12/24h aware)."""
        return per('clock', lambda c: per('tunit', lambda u: line(prefix_runs + [('t', hour_label(k, c)[0], hour_label(k, c)[1], color, S)], u)))

    def after_uv(r):
        return cond([
            (WX_OK + ' && %s >= %s' % (TODAY_RAIN, r), per_unit(lambda: [rain_ic, ('t', ' %s%%', [TODAY_RAIN], NEU, S)])),
            (H_OK(1) + ' && %s >= 3' % UV_NOW, per_unit(lambda: [('t', 'UV %s', [UV_NOW], NEU, S)])),
        ], per_unit(lambda: []))

    def uv_chain(u):
        hit = lambda k: '(%s && [WEATHER.HOURS.%d.UV_INDEX] >= %s)' % (H_OK(k), k, u)
        first = '(%s ? 2 : 3)' % hit(2)
        val = '(%s ? [WEATHER.HOURS.2.UV_INDEX] : [WEATHER.HOURS.3.UV_INDEX])' % hit(2)
        return cond([
            (hit(1), per_unit(lambda: [('t', 'UV %s', [UV_NOW], AMBER, S)])),
            ('%s || %s' % (hit(2), hit(3)), with_hour([('t', 'UV %s ', [val], AMBER, S)], first, AMBER)),
        ], per('rth', after_uv))

    r1 = '(%s && %s)' % (H_OK(1), RAINY('[WEATHER.HOURS.1.CONDITION]'))
    r2 = '(%s && %s)' % (H_OK(2), RAINY('[WEATHER.HOURS.2.CONDITION]'))
    weather = cond([
        (WX_OK + ' && ' + RAINY('[WEATHER.CONDITION]'), per_unit(lambda: [rain_ic, ('t', ' now', [], NEU, S)])),
        ('%s || %s' % (r1, r2), with_hour([rain_ic, ('t', ' ', [], NEU, S)], '(%s ? 1 : 2)' % r1, NEU)),
    ], per('uvt', uv_chain))
    return date + cond([(WX_OK, weather)])


def time_block():
    """Hours in accent, minutes in neutral; the colon is placed so the whole time is centred."""
    Y, S = 104, S_TIME
    H = round(S * 1.1)
    wc = round(tw(':', S, OUTFIT) * 1.1)
    w2, w1, wm = tw('10', S, OUTFIT), tw('8', S, OUTFIT), tw('08', S, OUTFIT)

    def colon_x(wh):
        return round(C - (wh + wc + wm) / 2 + wh)

    # Plain text, not <DigitalClock>: the always-on renderer keeps at most 2 clock elements,
    # and the analog clock must be the one it keeps.
    def clock(hour_src, cx):
        hours = text(cx - 260, Y, 260, H, '%s', [hour_src], S, ACC, 'END', font=FD)
        minutes = text(cx + wc, Y, 260, H, '%s', ['[MINUTE_Z]'], S, NEU, 'START', font=FD)
        colon = text(cx, Y - 6, wc, H, ':', [], S, NEU, 'CENTER', 115, FD)
        return hours + minutes + colon

    return per('clock', lambda c: clock('[HOUR_0_23_Z]', colon_x(w2)) if c == '24' else
               cond([('[HOUR_1_12] < 10', clock('[HOUR_1_12]', colon_x(w1)))], clock('[HOUR_1_12]', colon_x(w2))))


EV_Y = 252
HR_Y = 300
ROW_IC = 25
HR_EXPR = '([HEART_RATE] != null ? [HEART_RATE] : "--")'


def item(cx, y, res, tmpl, params, sample):
    w = ROW_IC + 7 + tw(sample, S_ROW)
    x = cx - w / 2
    return image(x, y - ROW_IC / 2, ROW_IC, res, ACC, 217) + text(x + ROW_IC + 7, y - 17, 110, 34, tmpl, params, S_ROW, NEU, 'START', 189)


def health_row():
    """Mirrored around the centre line. Left: sleep (morning, via the sleep slot) or steps. Right: heart rate."""
    g = 14
    steps = (text(C - g - ROW_IC - 7 - 130, HR_Y - 17, 130, 34, '%s', ['numberFormat("#,##0", [STEP_COUNT])'], S_ROW, NEU, 'END', 189)
             + image(C - g - ROW_IC, HR_Y - ROW_IC / 2, ROW_IC, 'ic_steps', ACC, 217))
    right = (draw('<Line startX="225" startY="%d" endX="225" endY="%d">%s</Line>' % (HR_Y - 9, HR_Y + 9, stroke(NEU, 1.5)), 60)
             + image(C + g, HR_Y - ROW_IC / 2, ROW_IC, 'ic_heart', ACC, 217)
             + text(C + g + ROW_IC + 7, HR_Y - 17, 130, 34, '%s', [HR_EXPR], S_ROW, NEU, 'START', 189))
    return right + per('mend', lambda m: cond([('%s >= %s' % (HOUR, m), steps)]))


def event_slot():
    w, h = 350, 44
    pill = ('<PartDraw x="0" y="0" width="%d" height="%d" alpha="16"><RoundRectangle x="0" y="0" width="%d" height="%d" '
            'cornerRadiusX="22" cornerRadiusY="22"><Fill color="%s"/></RoundRectangle></PartDraw>') % (w, h, w, h, ACC)

    # A real event is drawn at middle strength (about 60%): readable, but quieter than the time and health row.
    def body(tmpl, params):
        return pill + image(16, (h - 24) / 2, 24, 'ic_cal', ACC, 165) + text(48, 4, w - 64, h - 8, tmpl, params, S_ROW, NEU, 'START', 165, ellipsis=True)
    # With no events the row is faint (about 30%): no pill, small dim text.
    tw_ = tw('No upcoming events', S_ROW - 2)
    xi = (w - (20 + 8 + tw_)) / 2
    faint = (image(xi, (h - 20) / 2, 20, 'ic_cal', NEU, 70)
             + text(xi + 28, 4, w - xi - 28, h - 8, '%s', ['[COMPLICATION.TEXT]'], S_ROW - 2, NEU, 'START', 80, ellipsis=True))
    # Samsung's calendar sends events as text only (no title), so "no events" is recognised by its wording.
    # If the watch can't evaluate this, the row falls back to the faint look, as before.
    no_events = 'subText([COMPLICATION.TEXT], 0, 11) == "No upcoming"'
    long_ = cond([('[COMPLICATION.TITLE] != null', body('%s  %s', ['[COMPLICATION.TITLE]', '[COMPLICATION.TEXT]'])),
                  ('!(%s)' % no_events, body('%s', ['[COMPLICATION.TEXT]']))], faint)
    return ('<ComplicationSlot slotId="0" name="next_event" displayName="cfg_event" x="%d" y="%d" width="%d" height="%d" '
            'supportedTypes="LONG_TEXT SHORT_TEXT EMPTY" isCustomizable="FALSE"><Variant mode="AMBIENT" target="alpha" value="0"/>'
            '<DefaultProviderPolicy defaultSystemProvider="NEXT_EVENT" defaultSystemProviderType="LONG_TEXT"/>'
            '<BoundingBox x="0" y="0" width="%d" height="%d"/>'
            '<Complication type="LONG_TEXT">%s</Complication><Complication type="SHORT_TEXT">%s</Complication>'
            '<Complication type="EMPTY"></Complication></ComplicationSlot>') % (
        C - w // 2, EV_Y - h // 2, w, h, w, h, long_, long_)


SLEEP = 'com.samsung.android.wear.shealth/com.samsung.android.wear.shealth.complications.sleep.SleepComplicationProviderService'


def sleep_slot():
    """Last night's sleep from Samsung Health (locked), left half of the health row, mornings only."""
    g, sw, sh = 14, 190, 40
    x0 = C - g - sw

    def shown(src):
        content = (text(0, 3, sw - ROW_IC - 7, 34, '%s', [src], S_ROW, NEU, 'END', 189)
                   + image(sw - ROW_IC, (sh - ROW_IC) / 2, ROW_IC, 'ic_sleep', ACC, 217))
        return box(per('mend', lambda m: cond([('%s < %s' % (HOUR, m), content)])))
    return ('<ComplicationSlot slotId="2" name="sleep" displayName="cfg_sleep" x="%d" y="%d" width="%d" height="%d" '
            'supportedTypes="LONG_TEXT SHORT_TEXT EMPTY" isCustomizable="FALSE"><Variant mode="AMBIENT" target="alpha" value="0"/>'
            '<DefaultProviderPolicy defaultSystemProvider="EMPTY" defaultSystemProviderType="EMPTY" '
            'primaryProvider="%s" primaryProviderType="LONG_TEXT"/>'
            '<BoundingBox x="0" y="0" width="%d" height="%d"/>'
            '<Complication type="LONG_TEXT">%s</Complication>'
            '<Complication type="SHORT_TEXT">%s</Complication>'
            '<Complication type="EMPTY"></Complication></ComplicationSlot>') % (
        x0, HR_Y - sh // 2, sw, sh, SLEEP, sw, sh, shown('[COMPLICATION.TEXT]'), shown('[COMPLICATION.TEXT]'))


RB = 186
TH0 = math.degrees(math.asin(110 / RB))


def comb():
    out, overlay = '', {u: '' for u in opts('uvt')}
    for i in range(9):
        th = math.radians((180 - TH0) - (180 - 2 * TH0) * i / 8)
        c, s = math.cos(th), math.sin(th)
        p = lambda r: (C + c * r, C + s * r)
        cnd = '[WEATHER.CONDITION]' if i == 0 else '[WEATHER.HOURS.%d.CONDITION]' % i
        uv = UV_NOW if i == 0 else '[WEATHER.HOURS.%d.UV_INDEX]' % i
        ok = WX_OK if i == 0 else H_OK(i)
        bar = lambda ln, a: line(*p(RB), *p(RB + ln), ACC, 7, a)
        d = p(RB + 2)
        out += cond([
            ('!' + ok, dot(*d, 2.4, NEU, 77)),
            (HEAVY(cnd), bar(19, 255)),
            (MED(cnd), bar(12, 255)),
            (LIGHT(cnd), bar(6, 128)),
            ('%s >= 3' % uv, dot(*d, 3.2, AMBER, 190)),
        ], dot(*d, 2.4, NEU, 77))
        for u in overlay:
            overlay[u] += cond([('%s && !%s && %s >= %s' % (ok, RAINY(cnd), uv, u), dot(*d, 4, AMBER))])
    return out + per('uvt', lambda u: overlay[u])


def comb_labels():
    out = ''
    for i, dx in ((0, -78), (4, 0), (8, 78)):
        cx = C + dx
        y1, y2 = C + 114, C + 138
        if i == 0:
            out += text(cx - 40, y1 - 11, 80, 22, 'now', [], S_LAB_H, NEU, 'CENTER', 115)
            cnd, tmp, day, ok = '[WEATHER.CONDITION]', '[WEATHER.TEMPERATURE]', '[WEATHER.IS_DAY]', WX_OK
        else:
            out += per('clock', lambda c: text(cx - 40, y1 - 11, 80, 22, *hour_label(i, c), S_LAB_H, NEU, 'CENTER', 115))
            cnd, tmp, day = ('[WEATHER.HOURS.%d.%s]' % (i, f) for f in ('CONDITION', 'TEMPERATURE', 'IS_DAY'))
            ok = H_OK(i)
        iw = 21
        w = iw + 3 + tw('18°', S_LAB_T)
        x = cx - w / 2
        out += cond([(ok, icon_font(x, y2 - iw / 2, iw, cnd, day, ACC, 230)
                       + temp_text(x + iw + 3, y2 - 13, 60, 26, tmp, S_LAB_T, 'START', alpha=209))])
    return out


def tomorrow_line():
    Y, S = C + 112, S_TOM
    H = S + 8
    iw, ri = round(S * 1.2), round(S * 1.05)
    wd, wtmp, wr, wu = tw('WED', S), tw('20°/8°', S), tw('40%', S), tw('UV 5', S)
    total = wd + 11 + iw + 3 + wtmp + 11 + ri + 3 + wr + 11 + wu
    x = C - total / 2
    out = text(x, Y - H / 2, 70, H, '%s', [DOW_TOMORROW], S, NEU, 'START', 128)
    x += wd + 11
    out += icon_font(x, Y - iw / 2, iw, '[WEATHER.DAYS.1.CONDITION_DAY]')
    x += iw + 3
    hi, lo = '[WEATHER.DAYS.1.TEMPERATURE_HIGH]', '[WEATHER.DAYS.1.TEMPERATURE_LOW]'
    out += per('tunit', lambda un: text(x, Y - H / 2, 100, H, '%s°/%s°', [temp(hi, un), temp(lo, un)], S, NEU, 'START', 209))
    x += wtmp + 11
    rp = '[WEATHER.DAYS.1.CHANCE_OF_PRECIPITATION]'
    xr = x
    out += per('rth', lambda r: cond([('%s >= %s' % (rp, r), image(xr, Y - ri / 2, ri, 'ic_rain', ACC)
                                       + text(xr + ri + 3, Y - H / 2, 70, H, '%s%%', [rp], S, NEU, 'START', 209))]))
    x += ri + 3 + wr + 11
    uv = '[WEATHER.DAYS.1.UV_INDEX]'
    out += per('uvt', lambda u: cond([('%s >= %s' % (uv, u), text(x, Y - H / 2, 80, H, 'UV %s', [uv], S, AMBER, 'START')),
                                      ('%s >= 3' % uv, text(x, Y - H / 2, 80, H, 'UV %s', [uv], S, NEU, 'START', 209))]))
    return cond([('[WEATHER.DAYS.1.IS_AVAILABLE]', out)])


def bottom():
    """Hourly U; from 'evening starts' a dial-coloured cover hides it and the tomorrow line sits on top."""
    evening = per('dial2', lambda o: rect(0, C + 88, 450, 450 - C - 88, dial_color(o))) + tomorrow_line()
    return comb() + comb_labels() + per('eve23', lambda e: cond([('%s >= %s' % (HOUR, e), evening)]))


# ---------------------------------------------------------------- always-on
def aod():
    """Vector-only analog face: plain lines rotated by Transform (no images, no tints)."""
    out = rect(0, 0, 450, 450, '#ff000000')
    for i in range(12):
        a = math.radians(i * 30 - 90)
        major = i % 3 == 0
        r1, r2 = 203, (182 if major else 194)
        for o in ((-4.5, 4.5) if i == 0 else (0,)):
            px, py = math.cos(a + math.pi / 2) * o, math.sin(a + math.pi / 2) * o
            out += line(C + math.cos(a) * r1 + px, C + math.sin(a) * r1 + py, C + math.cos(a) * r2 + px, C + math.sin(a) * r2 + py,
                        ACC, 3.2 if major else 1.6, 150)
    out += text(0, C + 98, 450, 30, '%s · %s %s', [DOW, '[DAY]', MON], S_AOD, NEU, 'CENTER', 140, spacing='0.15')
    # The face's only clock element, so the always-on renderer can offload it.
    out += ('<AnalogClock x="0" y="0" width="450" height="450">'
            '<HourHand resource="hand_hour" x="220" y="113" width="10" height="126" pivotX="0.5" pivotY="%.5f" tintColor="%s"/>'
            '<MinuteHand resource="hand_minute" x="222" y="49" width="7" height="194" pivotX="0.5" pivotY="%.5f" tintColor="%s"/>'
            '</AnalogClock>') % (112 / 126, ACC, 176 / 194, HAND)  # hour hand in the accent: it's the critical one
    out += dot(C, C, 8.5, HAND) + dot(C, C, 3.2, '#ff000000')
    return out


def bitmap_fonts():
    out = '<BitmapFonts><BitmapFont name="wx">'
    for i in range(33):
        tag = 'Character' if i < 10 else 'Word'
        res = 'wx_d_%d' % i if i < 16 else ('wx_n_%d' % (i - 16) if i < 32 else 'ic_rain')
        sz = 64 if res == 'ic_rain' else 96
        out += '<%s name="%d" resource="%s" width="%d" height="%d"/>' % (tag, i, res, sz, sz)
    return out + '</BitmapFont></BitmapFonts>'


def watchface():
    main = background() + bottom() + battery_ring() + top_line() + time_block() + health_row()
    # Always-on layer underneath, always visible; the opaque main layer covers it and fades out in ambient.
    scene = ('<Scene backgroundColor="#ff000000">'
             + group('always_on', aod())
             + group('main', main, 0)
             + event_slot()
             + sleep_slot()
             + '</Scene>')
    return ('<?xml version="1.0" encoding="utf-8"?>\n<WatchFace width="450" height="450" clipShape="CIRCLE">'
            '<Metadata key="CLOCK_TYPE" value="DIGITAL"/><Metadata key="PREVIEW_TIME" value="10:08:00"/>'
            + user_configurations() + bitmap_fonts() + scene + '</WatchFace>\n')


for d in ('raw', 'values'):
    os.makedirs(os.path.join(RES, d), exist_ok=True)
xml = watchface()

# Test only: RC_FAKE=<scenario> swaps live data for fixed worst-case values to check that everything fits.
FAKES = {
    'base': {'[DAY]': '30', '[DAY_OF_WEEK]': '4', '[WEATHER.TEMPERATURE]': '-12', '[WEATHER.IS_AVAILABLE]': '1',
             '[WEATHER.CONDITION]': '14', '[WEATHER.IS_DAY]': '1', '[WEATHER.DAYS.0.CHANCE_OF_PRECIPITATION]': '0',
             '[WEATHER.DAYS.0.CHANCE_OF_PRECIPITATION_NIGHT]': '0',
             **{'[WEATHER.HOURS.%d.%s]' % (k, f): v for k in range(1, 9) for f, v in
                (('IS_AVAILABLE', '1'), ('CONDITION', '2'), ('UV_INDEX', '0'), ('TEMPERATURE', '-12'), ('IS_DAY', '1'))}},
    'rain_soon': {'[WEATHER.HOURS.2.CONDITION]': '6', '[WEATHER.HOURS.3.CONDITION]': '4', '[WEATHER.HOURS.4.CONDITION]': '6'},
    'uv_later': {'[WEATHER.CONDITION]': '8', '[WEATHER.HOURS.3.UV_INDEX]': '11', '[WEATHER.HOURS.4.UV_INDEX]': '9',
                 '[WEATHER.HOURS.5.UV_INDEX]': '6', '[WEATHER.HOURS.6.UV_INDEX]': '4'},
    'rain_pct': {'[WEATHER.DAYS.0.CHANCE_OF_PRECIPITATION]': '100', '[WEATHER.DAYS.0.CHANCE_OF_PRECIPITATION_NIGHT]': '100'},
}
fake = os.environ.get('RC_FAKE')
if fake:
    for k, v in {**FAKES['base'], **FAKES[fake]}.items():
        xml = xml.replace(k, '(%s)' % v)
with open(os.path.join(RES, 'raw/watchface.xml'), 'w', encoding='utf-8') as f:
    f.write(xml)
with open(os.path.join(RES, 'values/strings.xml'), 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n')
    for k, v in STRINGS.items():
        assert '%' not in v, 'a bare %% in a label crashes the watch: %r' % v
        f.write('  <string name="%s">%s</string>\n' % (k, escape(v).replace("'", "\\'")))
    f.write('</resources>\n')
print('watchface.xml: %d KB, %d conditions, shift %+dh' % (len(xml) // 1024, _n[0], SHIFT))
