function $(s){return document.querySelector(s)}
function qsp(params){const usp=new URLSearchParams(window.location.search);Object.keys(params).forEach(k=>{const v=params[k];if(v===null||v===""){usp.delete(k)}else{usp.set(k,String(v))}});return usp.toString()}
function bindFilters(){const c=$("#filter_category");const s=$("#filter_specialty");const d=$("#filter_doc_type");const t=$("#filter_tag");function push(){const qs=qsp({category:c?.value||"",specialty:s?.value||"",doc_type:d?.value||"",tag:t?.value||""});const url=window.location.pathname+(qs?`?${qs}`:"");window.location.assign(url)}c?.addEventListener("change",push);s?.addEventListener("change",push);d?.addEventListener("change",push);t?.addEventListener("change",push)}
document.addEventListener("DOMContentLoaded",bindFilters);
