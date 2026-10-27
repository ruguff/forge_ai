import asyncio
from app.main import app
async def main():
    async with app.router.lifespan_context(app):
        print('Catalogue and identity migrations are current')
asyncio.run(main())
