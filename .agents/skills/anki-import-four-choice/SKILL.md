---
name: anki-import-four-choice
description: 教材やメモから、正答が1つの4択問題をすべてのカードにしてAnkiインポートTXTを作成する。四択・選択問題を明示的に求められたときに使い、一問一答形式には使わない。
---

# Anki 4択インポートファイルの作成

入力資料に基づき、すべてのカードを正答が1つの4択問題にして、Ankiに読み込めるUTF-8の`.txt`ファイルを作る。ユーザーがサンプルや対象教材のAnkiエクスポートを渡した場合は、書式と既存GUIDの扱いを確認する。

## 教材フォルダの読み取り先と出力先

リポジトリの`target-folder/`直下に試験ごとのフォルダがある場合、選択した試験フォルダ（`target-folder/<試験slug>/`）を基準に標準構成を使う。ユーザーが`target-folder/`だけを指定した場合は依頼された試験に一致するフォルダを選び、見つからない、または候補が複数ある場合は確認する。試験フォルダや個別ファイルが明示された場合はその指定を優先する。

- 読み込む学習メモ：`input/`内の、依頼された章・範囲に該当するファイル。
- 参照資料：必要に応じて`Reference/`内の教材PDFなど。
- 試験範囲資料：`Exam-Guide/`があり、ガイドラインや試験ドメイン資料が置かれている場合に読む。未配置でも作業を続ける。
- 出力先：`output/`。なければ作成する。
- 問題作成済み資料:`Done/`問題作成済みのinput資料。

ここに記載した各フォルダ名は、すべて選択した試験フォルダからの相対パスである。Skill、生成ファイル、実行報告にマシン固有の絶対パス、ユーザー名、ホームディレクトリを含めず、報告では試験フォルダまたはリポジトリルートからの相対パスを使う。

Exam-Guideがある場合は、試験範囲・ドメイン（Domain）・タスク（Task）・スキル（Skill）・対象技術（In-scope/Out-of-scope）・試験対象者像（Target candidate）を把握し、それに沿った出題設計を行う。回答の事実関係や解説は学習メモとReferenceの正確な記述に基づけ、Exam-Guideに項目があっても教材にない事実や仕様を推測・捏造して作らない。章番号がファイル名に表れていない場合は、ファイル内容から対象範囲を確かめ、特定できないときだけユーザーに確認する。`output/`の既存カードTXTや`用語集.md`を入力メモとして読み込まない。

この構成で用語集を作成・更新する場合は、`output/用語集.md`に保存する。略語ごとに正式な英語フルスペルと日本語表記・意味を記載する。

## 問題作成

### Exam-Guideに沿った4択問題作成（Exam-Guideがある場合）

`Exam-Guide/`が存在する場合は、実際の試験形式・評価観点に即した4択問題を設計する：

- **試験のペルソナと出題趣旨への適合**:
  - Exam-Guideに定義されている対象者像（Target candidate）や前提知識（例: ビジネス意思決定者向け、アーキテクト向け、運用者向け等）に合わせ、設問の難易度や問う深さを調整する。
  - コードや細かい内部パラメータの丸暗記ではなく、Exam-Guideのタスクで求められる「ビジネス要件・制約条件に応じた最適なAIソリューションや手法の選定」「トレードオフの評価」「リスク軽減策やガバナンス対応」などの実務的な判断・状況判断を問うシナリオ型設問を積極的に取り入れる。
- **タスク・スキルの網羅と客観的設問**:
  - 対象資料の内容が対応するExam-Guideのタスク（Task）およびスキル（Skill）を特定し、そのスキルで検証される観点を直接問う。
  - 「教材で紹介されている〜」「テキストの記述として〜」などの内向き表現を排除し、試験本番と同様の客観的で実務的な設問文にする（例:「ある企業が〜を目的としてAIを導入しようとしている。この要件に最も適したアプローチはどれか」など）。
