import math

INK = "#111111"
INK2 = "#3a3a3a"
MUTED = "#8a8a8a"
GRID = "#ececec"
SOFT = "#d9d9d9"
MID = "#9b9b9b"


def smooth_path(points):
    if len(points) < 2:
        return ""
    d = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def monotone_path(points):
    n = len(points)
    if n < 3:
        return smooth_path(points)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [d[0]] + [0.0] * (n - 2) + [d[-1]]
    for i in range(1, n - 1):
        m[i] = 0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9:
                t = 3 / math.sqrt(s)
                m[i], m[i + 1] = t * a * d[i], t * b * d[i]
    out = f"M{xs[0]:.1f},{ys[0]:.1f}"
    for i in range(n - 1):
        h = xs[i + 1] - xs[i]
        out += (f" C{xs[i] + h / 3:.1f},{ys[i] + m[i] * h / 3:.1f} "
                f"{xs[i + 1] - h / 3:.1f},{ys[i + 1] - m[i + 1] * h / 3:.1f} {xs[i + 1]:.1f},{ys[i + 1]:.1f}")
    return out


def area_chart(values, labels, threshold, width=820, height=260, ymin=0.0, ymax=1.0,
               tooltip=None, bands=None, yticks=None, gid="g1", titles=None, line_label="alert line",
               dot_min=None, yfmt="{:.2f}"):
    """Smooth area chart with a dashed alert line.

    values: one number per day. labels: evenly spaced x-axis labels.
    tooltip: (index, line1, line2) drawn as a black bubble.
    bands: list of (start, end) index pairs to shade (7-day carry-over).
    titles: {index: text} shown when hovering a dot.
    """
    pad_l, pad_r, pad_t, pad_b = 44, 12, 16, 30
    w = width - pad_l - pad_r
    h = height - pad_t - pad_b
    n = len(values)

    def x(i):
        return pad_l + w * i / (n - 1)

    def y(v):
        return pad_t + h * (1 - (v - ymin) / (ymax - ymin))

    pts = [(x(i), y(v)) for i, v in enumerate(values)]
    line = monotone_path(pts)
    area = line + f" L{pts[-1][0]:.1f},{pad_t + h:.1f} L{pts[0][0]:.1f},{pad_t + h:.1f} Z"
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" preserveAspectRatio="none" class="chart">']
    out.append(f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0%" stop-color="#111" stop-opacity="0.16"/>'
               f'<stop offset="100%" stop-color="#111" stop-opacity="0"/></linearGradient></defs>')
    yticks = yticks or [ymin + (ymax - ymin) * k / 4 for k in range(5)]
    for t in yticks:
        out.append(f'<line x1="{pad_l}" x2="{width - pad_r}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{pad_l - 10}" y="{y(t) + 4:.1f}" text-anchor="end" class="tick">{yfmt.format(t)}</text>')
    for a, b in bands or []:
        bw_ = max(x(b) - x(a), 4)
        out.append(f'<rect x="{x(a) - 2:.1f}" y="{pad_t}" width="{bw_ + 4:.1f}" height="{h}" fill="#111" opacity="0.035" rx="6"/>')
    out.append(f'<path d="{area}" fill="url(#{gid})"/>')
    out.append(f'<path d="{line}" fill="none" stroke="{INK}" stroke-width="2.2" stroke-linecap="round"/>')
    ty = y(threshold)
    out.append(f'<line x1="{pad_l}" x2="{width - pad_r}" y1="{ty:.1f}" y2="{ty:.1f}" stroke="{INK}" stroke-width="1.2" stroke-dasharray="5 5" opacity=".55"/>')
    out.append(f'<text x="{width - pad_r}" y="{ty - 7:.1f}" text-anchor="end" class="tick strong">{line_label}</text>')
    titles = titles or {}
    dot_min = threshold if dot_min is None else dot_min
    for i, v in enumerate(values):
        if v >= dot_min:
            tip = f"<title>{titles[i]}</title>" if i in titles else ""
            out.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="4.2" fill="{INK}" stroke="#fff" stroke-width="2">{tip}</circle>')
    for k, lab in enumerate(labels):
        i = min(n - 1, round(k * (n - 1) / max(len(labels) - 1, 1)))
        out.append(f'<text x="{x(i):.1f}" y="{height - 8}" text-anchor="middle" class="tick">{lab}</text>')
    if tooltip is not None:
        i, text1, text2 = tooltip
        px, py = x(i), y(values[i])
        out.append(f'<line x1="{px:.1f}" x2="{px:.1f}" y1="{pad_t}" y2="{pad_t + h}" stroke="{INK}" stroke-width="1" stroke-dasharray="2 3" opacity=".5"/>')
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="{INK}" stroke="#fff" stroke-width="2.5"/>')
        bw = 184
        bx = min(max(px - bw / 2, pad_l), width - pad_r - bw)
        by = max(py - 62, 2)
        out.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw}" height="46" rx="12" fill="{INK}"/>')
        out.append(f'<text x="{bx + 14:.1f}" y="{by + 19:.1f}" class="tt1">{text1}</text>')
        out.append(f'<text x="{bx + 14:.1f}" y="{by + 36:.1f}" class="tt2">{text2}</text>')
    out.append("</svg>")
    return "".join(out)


