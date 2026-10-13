// =========================================================================
// SIGEduc Auto - Page Bridge (Runs in MAIN world)
// Intercepta e auto-aceita confirmações nativas (confirm/alert) do SIGEduc
// Exemplo: "Deseja realmente gravar as frequências para o dia selecionado?"
// =========================================================================
(function() {
  if (typeof window === "undefined") return;

  try {
    const _origConfirm = window.confirm;
    window.confirm = function(msg) {
      console.log("[SIGEduc Auto Page Bridge] confirm() auto-aceito:", msg);
      return true;
    };

    const _origAlert = window.alert;
    window.alert = function(msg) {
      console.log("[SIGEduc Auto Page Bridge] alert() interceptado:", msg);
      return true;
    };

    window.__sgn_bridge_active = true;
    console.log("[SIGEduc Auto Page Bridge] Bridge de confirmação ativa no mundo principal.");
  } catch (e) {
    console.warn("[SIGEduc Auto Page Bridge] Erro ao registrar interceptores:", e);
  }
})();