- **誤答（ディストラクター）の設計**:
  - 誤答の選択肢には、Exam-Guideの試験範囲内にある関連概念、他サービス、別アプローチを採用する。
  - Exam-Guideで区別が求められている概念同士（例: ルールベース vs 機械学習、RAG vs ファインチューニング、リアルタイム推論 vs バッチ推論など）を対比させ、試験が要求する正確な識別力と判断力を試す選択肢構成にする。
  - あからさまに無関係な選択肢やナンセンスな誤答ではなく、別のユースケースでは正解になり得るもっともらしい選択肢（ディストラクター）を用意する。
- **スコープと優先度**:
  - Exam-GuideのIn-scopeなコア技術・概念を優先して出題する。Exam-GuideでOut-of-scopeと指定されている事項や、出題意図から逸脱する重箱の隅の暗記は除外または優先度を下げる。
- **事実の根拠**:
  - 正答・誤答の記述、および裏面の解説は、必ず校正済み学習メモとReferenceの内容に基づく。資料にない事実や架空の機能を創作しない。

### 一般要件

- 正答は資料の記述に合わせる。選択肢の事実を資料外から作らない。
- 誤答は資料にある関連概念・用語・工程・サービスの役割を取り違えるなど、資料内の情報を使って作る。誤答を3つ用意しにくい場合は、資料内の近接概念が選択肢になるように設問を言い換えるか、論点を分ける。一問一答へ戻さない。
- 各カードの選択肢は重複のない4つ、正答は1つにする。問題文で単一選択であることを明らかにし、選択肢は同じ種類・粒度にそろえる。
- Question/Answerという見出しを表示する`question-header`・`answer-header`の`<div>`は作らない。
- 裏面には正答と、資料が説明を含む場合は短い理由・補足を置く。正答が複数の要素・手順・比較項目から成る場合は、HTMLの箇条書き（`<ul><li>...</li></ul>`）にして、項目ごとに1行で示す。例として「モデルの大規模化」「学習データの大規模化」「計算リソースの進化」のような複数要素は、1つの文に詰めず別々の箇条書きにする。
- Answerの説明文は1文ごとに独立した`<div>`に分け、複数の文を同じ段落に連結しない。
- 問題文・4つの選択肢・Answerのいずれかに略語が出る場合は、Answerの最後にフルスペル一覧を置く。`<div><strong>略語のフルスペル：</strong></div>`の後に`<ul class="abbreviation-expansions"><li>EDA = Exploratory Data Analysis（探索的データ分析）</li></ul>`の形式で、略語ごとに1つの箇条書き項目として、省略しない正式な英語表記を記載する。必要に応じて日本語訳も添える。正式名称が不明・複数ある場合は資料の意味に合わせ、推測で断定しない。
- 用語集を作成・更新する場合は、略語ごとに正式な英語表記と日本語表記・意味を記載する。AvroやParquetのような固有名は、略語でなければ無理に展開しない。
- HTML本文の文字は必要に応じてHTMLエスケープする。画像は提供資料に含まれるファイルだけ参照し、必要な配置を案内する。

## AnkiのノートID（GUID）

- AnkiのGUIDはカード面に表示する番号ではなく、ノートを識別するメタデータである。TXTでは先頭列をGUIDにし、ヘッダーに`#guid column:1`を記載する。その後ろにAnkiの表・裏フィールドを並べる。
- 新規ノート用GUIDはAnki本体と同じBase91形式で生成する。64ビット乱数を`abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&()*+,-./:;<=>?@[]^_`{|}~`の文字表でBase91エンコードし、ゼロ値を避ける。GUID列はカード本文へ埋め込まない。
- 既存ノートを更新するときは、ユーザーが指定したAnkiエクスポートの対象GUIDをそのまま保持し、`#guid column`と列順も元ファイルに合わせる。GUIDを変更すると別ノートとして扱われる。
- 教材フォルダ構成では`output/`の同形式・同範囲ファイルを照合し、再生成時に同じノートだと確実に判断できるカードはGUIDを維持する。新規ノートだけに新しいGUIDを割り当て、既存GUIDの再利用や重複を避ける。
- 既存ノートの再生成・更新で過去の`output/`ファイルもGUID付きAnkiエクスポートもない場合は、そのノートの更新を止めて対応ファイルを求める。新しいGUIDで更新を代用しない。
- 新規カードとGUID付きの既存ノート更新が混在する場合は、誤対応を避けるため別ファイルに分ける。

