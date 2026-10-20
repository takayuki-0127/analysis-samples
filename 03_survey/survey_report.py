# アンケート分析の1枚レポート（公開データ：UCI Somerville Happiness Survey 2015・CC BY 4.0）
# クロス集計 → カイ二乗検定 → ロジスティック回帰（総合の満足＝幸福 を、6項目の評価で説明）→ 「どの層に何をすべきか」
import os, numpy as np, pandas as pd, statsmodels.formula.api as smf, matplotlib.pyplot as plt
from scipy.stats import chi2_contingency
from analysis_kit import NAVY, TEAL, ORANGE, INK, MUTED, _wrap
OUT = "out"; os.makedirs(OUT, exist_ok=True)
SRC = os.environ.get("SURVEY_CSV", "data/SomervilleHappinessSurvey2015.csv")
d = pd.read_csv(SRC, encoding="utf-16")          # 元ファイルは UTF-16
ITEMS = {"X1": "市のサービス情報の得やすさ", "X2": "住宅費", "X3": "公立学校の質", "X4": "地元警察への信頼", "X5": "道路・歩道の維持", "X6": "地域イベントの多さ"}
base = d.D.mean() * 100

# クロス集計＋カイ二乗検定（高評価＝4〜5 と、それ以外）
rows = []
for c, name in ITEMS.items():
    hi = (d[c] >= 4).astype(int); tab = pd.crosstab(hi, d.D); chi, p, _, _ = chi2_contingency(tab)
    rows.append(dict(項目=name, 高評価の割合=hi.mean() * 100, 平均=d[c].mean(), 低評価の幸福率=d.D[hi == 0].mean() * 100,
                     高評価の幸福率=d.D[hi == 1].mean() * 100, 低評価の人数=(hi == 0).sum(), p値=p))
ct = pd.DataFrame(rows).set_index("項目"); ct["差"] = ct.高評価の幸福率 - ct.低評価の幸福率
print(ct.round(3))
# ロジスティック回帰（6項目を同時に）
m = smf.logit("D ~ X1 + X2 + X3 + X4 + X5 + X6", data=d).fit(disp=0, cov_type="HC3")
OR = pd.DataFrame({"OR": np.exp(m.params), "lo": np.exp(m.conf_int()[0]), "hi": np.exp(m.conf_int()[1]), "p": m.pvalues}).drop("Intercept")
OR.index = [ITEMS[i] for i in OR.index]; print(OR.round(3), round(m.prsquared, 3))
corr = d[list(ITEMS)].corr()

# 図1：クロス集計（評価が低い人／高い人の「幸福」の割合）
c2 = ct.sort_values("差")
fig, ax = plt.subplots(figsize=(4.1, 3.0)); yy = np.arange(len(c2))
ax.barh(yy + .18, c2.低評価の幸福率, height=.34, color=MUTED, label="評価1〜3の人")
ax.barh(yy - .18, c2.高評価の幸福率, height=.34, color=TEAL, label="評価4〜5の人")
for yv, (_, r) in zip(yy, c2.iterrows()):
    mark = "＊" if r.p値 < 0.05 else ""
    ax.text(max(r.低評価の幸福率, r.高評価の幸福率) + 1.5, yv, f"{r.差:+.0f}pt{mark}", va="center", fontsize=7)
ax.set_yticks(yy); ax.set_yticklabels(c2.index, fontsize=7.5); ax.set_xlim(0, 112); ax.axvline(base, color=NAVY, ls="--", lw=.8)
ax.set_xlabel("「幸福」と答えた人の割合（%）　＊ p<0.05", fontsize=7.5); ax.legend(fontsize=7, loc="lower right")
ax.set_title("項目の評価別に見た「幸福」の割合", fontsize=9.5, weight="bold"); ax.grid(axis="x", alpha=.3); fig.tight_layout()
f1 = os.path.join(OUT, "fig1_crosstab.png"); fig.savefig(f1, dpi=160); plt.close(fig)

# 図2：6項目を同時に入れた回帰（評価1段階あたりのオッズ比）
o = OR.sort_values("OR")
fig, ax = plt.subplots(figsize=(4.1, 3.0)); yy = np.arange(len(o))
cols = [TEAL if lo > 1 else MUTED for lo in o.lo]
ax.errorbar(o.OR, yy, xerr=[o.OR - o.lo, o.hi - o.OR], fmt="none", ecolor=INK, lw=.9, capsize=2)
ax.scatter(o.OR, yy, color=cols, s=36, zorder=3); ax.axvline(1, color=INK, lw=.8)
for yv, (orv, hi) in zip(yy, zip(o.OR, o.hi)): ax.text(hi + .08, yv, f"×{orv:.2f}", va="center", fontsize=7)
ax.set_yticks(yy); ax.set_yticklabels(o.index, fontsize=7.5); ax.set_xlim(.3, 4.2)
ax.set_xlabel("評価が1段階高いときのオッズ比（95%信頼区間）", fontsize=7.5)
ax.set_title("6項目を同時に入れて比べると", fontsize=9.5, weight="bold"); ax.grid(axis="x", alpha=.3); fig.tight_layout()
f2 = os.path.join(OUT, "fig2_logit.png"); fig.savefig(f2, dpi=160); plt.close(fig)

