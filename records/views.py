
User = get_user_model()

class SignUpView(CreateView):
    form_class = RegisterForm
    success_url = reverse_lazy("medj:login")
    template_name = "auth/register.html"

def _get_or_create_patient_profile(user):
    profile, _ = PatientProfile.objects.get_or_create(user=user)
    return profile

def _require_patient_profile(user):
    profile, _ = PatientProfile.objects.get_or_create(user=user)
    return profile

def cf_t(obj, field="name"):
    try:
        return obj.safe_translation_getter(field, any_language=True)
    except Exception:
        return getattr(obj, field, "") or ""

def cf_get_patient(user):
    return PatientProfile.objects.filter(user=user).first()

def cf_parse_multi(get, key):
    raw = get.getlist(key) or [get.get(key, "")]
    out = []
    for v in raw:
        if not v:
            continue
        for p in str(v).split(","):
            p = p.strip()
            if p:
                out.append(p)
    return out

def _get_patient(user):
    return PatientProfile.objects.filter(user=user).first()

def _media_tmp_dir() -> Path:
    root = Path(getattr(settings, "MEDIA_ROOT", "/app/media"))
    tmp = root / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp

def _save_tmp(upload_file) -> tuple[str, Path]:
    ext = Path(upload_file.name).suffix or ""
    name = f"{uuid.uuid4().hex}{ext}"
    dest = _media_tmp_dir() / name
    with open(dest, "wb") as out:
        for chunk in upload_file.chunks():
            out.write(chunk)
    return name, dest

def _call_ocr_api(file_path, doc_type_name="", specialty_name=""):
    url = os.environ.get("OCR_API_URL", getattr(settings, "OCR_API_URL", "http://ocrapi:5000/ocr"))
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            data = {}
            if doc_type_name: data["doc_type"] = doc_type_name
            if specialty_name: data["specialty"] = specialty_name
            r = requests.post(url, files=files, data=data, timeout=90)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def _safe_name(obj, field="name"):
    try:
        return obj.safe_translation_getter(field, any_language=True) or ""
    except Exception:
        return getattr(obj, field, "") or ""

def _add_tag(name: str, *objs):
    nm = (name or "").strip()
    if not nm:
        return
    try:
        t, _ = Tag.objects.get_or_create(name=nm)
        for o in objs:
            try:
                o.tags.add(t)
            except Exception:
                pass
    except Exception:
        pass

@require_GET
def landing_page(request: HttpRequest) -> HttpResponse:
    return render(request, "basetemplates/landingpage.html")


@login_required
def personal_card(request: HttpRequest) -> HttpResponse:
    return render(request, "main/personalcard.html")



@login_required
def events_by_specialty(request):
    if request.headers.get("x-requested-with") != "XMLHttpRequest":
        return HttpResponseBadRequest("Expected AJAX")
    patient = _get_patient(request.user)
    if not patient:
        return JsonResponse({"results": []})
    spec_id = request.GET.get("specialty")
    cat_id = request.GET.get("category")
    qs = MedicalEvent.objects.filter(patient=patient).order_by("-event_date", "-id")
    if spec_id and spec_id.isdigit():
        qs = qs.filter(specialty_id=int(spec_id))
    data = [{"id": ev.id, "date": ev.event_date.isoformat() if ev.event_date else "", "summary": (ev.summary or "")[:120]} for ev in qs[:100]]
    return JsonResponse({"results": data})


@login_required
def documents(request: HttpRequest) -> HttpResponse:
    patient = _require_patient_profile(request.user)
    qs = (
        Document.objects.filter(medical_event__patient=patient)
        .select_related("medical_event", "doc_type")
        .order_by("-document_date", "-id")
    )
    return render(request, "subpages/documents.html", {"documents": qs})

@login_required
def profile(request: HttpRequest) -> HttpResponse:
    return render(request, "subpages/profile.html")

@login_required
def doctors(request: HttpRequest) -> HttpResponse:
    return render(request, "subpages/doctors.html")

