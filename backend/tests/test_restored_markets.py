"""Regression check for the restored authenticated paper-order endpoints (fixture quotes)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.database import Base, get_db
from app.main import create_app
from app.models.trading import PaperFill
from app.models.user import User
from app.services.auth_service import create_access_token

async def test_restored_paper_buy_sell_idempotency_and_ownership():
    engine=create_async_engine('sqlite+aiosqlite:///:memory:')
    factory=async_sessionmaker(engine,expire_on_commit=False)
    async with engine.begin() as conn:await conn.run_sync(Base.metadata.create_all)
    async with factory() as db:
        db.add_all([User(id=u,email=u+'@test.invalid',username=u,hashed_password='unused') for u in ['paper-restore-a','paper-restore-b']])
        await db.commit()
    app=create_app()
    async def test_db():
        async with factory() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise
    app.dependency_overrides[get_db]=test_db
    headers={'Authorization':'Bearer '+create_access_token('paper-restore-a','student')}
    payload={'symbol':'AAPL','side':'buy','quantity':10,'stop_price':95,'take_profit_price':110,'idempotency_key':'restored-buy-0001'}
    quote={'price':100,'timestamp':datetime.now(timezone.utc),'provider':'fixture'}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        with patch('app.routers.trading.fetch_live_quote',new=AsyncMock(return_value=quote)):
            assert (await client.post('/paper/orders',json=payload)).status_code==401
            preview=await client.post('/paper/orders/preview',headers=headers,json=payload)
            assert preview.status_code==200 and preview.json()['allowed']
            bought=await client.post('/paper/orders',headers=headers,json=payload)
            assert bought.status_code==200 and bought.json()['status']=='filled'
            assert (await client.post('/paper/orders',headers=headers,json=payload)).json()['id']==bought.json()['id']
            sold=await client.post('/paper/orders',headers=headers,json={'symbol':'AAPL','side':'sell','quantity':5,'idempotency_key':'restored-sell-0001'})
            assert sold.status_code==200 and sold.json()['status']=='filled'
            portfolio=(await client.get('/paper/portfolio',headers=headers)).json()
            assert portfolio['positions'][0]['quantity']==5 and len(portfolio['orders'])==2
            other={'Authorization':'Bearer '+create_access_token('paper-restore-b','student')}
            assert (await client.get('/paper/portfolio',headers=other)).json()['orders']==[]
    async with factory() as db:
        assert await db.scalar(select(func.count()).select_from(PaperFill))==2
    await engine.dispose()
