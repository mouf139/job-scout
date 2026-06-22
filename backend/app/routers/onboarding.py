import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.resume import Resume
from app.models.resume_extraction import ResumeExtraction
from app.models.interview_session import InterviewSession
from app.models.search_criteria import SearchCriteria
from app.services.auth import get_current_user
from app.services.resume_parser import extract_resume_text
from app.services.interview import extract_resume, chat_interview, generate_criteria

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]:
        raise HTTPException(status_code=400, detail="Only .pdf and .docx files are accepted")

    ext = ".pdf" if file.content_type == "application/pdf" else ".docx"
    user_dir = os.path.join(settings.upload_dir, str(user.id))
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, f"base_resume{ext}")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Save or update resume record
    existing = await db.execute(
        select(Resume).where(Resume.user_id == user.id, Resume.is_base == True)
    )
    old_resume = existing.scalar_one_or_none()
    if old_resume:
        old_resume.file_path = file_path
        old_resume.file_type = ext.lstrip(".")
    else:
        db.add(Resume(user_id=user.id, file_path=file_path, file_type=ext.lstrip("."), is_base=True))

    # Extract text and run AI analysis
    extraction_data = None
    try:
        resume_text = extract_resume_text(file_path)
        extraction_data = await extract_resume(resume_text)

        existing_extraction = await db.execute(
            select(ResumeExtraction).where(ResumeExtraction.user_id == user.id)
        )
        ext_record = existing_extraction.scalar_one_or_none()
        if ext_record:
            ext_record.extracted_name = extraction_data.get("name")
            ext_record.education = extraction_data.get("education")
            ext_record.skills = extraction_data.get("skills")
            ext_record.work_history = extraction_data.get("work_history")
            ext_record.industries = extraction_data.get("industries")
            ext_record.certifications = extraction_data.get("certifications")
            ext_record.raw_extraction_json = extraction_data
        else:
            db.add(ResumeExtraction(
                user_id=user.id,
                extracted_name=extraction_data.get("name"),
                education=extraction_data.get("education"),
                skills=extraction_data.get("skills"),
                work_history=extraction_data.get("work_history"),
                industries=extraction_data.get("industries"),
                certifications=extraction_data.get("certifications"),
                raw_extraction_json=extraction_data,
            ))
    except Exception as e:
        logger.error(f"Resume extraction failed for user {user.id}: {e}")

    await db.commit()
    return {
        "message": "Resume uploaded and analyzed",
        "extraction": extraction_data,
    }


@router.get("/extraction")
async def get_extraction(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResumeExtraction).where(ResumeExtraction.user_id == user.id)
    )
    ext = result.scalar_one_or_none()
    if not ext:
        return None
    return ext.raw_extraction_json


class InterviewMessageRequest(BaseModel):
    message: str
    session_id: int | None = None


@router.post("/interview/start")
async def start_interview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResumeExtraction).where(ResumeExtraction.user_id == user.id)
    )
    extraction = result.scalar_one_or_none()

    # If extraction is missing but resume file exists, re-run extraction
    if not extraction:
        resume_result = await db.execute(
            select(Resume).where(Resume.user_id == user.id, Resume.is_base == True)
        )
        base_resume = resume_result.scalar_one_or_none()
        if not base_resume:
            raise HTTPException(status_code=400, detail="Upload your resume first")

        try:
            resume_text = extract_resume_text(base_resume.file_path)
            extraction_data = await extract_resume(resume_text)
        except Exception as e:
            logger.error(f"Resume extraction failed for user {user.id}: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"AI service unavailable: {type(e).__name__}. Use 'Skip to manual entry' instead.",
            )

        extraction = ResumeExtraction(
            user_id=user.id,
            extracted_name=extraction_data.get("name"),
            education=extraction_data.get("education"),
            skills=extraction_data.get("skills"),
            work_history=extraction_data.get("work_history"),
            industries=extraction_data.get("industries"),
            certifications=extraction_data.get("certifications"),
            raw_extraction_json=extraction_data,
        )
        db.add(extraction)
        await db.commit()
        await db.refresh(extraction)

    # Create a new interview session
    session = InterviewSession(user_id=user.id, messages_json=[])
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Generate the first AI message
    first_message = {"role": "user", "content": "Hi, I'm ready to start the interview."}
    try:
        response = await chat_interview([first_message], extraction.raw_extraction_json)
    except Exception as e:
        logger.error(f"Interview chat failed for user {user.id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"AI service unavailable: {type(e).__name__}. Use 'Skip to manual entry' instead.",
        )

    messages = [
        first_message,
        {"role": "assistant", "content": response["reply"]},
    ]
    session.messages_json = messages
    await db.commit()

    return {
        "session_id": session.id,
        "reply": response["reply"],
        "is_complete": response["is_complete"],
        "question_number": 1,
    }