@login_required
def event_list(request: HttpRequest) -> HttpResponse:
    patient = _require_patient_profile(request.user)
    tag_param = request.GET.get("tag")
    search_q = request.GET.get("q")
    qs = MedicalEvent.objects.filter(patient=patient).select_related("specialty").order_by("-event_date", "-id")
    if search_q:
        qs = qs.filter(summary__icontains=search_q)
    if tag_param:
        qs = qs.filter(tags__name__iexact=tag_param).distinct()
    return render(
        request,
        "subpages/event_list.html",
        {"medical_events": qs, "tags_query": tag_param, "search_query": search_q},
    )

@login_required
def event_detail(request: HttpRequest, pk: int) -> HttpResponse:
    patient = _require_patient_profile(request.user)
    event = get_object_or_404(
        MedicalEvent.objects.select_related("specialty", "patient").prefetch_related(
            "documents", "diagnoses", "treatment_plans", "narrative_sections", "medications", "tags"
        ),
        pk=pk,
        patient=patient,
    )
    measurements = (
        LabTestMeasurement.objects.filter(medical_event=event)
        .select_related("indicator")
        .order_by("indicator__name", "measured_at")
    )
    return render(
        request,
        "subpages/event_detail.html",
        {"medical_event": event, "measurements": measurements, "documents": event.documents.all()},
    )

@login_required
def event_history(request: HttpRequest, pk: int | None = None) -> HttpResponse:
    return event_list(request)

@login_required
@require_POST
def update_event_details(request: HttpRequest, event_id: int | None = None, pk: int | None = None) -> JsonResponse:
    return JsonResponse({"ok": True})

@login_required
def document_detail(request: HttpRequest, pk: int) -> HttpResponse:
    patient = _require_patient_profile(request.user)
    doc = get_object_or_404(
        Document.objects.select_related("medical_event", "doc_type"),
        pk=pk,
        medical_event__patient=patient,
    )
    return render(request, "subpages/document_detail.html", {"document": doc, "event": doc.medical_event})

@login_required
def document_edit(request: HttpRequest, pk: int) -> HttpResponse:
    patient = _require_patient_profile(request.user)
    doc = get_object_or_404(Document, pk=pk, medical_event__patient=patient)
    if request.method == "POST":
        form = DocumentEditForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            messages.success(request, _l("Документът е обновен."))
            return redirect("medj:document_detail", pk=doc.pk)
    else:
        form = DocumentEditForm(instance=doc)
    return render(request, "subpages/document_edit.html", {"document": doc, "form": form})

@login_required
def document_edit_tags(request: HttpRequest, pk: int) -> HttpResponse:
    patient = _require_patient_profile(request.user)
    doc = get_object_or_404(Document, pk=pk, medical_event__patient=patient)
    if request.method == "POST":
        form = DocumentTagForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            messages.success(request, _l("Таговете са обновени."))
            return redirect("medj:document_detail", pk=doc.pk)
    else:
        form = DocumentTagForm(instance=doc)
    return render(request, "subpages/document_edit_tags.html", {"form": form, "document": doc})

@login_required
def document_move(request: HttpRequest, pk: int) -> HttpResponse:
    patient = _require_patient_profile(request.user)
    doc = get_object_or_404(Document, pk=pk, medical_event__patient=patient)
    if request.method == "POST":
        form = MoveDocumentForm(request.POST)
        if form.is_valid():
            target_id = form.cleaned_data["target_event"]
            target_event = get_object_or_404(MedicalEvent, pk=target_id, patient=patient)
            doc.medical_event = target_event
            doc.save(update_fields=["medical_event"])
            messages.success(request, _l("Документът беше преместен."))
            return redirect("medj:document_detail", pk=doc.pk)
    else:
        events = MedicalEvent.objects.filter(patient=patient).order_by("-event_date", "-id")
        form = MoveDocumentForm()
        return render(request, "subpages/document_move.html", {"form": form, "events": events, "document": doc})
    return redirect("medj:document_detail", pk=doc.pk)

