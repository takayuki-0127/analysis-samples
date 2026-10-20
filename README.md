# analysis-samples：公開データで作った分析サンプル3本（仮説 → 分析 → 提案の1枚レポート）

SNS・EC・アンケートの3分野で、「問い → 仮説 → 検証 → 次の打ち手（確かめ方つき）→ 前提と限界」を A4 1枚にまとめたサンプルです。
**すべて公開データだけで作っています。クライアントのデータは含みません。**

![分析実績の一覧](analysis_samples_overview.png)

一覧の PDF：[analysis_samples_overview.pdf](analysis_samples_overview.pdf)

| フォルダ | 分野・問い | 手法 | 1枚レポート |
|---|---|---|---|
| [01_sns_trending](01_sns_trending) | SNS・動画：「伸びが続く投稿」は何が違うか（YouTube 急上昇・日本・11,808本） | ロジスティック回帰・平均限界効果・ブートストラップ | [PDF](01_sns_trending/out/proposal_1page.pdf) |
| [02_ec_retail](02_ec_retail) | EC：どの顧客層に何をすべきか（英国のネット通販・顧客4,338人） | RFM 分析・月別コホートの継続率 | [PDF](02_ec_retail/out/ec_1page.pdf) |
| [03_survey](03_survey) | アンケート：満足を左右する項目はどれか（市民アンケート・143人） | クロス集計・カイ二乗検定・ロジスティック回帰 | [PDF](03_survey/out/survey_1page.pdf) |

## データとライセンス
- 01：Kaggle「Trending YouTube Video Statistics」（datasnaek/youtube-new）日本分・CC0。元データは同梱していない
- 02：UCI Machine Learning Repository「Online Retail」・CC BY 4.0（https://archive.ics.uci.edu/dataset/352/online+retail）。元データは同梱していない
- 03：UCI Machine Learning Repository「Somerville Happiness Survey」・CC BY 4.0（Koczkodaj, W. (2017). https://doi.org/10.24432/C5PW36）。CSV（4KB）を同梱

## 書き方の約束
- 結果は関連（相関）で、原因とは限らない。打ち手は「比べて確かめる」方法とセットで出す
- 人数・期間・データの偏りなどの限界を、レポートの中に必ず書く

## 使っている道具
Python（pandas・statsmodels・scipy・matplotlib）。共通の色・フォント・日本語の折り返しは `analysis_kit.py`

作成：2026-10-20　松浦 孝征（https://github.com/takayuki-0127）
