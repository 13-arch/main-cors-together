// main.js — таймер AFK
const INACTIVITY_TIME = 5 * 60 * 1000;
let inactivityTimer;
function resetTimer() {
  clearTimeout(inactivityTimer);
  inactivityTimer = setTimeout(() => { window.location.href = '/logout_afk'; }, INACTIVITY_TIME);
}
['mousemove','keydown','scroll','click','touchstart'].forEach(e => document.addEventListener(e, resetTimer, false));
resetTimer();
