(function(){
  const $=s=>document.querySelector(s);
  function getValues(name){return Array.from(document.querySelectorAll('input[name="'+name+'"]:checked')).map(el=>el.value);}
  function clampHours(v){v=parseInt(v||0,10);if(isNaN(v)||v<1)v=1;if(v>8760)v=8760;return v;}
  function payloadFromForm(form){
    const fd=new FormData(form);
    const start_date=fd.get("start_date")||"";
    const end_date=fd.get("end_date")||"";
    const filters={specialty:getValues("specialty"),category:getValues("category"),event:getValues("event"),indicator:getValues("indicator")};
    const hours_events=clampHours(fd.get("hours_events"));
    const hours_labs=clampHours(fd.get("hours_labs"));
    const hours_csv=clampHours(fd.get("hours_csv"));
    const generate_events=!!form.querySelector('#generate-events')?.checked;
    const generate_labs=!!form.querySelector('#generate-labs')?.checked;
    const generate_csv=!!form.querySelector('#generate-csv')?.checked;
    return {start_date,end_date,filters,hours_events,hours_labs,hours_csv,generate_events,generate_labs,generate_csv};
  }
  async function generateLinks(){
    const form=document.getElementById("share-filters");
    const payload=payloadFromForm(form);
    const resp=await fetch(form.dataset.createLinksUrl||"{% url 'medj:create_download_links' %}",{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":form.querySelector('input[name=csrfmiddlewaretoken]').value},body:JSON.stringify(payload)});
    if(!resp.ok){alert("Грешка при генериране на линкове.");return;}
    const data=await resp.json();
    if(payload.generate_events&&data.pdf_events_url){$("#link-pdf-events").value=data.pdf_events_url;const a=$("#btn-pdf-events");a.href=data.pdf_events_url;a.classList.remove("opacity-50","pointer-events-none");}
    if(payload.generate_labs&&data.pdf_labs_url){$("#link-pdf-labs").value=data.pdf_labs_url;const a=$("#btn-pdf-labs");a.href=data.pdf_labs_url;a.classList.remove("opacity-50","pointer-events-none");}
    if(payload.generate_csv&&data.csv_url){$("#link-csv").value=data.csv_url;const a=$("#btn-csv");a.href=data.csv_url;a.classList.remove("opacity-50","pointer-events-none");}
    let qrTarget=null;
    if(payload.generate_events&&data.pdf_events_url) qrTarget=data.pdf_events_url;
    else if(payload.generate_labs&&data.pdf_labs_url) qrTarget=data.pdf_labs_url;
    else if(payload.generate_csv&&data.csv_url) qrTarget=data.csv_url;
    if(qrTarget){$("#qr-img").src=(form.dataset.qrForUrl||"{% url 'medj:qr_for_url' %}")+"?url="+encodeURIComponent(qrTarget);}
  }
  document.getElementById("gen-links").addEventListener("click",generateLinks);
})();
