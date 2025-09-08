// Admin Dashboard JS
(function () {
  const messageContainer = document.getElementById('messageContainer');
  function showMessage(message, type = 'success') {
    if (!messageContainer) return;
    messageContainer.innerHTML = `
      <div class="p-4 rounded-lg ${type === 'success' ? 'bg-green-100 text-green-700 border border-green-200' : 'bg-red-100 text-red-700 border border-red-200'}">
        <div class="flex items-center">
          <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-2"></i>
          ${message}
        </div>
      </div>`;
    setTimeout(() => { if (messageContainer) messageContainer.innerHTML = ''; }, 5000);
  }

  // Delete modal handlers
  const deleteModal = document.getElementById('deleteModal');
  const modalTitle = document.getElementById('modalTitle');
  const modalMessage = document.getElementById('modalMessage');
  const cancelDeleteBtn = document.getElementById('cancelDelete');
  const confirmDeleteBtn = document.getElementById('confirmDelete');
  let itemToDelete = null;
  let deleteType = null;

  window.confirmDeleteQuiz = (quizId, quizTitle) => {
    itemToDelete = quizId;
    deleteType = 'quiz';
    if (modalTitle) modalTitle.textContent = 'Delete Quiz';
    if (modalMessage) modalMessage.textContent = `Are you sure you want to delete the quiz "${quizTitle}"? This will remove all related questions and attempts.`;
    if (deleteModal) deleteModal.classList.remove('hidden');
  };

  window.confirmDeleteUser = (userId, username) => {
    itemToDelete = userId;
    deleteType = 'user';
    if (modalTitle) modalTitle.textContent = 'Delete User';
    if (modalMessage) modalMessage.textContent = `Are you sure you want to delete the user "${username}"?`;
    if (deleteModal) deleteModal.classList.remove('hidden');
  };

  cancelDeleteBtn?.addEventListener('click', () => {
    deleteModal?.classList.add('hidden');
    itemToDelete = null;
    deleteType = null;
  });

  confirmDeleteBtn?.addEventListener('click', async () => {
    try {
      let response;
      if (deleteType === 'quiz') {
        response = await fetch(`/admin/quiz/delete/${itemToDelete}`, { method: 'POST' });
      } else if (deleteType === 'user') {
        response = await fetch(`/admin/user/delete/${itemToDelete}`, { method: 'POST' });
      }
      if (response?.ok) {
        const result = await response.json();
        showMessage(result.message || 'Deleted', 'success');
        setTimeout(() => location.reload(), 800);
      } else {
        const err = await response.json();
        showMessage(err.error || 'Failed to delete', 'error');
      }
    } catch (e) {
      showMessage('Error deleting item', 'error');
    }
    deleteModal?.classList.add('hidden');
    itemToDelete = null;
    deleteType = null;
  });

  // Quiz edit
  const quizEditModal = document.getElementById('quizEditModal');
  const quizEditForm = document.getElementById('quizEditForm');
  const cancelQuizEditBtn = document.getElementById('cancelQuizEdit');

  window.editQuiz = async (quizId) => {
    try {
      const res = await fetch(`/admin/quiz/get/${quizId}`);
      if (!res.ok) throw await res.json();
      const quiz = await res.json();
      document.getElementById('editQuizId').value = quiz.id;
      document.getElementById('editQuizTitle').value = quiz.title || '';
      document.getElementById('editQuizDescription').value = quiz.description || '';
      document.getElementById('editQuizPassingScore').value = quiz.passing_score || 60;
      quizEditModal?.classList.remove('hidden');
    } catch (err) {
      showMessage(err.error || 'Error fetching quiz', 'error');
    }
  };

  cancelQuizEditBtn?.addEventListener('click', () => quizEditModal?.classList.add('hidden'));

  quizEditForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const quizId = document.getElementById('editQuizId').value;
    const payload = {
      title: document.getElementById('editQuizTitle').value,
      description: document.getElementById('editQuizDescription').value,
      passing_score: parseInt(document.getElementById('editQuizPassingScore').value, 10) || 60
    };
    try {
      const res = await fetch(`/admin/quiz/edit/${quizId}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      if (!res.ok) throw await res.json();
      const result = await res.json();
      showMessage(result.message || 'Updated', 'success');
      quizEditModal?.classList.add('hidden');
      setTimeout(() => location.reload(), 800);
    } catch (err) {
      showMessage(err.error || 'Error updating quiz', 'error');
    }
  });

  // Questions list / edit
  const questionsModal = document.getElementById('questionsModal');
  const closeQuestionsModalBtn = document.getElementById('closeQuestionsModal');
  const questionsQuizTitle = document.getElementById('questionsQuizTitle');
  const questionsListContainer = document.getElementById('questionsListContainer');

  window.manageQuestions = async (quizId, quizTitle) => {
    try {
      const res = await fetch(`/admin/quiz/${quizId}/questions`);
      if (!res.ok) throw await res.json();
      const questions = await res.json();
      if (questionsQuizTitle) questionsQuizTitle.textContent = quizTitle;
      if (!questions || !questions.length) {
        if (questionsListContainer) questionsListContainer.innerHTML = '<div class="text-center py-8 text-gray-500">No questions.</div>';
      } else {
        if (questionsListContainer) questionsListContainer.innerHTML = questions.map((q, idx) => `
          <div class=\"border border-gray-200 p-4 rounded-lg bg-gray-50\">
            <div class=\"flex justify-between items-start\">
              <div class=\"flex-1\">
                <div class=\"flex items-center justify-between mb-1\">
                  <h4 class=\"font-semibold text-gray-800\">Question ${idx + 1}</h4>
                  <span class=\"text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded\">${q.points} point${q.points > 1 ? 's' : ''}</span>
                </div>
                <p class=\"text-gray-700 mb-2\">${q.question_text || ''}</p>
                <div class=\"text-sm text-gray-600 mb-2\"><span class=\"font-medium\">Type:</span> ${q.question_type === 'true_false' ? 'True/False' : 'Multiple Choice'}</div>
                ${(q.options && q.options.length) ? `<div class=\"text-sm text-gray-600\"><span class=\"font-medium\">Options:</span> ${q.options.map(o => `<span class=\\"ml-2\\">${o}</span>`).join(' | ')}</div>` : ''}
                <div class=\"text-sm text-gray-700 mt-1\"><span class=\"font-medium\">Correct:</span> ${q.correct_answer || ''}</div>
              </div>
              <div class=\"ml-3\">
                <button onclick=\"editQuestion('${q.id}')\" class=\"text-yellow-600 hover:text-yellow-800 p-2 rounded hover:bg-yellow-50\"><i class=\"fas fa-edit\"></i></button>
              </div>
            </div>
          </div>`).join('');
      }
      questionsModal?.classList.remove('hidden');
    } catch (err) {
      showMessage(err.error || 'Error loading questions', 'error');
    }
  };

  closeQuestionsModalBtn?.addEventListener('click', () => questionsModal?.classList.add('hidden'));

  const questionEditModal = document.getElementById('questionEditModal');
  const questionEditForm = document.getElementById('questionEditForm');
  const cancelQuestionEditBtn = document.getElementById('cancelQuestionEdit');

  window.editQuestion = async (questionId) => {
    try {
      const res = await fetch(`/admin/question/get/${questionId}`);
      if (!res.ok) throw await res.json();
      const q = await res.json();
      document.getElementById('editQuestionId').value = q.id;
      document.getElementById('editQuestionText').value = q.question_text || '';
      document.getElementById('editQuestionType').value = q.question_type || 'multiple_choice';
      document.getElementById('editQuestionOptions').value = (q.options && q.options.length) ? q.options.join('|') : '';
      document.getElementById('editCorrectAnswer').value = q.correct_answer || '';
      document.getElementById('editQuestionPoints').value = q.points || 1;
      questionEditModal?.classList.remove('hidden');
    } catch (err) {
      showMessage(err.error || 'Error fetching question', 'error');
    }
  };

  cancelQuestionEditBtn?.addEventListener('click', () => questionEditModal?.classList.add('hidden'));

  questionEditForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const questionId = document.getElementById('editQuestionId').value;
    const payload = {
      question_text: document.getElementById('editQuestionText').value,
      question_type: document.getElementById('editQuestionType').value,
      options: (document.getElementById('editQuestionOptions').value || '').split('|').map(s => s.trim()).filter(Boolean),
      correct_answer: document.getElementById('editCorrectAnswer').value,
      points: parseInt(document.getElementById('editQuestionPoints').value, 10) || 1
    };
    try {
      const res = await fetch(`/admin/question/edit/${questionId}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      if (!res.ok) throw await res.json();
      const result = await res.json();
      showMessage(result.message || 'Question updated', 'success');
      questionEditModal?.classList.add('hidden');
      setTimeout(() => location.reload(), 800);
    } catch (err) {
      showMessage(err.error || 'Error updating question', 'error');
    }
  });

  // User edit
  const userEditModal = document.getElementById('userEditModal');
  const userEditForm = document.getElementById('userEditForm');
  const cancelUserEditBtn = document.getElementById('cancelUserEdit');

  window.editUser = async (userId) => {
    try {
      const res = await fetch(`/admin/user/get/${userId}`);
      if (!res.ok) throw await res.json();
      const user = await res.json();
      document.getElementById('editUserId').value = user.id;
      document.getElementById('editUsername').value = user.username || '';
      document.getElementById('editEmail').value = user.email || '';
      document.getElementById('editRole').value = user.role || 'student';
      userEditModal?.classList.remove('hidden');
    } catch (err) {
      showMessage(err.error || 'Error fetching user', 'error');
    }
  };

  cancelUserEditBtn?.addEventListener('click', () => userEditModal?.classList.add('hidden'));

  userEditForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const userId = document.getElementById('editUserId').value;
    const payload = {
      username: document.getElementById('editUsername').value,
      email: document.getElementById('editEmail').value,
      role: document.getElementById('editRole').value
    };
    try {
      const res = await fetch(`/admin/user/edit/${userId}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      if (!res.ok) throw await res.json();
      const result = await res.json();
      showMessage(result.message || 'User updated', 'success');
      userEditModal?.classList.add('hidden');
      setTimeout(() => location.reload(), 800);
    } catch (err) {
      showMessage(err.error || 'Error updating user', 'error');
    }
  });
})();
