const toolbarOptions = [
  ['bold', 'italic', 'underline', 'strike'],
  [{ header: [1, 2, 3, false] }],
  [{ list: 'ordered' }, { list: 'bullet' }],
  ['blockquote', 'code-block', 'link'],
  ['clean'],
];

const setMode = (container, quill, textarea, codeMirror, mode) => {
  if (mode === 'raw') {
    const html = quill.root.innerHTML;
    if (codeMirror) {
      codeMirror.setValue(html);
      codeMirror.refresh();
    } else {
      textarea.value = html;
    }
    container.classList.add('is-raw');
  } else {
    const html = codeMirror ? codeMirror.getValue() : textarea.value;
    quill.root.innerHTML = html || '';
    textarea.value = html || '';
    container.classList.remove('is-raw');
  }
};

const appendHtmlToEditor = (container, html) => {
  const editor = container?.richEditor;
  if (!editor) {
    return;
  }
  const { quill, textarea, codeMirror } = editor;
  const toggle = container.querySelector('.rich-editor__toggle-input');
  const isRaw = toggle?.checked;

  if (isRaw) {
    if (codeMirror) {
      const current = codeMirror.getValue();
      const nextValue = `${current}${current ? '\n' : ''}${html}`;
      codeMirror.setValue(nextValue);
      codeMirror.focus();
      codeMirror.setCursor(codeMirror.lineCount(), 0);
      textarea.value = nextValue;
    } else if (textarea) {
      textarea.value = `${textarea.value}${textarea.value ? '\n' : ''}${html}`;
      textarea.focus();
      textarea.selectionStart = textarea.selectionEnd = textarea.value.length;
    }
    return;
  }

  if (quill) {
    const current = quill.root.innerHTML;
    const nextValue = `${current}${current ? '\n' : ''}${html}`;
    quill.root.innerHTML = nextValue;
    quill.setSelection(quill.getLength(), 0);
    if (textarea) {
      textarea.value = nextValue;
    }
  }
};

const buildImageMarkup = (url) => `
  <a href="${url}" target="_blank" rel="noopener noreferrer">
    <img class="blog-image" src="${url}" alt="Imagen adjunta">
  </a>
`;

const ensureLightbox = () => {
  if (document.querySelector('[data-lightbox-overlay]')) {
    return;
  }
  const overlay = document.createElement('div');
  overlay.className = 'lightbox-overlay';
  overlay.dataset.lightboxOverlay = 'true';
  overlay.innerHTML = `
    <div class="lightbox-content">
      <button class="lightbox-close" type="button" aria-label="Cerrar">✕</button>
      <img src="" alt="Imagen ampliada" />
    </div>
  `;
  document.body.appendChild(overlay);
};

const openLightbox = (url) => {
  ensureLightbox();
  const overlay = document.querySelector('[data-lightbox-overlay]');
  if (!overlay) {
    return;
  }
  const img = overlay.querySelector('img');
  if (img) {
    img.src = url;
  }
  overlay.classList.add('is-active');
};

const closeLightbox = () => {
  const overlay = document.querySelector('[data-lightbox-overlay]');
  if (!overlay) {
    return;
  }
  overlay.classList.remove('is-active');
};