@router.post("/interview/message")
async def interview_message(
    req: InterviewMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get extraction data
    ext_result = await db.execute(
        select(ResumeExtraction).where(ResumeExtraction.user_id == user.id)
    )
    extraction = ext_result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=400, detail="No resume extraction found")

    # Get or find session
    if req.session_id:
        session_result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.id == req.session_id,
                InterviewSession.user_id == user.id,
            )
        )
        session = session_result.scalar_one_or_none()
    else:
        session_result = await db.execute(
            select(InterviewSession)
            .where(InterviewSession.user_id == user.id, InterviewSession.completed_at == None)
            .order_by(InterviewSession.id.desc())
            .limit(1)
        )
        session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=400, detail="No active interview session. Start one first.")

    # Add user message and get AI response
    messages = list(session.messages_json or [])
    messages.append({"role": "user", "content": req.message})

    response = await chat_interview(messages, extraction.raw_extraction_json)
    messages.append({"role": "assistant", "content": response["reply"]})

    session.messages_json = messages

    if response["is_complete"]:
        from datetime import datetime, timezone
        session.completed_at = datetime.utcnow()

    await db.commit()

    question_count = sum(1 for m in messages if m["role"] == "assistant")

    return {
        "session_id": session.id,
        "reply": response["reply"],
        "is_complete": response["is_complete"],
        "question_number": question_count,
    }


@router.post("/interview/generate-criteria")
async def interview_generate_criteria(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext_result = await db.execute(
        select(ResumeExtraction).where(ResumeExtraction.user_id == user.id)
    )
    extraction = ext_result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=400, detail="No resume extraction found")

    session_result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.user_id == user.id)
        .order_by(InterviewSession.id.desc())
        .limit(1)
    )
    session = session_result.scalar_one_or_none()
    interview_messages = session.messages_json if session else []

    criteria = await generate_criteria(extraction.raw_extraction_json, interview_messages)
    return {"criteria": criteria}


class CriteriaApproveRequest(BaseModel):
    titles: list[str] | None = None
    include_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    location: str | None = None
    radius_miles: int | None = None
    remote_preference: str | None = None
    experience_level: str | None = None
    job_type: str | None = None
    salary_minimum: int | None = None
    industries: list[str] | None = None


@router.post("/criteria/approve")
async def approve_criteria(
    criteria: CriteriaApproveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(SearchCriteria).where(SearchCriteria.user_id == user.id)
    )
    sc = existing.scalar_one_or_none()

    data = criteria.model_dump(exclude_unset=True)
    if sc:
        for key, value in data.items():
            if hasattr(sc, key):
                setattr(sc, key, value)
    else:
        sc = SearchCriteria(user_id=user.id, **data)
        db.add(sc)

    # Set up Google Drive folder if credentials are configured
    if settings.google_refresh_token and not user.google_drive_folder_id:
        try:
            from app.services.google_drive import create_user_folder, share_folder
            folder = create_user_folder(user.name)
            user.google_drive_folder_id = folder["folder_id"]
            user.google_drive_folder_url = folder["folder_url"]
            if user.email:
                share_folder(folder["folder_id"], user.email)
        except Exception as e:
            logger.error(f"Google Drive setup failed for user {user.id}: {e}")

    user.onboarding_completed = True
    await db.commit()
    return {
        "message": "Criteria approved, onboarding complete",
        "google_drive_url": user.google_drive_folder_url,
    }


@router.post("/restart")
async def restart_onboarding(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Clear extraction
    ext_result = await db.execute(
        select(ResumeExtraction).where(ResumeExtraction.user_id == user.id)
    )
    ext = ext_result.scalar_one_or_none()
    if ext:
        await db.delete(ext)

    # Clear incomplete interview sessions
    sessions_result = await db.execute(
        select(InterviewSession).where(InterviewSession.user_id == user.id)
    )
    for session in sessions_result.scalars().all():
        await db.delete(session)

    user.onboarding_completed = False
    await db.commit()
    return {"message": "Onboarding reset. You can now re-upload your resume and redo the interview."}


@router.get("/status")
async def onboarding_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await db.execute(
        select(Resume).where(Resume.user_id == user.id, Resume.is_base == True)
    )
    has_resume = resume.scalar_one_or_none() is not None

    extraction = await db.execute(
        select(ResumeExtraction).where(ResumeExtraction.user_id == user.id)
    )
    has_extraction = extraction.scalar_one_or_none() is not None

    sessions = await db.execute(
        select(InterviewSession).where(InterviewSession.user_id == user.id)
    )
    all_sessions = sessions.scalars().all()
    interview_done = any(s.completed_at for s in all_sessions)
    active_session = next((s for s in all_sessions if not s.completed_at), None)

    criteria = await db.execute(
        select(SearchCriteria).where(SearchCriteria.user_id == user.id)
    )
    has_criteria = criteria.scalar_one_or_none() is not None

    return {
        "has_resume": has_resume,
        "has_extraction": has_extraction,
        "interview_completed": interview_done,
        "active_session_id": active_session.id if active_session else None,
        "criteria_set": has_criteria,
        "onboarding_completed": user.onboarding_completed,
    }
