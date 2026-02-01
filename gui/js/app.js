/**
 * メインアプリケーション
 * 状態管理、イベントハンドリング、リサーチ監視を担当
 */

class App {
    constructor() {
        this.currentResearchId = null;
        this.currentChatId = null;
        this.monitoringInterval = null;
        this.messages = [];
        /** チャット単位の履歴（同一チャット内の複数調査を1つにまとめる） */
        this.chatHistory = [];
        /** 同一チャット内の完了した調査レポート。新規テーマ入力時に計画で考慮する（直近3件は全文、4件目以降は要約で含める） */
        this.previousReportsInChat = [];
        this.PREVIOUS_REPORTS_STORAGE_KEY = 'research_previousReportsInChat';
        this.CHAT_HISTORY_STORAGE_KEY = 'research_chatHistory';

        this.init();
    }

    /** 簡単なUUID生成 */
    _generateChatId() {
        return 'chat_' + Date.now() + '_' + Math.random().toString(36).slice(2, 11);
    }

    /**
     * 初期化
     */
    init() {
        // 設定の読み込み
        this.loadSettings();
        
        // 履歴の読み込み（localStorage）
        this.loadHistory();

        // 同一チャット内の既存レポートを復元（sessionStorage・リロード後も計画で考慮するため）
        this.loadPreviousReportsInChat();
        
        // イベントリスナーの設定
        this.setupEventListeners();
        
        // 初期ヘルスチェック
        this.checkHealth();
        
        // サーバーから履歴を復元（API再起動後も履歴を表示するため）
        this.syncHistoryFromServer();
        
        // グローバルに公開
        window.app = this;
    }

    /**
     * サーバーの永続化履歴と同期（API再起動後も履歴が見えるようにする）
     * サーバー取得成功時はサーバー一覧を信頼できる情報源として履歴を上書きする。
     * @param {number} retryCount - リトライ回数（サーバー起動直後の失敗時用）
     */
    async syncHistoryFromServer(retryCount = 0) {
        const maxRetry = 5;
        const retryDelayMs = 2000;
        const result = await api.getResearchHistory();
        if (result.success && result.items) {
            const serverItems = result.items.slice(0, 50);
            const serverIds = new Set(serverItems.map((i) => i.research_id));

            const updatedChats = this.chatHistory.map((chat) => ({
                ...chat,
                researches: (chat.researches || []).filter((r) => serverIds.has(r.research_id))
            })).filter((chat) => chat.researches.length > 0);

            const usedIds = new Set(updatedChats.flatMap((c) => c.researches.map((r) => r.research_id)));
            for (const item of serverItems) {
                if (usedIds.has(item.research_id)) continue;
                updatedChats.push({
                    chatId: this._generateChatId(),
                    researches: [{
                        research_id: item.research_id,
                        theme: item.theme || '',
                        status: item.status || 'completed',
                        created_at: item.created_at
                    }],
                    created_at: item.created_at
                });
                usedIds.add(item.research_id);
            }
            updatedChats.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
            this.chatHistory = updatedChats.slice(0, 50);
            this.saveChatHistory();
            this.renderHistory();
            return;
        }
        if (retryCount < maxRetry && this.chatHistory.length === 0) {
            setTimeout(() => this.syncHistoryFromServer(retryCount + 1), retryDelayMs);
        }
    }

    /**
     * 同一チャット内の既存レポートを sessionStorage から復元（リロード後も過去レポート考慮で計画するため）
     */
    loadPreviousReportsInChat() {
        try {
            const raw = sessionStorage.getItem(this.PREVIOUS_REPORTS_STORAGE_KEY);
            if (raw) {
                const parsed = JSON.parse(raw);
                if (Array.isArray(parsed) && parsed.length > 0) {
                    this.previousReportsInChat = parsed;
                }
            }
        } catch (e) {
            console.warn('previousReportsInChat の復元に失敗しました', e);
        }
    }

