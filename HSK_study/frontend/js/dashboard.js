(function () {
    "use strict";

    window.PageControllers = window.PageControllers || {};
    window.PageControllers.dashboard = async function () {
        const state = document.getElementById("dashboard-state");
        const content = document.getElementById("dashboard-content");

        document.getElementById("dashboard-flashcard").addEventListener("click", () => window.navigateTo("flashcard", { autoStart: true }));
        document.getElementById("dashboard-matching").addEventListener("click", () => window.navigateTo("matching", { autoStart: true }));
        document.getElementById("dashboard-sentences").addEventListener("click", () => window.navigateTo("sentences", { autoStart: true }));

        async function load() {
            state.hidden = false;
            content.hidden = true;
            state.innerHTML = '<div class="page-loading compact"><span class="spinner"></span><p>Đang tải thống kê...</p></div>';
            try {
                const data = await window.api.apiGet("/dashboard");
                render(data);
                state.hidden = true;
                content.hidden = false;
            } catch (error) {
                window.App.renderError(state, error.message, load);
            }
        }

        function render(data) {
            const stats = [
                ["Tổng từ HSK1", data.total_vocabulary, "Toàn bộ từ nền tảng", "词"],
                ["Từ đã xem", data.viewed_vocabulary, "Đã bắt đầu làm quen", "◉"],
                ["Đang học", data.learning_vocabulary, "Đang xây trí nhớ", "↗"],
                ["Cần ôn", data.review_vocabulary, "Nên xem lại sớm", "!"],
                ["Đã thuộc", data.mastered_vocabulary, "Nhớ đúng từ 3 lần", "✓"],
            ];
            document.getElementById("dashboard-stats").innerHTML = stats.map(([label, value, note, icon]) => `
                <article class="stat-card"><span class="stat-icon">${icon}</span><small>${label}</small><strong>${value}</strong><span class="stat-note">${note}</span></article>
            `).join("");

            const recent = document.getElementById("recent-vocabulary");
            recent.innerHTML = data.recent_vocabulary.length ? data.recent_vocabulary.map((item) => `
                <div class="recent-item">
                    <span class="recent-hanzi">${window.App.escapeHTML(item.hanzi)}</span>
                    <span><strong>${window.App.escapeHTML(item.meaning)}</strong><small>${window.App.escapeHTML(item.pinyin)}</small></span>
                    <span class="status-badge ${item.status}">${window.App.statusLabels[item.status]}</span>
                </div>
            `).join("") : '<div class="empty-inline">Chưa có từ nào được học. Bắt đầu một phiên Flashcard nhé!</div>';

            const accuracy = Math.max(0, Math.min(100, data.matching_accuracy));
            document.getElementById("matching-overview").innerHTML = `
                <div class="accuracy-display">
                    <div class="accuracy-circle" style="--accuracy:${accuracy}%"><strong>${accuracy}%</strong></div>
                    <div class="accuracy-copy"><strong>${data.matching_sessions}</strong><span>lượt chơi đã hoàn thành hoặc đang chơi</span></div>
                </div>
                <div class="matching-mini"><div><strong>${data.matching_correct}</strong><small>Cặp nối đúng</small></div><div><strong>${data.matching_incorrect}</strong><small>Lần nối sai</small></div></div>
            `;
            const sentenceAccuracy = Math.max(0, Math.min(100, data.sentence_accuracy));
            document.getElementById("sentence-overview").innerHTML = `
                <div class="sentence-dashboard-mark"><span>句</span><div><strong>${data.sentence_sessions}</strong><small>phiên luyện câu</small></div></div>
                <div class="sentence-dashboard-stats"><span><strong>${sentenceAccuracy}%</strong><small>Chính xác</small></span><span><strong>${data.sentence_correct}</strong><small>Câu đúng</small></span><span><strong>${data.sentence_incorrect}</strong><small>Lần thử sai</small></span></div>
            `;
            document.getElementById("view-progress").addEventListener("click", () => window.navigateTo("progress"));
            document.getElementById("view-vocabulary").addEventListener("click", () => window.navigateTo("vocabulary"));
            document.getElementById("view-sentences").addEventListener("click", () => window.navigateTo("sentences"));
        }

        await load();
    };
})();
