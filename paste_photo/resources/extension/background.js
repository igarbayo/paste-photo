// SPDX-FileCopyrightText: 2026 igarbayo
// SPDX-License-Identifier: MIT
//
// paste-photo: puente entre la app de escritorio y las pestañas de claude.ai.
//
// La app habla con esta extensión por "native messaging" (paste-photo-native-host).
// Mensajes que recibe (todos con `id`, la respuesta lleva el mismo `id`):
//   {cmd: "list"}                           -> {ok, tabs: [{tabId, windowId, url, title, active, lastUsed}]}
//   {cmd: "paste", tabId, png, name, activate} -> {ok} | {ok: false, error}
// No necesita foco ni simular teclas: inyecta un evento `paste` con la imagen en el editor
// (funciona igual en X11, Wayland, Windows y en pestañas en segundo plano).

const HOST = "io.github.igarbayo.paste_photo";
const CLAUDE_URLS = ["https://claude.ai/*"]; // las pruebas generan una copia con otra URL

let port = null;
let retryDelay = 2000;
const lastUsed = new Map(); // tabId -> ms epoch en que dejó de ser la pestaña en uso

function connect() {
  if (port) return;
  try {
    port = chrome.runtime.connectNative(HOST);
  } catch (e) {
    scheduleRetry();
    return;
  }
  port.onMessage.addListener(onMessage);
  port.onDisconnect.addListener(() => {
    // Sin la app instalada/abierta el host no existe: reintentar con espera creciente.
    void chrome.runtime.lastError;
    port = null;
    scheduleRetry();
  });
  port.postMessage({ event: "hello", version: chrome.runtime.getManifest().version });
  retryDelay = 2000;
}

function scheduleRetry() {
  setTimeout(connect, retryDelay);
  retryDelay = Math.min(retryDelay * 2, 60000);
}

// El host trocea los mensajes de más de 1 MB (límite del navegador): se recomponen aquí.
const chunks = new Map(); // chunkId -> [partes]

async function onMessage(msg) {
  if (msg && msg.chunk !== undefined) {
    const parts = chunks.get(msg.chunk) || new Array(msg.total);
    parts[msg.seq] = msg.data;
    chunks.set(msg.chunk, parts);
    if (parts.filter((p) => p !== undefined).length === msg.total) {
      chunks.delete(msg.chunk);
      return onMessage(JSON.parse(parts.join("")));
    }
    return;
  }
  if (!msg || msg.id === undefined) return;
  let reply;
  try {
    if (msg.cmd === "list") reply = { ok: true, tabs: await listTabs() };
    else if (msg.cmd === "paste") reply = await paste(msg);
    else if (msg.cmd === "ping") reply = { ok: true };
    else reply = { ok: false, error: `orden desconocida: ${msg.cmd}` };
  } catch (e) {
    reply = { ok: false, error: String(e && e.message ? e.message : e) };
  }
  if (port) port.postMessage({ id: msg.id, ...reply });
}

async function listTabs() {
  const tabs = await chrome.tabs.query({ url: CLAUDE_URLS });
  const focused = await chrome.windows.getLastFocused().catch(() => null);
  const now = Date.now();
  return tabs.map((t) => ({
    tabId: t.id,
    windowId: t.windowId,
    url: t.url,
    title: t.title,
    active: t.active,
    // En uso ahora mismo = pestaña activa de la ventana con el foco.
    lastUsed:
      t.active && focused && focused.focused && focused.id === t.windowId
        ? now
        : lastUsed.get(t.id) || t.lastAccessed || 0,
  }));
}

async function paste(msg) {
  if (msg.activate) {
    const tab = await chrome.tabs.update(msg.tabId, { active: true });
    await chrome.windows.update(tab.windowId, { focused: true });
  }
  // Dos pasos: el cursor se coloca en el mundo aislado de la extensión (ahí guarda cursor.js
  // la última posición) y el `paste` se lanza en el de la página: en Firefox, un evento
  // creado desde el mundo aislado llega a la página sin los archivos.
  const target = { tabId: msg.tabId };
  const [placed] = await chrome.scripting.executeScript({ target, func: placeCaret });
  const ready = placed && placed.result ? placed.result : { ok: false, error: "sin resultado" };
  if (!ready.ok) return ready;
  const [result] = await chrome.scripting.executeScript({
    target,
    world: "MAIN",
    func: dispatchPaste,
    args: [msg.png, msg.name || "screenshot.png"],
  });
  return result && result.result ? result.result : { ok: false, error: "sin resultado" };
}