document.addEventListener('click', (event) => {
  const link = event.target.closest('[data-lightbox-link]');
  if (link) {
    event.preventDefault();
    openLightbox(link.getAttribute('href'));
    return;
  }
  if (event.target.closest('.lightbox-close')) {
    closeLightbox();
    return;
  }
  if (event.target.matches('.lightbox-overlay.is-active')) {
    closeLightbox();
  }
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    closeLightbox();
  }
});

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
    const codeMirror =
      window.CodeMirror &&
      window.CodeMirror.fromTextArea(textarea, {
        mode: 'htmlmixed',
        lineNumbers: true,
        lineWrapping: true,
        theme: 'material-darker',
      });

    container.richEditor = {
      quill,
      textarea,
      codeMirror,
    };

    setMode(container, quill, textarea, codeMirror, 'rich');

    if (toggle) {
      toggle.addEventListener('change', () => {
        setMode(container, quill, textarea, codeMirror, toggle.checked ? 'raw' : 'rich');
      });
    }

    const form = container.closest('form');
    if (form) {
      form.addEventListener('submit', () => {
        if (!toggle || !toggle.checked) {
          textarea.value = quill.root.innerHTML;
        } else if (codeMirror) {
          textarea.value = codeMirror.getValue();
        }
      });
    }
  });

  document.querySelectorAll('[data-image-gallery]').forEach((gallery) => {
    const scope = gallery.dataset.imageScope;
    const toggleButton = gallery.querySelector('[data-gallery-toggle]');
    const panel = gallery.querySelector('.image-gallery__panel');
    const grid = gallery.querySelector('[data-gallery-grid]');
    const pagination = gallery.querySelector('[data-gallery-pagination]');
    const uploadInput = gallery.querySelector('[data-gallery-upload]');
    const dropzone = gallery.querySelector('[data-gallery-dropzone]');
    const insertButton = gallery.querySelector('[data-gallery-insert]');
    const selected = new Set();
    let loaded = false;
    let images = [];
    let currentPage = 1;
    const pageSize = 20;

    const updateInsertState = () => {
      if (insertButton) {
        insertButton.disabled = selected.size === 0;
      }
    };

    const renderPagination = (totalPages) => {
      if (!pagination) {
        return;
      }
      pagination.innerHTML = '';

      const createButton = (label, page, disabled) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'button ghost small';
        button.textContent = label;
        button.disabled = disabled;
        if (!disabled) {
          button.addEventListener('click', () => {
            currentPage = page;
            renderPage();
          });
        }
        return button;
      };

      pagination.appendChild(createButton('Anterior', currentPage - 1, currentPage === 1));
      const pageText = document.createElement('span');
      pageText.className = 'image-gallery__page';
      pageText.textContent = `Página ${currentPage} de ${totalPages}`;
      pagination.appendChild(pageText);
      pagination.appendChild(createButton('Siguiente', currentPage + 1, currentPage === totalPages));
    };

    const renderPage = () => {
      if (!grid) {
        return;
      }
      grid.innerHTML = '';
      const totalPages = Math.max(1, Math.ceil(images.length / pageSize));
      if (currentPage > totalPages) {
        currentPage = totalPages;
      }
      const start = (currentPage - 1) * pageSize;
      const pageImages = images.slice(start, start + pageSize);

      pageImages.forEach((url) => {
        const item = document.createElement('div');
        item.className = 'image-gallery__item';
        item.dataset.url = url;
        const img = document.createElement('img');
        img.src = url;
        img.alt = 'Imagen disponible';
        item.appendChild(img);
        if (selected.has(url)) {
          item.classList.add('is-selected');
        }
        item.addEventListener('click', () => {
          if (selected.has(url)) {
            selected.delete(url);
            item.classList.remove('is-selected');
          } else {
            selected.add(url);
            item.classList.add('is-selected');
          }
          updateInsertState();
        });
        grid.appendChild(item);
      });
      renderPagination(totalPages);
    };

    const setImages = (nextImages) => {
      images = nextImages;
      currentPage = 1;
      renderPage();
    };

    const loadImages = async () => {
      if (!scope) {
        return;
      }
      const response = await fetch(`/media/${scope}/list`);
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      setImages(payload.images || []);
      loaded = true;
    };

    if (toggleButton && panel) {
      toggleButton.addEventListener('click', async () => {
        panel.hidden = !panel.hidden;
        if (!panel.hidden && !loaded) {
          await loadImages();
        }
      });
    }

    if (uploadInput) {
      uploadInput.addEventListener('change', async () => {
        if (!uploadInput.files?.length || !scope) {
          return;
        }
        const formData = new FormData();
        Array.from(uploadInput.files).forEach((file) => {
          formData.append('files', file);
        });
        const response = await fetch(`/media/${scope}/upload`, {
          method: 'POST',
          body: formData,
        });
        if (!response.ok) {
          return;
        }
        const payload = await response.json();
        selected.clear();
        updateInsertState();
        setImages(payload.images || []);
        uploadInput.value = '';
      });
    }

    if (dropzone && uploadInput) {
      const triggerUpload = (files) => {
        if (!files.length) {
          return;
        }
        const dataTransfer = new DataTransfer();
        Array.from(files).forEach((file) => dataTransfer.items.add(file));
        uploadInput.files = dataTransfer.files;
        uploadInput.dispatchEvent(new Event('change'));
      };

      dropzone.addEventListener('click', () => {
        uploadInput.click();
      });

      dropzone.addEventListener('dragover', (event) => {
        event.preventDefault();
        dropzone.classList.add('is-dragging');
      });

      dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('is-dragging');
      });

      dropzone.addEventListener('drop', (event) => {
        event.preventDefault();
        dropzone.classList.remove('is-dragging');
        if (event.dataTransfer?.files) {
          triggerUpload(event.dataTransfer.files);
        }
      });
    }

    if (insertButton) {
      insertButton.addEventListener('click', () => {
        const urls = Array.from(selected);
        if (urls.length === 0) {
          return;
        }
        const html = urls.map((url) => `<p>${buildImageMarkup(url)}</p>`).join('\n');
        const editor = gallery.closest('form')?.querySelector('[data-rich-editor]');
        appendHtmlToEditor(editor, html);
        selected.clear();
        grid?.querySelectorAll('.image-gallery__item').forEach((item) => {
          item.classList.remove('is-selected');
        });
        updateInsertState();
      });
    }
  });
});
