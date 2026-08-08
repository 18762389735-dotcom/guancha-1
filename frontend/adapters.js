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
  global.GuanchaAdapters = { actionLabels, jobToCandidateStatus, candidateToViewModel };
}(window));
