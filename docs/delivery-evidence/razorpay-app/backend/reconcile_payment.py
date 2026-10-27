"""Explicit operator recovery, using configured server credentials only."""
import asyncio,sys
from app.main import app
async def main():
    async with app.router.lifespan_context(app):
        print(await asyncio.to_thread(app.state.reconcile_razorpay_order,int(sys.argv[1])))
if __name__=='__main__':asyncio.run(main())
