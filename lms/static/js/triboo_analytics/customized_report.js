var log = console.log.bind(console)

function expandSection(sectionToggleButton) {
  const $toggleButtonChevron = $(sectionToggleButton).children('.fa-chevron-down');
  const $contentPanel = $(document.getElementById(sectionToggleButton.getAttribute('aria-controls')));

  $contentPanel.slideDown();
  $contentPanel.removeClass('is-hidden');
  $toggleButtonChevron.addClass('fa-rotate-180');
  sectionToggleButton.setAttribute('aria-expanded', 'true');
}

function collapseSection(sectionToggleButton) {
  const $toggleButtonChevron = $(sectionToggleButton).children('.fa-chevron-down');
  const $contentPanel = $(document.getElementById(sectionToggleButton.getAttribute('aria-controls')));

  $contentPanel.slideUp();
  $contentPanel.addClass('is-hidden');
  $toggleButtonChevron.removeClass('fa-rotate-180');
  sectionToggleButton.setAttribute('aria-expanded', 'false');
}

function triggerExpand() {
  const sections = Array.prototype.slice.call(document.querySelectorAll('.accordion-trigger'));

  sections.forEach(section => section.addEventListener('click', (event) => {
    const sectionToggleButton = event.currentTarget;
    if (sectionToggleButton.classList.contains('accordion-trigger')) {
      const isExpanded = sectionToggleButton.getAttribute('aria-expanded') === 'true';
      if (!isExpanded) {
        expandSection(sectionToggleButton);
      } else if (isExpanded) {
        collapseSection(sectionToggleButton);
      }
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }));
}

function __main() {
  triggerExpand()
}

__main()