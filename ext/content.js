// ZEUS GUARD content script — injeta o hook no mundo da pagina ANTES de qualquer
// script do site rodar, garantindo que o ethereum embrulhado seja o que o dapp ve.
(function () {
  const container = document.head || document.documentElement || document;
  const s = document.createElement("script");
  s.src = chrome.runtime.getURL("zeus_hook.js");
  s.async = false;
  if (container.appendChild) {
    container.appendChild(s);
  } else {
    (document.head || document.documentElement).appendChild(s);
  }
})();
