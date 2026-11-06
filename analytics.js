(() => {
  "use strict";

  const measurementId = document.currentScript?.dataset.measurementId || "";
  if (!/^G-[A-Z0-9]+$/.test(measurementId) || window.__alienwayAnalyticsConsent) return;
  window.__alienwayAnalyticsConsent = true;

  const storageKey = "alienway.analytics-consent.v1";
  const disableKey = `ga-disable-${measurementId}`;
  const productionHost = location.protocol === "https:" && ["alienway.fun", "www.alienway.fun"].includes(location.hostname);
  const denied = {
    analytics_storage: "denied",
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
  };
  const granted = { ...denied, analytics_storage: "granted" };
  let started = false;
  let mounted = false;
  let panel;
  let settings;

  function readChoice() {
    try {
      const value = localStorage.getItem(storageKey);
      return value === "accepted" || value === "declined" ? value : null;
    } catch {
      return null;
    }
  }

  let choice = readChoice();
  window[disableKey] = true;

  function startAnalytics() {
    // Local previews and GitHub preview hostnames never send production traffic.
    if (!productionHost) return;
    window[disableKey] = false;
    if (started) {
      window.gtag("consent", "update", granted);
      return;
    }
    started = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    window.gtag("consent", "default", denied);
    window.gtag("set", {
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      ads_data_redaction: true,
      url_passthrough: false,
    });
    window.gtag("consent", "update", granted);
    window.gtag("js", new Date());
    let referrer = "";
    try { referrer = document.referrer ? new URL(document.referrer).origin : ""; } catch {}
    window.gtag("config", measurementId, {
      send_page_view: true,
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      cookie_domain: "none",
      cookie_flags: "SameSite=Lax;Secure",
      page_location: location.origin + location.pathname,
      page_referrer: referrer,
      page_title: "Alienway",
    });
    const tag = document.createElement("script");
    tag.async = true;
    tag.referrerPolicy = "origin";
    tag.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
    document.head.appendChild(tag);
  }

  function stopAnalytics() {
    // Set the opt-out flag before updating consent, including while gtag is loading.
    window[disableKey] = true;
    if (!started) return;
    window.gtag("consent", "update", denied);
    // This installation uses host-only cookies, scoped to the root path.
    for (const name of ["_ga", `_ga_${measurementId.slice(2)}`]) {
      try { document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax; Secure`; } catch {}
    }
  }

  function applyChoice() {
    if (!mounted) return;
    if (choice === "accepted") startAnalytics();
    else stopAnalytics();
    panel.hidden = choice !== null;
    settings.hidden = choice === null;
    settings.setAttribute("aria-expanded", String(!panel.hidden));
  }

  function choose(value) {
    choice = value;
    try { localStorage.removeItem(storageKey); } catch {}
    try { localStorage.setItem(storageKey, value); } catch {}
    applyChoice();
    settings.focus();
  }

  function mount() {
    if (mounted) return;
    mounted = true;
    const style = document.createElement("style");
    style.textContent = `
      #aw-analytics-consent,#aw-analytics-settings{box-sizing:border-box;position:fixed;z-index:10001;font:14px/1.5 system-ui,sans-serif;color:#e8f1f5;background:#0d1420;border:1px solid #536475;border-radius:12px;box-shadow:0 6px 28px #0005}
      #aw-analytics-consent{right:16px;bottom:16px;width:min(420px,calc(100vw - 32px));padding:20px}
      #aw-analytics-consent h2{font-size:17px;margin:0 0 8px;color:inherit}
      #aw-analytics-consent p{margin:0 0 14px}
      #aw-analytics-consent .aw-consent-actions{display:flex;gap:12px}
      #aw-analytics-consent button,#aw-analytics-settings{padding:10px 16px;font:inherit;cursor:pointer}
      #aw-analytics-consent button{flex:1;color:inherit;background:#17283a;border:1px solid #7993a8;border-radius:6px}
      #aw-analytics-settings{left:16px;bottom:16px}
      #aw-analytics-consent button:focus-visible,#aw-analytics-settings:focus-visible{outline:3px solid #4fd8e8;outline-offset:3px}
      #aw-analytics-consent[hidden],#aw-analytics-settings[hidden]{display:none}
    `;
    document.head.appendChild(style);
    panel = document.createElement("section");
    panel.id = "aw-analytics-consent";
    panel.setAttribute("aria-labelledby", "aw-analytics-title");
    const heading = document.createElement("h2");
    heading.id = "aw-analytics-title";
    heading.textContent = "Allow visit analytics?";
    const description = document.createElement("p");
    description.textContent = "With your permission, Google Analytics uses cookies to measure visits and device/browser information. Advertising features are off. We remember your choice in this browser when storage is available. You can change it using Analytics settings.";
    const actions = document.createElement("div");
    actions.className = "aw-consent-actions";
    for (const [label, value] of [["Accept", "accepted"], ["Decline", "declined"]]) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.addEventListener("click", () => choose(value));
      actions.appendChild(button);
    }
    panel.append(heading, description, actions);
    settings = document.createElement("button");
    settings.id = "aw-analytics-settings";
    settings.type = "button";
    settings.textContent = "Analytics settings";
    settings.setAttribute("aria-controls", panel.id);
    settings.addEventListener("click", () => {
      panel.hidden = false;
      settings.hidden = true;
      settings.setAttribute("aria-expanded", "true");
      panel.querySelector("button").focus();
    });
    document.body.append(panel, settings);
    applyChoice();
  }

  // The bundled landing page replaces documentElement before this event.
  window.addEventListener("alienway:page-ready", mount, { once: true });
  if (window.__alienwayPageReady) mount();
  window.addEventListener("storage", (event) => {
    if (event.key !== storageKey && event.key !== null) return;
    choice = readChoice();
    applyChoice();
  });
})();
