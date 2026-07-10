const pageTitles = {
  overview: '总览',
  run: 'Dev Run',
  review: '审阅队列',
  ask: 'Context Ask',
  sources: 'Sources',
  wiki: 'Wiki',
  skills: 'Skills',
  evaluation: 'Evaluations',
};

const views = new Map(
  [...document.querySelectorAll('[data-view]')].map((view) => [view.dataset.view, view]),
);
const mainContent = document.querySelector('#main-content');
const pageTitle = document.querySelector('[data-page-title]');
const drawer = document.querySelector('#mobile-drawer');
const drawerScrim = document.querySelector('.drawer-scrim');
const mobileQuery = window.matchMedia('(max-width: 899px)');
const liveRegion = document.querySelector('#live-region');

let lastFocusedElement = null;
let toastTimer = null;

function showToast(message) {
  window.clearTimeout(toastTimer);
  liveRegion.textContent = message;
  liveRegion.hidden = false;
  toastTimer = window.setTimeout(() => {
    liveRegion.hidden = true;
    liveRegion.textContent = '';
  }, 3600);
}

function activateView(route, options = {}) {
  const nextRoute = views.has(route) ? route : 'overview';
  const { updateHash = true, focus = true } = options;

  for (const [name, view] of views) {
    const active = name === nextRoute;
    view.hidden = !active;
    view.classList.toggle('is-active', active);
  }

  for (const navItem of document.querySelectorAll('.nav-item[data-route]')) {
    const active = navItem.dataset.route === nextRoute;
    navItem.classList.toggle('is-active', active);
    if (active) {
      navItem.setAttribute('aria-current', 'page');
    } else {
      navItem.removeAttribute('aria-current');
    }
  }

  pageTitle.textContent = pageTitles[nextRoute];
  document.title = `${pageTitles[nextRoute]} · Inkdesk`;

  if (updateHash && window.location.hash !== `#${nextRoute}`) {
    history.pushState(null, '', `#${nextRoute}`);
  }

  if (mobileQuery.matches) {
    toggleDrawer(false);
  }

  if (focus) {
    window.requestAnimationFrame(() => mainContent.focus({ preventScroll: true }));
  }
}

function toggleDrawer(force) {
  const shouldOpen = typeof force === 'boolean' ? force : !drawer.classList.contains('is-open');
  drawer.classList.toggle('is-open', shouldOpen);
  drawer.setAttribute('aria-hidden', String(!shouldOpen));
  drawerScrim.hidden = !shouldOpen;

  if (shouldOpen) {
    lastFocusedElement = document.activeElement;
    window.requestAnimationFrame(() => drawer.querySelector('.sidebar-close').focus());
  } else if (lastFocusedElement?.matches('[data-drawer-open]')) {
    lastFocusedElement.focus();
  }
}

function syncDrawerMode() {
  if (mobileQuery.matches) {
    drawer.classList.remove('is-open');
    drawer.setAttribute('aria-hidden', 'true');
    drawerScrim.hidden = true;
  } else {
    drawer.classList.remove('is-open');
    drawer.setAttribute('aria-hidden', 'false');
    drawerScrim.hidden = true;
  }
}

function getFocusable(container) {
  return [...container.querySelectorAll('a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])')]
    .filter((element) => !element.hidden && element.getClientRects().length > 0);
}

function openDialog(id) {
  const dialog = document.getElementById(id);
  if (!dialog) return;

  lastFocusedElement = document.activeElement;
  dialog.hidden = false;
  document.body.style.overflow = 'hidden';
  window.requestAnimationFrame(() => {
    const firstField = dialog.querySelector('input, select, textarea, button');
    firstField?.focus();
  });
}

function closeDialog(id) {
  const dialog = document.getElementById(id);
  if (!dialog || dialog.hidden) return;

  dialog.hidden = true;
  document.body.style.overflow = '';
  lastFocusedElement?.focus?.();
}

