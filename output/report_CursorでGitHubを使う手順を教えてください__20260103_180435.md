# CursorでGitHubを使う手順を教えてください。

## レポート情報

- **作成日時**: 2026年01月03日 18:04:35
- **リサーチID**: 0f209faf-5143-4b38-bcd7-65b7d5bead84
- **イテレーション回数**: 5
- **収集データ数**: 23

## 調査計画

**テーマ**: CursorでGitHubを使う手順を教えてください。

**調査観点**:
- Cursorの基本的な使い方
- GitHubとの連携方法
- Cursorを使ったリポジトリのクローン方法
- Cursorでのコミットとプッシュの手順
- Cursorを使ったブランチ管理

**検索クエリ**:
- How to use Cursor with GitHub
- CursorとGitHubの連携方法
- Cursorでリポジトリをクローンする方法
- Cursorでのコミットとプッシュの手順
- Cursorを使ったブランチ管理

---

# CursorでGitHubを使う手順

## エグゼクティブサマリー
CursorはAIを活用したコードエディタで、GitHubとの連携により開発効率を大幅に向上させることができます。本レポートでは、Cursorの基本的な使い方からGitHubとの連携方法、リポジトリのクローン、コミットとプッシュの手順、ブランチ管理までを詳しく解説します。Cursorを利用することで、複数のデバイス間でのコード共有や変更の自動保存が可能となり、チームでの協力作業がよりスムーズになります。これにより、開発者はコードの管理とバージョン管理を効率的に行うことができ、プロジェクトの進行を加速させることができます。

## 主要な発見
- CursorはAIを活用したコードエディタで、GitHubとの連携が可能である[^1][^2]。
- GitHubとの連携には、パーソナルアクセストークンの生成が必要[^1]。
- リポジトリのクローンはCursorのターミナルから簡単に行える[^11]。
- コミットとプッシュはCursorのGUIを使って直感的に操作可能[^6]。
- ブランチ管理はCursorのエージェント機能を活用して効率化できる[^18]。

## 詳細な分析

### Cursorの基本的な使い方
CursorはAIを搭載したコードエディタで、開発者の生産性を向上させるために設計されています。Cursorを使用することで、コードの自動補完やエラーチェックが容易になり、開発プロセスが効率化されます[^6]。

### GitHubとの連携方法
GitHubとCursorを連携するためには、GitHubでパーソナルアクセストークンを生成し、Cursorに設定する必要があります。これにより、Cursorから直接GitHubのリポジトリにアクセスし、操作することが可能になります[^1][^7]。

### Cursorを使ったリポジトリのクローン方法
Cursorのターミナルを使用して、GitHubからリポジトリをクローンすることができます。具体的には、`git clone`コマンドを使用し、リポジトリのSSH URLを指定することで、ローカル環境にリポジトリを取り込むことができます[^11]。

### Cursorでのコミットとプッシュの手順
Cursorでは、GUIを通じてコミットとプッシュを行うことができます。ファイルを編集した後、変更をステージし、コミットメッセージを入力してコミットを実行します。その後、プッシュボタンをクリックすることで、リモートリポジトリに変更を反映させることができます[^6][^17]。

### Cursorを使ったブランチ管理
Cursorのエージェント機能を活用することで、ブランチ管理を効率化することができます。作業ブランチとベースブランチを区別し、必要に応じて新しいブランチを作成する提案を行うことができます。また、危険な操作には二重確認を行うことで、プロジェクトの安全性を確保します[^18].

## 参考文献
[^1]: https://blog.codacy.com/how-to-connect-cursor-to-github-and-codacy-mcp-servers-and-supercharge-your-application-security
[^2]: https://cursor.com/docs/integrations/github
[^6]: https://note.com/techsenichiya/n/n0a85133a747f
[^7]: https://zenn.dev/shiaf/articles/6526b4a17c1d73
[^11]: https://note.com/blog_hideyuki/n/n4d985141baac
[^17]: https://note.com/aisha_feline29/n/nc87a6933184f
[^18]: https://qiita.com/kaisumi/items/707318aeb68d082be8ca

---

## 参照ソース

