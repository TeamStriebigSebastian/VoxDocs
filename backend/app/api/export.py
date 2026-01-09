"""
Export API endpoints for practice software integration.
"""

import json
import csv
import io
from datetime import datetime, date
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from loguru import logger

from app.core.database import get_db
from app.models.audio import AudioRecording, ProcessingStatus
from app.models.transcription import Transcription
from app.models.classification import Classification

router = APIRouter()


class ExportRequest(BaseModel):
    """Request model for data export."""
    practice_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    format: str = "json"  # json, csv, xml


class DocumentationEntry(BaseModel):
    """Model for a documentation entry."""
    recording_uuid: str
    recorded_at: datetime
    room_name: Optional[str]
    transcription_text: str
    classifications: List[dict]
    teeth_mentioned: List[str]
    diagnoses: List[dict]
    treatments: List[dict]
    findings: List[dict]


@router.post("/generate")
async def generate_export(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate export file for practice software integration.

    Supports JSON, CSV, and XML formats.
    """
    # Build query
    query = select(AudioRecording).options(
        selectinload(AudioRecording.transcription).selectinload(Transcription.classifications),
        selectinload(AudioRecording.room)
    ).where(
        and_(
            AudioRecording.practice_id == request.practice_id,
            AudioRecording.status == ProcessingStatus.COMPLETED,
            AudioRecording.is_deleted == False
        )
    )

    if request.start_date:
        query = query.where(AudioRecording.recorded_at >= datetime.combine(request.start_date, datetime.min.time()))
    if request.end_date:
        query = query.where(AudioRecording.recorded_at <= datetime.combine(request.end_date, datetime.max.time()))

    query = query.order_by(AudioRecording.recorded_at)

    result = await db.execute(query)
    recordings = result.scalars().all()

    # Build documentation entries
    entries = []
    for recording in recordings:
        if not recording.transcription:
            continue

        # Process classifications
        classifications = []
        teeth = set()
        diagnoses = []
        treatments = []
        findings = []

        for c in recording.transcription.classifications:
            class_dict = {
                "category": c.category.type.value if c.category else "other",
                "text": c.extracted_text,
                "normalized": c.normalized_value,
                "tooth": c.tooth_number,
                "surface": c.surface,
                "confidence": c.confidence_score
            }
            classifications.append(class_dict)

            if c.tooth_number:
                teeth.add(c.tooth_number)

            if c.category:
                if c.category.type.value == "diagnosis":
                    diagnoses.append(class_dict)
                elif c.category.type.value == "treatment":
                    treatments.append(class_dict)
                elif c.category.type.value == "finding":
                    findings.append(class_dict)

        entry = DocumentationEntry(
            recording_uuid=recording.uuid,
            recorded_at=recording.recorded_at,
            room_name=recording.room.name if recording.room else None,
            transcription_text=recording.transcription.full_text,
            classifications=classifications,
            teeth_mentioned=sorted(list(teeth)),
            diagnoses=diagnoses,
            treatments=treatments,
            findings=findings
        )
        entries.append(entry)

    logger.info(f"Generating {request.format} export with {len(entries)} entries")

    # Generate output based on format
    if request.format == "json":
        return _generate_json_export(entries, request.practice_id)
    elif request.format == "csv":
        return _generate_csv_export(entries)
    elif request.format == "xml":
        return _generate_xml_export(entries, request.practice_id)
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'json', 'csv', or 'xml'")


def _generate_json_export(entries: List[DocumentationEntry], practice_id: int):
    """Generate JSON export."""
    export_data = {
        "export_info": {
            "generated_at": datetime.utcnow().isoformat(),
            "practice_id": practice_id,
            "total_entries": len(entries),
            "format_version": "1.0"
        },
        "documentation": [entry.model_dump() for entry in entries]
    }

    content = json.dumps(export_data, indent=2, default=str, ensure_ascii=False)

    return StreamingResponse(
        io.StringIO(content),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=voxdocs_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        }
    )


def _generate_csv_export(entries: List[DocumentationEntry]):
    """Generate CSV export."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Recording UUID",
        "Recorded At",
        "Room",
        "Transcription",
        "Teeth Mentioned",
        "Diagnoses",
        "Treatments",
        "Findings"
    ])

    # Data rows
    for entry in entries:
        writer.writerow([
            entry.recording_uuid,
            entry.recorded_at.isoformat(),
            entry.room_name or "",
            entry.transcription_text,
            ", ".join(entry.teeth_mentioned),
            "; ".join([d["text"] for d in entry.diagnoses]),
            "; ".join([t["text"] for t in entry.treatments]),
            "; ".join([f["text"] for f in entry.findings])
        ])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=voxdocs_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


