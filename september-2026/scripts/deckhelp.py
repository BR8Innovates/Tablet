import copy, io
from pptx import Presentation
from pptx.dml.color import RGBColor
from lxml import etree
import openpyxl

NS = {'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart', 'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}


def ind(n, dec=0):
    """Indian digit grouping, as used in the August deck (1,27,793)."""
    neg = n < 0
    n = abs(n)
    s = ('%.*f' % (dec, n))
    ip, _, fp = s.partition('.')
    if len(ip) > 3:
        head, tail = ip[:-3], ip[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head: parts.insert(0, head)
        ip = ','.join(parts + [tail])
    return ('-' if neg else '') + ip + ('.' + fp if fp else '')


def chg(new, old, dec=1):
    """▲ 38.7% style change; returns text only"""
    if not old:
        return '—'
    p = (new - old) / old * 100
    return ('▲ ' if p >= 0 else '▼ ') + '%.*f%%' % (dec, abs(p))


def chgpp(new, old, dec=1):
    d = (new - old) * 100
    return ('▲ ' if d >= 0 else '▼ ') + '%.*f pp' % (dec, abs(d))


def set_par(par, text):
    """Replace a paragraph's text keeping the first run's formatting."""
    runs = par.runs
    if not runs:
        if text == '':
            return
        r = par.add_run(); r.text = text
        epr = par._p.find('{%s}endParaRPr' % NS['a'])
        if epr is not None:
            rpr = r._r.get_or_add_rPr()
            for k, v in epr.attrib.items():
                rpr.set(k, v)
            for ch in epr:
                rpr.append(copy.deepcopy(ch))
        return
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def set_runs(par, texts):
    runs = par.runs
    for r, t in zip(runs, texts):
        r.text = t


def settext(shape, value):
    tf = shape.text_frame
    if isinstance(value, tuple):          # multi-run single paragraph
        set_runs(tf.paragraphs[0], list(value)); return
    if isinstance(value, str):
        value = [value]
    pars = tf.paragraphs
    while len(pars) < len(value):
        new = copy.deepcopy(pars[-1]._p)
        pars[-1]._p.addnext(new)
        pars = tf.paragraphs
    while len(pars) > len(value):
        pars[-1]._p.getparent().remove(pars[-1]._p)
        pars = tf.paragraphs
    for p, t in zip(pars, value):
        set_par(p, t)


def color_of(run):
    try:
        return run.font.color.rgb
    except Exception:
        return None


def fill_table(tbl, rows, good=None):
    """rows: list of list of str|None (None = keep). cells starting ▲/▼ are coloured using good[(r,c)] (True=green/False=red)."""
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            if v is None:
                continue
            cell = tbl.cell(r, c)
            par = cell.text_frame.paragraphs[0]
            set_par(par, v)
            if good is not None and (r, c) in good and par.runs:
                par.runs[0].font.color.rgb = GREEN if good[(r, c)] else RED


GREEN = RGBColor(0x0E, 0x7C, 0x5A)
RED = RGBColor(0xB3, 0x26, 0x1E)


def set_chart(chart, cats, series, names=None):
    """Overwrite cached categories/values of every series in plot order, and the embedded workbook."""
    cs = chart._chartSpace
    sers = cs.findall('.//c:ser', NS)
    assert len(sers) == len(series), (len(sers), len(series))
    wbpart = chart.part.chart_workbook.xlsx_part
    wb = openpyxl.load_workbook(io.BytesIO(wbpart.blob))
    ws = wb.worksheets[0]
    for si, (ser, vals) in enumerate(zip(sers, series)):
        if names:
            tx = ser.find('c:tx', NS)
            tx.find('.//c:v', NS).text = names[si]
            ws.cell(row=1, column=2 + si, value=names[si])
        cat = ser.find('c:cat', NS)
        val = ser.find('c:val', NS)
        for node in (cat, val):
            if node is None: continue
            cache = node.find('.//c:strCache', NS)
            if cache is None: cache = node.find('.//c:numCache', NS)
            pts = cache.findall('c:pt', NS)
            data = cats if node is cat else vals
            for pt in pts:
                cache.remove(pt)
            cnt = cache.find('c:ptCount', NS)
            cnt.set('val', str(len(data)))
            for i, v in enumerate(data):
                pt = etree.SubElement(cache, '{%s}pt' % NS['c']); pt.set('idx', str(i))
                vv = etree.SubElement(pt, '{%s}v' % NS['c']); vv.text = str(v)
            f = node.find('.//c:f', NS)
            if f is not None and '!' in f.text:
                ref = f.text.split('!')[1].replace('$', '')
                a, _, b = ref.partition(':')
                from openpyxl.utils.cell import coordinate_from_string, column_index_from_string
                col, row = coordinate_from_string(a)
                ci = column_index_from_string(col)
                for i, v in enumerate(data):
                    # vertical range
                    ws.cell(row=row + i, column=ci, value=v)
    bio = io.BytesIO(); wb.save(bio)
    wbpart._blob = bio.getvalue()


def duplicate_slide(prs, src_idx, insert_at):
    src = prs.slides[src_idx]
    new = prs.slides.add_slide(src.slide_layout)
    for ph in list(new.placeholders):
        ph._element.getparent().remove(ph._element)
    for el in src.shapes._spTree:
        if el.tag.endswith('}nvGrpSpPr') or el.tag.endswith('}grpSpPr'):
            continue
        new.shapes._spTree.append(copy.deepcopy(el))
    # reorder
    lst = prs.slides._sldIdLst
    ids = list(lst)
    el = ids[-1]
    lst.remove(el)
    lst.insert(insert_at, el)
    return new


def recolor_arrows(tbl, rules, default=True, skip_cols=(0,)):
    """colour every cell containing an arrow: rules[row] = True if an increase is good"""
    for r, row in enumerate(tbl.rows):
        if r == 0:
            continue
        up_good = rules.get(r, default)
        for c in range(len(tbl.columns)):
            if c in skip_cols:
                continue
            par = tbl.cell(r, c).text_frame.paragraphs[0]
            txt = ''.join(x.text for x in par.runs)
            if ('▲' in txt or '▼' in txt) and par.runs:
                up = txt.index('▲') < txt.index('▼') if ('▲' in txt and '▼' in txt) else ('▲' in txt)
                par.runs[0].font.color.rgb = GREEN if (up == up_good) else RED


def paint(shape, rgb):
    for p in shape.text_frame.paragraphs:
        for r in p.runs:
            r.font.color.rgb = rgb


def set_cell_color(tbl, r, c, rgb):
    for run in tbl.cell(r, c).text_frame.paragraphs[0].runs:
        run.font.color.rgb = rgb
