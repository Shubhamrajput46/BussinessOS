/* Tiny dependency-free SVG charts: BosCharts.render(el, {type:'bar'|'line', labels:[], series:[{name,values,color}]}) */
(function (global) {
    "use strict";
    var NS = "http://www.w3.org/2000/svg";
    var PALETTE = ["#16594a", "#1d4ed8", "#b45309", "#6d28d9"];

    function el(name, attrs, text) {
        var n = document.createElementNS(NS, name);
        for (var k in attrs) n.setAttribute(k, attrs[k]);
        if (text != null) n.textContent = text;
        return n;
    }
    function fmt(v) {
        var a = Math.abs(v);
        if (a >= 1e7) return (v / 1e7).toFixed(1) + "Cr";
        if (a >= 1e5) return (v / 1e5).toFixed(1) + "L";
        if (a >= 1e3) return (v / 1e3).toFixed(1) + "k";
        return String(Math.round(v));
    }
    function niceMax(v) {
        if (v <= 0) return 1;
        var p = Math.pow(10, Math.floor(Math.log10(v))), n = v / p;
        return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
    }

    function draw(host, cfg) {
        host.innerHTML = "";
        var W = Math.max(host.clientWidth, 280), H = Math.round(Math.min(340, Math.max(200, W * 0.42)));
        var m = { t: 12, r: 12, b: 28, l: 46 }, iw = W - m.l - m.r, ih = H - m.t - m.b;
        var series = cfg.series || [], labels = cfg.labels || [];
        var all = [].concat.apply([], series.map(function (s) { return s.values; }));
        var max = niceMax(Math.max.apply(null, all.concat([0]))), min = Math.min.apply(null, all.concat([0]));
        if (min < 0) min = -niceMax(-min); else min = 0;
        var range = max - min || 1;
        var y = function (v) { return m.t + ih - ((v - min) / range) * ih; };

        var svg = el("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": cfg.title || "chart" });
        for (var i = 0; i <= 4; i++) {
            var val = min + (range * i) / 4, yy = y(val);
            svg.appendChild(el("line", { x1: m.l, x2: W - m.r, y1: yy, y2: yy, stroke: "#e6e2d8", "stroke-width": 1 }));
            svg.appendChild(el("text", { x: m.l - 8, y: yy + 4, "text-anchor": "end", "font-size": 11, fill: "#6f6b60" }, fmt(val)));
        }
        var n = labels.length, step = n > 0 ? iw / n : iw;
        var every = Math.ceil(n / Math.max(1, Math.floor(iw / 64)));
        labels.forEach(function (l, idx) {
            if (idx % every) return;
            svg.appendChild(el("text", { x: m.l + step * idx + step / 2, y: H - 8, "text-anchor": "middle", "font-size": 11, fill: "#6f6b60" }, l));
        });

        if (cfg.type === "line") {
            series.forEach(function (s, si) {
                var color = s.color || PALETTE[si % PALETTE.length];
                var pts = s.values.map(function (v, idx) { return [m.l + step * idx + step / 2, y(v)]; });
                if (pts.length > 1) {
                    svg.appendChild(el("polyline", { points: pts.map(function (p) { return p.join(","); }).join(" "), fill: "none", stroke: color, "stroke-width": 2.5, "stroke-linejoin": "round", "stroke-linecap": "round" }));
                }
                pts.forEach(function (p, idx) {
                    var c = el("circle", { cx: p[0], cy: p[1], r: 4, fill: "#fff", stroke: color, "stroke-width": 2 });
                    c.appendChild(el("title", {}, (s.name ? s.name + " - " : "") + labels[idx] + ": " + s.values[idx]));
                    svg.appendChild(c);
                });
            });
        } else {
            var groupW = step * 0.7, barW = groupW / Math.max(series.length, 1), zero = y(0);
            series.forEach(function (s, si) {
                var color = s.color || PALETTE[si % PALETTE.length];
                s.values.forEach(function (v, idx) {
                    var x = m.l + step * idx + (step - groupW) / 2 + barW * si, top = Math.min(y(v), zero), h = Math.abs(y(v) - zero);
                    var r = el("rect", { x: x, y: top, width: Math.max(barW - 3, 2), height: Math.max(h, 1), rx: 3, fill: color });
                    r.appendChild(el("title", {}, (s.name ? s.name + " - " : "") + labels[idx] + ": " + v));
                    svg.appendChild(r);
                });
            });
        }
        host.appendChild(svg);
    }

    function render(host, cfg) {
        if (typeof host === "string") host = document.getElementById(host);
        if (!host) return;
        draw(host, cfg);
        var t;
        window.addEventListener("resize", function () { clearTimeout(t); t = setTimeout(function () { draw(host, cfg); }, 120); });
    }
    global.BosCharts = { render: render };
})(window);