def donut(parts, size=190, thickness=26, center_top="", center_bottom=""):
    total = sum(v for _, v, _ in parts)
    r = size / 2 - thickness / 2
    c = size / 2
    out = [f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}">']
    start = -math.pi / 2
    gap = 0.035
    for _, v, color in parts:
        ang = 2 * math.pi * v / total
        a0, a1 = start + gap / 2, start + ang - gap / 2
        large = 1 if a1 - a0 > math.pi else 0
        x0, y0 = c + r * math.cos(a0), c + r * math.sin(a0)
        x1, y1 = c + r * math.cos(a1), c + r * math.sin(a1)
        out.append(f'<path d="M{x0:.2f},{y0:.2f} A{r},{r} 0 {large} 1 {x1:.2f},{y1:.2f}" fill="none" '
                   f'stroke="{color}" stroke-width="{thickness}" stroke-linecap="round"/>')
        start += ang
    out.append(f'<text x="{c}" y="{c - 2}" text-anchor="middle" class="donut-big">{center_top}</text>')
    out.append(f'<text x="{c}" y="{c + 20}" text-anchor="middle" class="tick">{center_bottom}</text>')
    out.append("</svg>")
    return "".join(out)


def heat_grid(weeks, rows=12, width=760, gap=4, labels=None):
    n = len(weeks)
    cell = (width - 34 - (n - 1) * gap) / n
    cell_h = 16
    top = 8
    height = top + rows * (cell_h + gap) + 26
    out = [f'<svg viewBox="0 0 {width} {height:.0f}" width="100%" class="chart">']
    for r in range(0, rows + 1, 4):
        yy = top + (rows - r) * (cell_h + gap) - gap / 2
        out.append(f'<text x="24" y="{yy + 4:.1f}" text-anchor="end" class="tick">{r * 5}</text>')
    for i, (dark, light) in enumerate(weeks):
        x0 = 34 + i * (cell + gap)
        for r in range(rows):
            yy = top + (rows - 1 - r) * (cell_h + gap)
            if r < dark:
                fill = INK
            elif r < dark + light:
                fill = "#bdbdbd"
            else:
                fill = "#f1f1f1"
            out.append(f'<rect x="{x0:.1f}" y="{yy:.1f}" width="{cell:.1f}" height="{cell_h}" rx="4" fill="{fill}"/>')
    if labels:
        for k, lab in enumerate(labels):
            i = round(k * (n - 1) / max(len(labels) - 1, 1))
            out.append(f'<text x="{34 + i * (cell + gap) + cell / 2:.1f}" y="{height - 6:.1f}" text-anchor="middle" class="tick">{lab}</text>')
    out.append("</svg>")
    return "".join(out)


def diverging_bars(items, width=420, row=42, maxv=20):
    height = len(items) * row + 10
    mid = 170
    span = width - mid - 70
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" class="chart">']
    out.append(f'<line x1="{mid}" x2="{mid}" y1="0" y2="{height - 6}" stroke="{SOFT}" stroke-width="1"/>')
    for k, (label, v) in enumerate(items):
        yy = k * row + 8
        out.append(f'<text x="0" y="{yy + 17}" class="lbl">{label}</text>')
        bw = max(4, abs(v) / maxv * span)
        color = INK if v > 0 else MID
        xx = mid if v > 0 else mid - bw
        out.append(f'<rect x="{xx:.1f}" y="{yy + 5}" width="{bw:.1f}" height="16" rx="8" fill="{color}"/>')
        tx = mid + bw + 8 if v > 0 else mid + 8
        out.append(f'<text x="{tx:.1f}" y="{yy + 17}" class="lbl strong">{v:+.1f}σ</text>')
    out.append("</svg>")
    return "".join(out)