## Anki TXT形式

- 先頭3行は`#separator:tab`、`#html:true`、`#guid column:1`。列名行は追加しない。
- 各ノートの物理列は「GUID」「表」「裏」の3列で、Ankiノート自体のフィールドは表・裏の2つ。各値を二重引用符で囲み、フィールド内の`"`は`""`にする。フィールド内の改行は引用符の内側に保つ。
- 表は次のラッパーを使い、選択肢を`<ol class="anki-shuffle">`内に4つの`<li>`で記述する。AnkiのJavaScript動作はクライアントによって異なるため、選択肢のシャッフルが必要な場合だけ、下記スクリプトを表フィールドの先頭に含める。
- 裏は`<div class="answer">...正答と補足...</div>`で包む。複数項目の正答と略語一覧は箇条書き、説明文は1文ごとに別のブロックにする。略語一覧はAnswer内の最後に置く。
- Ankiのタグ用フィールドは追加しない。1ノートを1つのTSVレコードにして、全ノートを1ファイルにまとめる。

```html
<script>
(function () {
  var question = document.querySelector(".question");
  var list = question && question.querySelector("ol.anki-shuffle");
  if (!list) return;
  var questionText = question.cloneNode(true);
  var clonedList = questionText.querySelector("ol.anki-shuffle");
  if (clonedList && clonedList.parentNode) clonedList.parentNode.removeChild(clonedList);
  var stem = questionText.textContent || questionText.innerText || "";
  stem = stem.replace(/\s+/g, " ").replace(/^\s+|\s+$/g, "");
  var optionMarkup = [];
  for (var i = 0; i < list.children.length; i++) optionMarkup.push(list.children[i].outerHTML);
  var key = stem + "\n" + JSON.stringify(optionMarkup.slice().sort());
  var state = window.__ankiOptionShuffleState;
  if (document.querySelector(".answer")) {
    if (state && state.key === key) list.innerHTML = state.html;
    return;
  }
  if (state && state.key === key) {
    list.innerHTML = state.html;
    return;
  }
  var shuffledOptions = Array.prototype.slice.call(list.children);
  for (var j = shuffledOptions.length - 1; j > 0; j--) {
    var swapIndex = Math.floor(Math.random() * (j + 1));
    var temporary = shuffledOptions[j];
    shuffledOptions[j] = shuffledOptions[swapIndex];
    shuffledOptions[swapIndex] = temporary;
  }
  for (var k = 0; k < shuffledOptions.length; k++) list.appendChild(shuffledOptions[k]);
  window.__ankiOptionShuffleState = { key: key, html: list.innerHTML };
})();
</script>
<div class="tags">
</div>
<div class="question">
<div>問題文</div>
<ol class="anki-shuffle">
<li>選択肢1</li>
<li>選択肢2</li>
<li>選択肢3</li>
<li>選択肢4</li>
</ol>
</div>
```

## 完成前の確認

- TSVとして読み戻し、ヘッダーが正しいこと、全レコードがGUID列を含む3物理列であり、GUIDが重複しないことを確認する。
- 各カードの選択肢が重複のない4つであること、正答がちょうど1つ含まれることを確認する。
- 出力先に保存し、ファイルパスとカード数を伝える。

試験フォルダ構成を使う場合、`output/`に`<試験slug>_<章・範囲>_4択_<YYYYMMDD-HHmmss-fff>_Anki.txt`として保存する。日時はローカル時刻で、同じ範囲の出力間でも時系列を判定できる精度で付ける。構成がない場合はユーザー指定の出力先を優先し、指定がなければ入力ファイルのフォルダに同様の日時付きファイル名で保存する。出力ファイルの相対パスとカード数を伝える。
