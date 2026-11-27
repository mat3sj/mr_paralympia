// Steppers on "my day" and hover cards on the board.
document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-step]');
  if (!button) return;
  const input = button.parentElement.querySelector('input');
  const value = parseFloat(input.value.replace(',', '.')) || 0;
  const next = Math.max(0, Math.round((value + parseFloat(button.dataset.step)) * 10) / 10);
  const decimalSeparator = document.documentElement.lang === 'cs' ? ',' : '.';
  input.value = String(next).replace('.', decimalSeparator);
  input.dispatchEvent(new Event('change', { bubbles: true }));
});

(() => {
  const tip = document.getElementById('tip');
  if (!tip) return;
  let anchor = null;
  const target = (event) => event.target.closest('[data-tip]');

  function hide() { tip.hidden = true; anchor = null; }
  function show(element) {
    tip.innerHTML = element.querySelector('template.tip-content').innerHTML;
    tip.hidden = false;
    anchor = element;
    const rect = element.getBoundingClientRect();
    const tipRect = tip.getBoundingClientRect();
    let x = rect.left + rect.width / 2 - tipRect.width / 2;
    let y = rect.bottom + 8;
    if (y + tipRect.height > innerHeight - 8) y = rect.top - tipRect.height - 8;
    x = Math.max(8, Math.min(x, innerWidth - tipRect.width - 8));
    tip.style.left = x + 'px';
    tip.style.top = Math.max(8, y) + 'px';
  }

  document.addEventListener('mouseover', (event) => {
    const element = target(event);
    if (element && element !== anchor) show(element);
  });
  document.addEventListener('mouseout', (event) => {
    const element = target(event);
    if (element && !element.contains(event.relatedTarget)) hide();
  });
  document.addEventListener('focusin', (event) => {
    const element = target(event);
    if (element) show(element);
  });
  document.addEventListener('focusout', hide);
  document.addEventListener('click', (event) => {
    const element = target(event);
    if (!element) return;
    if (anchor === element && !tip.hidden) hide(); else show(element);
  });
  document.addEventListener('scroll', hide, { capture: true, passive: true });

  const scroller = document.querySelector('.table-scroll');
  if (scroller) scroller.scrollLeft = scroller.scrollWidth;
})();