def budget_lines(series, width=820, height=300, xmin=0.4, xmax=35):
    pad_l, pad_r, pad_t, pad_b = 48, 20, 16, 34
    w = width - pad_l - pad_r
    h = height - pad_t - pad_b
    tick_values = [t for t in [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100] if xmin <= t <= xmax]
    xmin, xmax = math.log10(xmin), math.log10(xmax)

    def x(v):
        return pad_l + w * (math.log10(v) - xmin) / (xmax - xmin)

    def y(v):
        return pad_t + h * (1 - v)

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" class="chart">']
    for t in [0, .25, .5, .75, 1]:
        out.append(f'<line x1="{pad_l}" x2="{pad_l + w}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{pad_l - 10}" y="{y(t) + 4:.1f}" text-anchor="end" class="tick">{int(t * 100)}%</text>')
    for t in tick_values:
        out.append(f'<text x="{x(t):.1f}" y="{height - 10}" text-anchor="middle" class="tick">{t:g}</text>')
    for name, pts, color, dash, marker in series:
        coords = [(x(a), y(b)) for a, b in sorted(pts) if a > 0]
        if len(coords) < 2:
            continue
        d = smooth_path(coords)
        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{2.6 if color == INK else 2}" '
                   f'stroke-dasharray="{dash}" stroke-linecap="round"/>')
        for cx, cy in coords:
            if marker == "circle":
                out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="{color}" stroke="#fff" stroke-width="1.6"/>')
            else:
                out.append(f'<rect x="{cx - 3.6:.1f}" y="{cy - 3.6:.1f}" width="7.2" height="7.2" rx="1.5" fill="{color}" stroke="#fff" stroke-width="1.4"/>')
    out.append("</svg>")
    return "".join(out)


def grouped_bars(groups, series_names, colors, width=520, height=250, maxv=16, step=4, bw=22):
    pad_l, pad_b, pad_t = 30, 40, 14
    h = height - pad_b - pad_t
    gw = (width - pad_l) / len(groups)
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" class="chart">']
    for t in range(0, maxv + 1, step):
        yy = pad_t + h * (1 - t / maxv)
        out.append(f'<line x1="{pad_l}" x2="{width}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{pad_l - 8}" y="{yy + 4:.1f}" text-anchor="end" class="tick">{t}</text>')
    for g, (label, total, vals) in enumerate(groups):
        cx = pad_l + gw * g + gw / 2
        start = cx - (len(vals) * (bw + 6) - 6) / 2
        tot_y = pad_t + h * (1 - total / maxv)
        out.append(f'<rect x="{start - 8:.1f}" y="{tot_y:.1f}" width="{len(vals) * (bw + 6) + 10:.1f}" height="{pad_t + h - tot_y:.1f}" rx="12" fill="#f3f3f3"/>')
        for k, v in enumerate(vals):
            bh = h * v / maxv
            xx = start + k * (bw + 6)
            out.append(f'<rect x="{xx:.1f}" y="{pad_t + h - bh:.1f}" width="{bw}" height="{bh:.1f}" rx="7" fill="{colors[k]}"/>')
            out.append(f'<text x="{xx + bw / 2:.1f}" y="{pad_t + h - bh - 6:.1f}" text-anchor="middle" class="tick strong">{v}</text>')
        out.append(f'<text x="{cx:.1f}" y="{height - 18}" text-anchor="middle" class="lbl strong">{label}</text>')
        out.append(f'<text x="{cx:.1f}" y="{height - 3}" text-anchor="middle" class="tick">{total} insiders</text>')
    out.append("</svg>")
    return "".join(out)


def early_bars(rows, width=420, total=34):
    row = 50
    height = len(rows) * row + 8
    lab_w = 130
    span = width - lab_w - 50
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" class="chart">']
    for k, (name, during, early, chance) in enumerate(rows):
        yy = k * row + 6
        out.append(f'<text x="0" y="{yy + 20}" class="lbl">{name}</text>')
        out.append(f'<rect x="{lab_w}" y="{yy + 8}" width="{span}" height="16" rx="8" fill="#f1f1f1"/>')
        out.append(f'<rect x="{lab_w}" y="{yy + 8}" width="{span * early / total:.1f}" height="16" rx="8" fill="{INK}"/>')
        out.append(f'<rect x="{lab_w}" y="{yy + 8}" width="{span * during / total:.1f}" height="16" rx="8" fill="{MID}"/>')
        out.append(f'<text x="{lab_w + span + 8}" y="{yy + 21}" class="lbl strong">{early}/{total}</text>')
        out.append(f'<text x="{lab_w}" y="{yy + 40}" class="tick">during {during} · chance {chance}</text>')
    out.append("</svg>")
    return "".join(out)


