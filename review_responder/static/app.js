const state = {
  reviews: [],
  replies: {},      // review id -> GeneratedReply
  posted: new Set(),
  brandYamlOriginal: "",
};

const $ = (sel) => document.querySelector(sel);

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}

const postJSON = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

let toastTimer;
function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
}

function tag(text, cls = "") {
  const span = document.createElement("span");
  span.className = `tag ${cls}`;
  span.textContent = text;
  return span;
}

// --- Status & brand ---------------------------------------------------------

async function loadStatus() {
  const s = await api("/api/status");
  $("#business-name").textContent = `Replying as ${s.business}`;
  const status = $("#status");
  status.replaceChildren(
    s.generator === "claude"
      ? tag(`AI: ${s.model}`, "ok")
      : tag("Offline template mode (no API key)", "warn"),
    tag(s.google === "live" ? "Google: live" : "Google: demo data", s.google === "live" ? "ok" : ""),
  );
  $("#google-hint").textContent = s.google === "live"
    ? "Fetch unanswered reviews from your Google Business Profile."
    : "Google isn't connected, so this loads demo reviews from samples/google_reviews.json and posting is simulated.";
}

async function loadBrand() {
  const { yaml } = await api("/api/brand");
  state.brandYamlOriginal = yaml;
  $("#brand-input").value = yaml;
}

// --- Loading reviews ----------------------------------------------------------

function setReviews(reviews, label) {
  state.reviews = reviews;
  state.replies = {};
  state.posted = new Set();
  render();
  toast(reviews.length ? `Loaded ${reviews.length} review${reviews.length === 1 ? "" : "s"} from ${label}` : "No reviews found");
}

async function withBusy(button, fn) {
  const label = button.textContent;
  button.disabled = true;
  button.textContent = "Working…";
  try { await fn(); }
  catch (e) { toast(e.message); }
  finally { button.disabled = false; button.textContent = label; }
}

$("#load-sample").addEventListener("click", (e) =>
  withBusy(e.target, async () => setReviews(await api("/api/samples"), "sample data")));

$("#load-paste").addEventListener("click", (e) =>
  withBusy(e.target, async () => {
    const text = $("#paste-input").value.trim();
    if (!text) return toast("Paste some reviews first");
    setReviews(await postJSON("/api/parse/text", { text }), "pasted text");
  }));

$("#csv-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  try { setReviews(await api("/api/parse/csv", { method: "POST", body: form }), file.name); }
  catch (err) { toast(err.message); }
  e.target.value = "";
});

$("#load-google").addEventListener("click", (e) =>
  withBusy(e.target, async () => {
    const { mode, reviews } = await api("/api/google/reviews");
    setReviews(reviews, mode === "live" ? "Google" : "Google demo data");
  }));

document.querySelectorAll(".tab").forEach((tab) =>
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    document.querySelectorAll(".tab-body").forEach((b) => (b.hidden = b.dataset.body !== tab.dataset.tab));
  }));

$("#reset-brand").addEventListener("click", () => {
  $("#brand-input").value = state.brandYamlOriginal;
  toast("Brand voice reset");
});

// --- Generating -----------------------------------------------------------------

async function generate(reviews) {
  const brandYaml = $("#brand-input").value;
  const replies = await postJSON("/api/generate", {
    reviews,
    brand_yaml: brandYaml.trim() ? brandYaml : null,
  });
  for (const r of replies) state.replies[r.review_id] = r;
  return replies;
}

$("#generate").addEventListener("click", (e) =>
  withBusy(e.target, async () => {
    document.querySelectorAll(".card").forEach((c) => c.classList.add("loading"));
    try {
      const replies = await generate(state.reviews);
      const failed = replies.filter((r) => r.error).length;
      toast(failed ? `Generated with ${failed} error(s)` : `Generated ${replies.length} replies`);
    } finally {
      render();
    }
  }));

// --- Rendering ------------------------------------------------------------------

