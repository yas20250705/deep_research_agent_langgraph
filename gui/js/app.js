/**
 * メインアプリケーション
 * 状態管理、イベントハンドリング、リサーチ監視を担当
 */

class App {
    constructor() {
        this.currentResearchId = null;
        this.monitoringInterval = null;
        this.messages = [];
        this.researchHistory = [];
        
        this.init();
    }

    /**
     * 初期化
     */
    init() {
        // 設定の読み込み
        this.loadSettings();
        
        // 履歴の読み込み
        this.loadHistory();
        
        // イベントリスナーの設定
        this.setupEventListeners();
        
        // 初期ヘルスチェック
        this.checkHealth();
        
        // グローバルに公開
        window.app = this;
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
     * 履歴の読み込み
     */
    loadHistory() {
        const savedHistory = localStorage.getItem('researchHistory');
        if (savedHistory) {
            try {
                this.researchHistory = JSON.parse(savedHistory);
                this.renderHistory();
            } catch (e) {
                console.error('履歴の読み込みに失敗しました:', e);
                this.researchHistory = [];
            }
        }
    }

    /**
     * 履歴の保存
     */
    saveHistory() {
        localStorage.setItem('researchHistory', JSON.stringify(this.researchHistory));
    }

    /**
     * 履歴の表示
     */
    renderHistory() {
        const historyListEl = document.getElementById('historyList');
        historyListEl.innerHTML = '';

        if (this.researchHistory.length === 0) {
            historyListEl.innerHTML = '<div style="color: var(--text-secondary); font-size: 0.85rem;">履歴がありません</div>';
            return;
        }

        this.researchHistory.forEach((research, index) => {
            const item = document.createElement('div');
            item.className = 'history-item';
            if (research.research_id === this.currentResearchId) {
                item.classList.add('active');
            }

            const title = document.createElement('div');
            title.className = 'history-item-title';
            title.textContent = research.title || research.theme || '無題のリサーチ';
            title.onclick = () => this.loadResearchFromHistory(research.research_id);

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'history-item-delete';
            deleteBtn.textContent = '🗑️';
            deleteBtn.onclick = (e) => {
                e.stopPropagation();
                this.deleteResearchFromHistory(research.research_id);
            };

            item.appendChild(title);
            item.appendChild(deleteBtn);
            historyListEl.appendChild(item);
        });
    }

    /**
     * 履歴からリサーチを読み込み
     */
    async loadResearchFromHistory(researchId) {
        this.currentResearchId = researchId;
        this.renderHistory();

        // 結果を取得
        const result = await api.getResearch(researchId);
        if (result.success && result.data) {
            ui.clearMessages();
            
            // メッセージを再表示
            const research = this.researchHistory.find(r => r.research_id === researchId);
            if (research) {
                ui.addMessage('user', research.theme);
            }

            // 結果をチャット形式で表示
            ui.displayResearchResult(result.data, researchId);
        } else {
            ui.showNotification('リサーチ結果の取得に失敗しました', 'error');
        }
    }

    /**
     * 履歴からリサーチを削除
     */
    async deleteResearchFromHistory(researchId) {
        if (confirm('このリサーチを削除しますか？')) {
            // APIからも削除
            await api.deleteResearch(researchId);

            // 履歴から削除
            this.researchHistory = this.researchHistory.filter(r => r.research_id !== researchId);
            this.saveHistory();
            this.renderHistory();

            if (this.currentResearchId === researchId) {
                this.currentResearchId = null;
                ui.clearResults();
            }

            ui.showNotification('リサーチを削除しました', 'success');
        }
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
    }

    /**
     * 新規チャット
     */
    newChat() {
        this.currentResearchId = null;
        this.messages = [];
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

        const result = await api.createResearch(theme, maxIterations, enableHumanIntervention);

        if (result.success) {
            this.currentResearchId = result.data.research_id;
            
            // 履歴に追加
            const researchInfo = {
                research_id: result.data.research_id,
                theme: theme,
                status: 'started',
                title: theme.length > 50 ? theme.substring(0, 50) + '...' : theme,
                created_at: new Date().toISOString()
            };
            this.researchHistory.unshift(researchInfo);
            // 最大50件まで保持
            if (this.researchHistory.length > 50) {
                this.researchHistory = this.researchHistory.slice(0, 50);
            }
            this.saveHistory();
            this.renderHistory();

            // 「リサーチを開始しています...」メッセージを更新
            const messages = ui.chatMessagesEl.querySelectorAll('.message.assistant');
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
            // 最後のアシスタントメッセージ（「リサーチを開始しています...」）を削除
            const messages = ui.chatMessagesEl.querySelectorAll('.message.assistant');
            if (messages.length > 0) {
                const lastMessage = messages[messages.length - 1];
                // 「リサーチを開始しています...」というメッセージのみ削除
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
                        
                        // 履歴を更新
                        const research = this.researchHistory.find(r => r.research_id === researchId);
                        if (research) {
                            research.status = 'completed';
                            this.saveHistory();
                            this.renderHistory();
                        }

                        ui.showNotification('リサーチが完了しました！', 'success');
                    } else {
                        ui.showNotification('結果の取得に失敗しました', 'error');
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
                ui.showHumanInputForm(researchId, async (id, input) => {
                    ui.showLoading(true);
                    const result = await api.resumeResearch(id, input);
                    if (result.success) {
                        ui.showNotification('リサーチを再開しました', 'success');
                        this.startMonitoring(id);
                    } else {
                        ui.showLoading(false);
                        ui.showNotification(`再開に失敗しました: ${result.error}`, 'error');
                    }
                });
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
        const research = this.researchHistory.find(r => r.research_id === researchId);
        if (!research) {
            ui.showNotification('リサーチが見つかりません', 'error');
            return;
        }

        // 新しいリサーチを開始
        const theme = research.theme;
        const maxIterations = parseInt(document.getElementById('maxIterations').value);
        const enableHumanIntervention = document.getElementById('enableHumanIntervention').checked;

        ui.addMessage('user', theme);
        ui.showLoading(true);
        ui.addMessage('assistant', 'リサーチを再生成しています...');

        const result = await api.createResearch(theme, maxIterations, enableHumanIntervention);

        if (result.success) {
            this.currentResearchId = result.data.research_id;
            this.startMonitoring(result.data.research_id);
        } else {
            ui.showLoading(false);
            const messages = ui.chatMessagesEl.querySelectorAll('.message.assistant');
            if (messages.length > 0) {
                messages[messages.length - 1].remove();
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
                
                // 履歴から削除
                this.researchHistory = this.researchHistory.filter(r => r.research_id !== researchId);
                this.saveHistory();
                this.renderHistory();
                
                if (this.currentResearchId === researchId) {
                    this.currentResearchId = null;
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