def _generate_xml_export(entries: List[DocumentationEntry], practice_id: int):
    """Generate XML export for practice software integration."""
    # Build XML manually for compatibility
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<VoxDocsExport>',
        f'  <ExportInfo>',
        f'    <GeneratedAt>{datetime.utcnow().isoformat()}</GeneratedAt>',
        f'    <PracticeId>{practice_id}</PracticeId>',
        f'    <TotalEntries>{len(entries)}</TotalEntries>',
        f'    <FormatVersion>1.0</FormatVersion>',
        f'  </ExportInfo>',
        '  <Documentation>'
    ]

    for entry in entries:
        xml_parts.append('    <Entry>')
        xml_parts.append(f'      <RecordingUUID>{entry.recording_uuid}</RecordingUUID>')
        xml_parts.append(f'      <RecordedAt>{entry.recorded_at.isoformat()}</RecordedAt>')
        xml_parts.append(f'      <Room>{_escape_xml(entry.room_name or "")}</Room>')
        xml_parts.append(f'      <Transcription>{_escape_xml(entry.transcription_text)}</Transcription>')

        # Teeth
        xml_parts.append('      <TeethMentioned>')
        for tooth in entry.teeth_mentioned:
            xml_parts.append(f'        <Tooth>{tooth}</Tooth>')
        xml_parts.append('      </TeethMentioned>')

        # Diagnoses
        xml_parts.append('      <Diagnoses>')
        for d in entry.diagnoses:
            xml_parts.append('        <Diagnosis>')
            xml_parts.append(f'          <Text>{_escape_xml(d["text"])}</Text>')
            xml_parts.append(f'          <Tooth>{d.get("tooth") or ""}</Tooth>')
            xml_parts.append(f'          <Normalized>{_escape_xml(d.get("normalized") or "")}</Normalized>')
            xml_parts.append('        </Diagnosis>')
        xml_parts.append('      </Diagnoses>')

        # Treatments
        xml_parts.append('      <Treatments>')
        for t in entry.treatments:
            xml_parts.append('        <Treatment>')
            xml_parts.append(f'          <Text>{_escape_xml(t["text"])}</Text>')
            xml_parts.append(f'          <Tooth>{t.get("tooth") or ""}</Tooth>')
            xml_parts.append('        </Treatment>')
        xml_parts.append('      </Treatments>')

        # Findings
        xml_parts.append('      <Findings>')
        for f in entry.findings:
            xml_parts.append('        <Finding>')
            xml_parts.append(f'          <Text>{_escape_xml(f["text"])}</Text>')
            xml_parts.append(f'          <Tooth>{f.get("tooth") or ""}</Tooth>')
            xml_parts.append(f'          <Normalized>{_escape_xml(f.get("normalized") or "")}</Normalized>')
            xml_parts.append('        </Finding>')
        xml_parts.append('      </Findings>')

        xml_parts.append('    </Entry>')

    xml_parts.append('  </Documentation>')
    xml_parts.append('</VoxDocsExport>')

    content = "\n".join(xml_parts)

    return StreamingResponse(
        io.StringIO(content),
        media_type="application/xml",
        headers={
            "Content-Disposition": f"attachment; filename=voxdocs_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xml"
        }
    )


def _escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


@router.get("/formats")
async def get_supported_formats():
    """Get information about supported export formats."""
    return {
        "formats": [
            {
                "id": "json",
                "name": "JSON",
                "description": "Standard JSON format with full details",
                "mime_type": "application/json"
            },
            {
                "id": "csv",
                "name": "CSV",
                "description": "Comma-separated values for spreadsheet import",
                "mime_type": "text/csv"
            },
            {
                "id": "xml",
                "name": "XML",
                "description": "XML format for practice software integration",
                "mime_type": "application/xml"
            }
        ]
    }
