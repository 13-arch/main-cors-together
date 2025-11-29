// pract.js — основной скрипт квиза
// Важно: fetch использует credentials чтобы куки шли на сервер

// Состояние
let questions = [];
let currentIndex = 0;
let score = 0;

const username = typeof CURRENT_USER !== 'undefined' ? CURRENT_USER : "Guest";
const role = typeof CURRENT_ROLE !== 'undefined' ? CURRENT_ROLE : "user";

// Элементы
const startBtn = document.getElementById("start_but");
const addBtn = document.getElementById("add_but");
const backBtn = document.getElementById("back");
const saveBtn = document.getElementById("saveQuestion");
const cancelBtn = document.getElementById("cancelAdd");
const resultsBtn = document.getElementById("results_but");
const closeResultsBtn = document.getElementById("closeResults");

const block1 = document.getElementById("block1");
const block2 = document.getElementById("block2");
const block3 = document.getElementById("block3");
const addForm = document.getElementById("addForm");
const resultsBlock = document.getElementById("resultsBlock");
const resultsTableBody = document.querySelector("#resultsTable tbody");

const questEl = document.getElementById("quest1");
const answerBtns = document.querySelectorAll(".answer");
const progressBar = document.getElementById("progress-bar");
const progressText = document.getElementById("progress-text");
const scoreEl = document.getElementById("score");

// Инициализация интерфейса по роли
function initRoleInterface() {
  if (role === "admin") {
    if (addBtn) addBtn.style.display = "inline-block";
    if (resultsBtn) resultsBtn.style.display = "inline-block";
  } else {
    if (addBtn) addBtn.style.display = "none";
    if (resultsBtn) resultsBtn.style.display = "none";
  }
  if (block1) block1.style.display = "block";
}
initRoleInterface();

// Вспомогательная проверка ответа сервера
function ensureOk(res, onUnauthorized, onForbidden) {
  if (res.status === 401) { onUnauthorized?.(); return false; }
  if (res.status === 403) { onForbidden?.(); return false; }
  if (!res.ok) return false;
  return true;
}

// API: загрузка вопросов
async function loadQuestions() {
  try {
    const res = await fetch("/api/questions", { credentials: "same-origin" });
    const ok = ensureOk(res, () => { window.location.href = "/login"; }, () => { alert("Недостаточно прав"); });
    if (!ok) { alert("Не удалось загрузить вопросы."); return; }
    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("application/json")) { alert("Сервер вернул не JSON"); return; }
    questions = await res.json();
  } catch (e) {
    console.error("Ошибка загрузки вопросов", e);
    alert("Не удалось загрузить вопросы.");
  }
}

// API: сохранить вопрос (админ)
async function saveQuestionApi(newQ) {
  try {
    const res = await fetch("/api/questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(newQ)
    });
    const ok = ensureOk(res, () => { window.location.href = "/login"; }, () => { alert("Доступ только для администратора"); });
    if (!ok) { alert("Не удалось сохранить вопрос."); return false; }
    return true;
  } catch (e) {
    console.error("Ошибка сохранения вопроса", e);
    alert("Не удалось сохранить вопрос.");
    return false;
  }
}

// API: отправка результата
async function sendResult(finalScore, total) {
  try {
    await fetch("/api/results", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ username, score: finalScore, total })
    });
  } catch (e) {
    console.error("Ошибка отправки результата", e);
  }
}

// API: загрузка результатов (админ)
async function loadResults() {
  try {
    const res = await fetch("/api/results", { credentials: "same-origin" });
    const ok = ensureOk(res, () => { window.location.href = "/login"; }, () => { alert("Доступ только для администратора"); });
    if (!ok) { alert("Не удалось загрузить результаты."); return []; }
    return await res.json();
  } catch (e) {
    console.error("Ошибка загрузки результатов", e);
    alert("Не удалось загрузить результаты.");
    return [];
  }
}

// Старт теста
if (startBtn) {
  startBtn.onclick = async () => {
    await loadQuestions();
    if (!questions || questions.length === 0) {
      alert("В базе пока нет вопросов!");
      return;
    }
    currentIndex = 0;
    score = 0;
    block1.style.display = "none";
    block2.style.display = "block";
    showQuestion();
  };
}

