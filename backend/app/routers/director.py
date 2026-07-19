from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.director.live_client import (
    DirectorConfigurationError,
    DirectorResponseError,
    LiveDirectorClient,
)
from app.director.models import DirectorSpeechRequest, DirectorTurn, DirectorTurnRequest

router = APIRouter(prefix="/api/director", tags=["demo-director"])


def _make_director_client() -> LiveDirectorClient:
    return LiveDirectorClient()


@router.post("/turn", response_model=DirectorTurn)
def generate_director_turn(request: DirectorTurnRequest) -> DirectorTurn:
    try:
        return _make_director_client().generate_turn(request)
    except DirectorConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except DirectorResponseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/speech")
def generate_director_speech(request: DirectorSpeechRequest) -> Response:
    try:
        speech = _make_director_client().synthesize(request)
    except DirectorConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except DirectorResponseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return Response(
        content=speech.audio,
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store"},
    )