@login_required
def labtests(request: HttpRequest) -> HttpResponse:
    return render(request, "subpages/labtests.html")

@login_required
def labtests_view(request: HttpRequest, event_id: int | str) -> HttpResponse:
    patient = _require_patient_profile(request.user)
    event = get_object_or_404(MedicalEvent, pk=event_id, patient=patient)
    indicators = LabIndicator.objects.all().order_by("name")
    series: dict[str, list[dict]] = {}
    qs = (
        LabTestMeasurement.objects.filter(medical_event=event)
        .select_related("indicator")
        .order_by("indicator__name", "measured_at")
    )
    for m in qs:
        key = m.indicator.name
        series.setdefault(key, [])
        series[key].append(
            {
                "date": m.measured_at.isoformat() if m.measured_at else "",
                "value": float(m.value) if isinstance(m.value, Decimal) else m.value,
                "unit": m.indicator.unit or "",
                "abn": m.is_abnormal,
            }
        )
    return render(
        request,
        "subpages/labtests.html",
        {"medical_event": event, "series": series, "indicators": indicators},
    )

@login_required
def labtest_edit(request: HttpRequest, event_id: int | str) -> HttpResponse:
    patient = _require_patient_profile(request.user)
    event = get_object_or_404(MedicalEvent, pk=event_id, patient=patient)
    if request.method == "POST":
        form = LabTestMeasurementForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.medical_event = event
            obj.save()
            messages.success(request, _l("Записано."))
            return redirect("medj:labtests_view", event_id=event.id)
    else:
        form = LabTestMeasurementForm(initial={"medical_event": event.id})
    return render(request, "subpages/labtest_edit.html", {"event": event, "form": form})

@login_required
def share_document_page(request: HttpRequest, medical_event_id: int | str | None = None) -> HttpResponse:
    form = ShareCreateForm(initial={"duration_hours": 24})
    return render(request, "main/share.html", {"medical_event_id": medical_event_id, "form": form})

@login_required
@require_POST
def create_share_token(request: HttpRequest) -> JsonResponse:
    try:
        data = request.POST or json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST
    document_id = data.get("document_id")
    duration_hours = int(data.get("duration_hours", 24))
    if not document_id:
        return JsonResponse({"ok": False, "error": "document_id required"}, status=400)
    patient = _require_patient_profile(request.user)
    doc = get_object_or_404(Document, pk=document_id, medical_event__patient=patient)
    expires_at = timezone.now() + timedelta(hours=duration_hours)
    share = DocumentShare.objects.create(document=doc, expires_at=expires_at, is_active=True)
    return JsonResponse({"ok": True, "token": str(share.token), "expires_at": expires_at.isoformat()})

@require_GET
def share_view(request: HttpRequest, token: uuid.UUID) -> HttpResponse:
    st = get_object_or_404(DocumentShare, token=token)
    if not st.is_active or st.is_expired():
        raise Http404()
    doc = st.document
    return render(request, "subpages/share_view.html", {"mode": "token", "token": str(token), "documents": [doc]})

def share_qr(request: HttpRequest, token: uuid.UUID) -> HttpResponse:
    try:
        import qrcode
    except Exception:
        raise Http404("qrcode library not installed")
    url = request.build_absolute_uri(reverse("medj:share_view", args=[str(token)]))
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")

@login_required
@require_POST
def share_revoke(request: HttpRequest, token: uuid.UUID) -> HttpResponse:
    st = get_object_or_404(DocumentShare, token=token, document__owner=request.user)
    st.is_active = False
    st.save(update_fields=["is_active"])
    messages.success(request, _l("Линкът за споделяне е деактивиран."))
    return redirect("medj:dashboard")

@login_required
@require_POST
def delete_document(request: HttpRequest, document_id: int | str) -> JsonResponse:
    patient = _require_patient_profile(request.user)
    doc = get_object_or_404(Document, pk=document_id, medical_event__patient=patient)
    doc.delete()
    return JsonResponse({"ok": True, "deleted": document_id})

