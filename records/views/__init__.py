from .pages_public import landing_page

from .pages_profile import personal_card, profile, doctors

from .documents import (
    documents,
    document_detail,
    document_edit,
    document_edit_tags,
    document_move,
    delete_document,
)

from .events import (
    event_list,
    event_detail,
    event_history,
    update_event_details,
    events_by_specialty,
    tags_autocomplete,
)

from .labs import labtests, labtests_view, labtest_edit, export_lab_csv

from .upload import upload_preview, upload_confirm

from .share import (
    share_document_page,
    create_share_token,
    share_view,
    share_qr,
    share_revoke,
    healthcheck,
)

from .exports import (
    document_export_pdf,
    event_export_lab_period,
    event_export_pdf,
)
