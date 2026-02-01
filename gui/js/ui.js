/**
 * UI操作モジュール
 * メッセージ表示、結果表示、通知などのUI操作を担当
 */

class UI {
    constructor() {
        this.chatMessagesEl = document.getElementById('chatMessages');
        this.notificationsEl = document.getElementById('notifications');
        this.loadingOverlayEl = document.getElementById('loadingOverlay');
        this.connectionStatusEl = document.getElementById('connectionStatus');
    }

    /**
     * MarkdownをHTMLに変換
     */
    renderMarkdown(markdown) {
        if (!marked) {
            return markdown; // marked.jsが読み込まれていない場合
        }

        // marked.jsでMarkdownをHTMLに変換
        const html = marked.parse(markdown);

        // コードブロックのハイライト処理
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;

        // コードブロックをハイライト
        tempDiv.querySelectorAll('pre code').forEach((block) => {
            if (hljs) {
                hljs.highlightElement(block);
            }
        });

        // すべてのリンク（<a>タグ）にtarget="_blank"とrel="noopener noreferrer"を追加
        // ただし、アンカーリンク（#で始まる）やjavascript:リンクは除外
        tempDiv.querySelectorAll('a').forEach((link) => {
            const href = link.getAttribute('href') || '';
            // 外部リンク（http://, https://で始まる）のみ別タブで開く
            if ((href.startsWith('http://') || href.startsWith('https://')) && !link.hasAttribute('target')) {
                link.setAttribute('target', '_blank');
                link.setAttribute('rel', 'noopener noreferrer');
            }
        });

        return tempDiv.innerHTML;
    }

    /**
     * チャットメッセージを追加
     */
    addMessage(role, content, researchId = null) {
        // 進捗メッセージの後ろに追加するため、進捗メッセージの位置を確認
        const progressMessageContainer = document.getElementById('progressMessageContainer');
        
        const messageEl = document.createElement('div');
        messageEl.className = `message ${role}`;

        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        contentEl.innerHTML = this.renderMarkdown(content);

        messageEl.appendChild(contentEl);
        
        // 進捗メッセージがある場合は、その前に挿入（進捗メッセージは最後に残す）
        if (progressMessageContainer && progressMessageContainer.parentNode === this.chatMessagesEl) {
            this.chatMessagesEl.insertBefore(messageEl, progressMessageContainer);
        } else {
            this.chatMessagesEl.appendChild(messageEl);
        }

        // メッセージ内のすべてのリンクにtarget="_blank"を設定（念のため）
        contentEl.querySelectorAll('a').forEach((link) => {
            if (!link.hasAttribute('target')) {
                link.setAttribute('target', '_blank');
                link.setAttribute('rel', 'noopener noreferrer');
            }
        });

        // 再生成ボタンを追加（アシスタントメッセージの場合、進捗メッセージでない場合のみ）
        if (role === 'assistant' && researchId && messageEl.id !== 'progressMessageContainer') {
            const regenerateBtn = document.createElement('button');
            regenerateBtn.className = 'btn btn-secondary mt-1';
            regenerateBtn.textContent = '🔄 再生成';
            regenerateBtn.onclick = () => {
                // 再生成処理はapp.jsで実装
                if (window.app) {
                    window.app.regenerateResearch(researchId);
                }
            };
            contentEl.appendChild(regenerateBtn);
        }

        // スクロールを最下部に
        this.scrollToBottom();
    }

