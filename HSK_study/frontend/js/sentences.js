(function () {
    "use strict";

    window.PageControllers = window.PageControllers || {};
    window.PageControllers.sentences = async function (options = {}) {
        let session = null;
        let items = [];
        let index = 0;
        let answerPositions = [];
        let correctItems = 0;
        let incorrectAttempts = 0;
        let saving = false;
        let solved = false;

        const state = document.getElementById("sentence-state");
        const setup = document.getElementById("sentence-setup");
        const sessionView = document.getElementById("sentence-session");
        const resultView = document.getElementById("sentence-result");
        const workspace = document.getElementById("sentence-workspace");
        const answerZone = document.getElementById("sentence-answer");
        const tokenBank = document.getElementById("sentence-token-bank");
        const feedback = document.getElementById("sentence-feedback");
        const checkButton = document.getElementById("check-sentence");
        const nextButton = document.getElementById("next-sentence");
        const resetButton = document.getElementById("reset-sentence");
        const startButton = document.getElementById("start-sentences");
        const pinyinToggle = document.getElementById("toggle-pinyin");
        const vietnameseToggle = document.getElementById("toggle-vietnamese");

        startButton.addEventListener("click", startSession);
        document.getElementById("restart-sentences").addEventListener("click", startSession);
        document.querySelectorAll("[data-go-dashboard]").forEach((button) => button.addEventListener("click", () => window.navigateTo("dashboard")));
        pinyinToggle.addEventListener("change", applySubtitleOptions);
        vietnameseToggle.addEventListener("change", applySubtitleOptions);
        answerZone.addEventListener("click", handleTokenClick);
        tokenBank.addEventListener("click", handleTokenClick);
        resetButton.addEventListener("click", resetAnswer);
        checkButton.addEventListener("click", checkAnswer);
        nextButton.addEventListener("click", nextSentence);

        async function loadTopics() {
            const data = await window.api.apiGet("/sentences/topics");
            document.getElementById("sentence-topic").insertAdjacentHTML(
                "beforeend",
                data.items.map((topic) => `<option value="${window.App.escapeHTML(topic)}">${window.App.escapeHTML(topic)}</option>`).join("")
            );
        }

        async function startSession() {
            if (saving) return;
            setup.hidden = true; sessionView.hidden = true; resultView.hidden = true; state.hidden = false;
            state.innerHTML = '<div class="page-loading"><span class="spinner"></span><p>Đang chuẩn bị câu và xáo trộn cụm từ...</p></div>';
            window.App.setButtonLoading(startButton, true, "Đang tạo phiên...");
            try {
                const count = Number(document.getElementById("sentence-count").value);
                const topic = document.getElementById("sentence-topic").value || null;
                session = await window.api.apiPost("/sentences/session", { count, topic });
                items = session.items;
                index = 0; correctItems = 0; incorrectAttempts = 0;
                state.hidden = true; sessionView.hidden = false;
                renderSentence();
            } catch (error) {
                window.App.renderError(state, error.message, startSession);
                setup.hidden = false;
            } finally { window.App.setButtonLoading(startButton, false); }
        }

        function applySubtitleOptions() {
            workspace.classList.toggle("hide-pinyin", !pinyinToggle.checked);
            workspace.classList.toggle("hide-vietnamese", !vietnameseToggle.checked);
        }

        function renderSentence() {
            const item = items[index];
            answerPositions = []; solved = false;
            document.getElementById("sentence-position").textContent = `Câu ${index + 1} / ${items.length}`;
            document.getElementById("sentence-progress").style.width = `${index / items.length * 100}%`;
            document.getElementById("sentence-correct").textContent = correctItems;
            document.getElementById("sentence-incorrect").textContent = incorrectAttempts;
            document.getElementById("sentence-topic-label").textContent = item.topic || "HSK1";
            document.getElementById("sentence-meaning").textContent = item.meaning;
            feedback.hidden = true; feedback.className = "sentence-feedback"; feedback.innerHTML = "";
            checkButton.hidden = false; checkButton.disabled = true;
            resetButton.hidden = false; nextButton.hidden = true;
            nextButton.innerHTML = index === items.length - 1 ? "Xem tổng kết <span>→</span>" : "Câu tiếp theo <span>→</span>";
            applySubtitleOptions();
            renderTokens();
        }

        function renderTokens() {
            const item = items[index];
            const byPosition = new Map(item.tokens.map((token) => [token.position, token]));
            const available = item.tokens.filter((token) => !answerPositions.includes(token.position));
            answerZone.innerHTML = answerPositions.length
                ? answerPositions.map((position) => renderToken(byPosition.get(position), "answer")).join("")
                : '<span class="sentence-placeholder">Chọn các cụm từ bên dưới...</span>';
            tokenBank.innerHTML = available.length
                ? available.map((token) => renderToken(token, "bank")).join("")
                : '<span class="sentence-placeholder">Tất cả cụm từ đã được đưa vào câu.</span>';
            checkButton.disabled = saving || solved || answerPositions.length !== item.tokens.length;
        }

        function renderToken(token, source) {
            return `<button class="sentence-token" type="button" data-position="${token.position}" data-source="${source}" ${solved ? "disabled" : ""}><strong>${window.App.escapeHTML(token.text)}</strong><small>${window.App.escapeHTML(token.pinyin)}</small></button>`;
        }

        function handleTokenClick(event) {
            const button = event.target.closest("button[data-position]");
            if (!button || saving || solved) return;
            const position = Number(button.dataset.position);
            if (button.dataset.source === "bank") answerPositions.push(position);
            else answerPositions = answerPositions.filter((item) => item !== position);
            feedback.hidden = true;
            renderTokens();
        }

        function resetAnswer() {
            if (saving || solved) return;
            answerPositions = [];
            feedback.hidden = true;
            renderTokens();
        }

        async function checkAnswer() {
            if (saving || solved || answerPositions.length !== items[index].tokens.length) return;
            saving = true;
            window.App.setButtonLoading(checkButton, true, "Đang kiểm tra...");
            try {
                const response = await window.api.apiPost("/sentences/attempt", {
                    session_id: session.session_id,
                    sentence_id: items[index].id,
                    ordered_positions: answerPositions,
                });
                feedback.hidden = false;
                if (response.is_correct) {
                    solved = true; correctItems += 1;
                    feedback.className = "sentence-feedback correct";
                    feedback.innerHTML = `<strong>Chính xác! Câu hoàn chỉnh:</strong><div class="answer-hanzi">${window.App.escapeHTML(response.answer.hanzi)}</div><span class="answer-pinyin">${window.App.escapeHTML(response.answer.pinyin)}</span><span class="answer-meaning">${window.App.escapeHTML(response.answer.meaning)}</span>`;
                    checkButton.hidden = true; resetButton.hidden = true; nextButton.hidden = false;
                    document.getElementById("sentence-correct").textContent = correctItems;
                } else {
                    incorrectAttempts += 1;
                    feedback.className = "sentence-feedback wrong";
                    feedback.innerHTML = "<strong>Thứ tự chưa đúng.</strong><span>Hãy xem lại vị trí các cụm từ rồi thử lại; đáp án chưa được tiết lộ.</span>";
                    document.getElementById("sentence-incorrect").textContent = incorrectAttempts;
                }
            } catch (error) {
                window.App.showToast(error.message, "error");
            } finally {
                saving = false;
                window.App.setButtonLoading(checkButton, false);
                renderTokens();
            }
        }

        async function nextSentence() {
            if (!solved || saving) return;
            if (index < items.length - 1) {
                index += 1;
                renderSentence();
                return;
            }
            await finishSession();
        }

        async function finishSession() {
            saving = true;
            window.App.setButtonLoading(nextButton, true, "Đang lưu tổng kết...");
            try {
                await window.api.apiPost(`/sentences/session/${session.session_id}/complete`, {
                    total_items: items.length,
                    correct_items: correctItems,
                    incorrect_items: incorrectAttempts,
                });
                const attempts = correctItems + incorrectAttempts;
                const accuracy = attempts ? Math.round(correctItems / attempts * 100) : 0;
                sessionView.hidden = true; resultView.hidden = false;
                document.getElementById("sentence-result-stats").innerHTML = `
                    <div><strong>${items.length}</strong><small>Tổng số câu</small></div>
                    <div><strong>${correctItems}</strong><small>Câu hoàn thành</small></div>
                    <div><strong>${incorrectAttempts}</strong><small>Lần thử lại</small></div>
                    <div><strong>${accuracy}%</strong><small>Độ chính xác</small></div>`;
            } catch (error) {
                window.App.showToast(`Chưa thể lưu tổng kết: ${error.message}`, "error");
            } finally {
                saving = false;
                window.App.setButtonLoading(nextButton, false);
            }
        }

        try { await loadTopics(); }
        catch (error) { window.App.showToast(`Không tải được chủ đề câu: ${error.message}`, "error"); }
        if (options.autoStart) await startSession();
    };
})();