function applyReviewFilter(filter) {
  const items = [...document.querySelectorAll('[data-review-item]')];
  let visibleCount = 0;

  for (const item of items) {
    const visible = filter === 'all' || item.dataset.risk === filter;
    item.hidden = !visible;
    if (visible) visibleCount += 1;
  }

  for (const button of document.querySelectorAll('[data-review-filter]')) {
    const active = button.dataset.reviewFilter === filter;
    button.classList.toggle('is-active', active);
    button.setAttribute('aria-pressed', String(active));
  }

  const selected = items.find((item) => !item.hidden && item.classList.contains('is-selected'))
    ?? items.find((item) => !item.hidden);
  if (selected) selectDetail(selected.dataset.detailTarget, selected);
  showToast(`已显示 ${visibleCount} 项审阅内容`);
}

function selectDetail(target, trigger) {
  if (!target) return;

  const container = trigger?.closest('.split-workspace, .skills-layout, .eval-layout')
    ?? document.querySelector(`[data-detail-panel="${target}"]`)?.parentElement;
  if (!container) return;

  const panel = container.querySelector(`[data-detail-panel="${target}"]`);
  if (!panel) return;

  for (const candidate of container.querySelectorAll('[data-detail-panel]')) {
    candidate.hidden = candidate !== panel;
  }

  for (const candidate of container.querySelectorAll('[data-detail-target]')) {
    const selected = candidate.dataset.detailTarget === target;
    candidate.classList.toggle('is-selected', selected);
    candidate.setAttribute('aria-pressed', String(selected));
  }
}

function activateStage(stageName) {
  const runView = views.get('run');
  if (!runView) return;

  for (const panel of runView.querySelectorAll('[data-stage-panel]')) {
    const active = panel.dataset.stagePanel === stageName;
    panel.hidden = !active;
    panel.classList.toggle('is-active', active);
  }

  for (const step of runView.querySelectorAll('[data-stage]')) {
    const active = step.dataset.stage === stageName;
    if (active) {
      step.setAttribute('aria-current', 'step');
    } else {
      step.removeAttribute('aria-current');
    }
  }
}

function validateRunForm(form) {
  let valid = true;
  const fields = [
    { input: form.elements.name, error: document.querySelector('#run-name-error'), message: '请输入任务名称。' },
    { input: form.elements.goal, error: document.querySelector('#run-goal-error'), message: '请说明目标与验收标准。' },
  ];

  for (const field of fields) {
    const empty = !field.input.value.trim();
    field.error.textContent = empty ? field.message : '';
    field.input.closest('.ds-input, .dialog-field')?.classList.toggle('is-error', empty);
    field.input.setAttribute('aria-invalid', String(empty));
    if (empty && valid) {
      valid = false;
      field.input.focus();
    }
  }

  return valid;
}

