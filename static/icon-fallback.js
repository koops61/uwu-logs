(function () {
  function fallback(img) {
    var step = Number(img.getAttribute('data-step') || '0');
    var alt1 = img.getAttribute('data-alt1');
    var alt2 = img.getAttribute('data-alt2');
    if (step === 0 && alt1) {
      img.setAttribute('data-step', '1');
      img.src = alt1;
    } else if (step === 1 && alt2) {
      img.setAttribute('data-step', '2');
      img.src = alt2;
    } else {
      img.onerror = null;
      img.src = '/static/icons/inv_misc_questionmark.jpg';
    }
  }

  function hook(img) {
    img.addEventListener('error', function () { fallback(img); }, { once:false });
  }

  function init() {
    document
      .querySelectorAll('img.item-icon, img.gem-icon')
      .forEach(hook);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