function countWords(text) {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

function renderCard(review) {
  const node = $("#card-template").content.firstElementChild.cloneNode(true);
  node.dataset.id = review.id;
  node.querySelector(".author").textContent = review.author || "Anonymous";
  if (review.rating) {
    node.querySelector(".stars").textContent = "★".repeat(review.rating) + "☆".repeat(5 - review.rating);
    node.querySelector(".rating-text").textContent = `${review.rating} out of 5 stars`;
  }
  node.querySelector(".date").textContent = review.date || "";
  node.querySelector(".source").textContent = review.source;
  const text = node.querySelector(".review-text");
  if (review.text) text.textContent = review.text;
  else { text.textContent = "No written review, rating only."; text.classList.add("empty-text"); }

  const reply = state.replies[review.id];
  if (!reply) return node;

  const box = node.querySelector(".reply");
  box.hidden = false;
  const sentiment = node.querySelector(".sentiment");
  sentiment.textContent = reply.sentiment;
  sentiment.classList.add(reply.sentiment);
  node.querySelector(".attention").hidden = !reply.needs_attention;
  node.querySelector(".generator").textContent = reply.generator === "claude" ? "AI" : "template";
  node.querySelector(".notes").textContent = reply.notes || "";

  const textarea = node.querySelector(".reply-text");
  const words = node.querySelector(".words");
  textarea.value = reply.reply;
  const updateWords = () => (words.textContent = `${countWords(textarea.value)} words`);
  updateWords();
  textarea.addEventListener("input", () => { reply.reply = textarea.value; updateWords(); });

  if (reply.error) {
    const err = node.querySelector(".error");
    err.hidden = false;
    err.textContent = reply.error;
  }

  node.querySelector(".copy").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(textarea.value); toast("Reply copied"); }
    catch { textarea.select(); toast("Press Ctrl+C to copy"); }
  });

  node.querySelector(".regen").addEventListener("click", (e) =>
    withBusy(e.target, async () => {
      node.classList.add("loading");
      try { await generate([review]); }
      finally { render(); }
    }));

  const post = node.querySelector(".post");
  if (review.source === "google") {
    post.hidden = false;
    if (state.posted.has(review.id)) { post.disabled = true; post.textContent = "Posted ✓"; }
    post.addEventListener("click", () => {
      if (!textarea.value.trim()) return toast("Reply is empty");
      if (!confirm(`Post this reply publicly to ${review.author || "this reviewer"}'s Google review?`)) return;
      withBusy(post, async () => {
        const { mode } = await postJSON("/api/google/reply", { review_id: review.id, comment: textarea.value });
        state.posted.add(review.id);
        toast(mode === "live" ? "Reply posted to Google" : "Simulated post (demo mode, nothing was sent)");
      }).then(() => {
        if (state.posted.has(review.id)) { post.disabled = true; post.textContent = "Posted ✓"; }
      });
    });
  }
  return node;
}

function render() {
  const cards = $("#cards");
  const n = state.reviews.length;
  $("#generate").disabled = n === 0;
  $("#export").disabled = Object.keys(state.replies).length === 0;
  if (!n) {
    cards.innerHTML = '<div class="empty"><p><strong>Start with the sample data</strong> to see how it works, or paste your own reviews.</p></div>';
    $("#summary").textContent = "No reviews loaded yet.";
    return;
  }
  const replies = Object.values(state.replies);
  const flagged = replies.filter((r) => r.needs_attention).length;
  $("#summary").textContent = replies.length
    ? `${n} reviews · ${replies.length} replies drafted · ${flagged} flagged for follow-up`
    : `${n} reviews loaded. Generate replies when you're ready.`;
  cards.replaceChildren(...state.reviews.map(renderCard));
}

// --- Export -----------------------------------------------------------------------

function csvCell(value) {
  const s = String(value ?? "");
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

$("#export").addEventListener("click", () => {
  const header = ["id", "author", "rating", "date", "review", "reply", "sentiment", "needs_attention", "notes"];
  const rows = state.reviews.map((r) => {
    const rep = state.replies[r.id] || {};
    return [r.id, r.author, r.rating ?? "", r.date, r.text, rep.reply ?? "", rep.sentiment ?? "", rep.needs_attention ?? "", rep.notes ?? ""];
  });
  const csv = [header, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: "review-replies.csv" });
  a.click();
  URL.revokeObjectURL(url);
});

loadStatus().catch((e) => toast(e.message));
loadBrand().catch((e) => toast(e.message));