    /**
     * 同一チャット内の既存レポートを sessionStorage に保存
     */
    savePreviousReportsInChat() {
        try {
            sessionStorage.setItem(this.PREVIOUS_REPORTS_STORAGE_KEY, JSON.stringify(this.previousReportsInChat));
        } catch (e) {
            console.warn('previousReportsInChat の保存に失敗しました', e);
        }
    }

    /**
     * 設定の読み込み
     */
    loadSettings() {
        const savedApiUrl = localStorage.getItem('apiUrl');
        if (savedApiUrl) {
            document.getElementById('apiUrl').value = savedApiUrl;
            api.setBaseURL(savedApiUrl);
        }

        const savedMaxIterations = localStorage.getItem('maxIterations');
        if (savedMaxIterations) {
            document.getElementById('maxIterations').value = savedMaxIterations;
            document.getElementById('maxIterationsValue').textContent = savedMaxIterations;
        }

        const savedHumanIntervention = localStorage.getItem('enableHumanIntervention');
        if (savedHumanIntervention !== null) {
            document.getElementById('enableHumanIntervention').checked = savedHumanIntervention === 'true';
        }
    }

    /**
     * 設定の保存
     */
    saveSettings() {
        const apiUrl = document.getElementById('apiUrl').value;
        localStorage.setItem('apiUrl', apiUrl);
        api.setBaseURL(apiUrl);

        const maxIterations = document.getElementById('maxIterations').value;
        localStorage.setItem('maxIterations', maxIterations);

        const enableHumanIntervention = document.getElementById('enableHumanIntervention').checked;
        localStorage.setItem('enableHumanIntervention', enableHumanIntervention);
    }

    /**
     * 履歴の読み込み（旧形式 researchHistory から chatHistory へ移行）
     */
    loadHistory() {
        const savedChat = localStorage.getItem(this.CHAT_HISTORY_STORAGE_KEY);
        if (savedChat) {
            try {
                this.chatHistory = JSON.parse(savedChat);
                this.renderHistory();
                return;
            } catch (e) {
                console.warn('chatHistory の読み込みに失敗:', e);
            }
        }
        const savedLegacy = localStorage.getItem('researchHistory');
        if (savedLegacy) {
            try {
                const legacy = JSON.parse(savedLegacy);
                this.chatHistory = (Array.isArray(legacy) ? legacy : []).map((r) => ({
                    chatId: this._generateChatId(),
                    researches: [{ research_id: r.research_id, theme: r.theme || '', status: r.status || 'completed', created_at: r.created_at }],
                    created_at: r.created_at
                }));
                this.saveChatHistory();
                this.renderHistory();
            } catch (e) {
                console.error('履歴の移行に失敗しました:', e);
                this.chatHistory = [];
            }
        }
    }

    saveChatHistory() {
        localStorage.setItem(this.CHAT_HISTORY_STORAGE_KEY, JSON.stringify(this.chatHistory));
    }

    /**
     * 履歴の表示（チャット単位、同一チャット内の複数調査を1件として表示）
     */
    renderHistory() {
        const historyListEl = document.getElementById('historyList');
        const countEl = document.getElementById('historyCount');
        historyListEl.innerHTML = '';

        if (countEl) {
            countEl.textContent = this.chatHistory.length > 0 ? `（${this.chatHistory.length}件）` : '';
        }

        if (this.chatHistory.length === 0) {
            historyListEl.innerHTML = '<div style="color: var(--text-secondary); font-size: 0.85rem;">履歴がありません</div>';
            return;
        }

        this.chatHistory.forEach((chat) => {
            const researches = chat.researches || [];
            const first = researches[0];
            const theme = (first && first.theme) ? first.theme : '無題のリサーチ';
            const title = theme.length > 50 ? theme.substring(0, 50) + '...' : theme;
            const subtitle = researches.length > 1 ? `（${researches.length}件の調査）` : '';

            const item = document.createElement('div');
            item.className = 'history-item';
            item.dataset.chatId = chat.chatId;
            if (chat.chatId === this.currentChatId) {
                item.classList.add('active');
            }

            const titleEl = document.createElement('div');
            titleEl.className = 'history-item-title';
            titleEl.textContent = title + subtitle;

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'history-item-delete';
            deleteBtn.type = 'button';
            deleteBtn.textContent = '🗑️';
            deleteBtn.setAttribute('aria-label', '削除');

            item.appendChild(titleEl);
            item.appendChild(deleteBtn);
            historyListEl.appendChild(item);
        });
    }