def sparkline(values, width=110, height=34, dark=False):
    n = len(values)
    lo, hi = min(values), max(values)
    pts = [(4 + (width - 8) * i / (n - 1), height - 4 - (height - 8) * (v - lo) / ((hi - lo) or 1)) for i, v in enumerate(values)]
    color = "#ffffff" if dark else INK
    return (f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
            f'<path d="{smooth_path(pts)}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/></svg>')


def mini_bars(values, width=110, height=34, dark=False):
    n = len(values)
    hi = max(values) or 1
    bw = (width - (n - 1) * 3) / n
    out = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}">']
    for i, v in enumerate(values):
        bh = max(3, (height - 2) * v / hi)
        color = ("#ffffff" if i == n - 1 else "#5c5c5c") if dark else (INK if i == n - 1 else "#cfcfcf")
        out.append(f'<rect x="{i * (bw + 3):.1f}" y="{height - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="2" fill="{color}"/>')
    out.append("</svg>")
    return "".join(out)


def radar(axes, normal, worst, size=380, labels_extra=None):
    c = size / 2
    r = size / 2 - 92
    n = len(axes)
    ang = [-math.pi / 2 + 2 * math.pi * k / n for k in range(n)]

    def pt(k, v):
        return c + r * v * math.cos(ang[k]), c + r * v * math.sin(ang[k])

    out = [f'<svg viewBox="0 0 {size} {size}" width="100%" class="chart">']
    out.append('<defs><radialGradient id="rg" cx="50%" cy="50%" r="50%">'
               '<stop offset="0%" stop-color="#ffffff"/><stop offset="100%" stop-color="#f1f1f1"/></radialGradient>'
               '<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="6" stdDeviation="8" flood-opacity=".08"/></filter></defs>')
    for k, f in enumerate([1.08, 0.78, 0.48]):
        out.append(f'<circle cx="{c}" cy="{c}" r="{r * f:.1f}" fill="url(#rg)" stroke="#ececec" filter="url(#soft)"/>')
    for k in range(n):
        x, y = pt(k, 1)
        out.append(f'<line x1="{c}" y1="{c}" x2="{x:.1f}" y2="{y:.1f}" stroke="#e6e6e6"/>')
    for vals, stroke, fill, w, dash in [(normal, "#9b9b9b", "rgba(0,0,0,.06)", 1.8, "5 4"), (worst, INK, "rgba(0,0,0,.10)", 2.4, "")]:
        pts = [pt(k, v) for k, v in enumerate(vals)]
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
        out.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" stroke-linejoin="round" stroke-dasharray="{dash}"/>')
        for x, y in pts:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="#fff" stroke="{stroke}" stroke-width="1.8"/>')
    for k, a in enumerate(axes):
        x, y = pt(k, 1.32)
        anchor = "middle" if abs(math.cos(ang[k])) < 0.3 else ("start" if math.cos(ang[k]) > 0 else "end")
        out.append(f'<text x="{x:.1f}" y="{y - 4:.1f}" text-anchor="{anchor}" class="tick">{a}</text>')
        if labels_extra:
            out.append(f'<text x="{x:.1f}" y="{y + 12:.1f}" text-anchor="{anchor}" class="lbl strong">{labels_extra[k]}</text>')
    out.append("</svg>")
    return "".join(out)


