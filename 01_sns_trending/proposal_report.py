# 要因分析の1枚レポート（仮説 → 検証 → 提案）：公開データ（YouTube 急上昇・日本・CC0）
import os, numpy as np, pandas as pd, statsmodels.formula.api as smf, matplotlib.pyplot as plt
from analysis_kit import NAVY, TEAL, ORANGE, INK, MUTED, _wrap   # 分析テンプレートの色・フォント・折り返しを使う
from prep import load
OUT = "out"; os.makedirs(OUT, exist_ok=True)
v = load()
FM = 'stay ~ like_pct + com_pct + bracket + num + q + ex + tlen + night + cd + lv0 + lag + C(cat, Treatment("エンタメ"))'
m = smf.logit(FM, data=v).fit(disp=0, cov_type="HC3")
OR = pd.DataFrame({"OR": np.exp(m.params), "lo": np.exp(m.conf_int()[0]), "hi": np.exp(m.conf_int()[1]), "p": m.pvalues})

# 平均限界効果（確率のポイント差）とブートストラップ 95%CI
CONTR = {"公開当日に急上昇入り（翌日入りと比べ）": ("lag", 1, 0), "タイトルが20字（40字と比べ）": ("tlen", 40, 20),
         "タイトルに「！」": ("ex", 0, 1), "タイトルに【】": ("bracket", 0, 1), "夜（18〜23時）公開": ("night", 0, 1),
         "初日のいいね率 5%（1%と比べ）": ("like_pct", 1, 5)}
def ames(model, data):
    return {k: (model.predict(data.assign(**{c: b})).mean() - model.predict(data.assign(**{c: a})).mean()) * 100 for k, (c, a, b) in CONTR.items()}
CACHE = os.path.join(OUT, "effects.csv")
if os.path.exists(CACHE):   # ブートストラップは数分かかるので、2回目以降は保存した結果を使う
    eff = pd.read_csv(CACHE, index_col=0)
else:
    est = ames(m, v); rng = np.random.default_rng(0); boot = []
    for _ in range(200):
        s = v.sample(len(v), replace=True, random_state=int(rng.integers(1e9)))
        boot.append(ames(smf.logit(FM, data=s).fit(disp=0), s))
    B = pd.DataFrame(boot); eff = pd.DataFrame({"pt": pd.Series(est), "lo": B.quantile(.025), "hi": B.quantile(.975)})
print(eff.round(1)); print(OR.round(3))
base = v.stay.mean() * 100

# 図1：仮説1（いいね率の5分位ごとの「翌日も残った割合」）
q = pd.qcut(v.like_pct, 5); g = v.groupby(q, observed=True).stay.agg(["mean", "size"])
lab = [f"{iv.left:.1f}〜{iv.right:.1f}%" for iv in g.index]; lab[0] = f"〜{g.index[0].right:.1f}%"; lab[-1] = f"{g.index[-1].left:.1f}%〜"
fig, ax = plt.subplots(figsize=(4.1, 3.0))
ax.bar(range(5), g["mean"] * 100, color=[MUTED] * 5); ax.axhline(base, color=NAVY, lw=1, ls="--")
for i, val in enumerate(g["mean"] * 100): ax.text(i, val + .6, f"{val:.0f}%", ha="center", fontsize=8)
ax.set_xticks(range(5)); ax.set_xticklabels(lab, fontsize=7); ax.set_ylim(0, 55)
ax.set_xlabel("初日のいいね率（5等分）", fontsize=8); ax.set_ylabel("翌日以降も急上昇に残った割合（%）", fontsize=8)
ax.set_title("仮説1：いいね率が高いほど残る？", fontsize=9.5, weight="bold"); ax.grid(axis="y", alpha=.3)
fig.tight_layout(); f1 = os.path.join(OUT, "fig1_h1.png"); fig.savefig(f1, dpi=160); plt.close(fig)

# 図2：条件をそろえた比較（ポイント差と 95%CI）
e = eff.iloc[::-1]
fig, ax = plt.subplots(figsize=(4.1, 3.0))
cols = [MUTED if (lo < 0 < hi) else (TEAL if pt > 0 else ORANGE) for pt, lo, hi in zip(e.pt, e.lo, e.hi)]
ax.barh(range(len(e)), e.pt, color=cols, height=.55)
ax.errorbar(e.pt, range(len(e)), xerr=[e.pt - e.lo, e.hi - e.pt], fmt="none", ecolor=INK, lw=.8, capsize=2)
for i, (pt, hi) in enumerate(zip(e.pt, e.hi)): ax.text(max(hi, 0) + .4, i, f"{pt:+.1f}pt", va="center", fontsize=7.5)
ax.set_yticks(range(len(e))); ax.set_yticklabels(e.index, fontsize=7); ax.axvline(0, color=INK, lw=.8)
ax.set_xlabel("残る確率の差（ポイント、95%信頼区間）", fontsize=8); ax.set_xlim(-6, 22)
ax.set_title("条件をそろえて比べると", fontsize=9.5, weight="bold"); ax.grid(axis="x", alpha=.3)
fig.tight_layout(); f2 = os.path.join(OUT, "fig2_effects.png"); fig.savefig(f2, dpi=160); plt.close(fig)