@login_required
@require_POST
def add_medication_tag(request: HttpRequest) -> JsonResponse:
    try:
        data = request.POST or json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST
    document_id = data.get("document_id")
    tag_name = (data.get("tag") or "").strip()
    if not document_id or not tag_name:
        return JsonResponse({"ok": False, "error": "document_id and tag required"}, status=400)
    patient = _require_patient_profile(request.user)
    doc = get_object_or_404(Document, pk=document_id, medical_event__patient=patient)
    tag, _ = Tag.objects.get_or_create(name=tag_name, defaults={"category": "test_type"})
    DocumentTag.objects.get_or_create(document=doc, tag=tag, defaults={"is_inherited": False})
    return JsonResponse({"ok": True, "tag": {"id": tag.id, "name": tag.name}})

@login_required
def events_by_specialty(request: HttpRequest) -> JsonResponse:
    patient = _require_patient_profile(request.user)
    spec_val = request.GET.get("specialty_id") or request.GET.get("specialty")
    try:
        spec_id = int(spec_val)
    except (TypeError, ValueError):
        return JsonResponse({"results": []})
    qs = MedicalEvent.objects.filter(patient=patient, specialty_id=spec_id).order_by("-event_date", "-id")
    results = [
        {
            "id": e.id,
            "date": e.event_date.strftime("%Y-%m-%d") if e.event_date else "",
            "summary": e.summary or "",
        }
        for e in qs
    ]
    return JsonResponse({"results": results})

@login_required
def tags_autocomplete(request: HttpRequest) -> JsonResponse:
    q = request.GET.get("q") or ""
    if not q:
        return JsonResponse({"results": []})
    data = [{"id": t.id, "name": t.name} for t in Tag.objects.filter(name__icontains=q).order_by("name")[:20]]
    return JsonResponse({"results": data})

@login_required
def export_lab_csv(request: HttpRequest) -> HttpResponse:
    rows = ["date,indicator,value,unit\n"]
    content = "".join(rows).encode("utf-8")
    resp = HttpResponse(content, content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="labs.csv"'
    return resp

@require_GET
def healthcheck(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})

@login_required
@require_POST
def upload_preview(request: HttpRequest) -> HttpResponse:
    form = DocumentUploadForm(request.POST, request.FILES, user=request.user)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse({"ok": False, "error": "file is required"}, status=400)

    tmp_rel_path = _save_temp_upload(uploaded_file)

    ocr_text = _ocr(tmp_rel_path) or ""
    ocr_text = ocr_text.strip()
    if not ocr_text:
        ocr_text = ""

    anonymized = ocr_text if getattr(settings, "OCR_RETURNS_ANON", False) else _anonymize(ocr_text)

    specialty = form.cleaned_data["specialty"]
    doc_type = form.cleaned_data["doc_type"]

    gpt_result = _gpt_analyze(
        anonymized,
        doc_kind=getattr(doc_type, "slug", None) or getattr(doc_type, "pk", ""),
        file_type=("pdf" if uploaded_file.name.lower().endswith(".pdf") else "image"),
        specialty_name=getattr(specialty, "safe_translation_getter", lambda k, any_language=True: str(specialty))(
            "name", any_language=True
        ) if specialty else "",
    ) or {}

    html_fragment = gpt_result.get("html_fragment") or gpt_result.get("html") or ""
    explanation = gpt_result.get("explanation") or ""

    payload = {
        "tmp_rel_path": tmp_rel_path,
        "doc_type_id": getattr(doc_type, "id", doc_type),
        "specialty_id": getattr(specialty, "id", specialty),
        "target_event": form.cleaned_data.get("target_event").id if form.cleaned_data.get("target_event") else None,
        "new_event_date": (
            form.cleaned_data.get("new_event_date").strftime("%Y-%m-%d")
            if form.cleaned_data.get("new_event_date") else None
        ),
        "user_tags": form.get_normalized_tags() if hasattr(form, "get_normalized_tags") else [],
        "gpt": gpt_result,
        "ocr_text": ocr_text,
        "filename": uploaded_file.name,
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "ok": True,
            "extracted_text": ocr_text,
            "html_fragment": html_fragment,
            "explanation": explanation,
            "payload": payload,
        })

    return render(
        request,
        "subpages/upload_preview.html",
        {
            "extracted_text": ocr_text,
            "html_fragment": html_fragment,
            "explanation": explanation,
            "payload": json.dumps(payload),
        },
    )

