from __future__ import annotations
import os,uuid,json,io
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse,HttpRequest,HttpResponse
from django.shortcuts import render
import requests
from PIL import Image

TMP_DIR_NAME="tmp_uploads"

def _tmp_dir(user_id:str, token:str)->str:
    p=os.path.join(settings.MEDIA_ROOT,TMP_DIR_NAME,str(user_id),token)
    os.makedirs(p,exist_ok=True)
    return p

@login_required
def upload_page(request:HttpRequest)->HttpResponse:
    return render(request,"main/upload.html",{})

@login_required
def upload_preview(request:HttpRequest)->JsonResponse:
    token=str(uuid.uuid4())
    save_dir=_tmp_dir(request.user.id,token)
    files=request.FILES.getlist("files")
    paths=[]
    for f in files:
        name=f.name
        dest=os.path.join(save_dir,name)
        with open(dest,"wb") as out:
            for chunk in f.chunks():
                out.write(chunk)
        paths.append(dest)
    doc_kind=request.POST.get("doc_kind") or ""
    specialty=request.POST.get("specialty") or ""
    file_type=request.POST.get("file_type") or ""
    ocr_url=getattr(settings,"OCR_API_URL",None)
    html=""
    summary=""
    if ocr_url:
        try:
            mfd=[]
            for p in paths:
                mfd.append(("files",(os.path.basename(p),open(p,"rb"),"application/octet-stream")))
            data={"doc_kind":doc_kind,"specialty":specialty,"file_type":file_type}
            r=requests.post(ocr_url,files=mfd,data=data,timeout=60)
            if r.ok:
                js=r.json()
                html=js.get("html","")
                summary=js.get("summary","")
        except Exception:
            pass
    if not html and not summary:
        summary="Предварителен преглед е наличен. Натиснете Одобри и анализирай."
    return JsonResponse({"token":token,"html":html,"summary":summary})

@login_required
def upload_confirm(request:HttpRequest)->JsonResponse:
    token=request.POST.get("token")
    if not token:
        return JsonResponse({"ok":False})
    return JsonResponse({"ok":True})

@login_required
def upload_history(request:HttpRequest)->HttpResponse:
    return render(request,"main/history.html",{})
