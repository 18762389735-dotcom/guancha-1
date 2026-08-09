(function (global) {
  'use strict';
  const actionLabels = {
    'currently-selectable': '当前可选',
    'ask-before-buying': '先问清再买',
    'sample-first': '建议先试小样',
    'not-recommended-now': '暂不建议',
    'insufficient-information': '信息不足，无法判断',
  };
  function jobToCandidateStatus(job) {
    const status = job && job.status;
    return ['queued', 'processing', 'completed', 'failed', 'stale'].includes(status) ? status : 'empty';
  }
  function candidateToViewModel(candidate) {
    return {
      id: candidate.id,
      label: candidate.letter,
      displayName: candidate.name || '待提取商品信息',
      images: (candidate.images || []).map((image) => ({ id: image.id, status: image.status, errorCode: image.errorCode })),
      extractionVersionId: candidate.extractionVersionId || null,
      extractionStatus: candidate.extractionStatus || 'empty',
    };
  }
  function buildPreferenceReference({ o1 = {}, o2 = {} } = {}) {
    const references = [];
    const selectedDrinks = Object.values(o1).flat().filter(Boolean).slice(0, 2);
    if (selectedDrinks.length) {
      references.push({
        source: 'o1', source_value: selectedDrinks.join('、'),
        text: `你在偏好设置中选过${selectedDrinks.join('、')}。`,
      });
    }
    const flavors = Array.isArray(o2.flavors) ? o2.flavors.filter(Boolean).slice(0, 2) : [];
    if (flavors.length) {
      references.push({
        source: 'o2', source_value: flavors.join('、'),
        text: `你关注的风味里有${flavors.join('、')}。`,
      });
    }
    return references.slice(0, 2);
  }
  function buildPersonalFitPresentation({ need = {}, sensoryInterpretations = [], preferenceReference = [] } = {}) {
    const explicitNeed = [need.taste, need.purpose].filter(Boolean).join('、');
    const lines = [];
    if (explicitNeed) lines.push(`这次你明确想找${explicitNeed}，本次判断会优先按这个方向。`);
    if (sensoryInterpretations.length) {
      lines.push('这款目前能确认的风格线索，会作为判断它是否接近你这次需求的依据。');
    } else {
      lines.push('目前能确认的信息还不足以判断它是否符合你这次的口味方向。');
    }
    if (preferenceReference.length) lines.push(`${preferenceReference.map((item) => item.text).join('')}这只作为低置信口味参考，不会覆盖你这次的需求。`);
    return { lines, preferenceReference };
  }
  global.GuanchaAdapters = { actionLabels, jobToCandidateStatus, candidateToViewModel, buildPreferenceReference, buildPersonalFitPresentation };
}(window));