document.addEventListener('click', (event) => {
  const routeTrigger = event.target.closest('[data-route]');
  if (routeTrigger) {
    event.preventDefault();
    activateView(routeTrigger.dataset.route);
    if (routeTrigger.dataset.detailTarget) {
      const detailTrigger = document.querySelector(`[data-review-item][data-detail-target="${routeTrigger.dataset.detailTarget}"]`);
      selectDetail(routeTrigger.dataset.detailTarget, detailTrigger);
    }
    return;
  }

  if (event.target.closest('[data-drawer-open]')) {
    toggleDrawer(true);
    return;
  }

  if (event.target.closest('[data-drawer-close]')) {
    toggleDrawer(false);
    return;
  }

  const openTrigger = event.target.closest('[data-dialog-open]');
  if (openTrigger) {
    openDialog(openTrigger.dataset.dialogOpen);
    return;
  }

  const closeTrigger = event.target.closest('[data-dialog-close]');
  if (closeTrigger) {
    closeDialog(closeTrigger.dataset.dialogClose);
    return;
  }

  const filter = event.target.closest('[data-review-filter]');
  if (filter) {
    applyReviewFilter(filter.dataset.reviewFilter);
    return;
  }

  const detailTrigger = event.target.closest('[data-detail-target]');
  if (detailTrigger) {
    selectDetail(detailTrigger.dataset.detailTarget, detailTrigger);
    return;
  }

  const stage = event.target.closest('[data-stage]');
  if (stage) {
    activateStage(stage.dataset.stage);
    return;
  }

  const eventToggle = event.target.closest('[data-event-toggle]');
  if (eventToggle) {
    const expanded = eventToggle.getAttribute('aria-expanded') === 'true';
    eventToggle.setAttribute('aria-expanded', String(!expanded));
    eventToggle.querySelector('.event-chevron')?.setAttribute('alt', expanded ? '展开事件' : '收起事件');
    return;
  }

  const citation = event.target.closest('[data-citation-toggle]');
  if (citation) {
    const expanded = citation.getAttribute('aria-expanded') === 'true';
    citation.setAttribute('aria-expanded', String(!expanded));
    return;
  }

  const fillQuestion = event.target.closest('[data-fill-question]');
  if (fillQuestion) {
    const textarea = document.querySelector('#ask-question');
    textarea.value = fillQuestion.dataset.fillQuestion;
    textarea.focus();
    return;
  }

  const askSubmit = event.target.closest('[data-ask-submit]');
  if (askSubmit) {
    askSubmit.disabled = true;
    const originalText = askSubmit.textContent;
    askSubmit.textContent = '正在检索证据…';
    window.setTimeout(() => {
      askSubmit.disabled = false;
      askSubmit.textContent = originalText;
      showToast('回答已基于 6 条引用重新生成');
    }, 600);
    return;
  }

  const proposal = event.target.closest('[data-deposit-proposal]');
  if (proposal) {
    proposal.disabled = true;
    proposal.textContent = 'Proposal 已生成';
    showToast('3 条候选 claim 已进入审阅队列');
    return;
  }

  const notice = event.target.closest('[data-notice]');
  if (notice) {
    showToast(notice.dataset.notice);
    return;
  }

  const tab = event.target.closest('[role="tab"]');
  if (tab) {
    const tablist = tab.closest('[role="tablist"]');
    for (const candidate of tablist.querySelectorAll('[role="tab"]')) {
      const active = candidate === tab;
      candidate.classList.toggle('is-active', active);
      candidate.setAttribute('aria-selected', String(active));
    }
  }
});

document.addEventListener('input', (event) => {
  const search = event.target.closest('[data-list-search]');
  if (!search) return;

  const list = document.querySelector(`[data-search-list="${search.dataset.listSearch}"]`);
  if (!list) return;

  const query = search.value.trim().toLocaleLowerCase('zh-CN');
  for (const item of list.querySelectorAll('[data-search-text]')) {
    item.hidden = query !== '' && !item.dataset.searchText.toLocaleLowerCase('zh-CN').includes(query);
  }
});

document.querySelector('#new-run-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  if (!validateRunForm(form)) return;

  const name = form.elements.name.value.trim();
  closeDialog('new-run-dialog');
  form.reset();
  document.querySelector('#run-name-error').textContent = '';
  document.querySelector('#run-goal-error').textContent = '';
  showToast(`Dev Run“${name}”已创建，正在生成 Context Pack`);
  activateView('run');
});

document.addEventListener('keydown', (event) => {
  const activeDialog = document.querySelector('.dialog-layer:not([hidden])');

  if (event.key === 'Escape') {
    if (activeDialog) {
      closeDialog(activeDialog.id);
    } else if (drawer.classList.contains('is-open')) {
      toggleDrawer(false);
    }
    return;
  }

  if (event.key === 'Tab' && activeDialog) {
    const focusable = getFocusable(activeDialog);
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
});

window.addEventListener('hashchange', () => {
  activateView(window.location.hash.slice(1), { updateHash: false });
});

mobileQuery.addEventListener('change', syncDrawerMode);
syncDrawerMode();
activateView(window.location.hash.slice(1) || 'overview', { updateHash: false, focus: false });