r = lambda k: eff.loc[k]
TXT = dict(
    title="「伸びが続く投稿」の要因分析レポート（サンプル）",
    sub=f"公開データ：Kaggle「Trending YouTube Video Statistics」日本・CC0／2018年2〜6月に急上昇に載った {len(v):,} 本",
    q="急上昇に載った動画のうち、翌日以降も載り続ける（＝伸びが続く）動画は、何が違うのか。"
      f"全体では {base:.0f}% が2日以上残った。",
    h=[("仮説1", "初日のいいね率が高い動画ほど、翌日以降も残る", "支持されず",
        f"いいね率だけで並べると少し高く見えるが、初日の再生数・カテゴリ・公開からの日数をそろえると差は消えた（5%と1%で {r('初日のいいね率 5%（1%と比べ）').pt:+.1f}pt、95%CI {r('初日のいいね率 5%（1%と比べ）').lo:+.1f}〜{r('初日のいいね率 5%（1%と比べ）').hi:+.1f}）"),
       ("仮説2", "タイトルの型（【】・！・短さ）で残りやすさが違う", "支持",
        f"【】あり {r('タイトルに【】').pt:+.1f}pt、！あり {r('タイトルに「！」').pt:+.1f}pt、20字のタイトルは40字より {r('タイトルが20字（40字と比べ）').pt:+.1f}pt。"
        f"ほかに見えたこと：いちばん差が大きいのは、公開当日に急上昇に入った動画（翌日入りより {r('公開当日に急上昇入り（翌日入りと比べ）').pt:+.1f}pt）＝初速の速さ")],
    act=[("タイトルを「【テーマ】＋短い本文＋！」の型にそろえる",
          "次の10本を「型あり」と「今まで通り」で交互に出し、翌日以降の再生の伸びを比べる（2〜4週間）"),
         ("いいね数を追うより、公開直後の初速づくりに工数を回す",
          "公開の告知（SNS・コミュニティ投稿）を公開から数時間以内に集中させ、当日の再生数を記録して比べる")],
    lim=["急上昇に載った動画だけのデータなので「載ったものの中での差」。載らなかった動画とは比べていない",
         "関連（相関）であって原因とは限らない。打ち手は、交互に出す比較で原因かどうかを確かめる前提",
         f"モデルで説明できる部分は小さい（疑似決定係数 {m.prsquared:.2f}）。残る・残らないの大半は中身やタイミングなどデータにない要因",
         "実案件では、自社の全投稿と公開後の指標（クリック率・視聴維持率）を足して同じ比較を行う"],
    meth=f"方法：「2日以上残ったか」をロジスティック回帰（{int(m.nobs):,} 本、頑健な標準誤差 HC3）。初日の再生数・カテゴリ・公開からの日数・公開時刻・コメント欄の有無をそろえ、"
         "差は平均限界効果（確率のポイント差）で示した。信頼区間はブートストラップ200回")

def report(path):
    fig = plt.figure(figsize=(8.27, 11.69))
    def T(x, y, s, size=9.5, color=INK, weight="normal"): fig.text(x, y, s, fontsize=size, color=color, weight=weight, va="top")
    def W(x, y, s, n, size=9.2, color=INK, lh=.019, indent=""):
        for j, line in enumerate(_wrap(s, n)): T(x, y - j * lh, (indent if j else "") + line, size, color)
        return y - len(_wrap(s, n)) * lh
    fig.patches.append(plt.Rectangle((0, .935), 1, .065, transform=fig.transFigure, color=NAVY, zorder=0))
    T(.05, .985, TXT["title"], 15, "white", "bold"); T(.05, .955, TXT["sub"], 8.3, "#cbd5e1")
    T(.05, .918, "問い", 12, NAVY, "bold"); y = W(.05, .893, TXT["q"], 56)
    y -= .012; T(.05, y, "仮説と検証の結果", 12, NAVY, "bold"); y -= .026
    for name, h, verdict, body in TXT["h"]:
        col = TEAL if verdict == "支持" else ORANGE
        fig.patches.append(plt.Rectangle((.05, y - .016), .085, .019, transform=fig.transFigure, color=col, zorder=0))
        T(.056, y - .001, verdict, 8.5, "white", "bold"); T(.145, y, f"{name}：{h}", 9.6, INK, "bold")
        y = W(.145, y - .022, body, 52, 8.8, INK); y -= .012
    for k, img in enumerate([f1, f2]):
        ax = fig.add_axes([.04 + k * .47, y - .235, .45, .23]); ax.imshow(plt.imread(img)); ax.axis("off")
    y -= .25; T(.05, y, "次の打ち手（優先順）", 12, NAVY, "bold"); y -= .026
    for i, (a, how) in enumerate(TXT["act"]):
        T(.05, y, f"{'①②'[i]} {a}", 9.8, INK, "bold"); y = W(.08, y - .021, "確かめ方：" + how, 54, 8.8, MUTED); y -= .01
    T(.05, y, "前提と限界", 12, NAVY, "bold"); y -= .025
    for s in TXT["lim"]: y = W(.05, y, "・" + s, 57, 8.5, INK, .017, "   ")
    y -= .006; W(.05, y, TXT["meth"], 66, 7.6, MUTED, .015)
    fig.savefig(path); fig.savefig(path.replace(".pdf", ".png"), dpi=120); plt.close(fig)
report(os.path.join(OUT, "proposal_1page.pdf"))
eff.round(2).to_csv(os.path.join(OUT, "effects.csv")); OR.round(4).to_csv(os.path.join(OUT, "odds_ratios.csv"))
print("ok")
