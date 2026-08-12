(function () {
    "use strict";

    window.PageControllers = window.PageControllers || {};
    window.PageControllers.vocabulary = async function () {
        const pageSize = 20;
        let offset = 0;
        let searchTimer = null;
        let requestToken = 0;
        const state = document.getElementById("vocabulary-state");
        const content = document.getElementById("vocabulary-content");
        const list = document.getElementById("vocabulary-list");
        const countLabel = document.getElementById("vocabulary-count");
        const search = document.getElementById("vocabulary-search");
        const topic = document.getElementById("topic-filter");
        const status = document.getElementById("status-filter");
        const dialog = document.getElementById("word-dialog");

        document.getElementById("vocabulary-filters").addEventListener("submit", (event) => event.preventDefault());
        document.getElementById("dialog-close").addEventListener("click", () => dialog.close());
        dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
        search.addEventListener("input", () => {
            window.clearTimeout(searchTimer);
            searchTimer = window.setTimeout(() => { offset = 0; loadVocabulary(); }, 320);
        });
        topic.addEventListener("change", () => { offset = 0; loadVocabulary(); });
        status.addEventListener("change", () => { offset = 0; loadVocabulary(); });
        document.getElementById("clear-filters").addEventListener("click", () => {
            search.value = ""; topic.value = ""; status.value = ""; offset = 0; loadVocabulary();
        });

        list.addEventListener("click", async (event) => {
            const button = event.target.closest("button[data-action]");
            if (!button) return;
            const vocabularyId = Number(button.dataset.id);
            if (button.dataset.action === "detail") await openDetail(vocabularyId);
            else await markStatus(vocabularyId, button.dataset.action, button);
        });

        async function loadTopics() {
            const data = await window.api.apiGet("/vocabulary/topics");
            topic.insertAdjacentHTML("beforeend", data.items.map((item) => `<option value="${window.App.escapeHTML(item)}">${window.App.escapeHTML(item)}</option>`).join(""));
        }

        async function loadVocabulary() {
            const token = ++requestToken;
            state.hidden = false; content.hidden = true;
            state.innerHTML = '<div class="page-loading"><span class="spinner"></span><p>Đang tải từ vựng...</p></div>';
            const params = new URLSearchParams({ limit: pageSize, offset });
            if (search.value.trim()) params.set("search", search.value.trim());
            if (topic.value) params.set("topic", topic.value);
            if (status.value) params.set("status", status.value);
            try {
                const data = await window.api.apiGet(`/vocabulary?${params}`);
                if (token !== requestToken) return;
                countLabel.textContent = `Tìm thấy ${data.total} từ`;
                if (!data.items.length) {
                    state.innerHTML = '<div class="state-card"><div><span>⌕</span><h3>Không tìm thấy từ phù hợp</h3><p>Hãy thử từ khóa khác hoặc xóa bớt bộ lọc.</p><button class="button button-secondary" id="empty-clear" type="button">Xóa bộ lọc</button></div></div>';
                    document.getElementById("empty-clear").addEventListener("click", () => document.getElementById("clear-filters").click());
                    return;
                }
                list.innerHTML = data.items.map(renderRow).join("");
                renderPagination(data.total);
                state.hidden = true; content.hidden = false;
            } catch (error) {
                if (token !== requestToken) return;
                countLabel.textContent = "Không tải được danh sách";
                window.App.renderError(state, error.message, loadVocabulary);
            }
        }

        function renderRow(item) {
            return `<tr>
                <td><div class="word-cell"><span class="word-hanzi">${window.App.escapeHTML(item.hanzi)}</span><span><strong>${window.App.escapeHTML(item.hanzi)}</strong><small>${window.App.escapeHTML(item.pinyin)}</small></span></div></td>
                <td>${window.App.escapeHTML(item.meaning)}</td>
                <td><span class="topic-chip">${window.App.escapeHTML(item.topic || "Khác")}</span></td>
                <td><span class="status-badge ${item.status}">${window.App.statusLabels[item.status]}</span></td>
                <td><div class="row-actions"><button class="row-button" data-action="detail" data-id="${item.id}" type="button">Chi tiết</button><button class="row-button mark-action" data-action="review" data-id="${item.id}" type="button">Cần ôn</button><button class="row-button mark-action" data-action="mastered" data-id="${item.id}" type="button">Đã thuộc</button></div></td>
            </tr>`;
        }

        function renderPagination(total) {
            const pageCount = Math.ceil(total / pageSize);
            const current = Math.floor(offset / pageSize) + 1;
            const start = Math.max(1, current - 2);
            const end = Math.min(pageCount, start + 4);
            const buttons = [`<button type="button" data-page="${current - 1}" ${current === 1 ? "disabled" : ""}>‹</button>`];
            for (let page = start; page <= end; page += 1) buttons.push(`<button type="button" data-page="${page}" class="${page === current ? "active" : ""}">${page}</button>`);
            buttons.push(`<button type="button" data-page="${current + 1}" ${current === pageCount ? "disabled" : ""}>›</button>`);
            const pagination = document.getElementById("vocabulary-pagination");
            pagination.innerHTML = buttons.join("");
            pagination.querySelectorAll("button:not(:disabled)").forEach((button) => button.addEventListener("click", () => {
                offset = (Number(button.dataset.page) - 1) * pageSize;
                loadVocabulary();
                window.scrollTo({ top: 0, behavior: "smooth" });
            }));
        }

        async function openDetail(vocabularyId) {
            document.getElementById("word-detail").innerHTML = '<div class="page-loading compact"><span class="spinner"></span><p>Đang tải...</p></div>';
            dialog.showModal();
            try {
                const item = await window.api.apiGet(`/vocabulary/${vocabularyId}`);
                document.getElementById("word-detail").innerHTML = `
                    <div class="detail-head"><strong>${window.App.escapeHTML(item.hanzi)}</strong><span>${window.App.escapeHTML(item.pinyin)}</span></div>
                    <div class="detail-body"><div class="detail-meaning">${window.App.escapeHTML(item.meaning)}</div>
                    <div class="example-box"><span class="eyebrow">Câu ví dụ</span><strong>${window.App.escapeHTML(item.example || "Chưa có ví dụ")}</strong><span class="pinyin">${window.App.escapeHTML(item.example_pinyin || "")}</span><p>${window.App.escapeHTML(item.example_meaning || "")}</p></div>
                    <div class="detail-actions"><button class="button button-secondary" type="button" data-dialog-status="review">Đánh dấu cần ôn</button><button class="button button-primary" type="button" data-dialog-status="mastered">Đánh dấu đã thuộc</button></div></div>`;
                document.querySelectorAll("[data-dialog-status]").forEach((button) => button.addEventListener("click", async () => {
                    await markStatus(item.id, button.dataset.dialogStatus, button);
                    dialog.close();
                }));
            } catch (error) {
                document.getElementById("word-detail").innerHTML = `<div class="state-card"><div><span>!</span><h3>Không tải được chi tiết</h3><p>${window.App.escapeHTML(error.message)}</p></div></div>`;
            }
        }

        async function markStatus(vocabularyId, nextStatus, button) {
            window.App.setButtonLoading(button, true);
            try {
                await window.api.apiPost("/progress/status", { vocabulary_id: vocabularyId, status: nextStatus });
                window.App.showToast(nextStatus === "review" ? "Đã thêm vào danh sách cần ôn." : "Đã đánh dấu từ đã thuộc.");
                await loadVocabulary();
            } catch (error) {
                window.App.showToast(error.message, "error");
            } finally { window.App.setButtonLoading(button, false); }
        }

        try { await loadTopics(); } catch (error) { window.App.showToast(`Không tải được chủ đề: ${error.message}`, "error"); }
        await loadVocabulary();
        return () => window.clearTimeout(searchTimer);
    };
})();

