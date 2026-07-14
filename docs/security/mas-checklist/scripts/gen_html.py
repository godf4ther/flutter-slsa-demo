#!/usr/bin/env python3
"""从分类 CSV 生成可分享的 HTML 报告（Artifact 源）。"""
import os, csv, html
from collections import Counter

HERE = os.path.dirname(__file__)
CSV = os.path.join(HERE, "..", "data", "mas-static-classified.csv")
OUT = os.path.join(HERE, "..", "report.html")

PILL = {"yes": ('s-ok', '✅ 现成规则'), "partial": ('s-warn', '🟡 部分'), "no": ('s-no', '🔴 需自建')}

CSS = """<style>
:root{--paper:#E9ECEF;--surface:#F6F8F9;--surface-2:#FDFEFE;--line:#D0D6DC;--line-soft:#DDE2E7;
--ink:#191D24;--ink-2:#454C56;--ink-mute:#6C747E;--accent:#0B6E70;--accent-ink:#0A5658;--accent-wash:#D6E7E7;
--ok:#2E7A4E;--ok-wash:#D7E7DD;--warn:#A9720F;--warn-wash:#EDE0C6;--no:#A5432C;--no-wash:#EED9D2;--mute-wash:#E4E7EA;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;--sans:system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;}
@media(prefers-color-scheme:dark){:root{--paper:#101419;--surface:#171C22;--surface-2:#1E242B;--line:#2C333B;--line-soft:#262C33;
--ink:#E5E9ED;--ink-2:#B2BAC3;--ink-mute:#7E8892;--accent:#3FB6B0;--accent-ink:#6FD0CA;--accent-wash:#183436;
--ok:#5FB884;--ok-wash:#16301F;--warn:#D2A24E;--warn-wash:#332811;--no:#D97A5F;--no-wash:#33170F;--mute-wash:#20262D;}}
:root[data-theme=dark]{--paper:#101419;--surface:#171C22;--surface-2:#1E242B;--line:#2C333B;--line-soft:#262C33;
--ink:#E5E9ED;--ink-2:#B2BAC3;--ink-mute:#7E8892;--accent:#3FB6B0;--accent-ink:#6FD0CA;--accent-wash:#183436;
--ok:#5FB884;--ok-wash:#16301F;--warn:#D2A24E;--warn-wash:#332811;--no:#D97A5F;--no-wash:#33170F;--mute-wash:#20262D;}
:root[data-theme=light]{--paper:#E9ECEF;--surface:#F6F8F9;--surface-2:#FDFEFE;--line:#D0D6DC;--line-soft:#DDE2E7;
--ink:#191D24;--ink-2:#454C56;--ink-mute:#6C747E;--accent:#0B6E70;--accent-ink:#0A5658;--accent-wash:#D6E7E7;
--ok:#2E7A4E;--ok-wash:#D7E7DD;--warn:#A9720F;--warn-wash:#EDE0C6;--no:#A5432C;--no-wash:#EED9D2;--mute-wash:#E4E7EA;}
*{box-sizing:border-box}
.wrap{background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.6;padding:clamp(1rem,4vw,2.6rem) clamp(1rem,4vw,2rem) 5rem}
.col{max-width:64rem;margin:0 auto}
.eyebrow{font-family:var(--mono);font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--accent-ink);font-weight:600}
h1{font-size:clamp(1.5rem,4vw,2.2rem);line-height:1.14;letter-spacing:-.02em;font-weight:800;margin:.5rem 0 .4rem;text-wrap:balance}
.lede{font-size:1.05rem;color:var(--ink-2);max-width:44rem;margin:0}
.meta{font-family:var(--mono);font-size:.73rem;color:var(--ink-mute);margin-top:1rem;display:flex;flex-wrap:wrap;gap:.4rem 1.1rem}
.rule{height:1px;background:var(--line);border:0;margin:1.8rem 0}
h2{font-size:1.3rem;letter-spacing:-.01em;font-weight:700;margin:2.4rem 0 .9rem;text-wrap:balance}
h3{font-size:1rem;font-weight:700;margin:1.2rem 0 .4rem}
p{margin:.6rem 0}.k{font-family:var(--mono);font-size:.86em;background:var(--surface-2);border:1px solid var(--line-soft);border-radius:5px;padding:.05em .36em}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(8rem,1fr));gap:.7rem;margin:.5rem 0}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:.85rem .95rem}
.stat .n{font-family:var(--mono);font-size:1.8rem;font-weight:700;line-height:1;font-variant-numeric:tabular-nums}
.stat .l{font-size:.76rem;color:var(--ink-mute);margin-top:.35rem}
.stat.ok .n{color:var(--ok)}.stat.warn .n{color:var(--warn)}.stat.no .n{color:var(--no)}.stat.accent .n{color:var(--accent)}
.tbl-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin:.4rem 0}
table{border-collapse:collapse;width:100%;font-size:.85rem;min-width:34rem}
th,td{text-align:left;padding:.5rem .8rem;border-bottom:1px solid var(--line-soft);vertical-align:top}
thead th{background:var(--surface-2);font-size:.7rem;letter-spacing:.04em;text-transform:uppercase;color:var(--ink-mute);font-weight:600;position:sticky;top:0}
tbody tr:last-child td{border-bottom:0}
td.mono{font-family:var(--mono);font-size:.82em}
.pill{display:inline-flex;align-items:center;gap:.3em;font-family:var(--mono);font-size:.7rem;font-weight:700;padding:.1em .5em;border-radius:100px;white-space:nowrap}
.s-ok{color:var(--ok);background:var(--ok-wash)}.s-warn{color:var(--warn);background:var(--warn-wash)}.s-no{color:var(--no);background:var(--no-wash)}
.callout{border-left:3px solid var(--accent);background:var(--accent-wash);padding:.85rem 1.1rem;border-radius:0 10px 10px 0;font-size:.92rem;color:var(--ink-2);margin:1rem 0}
.callout b{color:var(--ink)}
.grp{font-family:var(--mono);font-size:.72rem;color:var(--accent-ink);font-weight:700;margin:1rem 0 .3rem;letter-spacing:.03em}
.foot{margin-top:2.6rem;padding-top:1.2rem;border-top:1px solid var(--line);font-size:.8rem;color:var(--ink-mute)}
details{margin:.5rem 0}summary{cursor:pointer;font-weight:600;color:var(--accent-ink);font-size:.92rem}
</style>"""