def hatched_bars(values, labels, highlight, tooltip, width=640, height=250, vmax=1.0, titles=None):
    pad_t, pad_b = 62, 30
    h = height - pad_t - pad_b
    n = len(values)
    gw = width / n
    bw = gw * 0.62
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" class="chart">']
    out.append('<defs><pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
               '<rect width="7" height="7" fill="#e4e4e4"/><line x1="0" y1="0" x2="0" y2="7" stroke="#d0d0d0" stroke-width="2.4"/></pattern>'
               '<pattern id="hatchd" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
               '<rect width="7" height="7" fill="#2a2a2a"/><line x1="0" y1="0" x2="0" y2="7" stroke="#555" stroke-width="2.4"/></pattern></defs>')
    for t in range(4):
        yy = pad_t + h * t / 3
        out.append(f'<line x1="0" x2="{width}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#efefef" stroke-dasharray="3 4"/>')
    for i, v in enumerate(values):
        x0 = i * gw + (gw - bw) / 2
        track_h = h * 0.92
        out.append(f'<rect x="{x0:.1f}" y="{pad_t + h - track_h:.1f}" width="{bw:.1f}" height="{track_h:.1f}" rx="9" fill="#f5f5f5"/>')
        bh = h * v / vmax
        fill = "url(#hatchd)" if i == highlight else "url(#hatch)"
        stroke = 'stroke="#111" stroke-width="2"' if i == highlight else ""
        tip = f"<title>{titles[i]}</title>" if titles else ""
        out.append(f'<rect x="{x0:.1f}" y="{pad_t + h - bh:.1f}" width="{bw:.1f}" height="{max(bh, 2):.1f}" rx="9" fill="{fill}" {stroke}>{tip}</rect>')
        out.append(f'<text x="{x0 + bw / 2:.1f}" y="{height - 8}" text-anchor="middle" class="tick">{labels[i]}</text>')
    x0 = highlight * gw + gw / 2
    top = pad_t + h - h * values[highlight] / vmax
    out.append(f'<circle cx="{x0:.1f}" cy="{top:.1f}" r="6" fill="#fff" stroke="#111" stroke-width="2.4"/>')
    t1, t2 = tooltip
    bw2 = 150
    bx = min(max(x0, bw2 / 2 + 2), width - bw2 / 2 - 2)
    out.append(f'<rect x="{bx - bw2 / 2:.1f}" y="{top - 58:.1f}" width="{bw2}" height="44" rx="11" fill="#111"/>')
    out.append(f'<path d="M{x0 - 6:.1f},{top - 14:.1f} L{x0:.1f},{top - 8:.1f} L{x0 + 6:.1f},{top - 14:.1f} Z" fill="#111"/>')
    out.append(f'<text x="{bx:.1f}" y="{top - 40:.1f}" text-anchor="middle" class="tt1">{t1}</text>')
    out.append(f'<text x="{bx:.1f}" y="{top - 23:.1f}" text-anchor="middle" class="tt2">{t2}</text>')
    out.append("</svg>")
    return "".join(out)


def gauge(value, vmax, big, small, marker=None, width=320, dark=False):
    c = width / 2
    r = width / 2 - 26
    cy = r + 20
    height = cy + 18
    track = "#2b2b2b" if dark else "#ececec"
    fg = "#ffffff" if dark else "#3c3c3c"

    def p(f):
        a = math.pi * (1 - f)
        return c + r * math.cos(a), cy - r * math.sin(a)

    out = [f'<svg viewBox="0 0 {width} {height:.0f}" width="100%" class="chart">']
    x0, y0 = p(0)
    x1, y1 = p(1)
    out.append(f'<path d="M{x0:.1f},{y0:.1f} A{r},{r} 0 0 1 {x1:.1f},{y1:.1f}" fill="none" stroke="{track}" stroke-width="30" stroke-linecap="round"/>')
    f = min(value / vmax, 1)
    xv, yv = p(f)
    out.append(f'<path d="M{x0:.1f},{y0:.1f} A{r},{r} 0 0 1 {xv:.1f},{yv:.1f}" fill="none" stroke="{fg}" stroke-width="30" stroke-linecap="round"/>')
    if marker is not None:
        a = math.pi * (1 - marker)
        mx1, my1 = c + (r - 22) * math.cos(a), cy - (r - 22) * math.sin(a)
        mx2, my2 = c + (r + 22) * math.cos(a), cy - (r + 22) * math.sin(a)
        out.append(f'<line x1="{mx1:.1f}" y1="{my1:.1f}" x2="{mx2:.1f}" y2="{my2:.1f}" stroke="{"#fff" if dark else "#111"}" stroke-width="2.5" stroke-linecap="round"/>')
    color = "#fff" if dark else "#111"
    out.append(f'<text x="{c}" y="{cy - 6:.1f}" text-anchor="middle" style="font-size:46px;font-weight:680;letter-spacing:-0.04em;fill:{color};font-family:Inter">{big}</text>')
    out.append("</svg>")
    return "".join(out)


