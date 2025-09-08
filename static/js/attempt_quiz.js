let currentQuestion = 1;
let rootEl = null;
let totalQuestions = 0;
let durationMinutes = 0;
let remainingSeconds = 0;
let countdownTimer = null;

function showQuestion(questionNum) {
  // Hide all questions
  document.querySelectorAll('.question-container').forEach(q => q.classList.add('hidden'));
  // Show current
  const el = document.getElementById(`question-${questionNum}`);
  if (el) el.classList.remove('hidden');

  // Update progress
  const progress = totalQuestions > 0 ? (questionNum / totalQuestions) * 100 : 0;
  const progressBar = document.getElementById('progress-bar');
  const progressText = document.getElementById('progress-text');
  if (progressBar) progressBar.style.width = `${progress}%`;
  if (progressText) progressText.textContent = `${questionNum} of ${totalQuestions}`;

  // Update nav buttons
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  if (prevBtn) prevBtn.disabled = questionNum === 1;
  if (nextBtn) {
    nextBtn.textContent = questionNum === totalQuestions ? 'Submit Quiz' : 'Next Question';
    nextBtn.className = questionNum === totalQuestions
      ? 'bg-green-500 hover:bg-green-600 text-white px-6 py-2 rounded-lg font-medium transition-colors duration-200'
      : 'bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium transition-colors duration-200';
  }
}

function nextQuestion() {
  if (currentQuestion < totalQuestions) {
    currentQuestion++;
    showQuestion(currentQuestion);
  }
}

function prevQuestion() {
  if (currentQuestion > 1) {
    currentQuestion--;
    showQuestion(currentQuestion);
  }
}

function validateForm() {
  const questions = document.querySelectorAll('.question-container');
  let isValid = true;
  let firstUnanswered = null;

  questions.forEach((question, index) => {
    const radios = question.querySelectorAll('input[type="radio"]');
    const answered = Array.from(radios).some(r => r.checked);
    if (!answered) {
      isValid = false;
      if (firstUnanswered === null) firstUnanswered = index + 1;
      question.classList.add('border-red-300', 'bg-red-50');
    } else {
      question.classList.remove('border-red-300', 'bg-red-50');
    }
  });

  if (!isValid) {
    alert('Please answer all questions before submitting. You can navigate to unanswered questions using the navigation buttons.');
    if (firstUnanswered) {
      currentQuestion = firstUnanswered;
      showQuestion(currentQuestion);
    }
    return false;
  }
  return true;
}

function startCountdown() {
  if (durationMinutes <= 0) return;
  const timerEl = document.getElementById('countdown-timer');
  const formEl = document.getElementById('quiz-form');
  function render() {
    const m = Math.floor(remainingSeconds / 60);
    const s = remainingSeconds % 60;
    if (timerEl) timerEl.textContent = `${m}:${s.toString().padStart(2, '0')}`;
  }
  render();
  countdownTimer = setInterval(() => {
    remainingSeconds -= 1;
    if (remainingSeconds <= 0) {
      clearInterval(countdownTimer);
      render();
      if (formEl) formEl.submit();
    } else {
      render();
    }
  }, 1000);
}

// Expose for inline handlers still present
window.showQuestion = showQuestion;
window.nextQuestion = nextQuestion;
window.prevQuestion = prevQuestion;
window.validateForm = validateForm;

// Init
document.addEventListener('DOMContentLoaded', function () {
  rootEl = document.getElementById('quiz-root');
  if (rootEl) {
    totalQuestions = parseInt(rootEl.dataset.totalQuestions, 10) || 0;
    durationMinutes = parseInt(rootEl.dataset.durationMinutes, 10) || 0;
    remainingSeconds = durationMinutes > 0 ? durationMinutes * 60 : 0;
  }

  // Bind nav page buttons if present
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.questionIndex, 10) || 1;
      currentQuestion = Math.min(Math.max(idx, 1), totalQuestions);
      showQuestion(currentQuestion);
    });
  });

  showQuestion(1);
  startCountdown();
});