@login_required
@require_POST
@transaction.atomic
def upload_confirm(request: HttpRequest) -> HttpResponse:
    try:
        payload_raw = request.POST.get("payload") or request.body.decode("utf-8")
        payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid payload"}, status=400)
    tmp_rel_path = payload.get("tmp_rel_path")
    if not tmp_rel_path or not default_storage.exists(tmp_rel_path):
        return JsonResponse({"ok": False, "error": "missing temp file"}, status=400)
    patient = _require_patient_profile(request.user)
    spec_id = payload.get("specialty_id")
    doc_type_id = payload.get("doc_type_id")
    specialty = get_object_or_404(MedicalSpecialty, pk=spec_id) if spec_id else None
    doc_type = get_object_or_404(settings.RECORDS_DOCUMENTTYPE_MODEL if hasattr(settings, "RECORDS_DOCUMENTTYPE_MODEL") else Document._meta.get_field("doc_type").remote_field.model, pk=doc_type_id) if doc_type_id else None
    target_event_id = payload.get("target_event")
    new_event_date_str = payload.get("new_event_date")
    ocr_text = payload.get("ocr_text") or ""
    user_tags = payload.get("user_tags") or []
    gpt = payload.get("gpt") or {}
    if target_event_id:
        event = get_object_or_404(MedicalEvent, pk=target_event_id, patient=patient)
    else:
        if not new_event_date_str:
            return JsonResponse({"ok": False, "error": "event date required"}, status=400)
        try:
            event_date = datetime.strptime(new_event_date_str, "%Y-%m-%d").date()
        except Exception:
            return JsonResponse({"ok": False, "error": "bad event date"}, status=400)
        event = MedicalEvent.objects.create(patient=patient, specialty=specialty, event_date=event_date, summary=gpt.get("summary") or "")
    file_bytes = _load_temp_file_bytes(tmp_rel_path)
    final_name = os.path.basename(tmp_rel_path.split("/", 1)[-1])
    content = ContentFile(file_bytes)
    document = Document(
        owner=request.user,
        medical_event=event,
        doc_type=doc_type,
        document_date=event.event_date,
        original_ocr_text=ocr_text,
    )
    document.file.save(final_name, content, save=True)
    all_tag_names = set(user_tags)
    for t in gpt.get("suggested_tags", []) or []:
        if isinstance(t, str):
            all_tag_names.add(t.strip())
        elif isinstance(t, dict):
            name = t.get("name") or t.get("text")
            if name:
                all_tag_names.add(name.strip())
    tag_objs = get_or_create_tags(
        sorted({x for x in all_tag_names if x}),
        doc_type=doc_type,
        specialty=specialty,
        default="test_type",
    )
    if tag_objs:
        event.tags.add(*tag_objs)
        for tag in tag_objs:
            DocumentTag.objects.get_or_create(document=document, tag=tag, defaults={"is_inherited": False})
    for item in gpt.get("blood_test_results", []) or []:
        ind_name = (item.get("indicator_name") or "").strip()
        if not ind_name:
            continue
        unit = (item.get("unit") or "").strip() or None
        ref = item.get("reference_range") or ""
        ref_low = ref_high = None
        if isinstance(ref, str) and "-" in ref:
            parts = [p.strip() for p in ref.split("-", 1)]
            try:
                ref_low = Decimal(parts[0].replace(",", "."))
                ref_high = Decimal(parts[1].replace(",", "."))
            except Exception:
                ref_low = ref_high = None
        indicator, _ = LabIndicator.objects.get_or_create(name=ind_name, defaults={"unit": unit})
        if unit and not indicator.unit:
            indicator.unit = unit
            indicator.save(update_fields=["unit"])
        if ref_low is not None or ref_high is not None:
            indicator.reference_low = ref_low
            indicator.reference_high = ref_high
            indicator.save(update_fields=["reference_low", "reference_high"])
        value = item.get("value")
        try:
            value_dec = Decimal(str(value).replace(",", ".")) if value is not None else None
        except Exception:
            value_dec = None
        LabTestMeasurement.objects.create(
            medical_event=event,
            indicator=indicator,
            value=value_dec if value_dec is not None else Decimal("0"),
            measured_at=event.event_date,
        )
    for d in gpt.get("diagnosis", []) or []:
        if isinstance(d, dict):
            Diagnosis.objects.create(
                medical_event=event,
                code=d.get("code") or None,
                text=d.get("text") or "",
                diagnosed_at=event.event_date,
            )
        elif isinstance(d, str):
            Diagnosis.objects.create(medical_event=event, text=d, diagnosed_at=event.event_date)
    for p in gpt.get("treatment_plan", []) or []:
        txt = p.get("text") if isinstance(p, dict) else str(p)
        if txt:
            TreatmentPlan.objects.create(medical_event=event, plan_text=txt, start_date=event.event_date)
    for n in gpt.get("narratives", []) or []:
        if isinstance(n, dict):
            title = n.get("title") or _l("Наратив")
            NarrativeSectionResult.objects.create(medical_event=event, title=title, content=n.get("content") or "")
        elif isinstance(n, str):
            NarrativeSectionResult.objects.create(medical_event=event, title=_l("Наратив"), content=n)
    for m in gpt.get("medications", []) or []:
        if isinstance(m, dict):
            name = m.get("name") or ""
            if name:
                Medication.objects.create(
                    medical_event=event,
                    name=name,
                    dosage=m.get("dosage") or None,
                    start_date=event.event_date,
                )
    try:
        default_storage.delete(tmp_rel_path)
    except Exception:
        pass
    messages.success(request, _l("Документът и събитието са записани успешно."))
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "saved_event_id": event.id, "document_id": document.id})
    return render(request, "subpages/upload_confirm.html", {"saved_event_id": event.id})
