    /**
     * リサーチ結果をチャット形式で表示（同一チャット内で複数回調査した場合も履歴として追加し、既存の結果は残す）
     * @param {Object} options - { scrollTo: 'top' | 'bottom' } 履歴から表示時は 'top' で調査クエリを最上部に
     */
    displayResearchResult(result, researchId, options = {}) {
        let content = '';

        // 各調査結果を識別するための見出し（複数結果が並んでもどれがどのテーマか分かるようにする）
        const themeLabel = (result.theme && result.theme.trim()) ? result.theme.trim() : '（無題）';
        const shortTheme = themeLabel.length > 60 ? themeLabel.substring(0, 60) + '...' : themeLabel;
        content += `## 📋 調査結果: ${shortTheme}\n\n`;

        // 統計情報
        if (result.statistics) {
            const stats = result.statistics;
            content += '## 📊 統計情報\n\n';
            content += `- **イテレーション回数**: ${stats.iterations || 0}\n`;
            content += `- **収集ソース数**: ${stats.sources_collected || 0}\n`;
            content += `- **処理時間**: ${stats.processing_time_seconds || 0}秒\n\n`;
        }

        // レポート
        if (result.report && result.report.draft) {
            content += '## 📄 レポート\n\n';
            
            // レポートのドラフトから参照ソースセクションを削除（後でHTML形式で追加するため）
            let draft = result.report.draft;
            // 「## 参考文献」「## 参照ソース」「## References」などのセクションを削除
            draft = draft.replace(/\n## 参考文献[\s\S]*$/i, '');
            draft = draft.replace(/\n## 参照ソース[\s\S]*$/i, '');
            draft = draft.replace(/\n## References[\s\S]*$/i, '');
            draft = draft.replace(/\n📚 参照ソース[\s\S]*$/i, '');
            
            content += draft;
            content += '\n\n';
        }

        // 参照ソース（HTML形式で直接生成）
        // 参照ソースセクションは後でHTMLで追加するため、ここではスキップ

        // 進捗メッセージを削除してから結果を表示（既存の結果ブロックは削除せず、常に末尾に追加）
        this.clearProgress();
        
        // 新しいメッセージとして追加（同一チャット内の複数調査結果をすべて残すため、常に append）
        const messageEl = document.createElement('div');
        messageEl.className = 'message assistant research-result-block';
        messageEl.dataset.researchId = researchId || '';

        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        
        // コンテンツがある場合はMarkdownをレンダリング
        if (content.trim()) {
            contentEl.innerHTML = this.renderMarkdown(content);
        }

        messageEl.appendChild(contentEl);
        this.chatMessagesEl.appendChild(messageEl);

        // メッセージ内のすべてのリンクにtarget="_blank"を設定（念のため）
        contentEl.querySelectorAll('a').forEach((link) => {
            if (!link.hasAttribute('target')) {
                link.setAttribute('target', '_blank');
                link.setAttribute('rel', 'noopener noreferrer');
            }
        });

        // ダウンロードボタンを追加（レポートがある場合のみ）
        if (result.report && result.report.draft) {
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'btn btn-primary mt-2';
            downloadBtn.textContent = '📥 レポートをダウンロード';
            downloadBtn.onclick = () => {
                this.downloadReport(result, researchId);
            };
            contentEl.appendChild(downloadBtn);

            // 再生成ボタンを追加
            const regenerateBtn = document.createElement('button');
            regenerateBtn.className = 'btn btn-secondary mt-1';
            regenerateBtn.textContent = '🔄 再生成';
            regenerateBtn.onclick = () => {
                if (window.app) {
                    window.app.regenerateResearch(researchId);
                }
            };
            contentEl.appendChild(regenerateBtn);
        }

        // 参照ソースセクションを追加（HTML形式）
        if (result.report && result.report.sources && result.report.sources.length > 0) {
            console.log('参照ソースを追加します:', result.report.sources.length, '件', result.report.sources);
            this.addSourcesSection(contentEl, result.report.sources, researchId || 'default', result.theme);
        } else {
            console.log('参照ソースが見つかりません:', {
                hasReport: !!result.report,
                hasSources: !!(result.report && result.report.sources),
                sourcesLength: result.report && result.report.sources ? result.report.sources.length : 0,
                result: result
            });
        }

        // スクロール：履歴から表示時は最上部（調査クエリ）、それ以外は最下部
        if (options.scrollTo === 'top') {
            this.scrollToTop();
        } else {
            this.scrollToBottom();
        }
    }

    /**
     * 進捗表示を更新（チャット形式）
     */
    updateProgress(statusData, researchId = null, onStop = null) {
        // 既存の進捗メッセージを探すか作成
        let progressMessageContainer = document.getElementById('progressMessageContainer');
        let progressMessage = null;
        
        if (!progressMessageContainer) {
            // 新しい進捗メッセージを作成
            const messageEl = document.createElement('div');
            messageEl.id = 'progressMessageContainer';
            messageEl.className = 'message assistant';
            this.chatMessagesEl.appendChild(messageEl);
            
            const contentEl = document.createElement('div');
            contentEl.className = 'message-content';
            contentEl.id = 'progressMessage';
            messageEl.appendChild(contentEl);
            
            progressMessageContainer = messageEl;
            progressMessage = contentEl;
        } else {
            // 既存のコンテナからcontent要素を取得
            progressMessage = progressMessageContainer.querySelector('.message-content');
            if (!progressMessage) {
                // content要素がない場合は作成
                progressMessage = document.createElement('div');
                progressMessage.className = 'message-content';
                progressMessage.id = 'progressMessage';
                progressMessageContainer.appendChild(progressMessage);
            }
        }

        const progress = statusData.progress;
        if (progress) {
            const progressValue = progress.max_iterations > 0 
                ? (progress.current_iteration / progress.max_iterations) * 100 
                : 0;

            let progressHtml = `
                <div class="progress-bar">
                    <div class="progress-bar-fill" style="width: ${progressValue}%"></div>
                </div>
                <div class="progress-info">
                    <span>📊 イテレーション: ${progress.current_iteration}/${progress.max_iterations}</span>
                    <span>⚙️ ノード: ${progress.current_node || 'unknown'}</span>
                </div>
            `;

            if (statusData.statistics) {
                const sourcesCount = statusData.statistics.sources_collected || 0;
                progressHtml += `<div class="progress-info mt-1">📚 ソース数: ${sourcesCount}</div>`;
            }

            if (statusData.status === 'processing' || statusData.status === 'started') {
                progressHtml += '<button id="stopResearchBtn" class="btn btn-secondary mt-1">⏹️ 停止</button>';
            }

            progressMessage.innerHTML = progressHtml;

            // 停止ボタンのイベントリスナー
            const stopBtn = document.getElementById('stopResearchBtn');
            if (stopBtn && onStop) {
                // 既存のイベントリスナーを削除してから追加
                const newStopBtn = stopBtn.cloneNode(true);
                stopBtn.parentNode.replaceChild(newStopBtn, stopBtn);
                newStopBtn.addEventListener('click', onStop);
            }
        }

        // スクロールを最下部に
        this.scrollToBottom();
    }

    /**
     * 人間介入の入力フォームを表示（チャット形式）。中断時のコンテキストがあれば入力フォームの上に表示する。
     */
    showHumanInputForm(researchId, onResume, interruptedState) {
        const messageEl = document.createElement('div');
        messageEl.className = 'message assistant';
        this.chatMessagesEl.appendChild(messageEl);

        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';

        let contextHtml = '';
        if (interruptedState) {
            const nextLabels = {
                writer: '次: Writer（レポート執筆）',
                researcher: '次: Researcher（情報収集）',
                supervisor: '次: Supervisor（計画立案）',
                planning_gate: '次: Researcher（情報収集）',
                revise_plan: '次: 計画の再作成（human input を反映）',
                reviewer: '次: Reviewer（レビュー）'
            };
            const nextLabel = nextLabels[interruptedState.next_node] || `次: ${interruptedState.next_node || '不明'}`;
            contextHtml += `<div style="margin-bottom: 1rem; padding: 0.75rem; background: #e8f4f8; border-radius: 6px; font-size: 0.9rem;"><strong>${nextLabel}</strong></div>`;
            // 調査計画のみ表示（収集ソース・ドラフト・フィードバックは表示しない）。観点は項目ごとに縦リストで表示。
            const plan = interruptedState.task_plan || {};
            const theme = plan.theme || '';
            const planText = (plan.plan_text || '').substring(0, 500);
            const points = plan.investigation_points || [];
            let planContent = '';
            if (theme || planText || points.length > 0) {
                if (theme) planContent += `<div style="margin-bottom: 0.5rem;"><strong>テーマ:</strong> ${this._escapeHtml(theme)}</div>`;
                if (planText) planContent += `<div style="margin-bottom: 0.5rem;">${this._escapeHtml(planText)}${(plan.plan_text || '').length > 500 ? '...' : ''}</div>`;
                if (points.length > 0) {
                    planContent += '<div style="margin-top: 0.5rem;"><strong>観点:</strong><ul style="margin: 0.25rem 0 0 0; padding-left: 1.25rem; font-size: 0.85rem;">';
                    points.forEach(p => {
                        const text = typeof p === 'string' ? p : (p && p.title) ? p.title : String(p);
                        planContent += `<li>${this._escapeHtml(text)}</li>`;
                    });
                    planContent += '</ul></div>';
                }
            } else {
                planContent = '<span style="color:#666;">（なし）</span>';
            }
            contextHtml += `<details open style="margin-bottom: 0.75rem;"><summary style="cursor:pointer;">調査計画</summary><div style="padding: 0.5rem 0; font-size: 0.85rem;">${planContent}</div></details>`;
        }

        contentEl.innerHTML = `
            ${contextHtml}
            <div style="padding: 1rem; background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 8px;">
                <h3 style="margin-bottom: 1rem;">⏸️ リサーチが中断されました</h3>
                <p style="margin-bottom: 1rem;">必要に応じて入力し、調査開始（再開）または再計画を選んでください。</p>
                <textarea id="humanInput" class="message-input" rows="3" placeholder="入力してください（任意）。再計画の場合は指示を入力..." style="width: 100%; margin-bottom: 0.5rem;"></textarea>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    <button id="resumeResearchBtn" class="btn btn-primary">調査開始</button>
                    <button id="replanBtn" class="btn btn-secondary">再計画</button>
                </div>
            </div>
        `;
        messageEl.appendChild(contentEl);

        const resumeBtn = contentEl.querySelector('#resumeResearchBtn');
        const replanBtn = contentEl.querySelector('#replanBtn');
        const humanInputEl = contentEl.querySelector('#humanInput');
        if (resumeBtn && humanInputEl) {
            resumeBtn.addEventListener('click', () => {
                onResume(researchId, humanInputEl.value.trim(), 'resume');
            });
        }
        if (replanBtn && humanInputEl) {
            replanBtn.addEventListener('click', () => {
                onResume(researchId, humanInputEl.value.trim(), 'replan');
            });
        }
        if (humanInputEl) {
            humanInputEl.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                    resumeBtn.click();
                }
            });
        }

        this.scrollToBottom();
    }

