const toolbarOptions = [
  ['bold', 'italic', 'underline', 'strike'],
  [{ header: [1, 2, 3, false] }],
  [{ list: 'ordered' }, { list: 'bullet' }],
  ['blockquote', 'code-block', 'link'],
  ['clean'],
];

const setMode = (container, quill, textarea, mode) => {
  if (mode === 'raw') {
    textarea.value = quill.root.innerHTML;
    container.classList.add('is-raw');
  } else {
    quill.root.innerHTML = textarea.value || '';
    container.classList.remove('is-raw');
  }
};

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-rich-editor]').forEach((container) => {
    const textarea = container.querySelector('textarea');
    const quillTarget = container.querySelector('[data-rich-editor-quill]');
    const toggle = container.querySelector('.rich-editor__toggle-input');

    if (!textarea || !quillTarget) {
      return;
    }

    const quill = new Quill(quillTarget, {
      modules: {
        toolbar: toolbarOptions,
      },
      theme: 'snow',
    });

    quill.root.innerHTML = textarea.value || '';
    setMode(container, quill, textarea, 'rich');

    if (toggle) {
      toggle.addEventListener('change', () => {
        setMode(container, quill, textarea, toggle.checked ? 'raw' : 'rich');
      });
    }

    const form = container.closest('form');
    if (form) {
      form.addEventListener('submit', () => {
        if (!toggle || !toggle.checked) {
          textarea.value = quill.root.innerHTML;
        }
      });
    }
  });
});