    /**
     * 履歴からチャットを読み込み（同一チャット内の全調査を順に表示）
     */
    async loadResearchFromHistory(chatId) {
        const chat = this.chatHistory.find((c) => c.chatId === chatId);
        if (!chat || !chat.researches || chat.researches.length === 0) {
            ui.showNotification('チャットが見つかりません', 'error');
            return;
        }
        const sorted = [...chat.researches].sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));

        this.currentChatId = chatId;
        this.currentResearchId = sorted[sorted.length - 1]?.research_id || null;
        this.previousReportsInChat = [];
        this.renderHistory();
        ui.clearMessages();

        for (let i = 0; i < sorted.length; i++) {
            const r = sorted[i];
            ui.addMessage('user', r.theme || '（無題）');
            const result = await api.getResearch(r.research_id);
            if (result.success && result.data) {
                ui.displayResearchResult(result.data, r.research_id, i === 0 ? { scrollTo: 'top' } : {});
                const draft = (result.data.report && result.data.report.draft) ? result.data.report.draft : '';
                const plan = result.data.plan || {};
                const investigationPoints = Array.isArray(plan.investigation_points) ? plan.investigation_points : [];
                if (result.data.theme || draft) {
                    this.previousReportsInChat.push({
                        theme: result.data.theme || '（無題）',
                        draft: typeof draft === 'string' ? draft : String(draft),
                        investigation_points: investigationPoints
                    });
                }
            } else {
                ui.addMessage('assistant', `❌ リサーチの読み込みに失敗しました: ${r.research_id}`);
            }
        }
        this.savePreviousReportsInChat();
    }

    /**
     * 履歴からリサーチを削除
     */
    async deleteResearchFromHistory(chatId) {
        const chat = this.chatHistory.find((c) => c.chatId === chatId);
        if (!chat || !confirm('このチャットを削除しますか？（含まれる調査がすべて削除されます）')) return;

        for (const r of chat.researches || []) {
            await api.deleteResearch(r.research_id);
        }
        this.chatHistory = this.chatHistory.filter((c) => c.chatId !== chatId);
        this.saveChatHistory();
        this.renderHistory();

        if (this.currentChatId === chatId) {
            this.currentChatId = null;
            this.currentResearchId = null;
            ui.clearResults();
        }
        ui.showNotification('チャットを削除しました', 'success');
    }

    /**
     * イベントリスナーの設定
     */
    setupEventListeners() {
        // 新規チャットボタン
        document.getElementById('newChatBtn').addEventListener('click', () => {
            this.newChat();
        });

        // 送信ボタン
        document.getElementById('sendBtn').addEventListener('click', () => {
            this.sendMessage();
        });

        // メッセージ入力（Enterで送信、Shift+Enterで改行）
        const messageInput = document.getElementById('messageInput');
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // 入力エリアの自動リサイズ
        messageInput.addEventListener('input', () => {
            messageInput.style.height = 'auto';
            messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
        });

        // 最大イテレーション数のスライダー
        const maxIterationsSlider = document.getElementById('maxIterations');
        maxIterationsSlider.addEventListener('input', (e) => {
            document.getElementById('maxIterationsValue').textContent = e.target.value;
            this.saveSettings();
        });

        // 人間介入チェックボックス
        document.getElementById('enableHumanIntervention').addEventListener('change', () => {
            this.saveSettings();
        });

        // API URL入力
        document.getElementById('apiUrl').addEventListener('change', () => {
            this.saveSettings();
            this.checkHealth();
        });

        // ヘルスチェックボタン
        document.getElementById('healthCheckBtn').addEventListener('click', () => {
            this.checkHealth();
        });

        // 履歴リスト：イベント委譲でクリックを処理（項目クリックで読み込み、削除ボタンで削除）
        const historyListEl = document.getElementById('historyList');
        if (historyListEl) {
            historyListEl.addEventListener('click', (e) => {
                const item = e.target.closest('.history-item');
                if (!item) return;
                const chatId = item.dataset.chatId;
                if (!chatId) return;
                if (e.target.closest('.history-item-delete')) {
                    this.deleteResearchFromHistory(chatId);
                    return;
                }
                this.loadResearchFromHistory(chatId);
            });
        }
    }

    /**
     * 新規チャット
     */
    newChat() {
        this.currentResearchId = null;
        this.currentChatId = null;
        this.messages = [];
        this.previousReportsInChat = [];
        try {
            sessionStorage.removeItem(this.PREVIOUS_REPORTS_STORAGE_KEY);
        } catch (e) {}
        ui.clearMessages();
        ui.clearResults();
        this.renderHistory();
    }

    /**
     * メッセージ送信
     */
    async sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const theme = messageInput.value.trim();

        if (!theme) {
            return;
        }

        // メッセージをクリア
        messageInput.value = '';
        messageInput.style.height = 'auto';

        // ユーザーメッセージを表示
        ui.addMessage('user', theme);
        this.messages.push({ role: 'user', content: theme });

        // リサーチを開始
        ui.showLoading(true);
        ui.addMessage('assistant', 'リサーチを開始しています...');

        const maxIterations = parseInt(document.getElementById('maxIterations').value);
        const enableHumanIntervention = document.getElementById('enableHumanIntervention').checked;

        // 同一チャット内の既存レポートを考慮して計画を作成するため渡す（観点・直近3件全文・4件目以降要約）
        const MAX_FULL_REPORTS = 3;
        const MAX_DRAFT_LEN = 3000;
        const MAX_SUMMARY_LEN = 600;
        let previousReportsContext = null;
        if (this.previousReportsInChat.length > 0) {
            const full = this.previousReportsInChat.slice(0, MAX_FULL_REPORTS).map(r => {
                const points = Array.isArray(r.investigation_points) && r.investigation_points.length > 0
                    ? r.investigation_points.map(p => `  - ${p}`).join('\n')
                    : '  （観点情報なし）';
                const draftExcerpt = (r.draft || '').length > MAX_DRAFT_LEN
                    ? (r.draft || '').substring(0, MAX_DRAFT_LEN) + '\n...(省略)'
                    : (r.draft || '');
                return `--- 既存レポート ---\nテーマ: ${r.theme}\n調査観点:\n${points}\n\nレポート本文:\n${draftExcerpt}`;
            });
            const overflow = this.previousReportsInChat.slice(MAX_FULL_REPORTS);
            const overflowSummary = overflow.length > 0
                ? '\n\n--- その他の既存レポート（要約） ---\n' + overflow.map(r => {
                    const points = Array.isArray(r.investigation_points) && r.investigation_points.length > 0
                        ? r.investigation_points.join('、')
                        : '（観点情報なし）';
                    const summary = (r.draft || '').length > MAX_SUMMARY_LEN
                        ? (r.draft || '').substring(0, MAX_SUMMARY_LEN) + '...(省略)'
                        : (r.draft || '');
                    return `テーマ: ${r.theme}\n観点: ${points}\n要約: ${summary}`;
                }).join('\n\n')
                : '';
            previousReportsContext = full.join('\n\n') + overflowSummary;
        }

        const result = await api.createResearch(theme, maxIterations, enableHumanIntervention, previousReportsContext);

        if (result.success) {
            this.currentResearchId = result.data.research_id;
            const researchInfo = {
                research_id: result.data.research_id,
                theme: theme,
                status: 'started',
                created_at: new Date().toISOString()
            };
            if (this.currentChatId) {
                const chat = this.chatHistory.find((c) => c.chatId === this.currentChatId);
                if (chat) {
                    chat.researches = chat.researches || [];
                    chat.researches.push(researchInfo);
                } else {
                    this.currentChatId = null;
                }
            }
            if (!this.currentChatId) {
                const chatId = this._generateChatId();
                this.chatHistory.unshift({
                    chatId,
                    researches: [researchInfo],
                    created_at: researchInfo.created_at
                });
                this.currentChatId = chatId;
            }
            if (this.chatHistory.length > 50) {
                this.chatHistory = this.chatHistory.slice(0, 50);
            }
            this.saveChatHistory();
            this.renderHistory();

            // 「リサーチを開始しています...」メッセージを更新（進捗コンテナは除外し、最後の通常アシスタントメッセージのみ更新）
            const messages = Array.from(ui.chatMessagesEl.querySelectorAll('.message.assistant'))
                .filter((el) => el.id !== 'progressMessageContainer');
            if (messages.length > 0) {
                const lastMessage = messages[messages.length - 1];
                const contentEl = lastMessage.querySelector('.message-content');
                if (contentEl && contentEl.textContent.includes('リサーチを開始しています')) {
                    contentEl.innerHTML = 
                        ui.renderMarkdown(`リサーチを開始しました。\n\n**リサーチID**: \`${result.data.research_id}\`\n\n進捗を監視しています...`);
                }
            }

            // 監視を開始
            this.startMonitoring(result.data.research_id);
        } else {
            ui.showLoading(false);
            // 最後のアシスタントメッセージ（「リサーチを開始しています...」）を削除（進捗コンテナは除外）
            const messages = Array.from(ui.chatMessagesEl.querySelectorAll('.message.assistant'))
                .filter((el) => el.id !== 'progressMessageContainer');
            if (messages.length > 0) {
                const lastMessage = messages[messages.length - 1];
                const content = lastMessage.querySelector('.message-content');
                if (content && content.textContent.includes('リサーチを開始しています')) {
                    lastMessage.remove();
                }
            }
            ui.addMessage('assistant', `❌ リサーチの作成に失敗しました: ${result.error}`);
            ui.showNotification(`エラー: ${result.error}`, 'error');
        }
    }

    /**
     * リサーチ監視を開始
     */
    startMonitoring(researchId) {
        // 既存の監視を停止
        this.stopMonitoring();

        let checkCount = 0;
        const maxChecks = 600; // 10分（1秒間隔）

        this.monitoringInterval = setInterval(async () => {
            checkCount++;

            const statusResult = await api.getResearchStatus(researchId);
            
            if (!statusResult.success) {
                ui.showNotification('ステータスの取得に失敗しました', 'error');
                this.stopMonitoring();
                return;
            }

            const statusData = statusResult.data;
            const status = statusData.status;

            // 進捗を更新（停止ボタン付き）
            ui.updateProgress(statusData, researchId, () => {
                this.stopResearch(researchId);
            });

            // 完了または失敗
            if (status === 'completed' || status === 'failed') {
                this.stopMonitoring();
                ui.showLoading(false);

                if (status === 'completed') {
                    // 結果を取得
                    const result = await api.getResearch(researchId);
                    if (result.success && result.data) {
                        // 進捗メッセージを削除（結果表示の前に）
                        ui.clearProgress();
                        
                        // チャット形式で結果を表示
                        ui.displayResearchResult(result.data, researchId);
                        
                        // 同一チャット内の既存レポートとして蓄積（観点を含め、計画に渡す）
                        const draft = (result.data.report && result.data.report.draft) ? result.data.report.draft : '';
                        const plan = result.data.plan || {};
                        const investigationPoints = Array.isArray(plan.investigation_points) ? plan.investigation_points : [];
                        if (result.data.theme || draft) {
                            this.previousReportsInChat.unshift({
                                theme: result.data.theme || '（無題）',
                                draft: typeof draft === 'string' ? draft : String(draft),
                                investigation_points: investigationPoints
                            });
                            // コンテキスト長を抑えるため最大20件まで保持（4件目以降は要約で含める）
                            const MAX_PREVIOUS_REPORTS = 20;
                            if (this.previousReportsInChat.length > MAX_PREVIOUS_REPORTS) {
                                this.previousReportsInChat = this.previousReportsInChat.slice(0, MAX_PREVIOUS_REPORTS);
                            }
                            this.savePreviousReportsInChat();
                        }
                        
                        // 履歴を更新
                        for (const chat of this.chatHistory) {
                            const r = (chat.researches || []).find((x) => x.research_id === researchId);
                            if (r) {
                                r.status = 'completed';
                                this.saveChatHistory();
                                this.renderHistory();
                                break;
                            }
                        }

                        ui.showNotification('リサーチが完了しました！', 'success');
                    } else {
                        const msg = result.notFound
                            ? '結果の取得に失敗しました（リサーチが見つかりません）'
                            : (result.error || '結果の取得に失敗しました');
                        ui.showNotification(msg, 'error');
                    }
                } else {
                    // 進捗メッセージを削除してから失敗メッセージを表示
                    ui.clearProgress();
                    ui.addMessage('assistant', '❌ リサーチが失敗しました');
                    ui.showNotification('リサーチが失敗しました', 'error');
                }
            } else if (status === 'interrupted') {
                this.stopMonitoring();
                ui.showLoading(false);
                ui.clearProgress();
                // 中断時は必ずステータスを再取得し、計画・ソース・ドラフト・フィードバックを確実に取得する
                let interruptedState = statusData.interrupted_state || null;
                const freshStatus = await api.getResearchStatus(researchId);
                if (freshStatus.success && freshStatus.data) {
                    interruptedState = freshStatus.data.interrupted_state || interruptedState;
                }
                // APIから取得できなかった場合でも、コンテキスト欄を表示するため最小のオブジェクトを渡す
                if (!interruptedState) {
                    interruptedState = {
                        next_node: '不明',
                        task_plan: null,
                        research_data_summary: [],
                        current_draft_preview: null,
                        feedback: null
                    };
                }
                ui.showHumanInputForm(researchId, async (id, input, action) => {
                    ui.showLoading(true);
                    const result = await api.resumeResearch(id, input, action || 'resume');
                    if (result.success) {
                        ui.showNotification(result.data && result.data.message ? result.data.message : (action === 'replan' ? '計画を再作成しました' : 'リサーチを再開しました'), 'success');
                        this.startMonitoring(id);
                    } else {
                        ui.showLoading(false);
                        ui.showNotification(`再開に失敗しました: ${result.error}`, 'error');
                    }
                }, interruptedState);
            }

            // タイムアウト
            if (checkCount >= maxChecks) {
                this.stopMonitoring();
                ui.showLoading(false);
                ui.showNotification('タイムアウト: 最大待機時間を超過しました', 'warning');
            }
        }, 1000); // 1秒間隔
    }

    /**
     * リサーチ監視を停止
     */
    stopMonitoring() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
        }
    }

    /**
     * リサーチを再生成
     */
    async regenerateResearch(researchId) {
        let research = null;
        let parentChat = null;
        for (const chat of this.chatHistory) {
            research = (chat.researches || []).find((r) => r.research_id === researchId);
            if (research) {
                parentChat = chat;
                break;
            }
        }
        if (!research) {
            ui.showNotification('リサーチが見つかりません', 'error');
            return;
        }

        const theme = research.theme;
        const maxIterations = parseInt(document.getElementById('maxIterations').value);
        const enableHumanIntervention = document.getElementById('enableHumanIntervention').checked;

        ui.addMessage('user', theme);
        ui.showLoading(true);
        ui.addMessage('assistant', 'リサーチを再生成しています...');

        const result = await api.createResearch(theme, maxIterations, enableHumanIntervention);

        if (result.success) {
            this.currentResearchId = result.data.research_id;
            const newInfo = { research_id: result.data.research_id, theme, status: 'started', created_at: new Date().toISOString() };
            if (parentChat) {
                parentChat.researches = parentChat.researches || [];
                parentChat.researches.push(newInfo);
                this.currentChatId = parentChat.chatId;
            } else {
                const chatId = this._generateChatId();
                this.chatHistory.unshift({ chatId, researches: [newInfo], created_at: newInfo.created_at });
                this.currentChatId = chatId;
            }
            this.saveChatHistory();
            this.renderHistory();
            this.startMonitoring(result.data.research_id);
        } else {
            ui.showLoading(false);
            const messages = Array.from(ui.chatMessagesEl.querySelectorAll('.message.assistant'))
                .filter((el) => el.id !== 'progressMessageContainer');
            if (messages.length > 0) {
                const lastMsg = messages[messages.length - 1];
                if (lastMsg && lastMsg.textContent && lastMsg.textContent.includes('リサーチを再生成しています')) {
                    lastMsg.remove();
                }
            }
            ui.addMessage('assistant', `❌ リサーチの再生成に失敗しました: ${result.error}`);
            ui.showNotification(`エラー: ${result.error}`, 'error');
        }
    }

    /**
     * リサーチを停止
     */
    async stopResearch(researchId) {
        if (confirm('リサーチを停止しますか？')) {
            this.stopMonitoring();
            ui.showLoading(true);
            
            const result = await api.deleteResearch(researchId);
            if (result.success) {
                ui.showLoading(false);
                ui.clearProgress();
                ui.showNotification('リサーチを停止しました', 'success');
                
                // 履歴から削除（該当リサーチをチャット内から除去、チャットが空になったらチャットごと削除）
                for (const chat of this.chatHistory) {
                    chat.researches = (chat.researches || []).filter((r) => r.research_id !== researchId);
                }
                this.chatHistory = this.chatHistory.filter((c) => (c.researches || []).length > 0);
                this.saveChatHistory();
                this.renderHistory();

                if (this.currentResearchId === researchId) this.currentResearchId = null;
                if (this.currentChatId && !this.chatHistory.some((c) => c.chatId === this.currentChatId)) {
                    this.currentChatId = null;
                }
            } else {
                ui.showLoading(false);
                ui.showNotification(`停止に失敗しました: ${result.error}`, 'error');
            }
        }
    }

    /**
     * ヘルスチェック
     */
    async checkHealth() {
        const result = await api.checkHealth();
        if (result.success) {
            ui.updateConnectionStatus(true);
            // 初回のみ通知を表示（連続チェック時は通知しない）
            if (!this.healthCheckShown) {
                ui.showNotification('APIサーバーに接続できました', 'success');
                this.healthCheckShown = true;
            }
        } else {
            // 詳細なエラーメッセージを取得
            const errorMsg = result.error || 'APIサーバーに接続できません';
            ui.updateConnectionStatus(false, errorMsg);
            
            // 初回のみ通知を表示
            if (!this.healthCheckErrorShown) {
                ui.showNotification('APIサーバーに接続できません。詳細は接続ステータスをクリックしてください。', 'error');
                this.healthCheckErrorShown = true;
            }
            
            // 接続エラーの詳細をコンソールに出力
            console.error('API接続エラー:', errorMsg);
            console.error('API URL:', api.baseURL);
            console.error('現在のプロトコル:', window.location.protocol);
            
            // file://プロトコルの場合、警告を表示
            if (window.location.protocol === 'file:') {
                console.warn('ローカルファイルから開いています。CORSエラーが発生する可能性があります。');
                console.warn('解決方法: ローカルWebサーバーを使用してください');
                console.warn('  cd gui && python -m http.server 8080');
            }
        }
    }
}

// アプリケーションを起動
document.addEventListener('DOMContentLoaded', () => {
    new App();
});