r = lambda k: ct.loc[ITEMS[k]]
TXT = dict(
    title="アンケート分析レポート（サンプル）：満足を左右する項目はどれか",
    sub=f"公開データ：UCI「Somerville Happiness Survey」（米国の市民アンケート 2015年・CC BY 4.0）回答 {len(d)} 人・市のサービス6項目を5段階で評価",
    q=f"「総合的に満足（幸福）か」と、6つの項目の評価はどう結びついているか。どの層に、何をすべきか。全体では {base:.0f}% が「幸福」と回答した。",
    f=[f"クロス集計とカイ二乗検定：4項目で差があった。地域イベント（評価が高い人 {r('X6').高評価の幸福率:.0f}% ／低い人 {r('X6').低評価の幸福率:.0f}%）、情報の得やすさ（{r('X1').高評価の幸福率:.0f}%／{r('X1').低評価の幸福率:.0f}%）、学校（{r('X3').高評価の幸福率:.0f}%／{r('X3').低評価の幸福率:.0f}%）、道路（{r('X5').高評価の幸福率:.0f}%／{r('X5').低評価の幸福率:.0f}%）",
       f"6項目を同時に入れたロジスティック回帰では「情報の得やすさ」だけがはっきり残る（評価1段階ごとのオッズ比は {OR.loc[ITEMS['X1'],'OR']:.2f}、95%CI {OR.loc[ITEMS['X1'],'lo']:.2f}〜{OR.loc[ITEMS['X1'],'hi']:.2f}）。学校・道路・イベントは項目どうしが似た動きをする（相関0.2〜0.4）ので、どれが効いているかは分けきれない",
       f"住宅費は評価がいちばん低い（平均 {r('X2').平均:.1f}、高評価は {r('X2').高評価の割合:.0f}%）が、幸福とは差が見えない（{r('X2').高評価の幸福率:.0f}%／{r('X2').低評価の幸福率:.0f}%）"],
    act=[(f"「情報の得やすさ」を低く評価した層（{int(r('X1').低評価の人数)}人・幸福の割合 {r('X1').低評価の幸福率:.0f}%）に、サービスの案内をまとめて送る",
          "案内を届けた地区とまだの地区で、次回のアンケートの「幸福」の割合と情報の評価を比べる"),
         ("学校・道路・イベントは「どれを良くするか」を決める前に、次回の調査で分けて確かめる",
          "改善した項目が地区ごとに違うことを使って比べる。設問に「この1年で良くなったと感じる項目」を足す")],
    lim=[f"回答は {len(d)} 人・1回分の調査なので、差の信頼区間が広い。とくに回帰は人数が少なく、はっきりしない項目が多い",
         "関連（相関）であって原因とは限らない。もともと満足している人が、どの項目も高く付けている可能性がある",
         "住宅費は「不満が多いのに幸福と関連が見えない」項目。重要でないとは言えず、定住したいか などの別の設問で見るべき",
         "実案件（顧客満足度・従業員満足度の調査）でも、総合評価と項目評価があれば同じ形で出せる。属性（年代・利用歴など）があれば層を細かく分けられる"],
    meth="方法：各項目を「4〜5」と「1〜3」に分けたクロス集計とカイ二乗検定。6項目の評価を同時に入れたロジスティック回帰（頑健な標準誤差 HC3）で、1段階あたりのオッズ比と95%信頼区間を出した")

def report(path):
    fig = plt.figure(figsize=(8.27, 11.69))
    def T(xx, y, s, size=9.5, color=INK, weight="normal"): fig.text(xx, y, s, fontsize=size, color=color, weight=weight, va="top")
    def W(xx, y, s, n, size=9.2, color=INK, lh=.019, indent=""):
        lines = _wrap(s, n)
        for j, line in enumerate(lines): T(xx, y - j * lh, (indent if j else "") + line, size, color)
        return y - len(lines) * lh
    fig.patches.append(plt.Rectangle((0, .935), 1, .065, transform=fig.transFigure, color=NAVY, zorder=0))
    T(.05, .985, TXT["title"], 14, "white", "bold"); T(.05, .955, TXT["sub"], 8.1, "#cbd5e1")
    T(.05, .918, "問い", 12, NAVY, "bold"); y = W(.05, .893, TXT["q"], 56)
    y -= .012; T(.05, y, "わかったこと", 12, NAVY, "bold"); y -= .026
    for i, s in enumerate(TXT["f"], 1): y = W(.05, y, f"{i}. {s}", 57, 8.9, INK, .018, "   "); y -= .004
    for k, img in enumerate([f1, f2]):
        ax = fig.add_axes([.04 + k * .47, y - .235, .45, .23]); ax.imshow(plt.imread(img)); ax.axis("off")
    y -= .25; T(.05, y, "次の打ち手（優先順）", 12, NAVY, "bold"); y -= .026
    for i, (a, how) in enumerate(TXT["act"]):
        y = W(.05, y, f"{'①②'[i]} {a}", 50, 9.6, INK, .02, "   "); y = W(.08, y - .002, "確かめ方：" + how, 54, 8.8, MUTED); y -= .01
    T(.05, y, "前提と限界", 12, NAVY, "bold"); y -= .025
    for s in TXT["lim"]: y = W(.05, y, "・" + s, 57, 8.5, INK, .017, "   ")
    y -= .006; W(.05, y, TXT["meth"], 66, 7.6, MUTED, .015)
    fig.savefig(path); fig.savefig(path.replace(".pdf", ".png"), dpi=120); plt.close(fig)
report(os.path.join(OUT, "survey_1page.pdf"))
ct.round(4).to_csv(os.path.join(OUT, "crosstab_chi2.csv")); OR.round(4).to_csv(os.path.join(OUT, "logit_or.csv")); corr.round(3).to_csv(os.path.join(OUT, "item_corr.csv"))
print("ok")
