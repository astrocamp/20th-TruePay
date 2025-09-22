const COPY_CONFIG = {
  FEEDBACK_DURATION: 2000,
  SUCCESS_CLASSES: ['bg-green-500', 'hover:bg-green-600'],
  DEFAULT_CLASSES: ['bg-[#0056B3]', 'hover:bg-[#00408A]'],
  SUCCESS_ICON: '<svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>',
  SUCCESS_TEXT: '已複製！'
};

async function copyToClipboard(elementId, options = {}) {
  try {
    const element = document.getElementById(elementId);
    if (!element) {
      throw new Error(`找不到元素: ${elementId}`);
    }

    const textToCopy = element.value || element.textContent || element.innerText;
    if (!textToCopy) {
      throw new Error('沒有內容可複製');
    }

    const button = findCopyButton(elementId);
    if (!button) {
      throw new Error('找不到複製按鈕');
    }

    await performCopy(textToCopy);
    showFeedback(button, 'success', options);

  } catch (error) {
    console.error('複製失敗:', error);
    showFeedback(null, 'error', options, error.message);
  }
}

function findCopyButton(elementId) {
  return document.querySelector(`button[onclick*="copyToClipboard('${elementId}')"]`);
}

async function performCopy(text) {
  await navigator.clipboard.writeText(text);
}

function showFeedback(button, type, options = {}, errorMessage = '') {
  if (type === 'error') {
    const message = errorMessage || '複製失敗，請手動選取代碼';
    if (options.showAlert !== false) {
      alert(message);
    }
    return;
  }

  if (!button) return;

  const originalContent = button.innerHTML;
  button.innerHTML = COPY_CONFIG.SUCCESS_ICON + COPY_CONFIG.SUCCESS_TEXT;
  button.classList.remove(...COPY_CONFIG.DEFAULT_CLASSES);
  button.classList.add(...COPY_CONFIG.SUCCESS_CLASSES);

  const duration = options.feedbackDuration || COPY_CONFIG.FEEDBACK_DURATION;
  setTimeout(() => {
    button.innerHTML = originalContent;
    button.classList.remove(...COPY_CONFIG.SUCCESS_CLASSES);
    button.classList.add(...COPY_CONFIG.DEFAULT_CLASSES);
  }, duration);
}

window.copyToClipboard = copyToClipboard;