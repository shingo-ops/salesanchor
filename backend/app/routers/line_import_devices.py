"""Initial approval uses Firebase; device credentials can only import Android LINE."""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.routers.tcg_line_import import ImportResultResponse, upload_android_line_export
from app.services import line_import_devices as service

router = APIRouter(prefix='/tcg/line-devices', tags=['line-devices'])
bearer = HTTPBearer()


class StartRequest(BaseModel):
    token_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    name: str = Field(default='Termux', min_length=1, max_length=80, pattern=r'^[^\x00-\x1f\x7f]+$')


class Approval(BaseModel):
    user_code: str = Field(min_length=8, max_length=12)


def no_store(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'


@router.post('/start')
async def start(data: StartRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    no_store(response)
    # Use the socket peer for a conservative limit; do not trust arbitrary XFF.
    return await service.start(db, data.token_hash, data.name, request.client.host if request.client else 'unknown')


@router.get('/status')
async def status(response: Response, cred: HTTPAuthorizationCredentials = Depends(bearer), db: AsyncSession = Depends(get_db)):
    no_store(response)
    return await service.status(db, cred.credentials)


@router.post('/approve')
async def approve(data: Approval, response: Response, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    no_store(response)
    return await service.approve(db, user, data.user_code)


@router.get('')
async def list_devices(response: Response, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    no_store(response)
    return await service.list_devices(db, user)


@router.post('/{identifier}/revoke')
async def revoke(identifier: UUID, response: Response, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    no_store(response)
    await service.revoke(db, user, identifier)
    return {'status': 'revoked'}


async def device_user(cred: HTTPAuthorizationCredentials = Depends(bearer), db: AsyncSession = Depends(get_db)):
    return await service.authenticate(db, cred.credentials)


@router.post('/import', response_model=ImportResultResponse)
async def upload(response: Response, file: UploadFile = File(...), window_hours: int = Form(default=0, ge=0),
                 user=Depends(device_user), db: AsyncSession = Depends(get_db)):
    no_store(response)
    result = await upload_android_line_export(file=file, window_hours=window_hours, db=db, current_user=user)
    await service.used(db, user.device_id)
    return result