def step_area(values, labels, width=520, height=270, vmax=34, ticks=(0, 10, 20, 30)):
    pad_l, pad_r, pad_t, pad_b = 34, 6, 18, 44
    w = width - pad_l - pad_r
    h = height - pad_t - pad_b
    n = len(values)
    sw = w / n

    def y(v):
        return pad_t + h * (1 - v / vmax)

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" class="chart">']
    out.append('<defs><linearGradient id="stepg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#111" stop-opacity=".16"/>'
               '<stop offset="100%" stop-color="#111" stop-opacity="0"/></linearGradient></defs>')
    for t in ticks:
        out.append(f'<line x1="{pad_l}" x2="{width - pad_r}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="#ececec" stroke-dasharray="3 4"/>')
        out.append(f'<text x="{pad_l - 8}" y="{y(t) + 4:.1f}" text-anchor="end" class="tick">{t}</text>')
    for i in range(1, n):
        xx = pad_l + sw * i
        out.append(f'<line x1="{xx:.1f}" x2="{xx:.1f}" y1="{pad_t}" y2="{pad_t + h}" stroke="#f1f1f1" stroke-dasharray="3 4"/>')
    d = f"M{pad_l},{pad_t + h}"
    for i, v in enumerate(values):
        d += f" L{pad_l + sw * i:.1f},{y(v):.1f} L{pad_l + sw * (i + 1):.1f},{y(v):.1f}"
    d += f" L{pad_l + w:.1f},{pad_t + h} Z"
    out.append(f'<path d="{d}" fill="url(#stepg)"/>')
    for i, (v, lab) in enumerate(zip(values, labels)):
        x0, x1 = pad_l + sw * i, pad_l + sw * (i + 1)
        last = i == n - 1
        out.append(f'<line x1="{x0:.1f}" x2="{x1:.1f}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{INK if last else "#6a6a6a"}" stroke-width="{4 if last else 3}" stroke-linecap="round"/>')
        out.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{y(v) - 10:.1f}" text-anchor="middle" class="lbl strong">{v}</text>')
        out.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{height - 22}" text-anchor="middle" class="lbl strong">{lab[0]}</text>')
        out.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{height - 6}" text-anchor="middle" class="tick">{lab[1]}</text>')
    out.append("</svg>")
    return "".join(out)


def rose(items, size=400, hole=26):
    c = size / 2
    rmax = size / 2 - 96
    total = sum(v for _, v, _ in items)
    vmax = max(v for _, v, _ in items)
    out = [f'<svg viewBox="0 0 {size} {size}" width="100%" class="chart" style="overflow:visible">']
    out.append(f'<circle cx="{c}" cy="{c}" r="{rmax + 14}" fill="none" stroke="#dcdcdc" stroke-dasharray="2 5"/>')
    start = -math.pi / 2
    for label, v, color in items:
        ang = 2 * math.pi * v / total
        r = hole + (rmax - hole) * math.sqrt(v / vmax)
        a0, a1 = start, start + ang
        large = 1 if ang > math.pi else 0
        p = [(c + hole * math.cos(a0), c + hole * math.sin(a0)), (c + r * math.cos(a0), c + r * math.sin(a0)),
             (c + r * math.cos(a1), c + r * math.sin(a1)), (c + hole * math.cos(a1), c + hole * math.sin(a1))]
        d = (f"M{p[0][0]:.1f},{p[0][1]:.1f} L{p[1][0]:.1f},{p[1][1]:.1f} A{r:.1f},{r:.1f} 0 {large} 1 {p[2][0]:.1f},{p[2][1]:.1f} "
             f"L{p[3][0]:.1f},{p[3][1]:.1f} A{hole},{hole} 0 {large} 0 {p[0][0]:.1f},{p[0][1]:.1f} Z")
        out.append(f'<path d="{d}" fill="{color}" stroke="#fff" stroke-width="2"/>')
        mid = (a0 + a1) / 2
        lx1, ly1 = c + (r + 4) * math.cos(mid), c + (r + 4) * math.sin(mid)
        lx2, ly2 = c + (rmax + 26) * math.cos(mid), c + (rmax + 26) * math.sin(mid)
        anchor = "start" if math.cos(mid) > 0.1 else ("end" if math.cos(mid) < -0.1 else "middle")
        out.append(f'<line x1="{lx1:.1f}" y1="{ly1:.1f}" x2="{lx2:.1f}" y2="{ly2:.1f}" stroke="#bbb" stroke-dasharray="2 3"/>')
        dx = 4 if anchor == "start" else (-4 if anchor == "end" else 0)
        out.append(f'<text x="{lx2 + dx:.1f}" y="{ly2 - 2:.1f}" text-anchor="{anchor}" style="font-size:17px;font-weight:700;fill:#111;font-family:Inter">{v}</text>')
        out.append(f'<text x="{lx2 + dx:.1f}" y="{ly2 + 13:.1f}" text-anchor="{anchor}" class="tick">{label}</text>')
        start = a1
    out.append(f'<circle cx="{c}" cy="{c}" r="{hole - 4}" fill="#111"/>')
    out.append("</svg>")
    return "".join(out)