--------------------EXPORTS-------------------------------------------------------------------------------------------------



@login_required
def document_export_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    context = {"document": doc, "user": request.user}
    pdf_bytes = render_template_to_pdf(request, "subpages/document_export_pdf.html", context)
    return pdf_response(f"document_{pk}.pdf", pdf_bytes, inline=True)

def _save_temp_upload(uploaded_file) -> str:
    tmp_dir = "temp_uploads"
    os.makedirs(os.path.join(settings.MEDIA_ROOT, tmp_dir), exist_ok=True)
    tmp_name = f"{uuid.uuid4()}_{uploaded_file.name}"
    tmp_rel_path = os.path.join(tmp_dir, tmp_name).replace("\\", "/")
    with default_storage.open(tmp_rel_path, "wb+") as dest:
        for chunk in uploaded_file.chunks():
            dest.write(chunk)
    return tmp_rel_path

def _load_temp_file_bytes(tmp_rel_path: str) -> bytes:
    with default_storage.open(tmp_rel_path, "rb") as f:
        return f.read()

def _ocr(tmp_rel_path: str) -> str:
    """
    Викаме ocrapi.vision_handler.extract_text_from_image(abs_path).
    Вземаме абсолютния път от default_storage.path; ако го няма, правим временно копие.
    """
    if not ocr_extract_text:
        return ""
    try:
        abs_path = default_storage.path(tmp_rel_path)
    except Exception:
        abs_path = None

    if not abs_path:
        try:
            from tempfile import NamedTemporaryFile
            with default_storage.open(tmp_rel_path, "rb") as src, NamedTemporaryFile(delete=False, suffix=".bin") as tf:
                tf.write(src.read())
                abs_path = tf.name
        except Exception:
             return ""

    try:
        return ocr_extract_text(abs_path) or ""
    except Exception:
        return ""


