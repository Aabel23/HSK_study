(function () {
    "use strict";

    window.PageControllers = window.PageControllers || {};
    window.PageControllers.flashcard = async function (options = {}) {
        let session = null;
        let items = [];
        let index = 0;
        let saving = false;
        let completed = false;
        const scores = { forgot: 0, hard: 0, remembered: 0 };
        const setup = document.getElementById("flashcard-setup");
        const sessionView = document.getElementById("flashcard-session");
        const resultView = document.getElementById("flashcard-result");
        const state = document.getElementById("flashcard-state");
        const card = document.getElementById("flashcard");
        const ratingArea = document.getElementById("rating-area");
        const startButton = document.getElementById("start-flashcard");

        startButton.addEventListener("click", startSession);
        card.addEventListener("click", () => {
            if (!card.classList.contains("flipped")) {
                card.classList.add("flipped");
                ratingArea.hidden = false;
            }
        });
        document.querySelectorAll("[data-result]").forEach((button) => button.addEventListener("click", () => rateCard(button.dataset.result)));
        document.getElementById("restart-flashcard").addEventListener("click", startSession);
        document.getElementById("exit-flashcard").addEventListener("click", () => finishSession(true));
        document.querySelectorAll("[data-go-dashboard]").forEach((button) => button.addEventListener("click", () => window.navigateTo("dashboard")));

        async function startSession() {
            if (saving) return;
            completed = false;
            Object.keys(scores).forEach((key) => { scores[key] = 0; });
            index = 0;
            setup.hidden = true; sessionView.hidden = true; resultView.hidden = true; state.hidden = false;
            state.innerHTML = '<div class="page-loading"><span class="spinner"></span><p>Đang chuẩn bị thẻ...</p></div>';
            window.App.setButtonLoading(startButton, true, "Đang tạo phiên...");
            try {
                const count = Number(document.getElementById("flashcard-count").value);
                const includeMastered = document.getElementById("include-mastered").checked;
                session = await window.api.apiPost("/flashcard/session", { count, include_mastered: includeMastered });
                items = shuffle([...session.items]);
                state.hidden = true; sessionView.hidden = false;
                renderCard();
            } catch (error) {
                window.App.renderError(state, error.message, startSession);
                setup.hidden = false;
            } finally { window.App.setButtonLoading(startButton, false); }
        }

        function shuffle(array) {
            for (let current = array.length - 1; current > 0; current -= 1) {
                const swap = Math.floor(Math.random() * (current + 1));
                [array[current], array[swap]] = [array[swap], array[current]];
            }
            return array;
        }

        function renderCard() {
            const item = items[index];
            card.classList.remove("flipped"); ratingArea.hidden = true;
            document.getElementById("flashcard-position").textContent = `Thẻ ${index + 1} / ${items.length}`;
            document.getElementById("flashcard-progress").style.width = `${index / items.length * 100}%`;
            document.getElementById("card-topic").textContent = item.topic || "HSK1";
            document.getElementById("card-front-hanzi").textContent = item.hanzi;
            document.getElementById("card-back-hanzi").textContent = item.hanzi;
            document.getElementById("card-pinyin").textContent = item.pinyin;
            document.getElementById("card-meaning").textContent = item.meaning;
            document.getElementById("card-example").textContent = item.example || "";
            document.getElementById("card-example-pinyin").textContent = item.example_pinyin || "";
            document.getElementById("card-example-meaning").textContent = item.example_meaning || "";
        }

        async function rateCard(result) {
            if (saving || !card.classList.contains("flipped")) return;
            saving = true;
            const buttons = document.querySelectorAll("[data-result]");
            buttons.forEach((button) => { button.disabled = true; });
            try {
                await window.api.apiPost("/flashcard/review", {
                    session_id: session.session_id,
                    vocabulary_id: items[index].id,
                    result,
                });
                scores[result] += 1;
                index += 1;
                if (index >= items.length) await finishSession(false);
                else renderCard();
            } catch (error) {
                window.App.showToast(error.message, "error");
            } finally {
                saving = false;
                buttons.forEach((button) => { button.disabled = false; });
            }
        }

        async function finishSession(early) {
            if (!session || completed || (early && saving)) return;
            if (early && index === 0) {
                sessionView.hidden = true; setup.hidden = false;
                return;
            }
            completed = true;
            const reviewed = scores.forgot + scores.hard + scores.remembered;
            try {
                await window.api.apiPost(`/flashcard/session/${session.session_id}/complete`, {
                    total_items: reviewed,
                    correct_items: scores.remembered,
                    incorrect_items: scores.forgot + scores.hard,
                });
            } catch (error) {
                completed = false;
                window.App.showToast(`Chưa thể kết thúc phiên: ${error.message}`, "error");
                return;
            }
            sessionView.hidden = true; setup.hidden = true; resultView.hidden = false;
            document.getElementById("flashcard-result-stats").innerHTML = `
                <div><strong>${reviewed}</strong><small>Tổng số thẻ</small></div>
                <div><strong>${scores.forgot}</strong><small>Chưa nhớ</small></div>
                <div><strong>${scores.hard}</strong><small>Khó</small></div>
                <div><strong>${scores.remembered}</strong><small>Đã nhớ</small></div>`;
        }

        if (options.autoStart) await startSession();
    };
})();