def dot_matrix(groups, per_row=8, r=10, gap=8, width=460):
    step = 2 * r + gap
    out_rows = []
    y = 10
    for name, desc, caught, early, missed in groups:
        total = caught + early + missed
        rows = math.ceil(total / per_row)
        out_rows.append((name, desc, caught, early, missed, y, rows))
        y += 26 + rows * step + 14
    height = y
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" class="chart">']
    for name, desc, caught, early, missed, y0, rows in out_rows:
        out.append(f'<text x="0" y="{y0 + 12}" class="lbl strong">{name}</text>')
        out.append(f'<text x="64" y="{y0 + 12}" class="tick">{desc}</text>')
        kinds = ["c"] * caught + ["e"] * early + ["m"] * missed
        for k, kind in enumerate(kinds):
            cx = r + (k % per_row) * step
            cy = y0 + 26 + r + (k // per_row) * step
            if kind == "c":
                out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#111"/>')
            elif kind == "e":
                out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#a6a6a6"/>')
            else:
                out.append(f'<circle cx="{cx}" cy="{cy}" r="{r - 1}" fill="#fff" stroke="#bdbdbd" stroke-width="2" stroke-dasharray="3 3"/>')
        tot = caught + early + missed
        out.append(f'<text x="{width}" y="{y0 + 26 + r + 4}" text-anchor="end" class="lbl strong">{caught + early}/{tot}</text>')
    out.append("</svg>")
    return "".join(out)


def diamond_pills(items, width=460, vmax=34, ref=None, total=34):
    row = 46
    lab_w = 150
    span = width - lab_w - 56
    height = len(items) * row + 6
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" class="chart">']
    out.append('<defs><linearGradient id="pillg" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#d9d9d9"/>'
               '<stop offset="100%" stop-color="#5a5a5a"/></linearGradient>'
               '<linearGradient id="pilld" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#6a6a6a"/>'
               '<stop offset="100%" stop-color="#111"/></linearGradient></defs>')
    if ref is not None:
        rx = lab_w + span * ref / vmax
        out.append(f'<line x1="{rx:.1f}" x2="{rx:.1f}" y1="0" y2="{height}" stroke="#bbb" stroke-dasharray="3 4"/>')
    for k, (label, v, hi) in enumerate(items):
        yy = k * row + 10
        out.append(f'<text x="{lab_w - 14}" y="{yy + 17}" text-anchor="end" class="lbl {"strong" if hi else ""}">{label}</text>')
        bw = span * v / vmax
        out.append(f'<rect x="{lab_w}" y="{yy + 4}" width="{bw:.1f}" height="18" rx="9" fill="url(#{"pilld" if hi else "pillg"})"/>')
        dx = lab_w + bw
        out.append(f'<rect x="{dx - 9:.1f}" y="{yy + 4:.1f}" width="18" height="18" rx="3" fill="#fff" stroke="{INK if hi else "#777"}" stroke-width="2" transform="rotate(45 {dx:.1f} {yy + 13:.1f})"/>')
        out.append(f'<text x="{dx + 18:.1f}" y="{yy + 18}" class="lbl strong">{v}/{total}</text>')
    out.append("</svg>")
    return "".join(out)


def nice_ticks(low, high, count=5):
    """Round axis limits and evenly spaced tick values, e.g. 0.2, 0.4, 0.6."""
    span = max(high - low, 1e-9)
    raw = span / (count - 1)
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    start = math.floor(low / step) * step
    stop = math.ceil(high / step) * step
    ticks = []
    t = start
    while t <= stop + step / 2:
        ticks.append(round(t, 6))
        t += step
    return ticks[0], ticks[-1], ticks