// Se ejecuta DENTRO de la página de claude.ai, en el mundo aislado (no puede usar nada de
// este archivo).
async function placeCaret() {
  const findEditor = () => document.querySelector('.ProseMirror[contenteditable="true"]');
  let editor = findEditor();
  for (let i = 0; !editor && i < 30; i++) {
    await new Promise((r) => setTimeout(r, 100)); // la página puede estar cargando
    editor = findEditor();
  }
  if (!editor) return { ok: false, error: "no-editor" };
  // Posición del cursor: la actual si está en el prompt; si no, la última que tuvo en él
  // (la guarda cursor.js); si nunca la tuvo, al final. `focus()` lo pondría al principio.
  const inEditor = (range) =>
    range && editor.contains(range.startContainer) && editor.contains(range.endContainer);
  const selection = document.getSelection();
  const current = selection && selection.rangeCount ? selection.getRangeAt(0) : null;
  let range = inEditor(current) ? current.cloneRange() : globalThis.pastePhotoLastRange;
  if (!inEditor(range)) {
    range = document.createRange();
    range.selectNodeContents(editor);
    range.collapse(false);
  }
  editor.focus({ preventScroll: true });
  selection.removeAllRanges();
  selection.addRange(range);
  // ProseMirror lee la selección del DOM en `selectionchange` (asíncrono): se le da tiempo
  // para que el `paste` vaya a ese punto y no a la selección que tenía guardada.
  await new Promise((r) => setTimeout(r, 50));
  return { ok: true };
}

// Se ejecuta DENTRO de la página de claude.ai, en su propio mundo (`world: "MAIN"`).
function dispatchPaste(base64, name) {
  const editor = document.querySelector('.ProseMirror[contenteditable="true"]');
  if (!editor) return { ok: false, error: "no-editor" };
  const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
  const data = new DataTransfer();
  data.items.add(new File([bytes], name, { type: "image/png" }));
  const init = { clipboardData: data, bubbles: true, cancelable: true };
  let event = new ClipboardEvent("paste", init);
  if (!event.clipboardData || event.clipboardData.files.length === 0) {
    // Firefox crea su propio `clipboardData` (vacío): se sustituye por el nuestro.
    event = new Event("paste", init);
    Object.defineProperty(event, "clipboardData", { value: data });
  }
  const handled = !editor.dispatchEvent(event);
  return handled ? { ok: true } : { ok: false, error: "paste-ignored" };
}

// Seguimiento de uso: el instante en que cada pestaña DEJÓ de estar en uso (cambio de
// pestaña o la ventana pierde el foco, también hacia otra aplicación). La pestaña en uso
// ahora mismo se calcula al vuelo en listTabs().
const activeByWindow = new Map(); // windowId -> tabId activa
let focusedWindow = chrome.windows.WINDOW_ID_NONE;

chrome.tabs.onActivated.addListener(({ tabId, windowId }) => {
  const previous = activeByWindow.get(windowId);
  if (previous !== undefined && previous !== tabId && windowId === focusedWindow) {
    lastUsed.set(previous, Date.now());
  }
  activeByWindow.set(windowId, tabId);
});
chrome.windows.onFocusChanged.addListener((windowId) => {
  const previous = activeByWindow.get(focusedWindow);
  if (previous !== undefined && windowId !== focusedWindow) lastUsed.set(previous, Date.now());
  focusedWindow = windowId;
});
chrome.tabs.onRemoved.addListener((tabId) => lastUsed.delete(tabId));
chrome.tabs.query({ active: true }).then((tabs) => {
  for (const t of tabs) activeByWindow.set(t.windowId, t.id);
});
chrome.windows.getLastFocused().then((w) => {
  if (w && w.focused) focusedWindow = w.id;
});

// El service worker de MV3 puede dormirse; la alarma lo despierta para reconectar.
chrome.alarms.create("keepalive", { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener(() => connect());
chrome.runtime.onStartup.addListener(connect);
chrome.runtime.onInstalled.addListener(connect);
connect();
