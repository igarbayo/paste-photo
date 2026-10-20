// SPDX-FileCopyrightText: 2026 igarbayo
// SPDX-License-Identifier: MIT
//
// paste-photo: recuerda dónde estaba el cursor en el prompt de claude.ai.
//
// Corre en el mundo aislado de la extensión, el mismo en el que `background.js` ejecuta
// `pasteImage`: así la captura se pega donde el usuario dejó el cursor la última vez,
// aunque luego hiciera clic fuera del prompt o cambiase de pestaña o de aplicación.

const EDITOR_SELECTOR = '.ProseMirror[contenteditable="true"]';

globalThis.pastePhotoLastRange = null;

document.addEventListener("selectionchange", () => {
  const selection = document.getSelection();
  if (!selection || selection.rangeCount === 0) return;
  const range = selection.getRangeAt(0);
  const node = range.startContainer;
  const element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
  if (element && element.closest(EDITOR_SELECTOR)) {
    globalThis.pastePhotoLastRange = range.cloneRange();
  }
});