def esc(s): return html.escape(s or "")


def stat_cards(rows):
    c = Counter(r["ready_rule"] for r in rows)
    return f"""<div class="stats">
<div class="stat accent"><div class="n">143</div><div class="l">静态原生 test</div></div>
<div class="stat ok"><div class="n">{c['yes']}</div><div class="l">✅ 现成规则</div></div>
<div class="stat warn"><div class="n">{c['partial']}</div><div class="l">🟡 部分/需人工</div></div>
<div class="stat no"><div class="n">{c['no']}</div><div class="l">🔴 需专用工具</div></div>
</div>"""


def plat_table(rows, plat):
    """按 checklist 控制项（MASVS control）分组呈现。"""
    from collections import OrderedDict
    pr = [r for r in rows if r["platform"] == plat]
    groups = OrderedDict()
    for r in sorted(pr, key=lambda r: (r["masvs"], r["masvs_control"], r["id"])):
        groups.setdefault((r["masvs_control"], r["control_title"]), []).append(r)
    blocks = []
    for (ctrl, title), items in groups.items():
        rows_html = []
        for r in items:
            cls, lab = PILL[r["ready_rule"]]
            note = esc(r["gap_note"]) or ("mobsfscan/MASTG 规则覆盖" if r["ready_rule"] == "yes" else "")
            rows_html.append(f'<tr><td class="mono">{esc(r["id"])}</td><td>{esc(r["tier"])}</td>'
                             f'<td><span class="pill {cls}">{lab}</span></td>'
                             f'<td>{esc(r["title"])[:55]}</td><td>{note}</td></tr>')
        blocks.append(
            f'<div class="grp">☑️ {esc(ctrl)} — {esc(title)[:80]}</div>'
            f'<div class="tbl-wrap"><table><thead><tr><th>TEST</th><th>档位</th>'
            f'<th>现成规则</th><th>标题</th><th>说明/替代</th></tr></thead><tbody>'
            + "".join(rows_html) + '</tbody></table></div>')
    return (f'<details open><summary>{plat.upper()} 明细（{len(pr)} 条，按 checklist 控制项分组）</summary>'
            + "".join(blocks) + '</details>')