    _escapeHtml(text) {
        if (text == null) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 進捗表示を削除
     */
    clearProgress() {
        const progressMessageContainer = document.getElementById('progressMessageContainer');
        if (progressMessageContainer) {
            progressMessageContainer.remove();
        }
    }

    /**
     * 通知を表示
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;

        this.notificationsEl.appendChild(notification);

        // 3秒後に自動削除
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    /**
     * ローディング表示
     */
    showLoading(show = true) {
        if (show) {
            this.loadingOverlayEl.classList.remove('hidden');
        } else {
            this.loadingOverlayEl.classList.add('hidden');
        }
    }

    /**
     * 接続ステータスを更新
     */
    updateConnectionStatus(connected, errorMessage = null) {
        if (connected) {
            this.connectionStatusEl.textContent = '✅ APIサーバーに接続中';
            this.connectionStatusEl.className = 'connection-status connected';
            this.connectionStatusEl.title = `API URL: ${api.baseURL}`;
        } else {
            this.connectionStatusEl.textContent = '❌ APIサーバーに接続できません';
            this.connectionStatusEl.className = 'connection-status disconnected';
            
            // エラーメッセージをツールチップに設定
            let tooltip = `API URL: ${api.baseURL}`;
            if (errorMessage) {
                tooltip += `\n\nエラー: ${errorMessage}`;
            }
            if (window.location.protocol === 'file:') {
                tooltip += '\n\n注意: ローカルファイルから開いています。CORSエラーが発生する可能性があります。\nローカルWebサーバーを使用してください: cd gui && python -m http.server 8080';
            }
            this.connectionStatusEl.title = tooltip;
            
            // クリックで詳細を表示
            this.connectionStatusEl.style.cursor = 'pointer';
            this.connectionStatusEl.onclick = () => {
                let message = `API URL: ${api.baseURL}\n\n`;
                if (errorMessage) {
                    message += `エラー: ${errorMessage}\n\n`;
                }
                if (window.location.protocol === 'file:') {
                    message += '注意: ローカルファイルから開いています。\nCORSエラーが発生する可能性があります。\n\n';
                    message += '解決方法:\n';
                    message += '1. ローカルWebサーバーを起動:\n';
                    message += '   cd gui\n';
                    message += '   python -m http.server 8080\n\n';
                    message += '2. ブラウザで http://localhost:8080 にアクセス\n\n';
                } else {
                    message += '解決方法:\n';
                    message += '1. APIサーバーが起動しているか確認\n';
                    message += '2. API URLが正しいか確認\n';
                    message += '3. ファイアウォールの設定を確認\n';
                }
                alert(message);
            };
        }
    }

    /**
     * チャット履歴をクリア
     */
    clearMessages() {
        this.chatMessagesEl.innerHTML = '';
    }

    /**
     * リサーチ結果をクリア（チャット形式では不要だが、互換性のため残す）
     */
    clearResults() {
        // チャット形式では結果はクリアしない（履歴として残す）
    }

    /**
     * スクロールを最下部に
     */
    scrollToBottom() {
        this.chatMessagesEl.scrollTop = this.chatMessagesEl.scrollHeight;
    }

    /**
     * チャットエリアを最上部（調査クエリ）にスクロール
     */
    scrollToTop() {
        this.chatMessagesEl.scrollTop = 0;
    }

    /**
     * 参照ソースセクションを追加
     * @param {string} [theme] - 人が入力した調査テーマ（query）。PDF冒頭タイトルに使用
     */
    addSourcesSection(container, sources, researchId, theme) {
        console.log('addSourcesSection called:', { sourcesCount: sources.length, researchId });
        
        const sourcesSection = document.createElement('div');
        sourcesSection.className = 'sources-section';
        sourcesSection.style.marginTop = '2rem';
        sourcesSection.style.paddingTop = '2rem';
        sourcesSection.style.borderTop = '2px solid var(--border-color)';

        const heading = document.createElement('h2');
        heading.textContent = `📚 参照ソース (${sources.length}件)`;
        heading.style.marginBottom = '1rem';
        sourcesSection.appendChild(heading);

        // 全選択/全解除/ダウンロードボタン（1行に配置、ダウンロードは右端）
        const buttonContainer = document.createElement('div');
        buttonContainer.style.display = 'flex';
        buttonContainer.style.alignItems = 'center';
        buttonContainer.style.gap = '0.5rem';
        buttonContainer.style.marginBottom = '1rem';
        buttonContainer.style.flexWrap = 'wrap';

        const selectAllBtn = document.createElement('button');
        selectAllBtn.className = 'btn btn-secondary';
        selectAllBtn.textContent = '✅ すべて選択';
        selectAllBtn.onclick = () => {
            sources.forEach((_, index) => {
                const checkbox = document.getElementById(`source-checkbox-${researchId}-${index}`);
                if (checkbox) checkbox.checked = true;
            });
        };

        const deselectAllBtn = document.createElement('button');
        deselectAllBtn.className = 'btn btn-secondary';
        deselectAllBtn.textContent = '❌ すべて解除';
        deselectAllBtn.onclick = () => {
            sources.forEach((_, index) => {
                const checkbox = document.getElementById(`source-checkbox-${researchId}-${index}`);
                if (checkbox) checkbox.checked = false;
            });
        };

        const downloadBtn = document.createElement('button');
        downloadBtn.className = 'btn btn-primary';
        downloadBtn.textContent = '📥 選択したソースをダウンロード';
        downloadBtn.style.marginLeft = 'auto';
        downloadBtn.onclick = () => {
            this.downloadSelectedSources(sources, researchId, theme);
        };

        buttonContainer.appendChild(selectAllBtn);
        buttonContainer.appendChild(deselectAllBtn);
        buttonContainer.appendChild(downloadBtn);
        sourcesSection.appendChild(buttonContainer);

        // ソースリスト（この枠内のみスクロール）
        const listWrapper = document.createElement('div');
        listWrapper.style.maxHeight = '800px'; 
        listWrapper.style.overflowY = 'auto';
        listWrapper.style.overflowX = 'hidden';

        const sourcesList = document.createElement('div');
        sourcesList.className = 'sources-list';
        sourcesList.style.display = 'flex';
        sourcesList.style.flexDirection = 'column';
        sourcesList.style.gap = '1rem';

        sources.forEach((source, index) => {
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-item';
            sourceItem.style.padding = '1rem';
            sourceItem.style.border = '1px solid var(--border-color)';
            sourceItem.style.borderRadius = '8px';
            sourceItem.style.backgroundColor = 'var(--background)';

            // チェックボックス
            const checkboxContainer = document.createElement('div');
            checkboxContainer.style.display = 'flex';
            checkboxContainer.style.alignItems = 'flex-start';
            checkboxContainer.style.gap = '0.75rem';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `source-checkbox-${researchId}-${index}`;
            checkbox.style.marginTop = '0.25rem';
            checkbox.style.cursor = 'pointer';

            const sourceContent = document.createElement('div');
            sourceContent.style.flex = '1';

            const title = document.createElement('h3');
            title.textContent = `${index + 1}. ${source.title || 'N/A'}`;
            title.style.marginBottom = '0.5rem';
            title.style.fontSize = '1rem';

            const urlLink = document.createElement('a');
            urlLink.href = source.url || '#';
            urlLink.textContent = source.url || 'N/A';
            urlLink.target = '_blank';
            urlLink.rel = 'noopener noreferrer';
            urlLink.style.color = 'var(--primary-color)';
            urlLink.style.textDecoration = 'underline';
            urlLink.style.display = 'block';
            urlLink.style.marginBottom = '0.5rem';

            sourceContent.appendChild(title);
            sourceContent.appendChild(urlLink);

            if (source.summary) {
                const summary = document.createElement('p');
                summary.textContent = `要約: ${source.summary}`;
                summary.style.fontSize = '0.9rem';
                summary.style.color = 'var(--text-secondary)';
                summary.style.marginBottom = '0.5rem';
                sourceContent.appendChild(summary);
            }

            if (source.relevance_score !== undefined) {
                const score = document.createElement('p');
                score.textContent = `関連性スコア: ${source.relevance_score.toFixed(2)}`;
                score.style.fontSize = '0.9rem';
                score.style.color = 'var(--text-secondary)';
                sourceContent.appendChild(score);
            }

            checkboxContainer.appendChild(checkbox);
            checkboxContainer.appendChild(sourceContent);
            sourceItem.appendChild(checkboxContainer);
            sourcesList.appendChild(sourceItem);
        });

        listWrapper.appendChild(sourcesList);
        sourcesSection.appendChild(listWrapper);

        container.appendChild(sourcesSection);
        console.log('参照ソースセクションを追加しました。要素数:', sourcesSection.children.length);
        
        // 追加された要素を確認
        const addedSection = container.querySelector('.sources-section');
        if (addedSection) {
            console.log('参照ソースセクションが正しく追加されました');
        } else {
            console.error('参照ソースセクションの追加に失敗しました');
        }
    }

    /**
     * 選択されたソースをダウンロード
     * @param {string} [theme] - 人が入力した調査テーマ（query）。PDF冒頭タイトルに使用
     */
    async downloadSelectedSources(sources, researchId, theme) {
        const selectedIndices = [];
        sources.forEach((_, index) => {
            const checkbox = document.getElementById(`source-checkbox-${researchId}-${index}`);
            if (checkbox && checkbox.checked) {
                selectedIndices.push(index);
            }
        });

        if (selectedIndices.length === 0) {
            this.showNotification('ソースを選択してください', 'warning');
            return;
        }

        this.showNotification(`📄 ${selectedIndices.length}件のファイルを準備中...`, 'info');

        for (const index of selectedIndices) {
            const source = sources[index];
            const url = source.url || '';
            const isPdfUrl = url.toLowerCase().endsWith('.pdf') || url.toLowerCase().includes('.pdf');

            try {
                if (isPdfUrl) {
                    // PDFファイルの場合はそのままダウンロード
                    const response = await fetch(url, {
                        method: 'GET',
                        mode: 'cors',
                        headers: {
                            'Accept': 'application/pdf,application/octet-stream,*/*',
                        }
                    });

                    if (response.ok) {
                        const blob = await response.blob();
                        const downloadUrl = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = downloadUrl;
                        a.download = url.split('/').pop().split('?')[0] || `source_${index + 1}.pdf`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(downloadUrl);
                    } else {
                        this.showNotification(`PDFファイルの取得に失敗しました: ${source.title}`, 'error');
                    }
                } else {
                    // HTMLのURLの場合はPDFに変換
                    this.showNotification(`📄 PDFを生成中: ${source.title}...`, 'info');
                    
                    const queryForPdf = theme || '参照ソース';
                    const result = await api.generateSourcePdf(source, queryForPdf);
                    if (result.success && result.saved) {
                        this.showNotification(`✅ PDFをサーバーの保存先に保存しました: ${source.title}`, 'success');
                    } else if (result.success && result.blob) {
                        const downloadUrl = URL.createObjectURL(result.blob);
                        const a = document.createElement('a');
                        a.href = downloadUrl;
                        const safeTitle = source.title ? source.title.replace(/[\\/:*?"<>|]/g, '_').substring(0, 80) : 'source';
                        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
                        a.download = result.filename || `${safeTitle}_${timestamp}.pdf`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(downloadUrl);
                        this.showNotification(`✅ PDFを生成しました: ${source.title}`, 'success');
                    } else {
                        this.showNotification(`PDF生成エラー (${source.title}): ${result.error}`, 'error');
                    }
                }
            } catch (error) {
                this.showNotification(`ダウンロードエラー (${source.title}): ${error.message}`, 'error');
            }
        }

        this.showNotification(`✅ ${selectedIndices.length}件の処理が完了しました`, 'success');
    }

    /**
     * レポートをダウンロード（DOWNLOAD_SAVE_DIR が設定されている場合はサーバー側にのみ保存）
     */
    async downloadReport(result, researchId) {
        let content = `# ${result.theme || 'リサーチレポート'}\n\n`;
        content += `## レポート情報\n\n`;
        content += `- **作成日時**: ${new Date().toLocaleString('ja-JP')}\n`;
        content += `- **リサーチID**: ${researchId}\n`;
        
        if (result.statistics) {
            content += `- **イテレーション回数**: ${result.statistics.iterations || 0}\n`;
            content += `- **収集ソース数**: ${result.statistics.sources_collected || 0}\n`;
        }
        
        content += `\n---\n\n`;
        
        if (result.report && result.report.draft) {
            content += result.report.draft;
        }
        
        if (result.report && result.report.sources) {
            content += `\n\n---\n\n## 📚 参照ソース\n\n`;
            content += `本レポートの作成にあたり、以下の ${result.report.sources.length} 件のソースを参照しました。\n\n`;
            
            result.report.sources.forEach((source, index) => {
                content += `### ${index + 1}. ${source.title || 'N/A'}\n\n`;
                content += `- **URL**: ${source.url || 'N/A'}\n`;
                if (source.summary) {
                    content += `- **要約**: ${source.summary}\n`;
                }
                if (source.relevance_score !== undefined) {
                    content += `- **関連性スコア**: ${source.relevance_score.toFixed(2)}\n`;
                }
                content += `\n`;
            });
        }

        // ファイル名に日本語を残す（禁止文字のみ除去: \ / : * ? " < > | 改行）
        const safeTheme = (result.theme || 'research').substring(0, 50).replace(/[\\/:*?"<>|\n\r]/g, '_').trim() || 'research';
        const downloadFilename = `report_${safeTheme}_${new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19)}.md`;
        // DOWNLOAD_SAVE_DIR が設定されている場合はサーバー側にのみ保存し、ブラウザのダウンロードフォルダには保存しない
        const exportRes = await api.exportReport(researchId, content, downloadFilename);
        if (exportRes.saved) {
            this.showNotification('レポートをサーバーの保存先に保存しました', 'success');
            return;
        }
        const blob = new Blob([content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = downloadFilename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

// グローバルUIインスタンス
const ui = new UI();
