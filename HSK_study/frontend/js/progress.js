(function () {
    "use strict";

    window.PageControllers = window.PageControllers || {};
    window.PageControllers.progress = async function () {
        const state = document.getElementById("progress-state");
        const content = document.getElementById("progress-content");

        async function load() {
            state.hidden = false; content.hidden = true;
            state.innerHTML = '<div class="page-loading"><span class="spinner"></span><p>Đang tổng hợp tiến độ...</p></div>';
            try {
                const data = await window.api.apiGet("/progress");
                render(data);
                state.hidden = true; content.hidden = false;
            } catch (error) { window.App.renderError(state, error.message, load); }
        }

        function render(data) {
            const completion = data.completion_percentage;
            document.getElementById("completion-value").textContent = `${completion}%`;
            document.getElementById("completion-copy").textContent = `Bạn đã thuộc ${data.mastered_count} / ${data.total_vocabulary} từ`;
            const ring = document.getElementById("completion-ring");
            ring.style.setProperty("--completion", `${completion}%`);
            ring.querySelector("span").textContent = `${completion}%`;
            const viewed = data.total_vocabulary - data.new_count;
            const stats = [
                ["Từ đã xem", viewed, "◉"], ["Đang học", data.learning_count, "↗"],
                ["Cần ôn", data.review_count, "!"], ["Đã thuộc", data.mastered_count, "✓"],
            ];
            document.getElementById("progress-stats").innerHTML = stats.map(([label, value, icon]) => `<article class="stat-card"><span class="stat-icon">${icon}</span><small>${label}</small><strong>${value}</strong><span class="stat-note">trên ${data.total_vocabulary} từ HSK1</span></article>`).join("");
            document.getElementById("review-badge").textContent = data.review_count;
            document.getElementById("mastered-badge").textContent = data.mastered_count;
            document.getElementById("review-list").innerHTML = renderWords(data.review_items, "Chưa có từ cần ôn. Tiếp tục phát huy!");
            document.getElementById("mastered-list").innerHTML = renderWords(data.mastered_items, "Chưa có từ đã thuộc. Hãy bắt đầu với Flashcard.");
            document.getElementById("recent-sessions").innerHTML = data.recent_sessions.length ? data.recent_sessions.map(renderSession).join("") : '<div class="empty-inline">Chưa có phiên học nào được ghi nhận.</div>';
        }

        function renderWords(items, emptyMessage) {
            if (!items.length) return `<div class="empty-inline">${emptyMessage}</div>`;
            return items.map((item) => `<div class="progress-word"><strong>${window.App.escapeHTML(item.hanzi)}</strong><span><strong>${window.App.escapeHTML(item.meaning)}</strong><small>${window.App.escapeHTML(item.pinyin)}</small></span><small>${item.review_count} lần ôn</small></div>`).join("");
        }

        function renderSession(item) {
            const isFlashcard = item.session_type === "flashcard";
            const isSentence = item.session_type === "sentence";
            const attempts = item.correct_items + item.incorrect_items;
            const accuracy = attempts ? Math.round(item.correct_items / attempts * 100) : 0;
            const icon = isFlashcard ? "卡" : (isSentence ? "句" : "连");
            const label = isFlashcard ? "Flashcard" : (isSentence ? "Luyện câu" : "Nối từ");
            return `<div class="session-item"><span class="session-type-icon">${icon}</span><span><strong>${label}</strong><small>${item.ended_at ? "Đã hoàn thành" : "Chưa kết thúc"} · ${item.total_items} mục</small></span><span class="session-score">${accuracy}%</span><span class="session-date">${window.App.formatDate(item.started_at)}</span></div>`;
        }

        await load();
    };
})();
