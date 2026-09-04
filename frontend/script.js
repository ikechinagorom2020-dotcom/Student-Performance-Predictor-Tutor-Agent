(function () {
  const TAB_ORDER = ["about", "family", "school", "lifestyle"];
  let currentTabIndex = 0;

  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".tab-panel");
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");
  const submitBtn = document.getElementById("submit-btn");
  const form = document.getElementById("predict-form");

  function showTab(index) {
    currentTabIndex = index;
    const targetName = TAB_ORDER[index];

    tabs.forEach((tab) => {
      const isActive = tab.dataset.tab === targetName;
      tab.classList.toggle("active", isActive);
      tab.setAttribute("aria-selected", isActive ? "true" : "false");
    });
    panels.forEach((panel) => {
      panel.classList.toggle("active", panel.dataset.panel === targetName);
    });

    prevBtn.disabled = index === 0;
    const isLast = index === TAB_ORDER.length - 1;
    nextBtn.classList.toggle("hidden", isLast);
    submitBtn.classList.toggle("hidden", !isLast);
  }

  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => showTab(i));
  });
  prevBtn.addEventListener("click", () => showTab(Math.max(0, currentTabIndex - 1)));
  nextBtn.addEventListener("click", () => showTab(Math.min(TAB_ORDER.length - 1, currentTabIndex + 1)));

  document.querySelectorAll(".toggle").forEach((toggle) => {
    const opts = toggle.querySelectorAll(".toggle-opt");
    opts.forEach((opt) => {
      opt.addEventListener("click", () => {
        opts.forEach((o) => o.classList.remove("active"));
        opt.classList.add("active");
      });
    });
  });

  function getToggleValue(name) {
    const toggle = document.querySelector(`.toggle[data-name="${name}"]`);
    const active = toggle.querySelector(".toggle-opt.active");
    return active ? active.dataset.value : "no";
  }

  document.querySelectorAll('input[type="range"]').forEach((slider) => {
    const out = document.getElementById(`${slider.id}-val`);
    if (out) {
      slider.addEventListener("input", () => { out.textContent = slider.value; });
    }
  });

  const resultsEmpty = document.getElementById("results-empty");
  const resultsLoading = document.getElementById("results-loading");
  const resultsContent = document.getElementById("results-content");
  const resultsError = document.getElementById("results-error");

  function setResultsState(state) {
    [resultsEmpty, resultsLoading, resultsContent, resultsError].forEach((el) => el.classList.add("hidden"));
    state.classList.remove("hidden");
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function formatPlanText(raw) {
    const escaped = escapeHtml(raw);
    return escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function scoreZoneInfo(score) {
    if (score < 10) return { className: "zone-low", label: "Needs attention" };
    if (score < 13) return { className: "zone-mid", label: "Room to grow" };
    return { className: "zone-high", label: "On track" };
  }

  const LOADING_MESSAGES = [
    "Running the model…",
    "Weighing your study habits…",
    "Writing your personalized plan…",
  ];
  let loadingInterval = null;

  function startLoadingMessages() {
    const el = document.getElementById("loading-message");
    let i = 0;
    el.textContent = LOADING_MESSAGES[0];
    loadingInterval = setInterval(() => {
      i = (i + 1) % LOADING_MESSAGES.length;
      el.textContent = LOADING_MESSAGES[i];
    }, 1100);
  }

  function stopLoadingMessages() {
    if (loadingInterval) {
      clearInterval(loadingInterval);
      loadingInterval = null;
    }
  }

  // ---------------- Practice quiz panel ----------------
  const quizForm = document.getElementById("quiz-form");
  const quizInput = document.getElementById("quiz-input");
  const quizLog = document.getElementById("quiz-log");
  const quizStatsBadge = document.getElementById("quiz-stats-badge");
  const quizSendBtn = document.getElementById("quiz-send-btn");

  function getSessionId() {
    let id = localStorage.getItem("tutor_session_id");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("tutor_session_id", id);
    }
    return id;
  }

  function appendQuizMessage(role, text) {
    const emptyHint = quizLog.querySelector(".quiz-empty-hint");
    if (emptyHint) emptyHint.remove();

    const bubble = document.createElement("div");
    bubble.className = `quiz-msg ${role}`;
    bubble.innerHTML = formatPlanText(text);
    quizLog.appendChild(bubble);
    quizLog.scrollTop = quizLog.scrollHeight;
    return bubble;
  }

  quizForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = quizInput.value.trim();
    if (!message) return;

    appendQuizMessage("user", message);
    quizInput.value = "";
    quizSendBtn.disabled = true;

    const loadingBubble = appendQuizMessage("assistant loading", "Thinking…");

    try {
      const res = await fetch("/api/tutor-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: getSessionId(),
          message: message,
          subject: document.getElementById("subject").value,
        }),
      });

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `Request failed (${res.status})`);
      }

      const data = await res.json();
      loadingBubble.remove();
      appendQuizMessage("assistant", data.reply);
      quizStatsBadge.textContent = `${data.quiz_stats.correct} / ${data.quiz_stats.attempted} correct`;
    } catch (err) {
      loadingBubble.remove();
      appendQuizMessage("assistant", `Sorry, something went wrong: ${err.message}`);
    } finally {
      quizSendBtn.disabled = false;
      quizInput.focus();
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setResultsState(resultsLoading);
    startLoadingMessages();
    submitBtn.disabled = true;

    const payload = {
      school: document.getElementById("school").value,
      sex: document.getElementById("sex").value,
      age: parseInt(document.getElementById("age").value, 10),
      address: document.getElementById("address").value,
      famsize: document.getElementById("famsize").value,
      Pstatus: document.getElementById("Pstatus").value,
      Medu: parseInt(document.getElementById("Medu").value, 10),
      Fedu: parseInt(document.getElementById("Fedu").value, 10),
      Mjob: document.getElementById("Mjob").value,
      Fjob: document.getElementById("Fjob").value,
      reason: document.getElementById("reason").value,
      guardian: document.getElementById("guardian").value,
      traveltime: parseInt(document.getElementById("traveltime").value, 10),
      studytime: parseInt(document.getElementById("studytime").value, 10),
      failures: parseInt(document.getElementById("failures").value, 10),
      schoolsup: getToggleValue("schoolsup"),
      famsup: getToggleValue("famsup"),
      paid: getToggleValue("paid"),
      activities: getToggleValue("activities"),
      nursery: getToggleValue("nursery"),
      higher: getToggleValue("higher"),
      internet: getToggleValue("internet"),
      romantic: getToggleValue("romantic"),
      famrel: parseInt(document.getElementById("famrel").value, 10),
      freetime: parseInt(document.getElementById("freetime").value, 10),
      goout: parseInt(document.getElementById("goout").value, 10),
      Dalc: parseInt(document.getElementById("Dalc").value, 10),
      Walc: parseInt(document.getElementById("Walc").value, 10),
      health: parseInt(document.getElementById("health").value, 10),
      absences: parseInt(document.getElementById("absences").value, 10),
      subject: document.getElementById("subject").value,
    };

    try {
      const res = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `Request failed (${res.status})`);
      }

      const data = await res.json();
      const zone = scoreZoneInfo(data.predicted_score);

      document.getElementById("score-number").textContent = data.predicted_score;
      document.getElementById("score-ring").className = "score-ring " + zone.className;
      document.getElementById("score-zone").textContent = zone.label;
      document.getElementById("score-zone").className = "score-zone " + zone.className;
      document.getElementById("plan-text").innerHTML = formatPlanText(data.study_plan);

      setResultsState(resultsContent);
    } catch (err) {
      document.getElementById("error-message").textContent = err.message || "Please try again in a moment.";
      setResultsState(resultsError);
    } finally {
      stopLoadingMessages();
      submitBtn.disabled = false;
    }
  });

  document.getElementById("retry-btn").addEventListener("click", () => {
    setResultsState(resultsEmpty);
  });

  document.getElementById("reset-btn").addEventListener("click", () => {
    form.reset();
    showTab(0);
    document.querySelectorAll(".toggle").forEach((toggle) => {
      const opts = toggle.querySelectorAll(".toggle-opt");
      opts.forEach((o, i) => o.classList.toggle("active", i === 0));
    });
    document.querySelectorAll('input[type="range"]').forEach((slider) => {
      const out = document.getElementById(`${slider.id}-val`);
      if (out) out.textContent = slider.value;
    });

    localStorage.removeItem("tutor_session_id");
    quizLog.innerHTML = '<p class="quiz-empty-hint">Ask to be quizzed on your subject, answer questions, and track your score here.</p>';
    quizStatsBadge.textContent = "0 / 0 correct";

    setResultsState(resultsEmpty);
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  showTab(0);
})();
