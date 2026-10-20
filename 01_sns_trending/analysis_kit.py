# -*- coding: utf-8 -*-
"""
副業用の分析テンプレート（SNS・YouTube などの「投稿ごとの数値」向け）
流れ：データの確認 → EDA（推移・分布・グループ比較）→ 仮説の検証（回帰・差の検定）→ 1枚レポート
受注したら load 部分だけ差し替える。入力は「1行＝1投稿」の表（日付・グループ・指標・説明変数）と、任意で日別の表
"""
import os, json, textwrap
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import statsmodels.formula.api as smf
from scipy import stats

NAVY, TEAL, ORANGE, INK, MUTED = "#0f2747", "#0d9488", "#ea6c1e", "#1f2937", "#64748b"
def setup_font():
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK-Regular" in f or "YuGothM" in f or "meiryo" in f.lower():
            font_manager.fontManager.addfont(f)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name(); return
setup_font()

def _wrap(s, n):
    """日本語向けの折り返し（空白で切らず、n 文字ごとに切る）"""
    return [s[i:i + n] for i in range(0, len(s), n)] or [""]


class Analysis:
    def __init__(self, posts, *, date, metric, group, metric_label=None, numeric=(), daily=None, daily_date=None,
                 daily_value=None, title="分析レポート", out_dir="out", log_metric=True):
        self.p = posts.copy(); self.date, self.metric, self.group = date, metric, group
        self.mlabel = metric_label or metric; self.numeric = list(numeric)
        self.daily, self.ddate, self.dval = daily, daily_date, daily_value
        self.title, self.out = title, out_dir; os.makedirs(out_dir, exist_ok=True)
        self.log_metric = log_metric; self.res = {}; self.figs = []
        self.p[date] = pd.to_datetime(self.p[date])

    # ---------- 1. データの確認 ----------
    def check(self):
        p = self.p
        info = {"件数": len(p), "期間": f"{p[self.date].min():%Y-%m-%d} 〜 {p[self.date].max():%Y-%m-%d}",
                "欠損（列：件数）": {c: int(n) for c, n in p.isna().sum().items() if n > 0},
                "グループ別の件数": p[self.group].value_counts().to_dict(),
                f"{self.mlabel}（中央値・平均・最大）": [float(p[self.metric].median()), round(float(p[self.metric].mean()), 1), float(p[self.metric].max())]}
        self.res["check"] = info
        return info

    # ---------- 2. EDA ----------
    def eda(self):
        p, g, m = self.p, self.group, self.metric
        groups = list(p[g].value_counts().index)
        colors = [TEAL, ORANGE, NAVY, MUTED][:len(groups)]
        # 推移
        fig, ax = plt.subplots(figsize=(8, 3.2))
        if self.daily is not None:
            d = self.daily.copy(); d[self.ddate] = pd.to_datetime(d[self.ddate]); d = d.sort_values(self.ddate)
            ax.plot(d[self.ddate], d[self.dval], color=MUTED, lw=1, label="日別")
            ax.plot(d[self.ddate], d[self.dval].rolling(7, min_periods=1).mean(), color=NAVY, lw=2, label="7日移動平均")
            ax.set_ylabel(self.dval)
        else:
            w = p.set_index(self.date).resample("W")[m].median()
            ax.plot(w.index, w.values, color=NAVY, marker="o"); ax.set_ylabel(f"{self.mlabel}（週の中央値）")
        ax.set_title("推移"); ax.legend(loc="upper left", fontsize=8); ax.grid(alpha=.3); fig.tight_layout()
        f1 = os.path.join(self.out, "fig1_trend.png"); fig.savefig(f1, dpi=150); plt.close(fig)
        # 分布＋グループ比較
        fig, axes = plt.subplots(1, 2, figsize=(8, 3.2))
        for gname, c in zip(groups, colors):
            v = p.loc[p[g] == gname, m]; v = v[v > 0]
            axes[0].hist(np.log10(v), bins=25, alpha=.6, color=c, label=f"{gname}（{len(v)}）")
        axes[0].set_xlabel(f"log10({self.mlabel})"); axes[0].set_title("分布"); axes[0].legend(fontsize=8)
        data = [p.loc[p[g] == gname, m] for gname in groups]
        axes[1].boxplot(data, labels=groups, showfliers=False)
        for i, (v, c) in enumerate(zip(data, colors), 1):
            axes[1].scatter(np.random.default_rng(0).normal(i, .05, len(v)), v, s=8, alpha=.5, color=c)
        axes[1].set_yscale("log"); axes[1].set_title("グループ比較"); axes[1].grid(axis="y", alpha=.3)
        fig.tight_layout(); f2 = os.path.join(self.out, "fig2_groups.png"); fig.savefig(f2, dpi=150); plt.close(fig)
        self.figs = [f1, f2]
        self.res["groups_median"] = p.groupby(g)[m].median().round(1).to_dict()
        return self.figs

    # ---------- 3. 仮説の検証 ----------
    def test(self, base_group=None):
        p, g, m = self.p.copy(), self.group, self.metric
        groups = list(p[g].value_counts().index); base = base_group or groups[0]
        p["_y"] = np.log(p[m].clip(lower=0) + 1) if self.log_metric else p[m]
        terms = [f'C({g}, Treatment(reference="{base}"))'] + self.numeric
        f = "_y ~ " + " + ".join(terms)
        mod = smf.ols(f, data=p.dropna(subset=self.numeric + [m])).fit(cov_type="HC3")
        ci = mod.conf_int(); rows = []
        for k in mod.params.index:
            if k == "Intercept": continue
            b, lo, hi = mod.params[k], ci.loc[k, 0], ci.loc[k, 1]
            name = k.split("[T.")[-1].rstrip("]") if "[T." in k else k
            rows.append(dict(要因=name, 倍率=np.exp(b) if self.log_metric else b, 下限=np.exp(lo) if self.log_metric else lo,
                             上限=np.exp(hi) if self.log_metric else hi, p値=mod.pvalues[k]))
        tab = pd.DataFrame(rows)
        # 差の検定（2グループ目 vs 基準）
        tests = []
        for gname in groups:
            if gname == base: continue
            a, b2 = p.loc[p[g] == gname, m], p.loc[p[g] == base, m]
            tests.append(dict(比較=f"{gname} vs {base}", 中央値=(float(a.median()), float(b2.median())),
                              マンホイットニーp=stats.mannwhitneyu(a, b2).pvalue))
        self.res.update(model=f, r2=mod.rsquared, n=int(mod.nobs), coef=tab, tests=tests, base=base)
        return tab, tests

    # ---------- 4. わかったこと → 次の打ち手 ----------
    def findings(self, actions=None, top=2, custom=None):
        """custom を渡すと、自動の文の代わりにそれを使う（案件の言葉で書き直したいとき）"""
        tab = self.res["coef"]; base = self.res["base"]; out = []
        sig = tab[tab["p値"] < 0.05].assign(d=lambda t: (np.log(t["倍率"])).abs()).sort_values("d", ascending=False)
        for _, r in sig.head(top).iterrows():
            unit = "（1増えるごと）" if r["要因"] in self.numeric else f"（{base}と比べて）"
            out.append(f"{r['要因']}{unit}：{self.mlabel}が約{r['倍率']:.2f}倍（95%信頼区間 {r['下限']:.2f}〜{r['上限']:.2f}倍）")
        ns = tab[tab["p値"] >= 0.05]["要因"].tolist()
        if ns: out.append("はっきりした差が見えなかったもの：" + "・".join(ns[:4]))
        self.res["findings"] = list(custom) if custom else out[:3]
        self.res["actions"] = actions or ["効いていた要因を増やした投稿を2〜4週続け、同じ比較で確かめる",
                                         "差が見えなかった要因は優先度を下げ、工数を効いた要因に回す",
                                         "変更した日（サムネイル・冒頭など）を記録し、前後で比べられるようにする"]
        return self.res["findings"], self.res["actions"]

    # ---------- 1枚レポート ----------
    def report(self, subtitle=""):
        fig = plt.figure(figsize=(8.27, 11.69))
        def T(x, y, s, size=10, color=INK, weight="normal"):
            fig.text(x, y, s, fontsize=size, color=color, weight=weight, va="top")
        fig.patches.append(plt.Rectangle((0, .935), 1, .065, transform=fig.transFigure, color=NAVY, zorder=0))
        T(.05, .985, self.title, 16, "white", "bold"); T(.05, .955, subtitle or f"対象：{self.res['check']['期間']}・{self.res['check']['件数']}件", 9, "#cbd5e1")
        T(.05, .915, "わかったこと", 13, NAVY, "bold")
        y = .885
        for i, s in enumerate(self.res["findings"], 1):
            for j, line in enumerate(_wrap(f"{i}. {s}", 46)):
                T(.05, y, ("   " if j else "") + line, 9.5); y -= .021
        for k, img in enumerate(self.figs):
            ax = fig.add_axes([.05, .56 - k * .2, .9, .19]); ax.imshow(plt.imread(img)); ax.axis("off")
        T(.05, .335, "次の打ち手（優先順）", 13, NAVY, "bold"); y = .305
        for i, s in enumerate(self.res["actions"], 1):
            for j, line in enumerate(_wrap(f"{'①②③'[i-1]} {s}", 46)):
                T(.05, y, ("   " if j else "") + line, 9.5); y -= .022
        T(.05, .2, "分析の方法", 13, NAVY, "bold")
        meth = [f"・回帰：{self.mlabel}を対数にした重回帰（{self.res['n']}件、決定係数 {self.res['r2']:.2f}、頑健な標準誤差 HC3）",
                "・差の検定：マン・ホイットニーの U 検定（外れ値に強い順位の比較）",
                "・相関であって原因とは限らない。原因を確かめるには、条件をそろえた比較（前後比較・A/B）が必要"]
        for i, s in enumerate(meth): T(.05, .17 - i * .024, s, 8.8, MUTED)
        pdf = os.path.join(self.out, "report_1page.pdf"); fig.savefig(pdf); fig.savefig(pdf.replace(".pdf", ".png"), dpi=110); plt.close(fig)
        # md でも残す
        md = [f"# {self.title}", "", "## データの確認", "```", json.dumps(self.res["check"], ensure_ascii=False, indent=1), "```",
              "## 回帰の結果", self.res["coef"].round(3).to_markdown(index=False), "", "## 差の検定",
              *[f"- {t['比較']}：中央値 {t['中央値'][0]:.0f} vs {t['中央値'][1]:.0f}、p={t['マンホイットニーp']:.4f}" for t in self.res["tests"]],
              "", "## わかったこと", *[f"- {s}" for s in self.res["findings"]], "", "## 次の打ち手", *[f"- {s}" for s in self.res["actions"]]]
        open(os.path.join(self.out, "report.md"), "w", encoding="utf-8").write("\n".join(md))
        return pdf