def main():
    with open(CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    tier = Counter(r["tier"] for r in rows)
    doc = f"""{CSS}
<div class="wrap"><div class="col">
<div class="eyebrow">DeGate · 安全 · MAS Checklist 静态自动化</div>
<h1>MAS Checklist 静态检查 · 自动化分类</h1>
<p class="lede">MASTG v2 的 143 个静态 test，逐条判定「能否用 semgrep/mobsfscan 自动化并进 GitHub CI」，并<b>对齐到 MAS Checklist 的具体控制项（MASVS control）</b>。<b>只针对原生代码（Swift/ObjC/Java/Kotlin），Dart 不在范围</b>——核心代码即原生代码。下方明细按 checklist 控制项分组，直接对应 checklist 里的每一条。</p>
<div class="meta"><span>范围 静态 × 原生</span><span>数据源 MASTG v2 tests-beta（201→静态143）</span><span>日期 2026-07-13</span></div>
<hr class="rule"/>
<h2>总览</h2>
{stat_cards(rows)}
<p>档位：可自动（纯静态）<b>{tier['auto']}</b> · 半自动（含 manual，工具初筛+人工确认）<b>{tier['semi']}</b>。</p>
<div class="callout"><b>一句话结论：</b>65/143 已有现成规则可直接进 CI；62 有工具但需人工确认（iOS ObjC 占多数，因 semgrep 不支持 ObjC，只能 mobsfscan libsast 正则）；16 属二进制/SCA 类，需 radare2/checksec/osv-scanner 等专用工具而非 semgrep。<b>静态原生检查绝大多数可进 GitHub CI</b>，无需 emulator。</div>
<h2>🔴 需专用工具的 16 项 + 替代方案</h2>
<h3>二进制编译加固（PIC / Stack Canary）· 二进制签名/符号/混淆</h3>
<p>语义扫描判不了编译产物属性。替代：<span class="k">checksec</span> / <span class="k">radare2</span> / <span class="k">otool</span> / <span class="k">nm</span> 对成品二进制核验，接 CI 构建后步骤。</p>
<h3>依赖漏洞 / 追踪域名（SCA）</h3>
<p>属软件成分分析，非代码模式。替代：<span class="k">osv-scanner</span> / GitHub Dependabot（原生依赖）+ 追踪域名黑名单比对。</p>
<div class="callout"><b>注意：</b>这 16 项虽不能用 semgrep 补规则，但对应工具都是 CLI、<b>同样可进 CI</b>，只是走二进制/SCA 轨道而非源码 SAST 轨道。</div>
<h2>GitHub Actions 可行性</h2>
<p>静态原生检查几乎全部可进 CI，比动态测试简单——SAST 容器化、普通 <span class="k">ubuntu-latest</span> runner 即可，<b>不需要 emulator/真机</b>。✅ 现成规则走 semgrep(MASTG rules+p/java+p/kotlin)+mobsfscan；🟡 部分走 mobsfscan(libsast) 做 PR 初筛+人工复核；🔴 二进制/SCA 各自独立 job。工程坑（P0 实测）：mobsfscan 多路径 bug 需逐目录跑；diff-aware 用 <span class="k">SEMGREP_BASELINE_REF</span> 只报新增。workflow 骨架见 <span class="k">github-actions-blueprint.yml</span>。</p>
<h2>分类明细</h2>
{plat_table(rows, 'android')}
{plat_table(rows, 'ios')}
<div class="foot">数据源 MASTG v2 <span class="k">tests-beta/</span>。完整数据 <span class="k">docs/security/mas-checklist/data/mas-static-classified.csv</span>。生成脚本 <span class="k">scripts/</span>（extract→enrich→annotate→gen）。范围：静态 × 原生代码，Dart 不在内。</div>
</div></div>"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"HTML 写出 → {OUT}")


if __name__ == "__main__":
    main()
