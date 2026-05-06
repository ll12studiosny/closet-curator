// Lightweight localStorage-backed store for the prototype.
window.CC = (function () {
  const KEY = 'cc.v1';

  const defaults = {
    onboarded: false,
    profile: {
      styles: [],          // ranked array of style ids
      body: { height_cm: null, weight_kg: null, body_type: null },
      fit_preference: 'regular',
    },
    closet: [],            // [{id, name, type, primary_color, fit, style_tags, image (dataURL)}]
    saved: [],             // saved outfits
    feedback: { liked: [], disliked: [] },
    weather: { temp_c: 18, condition: 'clear' },
  };

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return structuredClone(defaults);
      const data = JSON.parse(raw);
      return Object.assign(structuredClone(defaults), data);
    } catch (e) {
      return structuredClone(defaults);
    }
  }

  function save(state) {
    localStorage.setItem(KEY, JSON.stringify(state));
  }

  let state = load();

  return {
    get() { return state; },
    update(fn) {
      fn(state);
      save(state);
      return state;
    },
    reset() {
      state = structuredClone(defaults);
      save(state);
    },
    addClosetItem(item) {
      state.closet.push(item);
      save(state);
    },
    removeClosetItem(id) {
      state.closet = state.closet.filter(i => i.id !== id);
      save(state);
    },
    saveOutfit(outfit) {
      if (!state.saved.find(o => o.id === outfit.id)) {
        state.saved.push(outfit);
        save(state);
      }
    },
    unsaveOutfit(id) {
      state.saved = state.saved.filter(o => o.id !== id);
      save(state);
    },
    likeOutfit(id) {
      if (!state.feedback.liked.includes(id)) state.feedback.liked.push(id);
      state.feedback.disliked = state.feedback.disliked.filter(x => x !== id);
      save(state);
    },
    dislikeOutfit(id) {
      if (!state.feedback.disliked.includes(id)) state.feedback.disliked.push(id);
      state.feedback.liked = state.feedback.liked.filter(x => x !== id);
      save(state);
    },
  };
})();

window.toast = function (msg) {
  let t = document.querySelector('.toast');
  if (!t) {
    t = document.createElement('div');
    t.className = 'toast';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(window._toastT);
  window._toastT = setTimeout(() => t.classList.remove('show'), 2000);
};

window.uid = function () {
  return Math.random().toString(36).slice(2, 10);
};