def _anonymize(text: str) -> str:
    if anonymize_text_fn:
        try:
            return anonymize_text_fn(text)
        except Exception:
            return text
    return text

def _gpt_analyze(ocr_text: str, doc_kind: str, file_type: str, specialty_name: str) -> dict:
    if gpt_analyze_document:
        try:
            return gpt_analyze_document(
                ocr_text=ocr_text,
                doc_kind=doc_kind,
                file_type=file_type,
                specialty=specialty_name,
            )
        except Exception:
            return {}
    return {}

def _parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None






















@login_required
def event_export_lab_period(request, pk):
    event = get_object_or_404(MedicalEvent, pk=pk, patient__user=request.user)
    dfrom = _parse_date(request.GET.get("from"))
    dto = _parse_date(request.GET.get("to"))

    qs = (LabTestMeasurement.objects
          .filter(medical_event=event)
          .select_related("indicator")
          .order_by("indicator__name", "measured_at"))
    if dfrom:
        qs = qs.filter(measured_at__gte=dfrom)
    if dto:
        qs = qs.filter(measured_at__lte=dto)

    matrix = build_lab_matrix(qs)

    context = {
        "event": event,
        "period_from": dfrom,
        "period_to": dto,
        "lab_headers": matrix["headers"],
        "lab_rows": matrix["rows"],
    }
    pdf_bytes = render_template_to_pdf(request, "print/lab_period_v1.html", context)
    return pdf_response(f"event_{pk}_labs.pdf", pdf_bytes, inline=True)





















@login_required
def event_export_pdf(request, pk):
    event = get_object_or_404(
        MedicalEvent.objects.select_related("patient__user", "specialty").prefetch_related(
            "diagnoses", "medications", "lab_measurements__indicator", "documents", "tags"
        ),
        pk=pk, patient__user=request.user
    )

    patient_name = event.patient.user.get_full_name() or event.patient.user.username
    specialty_name = event.specialty.safe_translation_getter("name", any_language=True) if event.specialty else ""

    diagnoses_rows = [
        {"Код": d.code or "", "Описание": d.text or "", "Дата": d.diagnosed_at or ""}
        for d in event.diagnoses.all()
    ]
    medications_rows = [
        {"Име": m.name or "", "Дозировка": m.dosage or "", "Начало": m.start_date or "", "Край": m.end_date or ""}
        for m in event.medications.all()
    ]
    labs_rows = [
        {
            "Показател": m.indicator.name,
            "Стойност": m.value,
            "Единица": m.indicator.unit or "",
            "Дата": m.measured_at or event.event_date,
        }
        for m in event.lab_measurements.select_related("indicator").all()
    ]
    docs_rows = [
        {"Тип": d.doc_type.safe_translation_getter("name", any_language=True), "Дата": d.document_date, "Бележки": d.notes or ""}
        for d in event.documents.all()
    ]

    context = {
        "patient_name": patient_name,
        "event_date": event.event_date,
        "specialty_name": specialty_name,
        "event_summary": event.summary or "",
        "event_tags": [t.name for t in event.tags.all()],

        "diagnoses_headers": ["Код", "Описание", "Дата"],
        "diagnoses_rows": diagnoses_rows,

        "medications_headers": ["Име", "Дозировка", "Начало", "Край"],
        "medications_rows": medications_rows,

        "labs_headers": ["Показател", "Стойност", "Единица", "Дата"],
        "labs_rows": labs_rows,

        "docs_headers": ["Тип", "Дата", "Бележки"],
        "docs_rows": docs_rows,
    }

    pdf_bytes = render_template_to_pdf(request, "print/event_v1.html", context)
    return pdf_response(f"event_{pk}.pdf", pdf_bytes, inline=True)
