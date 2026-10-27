"""Explicit server operator action; no default administrator credentials."""
import argparse,asyncio,getpass,os
from app.main import app
from app.identity_runtime import create_admin
parser=argparse.ArgumentParser()
parser.add_argument('command',choices=['create-admin'])
parser.add_argument('--email',required=True)
parser.add_argument('--name',default='Administrator')
parser.add_argument('--password-env',help='Environment variable for synthetic automation only; otherwise prompts securely')
args=parser.parse_args()
password=os.environ.pop(args.password_env) if args.password_env else getpass.getpass('Admin passphrase (15+ characters): ')
async def main():
    async with app.router.lifespan_context(app):
        create_admin(app.state.engine,app.state.identity_metadata,args.email,password,args.name)
        print('Administrator created; no existing customer was promoted')
asyncio.run(main())
