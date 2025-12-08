let questions = [];
let currentIndex = 0;
let score = 0;
let currentTopic = ""; // Для хранения выбранной темы

// Ссылки на DOM элементы
const block1 = document.getElementById("block1");
const block2 = document.getElementById("block2");
const block3 = document.getElementById("block3");
const addForm = document.getElementById("addForm");
const resultsBlock = document.getElementById("resultsBlock");

const topicsList = document.getElementById("topics-list");
const adminControls = document.getElementById("admin-controls");
const container = document.getElementById("new-questions-container");
const addTopicBtn = document.getElementById("add_topic_btn");
const saveAllBtn = document.getElementById("saveAllBtn");
const addBlockBtn = document.getElementById("add-block-btn");
const topicNameInput = document.getElementById("topicNameInput");
const resultsTableBody = document.getElementById("resultsTableBody");
const closeResultsBtn = document.getElementById("closeResults");
const backToMenuBtn = document.getElementById("back-to-menu");

// Элементы для прохождения теста
const questEl = document.getElementById("quest1");
const answerBtns = document.querySelectorAll(".answer");
const progressBar = document.getElementById("progress-bar");
const progressText = document.getElementById("progress-text");
const finalScoreVal = document.getElementById("final-score-val");
const finalScoreText = document.getElementById("final-score-text");

// --- ОБЩАЯ ЛОГИКА И ИНИЦИАЛИЗАЦИЯ ---

document.addEventListener("DOMContentLoaded", () => {
    // Показываем админку, если роль admin
    if (typeof CURRENT_ROLE !== 'undefined' && CURRENT_ROLE === "admin") {
        adminControls.style.display = "block";
    }
    // Грузим темы
    loadTopics();
});

// --- 1. ЗАГРУЗКА ТЕМ И МЕНЮ ---

async function loadTopics() {
    try {
        const res = await fetch("/api/topics");
        const data = await res.json();
        
        topicsList.innerHTML = "";
        const dataList = document.getElementById("topics-datalist");
        if(dataList) dataList.innerHTML = ""; // Очистить подсказки для админки

        if (data.topics.length === 0) {
            topicsList.innerHTML = "<p>Нет доступных тестов. Администратор может добавить их.</p>";
        } else {
            data.topics.forEach(topic => {
                // Кнопка для выбора темы
                const btn = document.createElement("button");
                btn.textContent = topic;
                btn.className = "btn-topic";
                btn.onclick = () => startQuiz(topic);
                topicsList.appendChild(btn);

                // Опция для автодополнения в админской форме
                if (dataList) {
                    const option = document.createElement("option");
                    option.value = topic;
                    dataList.appendChild(option);
                }
            });
        }
    } catch (error) {
        console.error("Ошибка загрузки тем:", error);
        topicsList.innerHTML = "<p>Ошибка загрузки тем.</p>";
    }
}

async function startQuiz(topic) {
    currentTopic = topic;
    questions = await loadQuestions(topic);
    
    if (questions.length === 0) {
        alert(`Тема "${topic}" не содержит вопросов.`);
        return;
    }

    currentIndex = 0;
    score = 0;
    block1.style.display = "none";
    block2.style.display = "block";
    displayQuestion();
}

async function loadQuestions(topic) {
    const response = await fetch(`/api/questions?topic=${encodeURIComponent(topic)}`);
    if (response.status === 200) {
        return await response.json();
    }
    return [];
}


// --- 2. ЛОГИКА ТЕСТА ---

function displayQuestion() {
    if (currentIndex >= questions.length) {
        finishQuiz();
        return;
    }

    const q = questions[currentIndex];
    questEl.textContent = q.question;

    answerBtns.forEach((btn, index) => {
        btn.textContent = q.answers[index];
        btn.onclick = () => checkAnswer(index, q.correct);
        btn.disabled = false;
        btn.classList.remove('correct', 'incorrect');
    });

    // Обновление прогресса
    const progress = ((currentIndex + 1) / questions.length) * 100;
    progressBar.style.width = `${progress}%`;
    progressText.textContent = `Вопрос ${currentIndex + 1} из ${questions.length} (Тема: ${currentTopic})`;
}

function checkAnswer(selectedIndex, correctIndex) {
    // Отключаем все кнопки после ответа
    answerBtns.forEach(btn => btn.disabled = true);

    if (selectedIndex === correctIndex) {
        score++;
        answerBtns[selectedIndex].classList.add('correct');
    } else {
        answerBtns[selectedIndex].classList.add('incorrect');
        answerBtns[correctIndex].classList.add('correct'); // Показываем правильный
    }

    // Переход к следующему вопросу через 1.5 секунды
    setTimeout(() => {
        currentIndex++;
        displayQuestion();
    }, 1500);
}

async function finishQuiz() {
    block2.style.display = "none";
    block3.style.display = "block";
    
    const total = questions.length;
    const percentage = Math.round((score / total) * 100);

    finalScoreVal.textContent = `${score}/${total}`;
    finalScoreText.textContent = `Ваш результат: ${percentage}%`;

    // Отправка результата на сервер
    const ok = await saveResultApi(score, total, currentTopic);
    if (!ok) {
        console.error("Ошибка сохранения результата.");
    }
}

// Кнопка "В главное меню"
if(backToMenuBtn) {
    backToMenuBtn.onclick = () => {
        block3.style.display = "none";
        block1.style.display = "block";
    };
}