// Показ вопроса
function showQuestion() {
  if (!questions || questions.length === 0) {
    alert("В базе пока нет вопросов!");
    block1.style.display = "block";
    block2.style.display = "none";
    return;
  }
  if (currentIndex >= questions.length) {
    finishGame();
    return;
  }

  const q = questions[currentIndex];
  questEl.innerText = q.question || "";

  const progressPercent = (currentIndex / questions.length) * 100;
  if (progressBar) progressBar.style.width = `${progressPercent}%`;
  if (progressText) progressText.innerText = `Вопрос ${currentIndex + 1} из ${questions.length}`;

  answerBtns.forEach((btn, index) => {
    btn.innerText = q.answers[index] || "";
    btn.onclick = () => checkAnswer(index);
    btn.disabled = false;
    btn.style.background = "";
    btn.style.borderColor = "";
  });
}

// Проверка ответа
function checkAnswer(selectedIndex) {
  const q = questions[currentIndex];
  if (!q) return;

  if (selectedIndex === q.correct) {
    score++;
    answerBtns[selectedIndex].style.background = "#d4edda";
    answerBtns[selectedIndex].style.borderColor = "#28a745";
  } else {
    answerBtns[selectedIndex].style.background = "#f8d7da";
    answerBtns[selectedIndex].style.borderColor = "#dc3545";
  }

  answerBtns.forEach(btn => btn.disabled = true);

  setTimeout(() => {
    currentIndex++;
    if (currentIndex < questions.length) showQuestion();
    else finishGame();
  }, 900);
}

// Завершение теста
function finishGame() {
  block2.style.display = "none";
  block3.style.display = "block";
  scoreEl.innerText = `Ваш результат: ${score} из ${questions.length}`;
  sendResult(score, questions.length);
}

// Назад в меню
if (backBtn) backBtn.onclick = () => {
  block3.style.display = "none";
  block1.style.display = "block";
};

// Админ: открыть форму добавления
if (addBtn) addBtn.onclick = () => {
  block1.style.display = "none";
  addForm.style.display = "block";
};

// Отмена добавления
if (cancelBtn) cancelBtn.onclick = () => {
  addForm.style.display = "none";
  block1.style.display = "block";
};

// Сохранение вопроса (админ)
if (saveBtn) saveBtn.onclick = async () => {
  const qText = (document.getElementById("newQuestion") || {}).value || "";
  const answers = Array.from(document.querySelectorAll(".newAnswer")).map(i => (i.value || "").trim());
  const correctVal = (document.getElementById("newCorrect") || {}).value || "";
  const correct = parseInt(correctVal, 10);

  if (!qText.trim() || answers.some(a => !a) || Number.isNaN(correct)) {
    alert("Заполните все поля!");
    return;
  }
  if (correct < 0 || correct > 3) {
    alert("Правильный ответ должен быть от 0 до 3");
    return;
  }

  const newQ = { question: qText.trim(), answers, correct };
  const ok = await saveQuestionApi(newQ);
  if (!ok) return;

  // очистка формы
  document.getElementById("newQuestion").value = "";
  document.querySelectorAll(".newAnswer").forEach(i => i.value = "");
  document.getElementById("newCorrect").value = "";
  alert("Вопрос сохранен!");
  addForm.style.display = "none";
  block1.style.display = "block";
};

// Админ: показать результаты
if (resultsBtn) {
  resultsBtn.onclick = async () => {
    const data = await loadResults();
    resultsTableBody.innerHTML = "";
    data.forEach(r => {
      const row = document.createElement("tr");
      row.innerHTML = `<td>${r.username}</td><td>${r.score}</td><td>${r.total}</td>`;
      resultsTableBody.appendChild(row);
    });
    block1.style.display = "none";
    resultsBlock.style.display = "block";
  };
}

// Закрыть результаты
if (closeResultsBtn) closeResultsBtn.onclick = () => {
  resultsBlock.style.display = "none";
  block1.style.display = "block";
};
