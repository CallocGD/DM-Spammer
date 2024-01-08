import asyncclick as click
from attrs import define, field
from aiohttp_socks import ProxyType
from gdpy_extensions import ProxyClient, COMMON_PROXY_ERRORS
from gd import User, Client
import gd




import asyncio
import random
from string import digits, ascii_lowercase
from typing import NamedTuple





class AsyncHandle:
    def __init__(self, func, threads: int = 2, queue_limit:int = None, timer:int = None) -> None:
        self.q = asyncio.Queue(maxsize=queue_limit if queue_limit else 0)
        self.func = func
        self.threads = threads
        self.workers = [asyncio.create_task(self.run()) for _ in range(threads)]
        self.timer = timer
        self.loop = asyncio.get_event_loop()
    
    async def add_async(self, *args, **kwargs):
        await self.q.put((args, kwargs))

    def add(self, *args, **kwargs):
        self.q.put_nowait((args, kwargs))

    async def join(self):
        """Joins all results together"""
        await self.q.join()
        for w in self.workers:
            await self.q.put(None)
        for w in self.workers:
            w.cancel()
            
    async def cancel(self):
        """Shuts down and kill all the workers and queues..."""
        for w in self.workers:
            await self.q.put(None)
            
        for w in self.workers:
            w.cancel()

    async def run(self):
        while True:
            ak = await self.q.get()
            if ak is None:
                break
            a, k = ak
            try:
                if self.timer is not None:
                    await asyncio.wait_for(self.func(*a, **k), self.timer)
                else:
                    await self.func(*a, **k)
            except Exception as e:
                self.loop.call_soon(print, e)
            self.q.task_done()


class AccountInfo(NamedTuple):
    name:str
    password:str
    proxy:str

    async def send_mail(self, target:User, subject:str, content:str):
        try:
             
            async with ProxyClient(proxy_url=self.proxy).unsafe_login(self.name, self.password) as client:
                message = await client.send_message(target, subject, content)
            return message
        except COMMON_PROXY_ERRORS:
            return None
        except Exception as e:
            print(e)
            return None 


def countlines(file:str):
    def readblocks(_file:str):
        with open(_file, "r") as r:
            while True:
                data = r.read(65535)
                yield data 
                if len(data) < 65535:
                    break
    return sum(r.count("\n") for r in readblocks(file))


# Worth-it at the cost of 4-5 characters gone...
def obfuscate_message(message:str):
    """Prevents robtop from performing easy sql commands to get rid of the dms..."""
    return "".join(random.choices(ascii_lowercase + digits, k=4)) + " " + message



@define
class Death:
    target:User
    threads:int
    proxy_type:ProxyType
    accounts:str
    proxies:str
    dms:str
    titles:str
    lock:asyncio.Lock = asyncio.Lock()
    dm_lock:asyncio.Lock = asyncio.Lock()

    async def doomsday(self):
        async with self.lock:
            with open(self.proxies, "r") as r:
                proxy = self.proxy_type.name.lower() + "://" + random.choice(r.readlines()).stip()
            with open(self.accounts, "r") as r:
                username, password = random.choice(r.readlines()).strip().split(":", 1)
        return AccountInfo(username, password, proxy)
    
    async def random_dm(self):
        async with self.dm_lock:
            with open(self.dms, "r") as r:
                dm = obfuscate_message(random.choice(r.readlines()).strip())
            with open(self.titles, "r") as r:
                title = obfuscate_message(random.choice(r.readlines()).strip())
        return title , dm

    async def harass_target(self, i:int):
        account = await self.doomsday()
        subject , message = await self.random_dm()
        msg = await account.send_mail(self.target, subject, message)
        if msg:
            print(f"[+] Message sent: {msg.id}   Thread: {i}")

    async def start_death(self, limit:int = 100):
        handle = AsyncHandle(self.harass_target, self.threads, queue_limit=100)
        for i in range(limit):
            await handle.add_async(i)
        await handle.join()


def required_file(*names:str, help:str = ""):
    return click.option(*names, type=click.Path(exists=True, file_okay=True, readable=True), prompt=True, help=help)

@click.command
@click.argument("target")
@required_file("--accounts", help="A file with a list of accounts in the format -> username:password 1 per line")
@required_file("--proxies", help="A list of proxies to use")
@click.option("--proxy-type","-pt", default="http", type=click.Choice(["socks5","socks4","http"], help="The Type of proxies to be using", show_default=True))
@required_file("--titles", help="Random Subjects to put in the messages")
@required_file("--messages","-m", help="Random messages to spam at the victim")
@click.option("--limit",type=int, default=100, help="The number of messages to send before quitting out...")
@click.option("--threads","-t",type=click.IntRange(min=1, clamp=True), help="Number of threads to use...")
async def cli(target:str, titles:str, messages:str, accounts:str,  
              proxies:str, proxy_type:ProxyType = ProxyType.HTTP, limit:int = 100, threads:int = 1):
    """A Dm Spammer made by Calloc to spam your victims."""
    print("[...] Obtaining user")
    user = await Client().search_user(target)
    print(f"[+] Target Aquired named: {user.name}")
    death = Death(titles=titles, target=user, threads=threads, proxy_type=proxy_type, accounts=accounts, dms=messages, proxies=proxies)
    await death.start_death(limit=limit)
    print("[+] Spam complete!")

if __name__ == "__main__":
    cli()

