import asyncio
import time

from absl import app
from influxdb_client import Point
from line_protocol_cache.producer.autoproducer import (AutoProducer, put_line_protocol,
                                                       put_line_protocols)

from router_data_collection.loadavg import Loadavg
from router_data_collection.meminfo import Meminfo
from router_data_collection.netdev import NetDev
from router_data_collection.router import Router
from router_data_collection.stat import Stat


async def watch_cat(router: Router) -> None:
  analyzers = {
      Loadavg(),
      Meminfo(),
      NetDev(),
      Stat(),
  }

  async for output in router.watch_cat({analyzer.WATCH_CAT_FILE for analyzer in analyzers}, 1):
    time_ns = time.time_ns()

    points: list[Point] = []
    for analyzer in analyzers:
      points.extend(analyzer.generate_points(output, time_ns))

    # [print(p.to_line_protocol()) for p in points]
    # print()
    put_line_protocols([p.to_line_protocol() for p in points])


async def tail_syslog(router: Router) -> None:
  async for line in router.tail_follow('/jffs/syslog.log'):
    point = Point('syslog')
    point.field('syslog', line)
    point.time(time.time_ns())  # type: ignore
    put_line_protocol(point.to_line_protocol())


async def main(_: list[str]) -> None:
  async with AutoProducer(), Router() as router:
    tasks = [
        asyncio.create_task(watch_cat(router), name='watch_cat'),
        asyncio.create_task(tail_syslog(router), name='tail_syslog'),
    ]
    await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

    for task in tasks:
      task.cancel()
    await asyncio.wait(tasks)


def app_run_main() -> None:
  app.run(lambda args: asyncio.run(main(args), debug=True))