// --- 3. АДМИНСКАЯ ЛОГИКА ДОБАВЛЕНИЯ ВОПРОСОВ ---

let questionBlockCounter = 0;

if (addTopicBtn) {
    addTopicBtn.onclick = () => {
        block1.style.display = "none";
        addForm.style.display = "block";
        container.innerHTML = ''; // Очистка
        questionBlockCounter = 0;
        topicNameInput.value = '';
        addQuestionBlock(); // Добавляем первый вопрос
    };
}

if (addBlockBtn) {
    addBlockBtn.onclick = addQuestionBlock;
}

// Добавление HTML для одного вопроса
function addQuestionBlock() {
    questionBlockCounter++;
    const block = document.createElement('div');
    block.className = 'question-block';
    block.setAttribute('data-index', questionBlockCounter);
    block.innerHTML = `
        <fieldset class="question-fieldset">
            <legend>Вопрос ${questionBlockCounter}</legend>
            <input type="text" class="q-text" placeholder="Текст вопроса"><br>
            <div class="answers-grid">
                <input type="text" class="q-answer" placeholder="Ответ 0"><br>
                <input type="text" class="q-answer" placeholder="Ответ 1"><br>
                <input type="text" class="q-answer" placeholder="Ответ 2"><br>
                <input type="text" class="q-answer" placeholder="Ответ 3"><br>
            </div>
            <label>Номер правильного ответа (0-3):</label>
            <input type="number" class="q-correct" min="0" max="3" value="0"><br>
            <button type="button" class="remove-question-btn" style="background:#f44336; margin-top:10px;">Удалить</button>
        </fieldset>
    `;
    container.appendChild(block);
    
    // Логика удаления
    block.querySelector('.remove-question-btn').onclick = () => {
        block.remove();
        // Пересчет заголовков (опционально, но полезно)
        document.querySelectorAll('.question-block').forEach((b, i) => {
            b.querySelector('legend').textContent = `Вопрос ${i + 1}`;
        });
    };
}

// Сохранение всех вопросов в тему
if (saveAllBtn) {
    saveAllBtn.onclick = async () => {
        const topicName = topicNameInput.value.trim();
        if (!topicName) {
            alert("Введите название темы!");
            return;
        }

        const questionBlocks = document.querySelectorAll('#new-questions-container .question-block');
        const payloadQuestions = [];
        let hasError = false;

        questionBlocks.forEach(block => {
            const qText = block.querySelector('.q-text').value.trim();
            const answers = Array.from(block.querySelectorAll('.q-answer')).map(i => i.value.trim());
            const correct = parseInt(block.querySelector('.q-correct').value.trim(), 10);

            if (!qText || answers.some(a => !a) || Number.isNaN(correct) || correct < 0 || correct > 3) {
                hasError = true;
                return;
            }

            payloadQuestions.push({ question: qText, answers, correct });
        });

        if (payloadQuestions.length === 0) {
            alert("Добавьте хотя бы один вопрос.");
            return;
        }

        if (hasError) {
            alert("Ошибка: Заполните ВСЕ поля во всех вопросах.");
            return;
        }

        // Отправляем на новый роут /api/save_topic
        const resp = await fetch("/api/save_topic", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                topic_name: topicName,
                questions: payloadQuestions
            })
        });

        const resJson = await resp.json();
        if (resp.ok) {
            alert(`Успешно сохранено ${payloadQuestions.length} вопросов в тему "${topicName}"`);
            addForm.style.display = "none";
            block1.style.display = "block";
            loadTopics(); // Обновить список тем
        } else {
            alert("Ошибка сохранения: " + resJson.detail || resJson.message);
        }
    };
}

document.getElementById("cancelAdd").onclick = () => {
    addForm.style.display = "none";
    block1.style.display = "block";
};

// --- 4. ПРОСМОТР РЕЗУЛЬТАТОВ (Админ) ---

const resBtn = document.getElementById("results_but");

async function loadResults() {
    try {
        const res = await fetch("/api/results");
        if (res.status === 403) {
            alert("У вас нет прав для просмотра результатов.");
            return [];
        }
        return await res.json();
    } catch (e) {
        console.error("Error loading results:", e);
        return [];
    }
}

if (resBtn) {
    resBtn.onclick = async () => {
        const data = await loadResults();
        resultsTableBody.innerHTML = "";

        if (data.length === 0) {
            resultsTableBody.innerHTML = '<tr><td colspan="4">Нет сохраненных результатов.</td></tr>';
        } else {
            data.forEach(r => {
                const row = document.createElement("tr");
                const date = new Date().toLocaleDateString(); // Дата для примера, так как в CSV ее нет
                row.innerHTML = `
                    <td>${r.username}</td>
                    <td>${r.topic || 'Не указана'}</td>
                    <td>${r.score} из ${r.total}</td>
                    <td>${date}</td>
                `;
                resultsTableBody.appendChild(row);
            });
        }
        block1.style.display = "none";
        resultsBlock.style.display = "block";
    };
}

if (closeResultsBtn) {
    closeResultsBtn.onclick = () => {
        resultsBlock.style.display = "none";
        block1.style.display = "block";
    };
}

// --- 5. ФУНКЦИЯ API ДЛЯ СОХРАНЕНИЯ РЕЗУЛЬТАТА ---

async function saveResultApi(score, total, topic) {
    const data = { score, total, topic }; // Включаем тему
    const response = await fetch("/api/results", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    return response.ok;
}