1. **How to Connect Cursor to GitHub and Codacy MCP Servers and ...**
   - URL: https://blog.codacy.com/how-to-connect-cursor-to-github-and-codacy-mcp-servers-and-supercharge-your-application-security
   - 要約: As you can see, you’ll need to generate a personal access token in GitHub, which you’ll need to access GitHub’s API from your AI agent. Sign in to your GitHub account, click on your profile picture (i...
   - 関連性スコア: 0.84

2. **GitHub | Cursor Docs**
   - URL: https://cursor.com/docs/integrations/github
   - 要約: Building an MCP Server
Web Development
Data Science
Large Codebases
Mermaid Diagrams
Using Bugbot rules

## Troubleshooting

Common Issues
Getting a Request ID
Troubleshooting Guide
Downloads

Integra...
   - 関連性スコア: 0.82

3. **how I setup cursor with github and host for free with cloudflare**
   - URL: https://www.youtube.com/watch?v=shGWV34l4oc
   - 要約: you log in onto your cursor account on cursor what you usually have is you want to open a folder that contains your project files for example usually it's in your GitHub folder um and then uh you have...
   - 関連性スコア: 0.74

4. **Cursor System Instruction - GitHub Gist**
   - URL: https://gist.github.com/aashari/e1ee8f8817c3cccc271d59d62d0f7c75
   - 要約: 1. Unless explicitly requested by the USER, use the best suited external APIs and packages to solve the task. There is no need to ask the USER for permission.
2. When selecting which version of an API...
   - 関連性スコア: 0.74

5. **PatrickJS/awesome-cursorrules - GitHub**
   - URL: https://github.com/PatrickJS/awesome-cursorrules
   - 要約: 1. Install Cursor AI if you haven't already.
2. Browse the rules above to find a `.cursorrules` file that suits your needs.
3. Copy the chosen `.cursorrules` file to your project's root directory.
4. ...
   - 関連性スコア: 0.73

6. **【Cursor入門15】GitHubと連携してリモートリポジトリを作る - note**
   - URL: https://note.com/techsenichiya/n/n0a85133a747f
   - 要約: Cursorで連携する場合は、この後「Visual Studio Codeで認証」という画面が出てきますが、そのまま進めて問題ありません。  
そして生体認証の設定を済ませると……

認証が完了しました！  
これで、CursorとGitHubの連携が完了したことになります。

### リモートリポジトリの作成

連携ができたので、早速GitHubでリモートリポジトリを作成してみましょう。

Gi...
   - 関連性スコア: 1.00

7. **Cursor で GitHub 操作を効率化する方法 - GitHub MCP Server ... - Zenn**
   - URL: https://zenn.dev/shiaf/articles/6526b4a17c1d73
   - 要約: ### 2. Cursor に MCP サーバーを追加する

`env GITHUB_PERSONAL_ACCESS_TOKEN=<your-token> npx -y @modelcontextprotocol/server-github`

※ `<your-token>` の部分に先ほど作成した PAT を入力します

`<your-token>`

### 3. 動作確認

設定が完了した...
   - 関連性スコア: 1.00

8. **【非エンジニア向け】CursorとGitHubを連携方法を超わかりやすく ...**
   - URL: https://note.com/honest_murre3556/n/nb5d2264e1d56
   - 要約: ◆一例  
・Cursorでコードを書く  
・変更をGitHubに自動保存  
・複数のデバイスで同じコードを編集  
・チームメンバーとコードを共有

CursorとGitHubの連携は、最初は少し複雑に感じるかもしれませんが、  
一度設定してしまえば非常に便利です。

プログラミングの世界では、コードの管理は必須スキルです。この連携をマスターすることで、より効率的にプログラミングを学べるよ...
   - 関連性スコア: 1.00

9. **CursorとGitHubを連携した業務管理方法に関するハンズオンを ...**
   - URL: https://qiita.com/miyayama-n/items/a823acf4ac57eadba0ff
   - 要約: この機能により、Cursor上で特定のコマンド（`/create-issue`など）を実行するだけで、以下の処理を自動で実行できます：

`/create-issue`

#### 実装のポイント

`.cursor/rules/add-github-issue.mdc`にルールを定義することで、GitHub CLIを使った一連の操作を自動化しました。特に以下の点に注意しました： [...] `....
   - 関連性スコア: 1.00

10. **Cursorを使うならGitも同時に**
   - URL: https://python-engineer.co.jp/cursor-for-git/
   - 要約: Cursor のセーブポイントを作るために Git を使う
 Git のインストール方法
  + Windows
  + Mac
  + Git の初期設定
 GitHub にも登録しておく
 レポジトリの作成
  + ソース管理しないファイル・フォルダを設定する
  + 2 種類のセーブポイント
 ステージ〜コミットまで
 変更を元に戻す 2 つの方法
  + ステージされているものを元に戻す
...
   - 関連性スコア: 1.00

11. **初心者向けCursor AIエディタ初期設定マニュアル（Windows ... - note**
   - URL: https://note.com/blog_hideyuki/n/n4d985141baac
   - 要約: リポジトリをクローンする – Cursor で `Ctrl + ``（バッククオート）を押してターミナルを開き、以下のコマンドでリポジトリをクローンします。SSH URL は GitHub のリポジトリページの "Code" ボタン → "SSH" から取得します。

bash

プロジェクトを開く – Cursor メニューの File > Open Folder… からクローンしたフォルダを開...
   - 関連性スコア: 0.93

12. **「GitHubって難しい…」から実践へ！CursorでGitHub使ったら楽に ...**
   - URL: https://note.com/itella/n/nf12ab15412dd
   - 要約: # 

itella%22%20d%3D%22M-100-100h300v300h-300z%22%2F%3E%3C%2Fsvg%3E)
見出し画像

# 「GitHubって難しい…」から実践へ！CursorでGitHub使ったら楽になった話駆け出しエンジニアの備忘録②

itella%22%20d%3D%22M-100-100h300v300h-300z%22%2F%3E%3C%2Fsvg%3E...
   - 関連性スコア: 0.84

13. **Cursor × GitHub × Zenn/Qiitaで、学びを効率よく残す**
   - URL: https://zenn.dev/headwaters/articles/20240614-new-article
   - 要約: 実は元々この「GithubによってZenn&Qiitaの記事を管理する方法」というテーマで、今回記事を書くつもりでした。  
ただ調べていただくとわかるのですが、同様の解説記事がすでにたくさんあったので、ここでは参考になる記事を共有するのみにしたいと思います。  
以下の記事でGitHubでの記事管理方法を網羅的に理解できますので、各種インストールや連携を進めてください。

# Cursorでの記...
   - 関連性スコア: 0.81

14. **非エンジニア組織のCursor&Git/GitHub活用〜AIと一緒に作る ...**
   - URL: https://note.com/sakamototakuma/n/n7f22e1060dd0
   - 要約: Git/GitHub用語を身近な例えで理解する · 1. リポジトリ（Repository） · 2. クローン（Clone） · 3. コミット（Commit） · 4. プッシュ（Push） · 5. プル（Pull） · 6.
   - 関連性スコア: 0.32

15. **CursorでCursorRulesをCursor自身でうまく管理してもらう ...**
   - URL: https://qiita.com/yousan/items/b6b7ef0ac8313ba06a7a
   - 要約: あとはCursorRulesフロントマター自体を編集させようとしてもうまくいかないようです。

## さいごに

このRuleファイルを使ったプロジェクトのリポジトリは下記で公開しています。

フロントはReactベースのRefineフレームワークを使い、Vite、Antを指定しています。  
バックエンドとインフラはSupabaseです。

それぞれ専用のRuleファイルを用意していて背景ファイ...
   - 関連性スコア: 0.25

16. **Cursorエージェント機能でファイル・フォルダを作成してGitHubに ...**
   - URL: https://zenn.dev/sento_group/articles/cursor-agent-file-management-github-guide
   - 要約: `.cursor/rules/sync.mdc`
`「@sync」`

このコマンドで、未コミットの変更を自動的にコミット・pushしてくれます。

## Step 5: 実際の使用例

### 例1: 新しい記事の作成とpush

指示：

`「articlesフォルダに、CursorとGitの連携方法を説明する記事を書いて。作成したらGitに追加してコミットしてGitHubにpushして」`
...
   - 関連性スコア: 0.85

17. **Git × GitHub ： ローカル保存〜初pushまでの手順完全ガイド｜Aisha**
   - URL: https://note.com/aisha_feline29/n/nc87a6933184f
   - 要約: なお、「git add」や「git commit -m」といったコマンドは、Cursor上ではすべてボタン操作で実行可能です。  
この記事では学習の一環としてコマンドを扱いますが、Cursorのようなエディタを使うのであれば、実際の操作では手打ちの必要はないことも補足しておきます。

## ローカルで編集・初期設定

### ① テキストファイルをローカルで作成・保存

この時点ではGitとは無...
   - 関連性スコア: 0.75

18. **Cursorの賢い使い方を学ぶ#1 - Qiita**
   - URL: https://qiita.com/kaisumi/items/707318aeb68d082be8ca
   - 要約: `## Git操作に関するガイドライン
Cursor AgentがGit操作を行う際には、以下の点を厳守してください：
1. 作業ブランチ vs ベースブランチの区別がつかない前提で動作する
 - Agentは、今いるブランチが「main」「develop」などのベースブランチであるか、「feature/」などの作業用ブランチであるかを判断できません。
 - したがって、Agentが変更を検知した...
   - 関連性スコア: 0.71

19. **コーディングエージェントのカスタムコマンドでGit操作を効率化**
   - URL: https://kakehashi-dev.hatenablog.com/entry/2025/11/27/110000
   - 要約: Cursorの「コマンド」とは再利用可能なプロンプト定義です。チャットウィンドウでスラッシュを入力すると呼び出せます。Cursorに限らず、他のAIエージェントにもコマンド機能はありますね。

Cursorの場合は `.cursor/commands` ディレクトリにコマンド用のマークダウンファイルを置くことで、そのプロジェクトのコマンドとして利用できます。また、 `~/.cursor/comma...
   - 関連性スコア: 0.68

20. **Cursor使ってみてます**
   - URL: https://tech.unifa-e.com/entry/2025/10/16/112756
   - 要約: 例えばapiサーバのリポジトリであれば「このapiのxxxという機能を追加してほしい。機能を追加したらテストを追加し、rspecを流してほしい。」というようなものを出している。リポジトリの関係性を表すようなものを共通でどのwindowでも参照できるように用意できれば該当リポジトリではこれをやる、ということを自動で出してもらえるかもしれないが、まだこの部分は検証もできてないので今進行中のことの結果を...
   - 関連性スコア: 0.71

21. **Cursor × iOS開発 私はこうやってます - every Tech Blog**
   - URL: https://tech.every.tv/?page=1752195600
   - 要約: デフォルトは 20 分ですが、0 に設定するとタイムアウトを無効化できます。

### ベースブランチの選択

レビュー時に比較対象となるブランチを手動で選択できます。デフォルトでは現在のブランチの親ブランチが自動選択されますが、任意のローカルブランチを選択可能です。

サイドバーに現在のブランチと比較対象のブランチが表示され、クリックすることで変更できます。

### レビューの実行状況

レビ...
   - 関連性スコア: 0.57

22. **Git Worktreeで複数ブランチを同時に扱う #cursor**
   - URL: https://qiita.com/generokenken/items/34f3f0ea5fdd78033dc1
   - 要約: `# Worktreeを使った解決策
# AIと一緒に大規模リファクタリング中...
~/myapp-refactor (feature/refactoring)
# 緊急バグ報告が入る
git worktree add ../myapp-hotfix hotfix/critical-bug
# 既存のウィンドウを残した状態で新しいウィンドウでhotfixを開くことができる
# ✅ リファクタリン...
   - 関連性スコア: 0.56

23. **最強神器「Cursor」の本当に使い方を徹底解説【知らないとヤバ ...**
   - URL: https://zenn.dev/aimasaou/articles/f9b19ca901a0cd
   - 要約: プロジェクト規模が非常に大きい場合、インデックス化に時間がかかる  
AIが誤解をもとにコードを修正してしまうリスクがあります。

引数やクラス構造の変更を一気にやりすぎると破壊的変更になりかねない  
とはいえ、適切なガードレール（Git管理、CI/CDでのテスト/ドキュメント化など）を設ければ、デメリットよりも得られるメリットのほうが圧倒的に大きいでしょう。

## 6. 実際の運用ノウハウ
...
   - 関連性スコア: 0.55

